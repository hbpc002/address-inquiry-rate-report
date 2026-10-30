import os
from datetime import date
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.main import app
from app.models.database import Base, get_db
from app.models.department_group import DepartmentGroup, DepartmentGroupPath
from app.models.employee import Employee
from app.models.marketing_detail import MarketingDetail
from app.models.role import Role
from app.models.user import User
from app.core.security import create_access_token, get_password_hash

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
DEPT_A2 = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>A2部门"
DEPT_B = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>B部门"


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        admin_role = Role(name="admin", is_system=True, permissions="{}", data_scope="all")
        dept_role = Role(
            name="dept_overall_all",
            permissions='{"employees.view": true, "employees.edit": true, "marketing.view": true, "marketing_report.view": true, "marketing_report.export": true, "marketing_overall.view": true, "marketing_overall.export": true}',
            data_scope="dept",
            data_scope_config='{"marketing_overall": "all"}',
        )
        db.add_all([admin_role, dept_role])
        db.commit()

        group = DepartmentGroup(name="A部门组", description="多路径测试")
        db.add(group)
        db.flush()
        db.add_all([
            DepartmentGroupPath(group_id=group.id, path=DEPT_A),
            DepartmentGroupPath(group_id=group.id, path=DEPT_A2),
        ])
        db.commit()

        admin = User(
            username="dg_admin", password_hash=get_password_hash("pass"),
            display_name="管理员", role="admin", role_id=admin_role.id,
        )
        scoped = User(
            username="dg_scoped", password_hash=get_password_hash("pass"),
            display_name="部门组用户", role="dept_overall_all", role_id=dept_role.id,
            department_group_id=group.id,
        )
        db.add_all([admin, scoped])
        db.commit()

        db.add_all([
            Employee(emp_no="DGA001", name="A员工", team="A组", dept=DEPT_A, role="组员", status="在职"),
            Employee(emp_no="DGA002", name="A2员工", team="A2组", dept=DEPT_A2, role="组员", status="在职"),
            Employee(emp_no="DGB001", name="B员工", team="B组", dept=DEPT_B, role="组员", status="在职"),
        ])
        db.commit()

        db.add_all([
            MarketingDetail(kf_id="DGA001", data_type="xszb", finish_date=date(2026, 1, 10), service_type="叠加包", valid_type="日包", trade_id="DGA-T1", product_id="P1", product_name="产品1"),
            MarketingDetail(kf_id="DGA002", data_type="xszb", finish_date=date(2026, 1, 11), service_type="叠加包", valid_type="日包", trade_id="DGA-T2", product_id="P1", product_name="产品1"),
            MarketingDetail(kf_id="DGB001", data_type="xszb", finish_date=date(2026, 2, 5), service_type="叠加包", valid_type="日包", trade_id="DGB-T1", product_id="P2", product_name="产品2"),
        ])
        db.commit()

        global ADMIN_TOKEN, SCOPED_TOKEN, GROUP_ID
        ADMIN_TOKEN = create_access_token(data={"sub": str(admin.id)})
        SCOPED_TOKEN = create_access_token(data={"sub": str(scoped.id)})
        GROUP_ID = group.id
    finally:
        db.close()


def test_department_group_options_and_paths():
    res = client.get("/api/department-groups/options", headers=auth_header(ADMIN_TOKEN))
    assert res.status_code == 200
    data = res.json()
    group = next(item for item in data if item["id"] == GROUP_ID)
    assert set(group["paths"]) == {DEPT_A, DEPT_A2}


def test_auth_me_returns_department_group_and_page_scope():
    res = client.get("/api/auth/me", headers=auth_header(SCOPED_TOKEN))
    assert res.status_code == 200
    data = res.json()
    assert data["department_group_name"] == "A部门组"
    assert set(data["department_group_paths"]) == {DEPT_A, DEPT_A2}
    assert data["data_scope"] == "dept"
    assert data["data_scope_config"] == '{"marketing_overall": "all"}'
    assert data["employee_write_scope"] == "dept"


