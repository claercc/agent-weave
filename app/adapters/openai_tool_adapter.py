# app/adapters/openai_tool_adapter.py
from typing import Any, Dict, List

from app.tools.base import BaseTool


class OpenAIToolAdapter:
    """OpenAI 工具适配器"""

    @staticmethod
    def convert(tools: List[BaseTool]) -> List[Dict[str, Any]]:
        """将 OpenAI 工具调用转换为工具调用格式"""
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]
        return openai_tools
