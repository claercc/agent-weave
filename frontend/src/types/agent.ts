export type AgentMode = "auto" | "chat" | "rag" | "agent";

export type AgentRoute = "chat" | "rag" | "agent";

export type RequestIntent =
  | "conversation"
  | "knowledge_query"
  | "information_tool"
  | "action";

export interface AgentChatRequest {
  session_id: string;
  message: string;
  collection_name?: string;
  mode: AgentMode;
}

export interface AgentResumeRequest {
  session_id: string;
  interrupt_id: string;
  approved: boolean;
  feedback?: string;
}

export interface Citation {
  index: number;
  source: string;
  excerpt: string;
  score: number | null;
}

export interface RetrievalCandidate {
  source: string;
  page: number | string | null;
  score: number | null;
}

export interface RetrievalEventData {
  query: string;
  count: number;
  candidates: RetrievalCandidate[];
}

export interface RetrievalGradedEventData {
  input_count: number;
  kept_count: number;
  discarded_count: number;
  has_relevant_documents: boolean;
}

export interface ApprovalToolCall {
  id: string | null;
  name: string;
  arguments: Record<string, unknown>;
}

export interface StartEventData {
  session_id: string;
  requested_mode: AgentMode;
}

export interface RequestAnalysisEventData {
  intent: RequestIntent;
  route: AgentRoute;
  needs_knowledge: boolean;
  needs_tools: boolean;
  requires_clarification: boolean;
  rewritten_query: string | null;
  clarification_question: string | null;
  reason: string;
}

export interface RouteEventData {
  route: AgentRoute;
  reason: string;
}

export interface TokenEventData {
  content: string;
  node?: string;
}

export interface ToolCallEventData {
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResultEventData {
  name: string;
  content: string;
  executed: boolean;
}

export interface ApprovalRequiredEventData {
  type: "tool_approval";
  session_id: string;
  interrupt_id: string;
  tool_calls: ApprovalToolCall[];
}

export interface ApprovalResolvedEventData {
  session_id: string;
  interrupt_id: string;
  approved: boolean;
  feedback: string | null;
}

export interface CitationsEventData {
  items: Citation[];
}

export interface DoneEventData {
  session_id: string;
  answer: string;
  route: AgentRoute;
  route_reason: string;
  used_tools: string[];
  citations: Citation[];
}

export interface ErrorEventData {
  message: string;
}

export type AgentStreamEvent =
  | { type: "start"; data: StartEventData }
  | {
      type: "analysis";
      data: RequestAnalysisEventData;
    }
  | { type: "route"; data: RouteEventData }
  | {
      type: "retrieval";
      data: RetrievalEventData;
    }
  | {
      type: "retrieval_graded";
      data: RetrievalGradedEventData;
    }
  | { type: "token"; data: TokenEventData }
  | { type: "tool_call"; data: ToolCallEventData }
  | { type: "tool_result"; data: ToolResultEventData }
  | {
      type: "approval_required";
      data: ApprovalRequiredEventData;
    }
  | {
      type: "approval_resolved";
      data: ApprovalResolvedEventData;
    }
  | { type: "citations"; data: CitationsEventData }
  | { type: "done"; data: DoneEventData }
  | { type: "error"; data: ErrorEventData };