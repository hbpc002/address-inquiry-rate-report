from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from typing import Optional
from datetime import datetime, date
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
    "人工服务-满意度-非常满意量",
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
]


@router.get("", response_model=WorkloadListResponse)
def get_workloads(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    import_batch: Optional[str] = None,
    workload_date: Optional[str] = None,
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
    if name:
        query = query.filter(Workload.name.ilike(f'%{name}%'))
    if account:
        query = query.filter(Workload.account == account)

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

            emp = db.query(Employee).filter(Employee.emp_no == account_val).first()
            if not emp:
                continue
            name_val = emp.name or name_val
            team_desc_val = emp.team or ''

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
    name: Optional[str] = None,
    account: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    from datetime import timedelta

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

    if province:
        records = [r for r in records if r.province == province]
    if team_desc:
        records = [r for r in records if team_desc.lower() in (r.team_desc or '').lower()]
    if name:
        records = [r for r in records if name.lower() in (r.name or '').lower()]
    if account:
        records = [r for r in records if account.lower() in (r.account or '').lower()]

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

        items.append(WorkloadReportItem(
            account=data["account"],
            name=data["name"],
            emp_no=data["emp_no"],
            team_desc=data["team_desc"],
            province=data["province"],
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
    teams = list(set(r.team_desc for r in records if r.team_desc))

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
