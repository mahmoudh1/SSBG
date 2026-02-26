from __future__ import annotations

import secrets
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


@dataclass(frozen=True)
class EncryptionResult:
    nonce: bytes
    ciphertext: bytes
    tag: bytes


def _normalize_aes_key(key: bytes) -> bytes:
    if len(key) in {16, 24, 32}:
        return key
    # Derive a stable 256-bit AES key from arbitrary key material.
    from hashlib import sha256

    return sha256(key).digest()


def encrypt(plaintext: bytes, key: bytes) -> EncryptionResult:
    aes_key = _normalize_aes_key(key)
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(aes_key)
    encrypted = aesgcm.encrypt(nonce, plaintext, None)
    ciphertext = encrypted[:-16]
    tag = encrypted[-16:]
    return EncryptionResult(nonce=nonce, ciphertext=ciphertext, tag=tag)


def decrypt(ciphertext: bytes, key: bytes, nonce: bytes, tag: bytes) -> bytes:
    aes_key = _normalize_aes_key(key)
    aesgcm = AESGCM(aes_key)
    return aesgcm.decrypt(nonce, ciphertext + tag, None)
