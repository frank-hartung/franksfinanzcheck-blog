#!/usr/bin/env python3
# ============================================================
#  BACKUP-EINRICHTUNG – Voraussetzungen des Offsite-Backups prüfen
#  ------------------------------------------------------------
#  Vorgang WF-9E5A / Meldung #761 (15.10.2026):
#    Der Job „KV-/D1-Backup“ in backup-offsite.yml (Sicherheitsaudit M-11)
#    war ab seinem ersten Lauf rot. Das war richtig: Ohne Ziel, Passphrase
#    und Cloudflare-Lesezugang darf er kein Schein-Grün melden. Falsch war
#    die Lage drumherum:
#      · Die Meldung riet zu „API-Key abgelaufen (GROQ/GEMINI)“ und
#        „neu starten“ – bei einer unvollständigen Einrichtung hilft beides
#        nicht.
#      · Die alte Prüfung sah nur, OB ein Wert gesetzt ist. Falscher
#        Token-Umfang, ein Ziel ohne Zugriff, ein Namespace aus dem falschen
#        Konto oder ein Token, der in drei Wochen abläuft, wären erst mitten
#        im Export aufgefallen – oder gar nicht.
#      · Der Verweis „siehe Umsetzungs-Runbook“ zeigte auf keine Datei.
#
#  DIESES MODUL prüft jede Voraussetzung einzeln, live und mit Abhilfe:
#    E1 Ziel-Repository         Variable BACKUP_REPO            Format, ≠ Quelle
#    E2 Schreibzugang           Secret   BACKUP_REPO_TOKEN      gültig, Ziel PRIVAT, Ablauf
#    E3 Passphrase              Secret   BACKUP_PASSPHRASE      Mindestlänge
#    E4 Cloudflare-Konto        Secret   CLOUDFLARE_ACCOUNT_ID  Format
#    E5 Cloudflare-Lesezugang   Secret   CF_KV_BACKUP_TOKEN     aktiv, Ablauf
#    E6 KV-Namespace ABO        Variable KV_NAMESPACE_ID_ABO    mit E5 lesbar
#    E7 D1-Datenbank (optional) Variable D1_DATABASE_ID         mit E5 lesbar
#    E8 Environment-Schutz      Environment „backup“            nur Branch main
#  Ein offener Pflichtpunkt (E1–E6, E7 sobald gesetzt) ergibt Exit 1 –
#  fail-closed wie bisher. Jeder Punkt erscheint als Annotation UND als Zeile
#  in der Job-Zusammenfassung, mit dem Link, unter dem er erledigt wird.
#  E8 ist ein Hinweis: Er schützt die Zugänge, ohne die Sicherung zu stoppen.
#
#  FRISTEN: Die Ablaufdaten aus E2 (Header github-authentication-token-
#  expiration) und E5 (expires_on) gehen als BACKUP_FRIST_TAGE in die
#  Job-Umgebung. Der letzte Job-Schritt (`--fristen`) färbt den Lauf rot,
#  sobald weniger als FRIST_ROT Tage bleiben – NACH der Sicherung. So meldet
#  sich ein auslaufender Token zwei Wochen vorher über das normale Alerting,
#  statt die Sicherung eines Nachts still zu beenden.
#
#  GEHEIMNISSE: Kein Secret-Wert erscheint in Ausgabe, Annotation,
#  Zusammenfassung oder Umgebungsdatei. Ausgegeben werden nur Namen, Zustände
#  und Antworten der APIs (Selbsttest F12 prüft das mit vergifteten Werten).
#
#  Aufruf:
#    python3 scripts/backup_einrichtung.py --pruefen    # Workflow-Schritt, Exit 1 bei offenem Punkt
#    python3 scripts/backup_einrichtung.py --fristen    # letzter Schritt: Ablauf-Vorwarnung
#    python3 scripts/backup_einrichtung.py --selftest   # offline, ohne Netz
#  Anleitung: docs/ANLEITUNG-OFFSITE-BACKUP.md
# ============================================================
"""Prüft die Voraussetzungen des Offsite-Backups – live, einzeln, mit Abhilfe."""

from __future__ import annotations

import argparse
import datetime as dt
import io
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from contextlib import redirect_stdout
from dataclasses import dataclass, field

ANLEITUNG = "docs/ANLEITUNG-OFFSITE-BACKUP.md"
GH_API = "https://api.github.com"
CF_API = "https://api.cloudflare.com/client/v4"
ENVIRONMENT = "backup"
STANDARD_BESITZER = "frank-hartung"
STANDARD_ZIELNAME = "franksfinanzcheck-backup"

# Ab weniger als FRIST_GELB Resttagen: Hinweis. Ab weniger als FRIST_ROT:
# der letzte Schritt wird rot (nach der Sicherung) und das Alerting meldet.
FRIST_GELB = 30
FRIST_ROT = 14
# E3: Untergrenze für die Passphrase (unverändert gegenüber der alten
# Inline-Prüfung im Workflow). Empfehlung in der Anleitung: 32+ Zeichen.
MINDESTLAENGE_E3 = 20

STUFEN = ("ok", "info", "warnung", "fehler")
SYMBOL = {"ok": "✅", "info": "ℹ️", "warnung": "⚠️", "fehler": "❌"}

_REPO_FORM = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})/[A-Za-z0-9._-]{1,100}$")
_HEX32 = re.compile(r"^[0-9a-fA-F]{32}$")
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


# =====================================================================
#  Links, unter denen ein offener Punkt erledigt wird (eine Quelle der
#  Wahrheit – die Anleitung zitiert genau diese Adressen, ein Test prüft es)
# =====================================================================
def link_ziel_anlegen(besitzer: str = STANDARD_BESITZER) -> str:
    """GitHub-Formular „neues Repository“, vorbelegt: privat, fester Name."""
    abfrage = urllib.parse.urlencode({
        "owner": besitzer,
        "name": STANDARD_ZIELNAME,
        "visibility": "private",
        "description": "Private Sicherungen (verschlüsselt)",
    })
    return f"https://github.com/new?{abfrage}"


def link_schreibzugang(besitzer: str = STANDARD_BESITZER) -> str:
    """Fine-grained PAT, vorbelegt: Contents write, 366 Tage, Besitzer gesetzt.
    Die Repository-Auswahl lässt sich nicht vorbelegen – die Anleitung sagt,
    dass dort NUR das Backup-Repository gewählt wird."""
    abfrage = urllib.parse.urlencode({
        "name": "ff-offsite-backup",
        "description": "Offsite-Backup: Entwurfs-Releases im privaten Backup-Repo (nur dieses Repo)",
        "target_name": besitzer,
        "expires_in": "366",
        "contents": "write",
    })
    return f"https://github.com/settings/personal-access-tokens/new?{abfrage}"


def link_cloudflare_lesezugang(mit_d1: bool = False) -> str:
    """Konto-eigener Cloudflare-API-Token, vorbelegt: nur Lesen (KV, optional D1)."""
    rechte = [{"key": "workers_kv_storage", "type": "read"}]
    if mit_d1:
        rechte.append({"key": "d1", "type": "read"})
    abfrage = urllib.parse.urlencode({
        "permissionGroupKeys": json.dumps(rechte, separators=(",", ":")),
        "name": "ff-kv-backup (nur lesen)",
    })
    # `to=/:account/…` bleibt unkodiert – so steht es in der Cloudflare-Doku.
    return f"https://dash.cloudflare.com/?to=/:account/api-tokens&{abfrage}"


LINK_CLOUDFLARE_KONTO = "https://dash.cloudflare.com/?to=/:account/workers-and-pages"
LINK_KV_NAMESPACES = "https://dash.cloudflare.com/?to=/:account/workers/kv/namespaces"
LINK_D1 = "https://dash.cloudflare.com/?to=/:account/workers/d1"


def link_einstellungen(quelle: str, bereich: str) -> str:
    """bereich: environments | variables | secrets"""
    pfade = {
        "environments": "settings/environments",
        "variables": "settings/variables/actions",
        "secrets": "settings/secrets/actions",
    }
    return f"https://github.com/{quelle}/{pfade[bereich]}"


