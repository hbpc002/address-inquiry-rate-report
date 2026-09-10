import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.core.security import get_current_user, require_permission
try:
    from app.models.app_config import AppConfig
    _DB_CONFIG = True
except Exception:
    _DB_CONFIG = False

router = APIRouter(prefix="/api", tags=["界面名称配置"])

UI_LABEL_KEY = "ui_labels"

DEFAULT_UI_LABELS = {
    "project_name": "客户服务中心运营管理平台",
    "dashboard": "工效仪表盘",
    "checkin_report": "排班调度",
    "workload_report": "团队管理",
    "agent": "哟你通通",
}


class UILabelsIn(BaseModel):
    project_name: Optional[str] = None
    dashboard: Optional[str] = None
    checkin_report: Optional[str] = None
    workload_report: Optional[str] = None
    agent: Optional[str] = None


def _read_ui_labels(db: Session) -> dict:
    if not _DB_CONFIG:
        return dict(DEFAULT_UI_LABELS)
    rec = db.query(AppConfig).filter(AppConfig.key == UI_LABEL_KEY).first()
    merged = dict(DEFAULT_UI_LABELS)
    if rec and rec.value:
        try:
            stored = json.loads(rec.value)
            if isinstance(stored, dict):
                for k in DEFAULT_UI_LABELS:
                    if stored.get(k):
                        merged[k] = stored[k]
        except Exception:
            pass
    return merged


@router.get("/ui-labels")
def get_ui_labels(db: Session = Depends(get_db)):
    return _read_ui_labels(db)


@router.put("/ui-labels")
def put_ui_labels(
    body: UILabelsIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "system.config")
    if not _DB_CONFIG:
        raise HTTPException(status_code=503, detail="配置表不可用")
    base = _read_ui_labels(db)
    provided = body.dict(exclude_unset=True)
    changed = {
        k: v.strip() if isinstance(v, str) else v
        for k, v in provided.items()
        if k in DEFAULT_UI_LABELS and v is not None and str(v).strip()
    }
    base.update(changed)
    rec = db.query(AppConfig).filter(AppConfig.key == UI_LABEL_KEY).first()
    if not rec:
        rec = AppConfig(key=UI_LABEL_KEY, value="")
        db.add(rec)
    rec.value = json.dumps(base, ensure_ascii=False)
    db.commit()
    return base