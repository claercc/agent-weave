from pydantic import BaseModel
from typing import Any, Optional, Self


class ToolCallResult(BaseModel):
    """工具调用结果"""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    tool_name: str

    @classmethod
    def success_result(cls, tool_name: str, data: Any) -> Self:
        """创建成功结果"""
        return cls(success=True, data=data, tool_name=tool_name)

    @classmethod
    def error_result(cls, tool_name: str, error: str) -> Self:
        """创建失败结果"""
        return cls(success=False, error=error, tool_name=tool_name)
