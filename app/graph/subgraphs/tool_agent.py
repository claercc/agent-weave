from functools import partial
from typing import Any

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from app.graph.nodes import (
    _get_langchain_tools,
    agent_node,
    request_tool_approval,
    route_after_agent,
    route_after_approval,
)
from app.graph.state import State
from app.services.tool_service import ToolService


def create_tool_agent_subgraph(
    llm: ChatOpenAI,
    tool_service: ToolService,
) -> Any:
    """构建并编译工具 Agent 子图。

    参数：
        llm:
            负责生成回答和决定工具调用的聊天模型。
        tool_service:
            提供工具注册、工具执行和风险审批策略。

    返回：
        编译后的工具 Agent 子图。

    状态输入：
        messages:
            当前会话消息和已有工具执行结果。

    状态输出：
        messages:
            模型回答、工具调用和工具执行结果。
        approval_decision:
            用户对高风险工具的审批结果。

    设计边界：
        子图负责工具决策、风险审批和 ReAct 循环；
        主图只负责决定本轮请求是否进入工具 Agent。
    """

    # 将应用自己的 BaseTool 适配为 LangChain Tool。
    tools = _get_langchain_tools(tool_service)

    builder = StateGraph(State)

    # Agent 根据消息历史决定：
    # 1. 直接生成最终回答；
    # 2. 调用一个或多个工具。
    builder.add_node(
        "agent",
        partial(
            agent_node,
            llm=llm,
            tools=tools,
        ),
    )

    builder.add_edge(START, "agent")

    if not tools:
        # 没有注册工具时，Agent 只能直接回答。
        builder.add_edge("agent", END)
        return builder.compile()

    # ToolNode 只负责执行已经通过策略判断的工具调用。
    # 工具异常会转换为 ToolMessage 返回给 Agent，
    # 由 Agent 向用户解释失败原因。
    builder.add_node(
        "tools",
        ToolNode(
            tools,
            # 处理工具异常，将 ToolMessage 写回 State。
            handle_tool_errors=True,
        ),
    )

    # approval 节点只处理高风险操作。
    # interrupt 会保存当前状态并暂停子图，
    # 恢复时接收用户的批准或拒绝结果。
    builder.add_node(
        "approval",
        request_tool_approval,
    )

    # Agent 产生消息后，使用确定性代码检查工具调用，
    # 而不是让模型自己决定是否需要审批。
    builder.add_conditional_edges(
        "agent",
        partial(
            route_after_agent,
            tool_service=tool_service,
        ),
        {
            "approval": "approval",
            "tools": "tools",
            "end": END,
        },
    )

    # 审批通过后才允许进入 ToolNode。
    # 审批拒绝后返回 Agent，让模型根据拒绝原因继续回答。
    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {
            "tools": "tools",
            "agent": "agent",
        },
    )

    # 工具结果以 ToolMessage 写回 State。
    # Agent 观察结果后，可以生成最终回答，
    # 也可以继续发起下一次工具调用。
    builder.add_edge("tools", "agent")

    # 子图不创建独立 checkpointer。
    # 它会继承主图的 checkpoint，因此内部 interrupt
    # 可以通过主图的 thread_id 恢复。
    return builder.compile()
