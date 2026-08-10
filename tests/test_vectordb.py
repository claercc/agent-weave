from unittest.mock import Mock

import chromadb
import pytest

from app.core.exceptions import CollectionNotFoundError
from app.rag.vectordb import VectorDBService


def test_search_does_not_create_missing_collection() -> None:
    vector_db = object.__new__(VectorDBService)
    vector_db._client = Mock()
    vector_db._client.get_collection.side_effect = chromadb.errors.NotFoundError(
        "missing"
    )

    with pytest.raises(CollectionNotFoundError, match="missing_collection"):
        vector_db.search(
            collection_name="missing_collection",
            query_embedding=[0.1, 0.2],
            embedding_model="test-model",
        )

    vector_db._client.create_collection.assert_not_called()
    vector_db._client.get_or_create_collection.assert_not_called()
