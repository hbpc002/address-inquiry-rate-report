from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    permissions: dict = {}


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    permissions: Optional[dict] = None


class RoleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = ""
    permissions: str = "{}"
    is_system: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RoleListResponse(BaseModel):
    items: list[RoleResponse]
    total: int
