"""测试考勤数据准确性与仪表盘统计"""
import sys
from pathlib import Path
from datetime import date, datetime, time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

import pytest
from sqlalchemy import func
from app.models.database import SessionLocal, engine, Base
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.attendance_config import AttendanceConfig
from app.services.attendance import save_daily_report


def clear_tables(db):
    db.query(DailyReport).delete()
    db.query(Checkin).delete()
    db.query(Schedule).delete()
    db.query(ShiftType).delete()
    db.query(Employee).delete()
    db.query(AttendanceConfig).delete()
    db.commit()


def _setup_employees(db, emp_nos):
    result = {}
    for en in emp_nos:
        e = Employee(emp_no=en, name=f'员工{en}', team='一班1组', dept='客服中心', role='组员', status='在职')
        db.add(e)
        db.flush()
        result[en] = e.id
    db.commit()
    return result


def _setup_shift(db):
    s = ShiftType(shift_name='测试班', time_segments=[{"start": "09:00", "end": "18:00"}], work_hours=8.0, is_night=False)
    db.add(s)
    db.flush()
    db.commit()
    return s.id


def _setup_schedule(db, emp_id, date_obj, shift_id):
    s = Schedule(
        emp_id=emp_id, schedule_date=date_obj,
        shift_type_id=shift_id, shift_name='测试班',
        time_segments=[{"start": "09:00", "end": "18:00"}],
        work_hours=8.0, is_night=False, schedule_type='正常'
    )
    db.add(s)
    db.commit()


def _setup_report(db, emp_id, date_obj, shift_id, status):
    r = DailyReport(
        emp_id=emp_id, schedule_date=date_obj,
        shift_type_id=shift_id, schedule_type='正常',
        scheduled_start=time(9, 0), scheduled_end=time(18, 0),
        scheduled_hours=8.0, actual_hours=8.0,
        status=status, late_minutes=0, early_minutes=0, overtime_hours=0
    )
    db.add(r)
    db.commit()


