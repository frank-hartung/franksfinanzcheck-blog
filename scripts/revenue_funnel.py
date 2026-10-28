#!/usr/bin/env python3
"""
REVENUE-FUNNEL – die Umsatzmessung: Klick → Antrag → Provision

WARUM: Eine Profi-Agentur investiert keinen Euro in Reichweite, bevor der
Monetarisierungs-Trichter sichtbar ist. Die Einzelteile existieren (eigener
Klickzähler, Provisions-Tabelle, Klick-Attribution), aber die EINHEIT – der
Trichter mit seinen Kennzahlen je Woche – fehlte. Ohne ihn heißt es
„0 Klicks, 0.00 €“ – und das ist kein Messwert, sondern Unwissen. Dieses
Skript übersetzt Unwissen in eine dokumentierte Datenlücke und misst alles,
was messbar ist:

  1. Affiliate-Klicks             (eigener cookieloser /go/-Zähler je Stelle/Artikel)
  2. Klick → Antrag               (Abschlüsse aus der Provisions-Tabelle ÷ Klicks)
  3. Antrag → bestätigter Abschluss (approved ÷ alle Anträge)
  4. Stornoquote                  (declined ÷ abgeschlossene Anträge)
  5. EPC                          (Provision ÷ Affiliate-Klicks)
  dazu Provision gesamt/bezahlt   (Provisions-Tabelle, Monatssicht)

KEINE BESUCHE – mit Absicht: Seit 11.10.2026 läuft auf dem Blog kein
Besucherzähler und kein Reichweiten-Tracking (Datenschutzentscheidung). Eine
Kennzahl ohne Quelle wäre für immer „unbekannt“, also Dekoration – darum gibt
es weder Besuchszahlen noch Outbound-CTR noch „Provision pro 100 Besuche“. Der
Trichter beginnt beim Klick. Kommt je ein datenschutzgeprüfter Zähler, ist das
eine eigene Entscheidung samt Quelle, Meta-Datei und Test – kein stiller
Wiedereinbau (Sperre: scripts/fremdmessung_sperre.py).

EHRLICHE REGELN (Hausrecht der Messkette):
  - Fehlende Quelle ⇒ Kennzahl = „unbekannt“, NIE eine 0. Eine 0 ist eine
    Aussage über die Realität; „unbekannt“ ist eine Aussage über unsere Pipeline.
  - Eine bewusst ausgeschaltete oder noch nie befüllte Quelle ist eine
    BETRIEBSGRENZE (INFO, Ampel bleibt grün), keine Lücke. Eine Quelle, die
    laufen SOLL (Klickzähler `aktiv: true`) und nicht liefert, ist eine Lücke.
  - Jede Quelle trägt Alter + Status ins Report; der Governance-Gate macht aus
    „Messlücken: N“ einen gelben, handlungsbedürftigen Befund – das bleibt
    sichtbar, bis die Lücke zu ist. Kein Dauer-Alarm-Müll, aber auch kein
    Vergessen.
  - Keine Rohdaten im Report: nur Aggregat + Pfade (DSGVO wie die Importe).

AUSGABEN:
  - data/revenue_funnel.json           – maschinenlesbar (Scorecard, Engine, Dashboard)
  - data/revenue_funnel_history.jsonl  – Wochenreihen für Trend + WoW-Delta
  - REVENUE-FUNNEL-REPORT.md (root)    – Wochenseite mit Tabellen + Empfehlungen

Nutzung:
  python3 scripts/revenue_funnel.py            # berechnen + schreiben
  python3 scripts/revenue_funnel.py --print    # nur stdout (lokal, ohne Schreiblast)
  python3 scripts/revenue_funnel.py --selftest # Logik-Beweis, schreibt nichts ins Repo

Exit: 0 = kompletter Trichter gemessen oder bewusst begrenzt, 1 = Messlücken
      dokumentiert (kein Crash, aber Handlungsbedarf), 2 = Selbsttest/Hausfehler.
"""
import datetime
import glob
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

DATA = os.path.join(BLOG_DIR, "data")
# Eigener cookieloser /go/-Zähler: `scripts/klick_import.py` schreibt Zeilen im
# Format von click_attribution.py plus eine Meta-Datei (status ok |
# nicht_konfiguriert | fehler, stand = Zeitstempel). Der Betriebsschalter steht
# in `data/klickmessung.yaml` – derselbe, den click_chain_guard.py und
# affiliate_shield.py lesen.
CLICKS = os.path.join(DATA, "klicks_eigen.json")
CLICKS_META = os.path.join(DATA, "klicks_eigen.meta.json")
KLICKMESSUNG = os.path.join(DATA, "klickmessung.yaml")
# Manuelle Provisions-Monatssummen (Abgeleitetes aus `data/provisionen/provisionen.csv`,
# geschrieben von `scripts/offline_import.py`). Die CSV selbst ist gitignored –
# versioniert wird nur das Aggregat, weil es keine Abrechnungs-Details enthält.
PROVISIONEN = os.path.join(DATA, "provisionen_aggregat.json")
# Eigene Provenienz-Datei des Provisions-Imports.
OFFLINE_META = os.path.join(DATA, "offline_import.meta.json")
PROV_STALE_MONATE = 2      # letzter befüllter Monat älter als 2 Monate ⇒ Hinweis
OUT_JSON = os.path.join(DATA, "revenue_funnel.json")
HISTORY = os.path.join(DATA, "revenue_funnel_history.jsonl")
REPORT = os.path.join(BLOG_DIR, "REVENUE-FUNNEL-REPORT.md")

TODAY = datetime.date.today()
STALE_DAYS = 14         # Import älter als zwei Wochen ⇒ Quelle „veraltet“
MAX_HISTORY = 260       # gut 5 Jahre Wochenläufe

SOURCES = (
    # (Schlüssel, menschenlesbarer Name, Daten-/Meta-Pfade, Behebung)
    ("offline", "Provisions-Tabelle (Offline-Import)", PROVISIONEN, OFFLINE_META,
     "Abrechnung eintragen (`npm run mess:vorlage` legt die Tabelle an, Schema: "
     "docs/ANLEITUNG-PROVISIONEN.md) und `npm run mess:import` ausführen"),
    ("clicks", "Affiliate-Klicks (eigener Klickzähler)", CLICKS, CLICKS_META,
     "Zähler-Worker einrichten, `aktiv: true` in `data/klickmessung.yaml` setzen und "
     "`python3 scripts/klick_import.py` ausführen "
     "(docs/ANLEITUNG-KLICKMESSUNG-OHNE-COOKIES.md)"),
)


