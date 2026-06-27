"""network_client.py — Client HTTP pour le mode multi-PC.

En mode local (défaut) : accès direct à SQLite.
En mode réseau : appels HTTP vers le serveur SHEQ_MANAGEMENT principal.

La configuration est lue depuis DATA_DIR / "network_config.json".
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional

from app.config import DATA_DIR

_CONFIG_PATH = DATA_DIR / "network_config.json"

_DEFAULT_CONFIG: dict = {
    "enabled": False,
    "host": "",
    "port": 8765,
    "token": "",
}

_MAX_RETRIES = 3
_RETRY_DELAYS = (0.5, 1.0, 2.0)


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _load_config() -> dict:
    try:
        if _CONFIG_PATH.exists():
            raw = _CONFIG_PATH.read_text(encoding="utf-8")
            data = json.loads(raw)
            cfg = dict(_DEFAULT_CONFIG)
            cfg.update(data)
            return cfg
    except Exception:
        pass
    return dict(_DEFAULT_CONFIG)


def save_network_config(host: str, port: int, token: str, enabled: bool) -> None:
    """Sauvegarde la configuration réseau dans network_config.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {
        "enabled": bool(enabled),
        "host": host.strip(),
        "port": int(port),
        "token": token.strip(),
    }
    _CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def is_network_mode() -> bool:
    """Retourne True si le mode réseau est activé dans la config."""
    cfg = _load_config()
    return bool(cfg.get("enabled")) and bool(cfg.get("host"))


# ---------------------------------------------------------------------------
# NetworkClient
# ---------------------------------------------------------------------------


class NetworkClient:
    """Client HTTP léger pour communiquer avec le serveur SHEQ_MANAGEMENT.

    Utilise uniquement la bibliothèque standard (urllib).  Supporte les
    méthodes GET, POST, PUT, DELETE avec retry automatique.
    """

    def __init__(self, host: str, port: int, token: str, timeout: int = 10) -> None:
        self.base_url = f"http://{host}:{port}"
        self.token = token
        self.timeout = timeout

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_url(self, endpoint: str, params: Optional[dict] = None) -> str:
        endpoint = endpoint.lstrip("/")
        url = f"{self.base_url}/{endpoint}"
        if params:
            qs = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None}
            )
            url = f"{url}?{qs}"
        return url

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        data: Optional[dict] = None,
    ) -> Any:
        url = self._build_url(endpoint, params)
        body: Optional[bytes] = None
        if data is not None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")

        last_exc: Exception = RuntimeError("Aucune tentative effectuée")
        for attempt in range(_MAX_RETRIES):
            try:
                req = urllib.request.Request(
                    url, data=body, headers=self._headers(), method=method
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                    if raw.strip():
                        return json.loads(raw)
                    return {}
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    payload = json.loads(raw)
                except Exception:
                    payload = {"error": raw or str(exc)}
                raise RuntimeError(
                    f"HTTP {exc.code} sur {method} {endpoint}: {payload}"
                ) from exc
            except urllib.error.URLError as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAYS[attempt])
            except Exception as exc:
                last_exc = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RETRY_DELAYS[attempt])

        raise ConnectionError(
            f"Impossible de joindre le serveur après {_MAX_RETRIES} tentatives "
            f"({method} {endpoint}): {last_exc}"
        ) from last_exc

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def get(self, endpoint: str, params: Optional[dict] = None) -> Any:
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Optional[dict] = None) -> Any:
        return self._request("POST", endpoint, data=data or {})

    def put(self, endpoint: str, data: Optional[dict] = None) -> Any:
        return self._request("PUT", endpoint, data=data or {})

    def delete(self, endpoint: str) -> Any:
        return self._request("DELETE", endpoint)

    def ping(self) -> bool:
        """Teste la connectivité avec le serveur. Retourne True si OK."""
        try:
            result = self.get("/ping")
            return isinstance(result, dict) and result.get("status") == "ok"
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_client_instance: Optional[NetworkClient] = None


def get_client() -> Optional[NetworkClient]:
    """Retourne le client réseau configuré, ou None si mode local."""
    global _client_instance
    cfg = _load_config()
    if not cfg.get("enabled") or not cfg.get("host"):
        _client_instance = None
        return None
    if _client_instance is None:
        _client_instance = NetworkClient(
            host=cfg["host"],
            port=int(cfg.get("port", 8765)),
            token=cfg.get("token", ""),
        )
    return _client_instance
