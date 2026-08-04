# 工具注册器
from abc import ABC, abstractmethod
from app.tools.base import BaseTool


class ToolRegistry(ABC):
    """工具注册器"""

    @abstractmethod
    def get(self, tool_name: str) -> BaseTool | None:
        """根据工具名称获取工具"""
        raise NotImplementedError()

    @abstractmethod
    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        raise NotImplementedError()

    @abstractmethod
    def unregister(self, tool_name: str) -> None:
        """注销工具"""
        raise NotImplementedError()

    @abstractmethod
    def list_tools(self) -> list[BaseTool]:
        """列出所有工具"""
        raise NotImplementedError()


class InMemoryToolRegistry(ToolRegistry):
    """内存中的工具注册器"""

    def __init__(self) -> None:
        self._store: dict[str, BaseTool] = {}

    def get(self, tool_name: str) -> BaseTool | None:
        """根据工具名称获取工具"""
        return self._store.get(tool_name)

    def register(self, tool: BaseTool) -> None:
        """注册工具"""
        self._store[tool.name] = tool

    def unregister(self, tool_name: str) -> None:
        """注销工具"""
        self._store.pop(tool_name, None)

    def list_tools(self) -> list[BaseTool]:
        """列出所有工具"""
        return list(self._store.values())
