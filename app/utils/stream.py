import json
from collections.abc import Mapping
from typing import Any


def encode_sse(event: str, data: Mapping[str, Any]) -> str:
    """将事件和数据编码为标准 SSE 消息。"""

    payload = json.dumps(
        data,
        # 中文直接显示，不转换成 \u4f60\u597d
        ensure_ascii=False,
        # 遇到不能直接序列化的对象时转成字符串，避免流中断
        default=str,
    )
    return f"event: {event}\ndata: {payload}\n\n"
