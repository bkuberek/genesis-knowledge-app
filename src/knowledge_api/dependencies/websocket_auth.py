from fastapi import WebSocket, WebSocketException, status

from knowledge_core.domain.user import User
from knowledge_core.ports.auth_port import AuthPort


async def authenticate_websocket(
    websocket: WebSocket,
    auth_adapter: AuthPort,
) -> User:
    """Authenticate a WebSocket connection using the token query parameter."""
    token = websocket.query_params.get("token")
    if not token:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)

    try:
        return await auth_adapter.validate_token(token)
    except Exception as exc:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION) from exc
