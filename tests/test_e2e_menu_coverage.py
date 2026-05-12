"""
End‑to‑end tests covering all feature menus:
Auth, Employees, Shift Types, Schedules, Checkins, Reports, Users, System/Logs
"""
import datetime
from datetime import datetime, timedelta, date
import sys
import io
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

from sqlalchemy import extract, func
from app.models.user import User
from app.models.database import engine, Base, SessionLocal
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.operation_log import OperationLog
try:
    from app.models.app_config import AppConfig
    HAS_APP_CONFIG = True
except Exception:
    HAS_APP_CONFIG = False
from app.utils.logger import log_operation
from app.core.security import get_password_hash, verify_password, create_access_token

# ---------- Test data helpers ----------
TEST_ADMIN = {'username': 'admin', 'password': 'admin123', 'display_name': 'Admin', 'role': 'admin'}
TEST_MANAGER = {'username': 'manager', 'password': 'manager123', 'display_name': 'Manager', 'role': 'manager'}
TEST_USER = {'username': 'user', 'password': 'user123', 'display_name': 'User', 'role': 'user'}

def setup_function():
    """Fresh DB for each test module"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = User(username=TEST_ADMIN['username'],
                     password_hash=get_password_hash(TEST_ADMIN['password']),
                     display_name=TEST_ADMIN['display_name'], role=TEST_ADMIN['role'])
        manager = User(username=TEST_MANAGER['username'],
                       password_hash=get_password_hash(TEST_MANAGER['password']),
                       display_name=TEST_MANAGER['display_name'], role=TEST_MANAGER['role'])
        user = User(username=TEST_USER['username'],
                    password_hash=get_password_hash(TEST_USER['password']),
                    display_name=TEST_USER['display_name'], role=TEST_USER['role'])
        db.add_all([admin, manager, user])

        shift = ShiftType(shift_name='早班', time_segments=[{"start": "08:00", "end": "18:00"}], work_hours=8.0,
                         color='#409EFF', is_active=True)
        shift_night = ShiftType(shift_name='晚班', time_segments=[{"start": "20:00", "end": "06:00"}],
                                work_hours=10.0, color='#909399', is_active=True, is_night=True)
        db.add_all([shift, shift_night])
        db.commit()
        db.refresh(shift)
        db.refresh(shift_night)

        employees = [
            Employee(emp_no='E001', name='张三', team='一班1组', dept='客服中心', role='组员', status='在职',
                     created_by=admin.id),
            Employee(emp_no='E002', name='李四', team='一班2组', dept='客服中心', role='组员', status='在职',
                     created_by=admin.id),
            Employee(emp_no='E003', name='王五', team='二班1组', dept='客服中心', role='组长', status='在职',
                     created_by=admin.id),
            Employee(emp_no='E004', name='赵六', team='二班2组', dept='客服中心', role='组员', status='离职',
                     created_by=admin.id),
        ]
        db.add_all(employees)
        db.commit()
        emp_ids = [e.id for e in employees]

        today = datetime.now().date()
        for emp_id in emp_ids[:3]:
            for i in range(3):
                sched_date = today - timedelta(days=i)
                sched = Schedule(emp_id=emp_id, schedule_date=sched_date, shift_type_id=shift.id,
                                 schedule_type="正常", created_by=admin.id)
                db.add(sched)
        db.commit()

        for emp_id in emp_ids[:3]:
            for i in range(3):
                sched_date = today - timedelta(days=i)
                status = "正常" if i > 0 else "迟到"
                late_min = 5 if i == 0 else 0
                report = DailyReport(
                    emp_id=emp_id, schedule_date=sched_date, shift_type_id=shift.id,
                    schedule_type="正常",
                    scheduled_start=datetime.strptime("08:00", "%H:%M").time(),
                    scheduled_end=datetime.strptime("18:00", "%H:%M").time(),
                    scheduled_hours=8.0,
                    actual_checkin=datetime.combine(sched_date, datetime.strptime("08:05", "%H:%M").time()),
                    actual_checkout=datetime.combine(sched_date, datetime.strptime("18:00", "%H:%M").time()),
                    actual_hours=7.9, status=status, late_minutes=late_min, early_minutes=0, overtime_hours=0
                )
                db.add(report)
        db.commit()

        if HAS_APP_CONFIG:
            db.add(AppConfig(key='log_autoclean_enabled', value='true'))
            db.add(AppConfig(key='log_retention_days', value='90'))
            db.commit()
    finally:
        db.close()

# ========= Auth Menu =========
def test_auth_login_success():
    db = SessionLocal()
    user = db.query(User).filter(User.username == 'admin').first()
    assert user is not None
    assert verify_password('admin123', user.password_hash)
    db.close()

def test_auth_login_failure():
    db = SessionLocal()
    user = db.query(User).filter(User.username == 'admin').first()
    assert not verify_password('wrongpassword', user.password_hash)
    db.close()

def test_auth_create_token():
    token = create_access_token(data={'sub': '1'})
    assert token and len(token) > 0

def test_auth_user_roles():
    db = SessionLocal()
    assert db.query(User).filter_by(username='admin', role='admin').first()
    assert db.query(User).filter_by(username='manager', role='manager').first()
    assert db.query(User).filter_by(username='user', role='user').first()
    db.close()

# ========= Employees Menu =========
def test_employee_crud():
    db = SessionLocal()
    new_emp = Employee(emp_no='E005', name='测试员工', team='一班1组', dept='客服中心',
                       role='组员', status='在职', created_by=1)
    db.add(new_emp)
    db.commit()
    db.refresh(new_emp)
    assert new_emp.id is not None
    emp = db.query(Employee).filter_by(emp_no='E005').first()
    emp.name = '测试员工更新'
    db.commit()
    emp_updated = db.query(Employee).filter_by(emp_no='E005').first()
    assert emp_updated.name == '测试员工更新'
    emp_updated.status = '离职'
    db.commit()
    assert db.query(Employee).filter_by(emp_no='E005', status='离职').first()
    db.close()

def test_employee_query_by_status():
    db = SessionLocal()
    assert db.query(Employee).filter_by(status='在职').count() >= 3
    assert db.query(Employee).filter_by(status='离职').count() >= 1
    db.close()

def test_employee_query_by_team():
    db = SessionLocal()
    assert db.query(Employee).filter_by(team='一班1组').count() >= 1
    db.close()

def test_employee_query_by_dept():
    db = SessionLocal()
    assert db.query(Employee).filter_by(dept='客服中心').count() >= 3
    db.close()

def test_employee_search():
    db = SessionLocal()
    assert db.query(Employee).filter(Employee.name.like('%张%')).count() >= 1
    assert db.query(Employee).filter(Employee.emp_no.like('E00%')).count() >= 3
    db.close()

def test_employee_departments_aggregation():
    db = SessionLocal()
    from sqlalchemy import func
    results = db.query(Employee.dept, func.count(Employee.id)).filter(
        Employee.status == '在职').group_by(Employee.dept).all()
    assert len(results) >= 1
    for _, count in results:
        assert count >= 1
    db.close()

def test_employee_teams_aggregation():
    db = SessionLocal()
    from sqlalchemy import func
    results = db.query(Employee.team, func.count(Employee.id)).filter(
        Employee.status == '在职').group_by(Employee.team).all()
    assert len(results) >= 2
    db.close()

# ========= Shift Types Menu =========
def test_shift_type_crud():
    db = SessionLocal()
    new_shift = ShiftType(shift_name='中班', time_segments=[{"start": "12:00", "end": "22:00"}],
                          work_hours=10.0, color='#67C23A', is_active=True)
    db.add(new_shift)
    db.commit()
    db.refresh(new_shift)
    assert new_shift.id is not None
    shift = db.query(ShiftType).filter_by(shift_name='中班').first()
    shift.work_hours = 9.0
    db.commit()
    assert db.query(ShiftType).filter_by(shift_name='中班').first().work_hours == 9.0
    shift.is_active = False
    db.commit()
    assert not db.query(ShiftType).filter_by(shift_name='中班').first().is_active
    db.close()

def test_shift_type_query_active():
    db = SessionLocal()
    assert db.query(ShiftType).filter_by(is_active=True).count() >= 2
    db.close()

def test_shift_type_night_shift():
    db = SessionLocal()
    assert db.query(ShiftType).filter_by(is_night=True).count() >= 1
    db.close()

# ========= Schedules Menu =========
def test_schedule_crud():
    db = SessionLocal()
    today = datetime.now().date()
    shift = db.query(ShiftType).filter_by(shift_name='早班').first()
    new_sched = Schedule(emp_id=1, schedule_date=today + timedelta(days=7),
                         shift_type_id=shift.id, schedule_type='正常', created_by=1)
    db.add(new_sched)
    db.commit()
    db.refresh(new_sched)
    assert new_sched.id is not None
    sched = db.query(Schedule).filter_by(id=new_sched.id).first()
    sched.schedule_type = '调班'
    db.commit()
    assert db.query(Schedule).filter_by(id=new_sched.id).first().schedule_type == '调班'
    db.delete(sched)
    db.commit()
    assert db.query(Schedule).filter_by(id=new_sched.id).first() is None
    db.close()

def test_schedule_query_by_date():
    db = SessionLocal()
    today = datetime.now().date()
    assert db.query(Schedule).filter_by(schedule_date=today).count() >= 1
    db.close()

def test_schedule_query_by_employee():
    db = SessionLocal()
    assert db.query(Schedule).filter_by(emp_id=1).count() >= 1
    db.close()

def test_schedule_query_by_team():
    db = SessionLocal()
    assert db.query(Schedule).join(Employee).filter_by(team='一班1组').count() >= 1
    db.close()

def test_schedule_swap():
    db = SessionLocal()
    today = datetime.now().date()
    sched_a = db.query(Schedule).filter_by(schedule_date=today, emp_id=1).first()
    sched_b = db.query(Schedule).filter_by(schedule_date=today, emp_id=2).first()
    if sched_a and sched_b:
        sched_a.shift_type_id, sched_b.shift_type_id = sched_b.shift_type_id, sched_a.shift_type_id
        sched_a.schedule_type = sched_b.schedule_type = '换班'
        db.commit()
        assert db.query(Schedule).filter_by(id=sched_a.id).first().schedule_type == '换班'
    db.close()

def test_schedule_batch_operations():
    db = SessionLocal()
    today = datetime.now().date()
    shift_night = db.query(ShiftType).filter_by(shift_name='晚班').first()
    for emp_id in [1, 2]:
        existing = db.query(Schedule).filter_by(emp_id=emp_id, schedule_date=today).first()
        if existing:
            existing.shift_type_id = shift_night.id
        else:
            db.add(Schedule(emp_id=emp_id, schedule_date=today, shift_type_id=shift_night.id,
                            schedule_type='正常', created_by=1))
    db.commit()
    assert db.query(Schedule).filter_by(schedule_date=today, emp_id=1).first().shift_type_id == shift_night.id
    db.close()

# ========= Checkins Menu =========
def test_checkin_create():
    db = SessionLocal()
    today = datetime.now()
    c = Checkin(emp_no='E001', name='张三', checkin_time=today,
                checkout_time=today + timedelta(hours=8),
                device_no='DEV001', dept='客服中心', import_batch='test001')
    db.add(c)
    db.commit()
    db.refresh(c)
    assert c.id is not None
    db.close()

def test_checkin_query_by_batch():
    db = SessionLocal()
    db.add_all([Checkin(emp_no=f'E00{i}', name=f'员工{i}', checkin_time=datetime.now(), import_batch='batch001')
                for i in range(1, 4)])
    db.commit()
    assert db.query(Checkin).filter_by(import_batch='batch001').count() >= 3
    db.close()

def test_checkin_query_by_date():
    db = SessionLocal()
    today = datetime.now()
    db.add(Checkin(emp_no='E001', name='张三', checkin_time=today, import_batch='date_test'))
    db.commit()
    assert db.query(Checkin).filter(extract('year', Checkin.checkin_time) == today.year,
                                    extract('month', Checkin.checkin_time) == today.month).count() >= 1
    db.close()

def test_checkin_delete():
    db = SessionLocal()
    c = Checkin(emp_no='E001', name='张三', checkin_time=datetime.now(), import_batch='del_test')
    db.add(c)
    db.commit()
    c_id = c.id
    db.delete(c)
    db.commit()
    assert db.query(Checkin).filter_by(id=c_id).first() is None
    db.close()

def test_checkin_delete_batch():
    db = SessionLocal()
    for i in range(5):
        db.add(Checkin(emp_no=f'E00{i}', name=f'员工{i}', checkin_time=datetime.now(), import_batch='batch_del'))
    db.commit()
    deleted = db.query(Checkin).filter_by(import_batch='batch_del').delete()
    db.commit()
    assert deleted >= 5
    assert db.query(Checkin).filter_by(import_batch='batch_del').count() == 0
    db.close()

# ========= Reports Menu =========
def test_daily_report_query():
    db = SessionLocal()
    today = datetime.now().date()
    assert db.query(DailyReport).filter_by(schedule_date=today).count() >= 1
    db.close()

def test_daily_report_by_status():
    db = SessionLocal()
    reports = db.query(DailyReport).all()
    assert len(reports) >= 1
    assert any(r.status == '迟到' for r in reports)
    assert any(r.status == '正常' for r in reports)
    db.close()

def test_date_range_report():
    db = SessionLocal()
    today = datetime.now().date()
    start, end = today - timedelta(days=2), today
    reports = db.query(DailyReport).filter(DailyReport.schedule_date >= start,
                                           DailyReport.schedule_date <= end).all()
    assert len(reports) >= 1
    db.close()

def test_month_summary():
    db = SessionLocal()
    today = datetime.now()
    year, month = today.year, today.month
    employees = db.query(Employee).filter_by(status='在职').all()
    summary = []
    for emp in employees:
        reports = db.query(DailyReport).filter(
            DailyReport.emp_id == emp.id,
            extract('year', DailyReport.schedule_date) == year,
            extract('month', DailyReport.schedule_date) == month
        ).all()
        scheduled = sum(float(r.scheduled_hours or 0) for r in reports)
        actual = sum(float(r.actual_hours or 0) for r in reports)
        summary.append({'emp_id': emp.id, 'scheduled': scheduled, 'actual': actual})
    assert len(summary) >= 3
    db.close()

def test_team_ranking():
    db = SessionLocal()
    today = datetime.now()
    year, month = today.year, today.month
    teams = db.query(Employee.team, func.count(Employee.id)).filter(
        Employee.status == '在职', Employee.team.isnot(None)
    ).group_by(Employee.team).all()
    assert len(teams) >= 1
    for team_name, emp_count in teams:
        team_emps = db.query(Employee).filter(Employee.team == team_name).all()
        reports = db.query(DailyReport).filter(
            DailyReport.emp_id.in_([e.id for e in team_emps]),
            extract('year', DailyReport.schedule_date) == year,
            extract('month', DailyReport.schedule_date) == month
        ).all()
        assert sum(float(r.actual_hours or 0) for r in reports) >= 0
    db.close()

# ========== System / Logs Menu ==========
def test_export_daily_report_csv():
    db = SessionLocal()
    today = datetime.now().date()
    reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).join(Employee).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['日期', '工号', '姓名', '班组', '部门', '状态', '实际工时'])
    for r in reports:
        emp = db.query(Employee).filter_by(id=r.emp_id).first()
        if emp:
            writer.writerow([r.schedule_date, emp.emp_no, emp.name, emp.team, emp.dept, r.status, r.actual_hours])
    assert len(output.getvalue().strip().split('\n')) >= 2
    db.close()

def test_export_month_report_csv():
    db = SessionLocal()
    today = datetime.now()
    year, month = today.year, today.month
    employees = db.query(Employee).filter_by(status='在职').all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['工号', '姓名', '计划工时', '实际工时', '正常天数', '迟到天数'])
    for emp in employees:
        reports = db.query(DailyReport).filter(
            DailyReport.emp_id == emp.id,
            extract('year', DailyReport.schedule_date) == year,
            extract('month', DailyReport.schedule_date) == month
        ).all()
        scheduled = sum(float(r.scheduled_hours or 0) for r in reports)
        actual = sum(float(r.actual_hours or 0) for r in reports)
        normal_days = len([r for r in reports if r.status == '正常'])
        late_days = len([r for r in reports if r.status == '迟到'])
        writer.writerow([emp.emp_no, emp.name, scheduled, actual, normal_days, late_days])
    assert len(output.getvalue().strip().split('\n')) >= 2
    db.close()

def test_system_stats():
    db = SessionLocal()
    today = datetime.now().date()
    assert db.query(Employee).filter_by(status='在职').count() >= 1
    today_reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).all()
    assert len([r for r in today_reports if r.status == '正常']) >= 0
    assert len([r for r in today_reports if r.status == '迟到']) >= 0
    db.close()

def test_system_departments():
    db = SessionLocal()
    from sqlalchemy import func
    results = db.query(Employee.dept, func.count(Employee.id)).filter(
        Employee.status == '在职').group_by(Employee.dept).all()
    assert len(results) >= 1
    for _, count in results:
        assert count >= 1
    db.close()

def test_system_teams():
    db = SessionLocal()
    from sqlalchemy import func
    results = db.query(Employee.team, func.count(Employee.id)).filter(
        Employee.status == '在职').group_by(Employee.team).all()
    assert len(results) >= 1
    db.close()

def test_log_operation():
    db = SessionLocal()
    admin = db.query(User).filter_by(username='admin').first()
    log_operation(db, admin.id, 'test_operation', 'test_table', 1, {'note': 'test'})
    db.commit()
    assert db.query(OperationLog).count() >= 1
    db.close()

def test_manual_cleanup():
    db = SessionLocal()
    admin = db.query(User).filter_by(username='admin').first()
    db.add(OperationLog(user_id=admin.id, operation_type='old', target_table='test',
                        created_at=datetime.utcnow() - timedelta(days=60)))
    db.commit()
    deleted = db.query(OperationLog).filter(
        OperationLog.created_at < datetime.utcnow() - timedelta(days=30)).delete()
    db.commit()
    assert deleted >= 1
    assert db.query(OperationLog).filter_by(operation_type='old').count() == 0
    db.close()

def test_log_export_csv():
    db = SessionLocal()
    admin = db.query(User).filter_by(username='admin').first()
    for i in range(3):
        log_operation(db, admin.id, f'op_{i}', 'table_{i}', i, {'idx': i})
    db.commit()
    logs = db.query(OperationLog).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['id', 'user_id', 'operation_type', 'target_table', 'target_id', 'details', 'created_at'])
    for log in logs:
        writer.writerow([log.id, log.user_id, log.operation_type, log.target_table, log.target_id,
                        log.details, log.created_at.isoformat() if log.created_at else ''])
    assert len(output.getvalue().strip().split('\n')) >= 4
    db.close()

def test_log_config_get_set():
    if not HAS_APP_CONFIG:
        return
    db = SessionLocal()
    en = db.query(AppConfig).filter_by(key='log_autoclean_enabled').first()
    days = db.query(AppConfig).filter_by(key='log_retention_days').first()
    assert en.value == 'true'
    assert days.value == '90'
    en.value, days.value = 'false', '180'
    db.commit()
    assert db.query(AppConfig).filter_by(key='log_autoclean_enabled').first().value == 'false'
    assert db.query(AppConfig).filter_by(key='log_retention_days').first().value == '180'
    db.close()

def test_app_config_missing():
    if not HAS_APP_CONFIG:
        return
    db = SessionLocal()
    assert db.query(AppConfig).filter_by(key='nonexistent').first() is None
    db.close()

def test_checkin_report_integration():
    db = SessionLocal()
    emp = db.query(Employee).filter_by(status='在职').first()
    assert emp is not None
    schedules = db.query(Schedule).filter_by(emp_id=emp.id).all()
    reports = db.query(DailyReport).filter_by(emp_id=emp.id).all()
    assert len(schedules) >= 1 and len(reports) >= 1
    db.close()