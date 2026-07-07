from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.models.database import Base


class SalaryConfig(Base):
    __tablename__ = "salary_configs"

    id = Column(Integer, primary_key=True, index=True)
    rule_key = Column(String(50), nullable=False, unique=True, index=True)
    rule_data = Column(String(2000), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
