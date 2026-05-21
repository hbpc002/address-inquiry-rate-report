"""测试考勤报表分段详情"""
import sys
from pathlib import Path
from datetime import date, datetime, time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

import pytest
from app.models.database import SessionLocal, engine, Base
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.services.attendance import calculate_daily_attendance, save_daily_report


def clear_tables(db):
    db.query(DailyReport).delete()
    db.query(Checkin).delete()
    db.query(Schedule).delete()
    db.query(ShiftType).delete()
    db.query(Employee).delete()
    db.commit()


class TestSegmentDetails:

    def _setup_emp_shift_checkins(self, db, emp_no, name, shift_name, time_segments, work_hours, schedule_date, checkins):
        clear_tables(db)
        emp = Employee(emp_no=emp_no, name=name, team="一班1组", dept="客服中心", role="组员", status="在职")
        db.add(emp)
        db.flush()

        shift = ShiftType(shift_name=shift_name, time_segments=time_segments, work_hours=work_hours, is_night=False)
        db.add(shift)
        db.flush()

        s = Schedule(
            emp_id=emp.id,
            schedule_date=schedule_date,
            shift_type_id=shift.id,
            shift_name=shift_name,
            time_segments=time_segments,
            work_hours=work_hours,
            is_night=False,
            schedule_type="正常"
        )
        db.add(s)
        db.flush()

        for ci, co in checkins:
            c = Checkin(
                emp_no=emp_no,
                name=name,
                checkin_time=ci,
                checkout_time=co,
                dept="客服中心",
                import_batch="test"
            )
            db.add(c)
        db.commit()
        return emp

    def test_single_segment_no_segment_details(self, db):
        emp = self._setup_emp_shift_checkins(
            db, "T001", "测试A", "行政班",
            [{"start": "09:00", "end": "18:00"}], 8.0,
            date(2026, 5, 15),
            [(datetime(2026, 5, 15, 9, 0, 0), datetime(2026, 5, 15, 18, 0, 0))]
        )
        result = calculate_daily_attendance(db, emp.id, date(2026, 5, 15))
        assert result["segment_details"] is not None
        assert len(result["segment_details"]) == 1
        assert result["segment_details"][0]["start"] == "09:00"
        assert result["segment_details"][0]["end"] == "18:00"
        assert result["segment_details"][0]["status"] == "正常"
        assert result["segment_details"][0]["actual_hours"] > 0

    def test_multi_segment_two_details(self, db):
        emp = self._setup_emp_shift_checkins(
            db, "T002", "测试B", "中班",
            [{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}], 8.0,
            date(2026, 5, 16),
            [
                (datetime(2026, 5, 16, 9, 30, 0), datetime(2026, 5, 16, 13, 30, 0)),
                (datetime(2026, 5, 16, 16, 0, 0), datetime(2026, 5, 16, 20, 0, 0)),
            ]
        )
        result = calculate_daily_attendance(db, emp.id, date(2026, 5, 16))
        assert len(result["segment_details"]) == 2
        assert result["segment_details"][0]["start"] == "09:30"
        assert result["segment_details"][0]["end"] == "13:30"
        assert result["segment_details"][0]["status"] == "正常"
        assert result["segment_details"][1]["start"] == "16:00"
        assert result["segment_details"][1]["end"] == "20:00"
        assert result["segment_details"][1]["status"] == "正常"

    def test_multi_segment_first_late(self, db):
        emp = self._setup_emp_shift_checkins(
            db, "T003", "测试C", "中班",
            [{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}], 8.0,
            date(2026, 5, 16),
            [
                (datetime(2026, 5, 16, 9, 45, 0), datetime(2026, 5, 16, 13, 30, 0)),
                (datetime(2026, 5, 16, 16, 0, 0), datetime(2026, 5, 16, 20, 0, 0)),
            ]
        )
        result = calculate_daily_attendance(db, emp.id, date(2026, 5, 16))
        assert len(result["segment_details"]) == 2
        assert result["segment_details"][0]["status"] == "迟到"
        assert result["segment_details"][0]["late_minutes"] == 15
        assert result["segment_details"][1]["status"] == "正常"
        assert result["segment_details"][1]["late_minutes"] == 0
        assert result["status"] == "迟到"
        assert result["late_minutes"] == 15

    def test_multi_segment_second_absent(self, db):
        emp = self._setup_emp_shift_checkins(
            db, "T004", "测试D", "中班",
            [{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}], 8.0,
            date(2026, 5, 16),
            [
                (datetime(2026, 5, 16, 9, 30, 0), datetime(2026, 5, 16, 13, 30, 0)),
            ]
        )
        result = calculate_daily_attendance(db, emp.id, date(2026, 5, 16))
        assert len(result["segment_details"]) == 2
        assert result["segment_details"][0]["status"] == "正常"
        assert result["segment_details"][1]["status"] == "缺勤"
        assert result["segment_details"][1]["actual_hours"] == 0

    def test_segment_details_persisted(self, db):
        emp = self._setup_emp_shift_checkins(
            db, "T005", "测试E", "中班",
            [{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}], 8.0,
            date(2026, 5, 16),
            [
                (datetime(2026, 5, 16, 9, 30, 0), datetime(2026, 5, 16, 13, 30, 0)),
                (datetime(2026, 5, 16, 16, 0, 0), datetime(2026, 5, 16, 20, 0, 0)),
            ]
        )
        save_daily_report(db, emp.id, date(2026, 5, 16))
        report = db.query(DailyReport).filter(DailyReport.emp_id == emp.id).first()
        assert report is not None
        assert report.segment_details is not None
        assert len(report.segment_details) == 2
        assert report.segment_details[0]["start"] == "09:30"
        assert report.segment_details[1]["start"] == "16:00"

    def test_leave_has_segment_details(self, db):
        clear_tables(db)
        emp = Employee(emp_no="T006", name="测试F", team="一班1组", dept="客服中心", role="组员", status="在职")
        db.add(emp)
        db.flush()
        shift = ShiftType(shift_name="中班", time_segments=[{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}], work_hours=8.0, is_night=False)
        db.add(shift)
        db.flush()
        s = Schedule(emp_id=emp.id, schedule_date=date(2026, 5, 16), shift_type_id=shift.id, shift_name="中班", time_segments=[{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}], work_hours=8.0, is_night=False, schedule_type="请假")
        db.add(s)
        db.commit()

        result = calculate_daily_attendance(db, emp.id, date(2026, 5, 16))
        assert result["schedule_type"] == "请假"
        assert len(result["segment_details"]) == 2
        assert result["segment_details"][0]["status"] == "请假"
        assert result["segment_details"][1]["status"] == "请假"

    def test_absent_has_segment_details(self, db):
        clear_tables(db)
        emp = Employee(emp_no="T007", name="测试G", team="一班1组", dept="客服中心", role="组员", status="在职")
        db.add(emp)
        db.flush()
        shift = ShiftType(shift_name="中班", time_segments=[{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}], work_hours=8.0, is_night=False)
        db.add(shift)
        db.flush()
        s = Schedule(emp_id=emp.id, schedule_date=date(2026, 5, 16), shift_type_id=shift.id, shift_name="中班", time_segments=[{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}], work_hours=8.0, is_night=False, schedule_type="正常")
        db.add(s)
        db.commit()

        result = calculate_daily_attendance(db, emp.id, date(2026, 5, 16))
        assert result["status"] == "缺勤"
        assert len(result["segment_details"]) == 2
        assert result["segment_details"][0]["status"] == "缺勤"
        assert result["segment_details"][1]["status"] == "缺勤"


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])