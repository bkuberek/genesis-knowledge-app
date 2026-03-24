"""Integration tests for the health endpoint.

No authentication required — verifies the API is reachable and responsive.
"""

import httpx
import pytest

pytestmark = pytest.mark.integration


async def test_health_returns_200(api_client: httpx.AsyncClient):
    response = await api_client.get("/health")

    assert response.status_code == 200


async def test_health_returns_healthy_status(api_client: httpx.AsyncClient):
    response = await api_client.get("/health")

    body = response.json()
    assert body == {"status": "healthy"}


async def test_health_accessible_without_auth(anon_client: httpx.AsyncClient):
    response = await anon_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
