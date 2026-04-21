from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from app.models.database import get_db
from app.models.employee import Employee
from app.schemas.employee import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    EmployeeListResponse
)
from app.core.security import get_current_user

router = APIRouter(prefix="/api/employees", tags=["员工管理"])


@router.get("", response_model=EmployeeListResponse)
def get_employees(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    team: Optional[str] = None,
    dept: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
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
    existing = db.query(Employee).filter(Employee.emp_no == employee.emp_no).first()
    if existing:
        raise HTTPException(status_code=400, detail="工号已存在")

    db_employee = Employee(**employee.model_dump(), created_by=current_user["id"])
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return {"id": db_employee.id}


@router.put("/{employee_id}", response_model=dict)
def update_employee(
    employee_id: int,
    employee: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
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
    db_employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not db_employee:
        raise HTTPException(status_code=404, detail="员工不存在")

    db_employee.status = "离职"
    db.commit()
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