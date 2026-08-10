from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.lifespan import lifespan


def test_lifespan_initializes_tools(monkeypatch) -> None:
    initialized = False
    settings = Settings(openai_api_key="test-key")
    agent_service = object()

    def fake_init_tools() -> None:
        nonlocal initialized
        initialized = True

    def fake_build_agent_service(actual_settings: Settings) -> object:
        assert actual_settings is settings
        return agent_service

    monkeypatch.setattr(
        "app.core.lifespan.init_tools",
        fake_init_tools,
    )
    monkeypatch.setattr(
        "app.core.lifespan.get_settings",
        lambda: settings,
    )
    monkeypatch.setattr(
        "app.core.lifespan.build_agent_service",
        fake_build_agent_service,
    )

    test_app = FastAPI(lifespan=lifespan)

    with TestClient(test_app):
        assert initialized is True
        assert test_app.state.agent_service is agent_service

    assert test_app.state.agent_service is None
