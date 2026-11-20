# 格式、锚点与产物校验

## critic校验代码

来源：`df/critic机制/校验代码/critic校验代码.md`

import json

def parse_review(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    data = json.loads(text)
    assert data["verdict"] in ("pass", "fail")
    for issue in data.get("issues", []):
        assert issue["severity"] in ("blocker", "major", "minor")
        assert issue["location"].strip()
        assert issue["evidence"].strip()
    return data

## doc校验代码

来源：`df/critic机制/校验代码/doc校验代码.md`

from __future__ import annotations

import json
import re
import unicodedata
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_ANCHOR_RE = re.compile(r"(第\s*\d+\s*段|p\.?\s*\d+|L\d+)", re.IGNORECASE)


@dataclass
class ValidationResult:
    ok: bool
    mode: str | None = None
    data: dict[str, Any] | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json_output(text: str) -> dict[str, Any]:
    data = json.loads(strip_fences(text))
    if not isinstance(data, dict):
        raise ValueError("top-level JSON must be an object")
    return data


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def quote_in_original(original: str, quote: str) -> bool:
    if not isinstance(quote, str) or not quote.strip():
        return False
    return normalize_text(quote) in normalize_text(original)


def resolve_output_path(output_file: str, workspace_root: Path) -> Path | None:
    """把 /mnt/user-data/... 映射到本机 workspace_root，也接受绝对路径。"""
    if not isinstance(output_file, str) or not output_file.strip():
        return None
    raw = output_file.strip()
    prefix = "/mnt/user-data/"
    if raw.startswith(prefix):
        return (workspace_root / raw[len(prefix):]).resolve()
    p = Path(raw)
    return p if p.is_absolute() else (workspace_root / p).resolve()


def validate_analyze(data: dict[str, Any], original: str) -> list[str]:
    errors: list[str] = []
    notes = data.get("notes")
    if not isinstance(notes, list) or not notes:
        return ["analyze.notes must be a non-empty list"]

    for i, note in enumerate(notes):
        if not isinstance(note, dict):
            errors.append(f"notes[{i}] must be an object")
            continue
        anchor = note.get("anchor")
        if not isinstance(anchor, str) or not _ANCHOR_RE.search(anchor):
            errors.append(f"notes[{i}].anchor invalid: {anchor!r}")
        quote = note.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            errors.append(f"notes[{i}].quote missing")
        elif not quote_in_original(original, quote):
            errors.append(f"notes[{i}].quote not found in original: {quote[:40]!r}")
        if not isinstance(note.get("note"), str) or not note["note"].strip():
            errors.append(f"notes[{i}].note missing")

    coverage = data.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("analyze.coverage must be an object")
    else:
        total = coverage.get("sections_total")
        covered = coverage.get("sections_covered")
        if not isinstance(total, int) or not isinstance(covered, int):
            errors.append("coverage values must be integers")
        elif total < 0 or covered < 0 or covered > total:
            errors.append(f"coverage invalid: {covered}/{total}")
    return errors


def validate_edit(data: dict[str, Any], original: str, workspace_root: Path) -> list[str]:
    errors: list[str] = []
    changes = data.get("changes")
    if not isinstance(changes, list) or not changes:
        return ["edit.changes must be a non-empty list"]

    for i, change in enumerate(changes):
        if not isinstance(change, dict):
            errors.append(f"changes[{i}] must be an object")
            continue
        anchor = change.get("anchor")
        if not isinstance(anchor, str) or not _ANCHOR_RE.search(anchor):
            errors.append(f"changes[{i}].anchor invalid: {anchor!r}")
        before = change.get("before")
        if not isinstance(before, str) or not before.strip():
            errors.append(f"changes[{i}].before missing")
        elif not quote_in_original(original, before):
            errors.append(f"changes[{i}].before not found in original")
        after = change.get("after")
        if not isinstance(after, str) or not after.strip():
            errors.append(f"changes[{i}].after missing")
        if not isinstance(change.get("reason"), str) or not change["reason"].strip():
            errors.append(f"changes[{i}].reason missing")

    path = resolve_output_path(data.get("output_file"), workspace_root)
    if path is None:
        errors.append("edit.output_file missing")
    elif not path.exists():
        errors.append(f"output file not found: {path}")
    elif path.stat().st_size == 0:
        errors.append(f"output file is empty: {path}")
    elif path.suffix.lower() == ".docx":
        try:
            with zipfile.ZipFile(path) as zf:
                bad = zf.testzip()
                if bad:
                    errors.append(f"docx has corrupt member: {bad}")
                if "word/document.xml" not in zf.namelist():
                    errors.append("docx missing word/document.xml")
        except zipfile.BadZipFile:
            errors.append(f"output file is not a valid docx zip: {path}")
    return errors


def validate_doc_output(
    text: str,
    original: str,
    workspace_root: Path,
) -> ValidationResult:
    try:
        data = parse_json_output(text)
    except (json.JSONDecodeError, ValueError) as exc:
        return ValidationResult(ok=False, errors=[f"invalid JSON: {exc}"])

    mode = data.get("mode")
    if mode == "analyze":
        errors = validate_analyze(data, original)
    elif mode == "edit":
        errors = validate_edit(data, original, workspace_root)
    else:
        errors = [f"unknown mode: {mode!r}"]
    return ValidationResult(ok=not errors, mode=mode, data=data, errors=errors)
