from typing import List
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

class ChunkService:
    """文本分块服务"""
    def __init__(self,chunk_size: int = 500,chunk_overlap: int = 50):
        """
        params:
        chunk_size: 每个分块的字符数
        chunk_overlap: 每个分块的重叠字符数
        """
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def split_text(self,text: str) -> List[str]:
        """将文本分块"""
        return self._text_splitter.split_text(text)
    
    def split_texts(self,texts: List[str]) -> List[str]:
        """将文本列表分块"""
        all_chunks = []
        for text in texts:
            # split_text 返回 List[str]，用 extend 将其展平追加
            all_chunks.extend(self._text_splitter.split_text(text))
        return all_chunks
    
    def split_documents(self,documents: List[Document]) -> List[Document]:
        """将文档列表分块"""
        all_chunks: List[Document] = []
        for document in documents:
            document_chunks = self._text_splitter.split_documents([document])
            for chunk_index, chunk in enumerate(document_chunks):
                chunk.metadata["chunk_index"] = chunk_index
            all_chunks.extend(document_chunks)
        return all_chunks