# =====================================================================
#  Datentypen
# =====================================================================
@dataclass
class Befund:
    kennung: str
    titel: str
    stufe: str
    text: str
    abhilfe: str = ""
    link: str = ""

    def __post_init__(self) -> None:
        if self.stufe not in STUFEN:
            raise ValueError(f"unbekannte Stufe {self.stufe!r}")


@dataclass
class Ergebnis:
    befunde: list[Befund] = field(default_factory=list)
    # (Name der Einstellung, Resttage) – Namen, nie Werte
    fristen: list[tuple[str, int]] = field(default_factory=list)
    # E8: Käme ein fremder Branch an die Backup-Zugänge? (Environment fehlt,
    # keine Branch-Regel oder Regel erlaubt mehr als main.) Eine reine
    # Pflicht-Freigabe zählt nicht – sie bremst Läufe, öffnet aber nichts.
    environment_offen: bool = False

    def neu(self, *args, **kwargs) -> Befund:
        befund = Befund(*args, **kwargs)
        self.befunde.append(befund)
        return befund

    def offen(self) -> list[Befund]:
        return [b for b in self.befunde if b.stufe == "fehler"]

    def befund(self, kennung: str) -> Befund:
        for eintrag in self.befunde:
            if eintrag.kennung == kennung:
                return eintrag
        return Befund(kennung, "", "info", "")

    def stufe_von(self, kennung: str) -> str:
        return self.befund(kennung).stufe if any(b.kennung == kennung for b in self.befunde) else ""

    def knappste_frist(self) -> tuple[str, int] | None:
        return min(self.fristen, key=lambda f: f[1]) if self.fristen else None


# =====================================================================
#  HTTP (im Selbsttest austauschbar) – wirft nie, liefert den Status
# =====================================================================
def _json_oder_none(roh: str):
    try:
        return json.loads(roh) if roh else None
    except ValueError:
        return None


def _http_einmal(methode: str, url: str, kopf: dict | None = None, frist: int = 20):
    """Liefert (status, kopfzeilen_klein, json|None, netzfehler). Status 0 = kein Netz."""
    anfrage = urllib.request.Request(url, method=methode, headers={
        "User-Agent": "ff-backup-einrichtung/1",
        "Accept": "application/json",
        **(kopf or {}),
    })
    try:
        with urllib.request.urlopen(anfrage, timeout=frist) as antwort:
            roh = antwort.read().decode("utf-8", "replace")
            kopfzeilen = {k.lower(): v for k, v in antwort.headers.items()}
            return antwort.status, kopfzeilen, _json_oder_none(roh), ""
    except urllib.error.HTTPError as fehler:
        try:
            roh = fehler.read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 – Körper ist Beiwerk, Status zählt
            roh = ""
        kopfzeilen = {k.lower(): v for k, v in (fehler.headers or {}).items()}
        return fehler.code, kopfzeilen, _json_oder_none(roh), ""
    except (urllib.error.URLError, TimeoutError, OSError) as fehler:
        return 0, {}, None, type(fehler).__name__


VORUEBERGEHEND = {0, 429, 500, 502, 503, 504}
SCHLAF = time.sleep  # im Selbsttest austauschbar (keine Wartezeit)


def _http(methode: str, url: str, kopf: dict | None = None):
    """Bis zu drei Versuche bei vorübergehenden Fehlern (Netz, 429, 5xx)."""
    ergebnis = (0, {}, None, "nicht versucht")
    for versuch in range(3):
        ergebnis = _http_einmal(methode, url, kopf)
        if ergebnis[0] not in VORUEBERGEHEND:
            return ergebnis
        if versuch < 2:
            SCHLAF(2 * (versuch + 1))
    return ergebnis


HTTP = _http


# =====================================================================
#  Hilfen
# =====================================================================
def _kurz(text, grenze: int = 160) -> str:
    """API-Meldungen einzeilig und begrenzt (Log, Annotation, Tabelle)."""
    rein = " ".join(str(text or "").split())
    return rein if len(rein) <= grenze else rein[: grenze - 1] + "…"


def _cf_meldung(antwort) -> str:
    if isinstance(antwort, dict):
        fehlerliste = antwort.get("errors") or []
        if fehlerliste and isinstance(fehlerliste[0], dict):
            code = fehlerliste[0].get("code")
            return _kurz(f"{fehlerliste[0].get('message', '')}" + (f" (Code {code})" if code else ""))
    return ""


def _gh_meldung(antwort) -> str:
    return _kurz(antwort.get("message", "")) if isinstance(antwort, dict) else ""


def _dazu(vorher: str, neu: str) -> str:
    return f"{vorher} {neu}" if vorher else neu


