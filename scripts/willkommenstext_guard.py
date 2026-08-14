#!/usr/bin/env python3
# ============================================================
#  WILLKOMMENSTEXT-GUARD – ständige SEO-Optimierung + Selbstheilung
#  für den Startseiten-Willkommenstext (hugo.toml homeInfoParams)
#  (14.08.2026, Frank: "Optimiere fortlaufend den Willkommenstext …
#  niemals langweilig … immer als SEO-Unique-Content erkennbar …
#  ständige Automatisierung mit sofortiger Selbstheilung: Wenn der
#  Text an Einzigartigkeit verliert, SEO-Trends sich ändern, neue
#  Gesetze/Tarife/Energiepreise/Finanzregeln erscheinen oder
#  Suchmaschinen neue Qualitätsrichtlinien veröffentlichen →
#  automatisch anpassen.")
#
#  WARUM EIN EIGENES SKRIPT (statt brand_guard.py zu erweitern):
#  brand_guard.py schützt den Willkommenstext seit 10.08.2026 bewusst
#  vor UNGEWOLLTEN Änderungen (Bot-Unfälle, KI-Polish-Kollateralschäden
#  – siehe dortige Kopf-Doku). Dieser neue Auftrag verlangt das
#  GEGENTEIL: GEWOLLTE, aber kontrollierte Evolution genau dieses
#  Textes. Beides bleibt vereinbar: DIESES Skript ist die einzige
#  autorisierte Quelle für Änderungen an Title/Content und ruft nach
#  jeder Änderung sofort `brand_guard.py --set-current` auf – der
#  neue Stand wird zum neuen Schutz-Lock. Jede ANDERE, nicht über
#  dieses Skript laufende Änderung bleibt weiterhin ein Fund für
#  brand_guard.py (z. B. ein Bot-Bug, der den Text kaputt schreibt).
#
#  KEIN HALLUZINATIONS-RISIKO BEI "AKTUELLEN ENTWICKLUNGEN": echte,
#  einzelfallgeprüfte Fakten (Gesetze, Paragraphen, exakte Preise)
#  darf eine KI nicht selbst erfinden. Deshalb liest dieses Skript
#  seine "aktuellen Aufhänger" ausschließlich aus der kuratierten,
#  von Mensch/Agent gepflegten Liste data/aktuelle_entwicklungen.yaml
#  (siehe Kopf-Doku dort) – die KI darf diese nur natürlich
#  einbauen/umformulieren, nicht neue Fakten dazuerfinden (Prompt-Regel
#  unten). SEO-Trend-Wissen kommt aus SEO-STANDARDS-2026.md (bereits
#  bestehende Wissensbasis von web_uniqueness_guard.py).
#
#  AUSLÖSER FÜR EINE AUTOMATISCHE NEUFORMULIERUNG (jede Bedingung
#  reicht einzeln):
#    1. ALTER: letzte Änderung > WILLKOMMENSTEXT_MAX_AGE_TAGE alt
#       (Standard 7 Tage) – "niemals langweilig" braucht einen festen
#       Rhythmus, nicht nur Ad-hoc-Trigger.
#    2. SEO-SIGNAL: SEO-STANDARDS-2026.md wurde seit der letzten
#       Textänderung aktualisiert (Hash-Vergleich) – neue Google-
#       Spielregeln sollen sich zeitnah niederschlagen.
#    3. EINZIGARTIGKEITS-VERFALL: der aktuelle Text überlappt (Shingle-
#       Jaccard) zu stark mit einer der letzten Versionen – Zeichen
#       dafür, dass zu wenig Substanz zwischen den Läufen geändert
#       wurde.
#    4. --force: manuell/durch einen Workflow-Trigger auf eine
#       geänderte Signal-Quelle (siehe .github/workflows/
#       willkommenstext-refresh.yml: on.push.paths).
#
#  SELBSTHEILUNG OHNE KI-VERFÜGBARKEIT: Sind GROQ_API_KEY/
#  GEMINI_API_KEY nicht gesetzt, nicht erreichbar, oder liefert die KI
#  wiederholt ungültigen Text (Floskeln, falsche Länge, zu unähnlich/
#  zu ähnlich, Rechtschreibfehler laut hunspell), greift eine
#  kuratierte, handgeschriebene FALLBACK-Rotation (FALLBACK_POOL) –
#  die Automatik bleibt dadurch IMMER lauffähig, unabhängig von
#  externen APIs (echte Selbstheilung, kein Single Point of Failure).
#
#  Aufruf:
#    python3 scripts/willkommenstext_guard.py             # prüfen, ggf. heilen
#    python3 scripts/willkommenstext_guard.py --dry-run    # nur prüfen
#    python3 scripts/willkommenstext_guard.py --force      # sofort neu (Signal-Update)
#    python3 scripts/willkommenstext_guard.py --json
# ============================================================

