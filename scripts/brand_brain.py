#!/usr/bin/env python3
# ============================================================
#  BRAND BRAIN – Lader, Validator & Wächter (AGC-Parität, Stufe 1)
#  ------------------------------------------------------------
#  Single Source of Truth: data/brand_brain.yaml. Dieses Skript
#    - lädt das Brand Brain defensiv (fehlende Datei → Defaults,
#      nie ein Crash der Pipeline),
#    - validiert Struktur/Pflichtfelder,
#    - prüft die kanonischen Marken-Texte GEGEN data/brand_lock.yaml
#      (Drift-Wächter: description, disclaimer, home_title),
#    - liefert den kompakten "Marken-Hirn"-Block für Prompt-Injektion.
#
#  Aufruf:
#    python3 scripts/brand_brain.py              # validieren + Report
#    python3 scripts/brand_brain.py --selftest   # Exit 0/2 (für Workflows)
#    python3 scripts/brand_brain.py --fix        # Drift aus brand_lock heilen
#    python3 scripts/brand_brain.py --context    # Marken-Hirn-Block drucken
#
#  FAIL-CLOSED-Prinzip: Kann data/brand_lock.yaml nicht gelesen werden,
#  meldet --selftest den Werkzeugfehler (Exit 2) statt still "grün".
# ============================================================
import os
import sys

import yaml

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRAIN_FILE = os.path.join(BLOG_DIR, "data", "brand_brain.yaml")
LOCK_FILE = os.path.join(BLOG_DIR, "data", "brand_lock.yaml")

# Kanonische Keys, die 1:1 aus brand_lock.yaml gespiegelt werden müssen.
LOCK_KEY_MAP = {
    "params.description": "canonical.description",
    "params.disclaimer": "canonical.disclaimer",
    "homeInfoParams.Title": "canonical.home_title",
}

# Minimal-Struktur: bei beschädigter/fehlender Datei wird mit diesen Defaults
# weitergearbeitet (Autopilot darf nie am Brand Brain scheitern).
DEFAULTS = {
    "brand": {
        "name": "FranksFinanzcheck",
        "author": "Frank Hartung",
        "domain": "https://franksfinanzcheck.de/",
        "tagline": "So holst du mit ehrlichen Tipps das Beste aus deinem Geld",
        "niche": "Geld sparen leicht gemacht: Praxis-Ratgeber",
        "value_proposition": "Fixkosten senken – bis zu 1.800 € pro Jahr.",
        "languages": ["de"],
    },
    "voice": {
        "tone": "ehrlich, praxisnah, auf Augenhöhe",
        "anrede": "du",
        "perspectives": ["direkt", "erfahrung", "neutral"],
        "redaktionsstandard": "Capital · WirtschaftsWoche · DIE ZEIT",
        "forbidden_phrases": [
            "In der heutigen schnelllebigen Welt",
            "Zusammenfassend lässt sich sagen",
            "Tauchen wir ein",
        ],
    },
    "avatar": {
        "name": "Frank Hartung",
        "rolle": "Autor & Finanz-Praktiker",
        "erfahrung": "über zehn Jahre Erfahrung im Finanzbereich",
    },
    "default_cta": "Jetzt bei CHECK24 vergleichen",
    "products": [],
    "audience": {"primary": "", "secondary": "", "pain_points": []},
    "hard_rules": [],
    "frameworks": {"editorial": [], "openings": [], "hooks": []},
}


def load_brand_brain(path=None):
    """Lädt das Brand Brain defensiv. Fehlt die Datei oder ist sie kaputt,
    werden Defaults mit einem `_defaults_used`-Flag zurückgegeben."""
    path = path or BRAIN_FILE
    if not os.path.exists(path):
        brain = dict(DEFAULTS)
        brain["_defaults_used"] = True
        return brain
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:
        brain = dict(DEFAULTS)
        brain["_defaults_used"] = True
        return brain
    if not isinstance(data, dict):
        data = {}
    brain = _deep_merge(dict(DEFAULTS), data)
    return brain


def _deep_merge(base, override):
    """Merge override dict in base (rekursiv, Listen werden ersetzt)."""
    out = dict(base)
    for key, val in (override or {}).items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], val)
        else:
            out[key] = val
    return out


