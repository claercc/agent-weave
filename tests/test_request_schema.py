import pytest
from pydantic import ValidationError

from app.schemas.request import AgentChatRequest, RAGQueryRequest


def test_rag_mode_requires_collection_name():
    with pytest.raises(ValidationError):
        AgentChatRequest(
            session_id="session-001",
            message="Which framework is used?",
            mode="rag",
            collection_name=None,
        )


@pytest.mark.parametrize("top_k", [0, 21])
def test_rag_query_rejects_out_of_range_top_k(top_k: int) -> None:
    with pytest.raises(ValidationError):
        RAGQueryRequest(
            query="Which framework is used?",
            collection_name="engineering",
            top_k=top_k,
        )
