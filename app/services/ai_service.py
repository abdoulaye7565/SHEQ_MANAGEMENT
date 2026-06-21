from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any

from app.config import DATA_DIR
from app.services.app_logger import get_logger
from app.services.secure_config import (
    is_protected_secret,
    protect_secret,
    secret_source_label,
    unprotect_secret,
)

AI_CONFIG_PATH = DATA_DIR / "ai_config.json"
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4.1-mini"
LOGGER = get_logger(__name__)

KNOWN_MODELS = {
    "gpt-4.1-nano",
    "gpt-4.1-mini",
    "gpt-4.1",
    "gpt-4o-mini",
    "gpt-4o",
    "o1-mini",
    "o3-mini",
    "o4-mini",
}

_SYSTEM_PROMPT = (
    "Tu es un assistant industriel QHSE expert pour OREZONE, spécialisé en mines et forage. "
    "Réponds en français sauf demande contraire. Sois pratique, concis et professionnel. "
    "Ne fabrique jamais de données — appuie-toi uniquement sur le contexte fourni. "
    "Signale toujours ce qui nécessite une validation humaine ou une inspection terrain. "
    "Applique les normes ISO 45001, ISO 9001, ISO 14001 et la hiérarchie des contrôles : "
    "élimination → substitution → ingénierie → administratif → EPI."
)


class AIConfigurationError(ValueError):
    pass


# ── Config ────────────────────────────────────────────────────────────────────

def get_ai_settings() -> dict[str, Any]:
    config = _read_ai_config()
    _migrate_local_api_key(config)
    api_key = _resolve_api_key(config)
    ready = bool(config.get("enabled", False)) and bool(api_key)
    last_test_status = str(config.get("last_test_status") or "not_tested")
    return {
        "enabled": bool(config.get("enabled", False)),
        "provider": "OpenAI",
        "model": str(config.get("model") or DEFAULT_MODEL),
        "api_key_configured": bool(api_key),
        "ready": ready,
        "operational": ready and last_test_status == "ok",
        "last_test_status": last_test_status,
        "last_test_message": str(config.get("last_test_message") or ""),
        "last_test_at": str(config.get("last_test_at") or ""),
        "api_key_source": secret_source_label(config.get("api_key"), "OPENAI_API_KEY"),
        "config_path": str(AI_CONFIG_PATH),
    }


def save_ai_settings(values: dict[str, Any]) -> dict[str, Any]:
    current = _read_ai_config()
    model = str(values.get("model") or current.get("model") or DEFAULT_MODEL).strip()
    if not model:
        raise ValueError("Modèle IA obligatoire.")
    if model not in KNOWN_MODELS:
        known = ", ".join(sorted(KNOWN_MODELS))
        raise ValueError(f"Modèle inconnu : '{model}'. Modèles valides : {known}")
    api_key = values.get("api_key")
    clear_api_key = bool(values.get("clear_api_key"))
    key_changed = (
        api_key is not None
        and str(api_key).strip()
        and str(api_key).strip() != str(current.get("api_key") or "")
    )
    model_changed = model != str(current.get("model") or DEFAULT_MODEL)
    reset = key_changed or model_changed or clear_api_key
    payload: dict[str, Any] = {
        "enabled": bool(values.get("enabled", current.get("enabled", False))),
        "model": model,
        "last_test_status": "not_tested" if reset else str(current.get("last_test_status") or "not_tested"),
        "last_test_message": "" if reset else str(current.get("last_test_message") or ""),
        "last_test_at": "" if reset else str(current.get("last_test_at") or ""),
    }
    if clear_api_key:
        payload["api_key"] = ""
    elif api_key is not None and str(api_key).strip():
        payload["api_key"] = protect_secret(api_key)
    else:
        payload["api_key"] = str(current.get("api_key") or "")
    AI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    AI_CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return get_ai_settings()


