from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from typing import Optional
from datetime import datetime, date, timedelta
from calendar import monthrange
import uuid
import pandas as pd
import io
import math

from app.models.database import get_db
from app.models.workload import Workload
from app.models.employee import Employee
from app.utils.logger import log_operation
from app.schemas.workload import (
    WorkloadResponse, WorkloadListResponse, ImportWorkloadResponse,
    WorkloadReportItem, WorkloadReportResponse
)
from app.core.security import get_current_user, require_permission

router = APIRouter(prefix="/api/workloads", tags=["工作量统计"])

TARGET_DEPT = "广西分公司>>省中心>>客户服务营销中心"

CORE_METRICS_FIELDS = [
    "总体-签入次数",
    "总体-签出次数",
    "总体-工作总时长(秒)",
    "总体-工时利用率",
    "呼入人工服务-人工服务-通话次数",
    "呼入人工服务-人工服务-通话总时长(秒)",
    "呼入人工服务-人工服务-通话均长(秒)",
    "呼入人工服务-人工服务-服务后整理总时长(秒)",
    "呼入人工服务-人工服务-呼入等待应答时长",
    "人工服务-满意度-满意率",
    "呼入人工服务-解决率-解决率",
    "呼入人工服务-工单-生成总量",
    "呼入人工服务-工单-其中:咨询工单量",
    "呼入人工服务-工单-其中:投诉工单",
    "呼出服务-人工呼出呼叫量",
    "呼出服务-通话总时长(秒)",
    "服务量合计-通话量",
    "操作次数及时长-示忙次数",
    "操作次数及时长-休息时长(秒)",
    "操作次数及时长-呼入-静音次数",
    "操作次数及时长-整理次数",
    "呼入人工服务-满意度-非常满意量",
    "呼入人工服务-满意度-满意量",
    "呼入人工服务-满意度-一般量",
    "呼入人工服务-满意度-不满意量",
    "呼入人工服务-满意度-非常不满意量",
]


