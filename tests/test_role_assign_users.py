"""
测试角色分配用户功能
"""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.models.database import Base
from app.models.user import User
from app.models.role import Role
from app.core.security import get_password_hash, create_access_token
from app.main import app
from app.models.database import get_db

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:admin123%40kf@localhost:5432/schedule_test")
TEST_DB_URL = os.environ["DATABASE_URL"]
engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        admin_role = Role(
            name="admin",
            description="系统管理员",
            is_system=True,
            permissions='{"roles.view": true, "roles.manage": true, "users.view": true, "users.manage": true}',
        )
        manager_role = Role(
            name="manager",
            description="经理",
            is_system=False,
            permissions='{"roles.view": true, "roles.manage": true, "users.view": true}',
        )
        user_role = Role(
            name="user",
            description="普通用户",
            is_system=False,
            permissions='{"users.view": true}',
        )
        db.add_all([admin_role, manager_role, user_role])
        db.commit()

        admin = User(
            username='role_test_admin',
            password_hash=get_password_hash('admin123'),
            display_name='角色测试管理员',
            role='admin',
            role_id=admin_role.id,
            is_active=True,
        )
        user_a = User(
            username='user_a',
            password_hash=get_password_hash('pass123'),
            display_name='用户A',
            role='user',
            role_id=user_role.id,
            is_active=True,
        )
        user_b = User(
            username='user_b',
            password_hash=get_password_hash('pass123'),
            display_name='用户B',
            role='user',
            role_id=user_role.id,
            is_active=True,
        )
        unassigned_user = User(
            username='unassigned_user',
            password_hash=get_password_hash('pass123'),
            display_name='未分配用户',
            role='user',
            role_id=None,
            is_active=True,
        )
        db.add_all([admin, user_a, user_b, unassigned_user])
        db.commit()

        global ADMIN_TOKEN, USER_TOKEN, MANAGER_TOKEN, ADMIN_ROLE_ID, MANAGER_ROLE_ID, USER_ROLE_ID
        global USER_A_ID, USER_B_ID, UNASSIGNED_ID
        ADMIN_ROLE_ID = admin_role.id
        MANAGER_ROLE_ID = manager_role.id
        USER_ROLE_ID = user_role.id
        USER_A_ID = user_a.id
        USER_B_ID = user_b.id
        UNASSIGNED_ID = unassigned_user.id
        ADMIN_TOKEN = create_access_token(data={"sub": str(admin.id)})
        USER_TOKEN = create_access_token(data={"sub": str(user_a.id)})
        manager = User(
            username='role_test_manager',
            password_hash=get_password_hash('manager123'),
            display_name='角色测试经理',
            role='manager',
            role_id=manager_role.id,
            is_active=True,
        )
        db.add(manager)
        db.commit()
        MANAGER_TOKEN = create_access_token(data={"sub": str(manager.id)})
    finally:
        db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


class TestGetRoleUsers:
    def test_admin_can_get_role_users(self):
        res = client.get(f"/api/roles/{USER_ROLE_ID}/users", headers=auth_header(ADMIN_TOKEN))
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        ids = {u["id"] for u in data}
        assert USER_A_ID in ids
        assert USER_B_ID in ids

    def test_role_with_no_users(self):
        res = client.get(f"/api/roles/{MANAGER_ROLE_ID}/users", headers=auth_header(ADMIN_TOKEN))
        assert res.status_code == 200
        assert len(res.json()) == 1  # the manager user itself
        assert res.json()[0]["username"] == "role_test_manager"

    def test_403_without_roles_view(self):
        res = client.get(f"/api/roles/{USER_ROLE_ID}/users", headers=auth_header(USER_TOKEN))
        assert res.status_code == 403

    def test_404_for_nonexistent_role(self):
        res = client.get("/api/roles/99999/users", headers=auth_header(ADMIN_TOKEN))
        assert res.status_code == 404


class TestGetAllUsers:
    def test_admin_can_get_all_users(self):
        res = client.get("/api/roles/all-users", headers=auth_header(ADMIN_TOKEN))
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 5  # admin + user_a + user_b + unassigned + manager
        usernames = {u["username"] for u in data}
        assert "user_a" in usernames
        assert "unassigned_user" in usernames
        assert "role_test_admin" in usernames

    def test_403_without_roles_manage(self):
        res = client.get("/api/roles/all-users", headers=auth_header(USER_TOKEN))
        assert res.status_code == 403

    def test_returned_fields(self):
        res = client.get("/api/roles/all-users", headers=auth_header(ADMIN_TOKEN))
        assert res.status_code == 200
        for u in res.json():
            assert "id" in u
            assert "username" in u
            assert "display_name" in u


class TestAssignRoleUsers:
    def test_assign_users_to_role(self):
        res = client.put(
            f"/api/roles/{MANAGER_ROLE_ID}/users",
            json={"user_ids": [USER_A_ID, UNASSIGNED_ID]},
            headers=auth_header(ADMIN_TOKEN),
        )
        assert res.status_code == 200
        assert res.json()["message"] == "分配成功"

        db = TestingSessionLocal()
        try:
            ua = db.query(User).filter(User.id == USER_A_ID).first()
            assert ua.role_id == MANAGER_ROLE_ID
            assert ua.role == "manager"

            un = db.query(User).filter(User.id == UNASSIGNED_ID).first()
            assert un.role_id == MANAGER_ROLE_ID
            assert un.role == "manager"

            ub = db.query(User).filter(User.id == USER_B_ID).first()
            assert ub.role_id == USER_ROLE_ID
        finally:
            db.close()

    def test_assign_removes_previous_assignments(self):
        res = client.put(
            f"/api/roles/{MANAGER_ROLE_ID}/users",
            json={"user_ids": [USER_B_ID]},
            headers=auth_header(ADMIN_TOKEN),
        )
        assert res.status_code == 200

        db = TestingSessionLocal()
        try:
            ua = db.query(User).filter(User.id == USER_A_ID).first()
            assert ua.role_id is None
            assert ua.role == "user"

            ub = db.query(User).filter(User.id == USER_B_ID).first()
            assert ub.role_id == MANAGER_ROLE_ID

            un = db.query(User).filter(User.id == UNASSIGNED_ID).first()
            assert un.role_id is None
        finally:
            db.close()

    def test_unassign_all_users(self):
        res = client.put(
            f"/api/roles/{MANAGER_ROLE_ID}/users",
            json={"user_ids": []},
            headers=auth_header(ADMIN_TOKEN),
        )
        assert res.status_code == 200

        db = TestingSessionLocal()
        try:
            count = db.query(User).filter(User.role_id == MANAGER_ROLE_ID).count()
            assert count == 0
        finally:
            db.close()

    def test_assign_back_to_original_role(self):
        res = client.put(
            f"/api/roles/{USER_ROLE_ID}/users",
            json={"user_ids": [USER_A_ID, USER_B_ID]},
            headers=auth_header(ADMIN_TOKEN),
        )
        assert res.status_code == 200

        db = TestingSessionLocal()
        try:
            ua = db.query(User).filter(User.id == USER_A_ID).first()
            assert ua.role_id == USER_ROLE_ID
        finally:
            db.close()

    def test_403_without_roles_manage(self):
        res = client.put(
            f"/api/roles/{USER_ROLE_ID}/users",
            json={"user_ids": []},
            headers=auth_header(USER_TOKEN),
        )
        assert res.status_code == 403

    def test_404_for_nonexistent_role(self):
        res = client.put(
            "/api/roles/99999/users",
            json={"user_ids": []},
            headers=auth_header(ADMIN_TOKEN),
        )
        assert res.status_code == 404
