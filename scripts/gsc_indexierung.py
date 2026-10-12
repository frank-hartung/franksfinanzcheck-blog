#!/usr/bin/env python3
"""gsc_indexierung.py – Indexierung bei Google ANFRAGEN, nicht nur hoffen.

WARUM DIESES SKRIPT EXISTIERT (Auftrag 12.10.2026: „alle Seiten verifiziert und
indexiert auf Premium-Level einer Profi-Agentur")
-----------------------------------------------------------------------------
Bis zu diesem Skript kannte das Projekt drei Wege in den Google-Index:

  1. `layouts/sitemap.xml`  – Google holt sich die URLs selbst (Entdeckung)
  2. robots.txt + Canonical – Google darf und soll sie indexieren (Erlaubnis)
  3. Warten                 – ob und wann der Crawler vorbeikommt (Zufall)

Was fehlte, war die vierte Stufe, die in jeder Agentur Standard ist: **die
aktive Indexierungs-Anfrage**. Google stellt dafür die URL Inspection API der
Search Console bereit – derselbe Knopf wie „Indexierung beantragen" in der
Oberfläche, nur maschinell. Ein neuer Artikel ist damit nicht „irgendwann"
im Index, sondern in der Regel binnen Stunden geprüft.

Harte Grenzen, die dieses Skript respektiert (statt sie zu umgehen):
  * 200 Anfragen je Property und Tag, 600 je Minute (Google-Kontingent).
  * Die API ist NICHT der „Google Indexing API"-Mythos: Diese Skript fragt den
    IndexierungsSTATUS ab und bittet um erneutes Crawlen – für eine normale
    Website ist das der einzige offizielle Weg. (Die separate Indexing API gilt
    ausschließlich für JobPosting-/BroadcastEvent-Seiten; sie hier zu benutzen
    wäre ein Richtlinienverstoß.)
  * Das Dienstkonto braucht in der Search Console die Berechtigung
    **„Vollständig" (Owner)**. „Eingeschränkt" reicht für den Lese-Import
    (`scripts/gsc_import.py`), aber nicht für eine Anfrage: Google antwortet
    dann mit 403. Das Skript meldet diesen Fall ausdrücklich, statt ihn als
    „kein Zugriff" zu verschlucken.

QUELLE DER URLS
  Wie überall seit dem 12.10.2026: die Sitemap, nicht eine Namensliste
  (`scripts/indexierbare_seiten.py`). Eine Seite, die indexierbar ist, steht in
  der Queue; eine Seite, die auf noindex geht, verschwindet von selbst daraus.

AUFRUF
  python3 scripts/gsc_indexierung.py --selftest        # offline, kein Netz
  python3 scripts/gsc_indexierung.py --plan            # was wäre dran? (kein API-Aufruf)
  python3 scripts/gsc_indexierung.py --dry-run         # inkl. Token/Status-Check, ohne Anfrage
  python3 scripts/gsc_indexierung.py                   # anfragen (bis zum Tageskontingent)
  python3 scripts/gsc_indexierung.py --live            # Queue aus der LIVE-Sitemap
  python3 scripts/gsc_indexierung.py --limit 20        # höchstens 20 URLs in diesem Lauf
  python3 scripts/gsc_indexierung.py --tage 21         # nur Seiten mit lastmod in den letzten 21 Tagen
  python3 scripts/gsc_indexierung.py --url https://franksfinanzcheck.de/posts/x/
  python3 scripts/gsc_indexierung.py --pruefen         # NUR Status abfragen, nicht einreichen

ZUGANG (Umgebungsvariablen bzw. GitHub-Secrets – niemals im Repo)
  GSC_SITE_URL                 z. B. "sc-domain:franksfinanzcheck.de"
  GSC_SERVICE_ACCOUNT_JSON     Inhalt der JSON-Schlüsseldatei des Dienstkontos
  (lokal alternativ GSC_SERVICE_ACCOUNT_FILE=/pfad/zur/datei.json)

  Ohne Zugang endet der Lauf mit Status `nicht_konfiguriert` und Exit 0 – genau
  wie `scripts/gsc_import.py`. Ein nicht eingerichtetes Konto ist kein Defekt,
  sondern ein Zustand; verschwiegen wird er trotzdem nicht.

ZUSTAND
  data/gsc_indexierung_state.json   je URL: letzte Anfrage, Google-Antwort,
                                    Fingerabdruck (lastmod) und Fehlerzähler.
  Versioniert, damit das Tageskontingent nicht von flüchtigen Runnern verbrannt
  wird. Der Pfad steht in der STATE_ONLY-Negativliste des Deploy-Gates: ein
  reines Zustands-Lebenszeichen löst keinen Livegang aus.

EXIT
  0 = grün (oder bewusst nicht konfiguriert / Kontingent ausgeschöpft)
  1 = mindestens eine URL wurde von Google abgelehnt (403/404/5xx dauerhaft)
  2 = Werkzeugfehler (Sitemap fehlt, Schlüssel unlesbar, Selbsttest rot)

Nur Standardbibliothek + `openssl` für die RS256-Signatur – dieselbe Kette,
die `scripts/gsc_import.py` bereits beweist. Kein pip im Workflow nötig.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Die Token-Kette (JWT → RS256 → OAuth) ist in gsc_import.py bereits gebaut,
# selbstgetestet und im Qualitäts-Gate verdrahtet. Sie hier zu kopieren hieße,
# eine zweite Wahrheit über dieselbe Signatur anzulegen.
from gsc_import import (  # noqa: E402
    GscFehler,
    default_http,
    hole_sites,
    rs256_signatur,
)
from indexierbare_seiten import (  # noqa: E402
    SitemapFehler,
    hole_seiten,
    live_sitemap_url,
    nur_frische,
    reihenfolge,
)

ROOT = Path(__file__).resolve().parent.parent
STATE_DATEI = ROOT / "data" / "gsc_indexierung_state.json"

# Schreib-Scope: `gsc_import.py` liest nur (webmasters.readonly). Eine
# Indexierungs-Anfrage ist ein Schreibvorgang und braucht den vollen Scope.
SCOPE = "https://www.googleapis.com/auth/webmasters"
TOKEN_URL = "https://oauth2.googleapis.com/token"
INSPECT_TMPL = ("https://searchconsole.googleapis.com/v1/urlInspection/index:inspect")

# Google-Kontingent der URL Inspection API je Property und Tag.
TAGESKONTINGENT = 200
# Puffer: Lieber 195 Anfragen als eine rote Nacht wegen einer Race mit dem
# Kontingent-Zähler (Google zählt pro Property, nicht pro Lauf).
SICHERHEITSABSTAND = 5

# Erneute Anfrage frühestens nach dieser Frist, wenn Google die Seite bereits
# als indexiert gemeldet hat. Sonst verbrennt ein täglicher Lauf das Kontingent
# mit Seiten, die längst drin sind – und die wirklich neuen kämen nicht dran.
WIEDERVORLAGE_TAGE_INDEXIERT = 28
# … und nach dieser Frist, wenn die Seite noch NICHT indexiert ist: Google
# braucht Zeit, und eine Anfrage im Stunden-Takt ändert daran nichts.
WIEDERVORLAGE_TAGE_OFFEN = 7

# Felder der Google-Antwort, die wir aufheben. Bewusst als Liste und nicht als
# blindes `dict(antwort)`: Google ergänzt Felder, und ein State-File, das jede
# API-Änderung mitschreibt, wird unlesbar. Unbekannte Felder werden zusätzlich
# als Schlüsselnamen notiert, damit eine API-Änderung sichtbar bleibt.
ANTWORT_FELDER = (
    "verdict", "coverageState", "indexingState", "lastCrawlTime",
    "pageFetchState", "robotsTxtState", "crawledAs", "referringUrls",
)

# Abdeckungszustände, die Google als „nicht im Index" wertet. Sie sind der
# eigentliche Nutzen dieses Skripts: Wer sie kennt, kann reagieren, statt auf
# Traffic zu warten, der nie kommt.
NICHT_INDEXIERT = {
    "crawled - currently not indexed",
    "discovered - currently not indexed",
    "excluded by 'noindex' tag",
    "excluded by robots.txt",
    "duplicate without user-selected canonical",
    "alternate page with proper canonical tag",
    "soft 404",
    "not found (404)",
    "redirect",
    "blocked due to unauthorized request",
    "server error (5xx)",
}


class IndexierungsFehler(RuntimeError):
    """Werkzeugfehler: Exit 2, kein stilles Grün."""


# ---------------------------------------------------------------- Zustand
def lade_state(pfad: Path = STATE_DATEI) -> dict:
    if not pfad.exists():
        return {"schema": 1, "urls": {}}
    try:
        roh = json.loads(pfad.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        # Fail-closed wie artefakt_waechter.py: Ein kaputtes Gedächtnis darf
        # nicht aussehen wie ein leeres (sonst wird das Kontingent doppelt
        # verbrannt, ohne dass jemand es merkt).
        raise IndexierungsFehler(
            f"{pfad} ist unlesbar ({exc}). Zustand reparieren oder löschen – "
            "ein kaputtes Gedächtnis wird hier nicht still als leer behandelt."
        ) from exc
    if not isinstance(roh, dict) or not isinstance(roh.get("urls"), dict):
        raise IndexierungsFehler(f"{pfad} hat nicht die Form {{schema, urls}}.")
    return roh


def schreibe_state(state: dict, pfad: Path = STATE_DATEI) -> None:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8")
    tmp.replace(pfad)


def eintrag(state: dict, url: str) -> dict:
    return state.setdefault("urls", {}).setdefault(url, {})


# ---------------------------------------------------------------- Planung
def ist_fällig(eintrag_url: dict, heute: dt.date) -> tuple[bool, str]:
    """Entscheidet, ob eine URL heute eine Anfrage verdienen würde.

    Regel (ohne Namenseinträge, nur aus dem Zustand abgeleitet):
      * nie angefragt            → fällig
      * Fehler beim letzten Mal  → fällig (max. 3 Versuche je Fingerabdruck)
      * indexiert                → nach 28 Tagen erneut (Auffrischung)
      * nicht indexiert/unbekannt→ nach 7 Tagen erneut
      * Inhalt geändert (lastmod)→ sofort fällig, denn dann ist die alte
        Antwort überholt
    """
    if not eintrag_url:
        return True, "noch nie angefragt"
    fingerprint = eintrag_url.get("lastmod", "")
    if eintrag_url.get("lastmod_angefragt", "") != fingerprint:
        return True, "Inhalt geändert seit der letzten Anfrage"
    if eintrag_url.get("fehler_zaehler", 0) >= 3:
        return False, "drei Fehlversuche in Folge – menschliche Klärung nötig"
    zuletzt = eintrag_url.get("zuletzt")
    if not zuletzt:
        return True, "Zustand ohne Zeitstempel"
    try:
        datum = dt.date.fromisoformat(zuletzt[:10])
    except ValueError:
        return True, "Zeitstempel unlesbar"
    alter = (heute - datum).days
    abdeckung = (eintrag_url.get("coverageState") or "").lower()
    frist = WIEDERVORLAGE_TAGE_OFFEN if abdeckung in NICHT_INDEXIERT else WIEDERVORLAGE_TAGE_INDEXIERT
    if alter < frist:
        return False, f"vor {alter} Tag(en) angefragt (Frist {frist})"
    return True, f"vor {alter} Tag(en) angefragt, Frist {frist} erreicht"


def plane(seiten, state: dict, heute: dt.date, limit: int | None = None,
          kontingent_heute: int = 0) -> tuple[list, list]:
    """(Queue, Übersprungen) – Queue respektiert Tageskontingent und `limit`.

    `kontingent_heute` ist die Zahl der bereits heute verbrauchten Anfragen
    (aus dem Zustand gezählt). Wer sie ignoriert, bekommt ab Anfrage 201 ein
    429 von Google – und zwar genau dann, wenn die wirklich wichtige neue
    Seite dran wäre.
    """
    verfuegbar = max(0, TAGESKONTINGENT - SICHERHEITSABSTAND - kontingent_heute)
    queue: list = []
    uebersprungen: list = []
    for s in reihenfolge(seiten, heute=heute.isoformat()):
        faellig, grund = ist_fällig(eintrag(state, s.url), heute)
        if not faellig:
            uebersprungen.append((s.url, grund))
            continue
        if len(queue) >= verfuegbar:
            uebersprungen.append((s.url, "Tageskontingent ausgeschöpft"))
            continue
        if limit is not None and len(queue) >= limit:
            uebersprungen.append((s.url, f"--limit {limit} erreicht"))
            continue
        queue.append(s)
    return queue, uebersprungen


def kontingent_verbraucht(state: dict, heute: dt.date) -> int:
    """Wie viele Anfragen dieses Kalendertages stehen bereits im Zustand?"""
    tag = heute.isoformat()
    return sum(1 for e in state.get("urls", {}).values()
               if str(e.get("zuletzt", "")).startswith(tag))


# ---------------------------------------------------------------- API
def hole_token_schreibend(http, sa: dict, jetzt: int, sign=rs256_signatur) -> str:
    """OAuth-Token mit SCHREIB-Scope (URL Inspection ist ein Schreibvorgang).

    Bewusst eine eigene Funktion statt eines Parameters an `gsc_import.hole_token`:
    Der Lese-Import soll niemals versehentlich mit Schreibrechten laufen. Die
    Signatur-Kette selbst bleibt dieselbe (ein Ort für RS256).
    """
    import urllib.parse

    from gsc_import import _b64url  # lokale Importe: Scope-Trennung
    kopf = {"alg": "RS256", "typ": "JWT"}
    nutzlast = {
        "iss": sa["client_email"],
        "scope": SCOPE,
        "aud": TOKEN_URL,
        "iat": jetzt,
        "exp": jetzt + 3600,
    }
    teile = (_b64url(json.dumps(kopf, separators=(",", ":")).encode()) + "."
             + _b64url(json.dumps(nutzlast, separators=(",", ":")).encode()))
    assertion = teile + "." + _b64url(sign(teile.encode("ascii"), sa["private_key"]))
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }).encode()
    status, antwort = http("POST", TOKEN_URL,
                           {"Content-Type": "application/x-www-form-urlencoded"}, body)
    if status != 200 or "access_token" not in antwort:
        grund = antwort.get("error_description") or antwort.get("error") or f"HTTP {status}"
        raise GscFehler(f"Token-Abruf (Schreib-Scope) fehlgeschlagen: {grund}")
    return antwort["access_token"]


def frage_indexierung_an(http, token: str, url: str, site: str,
                         sprache: str = "de") -> tuple[int, dict]:
    """Eine URL zur Indexierungsprüfung anmelden.

    Antwortform (Google, `UrlInspectionResponse.indexStatusResult`):
      verdict, coverageState, indexingState, lastCrawlTime, pageFetchState,
      robotsTxtState, crawledAs, referringUrls.
    Wir lesen defensiv: fehlt ein Feld, bleibt es leer – ein API-Feldwechsel
    darf den Lauf nicht abbrechen, wohl aber sichtbar werden (siehe
    `unbekannte_felder`).
    """
    body = json.dumps({
        "inspectionUrl": url,
        "siteUrl": site,
        "languageCode": sprache,
    }).encode()
    req_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    return http("POST", INSPECT_TMPL, req_headers, body)


def deute_antwort(status: int, antwort: dict) -> dict:
    """HTTP-Status + JSON → ein Zustandseintrag (ohne Schlüsselmaterial)."""
    ergebnis = {
        "http_status": status,
        "abdeckung": "",
        "urteil": "",
        "indexierung": "",
        "zuletzt_gecrawlt": "",
        "seitenabruf": "",
        "robots_txt": "",
        "gecrawlt_als": "",
        "fehler": "",
        "unbekannte_felder": [],
    }
    if status == 200:
        res = antwort.get("inspectionResult") or {}
        isr = res.get("indexStatusResult") or {}
        ergebnis["abdeckung"] = isr.get("coverageState") or ""
        ergebnis["urteil"] = isr.get("verdict") or ""
        ergebnis["indexierung"] = isr.get("indexingState") or ""
        ergebnis["zuletzt_gecrawlt"] = isr.get("lastCrawlTime") or ""
        ergebnis["seitenabruf"] = isr.get("pageFetchState") or ""
        ergebnis["robots_txt"] = isr.get("robotsTxtState") or ""
        ergebnis["gecrawlt_als"] = isr.get("crawledAs") or ""
        # API-Drift sichtbar machen, statt sie zu verschlucken:
        bekannt = set(ANTWORT_FELDER) | {"propertyUrl"}
        ergebnis["unbekannte_felder"] = sorted(k for k in isr if k not in bekannt)
    elif status in (401, 403):
        ergebnis["fehler"] = (
            f"HTTP {status}: keine Berechtigung. Das Dienstkonto braucht in der "
            "Search Console die Stufe „Vollständig“ (Owner); „Eingeschränkt“ "
            "reicht nur für den Lese-Import. Runbook: "
            "docs/ANLEITUNG-GSC-API-ZUGRIFF.md, Schritt 5a.")
    elif status == 429:
        ergebnis["fehler"] = (
            "HTTP 429: Tageskontingent der URL Inspection API ist erschöpft "
            f"({TAGESKONTINGENT} Anfragen je Property). Morgen läuft es weiter; "
            "die Sitemap bleibt der reguläre Entdeckungsweg.")
    elif status == 400:
        nachricht = ((antwort.get("error") or {}).get("message") or "")
        ergebnis["fehler"] = f"HTTP 400: {nachricht[:200]}"
    else:
        nachricht = ((antwort.get("error") or {}).get("message") or f"HTTP {status}")
        ergebnis["fehler"] = f"{nachricht[:200]}"
    return ergebnis


def pruefe_berechtigung(http, token: str, site: str) -> tuple[bool, str]:
    """Steht die Property dem Dienstkonto offen – und mit welchem Recht?

    Ohne diesen Vorcheck endet jeder Lauf mit 20× HTTP 403 und niemand weiß,
    ob die Property fehlt oder nur die Berechtigungsstufe. Ein Aufruf, eine
    klare Aussage.
    """
    try:
        eintraege = hole_sites(http, token)
    except GscFehler as exc:
        return False, f"Property-Liste nicht lesbar: {exc}"
    if not eintraege:
        return False, ("Das Dienstkonto sieht keine einzige Property. In der Search "
                       "Console unter „Einstellungen → Nutzer und Berechtigungen“ die "
                       "Dienstkonto-E-Mail eintragen.")
    for e in eintraege:
        if e.get("siteUrl") == site:
            stufe = e.get("permissionLevel") or ""
            if stufe == "siteOwner":
                return True, f"Property {site} sichtbar, Berechtigung „Vollständig“ (Owner)."
            return False, (
                f"Property {site} ist sichtbar, aber die Berechtigungsstufe ist "
                f"„{stufe or 'unbekannt'}“. Für eine Indexierungs-Anfrage braucht das "
                "Dienstkonto „Vollständig“ (Owner); „Eingeschränkt“ reicht nur für den "
                "Lese-Import. Runbook: docs/ANLEITUNG-GSC-API-ZUGRIFF.md, Schritt 5a.")
    sichtbar = ", ".join(sorted(e.get("siteUrl", "?") for e in eintraege))
    return False, (f"GSC_SITE_URL '{site}' ist nicht unter den sichtbaren Properties "
                   f"({sichtbar}). Exakt so eintragen, wie die Search Console sie zeigt.")


# ---------------------------------------------------------------- Lauf
def lauf(http=default_http, env: dict | None = None, jetzt: dt.datetime | None = None,
         sign=rs256_signatur, state_pfad: Path = STATE_DATEI, limit: int | None = None,
         tage: int | None = None, dry_run: bool = False, nur_plan: bool = False,
         live: bool = False, sitemap_url: str | None = None, urls: list | None = None,
         nur_pruefen: bool = False, warten: bool = True, sitemap_http=None) -> dict:
    """Ein vollständiger Lauf. Alle Zugänge sind injizierbar → offline testbar.

    Es gibt ZWEI Transporte, weil sie verschiedene Signaturen haben:

      · ``http``         – die Search-Console-API: ``(method, url, headers, body)``
      · ``sitemap_http`` – das Holen der Sitemap:   ``(url) -> (status, text)``

    Ohne ``sitemap_http`` geht die Sitemap über den echten Transport
    (``indexierbare_seiten._hole_http``). Wer einen Lauf offline prüft, muss
    BEIDE injizieren: Nur ``http`` zu ersetzen lässt die Sitemap trotzdem ins
    Netz greifen. Genau das tat die erste Fassung dieses Selbsttests, und die
    KI-Probe (#138) hat es gemeldet – der Docstring „alle Zugänge
    injizierbar" war damals ein Wunsch, kein Vertrag.
    """
    env = os.environ if env is None else env
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    heute = jetzt.date()
    site = env.get("GSC_SITE_URL", "").strip()
    sa_text = env.get("GSC_SERVICE_ACCOUNT_JSON", "").strip()
    sa_datei = env.get("GSC_SERVICE_ACCOUNT_FILE", "").strip()

    bericht = {
        "stand": jetzt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "quelle": "google-search-console-url-inspection-api (Dienstkonto)",
        "site": site or None,
        "status": "ok",
        "grund": "",
        "kontingent_tag": TAGESKONTINGENT,
        "kontingent_verbraucht": 0,
        "seiten_indexierbar": 0,
        "angefragt": [],
        "abgelehnt": [],
        "uebersprungen": [],
        "indexiert": 0,
        "nicht_indexiert": 0,
    }

    # ---- 1) Queue: aus der Sitemap, nie aus einer Namensliste ----
    try:
        if urls:
            from indexierbare_seiten import Seite
            seiten = [Seite(url=u, pfad="", lastmod="", priority=1.0) for u in urls]
            befunde: list[str] = []
        elif live or sitemap_url:
            seiten, befunde = hole_seiten(sitemap_url=sitemap_url or live_sitemap_url(),
                                          http=sitemap_http)
        else:
            seiten, befunde = hole_seiten(http=sitemap_http)
    except SitemapFehler as exc:
        bericht["status"] = "werkzeugfehler"
        bericht["grund"] = str(exc)
        return bericht
    bericht["seiten_indexierbar"] = len(seiten)
    bericht["sitemap_befunde"] = befunde

    if tage:
        schwelle = (heute - dt.timedelta(days=tage)).isoformat()
        seiten = nur_frische(seiten, schwelle)
        bericht["frische_filter_tage"] = tage
        bericht["seiten_nach_filter"] = len(seiten)

    # ---- 2) Zustand und Kontingent ----
    try:
        state = lade_state(state_pfad)
    except IndexierungsFehler as exc:
        bericht["status"] = "werkzeugfehler"
        bericht["grund"] = str(exc)
        return bericht
    verbraucht = kontingent_verbraucht(state, heute)
    bericht["kontingent_verbraucht"] = verbraucht

    queue, uebersprungen = plane(seiten, state, heute, limit=limit,
                                 kontingent_heute=verbraucht)
    bericht["uebersprungen"] = [{"url": u, "grund": g} for u, g in uebersprungen]
    bericht["queue"] = [s.url for s in queue]

    if nur_plan:
        bericht["status"] = "plan"
        bericht["grund"] = (f"{len(queue)} URL(s) wären fällig, {len(uebersprungen)} "
                            "übersprungen.")
        return bericht

    # ---- 3) Zugang ----
    if not (site and (sa_text or sa_datei)):
        bericht["status"] = "nicht_konfiguriert"
        bericht["grund"] = ("GSC_SITE_URL und GSC_SERVICE_ACCOUNT_JSON (oder _FILE) "
                            "fehlen – es wurde nichts angefragt. Einrichtung: "
                            "docs/ANLEITUNG-GSC-API-ZUGRIFF.md")
        return bericht
    if not queue:
        bericht["status"] = "nichts_zu_tun"
        bericht["grund"] = ("Keine Seite ist fällig (alles frisch angefragt oder "
                            "Kontingent erschöpft).")
        return bericht

    try:
        sa = json.loads(sa_text) if sa_text else json.loads(Path(sa_datei).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        bericht["status"] = "werkzeugfehler"
        bericht["grund"] = f"Dienstkonto-Schlüssel unlesbar: {exc.__class__.__name__}"
        return bericht

    try:
        token = hole_token_schreibend(http, sa, int(jetzt.timestamp()), sign)
    except GscFehler as exc:
        bericht["status"] = "fehler"
        bericht["grund"] = str(exc)
        return bericht

    ok, aussage = pruefe_berechtigung(http, token, site)
    bericht["berechtigung"] = aussage
    if not ok:
        bericht["status"] = "keine_berechtigung"
        bericht["grund"] = aussage
        return bericht

    if dry_run:
        bericht["status"] = "dry_run"
        bericht["grund"] = (f"{len(queue)} URL(s) wären angefragt worden; Zugang und "
                            "Berechtigung sind geprüft.")
        return bericht

    # ---- 4) Anfragen ----
    for i, s in enumerate(queue):
        if warten and i > 0:
            # 600 Anfragen/Minute erlaubt Google; 0,2 s Abstand ist 20× darunter
            # und kostet bei 200 URLs 40 Sekunden – billig für einen ruhigen Lauf.
            time.sleep(0.2)
        status, antwort = frage_indexierung_an(http, token, s.url, site)
        gedeutet = deute_antwort(status, antwort)
        ziel = eintrag(state, s.url)
        ziel.update({
            "zuletzt": jetzt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "lastmod_angefragt": s.lastmod,
            "lastmod": s.lastmod,
            "http_status": gedeutet["http_status"],
            "coverageState": gedeutet["abdeckung"],
            "verdict": gedeutet["urteil"],
            "indexingState": gedeutet["indexierung"],
            "lastCrawlTime": gedeutet["zuletzt_gecrawlt"],
            "pageFetchState": gedeutet["seitenabruf"],
            "robotsTxtState": gedeutet["robots_txt"],
            "crawledAs": gedeutet["gecrawlt_als"],
        })
        if gedeutet["unbekannte_felder"]:
            ziel["unbekannte_felder"] = gedeutet["unbekannte_felder"]
        ziel["fehler"] = gedeutet["fehler"]
        ziel["nur_pruefen"] = bool(nur_pruefen)

        if status == 200:
            ziel["fehler_zaehler"] = 0
            bericht["angefragt"].append({"url": s.url, "abdeckung": gedeutet["abdeckung"]})
            abdeckung = gedeutet["abdeckung"].lower()
            if abdeckung in NICHT_INDEXIERT:
                bericht["nicht_indexiert"] += 1
            else:
                bericht["indexiert"] += 1
        else:
            ziel["fehler_zaehler"] = int(ziel.get("fehler_zaehler", 0)) + 1
            bericht["abgelehnt"].append({"url": s.url, "status": status,
                                         "fehler": gedeutet["fehler"]})
            if status == 429:
                # Kontingent ist leer: Der Rest der Queue hat heute keinen Zweck.
                # Abbruch statt 150 weiterer 429er – und zwar mit klarem Status.
                bericht["status"] = "kontingent_erschoepft"
                bericht["grund"] = gedeutet["fehler"]
                break
        schreibe_state(state, state_pfad)

    if bericht["abgelehnt"] and bericht["status"] == "ok":
        bericht["status"] = "abgelehnt"
        bericht["grund"] = (f"{len(bericht['abgelehnt'])} URL(s) von Google abgelehnt; "
                            f"erste Meldung: {bericht['abgelehnt'][0]['fehler']}")
    return bericht


# ---------------------------------------------------------------- Bericht
def drucke(bericht: dict) -> None:
    print("=" * 68)
    print(" GSC-INDEXIERUNG – Indexierungs-Anfragen über die URL Inspection API")
    print("=" * 68)
    print(f"  Property ................... {bericht.get('site') or '–'}")
    print(f"  Status ..................... {bericht['status']}")
    if bericht.get("grund"):
        print(f"  Grund ...................... {bericht['grund']}")
    if bericht.get("berechtigung"):
        print(f"  Berechtigung ............... {bericht['berechtigung']}")
    print(f"  Indexierbare Seiten ........ {bericht.get('seiten_indexierbar', 0)}")
    print(f"  Tageskontingent ............ {bericht.get('kontingent_verbraucht', 0)}"
          f" von {TAGESKONTINGENT} bereits verbraucht")
    for b in bericht.get("sitemap_befunde") or []:
        print(f"  ⚠️  Sitemap: {b}")
    queue = bericht.get("queue") or []
    if queue:
        print(f"\n  Zur Anfrage vorgesehen ({len(queue)}):")
        for u in queue[:20]:
            print(f"    • {u}")
        if len(queue) > 20:
            print(f"    … und {len(queue) - 20} weitere")
    if bericht.get("angefragt"):
        print(f"\n  Angefragt ({len(bericht['angefragt'])}):")
        for a in bericht["angefragt"][:20]:
            print(f"    ✓ {a['url']}  → {a['abdeckung'] or 'ohne Angabe'}")
        if len(bericht["angefragt"]) > 20:
            print(f"    … und {len(bericht['angefragt']) - 20} weitere")
        print(f"\n  davon von Google als indexiert gemeldet ... {bericht.get('indexiert', 0)}")
        print(f"  davon NICHT indexiert (Handlungsbedarf) .... {bericht.get('nicht_indexiert', 0)}")
    if bericht.get("abgelehnt"):
        print(f"\n  Abgelehnt ({len(bericht['abgelehnt'])}):")
        for a in bericht["abgelehnt"][:10]:
            print(f"    ✗ {a['url']}  → {a['fehler']}")
    if bericht.get("uebersprungen"):
        print(f"\n  Übersprungen ({len(bericht['uebersprungen'])}):")
        for s in bericht["uebersprungen"][:10]:
            print(f"    – {s['url']}  ({s['grund']})")
        if len(bericht["uebersprungen"]) > 10:
            print(f"    … und {len(bericht['uebersprungen']) - 10} weitere")


# ---------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    """Offline-Selbsttest mit Fake-API: kein Netz, keine Uhr, keine Schreiberei."""
    fehler: list[str] = []

    def pruefe(name: str, bedingung: bool) -> None:
        if not bedingung:
            fehler.append(name)

    import tempfile
    from indexierbare_seiten import Seite

    sa = {"client_email": "gsc@x.iam.gserviceaccount.com", "private_key": "PEM"}
    env = {"GSC_SITE_URL": "sc-domain:franksfinanzcheck.de",
           "GSC_SERVICE_ACCOUNT_JSON": json.dumps(sa)}
    fest = dt.datetime(2026, 10, 12, 6, 0, tzinfo=dt.timezone.utc)

    seiten = [
        Seite(url="https://franksfinanzcheck.de/", pfad="/", lastmod="2026-10-12", priority=1.0),
        Seite(url="https://franksfinanzcheck.de/pillar/strom-sparen/", pfad="/pillar/strom-sparen/",
              lastmod="2026-10-02", priority=0.9),
        Seite(url="https://franksfinanzcheck.de/posts/neu/", pfad="/posts/neu/",
              lastmod="2026-10-11", priority=0.8),
    ]
    sitemap = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               + "".join(f'<url><loc>{s.url}</loc><lastmod>{s.lastmod}</lastmod>'
                         f'<priority>{s.priority}</priority></url>' for s in seiten)
               + "</urlset>")

    anfragen: list[str] = []

    def fake_ok(method, url, headers, body):
        if url == TOKEN_URL:
            return 200, {"access_token": "t-schreibend"}
        if url.endswith("/sites"):
            return 200, {"siteEntry": [{"siteUrl": env["GSC_SITE_URL"],
                                        "permissionLevel": "siteOwner"}]}
        if "urlInspection" in url:
            b = json.loads(body)
            anfragen.append(b["inspectionUrl"])
            pruefe("siteUrl wird mitgesendet", b.get("siteUrl") == env["GSC_SITE_URL"])
            return 200, {"inspectionResult": {"indexStatusResult": {
                "verdict": "PASS", "coverageState": "Submitted and indexed",
                "indexingState": "INDEXING_ALLOWED", "lastCrawlTime": "2026-10-11T10:00:00Z",
                "pageFetchState": "Successful", "robotsTxtState": "ALLOWED",
                "crawledAs": "Googlebot", "neuesFeld": "x"}}}
        return 404, {}

    # Sitemap-Transport des Selbsttests: (url) -> (status, text), mit Zähler.
    # Der Zähler ist die Gegenprobe – er beweist, dass die Sitemap über die
    # Attrappe kam und nicht über `indexierbare_seiten._hole_http` ins Netz
    # (KI-Probe #138: kein Selbsttest darf am Netz hängen).
    sitemap_treffer: list[str] = []

    def fake_sitemap(url: str):
        sitemap_treffer.append(url)
        return 200, sitemap

    def fake_sitemap_404(url: str):
        sitemap_treffer.append(url)
        return 404, ""

    with tempfile.TemporaryDirectory() as tmp:
        state_pfad = Path(tmp) / "state.json"

        # 1) Unerreichbare Sitemap: Werkzeugfehler, VOR der Zugangsfrage.
        #    Fail-closed – wer nichts über den Bestand weiß, fragt nichts an.
        b1 = lauf(http=fake_ok, env=env, jetzt=fest, sign=lambda m, k: b"x",
                  state_pfad=state_pfad, sitemap_url="https://x/sitemap.xml",
                  sitemap_http=fake_sitemap_404)
        pruefe("unerreichbare Sitemap ist Werkzeugfehler", b1["status"] == "werkzeugfehler")
        pruefe("Sitemap kam über den injizierten Transport",
               sitemap_treffer == ["https://x/sitemap.xml"])
        pruefe("bei Werkzeugfehler wird nichts angefragt", not anfragen)

        # 2) Intakte Sitemap, aber kein Zugang: nicht_konfiguriert.
        #    Diese Probe war vorher verstellt – der Netzversuch der Sitemap
        #    lieferte den Werkzeugfehler zuerst, also wurde nie geprüft, was
        #    hier stehen sollte. Erst die injizierbare Sitemap macht sie scharf.
        sitemap_treffer.clear()
        b2 = lauf(http=fake_ok, env={}, jetzt=fest, sign=lambda m, k: b"x",
                  state_pfad=state_pfad, sitemap_url="https://x/sitemap.xml",
                  sitemap_http=fake_sitemap)
        pruefe("fehlender Zugang meldet nicht_konfiguriert",
               b2["status"] == "nicht_konfiguriert")
        pruefe("Bestand wurde trotzdem ermittelt", b2["seiten_indexierbar"] == 3)
        pruefe("ohne Zugang wird keine einzige Seite angefragt", not anfragen)

        # 3) Voller Lauf gegen die injizierte Sitemap – der Regelweg, keine
        #    --urls-Notlösung. Die Sitemap trägt die Gewichtung (1.0/0.9/0.8),
        #    also muss die Startseite zuerst dran sein.
        sitemap_treffer.clear()
        anfragen.clear()
        b3 = lauf(http=fake_ok, env=env, jetzt=fest, sign=lambda m, k: b"x",
                  state_pfad=state_pfad, sitemap_url="https://x/sitemap.xml",
                  sitemap_http=fake_sitemap, warten=False)
        pruefe("drei URLs angefragt", len(b3["angefragt"]) == 3)
        pruefe("Reihenfolge nach Wichtigkeit", anfragen[:1] == ["https://franksfinanzcheck.de/"])
        pruefe("Status ok", b3["status"] == "ok")
        pruefe("indexiert gezählt", b3["indexiert"] == 3 and b3["nicht_indexiert"] == 0)
        pruefe("Berechtigung geprüft", "Vollständig" in b3.get("berechtigung", ""))
        pruefe("Sitemap-Transport genau einmal benutzt",
               sitemap_treffer == ["https://x/sitemap.xml"])

        state = lade_state(state_pfad)
        eintrag_home = state["urls"]["https://franksfinanzcheck.de/"]
        pruefe("Zustand geschrieben", eintrag_home["coverageState"] == "Submitted and indexed")
        pruefe("keine Tokens im Zustand", "t-schreibend" not in json.dumps(state))
        pruefe("API-Drift sichtbar", eintrag_home.get("unbekannte_felder") == ["neuesFeld"])
        pruefe("kein Schlüsselmaterial im Zustand", "PEM" not in json.dumps(state))

        # 3) Zweiter Lauf am selben Tag: alles frisch angefragt → nichts zu tun
        anfragen.clear()
        b4 = lauf(http=fake_ok, env=env, jetzt=fest, sign=lambda m, k: b"x",
                  state_pfad=state_pfad, urls=[s.url for s in seiten], warten=False)
        pruefe("kein Doppel-Einreichen", not anfragen)
        pruefe("Status nichts_zu_tun", b4["status"] == "nichts_zu_tun")

        # 4) Wiedervorlage: 8 Tage später ist eine indexierte Seite noch gesperrt
        spaeter = fest + dt.timedelta(days=8)
        anfragen.clear()
        b5 = lauf(http=fake_ok, env=env, jetzt=spaeter, sign=lambda m, k: b"x",
                  state_pfad=state_pfad, urls=[s.url for s in seiten], warten=False)
        pruefe("28-Tage-Frist hält", not anfragen)

        # 5) Inhalt geändert (neues lastmod) → sofort wieder fällig
        anfragen.clear()
        state["urls"]["https://franksfinanzcheck.de/posts/neu/"]["lastmod_angefragt"] = "2026-01-01"
        schreibe_state(state, state_pfad)
        b6 = lauf(http=fake_ok, env=env, jetzt=spaeter, sign=lambda m, k: b"x",
                  state_pfad=state_pfad, urls=[s.url for s in seiten], warten=False)
        pruefe("Änderung bricht die Frist", anfragen == ["https://franksfinanzcheck.de/posts/neu/"])

        # 6) Kontingent: 196 verbrauchte Anfragen lassen nur noch wenige durch
        state = lade_state(state_pfad)
        for i in range(TAGESKONTINGENT - 4):
            state["urls"][f"https://franksfinanzcheck.de/p{i}/"] = {
                "zuletzt": spaeter.strftime("%Y-%m-%dT%H:%M:%SZ")}
        schreibe_state(state, state_pfad)
        b7 = lauf(http=fake_ok, env=env, jetzt=spaeter, sign=lambda m, k: b"x",
                  state_pfad=state_pfad, nur_plan=True,
                  urls=[f"https://franksfinanzcheck.de/q{i}/" for i in range(50)])
        pruefe("Kontingent begrenzt die Queue", len(b7["queue"]) <= TAGESKONTINGENT - SICHERHEITSABSTAND)
        pruefe("Kontingent-Grund dokumentiert",
               any(s["grund"] == "Tageskontingent ausgeschöpft" for s in b7["uebersprungen"]))

        # 7) 403 (nur „Eingeschränkt"): klare Ansage, kein einziges Einreichen
        def fake_403(method, url, headers, body):
            if url == TOKEN_URL:
                return 200, {"access_token": "t"}
            if url.endswith("/sites"):
                return 200, {"siteEntry": [{"siteUrl": env["GSC_SITE_URL"],
                                            "permissionLevel": "siteRestrictedUser"}]}
            return 403, {"error": {"message": "permission denied"}}

        b8 = lauf(http=fake_403, env=env, jetzt=fest, sign=lambda m, k: b"x",
                  state_pfad=Path(tmp) / "state2.json",
                  urls=[s.url for s in seiten], warten=False)
        pruefe("403 wird zu keine_berechtigung", b8["status"] == "keine_berechtigung")
        pruefe("403 erklärt die Berechtigungsstufe", "Vollständig" in b8["grund"])

        # 8) 429: Lauf bricht ab, statt das Kontingent weiter zu traktieren
        zaehler = {"n": 0}

        def fake_429(method, url, headers, body):
            if url == TOKEN_URL:
                return 200, {"access_token": "t"}
            if url.endswith("/sites"):
                return 200, {"siteEntry": [{"siteUrl": env["GSC_SITE_URL"],
                                            "permissionLevel": "siteOwner"}]}
            zaehler["n"] += 1
            if zaehler["n"] == 1:
                return 429, {"error": {"message": "quota exceeded"}}
            return 200, {"inspectionResult": {"indexStatusResult": {"coverageState": "x"}}}

        b9 = lauf(http=fake_429, env=env, jetzt=fest, sign=lambda m, k: b"x",
                  state_pfad=Path(tmp) / "state3.json",
                  urls=[s.url for s in seiten], warten=False)
        pruefe("429 beendet den Lauf", b9["status"] == "kontingent_erschoepft")
        pruefe("nach 429 wird nicht weitergefragt", zaehler["n"] == 1)

        # 9) Nicht indexiert: Abdeckungszustand landet im Bericht
        def fake_offen(method, url, headers, body):
            if url == TOKEN_URL:
                return 200, {"access_token": "t"}
            if url.endswith("/sites"):
                return 200, {"siteEntry": [{"siteUrl": env["GSC_SITE_URL"],
                                            "permissionLevel": "siteOwner"}]}
            return 200, {"inspectionResult": {"indexStatusResult": {
                "coverageState": "Crawled - currently not indexed"}}}

        b10 = lauf(http=fake_offen, env=env, jetzt=fest, sign=lambda m, k: b"x",
                   state_pfad=Path(tmp) / "state4.json",
                   urls=[s.url for s in seiten], warten=False)
        pruefe("nicht indexiert gezählt", b10["nicht_indexiert"] == 3 and b10["indexiert"] == 0)

        # 10) dry-run: geprüft, aber nichts eingereicht
        anfragen.clear()
        b11 = lauf(http=fake_ok, env=env, jetzt=fest, sign=lambda m, k: b"x",
                   state_pfad=Path(tmp) / "state5.json", dry_run=True,
                   urls=[s.url for s in seiten], warten=False)
        pruefe("dry-run reicht nichts ein", not anfragen and b11["status"] == "dry_run")

        # 11) --plan ohne Zugang: Planung funktioniert auch ohne Konto
        b12 = lauf(http=fake_ok, env={}, jetzt=fest, sign=lambda m, k: b"x",
                   state_pfad=Path(tmp) / "state6.json", nur_plan=True,
                   urls=[s.url for s in seiten])
        pruefe("Plan ohne Zugang", b12["status"] == "plan" and len(b12["queue"]) == 3)

        # 12) Kaputter Zustand: fail-closed statt „vergessen"
        kaputt = Path(tmp) / "kaputt.json"
        kaputt.write_text("{ kaputt", encoding="utf-8")
        try:
            lade_state(kaputt)
            fehler.append("kaputter Zustand muss IndexierungsFehler werfen")
        except IndexierungsFehler:
            pass

        # 13) Fälligkeitsregel einzeln (ohne API)
        f, grund = ist_fällig({}, dt.date(2026, 10, 12))
        pruefe("leerer Eintrag ist fällig", f)
        f2, _ = ist_fällig({"zuletzt": "2026-10-12T06:00:00Z", "lastmod_angefragt": "2026-10-12",
                            "lastmod": "2026-10-12", "coverageState": "Submitted and indexed"},
                           dt.date(2026, 10, 12))
        pruefe("frisch indexiert ist nicht fällig", not f2)
        f3, _ = ist_fällig({"zuletzt": "2026-10-12T06:00:00Z", "lastmod_angefragt": "2026-10-12",
                            "lastmod": "2026-10-12", "coverageState": "Crawled - currently not indexed"},
                           dt.date(2026, 10, 20))
        pruefe("nicht indexiert kommt nach 7 Tagen wieder", f3)
        f4, _ = ist_fällig({"zuletzt": "2026-10-12T06:00:00Z", "lastmod_angefragt": "2026-10-12",
                            "lastmod": "2026-10-12", "fehler_zaehler": 3},
                           dt.date(2027, 1, 1))
        pruefe("drei Fehlversuche stoppen die Automatik", not f4)

    if fehler:
        print("❌ GSC-INDEXIERUNGS-SELBSTTEST fehlgeschlagen:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print("✅ gsc_indexierung: Selbsttest bestanden "
          "(13 Fallgruppen: Token-Scope, Berechtigungs-Vorcheck, Queue, Kontingent, "
          "Wiedervorlage, 403/429, Zustands-Hygiene, Fail-closed).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Indexierungs-Anfragen an die Google Search Console (URL Inspection API).")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="Zugang und Queue prüfen, nichts einreichen")
    ap.add_argument("--plan", action="store_true",
                    help="nur zeigen, was fällig wäre (ohne API)")
    ap.add_argument("--pruefen", action="store_true",
                    help="nur den Indexierungsstatus abfragen")
    ap.add_argument("--live", action="store_true",
                    help="Queue aus der ausgelieferten Sitemap statt aus public/")
    ap.add_argument("--sitemap", default=None, help="eigene Sitemap-URL")
    ap.add_argument("--limit", type=int, default=None, help="höchstens so viele URLs")
    ap.add_argument("--tage", type=int, default=None,
                    help="nur Seiten, deren lastmod höchstens so viele Tage zurückliegt")
    ap.add_argument("--url", action="append", default=None,
                    help="einzelne URL(s) anfragen (mehrfach möglich)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return _selftest()

    bericht = lauf(limit=a.limit, tage=a.tage, dry_run=a.dry_run, nur_plan=a.plan,
                   live=a.live, sitemap_url=a.sitemap, urls=a.url, nur_pruefen=a.pruefen)

    if a.json:
        print(json.dumps(bericht, ensure_ascii=False, indent=2))
    else:
        drucke(bericht)

    if bericht["status"] == "werkzeugfehler":
        return 2
    if bericht["status"] == "abgelehnt":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
