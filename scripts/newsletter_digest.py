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
            Eingeständnis, dass die LISTE getroffen wird, und ohne beides
            passiert kein Netzwerkzugriff. Kein Testversand ohne
            `--test-adresse`. Ein Testversand (`--send --test-adresse X`,
            auch ohne `--live`) ist dagegen sofort real: er ist eine echte
            Mail an genau eine eingegebene Adresse (sendTest, nie sendNow)
            und zahlt sich deshalb nicht als Ausgabe in den Duplikatschutz
            ein. `--send` ALLEIN bleibt eine Vorschau (dry-run).

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
import time
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(BLOG_DIR, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
import newsletter_studio as studio      # noqa: E402  (Marke, Blöcke, Layout – eine Quelle)
import newsletter_qa as qa             # noqa: E402  (Vor-Versand-Prüfung, blockiert den Live-Versand)

STATE_REL = os.path.join("data", "newsletter_state.json")
LANDING_REL = os.path.join("content", "newsletter", "index.md")
SHORTCODE_REL = os.path.join("layouts", "shortcodes", "newsletter_form.html")
FOOTER_REL = os.path.join("layouts", "_partials", "extend_footer.html")
WORKFLOW_REL = os.path.join(".github", "workflows", "newsletter-daily.yml")
ERLAUBTE_HOSTS = ("brevo.com", "sendinblue.com", "sibforms.com", "franksfinanzcheck.de")
FELDNAME = "email"


# ------------------------------------------------------------------ Grundbausteine
def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


def params(root: str) -> dict:
    """Die drei Newsletter-Parameter – aus hugo.toml ODER data/newsletter_studio.json.

    Geparst wird die TOML-Insel, nicht die ganze Datei: Hugo 0.164 würde für
    einen echten Leservorgang einen Build verlangen, und die Wache soll auch
    ohne public/-Ausgabe urteilen können.

    Der Grund für die zweite Quelle: hugo.toml ist durch `data/integrity_lock.json`
    als KRITISCH versiegelt (Integritäts-Guard) – jede Änderung braucht eine
    menschliche Signatur. Der Anmeldeweg liegt deshalb zusätzlich im Studio-
    JSON, das der Betreiber füllen kann, ohne das Siegel zu berühren. Präzedenz
    hugo.toml > JSON, exakt wie in layouts/shortcodes/newsletter_form.html: ein
    Zustand, zwei Orte, eine Reihenfolge.
    """
    toml = _read(os.path.join(root, "hugo.toml"))
    out = {}
    for key in ("newsletterFormUrl", "newsletterFormAction", "newsletterPromise"):
        m = re.search(r'(?m)^\s*' + key + r'\s*=\s*"([^"]*)"', toml)
        out[key] = (m.group(1).strip() if m else "")
    studium = studio.capture(root)
    if not out["newsletterFormAction"]:
        out["newsletterFormAction"] = studium["form_action"]
    if not out["newsletterFormUrl"]:
        out["newsletterFormUrl"] = studium["form_url"]
    if not out["newsletterPromise"]:
        out["newsletterPromise"] = studium["versprechen"]
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
# Der CTA-Nachweis sucht ein gerendertes Element, nicht den Seitentext. Seit die
# Extended-CSS inline in die Seite eingebettet wird, steckt in jedem gebauten HTML
# der Selektor `.newsletter-footer` – eine Zeichenkette, kein Kasten. Auf rohen Text
# zu prüfen hätte in beide Richtungen falsch ergeben: im Leerzustand ein Fund wegen
# einer CSS-Zeile, und bei fehlendem Streifen ein grünes N6 wegen desselben.
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
        # Die Anmeldeseite und ihre Journeys dürfen den Zustand erklären – sie
        # bewerben nichts, sie beschreiben ihn. Fundwürdig ist Werbung dort,
        # wo kein Ausweg angeboten wird (deshalb der Pfadabgleich).
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
    elif action:
        # Der Feldname darf auf zwei Weisen feststehen: literal im Shortcode oder
        # über `capture.feld_email` im Studio-JSON (der Betreiber stellt dort
        # EMAIL_1 ein, wenn sein Formular so heißt). Beides ist dasselbe
        # Versprechen – die Wache prüft den Mechanismus, nicht die Kopie eines
        # Wertes, und erzwingt so keine zweite Stelle, die man pflegen muss.
        literal = f'name="{FELDNAME}"' in sc
        aus_konfig = re.search(r'name="\{\{[^}]*feld_email', sc) is not None
        if not (literal or aus_konfig):
            funde.append(("N4", f"Inline-Formular POSTet ohne Feld `{FELDNAME}` – "
                                "Brevo und Konsorten lesen die Adresse aus genau diesem "
                                "Namen (literal oder via capture.feld_email)", "feldname"))
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
    if not _cta_im_footer(footer):
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
    material = studio.material_aus_artikel(root, artikel)
    e = studio.baue_email(material, datum=tag, root=root, versprechen=versprechen)
    e["anzahl"] = len(artikel)
    return e


def baue_digest(artikel: list[dict], datum: str, versprechen: str,
                *, root: str = BLOG_DIR) -> tuple[str, str, int]:
    """Abwärtskompatible Fassade: (html, text, anzahl)."""
    e = baue_ausgabe(artikel, datum, versprechen, root=root)
    return e["html"], e["text"], e["anzahl"]


# ---------------------------------------------------------------------- Brevo-Transport
# Reparatur 23.09.2026 (Lauf #14): Der erste Lauf, der den Netz-Call überhaupt
# ausführte, scheiterte im Transport – und die Fehlerstelle war dreifach:
#   1. Der Payload nannte das Feld `preheader`. Brevo kennt in CreateEmailCampaign
#      kein solches Feld – das offizielle heißt `previewText`. Ein Schema-Bruch,
#      der jede Kampagne mit HTTP 400 ablehnt (oder sie still ohne Preheader
#      anlegt, je nachdem, wie streng die Validierung gerade ist).
#   2. Absender und Reply-To waren hart codiert statt aus der Studio-SSOT – und
#      nichts prüfte VOR dem Anlegen der Kampagne, ob der Absender im Brevo-Konto
#      verifiziert und die Liste vorhanden ist. Genau das steht (Absender-Auth,
#      SPF/DKIM) in der Freischalt-Checkliste als Betreiber-Schritt offen; ohne
#      Vorprüfung lief das Skript erst in Brevos Fehlermeldung hinein, statt den
#      Befund selbst auszusprechen.
#   3. Brevo-Fehler wurden auf 200 Zeichen verstümmelt, ohne `code`/`message` zu
#      trennen, und nichtflüchtige Ausfälle (429/5xx/Netz) wurden nie wiederholt.
TRANSIENTE_CODES = {429, 500, 502, 503, 504}   # Wiederholung wert
VERSUCHE = 3                                    # 1 Anfrage + 2 Wiederholungen
PAUSE_SEKUNDEN = (2.0, 5.0)                     # exponentiell-ish, CI-freundlich knapp
ANTWORT_LIMIT = 4000                            # Fehlerantworten vollständig, nicht verstümmelt


def _http_request(key: str, pfad: str, payload: dict | None, methode: str) -> tuple[int, str]:
    url = "https://api.brevo.com/v3/" + pfad.lstrip("/")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method=methode,
        headers={"api-key": key, "Content-Type": "application/json",
                 "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", "replace")[:ANTWORT_LIMIT]
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")[:ANTWORT_LIMIT]
    except Exception as exc:  # noqa: BLE001
        return 0, f"{exc.__class__.__name__}: {exc}"


def _mit_wiederholung(key: str, pfad: str, payload: dict | None, methode: str) -> tuple[int, str]:
    """Nur transiente Ausfälle wiederholen (429/5xx/Netz) – nie 4xx-Logikfehler.

    Ein 400 von Brevo ist ein Befund, keine Störung: Wiederholen würde die
    Kampagne drei Mal gegen dieselbe Wand fahren. Ein 502 ist eine Störung:
    dreimal Versuchen ist Agentur-Anstand, dreimal denselben 400 schicken nicht.
    """
    code, antwort = 0, ""
    for versuch in range(VERSUCHE):
        code, antwort = _http_request(key, pfad, payload, methode)
        if code not in TRANSIENTE_CODES and code != 0:
            return code, antwort
        if versuch + 1 < VERSUCHE:
            time.sleep(PAUSE_SEKUNDEN[min(versuch, len(PAUSE_SEKUNDEN) - 1)])
    return code, antwort


def brevo(api_key: str, pfad: str, payload: dict) -> tuple[int, str]:
    return _mit_wiederholung(api_key, pfad, payload, "POST")


def brevo_get(api_key: str, pfad: str) -> tuple[int, str]:
    return _mit_wiederholung(api_key, pfad, None, "GET")


TRANSPORT = brevo        # für den Selbsttest austauschbar – dann trifft kein Netz
TRANSPORT_GET = brevo_get


def brevo_fehler(code: int, antwort: str) -> str:
    """Brevo-Fehlerantwort strukturieren: code + message, nicht verstümmelt.

    Brevos Fehlerkörper ist `{"code": "...", "message": "..."}`. Die rohe
    Zeichenkette in ein Log zu kippen verstümmelt genau die Hälfte, die der
    Mensch braucht. → "HTTP 400: <message> · <code>".
    """
    msg = (antwort or "").strip()
    try:
        dat = json.loads(msg)
        if isinstance(dat, dict):
            teile = [str(dat[k]) for k in ("message", "code", "error") if dat.get(k)]
            if teile:
                msg = " · ".join(teile)
    except json.JSONDecodeError:
        pass
    return f"HTTP {code}: {msg[:600] or 'leere Antwort'}"


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
    global TRANSPORT, TRANSPORT_GET, PAUSE_SEKUNDEN, _http_request, speichere_state
    aufgerufen: list = []
    get_aufgerufen: list = []
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
             footer_extra='<div class="newsletter-footer">anmelden</div>')
        f4, n4, z4 = pruefe_capture(r4)
        pruefe(not f4, f"saubere Kette meldet Funde: {f4}")
        pruefe(z4 == "aktiv", f"gesunde Kette gilt nicht als aktiv: {z4}")

        # 8b) Echter Brevo-Formular-Endpunkt: *.sibforms.com/serve/… ist die
        #     Formularhost-Domain von Brevo (Quick Share/Embed – so liefert
        #     das Konto die URL), ebenso berechtigt wie l.brevo.com.
        sib = "https://0e12ee47.sibforms.com/serve/MUIFAD_test"
        r4s = os.path.join(tmp, "sib")
        os.makedirs(os.path.join(r4s, ".github", "workflows"), exist_ok=True)
        baum(r4s, f'newsletterFormAction = "{sib}"\\n'
                 'newsletterPromise = "Eine Mail pro Werktag."\\n',
             artikel=[("2026-09-11-neu-1", HEUTE_FIX - datetime.timedelta(days=1), "false")],
             seite_extra=f'<form action="{sib}"><input name="email">',
             datenschutz='<h2 id="newsletter">Newsletter</h2>'
                         '<p>Double-Opt-In, Widerruf formlos, Loeschung 30 Tage.</p>',
             workflow="BREVO_API_KEY\\n--strict-inert\\n",
             footer_extra='<div class="newsletter-footer">anmelden</div>')
        f4s, n4s, z4s = pruefe_capture(r4s)
        pruefe(not f4s, f"sibforms.com-Endpunkt meldet Funde (erlaubte Domain): {f4s}")
        pruefe(z4s == "aktiv", f"sibforms.com-Kette gilt nicht als aktiv: {z4s}")

        # 9c) `zustand` ist keine Dekoration: Datei und Längen kommen aus dem JSON
        pfad_z, betreff_len, artikel_len = zustand_konfig(r4)
        pruefe(pfad_z == STATE_REL and betreff_len == 12 and artikel_len == 400,
               f"Standard-Zustandsblock nicht gelesen: {pfad_z}, {betreff_len}, {artikel_len}")
        r4c = os.path.join(tmp, "zustand-versetzt")
        os.makedirs(os.path.join(r4c, ".github", "workflows"), exist_ok=True)
        os.makedirs(os.path.join(r4c, "data"), exist_ok=True)
        os.makedirs(os.path.join(r4c, "content"), exist_ok=True)
        with open(os.path.join(r4c, "hugo.toml"), "w", encoding="utf-8") as fh:
            fh.write("[params]\n")
        with open(os.path.join(r4c, "data", "newsletter_studio.json"), "w",
                  encoding="utf-8") as fh:
            fh.write(json.dumps({"zustand": {"datei": "data/nl-zustand.json",
                                             "betreff_historie": 2,
                                             "artikel_historie": 3}}))
        speichere_state(r4c, {"zuletzt_betreff": ["a", "b", "c"], "versandene_artikel": []})
        verschieb = lade_state(r4c)
        pruefe(os.path.exists(os.path.join(r4c, "data", "nl-zustand.json"))
               and not os.path.exists(os.path.join(r4c, STATE_REL)),
               f"State-Datei folgt nicht `zustand.datei`: {verschieb}")
        _, b_len, a_len = zustand_konfig(r4c)
        pruefe(b_len == 2 and a_len == 3,
               f"Historienlängen aus dem JSON ignoriert: {b_len}/{a_len}")

        # 9b) Adressfeld: literal falsch ist ein Fund, aus der Konfiguration gelesen
        #     ist erlaubt – der Betreiber benennt das Feld beim Anbieter, nicht im
        #     Template. Die Wache prüft den Mechanismus, nicht eine kopierte Zahl.
        r4b = os.path.join(tmp, "gut-feld")
        os.makedirs(os.path.join(r4b, ".github", "workflows"), exist_ok=True)
        baum(r4b, 'newsletterFormAction = "https://l.brevo.com/landing/x"\n',
             seite_extra='<form action="https://l.brevo.com/landing/x"><input name="email">',
             datenschutz='<h2 id="newsletter">Newsletter</h2><p>Double-Opt-In</p>',
             workflow="BREVO_API_KEY\n--strict-inert\n",
             footer_extra='<div class="newsletter-footer">anmelden</div>')
        kopie = os.path.join(r4b, SHORTCODE_REL)
        vorlage = _read(kopie)                      # erst lesen, dann öffnen (sonst leer)
        with open(kopie, "w", encoding="utf-8") as fh:
            fh.write(vorlage.replace('name="{{ $c.feld_email }}"', 'name="EMAIL_1"'))
        f4b, _, _ = pruefe_capture(r4b)
        pruefe(any(c == "feldname" for _, _, c in f4b),
               f"ein literal falsches Adressfeld muss feldname melden: {f4b}")

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
        pruefe(anzahl == 1 and "neu-1" in html and "{{unsubscribe}}" in text
               and "Weiterlesen" in html and "Double-Opt-In" in text,
               f"Digest-Inhalt unvollständig ({anzahl})")
        pruefe("{{unsubscribe}}" in html and "{{mirror}}" in html
               and "{{update_profile}}" in html,
               "Vorlagen-Marken des Anbieters fehlen im gebauten Digest")
        pruefe("<script" not in html and "display:flex" not in html
               and 'role="presentation"' in html,
               "gebautes E-Mail ignoriert die Layout-Regeln (Q2)")
        leeren = baue_digest([], heute.isoformat(), "x")
        pruefe(leeren[2] == 0 and not leeren[0],
               "Digest ohne Artikel erzeugt leere Mail")

        # 17–19) Versand-Verriegelung: ohne Bestätigung und ohne Key kein Netz
        def spy(api_key, pfad, payload):
            aufgerufen.append((api_key, pfad, payload))
            return 201, '{"id": 42}'
        def spy_get(api_key, pfad):
            get_aufgerufen.append(pfad)
            if pfad == "senders":
                return 200, json.dumps({"senders": [
                    {"email": "news@franksfinanzcheck.de", "active": True, "id": 1}]})
            return 200, json.dumps({"id": 7, "totalSubscribers": 3})
        TRANSPORT = spy
        TRANSPORT_GET = spy_get
        get_aufgerufen.clear()
        # Die Studio-SSOT in den Testbaum: der Versand-Payload muss aus ihr
        # lesen (Name/E-Mail/Reply-To), nicht aus hart codierten Defaultwerten.
        with open(os.path.join(r4, "data", "newsletter_studio.json"), "w",
                  encoding="utf-8") as fh:
            fh.write(json.dumps({"email": {"absender": {
                "name": "Frank von FranksFinanzcheck",
                "email": "news@franksfinanzcheck.de"},
                "antwort_an": "kontakt@franksfinanzcheck.de"}}))
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
        rc3 = versende(r4, html, text, "X", dry_run=False, preheader="Vorschautext")
        state = lade_state(r4)
        pruefe(bool(aufgerufen) and rc3 == 0
               and state.get("versandene_artikel", [])[-1:] == ["2026-09-11-neu-1"],
               f"verscharfter Versand läuft nicht durch (rc={rc3}): {state}")
        # 20a) Der Payload spricht Brevos Schema, nicht unser Wörterbuch:
        #      previewText (das Feld, das es gibt) statt preheader (das es
        #      nicht gibt – genau daran scheiterte Lauf #14), Absender und
        #      Reply-To aus der Studio-SSOT statt hart codiert.
        kampagne = aufgerufen[0][2] if aufgerufen else {}
        pruefe("previewText" in kampagne and "preheader" not in kampagne
               and kampagne.get("previewText") == "Vorschautext",
               f"Payload nutzt previewText nicht bzw. preheader noch: {sorted(kampagne)}")
        pruefe(kampagne.get("sender", {}).get("name") == "Frank von FranksFinanzcheck"
               and kampagne.get("sender", {}).get("email") == "news@franksfinanzcheck.de"
               and kampagne.get("replyTo", {}).get("email") == "kontakt@franksfinanzcheck.de",
               f"Absender/Reply-To nicht aus der Studio-SSOT: {kampagne.get('sender')} "
               f"/ {kampagne.get('replyTo')}")
        pruefe("senders" in get_aufgerufen
               and any(p.startswith("contacts/lists/") for p in get_aufgerufen),
               f"Vorprüfung (Absender/Liste) lief nicht vor dem Versand: {get_aufgerufen}")
        # 20) Testversand: ohne NEWSLETTER_SEND erlaubt, nutzt ausschließlich
        #     sendTest (nie sendNow) und verbucht sich NICHT als Ausgabe –
        #     ein Probe ist keine Ausgabe, sonst würde sich der Duplikatschutz
        #     (Q15) über eigene Testläufe staunen.
        os.environ["NEWSLETTER_SEND"] = ""
        aufgerufen.clear()
        vor = lade_state(r4)
        rc4 = versende(r4, html, text, "X", dry_run=False,
                       test_adresse="test@beispiel.de")
        pfade = [p for _, p, _ in aufgerufen]
        nach = lade_state(r4)
        pruefe(rc4 == 0 and any(p.endswith("/sendTest") for p in pfade)
               and not any(p.endswith("/sendNow") for p in pfade),
               f"Testversand nutzt nicht ausschließlich sendTest (rc={rc4}): {pfade}")
        pruefe(nach.get("versandene_artikel") == vor.get("versandene_artikel")
               and "kampagne_id" in nach,
               f"Testlauf verbucht sich als Ausgabe: {nach}")

        # 20b) Verdrahtung: auch MIT Bestätigung (NEWSLETTER_SEND=ja) bleibt ein
        #      Testversand ein sendTest an genau eine Adresse – die
        #      Leere-Liste-Prüfung darf ihn nicht blockieren. Der Probelauf ist
        #      der vorgesehene Weg, BEVOR die Liste ihre ersten Abonnenten hat
        #      (Checkliste Schritt 6a); ihn an der leeren Liste scheitern zu
        #      lassen, machte genau diesen Schritt unmöglich.
        os.environ["NEWSLETTER_SEND"] = "ja"
        aufgerufen.clear()

        def leer_liste_get(api_key, pfad):
            if pfad == "senders":
                return 200, json.dumps({"senders": [
                    {"email": "news@franksfinanzcheck.de", "active": True, "id": 1}]})
            return 200, json.dumps({"id": 7, "totalSubscribers": 0})
        TRANSPORT_GET = leer_liste_get
        rc20 = versende(r4, html, text, "X", dry_run=False,
                        test_adresse="test@beispiel.de")
        pfade20 = [p for _, p, _ in aufgerufen]
        pruefe(rc20 == 0 and any(p.endswith("/sendTest") for p in pfade20)
               and not any(p.endswith("/sendNow") for p in pfade20),
               f"Testversand mit Bestätigung von der leeren Liste blockiert oder "
               f"trifft die Liste (rc={rc20}): {pfade20}")
        os.environ["NEWSLETTER_SEND"] = ""
        TRANSPORT_GET = spy_get
        TRANSPORT = brevo

        # 21–24) Vorflug verriegelt, BEVOR eine Kampagne entsteht
        def leer_get(api_key, pfad):
            if pfad == "senders":
                return 200, json.dumps({"senders": [
                    {"email": "news@franksfinanzcheck.de", "active": True, "id": 1}]})
            return 200, json.dumps({"id": 7, "totalSubscribers": 0})
        TRANSPORT_GET = leer_get
        rc5, befund5 = vorflug("key", "7", "news@franksfinanzcheck.de", live=True)
        pruefe(rc5 == 1 and "0 Abonnenten" in befund5,
               f"leere Liste bei --live geht nicht laut schief: rc={rc5} {befund5!r}")
        rc6, befund6 = vorflug("key", "7", "news@franksfinanzcheck.de", live=False)
        pruefe(rc6 == 0,
               f"leere Liste blockiert zu Unrecht den Testversand: rc={rc6} {befund6!r}")
        def inaktiv_get(api_key, pfad):
            if pfad == "senders":
                return 200, json.dumps({"senders": [
                    {"email": "news@franksfinanzcheck.de", "active": False, "id": 1}]})
            return 200, json.dumps({"id": 7, "totalSubscribers": 3})
        TRANSPORT_GET = inaktiv_get
        rc7, befund7 = vorflug("key", "7", "news@franksfinanzcheck.de", live=False)
        pruefe(rc7 == 1 and "NICHT verifiziert" in befund7,
               f"unverifizierter Absender rutscht durch: rc={rc7} {befund7!r}")
        def fehlend_get(api_key, pfad):
            if pfad == "senders":
                return 200, json.dumps({"senders": [
                    {"email": "andere@woanders.de", "active": True, "id": 1}]})
            return 200, json.dumps({"id": 7, "totalSubscribers": 3})
        TRANSPORT_GET = fehlend_get
        rc8, befund8 = vorflug("key", "7", "news@franksfinanzcheck.de", live=False)
        pruefe(rc8 == 1 and "existiert im Brevo-Konto nicht" in befund8,
               f"fehlender Absender rutscht durch: rc={rc8} {befund8!r}")

        # 24b) 401/403 = Credential-Befund, nicht DNS-Befund (Läufe #15/#16,
        #      23.09.2026). Der Hinweis muss INNERHALB der ersten 350 Zeichen
        #      stehen – der Workflow kürzt die Annotation auf genau diese Länge.
        def unbefugt_get(api_key, pfad):
            return 401, json.dumps({"code": "unauthorized",
                                    "message": "Key not found"})
        TRANSPORT_GET = unbefugt_get
        rc24b, befund24b = vorflug("key", "7", "news@franksfinanzcheck.de", live=False)
        pruefe(rc24b == 1 and "BREVO_API_KEY" in befund24b and "fail-closed" in befund24b
               and "ANLEITUNG-ABSENDER-E-MAIL.md" in befund24b[:350],
               f"401 ohne Credential-Hinweis im sichtbaren Teil – Betreiber sucht "
               f"bei SPF/DKIM: rc={rc24b} {befund24b!r}")
        TRANSPORT_GET = spy_get

        # 25–26) Wiederholung: transient (502) ja, Logikfehler (400) nein –
        #     geprüft an der ECHTEN Kette brevo → _mit_wiederholung →
        #     _http_request; nur so übt der Test, was der Lauf auch ausführt.
        alte_pause = PAUSE_SEKUNDEN
        PAUSE_SEKUNDEN = (0.0, 0.0)
        http_echt = _http_request
        def trans_http(api_key, pfad, payload, methode):
            aufgerufen.append(pfad)
            return (201, '{"id": 9}') if len(aufgerufen) >= 3 else (502, "Bad Gateway")
        _http_request = trans_http
        TRANSPORT = brevo
        TRANSPORT_GET = spy_get
        aufgerufen.clear()
        os.environ["NEWSLETTER_SEND"] = "ja"
        rc9 = versende(r4, html, text, "X", dry_run=False)
        pruefe(rc9 == 0 and aufgerufen.count("emailCampaigns") == 3,
               f"transienter 502 wurde nicht genau dreimal bis zum Erfolg "
               f"probiert: rc={rc9}, {aufgerufen}")
        def hart_http(api_key, pfad, payload, methode):
            aufgerufen.append(pfad)
            return 400, '{"code":"invalid_parameter","message":"property preheader …"}'
        _http_request = hart_http
        aufgerufen.clear()
        rc10 = versende(r4, html, text, "X", dry_run=False)
        pruefe(rc10 == 1 and aufgerufen.count("emailCampaigns") == 1,
               f"400-Logikfehler wurde wiederholt statt gemeldet: rc={rc10}, {aufgerufen}")
        _http_request = http_echt
        TRANSPORT = brevo
        TRANSPORT_GET = brevo_get
        PAUSE_SEKUNDEN = alte_pause

        # 27) Ehrlichkeit nach dem Versand: scheitert das Status-Schreiben,
        #     NACHDEM die Kampagne unterwegs ist, bleibt der Lauf rot – aber
        #     der Befund sagt „VERSAND ERFOLGT“ und lügt nicht mit „es ist
        #     nichts versandt“ (die Annotation des Workflows liest genau diese
        #     Marke). Außerdem wird gelesen, was geschrieben wurde: ein Status,
        #     der die Kampagnen-ID nicht trägt, zählt als nicht geschrieben.
        echter_speicher = speichere_state

        def kaputter_speicher(root, state):
            raise OSError("Permission denied (Selbsttest)")
        speichere_state = kaputter_speicher
        aufgerufen.clear()
        TRANSPORT = spy
        TRANSPORT_GET = spy_get
        os.environ["NEWSLETTER_SEND"] = "ja"
        import io
        import contextlib
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc11 = versende(r4, html, text, "X", dry_run=False)
        pfade11 = [p for _, p, _ in aufgerufen]
        pruefe(rc11 == 1 and any(p.endswith("/sendNow") for p in pfade11)
               and "VERSAND ERFOLGT" in puffer.getvalue(),
               f"Status-Schreibfehler nach Versand nicht laut als „Versand raus, "
               f"Status kaputt“ gemeldet (rc={rc11}): {pfade11}\n{puffer.getvalue()!r}")
        speichere_state = echter_speicher
        os.environ["NEWSLETTER_SEND"] = ""
    except Exception as exc:  # noqa: BLE001
        import traceback
        fehler.append(f"Ausführung: {exc.__class__.__name__}: {exc}\n"
                      + traceback.format_exc()[-500:])
    finally:
        TRANSPORT = brevo
        TRANSPORT_GET = brevo_get
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
          f"Platzhalter, halbfertiger Abschnitt, Digest, Versand-Verriegelung, "
          f"previewText/SSOT-Payload, Vorflug, Testversand-Verdrahtung, "
          f"Wiederholung, Versand-Ehrlichkeit, State-Konfiguration).")
    return 0


