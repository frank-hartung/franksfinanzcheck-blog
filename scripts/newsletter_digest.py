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
            sendTest an eine Testadresse). Der Transport meldet sich beim
            Anbieter mit eigener Kennung (kein „Python-urllib“-Standard – genau
            der ließ Lauf #21 an der Cloudflare-Kante scheitern), wiederholt nur
            LESANFRAGEN, liest nach einem zweifelhaften sendNow die
            Kampagnen-Akte nach statt nochmal zu senden und hält bei bleibendem
            Zweifel den nächsten Listen-Versand an (`versand_unklar` in data/
            newsletter_state.json; Release nur von Hand). `BREVO_API_HOST` ist
            optional und nur für Brevo-eigene Domains erlaubt.
            Bewusst dreifach verriegelt:
            API-Key + Listen-ID als Secrets, `NEWSLETTER_SEND=ja` als
            Eingeständnis, dass die LISTE getroffen wird, und ohne beides
            passiert kein Netzwerkzugriff. Kein Testversand ohne
            `--test-adresse`. Ein Testversand (`--send --test-adresse X`,
            auch ohne `--live`) ist dagegen sofort real: er ist eine echte
            Mail an genau die eingegebenen Adressen (sendTest, nie sendNow)
            und zahlt sich deshalb nicht als Ausgabe in den Duplikatschutz
            ein. `--send` ALLEIN bleibt eine Vorschau (dry-run).
            Der Kampagnen-Payload spricht CreateEmailCampaign: `replyTo` ist
            eine Adresse (String), `emailTo` beim Test eine Liste. Das
            Transaktions-Objekt `{"email": "…"}` lehnt Brevo mit HTTP 400
            „ReplyTo email should be valid“ ab – Test und Live, weil beide
            zuerst die Kampagne anlegen (Lauf 35904226864, 23.09.2026).
            Eine TEST-Kampagne trägt außerdem KEINE `recipients`: Brevo löst
            die Empfänger beim Anlegen auf, und eine noch leere Zielliste
            ergab „There are no contacts associated with the given recipients
            info“ (Lauf 36015927654, 24.09.2026) – der dokumentierte Probelauf
            VOR den ersten Abonnenten war damit unmöglich. `recipients` ist im
            Schema optional (Pflicht wird `listIds` erst mit `scheduledAt`),
            `sendTest` braucht nur `emailTo`.
            Testadressen werden vor der Kampagne im Konto GEMESSEN: Brevo
            nimmt Testmails nur an existierende, nicht gesperrte Kontakte mit
            Listen-Zugehörigkeit an. Ein fehlender Kontakt wird – wenn nicht
            per `--test-kontakt-nicht-anlegen` untersagt – ohne Listen-Eintrag
            angelegt; eine Listen-Aufnahme passiert nur, wenn Brevo genau das
            verlangt (und wird ausgewiesen). Eine Sperrliste löst nie ein
            Skript – das bleibt ein Mensch (Kontakt anlegen: `POST /v3/contacts`,
            Liste: `POST /v3/contacts/lists/{id}/contacts/add`).

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
import newsletter_schedule as schedule
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
TRANSIENTE_CODES = {429, 500, 502, 503, 504}   # bei LESAGEN wiederholungswert
VERSUCHE = 3                                    # 1 Anfrage + 2 Wiederholungen (nur GET)
PAUSE_SEKUNDEN = (2.0, 5.0)                     # exponentiell-ish, CI-freundlich knapp
ANTWORT_LIMIT = 4000                            # Fehlerantworten vollständig, nicht verstümmelt
API_GRUND = "https://api.brevo.com/v3/"
ERLAUBTE_API_DOMAINS = ("api.brevo.com", "api.us.brevo.com", "api.sendinblue.com",
                        "api.us.sendinblue.com")

# Heilung Lauf #21 (23.09.2026, 12:16 UTC) – die Kante vor Brevos API, nicht Brevo:
#   ❌ Vorprüfung fehlgeschlagen: Absender-Vorprüfung nicht möglich (HTTP 403:
#   …/error-1010/ "Error 1010: Access denied" "The site owner has blocked access
#   based on your browser's signature.")
# Cloudflare-Fehler 1010 ist ein Browser-Signatur-Filter: er greift, bevor Brevos
# Authentifizierung die Anfrage überhaupt sieht. Auslöser war hier die
# Standardkennung der Python-Standardbibliothek („Python-urllib/3.11“), die
# urllib mitliefert, wenn kein User-Agent gesetzt wird – dieselbe Falle, an der
# bereits Lauf #14 scheiterte, nur einen Schritt früher.
#
# Die Antwort darauf ist EINE saubere Client-Kennnung, keine Imitation:
#   * Identität 0 nennt Projekt, Version, Referenz-URL und Laufumgebung – so,
#     wie ein API-Client sich anmelden gehört (und so, dass Brevo-Support in
#     seinen Logs exakt diesen Client wiederfindet);
#   * Identität 1 ist der Reservefall („compatible; …Bot…“ – weiterhin ehrlich,
#     kein vorgetäuschter Browser), falls die Kante den ersten String in eine
#     Sammelregel laufen lässt.
# Bewusst KEIN Mozilla-Chrome-Header: einen Browser vorzuspielen, um einen
# Botschutz auszuhebeln, wäre Betrug an der Kante statt Reparatur des Clients –
# und es wäre die nächste Störung, sobald die Signaturprüfung strenger wird.
CLIENT_KENNNUNG = "franksfinanzcheck-newsletter/1.1 (+https://franksfinanzcheck.de; Brevo-REST-v3; GitHub-Actions)"
CLIENT_RESERVE = "Mozilla/5.0 (compatible; FranksFinanzcheckBot/1.1; +https://franksfinanzcheck.de/newsletter/)"
IDENTITÄTEN = (CLIENT_KENNNUNG, CLIENT_RESERVE)
IDENTITÄTS_INDEX = 0                            # was zuletzt gesendet wurde (Diagnose)
IDENTITÄTS_WECHSEL_SEKUNDEN = 1.0
# Woran die Blockage zu erkennen ist. Cloudflare schreibt seinen
# Signaturfilter in den Leib (`error code: 1010`, HTML-Blockseite,
# `cf-ray`-Kopfzeile) – Brevos eigene Absagen sind JSON mit `code`/`message`.
KANTEN_MARKEN = ("error code: 1010", "error 1010", "cloudflare", "cf-mitigated",
                 "cf-ray", "security compromise", "attention required")
KANTEN_MUSTER = re.compile(
    r"cloudflare|cf-mitigated|cf-ray|error\s*code:\s*1010|error\s*1010|"
    r"security\s+compromise|attention\s+required", re.I)


def _kopf_beweis(exc: urllib.error.HTTPError) -> str:
    """Header-Beweis einer Kanten-Antwort, wenn der Körper kein JSON ist.

    Eine Cloudflare-Blockseite nennt sich selbst (`server: cloudflare`, `cf-ray`);
    Brevos eigene Fehler antworten als JSON. Wird der Körper verstümmelt oder
    ist er HTML, sichern diese zwei Felder die Unterscheidung „Kante blockiert“
    vs. „Anbieter lehnt ab“ – sie entscheidet, ob der Betreiber bei Brevo oder
    am Netzwerk ansetzen muss.
    """
    try:
        köpfe = exc.headers or {}
        teile = [f"{n}: {köpfe.get(n)}" for n in ("server", "cf-ray", "cf-mitigated")
                 if köpfe.get(n)]
    except Exception:  # noqa: BLE001  (Header-Zugriff darf nie die Diagnose ersetzen)
        teile = []
    return (" · " + " · ".join(teile)) if teile else ""


def api_host_fehler() -> str:
    """`BREVO_API_HOST` (optional) ist nur für Brevo-eigene Hosts erlaubt.

    Der Header `api-key` reist im Klartext der Anfrage mit – ein Tippfehler oder
    eine injizierte Domain würde den Kontoschlüssel an Fremde schicken. Deshalb
    gilt: gesetzt und nicht auf der Freigabeliste → kein Netzversuch, sondern ein
    Befund. (Nicht als Störung getarnt, nicht still ignoriert.)
    """
    host = os.environ.get("BREVO_API_HOST", "").strip().lower().rstrip("/")
    if not host:
        return ""
    host = host.removeprefix("https://").removeprefix("http://").split("/")[0]
    if host in ERLAUBTE_API_DOMAINS:
        return ""
    return (f"BREVO_API_HOST {host!r} ist kein freigegebener Brevo-Host "
            f"({', '.join(ERLAUBTE_API_DOMAINS)}) – der API-Schlüssel würde an eine "
            "fremde Domain geschickt. Kein Netzversuch; Wert korrigieren oder "
            "die Variable löschen (Standard: api.brevo.com).")


def _http_request(key: str, pfad: str, payload: dict | None, methode: str) -> tuple[int, str]:
    grund = API_GRUND
    host = os.environ.get("BREVO_API_HOST", "").strip().lower().rstrip("/")
    if host and not api_host_fehler():
        host = host.removeprefix("https://").removeprefix("http://").split("/")[0]
        grund = f"https://{host}/v3/"
    url = grund + pfad.lstrip("/")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    # sendNow hat im Schema keinen Body. Content-Type ohne Körper ist eine
    # zweite, unnötige Abweichung vom dokumentierten Aufruf – GET und sendNow
    # senden deshalb keinen JSON-Kopf.
    headers = {"api-key": key, "Accept": "application/json",
               # Die Zeile, an der Lauf #21 scheiterte: ohne User-Agent sendet
               # urllib „Python-urllib/3.11“, und genau diese Signatur filtert
               # die Kante mit Fehler 1010 aus, bevor Brevo den Key je liest.
               "User-Agent": IDENTITÄTEN[IDENTITÄTS_INDEX]}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=methode, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status, r.read().decode("utf-8", "replace")[:ANTWORT_LIMIT]
    except urllib.error.HTTPError as exc:
        körper = exc.read().decode("utf-8", "replace")[:ANTWORT_LIMIT]
        if körper.lstrip()[:1] not in ("{", "["):
            körper = körper[:400] + _kopf_beweis(exc)
        return exc.code, körper
    except Exception as exc:  # noqa: BLE001
        return 0, f"{exc.__class__.__name__}: {exc}"


def kanten_block(code: int, antwort: str) -> bool:
    """Ist diese Antwort eine Blockage der Kante (Cloudflare) und keine Absage Brevos?

    Der Unterschied entscheidet, WER repariert: Bei HTTP 403 mit JSON-Leib
    sagt Brevo „dein Key/dein Absender taugt nicht“ (Betreiber-Aufgabe im Konto).
    Bei HTTP 403 mit einer Nicht-JSON-Antwort, die nach Cloudflare klingt
    (`error 1010`, `cf-ray`, `security compromise`), hat Brevo die Anfrage nie
    gesehen – dann ist der Client schief konfiguriert, und ein zweiter Anlauf
    mit derselben Signatur wäre Zeitverschwendung. Die Marke sitzt im Leib bzw.
    (seit dieser Heilung) in den gesicherten Kopfzeilen.
    """
    if code not in (403, 406, 429, 503, 1010):
        return False
    return bool(KANTEN_MUSTER.search(antwort or ""))


def _ruf(key: str, pfad: str, payload: dict | None, methode: str) -> tuple[int, str]:
    """Ein Netzaufruf, bei Bedarf mit zweiter (weiterhin ehrlicher) Kennung.

    Nur die Kanten-Blockage löst den Identitätswechsel aus – ein 400/404 von
    Brevo hat nichts mit der Signatur zu tun und würde mit anderer Kennung
    dasselbe Ergebnis liefern.
    """
    global IDENTITÄTS_INDEX
    IDENTITÄTS_INDEX = 0
    code, antwort = _http_request(key, pfad, payload, methode)
    if kanten_block(code, antwort) and len(IDENTITÄTEN) > 1:
        time.sleep(IDENTITÄTS_WECHSEL_SEKUNDEN)
        IDENTITÄTS_INDEX = 1
        code, antwort = _http_request(key, pfad, payload, methode)
    return code, antwort


def _mit_wiederholung(key: str, pfad: str, payload: dict | None, methode: str) -> tuple[int, str]:
    """Lesen wiederholen (429/5xx/Netz), Schreiben NIE blind wiederholen.

    Zwei Getrenntes, das früher in einem Satz steckte:

    1. **Logikfehler wiederholen ist sinnlos.** Ein 400 von Brevo ist ein
       Befund, keine Störung – dreimal gegen dieselbe Wand fahren hilft nicht.
    2. **Ein wiederholtes Schreiben ist ein zweiter Versand.** GETs sind
       idempotent, POSTs bei Brevo sind es nicht: `POST /emailCampaigns` legt
       eine Kampagne an, `POST /emailCampaigns/{id}/sendNow` schickt sie an
       ALLE Abonnenten. Antwortete die Kante auf einen sendNow mit 502, obwohl
       die Sendung schon angenommen war, wiederholte die alte Fassung diesen
       Aufruf bis zu dreimal – genau die Doppelzustellung, die der ganze
       Duplikatsschutz des Skripts verhindern soll. Deshalb: schreibtreibende
       Methoden laufen genau einmal; der Zweifel wird danach NACHGELESEN
       (`_versand_nachlesen`), nicht nochmal gedrückt.
    """
    if (methode or "").upper() != "GET":
        return _ruf(key, pfad, payload, methode)
    code, antwort = 0, ""
    for versuch in range(VERSUCHE):
        code, antwort = _ruf(key, pfad, payload, methode)
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

    Seit der Heilung von Lauf #21 steht vor dieser Zeile die Klassifikation,
    denn die beiden Fälle haben verschiedene Besitzer: „Kante blockiert“
    (Signaturfilter vor Brevo – die Anfrage wurde dort nie gelesen) ist eine
    andere Baustelle als „Anbieter lehnt ab“ (Konto, Absender, Schema). Der
    Netzweg-Nullfall heißt ausdrücklich „Netzweg gestört“, weil er über das
    Konto nichts aussagt – ihn als Konto-Befund zu melden, war der zweite
    Irrtum, den Lauf #21 hinterließ.
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
    vor = ""
    if kanten_block(code, antwort):
        vor = ("Kante blockiert (Signaturfilter vor der API, nicht Brevo): HTTP "
               f"{code}, Antwort ist kein JSON. Probierte Client-Kennungen: "
               + " → ".join(k[:48] for k in IDENTITÄTEN) +
               ". Brevo hat die Anfrage nie gesehen – Konto, Absender und Liste "
               "sind damit NICHT geprüft. Nächster Schritt: diese Kennung beim "
               "Brevo-Support zur Freigabe nennen, oder den Versandlauf von einem "
               "Netz ohne Rechenzentrums-Egress starten (die Kante sortiert "
               "GitHub-Runner-IPs gern vor der Anwendung aus).")
    elif code == 0:
        vor = ("Netzweg gestört (DNS/TLS/Zeitlimit) – die Anfrage erreichte die API "
               "nicht; das ist keine Aussage über Konto, Absender oder Liste.")
    return f"HTTP {code}: {vor}{' – ' if vor else ''}{msg[:600] or 'leere Antwort'}"


def antwort_endgueltig_abgelehnt(code: int, antwort: str) -> bool:
    """Hat der Anbieter die Anfrage eindeutig abgelehnt (also: nichts passiert)?

    True  → 4xx-Absage aus Brevos Anwendung (außer der Kanten-Blockage): die
              Ressource wurde nicht angelegt, der Versand nicht angenommen.
    False → Kanten-Blockage, Netzweg-Nullfall, 429 oder 5xx: der Ausgang ist
              UNBEKANNT, denn die Antwort kann verloren gegangen sein, nachdem
              die Anfrage schon wirkte. Unbekannt ist hier kein Detail, sondern
              der Grund, warum nicht nochmal geschrieben wird.
    """
    return 400 <= code < 500 and code != 429 and not kanten_block(code, antwort)


# Statuswerte, die belegen, dass Brevo die Sendung angenommen hat (v3:
# `GET /emailCampaigns/{id}` → `status`). „draft“ und „suspend*“ belegen das
# Gegenteil, alles andere bleibt Ungewissheit und wird als solche gemeldet.
STATUS_RAUS = ("in_process", "sent", "finished", "delivered", "test_sent", "in_test",
               "sent_after_delay", "archive")


def versand_nachlesen(key: str, kennung) -> tuple[str, str]:
    """Nach einem zweifelhaften Sende-Aufruf: ist die Mail tatsächlich raus?

    Ein `sendNow` wird nie wiederholt (Doppelzustellung an die ganze Liste),
    also bleibt nach 502/Zeitlimit/Kantenblock die Frage offen. Beantwortet sie
    das Konto selbst: die Kampagnen-Akte nennt Status und Zähler.→
    ("raus"|"nicht raus"|"unklar", begründung)
    """
    code, antwort = TRANSPORT_GET(key, f"emailCampaigns/{kennung}")
    if code not in (200, 201):
        return "unklar", (f"Kampagnen-Status nicht ablesbar ({brevo_fehler(code, antwort)})")
    try:
        dat = json.loads(antwort)
    except json.JSONDecodeError:
        return "unklar", "Kampagnen-Status nicht lesbar (Antwort kein JSON)"
    status = str(dat.get("status") or "").strip().lower()
    stats = dat.get("statistics") or {}
    gesendet = 0
    for feld in ("deliveredCount", "nbSuccess", "sent", "totalSent"):
        try:
            gesendet = max(gesendet, int(stats.get(feld) or 0))
        except (TypeError, ValueError):
            continue
    if status in STATUS_RAUS or gesendet > 0:
        return "raus", f"Kampagnen-Status {status or '—'}, Zähler {gesendet}"
    if status in ("draft", "suspendend", "suspended", "suspend", "terminated",
                  "global_suppression", "error", "error_to_check", "schedule"):
        return "nicht raus", f"Kampagnen-Status {status}"
    return "unklar", f"Kampagnen-Status {status or 'leer'} – nicht einordenbar"


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
    from unittest.mock import patch
    kadenz_mock = patch(__name__ + ".kadenz_pruefen", return_value="")
    reservierung_mock = patch(__name__ + ".termin_reservieren")
    kadenz_mock.start()
    reservierung_mock.start()
    tmp = tempfile.mkdtemp(prefix="newsletter-selftest-")
    global TRANSPORT, TRANSPORT_GET, PAUSE_SEKUNDEN, _http_request, speichere_state
    global IDENTITÄTS_WECHSEL_SEKUNDEN
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
        # 20a) Der Payload spricht Brevos Kampagnen-Schema, nicht unser Wörterbuch
        #      und nicht das Transaktions-Schema:
        #      previewText statt preheader (Lauf #14), replyTo als STRING statt
        #      {"email": "…"} (Lauf 35904226864 – HTTP 400 „ReplyTo email should
        #      be valid“, Test und Live), kein textContent, kein status.
        #      sendNow trägt keinen Body.
        kampagne = aufgerufen[0][2] if aufgerufen else {}
        sende_body = [body for _, pfad, body in aufgerufen if str(pfad).endswith("/sendNow")]
        pruefe("previewText" in kampagne and "preheader" not in kampagne
               and kampagne.get("previewText") == "Vorschautext",
               f"Payload nutzt previewText nicht bzw. preheader noch: {sorted(kampagne)}")
        pruefe(kampagne.get("sender", {}).get("name") == "Frank von FranksFinanzcheck"
               and kampagne.get("sender", {}).get("email") == "news@franksfinanzcheck.de"
               and kampagne.get("replyTo") == "kontakt@franksfinanzcheck.de"
               and isinstance(kampagne.get("replyTo"), str),
               f"Absender/Reply-To nicht aus der Studio-SSOT oder replyTo kein String: "
               f"{kampagne.get('sender')} / {kampagne.get('replyTo')!r}")
        pruefe("textContent" not in kampagne and "status" not in kampagne
               and not kampagnen_schema_verstoesse(kampagne),
               f"Kampagnen-Payload verletzt CreateEmailCampaign: "
               f"{kampagnen_schema_verstoesse(kampagne) or sorted(kampagne)}")
        pruefe(sende_body == [None],
               f"sendNow darf keinen Body tragen (Schema hat keinen): {sende_body}")
        historisch = {"replyTo": {"email": "kontakt@franksfinanzcheck.de"},
                      "textContent": "x", "status": "draft", "preheader": "x",
                      "name": "n", "subject": "s", "htmlContent": "<p>x</p>",
                      "sender": {"name": "A", "email": "news@franksfinanzcheck.de"},
                      "recipients": {"listIds": [7]}, "previewText": "p",
                      "mirrorActive": True}
        hist_verstoss = kampagnen_schema_verstoesse(historisch)
        pruefe(any("replyTo" in v for v in hist_verstoss)
               and any("textContent" in v or "Transaktionsfelder" in v for v in hist_verstoss),
               f"der Payload von Lauf 35904226864 gilt als schema-gültig: {hist_verstoss}")
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
        test_bodies = [body for _, p, body in aufgerufen if str(p).endswith("/sendTest")]
        pruefe(rc4 == 0 and any(p.endswith("/sendTest") for p in pfade)
               and not any(p.endswith("/sendNow") for p in pfade)
               and test_bodies == [{"emailTo": ["test@beispiel.de"]}],
               f"Testversand nutzt nicht ausschließlich sendTest mit emailTo-Liste "
               f"(rc={rc4}): {pfade} {test_bodies}")
        pruefe(nach.get("versandene_artikel") == vor.get("versandene_artikel")
               and "test_kampagne_id" in nach,
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

        # 20c) Lauf 35904226864: Reply-To-Absage fällt genau einmal auf den
        #      verifizierten Absender zurück und sendet dann. Ein anderer 400
        #      wird nicht wiederholt. Eine ungültige Testadresse berührt das
        #      Netz nicht (kein leeres emailTo, kein stiller Listenversand).
        anlege: list = []

        def reply_ablehnung(api_key, pfad, payload):
            anlege.append((pfad, payload))
            if (pfad == "emailCampaigns" and isinstance(payload, dict)
                    and payload.get("replyTo") == "kontakt@franksfinanzcheck.de"):
                return 400, ('{"code":"invalid_parameter",'
                             '"message":"ReplyTo email should be valid"}')
            if pfad == "emailCampaigns":
                return 201, '{"id": 77}'
            return 204, ""

        TRANSPORT = reply_ablehnung
        rc_reply = versende(r4, html, text, "X", dry_run=False,
                            test_adresse="Frank <Probe@Beispiel.de>")
        kampagnen = [p for pfad, p in anlege if pfad == "emailCampaigns"]
        pruefe(rc_reply == 0 and len(kampagnen) == 2
               and kampagnen[0].get("replyTo") == "kontakt@franksfinanzcheck.de"
               and kampagnen[1].get("replyTo") == "news@franksfinanzcheck.de"
               and any(pfad.endswith("/sendTest") and body == {"emailTo": ["probe@beispiel.de"]}
                       for pfad, body in anlege),
               f"Reply-To-Absage fällt nicht auf den Absender zurück "
               f"(rc={rc_reply}): {anlege}")
        anlege.clear()

        def anderer_400(api_key, pfad, payload):
            anlege.append(pfad)
            return 400, '{"code":"invalid_parameter","message":"htmlContent is too short"}'

        TRANSPORT = anderer_400
        rc_ander = versende(r4, html, text, "X", dry_run=False,
                            test_adresse="probe@beispiel.de")
        pruefe(rc_ander == 1 and anlege.count("emailCampaigns") == 1,
               f"fremder 400 wurde wiederholt: {anlege}")
        anlege.clear()
        TRANSPORT = reply_ablehnung
        rc_bad = versende(r4, html, text, "X", dry_run=False,
                          test_adresse="keine-adresse")
        pruefe(rc_bad == 1 and not anlege,
               f"ungültige Testadresse hat das Netz berührt: {anlege}")
        gelesen, norm_fehler = test_adressen_lesen(
            "Frank <Probe@Beispiel.de>, probe@beispiel.de")
        pruefe(norm_fehler == "" and gelesen == ["probe@beispiel.de"],
               f"Testadressen nicht normalisiert: {gelesen!r} {norm_fehler!r}")
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
        TRANSPORT_GET = spy_get

        # 25–27) Der Netzweg selbst: Kennung, Wiederholung, Kanten-Blockage.
        #     Geprüft an der ECHTEN Kette brevo → _mit_wiederholung → _ruf →
        #     _http_request; nur so übt der Test, was der Lauf auch ausführt.
        alte_pause = PAUSE_SEKUNDEN
        alte_identpause = IDENTITÄTS_WECHSEL_SEKUNDEN
        PAUSE_SEKUNDEN = (0.0, 0.0)
        IDENTITÄTS_WECHSEL_SEKUNDEN = 0.0
        http_echt = _http_request

        # 25) Die Client-Kennung darf nie die Standardkennung der
        #     Standardbibliothek sein: genau die ließ Lauf #21 an der Kante
        #     scheitern (HTTP 403, „error code: 1010“ – Browser-Signatur-Filter,
        #     bevor Brevos Authentifizierung die Anfrage je las).
        pruefe(all("Python-urllib" not in k for k in IDENTITÄTEN),
               f"Kennung nennt die Standardbibliothek (Kanten-Falle): {IDENTITÄTEN}")
        pruefe(all(k.startswith(("franksfinanzcheck", "Mozilla/5.0 (compatible;"))
                   for k in IDENTITÄTEN),
               f"Kennung ist nicht selbstausgesprochen: {IDENTITÄTEN}")
        pruefe(len(IDENTITÄTEN) >= 2 and IDENTITÄTEN[0] != IDENTITÄTEN[1],
               f"Reserve-Kennung fehlt oder ist identisch: {IDENTITÄTEN}")
        pruefe(not any("Chrome/" in k and "compatible;" not in k for k in IDENTITÄTEN),
               f"Kennung imitiert einen Browser statt sich zu benennen: {IDENTITÄTEN}")

        # 26) LESANFRAGEN werden bei 502 wiederholt, bis es klappt.
        def trans_http(api_key, pfad, payload, methode):
            aufgerufen.append(pfad)
            return (200, '{"senders": []}') if len(aufgerufen) >= 3 else (502, "Bad Gateway")
        _http_request = trans_http
        TRANSPORT = brevo
        TRANSPORT_GET = brevo_get
        aufgerufen.clear()
        c, a = TRANSPORT_GET("key", "senders")
        pruefe(c == 200 and aufgerufen.count("senders") == 3,
               f"transiente Störung einer LESANfrage nicht wiederholt: {c}, {aufgerufen}")

        # 27) SCHREIBANFRAGEN werden nie wiederholt – ein wiederholtes sendNow
        #     wäre eine zweite Zustellung an die ganze Liste (Duplikatschutz ad absurdum).
        def trans_schreib_http(api_key, pfad, payload, methode):
            aufgerufen.append(pfad)
            return 502, "Bad Gateway"
        _http_request = trans_schreib_http
        aufgerufen.clear()
        c2, a2 = TRANSPORT("key", "emailCampaigns/9/sendNow", {})
        pruefe(c2 == 502 and aufgerufen.count("emailCampaigns/9/sendNow") == 1,
               f"schreibender Aufruf wurde wiederholt (Doppelversand-Risiko): {aufgerufen}")

        # 27b) Kanten-Blockage: zwete, ehrliche Kennung wird probiert, und der
        #      Befund sagt „Kante blockiert“, nicht „Brevo lehnt ab“ (Lauf #21
        #      meldete einen Konto-Befund für ein Signatur-Problem).
        def kanten_http(api_key, pfad, payload, methode):
            aufgerufen.append(f"{pfad}#{IDENTITÄTS_INDEX}")
            return 403, ('{"title":"Error 1010: Access denied","status":403,'
                         '"detail":"The site owner has blocked access based on your '
                         'browser\'s signature."} · server: cloudflare · cf-ray: 1')
        _http_request = kanten_http
        aufgerufen.clear()
        c3, a3 = TRANSPORT_GET("key", "senders")
        pruefe(c3 == 403 and "senders#1" in aufgerufen,
               f"Kanten-Blockage nicht mit zweiter Kennung versucht: {aufgerufen}")
        pruefe("Kante blockiert" in brevo_fehler(c3, a3),
               f"Kanten-Blockage heißt im Befund nicht „Kante“: {brevo_fehler(c3, a3)[:120]}")
        rc_kante, befund_kante = vorflug("key", "7", "news@franksfinanzcheck.de", live=False)
        pruefe(rc_kante == 1 and "Kante blockiert" in befund_kante,
               f"Vorflug meldet die Blockage nicht als Kanten-Befund: {befund_kante[:160]}")

        # 27c) Falscher/unsicherer API-Host: kein Netzversuch, bevor der
        #      Schlüssel eine fremde Domain erreichen könnte.
        def zähler_http(api_key, pfad, payload, methode):
            aufgerufen.append(pfad)
            return 200, "{}"
        _http_request = zähler_http
        os.environ["BREVO_API_HOST"] = "evil.example"
        aufgerufen.clear()
        rc_host = versende(r4, html, text, "X", dry_run=False, test_adresse="t@b.de")
        pruefe(rc_host == 1 and not aufgerufen,
               f"BREVO_API_HOST ohne Freigabe löst einen Netzversuch aus: {aufgerufen}")
        os.environ["BREVO_API_HOST"] = "api.brevo.com"
        pruefe(api_host_fehler() == "", "freigegebener Host gilt als Fehler")
        os.environ.pop("BREVO_API_HOST", None)

        # 28) Zweifelhafter Sende-Ausgang: NACHLESE statt Nachdrücken. Belegt die
        #     Kampagnen-Akte die Sendung, lautet der Befund „VERSAND ERFOLGT“
        #     (rc 1, damit der Zweifel im Alerting landet) – nie „nichts versandt“.
        def zweifel_http(api_key, pfad, payload, methode):
            if methode == "POST" and pfad.endswith("/sendNow"):
                return 502, "Bad Gateway"
            if methode == "POST":
                return 201, '{"id": 9}'
            if pfad == "senders":
                return 200, json.dumps({"senders": [
                    {"email": "news@franksfinanzcheck.de", "active": True, "id": 1}]})
            if pfad.startswith("contacts/lists/"):
                return 200, json.dumps({"id": 7, "totalSubscribers": 3})
            if pfad.startswith("emailCampaigns/"):
                return 200, json.dumps({"id": 9, "status": "in_process",
                                         "statistics": {"deliveredCount": 3}})
            return 200, "{}"
        _http_request = zweifel_http
        TRANSPORT = brevo
        TRANSPORT_GET = brevo_get
        os.environ["NEWSLETTER_SEND"] = "ja"
        speicher_echt = speichere_state
        geschrieben: list = []

        def speicher_mitzahl(root, state):
            geschrieben.append(dict(state))
            speicher_echt(root, state)
        speichere_state = speicher_mitzahl
        # Der Duplikatsschutz muss in diesem Fall etwas zu verbuchen haben:
        # pending tragen (der Digest des Tages), sonst ist „verbucht“ nicht messbar.
        speicher_echt(r4, {"pending": ["2026-09-11-neu-1"]})
        vor = lade_state(r4)
        rc_raus = versende(r4, html, text, "X", dry_run=False)
        state_raus = lade_state(r4)
        pruefe(rc_raus == 1 and state_raus.get("kampagne_id") == 9
               and "versand_unklar" not in state_raus,
               f"belegter Versand nach zweifelhafter Antwort nicht als VERSAND "
               f"ERFOLGT verbucht (rc={rc_raus}): {state_raus}")
        pruefe(state_raus.get("versandene_artikel") != vor.get("versandene_artikel"),
               f"belegter Versand nicht im Duplikatsschutz: {state_raus}")

        # 29) Kein Beleg, kein Gegenteil → Sperre: der nächste Listen-Versand
        #     bleibt an, bis ein Mensch nachgesehen hat. Testversände bleiben
        #     möglich (sie treffen genau eine Adresse, nie die Liste).
        def unklar_http(api_key, pfad, payload, methode):
            if methode == "POST" and pfad.endswith("/sendNow"):
                return 0, "URLError: timed out"
            if methode == "POST":
                return 201, '{"id": 12}'
            if pfad == "senders":
                return 200, json.dumps({"senders": [
                    {"email": "news@franksfinanzcheck.de", "active": True, "id": 1}]})
            if pfad.startswith("contacts/lists/"):
                return 200, json.dumps({"id": 7, "totalSubscribers": 3})
            if pfad.startswith("emailCampaigns/"):
                return 502, "Bad Gateway"
            return 200, "{}"
        _http_request = unklar_http
        rc_unklar = versende(r4, html, text, "X", dry_run=False)
        state_unklar = lade_state(r4)
        pruefe(rc_unklar == 1 and state_unklar.get("versand_unklar", {}).get("kampagne_id") == 12,
               f"unklarer Sende-Ausgang ohne Sperre: rc={rc_unklar} {state_unklar}")
        aufgerufen.clear()
        _http_request = zähler_http
        rc_halten = versende(r4, html, text, "X", dry_run=False)
        pruefe(rc_halten == 1 and not aufgerufen,
               f"Sperre hält den Listen-Versand nicht an (Netzversuch trotz Zweifel): "
               f"{aufgerufen}")

        # … aber der Testversand bleibt möglich: er trifft genau eine Adresse,
        #   nie die Liste, und ist damit kein Doppelungsrisiko.
        def probe_http(api_key, pfad, payload, methode):
            aufgerufen.append(pfad)
            if methode == "POST" and pfad == "emailCampaigns":
                return 201, '{"id": 14}'
            if methode == "POST":
                return 201, "{}"
            if pfad == "senders":
                return 200, json.dumps({"senders": [
                    {"email": "news@franksfinanzcheck.de", "active": True, "id": 1}]})
            return 200, json.dumps({"id": 7, "totalSubscribers": 3})
        _http_request = probe_http
        aufgerufen.clear()
        rc_test = versende(r4, html, text, "X", dry_run=False, test_adresse="t@b.de")
        pruefe(rc_test == 0 and any(p.endswith("/sendTest") for p in aufgerufen)
               and not any(p.endswith("/sendNow") for p in aufgerufen),
               f"Sperre blockiert zu Unrecht den Testversand (rc={rc_test}): {aufgerufen}")
        speichere_state = speicher_echt
        speicher_echt(r4, {k: v for k, v in state_unklar.items() if k != "versand_unklar"})
        os.environ["NEWSLETTER_SEND"] = ""

        def hart_http(api_key, pfad, payload, methode):
            aufgerufen.append(pfad)
            return 400, '{"code":"invalid_parameter","message":"property preheader …"}'
        _http_request = hart_http
        aufgerufen.clear()
        os.environ["NEWSLETTER_SEND"] = "ja"
        TRANSPORT_GET = spy_get          # Vorprüfung lässig – geprüft wird der POST
        rc10 = versende(r4, html, text, "X", dry_run=False)
        pruefe(rc10 == 1 and aufgerufen.count("emailCampaigns") == 1,
               f"400-Logikfehler wurde wiederholt statt gemeldet: rc={rc10}, {aufgerufen}")
        _http_request = http_echt
        TRANSPORT = brevo
        TRANSPORT_GET = brevo_get
        PAUSE_SEKUNDEN = alte_pause
        IDENTITÄTS_WECHSEL_SEKUNDEN = alte_identpause

        # 30) Ehrlichkeit nach dem Versand: scheitert das Status-Schreiben,
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

        # 31) DER PROBELAUF VOR DEN ERSTEN ABONNENTEN GEHT WIEDER.
        #     Lauf 36015927654 (24.09.2026) starb beim Anlegen der Kampagne an
        #     „There are no contacts associated with the given recipients info“:
        #     die TEST-Kampagne trug `recipients.listIds` auf eine Liste mit
        #     0 Abonnenten. Der Nachbau unten ist Brevos Verhalten – er lehnt
        #     genau diesen Payload ab und nimmt einen ohne Empfänger an. Dazu
        #     die zweite, gemessene Absage (sendTest an eine Adresse, die kein
        #     Kontakt ist bzw. in keiner Liste steht): der Lauf legt den
        #     Kontakt an (OHNE Listen-Eintrag – kein Abo nebenbei), trägt ihn
        #     auf Brevos Verlangen in die Zielliste nach und wiederholt GENAU
        #     EINMAL.
        kontakte: dict = {}
        listenmitglieder: set = set()
        gesperrt: set = set()
        anrufe: list = []
        PROBE = "frank@beispiel.de"

        def brevo_nachbau(api_key, pfad, payload, methode):
            anrufe.append((methode, pfad, payload))
            if methode == "GET":
                if pfad == "senders":
                    return 200, json.dumps({"senders": [
                        {"email": "news@franksfinanzcheck.de", "active": True, "id": 1}]})
                if pfad.startswith("contacts/lists/"):
                    return 200, json.dumps({"id": 7, "name": "Blog-Abonnenten",
                                            "totalSubscribers": 0})
                if pfad.startswith("contacts/"):
                    adr = urllib.parse.unquote(pfad.split("contacts/", 1)[1])
                    if adr in kontakte:
                        return 200, json.dumps(
                            {"email": adr, "id": 99,
                             "emailBlacklisted": adr in gesperrt,
                             "listIds": [7] if adr in listenmitglieder else []})
                    return 404, '{"code":"document_not_found","message":"Contact not found"}'
                if pfad.startswith("emailCampaigns/"):
                    return 200, json.dumps({"id": 21, "status": "test_sent"})
                return 200, "{}"
            if pfad == "contacts":
                kontakte[str((payload or {}).get("email") or "")] = True
                return 201, '{"id": 99}'
            if pfad.endswith("/contacts/add"):
                neu = list((payload or {}).get("emails") or [])
                listenmitglieder.update(neu)
                return 201, json.dumps({"contacts": {}, "success": neu, "failure": []})
            if pfad == "emailCampaigns":
                if (payload or {}).get("recipients"):
                    # Die echte Brevo-Absage aus Lauf 36015927654, wortgleich.
                    return 400, ('{"code":"invalid_parameter","message":"There are no '
                                 'contacts associated with the given recipients info"}')
                return 201, '{"id": 21}'
            if pfad.endswith("/sendTest"):
                adressen = list((payload or {}).get("emailTo") or [])
                fehlend = [a for a in adressen if a not in kontakte]
                ohne_liste = [a for a in adressen
                              if a in kontakte and a not in listenmitglieder]
                if fehlend or ohne_liste:
                    return 400, json.dumps(
                        {"code": "invalid_parameter",
                         "message": "Test email could not be sent to the following "
                                    "email addresses",
                         "unexistingEmails": fehlend,
                         "withoutListEmails": ohne_liste})
                return 204, ""
            return 201, "{}"

        _http_request = brevo_nachbau
        TRANSPORT = brevo
        TRANSPORT_GET = brevo_get
        os.environ["NEWSLETTER_SEND"] = ""
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc31 = versende(r4, html, text, "X", dry_run=False, test_adresse=PROBE)
        kampagnen31 = [p for m, pfad, p in anrufe
                       if m == "POST" and pfad == "emailCampaigns"]
        sendtests31 = [p for m, pfad, p in anrufe
                       if m == "POST" and str(pfad).endswith("/sendTest")]
        pruefe(rc31 == 0 and len(kampagnen31) == 1
               and "recipients" not in kampagnen31[0]
               and str(kampagnen31[0].get("name") or "").startswith("TESTLAUF"),
               f"TEST-Kampagne trägt Empfänger oder heißt nicht TESTLAUF "
               f"(rc={rc31}): {kampagnen31}")
        pruefe(sendtests31 == [{"emailTo": [PROBE]}, {"emailTo": [PROBE]}],
               f"Nachtrag wurde nicht genau einmal wiederholt: {sendtests31}")
        pruefe(any(m == "POST" and pfad == "contacts" for m, pfad, _ in anrufe)
               and any(str(pfad).endswith("/contacts/add") for _, pfad, _ in anrufe),
               f"Kontakt bzw. Listen-Eintrag nicht nachgetragen: "
               f"{[(m, p) for m, p, _ in anrufe]}")
        pruefe("no contacts associated" not in puffer.getvalue(),
               f"der Fehler aus Lauf 36015927654 steht noch im Protokoll: "
               f"{puffer.getvalue()[-240:]}")
        pruefe(lade_state(r4).get("test_kampagne_id") == 21
               and bool(lade_state(r4).get("zuletzt_getestet")),
               f"Testversand-Nachweis fehlt im Status: {lade_state(r4)}")

        # 32) Ohne Freigabe wird nichts angelegt: eine unbekannte Testadresse
        #     endet mit Klickweg, BEVOR eine Kampagne oder ein Kontakt entsteht.
        kontakte.clear()
        listenmitglieder.clear()
        anrufe.clear()
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc32 = versende(r4, html, text, "X", dry_run=False, test_adresse=PROBE,
                            test_kontakt_anlegen=False)
        pruefe(rc32 == 1 and not any(m == "POST" for m, _, _ in anrufe),
               f"ohne Freigabe wurde geschrieben (rc={rc32}): {anrufe}")
        pruefe("kein Kontakt im Brevo-Konto" in puffer.getvalue()
               and "test_kontakt" in puffer.getvalue(),
               f"Abbruch nennt Zustand und Weg nicht: {puffer.getvalue()[-260:]}")

        # 33) Eine gesperrte Testadresse wird NICHT automatisch entsperrt:
        #     eine Sperre ist das Ergebnis einer Beschwerde/eines Bounces –
        #     die löst ein Mensch, nicht ein Cron.
        kontakte[PROBE] = True
        listenmitglieder.add(PROBE)
        gesperrt.add(PROBE)
        anrufe.clear()
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc33 = versende(r4, html, text, "X", dry_run=False, test_adresse=PROBE)
        pruefe(rc33 == 1 and not any(m == "POST" for m, _, _ in anrufe)
               and not any(m in ("PUT", "DELETE") for m, _, _ in anrufe),
               f"gesperrte Adresse löste Schreibzugriffe aus: {anrufe}")
        pruefe("Sperrliste" in puffer.getvalue() and "Unblock" in puffer.getvalue(),
               f"Befund nennt die Sperre/das Entsperren nicht: {puffer.getvalue()[-200:]}")

        # 34) Die echten Brevo-Absagen werden zu Klickwegen – und eine
        #     unbekannte Absage bleibt ohne Deutung (kein Befund ohne Beleg).
        hinweis34 = kampagnen_absage_hinweis(
            '{"code":"invalid_parameter","message":"There are no contacts associated '
            'with the given recipients info"}')
        pruefe("probelauf" in hinweis34.lower() and "double-opt-in" in hinweis34.lower(),
               f"Leerliste-Absage ohne nächsten Schritt: {hinweis34!r}")
        pruefe(kampagnen_absage_hinweis(
            '{"code":"invalid_parameter","message":"ReplyTo email should be valid"}') == "",
            "unbekannte Absage wurde gedeutet")

        _http_request = http_echt
        TRANSPORT = brevo
        TRANSPORT_GET = brevo_get
        os.environ["NEWSLETTER_SEND"] = ""
    except Exception as exc:  # noqa: BLE001
        import traceback
        fehler.append(f"Ausführung: {exc.__class__.__name__}: {exc}\n"
                      + traceback.format_exc()[-500:])
    finally:
        kadenz_mock.stop()
        reservierung_mock.stop()
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
          f"previewText/SSOT-Payload, Kampagnen-Schema (replyTo-String, emailTo-Liste), "
          f"Vorflug, Testversand-Verdrahtung, "
          f"Probelauf an leerer Liste (TEST-Kampagne ohne Empfänger, "
          f"Kontakt-/Listen-Nachtrag genau einmal, Sperre ohne Auto-Entsperren), "
          f"Client-Kennung und Kantenblockage, Wiederholung nur fürs Lesen, "
          f"Nachlese bei unklarem Sendegang, Versand-Halt, Versand-Ehrlichkeit, "
          f"State-Konfiguration, Host-Guard für BREVO_API_HOST).")
    return 0


# ---------------------------------------------------------------- Kampagnen-Schema
# Lauf 35904226864 (23.09.2026, 18:41 UTC, workflow_dispatch):
#   ❌ Kampagne nicht angelegt (HTTP 400: ReplyTo email should be valid ·
#      invalid_parameter)
# Test und Live sterben an derselben Stelle. Beide legen zuerst eine Kampagne
# an (`POST /emailCampaigns`) und senden erst danach (`sendTest` bzw. `sendNow`).
# Der Payload trug `replyTo` als Objekt `{"email": "…"}`. Das ist das Schema
# von SendSmtpEmail (Transaktion). CreateEmailCampaign will einen String
# (format: email). Quellen: developers.brevo.com/reference/create-email-campaign
# und getbrevo/brevo-go `lib/model_create_email_campaign.go` (`ReplyTo string`).
# Dieselbe Verwechslung hätte den Testversand einen Schritt später noch einmal
# getötet: `sendTest` erwartet `emailTo` als Liste von Strings, nicht als String
# (developers.brevo.com/reference/send-test-email). Ein leeres `emailTo` schickt
# die Probe an die gesamte Testliste des Kontos – eine ungültige Testadresse
# ist deshalb ein Abbruch, kein stiller Fallback.
#
# `textContent` und `status` stehen nicht im Kampagnen-Schema. Sie gehören zum
# Transaktions-Endpunkt. Mitzuschicken ist der nächste HTTP 400, sobald Brevo
# unbekannte Felder ablehnt; der Reply-To-Fehler kam zuerst und hat die Klasse
# verdeckt. Der Klartext bleibt lokal (QA, Archiv). Die Kampagne trägt HTML.
KAMPAGNEN_SCHEMA = frozenset({
    "name", "tag", "sender", "htmlContent", "htmlUrl", "templateId",
    "scheduledAt", "subject", "previewText", "replyTo", "toField",
    "recipients", "attachmentUrl", "inlineImageActivation", "mirrorActive",
    "footer", "header", "utmCampaign", "utmContent", "utmTerm", "params",
    "sendAtBestTime", "abTesting", "subjectA", "subjectB", "splitRule",
    "winnerCriteria", "winnerDelay", "ipWarmupEnable", "initialQuota",
    "increaseRate", "unsubscriptionPageId", "updateFormId",
    "emailExpirationDate",
})
# Felder, die schon einmal aus dem falschen Schema hierher gerutscht sind.
KAMPAGNEN_FREMDE = frozenset({"preheader", "textContent", "status", "to", "html"})
EMAIL_MUSTER = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,63}$")
TEST_ADRESSEN_MAX = 10


