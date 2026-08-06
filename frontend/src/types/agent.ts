export type AgentMode = "auto" | "chat" | "rag" | "agent";

export type AgentRoute = "chat" | "rag" | "agent";

export interface AgentChatRequest {
  session_id: string;
  message: string;
  collection_name?: string;
  mode: AgentMode;
}

export interface Citation {
  index: number;
  source: string;
  excerpt: string;
  score: number | null;
}

export interface StartEventData {
  session_id: string;
  requested_mode: AgentMode;
}

export interface RouteEventData {
  route: AgentRoute;
  reason: string;
}

export interface TokenEventData {
  content: string;
  node: string;
}

export interface ToolCallEventData {
  name: string;
  arguments: Record<string, unknown>;
}

export interface ToolResultEventData {
  name: string;
  content: string;
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
  | {
      type: "start";
      data: StartEventData;
    }
  | {
      type: "route";
      data: RouteEventData;
    }
  | {
      type: "token";
      data: TokenEventData;
    }
  | {
      type: "tool_call";
      data: ToolCallEventData;
    }
  | {
      type: "tool_result";
      data: ToolResultEventData;
    }
  | {
      type: "citations";
      data: CitationsEventData;
    }
  | {
      type: "done";
      data: DoneEventData;
    }
  | {
      type: "error";
      data: ErrorEventData;
    };