def record_ai_test_status(status: str, message: str) -> dict[str, Any]:
    config = _read_ai_config()
    config["last_test_status"] = str(status or "error")
    config["last_test_message"] = str(message or "")[:500]
    config["last_test_at"] = datetime.now().isoformat(timespec="seconds")
    AI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    AI_CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8")
    return get_ai_settings()


# ── Context builder ───────────────────────────────────────────────────────────

def build_full_qhse_context() -> dict[str, Any]:
    """Collect live QHSE data from all modules for AI injection.

    Uses lazy imports to avoid circular dependencies. Each section is
    wrapped in its own try/except so a failing module never blocks the rest.
    """
    ctx: dict[str, Any] = {"date_heure": datetime.now().strftime("%Y-%m-%d %H:%M")}

    # ── Alerts ────────────────────────────────────────────────────────────────
    try:
        from app.services.alert_service import get_alert_summary
        ctx["alertes"] = get_alert_summary()
    except Exception as exc:
        LOGGER.debug("Context: alerts unavailable: %s", exc)
        ctx["alertes"] = {}

    # ── Maintenance / Actions / Risks ─────────────────────────────────────────
    try:
        from app.services.maintenance_action_service import get_maintenance_action_summary
        ctx["maintenance_actions"] = get_maintenance_action_summary()
    except Exception as exc:
        LOGGER.debug("Context: maintenance unavailable: %s", exc)
        ctx["maintenance_actions"] = {}

    # ── Accidents & incidents ─────────────────────────────────────────────────
    try:
        from app.services.accident_service import (
            compute_kpis,
            get_accident_summary,
            list_accidents,
        )
        recent = list_accidents()[:8]
        ctx["accidents"] = {
            "summary": get_accident_summary(),
            "kpis": compute_kpis(),
            "recents": [
                {
                    "type": a.get("type_evenement"),
                    "date": a.get("date_evenement"),
                    "gravite": a.get("gravite"),
                    "statut": a.get("statut"),
                    "lieu": a.get("lieu"),
                    "description": str(a.get("description") or "")[:150],
                }
                for a in recent
            ],
        }
    except Exception as exc:
        LOGGER.debug("Context: accidents unavailable: %s", exc)
        ctx["accidents"] = {}

    # ── EPI / PPE ─────────────────────────────────────────────────────────────
    try:
        from app.services.ppe_service import get_ppe_summary, list_ppe_expiration_alerts
        expiring = list_ppe_expiration_alerts(days=30)[:10]
        ctx["epi"] = {
            "summary": get_ppe_summary(),
            "expirations_30j": [
                {
                    "nom": e.get("nom"),
                    "type_epi": e.get("type_epi"),
                    "date_expiration": e.get("date_expiration"),
                    "alerte": e.get("alerte"),
                }
                for e in expiring
            ],
        }
    except Exception as exc:
        LOGGER.debug("Context: PPE unavailable: %s", exc)
        ctx["epi"] = {}

    # ── Formations / Training ─────────────────────────────────────────────────
    try:
        from app.services.training_service import get_training_matrix
        matrix = get_training_matrix()
        summary = matrix.get("summary", {})
        stats: list[dict[str, Any]] = matrix.get("training_stats", [])
        critical = sorted(
            [s for s in stats if (s.get("expired", 0) + s.get("missing", 0)) > 0],
            key=lambda s: -(s.get("expired", 0) + s.get("missing", 0)),
        )[:6]
        ctx["formations"] = {
            "summary": summary,
            "types_critiques": [
                {
                    "formation": s.get("formation"),
                    "department": s.get("department"),
                    "expired": s.get("expired", 0),
                    "missing": s.get("missing", 0),
                    "soon": s.get("soon", 0),
                    "valid": s.get("valid", 0),
                    "compliance": s.get("compliance", 0),
                }
                for s in critical
            ],
        }
    except Exception as exc:
        LOGGER.debug("Context: training unavailable: %s", exc)
        ctx["formations"] = {}

    return ctx


# ── Public AI functions ───────────────────────────────────────────────────────

