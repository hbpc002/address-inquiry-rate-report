from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_permission
from app.models.database import get_db
from app.models.department_group import DepartmentGroup, DepartmentGroupPath
from app.models.user import User
from app.schemas.department_group import (
    DepartmentGroupCreate,
    DepartmentGroupListResponse,
    DepartmentGroupResponse,
    DepartmentGroupUpdate,
)

router = APIRouter(prefix="/api/department-groups", tags=["部门设置"])


def _clean_paths(paths: list[str]) -> list[str]:
    result = []
    for path in paths or []:
        value = str(path or "").strip()
        if value and value not in result:
            result.append(value)
    return result


def _to_response(db: Session, group: DepartmentGroup) -> DepartmentGroupResponse:
    return DepartmentGroupResponse(
        id=group.id,
        name=group.name,
        description=group.description or "",
        is_active=group.is_active,
        paths=[item.path for item in group.paths],
        user_count=db.query(User).filter(User.department_group_id == group.id).count(),
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


def _ensure_name_available(db: Session, name: str, exclude_id: int | None = None):
    query = db.query(DepartmentGroup).filter(DepartmentGroup.name == name)
    if exclude_id is not None:
        query = query.filter(DepartmentGroup.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=400, detail="部门组名称已存在")


@router.get("", response_model=DepartmentGroupListResponse)
def list_department_groups(
    keyword: str = Query(default=""),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "department_groups.view")
    query = db.query(DepartmentGroup)
    if keyword:
        query = query.filter(DepartmentGroup.name.like(f"%{keyword}%"))
    items = query.order_by(DepartmentGroup.id).all()
    return DepartmentGroupListResponse(
        items=[_to_response(db, item) for item in items],
        total=len(items),
    )


@router.get("/options", response_model=list)
def department_group_options(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "department_groups.view")
    groups = db.query(DepartmentGroup).filter(DepartmentGroup.is_active.is_(True)).order_by(DepartmentGroup.name).all()
    return [
        {
            "id": group.id,
            "name": group.name,
            "paths": [item.path for item in group.paths],
        }
        for group in groups
    ]


@router.get("/{group_id}", response_model=DepartmentGroupResponse)
def get_department_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "department_groups.view")
    group = db.query(DepartmentGroup).filter(DepartmentGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="部门组不存在")
    return _to_response(db, group)


@router.post("", response_model=dict)
def create_department_group(
    body: DepartmentGroupCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "department_groups.manage")
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="部门组名称不能为空")
    _ensure_name_available(db, name)
    paths = _clean_paths(body.paths)
    if not paths:
        raise HTTPException(status_code=400, detail="请至少配置一个组织路径")

    group = DepartmentGroup(name=name, description=body.description or "", is_active=body.is_active)
    db.add(group)
    db.flush()
    for path in paths:
        db.add(DepartmentGroupPath(group_id=group.id, path=path))
    db.commit()
    db.refresh(group)
    return {"id": group.id}


@router.put("/{group_id}", response_model=dict)
def update_department_group(
    group_id: int,
    body: DepartmentGroupUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "department_groups.manage")
    group = db.query(DepartmentGroup).filter(DepartmentGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="部门组不存在")

    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="部门组名称不能为空")
        _ensure_name_available(db, name, exclude_id=group_id)
        group.name = name
    if "description" in data:
        group.description = data["description"] or ""
    if "is_active" in data:
        group.is_active = data["is_active"]
    if "paths" in data:
        paths = _clean_paths(data["paths"] or [])
        if not paths:
            raise HTTPException(status_code=400, detail="请至少配置一个组织路径")
        db.query(DepartmentGroupPath).filter(DepartmentGroupPath.group_id == group.id).delete(
            synchronize_session=False
        )
        for path in paths:
            db.add(DepartmentGroupPath(group_id=group.id, path=path))

    db.commit()
    return {"id": group.id}


@router.delete("/{group_id}", response_model=dict)
def delete_department_group(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "department_groups.manage")
    group = db.query(DepartmentGroup).filter(DepartmentGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="部门组不存在")
    user_count = db.query(User).filter(User.department_group_id == group_id).count()
    if user_count:
        raise HTTPException(status_code=400, detail=f"该部门组下还有 {user_count} 个用户，无法删除")
    db.delete(group)
    db.commit()
    return {"message": "删除成功"}
