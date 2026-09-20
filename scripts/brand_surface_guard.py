#!/usr/bin/env python3
"""
MARKEN-OBERFLÄCHEN-WACHE – die Außenseite des Repos muss die Marke zeigen
=========================================================================

WARUM ES DIESE DATEI GIBT (20.09.2026)
--------------------------------------
Frank Hartung positioniert sich auf franksfinanzcheck.de als Person mit
über zehn Jahren Praxiserfahrung. Bei einer Markensuche („FranksFinanzcheck
Frank Hartung") standen aber nicht die Expertenseite und der Ratgeber ganz
oben, sondern **GitHub-Seiten dieser Automatik**: 14 öffentliche Releases
(„Automatisches Offsite-Backup … Getrackte Dateien: 2297"), jede mit dem
vollständigen Quellstand als Download, dazu eine Repo-Beschreibung, die
„(Affiliate-Blog, Hugo)" sagte. Das ist keine Kleinigkeit: Suchmaschinen
indexieren Release-Seiten genauso wie README-Seiten, und wer die Marke
prüft, liest dann zuerst „Content-Bot" statt „10 Jahre Erfahrung".

Die Ursache war strukturell, nicht kosmetisch: Die Backup-Automation hat
den vollständigen Bestand **bewusst öffentlich** abgelegt (GitHub-Free
erlaubt Releases ohne Limit). Ein Fix, der nur aufräumt, hält nicht – der
nächste Nachtlauf (03:00 UTC) hätte die Seite wieder aufgebaut. Deshalb
gibt es diese Wache: Sie sieht jeden öffentlichen Ausgang des Repos, heilt
ihn und meldet, was admin-seitig zu tun ist.

WAS SIE PRÜFT (Oberflächen, die von außen sichtbar sind)
--------------------------------------------------------
  · O1 Öffentliche Backup-Spuren            ROT   (Releases → Entwurf, Tags → gelöscht,
                                                    jeweils mit Nachprüfung)
  · O2 README.md als Markenfläche            ROT   (Betriebssprache → Markencheck)
  · O3 Repo-Beschreibung / Homepage / Wiki   GELB  (Admin-Aufgabe, Anleitung im Befund)
  · O4 Repository-Sichtbarkeit (public?)     GELB  (Admin-Aufgabe, größter Hebel)
  · O5 Sonstige öffentliche Releases         INFO  (Marke prüfen, nichts erzwingen)
  · O6 Öffentliche Issue-Titel               GELB  (Betriebssprache ist auffindbar)

REGELN (Hausordnung)
--------------------
  · Heilung ohne Beweis ist keine Heilung: `--fix` schreibt nur, und liest
    danach zurück. Erst die Nachprüfung entscheidet (belegt/halb/heilbar).
  · Ein Detektor, der blind sein darf, ist keine Wache: `--selftest` führt
    belegte Fälle durch dieselben Funktionen – inklusive eines Falls, in dem
    die Heilung NICHT greift (dann bleibt es rot).
  · Netz ist nicht Vertrag (Alarm-Routing-Grundsatz, #272): Ist die API nicht
    erreichbar, meldet die Wache „nicht prüfbar" als ::warning:: und bleibt
    grün – außer `--strict`, das ist der Audit-Modus.
  · Eine Markenfläche darf über die Marke reden, nicht über die Maschine.
    Die Verbotsliste unten ist Betriebs-, nicht Alltagssprache; Ausnahmen
    stehen mit Begründung in `data/brand_surface_allowlist.txt`.

Nutzung
-------
    python3 scripts/brand_surface_guard.py --selftest     # Beweis, kein Netz, schreibt nie
    python3 scripts/brand_surface_guard.py --gate         # Tageslauf (Standard)
    python3 scripts/brand_surface_guard.py --fix          # heilt O1 (öffentliche Backups → Entwurf)
    python3 scripts/brand_surface_guard.py --fix --gate   # heilen und nachprüfen
    python3 scripts/brand_surface_guard.py --only readme  # nur eine Oberfläche
    python3 scripts/brand_surface_guard.py --json         # Maschinenlesbarer Befund
    python3 scripts/brand_surface_guard.py --offline --snapshot fall.json   # ohne Netz (Fixtures)

Umgebung: GH_TOKEN/GITHUB_TOKEN (Lesen; Schreiben nur für --fix),
GITHUB_REPOSITORY (owner/repo), GITHUB_STEP_SUMMARY (Kurzbericht).

Exit-Codes: 0 = grün oder nur GELB/INFO (inkl. „nicht prüfbar" ohne --strict)
            1 = ROT: öffentliche Betriebsfläche oder Markenfläche verletzt
            2 = Werkzeugfehler (Snapshot defekt, Aufruffehler, Selbsttest rot)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.github.com"
README_PFAD = os.path.join(HIER, "README.md")
ALLOWLIST_PFAD = os.path.join(HIER, "data", "brand_surface_allowlist.txt")

# ---------------------------------------------------------------
#  Betriebssprache: Begriffe, die auf einer Markenfläche (README,
#  Repo-Beschreibung, öffentlicher Release-Titel) nichts zu suchen
#  haben. Bewusst konservativ – geprüft wird nur die Außenseite,
#  interne Dokumente unter docs/ bleiben davon unberührt.
# ---------------------------------------------------------------
VERBOTEN: list[tuple[str, str]] = [
    (r"\bBots?\b", "Bot-Sprache"),
    (r"Autopilot", "Autopilot-Sprache"),
    (r"Automatik|automatisier\w*|Vollautomatik", "Automatik-Sprache"),
    (r"\bEngine\b", "Engine-Sprache"),
    (r"\bGates?\b|Publish-Gate|Quality-Gate|Gate-Komplex", "Gate-Sprache"),
    (r"\bWorkflows?\b", "Workflow-Sprache"),
    (r"GitHub Actions", "CI-Sprache"),
    (r"\bCron\b|cronjob", "Zeitplan-Sprache"),
    (r"Kadenz", "Kadenz-Sprache"),
    (r"\bSecrets?\b|\bTokens?\b|API-Key", "Zugangsdaten-Sprache"),
    (r"\bPipeline\b", "Pipeline-Sprache"),
    (r"\bAGC\b|Brand Brain", "Studio-Sprache"),
    (r"KI-Redaktion|Redaktions-KI", "KI-Redaktions-Sprache"),
    (r"publish_gate|quality_score|cadence|pin_queue|themenpool|topics\.yaml",
     "interne Werkzeugnamen"),
    (r"scripts/|\.ya?ml\b|\.py\b", "interne Dateipfade"),
    (r"Affiliate-Blog|Affiliate-Partner|Affiliate-Netzwerk",
     "Affiliate statt Experten-Positionierung"),
    (r"Scaled Content Abuse|Spam-Risiko", "Spam-/Risiko-Sprache"),
    # „Provision" (Singular) bleibt erlaubt: der Werbehinweis der Website nennt ihn
    # selbst – Ehrlichkeit ist Markenkern, Umsatz-Sprech ist keiner.
    (r"Monetarisierung|\bUmsatz\b|Revenue|Einnahmequellen|Werbeerlöse", "Umsatz-Sprache"),
    (r"\bSEO\b|Backlink\w*", "SEO-Betriebssprache"),
    (r"Plagiat|Duplicate-Guard", "Guard-Sprache"),
]

# Release-Erkennung: ein Backup ist ein Backup, egal wie es heißt.
BACKUP_TAG = re.compile(r"^backup[-_]?\d", re.IGNORECASE)
BACKUP_ASSET = re.compile(r"(backup\.bundle|worktree\.zip|\.bundle$|\.zip\.enc$|\.bundle\.enc$)",
                          re.IGNORECASE)
BACKUP_WORT = re.compile(r"backup", re.IGNORECASE)

RUNBOOK = "docs/MARKEN-OBERFLAECHE-RUNBOOK.md"


# =====================================================================
#  Befund-Modell
# =====================================================================
class Befund:
    """Ein einzelner Tatbestand auf einer öffentlichen Oberfläche."""

    def __init__(self, oberflaeche: str, stufe: str, text: str, detail: str = "",
                 reparatur: str = ""):
        self.oberflaeche = oberflaeche
        self.stufe = stufe          # ROT | GELB | INFO
        self.text = text
        self.detail = detail
        self.reparatur = reparatur

    def als_dict(self) -> dict:
        return {
            "oberflaeche": self.oberflaeche,
            "stufe": self.stufe,
            "text": self.text,
            "detail": self.detail,
            "reparatur": self.reparatur,
        }


def _kodiere(text: str, marke: str) -> str:
    """Markiert die Fundstelle für den Log lesbar (keine Farben, nur Zeichen)."""
    return text.replace(marke, f"[{marke}]", 1)


def _erlaubt(zeile: str, treffer: re.Match, allowlist: list[str]) -> bool:
    """Allowlist-Freigabe mit Begründung: greift nur, wenn die Ausnahme die
    Fundstelle wirklich überdeckt (z. B. „Content-Bot" überdeckt „Bot")."""
    for ausnahme in allowlist:
        umfeld = re.search(ausnahme, zeile, flags=re.IGNORECASE)
        if umfeld and umfeld.start() <= treffer.start() and umfeld.end() >= treffer.end():
            return True
    return False


def pruefe_text(text: str, quelle: str, oberflaeche: str,
                allowlist: list[str]) -> list[Befund]:
    """Sucht Betriebssprache in einem Außentext (zeilenweise, mit Zeilennummer)."""
    befunde: list[Befund] = []
    for nr, zeile in enumerate(text.splitlines(), start=1):
        for muster, warum in VERBOTEN:
            treffer = re.search(muster, zeile, flags=re.IGNORECASE)
            if not treffer:
                continue
            wort = treffer.group(0)
            if _erlaubt(zeile, treffer, allowlist):
                continue
            befunde.append(Befund(
                oberflaeche=oberflaeche,
                stufe="ROT" if oberflaeche == "O2 README (Markenfläche)" else "GELB",
                text=f"{quelle}:{nr} – „{wort}“",
                detail=f"{warum} · Zeile: {_kodiere(zeile.strip()[:160], wort)}",
            ))
    return befunde


def pruefe_readme(pfad: str, allowlist: list[str]) -> list[Befund]:
    if not os.path.exists(pfad):
        return []
    with open(pfad, encoding="utf-8") as datei:
        return pruefe_text(datei.read(), "README.md", "O2 README (Markenfläche)", allowlist)


def pruefe_releases(releases: list[dict]) -> tuple[list[Befund], list[Befund]]:
    """Trennt öffentliche Backup-Releases (ROT) von sonstigen Releases (INFO)."""
    rot: list[Befund] = []
    info: list[Befund] = []
    for rel in releases:
        tag = (rel.get("tag_name") or "").strip()
        name = (rel.get("name") or "").strip()
        assets = [a.get("name") or "" for a in (rel.get("assets") or [])]
        if rel.get("draft"):
            continue  # Entwürfe sind privat – genau das ist das Ziel
        stichhaltig = (
            BACKUP_TAG.match(tag)
            or any(BACKUP_ASSET.search(a) for a in assets)
            or (BACKUP_WORT.search(name) and bool(assets))
        )
        if stichhaltig:
            rot.append(Befund(
                oberflaeche="O1 Öffentliche Backup-Releases",
                stufe="ROT",
                text=f"Release „{tag}“ ist öffentlich lesbar ({len(assets)} Asset(s))",
                detail="Assets: " + (", ".join(assets) or "keine") +
                       " · Quelle: api.github.com (GET /releases)",
                reparatur="--fix stuft es auf ENTWURF zurück (privat) und prüft nach",
            ))
        else:
            info.append(Befund(
                oberflaeche="O5 Sonstige öffentliche Releases",
                stufe="INFO",
                text=f"Release „{tag}“ ist öffentlich ({len(assets)} Asset(s))",
                detail="Markenprüfung empfohlen, kein Automatik-Eingriff",
            ))
    return rot, info


def pruefe_tags(tags: list[dict]) -> list[Befund]:
    """Git-Tags sind ohne Login sichtbar (github.com/<repo>/tags) – ein Tag
    „backup-20260920-0809" erzählt die Nachtlauf-Geschichte weiter, auch wenn
    das Release selbst längst privat ist."""
    befunde: list[Befund] = []
    for tag in tags:
        name = (tag.get("name") or "").strip()
        if BACKUP_TAG.match(name):
            befunde.append(Befund(
                oberflaeche="O1 Öffentliche Backup-Tags",
                stufe="ROT",
                text=f"Tag „{name}“ ist öffentlich sichtbar",
                detail="Quelle: api.github.com (GET /tags) · "
                       "Inhalt (der Commit) liegt ohnehin in main",
                reparatur="--fix löscht die Tag-Referenz (kein Inhaltsverlust) und prüft nach",
            ))
    return befunde


def heile_tags(api, tags: list[dict]) -> tuple[list[str], list[str]]:
    """Löscht öffentliche Backup-Tag-Referenzen – erst löschen, dann nachzählen."""
    kandidaten = [t.get("name") for t in tags if BACKUP_TAG.match((t.get("name") or "").strip())]
    if not kandidaten:
        return [], []
    geheilt: list[str] = []
    for name in kandidaten:
        try:
            api.tag_loeschen(name)
        except Exception as fehler:  # noqa: BLE001
            geheilt.append(f"{name}: Löschung fehlgeschlagen ({fehler}) – bleibt sichtbar")
    nach = [ (t.get("name") or "") for t in (api.tags() or []) ]
    offen = [n for n in kandidaten if n in nach]
    for name in kandidaten:
        if name not in offen:
            geheilt.append(f"{name} → Tag gelöscht (nachgezählt: nicht mehr vorhanden)")
    return geheilt, offen


def pruefe_repo(repo: dict) -> list[Befund]:
    """Repo-Kopfdaten: Beschreibung, Homepage, Wiki, Sichtbarkeit (+ Themen)."""
    befunde: list[Befund] = []
    sichtbar = not repo.get("private", False)
    if sichtbar:
        befunde.append(Befund(
            oberflaeche="O4 Repository-Sichtbarkeit",
            stufe="GELB",
            text="Repository ist öffentlich – Betriebsdokumentation und Commit-Titel "
                 "sind Teil der Markensuche",
            detail="Admin-Aufgabe (kein Token-Recht in der Automatik)",
            reparatur=f"Anleitung & Befehle: {RUNBOOK} (Abschnitt „Repository privat stellen“)",
        ))

    beschreibung = (repo.get("description") or "").strip()
    for muster, warum in VERBOTEN:
        treffer = re.search(muster, beschreibung, flags=re.IGNORECASE)
        if treffer:
            befunde.append(Befund(
                oberflaeche="O3 Repo-Beschreibung",
                stufe="GELB",
                text=f"Beschreibung enthält Betriebssprache: „{treffer.group(0)}“",
                detail=f"{warum} · ist: {beschreibung[:160]}",
                reparatur='gh api -X PATCH repos/{owner}/{repo} '
                          '-f description="FranksFinanzcheck – unabhängiger '
                          'Finanz-Ratgeber von Frank Hartung"'
                          f" · Textvorschlag im {RUNBOOK}",
            ))
            break

    if not (repo.get("homepage") or "").strip():
        befunde.append(Befund(
            oberflaeche="O3 Repo-Kopf",
            stufe="GELB",
            text="Keine Homepage-URL gesetzt – der Ratgeber wird nicht verlinkt",
            detail="stattdessen verlinkt der Repo-Kopf nur Quellcode",
            reparatur='gh api -X PATCH repos/{owner}/{repo} '
                     '-f homepage="https://franksfinanzcheck.de/"',
        ))

    if repo.get("has_wiki"):
        befunde.append(Befund(
            oberflaeche="O3 Wiki",
            stufe="GELB",
            text="Wiki ist aktiviert – eine zweite, ungepflegte öffentliche Textfläche",
            detail="Markenflächen sollen eine Quelle haben",
            reparatur="gh api -X PATCH repos/{owner}/{repo} -F has_wiki=false",
        ))

    for thema in (repo.get("topics") or []):
        for muster, warum in VERBOTEN:
            if re.search(muster, thema, flags=re.IGNORECASE):
                befunde.append(Befund(
                    oberflaeche="O3 Repository-Themen",
                    stufe="GELB",
                    text=f"Thema „{thema}“ ist Betriebssprache ({warum})",
                    detail="Themen erscheinen in der Repo-Kopfzeile und in der Suche",
                    reparatur="gh api -X PUT repos/{owner}/{repo}/topics",
                ))
                break
    return befunde


def pruefe_issue_titel(issues: list[dict], grenze: int = 5) -> list[Befund]:
    befunde: list[Befund] = []
    for issue in issues:
        if "pull_request" in issue:
            continue
        titel = (issue.get("title") or "").strip()
        for muster, warum in VERBOTEN:
            treffer = re.search(muster, titel, flags=re.IGNORECASE)
            if treffer:
                befunde.append(Befund(
                    oberflaeche="O6 Öffentliche Issue-Titel",
                    stufe="GELB",
                    text=f"Issue #{issue.get('number')}: „{titel[:110]}“",
                    detail=f"{warum} – Titel sind öffentlich und werden indexiert",
                    reparatur="Titel neutral fassen oder Issues erst nach der "
                              "Privatstellung weiterführen",
                ))
                break
        if len(befunde) >= grenze:
            break
    return befunde


# =====================================================================
#  API-Zugriff (klein, prüfbar, ohne Fremdbibliotheken)
# =====================================================================
class Api:
    """Dünne Hülle um die GitHub-REST-API – genau die vier Aufrufe, die es braucht."""

    def __init__(self, repo: str, token: str = "", timeout: int = 30):
        self.repo = repo
        self.token = token
        self.timeout = timeout

    def ruf(self, pfad: str, methode: str = "GET", daten: dict | None = None):
        koerper = json.dumps(daten).encode() if daten is not None else None
        anfrage = urllib.request.Request(API + pfad, data=koerper, method=methode)
        anfrage.add_header("Accept", "application/vnd.github+json")
        anfrage.add_header("X-GitHub-Api-Version", "2022-11-28")
        anfrage.add_header("User-Agent", "brand-surface-guard")
        if self.token:
            anfrage.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(anfrage, timeout=self.timeout) as antwort:
            rohtext = antwort.read().decode("utf-8", "replace")
        return json.loads(rohtext) if rohtext.strip() else {}

    def repo_daten(self) -> dict:
        return self.ruf(f"/repos/{self.repo}")

    def releases(self) -> list:
        daten = self.ruf(f"/repos/{self.repo}/releases?per_page=100")
        return daten if isinstance(daten, list) else []

    def release_entwurf(self, release_id: int) -> str:
        """Stuft ein Release auf Entwurf zurück (privat) – und liest zurück."""
        self.ruf(f"/repos/{self.repo}/releases/{release_id}", "PATCH", {"draft": True})
        nach = self.ruf(f"/repos/{self.repo}/releases/{release_id}")
        return "privat" if nach.get("draft") else "noch-öffentlich"

    def tags(self) -> list:
        daten = self.ruf(f"/repos/{self.repo}/tags?per_page=100")
        return daten if isinstance(daten, list) else []

    def tag_loeschen(self, name: str) -> None:
        self.ruf(f"/repos/{self.repo}/git/refs/tags/{name}", "DELETE")

    def offene_issues(self) -> list:
        daten = self.ruf(f"/repos/{self.repo}/issues?state=open&per_page=50")
        return daten if isinstance(daten, list) else []


# =====================================================================
#  Heilung (nur O1 – alles andere ist Admin-Aufgabe)
# =====================================================================
def heile_releases(api, releases: list[dict]) -> tuple[list[str], list[str]]:
    """Stuft öffentliche Backup-Releases auf Entwurf zurück; gibt (geheilt, offen)
    zurück – nachgeprüft, nicht behauptet."""
    geheilt, offen = [], []
    for rel in releases:
        tag = (rel.get("tag_name") or "").strip()
        assets = [a.get("name") or "" for a in (rel.get("assets") or [])]
        if rel.get("draft"):
            continue
        stichhaltig = (
            BACKUP_TAG.match(tag)
            or any(BACKUP_ASSET.search(a) for a in assets)
            or (BACKUP_WORT.search((rel.get("name") or "")) and bool(assets))
        )
        if not stichhaltig:
            continue
        try:
            zustand = api.release_entwurf(rel.get("id"))
        except Exception as fehler:  # noqa: BLE001 – Fehler wird als Befund geführt
            offen.append(f"{tag}: Heilung fehlgeschlagen ({fehler})")
            continue
        if zustand == "privat":
            geheilt.append(f"{tag} → Entwurf (nachgeprüft: draft=true)")
        else:
            offen.append(f"{tag}: Nachprüfung meldet „{zustand}“ – Heilung ungültig")
    return geheilt, offen


def lies_allowlist(pfad: str = ALLOWLIST_PFAD) -> list[str]:
    """Ausnahmen mit Begründung: eine Regex pro Zeile, # startet einen Kommentar."""
    if not os.path.exists(pfad):
        return []
    ausnahmen: list[str] = []
    with open(pfad, encoding="utf-8") as datei:
        for zeile in datei:
            zeile = zeile.split("#", 1)[0].strip()
            if zeile:
                ausnahmen.append(zeile)
    return ausnahmen


