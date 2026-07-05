"""
model_router_adapter.py
-----------------------
Drops model_caller.py's interface while routing all calls through
zai-wrap's ModelRouter (the canonical multi-provider gateway).

Usage in improve_skill.py, trigger_dispatcher.py, etc.:

    from model_router_adapter import call_model, call_model_for_task

    # Direct model call (mimics old model_caller.call_model signature)
    response = call_model(prompt, model="claude/claude-sonnet-4-5")

    # Task-routed call (uses fallback chains from model_gateway.py)
    response = call_model_for_task(prompt, task_type="code")

Falls back to the original model_caller.py if zai-wrap is not on the path.
"""

import logging
import os
import sys
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Try to import ModelRouter from zai-wrap
# ---------------------------------------------------------------------------

_router = None
_router_available = False

def _init_router():
    global _router, _router_available
    if _router is not None:
        return

    zai_path = os.getenv("ZAI_WRAP_PATH", "../zai-wrap")
    sys.path.insert(0, zai_path)
    try:
        from model_gateway import ModelRouter  # noqa
        _router = ModelRouter()
        _router_available = True
        logger.info("model_router_adapter: ModelRouter loaded from zai-wrap")
    except ImportError:
        logger.warning(
            "model_router_adapter: zai-wrap ModelRouter not found at %s — "
            "falling back to local model_caller.py", zai_path
        )
    except Exception as exc:
        logger.warning("model_router_adapter: ModelRouter init failed: %s", exc)


# ---------------------------------------------------------------------------
# Backwards-compatible model_caller shim
# ---------------------------------------------------------------------------

_local_caller = None

def _get_local_caller():
    global _local_caller
    if _local_caller is None:
        try:
            import model_caller as mc
            _local_caller = mc
        except ImportError:
            pass
    return _local_caller


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def call_model(
    prompt: str,
    model: str = "claude/claude-sonnet-4-5",
    system: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.3,
    **kwargs,
) -> str:
    """
    Direct model call. Model string format: "provider/model-name".
    Falls back to model_caller.py if ModelRouter unavailable.
    """
    _init_router()

    if _router_available:
        try:
            resp = _router.call(
                prompt=prompt,
                model=model,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.content
        except Exception as exc:
            logger.warning("ModelRouter.call failed (%s): %s — falling back", model, exc)

    # Fallback: original model_caller
    caller = _get_local_caller()
    if caller:
        try:
            return caller.call_model(prompt, model=model, **kwargs)
        except Exception as exc:
            logger.error("model_caller fallback also failed: %s", exc)

    raise RuntimeError(
        f"No model backend available. Tried ModelRouter and model_caller. prompt[:80]={prompt[:80]!r}"
    )


def call_model_for_task(
    prompt: str,
    task_type: str = "reasoning",
    system: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.3,
) -> str:
    """
    Task-routed call. task_type ∈ {code, reasoning, fast, creative, vision}.
    Runs the fallback chain defined in model_gateway.ModelRouter.
    Falls back to call_model(model=default) if router unavailable.
    """
    _init_router()

    if _router_available:
        try:
            resp = _router.route(
                prompt=prompt,
                task_type=task_type,
                system=system,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.content
        except Exception as exc:
            logger.warning("ModelRouter.route failed (task=%s): %s — falling back", task_type, exc)

    # Fallback: pick a sensible default model per task type
    task_defaults = {
        "code": "deepseek/deepseek-coder",
        "reasoning": "claude/claude-sonnet-4-5",
        "fast": "deepseek/deepseek-chat",
        "creative": "claude/claude-sonnet-4-5",
        "vision": "claude/claude-opus-4-5",
    }
    default_model = task_defaults.get(task_type, "claude/claude-sonnet-4-5")
    return call_model(prompt, model=default_model, system=system,
                      max_tokens=max_tokens, temperature=temperature)


def usage_summary() -> Dict[str, Any]:
    """Return per-model usage stats from ModelRouter if available."""
    _init_router()
    if _router_available:
        try:
            return _router.usage_summary()
        except Exception:
            pass
    return {}
