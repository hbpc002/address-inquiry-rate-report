import io
import json
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:admin123%40kf@localhost:5432/schedule_test")

from fastapi.testclient import TestClient
from sqlalchemy import text

import app.models  # noqa: F401
from app.core.security import get_current_user, get_password_hash
from app.main import app
from app.models.database import Base, SessionLocal, engine, init_db
from app.models.employee import Employee
from app.models.marketing_detail import MarketingDetail
from app.models.marketing_opening import MarketingOpeningRecord
from app.models.operation_log import OperationLog
from app.models.user import User

ADMIN = {"id": 1, "username": "opening_admin", "role": "admin", "is_system": True, "permissions": "{}"}


def _override_user():
    return ADMIN


client = TestClient(app)
_previous_override = None

OPENING_HEADERS = [
    "接触记录号",
    "录音时间",
    "班组",
    "员工工号",
    "员工姓名",
    "坐席主动开口营销叠加包",
    "坐席已开口营销叠加包",
    "坐席主动开口营销宽带",
    "坐席已开口营销宽带",
    "坐席主动开口营销移网新装",
    "坐席已开口营销移网新装",
    "坐席主动开口营销终端",
    "坐席已开口营销终端",
    "坐席主动开口营销套餐",
    "坐席已开口营销套餐",
    "五大产品已开口",
]


def setup_module():
    global _previous_override
    Base.metadata.drop_all(bind=engine)
    init_db()
    _previous_override = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = _override_user
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.id == 1).first():
            db.add(
                User(
                    id=1,
                    username="opening_admin",
                    password_hash=get_password_hash("x"),
                    role="admin",
                    is_active=True,
                )
            )
            db.commit()
    finally:
        db.close()


def teardown_module():
    global _previous_override
    if _previous_override is not None:
        app.dependency_overrides[get_current_user] = _previous_override
    else:
        app.dependency_overrides.pop(get_current_user, None)
    _previous_override = None


def _clean():
    db = SessionLocal()
    try:
        db.query(MarketingOpeningRecord).delete()
        db.query(MarketingDetail).delete()
        db.query(Employee).delete()
        db.query(OperationLog).delete()
        db.commit()
    finally:
        db.close()


def _seed_employees():
    db = SessionLocal()
    try:
        db.add_all(
            [
                Employee(emp_no="KF001", name="张三", team="热线1组", dept="客服部", status="在职"),
                Employee(emp_no="KF002", name="李四", team="区域2组", dept="客服部", status="在职"),
                Employee(emp_no="KF003", name="王五", team="热线1组", dept="客服部", status="在职"),
            ]
        )
        db.commit()
    finally:
        db.close()


def _row(
    contact="C1",
    emp="KF001",
    name="张三",
    time="2026-11-02 09:00:00",
    team="10010热线客服代表",
    aa=False,
    **flags,
):
    data = {
        "接触记录号": contact,
        "录音时间": time,
        "班组": team,
        "员工工号": emp,
        "员工姓名": name,
        "五大产品已开口": "是" if aa else "否",
    }
    for key in OPENING_HEADERS[5:-1]:
        data[key] = "否"
    mapping = {
        "active_overlay": "坐席主动开口营销叠加包",
        "opened_overlay": "坐席已开口营销叠加包",
        "active_broadband": "坐席主动开口营销宽带",
        "opened_broadband": "坐席已开口营销宽带",
        "active_mobile_new": "坐席主动开口营销移网新装",
        "opened_mobile_new": "坐席已开口营销移网新装",
        "active_terminal": "坐席主动开口营销终端",
        "opened_terminal": "坐席已开口营销终端",
        "active_package": "坐席主动开口营销套餐",
        "opened_package": "坐席已开口营销套餐",
    }
    for key, value in flags.items():
        if key in mapping:
            data[mapping[key]] = "是" if value else "否"
    return data


