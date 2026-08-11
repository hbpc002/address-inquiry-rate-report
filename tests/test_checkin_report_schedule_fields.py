"""测试签入签出报表新增的5个Schedule字段"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

from sqlalchemy import func
from app.models.database import SessionLocal, engine, Base
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.models.checkin import Checkin
from app.models.daily_report import DailyReport
from app.models.work_hour_threshold import WorkHourThreshold
from app.models.role import Role
from app.models.user import User
from app.core.security import get_password_hash


def clear_tables(db):
    from app.models.operation_log import OperationLog
    db.query(OperationLog).delete()
    db.query(WorkHourThreshold).delete()
    db.query(DailyReport).delete()
    db.query(Checkin).delete()
    db.query(Schedule).delete()
    db.query(ShiftType).delete()
    db.query(Employee).delete()
    db.query(User).delete()
    db.query(Role).delete()
    db.commit()


def setup_employees_and_schedules(db):
    """Create test data: admin user, shift type, employees, schedules with 5 new fields, checkins, daily reports"""
    now = datetime.now()
    today = now.date()
    
    admin = User(username='admin', password_hash=get_password_hash('admin'), display_name='Admin', role='admin')
    db.add(admin)
    db.commit()
    db.refresh(admin)

    shift = ShiftType(shift_name='早班', time_segments=[{"start": "08:00", "end": "18:00"}], work_hours=8.0, color='#409EFF', is_active=True)
    db.add(shift)
    db.commit()
    db.refresh(shift)

    emp1 = Employee(emp_no='E001', name='张三', team='一班1组', dept='广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表', role='组员', status='在职', created_by=admin.id)
    emp2 = Employee(emp_no='E002', name='李四', team='一班1组', dept='广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表', role='组员', status='在职', created_by=admin.id)
    db.add_all([emp1, emp2])
    db.commit()
    db.refresh(emp1)
    db.refresh(emp2)

    for emp in [emp1, emp2]:
        for i in range(3):
            d = today - timedelta(days=i)
            sched = Schedule(
                emp_id=emp.id,
                schedule_date=d,
                shift_type_id=shift.id,
                schedule_type='正常',
                work_hours=8.0,
                punctuality_rate=98.50 if emp == emp1 else 95.00,
                call_duration=5.0 if emp == emp1 else 4.0,
                organize_duration=1.5 if emp == emp1 else 2.0,
                utilization_rate=81.25 if emp == emp1 else 75.00,
                attendance_rate=100.00 if emp == emp1 else 100.00,
                created_by=admin.id
            )
            db.add(sched)

            report = DailyReport(
                emp_id=emp.id,
                schedule_date=d,
                shift_type_id=shift.id,
                schedule_type='正常',
                scheduled_start=datetime.strptime('08:00', '%H:%M').time(),
                scheduled_end=datetime.strptime('18:00', '%H:%M').time(),
                scheduled_hours=8.0,
                actual_checkin=datetime.combine(d, datetime.strptime('08:05', '%H:%M').time()),
                actual_checkout=datetime.combine(d, datetime.strptime('18:00', '%H:%M').time()),
                actual_hours=7.9,
                status='正常',
                late_minutes=5 if i == 0 else 0,
                early_minutes=0,
                overtime_hours=0
            )
            db.add(report)

            for hour in range(9, 18):
                checkin = Checkin(
                    emp_no=emp.emp_no,
                    name=emp.name,
                    dept=emp.dept,
                    checkin_time=datetime.combine(d, datetime.strptime(f'{hour}:00', '%H:%M').time()),
                    checkout_time=datetime.combine(d, datetime.strptime(f'{hour + 1}:00', '%H:%M').time()),
                    device_no='DEV001',
                    import_batch='test-batch'
                )
                db.add(checkin)

    db.commit()


def test_personal_report_daily_stats_has_schedule_fields():
    """验证个人签到报表 daily_stats 包含5个新增字段"""
    db = SessionLocal()
    try:
        clear_tables(db)
        setup_employees_and_schedules(db)

        emp = db.query(Employee).filter(Employee.emp_no == 'E001').first()
        start = (datetime.now().date() - timedelta(days=2))
        end = datetime.now().date()

        schedules = db.query(Schedule).filter(
            Schedule.emp_id == emp.id,
            Schedule.schedule_date >= start,
            Schedule.schedule_date <= end
        ).order_by(Schedule.schedule_date).all()

        assert len(schedules) >= 2

        for s in schedules:
            assert s.punctuality_rate is not None
            assert s.call_duration is not None
            assert s.organize_duration is not None
            assert s.utilization_rate is not None
            assert s.attendance_rate is not None

        schedule_map = {s.schedule_date: s for s in schedules}

        daily_reports = db.query(DailyReport).filter(
            DailyReport.emp_id == emp.id,
            DailyReport.schedule_date >= start,
            DailyReport.schedule_date <= end
        ).all()

        for r in daily_reports:
            sched = schedule_map.get(r.schedule_date)
            assert sched is not None
            assert float(sched.punctuality_rate) == 98.50
            assert float(sched.call_duration) == 5.0
            assert float(sched.organize_duration) == 1.5
            assert float(sched.utilization_rate) == 81.25
            assert float(sched.attendance_rate) == 100.00

        total_call = sum(float(s.call_duration) for s in schedules)
        total_organize = sum(float(s.organize_duration) for s in schedules)
        assert total_call == 5.0 * len(schedules)
        assert total_organize == 1.5 * len(schedules)
    finally:
        db.close()


def test_personal_report_schedule_fields_vary_per_employee():
    """验证不同员工的Schedule字段值不同"""
    db = SessionLocal()
    try:
        clear_tables(db)
        setup_employees_and_schedules(db)

        emp1 = db.query(Employee).filter(Employee.emp_no == 'E001').first()
        emp2 = db.query(Employee).filter(Employee.emp_no == 'E002').first()
        start = (datetime.now().date() - timedelta(days=2))
        end = datetime.now().date()

        schedules_e001 = db.query(Schedule).filter(
            Schedule.emp_id == emp1.id,
            Schedule.schedule_date >= start,
            Schedule.schedule_date <= end
        ).all()

        schedules_e002 = db.query(Schedule).filter(
            Schedule.emp_id == emp2.id,
            Schedule.schedule_date >= start,
            Schedule.schedule_date <= end
        ).all()

        assert len(schedules_e001) >= 2
        assert len(schedules_e002) >= 2

        for s in schedules_e001:
            assert float(s.punctuality_rate) == 98.50
            assert float(s.call_duration) == 5.0
            assert float(s.organize_duration) == 1.5
            assert float(s.utilization_rate) == 81.25

        for s in schedules_e002:
            assert float(s.punctuality_rate) == 95.00
            assert float(s.call_duration) == 4.0
            assert float(s.organize_duration) == 2.0
            assert float(s.utilization_rate) == 75.00

        assert schedules_e001[0].punctuality_rate != schedules_e002[0].punctuality_rate
    finally:
        db.close()


def test_report_aggregation_schedule_fields():
    """验证签入签出报表聚合查询正确计算Schedule字段的AVG/SUM"""
    db = SessionLocal()
    try:
        clear_tables(db)
        setup_employees_and_schedules(db)

        start = (datetime.now().date() - timedelta(days=2))
        end = datetime.now().date()

        schedule_stats = db.query(
            Employee.emp_no,
            func.avg(Schedule.punctuality_rate),
            func.sum(Schedule.call_duration),
            func.sum(Schedule.organize_duration),
            func.avg(Schedule.utilization_rate),
            func.avg(Schedule.attendance_rate)
        ).join(Employee, Schedule.emp_id == Employee.id).filter(
            Schedule.schedule_date >= start,
            Schedule.schedule_date <= end
        ).group_by(Employee.emp_no).order_by(Employee.emp_no).all()

        assert len(schedule_stats) == 2

        e001_row = schedule_stats[0]
        assert e001_row[0] == 'E001'
        assert float(e001_row[1]) == 98.50  # avg punctuality
        assert float(e001_row[2]) == 5.0 * (sum(1 for _ in range(3)))   # sum call_duration
        assert float(e001_row[3]) == 1.5 * (sum(1 for _ in range(3)))   # sum organize_duration
        assert float(e001_row[4]) == 81.25  # avg utilization
        assert float(e001_row[5]) == 100.00  # avg attendance

        e002_row = schedule_stats[1]
        assert e002_row[0] == 'E002'
        assert float(e002_row[1]) == 95.00
        assert float(e002_row[4]) == 75.00
    finally:
        db.close()


def test_report_schedule_fields_null_when_no_schedule():
    """验证没有Schedule数据的员工，新字段返回None"""
    db = SessionLocal()
    try:
        clear_tables(db)

        admin = User(username='admin', password_hash=get_password_hash('admin'), display_name='Admin', role='admin')
        db.add(admin)
        db.commit()
        db.refresh(admin)

        shift = ShiftType(shift_name='早班', time_segments=[{"start": "08:00", "end": "18:00"}], work_hours=8.0, color='#409EFF', is_active=True)
        db.add(shift)
        db.commit()
        db.refresh(shift)

        emp = Employee(emp_no='E003', name='王五', team='一班1组', dept='广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表', role='组员', status='在职', created_by=admin.id)
        db.add(emp)
        db.commit()
        db.refresh(emp)

        today = datetime.now().date()
        sched = Schedule(
            emp_id=emp.id,
            schedule_date=today,
            shift_type_id=shift.id,
            schedule_type='正常',
            work_hours=8.0,
            created_by=admin.id
        )
        db.add(sched)
        db.commit()

        schedules = db.query(Schedule).filter(Schedule.emp_id == emp.id).all()
        for s in schedules:
            assert s.punctuality_rate is None
            assert s.call_duration is None
            assert s.organize_duration is None
            assert s.utilization_rate is None
            assert s.attendance_rate is None

        schedule_stats = db.query(
            Employee.emp_no,
            func.avg(Schedule.punctuality_rate),
            func.sum(Schedule.call_duration),
        ).join(Employee, Schedule.emp_id == Employee.id).filter(
            Schedule.schedule_date == today
        ).group_by(Employee.emp_no).all()

        assert len(schedule_stats) == 1
        assert schedule_stats[0][1] is None
        assert schedule_stats[0][2] is None
    finally:
        db.close()


def test_personal_report_no_checkins_still_shows_schedule():
    """验证即使没有签入记录，Schedule字段也能从数据库查询到"""
    db = SessionLocal()
    try:
        clear_tables(db)

        admin = User(username='admin', password_hash=get_password_hash('admin'), display_name='Admin', role='admin')
        db.add(admin)
        db.commit()
        db.refresh(admin)

        shift = ShiftType(shift_name='早班', time_segments=[{"start": "08:00", "end": "18:00"}], work_hours=8.0, color='#409EFF', is_active=True)
        db.add(shift)
        db.commit()
        db.refresh(shift)

        emp = Employee(emp_no='E004', name='赵六', team='一班1组', dept='广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表', role='组员', status='在职', created_by=admin.id)
        db.add(emp)
        db.commit()
        db.refresh(emp)

        today = datetime.now().date()
        sched = Schedule(
            emp_id=emp.id,
            schedule_date=today,
            shift_type_id=shift.id,
            schedule_type='正常',
            work_hours=8.0,
            punctuality_rate=99.00,
            call_duration=6.0,
            organize_duration=1.0,
            utilization_rate=87.50,
            attendance_rate=100.00,
            created_by=admin.id
        )
        db.add(sched)
        db.commit()

        schedules = db.query(Schedule).filter(
            Schedule.emp_id == emp.id,
            Schedule.schedule_date == today
        ).all()

        assert len(schedules) == 1
        s = schedules[0]
        assert float(s.punctuality_rate) == 99.00
        assert float(s.call_duration) == 6.0
        assert float(s.organize_duration) == 1.0
        assert float(s.utilization_rate) == 87.50
        assert float(s.attendance_rate) == 100.00
    finally:
        db.close()
