from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """基础工具类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """工具参数"""
        pass

    @property
    def requires_approval(self) -> bool:
        """工具执行前是否需要人工审批。"""
        return False
    
    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """执行工具"""
        raise NotImplementedError
