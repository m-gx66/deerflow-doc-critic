import json
from langchain.tools import tool


def validate_format(data) -> bool:
    try:
        assert data["verdict"] in ("pass", "revise")
        for i in data.get("issues", []):
            assert i["severity"] in ("blocker", "major", "minor")
            assert i["anchor"].strip()
            assert i["problem"].strip()
            assert i["suggest"].strip()
        return True
    except Exception:
        return False


@tool
def validate_review(review_json: str) -> dict:
    """Validate a critic review JSON. Returns {ok, errors}."""
    try:
        data = json.loads(review_json)
    except json.JSONDecodeError as e:
        return {"ok": False, "errors": [f"json: {e}"]}

    if validate_format(data):
        return {"ok": True, "errors": []}
    return {"ok": False, "errors": ["format invalid"]}