import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HUGO_TOML = os.path.join(ROOT, "hugo.toml")
SIGNALS_YAML = os.path.join(ROOT, "data", "aktuelle_entwicklungen.yaml")
HISTORY_FILE = os.path.join(ROOT, "data", "willkommenstext_history.jsonl")
SEO_STANDARDS = os.path.join(ROOT, "SEO-STANDARDS-2026.md")
PUBLIC_DIR = os.path.join(ROOT, "public")
REPORT = os.path.join(ROOT, "WILLKOMMENSTEXT-REPORT.md")

DRY_RUN = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv
AS_JSON = "--json" in sys.argv

MAX_AGE_DAYS = int(os.environ.get("WILLKOMMENSTEXT_MAX_AGE_TAGE", "7"))
JACCARD_STALE = 0.60   # Vorgänger-Version zu ähnlich -> Auslöser "Einzigartigkeits-Verfall"
JACCARD_REJECT = 0.55  # Kandidat zu ähnlich zu EINER der letzten 5 Versionen -> verworfen

TITLE_RX = re.compile(r'^(    Title\s*=\s*)"(.*)"\s*$', re.M)
CONTENT_RX = re.compile(r'^(    Content\s*=\s*)"(.*)"\s*$', re.M)

# Kern-Kategorien des Blogs (nur LIVE-Pillars, keine draft:true-Platzhalter
# wie frugalismus/mietwagen bewerben – siehe content/pillar/).
CORE_CATEGORIES = ["strom", "gas", "internet", "versicherung", "konto"]

# KI-Floskeln, die in KEINEM Profi-Text vorkommen dürfen (identische Liste
# wie scripts/generate_drafts.py PROFI_FLOSKELN / scripts/extend_articles.py
# – bewusst dupliziert, siehe dortige Konvention, statt Cross-Import).
# Marken-Stimme: Der gesamte Blog spricht Leser konsequent informell mit
# "du" an (siehe Original-Text "Dein Ratgeber", "dein Geld arbeitet für
# dich" sowie SYSTEM_ANREDE in generate_drafts.py für Artikel). Eine KI
# darf hier NIEMALS in die formelle "Sie"-Anrede kippen (14.08.2026,
# live entdeckt: Gemini generierte "Ich erkläre Ihnen…" – inkonsistente
# Markenstimme gegenüber jedem anderen Text auf der Seite).
FORMAL_ANREDE_RX = re.compile(r"\b(Sie|Ihnen|Ihrem|Ihrer|Ihren|Ihres|Ihr|Ihre)\b")

BANNED_PHRASES = [
    "in der heutigen schnelllebigen welt", "in der heutigen zeit",
    "es ist wichtig zu beachten", "zusammenfassend lässt sich sagen",
    "zusammenfassend kann man sagen", "des weiteren", "in diesem artikel werden wir",
    "in diesem artikel erfahren sie", "es gibt viele möglichkeiten",
    "es gibt zahlreiche", "wenn es darum geht", "heutzutage",
    "in der modernen welt", "tauchen wir ein", "lassen sie uns",
    "der schlüssel zum erfolg", "ein muss für jeden", "unverzichtbar für",
    "das a und o", "die welt der", "in einer welt, in der",
    "entdecke", "entdecken sie", "tauche ein", "willkommen in der welt",
]

