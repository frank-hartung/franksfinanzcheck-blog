#!/usr/bin/env python3
"""newsletter_zustellbarkeit.py – die Zustellbarkeits-Wache: Cloudflare-DNS + Brevo-Konto.

WARUM (23.09.2026, Newsletter-Daily Läufe #14 und #21):
Der Versand war im Repo dreifach verriegelt, die Kette *vor* der Verriegelung
aber ungeprüft. Zwei Vorfälle an einem Tag zeigen, was fehlt:

  * Lauf #21 scheiterte mit „HTTP 403 … Error 1010: Access denied / The site
    owner has blocked access based on your browser's signature". Das war nicht
    Brevos Authentifizierung und nicht der Absender – es war die Cloudflare-Kante
    VOR api.brevo.com, die die Standardkennung der Python-Bibliothek
    („Python-urllib/3.11") filtert, bevor die Anfrage den Anbieter erreicht.
    Ein Lauf, der das nicht von einer echten Konto-Absage unterscheiden kann,
    meldet wochenlang „Absender-Problem“, wo ein Client-Problem vorliegt.
  * Die Freischalt-Checkliste schrieb vor, SPF um `include:spf.brevo.com` zu
    erweitern, und ließ den Absender damit als nächstes Hindernis aussehen. Die
    gemessene Zone (23.09.2026) sagt etwas anderes: DKIM **ist** veröffentlicht
    (`brevo1`/`brevo2._domainkey` → `b1.`/`b2.franksfinanzcheck-de.dkim.brevo.com`),
    `brevo-code`-TXT ist ebenfalls gesetzt, DMARC steht auf `p=reject; adkim=s; aspf=s`. Der
    SPF-Wert der Checkliste hätte an der Zustellung also nichts geändert –
    SPF alignt auf Brevos geteiltem Weg nie, die Zustellung trägt das DKIM.
    Was die Zone WIRKLICH riskiert, ist die Reihenfolge: `p=reject` ist eine
    Anweisung an Gmail und Yahoo, alles Hart-abzuweisen, was nicht alignt. Ein
    einziger DKIM-Ausfall (Schlüssel-Rotation, ein Absender auf fremder Domain)
    macht aus „landet im Spam“ damit „kommt nie an“, und ohne `rua`-Auswertung
    fällt das erst auf, wenn ein Leser sich beschwert.

Diese Unterscheidung – Kante vs. Anbieter, DKIM vs. SPF, Messlücke vs. Befund –
ist der Grund für diese Wache. Sie misst beide Seiten und sagt zu jedem Befund
den exakten nächsten Schritt im jeweiligen Interface.

Diese Wache prüft deshalb die beiden Seiten, die kein CI-Job der Welt sonst sieht:

  CLOUDFLARE (DNS-Zone, per DNS-über-HTTPS gemessen, nie geraten):
    C0  Messlücke: welche Abfrage war nicht möglich – gemeldet, nie als Grün
    C1  SPF: genau ein Eintrag (zwei = permanenter Fehler), Cloudflare-Routing
        enthalten, Mechanik erklärt
    C2  Brevo in SPF: fehlt → Hinweis mit der wahren Begründung (kein
        Alignment-Gewinn auf geteilter IP; nur mit Dedicated IP/eigenem
        Return-Path nötig) – kein Blind-Reparieren der Checkliste
    C3  DKIM: Domain-Authentifizierung bei Brevo (TXT `mail._domainkey` ODER
        CNAMEs `brevo1`/`brevo2._domainkey`, oder `default._domainkey`)
    C4  `brevo-code`-TXT: Eigentumsnachweis des Kontos
    C5  DMARC: vorhanden? Policy nicht strenger als die Echtheitsnachweise?
        Berichtsweg? aspf/adkim zur realen Sendestrecke? (C5b–C5e die Teilstufen)
    C6  MX/Routing: Reply-To-Domain muss eingehende Mail annehmen
    C7  Absender-Postfach: eigene Routing-Regel für die Absender-Adresse
        (empfohlen, kein Zwang)
  BREVO (API, nur wenn ein Key da ist – sonst „nicht gemessen“):
    B0  Netzweg: kommt die Kante durch? (401/404-Versatz von Brevo = durchlässig;
        403 mit Signaturfilter-Marke = Blockage; 0 = DNS/TLS)
    B1  Absender existiert und ist verifiziert
    B2  Liste existiert, Abonnentenstand
    B3  Plan-Grenze gegen Listenstärke (Free = 300 Mails/Tag → ein Werktag
        erreicht nicht alle)
    B4  Themen-Chips: landet das Feld bei Brevo an (Attribut/Interest)?
  REPO-STATUS (data/newsletter_state.json, ohne Netz):
    S1  Versand-Halt nach unklarem Sendeausgang (blockiert den Listen-Versand)
    S2  Artikel, die auf den Versand warten
    S3  Versandnachweis (`zuletzt_versandt`/`kampagne_id`) vorhanden?

Grundsätze, so wie im Rest des Repos:
  * **Nachmessen statt nachschlagen.** Jede Zeile nennt Ist-Wert, Soll-Wert und
    den exakten Klickweg ins Cloudflare- bzw. Brevo-UI. Kein Befund ohne
    nächsten Schritt.
  * **Ohne Messung kein Grün.** Ist ein Record nicht abrufbar (Offline-Selbsttest,
    Netzsperre, DoH-Ausfall), steht bei ihm „nicht gemessen“ – nicht „in Ordnung“,
    und nie „fehlt“: die erreichbaren Schichten werden weiter bewertet, damit ein
    wackelnder Endpunkt keine Schreibaktion in einer laufenden Zone auslöst.
    `--strict` macht aus einer Lücke einen Fehler (Freigabe-Gate), der
    Standardlauf meldet sie nur laut.
  * **Reparieren tut ein Mensch, nicht dieses Skript.** DNS-Einträge und
    Konto-Einstellungen sind Betreiber-Entscheidungen; die Wache schreibt nichts
    an Brevo und sonst nirgends hin (nur GET, nie POST/PUT/DELETE).

Nutzung:
    python3 scripts/newsletter_zustellbarkeit.py --pruefen
    python3 scripts/newsletter_zustellbarkeit.py --pruefen --strict --md
    python3 scripts/newsletter_zustellbarkeit.py --pruefen --ohne-netz
    python3 scripts/newsletter_zustellbarkeit.py --json
    python3 scripts/newsletter_zustellbarkeit.py --selftest

Exit: 0 = keine Funde · 1 = Fund (Zustellung gefährdet) · 2 = Selbsttest rot
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
if os.path.join(BLOG_DIR, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

ZONE_Standard = "franksfinanzcheck.de"
# DNS-über-HTTPS-Endpunkte (Reihenfolge = Versuch). Alle drei antworten mit dem
#selben JSON-Format (`Answer[].data`); mehrere Anbieter, weil ein einzelner
# Ausfall sonst als „Zone kaputt“ missverstanden würde.
DOH_ENDPUNKTE = ("https://dns.google/resolve",
                 "https://cloudflare-dns.com/dns-query",
                 "https://dns.quad9.net/dns-query")
DOH_ZEITLIMIT = 12
# Kennung des Prüfers. „compatible; …Bot…“ ist die korrekte Selbstauskunft
# eines automatisierten Clients – kein vorgetäuschter Browser (der würde der
# Kante etwas vorspielen, statt sich zu melden).
PRÜFER_KENNUNG = ("Mozilla/5.0 (compatible; FranksFinanzcheckZustellbarkeit/1.0; "
                  "+https://franksfinanzcheck.de/newsletter/)")

# Selector-Kandidaten für Brevos Domain-Authentifizierung. Brevo zeigt im
# Konto, welche Variante das eigene Account benutzt (TXT an mail._domainkey
# oder die zwei CNAMEs brevo1/brevo2) – deshalb hier die Menge, nicht eine
# Vermutung. Wer einen eigenen Selector sieht: BREVO_DKIM_SELECTOR setzen.
DKIM_TXT_SELECTOR = ("mail", "default", "s1", "k1", "dkim")
DKIM_CNAME_SELECTOR = ("brevo1", "brevo2")
CLOUDFLARE_MX_MARKEN = ("mx.cloudflare.net", "route1.mx.cloudflare.net",
                        "route2.mx.cloudflare.net", "route3.mx.cloudflare.net")
BREVO_SPF_INCLUDE = ("spf.brevo.com", "spf.sendinblue.com")
PLAN_FREI_TAGESGRENZE = 300          # Brevo Free: 300 Mails/Tag – Werktagsversand


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
    frage = (f"?name={urllib.parse.quote(name)}&type={typ}")
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


# --------------------------------------------------------------------- Einstellungen
def zone(root: str) -> str:
    """Die zu prüfende Zone – aus der Variable, sonst die Domain der Impressum-URL."""
    gesetzt = os.environ.get("NEWSLETTER_MAILZONE", "").strip().lower()
    if gesetzt:
        return gesetzt.lstrip(".")
    toml = _read(os.path.join(root, "hugo.toml"))
    m = re.search(r'(?m)^\s*baseURL\s*=\s*"https?://([^/\"]+)', toml)
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


# ------------------------------------------------------------------------ Regeln C*
def _regel(nummer: str, ebene: str, gewicht: str, titel: str, ist: str, soll: str,
           weg: str, grund: str) -> dict:
    return {"regel": nummer, "ebene": ebene, "gewicht": gewicht, "titel": titel,
            "ist": ist, "soll": soll, "weg": weg, "grund": grund}


def pruefe_cloudflare(root: str) -> tuple[list[dict], dict]:
    """Alles, was in der DNS-Zone steht und die Zustellung entscheidet."""
    funde: list[dict] = []
    z = zone(root)
    abs_ = absender(root)
    messwerte: dict = {"zone": z}

    code_mx, mx = dns(z, "MX")
    code_txt, txt = dns(z, "TXT")
    code_dmarc, dmarc = dns(f"_dmarc.{z}", "TXT")
    fragen = (("MX @", code_mx), ("TXT @", code_txt), ("TXT _dmarc", code_dmarc))
    blind = [n for n, c in fragen if c == "nicht messbar"]
    frei = [n for n, c in fragen if c != "nicht messbar"]
    messwerte.update({"mx": mx, "txt": txt, "dmarc": dmarc,
                      "absturz": bool(blind), "blinden": blind})
    txt_gemessen = code_txt == "gemessen"

    # C0 – Messlücke, aber EHRLICH: was nicht zu sehen war, wird als Lücke
    # gemeldet, und die übrigen Regeln laufen trotzdem weiter. Eine ganze
    # Prüfung schweigen zu lassen (der frühere Zustand) hätte aus einem
    # wackelnden DoH-Endpunkt ein pauschales „nichts geprüft" gemacht – und
    # genau die Zone, die erreichbar war, ohne Befund durchgewinkt.
    if blind:
        funde.append(_regel(
            "C0", "cloudflare", "nicht messbar",
            "DNS-Abfrage teilweise nicht möglich: " + ", ".join(blind),
            "erreichbar: " + (", ".join(frei) or "keine Abfrage") +
            " · blind: " + ", ".join(blind) + " · Endpunkte: " +
            ", ".join(urllib.parse.urlsplit(g).netloc for g in DOH_ENDPUNKTE),
            "Ausgang/Zeitlimit der Laufumgebung prüfen; sonst lokal nachmessen: "
            "`dig TXT " + z + "` und `dig TXT _dmarc." + z + "`",
            "—",
            "Was nicht gemessen wurde, zählt nicht als „in Ordnung“ – gemeldet "
            "wird die Lücke, aber kein Ergebnis, das die Wache nicht hat."))

    # C1/C2 – SPF
    mx_zeilen = mx if code_mx == "gemessen" else []
    spf = [t for t in (txt if txt_gemessen else []) if t.lower().startswith("v=spf1")]
    if not txt_gemessen:
        funde.append(_regel("C1", "cloudflare", "nicht gemessen",
                            "SPF-Lage nicht gemessen",
                            "der TXT-Eintrag der Zone war nicht abfragbar",
                            "Abfrage wiederholen (ohne --ohne-netz) oder lokal per dig",
                            "—", "Ein nicht gelesener SPF ist kein fehlender SPF."))
    elif len(spf) == 0:
        funde.append(_regel("C1", "cloudflare", "fund",
                            "kein SPF-Eintrag in der Zone",
                            f"TXT @{z}: kein `v=spf1`-Eintrag gefunden",
                            "ein TXT-Eintrag @: `v=spf1 include:_spf.mx.cloudflare.net ~all`",
                            "Cloudflare → Zone → DNS → Records → Add → TXT (Name @, "
                            "Content wie oben)",
                            "Ohne SPF lehnt jeder Empfänger die weitergeleitete Post "
                            "(kontakt@) und die eigene Domain-Post als Fälschung ab."))
    elif len(spf) > 1:
        funde.append(_regel("C1", "cloudflare", "fund",
                            "mehrere SPF-Einträge = permanenter Prüffehler",
                            f"{len(spf)} TXT-Einträge mit `v=spf1`: " + " | ".join(spf),
                            "genau EIN SPF-Eintrag; alle Anbieter in dieser Zeile",
                            "Cloudflare → DNS → Records: die überzähligen `v=spf1`-"
                            "TXT-Einträge löschen, einen zusammengeführten setzen",
                            "RFC 7208: zwei SPF-Records werden nicht zusammengeführt, "
                            "sondern als `permerror` gewertet – seit dem Moment "
                            "scheitert jede Mail, auch die vorher grüne."))
    else:
        if "include:_spf.mx.cloudflare.net" not in spf[0]:
            if any(m in (mx_zeilen[0] if mx_zeilen else "") for m in CLOUDFLARE_MX_MARKEN):
                funde.append(_regel("C1", "cloudflare", "fund",
                                    "Cloudflare Email Routing nicht in SPF autorisiert",
                                    spf[0],
                                    "`v=spf1 include:_spf.mx.cloudflare.net ~all` "
                                    "(bestehende Includes beibehalten)",
                                    "Cloudflare → Email → Routing → Overview zeigt den "
                                    "exakten SPF-Wert; in denselben TXT-Eintrag "
                                    "zusammenführen, nicht als zweiten Eintrag",
                                    "Weitergeleitete Mails werden ohne Alignement als "
                                    "Fälschung verworfen."))
        else:
            funde.append(_regel("C1", "cloudflare", "ok", "SPF-Eintrag (einer, Routing enthalten)",
                                spf[0], "—", "—", ""))
    fehlend = [i for i in BREVO_SPF_INCLUDE if i not in " ".join(spf)]
    if txt_gemessen and spf and fehlend:
        funde.append(_regel("C2", "beides", "hinweis",
                            "Brevo nicht in SPF – bewusst, nicht vergessen",
                            "SPF: " + " | ".join(spf),
                            "Nur nötig bei Dedicated IP oder eigenem Return-Path: "
                            "`include:spf.brevo.com` in denselben Eintrag aufnehmen",
                            "Brevo → Senders, Domains & Dedicated IPs → Domains "
                            "(dort steht der für das Konto gültige SPF-/DKIM-Wortlaut)",
                            "Auf Brevos geteiltem Versandweg bleibt der Return-Path beim "
                            "Anbieter; ein Include der eigenen Zone bringt dafür kein "
                            "DMARC-Alignement und ändert an der Zustellung nichts. "
                            "Die Checklisten-Anweisung „unbedingt ergänzen“ war an dieser "
                            "Stelle zu pauschal (korrigiert 23.09.2026)."))

    # C3 – DKIM (Domain-Authentifizierung, der eigentliche Hebel)
    extra = [s.strip().strip(".") for s in
             os.environ.get("BREVO_DKIM_SELECTOR", "").split(",") if s.strip()]
    treffer_txt: list[str] = []
    treffer_cname: list[str] = []
    cname_geprüft: list[str] = []
    txt_geprüft: list[str] = []
    abgefragt = 0
    for sel in (extra + list(DKIM_TXT_SELECTOR)):
        code, ant = dns(f"{sel}._domainkey.{z}", "TXT")
        if code == "nicht messbar":
            continue
        abgefragt += 1
        txt_geprüft.append(sel)
        if ant:
            treffer_txt.append(f"{sel}._domainkey: {ant[0][:70]}")
    if not treffer_txt:
        for sel in DKIM_CNAME_SELECTOR:
            code, ant = dns(f"{sel}._domainkey.{z}", "CNAME")
            if code == "nicht messbar":
                continue
            abgefragt += 1
            cname_geprüft.append(sel)
            if ant:
                treffer_cname.append(f"{sel}._domainkey → {ant[0]}")
    messwerte["dkim"] = treffer_txt + treffer_cname
    if not abgefragt:
        # Kein einziger Selector war abfragbar -> „kein DKIM“ wäre eine
        # Erfindung. Diese Unterscheidung ist der ganze Sinn der Wache.
        funde.append(_regel("C3", "cloudflare", "nicht gemessen",
                            "DKIM-Lage nicht gemessen",
                            "keine der geprüften Selector-Abfragen war erreichbar "
                            f"(TXT: {', '.join(extra + list(DKIM_TXT_SELECTOR))}; "
                            f"CNAME: {', '.join(DKIM_CNAME_SELECTOR)})",
                            "Abfrage wiederholen; lokal: `dig CNAME brevo1._domainkey."
                            + z + "`", "—",
                            "Brevo veröffentlicht Domain-DKIM als zwei CNAMEs, nicht als "
                            "TXT – und eine nicht gestellte Abfrage ist kein fehlender "
                            "Schlüssel. Wer hier einen Fund meldet, erzeugt eine "
                            "Sachbeschädigung an der eigenen Zone."))
    elif treffer_txt or len(treffer_cname) >= 2:
        funde.append(_regel("C3", "cloudflare", "ok",
                            "DKIM-Signaturschlüssel der Domain veröffentlicht",
                            " | ".join((treffer_txt + treffer_cname)[:3])[:240],
                            "—", "—", ""))
    elif treffer_cname:
        # Genau eine der beiden Brevodelegationen war sichtbar. Das ist KEIN
        # „DKIM fehlt“: eine Signatur trägt DMARC, nur die Rotation ist nicht
        # möglich. Wer hier rot meldet, erzeugt aus einem wackelnden DoH-Endpunkt
        # einen DNS-Eingriff in eine laufende Zone.
        lücken = [s for s in DKIM_CNAME_SELECTOR if s not in cname_geprüft]
        funde.append(_regel("C3", "cloudflare", "hinweis",
                            "DKIM nur zur Hälfte sichtbar ("
                            + f"{len(treffer_cname)} von {len(DKIM_CNAME_SELECTOR)} CNAMEs)",
                            " | ".join(treffer_cname)[:240],
                            "beide Delegationen aus dem Brevo-Dialog setzen"
                            + (f" – nicht abfragbar war: {', '.join(lücken)}._domainkey"
                               if lücken else " – die zweite fehlt in der Zone"),
                            "Brevo → Senders, Domains & Dedicated IPs → Domains → "
                            "„Authenticate“ (beide CNAMEs zeigen)",
                            "Eine sichtbare Delegation genügt für das Alignement; die "
                            "zweite hält die Schlüssel-Rotation am Laufen. Als Fund "
                            "wäre das ein Fehlalarm – und Fehlalarme in dieser Zone "
                            "werden von Menschen mit Schreibrecht beantwortet."))
    else:
        funde.append(_regel("C3", "beides", "fund" if txt_geprüft else "nicht gemessen",
                            "kein DKIM für die Domain – Brevo kann nicht im eigenen Namen signieren",
                            (f"geprüfte TXT-Selector: {', '.join(extra + list(DKIM_TXT_SELECTOR))} "
                             f"(keiner gesetzt); CNAMEs: {', '.join(treffer_cname) or 'keine'}"),
                            "die BEIDEN Records aus dem Brevo-Dialog wörtlich "
                            "kopieren: entweder ein TXT an `mail._domainkey` ODER zwei "
                            "CNAMEs `brevo1._domainkey`/`brevo2._domainkey` → "
                            "`b1.`/`b2.<domain>.dkim.brevo.com`",
                            "Brevo → Senders, Domains & Dedicated IPs → Domains → "
                            "„Authenticate“ (Domain wählen, Werte kopieren) → Cloudflare → "
                            "DNS → Records → Add. Nicht tippen, kopieren – ein "
                            "abgeschriebener Schlüssel prüft nie.",
                            "Ohne eigenes DKIM signiert Brevo mit seinem Ersatz-Absender "
                            "(brevosend-Substitut): die Mail trägt dann keinen "
                            "verifizierbaren Beleg der eigenen Domain, DMARC scheitert, "
                            "und Gmail/Yahoo weisen sie bei p=reject hart ab. "
                            "Das ist der wahre Freischalt-Blocker, nicht die API."))

    # C4 – Eigentumsnachweis (dieselbe TXT-Antwort wie C1 – keine Zweitabfrage,
    # die ein anderes Ergebnis liefern könnte als die soeben gemessene)
    brevo_code = [t for t in (txt if txt_gemessen else [])
                  if t.lower().startswith("brevo-code:")]
    if not txt_gemessen:
        funde.append(_regel("C4", "brevo", "nicht gemessen",
                            "Domain-Code nicht gemessen",
                            "TXT @ war nicht abfragbar", "Abfrage wiederholen", "—",
                            "Ohne Antwort weiß die Wache nichts über den "
                            "Eigentumsnachweis – und sagt genau das."))
    elif brevo_code:
        funde.append(_regel("C4", "brevo", "ok", "Domain-Eigentum bei Brevo verifiziert",
                            brevo_code[0][:60], "—", "—", ""))
    else:
        funde.append(_regel("C4", "brevo", "fund",
                            "kein `brevo-code`-TXT – Brevos Domain-Wizard bleibt unvollständig",
                            f"TXT @{z}: kein Eintrag `brevo-code:…`",
                            "den von Brevo angezeigten Wert exakt so eintragen "
                            "(Name @, Typ TXT)",
                            "Brevo → Senders, Domains & Dedicated IPs → Domains → "
                            "„Authenticate domain“ → angezeigten `brevo-code:`-Wert "
                            "kopieren",
                            "Ohne Eigentumsnachweis verifiziert Brevo die Domain nicht; "
                            "Absender auf der Domain bleiben „nicht verifiziert“, und "
                            "die Vorprüfung des Versandlaufs bricht genau dort ab."))

    # C5 – DMARC
    if code_dmarc == "nicht messbar":
        funde.append(_regel("C5", "cloudflare", "nicht gemessen",
                            "DMARC-Lage nicht gemessen",
                            f"TXT _dmarc.{z} war nicht abfragbar",
                            "Abfrage wiederholen; lokal: `dig TXT _dmarc." + z + "`",
                            "—", "Eine Policy, die niemand gelesen hat, ist weder "
                            "scharf noch harmlos."))
    elif not dmarc:
        funde.append(_regel("C5", "cloudflare", "fund",
                            "kein DMARC-Eintrag",
                            f"TXT _dmarc.{z}:" + (' NXDOMAIN' if code_dmarc == 'NXDOMAIN' else ' leer'),
                            "`v=DMARC1; p=none;` (Start) – später p=quarantine, "
                            "p=reject erst mit belegt alignedem DKIM",
                            "Cloudflare → DNS → Records → Add → TXT: Name `_dmarc`, "
                            "Content `v=DMARC1; p=none;`",
                            "Gmail und Yahoo verlangen DMARC für Massenversand; ohne "
                            "Eintrag wird zugestellt, aber ohne jeden Schutz der "
                            "Domain-Identität – und ohne Rückkanal (rua) weiß niemand, "
                            "was schiefläuft."))
    else:
        d = dmarc[0].lower()
        policy = (re.search(r"p\s*=\s*(none|quarantine|reject)", d) or [None, ""])[1]
        adkim = (re.search(r"adkim\s*=\s*(s|r)", d) or [None, "r"])[1]
        aspf = (re.search(r"aspf\s*=\s*(s|r)", d) or [None, "r"])[1]
        pct = re.search(r"pct\s*=\s*(\d+)", d)
        rua = "rua=" in d
        messwerte["dmarc"] = dmarc[0]
        # Sichtbare Delegationen reichen für das Alignement – eine halbe DKIM-Lage
        # (eine von zwei CNAMEs, oder eine nicht abfragbare) ist kein Grund, eine
        # scharfe Policy zum Fund zu erklären. Fund bleibt sie nur ohne jeden Beleg.
        dkim_ok = any(x["regel"] == "C3" and x["gewicht"] in ("ok", "hinweis")
                      for x in funde)
        if policy in ("reject", "quarantine") and not dkim_ok:
            funde.append(_regel("C5", "beides", "fund",
                                f"DMARC-Policy ist strenger als die Authentifizierung (p={policy})",
                                dmarc[0],
                                "solange C3 kein DKIM findet: `p=none` (nur beobachten); "
                                "p=quarantine erst nach verifizierter Domain, "
                                "p=reject danach und mit sauberen Berichten",
                                "Cloudflare → DNS → Records → TXT `_dmarc` bearbeiten",
                                "p=reject sagt allen Empfängern: was nicht alignt, ist "
                                "abzuweisen. Ohne eigenes DKIM alignt auf Brevo nichts – "
                                "die Policy verwandelt einen Zustellfehler in eine "
                                "zustellungsverhindernde Regel. Genau das ist der Fund "
                                "der Live-Zone vom 23.09.2026."))
        elif not policy:
            funde.append(_regel("C5", "cloudflare", "fund", "DMARC ohne Policy-Wert",
                                dmarc[0], "`p=` ist Pflicht (`p=none` im Zweifel)",
                                "Cloudflare → DNS → Records → TXT `_dmarc`",
                                "Ein DMARC-Satz ohne p= wird von den meisten Auswertern "
                                "als fehlerhaft ignoriert – die Domain gilt dann als "
                                "unbeschattet und ungeschützt."))
        else:
            funde.append(_regel("C5", "cloudflare", "ok", f"DMARC-Policy p={policy}",
                                dmarc[0], "—", "—", ""))
        if aspf == "s":
            funde.append(_regel("C5b", "beides", "hinweis",
                                "aspf=s: die SPF-Seite kann auf dieser Strecke nie alignen",
                                dmarc[0],
                                "`aspf=r` (relaxed), solange der Return-Path beim "
                                "Anbieter liegt; strict erst mit Dedicated IP oder "
                                "eigener Bounce-Domain (dann `include:spf.brevo.com` "
                                "in die Zone)",
                                "Cloudflare → DNS → TXT `_dmarc` bearbeiten",
                                "Strict verlangt exakte Übereinstimmung von SPF-Domain "
                                "und From-Domain. Auf Brevos geteiltem Versandweg bleibt "
                                "der Return-Path beim Anbieter, also bleibt diese "
                                "dauerhaft unerfüllt. Solange das Domain-DKIM trägt, ist "
                                "das folgenlos – und genau das ist der Punkt: Fällt DKIM "
                                "je um (Schlüssel-Rotation, ein Absender auf fremder "
                                "Domain), bleibt bei p=reject kein zweiter Beleg und die "
                                "Mail wird hart abgewiesen statt nur zu scheitern."))
        if adkim == "s" and not dkim_ok:
            funde.append(_regel("C5c", "beides", "hinweis",
                                "adkim=s bei fehlendem Domain-DKIM",
                                dmarc[0],
                                "`adkim=r` bis DKIM (C3) verifiziert ist, danach kann s "
                                "bleiben – es ist die strengere, aber legitime Form",
                                "Cloudflare → DNS → TXT `_dmarc` bearbeiten",
                                "Strict-DKIM verlangt d= exakt = From-Domain. Solange "
                                "kein eigener Schlüssel existiert, ist das ein "
                                "Ausschluss-Kriterium, kein Sicherheitsgewinn."))
        if not rua:
            funde.append(_regel("C5d", "cloudflare", "hinweis",
                                "DMARC ohne Berichtsweg (rua)",
                                dmarc[0],
                                "`rua=mailto:…` ergänzen – oder Brevos Berichtadresse "
                                "als zweiten Empfänger eintragen",
                                "Cloudflare → DNS → TXT `_dmarc` bearbeiten; Auswertung "
                                "z. B. in Brevo → Deliverability",
                                "Ohne Berichte ist der einzige Beweis „kam irgendwo an“ "
                                "ein Zufallspostfach."))
        if pct and int(pct.group(1)) < 100:
            funde.append(_regel("C5e", "cloudflare", "info",
                                f"DMARC nur für {pct.group(1)} % des Verkehrs",
                                dmarc[0], "bewusste Teststufe – vor dem ersten "
                                "Listen-Versand auf 100 ziehen oder begründet lassen",
                                "Cloudflare → DNS → TXT `_dmarc`", ""))

    # C6 – MX / eingehende Route für Reply-To
    antwort_an = abs_["antwort_an"]
    if antwort_an and antwort_an.split("@")[-1].strip().lower() == z and code_mx == "nicht messbar":
        funde.append(_regel("C6", "cloudflare", "nicht gemessen",
                            "MX-Lage nicht gemessen",
                            f"MX @{z} war nicht abfragbar",
                            "Abfrage wiederholen; lokal: `dig MX " + z + "`", "—",
                            "Ohne MX-Blick ist die Reply-To-Route weder geprüft noch "
                            "freigegeben."))
    elif antwort_an:
        reply_domain = antwort_an.split("@")[-1].strip().lower()
        if reply_domain == z:
            if not mx or any(m.endswith(".") and m.count(" ") and m.split()[-1] == "." for m in mx):
                funde.append(_regel("C6", "cloudflare", "fund",
                                    "Reply-To-Domain nimmt keine Mail an",
                                    f"MX @{z}: {', '.join(mx) or 'kein Eintrag (bzw. Null-MX)'}",
                                    "Cloudflare Email Routing aktivieren (MX auf "
                                    "route1/2/3.mx.cloudflare.net) – der Reply-To muss "
                                    "ein Briefkasten sein, keine Sackgasse",
                                    "Cloudflare → Zone → Email → Routing → Overview → "
                                    "Enable/Repair DNS records",
                                    "Jede Newsletter-Mail trägt „antworten an "
                                    + antwort_an + "\"; landet der Brief im Nirgendwo, "
                                    "verliert der Kanal genau die Leser, die schreiben."))
            else:
                funde.append(_regel("C6", "cloudflare", "ok", "MX für die Reply-To-Domain gesetzt",
                                    " | ".join(mx)[:180], "—", "—", ""))
    # C7 – Absender-Postfach
    if abs_["email"].endswith("@" + z):
        funde.append(_regel("C7", "beides", "hinweis",
                            "eigene Routing-Regel für die Absender-Adresse empfohlen",
                            f"Absender {abs_['email']} – sendefähig braucht keine "
                            "Mailbox, eingehende Briefe an diese Adresse laufen aber "
                            "ins Leere",
                            "zusätzliche Regel in Cloudflare Email Routing: Muster „"
                            + abs_["email"].split("@")[0] + "“ → dieselbe Zieladresse "
                            "(kein Catch-all)",
                            "Cloudflare → Email → Routing → Routing Rules → Create rule",
                            "Zustellmeldungen, Rückläufer und manuelle Antworten an "
                            "news@ sind Post, die sonst niemand liest – und bei "
                            "Domain-Problemen die einzige frühe Warnung."))
    return funde, messwerte


# --------------------------------------------------------------------- Regeln B* (API)
def pruefe_brevo(root: str, *, mit_netz: bool) -> list[dict]:
    """Alles, was im Brevo-Konto steht – nur messbar, wenn ein Key da ist."""
    out: list[dict] = []
    key = os.environ.get("BREVO_API_KEY", "").strip()
    liste = os.environ.get("BREVO_LIST_ID", "").strip()
    try:
        import newsletter_digest as digest
    except Exception as exc:  # noqa: BLE001
        return [_regel("B0", "brevo", "nicht messbar", "Digest-Modul nicht ladbar",
                       f"{exc.__class__.__name__}: {exc}", "—", "—", "")]
    if not mit_netz:
        return [_regel("B0", "brevo", "nicht gemessen",
                       "Lauf ohne Netz – Konto nicht geprüft",
                       "--ohne-netz gesetzt", "beim nächsten Lauf weglassen", "—",
                       "Kein Befund, kein Grün: eine nicht ausgeführte Prüfung ist "
                       "keine bestandene Prüfung.")]

    # B0 – Netzweg: erreicht der Client die API überhaupt? (ohne Key prüfbar!)
    code, antwort = digest.TRANSPORT_GET(key or "zustellbarkeits-probe", "senders")
    # Ohne Key kann hier nichts senden – ein Netzfehler ist dann eine
    # Messlücke, kein Versandbefund. Mit Key ist er der Blocker selbst.
    if code == 0:
        out.append(_regel("B0", "brevo", "fund" if key else "nicht messbar",
                          "Netzweg zur API gestört (DNS/TLS/Zeitlimit)",
                          digest.brevo_fehler(code, antwort)[:300],
                          "DoH/Ausgang der Laufumgebung prüfen; `curl -sI "
                          "https://api.brevo.com/v3/` muss antworten",
                          "— (das ist kein Konto-Befund)",
                          "Ohne Antwort der Kante ist jede Aussage über Absender und "
                          "Liste unmöglich – und der Versandlauf würde denselben "
                          "Abbruch melden."))
        return out
    if digest.kanten_block(code, antwort):
        # Die Blockage ist auch ohne Key ein Befund: sie würde den Lauf #21
        # erneut rot machen, und niemand darf sie für ein Konto-Problem halten.
        out.append(_regel("B0", "brevo", "fund",
                          "Signaturfilter vor der API blockiert den Lauf",
                          digest.brevo_fehler(code, antwort)[:300],
                          "Client-Kennung ist "
                          + " / ".join(digest.IDENTITÄTEN) +
                          " – beide probiert. Bleibt die Blockage: Kennung beim "
                          "Anbieter zur Freigabe nennen oder Lauf aus anderem Netz "
                          "starten",
                          "Brevo-Support (API-Endpoint) bzw. eigener Proxy/allow-list",
                          "HTTP 403 mit Fehler 1010 ist keine Absender-Absage: die "
                          "Anfrage erreichte Brevo nie. Genau daran scheiterte Lauf #21."))
        return out
    if not key:
        out.append(_regel("B0", "brevo", "info",
                          "Kante durchlässig, Key fehlt – Konto nicht geprüft",
                          f"Antwort HTTP {code} von der API (kein Zugriff ohne Key)",
                          "Secret BREVO_API_KEY setzen, dann prüft die Wache Absender, "
                          "Liste und Plan",
                          "Repo → Settings → Secrets and variables → Actions → "
                          "New repository secret → `BREVO_API_KEY`",
                          "Der Vorlauf ist gemessen, das Konto bewusst nicht: ohne Key "
                          "gehört hierhin ein Hinweis, kein Grün."))
        return out
    if code not in (200, 201):
        out.append(_regel("B0", "brevo", "fund", "API-Aufruf fehlgeschlagen",
                          digest.brevo_fehler(code, antwort)[:300],
                          "Key gültig? Domain des Keys = Domain des Kontos?",
                          "Brevo → oben rechts → SMTP & API → API Keys", ""))
        return out
    out.append(_regel("B0", "brevo", "ok", "Netzweg zur API frei",
                      f"HTTP {code} von api.brevo.com (Client-Kennung "
                      f"{digest.IDENTITÄTEN[digest.IDENTITÄTS_INDEX][:40]}…)",
                      "—", "—", ""))

    abs_ = absender(root)
    # B1 – Absender
    try:
        sender = json.loads(antwort).get("senders", []) or []
    except json.JSONDecodeError:
        sender = []
    eintrag = next((s for s in sender
                    if str(s.get("email", "")).lower() == abs_["email"].lower()), None)
    if eintrag is None:
        out.append(_regel("B1", "brevo", "fund",
                          f"Absender {abs_['email']} fehlt im Konto",
                          f"Konto-Sender: {', '.join(str(s.get('email')) for s in sender) or 'keine'}",
                          "Sender exakt mit dieser Adresse anlegen (Name: „"
                          + str(abs_.get("name") or "FranksFinanzcheck") + "“)",
                          "Brevo → Senders, Domains & Dedicated IPs → Senders & IPs → "
                          "Add sender",
                          "Der Versand bricht in der Vorprüfung am selben Punkt ab – "
                          "hier steht der Befund aber auch dann, wenn gar nicht gesendet wird."))
    elif not eintrag.get("active", False):
        out.append(_regel("B1", "brevo", "fund",
                          f"Absender {abs_['email']} ist nicht verifiziert",
                          "Sender vorhanden, `active: false`",
                          "Bestätigungslink (und ggf. `brevo-code`/DKIM) abschließen, "
                          "bis der Sender grün ist",
                          "Postfach des Absenders öffnen → Brevo-Mail bestätigen; "
                          "Domain-Status: Brevo → Senders, Domains & Dedicated IPs → "
                          "Domains",
                          "Ein unverifizierter Absender wird von Brevo abgewiesen, bevor "
                          "irgendwer eine Mail sieht."))
    else:
        out.append(_regel("B1", "brevo", "ok", "Absender verifiziert",
                          f"{eintrag.get('email')} (id {eintrag.get('id')})", "—", "—", ""))

    # B2/B3 – Liste + Platzzahlen
    if not liste or not re.fullmatch(r"\d+", liste):
        out.append(_regel("B2", "brevo", "fund" if liste else "hinweis",
                          "BREVO_LIST_ID fehlt oder ist keine Zahl",
                          f"Secret-Wert: {liste!r}",
                          "die Zahl aus der Listen-URL eintragen (`…/lists/7` → `7`)",
                          "Brevo → Contacts → Listen → Liste öffnen → URL lesen",
                          "Ohne Listen-ID legt der Lauf keine Kampagne an – und als "
                          "Variable statt Secret gesetzt, übersieht ihn die Wache still."))
        liste = ""
    if liste:
        c2, a2 = digest.TRANSPORT_GET(key, f"contacts/lists/{liste}")
        if c2 == 404:
            out.append(_regel("B2", "brevo", "fund",
                              f"Liste {liste} existiert nicht im Konto",
                              "HTTP 404 von der API",
                              "Secret auf die richtige Listen-ID setzen (die liegt in der "
                              "Listen-URL, nicht im Namen)",
                              "Brevo → Contacts → Listen", ""))
        elif c2 in (200, 201):
            try:
                dat = json.loads(a2)
            except json.JSONDecodeError:
                dat = {}
            n = dat.get("totalSubscribers")
            name = dat.get("name") or "—"
            try:
                n_i = int(n)
            except (TypeError, ValueError):
                n_i = -1
            if n_i == 0:
                out.append(_regel("B2", "brevo", "hinweis",
                                  f"Liste „{name}“ hat 0 Abonnenten",
                                  "totalSubscribers: 0",
                                  "Live-Versand läuft ins Leere; der Testversand "
                                  "(Workflow-Eingabe `test_adresse`) bleibt der "
                                  "vorgesehene Probelauf",
                                  "Brevo → Contacts → Listen → „" + str(name) + "“",
                                  "Ein Versand an niemanden ist technisch Erfolg und "
                                  "faktisch Post ins Nirgendwo."))
            else:
                out.append(_regel("B2", "brevo", "ok",
                                  f"Liste „{name}“ vorhanden",
                                  f"{n_i} Abonnenten", "—", "—", ""))
                # B3 – Plan-Grenze (Free: 300 Mails/Tag)
                c3, a3 = digest.TRANSPORT_GET(key, "account")
                plan = {}
                if c3 in (200, 201):
                    try:
                        pl = json.loads(a3).get("plan") or []
                        plan = pl[0] if pl else {}
                    except json.JSONDecodeError:
                        plan = {}
                grenze = None
                for feld in ("allowSentEmails", "maxContactsPerMonth", "dailyLimit"):
                    try:
                        if plan.get(feld) not in (None, ""):
                            grenze = int(plan[feld])
                            break
                    except (TypeError, ValueError):
                        continue
                planname = str(plan.get("name") or "").lower()
                if grenze is None and "free" not in planname:
                    out.append(_regel("B3", "brevo", "info",
                                      "Plan-Grenze nicht lesbar",
                                      f"GET /account → {c3}",
                                      "Tagesgrenze im Konto lesen (Free: 300 Mails/Tag)",
                                      "Brevo → Plan & Billing", ""))
                elif ((grenze is not None and n_i > grenze)
                      or ("free" in planname and n_i > PLAN_FREI_TAGESGRENZE)):
                    lim = grenze or PLAN_FREI_TAGESGRENZE
                    out.append(_regel("B3", "brevo", "fund",
                                      f"Liste ({n_i}) über der Tagesgrenze des Plans ({lim})",
                                      f"Plan: {plan.get('name', '—')}, Grenze {lim} Mails/Tag",
                                      "Plan wechseln ODER Kadenz senken (nicht täglich an "
                                      "alle) – ein Digest, den 40 % nie bekommen, ist kein "
                                      "Newsletter",
                                      "Brevo → Plan & Billing",
                                      "Ein Free-Plan versendet 300 Mails pro Tag. Ab der "
                                      "301. Adresse bleibt die Ausgabe des Tages dort "
                                      "liegen, wo sie niemand sieht – der Lauf bleibt "
                                      "grün, die Zustellung ist es nicht."))
                else:
                    out.append(_regel("B3", "brevo", "ok",
                                      f"Plan-Grenze reicht für die Liste ({n_i})",
                                      f"Plan: {plan.get('name', '—')}", "—", "—", ""))
    # B4 – Themenpräferenzen: sammelt die Site etwas, das beim Anbieter niemand liest?
    fang: dict = {}
    themen: list = []
    try:
        import newsletter_studio as studio
        konf = studio.konfiguration(root, streng=False)
        fang = studio.capture(root)
        themen = konf.get("themen") or []
    except (Exception, SystemExit):  # noqa: BLE001  (Studio fehlt: B4 prüft dann nichts)
        pass
    if themen:
        feld = str(fang.get("feld_themen") or "").strip()
        # Brevo liest Zusatzdaten aus `attributes[NAME]` (bzw. dem im Formular
        # angelegten Feld). Ein freie Name wie `themen` geht im Endpunkt ungelesen
        # unter – die Chips wären Dekoration mit DSGVO-Fußabdruck.
        if not feld.startswith("attributes[") and feld not in ("", "0"):
            out.append(_regel("B4", "brevo", "hinweis",
                              "Themen-Chips erreichen Brevo nicht (Feldname)",
                              f"capture.feld_themen = {feld!r} – die Formulare der "
                              "Anbieter lesen Attribute ausschließlich über "
                              "`attributes[NAME]`",
                              "Attribut anlegen und das Feld auf "
                              "`attributes[NAME]` stellen, ODER `feld_themen` leer "
                              "lassen, damit die Site keine Themenwahl verspricht",
                              "Brevo → Contacts → Attributes → Create attribute; "
                              "danach in `data/newsletter_studio.json` "
                              "→ capture.feld_themen = `attributes[NAME]`",
                              "Eine Auswahl, die nirgends ankommt, ist kein "
                              "Präferenz-Center, sondern ein Formularelement – und "
                              "die Datenschutzseite begründet damit die Erhebung von "
                              "etwas, das niemand auswertet."))
    return out


# --------------------------------------------------------------------- Staat (Digest)
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
                       "schon draußen war. Das ist genau die Doppelzustellung, die dieser ganze "
                       "Apparat verhindern soll.")]
    if state.get("versand_unklar"):
        block = state["versand_unklar"]
        out.append(_regel("S1", "repo", "fund",
                          "Versand-Halt aktiv (Ergebnis eines Laufs war unbelegbar)",
                          f"Kampagne {block.get('kampagne_id', '?')}, notiert "
                          f"{block.get('zeitpunkt', '?')}",
                          "in Brevo nachsehen (Kampagnen → Detail → Sends), dann den "
                          "Block `versand_unklar` aus der Statusdatei entfernen bzw. "
                          "`versand_unklar_geloest` mit Datum setzen",
                          "Brevo → Campaigns → „Digest …“ → Sends/Reports",
                          "Der Halt ist gewollt: kein Lauf schickt dieselbe Ausgabe "
                          "zweimal, nur weil einer keine Quittung bekam."))
    pending = state.get("pending") or []
    if pending:
        out.append(_regel("S2", "repo", "info",
                          f"{len(pending)} Artikel warten auf den Versand",
                          ", ".join(str(p) for p in pending[:3]) +
                          (f" … (+{len(pending) - 3})" if len(pending) > 3 else ""),
                          "nächster Werktag-Cron 05:05 UTC holt sie ab",
                          "Actions → Newsletter-Daily → Run workflow (`tage` 3 für einen Nachlauf)",
                          ""))
    if state.get("zuletzt_versandt"):
        out.append(_regel("S3", "repo", "ok", "letzter Versand belegt",
                          str(state.get("zuletzt_versandt")) +
                          f" · Kampagne {state.get('kampagne_id', '—')}", "—", "—", ""))
    else:
        out.append(_regel("S3", "repo", "hinweis",
                          "noch kein Versand protokolliert",
                          "data/newsletter_state.json trägt kein zuletzt_versandt",
                          "erste Ausgabe = Testversand (6a), dann Freigabe (6b): "
                          "docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md",
                          "Actions → Newsletter-Daily (Capture-Wache + Digest) → "
                          "Run workflow", ""))
    return out


# ------------------------------------------------------------------------- Ausgabe
GEWICHTE = ("fund", "hinweis", "nicht messbar", "nicht gemessen", "info", "ok")


def pruefe(root: str = BLOG_DIR, *, mit_netz: bool = True) -> dict:
    funde = []
    if mit_netz:
        cf, messwerte = pruefe_cloudflare(root)
    else:
        cf, messwerte = ([_regel("C0", "cloudflare", "nicht gemessen",
                                 "Lauf ohne Netz – Zone nicht geprüft",
                                 "--ohne-netz gesetzt", "beim nächsten Lauf weglassen",
                                 "—", "Ohne Messung kein Grün.")], {})
    funde += cf
    funde += pruefe_brevo(root, mit_netz=mit_netz)
    funde += pruefe_state(root)
    zählung = {g: sum(1 for f in funde if f["gewicht"] == g) for g in GEWICHTE}
    return {"zone": messwerte.get("zone", zone(root)), "funde": funde,
            "messwerte": messwerte, "zählung": zählung,
            "rc": 1 if zählung["fund"] else 0,
            "gemessen": mit_netz}


def als_md(erg: dict) -> str:
    zeilen = ["## 🛡 Newsletter-Zustellbarkeit (Cloudflare + Brevo)", "",
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
    fehler: list = []
    zaehler = 0

    def pruefe_es(bedingung: bool, meldung: str) -> None:
        nonlocal zaehler
        if bedingung:
            zaehler += 1
        else:
            fehler.append(meldung)

    # Der gemessene Zustand vom 23.09.2026 – exakt so, wie die Live-Zone antwortete.
    ZONE = "beispiel.de"
    zonen_umgebung = os.environ.get("NEWSLETTER_MAILZONE", "")
    os.environ["NEWSLETTER_MAILZONE"] = ZONE      # dieselbe Override wie im Lauf

    def zone_vorfall(name: str, typ: str) -> tuple[int, list[str]]:
        werte = {
            f"{ZONE}": {"MX": [0, ["17 route2.mx.cloudflare.net.",
                                   "41 route1.mx.cloudflare.net."]],
                        "TXT": [0, ["v=spf1 include:_spf.mx.cloudflare.net ~all",
                                    "brevo-code:81fd84cb3fdce1639e158278d0d75cb1"]]},
            f"_dmarc.{ZONE}": {"TXT": [0, ["v=DMARC1; p=reject; adkim=s; aspf=s; "
                                           "rua=mailto:x@dmarc-reports.cloudflare.net;"]]},
        }
        for sel in ("mail", "default", "s1", "k1", "dkim"):
            werte.setdefault(f"{sel}._domainkey.{ZONE}", {"TXT": [3, []], "CNAME": [3, []]})
        for sel in ("brevo1", "brevo2"):
            werte.setdefault(f"{sel}._domainkey.{ZONE}", {"TXT": [3, []], "CNAME": [3, []]})
        try:
            return werte[name][typ]
        except KeyError:
            return 3, []

    global AUFLOESER
    echter = AUFLOESER
    try:
        AUFLOESER = zone_vorfall
        import tempfile
        tmp = tempfile.mkdtemp(prefix="zustell-selbsttest-")
        os.makedirs(os.path.join(tmp, "data"), exist_ok=True)
        with open(os.path.join(tmp, "data", "newsletter_state.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"pending": ["a"]}, fh)
        with open(os.path.join(tmp, "data", "newsletter_studio.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"capture": {"feld_themen": "themen"},
                       "email": {"absender": {"name": "Frank von FranksFinanzcheck",
                                             "email": "news@beispiel.de"},
                                 "antwort_an": "kontakt@beispiel.de"},
                       "themen": [{"id": "strom-sparen", "label": "Strom & Gas",
                                   "brevo_interest": "Strom & Gas"}]}, fh)
        regeln = {r["regel"]: r for r in pruefe_cloudflare(tmp)[0]}
        pruefe_es(regeln.get("C1", {}).get("gewicht") == "ok",
                  f"SPF (einer, Routing enthalten) meldet nicht ok: {regeln.get('C1')}")
        pruefe_es(regeln.get("C2", {}).get("gewicht") == "hinweis",
                  "fehlendes Brevo-Include bleibt unbemerkt (C2)")
        pruefe_es(regeln.get("C3", {}).get("gewicht") == "fund",
                  "fehlendes DKIM meldet nicht als Fund (C3)")
        pruefe_es("kopieren" in regeln["C3"]["weg"].lower() or "Domains" in regeln["C3"]["weg"],
                  f"C3 ohne Klickweg: {regeln['C3']['weg']}")
        pruefe_es(regeln.get("C4", {}).get("gewicht") == "ok",
                  "brevo-code vorhanden, aber C4 meldet Fund")
        pruefe_es(regeln.get("C5", {}).get("gewicht") == "fund",
                  "p=reject ohne DKIM meldet nicht als Fund (C5)")
        pruefe_es("reject" in regeln["C5"]["grund"],
                  "C5-Begründung erklärt die Ableitung nicht")
        pruefe_es(regeln.get("C5b", {}).get("gewicht") == "hinweis",
                  "aspf=s auf Brevo-Strecke unbemerkt (C5b)")
        pruefe_es(regeln.get("C6", {}).get("gewicht") == "ok",
                  f"MX vorhanden, C6 meldet nicht ok: {regeln.get('C6')}")
        pruefe_es(regeln.get("C7", {}).get("gewicht") == "hinweis",
                  "fehlende Absender-Regel unbemerkt (C7)")

        # Zwei SPF-Einträge = permerror: der Fund muss kommen, auch wenn beide ok aussehen
        def zone_doppelt(name: str, typ: str) -> tuple[int, list[str]]:
            if name == ZONE and typ == "TXT":
                return 0, ["v=spf1 include:_spf.mx.cloudflare.net ~all",
                           "v=spf1 include:spf.brevo.com ~all",
                           "brevo-code:x"]
            if name.startswith("_dmarc"):
                return 0, ["v=DMARC1; p=none; rua=mailto:x@y.de"]
            if name.endswith("._domainkey." + ZONE) and typ == "TXT":
                return 0, ["k=rsa;p=MII…"] if name.startswith("mail.") else [3, []][1]
            return 3, []
        AUFLOESER = zone_doppelt
        regeln2 = {r["regel"]: r for r in pruefe_cloudflare(tmp)[0]}
        pruefe_es(regeln2.get("C1", {}).get("gewicht") == "fund",
                  "zwei SPF-Einträge gelten nicht als permanenter Fehler (C1)")
        pruefe_es(regeln2.get("C5", {}).get("gewicht") == "ok",
                  "p=none mit eigenem DKIM-Schlüssel muss ok heißen")
        pruefe_es("C5b" not in regeln2,
                  "aspf fehlt im Datensatz, aber C5b meldet strict (Default ist relaxed)")

        # DNS nicht erreichbar → „nicht messbar“, nie „in Ordnung“
        def zone_tot(name: str, typ: str) -> tuple[int, list[str]]:
            return -1, ["dns.google: URLError"]
        AUFLOESER = zone_tot
        regeln3 = pruefe_cloudflare(tmp)[0]
        pruefe_es(regeln3 and regeln3[0]["gewicht"] == "nicht messbar",
                  f"Netz-Ausfall meldet nicht „nicht messbar“: {regeln3}")
        pruefe_es(not any(r["gewicht"] == "ok" for r in regeln3),
                  "ohne Messung gibt es Grün – verboten")

        # B-Regeln: der Transport wird eingespiegelt, kein Netz im Selbsttest
        AUFLOESER = zone_vorfall
        try:
            import newsletter_digest as digest
        except Exception as exc:  # noqa: BLE001
            pruefe_es(False, f"Digest-Modul nicht ladbar: {exc}")
            digest = None
        if digest:
            echt_get, echt_post = digest.TRANSPORT_GET, digest.TRANSPORT
            def fake_get(key, pfad):
                if pfad == "senders":
                    return 200, json.dumps({"senders": [
                        {"email": "news@beispiel.de", "active": True, "id": 1}]})
                if pfad.startswith("contacts/lists/"):
                    return 200, json.dumps({"id": 7, "name": "Blog-Abonnenten",
                                            "totalSubscribers": 420})
                if pfad == "account":
                    return 200, json.dumps({"plan": [{"name": "Free",
                                                      "allowSentEmails": 300}]})
                if pfad == "attributes":
                    return 200, json.dumps({"attributes": []})
                return 200, "{}"
            digest.TRANSPORT_GET = fake_get
            digest.TRANSPORT = lambda k, p, b: (201, "{}")
            os.environ["BREVO_API_KEY"] = "k"
            os.environ["BREVO_LIST_ID"] = "7"
            reg = {r["regel"]: r for r in pruefe_brevo(tmp, mit_netz=True)}
            pruefe_es(reg.get("B0", {}).get("gewicht") == "ok",
                      f"Netzweg bei HTTP 200 nicht ok: {reg.get('B0')}")
            pruefe_es(reg.get("B1", {}).get("gewicht") == "ok",
                      "verifizierter Absender meldet nicht ok (B1)")
            pruefe_es(reg.get("B3", {}).get("gewicht") == "fund",
                      f"420 Abonnenten > 300/Tag bleibt unbemerkt: {reg.get('B3')}")
            # Kantenblockage: dieselbe Antwort, die Lauf #21 rot machte
            def kanten_get(key, pfad):  # noqa: ANN001
                return 403, ('{"title":"Error 1010: Access denied","status":403,'
                              '"detail":"blocked based on your browser\'s signature"}')
            digest.TRANSPORT_GET = kanten_get
            reg_k = {r["regel"]: r for r in pruefe_brevo(tmp, mit_netz=True)}
            pruefe_es(reg_k.get("B0", {}).get("gewicht") == "fund"
                      and "1010" in json.dumps(reg_k["B0"], ensure_ascii=False),
                      f"Kantenblockage nicht als B0-Fund erkannt: {reg_k.get('B0')}")
            # Ohne Key: Hinweis, kein Grün, kein Netzversand-Alarm
            digest.TRANSPORT_GET = fake_get
            vorher = os.environ.pop("BREVO_API_KEY", "")
            reg_ohne = {r["regel"]: r for r in pruefe_brevo(tmp, mit_netz=True)}
            pruefe_es(reg_ohne.get("B0", {}).get("gewicht") == "info"
                      and "Secret" in reg_ohne["B0"]["soll"],
                      f"Key-los-Fall meldet nicht als Hinweis mit Weg: {reg_ohne.get('B0')}")
            os.environ["BREVO_API_KEY"] = vorher
            digest.TRANSPORT_GET, digest.TRANSPORT = echt_get, echt_post

        # Status-Datei: unlesbar = Fund, Halt = Fund, sonst Info/ok
        with open(os.path.join(tmp, "data", "newsletter_state.json"), "w",
                  encoding="utf-8") as fh:
            fh.write("{ kaputt")
        s1 = pruefe_state(tmp)
        pruefe_es(s1 and s1[0]["gewicht"] == "fund",
                  f"kaputte Statusdatei ohne Fund: {s1}")
        with open(os.path.join(tmp, "data", "newsletter_state.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"versand_unklar": {"kampagne_id": 12}}, fh)
        s2 = {r["regel"]: r for r in pruefe_state(tmp)}
        pruefe_es(s2.get("S1", {}).get("gewicht") == "fund"
                  and "versand_unklar" in json.dumps(s2["S1"], ensure_ascii=False),
                  f"Versand-Halt nicht gemeldet: {s2.get('S1')}")

        # B0 ohne Key: ein Netzfehler ist dann eine Messlücke, kein
        # Versandbefund – ohne Key sendet nichts, also darf nichts rot heißen.
        def netz_tot(key, pfad):
            return 0, "URLError: <urlopen error TLS blocked>"
        digest.TRANSPORT_GET = netz_tot
        vorher_key = os.environ.pop("BREVO_API_KEY", "")
        reg_l = {r["regel"]: r for r in pruefe_brevo(tmp, mit_netz=True)}
        pruefe_es(reg_l.get("B0", {}).get("gewicht") == "nicht messbar",
                  f"Netzfehler ohne Key als harter Befund: {reg_l.get('B0')}")
        os.environ["BREVO_API_KEY"] = "k"
        reg_l2 = {r["regel"]: r for r in pruefe_brevo(tmp, mit_netz=True)}
        pruefe_es(reg_l2.get("B0", {}).get("gewicht") == "fund",
                  "Netzfehler MIT Key nicht als Blocker erkannt (B0)")
        os.environ["BREVO_API_KEY"] = vorher_key

        # C3/C5 zusammen: ist das Domain-DKIM veröffentlicht, darf p=reject grün
        # sein – sonst meldet jede gesunde Zone einen False-Positive.
        def zone_mit_dkim(name: str, typ: str) -> tuple[int, list[str]]:
            if name == f"mail._domainkey.{ZONE}" and typ == "TXT":
                return 0, ["k=rsa; p=MIGfMA0GCSq…"]
            return zone_vorfall(name, typ)
        AUFLOESER = zone_mit_dkim
        reg_d = {r["regel"]: r for r in pruefe_cloudflare(tmp)[0]}
        pruefe_es(reg_d.get("C3", {}).get("gewicht") == "ok",
                  "veröffentlichtes Domain-DKIM meldet nicht ok (C3)")
        pruefe_es(reg_d.get("C5", {}).get("gewicht") == "ok",
                  "p=reject mit eigenem DKIM darf kein Fund sein (C5)")
        AUFLOESER = zone_vorfall

        # Ausgabeformate: Summary-Markdown und JSON tragen denselben Befund
        speicher_ruhig = os.path.join(tmp, "data", "newsletter_state.json")
        with open(speicher_ruhig, "w", encoding="utf-8") as fh:
            json.dump({"zuletzt_versandt": "2026-09-23T07:05:00+00:00",
                       "kampagne_id": 3}, fh)
        erg = pruefe(tmp, mit_netz=False)
        md = als_md(erg)
        pruefe_es(erg["rc"] == 0 and "🌫" in md,
                  f"ohne Netz muss „nicht gemessen“ stehen, rc aber 0 bleiben: {erg['rc']}\n{md[:200]}")
        # ---- Messlücke vs. Befund: eine nicht gestellte Frage ist kein Grün,
        # aber auch kein Grund, die erreichbaren Schichten nicht zu berichten.
        def zone_txt_blind(name: str, typ: str) -> tuple[int, list[str]]:
            if name == ZONE and typ == "TXT":
                return -1, ["dns.google: URLError"]
            return zone_vorfall(name, typ)

        AUFLOESER = zone_txt_blind
        blind = {r["regel"]: r for r in pruefe_cloudflare(tmp)[0]}
        pruefe_es(blind.get("C0", {}).get("gewicht") == "nicht messbar",
                  "eine Teillücke der DNS-Abfrage wird nicht als Lücke gemeldet (C0)")
        blind_teil = blind["C0"]["ist"].split("blind:")[-1].split("·")[0]
        pruefe_es("TXT @" in blind_teil and "MX @" not in blind_teil,
                  f"C0 benennt die falschen blinden Abfragen: {blind['C0']['ist']}")
        pruefe_es(blind.get("C1", {}).get("gewicht") == "nicht gemessen",
                  "ein ungelesener SPF zählt als Befund statt als Lücke (C1)")
        pruefe_es(blind.get("C4", {}).get("gewicht") == "nicht gemessen",
                  "ein ungelesener Domain-Code zählt als Befund (C4)")
        pruefe_es(blind.get("C5", {}).get("gewicht") == "fund",
                  "die erreichbare DMARC-Messung wurde trotz TXT-Lücke verschluckt (C5)")
        pruefe_es(blind.get("C6", {}).get("gewicht") == "ok",
                  "die erreichbare MX-Messung wurde verschluckt (C6)")
        pruefe_es("blind" not in json.dumps(blind["C6"]),
                  "C6 erbt die Lückenmeldung von C0")

        # ---- halbes DKIM: eine sichtbare Delegation ist kein „DKIM fehlt“
        def zone_halbes_dkim(name: str, typ: str) -> tuple[int, list[str]]:
            if name == f"brevo1._domainkey.{ZONE}" and typ == "CNAME":
                return 0, ["b1.beispiel-de.dkim.brevo.com."]
            if name == f"brevo2._domainkey.{ZONE}" and typ == "CNAME":
                return -1, ["dns.google: URLError"]     # nicht abfragbar, nicht fehlend
            return zone_vorfall(name, typ)

        AUFLOESER = zone_halbes_dkim
        halb = {r["regel"]: r for r in pruefe_cloudflare(tmp)[0]}
        pruefe_es(halb.get("C3", {}).get("gewicht") == "hinweis",
                  f"eine sichtbare + eine nicht abfragbare Delegation meldet als "
                  f"{halb.get('C3', {}).get('gewicht')} – erwartet hinweis")
        pruefe_es(halb.get("C5", {}).get("gewicht") != "fund",
                  "scharfe DMARC-Policy bei sichtbarem DKIM wird zum Fund (C5)")
        pruefe_es(halb.get("C5c", {}).get("gewicht") is None,
                  "adkim=s-Hinweis läuft trotz sichtbarer Delegation (C5c)")

        def zone_zweit_cname_weg(name: str, typ: str) -> tuple[int, list[str]]:
            if name == f"brevo1._domainkey.{ZONE}" and typ == "CNAME":
                return 0, ["b1.beispiel-de.dkim.brevo.com."]
            return zone_vorfall(name, typ)   # brevo2 antwortet NXDOMAIN = gemessen, leer

        AUFLOESER = zone_zweit_cname_weg
        einzeln = {r["regel"]: r for r in pruefe_cloudflare(tmp)[0]}
        pruefe_es(einzeln.get("C3", {}).get("gewicht") == "hinweis",
                  "nur eine von zwei Delegationen meldet nicht als hinweis")
        pruefe_es("zweite fehlt" in einzeln["C3"]["soll"],
                  f"der Hinweis sagt nicht, dass die zweite Delegation fehlt: {einzeln['C3']['soll']}")
        AUFLOESER = zone_vorfall

        pruefe_es(json.dumps(erg, ensure_ascii=False), "Ausgabe nicht JSON-tauglich")
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception as exc:  # noqa: BLE001
        import traceback
        fehler.append(f"Ausführung: {exc.__class__.__name__}: {exc}\n"
                      + traceback.format_exc()[-600:])
    finally:
        AUFLOESER = echter
        if zonen_umgebung:
            os.environ["NEWSLETTER_MAILZONE"] = zonen_umgebung
        else:
            os.environ.pop("NEWSLETTER_MAILZONE", None)
        for k in ("BREVO_API_KEY", "BREVO_LIST_ID"):
            os.environ.pop(k, None)
    if fehler:
        print("🛑 newsletter_zustellbarkeit-Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("  -", f)
        return 2
    print(f"✅ newsletter_zustellbarkeit-Selbsttest: {zaehler} Fälle grün (Live-Zone "
          f"23.09.2026, Doppel-SPF, DKIM als TXT und als CNAME, halbes DKIM, "
          f"DMARC-Strenge und ihre Kopplung an C3, Messlücke vs. Befund, "
          f"Netzweg/Kantenblockage, Plan-Grenze, inertes Themenfeld, Status-Halt, "
          f"Ausgabeformate).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Zustellbarkeits-Wache: Cloudflare-DNS + Brevo-Konto prüfen")
    ap.add_argument("--root", default=BLOG_DIR)
    ap.add_argument("--pruefen", action="store_true")
    ap.add_argument("--ohne-netz", action="store_true",
                    help="weder DNS noch API anfassen (meldet „nicht gemessen“)")
    ap.add_argument("--strict", action="store_true",
                    help="auch „nicht gemessen/nicht messbar“ als Fehler (Freigabe-Gate)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", action="store_true", help="Block für die Step-Summary")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if not args.pruefen:
        ap.error("entweder --pruefen oder --selftest")
    erg = pruefe(os.path.abspath(args.root), mit_netz=not args.ohne_netz)
    if args.json:
        print(json.dumps(erg, ensure_ascii=False, indent=2))
    elif args.md:
        print(als_md(erg))
    else:
        for f in erg["funde"]:
            print(f"[{f['regel']}/{f['gewicht']}] {f['titel']}")
            if f["ist"]:
                print(f"    Ist:  {f['ist']}")
            if f["soll"] and f["soll"] != "—":
                print(f"    Soll: {f['soll']}")
            if f["weg"] and f["weg"] != "—":
                print(f"    Weg:  {f['weg']}")
        print(f"Zustellbarkeit Zone {erg['zone']}: " +
              ", ".join(f"{k} {v}" for k, v in erg["zählung"].items() if v))
    rc = erg["rc"]
    if args.strict and any(f["gewicht"] in ("nicht messbar", "nicht gemessen")
                           for f in erg["funde"]):
        rc = 1
    for f in erg["funde"]:
        if f["gewicht"] == "fund":
            # Die Kurzfassung in der Actions-Übersicht: Ursache + nächster Schritt,
            # nicht nur eine Regelnummer.
            print(f"::error::[{f['regel']}] {f['titel']} – {f['soll'][:220]}")
        elif f["gewicht"] in ("hinweis", "nicht messbar", "nicht gemessen"):
            print(f"::warning::[{f['regel']}] {f['titel']} – {(f['soll'] or f['grund'])[:220]}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
