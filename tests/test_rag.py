from unittest.mock import Mock

from app.services.rag_service import RAGService
from langchain_core.documents import Document


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

def test_ingest_pdf_parses_chunks_and_stores_documents() -> None:
    rag_service = object.__new__(RAGService)

    rag_service._pdf_loader = Mock()
    rag_service._chunk_service = Mock()
    rag_service._vector_db_service = Mock()

    source_document = Document(
        page_content="Tokyo travel guide.",
        metadata={
            "source": "tokyo.pdf",
            "page": 2,
            "content_type": "application/pdf",
        },
    )
    chunk = Document(
        page_content="Visit Sensoji early.",
        metadata={
            "source": "tokyo.pdf",
            "page": 2,
            "content_type": "application/pdf",
            "chunk_index": 0,
        },
    )

    rag_service._pdf_loader.load.return_value = [
        source_document
    ]
    rag_service._chunk_service.split_documents.return_value = [
        chunk
    ]

    chunk_count = rag_service.ingest_pdf(
        content=b"fake-pdf",
        filename="tokyo.pdf",
        collection_name="travel-guides",
    )

    assert chunk_count == 1

    rag_service._pdf_loader.load.assert_called_once_with(
        content=b"fake-pdf",
        filename="tokyo.pdf",
    )
    rag_service._chunk_service.split_documents.assert_called_once_with(
        [source_document]
    )

    call_arguments = (
        rag_service
        ._vector_db_service
        .add_documents
        .call_args
        .kwargs
    )

    assert call_arguments["collection_name"] == (
        "travel-guides"
    )
    assert call_arguments["documents"] == [
        "Visit Sensoji early."
    ]
    assert call_arguments["metadatas"] == [
        chunk.metadata
    ]
    assert len(call_arguments["ids"]) == 1
    assert len(call_arguments["ids"][0]) == 64
