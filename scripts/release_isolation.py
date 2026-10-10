#!/usr/bin/env python3
# ============================================================
#  RELEASE-ISOLATION – ein blockierter Kandidat friert nicht die
#  ganze öffentliche Auslieferung ein (Dauerheilung Issue #676)
#  ------------------------------------------------------------
#  BEFUND 09.10.2026 (Bot-Watchdog #676, „Neuester Artikel nicht
#  live", HTTP 404 auf /posts/2026-10-07-campingurlaub-…/):
#
#    Der neueste Artikel war im Repo, `draft: false`, redaktionell
#    geprüft – und trotzdem nicht erreichbar. Nicht, weil der Deploy
#    nicht ausgelöst wurde (Deploy-Catchup lief stündlich und stieß
#    ihn sechsmal an), sondern weil er 13× in Folge am SELBEN Schritt
#    starb: „Release-Scorecard (Produktionswahrheit versiegeln,
#    fail-closed)" → Exit 1.
#
#    Der Befund war EIN Satz in EINEM Artikel: RD1-duplikate meldete
#    den End-CTA („👉 Jetzt das Tagesgeld-Angebot der C24 Bank
#    ansehen") als D3-X „Absatz wortgleich in 2 Artikeln" – obwohl
#    affiliate_intent_contract genau diesen Wortlaut vorschreibt.
#
#  DIE EIGENTLICHE SCHWÄCHE (warum daraus ein P1-Ausfall wurde):
#    Die Scorecard ist der LETZTE Gate vor der Auslieferung und steht
#    VOR `upload-pages-artifact`. Ein roter Kandidat bricht den Job
#    ab – damit wurde nicht dieser eine Artikel zurückgehalten,
#    sondern das komplette Pages-Deployment: 42 Live-Artikel blieben
#    auf dem Stand von 22:06 UTC am Vortag einfrieren, alle
#    nachgelagerten Schritte (Vertonung, Suchindex, gh-pages,
#    deploy-pages) liefen nie. Die härteste Wache hatte die größte
#    Sprengkraft, und ihre Sprengkraft galt dem falschen Objekt.
#
#    `entscheidung: auto` in data/release_scorecard.yaml verspricht
#    zudem, eine Maschine könne den Befund heilen. Für Cross-Artikel-
#    Duplikate stimmt das nicht (duplikat_guard: „werden NIE
#    auto-gefixed"). Ein harter Blocker ohne Heiler ist eine
#    Sackgasse – Regel C29 („Ein harter Blocker braucht einen
#    Heiler") beschreibt genau diese Klasse.
#
#  VERTRAG DIESES MODULS (fail-closed bleibt fail-closed):
#    Isolation ist KEIN `|| true` und kein `continue-on-error`.
#    Ein blockierter Kandidat geht weiterhin NICHT live – er wird
#    über park_state.hold() zurückgestellt, mit dem Check und dem
#    Befund als Grund im Frontmatter (sichtbar, nie automatisch
#    zurückgeholt). Geändert hat sich nur der BLUSTRADIUS:
#
#      vorher: 1 roter Kandidat  → 0 Artikel ausgeliefert (Site friert)
#      jetzt : 1 roter Kandidat  → dieser eine zurückgestellt,
#                                  Quote nachgefüllt (#287/#610),
#                                  der grüne Rest ausgeliefert
#
#    Nach jeder Runde wird neu gebaut und die Scorecard erneut
#    gemessen – über DIESELBE Engine (keine zweite Messregel,
#    Lektion #521). Ist nach `--runden` Runden noch immer ein
#    Kandidat blockiert, bleibt Exit 1 und der Deploy stoppt ehrlich.
#
#  Exit-Codes (Vertrag):
#    0 = Auslieferung darf laufen (Scope grün oder leer)
#    1 = weiterhin blockierende Kandidaten nach allen Runden
#    2 = Werkzeugfehler (fail-closed – kein Ausweichen ins Stille)
#
#  Nutzung:
#    python3 scripts/release_isolation.py --selftest
#    python3 scripts/release_isolation.py --trockenlauf     # Befund, kein Griff
#    python3 scripts/release_isolation.py --runden 3        # Deploy-Pfad
# ============================================================
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
POSTS = ROOT / "content" / "posts"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

