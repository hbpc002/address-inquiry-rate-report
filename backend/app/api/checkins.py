from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, case
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
from app.models.attendance_config import AttendanceConfig
from app.models.training_record import TrainingRecord
from app.utils.logger import log_operation


def determine_shift_name(sched, first_checkin_time_str, checkout_time_str=None):
    """根据排班班次名称确定班次，若无排班则按签出/签入时间兜底。

    Args:
        sched: Schedule 对象或 None，包含 shift_name 属性
        first_checkin_time_str: 形如 "2026-07-15 08:05" 的首签时间字符串
        checkout_time_str: 形如 "2026-07-15 20:30" 的最后签出时间（可选），兜底时用于判断晚班

    Returns:
        "早班", "中班", 或 "晚班"
    """
    if sched and sched.shift_name:
        raw = sched.shift_name
        if '晚' in raw:
            return "晚班"
        if '行政' in raw or '早' in raw:
            return "早班"
        if '中' in raw:
            return "中班"
    if checkout_time_str:
        checkout_hour = int(checkout_time_str.split()[1].split(':')[0])
        checkout_min = int(checkout_time_str.split()[1].split(':')[1])
        if checkout_hour > 20 or (checkout_hour == 20 and checkout_min >= 30):
            return "晚班"
    hour = int(first_checkin_time_str.split()[1].split(':')[0])
    if hour < 10:
        return "早班"
    if hour < 15:
        return "中班"
    return "晚班"
from app.schemas.checkin import CheckinResponse, CheckinListResponse, ImportCheckinResponse
from app.core.security import get_current_user, require_permission
from app.services.attendance import save_daily_report

router = APIRouter(prefix="/api/checkins", tags=["签到记录"])

# 只取这个部门的数据
TARGET_DEPT = "广西分公司>>省中心>>客户服务营销中心>>热线运营组>>10010热线客服代表"


@router.get("", response_model=CheckinListResponse)
def get_checkins(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    import_batch: Optional[str] = None,
    checkin_date: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    dept: Optional[str] = None,
    device_no: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Checkin)
    if import_batch:
        query = query.filter(Checkin.import_batch == import_batch)
    if checkin_date:
        query = query.filter(func.date(Checkin.checkin_time) == checkin_date)
    if name:
        query = query.filter(Checkin.name.ilike(f'%{name}%'))
    if emp_no:
        query = query.filter(Checkin.emp_no == emp_no)
    if dept:
        query = query.filter(Checkin.dept == dept)
    if device_no:
        query = query.filter(Checkin.device_no.ilike(f'%{device_no}%'))

    total = query.count()
    items = query.order_by(Checkin.checkin_time.desc()).offset((page-1)*limit).limit(limit).all()
    return CheckinListResponse(
        items=[CheckinResponse.model_validate(c) for c in items],
        total=total
    )


