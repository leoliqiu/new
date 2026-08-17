"use strict";

const MAX_BODY_BYTES = 2 * 1024 * 1024;

function readJsonBody(request) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];

    request.on("data", (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY_BYTES) {
        reject(Object.assign(new Error("Request body is too large."), { statusCode: 413 }));
        request.destroy();
        return;
      }
      chunks.push(chunk);
    });

    request.on("end", () => {
      try {
        const text = Buffer.concat(chunks).toString("utf8");
        resolve(text ? JSON.parse(text) : {});
      } catch {
        reject(Object.assign(new Error("Request body must be valid JSON."), { statusCode: 400 }));
      }
    });
    request.on("error", reject);
  });
}

function isAuthorized(request, token) {
  return request.headers.authorization === `Bearer ${token}`;
}

function writeJson(response, statusCode, data) {
  const body = Buffer.from(JSON.stringify(data), "utf8");
  response.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": body.length,
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff"
  });
  response.end(body);
}

function validateChatRequest(body) {
  if (!body || typeof body !== "object") {
    throw Object.assign(new Error("A JSON object is required."), { statusCode: 400 });
  }
  if (typeof body.modelId !== "string" || !body.modelId.trim()) {
    throw Object.assign(new Error("modelId is required."), { statusCode: 400 });
  }
  if (!Array.isArray(body.messages) || body.messages.length === 0) {
    throw Object.assign(new Error("messages must be a non-empty array."), { statusCode: 400 });
  }

  const messages = body.messages.map((message) => {
    if (!message || !["user", "assistant"].includes(message.role)) {
      throw Object.assign(new Error("Each message role must be user or assistant."), {
        statusCode: 400
      });
    }
    if (typeof message.content !== "string" || !message.content.trim()) {
      throw Object.assign(new Error("Each message must contain non-empty text."), {
        statusCode: 400
      });
    }
    return { role: message.role, content: message.content };
  });
  return { modelId: body.modelId.trim(), messages };
}

module.exports = { isAuthorized, readJsonBody, validateChatRequest, writeJson };