# =====================================================================
#  Bericht
# =====================================================================
MAX_JE_OBERFLAECHE = 15     # Lesbarkeit: ein Befund ist eine Zeile, kein Roman


def bericht(befunde: list[Befund], geheilt: list[str], offen: list[str],
            hinweise: list[str]) -> str:
    zeilen = ["# Marken-Oberfläche – Befund", ""]
    for stufe in ("ROT", "GELB", "INFO"):
        gruppe = [b for b in befunde if b.stufe == stufe]
        if not gruppe:
            continue
        zeichen = {"ROT": "🔴", "GELB": "🟡", "INFO": "ℹ️"}[stufe]
        zeilen.append(f"## {zeichen} {stufe} ({len(gruppe)})")
        gezeigt: dict[str, int] = {}
        for b in gruppe:
            gezeigt[b.oberflaeche] = gezeigt.get(b.oberflaeche, 0) + 1
            if gezeigt[b.oberflaeche] > MAX_JE_OBERFLAECHE:
                continue
            zeilen.append(f"- **{b.oberflaeche}** – {b.text}")
            if b.detail:
                zeilen.append(f"  - {b.detail}")
            if b.reparatur and stufe != "INFO":
                zeilen.append(f"  - Reparatur: {b.reparatur}")
        for oberflaeche, anzahl in sorted(gezeigt.items()):
            if anzahl > MAX_JE_OBERFLAECHE:
                zeilen.append(f"- … und {anzahl - MAX_JE_OBERFLAECHE} weitere Befunde "
                              f"auf {oberflaeche} (vollständig mit --json)")
        zeilen.append("")
    if geheilt:
        zeilen.append("## ✅ Geheilt (nachgeprüft)")
        zeilen.extend(f"- {g}" for g in geheilt)
        zeilen.append("")
    if offen:
        zeilen.append("## 🛑 Heilung nicht belegt")
        zeilen.extend(f"- {o}" for o in offen)
        zeilen.append("")
    if hinweise:
        zeilen.append("## Hinweise")
        zeilen.extend(f"- {h}" for h in hinweise)
        zeilen.append("")
    return "\n".join(zeilen).rstrip() + "\n"


