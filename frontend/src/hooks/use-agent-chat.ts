"use client";

import { useCallback, useRef, useState } from "react";

import { streamAgentChat } from "@/lib/agent-stream";
import type {
  AgentChatRequest,
  AgentRoute,
  AgentStreamEvent,
  Citation,
} from "@/types/agent";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [events, setEvents] = useState<AgentStreamEvent[]>([]);
  const [route, setRoute] = useState<AgentRoute | null>(null);
  const [routeReason, setRouteReason] = useState("");
  const [usedTools, setUsedTools] = useState<string[]>([]);
  const [citations, setCitations] = useState<Citation[]>([]);
  const [error, setError] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);

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

  const sendMessage = useCallback(
    async (request: AgentChatRequest) => {
      const content = request.message.trim();

      if (!content || abortControllerRef.current) {
        return;
      }

      const userMessageId = crypto.randomUUID();
      const assistantMessageId = crypto.randomUUID();
      const abortController = new AbortController();

      abortControllerRef.current = abortController;

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
          (event) => {
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

              case "tool_call":
                setUsedTools((currentTools) =>
                  currentTools.includes(event.data.name)
                    ? currentTools
                    : [...currentTools, event.data.name],
                );
                break;

              case "citations":
                setCitations(event.data.items);
                break;

              case "done":
                setRoute(event.data.route);
                setRouteReason(event.data.route_reason);
                setUsedTools(event.data.used_tools);
                setCitations(event.data.citations);

                updateAssistantMessage(
                  assistantMessageId,
                  () => event.data.answer,
                );
                break;

              case "error":
                setError(event.data.message);
                break;
            }
          },
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
    [updateAssistantMessage],
  );

  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    setIsStreaming(false);
  }, []);

  const clearChat = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;

    setMessages([]);
    setEvents([]);
    setRoute(null);
    setRouteReason("");
    setUsedTools([]);
    setCitations([]);
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
    error,
    isStreaming,
    sendMessage,
    stopStreaming,
    clearChat,
  };
}