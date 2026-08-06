import {
  BookOpen,
  Bot,
  CheckCircle2,
  CirclePlay,
  GitBranch,
  LoaderCircle,
  TriangleAlert,
  Wrench,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import type {
  AgentRoute,
  AgentStreamEvent,
  Citation,
} from "@/types/agent";

interface AgentTracePanelProps {
  events: AgentStreamEvent[];
  route: AgentRoute | null;
  routeReason: string;
  usedTools: string[];
  citations: Citation[];
  isStreaming: boolean;
}

function TraceEvent({ event }: { event: AgentStreamEvent }) {
  switch (event.type) {
    case "start":
      return (
        <div className="flex gap-3">
          <CirclePlay className="mt-0.5 size-4 shrink-0 text-blue-500" />
          <div>
            <p className="text-sm font-medium">请求开始</p>
            <p className="text-xs text-muted-foreground">
              请求模式：{event.data.requested_mode}
            </p>
          </div>
        </div>
      );

    case "route":
      return (
        <div className="flex gap-3">
          <GitBranch className="mt-0.5 size-4 shrink-0 text-violet-500" />
          <div>
            <p className="text-sm font-medium">
              路由到 {event.data.route}
            </p>
            <p className="mt-1 text-xs leading-5 text-muted-foreground">
              {event.data.reason}
            </p>
          </div>
        </div>
      );

    case "tool_call":
      return (
        <div className="flex gap-3">
          <Wrench className="mt-0.5 size-4 shrink-0 text-amber-500" />
          <div className="min-w-0">
            <p className="text-sm font-medium">
              调用工具：{event.data.name}
            </p>
            <pre className="mt-2 overflow-x-auto rounded-xl bg-muted p-2 text-xs">
              {JSON.stringify(event.data.arguments, null, 2)}
            </pre>
          </div>
        </div>
      );

    case "tool_result":
      return (
        <div className="flex gap-3">
          <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-500" />
          <div className="min-w-0">
            <p className="text-sm font-medium">
              工具执行完成
            </p>
            <p className="mt-1 break-words text-xs leading-5 text-muted-foreground">
              {event.data.content}
            </p>
          </div>
        </div>
      );

    case "citations":
      return (
        <div className="flex gap-3">
          <BookOpen className="mt-0.5 size-4 shrink-0 text-cyan-500" />
          <div>
            <p className="text-sm font-medium">引用已生成</p>
            <p className="text-xs text-muted-foreground">
              共 {event.data.items.length} 条引用
            </p>
          </div>
        </div>
      );

    case "done":
      return (
        <div className="flex gap-3">
          <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-500" />
          <div>
            <p className="text-sm font-medium">执行完成</p>
            <p className="text-xs text-muted-foreground">
              最终路由：{event.data.route}
            </p>
          </div>
        </div>
      );

    case "error":
      return (
        <div className="flex gap-3">
          <TriangleAlert className="mt-0.5 size-4 shrink-0 text-destructive" />
          <div>
            <p className="text-sm font-medium text-destructive">
              执行失败
            </p>
            <p className="text-xs text-destructive">
              {event.data.message}
            </p>
          </div>
        </div>
      );

    default:
      return null;
  }
}

export function AgentTracePanel({
  events,
  route,
  routeReason,
  usedTools,
  citations,
  isStreaming,
}: AgentTracePanelProps) {
  return (
    <aside className="hidden min-h-0 flex-col border-l bg-muted/10 lg:flex">
      <div className="flex items-center justify-between px-5 py-4">
        <div className="flex items-center gap-2">
          <Bot className="size-4" />
          <h2 className="font-medium">执行轨迹</h2>
        </div>

        {isStreaming && (
          <LoaderCircle className="size-4 animate-spin text-muted-foreground" />
        )}
      </div>

      <Separator />

      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-6 p-5">
          {route && (
            <section>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                当前路由
              </p>

              <Badge>{route}</Badge>

              {routeReason && (
                <p className="mt-2 text-xs leading-5 text-muted-foreground">
                  {routeReason}
                </p>
              )}
            </section>
          )}

          {usedTools.length > 0 && (
            <section>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                使用工具
              </p>

              <div className="flex flex-wrap gap-2">
                {usedTools.map((tool) => (
                  <Badge key={tool} variant="outline">
                    <Wrench />
                    {tool}
                  </Badge>
                ))}
              </div>
            </section>
          )}

          <section>
            <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              事件
            </p>

            {events.length === 0 ? (
              <p className="text-sm leading-6 text-muted-foreground">
                发送消息后，这里会显示路由、工具调用和引用信息。
              </p>
            ) : (
              <div className="space-y-5">
                {events.map((event, index) => (
                  <TraceEvent
                    key={`${event.type}-${index}`}
                    event={event}
                  />
                ))}
              </div>
            )}
          </section>

          {citations.length > 0 && (
            <section>
              <p className="mb-3 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                引用来源
              </p>

              <div className="space-y-3">
                {citations.map((citation) => (
                  <div
                    key={`${citation.index}-${citation.source}`}
                    className="rounded-2xl border bg-background p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="truncate text-sm font-medium">
                        [{citation.index}] {citation.source}
                      </p>

                      {citation.score !== null && (
                        <Badge variant="secondary">
                          {(citation.score * 100).toFixed(0)}%
                        </Badge>
                      )}
                    </div>

                    <p className="mt-2 line-clamp-4 text-xs leading-5 text-muted-foreground">
                      {citation.excerpt}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>
      </ScrollArea>
    </aside>
  );
}