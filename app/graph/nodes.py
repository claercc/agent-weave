from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.utils import count_tokens_approximately, trim_messages
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI

from app.core.config import get_settings
from app.domain.message import Message, MessageRole
from app.domain.routing import (
    RequestIntent,
    Route,
    RoutingMode,
)
from app.models.output_model import ToolCallResult
from app.prompts.system import SYSTEM_PROMPT
from app.services.tool_service import ToolService
from functools import partial
from html import unescape
import json
import re
from typing import Any, Literal, cast
from uuid import uuid4

from anyio import to_thread
from app.graph.state import (
    Citation,
    ProposedDecision,
    RetrievedDocument,
    State,
)
from app.rag.retriever import Retriever
import logging
from app.models.routing import RequestAnalysis
from app.prompts.routing import REQUEST_ANALYSIS_PROMPT
from langgraph.types import interrupt

logger = logging.getLogger(__name__)


_DSML_TAG = r"(?:｜{1,2}|\|{1,2})DSML(?:｜{1,2}|\|{1,2})"
_DSML_TOOL_CALLS_PATTERN = re.compile(
    rf"\s*<{_DSML_TAG}tool_calls>\s*(.*?)\s*</{_DSML_TAG}tool_calls>\s*",
    re.DOTALL,
)
_DSML_INVOKE_PATTERN = re.compile(
    rf'<{_DSML_TAG}invoke\s+name="([^"]+)">\s*' rf"(.*?)\s*</{_DSML_TAG}invoke>",
    re.DOTALL,
)
_DSML_PARAMETER_PATTERN = re.compile(
    rf'<{_DSML_TAG}parameter\s+name="([^"]+)"'
    rf'(?:\s+string="(true|false)")?>\s*'
    rf"(.*?)\s*</{_DSML_TAG}parameter>",
    re.DOTALL,
)

_NO_TOOLS_PROMPT = """
本次对话没有提供任何可调用的工具。
不要生成工具调用，也不要输出 DSML、XML 或其他内部协议标记。
请仅根据已有对话直接回答用户；如果无法确定，就明确说明无法确定。
""".strip()


def _parse_dsml_tool_calls(
    content: str,
    allowed_tool_names: set[str],
) -> list[dict[str, Any]] | None:
    """解析兼容模型放在 content 中的 DSML 工具调用。

    只有整段内容都是合法 DSML、且所有工具都在已绑定白名单中时才转换。
    这样既不会误处理用户可见文本，也不会绕过工具注册边界。
    """

    outer_match = _DSML_TOOL_CALLS_PATTERN.fullmatch(content)

    if outer_match is None:
        return None

    invoke_block = outer_match.group(1)
    invoke_matches = list(_DSML_INVOKE_PATTERN.finditer(invoke_block))

    if not invoke_matches:
        return None

    if _DSML_INVOKE_PATTERN.sub("", invoke_block).strip():
        return None

    tool_calls: list[dict[str, Any]] = []

    for invoke_match in invoke_matches:
        tool_name = unescape(invoke_match.group(1)).strip()

        if tool_name not in allowed_tool_names:
            return None

        parameter_block = invoke_match.group(2)
        parameter_matches = list(_DSML_PARAMETER_PATTERN.finditer(parameter_block))

        if _DSML_PARAMETER_PATTERN.sub("", parameter_block).strip():
            return None

        arguments: dict[str, Any] = {}

        for parameter_match in parameter_matches:
            parameter_name = unescape(parameter_match.group(1)).strip()
            is_string = parameter_match.group(2) == "true"
            raw_value = unescape(parameter_match.group(3)).strip()

            if not parameter_name or parameter_name in arguments:
                return None

            if is_string:
                value: Any = raw_value
            else:
                try:
                    value = json.loads(raw_value)
                except json.JSONDecodeError:
                    value = raw_value

            arguments[parameter_name] = value

        tool_calls.append(
            {
                "name": tool_name,
                "args": arguments,
                "id": f"dsml-{uuid4().hex}",
                "type": "tool_call",
            }
        )

    return tool_calls


def _normalize_tool_call_response(
    response: AIMessage,
    tools: list[BaseTool],
) -> AIMessage:
    """把 OpenAI 兼容服务返回的 DSML 文本规范为原生工具调用。"""

    if response.tool_calls or not isinstance(response.content, str):
        return response

    parsed_tool_calls = _parse_dsml_tool_calls(
        response.content,
        {tool.name for tool in tools},
    )

    if parsed_tool_calls is None:
        if re.search(rf"<{_DSML_TAG}tool_calls>", response.content):
            return response.model_copy(
                update={
                    "content": (
                        "模型生成了无法识别的工具调用，" "本次未执行任何工具，请重试。"
                    )
                }
            )

        return response

    return response.model_copy(
        update={
            "content": "",
            "tool_calls": parsed_tool_calls,
        }
    )


