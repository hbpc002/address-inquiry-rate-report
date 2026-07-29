"""测试培训记录API和签入签出报表的系统遵时率计算"""
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
from app.models.training_record import TrainingRecord
from app.models.role import Role
from app.models.user import User
from app.core.security import get_password_hash


_tables_created = False


def ensure_tables():
    global _tables_created
    if not _tables_created:
        Base.metadata.create_all(bind=engine)
        _tables_created = True


def clear_tables(db):
    db.query(TrainingRecord).delete()
    db.query(WorkHourThreshold).delete()
    db.query(DailyReport).delete()
    db.query(Checkin).delete()
    db.query(Schedule).delete()
    db.query(ShiftType).delete()
    db.query(Employee).delete()
    db.query(User).delete()
    db.query(Role).delete()
    db.commit()


def setup_test_data(db):
    ensure_tables()
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
                attendance_rate=100.00,
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
    return emp1, emp2, admin


def test_training_record_create_and_query():
    """测试培训记录的创建和查询"""
    ensure_tables()
    db = SessionLocal()
    try:
        clear_tables(db)
        emp1, emp2, admin = setup_test_data(db)
        today = datetime.now().date()

        records = [
            TrainingRecord(emp_no='E001', record_date=today, start_time='09:00', end_time='10:30', duration_minutes=90, type='培训', reason='产品培训', created_by='Admin'),
            TrainingRecord(emp_no='E001', record_date=today, start_time='14:00', end_time='15:00', duration_minutes=60, type='培训', reason='技能培训', created_by='Admin'),
            TrainingRecord(emp_no='E002', record_date=today, start_time='09:00', end_time='10:00', duration_minutes=60, type='请假', reason='个人事务', created_by='Admin'),
        ]
        db.add_all(records)
        db.commit()

        all_records = db.query(TrainingRecord).all()
        assert len(all_records) == 3

        e001_records = db.query(TrainingRecord).filter(TrainingRecord.emp_no == 'E001').all()
        assert len(e001_records) == 2

        training_records = db.query(TrainingRecord).filter(TrainingRecord.type == '培训').all()
        assert len(training_records) == 2

        leave_records = db.query(TrainingRecord).filter(TrainingRecord.type == '请假').all()
        assert len(leave_records) == 1

        for r in all_records:
            assert r.duration_minutes > 0
            assert r.start_time < r.end_time
            assert r.emp_no in ['E001', 'E002']
            assert r.reason is not None
    finally:
        db.close()


def test_training_record_duration_auto():
    """测试培训时长自动计算正确性"""
    ensure_tables()
    db = SessionLocal()
    try:
        clear_tables(db)
        emp1, emp2, admin = setup_test_data(db)
        today = datetime.now().date()

        record = TrainingRecord(emp_no='E001', record_date=today, start_time='08:00', end_time='12:00', duration_minutes=240, type='培训', reason='test')
        db.add(record)
        db.commit()
        db.refresh(record)

        assert record.duration_minutes == 240

        record2 = TrainingRecord(emp_no='E001', record_date=today, start_time='13:00', end_time='17:30', duration_minutes=270, type='培训', reason='test2')
        db.add(record2)
        db.commit()
        db.refresh(record2)
        assert record2.duration_minutes == 270
    finally:
        db.close()


def test_training_record_delete():
    """测试培训记录删除"""
    ensure_tables()
    db = SessionLocal()
    try:
        clear_tables(db)
        emp1, emp2, admin = setup_test_data(db)
        today = datetime.now().date()

        record = TrainingRecord(emp_no='E001', record_date=today, start_time='09:00', end_time='10:00', duration_minutes=60, type='培训', reason='delete test')
        db.add(record)
        db.commit()
        db.refresh(record)
        record_id = record.id

        assert db.query(TrainingRecord).count() == 1

        db.query(TrainingRecord).filter(TrainingRecord.id == record_id).delete()
        db.commit()

        assert db.query(TrainingRecord).count() == 0
    finally:
        db.close()


