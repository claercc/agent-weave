from functools import lru_cache
from io import BytesIO
from typing import Protocol

import numpy as np
from PIL import Image
from rapidocr import RapidOCR


class OCRService(Protocol):
    """OCR 服务"""

    def extract_text(self, image_content: bytes) -> str:
        """从图像中提取文本"""
        ...


class RapidOCRService:
    """使用 RapidOCR 实现本地文字识别。"""

    def __init__(self):
        self._engine = RapidOCR()

    def extract_text(self, image_content: bytes) -> str:
        """从图像中提取文本"""
        if not image_content:
            return ""
        with Image.open(BytesIO(image_content)) as image:
            rab_image = image.convert("RGB")
            image_array = np.array(rab_image)

        results = self._engine(image_array)
        texts = results.txts or ()
        return "\n".join(text.strip() for text in texts if text and text.strip())


@lru_cache(maxsize=1)
def get_ocr_service() -> OCRService:
    return RapidOCRService()
