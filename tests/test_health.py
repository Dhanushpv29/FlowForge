from fastapi.testclient import TestClient

from flowforge import __version__
from flowforge.main import create_app


def test_liveness_needs_no_dependencies():
    # No `client` fixture: liveness must work even when PostgreSQL/Redis are down.
    with TestClient(create_app()) as test_client:
        response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "FlowForge", "version": __version__}


def test_openapi_schema_is_served():
    with TestClient(create_app()) as test_client:
        response = test_client.get("/openapi.json")
    assert response.status_code == 200
    assert {"/health", "/ready"} <= set(response.json()["paths"])
