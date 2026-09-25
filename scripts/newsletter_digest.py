#!/usr/bin/env python3
"""newsletter_digest.py – Capture-Wache + Digest im Eigenbetrieb.

Warum dieses Skript existiert
-----------------------------
Der Blog versendet dienstags und freitags EINE Mail mit ausgewählten
Artikeln der letzten Tage. Dieses Skript ist der Sammler und Entscheider:
  * WACHE  (--check): meldet laut, ob der Anmeldeweg, die Landingpage,
               der Rechtstext, der Footer-CTA und der Versand-Workflow
               zusammenspielen – oder warum der Newsletter inert ist.
  * BUILD  (--build): liest neue Artikel, baut die Ausgabe über das
               Studio (Marke, Blöcke, Betreff, Preheader) und schreibt
               den Versandstatus (Duplikatsschutz).
  * VERSAND (--send): übergibt die Ausgabe an scripts/newsletter_versand.py –
               seit 24.09.2026 IM EIGENBETRIEB statt bei Brevo:

SEIT 24.09.2026: BREVO IST RAUS
-----------------------------
Der Versand lief über Brevos Kampagnen-API (Kampagne anlegen, sendTest,
sendNow, Kontakte nachtragen). Drei Reparatur-Reports in einer Woche
bewiesen, dass jede Änderung von Brevos API- und Kontosemantik den
Versand brach: Testkampagnen mit leeren Listen, Testmails nur an
„bestehende Kontakte“, Teilversand-Zustände, die niemand sauber lesen
konnte. Deshalb gilt jetzt:

  Adressen   Cloudflare Worker (KV) – nie in diesem (öffentlichen) Repo.
             Der Worker ist der Anmeldeweg (Formular-Endpunkt) UND die
             Abonnenten-Liste. Der Ablauf des Double-Opt-In steht in
             docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md.
  Versand    scripts/newsletter_versand.py (NUR Standardbibliothek):
             Resend (Default) oder SMTP, pro Empfänger eine Mail,
             Rate-Limit, Journal mit Adress-HASHES, Bounce-Handling.
  Test       --test-adresse ist jetzt trivial: die Mail geht direkt an
             die Adresse – es existiert kein „Kontakt muss erst im Konto
             anlegt werden“-Zustand mehr, weil es kein fremdes Konto gibt.

Verriegelung (bleibt wie gehabt, nur der Transport unter dem Boden):
  1. Ohne Worker-Konfiguration (NEWSLETTER_WORKER_BASE/EXPORT_KEY) kein
     Listen-Versand – fail-closed, mit Klickweg.
  2. LISTEN-Versand nur über NEWSLETTER_SEND=ja (Cron/live/planmaessig)
     ODER --live; ein --test-adresse trifft NUR die eingegebenen Adressen.
  3. QA (scripts/newsletter_qa.py) vor JEDEM Versand, auch Test.
  4. Kadenz-Vertrag (Dienstag/Freitag, max. 2/Woche, Versandpause).
  5. Duplikatsschutz: Versandstatus in data/newsletter_state.json;
     TEILVERSAND markiert nichts als gesendet – der nächste Lauf
     wiederholt, und zwar NUR an unversendete Empfänger (Hash-Abgleich
     über state["letzte_ausgabe"]["versendet"]).
  6. HARTER HALT: ein Versand, dessen Ergebnis unbelegbar ist, setzt
     state["versand_unklar"] – der nächste Listen-Versand bleibt stehen,
     bis ein Mensch den Zustand aufgelöst hat (aufheben: Schlüssel löschen).

Nur Standardbibliothek – der Versand-Workflow installiert bewusst nichts.

Nutzung:
    python3 scripts/newsletter_digest.py --check [--strict-inert] [--json]
    python3 scripts/newsletter_digest.py --build --days 7 [--out DIR]
    python3 scripts/newsletter_digest.py --build --send --live
    python3 scripts/newsletter_digest.py --build --send --test-adresse a@b.de
    python3 scripts/newsletter_digest.py --selftest

Exit: 0 = ok · 1 = Befund/Teilversand · 2 = Fehler
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.parse

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import newsletter_studio as studio      # noqa: E402  (Marke, Blöcke, Layout – eine Quelle)
import newsletter_schedule as schedule  # noqa: E402  (Dienstag/Freitag-Vertrag)
import newsletter_qa as qa              # noqa: E402  (Vor-Versand-Prüfung)
import newsletter_versand as versand    # noqa: E402  (Resend/SMTP/dry-run, Journal)

GRUND_URL = getattr(studio, "GRUND_URL", "https://franksfinanzcheck.de")
STATE_REL = os.path.join("data", "newsletter_state.json")
LANDING_REL = os.path.join("content", "newsletter", "index.md")
SHORTCODE_REL = os.path.join("layouts", "shortcodes", "newsletter_form.html")
FOOTER_REL = os.path.join("layouts", "_partials", "extend_footer.html")
WORKFLOW_REL = os.path.join(".github", "workflows", "newsletter-daily.yml")
WORKFLOW_LIFE_REL = os.path.join(".github", "workflows", "newsletter-lifecycle.yml")
ERLAUBTE_HOSTS = ("franksfinanzcheck.de", "workers.dev")
FELDNAME = "email"
EMAIL_MUSTER = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,63}$")
TEST_ADRESSEN_MAX = 10


# ------------------------------------------------------------------ Grundbausteine
def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def params(root: str) -> dict:
    """Newsletter-Parameter aus hugo.toml (Insel-Parser wie im Studio –
    kein Hugo-Build nötig). Leere Werte = „nicht gesetzt“ (JSON gewinnt)."""
    toml = _read(os.path.join(root, "hugo.toml"))
    def _wert(name: str) -> str:
        m = re.search(r'(?m)^\s*' + name + r'\s*=\s*"([^"]*)"', toml)
        return (m.group(1).strip() if m else "")
    return {"newsletterFormAction": _wert("newsletterFormAction"),
            "newsletterFormUrl": _wert("newsletterFormUrl"),
            "newsletterPromise": _wert("newsletterPromise")}


def live_artikel(root: str, seit: datetime.date | None, bis: datetime.date | None = None) -> list[dict]:
    out = []
    for idx in sorted(glob.glob(os.path.join(root, "content", "posts", "*", "index.md"))):
        text = _read(idx)
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if not m:
            continue
        # `draft: true` ist das Einverständnis, hier zu liegen; alles andere ist
        # Live-Bestand und darf in eine Mail an Abonnenten.
        if re.search(r"(?m)^draft:\s*true\s*$", m.group(1)):
            continue
        d = re.search(r"(?m)^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", m.group(1) if m else text)
        if not d:
            continue
        datum = datetime.date.fromisoformat(d.group(1))
        if seit and datum < seit:
            continue
        if bis and datum > bis:
            continue
        if datum > datetime.date.today():
            continue          # buildFuture=false: was nicht gebaut wird, wirbt nicht

        def feld(key: str) -> str:
            mm = re.search(r'(?m)^' + key + r':\s*["\']?(.*?)["\']?\s*$',
                           (m.group(1) if m else ""), re.S)
            return re.sub(r"\s+", " ", mm.group(1)).strip() if mm else ""

        slug = os.path.basename(os.path.dirname(idx))
        out.append({"slug": slug, "datum": datum.isoformat(),
                    "titel": feld("title") or slug.replace("-", " ").capitalize(),
                    "beschreibung": feld("description"),
                    "url": feld("url") or f"/posts/{slug}/",
                    "path": os.path.relpath(idx, root),
                    "pillar": feld("pillar")})
    return sorted(out, key=lambda a: a["datum"], reverse=True)


def zustand_konfig(root: str) -> tuple[str, int, int]:
    """(Datei, Betreff-Verlauf, Artikel-Verlauf) aus `zustand` im Studio-JSON.

    Der Block war bisher Dekoration: die Länge saß als `-12` im Code, der Pfad als
    Konstante. Jetzt gilt, was in der Datei steht – „ein Zustand, eine Datei" ist
    erst dann wahr, wenn beide Seiten dieselbe lesen. Die Konstanten bleiben
    Default, damit ein Checkout ohne Studio-JSON genau so weiterläuft.
    """
    try:
        z = studio.konfiguration(root, streng=False).get("zustand", {}) or {}
    except SystemExit:                    # kaputtes JSON: Wache meldet das, hier nicht sterben
        z = {}
    pfad = (str(z.get("datei") or "") or STATE_REL).strip()
    def _zahl(schlüssel, default):
        try:
            return max(1, int(z.get(schlüssel, default)))
        except (TypeError, ValueError):
            return default
    return pfad, _zahl("betreff_historie", 12), _zahl("artikel_historie", 400)


def lade_state(root: str) -> dict:
    pfad, _, _ = zustand_konfig(root)
    try:
        return json.loads(_read(os.path.join(root, pfad)) or "{}")
    except json.JSONDecodeError:
        return {}


def speichere_state(root: str, state: dict) -> None:
    pfad, _, _ = zustand_konfig(root)
    pfad = os.path.join(root, pfad)
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    tmp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=os.path.dirname(pfad),
                                         prefix=".newsletter-", delete=False) as fh:
            tmp = fh.name
            json.dump(state, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, pfad)
    finally:
        if tmp and os.path.exists(tmp):
            os.unlink(tmp)


def assert_worktree(root: str) -> None:
    try:
        top = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001
        top = ""
    if os.path.realpath(top or "") != os.path.realpath(root):
        raise SystemExit("❌ newsletter_digest: Zielverzeichnis ist kein Git-Worktree – "
                         "Schreibzugriff verweigert (Schutz vor Selbsttest-Unfällen).")


DS_REL = os.path.join("content", "datenschutz", "index.md")


def _ds_laden(pub: str, root: str) -> tuple[str, str]:
    """Den Rechtstext laden: gebautes HTML, sonst Fallback auf die Markdown-Quelle.

    → (text, herkunft) mit herkunft „html", „quelle" oder „fehlend".
    Der Fallback schließt den stillen Freispruch: ohne Hugo-Build (Sandbox,
    Check vor dem ersten Build) war die Zeichenkette leer – 0 geprüfte
    Zeichen, 0 Funde, grün. Ausgefallen ist nicht bestanden: wenn beides
    fehlt, meldet die Wache `ds-fehlt`, statt im Leerlauf grün zu leuchten.
    """
    ds = _read(os.path.join(pub, "datenschutz", "index.html"))
    if ds.strip():
        return ds, "html"
    qu = _read(os.path.join(root, DS_REL))
    if qu.strip():
        return qu, "quelle"
    return "", "fehlend"


def _ds_abschnitt(ds: str, herkunft: str) -> str | None:
    """Den Newsletter-Abschnitt aus dem Rechtstext herausschneiden.

    → None, wenn keine Überschrift den Abschnitt nennt („fehlt"), sonst den
    Abschnitts-Text – der auch leer sein kann („halbfertig"). Die beiden
    Zustände sind verschiedene Befunde: aus einem fehlenden Rechtstext und
    einem halbfertigen darf nicht derselbe Fund werden.
    """
    if herkunft == "html":
        heads = list(re.finditer(r"(?i)<h([1-3])(?:\s[^>]*)?>(.*?)</h\1\s*>", ds))
        for m in heads:
            if "newsletter" not in m.group(2).lower():
                continue
            stufe = int(m.group(1))
            nach = ds[m.end():]
            m2 = re.search(r"(?i)<h[1-" + str(stufe) + r"](?=[\s>])", nach)
            return nach[: m2.start()] if m2 else nach
        return None
    zeilen = ds.splitlines()
    start, stufe = None, 0
    for i, zeile in enumerate(zeilen):
        m = re.match(r"^(#{1,4})\s+(.*)$", zeile)
        if m and "newsletter" in m.group(2).lower():
            start, stufe = i + 1, len(m.group(1))
            break
    if start is None:
        return None
    for j in range(start, len(zeilen)):
        m = re.match(r"^(#{1,4})\s", zeilen[j])
        if m and len(m.group(1)) <= stufe:
            return "\n".join(zeilen[start:j])
    return "\n".join(zeilen[start:])


def _platzhalter(abschnitt: str | None) -> list[str]:
    """Vorlagen-Reste: Klammern im Abschnitts-Text, ausgenommen Markdown-Links.

    Die Vorlage (docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md) verlangt: keine
    Klammer darf im Live-Text übrig bleiben. Im gebauten HTML sind
    Markdown-Links <a>-Tags, dort ist jede Klammer ein Rest; in der Quelle
    ist „[Text](Ziel)" der legale Träger – nur „[Text]" ohne Ziel ist ein
    ungefüllter Pflichtwert.
    """
    if not abschnitt:
        return []
    return re.findall(r"\[([^\[\]]+)\](?!\()", abschnitt)


def _platzhalter_meldung(platz: list[str]) -> str:
    einzig = sorted(set(platz))
    stuecke = ", ".join(f"„{p}“" for p in einzig[:5])
    mehr = f" (+{len(einzig) - 5} weitere)" if len(einzig) > 5 else ""
    return ("der Newsletter-Rechtstext enthält Vorlagen-Reste in Klammern: "
            + stuecke + mehr + " – keine Klammer darf im Live-Text übrig bleiben "
            "(Vorlage: docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md)")


# -------------------------------------------------------------------------- --check
CTA_MARKUP_RE = re.compile(
    "<(?:div|section|aside|footer)\\b[^>]*newsletter-footer")


def _cta_im_footer(html: str) -> bool:
    return bool(CTA_MARKUP_RE.search(html or ""))


def pruefe_capture(root: str, offentlich: str = "") -> tuple[list, list, str]:
    """→ (Funde, Hinweise, Zustand: inert|aktiv|kaputt)"""
    funde: list = []
    note: list = []
    p = params(root)
    action, url = p["newsletterFormAction"], p["newsletterFormUrl"]
    pub = offentlich or os.path.join(root, "public")
    seite = _read(os.path.join(pub, "newsletter", "index.html"))
    footer = _read(os.path.join(pub, "index.html"))

    ds, ds_herkunft = _ds_laden(pub, root)
    ds_abschnitt = _ds_abschnitt(ds, ds_herkunft)
    ds_widerspruch = bool(re.search("(?i)(derzeit|zurzeit|aktuell) keinen newsletter"
                                    "|bietet[^.]{0,60}keinen newsletter", ds))
    ds_platz = _platzhalter(ds_abschnitt)

    if not action and not url:
        if ds_herkunft == "fehlend":
            funde.append(("N7", "die Datenschutzerklärung existiert weder gebaut "
                                "(public/) noch als Quelle (content/) – die Prüfung "
                                "ist ausgefallen, nicht bestanden", "ds-fehlt"))
        if ds_widerspruch:
            note.append(("N7", "die Datenschutzerklärung erklärt ausdrücklich, es "
                               "gäbe keinen Newsletter – bei Freischaltung des "
                               "Formulars wird daraus ein Widerspruch; vorher "
                               "ersetzen (docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md)",
                        "ds-widerspruch-vorstudie"))
        if ds_platz:
            funde.append(("N7", _platzhalter_meldung(ds_platz), "ds-platzhalter"))
        wirbt = []
        for f in glob.glob(os.path.join(pub, "**", "index.html"), recursive=True):
            if os.path.relpath(f, pub).replace(os.sep, "/").startswith("newsletter"):
                continue
            if re.search(r"Newsletter abonnieren|Newsletter-Anmeldung", _read(f)):
                wirbt.append(f)
        if wirbt or _cta_im_footer(footer):
            funde.append(("N1", "die Site wirbt für einen Newsletter, ohne dass ein "
                                "Anmeldeweg konfiguriert ist – toter Link für "
                                "Interessenten", "config-widerspruch"))
        note.append(("N0", "kein Anmeldeweg konfiguriert (params.newsletterFormUrl/"
                            "newsletterFormAction leer) – Capture INERT, es geht "
                            "keine Adresse ein", "inert"))
        return funde, note, "inert"

    if action:
        u = urllib.parse.urlsplit(action)
        if u.scheme != "https":
            funde.append(("N2", f"Formular-Endpunkt ist {u.scheme or 'http'} – "
                                "E-Mail-Adressen dürfen niemals unverschlüsselt "
                                "übertragen werden", "form-http"))
        if u.hostname and not any(u.hostname.endswith(h) for h in ERLAUBTE_HOSTS):
            note.append(("N2", f"Formular-Endpunkt {u.hostname} liegt außerhalb der "
                               f"erlaubten Hosts ({', '.join(ERLAUBTE_HOSTS)}) – "
                               "prüfen, ob das der eigene Worker ist",
                        "form-host"))
        if re.search(r"(TODO|BEISPIEL|example|<|\{\{)", action, re.I):
            funde.append(("N2", "Formular-Endpunkt enthält Platzhalter-Müll", "form-platzhalter"))
    if url:
        u = urllib.parse.urlsplit(url)
        if u.scheme != "http":
            pass
        if u.scheme != "https":
            funde.append(("N3", f"gehostetes Formular über {u.scheme or 'http'}", "url-http"))
        if url.rstrip("/") in ("", "/", GRUND_URL):
            funde.append(("N3", "newsletterFormUrl zeigt auf die Site selbst – "
                                "Button und Zielseite sind dasselbe, die Anmeldung "
                                "verpufft im Kreis", "url-selbstbezug"))

    # Shortcode und Seite müssen zueinander passen
    sc = _read(os.path.join(root, SHORTCODE_REL))
    if not sc:
        funde.append(("N4", f"fehlend: {SHORTCODE_REL} – ohne Shortcode zeigt die "
                            "Landingpage kein Feld", "shortcode-fehlt"))
    elif action:
        literal = f'name="{FELDNAME}"' in sc
        aus_konfig = re.search(r'name="\{\{[^}]*feld_email', sc) is not None
        if not (literal or aus_konfig):
            funde.append(("N4", f"Inline-Formular POSTet ohne Feld `{FELDNAME}` – "
                                "der Newsletter-Worker liest die Adresse aus genau "
                                "diesem Namen (literal oder via capture.feld_email)",
                        "feldname"))
    if not seite:
        funde.append(("N5", "Landingpage /newsletter/ ist nicht gebaut – Inhalt "
                            "fehlt oder Build veraltet", "landingpage-fehlt"))
    else:
        for marke, grund, code in (
                ("Double-Opt", "kein Double-Opt-In-Hinweis – ohne den ist die "
                 "Anmeldung nach DSGVO unzulässig beworben", "doi-fehlt"),
                ("/datenschutz/", "kein Link zu den Datenschutzhinweisen an der "
                 "Anmeldestelle – ohne den Verweis ist die Einwilligung nicht "
                 "informiert", "datenschutz-link")):
            if marke not in seite:
                funde.append(("N5", grund, code))
        if action and "<form" not in seite:
            funde.append(("N5", "Formular-Endpunkt gesetzt, aber die Seite zeigt "
                                "kein <form> – Shortcode-Zweig nicht erreicht?", "kein-form"))
    if not _cta_im_footer(footer):
        funde.append(("N6", "Capture konfiguriert, aber im Footer nirgends verlinkt "
                            "– die Liste wächst nie, weil niemand den Weg sieht",
                      "cta-versteckt"))
    if ds_herkunft == "fehlend":
        funde.append(("N7", "die Datenschutzerklärung existiert weder gebaut "
                            "(public/) noch als Quelle (content/datenschutz/index.md) "
                            "– die Prüfung ist ausgefallen, nicht bestanden", "ds-fehlt"))
    elif ds_abschnitt is None:
        funde.append(("N7", "datenschutz/-Seite hat keinen Newsletter-Abschnitt "
                            "(Anlass, Double-Opt-In-Nachweis, Speicherdauer, Widerruf) "
                            "– Capture ohne Rechtstext ist der Grund, warum "
                            "Formulare abgemahnt werden; Vorlage: "
                            "docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md", "rechtstext"))
    elif not ds_abschnitt.strip():
        funde.append(("N7", "Newsletter-Abschnitt hat eine Überschrift, aber keinen "
                            "Text – ein halbfertiger Rechtstext ist ein anderer "
                            "Befund als ein fehlender; Vorlage: "
                            "docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md", "ds-leer"))
    elif ds_platz:
        funde.append(("N7", _platzhalter_meldung(ds_platz), "ds-platzhalter"))
    if ds_widerspruch:
        funde.append(("N7", "Formular ist geschaltet, die Datenschutzerklärung "
                            "behauptet aber, es gebe „derzeit keinen Newsletter"
                            "\" – Widerspruch ohne Graubereich: Text vor dem "
                            "ersten Versand ersetzen", "ds-widerspruch"))
    wf = _read(os.path.join(root, WORKFLOW_REL))
    if not wf:
        note.append(("N8", f"kein Versand-Workflow ({WORKFLOW_REL}) – Digest wird "
                           "nicht automatisch erstellt", "workflow-fehlt"))
    else:
        if "NEWSLETTER_WORKER_EXPORT_KEY" not in wf:
            funde.append(("N8", "Workflow existiert, liest aber "
                                "NEWSLETTER_WORKER_EXPORT_KEY nicht – der "
                                "Listen-Versand wäre für immer leer (keine "
                                "Abonnenten-Liste abholbar)", "workflow-blind"))
        if "RESEND_API_KEY" not in wf and "NEWSLETTER_SMTP_HOST" not in wf:
            funde.append(("N8", "Workflow existiert, konfiguriert aber weder "
                                "RESEND_API_KEY noch NEWSLETTER_SMTP_HOST – kein "
                                "Transport, keine Mail", "workflow-transport"))
        if "--strict-inert" not in wf:
            note.append(("N8", "Workflow prüft den Leerzustand nicht laut "
                               "(--strict-inert) – ein inaktiver Versand bliebe "
                               "unsichtbar", "workflow-leise"))
    if not _read(os.path.join(root, WORKFLOW_LIFE_REL)):
        note.append(("N8", f"kein Lifecycle-Workflow ({WORKFLOW_LIFE_REL}) – "
                           "Bestätigungs-Mails (Double-Opt-In) werden nicht "
                           "automatisch versendet; der Worker meldet es als "
                           "Dispatch-Fehlgriff", "lifecycle-fehlt"))
    zustand = "kaputt" if funde else "aktiv"
    return funde, note, zustand


# -------------------------------------------------------------------------- Digest
def baue_ausgabe(artikel: list[dict], datum: str, versprechen: str,
                 *, root: str = BLOG_DIR) -> dict:
    """Die Ausgabe einer Ausgabe: Marke, Blöcke, Betreff, Preheader – vom Studio.

    Der Digest ist der Sammler und Entscheider (was ist neu, was schon versandt),
    das Studio ist die Setzerwerkstatt. Getrennt, weil der Versandpfad das Layout
    nicht kennt und das Layout den Duplikatsschutz nicht braucht.
    """
    if not artikel:
        return {"html": "", "text": "", "betreff": "", "preheader": "", "anzahl": 0,
                "blocks": [], "material": []}
    try:
        tag = datetime.date.fromisoformat(str(datum)[:10])
    except ValueError:
        tag = datetime.date.today()
    limit = max(1, int(studio.konfiguration(root)["email"].get("max_artikel", 5)))
    artikel = artikel[:limit]
    material = studio.material_aus_artikel(root, artikel)
    e = studio.baue_email(material, datum=tag, root=root, versprechen=versprechen)
    e["anzahl"] = len(artikel)
    return e


def baue_digest(artikel: list[dict], datum: str, versprechen: str,
                *, root: str = BLOG_DIR) -> tuple[str, str, int]:
    """Abwärtskompatible Fassade: (html, text, anzahl)."""
    e = baue_ausgabe(artikel, datum, versprechen, root=root)
    return e["html"], e["text"], e["anzahl"]


# --------------------------------------------------------------------- Eigenbetrieb
def marken_einsetzen(html: str, text: str, token: str,
                     worker_basis: str = "") -> tuple[str, str]:
    """Die Studio-Marken in echte, PRO EMPFÄNGER gültige Links auflösen.

    Mit Token zeigen die Links auf die Journey-ENDPUNKTE des Workers
    (eigene Subdomain, selbe Domain): GET /abmelden meldet direkt ab
    (derselbe One-Click-Weg wie der List-Unsubscribe-Header), /praferenzen
    rendert die Auswahl mit der aktuellen Häkchen-Stellung. Der Worker
    rendert pro Anfrage – das Token darf in das HTML, und ohne JavaScript
    funktioniert das Formular, weil es ein normales POST-Formular ist.
    Die Blog-Seiten /newsletter/abmelden/ & /newsletter/praeferenzen/
    bleiben die INFO-Seiten (Daten, Wege, Rechtliches) ohne Token.
    Ohne Token (Testversand an fremde Adressen) zeigen die Links auf
    diese Info-Seiten; dort steht der ehrliche Weg (formlos per Mail).
    {{mirror}} zeigt auf die Anmeldeseite – es gibt keinen Webbasis-Mirror
    dieser Ausgabe, und ein erfundener Link wäre ein toter Anker.
    """
    basis = (worker_basis or "").rstrip("/")
    if token and basis:
        abmelden = f"{basis}/abmeldung?token={token}"
        profil = f"{basis}/praferenzen?token={token}"
    else:
        abmelden = f"{GRUND_URL}/newsletter/abmelden/"
        profil = f"{GRUND_URL}/newsletter/praeferenzen/"
    spiegel = f"{GRUND_URL}/newsletter/"
    ersatz = {"{{unsubscribe}}": abmelden,
              "{{update_profile}}": profil,
              "{{mirror}}": spiegel}
    for marke, ziel in ersatz.items():
        html = html.replace(marke, ziel)
        text = text.replace(marke, ziel)
    return html, text


def themen_filter(artikel: list[dict], themen: list[str]) -> list[dict]:
    """Artikel nach der THEMENWAHL des Abonnenten filtern (pillar-Feld).

    Ohne Auswahl (leere Liste) kommt alles – das ist das Versprechen des
    Formulars. Mit Auswahl kommt nur das ausgewählte; „nichts passt“ ist
    ein legitimes Ergebnis (der Empfänger wird dann verschont, nicht mit
    einer Mail ohne Inhalt versorgt).
    """
    if not themen:
        return list(artikel)
    return [a for a in artikel if (a.get("pillar") or "") in themen]


def varianten_bauen(root: str, artikel: list[dict], datum_iso: str, versprechen: str,
                    themen_mengen: list[frozenset]) -> dict[frozenset, dict]:
    """Eine Ausgabe-Variante pro THEMENGROUPE.

    Die Hauptvariante (leere Menge) ist die, die main() bereits QA-geprüft
    hat; hier wird sie wiederverwendet, nicht neu gebaut. Weiter Varianten
    gelten nur für Gruppen, die wirklich Artikel abbilden; leere Gruppen
    werden nicht gebaut (kein Mail ohne Inhalt).
    """
    ausgaben: dict[frozenset, dict] = {}
    for menge in themen_mengen:
        if not menge:
            continue
        gefiltert = themen_filter(artikel, list(menge))
        if not gefiltert:
            continue
        ausgaben[frozenset(menge)] = baue_ausgabe(gefiltert, datum_iso, versprechen, root=root)
    return ausgaben


def worker_liste(base: str, key: str) -> list[dict]:
    """Aktive Abonnenten vom Worker holen (geschützter Export).

    → [{email, token, themen, bestaetigt}]. Netzwerkfehler werfen – der
    Aufrufer entscheidet, was damit ist (fail-closed beim Listen-Versand).
    """
    antwort = versand.worker_abfrage("/export/abonnenten", None, base=base, key=key)
    liste = antwort.get("abonnenten")
    return liste if isinstance(liste, list) else []


def email_aus_text(roh: str) -> str:
    """Eine Adresse aus Freitext, oder leer wenn keine gültige drinsteht.

    Akzeptiert `name@domain.tld` und `Name <name@domain.tld>`. Der
    Resend-API- und der Worker-Empfang prüfen streng – ein Anzeigename,
    ein Leerzeichen oder ein Objekt ist der 400er, an dem ein Lauf stirbt.
    """
    text = (roh or "").replace("\u00a0", " ").strip()
    if not text:
        return ""
    klammer = re.search(r"<([^<>]+)>", text)
    if klammer:
        text = klammer.group(1).strip()
    text = text.strip().strip("\"'").lower()
    if (len(text) > 254 or ".." in text or text.startswith(".")
            or text.endswith(".") or text.startswith("@")):
        return ""
    lokal, trenn, domain = text.partition("@")
    if (not trenn or not lokal or not domain or lokal.startswith(".")
            or lokal.endswith(".") or domain.startswith(".")
            or domain.endswith(".") or domain.startswith("-")):
        return ""
    if not EMAIL_MUSTER.fullmatch(text):
        return ""
    return text


def test_adressen_lesen(roh: str) -> tuple[list[str], str]:
    """Testadressen. → (liste, fehler).

    Komma, Semikolon oder Zeilenumbruch trennen mehrere Adressen. Ungültiges
    bricht ab: eine falsche Adresse trifft niemanden, aber sie dürfte nicht
    „irgendwo sonst“ landen – der Testversand geht exakt an die eingegebenen
    Adressen und an niemandem sonst.
    """
    text = (roh or "").strip()
    if not text:
        return [], ""
    adressen: list[str] = []
    for teil in re.split(r"[,;\n]+", text):
        teil = teil.strip()
        if not teil:
            continue
        norm = email_aus_text(teil)
        if not norm:
            return [], (
                f"Testadresse {teil!r} ist keine gültige E-Mail. Kein Versand: "
                "ein falsches Ziel wäre genau die Mail, die niemand bestellt hat.")
        if norm not in adressen:
            adressen.append(norm)
    if len(adressen) > TEST_ADRESSEN_MAX:
        return [], (f"Höchstens {TEST_ADRESSEN_MAX} Testadressen pro Lauf – "
                    "mehr ist kein Probelauf, sondern ein Massenversand.")
    return adressen, ""


def absender_konfig(root: str) -> dict:
    konf = studio.konfiguration(root, streng=False)
    e = konf.get("email", {}) or {}
    a = e.get("absender", {}) or {}
    email = (os.environ.get("NEWSLETTER_ABSENDER", "").strip()
             or str(a.get("email") or "news@franksfinanzcheck.de")).strip()
    return {"name": str(a.get("name") or "FranksFinanzcheck").strip() or "FranksFinanzcheck",
            "email": email,
            "antwort_an": str(e.get("antwort_an") or "").strip()}


# --------------------------------------------------------------------- Verriegelung
def kadenz_pruefen(root: str) -> str:
    """Status strikt lesen: ein kaputtes Journal darf nie einen Versand erlauben."""
    pfad, _, _ = zustand_konfig(root)
    with open(os.path.join(root, pfad), encoding="utf-8") as fh:
        state = json.load(fh)
    return schedule.versandpause(state)


def termin_reservieren(root: str) -> None:
    """Vor dem Versand schreiben; selbst ein Prozessabbruch verbraucht den Termin."""
    state = lade_state(root)
    termine = state.get("versand_termine", [])
    if "versand_termine" not in state and state.get("zuletzt_versandt"):
        termine = [state["zuletzt_versandt"]]
    state["versand_termine"] = (termine + [schedule.jetzt().isoformat()])[-60:]
    speichere_state(root, state)
    if lade_state(root).get("versand_termine") != state["versand_termine"]:
        raise OSError("Versandtermin konnte nicht verifiziert werden")


def sperre_pruefen(root: str) -> str:
    """Steht der Status auf „Versand unklar“? Dann kein weiterer Listen-Versand.

    Der Halt ist absichtlich eine MENSCHENAufgabe: Ein Lauf, der nicht weiß, ob
    die vorige Ausgabe ankam, darf sie nicht nochmal in die Welt schicken – aber
    er darf sie auch nicht eigenmächtig „für versandt“ erklären. Der Release
    steht im Status-JSON, die Prüfung liest ihn.
    """
    try:
        block = lade_state(root).get("versand_unklar") or {}
    except Exception:  # noqa: BLE001  (kaputtes JSON: das meldet die Wache separat)
        return ""
    if not block:
        return ""
    return (f"der Status trägt den Block „versand_unklar“ (Kennung "
            f"{block.get('kennung', '?')}, notiert {block.get('zeitpunkt', '?')}): "
            "ein früherer Sende-Aufruf ist ohne belegbares Ergebnis geblieben. "
            "Erst in der Zustellung nachsehen (Transport-Log/Postfach) und den "
            "Block auflösen (Schlüssel `versand_unklar` aus data/newsletter_state.json) – "
            "sonst droht dieselbe Ausgabe zweimal im Postfach.")


def sperre_setzen(root: str, kennung, betreff: str) -> None:
    """Halt schreiben (best effort): der nächste Lauf muss ihn sehen können."""
    try:
        state = lade_state(root)
        state["versand_unklar"] = {"kennung": kennung,
                                   "betreff": betreff,
                                   "zeitpunkt": datetime.datetime.now(datetime.timezone.utc)
                                   .isoformat(timespec="seconds")}
        speichere_state(root, state)
    except OSError as exc:
        print(f"   ⚠ Sperre konnte nicht geschrieben werden ({exc}) – der nächste Lauf "
              "kennt den Zweifel nicht und könnte dieselbe Ausgabe erneut senden.")


# --------------------------------------------------------------------- Versand
def versende(root: str, artikel: list[dict], ausgabe: dict, datum_iso: str,
             versprechen: str, *, dry_run: bool, test_adresse: str = "") -> int:
    """Die eigentliche Versandentscheidung. Drei Wege, einer Boden:

    * dry_run            → nichts verlässt die Maschine (nur Bauen),
    * test_adresse       → exakt die eingegebenen Adressen, nie die Liste
                           (kein fremdes Konto, kein „Kontakt muss existieren"),
    * LISTE              → aktive Abonnenten aus dem Worker, pro Themengruppe
                           eine Ausgabe-Variante, pro Empfänger echte Links.

    → Exit-Code: 0 ok/dry-run, 1 Befund/Teilversand, 2 Fehler.
    """
    konf = studio.konfiguration(root, streng=False)
    html, text = ausgabe["html"], ausgabe["text"]
    betreff = ausgabe["betreff"]
    preheader = ausgabe.get("preheader", "")
    if dry_run:
        print(f"   ℹ️  dry-run: keine Netz-Anfrage – die Ausgabe wäre so versendet "
              f"worden: Betreff {betreff!r}, {len(html)} Zeichen HTML, "
              f"Transport {versand.transport_waehle(root, konf)[0]}")
        return 0
    if (test_adresse or "").strip():
        return _versand_test(root, html, text, betreff, preheader,
                             test_adresse, konf, datum_iso)
    return _versand_liste(root, artikel, html, text, betreff, preheader,
                          versprechen, konf, datum_iso)


def _sende_datei_schreiben(datei: str, ausgabe: str, betreff: str,
                           empfaenger: list[dict]) -> None:
    with open(datei, "w", encoding="utf-8") as fh:
        json.dump({"ausgabe": ausgabe, "betreff": betreff, "empfaenger": empfaenger},
                  fh, ensure_ascii=False)


def _versand_test(root: str, html: str, text: str, betreff: str,
                  preheader: str, test_adresse: str, konf: dict, datum_iso: str) -> int:
    """Probelauf: die Mail geht DIREKT an die eingegebenen Adressen.

    Kein fremdes Konto, kein Listen-Bezug, kein „Kontakt anlegen“-Tanz:
    die Envelope ist so ehrlich wie eine einzelne Mail an eine Person.
    Die Marken zeigen ohne Token auf die Journey-Seiten (dort steht der
    ehrliche Weg, formlos per Mail).
    """
    adressen, fehler = test_adressen_lesen(test_adresse)
    if fehler or not adressen:
        print(f"   ❌ kein Testversand: {fehler or 'Testadresse fehlt'}")
        return 1
    absender = absender_konfig(root)
    roh_reply = absender["antwort_an"]
    if roh_reply and not email_aus_text(roh_reply):
        print(f"   ⚠️  Antwortadresse {roh_reply!r} ist keine gültige E-Mail – "
              f"Versand nutzt die Absenderadresse {absender['email']}.")
    html_t, text_t = marken_einsetzen(html, text, "", worker_basis="")
    datei = os.path.join(tempfile.gettempdir(), "ff-nl-testversand.json")
    _sende_datei_schreiben(datei, f"test-{datum_iso}", betreff,
                           [{"email": a, "token": "", "html": html_t, "text": text_t}
                            for a in adressen])
    try:
        rc = versand.sende_datei(datei, root=root, konf=konf)
    finally:
        try:
            os.remove(datei)
        except OSError:
            pass
    if rc == 0:
        print(f"✅ TESTVERSAND ERFOLGT: {len(adressen)} Adresse(n) – die Mail ist "
              "raus, genau an die eingegebenen Adressen.")
    elif rc == 1:
        print(f"⚠ TEILVERSAND: nicht alle Testadressen haben die Mail – Details im "
              "Journal (data/newsletter_journal.jsonl). Der Listen-Versand ist NICHT "
              "dafür blockiert.")
    else:
        # Die Ursache gehört in DIESE Zeile: sie ist die letzte ❌-Zeile im
        # Log und damit das, was als Annotation im Lauf steht. Ohne sie
        # stand dort am 25.09.2026 nur „nichts versendet“, während der
        # Grund (HTTP 403 an der Kante, Error 1010) im Journal lag.
        grund = versand.letzter_fehler(root, ausgabe=f"test-{datum_iso}")
        print("❌ TESTVERSAND FEHLGESCHLAGEN: nichts versendet – "
              f"{grund or 'Details im Journal (data/newsletter_journal.jsonl)'}. "
              "Der Listen-Versand ist NICHT dafür blockiert.")
    return rc


def _versand_liste(root: str, artikel: list[dict], html: str, text: str, betreff: str,
                   preheader: str, versprechen: str, konf: dict, datum_iso: str) -> int:
    """Echter Listen-Versand: Abonnenten aus dem Worker, pro Empfänger
    eigene Ausgabe-Variante (Themenwahl) und eigene Abmelde-Links.

    Idempotenz: wurde diese Ausgabe (selbes Datum + Betreff) bereits
    TEILWEISE versendet, springen die bedienten Empfänger über
    (Hash-Abgleich gegen state["letzte_ausgabe"]["versendet"]) – ein
    zweiter Lauf derselben Ausgabe trifft keinen Abonnenten doppelt.
    """
    base, key = versand.worker_konfig()
    if not base or not key:
        print("   ❌ kein Listen-Versand: NEWSLETTER_WORKER_BASE / "
              "NEWSLETTER_WORKER_EXPORT_KEY fehlen. Die Adressen liegen im "
              "Worker, nicht im Repo – Secrets setzen (Doku: "
              "docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md), dann erneut.")
        return 1
    # Der Halt ist eine Menschenentscheidung – hier, am einzigen Ort, an dem
    # eine LISTE getroffen wird (der Testversand betrifft ihn nicht).
    sperre = sperre_pruefen(root)
    if sperre:
        print(f"   ❌ kein Listen-Versand: {sperre}")
        return 1
    try:
        abonnten = worker_liste(base, key)
    except (RuntimeError, OSError) as exc:
        print(f"   ❌ kein Listen-Versand: Abonnenten-Liste nicht abholbar ({exc}) – "
              "lieber fail-closed, als blind zu versenden.")
        return 1
    if not abonnten:
        print("   ❌ kein Listen-Versand: der Worker meldet 0 aktive Abonnenten – "
              "es wäre eine Ausgabe an niemanden. Erst Anmeldungen sammeln "
              "(Double-Opt-In), dann --live; für die Probe --test-adresse nutzen.")
        return 1

    state = lade_state(root)
    letzte = state.get("letzte_ausgabe") or {}
    wiederholung = (letzte.get("datum") == datum_iso and letzte.get("betreff") == betreff)
    schon_gesendet = set(letzte.get("versendet", [])) if wiederholung else set()

    # EINE Ausgabe-Variante pro Distinkter Themenwahl (leere Menge = Haupt-
    # Variante, die main() bereits QA-geprüft hat). Varianten ohne Artikel
    # werden nicht gebaut – ein Mail ohne Inhalt ist kein Service.
    mengen = {frozenset(t for t in (p.get("themen") or []) if t) for p in abonnten}
    varianten = varianten_bauen(root, artikel, datum_iso, versprechen,
                                [m for m in mengen if m])
    # Variante-QA: jede zusätliche Variante muss dasselbe Niveau halten wie
    # die Hauptvariante. Fund → Gruppe wird verschont (kein halbguter Versand).
    for menge in list(varianten):
        pruef = qa.pruefe(varianten[menge], konf=studio.konfiguration(root, streng=False),
                          materiale=varianten[menge].get("material") or [],
                          zustand=state, root=root)
        if not pruef["bestanden"]:
            for f in pruef["funde"]:
                print(f"   ❌ QA-Variante ({', '.join(sorted(menge))}): "
                      f"[{f['regel']}] {f['meldung']}")
            varianten.pop(menge)
            print(f"   ⚠ Variante ({', '.join(sorted(menge))}) wird NICHT versendet – "
                  "die betroffenen Abonnenten werden diesen Tag verschont.")

    empfaenger: list[dict] = []
    uebersprungen = 0
    verschont = 0
    for person in abonnten:
        h = versand.hash16(person.get("email", ""))
        if h in schon_gesendet:
            uebersprungen += 1
            continue
        menge = frozenset(t for t in (person.get("themen") or []) if t)
        if menge:
            if menge not in varianten:
                verschont += 1
                continue
            variant = varianten[menge]
            html_v, text_v = variant["html"], variant["text"]
        else:
            html_v, text_v = html, text
        html_v, text_v = marken_einsetzen(html_v, text_v,
                                          person.get("token") or "",
                                          worker_basis=base)
        empfaenger.append({"email": person["email"],
                           "token": person.get("token") or "",
                           "html": html_v, "text": text_v,
                           "preheader": preheader})
    if uebersprungen:
        print(f"   ℹ️  Idempotenz: {uebersprungen} Empfänger dieser Ausgabe haben sie "
              "bereits erhalten – übersprungen.")
    if verschont:
        print(f"   ℹ️  {verschont} Abonnent(en) verschont: keine Artikel in ihrer "
              "gewählten Themenwelt (leere Mails sind kein Service).")
    if not empfaenger:
        print("   📭 Listen-Versand: alle Empfänger sind bereits bedient oder "
              "verschont – nichts zu senden (Status bleibt unangetastet).")
        return 0

    datei = os.path.join(tempfile.gettempdir(), "ff-nl-listenversand.json")
    _sende_datei_schreiben(datei, f"liste-{datum_iso}", betreff, empfaenger)
    termin_reservieren(root)
    try:
        rc = versand.sende_datei(datei, root=root, konf=konf)
    finally:
        try:
            os.remove(datei)
        except OSError:
            pass
    return _status_nach_versand(root, betreff, datum_iso, empfaenger, rc,
                                uebersprungen=uebersprungen, verschont=verschont)


def _status_nach_versand(root: str, betreff: str, datum_iso: str,
                         empfaenger: list[dict], rc: int,
                         uebersprungen: int = 0, verschont: int = 0) -> int:
    """Den Versandstatus schreiben – der Duplikatsschutz des nächsten Laufs.

    * rc 0 (alles zugestellt): Ausgabe als gesendet, Artikel in
      versandene_artikel, Halt auflösen, versendete Hashes als Nachweis.
    * rc 1 (TEILVERSAND): NUR die zugestellten Hashes als gesendet merken
      (aus dem Journal – es ist der Beleg); die Ausgabe bleibt offen,
      der nächste Lauf schickt sie an die REST-adressen nach.
    * rc 2 (nichts/unklar): HARTER HALT (versand_unklar) – der nächste
      Listen-Versand bleibt stehen, bis ein Mensch nachgeschaut hat.
    """
    hashes = set(versand.hash16(p["email"]) for p in empfaenger)
    state = lade_state(root)
    _, bet_hist, art_hist = zustand_konfig(root)
    jetzt = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    vorherige = state.get("letzte_ausgabe") or {}
    vorher = (set(vorherige.get("versendet", []))
              if vorherige.get("datum") == datum_iso
              and vorherige.get("betreff") == betreff else set())
    if rc == 0:
        state["letzte_ausgabe"] = {"datum": datum_iso, "betreff": betreff,
                                   "versendet": sorted(vorher | hashes),
                                   "uebersprungen": uebersprungen,
                                   "verschont": verschont,
                                   "transport": os.environ.get("NEWSLETTER_TRANSPORT", "")
                                   or "resend",
                                   "ts": jetzt}
        bereits = set(state.get("versandene_artikel", []))
        bereits.update(state.get("pending", []))
        # sortiert: die Datei wird im Workflow committet – willkürliche
        # Set-Reihenfolge wäre reiner Diff-Lärm in jedem Lauf.
        state["versandene_artikel"] = sorted(bereits)[-art_hist:]
        state.pop("versand_unklar", None)
        state["pending"] = []
        state["betreff_verlauf"] = ((state.get("betreff_verlauf", []) + [betreff])
                                    [-bet_hist:])
        speichere_state(root, state)
        print(f"✅ VERSAND ERFOLGT: {len(vorher | hashes)} Empfänger · Ausgabe "
              f"{datum_iso} als versendet markiert · Status gespeichert.")
        return 0
    if rc == 1:
        # TEILVERSAND: zugestellte Hashes aus dem Journal rekonstruieren –
        # es ist der einzige Beleg, wer die Ausgabe wirklich hat.
        zugestellt: set[str] = set()
        journal = os.path.join(root, "data", "newsletter_journal.jsonl")
        if os.path.exists(journal):
            with open(journal, encoding="utf-8") as fh:
                for zeile in fh:
                    try:
                        d = json.loads(zeile)
                    except json.JSONDecodeError:
                        continue
                    if (d.get("ausgabe") == f"liste-{datum_iso}"
                            and d.get("status") in ("zugestellt", "dryrun")):
                        zugestellt.add(d.get("empfaenger", ""))
        vorherige = (state.get("letzte_ausgabe") or {})
        vorher = set(vorherige.get("versendet", [])) if vorherige.get("datum") == datum_iso else set()
        state["letzte_ausgabe"] = {"datum": datum_iso, "betreff": betreff,
                                   "versendet": sorted(vorher | zugestellt),
                                   "uebersprungen": uebersprungen,
                                   "verschont": verschont,
                                   "ts": jetzt}
        speichere_state(root, state)
        print(f"⚠ TEILVERSAND: {len(vorher | zugestellt)} von {len(hashes) + len(vorher)} "
              "Empfänger haben die Ausgabe – der Rest wird im nächsten Lauf "
              "nachgeschickt (nur die unversendeten). Die Ausgabe bleibt offen.")
        return 1
    # rc 2: nichts oder unbelegbar – Halt setzen.
    kennung = f"liste:{datum_iso}:{betreff[:40]}"
    sperre_setzen(root, kennung, betreff)
    # Auch hier die Ursache in die Zeile schreiben: sie ist die letzte
    # sichtbare ❌-Zeile (Annotation im Lauf, `gh run view --log`).
    grund = versand.letzter_fehler(root, ausgabe=f"liste-{datum_iso}")
    print(f"🛑 VERSAND-STATUS UNKLAR: nichts (oder nicht belegbar) versendet – "
          f"Halt gesetzt ({kennung})."
          + (f" Erste Ursache: {grund}." if grund else "")
          + " Der nächste Listen-Versand bleibt stehen, "
          "bis im Transport-Log nachgesehen und der Block aufgelöst ist.")
    return 2


# --------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Newsletter-Capture-Wache + Digest (Eigenbetrieb)")
    ap.add_argument("--root", default=BLOG_DIR)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--strict-inert", action="store_true",
                    help="Leerzustand als Fehler (für Läufe, die senden wollen)")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--send", action="store_true",
                    help="Versand auslösen (allein: nur Vorschau/dry-run; mit "
                         "--live an die LISTE, mit --test-adresse an genau "
                         "die Adresse – nie an die Liste)")
    ap.add_argument("--live", action="store_true",
                    help="die LISTE wirklich treffen (sonst dry-run, auch mit --send); "
                         "ein Testversand via --test-adresse ist unabhängig davon real")
    ap.add_argument("--trotz-qa", action="store_true",
                    help="Versand trotz QA-Funden (Betreuer-Ausnahme; Funde werden "
                         "dennoch protokolliert)")
    ap.add_argument("--test-adresse", default="")
    ap.add_argument("--days", type=int, default=schedule.RUECKBLICK_TAGE)
    ap.add_argument("--out", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    root = os.path.abspath(args.root)
    schreiben = args.build or args.send
    if schreiben:
        assert_worktree(root)
    rc_gesamt = 0

    if args.check or not args.build:
        funde, note, zustand = pruefe_capture(root)
        if args.json:
            print(json.dumps({"zustand": zustand,
                              "funde": [{"regel": r, "meldung": m, "code": c} for r, m, c in funde],
                              "hinweise": [{"regel": r, "meldung": m, "code": c} for r, m, c in note],
                              "params": params(root)}, ensure_ascii=False, indent=2))
        else:
            print(f"Newsletter-Capture · {zustand}")
            for reg, msg, code in funde:
                print(f"  ❌ [{reg}/{code}] {msg}")
            for reg, msg, code in note:
                print(f"  ⚠ [{reg}/{code}] {msg}")
            if zustand == "aktiv" and not funde:
                print("  ✅ Anmeldeweg, Landingpage, Rechtstext und Footer-CTA greifen ineinander.")
        if funde or (args.strict_inert and zustand == "inert"):
            rc_gesamt = 1
    if not args.build:
        return rc_gesamt

    # Vor einem Live-Build prüfen, damit eine Pause auch vor Pending/QA greift.
    if args.send and args.live and not args.test_adresse:
        try:
            pause = kadenz_pruefen(root)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            print(f"❌ Versandstatus nicht sicher lesbar: {exc}")
            return 1
        if pause:
            print(f"ℹ️  {pause}")
            return rc_gesamt
    heute = schedule.jetzt().date()
    try:
        with open(os.path.join(root, *zustand_konfig(root)[0].split(os.sep)), encoding="utf-8") as fh:
            state = json.load(fh)
        if not isinstance(state, dict):
            raise ValueError("Versandstatus ist kein Objekt")
    except FileNotFoundError:
        state = {}  # nur Vorschau/Erstaufbau; Live ohne Status wurde oben gesperrt
    except (OSError, ValueError) as exc:
        print(f"❌ Versandstatus defekt, nicht überschrieben: {exc}")
        return 1
    halt = sperre_pruefen(root)
    if halt and args.send and args.live and not (args.test_adresse or "").strip():
        # Fail-Closed: ein Listen-Versand, dessen Ergebnis nicht belegt ist,
        # darf NICHT erneut in die Welt gehen (Doppelzustellung). Der
        # Testversand (eigene Adresse) ist davon ausgenommen – er dupliziert
        # keine Ausgabe bei Subscribers, er ist die SUCHE nach dem Beleg.
        print(f"🛑 Der Versand ist angehalten: {halt}")
        return 1
    schon = set(state.get("versandene_artikel", []))
    artikel = [a for a in live_artikel(root, heute - datetime.timedelta(days=max(1, args.days)))
               if a["slug"] not in schon]
    p = params(root)
    versprechen = p.get("newsletterPromise") or "Zweimal pro Woche: Spartipps und Rechner."
    ausgabe = baue_ausgabe(artikel, heute.isoformat(), versprechen, root=root)
    html, text, anzahl = ausgabe["html"], ausgabe["text"], ausgabe["anzahl"]
    if anzahl == 0:
        print("📬 Digest: nichts zu senden – seit dem letzten Lauf ist nichts Neues "
              "erschienen (oder alles wurde schon versandt).")
        return rc_gesamt
    # Bewusst NICHT unter public/: der gebaute Digest trägt die Marken
    # {{unsubscribe}}, {{mirror}}, {{update_profile}} – die lägen sonst als
    # „Links“ im Auslieferungszustand, wo der Link-Check sie als defekte
    # interne Ziele zählt. Der Versand löst sie PRO EMPFÄNGER auf (Token).
    # CI legt die Dateien nach /tmp (siehe Workflow).
    out_dir = args.out or os.path.join(tempfile.gettempdir(), "ff-newsletter")
    os.makedirs(out_dir, exist_ok=True)
    for ende, inhalt in (("html", html), ("txt", text)):
        with open(os.path.join(out_dir, f"digest-{heute.isoformat()}.{ende}"),
                  "w", encoding="utf-8") as fh:
            fh.write(inhalt)
    betreff = ausgabe["betreff"]
    print(f"📬 Digest gebaut: {anzahl} Artikel → {out_dir}/digest-{heute.isoformat()}.html")
    for a in artikel[:8]:
        print(f"   • {a['titel'][:66]} ({a['datum']})")
    state["pending"] = [a["slug"] for a in ausgabe["material"]]
    speichere_state(root, state)
    # Vor-Versand-Prüfung: die Wache kennt das gebaute E-Mail, nicht die Absicht.
    pruef = qa.pruefe(ausgabe, konf=studio.konfiguration(root), materiale=ausgabe["material"],
                      zustand=state, root=root)
    for f in pruef["funde"]:
        print(f"   ❌ QA [{f['regel']}] {f['meldung']}")
    for w in pruef["warnungen"]:
        print(f"   ⚠ QA [{w['regel']}] {w['meldung']}")
    print(f"   Vor-Versand-Prüfung: {pruef['score']}/100 · {pruef['regeln_geprueft']} Regeln · "
          f"{len(pruef['funde'])} Funde, {len(pruef['warnungen'])} Warnungen")
    if not pruef["bestanden"] and not args.trotz_qa:
        print("   ❌ Versand blockiert: die Vor-Versand-Prüfung meldet Funde. Bauen bleibt "
              "erlaubt, Senden nicht – Ausnahmeschalter: --trotz-qa.")
        return 1
    if args.send:
        # --live = real an die LISTE. Eine Testadresse macht den Versand auch
        # ohne --live real (direkte Mail an genau die Adresse) – sonst wäre der
        # dokumentierte Probelauf `--send --test-adresse X` eine stille
        # Vorschau, und genau so lief der 23.09.2026: grün, aber keine Mail.
        rc_gesamt = max(rc_gesamt, versende(
            root, artikel, ausgabe, heute.isoformat(), versprechen,
            dry_run=not (args.live or bool(args.test_adresse)),
            test_adresse=args.test_adresse))
    else:
        print("   (kein Versand – --send fehlt; gebaute Digeste bleiben bewusst lokal)")
    return rc_gesamt


# --------------------------------------------------------------------- Selftest
def _selftest() -> int:
    """Hermetisch: kein Netz, kein Worker, kein Hugo-Build nötig.

    Prüfziele (alles, was den Newsletter leben lässt):
      A. Capture-Wache: inert/aktiv/kaputt, Hosts, Feldname, N8-Workflow-Check
      B. Marken: pro Empfänger echte Token-Links, ohne Token Journey-Seiten
      C. Testadressen: gültig, ungültig, mehrere, Obergrenze
      D. Themen-Varianten: Filterung, leere Gruppe, QA-Gate der Variante
      E. Idempotenz: zweiter Lauf derselben Ausgabe trifft niemanden doppelt
      F. Verriegelung: Sperre setzt, liest, hebt; dry-run ohne Netz
      G. Journal: Hash statt Roh-Adresse
    """
    pruefungen = 0

    def pruefe(bedingung: bool, meldung: str) -> None:
        nonlocal pruefungen
        pruefungen += 1
        if not bedingung:
            raise AssertionError(f"❌ Selftest #{pruefungen}: {meldung}")

    tmp = tempfile.mkdtemp(prefix="ff-nl-selftest-")
    import shutil

    def baum(name: str, *, toml: str = "", landing: str = "", seite_html: str = "",
             footer_html: str = "", ds: str = "", workflow: str = "",
             lifecycle: str = "") -> str:
        base = os.path.join(tmp, name)
        os.makedirs(os.path.join(base, "public", "newsletter"), exist_ok=True)
        os.makedirs(os.path.join(base, "content"), exist_ok=True)
        os.makedirs(os.path.join(base, "layouts", "shortcodes"), exist_ok=True)
        os.makedirs(os.path.join(base, ".github", "workflows"), exist_ok=True)
        with open(os.path.join(base, "hugo.toml"), "w", encoding="utf-8") as fh:
            fh.write(toml)
        if landing:
            os.makedirs(os.path.join(base, "content", "newsletter"), exist_ok=True)
            with open(os.path.join(base, "content", "newsletter", "index.md"),
                      "w", encoding="utf-8") as fh:
                fh.write(landing)
        with open(os.path.join(base, "public", "newsletter", "index.html"),
                  "w", encoding="utf-8") as fh:
            fh.write(seite_html)
        with open(os.path.join(base, "public", "index.html"), "w", encoding="utf-8") as fh:
            fh.write(footer_html)
        if ds:
            os.makedirs(os.path.join(base, "content", "datenschutz"), exist_ok=True)
            with open(os.path.join(base, "content", "datenschutz", "index.md"),
                      "w", encoding="utf-8") as fh:
                fh.write(ds)
        with open(os.path.join(base, "layouts", "shortcodes", "newsletter_form.html"),
                  "w", encoding="utf-8") as fh:
            fh.write('<form action="{{ .form }}"><input name="email"></form>'
                     if "feldname-gut" in name else
                     '<form><input name="email"></form>')
        if workflow:
            with open(os.path.join(base, ".github", "workflows", "newsletter-daily.yml"),
                      "w", encoding="utf-8") as fh:
                fh.write(workflow)
        if lifecycle:
            with open(os.path.join(base, ".github", "workflows", "newsletter-lifecycle.yml"),
                      "w", encoding="utf-8") as fh:
                fh.write(lifecycle)
        return base

    DS_GUT = ("# Datenschutz\n\n## 8. Newsletter / Kontaktaufnahme\n\n"
              "Anmeldung mit Double-Opt-In; Speicherdauer bis Abmeldung, "
              "Löschung innerhalb von 30 Tagen, Widerruf jederzeit.")
    SEITE_GUT = ("<html><body>Double-Opt-In vorhanden. "
                 "<a href=\"/datenschutz/\">Datenschutz</a> "
                 "<form><input name=\"email\"></form></body></html>")
    FOOTER_GUT = '<div class="newsletter-footer">Abonniere</div>'
    WF_GUT = ("name: newsletter-daily\nenv:\n  NEWSLETTER_WORKER_EXPORT_KEY: secret\n"
              "  RESEND_API_KEY: secret\nrun: --strict-inert\n")
    LC_GUT = "name: newsletter-lifecycle\non: workflow_dispatch\n"

    # A1: inert ohne Konfiguration – ehrlicher Leerzustand.
    b = baum("inert", ds=DS_GUT)
    funde, note, zustand = pruefe_capture(b)
    pruefe(zustand == "inert", f"inert: Zustand {zustand}")
    pruefe(any(r == "N0" for r, _, _ in note), "inert: N0-Hinweis fehlt")

    # A2: aktiv mit Worker-Endpunkt + Workflow-Check.
    b = baum("aktiv", toml='newsletterFormAction = "https://abos.franksfinanzcheck.de/anmeldung"\n',
             landing="# NL", seite_html=SEITE_GUT, footer_html=FOOTER_GUT,
             ds=DS_GUT, workflow=WF_GUT, lifecycle=LC_GUT)
    funde, note, zustand = pruefe_capture(b)
    pruefe(zustand == "aktiv", f"aktiv: Zustand {zustand} ({funde})")

    # A3: http-Endpunkt = Fund (Adressen dürfen nicht im Klartext laufen).
    b = baum("http", toml='newsletterFormAction = "http://abos.franksfinanzcheck.de/anmeldung"\n',
             landing="# NL", seite_html=SEITE_GUT, footer_html=FOOTER_GUT, ds=DS_GUT,
             workflow=WF_GUT, lifecycle=LC_GUT)
    funde, _, _ = pruefe_capture(b)
    pruefe(any(r == "N2" for r, _, _ in funde), "http: N2-Fund fehlt")

    # A4: fremder Host = Hinweis (vielleicht die eigene Worker-Domain im Test).
    b = baum("fremd", toml='newsletterFormAction = "https://formular.bsp.example/x"\n',
             landing="# NL", seite_html=SEITE_GUT, footer_html=FOOTER_GUT, ds=DS_GUT,
             workflow=WF_GUT, lifecycle=LC_GUT)
    funde, note, _ = pruefe_capture(b)
    pruefe(any(r == "N2" for r, _, _ in note), "fremd: N2-Hinweis fehlt")

    # A5: Platzhalter im Endpunkt = Fund.
    b = baum("platz", toml='newsletterFormAction = "https://abos.franksfinanzcheck.de/{{TODO}}"\n',
             landing="# NL", seite_html=SEITE_GUT, footer_html=FOOTER_GUT, ds=DS_GUT,
             workflow=WF_GUT, lifecycle=LC_GUT)
    funde, _, _ = pruefe_capture(b)
    pruefe(any("Platzhalter" in m for r, m, _ in funde), "platz: N2-Platzhalter-Fund fehlt")

    # A6: Workflow ohne Export-Key = blinder Versand (Fund N8).
    b = baum("blind", toml='newsletterFormAction = "https://abos.franksfinanzcheck.de/anmeldung"\n',
             landing="# NL", seite_html=SEITE_GUT, footer_html=FOOTER_GUT, ds=DS_GUT,
             workflow="name: x\nrun: echo\n", lifecycle=LC_GUT)
    funde, _, _ = pruefe_capture(b)
    pruefe(any(r == "N8" for r, _, _ in funde), "blind: N8-Fund fehlt")

    # A7: Rechte fehlen (kein Newsletter-Abschnitt im DS) = Fund N7.
    b = baum("dsleer", toml='newsletterFormAction = "https://abos.franksfinanzcheck.de/anmeldung"\n',
             landing="# NL", seite_html=SEITE_GUT, footer_html=FOOTER_GUT,
             ds="# Datenschutz\n\n## 8. Sonstiges\n\nNix.", workflow=WF_GUT, lifecycle=LC_GUT)
    funde, _, _ = pruefe_capture(b)
    pruefe(any(r == "N7" for r, _, _ in funde), "dsleer: N7-Fund fehlt")

    # B1: Marken → pro Empfänger echte Token-Links.
    html_m = ('<a href="{{unsubscribe}}">Abmelden</a> <a href="{{update_profile}}">Profil</a> '
              '<a href="{{mirror}}">Browser</a>')
    text_m = "Abmelden: {{unsubscribe}} · Profil: {{update_profile}} · Im Browser: {{mirror}}"
    # Mit Worker-Basis: die Endpunkte des Workers (eigene Subdomain),
    # denn der rendert pro Anfrage und trägt das Token – ohne JavaScript
    # inklusive.
    h, t = marken_einsetzen(html_m, text_m, "tok-123",
                            worker_basis="https://abos.beispiel.de")
    pruefe("https://abos.beispiel.de/abmeldung?token=tok-123" in h,
           "Marken: Abmeldelink zeigt nicht auf den Worker")
    pruefe("https://abos.beispiel.de/praferenzen?token=tok-123" in h,
           "Marken: Profil-Link zeigt nicht auf den Worker")
    pruefe("https://abos.beispiel.de/abmeldung?token=tok-123" in t,
           "Marken: Textvariante ohne Worker-Abmeldelink")
    pruefe("{{unsubscribe}}" not in h and "{{unsubscribe}}" not in t, "Marken: Platzhalter geblieben")
    # Ohne Token (Testversand) und ohne Worker-Basis: die INFO-Seiten der
    # Site, kein Token, kein toter Endpunkt.
    h2, t2 = marken_einsetzen(html_m, text_m, "")
    pruefe("abmelden/" in h2 and "?token=" not in h2, "Marken: Testmodus ohne Token")
    pruefe("/newsletter/" in h2, "Marken: Mirror zeigt auf die Site")

    # C1: Testadressen.
    a, e = test_adressen_lesen("a@b.de, c@d.de")
    pruefe(a == ["a@b.de", "c@d.de"] and not e, f"Testadressen: {a} {e}")
    a, e = test_adressen_lesen("nicht-adresse")
    pruefe(not a and e, "Testadressen: ungültige nicht abgefangen")
    a, e = test_adressen_lesen(",".join(f"nr{i}@b.de" for i in range(TEST_ADRESSEN_MAX + 1)))
    pruefe(not a and "Höchstens" in e, "Testadressen: Obergrenze fehlt")
    a, e = test_adressen_lesen("Name <x@b.de>")
    pruefe(a == ["x@b.de"], "Testadressen: Klammern-Form nicht erkannt")

    # D1: Themen-Filterung + leere Gruppe.
    artikel = [{"slug": "s1", "datum": "2026-09-20", "titel": "T1", "beschreibung": "",
                "url": "/posts/s1/", "path": "", "pillar": "strom-sparen"},
               {"slug": "s2", "datum": "2026-09-21", "titel": "T2", "beschreibung": "",
                "url": "/posts/s2/", "path": "", "pillar": "internet-dsl"},
               {"slug": "s3", "datum": "2026-09-22", "titel": "T3", "beschreibung": "",
                "url": "/posts/s3/", "path": "", "pillar": "kaputt"}]
    pruefe(len(themen_filter(artikel, [])) == 3, "Themen: leere Auswahl = alles")
    pruefe(len(themen_filter(artikel, ["strom-sparen"])) == 1, "Themen: Filterung falsch")
    pruefe(len(themen_filter(artikel, ["geheim"])) == 0, "Themen: leere Gruppe")

    # E1: Idempotenz + F1: Sperre + G1: Journal-Hash (über _versand_liste
    #     mit monkeypatchten Worker/Transport – hermetisch, kein Netz).
    wq = os.path.join(tmp, "worker")
    os.makedirs(wq, exist_ok=True)
    pfad_state = os.path.join(wq, "data", "newsletter_state.json")
    os.makedirs(os.path.dirname(pfad_state), exist_ok=True)
    with open(pfad_state, "w", encoding="utf-8") as fh:
        json.dump({"pending": ["s1", "s2", "s3"], "versandene_artikel": []}, fh)
    # zustand_konfig liest das Studio-JSON – ohne JSON gilt der Default STATE_REL.
    pruefe(wq and os.path.isdir(wq), "Worker-Testbaum fehlt")

    konf_test = {"email": {"max_artikel": 5,
                           "absender": {"name": "F", "email": "news@franksfinanzcheck.de"},
                           "antwort_an": "k@franksfinanzcheck.de",
                           "versand": {"transport": "dryrun", "rat_pro_minute": 600},
                           "rechtliches": {"impressum_url": "https://franksfinanzcheck.de/impressum/",
                                           "datenschutz_url": "https://franksfinanzcheck.de/datenschutz/"}}}
    abonnten_test = [{"email": "eins@beispiel.de", "token": "t-1", "themen": [],
                      "bestaetigt": "2026-09-20T00:00:00Z"},
                     {"email": "zwei@beispiel.de", "token": "t-2", "themen": ["strom-sparen"],
                      "bestaetigt": "2026-09-20T00:00:00Z"},
                     {"email": "drei@beispiel.de", "token": "t-3", "themen": ["kaputt"],
                      "bestaetigt": "2026-09-20T00:00:00Z"}]

    # E1a: dry-run ohne Netz, ohne Worker – rc 0, State unverändert.
    rc = versende(wq, artikel, _mini_ausgabe(artikel), "2026-09-24", "Versprechen.",
                  dry_run=True, test_adresse="")
    pruefe(rc == 0, f"dry-run: rc {rc}")

    # E1b: LISTE mit gepatchtem Worker + Transport: Marken pro Token,
    #      Variante-QA-Gate, Idempotenz, Teilverband-Nachgang, Journal-Hash.
    #      Studio-Bau und QA werden gefaked (ihre Selftests testen sie selbst);
    #      geprüft wird der DIGEST-Entscheidweg: wer bekommt welche Ausgabe,
    #      was merkt sich der State, was steht im Journal.
    import types
    _modul = sys.modules[__name__]
    original_abfrage = versand.worker_abfrage
    original_sende = versand.sende_datei
    original_bau = _modul.baue_ausgabe
    original_qa = _modul.qa
    gesammelte: list[list[dict]] = []
    modus = {"rc": 0, "liefern": None}   # liefern=None → alle zugestellt

    def fake_bau(artikel_g, datum_g, versprechen_g, *, root=None):
        kaputt = any(a.get("pillar") == "kaputt" for a in artikel_g)
        html_g = ('<html><body>Variante <a href="{{unsubscribe}}">A</a> '
                  '<a href="{{update_profile}}">P</a> <a href="{{mirror}}">M</a></body></html>')
        return {"html": html_g, "text": "Variante {{unsubscribe}}",
                "betreff": ("QA-FALLEN " if kaputt else "Variante ") + datum_g,
                "preheader": "V", "anzahl": len(artikel_g), "blocks": [],
                "material": [{"slug": a["slug"], "titel": a["titel"]} for a in artikel_g]}

    def fake_qa_pruefe(email_g, *, konf=None, materiale=None, zustand=None, root=None):
        bestanden = "QA-FALLEN" not in (email_g.get("betreff") or "")
        return {"bestanden": bestanden, "score": 100 if bestanden else 0,
                "funde": [] if bestanden else [{"regel": "QX", "meldung": "geplant"}],
                "warnungen": [], "regeln_geprueft": 21}

    try:
        def fake_abfrage(pfad_g, param_g, *, base, key):
            pruefe(pfad_g == "/export/abonnenten", f"Worker-Pfad {pfad_g}")
            pruefe(base == "https://abos.franksfinanzcheck.de" and key == "key",
                   "Worker-Basis/Key falsch übergeben")
            return {"abonnenten": abonnten_test, "anzahl": len(abonnten_test)}

        def fake_sende(datei_g, root=None, env=None, konf=None, schlafen=None):
            with open(datei_g, encoding="utf-8") as fh:
                mit = json.load(fh)
            gesammelte.append(mit["empfaenger"])
            journal_g = os.path.join(root, "data", "newsletter_journal.jsonl")
            os.makedirs(os.path.dirname(journal_g), exist_ok=True)
            with open(journal_g, "a", encoding="utf-8") as fh:
                for p_g in mit["empfaenger"]:
                    zugestellt = modus["liefern"] is None or p_g["email"] in modus["liefern"]
                    fh.write(json.dumps({
                        "ts": "2026-09-24T12:00:00Z", "ausgabe": mit["ausgabe"],
                        "betreff": mit["betreff"],
                        "empfaenger": versand.hash16(p_g["email"]),
                        "status": "dryrun" if zugestellt else "hart",
                        "meldung": "dryrun" if zugestellt else "550"}) + "\n")
            return modus["rc"]

        versand.worker_abfrage = fake_abfrage
        versand.sende_datei = fake_sende
        _modul.baue_ausgabe = fake_bau
        _modul.qa = types.SimpleNamespace(pruefe=fake_qa_pruefe)
        os.environ["NEWSLETTER_WORKER_BASE"] = "https://abos.franksfinanzcheck.de"
        os.environ["NEWSLETTER_WORKER_EXPORT_KEY"] = "key"
        os.environ["NEWSLETTER_TRANSPORT"] = "dryrun"
        ausgabe_mini = _mini_ausgabe(artikel)

        # LAUF 1: kompletter Versand (Hauptvariante + Strom-Variante; „kaputt“
        # scheitert an der Variante-QA → deren Abonnent wird verschont).
        modus.update(rc=0, liefern=None)
        rc1 = _versand_liste(wq, artikel, ausgabe_mini["html"], ausgabe_mini["text"],
                             "Betreff Test", "Pre", "Versprechen.", konf_test, "2026-09-24")
        pruefe(rc1 == 0, f"Lauf 1 (komplett): rc {rc1}")
        pruefe(len(gesammelte) == 1 and len(gesammelte[0]) == 2,
               f"Lauf 1: Sendeliste {len(gesammelte[0]) if gesammelte else 0} ≠ 2")
        p1 = next(p for p in gesammelte[0] if p["email"] == "eins@beispiel.de")
        p2 = next(p for p in gesammelte[0] if p["email"] == "zwei@beispiel.de")
        pruefe("?token=t-1" in p1["html"], "Lauf 1: Abmeldelink ohne Token (eins)")
        pruefe("?token=t-2" in p2["html"], "Lauf 1: Abmeldelink ohne Token (zwei)")
        # „zwei“ bekam die THEMEN-VARIANTE (aus fake_bau), nicht die Haupt-
        # Ausgabe – Beweis, dass die Themenwahl eine eigene Ausgabe baute.
        pruefe("Variante" in p2["html"] and "Testausgabe" not in p2["html"],
               "Lauf 1: Themenwahl wirkte nicht – Haupt-Ausgabe statt Variante")
        pruefe("Testausgabe" in p1["html"], "Lauf 1: Haupt-Ausgabe falsch")
        state1 = lade_state(wq)
        pruefe(sorted(state1["letzte_ausgabe"]["versendet"]) ==
               sorted([versand.hash16("eins@beispiel.de"), versand.hash16("zwei@beispiel.de")]),
               "Lauf 1: State hat nicht alle Hashes")
        pruefe(sorted(state1["versandene_artikel"]) == ["s1", "s2", "s3"],
               f"Lauf 1: Artikel nicht übernommen: {state1.get('versandene_artikel')}")

        # LAUF 2: dieselbe Ausgabe erneut → alles übersprungen, kein Versand.
        gesammelte.clear()
        modus.update(rc=0, liefern=None)
        rc2 = _versand_liste(wq, artikel, ausgabe_mini["html"], ausgabe_mini["text"],
                             "Betreff Test", "Pre", "Versprechen.", konf_test, "2026-09-24")
        pruefe(rc2 == 0 and not gesammelte, "Lauf 2: Idempotenz fehlt – doppelt gesendet")

        # LAUF 3: neue Ausgabe, TEILVERSAND (nur „eins“ zugestellt).
        gesammelte.clear()
        modus.update(rc=1, liefern={"eins@beispiel.de"})
        rc3 = _versand_liste(wq, artikel, ausgabe_mini["html"], ausgabe_mini["text"],
                             "Betreff Zweite", "Pre", "Versprechen.", konf_test, "2026-09-25")
        pruefe(rc3 == 1, f"Lauf 3 (Teilverband): rc {rc3}")
        state3 = lade_state(wq)
        pruefe(state3["letzte_ausgabe"]["datum"] == "2026-09-25"
               and state3["letzte_ausgabe"]["versendet"]
               == [versand.hash16("eins@beispiel.de")],
               "Lauf 3: Teilverband-Zustand falsch")

        # LAUF 4: NACHGANG derselben Ausgabe → nur der Rest („zwei“).
        gesammelte.clear()
        modus.update(rc=0, liefern=None)
        rc4 = _versand_liste(wq, artikel, ausgabe_mini["html"], ausgabe_mini["text"],
                             "Betreff Zweite", "Pre", "Versprechen.", konf_test, "2026-09-25")
        pruefe(rc4 == 0, f"Lauf 4 (Nachgang): rc {rc4}")
        pruefe(len(gesammelte) == 1
               and [p["email"] for p in gesammelte[0]] == ["zwei@beispiel.de"],
               f"Lauf 4: Nachgang traf {gesammelte[0] if gesammelte else 'niemanden'}")
        state4 = lade_state(wq)
        pruefe(sorted(state4["letzte_ausgabe"]["versendet"]) ==
               sorted([versand.hash16("eins@beispiel.de"), versand.hash16("zwei@beispiel.de")]),
               "Lauf 4: Endzustand unvollständig (Double-Send droht)")

        # G1: Journal enthält Hash, keine Roh-Adresse.
        journal = os.path.join(wq, "data", "newsletter_journal.jsonl")
        pruefe(os.path.exists(journal), "Journal fehlt")
        roh = open(journal, encoding="utf-8").read()
        pruefe("eins@beispiel.de" not in roh, "Journal: Roh-Adresse gelakt!")
        pruefe(versand.hash16("eins@beispiel.de") in roh, "Journal: Hash fehlt")
    finally:
        versand.worker_abfrage = original_abfrage
        versand.sende_datei = original_sende
        _modul.baue_ausgabe = original_bau
        _modul.qa = original_qa
        os.environ.pop("NEWSLETTER_WORKER_BASE", None)
        os.environ.pop("NEWSLETTER_WORKER_EXPORT_KEY", None)
        os.environ.pop("NEWSLETTER_TRANSPORT", None)

    # F1: Sperre setzt, liest, hebt.
    sperre_setzen(wq, "kennung-test", "Betreff Test")
    meldung = sperre_pruefen(wq)
    pruefe("versand_unklar" in meldung and "kennung-test" in meldung, "Sperre: nicht lesbar")
    state = lade_state(wq)
    state.pop("versand_unklar", None)
    speichere_state(wq, state)
    pruefe(sperre_pruefen(wq) == "", "Sperre: nicht auflösbar")

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"✅ newsletter_digest Selftest: {pruefungen} Fälle grün "
          "(Capture-Wache, Marken, Testadressen, Themen, Idempotenz, Sperre, Journal).")
    return 0


def _mini_ausgabe(artikel: list[dict]) -> dict:
    """Winzige Ausgabe für den Selftest OHNE Studio-JSON/Bau:
    Marken drin, Material drin – genug für den Versandweg."""
    html = ('<html><body>Testausgabe <a href="{{unsubscribe}}">Abmelden</a> '
            '<a href="{{update_profile}}">Profil</a></body></html>')
    text = "Testausgabe · Abmelden: {{unsubscribe}} · Profil: {{update_profile}}"
    return {"html": html, "text": text, "betreff": "Betreff Test",
            "preheader": "Pre", "anzahl": len(artikel), "blocks": [],
            "material": [{"slug": a["slug"], "titel": a["titel"]} for a in artikel]}


if __name__ == "__main__":
    sys.exit(main())
