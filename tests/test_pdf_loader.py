from unittest.mock import Mock, patch

import pymupdf
import pytest

from app.rag.pdf_loader import PdfDocumentLoader


@patch("app.rag.pdf_loader.PdfReader")
def test_load_extracts_text_and_page_metadata(
    mock_pdf_reader: Mock,
) -> None:
    first_page = Mock()
    first_page.extract_text.return_value = "东京第一天游览浅草寺。"

    second_page = Mock()
    second_page.extract_text.return_value = "东京第二天游览镰仓。"

    mock_pdf_reader.return_value.pages = [
        first_page,
        second_page,
    ]

    ocr_service = Mock()
    loader = PdfDocumentLoader(ocr_service=ocr_service)

    documents = loader.load(
        content=b"fake-pdf-content",
        filename="tokyo-guide.pdf",
    )

    assert len(documents) == 2

    assert documents[0].page_content == ("东京第一天游览浅草寺。")
    assert documents[0].metadata == {
        "source": "tokyo-guide.pdf",
        "page": 1,
        "content_type": "application/pdf",
        "extraction_method": "text",
    }

    assert documents[1].metadata["page"] == 2
    assert documents[1].metadata["extraction_method"] == "text"

    ocr_service.extract_text.assert_not_called()


@patch("app.rag.pdf_loader.pymupdf.open")
@patch("app.rag.pdf_loader.PdfReader")
def test_load_uses_ocr_for_image_page(
    mock_pdf_reader: Mock,
    mock_pymupdf_open: Mock,
) -> None:
    pdf_page = Mock()
    pdf_page.extract_text.return_value = None
    mock_pdf_reader.return_value.pages = [pdf_page]

    render_document = Mock()
    render_page = Mock()
    pixmap = Mock()

    pixmap.tobytes.return_value = b"rendered-page"
    render_page.get_pixmap.return_value = pixmap
    render_document.load_page.return_value = render_page
    mock_pymupdf_open.return_value = render_document

    ocr_service = Mock()
    ocr_service.extract_text.return_value = "洛阳龙门石窟旅游攻略"

    loader = PdfDocumentLoader(
        ocr_service=ocr_service,
        ocr_dpi=200,
    )

    documents = loader.load(
        content=b"fake-pdf-content",
        filename="luoyang-guide.pdf",
    )

    assert len(documents) == 1
    assert documents[0].page_content == ("洛阳龙门石窟旅游攻略")
    assert documents[0].metadata == {
        "source": "luoyang-guide.pdf",
        "page": 1,
        "content_type": "application/pdf",
        "extraction_method": "ocr",
    }

    mock_pymupdf_open.assert_called_once_with(
        stream=b"fake-pdf-content",
        filetype="pdf",
    )
    render_document.load_page.assert_called_once_with(0)
    render_page.get_pixmap.assert_called_once_with(
        dpi=200,
        colorspace=pymupdf.csRGB,
        alpha=False,
    )
    pixmap.tobytes.assert_called_once_with("png")
    ocr_service.extract_text.assert_called_once_with(b"rendered-page")
    render_document.close.assert_called_once_with()


@patch("app.rag.pdf_loader.pymupdf.open")
@patch("app.rag.pdf_loader.PdfReader")
def test_load_rejects_pdf_when_ocr_returns_empty(
    mock_pdf_reader: Mock,
    mock_pymupdf_open: Mock,
) -> None:
    pdf_page = Mock()
    pdf_page.extract_text.return_value = None
    mock_pdf_reader.return_value.pages = [pdf_page]

    render_document = Mock()
    render_page = Mock()
    pixmap = Mock()

    pixmap.tobytes.return_value = b"rendered-page"
    render_page.get_pixmap.return_value = pixmap
    render_document.load_page.return_value = render_page
    mock_pymupdf_open.return_value = render_document

    ocr_service = Mock()
    ocr_service.extract_text.return_value = ""

    loader = PdfDocumentLoader(ocr_service=ocr_service)

    with pytest.raises(
        ValueError,
        match="没有识别到可用文字",
    ):
        loader.load(
            content=b"fake-pdf-content",
            filename="empty-guide.pdf",
        )

    render_document.close.assert_called_once_with()


def test_load_rejects_empty_file() -> None:
    loader = PdfDocumentLoader(ocr_service=Mock())

    with pytest.raises(ValueError):
        loader.load(
            content=b"",
            filename="empty.pdf",
        )
