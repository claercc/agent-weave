warning: in the working copy of 'app/services/agent_service.py', LF will be replaced by CRLF the next time Git touches it
[1mdiff --git a/app/schemas/response.py b/app/schemas/response.py[m
[1mindex 3e63878..471d60a 100644[m
[1m--- a/app/schemas/response.py[m
[1m+++ b/app/schemas/response.py[m
[36m@@ -1,4 +1,5 @@[m
 from pydantic import BaseModel, Field[m
[32m+[m[32mfrom app.domain.routing import Route[m
 [m
 [m
 class SummaryResponse(BaseModel):[m
[36m@@ -31,6 +32,8 @@[m [mclass AgentChatResponse(BaseModel):[m
 [m
     session_id: str = Field(description="会话ID", min_length=1)[m
     answer: str = Field(description="Agent 最终回答")[m
[32m+[m[32m    route: Route = Field(description="本次请求实际执行的路由")[m
[32m+[m[32m    route_reason: str = Field(description="路由选择原因",min_length=1)[m
     used_tools: list[str] = Field(description="使用的工具", default_factory=list)[m
     citations: list[CitationResponse] = Field([m
         description="引用列表", default_factory=list[m
[1mdiff --git a/app/services/agent_service.py b/app/services/agent_service.py[m
[1mindex 36e5f90..96ea40a 100644[m
[1m--- a/app/services/agent_service.py[m
[1m+++ b/app/services/agent_service.py[m
[36m@@ -6,7 +6,7 @@[m [mfrom typing import Any[m
 [m
 [m
 class AgentService:[m
[31m-    """Run the LangGraph agent and map its state to an API response."""[m
[32m+[m[32m    """运行LangGraph代理并将其状态映射到API响应."""[m
 [m
     def __init__(self, workflow: Any) -> None:[m
         self._workflow = workflow[m
[36m@@ -46,8 +46,12 @@[m [mclass AgentService:[m
             answer=answer,[m
             used_tools=used_tools,[m
             citations=citations,[m
[32m+[m[32m            route=result.get("route","agent"),[m
[32m+[m[32m            route_reason=result.get("route_reason","当前工作流未启用路由器，直接执行 Agent。")[m
         )[m
 [m
[32m+[m
[32m+[m
     @staticmethod[m
     def _find_final_answer(messages: list[Any]) -> str:[m
         for message in reversed(messages):[m
[1mdiff --git a/tests/test_agent_service.py b/tests/test_agent_service.py[m
[1mindex f96b19c..17c2b57 100644[m
[1m--- a/tests/test_agent_service.py[m
[1m+++ b/tests/test_agent_service.py[m
[36m@@ -5,7 +5,7 @@[m [mfrom langchain_core.messages import AIMessage, HumanMessage, ToolMessage[m
 from app.services.agent_service import AgentService[m
 [m
 [m
[31m-def test_used_tools_only_contains_tools_from_current_turn():[m
[32m+[m[32mdef test_used_tools_only_contains_tools_from_current_turn() -> None:[m
     tool_call_message = AIMessage([m
         content="",[m
         tool_calls=[[m
[36m@@ -56,7 +56,7 @@[m [mdef test_used_tools_only_contains_tools_from_current_turn():[m
     assert second_response.used_tools == [][m
 [m
 [m
[31m-def test_agent_service_passes_collection_name_to_workflow():[m
[32m+[m[32mdef test_agent_service_passes_collection_name_to_workflow() -> None:[m
     workflow = Mock()[m
     workflow.invoke.return_value = {[m
         "messages": [[m
[36m@@ -80,7 +80,7 @@[m [mdef test_agent_service_passes_collection_name_to_workflow():[m
     assert initial_state["messages"][0].content == ("How is the project deployed?")[m
 [m
 [m
[31m-def test_agent_service_returns_rag_citations():[m
[32m+[m[32mdef test_agent_service_returns_rag_citations() -> None:[m
     workflow = Mock()[m
     workflow.invoke.return_value = {[m
         "route": "rag",[m
[36m@@ -94,6 +94,7 @@[m [mdef test_agent_service_returns_rag_citations():[m
                 "source": "README.md",[m
                 "excerpt": "The service uses FastAPI.",[m
                 "score": 0.8,[m
[32m+[m[32m                "route_reason": "Explicit rag mode was requested.",[m
             }[m
         ],[m
     }[m
[36m@@ -111,3 +112,5 @@[m [mdef test_agent_service_returns_rag_citations():[m
     assert response.citations[0].index == 1[m
     assert response.citations[0].source == "README.md"[m
     assert response.citations[0].score == 0.8[m
[32m+[m[32m    assert response.route == "rag"[m
[32m+[m[32m    assert response.route_reason == "当前工作流未启用路由器，直接执行 Agent。"[m
