import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

import json
from datetime import datetime, date
from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.user import User
from app.models.employee import Employee
from app.models.checkin import Checkin
from app.models.shift_type import ShiftType
from app.models.daily_report import DailyReport
from app.main import app
from app.core.security import get_current_user, create_access_token


def override_get_current_user():
    return {
        "id": 1,
        "username": "admin",
        "role": "admin",
        "is_system": True,
        "permissions": "{}",
    }


app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()


def teardown_module():
    app.dependency_overrides.clear()


def _create_test_data(db):
    emp = Employee(
        emp_no="E001",
        name="测试员工",
        team="测试班组",
        dept="测试部门>>子部门",
        role="组员"
    )
    db.add(emp)
    db.flush()

    shift_type = ShiftType(
        shift_name="早班",
        time_segments=[{"start": "08:00", "end": "12:00"}, {"start": "13:00", "end": "17:00"}],
        work_hours=8.0,
        color="#409EFF",
        is_night=False
    )
    db.add(shift_type)
    db.flush()

    checkins_data = [
        Checkin(emp_no="E001", name="测试员工", checkin_time=datetime(2026, 5, 6, 8, 30, 0),
                checkout_time=datetime(2026, 5, 6, 18, 0, 0), dept="测试部门>>子部门", import_batch="test1"),
        Checkin(emp_no="E001", name="测试员工", checkin_time=datetime(2026, 5, 7, 9, 0, 0),
                checkout_time=datetime(2026, 5, 7, 17, 30, 0), dept="测试部门>>子部门", import_batch="test1"),
        Checkin(emp_no="E001", name="测试员工", checkin_time=datetime(2026, 5, 8, 12, 0, 0),
                checkout_time=datetime(2026, 5, 8, 21, 0, 0), dept="测试部门>>子部门", import_batch="test1"),
        Checkin(emp_no="E001", name="测试员工", checkin_time=datetime(2026, 5, 9, 14, 0, 0),
                checkout_time=datetime(2026, 5, 9, 22, 0, 0), dept="测试部门>>子部门", import_batch="test1"),
    ]
    for c in checkins_data:
        db.add(c)
    db.flush()

    daily_report = DailyReport(
        emp_id=emp.id,
        schedule_date=date(2026, 5, 6),
        shift_type_id=shift_type.id,
        schedule_type="正常",
        scheduled_start="08:00",
        scheduled_end="17:00",
        scheduled_hours=8.0,
        actual_hours=9.5,
        status="正常",
        late_minutes=0,
        early_minutes=0
    )
    db.add(daily_report)

    daily_report2 = DailyReport(
        emp_id=emp.id,
        schedule_date=date(2026, 5, 7),
        schedule_type="正常",
        scheduled_start="09:00",
        scheduled_end="18:00",
        scheduled_hours=8.0,
        actual_hours=8.5,
        status="迟到",
        late_minutes=15,
        early_minutes=0
    )
    db.add(daily_report2)
    db.commit()

    return emp, shift_type


def test_personal_report_success():
    db = SessionLocal()
    try:
        _create_test_data(db)
    finally:
        db.close()

    response = client.get("/api/checkins/personal-report", params={
        "emp_no": "E001",
        "start_date": "2026-05-01",
        "end_date": "2026-05-31"
    })

    assert response.status_code == 200
    data = response.json()

    assert data["emp_info"]["emp_no"] == "E001"
    assert data["emp_info"]["name"] == "测试员工"
    assert data["emp_info"]["team"] == "测试班组"

    summary = data["summary"]
    assert summary["attend_days"] == 4
    assert summary["total_hours"] > 0
    assert summary["total_scheduled_hours"] > 0
    assert summary["long_hour_days"] >= 0
    assert summary["morning_shift_days"] + summary["mid_shift_days"] + summary["night_shift_days"] == summary["attend_days"]

    daily_stats = data["daily_stats"]
    assert len(daily_stats) == 4
    for stat in daily_stats:
        assert "date" in stat
        assert "checkin_time" in stat
        assert "checkout_time" in stat
        assert "duration" in stat
        assert "shift_name" in stat
        assert "is_long_hour" in stat
        assert "scheduled_hours" in stat
        assert "status" in stat
        assert "late_minutes" in stat
        assert "early_minutes" in stat
        assert "actual_hours" in stat

    day1 = daily_stats[0]
    assert day1["date"] == "2026-05-06"
    assert day1["scheduled_hours"] == 8.0
    assert day1["status"] == "正常"
    assert day1["late_minutes"] == 0
    assert day1["early_minutes"] == 0

    day2 = daily_stats[1]
    assert day2["date"] == "2026-05-07"
    assert day2["status"] == "迟到"
    assert day2["late_minutes"] == 15
    assert day2["early_minutes"] == 0


