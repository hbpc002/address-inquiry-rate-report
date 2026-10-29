import json

from fastapi import HTTPException
from sqlalchemy import false, func, or_, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.marketing_detail import MarketingDetail


ALL_SCOPE = "all"
DEPT_SCOPE = "dept"

DATA_SCOPE_MODULES = {
    "employees": "员工管理",
    "marketing": "营销明细",
    "marketing_report": "营销统计",
    "marketing_overall": "总体营销",
}


def _load_scope_config(user: dict) -> dict:
    config = user.get("data_scope_config") or {}
    if isinstance(config, str):
        try:
            config = json.loads(config) if config else {}
        except Exception:
            config = {}
    return config if isinstance(config, dict) else {}


def is_all_scope(user: dict, module: str | None = None) -> bool:
    if user.get("is_system") or user.get("role") == "admin":
        return True
    config = _load_scope_config(user)
    if module and config.get(module) in (ALL_SCOPE, DEPT_SCOPE):
        return config[module] == ALL_SCOPE
    return (user.get("data_scope") or ALL_SCOPE) == ALL_SCOPE


def get_user_dept(user: dict) -> str:
    return (user.get("dept") or "").strip()


def get_user_scope_paths(user: dict) -> list[str]:
    paths = user.get("department_group_paths") or []
    if isinstance(paths, str):
        paths = [paths]
    result = []
    for path in paths:
        value = str(path or "").strip()
        if value and value not in result:
            result.append(value)
    if not result:
        legacy = get_user_dept(user)
        if legacy:
            result.append(legacy)
    return result


def _path_filters(paths: list[str], column):
    return [column.like(f"{path}%") for path in paths]


def employee_in_scope(employee: Employee, user: dict, module: str = "employees") -> bool:
    if is_all_scope(user, module):
        return True
    paths = get_user_scope_paths(user)
    return bool(
        employee.dept
        and any(employee.dept.startswith(path) for path in paths)
    )


def apply_employee_scope(query, user: dict, module: str = "employees"):
    if is_all_scope(user, module):
        return query
    paths = get_user_scope_paths(user)
    if not paths:
        return query.filter(false())
    return query.filter(or_(*_path_filters(paths, Employee.dept)))


def ensure_dept_in_scope(dept: str | None, user: dict, module: str = "employees") -> str:
    if is_all_scope(user, module):
        return (dept or "").strip()

    paths = get_user_scope_paths(user)
    if not paths:
        raise HTTPException(status_code=403, detail="当前账号未配置所属部门组，无法操作该数据")

    target = (dept or "").strip()
    if not target:
        return paths[0]
    if not any(target.startswith(path) for path in paths):
        raise HTTPException(status_code=403, detail="无权操作其他部门的员工")
    return target


def ensure_employee_in_scope(employee: Employee | None, user: dict, module: str = "employees") -> Employee:
    if not employee or not employee_in_scope(employee, user, module):
        raise HTTPException(status_code=404, detail="员工不存在")
    return employee


def apply_marketing_scope(query, db: Session, user: dict, module: str = "marketing"):
    if is_all_scope(user, module):
        return query
    paths = get_user_scope_paths(user)
    if not paths:
        return query.filter(false())

    emp_nos = select(func.upper(Employee.emp_no)).where(
        or_(*_path_filters(paths, Employee.dept))
    )
    return query.filter(func.upper(MarketingDetail.kf_id).in_(emp_nos))


def require_all_scope(user: dict, detail: str = "仅全部数据权限的账号可执行该操作", module: str | None = None):
    if not is_all_scope(user, module):
        raise HTTPException(status_code=403, detail=detail)
