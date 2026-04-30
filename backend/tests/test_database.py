import os
import sys
import tempfile

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 设置测试用的数据库URL
temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
temp_db.close()
os.environ['DATABASE_URL'] = f'sqlite:///{temp_db.name}'

from app.models.database import Base, engine, SessionLocal, init_db
from app.models.user import User


def setup_module():
    Base.metadata.drop_all(bind=engine)


def teardown_module():
    os.unlink(temp_db.name)


def test_init_db_creates_tables():
    init_db()
    db = SessionLocal()
    try:
        # 检查 users 表是否存在且有数据
        user_count = db.query(User).count()
        assert user_count >= 1
    finally:
        db.close()


def test_init_db_creates_admin():
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        assert admin is not None
        assert admin.role == "admin"
        assert admin.is_active == True
    finally:
        db.close()


def test_init_db_not_duplicate_admin():
    # 再次调用 init_db，不应该创建重复的 admin
    init_db()
    db = SessionLocal()
    try:
        admin_count = db.query(User).filter(User.username == "admin").count()
        assert admin_count == 1
    finally:
        db.close()
