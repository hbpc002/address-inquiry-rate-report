from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, DateTime
from sqlalchemy.sql import func
from app.models.database import Base


class ShiftType(Base):
    __tablename__ = "shift_types"

    id = Column(Integer, primary_key=True, index=True)
    shift_name = Column(String(20), unique=True, nullable=False)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    start_time2 = Column(String(5))
    end_time2 = Column(String(5))
    work_hours = Column(DECIMAL(4, 1), nullable=False)
    color = Column(String(20), default="#409EFF")
    is_night = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())