def email_aus_text(roh: str) -> str:
    """Eine Adresse aus Freitext, oder leer wenn keine gültige drinsteht.

    Akzeptiert `name@domain.tld` und `Name <name@domain.tld>`. Brevo prüft
    `format: email` streng – ein Anzeigename, ein Leerzeichen oder ein Objekt
    ist genau der 400er, an dem Lauf 35904226864 starb.
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
    """Testadressen für sendTest. → (liste, fehler).

    Komma, Semikolon oder Zeilenumbruch trennen mehrere Adressen. Ungültiges
    bricht ab: ein String statt Liste ist HTTP 400, eine leere Liste schickt
    die Probe an die ganze Testliste des Kontos.
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
                "ein falsches emailTo scheitert bei Brevo, ein leeres träfe die "
                "gesamte Testliste des Kontos.")
        if norm not in adressen:
            adressen.append(norm)
    if len(adressen) > TEST_ADRESSEN_MAX:
        return [], (f"Höchstens {TEST_ADRESSEN_MAX} Testadressen pro Lauf "
                    "(Brevo: 50 Testmails pro Tag).")
    return adressen, ""


def kampagnen_schema_verstoesse(payload: dict, *,
                                mit_empfaengern: bool = True) -> list[str]:
    """Menschenlesbare Verstöße gegen CreateEmailCampaign. Leer = senden darf.

    `mit_empfaengern=False` beschreibt die TEST-Kampagne. `recipients` ist im
    Schema optional (developers.brevo.com/reference/create-email-campaign:
    Pflicht wird `listIds` erst mit `scheduledAt`), und genau die Empfänger
    waren der Grund, an dem Lauf 36015927654 starb: eine noch leere
    Zielliste machte daraus `HTTP 400: There are no contacts associated with
    the given recipients info`. Für den Probelauf (sendTest an genau die
    eingegebenen Adressen) ist die Liste ohne Belang – sie darf deshalb nicht
    im Payload stehen, und wenn sie es doch täte, ist das ein Befund.
    """
    if not isinstance(payload, dict):
        return ["Payload ist kein Objekt"]
    funde: list[str] = []
    fremd = sorted(set(payload) - KAMPAGNEN_SCHEMA)
    if fremd:
        funde.append("Felder außerhalb CreateEmailCampaign: " + ", ".join(fremd))
    bekannt_fremd = sorted(set(payload) & KAMPAGNEN_FREMDE)
    if bekannt_fremd:
        funde.append("Transaktionsfelder in der Kampagne: " + ", ".join(bekannt_fremd))
    if "replyTo" in payload:
        reply = payload.get("replyTo")
        if not isinstance(reply, str):
            funde.append(
                "replyTo muss ein String sein, nicht "
                f"{type(reply).__name__} (Lauf 35904226864: Objekt → HTTP 400 "
                "ReplyTo email should be valid)")
        elif not email_aus_text(reply):
            funde.append(f"replyTo ist keine E-Mail: {reply!r}")
    sender = payload.get("sender")
    if not isinstance(sender, dict):
        funde.append("sender fehlt oder ist kein Objekt")
    else:
        if "id" in sender and "email" in sender:
            funde.append("sender darf nicht email und id gleichzeitig tragen")
        if "email" in sender and not email_aus_text(str(sender.get("email") or "")):
            funde.append(f"sender.email ist keine E-Mail: {sender.get('email')!r}")
        if not str(sender.get("name") or "").strip() and "id" not in sender:
            funde.append("sender.name fehlt")
    if not mit_empfaengern:
        if payload.get("recipients"):
            funde.append(
                "Test-Kampagne trägt recipients – eine leere Zielliste macht "
                "daraus HTTP 400 „There are no contacts associated with the "
                "given recipients info“ (Lauf 36015927654): der Testversand "
                "braucht nur emailTo")
    else:
        empfaenger = payload.get("recipients")
        ids = empfaenger.get("listIds") if isinstance(empfaenger, dict) else None
        if (not isinstance(ids, list) or not ids
                or not all(isinstance(i, int) and not isinstance(i, bool) for i in ids)):
            funde.append("recipients.listIds muss eine nichtleere Liste von Ganzzahlen sein")
    if (not str(payload.get("htmlContent") or "").strip()
            and not payload.get("htmlUrl") and not payload.get("templateId")):
        funde.append("htmlContent fehlt")
    if not str(payload.get("subject") or "").strip():
        funde.append("subject fehlt")
    if not str(payload.get("name") or "").strip():
        funde.append("name fehlt")
    return funde


