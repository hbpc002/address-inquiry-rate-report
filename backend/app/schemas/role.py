from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: Optional[str] = ""
    permissions: dict = {}
    data_scope: str = "all"
    data_scope_config: dict = {}
    employee_write_scope: str = "dept"


class RoleUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = None
    permissions: Optional[dict] = None
    data_scope: Optional[str] = None
    data_scope_config: Optional[dict] = None
    employee_write_scope: Optional[str] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = ""
    permissions: str = "{}"
    data_scope: str = "all"
    data_scope_config: str = "{}"
    employee_write_scope: str = "dept"
    is_system: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleAssignUsers(BaseModel):
    user_ids: list[int]


class RoleListResponse(BaseModel):
    items: list[RoleResponse]
    total: int
