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
}

function isAbortError(error: unknown): boolean {
  return (
    error instanceof DOMException &&
    error.name === "AbortError"
  );
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
    ) => {
      setMessages((currentMessages) =>
        currentMessages.map((message) =>
          message.id === assistantMessageId
            ? {
                ...message,
                content: update(message.content),
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
          );

          activeAssistantMessageIdRef.current = null;
          break;

        case "error":
          setError(event.data.message);
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

      const userMessageId = crypto.randomUUID();
      const assistantMessageId = crypto.randomUUID();
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
          setError(
            requestError instanceof Error
              ? requestError.message
              : "Agent 请求失败。",
          );
        }
      } finally {
        abortControllerRef.current = null;
        setIsStreaming(false);
      }
    },
    [handleStreamEvent, pendingApproval],
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
          setError(
            requestError instanceof Error
              ? requestError.message
              : "恢复 Agent 工作流失败。",
          );
        }
      } finally {
        abortControllerRef.current = null;
        setIsStreaming(false);
      }
    },
    [handleStreamEvent, pendingApproval],
  );

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsStreaming(false);
  }, []);

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