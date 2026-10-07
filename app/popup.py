"""Parse dashboard popup attributes from GeoParquet scalar values.

Input schema: a scalar or serialized list from the ``breached_rules`` column.
Output schema: a list containing only rule identifier strings.
"""

from __future__ import annotations

import ast


def parse_breached_rules(value: object) -> list[str]:
    """Safely normalize a breached-rules attribute without evaluating code."""
    if isinstance(value, (list, tuple)):
        return [item for item in value if isinstance(item, str)]
    if not isinstance(value, str) or not value:
        return []
    if not value.startswith("["):
        return [value]
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return [value]
    if isinstance(parsed, list) and all(isinstance(item, str) for item in parsed):
        return parsed
    return [value]
