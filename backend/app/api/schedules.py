from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import date, datetime
from collections import defaultdict
import zipfile
import io
import re
import logging
import pandas as pd
from xml.etree import ElementTree as ET

from app.models.database import get_db
from app.models.schedule import Schedule
from app.models.employee import Employee
from app.models.shift_type import ShiftType
from app.models.checkin import Checkin
from app.schemas.schedule import (
    ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleListResponse,
    BatchScheduleRequest, SwapScheduleRequest
)
from app.core.security import get_current_user, require_permission
from app.utils.logger import log_operation
from app.services.attendance import save_daily_report

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedules", tags=["排班管理"])


def _parse_xlsx_cell_text(cell, ns) -> str:
    """Extract text from an openpyxl-style XML cell, handling inline strings and numeric."""
    t = cell.get('t', '')
    v_el = cell.find('s:v', ns)
    v = v_el.text if v_el is not None else ''
    if t == 'inlineStr':
        t_el = cell.find('.//s:t', ns)
        return t_el.text if t_el is not None else ''
    return v


def _parse_attendance_report_xlsx(content: bytes) -> list[dict]:
    """Parse a 排班出勤情况 xlsx file using raw XML (bypasses openpyxl type bugs)."""
    ns = {'s': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
    rows_out = []
    with zipfile.ZipFile(io.BytesIO(content), 'r') as z:
        for name in z.namelist():
            if not name.startswith('xl/worksheets/') or not name.endswith('.xml'):
                continue
            xml_content = z.read(name)
            root = ET.fromstring(xml_content)
            sheet_rows = root.findall('.//s:row', ns)
            for row_el in sheet_rows[1:]:  # skip header row
                cells = row_el.findall('s:c', ns)
                rd = {}
                for cell in cells:
                    ref = cell.get('r')
                    col = ''.join(c for c in ref if c.isalpha())
                    rd[col] = _parse_xlsx_cell_text(cell, ns)

                date_val = rd.get('A', '')
                shift_name = rd.get('F', '')
                if not date_val or not shift_name:
                    continue

                time_range = rd.get('G', '') or '00:00~00:00'
                time_parts = time_range.split('~')
                time_start = time_parts[0].strip() if len(time_parts) > 0 else ''
                time_end = time_parts[1].strip() if len(time_parts) > 1 else ''

                def _num(val, default=0):
                    try:
                        return float(str(val).rstrip('%'))
                    except (ValueError, TypeError):
                        return default

                rows_out.append({
                    'date': date_val,
                    'dept': rd.get('B', ''),
                    'team': rd.get('C', ''),
                    'name': rd.get('D', ''),
                    'emp_no': rd.get('E', ''),
                    'shift_name': shift_name,
                    'time_start': time_start,
                    'time_end': time_end,
                    'work_hours': _num(rd.get('M')),
                    'punctuality_rate': _num(rd.get('O')),
                    'call_duration': _num(rd.get('P')),
                    'organize_duration': _num(rd.get('Q')),
                    'utilization_rate': _num(rd.get('R')),
                    'attendance_rate': _num(rd.get('S')),
                })
    return rows_out

def parse_shift_from_cell(cell_value: str) -> Optional[dict]:
    if pd.isna(cell_value) or not cell_value:
        return None
    cell = str(cell_value).strip()
    if '休息' in cell:
        return None
    name_match = re.match(r'^（?([^（\d]+)', cell)
    if not name_match:
        return None
    shift_name = name_match.group(1).strip()
    if not shift_name:
        return None
    cell_normalized = cell.replace('：', ':').replace('（', '(').replace('）', ')')
    time_pattern = r'(\d{1,2}:\d{2})[-—](\d{1,2}:\d{2})'
    times = re.findall(time_pattern, cell_normalized)
    if not times:
        return None
    # 去重：去除备注中重复的时间段（如 "（下午14:30-18:00到南分学习）"）
    seen = set()
    unique_times = []
    for t in times:
        key = (t[0], t[1])
        if key not in seen:
            seen.add(key)
            unique_times.append(t)
    hours_match = re.search(r'[（(](\d+\.?\d*)\s*H?\s*[)）]', cell)
    work_hours = float(hours_match.group(1)) if hours_match else 8.0
    is_night = '晚' in shift_name
    return {
        "name": shift_name,
        "work_hours": work_hours,
        "is_night": is_night,
        "time_segments": [{"start": t[0], "end": t[1]} for t in unique_times]
    }

def get_or_create_shift(db: Session, shift_info: dict) -> Optional[ShiftType]:
    shift = db.query(ShiftType).filter(ShiftType.shift_name == shift_info["name"]).first()
    if shift:
        return shift
    shift = ShiftType(
        shift_name=shift_info["name"],
        time_segments=shift_info.get("time_segments", [{"start": "08:00", "end": "18:00"}]),
        work_hours=shift_info.get("work_hours", 8.0),
        color="#409EFF" if not shift_info.get("is_night") else "#909399",
        is_night=shift_info.get("is_night", False)
    )
    db.add(shift)
    db.flush()
    return shift

def normalize_team(team: str) -> str:
    team_mapping = {
        '一班1组': '一班1组', '一班一组': '一班1组', '一班Ⅰ组': '一班1组', '一班①组': '一班1组',
        '一班2组': '一班2组', '一班二组': '一班2组', '一班Ⅱ组': '一班2组', '一班②组': '一班2组',
        '一班3组': '一班3组', '一班三组': '一班3组', '一班Ⅲ组': '一班3组', '一班③组': '一班3组',
        '二班1组': '二班1组', '二班一组': '二班1组', '二班Ⅰ组': '二班1组', '二班①组': '二班1组',
        '二班2组': '二班2组', '二班二组': '二班2组', '二班Ⅱ组': '二班2组', '二班②组': '二班2组',
        '二班3组': '二班3组', '二班三组': '二班3组', '二班Ⅲ组': '二班3组', '二班③组': '二班3组',
    }
    for key, value in team_mapping.items():
        if key in team:
            return value
    return team

def extract_team_role(col_a_value: str) -> tuple:
    col_a = str(col_a_value).strip() if col_a_value else ""
    team = None
    for t in ["一班1组", "一班2组", "一班3组", "二班1组", "二班2组", "二班3组"]:
        if t in col_a:
            team = t
            break
    if not team:
        team = col_a
    team = normalize_team(team)
    if "组长" in col_a:
        role = "组长"
    elif "师傅" in col_a:
        role = "师傅"
    else:
        role = "组员"
    return team, role

def is_valid_employee_name(name: str) -> bool:
    name = str(name).strip()
    if not name:
        return False
    if name in ['日期', '序号', '班组', '姓名', '工号']:
        return False
    if re.match(r'^\d{1,2}:\d{2}-\d{1,2}:\d{2}$', name):
        return False
    if re.match(r'^\d+$', name):
        return False
    if name.startswith('TEMP_') and re.match(r'^\d{1,2}:\d{2}-\d{1,2}:\d{2}$', name.replace('TEMP_', '')):
        return False
    return True

def parse_shift_from_header(header_value) -> Optional[dict]:
    if pd.isna(header_value) or not header_value:
        return None
    header = str(header_value).strip()
    if '休息' in header:
        return None
    name_match = re.match(r'^（?([^（\d]+)', header)
    if not name_match:
        return None
    shift_name = name_match.group(1).strip()
    if not shift_name:
        return None
    header_normalized = header.replace('：', ':').replace('（', '(').replace('）', ')')
    time_pattern = r'(\d{1,2}:\d{2})[-—](\d{1,2}:\d{2})'
    times = re.findall(time_pattern, header_normalized)
    if not times:
        return None
    seen = set()
    unique_times = []
    for t in times:
        key = (t[0], t[1])
        if key not in seen:
            seen.add(key)
            unique_times.append(t)
    hours_match = re.search(r'[（(](\d+\.?\d*)\s*H?\s*[)）]', header)
    work_hours = float(hours_match.group(1)) if hours_match else 8.0
    is_night = '晚' in shift_name
    shift_info = {
        "name": shift_name,
        "work_hours": work_hours,
        "is_night": is_night,
        "time_segments": [{"start": t[0], "end": t[1]} for t in unique_times]
    }
    return shift_info

def _format_shift_time(time_segments: list) -> str:
    if not time_segments:
        return ""
    parts = []
    for seg in time_segments:
        start = seg.get("start", "")
        end = seg.get("end", "")
        if start and end:
            parts.append(f"{start}-{end}")
    return ", ".join(parts)


@router.get("", response_model=ScheduleListResponse)
def get_schedules(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    schedule_date: Optional[date] = None,
    emp_id: Optional[int] = None,
    team: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    shift_type_id: Optional[int] = None,
    schedule_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Schedule).join(Employee)
    if schedule_date:
        query = query.filter(Schedule.schedule_date == schedule_date)
    if emp_id:
        query = query.filter(Schedule.emp_id == emp_id)
    if team:
        query = query.filter(Employee.team == team)
    if name:
        query = query.filter(Employee.name.ilike(f"%{name}%"))
    if emp_no:
        query = query.filter(Employee.emp_no.ilike(f"%{emp_no}%"))
    if shift_type_id:
        query = query.filter(Schedule.shift_type_id == shift_type_id)
    if schedule_type:
        query = query.filter(Schedule.schedule_type == schedule_type)
    
    total = query.count()
    items = query.order_by(Schedule.schedule_date.desc(), Employee.name).offset((page-1)*limit).limit(limit).all()
    
    result_items = []
    for s in items:
        emp = db.query(Employee).filter(Employee.id == s.emp_id).first()
        shift = db.query(ShiftType).filter(ShiftType.id == s.shift_type_id).first() if s.shift_type_id else None
        shift_name = s.shift_name or (shift.shift_name if shift else None)
        time_segments = s.time_segments or (shift.time_segments if shift else [])
        work_hours = float(s.work_hours) if s.work_hours is not None else (float(shift.work_hours) if shift else None)
        result_items.append({
            "id": s.id,
            "emp_id": s.emp_id,
            "schedule_date": s.schedule_date,
            "shift_type_id": s.shift_type_id,
            "schedule_type": s.schedule_type,
            "notes": s.notes,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "name": emp.name if emp else None,
            "emp_no": emp.emp_no if emp else None,
            "team": emp.team if emp else None,
            "shift_name": shift_name,
            "shift_time": _format_shift_time(time_segments),
            "time_segments": time_segments,
            "work_hours": work_hours,
            "punctuality_rate": float(s.punctuality_rate) if s.punctuality_rate is not None else None,
            "call_duration": float(s.call_duration) if s.call_duration is not None else None,
            "organize_duration": float(s.organize_duration) if s.organize_duration is not None else None,
            "utilization_rate": float(s.utilization_rate) if s.utilization_rate is not None else None,
            "attendance_rate": float(s.attendance_rate) if s.attendance_rate is not None else None,
        })
    return ScheduleListResponse(items=result_items, total=total)

@router.post("", response_model=dict)
def create_schedule(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "schedules.create")
    existing = db.query(Schedule).filter(
        and_(
            Schedule.emp_id == schedule.emp_id,
            Schedule.schedule_date == schedule.schedule_date
        )
    ).first()
    if existing:
        for key, value in schedule.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return {"id": existing.id}
    db_schedule = Schedule(**schedule.model_dump(), created_by=current_user["id"])
    db.add(db_schedule)
    db.commit()
    db.refresh(db_schedule)
    log_operation(db, current_user["id"], "create_schedule", "schedules", db_schedule.id, {"emp_id": schedule.emp_id, "schedule_date": str(schedule.schedule_date)})
    save_daily_report(db, schedule.emp_id, schedule.schedule_date)
    return {"id": db_schedule.id}

@router.put("/{schedule_id}", response_model=dict)
def update_schedule(
    schedule_id: int,
    schedule: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "schedules.edit")
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="排班记录不存在")
    for key, value in schedule.model_dump(exclude_unset=True).items():
        setattr(db_schedule, key, value)
    db.commit()
    save_daily_report(db, db_schedule.emp_id, db_schedule.schedule_date)
    return {"id": db_schedule.id}