EXIT_OK = 0
EXIT_BLOCKIERT = 1
EXIT_WERKZEUGFEHLER = 2

# Begrenzte Konvergenz wie publication_release.refill_until_min (#610):
# jede Runde kann einen nachgefüllten Kandidaten erneut rot sehen.
DEFAULT_RUNDEN = 3

# Warum diese Grenze: Ein Nachfüll-Kandidat, der selbst blockiert, darf
# nicht endlos weitere Kandidaten nachziehen – sonst würde die Isolation
# den Vorrat leer räumen, während der Deploy wartet.
MAX_ISOLATIONEN_PRO_LAUF = 6


def _importiere(name: str):
    """Gate-Module lesen teils sys.argv beim Import (affiliate_intent_guard:
    `ARGS = sys.argv[1:]`). Unsere eigenen Flags dürfen dort nie ankommen."""
    alt = sys.argv
    sys.argv = [alt[0]]
    try:
        return __import__(name)
    finally:
        sys.argv = alt


# ============================================================
#  Messung: die Scorecard-Engine selbst, nie eine zweite Regel
# ============================================================
def verdict(commit_sha: str | None = None, heute: dt.date | None = None):
    """(exit_code, ergebnis) der Release-Scorecard im Deploy-Scope.

    Liest über `release_scorecard.durchfuehren()` – dieselben Collector-
    Funktionen, dieselbe SSOT, dasselbe Urteil wie der Deploy-Schritt.
    Schreibt nichts (C15: Beweisläufe heilen nicht)."""
    rsc = _importiere("release_scorecard")
    heute = heute or dt.date.today()
    live, entwuerfe, fingerprints = rsc.bestand_aufnehmen()
    ergebnis = rsc.durchfuehren("kandidaten", heute, live, entwuerfe,
                               fingerprints, rsc.zustand_laden(), commit_sha)
    return rsc.exit_code(ergebnis, ergebnis["kandidaten"]), ergebnis


def blockierte_kandidaten(ergebnis: dict) -> dict[str, list[str]]:
    """{slug: [grund, …]} für Kandidaten, die nicht ausgeliefert werden dürfen.

    Dieselbe Prädikat wie `release_scorecard.exit_code()`: `blockiert` ODER
    `nicht beweisbar`. Ein unbeweisbarer Kandidat ist kein grüner – und ein
    unbeweisbarer Kandidat darf ebenso wenig die ganze Site einfrieren."""
    artikel = ergebnis.get("artikel") or {}
    auswahl: dict[str, list[str]] = {}
    for slug in ergebnis.get("kandidaten") or []:
        art = artikel.get(slug)
        if not art or art.get("urteil") not in ("blockiert", "nicht beweisbar"):
            continue
        gründe: list[str] = []
        for befund in art.get("befunde") or []:
            if befund.get("ausnahme"):
                continue
            if befund.get("wirkung") != "blockiert" and not befund.get("werkzeugfehler"):
                continue
            if befund.get("status") == "warnung":
                continue
            gründe.append(f"{befund.get('check')}: "
                          f"{str(befund.get('detail') or '')[:180]}")
        auswahl[slug] = gründe or [f"Urteil {art.get('urteil')} (ohne Detailfund)"]
    return auswahl


# ============================================================
#  Der Griff: zurückstellen, nie löschen, nie umschreiben
# ============================================================
def artikel_pfad(slug: str) -> Path:
    return POSTS / slug / "index.md"


def grund_text(slug: str, gründe: list[str]) -> str:
    """Frontmatter-Grund: kurz, YAML-sicher, mit der Check-ID als Spur.

    `park_state.hold()` zitiert den Text selbst YAML-sicher; die Kürzung
    schützt das Frontmatter trotzdem vor einem Mehrzeilen-Unfall."""
    kurz = " | ".join(gründe[:2])
    return (f"release-isolation (#676): {kurz}"
            f" – Auslieferung isoliert, Rest des Bestands bleibt live")[:400]


def isoliere(slug: str, gründe: list[str], *, trockenlauf: bool = False) -> bool:
    """Stellt EINEN blockierten Kandidaten auf hold. True = Griff erfolgt.

    `hold` und nicht `park`: Der Artikel braucht eine Korrektur, keinen
    späteren Slot. Ohne `cadence_wait` holt die Automatik ihn nicht
    zurück (park_state-Zustandsmaschine) – die Blockade bleibt sichtbar,
    bis ein Mensch oder ein Heiler den Befund wirklich aufgelöst hat."""
    pfad = artikel_pfad(slug)
    if not pfad.exists():
        print(f"  ⚠ {slug}: keine index.md – Isolation übersprungen "
              "(fail-closed, kein stiller Erfolg).")
        return False
    if trockenlauf:
        print(f"  ⏸ [Trockenlauf] {slug} → hold: {grund_text(slug, gründe)[:120]}")
        return True
    park_state = _importiere("park_state")
    ok = park_state.hold(str(pfad), grund_text(slug, gründe))
    if not ok:
        print(f"  🛑 {slug}: park_state.hold() konnte nicht schreiben.")
    return bool(ok)


def quote_nachfuellen() -> list[str]:
    """LIVE-Mindestziel wiederherstellen (Brandschutzlinie #287/#610).

    `finalize=False`: Der eigene Hugo-Build und das eigene Publish-Gate
    dieser Funktion würden der Isolation sonst zweimal bauen und den
    Render-Beweis der Scorecard vor dem Rebuild verwischen. Beides
    geschieht unten deterministisch in `neu_bauen()` bzw. über die
    erneute Scorecard-Messung."""
    try:
        pr = _importiere("publication_release")
        return list(pr.refill_until_min(finalize=False))
    except Exception as exc:  # noqa: BLE001 – Quote ist Best-Effort, Isolation nicht
        print(f"  ⚠ Quote-Nachfüllung fehlgeschlagen ({exc}) – die Isolation "
              "bleibt trotzdem stehen; der Kadenz-Backstop füllt nach.")
        return []


def neu_bauen() -> bool:
    """Render-Beweis erneuern: Die Scorecard liest public/ (T7, A1, A3).

    Ohne Rebuild würde die zweite Messung einen Build prüfen, in dem der
    isolierte Artikel noch enthalten ist – ein Mess-Artefakt, genau die
    Klasse, die C33 verbietet."""
    if os.environ.get("FF_ISOLATION_OHNE_BUILD") == "1":
        print("  ℹ FF_ISOLATION_OHNE_BUILD=1 – Rebuild übersprungen (Probe).")
        return True
    try:
        subprocess.run(["hugo", "--minify", "--destination", "public"],
                       cwd=ROOT, check=True, timeout=900)
        return True
    except FileNotFoundError:
        print("  🛑 Hugo fehlt im PATH – Render-Beweis nicht erneuerbar "
              "(fail-closed: ohne Build keine zweite Messung).")
        return False
    except subprocess.CalledProcessError as exc:
        print(f"  🛑 Hugo-Build nach Isolation fehlgeschlagen (Exit "
              f"{exc.returncode}) – fail-closed, kein Ausliefern ohne Beweis.")
        return False
    except subprocess.TimeoutExpired:
        print("  🛑 Hugo-Build nach Isolation: Timeout – fail-closed.")
        return False


def audit(erfahrung: dict) -> None:
    """Spur ins Audit-Log (Best-Effort: ein Audit-Fehler bricht nichts ab)."""
    try:
        audit_log = _importiere("audit_log")
        audit_log.log_event(
            module="release_isolation",
            action="lauf",
            input={"commit": erfahrung.get("commit")},
            output={"runden": erfahrung.get("runden"),
                    "isoliert": erfahrung.get("isoliert"),
                    "nachgefuellt": len(erfahrung.get("nachgefuellt") or []),
                    "exit": erfahrung.get("exit")},
            status="ok" if erfahrung.get("exit") == EXIT_OK else "blockiert")
    except Exception:  # noqa: BLE001
        pass


def zusammenfassung(erfahrung: dict) -> None:
    """Lauf-Zusammenfassung (GitHub Step Summary) – der Befund muss ohne
    Log-Wälzen lesbar sein (Lektion WF-A535 #529)."""
    pfad = os.environ.get("GITHUB_STEP_SUMMARY")
    if not pfad:
        return
    zeilen = [
        "## 🚧 Auslieferungs-Isolation (Issue #676)",
        "",
        f"**Runden:** {erfahrung.get('runden', 0)} · "
        f"**isoliert:** {len(erfahrung.get('isoliert') or {})} · "
        f"**nachgefüllt:** {len(erfahrung.get('nachgefuellt') or [])} · "
        f"**Exit:** {erfahrung.get('exit')}",
        "",
    ]
    if erfahrung.get("isoliert"):
        zeilen += ["| Artikel | Befund (Check) |", "|---|---|"]
        for slug, gründe in sorted(erfahrung["isoliert"].items()):
            zeilen.append(f"| `{slug}` | {'; '.join(gründe)[:200]} |")
        zeilen += ["", "_Zurückgestellt auf `hold` (Frontmatter nennt den "
                      "Grund). Der übrige Bestand wird ausgeliefert._"]
    else:
        zeilen.append("_Kein Kandidat musste isoliert werden._")
    try:
        with open(pfad, "a", encoding="utf-8") as fh:
            fh.write("\n".join(zeilen) + "\n")
    except OSError:
        pass


def lauf(commit_sha: str | None = None, *, runden: int = DEFAULT_RUNDEN,
         trockenlauf: bool = False, heute: dt.date | None = None) -> int:
    """Isolation bis zur Konvergenz – begrenzt, nachvollziehbar, fail-closed."""
    erfahrung: dict = {"commit": commit_sha, "runden": 0,
                       "isoliert": {}, "nachgefuellt": [], "exit": EXIT_OK}
    for runde in range(1, max(1, runden) + 1):
        erfahrung["runden"] = runde
        try:
            code, ergebnis = verdict(commit_sha=commit_sha, heute=heute)
        except Exception as exc:  # noqa: BLE001 – Werkzeugfehler ist Exit 2
            print(f"🛑 Release-Scorecard nicht auswertbar: {exc}")
            erfahrung["exit"] = EXIT_WERKZEUGFEHLER
            return erfahrung["exit"]

        if code == EXIT_OK:
            print(f"✅ Runde {runde}: Deploy-Scope freigabe-reif – "
                  "Auslieferung darf laufen.")
            erfahrung["exit"] = EXIT_OK
            return EXIT_OK
        if code == EXIT_WERKZEUGFEHLER:
            # Werkzeugfehler sind keine Inhaltsfrage: Isolation kann sie
            # nicht heilen, und „nicht messbar" darf nie als Grün
            # durchgehen (C33: eine fehlgeschlagene Messung ist kein
            # leerer Vorrat).
            print("🛑 Runde %d: Werkzeugfehler in der Scorecard – Isolation "
                  "greift bewusst nicht (fail-closed)." % runde)
            for check, grund in sorted((ergebnis.get("tool_fehler") or {}).items()):
                print(f"   ❔ {check}: {grund[:160]}")
            erfahrung["exit"] = EXIT_WERKZEUGFEHLER
            return EXIT_WERKZEUGFEHLER

        blockiert = blockierte_kandidaten(ergebnis)
        if not blockiert:
            print(f"🛑 Runde {runde}: Scope rot, aber kein Kandidat trägt den "
                  "Befund – Isolation wäre blind. Deploy stoppt (fail-closed).")
            erfahrung["exit"] = EXIT_BLOCKIERT
            return EXIT_BLOCKIERT

        neu = {slug: gründe for slug, gründe in blockiert.items()
               if slug not in erfahrung["isoliert"]}
        if not neu:
            # Der Kandidat ist bereits zurückgestellt und TROTZDEM noch rot:
            # Dann trägt nicht er den Befund (z. B. Nachschub aus der Quote
            # oder ein Mess-Artefakt). Weiteres Nachfüllen würde Material
            # verbrennen, ohne den Befund aufzulösen – ehrlich stoppen.
            print(f"🛑 Runde {runde}: Alle blockierten Kandidaten sind bereits "
                  "isoliert – der Befund ist durch Zurückstellen nicht "
                  "auflösbar. Deploy stoppt (fail-closed).")
            for slug, gründe in sorted(blockiert.items()):
                print(f"   ⛔ {slug}: {'; '.join(gründe)[:150]}")
            erfahrung["exit"] = EXIT_BLOCKIERT
            return EXIT_BLOCKIERT
        budget = MAX_ISOLATIONEN_PRO_LAUF - len(erfahrung["isoliert"])
        if budget <= 0:
            print(f"🛑 Isolationsobergrenze {MAX_ISOLATIONEN_PRO_LAUF} erreicht – "
                  "der Bestand hat ein strukturelles Problem, kein Einzelbefund. "
                  "Deploy stoppt (fail-closed).")
            erfahrung["exit"] = EXIT_BLOCKIERT
            return EXIT_BLOCKIERT
        if len(neu) > budget:
            print(f"⚠ {len(neu)} Kandidaten blockiert, Budget {budget} – "
                  "isoliert wird in dieser Runde nur das Budget.")
        neu = dict(sorted(neu.items())[:budget])

        print(f"🚧 Runde {runde}: {len(neu)} Kandidat(en) blockieren die "
              "Auslieferung – isolieren statt einfrieren (#676).")
        for slug, gründe in neu.items():
            if isoliere(slug, gründe, trockenlauf=trockenlauf):
                erfahrung["isoliert"][slug] = gründe
                for g in gründe:
                    print(f"   ⏸ {slug} → hold · {g[:150]}")

        if trockenlauf:
            print("ℹ Trockenlauf: keine Frontmatter-Änderung, kein Rebuild. "
                  "Der Befund oben ist die Antwort.")
            erfahrung["exit"] = EXIT_BLOCKIERT
            return EXIT_BLOCKIERT

        nachgeschoben = quote_nachfuellen()
        erfahrung["nachgefuellt"].extend(nachgeschoben)
        if nachgeschoben:
            print(f"   🛟 Quote nachgefüllt: {', '.join(nachgeschoben)}")

        if not neu_bauen():
            erfahrung["exit"] = EXIT_WERKZEUGFEHLER
            return EXIT_WERKZEUGFEHLER

    # Runden erschöpft: ehrlich rot, nicht still grün.
    print(f"🛑 Nach {erfahrung['runden']} Runde(n) weiterhin blockierte "
          "Kandidaten – Deploy stoppt (fail-closed).")
    erfahrung["exit"] = EXIT_BLOCKIERT
    return EXIT_BLOCKIERT


# ============================================================
#  Selbsttest: sabotierte Fassungen müssen rot werden
# ============================================================
def run_selftest() -> list[str]:
    """Prüft die Verträge dieses Moduls an Kunstbefunden (kein Netz, kein Hugo).

    Hausregel: „Ein `--selftest` muss das Modul prüfen, dessen Namen er
    trägt" – also Isolation, nicht die Scorecard."""
    fehler: list[str] = []

    ergebnis = {
        "kandidaten": ["gruen", "rot-blockiert", "rot-unbeweisbar", "warnung"],
        "artikel": {
            "gruen": {"urteil": "freigabe-reif", "befunde": []},
            "rot-blockiert": {"urteil": "blockiert", "befunde": [
                {"check": "RD1-duplikate", "wirkung": "blockiert",
                 "detail": "D3-X: Absatz wortgleich in 2 Artikeln",
                 "ausnahme": False, "werkzeugfehler": False},
                {"check": "T1w-zeichenlaenge-optimum", "wirkung": "warnung",
                 "detail": "unter Optimum", "ausnahme": False,
                 "werkzeugfehler": False},
            ]},
            "rot-unbeweisbar": {"urteil": "nicht beweisbar", "befunde": [
                {"check": "T7-render-beweis", "wirkung": "blockiert",
                 "detail": "Artikel fehlt im Build", "ausnahme": False,
                 "werkzeugfehler": True},
            ]},
            "warnung": {"urteil": "warnung", "befunde": [
                {"check": "Q2-quellen-vorhanden", "wirkung": "warnung",
                 "detail": "keine Belegkette", "ausnahme": False,
                 "werkzeugfehler": False},
            ]},
        },
    }

    # ST1 – Auswahl: nur blockiert/unbeweisbar, nie warnung, nie grün.
    auswahl = blockierte_kandidaten(ergebnis)
    if set(auswahl) != {"rot-blockiert", "rot-unbeweisbar"}:
        fehler.append(f"ST1 Auswahl: erwartet 2 blockierte Kandidaten, "
                      f"bekam {sorted(auswahl)}")

    # ST2 – Warnungen dürfen keine Isolation auslösen (sonst würde die
    # Isolation den Bestand für jede Optimum-Warnung zurückstellen).
    if any("T1w" in g for g in auswahl.get("rot-blockiert", [])):
        fehler.append("ST2 Warnung: T1w-Optimum-Warnung wurde als "
                      "Blockadegrund gewertet")

    # ST3 – Der Grund trägt die Check-ID (Spur im Frontmatter).
    if not any(g.startswith("RD1-duplikate:") for g in auswahl.get("rot-blockiert", [])):
        fehler.append("ST3 Grund: Check-ID fehlt im Isolations-Grund")

    # ST4 – Ein Befund ohne Detail darf nie zu einem leeren Grund führen
    # (ein leerer cadence_grund macht den Zustand wieder mehrdeutig, #129).
    leer = {"kandidaten": ["x"], "artikel": {"x": {"urteil": "blockiert", "befunde": []}}}
    gründe = blockierte_kandidaten(leer).get("x") or []
    if not gründe or not gründe[0].strip():
        fehler.append("ST4 leerer Grund: blockiert ohne Detail ergab keinen Grund")

    # ST5 – Grund ist einzeilig und begrenzt (YAML-Sicherheit im Frontmatter).
    lang = grund_text("x", ["RD1-duplikate: " + "y" * 900])
    if "\n" in lang or len(lang) > 400:
        fehler.append(f"ST5 Grund-Format: {len(lang)} Zeichen / mehrzeilig")

    # ST6 – Ausnahmen (Falsch-Alarm-Protokoll) sind kein Isolationsgrund:
    # Was die SSOT ausdrücklich freigegeben hat, darf die Isolation nicht
    # als Befund fortschreiben, sonst unterläuft sie die menschliche
    # Entscheidung (Frage 4 der Scorecard).
    ausnahme = {"kandidaten": ["a"], "artikel": {"a": {"urteil": "blockiert", "befunde": [
        {"check": "A2-intent", "wirkung": "blockiert", "detail": "freigegeben",
         "ausnahme": True, "werkzeugfehler": False}]}}}
    if any("A2-intent" in g for g in blockierte_kandidaten(ausnahme).get("a", [])):
        fehler.append("ST6 Ausnahme: eine SSOT-Ausnahme wurde als "
                      "Isolationsgrund gewertet")

    # ST7 – hold, nicht park: die Automatik darf einen blockierten Artikel
    # nicht in den nächsten Slot zurückholen (Zustandsmaschine park_state).
    # Die Suchbegriffe werden zusammengesetzt, sonst findet der Test seine
    # eigene Zeile (selbstreferenzieller Fund – ein Scheinrot, das genau
    # dieselbe Sackgasse öffnet wie ein Scheingrün).
    quelltext = (SCRIPTS / "release_isolation.py").read_text(encoding="utf-8")
    park_aufruf = "park_state." + "park("
    if park_aufruf in quelltext:
        fehler.append("ST7 Zustand: park() statt hold() – der Artikel würde "
                      "automatisch wiederkommen")
    hold_aufruf = "park_state." + "hold("
    if hold_aufruf not in quelltext:
        fehler.append("ST7 Zustand: hold() fehlt – ohne Blockade-Grund ist "
                      "„draft ohne cadence_wait“ wieder mehrdeutig (#129)")

    # ST8 – EINE Messregel: `verdict()` muss die Entscheidung bei
    # release_scorecard lassen und deren Exit-Vertrag unverändert
    # durchreichen. Geprüft mit einem Stub statt mit dem echten Baum: Der
    # Selbsttest muss in jeder Umgebung laufen (PR-Pfad/C6 ohne PyYAML) und
    # er soll die DELEGATION beweisen, nicht den Bestand vermessen.
    class _StubScorecard:
        aufrufe = []

        @staticmethod
        def bestand_aufnehmen():
            return ["a"], ["b"], {"a": "fp"}

        @staticmethod
        def zustand_laden():
            return {}

        @staticmethod
        def durchfuehren(modus, heute, live, entwuerfe, fingerprints,
                         vorher, commit):
            _StubScorecard.aufrufe.append(modus)
            return {"kandidaten": ["a"], "artikel": {}, "tool_fehler": {}}

        @staticmethod
        def exit_code(ergebnis, scope):
            return EXIT_BLOCKIERT

    stub = _StubScorecard()
    echt = sys.modules.get("release_scorecard")
    sys.modules["release_scorecard"] = stub
    try:
        code, erg = verdict(commit_sha="selftest")
    except Exception as exc:  # noqa: BLE001
        fehler.append(f"ST8 Messregel: verdict() über release_scorecard "
                      f"fehlgeschlagen: {exc}")
        code, erg = None, {}
    finally:
        if echt is not None:
            sys.modules["release_scorecard"] = echt
        else:
            sys.modules.pop("release_scorecard", None)
    if code != EXIT_BLOCKIERT:
        fehler.append(f"ST8 Messregel: verdict() reichte den Exit-Code der "
                      f"Scorecard nicht durch (bekam {code}, erwartet "
                      f"{EXIT_BLOCKIERT}) – eigene Ampel, Lektion #521")
    if _StubScorecard.aufrufe != ["kandidaten"]:
        fehler.append("ST8 Messregel: verdict() maß nicht den Deploy-Scope "
                      f"`kandidaten` (bekam {_StubScorecard.aufrufe})")
    if "kandidaten" not in erg:
        fehler.append("ST8 Messregel: verdict() lieferte kein Scorecard-"
                      "Ergebnis zurück")

    # ST9 – Kein Still-Schalter: `|| true` / continue-on-error im Deploy
    # würde die fail-closed-Garantie zerstören. Der Deploy-Schritt muss
    # den Exit-Code dieses Moduls durchreichen.
    deploy = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
    if "release_isolation.py" in deploy:
        for zeile in deploy.splitlines():
            if "release_isolation.py" in zeile and ("|| true" in zeile or
                                                    "continue-on-error" in zeile):
                fehler.append("ST9 Deploy: Isolation mit `|| true`/"
                              "continue-on-error verdrahtet (Scheingrün)")
    return fehler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Auslieferungs-Isolation: blockierte Kandidaten "
                    "zurückstellen, statt die ganze Site einzufrieren (#676)")
    parser.add_argument("--runden", type=int, default=DEFAULT_RUNDEN,
                        help=f"begrenzte Konvergenz (Default {DEFAULT_RUNDEN})")
    parser.add_argument("--trockenlauf", action="store_true",
                        help="Befund zeigen, nichts schreiben, kein Rebuild")
    parser.add_argument("--commit-sha", default=os.environ.get("GITHUB_SHA"),
                        help="Deploy-Commit (Default: $GITHUB_SHA)")
    parser.add_argument("--selftest", action="store_true",
                        help="Sabotage-Proben gegen dieses Modul")
    args = parser.parse_args(argv)

    if args.selftest:
        fehler = run_selftest()
        if fehler:
            print("🛑 RELEASE-ISOLATION-SELFTEST FEHLGESCHLAGEN:")
            for f in fehler:
                print(f"   - {f}")
            return EXIT_WERKZEUGFEHLER
        print("✅ RELEASE-ISOLATION-SELFTEST bestanden: Auswahl (blockiert/"
              "unbeweisbar, nie warnung), Grund mit Check-ID, YAML-Sicherheit, "
              "hold statt park, eine Messregel, kein Still-Schalter im Deploy.")
        return EXIT_OK

    if args.runden < 1:
        print("🛑 --runden muss >= 1 sein (fail-closed, keine Endlosschleife).")
        return EXIT_WERKZEUGFEHLER

    erfahrung: dict = {}
    try:
        code = lauf(commit_sha=args.commit_sha, runden=args.runden,
                    trockenlauf=args.trockenlauf)
    except Exception as exc:  # noqa: BLE001 – ein Crash darf nie als Grün enden
        print(f"🛑 Isolation abgebrochen: {exc}")
        return EXIT_WERKZEUGFEHLER
    erfahrung.update({"commit": args.commit_sha, "exit": code})
    audit(erfahrung)
    zusammenfassung(erfahrung)
    return code


if __name__ == "__main__":
    sys.exit(main())
