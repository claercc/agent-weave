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


def test_unicode_collection_name_uses_safe_storage_name() -> None:
    vector_db = object.__new__(VectorDBService)
    vector_db._client = Mock()

    collection = Mock()
    collection.metadata = {
        "embedding_model": "test-model",
        "display_name": "河南3",
    }
    vector_db._client.get_or_create_collection.return_value = collection

    vector_db.get_or_create_collection(
        collection_name="河南3",
        embedding_model="test-model",
    )

    call_arguments = vector_db._client.get_or_create_collection.call_args.kwargs
    storage_name = call_arguments["name"]

    assert storage_name.startswith("kb-")
    assert len(storage_name) == 67
    assert storage_name.isascii()
    assert call_arguments["metadata"]["display_name"] == "河南3"


def test_short_collection_name_uses_safe_storage_name() -> None:
    assert VectorDBService._to_storage_name("ab").startswith("kb-")


def test_list_collections_returns_display_names() -> None:
    vector_db = object.__new__(VectorDBService)
    vector_db._client = Mock()

    unicode_collection = Mock()
    unicode_collection.name = "kb-internal-name"
    unicode_collection.metadata = {
        "embedding_model": "test-model",
        "display_name": "河南3",
    }

    legacy_collection = Mock()
    legacy_collection.name = "english-docs"
    legacy_collection.metadata = {
        "embedding_model": "test-model",
    }

    vector_db._client.list_collections.return_value = [
        unicode_collection,
        legacy_collection,
    ]

    assert vector_db.list_collections() == [
        "河南3",
        "english-docs",
    ]
