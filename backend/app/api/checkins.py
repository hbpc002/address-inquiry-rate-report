from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime
import csv
import io
import uuid

from app.models.database import get_db
from app.models.checkin import Checkin
from app.models.employee import Employee
from app.models.schedule import Schedule
from app.models.daily_report import DailyReport
from app.models.work_hour_threshold import WorkHourThreshold
from app.utils.logger import log_operation
from app.schemas.checkin import CheckinResponse, CheckinListResponse, ImportCheckinResponse
from app.core.security import get_current_user, require_permission
from app.services.attendance import save_daily_report

router = APIRouter(prefix="/api/checkins", tags=["签到记录"])

# 只取这个部门的数据
TARGET_DEPT = "广西分公司>>省中心>>客户服务营销中心"


@router.get("", response_model=CheckinListResponse)
def get_checkins(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    import_batch: Optional[str] = None,
    checkin_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Checkin)
    if import_batch:
        query = query.filter(Checkin.import_batch == import_batch)
    if checkin_date:
        query = query.filter(func.date(Checkin.checkin_time) == checkin_date)

    total = query.count()
    items = query.order_by(Checkin.checkin_time.desc()).offset((page-1)*limit).limit(limit).all()
    return CheckinListResponse(
        items=[CheckinResponse.model_validate(c) for c in items],
        total=total
    )


