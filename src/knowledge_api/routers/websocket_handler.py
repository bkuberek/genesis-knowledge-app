import contextlib
import logging
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from knowledge_api.dependencies.container import container
from knowledge_api.dependencies.websocket_auth import authenticate_websocket
from knowledge_core.domain.chat_message import ChatMessage, MessageRole

router = APIRouter()

logger = logging.getLogger(__name__)

TITLE_MAX_LENGTH = 50


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time chat with the knowledge agent."""
    user = await authenticate_websocket(websocket, container.auth_adapter)

    session_id = _resolve_session_id(websocket)
    is_new_session = session_id is None
    if is_new_session:
        session = await container.repository.create_chat_session(user.id)
        session_id = session.id

    await websocket.accept()

    history = await container.repository.get_chat_messages(session_id)
    await _send_session_info(websocket, session_id, history)

    with contextlib.suppress(WebSocketDisconnect):
        await _message_loop(
            websocket,
            session_id,
            history,
            is_new_session,
        )


def _resolve_session_id(websocket: WebSocket) -> uuid.UUID | None:
    """Extract session_id from query params, if present."""
    raw = websocket.query_params.get("session_id")
    if raw:
        return uuid.UUID(raw)
    return None


def generate_session_title(message: str) -> str:
    """Generate a short session title from the first user message.

    Truncates at the last word boundary within TITLE_MAX_LENGTH characters,
    appending an ellipsis if the message was truncated.
    """
    text = message.strip().replace("\n", " ")
    if len(text) <= TITLE_MAX_LENGTH:
        return text

    truncated = text[:TITLE_MAX_LENGTH]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        truncated = truncated[:last_space]
    return truncated + "..."


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


def _build_conversation_history(
    messages: list[ChatMessage],
) -> list[dict]:
    """Convert persisted messages to the format the agent expects."""
    return [
        {"role": m.role.value, "content": m.content}
        for m in messages
        if m.role in {MessageRole.USER, MessageRole.ASSISTANT}
    ]


async def _maybe_update_title(
    websocket: WebSocket,
    session_id: uuid.UUID,
    user_message: str,
    is_first_message: bool,
) -> None:
    """Auto-generate a session title from the first user message."""
    if not is_first_message:
        return

    title = generate_session_title(user_message)
    await container.repository.update_chat_session(session_id, title)
    await websocket.send_json(
        {
            "type": "title_updated",
            "session_id": str(session_id),
            "title": title,
        }
    )


async def _message_loop(
    websocket: WebSocket,
    session_id: uuid.UUID,
    history: list[ChatMessage],
    is_new_session: bool,
) -> None:
    """Receive user messages, run them through the chat agent, respond."""
    conversation_history = _build_conversation_history(history)
    is_first_message = is_new_session and len(history) == 0

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
        conversation_history.append({"role": "user", "content": user_message})

        await _maybe_update_title(
            websocket,
            session_id,
            user_message,
            is_first_message,
        )
        is_first_message = False

        try:
            assistant_content = await container.chat_agent.process_message(
                user_message=user_message,
                conversation_history=conversation_history[:-1],
            )
        except Exception:
            logger.exception("Chat agent error for session %s", session_id)
            assistant_content = (
                "I'm sorry, something went wrong processing your request. Please try again."
            )

        assistant_msg = ChatMessage(
            session_id=session_id,
            role=MessageRole.ASSISTANT,
            content=assistant_content,
        )
        await container.repository.save_chat_message(assistant_msg)
        conversation_history.append(
            {"role": "assistant", "content": assistant_content},
        )

        await websocket.send_json(
            {
                "type": "message",
                "role": "assistant",
                "content": assistant_content,
            }
        )