def _make_file(rows, csv=False):
    df = pd.DataFrame(rows, columns=OPENING_HEADERS)
    buf = io.BytesIO()
    if csv:
        buf.write(df.to_csv(index=False).encode("utf-8-sig"))
    else:
        df.to_excel(buf, index=False)
    buf.seek(0)
    return buf


def _upload(rows, csv=False):
    data = {
        "file": (
            "openings.csv" if csv else "openings.xlsx",
            _make_file(rows, csv=csv),
            "text/csv" if csv else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    }
    return client.post("/api/marketing-openings/import", files=data)


def _employee(report, emp_no):
    return next(item for item in report["employees"] if item["kf_id"] == emp_no)


class TestMarketingOpening:

    def setup_method(self):
        _clean()
        _seed_employees()

    def test_import_and_multi_dimension_report(self):
        rows = [
            _row("C1", "KF001", aa=True, active_overlay=True, opened_overlay=True),
            _row("C2", "KF001", aa=False),
            _row("C3", "KF002", aa=True, active_broadband=True, opened_broadband=True),
            _row("C4", "KF002", aa=False, active_package=True, opened_package=True),
        ]
        resp = _upload(rows)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["count"] == 4
        assert body["dates"] == ["2026-11-02"]
        assert body["source"] == "大模型质检台"

        report = client.get(
            "/api/marketing-openings/report", params={"year_month": "2026-11"}
        ).json()
        assert report["stats"]["contact_count"] == 4
        assert report["stats"]["opened_count"] == 2
        assert report["stats"]["opening_rate"] == 0.5
        assert len(report["columns"]) == 10

        emp1 = _employee(report, "KF001")
        assert emp1["contact_count"] == 2
        assert emp1["opened_count"] == 1
        assert emp1["opening_rate"] == 0.5
        assert emp1["active_overlay"] == 1
        assert emp1["opened_overlay"] == 1

        emp2 = _employee(report, "KF002")
        assert emp2["contact_count"] == 2
        assert emp2["opened_count"] == 1
        assert emp2["opened_broadband"] == 1
        assert emp2["opened_package"] == 1

        team = next(item for item in report["teams"] if item["team"] == "热线1组")
        assert team["contact_count"] == 2
        assert team["opened_count"] == 1
        assert team["people"] == 1

        klass = next(item for item in report["classes"] if item["class_name"] == "热线")
        assert klass["contact_count"] == 2
        assert klass["opening_rate"] == 0.5

        day = report["days"][0]
        assert day["date"] == "2026-11-02"
        assert day["contact_count"] == 4
        assert day["opened_count"] == 2

        export = client.get(
            "/api/marketing-openings/report/export",
            params={"year_month": "2026-11", "dimension": "employee"},
        )
        assert export.status_code == 200
        text = export.content.decode("utf-8-sig")
        assert "接触量" in text
        assert "叠加包主动开口量" in text
        assert "50.00%" in text

    def test_same_date_overwrite_and_contact_deduplication(self):
        first = _upload(
            [
                _row("C1", aa=False),
                _row("C1", aa=True, active_overlay=True, opened_overlay=True),
            ]
        )
        assert first.status_code == 200, first.text
        assert first.json()["count"] == 1
        assert first.json()["skipped"] == 1

        report = client.get(
            "/api/marketing-openings/report", params={"year_month": "2026-11"}
        ).json()
        assert report["stats"]["contact_count"] == 1
        assert report["stats"]["opened_count"] == 1
        assert report["employees"][0]["opened_overlay"] == 1

        second = _upload([_row("C2", aa=True)])
        assert second.status_code == 200, second.text
        details = client.get("/api/marketing-openings").json()
        assert details["total"] == 1
        assert details["items"][0]["contact_id"] == "C2"

    def test_csv_import_and_raw_export(self):
        resp = _upload([_row("CSV1", aa=True, active_terminal=True, opened_terminal=True)], csv=True)
        assert resp.status_code == 200, resp.text
        assert resp.json()["count"] == 1

        listing = client.get("/api/marketing-openings").json()
        assert listing["total"] == 1
        item = listing["items"][0]
        assert item["contact_id"] == "CSV1"
        assert item["active_terminal"] == "是"
        assert item["five_products_opened"] == "是"

        export = client.get("/api/marketing-openings/export")
        assert export.status_code == 200
        text = export.content.decode("utf-8-sig")
        assert "接触记录号" in text
        assert "CSV1" in text

    def test_existing_marketing_report_matches_total_opening_rate_without_new_rows(self):
        db = SessionLocal()
        try:
            db.add(
                MarketingDetail(
                    kf_id="KF001",
                    finish_date=pd.Timestamp("2026-11-02").date(),
                    service_type="叠加包",
                    valid_type="月包",
                    product_id="P1",
                    product_name="测试产品",
                    trade_id="T1",
                    data_type="xszb",
                )
            )
            db.commit()
        finally:
            db.close()

        resp = _upload(
            [
                _row("C1", "KF001", aa=True),
                _row("C2", "KF001", aa=False),
                _row("C3", "KF003", aa=True),
            ]
        )
        assert resp.status_code == 200, resp.text

        report = client.get("/api/marketing/report", params={"year_month": "2026-11"}).json()
        assert len(report["employees"]) == 1
        employee = report["employees"][0]
        assert employee["kf_id"] == "KF001"
        assert employee["contact_count"] == 2
        assert employee["opened_count"] == 1
        assert employee["opening_rate"] == 0.5
        assert report["stats"]["contact_count"] == 2
        assert report["stats"]["opening_rate"] == 0.5

        product = report["products"][0]
        assert "opening_rate" not in product

    def test_delete_by_date_batch_and_single(self):
        first = _upload([_row("D1", aa=True)])
        batch = first.json()["batch"]
        assert client.get("/api/marketing-openings").json()["total"] == 1
        deleted = client.delete("/api/marketing-openings/by-date", params={"date": "2026-11-02"})
        assert deleted.status_code == 200
        assert deleted.json()["count"] == 1
        assert client.get("/api/marketing-openings").json()["total"] == 0

        second = _upload([_row("D2", aa=True)])
        batch = second.json()["batch"]
        deleted = client.delete(f"/api/marketing-openings/import/{batch}")
        assert deleted.status_code == 200
        assert deleted.json()["count"] == 1

        third = _upload([_row("D3", aa=True)])
        record_id = client.get("/api/marketing-openings").json()["items"][0]["id"]
        deleted = client.delete(f"/api/marketing-openings/{record_id}")
        assert deleted.status_code == 200

    def test_department_scope_filters_opening_data(self):
        dept_a = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>A部门"
        dept_b = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>B部门"
        db = SessionLocal()
        try:
            db.query(Employee).filter(Employee.emp_no == "KF001").update({"dept": dept_a})
            db.query(Employee).filter(Employee.emp_no == "KF002").update({"dept": dept_b})
            db.commit()
        finally:
            db.close()

        resp = _upload([_row("S1", "KF001", aa=True), _row("S2", "KF002", aa=True)])
        assert resp.status_code == 200, resp.text

        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: {
            "id": 2,
            "username": "dept_user",
            "role": "user",
            "is_system": False,
            "permissions": json.dumps(
                {"marketing_opening.view": True, "marketing_opening_report.view": True}
            ),
            "data_scope": "dept",
            "department_group_paths": [dept_a],
        }
        try:
            listing = client.get("/api/marketing-openings").json()
            assert listing["total"] == 1
            assert listing["items"][0]["emp_no"] == "KF001"

            report = client.get(
                "/api/marketing-openings/report", params={"year_month": "2026-11"}
            ).json()
            assert [item["kf_id"] for item in report["employees"]] == ["KF001"]
            assert report["stats"]["contact_count"] == 1
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original
            else:
                app.dependency_overrides.pop(get_current_user, None)

    def test_dept_user_with_upload_permission_can_import(self):
        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: {
            "id": 1,
            "username": "dept_upload_user",
            "role": "user",
            "is_system": False,
            "permissions": json.dumps({"marketing_opening.upload": True}),
            "data_scope": "dept",
            "department_group_paths": ["广西分公司>>省中心>>客户服务营销中心>>热线运营组>>A部门"],
        }
        try:
            resp = _upload([_row("U1", "KF001", aa=True)])
            assert resp.status_code == 200, resp.text
            assert resp.json()["count"] == 1
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original
            else:
                app.dependency_overrides.pop(get_current_user, None)

    def test_dept_user_without_upload_permission_cannot_import(self):
        original = app.dependency_overrides.get(get_current_user)
        app.dependency_overrides[get_current_user] = lambda: {
            "id": 1,
            "username": "dept_view_user",
            "role": "user",
            "is_system": False,
            "permissions": json.dumps({"marketing_opening.view": True}),
            "data_scope": "dept",
            "department_group_paths": ["广西分公司>>省中心>>客户服务营销中心>>热线运营组>>A部门"],
        }
        try:
            resp = _upload([_row("U2", "KF001", aa=True)])
            assert resp.status_code == 403
        finally:
            if original is not None:
                app.dependency_overrides[get_current_user] = original
            else:
                app.dependency_overrides.pop(get_current_user, None)

    def test_rejects_wrong_file_header(self):
        df = pd.DataFrame([["KF_ID", "FINISH_DATE"], ["KF001", "2026-11-02"]])
        buf = io.BytesIO()
        df.to_excel(buf, index=False, header=False)
        buf.seek(0)
        resp = client.post(
            "/api/marketing-openings/import",
            files={"file": ("wrong.xlsx", buf, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        assert resp.status_code == 400
        assert "开口数据表头" in resp.json()["detail"]


class TestAssignedTeamMerge:
    LEADER_DEPT = "广西分公司>>省中心>>客户服务营销中心>>二线支撑组"
    MEMBER_DEPT = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"

    def setup_method(self):
        _clean()
        db = SessionLocal()
        try:
            db.add_all([
                Employee(emp_no="KF001", name="张三", team="热线1组", dept=self.MEMBER_DEPT, status="在职"),
                Employee(emp_no="KF009", name="王组长", team="热线1组", dept=self.LEADER_DEPT, role="组长", status="在职"),
            ])
            db.commit()
        finally:
            db.close()

    def test_assign_team_merges_team_and_class_buckets(self):
        rows = [
            _row("C1", "KF001", "张三", aa=True, active_overlay=True, opened_overlay=True),
            _row("C2", "KF009", "王组长", aa=True, active_broadband=True, opened_broadband=True),
        ]
        resp = _upload(rows)
        assert resp.status_code == 200, resp.text

        report = client.get("/api/marketing-openings/report", params={"year_month": "2026-11"}).json()
        split = [t for t in report["teams"] if t["team"] == "热线1组"]
        assert len(split) == 2

        db = SessionLocal()
        try:
            leader = db.query(Employee).filter(Employee.emp_no == "KF009").first()
            leader_id = leader.id
        finally:
            db.close()
        resp = client.put(f"/api/employees/{leader_id}", json={
            "assign_dept": self.MEMBER_DEPT,
            "assign_team": "热线1组",
        })
        assert resp.status_code == 200, resp.text

        report = client.get("/api/marketing-openings/report", params={"year_month": "2026-11"}).json()
        merged = [t for t in report["teams"] if t["team"] == "热线1组"]
        assert len(merged) == 1
        team = merged[0]
        assert team["dept"] == self.MEMBER_DEPT
        assert team["contact_count"] == 2
        assert team["people"] == 2
        classes = [c for c in report["classes"] if c["class_name"] == "热线"]
        assert len(classes) == 1
        assert classes[0]["dept"] == self.MEMBER_DEPT
        assert classes[0]["people"] == 2
