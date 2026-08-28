from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func

from app.models.database import Base


class LLMProvider(Base):
    """用户自助配置的模型提供商（任意 OpenAI 兼容接口）。

    api_key 以加密形式存储（见 app.core.crypto），列表接口返回脱敏。
    model 列保存「当前默认模型」，便于 build_chat_model 直接取用；
    一个提供商可挂多个模型，见 LLMProviderModel。
    """

    __tablename__ = "llm_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    base_url = Column(String(255), nullable=False, default="https://api.openai.com/v1")
    api_key_encrypted = Column(Text, nullable=True)
    model = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())


class LLMProviderModel(Base):
    """一个提供商下的多个模型；is_default 标记该 provider 内的默认模型。"""

    __tablename__ = "llm_provider_models"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(
        Integer,
        ForeignKey("llm_providers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    model = Column(String(100), nullable=False)
    is_default = Column(Boolean, default=False)
