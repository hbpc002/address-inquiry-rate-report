"""供智能体工具复用的报表查询逻辑（与 API 端点相互独立，避免重复编排 HTTP）。"""
from datetime import datetime, date
from calendar import monthrange

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, extract, func

from app.models.employee import Employee
from app.models.daily_report import DailyReport
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType


def _parse_ym(year_month: str):
    year, month = map(int, year_month.split("-"))
    return year, month


def team_ranking(db: Session, year_month: str) -> list:
    year, month = _parse_ym(year_month)
    teams = (
        db.query(Employee.team, func.count(Employee.id))
        .filter(Employee.status == "在职", Employee.team.isnot(None))
        .group_by(Employee.team)
        .all()
    )
    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])

    result = []
    for team_name, _ in teams:
        emps = db.query(Employee).filter(
            Employee.team == team_name,
            or_(Employee.hire_date.is_(None), Employee.hire_date <= month_end),
            or_(Employee.deleted_at.is_(None), Employee.deleted_at >= month_start),
        ).all()
        emp_ids = [e.id for e in emps]
        reports = db.query(DailyReport).filter(
            DailyReport.emp_id.in_(emp_ids),
            extract("year", DailyReport.schedule_date) == year,
            extract("month", DailyReport.schedule_date) == month,
        ).all()
        schedules = db.query(Schedule).filter(
            Schedule.emp_id.in_(emp_ids),
            extract("year", Schedule.schedule_date) == year,
            extract("month", Schedule.schedule_date) == month,
        ).all()
        shift_cache = {}
        total_scheduled = 0.0
        for s in schedules:
            wh = float(s.work_hours) if s.work_hours is not None else None
            if wh is None and s.shift_type_id:
                if s.shift_type_id not in shift_cache:
                    shift_cache[s.shift_type_id] = db.query(ShiftType).filter(ShiftType.id == s.shift_type_id).first()
                sh = shift_cache[s.shift_type_id]
                if sh:
                    wh = float(sh.work_hours or 0)
            total_scheduled += wh or 0
        total_actual = sum(float(r.actual_hours or 0) for r in reports)
        total_overtime = sum(float(r.overtime_hours or 0) for r in reports)
        late = len([r for r in reports if r.status == "迟到"])
        absent = len([r for r in reports if r.status == "缺勤"])
        work_days = len(schedules)
        avg_attendance = (work_days - absent) / work_days if work_days > 0 else 0
        result.append({
            "team": team_name,
            "emp_count": len(emp_ids),
            "total_scheduled": round(total_scheduled, 1),
            "total_actual": round(total_actual, 1),
            "total_overtime": round(total_overtime, 1),
            "avg_attendance": round(avg_attendance, 3),
            "late_count": late,
            "absent_count": absent,
        })
    result.sort(key=lambda x: x["total_actual"], reverse=True)
    return result


def month_summary(
    db: Session, year_month: str,
    team: str = None, dept: str = None, name: str = None, emp_no: str = None,
) -> list:
    year, month = _parse_ym(year_month)
    q = db.query(Employee).filter(Employee.status == "在职")
    if team:
        q = q.filter(Employee.team == team)
    if dept:
        q = q.filter(Employee.dept == dept)
    if name:
        q = q.filter(Employee.name.ilike(f"%{name}%"))
    if emp_no:
        q = q.filter(Employee.emp_no.ilike(f"%{emp_no}%"))
    result = []
    for emp in q.order_by(Employee.name).all():
        reports = db.query(DailyReport).filter(
            DailyReport.emp_id == emp.id,
            extract("year", DailyReport.schedule_date) == year,
            extract("month", DailyReport.schedule_date) == month,
        ).all()
        schedules = db.query(Schedule).filter(
            Schedule.emp_id == emp.id,
            extract("year", Schedule.schedule_date) == year,
            extract("month", Schedule.schedule_date) == month,
        ).all()
        scheduled = 0.0
        for s in schedules:
            wh = float(s.work_hours) if s.work_hours is not None else None
            if wh is None and s.shift_type_id:
                sh = db.query(ShiftType).filter(ShiftType.id == s.shift_type_id).first()
                if sh:
                    wh = float(sh.work_hours or 0)
            scheduled += wh or 0
        actual = sum(float(r.actual_hours or 0) for r in reports)
        overtime = sum(float(r.overtime_hours or 0) for r in reports)
        owed = max(0, scheduled - actual - overtime)
        result.append({
            "emp_no": emp.emp_no, "name": emp.name, "team": emp.team, "dept": emp.dept,
            "scheduled_hours": round(scheduled, 1), "actual_hours": round(actual, 1),
            "overtime_hours": round(overtime, 1), "owed_hours": round(owed, 1),
            "normal_days": len([r for r in reports if r.status == "正常"]),
            "late_days": len([r for r in reports if r.status == "迟到"]),
            "early_days": len([r for r in reports if r.status == "早退"]),
            "absent_days": len([r for r in reports if r.status == "缺勤"]),
            "leave_days": len([r for r in reports if r.status == "请假"]),
            "timeoff_days": len([r for r in reports if r.status == "休息"]),
        })
    return result


