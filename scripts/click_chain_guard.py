#!/usr/bin/env python3
"""
CLICK-CHAIN-GUARD – beweist die Messkette: CTA → Event → Gateway → SubID → Partner

WARUM: „Keine Klicks" kann zwei Dinge heißen: es klickt niemand – ODER die
Messung ist irgendwo kaputt. Die Kette ist lang und jede Stufe kann still
sterben:
  1. CTA am Seitenende/Anker      → muss data-umami-event="affiliate_click"
                                    + data-umami-event-slug + -placement
                                    + ?subid= im href tragen
  2. Umami-Script geladen         → sonst feuert kein einziges Event
  3. /go/-Gateway                → muss die SubID an die Partner-URL anhängen
  4. Import (API)                 → Daten müssen im Repo ankommen (Funnel prüft das)
  5. Partner-Attribution          → Transaktionen müssen eine ClickRef tragen
Dieser Guard prüft Stufe 1–3 am GEMACHTEN Build (und optional live), Stufe 5 an
den importierten Awin-Daten. Fundklasse: 02.09.2026 – Shortcode-CTAs ohne Event,
hier jetzt für ALLE Seiten (Start, /pillar/, Artikel) als Vertrag.

SELBSTTEST-KLICK (SOP Frank, manuell – kein Roboter klickt beim Partner):
  1. `python3 scripts/click_chain_guard.py --test-page` zeigt den exakten Klickpfad.
  2. Frank klickt auf einer echten Seite einen /go/-Button (DA ist der Testklick).
  3. ≤ 24 h später muss der nächste Importlauf den Klick in `data/umami_clicks.json`
     zeigen (sonst: Meldung des Guards/Issues), und im Awin-Dashboard muss die
     Click-Reference = Seiten-Slug auftauchen (Reports → Click References).
  4. NIEMALS selbst einen Antrag abschließen (Eigenabschluss = Programmtod).
     Ein Klick ist erlaubt und üblich; eine Conversion vom eigenen Netz ist es nicht.

AUSGABE:
  stdout + optional `CLICK-CHAIN-REPORT.md` (root, gitignored, vom Gate gelesen)
  mit Befundtabelle (`| AMBER | chain_gap | … |`), Gesamt-Ampel und der
  Markerzeile `Messlücken: N` – dasselbe Protokoll wie der Revenue-Funnel.

Nutzung:
  python3 scripts/click_chain_guard.py                 # public/ prüfen
  python3 scripts/click_chain_guard.py --public public/ --selftest
  python3 scripts/click_chain_guard.py --live https://franksfinanzcheck.de
  python3 scripts/click_chain_guard.py --test-page      # SOP-Ausgabe
  python3 scripts/click_chain_guard.py --report CLICK-CHAIN-REPORT.md

Exit: 0 = Kette dicht, 1 = Messlücke gefunden, 2 = Hausfehler/Selbsttest.
"""
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

TODAY = datetime.date.today()
ANCHOR_RE = re.compile(r"<a\b[^>]*>", re.I | re.S)
ATTR_RE = re.compile(r"([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*(\"([^\"]*)\"|'([^']*)')", re.I)
GO_HREF_RE = re.compile(r"/go/([A-Za-z0-9_\-]+)/?")

# Seiten, die den vollen CTA-Vertrag tragen müssen (Platzierung = Report-Label).
KEY_PAGES = {
    "index.html": "Startseite",
    "pillar/index.html": "Ratgeber-Zentrale",
}


def _attrs(anchor_html):
    out = {}
    for m in ATTR_RE.finditer(anchor_html):
        key = m.group(1).lower()
        out[key] = m.group(3) if m.group(3) is not None else (m.group(4) or "")
    return out


