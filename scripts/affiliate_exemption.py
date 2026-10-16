#!/usr/bin/env python3
"""Shared editorial exemption contract for the weekly and daily guards (#762).

Only an explicit YAML boolean plus a nonempty reason waives the minimum-link
requirement. Existing links and broken CTA boxes are NEVER exempt from checks.
Malformed metadata remains a content error; a missing YAML dependency fails
loudly rather than silently allowing an exception.

ONE CONTRACT, ONE EVALUATOR (WF-53E2 / #780, 16.10.2026)
--------------------------------------------------------
This module is the only place that reads ``affiliate_exempt`` and
``affiliate_exempt_reason``. Consumers call one of the entry points below and
never re-implement the reading (own frontmatter split, own YAML load, or a
re-export imported from another guard). PR #776 did exactly that in two
guards, wrapped in ``except Exception``: a read error silently became
"not exempt", the daily guard's detector self-test went red and the guard
stood fail-closed (#780). ``scripts/tests/test_affiliate_exemption.py``
enforces the rule structurally.

Entry points:
  affiliate_exemption(frontmatter)  frontmatter text (YAML block)
  exemption_for_article(article)    integrity-gate article dicts (``fm``)
  exemption_for_text(text)          a raw Markdown file (profi check A8)
"""
from __future__ import annotations

import yaml

from post_utils import split_article


def affiliate_exemption(frontmatter: str) -> tuple[bool, str, str]:
    """Return (exempt, reason, metadata_error); semantics preserved from #742."""
    try:
        metadata = yaml.safe_load(frontmatter) or {}
    except yaml.YAMLError as exc:
        detail = str(exc).splitlines()[0] if str(exc) else "YAML-Fehler"
        return False, "", f"Frontmatter ist kein gültiges YAML: {detail}"
    if not isinstance(metadata, dict):
        return False, "", "Frontmatter muss ein YAML-Objekt sein"

    has_flag = "affiliate_exempt" in metadata
    raw_exempt = metadata.get("affiliate_exempt")
    raw_reason = metadata.get("affiliate_exempt_reason")
    reason = raw_reason.strip() if isinstance(raw_reason, str) else ""

    if not has_flag:
        if raw_reason is None or (isinstance(raw_reason, str) and not reason):
            return False, "", ""
        return False, "", (
            "affiliate_exempt_reason ist gesetzt, aber "
            "affiliate_exempt: true fehlt"
        )
    if not isinstance(raw_exempt, bool):
        return False, "", "affiliate_exempt muss ein YAML-Boolean true oder false sein"
    if raw_exempt:
        if not reason:
            return False, "", "affiliate_exempt: true braucht eine nichtleere Begründung"
        if not isinstance(raw_reason, str):
            return False, "", "affiliate_exempt_reason muss Text sein"
        return True, reason, ""
    if raw_reason is not None and (not isinstance(raw_reason, str) or reason):
        return False, "", (
            "affiliate_exempt_reason darf nur mit affiliate_exempt: true "
            "angegeben werden"
        )
    return False, "", ""


def exemption_for_article(article: dict) -> tuple[bool, str, str]:
    """Adapter for integrity articles, including direct render-proof callers."""
    return affiliate_exemption(article.get("fm", ""))


def exemption_for_text(text: str) -> tuple[bool, str, str]:
    """Adapter for callers holding a raw Markdown file (#780).

    The frontmatter boundary is the one Hugo sees (``post_utils.split_article``)
    – no caller-side ``split("---", 2)``. A file without frontmatter has no
    exemption and no metadata error.
    """
    _prefix, frontmatter, _body = split_article(text or "")
    return affiliate_exemption(frontmatter)


def exemption_label(reason: str) -> str:
    """Keep reasons safe for one-line Markdown reports."""
    return " ".join(reason.split()).replace("|", "\\|").replace("`", "'")
