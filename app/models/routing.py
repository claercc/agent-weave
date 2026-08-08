from pydantic import BaseModel, Field

from app.domain.routing import (
    RequestIntent,
    Route,
)


class RouteDecision(BaseModel):
    """旧版路由结果，后续完成迁移后删除。"""

    route: Route = Field(
        description="选择的工作流路由"
    )
    reason: str = Field(
        description="选择该路由的原因",
        min_length=1,
        max_length=100,
    )


class RequestAnalysis(BaseModel):
    """模型对用户请求生成的结构化分析结果。"""

    intent: RequestIntent = Field(
        description=(
            "用户意图：普通对话、知识库查询、"
            "信息工具查询或有副作用的业务操作"
        )
    )

    route: Route = Field(
        description=(
            "根据意图选择 chat、rag 或 agent 工作流"
        )
    )

    needs_knowledge: bool = Field(
        description="是否需要查询私有知识库"
    )

    needs_tools: bool = Field(
        description="是否需要调用外部工具"
    )

    requires_clarification: bool = Field(
        description=(
            "是否缺少完成任务所必需的信息，"
            "需要先向用户提出澄清问题"
        )
    )

    rewritten_query: str | None = Field(
        default=None,
        description=(
            "面向知识库检索的独立查询语句；"
            "仅知识库查询时使用"
        ),
        max_length=500,
    )

    clarification_question: str | None = Field(
        default=None,
        description=(
            "需要用户补充信息时提出的简短问题"
        ),
        max_length=300,
    )

    reason: str = Field(
        description="本次意图和路由判断的简短原因",
        min_length=1,
        max_length=200,
    )