async def route_request(
    state: State,
    *,
    router_llm: ChatOpenAI | None = None,
) -> dict[str, ProposedDecision]:
    """异步调用模型，产生原始请求分析建议。

    该节点只负责语义分析，不负责业务校验。
    返回结果必须经过 validate_decision 后才能用于路由。
    """

    mode: RoutingMode = state.get(
        "mode",
        "auto",
    )

    collection_name = state.get("collection_name")

    has_collection = bool(collection_name and collection_name.strip())

    conversation = _format_recent_conversation(state)

    # 没有配置 Router 模型时，直接使用确定性兜底策略。
    # 这个分支不发生网络请求，因此不需要 await。
    if router_llm is None:
        return {
            "proposed_decision": (
                _build_fallback_analysis(
                    state=state,
                    mode=mode,
                    has_collection=has_collection,
                )
            )
        }

    analysis_messages = [
        SystemMessage(content=REQUEST_ANALYSIS_PROMPT),
        HumanMessage(
            content=(
                f"用户指定模式：{mode}\n"
                f"是否存在可用知识库："
                f"{has_collection}\n\n"
                f"最近会话：\n{conversation}"
            )
        ),
    ]

    try:
        structured_router = router_llm.with_structured_output(
            RequestAnalysis,
            method="json_mode",
        )

        # ainvoke 在等待模型响应期间释放事件循环，
        # FastAPI 可以继续处理其他请求。
        analysis = cast(
            RequestAnalysis,
            await structured_router.ainvoke(analysis_messages),
        )
    except Exception as exc:
        logger.exception("结构化请求分析失败")

        return {
            "proposed_decision": (
                _build_fallback_analysis(
                    state=state,
                    mode=mode,
                    has_collection=has_collection,
                    failure=exc,
                )
            )
        }

    return {
        "proposed_decision": {
            "intent": analysis.intent,
            "route": analysis.route,
            "needs_knowledge": (analysis.needs_knowledge),
            "needs_tools": (analysis.needs_tools),
            "requires_clarification": (analysis.requires_clarification),
            "clarification_question": (analysis.clarification_question),
            "rewritten_query": (analysis.rewritten_query),
            "reason": analysis.reason,
        }
    }


def _build_fallback_analysis(
    state: State,
    mode: RoutingMode,
    has_collection: bool,
    failure: Exception | None = None,
) -> ProposedDecision:
    """模型不可用时生成可校验的兜底建议。"""

    if mode != "auto":
        route = mode
    elif has_collection:
        route = "rag"
    else:
        route = "agent"

    latest_user_text = _get_latest_user_text(state)

    intent: RequestIntent

    if route == "rag":
        intent = "knowledge_query"
    elif route == "agent":
        intent = "information_tool"
    else:
        intent = "conversation"

    failure_suffix = f"（{type(failure).__name__}）" if failure else ""

    return {
        "intent": intent,
        "route": route,
        "needs_knowledge": route == "rag",
        "needs_tools": route == "agent",
        "requires_clarification": False,
        "clarification_question": None,
        "rewritten_query": (latest_user_text if route == "rag" else None),
        "reason": (
            "请求分析模型不可用，" f"生成确定性兜底建议 {route}" f"{failure_suffix}。"
        ),
    }


def validate_decision(
    state: State,
) -> dict[str, Any]:
    """校验并规范 Router 模型产生的请求分析。

    模型负责理解语义；本节点负责保证意图、路由、
    知识库、工具需求和澄清状态之间保持一致。
    """

    decision = state.get("proposed_decision")

    if decision is None:
        raise ValueError("Router 没有产生请求分析建议")

    mode: RoutingMode = state.get(
        "mode",
        "auto",
    )

    collection_name = state.get("collection_name")

    has_collection = bool(collection_name and collection_name.strip())

    intent = decision["intent"]

    # 自动模式下不直接信任模型返回的 route，
    # 而是根据已经受枚举约束的 intent 进行确定性映射。
    intent_routes: dict[
        RequestIntent,
        Route,
    ] = {
        "conversation": "chat",
        "knowledge_query": "rag",
        "information_tool": "agent",
        "action": "agent",
    }

    expected_route = intent_routes[intent]
    route = expected_route
    reason = decision["reason"]

    if decision["route"] != expected_route:
        reason = (
            f"模型建议路由到 "
            f"{decision['route']}，"
            f"策略根据意图 {intent} "
            f"修正为 {expected_route}；"
            f"{decision['reason']}"
        )

    # 用户显式选择的模式拥有最高优先级。
    if mode != "auto":
        route = mode
        reason = f"用户显式选择 {mode} 模式；" f"{reason}"

    requires_clarification = decision["requires_clarification"]

    clarification_question = decision["clarification_question"]

    rewritten_query = decision["rewritten_query"]

    # knowledge_query 必须依赖知识库。
    # 如果没有选择知识库，就先要求用户补充，
    # 不能进入 RAG 后再发生运行时错误。
    if intent == "knowledge_query" and not has_collection:
        route = "chat"
        requires_clarification = True
        clarification_question = (
            "这个问题需要查询私有知识库，" "请先选择一个知识库后再继续。"
        )
        reason = "识别为知识库查询，" "但当前没有可用知识库。"

    # 显式 RAG 模式同样必须存在知识库。
    if route == "rag" and not has_collection:
        route = "chat"
        requires_clarification = True
        clarification_question = "请先选择一个知识库，" "再使用 RAG 模式继续提问。"
        reason = "用户选择了 RAG 模式，" "但当前没有可用知识库。"

    # 需要澄清时必须存在能够展示给用户的问题。
    if requires_clarification and not clarification_question:
        clarification_question = "为了继续完成这个任务，" "请补充必要的信息。"

    # 进入 RAG 时必须存在一条可执行的检索语句。
    if route == "rag" and not rewritten_query:
        rewritten_query = _get_latest_user_text(state)

    # 非知识库请求不应携带无关的检索查询。
    if intent != "knowledge_query" and route != "rag":
        rewritten_query = None

    # 最终能力需求由经过校验的意图和路由计算，
    # 不直接信任模型返回的布尔值。
    needs_knowledge = intent == "knowledge_query" or route == "rag"

    needs_tools = route == "agent" and intent in {
        "information_tool",
        "action",
    }

    return {
        "intent": intent,
        "route": route,
        "route_reason": reason,
        "needs_knowledge": needs_knowledge,
        "needs_tools": needs_tools,
        "requires_clarification": (requires_clarification),
        "clarification_question": (clarification_question),
        "rewritten_query": rewritten_query,
    }


def clarify_request(
    state: State,
) -> dict[str, list[AIMessage]]:
    """向用户询问完成任务所缺少的信息。"""

    question = state.get("clarification_question")

    if not question:
        question = "为了继续完成这个任务，" "请补充必要的信息。"

    return {"messages": [AIMessage(content=question)]}


def _convert_to_langchain_messages(messages: list[Message]) -> list[Any]:
    """将传统领域消息转换为LangChain消息"""
    langchain_messages: list[Any] = [SystemMessage(content=SYSTEM_PROMPT)]
    for message in messages:
        if message.role == MessageRole.USER:
            langchain_messages.append(HumanMessage(content=message.content))
        elif message.role == MessageRole.ASSISTANT:
            langchain_messages.append(AIMessage(content=message.content))
        elif message.role == MessageRole.TOOL:
            langchain_messages.append(
                ToolMessage(content=message.content, tool_call_id="legacy")
            )
    return langchain_messages


def _get_langchain_tools(tool_service: ToolService) -> list[BaseTool]:
    """将注册的应用程序工具适配为LangChain工具"""
    return [
        _create_langchain_tool(tool_dict, tool_service)
        for tool_dict in tool_service.list_tools()
    ]


def _create_langchain_tool(
    tool_dict: dict[str, Any],
    tool_service: ToolService,
) -> BaseTool:
    """将应用工具适配为 LangChain StructuredTool。

    同时注册同步和异步执行入口：
    同步入口用于兼容旧调用链，
    异步入口用于 LangGraph 异步工作流。
    """

    function_spec = tool_dict["function"]
    tool_name = function_spec["name"]

    def format_result(
        result: ToolCallResult,
    ) -> str:
        """将应用工具结果转换为模型可读取的文本。"""

        if isinstance(result, str):
            return result

        if result.success:
            return tool_service.serialize_result(result.data)

        return "Tool execution failed: " f"{result.error}"

    def tool_wrapper(
        **kwargs: Any,
    ) -> str:
        """同步工具适配入口。"""

        result = tool_service.call_tool(
            tool_name,
            **kwargs,
        )

        return format_result(result)

    async def async_tool_wrapper(
        **kwargs: Any,
    ) -> str:
        """异步工具适配入口。"""

        result = await tool_service.call_tool_async(
            tool_name,
            **kwargs,
        )

        return format_result(result)

    return StructuredTool.from_function(
        func=tool_wrapper,
        coroutine=async_tool_wrapper,
        args_schema=function_spec["parameters"],
        name=tool_name,
        description=function_spec["description"],
    )


