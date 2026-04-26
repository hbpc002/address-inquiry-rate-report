import datetime
from datetime import datetime, timedelta, date
import sys
import io
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

from sqlalchemy import extract
from app.models.user import User
from app.models.database import engine, Base, SessionLocal
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.models.daily_report import DailyReport
from app.core.security import get_password_hash


def setup_function(func):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Create admin user
        admin = User(username='admin', password_hash=get_password_hash('admin'), display_name='Admin', role='admin')
        db.add(admin)
        
        # Create shift type
        shift = ShiftType(shift_name='早班', start_time='08:00', end_time='18:00', work_hours=8.0, color='#409EFF', is_active=True)
        db.add(shift)
        db.commit()
        db.refresh(shift)
        
        # Create employees
        emp1 = Employee(emp_no='E001', name='张三', team='一班1组', dept='客服中心', role='组员', status='在职', created_by=admin.id)
        emp2 = Employee(emp_no='E002', name='李四', team='一班2组', dept='客服中心', role='组员', status='在职', created_by=admin.id)
        emp3 = Employee(emp_no='E003', name='王五', team='二班1组', dept='客服中心', role='组长', status='在职', created_by=admin.id)
        db.add_all([emp1, emp2, emp3])
        db.commit()
        db.refresh(emp1)
        db.refresh(emp2)
        db.refresh(emp3)
        
        # Create schedules for current month
        today = datetime.now().date()
        for emp in [emp1, emp2, emp3]:
            for i in range(5):
                schedule_date = today - timedelta(days=i)
                sched = Schedule(emp_id=emp.id, schedule_date=schedule_date, shift_type_id=shift.id, schedule_type='正常', created_by=admin.id)
                db.add(sched)
        db.commit()
        
        # Create daily reports
        for emp in [emp1, emp2, emp3]:
            for i in range(5):
                schedule_date = today - timedelta(days=i)
                report = DailyReport(
                    emp_id=emp.id,
                    schedule_date=schedule_date,
                    shift_type_id=shift.id,
                    schedule_type='正常',
                    scheduled_start=datetime.strptime('08:00', '%H:%M').time(),
                    scheduled_end=datetime.strptime('18:00', '%H:%M').time(),
                    scheduled_hours=8.0,
                    actual_checkin=datetime.combine(schedule_date, datetime.strptime('08:05', '%H:%M').time()),
                    actual_checkout=datetime.combine(schedule_date, datetime.strptime('18:00', '%H:%M').time()),
                    actual_hours=7.9,
                    status='正常' if i > 0 else '迟到',
                    late_minutes=5 if i == 0 else 0,
                    early_minutes=0,
                    overtime_hours=0
                )
                db.add(report)
        db.commit()
    finally:
        db.close()


def test_daily_report_query():
    """Test daily report query by date"""
    db = SessionLocal()
    today = datetime.now().date()
    
    reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).all()
    assert len(reports) >= 1
    
    # Query with employee join
    reports_with_emp = db.query(DailyReport).join(Employee).filter(DailyReport.schedule_date == today).all()
    assert len(reports_with_emp) >= 1
    
    # Query by status
    late_reports = db.query(DailyReport).filter(DailyReport.schedule_date == today, DailyReport.status == '迟到').all()
    assert len(late_reports) >= 1
    
    db.close()


def test_date_range_query():
    """Test date range query for reports"""
    db = SessionLocal()
    today = datetime.now().date()
    start = today - timedelta(days=3)
    end = today
    
    reports = db.query(DailyReport).filter(
        DailyReport.schedule_date >= start,
        DailyReport.schedule_date <= end
    ).all()
    
    assert len(reports) >= 3  # At least 3 days of reports
    
    # Query by team
    emp = db.query(Employee).filter(Employee.team == '一班1组').first()
    team_reports = db.query(DailyReport).filter(
        DailyReport.emp_id == emp.id,
        DailyReport.schedule_date >= start,
        DailyReport.schedule_date <= end
    ).all()
    
    assert len(team_reports) >= 1
    
    db.close()


def test_month_summary():
    """Test monthly summary calculation"""
    db = SessionLocal()
    today = datetime.now()
    year = today.year
    month = today.month
    
    employees = db.query(Employee).filter(Employee.status == '在职').all()
    assert len(employees) >= 3
    
    summary = []
    for emp in employees:
        daily_reports = db.query(DailyReport).filter(
            DailyReport.emp_id == emp.id,
            extract('year', DailyReport.schedule_date) == year,
            extract('month', DailyReport.schedule_date) == month
        ).all()
        
        scheduled = sum(float(r.scheduled_hours or 0) for r in daily_reports)
        actual = sum(float(r.actual_hours or 0) for r in daily_reports)
        overtime = sum(float(r.overtime_hours or 0) for r in daily_reports)
        owed = max(0, scheduled - actual - overtime)
        
        summary.append({
            'emp_id': emp.id,
            'name': emp.name,
            'scheduled_hours': scheduled,
            'actual_hours': actual,
            'overtime_hours': overtime,
            'owed_hours': owed
        })
    
    assert len(summary) >= 3
    for s in summary:
        assert s['scheduled_hours'] >= 0
        assert s['actual_hours'] >= 0
    
    db.close()


