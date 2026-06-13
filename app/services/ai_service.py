from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from datetime import datetime

from app.config import DATA_DIR


AI_CONFIG_PATH = DATA_DIR / "ai_config.json"
OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4o-mini"


class AIConfigurationError(ValueError):
    pass


def get_ai_settings() -> dict[str, Any]:
    config = _read_ai_config()
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
        "api_key_source": "Variable OPENAI_API_KEY" if os.getenv("OPENAI_API_KEY") else "Fichier local",
        "config_path": str(AI_CONFIG_PATH),
    }


def save_ai_settings(values: dict[str, Any]) -> dict[str, Any]:
    current = _read_ai_config()
    model = str(values.get("model") or current.get("model") or DEFAULT_MODEL).strip()
    if not model:
        raise ValueError("Modele IA obligatoire.")
    api_key = values.get("api_key")
    clear_api_key = bool(values.get("clear_api_key"))
    key_changed = api_key is not None and str(api_key).strip() and str(api_key).strip() != str(current.get("api_key") or "")
    model_changed = model != str(current.get("model") or DEFAULT_MODEL)
    payload = {
        "enabled": bool(values.get("enabled", current.get("enabled", False))),
        "model": model,
        "last_test_status": "not_tested" if key_changed or model_changed or clear_api_key else str(current.get("last_test_status") or "not_tested"),
        "last_test_message": "" if key_changed or model_changed or clear_api_key else str(current.get("last_test_message") or ""),
        "last_test_at": "" if key_changed or model_changed or clear_api_key else str(current.get("last_test_at") or ""),
    }
    if clear_api_key:
        payload["api_key"] = ""
    elif api_key is not None and str(api_key).strip():
        payload["api_key"] = str(api_key).strip()
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


def assistant_answer(question: str, context: dict[str, Any] | None = None) -> str:
    clean_question = str(question or "").strip()
    if not clean_question:
        raise ValueError("Question obligatoire.")
    return generate_ai_text(
        system_prompt=(
            "You are an industrial QHSE assistant for OREZONE. Answer in French unless the user asks "
            "for English. Be practical, concise, and professional. Do not invent records. Flag anything "
            "that needs human validation or site inspection."
        ),
        user_prompt=(
            f"Question utilisateur:\n{clean_question}\n\n"
            f"Contexte operationnel local JSON:\n{json.dumps(context or {}, ensure_ascii=False, default=str)}"
        ),
        max_output_tokens=900,
    )


def suggest_risk_assessment(values: dict[str, Any]) -> str:
    return generate_ai_text(
        system_prompt=(
            "You are a senior industrial QHSE risk assessor. Use ISO 31000 risk thinking, ISO 45001 "
            "occupational health and safety principles, and the hierarchy of controls: elimination, "
            "substitution, engineering, administrative controls, PPE. Output must support human review."
        ),
        user_prompt=(
            "Prepare a professional risk assessment suggestion in French with English key titles. "
            "Return: 1) Hazard, 2) Risk Event, 3) Consequences, 4) Existing Controls, "
            "5) Additional Controls by hierarchy, 6) Residual Risk Advice, 7) Review/approval notes.\n\n"
            f"Form values JSON:\n{json.dumps(values, ensure_ascii=False, default=str)}"
        ),
        max_output_tokens=1000,
    )


def suggest_toolbox_theme(values: dict[str, Any]) -> str:
    return generate_ai_text(
        system_prompt=(
            "You generate industrial Toolbox Talk topics for mining and drilling operations. Each topic "
            "must be bilingual and unique for the selected month. Keep topics short, practical and field-ready."
        ),
        user_prompt=(
            "Propose one bilingual Toolbox Talk theme in this exact format: "
            "English topic / Theme francais. Do not repeat existing monthly topics.\n\n"
            f"Context JSON:\n{json.dumps(values, ensure_ascii=False, default=str)}"
        ),
        max_output_tokens=220,
    )


def summarize_alerts_and_reports(context: dict[str, Any]) -> str:
    return generate_ai_text(
        system_prompt=(
            "You are an industrial QHSE reporting assistant. Prioritize critical alerts, overdue actions, "
            "high residual risks, training gaps and PPE issues. Be concise and action-oriented."
        ),
        user_prompt=f"Summarize this QHSE context and propose next actions:\n{json.dumps(context, ensure_ascii=False, default=str)}",
        max_output_tokens=900,
    )


def test_ai_connection() -> str:
    return generate_ai_text(
        system_prompt=(
            "You are a QHSE assistant health check. Reply in French with one short sentence confirming "
            "that the AI connection is operational."
        ),
        user_prompt="Test de connexion IA OREZONE QHSE. Reponds uniquement par une confirmation courte.",
        max_output_tokens=80,
    )


def generate_ai_text(system_prompt: str, user_prompt: str, max_output_tokens: int = 800) -> str:
    settings = get_ai_settings()
    if not settings["enabled"]:
        raise AIConfigurationError("Active l'IA dans Parametres avant d'utiliser cette fonction.")
    api_key = _resolve_api_key(_read_ai_config())
    if not api_key:
        raise AIConfigurationError("Configure une cle API OpenAI dans Parametres ou via OPENAI_API_KEY.")

    payload = {
        "model": settings["model"],
        "instructions": system_prompt,
        "input": user_prompt,
        "max_output_tokens": int(max_output_tokens),
    }
    request = urllib.request.Request(
        OPENAI_RESPONSES_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise AIConfigurationError(_http_error_message(exc.code, detail)) from exc
    except urllib.error.URLError as exc:
        raise AIConfigurationError(f"Connexion IA indisponible: {exc.reason}") from exc
    return _extract_response_text(data)


def _read_ai_config() -> dict[str, Any]:
    if not AI_CONFIG_PATH.exists():
        return {"enabled": False, "model": DEFAULT_MODEL, "api_key": ""}
    try:
        return json.loads(AI_CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"enabled": False, "model": DEFAULT_MODEL, "api_key": ""}


def _resolve_api_key(config: dict[str, Any]) -> str:
    return str(os.getenv("OPENAI_API_KEY") or config.get("api_key") or "").strip()


def _extract_response_text(data: dict[str, Any]) -> str:
    output_text = str(data.get("output_text") or "").strip()
    if output_text:
        return output_text
    parts: list[str] = []
    for item in data.get("output") or []:
        if not isinstance(item, dict):
            continue
        for content in item.get("content") or []:
            if isinstance(content, dict) and content.get("text"):
                parts.append(str(content["text"]))
    text = "\n".join(part.strip() for part in parts if part and part.strip())
    if not text:
        raise AIConfigurationError("La reponse IA est vide ou non lisible.")
    return text


def _short_error(detail: str) -> str:
    try:
        data = json.loads(detail)
        message = data.get("error", {}).get("message")
        if message:
            return str(message)[:280]
    except json.JSONDecodeError:
        pass
    return detail[:280]


def _http_error_message(code: int, detail: str) -> str:
    message = _short_error(detail)
    lowered = message.lower()
    if code == 429 and ("quota" in lowered or "billing" in lowered or "exceeded" in lowered):
        return (
            "Quota OpenAI depasse ou facturation inactive. Ajoute du credit, active la facturation "
            "ou augmente la limite du projet sur platform.openai.com, puis relance Tester IA."
        )
    if code == 401:
        return "Cle API OpenAI invalide ou revoquee. Cree une nouvelle cle et enregistre-la dans Parametres."
    if code == 404 and "model" in lowered:
        return "Modele OpenAI introuvable ou non autorise pour ce compte. Essaie un autre modele puis relance Tester IA."
    return f"Erreur OpenAI {code}: {message}"