def load_brand_lock():
    """Lädt data/brand_lock.yaml. Liefert None bei Fehler (Wächter-Check)."""
    if not os.path.exists(LOCK_FILE):
        return None
    try:
        with open(LOCK_FILE, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or []
    except Exception:
        return None


def validate(brain):
    """Struktur-Validierung. Liefert Liste von Fehlermeldungen (leer = ok)."""
    errs = []
    if not brain.get("brand", {}).get("name"):
        errs.append("brand.name fehlt")
    if not brain.get("voice", {}).get("anrede"):
        errs.append("voice.anrede fehlt (du|sie)")
    anrede = brain.get("voice", {}).get("anrede", "du")
    if anrede not in ("du", "sie"):
        errs.append(f"voice.anrede muss 'du' oder 'sie' sein, ist '{anrede}'")
    if not brain.get("default_cta"):
        errs.append("default_cta fehlt")
    return errs


def lock_drift(brain):
    """Vergleicht die kanonischen Texte mit brand_lock.yaml.

    Liefert (drift_liste, lock_ok). lock_ok=False = brand_lock.yaml nicht
    lesbar → Werkzeugfehler (fail-closed), nicht "grün".
    """
    lock = load_brand_lock()
    if lock is None:
        return [], False
    if not isinstance(lock, list):
        return [], False
    lock_map = {}
    for item in lock:
        if isinstance(item, dict) and "key" in item and "expected" in item:
            lock_map[item["key"]] = item["expected"]
    drift = []
    for lock_key, brain_key in LOCK_KEY_MAP.items():
        expected = lock_map.get(lock_key)
        if expected is None:
            continue  # Key nicht im Lock → nicht bewertbar, kein Drift
        actual = _get_path(brain, brain_key)
        if actual != expected:
            drift.append({"lock_key": lock_key, "brain_key": brain_key,
                          "expected": expected, "actual": actual})
    return drift, True


def _get_path(brain, dotted):
    node = brain
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _set_path(brain, dotted, value):
    parts = dotted.split(".")
    node = brain
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def fix_drift(brain, drift):
    """Heilt Drift: zieht die kanonischen Werte aus brand_lock.yaml."""
    lock = load_brand_lock()
    if not lock:
        return brain
    for item in drift:
        brain_key = item["brain_key"]
        # canonical-Wert aus dem Lock holen (expected == Lock-Wert)
        _set_path(brain, brain_key, item["expected"])
    return brain


def compact_context(brain):
    """Kompakter Marken-Hirn-Block für Prompt-Injektion (agc_context.py)."""
    b = brain.get("brand", {})
    v = brain.get("voice", {})
    a = brain.get("avatar", {})
    aud = brain.get("audience", {})
    lines = [
        f"MARKEN-HIRN: Du bist {a.get('name', b.get('author', 'der Autor'))} "
        f"({a.get('rolle', 'Autor')}, {a.get('erfahrung', '')}) und schreibst für "
        f"{b.get('name', '')} ({b.get('domain', '')}).",
        f"NISCHE: {b.get('niche', '')}",
        f"ZIELGRUPPE: {aud.get('primary', '')}",
        f"TON: {v.get('tone', '')} · Anrede: {v.get('anrede', 'du')}-Form · "
        f"Niveau: {v.get('redaktionsstandard', '')}.",
    ]
    verboten = v.get("forbidden_phrases", [])
    if verboten:
        lines.append("VERBOTENE Floskeln: " + " · ".join(verboten[:8]))
    regeln = brain.get("hard_rules", [])
    if regeln:
        lines.append("HARTE REGELN: " + " | ".join(regeln[:4]))
    return "\n".join(lines)


def save_brain(brain, path=None):
    path = path or BRAIN_FILE
    # _defaults_used-Flag nicht persistieren
    clean = {k: v for k, v in brain.items() if not k.startswith("_")}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(clean, fh, allow_unicode=True, sort_keys=False,
                       default_flow_style=False)


def main():
    if "--context" in sys.argv:
        brain = load_brand_brain()
        print(compact_context(brain))
        return 0

    brain = load_brand_brain()
    errs = validate(brain)
    drift, lock_ok = lock_drift(brain)

    if "--selftest" in sys.argv:
        if not lock_ok:
            print("🛑 BRAND-BRAIN-SELFTEST FEHLGESCHLAGEN: "
                  "data/brand_lock.yaml nicht lesbar (fail-closed).")
            return 2
        if errs:
            print("🛑 BRAND-BRAIN-SELFTEST FEHLGESCHLAGEN:")
            for e in errs:
                print(f"   - {e}")
            return 2
        if drift:
            print("🛑 BRAND-BRAIN-SELFTEST: Drift zu brand_lock.yaml:")
            for d in drift:
                print(f"   - {d['brain_key']}: erwartet {d['expected']!r}, "
                      f"ist {d['actual']!r}")
            return 2
        print("✅ BRAND-BRAIN-SELFTEST bestanden (Struktur + brand_lock-Drift).")
        return 0

    if "--fix" in sys.argv or "--set-current" in sys.argv:
        if drift:
            brain = fix_drift(brain, drift)
            save_brain(brain)
            print(f"✅ {len(drift)} Drift(en) aus brand_lock.yaml geheilt.")
        else:
            print("Kein Drift – Brand Brain konform.")
        return 0

    # Normaler Report
    if brain.get("_defaults_used"):
        print("⚠ BRAND BRAIN: data/brand_brain.yaml fehlt/beschädigt – "
              "Default-Werte aktiv.")
    if errs:
        print("❌ Validierungsfehler:")
        for e in errs:
            print(f"   - {e}")
    if drift:
        print("⚠ Drift zu brand_lock.yaml:")
        for d in drift:
            print(f"   - {d['brain_key']}: erwartet {d['expected']!r}, "
                  f"ist {d['actual']!r}")
    if not errs and not drift:
        print("✅ Brand Brain valide & konform (brand_lock.yaml).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
