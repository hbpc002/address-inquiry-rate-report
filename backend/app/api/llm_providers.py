import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.llm_provider import LLMProvider, LLMProviderModel
from app.models.app_config import AppConfig
from app.core.security import get_current_user, require_permission
from app.core.crypto import encrypt_secret, decrypt_secret, mask_secret
from app.core.llm import get_provider, list_providers, test_provider, NoProviderError

router = APIRouter(prefix="/api/llm-providers", tags=["智能体模型配置"])

LAUNCHER_KEY = "agent_launcher"
DEFAULT_LAUNCHER = {
    "enabled": True,
    "label": "智能助手",
    "icon_type": "emoji",
    "icon_value": "🤖",
    "position": "bottom-right",
    "color": "#409EFF",
    "draggable": True,
    "pos_x": None,
    "pos_y": None,
    "icon_offset_x": 0,
    "icon_offset_y": 0,
    "icon_scale": 100,
}

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "uploads",
)
ALLOWED_ICON_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


class ProviderModelIn(BaseModel):
    model: str
    is_default: bool = False


class ProviderIn(BaseModel):
    name: str
    base_url: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    model: Optional[str] = None
    models: Optional[List[ProviderModelIn]] = None
    is_default: bool = False


class ProviderOut(BaseModel):
    id: int
    name: str
    base_url: str
    model: str
    is_default: bool
    api_key_masked: str
    models: List[dict] = []


class TestIn(BaseModel):
    id: Optional[int] = None
    base_url: str = None
    model: str = None
    api_key: Optional[str] = None


class LauncherConfig(BaseModel):
    enabled: Optional[bool] = None
    label: Optional[str] = None
    icon_type: Optional[str] = None
    icon_value: Optional[str] = None
    position: Optional[str] = None
    color: Optional[str] = None
    draggable: Optional[bool] = None
    pos_x: Optional[int] = None
    pos_y: Optional[int] = None
    icon_offset_x: Optional[int] = None
    icon_offset_y: Optional[int] = None
    icon_scale: Optional[float] = None


def _models_of(db: Session, provider_id: int) -> List[dict]:
    rows = db.query(LLMProviderModel).filter(LLMProviderModel.provider_id == provider_id).all()
    return [{"model": r.model, "is_default": bool(r.is_default)} for r in rows]


def _to_out(p: LLMProvider, models: Optional[List[dict]] = None) -> ProviderOut:
    if models is None:
        models = [{"model": p.model, "is_default": True}]
    return ProviderOut(
        id=p.id, name=p.name, base_url=p.base_url, model=p.model,
        is_default=bool(p.is_default), api_key_masked=mask_secret(decrypt_secret(p.api_key_encrypted)),
        models=models,
    )


