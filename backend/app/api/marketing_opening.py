import csv
import io
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.data_scope import (
    apply_marketing_opening_scope,
    build_department_group_context,
    require_all_scope,
)
from app.core.security import get_current_user, require_permission
from app.models.database import get_db
from app.models.employee import Employee
from app.models.marketing_opening import MarketingOpeningRecord
from app.utils.logger import log_operation

router = APIRouter(prefix="/api/marketing-openings", tags=["开口率"])

UNASSIGNED_TEAM = "未匹配班组"
UNASSIGNED_EMP = "未匹配工号"

OPENING_FIELDS = [
    "active_overlay",
    "opened_overlay",
    "active_broadband",
    "opened_broadband",
    "active_mobile_new",
    "opened_mobile_new",
    "active_terminal",
    "opened_terminal",
    "active_package",
    "opened_package",
]
OPENING_COLUMNS = [
    {"key": "active_overlay", "product": "叠加包", "action": "主动", "label": "叠加包主动开口量"},
    {"key": "opened_overlay", "product": "叠加包", "action": "已开口", "label": "叠加包已开口量"},
    {"key": "active_broadband", "product": "宽带", "action": "主动", "label": "宽带主动开口量"},
    {"key": "opened_broadband", "product": "宽带", "action": "已开口", "label": "宽带已开口量"},
    {"key": "active_mobile_new", "product": "移网新装", "action": "主动", "label": "移网新装主动开口量"},
    {"key": "opened_mobile_new", "product": "移网新装", "action": "已开口", "label": "移网新装已开口量"},
    {"key": "active_terminal", "product": "终端", "action": "主动", "label": "终端主动开口量"},
    {"key": "opened_terminal", "product": "终端", "action": "已开口", "label": "终端已开口量"},
    {"key": "active_package", "product": "套餐", "action": "主动", "label": "套餐主动开口量"},
    {"key": "opened_package", "product": "套餐", "action": "已开口", "label": "套餐已开口量"},
]

FIELD_ALIASES = {
    "contact_id": ("接触记录号", "接触记录ID", "contact_id"),
    "record_time": ("录音时间", "通话时间", "record_time"),
    "emp_no": ("员工工号", "工号", "emp_no"),
    "emp_name": ("员工姓名", "姓名", "emp_name"),
    "source_team": ("班组", "源表班组", "team"),
    "active_overlay": ("坐席主动开口营销叠加包",),
    "opened_overlay": ("坐席已开口营销叠加包",),
    "active_broadband": ("坐席主动开口营销宽带",),
    "opened_broadband": ("坐席已开口营销宽带",),
    "active_mobile_new": ("坐席主动开口营销移网新装",),
    "opened_mobile_new": ("坐席已开口营销移网新装",),
    "active_terminal": ("坐席主动开口营销终端",),
    "opened_terminal": ("坐席已开口营销终端",),
    "active_package": ("坐席主动开口营销套餐",),
    "opened_package": ("坐席已开口营销套餐",),
    "five_products_opened": ("五大产品已开口",),
}
REQUIRED_FIELDS = {"contact_id", "record_time", "emp_no", "five_products_opened"}


def _norm_label(value: Any) -> str:
    return str(value).replace("\ufeff", "").strip().lower()


def _text(value: Any) -> str:
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if text.lower() in {"nan", "none", "nat", "--", "null"}:
        return ""
    return text


def _cell(values: List[Any], mapping: Dict[str, int], field: str) -> str:
    idx = mapping.get(field)
    if idx is None or idx >= len(values):
        return ""
    return _text(values[idx])


def _is_yes(value: Any) -> bool:
    return _text(value).strip().lower() in {"是", "已开口", "true", "yes", "y", "1"}


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    text = _text(value)
    if not text:
        return None
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.to_pydatetime()


