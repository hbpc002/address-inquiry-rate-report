from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date, timedelta
from calendar import monthrange
import uuid
import pandas as pd
import io
import math
import csv

from app.models.database import get_db
from app.models.seamless_order import SeamlessOrder
from app.models.employee import Employee
from app.utils.logger import log_operation
from app.core.security import get_current_user, require_permission

router = APIRouter(prefix="/api/broadband", tags=["宽带营销"])

# 表头行号（0 起）：新客服无缝订单原始表第 3 行为表头
HEADER_ROW = 2


def _cell(row, mapping, name, default=""):
    col = mapping.get(name)
    if col is None:
        return default
    val = row[col]
    if isinstance(val, float) and math.isnan(val):
        return default
    if val is None:
        return default
    s = str(val).strip()
    if s in ("nan", "--", "None"):
        return default
    return s


def _parse_row(row, mapping):
    order_no = _cell(row, mapping, "新客服无缝订单号")
    if not order_no:
        return None
    order_date_str = _cell(row, mapping, "下单日期")
    try:
        order_date = datetime.strptime(order_date_str, "%Y-%m-%d").date()
    except ValueError:
        return None

    def _bool_field(name):
        return _cell(row, mapping, name)

    return {
        "order_no": order_no,
        "emp_no": _cell(row, mapping, "下单新客服工号"),
        "order_date": order_date,
        "is_completed": _bool_field("是否竣工"),
        "city": _cell(row, mapping, "地市名称"),
        "is_hour_short": _bool_field("是否1小时短单"),
        "is_excluded": _bool_field("是否剔除"),
        "is_duplicate": _bool_field("是否重复单"),
        "cb_order_no": _cell(row, mapping, "线下办理CB订单号"),
        "cb_business_no": _cell(row, mapping, "线下办理CB业务号码"),
        "cb_order_status": _cell(row, mapping, "线下办理CB订单状态"),
        "product_name": _cell(row, mapping, "最终办理产品名称"),
        "bandwidth_speed": _cell(row, mapping, "最终办理宽带速率"),
        "order_status": _cell(row, mapping, "订单状态"),
        "month": _cell(row, mapping, "月份"),
        "intention_emp_no": _cell(row, mapping, "中台意向单受理人工号"),
    }


@router.post("/orders/import", response_model=dict)
def import_orders(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "broadband.upload")

    batch = str(uuid.uuid4())[:8]
    content = file.file.read()

    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name="Sheet_0", header=None)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"无法解析Excel文件: {str(e)}")

    if len(df) <= HEADER_ROW:
        raise HTTPException(status_code=400, detail="Excel文件数据行不足")

    header_row = df.iloc[HEADER_ROW]
    mapping = {}
    for col_idx, name in enumerate(header_row):
        if pd.notna(name):
            label = str(name).strip()
            if label and label != "nan" and label not in mapping:
                mapping[label] = col_idx

    data_rows = df.iloc[HEADER_ROW + 1:]
    new_records = []
    dates_set = set()
    seen_order_no = {}

    for idx in range(len(data_rows)):
        row = data_rows.iloc[idx]
        try:
            record = _parse_row(row, mapping)
            if record is None:
                continue
            order_no = record["order_no"]
            # 同一订单号只保留首次出现，避免重复
            if order_no in seen_order_no:
                continue
            seen_order_no[order_no] = True
            dates_set.add(record["order_date"])
            new_records.append(record)
        except Exception:
            continue

    if not new_records:
        raise HTTPException(status_code=400, detail="未解析到有效数据")

    for d in dates_set:
        db.query(SeamlessOrder).filter(SeamlessOrder.order_date == d).delete(synchronize_session=False)

    if new_records:
        payload = []
        for r in new_records:
            item = dict(r)
            item["import_batch"] = batch
            payload.append(item)
        db.bulk_insert_mappings(SeamlessOrder, payload)

    db.commit()
    count = len(new_records)
    log_operation(db, current_user["id"], "import_broadband_orders", "broadband", None, {"batch": batch, "count": count})

    return {"count": count, "batch": batch}