@router.delete("/{schedule_id}", response_model=dict)
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "schedules.delete")
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="排班记录不存在")
    emp_id = db_schedule.emp_id
    schedule_date = db_schedule.schedule_date
    db.delete(db_schedule)
    db.commit()
    save_daily_report(db, emp_id, schedule_date)
    log_operation(db, current_user["id"], "delete_schedule", "schedules", schedule_id)
    return {"message": "删除成功"}

@router.post("/batch", response_model=dict)
def batch_schedule(
    request: BatchScheduleRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "schedules.create")
    success_count = 0
    for emp_id in request.emp_ids:
        existing = db.query(Schedule).filter(
            and_(
                Schedule.emp_id == emp_id,
                Schedule.schedule_date == request.schedule_date
            )
        ).first()
        if existing:
            existing.shift_type_id = request.shift_type_id
        else:
            db_schedule = Schedule(
                emp_id=emp_id,
                schedule_date=request.schedule_date,
                shift_type_id=request.shift_type_id,
                created_by=current_user["id"]
            )
            db.add(db_schedule)
        success_count += 1
    db.commit()
    for emp_id in request.emp_ids:
        save_daily_report(db, emp_id, request.schedule_date)
    return {"success_count": success_count}

@router.post("/swap", response_model=dict)
def swap_schedule(
    request: SwapScheduleRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "schedules.edit")
    schedule_a = db.query(Schedule).filter(Schedule.id == request.schedule_a_id).first()
    schedule_b = db.query(Schedule).filter(Schedule.id == request.schedule_b_id).first()
    if not schedule_a or not schedule_b:
        raise HTTPException(status_code=404, detail="排班记录不存在")
    if schedule_a.schedule_date != schedule_b.schedule_date:
        raise HTTPException(status_code=400, detail="只能交换同一天的班次")
    temp_shift = schedule_a.shift_type_id
    schedule_a.shift_type_id = schedule_b.shift_type_id
    schedule_b.shift_type_id = temp_shift
    schedule_a.schedule_type = "换班"
    schedule_b.schedule_type = "换班"
    db.commit()
    save_daily_report(db, schedule_a.emp_id, schedule_a.schedule_date)
    save_daily_report(db, schedule_b.emp_id, schedule_b.schedule_date)
    log_operation(db, current_user["id"], "swap_schedule", "schedules", None, {"schedule_a_id": request.schedule_a_id, "schedule_b_id": request.schedule_b_id})
    return {"message": "换班成功"}

