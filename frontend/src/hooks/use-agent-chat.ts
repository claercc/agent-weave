"use client";

import { useCallback, useRef, useState } from "react";

import {
  resumeAgentChat,
  streamAgentChat,
} from "@/lib/agent-stream";
import type {
  AgentChatRequest,
  AgentRoute,
  AgentStreamEvent,
  ApprovalRequiredEventData,
  Citation,
} from "@/types/agent";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  status?: "streaming" | "complete" | "stopped" | "error";
}

function isAbortError(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    error.name === "AbortError"
  );
}

function createClientId(): string {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }

  if (typeof globalThis.crypto?.getRandomValues === "function") {
    const bytes = globalThis.crypto.getRandomValues(
      new Uint8Array(16),
    );

    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;

    const hex = Array.from(bytes, (byte) =>
      byte.toString(16).padStart(2, "0"),
    );

    return [
      hex.slice(0, 4).join(""),
      hex.slice(4, 6).join(""),
      hex.slice(6, 8).join(""),
      hex.slice(8, 10).join(""),
      hex.slice(10).join(""),
    ].join("-");
  }

  return `${Date.now().toString(36)}-${Math.random()
    .toString(36)
    .slice(2)}`;
}

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [events, setEvents] = useState<AgentStreamEvent[]>([]);
  const [route, setRoute] = useState<AgentRoute | null>(null);
  const [routeReason, setRouteReason] = useState("");
  const [usedTools, setUsedTools] = useState<string[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [pendingApproval, setPendingApproval] =
    useState<ApprovalRequiredEventData | null>(null);
  const [error, setError] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  const abortControllerRef =
    useRef<AbortController | null>(null);

  /*
   * 审批发生后，第一次 SSE 连接会结束。
   * 因此需要记录当前助手消息 ID，
   * 恢复执行时继续更新同一个回答气泡。
   */
  const activeAssistantMessageIdRef =
    useRef<string | null>(null);

  const updateAssistantMessage = useCallback(
    (
      assistantMessageId: string,
      update: (content: string) => string,
      status?: ChatMessage["status"],
    ) => {
      setMessages((currentMessages) =>
        currentMessages.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                content: update(message.content),
                ...(status ? { status } : {}),
              }
            : message,
        ),
      );
    },
    [],
  );

  const handleStreamEvent = useCallback(
    (
      event: AgentStreamEvent,
      assistantMessageId: string,
    ) => {
      if (event.type !== "token") {
        setEvents((currentEvents) => [
          ...currentEvents,
          event,
        ]);
      }

      switch (event.type) {
        case "route":
          setRoute(event.data.route);
          setRouteReason(event.data.reason);
          break;

        case "token":
          updateAssistantMessage(
            assistantMessageId,
            (currentContent) =>
              currentContent + event.data.content,
          );
          break;

        case "tool_result":
          /*
           * 只有 executed=true 才说明工具实际执行。
           * 被拒绝产生的 ToolMessage 不计入已用工具。
           */
          if (event.data.executed) {
            setUsedTools((currentTools) =>
              currentTools.includes(event.data.name)
                ? currentTools
                : [...currentTools, event.data.name],
            );
          }
          break;

        case "approval_required":
          setPendingApproval(event.data);
          break;

        case "approval_resolved":
          setPendingApproval(null);
          break;

        case "citations":
          setCitations(event.data.items);
          break;

        case "done":
          setRoute(event.data.route);
          setRouteReason(event.data.route_reason);
          setUsedTools(event.data.used_tools);
          setCitations(event.data.citations);
          setPendingApproval(null);

          updateAssistantMessage(
            assistantMessageId,
            () => event.data.answer,
            "complete",
          );

          activeAssistantMessageIdRef.current = null;
          break;

        case "error":
          setError(event.data.message);
          updateAssistantMessage(
            assistantMessageId,
            (currentContent) => currentContent,
            "error",
          );
          break;

        case "stopped":
          break;
      }
    },
    [updateAssistantMessage],
  );

  const sendMessage = useCallback(
    async (request: AgentChatRequest) => {
      const content = request.message.trim();

      if (
        !content ||
        abortControllerRef.current ||
        pendingApproval
      ) {
        return;
      }

      const userMessageId = createClientId();
      const assistantMessageId = createClientId();
      const abortController = new AbortController();

      abortControllerRef.current = abortController;
      activeAssistantMessageIdRef.current =
        assistantMessageId;

      setMessages((currentMessages) => [
        ...currentMessages,
        {
          id: userMessageId,
          role: "user",
          content,
        },
        {
          id: assistantMessageId,
          role: "assistant",
          content: "",
          status: "streaming",
        },
      ]);

      setEvents([]);
      setRoute(null);
      setRouteReason("");
      setUsedTools([]);
      setCitations([]);
      setPendingApproval(null);
      setError("");
      setIsStreaming(true);

      try {
        await streamAgentChat(
          {
            ...request,
            message: content,
            collection_name:
              request.collection_name?.trim() || undefined,
          },
          (event) =>
            handleStreamEvent(
              event,
              assistantMessageId,
            ),
          abortController.signal,
        );
      } catch (requestError) {
        if (!isAbortError(requestError)) {
          updateAssistantMessage(
            assistantMessageId,
            (currentContent) => currentContent,
            "error",
          );
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Agent 请求失败。",
          );
        }
      } finally {
        if (abortControllerRef.current === abortController) {
          abortControllerRef.current = null;
          setIsStreaming(false);
        }
      }
    },
    [handleStreamEvent, pendingApproval, updateAssistantMessage],
  );

  const resolveApproval = useCallback(
    async (approved: boolean, feedback?: string) => {
      const approval = pendingApproval;
      const assistantMessageId =
        activeAssistantMessageIdRef.current;

      if (
        !approval ||
        !assistantMessageId ||
        abortControllerRef.current
      ) {
        return;
      }

      const abortController = new AbortController();

      abortControllerRef.current = abortController;
      setError("");
      setIsStreaming(true);
      updateAssistantMessage(
        assistantMessageId,
        (currentContent) => currentContent,
        "streaming",
      );

      try {
        await resumeAgentChat(
          {
            session_id: approval.session_id,
            interrupt_id: approval.interrupt_id,
            approved,
            feedback: feedback?.trim() || undefined,
          },
          (event) =>
            handleStreamEvent(
              event,
              assistantMessageId,
            ),
          abortController.signal,
        );
      } catch (requestError) {
        if (!isAbortError(requestError)) {
          updateAssistantMessage(
            assistantMessageId,
            (currentContent) => currentContent,
            "error",
          );
          setError(
            requestError instanceof Error
              ? requestError.message
              : "恢复 Agent 工作流失败。",
          );
        }
      } finally {
        if (abortControllerRef.current === abortController) {
          abortControllerRef.current = null;
          setIsStreaming(false);
        }
      }
    },
    [handleStreamEvent, pendingApproval, updateAssistantMessage],
  );

  const stopStreaming = useCallback(() => {
    const abortController = abortControllerRef.current;
    const assistantMessageId =
      activeAssistantMessageIdRef.current;

    if (!abortController || !assistantMessageId) {
      return;
    }

    abortController.abort();
    abortControllerRef.current = null;
    activeAssistantMessageIdRef.current = null;

    updateAssistantMessage(
      assistantMessageId,
      (currentContent) => currentContent,
      "stopped",
    );
    setEvents((currentEvents) => [
      ...currentEvents,
      { type: "stopped", data: { reason: "user" } },
    ]);
    setPendingApproval(null);
    setIsStreaming(false);
  }, [updateAssistantMessage]);

  const clearChat = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    activeAssistantMessageIdRef.current = null;

    setMessages([]);
    setEvents([]);
    setRoute(null);
    setRouteReason("");
    setUsedTools([]);
    setCitations([]);
    setPendingApproval(null);
    setError("");
    setIsStreaming(false);
  }, []);

  return {
    messages,
    events,
    route,
    routeReason,
    usedTools,
    citations,
    pendingApproval,
    error,
    isStreaming,
    sendMessage,
    resolveApproval,
    stopStreaming,
    clearChat,
  };
}