def scan_page(html, label):
    """→ [(label, problem)] für alle /go/-Anker einer Seite.

    Vertragsanker (rel=…sponsored…) MÜSSEN tragen:
      data-umami-event="affiliate_click", data-umami-event-slug (nicht leer),
      data-umami-event-placement (nicht leer – sonst ist der Klick im Funnel
      keiner Stelle zuordenbar), ?subid=… bzw. &subid=… im href.
    Rohe Partnerlinks (a.check24.net / partner-versicherung.de direkt im
    Dokument) sind ein Leck: sie umgehen Gateway UND Messung.
    """
    problems = []
    for m in ANCHOR_RE.finditer(html):
        attrs = _attrs(m.group(0))
        href = (attrs.get("href") or "").replace("&amp;", "&")
        if re.match(r"https?://(a\.check24\.net|a\.partner-versicherung\.de)", href, re.I):
            problems.append((label, f"roher Partnerlink umgeht Gateway+Messung: {href[:70]}"))
            continue
        gm = GO_HREF_RE.search(href)
        if not gm:
            continue
        rel = (attrs.get("rel") or "").lower()
        if "sponsored" not in rel:
            continue  # interne /go/-Nav-Links (z. B. Sitemap-Vorschau) ohne CTA-Pflicht
        if attrs.get("data-umami-event") != "affiliate_click":
            problems.append((label, f"/go/{gm.group(1)}/ ohne data-umami-event=affiliate_click "
                                     f"(Klick unsichtbar für die Umsatzmessung)"))
        if not (attrs.get("data-umami-event-slug") or "").strip():
            problems.append((label, f"/go/{gm.group(1)}/ ohne data-umami-event-slug "
                                     f"(Ziel-Klick nicht zuordenbar)"))
        if not re.search(r"[?&]subid=", href):
            problems.append((label, f"/go/{gm.group(1)}/ ohne ?subid= "
                                     f"(Awin sieht den Klick, aber nicht die Quelle)"))
        if not (attrs.get("data-umami-event-placement") or "").strip():
            problems.append((label, f"/go/{gm.group(1)}/ ohne data-umami-event-placement "
                                     f"(Klick im Funnel keiner Stelle zuordenbar)"))
    return problems


def walk_site(root):
    """Alle relevanten Inhaltsseiten des Builds: home, /pillar/ (Übersicht +
    Ratgeber), Artikel. Gateways unter <root>/go/ werden separat geprüft."""
    pages = []
    for rel, label in KEY_PAGES.items():
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            pages.append((p, label))
    # Artikel-Indexseiten (ein Scan pro Ordner, tiefensicher genug für Hugo)
    for base in ("posts", "pillar"):
        d = os.path.join(root, base)
        if not os.path.isdir(d):
            continue
        for entry in sorted(os.listdir(d)):
            p = os.path.join(d, entry, "index.html")
            if os.path.isfile(p):
                pages.append((p, f"{base}/{entry}"))
    return pages


def read(path):
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            return f.read()
    except OSError:
        return ""


def check_gateway(root, key):
    """Das /go/-Gateway muss die SubID per Skript an die Partner-URL hängen."""
    p = os.path.join(root, "go", key, "index.html")
    if not os.path.isfile(p):
        return f"/go/{key}/ fehlt im Build (Klick ins Leere = verlorener Umsatz)"
    html = read(p)
    if "subid" not in html:
        return f"/go/{key}/ reicht die SubID nicht an den Partner weiter (Attribution tot)"
    if not re.search(r"http-equiv=[\"']?refresh", html, re.I):
        return f"/go/{key}/ leitet nicht weiter (kein meta refresh)"
    return ""


def check_umami_script(root):
    home = read(os.path.join(root, "index.html"))
    if not home:
        return "keine Startseite im Build – Seite leer?"
    if "umami" not in home.lower():
        return ("im Build der Startseite fehlt das Umami-Script "
                "(hugo.toml [params.umami] / Consent-Gate prüfen) – "
                "ohne Script gemessene Klicks IMMER null")
    return ""


# ------------------------------------------------------------------ Awin-Seite

def check_awin_coverage():
    """Wie viele importierten Transaktionen tragen eine Click-Reference (SubID)?

    Quelle: data/awin_provisions.json (aggregiert, dsGVO-OK). Ohne Import-Datei:
    Hinweis statt Lücke (der Funnel meldet die Quelle schon als Lücke – hier soll
    der Guard nur die Attribution bewerten, wenn Daten da sind)."""
    path = os.path.join(BLOG_DIR, "data", "awin_provisions.json")
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    articles = doc.get("articles") or {}
    total_tx = int(doc.get("transactions") or 0)
    if total_tx <= 0:
        return None
    matched = sum(1 for v in articles.values() if str(v.get("subid") or "").strip())
    unmatched = int(doc.get("unmatched") or 0)
    coverage = round(100.0 * matched / max(1, matched + unmatched), 1)
    problems = []
    if unmatched > 0:
        problems.append(f"{unmatched} Transaktion(en) ohne bekannte SubID – "
                        f"Awin-Empfänger verliert die Artikel-Zuordnung (coverage {coverage} %)")
    return {"transactions": total_tx, "coverage_pct": coverage, "problems": problems}


