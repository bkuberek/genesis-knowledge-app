"""Shared fixtures for live integration tests.

These tests hit a real API + Keycloak running via Docker Compose.
All URLs and credentials are configurable through environment variables.
"""

import os

import httpx
import pytest

# ---------------------------------------------------------------------------
# Default configuration (matches docker-compose.yml + realm-export.json)
# ---------------------------------------------------------------------------

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_KEYCLOAK_URL = "http://localhost:8080"
DEFAULT_REALM = "knowledge"
DEFAULT_CLIENT_ID = "knowledge-app"
DEFAULT_CLIENT_SECRET = "knowledge-app-secret"
DEFAULT_USERNAME = "test@knowledge.local"
DEFAULT_PASSWORD = "test123"

TOKEN_REQUEST_TIMEOUT = 10.0
API_REQUEST_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# URL fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.environ.get("TEST_API_URL", DEFAULT_API_URL)


@pytest.fixture(scope="session")
def keycloak_url() -> str:
    return os.environ.get("TEST_KEYCLOAK_URL", DEFAULT_KEYCLOAK_URL)


# ---------------------------------------------------------------------------
# Token acquisition (password grant — session-scoped for speed)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def keycloak_token(keycloak_url: str) -> str:
    """Fetch a Keycloak access token via the resource-owner password grant."""
    realm = os.environ.get("TEST_KEYCLOAK_REALM", DEFAULT_REALM)
    token_endpoint = f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token"

    payload = {
        "grant_type": "password",
        "client_id": os.environ.get("TEST_CLIENT_ID", DEFAULT_CLIENT_ID),
        "client_secret": os.environ.get("TEST_CLIENT_SECRET", DEFAULT_CLIENT_SECRET),
        "username": os.environ.get("TEST_USERNAME", DEFAULT_USERNAME),
        "password": os.environ.get("TEST_PASSWORD", DEFAULT_PASSWORD),
    }

    response = httpx.post(
        token_endpoint,
        data=payload,
        timeout=TOKEN_REQUEST_TIMEOUT,
    )

    if response.status_code != 200:
        pytest.fail(f"Failed to acquire Keycloak token: {response.status_code} {response.text}")

    token_data = response.json()
    access_token = token_data.get("access_token")
    if not access_token:
        pytest.fail(f"No access_token in Keycloak response: {token_data}")

    return access_token


@pytest.fixture(scope="session")
def auth_headers(keycloak_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {keycloak_token}"}


# ---------------------------------------------------------------------------
# Async HTTP client (session-scoped)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def api_client(
    base_url: str,
    auth_headers: dict[str, str],
) -> httpx.AsyncClient:
    async with httpx.AsyncClient(
        base_url=base_url,
        headers=auth_headers,
        timeout=API_REQUEST_TIMEOUT,
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Unauthenticated client (for 401 tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
async def anon_client(base_url: str) -> httpx.AsyncClient:
    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=API_REQUEST_TIMEOUT,
    ) as client:
        yield client
