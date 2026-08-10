import pytest


@pytest.fixture
def anyio_backend() -> str:
    """测试统一使用项目实际运行的 asyncio 后端。"""

    return "asyncio"
