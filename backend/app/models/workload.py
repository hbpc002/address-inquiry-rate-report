from sqlalchemy import Column, Integer, String, Date, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSON
from app.models.database import Base


class Workload(Base):
    __tablename__ = "workloads"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    province = Column(String(50))
    account = Column(String(50), nullable=False, index=True)
    name = Column(String(50))
    emp_no = Column(String(50))
    team_desc = Column(String(200))
    metrics = Column(JSON, default={})
    import_batch = Column(String(50), nullable=False, index=True)
    created_at = Column(DateTime, server_default=func.now())
