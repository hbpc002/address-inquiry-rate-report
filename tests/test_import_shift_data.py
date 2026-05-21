"""测试排班导入的班次数据正确性"""
import sys
from pathlib import Path
from datetime import date

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

import pytest
from app.models.database import SessionLocal, engine, Base
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.models.daily_report import DailyReport
from app.models.monthly_report import MonthlyReport
from app.api.schedules import parse_shift_from_cell, get_or_create_shift, parse_shift_from_header
from app.services.attendance import get_schedule_shift_info


def clear_tables(db):
    db.query(DailyReport).delete()
    db.query(MonthlyReport).delete()
    db.query(Schedule).delete()
    db.query(ShiftType).delete()
    db.query(Employee).delete()
    db.commit()


class TestParseShiftFromCell:

    def test_parse_zhongban_multi_segment(self):
        result = parse_shift_from_cell("中班（8.0）9:30-13:30  16:00-20:00")
        assert result is not None
        assert result["name"] == "中班"
        assert result["work_hours"] == 8.0
        assert result["time_segments"] == [
            {"start": "9:30", "end": "13:30"},
            {"start": "16:00", "end": "20:00"}
        ]

    def test_parse_waner_with_newline(self):
        result = parse_shift_from_cell("晚二（8.5) 12:30-17:00\n18:00-22:00")
        assert result is not None
        assert result["name"] == "晚二"
        assert result["work_hours"] == 8.5
        assert result["is_night"] is True
        assert result["time_segments"] == [
            {"start": "12:30", "end": "17:00"},
            {"start": "18:00", "end": "22:00"}
        ]

    def test_parse_xingzheng_with_training_note(self):
        result = parse_shift_from_cell("行政（8.5）8:00-12:30  14:00-18:00（14:30-17:00培训）")
        assert result is not None
        assert result["name"] == "行政"
        assert result["work_hours"] == 8.5
        assert len(result["time_segments"]) == 3

    def test_parse_three_segment(self):
        result = parse_shift_from_cell("早晚（8.0）9:30-13:00  16:00-18:30\n19:00-21:00")
        assert result is not None
        assert result["name"] == "早晚"
        assert len(result["time_segments"]) == 3

    def test_parse_single_segment(self):
        result = parse_shift_from_cell("上午（4.5H）8:00-12:30")
        assert result is not None
        assert result["name"] == "上午"
        assert result["work_hours"] == 4.5
        assert result["time_segments"] == [{"start": "8:00", "end": "12:30"}]

    def test_parse_rest_returns_none(self):
        assert parse_shift_from_cell("休息") is None

    def test_parse_empty_returns_none(self):
        assert parse_shift_from_cell("") is None
        assert parse_shift_from_cell(None) is None

    def test_parse_waner_with_hours_H_suffix(self):
        result = parse_shift_from_cell("晚二（8.0H) 12:30-17:00\n18:30-22:00")
        assert result is not None
        assert result["work_hours"] == 8.0
        assert result["name"] == "晚二"

    def test_parse_zhongban_with_hours_no_H(self):
        result = parse_shift_from_cell("中班（9.0）8:30-13:00  15:30-20:00")
        assert result is not None
        assert result["work_hours"] == 9.0
        assert result["time_segments"] == [
            {"start": "8:30", "end": "13:00"},
            {"start": "15:30", "end": "20:00"}
        ]

    def test_dedup_repeated_segment_from_note(self):
        result = parse_shift_from_cell("行政（8.0）8:00-12:30  14:30-18:00 （下午14:30-18:00到南分学习）")
        assert result is not None
        assert result["name"] == "行政"
        assert len(result["time_segments"]) == 2
        assert result["time_segments"] == [
            {"start": "8:00", "end": "12:30"},
            {"start": "14:30", "end": "18:00"}
        ]


class TestGetOrCreateShift:

    def test_create_new_shift(self, db):
        clear_tables(db)
        info = {"name": "测试班", "time_segments": [{"start": "09:00", "end": "18:00"}], "work_hours": 8.0, "is_night": False}
        shift = get_or_create_shift(db, info)
        assert shift.shift_name == "测试班"
        assert shift.work_hours == 8.0
        assert db.query(ShiftType).count() == 1

    def test_does_not_overwrite_existing(self, db):
        clear_tables(db)
        info1 = {"name": "中班", "time_segments": [{"start": "08:30", "end": "13:00"}, {"start": "15:30", "end": "19:30"}], "work_hours": 8.5, "is_night": False}
        shift1 = get_or_create_shift(db, info1)
        assert shift1.work_hours == 8.5

        info2 = {"name": "中班", "time_segments": [{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}], "work_hours": 8.0, "is_night": False}
        shift2 = get_or_create_shift(db, info2)
        assert shift2.id == shift1.id
        assert shift2.work_hours == 8.5
        assert shift2.time_segments == [{"start": "08:30", "end": "13:00"}, {"start": "15:30", "end": "19:30"}]

    def test_creates_multiple_distinct_names(self, db):
        clear_tables(db)
        get_or_create_shift(db, {"name": "早班", "time_segments": [{"start": "08:00", "end": "16:00"}], "work_hours": 8.0, "is_night": False})
        get_or_create_shift(db, {"name": "中班", "time_segments": [{"start": "16:00", "end": "24:00"}], "work_hours": 8.0, "is_night": False})
        assert db.query(ShiftType).count() == 2


