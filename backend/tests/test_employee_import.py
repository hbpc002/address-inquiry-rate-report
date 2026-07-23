import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.employee import Employee
from app.main import app
from app.core.security import get_current_user
from sqlalchemy import text
from datetime import date
import io
import openpyxl


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
    for table in ["employees"]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


def _make_xlsx(rows: list[list]) -> io.BytesIO:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


class TestEmployeeImport:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
        finally:
            db.close()

    def test_import_with_hire_date(self):
        rows = [
            ["工号", "姓名", "班组", "部门", "岗位", "状态", "入职日期"],
            ["E001", "张三", "热线一组", "客服中心", "组员", "在职", "2026-01-15"],
            ["E002", "李四", "热线二组", "客服中心", "组员", "在职", "2026-04-01"],
            ["E003", "王五", "热线一组", "客服中心", "师傅", "在职", "2026-07-01"],
        ]
        xlsx = _make_xlsx(rows)
        resp = client.post("/api/employees/import", files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 3
        assert data["updated"] == 0
        assert data["skipped"] == 0

        db = SessionLocal()
        try:
            emp1 = db.query(Employee).filter(Employee.emp_no == "E001").first()
            assert emp1 is not None
            assert emp1.hire_date == date(2026, 1, 15)

            emp2 = db.query(Employee).filter(Employee.emp_no == "E002").first()
            assert emp2 is not None
            assert emp2.hire_date == date(2026, 4, 1)

            emp3 = db.query(Employee).filter(Employee.emp_no == "E003").first()
            assert emp3 is not None
            assert emp3.hire_date == date(2026, 7, 1)
        finally:
            db.close()

    def test_import_without_hire_date(self):
        rows = [
            ["工号", "姓名", "班组"],
            ["E001", "张三", "热线一组"],
            ["E002", "李四", "热线二组"],
        ]
        xlsx = _make_xlsx(rows)
        resp = client.post("/api/employees/import", files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 2

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.emp_no == "E001").first()
            assert emp is not None
            assert emp.hire_date is None
        finally:
            db.close()

    def test_import_updates_hire_date(self):
        rows = [
            ["工号", "姓名", "班组", "入职日期"],
            ["E001", "张三", "热线一组", "2026-01-15"],
        ]
        xlsx = _make_xlsx(rows)
        resp = client.post("/api/employees/import", files={"file": ("test.xlsx", xlsx, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert resp.status_code == 200
        assert resp.json()["created"] == 1

        rows2 = [
            ["工号", "姓名", "班组", "入职日期"],
            ["E001", "张三", "热线一组", "2026-03-20"],
        ]
        xlsx2 = _make_xlsx(rows2)
        resp = client.post("/api/employees/import", files={"file": ("test.xlsx", xlsx2, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
        assert resp.status_code == 200
        assert resp.json()["updated"] == 1

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.emp_no == "E001").first()
            assert emp.hire_date == date(2026, 3, 20)
        finally:
            db.close()