def test_training_report_computed_punctuality_rate():
    """测试培训记录被正确计入系统遵时率：(实际工时 - 培训工时) / (排班工时 - 培训工时) × 100%"""
    ensure_tables()
    db = SessionLocal()
    try:
        clear_tables(db)
        emp1, emp2, admin = setup_test_data(db)
        today = datetime.now().date()

        record = TrainingRecord(emp_no='E001', record_date=today, start_time='09:00', end_time='10:30', duration_minutes=90, type='培训', reason='test', created_by='Admin')
        db.add(record)
        db.commit()

        training_stats = db.query(
            TrainingRecord.emp_no,
            func.sum(TrainingRecord.duration_minutes)
        ).filter(
            TrainingRecord.record_date >= today,
            TrainingRecord.record_date <= today
        ).group_by(TrainingRecord.emp_no).all()
        training_map = {emp_no: int(total) for emp_no, total in training_stats}

        assert 'E001' in training_map
        assert training_map['E001'] == 90

        # 验证公式: (actual_hours - training_hours) / (scheduled_hours - training_hours) * 100
        actual_hours = 7.9
        training_hours = 90 / 60.0  # 1.5
        scheduled_hours = 8.0
        computed_rate = round((actual_hours - training_hours) / (scheduled_hours - training_hours) * 100, 2)
        expected_rate = round((7.9 - 1.5) / (8.0 - 1.5) * 100, 2)
        assert computed_rate == expected_rate
        assert expected_rate < 98.50  # 扣除培训后遵时率应低于原导入值
    finally:
        db.close()


def test_training_report_multi_employee():
    """测试多人培训记录统计和系统遵时率差异"""
    ensure_tables()
    db = SessionLocal()
    try:
        clear_tables(db)
        emp1, emp2, admin = setup_test_data(db)
        today = datetime.now().date()
        yesterday = today - timedelta(days=1)

        # E001: 每天培训60分钟
        for d in [yesterday, today]:
            record = TrainingRecord(emp_no='E001', record_date=d, start_time='09:00', end_time='10:00', duration_minutes=60, type='培训', reason='daily training', created_by='Admin')
            db.add(record)

        # E002: 请半天假(240分钟)
        record2 = TrainingRecord(emp_no='E002', record_date=today, start_time='08:00', end_time='12:00', duration_minutes=240, type='请假', reason='半天假', created_by='Admin')
        db.add(record2)
        db.commit()

        # Verify E001 total training minutes
        e001_total = db.query(func.sum(TrainingRecord.duration_minutes)).filter(TrainingRecord.emp_no == 'E001').scalar()
        assert int(e001_total) == 120  # 60 * 2

        # Verify E002 total training minutes
        e002_total = db.query(func.sum(TrainingRecord.duration_minutes)).filter(TrainingRecord.emp_no == 'E002').scalar()
        assert int(e002_total) == 240

        # Verify daily breakdown for E001
        e001_daily = db.query(TrainingRecord.record_date, func.sum(TrainingRecord.duration_minutes)).filter(
            TrainingRecord.emp_no == 'E001'
        ).group_by(TrainingRecord.record_date).order_by(TrainingRecord.record_date).all()
        assert len(e001_daily) == 2
        for d, total in e001_daily:
            assert int(total) == 60
    finally:
        db.close()


def test_training_no_records_returns_zero():
    """测试没有培训记录时，培训字段返回默认值"""
    ensure_tables()
    db = SessionLocal()
    try:
        clear_tables(db)
        emp1, emp2, admin = setup_test_data(db)

        training_count = db.query(TrainingRecord).count()
        assert training_count == 0

        training_stats = db.query(
            TrainingRecord.emp_no,
            func.sum(TrainingRecord.duration_minutes)
        ).group_by(TrainingRecord.emp_no).all()
        assert len(training_stats) == 0

        training_map = {}
        emp = db.query(Employee).filter(Employee.emp_no == 'E001').first()
        training_minutes = training_map.get(emp.emp_no, 0)
        assert training_minutes == 0
    finally:
        db.close()


def test_training_record_date_filter():
    """测试培训记录的日期过滤"""
    ensure_tables()
    db = SessionLocal()
    try:
        clear_tables(db)
        emp1, emp2, admin = setup_test_data(db)
        today = datetime.now().date()

        for i in range(5):
            d = today - timedelta(days=i)
            record = TrainingRecord(emp_no='E001', record_date=d, start_time='09:00', end_time='10:00', duration_minutes=60, type='培训', reason='test', created_by='Admin')
            db.add(record)
        db.commit()

        # All 5 records
        all_records = db.query(TrainingRecord).filter(TrainingRecord.emp_no == 'E001').all()
        assert len(all_records) == 5

        # Filter by date range - last 3 days
        filtered = db.query(TrainingRecord).filter(
            TrainingRecord.emp_no == 'E001',
            TrainingRecord.record_date >= today - timedelta(days=2),
            TrainingRecord.record_date <= today
        ).all()
        assert len(filtered) == 3

        # Filter by single day
        single = db.query(TrainingRecord).filter(
            TrainingRecord.emp_no == 'E001',
            TrainingRecord.record_date == today
        ).all()
        assert len(single) == 1

        # Type filter
        training_only = db.query(TrainingRecord).filter(TrainingRecord.type == '培训').all()
        assert len(training_only) == 5

        leave_only = db.query(TrainingRecord).filter(TrainingRecord.type == '请假').all()
        assert len(leave_only) == 0
    finally:
        db.close()