def assistant_answer(question: str, context: dict[str, Any] | None = None) -> str:
    """Single-turn call (backward-compat). Prefer assistant_answer_with_history."""
    return assistant_answer_with_history(question, [], context)


def assistant_answer_with_history(
    question: str,
    history: list[dict[str, str]],
    context: dict[str, Any] | None = None,
) -> str:
    """Multi-turn QHSE assistant with conversation memory.

    history must be a list of {"role": "user"|"assistant", "content": "..."} dicts,
    ordered oldest-first, NOT including the current question.
    """
    clean = str(question or "").strip()
    if not clean:
        raise ValueError("Question obligatoire.")

    context_block = ""
    if context:
        context_json = json.dumps(context, ensure_ascii=False, default=str)
        # Guard: truncate context if it exceeds ~60 KB to stay well within token limits.
        if len(context_json) > 60_000:
            context_json = context_json[:60_000] + "\n... [contexte tronque]"
        context_block = (
            "\n\n--- CONTEXTE OPÉRATIONNEL TEMPS RÉEL ---\n"
            + context_json
            + "\n--- FIN CONTEXTE ---"
        )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": _SYSTEM_PROMPT + context_block},
    ]
    # keep at most 20 history items (10 turns) to avoid token overflow
    messages.extend({"role": m["role"], "content": m["content"]} for m in history[-20:])
    messages.append({"role": "user", "content": clean})

    return _generate_chat(messages, max_tokens=900)


def suggest_risk_assessment(values: dict[str, Any]) -> str:
    return _generate_chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un évaluateur de risques industriels senior (ISO 31000 + ISO 45001). "
                    "Utilise la hiérarchie des contrôles : élimination, substitution, ingénierie, "
                    "administratif, EPI. Tes sorties doivent supporter une revue humaine."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Prépare une suggestion d'évaluation des risques en français avec titres en anglais. "
                    "Structure : 1) Danger, 2) Événement de risque, 3) Conséquences, "
                    "4) Contrôles existants, 5) Contrôles additionnels par hiérarchie, "
                    "6) Avis risque résiduel, 7) Notes de revue.\n\n"
                    f"Données formulaire :\n{json.dumps(values, ensure_ascii=False, default=str)}"
                ),
            },
        ],
        max_tokens=1000,
    )


def suggest_toolbox_theme(values: dict[str, Any]) -> str:
    return _generate_chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu génères des sujets de Toolbox Talk industriels pour les opérations minières "
                    "et de forage. Chaque sujet doit être bilingue et unique pour le mois sélectionné. "
                    "Court, pratique, prêt pour le terrain."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Propose un thème Toolbox Talk bilingue dans ce format exact : "
                    "English topic / Thème français. Ne répète pas les thèmes du mois en cours.\n\n"
                    f"Contexte :\n{json.dumps(values, ensure_ascii=False, default=str)}"
                ),
            },
        ],
        max_tokens=220,
    )


def summarize_alerts_and_reports(context: dict[str, Any]) -> str:
    return _generate_chat(
        messages=[
            {
                "role": "system",
                "content": (
                    "Tu es un assistant de reporting QHSE industriel. "
                    "Priorise les alertes critiques, actions en retard, risques résiduels élevés, "
                    "lacunes de formation et problèmes EPI. Sois concis et orienté action."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Analyse ce contexte QHSE complet et fournis un plan d'action priorisé "
                    "pour les 48 prochaines heures :\n\n"
                    + json.dumps(context, ensure_ascii=False, default=str)
                ),
            },
        ],
        max_tokens=1200,
        temperature=0.5,
    )


def test_ai_connection() -> str:
    return _generate_chat(
        messages=[
            {
                "role": "system",
                "content": "Tu es l'assistant de vérification QHSE. Réponds par une phrase courte.",
            },
            {
                "role": "user",
                "content": "Test de connexion IA OREZONE QHSE. Confirme que tu es opérationnel.",
            },
        ],
        max_tokens=80,
        temperature=0.2,
    )


# ── Backward-compat wrapper (used by nothing external, kept for safety) ───────

