from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_permission
from app.models.agent_conversation import AgentConversation
from app.models.agent_message import AgentMessage
from app.models.database import get_db
from app.models.user import User
from app.services.agent_sessions import (
    can_access_conversation,
    get_conversation,
    is_admin_user,
    serialize_conversation,
    serialize_message,
)

router = APIRouter(prefix="/api/agent/conversations", tags=["智能体会话"])


class ConversationPatch(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None


def _owner_map(db: Session, conversations: list[AgentConversation]) -> dict:
    user_ids = {c.user_id for c in conversations if c.user_id is not None}
    if not user_ids:
        return {}
    return {
        user.id: user
        for user in db.query(User).filter(User.id.in_(user_ids)).all()
    }


@router.get("")
def list_conversations(
    q: str = Query("", max_length=200),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.use")
    admin = is_admin_user(current_user)
    query = db.query(AgentConversation).filter(
        AgentConversation.deleted_at.is_(None)
    )
    if not admin:
        query = query.filter(AgentConversation.user_id == current_user.get("id"))

    text = (q or "").strip()
    if text:
        pattern = f"%{text}%"
        filters = [
            AgentConversation.title.ilike(pattern),
            AgentConversation.last_message_preview.ilike(pattern),
            AgentConversation.messages.any(AgentMessage.content.ilike(pattern)),
        ]
        if admin:
            owner_ids = [
                row[0]
                for row in db.query(User.id)
                .filter(
                    or_(
                        User.username.ilike(pattern),
                        User.display_name.ilike(pattern),
                    )
                )
                .all()
            ]
            if owner_ids:
                filters.append(AgentConversation.user_id.in_(owner_ids))
        query = query.filter(or_(*filters))

    total = query.count()
    rows = (
        query.order_by(
            AgentConversation.is_pinned.desc(),
            AgentConversation.last_message_at.desc().nullslast(),
            AgentConversation.updated_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    owners = _owner_map(db, rows) if admin else {}
    return {
        "items": [
            serialize_conversation(
                item,
                owner=owners.get(item.user_id) if admin else None,
            )
            for item in rows
        ],
        "total": total,
        "has_more": offset + len(rows) < total,
    }


@router.get("/{conversation_id}")
def get_conversation_detail(
    conversation_id: int,
    limit: int = Query(200, ge=1, le=500),
    before_id: Optional[int] = Query(None, ge=1),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.use")
    conversation = get_conversation(db, conversation_id)
    if not conversation or not can_access_conversation(current_user, conversation):
        raise HTTPException(status_code=404, detail="会话不存在")
    query = db.query(AgentMessage).filter(
        AgentMessage.conversation_id == conversation_id
    )
    if before_id is not None:
        query = query.filter(AgentMessage.id < before_id)
    rows = query.order_by(AgentMessage.id.desc()).limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    rows.reverse()
    owner = (
        db.query(User).filter(User.id == conversation.user_id).first()
        if is_admin_user(current_user)
        else None
    )
    return {
        **serialize_conversation(conversation, owner=owner),
        "messages": [serialize_message(item) for item in rows],
        "has_more": has_more,
    }


@router.patch("/{conversation_id}")
def update_conversation(
    conversation_id: int,
    body: ConversationPatch,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.use")
    conversation = get_conversation(db, conversation_id)
    if not conversation or not can_access_conversation(current_user, conversation):
        raise HTTPException(status_code=404, detail="会话不存在")
    provided = body.dict(exclude_unset=True)
    if "title" in provided:
        title = str(provided.get("title") or "").strip()
        if not title:
            raise HTTPException(status_code=422, detail="会话标题不能为空")
        conversation.title = title[:200]
    if "is_pinned" in provided:
        conversation.is_pinned = bool(provided["is_pinned"])
        conversation.pinned_at = datetime.utcnow() if conversation.is_pinned else None
    db.commit()
    db.refresh(conversation)
    owner = (
        db.query(User).filter(User.id == conversation.user_id).first()
        if is_admin_user(current_user)
        else None
    )
    return serialize_conversation(conversation, owner=owner)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.use")
    conversation = get_conversation(db, conversation_id)
    if not conversation or not can_access_conversation(current_user, conversation):
        raise HTTPException(status_code=404, detail="会话不存在")
    conversation.deleted_at = datetime.utcnow()
    db.commit()
    return {"message": "会话已删除"}
