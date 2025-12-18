"""Model aliases and validation."""

from typing import Dict, List

# Model aliases for convenience
MODEL_ALIASES: Dict[str, str] = {
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-5-20251101",
    "haiku": "claude-haiku-3-5-20241022",
    # Legacy aliases
    "sonnet-3.5": "claude-3-5-sonnet-20241022",
    "haiku-3.5": "claude-3-5-haiku-20241022",
    "opus-3": "claude-3-opus-20240229",
}

# List of valid model prefixes
VALID_MODEL_PREFIXES: List[str] = [
    "claude-sonnet-",
    "claude-opus-",
    "claude-haiku-",
    "claude-3-",
    "claude-3.5-",
]


def resolve_model(model_name: str) -> str:
    """Resolve model alias to full model name.

    Args:
        model_name: Model alias or full model name

    Returns:
        Full model name
    """
    # Check if it's an alias
    if model_name.lower() in MODEL_ALIASES:
        return MODEL_ALIASES[model_name.lower()]

    # Return as-is if it looks like a full model name
    return model_name


def validate_model(model_name: str) -> bool:
    """Check if model name is valid.

    Args:
        model_name: Model name to validate

    Returns:
        True if valid, False otherwise
    """
    # Resolve alias first
    resolved = resolve_model(model_name)

    # Check if it starts with a valid prefix
    for prefix in VALID_MODEL_PREFIXES:
        if resolved.startswith(prefix):
            return True

    return False


def get_model_info(model_name: str) -> Dict[str, str]:
    """Get information about a model.

    Args:
        model_name: Model name or alias

    Returns:
        Dictionary with model info
    """
    resolved = resolve_model(model_name)

    return {
        "name": resolved,
        "alias": model_name if model_name != resolved else None,
        "family": _get_model_family(resolved),
    }


def _get_model_family(model_name: str) -> str:
    """Get the model family from a model name."""
    if "opus" in model_name.lower():
        return "opus"
    elif "sonnet" in model_name.lower():
        return "sonnet"
    elif "haiku" in model_name.lower():
        return "haiku"
    return "unknown"
