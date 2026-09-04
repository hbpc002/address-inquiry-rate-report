from sqlalchemy.orm import Session

from app.models.llm_provider import LLMProvider, LLMProviderModel
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


DEFAULT_MAX_RETRIES = 3


def build_chat_model(provider: LLMProvider, model: str = None, temperature: float = 0.2, **kwargs):
    """根据提供商配置构建 LangChain ChatOpenAI（兼容任意 OpenAI 接口）。

    model 可覆盖 provider 的默认模型（用于同一提供商下多模型选择）。
    max_retries 默认 3：OpenAI SDK 内置指数退避 + 随机抖动，自动处理瞬时 429/5xx。
    request_timeout 默认 60 秒：避免接口长时间挂起导致前端无反馈。
    """
    from langchain_openai import ChatOpenAI

    api_key = decrypt_secret(provider.api_key_encrypted) or "EMPTY"
    params = dict(
        model=model or provider.model,
        openai_api_base=provider.base_url,
        openai_api_key=api_key,
        temperature=temperature,
        streaming=True,
        max_retries=kwargs.pop("max_retries", DEFAULT_MAX_RETRIES),
    )
    params.setdefault("request_timeout", kwargs.pop("request_timeout", 60))
    params.update(kwargs)
    return ChatOpenAI(**params)


def fallback_models(db: Session, provider: LLMProvider, requested_model: str = None) -> list:
    """返回该 provider 内的降级链（已绑定给定父 provider 的 base_url/api_key）。

    主模型（is_default，或显式请求的模型）在前，其余按 fallback_order 升序。
    requested_model 用于前端下拉选择某模型时，以该模型为主、其余作降级。
    """
    rows = (
        db.query(LLMProviderModel)
        .filter(LLMProviderModel.provider_id == provider.id)
        .all()
    )
    if requested_model:
        ordered = [r for r in rows if r.model == requested_model]
        ordered += sorted(
            (r for r in rows if r.model != requested_model),
            key=lambda r: (r.fallback_order or 0),
        )
    else:
        ordered = sorted(
            rows,
            key=lambda r: (0 if r.is_default else 1, r.fallback_order or 0),
        )
    models = []
    seen = set()
    for r in ordered:
        if r.model not in seen:
            seen.add(r.model)
            models.append(build_chat_model(provider, model=r.model))
    if not models:
        models = [build_chat_model(provider)]
    return models


def build_fallback_model(provider: LLMProvider, models: list = None) -> "FallbackChatModel":
    """把若干 ChatOpenAI 实例包装为带限流降级能力的代理模型。"""
    if not models:
        models = [build_chat_model(provider)]
    return FallbackChatModel(models)


class FallbackChatModel:
    """透明代理多个模型形成降级链：主模型重试仍限流时依次切换备用模型。

    对 langchain ChatOpenAI 的 invoke/ainvoke/generate/bind_tools 做透明转发，
    仅拦截 openai.RateLimitError（HTTP 429）。used_fallback 与 used_model 供
    上层判断是否发生了降级。
    """

    def __init__(self, models: list, _meta: dict = None):
        if not models:
            raise ValueError("至少需要一个模型")
        self._models = list(models)
        self._primary = self._models[0]
        # 共享状态：bind_tools 产生的新包装器写这里，外层对象可读取是否降级
        self._meta = _meta if _meta is not None else {"used_fallback": False, "used_model": None}
        self._last_error = None

    @property
    def models(self) -> list:
        return list(self._models)

    @property
    def used_fallback(self) -> bool:
        return bool(self._meta["used_fallback"])

    @property
    def used_model(self):
        return self._meta["used_model"]

    def _run_chain(self, fn):
        last_err = None
        self._meta["used_fallback"] = False
        self._meta["used_model"] = None
        for i, m in enumerate(self._models):
            try:
                out = fn(m)
            except Exception as e:  # noqa: BLE001
                if _is_rate_limit(e):
                    last_err = e
                    if i < len(self._models) - 1:
                        self._meta["used_fallback"] = True
                        self._meta["used_model"] = getattr(m, "model_name", None)
                    continue
                raise
            self._meta["used_model"] = getattr(m, "model_name", None)
            return out
        raise last_err if last_err else RuntimeError("fallback 链为空")

    def invoke(self, messages, **kwargs):
        return self._run_chain(lambda m: m.invoke(messages, **kwargs))

    async def ainvoke(self, messages, **kwargs):
        return await self._run_chain(lambda m: m.ainvoke(messages, **kwargs))

    def generate(self, messages, **kwargs):
        return self._run_chain(lambda m: m.generate(messages, **kwargs))

    async def agenerate(self, messages, **kwargs):
        return await self._run_chain(lambda m: m.agenerate(messages, **kwargs))

    def bind_tools(self, *args, **kwargs):
        return FallbackChatModel(
            [m.bind_tools(*args, **kwargs) for m in self._models],
            _meta=self._meta,
        )

    def bind(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        return getattr(self._primary, name)


def _is_rate_limit(exc: Exception) -> bool:
    """判断异常是否为限流类(429)。可识别 openai.RateLimitError 及接口异常串。"""
    from openai import RateLimitError

    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, Exception):
        text = str(exc).lower()
        return "429" in text and "rate limit" in text
    return False


def test_provider(provider: LLMProvider) -> dict:
    """用极简请求验证提供商连通性与鉴权。"""
    try:
        llm = build_chat_model(provider, temperature=0)
        resp = llm.invoke("ping")
        content = getattr(resp, "content", "") or ""
        return {"ok": True, "sample": content[:50]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": str(e)}