@router.delete("/batch", response_model=dict)
def batch_delete_schedules(
    ids: list[int] = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "schedules.delete")
    if not ids:
        raise HTTPException(status_code=400, detail="请选择要删除的排班记录")
    schedules = db.query(Schedule).filter(Schedule.id.in_(ids)).all()
    if not schedules:
        raise HTTPException(status_code=404, detail="未找到排班记录")
    affected = set()
    for s in schedules:
        affected.add((s.emp_id, s.schedule_date))
        db.delete(s)
    db.commit()
    for emp_id, schedule_date in affected:
        save_daily_report(db, emp_id, schedule_date)
    log_operation(db, current_user["id"], "batch_delete_schedules", "schedules", None, {"ids": ids, "count": len(schedules)})
    return {"message": f"批量删除成功，共删除{len(schedules)}条", "count": len(schedules)}

@router.post("/import-attendance-report", response_model=dict)
def import_attendance_report(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """从考勤出勤报表(.xlsx)导入排班数据，替换已有排班"""
    require_permission(current_user, "schedules.upload")

    contents = file.file.read()
    logger.info(f"收到考勤报表文件，大小: {len(contents)}")

    if not contents:
        raise HTTPException(status_code=400, detail="文件为空")

    try:
        rows = _parse_attendance_report_xlsx(contents)
    except Exception as e:
        logger.error(f"考勤报表解析失败: {e}")
        raise HTTPException(status_code=400, detail=f"文件解析失败: {str(e)}")

    if not rows:
        raise HTTPException(status_code=400, detail="未解析到有效数据")

    groups = defaultdict(list)
    for r in rows:
        key = (r['emp_no'], r['date'])
        groups[key].append(r)

    covered_dates = {r['date'] for r in rows}
    date_objs = set()
    for d in covered_dates:
        try:
            date_objs.add(datetime.strptime(d, '%Y-%m-%d').date())
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效日期格式: {d}")

    # Delete existing schedules for covered dates
    deleted = db.query(Schedule).filter(Schedule.schedule_date.in_(date_objs)).delete(synchronize_session=False)
    db.commit()
    if deleted:
        logger.info(f"已清理 {deleted} 条旧排班记录")

    created_employees = 0
    created_schedules = 0
    created_shifts = 0

    for (emp_no, schedule_date_str), segments in groups.items():
        try:
            schedule_date = datetime.strptime(schedule_date_str, '%Y-%m-%d').date()
        except ValueError:
            continue

        first_seg = segments[0]
        shift_name = first_seg['shift_name']

        if shift_name == '离职':
            continue

        emp = db.query(Employee).filter(Employee.emp_no == emp_no).first()
        if not emp:
            emp = db.query(Employee).filter(Employee.name == first_seg['name']).first()
        if not emp:
            emp = Employee(
                emp_no=emp_no,
                name=first_seg['name'],
                team=first_seg['team'],
                dept=first_seg['dept'] or '客服中心',
                role='组员',
                status='在职',
                created_by=current_user["id"]
            )
            db.add(emp)
            db.flush()
            created_employees += 1

        time_segments = []
        total_work_hours = 0.0
        total_call = 0.0
        total_organize = 0.0
        weighted_punctuality = 0.0
        weighted_utilization = 0.0
        weighted_attendance = 0.0

        for seg in segments:
            seg_hours = seg['work_hours']
            seg_entry = {
                "start": seg['time_start'],
                "end": seg['time_end'],
                "work_hours": seg_hours,
                "punctuality_rate": seg['punctuality_rate'],
                "call_duration": seg['call_duration'],
                "organize_duration": seg['organize_duration'],
                "utilization_rate": seg['utilization_rate'],
                "attendance_rate": seg['attendance_rate'],
            }
            time_segments.append(seg_entry)
            total_work_hours += seg_hours
            total_call += seg['call_duration']
            total_organize += seg['organize_duration']
            weighted_punctuality += seg['punctuality_rate'] * seg_hours
            weighted_utilization += seg['utilization_rate'] * seg_hours
            weighted_attendance += seg['attendance_rate'] * seg_hours

        if total_work_hours > 0:
            overall_punctuality = round(weighted_punctuality / total_work_hours, 2)
            overall_utilization = round(weighted_utilization / total_work_hours, 2)
            overall_attendance = round(weighted_attendance / total_work_hours, 2)
        else:
            overall_punctuality = 0.0
            overall_utilization = 0.0
            overall_attendance = 0.0

        is_night = '晚' in shift_name
        is_rest = (shift_name == '休息')
        schedule_type = '休息' if is_rest else '正常'

        shift_type_id = None
        if not is_rest:
            shift_info = {
                "name": shift_name,
                "time_segments": [{"start": s['time_start'], "end": s['time_end']} for s in segments],
                "work_hours": total_work_hours,
                "is_night": is_night,
            }
            shift = get_or_create_shift(db, shift_info)
            if shift:
                created_shifts += 1
                shift_type_id = shift.id

        schedule = Schedule(
            emp_id=emp.id,
            schedule_date=schedule_date,
            shift_type_id=shift_type_id,
            shift_name=shift_name,
            time_segments=time_segments,
            work_hours=total_work_hours,
            is_night=is_night,
            schedule_type=schedule_type,
            punctuality_rate=overall_punctuality,
            call_duration=total_call,
            organize_duration=total_organize,
            utilization_rate=overall_utilization,
            attendance_rate=overall_attendance,
            created_by=current_user["id"],
        )
        db.add(schedule)
        created_schedules += 1

    db.commit()

    # Trigger attendance recalculation for covered dates
    for d in date_objs:
        emp_ids = db.query(Schedule.emp_id).filter(Schedule.schedule_date == d).distinct().all()
        for (eid,) in emp_ids:
            save_daily_report(db, eid, d)

    return {
        "message": "导入成功",
        "employees": created_employees,
        "schedules": created_schedules,
        "shift_types": created_shifts,
    }