def date_range_summary(
    db: Session, start_date: str, end_date: str,
    team: str = None, dept: str = None,
) -> list:
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()
    q = db.query(DailyReport).join(Employee)
    q = q.filter(and_(DailyReport.schedule_date >= start, DailyReport.schedule_date <= end))
    if team:
        q = q.filter(Employee.team == team)
    if dept:
        q = q.filter(Employee.dept == dept)
    items = q.order_by(DailyReport.schedule_date, Employee.name).all()
    summary = {}
    for item in items:
        emp = db.query(Employee).filter(Employee.id == item.emp_id).first()
        if not emp:
            continue
        key = emp.id
        if key not in summary:
            summary[key] = {
                "emp_no": emp.emp_no, "name": emp.name, "team": emp.team, "dept": emp.dept,
                "scheduled_hours": 0.0, "actual_hours": 0.0, "overtime_hours": 0.0,
                "normal_days": 0, "late_days": 0, "early_days": 0,
                "absent_days": 0, "leave_days": 0, "timeoff_days": 0, "work_days": 0,
            }
        s = summary[key]
        s["scheduled_hours"] += float(item.scheduled_hours or 0)
        s["actual_hours"] += float(item.actual_hours or 0)
        s["overtime_hours"] += float(item.overtime_hours or 0)
        s["work_days"] += 1
        st = item.status
        if st == "正常":
            s["normal_days"] += 1
        elif st == "迟到":
            s["late_days"] += 1
        elif st == "早退":
            s["early_days"] += 1
        elif st == "缺勤":
            s["absent_days"] += 1
        elif st == "请假":
            s["leave_days"] += 1
        elif st == "休息":
            s["timeoff_days"] += 1
    for s in summary.values():
        s["owed_hours"] = max(0, s["scheduled_hours"] - s["actual_hours"] - s["overtime_hours"])
    out = list(summary.values())
    out.sort(key=lambda x: x["name"])
    return out


def daily(
    db: Session, schedule_date: str,
    team: str = None, dept: str = None, status: str = None,
    name: str = None, emp_no: str = None, page: int = 1, limit: int = 50,
) -> dict:
    d = datetime.strptime(schedule_date, "%Y-%m-%d").date()
    q = db.query(DailyReport).join(Employee).filter(DailyReport.schedule_date == d)
    if team:
        q = q.filter(Employee.team == team)
    if dept:
        q = q.filter(Employee.dept == dept)
    if status:
        q = q.filter(DailyReport.status == status)
    if name:
        q = q.filter(Employee.name.ilike(f"%{name}%"))
    if emp_no:
        q = q.filter(Employee.emp_no.ilike(f"%{emp_no}%"))
    total = q.count()
    items = q.order_by(Employee.name).offset((page - 1) * limit).limit(limit).all()
    out = []
    for item in items:
        emp = db.query(Employee).filter(Employee.id == item.emp_id).first()
        out.append({
            "emp_no": emp.emp_no if emp else "", "name": emp.name if emp else "",
            "team": emp.team if emp else "", "dept": emp.dept if emp else "",
            "schedule_date": str(item.schedule_date), "status": item.status,
            "scheduled_hours": float(item.scheduled_hours or 0),
            "actual_hours": float(item.actual_hours or 0),
            "late_minutes": item.late_minutes, "early_minutes": item.early_minutes,
            "overtime_hours": float(item.overtime_hours or 0),
        })
    return {"items": out, "total": total}


