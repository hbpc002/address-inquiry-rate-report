from typing import Optional, Tuple

from app.models.employee import Employee

UNASSIGNED_TEAM = "未匹配班组"


def effective_dept(emp: Optional[Employee]) -> str:
    if not emp:
        return ""
    return (emp.assign_dept or emp.dept or "").strip()


def effective_team(emp: Optional[Employee]) -> str:
    if not emp:
        return UNASSIGNED_TEAM
    return (emp.assign_team or emp.team or UNASSIGNED_TEAM).strip() or UNASSIGNED_TEAM
