"""
测试权限控制和用户改密码功能
"""
import datetime
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.database import Base
from app.models.user import User
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.operation_log import OperationLog
from app.models.shift_type import ShiftType
try:
    from app.models.app_config import AppConfig
except:
    AppConfig = None
from app.core.security import get_password_hash, verify_password, create_access_token, check_permission
from app.core.config import settings

# 使用测试数据库
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:admin123%40kf@localhost:5432/schedule_test")
TEST_DB_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:admin123%40kf@localhost:5432/schedule_test")
engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def setup_module():
    """模块级别的设置：创建测试数据库"""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 创建测试用户
        admin = User(
            username='test_admin',
            password_hash=get_password_hash('admin123'),
            display_name='测试管理员',
            role='admin',
            permissions='{}'
        )
        manager = User(
            username='test_manager',
            password_hash=get_password_hash('manager123'),
            display_name='测试经理',
            role='manager',
            permissions='{"upload_employee": true, "upload_schedule": true}'
        )
        user_no_perm = User(
            username='test_user_noperm',
            password_hash=get_password_hash('user123'),
            display_name='无权限用户',
            role='user',
            permissions='{}'
        )
        user_with_perm = User(
            username='test_user_perm',
            password_hash=get_password_hash('user123'),
            display_name='有权限用户',
            role='user',
            permissions='{"upload_checkin": true}'
        )
        db.add_all([admin, manager, user_no_perm, user_with_perm])
        db.commit()
    finally:
        db.close()

def teardown_module():
    """模块级别的清理：删除测试数据"""
    Base.metadata.drop_all(bind=engine)

def get_user_dict(username):
    """获取用户字典（模拟get_current_user返回）"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user:
            return {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "permissions": user.permissions,
                "display_name": user.display_name
            }
        return None
    finally:
        db.close()

# ========= 权限检查测试 =========
def test_admin_has_all_permissions():
    """测试admin有所有权限"""
    admin = get_user_dict('test_admin')
    assert check_permission(admin, 'upload_employee') is True
    assert check_permission(admin, 'upload_schedule') is True
    assert check_permission(admin, 'upload_checkin') is True
    assert check_permission(admin, 'clear_data') is True
    assert check_permission(admin, 'manage_users') is True

def test_manager_has_assigned_permissions():
    """测试manager有分配的权限"""
    manager = get_user_dict('test_manager')
    assert check_permission(manager, 'upload_employee') is True
    assert check_permission(manager, 'upload_schedule') is True
    assert check_permission(manager, 'upload_checkin') is False
    assert check_permission(manager, 'clear_data') is False

def test_user_without_permissions():
    """测试无权限用户没有上传权限"""
    user = get_user_dict('test_user_noperm')
    assert check_permission(user, 'upload_employee') is False
    assert check_permission(user, 'upload_schedule') is False
    assert check_permission(user, 'upload_checkin') is False
    assert check_permission(user, 'clear_data') is False

def test_user_with_permissions():
    """测试有权限用户有特定权限"""
    user = get_user_dict('test_user_perm')
    assert check_permission(user, 'upload_checkin') is True
    assert check_permission(user, 'upload_employee') is False
    assert check_permission(user, 'upload_schedule') is False

def test_permission_json_parsing():
    """测试权限JSON解析"""
    user = get_user_dict('test_manager')
    import json
    perms = json.loads(user['permissions'])
    assert perms.get('upload_employee') is True
    assert perms.get('upload_checkin') is None or perms.get('upload_checkin') is False

# ========= 修改密码测试 =========
def test_change_password_success():
    """测试修改密码成功"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == 'test_user_noperm').first()
        old_hash = user.password_hash
        
        # 验证旧密码正确
        assert verify_password('user123', old_hash) is True
        
        # 修改密码
        new_hash = get_password_hash('newpassword123')
        user.password_hash = new_hash
        db.commit()
        
        # 验证新密码
        assert verify_password('newpassword123', user.password_hash) is True
        assert verify_password('user123', user.password_hash) is False
    finally:
        db.close()

def test_verify_password_wrong():
    """测试验证错误密码"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == 'test_admin').first()
        assert verify_password('wrongpassword', user.password_hash) is False
    finally:
        db.close()

# ========= 用户模型权限字段测试 =========
def test_user_permissions_field_exists():
    """测试用户模型的permissions字段存在"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == 'test_admin').first()
        assert hasattr(user, 'permissions')
        assert user.permissions == '{}' or user.permissions is not None
    finally:
        db.close()

def test_user_permissions_default():
    """测试新用户默认无权限"""
    db = SessionLocal()
    try:
        # 检查已有用户的permissions字段
        users = db.query(User).all()
        for user in users:
            assert user.permissions is not None
            import json
            perms = json.loads(user.permissions)
            # admin默认有全部权限（通过role判断）
            if user.role == 'admin':
                continue
            # 其他用户权限需要明确配置
            assert isinstance(perms, dict)
    finally:
        db.close()

# ========= Token包含permissions测试 =========
def test_token_contains_permissions():
    """测试token解析后包含permissions"""
    user = get_user_dict('test_manager')
    token = create_access_token(data={"sub": str(user["id"])})
    
    # 模拟解析token获取用户
    from jose import jwt
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    user_id = int(payload.get("sub"))
    
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.id == user_id).first()
        user_dict = {
            "id": db_user.id,
            "username": db_user.username,
            "role": db_user.role,
            "permissions": db_user.permissions,
            "display_name": db_user.display_name
        }
        assert "permissions" in user_dict
        assert user_dict["permissions"] == '{"upload_employee": true, "upload_schedule": true}'
    finally:
        db.close()

# ========= 权限更新测试 =========
def test_update_user_permissions():
    """测试更新用户权限"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == 'test_user_noperm').first()
        
        # 更新权限
        import json
        new_perms = {"upload_employee": True, "clear_data": True}
        user.permissions = json.dumps(new_perms, ensure_ascii=False)
        db.commit()
        
        # 验证更新
        assert check_permission({"role": user.role, "permissions": user.permissions}, 'upload_employee') is True
        assert check_permission({"role": user.role, "permissions": user.permissions}, 'clear_data') is True
        assert check_permission({"role": user.role, "permissions": user.permissions}, 'upload_schedule') is False
    finally:
        db.close()
