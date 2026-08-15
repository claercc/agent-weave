from typing import Any
from app.models.output_model import ToolCallResult
from app.tools.base import BaseTool
from app.tools.registry import ToolRegistry, InMemoryToolRegistry
import json


class ToolService:
    """工具服务"""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._tool_registry = tool_registry

    def call_tool(self, tool_name: str, **kwargs: Any) -> ToolCallResult:
        """调用工具"""
        try:
            tool = self._tool_registry.get(tool_name)
            if not tool:
                return ToolCallResult.error_result(
                    tool_name, f"工具 {tool_name} 不存在"
                )
            required_params = self._get_required_params(tool)
            missing_params = [param for param in required_params if param not in kwargs]
            if missing_params:
                return ToolCallResult.error_result(
                    tool_name, f"缺少参数：{', '.join(missing_params)}"
                )
            result = tool.run(**kwargs)
            return ToolCallResult.success_result(tool_name, result)
        except Exception as e:
            return ToolCallResult.error_result(
                tool_name, f"工具 {tool_name} 执行失败，错误信息：{str(e)}"
            )

    async def call_tool_async(
        self,
        tool_name: str,
        **kwargs: Any,
    ) -> ToolCallResult:
        """异步调用工具。

        原生异步工具会直接执行异步 I/O；
        同步工具由 BaseTool.arun() 放入工作线程执行。
        """

        try:
            tool = self._tool_registry.get(tool_name)

            if not tool:
                return ToolCallResult.error_result(
                    tool_name,
                    f"工具 {tool_name} 不存在",
                )

            required_params = self._get_required_params(tool)

            missing_params = [param for param in required_params if param not in kwargs]

            if missing_params:
                return ToolCallResult.error_result(
                    tool_name,
                    ("缺少参数：" f"{', '.join(missing_params)}"),
                )

            result = await tool.arun(**kwargs)

            return ToolCallResult.success_result(
                tool_name,
                result,
            )
        except Exception as exc:
            return ToolCallResult.error_result(
                tool_name,
                (f"工具 {tool_name} 执行失败，" f"错误信息：{exc}"),
            )

    def _get_required_params(self, tool: BaseTool) -> list[str]:
        """获取工具必填参数"""
        if tool.parameters and "required" not in tool.parameters:
            return []
        return [param for param in tool.parameters["required"]]

    def _tool_to_dict(self, tool: BaseTool) -> dict[str, Any]:
        """将工具转换为字典"""
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }

    def list_tools(self) -> list[dict[str, Any]]:
        """列出所有工具"""
        return [self._tool_to_dict(tool) for tool in self._tool_registry.list_tools()]

    def requires_approval(self, tool_name: str) -> bool:
        """检查工具是否需要人工审批"""
        tool = self._tool_registry.get(tool_name)
        if not tool:
            return False
        return tool.requires_approval

    def execute_tool(self, tool_name: str, **kwargs: Any) -> str:
        """执行工具"""
        try:
            arguments = kwargs.get("arguments", "")
            params = json.loads(arguments) if arguments else {}
            result = self.call_tool(tool_name, **params)
            if not result.success:
                raise ValueError(f"工具 {tool_name} 执行失败，错误信息：{result.error}")
            return self.serialize_result(result.data)
        except json.JSONDecodeError as e:
            raise ValueError(f"工具 {tool_name} 参数解析失败，错误信息：{str(e)}")
        except Exception as e:
            raise ValueError(f"工具 {tool_name} 执行失败，错误信息：{str(e)}")

    @staticmethod
    def serialize_result(data: Any) -> str:
        if data is None:
            return ""

        if isinstance(data, str):
            return data

        return json.dumps(
            data,
            ensure_ascii=False,
            default=str,
        )


_global_registry = InMemoryToolRegistry()


def get_tool_service() -> ToolService:
    """获取工具服务"""
    return ToolService(_global_registry)


def register_tool(tool: BaseTool) -> None:
    """注册工具"""
    _global_registry.register(tool)


def unregister_tool(tool_name: str) -> None:
    """注销工具"""
    _global_registry.unregister(tool_name)


def init_tools() -> None:
    """初始化工具"""
    from app.tools.weather import WeatherTool
    from app.tools.calculator import CalculatorTool
    from app.tools.support_ticket import CreateSupportTicketTool
    from app.tools.time import TimeTool
    from app.tools.web_search import WebSearchTool

    register_tool(WeatherTool())
    register_tool(CalculatorTool())
    register_tool(TimeTool())
    register_tool(CreateSupportTicketTool())
    register_tool(WebSearchTool())