def kurzfassung(befunde: list[Befund]) -> str:
    rot = sum(1 for b in befunde if b.stufe == "ROT")
    gelb = sum(1 for b in befunde if b.stufe == "GELB")
    info = sum(1 for b in befunde if b.stufe == "INFO")
    return f"ROT={rot} · GELB={gelb} · INFO={info}"


# =====================================================================
#  Selbsttest – der Beweis, dass der Detektor sieht (und die Heilung belegt)
# =====================================================================
class FakeApi:
    """Stub für den Selbsttest: antwortet vorgegeben, ohne Netz."""

    def __init__(self, verhalten: str = "normal", tags: list | None = None):
        self.verhalten = verhalten
        self.schreibvorgaenge: list[int] = []
        self.tagbestand = [t.get("name") for t in (tags or [])]

    def tag_loeschen(self, name: str) -> None:
        self.tagbestand = [t for t in self.tagbestand if t != name]

    def tags(self) -> list:
        return [{"name": n} for n in self.tagbestand]

    def release_entwurf(self, release_id: int) -> str:
        self.schreibvorgaenge.append(release_id)
        if self.verhalten == "taub":
            return "noch-öffentlich"     # API nimmt den Auftrag nicht an
        if self.verhalten == "fehler":
            raise RuntimeError("403 Resource not accessible by integration")
        return "privat"


