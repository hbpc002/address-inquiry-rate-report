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
from app.core.security import get_current_user, require_permission, require_role
from app.utils.logger import log_operation
from app.services.attendance import save_daily_report

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
            "work_hours": work_hours
        })
    return ScheduleListResponse(items=result_items, total=total)

@router.post("", response_model=dict)
def create_schedule(
    schedule: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_role(current_user, ["admin", "manager"])
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
    require_role(current_user, ["admin", "manager"])
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
    require_role(current_user, ["admin", "manager"])
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
    require_role(current_user, ["admin", "manager"])
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
    require_role(current_user, ["admin", "manager"])
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
    require_role(current_user, ["admin", "manager"])
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

@router.post("/import", response_model=dict)
def import_schedule_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """从排班Excel导入员工和排班（支持多个sheet：组长、组员、新人）"""
    import logging
    logger = logging.getLogger(__name__)
    
    require_permission(current_user, "upload_schedule")
    
    contents = file.file.read()
    logger.info(f"收到文件，大小: {len(contents)}")
    
    if not contents:
        raise HTTPException(status_code=400, detail="文件为空")
    
    # 解析Excel
    try:
        xlsx = pd.ExcelFile(io.BytesIO(contents))
        sheet_names = xlsx.sheet_names
        logger.info(f"解析成功: {sheet_names}")
    except Exception as e:
        try:
            xlsx = pd.ExcelFile(io.BytesIO(contents), engine='openpyxl')
            sheet_names = xlsx.sheet_names
        except Exception as e2:
            logger.error(f"Excel解析失败: {e2}")
            raise HTTPException(status_code=400, detail=f"Excel解析失败: {str(e2)}")
    
    if not sheet_names:
        raise HTTPException(status_code=400, detail="Excel文件中没有sheet")
    
    # 过滤有效sheet
    valid_sheets = [sn for sn in sheet_names 
                 if not any(kw in sn for kw in ['工时', '人员分组', '人员'])
                 and any(kw in sn for kw in ['组长', '组员', '新人'])]
    
    if not valid_sheets:
        raise HTTPException(status_code=400, detail=f"未找到有效sheet，现有: {sheet_names}")
    
    # 员工映射
    emp_map = {}
    for e in db.query(Employee).all():
        emp_map[e.emp_no] = {"name": e.name, "emp_id": e.id}
    
    created_employees = 0
    created_schedules = 0
    created_shifts = 0
    skipped_no_match = 0
    
    for sheet_name in valid_sheets:
        df = pd.read_excel(xlsx, sheet_name=sheet_name)
        
        if df.empty:
            continue
            
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
                        shift_name=shift_info["name"],
                        time_segments=shift_info.get("time_segments"),
                        work_hours=shift_info.get("work_hours"),
                        is_night=shift_info.get("is_night", False),
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