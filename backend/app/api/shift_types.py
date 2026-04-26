from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.shift_type import ShiftType
from app.schemas.shift_type import (
    ShiftTypeCreate, ShiftTypeUpdate, ShiftTypeResponse
)
from app.core.security import get_current_user
from app.utils.logger import log_operation
from typing import List

router = APIRouter(prefix="/api/shift-types", tags=["班次类型管理"])


@router.get("", response_model=List[ShiftTypeResponse])
def get_shift_types(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    return db.query(ShiftType).filter(ShiftType.is_active == True).all()


@router.post("", response_model=dict)
def create_shift_type(
    shift_type: ShiftTypeCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    existing = db.query(ShiftType).filter(ShiftType.shift_name == shift_type.shift_name).first()
    if existing:
        raise HTTPException(status_code=400, detail="班次名称已存在")

    db_shift_type = ShiftType(**shift_type.model_dump())
    db.add(db_shift_type)
    db.commit()
    db.refresh(db_shift_type)
    log_operation(db, current_user["id"], "create_shift_type", "shift_types", db_shift_type.id, {"shift_name": shift_type.shift_name})
    return {"id": db_shift_type.id}


@router.put("/{shift_type_id}", response_model=dict)
def update_shift_type(
    shift_type_id: int,
    shift_type: ShiftTypeUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_shift_type = db.query(ShiftType).filter(ShiftType.id == shift_type_id).first()
    if not db_shift_type:
        raise HTTPException(status_code=404, detail="班次类型不存在")

    for key, value in shift_type.model_dump(exclude_unset=True).items():
        setattr(db_shift_type, key, value)
    db.commit()
    log_operation(db, current_user["id"], "update_shift_type", "shift_types", shift_type_id, {"changes": list(shift_type.model_dump(exclude_unset=True).keys())})
    return {"id": db_shift_type.id}


@router.delete("/{shift_type_id}", response_model=dict)
def delete_shift_type(
    shift_type_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_shift_type = db.query(ShiftType).filter(ShiftType.id == shift_type_id).first()
    if not db_shift_type:
        raise HTTPException(status_code=404, detail="班次类型不存在")

    db_shift_type.is_active = False
    db.commit()
    log_operation(db, current_user["id"], "delete_shift_type", "shift_types", shift_type_id, {"shift_name": db_shift_type.shift_name})
    return {"message": "删除成功"}