class TestCheckinImportRecalculation:

    def test_all_employees_get_reports_after_checkin_import(self, db):
        """签到导入后，所有有排班的员工都必须有日报（包括无打卡的标记为缺勤）。"""
        clear_tables(db)
        today = date(2026, 6, 22)
        emps = _setup_employees(db, ['E001', 'E002', 'E003'])
        shift_id = _setup_shift(db)
        for eid in emps.values():
            _setup_schedule(db, eid, today, shift_id)

        # 模拟签到导入: 只导入2人（第三人不打卡）
        db.add(Checkin(emp_no='E001', name='员工E001', checkin_time=datetime(2026, 6, 22, 9, 0, 0), checkout_time=datetime(2026, 6, 22, 18, 0, 0), dept='客服中心', import_batch='test'))
        db.add(Checkin(emp_no='E002', name='员工E002', checkin_time=datetime(2026, 6, 22, 9, 0, 0), checkout_time=datetime(2026, 6, 22, 18, 0, 0), dept='客服中心', import_batch='test'))
        db.commit()

        # 模拟修复后的重算逻辑（checkins.py）
        dates = {today}
        processed = set()
        for d in dates:
            rows = db.query(Schedule.emp_id).filter(Schedule.schedule_date == d).distinct().all()
            for (eid,) in rows:
                key = (eid, d)
                if key in processed:
                    continue
                processed.add(key)
                save_daily_report(db, eid, d)

        reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).all()
        assert len(reports) == 3, f"应有3份日报，实际{len(reports)}"

        statuses = {r.status for r in reports}
        assert '正常' in statuses
        assert '缺勤' in statuses

        emp3_report = db.query(DailyReport).join(Employee, DailyReport.emp_id == Employee.id).filter(
            Employee.emp_no == 'E003', DailyReport.schedule_date == today
        ).first()
        assert emp3_report is not None
        assert emp3_report.status == '缺勤'

    def test_reimport_checkins_preserves_absent_status(self, db):
        """重新导入签到（部分员工无打卡）后，无打卡员工应变为缺勤。"""
        clear_tables(db)
        today = date(2026, 6, 23)
        emps = _setup_employees(db, ['E011', 'E012', 'E013'])
        shift_id = _setup_shift(db)
        for eid in emps.values():
            _setup_schedule(db, eid, today, shift_id)

        db.add(Checkin(emp_no='E011', name='员工E011', checkin_time=datetime(2026, 6, 23, 9, 0, 0), checkout_time=datetime(2026, 6, 23, 18, 0, 0), dept='客服中心', import_batch='b1'))
        db.add(Checkin(emp_no='E012', name='员工E012', checkin_time=datetime(2026, 6, 23, 9, 0, 0), checkout_time=datetime(2026, 6, 23, 18, 0, 0), dept='客服中心', import_batch='b1'))
        db.add(Checkin(emp_no='E013', name='员工E013', checkin_time=datetime(2026, 6, 23, 9, 0, 0), checkout_time=datetime(2026, 6, 23, 18, 0, 0), dept='客服中心', import_batch='b1'))
        db.commit()

        dates = {today}
        processed = set()
        for d in dates:
            rows = db.query(Schedule.emp_id).filter(Schedule.schedule_date == d).distinct().all()
            for (eid,) in rows:
                processed.add((eid, d))
                save_daily_report(db, eid, d)

        reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).all()
        assert len(reports) == 3
        assert all(r.status == '正常' for r in reports)

        # 模拟重新导入：删除旧打卡，只插入2人
        db.query(Checkin).filter(func.date(Checkin.checkin_time) == today).delete()
        db.commit()
        db.add(Checkin(emp_no='E011', name='员工E011', checkin_time=datetime(2026, 6, 23, 9, 0, 0), checkout_time=datetime(2026, 6, 23, 18, 0, 0), dept='客服中心', import_batch='b2'))
        db.add(Checkin(emp_no='E012', name='员工E012', checkin_time=datetime(2026, 6, 23, 9, 0, 0), checkout_time=datetime(2026, 6, 23, 18, 0, 0), dept='客服中心', import_batch='b2'))
        db.commit()

        for d in dates:
            rows = db.query(Schedule.emp_id).filter(Schedule.schedule_date == d).distinct().all()
            for (eid,) in rows:
                save_daily_report(db, eid, d)

        reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).all()
        assert len(reports) == 3

        emp3 = db.query(DailyReport).join(Employee, DailyReport.emp_id == Employee.id).filter(
            Employee.emp_no == 'E013', DailyReport.schedule_date == today
        ).first()
        assert emp3 is not None
        assert emp3.status == '缺勤', f"重新导入后无打卡员工应为缺勤，实际为{emp3.status}"

    def test_attendance_includes_late_early_overtime(self, db):
        """出勤=正常+迟到+早退+加班。"""
        clear_tables(db)
        today = date(2026, 6, 24)
        emps = _setup_employees(db, ['E021', 'E022', 'E023', 'E024'])
        shift_id = _setup_shift(db)
        for eid in emps.values():
            _setup_schedule(db, eid, today, shift_id)
        _setup_report(db, emps['E021'], today, shift_id, '正常')
        _setup_report(db, emps['E022'], today, shift_id, '迟到')
        _setup_report(db, emps['E023'], today, shift_id, '早退')
        _setup_report(db, emps['E024'], today, shift_id, '加班')

        reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).all()
        attendance = len([r for r in reports if r.status in ("正常", "迟到", "早退", "加班")])
        assert attendance == 4

    def test_absent_count(self, db):
        """缺勤=仅'缺勤'状态。"""
        clear_tables(db)
        today = date(2026, 6, 25)
        emps = _setup_employees(db, ['E031', 'E032'])
        shift_id = _setup_shift(db)
        for eid in emps.values():
            _setup_schedule(db, eid, today, shift_id)
        _setup_report(db, emps['E031'], today, shift_id, '正常')
        _setup_report(db, emps['E032'], today, shift_id, '缺勤')

        reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).all()
        assert len([r for r in reports if r.status == '缺勤']) == 1

    def test_all_categories_sum_to_total(self, db):
        """出勤+请假+休息+缺勤=当日总人数。"""
        clear_tables(db)
        today = date(2026, 6, 26)
        emps = _setup_employees(db, ['E041', 'E042', 'E043', 'E044', 'E045'])
        shift_id = _setup_shift(db)
        for eid in emps.values():
            _setup_schedule(db, eid, today, shift_id)

        statuses = {'E041': '正常', 'E042': '迟到', 'E043': '缺勤', 'E044': '请假', 'E045': '休息'}
        for en, st in statuses.items():
            _setup_report(db, emps[en], today, shift_id, st)

        reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).all()
        attendance = len([r for r in reports if r.status in ("正常", "迟到", "早退", "加班")])
        leave = len([r for r in reports if r.status == '请假'])
        timeoff = len([r for r in reports if r.status == '休息'])
        absent = len([r for r in reports if r.status == '缺勤'])

        total = attendance + leave + timeoff + absent
        assert total == len(reports), f"{attendance}+{leave}+{timeoff}+{absent}={total} != {len(reports)}"
        assert attendance == 2
        assert leave == 1
        assert timeoff == 1
        assert absent == 1


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for key in ["late_threshold_minutes", "early_leave_threshold_minutes"]:
            existing = db.query(AttendanceConfig).filter(AttendanceConfig.key == key).first()
            if existing:
                existing.value = "0"
            else:
                db.add(AttendanceConfig(key=key, value="0"))
        db.commit()
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])