class TestScheduleStoresOwnShiftData:

    def test_schedule_has_own_shift_fields(self, db):
        clear_tables(db)
        emp = Employee(emp_no="T001", name="测试员工", team="一班1组", dept="客服中心", role="组员", status="在职")
        db.add(emp)
        db.flush()

        shift_info = {"name": "中班", "time_segments": [{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}], "work_hours": 8.0, "is_night": False}
        shift = get_or_create_shift(db, shift_info)

        s1 = Schedule(
            emp_id=emp.id,
            schedule_date=date(2026, 5, 16),
            shift_type_id=shift.id,
            shift_name=shift_info["name"],
            time_segments=shift_info["time_segments"],
            work_hours=shift_info["work_hours"],
            is_night=shift_info["is_night"],
            schedule_type="正常"
        )
        db.add(s1)
        db.commit()

        s1 = db.query(Schedule).first()
        assert s1.shift_name == "中班"
        assert s1.time_segments == [{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}]
        assert s1.work_hours == 8.0
        assert s1.is_night is False

    def test_two_schedules_same_name_different_times(self, db):
        clear_tables(db)
        emp = Employee(emp_no="T002", name="测试员工2", team="一班1组", dept="客服中心", role="组员", status="在职")
        db.add(emp)
        db.flush()

        shift_info_1 = {"name": "中班", "time_segments": [{"start": "08:30", "end": "13:00"}, {"start": "15:30", "end": "19:30"}], "work_hours": 8.5, "is_night": False}
        shift_info_2 = {"name": "中班", "time_segments": [{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}], "work_hours": 8.0, "is_night": False}
        shift = get_or_create_shift(db, shift_info_1)

        s1 = Schedule(emp_id=emp.id, schedule_date=date(2026, 5, 6), shift_type_id=shift.id, shift_name=shift_info_1["name"], time_segments=shift_info_1["time_segments"], work_hours=shift_info_1["work_hours"], is_night=shift_info_1["is_night"], schedule_type="正常")
        s2 = Schedule(emp_id=emp.id, schedule_date=date(2026, 5, 16), shift_type_id=shift.id, shift_name=shift_info_2["name"], time_segments=shift_info_2["time_segments"], work_hours=shift_info_2["work_hours"], is_night=shift_info_2["is_night"], schedule_type="正常")
        db.add_all([s1, s2])
        db.commit()

        schedules = db.query(Schedule).order_by(Schedule.schedule_date).all()
        assert schedules[0].time_segments == [{"start": "08:30", "end": "13:00"}, {"start": "15:30", "end": "19:30"}]
        assert schedules[1].time_segments == [{"start": "09:30", "end": "13:30"}, {"start": "16:00", "end": "20:00"}]
        assert float(schedules[0].work_hours) == 8.5
        assert float(schedules[1].work_hours) == 8.0


class TestGetScheduleShiftInfo:

    def test_returns_schedule_own_fields(self, db):
        clear_tables(db)
        emp = Employee(emp_no="T003", name="测试员工3", team="一班1组", dept="客服中心", role="组员", status="在职")
        db.add(emp)
        db.flush()

        shift_info = {"name": "晚二", "time_segments": [{"start": "12:30", "end": "17:00"}, {"start": "18:00", "end": "22:00"}], "work_hours": 8.5, "is_night": True}
        shift = get_or_create_shift(db, shift_info)

        s = Schedule(emp_id=emp.id, schedule_date=date(2026, 5, 13), shift_type_id=shift.id, shift_name=shift_info["name"], time_segments=shift_info["time_segments"], work_hours=shift_info["work_hours"], is_night=shift_info["is_night"], schedule_type="正常")
        db.add(s)
        db.commit()

        info = get_schedule_shift_info(s, db)
        assert info is not None
        assert info["shift_name"] == "晚二"
        assert info["time_segments"] == [{"start": "12:30", "end": "17:00"}, {"start": "18:00", "end": "22:00"}]
        assert info["work_hours"] == 8.5

    def test_fallback_to_shift_type(self, db):
        clear_tables(db)
        emp = Employee(emp_no="T004", name="测试员工4", team="一班1组", dept="客服中心", role="组员", status="在职")
        shift = ShiftType(shift_name="行政班", time_segments=[{"start": "09:00", "end": "18:00"}], work_hours=8.0, is_night=False)
        db.add_all([emp, shift])
        db.flush()

        s = Schedule(emp_id=emp.id, schedule_date=date(2026, 5, 1), shift_type_id=shift.id, shift_name=None, time_segments=None, work_hours=None, schedule_type="正常")
        db.add(s)
        db.commit()

        info = get_schedule_shift_info(s, db)
        assert info is not None
        assert info["shift_name"] == "行政班"
        assert info["work_hours"] == 8.0


class TestParseShiftFromHeader:

    def test_parse_header(self):
        result = parse_shift_from_header("中班（8.0）8:30-13:00  15:30-19:00")
        assert result is not None
        assert result["name"] == "中班"
        assert result["work_hours"] == 8.0
        assert len(result["time_segments"]) == 2


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