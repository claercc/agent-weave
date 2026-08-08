from typing import Literal, TypeAlias

# 路由目标
Route: TypeAlias = Literal[
    "chat",
    "rag",
    "agent",
]

# 路由模式
RoutingMode: TypeAlias = Literal[
    "auto",
    "chat",
    "rag",
    "agent",
]

# 请求意图
RequestIntent: TypeAlias = Literal[
    # 普通对话、解释、问候
    "conversation",
    # 查询私有知识库
    "knowledge_query",
    # 天气、时间、计算等只读工具
    "information_tool",
    # 创建工单等会产生副作用的操作
    "action",
]