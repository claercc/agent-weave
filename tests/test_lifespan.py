from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.lifespan import lifespan
from pytest import MonkeyPatch


def test_lifespan_initializes_tools(monkeypatch: MonkeyPatch) -> None:
    initialized = False
    settings = object()
    agent_service = object()
    rag_service = object()

    def fake_init_tools() -> None:
        nonlocal initialized
        initialized = True

    def fake_build_application_services(actual_settings: object) -> object:
        assert actual_settings is settings
        return SimpleNamespace(
            agent_service=agent_service,
            rag_service=rag_service,
        )

    monkeypatch.setattr(
        "app.core.lifespan.init_tools",
        fake_init_tools,
    )
    monkeypatch.setattr(
        "app.core.lifespan.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "app.core.lifespan.build_application_services",
        fake_build_application_services,
    )

    test_app = FastAPI(lifespan=lifespan)

    with TestClient(test_app):
        assert initialized is True
        assert test_app.state.agent_service is agent_service
        assert test_app.state.rag_service is rag_service

    assert test_app.state.agent_service is None
    assert test_app.state.rag_service is None
