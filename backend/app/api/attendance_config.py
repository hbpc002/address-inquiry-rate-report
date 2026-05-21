from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.database import get_db
from app.models.attendance_config import AttendanceConfig
from app.core.security import get_current_user, require_permission, require_role

router = APIRouter(prefix="/api/attendance-config", tags=["考勤配置"])


class AttendanceConfigResponse(BaseModel):
    late_threshold_minutes: int = 30
    early_leave_threshold_minutes: int = 30

    class Config:
        from_attributes = True


class AttendanceConfigUpdate(BaseModel):
    late_threshold_minutes: Optional[int] = None
    early_leave_threshold_minutes: Optional[int] = None


def _get_config_value(db: Session, key: str, default: str) -> str:
    row = db.query(AttendanceConfig).filter(AttendanceConfig.key == key).first()
    return row.value if row else default


def _set_config_value(db: Session, key: str, value: str):
    row = db.query(AttendanceConfig).filter(AttendanceConfig.key == key).first()
    if row:
        row.value = value
    else:
        row = AttendanceConfig(key=key, value=value)
        db.add(row)


@router.get("", response_model=AttendanceConfigResponse)
def get_attendance_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    late = int(_get_config_value(db, "late_threshold_minutes", "30"))
    early = int(_get_config_value(db, "early_leave_threshold_minutes", "30"))
    return AttendanceConfigResponse(
        late_threshold_minutes=late,
        early_leave_threshold_minutes=early
    )


@router.put("", response_model=AttendanceConfigResponse)
def update_attendance_config(
    data: AttendanceConfigUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_role(current_user, ["admin", "manager"])
    require_permission(current_user, "manage_threshold")

    if data.late_threshold_minutes is not None:
        _set_config_value(db, "late_threshold_minutes", str(data.late_threshold_minutes))
    if data.early_leave_threshold_minutes is not None:
        _set_config_value(db, "early_leave_threshold_minutes", str(data.early_leave_threshold_minutes))

    db.commit()

    late = int(_get_config_value(db, "late_threshold_minutes", "30"))
    early = int(_get_config_value(db, "early_leave_threshold_minutes", "30"))
    return AttendanceConfigResponse(
        late_threshold_minutes=late,
        early_leave_threshold_minutes=early
    )