def selftest() -> int:
    fehler: list[str] = []
    stub = FakeApi()
    stub_taub = FakeApi("taub")
    stub_fehler = FakeApi("fehler")

    oeffentlich = [
        {"id": 1, "tag_name": "backup-20260920-0809", "name": "Backup backup-20260920-0809",
         "draft": False, "assets": [{"name": "backup.bundle"}, {"name": "worktree.zip"}]},
        {"id": 2, "tag_name": "backup-20260919-0741", "name": "Backup backup-20260919-0741",
         "draft": True, "assets": [{"name": "backup.bundle"}]},
        {"id": 3, "tag_name": "pinterest-video-strom-sparen-20260828",
         "name": "Strom sparen – Pinterest Video", "draft": False, "assets": []},
        {"id": 4, "tag_name": "v1.2-archiv", "name": "Quellstand",
         "draft": False, "assets": [{"name": "worktree.zip"}]},
    ]
    rot, info = pruefe_releases(oeffentlich)
    if [b.text for b in rot] != [
        "Release „backup-20260920-0809“ ist öffentlich lesbar (2 Asset(s))",
        "Release „v1.2-archiv“ ist öffentlich lesbar (1 Asset(s))",
    ]:
        fehler.append(f"F1: öffentliche Backups nicht erkannt: {[b.text for b in rot]}")
    if len(info) != 1 or "pinterest-video" not in info[0].text:
        fehler.append(f"F2: sonstiges Release falsch einsortiert: {[b.text for b in info]}")
    if any("backup-20260919-0741" in b.text for b in rot + info):
        fehler.append("F3: Entwurf (privat) wurde als Befund gemeldet")

    geheilt, offen = heile_releases(stub, oeffentlich)
    if len(geheilt) != 2 or offen:
        fehler.append(f"F4: Heilung falsch: geheilt={geheilt} offen={offen}")
    if stub.schreibvorgaenge != [1, 4]:
        fehler.append(f"F4b: falsche Schreibziele: {stub.schreibvorgaenge}")

    geheilt_taub, offen_taub = heile_releases(stub_taub, oeffentlich)
    if geheilt_taub or len(offen_taub) != 2:
        fehler.append(f"F5: blinde Heilung wurde als Erfolg gemeldet: {geheilt_taub}")

    geheilt_fehler, offen_fehler = heile_releases(stub_fehler, oeffentlich)
    if geheilt_fehler or len(offen_fehler) != 2 or "fehlgeschlagen" not in offen_fehler[0]:
        fehler.append(f"F5b: API-Fehler nicht als offener Befund geführt: {offen_fehler}")

    marken_text = (
        "# FranksFinanzcheck\n\n"
        "Unabhängiger Finanz-Ratgeber von Frank Hartung: Strom, Gas, DSL,\n"
        "Versicherungen und Sparen – mit konkreten Euro-Beträgen.\n"
    )
    if pruefe_text(marken_text, "README.md", "O2 README (Markenfläche)", []):
        fehler.append("F6: saubere Markenfläche wurde beanstandet")

    betrieb_text = (
        "# FranksFinanzcheck – Hugo Affiliate-Blog (CHECK24)\n"
        "Der Content-Bot veröffentlicht automatisch Mo/Mi/Fr.\n"
        "Details: docs/CADENCE-REPORT.md und scripts/publish.py\n"
    )
    funde = pruefe_text(betrieb_text, "README.md", "O2 README (Markenfläche)", [])
    if not funde or not all(f.stufe == "ROT" for f in funde):
        fehler.append(f"F7: Betriebssprache im README nicht erkannt: {[f.text for f in funde]}")
    if not any("Affiliate-Blog" in f.text for f in funde):
        fehler.append("F7b: Framing „Affiliate-Blog“ nicht erkannt")
    if not any("README.md:2" == f.text.split(" – ")[0] for f in funde):
        fehler.append(f"F7c: Zeilennummer fehlt/falsch: {[f.text for f in funde]}")

    funde_erlaubt = pruefe_text("Der Content-Bot ist erlaubt.\n", "x", "O2 README (Markenfläche)",
                                [r"Content-Bot"])
    if funde_erlaubt:
        fehler.append(f"F8: Allowlist wirkungslos: {[f.text for f in funde_erlaubt]}")

    repo_befunde = pruefe_repo({"private": False, "has_wiki": True, "homepage": "",
                                "description": "FranksFinanzcheck – Geld sparen & Frugalismus "
                                               "(Affiliate-Blog, Hugo)",
                                "topics": ["finanzen", "content-bot"]})
    oberflaechen = {b.oberflaeche for b in repo_befunde}
    if not {"O4 Repository-Sichtbarkeit", "O3 Repo-Beschreibung", "O3 Repo-Kopf",
            "O3 Wiki", "O3 Repository-Themen"} <= oberflaechen:
        fehler.append(f"F9: Repo-Kopfdaten unvollständig geprüft: {sorted(oberflaechen)}")
    if any(b.stufe == "ROT" for b in repo_befunde):
        fehler.append("F9b: Admin-Aufgaben dürfen nicht rot werden (Dauer-Alarm)")

    privat = pruefe_repo({"private": True, "has_wiki": False,
                          "homepage": "https://franksfinanzcheck.de/",
                          "description": "Unabhängiger Finanz-Ratgeber von Frank Hartung.",
                          "topics": ["finanzen", "geld-sparen"]})
    if privat:
        fehler.append(f"F10: sauberer Repo-Kopf wurde beanstandet: {[b.text for b in privat]}")

    titel = pruefe_issue_titel([
        {"number": 7, "title": "Content-Bot hängt seit heute Nacht"},
        {"number": 8, "title": "Strompreis-Artikel aktualisieren"},
        {"number": 9, "title": "Fix: Publish-Gate blockiert", "pull_request": {}},
    ])
    if len(titel) != 1 or "#7" not in titel[0].text:
        fehler.append(f"F11: Issue-Titel falsch bewertet: {[b.text for b in titel]}")

    if kurzfassung(oeffentlich_befunde := rot + info) != "ROT=2 · GELB=0 · INFO=1":
        fehler.append(f"F12: Kurzfassung falsch: {kurzfassung(oeffentlich_befunde)}")

    tagbefund = pruefe_tags([
        {"name": "backup-20260920-0809"},
        {"name": "retention-pinterest-video-20260828"},
        {"name": "v1.0"},
    ])
    if len(tagbefund) != 1 or "backup-20260920-0809" not in tagbefund[0].text:
        fehler.append(f"F13: Backup-Tag nicht erkannt: {[b.text for b in tagbefund]}")

    tagstub = FakeApi(tags=[{"name": "backup-20260920-0809"}, {"name": "v1.0"}])
    tag_geheilt, tag_offen = heile_tags(tagstub, [{"name": "backup-20260920-0809"},
                                                  {"name": "v1.0"}])
    if tag_offen or len(tag_geheilt) != 1 or "nicht mehr vorhanden" not in tag_geheilt[0]:
        fehler.append(f"F14: Tag-Heilung ohne belastende Nachzählung: {tag_geheilt} / {tag_offen}")
    if tagstub.tagbestand != ["v1.0"]:
        fehler.append(f"F14b: falscher Tag-Bestand nach Heilung: {tagstub.tagbestand}")

    if fehler:
        print("🛑 Selbsttest der Marken-Oberflächen-Wache FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   · {f}")
        return 2
    print("✅ Selbsttest: 14 Fallgruppen bestanden "
          "(Erkennung, Entwurfs- und Tag-Heilung mit Nachprüfung, blinder Detektor, "
          "Markenfläche, Allowlist, Repo-Kopf, Issue-Titel).")
    return 0


