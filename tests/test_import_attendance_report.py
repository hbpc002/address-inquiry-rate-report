"""测试考勤出勤报表导入"""
import sys
import io
from pathlib import Path
from datetime import date
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'backend'
sys.path.insert(0, str(BASE))

import pytest
from app.models.database import SessionLocal, engine, Base
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.shift_type import ShiftType
from app.models.daily_report import DailyReport
from app.models.monthly_report import MonthlyReport
from app.api.schedules import _parse_attendance_report_xlsx


def clear_tables(db):
    db.query(DailyReport).delete()
    db.query(MonthlyReport).delete()
    db.query(Schedule).delete()
    db.query(ShiftType).delete()
    db.query(Employee).delete()
    db.commit()


def _build_test_xlsx(rows: list[list]) -> bytes:
    """Build a minimal xlsx in the attendance-report format using raw XML."""
    ns = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    sheet_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<worksheet xmlns="{ns}">
  <sheetData>
    <row r="1">
      <c r="A1" t="inlineStr"><is><t>排班日期</t></is></c>
      <c r="B1" t="inlineStr"><is><t>区队名称</t></is></c>
      <c r="C1" t="inlineStr"><is><t>班组名称</t></is></c>
      <c r="D1" t="inlineStr"><is><t>姓名</t></is></c>
      <c r="E1" t="inlineStr"><is><t>账号</t></is></c>
      <c r="F1" t="inlineStr"><is><t>班次名称</t></is></c>
      <c r="G1" t="inlineStr"><is><t>时间范围</t></is></c>
      <c r="H1" t="inlineStr"><is><t>首次签入时间</t></is></c>
      <c r="I1" t="inlineStr"><is><t>最后签出时间</t></is></c>
      <c r="J1" t="inlineStr"><is><t>应签时间</t></is></c>
      <c r="K1" t="inlineStr"><is><t>是否准时</t></is></c>
      <c r="L1" t="inlineStr"><is><t>工作总时长</t></is></c>
      <c r="M1" t="inlineStr"><is><t>班次时长</t></is></c>
      <c r="N1" t="inlineStr"><is><t>欠时长</t></is></c>
      <c r="O1" t="inlineStr"><is><t>遵时率</t></is></c>
      <c r="P1" t="inlineStr"><is><t>通话时长(H)</t></is></c>
      <c r="Q1" t="inlineStr"><is><t>整理时长(H)</t></is></c>
      <c r="R1" t="inlineStr"><is><t>工时利用率</t></is></c>
      <c r="S1" t="inlineStr"><is><t>班表出勤率</t></is></c>
    </row>'''

    for i, row in enumerate(rows, 2):
        r = i
        cols = 'ABCDEFGHIJKLMNOPQRS'
        sheet_xml += f'    <row r="{r}">\n'
        for j, val in enumerate(row):
            col = cols[j]
            if val is None:
                sheet_xml += f'      <c r="{col}{r}"/>\n'
            elif isinstance(val, (int, float)):
                sheet_xml += f'      <c r="{col}{r}"><v>{val}</v></c>\n'
            else:
                escaped = str(val).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                sheet_xml += f'      <c r="{col}{r}" t="inlineStr"><is><t>{escaped}</t></is></c>\n'
        sheet_xml += f'    </row>\n'

    sheet_xml += '''  </sheetData>
</worksheet>'''

    buf = io.BytesIO()
    with ZipFile(buf, 'w') as z:
        z.writestr('[Content_Types].xml', '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>''')
        z.writestr('_rels/.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>''')
        z.writestr('xl/workbook.xml', '''<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets><sheet name="sheet1" sheetId="1" r:id="rId1"/></sheets>
</workbook>''')
        z.writestr('xl/_rels/workbook.xml.rels', '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>''')
        z.writestr('xl/worksheets/sheet1.xml', sheet_xml)
    return buf.getvalue()


