from sqlalchemy import Column, Integer, String, Date, DateTime, DECIMAL, Boolean, JSON, ForeignKey
from sqlalchemy.sql import func
from app.models.database import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    schedule_date = Column(Date, nullable=False, index=True)
    shift_type_id = Column(Integer, ForeignKey("shift_types.id"))
    shift_name = Column(String(50))
    time_segments = Column(JSON)
    work_hours = Column(DECIMAL(4, 1))
    is_night = Column(Boolean, default=False)
    schedule_type = Column(String(20), default="正常")
    original_shift_id = Column(Integer, ForeignKey("shift_types.id"))
    notes = Column(String(200))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())