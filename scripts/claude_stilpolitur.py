#!/usr/bin/env python3
# ============================================================
#  CLAUDE-STILPOLITUR – Premium-Stil-Layer über der Offline-Optimierung
#  ------------------------------------------------------------
#  AUFTRAG (Frank, 25.09.2026), wörtlich:
#    „Nutze für jeden bestehenden und zukünftigen Blogartikel nach
#    der Offline-Optimierung zusätzlich automatisch täglich Claude
#    mit einem personalisierten Prompt für meinen eigenen
#    Schreibstil auf Premium-Level einer Profi-Agentur."
#    Nachtrag selben Tages: „Claude sollte nur OHNE API genutzt
#    werden. Dafür sollte das aktuell beste kostenlose
#    Claude-Modell gewählt werden."
#
#  EINORDNUNG (Regelwerk-Prinzip „jede Regel genau einmal“):
#    1. Offline-Optimierung (läuft IMMER zuerst, ohne API, 25.09.2026):
#       grammar_check.py (LT1–LT4) + sprachglatt.py (DW1–DW9)
#    2. DIESE Datei (kostenlose Claude-Lane): Claude via Puter.js
#       (User-Pays, OHNE Anthropic-API, OHNE Kosten) mit
#       PERSONALISIERTEM Prompt aus data/schreibstil.yaml (Franks
#       eigener Schreibstil) + data/brand_brain.yaml (Marken-Stimme)
#       – Stil-Politur auf Premium-Level einer Profi-Agentur.
#
#  MODELL: das aktuell beste KOSTENLOSE Claude-Modell (Auftrag):
#    data/ki_redaktion.yaml → stilpolitur.modell, Stand 25.09.2026:
#    „claude-fable-5-1“ (Fable 5.1 – Spitze der Modellkarte).
#    Fallbacks: claude-opus-5-5 → claude-sonnet-5. Override:
#    STILPOLITUR_MODEL. Der Selbsttest (ST3) prüft die Frei-Liste –
#    ein bezahlter Modell-/API-Pfad wird damit abgewiesen.
#
#  ZUGANG (Puter.js, „Free, Unlimited Claude API“, User-Pays):
#    - KEINE Anthropic-Abrechnung, kein Modell-Key – nur ein
#      PUTER_AUTH_TOKEN (kostenloser Puter-Account mit monatlichem
#      Gratis-Kontingent; Brücke: scripts/puter_chat.mjs).
#    - Die Gratis-Regel der Artikel-GENERIERUNG (ki_redaktion.yaml →
#      anbieter_kette_*) bleibt unangetastet – die Lane ist nun
#      ebenfalls kostenfrei.
#  Budget: max_artikel_pro_tag (Rotation) + auffrischung_tage.
#
#  SICHERHEIT (Repo-Vertrag, wie sprachkern/redaktions_standard):
#    - Schutzzonen (Markdown-Links inkl. ANKERTEXT, Shortcodes, Code,
#      URLs, HTML) bleiben byte-identisch (Multiset-Vergleich)
#    - Überschriften-Zeilen bleiben in Reihe UND Wortlaut identisch
#      (Anker-Slugs, SEO, Cover-Verträge)
#    - Zahlen/Prozente/Euro-Beträge bleiben byte-identisch
#      (Fakten + Rechenbeispiele – Anti-Halluzination)
#    - Tabellen-Skelett & Trennlinien stabil, Wortzahl ≥ 90 %
#    - Frontmatter wird nie angefasst (title = Cover-Marken-Lock)
#    - Zweite Verifikation via sprachkern.write_verified vor Schreiben
#    - Selbsttest (11 eingefrorene Fälle) vor JEDEM Schreibvorgang,
#      Abweichung = Exit 2, kein Schreiben (Sabotage-Schutz)
#
#  NUTZUNG:
#    python3 scripts/claude_stilpolitur.py                 # Report (alle)
#    python3 scripts/claude_stilpolitur.py --fix           # polieren (API)
#    python3 scripts/claude_stilpolitur.py --fix --new-only
#    python3 scripts/claude_stilpolitur.py --fix --force --file X.md
#    python3 scripts/claude_stilpolitur.py --fix --dry-run # Trockenlauf
#    python3 scripts/claude_stilpolitur.py --selftest      # Sabotage-Schutz
#
#  EXIT: 0 sauber/gelaufen · 1 offene Kandidaten (nur --strict)
#        2 Selbsttest rot · 3 --fix ohne PUTER_AUTH_TOKEN
#  REPORT: CLAUDE-STILPOLITUR-REPORT.md + .claude_stilpolitur_report.json
#  HISTORIE: data/claude_stil_history.jsonl (versioniert)
#  STATE: data/claude_stil_state.json (versioniert, Fingerprint-Dedupe)
# ============================================================
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import sprachkern as sk  # noqa: E402  (Schutzzonen, load_articles, write_verified)
import post_utils  # noqa: E402

try:
    import yaml  # noqa: E402
except Exception:  # noqa: BLE001
    yaml = None