@router.get("/orders", response_model=dict)
def get_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    import_batch: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    query = db.query(SeamlessOrder)
    if import_batch:
        query = query.filter(SeamlessOrder.import_batch == import_batch)
    if start_date:
        query = query.filter(SeamlessOrder.order_date >= datetime.strptime(start_date, "%Y-%m-%d").date())
    if end_date:
        query = query.filter(SeamlessOrder.order_date <= datetime.strptime(end_date, "%Y-%m-%d").date())
    if emp_no:
        query = query.filter(SeamlessOrder.emp_no.ilike(f"%{emp_no}%"))
    if name:
        emp_nos = [e[0] for e in db.query(Employee.emp_no).filter(
            Employee.name.ilike(f"%{name}%")
        ).all()]
        if emp_nos:
            query = query.filter(SeamlessOrder.emp_no.in_(emp_nos))
        else:
            return {"items": [], "total": 0}

    total = query.count()
    items = query.order_by(SeamlessOrder.order_date.desc(), SeamlessOrder.order_no).offset((page - 1) * limit).limit(limit).all()

    emp_map = {e.emp_no: e for e in db.query(Employee).all()}
    result = []
    for o in items:
        emp = emp_map.get(o.emp_no)
        result.append({
            "id": o.id,
            "order_no": o.order_no,
            "emp_no": o.emp_no,
            "name": emp.name if emp else "",
            "team": emp.team if emp else "",
            "order_date": o.order_date.isoformat() if o.order_date else None,
            "is_completed": o.is_completed,
            "is_excluded": o.is_excluded,
            "is_duplicate": o.is_duplicate,
            "is_hour_short": o.is_hour_short,
            "city": o.city,
            "cb_order_status": o.cb_order_status,
            "product_name": o.product_name,
            "bandwidth_speed": o.bandwidth_speed,
            "order_status": o.order_status,
            "intention_emp_no": o.intention_emp_no,
            "import_batch": o.import_batch,
        })

    return {"items": result, "total": total}


@router.delete("/orders/by-date", response_model=dict)
def delete_orders_by_date(
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "broadband.delete")
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式无效，应为 YYYY-MM-DD")
    records = db.query(SeamlessOrder).filter(SeamlessOrder.order_date == target).all()
    count = len(records)
    for r in records:
        db.delete(r)
    db.commit()
    log_operation(db, current_user["id"], "delete_broadband_orders_by_date", "broadband", None, {"date": date, "count": count})
    return {"count": count}


