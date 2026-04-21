from sqlalchemy import Column, Integer, String, DECIMAL, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.models.database import Base


class MonthlyReport(Base):
    __tablename__ = "monthly_reports"

    id = Column(Integer, primary_key=True, index=True)
    emp_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    year_month = Column(String(7), nullable=False, index=True)
    scheduled_hours = Column(DECIMAL(6, 1), default=0)
    actual_hours = Column(DECIMAL(6, 1), default=0)
    normal_days = Column(Integer, default=0)
    late_days = Column(Integer, default=0)
    early_days = Column(Integer, default=0)
    absent_days = Column(Integer, default=0)
    leave_days = Column(Integer, default=0)
    timeoff_days = Column(Integer, default=0)
    overtime_hours = Column(DECIMAL(6, 1), default=0)
    owed_hours = Column(DECIMAL(6, 1), default=0)
    calculated_at = Column(DateTime, server_default=func.now())