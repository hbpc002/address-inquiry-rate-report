from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class EmployeeBase(BaseModel):
    emp_no: str
    name: str
    team: str
    dept: Optional[str] = None
    role: str = "组员"


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    name: Optional[str] = None
    team: Optional[str] = None
    dept: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class EmployeeListResponse(BaseModel):
    items: list[EmployeeResponse]
    total: int