# ------------------------------------------------------------------------- Versand
def absender_konfig(root: str) -> dict:
    """Absender (Name, E-Mail, Reply-To) aus der Studio-SSOT – eine Quelle.

    Bis zur Reparatur stand hier `"FranksFinanzcheck"` hart im Code und als
    E-Mail ein Default, den die Konfiguration nie sah. Die SSOT
    (`data/newsletter_studio.json` → `email`) nennt Name, Adresse und Reply-To;
    `NEWSLETTER_ABSENDER` (Repository-Variable) bleibt die bewusste Ausnahme
    oben drauf, falls der Absender je wechseln soll – Vorrang env > SSOT,
    wie in der Freischalt-Checkliste dokumentiert.
    """
    try:
        e = studio.konfiguration(root, streng=False).get("email", {}) or {}
    except SystemExit:                    # kaputtes JSON: die Wache meldet es, hier nicht sterben
        e = {}
    a = e.get("absender", {}) or {}
    email = (os.environ.get("NEWSLETTER_ABSENDER", "").strip()
             or str(a.get("email") or "news@franksfinanzcheck.de")).strip()
    return {"name": str(a.get("name") or "FranksFinanzcheck").strip() or "FranksFinanzcheck",
            "email": email,
            "antwort_an": str(e.get("antwort_an") or "").strip()}