# ------------------------------------------------------------------ Live-Variante

def fetch_live(base, paths, timeout=15):
    out = []
    for rel, label in paths:
        url = urllib.parse.urljoin(base.rstrip("/") + "/", rel)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "franksfin-chain/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out.append((url, label, r.read(2_000_000).decode("utf-8", "ignore")))
        except (urllib.error.URLError, TimeoutError, OSError):
            out.append((url, label, ""))   # leer => Caller meldet die Unerreichbarkeit
    return out


# ------------------------------------------------------------------ Hauptlauf

def run(public_dir, report_path="", do_live=None, require_events=False):
    gaps = []
    notes = []
    checked = 0
    not_measured = False
    if do_live:
        for url, label, html in fetch_live(do_live, list(KEY_PAGES.items())):
            checked += 1
            if not html:
                gaps.append(f"LIVE {label}: nicht erreichbar – Messkette nicht beweisbar")
                continue
            for lab, problem in scan_page(html, f"LIVE {label}"):
                gaps.append(problem)
    else:
        if not os.path.isdir(public_dir):
            msg = (f"kein Build unter {os.path.relpath(public_dir, BLOG_DIR)}/ "
                   "– Guard kann die Kette nicht beweisen (erst `hugo` bauen); "
                   "Gemessene Anker: 0 – noch keine daten")
            if require_events:
                gaps.append(msg)
            else:
                notes.append(msg)
            not_measured = True
            pages = []
        else:
            home_html = read(os.path.join(public_dir, "index.html"))
            umami_gap = check_umami_script(public_dir)
            if umami_gap:
                gaps.append(umami_gap)
            pages = walk_site(public_dir)
            for path, label in pages:
                checked += 1
                for lab, problem in scan_page(read(path), label):
                    gaps.append(problem)
            # Gateway-Drift: jedes im Content registrierte /go/-Ziel muss
            # SubID durchreichen (Register = check24_links.yaml)
            try:
                keys = gateway_keys()
            except Exception:  # noqa: BLE001 – Register optional lesbar
                keys = set()
            for key in sorted(keys):
                problem = check_gateway(public_dir, key)
                if problem:
                    gaps.append(problem)
            checked += len(keys)
    cov = check_awin_coverage()
    if cov and cov["problems"]:
        gaps += cov["problems"]
    elif cov:
        notes.append(f"Awin-ClickRef-Abdeckung {cov['coverage_pct']} % "
                     f"bei {cov['transactions']} Transaktionen")
    else:
        notes.append("Awin-Attribution noch nicht bewertbar (kein Transaktions-Import) – "
                     "Secrets `AWIN_API_TOKEN`+`AWIN_PUBLISHER_ID` setzen oder CSV liefern")

    ampel = "AMBER" if gaps else ("NICHT GEMESSEN" if not_measured else "GREEN")
    lines = ["# 🔗 Klick-Messkette – Guard (Build → Umami → Gateway → Awin)",
             f"**Stand:** {TODAY.isoformat()} · **Geprüfte Anker-Seiten:** {checked} · "
             f"**Ampel:** **{ampel}** · **Messlücken: {len(gaps)}**",
             "",
             "## 🚦 Gesamt-Ampel: **" + ampel + "**",
             ""]
    if gaps:
        lines += ["| Level | Code | Befund |", "|---|---|---|"]
        lines += [f"| AMBER | chain_gap | {g[:150]} |" for g in gaps]
        lines += ["", "## 🛠️ Behebung", "",
                  "Die Lücken gehören an die Quelle der Kette (Render-Hook,",
                  "`affiliate_anchor_attrs.html`, Layout-CTA oder Awin-Zugang).",
                  "Nach der Reparatur reicht der nächste Build – dieser Guard und",
                  "der Wochen-Funnel melden dann grün."]
    elif not_measured:
        lines.append("⚪ Kette NICHT gemessen – kein Build unter "
                     f"{os.path.relpath(public_dir, BLOG_DIR)}/ gefunden.")
    else:
        lines.append("🟢 Kette dicht: jeder Affiliate-CTA trägt Event+SubID, jedes "
                     "Gateway reicht die SubID durch, das Umami-Script ist drin.")
    if notes:
        lines += ["", "## ℹ️ Hinweise", ""] + [f"- {n}" for n in notes]
    lines += ["", "## 🧪 Eigen-Testklick (SOP – maximal ein Klick, NIE eine Anmeldung)",
              "",
              "1. Live-Artikel öffnen (z. B. letzter Gastbeitrag) und EINEN",
              "   /go/-Button klicken – der Klick erzeugt die Click-Reference im",
              "   Awin-Dashboard (Reports → Click References, bis 24 h Verzögerung).",
              "2. Beim nächsten Importlauf (revenue-import.yml) muss der Klick in",
              "   `data/umami_clicks.json` auftauchen.",
              "3. Beides da? ⇒ Kette bewiesen. Sonst Issue-Kommentar des Guards",
              "   abarbeiten (Stufe zeigen, die fehlt).",
              "4. Kein Eigenabschluss! Transaktionen aus dem eigenen Netz werden",
              "   storniert und können das Programm kosten.",
              "",
              f"_Erzeugt von `scripts/click_chain_guard.py`._", ""]
    body = "\n".join(lines) + "\n"
    print(body)
    if report_path:
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(body)
        except OSError:
            pass
    return len(gaps)


