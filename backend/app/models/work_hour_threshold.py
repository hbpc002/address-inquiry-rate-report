from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.models.database import Base


class WorkHourThreshold(Base):
    __tablename__ = "work_hour_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    team = Column(String(50), nullable=False, index=True)
    overtime_ratio = Column(Float, default=1.2)
    undertime_ratio = Column(Float, default=0.8)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())