def _build_simple_xlsx_training(today_str: str) -> bytes:
    """Build a training-records-format xlsx (last sheet only, simplified)."""
    import zipfile as zf
    import io as io_b

    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"

    def cell(ref, value, t=""):
        if t == "inlineStr":
            return f'<c r="{ref}" t="inlineStr"><is><t>{value}</t></is></c>'
        return f'<c r="{ref}"><v>{value}</v></c>'

    sheet_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        f'<worksheet xmlns="{ns}">'
        "<sheetData>"
        f'<row r="1">{cell("A1","工号","inlineStr")}{cell("B1","班组","inlineStr")}{cell("C1","姓名","inlineStr")}{cell("D1","培训总时长","inlineStr")}{cell("E1",today_str,"inlineStr")}</row>'
        f'<row r="2"><c r="A1"/><c r="B1"/><c r="C1"/><c r="D1"/><c r="E1" t="inlineStr"><is><t>签出时间段</t></is></c></row>'
        f'<row r="3"/>'
        f'<row r="4">{cell("A1","E001","inlineStr")}{cell("B1","一班1组","inlineStr")}{cell("C1","张三","inlineStr")}{cell("D1","")}{cell("E1","09:00-10:30","inlineStr")}</row>'
        "</sheetData>"
        "</worksheet>"
    )

    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        '</Types>'
    )

    rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        '</Relationships>'
    )

    workbook = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheets>"
        '<sheet name="sheet1" sheetId="1" r:id="rId1"/>'
        "</sheets>"
        "</workbook>"
    )

    workbook_rels = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        '</Relationships>'
    )

    buf = io_b.BytesIO()
    with zf.ZipFile(buf, "w", zf.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", rels)
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        z.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    return buf.getvalue()


def test_import_training_records_endpoint():
    """测试培训记录导入端点"""
    ensure_tables()
    from fastapi.testclient import TestClient
    from app.main import app
    from app.models.database import SessionLocal as _SessionLocal
    from app.models.employee import Employee
    from app.models.shift_type import ShiftType
    from app.core.security import get_password_hash

    # Clean up first
    db = _SessionLocal()
    db.query(TrainingRecord).delete()
    db.commit()
    db.close()

    client = TestClient(app)

    # First create the employee
    db = _SessionLocal()
    emp = db.query(Employee).filter(Employee.emp_no == "E001").first()
    if not emp:
        shift = ShiftType(shift_name="早班", time_segments=[{"start": "08:00", "end": "18:00"}], work_hours=8.0, color="#409EFF", is_active=True)
        db.add(shift)
        db.commit()
        db.refresh(shift)
        emp = Employee(emp_no="E001", name="张三", team="一班1组", dept="广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表", role="组员", status="在职", created_by=1)
        db.add(emp)
        db.commit()
        db.refresh(emp)
    db.close()

    today = datetime.now().date().strftime("%Y%m%d")
    xlsx_bytes = _build_simple_xlsx_training(today)

    from app.core.security import create_access_token, get_password_hash
    # Setup admin user
    from app.models.role import Role
    admin_role = db.query(Role).filter(Role.name == 'admin').first()
    if not admin_role:
        admin_role = Role(name='admin', permissions='{}', is_system=True)
        db.add(admin_role)
        db.commit()
        db.refresh(admin_role)
    admin_user = db.query(User).filter(User.username == 'admin').first()
    if not admin_user:
        admin_user = User(username='admin', password_hash=get_password_hash('admin'), display_name='Admin', role='admin', role_id=admin_role.id)
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
    token = create_access_token(data={"sub": str(admin_user.id)})
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/api/training-records/import",
        files={"file": ("test.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 1
    assert "成功导入 1 条培训记录" in data["message"]

    db = _SessionLocal()
    records = db.query(TrainingRecord).filter(TrainingRecord.emp_no == "E001").all()
    assert len(records) == 1
    assert records[0].duration_minutes == 90
    assert records[0].type == "培训"
    db.close()
