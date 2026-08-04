from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.rag import get_rag_service, router


def create_test_client(
    rag_service: Mock,
) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")

    app.dependency_overrides[get_rag_service] = lambda: rag_service

    return TestClient(app)


def test_pdf_ingestion_accepts_multipart_upload() -> None:
    rag_service = Mock()
    rag_service.ingest_pdf.return_value = 3

    client = create_test_client(rag_service)

    response = client.post(
        "/api/rag/ingest/pdf",
        files={
            "file": (
                "guide.pdf",
                b"fake-pdf-content",
                "application/pdf",
            )
        },
        data={
            "collection_name": "guides",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "PDF 导入成功",
        "filename": "guide.pdf",
        "collection_name": "guides",
        "chunk_count": 3,
    }

    rag_service.ingest_pdf.assert_called_once_with(
        content=b"fake-pdf-content",
        filename="guide.pdf",
        collection_name="guides",
    )


def test_pdf_ingestion_rejects_non_pdf_file() -> None:
    rag_service = Mock()
    client = create_test_client(rag_service)

    response = client.post(
        "/api/rag/ingest/pdf",
        files={
            "file": (
                "notes.txt",
                b"plain-text",
                "text/plain",
            )
        },
        data={
            "collection_name": "guides",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "文件必须是 PDF 格式"}

    rag_service.ingest_pdf.assert_not_called()


def test_pdf_ingestion_maps_invalid_pdf_to_400() -> None:
    rag_service = Mock()
    rag_service.ingest_pdf.side_effect = ValueError("Unable to read PDF")

    client = create_test_client(rag_service)

    response = client.post(
        "/api/rag/ingest/pdf",
        files={
            "file": (
                "broken.pdf",
                b"broken-content",
                "application/pdf",
            )
        },
        data={
            "collection_name": "guides",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Unable to read PDF"}
