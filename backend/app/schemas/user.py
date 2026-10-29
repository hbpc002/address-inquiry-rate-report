from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    display_name: Optional[str] = None
    dept: Optional[str] = None
    department_group_id: Optional[int] = None
    department_group_name: Optional[str] = None
    department_group_paths: Optional[list[str]] = None
    role: str = "user"


class UserCreate(UserBase):
    password: str
    role_id: Optional[int] = None


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    dept: Optional[str] = None
    department_group_id: Optional[int] = None
    role: Optional[str] = None
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    id: int
    role_id: Optional[int] = None
    permissions: Optional[str] = "{}"
    data_scope: Optional[str] = "all"
    data_scope_config: Optional[str] = "{}"
    is_system: Optional[bool] = False
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class SetPermissionsRequest(BaseModel):
    permissions: dict