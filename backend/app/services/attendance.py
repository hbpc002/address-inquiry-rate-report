from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from datetime import datetime, date, timedelta, time
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

    employee = db.query(Employee).filter(Employee.id == emp_id).first()
    
    checkins = db.query(Checkin).filter(
        and_(
            Checkin.name == employee.name,
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

    def time_to_minutes(t: str) -> int:
        h, m = map(int, t.split(':'))
        return h * 60 + m

    def in_segment(c_in_h: int, c_in_m: int, c_out_h: int, c_out_m: int, seg_start: str, seg_end: str) -> bool:
        s = time_to_minutes(seg_start)
        e = time_to_minutes(seg_end)
        ci = c_in_h * 60 + c_in_m
        co = c_out_h * 60 + c_out_m
        if e > s:
            return s <= ci and co <= e
        else:
            return ci >= s or co <= e

    def checkin_in_shifts(c: Checkin) -> bool:
        if not c.checkout_time or not shift:
            return False
        ci_h, ci_m = c.checkin_time.hour, c.checkin_time.minute
        co_h, co_m = c.checkout_time.hour, c.checkout_time.minute
        seg1 = shift.start_time and shift.end_time and in_segment(ci_h, ci_m, co_h, co_m, shift.start_time, shift.end_time)
        seg2 = shift.start_time2 and shift.end_time2 and in_segment(ci_h, ci_m, co_h, co_m, shift.start_time2, shift.end_time2)
        return seg1 or seg2

    if schedule.schedule_type in ["请假", "公休", "加班"]:
        return {
            "status": schedule.schedule_type,
            "late_minutes": 0,
            "early_minutes": 0,
            "actual_hours": 0,
            "scheduled_hours": shift.work_hours if shift else 0,
            "overtime_hours": 0,
            "schedule_type": schedule.schedule_type
        }

    valid = [c for c in checkins if checkin_in_shifts(c)]

    if not valid:
        return {
            "status": "缺勤",
            "late_minutes": 0,
            "early_minutes": 0,
            "actual_hours": 0,
            "scheduled_hours": shift.work_hours if shift else 0,
            "overtime_hours": 0
        }

    scheduled_hours = shift.work_hours if shift else 0

    first_checkin = min(valid, key=lambda x: x.checkin_time)
    last_checkout = max((c for c in valid if c.checkout_time), key=lambda x: x.checkout_time)

    late_minutes = 0
    early_minutes = 0

    if shift and shift.start_time:
        shift_start = datetime.strptime(shift.start_time, '%H:%M').time()
        if first_checkin.checkin_time.time() > shift_start:
            late_minutes = (datetime.combine(schedule_date, first_checkin.checkin_time.time()) -
                          datetime.combine(schedule_date, shift_start)).seconds // 60

    if shift and shift.end_time:
        seg1_early = None
        if shift.start_time and shift.end_time:
            seg1_end = datetime.strptime(shift.end_time, '%H:%M').time()
            if last_checkout and last_checkout.checkout_time.time() < seg1_end:
                seg1_early = (datetime.combine(schedule_date, seg1_end) -
                            datetime.combine(schedule_date, last_checkout.checkout_time.time())).seconds // 60
        seg2_early = None
        if shift.start_time2 and shift.end_time2:
            seg2_end = datetime.strptime(shift.end_time2, '%H:%M').time()
            if last_checkout and last_checkout.checkout_time.time() < seg2_end:
                seg2_early = (datetime.combine(schedule_date, seg2_end) -
                            datetime.combine(schedule_date, last_checkout.checkout_time.time())).seconds // 60
        early_minutes = min(x for x in [seg1_early, seg2_early] if x is not None) if (seg1_early is not None or seg2_early is not None) else 0

    actual_hours = 0
    for c in valid:
        actual_hours += (c.checkout_time - c.checkin_time).seconds / 3600

    overtime_hours = max(0, actual_hours - float(scheduled_hours)) if scheduled_hours else 0

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
        scheduled_start = None
        scheduled_end = None
        if shift:
            if shift.start_time:
                parts = shift.start_time.split(':')
                scheduled_start = time(int(parts[0]), int(parts[1]))
            if shift.end_time:
                parts = shift.end_time.split(':')
                scheduled_end = time(int(parts[0]), int(parts[1]))
        report = DailyReport(
            emp_id=emp_id,
            schedule_date=schedule_date,
            shift_type_id=result.get("shift_type_id"),
            schedule_type=result.get("schedule_type"),
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
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