from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.models.database import get_db
from app.models.field_annotation import FieldAnnotation
from app.schemas.field_annotation import (
    FieldAnnotationCreate,
    FieldAnnotationUpdate,
    FieldAnnotationResponse,
    FieldAnnotationListResponse,
)
from app.core.security import get_current_user, require_permission

router = APIRouter(prefix="/api/field-annotations", tags=["字段批注"])


@router.get("", response_model=FieldAnnotationListResponse)
def list_field_annotations(
    report_type: Optional[str] = Query(None, description="按报表类型筛选"),
    page: int = Query(1, ge=1),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "field_annotations.view")
    q = db.query(FieldAnnotation)
    if report_type:
        q = q.filter(FieldAnnotation.report_type == report_type)
    total = q.count()
    items = q.order_by(FieldAnnotation.sort_order, FieldAnnotation.id).offset(
        (page - 1) * limit
    ).limit(limit).all()
    return FieldAnnotationListResponse(items=items, total=total)


@router.get("/public", response_model=list[FieldAnnotationResponse])
def get_public_annotations(
    report_type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(FieldAnnotation)
    if report_type:
        q = q.filter(FieldAnnotation.report_type == report_type)
    return q.order_by(FieldAnnotation.sort_order, FieldAnnotation.id).all()


@router.post("", response_model=FieldAnnotationResponse)
def create_field_annotation(
    data: FieldAnnotationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "field_annotations.edit")
    annotation = FieldAnnotation(**data.model_dump())
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    return annotation


@router.put("/{annotation_id}", response_model=FieldAnnotationResponse)
def update_field_annotation(
    annotation_id: int,
    data: FieldAnnotationUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "field_annotations.edit")
    annotation = db.query(FieldAnnotation).filter(FieldAnnotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="字段批注不存在")
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(annotation, key, value)
    db.commit()
    db.refresh(annotation)
    return annotation


@router.delete("/{annotation_id}")
def delete_field_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "field_annotations.edit")
    annotation = db.query(FieldAnnotation).filter(FieldAnnotation.id == annotation_id).first()
    if not annotation:
        raise HTTPException(status_code=404, detail="字段批注不存在")
    db.delete(annotation)
    db.commit()
    return {"message": "已删除"}
