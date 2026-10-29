from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DepartmentGroupBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = ""
    is_active: bool = True


class DepartmentGroupCreate(DepartmentGroupBase):
    paths: list[str] = []


class DepartmentGroupUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    paths: Optional[list[str]] = None


class DepartmentGroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = ""
    is_active: bool = True
    paths: list[str] = []
    user_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DepartmentGroupListResponse(BaseModel):
    items: list[DepartmentGroupResponse]
    total: int
