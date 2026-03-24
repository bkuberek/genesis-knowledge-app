"""Integration tests for the WebSocket chat endpoint.

Tests connection handshake, session info delivery, and auth rejection.
Message exchange with the LLM is marked with ``@pytest.mark.llm``.
"""

import json

import pytest
import websockets
import websockets.exceptions

pytestmark = pytest.mark.integration

WS_CONNECT_TIMEOUT = 10
WS_RECEIVE_TIMEOUT = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ws_url(base_url: str, token: str, session_id: str | None = None) -> str:
    """Build the WebSocket URL with token and optional session_id."""
    host = base_url.replace("http://", "ws://").replace("https://", "wss://")
    url = f"{host}/ws/chat?token={token}"
    if session_id:
        url += f"&session_id={session_id}"
    return url


# ---------------------------------------------------------------------------
# Connection & session info
# ---------------------------------------------------------------------------


class TestWebSocketConnect:
    async def test_connect_receives_session_message(self, base_url: str, keycloak_token: str):
        url = _ws_url(base_url, keycloak_token)
        async with websockets.connect(url, open_timeout=WS_CONNECT_TIMEOUT) as ws:
            raw = await ws.recv()
            data = json.loads(raw)

            assert data["type"] == "session"

    async def test_session_message_contains_session_id(self, base_url: str, keycloak_token: str):
        url = _ws_url(base_url, keycloak_token)
        async with websockets.connect(url, open_timeout=WS_CONNECT_TIMEOUT) as ws:
            raw = await ws.recv()
            data = json.loads(raw)

            assert "session_id" in data
            assert isinstance(data["session_id"], str)
            assert len(data["session_id"]) > 0

    async def test_session_message_contains_history(self, base_url: str, keycloak_token: str):
        url = _ws_url(base_url, keycloak_token)
        async with websockets.connect(url, open_timeout=WS_CONNECT_TIMEOUT) as ws:
            raw = await ws.recv()
            data = json.loads(raw)

            assert "history" in data
            assert isinstance(data["history"], list)


# ---------------------------------------------------------------------------
# Message exchange (requires LLM)
# ---------------------------------------------------------------------------


class TestWebSocketMessages:
    @pytest.mark.llm
    async def test_send_message_receives_assistant_reply(self, base_url: str, keycloak_token: str):
        url = _ws_url(base_url, keycloak_token)
        async with websockets.connect(url, open_timeout=WS_CONNECT_TIMEOUT) as ws:
            # Consume the session info message
            await ws.recv()

            await ws.send(json.dumps({"content": "Hello"}))

            # We may receive a title_updated message before the response
            response_data = None
            for _ in range(5):
                raw = await ws.recv()
                data = json.loads(raw)
                if data.get("type") == "message":
                    response_data = data
                    break

            assert response_data is not None
            assert response_data["type"] == "message"
            assert response_data["role"] == "assistant"
            assert len(response_data["content"]) > 0


# ---------------------------------------------------------------------------
# Auth rejection
# ---------------------------------------------------------------------------


class TestWebSocketAuthReject:
    async def test_connect_without_token_rejected(self, base_url: str):
        host = base_url.replace("http://", "ws://").replace("https://", "wss://")
        url = f"{host}/ws/chat"

        with pytest.raises(
            (
                websockets.exceptions.InvalidStatus,
                websockets.exceptions.ConnectionClosed,
                ConnectionRefusedError,
                OSError,
            )
        ):
            async with websockets.connect(url, open_timeout=WS_CONNECT_TIMEOUT) as ws:
                await ws.recv()

    async def test_connect_with_invalid_token_rejected(self, base_url: str):
        url = _ws_url(base_url, "invalid-token-value")

        with pytest.raises(
            (
                websockets.exceptions.InvalidStatus,
                websockets.exceptions.ConnectionClosed,
                ConnectionRefusedError,
                OSError,
            )
        ):
            async with websockets.connect(url, open_timeout=WS_CONNECT_TIMEOUT) as ws:
                await ws.recv()

    async def test_connect_with_expired_token_rejected(self, base_url: str):
        expired_token = (
            "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJmYWtlIn0."
            "eyJleHAiOjEwMDAwMDAwMDAsImlhdCI6MTAwMDAwMDAwMCwic3ViIjoiZmFrZSJ9."
            "fake-signature"
        )
        url = _ws_url(base_url, expired_token)

        with pytest.raises(
            (
                websockets.exceptions.InvalidStatus,
                websockets.exceptions.ConnectionClosed,
                ConnectionRefusedError,
                OSError,
            )
        ):
            async with websockets.connect(url, open_timeout=WS_CONNECT_TIMEOUT) as ws:
                await ws.recv()
