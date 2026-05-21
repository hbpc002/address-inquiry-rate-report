import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
temp_db.close()
os.environ['DATABASE_URL'] = f'sqlite:///{temp_db.name}'

from app.models.database import Base, SessionLocal, init_db
from app.models.employee import Employee
from app.models.shift_type import ShiftType
from app.models.schedule import Schedule
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.monthly_report import MonthlyReport
from app.models.attendance_config import AttendanceConfig
from app.services.attendance import calculate_daily_attendance, save_daily_report
from datetime import datetime, date, time


def setup_module():
    init_db()


def teardown_module():
    os.unlink(temp_db.name)


_emp_counter = 0


def _unique_emp_no():
    global _emp_counter
    _emp_counter += 1
    return f"T{_emp_counter:03d}"


def _clean_tables(db):
    for table in ["daily_reports", "monthly_reports", "checkins", "schedules", "shift_types", "employees", "attendance_configs"]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


def _seed_zero_thresholds(db):
    for key in ["late_threshold_minutes", "early_leave_threshold_minutes"]:
        existing = db.query(AttendanceConfig).filter(AttendanceConfig.key == key).first()
        if existing:
            existing.value = "0"
        else:
            db.add(AttendanceConfig(key=key, value="0"))
    db.commit()


class TestSingleSegment:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            _seed_zero_thresholds(db)
        finally:
            db.close()

    def test_on_time(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp)
            db.commit()
            db.refresh(emp)
            shift = ShiftType(shift_name="白班", time_segments=[{"start": "08:00", "end": "12:00"}], work_hours=4.0)
            db.add(shift)
            db.commit()
            db.refresh(shift)
            sched = Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id)
            db.add(sched)
            db.commit()
            c = Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 8, 0, 0), checkout_time=datetime(2024, 3, 1, 12, 0, 0), import_batch="test")
            db.add(c)
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "正常"
            assert result["late_minutes"] == 0
            assert result["early_minutes"] == 0
            assert result["actual_hours"] == 4.0
        finally:
            db.close()

    def test_late(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp)
            db.commit()
            db.refresh(emp)
            shift = ShiftType(shift_name="白班晚到", time_segments=[{"start": "08:00", "end": "12:00"}], work_hours=4.0)
            db.add(shift)
            db.commit()
            db.refresh(shift)
            sched = Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id)
            db.add(sched)
            db.commit()
            c = Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 8, 30, 0), checkout_time=datetime(2024, 3, 1, 12, 0, 0), import_batch="test")
            db.add(c)
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "迟到"
            assert result["late_minutes"] == 30
            assert result["actual_hours"] == 3.5
        finally:
            db.close()

    def test_early_departure(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp)
            db.commit()
            db.refresh(emp)
            shift = ShiftType(shift_name="白班早退", time_segments=[{"start": "08:00", "end": "12:00"}], work_hours=4.0)
            db.add(shift)
            db.commit()
            db.refresh(shift)
            sched = Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id)
            db.add(sched)
            db.commit()
            c = Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 8, 0, 0), checkout_time=datetime(2024, 3, 1, 11, 30, 0), import_batch="test")
            db.add(c)
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "早退"
            assert result["early_minutes"] == 30
            assert result["actual_hours"] == 3.5
        finally:
            db.close()

    def test_both_late_and_early(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp)
            db.commit()
            db.refresh(emp)
            shift = ShiftType(shift_name="白班早晚", time_segments=[{"start": "08:00", "end": "12:00"}], work_hours=4.0)
            db.add(shift)
            db.commit()
            db.refresh(shift)
            sched = Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id)
            db.add(sched)
            db.commit()
            c = Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 8, 20, 0), checkout_time=datetime(2024, 3, 1, 11, 40, 0), import_batch="test")
            db.add(c)
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "迟到"
            assert result["late_minutes"] == 20
            assert result["early_minutes"] == 20
            assert result["actual_hours"] == 3.3
        finally:
            db.close()


