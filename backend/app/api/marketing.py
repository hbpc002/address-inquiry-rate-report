import io
import json
import re
import uuid
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.security import get_current_user, require_permission
from app.models.app_config import AppConfig
from app.models.database import get_db
from app.models.employee import Employee
from app.models.marketing_detail import MarketingDetail
from app.utils.logger import log_operation

router = APIRouter(prefix="/api/marketing", tags=["营销统计"])

GROUP_CONFIG_KEY = "marketing_group_rules"
OVERALL_CONFIG_KEY = "marketing_overall_row_rules"
DEFAULT_GROUP_CONFIG = {"default_group": "未分组", "rules": []}
DEFAULT_OVERALL_CONFIG = {"rules": []}
MATCH_TYPES = {"contains", "equals", "prefix", "suffix", "regex"}

OVERALL_SECTIONS = [
    {
        "section_no": 1,
        "section_name": "线上直办",
        "bg": "blue",
        "rows": ["线上直办-热线", "线上直办-区域", "线上直办-维系", "线上直办-工单", "线上直办-分公司"],
        "subtotal": True,
    },
    {
        "section_no": 2,
        "section_name": "办理工单",
        "bg": "pink",
        "rows": ["办理工单"],
        "subtotal": False,
    },
    {
        "section_no": 3,
        "section_name": "营销工单",
        "bg": "green",
        "rows": ["营销工单-热线", "营销工单-区域", "营销工单-维系", "营销工单-工单", "营销工单-分公司"],
        "subtotal": True,
    },
    {
        "section_no": 4,
        "section_name": "降套维系",
        "bg": "yellow",
        "rows": ["降套维系"],
        "subtotal": False,
    },
]

OVERALL_ROW_LABELS = [row for section in OVERALL_SECTIONS for row in section["rows"]]
OVERALL_FIELDS = [
    "org_name",
    "channel",
    "pos_sequence",
    "develop_depart_name",
    "service_type",
    "data_type",
    "area_name",
    "tb_region_name",
]
OVERALL_COLUMNS = [
    {"key": "overlay", "label": "叠加包"},
    {"key": "package_change", "label": "套餐变更"},
    {"key": "broadband_new", "label": "宽带新装"},
    {"key": "mobile", "label": "移网"},
    {"key": "terminal", "label": "终端"},
]

FIELD_ALIASES = {
    "kf_id": ("KF_ID", "客服id", "客服ID"),
    "org_name": ("RESERVE6", "预留字段6"),
    "data_type": ("DATA_TYPE",),
    "pos_sequence": ("POS_SEQUENCE", "人员岗位性质"),
    "develop_depart_name": ("DEVELOP_DEPART_NAME", "发展渠道"),
    "develop_depart_id": ("DEVELOP_DEPART_ID", "发展渠道编码"),
    "develop_staff_name": ("DEVELOP_STAFF_NAME", "发展人"),
    "develop_staff_id": ("DEVELOP_STAFF_ID", "发展人编码"),
    "tb_region_name": ("TB_REGION_NAME",),
    "channel": ("CHANNEL", "受理渠道"),
    "area_name": ("AREA_NAME", "地市名称_cbss", "地市名称"),
    "net_type": ("NET_TYPE", "网别"),
    "trade_id": ("TRADE_ID", "CBSS订单号"),
    "finish_date": ("FINISH_DATE", "CBSS订单竣工时间"),
    "service_type": ("SERVICE_TYPE", "重点业务分类"),
    "package_type": ("PACKAGE_TYPE", "叠加包分类"),
    "valid_type": ("VALID_TYPE", "叠加包有效期"),
    "product_id": ("PRODUCT_ID", "产品ID"),
    "product_name": ("PRODUCT_NAME", "产品名称"),
    "lh_qh": ("LH_QH", "来话去话"),
    "is_zero": ("IS_ZERO", "0元/非0元"),
}


class GroupRule(BaseModel):
    id: Optional[str] = None
    group_name: str = ""
    match_type: str = "contains"
    pattern: str = ""
    priority: int = 0
    enabled: bool = True


class GroupRulesIn(BaseModel):
    default_group: str = "未分组"
    rules: List[GroupRule] = []


class OverallRowRule(BaseModel):
    id: Optional[str] = None
    row_label: str
    field: str = "org_name"
    match_type: str = "contains"
    pattern: str = ""
    priority: int = 0
    enabled: bool = True


class OverallRulesIn(BaseModel):
    rules: List[OverallRowRule] = []


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
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    if text.lower() in {"nan", "none", "nat", "--", "null"}:
        return ""
    return text


def _parse_finish_date(value: Any) -> Optional[date]:
    text = _text(value)
    if not text:
        return None
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d", "%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text[:len(datetime.now().strftime(fmt))], fmt).date()
        except Exception:
            pass
    parsed = pd.to_datetime(text, errors="coerce")
    if pd.isna(parsed):
        return None
    return parsed.date()


