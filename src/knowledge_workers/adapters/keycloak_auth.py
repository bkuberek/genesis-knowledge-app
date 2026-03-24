import uuid

import httpx
from jose import JWTError, jwt

from knowledge_core.config import settings
from knowledge_core.domain.user import User
from knowledge_core.exceptions import AuthenticationError
from knowledge_core.ports.auth_port import AuthPort


class KeycloakAuthAdapter(AuthPort):
    """Keycloak-backed authentication adapter using JWKS validation."""

    def __init__(self) -> None:
        self._jwks: dict | None = None
        server_url = settings.keycloak.server_url
        realm = settings.keycloak.realm
        self._issuer = f"{server_url}/realms/{realm}"
        self._jwks_url = f"{self._issuer}/protocol/openid-connect/certs"

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