def generate_ai_text(
    system_prompt: str,
    user_prompt: str,
    max_output_tokens: int = 800,
) -> str:
    return _generate_chat(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=max_output_tokens,
    )


# ── Core HTTP ─────────────────────────────────────────────────────────────────

def _generate_chat(
    messages: list[dict[str, str]],
    max_tokens: int = 800,
    temperature: float = 0.7,
) -> str:
    settings = get_ai_settings()
    if not settings["enabled"]:
        raise AIConfigurationError(
            "Active l'IA dans Paramètres avant d'utiliser cette fonction."
        )
    api_key = _resolve_api_key(_read_ai_config())
    if not api_key:
        raise AIConfigurationError(
            "Configure une clé API OpenAI dans Paramètres ou via la variable OPENAI_API_KEY."
        )

    payload = {
        "model": settings["model"],
        "messages": messages,
        "max_tokens": int(max_tokens),
        "temperature": temperature,
    }
    req = urllib.request.Request(
        OPENAI_CHAT_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        message = _http_error_message(exc.code, detail)
        LOGGER.warning("OpenAI HTTP error %s: %s", exc.code, message)
        raise AIConfigurationError(message) from exc
    except urllib.error.URLError as exc:
        LOGGER.warning("OpenAI connection unavailable: %s", exc.reason)
        raise AIConfigurationError(f"Connexion IA indisponible : {exc.reason}") from exc
    return _extract_response_text(data)


# ── Private helpers ───────────────────────────────────────────────────────────

def _read_ai_config() -> dict[str, Any]:
    if not AI_CONFIG_PATH.exists():
        return {"enabled": False, "model": DEFAULT_MODEL, "api_key": ""}
    try:
        return json.loads(AI_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"enabled": False, "model": DEFAULT_MODEL, "api_key": ""}


def _resolve_api_key(config: dict[str, Any]) -> str:
    env_key = os.getenv("OPENAI_API_KEY")
    if env_key:
        return env_key.strip()
    return unprotect_secret(config.get("api_key"))


def _migrate_local_api_key(config: dict[str, Any]) -> None:
    raw_key = str(config.get("api_key") or "").strip()
    if not raw_key or is_protected_secret(raw_key):
        return
    try:
        config["api_key"] = protect_secret(raw_key)
        AI_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        AI_CONFIG_PATH.write_text(
            json.dumps(config, ensure_ascii=True, indent=2), encoding="utf-8"
        )
    except OSError as exc:
        LOGGER.warning("AI key migration failed: %s", exc)


def _extract_response_text(data: dict[str, Any]) -> str:
    """Parse OpenAI Chat Completions response."""
    try:
        content = data["choices"][0]["message"]["content"]
        if content:
            return str(content).strip()
    except (KeyError, IndexError):
        pass
    raise AIConfigurationError(
        "La réponse IA est vide ou dans un format non reconnu. "
        "Vérifie le modèle sélectionné dans Paramètres."
    )


def _short_error(detail: str) -> str:
    try:
        msg = json.loads(detail).get("error", {}).get("message")
        if msg:
            return str(msg)[:280]
    except json.JSONDecodeError:
        pass
    return detail[:280]


def _http_error_message(code: int, detail: str) -> str:
    message = _short_error(detail)
    lowered = message.lower()
    if code == 429 and ("quota" in lowered or "billing" in lowered or "exceeded" in lowered):
        return (
            "Quota OpenAI dépassé ou facturation inactive. Ajoute du crédit, active la "
            "facturation ou augmente la limite du projet sur platform.openai.com, "
            "puis relance Tester IA."
        )
    if code == 401:
        return (
            "Clé API OpenAI invalide ou révoquée. "
            "Crée une nouvelle clé et enregistre-la dans Paramètres."
        )
    if code == 404 and "model" in lowered:
        return (
            "Modèle OpenAI introuvable ou non autorisé pour ce compte. "
            "Essaie un autre modèle puis relance Tester IA."
        )
    return f"Erreur OpenAI {code} : {message}"