def gateway_keys():
    """Schlüssel aus dem Affiliate-Register (check24_links.yaml) – ohne PyYAML-
    Pflicht (Notfall-Regex wie im Affiliate-Shield)."""
    path = os.path.join(BLOG_DIR, "scripts", "check24_links.yaml")
    try:
        import yaml
        data = yaml.safe_load(open(path, encoding="utf-8")) or {}
        return set((data.get("links") or {}).keys())
    except Exception:  # noqa: BLE001
        txt = read(path)
        block = txt.split("links:", 1)[-1]
        return set(re.findall(r"^\s{2}([A-Za-z0-9_\-]+):", block, re.M))


def test_page_sop():
    print("Testklick-Anleitung (manuell, vom Betreiber – nie automatisiert):")
    print("  1. Live-Artikel öffnen, einen /go/-CTA klicken (rel=sponsored, SubID aktiv).")
    print("  2. Danach: python3 scripts/revenue_funnel.py --print  → Klickzähler > 0?")
    print("  3. Awin: Reports → Click References → Slug der Seite suchen.")
    print("  4. KEINE Anmeldung, KEIN Antrag – nur der Klick ist der Test.")
    return 0


# ------------------------------------------------------------------ Selftest

def _selftest():
    failures = []
    good = ('<a href="/go/strom/?subid=posts-x" rel="sponsored nofollow noopener" '
            'target="_blank" data-umami-event="affiliate_click" '
            'data-umami-event-slug="strom" data-umami-event-placement="artikel">Strom ↔</a>')
    no_sub = '<a href="/go/gas/" rel="sponsored nofollow noopener" data-umami-event="affiliate_click" data-umami-event-slug="gas">Gas</a>'
    no_event = ('<a href="/go/dsl/?subid=y" rel="sponsored nofollow noopener" '
                'data-umami-event="click" data-umami-event-slug="dsl">DSL</a>')
    no_platz = ('<a href="/go/heiz/?subid=z" rel="sponsored nofollow noopener" '
                'data-umami-event="affiliate_click" data-umami-event-slug="heiz">Heiz</a>')
    raw_link = '<a href="https://a.check24.net/misc/click.php?pid=1" rel="sponsored">direkt</a>'
    internal = '<a href="/go/allgemein/">nur Navigation</a>'
    probs = scan_page(good + no_sub + no_event + raw_link + internal, "t")
    text = " | ".join(p for _l, p in probs)
    if "ohne ?subid=" not in text:
        failures.append("fehlende SubID am CTA bleibt unerkannt")
    if "ohne data-umami-event=affiliate_click" not in text:
        failures.append("fehlendes Event bleibt unerkannt")
    if "roher Partnerlink" not in text:
        failures.append("roher Partnerlink (Gateway umgangen) bleibt unerkannt")
    if not any("ohne data-umami-event-placement" in p for _l, p in scan_page(no_platz, "t")):
        failures.append("fehlende Platzierung am CTA bleibt unerkannt")
    if scan_page(good, "t"):
        failures.append("sauberer Anker wird gemeldet (False Positive)")
    if scan_page(internal, "t"):
        failures.append("interner Link ohne CTA-Vertrag wird gemeldet (False Positive)")
    # --- Attribut-Robustheit: einfache Anführungszeichen, Zeilenumbrüche im Tag
    weird = ('<a\n  href="/go/x/?a=1&amp;subid=slug" rel=\'sponsored nofollow noopener\'\n'
             '  data-umami-event="affiliate_click" data-umami-event-slug="x"'
             ' data-umami-event-placement="pillar">y</a>')
    if scan_page(weird, "t"):
        failures.append("mehrzeiliger sauberer Anker falsch gemeldet")
    # --- Gateway-Check gegen Kunst-Baum
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "go", "strom"), exist_ok=True)
        with open(os.path.join(td, "go", "strom", "index.html"), "w", encoding="utf-8") as f:
            f.write("<meta http-equiv=\"refresh\" content=\"0; url=x\">subid= ok")
        if check_gateway(td, "strom"):
            failures.append("korrektes Gateway wird beanstandet")
        os.makedirs(os.path.join(td, "go", "gas"), exist_ok=True)
        with open(os.path.join(td, "go", "gas", "index.html"), "w", encoding="utf-8") as f:
            f.write("<p>vergessen</p>")
        if "SubID" not in check_gateway(td, "gas"):
            failures.append("Gateway ohne SubID-Förderung bleibt unentdeckt")
        if "Build" not in check_gateway(td, "kies"):
            failures.append("Gateway ohne Datei bleibt unentdeckt")
        # Umami-Script
        if not check_umami_script(td):
            failures.append("fehlendes Umami-Script bleibt unentdeckt")
        with open(os.path.join(td, "index.html"), "w", encoding="utf-8") as f:
            f.write("<script src=\"https://cloud.umami.is/script.js\"></script>")
        if check_umami_script(td):
            failures.append("Script vorhanden wird als Lücke gemeldet")
        # walk_site findet home + Sektionen
        os.makedirs(os.path.join(td, "pillar"), exist_ok=True)
        with open(os.path.join(td, "pillar", "index.html"), "w") as f:
            f.write(good)
        pages = dict((os.path.relpath(p, td), l) for p, l in walk_site(td))
        if "pillar/index.html" not in pages or "index.html" not in pages:
            failures.append(f"walk_site verliert Seiten: {pages}")
    if failures:
        print("❌ CLICK-CHAIN-GUARD-SELFTEST FEHLGESCHLAGEN:")
        for x in failures:
            print("   -", x)
        return 2
    print("✅ CLICK-CHAIN-GUARD-SELFTEST bestanden (CTA-Vertrag, rohe Partnerlinks, "
          "Gateway-Drift, Umami-Script, Seiten-Findung).")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    if "--test-page" in argv:
        return test_page_sop()

    def val(flag, default=None):
        if flag in argv:
            i = argv.index(flag) + 1
            if i < len(argv):
                return argv[i]
        return default

    public_dir = val("--public") or os.path.join(BLOG_DIR, "public")
    if not os.path.isabs(public_dir):
        public_dir = os.path.join(BLOG_DIR, public_dir)
    report = val("--report", "")
    live = val("--live", "")
    try:
        n = run(public_dir, report_path=report or "", do_live=live or None,
                require_events="--require-green" in argv)
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Klick-Ketten-Guard intern fehlgeschlagen: {exc.__class__.__name__}: {exc}")
        return 2
    try:
        from audit_log import log_event
        log_event(module="click_chain_guard", action="check",
                  input={"public": public_dir, "live": live},
                  output={"gaps": n}, status="ok" if n == 0 else "error")
    except Exception:  # noqa: BLE001
        pass
    return 1 if n else 0


if __name__ == "__main__":
    sys.exit(main())
