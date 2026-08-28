import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, Body, UploadFile, File
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.llm_provider import LLMProvider
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
}

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "uploads",
)
ALLOWED_ICON_EXT = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}


class ProviderIn(BaseModel):
    name: str
    base_url: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    model: str
    is_default: bool = False


class ProviderOut(BaseModel):
    id: int
    name: str
    base_url: str
    model: str
    is_default: bool
    api_key_masked: str


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


def _to_out(p: LLMProvider) -> ProviderOut:
    return ProviderOut(
        id=p.id, name=p.name, base_url=p.base_url, model=p.model,
        is_default=bool(p.is_default), api_key_masked=mask_secret(decrypt_secret(p.api_key_encrypted)),
    )


@router.get("", response_model=List[ProviderOut])
def list_providers_api(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.config")
    return [_to_out(p) for p in list_providers(db)]


@router.post("", response_model=ProviderOut)
def create_provider(
    body: ProviderIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    require_permission(current_user, "agent.config")
    if db.query(LLMProvider).filter(LLMProvider.name == body.name).first():
        raise HTTPException(status_code=400, detail="同名提供商已存在")
    if body.is_default:
        for old in db.query(LLMProvider).filter(LLMProvider.is_default == True).all():
            old.is_default = False
    p = LLMProvider(
        name=body.name, base_url=body.base_url, model=body.model,
        is_default=body.is_default,
        api_key_encrypted=encrypt_secret(body.api_key) if body.api_key else None,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return _to_out(p)


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
    p.model = body.model
    p.is_default = body.is_default
    if body.api_key:
        p.api_key_encrypted = encrypt_secret(body.api_key)
    db.commit()
    db.refresh(p)
    return _to_out(p)


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



