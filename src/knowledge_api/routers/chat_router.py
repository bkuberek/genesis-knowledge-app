import uuid

from fastapi import APIRouter, Depends, HTTPException

from knowledge_api.dependencies.auth import get_current_user
from knowledge_api.dependencies.container import container
from knowledge_api.schemas.chat_schemas import (
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionUpdate,
)
from knowledge_core.domain.user import User  # noqa: TCH001

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=201,
    operation_id="create_chat_session",
)
async def create_session(
    request: ChatSessionCreate,
    user: User = Depends(get_current_user),  # noqa: B008
) -> ChatSessionResponse:
    """Create a new chat session."""
    session = await container.repository.create_chat_session(
        user.id,
        request.title,
    )
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get(
    "/sessions",
    response_model=list[ChatSessionResponse],
    operation_id="list_chat_sessions",
)
async def list_sessions(
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[ChatSessionResponse]:
    """List the current user's chat sessions."""
    sessions = await container.repository.get_chat_sessions(user.id)
    return [
        ChatSessionResponse(
            id=s.id,
            title=s.title,
            created_at=s.created_at,
            updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    operation_id="get_chat_session",
)
async def get_session(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),  # noqa: B008
) -> ChatSessionResponse:
    """Get a specific chat session."""
    session = await container.repository.get_chat_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.patch(
    "/sessions/{session_id}",
    operation_id="update_chat_session",
)
async def update_session(
    session_id: uuid.UUID,
    request: ChatSessionUpdate,
    user: User = Depends(get_current_user),  # noqa: B008
) -> dict:
    """Update a chat session's title."""
    await container.repository.update_chat_session(session_id, request.title)
    return {"status": "updated"}


@router.delete(
    "/sessions/{session_id}",
    status_code=204,
    operation_id="delete_chat_session",
)
async def delete_session(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),  # noqa: B008
) -> None:
    """Delete a chat session."""
    await container.repository.delete_chat_session(session_id)


@router.get(
    "/sessions/{session_id}/messages",
    response_model=list[ChatMessageResponse],
    operation_id="get_chat_messages",
)
async def get_messages(
    session_id: uuid.UUID,
    user: User = Depends(get_current_user),  # noqa: B008
) -> list[ChatMessageResponse]:
    """Get messages from a chat session."""
    messages = await container.repository.get_chat_messages(session_id)
    return [
        ChatMessageResponse(
            id=m.id,
            role=m.role.value,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]