def efficiency_summary(
    db: Session, year_month: str, team: str = None, dept: str = None,
) -> list:
    year, month = _parse_ym(year_month)
    q = db.query(Employee).filter(Employee.status == "在职")
    if team:
        q = q.filter(Employee.team == team)
    if dept:
        q = q.filter(Employee.dept == dept)
    result = []
    for emp in q.order_by(Employee.name).all():
        reports = db.query(DailyReport).filter(
            DailyReport.emp_id == emp.id,
            extract("year", DailyReport.schedule_date) == year,
            extract("month", DailyReport.schedule_date) == month,
        ).all()
        if not reports:
            continue
        total = len(reports)
        normal = len([r for r in reports if r.status == "正常"])
        scheduled = sum(float(r.scheduled_hours or 0) for r in reports)
        actual = sum(float(r.actual_hours or 0) for r in reports)
        overtime = sum(float(r.overtime_hours or 0) for r in reports)
        attendance_rate = round(normal / total * 100, 1) if total else 0
        efficiency_rate = round(actual / scheduled * 100, 1) if scheduled else 0
        result.append({
            "emp_no": emp.emp_no, "name": emp.name, "team": emp.team, "dept": emp.dept,
            "attendance_rate": attendance_rate, "efficiency_rate": efficiency_rate,
            "scheduled_hours": round(scheduled, 1), "actual_hours": round(actual, 1),
            "overtime_hours": round(overtime, 1),
            "late_days": len([r for r in reports if r.status == "迟到"]),
            "absent_days": len([r for r in reports if r.status == "缺勤"]),
        })
    return result


def dashboard_stats(db: Session, year_month: str = None) -> dict:
    if year_month:
        year, month = _parse_ym(year_month)
    else:
        now = datetime.now()
        year, month = now.year, now.month
    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])
    employee_count = db.query(Employee).filter(Employee.status == "在职").count()
    latest_date = db.query(func.max(DailyReport.schedule_date)).scalar()
    reports = db.query(DailyReport).filter(
        extract("year", DailyReport.schedule_date) == year,
        extract("month", DailyReport.schedule_date) == month,
    ).all()
    total = len(reports)
    normal = len([r for r in reports if r.status == "正常"])
    late = len([r for r in reports if r.status == "迟到"])
    absent = len([r for r in reports if r.status == "缺勤"])
    leave = len([r for r in reports if r.status == "请假"])
    timeoff = len([r for r in reports if r.status == "休息"])
    actual = sum(float(r.actual_hours or 0) for r in reports)
    scheduled = sum(float(r.scheduled_hours or 0) for r in reports)
    overtime = sum(float(r.overtime_hours or 0) for r in reports)
    attendance_rate = round(normal / total * 100, 1) if total else 0
    owed = max(0, scheduled - actual - overtime)
    return {
        "employee_count": employee_count,
        "latest_date": latest_date.isoformat() if latest_date else "",
        "total": total, "normal": normal, "late": late, "absent": absent,
        "leave": leave, "timeoff": timeoff,
        "scheduled_hours": round(scheduled, 1), "actual_hours": round(actual, 1),
        "overtime_hours": round(overtime, 1), "owed_hours": round(owed, 1),
        "attendance_rate": attendance_rate,
    }


def schema_hint() -> str:
    """提供给 text-to-SQL 工具的数据库结构说明（只读表）。"""
    return (
        "数据库为 PostgreSQL，主要相关表：\n"
        "- employees(id, emp_no, name, team, dept, status, hire_date)：员工信息\n"
        "- daily_reports(id, emp_id, schedule_date, status, scheduled_hours, actual_hours, "
        "overtime_hours, late_minutes, early_minutes)：每日考勤汇总，status 取值为 "
        "正常/迟到/早退/缺勤/请假/休息\n"
        "- schedules(id, emp_id, schedule_date, shift_type_id, work_hours)：排班\n"
        "- shift_types(id, shift_name, work_hours, is_night)：班次类型\n"
        "- workloads(id, account, date, metrics jsonb)：工作量(含通话量/工单量等)\n"
        "联表用 employees.id = daily_reports.emp_id。只允许 SELECT，禁止写操作。"
    )
