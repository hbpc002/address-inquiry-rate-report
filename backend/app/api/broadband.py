from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date, timedelta
from calendar import monthrange
import uuid
import json
import pandas as pd
import io
import math
import csv

from app.models.database import get_db
from app.models.seamless_order import SeamlessOrder
from app.models.employee import Employee
from app.models.salary_config import SalaryConfig
from app.utils.logger import log_operation
from app.core.security import get_current_user, require_permission
from app.core.data_scope import (
    apply_legacy_broadband_scope,
    apply_legacy_employee_scope,
    has_legacy_all_scope,
)

router = APIRouter(prefix="/api/broadband", tags=["宽带营销"])

DEFAULT_POINTS_FORMULA = {"recommend_coeff": 2, "completed_coeff": 10}


def _points_formula(db: Session) -> dict:
    row = db.query(SalaryConfig).filter(SalaryConfig.rule_key == "points_formula").first()
    if row:
        data = json.loads(row.rule_data)
    else:
        data = dict(DEFAULT_POINTS_FORMULA)
    return {
        "recommend_coeff": float(data.get("recommend_coeff") or DEFAULT_POINTS_FORMULA["recommend_coeff"]),
        "completed_coeff": float(data.get("completed_coeff") or DEFAULT_POINTS_FORMULA["completed_coeff"]),
    }


def _calc_points(recommend, completed, formula) -> int:
    return round(recommend * formula["recommend_coeff"] + completed * formula["completed_coeff"])

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


def _parse_finish_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    s = str(value).strip()
    if not s or s in ("nan", "--", "None"):
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_row(row, mapping):
    order_no = _cell(row, mapping, "新客服无缝订单号")
    if not order_no:
        return None
    order_date_str = _cell(row, mapping, "下单日期")
    try:
        order_date = datetime.strptime(order_date_str, "%Y-%m-%d").date()
    except ValueError:
        return None
    finish_raw = _cell(row, mapping, "线下办理CB竣工时间") or _cell(row, mapping, "竣工日期")

    def _bool_field(name):
        return _cell(row, mapping, name)

    return {
        "order_no": order_no,
        "emp_no": _cell(row, mapping, "下单新客服工号"),
        "order_date": order_date,
        "finish_date": _parse_finish_date(finish_raw),
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

    if not has_legacy_all_scope(current_user):
        legacy_emp_nos = {
            e[0] for e in apply_legacy_employee_scope(
                db.query(Employee.emp_no).filter(Employee.status == "在职"), current_user
            ).all()
        }
        new_records = [r for r in new_records if r.get("emp_no") in legacy_emp_nos]

    if not new_records:
        raise HTTPException(status_code=400, detail="未解析到热线运营组范围内的有效数据")

    for d in dates_set:
        apply_legacy_broadband_scope(
            db.query(SeamlessOrder).filter(SeamlessOrder.order_date == d), current_user
        ).delete(synchronize_session=False)

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
    query = apply_legacy_broadband_scope(db.query(SeamlessOrder), current_user)
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
            "finish_date": o.finish_date.isoformat() if o.finish_date else None,
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
    records = apply_legacy_broadband_scope(
        db.query(SeamlessOrder).filter(SeamlessOrder.order_date == target), current_user
    ).all()
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
    record = apply_legacy_broadband_scope(
        db.query(SeamlessOrder).filter(SeamlessOrder.id == order_id), current_user
    ).first()
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
    count = apply_legacy_broadband_scope(
        db.query(SeamlessOrder).filter(SeamlessOrder.import_batch == batch), current_user
    ).delete(synchronize_session=False)
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

    records = apply_legacy_broadband_scope(
        db.query(SeamlessOrder).filter(
            SeamlessOrder.order_date >= start,
            SeamlessOrder.order_date <= end,
            SeamlessOrder.is_excluded == "否",
            SeamlessOrder.is_duplicate == "否",
        ),
        current_user,
    ).all()

    # 按订单号去重
    by_order = {}
    for r in records:
        if r.order_no not in by_order:
            by_order[r.order_no] = r
    records = list(by_order.values())

    emp_map = {
        e.emp_no: e for e in apply_legacy_employee_scope(
            db.query(Employee).filter(Employee.status == "在职"), current_user
        ).all()
    }

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

    formula = _points_formula(db)
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
            "recommend": recommend,
            "completed": completed,
            "success_rate": round(completed / recommend, 4) if recommend > 0 else 0,
            "points": _calc_points(recommend, completed, formula),
        })

    items.sort(key=lambda x: (x["recommend"], x["success_rate"]), reverse=True)

    total_people = len(items)
    total_recommend = sum(i["recommend"] for i in items)
    total_completed = sum(i["completed"] for i in items)
    total_points = sum(i["points"] for i in items)

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
            "total_points": total_points,
            "avg_success_rate": round(total_completed / total_recommend, 4) if total_recommend > 0 else 0,
            "teams": teams,
            "classes": sorted(filter(None, classes)),
            "cities": cities,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
        "items": items,
    }


