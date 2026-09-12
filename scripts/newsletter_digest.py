#!/usr/bin/env python3
"""newsletter_digest.py – Capture-Prüfung und Wochen-/Tagesdigest des Newsletters.

WARUM (Premium-Audit 12.09.2026, Empfehlung 1 – der größte Hebel):
Ein Blog ohne Liste vermietet seine Reichweite an Pinterest, Google und Awin.
FranksFinanzcheck schrieb 31 Artikel, sammelte aber null Adressen: das
Newsletter-Feld in `hugo.toml` war leer, der Footer-Block in
`extend_footer.html` hängt an genau diesem Feld – unsichtbar, folgenlos, grün.
Gleichzeitig dokumentierte `docs/ANLEITUNG-NEWSLETTER.md` einen Versandworkflow
`Newsletter-AI` und eine `NEWSLETTER-STATUS.md`, die es nie gab. Die Lücke war
also nicht „nur" eine fehlende Funktion, sondern eine dokumentierte, die niemand
vermisste, weil sie nirgends rot wurde.

Dieses Skript schließt beide Seiten der Lücke:

  --check   Die Capture-Kette wird geprüft, nicht beworben. Ein Formular, das
            nirgends verlinkt ist, eine Landingpage ohne Double-Optin-Hinweis,
            ein Datenschutzhinweis, der den Widerruf nicht beschreibt, oder ein
            http-Endpunkt für Adressdaten sind Funde. Leerzustand ist erlaubt –
            er muss aber laut als INERT gemeldet werden, damit „keine Anmeldung"
            nie mit „alles in Ordnung" verwechselt wird (--strict-inert macht
            daraus einen Fehler, für Läufe, die senden wollen).

  --build   Baut den Digest aus den Live-Artikeln seit `--days` Tagen
            (HTML + Text, {unsubscribe}-Marke, ohne bereits versendete Artikel).

  --send    Übergibt den Digest an Brevo (v3: Kampagne anlegen → sendNow, oder
            sendTest an eine Testadresse). Bewusst dreifach verriegelt:
            API-Key + Listen-ID als Secrets, `NEWSLETTER_SEND=ja` als
            Eingeständnis, dass echte Postfächer getroffen werden, und ohne
            beides passiert kein Netzwerkzugriff. Kein Testversand ohne
            `--test-adresse`.

  --selftest Selbsttest, ohne Netzwerk, ohne Schreibzugriff auf den Bestand.

Nutzung:
    python3 scripts/newsletter_digest.py --check
    python3 scripts/newsletter_digest.py --check --strict-inert --json
    python3 scripts/newsletter_digest.py --build --days 1
    python3 scripts/newsletter_digest.py --build --days 1 --send --test-adresse frank@beispiel.de
    python3 scripts/newsletter_digest.py --selftest

Exit: 0 = ok oder INERT · 1 = Befund/Abbruch · 2 = Fehler
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
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_REL = os.path.join("data", "newsletter_state.json")
LANDING_REL = os.path.join("content", "newsletter", "index.md")
SHORTCODE_REL = os.path.join("layouts", "shortcodes", "newsletter_form.html")
FOOTER_REL = os.path.join("layouts", "_partials", "extend_footer.html")
WORKFLOW_REL = os.path.join(".github", "workflows", "newsletter-daily.yml")
ERLAUBTE_HOSTS = ("brevo.com", "sendinblue.com", "franksfinanzcheck.de")
FELDNAME = "email"


# ------------------------------------------------------------------ Grundbausteine
def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def params(root: str) -> dict:
    """Die drei Newsletter-Parameter aus hugo.toml, ohne Hugo-Abhängigkeit.

    Geparst wird die TOML-Insel, nicht die ganze Datei: Hugo 0.164 würde für
    einen echten Leservorgang einen Build verlangen, und die Wache soll auch
    ohne public/-Ausgabe urteilen können.
    """
    toml = _read(os.path.join(root, "hugo.toml"))
    out = {}
    for key in ("newsletterFormUrl", "newsletterFormAction", "newsletterPromise"):
        m = re.search(r'(?m)^\s*' + key + r'\s*=\s*"([^"]*)"', toml)
        out[key] = (m.group(1).strip() if m else "")
    return out


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
                    "path": os.path.relpath(idx, root)})
    return sorted(out, key=lambda a: a["datum"], reverse=True)


def lade_state(root: str) -> dict:
    try:
        return json.loads(_read(os.path.join(root, STATE_REL)) or "{}")
    except json.JSONDecodeError:
        return {}


def speichere_state(root: str, state: dict) -> None:
    pfad = os.path.join(root, STATE_REL)
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


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
    # Markdown-Quelle: Abschnitt = Zeilen bis zur nächsten gleichrangigen
    # oder höheren Überschrift.
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
    # Ein Newsletter-Abschnitt gilt als vorhanden, wenn eine Überschrift ihn nennt.
    # Ein Anker (`id="newsletter"`) wird nicht verlangt – verlinkt wird ohne
    # Fragment, damit der Link trägt, auch wenn die Ziffer der Überschrift wandert.
    ds_abschnitt = _ds_abschnitt(ds, ds_herkunft)
    ds_widerspruch = bool(re.search("(?i)(derzeit|zurzeit|aktuell) keinen newsletter"
                                    "|bietet[^.]{0,60}keinen newsletter", ds))
    ds_platz = _platzhalter(ds_abschnitt)

    if not action and not url:
        # Leerzustand ist erlaubt, aber er darf keine leeren Versprechen erzeugen.
        if ds_herkunft == "fehlend":
            funde.append(("N7", "die Datenschutzerklärung existiert weder gebaut "
                                "(public/) noch als Quelle (content/) – die Prüfung "
                                "ist ausgefallen, nicht bestanden", "ds-fehlt"))
        if ds_widerspruch:
            # Noch kein Fund: solange kein Formular läuft, ist „bietet derzeit
            # keinen Newsletter an" die Wahrheit. Der Widerspruch entsteht erst mit
            # der Freischaltung – deshalb steht er als Hinweis da, mit dem Satz,
            # der dann geändert werden muss (Vorlage in docs/).
            note.append(("N7", "die Datenschutzerklärung erklärt ausdrücklich, es "
                               "gäbe keinen Newsletter – bei Freischaltung des "
                               "Formulars wird daraus ein Widerspruch; vorher "
                               "ersetzen (docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md)",
                        "ds-widerspruch-vorstudie"))
        if ds_platz:
            funde.append(("N7", _platzhalter_meldung(ds_platz), "ds-platzhalter"))
        wirbt = [f for f in glob.glob(os.path.join(pub, "**", "index.html"), recursive=True)
                 if re.search(r"Newsletter abonnieren|Newsletter-Anmeldung", _read(f))]
        if wirbt or "newsletter-footer" in footer:
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
                               f"erlaubten Absender ({', '.join(ERLAUBTE_HOSTS)}) – "
                               "prüfen, ob das die eigene Formularhost-Domain ist",
                        "form-host"))
        if re.search(r"(TODO|BEISPIEL|example|<|\{\{)", action, re.I):
            funde.append(("N2", "Formular-Endpunkt enthält Platzhalter-Müll", "form-platzhalter"))
    if url:
        u = urllib.parse.urlsplit(url)
        if u.scheme != "https":
            funde.append(("N3", f"gehostetes Formular über {u.scheme or 'http'}", "url-http"))
        if url.rstrip("/") in ("", "/", "https://franksfinanzcheck.de"):
            funde.append(("N3", "newsletterFormUrl zeigt auf die Site selbst – "
                                "Button und Zielseite sind dasselbe, die Anmeldung "
                                "verpufft im Kreis", "url-selbstbezug"))

    #shortcode und Seite müssen zueinander passen
    sc = _read(os.path.join(root, SHORTCODE_REL))
    if not sc:
        funde.append(("N4", f"fehlend: {SHORTCODE_REL} – ohne Shortcode zeigt die "
                            "Landingpage kein Feld", "shortcode-fehlt"))
    elif action and f'name="{FELDNAME}"' not in sc:
        funde.append(("N4", f"Inline-Formular POSTet ohne Feld `{FELDNAME}` – "
                            "Brevo und Konsorten lesen die Adresse aus genau diesem "
                            "Namen", "feldname"))
    if not seite:
        funde.append(("N5", "Landingpage /newsletter/ ist nicht gebaut – Inhalt "
                            "fehlt oder Build veraltet", "landingpage-fehlt"))
    else:
        for marke, grund, code in (
                ("Double-Opt", "kein Double-Opt-In-Hinweis – ohne den ist die "
                 "Anmeldung nach DSGVO unzulässig beworben", "doi-fehlt"),
                ("/datenschutz/", "kein Link zu den Datenschutzhinweisen an der "
                 "Anmeldestelle – ohne den Verweis ist die Einwilligung nicht "
                 "informiert (ohne Fragment verlinken: die Überschrift hat keinen "
                 "eigenen Anker, ein erdachtes #newsletter inszeniert einen Sprung "
                 "ins Leere)", "datenschutz-link")):
            if marke not in seite:
                funde.append(("N5", grund, code))
        if action and "<form" not in seite:
            funde.append(("N5", "Formular-Endpunkt gesetzt, aber die Seite zeigt "
                                "kein <form> – Shortcode-Zweig nicht erreicht?", "kein-form"))
    if "newsletter-footer" not in footer:
        funde.append(("N6", "Capture konfiguriert, aber im Footer nirgends verlinkt "
                            "– die Liste wächst nie, weil niemand den Weg sieht",
                      "cta-versteckt"))
    if ds_herkunft == "fehlend":
        funde.append(("N7", "die Datenschutzerklärung existiert weder gebaut "
                            "(public/) noch als Quelle (content/datenschutz/index.md) "
                            "– die Prüfung ist ausgefallen, nicht bestanden",
                      "ds-fehlt"))
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
        if "BREVO_API_KEY" not in wf:
            funde.append(("N8", "Workflow existiert, liest aber BREVO_API_KEY nicht "
                               "– der Versand wäre für immer leer", "workflow-blind"))
        if "--strict-inert" not in wf:
            note.append(("N8", "Workflow prüft den Leerzustand nicht laut "
                               "(--strict-inert) – ein inaktiver Versand bliebe "
                               "unsichtbar", "workflow-leise"))
    zustand = "kaputt" if funde else "aktiv"
    return funde, note, zustand


# -------------------------------------------------------------------------- Digest
def baue_digest(artikel: list[dict], datum: str, versprechen: str) -> tuple[str, str, int]:
    if not artikel:
        return "", "", 0
    betreff = (f"FranksFinanzcheck: {artikel[0]['titel']}" if len(artikel) == 1 else
               f"FranksFinanzcheck: {len(artikel)} Sparechnungen für {datum}")
    stuecke_h, stuecke_t = [], []
    for a in artikel:
        titel = a["titel"].replace("&", "&amp;").replace("<", "&lt;")
        text = (a["beschreibung"] or "Rechnung im Artikel öffnen.").replace("<", "&lt;")
        url = a["url"] if a["url"].startswith("http") else "https://franksfinanzcheck.de" + a["url"]
        stuecke_h.append(
            f'<tr><td style="padding:14px 18px;font-family:Georgia,serif;">'
            f'<h2 style="margin:0 0 6px;font-size:19px;line-height:1.3;">'
            f'<a href="{url}" style="color:#0f6049;text-decoration:none;">{titel}</a></h2>'
            f'<p style="margin:0;color:#3c4a56;font-size:15px;line-height:1.5;">{text}</p>'
            f'<p style="margin:8px 0 0;"><a href="{url}" style="font-weight:700;'
            f'color:#0f6049;">Rechnung öffnen →</a></p></td></tr>')
        stuecke_t.append(f"* {a['titel']}\n  {url}\n  {text}")
    html = ("<!doctype html><html lang=\"de\"><meta charset=\"utf-8\">"
            f"<body style=\"margin:0;background:#f4f6f8;\"><table role=presentation "
            f"width=100% cellpadding=0 cellspacing=0 style=\"max-width:620px;"
            f"margin:0 auto;background:#fff;\">"
            f"<tr><td style=\"padding:18px;border-bottom:1px solid #e5e9ed;\">"
            f"<strong style=\"font-size:17px;\">FranksFinanzcheck</strong>"
            f"<div style=\"color:#5a6a78;font-size:13px;\">{versprechen} · {datum}</div></td></tr>"
            + "".join(stuecke_h) +
            "<tr><td style=\"padding:16px 18px;border-top:1px solid #e5e9ed;"
            "color:#5a6a78;font-size:12px;\">Du erhältst diese Mail, weil du dich auf "
            "franksfinanzcheck.de mit Double-Opt-In angemeldet hast. "
            "<a href=\"{unsubscribe}\">Abmelden</a></td></tr></table></body></html>")
    text = (f"FranksFinanzcheck – {versprechen}\n{datum}\n\n"
            + "\n\n".join(stuecke_t)
            + "\n\n---\nAbmelden: {unsubscribe}\n"
              "Angemeldet über franksfinanzcheck.de/newsletter/ (Double-Opt-In).")
    return html, text, len(artikel)


# ---------------------------------------------------------------------- Brevo-Transport
def brevo(api_key: str, pfad: str, payload: dict) -> tuple[int, str]:
    req = urllib.request.Request(
        "https://api.brevo.com/v3/" + pfad.lstrip("/"),
        data=json.dumps(payload).encode("utf-8"),
        headers={"api-key": api_key, "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", "replace")[:400]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:400]
    except Exception as exc:  # noqa: BLE001
        return 0, f"{exc.__class__.__name__}: {exc}"


TRANSPORT = brevo      # für den Selbsttest austauschbar – dann trifft kein Netz


# ---------------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    import shutil
    import tempfile
    fehler: list = []
    zaehler = 0

    def pruefe(bedingung: bool, meldung: str) -> None:
        nonlocal zaehler
        if bedingung:
            zaehler += 1
        else:
            fehler.append(meldung)

    HEUTE_FIX = datetime.date.today()
    tmp = tempfile.mkdtemp(prefix="newsletter-selftest-")
    global TRANSPORT
    aufgerufen: list = []
    try:
        def baum(root: str, params_toml: str, *, seite_extra: str = "",
                 footer_extra: str = "newsletter-CTA", datenschutz: str = "",
                 workflow: str = "x", artikel: list | None = None,
                 ds_md: str = ""):
            os.makedirs(os.path.join(root, "layouts", "shortcodes"), exist_ok=True)
            os.makedirs(os.path.join(root, "public", "newsletter"), exist_ok=True)
            os.makedirs(os.path.join(root, "public", "datenschutz"), exist_ok=True)
            os.makedirs(os.path.join(root, "content", "posts"), exist_ok=True)
            os.makedirs(os.path.join(root, "data"), exist_ok=True)
            with open(os.path.join(root, "hugo.toml"), "w", encoding="utf-8") as fh:
                fh.write("[params]\n" + params_toml)
            shutil.copy(os.path.join(BLOG_DIR, SHORTCODE_REL),
                        os.path.join(root, SHORTCODE_REL))
            landing = ('<div class="ff-newsletter">Double-Opt-In nötig. '
                       '<a href="/datenschutz/#newsletter">Datenschutz</a>'
                       + seite_extra + "</div>")
            if seite_extra == "KEINE_SEITE":
                landing = ""
            with open(os.path.join(root, "public", "newsletter", "index.html"),
                      "w", encoding="utf-8") as fh:
                fh.write(landing)
            with open(os.path.join(root, "public", "index.html"), "w", encoding="utf-8") as fh:
                fh.write("<html><footer>" + footer_extra + "</footer></html>")
            with open(os.path.join(root, "public", "datenschutz", "index.html"),
                      "w", encoding="utf-8") as fh:
                fh.write(datenschutz)
            with open(os.path.join(root, WORKFLOW_REL), "w", encoding="utf-8") as fh:
                fh.write(workflow)
            for slug, dat, draft in (artikel or []):
                d = os.path.join(root, "content", "posts", slug)
                os.makedirs(d, exist_ok=True)
                with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as fh:
                    fh.write(f"---\ntitle: {slug}\ndate: {dat}\n"
                             f"description: Beschreibung {slug}\ndraft: {draft}\n---\nText\n")
            if ds_md:
                d = os.path.join(root, "content", "datenschutz")
                os.makedirs(d, exist_ok=True)
                with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as fh:
                    fh.write(ds_md)

        # 1–3) INERT: nichts konfiguriert, nirgends wird geworben
        r1 = os.path.join(tmp, "inert")
        os.makedirs(os.path.join(r1, ".github", "workflows"), exist_ok=True)
        baum(r1, "", footer_extra="", datenschutz="<p>Newsletter: Widerruf jederzeit.</p>")
        f, n, z = pruefe_capture(r1)
        pruefe(z == "inert", f"Leerzustand meldet {z} statt inert: {f} {n}")
        pruefe(not f, f"Leerzustand meldet Funde: {f}")
        pruefe(any(x[2] == "inert" for x in n), "Leerzustand meldet den Code inert nicht")

        # 4) totes Versprechen: wirbt, aber kein Weg konfiguriert
        with open(os.path.join(r1, "public", "index.html"), "w", encoding="utf-8") as fh:
            fh.write("<html>Jetzt Newsletter abonnieren</html>")
        f2, _, z2 = pruefe_capture(r1)
        pruefe(any(c == "config-widerspruch" for _, _, c in f2),
               f"toter Werbe-Link ohne Anmeldung bleibt unsichtbar: {f2}")

        # 5–7) http-Endpunkt + Rechtstext nirgends -> Funde, kein Grün
        r3 = os.path.join(tmp, "kaputt")
        os.makedirs(os.path.join(r3, ".github", "workflows"), exist_ok=True)
        baum(r3, 'newsletterFormAction = "http://form.example.de/x"\n',
             datenschutz="")
        f3, _, z3 = pruefe_capture(r3)
        codes = {c for _, _, c in f3}
        pruefe("form-http" in codes,
               f"http-Endpunkt meldet form-http nicht: {sorted(codes)}")
        pruefe("ds-fehlt" in codes,
               f"Rechtstext weder gebautes HTML noch Quelle meldet ds-fehlt "
               f"nicht (ausgefallen ist nicht bestanden): {sorted(codes)}")
        pruefe(z3 == "kaputt", f"Zustand nach Funden nicht kaputt: {z3}")

        # 8–9) saubere Kette: https, Feldname, DOI, Rechtstext, CTA, Workflow
        r4 = os.path.join(tmp, "gut")
        os.makedirs(os.path.join(r4, ".github", "workflows"), exist_ok=True)
        baum(r4, 'newsletterFormAction = "https://l.brevo.com/landing/x"\n'
                 'newsletterPromise = "Eine Mail pro Werktag."\n',
             artikel=[("2026-09-11-neu-1", HEUTE_FIX - datetime.timedelta(days=1), "false"),
                      ("2026-01-01-alt-1", datetime.date(2026, 1, 1), "false"),
                      ("2026-09-11-draft-1", HEUTE_FIX, "true")],
             seite_extra='<form action="https://l.brevo.com/landing/x"><input name="email">',
             datenschutz='<h2 id="newsletter">Newsletter</h2>'
                         '<p>Double-Opt-In, Widerruf formlos, Loeschung 30 Tage.</p>',
             workflow="BREVO_API_KEY\n--strict-inert\n",
             footer_extra="newsletter-footer")
        f4, n4, z4 = pruefe_capture(r4)
        pruefe(not f4, f"saubere Kette meldet Funde: {f4}")
        pruefe(z4 == "aktiv", f"gesunde Kette gilt nicht als aktiv: {z4}")

        # 10–11) Quell-Fallback: kein Build (public/-Seite weg), Markdown trägt
        r5 = os.path.join(tmp, "quelle")
        os.makedirs(os.path.join(r5, ".github", "workflows"), exist_ok=True)
        baum(r5, 'newsletterFormAction = "https://l.brevo.com/landing/x"\n',
             datenschutz="",
             ds_md="## 8. Newsletter\n\nAnmeldung über [die Anmeldeseite]"
                   "(/newsletter/), Double-Opt-In, Widerruf formlos.\n")
        os.remove(os.path.join(r5, "public", "datenschutz", "index.html"))
        f5, _, z5 = pruefe_capture(r5)
        codes5 = {c for _, _, c in f5}
        pruefe(not ({"ds-fehlt", "rechtstext", "ds-leer"} & codes5),
               f"Quell-Fallback liest den Rechtstext aus content/ nicht: "
               f"{sorted(codes5)}")
        pruefe("ds-platzhalter" not in codes5,
               f"Markdown-Link wird als Platzhalter geschrien: {sorted(codes5)}")

        # 12) Platzhalter-Rest im Live-Text -> Fund ds-platzhalter
        r6 = os.path.join(tmp, "platzhalter")
        os.makedirs(os.path.join(r6, ".github", "workflows"), exist_ok=True)
        baum(r6, 'newsletterFormAction = "https://l.brevo.com/landing/x"\n',
             datenschutz="",
             ds_md="## 8. Newsletter\n\nSpeicherdauer: [30] Tage, Widerruf an "
                   "[deine Adresse].\n")
        os.remove(os.path.join(r6, "public", "datenschutz", "index.html"))
        f6, _, z6 = pruefe_capture(r6)
        codes6 = {c for _, _, c in f6}
        pruefe("ds-platzhalter" in codes6,
               f"Platzhalter-Rest im Live-Text meldet ds-platzhalter nicht: "
               f"{sorted(codes6)}")

        # 13) Überschrift da, Abschnitt leer -> eigener Befund, kein rechtstext
        r7 = os.path.join(tmp, "leer")
        os.makedirs(os.path.join(r7, ".github", "workflows"), exist_ok=True)
        baum(r7, 'newsletterFormAction = "https://l.brevo.com/landing/x"\n',
             datenschutz='<h2 id="newsletter">Newsletter</h2>')
        f7, _, z7 = pruefe_capture(r7)
        codes7 = {c for _, _, c in f7}
        pruefe("ds-leer" in codes7 and "rechtstext" not in codes7,
               f"halbfertiger Abschnitt und fehlende Überschrift fallen "
               f"zusammen: {sorted(codes7)}")

        # 14–16) Digest-Bau + Duplikat-Schutz über den State
        heute = datetime.date.today()
        artikel = live_artikel(r4, heute - datetime.timedelta(days=3))
        pruefe([a["slug"] for a in artikel] == ["2026-09-11-neu-1"],
               f"Digest-Auswahl falsch: {[a['slug'] for a in artikel]}")
        html, text, anzahl = baue_digest(artikel, heute.isoformat(), "Eine Mail/Tag")
        pruefe(anzahl == 1 and "neu-1" in html and "{unsubscribe}" in text
               and "Rechnung öffnen" in html,
               f"Digest-Inhalt unvollständig ({anzahl})")
        leeren = baue_digest([], heute.isoformat(), "x")
        pruefe(leeren[2] == 0 and not leeren[0],
               "Digest ohne Artikel erzeugt leere Mail")

        # 17–19) Versand-Verriegelung: ohne Bestätigung und ohne Key kein Netz
        def spy(api_key, pfad, payload):
            aufgerufen.append((api_key, pfad))
            return 201, '{"id": 42}'
        TRANSPORT = spy
        rc = versende(r4, html, text, "FranksFinanzcheck", dry_run=True)
        pruefe(not aufgerufen and rc == 0, f"--dry-run fasst das Netz an (rc={rc})")
        aufgerufen.clear()
        rc2 = versende(r4, html, text, "X", dry_run=False, test_adresse="")
        pruefe(not aufgerufen and rc2 != 0,
               "Versand ohne Secrets/Bestätigung berührt das Netz oder meldet Erfolg")
        speichere_state(r4, {"pending": [a["slug"] for a in artikel]})
        os.environ["BREVO_API_KEY"] = "key"
        os.environ["BREVO_LIST_ID"] = "7"
        os.environ["NEWSLETTER_SEND"] = "ja"
        rc3 = versende(r4, html, text, "X", dry_run=False)
        state = lade_state(r4)
        pruefe(bool(aufgerufen) and rc3 == 0
               and state.get("versandene_artikel", [])[-1:] == ["2026-09-11-neu-1"],
               f"verscharfter Versand läuft nicht durch (rc={rc3}): {state}")
        TRANSPORT = brevo
    except Exception as exc:  # noqa: BLE001
        import traceback
        fehler.append(f"Ausführung: {exc.__class__.__name__}: {exc}\n"
                      + traceback.format_exc()[-500:])
    finally:
        TRANSPORT = brevo
        for k in ("BREVO_API_KEY", "BREVO_LIST_ID", "NEWSLETTER_SEND"):
            os.environ.pop(k, None)
        shutil.rmtree(tmp, ignore_errors=True)
    if fehler:
        print("🛑 newsletter_digest-Selbsttest FEHLGESCHLAGEN:")
        for e in fehler:
            print("  -", e)
        return 2
    print(f"✅ Newsletter-Selbsttest: {zaehler} Fälle grün (INERT, totes "
          f"Versprechen, http + ds-fehlt, saubere Kette, Quell-Fallback, "
          f"Platzhalter, halbfertiger Abschnitt, Digest, Versand-Verriegelung).")
    return 0


# ------------------------------------------------------------------------- Versand
def versende(root: str, html: str, text: str, betreff: str, *, dry_run: bool,
             test_adresse: str = "") -> int:
    """Kampagne bei Brevo anlegen und senden. Dreifach verriegelt, s. Dokumentation."""
    key = os.environ.get("BREVO_API_KEY", "").strip()
    liste = os.environ.get("BREVO_LIST_ID", "").strip()
    bestaetigt = os.environ.get("NEWSLETTER_SEND", "").strip().lower() in ("ja", "true", "1")
    if dry_run:
        print("   ℹ️  dry-run: keine Netzwerk- Anfrage, Kampagne würde so aussehen: "
              f"Betreff {betreff!r}, Liste {liste or '—'}, {len(html)} Zeichen HTML")
        return 0
    if not key or not liste:
        print("   ❌ kein Versand: Secrets BREVO_API_KEY / BREVO_LIST_ID fehlen. "
              "Der Digest bleibt lokal – lieber nichts senden als ins Leere.")
        return 1
    if not bestaetigt and not test_adresse:
        print("   ❌ kein Versand: NEWSLETTER_SEND=ja fehlt. Echte Listen werden nur "
              "bestätigt getroffen; für Probeläufe --test-adresse nutzen.")
        return 1
    payload = {"name": f"Digest {datetime.date.today().isoformat()}",
               "subject": betreff, "htmlContent": html, "textContent": text,
               "sender": {"name": "FranksFinanzcheck",
                         "email": os.environ.get("NEWSLETTER_ABSENDER",
                                                 "news@franksfinanzcheck.de")},
               "recipients": {"listIds": [int(liste)]},
               "status": "draft", "preheader": betreff[:90]}
    code, antwort = TRANSPORT(key, "emailCampaigns", payload)
    if code not in (200, 201):
        print(f"   ❌ Kampagne nicht angelegt (HTTP {code}): {antwort[:200]}")
        return 1
    try:
        kennung = json.loads(antwort).get("id")
    except json.JSONDecodeError:
        kennung = None
    if not kennung:
        print(f"   ❌ Antwort ohne Kampagnen-ID: {antwort[:200]}")
        return 1
    pfad = (f"emailCampaigns/{kennung}/sendTest" if test_adresse
            else f"emailCampaigns/{kennung}/sendNow")
    body = {"emailTo": test_adresse} if test_adresse else {}
    code2, antwort2 = TRANSPORT(key, pfad, body)
    if code2 not in (200, 201, 202, 204):
        print(f"   ❌ Versand fehlgeschlagen (HTTP {code2}): {antwort2[:200]}")
        return 1
    print(f"   ✅ {'Testversand an ' + test_adresse if test_adresse else 'Versand angestoßen'}"
          f" (Kampagne {kennung})")
    state = lade_state(root)
    state.update({"zuletzt_versandt": datetime.datetime.now(datetime.timezone.utc)
                  .isoformat(timespec="seconds"),
                  "kampagne_id": kennung})
    if not test_adresse:
        neu = state.get("versandene_artikel", [])
        for slug in state.get("pending", []):
            if slug not in neu:
                neu.append(slug)
        state["versandene_artikel"] = sorted(neu)[-400:]
        state.pop("pending", None)
    speichere_state(root, state)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Newsletter-Capture-Wache + Digest")
    ap.add_argument("--root", default=BLOG_DIR)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--strict-inert", action="store_true",
                    help="Leerzustand als Fehler (für Läufe, die senden wollen)")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--live", action="store_true",
                    help="wirklich senden (sonst dry-run, auch mit --send)")
    ap.add_argument("--test-adresse", default="")
    ap.add_argument("--days", type=int, default=1)
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

    heute = datetime.date.today()
    state = lade_state(root)
    schon = set(state.get("versandene_artikel", []))
    artikel = [a for a in live_artikel(root, heute - datetime.timedelta(days=max(1, args.days)))
               if a["slug"] not in schon]
    p = params(root)
    html, text, anzahl = baue_digest(artikel, heute.isoformat(),
                                    p.get("newsletterPromise") or "Die Sparechnungen des Tages.")
    if anzahl == 0:
        print("📬 Digest: nichts zu senden – seit dem letzten Lauf ist nichts Neues "
              "erschienen (oder alles wurde schon versandt).")
        return rc_gesamt
    # Bewusst NICHT unter public/: ein gebauter Digest enthält die Brevo-Marke
    # {unsubscribe}, und die liegt sonst als „Link" im Auslieferungszustand – wo
    # er einen defekten internen Link markschiert und im schlimmsten Fall als
    # Newsletter-Ausgabe im Index landete. CI schreibt nach /tmp (siehe Workflow).
    out_dir = args.out or os.path.join(tempfile.gettempdir(), "ff-newsletter")
    os.makedirs(out_dir, exist_ok=True)
    for ende, inhalt in (("html", html), ("txt", text)):
        with open(os.path.join(out_dir, f"digest-{heute.isoformat()}.{ende}"),
                  "w", encoding="utf-8") as fh:
            fh.write(inhalt)
    betreff = re.sub(r"^FranksFinanzcheck:\s*", "FranksFinanzcheck: ",
                     (f"FranksFinanzcheck: {artikel[0]['titel']}" if anzahl == 1 else
                      f"FranksFinanzcheck: {anzahl} Sparechnungen für {heute.isoformat()}"))
    print(f"📬 Digest gebaut: {anzahl} Artikel → {out_dir}/digest-{heute.isoformat()}.html")
    for a in artikel[:8]:
        print(f"   • {a['titel'][:66]} ({a['datum']})")
    state["pending"] = [a["slug"] for a in artikel]
    speichere_state(root, state)
    if args.send:
        rc_gesamt = max(rc_gesamt, versende(root, html, text, betreff,
                                            dry_run=not args.live,
                                            test_adresse=args.test_adresse))
    else:
        print("   (kein Versand – --send fehlt; gebaute Digeste bleiben bewusst lokal)")
    return rc_gesamt


if __name__ == "__main__":
    sys.exit(main())