@router.delete("/orders/{order_id}", response_model=dict)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "broadband.delete")
    record = db.query(SeamlessOrder).filter(SeamlessOrder.id == order_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    log_operation(db, current_user["id"], "delete_broadband_order", "broadband", order_id, {"order_no": record.order_no})
    return {"message": "删除成功"}


@router.delete("/orders/import/{batch}", response_model=dict)
def delete_batch(
    batch: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "broadband.delete")
    count = db.query(SeamlessOrder).filter(SeamlessOrder.import_batch == batch).delete(synchronize_session=False)
    db.commit()
    log_operation(db, current_user["id"], "delete_broadband_import_batch", "broadband", None, {"batch": batch, "count": count})
    return {"count": count}


def _resolve_range(year_month, start_date, end_date):
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
        now = datetime.now()
        _, last_day = monthrange(now.year, now.month)
        start = date(now.year, now.month, 1)
        end = date(now.year, now.month, last_day)
    return start, end


def _extract_class(team):
    import re
    m = re.match(r"^(.+?)[\d]+组$", team or "")
    return m.group(1) if m else team


@router.get("/report", response_model=dict)
def get_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year_month: Optional[str] = None,
    city: Optional[str] = None,
    team: Optional[str] = None,
    team_prefix: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    start, end = _resolve_range(year_month, start_date, end_date)

    records = db.query(SeamlessOrder).filter(
        SeamlessOrder.order_date >= start,
        SeamlessOrder.order_date <= end,
        SeamlessOrder.is_excluded == "否",
        SeamlessOrder.is_duplicate == "否",
    ).all()

    # 按订单号去重
    by_order = {}
    for r in records:
        if r.order_no not in by_order:
            by_order[r.order_no] = r
    records = list(by_order.values())

    emp_map = {e.emp_no: e for e in db.query(Employee).filter(Employee.status == "在职").all()}

    if city:
        records = [r for r in records if r.city == city]
    if team:
        team_emp_nos = {e[0] for e in db.query(Employee.emp_no).filter(
            Employee.team == team, Employee.status == "在职"
        ).all()}
        records = [r for r in records if r.emp_no in team_emp_nos]
    if team_prefix:
        team_emp_nos = {e[0] for e in db.query(Employee.emp_no).filter(
            Employee.team.startswith(team_prefix), Employee.status == "在职"
        ).all()}
        records = [r for r in records if r.emp_no in team_emp_nos]
    if name:
        emp_nos = [e[0] for e in db.query(Employee.emp_no).filter(
            Employee.name.ilike(f"%{name}%")
        ).all()]
        records = [r for r in records if r.emp_no in emp_nos]
    if emp_no:
        records = [r for r in records if emp_no.lower() in (r.emp_no or "").lower()]

    agg = {}
    for r in records:
        emp = emp_map.get(r.emp_no)
        if not emp:
            continue
        key = emp.emp_no
        if key not in agg:
            agg[key] = {
                "emp_no": emp.emp_no,
                "name": emp.name,
                "team": emp.team or "",
                "dept": emp.dept or "",
                "role": emp.role or "",
                "class_name": _extract_class(emp.team) or "",
                "recommend": 0,
                "completed": 0,
            }
        agg[key]["recommend"] += 1
        if r.is_completed == "是":
            agg[key]["completed"] += 1

    items = []
    for key, data in agg.items():
        recommend = data["recommend"]
        completed = data["completed"]
        items.append({
            "emp_no": data["emp_no"],
            "name": data["name"],
            "team": data["team"],
            "dept": data["dept"],
            "role": data["role"],
            "class_name": data["class_name"],
            "intention_count": recommend,
            "recommend": recommend,
            "completed": completed,
            "success_rate": round(completed / recommend, 4) if recommend > 0 else 0,
        })

    items.sort(key=lambda x: (x["recommend"], x["success_rate"]), reverse=True)

    total_people = len(items)
    total_recommend = sum(i["recommend"] for i in items)
    total_completed = sum(i["completed"] for i in items)

    emp_nos_in_range = list(agg.keys())
    if emp_nos_in_range:
        teams = [row[0] for row in db.query(Employee.team).filter(
            Employee.emp_no.in_(emp_nos_in_range),
            Employee.team.isnot(None),
            Employee.team != ""
        ).distinct().all()]
        classes = list({_extract_class(t) for t in teams} - {None})
    else:
        teams = []
        classes = []
    cities = list({r.city for r in records if r.city})

    return {
        "stats": {
            "total_people": total_people,
            "total_recommend": total_recommend,
            "total_completed": total_completed,
            "avg_success_rate": round(total_completed / total_recommend, 4) if total_recommend > 0 else 0,
            "teams": teams,
            "classes": sorted(filter(None, classes)),
            "cities": cities,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
        "items": items,
    }


@router.get("/report/export")
def export_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year_month: Optional[str] = None,
    city: Optional[str] = None,
    team: Optional[str] = None,
    team_prefix: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "broadband_report.export")

    start, end = _resolve_range(year_month, start_date, end_date)

    records = db.query(SeamlessOrder).filter(
        SeamlessOrder.order_date >= start,
        SeamlessOrder.order_date <= end,
        SeamlessOrder.is_excluded == "否",
        SeamlessOrder.is_duplicate == "否",
    ).all()

    by_order = {}
    for r in records:
        if r.order_no not in by_order:
            by_order[r.order_no] = r
    records = list(by_order.values())

    emp_map = {e.emp_no: e for e in db.query(Employee).filter(Employee.status == "在职").all()}

    if city:
        records = [r for r in records if r.city == city]
    if team:
        team_emp_nos = {e[0] for e in db.query(Employee.emp_no).filter(
            Employee.team == team, Employee.status == "在职"
        ).all()}
        records = [r for r in records if r.emp_no in team_emp_nos]
    if team_prefix:
        team_emp_nos = {e[0] for e in db.query(Employee.emp_no).filter(
            Employee.team.startswith(team_prefix), Employee.status == "在职"
        ).all()}
        records = [r for r in records if r.emp_no in team_emp_nos]
    if name:
        emp_nos = [e[0] for e in db.query(Employee.emp_no).filter(
            Employee.name.ilike(f"%{name}%")
        ).all()]
        records = [r for r in records if r.emp_no in emp_nos]
    if emp_no:
        records = [r for r in records if emp_no.lower() in (r.emp_no or "").lower()]

    agg = {}
    for r in records:
        emp = emp_map.get(r.emp_no)
        if not emp:
            continue
        if emp.emp_no not in agg:
            agg[emp.emp_no] = {"emp_no": emp.emp_no, "name": emp.name, "team": emp.team or "",
                               "dept": emp.dept or "", "recommend": 0, "completed": 0}
        agg[emp.emp_no]["recommend"] += 1
        if r.is_completed == "是":
            agg[emp.emp_no]["completed"] += 1

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["工号", "姓名", "班组", "部门", "意向单数量", "推荐量", "成功推荐", "成功率(%)"])
    for key, d in agg.items():
        rate = round(d["completed"] / d["recommend"] * 100, 2) if d["recommend"] > 0 else 0
        writer.writerow([d["emp_no"], d["name"], d["team"], d["dept"],
                         d["recommend"], d["recommend"], d["completed"], rate])

    filename = f"broadband_report_{start}_{end}.csv"
    output.seek(0)
    log_operation(db, current_user["id"], "export_broadband_report", "broadband", None, {"start_date": start.isoformat(), "end_date": end.isoformat()})
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )