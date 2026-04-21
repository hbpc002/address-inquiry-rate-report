from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from datetime import datetime, date, timedelta
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.models.employee import Employee
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.monthly_report import MonthlyReport


def calculate_daily_attendance(db: Session, emp_id: int, schedule_date: date):
    """计算单个员工单天考勤"""
    schedule = db.query(Schedule).filter(
        and_(
            Schedule.emp_id == emp_id,
            Schedule.schedule_date == schedule_date
        )
    ).first()

    checkins = db.query(Checkin).filter(
        and_(
            Checkin.emp_no == db.query(Employee).filter(Employee.id == emp_id).first().emp_no,
            func.date(Checkin.checkin_time) == schedule_date
        )
    ).all()

    if not schedule:
        return {
            "status": "未排班",
            "late_minutes": 0,
            "early_minutes": 0,
            "actual_hours": 0,
            "scheduled_hours": 0,
            "overtime_hours": 0
        }

    shift = db.query(ShiftType).filter(ShiftType.id == schedule.shift_type_id).first() if schedule.shift_type_id else None
    scheduled_hours = shift.work_hours if shift else 0

    if schedule.schedule_type in ["请假", "公休", "加班"]:
        return {
            "status": schedule.schedule_type,
            "late_minutes": 0,
            "early_minutes": 0,
            "actual_hours": 0,
            "scheduled_hours": scheduled_hours,
            "overtime_hours": 0,
            "schedule_type": schedule.schedule_type
        }

    if not checkins:
        return {
            "status": "缺勤",
            "late_minutes": 0,
            "early_minutes": 0,
            "actual_hours": 0,
            "scheduled_hours": scheduled_hours,
            "overtime_hours": 0
        }

    first_checkin = min(checkins, key=lambda x: x.checkin_time)
    checkout_candidates = [c for c in checkins if c.checkout_time]
    last_checkout = max(checkout_candidates, key=lambda x: x.checkout_time) if checkout_candidates else None

    late_minutes = 0
    early_minutes = 0

    if shift:
        if first_checkin.checkin_time.time() > datetime.strptime(shift.start_time, '%H:%M').time():
            late_minutes = (datetime.combine(schedule_date, first_checkin.checkin_time.time()) - 
                          datetime.combine(schedule_date, datetime.strptime(shift.start_time, '%H:%M').time())).seconds // 60

        if last_checkout and last_checkout.checkout_time.time() < datetime.strptime(shift.end_time, '%H:%M').time():
            early_minutes = (datetime.combine(schedule_date, datetime.strptime(shift.end_time, '%H:%M').time()) -
                           datetime.combine(schedule_date, last_checkout.checkout_time.time())).seconds // 60

    actual_hours = 0
    if first_checkin and last_checkout:
        actual_hours = (last_checkout.checkout_time - first_checkin.checkin_time).seconds / 3600

    overtime_hours = max(0, actual_hours - scheduled_hours) if scheduled_hours else 0

    if late_minutes > 0:
        status = "迟到"
    elif early_minutes > 0:
        status = "早退"
    else:
        status = "正常"

    return {
        "status": status,
        "late_minutes": late_minutes,
        "early_minutes": early_minutes,
        "actual_hours": round(actual_hours, 1),
        "scheduled_hours": scheduled_hours,
        "overtime_hours": round(overtime_hours, 1),
        "actual_checkin": first_checkin.checkin_time,
        "actual_checkout": last_checkout.checkout_time if last_checkout else None,
        "shift_type_id": schedule.shift_type_id,
        "schedule_type": schedule.schedule_type
    }


def save_daily_report(db: Session, emp_id: int, schedule_date: date):
    """保存或更新考勤汇总"""
    employee = db.query(Employee).filter(Employee.id == emp_id).first()
    if not employee:
        return

    result = calculate_daily_attendance(db, emp_id, schedule_date)

    existing = db.query(DailyReport).filter(
        and_(
            DailyReport.emp_id == emp_id,
            DailyReport.schedule_date == schedule_date
        )
    ).first()

    if existing:
        existing.status = result["status"]
        existing.late_minutes = result["late_minutes"]
        existing.early_minutes = result["early_minutes"]
        existing.actual_hours = result["actual_hours"]
        existing.overtime_hours = result["overtime_hours"]
        existing.actual_checkin = result.get("actual_checkin")
        existing.actual_checkout = result.get("actual_checkout")
        existing.calculated_at = datetime.now()
    else:
        shift = db.query(ShiftType).filter(ShiftType.id == result.get("shift_type_id")).first() if result.get("shift_type_id") else None
        report = DailyReport(
            emp_id=emp_id,
            schedule_date=schedule_date,
            shift_type_id=result.get("shift_type_id"),
            schedule_type=result.get("schedule_type"),
            scheduled_start=shift.start_time if shift else None,
            scheduled_end=shift.end_time if shift else None,
            scheduled_hours=result["scheduled_hours"],
            actual_checkin=result.get("actual_checkin"),
            actual_checkout=result.get("actual_checkout"),
            actual_hours=result["actual_hours"],
            status=result["status"],
            late_minutes=result["late_minutes"],
            early_minutes=result["early_minutes"],
            overtime_hours=result["overtime_hours"],
            calculated_at=datetime.now()
        )
        db.add(report)

    db.commit()


def calculate_monthly_summary(db: Session, emp_id: int, year_month: str):
    """计算月度汇总"""
    year, month = map(int, year_month.split('-'))
    
    daily_reports = db.query(DailyReport).filter(
        and_(
            DailyReport.emp_id == emp_id,
            extract('year', DailyReport.schedule_date) == year,
            extract('month', DailyReport.schedule_date) == month
        )
    ).all()

    scheduled = sum(float(r.scheduled_hours or 0) for r in daily_reports)
    actual = sum(float(r.actual_hours or 0) for r in daily_reports)
    overtime = sum(float(r.overtime_hours or 0) for r in daily_reports)

    normal_days = len([r for r in daily_reports if r.status == "正常"])
    late_days = len([r for r in daily_reports if r.status == "迟到"])
    early_days = len([r for r in daily_reports if r.status == "早退"])
    absent_days = len([r for r in daily_reports if r.status == "缺勤"])
    leave_days = len([r for r in daily_reports if r.status == "请假"])
    timeoff_days = len([r for r in daily_reports if r.status == "公休"])

    owed_hours = max(0, scheduled - actual - overtime)

    existing = db.query(MonthlyReport).filter(
        and_(
            MonthlyReport.emp_id == emp_id,
            MonthlyReport.year_month == year_month
        )
    ).first()

    if existing:
        existing.scheduled_hours = scheduled
        existing.actual_hours = actual
        existing.overtime_hours = overtime
        existing.owed_hours = owed_hours
        existing.normal_days = normal_days
        existing.late_days = late_days
        existing.early_days = early_days
        existing.absent_days = absent_days
        existing.leave_days = leave_days
        existing.timeoff_days = timeoff_days
        existing.calculated_at = datetime.now()
    else:
        report = MonthlyReport(
            emp_id=emp_id,
            year_month=year_month,
            scheduled_hours=scheduled,
            actual_hours=actual,
            overtime_hours=overtime,
            owed_hours=owed_hours,
            normal_days=normal_days,
            late_days=late_days,
            early_days=early_days,
            absent_days=absent_days,
            leave_days=leave_days,
            timeoff_days=timeoff_days,
            calculated_at=datetime.now()
        )
        db.add(report)

    db.commit()