"""
测试用户批量导入功能
"""
import io
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

import pandas as pd
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
            permissions='{"users.view": true, "users.manage": true}',
        )
        user_role = Role(
            name="user",
            description="普通用户",
            is_system=False,
            permissions='{"users.view": true}',
        )
        manager_role = Role(
            name="manager",
            description="经理",
            is_system=False,
            permissions='{"users.view": true, "users.manage": true}',
        )
        db.add_all([admin_role, user_role, manager_role])
        db.commit()

        admin = User(
            username='import_admin',
            password_hash=get_password_hash('admin123'),
            display_name='导入测试管理员',
            role='admin',
            role_id=admin_role.id,
            is_active=True,
        )
        normal_user = User(
            username='import_normal',
            password_hash=get_password_hash('user123'),
            display_name='导入测试普通用户',
            role='user',
            role_id=user_role.id,
            is_active=True,
        )
        db.add_all([admin, normal_user])
        db.commit()

        global ADMIN_ID, ADMIN_TOKEN, USER_TOKEN
        ADMIN_ID = admin.id
        ADMIN_TOKEN = create_access_token(data={"sub": str(admin.id)})
        USER_TOKEN = create_access_token(data={"sub": str(normal_user.id)})
    finally:
        db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def _make_excel(rows):
    """Helper to create an Excel file in memory from a list of dict rows."""
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='users')
    output.seek(0)
    return output


# ========= 批量导入成功 =========

def test_import_users_success():
    excel = _make_excel([
        {'用户名': 'import_test1', '密码': 'pass123', '显示名': '测试用户1', '角色': 'user'},
        {'用户名': 'import_test2', '密码': 'pass456', '显示名': '测试用户2', '角色': 'manager'},
    ])
    res = client.post(
        "/api/users/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["created"] == 2
    assert data["skipped"] == 0
    assert data["errors"] == []

    db = TestingSessionLocal()
    try:
        u1 = db.query(User).filter(User.username == 'import_test1').first()
        assert u1 is not None
        assert u1.display_name == '测试用户1'
        assert u1.role == 'user'
        assert u1.role_id is not None

        u2 = db.query(User).filter(User.username == 'import_test2').first()
        assert u2 is not None
        assert u2.display_name == '测试用户2'
        assert u2.role == 'manager'
    finally:
        db.close()


# ========= 导入时角色名不存在，自动使用默认角色 =========

def test_import_users_role_not_found():
    excel = _make_excel([
        {'用户名': 'import_norole', '密码': 'pass123', '显示名': '无角色', '角色': 'nonexistent_role'},
    ])
    res = client.post(
        "/api/users/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["created"] == 1
    assert data["skipped"] == 0

    db = TestingSessionLocal()
    try:
        u = db.query(User).filter(User.username == 'import_norole').first()
        assert u is not None
        assert u.role == 'nonexistent_role'
        assert u.role_id is None
    finally:
        db.close()


# ========= 用户名重复时跳过 =========

def test_import_users_duplicate_username():
    excel = _make_excel([
        {'用户名': 'import_normal', '密码': 'pass123', '显示名': '已有用户', '角色': 'user'},
    ])
    res = client.post(
        "/api/users/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["created"] == 0
    assert data["skipped"] == 1
    assert len(data["errors"]) == 1
    assert 'import_normal' in data["errors"][0]
    assert '已存在' in data["errors"][0]


# ========= 空用户名和空密码行跳过 =========

def test_import_users_skip_empty_rows():
    excel = _make_excel([
        {'用户名': '', '密码': '', '显示名': '', '角色': ''},
        {'用户名': 'import_valid', '密码': 'validpass', '显示名': '有效用户', '角色': 'user'},
    ])
    res = client.post(
        "/api/users/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["created"] == 1
    assert data["skipped"] == 1


# ========= 缺少必需列时报错 =========

def test_import_users_missing_required_columns():
    df = pd.DataFrame({'显示名': ['用户A'], '角色': ['user']})
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    output.seek(0)
    res = client.post(
        "/api/users/import",
        files={"file": ("bad.xlsx", output, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert res.status_code == 400
    assert '缺少必需列' in res.json()["detail"]


# ========= 非Excel文件上传 =========

def test_import_users_not_excel():
    res = client.post(
        "/api/users/import",
        files={"file": ("test.txt", io.BytesIO(b"not an excel"), "text/plain")},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert res.status_code == 400
    assert 'Excel' in res.json()["detail"]


# ========= 无管理权限 =========

def test_import_users_no_permission():
    excel = _make_excel([
        {'用户名': 'import_noperm', '密码': 'pass123', '显示名': '无权限', '角色': 'user'},
    ])
    res = client.post(
        "/api/users/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(USER_TOKEN),
    )
    assert res.status_code == 403
    assert '权限不足' in res.json()["detail"]


# ========= 未认证 =========

def test_import_users_unauthenticated():
    excel = _make_excel([
        {'用户名': 'import_noauth', '密码': 'pass123', '显示名': '未认证', '角色': 'user'},
    ])
    res = client.post(
        "/api/users/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 401


# ========= 带显示名的导入 =========

def test_import_users_with_display_name():
    excel = _make_excel([
        {'用户名': 'import_display', '密码': 'pass123', '显示名': '自定义显示名', '角色': ''},
    ])
    res = client.post(
        "/api/users/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["created"] == 1

    db = TestingSessionLocal()
    try:
        u = db.query(User).filter(User.username == 'import_display').first()
        assert u is not None
        assert u.display_name == '自定义显示名'
        assert u.role == 'user'
    finally:
        db.close()


# ========= 不指定角色 =========

def test_import_users_without_role():
    excel = _make_excel([
        {'用户名': 'import_norole2', '密码': 'pass123', '显示名': '', '角色': ''},
    ])
    res = client.post(
        "/api/users/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["created"] == 1

    db = TestingSessionLocal()
    try:
        u = db.query(User).filter(User.username == 'import_norole2').first()
        assert u is not None
        assert u.role == 'user'
        assert u.display_name is None
    finally:
        db.close()


# ========= 混合成功/失败场景 =========

def test_import_users_mixed():
    excel = _make_excel([
        {'用户名': 'import_mix1', '密码': 'pass1', '显示名': '混合1', '角色': 'user'},
        {'用户名': 'import_normal', '密码': 'pass2', '显示名': '已存在', '角色': 'admin'},
        {'用户名': 'import_mix2', '密码': 'pass3', '显示名': '混合2', '角色': 'manager'},
        {'用户名': '', '密码': 'pass4', '显示名': '空用户名', '角色': 'user'},
    ])
    res = client.post(
        "/api/users/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert res.status_code == 200
    data = res.json()
    assert data["created"] == 2
    assert data["skipped"] == 2
    assert len(data["errors"]) == 1


# ========= 下载模板 =========

def test_download_import_template():
    res = client.get("/api/users/import-template", headers=auth_header(ADMIN_TOKEN))
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "UTF-8''" in res.headers.get("content-disposition", "")


def test_download_import_template_no_permission():
    res = client.get("/api/users/import-template", headers=auth_header(USER_TOKEN))
    assert res.status_code == 403


def test_download_import_template_unauthenticated():
    res = client.get("/api/users/import-template")
    assert res.status_code == 401


# ========= 导入操作日志 =========

def test_import_users_logged():
    from app.models.operation_log import OperationLog
    excel = _make_excel([
        {'用户名': 'import_log_test', '密码': 'logpass', '显示名': '日志用户', '角色': 'user'},
    ])
    res = client.post(
        "/api/users/import",
        files={"file": ("test.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_header(ADMIN_TOKEN),
    )
    assert res.status_code == 200

    db = TestingSessionLocal()
    try:
        log = db.query(OperationLog).filter(
            OperationLog.operation_type == "import_users",
        ).order_by(OperationLog.id.desc()).first()
        assert log is not None
        assert log.user_id == ADMIN_ID
        assert log.target_table == "users"
    finally:
        db.close()