@router.get("", response_model=WorkloadListResponse)
def get_workloads(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    import_batch: Optional[str] = None,
    workload_date: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    name: Optional[str] = None,
    account: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(Workload)
    if import_batch:
        query = query.filter(Workload.import_batch == import_batch)
    if workload_date:
        query = query.filter(cast(Workload.date, Date) == workload_date)
    if start_date:
        query = query.filter(cast(Workload.date, Date) >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(cast(Workload.date, Date) <= datetime.strptime(end_date, "%Y-%m-%d").date())
    if name:
        emp_nos = [e[0] for e in db.query(Employee.emp_no).filter(
            Employee.name.ilike(f'%{name}%')
        ).all()]
        if emp_nos:
            query = query.filter(Workload.account.in_(emp_nos))
        else:
            return WorkloadListResponse(items=[], total=0)
    if account:
        query = query.filter(Workload.account == account)

    emp_accounts = [e[0] for e in db.query(Employee.emp_no).filter(Employee.status == "在职").all()]
    if emp_accounts:
        query = query.filter(Workload.account.in_(emp_accounts))
    else:
        return WorkloadListResponse(items=[], total=0)

    total = query.count()
    items = query.order_by(Workload.date.desc(), Workload.account).offset((page - 1) * limit).limit(limit).all()

    response_items = []
    for w in items:
        item = WorkloadResponse.model_validate(w)
        emp = db.query(Employee).filter(Employee.emp_no == w.account).first()
        if emp:
            item.name = emp.name or item.name
            item.team_desc = emp.team or item.team_desc
        response_items.append(item)

    return WorkloadListResponse(
        items=response_items,
        total=total
    )


@router.post("/import", response_model=ImportWorkloadResponse)
def import_workloads(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "workload.upload")

    batch = str(uuid.uuid4())[:8]
    content = file.file.read()

    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name='Sheet_0', header=None)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法解析Excel文件: {str(e)}")

    if len(df) < 4:
        raise HTTPException(status_code=400, detail="Excel文件数据行不足")

    header = df.iloc[2].tolist()
    data_rows = df.iloc[3:]

    new_records = []
    dates_set = set()

    for idx in range(len(data_rows)):
        row = data_rows.iloc[idx]
        try:
            date_val = str(row[0]).strip() if pd.notna(row[0]) else ''
            if not date_val or date_val == '合计' or date_val == '日期':
                continue

            account_val = str(row[2]).strip() if pd.notna(row[2]) else ''
            if not account_val or account_val == 'nan' or account_val == '账号':
                continue

            try:
                parsed_date = datetime.strptime(date_val, '%Y%m%d').date()
            except ValueError:
                continue

            province_val = str(row[1]).strip() if pd.notna(row[1]) else ''
            name_val = str(row[3]).strip() if pd.notna(row[3]) else ''
            emp_no_val = str(row[4]).strip() if pd.notna(row[4]) else ''
            team_desc_val = str(row[5]).strip() if pd.notna(row[5]) else ''

            if TARGET_DEPT not in team_desc_val:
                continue

            metrics = {}
            for col_idx in range(6, len(header)):
                if col_idx < len(row):
                    val = row[col_idx]
                    col_name = str(header[col_idx]).strip() if pd.notna(header[col_idx]) else f'col_{col_idx}'
                    if col_name and col_name != 'nan':
                        if pd.notna(val):
                            if isinstance(val, (int, float)):
                                if math.isnan(val):
                                    metrics[col_name] = None
                                elif val == int(val):
                                    metrics[col_name] = int(val)
                                else:
                                    metrics[col_name] = round(float(val), 4)
                            else:
                                try:
                                    num_val = float(val)
                                    if num_val == int(num_val):
                                        metrics[col_name] = int(num_val)
                                    else:
                                        metrics[col_name] = round(num_val, 4)
                                except (ValueError, TypeError):
                                    metrics[col_name] = str(val)
                        else:
                            metrics[col_name] = None

            dates_set.add(parsed_date)
            new_records.append({
                "date": parsed_date,
                "province": province_val,
                "account": account_val,
                "name": name_val,
                "emp_no": emp_no_val,
                "team_desc": team_desc_val,
                "metrics": metrics,
                "import_batch": batch,
            })
        except Exception:
            continue

    if dates_set:
        for d in dates_set:
            db.query(Workload).filter(Workload.date == d).delete(synchronize_session=False)

    if new_records:
        db.bulk_insert_mappings(Workload, new_records)

    db.commit()
    count = len(new_records)
    log_operation(db, current_user["id"], "import_workloads", "workloads", None, {"batch": batch, "count": count})

    return ImportWorkloadResponse(count=count, batch=batch)


@router.delete("/by-date", response_model=dict)
def delete_workloads_by_date(
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "workload.delete")
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式无效，应为 YYYY-MM-DD")
    records = db.query(Workload).filter(Workload.date == target).all()
    count = len(records)
    for r in records:
        db.delete(r)
    db.commit()
    log_operation(db, current_user["id"], "delete_workloads_by_date", "workloads", None, {"date": date, "count": count})
    return {"count": count}


@router.delete("/{workload_id}", response_model=dict)
def delete_workload(
    workload_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "workload.delete")
    record = db.query(Workload).filter(Workload.id == workload_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    log_operation(db, current_user["id"], "delete_workload", "workloads", workload_id, {"account": record.account})
    return {"message": "删除成功"}


@router.delete("/import/{batch}", response_model=dict)
def delete_batch(
    batch: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "workload.delete")
    count = db.query(Workload).filter(Workload.import_batch == batch).delete()
    db.commit()
    log_operation(db, current_user["id"], "delete_workload_batch", "workloads", None, {"batch": batch, "count": count})
    return {"count": count}


@router.get("/metrics-fields", response_model=list[str])
def get_metrics_fields(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    sample = db.query(Workload.metrics).filter(Workload.metrics.isnot(None)).first()
    if sample and sample[0]:
        fields = list(sample[0].keys())
        return fields
    return CORE_METRICS_FIELDS


@router.get("/report", response_model=WorkloadReportResponse)
def get_workload_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year_month: Optional[str] = None,
    province: Optional[str] = None,
    team_desc: Optional[str] = None,
    team_prefix: Optional[str] = None,
    name: Optional[str] = None,
    account: Optional[str] = None,
    tenure_mode: Optional[str] = None,
    tenure_months: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    if year_month:
        start = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
        if year_month == datetime.now().strftime("%Y-%m"):
            end = datetime.now().date()
        else:
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_month - timedelta(days=1)
    elif start_date and end_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = datetime.now().date()
        start = end

    query = db.query(Workload).filter(
        Workload.date >= start,
        Workload.date <= end
    )

    records = query.all()

    emp_accounts = {e[0] for e in db.query(Employee.emp_no).filter(Employee.status == "在职").all()}
    records = [r for r in records if r.account in emp_accounts]

    if province:
        records = [r for r in records if r.province == province]
    if team_desc:
        team_emp_nos = {e[0] for e in db.query(Employee.emp_no).filter(
            Employee.team == team_desc, Employee.status == "在职"
        ).all()}
        records = [r for r in records if r.account in team_emp_nos]
    if team_prefix:
        team_emp_nos = {e[0] for e in db.query(Employee.emp_no).filter(
            Employee.team.startswith(team_prefix), Employee.status == "在职"
        ).all()}
        records = [r for r in records if r.account in team_emp_nos]
    if name:
        emp_nos = [e[0] for e in db.query(Employee.emp_no).filter(
            Employee.name.ilike(f'%{name}%')
        ).all()]
        records = [r for r in records if r.account in emp_nos]
    if account:
        records = [r for r in records if account.lower() in (r.account or '').lower()]

    if tenure_mode:
        months = tenure_months or 3
        today = datetime.now().date()
        cutoff = today - timedelta(days=months * 30)
        emp_tenure_map = {}
        for e in db.query(Employee.emp_no, Employee.hire_date).filter(Employee.status == "在职").all():
            if e.hire_date is not None:
                emp_tenure_map[e.emp_no] = e.hire_date > cutoff
            else:
                emp_tenure_map[e.emp_no] = False
        if tenure_mode == "le":
            records = [r for r in records if emp_tenure_map.get(r.account, False)]
        elif tenure_mode == "gt":
            records = [r for r in records if not emp_tenure_map.get(r.account, False)]

    emp_agg = {}
    for r in records:
        key = r.account
        emp = db.query(Employee).filter(Employee.emp_no == r.account).first()
        real_name = emp.name if emp else (r.name or '')
        real_team = emp.team if emp else (r.team_desc or '')
        if key not in emp_agg:
            emp_agg[key] = {
                "account": r.account,
                "name": real_name,
                "emp_no": r.emp_no or '',
                "team_desc": real_team,
                "province": r.province or '',
                "role": emp.role if emp else "",
                "date_count": 0,
                "agg": {}
            }
        emp_agg[key]["date_count"] += 1

        metrics = r.metrics or {}
        for field in CORE_METRICS_FIELDS:
            val = metrics.get(field)
            if val is not None:
                try:
                    num_val = float(val)
                    if field not in emp_agg[key]["agg"]:
                        emp_agg[key]["agg"][field] = {"sum": 0.0, "count": 0, "non_null_count": 0}
                    emp_agg[key]["agg"][field]["sum"] += num_val
                    emp_agg[key]["agg"][field]["count"] += 1
                    emp_agg[key]["agg"][field]["non_null_count"] += 1
                except (ValueError, TypeError):
                    pass

    items = []
    for key, data in emp_agg.items():
        aggregated = {}
        for field in CORE_METRICS_FIELDS:
            agg_data = data["agg"].get(field)
            if agg_data and agg_data["count"] > 0:
                is_rate_field = "率" in field or "均长" in field
                if is_rate_field:
                    aggregated[field] = round(agg_data["sum"] / agg_data["count"], 2)
                else:
                    aggregated[field] = round(agg_data["sum"], 1)
            else:
                aggregated[field] = None

        sat_count_fields = [
            aggregated.get("呼入人工服务-满意度-非常满意量"),
            aggregated.get("呼入人工服务-满意度-满意量"),
            aggregated.get("呼入人工服务-满意度-一般量"),
            aggregated.get("呼入人工服务-满意度-不满意量"),
            aggregated.get("呼入人工服务-满意度-非常不满意量"),
        ]
        if all(c is not None for c in sat_count_fields):
            denominator = sum(sat_count_fields)
            if denominator > 0:
                aggregated["人工服务-满意度-满意率"] = round(
                    (sat_count_fields[0] + sat_count_fields[1]) / denominator, 4
                )
            else:
                aggregated["人工服务-满意度-满意率"] = None

        items.append(WorkloadReportItem(
            account=data["account"],
            name=data["name"],
            emp_no=data["emp_no"],
            team_desc=data["team_desc"],
            province=data["province"],
            role=data["role"],
            date_count=data["date_count"],
            aggregated_metrics=aggregated
        ))

    items.sort(key=lambda x: x.date_count, reverse=True)

    total_people = len(items)
    total_call_count = sum(
        (i.aggregated_metrics.get("呼入人工服务-人工服务-通话次数") or 0) for i in items
    )
    total_work_duration = sum(
        (i.aggregated_metrics.get("总体-工作总时长(秒)") or 0) for i in items
    )
    total_ticket_count = sum(
        (i.aggregated_metrics.get("呼入人工服务-工单-生成总量") or 0) for i in items
    )
    total_outbound = sum(
        (i.aggregated_metrics.get("呼出服务-人工呼出呼叫量") or 0) for i in items
    )

    provinces = list(set(r.province for r in records if r.province))
    emp_accounts_in_range = list(set(r.account for r in records))
    if emp_accounts_in_range:
        teams = [row[0] for row in db.query(Employee.team).filter(
            Employee.emp_no.in_(emp_accounts_in_range),
            Employee.team.isnot(None),
            Employee.team != ''
        ).distinct().all()]
    else:
        teams = []

    return WorkloadReportResponse(
        stats={
            "total_people": total_people,
            "total_records": len(records),
            "total_call_count": round(total_call_count, 1),
            "total_work_duration": round(total_work_duration, 1),
            "total_ticket_count": round(total_ticket_count, 1),
            "total_outbound": round(total_outbound, 1),
            "provinces": provinces,
            "teams": teams,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
        items=items,
        metrics_fields=CORE_METRICS_FIELDS
    )


@router.get("/daily-production")
def get_daily_production(
    year_month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if year_month:
        parts = year_month.split("-")
        year, month = int(parts[0]), int(parts[1])
        start = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end = date(year, month, last_day)
    else:
        now = datetime.now()
        start = date(now.year, now.month, 1)
        _, last_day = monthrange(now.year, now.month)
        end = date(now.year, now.month, last_day)

    emp_accounts = {e[0] for e in db.query(Employee.emp_no).filter(Employee.status == "在职").all()}
    if not emp_accounts:
        return _fill_daily_empty(start, end)

    records = db.query(Workload).filter(
        Workload.date >= start,
        Workload.date <= end,
        Workload.account.in_(emp_accounts),
    ).all()

    daily = {}
    for r in records:
        d = r.date.isoformat()
        if d not in daily:
            daily[d] = {"call_count": 0, "ticket_count": 0, "outbound_count": 0, "_people": set()}
        m = r.metrics or {}
        daily[d]["call_count"] += m.get("呼入人工服务-人工服务-通话次数", 0) or 0
        daily[d]["ticket_count"] += m.get("呼入人工服务-工单-生成总量", 0) or 0
        daily[d]["outbound_count"] += m.get("呼出服务-人工呼出呼叫量", 0) or 0
        daily[d]["_people"].add(r.account)

    result = []
    for day_num in range(1, last_day + 1):
        d = date(year, month, day_num).isoformat()
        if d in daily:
            entry = daily[d]
            result.append({
                "date": d,
                "call_count": entry["call_count"],
                "ticket_count": entry["ticket_count"],
                "outbound_count": entry["outbound_count"],
                "people_count": len(entry["_people"]),
            })
        else:
            result.append({"date": d, "call_count": 0, "ticket_count": 0, "outbound_count": 0, "people_count": 0})

    return result


def _fill_daily_empty(start: date, end: date) -> list:
    result = []
    d = start
    while d <= end:
        result.append({"date": d.isoformat(), "call_count": 0, "ticket_count": 0, "outbound_count": 0, "people_count": 0})
        from datetime import timedelta
        d += timedelta(days=1)
    return result


@router.get("/team-production")
def get_team_production(
    year_month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if year_month:
        parts = year_month.split("-")
        year, month = int(parts[0]), int(parts[1])
        start = date(year, month, 1)
        _, last_day = monthrange(year, month)
        end = date(year, month, last_day)
    else:
        now = datetime.now()
        start = date(now.year, now.month, 1)
        _, last_day = monthrange(now.year, now.month)
        end = date(now.year, now.month, last_day)

    employees = db.query(Employee).filter(Employee.status == "在职").all()
    emp_map = {e.emp_no: e for e in employees}
    emp_accounts = set(emp_map.keys())
    if not emp_accounts:
        return []

    records = db.query(Workload).filter(
        Workload.date >= start,
        Workload.date <= end,
        Workload.account.in_(emp_accounts),
    ).all()

    team_data = {}
    for r in records:
        emp = emp_map.get(r.account)
        team = emp.team if emp and emp.team else "未知班组"
        if team not in team_data:
            team_data[team] = {"team": team, "emp_count": 0, "call_count": 0, "ticket_count": 0, "outbound_count": 0, "_people": set()}
        m = r.metrics or {}
        team_data[team]["call_count"] += m.get("呼入人工服务-人工服务-通话次数", 0) or 0
        team_data[team]["ticket_count"] += m.get("呼入人工服务-工单-生成总量", 0) or 0
        team_data[team]["outbound_count"] += m.get("呼出服务-人工呼出呼叫量", 0) or 0
        team_data[team]["_people"].add(r.account)

    result = []
    for team, data in team_data.items():
        result.append({
            "team": team,
            "emp_count": len(data["_people"]),
            "call_count": data["call_count"],
            "ticket_count": data["ticket_count"],
            "outbound_count": data["outbound_count"],
        })

    result.sort(key=lambda x: x["call_count"], reverse=True)
    return result


@router.get("/report/export")
def export_workload_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year_month: Optional[str] = None,
    team_desc: Optional[str] = None,
    team_prefix: Optional[str] = None,
    name: Optional[str] = None,
    account: Optional[str] = None,
    tenure_mode: Optional[str] = None,
    tenure_months: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """导出工作量报表 CSV"""
    require_permission(current_user, "workload_report.export")

    if year_month:
        start = datetime.strptime(f"{year_month}-01", "%Y-%m-%d").date()
        if year_month == datetime.now().strftime("%Y-%m"):
            end = datetime.now().date()
        else:
            next_month = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
            end = next_month - timedelta(days=1)
    elif start_date and end_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end = datetime.now().date()
        start = end

    query = db.query(Workload).filter(Workload.date >= start, Workload.date <= end)
    records = query.all()

    emp_accounts = {e[0] for e in db.query(Employee.emp_no).filter(Employee.status == "在职").all()}
    records = [r for r in records if r.account in emp_accounts]
    if team_desc:
        team_emp_nos = {e[0] for e in db.query(Employee.emp_no).filter(Employee.team == team_desc, Employee.status == "在职").all()}
        records = [r for r in records if r.account in team_emp_nos]
    if team_prefix:
        team_emp_nos = {e[0] for e in db.query(Employee.emp_no).filter(
            Employee.team.startswith(team_prefix), Employee.status == "在职"
        ).all()}
        records = [r for r in records if r.account in team_emp_nos]
    if name:
        emp_nos = [e[0] for e in db.query(Employee.emp_no).filter(Employee.name.ilike(f'%{name}%')).all()]
        records = [r for r in records if r.account in emp_nos]
    if account:
        records = [r for r in records if account.lower() in (r.account or '').lower()]

    if tenure_mode:
        months = tenure_months or 3
        today = datetime.now().date()
        cutoff = today - timedelta(days=months * 30)
        emp_tenure_map = {}
        for e in db.query(Employee.emp_no, Employee.hire_date).filter(Employee.status == "在职").all():
            if e.hire_date is not None:
                emp_tenure_map[e.emp_no] = e.hire_date > cutoff
            else:
                emp_tenure_map[e.emp_no] = False
        if tenure_mode == "le":
            records = [r for r in records if emp_tenure_map.get(r.account, False)]
        elif tenure_mode == "gt":
            records = [r for r in records if not emp_tenure_map.get(r.account, False)]

    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    headers = ["账号", "姓名", "工号", "班组", "日期"]
    for field in CORE_METRICS_FIELDS:
        label = field.split('-')[-1]
        headers.append(label)
    writer.writerow(headers)

    for r in records:
        emp = db.query(Employee).filter(Employee.emp_no == r.account).first()
        m = r.metrics or {}
        row = [r.account, emp.name if emp else (r.name or ''), r.emp_no or '',
               emp.team if emp else (r.team_desc or ''), r.date.isoformat()]
        for field in CORE_METRICS_FIELDS:
            val = m.get(field)
            row.append(val if val is not None else '')
        writer.writerow(row)

    filename = f"workload_report_{start}_{end}.csv"
    output.seek(0)
    log_operation(db, current_user["id"], "export_workload_report", "workloads", None, {"start_date": start.isoformat(), "end_date": end.isoformat()})
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
