import pytest

from app.core.config import Settings


def test_settings_can_load_without_api_keys() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key=None,
        openweather_api_key=None,
    )

    assert settings.openai_api_key is None
    assert settings.openweather_api_key is None


def test_require_openai_api_key_returns_configured_secret() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key="test-model-key",
    )

    api_key = settings.require_openai_api_key()

    assert api_key.get_secret_value() == "test-model-key"
    assert str(api_key) == "**********"


def test_require_openai_api_key_raises_when_missing() -> None:
    settings = Settings(
        _env_file=None,
        openai_api_key=None,
    )

    with pytest.raises(
        RuntimeError,
        match="OPENAI_API_KEY is required",
    ):
        settings.require_openai_api_key()


def test_require_openweather_api_key_raises_when_missing() -> None:
    settings = Settings(
        _env_file=None,
        openweather_api_key=None,
    )

    with pytest.raises(
        RuntimeError,
        match="OPENWEATHER_API_KEY is required",
    ):
        settings.require_openweather_api_key()
