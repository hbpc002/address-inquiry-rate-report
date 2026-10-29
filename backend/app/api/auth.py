from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.models.database import get_db
from app.models.user import User
from app.models.role import Role
from app.models.department_group import DepartmentGroup
from app.schemas.user import LoginRequest, TokenResponse, UserResponse
from app.core.security import verify_password, create_access_token, get_current_user
from app.core.config import settings
from app.utils.logger import log_operation

router = APIRouter(prefix="/api/auth", tags=["认证"])


@router.post("/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    role_permissions = "{}"
    role_name = user.role
    is_system = False
    data_scope = "all"
    data_scope_config = "{}"
    employee_write_scope = "dept"
    if user.role_id:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if role:
            role_permissions = role.permissions or "{}"
            role_name = role.name
            is_system = role.is_system
            data_scope = role.data_scope or "all"
            data_scope_config = role.data_scope_config or "{}"
            employee_write_scope = role.employee_write_scope or "dept"
    group = None
    group_paths = []
    if user.department_group_id:
        group = db.query(DepartmentGroup).filter(DepartmentGroup.id == user.department_group_id).first()
        if group:
            group_paths = [item.path for item in group.paths]

    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    log_operation(db, user.id, "login", "users", user.id, {"username": user.username})
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            username=user.username,
            display_name=user.display_name,
            dept=user.dept,
            department_group_id=user.department_group_id,
            department_group_name=group.name if group else None,
            department_group_paths=group_paths,
            role=role_name,
            role_id=user.role_id,
            permissions=role_permissions,
            data_scope=data_scope,
            data_scope_config=data_scope_config,
            employee_write_scope=employee_write_scope,
            is_system=is_system,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.post("/logout")
def logout(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    log_operation(db, current_user["id"], "logout", "users", current_user["id"])
    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
def get_me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    role_permissions = "{}"
    role_name = user.role
    is_system = False
    data_scope = "all"
    data_scope_config = "{}"
    employee_write_scope = "dept"
    if user.role_id:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if role:
            role_permissions = role.permissions or "{}"
            role_name = role.name
            is_system = role.is_system
            data_scope = role.data_scope or "all"
            data_scope_config = role.data_scope_config or "{}"
            employee_write_scope = role.employee_write_scope or "dept"
    group = None
    group_paths = []
    if user.department_group_id:
        group = db.query(DepartmentGroup).filter(DepartmentGroup.id == user.department_group_id).first()
        if group:
            group_paths = [item.path for item in group.paths]

    if not is_system and user.role == "admin":
        is_system = True

    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        dept=user.dept,
        department_group_id=user.department_group_id,
        department_group_name=group.name if group else None,
        department_group_paths=group_paths,
        role=role_name,
        role_id=user.role_id,
        permissions=role_permissions,
        data_scope=data_scope,
        data_scope_config=data_scope_config,
        employee_write_scope=employee_write_scope,
        is_system=is_system,
        is_active=user.is_active,
        created_at=user.created_at,
    )