def kampagnen_absage_hinweis(antwort: str) -> str:
    """Bekannte Kampagnen-Absagen in den nächsten Betreiberschritt übersetzen.

    Die rohe Brevo-Zeile nennt das Symptom, nicht den Klickweg. Drei Klassen
    sind hier schon aufgetreten bzw. drohen in genau diesem Konto – jede
    bekommt ihren Satz. Unbekanntes bleibt leer: lieber keine Deutung als eine
    falsche (die Regel des Repos: kein Befund ohne nächsten Schritt, aber auch
    kein Befund ohne Beleg).
    """
    text = (antwort or "").lower()
    if "no contacts associated with the given recipients" in text:
        return ("Die Zielliste hat 0 Kontakte (Brevo löst die Empfänger beim Anlegen "
                "auf). Listen-Versand: erst Anmeldungen sammeln (Double-Opt-In über "
                "das Formular) – oder die Zielliste in Brevo prüfen. Der PROBELAUF "
                "ist davon unabhängig: er legt die Kampagne ohne Empfängerliste an "
                "und schickt per sendTest an genau die eingegebenen Adressen.")
    if "dmarc policy requires domain authentication" in text:
        return ("Brevo verlangt eine authentifizierte Sender-Domain (DMARC). "
                "Nächster Schritt: Brevo → Senders, Domains & Dedicated IPs → "
                "Domains → Authentifizieren; die Zone prüft "
                "`scripts/newsletter_zustellbarkeit.py --pruefen`. Der DMARC-Satz "
                "steht dort auf `p=reject; aspf=s` – für den Probelauf ist "
                "`p=none; aspf=r` die richtige Stufe (Checkliste Schritt 2).")
    if "account_under_validation" in text or "account under validation" in text:
        return ("Das Brevo-Konto ist noch in der Prüfung („account_under_validation“). "
                "Nächster Schritt: Brevo → Absender/Domain verifizieren und die "
                "Kontoprüfung abschließen; Konten in Prüfung dürfen nur begrenzt "
                "Kampagnen anlegen.")
    if "not_enough_credits" in text or "insufficient credits" in text:
        return ("Brevo meldet zu wenig Guthaben/Kontingent. Nächster Schritt: "
                "Brevo → Settings → Plan (Free = 300 Mails/Tag) – die "
                "Zustellbarkeits-Wache vergleicht Plan-Grenze und Listenstärke.")
    return ""


