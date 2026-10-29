from fastapi import HTTPException
from sqlalchemy import false, func, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.marketing_detail import MarketingDetail


ALL_SCOPE = "all"
DEPT_SCOPE = "dept"


def is_all_scope(user: dict) -> bool:
    if user.get("is_system") or user.get("role") == "admin":
        return True
    return (user.get("data_scope") or ALL_SCOPE) == ALL_SCOPE


def get_user_dept(user: dict) -> str:
    return (user.get("dept") or "").strip()


def employee_in_scope(employee: Employee, user: dict) -> bool:
    if is_all_scope(user):
        return True
    dept = get_user_dept(user)
    return bool(dept and employee.dept and employee.dept.startswith(dept))


def apply_employee_scope(query, user: dict):
    if is_all_scope(user):
        return query
    dept = get_user_dept(user)
    if not dept:
        return query.filter(false())
    return query.filter(Employee.dept.like(f"{dept}%"))


def ensure_dept_in_scope(dept: str | None, user: dict) -> str:
    if is_all_scope(user):
        return (dept or "").strip()

    user_dept = get_user_dept(user)
    if not user_dept:
        raise HTTPException(status_code=403, detail="当前账号未配置所属部门，无法操作该数据")

    target = (dept or "").strip()
    if not target:
        return user_dept
    if not target.startswith(user_dept):
        raise HTTPException(status_code=403, detail="无权操作其他部门的员工")
    return target


def ensure_employee_in_scope(employee: Employee | None, user: dict) -> Employee:
    if not employee or not employee_in_scope(employee, user):
        raise HTTPException(status_code=404, detail="员工不存在")
    return employee


def apply_marketing_scope(query, db: Session, user: dict):
    if is_all_scope(user):
        return query
    dept = get_user_dept(user)
    if not dept:
        return query.filter(false())

    emp_nos = select(func.upper(Employee.emp_no)).where(Employee.dept.like(f"{dept}%"))
    return query.filter(func.upper(MarketingDetail.kf_id).in_(emp_nos))


def require_all_scope(user: dict, detail: str = "仅全部数据权限的账号可执行该操作"):
    if not is_all_scope(user):
        raise HTTPException(status_code=403, detail=detail)
