from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, list
from datetime import date, datetime

from app.models.database import get_db
from app.models.training_record import TrainingRecord
from app.core.security import get_current_user, require_permission

router = APIRouter(prefix="/api/training-records", tags=["培训记录"])


class TrainingRecordItem(BaseModel):
    emp_no: str
    record_date: str
    start_time: str
    end_time: str
    type: str = "培训"
    reason: Optional[str] = None


class BatchCreateRequest(BaseModel):
    records: list[TrainingRecordItem]


class TrainingRecordResponse(BaseModel):
    id: int
    emp_no: str
    record_date: str
    start_time: str
    end_time: str
    duration_minutes: int
    type: str
    reason: Optional[str] = None
    created_by: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


def _duration_minutes(start: str, end: str) -> int:
    sh, sm = map(int, start.split(':'))
    eh, em = map(int, end.split(':'))
    return max(0, (eh * 60 + em) - (sh * 60 + sm))


@router.get("")
def list_training_records(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    emp_no: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "training_records.view")
    query = db.query(TrainingRecord)
    if start_date:
        query = query.filter(TrainingRecord.record_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(TrainingRecord.record_date <= datetime.strptime(end_date, "%Y-%m-%d").date())
    if emp_no:
        query = query.filter(TrainingRecord.emp_no == emp_no)
    if type:
        query = query.filter(TrainingRecord.type == type)
    records = query.order_by(TrainingRecord.record_date.desc(), TrainingRecord.emp_no).all()
    total_minutes = sum(r.duration_minutes for r in records)
    return {
        "total": len(records),
        "total_minutes": total_minutes,
        "items": [
            {
                "id": r.id,
                "emp_no": r.emp_no,
                "record_date": r.record_date.isoformat() if r.record_date else None,
                "start_time": r.start_time,
                "end_time": r.end_time,
                "duration_minutes": r.duration_minutes,
                "type": r.type,
                "reason": r.reason,
                "created_by": r.created_by,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in records
        ]
    }


@router.post("/batch")
def batch_create(
    data: BatchCreateRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "training_records.create")
    created = []
    for item in data.records:
        d = datetime.strptime(item.record_date, "%Y-%m-%d").date()
        minutes = _duration_minutes(item.start_time, item.end_time)
        record = TrainingRecord(
            emp_no=item.emp_no,
            record_date=d,
            start_time=item.start_time,
            end_time=item.end_time,
            duration_minutes=minutes,
            type=item.type,
            reason=item.reason,
            created_by=current_user.get("display_name") or current_user.get("username"),
        )
        db.add(record)
        created.append(record)
    db.commit()
    return {
        "message": f"成功创建 {len(created)} 条记录",
        "count": len(created)
    }


@router.delete("/{record_id}")
def delete_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "training_records.delete")
    record = db.query(TrainingRecord).filter(TrainingRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    return {"message": "删除成功"}
