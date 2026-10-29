import io
import os
from datetime import date
from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.models.database import Base, get_db
from app.models.user import User
from app.models.role import Role
from app.models.employee import Employee
from app.models.marketing_detail import MarketingDetail
from app.core.security import create_access_token, get_password_hash
from app.main import app

TEST_DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:admin123%40kf@localhost:5432/schedule_test",
)
engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

DEPT_A = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>A部门"
DEPT_B = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>B部门"


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _make_excel(rows):
    output = io.BytesIO()
    pd.DataFrame(rows).to_excel(output, index=False)
    output.seek(0)
    return output


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        all_role = Role(
            name="scope_all",
            data_scope="all",
            permissions='{"employees.view": true, "employees.edit": true, "employees.create": true, "employees.delete": true, "employees.upload": true, "employees.export": true, "marketing.view": true, "marketing_report.view": true, "marketing_report.export": true, "marketing_overall.view": true, "marketing_overall.export": true, "roles.view": true, "roles.manage": true}',
        )
        dept_role = Role(
            name="scope_dept",
            data_scope="dept",
            permissions='{"employees.view": true, "employees.edit": true, "employees.create": true, "employees.delete": true, "employees.upload": true, "employees.export": true, "marketing.view": true, "marketing_report.view": true, "marketing_report.export": true, "marketing_overall.view": true, "marketing_overall.export": true}',
        )
        no_attendance_role = Role(
            name="dept_no_att",
            data_scope="dept",
            permissions='{"marketing.view": true}',
        )
        db.add_all([all_role, dept_role, no_attendance_role])
        db.commit()

        all_user = User(
            username="scope_all_user",
            password_hash=get_password_hash("pass"),
            display_name="全部数据用户",
            role="scope_all",
            role_id=all_role.id,
        )
        dept_user = User(
            username="scope_dept_user",
            password_hash=get_password_hash("pass"),
            display_name="A部门用户",
            dept=DEPT_A,
            role="scope_dept",
            role_id=dept_role.id,
        )
        no_attendance_user = User(
            username="scope_no_attendance_user",
            password_hash=get_password_hash("pass"),
            display_name="无考勤用户",
            dept=DEPT_A,
            role="dept_no_att",
            role_id=no_attendance_role.id,
        )
        db.add_all([all_user, dept_user, no_attendance_user])
        db.commit()

        emp_a = Employee(emp_no="A001", name="A部门员工", team="A班组", dept=DEPT_A, role="组员", status="在职")
        emp_b = Employee(emp_no="B001", name="B部门员工", team="B班组", dept=DEPT_B, role="组员", status="在职")
        db.add_all([emp_a, emp_b])
        db.commit()

        db.add_all([
            MarketingDetail(
                kf_id="A001", org_name=DEPT_A, organization=DEPT_A,
                tenant="A租户", data_type="xszb", finish_date=date(2026, 1, 10),
                service_type="叠加包", valid_type="日包", trade_id="TA001",
                product_id="P1", product_name="产品1", lh_qh="来话",
            ),
            MarketingDetail(
                kf_id="B001", org_name=DEPT_B, organization=DEPT_B,
                tenant="B租户", data_type="xszb", finish_date=date(2026, 2, 5),
                service_type="叠加包", valid_type="日包", trade_id="TB001",
                product_id="P2", product_name="产品2", lh_qh="去话",
            ),
        ])
        db.commit()

        global ALL_TOKEN, DEPT_TOKEN, NO_ATTENDANCE_TOKEN, EMP_A_ID, EMP_B_ID, DETAIL_B_ID
        ALL_TOKEN = create_access_token(data={"sub": str(all_user.id)})
        DEPT_TOKEN = create_access_token(data={"sub": str(dept_user.id)})
        NO_ATTENDANCE_TOKEN = create_access_token(data={"sub": str(no_attendance_user.id)})
        EMP_A_ID = emp_a.id
        EMP_B_ID = emp_b.id
        DETAIL_B_ID = db.query(MarketingDetail).filter(MarketingDetail.kf_id == "B001").first().id
    finally:
        db.close()
    yield


def test_auth_me_exposes_scope_fields():
    res = client.get("/api/auth/me", headers=auth_header(DEPT_TOKEN))
    assert res.status_code == 200
    data = res.json()
    assert data["dept"] == DEPT_A
    assert data["data_scope"] == "dept"


def test_employee_list_and_options_are_scoped():
    res = client.get("/api/employees", headers=auth_header(DEPT_TOKEN))
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["emp_no"] == "A001"

    all_res = client.get("/api/employees", headers=auth_header(ALL_TOKEN))
    assert all_res.status_code == 200
    assert all_res.json()["total"] == 2

    teams = client.get("/api/employees/teams", headers=auth_header(DEPT_TOKEN)).json()
    assert {item["team"] for item in teams} == {"A班组"}
    depts = client.get("/api/employees/departments", headers=auth_header(DEPT_TOKEN)).json()
    assert {item["dept"] for item in depts} == {DEPT_A}


