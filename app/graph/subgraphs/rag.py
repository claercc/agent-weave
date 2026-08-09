from functools import partial
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    fallback_no_relevant_documents,
    generate_rag_answer,
    grade_documents,
    prepare_retrieval_query,
    retrieve_documents,
    route_after_grading,
)
from app.graph.state import State
from app.rag.retriever import Retriever


def create_rag_subgraph(
    llm: ChatOpenAI,
    retriever: Retriever,
    min_score: float = 0.4,
) -> Any:
    """构建并编译 RAG 子图。

    参数：
        llm:
            根据知识库证据生成最终回答的聊天模型。
        retriever:
            负责查询向量化和 Chroma 检索的检索器。
        min_score:
            文档最低 cosine 相似度。低于该分数的文档
            不会进入最终回答上下文。

    返回：
        编译后的 RAG 子图。

    状态输入：
        messages:
            当前会话消息。
        collection_name:
            本轮查询使用的知识库名称。
        rewritten_query:
            Router 生成的独立检索问题。

    状态输出：
        retrieval_query:
            实际执行向量检索的查询。
        retrieved_documents:
            通过相关性过滤的文档。
        has_relevant_documents:
            是否存在可以支持回答的证据。
        messages:
            RAG 回答或无证据时的兜底回答。
        citations:
            最终回答使用的引用来源。
    """

    builder = StateGraph(State)

    # 将 Router 产生的改写问题转换为实际检索语句。
    builder.add_node(
        "prepare_retrieval_query",
        prepare_retrieval_query,
    )

    # Retriever 在节点内部完成：
    # 查询向量化 → Chroma 检索 → cosine score 转换。
    builder.add_node(
        "retrieve",
        partial(
            retrieve_documents,
            retriever=retriever,
        ),
    )

    # 使用确定性分数阈值过滤候选文档。
    # 这属于业务规则，不交给模型自由判断。
    builder.add_node(
        "grade",
        partial(
            grade_documents,
            min_score=min_score,
        ),
    )

    # 只有存在有效证据时才允许模型生成 RAG 回答。
    builder.add_node(
        "generate",
        partial(
            generate_rag_answer,
            llm=llm,
        ),
    )

    # 没有有效证据时返回固定回答，避免模型脱离知识库编造。
    builder.add_node(
        "fallback",
        fallback_no_relevant_documents,
    )

    # 子图内部入口。
    builder.add_edge(
        START,
        "prepare_retrieval_query",
    )

    # RAG 固定执行链路：
    # 准备查询 → 检索 → 过滤。
    builder.add_edge(
        "prepare_retrieval_query",
        "retrieve",
    )
    builder.add_edge(
        "retrieve",
        "grade",
    )

    # 过滤完成后根据是否存在有效证据选择结果节点。
    builder.add_conditional_edges(
        "grade",
        route_after_grading,
        {
            "generate": "generate",
            "fallback": "fallback",
        },
    )

    builder.add_edge("generate", END)
    builder.add_edge("fallback", END)

    # 子图不配置独立 checkpointer。
    # 作为主图节点运行时，它会继承主图的持久化上下文。
    return builder.compile()
