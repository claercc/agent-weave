from typing import Any
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings
from app.tools.base import BaseTool


class WebSearchTool(BaseTool):
    """通过 Tavily Search API 查询互联网信息。"""

    API_URL = "https://api.tavily.com/search"
    REQUEST_TIMEOUT_SECONDS = 10.0
    MAX_RESULTS = 5

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "搜索互联网中的最新公开信息。"
            "适用于新闻、实时事件、最新版本、政策变化、"
            "近期发布信息，以及无法仅依靠已有知识回答的问题。"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": ("完整、明确、能够独立执行的搜索关键词或问题"),
                },
            },
            "required": ["query"],
        }

    def run(self, **kwargs: Any) -> dict[str, Any]:
        """同步执行搜索，兼容传统工具调用入口。"""

        query = self._validate_query(kwargs.get("query"))

        with httpx.Client(
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        ) as client:
            response = client.post(
                self.API_URL,
                headers=self._build_headers(),
                json=self._build_request_body(query),
            )

        response.raise_for_status()

        return self._parse_response(
            query=query,
            response=response,
        )

    async def arun(self, **kwargs: Any) -> dict[str, Any]:
        """异步执行搜索，供 LangGraph Tool Agent 使用。"""

        query = self._validate_query(kwargs.get("query"))

        async with httpx.AsyncClient(
            timeout=self.REQUEST_TIMEOUT_SECONDS,
        ) as client:
            response = await client.post(
                self.API_URL,
                headers=self._build_headers(),
                json=self._build_request_body(query),
            )

        response.raise_for_status()

        return self._parse_response(
            query=query,
            response=response,
        )

    @staticmethod
    def _validate_query(value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("搜索内容不能为空")

        query = value.strip()

        if not query:
            raise ValueError("搜索内容不能为空")

        if len(query) > 500:
            raise ValueError("搜索内容不能超过 500 个字符")

        return query

    @staticmethod
    def _build_headers() -> dict[str, str]:
        api_key = get_settings().require_tavily_api_key().get_secret_value()

        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    @classmethod
    def _build_request_body(
        cls,
        query: str,
    ) -> dict[str, Any]:
        return {
            "query": query,
            "topic": "general",
            "search_depth": "basic",
            "max_results": cls.MAX_RESULTS,
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
        }

    @classmethod
    def _parse_response(
        cls,
        query: str,
        response: httpx.Response,
    ) -> dict[str, Any]:
        payload = response.json()

        if not isinstance(payload, dict):
            raise ValueError("Tavily 返回了无效的搜索结果")

        raw_results = payload.get("results", [])

        if not isinstance(raw_results, list):
            raw_results = []

        items: list[dict[str, Any]] = []

        for raw_item in raw_results[: cls.MAX_RESULTS]:
            if not isinstance(raw_item, dict):
                continue

            url = raw_item.get("url")

            if not isinstance(url, str):
                continue

            url = url.strip()
            parsed_url = urlparse(url)

            if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
                continue

            title = raw_item.get("title")
            snippet = raw_item.get("content")
            score_value = raw_item.get("score")
            published_at = raw_item.get("published_date")

            if not isinstance(title, str) or not title.strip():
                title = url

            if not isinstance(snippet, str):
                snippet = ""

            if isinstance(score_value, (int, float)) and not isinstance(
                score_value, bool
            ):
                score: float | None = max(
                    0.0,
                    min(1.0, float(score_value)),
                )
            else:
                score = None

            if not isinstance(published_at, str):
                published_at = None

            items.append(
                {
                    "title": title.strip(),
                    "url": url,
                    "snippet": snippet.strip(),
                    "score": score,
                    "published_at": published_at,
                }
            )

        return {
            "query": query,
            "items": items,
        }
