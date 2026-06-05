"""Helpers for turning retrieval results into user-facing scores."""

from __future__ import annotations

import math
import re


def confidence_from_distance(distance: float | None) -> float | None:
    if distance is None:
        return None
    normalized = max(0.0, float(distance))
    return round(1.0 / (1.0 + normalized), 3)


def complexity_from_text(text: str) -> tuple[float, str]:
    """Estimate how structurally complex a snippet is.

    The score is normalized to 0..1 and the label is a simple low/medium/high
    bucket. This is a heuristic, not a true semantic complexity model.
    """

    if not text:
        return 0.0, "low"

    line_count = text.count("\n") + 1
    token_count = len(re.findall(r"\w+", text))
    unique_tokens = len(set(re.findall(r"\w+", text.lower())))
    diversity = unique_tokens / max(1, token_count)

    length_component = min(1.0, line_count / 120.0)
    token_component = min(1.0, token_count / 800.0)
    diversity_component = min(1.0, diversity)

    score = round(
        min(1.0, (0.45 * length_component) + (0.35 * token_component) + (0.20 * diversity_component)),
        3,
    )

    if score < 0.33:
        label = "low"
    elif score < 0.66:
        label = "medium"
    else:
        label = "high"

    return score, label


def format_citation(item: dict) -> str:
    """Build a human-readable citation string from a retrieval result item.

    Returns a formatted string like:
        [GitHub: org/repo/path/file.py]
        [Jira: ABC-123] by jdoe
        [Wiki: Page Title] by jdoe
    """
    source = item.get("source", "kb")
    source_id = item.get("source_id", item.get("id", "?"))
    title = item.get("title", "")
    author = item.get("author")

    # Map internal source name to display label
    source_labels = {
        "github": "GitHub",
        "jira": "Jira",
        "wiki": "Wiki",
        "kb": "KB",
    }
    label = source_labels.get(source, source.upper())

    # Build the core citation part
    if source == "github":
        citation = f"[{label}: {source_id}]"
    elif source == "jira":
        citation = f"[{label}: {source_id}]"
    elif source == "wiki":
        citation = f"[{label}: {title}]" if title else f"[{label}: {source_id}]"
    else:
        citation = f"[{label}: {title or source_id}]"

    # Append attribution if available
    if author:
        citation += f" by {author}"

    return citation


def format_citation_markdown(item: dict) -> str:
    """Build a Markdown link citation from a retrieval result item.

    Returns a formatted string like:
        [org/repo/path/file.py](https://github.com/...) by jdoe
    """
    source = item.get("source", "kb")
    source_url = item.get("source_url", "")
    title = item.get("title", item.get("source_id", "?"))
    author = item.get("author")

    if source_url:
        citation = f"[{title}]({source_url})"
    else:
        citation = f"`{title}`"

    if author:
        citation += f" by {author}"

    return citation
