from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


class EmployeeBase(BaseModel):
    emp_no: str
    name: str
    team: str
    dept: Optional[str] = None
    role: str = "组员"
    hire_date: Optional[date] = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    emp_no: Optional[str] = None
    name: Optional[str] = None
    team: Optional[str] = None
    dept: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    hire_date: Optional[date] = None


class EmployeeResponse(EmployeeBase):
    id: int
    status: str
    deleted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int