class TestTwoSegments:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            _seed_zero_thresholds(db)
        finally:
            db.close()

    def test_both_on_time(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="早晚班", time_segments=[{"start": "08:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}], work_hours=8.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 8, 0, 0), checkout_time=datetime(2024, 3, 1, 12, 0, 0), import_batch="test"))
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 13, 0, 0), checkout_time=datetime(2024, 3, 1, 17, 0, 0), import_batch="test"))
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "正常"
            assert result["late_minutes"] == 0
            assert result["early_minutes"] == 0
            assert result["actual_hours"] == 8.0
        finally:
            db.close()

    def test_first_segment_early_only(self):
        """早退出在非末段（旧代码遗漏的场景）"""
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="早晚班早退1", time_segments=[{"start": "08:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}], work_hours=8.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 8, 0, 0), checkout_time=datetime(2024, 3, 1, 11, 30, 0), import_batch="test"))
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 13, 0, 0), checkout_time=datetime(2024, 3, 1, 17, 0, 0), import_batch="test"))
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "早退"
            assert result["early_minutes"] == 30
            assert result["actual_hours"] == 7.5
        finally:
            db.close()

    def test_both_segments_early(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="早晚班早退2", time_segments=[{"start": "08:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}], work_hours=8.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 8, 0, 0), checkout_time=datetime(2024, 3, 1, 11, 30, 0), import_batch="test"))
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 13, 0, 0), checkout_time=datetime(2024, 3, 1, 16, 30, 0), import_batch="test"))
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "早退"
            assert result["early_minutes"] == 30
            assert result["actual_hours"] == 7.0
        finally:
            db.close()

    def test_miss_morning_late_afternoon(self):
        """上午缺勤，下午迟到5分钟"""
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="早晚班下午到", time_segments=[{"start": "08:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}], work_hours=8.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 13, 5, 0), checkout_time=datetime(2024, 3, 1, 17, 0, 0), import_batch="test"))
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "迟到"
            assert result["late_minutes"] == 5
            assert result["actual_hours"] == 3.9
        finally:
            db.close()

    def test_miss_morning_on_time_afternoon(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="早晚班下午到2", time_segments=[{"start": "08:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}], work_hours=8.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 13, 0, 0), checkout_time=datetime(2024, 3, 1, 17, 0, 0), import_batch="test"))
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "正常"
            assert result["late_minutes"] == 0
            assert result["actual_hours"] == 4.0
        finally:
            db.close()

    def test_late_morning_early_afternoon(self):
        """上午迟到10分 + 下午早退30分"""
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="早晚班早晚", time_segments=[{"start": "08:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}], work_hours=8.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 8, 10, 0), checkout_time=datetime(2024, 3, 1, 12, 0, 0), import_batch="test"))
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 13, 0, 0), checkout_time=datetime(2024, 3, 1, 16, 30, 0), import_batch="test"))
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "迟到"
            assert result["late_minutes"] == 10
            assert result["early_minutes"] == 30
            assert result["actual_hours"] == 7.3
        finally:
            db.close()

    def test_only_morning_attended_no_early(self):
        """用户报告的场景：多段班只打了上午卡，不应早退"""
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="农诗琪", team="一班3组", dept="客服中心")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="多段班", time_segments=[
                {"start": "08:00", "end": "12:30"},
                {"start": "14:00", "end": "17:30"}
            ], work_hours=8.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2026, 5, 13), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="农诗琪", checkin_time=datetime(2026, 5, 13, 8, 0, 43), checkout_time=datetime(2026, 5, 13, 12, 35, 34), import_batch="test"))
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2026, 5, 13))
            assert result["status"] == "正常"
            assert result["late_minutes"] == 0
            assert result["early_minutes"] == 0
            assert result["actual_hours"] == 4.5
        finally:
            db.close()

    def test_save_daily_report_multi_segment_range(self):
        """保存后 scheduled_start 是首段开始，scheduled_end 是末段结束"""
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="多段范围", time_segments=[
                {"start": "08:00", "end": "12:30"},
                {"start": "14:00", "end": "17:30"}
            ], work_hours=8.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2026, 5, 13), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2026, 5, 13, 8, 0, 0), checkout_time=datetime(2026, 5, 13, 12, 30, 0), import_batch="test"))
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2026, 5, 13, 14, 0, 0), checkout_time=datetime(2026, 5, 13, 17, 30, 0), import_batch="test"))
            db.commit()

            save_daily_report(db, emp.id, date(2026, 5, 13))
            report = db.query(DailyReport).filter(
                DailyReport.emp_id == emp.id,
                DailyReport.schedule_date == date(2026, 5, 13)
            ).first()
            assert report is not None
            assert str(report.scheduled_start) == "08:00:00"
            assert str(report.scheduled_end) == "17:30:00"
        finally:
            db.close()