# =====================================================================
#  Hauptlauf
# =====================================================================
def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        description="Marken-Oberflächen-Wache (öffentliche Sichtbarkeit des Repos)")
    zerleger.add_argument("--gate", action="store_true", help="Standardlauf (prüfen)")
    zerleger.add_argument("--fix", action="store_true",
                          help="öffentliche Backup-Releases auf Entwurf zurückstufen")
    zerleger.add_argument("--selftest", action="store_true", help="Logik-Beweis ohne Netz")
    zerleger.add_argument("--json", action="store_true", help="Befund als JSON")
    zerleger.add_argument("--offline", action="store_true", help="kein Netz-Zugriff")
    zerleger.add_argument("--strict", action="store_true",
                          help="auch „nicht prüfbar“ und unbestätigte Heilung sind Exit 1")
    zerleger.add_argument("--snapshot", help="JSON-Datei mit Fixtures "
                                             "(repo/releases/issues) für --offline")
    zerleger.add_argument("--only", choices=["releases", "readme", "repo", "issues"],
                          help="nur eine Oberfläche prüfen")
    args = zerleger.parse_args(argv)

    if args.selftest:
        return selftest()

    repo = os.environ.get("GITHUB_REPOSITORY", "frank-hartung/franksfinanzcheck-blog")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""

    # ---- Fixtures (offline) einlesen ----
    fixture: dict = {}
    if args.snapshot:
        try:
            with open(args.snapshot, encoding="utf-8") as datei:
                fixture = json.load(datei)
        except Exception as fehler:  # noqa: BLE001
            print(f"::error::Snapshot {args.snapshot} ist nicht lesbar: {fehler}")
            return 2

    allowlist = lies_allowlist()
    befunde: list[Befund] = []
    hinweise: list[str] = []
    geheilt: list[str] = []
    offen: list[str] = []

    api = None
    api_fehler = ""
    if not args.offline:
        api = Api(repo, token)
        try:
            api.repo_daten()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError,
                ValueError) as fehler:
            api_fehler = f"{type(fehler).__name__}: {fehler}"

    def hole(name: str, ruf):
        """API-Aufruf mit sauberem Fehlerpfad: ein Schluckauf wird Befund, nie Absturz."""
        if args.offline or api is None:
            return fixture.get(name)
        if api_fehler:
            return None
        try:
            return ruf()
        except Exception as fehler:  # noqa: BLE001
            hinweise.append(f"{name}: nicht abrufbar ({type(fehler).__name__}: {fehler})")
            return None

    # ---- O2 README (immer lokal prüfbar, auch offline) ----
    if args.only in (None, "readme"):
        befunde += pruefe_readme(README_PFAD, allowlist)

    # ---- O1/O5 Releases ----
    releases = None
    tags = None
    if args.only in (None, "releases"):
        releases = hole("releases", api.releases) if api else fixture.get("releases")
        if releases is None and not args.snapshot:
            hinweise.append("Releases: nicht abrufbar – O1/O5 nicht geprüft (nicht prüfbar)")
        elif releases is not None:
            if args.fix:
                if args.offline:
                    hinweise.append("--fix im Offline-Modus: keine Schreibvorgänge")
                else:
                    geheilt, offen = heile_releases(api, releases)
                    releases = hole("releases", api.releases) or releases
            rot, info = pruefe_releases(releases)
            befunde += rot + info
            if args.fix and not args.offline:
                if rot:
                    for b in rot:
                        offen.append(f"{b.text} – nach der Heilung weiterhin öffentlich")
                if geheilt:
                    hinweise.append(f"{len(geheilt)} Backup-Release(s) auf Entwurf gestuft "
                                    "(privat, Assets erhalten, jederzeit wieder veröffentlichbar)")

        tags = hole("tags", api.tags) if api else fixture.get("tags")
        if tags is not None:
            if args.fix and not args.offline:
                tag_geheilt, tag_offen = heile_tags(api, tags)
                geheilt += tag_geheilt
                offen += [f"{n}: Tag weiterhin öffentlich" for n in tag_offen]
                tags = hole("tags", api.tags) or tags
            befunde += pruefe_tags(tags)
        elif not args.snapshot:
            hinweise.append("Tags: nicht abrufbar – O1 (Tags) nicht geprüft (nicht prüfbar)")

    # ---- O3/O4 Repo-Kopf ----
    if args.only in (None, "repo"):
        repodaten = fixture.get("repo") if args.offline else hole("repo", api.repo_daten)
        if repodaten:
            befunde += pruefe_repo(repodaten)
        else:
            hinweise.append("Repo-Kopfdaten: nicht abrufbar – O3/O4 nicht geprüft (nicht prüfbar)")

    # ---- O6 öffentliche Issue-Titel ----
    if args.only in (None, "issues"):
        issues = fixture.get("issues") if args.offline else hole("issues", api.offene_issues)
        if issues:
            befunde += pruefe_issue_titel(issues)

    # ---- Nicht prüfbar? ----
    if api_fehler and not args.offline:
        meldung = ("Marken-Oberfläche: GitHub-API nicht erreichbar – Netz-Probe nicht möglich "
                   f"({api_fehler}). Freigabe: nur, weil Netz kein Vertrag ist (#272).")
        print(f"::warning::{meldung}")
        hinweise.append(meldung)
        if args.strict:
            print("::error::--strict: „nicht prüfbar“ gilt als Befund.")
            return 1

    text = bericht(befunde, geheilt, offen, hinweise)
    # Bericht und Maschinenausgabe trennen: mit --json bleibt stdout reines JSON.
    print(text, file=sys.stderr if args.json else sys.stdout)
    if args.json:
        print(json.dumps({
            "repo": repo,
            "stand": "live" if not args.offline else "offline",
            "befunde": [b.als_dict() for b in befunde],
            "geheilt": geheilt,
            "offen": offen,
            "hinweise": hinweise,
        }, ensure_ascii=False, indent=2))

    schritt = os.environ.get("GITHUB_STEP_SUMMARY")
    if schritt:
        try:
            with open(schritt, "a", encoding="utf-8") as datei:
                datei.write(text)
        except OSError:
            pass

    rot = [b for b in befunde if b.stufe == "ROT"]
    melde = (lambda t: print(t, file=sys.stderr)) if args.json else print
    melde(f"Urteil: {kurzfassung(befunde)}")
    if rot:
        for b in rot[:20]:
            melde(f"::error::{b.oberflaeche}: {b.text}")
        if len(rot) > 20:
            melde(f"::error::… und {len(rot) - 20} weitere ROT-Befunde (vollständig mit --json)")
        melde("🛑 Öffentliche Betriebsfläche gefunden – Markenfläche verletzt (Exit 1).")
        return 1
    if offen:
        melde("::error::Heilung nicht belegt – " + "; ".join(offen))
        return 1
    melde("✅ Markenfläche sauber (GELB = Admin-Aufgabe, siehe Runbook).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
