from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.database import Base


class AgentConversation(Base):
    __tablename__ = "agent_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False, default="新对话")
    provider = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    is_pinned = Column(Boolean, nullable=False, default=False, index=True)
    pinned_at = Column(DateTime, nullable=True)
    message_count = Column(Integer, nullable=False, default=0)
    last_message_at = Column(DateTime, nullable=True, index=True)
    last_message_preview = Column(String(200), nullable=False, default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True, index=True)

    messages = relationship(
        "AgentMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
