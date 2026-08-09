from typing import Any

import httpx

from app.core.config import get_settings
from app.tools.base import BaseTool


class WeatherTool(BaseTool):
    """通过 OpenWeather API 查询城市天气。"""

    API_URL = (
        "https://api.openweathermap.org/"
        "data/2.5/weather"
    )

    REQUEST_TIMEOUT_SECONDS = 10.0

    @property
    def name(self) -> str:
        return "get_weather"

    @property
    def description(self) -> str:
        return "获取指定城市的天气信息"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": (
                        "城市名称，如：Beijing、"
                        "Shanghai、Singapore"
                    ),
                }
            },
            "required": ["city"],
        }

    def run(self, **kwargs: Any) -> str:
        """同步查询天气，供旧版同步接口使用。"""

        city = self._validate_city(
            kwargs.get("city")
        )

        try:
            with httpx.Client(
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            ) as client:
                response = client.get(
                    self.API_URL,
                    params=self._build_params(city),
                )

            return self._format_response(
                city,
                response,
            )
        except Exception as exc:
            return (
                "天气查询失败，错误信息："
                f"{exc}"
            )

    async def arun(self, **kwargs: Any) -> str:
        """异步查询天气，供 Tool Agent 工作流使用。"""

        city = self._validate_city(
            kwargs.get("city")
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            ) as client:
                response = await client.get(
                    self.API_URL,
                    params=self._build_params(city),
                )

            return self._format_response(
                city,
                response,
            )
        except Exception as exc:
            return (
                "天气查询失败，错误信息："
                f"{exc}"
            )

    @staticmethod
    def _validate_city(value: Any) -> str:
        """校验并规范化城市名称。"""

        if not isinstance(value, str):
            raise ValueError(
                "城市名称不能为空"
            )

        city = value.strip()

        if not city:
            raise ValueError(
                "城市名称不能为空"
            )

        return city

    @staticmethod
    def _build_params(
        city: str,
    ) -> dict[str, str]:
        """构造 OpenWeather API 查询参数。"""

        settings = get_settings()
        api_key = (
            settings
            .require_openweather_api_key()
            .get_secret_value()
        )

        return {
            "q": city,
            "appid": api_key,
            "units": "metric",
            "lang": "zh_cn",
        }

    @staticmethod
    def _format_response(
        city: str,
        response: httpx.Response,
    ) -> str:
        """将天气 API 响应转换为 Agent 可读文本。"""

        if response.status_code != 200:
            return (
                "天气查询失败，状态码："
                f"{response.status_code}"
            )

        data = response.json()

        description = data["weather"][0][
            "description"
        ]

        temperature = data["main"]["temp"]

        return (
            f"{city} 的天气：{description}，"
            f"温度：{temperature}°C"
        )