def _resttage(ende: dt.datetime, jetzt: dt.datetime) -> int:
    return int((ende - jetzt).total_seconds() // 86400)


def gh_ablauf_lesen(kopfwert: str) -> dt.datetime | None:
    """Header `github-authentication-token-expiration`, z. B. „2027-10-15 07:00:00 UTC“."""
    wert = (kopfwert or "").strip()
    if not wert:
        return None
    for muster in ("%Y-%m-%d %H:%M:%S UTC", "%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d %H:%M:%S"):
        try:
            zeit = dt.datetime.strptime(wert, muster)
        except ValueError:
            continue
        return zeit if zeit.tzinfo else zeit.replace(tzinfo=dt.timezone.utc)
    return iso_lesen(wert)


def iso_lesen(wert: str) -> dt.datetime | None:
    try:
        zeit = dt.datetime.fromisoformat(str(wert).strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return zeit if zeit.tzinfo else zeit.replace(tzinfo=dt.timezone.utc)


def _frist_bewerten(ergebnis: Ergebnis, befund: Befund, name: str,
                    ende: dt.datetime | None, jetzt: dt.datetime) -> None:
    """Hängt die Restlaufzeit an einen grünen Befund und stuft bei Bedarf herab."""
    if ende is None:
        befund.text += " · ohne Ablaufdatum"
        return
    tage = _resttage(ende, jetzt)
    ergebnis.fristen.append((name, tage))
    datum = ende.astimezone(dt.timezone.utc).strftime("%d.%m.%Y")
    if tage < 0:
        befund.stufe = "fehler"
        befund.text += f" · ABGELAUFEN am {datum}"
        befund.abhilfe = _dazu(befund.abhilfe, "Zugang neu erzeugen und das Secret ersetzen "
                                                 "(Anleitung, Abschnitt „Zugänge erneuern“).")
    elif tage < FRIST_GELB:
        befund.stufe = "warnung"
        befund.text += f" · läuft am {datum} ab (noch {tage} Tag(e))"
        befund.abhilfe = _dazu(befund.abhilfe, "Rechtzeitig erneuern (Anleitung, Abschnitt „Zugänge erneuern“).")
    else:
        befund.text += f" · gültig bis {datum} (noch {tage} Tage)"


# =====================================================================
#  Die Prüfpunkte E1–E8
# =====================================================================
def _e1_ziel(ergebnis: Ergebnis, umgebung: dict, besitzer: str) -> str:
    titel = "Ziel-Repository · Variable BACKUP_REPO"
    ziel = (umgebung.get("ZIEL_REPO") or "").strip()
    quelle = (umgebung.get("GITHUB_REPOSITORY") or "").strip()
    if not ziel:
        ergebnis.neu("E1", titel, "fehler", "fehlt",
                     "Privates Repository anlegen und seinen Namen (besitzer/name) als "
                     "Repository-Variable BACKUP_REPO eintragen.", link_ziel_anlegen(besitzer))
        return ""
    if not _REPO_FORM.match(ziel):
        ergebnis.neu("E1", titel, "fehler", "kein gültiger Name (erwartet: besitzer/name)",
                     "Wert der Variable BACKUP_REPO korrigieren, z. B. "
                     f"{besitzer}/{STANDARD_ZIELNAME}.",
                     link_einstellungen(quelle or f"{besitzer}/franksfinanzcheck-blog", "variables"))
        return ""
    if quelle and ziel.lower() == quelle.lower():
        ergebnis.neu("E1", titel, "fehler",
                     "zeigt auf das (öffentliche) Quell-Repository selbst – das ist kein Offsite-Ziel",
                     "Eigenes privates Repository anlegen und in BACKUP_REPO eintragen.",
                     link_ziel_anlegen(besitzer))
        return ""
    ergebnis.neu("E1", titel, "ok", ziel)
    return ziel


def _e2_schreibzugang(ergebnis: Ergebnis, umgebung: dict, ziel: str,
                      besitzer: str, jetzt: dt.datetime) -> None:
    titel = "Schreibzugang · Secret BACKUP_REPO_TOKEN"
    gh_zugang = (umgebung.get("ZIEL_TOKEN") or "").strip()
    if not gh_zugang:
        ergebnis.neu("E2", titel, "fehler", "fehlt",
                     "Fine-grained Token anlegen (Repository access: NUR das Backup-Repository, "
                     "Contents: Read and write) und als Secret BACKUP_REPO_TOKEN im Environment "
                     "„backup“ speichern.", link_schreibzugang(besitzer))
        return
    if not ziel:
        ergebnis.neu("E2", titel, "fehler", "vorhanden, aber ohne gültiges Ziel (E1) nicht prüfbar",
                     "Erst E1 erledigen.")
        return
    status, kopf, antwort, netz = HTTP("GET", f"{GH_API}/repos/{ziel}", {
        "Authorization": f"Bearer {gh_zugang}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    if status == 0:
        ergebnis.neu("E2", titel, "fehler", f"GitHub-API nicht erreichbar ({netz}) – vermutlich vorübergehend",
                     "Lauf später neu starten (Actions → Offsite-Backup → Run workflow).")
        return
    if status == 401:
        ergebnis.neu("E2", titel, "fehler", "Token ungültig oder abgelaufen (HTTP 401)",
                     "Token neu erzeugen und das Secret ersetzen.", link_schreibzugang(besitzer))
        return
    if status == 404:
        ergebnis.neu("E2", titel, "fehler",
                     f"{ziel} nicht gefunden – das Repository fehlt, oder der Token hat keinen Zugriff darauf",
                     "Repository anlegen bzw. im Token unter „Only select repositories“ genau dieses "
                     "Repository auswählen.", link_ziel_anlegen(besitzer))
        return
    if status == 403:
        meldung = _gh_meldung(antwort)
        # 403 unterscheidet: Rate-Limit (secondary), fehlende Rechte oder IP-Beschränkung.
        # Die API-Meldung nennen – „rate limit“ ist vorübergehend, sonst Konfiguration.
        if meldung and "rate limit" in meldung.lower():
            ergebnis.neu("E2", titel, "fehler",
                         f"GitHub-Rate-Limit erreicht (HTTP 403){f': {meldung}' if meldung else ''}",
                         "Einige Minuten warten und den Lauf neu starten (Actions → Offsite-Backup → Run workflow).")
        else:
            ergebnis.neu("E2", titel, "fehler",
                         f"Zugriff verweigert (HTTP 403){f': {meldung}' if meldung else ''} – Token ohne Zugriff auf {ziel}",
                         "Im Token unter „Only select repositories“ genau dieses Repository wählen und "
                         "„Contents: Read and write“ prüfen.", link_schreibzugang(besitzer))
        return
    if status != 200 or not isinstance(antwort, dict):
        meldung = _gh_meldung(antwort)
        ergebnis.neu("E2", titel, "fehler",
                     f"unerwartete Antwort HTTP {status}" + (f": {meldung}" if meldung else ""),
                     "Token und Ziel prüfen; bei wiederholtem HTTP 403 Rate-Limit ausschließen.")
        return
    if antwort.get("private") is not True:
        sichtbar = "ÖFFENTLICH" if antwort.get("private") is False else "Sichtbarkeit unbekannt"
        ergebnis.neu("E2", titel, "fehler",
                     f"{ziel} ist {sichtbar} – ein Backup darf nie öffentlich liegen",
                     "Ziel auf privat stellen (Settings → General → Danger Zone → Change visibility) "
                     "oder ein privates Repository verwenden.")
        return
    if antwort.get("archived") is True:
        ergebnis.neu("E2", titel, "fehler", f"{ziel} ist archiviert und damit schreibgeschützt",
                     "Archivierung aufheben (Settings → General → Danger Zone → Unarchive).")
        return
    befund = ergebnis.neu("E2", titel, "ok", f"Zugriff auf {ziel} bestätigt, Ziel ist privat")
    if gh_zugang.startswith("ghp_"):
        befund.stufe = "warnung"
        befund.text += " · klassischer Token (Zugriff auf ALLE Repositories)"
        befund.abhilfe = "Durch einen fine-grained Token ersetzen, der nur das Backup-Repository sieht."
        befund.link = link_schreibzugang(besitzer)
    ende = gh_ablauf_lesen(kopf.get("github-authentication-token-expiration", ""))
    _frist_bewerten(ergebnis, befund, "BACKUP_REPO_TOKEN", ende, jetzt)


def _e3_entschluesselung(ergebnis: Ergebnis, umgebung: dict) -> None:
    titel = "Passphrase · Secret BACKUP_PASSPHRASE"
    wert = umgebung.get("PASSWORT") or ""
    if not wert:
        ergebnis.neu("E3", titel, "fehler", "fehlt",
                     "Zufällige Passphrase (32+ Zeichen) ERST im Passwort-Manager speichern – ohne sie "
                     "ist jede Sicherung unlesbar –, dann als Secret BACKUP_PASSPHRASE im Environment "
                     "„backup“ eintragen.")
        return
    if len(wert) < MINDESTLAENGE_E3:
        ergebnis.neu("E3", titel, "fehler", f"kürzer als {MINDESTLAENGE_E3} Zeichen – zu schwach für ein Offline-Ziel",
                     "Längere zufällige Passphrase erzeugen (32+ Zeichen) und ersetzen. Ältere "
                     "Sicherungen bleiben mit der alten Passphrase lesbar – beide aufbewahren.")
        return
    ergebnis.neu("E3", titel, "ok", f"gesetzt (mindestens {MINDESTLAENGE_E3} Zeichen)")


def _e4_konto(ergebnis: Ergebnis, umgebung: dict) -> str:
    titel = "Cloudflare-Konto · Secret CLOUDFLARE_ACCOUNT_ID"
    konto = (umgebung.get("CF_ACCOUNT_ID") or "").strip()
    if not konto:
        ergebnis.neu("E4", titel, "fehler", "fehlt",
                     "Account ID aus dem Cloudflare-Dashboard (Workers & Pages, rechte Spalte) als "
                     "Secret CLOUDFLARE_ACCOUNT_ID eintragen.", LINK_CLOUDFLARE_KONTO)
        return ""
    if not _HEX32.match(konto):
        ergebnis.neu("E4", titel, "fehler", "kein gültiges Format (erwartet: 32 Hex-Zeichen)",
                     "Account ID erneut aus dem Dashboard kopieren.", LINK_CLOUDFLARE_KONTO)
        return ""
    ergebnis.neu("E4", titel, "ok", "gesetzt (Format gültig)")
    return konto


def _cf_kopf(cf_zugang: str) -> dict:
    return {"Authorization": f"Bearer {cf_zugang}"}


def _e5_lesezugang(ergebnis: Ergebnis, umgebung: dict, konto: str,
                   jetzt: dt.datetime) -> str:
    titel = "Cloudflare-Lesezugang · Secret CF_KV_BACKUP_TOKEN"
    cf_zugang = (umgebung.get("CF_API_TOKEN") or "").strip()
    mit_d1 = bool((umgebung.get("D1_DATABASE_ID") or "").strip())
    if not cf_zugang:
        ergebnis.neu("E5", titel, "fehler", "fehlt",
                     "Cloudflare-API-Token NUR mit „Workers KV Storage: Read“"
                     + (" und „D1: Read“" if mit_d1 else "")
                     + " anlegen und als Secret CF_KV_BACKUP_TOKEN im Environment „backup“ speichern.",
                     link_cloudflare_lesezugang(mit_d1))
        return ""
    # Nutzer-eigene Tokens antworten unter /user, konto-eigene nur unter /accounts/<id>.
    pfade = [("Nutzer-Token", f"{CF_API}/user/tokens/verify")]
    if konto:
        pfade.append(("Konto-Token", f"{CF_API}/accounts/{konto}/tokens/verify"))
    letzte_meldung, netzfehler = "", ""
    for art, url in pfade:
        status, _kopf, antwort, netz = HTTP("GET", url, _cf_kopf(cf_zugang))
        if status == 0:
            netzfehler = netz
            continue
        if status == 200 and isinstance(antwort, dict) and antwort.get("success"):
            daten = antwort.get("result") or {}
            zustand = str(daten.get("status") or "").lower()
            if zustand != "active":
                ergebnis.neu("E5", titel, "fehler", f"{art} ist „{zustand or 'unbekannt'}“, nicht aktiv",
                             "Token neu erzeugen bzw. reaktivieren und das Secret ersetzen.",
                             link_cloudflare_lesezugang(mit_d1))
                return ""
            befund = ergebnis.neu("E5", titel, "ok", f"{art} aktiv")
            _frist_bewerten(ergebnis, befund, "CF_KV_BACKUP_TOKEN",
                            iso_lesen(daten["expires_on"]) if daten.get("expires_on") else None, jetzt)
            return cf_zugang if befund.stufe != "fehler" else ""
        letzte_meldung = _cf_meldung(antwort) or f"HTTP {status}"
    if netzfehler and not letzte_meldung:
        ergebnis.neu("E5", titel, "fehler", f"Cloudflare-API nicht erreichbar ({netzfehler}) – vermutlich vorübergehend",
                     "Lauf später neu starten.")
        return ""
    ergebnis.neu("E5", titel, "fehler", f"Token wird von Cloudflare nicht anerkannt ({letzte_meldung})",
                 "Token neu erzeugen und das Secret ersetzen."
                 + ("" if konto else " Bei einem Konto-Token zusätzlich E4 erledigen."),
                 link_cloudflare_lesezugang(mit_d1))
    return ""


def _e6_namespace(ergebnis: Ergebnis, umgebung: dict, konto: str, cf_zugang: str) -> None:
    titel = "KV-Namespace ABO · Variable KV_NAMESPACE_ID_ABO"
    ns = (umgebung.get("KV_NAMESPACE_ID") or "").strip()
    if not ns:
        ergebnis.neu("E6", titel, "fehler", "fehlt",
                     "ID des Namespace ABO (Cloudflare → Storage & Databases → Workers KV) als "
                     "REPOSITORY-Variable KV_NAMESPACE_ID_ABO eintragen – das Offsite-Backup "
                     "benötigt sie weiterhin; der Worker-Deploy kann die bestehende ABO-Bindung "
                     "inzwischen selbst auflösen.", LINK_KV_NAMESPACES)
        return
    if not _HEX32.match(ns):
        ergebnis.neu("E6", titel, "fehler", "kein gültiges Format (erwartet: 32 Hex-Zeichen, nicht der Name)",
                     "Die ID (nicht den Titel) des Namespace kopieren.", LINK_KV_NAMESPACES)
        return
    if not (konto and cf_zugang):
        ergebnis.neu("E6", titel, "fehler", "gesetzt, aber ohne E4/E5 nicht prüfbar", "Erst E4 und E5 erledigen.")
        return
    status, _kopf, antwort, netz = HTTP(
        "GET", f"{CF_API}/accounts/{konto}/storage/kv/namespaces/{ns}", _cf_kopf(cf_zugang))
    if status == 200 and isinstance(antwort, dict) and antwort.get("success"):
        name = _kurz((antwort.get("result") or {}).get("title") or "ohne Titel", 60)
        ergebnis.neu("E6", titel, "ok", f"lesbar (Namespace „{name}“)")
        return
    if status == 0:
        ergebnis.neu("E6", titel, "fehler", f"Cloudflare-API nicht erreichbar ({netz})", "Lauf später neu starten.")
        return
    meldung = _cf_meldung(antwort)
    if status in (401, 403):
        ergebnis.neu("E6", titel, "fehler",
                     "der Token darf diesen Namespace nicht lesen" + (f" ({meldung})" if meldung else ""),
                     "Im Token das Recht „Workers KV Storage: Read“ für dieses Konto ergänzen "
                     "(oder Token neu anlegen).", link_cloudflare_lesezugang(bool(umgebung.get("D1_DATABASE_ID"))))
        return
    if status == 404:
        ergebnis.neu("E6", titel, "fehler", "Namespace in diesem Konto nicht gefunden",
                     "ID prüfen – sie muss zum Konto aus E4 gehören.", LINK_KV_NAMESPACES)
        return
    ergebnis.neu("E6", titel, "fehler", f"unerwartete Antwort HTTP {status}" + (f": {meldung}" if meldung else ""),
                 "Später erneut prüfen; bleibt es, Token und ID kontrollieren.")


def _e7_d1(ergebnis: Ergebnis, umgebung: dict, konto: str, cf_zugang: str) -> None:
    titel = "D1-Datenbank (optional) · Variable D1_DATABASE_ID"
    db = (umgebung.get("D1_DATABASE_ID") or "").strip()
    if not db:
        ergebnis.neu("E7", titel, "info", "nicht gesetzt – gesichert wird nur KV (Klick-Zähler nicht im Backup)")
        return
    if not _UUID.match(db):
        ergebnis.neu("E7", titel, "fehler", "kein gültiges Format (erwartet: UUID)",
                     "Datenbank-ID kopieren oder die Variable entfernen.", LINK_D1)
        return
    if not (konto and cf_zugang):
        ergebnis.neu("E7", titel, "fehler", "gesetzt, aber ohne E4/E5 nicht prüfbar", "Erst E4 und E5 erledigen.")
        return
    status, _kopf, antwort, netz = HTTP("GET", f"{CF_API}/accounts/{konto}/d1/database/{db}", _cf_kopf(cf_zugang))
    if status == 200 and isinstance(antwort, dict) and antwort.get("success"):
        name = _kurz((antwort.get("result") or {}).get("name") or "ohne Namen", 60)
        ergebnis.neu("E7", titel, "ok", f"lesbar (Datenbank „{name}“)")
        return
    if status == 0:
        ergebnis.neu("E7", titel, "fehler", f"Cloudflare-API nicht erreichbar ({netz})", "Lauf später neu starten.")
        return
    meldung = _cf_meldung(antwort)
    ergebnis.neu("E7", titel, "fehler",
                 f"nicht lesbar (HTTP {status})" + (f": {meldung}" if meldung else ""),
                 "Im Token „D1: Read“ ergänzen – oder die Variable D1_DATABASE_ID entfernen, wenn "
                 "der Klick-Zähler nicht gesichert werden soll.", link_cloudflare_lesezugang(True))


def _e8_environment(ergebnis: Ergebnis, umgebung: dict) -> None:
    titel = f"Environment-Schutz · „{ENVIRONMENT}“ nur für main"
    quelle = (umgebung.get("GITHUB_REPOSITORY") or "").strip()
    if not quelle:
        ergebnis.neu("E8", titel, "info", "nur im Workflow prüfbar (GITHUB_REPOSITORY fehlt)")
        return
    kopf = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    lauf_zugang = (umgebung.get("GH_TOKEN") or umgebung.get("GITHUB_TOKEN") or "").strip()
    if lauf_zugang:
        kopf["Authorization"] = f"Bearer {lauf_zugang}"
    basis = f"{GH_API}/repos/{quelle}/environments/{ENVIRONMENT}"
    status, _k, antwort, _netz = HTTP("GET", basis, kopf)
    if status in (401, 403) and "Authorization" in kopf:
        # Fehlt dem Lauf-Token das Recht „actions: read“, bleibt der Weg ohne
        # Token: Bei einem öffentlichen Repo sind die Environment-Daten lesbar.
        kopf = {k: v for k, v in kopf.items() if k != "Authorization"}
        status, _k, antwort, _netz = HTTP("GET", basis, kopf)
    einstellungen = link_einstellungen(quelle, "environments")
    if status == 404:
        ergebnis.environment_offen = True
        ergebnis.neu("E8", titel, "warnung", "Environment fehlt – GitHub legt es beim ersten Lauf OHNE Schutz an",
                     "Environment „backup“ anlegen, Deployment branches: nur main.", einstellungen)
        return
    if status != 200 or not isinstance(antwort, dict):
        ergebnis.neu("E8", titel, "info", f"nicht prüfbar (HTTP {status})")
        return
    hinweise = []
    regeln = [str((r or {}).get("type")) for r in (antwort.get("protection_rules") or [])]
    if "required_reviewers" in regeln:
        hinweise.append("Pflicht-Freigabe aktiv: jeder nächtliche Lauf wartet auf einen Klick und bricht "
                        "nach 30 Tagen ab – für „backup“ entfernen, Schutz über die Branch-Regel")
    politik = antwort.get("deployment_branch_policy")
    if politik is None:
        ergebnis.environment_offen = True
        hinweise.append("jeder Branch darf das Environment nutzen – ein Arbeitszweig mit geänderter "
                        "Workflow-Datei käme an die Backup-Zugänge")
    elif politik.get("custom_branch_policies"):
        status2, _k2, liste, _n2 = HTTP("GET", f"{basis}/deployment-branch-policies", kopf)
        if status2 == 200 and isinstance(liste, dict):
            namen = sorted(str((p or {}).get("name")) for p in (liste.get("branch_policies") or []))
            fremde = [n for n in namen if n != "main"]
            if fremde:
                ergebnis.environment_offen = True
            if fremde or not namen:
                hinweise.append("Branch-Regel erlaubt mehr als main: " + _kurz(", ".join(fremde) or "(leer)", 80))
    if hinweise:
        ergebnis.neu("E8", titel, "warnung", " · ".join(hinweise),
                     "Settings → Environments → backup: „Deployment branches and tags“ → Selected → "
                     "nur main; keine Required reviewers.", einstellungen)
        return
    ergebnis.neu("E8", titel, "ok", "nur main darf die Backup-Zugänge nutzen")


def pruefen(umgebung: dict, jetzt: dt.datetime | None = None) -> Ergebnis:
    """Alle Prüfpunkte in fester Reihenfolge. Reine Funktion bis auf HTTP."""
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    quelle = (umgebung.get("GITHUB_REPOSITORY") or "").strip()
    besitzer = quelle.split("/", 1)[0] if "/" in quelle else STANDARD_BESITZER
    ergebnis = Ergebnis()
    ziel = _e1_ziel(ergebnis, umgebung, besitzer)
    _e2_schreibzugang(ergebnis, umgebung, ziel, besitzer, jetzt)
    _e3_entschluesselung(ergebnis, umgebung)
    konto = _e4_konto(ergebnis, umgebung)
    cf_zugang = _e5_lesezugang(ergebnis, umgebung, konto, jetzt)
    _e6_namespace(ergebnis, umgebung, konto, cf_zugang)
    _e7_d1(ergebnis, umgebung, konto, cf_zugang)
    _e8_environment(ergebnis, umgebung)
    return ergebnis


# =====================================================================
#  Ausgabe: Konsole, Annotationen, Job-Zusammenfassung, Umgebungsdatei
# =====================================================================
def _befehl_daten(text: str) -> str:
    return str(text).replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _befehl_eigenschaft(text: str) -> str:
    return _befehl_daten(text).replace(":", "%3A").replace(",", "%2C")


def _md(text: str) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def reihenfolge_hinweis(ergebnis: Ergebnis) -> str:
    """Erst absichern, dann befüllen.

    Die Prüfliste steht in Kennungs-Reihenfolge (E1 … E8). Wer sie während der
    Einrichtung von oben nach unten abarbeitet, legte die Secrets in ein
    Environment, das noch jeder Branch nutzen darf. Solange Pflichtpunkte offen
    sind und das Environment offensteht, gehört E8 deshalb an den Anfang.
    """
    if ergebnis.offen() and ergebnis.environment_offen:
        return ("Zuerst E8: das Environment „backup“ auf main beschränken, dann die Zugänge eintragen – "
                "so liegt kein Secret in einem Environment, das jeder Branch nutzen darf.")
    return ""


def konsolen_bericht(ergebnis: Ergebnis) -> str:
    zeilen = ["Offsite-Backup – Einrichtungsprüfung (Vorgang WF-9E5A)"]
    hinweis = reihenfolge_hinweis(ergebnis)
    if hinweis:
        zeilen.append(f"  👉 {hinweis}")
    for b in ergebnis.befunde:
        zeilen.append(f"  {SYMBOL[b.stufe]} {b.kennung} {b.titel}: {b.text}")
        if b.abhilfe and b.stufe != "ok":
            zeilen.append(f"       → {b.abhilfe}")
        if b.link and b.stufe != "ok":
            zeilen.append(f"       → {b.link}")
    zeilen.append(schlusssatz(ergebnis))
    zeilen.append(f"Anleitung: {ANLEITUNG}")
    return "\n".join(zeilen)


def schlusssatz(ergebnis: Ergebnis) -> str:
    offen = ergebnis.offen()
    if offen:
        kennungen = ", ".join(b.kennung for b in offen)
        return (f"🛑 {len(offen)} Pflichtpunkt(e) offen ({kennungen}) – es wird NICHTS gesichert "
                "(fail-closed). Ein Neustart ändert daran nichts.")
    warnungen = [b.kennung for b in ergebnis.befunde if b.stufe == "warnung"]
    if warnungen:
        return f"✅ Alle Pflichtpunkte erfüllt – mit Hinweis(en): {', '.join(warnungen)}."
    return "✅ Alle Pflichtpunkte erfüllt."


def annotationen(ergebnis: Ergebnis) -> list[str]:
    aus = []
    for b in ergebnis.befunde:
        if b.stufe not in ("fehler", "warnung"):
            continue
        art = "error" if b.stufe == "fehler" else "warning"
        titel = f"Backup-Einrichtung {b.kennung} – {b.titel}"
        text = b.text
        if b.abhilfe:
            text += f" → {b.abhilfe}"
        if b.link:
            text += f" {b.link}"
        text += f" · Anleitung: {ANLEITUNG}"
        aus.append(f"::{art} title={_befehl_eigenschaft(titel)}::{_befehl_daten(text)}")
    return aus


def zusammenfassung(ergebnis: Ergebnis, quelle: str = "") -> str:
    anleitung = (f"[`{ANLEITUNG}`](https://github.com/{quelle}/blob/main/{ANLEITUNG})"
                 if quelle else f"`{ANLEITUNG}`")
    zeilen = ["## Offsite-Backup – Einrichtungsprüfung", ""]
    hinweis = reihenfolge_hinweis(ergebnis)
    if hinweis:
        zeilen += [f"> 👉 **{_md(hinweis)}**", ""]
    zeilen += [
        "| Punkt | Stand | Befund | Was tun |",
        "|---|:-:|---|---|",
    ]
    for b in ergebnis.befunde:
        tun = "–"
        if b.stufe != "ok" and (b.abhilfe or b.link):
            tun = _md(b.abhilfe)
            if b.link:
                tun = (tun + " " if tun else "") + f"[Hier erledigen]({b.link})"
        zeilen.append(f"| **{b.kennung}** {_md(b.titel)} | {SYMBOL[b.stufe]} | {_md(b.text)} | {tun} |")
    zeilen += ["", f"**{schlusssatz(ergebnis)}**", "", f"Anleitung Schritt für Schritt: {anleitung}", ""]
    return "\n".join(zeilen)


def _anhaengen(pfad: str, text: str) -> None:
    if pfad:
        with open(pfad, "a", encoding="utf-8") as datei:
            datei.write(text if text.endswith("\n") else text + "\n")


def _fristen_exportieren(ergebnis: Ergebnis, pfad: str) -> None:
    knapp = ergebnis.knappste_frist()
    if knapp and pfad:
        name, tage = knapp
        _anhaengen(pfad, f"BACKUP_FRIST_TAGE={int(tage)}\nBACKUP_FRIST_ZUGANG={name}\n")


def befehl_pruefen(umgebung: dict | None = None, jetzt: dt.datetime | None = None) -> int:
    umgebung = dict(os.environ) if umgebung is None else umgebung
    ergebnis = pruefen(umgebung, jetzt)
    print(konsolen_bericht(ergebnis))
    if umgebung.get("GITHUB_ACTIONS") == "true":
        for zeile in annotationen(ergebnis):
            print(zeile)
    _anhaengen(umgebung.get("GITHUB_STEP_SUMMARY", ""),
               zusammenfassung(ergebnis, (umgebung.get("GITHUB_REPOSITORY") or "").strip()))
    _fristen_exportieren(ergebnis, umgebung.get("GITHUB_ENV", ""))
    return 1 if ergebnis.offen() else 0


def befehl_fristen(umgebung: dict | None = None) -> int:
    """Letzter Job-Schritt: läuft nur nach erfolgreicher Sicherung."""
    umgebung = dict(os.environ) if umgebung is None else umgebung
    roh = (umgebung.get("BACKUP_FRIST_TAGE") or "").strip()
    name = (umgebung.get("BACKUP_FRIST_ZUGANG") or "").strip() or "ein Zugang"
    summary = umgebung.get("GITHUB_STEP_SUMMARY", "")
    if not roh:
        print("✅ Fristen: keine Ablaufdaten gemeldet (Zugänge ohne Ablaufdatum) – nichts zu erneuern.")
        return 0
    try:
        tage = int(roh)
    except ValueError:
        print(f"::error title=Fristwarnung::BACKUP_FRIST_TAGE ist keine Zahl – die Einrichtungsprüfung "
              f"hat einen ungültigen Wert hinterlassen. Anleitung: {ANLEITUNG}")
        return 1
    if tage < FRIST_ROT:
        text = (f"{name} läuft in {tage} Tag(en) ab. Die heutige Sicherung ist gelaufen – jetzt erneuern, "
                f"sonst endet die Sicherung am Ablaufdatum. Anleitung: {ANLEITUNG}, Abschnitt „Zugänge erneuern“.")
        print(f"::error title={_befehl_eigenschaft('Fristwarnung – Zugang läuft ab')}::{_befehl_daten(text)}")
        _anhaengen(summary, f"### ⏰ Fristwarnung\n\n**{_md(text)}**\n")
        return 1
    if tage < FRIST_GELB:
        text = f"{name} läuft in {tage} Tagen ab – bitte in den nächsten Tagen erneuern ({ANLEITUNG})."
        print(f"::warning title={_befehl_eigenschaft('Fristwarnung')}::{_befehl_daten(text)}")
        _anhaengen(summary, f"### ⏰ Fristwarnung\n\n{_md(text)}\n")
        return 0
    print(f"✅ Fristen: der knappste Zugang ({name}) ist noch {tage} Tage gültig.")
    return 0


# =====================================================================
#  Selbsttest – offline, ohne Netz, mit vergifteten Secret-Werten
# =====================================================================
def selbsttest() -> int:  # noqa: C901 – bewusst ein Block: jede Fallgruppe sichtbar
    global HTTP, SCHLAF, _http_einmal
    echt_http, echt_schlaf, echt_einmal = HTTP, SCHLAF, _http_einmal
    jetzt = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.timezone.utc)
    gift = {"ZIEL_TOKEN": "github_pat_GIFTWERT_E2_0123456789",
            "PASSWORT": "GIFTWERT-E3-passphrase-0123456789",
            "CF_API_TOKEN": "GIFTWERT_E5_cf_0123456789abcdef"}
    konto, ns, db = "a" * 32, "b" * 32, "12345678-1234-1234-1234-123456789abc"
    voll = {"ZIEL_REPO": "frank-hartung/franksfinanzcheck-backup", **gift,
            "CF_ACCOUNT_ID": konto, "KV_NAMESPACE_ID": ns,
            "GITHUB_REPOSITORY": "frank-hartung/franksfinanzcheck-blog", "GH_TOKEN": "GIFTWERT_LAUF"}
    fehler: list[str] = []
    aufrufe: list[str] = []

    def welt(**anders):
        """Baut eine gefälschte API-Welt; Schlüssel überschreiben einzelne Antworten."""
        antworten = {
            "repo": (200, {"github-authentication-token-expiration": "2027-04-15 07:00:00 UTC"},
                     {"private": True, "full_name": voll["ZIEL_REPO"]}),
            "cf_user": (200, {}, {"success": True, "result": {"id": "x", "status": "active"}}),
            "cf_konto": (401, {}, {"success": False, "errors": [{"code": 1000, "message": "Invalid API Token"}]}),
            "kv": (200, {}, {"success": True, "result": {"id": ns, "title": "ABO"}}),
            "d1": (200, {}, {"success": True, "result": {"name": "klicks"}}),
            "env": (200, {}, {"protection_rules": [], "deployment_branch_policy":
                              {"protected_branches": False, "custom_branch_policies": True}}),
            "env_politik": (200, {}, {"branch_policies": [{"name": "main", "type": "branch"}]}),
        }
        antworten.update(anders)

        def gefaelscht(methode, url, kopf=None):
            aufrufe.append(url)
            if "/deployment-branch-policies" in url:
                schluessel = "env_politik"
            elif "/environments/" in url:
                schluessel = "env_mit_token" if ("env_mit_token" in antworten and
                                                 "Authorization" in (kopf or {})) else "env"
            elif url.startswith(GH_API + "/repos/"):
                schluessel = "repo"
            elif url.endswith("/user/tokens/verify"):
                schluessel = "cf_user"
            elif "/tokens/verify" in url:
                schluessel = "cf_konto"
            elif "/storage/kv/namespaces/" in url:
                schluessel = "kv"
            elif "/d1/database/" in url:
                schluessel = "d1"
            else:
                raise AssertionError(f"unerwartete URL {url}")
            status, kopfzeilen, koerper = antworten[schluessel]
            return status, kopfzeilen, koerper, ("ConnectionError" if status == 0 else "")
        return gefaelscht

    def lauf(umgebung, **anders) -> Ergebnis:
        global HTTP
        HTTP = welt(**anders)
        return pruefen(umgebung, jetzt)

    try:
        SCHLAF = lambda _s: None  # noqa: E731 – keine Wartezeit im Test

        # F1: Leere Einrichtung (die Lage von #761) → E1–E6 rot, E7 Info, kein Netzaufruf
        aufrufe.clear()
        leer = lauf({})
        if [b.kennung for b in leer.offen()] != ["E1", "E2", "E3", "E4", "E5", "E6"]:
            fehler.append(f"F1: offene Punkte {[b.kennung for b in leer.offen()]}")
        if leer.stufe_von("E7") != "info" or leer.stufe_von("E8") != "info":
            fehler.append("F1: E7/E8 müssen ohne Werte Info sein")
        if aufrufe:
            fehler.append(f"F1: ohne Werte darf nichts live geprüft werden: {aufrufe}")
        links = " ".join(b.link for b in leer.befunde)
        for soll in ("github.com/new?", "personal-access-tokens/new?", "dash.cloudflare.com/?to=/:account/api-tokens",
                     "workers_kv_storage", "contents=write", "visibility=private"):
            if soll not in links:
                fehler.append(f"F1: Abhilfe-Link fehlt: {soll}")

        # F2: Vollständige, gesunde Einrichtung → alles grün, Frist bekannt
        gut = lauf(voll)
        if gut.offen() or any(b.stufe == "warnung" for b in gut.befunde):
            fehler.append(f"F2: gesunde Einrichtung nicht grün: {[(b.kennung, b.stufe, b.text) for b in gut.befunde]}")
        if gut.knappste_frist() != ("BACKUP_REPO_TOKEN", 181):
            fehler.append(f"F2: Frist falsch: {gut.knappste_frist()}")
        if "ABO" not in gut.befund("E6").text:
            fehler.append("F2: Namespace-Titel fehlt im Befund")

        # F3: Ziel ÖFFENTLICH → E2 rot (Kern des Audits: nie öffentlich ablegen)
        offen = lauf(voll, repo=(200, {}, {"private": False}))
        if offen.stufe_von("E2") != "fehler" or "ÖFFENTLICH" not in offen.befund("E2").text:
            fehler.append("F3: öffentliches Ziel nicht rot")

        # F4: 404 und 401 werden unterschieden – keine „nicht privat“-Fehldeutung mehr
        e404 = lauf(voll, repo=(404, {}, {"message": "Not Found"}))
        e401 = lauf(voll, repo=(401, {}, {"message": "Bad credentials"}))
        if "keinen Zugriff" not in e404.befund("E2").text or \
                "ungültig oder abgelaufen" not in e401.befund("E2").text:
            fehler.append("F4: 404/401 nicht präzise benannt")

        # F5: Ablauf in 10 Tagen → E2 Warnung (Sicherung läuft), Frist 10 → --fristen rot
        knapp = lauf(voll, repo=(200, {"github-authentication-token-expiration": "2026-10-25 13:00:00 UTC"},
                                 {"private": True}))
        if knapp.offen() or knapp.stufe_von("E2") != "warnung" or knapp.knappste_frist() != ("BACKUP_REPO_TOKEN", 10):
            fehler.append(f"F5: Ablauf-Vorwarnung falsch: {knapp.knappste_frist()} {knapp.stufe_von('E2')}")
        # Die Workflow-Befehle des Prüflings (::error …) landen im Puffer: Ein
        # Selbsttest im CI-Lauf darf nie eine echte Annotation erzeugen.
        with redirect_stdout(io.StringIO()):
            rot = befehl_fristen({"BACKUP_FRIST_TAGE": "10", "BACKUP_FRIST_ZUGANG": "BACKUP_REPO_TOKEN"})
            gelb, ohne = befehl_fristen({"BACKUP_FRIST_TAGE": "20"}), befehl_fristen({})
            kaputt = befehl_fristen({"BACKUP_FRIST_TAGE": "kaputt"})
        if rot != 1:
            fehler.append("F5: --fristen muss unter 14 Tagen rot sein")
        if gelb != 0 or ohne != 0:
            fehler.append("F5: --fristen über 14 Tagen bzw. ohne Ablaufdatum muss grün sein")
        if kaputt != 1:
            fehler.append("F5: ungültiger Fristwert muss rot sein")
        abgelaufen = lauf(voll, repo=(200, {"github-authentication-token-expiration": "2026-10-01 00:00:00 UTC"},
                                      {"private": True}))
        if abgelaufen.stufe_von("E2") != "fehler":
            fehler.append("F5: abgelaufener Zugang muss rot sein")

        # F6: Passphrase-Grenze exakt bei MINDESTLAENGE_E3
        kurz = lauf({**voll, "PASSWORT": "x" * (MINDESTLAENGE_E3 - 1)})
        genau = lauf({**voll, "PASSWORT": "x" * MINDESTLAENGE_E3})
        if kurz.stufe_von("E3") != "fehler" or genau.stufe_von("E3") != "ok":
            fehler.append("F6: Passphrase-Grenze falsch")

        # F7: Konto-eigener Cloudflare-Token (nur /accounts/<id>/tokens/verify) wird anerkannt
        konto_token = lauf(voll, cf_user=(401, {}, {"success": False, "errors": [{"code": 1000, "message": "Invalid"}]}),
                           cf_konto=(200, {}, {"success": True, "result": {"status": "active",
                                                                         "expires_on": "2027-01-01T00:00:00Z"}}))
        if konto_token.stufe_von("E5") != "ok" or "Konto-Token" not in konto_token.befund("E5").text:
            fehler.append("F7: Konto-Token nicht anerkannt")
        # 2026-10-15T12:00Z → 2027-01-01T00:00Z = 77,5 Tage → 77 volle Tage
        if ("CF_KV_BACKUP_TOKEN", 77) not in konto_token.fristen:
            fehler.append(f"F7: Cloudflare-Frist fehlt: {konto_token.fristen}")
        tot = lauf(voll, cf_user=(200, {}, {"success": True, "result": {"status": "expired"}}))
        if tot.stufe_von("E5") != "fehler" or tot.stufe_von("E6") != "fehler":
            fehler.append("F7: abgelaufener Cloudflare-Token muss E5 (und damit E6) rot machen")

        # F8: KV-Rechte fehlen bzw. Namespace falsch → präzise Abhilfe
        k403 = lauf(voll, kv=(403, {}, {"success": False, "errors": [{"code": 10000, "message": "Authentication error"}]}))
        k404 = lauf(voll, kv=(404, {}, {"success": False, "errors": [{"code": 10013, "message": "not found"}]}))
        if "Workers KV Storage: Read" not in k403.befund("E6").abhilfe or \
                "nicht gefunden" not in k404.befund("E6").text:
            fehler.append("F8: KV-403/404 nicht präzise benannt")

        # F9: D1 optional – gesetzt und lesbar = grün, gesetzt ohne Recht = rot
        d1_gut = lauf({**voll, "D1_DATABASE_ID": db})
        d1_rot = lauf({**voll, "D1_DATABASE_ID": db}, d1=(403, {}, {"success": False, "errors": []}))
        if d1_gut.stufe_von("E7") != "ok" or d1_rot.stufe_von("E7") != "fehler":
            fehler.append("F9: D1-Prüfung falsch")
        if "%22d1%22" not in d1_rot.befund("E7").link:
            fehler.append("F9: D1-Abhilfe-Link ohne D1-Leserecht")

        # F10: Environment-Schutz – offen für alle Branches / Pflicht-Freigabe / fremde Branches
        alle = lauf(voll, env=(200, {}, {"protection_rules": [], "deployment_branch_policy": None}))
        pruefer = lauf(voll, env=(200, {}, {"protection_rules": [{"type": "required_reviewers"}],
                                            "deployment_branch_policy": {"protected_branches": True,
                                                                         "custom_branch_policies": False}}))
        fremd = lauf(voll, env_politik=(200, {}, {"branch_policies": [{"name": "main"}, {"name": "arena/*"}]}))
        if not (alle.stufe_von("E8") == pruefer.stufe_von("E8") == fremd.stufe_von("E8") == "warnung"):
            fehler.append("F10: Environment-Hinweise fehlen")
        if alle.offen() or pruefer.offen() or fremd.offen():
            fehler.append("F10: E8 darf die Sicherung nie stoppen (nur Hinweis)")
        # F10b: Lauf-Token ohne „actions: read“ (403) → Rückfall ohne Token liest trotzdem
        ohne_recht = lauf(voll, env_mit_token=(403, {}, {"message": "Resource not accessible by integration"}),
                          env=(200, {}, {"protection_rules": [], "deployment_branch_policy": None}))
        if ohne_recht.stufe_von("E8") != "warnung":
            fehler.append("F10b: Rückfall ohne Token greift nicht")

        # F11: Netzausfall → fail-closed mit „vorübergehend“, drei Versuche
        netz = lauf(voll, repo=(0, {}, None))
        if netz.stufe_von("E2") != "fehler" or "vorübergehend" not in netz.befund("E2").text:
            fehler.append("F11: Netzausfall nicht fail-closed benannt")
        # F11b: Die Wiederholung selbst sitzt in _http (die gefälschte Welt oben
        # ersetzt _http als Ganzes) – deshalb hier direkt an _http geprüft.
        zaehler = []
        try:
            _http_einmal = lambda m, u, k=None, frist=20: (zaehler.append(u) or (503, {}, None, ""))  # noqa: E731
            if _http("GET", "https://x.invalid/")[0] != 503 or len(zaehler) != 3:
                fehler.append(f"F11b: Wiederholung bei 5xx falsch ({len(zaehler)} Versuche)")
        finally:
            _http_einmal = echt_einmal

        # F12: Kein Secret-Wert in Konsole, Annotation, Zusammenfassung, Umgebungsdatei
        with tempfile.TemporaryDirectory() as ordner:
            summary, umg = os.path.join(ordner, "summary.md"), os.path.join(ordner, "env")
            puffer = io.StringIO()
            HTTP = welt(repo=(200, {"github-authentication-token-expiration": "2026-10-20 00:00:00 UTC"},
                              {"private": True}))
            with redirect_stdout(puffer):
                code = befehl_pruefen({**voll, "GITHUB_ACTIONS": "true", "GITHUB_STEP_SUMMARY": summary,
                                       "GITHUB_ENV": umg}, jetzt)
                befehl_pruefen({"GITHUB_ACTIONS": "true", "PASSWORT": "kurz-GIFTWERT",
                                "GITHUB_STEP_SUMMARY": summary, "GITHUB_ENV": umg}, jetzt)
            gesamt = puffer.getvalue() + open(summary, encoding="utf-8").read() + open(umg, encoding="utf-8").read()
            for wert in list(gift.values()) + ["GIFTWERT_LAUF", "kurz-GIFTWERT"]:
                if wert in gesamt:
                    fehler.append("F12: ein Secret-Wert ist in der Ausgabe gelandet")
            if code != 0 or "BACKUP_FRIST_TAGE=4" not in gesamt or "BACKUP_FRIST_ZUGANG=BACKUP_REPO_TOKEN" not in gesamt:
                fehler.append("F12: Frist nicht in die Job-Umgebung exportiert")
            if "::warning title=Backup-Einrichtung E2" not in gesamt or "| **E1**" not in gesamt:
                fehler.append("F12: Annotation oder Zusammenfassung fehlt")

        # F13: Annotationen sind einzeilig und korrekt kodiert
        probe = Ergebnis()
        probe.neu("E9", "Titel: mit, Sonderzeichen", "fehler", "Zeile 1\nZeile 2 100%")
        zeile = annotationen(probe)[0]
        if "\n" in zeile or "Zeile 1%0AZeile 2 100%25" not in zeile or "Titel%3A mit%2C" not in zeile:
            fehler.append(f"F13: Annotation falsch kodiert: {zeile}")

        # F14: Ungültige Formate werden ohne Netzaufruf abgefangen (der Name
        # „ABO“ statt der ID ist der typische Kopierfehler); Quelle = Ziel ist rot.
        aufrufe.clear()
        formate = lauf({**voll, "CF_ACCOUNT_ID": "xyz", "KV_NAMESPACE_ID": "ABO"})
        if [b.kennung for b in formate.offen()] != ["E4", "E6"]:
            fehler.append(f"F14: Formatfehler falsch erkannt: {[b.kennung for b in formate.offen()]}")
        if any("/storage/kv/" in u for u in aufrufe):
            fehler.append("F14: ungültige Namespace-ID wurde trotzdem live abgefragt")
        selbst = lauf({**voll, "ZIEL_REPO": voll["GITHUB_REPOSITORY"].upper()})
        if [b.kennung for b in selbst.offen()] != ["E1", "E2"]:
            fehler.append(f"F14: Quelle = Ziel nicht rot: {[b.kennung for b in selbst.offen()]}")
        archiviert = lauf(voll, repo=(200, {}, {"private": True, "archived": True}))
        if archiviert.stufe_von("E2") != "fehler":
            fehler.append("F14: archiviertes Ziel muss rot sein")

        # F15: Klassischer Token → Warnung, Sicherung läuft trotzdem
        klassisch = lauf({**voll, "ZIEL_TOKEN": "ghp_GIFTWERT_klassisch"})
        if klassisch.stufe_von("E2") != "warnung" or klassisch.offen():
            fehler.append("F15: klassischer Token nicht als Hinweis markiert")

        # F16: Ablauf-Header in mehreren Schreibweisen lesbar
        for roh in ("2027-10-15 07:00:00 UTC", "2027-10-15 07:00:00 +0000", "2027-10-15T07:00:00Z"):
            if gh_ablauf_lesen(roh) != dt.datetime(2027, 10, 15, 7, 0, tzinfo=dt.timezone.utc):
                fehler.append(f"F16: Ablauf-Header nicht lesbar: {roh}")

        # F17: Erst absichern, dann befüllen – die Lage nach dem Merge von #769
        # (Environment ohne Branch-Regel, Zugänge fehlen) stellt E8 nach vorn;
        # eine reine Pflicht-Freigabe oder eine fertige Einrichtung nicht.
        ohne_regel = (200, {}, {"protection_rules": [], "deployment_branch_policy": None})
        teil = {"GITHUB_REPOSITORY": voll["GITHUB_REPOSITORY"], "CF_ACCOUNT_ID": konto}
        offen_env = lauf(teil, env=ohne_regel)
        konsole, summary = konsolen_bericht(offen_env), zusammenfassung(offen_env, "x/y")
        if not (offen_env.environment_offen and offen_env.stufe_von("E8") == "warnung"):
            fehler.append("F17: Environment ohne Branch-Regel nicht als offen erkannt")
        elif not (0 <= konsole.find("Zuerst E8") < konsole.find(" E1 ")) or \
                not (0 <= summary.find("Zuerst E8") < summary.find("| Punkt |")):
            fehler.append("F17: Reihenfolge-Hinweis fehlt oder steht nicht vor der Prüfliste")
        fehlt = lauf(teil, env=(404, {}, {"message": "Not Found"}))
        fremd = lauf(teil, env=(200, {}, {"protection_rules": [], "deployment_branch_policy":
                                          {"protected_branches": False, "custom_branch_policies": True}}),
                     env_politik=(200, {}, {"branch_policies": [{"name": "main"}, {"name": "arena/*"}]}))
        if not (reihenfolge_hinweis(fehlt) and reihenfolge_hinweis(fremd)):
            fehler.append("F17: fehlendes Environment / fremder Branch stellt E8 nicht nach vorn")
        freigabe = lauf(teil, env=(200, {}, {"protection_rules": [{"type": "required_reviewers"}],
                                             "deployment_branch_policy": {"protected_branches": False,
                                                                          "custom_branch_policies": True}}))
        if freigabe.stufe_von("E8") != "warnung" or freigabe.environment_offen or reihenfolge_hinweis(freigabe):
            fehler.append("F17: reine Pflicht-Freigabe darf keinen Reihenfolge-Hinweis auslösen")
        fertig = lauf(voll, env=ohne_regel)
        if fertig.offen() or reihenfolge_hinweis(fertig) or "E8" not in schlusssatz(fertig):
            fehler.append("F17: fertige Einrichtung – E8 gehört in den Schlusssatz, nicht nach vorn")
    finally:
        HTTP, SCHLAF, _http_einmal = echt_http, echt_schlaf, echt_einmal

    if fehler:
        for eintrag in fehler:
            print(f"❌ {eintrag}")
        print(f"🛑 backup_einrichtung-Selbsttest: {len(fehler)} Abweichung(en).")
        return 1
    print("✅ backup_einrichtung-Selbsttest: 17 Fallgruppen – Leerstand (#761), gesunde Einrichtung, "
          "öffentliches Ziel, 401/404, Fristen, Passphrase-Grenze, Konto-Token, KV-/D1-Rechte, "
          "Environment-Schutz, Netzausfall + Wiederholung, keine Secret-Werte in der Ausgabe, Kodierung, "
          "Reihenfolge „erst absichern, dann befüllen“.")
    return 0


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(description=__doc__)
    gruppe = zerleger.add_mutually_exclusive_group(required=True)
    gruppe.add_argument("--pruefen", action="store_true", help="Voraussetzungen prüfen (Exit 1 bei offenem Punkt)")
    gruppe.add_argument("--fristen", action="store_true", help="Ablauf-Vorwarnung (letzter Job-Schritt)")
    gruppe.add_argument("--selftest", action="store_true", help="Selbsttest ohne Netz")
    argumente = zerleger.parse_args(argv)
    if argumente.selftest:
        return selbsttest()
    if argumente.fristen:
        return befehl_fristen()
    return befehl_pruefen()


if __name__ == "__main__":
    sys.exit(main())
