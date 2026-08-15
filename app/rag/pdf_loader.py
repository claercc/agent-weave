from io import BytesIO
from pathlib import Path
from threading import Lock

import pymupdf
from langchain_core.documents import Document
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.rag.ocr import OCRService, get_ocr_service


class PdfDocumentLoader:
    """PDF文档加载器"""

    def __init__(
        self,
        ocr_service: OCRService | None = None,
        ocr_dpi: int = 200,
        max_pages: int = 100,
    ):
        self._ocr_service = ocr_service
        self._ocr_lock = Lock()
        self._ocr_dpi = ocr_dpi
        self._max_pages = max_pages

    def load(self, content: bytes, filename: str) -> list[Document]:
        """加载PDF文档"""
        if not content:
            raise ValueError("PDF内容不能为空")

        safe_filename = Path(filename).name
        if not safe_filename:
            raise ValueError("文件名不能为空")

        try:
            reader = PdfReader(BytesIO(content))
        except (PdfReadError, ValueError, OSError) as e:
            raise ValueError(f"无法读取PDF文件: {e}") from e

        if len(reader.pages) > self._max_pages:
            raise ValueError(f"PDF 页数不能超过 {self._max_pages} 页")

        documents: list[Document] = []
        render_document: pymupdf.Document | None = None

        try:
            for page_index, page in enumerate(reader.pages):
                page_number = page_index + 1

                text = self._extract_page_text(page)

                extraction_method = "text"
                if not text:
                    if render_document is None:
                        render_document = pymupdf.open(  # type: ignore[no-untyped-call]
                            stream=content,
                            filetype="pdf",
                        )
                    text = self._extract_page_with_ocr(
                        pdf_document=render_document, page_index=page_index
                    )

                    extraction_method = "ocr"
                if not text:
                    continue

                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": safe_filename,
                            "page": page_number,
                            "content_type": "application/pdf",
                            "extraction_method": (extraction_method),
                        },
                    )
                )
        finally:
            if render_document is not None:
                render_document.close()  # type: ignore[no-untyped-call]

        if not documents:
            raise ValueError("PDF 中没有识别到可用文字")
        return documents

    @staticmethod
    def _extract_page_text(page: object) -> str:
        """优先提取页面文本"""

        try:
            extract_text = getattr(page, "extract_text")
            return (extract_text() or "").strip()
        except Exception:
            return ""

    def _extract_page_with_ocr(
        self, pdf_document: pymupdf.Document, page_index: int
    ) -> str:
        """将指定 PDF 页面渲染为图片后进行 OCR。"""
        try:
            page = pdf_document.load_page(page_index)  # type: ignore[no-untyped-call]

            pixmap = page.get_pixmap(
                dpi=self._ocr_dpi,
                colorspace=pymupdf.csRGB,
                alpha=False,
            )

            image_content = pixmap.tobytes("png")

            # RapidOCR/ONNX 延迟到真正遇到图片页时初始化。
            # 同一个 loader 的 OCR 推理串行执行，避免并发初始化
            # 或共享 ONNX session 时发生资源竞争。
            with self._ocr_lock:
                if self._ocr_service is None:
                    self._ocr_service = get_ocr_service()

                return self._ocr_service.extract_text(image_content).strip()
        except Exception as exc:
            raise ValueError(f"第 {page_index + 1} 页 OCR 识别失败: {exc}") from exc
