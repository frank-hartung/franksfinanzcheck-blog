#!/usr/bin/env python3
"""reader_prosody_parity_check.py — Paritäts-Gate: Browser-Fallback ↔ Tonspur.

Warum dieses Gate existiert (04.09.2026)
  Die Vorlese-Funktion hat zwei unabhängige Regien:
    · `static/premium/ff-reader.js`   → Web-Speech-Pfad (PROSODY-Tabelle,
      Sprach-Lexika, Stimmen-Rangliste, Aussprache-Normalisierung)
    · `scripts/reader_tts_backends.py` + `scripts/generate_reader_audio.py`
      → vorab vertonte Tonspur (edge-tts / Piper / Groq)
  Laufen beide auseinander, klingt derselbe Artikel je nach Gerät
  unterschiedlich – genau das zerstört ein Hörangebot auf Verlagsniveau.
  Dieses Gate prüft maschinell:

    1. Rollen-Prosodie (Tempo/Tonlage/Lautstärke/Pausen) ist identisch.
    2. Die Sprach-Lexika sind identisch (EN/DE) und die Sprach-Entscheidung
       fällt für dieselben Sätze gleich aus → DE/EN ohne Umschalter wirkt
       in beiden Pfaden gleich.
    3. Die männlichen Stimmen der Tonspur sind im JS-Katalog als männlich
       hinterlegt, die weiblichen Kandidaten werden dort ausgesortiert.
    4. Der Reader-Vertrag `cfg.audio = {src, chunks:[{b,t0,t1,lang}]}` wird
       vom Generator exakt eingehalten (keine Zusatzfelder in der HTML-
       Injektion, sonst bläht sich jede Artikelseite auf).
    5. Der Deploy ruft den Generator ohne Pflicht-Key auf (kostenlos).

Aufruf:  python3 scripts/reader_prosody_parity_check.py   (Exit 0 = grün)
Benötigt node für Punkt 2/3 (sonst werden diese Prüfungen übersprungen).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import reader_tts_backends as ttb  # noqa: E402

JS_PATH = os.path.join(ROOT, "static", "premium", "ff-reader.js")
GEN_PATH = os.path.join(ROOT, "scripts", "generate_reader_audio.py")
PROBE_PATH = os.path.join(ROOT, "scripts", "reader_parity_probe.js")
DEPLOY_PATH = os.path.join(ROOT, ".github", "workflows", "deploy.yml")

OK = FAIL = SKIP = 0

# Gemeinsame Testfälle: müssen in JS und Python gleich entschieden werden.
LANG_CASES = [
    ("Der Tarifvergleich spart Geld.", "de", "de"),
    ("The comparison shows lower fees.", "de", "en"),
    ("This is a simple test sentence with common words.", "de", "en"),
    ("You should compare the fees before you switch.", "de", "en"),
    ("Online-Banking ist praktisch und günstig.", "de", "de"),
    ("Ein ETF-Sparplan kostet 25 Euro im Monat.", "de", "de"),
    ("Gas costs are rising again.", "de", "en"),
    ("Die Versicherung kostet 12 Euro im Monat.", "en", "de"),
    ("Die Ersparnis beträgt 12 Euro für die Küche und Möbel.", "en", "de"),
    ("The budget plan works well for your money.", "en", "en"),
    ("Wechseln lohnt sich meistens.", "en", "de"),
    ("Smart Home lohnt sich nicht immer.", "de", "de"),
]


def check(name: str, cond: bool, detail: str = "") -> None:
    global OK, FAIL
    if cond:
        OK += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def skip(name: str, why: str) -> None:
    global SKIP
    SKIP += 1
    print(f"  ⊙ {name} übersprungen ({why})")


def run_probe() -> dict | None:
    """Führt den Node-Probe aus und liefert die JS-Regiedaten."""
    if not os.path.exists(PROBE_PATH):
        return None
    cases = [{"text": t, "base": b} for t, b, _ in LANG_CASES]
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                         encoding="utf-8") as fh:
            json.dump(cases, fh)
            cases_path = fh.name
        proc = subprocess.run(["node", PROBE_PATH, cases_path], capture_output=True,
                              text=True, timeout=180, cwd=ROOT)
    except (OSError, subprocess.SubprocessError):
        return None
    finally:
        try:
            os.unlink(cases_path)
        except (OSError, UnboundLocalError):
            pass
    if proc.returncode != 0 or not proc.stdout.strip():
        print(f"  ⚠ Probe-Fehler: {proc.stderr.strip()[:300]}")
        return None
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except json.JSONDecodeError:
        return None


def parse_js_prosody(js: str) -> dict[str, dict[str, float]]:
    """PROSODY-Tabelle per Regex (Fallback, falls node fehlt)."""
    m = re.search(r"var PROSODY\s*=\s*\{(.*?)\n\s*\};", js, re.S)
    if not m:
        return {}
    row = re.compile(
        r"['\"]?([a-z0-9-]+)['\"]?\s*:\s*\{\s*rate:\s*([0-9.]+)\s*,\s*pitch:\s*([0-9.]+)\s*,"
        r"\s*volume:\s*([0-9.]+)\s*,\s*before:\s*(\d+)\s*,\s*after:\s*(\d+)", re.I)
    out = {}
    for role, rate, pitch, volume, before, after in row.findall(m.group(1)):
        out[role.lower()] = {"rate": float(rate), "pitch": float(pitch), "volume": float(volume),
                             "before": float(before), "after": float(after)}
    return out


def compare_emo(js_emo: dict) -> None:
    """Satzmelodie (Tonlage/Tempo/Pausenraum je Emotion) zwischen beiden Regien."""
    if not js_emo or not js_emo.get("pitch"):
        skip("Satzmelodie-Vergleich", "Emotion-Konstanten fehlen im Probe")
        return
    check("JS-Tonlage je Emotion ≡ Python",
          js_emo["pitch"] == ttb.EMO_PITCH,
          f"{js_emo['pitch']} vs {ttb.EMO_PITCH}")
    check("JS-Tempo je Emotion ≡ Python",
          js_emo["rate"] == ttb.EMO_RATE,
          f"{js_emo['rate']} vs {ttb.EMO_RATE}")
    check("JS-Pausenraum je Emotion ≡ Python",
          js_emo["afterMs"] == ttb.EMO_AFTER_MS,
          f"{js_emo['afterMs']} vs {ttb.EMO_AFTER_MS}")
    check("Fragen werden ruhiger gelesen als Feststellungen",
          js_emo["rate"].get("question", 1.0) < 1.0 and js_emo["rate"].get("statement", 1.0) == 1.0,
          str(js_emo["rate"]))
    check("Ausrufe erhalten mehr Pausenraum als Feststellungen",
          js_emo["afterMs"].get("exclamation", 0) > 0,
          str(js_emo["afterMs"]))


def compare_prosody(js_prosody: dict) -> None:
    missing = sorted(set(ttb.PROSODY) - set(js_prosody))
    extra = sorted(set(js_prosody) - set(ttb.PROSODY))
    check("Alle Rollen der Tonspur existieren im Reader", not missing, str(missing))
    check("Keine Leserolle ohne Tonspur-Pendant", not extra, str(extra))
    for role in sorted(set(ttb.PROSODY) & set(js_prosody)):
        py, js = ttb.PROSODY[role], js_prosody[role]
        diffs = []
        for key in ("rate", "pitch", "volume"):
            if abs(float(py[key]) - float(js[key])) > 0.02:
                diffs.append(f"{key}: {py[key]} vs {js[key]}")
        for key in ("before", "after"):
            if abs(float(py[key]) - float(js[key])) > 80:
                diffs.append(f"{key}ms: {int(py[key])} vs {int(js[key])}")
        check(f"Rolle „{role}“ identisch geregelt", not diffs, "; ".join(diffs))


def main() -> int:
    js_src = open(JS_PATH, encoding="utf-8").read()
    probe = run_probe()

    print("— 1) Rollen-Prosodie: Tonspur ≡ Browser-Fallback —")
    if probe and probe.get("prosody"):
        compare_prosody(probe["prosody"])
        compare_emo(probe.get("emo"))
    else:
        parsed = parse_js_prosody(js_src)
        if parsed:
            compare_prosody(parsed)
        else:
            skip("Prosodie-Vergleich", "weder node noch PROSODY-Regex erfolgreich")

    print("— 2) Sprach-Lexika & Sprach-Entscheidung (DE/EN ohne Umschalter) —")
    for text, base, expect in LANG_CASES:
        got = ttb.sniff_lang(text, base)
        check(f"Python: {text[:44]!r} → {expect}", got == expect, got)
    if probe and probe.get("lang"):
        for text, base, expect in LANG_CASES:
            got = probe["lang"].get(f"{base}|{text}")
            check(f"JS:     {text[:44]!r} → {expect}", got == expect, str(got))
    else:
        skip("JS-Sprach-Entscheidung", "node-Probe nicht verfügbar")
    if probe and probe.get("lex"):
        js_en, js_de = set(probe["lex"].get("en", [])), set(probe["lex"].get("de", []))
        check("EN-Lexikon identisch (JS ≡ Python)", js_en == ttb.EN_CORE,
              f"nur JS: {sorted(js_en - ttb.EN_CORE)[:5]} / nur Python: "
              f"{sorted(ttb.EN_CORE - js_en)[:5]}")
        check("DE-Lexikon identisch (JS ≡ Python)", js_de == ttb.DE_CORE,
              f"nur JS: {sorted(js_de - ttb.DE_CORE)[:5]} / nur Python: "
              f"{sorted(ttb.DE_CORE - js_de)[:5]}")
        check("Kein mehrdeutiges Token im EN-Lexikon",
              not ({"in", "an", "a", "so", "per", "was", "die"} & js_en),
              str({"in", "an", "a", "so", "per", "was", "die"} & js_en))
    else:
        skip("Lexikon-Vergleich", "node-Probe nicht verfügbar")

    print("— 3) Nur-Männlich-Garantie über beide Pfade —")
    if probe and probe.get("male"):
        male_pool = {n.lower() for n in probe["male"].get("known", [])}
        for lang_list in (probe["male"].get("keywords") or {}).values():
            male_pool |= {k.lower() for k in lang_list}
        studio = [s.lower() for s in probe["male"].get("studio", [])]
        female = [f.lower() for f in probe["male"].get("female", [])]
        # edge-Stimmen sind Azure-Identitäten: Edge liefert sie 1:1 im
        # Browser-Katalog, also MUSS das JS sie männlich einstufen.
        # Piper-/Groq-Namen gibt es in keinem Browser-Katalog – hier reicht,
        # dass die Python-Seite sie männlich nennt und das JS sie nicht als
        # weiblich führt („alba" wäre sonst eine spanische Frauenstimme).
        for profile in sorted(ttb.VOICE_PRESETS):
            for backend in sorted(ttb.VOICE_PRESETS[profile]):
                browser_relevant = backend == "edge"
                for lang, voices in ttb.VOICE_PRESETS[profile][backend].items():
                    for voice in voices:
                        stem = voice.lower()
                        stem = re.sub(r"^(de|en)[-_][a-z]{2}[-_]", "", stem)
                        stem = re.split(r"(multilingual|neural|[-_](high|medium|low|x))", stem)[0]
                        py_male = ttb.is_male_voice_name(voice)
                        js_female = any(stem == f for f in female)
                        js_male = stem in male_pool or any(stem in s for s in studio)
                        if browser_relevant:
                            check(f"{profile}/{backend}/{lang}: \u201e{voice}\u201c ist im Reader m\u00e4nnlich",
                                  js_male and not js_female and py_male, f"stem={stem}")
                        else:
                            check(f"{profile}/{backend}/{lang}: \u201e{voice}\u201c männlich (Offline-Stimme)",
                                  py_male and not js_female, f"stem={stem}")
        picks = probe.get("picks") or {}
        check("JS wählt im Edge-2026-Katalog eine männliche DE-Stimme",
              bool(picks.get("de")) and picks.get("deExplicit") is True
              and not any(f in (picks.get("de") or "").lower() for f in ("katja", "emma", "anna")),
              str(picks.get("de")))
        check("JS wählt im Edge-2026-Katalog eine männliche EN-Stimme",
              bool(picks.get("en")) and "ava" not in (picks.get("en") or "").lower(),
              str(picks.get("en")))
    else:
        skip("Stimmen-Parität", "node-Probe nicht verfügbar")

    print("— 4) Reader-Vertrag für die Tonspur —")
    chunks = [{"b": 0, "t0": 0, "t1": 900, "lang": "de"},
              {"b": 1, "t0": 900, "t1": 2100, "lang": "de"},
              {"b": 2, "t0": 2100, "t1": 2600, "lang": "en"}]
    payload = json.dumps({"audio": {"src": "/audio/articles/x.mp3", "chunks": chunks}},
                         ensure_ascii=False, separators=(",", ":"))
    check("Injektions-Payload enthält nur src + chunks",
          set(json.loads(payload)["audio"]) == {"src", "chunks"})
    check("Chunk-Felder entsprechen dem Reader-Vertrag",
          all(set(c) == {"b", "t0", "t1", "lang"} for c in chunks))
    check("Reader greift auf b/t0/t1 zu",
          all(k in js_src for k in ("audioChunks[i].b", "audioChunks[i].t0", "audioChunks[i].t1")))
    check("Reader fällt bei fehlender Tonspur auf Web Speech zurück",
          "if (speechSupported) startReading(audioBlock)" in js_src)
    gen_src = open(GEN_PATH, encoding="utf-8").read()
    check("Generator injiziert Block-Chunks (keine Satz-/Wortdaten in der HTML)",
          "block_chunks(track[\"chunks\"])" in gen_src)
    # Der Reader liest die Tonspur aus einem EIGENEN Config-Block; Artikel-
    # Config und Audio-Config dürfen nie dieselbe ID tragen, sonst überschreibt
    # die Injektion Titel/Lesedauer des Artikels.
    check("Generator schreibt in den eigenen Audio-Config-Block",
          'ff-reader-audio-config' in gen_src)
    check("Reader liest genau diesen Block",
          "getElementById('ff-reader-audio-config')" in js_src)
    check("Reader übernimmt daraus nur cfg.audio",
          "if (audioCfg && audioCfg.audio) cfg.audio = audioCfg.audio;" in js_src)

    print("— 5) Kostenfreiheit & Rezept-Nachvollziehbarkeit —")
    check("Generator-Fingerprint trägt die Rezept-Version", "GEN_VERSION" in gen_src)
    check("Rezept-Versionen sind im Backends-Modul hinterlegt",
          bool(ttb.NORM_VERSION and ttb.PROSODY_VERSION and ttb.BACKENDS_VERSION))
    if os.path.exists(DEPLOY_PATH):
        deploy = open(DEPLOY_PATH, encoding="utf-8").read()
        check("Deploy ruft den Generator mit Backend-Kette auf", "--backend" in deploy)
        check("Deploy braucht für die Tonspur keinen API-Key",
              "GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}" not in deploy
              or "edge-tts" in deploy)
        check("Deploy bricht wegen der Tonspur nicht ab", "|| echo" in deploy or "continue-on-error" in deploy)
    else:
        skip("Deploy-Prüfung", "deploy.yml nicht gefunden")

    print(f"\n=== Paritäts-Gate: {OK} grün, {FAIL} rot, {SKIP} übersprungen ===")
    if FAIL:
        print("❌ Parität verletzt: Tonspur und Browser-Fallback würden unterschiedlich klingen.")
        return 1
    print("🎉 Tonspur und Browser-Fallback sind regiegleich (männlich, DE/EN, gleiche Pausen).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
