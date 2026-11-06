"""报表页面查询班组/组长下拉时，不应强制要求员工管理查看权限。"""
import json
import os
from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "backend"
sys.path.insert(0, str(BASE))

from app.core.config import settings
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.database import Base, get_db
from app.models.employee import Employee
from app.models.role import Role
from app.models.user import User

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

HOTLINE = settings.LEGACY_SCOPE_DEPT_PATH
DEPT_A = f"{HOTLINE}>>A部门"
DEPT_B = f"{HOTLINE}>>B部门"
TEAM_A = "热线一班1组"
TEAM_B = "热线二班1组"


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        report_role = Role(
            name="workload_report_only",
            data_scope="dept",
            permissions=json.dumps({"workload_report.view": True}),
        )
        no_permission_role = Role(
            name="no_team_lookup_permission",
            data_scope="dept",
            permissions=json.dumps({"agent.use": True}),
        )
        db.add_all([report_role, no_permission_role])
        db.commit()

        report_user = User(
            username="report_only_user",
            password_hash=get_password_hash("pass"),
            display_name="团队管理用户",
            dept=DEPT_A,
            role=report_role.name,
            role_id=report_role.id,
        )
        no_permission_user = User(
            username="no_team_lookup_user",
            password_hash=get_password_hash("pass"),
            display_name="无下拉权限用户",
            dept=DEPT_A,
            role=no_permission_role.name,
            role_id=no_permission_role.id,
        )
        db.add_all([report_user, no_permission_user])
        db.add_all([
            Employee(emp_no="A001", name="A组长", team=TEAM_A, dept=DEPT_A, role="组长", status="在职"),
            Employee(emp_no="A002", name="A组员", team=TEAM_A, dept=DEPT_A, role="组员", status="在职"),
            Employee(emp_no="B001", name="B组长", team=TEAM_B, dept=DEPT_B, role="组长", status="在职"),
        ])
        db.commit()

        global REPORT_TOKEN, NO_PERMISSION_TOKEN
        REPORT_TOKEN = create_access_token(data={"sub": str(report_user.id)})
        NO_PERMISSION_TOKEN = create_access_token(data={"sub": str(no_permission_user.id)})
    finally:
        db.close()
    yield


def test_report_permission_can_load_legacy_team_options_and_leaders():
    headers = auth_header(REPORT_TOKEN)
    teams = client.get(
        "/api/employees/teams",
        params={"include_dept": True, "scope": "legacy"},
        headers=headers,
    )
    assert teams.status_code == 200
    assert {(item["dept"], item["team"]) for item in teams.json()} == {
        (DEPT_A, TEAM_A),
        (DEPT_B, TEAM_B),
    }

    leaders = client.get("/api/employees/leaders", params={"scope": "legacy"}, headers=headers)
    assert leaders.status_code == 200
    assert {(item["dept"], item["team"], item["leader"]) for item in leaders.json()} == {
        (DEPT_A, TEAM_A, "A组长"),
        (DEPT_B, TEAM_B, "B组长"),
    }


def test_report_permission_still_respects_department_scope():
    headers = auth_header(REPORT_TOKEN)
    teams = client.get("/api/employees/teams", params={"include_dept": True}, headers=headers)
    assert teams.status_code == 200
    assert {(item["dept"], item["team"]) for item in teams.json()} == {(DEPT_A, TEAM_A)}


def test_user_without_report_or_employee_permission_is_forbidden():
    headers = auth_header(NO_PERMISSION_TOKEN)
    assert client.get("/api/employees/teams", headers=headers).status_code == 403
    assert client.get("/api/employees/leaders", headers=headers).status_code == 403
