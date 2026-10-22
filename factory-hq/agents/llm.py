"""Factory HQ shared LLM backend (v2.0). Standard library only.

ask(prompt, system=None, max_tokens=800):
  - reads ANTHROPIC_API_KEY / OPENAI_API_KEY from the environment
    (or from a .env file next to app.py - never committed to git)
  - tries Anthropic Claude first, falls back to OpenAI if the first
    key is missing or the call fails
  - returns the text answer, or None when no key is set (or both fail),
    so agents fall back to their deterministic rule-based mode

Keys are never hardcoded, never logged, never written to files.
"""
import json
import os
import urllib.request

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-5"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-4o-mini"
TIMEOUT = 60


def _load_dotenv():
    """Load KEY=VALUE lines from factory/.env into os.environ (no override)."""
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    try:
        with open(env_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip("'\"")
                if k and v and k not in os.environ:
                    os.environ[k] = v
    except FileNotFoundError:
        pass


def _post(url, headers, payload):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def _ask_anthropic(key, prompt, system, max_tokens):
    headers = {
        "x-api-key": key,  # never logged
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {"model": ANTHROPIC_MODEL, "max_tokens": max_tokens,
               "messages": [{"role": "user", "content": prompt}]}
    if system:
        payload["system"] = system
    data = _post(ANTHROPIC_URL, headers, payload)
    parts = [b.get("text", "") for b in data.get("content", [])
             if b.get("type") == "text"]
    text = "".join(parts).strip()
    return text or None


def _ask_openai(key, prompt, system, max_tokens):
    headers = {"Authorization": "Bearer " + key,  # never logged
               "content-type": "application/json"}
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    payload = {"model": OPENAI_MODEL, "max_tokens": max_tokens,
               "messages": messages}
    data = _post(OPENAI_URL, headers, payload)
    text = (data.get("choices", [{}])[0].get("message", {})
            .get("content", "") or "").strip()
    return text or None


def ask(prompt, system=None, max_tokens=800):
    """Return the model's answer text, or None when no key is available."""
    if not prompt:
        return None
    _load_dotenv()
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        try:
            return _ask_anthropic(key, prompt, system, max_tokens)
        except Exception:
            pass  # fall through to OpenAI
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        try:
            return _ask_openai(key, prompt, system, max_tokens)
        except Exception:
            pass
    return None
