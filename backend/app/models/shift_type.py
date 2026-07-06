from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime, JSON
from sqlalchemy.sql import func
from app.models.database import Base


class ShiftType(Base):
    __tablename__ = "shift_types"

    id = Column(Integer, primary_key=True, index=True)
    shift_name = Column(String(100), unique=True, nullable=False)
    time_segments = Column(JSON, nullable=False)
    work_hours = Column(DECIMAL(4, 1), nullable=False)
    color = Column(String(20), default="#409EFF")
    is_night = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())