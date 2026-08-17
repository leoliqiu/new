"use strict";

const crypto = require("crypto");
const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const vscode = require("vscode");
const {
  isAuthorized,
  readJsonBody,
  validateChatRequest,
  writeJson
} = require("./bridge-core");

const CONFIG_PATH = path.join(os.homedir(), ".vscode-ai-bridge.json");
const AGENT_TOOLS = [
  {
    name: "workspace_list_files",
    description: "List files in the currently open VS Code workspace. This tool is read-only.",
    inputSchema: {
      type: "object",
      properties: {
        glob: {
          type: "string",
          description: "VS Code glob such as **/*.md or **/README.md."
        }
      },
      additionalProperties: false
    }
  },
  {
    name: "workspace_read_file",
    description: "Read a UTF-8 text file inside the currently open VS Code workspace. This tool is read-only.",
    inputSchema: {
      type: "object",
      properties: {
        path: {
          type: "string",
          description: "Workspace-relative or absolute path to a file inside the workspace."
        }
      },
      required: ["path"],
      additionalProperties: false
    }
  }
];

let server;
let token;
let output;
let approvedModels = [];

async function discoverModels() {
  approvedModels = await vscode.lm.selectChatModels({ vendor: "copilot" });
  return approvedModels;
}

function modelInfo(model) {
  return {
    id: model.id,
    name: model.name || model.id,
    vendor: model.vendor,
    family: model.family,
    version: model.version,
    maxInputTokens: model.maxInputTokens,
    toolCalling: Boolean(model.capabilities && model.capabilities.toolCalling)
  };
}

function writeConnectionConfig(port, authToken) {
  fs.writeFileSync(
    CONFIG_PATH,
    `${JSON.stringify({ host: "127.0.0.1", port, token: authToken }, null, 2)}\n`,
    { encoding: "utf8", mode: 0o600 }
  );
}

async function selectModel(modelId) {
  let model = approvedModels.find((item) => item.id === modelId);
  if (!model) {
    await discoverModels();
    model = approvedModels.find((item) => item.id === modelId);
  }
  if (!model) {
    throw Object.assign(new Error(`Model "${modelId}" is not currently available.`), {
      statusCode: 404
    });
  }
  return model;
}

function toPrompt(messages) {
  return messages.map((message) =>
    message.role === "assistant"
      ? vscode.LanguageModelChatMessage.Assistant(message.content)
      : vscode.LanguageModelChatMessage.User(message.content)
  );
}

async function sendChat(modelId, messages) {
  const model = await selectModel(modelId);
  const request = await model.sendRequest(
    toPrompt(messages),
    {},
    new vscode.CancellationTokenSource().token
  );
  let text = "";
  for await (const fragment of request.text) {
    text += fragment;
  }
  return text;
}

function workspaceFolders() {
  return (vscode.workspace.workspaceFolders || []).map((folder) => folder.uri.fsPath);
}

function isInside(parent, candidate) {
  const relative = path.relative(path.resolve(parent), path.resolve(candidate));
  return relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative));
}

function resolveWorkspacePath(requestedPath) {
  const roots = workspaceFolders();
  if (roots.length === 0) {
    throw new Error("No folder is open in VS Code.");
  }
  const candidate = path.isAbsolute(requestedPath)
    ? path.resolve(requestedPath)
    : path.resolve(roots[0], requestedPath);
  if (!roots.some((root) => isInside(root, candidate))) {
    throw new Error("The agent can only read files inside the open VS Code workspace.");
  }
  return candidate;
}

async function invokePrivateTool(call) {
  if (call.name === "workspace_list_files") {
    const glob = typeof call.input.glob === "string" && call.input.glob.trim()
      ? call.input.glob.trim()
      : "**/*";
    const uris = await vscode.workspace.findFiles(
      glob,
      "**/{.git,node_modules,.venv,venv,__pycache__}/**",
      200
    );
    const files = uris.map((uri) => vscode.workspace.asRelativePath(uri, false));
    return files.length ? files.join("\n") : "No matching workspace files.";
  }
  if (call.name === "workspace_read_file") {
    const requested = String(call.input.path || "").trim();
    if (!requested) {
      throw new Error("workspace_read_file requires a path.");
    }
    const resolved = resolveWorkspacePath(requested);
    const bytes = await vscode.workspace.fs.readFile(vscode.Uri.file(resolved));
    if (bytes.byteLength > 200_000) {
      throw new Error("The requested file is larger than the 200 KB agent read limit.");
    }
    return Buffer.from(bytes).toString("utf8");
  }
  throw new Error(`Unknown private agent tool: ${call.name}`);
}

