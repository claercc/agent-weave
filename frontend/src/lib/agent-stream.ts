"use client";

import type {
  AgentChatRequest,
  AgentResumeRequest,
  AgentStreamEvent,
} from "@/types/agent";

const AGENT_EVENT_TYPES = new Set<AgentStreamEvent["type"]>([
  "start",
  "analysis",
  "route",
  "retrieval",
  "retrieval_graded",
  "token",
  "tool_call",
  "tool_result",
  "approval_required",
  "approval_resolved",
  "citations",
  "done",
  "error",
]);

interface ParsedSseBlock {
  event: string;
  data: string;
}

/**
 * 解析单个 SSE 消息块。
 *
 * 一个消息块通常类似：
 *
 * event: token
 * data: {"content":"你好"}
 */
function parseSseBlock(block: string): ParsedSseBlock | null {
  let event = "message";
  const dataLines: string[] = [];

  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
      continue;
    }

    if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trimStart());
    }
  }

  if (dataLines.length === 0) {
    return null;
  }

  return {
    event,
    data: dataLines.join("\n"),
  };
}

/**
 * 消费 Agent SSE 流。
 *
 * 普通聊天和审批恢复都使用相同的流解析逻辑，
 * 区别只在请求地址和请求体。
 */
async function consumeAgentStream(
  url: string,
  requestBody: AgentChatRequest | AgentResumeRequest,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(requestBody),
    signal,
  });

  if (!response.ok) {
    const message = await response.text();

    throw new Error(
      message || `Agent 请求失败，HTTP 状态码：${response.status}`,
    );
  }

  if (!response.body) {
    throw new Error("浏览器没有收到 Agent 流式响应体");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) {
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    buffer = buffer.replaceAll("\r\n", "\n");

    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      dispatchSseBlock(block, onEvent);
    }
  }

  buffer += decoder.decode();
  buffer = buffer.trim();

  if (buffer) {
    dispatchSseBlock(buffer, onEvent);
  }
}

/**
 * 将解析后的 SSE 消息交给页面状态层。
 */
function dispatchSseBlock(
  block: string,
  onEvent: (event: AgentStreamEvent) => void,
): void {
  const parsed = parseSseBlock(block);

  if (!parsed || !AGENT_EVENT_TYPES.has(parsed.event as AgentStreamEvent["type"])) {
    return;
  }

  try {
    onEvent({
      type: parsed.event,
      data: JSON.parse(parsed.data),
    } as AgentStreamEvent);
  } catch {
    onEvent({
      type: "error",
      data: {
        message: `无法解析 Agent SSE 事件：${parsed.event}`,
      },
    });
  }
}

/**
 * 发起新的 Agent 对话。
 */
export async function streamAgentChat(
  request: AgentChatRequest,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  await consumeAgentStream(
    "/backend/agent/chat/stream",
    request,
    onEvent,
    signal,
  );
}

/**
 * 提交人工审批结果，并恢复之前暂停的 Agent 工作流。
 */
export async function resumeAgentChat(
  request: AgentResumeRequest,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  await consumeAgentStream(
    "/backend/agent/chat/resume/stream",
    request,
    onEvent,
    signal,
  );
}