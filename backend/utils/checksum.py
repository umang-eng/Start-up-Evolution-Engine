"""
Semantic Checksum Utilities — Deterministic Input Hashing for Pipeline Caching

Computes a SHA-256 hash from the exact inputs that would be fed to a pipeline stage.
This allows the orchestrator to detect when upstream data hasn't changed and skip
redundant LLM calls entirely.

Hash Design:
- Deterministic: same inputs always produce the same hash
- Cascade-aware: includes all upstream stage outputs that feed into the current stage
- Project-scoped: includes project title/industry/description as base seeds
- JSON-stable: sorts keys, normalizes floats, strips whitespace from strings
"""

import hashlib
import json
from typing import Any


# ── Stage Dependency Graph ──────────────────────────────────────────
# Defines which upstream context keys each stage depends on.
# Used by compute_stage_checksum to know exactly what to include.

STAGE_INPUT_DEPENDENCIES: dict[str, list[str]] = {
    "dna":              [],                                                    # Only project base inputs
    "features":         ["dna"],                                               # Depends on DNA output
    "roadmap":          ["dna", "features"],                                   # Depends on DNA + Features
    "team":             ["dna", "features", "roadmap"],                        # Depends on DNA + Features + Roadmap
    "swot":             ["dna", "features", "roadmap", "team"],                # Depends on DNA + Features + Roadmap + Team
    "cost":             ["dna", "features", "roadmap", "team", "swot"],        # All previous
    "blueprint":        ["dna", "features", "roadmap", "team", "swot", "cost"],# All previous
    "legal_compliance": ["dna", "cost"],                                       # Depends on DNA + Cost
}


def _stable_json_dumps(obj: Any) -> str:
    """Produce a deterministic JSON string for any Python object.

    - Sorts all dict keys recursively
    - Normalizes floats to 2 decimal places for stability
    - Strips whitespace from strings
    - Uses separators=(',', ':') for compact output
    """
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_default_handler,
        ensure_ascii=True,
    )


def _json_default_handler(obj: Any) -> Any:
    """Fallback serializer for non-standard types."""
    if isinstance(obj, float):
        return round(obj, 2)
    if isinstance(obj, set):
        return sorted(obj)
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "__dict__"):
        return {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def _normalize_value(value: Any) -> Any:
    """Recursively normalize a value for stable hashing."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, float):
        return round(value, 2)
    if isinstance(value, dict):
        return {k: _normalize_value(value[k]) for k in sorted(value.keys())}
    if isinstance(value, (list, tuple)):
        return [_normalize_value(item) for item in value]
    return value


def compute_stage_checksum(
    stage_name: str,
    project_title: str,
    project_industry: str | None,
    project_description: str | None,
    context: dict[str, Any],
) -> str:
    """Compute a deterministic SHA-256 checksum for a pipeline stage's inputs.

    The hash covers:
    1. Project base inputs (title, industry, description)
    2. All upstream stage outputs that this stage depends on (from context dict)

    Args:
        stage_name: Name of the stage (e.g. "dna", "features", "roadmap")
        project_title: Project title string
        project_industry: Project industry string (may be None)
        project_description: Project description string (may be None)
        context: Full context dict containing upstream stage results

    Returns:
        Hex-encoded SHA-256 hash string (64 chars)
    """
    # 1. Build the input payload
    payload: dict[str, Any] = {
        "_project": {
            "title": (project_title or "").strip(),
            "industry": (project_industry or "").strip(),
            "description": (project_description or "").strip(),
        },
        "_stage": stage_name,
    }

    # 2. Attach only the upstream dependencies this stage needs
    dependencies = STAGE_INPUT_DEPENDENCIES.get(stage_name, [])
    for dep_key in dependencies:
        dep_data = context.get(dep_key)
        if dep_data is not None:
            payload[dep_key] = _normalize_value(dep_data)

    # 3. Serialize deterministically and hash
    stable_json = _stable_json_dumps(payload)
    checksum = hashlib.sha256(stable_json.encode("utf-8")).hexdigest()

    return checksum


def compute_checksum_from_result_data(
    stage_name: str,
    project_title: str,
    project_industry: str | None,
    project_description: str | None,
    result_data: dict[str, Any],
) -> str:
    """Compute checksum for a result that was just generated (cache-miss path).

    This is called after an LLM call succeeds, to store the checksum alongside
    the result. On subsequent runs, the orchestrator computes the *input* checksum
    and compares it against this stored *output* checksum.

    Actually, for cache comparison we need the INPUT checksum (what went into
    the stage), not the output. So this function builds a context dict from
    the result_data and computes the same way as compute_stage_checksum.

    The key insight: we store the INPUT checksum alongside the OUTPUT data.
    When re-running, we compute a new INPUT checksum and compare.
    """
    # Build a synthetic context that includes only the dependencies
    # that were actually used to produce this result
    dependencies = STAGE_INPUT_DEPENDENCIES.get(stage_name, [])
    synthetic_context: dict[str, Any] = {}
    for dep_key in dependencies:
        if dep_key in result_data:
            synthetic_context[dep_key] = result_data[dep_key]

    return compute_stage_checksum(
        stage_name=stage_name,
        project_title=project_title,
        project_industry=project_industry,
        project_description=project_description,
        context=synthetic_context,
    )
