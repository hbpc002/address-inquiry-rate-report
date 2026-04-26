from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, extract, func
from typing import Optional, List
from datetime import datetime, date, timedelta
import io
import csv
from app.models.database import get_db
from app.models.employee import Employee
from app.models.daily_report import DailyReport
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.schemas.daily_report import DailyReportResponse, DailyReportListResponse
from app.core.security import get_current_user
from app.utils.logger import log_operation

router = APIRouter(prefix="/api/reports", tags=["考勤报表"])


@router.get("/daily", response_model=DailyReportListResponse)
def get_daily_reports(
    schedule_date: str = Query(...),
    team: Optional[str] = None,
    dept: Optional[str] = None,
    status: Optional[str] = None,
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

    items = query.order_by(Employee.name).all()

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
                calculated_at=item.calculated_at
            ))

    return DailyReportListResponse(items=result_items, total=len(result_items))


@router.get("/date-range", response_model=dict)
def get_reports_by_date_range(
    start_date: str = Query(...),
    end_date: str = Query(...),
    team: Optional[str] = None,
    dept: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """按日期范围查询考勤报表"""
    start = datetime.strptime(start_date, '%Y-%m-%d').date()
    end = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    query = db.query(DailyReport).join(Employee)
    query = query.filter(and_(
        DailyReport.schedule_date >= start,
        DailyReport.schedule_date <= end
    ))
    
    if team:
        query = query.filter(Employee.team == team)
    if dept:
        query = query.filter(Employee.dept == dept)
    if status:
        query = query.filter(DailyReport.status == status)
    
    items = query.order_by(DailyReport.schedule_date, Employee.name).all()
    
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
        
        status = item.status
        if status == "正常":
            summary["normal_days"] += 1
        elif status == "迟到":
            summary["late_days"] += 1
        elif status == "早退":
            summary["early_days"] += 1
        elif status == "缺勤":
            summary["absent_days"] += 1
        elif status == "请假":
            summary["leave_days"] += 1
        elif status == "公休":
            summary["timeoff_days"] += 1
    
    # 计算欠时
    for emp_key in emp_summary:
        s = emp_summary[emp_key]
        s["owed_hours"] = max(0, s["scheduled_hours"] - s["actual_hours"] - s["overtime_hours"])
    
    return {
        "items": list(emp_summary.values()),
        "total": len(emp_summary),
        "start_date": start_date,
        "end_date": end_date,
        "days": (end - start).days + 1
    }


@router.get("/month", response_model=DailyReportListResponse)
def get_month_reports(
    year_month: str = Query(...),
    team: Optional[str] = None,
    dept: Optional[str] = None,
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

    items = query.order_by(Employee.name).all()
    return DailyReportListResponse(
        items=[DailyReportResponse.model_validate(i) for i in items],
        total=len(items)
    )


@router.get("/month-summary", response_model=list)
def get_month_summary(
    year_month: str = Query(...),
    team: Optional[str] = None,
    dept: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    year, month = map(int, year_month.split('-'))

    employees = db.query(Employee).filter(Employee.status == "在职")
    if team:
        employees = employees.filter(Employee.team == team)
    if dept:
        employees = employees.filter(Employee.dept == dept)

    result = []
    for emp in employees.all():
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
        shift_cache = {}
        for s in schedules:
            if s.shift_type_id not in shift_cache:
                shift_cache[s.shift_type_id] = db.query(ShiftType).filter(ShiftType.id == s.shift_type_id).first()
            shift = shift_cache[s.shift_type_id]
            if shift:
                scheduled += float(shift.work_hours or 0)
        
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
            "timeoff_days": len([r for r in daily_reports if r.status == "公休"])
        })

    return result


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

    result = []
    for team_name, emp_count in teams:
        team_employees = db.query(Employee).filter(Employee.team == team_name).all()
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
            if s.shift_type_id not in shift_cache:
                shift_cache[s.shift_type_id] = db.query(ShiftType).filter(ShiftType.id == s.shift_type_id).first()
            shift = shift_cache[s.shift_type_id]
            if shift:
                total_scheduled += float(shift.work_hours or 0)
        
        total_actual = sum(float(r.actual_hours or 0) for r in daily_reports)
        total_overtime = sum(float(r.overtime_hours or 0) for r in daily_reports)
        
        late_count = len([r for r in daily_reports if r.status == "迟到"])
        absent_count = len([r for r in daily_reports if r.status == "缺勤"])
        
        work_days = len(schedules)
        avg_attendance = (work_days - absent_count) / work_days if work_days > 0 else 0

        result.append({
            "team": team_name,
            "emp_count": emp_count,
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

        writer.writerow(["工号", "姓名", "班组", "部门", "计划工时", "实际工时", "加班工时", "欠时工时", "正常天数", "迟到天数", "早退天数", "缺勤天数", "请假天数", "公休天数"])

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
                len([r for r in daily_reports if r.status == "公休"])
            ])
        filename = f"monthly_report_{year_month}.csv"

        output.seek(0)
    log_operation(db, current_user["id"], "export_report", "reports", None, {"export_type": type, "schedule_date": schedule_date})
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
