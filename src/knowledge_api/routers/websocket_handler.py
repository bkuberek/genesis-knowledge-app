import contextlib
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from knowledge_api.dependencies.container import container
from knowledge_api.dependencies.websocket_auth import authenticate_websocket
from knowledge_core.domain.chat_message import ChatMessage, MessageRole

router = APIRouter()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time chat with the knowledge agent."""
    user = await authenticate_websocket(websocket, container.auth_adapter)

    session_id = _resolve_session_id(websocket)
    if session_id is None:
        session = await container.repository.create_chat_session(user.id)
        session_id = session.id

    await websocket.accept()

    history = await container.repository.get_chat_messages(session_id)
    await _send_session_info(websocket, session_id, history)

    with contextlib.suppress(WebSocketDisconnect):
        await _message_loop(websocket, session_id)


def _resolve_session_id(websocket: WebSocket) -> uuid.UUID | None:
    """Extract session_id from query params, if present."""
    raw = websocket.query_params.get("session_id")
    if raw:
        return uuid.UUID(raw)
    return None


async def _send_session_info(
    websocket: WebSocket,
    session_id: uuid.UUID,
    history: list[ChatMessage],
) -> None:
    """Send session metadata and conversation history to the client."""
    await websocket.send_json(
        {
            "type": "session",
            "session_id": str(session_id),
            "history": [
                {
                    "role": m.role.value,
                    "content": m.content,
                    "created_at": m.created_at.isoformat(),
                }
                for m in history
            ],
        }
    )


async def _message_loop(
    websocket: WebSocket,
    session_id: uuid.UUID,
) -> None:
    """Receive user messages and respond (stub — Phase 6 adds the agent)."""
    while True:
        data = await websocket.receive_json()
        user_message = data.get("content", "")

        if not user_message:
            continue

        user_msg = ChatMessage(
            session_id=session_id,
            role=MessageRole.USER,
            content=user_message,
        )
        await container.repository.save_chat_message(user_msg)

        # TODO: Phase 6 will replace this stub with the chat agent
        assistant_content = (
            f"I received your message: '{user_message}'. The chat agent is not yet implemented."
        )

        assistant_msg = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=assistant_content,
        )
        await container.repository.save_chat_message(assistant_msg)

        await websocket.send_json(
            {
                "type": "message",
                "role": "assistant",
                "content": assistant_content,
            }
        )