def _read_excel(content: bytes):
    try:
        raw = pd.read_excel(io.BytesIO(content), header=None, dtype=object)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"无法解析Excel文件: {exc}")

    if raw.empty:
        raise HTTPException(status_code=400, detail="Excel文件为空")

    alias_lookup = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            alias_lookup[_norm_label(alias)] = field

    best_idx = 0
    best_hits = 0
    for idx in range(min(10, len(raw))):
        labels = [_norm_label(v) for v in raw.iloc[idx].tolist()]
        hits = sum(1 for label in labels if label in alias_lookup)
        if hits > best_hits:
            best_idx = idx
            best_hits = hits

    if best_hits < 3:
        raise HTTPException(status_code=400, detail="未识别到有效的营销明细表头")

    mapping = {}
    seen_fields = set()
    for col_idx, value in enumerate(raw.iloc[best_idx].tolist()):
        field = alias_lookup.get(_norm_label(value))
        if field and field not in seen_fields:
            mapping[field] = col_idx
            seen_fields.add(field)

    required = {"finish_date", "service_type"}
    missing = required - set(mapping)
    if missing:
        raise HTTPException(status_code=400, detail=f"Excel缺少必要列: {', '.join(sorted(missing))}")
    if "product_id" not in mapping and "product_name" not in mapping:
        raise HTTPException(status_code=400, detail="Excel缺少产品ID/产品名称列")

    return raw.iloc[best_idx + 1 :], mapping


def _cell(values: List[Any], mapping: Dict[str, int], field: str) -> str:
    idx = mapping.get(field)
    if idx is None or idx >= len(values):
        return ""
    return _text(values[idx])


def _rule_match(value: str, rule: Dict[str, Any]) -> bool:
    pattern = str(rule.get("pattern") or "")
    if not pattern:
        return False
    source = value or ""
    match_type = rule.get("match_type") or "contains"
    if match_type == "regex":
        try:
            return re.search(pattern, source, flags=re.IGNORECASE) is not None
        except re.error:
            return False
    source_cmp = source.lower()
    pattern_cmp = pattern.lower()
    if match_type == "equals":
        return source_cmp == pattern_cmp
    if match_type == "prefix":
        return source_cmp.startswith(pattern_cmp)
    if match_type == "suffix":
        return source_cmp.endswith(pattern_cmp)
    return pattern_cmp in source_cmp


def _get_config(db: Session, key: str, default: Dict[str, Any]) -> Dict[str, Any]:
    rec = db.query(AppConfig).filter(AppConfig.key == key).first()
    if not rec or not rec.value:
        return json.loads(json.dumps(default, ensure_ascii=False))
    try:
        data = json.loads(rec.value)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return json.loads(json.dumps(default, ensure_ascii=False))


def _set_config(db: Session, key: str, data: Dict[str, Any]):
    rec = db.query(AppConfig).filter(AppConfig.key == key).first()
    serialized = json.dumps(data, ensure_ascii=False)
    if rec:
        rec.value = serialized
    else:
        db.add(AppConfig(key=key, value=serialized))


def _group_config(db: Session) -> Dict[str, Any]:
    return _get_config(db, GROUP_CONFIG_KEY, DEFAULT_GROUP_CONFIG)


def _overall_config(db: Session) -> Dict[str, Any]:
    return _get_config(db, OVERALL_CONFIG_KEY, DEFAULT_OVERALL_CONFIG)


def _clean_rules(rules: List[Any]) -> List[Dict[str, Any]]:
    result = []
    for item in rules:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        match_type = data.get("match_type") or "contains"
        if match_type not in MATCH_TYPES:
            raise HTTPException(status_code=400, detail=f"不支持的匹配方式: {match_type}")
        data["id"] = data.get("id") or uuid.uuid4().hex
        data["match_type"] = match_type
        data["priority"] = int(data.get("priority") or 0)
        data["enabled"] = bool(data.get("enabled", True))
        result.append(data)
    return result


def _classify_group(org_name: str, config: Dict[str, Any], cache: Dict[str, str]) -> str:
    if org_name in cache:
        return cache[org_name]
    default_group = str(config.get("default_group") or "未分组")
    rules = [r for r in config.get("rules", []) if r.get("enabled", True)]
    rules = sorted(enumerate(rules), key=lambda pair: (int(pair[1].get("priority") or 0), pair[0]))
    group = default_group
    for _, rule in rules:
        if _rule_match(org_name, rule):
            group = str(rule.get("group_name") or "").strip() or default_group
            break
    cache[org_name] = group
    return group


def _detail_value(detail: MarketingDetail, field: str) -> str:
    return str(getattr(detail, field, "") or "")


def _classify_overall_row(detail: MarketingDetail, config: Dict[str, Any], cache: Dict[str, str]) -> Optional[str]:
    keys = []
    for field in OVERALL_FIELDS:
        keys.append(_detail_value(detail, field))
    cache_key = "\u0001".join(keys)
    if cache_key in cache:
        return cache[cache_key] or None
    rules = [r for r in config.get("rules", []) if r.get("enabled", True)]
    rules = sorted(enumerate(rules), key=lambda pair: (int(pair[1].get("priority") or 0), pair[0]))
    result = None
    for _, rule in rules:
        field = rule.get("field") or "org_name"
        if field not in OVERALL_FIELDS:
            continue
        if _rule_match(_detail_value(detail, field), rule):
            result = str(rule.get("row_label") or "").strip()
            if result in OVERALL_ROW_LABELS:
                break
            result = None
    cache[cache_key] = result or ""
    return result


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