async def agent_node(
    state: State,
    *,
    llm: ChatOpenAI,
    tools: list[BaseTool],
) -> dict[str, list[AIMessage]]:
    """向模型询问下一个响应或工具调用"""
    system_prompt = SYSTEM_PROMPT

    if not tools:
        system_prompt = f"{SYSTEM_PROMPT}\n\n{_NO_TOOLS_PROMPT}"

    messages = trim_messages(
        [SystemMessage(content=system_prompt), *state["messages"]],
        strategy="last",
        token_counter=count_tokens_approximately,
        max_tokens=get_settings().agent_context_max_input_tokens,
        start_on="human",
        end_on=("human", "tool"),
        include_system=True,
        allow_partial=False,
    )
    model = llm.bind_tools(tools) if tools else llm
    response = await model.ainvoke(messages)
    response = _normalize_tool_call_response(response, tools)
    return {"messages": [response]}


def route_after_agent(
    state: State,
    *,
    tool_service: ToolService,
) -> Literal["approval", "tools", "end"]:
    """判断 Agent 应该结束、直接执行工具还是等待人工审批。"""

    last_message = state["messages"][-1]

    if not isinstance(last_message, AIMessage):
        return "end"

    if not last_message.tool_calls:
        return "end"

    requires_approval = any(
        tool_service.requires_approval(tool_call["name"])
        for tool_call in last_message.tool_calls
    )

    return "approval" if requires_approval else "tools"


def request_tool_approval(state: State) -> dict[str, Any]:
    """暂停工作流并请求用户审批工具调用。"""

    last_message = state["messages"][-1]

    if not isinstance(last_message, AIMessage):
        raise ValueError("审批节点需要一条 AIMessage。")

    if not last_message.tool_calls:
        raise ValueError("审批节点没有找到工具调用。")

    approval_request = {
        "type": "tool_approval",
        "tool_calls": [
            {
                "id": tool_call.get("id"),
                "name": tool_call["name"],
                "arguments": tool_call.get("args", {}),
            }
            for tool_call in last_message.tool_calls
        ],
    }

    # 首次执行时，这里暂停图并将 approval_request 返回给调用方。
    # 使用 Command(resume=...) 恢复后，interrupt 会返回用户决定。
    resume_value = interrupt(approval_request)

    approved = isinstance(resume_value, dict) and resume_value.get("approved") is True

    feedback: str | None = None

    if isinstance(resume_value, dict):
        feedback_value = resume_value.get("feedback")

        if isinstance(feedback_value, str) and feedback_value.strip():
            feedback = feedback_value.strip()

    approval_decision = {
        "approved": approved,
        "feedback": feedback,
    }

    if approved:
        return {
            "approval_decision": approval_decision,
        }

    rejection_reason = feedback or "用户未批准本次操作。"

    rejection_messages = [
        ToolMessage(
            content=f"工具执行已被用户拒绝。原因：{rejection_reason}",
            name=tool_call["name"],
            tool_call_id=(tool_call.get("id") or f"rejected-{index}"),
        )
        for index, tool_call in enumerate(
            last_message.tool_calls,
            start=1,
        )
    ]

    return {
        "approval_decision": approval_decision,
        "messages": rejection_messages,
    }


def route_after_approval(
    state: State,
) -> Literal["tools", "agent"]:
    """根据审批结果继续执行工具或返回 Agent。"""

    decision = state.get("approval_decision")

    if decision and decision["approved"]:
        return "tools"

    return "agent"


def prepare_retrieval_query(
    state: State,
) -> dict[str, str]:
    """优先使用 Router 改写后的独立检索问题。"""

    rewritten_query = state.get("rewritten_query")

    if isinstance(rewritten_query, str) and rewritten_query.strip():
        retrieval_query = rewritten_query.strip()
    else:
        retrieval_query = _get_latest_user_text(state)

    return {"retrieval_query": retrieval_query}