def vorflug(key: str, liste: str, absender_email: str, *, live: bool) -> tuple[int, str]:
    """Den Absender und die Liste beim Anbieter prüfen, BEVOR etwas angelegt wird.

    → (rc, meldung) mit rc 0 = weiter, 1 = Abbruch mit Befund. Der Lauf #14
    legte blind Kampagnen an und ließ Brevo die Diagnose machen – dabei weiß
    Brevo nichts von der Checkliste, unser Skript schon: Absender fehlt oder
    ist nicht verifiziert, Liste fehlt, leere Liste bei --live sind alles
    Zustände, die hier lautsprachlich mit dem exakten nächsten Schritt für den
    Betreiber ausgesprochen werden.

    Scheitert die Vorprüfung selbst am Netz, wird abgebrochen (fail-closed):
    eine Kampagne mit ungeprüftem Empfängerkreis entsteht nicht.
    """
    code, antwort = TRANSPORT_GET(key, "senders")
    if code not in (200, 201):
        # 401/403 ist kein DNS-Befund und kein Absender-Befund, sondern ein
        # Credential-Befund: das Secret erreicht Brevo, wird dort aber nicht
        # erkannt (SMTP-Schlüssel statt API-v3-Key, anderes Konto, Key
        # regeneriert – so geschehen in den Läufen #15/#16 am 23.09.2026).
        # Ohne den Hinweis sucht der Betreiber in Schritt 2 der Checkliste
        # (SPF/DKIM), wo nichts zu holen ist. Der Hinweis steht VOR dem
        # Standardsatz, weil der Workflow die Annotation auf 350 Zeichen
        # kürzt – die Handlungsanweisung darf nicht abgeschnitten werden.
        hinweis = ""
        if code in (401, 403):
            hinweis = (" Secret BREVO_API_KEY prüfen: API-v3-Key aus „SMTP & API → "
                       "API keys“ (nie der SMTP-Schlüssel), gleiches Brevo-Konto wie "
                       "die Liste, nicht regeneriert – Anleitung "
                       "docs/ANLEITUNG-ABSENDER-E-MAIL.md, Abschnitt 1.")
        return 1, ("Absender-Vorprüfung nicht möglich (" + brevo_fehler(code, antwort)
                   + ")." + hinweis + " Kein Versand: lieber fail-closed, als eine "
                   "Kampagne mit ungeprüftem Absender anzulegen.")
    try:
        sender = json.loads(antwort).get("senders", [])
    except json.JSONDecodeError:
        return 1, "Absender-Vorprüfung: unverständliche Antwort des Anbieters – kein Versand."
    eintrag = next((s for s in sender
                    if str(s.get("email", "")).lower() == absender_email.lower()), None)
    if eintrag is None:
        return 1, (f"Absender {absender_email} existiert im Brevo-Konto nicht – Kampagne "
                   "nicht angelegt. Brevo → Senders, Domains & Dedicated IPs → Senders & IPs "
                   "→ Add sender (exakt diese Adresse), dann erneut laufen lassen "
                   "(Checkliste: docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md, Schritt 2).")
    if not eintrag.get("active", False):
        return 1, (f"Absender {absender_email} ist im Brevo-Konto vorhanden, aber NICHT "
                   "verifiziert – Brevo weist Kampagnen damit ab. Den 6-stelligen "
                   "Bestätigungscode aus der Absender-Mail eingeben bzw. SPF/DKIM auf "
                   "„verifiziert“ bringen (Checkliste Schritt 2), dann erneut laufen lassen.")
    code2, antwort2 = TRANSPORT_GET(key, f"contacts/lists/{liste}")
    if code2 == 404:
        return 1, (f"Liste {liste} existiert im Brevo-Konto nicht (HTTP 404) – Kampagne "
                   "nicht angelegt. Secret BREVO_LIST_ID gegen die Zahl in der "
                   "Listen-URL prüfen (Checkliste Schritt 3/4).")
    if code2 not in (200, 201):
        return 1, ("Listen-Vorprüfung nicht möglich ("
                   + brevo_fehler(code2, antwort2) + ") – kein Versand.")
    if live:
        try:
            gesamt = int(json.loads(antwort2).get("totalSubscribers", 0))
        except (json.JSONDecodeError, TypeError, ValueError):
            gesamt = -1
        if gesamt == 0:
            return 1, ("Die Zielliste hat 0 Abonnenten – ein Live-Versand ginge ins Leere, "
                       "es wäre eine Kampagne auf niemanden. Erst Anmeldungen sammeln "
                       "(Double-Opt-In), dann --live; für die Probe den Testversand über "
                       "--test-adresse nutzen (der trifft genau eine Adresse, nie die Liste).")
    return 0, ""


