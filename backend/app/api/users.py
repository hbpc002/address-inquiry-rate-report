from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.models.database import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse,
    UserListResponse, ChangePasswordRequest, SetPermissionsRequest
)
from app.core.security import get_current_user, get_password_hash, verify_password
from app.utils.logger import log_operation

router = APIRouter(prefix="/api/users", tags=["用户管理"])


@router.get("", response_model=UserListResponse)
def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """获取用户列表"""
    if current_user.get("role") not in ["admin", "manager"]:
        raise HTTPException(status_code=403, detail="权限不足")
    
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if search:
        query = query.filter(
            (User.username.like(f"%{search}%")) |
            (User.display_name.like(f"%{search}%"))
        )

    total = query.count()
    items = query.order_by(User.id.desc()).offset((page-1)*limit).limit(limit).all()
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in items],
        total=total
    )


@router.post("", response_model=dict)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """创建用户"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可创建用户")
    
    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    db_user = User(
        username=user.username,
        password_hash=get_password_hash(user.password),
        display_name=user.display_name,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    log_operation(db, current_user["id"], "create_user", "users", db_user.id, {"username": user.username})
    return {"id": db_user.id}


@router.put("/{user_id}", response_model=dict)
def update_user(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """更新用户"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可编辑用户")
    
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 不能修改自己的admin权限
    if user_id == current_user["id"] and user.role and user.role != "admin":
        raise HTTPException(status_code=400, detail="不能取消自己的管理员权限")

    update_data = user.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    db.commit()
    log_operation(db, current_user["id"], "update_user", "users", user_id, {"fields": list(update_data.keys())})
    return {"id": db_user.id}


@router.delete("/{user_id}", response_model=dict)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """删除/禁用用户"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可删除用户")
    
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="不能删除自己")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    db_user.is_active = False
    db.commit()
    log_operation(db, current_user["id"], "delete_user", "users", user_id, {"username": db_user.username})
    return {"message": "删除成功"}


@router.post("/{user_id}/reset-password", response_model=dict)
def reset_password(
    user_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """重置密码"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可重置密码")
    
    new_password = body.get("new_password")
    if not new_password:
        raise HTTPException(status_code=400, detail="密码不能为空")
    
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    db_user.password_hash = get_password_hash(new_password)
    db.commit()
    log_operation(db, current_user["id"], "reset_password", "users", user_id, {"username": db_user.username})
    return {"message": "密码重置成功"}


@router.post("/me/change-password", response_model=dict)
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """用户自己修改密码"""
    db_user = db.query(User).filter(User.id == current_user["id"]).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not verify_password(body.old_password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")

    if len(body.new_password) < 3:
        raise HTTPException(status_code=400, detail="新密码长度至少3位")

    db_user.password_hash = get_password_hash(body.new_password)
    db.commit()
    log_operation(db, current_user["id"], "change_password", "users", db_user.id, {"username": db_user.username})
    return {"message": "密码修改成功"}


@router.post("/{user_id}/set-permissions", response_model=dict)
def set_permissions(
    user_id: int,
    body: SetPermissionsRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """管理员设置用户权限"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="仅管理员可设置权限")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    import json
    db_user.permissions = json.dumps(body.permissions, ensure_ascii=False)
    db.commit()
    log_operation(db, current_user["id"], "set_permissions", "users", user_id, {"permissions": body.permissions})
    return {"message": "权限设置成功"}
