from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from app.tools.base import BaseTool


class CreateSupportTicketTool(BaseTool):
    """创建支持工单的模拟业务工具。"""

    def __init__(self) -> None:
        self._tickets: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "create_support_ticket"

    @property
    def description(self) -> str:
        return (
            "创建一条需要后续人工处理的支持工单。"
            "只有当用户明确要求提交、创建或登记工单时才能调用。"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "简短明确的工单标题",
                },
                "description": {
                    "type": "string",
                    "description": "需要人工处理的问题详情",
                },
                "priority": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "description": "工单优先级",
                },
            },
            "required": [
                "title",
                "description",
                "priority",
            ],
        }

    @property
    def requires_approval(self) -> bool:
        """创建工单属于有副作用的操作，执行前必须审批。"""

        return True

    def run(self, **kwargs: Any) -> dict[str, Any]:
        """创建并保存一条模拟支持工单。"""

        title = kwargs.get("title")
        description = kwargs.get("description")
        priority = kwargs.get("priority")

        if not isinstance(title, str) or not title.strip():
            raise ValueError("工单标题不能为空")

        if not isinstance(description, str) or not description.strip():
            raise ValueError("工单描述不能为空")

        if priority not in {"low", "medium", "high"}:
            raise ValueError("工单优先级必须是 low、medium 或 high")

        ticket = {
            "ticket_id": f"TICKET-{uuid4().hex[:8].upper()}",
            "title": title.strip(),
            "description": description.strip(),
            "priority": priority,
            "status": "created",
            "created_at": datetime.now(UTC).isoformat(),
        }

        self._tickets.append(ticket)

        return ticket

    def list_tickets(self) -> list[dict[str, Any]]:
        """返回当前进程中创建的工单。"""

        return list(self._tickets)