def versende(root: str, html: str, text: str, betreff: str, *, dry_run: bool,
             test_adresse: str = "", preheader: str = "") -> int:
    """Kampagne bei Brevo anlegen und senden. Dreifach verriegelt, s. Dokumentation.

    Seit der Reparatur von Lauf #14 zusätzlich: Absender/Reply-To aus der
    Studio-SSOT, `previewText` statt des nicht existierenden `preheader`-Felds,
    Vorprüfung von Absender + Liste vor dem Anlegen, strukturierte Fehler,
    Wiederholung nur bei transienten Störungen.
    """
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
    if not re.fullmatch(r"\d+", liste):
        print(f"   ❌ kein Versand: BREVO_LIST_ID ist keine Zahl ({liste!r}) – Brevo liest "
              "die Listen-ID als Ganzzahl (Zahl in der Listen-URL).")
        return 1
    absender = absender_konfig(root)
    # live=False bei Testversand: die Prüfung „Liste hat 0 Abonnenten“ gilt nur
    # dem echten Listen-Versand (sendNow). Ein sendTest trifft genau eine
    # Adresse, nie die Liste – genau deshalb ist er laut Checkliste der
    # vorgesehene Probelauf, BEVOR die Liste Abonnenten hat. Ihn an der leeren
    # Liste zu blockieren, würde den Probelauf unmöglich machen (Fehlerklasse
    # des 23.09.2026: dokumentierter Weg, den kein Lauf gehen konnte).
    # Existenz-Prüfungen (Absender da? verifiziert? Liste vorhanden?) bleiben
    # auch beim Testversand an – der Payload trägt die listIds trotzdem.
    rc_vor, befund = vorflug(key, liste, absender["email"],
                             live=bool(bestaetigt) and not test_adresse)
    if rc_vor != 0:
        print(f"   ❌ Vorprüfung fehlgeschlagen: {befund}")
        return 1
    payload = {"name": f"Digest {datetime.date.today().isoformat()}",
               "subject": betreff, "htmlContent": html, "textContent": text,
               "sender": {"name": absender["name"], "email": absender["email"]},
               "recipients": {"listIds": [int(liste)]},
               "status": "draft",
               # Brevo-Schema (CreateEmailCampaign): das Feld heißt previewText,
               # nicht preheader – Lauf #14 scheiterte genau daran, dass der
               # Payload ein Feld trug, das es beim Anbieter nie gab.
               "previewText": (preheader.strip() or betreff)[:300],
               "mirrorActive": True}
    if absender["antwort_an"]:
        payload["replyTo"] = {"email": absender["antwort_an"]}
    code, antwort = TRANSPORT(key, "emailCampaigns", payload)
    if code not in (200, 201):
        print(f"   ❌ Kampagne nicht angelegt ({brevo_fehler(code, antwort)})")
        return 1
    try:
        kennung = json.loads(antwort).get("id")
    except json.JSONDecodeError:
        kennung = None
    if not kennung:
        print(f"   ❌ Antwort ohne Kampagnen-ID: {antwort[:400]}")
        return 1
    pfad = (f"emailCampaigns/{kennung}/sendTest" if test_adresse
            else f"emailCampaigns/{kennung}/sendNow")
    body = {"emailTo": test_adresse} if test_adresse else {}
    code2, antwort2 = TRANSPORT(key, pfad, body)
    if code2 not in (200, 201, 202, 204):
        print(f"   ❌ Versand fehlgeschlagen ({brevo_fehler(code2, antwort2)})")
        return 1
    print(f"   ✅ {'Testversand an ' + test_adresse if test_adresse else 'Versand angestoßen'}"
          f" (Kampagne {kennung})")
    # Der Versand ist RAUS – ab hier darf kein Fehler mehr so gemeldet werden,
    # als hätte nichts stattgefunden. Genau das passierte bei einer
    # mikroskopischen Fehlerklasse: scheiterte das Status-Schreiben NACH dem
    # erfolgreichen sendNow, meldete der Lauf rot und die Annotation behauptete
    # „es ist nichts versandt“ – der Empfänger hielt die Mail indes in der Hand.
    # Jetzt: der Befund nennt die Wahrheit (VERSAND ERFOLGT) und der Workflow
    # spricht sie entsprechend aus. Risiko bei nicht schreibbarem Status:
    # der nächste Lauf kennt die Ausgabe nicht und könnte doppelt liefern –
    # darum rc 1, damit der Befund im Alerting landet.
    try:
        state = lade_state(root)
        state.update({"zuletzt_versandt": datetime.datetime.now(datetime.timezone.utc)
                      .isoformat(timespec="seconds"),
                      "kampagne_id": kennung})
        if not test_adresse:
            # Nur nach echtem Versand: ein Testlauf war keine Ausgabe, und wer ihn
            # zählte, müsste sich bald über sich selbst wundern (Q15, Duplikatschutz).
            _, betreff_len, artikel_len = zustand_konfig(root)
            verlauf = [b for b in state.get("zuletzt_betreff", []) if b]
            if betreff and betreff not in verlauf:
                verlauf.append(betreff)
            state["zuletzt_betreff"] = verlauf[-betreff_len:]
            schon = state.get("versandene_artikel", [])
            for slug in state.get("pending", []):
                if slug not in schon:
                    schon.append(slug)
            state["versandene_artikel"] = sorted(schon)[-artikel_len:]
            state.pop("pending", None)
        speichere_state(root, state)
        # Nachkontrolle: gelesen, was geschrieben wurde. lade_state ist tolerant
        # (kaputtes JSON → {}) – Toleranz ist hier der stille Doppelversand.
        if lade_state(root).get("kampagne_id") != kennung:
            raise OSError("Nachkontrolle: Status trägt die Kampagnen-ID nicht "
                          "(Schreib- oder Lesefehler)")
    except OSError as exc:
        print(f"   ❌ VERSAND ERFOLGT (Kampagne {kennung}), aber der Status konnte nicht "
              f"geschrieben werden: {exc} – der nächste Lauf kennt diese Ausgabe nicht "
              f"(Doppelungsgefahr). data/newsletter_state.json prüfen, Duplikatschutz "
              f"nicht umgehen.")
        return 1
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Newsletter-Capture-Wache + Digest")
    ap.add_argument("--root", default=BLOG_DIR)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--strict-inert", action="store_true",
                    help="Leerzustand als Fehler (für Läufe, die senden wollen)")
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--send", action="store_true",
                    help="Digest an Brevo übergeben (allein: nur Vorschau/dry-run)")
    ap.add_argument("--live", action="store_true",
                    help="die LISTE wirklich treffen (sonst dry-run, auch mit --send); "
                         "ein Testversand via --test-adresse ist unabhängig davon real "
                         "(sendTest an genau eine Adresse)")
    ap.add_argument("--trotz-qa", action="store_true",
                    help="Versand trotz QA-Funden (Betreuer-Ausnahme; Funde werden "
                         "dennoch protokolliert)")
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
    ausgabe = baue_ausgabe(artikel, heute.isoformat(),
                           p.get("newsletterPromise") or "Die Sparechnungen des Tages.",
                           root=root)
    html, text, anzahl = ausgabe["html"], ausgabe["text"], ausgabe["anzahl"]
    if anzahl == 0:
        print("📬 Digest: nichts zu senden – seit dem letzten Lauf ist nichts Neues "
              "erschienen (oder alles wurde schon versandt).")
        return rc_gesamt
    # Bewusst NICHT unter public/: der gebaute Digest trägt die Vorlagen-Marken
    # {{unsubscribe}}, {{mirror}}, {{update_profile}} – die lägen sonst als
    # „Links“ im Auslieferungszustand, wo der Link-Check sie als defekte interne
    # Ziele zählt und Hugo sie im schlimmsten Fall in den Index schreibt. CI legt
    # sie nach /tmp (siehe Workflow).
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
    state["pending"] = [a["slug"] for a in artikel]
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
        # ohne --live real (sendTest an genau eine Adresse) – sonst wäre der
        # dokumentierte Probelauf `--send --test-adresse X` eine stille
        # Vorschau, und genau so lief der 23.09.2026: grün, aber keine Mail.
        rc_gesamt = max(rc_gesamt, versende(root, html, text, betreff,
                                            dry_run=not (args.live or bool(args.test_adresse)),
                                            test_adresse=args.test_adresse,
                                            preheader=ausgabe.get("preheader", "")))
    else:
        print("   (kein Versand – --send fehlt; gebaute Digeste bleiben bewusst lokal)")
    return rc_gesamt


if __name__ == "__main__":
    sys.exit(main())
