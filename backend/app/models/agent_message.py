from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.database import Base


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("agent_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False, index=True)
    content = Column(Text, nullable=False, default="")
    events = Column(JSON, nullable=False, default=list)
    status = Column(String(20), nullable=False, default="complete", index=True)
    provider = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    conversation = relationship("AgentConversation", back_populates="messages")
