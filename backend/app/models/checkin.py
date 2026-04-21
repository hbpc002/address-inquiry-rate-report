from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.models.database import Base


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    emp_no = Column(String(20), nullable=False, index=True)
    name = Column(String(50))
    checkin_time = Column(DateTime, nullable=False, index=True)
    checkout_time = Column(DateTime)
    device_no = Column(String(50))
    dept = Column(String(100))
    import_batch = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())