from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.lifespan import lifespan


def test_lifespan_initializes_tools(monkeypatch) -> None:
    initialized = False

    def fake_init_tools() -> None:
        nonlocal initialized
        initialized = True

    monkeypatch.setattr(
        "app.core.lifespan.init_tools",
        fake_init_tools,
    )

    test_app = FastAPI(lifespan=lifespan)

    with TestClient(test_app):
        assert initialized is True
