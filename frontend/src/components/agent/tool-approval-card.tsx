"use client";

import { useState } from "react";
import {
  Check,
  ShieldAlert,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import type { ApprovalRequiredEventData } from "@/types/agent";

interface ToolApprovalCardProps {
  approval: ApprovalRequiredEventData;
  disabled: boolean;
  onDecision: (
    approved: boolean,
    feedback?: string,
  ) => void;
}

export function ToolApprovalCard({
  approval,
  disabled,
  onDecision,
}: ToolApprovalCardProps) {
  const [feedback, setFeedback] = useState("");

  return (
    <Card className="min-w-0 max-w-full border-amber-500/40 bg-amber-500/5">
      <CardHeader>
        <div className="flex items-start gap-3">
          <div className="rounded-xl bg-amber-500/15 p-2 text-amber-600">
            <ShieldAlert className="size-5" />
          </div>

          <div className="min-w-0">
            <CardTitle className="text-base">
              Agent 请求执行操作
            </CardTitle>

            <CardDescription className="mt-1">
              该工具可能产生外部副作用，需要你确认后才能继续。
            </CardDescription>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {approval.tool_calls.map((toolCall, index) => (
          <div
            key={toolCall.id ?? `${toolCall.name}-${index}`}
            className="min-w-0 rounded-xl border bg-background p-3"
          >
            <div className="flex items-center justify-between gap-3">
              <p className="min-w-0 text-sm font-medium [overflow-wrap:anywhere]">
                {toolCall.name}
              </p>

              <Badge variant="outline">
                等待授权
              </Badge>
            </div>

            <pre className="mt-3 max-w-full overflow-x-auto whitespace-pre-wrap rounded-lg bg-muted p-3 text-xs leading-5 [overflow-wrap:anywhere]">
              {JSON.stringify(
                toolCall.arguments,
                null,
                2,
              )}
            </pre>
          </div>
        ))}

        <Textarea
          value={feedback}
          onChange={(event) =>
            setFeedback(event.target.value)
          }
          placeholder="审批说明或拒绝原因（可选）"
          disabled={disabled}
          className="min-h-20"
        />

        <div className="flex flex-wrap justify-end gap-2">
          <Button
            type="button"
            variant="outline"
            disabled={disabled}
            onClick={() =>
              onDecision(false, feedback)
            }
          >
            <X />
            拒绝执行
          </Button>

          <Button
            type="button"
            disabled={disabled}
            onClick={() =>
              onDecision(true, feedback)
            }
          >
            <Check />
            批准执行
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
