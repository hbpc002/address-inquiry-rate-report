import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from fastapi.testclient import TestClient
from app.models.database import Base, engine, SessionLocal, init_db
from app.models.checkin import Checkin
from app.models.employee import Employee
from app.main import app
from app.core.security import get_current_user
from sqlalchemy import text
from datetime import datetime, date
import io
import csv


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
    for table in ["checkins", "employees"]:
        db.execute(text(f"DELETE FROM {table}"))
    db.commit()


def _make_csv(content: str) -> io.BytesIO:
    return io.BytesIO(content.encode("utf-8"))


class TestCheckinImport:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            emp = Employee(emp_no="E001", name="张三", team="测试班组", dept="广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表")
            db.add(emp)
            db.commit()
        finally:
            db.close()

    def _upload_csv(self, content: str):
        data = {"file": ("test.csv", _make_csv(content), "text/csv")}
        return client.post("/api/checkins/import", files=data)

    def test_import_normal_csv(self):
        csv_content = "工号,姓名,签到时间,签退时间,设备号,归属部门\nE001,张三,2026-05-30 08:00:00,2026-05-30 17:00:00,D001,广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"
        resp = self._upload_csv(csv_content)
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert len(data["batch"]) == 8

    def test_import_skips_non_target_dept(self):
        csv_content = "工号,姓名,签到时间,签退时间,设备号,归属部门\nE001,张三,2026-05-30 08:00:00,2026-05-30 17:00:00,D001,其他部门"
        resp = self._upload_csv(csv_content)
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_import_empty_file(self):
        data = {"file": ("empty.csv", _make_csv(""), "text/csv")}
        resp = client.post("/api/checkins/import", files=data)
        assert resp.status_code == 400

    def test_import_missing_required_fields(self):
        csv_content = "名称,备注\nfoo,bar"
        resp = self._upload_csv(csv_content)
        assert resp.status_code == 400

    def test_import_replaces_old_records_on_same_date(self):
        # 第一次导入
        csv_content = (
            "工号,姓名,签到时间,签退时间,设备号,归属部门\n"
            "E001,张三,2026-05-30 08:00:00,2026-05-30 17:00:00,D001,"
            "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"
        )
        resp1 = self._upload_csv(csv_content)
        assert resp1.status_code == 200
        assert resp1.json()["count"] == 1

        # 第二次导入同一日期，不同数据
        csv_content2 = (
            "工号,姓名,签到时间,签退时间,设备号,归属部门\n"
            "E001,张三,2026-05-30 09:00:00,2026-05-30 18:00:00,D002,"
            "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"
        )
        resp2 = self._upload_csv(csv_content2)
        assert resp2.status_code == 200
        assert resp2.json()["count"] == 1

        # 验证旧记录被替换，只有 1 条记录
        db = SessionLocal()
        try:
            records = db.query(Checkin).all()
            assert len(records) == 1
            assert records[0].checkin_time.hour == 9
            assert records[0].device_no == "D002"
        finally:
            db.close()

    def test_import_updates_employee_dept(self):
        csv_content = (
            "工号,姓名,签到时间,签退时间,设备号,归属部门\n"
            "E001,张三,2026-05-30 08:00:00,2026-05-30 17:00:00,D001,"
            "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"
        )
        resp = self._upload_csv(csv_content)
        assert resp.status_code == 200

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.emp_no == "E001").first()
            assert emp is not None
            assert emp.dept == "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"
        finally:
            db.close()

    def test_import_dedup_employee_dept_multiple_rows(self):
        # 同一员工多行导入，dept 只更新一次（验证不会报错）
        csv_content = (
            "工号,姓名,签到时间,签退时间,设备号,归属部门\n"
            "E001,张三,2026-05-30 08:00:00,2026-05-30 12:00:00,D001,"
            "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表\n"
            "E001,张三,2026-05-30 13:00:00,2026-05-30 17:00:00,D001,"
            "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"
        )
        resp = self._upload_csv(csv_content)
        assert resp.status_code == 200
        assert resp.json()["count"] == 2

        db = SessionLocal()
        try:
            emp = db.query(Employee).filter(Employee.emp_no == "E001").first()
            assert emp.dept == "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"
        finally:
            db.close()


class TestCheckinDeleteByDate:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            for i, day in enumerate([28, 29, 30]):
                ck = Checkin(
                    emp_no=f"E00{i+1}",
                    name=f"员工{i+1}",
                    checkin_time=datetime(2026, 5, day, 8, 0, 0),
                    checkout_time=datetime(2026, 5, day, 17, 0, 0),
                    dept="广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表",
                    import_batch=f"batch-{day}",
                )
                db.add(ck)
            db.commit()
        finally:
            db.close()

    def test_delete_by_date(self):
        resp = client.delete("/api/checkins/by-date", params={"date": "2026-05-29"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1

        db = SessionLocal()
        try:
            remaining = db.query(Checkin).all()
            assert len(remaining) == 2
        finally:
            db.close()

    def test_delete_by_date_no_records(self):
        resp = client.delete("/api/checkins/by-date", params={"date": "2026-06-01"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_delete_by_date_invalid_format(self):
        resp = client.delete("/api/checkins/by-date", params={"date": "not-a-date"})
        assert resp.status_code == 400

    def test_delete_by_date_missing_param(self):
        resp = client.delete("/api/checkins/by-date")
        assert resp.status_code == 422


class TestCheckinDeleteByBatch:

    def setup_method(self):
        db = SessionLocal()
        try:
            _clean_tables(db)
            for i in range(3):
                ck = Checkin(
                    emp_no=f"E00{i+1}",
                    name=f"员工{i+1}",
                    checkin_time=datetime(2026, 5, 30, 8, 0, 0),
                    checkout_time=datetime(2026, 5, 30, 17, 0, 0),
                    dept="广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表",
                    import_batch="batch-to-delete",
                )
                db.add(ck)
            ck2 = Checkin(
                emp_no="E004",
                name="员工4",
                checkin_time=datetime(2026, 5, 30, 8, 0, 0),
                checkout_time=datetime(2026, 5, 30, 17, 0, 0),
                dept="广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表",
                import_batch="other-batch",
            )
            db.add(ck2)
            db.commit()
        finally:
            db.close()

    def test_delete_by_batch(self):
        resp = client.delete("/api/checkins/import/batch-to-delete")
        assert resp.status_code == 200
        assert resp.json()["count"] == 3

        db = SessionLocal()
        try:
            remaining = db.query(Checkin).all()
            assert len(remaining) == 1
            assert remaining[0].import_batch == "other-batch"
        finally:
            db.close()
