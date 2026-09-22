import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.core.security import get_current_user, require_permission
from app.agent.settings import DEFAULT_SETTINGS, get_settings, validate_settings
try:
    from app.models.app_config import AppConfig
    _DB_CONFIG = True
except Exception:
    _DB_CONFIG = False

router = APIRouter(prefix="/api/agent-settings", tags=["智能体配置"])

SETTINGS_KEY = "agent_settings"


class AgentSettingsIn(BaseModel):
    system_prompt: Optional[str] = None
    suggestions: Optional[List[str]] = None
    max_iterations: Optional[int] = None
    max_history_messages: Optional[int] = None
    consecutive_run_sql_failures: Optional[int] = None


@router.get("")
def get_agent_settings(db: Session = Depends(get_db)):
    return get_settings(db)


@router.put("")
def put_agent_settings(
    body: AgentSettingsIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.config")
    if not _DB_CONFIG:
        raise HTTPException(status_code=503, detail="配置表不可用")
    provided = body.dict(exclude_unset=True)
    try:
        changed = validate_settings(provided)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    base = dict(DEFAULT_SETTINGS)
    base.update(get_settings(db))
    base.update(changed)
    rec = db.query(AppConfig).filter(AppConfig.key == SETTINGS_KEY).first()
    if not rec:
        rec = AppConfig(key=SETTINGS_KEY, value="")
        db.add(rec)
    rec.value = json.dumps(base, ensure_ascii=False)
    db.commit()
    return base


@router.post("/reset")
def reset_agent_settings(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.config")
    if not _DB_CONFIG:
        raise HTTPException(status_code=503, detail="配置表不可用")
    rec = db.query(AppConfig).filter(AppConfig.key == SETTINGS_KEY).first()
    if rec:
        db.delete(rec)
        db.commit()
    return dict(DEFAULT_SETTINGS)