def _read_raw(content: bytes):
    try:
        raw = pd.read_excel(io.BytesIO(content), header=None, dtype=object)
        return raw
    except Exception:
        pass

    last_error = None
    for encoding in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            return pd.read_csv(io.BytesIO(content), header=None, dtype=object, encoding=encoding)
        except Exception as exc:
            last_error = exc
    raise HTTPException(status_code=400, detail=f"无法解析文件: {last_error}")


def _read_opening(content: bytes):
    raw = _read_raw(content)
    if raw.empty:
        raise HTTPException(status_code=400, detail="文件为空")

    alias_lookup = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            alias_lookup[_norm_label(alias)] = field

    best_idx = 0
    best_hits = 0
    best_fields = set()
    for idx in range(min(10, len(raw))):
        labels = [_norm_label(v) for v in raw.iloc[idx].tolist()]
        fields = {alias_lookup[label] for label in labels if label in alias_lookup}
        if len(fields) > best_hits:
            best_idx = idx
            best_hits = len(fields)
            best_fields = fields

    missing = REQUIRED_FIELDS - best_fields
    if missing:
        raise HTTPException(
            status_code=400,
            detail="未识别到有效的开口数据表头，需包含：接触记录号、录音时间、员工工号、五大产品已开口",
        )

    mapping = {}
    seen_fields = set()
    for col_idx, value in enumerate(raw.iloc[best_idx].tolist()):
        field = alias_lookup.get(_norm_label(value))
        if field and field not in seen_fields:
            mapping[field] = col_idx
            seen_fields.add(field)

    return raw.iloc[best_idx + 1 :], mapping


def _serialize_record(record: MarketingOpeningRecord, emp: Optional[Employee]) -> Dict[str, Any]:
    data = {
        "id": record.id,
        "contact_id": record.contact_id,
        "record_time": record.record_time.strftime("%Y-%m-%d %H:%M:%S") if record.record_time else None,
        "record_date": record.record_date.isoformat() if record.record_date else None,
        "emp_no": record.emp_no or "",
        "emp_name": record.emp_name or (emp.name if emp else ""),
        "name": emp.name if emp else (record.emp_name or ""),
        "team": record.source_team or "",
        "system_team": emp.team if emp else "",
        "import_batch": record.import_batch or "",
        "five_products_opened": "是" if record.five_products_opened else "否",
    }
    for field in OPENING_FIELDS:
        data[field] = "是" if getattr(record, field) else "否"
    return data


