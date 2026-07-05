"""
model_caller.py — Multi-provider LLM caller with priority chain and backoff.

Provider priority (first key present wins):
  1. Z.AI / GLM  — ZAI_API_KEY   → https://api.z.ai/api/paas/v4
  2. Anthropic    — ANTHROPIC_API_KEY
  3. OpenAI       — OPENAI_API_KEY
  4. Ollama local — always available (no key needed)

All callers return a plain string (the model's text response).
Raises ModelCallerError on total failure across all providers.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

log = logging.getLogger(__name__)


class ModelCallerError(RuntimeError):
    pass


@dataclass
class CallSpec:
    system: str
    user: str
    max_tokens: int = 2048
    temperature: float = 0.4
    model_hint: Optional[str] = None  # override preferred model name


@dataclass
class ProviderResult:
    provider: str
    model: str
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _post_json(url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
    """Thin stdlib POST — no requests dependency."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:400]
        raise ModelCallerError(f"HTTP {exc.code} from {url}: {body}") from exc


def _backoff_call(fn, retries: int = 3, base_delay: float = 1.5):
    """Exponential backoff wrapper."""
    last_exc = None
    for attempt in range(retries):
        try:
            return fn()
        except ModelCallerError as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = base_delay * (2 ** attempt)
                log.warning("Attempt %d failed (%s); retrying in %.1fs", attempt + 1, exc, delay)
                time.sleep(delay)
    raise last_exc


# ---------------------------------------------------------------------------
# Per-provider callers
# ---------------------------------------------------------------------------

def _call_zai(spec: CallSpec) -> ProviderResult:
    api_key = os.environ["ZAI_API_KEY"]
    model = spec.model_hint or os.environ.get("ZAI_MODEL", "glm-4-plus")
    url = "https://api.z.ai/api/paas/v4/chat/completions"
    t0 = time.monotonic()
    resp = _post_json(
        url,
        {
            "model": model,
            "messages": [
                {"role": "system", "content": spec.system},
                {"role": "user", "content": spec.user},
            ],
            "max_tokens": spec.max_tokens,
            "temperature": spec.temperature,
        },
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    text = resp["choices"][0]["message"]["content"]
    usage = resp.get("usage", {})
    return ProviderResult(
        provider="zai",
        model=model,
        text=text,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        latency_ms=(time.monotonic() - t0) * 1000,
    )


def _call_anthropic(spec: CallSpec) -> ProviderResult:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    model = spec.model_hint or os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-20241022")
    url = "https://api.anthropic.com/v1/messages"
    t0 = time.monotonic()
    resp = _post_json(
        url,
        {
            "model": model,
            "system": spec.system,
            "messages": [{"role": "user", "content": spec.user}],
            "max_tokens": spec.max_tokens,
        },
        {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
    )
    text = resp["content"][0]["text"]
    usage = resp.get("usage", {})
    return ProviderResult(
        provider="anthropic",
        model=model,
        text=text,
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        latency_ms=(time.monotonic() - t0) * 1000,
    )


def _call_openai(spec: CallSpec) -> ProviderResult:
    api_key = os.environ["OPENAI_API_KEY"]
    model = spec.model_hint or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    url = "https://api.openai.com/v1/chat/completions"
    t0 = time.monotonic()
    resp = _post_json(
        url,
        {
            "model": model,
            "messages": [
                {"role": "system", "content": spec.system},
                {"role": "user", "content": spec.user},
            ],
            "max_tokens": spec.max_tokens,
            "temperature": spec.temperature,
        },
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    text = resp["choices"][0]["message"]["content"]
    usage = resp.get("usage", {})
    return ProviderResult(
        provider="openai",
        model=model,
        text=text,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        latency_ms=(time.monotonic() - t0) * 1000,
    )


def _call_ollama(spec: CallSpec) -> ProviderResult:
    model = spec.model_hint or os.environ.get("OLLAMA_MODEL", "llama3.2")
    url = f"{os.environ.get('OLLAMA_HOST', 'http://localhost:11434')}/api/chat"
    t0 = time.monotonic()
    resp = _post_json(
        url,
        {
            "model": model,
            "messages": [
                {"role": "system", "content": spec.system},
                {"role": "user", "content": spec.user},
            ],
            "stream": False,
            "options": {"temperature": spec.temperature, "num_predict": spec.max_tokens},
        },
        {"Content-Type": "application/json"},
        timeout=120,
    )
    text = resp["message"]["content"]
    return ProviderResult(
        provider="ollama",
        model=model,
        text=text,
        latency_ms=(time.monotonic() - t0) * 1000,
    )


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

_PROVIDER_CHAIN = [
    ("ZAI_API_KEY", _call_zai),
    ("ANTHROPIC_API_KEY", _call_anthropic),
    ("OPENAI_API_KEY", _call_openai),
    (None, _call_ollama),  # None = always try
]


class ModelCaller:
    """
    Call with priority chain. First provider whose key is present is tried
    (with backoff). If it fails, falls to the next. Ollama is always last.

    Usage:
        caller = ModelCaller()
        result = caller.call(CallSpec(system="...", user="..."))
        print(result.text)
    """

    def __init__(self, preferred_provider: Optional[str] = None):
        """
        preferred_provider: 'zai' | 'anthropic' | 'openai' | 'ollama' | None.
        If None, uses the first provider whose key is set.
        """
        self.preferred_provider = preferred_provider

    def _ordered_chain(self):
        chain = _PROVIDER_CHAIN
        if self.preferred_provider:
            name_map = {
                "zai": _call_zai,
                "anthropic": _call_anthropic,
                "openai": _call_openai,
                "ollama": _call_ollama,
            }
            fn = name_map.get(self.preferred_provider)
            if fn:
                chain = [(None, fn)] + [(k, f) for k, f in chain if f is not fn]
        return chain

    def call(self, spec: CallSpec) -> ProviderResult:
        errors = []
        for key, fn in self._ordered_chain():
            if key and not os.environ.get(key):
                continue
            try:
                result = _backoff_call(lambda f=fn: f(spec))
                log.info(
                    "[model_caller] %s/%s — %d+%d tok, %.0fms",
                    result.provider, result.model,
                    result.input_tokens, result.output_tokens, result.latency_ms,
                )
                return result
            except ModelCallerError as exc:
                log.warning("[model_caller] %s failed: %s", fn.__name__, exc)
                errors.append(f"{fn.__name__}: {exc}")

        raise ModelCallerError(
            "All providers failed:\n" + "\n".join(errors)
        )

    def available_providers(self) -> list[str]:
        out = []
        for key, fn in _PROVIDER_CHAIN:
            if key is None or os.environ.get(key):
                out.append(fn.__name__.lstrip("_call_"))
        return out
