import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault('DATABASE_URL', 'postgresql://postgres:admin123%40kf@localhost:5432/schedule_test')

from app.models.database import Base, engine, SessionLocal, init_db
from app.models.role import Role
from app.main import _migrate_role_permissions
from app.core.permissions import get_all_permission_keys


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    init_db()


def test_migration_adds_missing_keys_to_existing_role():
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.name == "manager").first()
        assert role is not None

        old_perms = json.loads(role.permissions)
        for key in get_all_permission_keys():
            old_perms.pop(key, None)
        role.permissions = json.dumps(old_perms, ensure_ascii=False)
        db.commit()
    finally:
        db.close()

    _migrate_role_permissions()

    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.name == "manager").first()
        updated = json.loads(role.permissions)
        all_keys = get_all_permission_keys()

        for key in all_keys:
            assert key in updated, f"Key {key} missing after migration"
            assert updated[key] is True or updated[key] is False, f"Key {key} has non-boolean value"
    finally:
        db.close()


def test_migration_does_not_change_existing_keys():
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.name == "user").first()
        assert role is not None
        old_perms = json.loads(role.permissions)
    finally:
        db.close()

    _migrate_role_permissions()

    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.name == "user").first()
        new_perms = json.loads(role.permissions)
        for key in old_perms:
            assert new_perms.get(key) == old_perms[key], f"Key {key} changed from {old_perms[key]} to {new_perms.get(key)}"
    finally:
        db.close()


def test_migration_adds_dashboard_export_to_existing_role():
    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.name == "manager").first()
        assert role is not None
        old_perms = json.loads(role.permissions)
        old_perms.pop("reports.dashboard_export", None)
        old_perms.pop("reports.efficiency_export", None)
        old_perms.pop("checkin_report.export", None)
        old_perms.pop("workload_report.export", None)
        role.permissions = json.dumps(old_perms, ensure_ascii=False)
        db.commit()
    finally:
        db.close()

    _migrate_role_permissions()

    db = SessionLocal()
    try:
        role = db.query(Role).filter(Role.name == "manager").first()
        updated = json.loads(role.permissions)
        assert "reports.dashboard_export" in updated
        assert "reports.efficiency_export" in updated
        assert "checkin_report.export" in updated
        assert "workload_report.export" in updated
        assert updated["reports.dashboard_export"] is True
        assert updated["reports.efficiency_export"] is True
        assert updated["checkin_report.export"] is True
        assert updated["workload_report.export"] is True
    finally:
        db.close()
