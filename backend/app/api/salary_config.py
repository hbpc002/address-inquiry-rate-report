from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from app.models.database import get_db
from app.models.salary_config import SalaryConfig
from app.core.security import get_current_user, require_permission

router = APIRouter(prefix="/api/salary-config", tags=["绩效配置"])


class SalaryConfigItem(BaseModel):
    rule_key: str
    rule_data: Any


class SalaryConfigListResponse(BaseModel):
    items: List[SalaryConfigItem]


class SalaryConfigUpdate(BaseModel):
    rule_data: Any


DEFAULT_CONFIGS = {
    "call_salary_tiers": {
        "tiers": [
            {"min": 0, "max": 1000, "rate": 1.0},
            {"min": 1000, "max": 2000, "rate": 1.5},
            {"min": 2000, "max": 3500, "rate": 1.2},
            {"min": 3500, "max": None, "rate": 1.0}
        ]
    },
    "sat_salary": {
        "field_e": "呼入人工服务-满意度-非常满意量",
        "field_f": "呼入人工服务-满意度-满意量",
        "coefficient": 0.5
    },
    "sat_diff": {
        "field_e": "呼入人工服务-满意度-非常满意量",
        "field_f": "呼入人工服务-满意度-满意量",
        "field_g": "呼入人工服务-满意度-一般量",
        "field_h": "呼入人工服务-满意度-不满意量",
        "field_i": "呼入人工服务-满意度-非常不满意量",
        "coeff_a": 19,
        "coeff_b": 20
    },
    "call_gap_targets": {
        "targets": [2000, 2500, 3000]
    },
    "metric_targets": {
        "targets": [
            {
                "field": "人工服务-满意度-满意率",
                "label": "满意率",
                "operator": "lt",
                "value": 0.95,
                "color": "#F56C6C",
                "enabled": True
            },
            {
                "field": "_ti_dan_lv",
                "label": "提单率",
                "operator": "gt",
                "value": 0.15,
                "color": "#F56C6C",
                "enabled": True
            }
        ]
    }
}

import json


def _get_rule(db: Session, rule_key: str) -> dict:
    row = db.query(SalaryConfig).filter(SalaryConfig.rule_key == rule_key).first()
    if row:
        return json.loads(row.rule_data)
    return DEFAULT_CONFIGS.get(rule_key, {})


def _set_rule(db: Session, rule_key: str, data: dict):
    row = db.query(SalaryConfig).filter(SalaryConfig.rule_key == rule_key).first()
    serialized = json.dumps(data, ensure_ascii=False)
    if row:
        row.rule_data = serialized
    else:
        row = SalaryConfig(rule_key=rule_key, rule_data=serialized)
        db.add(row)


@router.get("", response_model=SalaryConfigListResponse)
def get_salary_config(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    items = []
    for key in DEFAULT_CONFIGS:
        data = _get_rule(db, key)
        items.append(SalaryConfigItem(rule_key=key, rule_data=data))
    return SalaryConfigListResponse(items=items)


@router.put("/{rule_key}", response_model=SalaryConfigItem)
def update_salary_config(
    rule_key: str,
    data: SalaryConfigUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    require_permission(current_user, "salary_config.edit")
    if rule_key not in DEFAULT_CONFIGS:
        raise HTTPException(status_code=404, detail="规则不存在")
    _set_rule(db, rule_key, data.rule_data)
    db.commit()
    return SalaryConfigItem(rule_key=rule_key, rule_data=_get_rule(db, rule_key))
