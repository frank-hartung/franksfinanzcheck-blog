#!/usr/bin/env python3
"""newsletter_zustellbarkeit.py – die Zustellbarkeits-Wache: Cloudflare-DNS + Resend + Worker.

WARUM (Vorfälle 23.–24.09.2026, Newsletter-Daily Läufe #14–#26):
Der Versand war im Repo dreifach verriegelt, die Kette *vor* der
Verriegelung aber ungeprüft. Zwei Vorfälle an einem Tag zeigten, was
fehlt: ein 403 von der Cloudflare-KANTE (Error 1010, Signaturfilter)
wurde wochenlang für ein „Absender-Problem beim Anbieter“ gehalten, und
eine Checkliste empfahl eine SPF-Erweiterung, die an der Zustellung
nichts geändert hätte. Die Unterscheidung – Kante vs. Anbieter, DKIM vs.
SPF, Messlücke vs. Befund – ist der Grund für diese Wache: sie misst
beide Seiten und sagt zu jedem Befund den exakten nächsten Schritt im
jeweiligen Interface.

SEIT 24.09.2026 (Eigenbetrieb):
Die Brevo-Schicht ist raus. Geprüft wird jetzt, was in dieser
Architektur Zustellung entscheidet:

  CLOUDFLARE (DNS-Zone, per DNS-über-HTTPS gemessen, nie geraten):
    C1  SPF: genau ein Eintrag (zwei = permanenter Fehler), mit Mechanik.
        Die Apex-SPF bleibt die eigene der Zone (hier: Cloudflare-Routing)
        – Resend verlangt seit seinem SES-Modell KEIN Include an der Spitze
    C2  Resend-Send-Subdomain: TXT-SPF auf `send.` (z. B.
        `v=spf1 include:amazonses.com ~all`) + MX für Bounces
        (`feedback-smtp.<region>.amazonses.com`) – exakte Werte aus
        Resend → Domains; gemessen wird Existenz + Form
    C3  Resend-DKIM: TXT `resend._domainkey` (ein Datensatz mit `p=`-Key)
    C4  DMARC: vorhanden? `rua`-Berichtsweg? Policy nicht strenger als
        die Echtheitsnachweise (p=reject OHNE DKIM = Fund: alles ohne
        Alignment wird hart abgewiesen)?
    C5  MX/Routing: die Reply-to-Domain muss eingehende Mail annehmen
    C6  Absender-Postfach: MX auf der Absender-Domain (empfohlen,
        kein Zwang – sonst würde Reply-to ins Leere gehen)
  WORKER (der Anmeldeweg UND die Adressliste – er versendet nichts):
    C7  Capture-Endpunkt lebt: die Domain löst sich auf, der Worker
        antwortet (sonst gehen keine Adressen ein – und der Versand
        läuft gegen eine leere Liste)
    C8  Taktgeber (seit 25.09.2026): der Worker startet den Digest per
        Cron Trigger (Di/Fr 04:30 UTC), weil GitHubs Scheduler an
        diesem Repo Stunden zu spät oder gar nicht feuert. Gemessen wird
        aus /healthz → `takt.letzte.digest`: fehlt der Takt ganz (alte
        Worker-Version), ist der letzte Dispatch gescheitert (HTTP 403 =
        PAT ohne „Actions: write“) oder wurde der letzte fällige
        Versandtag verpasst → Fund. „Nie gefeuert“ vor dem ersten
        fälligen Termin ist ein Hinweis, kein Fund.
  RESEND (API, nur wenn ein Key da ist – sonst „nicht gemessen“):
    B0  Netzweg: erreicht der Client api.resend.com? (401 ohne Key =
        Kante durchlässig; 403 mit Signaturfilter-Marke = Blockage;
        das sind verschiedene Befunde – genau die Verwechslung von
        Lauf #21)
    B1  Sende-Domain verifiziert (sonst nimmt Resend keine Mail an)
    B2  Abonnentenstand aus dem Worker-Export (die „Liste“; 0 = leerer
        Zustand, nicht gemessen ≠ gefunden)
    B3  Plan-Grenze: Free = 100 Mails/TAG – ein Tag mit mehr Abonnenten
        schafft nicht alle (Upgrade-Pfad, nicht Alarm)
  REPO-STATUS (data/newsletter_state.json, ohne Netz):
    S1  Versand-Halt nach unklarem Sendeausgang (blockiert den
        Listen-Versand)
    S2  Artikel, die auf den Versand warten
    S3  Versandnachweis (`letzte_ausgabe` mit Datum/Betreff/Transport)

Exit: 0 = keine Funde · 1 = Befund · 2 = Fehler (Prüfung ausgefallen)
Nur Standardbibliothek.

Nutzung:
    python3 scripts/newsletter_zustellbarkeit.py --selftest
    python3 scripts/newsletter_zustellbarkeit.py --pruefen [--md|--json]
    python3 scripts/newsletter_zustellbarkeit.py --pruefen --ohne-netz
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import datetime as _dt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newsletter_schedule as _schedule  # noqa: E402  (Di/Fr + Soll-Uhrzeit, eine Quelle)

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONE_Standard = "franksfinanzcheck.de"
PRÜFER_KENNUNG = "FranksFinanzcheck-Zustellbarkeitswaechter/1.0"
# Zwei Resolver, EINE Abfrage je Resolver. Der Parameter wird genau einmal
# angehängt – mit `urllib.parse.urlencode`, nicht per Zeichenkette. Bis
# 25.09.2026 endeten die Basen auf „?“ UND die Frage begann mit „?“:
# dns.google antwortete HTTP 400, cloudflare-dns.com ebenso, und die Wache
# meldete daraus „DNS nicht erreichbar“ (C0/C7 gelb), obwohl das Netz frei
# war – `curl 'https://dns.google/resolve?name=…&type=TXT'` bewies es. Ein
# Messfehler, der wie ein Netzausfall aussieht, ist der teuerste Fehler
# einer Wache: er entschuldigt jeden echten Befund gleich mit.
DOH_ENDPUNKTE = (("https://dns.google/resolve", {"dnssec": "false"}),
                 ("https://cloudflare-dns.com/dns-query", {}))
DOH_ZEITLIMIT = 8
RESEND_API = "https://api.resend.com"
RESEND_FREE_TAGESGRENZE = 100   # Resend Free: 3000/Monat, davon 100/Tag
# Resend (AWS-SES-Modell, seit 2025): Authentifizierung läuft über die
# SEND-SUBDOMAIN (Default `send.`) – SPF-TXT + Bounce-MX dort, DKIM auf
# `resend._domainkey`, DMARC an der Spitze. An der Apex-SPF ändert sich
# nichts. Der MX-Wert ist Region-spezifisch (Konto-Region), deshalb
# Muster statt fester Domain.
RESEND_SEND_SUBDOMAINE = "send"
RESEND_SES_MX = re.compile(r"feedback-smtp\.[a-z0-9-]+\.amazonses\.com",
                           re.IGNORECASE)
# CNAME-Ziele der Send-Subdomain (aktuelles Resend-Modell: forge-Delegation;
# davor: direkte SES-Eintraege). Was zaehLT: ein Resend-eigener Zielwert.
RESEND_SEND_ZIEL = re.compile(
    r"forge\.rmta\.net|rmta\.net|resend-dns\.com|amazonses\.com",
    re.IGNORECASE)
CLOUDFLARE_MX_MARKEN = ("mx.cloudflare.net", "route1.mx.cloudflare.net",
                        "route2.mx.cloudflare.net", "route3.mx.cloudflare.net")


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return ""


# ------------------------------------------------------------------ DNS (gemessen)
def _txt_fetzen(antwort: str) -> str:
    """DoH liefert einen langen TXT als `'teil1' 'teil2'` → ein String (RFC 1035)."""
    teile = re.findall(r'"([^"]*)"', antwort)
    return "".join(teile) if teile else antwort.strip().strip('"')


def doh_url(basis: str, name: str, typ: str, extra: dict | None = None) -> str:
    """Die vollständige DoH-Abfrage-URL – Parameter nur EINMAL, kodiert."""
    parameter = {"name": name, "type": typ}
    parameter.update(extra or {})
    return basis + "?" + urllib.parse.urlencode(parameter)


def _doh(name: str, typ: str) -> tuple[int, list[str]]:
    """Eine DNS-Frage, mehrere Resolver. → (RCode, Antworten).

    RCode 3 (NXDOMAIN) ist eine AUSSAGE („den Eintrag gibt es nicht"), ein
    Netzwerkfehler ist das nicht – die Wache darf eine Blockade nicht als
    fehlenden Eintrag melden und umgekehrt. Und ein HTTP-Fehler der
    Resolver ist ein dritter Fall: dann war die ABFRAGE falsch (4xx) oder
    die Kante hat sie abgewiesen (403) – beides wird mit Status gemeldet,
    nicht als „Netz weg“ verkleidet.
    """
    letzte_fehler: list[str] = []
    for basis, extra in DOH_ENDPUNKTE:
        knoten = urllib.parse.urlsplit(basis).netloc
        try:
            anfrage = urllib.request.Request(
                doh_url(basis, name, typ, extra), method="GET",
                headers={"accept": "application/dns-json",
                         "User-Agent": PRÜFER_KENNUNG})
            with urllib.request.urlopen(anfrage, timeout=DOH_ZEITLIMIT) as antwort:
                dat = json.loads(antwort.read().decode("utf-8", "replace"))
            code = int(dat.get("Status", -1))
            zeilen = [a.get("data", "") for a in (dat.get("Answer") or [])]
            if typ == "TXT":
                zeilen = [_txt_fetzen(z) for z in zeilen]
            return code, [z.strip() for z in zeilen if z and z.strip()]
        except urllib.error.HTTPError as exc:  # 4xx = Abfrage falsch gebaut
            letzte_fehler.append(f"{knoten}: HTTP {exc.code}")
        except Exception as exc:  # noqa: BLE001  (DNS, TLS, Timeout, Sperre …)
            letzte_fehler.append(f"{knoten}: {exc.__class__.__name__}")
    return -1, ["; ".join(letzte_fehler)]


def messluecke(fehler: list[str]) -> str:
    """Der Ist-Text einer Messlücke – mit der Unterscheidung, die zählt.

    Antworten BEIDE Resolver mit 4xx, ist die Abfrage falsch gebaut (Fehler
    der Wache); alles andere ist ein Ausgangsproblem (Netz, TLS, Blockade).
    Ohne diese Unterscheidung stand am 25.09.2026 „DNS nicht erreichbar“
    über einem HTTP 400, das die Wache sich selbst gebaut hatte.
    """
    roh = "; ".join(fehler)[:200] or "keine Antwort der Resolver"
    if fehler and all("HTTP 4" in f for f in fehler):
        return (roh + " – alle Resolver haben die ABFRAGE abgewiesen (4xx): "
                "das ist ein Fehler dieser Wache (URL/Parameter), kein "
                "Netzausfall.")
    return roh


AUFLOESER = _doh          # im Selbsttest austauschbar – dann trifft kein Netz


def dns(name: str, typ: str) -> tuple[str, list[str]]:
    """→ ("gemessen"|"nicht messbar"|"NXDOMAIN", antworten)."""
    code, antworten = AUFLOESER(name, typ)
    if code == -1:
        return "nicht messbar", antworten
    if code == 3:
        return "NXDOMAIN", []
    return "gemessen", antworten


# ------------------------------------------------------------------ HTTP (gemessen)
def _api_ruf(url: str, *, headers: dict | None = None, timeout: int = 15) -> tuple[int, str]:
    """Eine HTTP-Anfrage → (Code, Körper). Code 0 = keine Antwort (DNS/TLS/Timeout).

    Die Kanten-Blockage (403 mit Signaturfilter-Marke) wird NICHT in den
    normalen Fehlertext verpackt – wer Lauf #21 wiederholt, muss beide
    Klassen unterscheiden können.
    """
    anfrage = urllib.request.Request(url, method="GET",
                                     headers={"User-Agent": PRÜFER_KENNUNG,
                                              **(headers or {})})
    try:
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            return int(antwort.status or 0), antwort.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        try:
            rohe = exc.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            rohe = ""
        return int(exc.code or 0), rohe
    except Exception as exc:  # noqa: BLE001
        return 0, f"{exc.__class__.__name__}: {exc}"


NETZ_RUF = _api_ruf       # im Selbsttest austauschbar


_KANTEN_MUSTER = re.compile(
    r'(1010|browser.?s signature|Access denied[^"]*signature|Just a moment)', re.I)


def _kanten_block_reserve(code: int, antwort: str) -> bool:
    """403 der Cloudflare-KANTE (nicht des Anbieters): Signaturfilter-Marke.

    Reserve-Kopie – im Normalfall gilt `kanten_block` aus dem MAILER, denn
    Wache und Versand müssen dieselbe Antwort gleich lesen. Diese Kopie
    greift nur, wenn der Mailer nicht importierbar ist (dann ist der
    Versand ohnehin kaputt, und C7 soll trotzdem messen können).
    """
    if code != 403:
        return False
    return bool(_KANTEN_MUSTER.search(antwort or ""))


try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import newsletter_versand as _mailer          # noqa: E402  (Signatur-Quelle)
    kanten_block = _mailer.kanten_block           # eine Quelle, eine Wahrheit
    KANTEN_AUS_MAILER = True
except Exception:  # noqa: BLE001  (kaputter Mailer darf die Wache nicht töten)
    _mailer = None
    kanten_block = _kanten_block_reserve
    KANTEN_AUS_MAILER = False


# --------------------------------------------------------------------- Einstellungen
def zone(root: str) -> str:
    """Die zu prüfende Zone – aus der Variable, sonst die Domain der Impressum-URL."""
    gesetzt = os.environ.get("NEWSLETTER_MAILZONE", "").strip().lower()
    if gesetzt:
        return gesetzt.lstrip(".")
    toml = _read(os.path.join(root, "hugo.toml"))
    m = re.search(r'(?m)^\s*baseURL\s*=\s*"https?://([^/"]+)', toml)
    if m:
        return m.group(1).strip(".").lower()
    return ZONE_Standard


def absender(root: str) -> dict:
    """Absender + Reply-To aus derselben Quelle wie der Versand (Studio-SSOT)."""
    try:
        import newsletter_studio as studio
        e = studio.konfiguration(root, streng=False).get("email", {}) or {}
    except (Exception, SystemExit):  # noqa: BLE001  (Kaputt/fehlend: C-Regeln gelten trotzdem)
        e = {}
    a = e.get("absender", {}) or {}
    return {"email": (os.environ.get("NEWSLETTER_ABSENDER", "").strip()
                      or str(a.get("email") or f"news@{ZONE_Standard}")).strip(),
            "antwort_an": str(e.get("antwort_an") or "").strip()}


def worker_basis(root: str) -> str:
    """Die Worker-URL – aus der Variable, sonst der Formular-Endpunkt aus
    hugo.toml (dieselbe Quelle wie Capture-Wache N2), sonst leer."""
    gesetzt = os.environ.get("NEWSLETTER_WORKER_BASE", "").strip()
    if gesetzt:
        return gesetzt.rstrip("/")
    toml = _read(os.path.join(root, "hugo.toml"))
    m = re.search(r'(?m)^\s*newsletterFormAction\s*=\s*"([^"]+)"', toml)
    if m and m.group(1).strip():
        ziel = m.group(1).strip()
        u = urllib.parse.urlsplit(ziel)
        return f"{u.scheme}://{u.netloc}" if u.scheme and u.netloc else ""
    return ""


# ------------------------------------------------------------------------ Regeln C*
def _regel(nummer: str, ebene: str, gewicht: str, titel: str, ist: str, soll: str,
           weg: str, grund: str) -> dict:
    return {"regel": nummer, "ebene": ebene, "gewicht": gewicht, "titel": titel,
            "ist": ist, "soll": soll, "weg": weg, "grund": grund}


def _spf_werte(z: str) -> tuple[str, list[str]]:
    """Alle TXTs der Zone; SPF-Einträge (= `v=spf1`) separat."""
    status, zeilen = dns(z, "TXT")
    return status, zeilen


def pruefe_cloudflare(root: str) -> tuple[list[dict], dict]:
    """Alles, was in der DNS-Zone steht und die Zustellung entscheidet."""
    funde: list[dict] = []
    z = zone(root)
    abs_ = absender(root)
    abs_domain = abs_["email"].split("@")[-1].lower() if "@" in abs_["email"] else ""

    status, txts = _spf_werte(z)
    messwerte: dict = {"zone": z, "spf": (status, txts)}
    if status == "nicht messbar":
        return ([_regel("C0", "cloudflare", "nicht messbar",
                        "DNS nicht erreichbar – keine Zone geprüft",
                        messluecke(txts),
                        "DoH-Ausfall ist keine Messlücke der Zone: beim nächsten Lauf "
                        "erneut messen; `curl 'https://dns.google/resolve?name=" + z + "&type=TXT'`",
                        "—",
                        "Ohne Messung kein Grün: eine nicht ausgeführte Prüfung ist "
                        "keine bestandene Prüfung.")], messwerte)

    spf = [t for t in txts if t.strip().lower().startswith("v=spf1")]
    # C1 – SPF-Eintrag: genau einer, mit Mechanik. (SPF betrifft die AUSGANGS-
    # Authentifizierung der Zone – Resend sendet IM NAMEN der Zone. Ob Reply-to
    # ankommt, ist MX-Sache (C5/C6), nicht SPF-Sache.)
    if not spf:
        funde.append(_regel("C1", "cloudflare", "fund", "kein SPF-Eintrag in der Zone",
                            f"TXT {z}: " + (", ".join(txts)[:120] or "leer"),
                            "v=spf1 include:_spf.mx.cloudflare.net ~all "
                            "(die eigene SPF der Zone)",
                            "Cloudflare → DNS → Records → TXT anlegen (Name @)",
                            "Ohne SPF kann jede fremde IP im Zone-Namen mailen – "
                            "Empfänger-Server senken die Anlieferungsbewertung dafür "
                            "und Resends Mails verlieren den SPF-Nachweis."))
    elif len(spf) > 1:
        funde.append(_regel("C1", "cloudflare", "fund",
                            "mehrere SPF-Einträge (permanenter Fehler)",
                            " · ".join(spf)[:200],
                            "exakt EINER (die eigene der Zone, z. B. "
                            "v=spf1 include:_spf.mx.cloudflare.net ~all)",
                            "Cloudflare → DNS → TXT-Records: alle `v=spf1`-Einträge "
                            "auf einen zusammenführen",
                            "Mehrere SPF-Records machen die Zone per RFC dauerhaft "
                            "ungültig (permerror) – Empfänger behandeln das wie "
                            "keinen SPF."))
    else:
        wert = spf[0]
        if re.search(r"(include:|ip4:|ip6:|a\b|mx\b|redirect=)", wert):
            funde.append(_regel("C1", "cloudflare", "ok", "SPF in Ordnung",
                                wert[:200], "—", "—", ""))
        else:
            funde.append(_regel("C1", "cloudflare", "fund",
                                "SPF ohne Mechanik (niemand darf mailen)",
                                wert[:200],
                                "v=spf1 include:_spf.mx.cloudflare.net ~all",
                                "Cloudflare → DNS → TXT-Record @ bearbeiten",
                                "Ein SPF wie `v=spf1 ~all` nimmt niemanden auf – "
                                "auch die eigene Mail-Weiterleitung nicht."))

    # C2 – Resend-Send-Subdomain. Beide Formen der Resend-Infrastruktur sind
    # gültig: (a) AKTUELL: CNAME `send.` → Resend-Forge-Domain (SPF + Bounce-
    # Host sitzen auf dem Ziel, SPF- und MX-Lookup folgen die CNAME-Kette);
    # (b) ALT: SPF-TXT + Bounce-MX direkt auf `send.`. Die Apex-SPF ändert
    # sich in beiden Fällen NICHT. Die maßgebliche Prüfung ist B1
    # (Resend-Status „verified“) – hier wird die Zone selbst gemessen.
    send_c_s, send_c = dns(RESEND_SEND_SUBDOMAINE + "." + z, "CNAME")
    send_txt_s, send_txt = dns(RESEND_SEND_SUBDOMAINE + "." + z, "TXT")
    send_mx_s, send_mx = dns(RESEND_SEND_SUBDOMAINE + "." + z, "MX")
    cname_ok = (send_c_s == "gemessen"
                and any(RESEND_SEND_ZIEL.search(c) for c in send_c))
    send_spf = [t for t in send_txt if t.strip().lower().startswith("v=spf1")]
    send_mx_ok = [m for m in send_mx
                  if RESEND_SES_MX.search(m) or RESEND_SEND_ZIEL.search(m)]
    if cname_ok:
        funde.append(_regel("C2", "cloudflare", "ok",
                            "Resend-Send-Subdomain per CNAME (Forge-Modell)",
                            "CNAME send → " + send_c[0][:60], "—", "—", ""))
    elif send_spf and send_mx_ok:
        funde.append(_regel("C2", "cloudflare", "ok",
                            "Resend-Send-Subdomain direkt (SES-Modell)",
                            "TXT send: " + send_spf[0][:80] + " · MX send: "
                            + send_mx_ok[0][:60], "—", "—", ""))
    else:
        teile = [f"CNAME send: {send_c[0][:50]}" if send_c else
                 f"CNAME send: {send_c_s}",
                 "TXT send: " + (", ".join(send_txt)[:60] or "leer"),
                 "MX send: " + (", ".join(send_mx)[:60] or "leer")]
        gewicht = ("nicht messbar"
                   if "nicht messbar" in (send_c_s, send_txt_s, send_mx_s)
                   else "fund")
        funde.append(_regel("C2", "cloudflare", gewicht,
                            "Resend-Send-Subdomain fehlt oder unvollständig",
                            " · ".join(teile),
                            "CNAME `send` → `send.forge.rmta.net` (Resend-Setup) "
                            "ODER SPF-TXT + Bounce-MX auf `send.`",
                            "Resend → Domains → " + z + " → DNS-Setup → "
                            "„Cloudflare autorisieren“ (One-Klick, Resend legt die "
                            "Einträge selbst an) – oder die Einträge manuell "
                            "nach Cloudflare → DNS kopieren",
                            "Ohne die Send-Subdomain ist die Mail SPF-ungeprüft "
                            "und Rückläufer landen nirgends. Apex-SPF: bewusst "
                            "unverändert."))

    # C3 – Resend-DKIM: EIN Datensatz, TXT `resend._domainkey` (p=-Key).
    ds, d = dns("resend._domainkey." + z, "TXT")
    dkim_da = ds == "gemessen" and bool(d)
    if dkim_da:
        funde.append(_regel("C3", "cloudflare", "ok", "Resend-DKIM vorhanden",
                            "resend._domainkey gemessen (" + d[0][:40] + "…)",
                            "—", "—", ""))
    else:
        funde.append(_regel("C3", "cloudflare",
                            "fund" if ds != "nicht messbar" else "nicht messbar",
                            "Resend-DKIM fehlt",
                            f"resend._domainkey.{z}: {ds}",
                            "TXT `resend._domainkey` aus Resend (Wert beginnt mit "
                            "`p=` – im Stück kopieren; UI-Trunkatur ist die häufige "
                            "Fehlstelle)",
                            "Resend → Domains → " + z + " → DKIM-Record kopieren; "
                            "Cloudflare → DNS → TXT anlegen (Name "
                            "`resend._domainkey`, TTL auto)",
                            "DKIM trägt die Zustellung, wenn SPF auf geteilten IPs nie "
                            "alignt – ohne DKIM ist p=reject oben eine Selbstabsage."))

    # C4 – DMARC (Berichtsweg + Policy gegenüber den Echtheitsnachweisen)
    ms, dm = dns("_dmarc." + z, "TXT")
    if ms != "gemessen" or not dm:
        # Unmessbar ist kein Befund: ein Resolver-Ausfall darf nicht als
        # „kein DMARC“ durchgehen (dieselbe Klasse Fehler wie C0 am 25.09.).
        gewicht = ("nicht messbar" if ms == "nicht messbar"
                   else ("fund" if dkim_da else "hinweis"))
        funde.append(_regel("C4", "cloudflare", gewicht,
                            "kein DMARC-Eintrag" if ms != "nicht messbar"
                            else "DMARC nicht messbar",
                            f"_dmarc.{z}: {messluecke(dm) if ms == 'nicht messbar' else ms}",
                            "v=DMARC1; p=none; rua=mailto:dmarc@" + z + "; adkim=s; aspf=s",
                            "Cloudflare → DNS → TXT anlegen (Name `_dmarc`) – oder bei "
                            "Cloudflare: Email → DMARC",
                            "Ohne DMARC bekommt die Zone keine Zustellberichte – Ausfälle "
                            "fallen erst auf, wenn sich ein Leser beschwert."))
    else:
        text = " ".join(dm)
        has_ru = "rua=" in text
        policy = re.search(r"\bp=([a-z]+)", text)
        policy = policy.group(1) if policy else "none"
        if not has_ru:
            funde.append(_regel("C4", "cloudflare", "fund", "DMARC ohne Berichtsweg",
                                text[:200], "rua=mailto:dmarc@" + z + " ergänzen",
                                "Cloudflare → DNS → TXT `_dmarc` bearbeiten",
                                "p=reject ohne rua ist eine Entscheidung ohne Kontrolle: "
                                "was abgewiesen wird, erfährt niemand."))
        elif policy in ("reject", "quarantine") and not dkim_da:
            funde.append(_regel("C4", "cloudflare", "fund",
                                f"DMARC p={policy} ohne DKIM-Nachweis",
                                text[:200],
                                "erst Resend-DKIM (C3) abschließen, dann Policy "
                                "behalten – sonst p=none",
                                "C3 schliessen, dann hier nichts ändern",
                                "reject/quarantine sagt dem Empfänger: alles ohne "
                                "Alignment hart abzulehnen. Ohne DKIM ist ALLES ohne "
                                "Alignment – die eigene Mail wäre die erste Spende an "
                                "den Spamordner."))
        elif policy == "none" and dkim_da:
            funde.append(_regel("C4", "cloudflare", "hinweis",
                                "DMARC nur im Berichtmodus (p=none)",
                                text[:200],
                                "nach ein paar Wochen sauberer Berichte auf p=quarantine, "
                                "dann p=reject",
                                "Cloudflare → DNS → TXT `_dmarc` bearbeiten",
                                "p=none ist der sichere Start – aber er schützt nicht. "
                                "Die Stufen sind der übliche Weg."))
        else:
            funde.append(_regel("C4", "cloudflare", "ok",
                                f"DMARC in Ordnung (p={policy}, "
                                + ("mit" if has_ru else "ohne") + " rua)",
                                text[:200], "—", "—", ""))

    # C5 – MX auf der Zone (Reply-to muss ankommen). Unmessbar ist auch hier
    # kein Fund: „MX-Abfrage gescheitert“ ≠ „die Zone nimmt keine Mail an“.
    mst, mx = dns(z, "MX")
    if mst == "gemessen" and mx:
        funde.append(_regel("C5", "cloudflare", "ok", "MX vorhanden",
                            ", ".join(mx)[:120], "—", "—", ""))
    elif mst == "nicht messbar":
        funde.append(_regel("C5", "cloudflare", "nicht messbar",
                            "MX nicht messbar – Zone nicht beurteilt",
                            f"MX {z}: {messluecke(mx)}",
                            "beim nächsten Lauf erneut messen; `curl "
                            f"'https://dns.google/resolve?name={z}&type=MX'`", "—",
                            "Ohne Messung kein Grün – und kein „kein MX“: der "
                            "Resolver-Ausfall ist keine Aussage der Zone."))
    else:
        funde.append(_regel("C5", "cloudflare", "fund", "kein MX auf der Zone",
                            f"MX {z}: {mst}",
                            "Cloudflare-Email-Routing aktivieren (MX + Auto-Reply)",
                            "Cloudflare → Email → Email Routing → aktivieren",
                            "Antworten auf den Newsletter müssten nirgendwohin – und "
                            "jeder, der dem Absender schreibt, bekommt einen Hopper."))

    # C6 – Absender-Domain nimmt Mail an (empfohlen)
    if abs_domain and abs_domain != z:
        ast, amx = dns(abs_domain, "MX")
        if ast == "gemessen" and amx:
            funde.append(_regel("C6", "cloudflare", "ok",
                                f"Absender-Domain {abs_domain} nimmt Mail an",
                                ", ".join(amx)[:120], "—", "—", ""))
        else:
            funde.append(_regel("C6", "cloudflare",
                                "nicht messbar" if ast == "nicht messbar" else "hinweis",
                                f"Absender-Domain {abs_domain} ohne MX"
                                if ast != "nicht messbar" else
                                f"Absender-Domain {abs_domain} nicht beurteilt",
                                f"MX {abs_domain}: "
                                + (messluecke(amx) if ast == "nicht messbar" else ast),
                                "Reply-To auf eine Domain mit MX zeigen, oder Routing "
                                "einrichten",
                                "Zone-Interface der Absender-Domain (hier: "
                                "Cloudflare → Email)",
                                "Nur ein Wegweiser: der Versand läuft trotzdem, aber "
                                "Antworten der Leser gehen verloren."))

    messwerte["mx"] = (mst, mx)
    return funde, messwerte


# ------------------------------------------------------------------------ Regel C8
def letzter_faelliger_takt(jetzt: "_dt.datetime | None" = None) -> "_dt.datetime | None":
    """Der jüngste Di/Fr-Termin (SOLL_UTC) der bereits ≥ 10 Minuten zurückliegt.

    Vor dem allerersten fälligen Termin nach einem Deploy kann niemand einen
    Takt erwarten – deshalb liefert die Funktion den Termin, gegen den ein
    „letzter Dispatch“ gemessen werden DARF, nicht den nächsten.
    """
    jetzt = (jetzt or _dt.datetime.now(_dt.timezone.utc)).astimezone(_dt.timezone.utc)
    soll = _schedule.send_uhrzeit_utc()
    for zurueck in range(0, 8):
        tag = (jetzt - _dt.timedelta(days=zurueck)).date()
        if tag.weekday() not in _schedule.VERSANDTAGE:
            continue
        termin = _dt.datetime.combine(tag, soll, _dt.timezone.utc)
        if termin + _dt.timedelta(minutes=10) <= jetzt:
            return termin
    return None


def pruefe_taktgeber(health_roh: str, jetzt: "_dt.datetime | None" = None) -> dict:
    """C8 – hat der Worker-Taktgeber den letzten fälligen Digest gestartet?

    Liest die /healthz-Antwort des Workers (`takt.letzte.digest`). Kein Netz
    hier – der Aufrufer (C7) hat die Antwort schon. Ohne Messung kein Grün:
    eine unlesbare Antwort ist „nicht messbar“, kein ok.
    """
    weg_deploy = ("cd newsletter-worker && npx wrangler deploy (aktiviert [triggers].crons); "
                  "danach Cloudflare → Worker → Settings → Trigger Events")
    try:
        daten = json.loads(health_roh or "")
    except (ValueError, TypeError):
        daten = None
    if not isinstance(daten, dict):
        return _regel("C8", "worker", "nicht messbar",
                      "Taktgeber nicht prüfbar – /healthz liefert kein JSON",
                      (health_roh or "")[:120] or "leer",
                      "Worker-Version mit `takt` in /healthz deployen", weg_deploy,
                      "Ohne lesbare Antwort keine Aussage über den Takt.")
    takt = daten.get("takt")
    if not isinstance(takt, dict):
        return _regel("C8", "worker", "fund",
                      "Taktgeber fehlt – laufende Worker-Version kennt keine Cron-Triggers",
                      "/healthz ohne Feld `takt`",
                      "newsletter-worker deployen (src/index.js scheduled() + "
                      "wrangler.toml [triggers])", weg_deploy,
                      "Ohne Taktgeber hängt der Versand allein an GitHubs Scheduler – "
                      "der am 23.09. und 25.09.2026 den Versandtag still ausließ.")
    crons = takt.get("crons") or []
    digest_cron = next((c for c in crons if str(c).startswith("30 4 ")), None)
    if not digest_cron:
        return _regel("C8", "worker", "fund",
                      "Taktgeber ohne Digest-Takt (04:30 UTC Di/Fr)",
                      f"crons: {', '.join(map(str, crons))[:120] or 'leer'}",
                      "wrangler.toml [triggers].crons muss „30 4 * * TUE,FRI“ tragen",
                      weg_deploy, "")
    letzte = (takt.get("letzte") or {}).get("digest")
    faellig = letzter_faelliger_takt(jetzt)
    if not isinstance(letzte, dict):
        return _regel("C8", "worker", "hinweis",
                      "Taktgeber aktiv, aber noch nie gefeuert",
                      f"crons: {', '.join(map(str, crons))[:120]}; kein Eintrag takt.letzte.digest",
                      ("aussagekräftig ab dem nächsten Di/Fr 04:30 UTC" if faellig is None
                       else f"spätestens am fälligen Termin {faellig:%Y-%m-%d %H:%M} UTC "
                            "hätte ein Dispatch stehen müssen – Cloudflare → Worker → "
                            "Trigger Events prüfen (wurde der Worker nach dem Termin deployt, "
                            "ist das normal)"),
                      "Cloudflare → Workers & Pages → ff-newsletter → Settings → Trigger Events",
                      "Ein Takt, der noch nie tickte, ist kein Beweis – aber vor dem ersten "
                      "Termin auch kein Fund.")
    status = str(letzte.get("status") or "")
    ts_roh = str(letzte.get("ts") or "")
    try:
        ts = _dt.datetime.fromisoformat(ts_roh.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        ts = None
    if status != "dispatched":
        warum = str(letzte.get("warum") or letzte.get("http") or "unbekannt")
        soll = ("Fine-Grained-PAT mit „Actions: Read and write“ auf dieses Repo als "
                "Worker-Secret GITHUB_PAT setzen (`npx wrangler secret put GITHUB_PAT`)"
                if "403" in warum or "401" in warum else
                "Worker-Logs prüfen; GitHub-API-Status; danach Takt am nächsten Termin "
                "erneut messen")
        return _regel("C8", "worker", "fund",
                      "Taktgeber: letzter Digest-Dispatch fehlgeschlagen",
                      f"{ts_roh or '?'} · {status or '?'} · {warum} · "
                      f"{letzte.get('versuche', '?')} Versuch(e)",
                      soll, "github.com → Settings → Developer settings → Fine-grained tokens",
                      "Ein Takt, der ins Leere schlägt, ist so still wie gar keiner – "
                      "genau der Zustand vom 25.09.2026.")
    if faellig is not None and (ts is None or ts < faellig - _dt.timedelta(minutes=5)):
        return _regel("C8", "worker", "fund",
                      "Taktgeber hat den letzten fälligen Versandtag verpasst",
                      f"letzter Dispatch {ts_roh or '?'}, fällig war {faellig:%Y-%m-%d %H:%M} UTC",
                      "Cloudflare → Worker → Trigger Events: wurde der Cron ausgeführt? "
                      "Worker-Logs auf Fehler im scheduled()-Handler prüfen",
                      "Cloudflare → Workers & Pages → ff-newsletter → Settings",
                      "Ein verpasster Takt ohne Fehlereintrag heißt: der Cron feuerte nicht "
                      "– oder eine ältere Version ohne Taktgeber lief.")
    return _regel("C8", "worker", "ok", "Taktgeber tickt",
                  f"letzter Digest-Dispatch {ts_roh} (HTTP {letzte.get('http', '?')}, "
                  f"{letzte.get('versuche', '?')} Versuch(e)); crons: "
                  f"{', '.join(map(str, crons))[:100]}",
                  "—", "—", "")


# ------------------------------------------------------------------------ Regeln C7
def pruefe_worker(root: str, *, mit_netz: bool) -> list[dict]:
    """Der Capture-Endpunkt ist der Hahn für die ganze Kette: geht kein
    Wasser (Adresse) rein, hilft jeder noch so gute Pumpenversand."""
    if not mit_netz:
        return [_regel("C7", "worker", "nicht gemessen",
                       "Lauf ohne Netz – Endpunkt nicht geprüft",
                       "--ohne-netz gesetzt", "beim nächsten Lauf weglassen", "—",
                       "Kein Befund, kein Grün.")]
    basis = worker_basis(root)
    if not basis:
        return [_regel("C7", "worker", "hinweis",
                       "kein Capture-Endpunkt konfiguriert",
                       "NEWSLETTER_WORKER_BASE leer und kein newsletterFormAction in "
                       "hugo.toml",
                       "Worker deployen, dann Var `NEWSLETTER_WORKER_BASE` = "
                       "https://abos.franksfinanzcheck.de (Doku: "
                       "docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md)",
                       "Cloudflare → Workers → deploy; DNS → CNAME abos → Worker-Domain",
                       "Der Leerzustand ist ehrlich gemeldet – der Digest meldet denselben "
                       "Zustand als N0.")]
    u = urllib.parse.urlsplit(basis)
    host = (u.netloc or "").lower()
    if not host:
        return [_regel("C7", "worker", "fund", "Worker-Basis ist keine gültige URL",
                       basis[:120], "https://abos.franksfinanzcheck.de",
                       "Var NEWSLETTER_WORKER_BASE korrigieren", "")]
    status, antworten = dns(host, "CNAME")
    if status == "nicht messbar":
        return [_regel("C7", "worker", "nicht messbar",
                       "DNS nicht erreichbar – Endpunkt nicht geprüft",
                       messluecke(antworten),
                       "beim nächsten Lauf erneut messen", "—",
                       "Ohne Messung kein Grün.")]
    if status == "NXDOMAIN":
        return [_regel("C7", "worker", "fund",
                       f"Worker-Domain {host} löst sich nicht auf",
                       f"CNAME {host}: NXDOMAIN",
                       f"CNAME {host} → Worker-Domain (z. B. …workers.dev) anlegen",
                       "Cloudflare → DNS → Records → CNAME anlegen",
                       "Ohne Auflösung geht keine einzige Anmeldung rein – der Hahn der "
                       "ganzen Kette zu.")]
    # Antwort: der Worker muss antworten (2xx = Formular-Seite)
    code, antwort = NETZ_RUF(basis + "/", headers={"User-Agent": PRÜFER_KENNUNG})
    if code == 0:
        return [_regel("C7", "worker", "nicht messbar",
                       "Worker nicht erreichbar (DNS/TLS/Timeout)",
                       antwort[:200],
                       "Worker-Status prüfen (Cloudflare → Workers → Logs); "
                       "CNAME-Ziel gegen die Worker-Domain abgleichen", "—",
                       "Der DNS-Eintrag steht – die Antwort fehlt. Genau dazwischen "
                       "sitzt der Worker selbst.")]
    if kanten_block(code, antwort):
        return [_regel("C7", "worker", "fund",
                       "Signaturfilter vor dem Worker blockiert die Anfrage",
                       f"HTTP {code}: {antwort[:160]}",
                       "Cloudflare → Security → Bots: Worker-Pfad freigeben (oder "
                       "WAF-Regel prüfen)", "—",
                       "403 mit 1010-Marker kommt von der KANTE, nicht vom Worker – "
                       "der Worker hat die Anfrage nie gesehen.")]
    if 200 <= code < 300:
        return [_regel("C7", "worker", "ok", "Capture-Endpunkt lebt",
                       f"{host} → HTTP {code} (CNAME: {', '.join(antworten)[:120] or '—'})",
                       "—", "—", ""),
                pruefe_taktgeber(antwort)]
    return [_regel("C7", "worker", "fund",
                   f"Capture-Endpunkt antwortet HTTP {code}",
                   antwort[:200],
                   "Worker-Logs prüfen (Cloudflare → Workers → Logs); Version neu "
                   "deployen, wenn der Stand veraltet ist", "—",
                   "Ein 4xx/5xx am Formular-Endpunkt heisst: Adressen werden "
                   "angenommen und verworfen – das ist lauter als keine Antwort.")]


# ------------------------------------------------------------------------ Regeln B*
def pruefe_resend(root: str, *, mit_netz: bool) -> list[dict]:
    """Alles, was bei Resend und im Worker steht – ohne Key/Messung bleibt es
    „nicht gemessen“ (kein Grün). B0/B1 brauchen den Resend-Key, B2/B3 den
    Worker-Export: zwei Systeme, zwei Messungen, keine gegenseitige Stummschaltung."""
    if not mit_netz:
        return [_regel("B0", "resend", "nicht gemessen",
                       "Lauf ohne Netz – Resend und Worker nicht geprüft",
                       "--ohne-netz gesetzt", "beim nächsten Lauf weglassen", "—",
                       "Kein Befund, kein Grün: eine nicht ausgeführte Prüfung ist "
                       "keine bestandene Prüfung.")]
    out: list[dict] = []
    out += _pruefe_resend_api(root)
    anzahl = _pruefe_worker_liste(root, out)
    out += _pruefe_plan(anzahl)
    return out


def _resend_name(domäne: dict) -> str:
    """Der Domainname aus einer Resend-Antwort.

    Die API (GET /domains, Stand 2026) liefert `name`; ältere Fassungen und
    manche Kunden-Beispiele `domain`. Gelesen wird beides – am 25.09.2026
    las die Wache nur `domain`, bekam für jede Domäne `None` und meldete
    daraus einen Falsch-Fund („Sende-Domain fehlt im Resend-Konto ·
    Konto-Domänen: None“), obwohl die API mit `name` antwortet.
    """
    return str(domäne.get("name") or domäne.get("domain") or "").strip().lower()


def _resend_verifiziert(domäne: dict) -> tuple[bool, str]:
    """→ (verifiziert, Statuswort). Resend liefert `status`
    (`verified`, `pending`, `not_started`, `failed`, `temporary_failure`,
    `partially_verified`), ältere Antworten `verified: true/false`.
    Beides wird gelesen; ein unbekanntes Statuswort ist NICHT verifiziert
    (kein Grün aus Nichtwissen)."""
    st = str(domäne.get("status") or "").strip().lower()
    if domäne.get("verified") is True or st == "verified":
        return True, st or "verified"
    if st == "partially_verified":
        # Teilzustand: nur die Sende-Berechtigung zählt für diesen Versand.
        faehig = str((domäne.get("capabilities") or {}).get("sending") or "").lower()
        return faehig == "enabled", st
    return False, st or ("unverified" if domäne.get("verified") is False else "unbekannt")


def _sendesignatur(key: str) -> dict:
    """Die Kopfzeilen des VERSANDWEGS – aus dem Mailer, nicht nachgebaut.

    B0 misst nur dann den Weg, den der Versand geht, wenn die Signatur
    dieselbe ist (User-Agent!). Am 25.09.2026 fragte die Wache mit ihrem
    eigenen User-Agent, der Versand mit `Python-urllib/3.x`: B0 grün, der
    Testversand an derselben Kante HTTP 403 · Error 1010. Ist der Mailer
    nicht importierbar, bleibt die Wache ehrlich ungemessen (siehe unten)
    statt mit einer eigenen Signatur „ok“ zu melden.
    """
    if _mailer is None:              # Import oben gescheitert → keine Signatur
        return {}
    return _mailer.api_headers(key)


def _pruefe_resend_api(root: str) -> list[dict]:
    """B0 (Netzweg, OHNE Key prüfbar: 401 = Kante durchlässig) + B1 (Domain
    verifiziert, nur mit Key)."""
    out: list[dict] = []
    key = os.environ.get("RESEND_API_KEY", "").strip() or \
        os.environ.get("NEWSLETTER_RESEND_KEY", "").strip()
    headers = _sendesignatur(key)
    if not headers:
        out.append(_regel("B0", "resend", "nicht messbar",
                          "Sendesignatur nicht verfügbar – Netzweg nicht gemessen",
                          "newsletter_versand.py nicht importierbar",
                          "Mailer prüfen (`python3 scripts/newsletter_versand.py "
                          "--selftest`); B0 erst dann wieder messen",
                          "—",
                          "Die Vorprüfung muss mit DERSELBEN Signatur fragen wie der "
                          "Versand – sonst misst sie einen Weg, den niemand geht."))
        return out
    code, antwort = NETZ_RUF(RESEND_API + "/domains", headers=headers)
    if code == 0:
        out.append(_regel("B0", "resend", "fund" if key else "nicht messbar",
                          "Netzweg zur Resend-API gestört (DNS/TLS/Zeitlimit)",
                          antwort[:300],
                          "DoH/Ausgang der Laufumgebung prüfen; `curl -sI "
                          "https://api.resend.com/` muss antworten",
                          "— (das ist kein Konto-Befund)",
                          "Ohne Antwort der Kante ist jede Aussage über Domain und "
                          "Zustellung unmöglich – und der Versandlauf würde denselben "
                          "Abbruch melden."))
        return out
    if kanten_block(code, antwort):
        out.append(_regel("B0", "resend", "fund",
                          "Signaturfilter vor der API blockiert den Lauf",
                          f"HTTP {code}: {antwort[:200]}",
                          "Cloudflare/WAF zwischen Runner und api.resend.com prüfen; "
                          "Lauf aus anderem Netz starten, wenn lokal reproduzierbar",
                          "— (kein Konto-Befund)",
                          "HTTP 403 mit 1010-Marker ist keine Absender-Absage: die "
                          "Anfrage erreichte Resend nie. Genau diese Verwechslung "
                          "hatte Lauf #21 wochenlang rot gemeldet."))
        return out
    if not key:
        out.append(_regel("B0", "resend", "info",
                          "Kante durchlässig, Key fehlt – Konto nicht geprüft",
                          f"Antwort HTTP {code} von api.resend.com (kein Zugriff ohne Key)",
                          "Secret RESEND_API_KEY setzen, dann prüft die Wache die "
                          "Sende-Domain",
                          "Repo → Settings → Secrets and variables → Actions → "
                          "`RESEND_API_KEY`",
                          "Der Vorlauf ist gemessen, das Konto bewusst nicht: ohne Key "
                          "gehört hierhin ein Hinweis, kein Grün."))
        return out
    if code not in (200, 201):
        out.append(_regel("B0", "resend", "fund", "API-Aufruf fehlgeschlagen",
                          f"HTTP {code}: {antwort[:200]}",
                          "Key gültig? Scope des Keys = Sending-Domains?",
                          "Resend → API Keys → Schlüssel prüfen", ""))
        return out
    out.append(_regel("B0", "resend", "ok",
                      "Netzweg zur Resend-API frei (mit der Signatur des Versands)",
                      f"HTTP {code} von api.resend.com · User-Agent "
                      f"„{headers.get('User-Agent', '').split(' ')[0]}“", "—", "—", ""))
    z = zone(root)
    try:
        daten = json.loads(antwort)
    except json.JSONDecodeError:
        daten = {}
    domänen = daten.get("data")
    if not isinstance(domänen, list):
        # 200, aber keine Liste: kein Fund und kein Grün – die Antwort ist
        # nicht deutbar. (Ein `{}` als [] zu lesen hat am 25.09.2026
        # „Konto-Domänen: None“ ergeben.)
        out.append(_regel("B1", "resend", "nicht messbar",
                          "Kontostand nicht deutbar – Domänenliste fehlt",
                          f"Antwort ohne `data`-Liste: {str(antwort)[:160]}",
                          "Antwort im Resend-Dashboard gegenprüfen (Sending Domains); "
                          "Key-Scope prüfen (Domains: Read)",
                          "Resend → API Keys / Sending Domains",
                          "Kein Grün ohne Messung: eine unlesbare Antwort ist keine "
                          "leere Kontoliste."))
        return out
    domänen = [d for d in domänen if isinstance(d, dict)]
    own = next((d for d in domänen if _resend_name(d) == z), None)
    if own is None:
        out.append(_regel("B1", "resend", "fund",
                          f"Sende-Domain {z} fehlt im Resend-Konto",
                          "Konto-Domänen: "
                          + (", ".join(_resend_name(d) for d in domänen
                                       if _resend_name(d)) or "keine")
                          + ("  (Antwort gekürzt: has_more=true)"
                             if daten.get("has_more") else ""),
                          "Domain in Resend hinzufügen (Sending Domains → Add Domain) "
                          "und die DNS-Einträge (C2/C3) abschliessen",
                          "Resend → Sending Domains → Add Domain",
                          "Ohne registrierte Domain nimmt Resend keine Mail der Zone an "
                          "– der Versand bricht in derselben Vorprüfung ab, die hier "
                          "gemessen wurde."))
    elif not _resend_verifiziert(own)[0]:
        out.append(_regel("B1", "resend", "fund",
                          f"Sende-Domain {z} nicht verifiziert",
                          f"Domain vorhanden, Status `{_resend_verifiziert(own)[1]}`",
                          "DNS-Einträge aus dem Resend-Dashboard vollständig anlegen "
                          "(SPF-TXT + MX auf `send.`, DKIM `resend._domainkey`)",
                          "Resend → Sending Domains → die Checkliste der Domain",
                          "Verifizierung = SPF+DKIM live. Solange sie fehlt, sendet "
                          "Resend nicht."))
    else:
        out.append(_regel("B1", "resend", "ok", f"Domain {z} verifiziert",
                          f"Status `{_resend_verifiziert(own)[1]}`", "—", "—", ""))
        # Zusatzbeleg: Resends eigener Record-Status (welcher Eintrag ist
        # verifiziert, welcher verendet). Die List-Antwort traegt die Aussage
        # (verified = Resend hat die Eintraege geprueft); das Nachlesen faengt
        # spaetere Verfaelle – und faellt ehrlich ab, wenn es nicht gelingt.
        did = str(own.get("id") or "")
        if did:
            d_code, d_antwort = NETZ_RUF(RESEND_API + "/domains/" + did,
                                         headers=headers)
            if d_code in (200, 201):
                try:
                    recs = (json.loads(d_antwort) or {}).get("records") or []
                except json.JSONDecodeError:
                    recs = []
                for rec in recs:
                    st = str(rec.get("status") or "")
                    if st == "verified":
                        continue
                    optional = str(rec.get("record") or "").lower() == "tracking"
                    out.append(_regel(
                        "B1", "resend", "hinweis" if optional else "fund",
                        f"Resend-Record nicht verifiziert "
                        f"({rec.get('type') or '?'} {rec.get('name') or '?'})",
                        f"status: {st or 'unbekannt'}",
                        "Resend → Domains → " + z + " → die Checkliste "
                        "abschließen",
                        "Resend → Domains → " + z,
                        "Tracking ist bei uns ausgeschaltet (Mailer sendet "
                        "click_tracking=false) – der CNAME ist dann harmlos."
                        if optional else
                        "Solange der Eintrag nicht verifiziert ist, kann die "
                        "Authentifizierung lückenhaft sein."))
            else:
                out.append(_regel("B1", "resend", "info",
                                  "Domain verifiziert; Record-Status nicht "
                                  "nachgelesen",
                                  f"GET /domains/<id>: "
                                  f"HTTP {d_code if d_code else 'keine Antwort'}",
                                  "beim nächsten Lauf erneut versuchen", "—",
                                  "Die List-Antwort trägt die Aussage; das "
                                  "Nachlesen ist Zusatzbeleg, kein Ersatz."))
    return out


def _pruefe_worker_liste(root: str, out: list[dict]) -> int | None:
    """B2 – Abonnentenstand aus dem Worker-Export (NICHT aus Resend – die
    Liste kennt Resend nicht, das ist der Punkt). → anzahl oder None."""
    base = os.environ.get("NEWSLETTER_WORKER_BASE", "").strip().rstrip("/")
    wkey = os.environ.get("NEWSLETTER_WORKER_EXPORT_KEY", "").strip()
    if not base or not wkey:
        out.append(_regel("B2", "worker", "hinweis",
                          "Abonnentenstand nicht gemessen (Worker-Konfiguration fehlt)",
                          "NEWSLETTER_WORKER_BASE" + ("" if base else " fehlt")
                          + (" und NEWSLETTER_WORKER_EXPORT_KEY" if not wkey else ""),
                          "Secret NEWSLETTER_WORKER_EXPORT_KEY und Var "
                          "NEWSLETTER_WORKER_BASE setzen (Doku: "
                          "docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md)",
                          "Repo → Settings → Secrets and variables → Actions",
                          "Ohne Export-Schlüssel bleibt die Liste ein Schwarzbox – und "
                          "deshalb auch ungemessen."))
        return None
    u = urllib.parse.urlsplit(base)
    host = (u.netloc or "").lower()
    cstat, cantwort = NETZ_RUF(base + "/export/abonnenten", headers={"x-ff-key": wkey})
    if cstat == 0:
        out.append(_regel("B2", "worker", "fund",
                          "Worker-Export nicht erreichbar",
                          cantwort[:200],
                          "Worker-Logs prüfen; CNAME gegen Worker-Domain abgleichen",
                          "—", "Ohne Export kein Versand – der Lauf scheitert "
                          "fail-closed am selben Punkt."))
        return None
    if cstat in (401, 403):
        out.append(_regel("B2", "worker", "fund",
                          f"Worker-Export abgelehnt (HTTP {cstat})",
                          cantwort[:200],
                          "NEWSLETTER_WORKER_EXPORT_KEY exakt auf den Worker-Secret "
                          "abgleichen (derselbe Schlüssel, beide Seiten)",
                          "Cloudflare → Workers → Settings → Variables → EXPORT_KEY",
                          "Ein falsch übergebener Key ist die häufigste Stummschaltung "
                          "des eigenen Systems."))
        return None
    if cstat not in (200, 201):
        out.append(_regel("B2", "worker", "fund",
                          f"Worker-Export antwortet HTTP {cstat}",
                          cantwort[:200], "Worker-Logs prüfen", "—", ""))
        return None
    try:
        edaten = json.loads(cantwort)
        liste = edaten.get("abonnenten")
        anzahl = int(edaten.get("anzahl")
                     or (len(liste) if isinstance(liste, list) else 0))
    except (json.JSONDecodeError, TypeError, ValueError):
        out.append(_regel("B2", "worker", "fund",
                          "Worker-Export antwortet, aber nicht als JSON",
                          cantwort[:200], "Worker-Version gegen Repo-Stand abgleichen "
                          "(neu deployen)", "—", ""))
        return None
    out.append(_regel("B2", "worker", "ok" if anzahl else "info",
                      f"{anzahl} aktive Abonnenten"
                      + ("" if anzahl else
                         " (leer – Normalzustand vor der Freischaltung)"),
                      f"{host}/export/abonnenten → HTTP {cstat}", "—", "—",
                      "" if anzahl else
                      "Bis die Liste wächst, ist jeder Listen-Versand leer – der "
                      "Testweg ist --test-adresse, nicht --live."))
    return anzahl


def _pruefe_plan(anzahl: int | None) -> list[dict]:
    """B3 – Plan-Grenze: Resend Free = 3000/Monat, davon 100/Tag."""
    if anzahl is None:
        return [_regel("B3", "resend", "nicht gemessen",
                       "Plan-Grenze nicht geprüft (Liste unbekannt)",
                       "B2 hat keinen Wert geliefert",
                       "B2 erst schließen", "—",
                       "Ohne Listenstärke kein Urteil über die Tagesgrenze.")]
    if anzahl > RESEND_FREE_TAGESGRENZE:
        return [_regel("B3", "resend", "hinweis",
                       f"{anzahl} Abonnenten > Free-Tagesgrenze "
                       f"({RESEND_FREE_TAGESGRENZE}/Tag)",
                       "Resend Free: 3000/Monat, davon 100/Tag",
                       "Resend-Plan upgraden (oder Versand-Tage halten und Rest im "
                       "Nachgang-Lauf verteilen)",
                       "Resend → Billing → Upgrade",
                       "Nicht ein Alarm: mit 2 Versandtagen/Woche und einem "
                       "nachholenden Lauf verteilt sich eine Liste über mehrere Tage – "
                       "der Preis ist ein späterer Zustelltag für die letzten Abos.")]
    return [_regel("B3", "resend", "ok",
                   f"Liste unter der Free-Tagesgrenze ({anzahl} ≤ "
                   f"{RESEND_FREE_TAGESGRENZE})",
                   "—", "—", "", "")]


# ------------------------------------------------------------------------ Regeln S*
def _letzter_journal_eintrag(root: str, praefix: str = "") -> dict | None:
    """Die letzte Journal-Zeile (optional nur Ausgaben mit Präfix).

    Das Journal trägt nur Adress-Hashes und die Anbieter-Meldung – es ist
    zitierfähig, auch im Summary eines öffentlichen Repos.
    """
    pfad = os.path.join(root, "data", "newsletter_journal.jsonl")
    try:
        with open(pfad, encoding="utf-8") as fh:
            zeilen = fh.readlines()
    except OSError:
        return None
    for zeile in reversed(zeilen):
        try:
            eintrag = json.loads(zeile)
        except (json.JSONDecodeError, TypeError):
            continue
        if praefix and not str(eintrag.get("ausgabe") or "").startswith(praefix):
            continue
        return eintrag
    return None


def pruefe_state(root: str) -> list[dict]:
    out: list[dict] = []
    pfad = os.path.join(root, "data", "newsletter_state.json")
    try:
        state = json.loads(_read(pfad) or "{}")
    except json.JSONDecodeError:
        return [_regel("S1", "repo", "fund",
                       "data/newsletter_state.json ist kein lesbares JSON",
                       _read(pfad)[:120] or "leer",
                       "Datei reparieren (Schreibzugriff: nur über "
                       "`scripts/newsletter_digest.py`) – der Duplikatsschutz liest sie",
                       "—",
                       "Ein unlesbarer Status bedeutet: der nächste Lauf weiß nicht, was "
                       "schon draußen war. Das ist genau die Doppelzustellung, die dieser "
                       "ganze Apparat verhindern soll.")]
    if state.get("versand_unklar"):
        block = state["versand_unklar"]
        out.append(_regel("S1", "repo", "fund",
                          "Versand-Halt aktiv (Ergebnis eines Laufs war unbelegbar)",
                          f"Kennung {block.get('kennung', '?')}, notiert "
                          f"{block.get('zeitpunkt', '?')}",
                          "in den Transport-Logbooks/Postfächern nachsehen (Resend → "
                          "Emails, Journal: data/newsletter_journal.jsonl trägt nur "
                          "Hashes), dann den Block `versand_unklar` aus der "
                          "Statusdatei entfernen",
                          "Resend → Emails (Suche nach Datum) + Actions → Lauf-Log",
                          "Der Halt ist gewollt: kein Lauf schickt dieselbe Ausgabe "
                          "zweimal, nur weil einer keine Quittung bekam."))
    pending = state.get("pending") or []
    if pending:
        out.append(_regel("S2", "repo", "info",
                          f"{len(pending)} Artikel warten auf den Versand",
                          ", ".join(str(p) for p in pending[:3]) +
                          (f" … (+{len(pending) - 3})" if len(pending) > 3 else ""),
                          "nächster Di/Fr-Cron 04:30 UTC holt sie ab",
                          "Actions → Newsletter-Daily → Run workflow (`tage` 3 für "
                          "einen Nachlauf)", ""))
    letzte = state.get("letzte_ausgabe") or {}
    if letzte.get("datum"):
        out.append(_regel("S3", "repo", "ok", "letzter Versand belegt",
                          f"{letzte.get('datum')} · „{letzte.get('betreff', '—')}"[:120] +
                          f"“ · {letzte.get('transport', '—')}", "—", "—", ""))
    else:
        # Der Status kennt nur den LISTEN-Versand. Ein Testversand steht im
        # Journal – ihn zu nennen macht aus „nichts passiert“ ein „das ist
        # passiert“ (am 25.09.2026 scheiterte der Testversand, und der Lauf
        # zeigte an dieser Stelle nichts davon).
        j = _letzter_journal_eintrag(root)
        ist = "data/newsletter_state.json trägt keine letzte_ausgabe"
        if j:
            ist += (f"; letzte Journal-Zeile: {j.get('ausgabe', '?')} · "
                    f"{j.get('status', '?')}"
                    + (f" · {str(j.get('detail') or '')[:80]}"
                       if j.get("detail") else ""))
        out.append(_regel("S3", "repo", "hinweis",
                          "noch kein Listen-Versand protokolliert",
                          ist,
                          "erste Ausgabe = Testversand, dann Freigabe (Doku: "
                          "docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md)",
                          "Actions → Newsletter-Daily (Capture-Wache + Digest) → "
                          "Run workflow", ""))
    return out


# ------------------------------------------------------------------------- Ausgabe
GEWICHTE = ("fund", "hinweis", "nicht messbar", "nicht gemessen", "info", "ok")


def pruefe(root: str = BLOG_DIR, *, mit_netz: bool = True) -> dict:
    funde = []
    if mit_netz:
        cf, messwerte = pruefe_cloudflare(root)
        funde += pruefe_worker(root, mit_netz=True)
    else:
        cf, messwerte = ([_regel("C0", "cloudflare", "nicht gemessen",
                                 "Lauf ohne Netz – Zone nicht geprüft",
                                 "--ohne-netz gesetzt", "beim nächsten Lauf weglassen",
                                 "—", "Ohne Messung kein Grün.")], {})
        funde += pruefe_worker(root, mit_netz=False)
    funde += cf
    funde += pruefe_resend(root, mit_netz=mit_netz)
    funde += pruefe_state(root)
    zählung = {g: sum(1 for f in funde if f["gewicht"] == g) for g in GEWICHTE}
    return {"zone": messwerte.get("zone", zone(root)), "funde": funde,
            "messwerte": messwerte, "zählung": zählung,
            "rc": 1 if zählung["fund"] else 0,
            "gemessen": mit_netz}


def als_md(erg: dict) -> str:
    zeilen = ["## 🛡 Newsletter-Zustellbarkeit (Cloudflare + Resend + Worker)", "",
              f"Zone `{erg['zone']}` · " +
              " · ".join(f"{k} {v}" for k, v in erg["zählung"].items() if v) +
              (" · _ohne Netz, Prüfung nicht ausgeführt_" if not erg["gemessen"] else ""),
              ""]
    sym = {"fund": "❌", "hinweis": "⚠", "info": "ℹ️", "ok": "✅",
           "nicht messbar": "🌫", "nicht gemessen": "🌫"}
    for f in erg["funde"]:
        zeilen.append(f"{sym.get(f['gewicht'], '•')} **[{f['regel']}/{f['ebene']}] "
                      f"{f['titel']}**  ")
        if f["ist"]:
            zeilen.append(f"  * Ist: `{f['ist'][:300]}`  ")
        if f["soll"] and f["soll"] != "—":
            zeilen.append(f"  * Soll: {f['soll']}  ")
        if f["weg"] and f["weg"] != "—":
            zeilen.append(f"  * Weg: {f['weg']}  ")
        if f["grund"]:
            zeilen.append(f"  * Warum: {f['grund']}  ")
        zeilen.append("")
    if not erg["funde"]:
        zeilen.append("✅ Keine Befunde – die gemessenen Schichten tragen denselben Stand.")
    return "\n".join(zeilen)


# ------------------------------------------------------------------------ Selbsttest
def _selftest() -> int:
    """Hermetisch: DNS und HTTP werden eingespiegelt – kein Netz im Lauf."""
    fehler: list = []
    zaehler = 0

    def pruefe_es(bedingung: bool, meldung: str) -> None:
        nonlocal zaehler
        if bedingung:
            zaehler += 1
        else:
            fehler.append(meldung)

    ZONE = "beispiel.de"
    zonen_umgebung = os.environ.get("NEWSLETTER_MAILZONE", "")
    os.environ["NEWSLETTER_MAILZONE"] = ZONE      # dieselbe Override wie im Lauf

    def zone_gesund(name: str, typ: str) -> tuple[int, list[str]]:
        werte = {
            ZONE: {"MX": [0, ["17 route2.mx.cloudflare.net.",
                             "41 route1.mx.cloudflare.net."]],
                   "TXT": [0, ["v=spf1 include:_spf.mx.cloudflare.net ~all"]]},
            f"send.{ZONE}": {"CNAME": [0, ["send.forge.rmta.net"]],
                             "TXT": [3, []], "MX": [3, []]},
            f"_dmarc.{ZONE}": {"TXT": [0, ["v=DMARC1; p=reject; adkim=s; aspf=s; "
                                           "rua=mailto:dmarc@beispiel.de;"]]},
            f"resend._domainkey.{ZONE}": {"TXT": [0, ["k=rsa;p=MII…resend"]]},
        }
        for sel in ("mail", "default", "s1", "k1", "dkim"):
            werte.setdefault(f"{sel}._domainkey.{ZONE}", {"TXT": [3, []], "CNAME": [3, []]})
        try:
            return werte[name][typ]
        except KeyError:
            return 3, []

    def netz_gesund(url: str, *, headers=None, timeout=15):
        kopf = headers or {}
        if url.startswith("https://api.resend.com"):
            if "Authorization" not in kopf:
                return 401, '{"status":"error","message":"Missing or Invalid API Key"}'
            return 200, json.dumps({"data": [{"domain": ZONE, "verified": True}]})
        if url.rstrip("/").endswith("/export/abonnenten"):
            return 200, json.dumps({"anzahl": 12,
                                    "abonnenten": [{"email": f"a{i}@beispiel.de",
                                                   "token": "t", "themen": [],
                                                   "bestaetigt": "2026-01-01T00:00:00Z"}
                                                  for i in range(12)]})
        # / und /healthz liefern dieselbe Health-Antwort (Worker-Routing)
        return 200, json.dumps(health_gesund())

    def health_gesund(**letzte_digest):
        letzter = letzter_faelliger_takt()
        eintrag = {"ts": ((letzter + _dt.timedelta(seconds=8)).isoformat()
                          if letzter else "2026-09-25T04:30:08+00:00"),
                   "cron": "30 4 * * TUE,FRI", "workflow": "newsletter-daily.yml",
                   "status": "dispatched", "http": 204, "versuche": 1, "warum": None}
        eintrag.update(letzte_digest)
        return {"ok": True, "kv": "ok",
                "takt": {"crons": ["30 4 * * TUE,FRI", "5 5 * * TUE,FRI", "17 * * * *"],
                         "letzte": {"digest": eintrag}}}

    global AUFLOESER, NETZ_RUF
    echt_aufloeser, echt_netz = AUFLOESER, NETZ_RUF
    try:
        AUFLOESER = zone_gesund
        NETZ_RUF = netz_gesund
        import tempfile
        tmp = tempfile.mkdtemp(prefix="zustell-selbsttest-")
        os.makedirs(os.path.join(tmp, "data"), exist_ok=True)
        with open(os.path.join(tmp, "data", "newsletter_state.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"pending": ["a"],
                       "letzte_ausgabe": {"datum": "2026-09-22",
                                          "betreff": "Test", "transport": "dryrun",
                                          "versendet": ["x"]}}, fh)
        os.environ.pop("NEWSLETTER_WORKER_BASE", None)
        os.environ.pop("NEWSLETTER_WORKER_EXPORT_KEY", None)
        os.environ.pop("RESEND_API_KEY", None)

        # 1. Gesunde Welt (ohne Resend-Key: B0 „info", B1–B3 nicht gemessen)
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("C1", {}).get("gewicht") == "ok",
                  f"SPF ok erwartet: {rg.get('C1')}")
        pruefe_es(rg.get("C2", {}).get("gewicht") == "ok",
                  f"send.-Einträge (C2) erwartet ok: {rg.get('C2')}")
        pruefe_es(rg.get("C3", {}).get("gewicht") == "ok",
                  f"DKIM resend._domainkey (C3) erwartet ok: {rg.get('C3')}")
        pruefe_es(rg.get("C4", {}).get("gewicht") == "ok",
                  f"DMARC p=reject+rua+DKIM erwartet ok: {rg.get('C4')}")
        pruefe_es(rg.get("C5", {}).get("gewicht") == "ok", f"MX erwartet ok: {rg.get('C5')}")
        pruefe_es(rg.get("B0", {}).get("gewicht") == "info",
                  f"401-Proxy ohne Key: info erwartet: {rg.get('B0')}")
        pruefe_es(rg.get("S3", {}).get("gewicht") == "ok",
                  f"letzte_ausgabe erwartet ok: {rg.get('S3')}")
        pruefe_es(rg.get("S2", {}).get("gewicht") == "info",
                  f"pending erwartet info: {rg.get('S2')}")

        # 2. Resend-Send-Subdomain fehlt → C2 Fund – und die Apex-SPF bleibt
        #    trotzdem OK (sie braucht KEIN Resend-Include mehr)
        def zone_ohne_send(name: str, typ: str) -> tuple[int, list[str]]:
            if name == f"send.{ZONE}":
                return 3, []
            return zone_gesund(name, typ)
        AUFLOESER = zone_ohne_send
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("C2", {}).get("gewicht") == "fund",
                  f"fehlende send.-Einträge melden nicht Fund: {rg.get('C2')}")
        pruefe_es(rg.get("C1", {}).get("gewicht") == "ok",
                  f"Apex-SPF ohne Resend-Include muss ok sein: {rg.get('C1')}")

        # 2b. SES-Form unvollständig (keine CNAME, SPF-TXT vorhanden,
        #      Bounce-MX fehlt) → C2 Fund
        def zone_ohne_bounce(name: str, typ: str) -> tuple[int, list[str]]:
            if name == f"send.{ZONE}" and typ in ("MX", "CNAME"):
                return 3, []
            return zone_gesund(name, typ)
        AUFLOESER = zone_ohne_bounce
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("C2", {}).get("gewicht") == "fund",
                  f"fehlendes Bounce-MX meldet nicht Fund: {rg.get('C2')}")

        # 2c. Altes SES-Modell (keine CNAME, SPF-TXT + Bounce-MX direkt auf
        #      send.) bleibt als zweite gültige Form ok
        def zone_ses_form(name: str, typ: str) -> tuple[int, list[str]]:
            if name == f"send.{ZONE}":
                if typ == "CNAME":
                    return 3, []
                if typ == "TXT":
                    return 0, ["v=spf1 include:amazonses.com ~all"]
                return 0, ["10 feedback-smtp.us-east-1.amazonses.com"]
            return zone_gesund(name, typ)
        AUFLOESER = zone_ses_form
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("C2", {}).get("gewicht") == "ok",
                  f"SES-Form (TXT+MX direkt) erwartet ok: {rg.get('C2')}")
        AUFLOESER = zone_gesund

        # 3. Kein DKIM + p=reject → C3 Fund UND C4 Fund (Selbstabsage)
        def zone_ohne_dkim(name: str, typ: str) -> tuple[int, list[str]]:
            if name == f"resend._domainkey.{ZONE}":
                return 3, []
            return zone_gesund(name, typ)
        AUFLOESER = zone_ohne_dkim
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("C3", {}).get("gewicht") == "fund",
                  f"fehlendes DKIM meldet nicht Fund: {rg.get('C3')}")
        pruefe_es(rg.get("C4", {}).get("gewicht") == "fund",
                  f"p=reject ohne DKIM meldet nicht Fund: {rg.get('C4')}")

        # 4. p=none mit DKIM → nur Hinweis (Berichtmodus)
        def zone_p_none(name: str, typ: str) -> tuple[int, list[str]]:
            if name == f"_dmarc.{ZONE}":
                return 0, ["v=DMARC1; p=none; rua=mailto:x@beispiel.de;"]
            return zone_gesund(name, typ)
        AUFLOESER = zone_p_none
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("C4", {}).get("gewicht") == "hinweis",
                  f"p=none mit DKIM erwartet Hinweis: {rg.get('C4')}")

        # 5. Zwei SPF-Einträge → permerror-Fund
        def zone_doppelt(name: str, typ: str) -> tuple[int, list[str]]:
            if name == ZONE and typ == "TXT":
                return 0, ["v=spf1 include:_spf.mx.cloudflare.net ~all",
                           "v=spf1 ip4:198.51.100.7 ~all"]
            return zone_gesund(name, typ)
        AUFLOESER = zone_doppelt
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("C1", {}).get("gewicht") == "fund",
                  f"zwei SPF-Einträge gelten nicht als permerror: {rg.get('C1')}")

        # 6. DNS tot → „nicht messbar“, nie grün (repo-Ebene S* darf ok sein)
        def zone_tot(name: str, typ: str) -> tuple[int, list[str]]:
            return -1, ["dns.google: URLError"]
        AUFLOESER = zone_tot
        funde6 = pruefe(tmp, mit_netz=True)["funde"]
        pruefe_es(any(r["regel"] == "C0" and r["gewicht"] == "nicht messbar"
                      for r in funde6),
                  f"DNS-Ausfall meldet nicht „nicht messbar“: {funde6[:2]}")
        pruefe_es(not any(r["gewicht"] == "ok" for r in funde6
                          if r["ebene"] in ("cloudflare", "resend", "worker")),
                  "ohne Messung gibt es Grün in einer Netz-Ebene – verboten")

        # 7. Worker: Domain ohne Auflösung → Fund
        def zone_worker_nxdomain(name: str, typ: str) -> tuple[int, list[str]]:
            if name == "abos." + ZONE:
                return 3, []
            return zone_gesund(name, typ)
        AUFLOESER = zone_worker_nxdomain
        os.environ["NEWSLETTER_WORKER_BASE"] = f"https://abos.{ZONE}"
        os.environ["NEWSLETTER_WORKER_EXPORT_KEY"] = "key"
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("C7", {}).get("gewicht") == "fund",
                  f"NXDOMAIN am Worker erwartet Fund: {rg.get('C7')}")

        # 8. Worker: 5xx am Endpunkt → Fund (DNS ist wieder gesund)
        def zone_worker_live(name: str, typ: str) -> tuple[int, list[str]]:
            if name == "abos." + ZONE:
                return 0, ["abos-worker-xyz.example.workers.dev."]
            return zone_gesund(name, typ)
        AUFLOESER = zone_worker_live

        def netz_worker_500(url: str, *, headers=None, timeout=15):
            if url.startswith("https://api.resend.com"):
                return 200, json.dumps({"data": []})
            if url.rstrip("/").endswith("/export/abonnenten"):
                return 200, json.dumps({"anzahl": 0, "abonnenten": []})
            return 502, "bad gateway"
        NETZ_RUF = netz_worker_500
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("C7", {}).get("gewicht") == "fund",
                  f"502 am Worker erwartet Fund: {rg.get('C7')}")
        pruefe_es(rg.get("B2", {}).get("gewicht") == "info",
                  f"0 Abonnenten erwartet info: {rg.get('B2')}")

        # 9. Worker: 403 mit 1010 → Kanten-Fund (kein Worker-Fehler)
        def netz_kante(url: str, *, headers=None, timeout=15):
            if url.startswith("https://api.resend.com"):
                return 200, json.dumps({"data": []})
            return 403, ("{\"errors\":[{\"code\":\"1010\",\"message\":\"Access denied; "
                         "the site owner has blocked access based on your browser "
                         "signature\"}]}")
        NETZ_RUF = netz_kante
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es("Signaturfilter" in rg.get("C7", {}).get("titel", ""),
                  f"1010-Marker erkannt als Kanten-Block: {rg.get('C7')}")

        # 9b. Taktgeber (C8): frisch = ok · alte Version ohne takt = Fund ·
        #     403 = Fund mit PAT-Klickweg · verpasster Termin = Fund ·
        #     nie gefeuert = Hinweis · kein JSON = nicht messbar
        NETZ_RUF = netz_gesund
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("C8", {}).get("gewicht") == "ok",
                  f"frischer Takt erwartet ok: {rg.get('C8')}")
        alt = pruefe_taktgeber(json.dumps({"ok": True, "kv": "ok"}))
        pruefe_es(alt["gewicht"] == "fund" and "fehlt" in alt["titel"],
                  f"Worker ohne takt erwartet Fund: {alt}")
        kaputt = pruefe_taktgeber(json.dumps(health_gesund(status="fehlgeschlagen",
                                                           http=403, warum="HTTP 403")))
        pruefe_es(kaputt["gewicht"] == "fund" and "Actions: Read and write" in kaputt["soll"],
                  f"403 erwartet Fund mit PAT-Weg: {kaputt}")
        spaeter = _dt.datetime(2026, 9, 25, 9, 0, tzinfo=_dt.timezone.utc)
        verpasst = pruefe_taktgeber(json.dumps(health_gesund(ts="2026-09-22T04:30:05+00:00")),
                                    spaeter)
        pruefe_es(verpasst["gewicht"] == "fund" and "verpasst" in verpasst["titel"],
                  f"Dispatch vom Dienstag am Freitag 09:00 erwartet Fund: {verpasst}")
        rechtzeitig = pruefe_taktgeber(json.dumps(health_gesund(ts="2026-09-25T04:30:05+00:00")),
                                       spaeter)
        pruefe_es(rechtzeitig["gewicht"] == "ok", f"Takt von heute erwartet ok: {rechtzeitig}")
        vor_termin = pruefe_taktgeber(json.dumps(health_gesund(ts="2026-09-22T04:30:05+00:00")),
                                      _dt.datetime(2026, 9, 25, 4, 35, tzinfo=_dt.timezone.utc))
        pruefe_es(vor_termin["gewicht"] == "ok",
                  f"5 min nach dem Termin ist noch der Vortermin maßgeblich: {vor_termin}")
        nie = health_gesund()
        nie["takt"]["letzte"] = {}
        nie_r = pruefe_taktgeber(json.dumps(nie))
        pruefe_es(nie_r["gewicht"] == "hinweis", f"nie gefeuert erwartet Hinweis: {nie_r}")
        pruefe_es(pruefe_taktgeber("<html>")["gewicht"] == "nicht messbar",
                  "kein JSON erwartet nicht messbar")
        pruefe_es(letzter_faelliger_takt(_dt.datetime(2026, 9, 25, 4, 35, tzinfo=_dt.timezone.utc))
                  == _dt.datetime(2026, 9, 22, 4, 30, tzinfo=_dt.timezone.utc),
                  "fälliger Takt: 04:35 Fr → noch Dienstag (10 min Gnade)")
        pruefe_es(letzter_faelliger_takt(_dt.datetime(2026, 9, 25, 4, 41, tzinfo=_dt.timezone.utc))
                  == _dt.datetime(2026, 9, 25, 4, 30, tzinfo=_dt.timezone.utc),
                  "fälliger Takt: 04:41 Fr → Freitag")

        # 10. Resend mit Key: Domain unverifiziert → B1 Fund; Liste 150 → B3 Hinweis
        os.environ["RESEND_API_KEY"] = "re_test"
        def netz_resend(url: str, *, headers=None, timeout=15):
            if url.startswith("https://api.resend.com"):
                return 200, json.dumps({"data": [{"domain": ZONE, "verified": False}]})
            if url.rstrip("/").endswith("/export/abonnenten"):
                return 200, json.dumps({"anzahl": 150, "abonnenten": []})
            return 200, "<html>Formular</html>"
        NETZ_RUF = netz_resend
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("B0", {}).get("gewicht") == "ok",
                  f"200 mit Key erwartet ok: {rg.get('B0')}")
        pruefe_es(rg.get("B1", {}).get("gewicht") == "fund",
                  f"unverifizierte Domain erwartet Fund: {rg.get('B1')}")
        pruefe_es(rg.get("B3", {}).get("gewicht") == "hinweis",
                  f"150 > 100 erwartet Hinweis: {rg.get('B3')}")

        # 10b. Verifiziert + alle Records verifiziert → B1 ok (Zusatzbeleg haelt)
        def netz_resend_records(url: str, *, headers=None, timeout=15,
                                unverified: str = ""):
            if url.startswith("https://api.resend.com/domains/"):
                recs = [
                    {"record": "SPF", "name": "send", "type": "CNAME",
                     "status": "verified"},
                    {"record": "DKIM", "name": "resend._domainkey", "type": "TXT",
                     "status": "verified"},
                    {"record": "Tracking", "name": "rsend", "type": "CNAME",
                     "status": "verified"},
                ]
                for r in recs:
                    if r["record"] == unverified:
                        r["status"] = "pending"
                return 200, json.dumps({"records": recs})
            if url.startswith("https://api.resend.com"):
                return 200, json.dumps(
                    {"data": [{"domain": ZONE, "id": "dom_selftest",
                               "verified": True}]})
            if url.rstrip("/").endswith("/export/abonnenten"):
                return 200, json.dumps({"anzahl": 1, "abonnenten": []})
            return 200, "<html>Formular</html>"

        class _netz10b:
            def __init__(self, unverified=""):
                self.unverified = unverified
            def __call__(self, url, *, headers=None, timeout=15):
                return netz_resend_records(url, headers=headers,
                                           timeout=timeout,
                                           unverified=self.unverified)
        NETZ_RUF = _netz10b()
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("B1", {}).get("gewicht") == "ok",
                  f"verifiziert + alle Records ok erwartet ok: {rg.get('B1')}")
        NETZ_RUF = _netz10b(unverified="SPF")
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("B1", {}).get("gewicht") == "fund",
                  f"nicht verifizierter SPF-Record erwartet Fund: {rg.get('B1')}")
        # 10d. Nur der Tracking-Record offen → Hinweis (Tracking ist bewusst aus)
        NETZ_RUF = _netz10b(unverified="Tracking")
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("B1", {}).get("gewicht") == "hinweis",
                  f"offener Tracking-Record erwartet Hinweis: {rg.get('B1')}")

        # 10e. B1 in der API-Form von 2026: `name` + `status` (die alte
        #      Form `domain`/`verified` bleibt lesbar). Ohne das las die
        #      Wache überall `None` und meldete am 25.09.2026 einen
        #      Falsch-Fund („Sende-Domain fehlt · Konto-Domänen: None“).
        def netz_resend_api_form(url: str, *, headers=None, timeout=15,
                                 daten=None, status=200):
            if url.startswith("https://api.resend.com/domains/"):
                return 200, json.dumps({"records": [
                    {"record": "SPF", "name": "send", "type": "CNAME",
                     "status": "verified"},
                    {"record": "DKIM", "name": "resend._domainkey",
                     "type": "TXT", "status": "verified"}]})
            if url.startswith("https://api.resend.com"):
                return status, json.dumps(daten if daten is not None else {})
            if url.rstrip("/").endswith("/export/abonnenten"):
                return 200, json.dumps({"anzahl": 0, "abonnenten": []})
            return 200, "<html>Formular</html>"

        class _netzApiForm:
            def __init__(self, daten, status=200):
                self.daten, self.status = daten, status
                self.headers: dict = {}
            def __call__(self, url, *, headers=None, timeout=15):
                if url.startswith("https://api.resend.com"):
                    self.headers = dict(headers or {})
                return netz_resend_api_form(url, headers=headers,
                                            timeout=timeout,
                                            daten=self.daten, status=self.status)

        stub_api = _netzApiForm({"object": "list", "has_more": False,
                                 "data": [{"id": "dom_1", "name": ZONE,
                                           "status": "verified"}]})
        NETZ_RUF = stub_api
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("B1", {}).get("gewicht") == "ok",
                  f"API-Form name/status=verified erwartet ok: {rg.get('B1')}")
        # B0 fragt mit der Signatur des Versands (User-Agent aus dem Mailer):
        # die Wache und der Versand müssen denselben Weg messen.
        pruefe_es(stub_api.headers.get("User-Agent")
                  == _mailer.UA_KENNUNG if _mailer else False,
                  f"B0 fragt nicht mit der Sendesignatur: {stub_api.headers}")
        NETZ_RUF = _netzApiForm({"data": [{"name": "andere.example",
                                           "status": "verified"}]})
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("B1", {}).get("gewicht") == "fund"
                  and "andere.example" in rg["B1"]["ist"]
                  and "None" not in rg["B1"]["ist"],
                  f"fremde Domain erwartet Fund mit Namen: {rg.get('B1')}")
        NETZ_RUF = _netzApiForm({"data": "quatsch"})
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("B1", {}).get("gewicht") == "nicht messbar",
                  f"unlesbare Domänenliste erwartet nicht messbar: {rg.get('B1')}")
        NETZ_RUF = _netzApiForm({"data": [{"name": ZONE, "status": "not_started"}]})
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("B1", {}).get("gewicht") == "fund"
                  and "not_started" in rg["B1"]["ist"],
                  f"not_started erwartet Fund mit Status: {rg.get('B1')}")

        # 10f. Die Abfrage-URL: genau EIN „?“ – der 400er, der am
        #      25.09.2026 als „DNS nicht erreichbar“ gelesen wurde.
        probe_url = doh_url("https://dns.google/resolve", ZONE, "TXT",
                            {"dnssec": "false"})
        pruefe_es(probe_url.count("?") == 1 and ZONE in probe_url,
                  f"DoH-URL falsch gebaut: {probe_url}")
        pruefe_es(all("?" not in basis for basis, _x in DOH_ENDPUNKTE),
                  f"DoH-Basis trägt eine Abfrage: {DOH_ENDPUNKTE}")
        pruefe_es("4xx" in messluecke(["dns.google: HTTP 400",
                                       "cloudflare-dns.com: HTTP 400"]),
                  "HTTP-400-Messlücke wird nicht als Abfragefehler benannt")

        # 11. Worker-Export mit falschem Key → B2 Fund
        os.environ["NEWSLETTER_WORKER_EXPORT_KEY"] = "falsch"
        def netz_403_export(url: str, *, headers=None, timeout=15):
            if url.startswith("https://api.resend.com"):
                return 200, json.dumps({"data": [{"domain": ZONE, "verified": True}]})
            if url.rstrip("/").endswith("/export/abonnenten"):
                return 403, '{"error":"unauthorized"}'
            return 200, "<html>Formular</html>"
        NETZ_RUF = netz_403_export
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("B2", {}).get("gewicht") == "fund",
                  f"403 am Export erwartet Fund: {rg.get('B2')}")

        # 12. State: Halt → S1 Fund
        AUFLOESER = zone_gesund
        NETZ_RUF = netz_gesund
        os.environ.pop("RESEND_API_KEY", None)
        with open(os.path.join(tmp, "data", "newsletter_state.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"versand_unklar": {"kennung": "liste:2026-09-24:Test",
                                          "zeitpunkt": "2026-09-24T12:00:00+00:00"}}, fh)
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("S1", {}).get("gewicht") == "fund",
                  f"versand_unklar erwartet Fund: {rg.get('S1')}")
        pruefe_es("kennung" in rg.get("S1", {}).get("ist", "") or
                  "liste:2026-09-24" in rg.get("S1", {}).get("ist", ""),
                  f"S1 trägt die Kennung: {rg.get('S1')}")
    finally:
        AUFLOESER, NETZ_RUF = echt_aufloeser, echt_netz
        if zonen_umgebung:
            os.environ["NEWSLETTER_MAILZONE"] = zonen_umgebung
        else:
            os.environ.pop("NEWSLETTER_MAILZONE", None)
        os.environ.pop("NEWSLETTER_WORKER_BASE", None)
        os.environ.pop("NEWSLETTER_WORKER_EXPORT_KEY", None)
        os.environ.pop("RESEND_API_KEY", None)

    if fehler:
        for m in fehler:
            print(f"❌ Zustellbarkeit-Selftest: {m}")
        return 2
    print(f"✅ Zustellbarkeits-Selftest: {zaehler} Fälle grün "
          "(SPF/DMARC/DKIM, Kanten-Block, Worker, Resend, Plan, State).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Newsletter-Zustellbarkeits-Wache "
                                             "(Cloudflare-DNS + Resend + Worker)")
    ap.add_argument("--root", default=BLOG_DIR)
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ohne-netz", action="store_true",
                    help="nur den Repo-Status prüfen (keine DNS/HTTP-Messung)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.pruefen:
        ap.print_help()
        return 2
    erg = pruefe(os.path.abspath(args.root), mit_netz=not args.ohne_netz)
    if args.json:
        print(json.dumps(erg, ensure_ascii=False, indent=2))
    else:
        print(als_md(erg))
    return erg["rc"]


if __name__ == "__main__":
    sys.exit(main())