def klickmessung_aktiv(config_path=None):
    """Betriebsschalter des eigenen Klickzählers (`data/klickmessung.yaml`,
    Sicherheitsaudit 14.10.2026, M-13). Gleiches Muster wie click_chain_guard.py
    und affiliate_shield.py: fehlt die Datei oder ist sie kaputt, gilt der
    Zähler als AUS (datensparsam) – und dann ist „keine Klicks“ keine Lücke,
    sondern eine Betriebsgrenze."""
    try:
        with open(config_path or KLICKMESSUNG, encoding="utf-8") as f:
            return re.search(r"(?m)^aktiv:\s*true\s*$", f.read()) is not None
    except OSError:
        return False


# ------------------------------------------------------------------ IO-Helfer

def _read_json(path, default=None):
    try:
        with open(path if os.path.isabs(path) else os.path.join(BLOG_DIR, path),
                  encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default


def _age_days(meta, keys=("written", "generated", "attempted", "stand")):
    """Alter einer Messung in Tagen (robust gegen Formatsuppe, None wenn unbekannt).

    `stand` ist der Zeitstempel der Meta des eigenen Klickzählers
    (klick_import.py), die übrigen Schlüssel die des Provisions-Imports."""
    if not isinstance(meta, dict):
        return None
    for k in keys:
        v = meta.get(k)
        if isinstance(v, str):
            try:
                return (TODAY - datetime.date.fromisoformat(v[:10])).days
            except ValueError:
                continue
    return None


def _month_age(jjjj_mm: str) -> int:
    """Monate zwischen `JJJJ-MM` und heute (0 = aktueller Monat). Wirft bei
    unplausiblem Format – der Aufrufer dokumentiert dann „unbekannt“ statt zu
    raten. Bewusst grob (30-Tage-Monate): Es geht um „nachtragen oder nicht“."""
    y, m = jjjj_mm.split("-")
    given = datetime.date(int(y), int(m), 1)
    if given > TODAY:
        raise ValueError("Zukunft")
    return (TODAY.year - given.year) * 12 + (TODAY.month - given.month)


def _source_state(data, meta):
    """→ (status, age_days). status: ok | alt | skipped | fehler | disabled | fehlt.

    Meta-Vokabular: `skipped`/`disabled` (allgemein) sowie `nicht_konfiguriert`
    und `fehler` aus klick_import.py. Eine Meta mit `ok` und leerer Datei ist
    eine MESSUNG (echte 0), kein Loch – deshalb zählt bei `ok` nur das Alter."""
    meta = meta if isinstance(meta, dict) else {}
    status = meta.get("status")
    if status in ("skipped", "disabled"):
        return status, _age_days(meta)
    if status == "nicht_konfiguriert":
        return "skipped", _age_days(meta)
    if status == "fehler":
        return "fehler", _age_days(meta)
    if status != "ok" and not data:
        return "fehlt", None
    age = _age_days(meta) if meta else (_age_days(data) if isinstance(data, dict) else None)
    if age is not None and age > STALE_DAYS:
        return "alt", age
    return "ok", age


# ------------------------------------------------------------------ Kaufnahe Seiten

def kaufnahe_paths(root=None):
    """Seiten, die direkt Geld verdienen können: jeder Artikel mit /go/-Link,
    jeder Pillar-Ratgeber und die Ratgeber-Zentrale (/pillar/ – dort sitzt die
    Spar-Matrix mit sechs Gateway-Buttons).

    Die Startseite ist bewusst NICHT dabei: sie führt zu den kaufnahen Seiten,
    verkauft aber nichts direkt.
    Deterministisch aus dem Content-Scan (keine Laufzeit-Abhängigkeit von
    Namenskonventionen einer Messquelle); die Layout-Plätze sind fix, weil ihre
    CTA-Verträge (pillar/list.html, render-link.html) bei jedem Build
    getestet werden (click_chain_guard.py + E2E)."""
    root = root or BLOG_DIR
    out = {"/pillar/"}
    for p in sorted(glob.glob(os.path.join(root, "content", "posts", "*", "index.md"))) + \
             sorted(glob.glob(os.path.join(root, "content", "posts", "*.md"))):
        try:
            body = open(p, encoding="utf-8").read()
        except OSError:
            continue
        if re.search(r"/go/[A-Za-z0-9_\-]+/?", body) or re.search(
                r"(tarifvergleich|einspartabelle)", body):
            slug = os.path.basename(os.path.dirname(p)) if os.path.basename(p) == "index.md" \
                else os.path.basename(p)[:-3]
            if slug and not slug.startswith("_"):
                out.add(f"/posts/{slug}/")
    for p in sorted(glob.glob(os.path.join(root, "content", "pillar", "*", "index.md"))):
        out.add(f"/pillar/{os.path.basename(os.path.dirname(p))}/")
    return out


def article_to_path(article):
    """`article`-Attribut („posts/<slug>/index.md“, „pillar/<k>/index.md“ – die
    Form von `data-klick-article` und der Zeilen in `klicks_eigen.json`) →
    Blog-Pfad. Leeres Ergebnis = Sonstiges."""
    a = str(article or "").strip().strip("/")
    if not a:
        return ""
    if a in ("posts", "pillar", "content", "_index"):
        # nackte Sektionsnamen sind keine Slugs (würde /pillar/posts/ erfinden)
        return "/pillar/" if a == "pillar" else ""
    if a in ("home", "pillar/_index"):
        return "/pillar/" if a == "pillar/_index" else "/"
    if a.startswith("posts/"):
        slug = a[len("posts/"):].removesuffix("/index.md").removesuffix(".md")
        slug = re.sub(r"/?_index$", "", slug)  # posts/x/_index.md → x
        return f"/posts/{slug}/" if slug and slug != "_index" else ""
    if a.startswith("pillar/"):
        seg = a[len("pillar/"):].removesuffix("/index.md").removesuffix(".md")
        return f"/pillar/{seg}/" if seg and seg != "_index" else "/pillar/"
    m = re.match(r"^([A-Za-z0-9_\-]+)$", a)  # roher SubID-Slug (Pillar-Name)
    return f"/pillar/{m.group(1)}/" if m else ""


# ------------------------------------------------------------------ Trichter

def _rate(num, den):
    """Prozentsatz oder None (unbekannt)."""
    if num is None or den is None or den <= 0:
        return None
    return round(100.0 * num / den, 2)


def _count(row):
    """Zähler einer Klick-Zeile; Müll (Text, negativ, None) zählt als 0 statt
    den Trichter abstürzen zu lassen – eine kaputte Zeile darf nie den Report
    der übrigen verhindern."""
    try:
        return max(0, int(float(row.get("count") or 0)))
    except (TypeError, ValueError, OverflowError):
        return 0


def _per_unit(revenue, clicks):
    if revenue is None or not clicks:
        return None
    return round(revenue / clicks, 2)


def fmt(v, kind="int"):
    if v is None:
        return "unbekannt"
    if kind == "int":
        return f"{int(v):,}".replace(",", ".")
    if kind == "pct":
        return f"{v:.2f} %".replace(".", ",")
    if kind == "eur":
        return f"{v:.2f} €".replace(".", ",")
    return f"{v:.4f}".replace(".", ",")


def compute(clicks_rows, paths, measured=None, manual_prov=None):
    """Reine Trichter-Rechnung (testbar, ohne Dateizugriff).

    `measured` = {clicks: bool}: „der Klickzähler hat erfolgreich geliefert“.
    Nur dann darf eine 0 als echte Null stehen – sonst gilt überall die
    Hausregel: nicht gemessen ⇒ unbekannt, nie eine Null.

    `manual_prov` = Monatsaggregate der Partnerabrechnungen (manuelle
    Provisions-Tabelle). Sie ist die einzige Provisionsquelle und wird überall
    als „provisionen-tabelle“ gekennzeichnet – eine Abrechnungs-
    summe ist kein Transaktionszähler und darf auch nicht wie einer
    aussehen (Monats-, nicht Fenster-Sicht)."""
    clicks_rows = [r for r in (clicks_rows or []) if isinstance(r, dict)]
    m = measured or {"clicks": bool(clicks_rows)}

    # Klicks je Pfad + gesamt (nur Affiliate-Ereignisse)
    aff = [r for r in clicks_rows if "affiliate_click" in str(r.get("event") or "affiliate_click")]
    clicks_total = sum(_count(r) for r in aff) if m.get("clicks") else None
    clicks_by_path = {}
    for r in aff:
        p = article_to_path(r.get("article"))
        if p:
            clicks_by_path[p] = clicks_by_path.get(p, 0) + _count(r)

    # Trichter-Kennzahlen starten als „unbekannt“ (None). Nur die Provisions-
    # Tabelle füllt sie – nie eine Null, die es nicht gibt.
    antraege = None
    confirmed = None
    declined = None
    pending = None
    revenue = None
    provision_bezahlt = None
    prov_quelle = None

    # Provisions-Tabelle (Partnerabrechnungen, Monatssummen): einzige Quelle für
    # Anträge, Abschlüsse, Stornos und Provision.
    mp = manual_prov if isinstance(manual_prov, dict) else {}
    ms = mp.get("summe") if isinstance(mp.get("summe"), dict) else {}
    prov_monats_alter = None
    if ms:
        abschl = int(ms.get("abschluesse") or 0)
        stornos = int(ms.get("stornos") or 0)
        antraege = abschl if abschl else 0
        confirmed = max(0, abschl - stornos)
        declined = stornos
        pending = 0
        rev_m = ms.get("provision_eur")
        if rev_m is not None:
            revenue = round(float(rev_m), 2)
            provision_bezahlt = revenue
        prov_quelle = "provisionen-tabelle"
        try:
            prov_monats_alter = _month_age(str(mp.get("letzter_monat") or ""))
        except (ValueError, TypeError):
            prov_monats_alter = None

    # Kennzahlen – None heißt „unbekannt“, das ist der ganze Witz.
    rates = {
        "klick_antrag": _rate(antraege, clicks_total),
        "antrag_abschluss": _rate(confirmed, antraege),
        "stornoquote": _rate(declined, (confirmed or 0) + (declined or 0) if prov_quelle else None),
        "epc": _per_unit(revenue, clicks_total),
    }

    # Klicks je kaufnahe Seite. Die Provision je Seite ist NICHT messbar: die
    # Tabelle liefert nur Monatssummen – eine Monatssumme einer Seite zu
    # buchen wäre erfunden und bleibt verboten (kein revenue-/epc-Feld).
    per_page = [{"path": p, "clicks": clicks_by_path[p]}
                for p in sorted(paths) if p in clicks_by_path]
    per_page.sort(key=lambda d: -(d.get("clicks") or 0))

    return {
        "generated": TODAY.isoformat(),
        "kaufnah_seiten": len(paths),
        "affiliate_klicks": clicks_total,
        "transaktionen": {"antraege": antraege, "pending": pending, "bestaetigt": confirmed,
                          "stornos": declined, "quelle": prov_quelle},
        "provision": {"gesamt": revenue, "bezahlt": provision_bezahlt,
                      "quelle": prov_quelle,
                      "monat": (mp.get("letzter_monat") if prov_quelle == "provisionen-tabelle"
                                else None),
                      "zeitbezug": ("monat" if prov_quelle == "provisionen-tabelle"
                                    else None),
                      "monats_alter": prov_monats_alter},
        "raten": rates,
        "seiten": per_page,
    }


def evaluate(sources):
    """→ gaps: welche Quellen sind Löcher, was kostet die Behebung?

    `ok` und `disabled` (bewusste Betriebsgrenze, siehe main) sind keine Lücke.
    Alles andere schon: eine Quelle, die liefern SOLL und es nicht tut."""
    gaps = []
    for _key, label, data_state, age in sources:
        if data_state in ("ok", "disabled"):
            continue
        why = {"fehlt": "noch nie importiert",
               "skipped": "Import übersprungen (Zugang oder Konfiguration fehlt)",
               "fehler": "letzter Import fehlgeschlagen",
               "alt": f"Import {age or '?'}d alt (Frist {STALE_DAYS}d)"}.get(data_state, data_state)
        gaps.append(f"{label}: {why}")
    return gaps


# ------------------------------------------------------------------ Report

def messbarkeit(src):
    """Geschäftliche Messabdeckung getrennt von der technischen Pipeline-Ampel.

    Eine bewusst deaktivierte Quelle bleibt kein technischer Fehler – sie ist
    aber auch keine gemessene Geschäftswirkung. Nur zwei frische Quellen
    (Affiliate-Klicks und bestätigte Partnerabrechnung) erlauben den Status
    ``vollstaendig``. So kann ein gesunder Import-Job nicht mehr wie ein
    erfolgreicher Affiliate-Funnel aussehen.
    """
    states = {key: state for key, _label, state, _age in src}
    required = ("clicks", "offline")
    measured = sum(states.get(key) == "ok" for key in required)
    stale = any(states.get(key) == "alt" for key in required)
    if measured == len(required):
        status = "vollstaendig"
        label = "VOLLSTÄNDIG GEMESSEN"
    elif stale:
        status = "veraltet"
        label = "VERALTET / UNVOLLSTÄNDIG"
    elif measured:
        status = "teilweise"
        label = "TEILWEISE GEMESSEN"
    else:
        status = "unbekannt"
        label = "UNBEKANNT – KEINE GESCHÄFTSMESSUNG"
    return {
        "status": status,
        "label": label,
        "gemessene_quellen": measured,
        "erforderliche_quellen": len(required),
        "abdeckung_prozent": round(100 * measured / len(required)),
    }


def quellen_text(src, offline_meta, clicks_meta=None):
    """Zeile im Report: WOHER kommen die Zahlen gerade? (Agentur-Standard: jede
    Kennzahl braucht ihre Quelle – eine Zahl ohne Herkunft ist ein Gerücht.)"""
    state = {k: st for k, _l, st, _a in src}
    teile = []
    if state.get("clicks") in ("ok", "alt"):
        stand = str((clicks_meta or {}).get("stand") or "unbekannt")[:10]
        teile.append(f"Klicks: eigener Zähler (`scripts/klick_import.py`, Stand {stand})")
    if state.get("offline") in ("ok", "alt"):
        stand = (offline_meta or {}).get("written") or "unbekannt"
        monate = (offline_meta or {}).get("provisionen_monate")
        extra = f", {monate} Monate" if isinstance(monate, int) else ""
        teile.append(f"Provision: Abrechnungstabelle (`scripts/offline_import.py`, Stand {stand}{extra})")
    if teile:
        return " · ".join(teile)
    return ("keine – derzeit liefert keine Quelle Zahlen (Grund: Datenqualität unten; "
            "Zahlen bleiben „unbekannt“, docs/UMSATZ-MESSUNG-PREMIUM.md)")


def render(f, gaps, fix_hints, wow=None, operating_boundaries=None, quellen=None,
           prov_monate=None, business_measurement=None):
    """Markdown-Wochenseite. Enthält die Markerzeile `Messlücken: N` und die
    Gesamt-Ampel – der Governance-Gate liest beides (kein Exit-Code-Raten)."""
    rate = f["raten"]
    tx = f["transaktionen"]
    rows = [
        ("Affiliate-Klicks", fmt(f["affiliate_klicks"])),
        ("Vermittelte Abschlüsse (alle Status)", fmt(tx["antraege"])),
        ("Klick → Antrag", fmt(rate["klick_antrag"], "pct")),
        ("Antrag → bestätigter Abschluss", fmt(rate["antrag_abschluss"], "pct")),
        ("Stornoquote (declined ÷ abgeschlossene)", fmt(rate["stornoquote"], "pct")),
        ("Provision (gesamt)", fmt(f["provision"]["gesamt"], "eur")),
        ("Provision bezahlt", fmt(f["provision"]["bezahlt"], "eur")),
        ("EPC (Einnahmen pro Affiliate-Klick)", fmt(rate["epc"], "eur")),
    ]
    # Monats-Sicht überlagert Klick-Sicht ⇒ zwei Zeilen mischen zwei Bezüge.
    # Ehrliche Beschriftung statt stiller Rundung: Sternchen + Fußnote.
    mischt = f["provision"].get("quelle") == "provisionen-tabelle"
    if mischt:
        stand = f["provision"].get("monat") or "Stand unbekannt"
        rows = [(k + (" *" if k in ("Klick → Antrag",
                                    "EPC (Einnahmen pro Affiliate-Klick)") else ""), v)
                for k, v in rows]
        rows = [(k.replace("Provision (gesamt)", f"Provision (Abrechnungstabelle, Stand {stand})")
                 .replace("Provision bezahlt",
                          "Provision bezahlt (lt. Abrechnungstabelle)"), v)
                for k, v in rows]
    ampel = "GREEN" if not gaps else "AMBER"
    business_measurement = business_measurement or messbarkeit([])
    out = ["# 📈 Umsatz-Funnel – Klick → Antrag → Provision",
           f"**Stand:** {f['generated']} · **Pipeline-Ampel:** **{ampel}** · "
           f"**Messlücken: {len(gaps)}**",
           f"**Geschäftsmessbarkeit:** **{business_measurement['label']}** "
           f"({business_measurement['gemessene_quellen']}/"
           f"{business_measurement['erforderliche_quellen']} Quellen; "
           f"{business_measurement['abdeckung_prozent']} % Abdeckung).",
           "",
           "## 🚦 Gesamt-Ampel: **" + ampel + "**",
           "",
           "_Die Pipeline-Ampel bewertet den technischen Betrieb. Sie ist "
           "ausdrücklich kein Umsatz- oder Erfolgssignal; dafür gilt die "
           "Geschäftsmessbarkeit oben._",
           "",
           "| Kennzahl | Wert |",
           "|---|---|"]
    out += [f"| {k} | {v} |" for k, v in rows]
    if mischt:
        out += ["", "_* Diese beiden Zeilen mischen zwei Zeitbezüge: Klicks aus dem "
                "Zähler, Abschlüsse und Provision aus der **abgerechneten "
                "Monatssicht** der Provisions-Tabelle. Sie taugen als "
                "Größenordnung, nicht als Wochenvergleich._", ""]
    if quellen:
        out += [f"**Quellen:** {quellen}", ""]
    if prov_monate:
        out += ["## 🧾 Abrechnungstabelle (Provision je Monat)", "",
                "| Monat | Partner | Abschlüsse | Stornos | Provision |", "|---|---|---|---|---|"]
        for mrow in prov_monate[:12]:
            partner = ", ".join(str(x) for x in (mrow.get("partner") or [])) or "unbenannt"
            out.append(f"| {mrow.get('monat') or 'unbekannt'} | {partner} | "
                       f"{fmt(mrow.get('abschluesse'))} | {fmt(mrow.get('stornos'))} | "
                       f"{fmt(mrow.get('provision_eur'), 'eur')} |")
        out += ["", "_Monatssicht der abgerechneten Provisionen – deshalb kein "
                "Wochenvergleich und keine Tageskurve. Quelle: "
                "`data/provisionen/provisionen.csv` (intern, gitignored)._", ""]
    if wow:
        out += ["", "## 🔁 Vorwoche (Woche für Woche)", "",
                "| Kennzahl | letzte Woche | Δ |", "|---|---|---|"]
        out += [f"| {k} | {prev} | {d} |" for k, prev, d in wow]
    if f["seiten"]:
        out += ["", "## 🧭 Klicks je kaufnahe Seite (Top 15)", "",
                "| Seite | Klicks |",
                "|---|---|"]
        for p in f["seiten"][:15]:
            out.append(f"| `{p['path']}` | {fmt(p['clicks'])} |")
        out += ["", "_Provision je Seite ist nicht messbar: die Abrechnungstabelle "
                "kennt nur Monatssummen._"]
    out += ["", "## 🧾 Datenqualität der Messkette", ""]
    if gaps or operating_boundaries:
        out += ["| Level | Code | Befund |", "|---|---|---|"]
        if gaps:
            out += [f"| AMBER | funnel_gap | {g} |" for g in gaps]
        if operating_boundaries:
            out += [f"| INFO | operating_boundary | {b} |" for b in operating_boundaries]
        if gaps:
            out += ["", "Behebung (Reihenfolge = Wirkung):"]
            out += [f"- {h}" for h in fix_hints]
    else:
        out += ["_keine Befunde_ – alle Quellen gemessen und frisch (≤ 14 Tage)."]
    out += ["", "## 🎯 Empfehlung (Agentur-Modus)", "",
            "1. **Reichweite nur auf bewiesenen Trichter:** EPC < 0,10 € auf einer",
            "   kaufnahen Seite ⇒ CTA/Anker überarbeiten, BEVOR Traffic gekauft wird.",
            "2. **Storno > 15 %** ⇒ Partner-Ziel prüfen (falsches Produkt versprochen?",
            "   Intent-Gate IW3) – Stornos sind verlorene Margen, keine Petitesse.",
            "3. **Antrag → Abschluss < 40 %** ⇒ Erwartungsmanagement am Link prüfen",
            "   (Tooltip/Anker müssen halten, was sie versprechen – siehe Intent-Wache).",
            "",
            "_Erzeugt von `scripts/revenue_funnel.py`; Quellen der Zahlen: eigener",
            "Klickzähler + Provisions-Tabelle. Besucherzahlen gibt es bewusst nicht",
            "(kein Reichweiten-Tracking). „unbekannt“ heißt: Messkette noch nicht",
            "befüllt – siehe Datenqualität oben, nicht „nichts verdient“._",
            ""]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ History + WoW

def _history_row(f):
    r = f["raten"]
    return {"date": f["generated"],
            "clicks": f["affiliate_klicks"],
            "antraege": f["transaktionen"]["antraege"],
            "confirmed": f["transaktionen"]["bestaetigt"],
            "storno_pct": r["stornoquote"], "revenue": f["provision"]["gesamt"],
            "epc": r["epc"]}


def _prev_metrics():
    """Letzte abgeschlossene Woche aus der History (für Δ), None wenn keine."""
    try:
        lines = [l for l in open(HISTORY, encoding="utf-8").read().splitlines() if l.strip()]
    except OSError:
        return None
    for line in reversed(lines):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if d.get("date") != TODAY.isoformat():
            return d
    return None


def _wow(cur, prev):
    """Zeilen (Kennzahl, Vorwoche, Δ) – Δ bleibt None, wenn eine Seite fehlt.

    Ältere History-Zeilen tragen noch Spalten, die es nicht mehr gibt
    (Besuchs-Kennzahlen): gelesen wird nur, was die Tabelle unten nennt."""
    if not prev:
        return []
    out = []
    for label, key, kind in (("Affiliate-Klicks", "clicks", "int"),
                             ("Anträge", "antraege", "int"),
                             ("Stornoquote (%)", "storno_pct", "pct"),
                             ("Provision (€)", "revenue", "eur"),
                             ("EPC (€)", "epc", "eur")):
        a, b = cur.get(key), prev.get(key)
        diff = round(a - b, 2) if isinstance(a, (int, float)) and isinstance(b, (int, float)) else None
        delta = "unbekannt" if diff is None else ("+" if diff >= 0 else "") + fmt(diff, kind)
        out.append((label, fmt(b, kind), delta))
    return out


def lage(clicks_rows, clicks_meta, prov_doc, offline_meta, zaehler_aktiv):
    """Messlage der beiden Quellen → (src, measured, operating_boundaries).

    Reine Funktion (ohne Dateizugriff), damit Selbsttest und Unit-Tests dieselbe
    Entscheidung prüfen wie der echte Lauf:

      · Provisions-Tabelle noch NIE befüllt  → Betriebsgrenze (INFO), keine Lücke:
        ein manueller, freiwilliger Weg meldet sein Nichtvorhandensein nicht
        als Störung. Ist sie befüllt, aber der Import veraltet, ist es eine Lücke.
      · Klickzähler AUS (`aktiv: false`)     → Betriebsgrenze (INFO). Auch alte
        Zeilen zählen dann NICHT: ausgeschaltet heißt nicht gemessen.
      · Klickzähler AN und liefert nicht      → Lücke (AMBER, `funnel_gap`)."""
    st_prov, age_prov = _source_state(prov_doc or {}, offline_meta or {})
    boundaries = []
    if st_prov == "fehlt":
        st_prov = "disabled"
        boundaries.append(
            "Provisions-Tabelle noch nicht befüllt – Anträge, Abschlüsse, Provision "
            "und EPC bleiben „unbekannt“ (Abrechnung eintragen: `npm run mess:vorlage`, "
            "danach `npm run mess:import`)")
    if zaehler_aktiv:
        st_clk, age_clk = _source_state(clicks_rows, clicks_meta or {})
        measured_clicks = (clicks_meta or {}).get("status") == "ok"
    else:
        st_clk, age_clk, measured_clicks = "disabled", None, False
        boundaries.append(
            "Klickzähler aus (`aktiv: false` in `data/klickmessung.yaml`) – Klicks, "
            "Klick → Antrag und EPC bleiben „unbekannt“ "
            "(Einschalten: docs/ANLEITUNG-KLICKMESSUNG-OHNE-COOKIES.md)")
    src = [("offline", SOURCES[0][1], st_prov, age_prov),
           ("clicks", SOURCES[1][1], st_clk, age_clk)]
    return src, {"clicks": measured_clicks}, boundaries


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    print_only = "--print" in argv
    paths = kaufnahe_paths()
    clicks_rows = _read_json(CLICKS, []) or []
    clicks_meta = _read_json(CLICKS_META, {}) or {}
    prov_doc = _read_json(PROVISIONEN, {}) or {}
    offline_meta = _read_json(OFFLINE_META, {}) or {}

    src, measured, operating_boundaries = lage(
        clicks_rows, clicks_meta, prov_doc, offline_meta, klickmessung_aktiv())
    gaps = evaluate(src)
    source_fixes = {k: SOURCES[i][4] for i, k in enumerate(("offline", "clicks"))}
    fixes = [source_fixes[k] for k, _l, state, _a in src if state not in ("ok", "disabled")]
    f = compute(clicks_rows if measured["clicks"] else [], paths, measured=measured,
                manual_prov=prov_doc)
    # Info-Grenze (keine Lücke): Abrechnungstabelle zu lange nicht nachgetragen.
    alter = f["provision"].get("monats_alter")
    if f["provision"].get("quelle") == "provisionen-tabelle" \
            and isinstance(alter, int) and alter > PROV_STALE_MONATE:
        operating_boundaries.append(
            f"Provisions-Tabelle: letzter befüllter Monat "
            f"{f['provision'].get('monat')} ist {alter} Monate her – "
            f"abrechnen und nachtragen (`data/provisionen/provisionen.csv`) "
            f"und `npm run mess:import`)")
    f["quellen"] = [{"quelle": k, "status": state, "alter_tage": age}
                   for k, _l, state, age in src]

    prev = _prev_metrics()
    wow = _wow(_history_row(f), prev)
    visibility = messbarkeit(src)
    body = render(f, gaps, fixes, wow, operating_boundaries=operating_boundaries,
                  quellen=quellen_text(src, offline_meta, clicks_meta),
                  prov_monate=(prov_doc.get("monate") if isinstance(prov_doc, dict) else None),
                  business_measurement=visibility)

    if print_only:
        print(body)
    else:
        _write_atomic(REPORT, body)
        _write_atomic(OUT_JSON, json.dumps({**f, "messluecken": len(gaps),
                                            "geschaeftsmessbarkeit": visibility,
                                            "quellen": f["quellen"]},
                                           ensure_ascii=False, indent=2) + "\n")
        try:
            os.makedirs(DATA, exist_ok=True)
            row = json.dumps(_history_row(f), ensure_ascii=False)
            lines = []
            if os.path.exists(HISTORY):
                lines = [l for l in open(HISTORY, encoding="utf-8").read().splitlines()
                         if l.strip()]
            # Idempotenz pro Tag: Mehrfachläufe am selben Tag überschreiben die
            # letzte Zeile – sonst zählt die Woche doppelt und Δ wird Unsinn.
            if lines:
                try:
                    same_day = json.loads(lines[-1]).get("date") == TODAY.isoformat()
                except json.JSONDecodeError:
                    same_day = False
                lines = lines[:-1] if same_day else lines
            lines.append(row)
            _write_atomic(HISTORY, "\n".join(lines[-MAX_HISTORY:]) + "\n")
        except (OSError, json.JSONDecodeError):
            pass
        print(f"📈 Umsatz-Funnel: {fmt(f['affiliate_klicks'])} Klicks · "
              f"{fmt(f['provision']['gesamt'], 'eur')} Provision · "
              f"EPC {fmt(f['raten']['epc'], 'eur')} · Messlücken: {len(gaps)}")
    try:
        from audit_log import log_event
        def _zustand(key, fallback):
            return next((st for k, _l, st, _a in src if k == key), fallback)
        log_event(module="revenue_funnel", action="report",
                  input={"clicks": _zustand("clicks", "unknown"),
                         "offline": _zustand("offline", "unknown")},
                  output={"gaps": len(gaps), "clicks": f["affiliate_klicks"],
                          "revenue": f["provision"]["gesamt"]}, status="ok")
    except Exception:  # noqa: BLE001
        pass
    print(f"\nMesslücken: {len(gaps)}")
    return 1 if gaps else 0


def _write_atomic(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


# ------------------------------------------------------------------ Selftest

def _selftest():
    """Deterministisch – und damit uhrfest: alle Datums-Fixtures werden RELATIV
    zum Testdatum gebaut (`vor()` / `monat_rel()`), absolut eingestempelt wird
    nur, was ein ferner Vergangenheitstag bleiben soll. Der Beweis läuft in
    der CI: `python3 scripts/selftest_clock.py --trap scripts/revenue_funnel.py
    --offset 1461` (Verbrannt am 10.10.2026: ein auf 2030-01 eingefrorener
    Zukunfts-Monat wurde vier Jahre später zum Vergangenheits-Monat)."""
    import tempfile

    def vor(tage):
        return (TODAY - datetime.timedelta(days=tage)).isoformat()

    def monat_rel(rueckwaerts=0):
        """JJJJ-MM, `rueckwaerts` Monate vor dem aktuellen Monat."""
        m = TODAY.year * 12 + (TODAY.month - 1) - rueckwaerts
        return f"{m // 12:04d}-{m % 12 + 1:02d}"

    failures = []
    # --- Artikel-Attribut → Pfad (die Brücke Klick↔Seite muss sitzen)
    for art, want in (("posts/2026-08-16-gas-anbieter-wechseln/index.md",
                       "/posts/2026-08-16-gas-anbieter-wechseln/"),
                      ("pillar/strom-sparen/index.md", "/pillar/strom-sparen/"),
                      ("strom-sparen", "/pillar/strom-sparen/"),
                      ("home", "/"), ("pillar/_index", "/pillar/"),
                      ("", ""), ("posts/", ""), ("unsinn/tief/hier", "")):
        got = article_to_path(art)
        if got != want:
            failures.append(f"article_to_path({art!r}) = {got!r}, erwartet {want!r}")
    # --- Kaufnahe-Menge: Zentrale + Ratgeber drin, Startseite draußen
    k = kaufnahe_paths()
    if "/pillar/" not in k:
        failures.append("Ratgeber-Zentrale fehlt in der kaufnahen Menge")
    if "/" in k:
        failures.append("Startseite gehört nicht in die kaufnahen Seiten (kein direkter Verkauf)")
    if not any(p.startswith("/pillar/") and p != "/pillar/" for p in k):
        failures.append("Pillar-Ratgeber fehlen in der kaufnahen Menge")
    # --- Trichter-Synthese: alle Kennzahlen mit Absichtswerten
    clicks = [{"event": "affiliate_click", "slug": "gas",
               "article": "posts/2026-08-16-gas-anbieter-wechseln/index.md",
               "pillar": "", "count": 40},
              {"event": "cta_click", "slug": "home-strom", "article": "home", "count": 25}]
    # Provisions-Tabelle als einzige Quelle: 20 Abschlüsse, 5 Stornos, 210 € Provision.
    mp1 = {"summe": {"abschluesse": 20, "stornos": 5, "provision_eur": 210.0},
           "monate": [f"{TODAY:%Y-%m}"], "letzter_monat": f"{TODAY:%Y-%m}", "partner": ["CHECK24"]}
    f = compute(clicks, {"/pillar/", "/posts/2026-08-16-gas-anbieter-wechseln/",
                         "/pillar/strom-sparen/"}, manual_prov=mp1)
    r = f["raten"]
    if f["affiliate_klicks"] != 40:
        failures.append(f"fremdes Ereignis (cta_click) verunreinigt den Affiliate-Zähler: {f['affiliate_klicks']}")
    if f["transaktionen"]["antraege"] != 20:
        failures.append(f"Anträge gesamt: {f['transaktionen']['antraege']}")
    if abs(r["klick_antrag"] - 50.0) > 0.01:
        failures.append(f"Klick→Antrag: {r['klick_antrag']}")
    if abs(r["antrag_abschluss"] - 75.0) > 0.01:
        failures.append(f"Antrag→Abschluss: {r['antrag_abschluss']}")
    if abs(r["stornoquote"] - 25.0) > 0.01:
        failures.append(f"Stornoquote: {r['stornoquote']}")
    if abs(r["epc"] - 5.25) > 0.01:
        failures.append(f"EPC: {r['epc']}")
    top = f["seiten"][0]
    if (top["path"] != "/posts/2026-08-16-gas-anbieter-wechseln/" or top["clicks"] != 40
            or "revenue" in top or "epc" in top):
        failures.append(f"Seiten-Trichter Top (Provision je Seite wäre erfunden): {top}")
    # Keine Besuchs-Kennzahlen mehr – ohne Quelle wären sie für immer „unbekannt“.
    verboten = {"outbound_ctr", "rev_per_100_visits", "rev_per_100_kaufnah"}
    if verboten & set(r) or "views" in f or "platzierungen" in f:
        failures.append("Kennzahl ohne Quelle (Besuche/Platzierungen) ist wieder im Trichter")
    # --- „unbekannt“ ≠ 0: leere Quellen dürfen nirgends Nullen gebären
    empty = compute([], {"/", "/pillar/"}, measured={"clicks": False})
    for name, v in list(empty["raten"].items()) + [("klicks", empty["affiliate_klicks"]),
                                                   ("prov", empty["provision"]["gesamt"]),
                                                   ("antraege", empty["transaktionen"]["antraege"])]:
        if v is not None:
            failures.append(f"ohne Quellen erfindet der Trichter {name}={v} (soll unbekannt)")
    if "unbekannt" not in render(empty, ["Klicks: fehlt", "Provisionen: fehlt"],
                                 ["Quelle einrichten"], []):
        failures.append("Report versteckt das Wort „unbekannt“")
    gemessen_leer = compute([], {"/pillar/"}, measured={"clicks": True})
    if gemessen_leer["affiliate_klicks"] != 0 or gemessen_leer["transaktionen"]["antraege"] is not None:
        failures.append("gemessen-und-leer muss echte 0 Klicks, aber unbekannte Anträge liefern")
    # --- Ampel + Marker + Befundtabelle für den Governance-Gate
    rep = render(empty, ["a", "b"], ["d"], [])
    if "Messlücken: 2" not in rep or "**AMBER**" not in rep:
        failures.append("Report-Linie `Messlücken: N` / Ampel fehlt (Gate wäre blind)")
    if "funnel_gap" not in rep:
        failures.append("Lücken stehen nicht als AMBER/funnel_gap-Befunde da – "
                        "der Gate-Filter (ACTIONABLE_AMBER) läuft ins Leere")
    rep_ok = render(f, [], [], [])
    if "Messlücken: 0" not in rep_ok or "GREEN" not in rep_ok:
        failures.append("grüner Trichter meldet nicht grün")
    # --- Betriebsgrenze: INFO, keine Lücke, Ampel bleibt grün
    rep_bound = render(empty, [], [], operating_boundaries=["Klickzähler aus"])
    if "Messlücken: 0" not in rep_bound or "GREEN" not in rep_bound or "operating_boundary" not in rep_bound:
        failures.append("Betriebsgrenze (operating_boundary) wird nicht grün als INFO formatiert")
    if evaluate([("offline", "P", "disabled", None), ("clicks", "K", "disabled", None)]) != []:
        failures.append("bewusst begrenzte Quellen (disabled) dürfen nicht als Lücke gemeldet werden")
    # --- Messlage: Betriebsschalter statt stiller Annahmen --------------------
    s, m_, b_ = lage([], {}, {}, {}, zaehler_aktiv=False)
    if evaluate(s) != [] or m_["clicks"] or len(b_) != 2:
        failures.append(f"Zähler aus + leere Tabelle: erwartet GREEN mit 2 Betriebsgrenzen, bekam {s} {b_}")
    s, m_, b_ = lage([{"count": 9}], {"status": "ok", "stand": vor(0) + "T06:00:00Z"},
                     {}, {}, zaehler_aktiv=False)
    if m_["clicks"]:
        failures.append("ausgeschalteter Zähler: alte Zeilen dürfen nicht als Messung zählen")
    s, m_, b_ = lage([], {}, {}, {}, zaehler_aktiv=True)
    if len(evaluate(s)) != 1 or "Klickzähler" not in evaluate(s)[0] or m_["clicks"]:
        failures.append("Zähler AN aber ohne Lieferung muss genau eine Lücke melden")
    s, m_, b_ = lage([], {"status": "nicht_konfiguriert", "stand": vor(0) + "T06:00:00Z"},
                     {}, {}, zaehler_aktiv=True)
    if len(evaluate(s)) != 1 or "übersprungen" not in evaluate(s)[0]:
        failures.append("nicht_konfiguriert bei laufendem Zähler muss als Lücke (skipped) erscheinen")
    s, m_, b_ = lage([], {"status": "fehler", "stand": vor(0) + "T06:00:00Z"},
                     {}, {}, zaehler_aktiv=True)
    if len(evaluate(s)) != 1 or "fehlgeschlagen" not in evaluate(s)[0]:
        failures.append("Import-Fehler bei laufendem Zähler muss als Lücke erscheinen")
    s, m_, b_ = lage([], {"status": "ok", "stand": vor(0) + "T06:00:00Z"},
                     {}, {}, zaehler_aktiv=True)
    if evaluate(s) != [] or not m_["clicks"]:
        failures.append("frischer Import mit leerer Zeilenliste ist eine echte 0, keine Lücke")
    s, m_, b_ = lage([], {"status": "ok", "stand": vor(STALE_DAYS + 5) + "T06:00:00Z"},
                     {}, {}, zaehler_aktiv=True)
    if len(evaluate(s)) != 1 or f"{STALE_DAYS + 5}d" not in evaluate(s)[0]:
        failures.append("veralteter Klick-Import muss als Lücke mit Alter erscheinen")
    s, m_, b_ = lage([], {}, {"summe": {"abschluesse": 1}},
                     {"status": "ok", "written": vor(STALE_DAYS + 1)}, zaehler_aktiv=False)
    if len(evaluate(s)) != 1 or "Provisions-Tabelle" not in evaluate(s)[0]:
        failures.append("befüllte, aber veraltete Provisions-Tabelle muss eine Lücke bleiben")
    # --- Schalter-Datei: aktiv: true / false / fehlt -------------------------
    with tempfile.TemporaryDirectory() as td:
        pfad = os.path.join(td, "klickmessung.yaml")
        for text, soll in (("aktiv: true\n", True), ("aktiv: false\n", False),
                           ("# aktiv: true\naktiv: false\n", False), ("", False)):
            with open(pfad, "w", encoding="utf-8") as fh:
                fh.write(text)
            if klickmessung_aktiv(pfad) is not soll:
                failures.append(f"klickmessung_aktiv({text!r}) ≠ {soll}")
        if klickmessung_aktiv(os.path.join(td, "fehlt.yaml")) is not False:
            failures.append("fehlende Schalter-Datei muss AUS heißen (datensparsam)")
    # --- Provisions-Tabelle: zweite Quelle, gleiche Hausregeln ---------------
    AB_RECHNUNG = monat_rel(1)           # relativ: der zuletzt abgerechnete Monat
    mp = {"summe": {"abschluesse": 4, "stornos": 1, "provision_eur": 67.5},
          "monate": [AB_RECHNUNG], "letzter_monat": AB_RECHNUNG, "partner": ["CHECK24"]}
    fm = compute([{"event": "affiliate_click", "count": 12, "article": "pillar/strom-sparen/index.md"}],
                 {"/pillar/strom-sparen/"}, measured={"clicks": True}, manual_prov=mp)
    if fm["provision"]["gesamt"] != 67.5 or fm["provision"]["quelle"] != "provisionen-tabelle":
        failures.append(f"Provisionstabelle wird nicht genutzt: {fm['provision']}")
    if fm["provision"]["zeitbezug"] != "monat" or fm["transaktionen"]["antraege"] != 4:
        failures.append(f"Zeitbezug/Anträge der Provisionstabelle falsch: {fm['provision']}")
    if fm["transaktionen"]["stornos"] != 1 or fm["transaktionen"]["bestaetigt"] != 3:
        failures.append(f"Storno/Abschluss-Zerlegung fehlt: {fm['transaktionen']}")
    if "revenue" in fm["seiten"][0]:
        failures.append("Monatssumme wird auf eine Seite gebucht (erfunden) – verboten")
    if abs(fm["raten"]["epc"] - 67.5 / 12) > 0.01:
        failures.append(f"EPC mit Tabellenzahlen: {fm['raten']['epc']}")
    rep_m = render(fm, [], [], [],
                   quellen=f"Provision: Abrechnungstabelle (`scripts/offline_import.py`, Stand {vor(0)})",
                   prov_monate=[dict(mp, monat=AB_RECHNUNG)])
    if AB_RECHNUNG not in rep_m:
        failures.append(f"Monatsmarke {AB_RECHNUNG} steht nicht im Report – "
                        f"die Monatsbasis wäre ohne Datum nicht prüfbar")
    if "Abrechnungstabelle (Provision je Monat)" not in rep_m:
        failures.append("Provisions-Tabelle fehlt im Report – Monatsbasis ist nicht belegbar")
    if "**Quellen:** Provision: Abrechnungstabelle" not in rep_m:
        failures.append("Report verschweigt die Herkunft der Zahlen")
    if rep_m.count(" * |") != 2 or "_* Diese beiden Zeilen mischen zwei Zeitbezüge" not in rep_m:
        failures.append("gemischter Zeitbezug wird nicht mit Sternchen + Fußnote markiert")
    for zustand_clk in ("disabled", "skipped", "fehler", "fehlt"):
        q_leer = quellen_text([("offline", "P", "disabled", None), ("clicks", "K", zustand_clk, None)], {}, {})
        if not q_leer.startswith("keine –") or "aus " in q_leer:
            failures.append(f"ohne jede Quelle muss der Report „keine“ ohne falschen Grund nennen ({zustand_clk}): {q_leer}")
    q_beide = quellen_text([("offline", "P", "ok", 0), ("clicks", "K", "ok", 0)],
                           {"written": vor(0), "provisionen_monate": 3},
                           {"stand": vor(0) + "T06:00:00Z"})
    if "eigener Zähler" not in q_beide or "Abrechnungstabelle" not in q_beide or "3 Monate" not in q_beide:
        failures.append(f"Herkunftszeile unvollständig: {q_beide}")
    if _month_age(TODAY.strftime("%Y-%m")) != 0:
        failures.append("_month_age(aktueller Monat) ≠ 0")
    n = TODAY.year * 12 + TODAY.month          # der Monat NACH heute
    try:
        _month_age(f"{n // 12:04d}-{n % 12 + 1:02d}")
        failures.append("Zukunfts-Monat muss werfen (nichts erfinden)")
    except ValueError:
        pass
    if _month_age(monat_rel(1)) != 1 or _month_age(monat_rel(PROV_STALE_MONATE)) != PROV_STALE_MONATE:
        failures.append("_month_age zählt Monate falsch (Relative-Fixture-Vertrag)")
    try:
        # Zweite Zukunfts-Probe, bewusst WEIT vorn (10 Jahre) und relativ:
        # Hier stand bis 10.10.2026 ein eingefrorenes "2030-01" – unter der
        # 1461-Tage-Uhrprobe des Selbsttest-Runners war das ein VERGANGENHEITS-
        # Monat, der Selbsttest wurde datumsabhängig rot. Ein absolutes Datum
        # in einer Zukunfts-Zusicherung ist immer eine Zeitbombe.
        _month_age(monat_rel(-120))
        failures.append("Ferner Zukunfts-Monat muss werfen (nichts erfinden)")
    except ValueError:
        pass
    # --- Datenqualitäts-Logik
    if evaluate([("offline", "P", "ok", 0), ("clicks", "K", "ok", 2)]) != []:
        failures.append("frische Quellen werden als Lücke gemeldet")
    g = evaluate([("offline", "P", "alt", 30), ("clicks", "K", "skipped", 1)])
    if len(g) != 2 or "30d" not in " ".join(g):
        failures.append(f"Lückentext unvollständig: {g}")
    # --- Alter aus Meta (beide Meta-Dialekte) + History-Altlast
    if _age_days({"written": TODAY.isoformat()}) != 0 or _age_days({"stand": vor(3) + "T01:02:03Z"}) != 3:
        failures.append("_age_days kennt `written` und `stand` nicht")
    if _age_days([1, 2]) is not None or _age_days(None) is not None:
        failures.append("_age_days muss bei Nicht-Dict None liefern (nicht crashen)")
    if _source_state([], {"status": "skipped", "attempted": "2026-01-01"})[0] != "skipped":
        failures.append("skipped-Meta muss als skipped durchkommen (nie als „fehlt“)")
    if _source_state({"pages": []}, {"generated": "2026-01-01"})[0] != "alt":
        failures.append("uralt-Bestand muss „alt“ heißen")
    alt_prev = {"date": vor(7), "views_total": 5, "ctr_pct": 1.0, "clicks": 3, "revenue": 10.0}
    wow_zeilen = _wow({"clicks": 5, "antraege": None, "storno_pct": None, "revenue": 12.0, "epc": None}, alt_prev)
    if [z[0] for z in wow_zeilen] != ["Affiliate-Klicks", "Anträge", "Stornoquote (%)", "Provision (€)", "EPC (€)"]:
        failures.append(f"Vorwochen-Tabelle trägt Altlasten oder fehlt: {[z[0] for z in wow_zeilen]}")
    if wow_zeilen and wow_zeilen[0][2] != "+2":
        failures.append(f"Δ Klicks falsch gerechnet: {wow_zeilen[0]}")
    # --- Zahlenformat
    if fmt(None) != "unbekannt" or fmt(1234) != "1.234" or fmt(12.5, "eur") != "12,50 €":
        failures.append("fmt-Formatierung (1.234 / 12,50 € / unbekannt)")
    # --- Müll crashet nie
    for bad in (None, {}, [], "apfelsaft", [1, None, "x"], [{"count": "viel"}]):
        try:
            compute(bad, set(), measured={"clicks": True}, manual_prov=bad)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"Müll {bad!r} wirft {exc.__class__.__name__}")
    if failures:
        print("❌ REVENUE-FUNNEL-SELFTEST FEHLGESCHLAGEN:")
        for x in failures:
            print("   -", x)
        return 2
    print("✅ REVENUE-FUNNEL-SELFTEST bestanden (Trichter-Rechnung, unbekannt≠0, "
          "Ampel+Marker für den Gate, Betriebsgrenze vs. Lücke, Provisions-Tabelle, "
          "Robustheit).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