async function sendAgent(modelId, messages) {
  const model = await selectModel(modelId);
  if (!model.capabilities || !model.capabilities.toolCalling) {
    throw Object.assign(
      new Error(`Model "${modelId}" does not support VS Code agent tool calling.`),
      { statusCode: 400 }
    );
  }
  const prompt = toPrompt(messages);
  const cancellation = new vscode.CancellationTokenSource();
  const maxTurns = vscode.workspace
    .getConfiguration("vscodeAiBridge")
    .get("maxAgentTurns", 8);
  const usedTools = [];

  try {
    for (let turn = 0; turn < maxTurns; turn += 1) {
      const request = await model.sendRequest(
        prompt,
        { tools: AGENT_TOOLS, toolMode: vscode.LanguageModelChatToolMode.Auto },
        cancellation.token
      );
      const assistantParts = [];
      const calls = [];
      let finalText = "";
      for await (const part of request.stream) {
        if (part instanceof vscode.LanguageModelTextPart) {
          assistantParts.push(part);
          finalText += part.value;
        } else if (part instanceof vscode.LanguageModelToolCallPart) {
          assistantParts.push(part);
          calls.push(part);
        }
      }
      if (calls.length === 0) {
        return { text: finalText, usedTools, turns: turn + 1 };
      }

      prompt.push(vscode.LanguageModelChatMessage.Assistant(assistantParts));
      const toolResults = [];
      for (const call of calls) {
        let content;
        try {
          content = await invokePrivateTool(call);
          usedTools.push(call.name);
        } catch (error) {
          content = `Tool error: ${error.message || String(error)}`;
        }
        toolResults.push(
          new vscode.LanguageModelToolResultPart(call.callId, [
            new vscode.LanguageModelTextPart(content)
          ])
        );
      }
      prompt.push(vscode.LanguageModelChatMessage.User(toolResults));
    }
  } finally {
    cancellation.dispose();
  }
  throw Object.assign(new Error("VS Code agent reached its maximum tool-turn limit."), {
    statusCode: 422
  });
}

async function handleRequest(request, response) {
  try {
    if (request.method === "GET" && request.url === "/health") {
      writeJson(response, 200, {
        ok: true,
        service: "vscode-ai-bridge",
        agent: true,
        agentTools: AGENT_TOOLS.map((tool) => tool.name)
      });
      return;
    }
    if (!isAuthorized(request, token)) {
      writeJson(response, 401, { error: "Unauthorized." });
      return;
    }
    if (request.method === "GET" && request.url === "/capabilities") {
      writeJson(response, 200, {
        agent: true,
        agentTools: AGENT_TOOLS.map((tool) => tool.name),
        workspaceFolders: workspaceFolders()
      });
      return;
    }
    if (request.method === "GET" && request.url === "/models") {
      const models = await discoverModels();
      writeJson(response, 200, { models: models.map(modelInfo) });
      return;
    }
    if (request.method === "POST" && ["/chat", "/agent"].includes(request.url)) {
      const body = validateChatRequest(await readJsonBody(request));
      if (request.url === "/agent") {
        writeJson(response, 200, await sendAgent(body.modelId, body.messages));
      } else {
        writeJson(response, 200, { text: await sendChat(body.modelId, body.messages) });
      }
      return;
    }
    writeJson(response, 404, { error: "Not found." });
  } catch (error) {
    const statusCode = Number.isInteger(error.statusCode) ? error.statusCode : 500;
    output.appendLine(error.stack || String(error));
    writeJson(response, statusCode, {
      error: error.message || "The VS Code AI request failed."
    });
  }
}

async function startBridge(showMessage = true) {
  if (server) {
    if (showMessage) {
      vscode.window.showInformationMessage("Playwright VS Code Agent Bridge is already running.");
    }
    return;
  }
  const port = vscode.workspace.getConfiguration("vscodeAiBridge").get("port", 32123);
  token = crypto.randomBytes(32).toString("hex");
  server = http.createServer((request, response) => void handleRequest(request, response));
  server.on("error", (error) => {
    output.appendLine(error.stack || String(error));
    vscode.window.showErrorMessage(`Playwright VS Code Agent Bridge failed: ${error.message}`);
    server = undefined;
  });
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "127.0.0.1", resolve);
  });
  writeConnectionConfig(port, token);
  try {
    await discoverModels();
  } catch (error) {
    output.appendLine(`Copilot model discovery is waiting for sign-in: ${error.message}`);
  }
  output.appendLine(`Listening at http://127.0.0.1:${port} with read-only agent tools.`);
  if (showMessage) {
    vscode.window.showInformationMessage(
      `Playwright VS Code Agent Bridge started with ${approvedModels.length} model(s).`
    );
  }
}

async function stopBridge() {
  if (!server) return;
  await new Promise((resolve) => server.close(resolve));
  server = undefined;
  token = undefined;
  approvedModels = [];
  try {
    fs.unlinkSync(CONFIG_PATH);
  } catch (error) {
    if (error.code !== "ENOENT") output.appendLine(error.stack || String(error));
  }
  vscode.window.showInformationMessage("Playwright VS Code Agent Bridge stopped.");
}

function activate(context) {
  output = vscode.window.createOutputChannel("Playwright VS Code Agent Bridge");
  context.subscriptions.push(
    output,
    vscode.commands.registerCommand("vscodeAiBridge.start", () => startBridge(true)),
    vscode.commands.registerCommand("vscodeAiBridge.stop", stopBridge),
    { dispose: () => void stopBridge() }
  );
  void startBridge(false);
}

function deactivate() {
  return stopBridge();
}

module.exports = { activate, deactivate };