# ------------------------------------------------------------------
#  Kuratierte Fallback-Rotation (siehe Kopf-Doku): jede Variante
#  gehört zu genau einem Eintrag aus data/aktuelle_entwicklungen.yaml
#  (gleicher Index) und ist von Hand geschrieben/geprüft – so bleibt
#  die Automatik auch ohne KI-Zugriff funktionsfähig und lauffähig.
# ------------------------------------------------------------------
FALLBACK_POOL = [
    {
        "signal_id": "energie-herbst-nachzahlung",
        "title": "Geld sparen ohne Verzicht: Dein Ratgeber für Strom, Gas, Versicherungen & Finanzen",
        "content": (
            "💰 Geld sparen, ohne den Gürtel enger zu schnallen – genau darum geht es hier.\n\n"
            "Regelmäßig erscheint ein neuer, verständlicher Ratgeber: **Strom, Gas und Internet günstiger**, "
            "Versicherungen richtig wählen und Konto & Karte ohne Gebührenfallen. Gerade im Herbst und Winter "
            "kommen die teuren Nachzahlungen – wer vorher vergleicht, spart oft mehrere hundert Euro im Jahr. "
            "Ohne Fachchinesisch, ohne Verkaufsdruck – dafür mit konkreten Zahlen, ehrlichen Vor- und Nachteilen "
            "und Schritt-für-Schritt-Anleitungen.\n\n"
            "Stöbere dich durch die Ratgeber – dein Geld arbeitet ab heute für dich, nicht umgekehrt. 🚀"
        ),
    },
    {
        "signal_id": "energie-jahreswechsel-wechselfenster",
        "title": "Strom, Gas, Versicherungen & Finanzen: Dein ehrlicher Spar-Ratgeber",
        "content": (
            "💡 Sparen heißt hier nicht verzichten, sondern besser vergleichen.\n\n"
            "Regelmäßig ein neuer, klar geschriebener Ratgeber zu **Strom, Gas, Internet, Versicherungen und "
            "Konto & Karte** – mit echten Zahlen statt Werbeversprechen. Rund um den Jahreswechsel ändern viele "
            "Versorger ihre Preise neu, genau dann lohnt sich ein Wechsel am meisten. Kein Fachchinesisch, kein "
            "Verkaufsdruck: nur ehrliche Vor- und Nachteile und Schritt-für-Schritt-Anleitungen zum Nachmachen.\n\n"
            "Schau dich um – dein Geld sollte für dich arbeiten, nicht umgekehrt. 🚀"
        ),
    },
    {
        "signal_id": "versicherung-beitragsanpassung-jahresende",
        "title": "Dein Ratgeber für Strom, Gas, Versicherungen & Konto – ehrlich erklärt",
        "content": (
            "📊 Weniger zahlen, ohne auf etwas zu verzichten – das ist das Versprechen dieses Blogs.\n\n"
            "Regelmäßig neue, verständliche Ratgeber zu **Strom, Gas und Internet**, zu Versicherungen und zu "
            "Konto & Karte ohne versteckte Gebühren. Viele Versicherer verschicken ihre Beitragsanpassung zum "
            "Jahresende – der jährliche Vergleich lohnt sich fast immer mehr als das automatische Verlängern. "
            "Ohne Fachchinesisch, ohne Verkaufsdruck: nur konkrete Zahlen, ehrliche Vor- und Nachteile, klare "
            "Schritt-für-Schritt-Anleitungen.\n\n"
            "Stöbere durch die Ratgeber – dein Geld arbeitet ab heute für dich. 🚀"
        ),
    },
    {
        "signal_id": "konto-gebuehren-transparenz",
        "title": "Strom, Gas, Internet, Versicherungen, Konto: Spar-Ratgeber ohne Fachchinesisch",
        "content": (
            "💰 Geld sparen, ohne den Alltag einzuschränken – genau darum geht's.\n\n"
            "Hier erscheint regelmäßig ein neuer, gut verständlicher Ratgeber: **Strom, Gas und Internet "
            "günstiger**, Versicherungen richtig wählen, Konto & Karte ohne Gebührenfallen. Gerade bei "
            "Girokonten ändern sich Bedingungen und Gebühren inzwischen häufiger als früher – ein kurzer Check "
            "pro Jahr reicht meist schon. Keine Verkaufsfloskeln, dafür konkrete Zahlen, ehrliche Vor- und "
            "Nachteile und Anleitungen zum direkten Umsetzen.\n\n"
            "Stöbere dich durch – dein Geld arbeitet ab heute für dich, nicht umgekehrt. 🚀"
        ),
    },
    {
        "signal_id": "internet-tarifdschungel-bandbreite",
        "title": "Geld sparen ohne Verzicht: Ratgeber für Strom, Gas, Internet & Versicherungen",
        "content": (
            "⚡ Weniger zahlen, ohne dass sich dein Alltag ändert – das ist das Ziel hier.\n\n"
            "Regelmäßig ein neuer, klar geschriebener Ratgeber: Strom, Gas und **Internet günstiger**, "
            "Versicherungen ohne Kleingedrucktes und Konto & Karte ohne Gebührenfallen. Beim Internet-Tarif "
            "zahlen viele für mehr Tempo, als sie im Alltag wirklich brauchen – ein realistischer Bedarfscheck "
            "spart oft mehr als der bloße Anbieterwechsel. Ohne Fachchinesisch, ohne Verkaufsdruck – dafür mit "
            "Zahlen, ehrlichen Vor- und Nachteilen und Schritt-für-Schritt-Anleitungen.\n\n"
            "Stöbere dich durch die Ratgeber – dein Geld arbeitet ab heute für dich. 🚀"
        ),
    },
    {
        "signal_id": "zinsumfeld-tagesgeld",
        "title": "Dein ehrlicher Ratgeber für Strom, Gas, Versicherungen, Konto & Karte",
        "content": (
            "💰 Sparen, ohne zu verzichten – dafür ist dieser Blog da.\n\n"
            "Regelmäßig ein neuer, verständlicher Ratgeber zu **Strom, Gas und Internet**, zu Versicherungen "
            "und zu Konto & Karte ohne Gebührenfallen. Bei Tagesgeld und Zinsangeboten lohnt sich gerade jetzt "
            "der genaue Blick auf befristete Lockzinsen, die nach wenigen Monaten wieder fallen. Ohne "
            "Fachchinesisch, ohne Verkaufsdruck: konkrete Zahlen, ehrliche Vor- und Nachteile, Schritt-für-"
            "Schritt erklärt.\n\n"
            "Stöbere dich durch die Ratgeber – dein Geld arbeitet ab heute für dich, nicht umgekehrt. 🚀"
        ),
    },
    {
        "signal_id": "seo-qualitaet-e-e-a-t",
        "title": "Strom, Gas, Versicherungen & Finanzen: Ratgeber mit echten Erfahrungen",
        "content": (
            "🔍 Sparen beginnt mit ehrlichen Informationen, nicht mit Werbeversprechen.\n\n"
            "Jeder Ratgeber hier zu **Strom, Gas, Internet**, Versicherungen und Konto & Karte basiert auf "
            "echten Vergleichen und nachvollziehbaren Zahlen statt austauschbaren Floskeln. Kein Fachchinesisch, "
            "kein Verkaufsdruck – dafür klare Vor- und Nachteile und Schritt-für-Schritt-Anleitungen, die du "
            "direkt umsetzen kannst.\n\n"
            "Stöbere durch die Ratgeber – dein Geld arbeitet ab heute für dich, nicht umgekehrt. 🚀"
        ),
    },
    {
        "signal_id": "energie-variable-vs-fest",
        "title": "Geld sparen ohne Verzicht: Dein Ratgeber für Strom, Gas & Versicherungen",
        "content": (
            "💰 Weniger zahlen, ohne den Alltag einzuschränken – darum geht's hier.\n\n"
            "Regelmäßig ein neuer, verständlicher Ratgeber: **Strom, Gas und Internet günstiger**, "
            "Versicherungen richtig wählen, Konto & Karte ohne Gebührenfallen. Zwischen variablen Tarifen und "
            "Festpreisverträgen gibt es aktuell wieder größere Unterschiede – pauschale Empfehlungen greifen da "
            "zu kurz, es kommt auf den eigenen Verbrauch an. Ohne Fachchinesisch, ohne Verkaufsdruck: konkrete "
            "Zahlen, ehrliche Vor- und Nachteile, klare Anleitungen.\n\n"
            "Stöbere dich durch die Ratgeber – dein Geld arbeitet ab heute für dich. 🚀"
        ),
    },
    {
        "signal_id": "versicherung-vergleichsportale-nicht-vollstaendig",
        "title": "Dein Ratgeber für Strom, Gas, Versicherungen & Konto – ohne Verkaufsdruck",
        "content": (
            "💰 Sparen, ohne etwas aufzugeben – dafür gibt's diesen Blog.\n\n"
            "Regelmäßig ein neuer, klar geschriebener Ratgeber: **Strom, Gas und Internet günstiger**, "
            "Versicherungen richtig wählen, Konto & Karte ohne Gebührenfallen. Vergleichsportale zeigen selten "
            "alle Anbieter am Markt – wer nur das erste Ergebnis nimmt, lässt oft bares Geld liegen. Ohne "
            "Fachchinesisch: konkrete Zahlen, ehrliche Vor- und Nachteile, Schritt-für-Schritt-Anleitungen zum "
            "Nachmachen.\n\n"
            "Stöbere dich durch – dein Geld arbeitet ab heute für dich, nicht umgekehrt. 🚀"
        ),
    },
    {
        "signal_id": "saisonal-fruehjahrsputz-vertraege",
        "title": "Strom, Gas, Versicherungen, Konto: Dein jährlicher Spar-Check",
        "content": (
            "🧾 Einmal im Jahr richtig vergleichen bringt oft mehr als viele einzelne spontane Wechsel.\n\n"
            "Hier erscheint regelmäßig ein neuer, verständlicher Ratgeber zu **Strom, Gas und Internet**, zu "
            "Versicherungen und zu Konto & Karte ohne Gebührenfallen. Ein kompletter Vertrags-Check an einem "
            "Nachmittag deckt erfahrungsgemäß mehr Sparpotenzial auf als Einzelaktionen übers Jahr verteilt. "
            "Ohne Fachchinesisch, ohne Verkaufsdruck – dafür konkrete Zahlen und Schritt-für-Schritt-"
            "Anleitungen.\n\n"
            "Stöbere dich durch die Ratgeber – dein Geld arbeitet ab heute für dich, nicht umgekehrt. 🚀"
        ),
    },
]


