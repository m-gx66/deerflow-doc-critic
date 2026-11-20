from __future__ import annotations

import json
import re

from langchain.tools import tool


VALID_VERDICTS = ("pass", "revise")
VALID_SEVERITIES = ("blocker", "major", "minor")


def _parse_review(review_json: str | dict) -> dict:
    if isinstance(review_json, dict):
        return review_json
    text = review_json.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("review must be a JSON object")
    return data


def _validate_review(data: dict) -> list[str]:
    errors: list[str] = []
    if data.get("verdict") not in VALID_VERDICTS:
        errors.append("verdict must be pass or revise")

    issues = data.get("issues", [])
    if not isinstance(issues, list):
        return errors + ["issues must be a list"]

    if data.get("verdict") == "pass" and issues:
        errors.append("verdict=pass must have empty issues")
    if data.get("verdict") == "revise" and not issues:
        errors.append("verdict=revise must have at least one issue")

    for i, issue in enumerate(issues):
        if not isinstance(issue, dict):
            errors.append(f"issues[{i}] must be object")
            continue
        if issue.get("severity") not in VALID_SEVERITIES:
            errors.append(f"issues[{i}].severity invalid")
        for key in ("anchor", "problem", "suggest"):
            value = issue.get(key)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"issues[{i}].{key} missing")

    return errors


@tool
def rework_guard(
    review_json: str,
    round_no: int = 0,
    max_rounds: int = 2,
) -> dict:
    """Decide whether a critic review may trigger another rework round.

    Args:
        review_json: Critic review JSON string.
        round_no: Number of completed rework rounds; initial review is 0.
        max_rounds: Maximum edit rounds (clamped to 1..3).

    Returns:
        {
          "status": "continue|resolved|unresolved|invalid",
          "needs_rework": bool,
          "round_no": int,
          "max_rounds": int,
          "next_round": int | None,
          "blockers": [...],
          "remaining_issues": [...],
          "unresolved": [...],
          "errors": [...]
        }
    """
    max_rounds = max(1, min(3, int(max_rounds)))
    round_no = max(0, int(round_no))

    try:
        review = _parse_review(review_json)
    except Exception as exc:
        return {
            "status": "invalid",
            "needs_rework": False,
            "round_no": round_no,
            "max_rounds": max_rounds,
            "next_round": None,
            "blockers": [],
            "remaining_issues": [],
            "unresolved": [],
            "errors": [f"json: {exc}"],
        }

    errors = _validate_review(review)
    if errors:
        return {
            "status": "invalid",
            "needs_rework": False,
            "round_no": round_no,
            "max_rounds": max_rounds,
            "next_round": None,
            "blockers": [],
            "remaining_issues": [],
            "unresolved": [],
            "errors": errors,
        }

    issues = review.get("issues", [])
    blockers = [
        issue for issue in issues
        if issue.get("severity") == "blocker"
    ]
    remaining = [
        issue for issue in issues
        if issue.get("severity") != "blocker"
    ]

    if not blockers:
        return {
            "status": "resolved",
            "needs_rework": False,
            "round_no": round_no,
            "max_rounds": max_rounds,
            "next_round": None,
            "blockers": [],
            "remaining_issues": remaining,
            "unresolved": [],
            "errors": [],
        }

    if round_no >= max_rounds:
        return {
            "status": "unresolved",
            "needs_rework": False,
            "round_no": round_no,
            "max_rounds": max_rounds,
            "next_round": None,
            "blockers": blockers,
            "remaining_issues": remaining,
            "unresolved": blockers,
            "errors": [],
        }

    return {
        "status": "continue",
        "needs_rework": True,
        "round_no": round_no,
        "max_rounds": max_rounds,
        "next_round": round_no + 1,
        "blockers": blockers,
        "remaining_issues": remaining,
        "unresolved": [],
        "errors": [],
    }


__all__ = ["rework_guard"]