async def retrieve_documents(
    state: State, *, retriever: Retriever, top_k: int = 4
) -> dict[str, list[RetrievedDocument]]:
    """检索文档"""
    query = state["retrieval_query"]
    collection_name = state.get("collection_name")
    if not collection_name:
        raise ValueError("Collection name is required for retrieval.")
    if not query:
        raise ValueError("Retrieval query is required.")
    results = await to_thread.run_sync(
        partial(
            retriever.retrieve,
            query=query,
            collection_name=collection_name,
            top_k=top_k,
        )
    )

    documents: list[RetrievedDocument] = []
    for result in results:
        distance = result.get("distance")
        score = (
            None
            if distance is None
            else max(
                0.0,
                min(
                    1.0,
                    1.0 - float(distance),
                ),
            )
        )
        metadata = result.get("metadata") or result.get("metadatas") or {}
        documents.append(
            {
                "content": result["document"],
                "metadata": metadata,
                "score": score,
            }
        )
    return {"retrieved_documents": documents}


# 实现文档过滤节点
def grade_documents(state: State, *, min_score: float = 0.5) -> dict[str, Any]:
    """过滤文档"""
    documents = state["retrieved_documents"]
    filtered_documents: list[RetrievedDocument] = []

    for document in documents:
        score = document.get("score")
        if score is not None and score >= min_score:
            filtered_documents.append(document)
    return {
        "retrieved_documents": filtered_documents,
        "has_relevant_documents": bool(filtered_documents),
    }


# 实现条件路由函数
def route_after_grading(state: State) -> Literal["generate", "fallback"]:
    """根据是否有相关文档判断是否需要继续检索或使用模型"""
    has_relevant_documents = state["has_relevant_documents"]
    return "generate" if has_relevant_documents else "fallback"


# 增加 RAG 生成和兜底节点
def select_request_route(
    state: State,
) -> Literal[
    "clarify",
    "chat",
    "rag",
    "agent",
]:
    """选择澄清、聊天、知识库或工具工作流。"""

    if state.get(
        "requires_clarification",
        False,
    ):
        return "clarify"

    route = state.get("route")

    if route in {
        "chat",
        "rag",
        "agent",
    }:
        return route

    raise ValueError("请求分析没有产生有效路由")


# 格式化检索文档
def _format_retrieved_documents(documents: list[RetrievedDocument]) -> str:
    parts: list[str] = []

    for index, document in enumerate(documents, start=1):
        source = document["metadata"].get("source", "unknown")
        parts.append(f"[{index}] Source: {source}\n" f"{document['content']}")
    return "\n".join(parts)


async def generate_rag_answer(state: State, *, llm: ChatOpenAI) -> dict[str, Any]:
    """根据检索文档生成 RAG 回答"""
    query = state["retrieval_query"]
    documents = state.get("retrieved_documents", [])

    if not documents:
        raise ValueError("No documents to generate RAG answer.")
    if not query:
        raise ValueError("Retrieval query is required.")
    context = _format_retrieved_documents(documents)
    citations = _build_citations(documents)
    messages = [
        SystemMessage(
            content=(
                "You are a knowledge-base assistant. "
                "Answer only from the supplied evidence. "
                "Cite evidence using [1], [2], and so on. "
                "Do not invent facts that are not present in the evidence."
            )
        ),
        HumanMessage(content=(f"Question:\n{query}\n\n" f"Evidence:\n{context}")),
    ]
    response = await llm.ainvoke(messages)
    return {"messages": [response], "citations": citations}


def fallback_no_relevant_documents(state: State) -> dict[str, Any]:
    """将控制流切换到模型节点"""
    return {
        "messages": [
            AIMessage(content=("根据当前知识库中检索到的信息，" "我无法回答这个问题。"))
        ],
        "citations": [],
    }


def _build_citations(documents: list[RetrievedDocument]) -> list[Citation]:
    """根据检索文档构建引用"""
    citations: list[Citation] = []
    for index, document in enumerate(documents, start=1):
        source = str(document["metadata"].get("source", "unknown"))
        citations.append(
            {
                "index": index,
                "source": source,
                "excerpt": document["content"][:300],
                "score": document.get("score"),
            }
        )
    return citations


def _format_recent_conversation(
    state: State,
    limit: int = 6,
) -> str:
    """把最近几条消息转换为 Router 可读文本。"""

    formatted_messages: list[str] = []

    for message in state["messages"][-limit:]:
        if isinstance(message, HumanMessage):
            role = "用户"
        elif isinstance(message, AIMessage):
            role = "助手"
        elif isinstance(message, ToolMessage):
            role = "工具"
        else:
            role = "未知"

        content = message.content

        if not isinstance(content, str):
            content = str(content)

        formatted_messages.append(f"{role}：{content}")

    return "\n".join(formatted_messages)


def _get_latest_user_text(state: State) -> str:
    """获取最新的用户消息"""
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            if not isinstance(message.content, str):
                raise ValueError("User message content must be a string.")
            return message.content
    raise ValueError("No user message found.")
