"""SSE serialization helpers — convert Pydantic-laden LangGraph events to
JSON-safe primitives BEFORE handing them to ``ctx.utils.sse``.

Why this exists:

The platform's ``ctx.utils.sse(data, ...)`` calls ``json.dumps(data, ...)``
and falls back to ``str(data)`` on ``TypeError`` (see
``.edgeone/agent-python/_platform/context.py:sse``). LangGraph
``stream_mode="updates"`` events look like::

    {"classify": {"classified": [<ClassifiedEmail …>, …]}}

…where the leaf values are Pydantic v2 models. ``json.dumps`` can't
serialize those, the platform writes a Python repr to the wire, and the
frontend can't parse it as JSON — so the inbox tree never fills and the
pipeline visualizer never advances.

The fix is to recursively coerce Pydantic / dataclass / list / dict / set
nodes into JSON-safe types using ``model_dump(mode="json")`` (which also
handles datetime → ISO strings, UUID → str, etc.). We do this exactly
once per yielded SSE frame, in the handlers — node code stays unchanged.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def to_jsonable(obj: Any) -> Any:
    """Recursively convert ``obj`` into JSON-safe primitives.

    - Pydantic v2 models → ``model_dump(mode="json")``
    - Pydantic v1 models / objects with ``.dict()`` → ``.dict()``
    - dataclasses → ``asdict``
    - dict / list / tuple / set → recurse into elements
    - everything else (str, int, float, bool, None) → returned as-is
    - last-resort fallback for unknown objects → ``str(obj)``
    """
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj

    # Pydantic v2 (preferred): model_dump(mode="json") handles datetime / UUID etc.
    if hasattr(obj, "model_dump"):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            pass

    # Pydantic v1 fallback (uses dict()).
    if hasattr(obj, "dict") and callable(getattr(obj, "dict", None)):
        try:
            return to_jsonable(obj.dict())
        except Exception:
            pass

    if is_dataclass(obj) and not isinstance(obj, type):
        return to_jsonable(asdict(obj))

    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set, frozenset)):
        return [to_jsonable(v) for v in obj]

    # LangGraph wraps interrupt payloads in an Interrupt namedtuple-ish object.
    if hasattr(obj, "value"):
        try:
            return to_jsonable(getattr(obj, "value"))
        except Exception:
            pass

    # Fallback — keep the wire format JSON-safe even for surprises.
    return str(obj)
