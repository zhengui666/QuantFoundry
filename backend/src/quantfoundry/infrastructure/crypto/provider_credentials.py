"""AEAD storage for provider credentials.

The master key is deployment configuration.  Plaintext credentials never enter
domain records, idempotency payloads, audit rows, events, or checkpoints.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class CredentialConfigurationError(RuntimeError):
    pass


def _decode_key(key_id: str, encoded: str) -> bytes:
    try:
        if not re.fullmatch(r"[A-Za-z0-9_-]+={0,2}", encoded):
            raise ValueError("invalid URL-safe base64 alphabet")
        padded = encoded + "=" * (-len(encoded) % 4)
        key = base64.b64decode(
            padded.encode("ascii"), altchars=b"-_", validate=True
        )
    except (UnicodeEncodeError, binascii.Error, ValueError) as error:
        raise CredentialConfigurationError(
            f"provider credential key is invalid: {key_id}"
        ) from error
    if len(key) != 32:
        raise CredentialConfigurationError(
            f"provider credential key must decode to 32 bytes: {key_id}"
        )
    return key


def _credential_keys() -> tuple[str, dict[str, bytes]]:
    key_id = os.getenv("QF_CREDENTIAL_ENCRYPTION_KEY_ID", "").strip()
    encoded = os.getenv("QF_CREDENTIAL_ENCRYPTION_KEY", "").strip()
    keyring = os.getenv("QF_CREDENTIAL_ENCRYPTION_KEYS", "").strip()
    if not key_id:
        raise CredentialConfigurationError(
            "provider credential encryption key is not configured"
        )
    if keyring:
        try:
            values = json.loads(keyring)
        except (TypeError, json.JSONDecodeError) as error:
            raise CredentialConfigurationError(
                "provider credential keyring is invalid"
            ) from error
        if not isinstance(values, dict) or not values:
            raise CredentialConfigurationError("provider credential keyring is invalid")
        keys = {
            str(item_id): _decode_key(str(item_id), item)
            for item_id, item in values.items()
            if isinstance(item_id, str) and isinstance(item, str)
        }
        if set(keys) != set(values) or key_id not in keys:
            raise CredentialConfigurationError(
                "active provider credential key is absent from keyring"
            )
        return key_id, keys
    if not encoded:
        raise CredentialConfigurationError(
            "provider credential encryption key is not configured"
        )
    return key_id, {key_id: _decode_key(key_id, encoded)}


def _master_key() -> tuple[str, bytes]:
    key_id, keys = _credential_keys()
    return key_id, keys[key_id]


def encryption_is_configured() -> bool:
    try:
        _master_key()
    except CredentialConfigurationError:
        return False
    return True


def credential_aad(
    *,
    connection_id: str,
    workspace_id: str,
    actor_id: str,
    provider_id: str,
    model_name: str | None,
) -> bytes:
    fields = (
        connection_id,
        workspace_id,
        actor_id,
        provider_id,
        model_name or "",
    )
    return "\x1f".join(fields).encode("utf-8")


def encrypt_credential(credential: str, *, aad: bytes) -> tuple[bytes, bytes, str]:
    key_id, key = _master_key()
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, credential.encode("utf-8"), aad)
    return ciphertext, nonce, key_id


def decrypt_credential(
    ciphertext: bytes, nonce: bytes, key_id: str, *, aad: bytes
) -> str:
    _configured_key_id, keys = _credential_keys()
    key = keys.get(key_id)
    if key is None:
        raise CredentialConfigurationError("provider credential key id is unavailable")
    try:
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
        return plaintext.decode("utf-8")
    except (InvalidTag, UnicodeDecodeError, ValueError) as error:
        raise CredentialConfigurationError(
            "provider credential authentication failed"
        ) from error


def credential_fingerprint(credential: str) -> str:
    """Keyed request identity; unlike raw SHA-256 it resists offline guessing."""

    encoded = os.getenv("QF_CREDENTIAL_FINGERPRINT_KEY", "").strip()
    if not encoded:
        raise CredentialConfigurationError(
            "provider credential fingerprint key is not configured"
        )
    key = _decode_key("fingerprint", encoded)
    return hmac.new(key, credential.encode("utf-8"), hashlib.sha256).hexdigest()
