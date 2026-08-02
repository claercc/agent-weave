from pydantic import BaseModel, Field

from app.domain.routing import Route


class RouteDecision(BaseModel):
    """路由模型生成的结构化决策"""

    route: Route = Field(description="选择的工作流路由")
    reason: str = Field(
        description="选择该路由的原因",
        min_length=1,
        max_length=100,
    )