@router.post("/import", response_model=ImportCheckinResponse)
def import_checkins(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导入签到记录，只取目标部门的员工"""
    require_permission(current_user, "upload_checkin")
    
    batch = str(uuid.uuid4())[:8]
    content = file.file.read()

    try:
        content.decode('utf-8')
        encoding = 'utf-8'
    except UnicodeDecodeError:
        encoding = 'gbk'

    text = content.decode(encoding)
    reader = csv.DictReader(io.StringIO(text))
    
    count = 0
    skipped = 0
    
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV文件为空")
    
    required_fields = ['账号', '工号', '用户名', '姓名', '签入时间', '签到时间']
    has_required = any(any(f in row for f in required_fields) for row in rows[:1])
    if not has_required:
        raise HTTPException(status_code=400, detail="CSV文件格式错误：缺少必要字段")
    
    for row in rows:
        try:
            dept = row.get('所属部门全路径', '') or row.get('归属部门', '') or ''
            dept = str(dept).strip()
            
            # 检查是否在目标部门下
            if not dept.startswith(TARGET_DEPT):
                skipped += 1
                continue
            
            emp_no = row.get('账号', '') or row.get('工号', '') or ''
            name = row.get('用户名', '') or row.get('姓名', '') or ''
            checkin_time_str = row.get('签入时间', '') or row.get('签到时间', '')
            checkout_time_str = row.get('签出时间', '') or row.get('签退时间', '')
            device_no = row.get('签入分机', '') or row.get('设备号', '') or ''

            emp_no = str(emp_no).strip()
            if emp_no.startswith('='):
                emp_no = emp_no[2:-1]

            name = str(name).strip()
            checkin_time_str = str(checkin_time_str).strip()
            checkout_time_str = str(checkout_time_str).strip()
            device_no = str(device_no).strip()
            if device_no.startswith('='):
                device_no = device_no[2:-1]

            if not emp_no or not checkin_time_str:
                continue

            checkin_time = datetime.strptime(checkin_time_str, '%Y-%m-%d %H:%M:%S')
            checkout_time = None
            if checkout_time_str and checkout_time_str != 'nan':
                try:
                    checkout_time = datetime.strptime(checkout_time_str, '%Y-%m-%d %H:%M:%S')
                except:
                    pass

            existing = db.query(Checkin).filter(
                Checkin.name == name,
                Checkin.checkin_time == checkin_time
            ).first()
            if existing:
                if checkout_time and not existing.checkout_time:
                    existing.checkout_time = checkout_time
                skipped += 1
                continue

            checkin = Checkin(
                emp_no=emp_no,
                name=name,
                checkin_time=checkin_time,
                checkout_time=checkout_time,
                device_no=device_no,
                dept=dept,
                import_batch=batch
            )
            db.add(checkin)
            count += 1
        except Exception as e:
            continue

    db.commit()
    log_operation(db, current_user["id"], "import_checkins", "checkins", None, {"batch": batch, "count": count})

    checkin_names = db.query(Checkin.name).filter(Checkin.import_batch == batch).distinct().all()
    checkin_names = [n[0] for n in checkin_names]
    
    emp_with_schedule = db.query(Employee).join(Schedule).filter(
        Employee.name.in_(checkin_names)
    ).all()

    for emp in emp_with_schedule:
        schedules = db.query(Schedule).filter(Schedule.emp_id == emp.id).all()
        for schedule in schedules:
            checkins_exist = db.query(Checkin).filter(
                Checkin.name == emp.name,
                func.date(Checkin.checkin_time) == schedule.schedule_date
            ).first()
            if checkins_exist:
                save_daily_report(db, emp.id, schedule.schedule_date)

    # 更新员工工号：签到记录导入后，将 TEMP_ 开头的工号更新为真实工号
    updated_count = 0
    try:
        temp_employees = db.query(Employee).filter(Employee.emp_no.like('TEMP_%')).all()
        for emp in temp_employees:
            checkin_with_real_no = db.query(Checkin).filter(
                Checkin.name == emp.name,
                ~Checkin.emp_no.like('TEMP_%')
            ).first()
            if checkin_with_real_no:
                # 检查真实工号是否已被使用
                existing = db.query(Employee).filter(
                    Employee.emp_no == checkin_with_real_no.emp_no,
                    Employee.id != emp.id
                ).first()
                if existing:
                    continue
                emp.emp_no = checkin_with_real_no.emp_no
                updated_count += 1

        if updated_count > 0:
            db.commit()
            log_operation(db, current_user["id"], "sync_emp_no", "employees", None, {"updated_count": updated_count})
    except Exception as e:
        db.rollback()
        pass

    return ImportCheckinResponse(count=count, batch=batch)


@router.delete("/{checkin_id}", response_model=dict)
def delete_checkin(
    checkin_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    checkin = db.query(Checkin).filter(Checkin.id == checkin_id).first()
    if not checkin:
        raise HTTPException(status_code=404, detail="记录不存在")

    db.delete(checkin)
    db.commit()
    log_operation(db, current_user["id"], "delete_checkin", "checkins", checkin_id, {"name": checkin.name})
    return {"message": "删除成功"}


@router.delete("/import/{batch}", response_model=dict)
def delete_batch(
    batch: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    count = db.query(Checkin).filter(Checkin.import_batch == batch).delete()
    db.commit()
    log_operation(db, current_user["id"], "delete_batch", "checkins", None, {"batch": batch, "count": count})
    return {"count": count}


@router.get("/report")
def get_checkin_report(
    date: Optional[str] = None,
    year_month: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    team: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """签入签出报表"""
    from datetime import timedelta
    
    query = db.query(Checkin).join(Employee, Checkin.emp_no == Employee.emp_no)
    
    if date:
        query = query.filter(func.date(Checkin.checkin_time) == date)
    elif year_month:
        start = datetime.strptime(f"{year_month}-01", "%Y-%m-%d")
        if year_month == datetime.now().strftime("%Y-%m"):
            end = datetime.now()
        else:
            next_month = start.replace(day=28) + timedelta(days=4)
            end = next_month.replace(day=1) - timedelta(days=1)
        query = query.filter(
            func.date(Checkin.checkin_time) >= start.date(),
            func.date(Checkin.checkin_time) <= end.date()
        )
    elif start_date and end_date:
        query = query.filter(
            func.date(Checkin.checkin_time) >= start_date,
            func.date(Checkin.checkin_time) <= end_date
        )
    else:
        query = query.filter(func.date(Checkin.checkin_time) == datetime.now().strftime("%Y-%m-%d"))
    
    checkins = query.all()

    if team:
        emp_nos = db.query(Employee.emp_no).filter(Employee.team == team).all()
        emp_nos = [e[0] for e in emp_nos]
        checkins = [c for c in checkins if c.emp_no in emp_nos]
    
    if name:
        checkins = [c for c in checkins if name.lower() in c.name.lower()]
    if emp_no:
        checkins = [c for c in checkins if emp_no.lower() in c.emp_no.lower()]
    
    emp_stats = {}
    for c in checkins:
        key = c.emp_no
        if key not in emp_stats:
            emp = db.query(Employee).filter(Employee.emp_no == key).first()
            emp_stats[key] = {
                "emp_no": c.emp_no,
                "name": c.name,
                "dept": c.dept,
                "team": emp.team if emp else '',
                "checkin_count": 0,
                "total_hours": 0.0,
                "checkins": []
            }
        emp_stats[key]["checkin_count"] += 1
        
        checkin_time_str = None
        checkout_time_str = None
        duration = 0.0
        
        if c.checkin_time:
            checkin_time_str = c.checkin_time.strftime('%Y-%m-%d %H:%M')
        if c.checkout_time:
            checkout_time_str = c.checkout_time.strftime('%Y-%m-%d %H:%M')
        if c.checkout_time and c.checkin_time:
            duration = (c.checkout_time - c.checkin_time).total_seconds() / 3600
            emp_stats[key]["total_hours"] += duration
        
        emp_stats[key]["checkins"].append({
            "checkin_time": checkin_time_str,
            "checkout_time": checkout_time_str,
            "duration": round(duration, 1)
        })
        if emp:
            emp_stats[key]["role"] = emp.role
    
    for key in emp_stats:
        emp_stats[key]["checkins"].sort(key=lambda x: x["checkin_time"] or '')
    
    thresholds = db.query(WorkHourThreshold).all()
    threshold_map = {t.team: {"overtime": t.overtime_ratio, "undertime": t.undertime_ratio} for t in thresholds}
    
    team_hours = {}
    for item in emp_stats.values():
        team = item.get("team") or "未知班组"
        role = item.get("role", "")
        if role not in ["组长", "师傅"]:
            if team not in team_hours:
                team_hours[team] = []
            team_hours[team].append(item["total_hours"])
    
    team_avg = {}
    for team, hours in team_hours.items():
        team_avg[team] = sum(hours) / len(hours) if hours else 0
    
    overtime_count = 0
    undertime_count = 0
    
    for item in emp_stats.values():
        team = item.get("team") or "未知班组"
        role = item.get("role", "")
        
        if role in ["组长", "师傅"]:
            item["hour_status"] = "normal"
            item["hour_status_text"] = "-"
        else:
            avg = team_avg.get(team, 0)
            if avg > 0:
                ratio = item["total_hours"] / avg
                overtime_ratio = threshold_map.get(team, {}).get("overtime", 1.2)
                undertime_ratio = threshold_map.get(team, {}).get("undertime", 0.8)
                
                if ratio >= overtime_ratio:
                    item["hour_status"] = "overtime"
                    item["hour_status_text"] = f"超时 ({ratio*100:.0f}%)"
                    overtime_count += 1
                elif ratio <= undertime_ratio:
                    item["hour_status"] = "undertime"
                    item["hour_status_text"] = f"过短 ({ratio*100:.0f}%)"
                    undertime_count += 1
                else:
                    item["hour_status"] = "normal"
                    item["hour_status_text"] = f"正常 ({ratio*100:.0f}%)"
            else:
                item["hour_status"] = "normal"
                item["hour_status_text"] = "-"
    
    items = list(emp_stats.values())
    items.sort(key=lambda x: x["checkin_count"], reverse=True)
    
    total_checkins = sum(x["checkin_count"] for x in items)
    total_hours = sum(x["total_hours"] for x in items)
    avg_hours = total_hours / len(items) if items else 0
    
    return {
        "stats": {
            "total_checkins": total_checkins,
            "total_hours": round(total_hours, 1),
            "avg_hours": round(avg_hours, 1),
            "emp_count": len(items),
            "overtime_count": overtime_count,
            "undertime_count": undertime_count
        },
        "items": items
    }
