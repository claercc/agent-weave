from typing import Any
from app.tools.base import BaseTool

class CalculatorTool(BaseTool):
    """计算器工具"""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return "使用计算器进行计算"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "left": {
                    "type": "number",
                    "description": "左侧数字",
                },
                "right": {
                    "type": "number",
                    "description": "右侧数字",
                },
                "operator": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": (
                        "运算类型：add 加法、subtract 减法、"
                        "multiply 乘法、divide 除法"
                    ),
                },
            },
            "required": ["left", "right", "operator"],
        }

    def run(self, **kwargs: Any) -> float:
        """执行计算并返回结果。"""
        left = kwargs.get("left")
        right = kwargs.get("right")
        operator = kwargs.get("operator")

        if not self._is_number(left) or not self._is_number(right):
            raise ValueError("left 和 right 必须是数字")

        left_number = float(left)
        right_number = float(right)

        if operator == "add":
            return left_number + right_number

        if operator == "subtract":
            return left_number - right_number

        if operator == "multiply":
            return left_number * right_number

        if operator == "divide":
            if right_number == 0:
                raise ValueError("除数不能为 0")
            return left_number / right_number

        raise ValueError(f"不支持的运算类型：{operator}")

    @staticmethod
    def _is_number(value: Any) -> bool:
        """检查值是否为数字"""
        return (
                isinstance(value, (int, float))
                and not isinstance(value, bool) #bool 在 Python 中是 int 的子类
            )
