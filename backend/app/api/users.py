import io
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from urllib.parse import quote
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.models.database import get_db
from app.models.user import User
from app.models.role import Role
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse,
    UserListResponse, ChangePasswordRequest, SetPermissionsRequest
)
from app.core.security import get_current_user, get_password_hash, verify_password, check_permission, require_permission
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
    if not check_permission(current_user, "users.view"):
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

    result_items = []
    for u in items:
        role_name = u.role
        role_permissions = "{}"
        is_system = False
        if u.role_id:
            r = db.query(Role).filter(Role.id == u.role_id).first()
            if r:
                role_name = r.name
                role_permissions = r.permissions or "{}"
                is_system = r.is_system
        result_items.append(UserResponse(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            role=role_name,
            role_id=u.role_id,
            permissions=role_permissions,
            is_system=is_system,
            is_active=u.is_active,
            created_at=u.created_at,
        ))

    return UserListResponse(items=result_items, total=total)


@router.post("", response_model=dict)
def create_user(
    user: UserCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "users.manage"):
        raise HTTPException(status_code=403, detail="权限不足")

    existing = db.query(User).filter(User.username == user.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    role_id = user.role_id
    role_name = user.role
    if role_id:
        role = db.query(Role).filter(Role.id == role_id).first()
        if role:
            role_name = role.name

    db_user = User(
        username=user.username,
        password_hash=get_password_hash(user.password),
        display_name=user.display_name,
        role=role_name,
        role_id=role_id,
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
    if not check_permission(current_user, "users.manage"):
        raise HTTPException(status_code=403, detail="权限不足")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user_id == current_user["id"] and user.role_id is not None:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role and user.role_id != admin_role.id:
            raise HTTPException(status_code=400, detail="不能取消自己的管理员权限")

    update_data = user.model_dump(exclude_unset=True)
    if "role_id" in update_data and update_data["role_id"] is not None:
        role = db.query(Role).filter(Role.id == update_data["role_id"]).first()
        if role:
            update_data["role"] = role.name
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
    if not check_permission(current_user, "users.manage"):
        raise HTTPException(status_code=403, detail="权限不足")

    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="不能删除自己")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    db_user.is_active = False
    db.commit()
    log_operation(db, current_user["id"], "delete_user", "users", user_id, {"username": db_user.username})
    return {"message": "删除成功"}


@router.post("/{user_id}/enable", response_model=dict)
def enable_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "users.manage"):
        raise HTTPException(status_code=403, detail="权限不足")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if db_user.is_active:
        raise HTTPException(status_code=400, detail="用户已是启用状态")

    db_user.is_active = True
    db.commit()
    log_operation(db, current_user["id"], "enable_user", "users", user_id, {"username": db_user.username})
    return {"message": "启用成功"}


@router.post("/{user_id}/reset-password", response_model=dict)
def reset_password(
    user_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "users.manage"):
        raise HTTPException(status_code=403, detail="权限不足")

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
    if not check_permission(current_user, "users.manage"):
        raise HTTPException(status_code=403, detail="权限不足")

    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if not db_user.role_id:
        raise HTTPException(status_code=400, detail="用户没有关联角色，无法设置权限")

    import json
    role = db.query(Role).filter(Role.id == db_user.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    if role.is_system:
        raise HTTPException(status_code=400, detail="系统角色不允许修改权限")

    role.permissions = json.dumps(body.permissions, ensure_ascii=False)
    db.commit()
    log_operation(db, current_user["id"], "set_permissions", "roles", role.id, {"permissions": body.permissions})
    return {"message": "权限设置成功"}


@router.get("/roles", response_model=list)
def get_user_roles(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if not check_permission(current_user, "users.view"):
        raise HTTPException(status_code=403, detail="权限不足")
    from app.models.role import Role
    roles = db.query(Role).all()
    return [{"id": r.id, "name": r.name, "description": r.description, "is_system": r.is_system} for r in roles]


@router.post("/import", response_model=dict)
def import_users(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """批量导入用户Excel"""
    require_permission(current_user, "users.manage")

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传Excel文件(.xlsx或.xls)")

    import pandas as pd
    contents = file.file.read()
    try:
        xlsx = pd.ExcelFile(io.BytesIO(contents))
        df = pd.read_excel(xlsx, sheet_name=0)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法解析Excel文件: {str(e)}")

    cols = df.columns.tolist()
    required_cols = ['用户名', '密码']
    for col in required_cols:
        if col not in cols:
            raise HTTPException(status_code=400, detail=f"缺少必需列: {col}")

    role_cache = {}
    roles_list = db.query(Role).all()
    for r in roles_list:
        role_cache[r.name] = r

    created = 0
    skipped = 0
    errors = []

    for idx, row in df.iterrows():
        username = str(row.get('用户名', '')).strip()
        password = str(row.get('密码', '')).strip()
        display_name = str(row.get('显示名', '')).strip() if pd.notna(row.get('显示名')) else ''
        role_name = str(row.get('角色', '')).strip() if pd.notna(row.get('角色')) else ''

        if not username or not password or username == 'nan' or password == 'nan':
            skipped += 1
            continue

        existing = db.query(User).filter(User.username == username).first()
        if existing:
            errors.append(f"第{idx+2}行: 用户名'{username}'已存在")
            skipped += 1
            continue

        role_id = None
        if role_name:
            role = role_cache.get(role_name)
            if role:
                role_id = role.id
            else:
                role_cache[role_name] = None

        db_user = User(
            username=username,
            password_hash=get_password_hash(password),
            display_name=display_name or None,
            role=role_name or 'user',
            role_id=role_id,
        )
        db.add(db_user)
        created += 1

    db.commit()
    log_operation(db, current_user["id"], "import_users", "users", None, {"created": created, "skipped": skipped, "errors": errors})
    return {
        "message": "导入完成",
        "created": created,
        "skipped": skipped,
        "errors": errors
    }


@router.get("/import-template")
def download_import_template(
    current_user: dict = Depends(get_current_user)
):
    """下载用户导入模板"""
    require_permission(current_user, "users.manage")

    import pandas as pd
    df = pd.DataFrame(columns=['用户名', '密码', '显示名', '角色'])
    df.loc[0] = ['张三', 'password123', '张三', 'user']

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='用户导入模板')
    output.seek(0)

    filename = quote('用户导入模板.xlsx')
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"}
    )
