import "client-only";

import type {
  AgentChatRequest,
  AgentStreamEvent,
} from "@/types/agent";

const AGENT_EVENT_TYPES = new Set<AgentStreamEvent["type"]>([
  "start",
  "route",
  "token",
  "tool_call",
  "tool_result",
  "citations",
  "done",
  "error",
]);

function isAgentEventType(
  value: string,
): value is AgentStreamEvent["type"] {
  return AGENT_EVENT_TYPES.has(value as AgentStreamEvent["type"]);
}

function parseSseBlock(block: string): AgentStreamEvent | null {
  let eventType = "";
  const dataLines: string[] = [];

  for (const line of block.split(/\r?\n/)) {
    if (line.startsWith("event:")) {
      eventType = line.slice("event:".length).trim();
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (!isAgentEventType(eventType) || dataLines.length === 0) {
    return null;
  }

  const data = JSON.parse(dataLines.join("\n")) as unknown;

  return {
    type: eventType,
    data,
  } as AgentStreamEvent;
}

export async function streamAgentChat(
  request: AgentChatRequest,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch("/backend/agent/chat/stream", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    signal,
  });

  if (!response.ok) {
    const detail = await response.text();

    throw new Error(
      detail || `Agent 请求失败，状态码：${response.status}`,
    );
  }

  if (!response.body) {
    throw new Error("浏览器没有收到可读取的 SSE 响应流。");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });

    let boundaryIndex = buffer.indexOf("\n\n");

    while (boundaryIndex >= 0) {
      const block = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);

      const event = parseSseBlock(block);

      if (event) {
        onEvent(event);
      }

      boundaryIndex = buffer.indexOf("\n\n");
    }
  }

  buffer += decoder.decode();

  const finalBlock = buffer.trim();

  if (finalBlock) {
    const event = parseSseBlock(finalBlock);

    if (event) {
      onEvent(event);
    }
  }
}