def test_personal_report_shift_inference():
    db = SessionLocal()
    try:
        emp = Employee(
            emp_no="E002",
            name="推断班次员工",
            team="测试班组",
            dept="测试部门",
            role="组员"
        )
        db.add(emp)
        db.flush()

        checkins_data = [
            Checkin(emp_no="E002", name="推断班次员工", checkin_time=datetime(2026, 5, 10, 8, 0, 0),
                    checkout_time=datetime(2026, 5, 10, 17, 0, 0), dept="测试部门", import_batch="test2"),
            Checkin(emp_no="E002", name="推断班次员工", checkin_time=datetime(2026, 5, 11, 12, 0, 0),
                    checkout_time=datetime(2026, 5, 11, 21, 0, 0), dept="测试部门", import_batch="test2"),
            Checkin(emp_no="E002", name="推断班次员工", checkin_time=datetime(2026, 5, 12, 16, 0, 0),
                    checkout_time=datetime(2026, 5, 13, 0, 0, 0), dept="测试部门", import_batch="test2"),
        ]
        for c in checkins_data:
            db.add(c)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/checkins/personal-report", params={
        "emp_no": "E002",
        "start_date": "2026-05-01",
        "end_date": "2026-05-31"
    })

    assert response.status_code == 200
    data = response.json()
    daily_stats = data["daily_stats"]
    assert len(daily_stats) == 3

    shift_names = [d["shift_name"] for d in daily_stats]
    assert "早班" in shift_names
    assert "中班" in shift_names
    assert "晚班" in shift_names


def test_personal_report_long_hour():
    db = SessionLocal()
    try:
        emp = Employee(
            emp_no="E003",
            name="超长工时员工",
            team="测试班组",
            dept="测试部门",
            role="组员"
        )
        db.add(emp)
        db.flush()

        checkins_data = [
            Checkin(emp_no="E003", name="超长工时员工", checkin_time=datetime(2026, 5, 15, 8, 0, 0),
                    checkout_time=datetime(2026, 5, 15, 20, 0, 0), dept="测试部门", import_batch="test3"),
            Checkin(emp_no="E003", name="超长工时员工", checkin_time=datetime(2026, 5, 16, 9, 0, 0),
                    checkout_time=datetime(2026, 5, 16, 17, 0, 0), dept="测试部门", import_batch="test3"),
        ]
        for c in checkins_data:
            db.add(c)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/checkins/personal-report", params={
        "emp_no": "E003",
        "start_date": "2026-05-01",
        "end_date": "2026-05-31"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["long_hour_days"] == 1
    assert data["summary"]["attend_days"] == 2


def test_personal_report_not_found():
    response = client.get("/api/checkins/personal-report", params={
        "emp_no": "NOT_EXIST",
        "start_date": "2026-05-01",
        "end_date": "2026-05-31"
    })

    assert response.status_code == 404


def test_personal_report_no_data():
    db = SessionLocal()
    try:
        emp = Employee(
            emp_no="E004",
            name="无签到员工",
            team="测试班组",
            dept="测试部门",
            role="组员"
        )
        db.add(emp)
        db.commit()
    finally:
        db.close()

    response = client.get("/api/checkins/personal-report", params={
        "emp_no": "E004",
        "start_date": "2026-05-01",
        "end_date": "2026-05-31"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["attend_days"] == 0
    assert data["summary"]["total_hours"] == 0
    assert len(data["daily_stats"]) == 0


def test_long_hour_threshold_config_affects_result():
    db = SessionLocal()
    try:
        from app.models.attendance_config import AttendanceConfig
        config = db.query(AttendanceConfig).filter(AttendanceConfig.key == "long_hour_threshold").first()
        if not config:
            config = AttendanceConfig(key="long_hour_threshold", value="13.0")
            db.add(config)
        else:
            config.value = "13.0"
        db.commit()
    finally:
        db.close()

    response = client.get("/api/checkins/personal-report", params={
        "emp_no": "E003",
        "start_date": "2026-05-01",
        "end_date": "2026-05-31"
    })

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["long_hour_days"] == 0

    db = SessionLocal()
    try:
        config = db.query(AttendanceConfig).filter(AttendanceConfig.key == "long_hour_threshold").first()
        if config:
            config.value = "9.5"
            db.commit()
    finally:
        db.close()


def test_attendance_config_get_includes_long_hour():
    response = client.get("/api/attendance-config")
    assert response.status_code == 200
    data = response.json()
    assert "long_hour_threshold" in data
    assert isinstance(data["long_hour_threshold"], float)


def test_attendance_config_update_long_hour():
    response = client.put("/api/attendance-config", json={"long_hour_threshold": 8.0})
    assert response.status_code == 200
    data = response.json()
    assert data["long_hour_threshold"] == 8.0

    response = client.put("/api/attendance-config", json={"long_hour_threshold": 9.5})
    assert response.status_code == 200
