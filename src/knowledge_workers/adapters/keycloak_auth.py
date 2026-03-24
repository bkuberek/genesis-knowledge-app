import logging
import uuid

import httpx
from jose import JWTError, jwt

from knowledge_core.config import settings
from knowledge_core.domain.user import User
from knowledge_core.exceptions import AuthenticationError
from knowledge_core.ports.auth_port import AuthPort

logger = logging.getLogger(__name__)


class KeycloakAuthAdapter(AuthPort):
    """Keycloak-backed authentication adapter using JWKS validation.

    Supports split URL configuration for Docker environments where the
    browser reaches Keycloak at one URL (e.g. ``localhost:8080``) but
    the app container reaches it at another (e.g. ``keycloak:8080``).

    Config keys (via dynaconf / env vars):
        keycloak.server_url   — base URL used to build JWKS URL
        keycloak.realm        — Keycloak realm name
        keycloak.jwks_url     — override full JWKS endpoint URL
        keycloak.issuer_url   — override expected ``iss`` claim value
    """

    def __init__(self) -> None:
        self._jwks: dict | None = None
        server_url = settings.keycloak.server_url
        realm = settings.keycloak.realm
        default_realm_url = f"{server_url}/realms/{realm}"

        self._jwks_url = (
            getattr(settings.keycloak, "jwks_url", "")
            or f"{default_realm_url}/protocol/openid-connect/certs"
        )
        self._issuer = getattr(settings.keycloak, "issuer_url", "") or default_realm_url
        logger.info("Keycloak JWKS URL: %s", self._jwks_url)
        logger.info("Keycloak expected issuer: %s", self._issuer)

    async def get_public_keys(self) -> dict:
        if self._jwks is None:
            async with httpx.AsyncClient() as client:
                response = await client.get(self._jwks_url)
                response.raise_for_status()
                self._jwks = response.json()
        return self._jwks

    async def validate_token(self, token: str) -> User:
        try:
            jwks = await self.get_public_keys()
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            rsa_key = self._find_matching_key(jwks, kid)
            if not rsa_key:
                raise AuthenticationError("Unable to find matching key")

            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                options={"verify_aud": False},
            )

            return User(
                id=uuid.UUID(payload["sub"]),
                email=payload.get("email", ""),
                name=payload.get("preferred_username", payload.get("name", "")),
            )
        except AuthenticationError:
            raise
        except JWTError as exc:
            raise AuthenticationError(f"Invalid token: {exc}") from exc
        except Exception as exc:
            raise AuthenticationError(f"Authentication failed: {exc}") from exc

    @staticmethod
    def _find_matching_key(jwks: dict, kid: str | None) -> dict:
        """Find the RSA key in JWKS that matches the token's key ID."""
        for key in jwks.get("keys", []):
            if key["kid"] == kid:
                return key
        return {}
