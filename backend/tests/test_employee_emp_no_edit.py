import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.employee import Employee
from app.models.checkin import Checkin
from app.main import app
from app.core.security import get_current_user
from sqlalchemy import text
from datetime import datetime


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
    for table in ["checkins", "monthly_reports", "daily_reports", "schedules", "employees"]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


class TestEmployeeEmpNoEdit:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            self.emp_normal = Employee(emp_no="KF77100020", name="正常员工", team="热线一组", dept="客服中心")
            self.emp_temp = Employee(emp_no="TEMP_陈坤兰", name="陈坤兰", team="热线二组", dept="客服中心")
            db.add_all([self.emp_normal, self.emp_temp])
            db.commit()
            self.normal_id = self.emp_normal.id
            self.temp_id = self.emp_temp.id
        finally:
            db.close()

    def test_update_emp_no_success(self):
        resp = client.put(f"/api/employees/{self.temp_id}", json={"emp_no": "KF77100021"})
        assert resp.status_code == 200
        assert resp.json()["id"] == self.temp_id

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == self.temp_id).first()
            assert emp.emp_no == "KF77100021"
        finally:
            db.close()

    def test_update_emp_no_duplicate(self):
        resp = client.put(f"/api/employees/{self.temp_id}", json={"emp_no": "KF77100020"})
        assert resp.status_code == 400
        assert "工号已存在" in resp.json()["detail"]

    def test_update_emp_no_to_itself_should_work(self):
        resp = client.put(f"/api/employees/{self.temp_id}", json={"emp_no": "TEMP_陈坤兰"})
        assert resp.status_code == 200

    def test_update_emp_no_syncs_checkins(self):
        db = SessionLocal()
        try:
            checkin = Checkin(
                emp_no="TEMP_陈坤兰", name="陈坤兰",
                checkin_time=datetime(2026, 7, 1, 8, 0, 0),
                import_batch="test"
            )
            db.add(checkin)
            db.commit()
        finally:
            db.close()

        resp = client.put(f"/api/employees/{self.temp_id}", json={"emp_no": "KF77100021"})
        assert resp.status_code == 200

        db = SessionLocal()
        try:
            updated = db.query(Checkin).filter(Checkin.emp_no == "KF77100021").first()
            assert updated is not None
            assert updated.name == "陈坤兰"

            old = db.query(Checkin).filter(Checkin.emp_no == "TEMP_陈坤兰").first()
            assert old is None
        finally:
            db.close()

    def test_update_normal_emp_no_still_rejected_by_frontend(self):
        resp = client.put(f"/api/employees/{self.normal_id}", json={"emp_no": "KF77100022"})
        assert resp.status_code == 200

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == self.normal_id).first()
            assert emp.emp_no == "KF77100022"
        finally:
            db.close()

    def test_update_only_name_other_fields_unchanged(self):
        resp = client.put(f"/api/employees/{self.temp_id}", json={"name": "陈坤兰(改)"})
        assert resp.status_code == 200

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.id == self.temp_id).first()
            assert emp.name == "陈坤兰(改)"
            assert emp.emp_no == "TEMP_陈坤兰"
        finally:
            db.close()

    def test_update_emp_no_not_found(self):
        resp = client.put("/api/employees/99999", json={"emp_no": "NEW001"})
        assert resp.status_code == 404
