"""智能体会话持久化、访问控制与清理。"""
from datetime import datetime, timedelta

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.agent_conversation import AgentConversation
from app.models.agent_message import AgentMessage


def is_admin_user(user: dict) -> bool:
    return bool(user.get("is_system")) or user.get("role") == "admin"


def can_access_conversation(user: dict, conversation: AgentConversation) -> bool:
    return is_admin_user(user) or conversation.user_id == user.get("id")


def make_title(message: str, limit: int = 30) -> str:
    text = " ".join(str(message or "").split())
    return (text[:limit] + ("…" if len(text) > limit else "")) or "新对话"


def get_conversation(db: Session, conversation_id: int) -> AgentConversation:
    return (
        db.query(AgentConversation)
        .filter(
            AgentConversation.id == conversation_id,
            AgentConversation.deleted_at.is_(None),
        )
        .first()
    )


def create_conversation(
    db: Session,
    user: dict,
    message: str,
    provider: str = None,
    model: str = None,
) -> AgentConversation:
    conversation = AgentConversation(
        user_id=user.get("id"),
        title=make_title(message),
        provider=provider,
        model=model,
        message_count=0,
        last_message_preview="",
    )
    db.add(conversation)
    db.flush()
    return conversation


def add_message(
    db: Session,
    conversation: AgentConversation,
    role: str,
    content: str,
    *,
    events: list = None,
    status: str = "complete",
    provider: str = None,
    model: str = None,
    update_preview: bool = True,
) -> AgentMessage:
    now = datetime.utcnow()
    message = AgentMessage(
        conversation_id=conversation.id,
        role=role,
        content=content or "",
        events=events or [],
        status=status,
        provider=provider,
        model=model,
    )
    db.add(message)
    conversation.message_count = int(conversation.message_count or 0) + 1
    conversation.last_message_at = now
    if update_preview:
        conversation.last_message_preview = (content or "")[:200]
    db.flush()
    return message


def load_context_messages(
    db: Session,
    conversation_id: int,
    limit: int,
) -> list[dict]:
    """读取最近 N 条可用于 LLM 上下文的 user/assistant 文本消息。"""
    limit = max(0, int(limit or 0))
    if limit <= 0:
        return []
    rows = (
        db.query(AgentMessage)
        .filter(
            AgentMessage.conversation_id == conversation_id,
            AgentMessage.role.in_(("user", "assistant")),
            AgentMessage.status != "streaming",
            AgentMessage.content.isnot(None),
            AgentMessage.content != "",
        )
        .order_by(AgentMessage.id.desc())
        .limit(limit + 1)
        .all()
    )
    rows.reverse()
    if len(rows) > limit:
        rows = rows[-limit:]
    while rows and rows[0].role == "assistant":
        rows.pop(0)
    return [{"role": row.role, "content": row.content} for row in rows]


def finalize_assistant_message(
    db: Session,
    message_id: int,
    content: str,
    events: list,
    status: str,
) -> AgentMessage | None:
    message = db.query(AgentMessage).filter(AgentMessage.id == message_id).first()
    if not message:
        return None
    message.content = content or ""
    message.events = events or []
    message.status = status or "complete"
    conversation = (
        db.query(AgentConversation)
        .filter(AgentConversation.id == message.conversation_id)
        .first()
    )
    if conversation:
        conversation.last_message_at = datetime.utcnow()
        conversation.last_message_preview = (
            message.content[:200] if message.content else "（无输出）"
        )
    db.commit()
    db.refresh(message)
    return message


def serialize_message(message: AgentMessage) -> dict:
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content or "",
        "events": message.events or [],
        "status": message.status,
        "provider": message.provider,
        "model": message.model,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def serialize_conversation(conversation: AgentConversation, owner=None) -> dict:
    data = {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "title": conversation.title,
        "provider": conversation.provider,
        "model": conversation.model,
        "is_pinned": bool(conversation.is_pinned),
        "pinned_at": conversation.pinned_at.isoformat() if conversation.pinned_at else None,
        "message_count": int(conversation.message_count or 0),
        "last_message_at": (
            conversation.last_message_at.isoformat() if conversation.last_message_at else None
        ),
        "last_message_preview": conversation.last_message_preview or "",
        "created_at": conversation.created_at.isoformat() if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat() if conversation.updated_at else None,
    }
    if owner is not None:
        data["owner_id"] = owner.id
        data["owner_username"] = owner.username
        data["owner_name"] = owner.display_name or owner.username
    return data


def cleanup_expired_conversations(
    db: Session,
    retention_days: int,
    now: datetime = None,
) -> int:
    """软删除过期非置顶会话，并物理删除已软删除超过 7 天的会话。"""
    now = now or datetime.utcnow()
    removed = 0
    if retention_days and int(retention_days) > 0:
        cutoff = now - timedelta(days=int(retention_days))
        empty_cutoff = now - timedelta(days=1)
        query = db.query(AgentConversation).filter(
            AgentConversation.deleted_at.is_(None),
            AgentConversation.is_pinned.is_(False),
            or_(
                AgentConversation.last_message_at < cutoff,
                and_(
                    AgentConversation.last_message_at.is_(None),
                    AgentConversation.created_at < empty_cutoff,
                ),
            ),
        )
        removed = query.update(
            {AgentConversation.deleted_at: now},
            synchronize_session=False,
        )
    purge_before = now - timedelta(days=7)
    db.query(AgentConversation).filter(
        AgentConversation.deleted_at.isnot(None),
        AgentConversation.deleted_at < purge_before,
    ).delete(synchronize_session=False)
    db.commit()
    return int(removed or 0)