def reply_to_abgelehnt(code: int, antwort: str) -> bool:
    """Hat Brevo genau die Antwortadresse abgelehnt – die Kampagne also nicht angelegt?"""
    if not antwort_endgueltig_abgelehnt(code, antwort):
        return False
    text = (antwort or "").lower().replace("_", "").replace("-", "").replace(" ", "")
    return "replyto" in text


def kampagnen_payload(name: str, betreff: str, html: str, absender: dict,
                      liste: str, preheader: str, reply_to: str, *,
                      mit_empfaengern: bool = True) -> dict:
    """Der Body von POST /emailCampaigns – nur Felder, die das Schema kennt.

    `mit_empfaengern=False` (reiner Testversand) lässt `recipients` WEG, statt
    eine leere Liste zu senden. Das ist die Reparatur von Lauf 36015927654
    (24.09.2026): Brevo löst die Empfänger beim Anlegen auf und weist eine
    Kampagne mit 0 Empfängern ab – auch dann, wenn sie nur als Behälter für
    eine Testmail (sendTest, an genau die eingegebenen Adressen) dient. Ohne
    `recipients` ist die TEST-Kampagne schemakonform und trifft nie eine Liste.
    """
    sender_email = email_aus_text(str(absender.get("email") or ""))
    payload = {
        "name": (name or "Digest")[:255],
        "subject": (betreff or "Newsletter")[:255],
        "htmlContent": html,
        "sender": {
            "name": (str(absender.get("name") or "FranksFinanzcheck").strip()
                     or "FranksFinanzcheck")[:70],
            "email": sender_email,
        },
        "previewText": ((preheader or "").strip() or betreff or "Newsletter")[:300],
        "mirrorActive": True,
    }
    if mit_empfaengern:
        payload["recipients"] = {"listIds": [int(liste)]}
    reply = email_aus_text(reply_to)
    if reply:
        payload["replyTo"] = reply
    return payload


