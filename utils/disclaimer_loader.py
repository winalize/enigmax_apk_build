"""Disclaimer loader.

Android note:
    The APK-packaged `data/disclaimer.json` is an asset (read-only). Therefore we only
    *read* it here using Kivy's resource lookup to avoid CWD/path issues.
"""

import json
from typing import Any, Dict

from kivy.resources import resource_find


def _load_raw_disclaimer_json() -> Dict[str, Any]:
    # Prefer exact relative path; fall back to filename-only (some packagers flatten).
    cand = resource_find("data/disclaimer.json") or resource_find("disclaimer.json")
    if not cand:
        raise FileNotFoundError("disclaimer.json not found in packaged resources")
    with open(cand, "r", encoding="utf-8") as f:
        return json.load(f)


def load_disclaimer(lang: str = "en") -> Dict[str, Any]:
    data = _load_raw_disclaimer_json()
    texts = data.get("texts", {}) or {}
    version = data.get("version", 1)
    acceptance_text = data.get("acceptance_text", {}) or {}
    updated_at = data.get("updated_at", "")

    if lang not in texts:
        lang = "en" if "en" in texts else (next(iter(texts.keys()), "en"))

    return {
        "version": version,
        "updated_at": updated_at,
        "acceptance_text": acceptance_text,
        "title": (texts.get(lang, {}) or {}).get("title", "Disclaimer"),
        "body": (texts.get(lang, {}) or {}).get("body", ""),
        "texts": texts,
    }

