# Authentication — Specification

**Phase**: 4
**Status**: Implemented (retroactive spec)
**Change**: auth-phase4

## Intent

Implement the authentication layer for the knowledge app — a port interface in the domain,
a Keycloak JWKS adapter for JWT validation, and FastAPI dependencies for both HTTP and
WebSocket authentication. All API endpoints must require a valid Bearer token.

## Key Requirements

### REQ-4.1: AuthPort Interface

**GIVEN** the hexagonal architecture with abstract ports
**WHEN** the system needs to authenticate users
**THEN** `AuthPort` must define two async methods: `validate_token(token) -> User` and
`get_public_keys() -> dict`, allowing any identity provider implementation.

### REQ-4.2: Keycloak Auth Adapter

**GIVEN** Keycloak is the identity provider
**WHEN** a JWT token needs validation
**THEN** `KeycloakAuthAdapter` must: fetch JWKS from Keycloak's OpenID Connect endpoint
(with caching), match the token's `kid` header to a public key, decode with RS256 algorithm,
verify the issuer claim, and return a `User` domain object with `id`, `email`, and `name`
from JWT claims.

### REQ-4.3: Audience Verification Disabled

**GIVEN** the frontend (public PKCE client) and backend (confidential client) receive
different `aud` claims from Keycloak
**WHEN** validating tokens
**THEN** audience verification must be disabled (`verify_aud: False`) to accept tokens
from both clients.

### REQ-4.4: HTTP Bearer Authentication

**GIVEN** a REST API endpoint requiring authentication
**WHEN** a request arrives with an `Authorization: Bearer <token>` header
**THEN** the `get_current_user` FastAPI dependency must extract the token, validate it
via the configured `AuthPort`, and return the `User` object. Missing tokens must return
401 with `WWW-Authenticate: Bearer`. Invalid tokens must return 401.

### REQ-4.5: WebSocket Authentication

**GIVEN** WebSocket connections cannot set custom headers
**WHEN** a WebSocket upgrade request arrives
**THEN** `authenticate_websocket` must extract the JWT from the `token` query parameter
and validate it via `AuthPort`. Missing or invalid tokens must raise
`WebSocketException(WS_1008_POLICY_VIOLATION)`.

### REQ-4.6: Split URL Configuration for Docker

**GIVEN** Docker environments where the browser reaches Keycloak at `localhost:8080` but
the app container reaches it at `keycloak:8080`
**WHEN** configuring the Keycloak adapter
**THEN** the adapter must support separate `keycloak.jwks_url` (for fetching keys) and
`keycloak.issuer_url` (for validating the `iss` claim) configuration overrides.

### REQ-4.7: Auth Adapter Singleton Pattern

**GIVEN** FastAPI's dependency injection system
**WHEN** the application starts
**THEN** a module-level `_auth_adapter` singleton must be set via `set_auth_adapter()` during
lifespan startup, used by `get_current_user` without requiring the adapter as a parameter.

## Implementation Summary

### Files Created/Modified

- `src/knowledge_core/ports/auth_port.py` — Abstract authentication interface
- `src/knowledge_core/ports/__init__.py` — Added `AuthPort` export
- `src/knowledge_workers/adapters/keycloak_auth.py` — JWKS caching, RS256 validation
- `src/knowledge_api/dependencies/auth.py` — `get_current_user` FastAPI dependency
- `src/knowledge_api/dependencies/websocket_auth.py` — WebSocket token query param auth
- `src/knowledge_api/dependencies/__init__.py` — Re-exports auth utilities
- `tests/unit/test_auth.py` — 16 tests (adapter, dependency, WS auth, boundaries)

### Key Patterns & Decisions

- `noqa: B008` required for FastAPI `Depends()` in function signatures (ruff false positive)
- `noqa: TCH001` for imports used by FastAPI at runtime (not under `TYPE_CHECKING`)
- `noqa: PLW0603` for the module-level `global` auth adapter singleton
- `raise ... from exc` enforced in except clauses by ruff B904
- `_find_matching_key` extracted as `@staticmethod` for clean single-responsibility

## Discoveries

- Keycloak issues different `aud` claims for public (PKCE) vs confidential clients —
  `verify_aud: False` is required to accept frontend-issued tokens at the backend
- Test JWT tokens can be created using `cryptography` + `python-jose` with RSA key pairs
- Keycloak 26 changed the health endpoint behavior — uses port 9000 for the management
  interface, not 8080