def test_dept_user_can_update_own_employee_only():
    ok = client.put(
        f"/api/employees/{EMP_A_ID}",
        json={"name": "A部门员工改名"},
        headers=auth_header(DEPT_TOKEN),
    )
    assert ok.status_code == 200

    forbidden = client.put(
        f"/api/employees/{EMP_B_ID}",
        json={"name": "越权改名"},
        headers=auth_header(DEPT_TOKEN),
    )
    assert forbidden.status_code == 404

    delete_b = client.delete(f"/api/employees/{EMP_B_ID}", headers=auth_header(DEPT_TOKEN))
    assert delete_b.status_code == 404


def test_dept_user_create_employee_is_forced_into_own_dept():
    res = client.post(
        "/api/employees",
        json={"emp_no": "A002", "name": "新增A部门员工", "team": "A班组", "dept": "", "role": "组员"},
        headers=auth_header(DEPT_TOKEN),
    )
    assert res.status_code == 200

    db = TestingSessionLocal()
    try:
        emp = db.query(Employee).filter(Employee.emp_no == "A002").first()
        assert emp.dept == DEPT_A
    finally:
        db.close()

    forbidden = client.post(
        "/api/employees",
        json={"emp_no": "B002", "name": "新增B部门员工", "team": "B班组", "dept": DEPT_B, "role": "组员"},
        headers=auth_header(DEPT_TOKEN),
    )
    assert forbidden.status_code == 403


def test_dept_user_import_only_own_department():
    excel = _make_excel([
        {"工号": "A003", "姓名": "导入A", "班组": "A班组", "部门": "", "岗位": "组员"},
        {"工号": "B003", "姓名": "导入B", "班组": "B班组", "部门": DEPT_B, "岗位": "组员"},
    ])
    res = client.post(
        "/api/employees/import",
        files={"file": ("employees.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(DEPT_TOKEN),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["created"] == 1
    assert data["skipped"] == 1
    assert data["errors"]

    db = TestingSessionLocal()
    try:
        assert db.query(Employee).filter(Employee.emp_no == "A003").first().dept == DEPT_A
        assert db.query(Employee).filter(Employee.emp_no == "B003").first() is None
    finally:
        db.close()


def test_employee_export_is_scoped():
    res = client.get("/api/employees/export", headers=auth_header(DEPT_TOKEN))
    assert res.status_code == 200
    text = res.content.decode("utf-8")
    assert "A001" in text
    assert "B001" not in text


def test_marketing_details_and_report_are_scoped():
    details = client.get("/api/marketing/details", headers=auth_header(DEPT_TOKEN))
    assert details.status_code == 200
    data = details.json()
    assert data["total"] == 1
    assert data["items"][0]["kf_id"] == "A001"

    all_details = client.get("/api/marketing/details", headers=auth_header(ALL_TOKEN))
    assert all_details.json()["total"] == 2

    report = client.get("/api/marketing/report", params={"start_date": "2026-01-01", "end_date": "2026-01-31"}, headers=auth_header(DEPT_TOKEN))
    assert report.status_code == 200
    employees = report.json()["employees"]
    assert [item["kf_id"] for item in employees] == ["A001"]
    assert report.json()["stats"]["total"] == 1


def test_marketing_overall_is_scoped():
    res = client.get(
        "/api/marketing/overall-report",
        params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        headers=auth_header(DEPT_TOKEN),
    )
    assert res.status_code == 200
    assert res.json()["data_ranges"]["database"]["xszb"]["end_date"] == "2026-01-10"


def test_dept_user_cannot_delete_or_import_marketing_data():
    delete_res = client.delete(f"/api/marketing/details/{DETAIL_B_ID}", headers=auth_header(DEPT_TOKEN))
    assert delete_res.status_code == 403

    excel = _make_excel([{"kf_id": "A001"}])
    import_res = client.post(
        "/api/marketing/details/import",
        files={"file": ("marketing.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(DEPT_TOKEN),
    )
    assert import_res.status_code == 403


def test_attendance_read_endpoints_require_permission():
    res = client.get("/api/checkins/report", headers=auth_header(NO_ATTENDANCE_TOKEN))
    assert res.status_code == 403

    res = client.get("/api/reports/month", params={"year_month": "2026-01"}, headers=auth_header(NO_ATTENDANCE_TOKEN))
    assert res.status_code == 403


def test_role_data_scope_can_be_configured():
    res = client.post(
        "/api/roles",
        json={
            "name": "scope_dept_temp",
            "description": "临时本部门角色",
            "data_scope": "dept",
            "permissions": {"employees.view": True},
        },
        headers=auth_header(ALL_TOKEN),
    )
    assert res.status_code == 200

    roles = client.get("/api/roles/all", headers=auth_header(ALL_TOKEN)).json()
    role = next(item for item in roles if item["name"] == "scope_dept_temp")
    assert role["data_scope"] == "dept"

    invalid = client.post(
        "/api/roles",
        json={"name": "scope_invalid", "data_scope": "invalid", "permissions": {}},
        headers=auth_header(ALL_TOKEN),
    )
    assert invalid.status_code == 400
