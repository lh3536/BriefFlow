"""Minimal optional LLM client shared by the input/output agents (AO scope).

Stdlib only (urllib): BriefFlow must keep running with no third-party
packages, no network and no API key. Agents treat this module as
best-effort; every call site falls back to deterministic rules on failure.

Configuration via environment variables or a repo-root .env file:
    BRIEF_LLM_API_KEY   - required to enable; missing means LLM disabled
    BRIEF_LLM_BASE_URL  - OpenAI-compatible endpoint, default https://api.openai.com/v1
    BRIEF_LLM_MODEL     - default gpt-4o-mini
    BRIEF_LLM_TIMEOUT   - request timeout in seconds, default 8
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.request

_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_TIMEOUT = 8.0


def _load_dotenv() -> None:
    """Populate missing BRIEF_LLM_* variables from a repo-root .env file."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _config() -> dict:
    _load_dotenv()
    try:
        timeout = float(os.environ.get("BRIEF_LLM_TIMEOUT", _DEFAULT_TIMEOUT))
    except ValueError:
        timeout = _DEFAULT_TIMEOUT
    return {
        "api_key": os.environ.get("BRIEF_LLM_API_KEY", "").strip(),
        "base_url": os.environ.get("BRIEF_LLM_BASE_URL", _DEFAULT_BASE_URL).strip() or _DEFAULT_BASE_URL,
        "model": os.environ.get("BRIEF_LLM_MODEL", _DEFAULT_MODEL).strip() or _DEFAULT_MODEL,
        "timeout": timeout,
    }


def llm_available() -> bool:
    """True only when an API key is configured; never raises."""
    return bool(_config()["api_key"])


def chat_completion(messages: list[dict], *, max_tokens: int = 512) -> str:
    """Return the assistant message content; raises on any failure.

    Callers are responsible for validating the content and falling back to
    deterministic rules. No retries here; retry policy lives with callers.
    """
    cfg = _config()
    if not cfg["api_key"]:
        raise RuntimeError("LLM disabled: BRIEF_LLM_API_KEY is not set")
    body = json.dumps({
        "model": cfg["model"],
        "messages": messages,
        "temperature": 0,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    request = urllib.request.Request(
        cfg["base_url"].rstrip("/") + "/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['api_key']}",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=cfg["timeout"]) as response:
        payload = json.loads(response.read().decode("utf-8"))
    content = payload["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("LLM response content is not a string")
    return content
