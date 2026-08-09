from functools import lru_cache
from typing import cast

import numpy as np
from sentence_transformers import SentenceTransformer

from app.core.config import Settings


@lru_cache(maxsize=4)
def _load_embedding_model(
    model_name: str,
) -> SentenceTransformer:
    """加载并缓存本地 Embedding 模型。

    FastAPI 每次创建 RAGService 时都可能创建新的
    EmbeddingService，但底层模型只应该加载一次。
    """

    return cast(SentenceTransformer, SentenceTransformer(model_name))


class EmbeddingService:
    """使用本地 SentenceTransformer 生成文本向量。"""

    def __init__(self, settings: Settings) -> None:
        self._model_name = settings.embedding_model

    @property
    def model_name(self) -> str:
        """返回当前使用的 Embedding 模型名称。"""

        return self._model_name

    def embed_query(self, text: str) -> list[float]:
        """为单条查询生成归一化向量。"""

        normalized_text = text.strip()

        if not normalized_text:
            raise ValueError("Embedding 查询文本不能为空")

        return self.embed_documents([normalized_text])[0]

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """批量生成文档向量。

        批量编码比循环调用模型更高效。
        normalize_embeddings=True 会把向量归一化，
        便于后续使用 cosine similarity。
        """

        if not texts:
            return []

        normalized_texts = [text.strip() for text in texts]

        # 检查是否有空字符串
        # 这会导致模型报错
        # 所以这里先过滤掉空字符串
        if any(not text for text in normalized_texts):
            raise ValueError("Embedding 文档文本不能为空")

        model = _load_embedding_model(self._model_name)

        encoded_vectors = model.encode(
            normalized_texts,
            # 模型不会一次性把所有文本塞进内存/显存，而是分成每 32 条文本一组（Batch）进行计算
            batch_size=32,
            # 隐藏进度条
            show_progress_bar=False,
            # 指定返回的向量数据类型为 NumPy 数组 (np.ndarray)
            convert_to_numpy=True,
            # 自动将输出的向量进行 L2 归一化（使每个向量的模长/长度等于 1）
            # 归一化后，“余弦相似度 (Cosine Similarity)” 的计算可以简化为更快的 “点积 (Dot Product)” 计算
            normalize_embeddings=True,
        )

        vectors = np.asarray(
            encoded_vectors,
            dtype=np.float32,
        )

        # cast强制类型转换为 Python 列表
        # 这是 FastAPI 所需的格式
        return cast(
            list[list[float]],
            vectors.tolist(),
        )
