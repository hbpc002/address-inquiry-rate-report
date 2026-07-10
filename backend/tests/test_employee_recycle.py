import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.daily_report import DailyReport
from app.models.monthly_report import MonthlyReport
from app.models.shift_type import ShiftType
from app.main import app
from app.core.security import get_current_user
from sqlalchemy import text
from datetime import date, datetime


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
    for table in ["monthly_reports", "daily_reports", "schedules", "employees"]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


class TestEmployeeRecycle:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp1 = Employee(emp_no="E001", name="张三", team="热线一组", dept="客服中心")
            emp2 = Employee(emp_no="E002", name="李四", team="热线二组", dept="客服中心")
            emp3 = Employee(emp_no="E003", name="王五", team="热线三组", dept="客服中心")
            db.add_all([emp1, emp2, emp3])
            db.commit()
            self.emp1_id = emp1.id
            self.emp2_id = emp2.id
            self.emp3_id = emp3.id
        finally:
            db.close()

    def test_soft_delete_sets_deleted_at(self):
        resp = client.delete(f"/api/employees/{self.emp1_id}")
        assert resp.status_code == 200

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == self.emp1_id).first()
            assert emp.status == "离职"
            assert emp.deleted_at is not None
        finally:
            db.close()

    def test_restore_sets_status_back_to_active(self):
        client.delete(f"/api/employees/{self.emp1_id}")

        resp = client.put(f"/api/employees/{self.emp1_id}/restore")
        assert resp.status_code == 200
        assert resp.json()["message"] == "恢复成功"

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == self.emp1_id).first()
            assert emp.status == "在职"
            assert emp.deleted_at is None
        finally:
            db.close()

    def test_restore_active_employee_returns_400(self):
        resp = client.put(f"/api/employees/{self.emp1_id}/restore")
        assert resp.status_code == 400
        assert "无需恢复" in resp.json()["detail"]

    def test_restore_nonexistent_employee_returns_404(self):
        resp = client.put("/api/employees/99999/restore")
        assert resp.status_code == 404

    def test_hard_delete_removes_employee_and_related_data(self):
        db = SessionLocal()
        try:
            client.delete(f"/api/employees/{self.emp1_id}")

            shift = ShiftType(shift_name="早班", time_segments=[{"start": "08:00", "end": "17:00"}], work_hours=8.0)
            db.add(shift)
            db.flush()

            schedule = Schedule(emp_id=self.emp1_id, schedule_date=date(2026, 7, 1), shift_type_id=shift.id, schedule_type="正常")
            db.add(schedule)
            db.flush()

            daily = DailyReport(emp_id=self.emp1_id, schedule_date=date(2026, 7, 1), status="正常")
            db.add(daily)
            db.flush()

            monthly = MonthlyReport(emp_id=self.emp1_id, year_month="2026-07")
            db.add(monthly)
            db.commit()
        finally:
            db.close()

        resp = client.delete(f"/api/employees/{self.emp1_id}/hard-delete")
        assert resp.status_code == 200
        assert resp.json()["message"] == "已彻底删除"

        db = SessionLocal()
        try:
            assert db.query(Employee).filter(Employee.id == self.emp1_id).first() is None
            assert db.query(Schedule).filter(Schedule.emp_id == self.emp1_id).first() is None
            assert db.query(DailyReport).filter(DailyReport.emp_id == self.emp1_id).first() is None
            assert db.query(MonthlyReport).filter(MonthlyReport.emp_id == self.emp1_id).first() is None
        finally:
            db.close()

    def test_hard_delete_nonexistent_returns_404(self):
        resp = client.delete("/api/employees/99999/hard-delete")
        assert resp.status_code == 404

    def test_batch_restore(self):
        for eid in [self.emp1_id, self.emp2_id]:
            client.delete(f"/api/employees/{eid}")

        resp = client.post("/api/employees/batch-restore", json=[self.emp1_id, self.emp2_id])
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

        db = SessionLocal()
        try:
            emp1 = db.query(Employee).filter(Employee.id == self.emp1_id).first()
            emp2 = db.query(Employee).filter(Employee.id == self.emp2_id).first()
            assert emp1.status == "在职"
            assert emp2.status == "在职"
            assert emp1.deleted_at is None
            assert emp2.deleted_at is None
        finally:
            db.close()

    def test_batch_hard_delete(self):
        db = SessionLocal()
        try:
            shift = ShiftType(shift_name="早班", time_segments=[{"start": "08:00", "end": "17:00"}], work_hours=8.0)
            db.add(shift)
            db.flush()

            for eid in [self.emp1_id, self.emp2_id]:
                db.add(Schedule(emp_id=eid, schedule_date=date(2026, 7, 1), shift_type_id=shift.id, schedule_type="正常"))
            db.commit()
        finally:
            db.close()

        for eid in [self.emp1_id, self.emp2_id]:
            client.delete(f"/api/employees/{eid}")

        resp = client.post("/api/employees/batch-hard-delete", json=[self.emp1_id, self.emp2_id])
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

        db = SessionLocal()
        try:
            assert db.query(Employee).filter(Employee.id == self.emp1_id).first() is None
            assert db.query(Employee).filter(Employee.id == self.emp2_id).first() is None
            assert db.query(Schedule).filter(Schedule.emp_id.in_([self.emp1_id, self.emp2_id])).count() == 0
        finally:
            db.close()

    def test_employee_list_filters_by_status(self):
        client.delete(f"/api/employees/{self.emp1_id}")

        resp_active = client.get("/api/employees", params={"status": "在职"})
        assert resp_active.status_code == 200
        active_ids = [e["id"] for e in resp_active.json()["items"]]
        assert self.emp1_id not in active_ids
        assert self.emp2_id in active_ids
        assert self.emp3_id in active_ids

        resp_deleted = client.get("/api/employees", params={"status": "离职"})
        assert resp_deleted.status_code == 200
        deleted_ids = [e["id"] for e in resp_deleted.json()["items"]]
        assert self.emp1_id in deleted_ids
        assert self.emp2_id not in deleted_ids
