from __future__ import annotations

import base64
import ctypes
import getpass
import hashlib
import socket
import sys
from ctypes import wintypes
from typing import Any


PROTECTED_PREFIX = "dpapi:"
LOCAL_PREFIX = "local:"       # legacy: base64 nu (pas de liaison machine)
LOCAL_MACHINE_PREFIX = "localx:"  # nouveau: XOR machine-bound + base64


class _DataBlob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def protect_secret(secret: Any) -> str:
    value = str(secret or "").strip()
    if not value:
        return ""
    if value.startswith((PROTECTED_PREFIX, LOCAL_MACHINE_PREFIX, LOCAL_PREFIX)):
        return value
    if sys.platform != "win32":
        key = _local_machine_key()
        ciphered = _xor_cipher(value.encode("utf-8"), key)
        return f"{LOCAL_MACHINE_PREFIX}{base64.b64encode(ciphered).decode('ascii')}"
    protected = _crypt_protect_data(value.encode("utf-8"))
    return f"{PROTECTED_PREFIX}{base64.b64encode(protected).decode('ascii')}"


def unprotect_secret(secret: Any) -> str:
    value = str(secret or "").strip()
    if not value:
        return ""
    if value.startswith(PROTECTED_PREFIX):
        if sys.platform != "win32":
            return ""
        try:
            raw = base64.b64decode(value[len(PROTECTED_PREFIX):])
            return _crypt_unprotect_data(raw).decode("utf-8")
        except (OSError, ValueError, UnicodeDecodeError):
            return ""
    if value.startswith(LOCAL_MACHINE_PREFIX):
        try:
            raw = base64.b64decode(value[len(LOCAL_MACHINE_PREFIX):])
            key = _local_machine_key()
            return _xor_cipher(raw, key).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return ""
    if value.startswith(LOCAL_PREFIX):
        # legacy: base64 nu - lisible directement (migration transparente)
        try:
            return base64.b64decode(value[len(LOCAL_PREFIX):]).decode("utf-8")
        except (ValueError, UnicodeDecodeError):
            return ""
    return value


def is_protected_secret(secret: Any) -> bool:
    return str(secret or "").strip().startswith((PROTECTED_PREFIX, LOCAL_MACHINE_PREFIX, LOCAL_PREFIX))


def is_weakly_protected(secret: Any) -> bool:
    """Retourne True si le secret n'est protege que par obfuscation (non-Windows)."""
    value = str(secret or "").strip()
    return value.startswith((LOCAL_MACHINE_PREFIX, LOCAL_PREFIX))


def secret_source_label(config_value: Any, env_name: str) -> str:
    import os

    if os.getenv(env_name):
        return f"Variable {env_name}"
    value = str(config_value or "").strip()
    if value.startswith(PROTECTED_PREFIX):
        return "Coffre Windows (DPAPI)"
    if value.startswith(LOCAL_MACHINE_PREFIX):
        return "Protection machine locale"
    if value.startswith(LOCAL_PREFIX):
        return "Obfuscation locale (migrer)"
    return "Fichier local"


def _local_machine_key() -> bytes:
    try:
        host = socket.gethostname()
    except OSError:
        host = "localhost"
    try:
        user = getpass.getuser()
    except OSError:
        user = "user"
    material = f"OREZONE_QHSE_2026:{host}:{user}".encode("utf-8")
    return hashlib.sha256(material).digest()


def _xor_cipher(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _crypt_protect_data(data: bytes) -> bytes:
    buffer_in = ctypes.create_string_buffer(data)
    blob_in = _blob_from_buffer(buffer_in, len(data))
    blob_out = _DataBlob()
    description = ctypes.c_wchar_p("OREZONE QHSE local secret")
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in),
        description,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        raise OSError("CryptProtectData failed")
    return _bytes_from_blob(blob_out)


def _crypt_unprotect_data(data: bytes) -> bytes:
    buffer_in = ctypes.create_string_buffer(data)
    blob_in = _blob_from_buffer(buffer_in, len(data))
    blob_out = _DataBlob()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(blob_out),
    ):
        raise OSError("CryptUnprotectData failed")
    return _bytes_from_blob(blob_out)


def _blob_from_buffer(buffer: Any, size: int) -> _DataBlob:
    return _DataBlob(size, ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))


def _bytes_from_blob(blob: _DataBlob) -> bytes:
    try:
        return ctypes.string_at(blob.pbData, blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob.pbData)