def kampagne_anlegen(key: str, payload: dict, *,
                     mit_empfaengern: bool = True) -> tuple[int, str, dict]:
    """Kampagne anlegen. Bei Reply-To-Absage genau ein zweiter Anlauf.

    Der zweite Anlauf ist nur legitim, weil ein endgültiges HTTP 4xx bedeutet:
    nichts wurde angelegt. Er setzt die Antwortadresse auf den bereits
    verifizierten Absender – oder lässt sie weg, wenn genau die abgelehnt
    wurde. Andere 400er werden nicht wiederholt: das wäre derselbe Fehler
    zweimal und würde die Ursache verdecken.
    """
    verstoesse = kampagnen_schema_verstoesse(payload, mit_empfaengern=mit_empfaengern)
    if verstoesse:
        return 0, "Schema: " + "; ".join(verstoesse), payload
    code, antwort = TRANSPORT(key, "emailCampaigns", payload)
    if code in (200, 201) or not reply_to_abgelehnt(code, antwort):
        return code, antwort, payload
    sender_email = email_aus_text(str((payload.get("sender") or {}).get("email") or ""))
    aktuell = payload.get("replyTo")
    if not aktuell:
        return code, antwort, payload
    ersatz = dict(payload)
    if sender_email and aktuell != sender_email:
        ersatz["replyTo"] = sender_email
        grund = f"der verifizierten Absenderadresse {sender_email}"
    else:
        ersatz.pop("replyTo", None)
        grund = "ohne Reply-To (Brevo setzt dann den Absender)"
    print(f"   ⚠️  Reply-To {aktuell!r} von Brevo abgelehnt "
          f"({brevo_fehler(code, antwort)}). Zweiter Anlauf mit {grund}. "
          f"Antworten landen dort, bis {aktuell} in Brevo als Absender "
          "verifiziert ist (Senders & IPs → Add sender).")
    code2, antwort2 = TRANSPORT(key, "emailCampaigns", ersatz)
    return code2, antwort2, ersatz