@router.get("/departments", response_model=list)
def get_checkin_departments(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    results = db.query(Checkin.dept, func.count(Checkin.id)).group_by(Checkin.dept).all()
    return [{"dept": r[0], "count": r[1]} for r in results if r[0]]


@router.post("/import", response_model=ImportCheckinResponse)
def import_checkins(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导入签到记录，只取目标部门的员工。按日期删除旧数据后批量插入。"""
    require_permission(current_user, "checkins.upload")
    
    batch = str(uuid.uuid4())[:8]
    content = file.file.read()

    try:
        content.decode('utf-8')
        encoding = 'utf-8'
    except UnicodeDecodeError:
        encoding = 'gbk'

    text = content.decode(encoding)
    reader = csv.DictReader(io.StringIO(text))
    
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV文件为空")
    
    required_fields = ['账号', '工号', '用户名', '姓名', '签入时间', '签到时间']
    has_required = any(any(f in row for f in required_fields) for row in rows[:1])
    if not has_required:
        raise HTTPException(status_code=400, detail="CSV文件格式错误：缺少必要字段")
    
    new_records = []
    dates = set()
    dept_updates = {}

    for row in rows:
        try:
            dept = row.get('所属部门全路径', '') or row.get('归属部门', '') or ''
            dept = str(dept).strip()

            if not dept.startswith(TARGET_DEPT):
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

            dates.add(checkin_time.date())
            new_records.append({
                "emp_no": emp_no,
                "name": name,
                "checkin_time": checkin_time,
                "checkout_time": checkout_time,
                "device_no": device_no,
                "dept": dept,
                "import_batch": batch,
            })

            if dept:
                dept_updates[emp_no] = dept
        except Exception:
            continue

    # 批量更新员工表的部门（去重后一次提交）
    for emp_no, dept in dept_updates.items():
        db.query(Employee).filter(Employee.emp_no == emp_no).update({"dept": dept}, synchronize_session=False)

    # 按日期删除旧数据，再批量插入新数据
    if dates:
        db.query(Checkin).filter(
            func.date(Checkin.checkin_time).in_(dates)
        ).delete(synchronize_session=False)

    if new_records:
        db.bulk_insert_mappings(Checkin, new_records)

    db.commit()
    count = len(new_records)
    log_operation(db, current_user["id"], "import_checkins", "checkins", None, {"batch": batch, "count": count})

    # 重算受影响日期上所有有排班员工的考勤日报（无论有无打卡记录）
    processed_reports = set()
    for d in dates:
        emp_ids = db.query(Schedule.emp_id).filter(Schedule.schedule_date == d).distinct().all()
        for (eid,) in emp_ids:
            key = (eid, d)
            if key in processed_reports:
                continue
            processed_reports.add(key)
            save_daily_report(db, eid, d)

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


@router.delete("/by-date", response_model=dict)
def delete_checkins_by_date(
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """按日期删除签到记录"""
    require_permission(current_user, "checkins.delete")
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式无效，应为 YYYY-MM-DD")
    records = db.query(Checkin).filter(func.date(Checkin.checkin_time) == target).all()
    count = len(records)
    for r in records:
        db.delete(r)
    db.commit()
    log_operation(db, current_user["id"], "delete_by_date", "checkins", None, {"date": date, "count": count})
    return {"count": count}


@router.delete("/{checkin_id}", response_model=dict)
def delete_checkin(
    checkin_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "checkins.delete")
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
    require_permission(current_user, "checkins.delete")
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

    # Step 1: Determine date range
    if date:
        d = datetime.strptime(date, "%Y-%m-%d").date()
        query_start = d
        query_end = d
    elif year_month:
        query_start = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
        if year_month == datetime.now().strftime("%Y-%m"):
            query_end = datetime.now().date()
        else:
            next_month = (query_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            query_end = next_month - timedelta(days=1)
    elif start_date and end_date:
        query_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        query_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        query_start = datetime.now().date()
        query_end = query_start

    # Step 2: Query checkins — only employees with valid team from employee table
    query = db.query(Checkin).join(Employee, Checkin.emp_no == Employee.emp_no)
    query = query.filter(
        Employee.team != '',
        func.date(Checkin.checkin_time) >= query_start,
        func.date(Checkin.checkin_time) <= query_end
    )

    checkins = query.all()

    # 只取目标部门的数据
    checkins = [c for c in checkins if c.dept and c.dept.startswith(TARGET_DEPT)]

    if team:
        emp_nos = db.query(Employee.emp_no).filter(Employee.team == team).all()
        emp_nos = [e[0] for e in emp_nos]
        checkins = [c for c in checkins if c.emp_no in emp_nos]

    if name:
        checkins = [c for c in checkins if name.lower() in c.name.lower()]
    if emp_no:
        checkins = [c for c in checkins if emp_no.lower() in c.emp_no.lower()]

    # Step 3: Get scheduled_hours from DailyReport for the same date range
    scheduled_data = db.query(
        Employee.emp_no,
        func.sum(DailyReport.scheduled_hours)
    ).join(Employee, DailyReport.emp_id == Employee.id).filter(
        DailyReport.schedule_date >= query_start,
        DailyReport.schedule_date <= query_end
    ).group_by(Employee.emp_no).all()
    scheduled_map = {emp_no: float(total or 0) for emp_no, total in scheduled_data}

    # Get aggregated Schedule metrics for the same date range
    schedule_stats = db.query(
        Employee.emp_no,
        func.avg(Schedule.punctuality_rate),
        func.sum(Schedule.call_duration),
        func.sum(Schedule.organize_duration),
        func.avg(Schedule.utilization_rate),
        func.avg(Schedule.attendance_rate)
    ).join(Employee, Schedule.emp_id == Employee.id).filter(
        Schedule.schedule_date >= query_start,
        Schedule.schedule_date <= query_end
    ).group_by(Employee.emp_no).all()
    schedule_agg_map = {}
    for row in schedule_stats:
        schedule_agg_map[row[0]] = {
            "avg_punctuality_rate": float(row[1]) if row[1] is not None else None,
            "total_call_duration": float(row[2]) if row[2] is not None else None,
            "total_organize_duration": float(row[3]) if row[3] is not None else None,
            "avg_utilization_rate": float(row[4]) if row[4] is not None else None,
            "avg_attendance_rate": float(row[5]) if row[5] is not None else None,
        }

    training_stats = db.query(
        TrainingRecord.emp_no,
        func.sum(TrainingRecord.duration_minutes)
    ).filter(
        TrainingRecord.record_date >= query_start,
        TrainingRecord.record_date <= query_end
    ).group_by(TrainingRecord.emp_no).all()
    training_map = {emp_no: int(total) for emp_no, total in training_stats}

    emp_stats = {}
    for c in checkins:
        key = c.emp_no
        if key not in emp_stats:
            emp = db.query(Employee).filter(Employee.emp_no == key).first()
            sched_agg = schedule_agg_map.get(key, {})
            emp_stats[key] = {
                "emp_no": c.emp_no,
                "name": c.name,
                "dept": c.dept,
                "team": emp.team if emp else '',
                "checkin_count": 0,
                "total_hours": 0.0,
                "scheduled_hours": scheduled_map.get(key, 0),
                "avg_punctuality_rate": sched_agg.get("avg_punctuality_rate"),
                "total_call_duration": sched_agg.get("total_call_duration"),
                "total_organize_duration": sched_agg.get("total_organize_duration"),
                "avg_utilization_rate": sched_agg.get("avg_utilization_rate"),
                "avg_attendance_rate": sched_agg.get("avg_attendance_rate"),
                "training_minutes": training_map.get(key, 0),
                "computed_punctuality_rate": None,
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

    # Build team median fallback (for employees without schedule data)
    team_hours = {}
    for item in emp_stats.values():
        team = item.get("team") or "未知班组"
        role = item.get("role", "")
        if role not in ["组长", "师傅"]:
            if team not in team_hours:
                team_hours[team] = []
            team_hours[team].append(item["total_hours"])

    team_median = {}
    for team, hours in team_hours.items():
        if hours:
            sorted_hours = sorted(hours)
            n = len(sorted_hours)
            if n % 2 == 1:
                team_median[team] = sorted_hours[n // 2]
            else:
                team_median[team] = (sorted_hours[n // 2 - 1] + sorted_hours[n // 2]) / 2
        else:
            team_median[team] = 0

    overtime_count = 0
    undertime_count = 0

    for item in emp_stats.values():
        team = item.get("team") or "未知班组"
        role = item.get("role", "")

        if role in ["组长", "师傅"]:
            item["hour_status"] = "normal"
            item["hour_status_text"] = "-"
        else:
            scheduled = item.get("scheduled_hours", 0)
            if scheduled > 0:
                ratio = item["total_hours"] / scheduled
            else:
                median = team_median.get(team, 0)
                ratio = item["total_hours"] / median if median > 0 else 0

            overtime_ratio = threshold_map.get(team, {}).get("overtime", 1.2)
            undertime_ratio = threshold_map.get(team, {}).get("undertime", 0.8)

            if ratio >= overtime_ratio:
                item["hour_status"] = "overtime"
                item["hour_status_text"] = f"超时 ({ratio*100:.0f}%)"
                overtime_count += 1
            elif 0 < ratio <= undertime_ratio:
                item["hour_status"] = "undertime"
                item["hour_status_text"] = f"过短 ({ratio*100:.0f}%)"
                undertime_count += 1
            else:
                item["hour_status"] = "normal"
                item["hour_status_text"] = f"正常 ({ratio*100:.0f}%)"

        training_hours = item.get("training_minutes", 0) / 60.0
        scheduled = item.get("scheduled_hours", 0)
        if scheduled > 0:
            effective_hours = max(0, item["total_hours"] - training_hours)
            effective_scheduled = scheduled - training_hours
            if effective_scheduled > 0:
                item["computed_punctuality_rate"] = round((effective_hours / effective_scheduled) * 100, 2)
            else:
                item["computed_punctuality_rate"] = None
        else:
            item["computed_punctuality_rate"] = None
    
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


@router.get("/time-analysis")
def get_time_analysis(
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
    """按时段规律分析：分时签入/签出分布、班次分布、分时工时利用率"""
    from datetime import timedelta

    if date:
        d = datetime.strptime(date, "%Y-%m-%d").date()
        query_start = d
        query_end = d
    elif year_month:
        query_start = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
        if year_month == datetime.now().strftime("%Y-%m"):
            query_end = datetime.now().date()
        else:
            next_month = (query_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            query_end = next_month - timedelta(days=1)
    elif start_date and end_date:
        query_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        query_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        query_start = datetime.now().date()
        query_end = query_start

    base_filters = [
        Employee.team != '',
        Employee.dept.like(TARGET_DEPT + '%'),
    ]
    if team:
        base_filters.append(Employee.team == team)
    if name:
        base_filters.append(Employee.name.ilike(f'%{name}%'))
    if emp_no:
        base_filters.append(Employee.emp_no.ilike(f'%{emp_no}%'))

    # ---- 1) 分时签入/签出分布 (0-23) ----
    checkin_rows = db.query(
        func.extract('hour', Checkin.checkin_time).label('h'),
        func.count(Checkin.id)
    ).join(Employee, Checkin.emp_no == Employee.emp_no).filter(
        *base_filters,
        func.date(Checkin.checkin_time) >= query_start,
        func.date(Checkin.checkin_time) <= query_end
    ).group_by('h').all()

    checkout_rows = db.query(
        func.extract('hour', Checkin.checkout_time).label('h'),
        func.count(Checkin.id)
    ).join(Employee, Checkin.emp_no == Employee.emp_no).filter(
        *base_filters,
        Checkin.checkout_time.isnot(None),
        func.date(Checkin.checkin_time) >= query_start,
        func.date(Checkin.checkin_time) <= query_end
    ).group_by('h').all()

    checkin_hour_counts = {int(h): c for h, c in checkin_rows}
    checkout_hour_counts = {int(h): c for h, c in checkout_rows}
    hourly = [{
        "hour": h,
        "checkin_count": checkin_hour_counts.get(h, 0),
        "checkout_count": checkout_hour_counts.get(h, 0)
    } for h in range(24)]

    # ---- 2. 班次分布（整体 + 按班组）----
    def normalize_shift(raw):
        if not raw:
            return "其他"
        if '晚' in raw:
            return "晚班"
        if '行政' in raw or '早' in raw:
            return "早班"
        if '中' in raw:
            return "中班"
        return raw

    shift_rows = db.query(
        Employee.team,
        Schedule.shift_name,
        func.count(Schedule.id)
    ).join(Schedule, Schedule.emp_id == Employee.id).filter(
        *base_filters,
        Schedule.shift_name.isnot(None),
        Schedule.schedule_date >= query_start,
        Schedule.schedule_date <= query_end
    ).group_by(Employee.team, Schedule.shift_name).all()

    overall_counter = {}
    by_team_counter = {}
    for team_name, shift_name, cnt in shift_rows:
        norm = normalize_shift(shift_name)
        overall_counter[norm] = overall_counter.get(norm, 0) + cnt
        by_team_counter.setdefault(team_name, {})
        by_team_counter[team_name][norm] = by_team_counter[team_name].get(norm, 0) + cnt

    overall_shifts = [{"shift_name": k, "count": v} for k, v in overall_counter.items()]
    overall_shifts.sort(key=lambda x: -x["count"])
    team_shifts = [
        {"team": t, "shift_name": s, "count": c}
        for t, counts in by_team_counter.items() for s, c in counts.items()
    ]

    # ---- 3. 分时工时利用率 (0-23) ----
    def to_minutes(h, m):
        return int(h) * 60 + int(m)

    def overlaps(a0, a1, b0, b1):
        return a0 < b1 and b0 < a1

    def hour_covered(win_start, win_end, wrap, hour):
        s = win_start
        e = win_end + (1440 if wrap else 0)
        return any(
            overlaps(hb, hb + 60, s, e)
            for hb in (hour * 60, hour * 60 + 1440)
        )

    reports = db.query(DailyReport).join(Employee, DailyReport.emp_id == Employee.id).filter(
        *base_filters,
        DailyReport.schedule_date >= query_start,
        DailyReport.schedule_date <= query_end
    ).all()

    scheduled_count = [0] * 24
    actual_count = [0] * 24
    for r in reports:
        sched_start = r.scheduled_start
        sched_end = r.scheduled_end
        actual_in = r.actual_checkin
        actual_out = r.actual_checkout

        if sched_start and sched_end:
            ss = to_minutes(*map(int, str(sched_start).split(':')[:2]))
            se = to_minutes(*map(int, str(sched_end).split(':')[:2]))
            wrap = se < ss
            for h in range(24):
                if hour_covered(ss, se, wrap, h):
                    scheduled_count[h] += 1

        if actual_in and actual_out:
            ai = to_minutes(actual_in.hour, actual_in.minute)
            ao = to_minutes(actual_out.hour, actual_out.minute)
            wrap = actual_out.date() > actual_in.date() or ao < ai
            for h in range(24):
                if hour_covered(ai, ao, wrap, h):
                    actual_count[h] += 1

    hourly_utilization = [{
        "hour": h,
        "scheduled_count": scheduled_count[h],
        "actual_count": actual_count[h],
        "utilization": round(actual_count[h] / scheduled_count[h] * 100, 1)
        if scheduled_count[h] > 0 else 0
    } for h in range(24)]

    return {
        "hourly": hourly,
        "shifts": {
            "overall": overall_shifts,
            "by_team": team_shifts,
        },
        "hourly_utilization": hourly_utilization,
        "period": {
            "start": query_start.isoformat(),
            "end": query_end.isoformat()
        }
    }


@router.get("/team-report")
def get_team_report(
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
    """按班组报表：统计每位员工的晚签/早退情况，便于查看组内谁晚签多、谁提前签出多（可排序）"""
    from datetime import timedelta

    # 与 report 一致的日期范围解析
    if date:
        d = datetime.strptime(date, "%Y-%m-%d").date()
        query_start = d
        query_end = d
    elif year_month:
        query_start = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
        if year_month == datetime.now().strftime("%Y-%m"):
            query_end = datetime.now().date()
        else:
            next_month = (query_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            query_end = next_month - timedelta(days=1)
    elif start_date and end_date:
        query_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        query_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        query_start = datetime.now().date()
        query_end = query_start

    emp_filters = [
        Employee.team != '',
        Employee.dept.like(TARGET_DEPT + '%'),
    ]
    if team:
        emp_filters.append(Employee.team == team)
    if name:
        emp_filters.append(Employee.name.ilike(f'%{name}%'))
    if emp_no:
        emp_filters.append(Employee.emp_no.ilike(f'%{emp_no}%'))

    emp_rows = db.query(
        Employee.emp_no,
        Employee.name,
        Employee.team,
        Employee.dept,
        func.sum(func.coalesce(DailyReport.late_minutes, 0)),
        func.sum(func.coalesce(DailyReport.early_minutes, 0)),
        func.sum(case((DailyReport.late_minutes > 0, 1), else_=0)),
        func.sum(case((DailyReport.early_minutes > 0, 1), else_=0)),
        func.sum(case((DailyReport.actual_checkin.isnot(None), 1), else_=0)),
    ).join(DailyReport, DailyReport.emp_id == Employee.id).filter(
        *emp_filters,
        DailyReport.schedule_date >= query_start,
        DailyReport.schedule_date <= query_end
    ).group_by(
        Employee.emp_no,
        Employee.name,
        Employee.team,
        Employee.dept
    ).all()

    # 签到次数来自签到表，与汇总报表口径一致
    checkin_counts = db.query(
        Employee.emp_no,
        func.count(Checkin.id)
    ).join(Employee, Checkin.emp_no == Employee.emp_no).filter(
        Employee.team != '',
        Employee.dept.like(TARGET_DEPT + '%'),
        func.date(Checkin.checkin_time) >= query_start,
        func.date(Checkin.checkin_time) <= query_end
    ).group_by(Employee.emp_no).all()
    checkin_count_map = {emp_no: cnt for emp_no, cnt in checkin_counts}

    items = []
    for emp_no, emp_name, team_name, dept, late_min, early_min, late_days, early_days, attend_days in emp_rows:
        items.append({
            "emp_no": emp_no,
            "name": emp_name,
            "team": team_name,
            "dept": dept or '',
            "checkin_count": checkin_count_map.get(emp_no, 0),
            "late_days": int(late_days or 0),
            "late_minutes": int(late_min or 0),
            "early_days": int(early_days or 0),
            "early_minutes": int(early_min or 0),
            "attend_days": int(attend_days or 0),
        })

    items.sort(key=lambda x: x["late_minutes"], reverse=True)

    return {"items": items}


@router.get("/personal-report")
def get_personal_report(
    emp_no: str = Query(...),
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """个人签到多维度统计"""
    from datetime import timedelta

    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    emp = db.query(Employee).filter(Employee.emp_no == emp_no).first()
    if not emp:
        raise HTTPException(status_code=404, detail="员工不存在")

    config_row = db.query(AttendanceConfig).filter(AttendanceConfig.key == "long_hour_threshold").first()
    long_hour_threshold = float(config_row.value) if config_row else 9.5

    checkins = db.query(Checkin).filter(
        Checkin.emp_no == emp_no,
        func.date(Checkin.checkin_time) >= start,
        func.date(Checkin.checkin_time) <= end
    ).order_by(Checkin.checkin_time).all()

    daily_reports = db.query(DailyReport).filter(
        DailyReport.emp_id == emp.id,
        DailyReport.schedule_date >= start,
        DailyReport.schedule_date <= end
    ).all()
    daily_report_map = {r.schedule_date: r for r in daily_reports}

    schedules = db.query(Schedule).filter(
        Schedule.emp_id == emp.id,
        Schedule.schedule_date >= start,
        Schedule.schedule_date <= end
    ).all()
    schedule_map = {s.schedule_date: s for s in schedules}

    training_recs = db.query(TrainingRecord).filter(
        TrainingRecord.emp_no == emp_no,
        TrainingRecord.record_date >= start,
        TrainingRecord.record_date <= end
    ).all()
    training_map = {}
    for tr in training_recs:
        d = tr.record_date.isoformat()
        if d not in training_map:
            training_map[d] = 0
        training_map[d] += tr.duration_minutes

    daily_map = {}
    for c in checkins:
        d = c.checkin_time.date()
        if d not in daily_map:
            daily_map[d] = {
                "date": d.isoformat(),
                "checkins": [],
                "total_duration": 0.0
            }

        duration = 0.0
        if c.checkout_time and c.checkin_time:
            duration = (c.checkout_time - c.checkin_time).total_seconds() / 3600

        daily_map[d]["checkins"].append({
            "checkin_time": c.checkin_time.strftime('%Y-%m-%d %H:%M'),
            "checkout_time": c.checkout_time.strftime('%Y-%m-%d %H:%M') if c.checkout_time else None,
            "duration": round(duration, 1),
            "device_no": c.device_no or ''
        })
        daily_map[d]["total_duration"] += duration

    daily_stats = []
    for d in sorted(daily_map.keys()):
        entry = daily_map[d]

        report = daily_report_map.get(d)
        sched = schedule_map.get(d)

        shift_name = determine_shift_name(
            sched,
            entry["checkins"][0]["checkin_time"],
            entry["checkins"][-1]["checkout_time"]
        )
        training_minutes = training_map.get(entry["date"], 0)
        scheduled_hours = float(report.scheduled_hours) if report and report.scheduled_hours else 0
        actual_hours = float(report.actual_hours) if report and report.actual_hours else 0
        if scheduled_hours > 0:
            effective_hours = max(0, actual_hours - training_minutes / 60.0)
            effective_scheduled = scheduled_hours - training_minutes / 60.0
            if effective_scheduled > 0:
                computed_punctuality = round((effective_hours / effective_scheduled) * 100, 2)
            else:
                computed_punctuality = None
        else:
            computed_punctuality = None

        daily_stats.append({
            "date": entry["date"],
            "checkin_time": entry["checkins"][0]["checkin_time"] if entry["checkins"] else None,
            "checkout_time": entry["checkins"][-1]["checkout_time"] if entry["checkins"] else None,
            "duration": round(entry["total_duration"], 1),
            "shift_name": shift_name,
            "is_long_hour": entry["total_duration"] > long_hour_threshold,
            "scheduled_hours": scheduled_hours,
            "status": report.status if report else '',
            "actual_hours": actual_hours,
            "late_minutes": report.late_minutes if report else 0,
            "early_minutes": report.early_minutes if report else 0,
            "punctuality_rate": float(sched.punctuality_rate) if sched and sched.punctuality_rate is not None else None,
            "call_duration": float(sched.call_duration) if sched and sched.call_duration is not None else None,
            "organize_duration": float(sched.organize_duration) if sched and sched.organize_duration is not None else None,
            "utilization_rate": float(sched.utilization_rate) if sched and sched.utilization_rate is not None else None,
            "attendance_rate": float(sched.attendance_rate) if sched and sched.attendance_rate is not None else None,
            "training_minutes": training_minutes,
            "computed_punctuality_rate": computed_punctuality
        })

    attend_days = len(daily_stats)
    scheduled_days = sum(1 for d in daily_stats if d["scheduled_hours"] > 0)
    total_hours = sum(d["duration"] for d in daily_stats)
    total_scheduled_hours = sum(d["scheduled_hours"] for d in daily_stats)
    long_hour_days = sum(1 for d in daily_stats if d["is_long_hour"])
    late_days = sum(1 for d in daily_stats if d["late_minutes"] > 0)
    early_days = sum(1 for d in daily_stats if d["early_minutes"] > 0)
    morning_days = sum(1 for d in daily_stats if d["shift_name"] == "早班")
    mid_days = sum(1 for d in daily_stats if d["shift_name"] == "中班")
    night_days = sum(1 for d in daily_stats if d["shift_name"] == "晚班")

    team_avg = {"avg_hours": 0, "avg_checkin_count": 0}
    if emp.team:
        team_emps = db.query(Employee.emp_no).filter(
            Employee.team == emp.team,
            Employee.emp_no != emp_no
        ).all()
        team_emp_nos = [e[0] for e in team_emps]
        if team_emp_nos:
            team_data = db.query(
                Checkin.emp_no,
                func.count(Checkin.id),
                func.sum(
                    func.extract('epoch', Checkin.checkout_time - Checkin.checkin_time) / 3600
                )
            ).filter(
                Checkin.emp_no.in_(team_emp_nos),
                func.date(Checkin.checkin_time) >= start,
                func.date(Checkin.checkin_time) <= end,
                Checkin.checkout_time.isnot(None),
                Checkin.checkin_time.isnot(None)
            ).group_by(Checkin.emp_no).all()
            if team_data:
                total_h = sum(float(t[2] or 0) for t in team_data)
                total_c = sum(t[1] for t in team_data)
                n = len(team_data)
                team_avg["avg_hours"] = round(total_h / n, 1) if n else 0
                team_avg["avg_checkin_count"] = round(total_c / n, 1) if n else 0

    return {
        "emp_info": {
            "emp_no": emp.emp_no,
            "name": emp.name,
            "team": emp.team or '',
            "dept": emp.dept or ''
        },
        "summary": {
            "total_hours": round(total_hours, 1),
            "total_scheduled_hours": round(total_scheduled_hours, 1),
            "attend_days": attend_days,
            "scheduled_days": scheduled_days,
            "long_hour_days": long_hour_days,
            "long_hour_threshold": long_hour_threshold,
            "late_days": late_days,
            "early_days": early_days,
            "morning_shift_days": morning_days,
            "mid_shift_days": mid_days,
            "night_shift_days": night_days,
            "team_avg_hours": team_avg["avg_hours"],
            "team_avg_checkin_count": team_avg["avg_checkin_count"],
            "total_call_duration": round(sum(d.get("call_duration") or 0 for d in daily_stats), 1),
            "total_organize_duration": round(sum(d.get("organize_duration") or 0 for d in daily_stats), 1),
            "total_training_minutes": sum(d.get("training_minutes") or 0 for d in daily_stats)
        },
            "daily_stats": daily_stats
    }


@router.get("/report/export")
def export_checkin_report(
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
    """导出签入签出报表 CSV"""
    require_permission(current_user, "checkin_report.export")

    from datetime import timedelta
    if date:
        d = datetime.strptime(date, "%Y-%m-%d").date()
        query_start = d
        query_end = d
    elif year_month:
        query_start = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
        if year_month == datetime.now().strftime("%Y-%m"):
            query_end = datetime.now().date()
        else:
            next_month = (query_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            query_end = next_month - timedelta(days=1)
    elif start_date and end_date:
        query_start = datetime.strptime(start_date, "%Y-%m-%d").date()
        query_end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        query_start = datetime.now().date()
        query_end = query_start

    query = db.query(Checkin).join(Employee, Checkin.emp_no == Employee.emp_no)
    query = query.filter(
        Employee.team != '',
        func.date(Checkin.checkin_time) >= query_start,
        func.date(Checkin.checkin_time) <= query_end
    )
    checkins = query.all()
    checkins = [c for c in checkins if c.dept and c.dept.startswith(TARGET_DEPT)]

    if team:
        emp_nos = [e[0] for e in db.query(Employee.emp_no).filter(Employee.team == team).all()]
        checkins = [c for c in checkins if c.emp_no in emp_nos]
    if name:
        checkins = [c for c in checkins if name.lower() in c.name.lower()]
    if emp_no:
        checkins = [c for c in checkins if emp_no.lower() in c.emp_no.lower()]

    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)

    scheduled_by_emp_date = {}
    scheduled_rows = db.query(
        Employee.emp_no,
        DailyReport.schedule_date,
        DailyReport.scheduled_hours
    ).join(Employee, DailyReport.emp_id == Employee.id).filter(
        DailyReport.schedule_date >= query_start,
        DailyReport.schedule_date <= query_end
    ).all()
    for emp_no, sched_date, sched_hours in scheduled_rows:
        scheduled_by_emp_date[(emp_no, sched_date.isoformat())] = float(sched_hours) if sched_hours else 0.0

    writer.writerow(["账号", "姓名", "部门", "签入时间", "签出时间", "工作时长(h)", "排班工时(h)", "日期"])
    for c in checkins:
        duration = 0.0
        if c.checkout_time and c.checkin_time:
            duration = round((c.checkout_time - c.checkin_time).total_seconds() / 3600, 1)
        sched_hours = scheduled_by_emp_date.get((c.emp_no, c.checkin_time.date().isoformat() if c.checkin_time else ''), '')
        writer.writerow([
            c.emp_no, c.name, c.dept or "",
            c.checkin_time.strftime('%Y-%m-%d %H:%M') if c.checkin_time else "",
            c.checkout_time.strftime('%Y-%m-%d %H:%M') if c.checkout_time else "",
            duration,
            sched_hours,
            c.checkin_time.strftime('%Y-%m-%d') if c.checkin_time else "",
        ])

    filename = f"checkin_report_{query_start}_{query_end}.csv"
    output.seek(0)
    log_operation(db, current_user["id"], "export_checkin_report", "checkins", None, {"start_date": query_start.isoformat(), "end_date": query_end.isoformat()})
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