class TestCrossMidnight:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            _seed_zero_thresholds(db)
        finally:
            db.close()

    def test_on_time(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="夜班", time_segments=[{"start": "22:00", "end": "06:00"}], work_hours=8.0, is_night=True)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 22, 0, 0), checkout_time=datetime(2024, 3, 2, 6, 0, 0), import_batch="test"))
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "正常"
            assert result["late_minutes"] == 0
            assert result["early_minutes"] == 0
            assert result["actual_hours"] == 8.0
        finally:
            db.close()

    def test_late(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="夜班迟到", time_segments=[{"start": "22:00", "end": "06:00"}], work_hours=8.0, is_night=True)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 23, 0, 0), checkout_time=datetime(2024, 3, 2, 6, 0, 0), import_batch="test"))
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "迟到"
            assert result["late_minutes"] == 60
            assert result["actual_hours"] == 7.0
        finally:
            db.close()

    def test_early_departure(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="夜班早退", time_segments=[{"start": "22:00", "end": "06:00"}], work_hours=8.0, is_night=True)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 22, 0, 0), checkout_time=datetime(2024, 3, 2, 5, 30, 0), import_batch="test"))
            db.commit()

            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "早退"
            assert result["early_minutes"] == 30
            assert result["actual_hours"] == 7.5
        finally:
            db.close()


class TestEdgeCases:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            _seed_zero_thresholds(db)
        finally:
            db.close()

    def test_no_schedule(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 8, 0, 0), checkout_time=datetime(2024, 3, 1, 12, 0, 0), import_batch="test"))
            db.commit()
            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "未排班"
        finally:
            db.close()

    def test_on_leave(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="白班请假", time_segments=[{"start": "08:00", "end": "12:00"}], work_hours=4.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id, schedule_type="请假"))
            db.commit()
            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "请假"
            assert result["actual_hours"] == 0
        finally:
            db.close()

    def test_absent_no_checkin(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="白班缺勤", time_segments=[{"start": "08:00", "end": "12:00"}], work_hours=4.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "缺勤"
        finally:
            db.close()

    def test_no_checkout_marked_absent(self):
        """打了卡但没签退，返回缺勤"""
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="白班无签退", time_segments=[{"start": "08:00", "end": "12:00"}], work_hours=4.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 8, 0, 0), checkout_time=None, import_batch="test"))
            db.commit()
            result = calculate_daily_attendance(db, emp.id, date(2024, 3, 1))
            assert result["status"] == "缺勤"
        finally:
            db.close()

    def test_save_and_read_daily_report(self):
        db = SessionLocal()
        try:
            emp_no = _unique_emp_no()
            emp = Employee(emp_no=emp_no, name="测试员工", team="测试班组", dept="测试部门")
            db.add(emp); db.commit(); db.refresh(emp)
            shift = ShiftType(shift_name="白班持久化", time_segments=[{"start": "08:00", "end": "12:00"}], work_hours=4.0)
            db.add(shift); db.commit(); db.refresh(shift)
            db.add(Schedule(emp_id=emp.id, schedule_date=date(2024, 3, 1), shift_type_id=shift.id))
            db.commit()
            db.add(Checkin(emp_no=emp_no, name="测试员工", checkin_time=datetime(2024, 3, 1, 8, 15, 0), checkout_time=datetime(2024, 3, 1, 12, 0, 0), import_batch="test"))
            db.commit()

            save_daily_report(db, emp.id, date(2024, 3, 1))
            report = db.query(DailyReport).filter(
                DailyReport.emp_id == emp.id,
                DailyReport.schedule_date == date(2024, 3, 1)
            ).first()
            assert report is not None
            assert report.status == "迟到"
            assert report.late_minutes == 15
            assert float(report.actual_hours) == 3.8
        finally:
            db.close()