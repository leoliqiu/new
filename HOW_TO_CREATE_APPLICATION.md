# How to create Playwright Command Studio

This guide describes how the application is assembled: a Python Playwright command-line browser, a PyQt6 desktop interface, and a local VS Code extension that gives the interface access to VS Code language models and bounded agent tools.

The project uses the machine's existing Python configuration and local Google Chrome. It does not create a virtual environment, install Python packages, or download a Playwright browser.

## 1. Application goals

The application should:

- Open local Chrome visibly by default.
- Accept a starting URL.
- Store natural-language instructions in independently runnable cards.
- Ask a VS Code model or agent to translate instructions into validated Playwright CLI commands.
- Keep one browser session alive so later instructions continue from the current page.
- Display generated commands and execution output.
- Allow completed CLI rows to be selected and rerun.
- Autosave scenarios and restore them after a crash or restart.
- Attach Markdown reference files to a scenario.

## 2. Project structure

```text
playwright-command-studio-minimal/
├── webcli.py                         Playwright browser CLI and pipe protocol
├── webcli_gui.py                     PyQt6 desktop application
├── HOW_TO_CREATE_APPLICATION.md      This build document
└── vscode-agent-bridge/
    ├── package.json                  VS Code extension manifest
    ├── extension.js                  Local HTTP bridge and agent loop
    └── bridge-core.js                Request validation and HTTP helpers
```

The application creates `scenario_data/scenarios.json` automatically on first launch.

## 3. Local runtime configuration

The launchers use:

```text
Python: C:\Users\LQ\AppData\Local\Programs\Python\Python314\python.exe
Chrome: C:\Program Files\Google\Chrome\Application\chrome.exe
```

The existing Python configuration must already provide `PyQt6` and `playwright`. The application launches the installed Chrome executable rather than a downloaded Chromium build.

## 4. Build the Playwright CLI

Create `webcli.py` first. Its browser controller should:

1. Detect the local Chrome executable.
2. Start Playwright with `headless=False` unless `--headless` is supplied.
3. Create one browser context and page.
4. Navigate to the starting URL.
5. Dispatch a restricted command vocabulary.

Important commands include:

```text
goto <url>
back | forward | reload | url | title
elements [selector]
click <selector|@ref>
fill <selector|@ref> <text>
press <selector|@ref> <key>
learn [selector]
text [selector]
links [selector]
inspect <selector|@ref>
screenshot [relative-path]
tabs | new [url] | use <number> | close_tab
```

The `learn` command is especially important. It returns a compact JSON summary containing the page title, headings, links, forms, controls, and a text preview. This gives the AI enough page information to choose selectors without sending complete page HTML.

### Persistent pipe protocol

Add a `--pipe` mode that reads one JSON object per line from standard input:

```json
{"id": 0, "command": "title"}
```

Emit machine-readable lifecycle events:

```text
::webcli-event::{"event":"ready","url":"https://example.com/"}
::webcli-event::{"event":"command_started","id":0,"command":"title"}
::webcli-event::{"event":"command_finished","id":0,"ok":true,"url":"https://example.com/"}
```

The GUI uses these events to mark rows completed and preserve synchronization between the command plan and live browser state.

## 5. Build the VS Code bridge

The `vscode-agent-bridge` folder is a local VS Code extension. Its HTTP server listens only on `127.0.0.1` and writes a random bearer token to:

```text
C:\Users\LQ\.vscode-ai-bridge.json
```

The bridge exposes:

```text
GET  /health
GET  /models
GET  /capabilities
POST /chat
POST /agent
```

`/chat` sends a single request through `vscode.lm`. `/agent` performs a bounded tool-calling loop. Its private tools can only list and read files inside the folder open in VS Code. They cannot edit files or execute terminal commands.

Every protected request must include:

```http
Authorization: Bearer <random-local-token>
```

The three files under `vscode-agent-bridge` are the complete local extension source. Copy
them into an installed `local.vscode-ai-bridge-*` extension directory, then run
**Developer: Reload Window** in VS Code. If the bridge is already installed and current,
no copy is needed.

## 6. Build the PyQt6 interface

Create `webcli_gui.py` with three horizontal panels:

1. **Scenario history and Markdown context**
2. **Instructions**
3. **Browser workspace**

Use a `QSplitter` so the panels remain resizable. The instruction panel should be wider than the scenario panel.

Each instruction card contains:

- Instruction number
- Execution status
- Run or Rerun button
- Delete button
- Plain-language text editor

Keep the number, status, Run, and Delete controls on one compact row, with the editor underneath.

