from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
import pandas as pd
import io
import csv
from app.models.database import get_db
from app.models.employee import Employee
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    EmployeeListResponse
)
from app.core.security import get_current_user, require_permission
from app.utils.logger import log_operation

router = APIRouter(prefix="/api/employees", tags=["员工管理"])


@router.get("", response_model=EmployeeListResponse)
def get_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    team: Optional[str] = None,
    dept: Optional[str] = None,
    status: Optional[str] = None,
    role: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Employee)
    if team:
        query = query.filter(Employee.team == team)
    if dept:
        query = query.filter(Employee.dept == dept)
    if role:
        query = query.filter(Employee.role == role)
    if status:
        query = query.filter(Employee.status == status)
    if search:
        query = query.filter(
            (Employee.name.like(f"%{search}%")) |
            (Employee.emp_no.like(f"%{search}%"))
        )

    total = query.count()
    items = query.order_by(Employee.id.desc()).offset((page-1)*limit).limit(limit).all()
    return EmployeeListResponse(
        items=[EmployeeResponse.model_validate(e) for e in items],
        total=total
    )


@router.post("", response_model=dict)
def create_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "employees.create")
    existing = db.query(Employee).filter(Employee.emp_no == employee.emp_no).first()
    if existing:
        raise HTTPException(status_code=400, detail="工号已存在")

    db_employee = Employee(**employee.model_dump(), created_by=current_user["id"])
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    log_operation(db, current_user["id"], "create_employee", "employees", db_employee.id, {"emp_no": employee.emp_no, "name": employee.name})
    return {"id": db_employee.id}


@router.put("/{employee_id}", response_model=dict)
def update_employee(
    employee_id: int,
    employee: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "employees.edit")
    db_employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not db_employee:
        raise HTTPException(status_code=404, detail="员工不存在")

    for key, value in employee.model_dump(exclude_unset=True).items():
        setattr(db_employee, key, value)
    db.commit()
    return {"id": db_employee.id}


@router.delete("/{employee_id}", response_model=dict)
def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "employees.delete")
    db_employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not db_employee:
        raise HTTPException(status_code=404, detail="员工不存在")

    db_employee.status = "离职"
    db.commit()
    log_operation(db, current_user["id"], "delete_employee", "employees", employee_id, {"emp_no": db_employee.emp_no, "name": db_employee.name})
    return {"message": "删除成功"}


@router.get("/departments", response_model=list)
def get_departments(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    results = db.query(Employee.dept, func.count(Employee.id)).filter(
        Employee.status == "在职"
    ).group_by(Employee.dept).all()
    return [{"dept": r[0] or "未设置", "count": r[1]} for r in results if r[0]]


@router.get("/teams", response_model=list)
def get_teams(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    results = db.query(Employee.team, func.count(Employee.id)).filter(
        Employee.status == "在职"
    ).group_by(Employee.team).all()
    return [{"team": r[0], "count": r[1]} for r in results if r[0]]


@router.get("/roles", response_model=list)
def get_roles(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    results = db.query(Employee.role, func.count(Employee.id)).filter(
        Employee.status == "在职"
    ).group_by(Employee.role).all()
    return [{"role": r[0], "count": r[1]} for r in results if r[0]]


@router.post("/import", response_model=dict)
def import_employees(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导入员工信息Excel"""
    require_permission(current_user, "employees.upload")
    contents = file.file.read()
    try:
        xlsx = pd.ExcelFile(io.BytesIO(contents))
        df = pd.read_excel(xlsx, sheet_name=0)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法解析Excel文件: {str(e)}")
    
    cols = df.columns.tolist()
    required_cols = ['工号', '姓名']
    for col in required_cols:
        if col not in cols:
            raise HTTPException(status_code=400, detail=f"缺少必需列: {col}")
    
    created = 0
    updated = 0
    skipped = 0
    
    for _, row in df.iterrows():
        emp_no = str(row.get('工号', '')).strip()
        name = str(row.get('姓名', '')).strip()
        
        if not emp_no or not name or emp_no == 'nan':
            skipped += 1
            continue
        
        existing = db.query(Employee).filter(Employee.emp_no == emp_no).first()
        if existing:
            existing.name = name
            existing.team = str(row.get('班组', existing.team or '')).strip() if pd.notna(row.get('班组')) else existing.team
            existing.dept = str(row.get('部门', existing.dept or '')).strip() if pd.notna(row.get('部门')) else existing.dept
            existing.role = str(row.get('岗位', existing.role or '')).strip() if pd.notna(row.get('岗位')) else existing.role
            if pd.notna(row.get('状态')):
                existing.status = str(row.get('状态', '在职')).strip()
            updated += 1
        else:
            emp = Employee(
                emp_no=emp_no,
                name=name,
                team=str(row.get('班组', '')).strip() if pd.notna(row.get('班组')) else '',
                dept=str(row.get('部门', '客服中心')).strip() if pd.notna(row.get('部门')) else '客服中心',
                role=str(row.get('岗位', '组员')).strip() if pd.notna(row.get('岗位')) else '组员',
                status=str(row.get('状态', '在职')).strip() if pd.notna(row.get('状态')) else '在职',
                created_by=current_user["id"]
            )
            db.add(emp)
            created += 1
    
    db.commit()
    log_operation(db, current_user["id"], "import_employees", "employees", None, {"created": created, "updated": updated, "skipped": skipped})
    return {
        "message": "导入完成",
        "created": created,
        "updated": updated,
        "skipped": skipped
    }


@router.get("/export")
def export_employees(
    team: Optional[str] = None,
    dept: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Employee)
    if team:
        query = query.filter(Employee.team == team)
    if dept:
        query = query.filter(Employee.dept == dept)
    if status:
        query = query.filter(Employee.status == status)

    items = query.order_by(Employee.emp_no).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["工号", "姓名", "班组", "部门", "岗位", "状态"])
    for emp in items:
        writer.writerow([emp.emp_no, emp.name, emp.team, emp.dept or "", emp.role, emp.status])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=employees.csv"}
    )