from fastapi import APIRouter, Depends, Query, HTTPException, Body
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from datetime import datetime, timedelta, date
from calendar import monthrange
from app.models.database import get_db
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.shift_type import ShiftType
from app.models.operation_log import OperationLog
from app.models.user import User
from app.utils.logger import log_operation
from app.models.attendance_config import AttendanceConfig
try:
    from app.models.app_config import AppConfig
    _DB_CONFIG = True
except Exception:
    _DB_CONFIG = False
    _AUTO_CONFIG = {'enabled': True, 'retention_days': 90}
from app.core.security import get_current_user, require_permission

router = APIRouter(prefix="/api", tags=["系统管理"])


def _get_ym() -> tuple:
    now = datetime.now()
    return now.year, now.month


def _get_long_hour_threshold(db: Session) -> float:
    config = db.query(AttendanceConfig).filter(AttendanceConfig.key == "long_hour_threshold").first()
    if config and config.value:
        try:
            return float(config.value)
        except ValueError:
            pass
    return 9.5


@router.get("/stats")
def get_stats(
    year_month: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    employee_count = db.query(Employee).filter(Employee.status == "在职").count()

    latest_date = db.query(func.max(DailyReport.schedule_date)).scalar()

    if year_month:
        parts = year_month.split("-")
        year, month = int(parts[0]), int(parts[1])
    else:
        year, month = _get_ym()

    month_reports = db.query(DailyReport).filter(
        extract("year", DailyReport.schedule_date) == year,
        extract("month", DailyReport.schedule_date) == month,
    ).all()

    monthly_total = len(month_reports)
    monthly_normal = len([r for r in month_reports if r.status == "正常"])
    monthly_late = len([r for r in month_reports if r.status == "迟到"])
    monthly_absent = len([r for r in month_reports if r.status == "缺勤"])
    monthly_leave = len([r for r in month_reports if r.status == "请假"])
    monthly_timeoff = len([r for r in month_reports if r.status == "休息"])
    monthly_actual_hours = sum(float(r.actual_hours or 0) for r in month_reports)
    monthly_scheduled_hours = sum(float(r.scheduled_hours or 0) for r in month_reports)
    monthly_overtime_hours = sum(float(r.overtime_hours or 0) for r in month_reports)

    latest_reports = []
    if latest_date:
        latest_reports = db.query(DailyReport).filter(DailyReport.schedule_date == latest_date).all()
    latest_attendance = len([r for r in latest_reports if r.status in ("正常", "迟到", "早退", "加班")])
    latest_late = len([r for r in latest_reports if r.status == "迟到"])
    latest_absent = len([r for r in latest_reports if r.status == "缺勤"])
    latest_leave = len([r for r in latest_reports if r.status == "请假"])
    latest_timeoff = len([r for r in latest_reports if r.status == "休息"])

    attendance_rate = round(monthly_normal / monthly_total * 100, 1) if monthly_total > 0 else 0
    overtime_rate = round(monthly_overtime_hours / monthly_actual_hours * 100, 1) if monthly_actual_hours > 0 else 0
    owed_hours = max(0, monthly_scheduled_hours - monthly_actual_hours - monthly_overtime_hours)
    owed_rate = round(owed_hours / monthly_scheduled_hours * 100, 1) if monthly_scheduled_hours > 0 else 0

    return {
        "employee_count": employee_count,
        "latest_data_date": latest_date.isoformat() if latest_date else None,
        "latest_attendance": latest_attendance,
        "latest_late": latest_late,
        "latest_absent": latest_absent,
        "latest_leave": latest_leave,
        "latest_timeoff": latest_timeoff,
        "monthly_total_days": monthly_total,
        "monthly_normal_days": monthly_normal,
        "monthly_late_days": monthly_late,
        "monthly_absent_days": monthly_absent,
        "monthly_leave_days": monthly_leave,
        "monthly_timeoff_days": monthly_timeoff,
        "monthly_actual_hours": round(monthly_actual_hours, 1),
        "monthly_scheduled_hours": round(monthly_scheduled_hours, 1),
        "monthly_overtime_hours": round(monthly_overtime_hours, 1),
        "monthly_owed_hours": round(owed_hours, 1),
        "attendance_rate": attendance_rate,
        "overtime_rate": overtime_rate,
        "owed_rate": owed_rate,
    }


@router.get("/daily-trend")
def get_daily_trend(
    year_month: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if year_month:
        parts = year_month.split("-")
        year, month = int(parts[0]), int(parts[1])
    else:
        year, month = _get_ym()

    rows = db.query(
        DailyReport.schedule_date,
        DailyReport.status,
        DailyReport.actual_hours,
        DailyReport.scheduled_hours,
    ).filter(
        extract("year", DailyReport.schedule_date) == year,
        extract("month", DailyReport.schedule_date) == month,
    ).order_by(DailyReport.schedule_date).all()

    threshold = _get_long_hour_threshold(db)

    daily = {}
    for r in rows:
        d = r.schedule_date.isoformat()
        if d not in daily:
            daily[d] = {
                "date": d, "total": 0, "expected_count": 0, "total_with_hours": 0,
                "normal": 0, "late": 0, "absent": 0, "leave": 0, "timeoff": 0,
                "actual_hours": 0.0, "scheduled_hours": 0.0,
                "long_hours": 0, "normal_hours_count": 0, "slight_short": 0, "short_hours": 0,
            }
        daily[d]["total"] += 1
        status_raw = r.status or "未知"
        if status_raw != "休息":
            daily[d]["expected_count"] += 1
        status = r.status or "未知"
        status_key_map = {"正常": "normal", "迟到": "late", "缺勤": "absent", "请假": "leave", "休息": "timeoff"}
        mapped_status = status_key_map.get(status, status)
        if mapped_status in daily[d]:
            daily[d][mapped_status] += 1
        else:
            daily[d][mapped_status] = 1
        ah = float(r.actual_hours or 0)
        if ah > 0:
            daily[d]["total_with_hours"] += 1
        daily[d]["actual_hours"] = round(daily[d]["actual_hours"] + ah, 1)
        daily[d]["scheduled_hours"] = round(daily[d]["scheduled_hours"] + float(r.scheduled_hours or 0), 1)

        if ah >= threshold:
            daily[d]["long_hours"] += 1
        elif ah >= 8:
            daily[d]["normal_hours_count"] += 1
        elif ah >= 7:
            daily[d]["slight_short"] += 1
        elif ah > 0:
            daily[d]["short_hours"] += 1

    _zero_template = {
        "date": "", "total": 0, "expected_count": 0, "total_with_hours": 0,
        "normal": 0, "late": 0, "absent": 0, "leave": 0, "timeoff": 0,
        "actual_hours": 0.0, "scheduled_hours": 0.0,
        "long_hours": 0, "normal_hours_count": 0, "slight_short": 0, "short_hours": 0,
    }

    _, last_day = monthrange(year, month)
    all_dates = [f"{year}-{month:02d}-{day:02d}" for day in range(1, last_day + 1)]
    for d in all_dates:
        if d not in daily:
            entry = dict(_zero_template)
            entry["date"] = d
            daily[d] = entry

    return [daily[d] for d in sorted(daily.keys())]


@router.get("/daily-detail")
def get_daily_detail(
    date: str = Query(...),
    team: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    schedule_date = datetime.strptime(date, "%Y-%m-%d").date()
    query = db.query(DailyReport).join(
        Employee, DailyReport.emp_id == Employee.id
    ).filter(DailyReport.schedule_date == schedule_date)
    if team:
        query = query.filter(Employee.team == team)

    items = query.order_by(Employee.name).all()
    result = []
    for r in items:
        emp = db.query(Employee).filter(Employee.id == r.emp_id).first()
        if emp:
            result.append({
                "emp_id": emp.id,
                "emp_no": emp.emp_no,
                "name": emp.name,
                "team": emp.team,
                "status": r.status,
                "scheduled_hours": float(r.scheduled_hours or 0),
                "actual_hours": float(r.actual_hours or 0),
                "overtime_hours": float(r.overtime_hours or 0),
                "late_minutes": r.late_minutes or 0,
                "early_minutes": r.early_minutes or 0,
            })
    return result


@router.get("/hour-bucket-detail")
def get_hour_bucket_detail(
    date: str = Query(...),
    bucket: str = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    schedule_date = datetime.strptime(date, "%Y-%m-%d").date()
    threshold = _get_long_hour_threshold(db)

    items = db.query(DailyReport).join(
        Employee, DailyReport.emp_id == Employee.id
    ).filter(DailyReport.schedule_date == schedule_date).all()

    def _in_bucket(r):
        ah = float(r.actual_hours or 0)
        if bucket == "long":
            return ah >= threshold
        elif bucket == "normal":
            return 8 <= ah < threshold
        elif bucket == "slight":
            return 7 <= ah < 8
        elif bucket == "short":
            return 0 < ah < 7
        return False

    result = []
    for r in items:
        if _in_bucket(r):
            emp = db.query(Employee).filter(Employee.id == r.emp_id).first()
            if emp:
                result.append({
                    "emp_id": emp.id,
                    "emp_no": emp.emp_no,
                    "name": emp.name,
                    "team": emp.team,
                    "actual_hours": float(r.actual_hours or 0),
                    "status": r.status,
                })
    return result


@router.get("/consecutive-overtime")
def get_consecutive_overtime(
    year_month: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if year_month:
        parts = year_month.split("-")
        year, month = int(parts[0]), int(parts[1])
    else:
        year, month = _get_ym()

    threshold = _get_long_hour_threshold(db)

    emp_ids = [e.id for e in db.query(Employee.id).filter(Employee.status == "在职").all()]

    all_reports = db.query(DailyReport).filter(
        DailyReport.emp_id.in_(emp_ids),
        extract("year", DailyReport.schedule_date) == year,
        extract("month", DailyReport.schedule_date) == month,
        DailyReport.actual_hours.isnot(None),
    ).order_by(DailyReport.emp_id, DailyReport.schedule_date).all()

    consecutive_counts = []
    i = 0
    while i < len(all_reports):
        if float(all_reports[i].actual_hours or 0) >= threshold:
            streak = 1
            j = i + 1
            while j < len(all_reports) and all_reports[j].emp_id == all_reports[i].emp_id:
                gap = (all_reports[j].schedule_date - all_reports[j - 1].schedule_date).days
                if gap == 1 and float(all_reports[j].actual_hours or 0) >= threshold:
                    streak += 1
                    j += 1
                elif gap == 1:
                    break
                else:
                    break
            consecutive_counts.append(streak)
            i = j
        else:
            i += 1

    dist = {}
    for c in consecutive_counts:
        key = "5+" if c >= 5 else str(c)
        dist[key] = dist.get(key, 0) + 1

    result = []
    for key in ["1", "2", "3", "4", "5+"]:
        result.append({"consecutive_days": key, "count": dist.get(key, 0)})

    return result


@router.get("/shift-distribution")
def get_shift_distribution(
    year_month: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if year_month:
        parts = year_month.split("-")
        year, month = int(parts[0]), int(parts[1])
    else:
        year, month = _get_ym()

    results = db.query(
        Schedule.shift_name,
        func.count(Schedule.id).label("cnt"),
    ).filter(
        extract("year", Schedule.schedule_date) == year,
        extract("month", Schedule.schedule_date) == month,
        Schedule.shift_name.isnot(None),
        Schedule.shift_name != "",
    ).group_by(Schedule.shift_name).order_by(func.count(Schedule.id).desc()).all()

    return [{"shift_name": r[0], "count": r[1]} for r in results]


@router.get("/team-hours")
def get_team_hours(
    year_month: str = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if year_month:
        parts = year_month.split("-")
        year, month = int(parts[0]), int(parts[1])
    else:
        year, month = _get_ym()

    teams_data = db.query(Employee.team).filter(
        Employee.status == "在职",
        Employee.team.isnot(None),
    ).distinct().all()

    result = []
    for (team_name,) in teams_data:
        emp_ids = [e.id for e in db.query(Employee.id).filter(Employee.team == team_name).all()]
        if not emp_ids:
            continue
        reports = db.query(DailyReport).filter(
            DailyReport.emp_id.in_(emp_ids),
            extract("year", DailyReport.schedule_date) == year,
            extract("month", DailyReport.schedule_date) == month,
        ).all()
        scheduled = sum(float(r.scheduled_hours or 0) for r in reports)
        actual = sum(float(r.actual_hours or 0) for r in reports)
        normal = len([r for r in reports if r.status == "正常"])
        late = len([r for r in reports if r.status == "迟到"])
        absent = len([r for r in reports if r.status == "缺勤"])
        result.append({
            "team": team_name,
            "emp_count": len(emp_ids),
            "scheduled_hours": round(scheduled, 1),
            "actual_hours": round(actual, 1),
            "normal_days": normal,
            "late_days": late,
            "absent_days": absent,
        })

    result.sort(key=lambda x: x["actual_hours"], reverse=True)
    return result


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

    user_ids = list({i.user_id for i in items if i.user_id is not None})
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    return {
        "items": [
            {
                "id": i.id,
                "user_id": i.user_id,
                "user_name": users[i.user_id].display_name or users[i.user_id].username if i.user_id in users else None,
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
    require_permission(current_user, "system.export_logs")
    query = db.query(OperationLog)
    if user_id:
        query = query.filter(OperationLog.user_id == user_id)
    if operation:
        query = query.filter(OperationLog.operation_type.like(f"%{operation}%"))

    items = query.order_by(OperationLog.created_at.desc()).offset((page-1)*limit).limit(limit).all()

    user_ids = list({i.user_id for i in items if i.user_id is not None})
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}

    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_id", "user_name", "operation_type", "target_table", "target_id", "details", "created_at"])
    for i in items:
        user_name = users[i.user_id].display_name or users[i.user_id].username if i.user_id in users else ""
        writer.writerow([i.id, i.user_id, user_name, i.operation_type, i.target_table, i.target_id, i.details, i.created_at.isoformat() if i.created_at else ""])
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
    require_permission(current_user, "system.clear_data")
    
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
    if not (1 <= cfg.retention_months <= 6):
        raise HTTPException(status_code=400, detail="retention_months 必须在 1-6 之间")
    if _DB_CONFIG:
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