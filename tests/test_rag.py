from unittest.mock import Mock

from app.services.rag_service import RAGService


def test_retrieve_context_passes_collection_name_to_retriever() -> None:
    rag_service = object.__new__(RAGService)

    retriever = Mock()
    retriever.get_relevant_context.return_value = "retrieved context"
    rag_service._retriever = retriever

    context = rag_service.retrieve_context(
        query="How do I deploy the service?",
        collection_name="engineering",
        top_k=2,
    )

    assert context == "retrieved context"

    retriever.get_relevant_context.assert_called_once_with(
        query="How do I deploy the service?",
        collection_name="engineering",
        top_k=2,
    )
def test_query_uses_requested_top_k_for_retrieval() -> None:
    rag_service = object.__new__(RAGService)

    retriever = Mock()
    retriever.get_relevant_context.return_value = "retrieved context"
    rag_service._retriever = retriever

    rag_service.generate_with_context = Mock(return_value="generated answer")

    response = rag_service.query(
        query="How do I deploy the service?",
        collection_name="engineering",
        top_k=6,
    )

    assert response.answer == "generated answer"
    assert response.context == "retrieved context"

    retriever.get_relevant_context.assert_called_once_with(
        query="How do I deploy the service?",
        collection_name="engineering",
        top_k=6,
    )