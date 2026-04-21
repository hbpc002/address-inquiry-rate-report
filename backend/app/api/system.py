from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime
from app.models.database import get_db
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.operation_log import OperationLog
from app.core.security import get_current_user
from typing import Optional

router = APIRouter(prefix="/api", tags=["系统管理"])


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    today = datetime.now().date()
    
    employee_count = db.query(Employee).filter(Employee.status == "在职").count()
    
    today_reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).all()
    today_attendance = len([r for r in today_reports if r.status == "正常"])
    today_late = len([r for r in today_reports if r.status == "迟到"])
    today_absent = len([r for r in today_reports if r.status == "缺勤"])
    
    return {
        "employee_count": employee_count,
        "today_attendance": today_attendance,
        "today_late": today_late,
        "today_absent": today_absent
    }


@router.get("/logs")
def get_logs(
    page: int = 1,
    limit: int = 20,
    user_id: Optional[int] = None,
    operation: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(OperationLog)
    if user_id:
        query = query.filter(OperationLog.user_id == user_id)
    if operation:
        query = query.filter(OperationLog.operation_type.like(f"%{operation}%"))
    
    total = query.count()
    items = query.order_by(OperationLog.created_at.desc()).offset((page-1)*limit).limit(limit).all()
    
    return {
        "items": [
            {
                "id": i.id,
                "user_id": i.user_id,
                "operation_type": i.operation_type,
                "target_table": i.target_table,
                "target_id": i.target_id,
                "details": i.details,
                "created_at": i.created_at.isoformat() if i.created_at else None
            }
            for i in items
        ],
        "total": total
    }


@router.get("/departments")
def get_departments(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    results = db.query(Employee.dept, func.count(Employee.id)).filter(
        Employee.status == "在职"
    ).group_by(Employee.dept).all()
    return [{"dept": r[0] or "未设置", "count": r[1]} for r in results if r[0]]


@router.get("/teams")
def get_teams(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    results = db.query(Employee.team, func.count(Employee.id)).filter(
        Employee.status == "在职"
    ).group_by(Employee.team).all()
    return [{"team": r[0], "count": r[1]} for r in results if r[0]]


@router.delete("/clear-data")
def clear_data(
    tables: str = Query(..., description="要清空的表，多个用逗号分隔: employees,schedules,checkins,daily_reports"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """清空指定表的数据"""
    table_map = {
        "employees": Employee,
        "schedules": Schedule,
        "checkins": Checkin,
        "daily_reports": DailyReport
    }
    
    result = {}
    for name in tables.split(","):
        name = name.strip()
        if name in table_map:
            try:
                count = db.query(table_map[name]).delete()
                result[name] = count
            except Exception as e:
                result[name] = f"error: {str(e)}"
    
    db.commit()
    return {"message": "数据已清空", "result": result}