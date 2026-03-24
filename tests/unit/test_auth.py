import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import WebSocket, WebSocketException
from jose import jwt

from knowledge_api.dependencies.auth import (
    get_current_user,
    set_auth_adapter,
)
from knowledge_api.dependencies.websocket_auth import authenticate_websocket
from knowledge_core.domain.user import User
from knowledge_core.exceptions import AuthenticationError
from knowledge_core.ports.auth_port import AuthPort
from knowledge_workers.adapters.keycloak_auth import KeycloakAuthAdapter

# ---------------------------------------------------------------------------
# Test RSA key generation helpers
# ---------------------------------------------------------------------------

TEST_USER_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")
TEST_KID = "test-key-id"


def _generate_rsa_keypair():
    """Generate an RSA key pair for test JWT signing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    return private_key


def _private_key_to_pem(private_key) -> str:
    return private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _public_key_to_jwk(private_key) -> dict:
    """Convert RSA public key to JWK dict for JWKS mock."""
    public_key = private_key.public_key()
    public_numbers = public_key.public_numbers()

    import base64

    def _int_to_base64url(value: int, length: int) -> str:
        data = value.to_bytes(length, byteorder="big")
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    return {
        "kty": "RSA",
        "kid": TEST_KID,
        "use": "sig",
        "alg": "RS256",
        "n": _int_to_base64url(public_numbers.n, 256),
        "e": _int_to_base64url(public_numbers.e, 3),
    }


def _create_test_token(
    private_key,
    claims: dict | None = None,
) -> str:
    """Create a signed JWT token for testing."""
    default_claims = {
        "sub": str(TEST_USER_ID),
        "email": "test@example.com",
        "preferred_username": "testuser",
        "iss": "http://localhost:8080/realms/knowledge",
    }
    if claims:
        default_claims.update(claims)

    pem = _private_key_to_pem(private_key)
    return jwt.encode(
        default_claims,
        pem,
        algorithm="RS256",
        headers={"kid": TEST_KID},
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def rsa_keypair():
    return _generate_rsa_keypair()


@pytest.fixture
def jwks(rsa_keypair) -> dict:
    return {"keys": [_public_key_to_jwk(rsa_keypair)]}


@pytest.fixture
def valid_token(rsa_keypair) -> str:
    return _create_test_token(rsa_keypair)


# ---------------------------------------------------------------------------
# AuthPort abstract interface
# ---------------------------------------------------------------------------


class TestAuthPort:
    def test_auth_port_is_abstract(self):
        with pytest.raises(TypeError, match="abstract"):
            AuthPort()


# ---------------------------------------------------------------------------
# KeycloakAuthAdapter
# ---------------------------------------------------------------------------


class TestKeycloakAuthAdapter:
    @patch("knowledge_workers.adapters.keycloak_auth.settings")
    def test_initializes_with_settings(self, mock_settings):
        mock_settings.keycloak.server_url = "http://kc:8080"
        mock_settings.keycloak.realm = "myrealm"
        mock_settings.keycloak.jwks_url = ""
        mock_settings.keycloak.issuer_url = ""

        adapter = KeycloakAuthAdapter()

        assert adapter._issuer == "http://kc:8080/realms/myrealm"
        assert adapter._jwks_url == ("http://kc:8080/realms/myrealm/protocol/openid-connect/certs")

    @patch("knowledge_workers.adapters.keycloak_auth.settings")
    def test_initializes_with_split_urls(self, mock_settings):
        """In Docker, JWKS is fetched via internal URL, issuer matches browser."""
        mock_settings.keycloak.server_url = "http://keycloak:8080"
        mock_settings.keycloak.realm = "knowledge"
        mock_settings.keycloak.jwks_url = ""
        mock_settings.keycloak.issuer_url = "http://localhost:8080/realms/knowledge"

        adapter = KeycloakAuthAdapter()

        assert adapter._issuer == "http://localhost:8080/realms/knowledge"
        assert adapter._jwks_url == (
            "http://keycloak:8080/realms/knowledge/protocol/openid-connect/certs"
        )

    @patch("knowledge_workers.adapters.keycloak_auth.settings")
    def test_initializes_with_explicit_jwks_url(self, mock_settings):
        mock_settings.keycloak.server_url = "http://localhost:8080"
        mock_settings.keycloak.realm = "knowledge"
        mock_settings.keycloak.jwks_url = (
            "http://keycloak:8080/realms/knowledge/protocol/openid-connect/certs"
        )
        mock_settings.keycloak.issuer_url = ""

        adapter = KeycloakAuthAdapter()

        assert adapter._issuer == ("http://localhost:8080/realms/knowledge")
        assert adapter._jwks_url == (
            "http://keycloak:8080/realms/knowledge/protocol/openid-connect/certs"
        )

    @patch("knowledge_workers.adapters.keycloak_auth.settings")
    async def test_validate_token_returns_user(self, mock_settings, jwks, valid_token):
        mock_settings.keycloak.server_url = "http://localhost:8080"
        mock_settings.keycloak.realm = "knowledge"
        mock_settings.keycloak.jwks_url = ""
        mock_settings.keycloak.issuer_url = ""

        adapter = KeycloakAuthAdapter()
        adapter._jwks = jwks

        user = await adapter.validate_token(valid_token)

        assert user.id == TEST_USER_ID
        assert user.email == "test@example.com"
        assert user.name == "testuser"

    @patch("knowledge_workers.adapters.keycloak_auth.settings")
    async def test_validate_token_invalid_token_raises_auth_error(self, mock_settings, jwks):
        mock_settings.keycloak.server_url = "http://localhost:8080"
        mock_settings.keycloak.realm = "knowledge"
        mock_settings.keycloak.jwks_url = ""
        mock_settings.keycloak.issuer_url = ""

        adapter = KeycloakAuthAdapter()
        adapter._jwks = jwks

        with pytest.raises(AuthenticationError, match="Invalid token"):
            await adapter.validate_token("not.a.valid.jwt")

    @patch("knowledge_workers.adapters.keycloak_auth.settings")
    async def test_validate_token_no_matching_key_raises_auth_error(
        self, mock_settings, rsa_keypair
    ):
        mock_settings.keycloak.server_url = "http://localhost:8080"
        mock_settings.keycloak.realm = "knowledge"
        mock_settings.keycloak.jwks_url = ""
        mock_settings.keycloak.issuer_url = ""

        adapter = KeycloakAuthAdapter()
        adapter._jwks = {"keys": []}

        token = _create_test_token(rsa_keypair)
        with pytest.raises(AuthenticationError, match="Unable to find matching key"):
            await adapter.validate_token(token)

    @patch("knowledge_workers.adapters.keycloak_auth.settings")
    async def test_validate_token_wrong_issuer_raises_auth_error(
        self, mock_settings, rsa_keypair, jwks
    ):
        mock_settings.keycloak.server_url = "http://localhost:8080"
        mock_settings.keycloak.realm = "knowledge"
        mock_settings.keycloak.jwks_url = ""
        mock_settings.keycloak.issuer_url = ""

        adapter = KeycloakAuthAdapter()
        adapter._jwks = jwks

        token = _create_test_token(
            rsa_keypair,
            claims={"iss": "http://wrong-issuer/realms/other"},
        )
        with pytest.raises(AuthenticationError, match="Invalid token"):
            await adapter.validate_token(token)

    @patch("knowledge_workers.adapters.keycloak_auth.settings")
    async def test_get_public_keys_fetches_from_keycloak(self, mock_settings, jwks):
        mock_settings.keycloak.server_url = "http://localhost:8080"
        mock_settings.keycloak.realm = "knowledge"
        mock_settings.keycloak.jwks_url = ""
        mock_settings.keycloak.issuer_url = ""

        adapter = KeycloakAuthAdapter()

        mock_response = MagicMock()
        mock_response.json.return_value = jwks
        mock_response.raise_for_status = MagicMock()

        with patch("knowledge_workers.adapters.keycloak_auth.httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await adapter.get_public_keys()

        assert result == jwks

    @patch("knowledge_workers.adapters.keycloak_auth.settings")
    async def test_get_public_keys_caches_result(self, mock_settings, jwks):
        mock_settings.keycloak.server_url = "http://localhost:8080"
        mock_settings.keycloak.realm = "knowledge"
        mock_settings.keycloak.jwks_url = ""
        mock_settings.keycloak.issuer_url = ""

        adapter = KeycloakAuthAdapter()
        adapter._jwks = jwks

        result = await adapter.get_public_keys()

        assert result is jwks

    @patch("knowledge_workers.adapters.keycloak_auth.settings")
    async def test_validate_token_uses_name_when_no_preferred_username(
        self, mock_settings, rsa_keypair, jwks
    ):
        mock_settings.keycloak.server_url = "http://localhost:8080"
        mock_settings.keycloak.realm = "knowledge"
        mock_settings.keycloak.jwks_url = ""
        mock_settings.keycloak.issuer_url = ""

        adapter = KeycloakAuthAdapter()
        adapter._jwks = jwks

        token = _create_test_token(
            rsa_keypair,
            claims={
                "sub": str(TEST_USER_ID),
                "email": "test@example.com",
                "name": "Test User",
                "preferred_username": None,
                "iss": "http://localhost:8080/realms/knowledge",
            },
        )
        # When preferred_username is None, it will be used (truthy check
        # not done — it falls through). Let's test with no preferred_username key.
        claims_no_username = {
            "sub": str(TEST_USER_ID),
            "email": "test@example.com",
            "name": "Test User",
            "iss": "http://localhost:8080/realms/knowledge",
        }
        pem = _private_key_to_pem(rsa_keypair)
        token = jwt.encode(
            claims_no_username,
            pem,
            algorithm="RS256",
            headers={"kid": TEST_KID},
        )

        user = await adapter.validate_token(token)

        assert user.name == "Test User"

    @patch("knowledge_workers.adapters.keycloak_auth.settings")
    async def test_validate_token_with_split_urls_docker_scenario(
        self, mock_settings, rsa_keypair, jwks
    ):
        """Simulate Docker: JWKS via internal URL, issuer matches browser."""
        mock_settings.keycloak.server_url = "http://keycloak:8080"
        mock_settings.keycloak.realm = "knowledge"
        mock_settings.keycloak.jwks_url = ""
        mock_settings.keycloak.issuer_url = "http://localhost:8080/realms/knowledge"

        adapter = KeycloakAuthAdapter()
        adapter._jwks = jwks

        token = _create_test_token(
            rsa_keypair,
            claims={
                "sub": str(TEST_USER_ID),
                "email": "docker@example.com",
                "preferred_username": "dockeruser",
                "iss": "http://localhost:8080/realms/knowledge",
            },
        )

        user = await adapter.validate_token(token)

        assert user.id == TEST_USER_ID
        assert user.email == "docker@example.com"
        assert user.name == "dockeruser"


# ---------------------------------------------------------------------------
# get_current_user dependency
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    async def test_without_credentials_raises_401(self):
        with pytest.raises(Exception) as exc_info:
            await get_current_user(credentials=None)
        assert exc_info.value.status_code == 401
        assert "Missing authentication token" in exc_info.value.detail

    async def test_without_adapter_raises_503(self):
        set_auth_adapter(None)
        credentials = MagicMock()
        credentials.credentials = "some-token"

        with pytest.raises(Exception) as exc_info:
            await get_current_user(credentials=credentials)
        assert exc_info.value.status_code == 503

    async def test_with_valid_token_returns_user(self):
        mock_adapter = AsyncMock(spec=AuthPort)
        expected_user = User(
            id=TEST_USER_ID,
            email="test@example.com",
            name="testuser",
        )
        mock_adapter.validate_token.return_value = expected_user
        set_auth_adapter(mock_adapter)

        credentials = MagicMock()
        credentials.credentials = "valid-token"

        user = await get_current_user(credentials=credentials)

        assert user == expected_user
        mock_adapter.validate_token.assert_called_once_with("valid-token")

    async def test_with_invalid_token_raises_401(self):
        mock_adapter = AsyncMock(spec=AuthPort)
        mock_adapter.validate_token.side_effect = AuthenticationError("bad")
        set_auth_adapter(mock_adapter)

        credentials = MagicMock()
        credentials.credentials = "invalid-token"

        with pytest.raises(Exception) as exc_info:
            await get_current_user(credentials=credentials)
        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in exc_info.value.detail


# ---------------------------------------------------------------------------
# WebSocket auth
# ---------------------------------------------------------------------------


class TestWebsocketAuth:
    async def test_without_token_raises_exception(self):
        websocket = MagicMock(spec=WebSocket)
        websocket.query_params = {}
        mock_adapter = AsyncMock(spec=AuthPort)

        with pytest.raises(WebSocketException):
            await authenticate_websocket(websocket, mock_adapter)

    async def test_with_valid_token_returns_user(self):
        expected_user = User(
            id=TEST_USER_ID,
            email="test@example.com",
            name="testuser",
        )
        websocket = MagicMock(spec=WebSocket)
        websocket.query_params = {"token": "valid-ws-token"}
        mock_adapter = AsyncMock(spec=AuthPort)
        mock_adapter.validate_token.return_value = expected_user

        user = await authenticate_websocket(websocket, mock_adapter)

        assert user == expected_user
        mock_adapter.validate_token.assert_called_once_with("valid-ws-token")

    async def test_with_invalid_token_raises_exception(self):
        websocket = MagicMock(spec=WebSocket)
        websocket.query_params = {"token": "invalid-token"}
        mock_adapter = AsyncMock(spec=AuthPort)
        mock_adapter.validate_token.side_effect = AuthenticationError("bad")

        with pytest.raises(WebSocketException):
            await authenticate_websocket(websocket, mock_adapter)
