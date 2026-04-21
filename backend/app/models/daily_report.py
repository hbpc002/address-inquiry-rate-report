from sqlalchemy import Column, Integer, String, Date, DateTime, DECIMAL, Time, ForeignKey
from sqlalchemy.sql import func
from app.models.database import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    schedule_date = Column(Date, nullable=False, index=True)
    shift_type_id = Column(Integer, ForeignKey("shift_types.id"))
    schedule_type = Column(String(20))
    scheduled_start = Column(Time)
    scheduled_end = Column(Time)
    scheduled_hours = Column(DECIMAL(4, 1))
    actual_checkin = Column(DateTime)
    actual_checkout = Column(DateTime)
    actual_hours = Column(DECIMAL(4, 1))
    status = Column(String(20), index=True)
    late_minutes = Column(Integer, default=0)
    early_minutes = Column(Integer, default=0)
    overtime_hours = Column(DECIMAL(4, 1), default=0)
    calculated_at = Column(DateTime, server_default=func.now())