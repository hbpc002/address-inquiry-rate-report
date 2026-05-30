"""
测试用户启用/禁用功能
"""
import os
import json
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
from app.models.operation_log import OperationLog
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
            permissions='{"users.view": true, "users.manage": true}',
        )
        user_role = Role(
            name="user",
            description="普通用户",
            is_system=False,
            permissions='{"users.view": true}',
        )
        db.add_all([admin_role, user_role])
        db.commit()

        admin = User(
            username='enable_admin',
            password_hash=get_password_hash('admin123'),
            display_name='启用测试管理员',
            role='admin',
            role_id=admin_role.id,
            is_active=True,
        )
        normal_user = User(
            username='enable_normal',
            password_hash=get_password_hash('user123'),
            display_name='启用测试普通用户',
            role='user',
            role_id=user_role.id,
            is_active=True,
        )
        disabled_user = User(
            username='enable_disabled',
            password_hash=get_password_hash('disabled123'),
            display_name='已禁用用户',
            role='user',
            role_id=user_role.id,
            is_active=False,
        )
        db.add_all([admin, normal_user, disabled_user])
        db.commit()

        global ADMIN_ID, NORMAL_ID, DISABLED_ID, ADMIN_TOKEN, USER_TOKEN
        ADMIN_ID = admin.id
        NORMAL_ID = normal_user.id
        DISABLED_ID = disabled_user.id
        ADMIN_TOKEN = create_access_token(data={"sub": str(admin.id)})
        USER_TOKEN = create_access_token(data={"sub": str(normal_user.id)})
    finally:
        db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


# ========= 启用成功 =========

def test_enable_user_success():
    res = client.post(f"/api/users/{DISABLED_ID}/enable", headers=auth_header(ADMIN_TOKEN))
    assert res.status_code == 200
    assert res.json()["message"] == "启用成功"

    db = TestingSessionLocal()
    try:
        user = db.query(User).filter(User.id == DISABLED_ID).first()
        assert user.is_active is True
    finally:
        db.close()


# ========= 已启用状态下重复启用 =========

def test_enable_user_already_active():
    res = client.post(f"/api/users/{NORMAL_ID}/enable", headers=auth_header(ADMIN_TOKEN))
    assert res.status_code == 400
    assert "已是启用状态" in res.json()["detail"]


# ========= 用户不存在 =========

def test_enable_user_not_found():
    res = client.post("/api/users/99999/enable", headers=auth_header(ADMIN_TOKEN))
    assert res.status_code == 404
    assert "不存在" in res.json()["detail"]


# ========= 无管理权限 =========

def test_enable_user_no_permission():
    res = client.post(f"/api/users/{NORMAL_ID}/enable", headers=auth_header(USER_TOKEN))
    assert res.status_code == 403
    assert "权限不足" in res.json()["detail"]


# ========= 未认证 =========

def test_enable_user_unauthenticated():
    res = client.post(f"/api/users/{DISABLED_ID}/enable")
    assert res.status_code == 401


# ========= 禁用后再启用 =========

def test_disable_then_enable():
    db = TestingSessionLocal()
    try:
        test_user = User(
            username='enable_disable_test',
            password_hash=get_password_hash('test123'),
            display_name='禁用启用测试',
            role='user',
            is_active=True,
        )
        db.add(test_user)
        db.commit()
        user_id = test_user.id
    finally:
        db.close()

    res = client.delete(f"/api/users/{user_id}", headers=auth_header(ADMIN_TOKEN))
    assert res.status_code == 200

    db = TestingSessionLocal()
    try:
        assert db.query(User).filter(User.id == user_id).first().is_active is False
    finally:
        db.close()

    res = client.post(f"/api/users/{user_id}/enable", headers=auth_header(ADMIN_TOKEN))
    assert res.status_code == 200

    db = TestingSessionLocal()
    try:
        assert db.query(User).filter(User.id == user_id).first().is_active is True
    finally:
        db.close()


# ========= 操作日志记录 =========

def test_enable_user_logged():
    db = TestingSessionLocal()
    try:
        test_user = User(
            username='enable_log_test',
            password_hash=get_password_hash('log123'),
            display_name='日志测试',
            role='user',
            is_active=False,
        )
        db.add(test_user)
        db.commit()
        user_id = test_user.id
    finally:
        db.close()

    res = client.post(f"/api/users/{user_id}/enable", headers=auth_header(ADMIN_TOKEN))
    assert res.status_code == 200

    db = TestingSessionLocal()
    try:
        log = db.query(OperationLog).filter(
            OperationLog.operation_type == "enable_user",
            OperationLog.target_id == user_id,
        ).order_by(OperationLog.id.desc()).first()
        assert log is not None
        assert log.user_id == ADMIN_ID
        assert log.target_table == "users"
    finally:
        db.close()


# ========= 重新启用后可登录 =========

def test_enabled_user_can_login():
    password = "justenabled123"
    pw_hash = get_password_hash(password)

    db = TestingSessionLocal()
    try:
        user = User(
            username='enable_login_test',
            password_hash=pw_hash,
            display_name='登录测试',
            role='user',
            is_active=False,
        )
        db.add(user)
        db.commit()
        user_id = user.id
    finally:
        db.close()

    res = client.post(f"/api/users/{user_id}/enable", headers=auth_header(ADMIN_TOKEN))
    assert res.status_code == 200

    res = client.post("/api/auth/login", data={"username": "enable_login_test", "password": password})
    assert res.status_code == 200
    assert "access_token" in res.json()


# ========= 禁用状态无法登录 =========

def test_disabled_user_cannot_login():
    password = "stilldisabled123"
    pw_hash = get_password_hash(password)

    db = TestingSessionLocal()
    try:
        user = User(
            username='enable_still_disabled',
            password_hash=pw_hash,
            display_name='仍禁用用户',
            role='user',
            is_active=False,
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    res = client.post("/api/auth/login", data={"username": "enable_still_disabled", "password": password})
    assert res.status_code == 403
