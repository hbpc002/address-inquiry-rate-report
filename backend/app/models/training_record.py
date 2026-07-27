from sqlalchemy import Column, Integer, String, Date, Text, DateTime
from sqlalchemy.sql import func
from app.models.database import Base


class TrainingRecord(Base):
    __tablename__ = "training_records"

    id = Column(Integer, primary_key=True, index=True)
    emp_no = Column(String(20), nullable=False, index=True)
    record_date = Column(Date, nullable=False, index=True)
    start_time = Column(String(5), nullable=False)
    end_time = Column(String(5), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    type = Column(String(20), nullable=False, default="培训")
    reason = Column(Text)
    created_by = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
