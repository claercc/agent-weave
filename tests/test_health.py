from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.health import router


def create_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")
    return TestClient(app)


def test_liveness_returns_ok() -> None:
    client = create_test_client()

    response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_returns_ok() -> None:
    client = create_test_client()

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}