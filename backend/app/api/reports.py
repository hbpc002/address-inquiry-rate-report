from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, extract, func
from typing import Optional, List
from datetime import datetime, date, timedelta
from calendar import monthrange
import io
import csv
from app.models.database import get_db
from app.models.employee import Employee
from app.models.daily_report import DailyReport
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.models.workload import Workload
from app.models.attendance_config import AttendanceConfig
from app.schemas.daily_report import DailyReportResponse, DailyReportListResponse
from app.core.security import get_current_user, require_permission
from app.utils.logger import log_operation
from app.services.attendance import save_daily_report

router = APIRouter(prefix="/api/reports", tags=["考勤报表"])


@router.get("/daily", response_model=DailyReportListResponse)
def get_daily_reports(
    schedule_date: str = Query(...),
    team: Optional[str] = None,
    dept: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(DailyReport).join(Employee)

    schedule_date_obj = datetime.strptime(schedule_date, '%Y-%m-%d').date()
    query = query.filter(DailyReport.schedule_date == schedule_date_obj)

    if team:
        query = query.filter(Employee.team == team)
    if dept:
        query = query.filter(Employee.dept == dept)
    if status:
        query = query.filter(DailyReport.status == status)
    if name:
        query = query.filter(Employee.name.ilike(f"%{name}%"))
    if emp_no:
        query = query.filter(Employee.emp_no.ilike(f"%{emp_no}%"))

    total = query.count()
    items = query.order_by(Employee.name).offset((page-1)*limit).limit(limit).all()

    result_items = []
    for item in items:
        emp = db.query(Employee).filter(Employee.id == item.emp_id).first()
        if emp:
            result_items.append(DailyReportResponse(
                id=item.id,
                emp_id=item.emp_id,
                emp_no=emp.emp_no,
                name=emp.name,
                team=emp.team,
                dept=emp.dept,
                schedule_date=item.schedule_date,
                shift_type_id=item.shift_type_id,
                schedule_type=item.schedule_type,
                scheduled_start=str(item.scheduled_start) if item.scheduled_start else None,
                scheduled_end=str(item.scheduled_end) if item.scheduled_end else None,
                scheduled_hours=float(item.scheduled_hours or 0),
                actual_checkin=item.actual_checkin,
                actual_checkout=item.actual_checkout,
                actual_hours=float(item.actual_hours or 0),
                status=item.status,
                late_minutes=item.late_minutes,
                early_minutes=item.early_minutes,
                overtime_hours=float(item.overtime_hours or 0),
                segment_details=item.segment_details,
                calculated_at=item.calculated_at
            ))

    return DailyReportListResponse(items=result_items, total=total)


@router.get("/date-range", response_model=dict)
def get_reports_by_date_range(
    start_date: str = Query(...),
    end_date: str = Query(...),
    team: Optional[str] = None,
    dept: Optional[str] = None,
    status: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """按日期范围查询考勤报表"""
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    report_query = db.query(DailyReport).join(Employee)
    report_query = report_query.filter(and_(
        DailyReport.schedule_date >= start,
        DailyReport.schedule_date <= end
    ))
    
    if team:
        report_query = report_query.filter(Employee.team == team)
    if dept:
        report_query = report_query.filter(Employee.dept == dept)
    if status:
        report_query = report_query.filter(DailyReport.status == status)
    if name:
        report_query = report_query.filter(Employee.name.ilike(f"%{name}%"))
    if emp_no:
        report_query = report_query.filter(Employee.emp_no.ilike(f"%{emp_no}%"))
    
    items = report_query.order_by(DailyReport.schedule_date, Employee.name).all()
    
    # 按员工汇总
    emp_summary = {}
    for item in items:
        emp = db.query(Employee).filter(Employee.id == item.emp_id).first()
        if not emp:
            continue
            
        emp_key = emp.id
        if emp_key not in emp_summary:
            emp_summary[emp_key] = {
                "emp_id": emp.id,
                "emp_no": emp.emp_no,
                "name": emp.name,
                "team": emp.team,
                "dept": emp.dept,
                "scheduled_hours": 0,
                "actual_hours": 0,
                "overtime_hours": 0,
                "normal_days": 0,
                "late_days": 0,
                "early_days": 0,
                "absent_days": 0,
                "leave_days": 0,
                "timeoff_days": 0,
                "work_days": 0
            }
        
        summary = emp_summary[emp_key]
        summary["scheduled_hours"] += float(item.scheduled_hours or 0)
        summary["actual_hours"] += float(item.actual_hours or 0)
        summary["overtime_hours"] += float(item.overtime_hours or 0)
        summary["work_days"] += 1
        
        s = item.status
        if s == "正常":
            summary["normal_days"] += 1
        elif s == "迟到":
            summary["late_days"] += 1
        elif s == "早退":
            summary["early_days"] += 1
        elif s == "缺勤":
            summary["absent_days"] += 1
        elif s == "请假":
            summary["leave_days"] += 1
        elif s == "休息":
            summary["timeoff_days"] += 1
    
    # 计算欠时
    for emp_key in emp_summary:
        s = emp_summary[emp_key]
        s["owed_hours"] = max(0, s["scheduled_hours"] - s["actual_hours"] - s["overtime_hours"])
    
    summary_list = list(emp_summary.values())
    summary_list.sort(key=lambda x: x["name"])
    total = len(summary_list)
    summary_list = summary_list[(page-1)*limit:page*limit]
    
    return {
        "items": summary_list,
        "total": total,
        "start_date": start_date,
        "end_date": end_date,
        "days": (end - start).days + 1
    }


@router.get("/month", response_model=DailyReportListResponse)
def get_month_reports(
    year_month: str = Query(...),
    team: Optional[str] = None,
    dept: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    year, month = map(int, year_month.split('-'))

    query = db.query(DailyReport).filter(
        and_(
            extract('year', DailyReport.schedule_date) == year,
            extract('month', DailyReport.schedule_date) == month
        )
    ).join(Employee)

    if team:
        query = query.filter(Employee.team == team)
    if dept:
        query = query.filter(Employee.dept == dept)

    total = query.count()
    items = query.order_by(Employee.name).offset((page-1)*limit).limit(limit).all()
    return DailyReportListResponse(
        items=[DailyReportResponse.model_validate(i) for i in items],
        total=total
    )


@router.get("/month-summary", response_model=dict)
def get_month_summary(
    year_month: str = Query(...),
    team: Optional[str] = None,
    dept: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    year, month = map(int, year_month.split('-'))

    emp_query = db.query(Employee).filter(Employee.status == "在职")
    if team:
        emp_query = emp_query.filter(Employee.team == team)
    if dept:
        emp_query = emp_query.filter(Employee.dept == dept)
    if name:
        emp_query = emp_query.filter(Employee.name.ilike(f"%{name}%"))
    if emp_no:
        emp_query = emp_query.filter(Employee.emp_no.ilike(f"%{emp_no}%"))

    total = emp_query.count()
    employees = emp_query.order_by(Employee.name).offset((page-1)*limit).limit(limit).all()

    result = []
    for emp in employees:
        daily_reports = db.query(DailyReport).filter(
            and_(
                DailyReport.emp_id == emp.id,
                extract('year', DailyReport.schedule_date) == year,
                extract('month', DailyReport.schedule_date) == month
            )
        ).all()

        schedules = db.query(Schedule).filter(
            and_(
                Schedule.emp_id == emp.id,
                extract('year', Schedule.schedule_date) == year,
                extract('month', Schedule.schedule_date) == month
            )
        ).all()
        
        scheduled = 0
        for s in schedules:
            work_hours = float(s.work_hours) if s.work_hours is not None else None
            if work_hours is None and s.shift_type_id:
                shift = db.query(ShiftType).filter(ShiftType.id == s.shift_type_id).first()
                if shift:
                    work_hours = float(shift.work_hours or 0)
            scheduled += work_hours or 0
        
        actual = sum(float(r.actual_hours or 0) for r in daily_reports)
        overtime = sum(float(r.overtime_hours or 0) for r in daily_reports)
        owed = max(0, scheduled - actual - overtime)

        result.append({
            "emp_id": emp.id,
            "emp_no": emp.emp_no,
            "name": emp.name,
            "team": emp.team,
            "dept": emp.dept,
            "scheduled_hours": scheduled,
            "actual_hours": actual,
            "overtime_hours": overtime,
            "owed_hours": owed,
            "normal_days": len([r for r in daily_reports if r.status == "正常"]),
            "late_days": len([r for r in daily_reports if r.status == "迟到"]),
            "early_days": len([r for r in daily_reports if r.status == "早退"]),
            "absent_days": len([r for r in daily_reports if r.status == "缺勤"]),
            "leave_days": len([r for r in daily_reports if r.status == "请假"]),
            "timeoff_days": len([r for r in daily_reports if r.status == "休息"])
        })

    return {"items": result, "total": total}


@router.get("/team-ranking", response_model=list)
def get_team_ranking(
    year_month: str = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    year, month = map(int, year_month.split('-'))

    teams = db.query(Employee.team, func.count(Employee.id)).filter(
        Employee.status == "在职",
        Employee.team.isnot(None)
    ).group_by(Employee.team).all()

    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])

    result = []
    for team_name, _ in teams:
        team_employees = db.query(Employee).filter(
            Employee.team == team_name,
            or_(Employee.hire_date.is_(None), Employee.hire_date <= month_end),
            or_(Employee.deleted_at.is_(None), Employee.deleted_at >= month_start),
        ).all()
        emp_ids = [e.id for e in team_employees]
        
        daily_reports = db.query(DailyReport).filter(
            DailyReport.emp_id.in_(emp_ids),
            extract('year', DailyReport.schedule_date) == year,
            extract('month', DailyReport.schedule_date) == month
        ).all()
        
        schedules = db.query(Schedule).filter(
            Schedule.emp_id.in_(emp_ids),
            extract('year', Schedule.schedule_date) == year,
            extract('month', Schedule.schedule_date) == month
        ).all()
        
        shift_cache = {}
        total_scheduled = 0
        for s in schedules:
            work_hours = float(s.work_hours) if s.work_hours is not None else None
            if work_hours is None and s.shift_type_id:
                if s.shift_type_id not in shift_cache:
                    shift_cache[s.shift_type_id] = db.query(ShiftType).filter(ShiftType.id == s.shift_type_id).first()
                shift = shift_cache[s.shift_type_id]
                if shift:
                    work_hours = float(shift.work_hours or 0)
            total_scheduled += work_hours or 0
        
        total_actual = sum(float(r.actual_hours or 0) for r in daily_reports)
        total_overtime = sum(float(r.overtime_hours or 0) for r in daily_reports)
        
        late_count = len([r for r in daily_reports if r.status == "迟到"])
        absent_count = len([r for r in daily_reports if r.status == "缺勤"])
        
        work_days = len(schedules)
        avg_attendance = (work_days - absent_count) / work_days if work_days > 0 else 0

        result.append({
            "team": team_name,
            "emp_count": len(emp_ids),
            "total_scheduled": round(total_scheduled, 1),
            "total_actual": round(total_actual, 1),
            "total_overtime": round(total_overtime, 1),
            "avg_attendance": round(avg_attendance, 3),
            "late_count": late_count,
            "absent_count": absent_count
        })

    result.sort(key=lambda x: x['total_actual'], reverse=True)
    return result


@router.get("/export")
def export_report(
    type: str = Query("month"),
    schedule_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year_month: Optional[str] = None,
    team: Optional[str] = None,
    dept: Optional[str] = None,
    status: Optional[str] = None,
    format: str = Query("csv"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "reports.export")
    output = io.StringIO()
    writer = csv.writer(output)

    if type == "daily" and schedule_date:
        schedule_date_obj = datetime.strptime(schedule_date, '%Y-%m-%d').date()
        query = db.query(DailyReport).filter(DailyReport.schedule_date == schedule_date_obj).join(Employee)

        if team:
            query = query.filter(Employee.team == team)
        if dept:
            query = query.filter(Employee.dept == dept)
        if status:
            query = query.filter(DailyReport.status == status)

        items = query.order_by(Employee.name).all()

        writer.writerow(["日期", "工号", "姓名", "班组", "部门", "计划开始", "计划结束", "实际签到", "实际签退", "状态", "迟到分钟", "早退分钟", "实际工时"])
        for item in items:
            emp = db.query(Employee).filter(Employee.id == item.emp_id).first()
            if emp:
                writer.writerow([
                    item.schedule_date,
                    emp.emp_no,
                    emp.name,
                    emp.team,
                    emp.dept or "",
                    item.scheduled_start or "",
                    item.scheduled_end or "",
                    item.actual_checkin.strftime("%Y-%m-%d %H:%M:%S") if item.actual_checkin else "",
                    item.actual_checkout.strftime("%Y-%m-%d %H:%M:%S") if item.actual_checkout else "",
                    item.status or "",
                    item.late_minutes or 0,
                    item.early_minutes or 0,
                    item.actual_hours or 0
                ])
        filename = f"daily_report_{schedule_date}.csv"
    
    elif type == "date_range" and start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        query = db.query(DailyReport).filter(and_(
            DailyReport.schedule_date >= start,
            DailyReport.schedule_date <= end
        )).join(Employee)
        
        if team:
            query = query.filter(Employee.team == team)
        if dept:
            query = query.filter(Employee.dept == dept)
        
        writer.writerow(["日期", "工号", "姓名", "班组", "部门", "计划工时", "实际工时", "状态", "迟到分钟", "早退分钟", "加班工时"])
        
        items = query.order_by(DailyReport.schedule_date, Employee.name).all()
        for item in items:
            emp = db.query(Employee).filter(Employee.id == item.emp_id).first()
            if emp:
                writer.writerow([
                    item.schedule_date,
                    emp.emp_no,
                    emp.name,
                    emp.team,
                    emp.dept or "",
                    item.scheduled_hours or 0,
                    item.actual_hours or 0,
                    item.status or "",
                    item.late_minutes or 0,
                    item.early_minutes or 0,
                    item.overtime_hours or 0
                ])
        filename = f"report_{start_date}_{end_date}.csv"
    
    else:
        if not year_month:
            year_month = datetime.now().strftime("%Y-%m")

        year, month = map(int, year_month.split('-'))
        employees = db.query(Employee).filter(Employee.status == "在职")
        if team:
            employees = employees.filter(Employee.team == team)
        if dept:
            employees = employees.filter(Employee.dept == dept)

        writer.writerow(["工号", "姓名", "班组", "部门", "计划工时", "实际工时", "加班工时", "欠时工时", "正常天数", "迟到天数", "早退天数", "缺勤天数", "请假天数", "休息天数"])

        for emp in employees.all():
            daily_reports = db.query(DailyReport).filter(
                and_(
                    DailyReport.emp_id == emp.id,
                    extract('year', DailyReport.schedule_date) == year,
                    extract('month', DailyReport.schedule_date) == month
                )
            ).all()

            scheduled = sum(float(r.scheduled_hours or 0) for r in daily_reports)
            actual = sum(float(r.actual_hours or 0) for r in daily_reports)
            overtime = sum(float(r.overtime_hours or 0) for r in daily_reports)
            owed = max(0, scheduled - actual - overtime)

            writer.writerow([
                emp.emp_no,
                emp.name,
                emp.team,
                emp.dept or "",
                scheduled,
                actual,
                overtime,
                owed,
                len([r for r in daily_reports if r.status == "正常"]),
                len([r for r in daily_reports if r.status == "迟到"]),
                len([r for r in daily_reports if r.status == "早退"]),
                len([r for r in daily_reports if r.status == "缺勤"]),
                len([r for r in daily_reports if r.status == "请假"]),
                len([r for r in daily_reports if r.status == "休息"])
            ])
        filename = f"monthly_report_{year_month}.csv"

        output.seek(0)
    log_operation(db, current_user["id"], "export_report", "reports", None, {"export_type": type, "schedule_date": schedule_date})
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/recalculate", response_model=dict)
def recalculate_attendance(
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """重算指定日期范围内的考勤报表"""
    require_permission(current_user, "reports.recalculate")
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()

    schedules = db.query(Schedule).filter(
        and_(
            Schedule.schedule_date >= start,
            Schedule.schedule_date <= end
        )
    ).all()

    processed = set()
    count = 0
    for s in schedules:
        key = (s.emp_id, s.schedule_date.isoformat())
        if key not in processed:
            processed.add(key)
            save_daily_report(db, s.emp_id, s.schedule_date)
            count += 1

    # 也处理有签到但无排班的员工（标记为"未排班"）
    from app.models.checkin import Checkin
    checkin_data = db.query(
        func.date(Checkin.checkin_time).label('d'),
        Checkin.emp_no
    ).filter(
        func.date(Checkin.checkin_time) >= start,
        func.date(Checkin.checkin_time) <= end,
        Checkin.emp_no.isnot(None),
        Checkin.emp_no != ''
    ).distinct().all()

    emp_no_cache = {e.emp_no: e.id for e in db.query(Employee).all()}
    for cd in checkin_data:
        emp_id = emp_no_cache.get(cd[1])
        if emp_id:
            key = (emp_id, cd[0])
            if key not in processed:
                processed.add(key)
                save_daily_report(db, emp_id, cd[0])
                count += 1

    db.commit()
    log_operation(db, current_user["id"], "recalculate_attendance", "reports", None, {"start_date": start_date, "end_date": end_date, "count": count})
    return {"message": f"重算完成，共处理{count}条记录", "count": count}


@router.get("/dashboard-export")
def export_dashboard(
    year_month: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导出仪表盘全部数据为 CSV（多段：统计、每日趋势、班组工时、每日产量、班组产量）"""
    require_permission(current_user, "reports.dashboard_export")

    def _get_ym():
        now = datetime.now()
        return now.year, now.month

    def _get_long_hour_threshold():
        config = db.query(AttendanceConfig).filter(AttendanceConfig.key == "long_hour_threshold").first()
        if config and config.value:
            try:
                return float(config.value)
            except ValueError:
                pass
        return 9.5

    if year_month:
        parts = year_month.split("-")
        year, month = int(parts[0]), int(parts[1])
    else:
        year, month = _get_ym()

    month_start = date(year, month, 1)
    month_end = date(year, month, monthrange(year, month)[1])

    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)

    # === Section 1: Stats ===
    writer.writerow(["== 月度统计 =="])
    employee_count = db.query(Employee).filter(Employee.status == "在职").count()
    latest_date = db.query(func.max(DailyReport.schedule_date)).scalar()
    month_reports = db.query(DailyReport).filter(
        extract("year", DailyReport.schedule_date) == year,
        extract("month", DailyReport.schedule_date) == month,
    ).all()
    monthly_total = len(month_reports)
    monthly_normal = len([r for r in month_reports if r.status == "正常"])
    monthly_absent = len([r for r in month_reports if r.status == "缺勤"])
    monthly_late = len([r for r in month_reports if r.status == "迟到"])
    monthly_leave = len([r for r in month_reports if r.status == "请假"])
    monthly_timeoff = len([r for r in month_reports if r.status == "休息"])
    monthly_actual_hours = sum(float(r.actual_hours or 0) for r in month_reports)
    monthly_scheduled_hours = sum(float(r.scheduled_hours or 0) for r in month_reports)
    monthly_overtime_hours = sum(float(r.overtime_hours or 0) for r in month_reports)
    attendance_rate = round(monthly_normal / monthly_total * 100, 1) if monthly_total > 0 else 0
    owed_hours = max(0, monthly_scheduled_hours - monthly_actual_hours - monthly_overtime_hours)
    writer.writerow(["总人数", "在职人数", "最新数据日期", "应出勤人次", "正常", "迟到", "缺勤", "请假", "休息", "计划工时", "实际工时", "加班工时", "欠时工时", "出勤率(%)"])
    writer.writerow([
        employee_count, employee_count,
        latest_date.isoformat() if latest_date else "",
        monthly_total, monthly_normal, monthly_late, monthly_absent, monthly_leave, monthly_timeoff,
        round(monthly_scheduled_hours, 1), round(monthly_actual_hours, 1),
        round(monthly_overtime_hours, 1), round(owed_hours, 1), attendance_rate
    ])
    writer.writerow([])

    # === Section 2: Daily Trend ===
    writer.writerow(["== 每日工时趋势 =="])
    threshold = _get_long_hour_threshold()
    rows = db.query(
        DailyReport.schedule_date, DailyReport.status,
        DailyReport.actual_hours, DailyReport.scheduled_hours,
    ).filter(
        extract("year", DailyReport.schedule_date) == year,
        extract("month", DailyReport.schedule_date) == month,
    ).order_by(DailyReport.schedule_date).all()
    daily = {}
    for r in rows:
        d = r.schedule_date.isoformat()
        if d not in daily:
            daily[d] = {"date": d, "应到人数": 0, "实际人数": 0, "正常": 0, "迟到": 0, "缺勤": 0,
                         "请假": 0, "休息": 0, "计划工时": 0.0, "实际工时": 0.0,
                         "≥9h": 0, "8~9h": 0, "7~8h": 0, "<7h": 0}
        daily[d]["应到人数"] += 1
        if r.status != "休息":
            daily[d]["实际人数"] += 1
        daily[d][r.status or "未知"] = daily[d].get(r.status, 0) + 1
        daily[d]["计划工时"] += float(r.scheduled_hours or 0)
        daily[d]["实际工时"] += float(r.actual_hours or 0)
        ah = float(r.actual_hours or 0)
        if ah >= threshold:
            daily[d]["≥9h"] += 1
        elif ah >= 8:
            daily[d]["8~9h"] += 1
        elif ah >= 7:
            daily[d]["7~8h"] += 1
        elif ah > 0:
            daily[d]["<7h"] += 1

    _, last_day = monthrange(year, month)
    all_dates = [f"{year}-{month:02d}-{day:02d}" for day in range(1, last_day + 1)]
    writer.writerow(["日期", "应到人数", "正常", "迟到", "缺勤", "请假", "休息", "计划工时", "实际工时", "≥9h", "8~9h", "7~8h", "<7h"])
    for d in all_dates:
        entry = daily.get(d, {"date": d, "应到人数": 0, "实际人数": 0, "正常": 0, "迟到": 0, "缺勤": 0,
                               "请假": 0, "休息": 0, "计划工时": 0.0, "实际工时": 0.0,
                               "≥9h": 0, "8~9h": 0, "7~8h": 0, "<7h": 0})
        writer.writerow([entry["date"], entry["应到人数"], entry.get("正常", 0), entry.get("迟到", 0),
                         entry.get("缺勤", 0), entry.get("请假", 0), entry.get("休息", 0),
                         round(entry["计划工时"], 1), round(entry["实际工时"], 1),
                         entry["≥9h"], entry["8~9h"], entry["7~8h"], entry["<7h"]])
    writer.writerow([])

    # === Section 3: Team Hours ===
    writer.writerow(["== 班组工时 =="])
    teams_data = db.query(Employee.team).filter(
        Employee.status == "在职", Employee.team.isnot(None),
    ).distinct().all()
    writer.writerow(["班组", "人数", "计划工时", "实际工时", "正常天数", "迟到天数", "缺勤天数"])
    for (team_name,) in teams_data:
        emp_ids = [e.id for e in db.query(Employee.id).filter(
            Employee.team == team_name,
            or_(Employee.hire_date.is_(None), Employee.hire_date <= month_end),
            or_(Employee.deleted_at.is_(None), Employee.deleted_at >= month_start),
        ).all()]
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
        writer.writerow([team_name, len(emp_ids), round(scheduled, 1), round(actual, 1), normal, late, absent])
    writer.writerow([])

    # === Section 4: Daily Production ===
    writer.writerow(["== 每日产量趋势 =="])
    emp_accounts = {e[0] for e in db.query(Employee.emp_no).filter(Employee.status == "在职").all()}
    if emp_accounts:
        start = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end = date(year, month, last_day)
        records = db.query(Workload).filter(
            Workload.date >= start, Workload.date <= end,
            Workload.account.in_(emp_accounts),
        ).all()
        prod_daily = {}
        for r in records:
            d = r.date.isoformat()
            if d not in prod_daily:
                prod_daily[d] = {"通话量": 0, "工单量": 0, "呼出量": 0, "人数": set()}
            m = r.metrics or {}
            prod_daily[d]["通话量"] += m.get("呼入人工服务-人工服务-通话次数", 0) or 0
            prod_daily[d]["工单量"] += m.get("呼入人工服务-工单-生成总量", 0) or 0
            prod_daily[d]["呼出量"] += m.get("呼出服务-人工呼出呼叫量", 0) or 0
            prod_daily[d]["人数"].add(r.account)
        writer.writerow(["日期", "通话量", "工单量", "呼出量", "人数"])
        for day_num in range(1, last_day + 1):
            d = date(year, month, day_num).isoformat()
            entry = prod_daily.get(d, {"通话量": 0, "工单量": 0, "呼出量": 0, "人数": set()})
            writer.writerow([d, entry["通话量"], entry["工单量"], entry["呼出量"], len(entry["人数"])])
        writer.writerow([])

    # === Section 5: Team Production ===
    writer.writerow(["== 班组产量对比 =="])
    if emp_accounts:
        start = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end = date(year, month, last_day)
        employees = db.query(Employee).filter(Employee.status == "在职").all()
        emp_map = {e.emp_no: e for e in employees}
        records = db.query(Workload).filter(
            Workload.date >= start, Workload.date <= end,
            Workload.account.in_(emp_accounts),
        ).all()
        team_prod = {}
        for r in records:
            emp = emp_map.get(r.account)
            team = emp.team if emp and emp.team else "未知班组"
            if team not in team_prod:
                team_prod[team] = {"通话量": 0, "工单量": 0, "呼出量": 0, "_people": set()}
            m = r.metrics or {}
            team_prod[team]["通话量"] += m.get("呼入人工服务-人工服务-通话次数", 0) or 0
            team_prod[team]["工单量"] += m.get("呼入人工服务-工单-生成总量", 0) or 0
            team_prod[team]["呼出量"] += m.get("呼出服务-人工呼出呼叫量", 0) or 0
            team_prod[team]["_people"].add(r.account)
        writer.writerow(["班组", "人数", "通话量", "工单量", "呼出量"])
        for team, data in team_prod.items():
            writer.writerow([team, len(data["_people"]), data["通话量"], data["工单量"], data["呼出量"]])

    filename = f"dashboard_{year}_{month:02d}.csv"
    output.seek(0)
    log_operation(db, current_user["id"], "export_dashboard", "reports", None, {"year_month": f"{year}-{month:02d}"})
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/efficiency-export")
def export_efficiency(
    type: str = Query("employee"),
    year_month: Optional[str] = Query(default=None),
    dept: Optional[str] = Query(default=None),
    team: Optional[str] = Query(default=None),
    start_month: Optional[str] = Query(default=None),
    end_month: Optional[str] = Query(default=None),
    emp_no: Optional[str] = Query(default=None),
    warn_type: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导出效能监控数据为 CSV（支持 employee/warning/ranking/trend 四种类型）"""
    require_permission(current_user, "reports.efficiency_export")

    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)

    now = datetime.now()
    ym = year_month or now.strftime("%Y-%m")

    if type == "employee":
        writer.writerow(["工号", "姓名", "班组", "部门", "出勤率(%)", "工时效率(%)", "计划工时", "实际工时", "加班", "迟到天数", "缺勤天数", "出勤天数"])
        parts = ym.split("-")
        y, m = int(parts[0]), int(parts[1])
        employees = db.query(Employee).filter(Employee.status == "在职")
        if team:
            employees = employees.filter(Employee.team == team)
        if dept:
            employees = employees.filter(Employee.dept == dept)
        for emp in employees.all():
            reports = db.query(DailyReport).filter(
                DailyReport.emp_id == emp.id,
                extract("year", DailyReport.schedule_date) == y,
                extract("month", DailyReport.schedule_date) == m,
            ).all()
            total = len(reports)
            if total == 0:
                continue
            normal = len([r for r in reports if r.status == "正常"])
            late = len([r for r in reports if r.status == "迟到"])
            absent = len([r for r in reports if r.status == "缺勤"])
            scheduled = sum(float(r.scheduled_hours or 0) for r in reports)
            actual = sum(float(r.actual_hours or 0) for r in reports)
            overtime = sum(float(r.overtime_hours or 0) for r in reports)
            work_days = len([r for r in reports if r.status not in ("休息", "缺勤")])
            attendance_rate = round(normal / total * 100, 1) if total > 0 else 0
            efficiency_rate = round(actual / scheduled * 100, 1) if scheduled > 0 else 0
            writer.writerow([emp.emp_no, emp.name, emp.team, emp.dept or "",
                           attendance_rate, efficiency_rate, round(scheduled, 1),
                           round(actual, 1), round(overtime, 1), late, absent, work_days])

    elif type == "warning":
        writer.writerow(["工号", "姓名", "班组", "部门", "预警类型", "次数", "详情"])
        parts = ym.split("-")
        y, m = int(parts[0]), int(parts[1])
        employees = db.query(Employee).filter(Employee.status == "在职").all()
        for emp in employees:
            reports = db.query(DailyReport).filter(
                DailyReport.emp_id == emp.id,
                extract("year", DailyReport.schedule_date) == y,
                extract("month", DailyReport.schedule_date) == m,
            ).all()
            if not reports:
                continue
            late_count = len([r for r in reports if r.status == "迟到"])
            absent_count = len([r for r in reports if r.status == "缺勤"])
            actual = sum(float(r.actual_hours or 0) for r in reports)
            scheduled = sum(float(r.scheduled_hours or 0) for r in reports)
            efficiency = round(actual / scheduled * 100, 1) if scheduled > 0 else 100

            if warn_type and warn_type not in ("late", "absent", "efficiency"):
                continue

            if (not warn_type or warn_type == "late") and late_count > 0:
                writer.writerow([emp.emp_no, emp.name, emp.team, emp.dept or "", "迟到预警", late_count, f"迟到{late_count}次"])
            if (not warn_type or warn_type == "absent") and absent_count > 0:
                writer.writerow([emp.emp_no, emp.name, emp.team, emp.dept or "", "缺勤预警", absent_count, f"缺勤{absent_count}次"])
            if (not warn_type or warn_type == "efficiency") and efficiency < 80:
                writer.writerow([emp.emp_no, emp.name, emp.team, emp.dept or "", "效率预警", 1, f"工时效率{efficiency}%"])

    elif type == "ranking":
        writer.writerow(["排名", "工号", "姓名", "班组", "部门", "效能得分", "出勤率(%)", "迟到天数", "缺勤天数"])
        parts = ym.split("-")
        y, m = int(parts[0]), int(parts[1])
        employees = db.query(Employee).filter(Employee.status == "在职")
        if dept:
            employees = employees.filter(Employee.dept == dept)
        rankings = []
        for emp in employees.all():
            reports = db.query(DailyReport).filter(
                DailyReport.emp_id == emp.id,
                extract("year", DailyReport.schedule_date) == y,
                extract("month", DailyReport.schedule_date) == m,
            ).all()
            if not reports:
                continue
            total = len(reports)
            normal = len([r for r in reports if r.status == "正常"])
            scheduled = sum(float(r.scheduled_hours or 0) for r in reports)
            actual = sum(float(r.actual_hours or 0) for r in reports)
            late = len([r for r in reports if r.status == "迟到"])
            absent = len([r for r in reports if r.status == "缺勤"])
            attendance_rate = round(normal / total * 100, 1) if total > 0 else 0
            efficiency_rate = round(actual / scheduled * 100, 1) if scheduled > 0 else 0
            score = round((attendance_rate + efficiency_rate) / 2, 1)
            rankings.append((score, emp.emp_no, emp.name, emp.team, emp.dept or "", attendance_rate, late, absent))
        rankings.sort(key=lambda x: x[0], reverse=True)
        for i, (score, en, name, team, dept_name, att_rate, late_c, absent_c) in enumerate(rankings, 1):
            writer.writerow([i, en, name, team, dept_name, score, att_rate, late_c, absent_c])

    elif type == "trend":
        writer.writerow(["月份", "工号", "姓名", "出勤率(%)", "工时效率(%)", "计划工时", "实际工时", "迟到天数", "缺勤天数", "出勤天数"])
        if not emp_no:
            writer.writerow(["请选择员工"])
        else:
            emp = db.query(Employee).filter(Employee.emp_no == emp_no).first()
            if emp:
                sm = start_month or ym
                em = end_month or ym
                start_parts = sm.split("-")
                end_parts = em.split("-")
                cur_y, cur_m = int(start_parts[0]), int(start_parts[1])
                end_y, end_m = int(end_parts[0]), int(end_parts[1])
                while (cur_y < end_y) or (cur_y == end_y and cur_m <= end_m):
                    reports = db.query(DailyReport).filter(
                        DailyReport.emp_id == emp.id,
                        extract("year", DailyReport.schedule_date) == cur_y,
                        extract("month", DailyReport.schedule_date) == cur_m,
                    ).all()
                    total = len(reports)
                    if total > 0:
                        normal = len([r for r in reports if r.status == "正常"])
                        late = len([r for r in reports if r.status == "迟到"])
                        absent = len([r for r in reports if r.status == "缺勤"])
                        scheduled = sum(float(r.scheduled_hours or 0) for r in reports)
                        actual = sum(float(r.actual_hours or 0) for r in reports)
                        work_days = len([r for r in reports if r.status not in ("休息", "缺勤")])
                        att_rate = round(normal / total * 100, 1) if total > 0 else 0
                        eff_rate = round(actual / scheduled * 100, 1) if scheduled > 0 else 0
                        ym_label = f"{cur_y}-{cur_m:02d}"
                        writer.writerow([ym_label, emp.emp_no, emp.name, att_rate, eff_rate,
                                       round(scheduled, 1), round(actual, 1), late, absent, work_days])
                    cur_m += 1
                    if cur_m > 12:
                        cur_m = 1
                        cur_y += 1

    filename = f"efficiency_{type}_{ym}.csv"
    output.seek(0)
    log_operation(db, current_user["id"], "export_efficiency", "reports", None, {"type": type, "year_month": ym})
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
