from sqlalchemy.orm import Session
from sqlalchemy import and_, func, extract
from datetime import datetime, date, timedelta, time
import json
from typing import Optional
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.models.employee import Employee
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.monthly_report import MonthlyReport


def get_schedule_shift_info(schedule: Schedule, db: Session) -> Optional[dict]:
    if schedule.time_segments and schedule.work_hours is not None:
        return {
            "shift_name": schedule.shift_name,
            "time_segments": schedule.time_segments,
            "work_hours": float(schedule.work_hours),
            "is_night": schedule.is_night or False
        }
    if schedule.shift_type_id:
        shift = db.query(ShiftType).filter(ShiftType.id == schedule.shift_type_id).first()
        if shift:
            return {
                "shift_name": shift.shift_name,
                "time_segments": shift.time_segments,
                "work_hours": float(shift.work_hours),
                "is_night": shift.is_night or False
            }
    return None


def get_time_segments(shift: ShiftType) -> list:
    if not shift.time_segments:
        return []
    if isinstance(shift.time_segments, str):
        try:
            return json.loads(shift.time_segments)
        except:
            return []
    return shift.time_segments


def calculate_daily_attendance(db: Session, emp_id: int, schedule_date: date):
    schedule = db.query(Schedule).filter(
        and_(
            Schedule.emp_id == emp_id,
            Schedule.schedule_date == schedule_date
        )
    ).first()

    employee = db.query(Employee).filter(Employee.id == emp_id).first()
    
    checkins = db.query(Checkin).filter(
        and_(
            Checkin.emp_no == employee.emp_no,
            func.date(Checkin.checkin_time) == schedule_date
        )
    ).all()

    shift_info = get_schedule_shift_info(schedule, db) if schedule else None

    if not schedule:
        return {
            "status": "未排班",
            "late_minutes": 0,
            "early_minutes": 0,
            "actual_hours": 0,
            "scheduled_hours": 0,
            "overtime_hours": 0
        }

    def time_to_minutes(t: str) -> int:
        h, m = map(int, t.split(':'))
        return h * 60 + m

    def in_segment(c_in_h: int, c_in_m: int, c_out_h: int, c_out_m: int, seg_start: str, seg_end: str) -> bool:
        s = time_to_minutes(seg_start)
        e = time_to_minutes(seg_end)
        ci = c_in_h * 60 + c_in_m
        co = c_out_h * 60 + c_out_m
        if e < s:
            e += 1440
        if co < ci:
            co += 1440
        return ci < e and co > s

    def checkin_in_shifts(c: Checkin) -> bool:
        if not c.checkout_time or not shift_info:
            return False
        ci_h, ci_m = c.checkin_time.hour, c.checkin_time.minute
        co_h, co_m = c.checkout_time.hour, c.checkout_time.minute
        segments = shift_info["time_segments"]
        for seg in segments:
            if in_segment(ci_h, ci_m, co_h, co_m, seg["start"], seg["end"]):
                return True
        return False

    if schedule.schedule_type in ["请假", "公休", "加班"]:
        segments = (shift_info or {}).get("time_segments", [])
        scheduled_hours = shift_info["work_hours"] if shift_info else 0
        segment_details = [{
            "start": seg.get("start", ""),
            "end": seg.get("end", ""),
            "actual_checkin": None,
            "actual_checkout": None,
            "actual_hours": 0,
            "late_minutes": 0,
            "early_minutes": 0,
            "status": schedule.schedule_type
        } for seg in segments] if segments else []
        return {
            "status": schedule.schedule_type,
            "late_minutes": 0,
            "early_minutes": 0,
            "actual_hours": 0,
            "scheduled_hours": scheduled_hours,
            "overtime_hours": 0,
            "schedule_type": schedule.schedule_type,
            "time_segments": segments,
            "segment_details": segment_details
        }

    valid = [c for c in checkins if checkin_in_shifts(c)]

    if not valid:
        segments = shift_info["time_segments"] if shift_info else []
        scheduled_hours = shift_info["work_hours"] if shift_info else 0
        segment_details = [{
            "start": seg.get("start", ""),
            "end": seg.get("end", ""),
            "actual_checkin": None,
            "actual_checkout": None,
            "actual_hours": 0,
            "late_minutes": 0,
            "early_minutes": 0,
            "status": "缺勤"
        } for seg in segments] if segments else []
        return {
            "status": "缺勤",
            "late_minutes": 0,
            "early_minutes": 0,
            "actual_hours": 0,
            "scheduled_hours": scheduled_hours,
            "overtime_hours": 0,
            "time_segments": segments,
            "segment_details": segment_details
        }

    scheduled_hours = shift_info["work_hours"] if shift_info else 0

    first_checkin = min(valid, key=lambda x: x.checkin_time) if valid else None
    last_checkout = max((c for c in valid if c.checkout_time), key=lambda x: x.checkout_time) if any(c.checkout_time for c in valid) else None

    late_minutes = 0
    early_minutes = 0

    segments = shift_info["time_segments"] if shift_info else []
    segment_details = []
    if segments:
        def _checkin_range(c):
            ci = c.checkin_time.hour * 60 + c.checkin_time.minute
            co = c.checkout_time.hour * 60 + c.checkout_time.minute
            if c.checkout_time.date() > c.checkin_time.date():
                co += 1440
            return ci, co

        seg_ranges = []
        for seg in segments:
            s = time_to_minutes(seg["start"])
            e = time_to_minutes(seg["end"])
            if e <= s:
                e += 1440
            seg_ranges.append((s, e))

        n = len(segments)
        seg_has_checkin = [False] * n
        seg_last_effective_co = [None] * n
        seg_first_ci = [None] * n
        seg_actual_checkin_dt = [None] * n
        seg_actual_checkout_dt = [None] * n
        seg_actual_hours = [0.0] * n

        for c in valid:
            ci_m, co_m = _checkin_range(c)
            for idx, (s, e) in enumerate(seg_ranges):
                if ci_m < e and co_m > s:
                    seg_has_checkin[idx] = True
                    effective_co = min(co_m, e)
                    if seg_last_effective_co[idx] is None or effective_co > seg_last_effective_co[idx]:
                        seg_last_effective_co[idx] = effective_co
                    if seg_first_ci[idx] is None or ci_m < seg_first_ci[idx]:
                        seg_first_ci[idx] = ci_m
                        seg_actual_checkin_dt[idx] = c.checkin_time

        for c in valid:
            ci_m, co_m = _checkin_range(c)
            ci = c.checkin_time
            co = c.checkout_time
            ci_m2 = ci.hour * 60 + ci.minute
            co_m2 = co.hour * 60 + co.minute
            if co.date() > ci.date():
                co_m2 += 1440
            for idx, (s, e) in enumerate(seg_ranges):
                if ci_m < e and co_m > s:
                    effective_co_actual = min(co_m, e)
                    if seg_actual_checkout_dt[idx] is None or effective_co_actual > time_to_minutes(seg_actual_checkout_dt[idx].strftime('%H:%M')) if seg_actual_checkout_dt[idx] else 0:
                        if seg_actual_checkout_dt[idx] is None or c.checkout_time > seg_actual_checkout_dt[idx]:
                            seg_actual_checkout_dt[idx] = c.checkout_time
                    o_start = max(ci_m2, s)
                    o_end = min(co_m2, e)
                    if o_end > o_start:
                        seg_actual_hours[idx] += (o_end - o_start) / 60.0

        first_attended_idx = -1
        for idx in range(n):
            if seg_has_checkin[idx]:
                first_attended_idx = idx
                break

        if first_attended_idx >= 0:
            seg_start_mins = seg_ranges[first_attended_idx][0]
            if seg_first_ci[first_attended_idx] is not None and seg_first_ci[first_attended_idx] > seg_start_mins:
                late_minutes = seg_first_ci[first_attended_idx] - seg_start_mins

        early_minutes_list = []
        for idx in range(n):
            if seg_has_checkin[idx] and seg_last_effective_co[idx] is not None:
                seg_end_mins = seg_ranges[idx][1]
                if seg_last_effective_co[idx] < seg_end_mins:
                    early_minutes_list.append(seg_end_mins - seg_last_effective_co[idx])
        early_minutes = min(early_minutes_list) if early_minutes_list else 0

        # 构建每段详情
        for idx in range(n):
            seg = segments[idx]
            seg_late = 0
            seg_early = 0
            seg_status = "正常"
            if seg_has_checkin[idx]:
                s_mins = seg_ranges[idx][0]
                if seg_first_ci[idx] is not None and seg_first_ci[idx] > s_mins:
                    seg_late = seg_first_ci[idx] - s_mins
                e_mins = seg_ranges[idx][1]
                if seg_last_effective_co[idx] is not None and seg_last_effective_co[idx] < e_mins:
                    seg_early = e_mins - seg_last_effective_co[idx]
                if seg_late > 0:
                    seg_status = "迟到"
                elif seg_early > 0:
                    seg_status = "早退"
            else:
                seg_status = "缺勤"

            seg_ci = seg_actual_checkin_dt[idx]
            seg_co = seg_actual_checkout_dt[idx]
            segment_details.append({
                "start": seg["start"],
                "end": seg["end"],
                "actual_checkin": seg_ci.isoformat() if seg_ci else None,
                "actual_checkout": seg_co.isoformat() if seg_co else None,
                "actual_hours": round(seg_actual_hours[idx], 1),
                "late_minutes": seg_late,
                "early_minutes": seg_early,
                "status": seg_status
            })

    actual_hours = 0
    for c in valid:
        ci = c.checkin_time
        co = c.checkout_time
        ci_m = ci.hour * 60 + ci.minute
        co_m = co.hour * 60 + co.minute
        if co.date() > ci.date():
            co_m += 1440
        overlap = 0
        for seg in segments:
            s = time_to_minutes(seg["start"])
            e = time_to_minutes(seg["end"])
            if e < s:
                e += 1440
            o_start = max(ci_m, s)
            o_end = min(co_m, e)
            if o_end > o_start:
                overlap += o_end - o_start
        actual_hours += overlap / 60.0

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
        "schedule_type": schedule.schedule_type,
        "time_segments": segments,
        "segment_details": segment_details
    }

    def time_to_minutes(t: str) -> int:
        h, m = map(int, t.split(':'))
        return h * 60 + m

    def in_segment(c_in_h: int, c_in_m: int, c_out_h: int, c_out_m: int, seg_start: str, seg_end: str) -> bool:
        s = time_to_minutes(seg_start)
        e = time_to_minutes(seg_end)
        ci = c_in_h * 60 + c_in_m
        co = c_out_h * 60 + c_out_m
        if e < s:
            e += 1440
        if co < ci:
            co += 1440
        return ci < e and co > s

    def checkin_in_shifts(c: Checkin) -> bool:
        if not c.checkout_time or not shift_info:
            return False
        ci_h, ci_m = c.checkin_time.hour, c.checkin_time.minute
        co_h, co_m = c.checkout_time.hour, c.checkout_time.minute
        segments = shift_info["time_segments"]
        for seg in segments:
            if in_segment(ci_h, ci_m, co_h, co_m, seg["start"], seg["end"]):
                return True
        return False

    if schedule.schedule_type in ["请假", "公休", "加班"]:
        return {
            "status": schedule.schedule_type,
            "late_minutes": 0,
            "early_minutes": 0,
            "actual_hours": 0,
            "scheduled_hours": shift_info["work_hours"] if shift_info else 0,
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
            "scheduled_hours": shift_info["work_hours"] if shift_info else 0,
            "overtime_hours": 0
        }

    scheduled_hours = shift_info["work_hours"] if shift_info else 0

    first_checkin = min(valid, key=lambda x: x.checkin_time) if valid else None
    last_checkout = max((c for c in valid if c.checkout_time), key=lambda x: x.checkout_time) if any(c.checkout_time for c in valid) else None

    late_minutes = 0
    early_minutes = 0

    segments = shift_info["time_segments"] if shift_info else []
    if segments:
        def _checkin_range(c):
            ci = c.checkin_time.hour * 60 + c.checkin_time.minute
            co = c.checkout_time.hour * 60 + c.checkout_time.minute
            if c.checkout_time.date() > c.checkin_time.date():
                co += 1440
            return ci, co

        seg_ranges = []
        for seg in segments:
            s = time_to_minutes(seg["start"])
            e = time_to_minutes(seg["end"])
            if e <= s:
                e += 1440
            seg_ranges.append((s, e))

        n = len(segments)
        seg_has_checkin = [False] * n
        seg_last_effective_co = [None] * n
        seg_first_ci = [None] * n

        for c in valid:
            ci_m, co_m = _checkin_range(c)
            for idx, (s, e) in enumerate(seg_ranges):
                if ci_m < e and co_m > s:
                    seg_has_checkin[idx] = True
                    effective_co = min(co_m, e)
                    if seg_last_effective_co[idx] is None or effective_co > seg_last_effective_co[idx]:
                        seg_last_effective_co[idx] = effective_co
                    if seg_first_ci[idx] is None or ci_m < seg_first_ci[idx]:
                        seg_first_ci[idx] = ci_m

        first_attended_idx = -1
        for idx in range(n):
            if seg_has_checkin[idx]:
                first_attended_idx = idx
                break

        if first_attended_idx >= 0:
            seg_start_mins = seg_ranges[first_attended_idx][0]
            if seg_first_ci[first_attended_idx] is not None and seg_first_ci[first_attended_idx] > seg_start_mins:
                late_minutes = seg_first_ci[first_attended_idx] - seg_start_mins

        early_minutes_list = []
        for idx in range(n):
            if seg_has_checkin[idx] and seg_last_effective_co[idx] is not None:
                seg_end_mins = seg_ranges[idx][1]
                if seg_last_effective_co[idx] < seg_end_mins:
                    early_minutes_list.append(seg_end_mins - seg_last_effective_co[idx])
        early_minutes = min(early_minutes_list) if early_minutes_list else 0

    actual_hours = 0
    for c in valid:
        ci = c.checkin_time
        co = c.checkout_time
        ci_m = ci.hour * 60 + ci.minute
        co_m = co.hour * 60 + co.minute
        if co.date() > ci.date():
            co_m += 1440
        overlap = 0
        for seg in segments:
            s = time_to_minutes(seg["start"])
            e = time_to_minutes(seg["end"])
            if e < s:
                e += 1440
            o_start = max(ci_m, s)
            o_end = min(co_m, e)
            if o_end > o_start:
                overlap += o_end - o_start
        actual_hours += overlap / 60.0

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
        "schedule_type": schedule.schedule_type,
        "time_segments": segments
    }


def save_daily_report(db: Session, emp_id: int, schedule_date: date):
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

    segments = result.get("time_segments", [])
    scheduled_start = None
    scheduled_end = None
    if segments:
        first_seg = segments[0]
        last_seg = segments[-1]
        parts = first_seg["start"].split(':')
        scheduled_start = time(int(parts[0]), int(parts[1]))
        parts = last_seg["end"].split(':')
        scheduled_end = time(int(parts[0]), int(parts[1]))

    if existing:
        existing.status = result["status"]
        existing.late_minutes = result["late_minutes"]
        existing.early_minutes = result["early_minutes"]
        existing.actual_hours = result["actual_hours"]
        existing.overtime_hours = result["overtime_hours"]
        existing.actual_checkin = result.get("actual_checkin")
        existing.actual_checkout = result.get("actual_checkout")
        existing.shift_type_id = result.get("shift_type_id")
        existing.schedule_type = result.get("schedule_type")
        existing.scheduled_hours = result["scheduled_hours"]
        existing.scheduled_start = scheduled_start
        existing.scheduled_end = scheduled_end
        existing.segment_details = result.get("segment_details")
        existing.calculated_at = datetime.now()
    else:
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
            segment_details=result.get("segment_details"),
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