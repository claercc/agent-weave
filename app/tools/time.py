from datetime import UTC, datetime, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.tools.base import BaseTool


class TimeTool(BaseTool):
    """查询指定 IANA 时区的当前时间。"""

    @property
    def name(self) -> str:
        return "get_current_time"

    @property
    def description(self) -> str:
        return "查询指定 IANA 时区的当前日期和时间，例如 Asia/Shanghai。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "timezone": {
                    "type": "string",
                    "description": "IANA 时区名称，默认 UTC",
                }
            },
        }

    def run(self, **kwargs: Any) -> dict[str, str]:
        timezone_name = kwargs.get("timezone", "UTC")

        if not isinstance(timezone_name, str) or not timezone_name.strip():
            raise ValueError("timezone 必须是非空字符串")

        normalized_timezone = timezone_name.strip()
        resolved_timezone: tzinfo

        if normalized_timezone.upper() == "UTC":
            resolved_timezone = UTC
        else:
            try:
                resolved_timezone = ZoneInfo(normalized_timezone)
            except ZoneInfoNotFoundError as exc:
                raise ValueError(f"未知时区：{normalized_timezone}") from exc

        current_time = datetime.now(resolved_timezone)

        return {
            "timezone": normalized_timezone,
            "datetime": current_time.isoformat(),
        }
