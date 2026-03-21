"""Fernet encryption utilities for design tool access tokens."""

from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _derive_key() -> bytes:
    """Derive a Fernet-compatible key from the configured encryption key or JWT secret."""
    settings = get_settings()
    source = settings.design_sync.encryption_key or settings.auth.jwt_secret_key
    # PBKDF2-derive a 32-byte key, then base64-encode for Fernet
    raw = hashlib.pbkdf2_hmac("sha256", source.encode(), b"design-sync-salt", 100_000)
    return base64.urlsafe_b64encode(raw)


def _get_fernet() -> Fernet:
    return Fernet(_derive_key())


def encrypt_token(plaintext: str) -> str:
    """Encrypt an access token for storage."""
    return str(_get_fernet().encrypt(plaintext.encode()).decode())


def decrypt_token(ciphertext: str) -> str:
    """Decrypt a stored access token."""
    return str(_get_fernet().decrypt(ciphertext.encode()).decode())


def can_decrypt(ciphertext: str) -> bool:
    """Check if a ciphertext can be decrypted with the current key."""
    try:
        _get_fernet().decrypt(ciphertext.encode())
    except Exception:
        return False
    return True