REPORT_FILE = os.path.join(BLOG_DIR, "CLAUDE-STILPOLITUR-REPORT.md")
JSON_FILE = os.path.join(BLOG_DIR, ".claude_stilpolitur_report.json")
HISTORY_FILE = os.path.join(BLOG_DIR, "data", "claude_stil_history.jsonl")
STATE_FILE = os.path.join(BLOG_DIR, "data", "claude_stil_state.json")
STIL_FILE = os.path.join(BLOG_DIR, "data", "schreibstil.yaml")
BRAND_FILE = os.path.join(BLOG_DIR, "data", "brand_brain.yaml")
CONFIG_FILE = os.path.join(BLOG_DIR, "data", "ki_redaktion.yaml")

ENGINE = "claude-stilpolitur (Claude, kostenlos ohne API, personalisiert)"
BRUECKE = os.path.join(BLOG_DIR, "scripts", "puter_chat.mjs")

# Modell-SSOT: bestes KOSTENLOSES Claude-Modell (Auftrag 25.09.2026).
# Frei-Liste = Puter-Katalog „Free, Unlimited Claude API“ – alles ohne
# Anthropic-Abrechnung erreichbar (User-Pays-Gratis-Kontingent).
FREIE_CLAUDE_MODELLE = (
    "claude-fable-5-1", "claude-fable-5",
    "claude-opus-5-5", "claude-opus-5", "claude-opus-5-fast",
    "claude-opus-4.8-fast", "claude-opus-4-8", "claude-opus-4-7",
    "claude-opus-4-6", "claude-opus-4-5",
    "claude-sonnet-5", "claude-sonnet-4-6", "claude-sonnet-4-5", "claude-sonnet-4",
    "claude-haiku-4-5",
)

DEFAULT_CONFIG = {
    "modell": "claude-fable-5-1",           # bestes kostenloses Modell
    "modell_fallback": ["claude-opus-5-5", "claude-sonnet-5"],
    "temperatur": 0.5,
    "max_tokens": 8192,
    "timeout": 300,
    "max_artikel_pro_tag": 12,
    "auffrischung_tage": 7,
}

NUM_RX = re.compile(r"\d[\d.,]*")
PLACEHOLDER_RX = re.compile(r"\x00Z\d+\x00")
HR_RX = re.compile(r"(?m)^\s*---\s*$")
HEADING_RX = re.compile(r"(?m)^#{1,6}\s.*$")
FM_START_RX = re.compile(r"^\s*---\s*\n")


# ----------------------------------------------------------- Konfiguration
def load_config() -> dict:
    """stilpolitur-Sektion aus data/ki_redaktion.yaml (Defaults nie crashen)."""
    cfg = dict(DEFAULT_CONFIG)
    cfg["modell"] = (os.environ.get("STILPOLITUR_MODEL") or cfg["modell"]).strip()
    if yaml is not None and os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            section = (data.get("stilpolitur") or {}) if isinstance(data, dict) else {}
            for k, v in section.items():
                if k in DEFAULT_CONFIG and v is not None:
                    cfg[k] = v
        except Exception:  # noqa: BLE001
            pass
    if os.environ.get("STILPOLITUR_MODEL"):
        cfg["modell"] = os.environ["STILPOLITUR_MODEL"].strip()
    return cfg


def load_stil() -> tuple[dict, dict]:
    """Lädt Franks Stilprofil + Marken-Brain. Beide Pflicht (fail-closed)."""
    stil, brand = {}, {}
    if yaml is None:
        return stil, brand
    for path, target in ((STIL_FILE, "stil"), (BRAND_FILE, "brand")):
        if not os.path.exists(path):
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception:  # noqa: BLE001
            data = {}
        if target == "stil":
            stil = data
        else:
            brand = data
    return stil, brand


