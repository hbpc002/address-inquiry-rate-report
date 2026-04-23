from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import date, datetime
import pandas as pd
import io
import re

from app.models.database import get_db
from app.models.schedule import Schedule
from app.models.employee import Employee
from app.models.shift_type import ShiftType
from app.models.checkin import Checkin
from app.schemas.schedule import (
    ScheduleCreate, ScheduleUpdate, ScheduleResponse, ScheduleListResponse,
    BatchScheduleRequest, SwapScheduleRequest
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/schedules", tags=["排班管理"])

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
    hours_match = re.search(r'（?(\d+\.?\d*)H', cell)
    work_hours = float(hours_match.group(1)) if hours_match else 8.0
    is_night = '晚' in shift_name
    return {
        "name": shift_name,
        "work_hours": work_hours,
        "is_night": is_night,
        "start_time": times[0][0],
        "end_time": times[0][1]
    }

def get_or_create_shift(db: Session, shift_info: dict) -> Optional[ShiftType]:
    shift = db.query(ShiftType).filter(ShiftType.shift_name == shift_info["name"]).first()
    if shift:
        shift.start_time = shift_info.get("start_time", shift.start_time)
        shift.end_time = shift_info.get("end_time", shift.end_time)
        shift.work_hours = shift_info.get("work_hours", shift.work_hours)
        shift.is_night = shift_info.get("is_night", shift.is_night)
        db.flush()
        return shift
    shift = ShiftType(
        shift_name=shift_info["name"],
        start_time=shift_info.get("start_time", "08:00"),
        end_time=shift_info.get("end_time", "18:00"),
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
    hours_match = re.search(r'（?(\d+\.?\d*)H', header)
    work_hours = float(hours_match.group(1)) if hours_match else 8.0
    is_night = '晚' in shift_name
    shift_info = {
        "name": shift_name,
        "work_hours": work_hours,
        "is_night": is_night
    }
    shift_info["start_time"] = times[0][0]
    shift_info["end_time"] = times[0][1]
    if len(times) >= 2:
        shift_info["start_time2"] = times[1][0]
        shift_info["end_time2"] = times[1][1]
    if len(times) >= 3:
        shift_info["start_time3"] = times[2][0]
        shift_info["end_time3"] = times[2][1]
    return shift_info

@router.get("", response_model=ScheduleListResponse)
def get_schedules(
    schedule_date: Optional[date] = None,
    emp_id: Optional[int] = None,
    team: Optional[str] = None,
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
    items = query.order_by(Schedule.schedule_date, Employee.name).all()
    
    result_items = []
    for s in items:
        emp = db.query(Employee).filter(Employee.id == s.emp_id).first()
        shift = db.query(ShiftType).filter(ShiftType.id == s.shift_type_id).first() if s.shift_type_id else None
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
            "shift_name": shift.shift_name if shift else None
        })
    return ScheduleListResponse(items=result_items, total=len(result_items))

@router.post("", response_model=dict)
def create_schedule(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
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
    return {"id": db_schedule.id}

@router.put("/{schedule_id}", response_model=dict)
def update_schedule(
    schedule_id: int,
    schedule: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="排班记录不存在")
    for key, value in schedule.model_dump(exclude_unset=True).items():
        setattr(db_schedule, key, value)
    db.commit()
    return {"id": db_schedule.id}

@router.delete("/{schedule_id}", response_model=dict)
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    db_schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if not db_schedule:
        raise HTTPException(status_code=404, detail="排班记录不存在")
    db.delete(db_schedule)
    db.commit()
    return {"message": "删除成功"}

@router.post("/batch", response_model=dict)
def batch_schedule(
    request: BatchScheduleRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
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
    return {"success_count": success_count}

@router.post("/swap", response_model=dict)
def swap_schedule(
    request: SwapScheduleRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
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
    return {"message": "换班成功"}

@router.post("/import", response_model=dict)
def import_schedule_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """从排班Excel导入员工和排班（支持多个sheet：组长、组员、新人）"""
    contents = file.file.read()
    try:
        xlsx = pd.ExcelFile(io.BytesIO(contents))
        sheet_names = xlsx.sheet_names
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法解析Excel文件: {str(e)}")

    emp_map = {}
    existing_employees = db.query(Employee).all()
    for e in existing_employees:
        emp_map[e.emp_no] = {"name": e.name, "emp_id": e.id}

    created_employees = 0
    created_schedules = 0
    created_shifts = 0
    skipped_no_match = 0

    for sheet_name in sheet_names:
        skip = False
        for kw in ['工时', '人员分组', '人员']:
            if kw in sheet_name:
                skip = True
                break
        if skip:
            continue
        if '组长' not in sheet_name and '组员' not in sheet_name and '新人' not in sheet_name:
            continue

        df = pd.read_excel(xlsx, sheet_name=sheet_name)
        cols = df.columns.tolist()

        shift_definitions = {}
        for col in cols:
            if pd.isna(col):
                continue
            col_str = str(col)
            try:
                if int(col_str):
                    continue
            except (ValueError, TypeError):
                pass
            if '休息' in col_str:
                continue
            shift_info = parse_shift_from_header(col_str)
            if shift_info and shift_info["name"]:
                shift_definitions[shift_info["name"]] = shift_info

        for idx, row in df.iterrows():
            if idx == 0:
                continue
            col_a = row.get('日期') or row.get('班组')
            col_b = row.get('Unnamed: 1') or row.get('姓名')
            if pd.isna(col_a) or pd.isna(col_b):
                continue
            col_a = str(col_a).strip()
            col_b = str(col_b).strip()
            if not is_valid_employee_name(col_b):
                continue
            team, role = extract_team_role(col_a)

            matched_emp_id = None
            for emp_no, info in emp_map.items():
                if info["name"] == col_b:
                    matched_emp_id = info["emp_id"]
                    break

            if not matched_emp_id:
                emp = Employee(
                    emp_no=f"TEMP_{col_b}",
                    name=col_b,
                    team=team,
                    dept='客服中心',
                    role=role,
                    status='在职',
                    created_by=current_user["id"]
                )
                db.add(emp)
                db.flush()
                emp_map[f"TEMP_{col_b}"] = {"name": col_b, "emp_id": emp.id}
                created_employees += 1
                matched_emp_id = emp.id

            emp = db.query(Employee).filter(Employee.id == matched_emp_id).first()

            for col in cols:
                if pd.isna(col):
                    continue
                try:
                    col_int = int(col)
                except (ValueError, TypeError):
                    continue
                if col_int < 20200000:
                    continue
                try:
                    schedule_date = datetime.strptime(str(col_int), '%Y%m%d').date()
                except:
                    continue
                shift_name = row.get(col_int)
                if pd.isna(shift_name):
                    continue
                shift_name = str(shift_name).strip()
                if shift_name == '休息' or not shift_name:
                    continue
                shift_info = None
                for name, info in shift_definitions.items():
                    if name in shift_name or shift_name in name:
                        shift_info = info
                        break
                if not shift_info:
                    shift_info = parse_shift_from_cell(shift_name)
                if not shift_info:
                    continue
                shift = get_or_create_shift(db, shift_info)
                if shift:
                    created_shifts += 1
                if not shift:
                    continue
                existing = db.query(Schedule).filter(
                    and_(
                        Schedule.emp_id == emp.id,
                        Schedule.schedule_date == schedule_date
                    )
                ).first()
                if not existing:
                    schedule = Schedule(
                        emp_id=emp.id,
                        schedule_date=schedule_date,
                        shift_type_id=shift.id,
                        schedule_type='正常',
                        created_by=current_user["id"]
                    )
                    db.add(schedule)
                    created_schedules += 1

    db.commit()
    return {
        "message": "导入成功",
        "employees": created_employees,
        "schedules": created_schedules,
        "shift_types": created_shifts,
        "skipped": skipped_no_match
    }