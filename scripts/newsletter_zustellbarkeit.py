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

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONE_Standard = "franksfinanzcheck.de"
PRÜFER_KENNUNG = "FranksFinanzcheck-Zustellbarkeitswaechter/1.0"
DOH_ENDPUNKTE = ("https://dns.google/resolve?dnssec=false&",
                 "https://cloudflare-dns.com/dns-query?")
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


def _doh(name: str, typ: str) -> tuple[int, list[str]]:
    """Eine DNS-Frage, mehrere Resolver. → (RCode, Antworten).

    RCode 3 (NXDOMAIN) ist eine AUSSAGE („den Eintrag gibt es nicht"), ein
    Netzwerkfehler ist das nicht – die Wache darf eine Blockade nicht als
    fehlenden Eintrag melden und umgekehrt.
    """
    frage = f"?name={urllib.parse.quote(name)}&type={typ}"
    letzte_fehler: list[str] = []
    for grund in DOH_ENDPUNKTE:
        try:
            anfrage = urllib.request.Request(
                grund + frage, method="GET",
                headers={"accept": "application/dns-json",
                         "User-Agent": PRÜFER_KENNUNG})
            with urllib.request.urlopen(anfrage, timeout=DOH_ZEITLIMIT) as antwort:
                dat = json.loads(antwort.read().decode("utf-8", "replace"))
            code = int(dat.get("Status", -1))
            zeilen = [a.get("data", "") for a in (dat.get("Answer") or [])]
            if typ == "TXT":
                zeilen = [_txt_fetzen(z) for z in zeilen]
            return code, [z.strip() for z in zeilen if z and z.strip()]
        except Exception as exc:  # noqa: BLE001  (DNS, TLS, Timeout, Sperre …)
            letzte_fehler.append(f"{urllib.parse.urlsplit(grund).netloc}: "
                                 f"{exc.__class__.__name__}")
    return -1, ["; ".join(letzte_fehler)]


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


def kanten_block(code: int, antwort: str) -> bool:
    """403 der Cloudflare-KANTE (nicht des Anbieters): Signaturfilter-Marke.

    Genau diese Antwort trägt `Error 1010` / „browser's signature" – der
    Anbieter hat die Anfrage nie gesehen.
    """
    if code != 403:
        return False
    m = re.search(r'(1010|browser.?s signature|Access denied[^"]*signature|Just a moment)',
                  antwort or "", re.I)
    return bool(m)


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
                        "; ".join(txts)[:200] or "keine Antwort der Resolver",
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

    # C2 – Resend-Send-Subdomain (SES-Modell: SPF-TXT + Bounce-MX auf `send.`;
    # an der Apex-SPF ändert sich NICHTS). Der MX-Wert ist Region-spezifisch
    # (Konto-Region) → Existenz + Form messen, nicht einen festen Host.
    send_txt_s, send_txt = dns(RESEND_SEND_SUBDOMAINE + "." + z, "TXT")
    send_mx_s, send_mx = dns(RESEND_SEND_SUBDOMAINE + "." + z, "MX")
    send_spf = [t for t in send_txt if t.strip().lower().startswith("v=spf1")]
    send_mx_ok = [m for m in send_mx if RESEND_SES_MX.search(m)]
    if send_spf and send_mx_ok:
        funde.append(_regel("C2", "cloudflare", "ok",
                            "Resend-Send-Subdomain-Einträge vorhanden",
                            "TXT send: " + send_spf[0][:80] + " · MX send: "
                            + send_mx_ok[0][:60], "—", "—", ""))
    else:
        fehlt = []
        if not send_spf:
            fehlt.append("TXT `send` (SPF, so wie Resend zeigt: "
                         "`v=spf1 include:amazonses.com ~all`)")
        if not send_mx_ok:
            fehlt.append("MX `send` (Bounce, so wie Resend zeigt: "
                         "`feedback-smtp.<region>.amazonses.com`, Priorität 10)")
        gewicht = ("nicht messbar"
                   if "nicht messbar" in (send_txt_s, send_mx_s) else "fund")
        funde.append(_regel("C2", "cloudflare", gewicht,
                            "Resend-Send-Subdomain-Einträge fehlen oder unvollständig",
                            "TXT send: " + (", ".join(send_txt)[:80] or send_txt_s)
                            + " · MX send: " + (", ".join(send_mx)[:60] or send_mx_s),
                            "anlegen: " + " und ".join(fehlt),
                            "Resend → Domains → " + z + " → die beiden SPF-Records "
                            "(TXT + MX, Name `send`) exakt kopieren; Cloudflare → DNS "
                            "→ Records → hinzufügen",
                            "Resend authentifiziert über die send.-Subdomain (AWS SES): "
                            "ohne TXT ist die Mail SPF-ungeprüft, ohne MX landen "
                            "Rückläufer nirgends. Apex-SPF: bewusst unverändert."))

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
        gewicht = "fund" if dkim_da else "hinweis"
        funde.append(_regel("C4", "cloudflare", gewicht, "kein DMARC-Eintrag",
                            f"_dmarc.{z}: {ms}",
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

    # C5 – MX auf der Zone (Reply-to muss ankommen)
    mst, mx = dns(z, "MX")
    if mst == "gemessen" and mx:
        funde.append(_regel("C5", "cloudflare", "ok", "MX vorhanden",
                            ", ".join(mx)[:120], "—", "—", ""))
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
            funde.append(_regel("C6", "cloudflare", "hinweis",
                                f"Absender-Domain {abs_domain} ohne MX",
                                f"MX {abs_domain}: {ast}",
                                "Reply-To auf eine Domain mit MX zeigen, oder Routing "
                                "einrichten",
                                "Zone-Interface der Absender-Domain (hier: "
                                "Cloudflare → Email)",
                                "Nur ein Wegweiser: der Versand läuft trotzdem, aber "
                                "Antworten der Leser gehen verloren."))

    messwerte["mx"] = (mst, mx)
    return funde, messwerte


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
                       "; ".join(antworten)[:200] or "keine Antwort",
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
                       "—", "—", "")]
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


