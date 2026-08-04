import pytest
from pydantic import ValidationError

from app.schemas.request import AgentChatRequest


def test_rag_mode_requires_collection_name():
    with pytest.raises(ValidationError):
        AgentChatRequest(
            session_id="session-001",
            message="Which framework is used?",
            mode="rag",
            collection_name=None,
        )