# ------------------------------------------------------------------ Hilfsfunktionen

def toml_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def toml_unescape(s: str) -> str:
    return s.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")


def read_hugo_toml() -> str:
    with open(HUGO_TOML, encoding="utf-8") as f:
        return f.read()


def current_title_content(src: str) -> tuple[str, str]:
    tm = TITLE_RX.search(src)
    cm = CONTENT_RX.search(src)
    title = toml_unescape(tm.group(2)) if tm else ""
    content = toml_unescape(cm.group(2)) if cm else ""
    return title, content


def normalize(text: str) -> str:
    t = re.sub(r"[*_#>`]", " ", text)
    t = t.lower().replace("ß", "ss")
    return " ".join(re.findall(r"[a-zäöüß0-9]+", t))


def shingles(norm: str, n: int = 4) -> set:
    w = norm.split()
    if len(w) < n:
        return {" ".join(w)} if w else set()
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def load_signals() -> list[dict]:
    with open(SIGNALS_YAML, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or []
    today = datetime.date.today().isoformat()
    valid = []
    for entry in raw:
        if entry.get("ab") and entry["ab"] > today:
            continue
        if entry.get("bis") and entry["bis"] < today:
            continue
        valid.append(entry)
    return valid or raw  # niemals leer laufen: notfalls auch abgelaufene nehmen


def pick_signal_index(signals: list[dict]) -> int:
    """Deterministisch nach ISO-Kalenderwoche – ändert sich automatisch mit
    der Zeit, ist aber für denselben Lauf reproduzierbar (kein Zufall,
    der Tests/Nachvollziehbarkeit erschwert)."""
    week = datetime.date.today().isocalendar()[1]
    return week % len(signals) if signals else 0


def load_history() -> list[dict]:
    if not os.path.isfile(HISTORY_FILE):
        return []
    out = []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return out


def append_history(entry: dict) -> None:
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def file_hash(path: str) -> str:
    if not os.path.isfile(path):
        return ""
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


# ------------------------------------------------------------------ Auslöser-Logik

def needs_refresh(current_content: str, history: list[dict]) -> tuple[bool, list[str]]:
    reasons = []
    if FORCE:
        reasons.append("manuell/Trigger erzwungen (--force)")

    if not history:
        reasons.append("noch keine Historie – Erstlauf")
        return True, reasons

    last = history[-1]
    last_ts = datetime.datetime.fromisoformat(last["ts"].replace("Z", "+00:00"))
    age_days = (datetime.datetime.now(datetime.timezone.utc) - last_ts).days
    if age_days >= MAX_AGE_DAYS:
        reasons.append(f"Alter: letzte Änderung vor {age_days} Tagen (Limit {MAX_AGE_DAYS})")

    last_seo_hash = last.get("seo_standards_hash", "")
    current_seo_hash = file_hash(SEO_STANDARDS)
    if last_seo_hash and current_seo_hash and last_seo_hash != current_seo_hash:
        reasons.append("SEO-STANDARDS-2026.md wurde seit der letzten Anpassung aktualisiert")

    # Einzigartigkeits-Verfall: aktueller Live-Text vs. die Version davor
    if len(history) >= 2:
        prev_norm = normalize(history[-2].get("content", ""))
        cur_norm = normalize(current_content)
        j = jaccard(shingles(prev_norm), shingles(cur_norm))
        if j >= JACCARD_STALE:
            reasons.append(f"Einzigartigkeits-Verfall: Jaccard {j:.2f} ggü. Vorgänger-Version (Limit {JACCARD_STALE})")

    return bool(reasons), reasons


# ------------------------------------------------------------------ Validierung

def validate_candidate(title: str, content: str, history: list[dict]) -> list[str]:
    problems = []
    if not (40 <= len(title) <= 120):
        problems.append(f"Titel-Länge {len(title)} außerhalb 40-120 Zeichen")
    if not (250 <= len(content) <= 700):
        problems.append(f"Content-Länge {len(content)} außerhalb 250-700 Zeichen")

    low = (title + " " + content).lower()
    hits = [p for p in BANNED_PHRASES if p in low]
    if hits:
        problems.append("KI-Floskel(n) gefunden: " + ", ".join(hits))

    formal_hits = FORMAL_ANREDE_RX.findall(title + " " + content)
    if formal_hits:
        problems.append(f"formelle 'Sie'-Anrede statt Marken-'du' gefunden: {set(formal_hits)}")

    mentioned = [c for c in CORE_CATEGORIES if c in low or (c == "versicherung" and "versicherung" in low)]
    if len(mentioned) < 3:
        problems.append(f"zu wenige Kern-Kategorien erwähnt ({mentioned})")

    if '"' in content or '"' in title:
        problems.append("enthält doppelte Anführungszeichen (TOML-Konflikt)")

    cand_shingles = shingles(normalize(content))
    for h in history[-5:]:
        j = jaccard(cand_shingles, shingles(normalize(h.get("content", ""))))
        if j >= JACCARD_REJECT:
            problems.append(f"zu ähnlich zu früherer Version vom {h.get('ts', '?')[:10]} (Jaccard {j:.2f})")

    words = re.findall(r"[A-Za-zÄÖÜäöüß]+", content)
    candidates = [w for w in words if len(w) > 3 and not w[0].isupper()]
    if candidates and shutil.which("hunspell"):
        try:
            proc = subprocess.run(
                ["hunspell", "-d", "de_DE"], input="\n".join(candidates),
                capture_output=True, text=True, timeout=15,
            )
            unknown = sum(1 for line in proc.stdout.splitlines() if line.startswith("&") or line.startswith("#"))
            ratio = unknown / len(candidates)
            if ratio > 0.25:
                problems.append(f"zu viele hunspell-unbekannte Wörter ({ratio:.0%})")
        except Exception:  # noqa: BLE001
            pass

    return problems


# ------------------------------------------------------------------ KI-Generierung

def _retry(fn, attempts=2, base_delay=2):
    last_err = None
    for i in range(attempts):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 500, 502, 503, 504):
                time.sleep(base_delay * (i + 1))
                continue
            raise
        except (TimeoutError, urllib.error.URLError, ConnectionError):
            last_err = None
            time.sleep(base_delay * (i + 1))
    if last_err:
        raise last_err
    return None


