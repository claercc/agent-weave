from langchain.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool, StructuredTool
from langchain_openai import ChatOpenAI

from app.domain.message import Message, MessageRole
from app.graph.state import State, Route
from app.prompts.system import SYSTEM_PROMPT
from app.services.tool_service import ToolService
from typing import Any, Literal
from app.graph.state import Route, State,RetrievedDocument
from app.rag.retriever import Retriever


def route_request(state: State) -> dict[str, Route]:
    """根据请求路由到正确的节点"""
    collection_name = state.get("collection_name")

    route: Route = (
        "rag"
        if collection_name and collection_name.strip()
        else "agent"
    )
    return {"route": route}

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
    """Create a LangChain tool backed by ToolService."""
    function_spec = tool_dict["function"]

    def tool_wrapper(**kwargs: Any) -> str:
        result = tool_service.call_tool(function_spec["name"], **kwargs)
        if isinstance(result, str):
            return result
        if result.success:
            return str(result.data)
        return f"Tool execution failed: {result.error}"

    return StructuredTool.from_function(
        func=tool_wrapper,
        args_schema=function_spec["parameters"],
        name=function_spec["name"],
        description=function_spec["description"],
    )

def agent_node(
    state: State,
    *,
    llm: ChatOpenAI,
    tools: list[BaseTool],
) -> dict[str, list[AIMessage]]:
    """向模型询问下一个响应或工具调用"""
    messages = [SystemMessage(content=SYSTEM_PROMPT), *state["messages"]]
    model = llm.bind_tools(tools) if tools else llm
    response = model.invoke(messages)
    return {"messages": [response]}

def route_after_agent(state: State) -> Literal["tools", "end"]:
    """根据模型响应判断是否需要调用工具或结束流程"""
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        return "tools"
    return "end"

def prepare_retrieval_query(state: State) -> dict[str, str]:
    """准备检索查询"""
    for message in reversed(state["messages"]):
        if isinstance(message, HumanMessage):
            if not isinstance(message.content, str):
                raise ValueError("HumanMessage content must be a string")
            return {"retrieval_query": message.content}
    raise ValueError("No user message found for retrieval.")

def retrieve_documents(state: State,*,retriever:Retriever,top_k:int=4) -> dict[str, list[RetrievedDocument]]:
    """检索文档"""
    query = state["retrieval_query"]
    collection_name = state.get("collection_name")
    if not collection_name:
        raise ValueError("Collection name is required for retrieval.")
    if not query:
        raise ValueError("Retrieval query is required.")
    results = retriever.retrieve(query=query, collection_name=collection_name, top_k=top_k)

    documents : list[RetrievedDocument] = []
    for result in results:
        distance = result.get("distance")
        score = (
            None if distance is None else 1.0 / (1.0 + float(distance))
        )
        metadata = (
            result.get("metadata")
            or result.get("metadatas")
            or {}
        )
        documents.append(
            {
                "content": result["document"],
                "metadata": metadata,
                "score": score,
            }
        )
    return {"retrieved_documents": documents}

# 实现文档过滤节点
def grade_documents(state: State,*,min_score: float=0.5)  -> dict[str, Any]:
    """过滤文档"""
    documents = state["retrieved_documents"]
    filtered_documents = [
        document
        for document in documents
        if document.get("score") is not None
        and document["score"] >= min_score
    ]
    return {"retrieved_documents": filtered_documents,
            "has_relevant_documents": bool(filtered_documents)}

# 实现条件路由函数
def route_after_grading(state: State) -> Literal["generate", "fallback"]:
    """根据是否有相关文档判断是否需要继续检索或使用模型"""
    has_relevant_documents = state["has_relevant_documents"]
    return "generate" if has_relevant_documents else "fallback"

# 增加 RAG 生成和兜底节点
def select_request_route(state: State) -> Literal["rag", "agent"]:
    """根据是否有集合名称判断是否需要使用 RAG 或模型"""
    route = state.get("route")
    if route == "rag":
        return "rag"
    if route == "agent":
        return "agent"
    raise ValueError("Invalid route selection.")
# 格式化检索文档
def _format_retrieved_documents(documents: list[RetrievedDocument]) -> str:
    parts: list[str] = []

    for index,document in enumerate(documents, start=1):
        source = document["metadata"].get("source", "unknown")
        parts.append(f"[{index}] Source: {source}\n"
                     f"{document['content']}")
    return "\n".join(parts)

def generate_rag_answer(state: State,*,llm: ChatOpenAI) -> dict[str, list[AIMessage]]:
    """根据检索文档生成 RAG 回答"""
    query = state["retrieval_query"]
    documents = state.get("retrieved_documents", [])

    if not documents:
        raise ValueError("No documents to generate RAG answer.")
    if not query:
        raise ValueError("Retrieval query is required.")
    context = _format_retrieved_documents(documents)
    messages = [SystemMessage(content=(
                "You are a knowledge-base assistant. "
                "Answer only from the supplied evidence. "
                "Cite evidence using [1], [2], and so on. "
                "Do not invent facts that are not present in the evidence.")),
                HumanMessage(content=(
                    f"Question:\n{query}\n\n"
                    f"Evidence:\n{context}"
                ))]
    response = llm.invoke(messages)
    return {"messages": [response]}

def fallback_no_relevant_documents(state: State) -> dict[str, list[AIMessage]]:
    """将控制流切换到模型节点"""
    return {"messages": [
        AIMessage(content=(
            "根据当前知识库中检索到的信息，"
            "我无法回答这个问题。"
        ))
    ]}