import hashlib
import base64

from cryptography.fernet import Fernet

from app.core.config import settings


def _derive_key() -> bytes:
    digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_key())


def encrypt_secret(plain: str) -> str:
    """对敏感字符串（如 LLM api_key）进行加密，返回可存储的密文。"""
    if plain is None:
        return None
    return _fernet.encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    """解密 encrypt_secret 产生的密文。"""
    if token is None:
        return None
    return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")


def mask_secret(token: str) -> str:
    """用于列表接口展示的脱敏：仅保留前后若干字符。"""
    if not token:
        return ""
    if len(token) <= 8:
        return "****"
    return token[:4] + "****" + token[-4:]
