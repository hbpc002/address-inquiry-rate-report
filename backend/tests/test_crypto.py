from app.core.crypto import encrypt_secret, decrypt_secret, mask_secret


def test_roundtrip():
    secret = "sk-1234567890abcdef"
    token = encrypt_secret(secret)
    assert token != secret
    assert decrypt_secret(token) == secret


def test_none_handling():
    assert encrypt_secret(None) is None
    assert decrypt_secret(None) is None


def test_mask():
    assert mask_secret("sk-1234567890abcdef") == "sk-1****cdef"
    assert mask_secret("short") == "****"
    assert mask_secret("") == ""