def test_multi_path_employee_scope():
    res = client.get("/api/employees", headers=auth_header(SCOPED_TOKEN))
    assert res.status_code == 200
    emp_nos = {item["emp_no"] for item in res.json()["items"]}
    assert emp_nos == {"DGA001", "DGA002"}


def test_page_level_scope_all_for_overall_only():
    details = client.get("/api/marketing/details", headers=auth_header(SCOPED_TOKEN))
    assert details.status_code == 200
    assert {item["kf_id"] for item in details.json()["items"]} == {"DGA001", "DGA002"}

    report = client.get(
        "/api/marketing/report",
        params={"start_date": "2026-01-01", "end_date": "2026-02-28"},
        headers=auth_header(SCOPED_TOKEN),
    )
    assert report.status_code == 200
    assert {item["kf_id"] for item in report.json()["employees"]} == {"DGA001", "DGA002"}

    overall = client.get(
        "/api/marketing/overall-report",
        params={"start_date": "2026-01-01", "end_date": "2026-02-28"},
        headers=auth_header(SCOPED_TOKEN),
    )
    assert overall.status_code == 200
    assert overall.json()["data_ranges"]["database"]["xszb"]["end_date"] == "2026-02-05"


def test_department_group_crud_requires_permission_and_blocks_delete_in_use():
    denied = client.post(
        "/api/department-groups",
        json={"name": "越权部门", "paths": [DEPT_A]},
        headers=auth_header(SCOPED_TOKEN),
    )
    assert denied.status_code == 403

    created = client.post(
        "/api/department-groups",
        json={"name": "临时部门组", "paths": [DEPT_A], "description": "test"},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert created.status_code == 200
    group_id = created.json()["id"]

    updated = client.put(
        f"/api/department-groups/{group_id}",
        json={"paths": [DEPT_A, DEPT_A2]},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert updated.status_code == 200

    in_use = client.delete(f"/api/department-groups/{GROUP_ID}", headers=auth_header(ADMIN_TOKEN))
    assert in_use.status_code == 400

    deleted = client.delete(f"/api/department-groups/{group_id}", headers=auth_header(ADMIN_TOKEN))
    assert deleted.status_code == 200


def test_long_role_name_can_create_and_update_user():
    role_name = "ComplaintsHandlingTeam"
    created_role = client.post(
        "/api/roles",
        json={"name": role_name, "data_scope": "dept", "permissions": {"employees.view": True}},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert created_role.status_code == 200
    role_id = created_role.json()["id"]

    created_user = client.post(
        "/api/users",
        json={"username": "dg_long_role", "password": "pass123", "display_name": "长角色", "role_id": role_id, "department_group_id": GROUP_ID},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert created_user.status_code == 200
    user_id = created_user.json()["id"]

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        assert user.role == role_name
        assert user.department_group_id == GROUP_ID
    finally:
        db.close()

    updated = client.put(
        f"/api/users/{user_id}",
        json={"display_name": "长角色改名", "role_id": role_id, "department_group_id": GROUP_ID},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert updated.status_code == 200

    too_long = client.post(
        "/api/roles",
        json={"name": "x" * 51, "data_scope": "dept", "permissions": {}},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert too_long.status_code == 422


def test_role_page_scope_config_is_saved_and_filtered():
    created = client.post(
        "/api/roles",
        json={
            "name": "dept_page_scope",
            "data_scope": "dept",
            "data_scope_config": {"marketing_overall": "all", "invalid": "all"},
            "permissions": {"marketing_overall.view": True},
        },
        headers=auth_header(ADMIN_TOKEN),
    )
    assert created.status_code == 200

    roles = client.get("/api/roles/all", headers=auth_header(ADMIN_TOKEN)).json()
    role = next(item for item in roles if item["name"] == "dept_page_scope")
    assert role["data_scope"] == "dept"
    assert role["data_scope_config"] == '{"marketing_overall": "all"}'


def test_legacy_user_department_is_migrated_to_group():
    from app.models.database import _migrate_legacy_user_departments

    legacy_dept = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>历史部门"
    db = TestingSessionLocal()
    try:
        user = User(
            username="dg_legacy", password_hash=get_password_hash("pass"),
            display_name="历史用户", role="user", dept=legacy_dept,
        )
        db.add(user)
        db.commit()
        _migrate_legacy_user_departments(db)
        db.refresh(user)
        assert user.department_group_id is not None
        group = db.query(DepartmentGroup).filter(DepartmentGroup.id == user.department_group_id).first()
        assert group is not None
        assert [item.path for item in group.paths] == [legacy_dept]
    finally:
        db.close()


def _create_scope_user(role_payload, username):
    role_res = client.post(
        "/api/roles",
        json=role_payload,
        headers=auth_header(ADMIN_TOKEN),
    )
    assert role_res.status_code == 200, role_res.text
    role_id = role_res.json()["id"]

    user_res = client.post(
        "/api/users",
        json={
            "username": username,
            "password": "pass123",
            "display_name": username,
            "role_id": role_id,
            "department_group_id": GROUP_ID,
        },
        headers=auth_header(ADMIN_TOKEN),
    )
    assert user_res.status_code == 200, user_res.text
    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == user_res.json()["id"]).first()
        return create_access_token(data={"sub": str(user.id)})
    finally:
        db.close()


def test_employee_read_all_but_write_only_own_department():
    token = _create_scope_user({
        "name": "employee_read_all_write_dept",
        "data_scope": "dept",
        "data_scope_config": {"employees": "all"},
        "employee_write_scope": "dept",
        "permissions": {"employees.view": True, "employees.edit": True, "employees.delete": True},
    }, "dg_read_all_write_dept")

    all_res = client.get("/api/employees", params={"scope": "all"}, headers=auth_header(token))
    assert all_res.status_code == 200
    assert {item["emp_no"] for item in all_res.json()["items"]} == {"DGA001", "DGA002", "DGB001"}

    dept_res = client.get("/api/employees", params={"scope": "dept"}, headers=auth_header(token))
    assert dept_res.status_code == 200
    assert {item["emp_no"] for item in dept_res.json()["items"]} == {"DGA001", "DGA002"}

    db = TestingSessionLocal()
    try:
        emp_b = db.query(Employee).filter(Employee.emp_no == "DGB001").first()
        emp_a = db.query(Employee).filter(Employee.emp_no == "DGA001").first()
        emp_b_id, emp_a_id = emp_b.id, emp_a.id
    finally:
        db.close()

    forbidden = client.put(
        f"/api/employees/{emp_b_id}",
        json={"name": "越权改名"},
        headers=auth_header(token),
    )
    assert forbidden.status_code == 404

    allowed = client.put(
        f"/api/employees/{emp_a_id}",
        json={"name": "A员工改名"},
        headers=auth_header(token),
    )
    assert allowed.status_code == 200


def test_employee_write_all_role_can_edit_other_department():
    token = _create_scope_user({
        "name": "employee_write_all",
        "data_scope": "dept",
        "data_scope_config": {"employees": "all"},
        "employee_write_scope": "all",
        "permissions": {"employees.view": True, "employees.edit": True},
    }, "dg_write_all")

    db = TestingSessionLocal()
    try:
        emp_b = db.query(Employee).filter(Employee.emp_no == "DGB001").first()
        emp_b_id = emp_b.id
    finally:
        db.close()

    res = client.put(
        f"/api/employees/{emp_b_id}",
        json={"name": "B员工被授权修改"},
        headers=auth_header(token),
    )
    assert res.status_code == 200


def test_department_group_batch_assign_and_remove_users():
    db = TestingSessionLocal()
    try:
        other_group = DepartmentGroup(name="B分配测试部门组", description="批量分配")
        db.add(other_group)
        db.flush()
        db.add(DepartmentGroupPath(group_id=other_group.id, path=DEPT_B))
        unassigned = User(
            username="dg_batch_unassigned", password_hash=get_password_hash("pass"),
            display_name="批量未分配", role="user",
        )
        other = User(
            username="dg_batch_other", password_hash=get_password_hash("pass"),
            display_name="批量其他部门", role="user", department_group_id=other_group.id, dept=DEPT_B,
        )
        db.add_all([unassigned, other])
        db.commit()
        unassigned_id, other_id = unassigned.id, other.id
        other_group_name = other_group.name
    finally:
        db.close()

    available = client.get(
        f"/api/department-groups/{GROUP_ID}/available-users",
        params={"keyword": "dg_batch"},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert available.status_code == 200
    available_items = {item["username"]: item for item in available.json()}
    assert set(available_items) == {"dg_batch_unassigned", "dg_batch_other"}
    assert available_items["dg_batch_other"]["department_group_name"] == other_group_name

    assigned = client.post(
        f"/api/department-groups/{GROUP_ID}/members",
        json={"user_ids": [unassigned_id, other_id, other_id]},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert assigned.status_code == 200
    assert assigned.json()["assigned"] == 2
    assert assigned.json()["skipped"] == 0

    db = TestingSessionLocal()
    try:
        users = db.query(User).filter(User.id.in_([unassigned_id, other_id])).all()
        assert {user.department_group_id for user in users} == {GROUP_ID}
        assert {user.dept for user in users} == {DEPT_A}
    finally:
        db.close()

    repeated = client.post(
        f"/api/department-groups/{GROUP_ID}/members",
        json={"user_ids": [unassigned_id, other_id]},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert repeated.status_code == 200
    assert repeated.json()["assigned"] == 0
    assert repeated.json()["skipped"] == 2

    members = client.get(
        f"/api/department-groups/{GROUP_ID}/members",
        params={"keyword": "dg_batch", "page": 1, "limit": 10},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert members.status_code == 200
    assert members.json()["total"] == 2
    assert {item["username"] for item in members.json()["items"]} == {"dg_batch_unassigned", "dg_batch_other"}

    removed = client.post(
        f"/api/department-groups/{GROUP_ID}/members/remove",
        json={"user_ids": [unassigned_id]},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert removed.status_code == 200
    assert removed.json()["removed"] == 1
    assert removed.json()["skipped"] == 0

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == unassigned_id).first()
        assert user.department_group_id is None
        assert user.dept is None
    finally:
        db.close()


def test_department_group_member_endpoints_require_manage_permission():
    denied_available = client.get(
        f"/api/department-groups/{GROUP_ID}/available-users",
        headers=auth_header(SCOPED_TOKEN),
    )
    assert denied_available.status_code == 403

    denied_members = client.get(
        f"/api/department-groups/{GROUP_ID}/members",
        headers=auth_header(SCOPED_TOKEN),
    )
    assert denied_members.status_code == 403

    denied_add = client.post(
        f"/api/department-groups/{GROUP_ID}/members",
        json={"user_ids": [1]},
        headers=auth_header(SCOPED_TOKEN),
    )
    assert denied_add.status_code == 403

    denied_remove = client.post(
        f"/api/department-groups/{GROUP_ID}/members/remove",
        json={"user_ids": [1]},
        headers=auth_header(SCOPED_TOKEN),
    )
    assert denied_remove.status_code == 403

    missing_user = client.post(
        f"/api/department-groups/{GROUP_ID}/members",
        json={"user_ids": [999999]},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert missing_user.status_code == 404

    missing_group = client.get(
        "/api/department-groups/999999/members",
        headers=auth_header(ADMIN_TOKEN),
    )
    assert missing_group.status_code == 404


def test_update_user_clears_department_scope_when_group_removed():
    db = TestingSessionLocal()
    try:
        user = User(
            username="dg_clear_group", password_hash=get_password_hash("pass"),
            display_name="清空部门组", role="user", department_group_id=GROUP_ID, dept=DEPT_A,
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    res = client.put(
        f"/api/users/{user_id}",
        json={"department_group_id": None},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert res.status_code == 200

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        assert user.department_group_id is None
        assert user.dept is None
    finally:
        db.close()