def _pruefe_resend_api(root: str) -> list[dict]:
    """B0 (Netzweg, OHNE Key prüfbar: 401 = Kante durchlässig) + B1 (Domain
    verifiziert, nur mit Key)."""
    out: list[dict] = []
    key = os.environ.get("RESEND_API_KEY", "").strip() or \
        os.environ.get("NEWSLETTER_RESEND_KEY", "").strip()
    headers = {"Authorization": f"Bearer {key}"} if key else {}
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
    out.append(_regel("B0", "resend", "ok", "Netzweg zur Resend-API frei",
                      f"HTTP {code} von api.resend.com", "—", "—", ""))
    z = zone(root)
    try:
        daten = json.loads(antwort)
    except json.JSONDecodeError:
        daten = {}
    domänen = daten.get("data") or []
    own = next((d for d in domänen if str(d.get("domain", "")).lower() == z), None)
    if own is None:
        out.append(_regel("B1", "resend", "fund",
                          f"Sende-Domain {z} fehlt im Resend-Konto",
                          "Konto-Domänen: "
                          + (", ".join(str(d.get("domain")) for d in domänen) or "keine"),
                          "Domain in Resend hinzufügen (Sending Domains → Add Domain) "
                          "und die DNS-Einträge (C2/C3) abschliessen",
                          "Resend → Sending Domains → Add Domain",
                          "Ohne registrierte Domain nimmt Resend keine Mail der Zone an "
                          "– der Versand bricht in derselben Vorprüfung ab, die hier "
                          "gemessen wurde."))
    elif not own.get("verified"):
        out.append(_regel("B1", "resend", "fund",
                          f"Sende-Domain {z} nicht verifiziert",
                          "Domain vorhanden, `verified: false`",
                          "DNS-Einträge aus dem Resend-Dashboard vollständig anlegen "
                          "(SPF-TXT + MX auf `send.`, DKIM `resend._domainkey`)",
                          "Resend → Sending Domains → die Checkliste der Domain",
                          "Verifizierung = SPF+DKIM live. Solange sie fehlt, sendet "
                          "Resend nicht."))
    else:
        out.append(_regel("B1", "resend", "ok", f"Domain {z} verifiziert",
                          "verified: true", "—", "—", ""))
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
                          "nächster Di/Fr-Cron 05:05 UTC holt sie ab",
                          "Actions → Newsletter-Daily → Run workflow (`tage` 3 für "
                          "einen Nachlauf)", ""))
    letzte = state.get("letzte_ausgabe") or {}
    if letzte.get("datum"):
        out.append(_regel("S3", "repo", "ok", "letzter Versand belegt",
                          f"{letzte.get('datum')} · „{letzte.get('betreff', '—')}"[:120] +
                          f"“ · {letzte.get('transport', '—')}", "—", "—", ""))
    else:
        out.append(_regel("S3", "repo", "hinweis",
                          "noch kein Versand protokolliert",
                          "data/newsletter_state.json trägt keine letzte_ausgabe",
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
            f"send.{ZONE}": {"TXT": [0, ["v=spf1 include:amazonses.com ~all"]],
                             "MX": [0, ["10 feedback-smtp.us-east-1.amazonses.com"]]},
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
        return 200, "<html>Formular</html>"

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

        # 2b. Bounce-MX auf send. fehlt (SPF-TXT vorhanden) → C2 Fund
        def zone_ohne_bounce(name: str, typ: str) -> tuple[int, list[str]]:
            if name == f"send.{ZONE}" and typ == "MX":
                return 3, []
            return zone_gesund(name, typ)
        AUFLOESER = zone_ohne_bounce
        rg = {r["regel"]: r for r in pruefe(tmp, mit_netz=True)["funde"]}
        pruefe_es(rg.get("C2", {}).get("gewicht") == "fund",
                  f"fehlendes Bounce-MX meldet nicht Fund: {rg.get('C2')}")

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