def http_json(url, data=None, headers=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_prompt(signal: dict, month_year: str) -> str:
    return f"""Du schreibst den Willkommenstext (Titel + Kurztext) für die Startseite des
deutschen Finanz-Ratgeber-Blogs "FranksFinanzcheck" (Themen: Strom, Gas,
Internet/DSL, Versicherungen, Konto & Karten).

STIL: menschlich, klar, aktiv, modern. Sprich den Leser durchgehend mit
dem informellen "du" an (NIEMALS "Sie"/"Ihnen"/"Ihr" – die gesamte Seite
duzt konsequent, eine formelle Anrede wäre ein Markenbruch). KEINE
KI-Floskeln (verboten u. a.: "In der heutigen Zeit", "Zusammenfassend
lässt sich sagen", "Tauche ein", "Entdecke", "Der Schlüssel zum Erfolg",
"Es ist wichtig zu beachten"). Kurze, aktive Sätze. Kein Werbesprech,
kein Verkaufsdruck.

AKTUELLER AUFHÄNGER (baue ihn natürlich in EINEM Satz ein, erfinde KEINE
zusätzlichen Fakten, Zahlen, Gesetze oder Paragraphen dazu):
"{signal['hook']}"

STAND: {month_year}

PFLICHT-INHALT:
- Erwähne mindestens 3 der 5 Kategorien Strom, Gas, Internet, Versicherungen,
  Konto (natürlich im Fließtext, kein Aufzählungs-Stakkato).
- Betone: ohne Fachchinesisch, ohne Verkaufsdruck, mit konkreten Zahlen und
  ehrlichen Vor-/Nachteilen.
- 1-2 passende Emojis (nicht mehr).

FORMAT (exakt, keine weiteren Zeilen davor/danach):
TITLE: <Titel, 50-100 Zeichen, KEINE Anführungszeichen>
CONTENT: <Text, 300-600 Zeichen, 2-3 Absätze getrennt durch \\n\\n, darf
**Markdown-Bold** für 1-2 Kernbegriffe nutzen, KEINE Anführungszeichen>
"""


def call_groq(prompt: str):
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        return None
    body = json.dumps({
        "model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 1.0,
        "max_tokens": 500,
    }).encode("utf-8")

    def _call():
        resp = http_json(
            "https://api.groq.com/openai/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        )
        return resp["choices"][0]["message"]["content"]

    return _retry(_call)


def call_gemini(prompt: str):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")

    def _call():
        resp = http_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        return resp["candidates"][0]["content"]["parts"][0]["text"]

    return _retry(_call)


def parse_ai_output(raw: str) -> tuple[str, str] | None:
    tm = re.search(r"TITLE:\s*(.+)", raw)
    cm = re.search(r"CONTENT:\s*(.+)", raw, re.S)
    if not tm or not cm:
        return None
    title = tm.group(1).strip().strip('"').split("\n")[0].strip()
    content = cm.group(1).strip().strip('"')
    content = content.replace("\\n\\n", "\n\n").replace("\\n", "\n")
    return title, content


def generate_candidate(signal: dict, history: list[dict]) -> tuple[str, str, str]:
    """Liefert (title, content, quelle). Quelle = 'ai:groq' | 'ai:gemini' | 'fallback'."""
    month_year = datetime.date.today().strftime("%B %Y")
    prompt = build_prompt(signal, month_year)

    for provider_name, provider_fn in (("ai:groq", call_groq), ("ai:gemini", call_gemini)):
        for _attempt in range(2):
            try:
                raw = provider_fn(prompt)
            except Exception:  # noqa: BLE001
                raw = None
            if not raw:
                break  # kein Key/Provider nicht erreichbar -> nächster Provider
            parsed = parse_ai_output(raw)
            if not parsed:
                continue
            title, content = parsed
            problems = validate_candidate(title, content, history)
            if not problems:
                return title, content, provider_name
            # ungültig -> nochmal versuchen (gleicher Provider), sonst nächster

    # Fallback: kuratierte Variante zum gewählten Signal – garantiert
    # valide (Länge/Floskeln/Kategorien, siehe FALLBACK_POOL-Selbsttest),
    # aber falls sie (z. B. bei zweimaligem Lauf in derselben Kalenderwoche
    # ohne KI-Zugriff) zu ähnlich zur jüngsten Historie wäre, rotiert die
    # Auswahl deterministisch zum NÄCHSTEN Pool-Eintrag weiter – Text
    # wiederholt sich dadurch nie, auch rein offline nicht.
    start = next((i for i, f in enumerate(FALLBACK_POOL) if f["signal_id"] == signal["id"]), 0)
    n = len(FALLBACK_POOL)
    for step in range(n):
        fb = FALLBACK_POOL[(start + step) % n]
        problems = validate_candidate(fb["title"], fb["content"], history)
        if not problems:
            return fb["title"], fb["content"], "fallback"
    # Unwahrscheinlicher Extremfall (alle Varianten "verbraucht"): lieber
    # eine bereits genutzte, aber strukturell einwandfreie Variante
    # ausliefern als gar nichts zu heilen (Selbstheilung geht vor Perfektion).
    fb = FALLBACK_POOL[start]
    return fb["title"], fb["content"], "fallback"


# ------------------------------------------------------------------ Schreiben + Verifikation

def write_hugo_toml(title: str, content: str) -> None:
    """Ersetzt NUR den Inhalt der Anführungszeichen (wie brand_guard.py
    heal()), NICHT das gesamte Regex-Match – sonst frisst `\\s*$` im
    Pattern (matched in MULTILINE-Modus auch Zeilenumbrüche) versehentlich
    die Leerzeile NACH dem Content-Feld mit."""
    src = read_hugo_toml()
    tm = TITLE_RX.search(src)
    if tm:
        src = src[:tm.start(2)] + toml_escape(title) + src[tm.end(2):]
    cm = CONTENT_RX.search(src)
    if cm:
        src = src[:cm.start(2)] + toml_escape(content) + src[cm.end(2):]
    with open(HUGO_TOML, "w", encoding="utf-8") as f:
        f.write(src)


def resign_brand_guard() -> bool:
    """hugo.toml ist sowohl in brand_guard.py (Title/Content-Werte) als auch
    in integrity_guard.py (KRITISCH: ganze Datei per SHA-256) gesperrt;
    data/brand_lock.yaml selbst ist zusätzlich FEST-gelockt in
    integrity_guard.py. Nach einer autorisierten Änderung müssen daher
    BEIDE Wachen neu signiert werden, sonst stellt der jeweils andere
    Guard beim nächsten Lauf den alten Text automatisch wieder her."""
    r1 = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "brand_guard.py"), "--set-current"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    r2 = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "integrity_guard.py"), "--set-current"],
        cwd=ROOT, capture_output=True, text=True, timeout=60,
    )
    return r1.returncode == 0 and r2.returncode == 0