def _employee_report_map(db, current_user, team=None, team_prefix=None, name=None, emp_no=None):
    query = apply_legacy_employee_scope(
        db.query(Employee).filter(Employee.status == "在职"), current_user
    )
    if team:
        query = query.filter(Employee.team == team)
    if team_prefix:
        query = query.filter(Employee.team.startswith(team_prefix))
    if name:
        query = query.filter(Employee.name.ilike(f"%{name}%"))
    if emp_no:
        query = query.filter(Employee.emp_no.ilike(f"%{emp_no}%"))
    return {e.emp_no: e for e in query.all()}


def _dedupe_by_order(records):
    by_order = {}
    for r in records:
        if r.order_no not in by_order:
            by_order[r.order_no] = r
    return list(by_order.values())


def _compare_records(db, current_user, date_field, start, end, emp_nos, city, completed_only=False):
    if not emp_nos:
        return []
    query = apply_legacy_broadband_scope(
        db.query(SeamlessOrder).filter(
            date_field >= start,
            date_field <= end,
            SeamlessOrder.is_excluded == "否",
            SeamlessOrder.is_duplicate == "否",
            SeamlessOrder.emp_no.in_(emp_nos),
        ),
        current_user,
    )
    if completed_only:
        query = query.filter(SeamlessOrder.is_completed == "是")
    records = query.all()
    if city:
        records = [r for r in records if r.city == city]
    return _dedupe_by_order(records)


def _compare_report_data(db, current_user, start, end, city=None, team=None,
                         team_prefix=None, name=None, emp_no=None):
    emp_map = _employee_report_map(
        db, current_user, team=team, team_prefix=team_prefix, name=name, emp_no=emp_no
    )
    emp_nos = list(emp_map.keys())

    order_records = _compare_records(
        db, current_user, SeamlessOrder.order_date, start, end, emp_nos, city
    )
    finish_records = _compare_records(
        db, current_user, SeamlessOrder.finish_date, start, end, emp_nos, city,
        completed_only=True,
    )

    agg = {}

    def _ensure(emp):
        if emp.emp_no not in agg:
            agg[emp.emp_no] = {
                "emp_no": emp.emp_no,
                "name": emp.name,
                "team": emp.team or "",
                "dept": emp.dept or "",
                "role": emp.role or "",
                "class_name": _extract_class(emp.team) or "",
                "recommend": 0,
                "completed_by_order": 0,
                "completed_by_finish": 0,
            }
        return agg[emp.emp_no]

    for r in order_records:
        emp = emp_map.get(r.emp_no)
        if not emp:
            continue
        data = _ensure(emp)
        data["recommend"] += 1
        if r.is_completed == "是":
            data["completed_by_order"] += 1

    for r in finish_records:
        emp = emp_map.get(r.emp_no)
        if not emp:
            continue
        _ensure(emp)["completed_by_finish"] += 1

    formula = _points_formula(db)
    items = []
    for data in agg.values():
        recommend = data["recommend"]
        completed_by_order = data["completed_by_order"]
        completed_by_finish = data["completed_by_finish"]
        items.append({
            **data,
            "diff": completed_by_finish - completed_by_order,
            "success_rate_by_order": round(completed_by_order / recommend, 4) if recommend > 0 else 0,
            "success_rate_by_finish": round(completed_by_finish / recommend, 4) if recommend > 0 else 0,
            "points_by_order": _calc_points(recommend, completed_by_order, formula),
            "points_by_finish": _calc_points(recommend, completed_by_finish, formula),
        })

    items.sort(key=lambda x: (x["recommend"], x["completed_by_finish"]), reverse=True)

    total_recommend = sum(i["recommend"] for i in items)
    total_completed_by_order = sum(i["completed_by_order"] for i in items)
    total_completed_by_finish = sum(i["completed_by_finish"] for i in items)
    cities = sorted({r.city for r in order_records + finish_records if r.city})
    teams = sorted({i["team"] for i in items if i["team"]})
    classes = sorted({_extract_class(i["team"]) for i in items if _extract_class(i["team"])})

    return {
        "stats": {
            "total_people": len(items),
            "total_recommend": total_recommend,
            "total_completed_by_order": total_completed_by_order,
            "total_completed_by_finish": total_completed_by_finish,
            "total_diff": total_completed_by_finish - total_completed_by_order,
            "total_points_by_order": sum(i["points_by_order"] for i in items),
            "total_points_by_finish": sum(i["points_by_finish"] for i in items),
            "avg_success_rate_by_order": round(total_completed_by_order / total_recommend, 4) if total_recommend > 0 else 0,
            "avg_success_rate_by_finish": round(total_completed_by_finish / total_recommend, 4) if total_recommend > 0 else 0,
            "teams": teams,
            "classes": classes,
            "cities": cities,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        },
        "items": items,
    }