def _date_param(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式无效，应为 YYYY-MM-DD")


def _resolve_range(year_month: Optional[str], start_date: Optional[str], end_date: Optional[str]):
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
    elif start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = start
    elif end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        start = end
    else:
        now = datetime.now()
        _, last_day = monthrange(now.year, now.month)
        start = date(now.year, now.month, 1)
        end = date(now.year, now.month, last_day)
    return start, end


def _norm_emp_no(value: Any) -> str:
    return str(value or "").strip().upper()


def _emp_map(db: Session) -> Dict[str, Employee]:
    result = {}
    for emp in db.query(Employee).all():
        key = _norm_emp_no(emp.emp_no)
        if key:
            result.setdefault(key, emp)
    return result


def _extract_class(team: Optional[str]) -> str:
    import re

    match = re.match(r"^(.+?)[\d]+组$", (team or "").strip())
    return match.group(1) if match else (team or "").strip()


def _record_team(record: MarketingOpeningRecord, emp: Optional[Employee]) -> str:
    if emp and emp.team:
        return emp.team
    return record.source_team or UNASSIGNED_TEAM


def _record_name(record: MarketingOpeningRecord, emp: Optional[Employee]) -> str:
    return emp.name if emp else (record.emp_name or "")


def _record_dept(record: MarketingOpeningRecord, emp: Optional[Employee]) -> str:
    return emp.dept if emp else ""


def _opening_query(
    db: Session,
    current_user: dict,
    start: Optional[date] = None,
    end: Optional[date] = None,
    import_batch: Optional[str] = None,
    emp_no: Optional[str] = None,
    name: Optional[str] = None,
    team: Optional[str] = None,
    five_products_opened: Optional[str] = None,
):
    query = apply_marketing_opening_scope(
        db.query(MarketingOpeningRecord), db, current_user, "marketing_opening"
    )
    if start:
        query = query.filter(MarketingOpeningRecord.record_date >= start)
    if end:
        query = query.filter(MarketingOpeningRecord.record_date <= end)
    if import_batch:
        query = query.filter(MarketingOpeningRecord.import_batch == import_batch)
    if emp_no:
        query = query.filter(MarketingOpeningRecord.emp_no.ilike(f"%{emp_no}%"))
    if name:
        emp_nos = [
            row[0]
            for row in db.query(Employee.emp_no).filter(Employee.name.ilike(f"%{name}%")).all()
        ]
        conditions = [MarketingOpeningRecord.emp_name.ilike(f"%{name}%")]
        if emp_nos:
            conditions.append(MarketingOpeningRecord.emp_no.in_(emp_nos))
        query = query.filter(or_(*conditions))
    if team:
        emp_nos = [
            row[0]
            for row in db.query(Employee.emp_no).filter(Employee.team == team).all()
        ]
        conditions = [MarketingOpeningRecord.source_team == team]
        if emp_nos:
            conditions.append(MarketingOpeningRecord.emp_no.in_(emp_nos))
        query = query.filter(or_(*conditions))
    if five_products_opened in ("是", "否"):
        query = query.filter(
            MarketingOpeningRecord.five_products_opened.is_(five_products_opened == "是")
        )
    return query


@router.post("/import", response_model=dict)
def import_openings(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_opening.upload")

    batch = uuid.uuid4().hex[:8]
    content = file.file.read()
    data, mapping = _read_opening(content)

    records: Dict[str, Dict[str, Any]] = {}
    skipped = 0
    dates = set()
    for pos in range(len(data)):
        values = data.iloc[pos].tolist()
        try:
            contact_id = _cell(values, mapping, "contact_id")
            record_time = _parse_datetime(
                values[mapping["record_time"]] if "record_time" in mapping else None
            )
            emp_no = _cell(values, mapping, "emp_no").strip()
            if not contact_id or not record_time or not emp_no:
                skipped += 1
                continue
            record_date = record_time.date()
            flags = {field: _is_yes(_cell(values, mapping, field)) for field in OPENING_FIELDS}
            flags["five_products_opened"] = _is_yes(
                _cell(values, mapping, "five_products_opened")
            )
            record = records.get(contact_id)
            if record is None:
                record = {
                    "contact_id": contact_id,
                    "record_time": record_time,
                    "record_date": record_date,
                    "emp_no": emp_no,
                    "emp_name": _cell(values, mapping, "emp_name"),
                    "source_team": _cell(values, mapping, "source_team"),
                    "import_batch": batch,
                    **flags,
                }
                records[contact_id] = record
                dates.add(record_date)
            else:
                skipped += 1
                for field, value in flags.items():
                    record[field] = bool(record[field] or value)
        except Exception:
            skipped += 1

    if not records:
        raise HTTPException(status_code=400, detail="未解析到有效数据")

    db.query(MarketingOpeningRecord).filter(
        MarketingOpeningRecord.record_date.in_(sorted(dates))
    ).delete(synchronize_session=False)
    db.bulk_insert_mappings(MarketingOpeningRecord, list(records.values()))
    db.commit()
    log_operation(
        db,
        current_user["id"],
        "import_marketing_openings",
        "marketing_opening",
        None,
        {
            "batch": batch,
            "count": len(records),
            "dates": [d.isoformat() for d in sorted(dates)],
        },
    )
    return {
        "count": len(records),
        "skipped": skipped,
        "batch": batch,
        "dates": [d.isoformat() for d in sorted(dates)],
        "source": "大模型质检台",
    }


@router.get("", response_model=dict)
def get_openings(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    import_batch: Optional[str] = None,
    emp_no: Optional[str] = None,
    name: Optional[str] = None,
    team: Optional[str] = None,
    five_products_opened: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_opening.view")
    query = _opening_query(
        db,
        current_user,
        _date_param(start_date),
        _date_param(end_date),
        import_batch,
        emp_no,
        name,
        team,
        five_products_opened,
    )
    total = query.count()
    items = query.order_by(
        MarketingOpeningRecord.record_date.desc(),
        MarketingOpeningRecord.record_time.desc(),
        MarketingOpeningRecord.id.desc(),
    ).offset((page - 1) * limit).limit(limit).all()
    emps = _emp_map(db)
    return {
        "items": [_serialize_record(item, emps.get(_norm_emp_no(item.emp_no))) for item in items],
        "total": total,
    }


@router.get("/export")
def export_openings(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    import_batch: Optional[str] = None,
    emp_no: Optional[str] = None,
    name: Optional[str] = None,
    team: Optional[str] = None,
    five_products_opened: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_opening.export")
    items = _opening_query(
        db,
        current_user,
        _date_param(start_date),
        _date_param(end_date),
        import_batch,
        emp_no,
        name,
        team,
        five_products_opened,
    ).order_by(
        MarketingOpeningRecord.record_date.desc(),
        MarketingOpeningRecord.record_time.desc(),
        MarketingOpeningRecord.id.desc(),
    ).all()
    emps = _emp_map(db)
    rows = [_serialize_record(item, emps.get(_norm_emp_no(item.emp_no))) for item in items]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["接触记录号", "录音时间", "员工工号", "姓名", "源表班组", "系统班组"]
        + [column["label"] for column in OPENING_COLUMNS]
        + ["五大产品已开口", "批次"]
    )
    for row in rows:
        writer.writerow(
            [
                row["contact_id"],
                row["record_time"] or "",
                row["emp_no"],
                row["name"],
                row["team"],
                row["system_team"],
            ]
            + [row[column["key"]] for column in OPENING_COLUMNS]
            + [row["five_products_opened"], row["import_batch"]]
        )

    start = _date_param(start_date)
    end = _date_param(end_date)
    filename = f"开口率明细_{start or '全部'}_{end or '全部'}.csv"
    encoded = quote(filename)
    log_operation(
        db,
        current_user["id"],
        "export_marketing_openings",
        "marketing_opening",
        None,
        {"count": len(rows), "start_date": start_date, "end_date": end_date},
    )
    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.delete("/by-date", response_model=dict)
def delete_openings_by_date(
    date: str = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_opening.delete")
    require_all_scope(current_user, "仅全部数据权限的账号可删除开口数据", "marketing_opening")
    target = _date_param(date)
    count = (
        db.query(MarketingOpeningRecord)
        .filter(MarketingOpeningRecord.record_date == target)
        .delete(synchronize_session=False)
    )
    db.commit()
    log_operation(
        db,
        current_user["id"],
        "delete_marketing_openings_by_date",
        "marketing_opening",
        None,
        {"date": date, "count": count},
    )
    return {"count": count}


@router.delete("/import/{batch}", response_model=dict)
def delete_openings_batch(
    batch: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_opening.delete")
    require_all_scope(current_user, "仅全部数据权限的账号可删除开口数据", "marketing_opening")
    count = (
        db.query(MarketingOpeningRecord)
        .filter(MarketingOpeningRecord.import_batch == batch)
        .delete(synchronize_session=False)
    )
    db.commit()
    log_operation(
        db,
        current_user["id"],
        "delete_marketing_openings_batch",
        "marketing_opening",
        None,
        {"batch": batch, "count": count},
    )
    return {"count": count}


@router.delete("/{record_id}", response_model=dict)
def delete_opening(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_opening.delete")
    require_all_scope(current_user, "仅全部数据权限的账号可删除开口数据", "marketing_opening")
    record = db.query(MarketingOpeningRecord).filter(MarketingOpeningRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    log_operation(
        db,
        current_user["id"],
        "delete_marketing_opening",
        "marketing_opening",
        record_id,
        {"contact_id": record.contact_id},
    )
    return {"message": "删除成功"}


def _merge_records(records: List[MarketingOpeningRecord]) -> List[MarketingOpeningRecord]:
    merged: Dict[str, MarketingOpeningRecord] = {}
    for record in records:
        key = record.contact_id or f"id:{record.id}"
        current = merged.get(key)
        if current is None:
            merged[key] = record
            continue
        for field in OPENING_FIELDS + ["five_products_opened"]:
            setattr(current, field, bool(getattr(current, field) or getattr(record, field)))
    return list(merged.values())


def _record_matches(
    record: MarketingOpeningRecord,
    emp: Optional[Employee],
    dept: str,
    department_group: str,
    team: str,
    class_name: str,
    name: str,
    emp_no: str,
    resolve_dept_group,
) -> bool:
    record_team = _record_team(record, emp)
    record_dept = _record_dept(record, emp)
    if dept and record_dept != dept:
        return False
    if department_group and resolve_dept_group(record_dept) != department_group:
        return False
    if team and record_team != team:
        return False
    if class_name and _extract_class(record_team) != class_name:
        return False
    if name:
        target = _record_name(record, emp)
        if name.lower() not in target.lower():
            return False
    if emp_no and emp_no.lower() not in (record.emp_no or "").lower():
        return False
    return True


def _new_opening_bucket() -> Dict[str, Any]:
    bucket = {
        "contacts": set(),
        "opened_contacts": set(),
    }
    for field in OPENING_FIELDS:
        bucket[field] = set()
    return bucket


def _opening_bucket_add(bucket: Dict[str, Any], record: MarketingOpeningRecord):
    contact_id = record.contact_id
    bucket["contacts"].add(contact_id)
    if record.five_products_opened:
        bucket["opened_contacts"].add(contact_id)
    for field in OPENING_FIELDS:
        if getattr(record, field):
            bucket[field].add(contact_id)


def _finalize_opening_bucket(bucket: Dict[str, Any]) -> Dict[str, Any]:
    contact_count = len(bucket["contacts"])
    opened_count = len(bucket["opened_contacts"])
    data = {
        "contact_count": contact_count,
        "opened_count": opened_count,
        "opening_rate": round(opened_count / contact_count, 4) if contact_count else None,
    }
    for column in OPENING_COLUMNS:
        data[column["key"]] = len(bucket[column["key"]])
    return data


def _compute_opening_report(
    db: Session,
    start: date,
    end: date,
    filters: Dict[str, Any],
    current_user: dict,
) -> Dict[str, Any]:
    query = apply_marketing_opening_scope(
        db.query(MarketingOpeningRecord).filter(
            MarketingOpeningRecord.record_date >= start,
            MarketingOpeningRecord.record_date <= end,
        ),
        db,
        current_user,
        "marketing_opening_report",
    )
    opened_filter = filters.get("five_products_opened") or ""
    if opened_filter in ("是", "否"):
        query = query.filter(
            MarketingOpeningRecord.five_products_opened.is_(opened_filter == "是")
        )

    all_records = _merge_records(query.all())
    emps = _emp_map(db)
    department_group_names, resolve_dept_group = build_department_group_context(db)

    all_teams = set()
    all_classes = set()
    all_people = set()
    for record in all_records:
        emp = emps.get(_norm_emp_no(record.emp_no))
        team = _record_team(record, emp)
        all_teams.add(team)
        class_name = _extract_class(team)
        if class_name:
            all_classes.add(class_name)
        if record.emp_no:
            all_people.add(record.emp_no)

    dept = (filters.get("dept") or "").strip()
    department_group = (filters.get("department_group") or "").strip()
    team = filters.get("team") or ""
    class_name = filters.get("class_name") or ""
    name = filters.get("name") or ""
    emp_no = filters.get("emp_no") or ""

    records = []
    for record in all_records:
        emp = emps.get(_norm_emp_no(record.emp_no))
        if not _record_matches(
            record,
            emp,
            dept,
            department_group,
            team,
            class_name,
            name,
            emp_no,
            resolve_dept_group,
        ):
            continue
        records.append((record, emp))

    employees: Dict[str, Dict[str, Any]] = {}
    teams: Dict[tuple, Dict[str, Any]] = {}
    classes: Dict[tuple, Dict[str, Any]] = {}
    days: Dict[str, Dict[str, Any]] = {}
    total_bucket = _new_opening_bucket()

    for record, emp in records:
        emp_key = record.emp_no or UNASSIGNED_EMP
        record_team = _record_team(record, emp)
        record_dept = _record_dept(record, emp)
        record_dept_group = resolve_dept_group(record_dept)
        record_class = _extract_class(record_team)

        employee_bucket = employees.setdefault(
            emp_key,
            {
                **_new_opening_bucket(),
                "kf_id": record.emp_no or "",
                "name": _record_name(record, emp),
                "team": record_team,
                "dept": record_dept,
                "dept_group": record_dept_group,
                "class_name": record_class,
            },
        )
        _opening_bucket_add(employee_bucket, record)

        team_bucket = teams.setdefault(
            (record_dept, record_dept_group, record_team),
            {
                **_new_opening_bucket(),
                "dept": record_dept,
                "dept_group": record_dept_group,
                "team": record_team,
                "people": set(),
            },
        )
        _opening_bucket_add(team_bucket, record)
        team_bucket["people"].add(emp_key)

        class_bucket = classes.setdefault(
            (record_dept, record_dept_group, record_class),
            {
                **_new_opening_bucket(),
                "dept": record_dept,
                "dept_group": record_dept_group,
                "class_name": record_class,
                "people": set(),
            },
        )
        _opening_bucket_add(class_bucket, record)
        class_bucket["people"].add(emp_key)

        day_key = record.record_date.isoformat() if record.record_date else ""
        day_bucket = days.setdefault(
            day_key, {**_new_opening_bucket(), "date": day_key, "people": set()}
        )
        _opening_bucket_add(day_bucket, record)
        day_bucket["people"].add(emp_key)

        _opening_bucket_add(total_bucket, record)

    def finalize_items(mapping, extra=None):
        result = []
        for key, bucket in mapping.items():
            item = _finalize_opening_bucket(bucket)
            if extra:
                extra(item, bucket, key)
            result.append(item)
        result.sort(
            key=lambda item: (item.get("contact_count", 0), item.get("opened_count", 0)),
            reverse=True,
        )
        return result

    def employee_extra(item, bucket, _key):
        for field in ("kf_id", "name", "team", "dept", "dept_group", "class_name"):
            item[field] = bucket.get(field, "")

    def team_extra(item, bucket, _key):
        item["dept"] = bucket.get("dept", "")
        item["dept_group"] = bucket.get("dept_group", "")
        item["team"] = bucket.get("team", "")
        item["people"] = len(bucket.get("people") or set())

    def class_extra(item, bucket, _key):
        item["dept"] = bucket.get("dept", "")
        item["dept_group"] = bucket.get("dept_group", "")
        item["class_name"] = bucket.get("class_name", "")
        item["people"] = len(bucket.get("people") or set())

    def day_extra(item, bucket, _key):
        item["date"] = bucket.get("date", "")
        item["people"] = len(bucket.get("people") or set())

    employee_items = finalize_items(employees, employee_extra)
    employee_items.sort(
        key=lambda item: (item.get("contact_count", 0), item.get("opened_count", 0)),
        reverse=True,
    )
    team_items = finalize_items(teams, team_extra)
    class_items = finalize_items(classes, class_extra)
    day_items = finalize_items(days, day_extra)
    day_items.sort(key=lambda item: item.get("date") or "")

    stats = _finalize_opening_bucket(total_bucket)
    stats.update(
        {
            "people_count": len(all_people),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
        }
    )

    return {
        "stats": stats,
        "columns": OPENING_COLUMNS,
        "employees": employee_items,
        "teams": team_items,
        "classes": class_items,
        "days": day_items,
        "options": {
            "teams": sorted(filter(None, all_teams)),
            "classes": sorted(filter(None, all_classes)),
            "department_groups": department_group_names,
        },
    }


@router.get("/report", response_model=dict)
def get_opening_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year_month: Optional[str] = None,
    dept: Optional[str] = None,
    department_group: Optional[str] = None,
    team: Optional[str] = None,
    class_name: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    five_products_opened: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_opening_report.view")
    start, end = _resolve_range(year_month, start_date, end_date)
    return _compute_opening_report(
        db,
        start,
        end,
        {
            "dept": dept,
            "department_group": department_group,
            "team": team,
            "class_name": class_name,
            "name": name,
            "emp_no": emp_no,
            "five_products_opened": five_products_opened,
        },
        current_user,
    )


def _rate_text(value: Any) -> str:
    if value is None:
        return ""
    return f"{float(value) * 100:.2f}%"


@router.get("/report/export")
def export_opening_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year_month: Optional[str] = None,
    dimension: str = Query("employee"),
    dept: Optional[str] = None,
    department_group: Optional[str] = None,
    team: Optional[str] = None,
    class_name: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    five_products_opened: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_opening_report.export")
    start, end = _resolve_range(year_month, start_date, end_date)
    data = _compute_opening_report(
        db,
        start,
        end,
        {
            "dept": dept,
            "department_group": department_group,
            "team": team,
            "class_name": class_name,
            "name": name,
            "emp_no": emp_no,
            "five_products_opened": five_products_opened,
        },
        current_user,
    )

    common_keys = ["contact_count", "opened_count", "opening_rate"] + [
        column["key"] for column in data["columns"]
    ]
    common_labels = ["接触量", "五大产品已开口量", "总开口率"] + [
        column["label"] for column in data["columns"]
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    if dimension == "team":
        writer.writerow(["部门组", "部门", "班组", "人数"] + common_labels)
        for item in data["teams"]:
            writer.writerow(
                [
                    item.get("dept_group", ""),
                    item.get("dept", ""),
                    item.get("team", ""),
                    item.get("people", 0),
                ]
                + [
                    _rate_text(item.get(key)) if key == "opening_rate" else item.get(key, 0)
                    for key in common_keys
                ]
            )
    elif dimension == "class":
        writer.writerow(["部门组", "部门", "班级", "人数"] + common_labels)
        for item in data["classes"]:
            writer.writerow(
                [
                    item.get("dept_group", ""),
                    item.get("dept", ""),
                    item.get("class_name", ""),
                    item.get("people", 0),
                ]
                + [
                    _rate_text(item.get(key)) if key == "opening_rate" else item.get(key, 0)
                    for key in common_keys
                ]
            )
    elif dimension == "day":
        writer.writerow(["日期", "人数"] + common_labels)
        for item in data["days"]:
            writer.writerow(
                [item.get("date", ""), item.get("people", 0)]
                + [
                    _rate_text(item.get(key)) if key == "opening_rate" else item.get(key, 0)
                    for key in common_keys
                ]
            )
    else:
        writer.writerow(["工号", "姓名", "班组", "部门", "部门组", "班级"] + common_labels)
        for item in data["employees"]:
            writer.writerow(
                [
                    item.get("kf_id", ""),
                    item.get("name", ""),
                    item.get("team", ""),
                    item.get("dept", ""),
                    item.get("dept_group", ""),
                    item.get("class_name", ""),
                ]
                + [
                    _rate_text(item.get(key)) if key == "opening_rate" else item.get(key, 0)
                    for key in common_keys
                ]
            )

    filename = f"开口率报表_{start}_{end}_{dimension}.csv"
    encoded = quote(filename)
    log_operation(
        db,
        current_user["id"],
        "export_marketing_opening_report",
        "marketing_opening_report",
        None,
        {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "dimension": dimension,
        },
    )
    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )
