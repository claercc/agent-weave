from langchain_core.documents import Document

from app.rag.chunk import ChunkService


def test_split_documents_preserves_metadata() -> None:
    chunk_service = ChunkService(
        chunk_size=25,
        chunk_overlap=5,
    )
    source_document = Document(
        page_content=(
            "Visit Sensoji early. " "Take the train to Ueno. " "Eat sushi at noon."
        ),
        metadata={
            "source": "tokyo-guide.pdf",
            "page": 3,
            "content_type": "application/pdf",
        },
    )

    chunks = chunk_service.split_documents([source_document])

    assert len(chunks) > 1

    for chunk in chunks:
        assert chunk.metadata["source"] == ("tokyo-guide.pdf")
        assert chunk.metadata["page"] == 3
        assert chunk.metadata["content_type"] == ("application/pdf")

    assert [chunk.metadata["chunk_index"] for chunk in chunks] == list(
        range(len(chunks))
    )
