from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List

from app.models.database import get_db
from app.models.work_hour_threshold import WorkHourThreshold
from app.core.security import get_current_user, require_permission

router = APIRouter(prefix="/api/work-hour-thresholds", tags=["工时预警阈值"])


class ThresholdResponse(BaseModel):
    id: int
    team: str
    overtime_ratio: float
    undertime_ratio: float

    class Config:
        from_attributes = True


class ThresholdCreate(BaseModel):
    team: str
    overtime_ratio: float = 1.2
    undertime_ratio: float = 0.8


class ThresholdUpdate(BaseModel):
    overtime_ratio: Optional[float] = None
    undertime_ratio: Optional[float] = None


@router.get("", response_model=List[ThresholdResponse])
def get_thresholds(
    team: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(WorkHourThreshold)
    if team:
        query = query.filter(WorkHourThreshold.team == team)
    return query.order_by(WorkHourThreshold.team).all()


@router.post("", response_model=ThresholdResponse)
def create_threshold(
    data: ThresholdCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "work_hour_settings.create")
    
    existing = db.query(WorkHourThreshold).filter(
        WorkHourThreshold.team == data.team
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该班组阈值已存在")
    
    threshold = WorkHourThreshold(
        team=data.team,
        overtime_ratio=data.overtime_ratio,
        undertime_ratio=data.undertime_ratio,
        created_by=current_user["id"]
    )
    db.add(threshold)
    db.commit()
    db.refresh(threshold)
    return threshold


@router.put("/{threshold_id}", response_model=ThresholdResponse)
def update_threshold(
    threshold_id: int,
    data: ThresholdUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "work_hour_settings.edit")
    
    threshold = db.query(WorkHourThreshold).filter(
        WorkHourThreshold.id == threshold_id
    ).first()
    if not threshold:
        raise HTTPException(status_code=404, detail="阈值配置不存在")
    
    if data.overtime_ratio is not None:
        threshold.overtime_ratio = data.overtime_ratio
    if data.undertime_ratio is not None:
        threshold.undertime_ratio = data.undertime_ratio
    
    db.commit()
    db.refresh(threshold)
    return threshold


@router.delete("/{threshold_id}")
def delete_threshold(
    threshold_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "work_hour_settings.delete")
    
    threshold = db.query(WorkHourThreshold).filter(
        WorkHourThreshold.id == threshold_id
    ).first()
    if not threshold:
        raise HTTPException(status_code=404, detail="阈值配置不存在")
    
    db.delete(threshold)
    db.commit()
    return {"message": "删除成功"}


@router.get("/teams")
def get_teams_with_threshold(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from app.models.employee import Employee
    
    teams = db.query(Employee.team).distinct().all()
    teams = [t[0] for t in teams if t[0]]
    
    thresholds = db.query(WorkHourThreshold).all()
    threshold_map = {t.team: {"overtime": t.overtime_ratio, "undertime": t.undertime_ratio} for t in thresholds}
    
    result = []
    for team in teams:
        result.append({
            "team": team,
            "has_threshold": team in threshold_map,
            "overtime_ratio": threshold_map.get(team, {}).get("overtime", 1.2),
            "undertime_ratio": threshold_map.get(team, {}).get("undertime", 0.8)
        })
    
    return result