def sendeaufruf_body(adressen: list[str]) -> dict | None:
    """sendTest: emailTo als Liste. sendNow: kein Body (das Schema hat keinen)."""
    if not adressen:
        return None
    if not all(isinstance(a, str) and email_aus_text(a) == a for a in adressen):
        raise ValueError("emailTo muss eine Liste gültiger, normalisierter Adressen sein")
    return {"emailTo": list(adressen)}


# ------------------------------------------------- Testadressen: Kontaktpflicht
# Zwei Absagen, die eine Testmail verhindern – beide sind gemessen bzw. belegt:
#   (1) Beim ANLEGEN der Kampagne: „There are no contacts associated with the
#       given recipients info“ (Lauf 36015927654, 24.09.2026). Sie entsteht aus
#       `recipients.listIds`, wenn die Zielliste 0 Abonnenten hat – deshalb
#       trägt eine TEST-Kampagne seit dieser Reparatur keine Empfänger mehr.
#   (2) Beim SENDEN der Testmail: „Test emails cannot be sent to non-existent/
#       blacklisted/without-contact-list users“ (Brevo, sendTest; belegt u. a.
#       in vjpixel/diaria-studio#8436, 19.09.2026). Eine Testadresse muss also
#       als Kontakt im Konto existieren, darf nicht gesperrt sein und braucht
#       eine Listen-Zugehörigkeit (Brevo-Hilfe „Create a test list“: „To add an
#       email address to your test list, you first have to add it to your
#       contacts.“).
# Der Probelauf aus Checkliste 6a fällt damit nicht mehr an Zuständen des
# Kontos um, die er selbst erzeugen kann: Er MISST die Testadresse vor der
# Kampagne, legt einen fehlenden Kontakt an (ohne Listen-Eintrag – kein
# Newsletter an jemanden, der nie zugestimmt hat) und trägt ihn nur dann in die
# Zielliste nach, wenn Brevo genau das verlangt (und die Freigabe es erlaubt).
TESTMAIL_CLASSES = {
    "blackListedEmails": "blacklist",
    "unexistingEmails": "unbekannt",
    "withoutListEmails": "ohne_liste",
}


def kontakt_lesen(key: str, adresse: str) -> tuple[str, dict, str]:
    """Zustand einer Adresse im Konto: 'kontakt' | 'kein-kontakt' | 'unklar'.

    `GET /v3/contacts/{identifier}` (developers.brevo.com/reference/get-contact-info):
    200 mit `emailBlacklisted`/`listIds`, 404 „Contact not found“. Jeder andere
    Ausgang ist UNKLAR und damit ein Abbruch – eine Vorprüfung, die bei
    Netzfehlern „gilt schon“ sagt, wäre schlimmer als keine.
    """
    pfad = "contacts/" + urllib.parse.quote(adresse, safe="@")
    code, antwort = TRANSPORT_GET(key, pfad)
    if code in (200, 201):
        try:
            dat = json.loads(antwort)
        except json.JSONDecodeError:
            return "unklar", {}, f"Antwort auf {pfad} ist kein JSON: {antwort[:160]}"
        if not isinstance(dat, dict):
            return "unklar", {}, f"Antwort auf {pfad} ist kein Objekt: {antwort[:160]}"
        return "kontakt", dat, ""
    if code == 404 or (code == 400 and "not found" in (antwort or "").lower()):
        return "kein-kontakt", {}, ""
    return "unklar", {}, f"{pfad}: {brevo_fehler(code, antwort)}"


def kontakt_anlegen(key: str, adresse: str) -> tuple[int, str]:
    """`POST /v3/contacts` – Kontakt ohne Listen-Eintrag (kein Newsletter-Abo).

    `updateEnabled: true`: existiert die Adresse doch schon, ist die Antwort ein
    Erfolg (204) statt eines 400 „Contact already exist“. Genau das ist der
    Unterschied zwischen einem idempotenten Nachtrag und einem Fehlalarm.
    """
    return TRANSPORT(key, "contacts", {"email": adresse, "updateEnabled": True})


def liste_aufnehmen(key: str, liste: str, adressen: list[str]) -> tuple[int, list[str], str]:
    """`POST /v3/contacts/lists/{id}/contacts/add` – bestehende Kontakte in die Liste.

    Dieser Endpunkt fügt hinzu, statt die Listen-Zugehörigkeiten zu ersetzen
    (ein `PUT /contacts/{id}` mit `listIds` würde andere Listen überschreiben –
    für einen Testnachtrag der falsche Hammer). Antwort:
    `{"contacts": {...}, "success": [...], "failure": [...]}`.
    → (rc, aufgenommene, meldung)
    """
    code, antwort = TRANSPORT(key, f"contacts/lists/{liste}/contacts/add",
                              {"emails": list(adressen)})
    if code not in (200, 201):
        return 1, [], brevo_fehler(code, antwort)
    try:
        dat = json.loads(antwort)
    except json.JSONDecodeError:
        dat = {}
    erfolg = [str(a) for a in (dat.get("success") or [])]
    fehler = [str(a) for a in (dat.get("failure") or [])]
    if fehler:
        return 1, erfolg, ("nicht aufgenommen: " + ", ".join(fehler))
    fehlend = [a for a in adressen if a not in erfolg] if erfolg else list(adressen)
    if fehlend:
        return 1, erfolg, ("ohne Quittung geblieben: " + ", ".join(fehlend))
    return 0, erfolg, ""


def testadressen_pruefen(key: str, adressen: list[str], *,
                         anlegen: bool) -> tuple[int, str, dict]:
    """Vorflug der Testadressen. → (rc, befund, zustand je Adresse)

    Gemessen wird, was Brevo für `sendTest` verlangt: Kontakt ja/nein,
    E-Mail-Sperre ja/nein, Listen-Zugehörigkeit. Ein fehlender Kontakt wird –
    sofern freigegeben – angelegt; eine Sperre wird NIE automatisch gelöst
    (eine Sperrliste ist eine Aussage eines Menschen oder eines Bounces, kein
    Tippfehler). Ohne Freigabe bricht der Lauf mit dem exakten Klickweg ab.
    """
    zustand: dict = {}
    for adresse in adressen:
        art, dat, meldung = kontakt_lesen(key, adresse)
        if art == "unklar":
            return 1, (f"Testadresse {adresse} nicht prüfbar ({meldung}) – kein "
                       "Versand: lieber fail-closed als eine Testmail an einen "
                       "ungeprüften Kontakt."), zustand
        if art == "kein-kontakt":
            if not anlegen:
                return 1, (
                    f"Testadresse {adresse} ist kein Kontakt im Brevo-Konto – "
                    "Brevo weist Testmails an unbekannte Adressen ab. Nächster "
                    "Schritt: Brevo → Contacts → Add a contact (exakt diese "
                    "Adresse), oder den Lauf mit angelegtem Kontakt starten "
                    "(Workflow-Eingabe `test_kontakt` = anlegen)."), zustand
            code, antwort = kontakt_anlegen(key, adresse)
            if code not in (200, 201, 204):
                return 1, (f"Testadresse {adresse} konnte nicht als Kontakt "
                           f"angelegt werden ({brevo_fehler(code, antwort)})."), zustand
            print(f"   ℹ️  Testadresse {adresse} war kein Kontakt im Konto und "
                  "wurde als Kontakt angelegt (ohne Listen-Eintrag – kein "
                  "Newsletter-Abo).")
            art, dat, meldung = kontakt_lesen(key, adresse)
            if art != "kontakt":
                return 1, (f"Testadresse {adresse} nach dem Anlegen nicht "
                           f"nachlesbar ({meldung or art})."), zustand
        if dat.get("emailBlacklisted") is True:
            return 1, (
                f"Testadresse {adresse} steht im Brevo-Konto auf der "
                "E-Mail-Sperrliste – Testmails dorthin weist Brevo ab "
                "(„Test emails cannot be sent to non-existent/blacklisted/"
                "without-contact-list users“). Nächster Schritt: Brevo → "
                "Contacts → Kontakt öffnen → „Unblock“ (bewusst ein Mensch: "
                "eine Sperre kann das Ergebnis einer Beschwerde sein)."), zustand
        zustand[adresse] = dat
    return 0, "", zustand


def testmail_abweisung(antwort: str) -> dict:
    """Brevos sendTest-Absage in Adressklassen zerlegen.

    Body laut developers.brevo.com/reference/send-test-email (400):
      {"code": "invalid_parameter",
       "message": "Test email could not be sent to the following email addresses",
       "blackListedEmails": [...], "unexistingEmails": [...],
       "withoutListEmails": [...]}
    → {"blacklist": […], "unbekannt": […], "ohne_liste": […], "roh": "…"}
    """
    aus: dict = {"blacklist": [], "unbekannt": [], "ohne_liste": [], "roh": ""}
    try:
        dat = json.loads(antwort or "")
    except json.JSONDecodeError:
        return aus
    if not isinstance(dat, dict):
        return aus
    aus["roh"] = str(dat.get("message") or "")
    for feld, klasse in TESTMAIL_CLASSES.items():
        werte = dat.get(feld)
        if isinstance(werte, list):
            aus[klasse] = [str(w) for w in werte if w]
    return aus