# ----------------------------------------------------------- Prompt-Bau
def _fmt_block(v) -> str:
    """Formatiert YAML-Werte (str/list/dict) als Prompt-Block."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return "\n".join(f"- {str(x).strip()}" for x in v)
    if isinstance(v, dict):
        return "\n".join(f"- {str(k).strip()}: {str(val).strip()}"
                         for k, val in v.items())
    return str(v)


def render_system_prompt(stil: dict, brand: dict) -> str:
    """Der personalisierte Premium-Prompt (Franks Stimme + Marken-Brain)."""
    stimme = brand.get("voice") or {}
    avatar = brand.get("avatar") or {}
    forbidden = list(stimme.get("forbidden_phrases") or [])
    tabu = stil.get("woerter", {}).get("tabu") or []
    tabu_gesamt = list(dict.fromkeys(list(tabu) + forbidden))

    teile = [
        "Du bist Chefredakteur und Ghostwriter einer der besten deutschen",
        "Finanz-Redaktionsagenturen (Verlagsniveau: Capital, WirtschaftsWoche,",
        "DIE ZEIT). Dein Auftrag: einen bestehenden Ratgeber-Artikel so zu",
        "überarbeiten, dass er auf PREMIUM-LEVEL EINER PROFI-AGENTUR glänzt –",
        "geschrieben im PERSÖNLICHEN SCHREIBSTIL von Frank Hartung",
        "(FranksFinanzcheck), nie in generischem KI-Ton.",
        "",
        f"== FRANKS SCHREIBSTIL (verbindlich – so klingt er: „{stil.get('stilname', 'Franks Stimme')}“) ==",
        "",
        "HALTUNG:",
        _fmt_block(stil.get('haltung')),
        "",
        "SATZRHYTHMUS:",
        _fmt_block(stil.get('satzrhythmus')),
        "",
        "TONFALL:",
        _fmt_block(stil.get('tonfall')),
        "",
        "WORTWAHL (liebt):",
        _fmt_block((stil.get('woerter') or {}).get('lieblings')),
        "",
        "STIMMEN-ERSATZ (so klingt Frank statt der Floskel):",
        _fmt_block((stil.get('woerter') or {}).get('ersatz')),
        "",
        "STIL-HEBEL (genau daran arbeitest du):",
        _fmt_block(stil.get('hebel')),
        "",
        "QUALITÄTSZIELE (messbar):",
        _fmt_block(stil.get('qualitaetsziele')),
        "",
        "== MARKEN-STIMME (data/brand_brain.yaml) ==",
        f"Ton: {stimme.get('tone', 'ehrlich, praxisnah, auf Augenhöhe, zahlengetrieben, kein Verkaufsdruck')}",
        f"Leseniveau: {(brand.get('audience') or {}).get('reading_level', 'verständliche Alltagssprache, kurze Sätze, ein Gedanke pro Absatz')}",
        f"Autor: {avatar.get('name', 'Frank Hartung')} – {avatar.get('rolle', 'Autor & Finanz-Praktiker')} "
        f"({avatar.get('erfahrung', 'über zehn Jahre Erfahrung im Finanzbereich')})",
        "",
        "== AUFGABE (Stil-Politur, NIE Faktenarbeit) ==",
        "Überarbeite den Artikel als Ganzes auf Premium-Level: Rhythmus schärfen,",
        "Übergänge tragen lassen, Alltagsbilder finden, Füllwörter raus, Franks",
        "Stimme hörbar machen. Inhalt, Aussagen, Struktur-Module („Das Wichtigste",
        "in Kürze“, Rechenbeispiele, FAQ) und Aussage bleiben EXAKT dieselben.",
        "Die Offline-Optimierung (Grammatik/Glättung) ist bereits gelaufen –",
        "du feilst eine Ebene darüber: Sprachbild, Klang, Prägnanz, Haltung.",
        "",
        "== HARTE REGELN (Verstoß = unbrauchbar, wird verworfen) ==",
        "1. FAKTEN HEILIG: Alle Zahlen, Prozente, Euro-Beträge, Zeiträume bleiben",
        "   BYTE-IDENTISCH. Erfinde NIEMALS Studien, Institute, Paragraphen,",
        "   Preise, Daten oder Quellen. Keine Phantom-Quellen („laut einer Studie“).",
        "2. SCHUTZZONEN BYTE-IDENTISCH: Markdown-Links MIT Ankertext, Bilder,",
        "   Hugo-Shortcodes, Inline-Code, Code-Blöcke, URLs, HTML-Tags und",
        "   -Kommentare unverändert wörtlich übernehmen.",
        "3. ÜBERSCHRIFTEN UNANTASTBAR: Jede Zeile mit # (##, ### …) bleibt in",
        "   Wortlaut UND Reihenfolge exakt gleich – nur der Fließtext darunter",
        "   wird poliert.",
        "4. TABELLEN: Zell-Texte dürfen glänzen, das Skelett (Zeilen/Spalten/",
        "   Trennzeile) bleibt. Trennlinien (---) nicht umhängen.",
        "5. DEUTSCH, Du-Ansprache (außer der Artikel nutzt die Sie-Form), warm",
        "   und konkret. Keine Emojis im Fließtext. Keine Übertreibungen, keine",
        "   Heilsversprechen, kein Clickbait. Keine GROSSBUCHSTABEN als Betonung.",
        "6. Keine Anbieter-Empfehlungen außer CHECK24 als Vergleichsportal.",
        "   Marken exakt: CHECK24, FRITZ!Box, congstar, otelo, idealo, Verivox,",
        "   O2, PAYBACK, Pinterest, Excel, Vodafone. Fachkürzel groß: DSL, WLAN,",
        "   kWh, AGB, FAQ.",
        "7. Tabu-Formulierungen (NIEMALS verwenden): "
        + "; ".join(f"„{t}“" for t in tabu_gesamt),
        "8. Umfang halten: mindestens 90 % der Wortzahl (Ziel ≥ 95 %). Straffen",
        "   ja, ausdünnen bis zum Skelett nein.",
        "9. Ausgabe: NUR den fertigen Markdown-Fließtext OHNE Frontmatter, OHNE",
        "   Titel-Zeile (# …), OHNE Kommentare, OHNE Code-Zaun um den Text,",
        "   OHNE jede Erklärung.",
    ]
    return "\n".join(p for p in teile if p is not None)


def build_user_prompt(a: dict) -> str:
    """Artikel-Auftrag für das Modell (Body zwischen festen Markern)."""
    anrede = "Du-Form (durchgehend)"
    m = re.search(r"(?m)^anrede:\s*[\"']?(.+?)[\"']?\s*$", a.get("fm", ""))
    if m and m.group(1).strip().lower().strip('"\'') in ("sie", "sie-form", "höflich"):
        anrede = "Sie-Form (durchgehend, höflich)"
    return (
        f"ARTIKEL-TITEL: {a.get('title', '')}\n"
        f"ANREDE: {anrede}\n"
        f"SEO-BESCHREIBUNG (Kontext, nicht Teil des Textes): "
        f"{a.get('description', '')}\n\n"
        "Poliere den folgenden Artikel in Franks persönlichem Schreibstil auf\n"
        "Premium-Level einer Profi-Agentur. Gib AUSSCHLIESSLICH den fertigen\n"
        "Markdown-Fließtext zurück.\n\n"
        "<<<ARTIKEL-START\n"
        f"{a['body']}\n"
        "ARTIKEL-ENDE>>>"
    )


# ----------------------------------------------------------- Verifikation
def _prose(text: str) -> str:
    masked, _ = sk.protect_zones(text)
    return PLACEHOLDER_RX.sub("", masked)


def _table_rows(text: str) -> list:
    return [ln for ln in text.splitlines() if ln.strip().startswith("|")]


def verify(orig_body: str, new_body: str) -> tuple[bool, str]:
    """Sicherheits-Verifikation VOR dem Schreiben. → (ok, meldung)."""
    _, o_tok = sk.protect_zones(orig_body)
    _, n_tok = sk.protect_zones(new_body)
    if sorted(o_tok) != sorted(n_tok):
        return False, "Schutzzonen verändert (Link/Ankertext/Shortcode/Code/URL/HTML)"
    if HEADING_RX.findall(orig_body) != HEADING_RX.findall(new_body):
        return False, "Überschriften verändert (Anker-/SEO-Vertrag)"
    if sorted(NUM_RX.findall(_prose(orig_body))) != \
            sorted(NUM_RX.findall(_prose(new_body))):
        return False, "Zahlen verändert (Fakten-/Rechenbeispiel-Vertrag)"
    if len(_table_rows(orig_body)) != len(_table_rows(new_body)):
        return False, "Tabellen-Skelett verändert"
    if len(HR_RX.findall(orig_body)) != len(HR_RX.findall(new_body)):
        return False, "Trennlinien-Anzahl verändert"
    if sk.words(new_body) < 0.90 * sk.words(orig_body):
        return False, "Wortzahl unter 90 % des Originals"
    return True, "ok"


def fingerprint(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


# ----------------------------------------------------------- State/Rotation
def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and "artikel" in data:
                return data
        except Exception:  # noqa: BLE001
            pass
    return {"version": 1, "artikel": {}}


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.replace(tmp, STATE_FILE)


def auswahl(slug: str, body: str, state: dict, auffrischung_tage: int,
            now: datetime.datetime):
    """Braucht dieser Artikel Claude? → (fp, prio, grund) · prio None = nein."""
    fp = fingerprint(body)
    e = (state.get("artikel") or {}).get(slug)
    if not e:
        return fp, 0, "neu"
    if e.get("status") != "ok":
        return fp, 0, f"offen ({e.get('status', '?')})"
    if e.get("fp") != fp:
        return fp, 1, "geändert"
    if auffrischung_tage:
        age = auffrischung_tage
        try:
            last = datetime.datetime.fromisoformat(str(e.get("last", "")).replace("Z", "+00:00"))
            age = max(0, (now - last).days)
        except Exception:  # noqa: BLE001
            pass
        if age >= auffrischung_tage:
            return fp, 2, f"auffrischen ({age}d)"
    return fp, None, None


# ----------------------------------------------------------- KI-Politur
def puter_chat(system: str, user: str, modell: str, cfg: dict) -> str | None:
    """Ein Aufruf über die Puter-Brücke (kostenlos, ohne API). None = Fehler."""
    payload = json.dumps({
        "system": system, "user": user, "model": modell,
        "temperature": float(cfg["temperatur"]),
        "max_tokens": int(cfg["max_tokens"]),
    })
    try:
        r = subprocess.run(["node", BRUECKE], input=payload,
                           capture_output=True, text=True,
                           timeout=int(cfg["timeout"]))
    except FileNotFoundError:
        print("  🛑 node nicht gefunden – Node.js 24+ nötig (Brücke "
              "scripts/puter_chat.mjs).", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print(f"  ⚠ puter_chat[{modell}]: Zeitüberschreitung", file=sys.stderr)
        return None
    if r.returncode != 0:
        err = (r.stderr or "").strip().splitlines()
        print(f"  ⚠ puter_chat[{modell}]: {err[-1][:200] if err else 'Exit ' + str(r.returncode)}",
              file=sys.stderr)
        return None
    return (r.stdout or "").strip() or None


def call_claude(system: str, user: str, cfg: dict) -> str | None:
    """Claude KOSTENLOS über Puter.js (User-Pays, ohne Anthropic-API).

    Modell-Kette: bestes kostenloses Modell zuerst (Auftrag), dann die
    Fallbacks aus data/ki_redaktion.yaml. None = keine Antwort möglich.
    """
    kette = [cfg.get("modell")] + list(cfg.get("modell_fallback") or [])
    for modell in [m for m in kette if m]:
        text = puter_chat(system, user, str(modell), cfg)
        if text:
            return text
    return None


def clean_answer(text: str) -> tuple[str, list]:
    """Antwort entzaubern: Code-Wrapping + Prompt-Gerüst weg."""
    t = (text or "").strip()
    m = re.match(r"^```[a-zA-Z]*\n(.*)\n```\s*$", t, re.S)
    if m:
        t = m.group(1).strip()
    t, geruest = post_utils.strip_generator_scaffolding(t)
    return t, geruest


def polish_body(system: str, user: str, orig_body: str, cfg: dict,
                caller=None) -> tuple[str | None, str]:
    """Ein Claude-Durchgang inkl. Verifikation. → (neuer_body|None, meldung)."""
    caller = caller or call_claude
    answer = caller(system, user, cfg)
    if not answer:
        return None, "KI-Antwort leer (Token/Netz/Modell – siehe puter_chat-Meldung)"
    neu, geruest = clean_answer(answer)
    if geruest:
        print(f"  ⚠ Prompt-Gerüst der KI-Antwort entfernt ({len(geruest)} Zeile(n))")
    if FM_START_RX.match(neu):
        return None, "Frontmatter im Ergebnis – verworfen"
    if len(neu) < 500:
        return None, "Ergebnis zu kurz (< 500 Zeichen) – verworfen"
    ok, meldung = verify(orig_body, neu)
    if not ok:
        return None, f"Verifikation: {meldung}"
    return neu, "ok"


# ----------------------------------------------------------- Selbsttest
def _st_prompt() -> bool:
    stil, brand = load_stil()
    p = render_system_prompt(stil, brand)
    pflicht = [
        "PREMIUM-LEVEL EINER PROFI-AGENTUR",
        "PERSÖNLICHEN SCHREIBSTIL",
        "Frank Hartung",
        "BYTE-IDENTISCH",
        "ÜBERSCHRIFTEN UNANTASTBAR",
        "Frank",
    ]
    pflicht += [str(t) for t in (stil.get("woerter", {}).get("tabu") or [])][:3]
    pflicht += [str(t) for t in
                ((brand.get("voice") or {}).get("forbidden_phrases") or [])][:3]
    return all(x in p for x in pflicht)


def _st_stilprofil() -> bool:
    stil, brand = load_stil()
    pflicht = ("stilname", "haltung", "satzrhythmus", "tonfall", "woerter",
               "hebel", "qualitaetsziele")
    if any(k not in stil for k in pflicht):
        return False
    return bool((brand.get("voice") or {}).get("tone"))


def _st_modell() -> bool:
    cfg = load_config()
    kette = [str(cfg.get("modell", ""))] + [str(m) for m in
                                            (cfg.get("modell_fallback") or [])]
    kette = [m for m in kette if m]
    return bool(kette) and all(m in FREIE_CLAUDE_MODELLE for m in kette)


def _st_ohne_anthropic_api() -> bool:
    """Auftrag: Claude NUR ohne API – kein Anthropic-Key in Lane/Workflows.

    Die Verbots-Strings werden bewusst dynamisch zusammengesetzt: ein
    Klartext-Literal hier würde den Check selbst immer rot machen.
    """
    verboten = ("ANTH" + "ROPIC_API" + "_KEY", "api." + "anthropic" + ".com")
    pfade = [os.path.abspath(__file__),
             os.path.join(BLOG_DIR, ".github", "workflows", "claude-stilpolitur.yml"),
             os.path.join(BLOG_DIR, ".github", "workflows", "content-engine-v2.yml")]
    blob = []
    for p in pfade:
        if os.path.exists(p):
            with open(p, encoding="utf-8") as fh:
                blob.append(fh.read())
    text = "\n".join(blob)
    return (all(v not in text for v in verboten)
            and "PUTER_AUTH_TOKEN" in text)


def _st_bruecke() -> bool:
    """Die Puter-Brücke existiert und spricht das vereinbarte Protokoll."""
    if not os.path.exists(BRUECKE):
        return False
    with open(BRUECKE, encoding="utf-8") as fh:
        src = fh.read()
    return ("@heyputer/puter.js" in src and "PUTER_AUTH_TOKEN" in src
            and "readFileSync(0" in src and "claude-fable-5-1" in src)


def _st_schutzzonen() -> bool:
    t = "Text [CHECK24](https://a.check24.net/x?pid=1) mit `konto` und {{< check24 strom >}}."
    masked, origs = sk.protect_zones(t)
    return sk.unprotect(masked, origs) == t and len(origs) == 3


def _st_link_ziel() -> bool:
    o = "Siehe [CHECK24](https://a.check24.net/x?pid=1) und spare rund 300 € im Jahr hier."
    n = "Siehe [CHECK24](https://evil.example/x) und spare rund 300 € im Jahr hier."
    return verify(o, n)[0] is False


def _st_anker_text() -> bool:
    o = "Siehe [jetzt vergleichen](https://a.check24.net/x?pid=1) und sparen."
    n = "Siehe [jetzt ansehen](https://a.check24.net/x?pid=1) und sparen."
    return verify(o, n)[0] is False


def _st_ueberschrift() -> bool:
    o = "## Sparpotenzial prüfen\n\nHier spart man rund 300 € pro Jahr hier."
    n = "## Sparpotenzial checken\n\nHier spart man rund 300 € pro Jahr hier."
    return verify(o, n)[0] is False


def _st_zahlen() -> bool:
    o = "## Thema\n\nWer rund 300 € spart, spart viel Geld im Jahr hier."
    n = "## Thema\n\nWer rund 400 € spart, spart viel Geld im Jahr hier."
    return verify(o, n)[0] is False


def _st_shortcode() -> bool:
    o = "## Thema\n\n{{< check24 strom >}} spart bares Geld im Alltag hier."
    n = "## Thema\n\nSpares bares Geld im Alltag hier und hier."
    return verify(o, n)[0] is False


def _st_wortzahl() -> bool:
    o = "## Thema\n\n" + ("Wort Wort Wort Wort Wort. " * 40)
    n = "## Thema\n\nWort Wort."
    return verify(o, n)[0] is False


def _st_legitim() -> bool:
    o = ("## Thema\n\nDer erste Absatz folgt hier und ein zweiter Satz kommt "
         "dann mit rund 300 € pro Jahr.\n\nMehr Text folgt direkt danach hier.")
    n = ("## Thema\n\nDer erste Absatz beginnt hier, gefolgt von einem zweiten "
         "Satz mit rund 300 € pro Jahr.\n\nMehr Text folgt unmittelbar danach "
         "hier und schließt ab.")
    return verify(o, n)[0] is True


def _st_fingerprint() -> bool:
    a = fingerprint("gleicher Text")
    b = fingerprint("gleicher Text")
    c = fingerprint("anderer Text")
    return a == b and a != c


def _st_fake_caller() -> bool:
    """Bösartige/geheilte KI-Antworten werden korrekt verworfen/akzeptiert."""
    orig = ("## Thema\n\nEin kurzer Anfang mit 300 € als Zahl für den Fakten-"
            "Schutz und genug Wörter für die Längenprüfung hier und dort. "
            "Der zweite Satz liefert weitere Substanz für die Längenprüfung "
            "und klingt nachher hoffentlich besser als vorher im Raum. "
            "Der dritte Satz rundet den Absatz ab und bleibt faktentreu. "
            "Ein weiterer Absatz kommt hier dazu und sorgt für reichlich "
            "Fließtext, damit die Untergrenze von fünfhundert Zeichen auf "
            "jeden Fall überschritten wird und der Selbsttest ehrlich bleibt. "
            "Der Schlusssatz macht den Text deutlich länger als nötig.")
    bösartig = orig.replace("300 €", "999 €")
    neu = orig.replace("Ein kurzer Anfang", "Der kurze Einstieg")
    cfg = dict(DEFAULT_CONFIG)
    r1, _ = polish_body("sys", "usr", orig, cfg, caller=lambda s, u, c: bösartig)
    r2, _ = polish_body("sys", "usr", orig, cfg, caller=lambda s, u, c: neu)
    return r1 is None and r2 == neu


SELFTEST = [
    ("ST1 Prompt-Kanon (Stil + Marke + Premium + Tabu)", _st_prompt, True),
    ("ST2 Stilprofil vollständig (schreibstil.yaml + brand_brain.yaml)", _st_stilprofil, True),
    ("ST3 Modell-Kette nur kostenlose Claude-Modelle", _st_modell, True),
    ("ST4 Schutzzonen-Roundtrip (sprachkern)", _st_schutzzonen, True),
    ("ST5 Link-ZIEL-Änderung wird verworfen", _st_link_ziel, True),
    ("ST6 Anker-TEXT-Änderung wird verworfen", _st_anker_text, True),
    ("ST7 Überschriften-Änderung wird verworfen", _st_ueberschrift, True),
    ("ST8 Zahlen-Änderung wird verworfen (Fakten)", _st_zahlen, True),
    ("ST9 Shortcode-Verlust wird verworfen", _st_shortcode, True),
    ("ST10 Wortzahl < 90 % wird verworfen", _st_wortzahl, True),
    ("ST11 Legitime Stil-Änderung wird akzeptiert", _st_legitim, True),
    ("ST12 Fingerprint stabil/empfindlich", _st_fingerprint, True),
    ("ST13 KI-Antwort-Gate (fake caller: heilt/schützt)", _st_fake_caller, True),
    ("ST14 Ohne Anthropic-API (Auftrag: Claude nur ohne API)", _st_ohne_anthropic_api, True),
    ("ST15 Puter-Brücke vorhanden (Protokoll + Gratis-Zugang)", _st_bruecke, True),
]


def run_selftest() -> list:
    fehler = []
    for name, fn, erw in SELFTEST:
        try:
            ist = fn()
        except Exception as e:  # noqa: BLE001
            fehler.append(f"{name}: Exception {e.__class__.__name__}: {e}")
            continue
        if ist != erw:
            fehler.append(f"{name}: {ist}, erwartet {erw}")
    return fehler


def selftest() -> int:
    fehler = run_selftest()
    if fehler:
        print("🛑 CLAUDE-STILPOLITUR-SELBSTTEST ROT – die Lane selbst ist "
              "defekt (Exit 2, keine Datei wird geschrieben):")
        for f in fehler:
            print("   -", f)
        return 2
    print(f"✅ Claude-Stilpolitur-Selbsttest: {len(SELFTEST)} eingefrorene "
          "Fälle bestanden (offline, ohne API).")
    return 0


# ----------------------------------------------------------- Report/Historie
def write_report(rows: list, meta: dict, offen: int) -> None:
    L = [
        "# ✍️ CLAUDE-STILPOLITUR-REPORT (Claude, kostenlos ohne API, personalisiert)",
        "",
        f"**Stand:** {sk.now_utc()} UTC",
        f"**Modus:** {meta['mode']} · **Modell:** `{meta['modell']}`",
        f"**Artikel geprüft:** {meta['posts']} · **Kandidaten:** {meta['kandidaten']} "
        f"· **poliert:** {meta['poliert']} · **verworfen:** {meta['verworfen']} "
        f"· **offen (Budget/Rotation):** {offen}",
        "",
    ]
    if rows:
        L += ["| Artikel | Grund | Ergebnis | Δ Zeichen |", "|---|---|---|---|"]
        for r in rows[:80]:
            L.append(f"| `{r['slug']}` | {r['grund']} | {r['ergebnis']} | {r.get('delta', '')} |")
    else:
        L.append("🎉 Nichts zu polieren – Bestand auf Premium-Level (Fingerprint aktuell).")
    L += [
        "",
        "---",
        "_Claude (kostenlos, ohne API: Puter.js User-Pays) mit personalisiertem "
        "Prompt aus data/schreibstil.yaml "
        "+ data/brand_brain.yaml (Auftrag 25.09.2026). Läuft NACH der "
        "Offline-Optimierung (grammar_check + sprachglatt). Verifikation: "
        "Schutzzonen/Überschriften/Zahlen byte-identisch, Wortzahl ≥ 90 %. "
        "Offline-Grammatik: grammar_check.py · Glättung: sprachglatt.py · "
        "Stil-Messung: stil_guard.py._",
    ]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    with open(JSON_FILE, "w", encoding="utf-8") as fh:
        json.dump({"generated": datetime.datetime.now(datetime.timezone.utc)
                   .isoformat(timespec="seconds"),
                   **meta, "open": offen, "items": rows[:200]},
                  fh, ensure_ascii=False, indent=2)


def log_history(entry: dict) -> None:
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ----------------------------------------------------------- Main
def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="Claude-Stilpolitur (Claude 3.5 "
                                             "Sonnet, personalisiert)")
    ap.add_argument("--fix", action="store_true", help="polieren (Paid-API)")
    ap.add_argument("--dry-run", action="store_true",
                    help="KI-Antwort prüfen, nichts schreiben (C15-Trockenlauf)")
    ap.add_argument("--new-only", action="store_true", help="nur heutige Artikel")
    ap.add_argument("--include-drafts", action="store_true",
                    help="auch Entwürfe (draft: true) polieren")
    ap.add_argument("--force", action="store_true",
                    help="ignoriert Fingerprint/Rotations-Status")
    ap.add_argument("--limit", type=int, default=None,
                    help="max. Artikel pro Lauf (0 = unbegrenzt; Default "
                         "max_artikel_pro_tag aus ki_redaktion.yaml)")
    ap.add_argument("--file", default=None, help="nur dieser Artikel")
    ap.add_argument("--selftest", action="store_true", help="Sabotage-Schutz")
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1, wenn Kandidaten übrig bleiben")
    ap.add_argument("--json", action="store_true", help="Report als JSON")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    stf = run_selftest()
    if stf:
        print("🛑 SELBSTTEST ROT – Sabotage verhindert, kein Schreiben:")
        for f in stf:
            print("   -", f)
        return 2

    cfg = load_config()
    stil, brand = load_stil()
    system_prompt = render_system_prompt(stil, brand)
    now = datetime.datetime.now(datetime.timezone.utc)
    do_fix = args.fix and not args.dry_run

    if args.fix and not args.dry_run and not (os.environ.get("PUTER_AUTH_TOKEN") or "").strip():
        print("🛑 PUTER_AUTH_TOKEN fehlt – der KOSTENLOSE Claude-Zugang "
              "(Puter.js, ohne API) ist nicht eingerichtet.")
        print("   Einrichten: puter.com → kostenloses Konto → Auth-Token erzeugen "
              "(docs.puter.com) → GitHub → Settings → Secrets → Actions → "
              "PUTER_AUTH_TOKEN")
        if os.environ.get("GITHUB_ACTIONS"):
            print("::error title=Claude-Stilpolitur::PUTER_AUTH_TOKEN fehlt – "
                  "kostenlose Claude-Stil-Politur blockiert (kein Anthropic-Key "
                  "nötig, siehe docs/ANLEITUNG-CLAUDE-STILPOLITUR.md).")
        return 3

    only_file = None
    if args.file:
        p = args.file if os.path.isabs(args.file) else os.path.join(BLOG_DIR, args.file)
        if not os.path.exists(p):
            p = os.path.join(BLOG_DIR, "content", "posts", args.file)
        only_file = [p]

    arts = sk.load_articles(files=only_file, new_only=args.new_only,
                            include_drafts=args.include_drafts)
    state = load_state()
    auffrischung = int(cfg["auffrischung_tage"] or 0)

    kandidaten = []
    for a in arts:
        fp, prio, grund = auswahl(a["slug"], a["body"], state, auffrischung, now)
        if prio is not None or args.force:
            kandidaten.append((prio if prio is not None else 0, grund or "force",
                               fp, a))
    kandidaten.sort(key=lambda t: (t[0], t[3]["slug"]))

    limit = cfg["max_artikel_pro_tag"] if args.limit is None else args.limit
    if args.force and args.limit is None:
        limit = 0  # Force ohne Limit = alles
    ziel = kandidaten if not limit else kandidaten[:max(0, int(limit))]
    offen = max(0, len(kandidaten) - len(ziel))

    rows, polished, verworfen = [], 0, 0
    for prio, grund, fp, a in ziel:
        if args.dry_run or not args.fix:
            rows.append({"slug": a["slug"], "grund": grund,
                         "ergebnis": "Kandidat (kein --fix)" if not args.dry_run
                         else "Kandidat (Trockenlauf)", "delta": ""})
            continue
        neu, meldung = polish_body(system_prompt, build_user_prompt(a),
                                   a["body"], cfg)
        if neu is None:
            verworfen += 1
            rows.append({"slug": a["slug"], "grund": grund,
                         "ergebnis": f"verworfen – {meldung}", "delta": ""})
            state.setdefault("artikel", {})[a["slug"]] = {
                "fp": fp, "status": "verworfen", "grund": meldung[:120],
                "modell": cfg["modell"],
                "last": now.isoformat(timespec="seconds"),
            }
            continue
        new_content = sk.rebuild(a, neu)
        ok, grund_s = sk.write_verified(a, new_content, ENGINE)
        if not ok:
            verworfen += 1
            rows.append({"slug": a["slug"], "grund": grund,
                         "ergebnis": f"Schreibsperre – {grund_s}", "delta": ""})
            continue
        polished += 1
        state.setdefault("artikel", {})[a["slug"]] = {
            "fp": fingerprint(neu), "status": "ok",
            "modell": cfg["modell"], "grund": grund,
            "last": now.isoformat(timespec="seconds"),
        }
        rows.append({"slug": a["slug"], "grund": grund, "ergebnis": "poliert",
                     "delta": f"{len(neu) - len(a['body']):+d}"})
        print(f"  ✍️ {a['slug']}: poliert ({grund}, "
              f"{len(neu) - len(a['body']):+d} Zeichen)")

    meta = {"mode": "FIX" if do_fix else ("TROCKENLAUF" if args.dry_run else "REPORT"),
            "modell": cfg["modell"], "posts": len(arts),
            "kandidaten": len(kandidaten), "poliert": polished,
            "verworfen": verworfen}
    if do_fix:
        save_state(state)
    log_history({"date": now.strftime("%Y-%m-%d"), "mode": meta["mode"],
                 "modell": cfg["modell"], "posts": len(arts),
                 "kandidaten": len(kandidaten), "poliert": polished,
                 "verworfen": verworfen, "offen": offen})
    write_report(rows, meta, offen)

    if args.json:
        with open(JSON_FILE, encoding="utf-8") as fh:
            print(fh.read())
    else:
        print(f"✅ Claude-Stilpolitur {meta['mode']}: {len(arts)} Artikel "
              f"geprüft · {len(kandidaten)} Kandidaten · {polished} poliert · "
              f"{verworfen} verworfen · {offen} offen (Budget/Rotation).")
        print("   Report: CLAUDE-STILPOLITUR-REPORT.md · "
              f"Modell: {cfg['modell']}")

    return 1 if (args.strict and (offen or verworfen)) else 0


if __name__ == "__main__":
    sys.exit(main())
