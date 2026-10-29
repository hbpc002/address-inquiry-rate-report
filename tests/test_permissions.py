"""
测试权限控制和用户改密码功能（当前角色权限模型）。
"""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - register all model metadata
import app.models.announcement  # noqa: F401
from app.models.database import Base
from app.models.user import User
from app.models.role import Role
from app.core.security import get_password_hash, verify_password, create_access_token, check_permission
from app.core.config import settings

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:admin123%40kf@localhost:5432/schedule_test")
TEST_DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:admin123%40kf@localhost:5432/schedule_test")
engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin_role = Role(
            name='admin',
            is_system=True,
            data_scope='all',
            permissions='{}',
        )
        manager_role = Role(
            name='manager',
            data_scope='all',
            permissions=json.dumps({
                'employees.upload': True,
                'schedules.upload': True,
                'employees.view': True,
            }),
        )
        user_role = Role(
            name='user',
            data_scope='dept',
            permissions=json.dumps({
                'employees.view': True,
                'checkins.upload': True,
            }),
        )
        db.add_all([admin_role, manager_role, user_role])
        db.commit()

        db.add_all([
            User(
                username='test_admin',
                password_hash=get_password_hash('admin123'),
                display_name='测试管理员',
                role='admin',
                role_id=admin_role.id,
            ),
            User(
                username='test_manager',
                password_hash=get_password_hash('manager123'),
                display_name='测试经理',
                role='manager',
                role_id=manager_role.id,
            ),
            User(
                username='test_user_noperm',
                password_hash=get_password_hash('user123'),
                display_name='无权限用户',
                role='user',
                role_id=user_role.id,
            ),
            User(
                username='test_user_perm',
                password_hash=get_password_hash('user123'),
                display_name='有权限用户',
                role='user',
                dept='A部门',
                role_id=user_role.id,
            ),
        ])
        db.commit()
    finally:
        db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)


def get_user_dict(username):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return None
        role = db.query(Role).filter(Role.id == user.role_id).first() if user.role_id else None
        return {
            'id': user.id,
            'username': user.username,
            'role': role.name if role else user.role,
            'permissions': role.permissions if role else '{}',
            'data_scope': role.data_scope if role else 'all',
            'dept': user.dept,
            'display_name': user.display_name,
            'is_system': bool(role and role.is_system),
        }
    finally:
        db.close()


def test_admin_has_all_permissions():
    admin = get_user_dict('test_admin')
    assert check_permission(admin, 'employees.upload') is True
    assert check_permission(admin, 'schedules.upload') is True
    assert check_permission(admin, 'checkins.upload') is True
    assert check_permission(admin, 'system.clear_data') is True
    assert admin['data_scope'] == 'all'


def test_manager_has_assigned_permissions():
    manager = get_user_dict('test_manager')
    assert check_permission(manager, 'employees.upload') is True
    assert check_permission(manager, 'schedules.upload') is True
    assert check_permission(manager, 'checkins.upload') is False
    assert check_permission(manager, 'system.clear_data') is False


def test_user_without_permissions():
    user = get_user_dict('test_user_noperm')
    assert check_permission(user, 'employees.upload') is False
    assert check_permission(user, 'schedules.upload') is False
    assert check_permission(user, 'checkins.upload') is True
    assert check_permission(user, 'system.clear_data') is False
    assert user['data_scope'] == 'dept'


def test_user_permissions_json_parsing():
    user = get_user_dict('test_user_perm')
    perms = json.loads(user['permissions'])
    assert perms.get('employees.view') is True
    assert perms.get('checkins.upload') is True
    assert perms.get('employees.upload') is None or perms.get('employees.upload') is False


def test_change_password_success():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == 'test_user_noperm').first()
        assert verify_password('user123', user.password_hash) is True
        user.password_hash = get_password_hash('newpassword123')
        db.commit()
        assert verify_password('newpassword123', user.password_hash) is True
        assert verify_password('user123', user.password_hash) is False
    finally:
        db.close()


def test_verify_password_wrong():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == 'test_admin').first()
        assert verify_password('wrongpassword', user.password_hash) is False
    finally:
        db.close()


def test_token_contains_valid_user():
    user = get_user_dict('test_manager')
    token = create_access_token(data={"sub": str(user["id"])})

    from jose import jwt
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    assert int(payload.get("sub")) == user["id"]


def test_role_permission_update():
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.name == 'user').first()
        role.permissions = json.dumps({
            'employees.view': True,
            'employees.upload': True,
            'system.clear_data': True,
        })
        db.commit()
    finally:
        db.close()

    user = get_user_dict('test_user_perm')
    assert check_permission(user, 'employees.upload') is True
    assert check_permission(user, 'system.clear_data') is True
    assert check_permission(user, 'schedules.upload') is False
