import asyncio
from abc import ABC, abstractmethod
from typing import Any


class BaseTool(ABC):
    """应用工具的统一抽象基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """返回工具名称。"""

        raise NotImplementedError

    @property
    @abstractmethod
    def description(self) -> str:
        """返回工具功能描述。"""

        raise NotImplementedError

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """返回符合 JSON Schema 的工具参数定义。"""

        raise NotImplementedError

    @property
    def requires_approval(self) -> bool:
        """工具执行前是否需要人工审批。"""

        return False

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """同步执行工具。

        该入口保留给旧接口和同步调用场景使用。
        """

        raise NotImplementedError

    async def arun(self, **kwargs: Any) -> Any:
        """异步执行工具。

        默认通过工作线程运行同步工具，使已有的计算器、
        工单工具不需要立刻重写成异步实现。

        网络 I/O 工具应当覆盖该方法，提供原生异步实现。
        """

        return await asyncio.to_thread(
            self.run,
            **kwargs,
        )