@router.get("", response_model=List[ProviderOut])
def list_providers_api(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.use")
    providers = list_providers(db)
    grouped = {}
    for r in db.query(LLMProviderModel).all():
        grouped.setdefault(r.provider_id, []).append({"model": r.model, "is_default": bool(r.is_default)})
    return [_to_out(p, grouped.get(p.id)) for p in providers]


def _resolve_models(body: ProviderIn):
    """把入参规整为模型列表，并保证恰好一个默认。"""
    if body.models:
        items = [{"model": m.model, "is_default": bool(m.is_default)} for m in body.models if m.model and m.model.strip()]
    elif body.model:
        items = [{"model": body.model, "is_default": True}]
    else:
        items = []
    if not items:
        raise HTTPException(status_code=400, detail="至少需提供一个模型")
    if not any(m["is_default"] for m in items):
        items[0]["is_default"] = True
    return items


@router.post("", response_model=ProviderOut)
def create_provider(
    body: ProviderIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.config")
    if db.query(LLMProvider).filter(LLMProvider.name == body.name).first():
        raise HTTPException(status_code=400, detail="同名提供商已存在")
    items = _resolve_models(body)
    default_model = next((m["model"] for m in items if m["is_default"]), items[0]["model"])
    if body.is_default:
        for old in db.query(LLMProvider).filter(LLMProvider.is_default == True).all():
            old.is_default = False
    p = LLMProvider(
        name=body.name, base_url=body.base_url, model=default_model,
        is_default=body.is_default,
        api_key_encrypted=encrypt_secret(body.api_key) if body.api_key else None,
    )
    db.add(p)
    db.flush()
    for m in items:
        db.add(LLMProviderModel(provider_id=p.id, model=m["model"], is_default=m["is_default"]))
    db.commit()
    db.refresh(p)
    return _to_out(p, items)


@router.get("/launcher")
def get_launcher(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    rec = db.query(AppConfig).filter(AppConfig.key == LAUNCHER_KEY).first()
    if not rec or not rec.value:
        return DEFAULT_LAUNCHER
    import json
    try:
        return json.loads(rec.value)
    except Exception:
        return DEFAULT_LAUNCHER


@router.put("/launcher")
def put_launcher(
    body: LauncherConfig,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.config")
    import json
    merged = dict(DEFAULT_LAUNCHER)
    provided = body.dict(exclude_unset=True)
    merged.update({k: v for k, v in provided.items() if k in DEFAULT_LAUNCHER})
    rec = db.query(AppConfig).filter(AppConfig.key == LAUNCHER_KEY).first()
    if not rec:
        rec = AppConfig(key=LAUNCHER_KEY, value="")
        db.add(rec)
    rec.value = json.dumps(merged, ensure_ascii=False)
    db.commit()
    return merged


@router.post("/launcher/icon")
async def upload_launcher_icon(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.config")
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_ICON_EXT:
        raise HTTPException(status_code=400, detail="仅支持图片文件 (png/jpg/jpeg/gif/svg/webp)")
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图标图片不能超过 2MB")
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    fname = f"agent-icon-{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR, fname), "wb") as f:
        f.write(content)
    return {"url": f"/static/{fname}"}


@router.put("/{provider_id}", response_model=ProviderOut)
def update_provider(
    provider_id: int,
    body: ProviderIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.config")
    p = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="提供商不存在")
    if p.name != body.name and db.query(LLMProvider).filter(LLMProvider.name == body.name).first():
        raise HTTPException(status_code=400, detail="同名提供商已存在")
    if body.is_default:
        for old in db.query(LLMProvider).filter(LLMProvider.is_default == True).all():
            old.is_default = False
    p.name = body.name
    p.base_url = body.base_url
    p.is_default = body.is_default
    if body.api_key:
        p.api_key_encrypted = encrypt_secret(body.api_key)
    models_out = None
    if body.models is not None:
        items = _resolve_models(body)
        db.query(LLMProviderModel).filter(LLMProviderModel.provider_id == p.id).delete()
        for m in items:
            db.add(LLMProviderModel(provider_id=p.id, model=m["model"], is_default=m["is_default"]))
        p.model = next((m["model"] for m in items if m["is_default"]), items[0]["model"])
        models_out = items
    elif body.model:
        p.model = body.model
    db.commit()
    db.refresh(p)
    return _to_out(p, models_out)


@router.delete("/{provider_id}")
def delete_provider(
    provider_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.config")
    p = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="提供商不存在")
    db.query(LLMProviderModel).filter(LLMProviderModel.provider_id == p.id).delete()
    db.delete(p)
    db.commit()
    return {"ok": True}


@router.post("/test")
def test_provider_api(
    body: TestIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.config")
    if body.id is not None:
        existing = db.query(LLMProvider).filter(LLMProvider.id == body.id).first()
        if not existing:
            raise HTTPException(status_code=404, detail="提供商不存在")
        probe = existing
    else:
        probe = LLMProvider(
            name="__probe__", base_url=body.base_url, model=body.model,
            api_key_encrypted=encrypt_secret(body.api_key) if body.api_key else None,
        )
    return test_provider(probe)