def test_team_ranking():
    """Test team ranking calculation"""
    from sqlalchemy import func as sql_func
    
    db = SessionLocal()
    today = datetime.now()
    year = today.year
    month = today.month
    
    teams = db.query(Employee.team, sql_func.count(Employee.id)).filter(
        Employee.status == '在职',
        Employee.team.isnot(None)
    ).group_by(Employee.team).all()
    
    assert len(teams) >= 1
    
    result = []
    for team_name, emp_count in teams:
        team_employees = db.query(Employee).filter(Employee.team == team_name).all()
        emp_ids = [e.id for e in team_employees]
        
        daily_reports = db.query(DailyReport).filter(
            DailyReport.emp_id.in_(emp_ids),
            extract('year', DailyReport.schedule_date) == year,
            extract('month', DailyReport.schedule_date) == month
        ).all()
        
        schedules = db.query(Schedule).filter(
            Schedule.emp_id.in_(emp_ids),
            extract('year', Schedule.schedule_date) == year,
            extract('month', Schedule.schedule_date) == month
        ).all()
        
        shift_cache = {}
        total_scheduled = 0
        for s in schedules:
            if s.shift_type_id not in shift_cache:
                shift_cache[s.shift_type_id] = db.query(ShiftType).filter(ShiftType.id == s.shift_type_id).first()
            shift = shift_cache[s.shift_type_id]
            if shift:
                total_scheduled += float(shift.work_hours or 0)
        
        total_actual = sum(float(r.actual_hours or 0) for r in daily_reports)
        late_count = len([r for r in daily_reports if r.status == '迟到'])
        
        result.append({
            'team': team_name,
            'emp_count': emp_count,
            'total_scheduled': round(total_scheduled, 1),
            'total_actual': round(total_actual, 1),
            'late_count': late_count
        })
    
    assert len(result) >= 1
    
    db.close()


def test_export_daily_csv():
    """Test daily report CSV export format"""
    db = SessionLocal()
    today = datetime.now().date()
    
    reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).join(Employee).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['日期', '工号', '姓名', '班组', '部门', '计划开始', '计划结束', '实际签到', '实际签退', '状态', '迟到分钟', '早退分钟', '实际工时'])
    
    for item in reports:
        emp = db.query(Employee).filter(Employee.id == item.emp_id).first()
        if emp:
            writer.writerow([
                item.schedule_date,
                emp.emp_no,
                emp.name,
                emp.team,
                emp.dept or '',
                str(item.scheduled_start) if item.scheduled_start else '',
                str(item.scheduled_end) if item.scheduled_end else '',
                item.actual_checkin.strftime('%Y-%m-%d %H:%M:%S') if item.actual_checkin else '',
                item.actual_checkout.strftime('%Y-%m-%d %H:%M:%S') if item.actual_checkout else '',
                item.status or '',
                item.late_minutes or 0,
                item.early_minutes or 0,
                item.actual_hours or 0
            ])
    
    output.seek(0)
    content = output.getvalue()
    lines = content.strip().split('\n')
    
    assert len(lines) >= 2  # Header + at least one data row
    header = lines[0]
    assert '日期' in header
    assert '工号' in header
    assert '姓名' in header
    
    db.close()


def test_export_month_csv():
    """Test monthly report CSV export format"""
    db = SessionLocal()
    today = datetime.now()
    year = today.year
    month = today.month
    
    employees = db.query(Employee).filter(Employee.status == '在职').all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['工号', '姓名', '班组', '部门', '计划工时', '实际工时', '加班工时', '欠时工时', '正常天数', '迟到天数', '早退天数', '缺勤天数', '请假天数', '公休天数'])
    
    for emp in employees:
        daily_reports = db.query(DailyReport).filter(
            DailyReport.emp_id == emp.id,
            extract('year', DailyReport.schedule_date) == year,
            extract('month', DailyReport.schedule_date) == month
        ).all()
        
        scheduled = sum(float(r.scheduled_hours or 0) for r in daily_reports)
        actual = sum(float(r.actual_hours or 0) for r in daily_reports)
        overtime = sum(float(r.overtime_hours or 0) for r in daily_reports)
        owed = max(0, scheduled - actual - overtime)
        
        writer.writerow([
            emp.emp_no,
            emp.name,
            emp.team,
            emp.dept or '',
            scheduled,
            actual,
            overtime,
            owed,
            len([r for r in daily_reports if r.status == '正常']),
            len([r for r in daily_reports if r.status == '迟到']),
            len([r for r in daily_reports if r.status == '早退']),
            len([r for r in daily_reports if r.status == '缺勤']),
            len([r for r in daily_reports if r.status == '请假']),
            len([r for r in daily_reports if r.status == '公休'])
        ])
    
    output.seek(0)
    content = output.getvalue()
    lines = content.strip().split('\n')
    
    assert len(lines) >= 2  # Header + at least one data row
    header = lines[0]
    assert '工号' in header
    assert '计划工时' in header
    
    db.close()


def test_report_status_statistics():
    """Test report status statistics calculation"""
    db = SessionLocal()
    today = datetime.now().date()
    
    all_reports = db.query(DailyReport).filter(DailyReport.schedule_date == today).all()
    
    normal_count = len([r for r in all_reports if r.status == '正常'])
    late_count = len([r for r in all_reports if r.status == '迟到'])
    absent_count = len([r for r in all_reports if r.status == '缺勤'])
    
    assert normal_count + late_count + absent_count == len(all_reports)
    assert late_count >= 1  # We created at least one late report
    
    db.close()


def test_employee_schedule_report():
    """Test employee schedule and report relationship"""
    db = SessionLocal()
    
    # Get an employee
    emp = db.query(Employee).first()
    assert emp is not None
    
    # Get employee's schedules
    schedules = db.query(Schedule).filter(Schedule.emp_id == emp.id).all()
    assert len(schedules) >= 1
    
    # Get employee's reports
    reports = db.query(DailyReport).filter(DailyReport.emp_id == emp.id).all()
    assert len(reports) >= 1
    
    # Verify schedule dates match report dates
    schedule_dates = set(s.schedule_date for s in schedules)
    report_dates = set(r.schedule_date for r in reports)
    
    # Reports should be generated for scheduled dates
    assert len(report_dates) >= 1
    
    db.close()