def testmail_nachtragen(key: str, liste: str, adressen: list[str], antwort: str, *,
                        anlegen: bool) -> tuple[int, list[str], str]:
    """Reparatur einer sendTest-Absage: Kontakt nachtragen, Liste nachtragen.

    Nur für die beiden Klassen, die eine Reparatur überhaupt kennen
    (unbekannte Adresse → Kontakt anlegen; ohne Listen-Eintrag → in die
    Zielliste aufnehmen). Gesperrte Adressen bleiben gesperrt – das ist eine
    Betreiber-Entscheidung, kein Automatismus.
    → (rc, wiederholbare_adressen, meldung)
    """
    klasse = testmail_abweisung(antwort)
    kandidaten = [a for a in klasse["unbekannt"] + klasse["ohne_liste"] if a in adressen]
    if not kandidaten:
        return 1, [], ""
    if not anlegen:
        return 1, [], (
            f"Brevo lehnt die Testmail an {', '.join(kandidaten)} ab (nicht "
            "vorhandener Kontakt oder ohne Listen-Eintrag). Nächster Schritt: "
            "Brevo → Contacts → Add a contact, dann Brevo → Contacts → Listen → "
            "Blog-Abonnenten → Add contacts. Ohne diesen Eintrag bleibt der "
            "Testversand gesperrt (Workflow-Eingabe `test_kontakt` = anlegen "
            "macht das automatisch).")
    offen = list(kandidaten)
    for adresse in list(offen):
        if adresse in klasse["unbekannt"]:
            code, ant = kontakt_anlegen(key, adresse)
            if code not in (200, 201, 204):
                offen.remove(adresse)
                print(f"   ⚠️  Kontakt {adresse} nicht angelegt "
                      f"({brevo_fehler(code, ant)}).")
    if not offen:
        return 1, [], ""
    rc, aufgenommen, meldung = liste_aufnehmen(key, liste, offen)
    if rc != 0:
        return 1, [], (f"Testadressen {', '.join(offen)} konnten nicht in die "
                       f"Zielliste {liste} aufgenommen werden ({meldung}) – "
                       "Brevo verlangt für Testmails eine Listen-Zugehörigkeit.")
    print(f"   ℹ️  Testadressen {', '.join(aufgenommen)} in die Zielliste "
          f"{liste} aufgenommen (Zustimmung des Betreibers über die "
          "Testadress-Eingabe; jede Mail trägt den Ein-Klick-Abmeldelink) – "
          "genau das verlangt Brevo für Testmails an Kontakte ohne Liste.")
    return 0, list(aufgenommen), ""


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
        return 1, ("Absender-Vorprüfung nicht möglich (" + brevo_fehler(code, antwort)
                   + ") – kein Versand: lieber fail-closed, als eine Kampagne mit "
                   "ungeprüftem Absender anzulegen.")
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
                   "Bestätigungscode aus der Absender-Mail eingeben bzw. die "
                   "Domain-Authentifizierung auf „verifiziert“ bringen (Checkliste "
                   "Schritt 2: `brevo-code`-TXT und die zwei DKIM-CNAMEs – der "
                   "SPF-Eintrag ist hier nicht der Hebel, er alignt auf Brevos "
                   "geteiltem Weg nie), dann erneut laufen lassen.")
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


def kadenz_pruefen(root: str) -> str:
    """Status strikt lesen: ein kaputtes Journal darf nie einen Versand erlauben."""
    pfad, _, _ = zustand_konfig(root)
    with open(os.path.join(root, pfad), encoding="utf-8") as fh:
        state = json.load(fh)
    return schedule.versandpause(state)


def termin_reservieren(root: str) -> None:
    """Vor sendNow schreiben; selbst ein Prozessabbruch verbraucht diesen Termin."""
    state = lade_state(root)
    termine = state.get("versand_termine", [])
    if "versand_termine" not in state and state.get("zuletzt_versandt"):
        termine = [state["zuletzt_versandt"]]
    state["versand_termine"] = (termine + [schedule.jetzt().isoformat()])[-60:]
    speichere_state(root, state)
    if lade_state(root).get("versand_termine") != state["versand_termine"]:
        raise OSError("Versandtermin konnte nicht verifiziert werden")


def versende(root: str, html: str, text: str, betreff: str, *, dry_run: bool,
             test_adresse: str = "", preheader: str = "",
             test_kontakt_anlegen: bool = True) -> int:
    """Kampagne bei Brevo anlegen und senden. Dreifach verriegelt, s. Dokumentation.

    Seit der Reparatur von Lauf #14 zusätzlich: Absender/Reply-To aus der
    Studio-SSOT, `previewText` statt des nicht existierenden `preheader`-Felds,
    Vorprüfung von Absender + Liste vor dem Anlegen, strukturierte Fehler,
    Wiederholung nur bei transienten Störungen.
    """
    # Der Netzweg gehört vor jede Anfrage: ein falscher Host würde den
    # API-Schlüssel an eine fremde Domain schicken. Kein Retry, kein Netzversuch.
    host_fehler = api_host_fehler()
    if host_fehler:
        print(f"   ❌ kein Versand: {host_fehler}")
        return 1
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
    # Testadressen VOR jedem Netzaufruf. Eine ungültige Adresse darf nicht zur
    # Liste durchfallen, auch nicht wenn zusätzlich NEWSLETTER_SEND=ja steht:
    # der Probelauf, der scheitert, ist kein Live-Versand.
    adressen: list[str] = []
    if (test_adresse or "").strip():
        adressen, adress_fehler = test_adressen_lesen(test_adresse)
        if adress_fehler or not adressen:
            print(f"   ❌ kein Versand: {adress_fehler or 'Testadresse fehlt'}")
            return 1
    if not bestaetigt and not adressen:
        print("   ❌ kein Versand: NEWSLETTER_SEND=ja fehlt. Echte Listen werden nur "
              "bestätigt getroffen; für Probeläufe --test-adresse nutzen.")
        return 1
    if not re.fullmatch(r"\d+", liste):
        print(f"   ❌ kein Versand: BREVO_LIST_ID ist keine Zahl ({liste!r}) – Brevo liest "
              "die Listen-ID als Ganzzahl (Zahl in der Listen-URL).")
        return 1
    if bestaetigt and not adressen:
        sperre = sperre_pruefen(root)
        if sperre:
            print(f"   ❌ kein Listen-Versand: {sperre}")
            return 1
    if not adressen:
        try:
            pause = kadenz_pruefen(root)
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            print(f"   ❌ kein Listen-Versand: Versandhistorie nicht sicher lesbar: {exc}")
            return 1
        if pause:
            print(f"   ℹ️  {pause}")
            return 0
    absender = absender_konfig(root)
    # live=False bei Testversand: die Prüfung „Liste hat 0 Abonnenten“ gilt nur
    # dem echten Listen-Versand (sendNow). Ein sendTest trifft genau die
    # eingegebenen Adressen, nie die Liste – genau deshalb ist er laut
    # Checkliste der vorgesehene Probelauf, BEVOR die Liste Abonnenten hat.
    # Ihn an der leeren Liste zu blockieren, würde den Probelauf unmöglich
    # machen (Fehlerklasse des 23.09.2026: dokumentierter Weg, den kein Lauf
    # gehen konnte). Existenz-Prüfungen (Absender da? verifiziert? Liste
    # vorhanden?) bleiben auch beim Testversand an – die Kampagne trägt die
    # Liste aber nicht mehr (s. kampagnen_payload: 0 Empfänger = HTTP 400).
    rc_vor, befund = vorflug(key, liste, absender["email"],
                             live=bool(bestaetigt) and not adressen)
    if rc_vor != 0:
        print(f"   ❌ Vorprüfung fehlgeschlagen: {befund}")
        return 1
    # Zweite Vorprüfung, nur für den Probelauf: Brevo nimmt Testmails ausschließlich
    # an existierende, nicht gesperrte Kontakte an. Gemessen wird vor der
    # Kampagne, damit der Lauf nicht erst eine Kampagne anlegt und dann an der
    # Adresse scheitert – und damit „kein Kontakt“ nie als „Brevo kaputt“
    # missverstanden wird.
    if adressen:
        rc_t, befund_t, _ = testadressen_pruefen(key, adressen,
                                                 anlegen=test_kontakt_anlegen)
        if rc_t != 0:
            print(f"   ❌ kein Testversand: {befund_t}")
            return 1
    roh_reply = absender["antwort_an"]
    reply = email_aus_text(roh_reply)
    if roh_reply and not reply:
        print(f"   ⚠️  Antwortadresse {roh_reply!r} ist keine gültige E-Mail – "
              f"Versand nutzt die Absenderadresse {absender['email']}.")
        reply = email_aus_text(absender["email"])
    # CreateEmailCampaign: replyTo ist ein String, nicht {"email": "…"}.
    # textContent und status gehören nicht in dieses Schema (Lauf 35904226864).
    # Eine TEST-Kampagne heißt „TESTLAUF …“ und trägt KEINE Empfänger: sie ist
    # der Behälter für den Inhalt, den sendTest an genau die eingegebenen
    # Adressen schickt. Mit `recipients.listIds` (leere Liste) starb Lauf
    # 36015927654 an „There are no contacts associated with the given
    # recipients info“ – der Probelauf war damit per Konstruktion unmöglich.
    test_lauf = bool(adressen)
    heute = datetime.date.today().isoformat()
    name = (f"TESTLAUF {heute} – Probe an {', '.join(adressen)}" if test_lauf
            else f"Digest {heute}")
    payload = kampagnen_payload(name, betreff, html, absender,
                                liste, preheader, reply,
                                mit_empfaengern=not test_lauf)
    code, antwort, payload = kampagne_anlegen(key, payload,
                                              mit_empfaengern=not test_lauf)
    if code not in (200, 201):
        if str(antwort).startswith("Schema:"):
            print(f"   ❌ Kampagne nicht angelegt ({antwort}) – nichts an Brevo geschickt.")
            return 1
        print(f"   ❌ Kampagne nicht angelegt ({brevo_fehler(code, antwort)})")
        hinweis = kampagnen_absage_hinweis(antwort)
        if hinweis:
            print(f"   ℹ️  {hinweis}")
        if not antwort_endgueltig_abgelehnt(code, antwort):
            print("   ℹ️  Kein zweiter Anlauf: dieser Aufruf war SCHREIBEND. Ein "
                  "Wiederholen nach 502/Zeitlimit würde die Kampagne mehrfach "
                  "anlegen. Falls Brevo die Anlage trotzdem annahm, liegt jetzt "
                  "ein Entwurf „Digest <Datum>“ im Konto (Kampagnen → Drafts) – "
                  "vor dem nächsten Lauf löschen oder verwenden, sonst wächst der "
                  "Stapel nur.")
        return 1
    try:
        kennung = json.loads(antwort).get("id")
    except json.JSONDecodeError:
        kennung = None
    if not kennung:
        print(f"   ❌ Antwort ohne Kampagnen-ID: {antwort[:400]}")
        return 1
    # sendTest: emailTo ist eine LISTE von Strings. Ein einzelner String ist
    # HTTP 400; ein leeres emailTo trifft die ganze Testliste des Kontos.
    # sendNow hat keinen Body – `{}` wäre eine zweite, unbelegte Abweichung.
    try:
        body = sendeaufruf_body(adressen)
    except ValueError as exc:
        print(f"   ❌ kein Versand: {exc} – die Kampagne {kennung} bleibt Entwurf.")
        return 1
    pfad = (f"emailCampaigns/{kennung}/sendTest" if adressen
            else f"emailCampaigns/{kennung}/sendNow")
    if not adressen:
        try:
            termin_reservieren(root)
        except (OSError, ValueError, TypeError) as exc:
            print(f"   ❌ kein Versand: Versandtermin nicht sicher gespeichert: {exc}")
            return 1
    code2, antwort2 = TRANSPORT(key, pfad, body)
    # Testmail-Absage mit Adressklassen (Kontakt fehlt / ohne Listen-Eintrag):
    # reparieren und GENAU EINMAL wiederholen. Der 400er ist hier ein Beleg
    # dafür, dass nichts rausging (Brevo nennt die abgewiesenen Adressen
    # einzeln) – ein Wiederholen ist also kein Doppelversand, sondern der
    # vorgesehene zweite Schritt. Gesperrte Adressen werden nicht angefasst.
    SEND_OK = (200, 201, 202, 204)
    if code2 not in SEND_OK and adressen and antwort_endgueltig_abgelehnt(code2, antwort2):
        klassen = testmail_abweisung(antwort2)
        if klassen["unbekannt"] or klassen["ohne_liste"] or klassen["blacklist"]:
            print("   ℹ️  Brevo nennt die abgewiesenen Testadressen einzeln – "
                  f"unbekannt: {klassen['unbekannt'] or '—'}, ohne Liste: "
                  f"{klassen['ohne_liste'] or '—'}, gesperrt: "
                  f"{klassen['blacklist'] or '—'}.")
        _, nachgetragen, meldung_n = testmail_nachtragen(
            key, liste, adressen, antwort2, anlegen=test_kontakt_anlegen)
        if meldung_n:
            print(f"   ⚠️  {meldung_n}")
        if nachgetragen:
            rest = [a for a in adressen if a not in nachgetragen]
            if rest:
                print(f"   ⚠️  Nicht reparierbar: {', '.join(rest)} – diese Adressen "
                      "bleiben unerreicht (Grund steht oben); erneut laufen lassen, "
                      "sobald der Kontakt im Konto sauber ist.")
            print(f"   ℹ️  sendTest an {', '.join(nachgetragen)} abgewiesen "
                  f"({brevo_fehler(code2, antwort2)}) – nach dem Nachtrag genau "
                  "ein Wiederholungsversuch an die reparierten Adressen.")
            code2, antwort2 = TRANSPORT(key, pfad, sendeaufruf_body(nachgetragen))
    if code2 not in SEND_OK:
        # Der seltene, teure Fall: die Antwort auf den Sende-Aufruf ist verloren
        # gegangen (Kantenblock, 502, Zeitlimit), die Sendung kann aber schon
        # angenommen sein. Wiederholen hieße: die Liste ein zweites Mal treffen.
        # Also nachlesen statt nachdrücken – und den Befund so melden, wie die
        # Wahrheit ist (Lauf #14/#21-Lehre: die Annotation darf nicht lügen).
        if antwort_endgueltig_abgelehnt(code2, antwort2):
            print(f"   ❌ Versand fehlgeschlagen ({brevo_fehler(code2, antwort2)}) "
                  "– die Kampagne existiert als Entwurf, versandt ist nichts.")
            return 1
        kunde, grund = versand_nachlesen(key, kennung)
        if kunde == "raus":
            print(f"   ✅ VERSAND ERFOLGT (Kampagne {kennung}) – die Antwort auf den "
                  f"Sende-Aufruf war unleserlich ({brevo_fehler(code2, antwort2)}), "
                  f"die Kampagnen-Akte belegt die Sendung aber: {grund}.")
            return _status_schreiben(root, kennung, betreff,
                                     ", ".join(adressen), vorab_rc=1)
        if kunde == "nicht raus":
            print(f"   ❌ Versand nicht angekommen ({brevo_fehler(code2, antwort2)}); "
                  f"Nachlese: {grund} – es ist nichts versandt, der nächste Lauf darf "
                  "erneut senden.")
            return 1
        # UNKLAR: weder Beleg noch Gegenteil. Hier entscheidet die Richtung des
        # Schadens: eine verpasste Ausgabe ist ärgerlich, eine Doppelzustellung an
        # die ganze Liste erzeugt Abmeldungen, Spam-Beschwerden und – bei Gmail –
        # einen Reputationsschaden, der wochenlang nachwirkt. Also: NICHTS
        # wiederholen, NICHTS verbuchen, aber den nächsten Listen-Versand
        # anhalten, bis ein Mensch im Konto nachgesehen hat (Sperre im Status).
        print(f"   ❌ VERSAND-STATUS UNKLAR ({brevo_fehler(code2, antwort2)}); Nachlese: "
              f"{grund}. Der Versand wurde NICHT wiederholt (Doppelungsgefahr) und "
              f"der Duplikatsschutz wurde NICHT verbucht. Kampagne {kennung} in Brevo "
              "prüfen (Kampagnen → Detail → Sends); ist sie raus, data/"
              "newsletter_state.json um \"zuletzt_versandt\" und \"kampagne_id\" "
              "ergänzen. Bis dahin hält eine Sperre jeden weiteren "
              "Listen-Versand an (Release: Block \"versand_unklar\" in data/"
              "newsletter_state.json löschen bzw. durch \"versand_unklar_geloest\" "
              "mit Datum ersetzen – bewusst Mensch, nicht Automatik).")
        sperre_setzen(root, kennung, betreff)
        return 1
    ziel = ", ".join(adressen)
    print(f"   ✅ {'Testversand an ' + ziel if adressen else 'Versand angestoßen'}"
          f" (Kampagne {kennung})")
    return _status_schreiben(root, kennung, betreff, ziel, vorab_rc=0)


