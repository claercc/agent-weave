"use client";

import {
  FormEvent,
  KeyboardEvent,
  useEffect,
  useId,
  useRef,
  useState,
} from "react";
import {
  Bot,
  LoaderCircle,
  Send,
  ShieldAlert,
  Square,
  Trash2,
  User,
} from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useAgentChat } from "@/hooks/use-agent-chat";
import { cn } from "@/lib/utils";
import type { AgentMode } from "@/types/agent";
import { AgentTracePanel } from "@/components/agent/agent-trace-panel";
import { KnowledgeBaseDialog } from "@/components/agent/knowledge-base-dialog";
import { ToolApprovalCard } from "@/components/agent/tool-approval-card";

export function AgentChat() {
  const generatedId = useId().replaceAll(":", "");
  const sessionId = `web-${generatedId}`;

  const [input, setInput] = useState("");
  const [mode, setMode] = useState<AgentMode>("auto");
  const [collectionName, setCollectionName] = useState("");

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

const {
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
} = useAgentChat();

  const canSend =
    input.trim().length > 0 &&
    !isStreaming &&
    !pendingApproval &&
    (mode !== "rag" || collectionName.trim().length > 0);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, pendingApproval]);

  function handleSend() {
    if (!canSend) {
      return;
    }

    void sendMessage({
      session_id: sessionId,
      message: input,
      mode,
      collection_name: collectionName || undefined,
    });

    setInput("");
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    handleSend();
  }

  function handleInputKeyDown(
    event: KeyboardEvent<HTMLTextAreaElement>,
  ) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  return (
    <main className="flex min-h-svh items-center justify-center bg-muted/30 p-4 md:p-8">
      <Card className="flex h-[calc(100svh-2rem)] w-full max-w-7xl flex-col overflow-hidden md:h-[calc(100svh-4rem)]">
        <CardHeader className="border-b">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <CardTitle className="flex items-center gap-2 text-xl">
                <Bot className="size-5" />
                AI Agent Backend
              </CardTitle>

              <CardDescription className="mt-1">
                LangGraph、工具调用与知识库问答
              </CardDescription>
            </div>

            <div className="flex items-center gap-2">
              <Badge variant="secondary">
                {route ? `route: ${route}` : "等待请求"}
              </Badge>

              <Button
                type="button"
                variant="ghost"
                size="icon"
                onClick={clearChat}
                aria-label="清空聊天"
              >
                <Trash2 />
              </Button>
            </div>
          </div>

          <div className="mt-4 flex flex-col gap-3 sm:flex-row">
            <Select
              value={mode}
              onValueChange={(value) =>
                setMode(value as AgentMode)
              }
              disabled={isStreaming}
            >
              <SelectTrigger className="w-full sm:w-40">
                <SelectValue placeholder="选择模式" />
              </SelectTrigger>

              <SelectContent>
                <SelectItem value="auto">自动路由</SelectItem>
                <SelectItem value="chat">普通聊天</SelectItem>
                <SelectItem value="rag">知识库问答</SelectItem>
                <SelectItem value="agent">工具 Agent</SelectItem>
              </SelectContent>
            </Select>

            <Input
              value={collectionName}
              onChange={(event) =>
                setCollectionName(event.target.value)
              }
              placeholder={
                mode === "rag"
                  ? "请输入知识库名称"
                  : "知识库名称（可选）"
              }
              disabled={isStreaming}
              className="flex-1"
            />
            <KnowledgeBaseDialog
                value={collectionName}
                onValueChange={setCollectionName}
                disabled={isStreaming}
            />
          </div>
        </CardHeader>

        <CardContent className="grid min-h-0 flex-1 grid-cols-1 p-0 lg:grid-cols-[minmax(0,1fr)_24rem]">
            <section className="flex min-h-0 flex-col">
                <ScrollArea className="min-h-0 flex-1">
                    <div className="space-y-6 p-4 md:p-6">
                    {messages.length === 0 && (
                        <div className="flex min-h-80 flex-col items-center justify-center text-center">
                        <div className="mb-4 flex size-14 items-center justify-center rounded-2xl bg-primary text-primary-foreground">
                            <Bot className="size-7" />
                        </div>

                        <h2 className="text-lg font-medium">
                            开始与 Agent 对话
                        </h2>

                        <p className="mt-2 max-w-md text-sm text-muted-foreground">
                            可以进行普通聊天、查询知识库，或者要求
                            Agent 使用计算器和天气工具。
                        </p>
                        </div>
                    )}

                    {messages.map((message) => (
                        <div
                        key={message.id}
                        className={cn(
                            "flex items-start gap-3",
                            message.role === "user" && "flex-row-reverse",
                        )}
                        >
                        <Avatar>
                            <AvatarFallback>
                            {message.role === "user" ? (
                                <User className="size-4" />
                            ) : (
                                <Bot className="size-4" />
                            )}
                            </AvatarFallback>
                        </Avatar>

                        <div
                            className={cn(
                            "max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6",
                            message.role === "user"
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted",
                            )}
                        >
                            {message.content ? (
                            <p className="whitespace-pre-wrap">
                                {message.content}
                            </p>
                            ) : (
                            <div className="flex items-center gap-2 text-muted-foreground">
                              {pendingApproval ? (
                                <>
                                  <ShieldAlert className="size-4" />
                                  等待操作授权
                                </>
                              ) : (
                                <>
                                  <LoaderCircle className="size-4 animate-spin" />
                                  Agent 正在思考
                                </>
                              )}
                            </div>
                            )}
                        </div>
                        </div>
                    ))}
                    {pendingApproval && (
                      <ToolApprovalCard
                        approval={pendingApproval}
                        disabled={isStreaming}
                        onDecision={(approved, feedback) => {
                          void resolveApproval(approved, feedback);
                        }}
                      />
                    )}
                    <div ref={messagesEndRef} />
                    </div>
                </ScrollArea>

                {error && (
                    <div className="border-t border-destructive/20 bg-destructive/10 px-4 py-2 text-sm text-destructive">
                    {error}
                    </div>
                )}

                <form
                    onSubmit={handleSubmit}
                    className="border-t bg-background p-4"
                >
                    <div className="rounded-2xl border bg-muted/20 p-2">
                    <Textarea
                        value={input}
                        onChange={(event) => setInput(event.target.value)}
                        onKeyDown={handleInputKeyDown}
                        placeholder="输入消息，Enter 发送，Shift + Enter 换行"
                        disabled={isStreaming}
                        className="min-h-20 resize-none border-0 bg-transparent shadow-none focus-visible:ring-0"
                    />

                    <div className="flex items-center justify-between px-1 pt-2">
                        <span className="text-xs text-muted-foreground">
                        会话：{sessionId}
                        </span>

                        {isStreaming ? (
                        <Button
                            type="button"
                            variant="destructive"
                            onClick={stopStreaming}
                        >
                            <Square />
                            停止
                        </Button>
                        ) : (
                        <Button type="submit" disabled={!canSend}>
                            <Send />
                            发送
                        </Button>
                        )}
                    </div>
                    </div>
                </form>
            </section>

        <AgentTracePanel
          events={events}
          route={route}
          routeReason={routeReason}
          usedTools={usedTools}
          citations={citations}
          isStreaming={isStreaming}
        />
      </CardContent>
      </Card>
    </main>
  );
}