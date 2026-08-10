import pytest

from app.tools.calculator import CalculatorTool
from app.tools.time import TimeTool


def test_calculator_multiplies_two_numbers() -> None:
    tool = CalculatorTool()

    result = tool.run(
        left=125,
        right=48,
        operator="multiply",
    )

    assert result == 6000


def test_calculator_rejects_division_by_zero() -> None:
    tool = CalculatorTool()

    with pytest.raises(ValueError, match="除数不能为 0"):
        tool.run(
            left=10,
            right=0,
            operator="divide",
        )


def test_time_tool_returns_requested_timezone() -> None:
    result = TimeTool().run(timezone="UTC")

    assert result["timezone"] == "UTC"
    assert result["datetime"].endswith("+00:00")