def rebuild_hugo() -> bool:
    hugo_bin = shutil.which("hugo") or ("/tmp/hugo" if os.path.isfile("/tmp/hugo") else None)
    if not hugo_bin:
        return False
    r = subprocess.run([hugo_bin, "--minify"], cwd=ROOT, capture_output=True, text=True, timeout=180)
    return r.returncode == 0


def verify_render(title: str) -> tuple[bool, str]:
    index_html = os.path.join(PUBLIC_DIR, "index.html")
    if not os.path.isfile(index_html):
        return False, "public/index.html fehlt (hugo --minify gelaufen?)"
    html = open(index_html, encoding="utf-8", errors="ignore").read()
    # Hugo escaped Sonderzeichen in HTML (z. B. & -> &amp;) - grober,
    # aber robuster Teil-String-Vergleich auf die ersten reinen Wörter.
    probe = re.sub(r"[^\w\s]", "", title)[:30].strip()
    if probe and probe not in re.sub(r"[^\w\s]", "", re.sub(r"<[^>]+>", " ", html)):
        return False, "Neuer Titel taucht nicht im gebauten public/index.html auf"
    return True, ""


# ------------------------------------------------------------------ Main

def main() -> int:
    src = read_hugo_toml()
    current_title, current_content = current_title_content(src)
    history = load_history()

    refresh, reasons = needs_refresh(current_content, history)

    if not refresh:
        result = {
            "refreshed": False, "reasons": [], "title": current_title,
            "content_len": len(current_content),
        }
        if AS_JSON:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("# 🌱 WILLKOMMENSTEXT-REPORT (willkommenstext_guard.py)\n")
            print("🎉 Kein Auffrischungsbedarf – Text ist aktuell, einzigartig und SEO-frisch genug.")
        return 0

    signals = load_signals()
    idx = pick_signal_index(signals)
    signal = signals[idx] if signals else {"id": "generisch", "hook": ""}

    new_title, new_content, source = generate_candidate(signal, history)

    if DRY_RUN:
        result = {
            "refreshed": True, "dry_run": True, "reasons": reasons,
            "signal": signal.get("id"), "source": source,
            "old_title": current_title, "new_title": new_title,
            "old_content": current_content, "new_content": new_content,
        }
        if AS_JSON:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("# 🌱 WILLKOMMENSTEXT-REPORT (willkommenstext_guard.py, DRY-RUN)\n")
            print(f"**Auslöser:** {'; '.join(reasons)}")
            print(f"**Signal:** {signal.get('id')} · **Quelle:** {source}\n")
            print(f"### Neuer Titel\n{new_title}\n")
            print(f"### Neuer Content\n{new_content}\n")
        return 0

    write_hugo_toml(new_title, new_content)
    resigned = resign_brand_guard()
    built = rebuild_hugo()
    render_ok, render_msg = verify_render(new_title) if built else (False, "Hugo-Build fehlgeschlagen")

    append_history({
        "ts": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
        "title": new_title,
        "content": new_content,
        "signal_id": signal.get("id"),
        "source": source,
        "reasons": reasons,
        "seo_standards_hash": file_hash(SEO_STANDARDS),
        "render_verified": render_ok,
    })

    mode = "REFRESHED"
    lines = [
        "# 🌱 WILLKOMMENSTEXT-REPORT (willkommenstext_guard.py)", "",
        f"**Stand:** {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}",
        f"**Auslöser:** {'; '.join(reasons)}",
        f"**Signal:** `{signal.get('id')}` · **Quelle:** {source} · "
        f"**Brand-/Integrity-Lock neu signiert:** {'✅' if resigned else '❌'} · "
        f"**Render-Beweis:** {'✅' if render_ok else '❌ ' + render_msg}",
        "",
        "### Vorher (Titel)", f"> {current_title}", "",
        "### Nachher (Titel)", f"> {new_title}", "",
        "### Vorher (Content)", f"> {current_content}", "",
        "### Nachher (Content)", f"> {new_content}", "",
        "---",
        "_Automatisch erzeugt/geheilt – Änderungen an diesem Text NUR über dieses Skript, "
        "sonst stellt brand_guard.py den letzten signierten Stand wieder her._",
    ]
    report_text = "\n".join(lines)
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(report_text + "\n")

    if AS_JSON:
        print(json.dumps({
            "refreshed": True, "reasons": reasons, "signal": signal.get("id"),
            "source": source, "new_title": new_title, "new_content": new_content,
            "resigned": resigned, "render_ok": render_ok,
        }, ensure_ascii=False, indent=2))
    else:
        print(report_text)

    return 0 if (resigned and render_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
