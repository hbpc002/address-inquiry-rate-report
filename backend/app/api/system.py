from fastapi import APIRouter, Depends, Query, HTTPException, Body
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
from app.models.database import get_db
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.operation_log import OperationLog
from app.utils.logger import log_operation
try:
    from app.models.app_config import AppConfig
    _DB_CONFIG = True
except Exception:
    _DB_CONFIG = False
    _AUTO_CONFIG = {'enabled': True, 'retention_days': 90}
from app.core.security import get_current_user, require_permission

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


@router.get("/logs/export")
def export_logs_csv(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    limit: int = 1000,
    user_id: Optional[int] = None,
    operation: Optional[str] = None,
):
    """导出操作日志为CSV"""
    query = db.query(OperationLog)
    if user_id:
        query = query.filter(OperationLog.user_id == user_id)
    if operation:
        query = query.filter(OperationLog.operation_type.like(f"%{operation}%"))

    items = query.order_by(OperationLog.created_at.desc()).offset((page-1)*limit).limit(limit).all()

    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_id", "operation_type", "target_table", "target_id", "details", "created_at"])
    for i in items:
        writer.writerow([i.id, i.user_id, i.operation_type, i.target_table, i.target_id, i.details, i.created_at.isoformat() if i.created_at else ""])
    output.seek(0)
    filename = "operation_logs.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/logs/cleanup", response_model=dict)
def manual_cleanup_logs(
    months: int = Body(..., embed=True),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if months < 1 or months > 6:
        raise HTTPException(status_code=400, detail="retention months must be between 1 and 6")
    cutoff = datetime.utcnow() - timedelta(days=months * 30)
    deleted = db.query(OperationLog).filter(OperationLog.created_at < cutoff).delete()
    db.commit()
    log_operation(db, current_user["id"], "manual_cleanup", "system", None, {"months": months, "deleted": deleted})
    return {"deleted": deleted, "cutoff": cutoff.isoformat()}


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
    require_permission(current_user, "clear_data")
    
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
    log_operation(db, current_user["id"], "clear_data", "system", None, {"tables": tables})
    return {"message": "数据已清空", "result": result}


class LogConfig(BaseModel):
    enable_autoclean: bool
    retention_months: int


@router.get("/logs/config", response_model=dict)
def get_log_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    if _DB_CONFIG:
        conf_en = True
        conf_ret_days = 90
        en = db.query(AppConfig).filter(AppConfig.key == 'log_autoclean_enabled').first()
        if en and getattr(en, 'value', None):
            conf_en = en.value.lower() == 'true'
        r = db.query(AppConfig).filter(AppConfig.key == 'log_retention_days').first()
        if r and r.value and str(r.value).isdigit():
            conf_ret_days = int(r.value)
        conf_ret_months = max(1, min(6, int(conf_ret_days / 30)))
        return {
            "enable_autoclean": conf_en,
            "retention_months": conf_ret_months
        }
    else:
        return {
            "enable_autoclean": _AUTO_CONFIG.get('enabled', True),
            "retention_months": max(1, min(6, int(_AUTO_CONFIG.get('retention_days', 90) / 30)))
        }


@router.post("/logs/config", response_model=dict)
def set_log_config(
    cfg: LogConfig,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # validate range
    if not (1 <= cfg.retention_months <= 6):
        raise HTTPException(status_code=400, detail="retention_months 必须在 1-6 之间")
    if _DB_CONFIG:
        # upsert config values in DB
        def _upsert(key: str, value: str):
            rec = db.query(AppConfig).filter(AppConfig.key == key).first()
            if rec:
                rec.value = value
            else:
                db.add(AppConfig(key=key, value=value))
            db.commit()

        _upsert('log_autoclean_enabled', 'true' if cfg.enable_autoclean else 'false')
        days = cfg.retention_months * 30
        _upsert('log_retention_days', str(days))
    else:
        _AUTO_CONFIG['enabled'] = bool(cfg.enable_autoclean)
        _AUTO_CONFIG['retention_days'] = cfg.retention_months * 30
    return {
        "enable_autoclean": cfg.enable_autoclean,
        "retention_months": cfg.retention_months
    }
