from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.models.database import Base


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    emp_no = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    team = Column(String(50), nullable=False, index=True)
    dept = Column(String(100), index=True)
    role = Column(String(20), default="组员")
    status = Column(String(20), default="在职", index=True)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())