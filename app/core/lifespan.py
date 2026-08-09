from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.container import (
    build_agent_service,
)
from app.services.tool_service import init_tools


@asynccontextmanager
async def lifespan(
    application: FastAPI,
) -> AsyncIterator[None]:
    """管理应用级服务的启动和关闭。

    启动阶段：
        1. 注册应用工具；
        2. 构建并编译 Agent Workflow；
        3. 将 AgentService 保存到应用状态。

    请求阶段：
        所有 Agent API 共享同一个 AgentService。

    关闭阶段：
        释放应用状态中的服务引用。
    """

    settings = get_settings()

    # 必须先注册工具，再编译 Tool Agent 子图。
    # 否则子图编译时获取不到工具定义。
    init_tools()

    # Workflow 只在应用启动时编译一次。
    application.state.agent_service = (
        build_agent_service(settings)
    )

    yield

    # 当前服务没有必须手动关闭的网络连接。
    # 清除引用可以明确表示应用生命周期已经结束。
    application.state.agent_service = None