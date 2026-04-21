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
from app.schemas.checkin import CheckinResponse, CheckinListResponse, ImportCheckinResponse
from app.core.security import get_current_user

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

    for row in reader:
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
    return {"message": "删除成功"}


@router.delete("/import/{batch}", response_model=dict)
def delete_batch(
    batch: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    count = db.query(Checkin).filter(Checkin.import_batch == batch).delete()
    db.commit()
    return {"count": count}