from sqlalchemy.orm import Session

from app.models.llm_provider import LLMProvider
from app.core.crypto import decrypt_secret


class NoProviderError(Exception):
    """未配置任何可用模型提供商时抛出。"""


def get_provider(db: Session, name: str = None) -> LLMProvider:
    """按名称取提供商；未指定时取默认，其次取第一条。"""
    if name:
        provider = db.query(LLMProvider).filter(LLMProvider.name == name).first()
        if not provider:
            raise NoProviderError(f"未找到模型提供商: {name}")
        return provider
    provider = db.query(LLMProvider).filter(LLMProvider.is_default == True).first()
    if not provider:
        provider = db.query(LLMProvider).order_by(LLMProvider.id).first()
    if not provider:
        raise NoProviderError("尚未配置任何模型提供商，请先在「模型配置」中添加")
    return provider


def list_providers(db: Session) -> list:
    return db.query(LLMProvider).order_by(LLMProvider.is_default.desc(), LLMProvider.id).all()


def build_chat_model(provider: LLMProvider, temperature: float = 0.2, **kwargs):
    """根据提供商配置构建 LangChain ChatOpenAI（兼容任意 OpenAI 接口）。"""
    from langchain_openai import ChatOpenAI

    api_key = decrypt_secret(provider.api_key_encrypted) or "EMPTY"
    return ChatOpenAI(
        model=provider.model,
        openai_api_base=provider.base_url,
        openai_api_key=api_key,
        temperature=temperature,
        streaming=True,
        max_retries=1,
        **kwargs,
    )


def test_provider(provider: LLMProvider) -> dict:
    """用极简请求验证提供商连通性与鉴权。"""
    try:
        llm = build_chat_model(provider, temperature=0)
        resp = llm.invoke("ping")
        content = getattr(resp, "content", "") or ""
        return {"ok": True, "sample": content[:50]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