@router.get("/report/compare", response_model=dict)
def get_compare_report(
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
    return _compare_report_data(
        db, current_user, start, end, city=city, team=team,
        team_prefix=team_prefix, name=name, emp_no=emp_no,
    )


@router.get("/report/compare/export")
def export_compare_report(
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
    data = _compare_report_data(
        db, current_user, start, end, city=city, team=team,
        team_prefix=team_prefix, name=name, emp_no=emp_no,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "工号", "姓名", "班组", "部门", "推荐量(按下单日期)",
        "成功推荐(按下单日期)", "成功推荐(按竣工日期)", "差异",
        "下单口径成功率(%)", "竣工口径成功率(%)",
        "下单口径积分", "竣工口径积分",
    ])
    for d in data["items"]:
        writer.writerow([
            d["emp_no"], d["name"], d["team"], d["dept"], d["recommend"],
            d["completed_by_order"], d["completed_by_finish"], d["diff"],
            round(d["success_rate_by_order"] * 100, 2),
            round(d["success_rate_by_finish"] * 100, 2),
            d["points_by_order"], d["points_by_finish"],
        ])

    filename = f"broadband_compare_{start}_{end}.csv"
    output.seek(0)
    log_operation(db, current_user["id"], "export_broadband_compare", "broadband", None, {
        "start_date": start.isoformat(), "end_date": end.isoformat(),
    })
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


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

    records = apply_legacy_broadband_scope(
        db.query(SeamlessOrder).filter(
            SeamlessOrder.order_date >= start,
            SeamlessOrder.order_date <= end,
            SeamlessOrder.is_excluded == "否",
            SeamlessOrder.is_duplicate == "否",
        ),
        current_user,
    ).all()

    by_order = {}
    for r in records:
        if r.order_no not in by_order:
            by_order[r.order_no] = r
    records = list(by_order.values())

    emp_map = {
        e.emp_no: e for e in apply_legacy_employee_scope(
            db.query(Employee).filter(Employee.status == "在职"), current_user
        ).all()
    }

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
    formula = _points_formula(db)
    writer.writerow(["工号", "姓名", "班组", "部门", "推荐量", "成功推荐", "成功率(%)", "积分"])
    for key, d in agg.items():
        rate = round(d["completed"] / d["recommend"] * 100, 2) if d["recommend"] > 0 else 0
        writer.writerow([d["emp_no"], d["name"], d["team"], d["dept"],
                         d["recommend"], d["completed"], rate,
                         _calc_points(d["recommend"], d["completed"], formula)])

    filename = f"broadband_report_{start}_{end}.csv"
    output.seek(0)
    log_operation(db, current_user["id"], "export_broadband_report", "broadband", None, {"start_date": start.isoformat(), "end_date": end.isoformat()})
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )