from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from app.models.database import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    operation_type = Column(String(50), nullable=False)
    target_table = Column(String(50), nullable=False)
    target_id = Column(Integer)
    details = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())