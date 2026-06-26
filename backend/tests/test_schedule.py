import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.schedule import Schedule
from app.models.employee import Employee
from app.models.shift_type import ShiftType
from app.main import app
from app.core.security import get_current_user
from sqlalchemy import text
from datetime import date


_admin_user = {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "is_system": True,
    "permissions": "{}",
}


def override_get_current_user():
    return _admin_user


app.dependency_overrides[get_current_user] = override_get_current_user
client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    init_db()


def teardown_module():
    app.dependency_overrides.clear()


def _clean_tables(db):
    for table in ["schedules", "shift_types", "employees"]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


class TestScheduleDeleteByDate:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp1 = Employee(emp_no="E001", name="张三", team="测试班组")
            emp2 = Employee(emp_no="E002", name="李四", team="测试班组")
            emp3 = Employee(emp_no="E003", name="王五", team="测试班组")
            db.add_all([emp1, emp2, emp3])
            db.flush()

            shift = ShiftType(shift_name="早班", time_segments=[{"start": "08:00", "end": "17:00"}], work_hours=8.0)
            db.add(shift)
            db.flush()

            schedules = [
                Schedule(emp_id=emp1.id, schedule_date=date(2026, 5, 28), shift_type_id=shift.id, schedule_type="正常"),
                Schedule(emp_id=emp2.id, schedule_date=date(2026, 5, 28), shift_type_id=shift.id, schedule_type="正常"),
                Schedule(emp_id=emp3.id, schedule_date=date(2026, 5, 29), shift_type_id=shift.id, schedule_type="正常"),
            ]
            db.add_all(schedules)
            db.commit()
        finally:
            db.close()

    def test_delete_by_date(self):
        resp = client.delete("/api/schedules/by-date", params={"date": "2026-05-28"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert "已删除" in data["message"]

        db = SessionLocal()
        try:
            remaining = db.query(Schedule).all()
            assert len(remaining) == 1
            assert remaining[0].schedule_date == date(2026, 5, 29)
        finally:
            db.close()

    def test_delete_by_date_no_records(self):
        resp = client.delete("/api/schedules/by-date", params={"date": "2026-06-01"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert "没有排班记录" in data["message"]

    def test_delete_by_date_invalid_format(self):
        resp = client.delete("/api/schedules/by-date", params={"date": "not-a-date"})
        assert resp.status_code == 400
        assert "日期格式无效" in resp.json()["detail"]

    def test_delete_by_date_missing_param(self):
        resp = client.delete("/api/schedules/by-date")
        assert resp.status_code == 422