def _date_param(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式无效，应为 YYYY-MM-DD")


def _norm_emp_no(value: Any) -> str:
    return str(value or "").strip().upper()


def _emp_map(db: Session) -> Dict[str, Employee]:
    result = {}
    for emp in db.query(Employee).all():
        key = _norm_emp_no(emp.emp_no)
        if key:
            result.setdefault(key, emp)
    return result


def _new_bucket():
    return {
        "total": 0,
        "inbound": 0,
        "outbound": 0,
        "overlay": 0,
        "overlay_day": 0,
        "overlay_month": 0,
        "overlay_long": 0,
        "overlay_undefined": 0,
        "package_change": 0,
        "orders": set(),
    }


def _business_key(service_type: str) -> Optional[str]:
    text = (service_type or "").strip()
    if text == "叠加包":
        return "overlay"
    if text in ("套餐适配", "套餐变更"):
        return "package_change"
    return None


def _valid_key(valid_type: str) -> str:
    text = (valid_type or "").strip()
    if text == "日包":
        return "overlay_day"
    if text == "月包":
        return "overlay_month"
    if text in ("长期", "长期包"):
        return "overlay_long"
    return "overlay_undefined"


def _accumulate(bucket: Dict[str, Any], detail: MarketingDetail):
    bucket["total"] += 1
    lh = (detail.lh_qh or "").strip()
    if "来" in lh:
        bucket["inbound"] += 1
    elif "去" in lh:
        bucket["outbound"] += 1
    biz = _business_key(detail.service_type or "")
    if biz == "overlay":
        bucket["overlay"] += 1
        bucket[_valid_key(detail.valid_type or "")] += 1
    elif biz == "package_change":
        bucket["package_change"] += 1
    if detail.trade_id:
        bucket["orders"].add(detail.trade_id)


def _finalize(bucket: Dict[str, Any]) -> Dict[str, Any]:
    data = {k: v for k, v in bucket.items() if k != "orders"}
    data["order_count"] = len(bucket.get("orders") or set())
    return data


def _add_to(bucket: Dict[str, Any], row: Dict[str, Any]):
    for key in (
        "total",
        "inbound",
        "outbound",
        "overlay",
        "overlay_day",
        "overlay_month",
        "overlay_long",
        "overlay_undefined",
        "package_change",
    ):
        bucket[key] = bucket.get(key, 0) + int(row.get(key) or 0)
    bucket.setdefault("orders", set())
    if row.get("_trade_id"):
        bucket["orders"].add(row["_trade_id"])


def _match_business_filter(detail: MarketingDetail, business_type: str) -> bool:
    if not business_type:
        return True
    biz = _business_key(detail.service_type or "")
    if business_type in ("叠加包", "overlay"):
        return biz == "overlay"
    if business_type in ("套餐变更", "套餐适配", "package_change"):
        return biz == "package_change"
    return True


def _match_valid_filter(detail: MarketingDetail, valid_type: str) -> bool:
    if not valid_type:
        return True
    if (detail.service_type or "").strip() != "叠加包":
        return False
    mapping = {
        "日包": "overlay_day",
        "月包": "overlay_month",
        "长期": "overlay_long",
        "长期包": "overlay_long",
        "未定义": "overlay_undefined",
        "day": "overlay_day",
        "month": "overlay_month",
        "long": "overlay_long",
        "undefined": "overlay_undefined",
    }
    return _valid_key(detail.valid_type or "") == mapping.get(valid_type)


def _compute_report(db: Session, start: date, end: date, filters: Dict[str, Any]) -> Dict[str, Any]:
    details = db.query(MarketingDetail).filter(
        MarketingDetail.finish_date >= start,
        MarketingDetail.finish_date <= end,
    ).all()
    emps = _emp_map(db)
    config = _group_config(db)
    group_cache: Dict[str, str] = {}

    prepared = []
    all_groups = set()
    all_teams = set()
    all_orgs = set()
    all_products = set()
    for detail in details:
        emp = emps.get(_norm_emp_no(detail.kf_id))
        group = _classify_group(detail.org_name or "", config, group_cache)
        prepared.append((detail, emp, group))
        all_groups.add(group)
        all_teams.add(emp.team if emp and emp.team else "未匹配班组")
        if detail.org_name:
            all_orgs.add(detail.org_name)
        if detail.product_id or detail.product_name:
            all_products.add(detail.product_id or detail.product_name)

    group_name = filters.get("group_name") or ""
    team = filters.get("team") or ""
    name = filters.get("name") or ""
    emp_no = filters.get("emp_no") or ""
    org_name = filters.get("org_name") or ""
    business_type = filters.get("business_type") or ""
    valid_type = filters.get("valid_type") or ""
    lh_qh = filters.get("lh_qh") or ""
    product = filters.get("product") or ""

    filtered = []
    for detail, emp, group in prepared:
        if group_name and group != group_name:
            continue
        if team:
            team_value = emp.team if emp and emp.team else "未匹配班组"
            if team_value != team:
                continue
        if name and not (emp and name.lower() in (emp.name or "").lower()):
            continue
        if emp_no and emp_no.lower() not in (detail.kf_id or "").lower():
            continue
        if org_name and org_name.lower() not in (detail.org_name or "").lower():
            continue
        if lh_qh and (detail.lh_qh or "").strip() != lh_qh:
            continue
        if product:
            haystack = f"{detail.product_id or ''} {detail.product_name or ''}".lower()
            if product.lower() not in haystack:
                continue
        if not _match_business_filter(detail, business_type):
            continue
        if not _match_valid_filter(detail, valid_type):
            continue
        filtered.append((detail, emp, group))

    employees: Dict[str, Any] = {}
    teams: Dict[str, Any] = {}
    groups: Dict[str, Any] = {}
    products: Dict[str, Any] = {}
    days: Dict[str, Any] = {}
    overall_bucket = _new_bucket()
    people = set()
    product_set = set()

    for detail, emp, group in filtered:
        kf_id = detail.kf_id or ""
        emp_name = emp.name if emp else ""
        emp_team = emp.team if emp and emp.team else "未匹配班组"
        emp_dept = emp.dept if emp else ""
        if kf_id:
            people.add(kf_id)
        if detail.product_id or detail.product_name:
            product_set.add(detail.product_id or detail.product_name)

        emp_key = kf_id or "未匹配工号"
        bucket = employees.setdefault(emp_key, {
            **_new_bucket(),
            "kf_id": kf_id,
            "name": emp_name,
            "team": emp_team,
            "dept": emp_dept,
            "group_name": group,
            "org_name": detail.org_name or "",
        })
        _accumulate(bucket, detail)
        bucket["_trade_id"] = detail.trade_id

        team_bucket = teams.setdefault(emp_team, {
            **_new_bucket(),
            "team": emp_team,
            "people": set(),
        })
        _accumulate(team_bucket, detail)
        team_bucket["people"].add(kf_id or emp_key)
        team_bucket["_trade_id"] = detail.trade_id

        group_bucket = groups.setdefault(group, {**_new_bucket(), "group_name": group, "people": set()})
        _accumulate(group_bucket, detail)
        group_bucket["people"].add(kf_id or emp_key)
        group_bucket["_trade_id"] = detail.trade_id

        product_key = detail.product_id or detail.product_name or "未匹配产品"
        product_bucket = products.setdefault(product_key, {
            **_new_bucket(),
            "product_id": detail.product_id or "",
            "product_name": detail.product_name or "",
        })
        _accumulate(product_bucket, detail)
        product_bucket["_trade_id"] = detail.trade_id

        day_key = detail.finish_date.isoformat() if detail.finish_date else ""
        day_bucket = days.setdefault(day_key, {**_new_bucket(), "date": day_key})
        _accumulate(day_bucket, detail)
        day_bucket["_trade_id"] = detail.trade_id

        _accumulate(overall_bucket, detail)

    def finalize_items(mapping, extra=None):
        result = []
        for key, bucket in mapping.items():
            item = _finalize(bucket)
            if extra:
                extra(item, bucket, key)
            result.append(item)
        result.sort(key=lambda item: (item.get("total", 0), item.get("order_count", 0)), reverse=True)
        return result

    def team_extra(item, bucket, _key):
        item["people"] = len(bucket.get("people") or set())

    def group_extra(item, bucket, _key):
        item["people"] = len(bucket.get("people") or set())

    employee_items = finalize_items(employees)
    team_items = finalize_items(teams, team_extra)
    group_items = finalize_items(groups, group_extra)
    product_items = finalize_items(products)
    day_items = finalize_items(days)
    day_items.sort(key=lambda item: item.get("date") or "")

    stats = _finalize(overall_bucket)
    stats.update({
        "people_count": len(people),
        "product_count": len(product_set),
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
    })

    return {
        "stats": stats,
        "employees": employee_items,
        "teams": team_items,
        "groups": group_items,
        "products": product_items,
        "days": day_items,
        "options": {
            "groups": sorted(filter(None, all_groups)),
            "teams": sorted(filter(None, all_teams)),
            "orgs": sorted(filter(None, all_orgs)),
            "products": sorted(filter(None, all_products)),
        },
    }


def _overall_counts() -> Dict[str, int]:
    return {col["key"]: 0 for col in OVERALL_COLUMNS}


def _compute_overall(db: Session, start: date, end: date) -> Dict[str, Any]:
    details = db.query(MarketingDetail).filter(
        MarketingDetail.finish_date >= start,
        MarketingDetail.finish_date <= end,
    ).all()
    config = _overall_config(db)
    cache: Dict[str, str] = {}
    row_counts = {label: _overall_counts() for label in OVERALL_ROW_LABELS}
    unclassified_rows = 0
    unclassified_business_rows = 0

    for detail in details:
        biz = _business_key(detail.service_type or "")
        if biz not in ("overlay", "package_change"):
            unclassified_business_rows += 1
            continue
        row_label = _classify_overall_row(detail, config, cache)
        if not row_label:
            unclassified_rows += 1
            continue
        row_counts[row_label][biz] += 1

    rows = []
    grand_total = 0
    for section in OVERALL_SECTIONS:
        item_rows = []
        for row_label in section["rows"]:
            counts = row_counts[row_label]
            total = sum(counts.values())
            item_rows.append({
                "section_no": section["section_no"],
                "section_name": section["section_name"],
                "bg": section["bg"],
                "label": row_label,
                "is_subtotal": False,
                "counts": counts,
                "total": total,
            })
        subtotal_counts = {
            col["key"]: sum(row["counts"][col["key"]] for row in item_rows)
            for col in OVERALL_COLUMNS
        }
        subtotal_total = sum(subtotal_counts.values())
        if section["subtotal"]:
            section_rows = item_rows + [{
                "section_no": section["section_no"],
                "section_name": section["section_name"],
                "bg": section["bg"],
                "label": "小计",
                "is_subtotal": True,
                "counts": subtotal_counts,
                "total": subtotal_total,
            }]
        else:
            section_rows = item_rows
        for idx, row in enumerate(section_rows):
            row["rowspan"] = (len(section_rows)) if idx == 0 else 0
            row["ratio"] = round(row["total"] / grand_total, 6) if grand_total else None
            rows.append(row)
        grand_total += subtotal_total

    for row in rows:
        row["ratio"] = round(row["total"] / grand_total, 6) if grand_total else None

    top_rows = []
    for section in OVERALL_SECTIONS:
        section_rows = [r for r in rows if r["section_no"] == section["section_no"]]
        if section["subtotal"]:
            top_rows.extend([r for r in section_rows if r["label"] == "小计"])
        else:
            top_rows.extend([r for r in section_rows if not r["is_subtotal"]])
    total_counts = {
        col["key"]: sum(row["counts"][col["key"]] for row in top_rows)
        for col in OVERALL_COLUMNS
    }

    total_row = {
        "label": "合计",
        "counts": total_counts,
        "total": sum(total_counts.values()),
        "ratio": 1 if total_counts else None,
    }
    return {
        "stats": {
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "grand_total": grand_total,
            "unclassified_rows": unclassified_rows,
            "unclassified_business_rows": unclassified_business_rows,
        },
        "columns": OVERALL_COLUMNS,
        "rows": rows,
        "total_row": total_row,
    }


@router.post("/details/import", response_model=dict)
def import_details(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing.upload")
    batch = uuid.uuid4().hex[:8]
    content = file.file.read()
    data, mapping = _read_excel(content)

    records = []
    dates = set()
    seen = set()
    skipped = 0
    for pos in range(len(data)):
        values = data.iloc[pos].tolist()
        try:
            finish_date = _parse_finish_date(values[mapping["finish_date"]] if "finish_date" in mapping else None)
            if not finish_date:
                skipped += 1
                continue
            product_id = _cell(values, mapping, "product_id")
            product_name = _cell(values, mapping, "product_name")
            if not product_id and not product_name:
                skipped += 1
                continue
            record = {
                "kf_id": _cell(values, mapping, "kf_id"),
                "org_name": _cell(values, mapping, "org_name"),
                "data_type": _cell(values, mapping, "data_type"),
                "pos_sequence": _cell(values, mapping, "pos_sequence"),
                "develop_depart_name": _cell(values, mapping, "develop_depart_name"),
                "develop_depart_id": _cell(values, mapping, "develop_depart_id"),
                "develop_staff_name": _cell(values, mapping, "develop_staff_name"),
                "develop_staff_id": _cell(values, mapping, "develop_staff_id"),
                "tb_region_name": _cell(values, mapping, "tb_region_name"),
                "channel": _cell(values, mapping, "channel"),
                "area_name": _cell(values, mapping, "area_name"),
                "net_type": _cell(values, mapping, "net_type"),
                "trade_id": _cell(values, mapping, "trade_id"),
                "finish_date": finish_date,
                "service_type": _cell(values, mapping, "service_type"),
                "package_type": _cell(values, mapping, "package_type"),
                "valid_type": _cell(values, mapping, "valid_type"),
                "product_id": product_id,
                "product_name": product_name,
                "lh_qh": _cell(values, mapping, "lh_qh"),
                "is_zero": _cell(values, mapping, "is_zero"),
                "import_batch": batch,
            }
            key = (
                record["trade_id"],
                record["product_id"],
                record["product_name"],
                record["service_type"],
                record["valid_type"],
            )
            if record["trade_id"] and key in seen:
                skipped += 1
                continue
            if record["trade_id"]:
                seen.add(key)
            records.append(record)
            dates.add(finish_date)
        except Exception:
            skipped += 1

    if not records:
        raise HTTPException(status_code=400, detail="未解析到有效数据")

    db.query(MarketingDetail).filter(MarketingDetail.finish_date.in_(sorted(dates))).delete(synchronize_session=False)
    db.bulk_insert_mappings(MarketingDetail, records)
    db.commit()
    log_operation(
        db,
        current_user["id"],
        "import_marketing_details",
        "marketing",
        None,
        {"batch": batch, "count": len(records), "dates": [d.isoformat() for d in sorted(dates)]},
    )
    return {
        "count": len(records),
        "skipped": skipped,
        "batch": batch,
        "dates": [d.isoformat() for d in sorted(dates)],
    }


@router.get("/details", response_model=dict)
def get_details(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    import_batch: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    kf_id: Optional[str] = None,
    name: Optional[str] = None,
    org_name: Optional[str] = None,
    product: Optional[str] = None,
    service_type: Optional[str] = None,
    lh_qh: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing.view")
    query = db.query(MarketingDetail)
    if import_batch:
        query = query.filter(MarketingDetail.import_batch == import_batch)
    start = _date_param(start_date)
    end = _date_param(end_date)
    if start:
        query = query.filter(MarketingDetail.finish_date >= start)
    if end:
        query = query.filter(MarketingDetail.finish_date <= end)
    if kf_id:
        query = query.filter(MarketingDetail.kf_id.ilike(f"%{kf_id}%"))
    if name:
        emp_nos = [e[0] for e in db.query(Employee.emp_no).filter(Employee.name.ilike(f"%{name}%")).all()]
        if not emp_nos:
            return {"items": [], "total": 0}
        query = query.filter(MarketingDetail.kf_id.in_(emp_nos))
    if org_name:
        query = query.filter(MarketingDetail.org_name.ilike(f"%{org_name}%"))
    if product:
        query = query.filter(or_(
            MarketingDetail.product_id.ilike(f"%{product}%"),
            MarketingDetail.product_name.ilike(f"%{product}%"),
        ))
    if service_type:
        query = query.filter(MarketingDetail.service_type == service_type)
    if lh_qh:
        query = query.filter(MarketingDetail.lh_qh == lh_qh)

    total = query.count()
    items = query.order_by(
        MarketingDetail.finish_date.desc(), MarketingDetail.id.desc()
    ).offset((page - 1) * limit).limit(limit).all()

    emps = _emp_map(db)
    config = _group_config(db)
    cache: Dict[str, str] = {}
    result = []
    for detail in items:
        emp = emps.get(_norm_emp_no(detail.kf_id))
        result.append({
            "id": detail.id,
            "kf_id": detail.kf_id,
            "name": emp.name if emp else "",
            "team": emp.team if emp else "",
            "dept": emp.dept if emp else "",
            "group_name": _classify_group(detail.org_name or "", config, cache),
            "org_name": detail.org_name,
            "data_type": detail.data_type,
            "pos_sequence": detail.pos_sequence,
            "develop_depart_name": detail.develop_depart_name,
            "channel": detail.channel,
            "area_name": detail.area_name,
            "net_type": detail.net_type,
            "trade_id": detail.trade_id,
            "finish_date": detail.finish_date.isoformat() if detail.finish_date else None,
            "service_type": detail.service_type,
            "package_type": detail.package_type,
            "valid_type": detail.valid_type,
            "product_id": detail.product_id,
            "product_name": detail.product_name,
            "lh_qh": detail.lh_qh,
            "is_zero": detail.is_zero,
            "import_batch": detail.import_batch,
        })
    return {"items": result, "total": total}


@router.delete("/details/by-date", response_model=dict)
def delete_details_by_date(
    date: str = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing.delete")
    target = _date_param(date)
    count = db.query(MarketingDetail).filter(MarketingDetail.finish_date == target).delete(synchronize_session=False)
    db.commit()
    log_operation(db, current_user["id"], "delete_marketing_details_by_date", "marketing", None, {"date": date, "count": count})
    return {"count": count}


@router.delete("/details/import/{batch}", response_model=dict)
def delete_details_batch(
    batch: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing.delete")
    count = db.query(MarketingDetail).filter(MarketingDetail.import_batch == batch).delete(synchronize_session=False)
    db.commit()
    log_operation(db, current_user["id"], "delete_marketing_batch", "marketing", None, {"batch": batch, "count": count})
    return {"count": count}


@router.delete("/details/{detail_id}", response_model=dict)
def delete_detail(
    detail_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing.delete")
    record = db.query(MarketingDetail).filter(MarketingDetail.id == detail_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    log_operation(db, current_user["id"], "delete_marketing_detail", "marketing", detail_id)
    return {"message": "删除成功"}


@router.get("/group-rules", response_model=dict)
def get_group_rules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_settings.view")
    return _group_config(db)


@router.put("/group-rules", response_model=dict)
def update_group_rules(
    body: GroupRulesIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_settings.edit")
    data = {
        "default_group": body.default_group.strip() or "未分组",
        "rules": _clean_rules(body.rules),
    }
    _set_config(db, GROUP_CONFIG_KEY, data)
    db.commit()
    return _group_config(db)


@router.get("/overall-row-rules", response_model=dict)
def get_overall_row_rules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_settings.view")
    return _overall_config(db)


@router.put("/overall-row-rules", response_model=dict)
def update_overall_row_rules(
    body: OverallRulesIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_settings.edit")
    cleaned = _clean_rules(body.rules)
    for rule in cleaned:
        if rule.get("row_label") not in OVERALL_ROW_LABELS:
            raise HTTPException(status_code=400, detail=f"不支持的行分类: {rule.get('row_label')}")
        if rule.get("field") not in OVERALL_FIELDS:
            raise HTTPException(status_code=400, detail=f"不支持的匹配字段: {rule.get('field')}")
    _set_config(db, OVERALL_CONFIG_KEY, {"rules": cleaned})
    db.commit()
    return _overall_config(db)


@router.get("/organizations", response_model=dict)
def get_organizations(
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_settings.view")
    rows = db.query(
        MarketingDetail.org_name, func.count(MarketingDetail.id)
    ).group_by(MarketingDetail.org_name).order_by(func.count(MarketingDetail.id).desc()).limit(limit).all()
    config = _group_config(db)
    cache: Dict[str, str] = {}
    return {
        "items": [
            {"org_name": org or "", "count": count, "group_name": _classify_group(org or "", config, cache)}
            for org, count in rows
        ]
    }


@router.get("/row-rule-preview", response_model=dict)
def get_row_rule_preview(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_settings.view")
    config = _overall_config(db)
    cache: Dict[str, str] = {}
    details = db.query(MarketingDetail).all()
    unclassified = 0
    counter: Dict[tuple, int] = {}
    for detail in details:
        if _business_key(detail.service_type or "") not in ("overlay", "package_change"):
            continue
        row_label = _classify_overall_row(detail, config, cache)
        if row_label:
            continue
        unclassified += 1
        for field in OVERALL_FIELDS:
            value = _detail_value(detail, field)
            if value:
                key = (field, value)
                counter[key] = counter.get(key, 0) + 1
    samples = [
        {"field": field, "value": value, "count": count}
        for (field, value), count in sorted(counter.items(), key=lambda item: item[1], reverse=True)[:limit]
    ]
    return {"unclassified": unclassified, "samples": samples}


@router.get("/report", response_model=dict)
def get_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year_month: Optional[str] = None,
    group_name: Optional[str] = None,
    team: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    org_name: Optional[str] = None,
    business_type: Optional[str] = None,
    valid_type: Optional[str] = None,
    lh_qh: Optional[str] = None,
    product: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_report.view")
    start, end = _resolve_range(year_month, start_date, end_date)
    return _compute_report(db, start, end, {
        "group_name": group_name,
        "team": team,
        "name": name,
        "emp_no": emp_no,
        "org_name": org_name,
        "business_type": business_type,
        "valid_type": valid_type,
        "lh_qh": lh_qh,
        "product": product,
    })


@router.get("/report/export")
def export_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year_month: Optional[str] = None,
    dimension: str = Query("employee"),
    group_name: Optional[str] = None,
    team: Optional[str] = None,
    name: Optional[str] = None,
    emp_no: Optional[str] = None,
    org_name: Optional[str] = None,
    business_type: Optional[str] = None,
    valid_type: Optional[str] = None,
    lh_qh: Optional[str] = None,
    product: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_report.export")
    start, end = _resolve_range(year_month, start_date, end_date)
    data = _compute_report(db, start, end, {
        "group_name": group_name,
        "team": team,
        "name": name,
        "emp_no": emp_no,
        "org_name": org_name,
        "business_type": business_type,
        "valid_type": valid_type,
        "lh_qh": lh_qh,
        "product": product,
    })
    output = io.StringIO()
    import csv

    writer = csv.writer(output)
    common = ["产品办理量", "订单数", "来话量", "去话量", "叠加包", "日包", "月包", "长期包", "未定义", "套餐变更"]
    if dimension == "team":
        writer.writerow(["班组", "人数"] + common)
        for item in data["teams"]:
            writer.writerow([item.get("team"), item.get("people", 0)] + [item.get(k, 0) for k in ("total", "order_count", "inbound", "outbound", "overlay", "overlay_day", "overlay_month", "overlay_long", "overlay_undefined", "package_change")])
    elif dimension == "group":
        writer.writerow(["自定义分组", "人数"] + common)
        for item in data["groups"]:
            writer.writerow([item.get("group_name"), item.get("people", 0)] + [item.get(k, 0) for k in ("total", "order_count", "inbound", "outbound", "overlay", "overlay_day", "overlay_month", "overlay_long", "overlay_undefined", "package_change")])
    elif dimension == "product":
        writer.writerow(["产品ID", "产品名称"] + common)
        for item in data["products"]:
            writer.writerow([item.get("product_id"), item.get("product_name")] + [item.get(k, 0) for k in ("total", "order_count", "inbound", "outbound", "overlay", "overlay_day", "overlay_month", "overlay_long", "overlay_undefined", "package_change")])
    elif dimension == "day":
        writer.writerow(["日期"] + common)
        for item in data["days"]:
            writer.writerow([item.get("date")] + [item.get(k, 0) for k in ("total", "order_count", "inbound", "outbound", "overlay", "overlay_day", "overlay_month", "overlay_long", "overlay_undefined", "package_change")])
    else:
        writer.writerow(["工号", "姓名", "班组", "部门", "自定义分组"] + common)
        for item in data["employees"]:
            writer.writerow([item.get("kf_id"), item.get("name"), item.get("team"), item.get("dept"), item.get("group_name")] + [item.get(k, 0) for k in ("total", "order_count", "inbound", "outbound", "overlay", "overlay_day", "overlay_month", "overlay_long", "overlay_undefined", "package_change")])

    filename = f"marketing_report_{start}_{end}_{dimension}.csv"
    log_operation(db, current_user["id"], "export_marketing_report", "marketing", None, {"start_date": start.isoformat(), "end_date": end.isoformat(), "dimension": dimension})
    return StreamingResponse(
        iter(["\ufeff" + output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/overall-report", response_model=dict)
def get_overall_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year_month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_overall.view")
    start, end = _resolve_range(year_month, start_date, end_date)
    return _compute_overall(db, start, end)


def _excel_border():
    side = Side(style="thin", color="FF000000")
    return Border(left=side, right=side, top=side, bottom=side)


def _fill(color: str):
    return PatternFill(start_color=color, end_color=color, fill_type="solid")


def _style_cell(cell, fill_color=None, bold=False, font_color=None):
    cell.alignment = Alignment(horizontal="center", vertical="center")
    cell.border = _excel_border()
    if fill_color:
        cell.fill = _fill(fill_color)
    if font_color or bold:
        cell.font = Font(bold=bold, color=font_color or "FF000000")


@router.get("/overall-report/export")
def export_overall_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    year_month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "marketing_overall.export")
    start, end = _resolve_range(year_month, start_date, end_date)
    data = _compute_overall(db, start, end)
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "总体营销"

    headers = ["序号", "五大类业务", "叠加包", "套餐变更", "宽带新装", "移网", "终端", "合计", "占比"]
    for col_idx, label in enumerate(headers, start=1):
        cell = sheet.cell(row=1, column=col_idx, value=label)
        font_color = "FFFF0000" if 3 <= col_idx <= 7 else "FF000000"
        _style_cell(cell, fill_color="FFFFFFFF", bold=True, font_color=font_color)

    colors = {
        "blue": "FFDDEBF7",
        "pink": "FFFCE4EC",
        "green": "FFE2EFDA",
        "yellow": "FFFFFF00",
    }

    row_number = 2
    section_first_rows = {}
    merge_ranges = []
    total_row_number = 2 + len(data["rows"])

    for section in OVERALL_SECTIONS:
        section_rows = [row for row in data["rows"] if row["section_no"] == section["section_no"]]
        section_first_rows[section["section_no"]] = row_number
        for row in section_rows:
            fill_color = colors.get(row["bg"])
            sheet.cell(row=row_number, column=1, value=row["section_no"] if row["rowspan"] else None)
            sheet.cell(row=row_number, column=2, value=row["label"])
            for offset, column in enumerate(OVERALL_COLUMNS):
                sheet.cell(row=row_number, column=3 + offset, value=row["counts"][column["key"]])
            sheet.cell(row=row_number, column=8, value=f"=SUM(C{row_number}:G{row_number})")
            sheet.cell(row=row_number, column=9, value=f"=IFERROR(H{row_number}/$H${total_row_number},0)")
            for col_idx in range(1, 10):
                cell = sheet.cell(row=row_number, column=col_idx)
                _style_cell(cell, fill_color=fill_color, bold=bool(row.get("is_subtotal")))
                if col_idx == 9 and data["stats"]["grand_total"] == 0:
                    cell.font = Font(color="FF00B050", bold=True)
                    cell.fill = _fill("FFC6EFCE")
            if row["rowspan"] > 1:
                merge_ranges.append((row_number, row_number + row["rowspan"] - 1))
            row_number += 1

    for start_row, end_row in merge_ranges:
        sheet.merge_cells(start_row=start_row, start_column=1, end_row=end_row, end_column=1)

    total_row_number = row_number
    for col_idx, value in enumerate([None, None, 0, 0, 0, 0, 0, 0, 1], start=1):
        cell = sheet.cell(row=total_row_number, column=col_idx)
        if col_idx == 1:
            cell.value = "合计"
        elif col_idx >= 3 and col_idx <= 7:
            col_letter = chr(ord("A") + col_idx - 1)
            refs = []
            for section in OVERALL_SECTIONS:
                if section["subtotal"]:
                    refs.append(f"{col_letter}{section_first_rows[section['section_no']] + len(section['rows'])}")
                else:
                    refs.append(f"{col_letter}{section_first_rows[section['section_no']]}")
            cell.value = "=" + "+".join(refs)
        elif col_idx == 8:
            cell.value = f"=SUM(C{total_row_number}:G{total_row_number})"
        elif col_idx == 9:
            cell.value = 1
        _style_cell(cell, fill_color="FFFFFFFF", bold=True)

    sheet.merge_cells(start_row=total_row_number, start_column=1, end_row=total_row_number, end_column=2)

    widths = {"A": 7, "B": 24, "C": 12, "D": 12, "E": 12, "F": 12, "G": 12, "H": 12, "I": 12}
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    sheet.freeze_panes = "A2"

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    filename = f"总体营销_{start}_{end}.xlsx"
    encoded = quote(filename)
    log_operation(db, current_user["id"], "export_marketing_overall", "marketing", None, {"start_date": start.isoformat(), "end_date": end.isoformat()})
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )
