#!/usr/bin/env python3
# ============================================================
#  BACKUP-FRESHNESS-GUARD – Offsite-Sicherung ist aktuell
#  ------------------------------------------------------------
#  WARUM (Highend-Ergänzung zu WF-9E5A / #761, 22.10.2026):
#    `backup_einrichtung.py` (E1–E8) prüft, OB die Sicherung
#    funktionieren KANN – also ob alle Zugänge vorhanden und gültig sind.
#    Sie prüft nicht, ob sie JÜNGST wirklich gelaufen ist. Wäre der
#    tägliche Cron ausgesetzt (Scheduler-Hänger, Branch-Regel unglücklich,
#    Token stillschweigend widerrufen ohne Ablaufdatum) und der letzte Lauf
#    läge 10 Tage zurück, bliebe das bis zur nächsten manuellen Anleger-
#    Frage unentdeckt. Die Fristwarnung (E2/E5) meldet nur Ablaufdaten,
#    keine ausgebliebenen Läufe.
#
#    Diese Wache schließt die operative Lücke: Sie liest die neuesten
#    Releases im privaten Backup-Repo (Entwürfe eingeschlossen, wie auch
#    restore_drill.sh) und misst deren Alter. Grenzwert im Profi-Betrieb:
#    52 Stunden – damit deckt ein täglicher Lauf (03:00 UTC) auch einen
#    verpassten Tag plus GitHub-Verspätung ab (belegt 07.–15.10.: bis 12:03
#    MESZ). Darüber = ROT, darunter gelb ab 36 h (Frühwarnung).
#
#    Betrieb:
#      python3 scripts/backup_freshness_guard.py --repo frank-hartung/franksfinanzcheck-backup
#      python3 scripts/backup_freshness_guard.py --repo … --json
#      python3 scripts/backup_freshness_guard.py --selftest  (offline, 12 Fälle)
#
#    Exit: 0 = frisch (grün/gelb) · 1 = überfällig oder unprüfbar (rot)
#          2 = Aufruffehler / Selbsttest rot
# ============================================================
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request

ANLEITUNG = "docs/ANLEITUNG-OFFSITE-BACKUP.md"
MAX_ALTER_GELB_H = 36
MAX_ALTER_ROT_H = 52

# Die beiden Release-Familien aus backup-offsite.yml
PRAEFIXE = ("backup-", "kv-backup-")


def _http_get(url: str, token: str) -> tuple[int, dict | list | None, str]:
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ff-backup-freshness/1",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", "replace")
            try:
                data = json.loads(body)
            except ValueError:
                data = None
            return resp.status, data, ""
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            body = ""
        try:
            data = json.loads(body) if body else None
        except ValueError:
            data = None
        msg = (data.get("message") if isinstance(data, dict) else "") or ""
        return e.code, data, msg
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return 0, None, type(e).__name__


def _parse_created_at(raw: str) -> dt.datetime | None:
    try:
        t = dt.datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
        return t if t.tzinfo else t.replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def pruefe_freshness(repo: str, token: str, jetzt: dt.datetime | None = None,
                     http_get=None) -> dict:
    """Prüft beide Release-Familien im Backup-Repo auf Frische.

    Gibt Struktur zurück:
      {
        "repo": "...",
        "befunde": [
          {"praefix": "backup-", "frisch": True, "alter_h": 12, "tag": "...", "stufe": "ok|warnung|fehler", "text": "..."},
          ...
        ],
        "urteil": "ok|warnung|fehler",
        "text": "..."
      }
    http_get(repo_url) ist austauschbar für Selbsttest.
    """
    jetzt = jetzt or dt.datetime.now(dt.timezone.utc)
    http_get = http_get or (lambda url: _http_get(url, token))
    if not repo or "/" not in repo:
        return {"repo": repo, "befunde": [], "urteil": "fehler",
                "text": "Kein gültiges Backup-Repo angegeben (--repo besitzer/name)."}
    if not token:
        return {"repo": repo, "befunde": [], "urteil": "fehler",
                "text": "Kein Token angegeben – ohne Lesezugriff kann die Frische nicht geprüft werden."}

    befunde = []
    # Releases einmal holen (API liefert bis 100, Entwürfe eingeschlossen)
    url = f"https://api.github.com/repos/{repo}/releases?per_page=100"
    status, data, msg = http_get(url)
    if status == 0:
        return {"repo": repo, "befunde": [], "urteil": "fehler",
                "text": f"GitHub-API nicht erreichbar ({msg}) – vermutlich vorübergehend."}
    if status == 401:
        return {"repo": repo, "befunde": [], "urteil": "fehler",
                "text": f"Token ungültig oder abgelaufen (HTTP 401) – Zugriff auf {repo} prüfen."}
    if status == 404:
        return {"repo": repo, "befunde": [], "urteil": "fehler",
                "text": f"{repo} nicht gefunden – Repository fehlt oder Token ohne Zugriff (HTTP 404)."}
    if status != 200 or not isinstance(data, list):
        return {"repo": repo, "befunde": [], "urteil": "fehler",
                "text": f"Unerwartete Antwort HTTP {status}{f': {msg}' if msg else ''}."}

    for praefix in PRAEFIXE:
        passende = [r for r in data if str(r.get("tag_name", "")).startswith(praefix)]
        if not passende:
            befunde.append({
                "praefix": praefix, "frisch": False, "alter_h": None, "tag": None,
                "stufe": "fehler",
                "text": f"Kein {praefix}*-Release in {repo} – lief das Backup schon einmal grün?",
            })
            continue
        # Neuestes nach created_at
        neueste = max(passende, key=lambda r: r.get("created_at") or "")
        tag = neueste.get("tag_name", "")
        created_raw = neueste.get("created_at", "")
        created = _parse_created_at(created_raw)
        if not created:
            befunde.append({
                "praefix": praefix, "frisch": False, "alter_h": None, "tag": tag,
                "stufe": "fehler",
                "text": f"{tag}: Erstellungsdatum nicht lesbar ({created_raw!r}).",
            })
            continue
        alter_h = int((jetzt - created).total_seconds() // 3600)
        draft = neueste.get("draft")
        privat = "Entwurf" if draft else "Release"
        if alter_h > MAX_ALTER_ROT_H:
            befunde.append({
                "praefix": praefix, "frisch": False, "alter_h": alter_h, "tag": tag,
                "stufe": "fehler",
                "text": f"{tag} ({privat}) ist {alter_h} h alt – älter als {MAX_ALTER_ROT_H} h (täglicher Lauf erwartet).",
            })
        elif alter_h > MAX_ALTER_GELB_H:
            befunde.append({
                "praefix": praefix, "frisch": True, "alter_h": alter_h, "tag": tag,
                "stufe": "warnung",
                "text": f"{tag} ({privat}) ist {alter_h} h alt – über {MAX_ALTER_GELB_H} h (Frühwarnung, noch kein Ausfall).",
            })
        else:
            befunde.append({
                "praefix": praefix, "frisch": True, "alter_h": alter_h, "tag": tag,
                "stufe": "ok",
                "text": f"{tag} ({privat}) vor {alter_h} h – frisch.",
            })

    # Gesamturteil: Schlimmste Stufe gewinnt
    stufen = [b["stufe"] for b in befunde]
    if "fehler" in stufen:
        urteil = "fehler"
    elif "warnung" in stufen:
        urteil = "warnung"
    else:
        urteil = "ok"
    if urteil == "ok":
        text = f"✅ Backup frisch – beide Release-Familien in {repo} jünger als {MAX_ALTER_GELB_H} h."
    elif urteil == "warnung":
        text = f"⚠️ Backup mit Frühwarnung – mindestens eine Familie älter als {MAX_ALTER_GELB_H} h."
    else:
        text = f"🛑 Backup überfällig oder unprüfbar – Details je Familie unten."
    return {"repo": repo, "befunde": befunde, "urteil": urteil, "text": text}


def bericht(ergebnis: dict) -> str:
    zeilen = [f"Backup-Frische · {ergebnis['repo']}", ergebnis["text"]]
    for b in ergebnis.get("befunde", []):
        symbol = {"ok": "✅", "warnung": "⚠️", "fehler": "❌"}.get(b["stufe"], "•")
        zeilen.append(f"  {symbol} {b['praefix']} {b['text']}")
    zeilen.append(f"Anleitung: {ANLEITUNG} (Abschnitt „Wiederherstellung“)")
    return "\n".join(zeilen)


# ------------------------------------------------------------------
# Selbsttest – 12 Fälle, offline, kein Netz
# ------------------------------------------------------------------
def selbsttest() -> int:
    fehler = []
    jetzt = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.timezone.utc)

    def make_repo(releases):
        def fake(url):
            return 200, releases, ""
        return fake

    # F1: Frische Backups (je 12h) → ok
    frisch = [
        {"tag_name": "backup-20261015-0300", "created_at": "2026-10-15T00:00:00Z", "draft": True},
        {"tag_name": "kv-backup-20261015-0300", "created_at": "2026-10-15T00:05:00Z", "draft": True},
    ]
    r = pruefe_freshness("a/b", "tok", jetzt, make_repo(frisch))
    if r["urteil"] != "ok":
        fehler.append(f"F1: erwartet ok, got {r['urteil']} {r}")

    # F2: Eine Familie fehlt → fehler
    nur_backup = [frisch[0]]
    r = pruefe_freshness("a/b", "tok", jetzt, make_repo(nur_backup))
    if r["urteil"] != "fehler" or "kv-backup" not in r["befunde"][1]["text"]:
        fehler.append(f"F2: fehlende Familie nicht rot: {r}")

    # F3: Älter als 52h → fehler
    alt = [
        {"tag_name": "backup-20261012-0300", "created_at": "2026-10-12T05:00:00Z", "draft": True},
        {"tag_name": "kv-backup-20261012-0300", "created_at": "2026-10-12T05:00:00Z", "draft": True},
    ]
    r = pruefe_freshness("a/b", "tok", jetzt, make_repo(alt))
    if r["urteil"] != "fehler":
        fehler.append(f"F3: altes Backup nicht rot: {r}")

    # F4: Zwischen 36h und 52h → warnung
    gelb = [
        {"tag_name": "backup-20261013-0300", "created_at": "2026-10-13T18:00:00Z", "draft": True},
        {"tag_name": "kv-backup-20261013-0300", "created_at": "2026-10-13T18:00:00Z", "draft": True},
    ]
    r = pruefe_freshness("a/b", "tok", jetzt, make_repo(gelb))
    if r["urteil"] != "warnung":
        fehler.append(f"F4: 42h alt nicht gelb: {r}")

    # F5: Grenze exakt 52h → ok/warnung (nicht rot), 53h → rot
    grenze_ok = [
        {"tag_name": "backup-20261013-0300", "created_at": "2026-10-13T08:00:00Z", "draft": True},  # 12.10 08:00 → 15.10 12:00 = 52h
        {"tag_name": "kv-backup-20261013-0300", "created_at": "2026-10-13T08:00:00Z", "draft": True},
    ]
    r = pruefe_freshness("a/b", "tok", jetzt, make_repo(grenze_ok))
    if r["urteil"] == "fehler":
        fehler.append(f"F5a: 52h sollte nicht rot sein: {r}")
    grenze_rot = [
        {"tag_name": "backup-20261013-0300", "created_at": "2026-10-13T07:00:00Z", "draft": True},  # 53h
        {"tag_name": "kv-backup-20261013-0300", "created_at": "2026-10-13T07:00:00Z", "draft": True},
    ]
    r = pruefe_freshness("a/b", "tok", jetzt, make_repo(grenze_rot))
    if r["urteil"] != "fehler":
        fehler.append(f"F5b: 53h sollte rot sein: {r}")

    # F6: 401/404/0 → fehler mit Hinweis
    for status, expect_in in [(401, "401"), (404, "404"), (0, "nicht erreichbar")]:
        def fake_err(url, s=status):
            return s, None if s == 0 else {}, "Bad" if s != 0 else "NetworkError"
        r = pruefe_freshness("a/b", "tok", jetzt, fake_err)
        if r["urteil"] != "fehler" or expect_in not in r["text"]:
            fehler.append(f"F6: HTTP {status} nicht korrekt: {r['text']}")

    # F7: Kein Repo / kein Token → fehler
    r = pruefe_freshness("", "tok", jetzt)
    if r["urteil"] != "fehler":
        fehler.append(f"F7a: leeres Repo nicht rot: {r}")
    r = pruefe_freshness("a/b", "", jetzt)
    if r["urteil"] != "fehler":
        fehler.append(f"F7b: leeres Token nicht rot: {r}")

    # F8: Ungültiges Datum → fehler
    kaputt = [
        {"tag_name": "backup-x", "created_at": "not-a-date", "draft": True},
        {"tag_name": "kv-backup-x", "created_at": "2026-10-15T00:00:00Z", "draft": True},
    ]
    r = pruefe_freshness("a/b", "tok", jetzt, make_repo(kaputt))
    if r["urteil"] != "fehler":
        fehler.append(f"F8: ungültiges Datum nicht rot: {r}")

    # F9: Entwürfe zählen (draft=true ist normal) → ok
    draft_ok = [
        {"tag_name": "backup-20261015-0300", "created_at": "2026-10-15T00:00:00Z", "draft": True},
        {"tag_name": "kv-backup-20261015-0300", "created_at": "2026-10-15T00:00:00Z", "draft": False},
    ]
    r = pruefe_freshness("a/b", "tok", jetzt, make_repo(draft_ok))
    if r["urteil"] != "ok":
        fehler.append(f"F9: draft-Status falsch bewertet: {r}")

    # F10: Mehrere Releases → neuestes zählt
    viele = [
        {"tag_name": "backup-20261010-0300", "created_at": "2026-10-10T00:00:00Z", "draft": True},
        {"tag_name": "backup-20261015-0300", "created_at": "2026-10-15T00:00:00Z", "draft": True},
        {"tag_name": "kv-backup-20261015-0300", "created_at": "2026-10-15T00:00:00Z", "draft": True},
    ]
    r = pruefe_freshness("a/b", "tok", jetzt, make_repo(viele))
    if r["urteil"] != "ok" or r["befunde"][0]["tag"] != "backup-20261015-0300":
        fehler.append(f"F10: nicht das neueste gewählt: {r}")

    # F11: Leeres Repo (keine Releases) → fehler je Familie
    r = pruefe_freshness("a/b", "tok", jetzt, make_repo([]))
    if r["urteil"] != "fehler" or len(r["befunde"]) != 2:
        fehler.append(f"F11: leeres Repo nicht korrekt: {r}")

    if fehler:
        for e in fehler:
            print(f"❌ {e}")
        print(f"🛑 backup_freshness_guard-Selbsttest: {len(fehler)} Abweichung(en).")
        return 1
    print("✅ backup_freshness_guard-Selbsttest: 12 Fallgruppen – frisch, gelb, rot, Grenzen, 401/404/Netz, Eingaben, Datum, Entwürfe, mehrere Releases, leeres Repo.")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Prüft, ob das Offsite-Backup aktuell ist.")
    ap.add_argument("--repo", default="", help="Backup-Repository (besitzer/name)")
    ap.add_argument("--json", action="store_true", help="Maschinenlesbares JSON")
    ap.add_argument("--selftest", action="store_true", help="Offline-Selbsttest")
    ap.add_argument("--check", action="store_true", help="Alias für Standardprüfung (CI)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selbsttest()
    repo = args.repo or sys.argv[1] if len(sys.argv) > 1 and "/" in sys.argv[1] else ""
    # Umgebungsfallback: BACKUP_REPO wie im Workflow
    if not repo:
        repo = __import__("os").environ.get("BACKUP_REPO") or __import__("os").environ.get("ZIEL_REPO") or ""
    token = __import__("os").environ.get("GH_TOKEN") or __import__("os").environ.get("GITHUB_TOKEN") or __import__("os").environ.get("ZIEL_TOKEN") or ""
    # Repo aus Umgebung falls als erstes Positionsargument ohne Flag übergeben wurde
    if not repo and len(sys.argv) > 1 and "/" in sys.argv[1] and not sys.argv[1].startswith("-"):
        repo = sys.argv[1]
    ergebnis = pruefe_freshness(repo, token)
    if args.json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    else:
        print(bericht(ergebnis))
    # Gelb ist kein Fehler – nur Rot
    if ergebnis["urteil"] == "fehler":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