def _status_schreiben(root: str, kennung, betreff: str, test_adresse: str, *,
                      vorab_rc: int) -> int:
    """Versandstatus festschreiben – nachgelesen, nicht vermutet.

    Der Versand ist RAUS – ab hier darf kein Fehler mehr so gemeldet werden,
    als hätte nichts stattgefunden. Genau das passierte bei einer
    mikroskopischen Fehlerklasse: scheiterte das Status-Schreiben NACH dem
    erfolgreichen sendNow, meldete der Lauf rot und die Annotation behauptete
    „es ist nichts versandt“ – der Empfänger hielt die Mail indes in der Hand.
    Jetzt: der Befund nennt die Wahrheit (VERSAND ERFOLGT) und der Workflow
    spricht sie entsprechend aus. Risiko bei nicht schreibbarem Status:
    der nächste Lauf kennt die Ausgabe nicht und könnte doppelt liefern –
    darum rc 1, damit der Befund im Alerting landet.
    """
    try:
        state = lade_state(root)
        id_feld = "test_kampagne_id" if test_adresse else "kampagne_id"
        zeit_feld = "zuletzt_getestet" if test_adresse else "zuletzt_versandt"
        state.update({zeit_feld: datetime.datetime.now(datetime.timezone.utc)
                      .isoformat(timespec="seconds"), id_feld: kennung})
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
        if lade_state(root).get(id_feld) != kennung:
            raise OSError("Nachkontrolle: Status trägt die Kampagnen-ID nicht "
                          "(Schreib- oder Lesefehler)")
    except OSError as exc:
        print(f"   ❌ VERSAND ERFOLGT (Kampagne {kennung}), aber der Status konnte nicht "
              f"geschrieben werden: {exc} – der nächste Lauf kennt diese Ausgabe nicht "
              f"(Doppelungsgefahr). data/newsletter_state.json prüfen, Duplikatschutz "
              f"nicht umgehen.")
        return 1
    return vorab_rc


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
    return (f"der Status trägt den Block „versand_unklar“ (Kampagne "
            f"{block.get('kampagne_id', '?')}, notiert {block.get('zeitpunkt', '?')}): "
            "ein früherer Sende-Aufruf ist ohne belegbares Ergebnis geblieben. "
            "Erst in Brevo nachsehen (Kampagnen → Detail → Sends) und den Block "
            "auflösen – sonst droht dieselbe Ausgabe zweimal im Postfach.")


def sperre_setzen(root: str, kennung, betreff: str) -> None:
    """Halt schreiben (best effort): der nächste Lauf muss ihn sehen können."""
    try:
        state = lade_state(root)
        state["versand_unklar"] = {"kampagne_id": kennung,
                                   "betreff": betreff,
                                   "zeitpunkt": datetime.datetime.now(datetime.timezone.utc)
                                   .isoformat(timespec="seconds")}
        speichere_state(root, state)
    except OSError as exc:
        print(f"   ⚠ Sperre konnte nicht geschrieben werden ({exc}) – der nächste Lauf "
              "kennt den Zweifel nicht und könnte dieselbe Ausgabe erneut senden.")


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
    ap.add_argument("--test-kontakt-nicht-anlegen", action="store_true",
                    help="Testversand ohne Schreibzugriff auf Kontakte: eine Adresse, "
                         "die im Brevo-Konto fehlt oder in keiner Liste steht, führt "
                         "dann zum Abbruch mit Klickweg statt zum Nachtrag")
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
    pfad, _, _ = zustand_konfig(root)
    try:
        with open(os.path.join(root, pfad), encoding="utf-8") as fh:
            state = json.load(fh)
        if not isinstance(state, dict):
            raise ValueError("Versandstatus ist kein Objekt")
    except FileNotFoundError:
        state = {}  # nur Vorschau/Erstaufbau; Live ohne Status wurde oben gesperrt
    except (OSError, ValueError) as exc:
        print(f"❌ Versandstatus defekt, nicht überschrieben: {exc}")
        return 1
    halt = sperre_pruefen(root)
    if halt:
        # Nicht nur im Sendeschritt: ein Lauf, der den Halt verschweigt, lässt
        # den nächsten Betreiber glauben, der Newsletter laufe nur gerade nicht.
        print(f"🛑 Der Versand ist angehalten: {halt}")
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
        # ohne --live real (sendTest an genau eine Adresse) – sonst wäre der
        # dokumentierte Probelauf `--send --test-adresse X` eine stille
        # Vorschau, und genau so lief der 23.09.2026: grün, aber keine Mail.
        rc_gesamt = max(rc_gesamt, versende(root, html, text, betreff,
                                            dry_run=not (args.live or bool(args.test_adresse)),
                                            test_adresse=args.test_adresse,
                                            preheader=ausgabe.get("preheader", ""),
                                            test_kontakt_anlegen=not args.test_kontakt_nicht_anlegen))
    else:
        print("   (kein Versand – --send fehlt; gebaute Digeste bleiben bewusst lokal)")
    return rc_gesamt


if __name__ == "__main__":
    sys.exit(main())
