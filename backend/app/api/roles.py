from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.models.database import get_db
from app.models.role import Role
from app.models.user import User
from app.models.department_group import DepartmentGroup
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse, RoleListResponse, RoleAssignUsers
from app.core.security import get_current_user, check_permission
from app.core.permissions import get_all_permission_keys
from app.core.data_scope import DATA_SCOPE_MODULES
import json


def _clean_scope_config(config: dict) -> dict:
    cleaned = {}
    for key, value in (config or {}).items():
        if key in DATA_SCOPE_MODULES and value in ("all", "dept"):
            cleaned[key] = value
    return cleaned


def _assignment_user(db: Session, user: User) -> dict:
    group = None
    if user.department_group_id:
        group = db.query(DepartmentGroup).filter(DepartmentGroup.id == user.department_group_id).first()
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "dept": user.dept,
        "department_group_id": user.department_group_id,
        "department_group_name": group.name if group else None,
        "department_group_paths": [item.path for item in group.paths] if group else [],
    }

router = APIRouter(prefix="/api/roles", tags=["角色管理"])


@router.get("", response_model=RoleListResponse)
def get_roles(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "roles.view"):
        raise HTTPException(status_code=403, detail="权限不足")

    total = db.query(Role).count()
    items = db.query(Role).order_by(Role.id).offset((page-1)*limit).limit(limit).all()
    return RoleListResponse(items=[RoleResponse.model_validate(r) for r in items], total=total)


@router.get("/all", response_model=list)
def get_all_roles(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "roles.view"):
        raise HTTPException(status_code=403, detail="权限不足")
    items = db.query(Role).order_by(Role.id).all()
    return [RoleResponse.model_validate(r) for r in items]


@router.post("", response_model=dict)
def create_role(
    role: RoleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "roles.manage"):
        raise HTTPException(status_code=403, detail="权限不足")

    existing = db.query(Role).filter(Role.name == role.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色名称已存在")
    if role.data_scope not in ("all", "dept"):
        raise HTTPException(status_code=400, detail="无效的数据范围")
    if role.employee_write_scope not in ("all", "dept"):
        raise HTTPException(status_code=400, detail="无效的员工编辑范围")

    valid_keys = set(get_all_permission_keys())
    perms = {}
    for k, v in role.permissions.items():
        if k in valid_keys:
            perms[k] = v

    db_role = Role(
        name=role.name,
        description=role.description or "",
        permissions=json.dumps(perms, ensure_ascii=False),
        data_scope=role.data_scope,
        data_scope_config=json.dumps(_clean_scope_config(role.data_scope_config), ensure_ascii=False),
        employee_write_scope=role.employee_write_scope,
    )
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return {"id": db_role.id}


@router.put("/{role_id}", response_model=dict)
def update_role(
    role_id: int,
    role: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "roles.manage"):
        raise HTTPException(status_code=403, detail="权限不足")

    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if db_role.is_system:
        raise HTTPException(status_code=400, detail="系统角色不允许修改")

    update_data = role.model_dump(exclude_unset=True)
    if "data_scope" in update_data and update_data["data_scope"] not in ("all", "dept"):
        raise HTTPException(status_code=400, detail="无效的数据范围")
    if "employee_write_scope" in update_data and update_data["employee_write_scope"] not in ("all", "dept"):
        raise HTTPException(status_code=400, detail="无效的员工编辑范围")
    if "data_scope_config" in update_data:
        update_data["data_scope_config"] = json.dumps(
            _clean_scope_config(update_data["data_scope_config"] or {}), ensure_ascii=False
        )
    if "permissions" in update_data:
        valid_keys = set(get_all_permission_keys())
        perms = {}
        for k, v in update_data["permissions"].items():
            if k in valid_keys:
                perms[k] = v
        update_data["permissions"] = json.dumps(perms, ensure_ascii=False)
    old_name = db_role.name
    for key, value in update_data.items():
        setattr(db_role, key, value)
    if db_role.name != old_name:
        db.query(User).filter(User.role_id == db_role.id).update(
            {"role": db_role.name}, synchronize_session=False
        )
    db.commit()
    return {"id": db_role.id}


@router.delete("/{role_id}", response_model=dict)
def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "roles.manage"):
        raise HTTPException(status_code=403, detail="权限不足")

    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if db_role.is_system:
        raise HTTPException(status_code=400, detail="系统角色不允许删除")

    users_with_role = db.query(User).filter(User.role_id == role_id).count()
    if users_with_role > 0:
        raise HTTPException(status_code=400, detail=f"该角色下有 {users_with_role} 个用户，无法删除")

    db.delete(db_role)
    db.commit()
    return {"message": "删除成功"}


@router.get("/{role_id}/users", response_model=list)
def get_role_users(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "roles.view"):
        raise HTTPException(status_code=403, detail="权限不足")

    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="角色不存在")

    users = db.query(User).filter(User.role_id == role_id).all()
    return [_assignment_user(db, u) for u in users]


@router.get("/all-users", response_model=list)
def get_all_users_for_assignment(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "roles.manage"):
        raise HTTPException(status_code=403, detail="权限不足")

    users = db.query(User).all()
    return [_assignment_user(db, u) for u in users]


@router.put("/{role_id}/users", response_model=dict)
def assign_role_users(
    role_id: int,
    body: RoleAssignUsers,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "roles.manage"):
        raise HTTPException(status_code=403, detail="权限不足")

    db_role = db.query(Role).filter(Role.id == role_id).first()
    if not db_role:
        raise HTTPException(status_code=404, detail="角色不存在")

    user_ids = body.user_ids

    previously_assigned = db.query(User).filter(User.role_id == role_id).all()
    prev_ids = {u.id for u in previously_assigned}
    new_ids = set(user_ids)

    to_remove = prev_ids - new_ids
    if to_remove:
        db.query(User).filter(User.id.in_(to_remove)).update(
            {"role_id": None, "role": "user"}, synchronize_session=False
        )

    to_add = new_ids - prev_ids
    if to_add:
        db.query(User).filter(User.id.in_(to_add)).update(
            {"role_id": role_id, "role": db_role.name}, synchronize_session=False
        )

    already_assigned = prev_ids & new_ids
    if already_assigned:
        db.query(User).filter(User.id.in_(already_assigned), User.role != db_role.name).update(
            {"role": db_role.name}, synchronize_session=False
        )

    db.commit()
    return {"message": "分配成功"}


@router.get("/permissions", response_model=dict)
def get_permission_registry(
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "roles.view"):
        raise HTTPException(status_code=403, detail="权限不足")
    from app.core.permissions import PERMISSION_REGISTRY
    return PERMISSION_REGISTRY