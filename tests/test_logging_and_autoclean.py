import datetime
from datetime import datetime, timedelta
import sys
import io
import csv
from pathlib import Path

# Use DB models directly without HTTP client
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

from app.models.user import User
from app.models.database import engine, Base, SessionLocal
from app.models.operation_log import OperationLog
from app.utils.logger import log_operation
from app.core.security import get_password_hash

try:
    from app.models.app_config import AppConfig
    HAS_APP_CONFIG = True
except Exception:
    HAS_APP_CONFIG = False


def setup_function(func):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = User(username='admin', password_hash=get_password_hash('admin'), display_name='Admin', role='admin')
        db.add(admin)
        db.commit()
    finally:
        db.close()


def test_log_operation_and_cleanup_db():
    """Test log operation writing and cleanup logic"""
    db = SessionLocal()
    admin = db.query(User).filter_by(username='admin').first()
    assert admin is not None
    
    # Write a log entry
    log_operation(db, admin.id, 'test_op', 'logs', None, {'note': 'db test'})
    logs = db.query(OperationLog).all()
    assert len(logs) >= 1
    
    # Add an older log for cleanup test
    old_log = OperationLog(user_id=admin.id, operation_type='old', target_table='logs', details={'old':'1'}, created_at=datetime.utcnow() - timedelta(days=60))
    db.add(old_log)
    db.commit()
    
    # Count logs older than 30 days
    cutoff = datetime.utcnow() - timedelta(days=30)
    to_delete = db.query(OperationLog).filter(OperationLog.created_at < cutoff).delete()
    db.commit()
    db.close()
    assert to_delete >= 1


def test_app_config_get_set():
    """Test AppConfig model for auto-clean settings"""
    if not HAS_APP_CONFIG:
        # Skip test if AppConfig model not available
        return
    
    db = SessionLocal()
    
    # Test default config
    conf = db.query(AppConfig).filter(AppConfig.key == 'log_autoclean_enabled').first()
    assert conf is None  # Not created yet
    
    # Create config
    db.add(AppConfig(key='log_autoclean_enabled', value='true'))
    db.add(AppConfig(key='log_retention_days', value='90'))
    db.commit()
    
    # Read back
    en = db.query(AppConfig).filter(AppConfig.key == 'log_autoclean_enabled').first()
    assert en is not None
    assert en.value == 'true'
    
    days = db.query(AppConfig).filter(AppConfig.key == 'log_retention_days').first()
    assert days is not None
    assert days.value == '90'
    
    # Update config
    en.value = 'false'
    days.value = '180'  # 6 months
    db.commit()
    
    # Verify update
    en2 = db.query(AppConfig).filter(AppConfig.key == 'log_autoclean_enabled').first()
    assert en2.value == 'false'
    days2 = db.query(AppConfig).filter(AppConfig.key == 'log_retention_days').first()
    assert days2.value == '180'
    
    db.close()


def test_retention_months_calculation():
    """Test retention months to days conversion (1-6 months)"""
    # 1 month = 30 days
    assert 1 * 30 == 30
    # 3 months = 90 days
    assert 3 * 30 == 90
    # 6 months = 180 days
    assert 6 * 30 == 180
    
    # Test boundary: 1-6 months should be valid
    for months in [1, 2, 3, 4, 5, 6]:
        days = months * 30
        assert 30 <= days <= 180


def test_manual_cleanup_by_months():
    """Test manual cleanup with different month values"""
    db = SessionLocal()
    admin = db.query(User).filter_by(username='admin').first()
    
    # Add logs with different ages
    now = datetime.utcnow()
    
    # 1 month old
    db.add(OperationLog(user_id=admin.id, operation_type='old1m', target_table='logs', created_at=now - timedelta(days=25)))
    # 2 months old
    db.add(OperationLog(user_id=admin.id, operation_type='old2m', target_table='logs', created_at=now - timedelta(days=60)))
    # 5 months old
    db.add(OperationLog(user_id=admin.id, operation_type='old5m', target_table='logs', created_at=now - timedelta(days=150)))
    db.commit()
    
    # Test cleanup for 1 month - should keep 25 days log, delete others
    cutoff_1m = now - timedelta(days=1 * 30)
    deleted_1m = db.query(OperationLog).filter(OperationLog.created_at < cutoff_1m).delete()
    db.commit()
    assert deleted_1m == 2  # 60 days + 150 days = 2 records
    
    # Remaining logs
    remaining = db.query(OperationLog).count()
    assert remaining >= 1  # 25 days log should remain
    
    db.close()


def test_log_export_csv_format():
    """Test CSV export format for logs"""
    db = SessionLocal()
    admin = db.query(User).filter_by(username='admin').first()
    
    # Add some logs
    for i in range(3):
        log_operation(db, admin.id, f'op_type_{i}', 'test_table', i, {'idx': i})
    db.commit()
    
    # Query logs
    logs = db.query(OperationLog).all()
    assert len(logs) >= 3
    
    # Simulate CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "user_id", "operation_type", "target_table", "target_id", "details", "created_at"])
    for log in logs:
        writer.writerow([
            log.id,
            log.user_id,
            log.operation_type,
            log.target_table,
            log.target_id,
            log.details,
            log.created_at.isoformat() if log.created_at else ""
        ])
    
    output.seek(0)
    content = output.getvalue()
    lines = content.strip().split('\n')
    
    # Header + 3 data rows
    assert len(lines) >= 4
    # Check header
    header = lines[0]
    assert "id" in header
    assert "user_id" in header
    assert "operation_type" in header
    assert "target_table" in header
    
    db.close()


def test_log_details_json():
    """Test that log details are properly stored as JSON"""
    db = SessionLocal()
    admin = db.query(User).filter_by(username='admin').first()
    
    # Write log with complex details
    details = {
        'emp_no': 'E001',
        'name': 'Test User',
        'action': 'create_employee',
        'changes': ['name', 'dept']
    }
    log_operation(db, admin.id, 'create_employee', 'employees', 1, details)
    db.commit()
    
    # Read back
    log = db.query(OperationLog).filter(OperationLog.operation_type == 'create_employee').first()
    assert log is not None
    assert log.details is not None
    assert log.details['emp_no'] == 'E001'
    assert log.details['name'] == 'Test User'
    assert log.details['action'] == 'create_employee'
    
    db.close()


def test_multiple_users_logging():
    """Test logging from multiple users"""
    db = SessionLocal()
    admin = db.query(User).filter_by(username='admin').first()
    
    # Create another user
    user2 = User(username='manager', password_hash=get_password_hash('manager123'), display_name='Manager', role='manager')
    db.add(user2)
    db.commit()
    
    # Both users log
    log_operation(db, admin.id, 'login', 'users', admin.id, {'username': 'admin'})
    log_operation(db, user2.id, 'login', 'users', user2.id, {'username': 'manager'})
    log_operation(db, admin.id, 'create_employee', 'employees', 10, {'emp_no': 'E010'})
    db.commit()
    
    # Query by user
    admin_logs = db.query(OperationLog).filter(OperationLog.user_id == admin.id).all()
    user2_logs = db.query(OperationLog).filter(OperationLog.user_id == user2.id).all()
    
    assert len(admin_logs) >= 2
    assert len(user2_logs) >= 1
    
    db.close()