import pytest
from redis import Redis

from flowforge.api.deps import get_redis
from flowforge.main import app

pytestmark = pytest.mark.integration


def test_ready_when_database_and_redis_are_up(client, redis_client):
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["components"]["database"]["status"] == "ok"
    assert body["components"]["redis"]["status"] == "ok"


def test_ready_returns_503_when_redis_is_down(client):
    # Port 1 is closed: the connection is refused immediately.
    app.dependency_overrides[get_redis] = lambda: Redis.from_url(
        "redis://127.0.0.1:1/0", socket_connect_timeout=0.2
    )
    response = client.get("/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["components"]["database"]["status"] == "ok"
    assert body["components"]["redis"]["status"] == "error"