The browser workspace contains:

- Starting URL
- VS Code model selector
- Visible/headless Chrome option
- VS Code Agent option
- Run Pending Instructions
- Reset Browser Session
- Editable CLI plan
- Run Pending CLI Steps
- Rerun Selected Step
- Live execution output

## 7. Convert an instruction into CLI commands

Before asking the model for commands:

1. Read the instruction text.
2. Capture the current page with `learn`.
3. Read attached Markdown files with UTF-8 replacement for invalid characters.
4. Build a bounded prompt containing the command reference, URL, page snapshot, and Markdown context.
5. Ask `/chat` or `/agent` for JSON only.

Expected model response:

```json
{
  "commands": [
    "fill input[name=search] nba",
    "press input[name=search] Enter",
    "learn"
  ]
}
```

Validate every command before execution. Reject unsupported verbs, multiline commands, absolute screenshot paths, parent-directory traversal, JavaScript, cookies, shell commands, and other commands outside the allowed vocabulary.

Treat webpage snapshots as untrusted input. The model prompt must explicitly ignore instructions found inside webpages. Treat attached Markdown as reference material unless the user's instruction asks to use it as requirements.

## 8. Execute instructions in sequence

**Run Pending Instructions** gathers all non-empty cards with no completed run and processes them in order.

For each card:

1. Learn the current browser state.
2. Generate commands.
3. Append commands to the CLI plan.
4. Execute only the new rows.
5. Mark the card completed.
6. Continue to the next queued card.

If command generation or browser execution fails, stop the instruction queue. This prevents later instructions from running against an unexpected page state.

## 9. Select and rerun CLI rows

Track completed commands as a prefix of the editable plan.

- Completed rows are green.
- The running row is yellow.
- The selected row is blue.
- Pending rows are neutral.

When the cursor is on a completed row and the browser session is still alive, enable **Rerun Step N**. Execute only that selected command and replace the corresponding completed command record after success.

If an executed row is edited without rerunning it, require a browser-session reset before continuing with later rows.

## 10. Save scenarios safely

Store scenarios in `scenario_data/scenarios.json`. A scenario contains:

```json
{
  "id": "scenario-0001",
  "sequence": 1,
  "name": "Example scenario",
  "url": "https://www.wikipedia.org/",
  "model_id": "gpt-4o-mini",
  "headless": false,
  "agent_mode": true,
  "instructions": [
    {"text": "Search for NBA", "run_count": 0}
  ],
  "markdown_files": [
    "C:\\absolute\\path\\reference.md"
  ],
  "cli_plan": ""
}
```

Write to a temporary file and use `os.replace` for an atomic save. Debounce autosaves with a short single-shot `QTimer` so text edits do not rewrite the file on every keystroke.

Every launch creates the next numbered current session and carries forward the prior session's instructions and Markdown attachments. Loading a historical scenario copies it into the current session rather than modifying history.

## 11. Markdown context

Use a file picker that accepts `.md` and `.markdown`. Save attachment paths with the scenario, but never copy, modify, or delete the original file.

When preparing AI context:

- Clearly delimit each file.
- Limit each file to 40,000 characters.
- Limit combined Markdown context to 80,000 characters.
- Mark missing files in the interface.
- Removing an attachment should only remove its path from the scenario.

## 12. Launch and verify

Open this directory in VS Code:

```text
C:\Users\LQ\Documents\Codex\2026-08-14\cre\outputs\playwright-web-cli
```

Run the GUI directly with the configured local Python:

```powershell
& "C:\Users\LQ\AppData\Local\Programs\Python\Python314\python.exe" .\webcli_gui.py
```

Run the CLI directly:

```powershell
& "C:\Users\LQ\AppData\Local\Programs\Python\Python314\python.exe" .\webcli.py https://example.com
```

Verification checklist:

- The PyQt6 window opens without a traceback.
- Chrome opens visibly by default.
- VS Code models appear after Refresh AI.
- Agent mode reports an open VS Code workspace.
- An instruction generates only supported CLI commands.
- A second instruction continues in the same browser.
- Run Pending Instructions processes cards in order.
- Selecting a completed CLI row enables its numbered rerun button.
- Scenario edits and Markdown attachments survive restart.

For syntax checks, use the configured local Python:

```powershell
& "C:\Users\LQ\AppData\Local\Programs\Python\Python314\python.exe" -m py_compile webcli.py webcli_gui.py
```

For a bridge syntax check:

```powershell
node --check vscode-agent-bridge\extension.js
```