class TestParseAttendanceXlsx:

    def test_parse_single_employee_single_segment(self):
        rows_data = [
            ['2026-06-22', '热线运营组', '一班1组', '张三', 'KF001',
             '行政9', '08:00~12:30', '', '', '08:00', '是',
             4.5, 4.5, 0.0, 100.0, 3.0, 0.5, 77.78, 100.0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        result = _parse_attendance_report_xlsx(xlsx)
        assert len(result) == 1
        r = result[0]
        assert r['date'] == '2026-06-22'
        assert r['dept'] == '热线运营组'
        assert r['team'] == '一班1组'
        assert r['name'] == '张三'
        assert r['emp_no'] == 'KF001'
        assert r['shift_name'] == '行政9'
        assert r['time_start'] == '08:00'
        assert r['time_end'] == '12:30'
        assert r['work_hours'] == 4.5
        assert r['punctuality_rate'] == 100.0
        assert r['call_duration'] == 3.0
        assert r['organize_duration'] == 0.5
        assert r['utilization_rate'] == 77.78
        assert r['attendance_rate'] == 100.0

    def test_parse_multi_segment_same_employee(self):
        rows_data = [
            ['2026-06-22', '热线运营组', '一班1组', '李四', 'KF002',
             '中班9', '08:30~13:00', '', '', '08:30', '否',
             4.0, 4.5, -0.5, 88.89, 2.0, 0.3, 57.50, 88.89],
            ['2026-06-22', '热线运营组', '一班1组', '李四', 'KF002',
             '中班9', '15:30~20:00', '', '', '15:30', '是',
             4.3, 4.5, -0.2, 95.56, 2.5, 0.4, 67.44, 95.56],
        ]
        xlsx = _build_test_xlsx(rows_data)
        result = _parse_attendance_report_xlsx(xlsx)
        assert len(result) == 2
        assert all(r['emp_no'] == 'KF002' for r in result)
        assert result[0]['time_start'] == '08:30'
        assert result[1]['time_start'] == '15:30'

    def test_parse_rest_day(self):
        rows_data = [
            ['2026-06-22', '热线运营组', '一班4组', '王五', 'KF003',
             '休息', '00:00~00:00', '', '', '-', '-',
             0, 0, 0, 0, 0, 0, 0, 0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        result = _parse_attendance_report_xlsx(xlsx)
        assert len(result) == 1
        assert result[0]['shift_name'] == '休息'
        assert result[0]['work_hours'] == 0

    def test_parse_resigned(self):
        rows_data = [
            ['2026-06-22', '热线运营组', '一班1组', '赵六', 'KF004',
             '离职', '00:00~00:00', '', '', '-', '-',
             0, 0, 0, 0, 0, 0, 0, 0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        result = _parse_attendance_report_xlsx(xlsx)
        assert len(result) == 1
        assert result[0]['shift_name'] == '离职'

    def test_percent_stripped(self):
        rows_data = [
            ['2026-06-22', '热线运营组', '一班2组', '测试员工', 'KF010',
             '晚二8.5', '12:30~17:00', '', '', '12:30', '是',
             4.5, 4.5, 0, 100, 3.0, 0.5, 77.78, '100%'],
        ]
        xlsx = _build_test_xlsx(rows_data)
        result = _parse_attendance_report_xlsx(xlsx)
        assert result[0]['attendance_rate'] == 100.0


class TestImportAttendanceReport:

    @pytest.fixture(autouse=True)
    def patch_permissions(self, monkeypatch):
        monkeypatch.setattr('app.api.schedules.require_permission', lambda user, perm: None)

    def test_import_single_employee(self, db):
        clear_tables(db)
        from app.api.schedules import import_attendance_report
        from fastapi import UploadFile

        rows_data = [
            ['2026-06-22', '热线运营组', '一班1组', '张三', 'KF001',
             '行政9', '08:00~12:30', '', '', '08:00', '是',
             4.5, 4.5, 0.0, 100.0, 3.0, 0.5, 77.78, 100.0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))

        # Mock current_user
        result = import_attendance_report(file=file, db=db, current_user={"id": 1})

        assert result["employees"] == 1  # new employee created
        assert result["schedules"] == 1
        assert result["shift_types"] == 1

        schedule = db.query(Schedule).first()
        assert schedule is not None
        assert schedule.shift_name == '行政9'
        assert float(schedule.work_hours) == 4.5
        assert float(schedule.punctuality_rate) == 100.0
        assert float(schedule.call_duration) == 3.0
        assert float(schedule.organize_duration) == 0.5
        assert float(schedule.utilization_rate) == 77.78
        assert float(schedule.attendance_rate) == 100.0

        employee = db.query(Employee).filter(Employee.emp_no == 'KF001').first()
        assert employee is not None
        assert employee.name == '张三'
        assert employee.team == '一班1组'
        assert employee.dept == '热线运营组'

    def test_import_multi_segment_aggregation(self, db):
        clear_tables(db)
        from app.api.schedules import import_attendance_report
        from fastapi import UploadFile

        rows_data = [
            ['2026-06-22', '热线运营组', '一班1组', '李四', 'KF002',
             '中班9', '08:30~13:00', '', '', '08:30', '否',
             4.0, 4.5, -0.5, 88.89, 2.0, 0.3, 57.50, 88.89],
            ['2026-06-22', '热线运营组', '一班1组', '李四', 'KF002',
             '中班9', '15:30~20:00', '', '', '15:30', '是',
             4.3, 4.5, -0.2, 95.56, 2.5, 0.4, 67.44, 95.56],
        ]
        xlsx = _build_test_xlsx(rows_data)
        file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
        result = import_attendance_report(file=file, db=db, current_user={"id": 1})

        assert result["schedules"] == 1
        assert result["employees"] == 1

        schedule = db.query(Schedule).first()
        assert schedule is not None
        # Aggregated values
        assert float(schedule.work_hours) == 9.0  # 4.5 + 4.5
        assert float(schedule.call_duration) == 4.5       # 2.0 + 2.5
        assert float(schedule.organize_duration) == 0.7   # 0.3 + 0.4
        # Weighted averages
        expected_punctuality = round((88.89 * 4.5 + 95.56 * 4.5) / 9.0, 2)
        assert float(schedule.punctuality_rate) == expected_punctuality

        # time_segments should contain 2 entries with extended fields
        assert len(schedule.time_segments) == 2
        for seg in schedule.time_segments:
            assert 'punctuality_rate' in seg
            assert 'call_duration' in seg
            assert 'organize_duration' in seg
            assert 'utilization_rate' in seg
            assert 'attendance_rate' in seg

    def test_import_rest_day(self, db):
        clear_tables(db)
        from app.api.schedules import import_attendance_report
        from fastapi import UploadFile

        # Pre-create employee
        emp = Employee(emp_no='KF003', name='王五', team='一班4组', dept='客服中心', role='组员', status='在职')
        db.add(emp)
        db.commit()

        rows_data = [
            ['2026-06-22', '热线运营组', '一班4组', '王五', 'KF003',
             '休息', '00:00~00:00', '', '', '-', '-',
             0, 0, 0, 0, 0, 0, 0, 0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
        result = import_attendance_report(file=file, db=db, current_user={"id": 1})

        assert result["schedules"] == 1
        schedule = db.query(Schedule).first()
        assert schedule.schedule_type == '公休'
        assert float(schedule.work_hours) == 0
        assert schedule.shift_name == '休息'

    def test_import_resigned_skipped(self, db):
        clear_tables(db)
        from app.api.schedules import import_attendance_report
        from fastapi import UploadFile

        rows_data = [
            ['2026-06-22', '热线运营组', '一班1组', '张忆庆', 'KF020',
             '离职', '00:00~00:00', '', '', '-', '-',
             0, 0, 0, 0, 0, 0, 0, 0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
        result = import_attendance_report(file=file, db=db, current_user={"id": 1})

        assert result["schedules"] == 0

    def test_import_replaces_existing_schedules(self, db):
        clear_tables(db)
        from app.api.schedules import import_attendance_report
        from fastapi import UploadFile

        # Create an existing schedule for 2026-06-22
        emp = Employee(emp_no='KF001', name='张三', team='一班1组', dept='客服中心', role='组员', status='在职')
        db.add(emp)
        db.flush()
        old_schedule = Schedule(
            emp_id=emp.id, schedule_date=date(2026, 6, 22),
            shift_name='旧班次', work_hours=8.0, schedule_type='正常',
            created_by=1
        )
        db.add(old_schedule)
        db.commit()

        assert db.query(Schedule).count() == 1
        old_id = old_schedule.id

        rows_data = [
            ['2026-06-22', '热线运营组', '一班1组', '张三', 'KF001',
             '行政9', '08:00~12:30', '', '', '08:00', '是',
             4.5, 4.5, 0.0, 100.0, 3.0, 0.5, 77.78, 100.0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
        result = import_attendance_report(file=file, db=db, current_user={"id": 1})

        # Old schedule should be replaced (new ID)
        all_schedules = db.query(Schedule).all()
        assert len(all_schedules) == result["schedules"]
        assert all_schedules[0].shift_name == '行政9'
        assert all_schedules[0].id != old_id

    def test_import_existing_employee_matches_by_emp_no(self, db):
        clear_tables(db)
        from app.api.schedules import import_attendance_report
        from fastapi import UploadFile

        emp = Employee(emp_no='KF100', name='赵六', team='二班1组', dept='客服中心', role='组员', status='在职')
        db.add(emp)
        db.commit()

        rows_data = [
            ['2026-06-22', '热线运营组', '二班1组', '赵六', 'KF100',
             '晚4.5H', '12:30~17:00', '', '', '12:30', '是',
             4.5, 4.5, 0.0, 100.0, 3.5, 0.2, 82.22, 100.0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
        result = import_attendance_report(file=file, db=db, current_user={"id": 1})

        assert result["employees"] == 0  # no new employee
        assert result["schedules"] == 1

        schedule = db.query(Schedule).first()
        assert schedule.emp_id == emp.id

    def test_import_existing_employee_matches_by_name(self, db):
        clear_tables(db)
        from app.api.schedules import import_attendance_report
        from fastapi import UploadFile

        emp = Employee(emp_no='OLD999', name='陈七', team='二班2组', dept='客服中心', role='组员', status='在职')
        db.add(emp)
        db.commit()

        rows_data = [
            ['2026-06-22', '热线运营组', '二班2组', '陈七', 'KF200',
             '行8.5', '08:00~12:30', '', '', '08:00', '是',
             4.5, 4.5, 0.0, 100.0, 4.0, 0.1, 91.11, 100.0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
        result = import_attendance_report(file=file, db=db, current_user={"id": 1})

        assert result["employees"] == 0
        # Emp no should not be overwritten
        emp = db.query(Employee).filter(Employee.id == emp.id).first()
        assert emp.emp_no == 'OLD999'

    def test_call_duration_and_organize_sums(self, db):
        clear_tables(db)
        from app.api.schedules import import_attendance_report
        from fastapi import UploadFile

        emp = Employee(emp_no='KF005', name='测试', team='一班1组', dept='客服中心', role='组员', status='在职')
        db.add(emp)
        db.commit()

        rows_data = [
            ['2026-06-22', '热线运营组', '一班1组', '测试', 'KF005',
             '行政9', '08:00~12:30', '', '', '08:00', '是',
             4.0, 4.5, -0.5, 80.0, 2.0, 0.3, 57.50, 80.0],
            ['2026-06-22', '热线运营组', '一班1组', '测试', 'KF005',
             '行政9', '13:30~18:00', '', '', '13:30', '是',
             4.5, 4.5, 0.0, 100.0, 3.0, 0.4, 82.22, 100.0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
        result = import_attendance_report(file=file, db=db, current_user={"id": 1})

        assert result["schedules"] == 1
        schedule = db.query(Schedule).first()
        assert float(schedule.call_duration) == 5.0       # 2.0 + 3.0
        assert float(schedule.organize_duration) == 0.7   # 0.3 + 0.4

    def test_utilization_and_attendance_weighted_average(self, db):
        clear_tables(db)
        from app.api.schedules import import_attendance_report
        from fastapi import UploadFile

        emp = Employee(emp_no='KF006', name='加权测试', team='一班1组', dept='客服中心', role='组员', status='在职')
        db.add(emp)
        db.commit()

        rows_data = [
            ['2026-06-22', '热线运营组', '一班1组', '加权测试', 'KF006',
             '晚二8.5', '12:30~17:00', '', '', '12:30', '是',
             4.5, 4.5, 0.0, 90.0, 3.0, 0.2, 71.11, 90.0],
            ['2026-06-22', '热线运营组', '一班1组', '加权测试', 'KF006',
             '晚二8.5', '18:00~22:00', '', '', '18:00', '是',
             4.0, 4.0, 0.0, 85.0, 3.5, 0.3, 82.50, 85.0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
        result = import_attendance_report(file=file, db=db, current_user={"id": 1})

        assert result["schedules"] == 1
        schedule = db.query(Schedule).first()
        total_hours = 8.5  # 4.5 + 4.0
        expected_util = round((71.11 * 4.5 + 82.50 * 4.0) / total_hours, 2)
        expected_attend = round((90.0 * 4.5 + 85.0 * 4.0) / total_hours, 2)
        assert float(schedule.utilization_rate) == expected_util
        assert float(schedule.attendance_rate) == expected_attend

    def test_import_dedup_duplicate_segments(self, db):
        clear_tables(db)
        from app.api.schedules import import_attendance_report
        from fastapi import UploadFile

        emp = Employee(emp_no='KF010', name='去重测试', team='一班2组', dept='客服中心', role='组员', status='在职')
        db.add(emp)
        db.commit()

        rows_data = [
            # 4 rows, but only 2 unique segments (12:30~17:00 and 18:30~22:00)
            ['2026-05-02', '热线运营组', '一班2组', '去重测试', 'KF010',
             '晚二', '12:30~17:00', '', '', '12:30', '是',
             4.5, 4.5, 0.0, 88.0, 3.04, 0.01, 77.1, 87.6],
            ['2026-05-02', '热线运营组', '一班2组', '去重测试', 'KF010',
             '晚二', '12:30~17:00', '', '', '12:30', '是',
             4.5, 4.5, 0.0, 88.0, 3.04, 0.01, 77.1, 87.6],
            ['2026-05-02', '热线运营组', '一班2组', '去重测试', 'KF010',
             '晚二', '18:30~22:00', '', '', '18:30', '是',
             3.5, 3.5, 0.0, 98.0, 2.80, 0.01, 82.0, 95.4],
            ['2026-05-02', '热线运营组', '一班2组', '去重测试', 'KF010',
             '晚二', '18:30~22:00', '', '', '18:30', '是',
             3.5, 3.5, 0.0, 98.0, 2.80, 0.01, 82.0, 95.4],
        ]
        xlsx = _build_test_xlsx(rows_data)
        file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
        result = import_attendance_report(file=file, db=db, current_user={"id": 1})

        assert result["schedules"] == 1
        schedule = db.query(Schedule).first()
        # Should have 2 time_segments, not 4
        assert len(schedule.time_segments) == 2, f"Expected 2 segments, got {len(schedule.time_segments)}"
        # Verify the correct segments
        starts = {seg['start'] for seg in schedule.time_segments}
        assert '12:30' in starts
        assert '18:30' in starts
        # Verify weighted aggregation (4.5 + 3.5 = 8.0)
        assert float(schedule.work_hours) == 8.0
        expected_punctuality = round((88.0 * 4.5 + 98.0 * 3.5) / 8.0, 2)
        assert float(schedule.punctuality_rate) == expected_punctuality

    def test_import_dedup_does_not_remove_different_segments(self, db):
        clear_tables(db)
        from app.api.schedules import import_attendance_report
        from fastapi import UploadFile

        emp = Employee(emp_no='KF011', name='去重测试2', team='一班1组', dept='客服中心', role='组员', status='在职')
        db.add(emp)
        db.commit()

        rows_data = [
            # 3 unique segments, no duplicates
            ['2026-06-22', '热线运营组', '一班1组', '去重测试2', 'KF011',
             '行政9', '08:00~12:30', '', '', '08:00', '是',
             4.5, 4.5, 0.0, 100.0, 3.0, 0.5, 77.78, 100.0],
            ['2026-06-22', '热线运营组', '一班1组', '去重测试2', 'KF011',
             '行政9', '13:30~18:00', '', '', '13:30', '是',
             4.5, 4.5, 0.0, 100.0, 3.0, 0.5, 77.78, 100.0],
            ['2026-06-22', '热线运营组', '一班1组', '去重测试2', 'KF011',
             '晚班', '18:30~22:00', '', '', '18:30', '是',
             3.5, 3.5, 0.0, 100.0, 2.0, 0.3, 85.71, 100.0],
        ]
        xlsx = _build_test_xlsx(rows_data)
        file = UploadFile(filename="test.xlsx", file=io.BytesIO(xlsx))
        result = import_attendance_report(file=file, db=db, current_user={"id": 1})

        assert result["schedules"] == 1
        schedule = db.query(Schedule).first()
        assert len(schedule.time_segments) == 3, f"Expected 3 segments, got {len(schedule.time_segments)}"


@pytest.fixture(autouse=True)
def db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
