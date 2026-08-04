from typing import Any

import requests

from app.tools.base import BaseTool
from app.core.config import get_settings


class WeatherTool(BaseTool):
    """天气工具"""

    # def __init__(self):
    #     self.name = "weather"
    #     self.description = "获取天气信息"
    #     self.parameters  = {
    #         "location": {
    #             "type": "string",
    #             "description": "天气查询地点"
    #         }
    #     }
    #     self.run = self._run
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
                    "description": "城市名称，如：Beijing, Shanghai",
                }
            },
            "required": ["city"],
        }

    def run(self, **kwargs: Any) -> str:
        """获取指定城市的天气信息"""

        city = kwargs.get("city")

        if not isinstance(city, str) or not city.strip():
            raise ValueError("城市名称不能为空")

        city = city.strip()
        try:

            settings = get_settings()
            api_key = settings.require_openweather_api_key().get_secret_value()
            url = (
                "http://api.openweathermap.org/data/2.5/weather"
                f"?q={city}&appid={api_key}&units=metric&lang=zh_cn"
            )
            response = requests.get(url)
            data = response.json()
            if response.status_code == 200:
                return (
                    f"{city} 的天气：{data['weather'][0]['description']}，"
                    f"温度：{data['main']['temp']}°C"
                )
            else:
                return f"天气查询失败，状态码：{response.status_code}"
        except Exception as e:
            return f"天气查询失败，错误信息：{str(e)}"
