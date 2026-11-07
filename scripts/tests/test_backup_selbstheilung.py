"""Verträge der Backup-Selbstheilung (WF-3150 / #1030, 07.11.2026).

DIE KLASSE, DIE HIER ZU IST
----------------------------
Die Frischwache hat bis zum 06.11.2026 gemessen und gemeldet – geheilt hat
sie nicht. Fiel der nächtliche Sicherungslauf aus (Scheduler-Aussetzer, still
widerrufenes Token, Environment-Regel nach einem Settings-Umbau), blieb es
bei einer Meldung; der eine wirksame Schritt war ein Handbefehl. Dieselbe
Klasse wie bei der GSC-Verlinkung (Akte
`GSC-VERLINKUNG-SELBSTHEILUNG-1097-HIGHEND-2026-11-06.md`, §2.1): „Heilung
vorhanden, aber nicht verdrahtet“.

DIE GRENZE, DIE HIER BEWACHT WIRD
----------------------------------
Selbstheilung darf nicht in Selbstbetrug kippen. Deshalb prüfen diese Tests
in beide Richtungen:
  · Sie stößt WIRKLICH an, wenn das Tagesfenster verpasst ist (sonst wäre
    die Heilung wieder nur eine Warteschlange).
  · Sie stößt NICHT an, wenn eine Sicherung läuft, wenn der Mindestabstand
    unterschritten ist, wenn das Budget erschöpft ist oder wenn die
    Lauf-Historie nicht lesbar ist (sonst Doppelläufe und Dauerfeuer).
  · Grün gibt es NUR nach der zweiten Messung – ein angestoßener Lauf ist
    kein Nachweis (dieselbe Doktrin wie E1–E8 und „Restore-Drill ohne
    geprüfte Familie“).
"""

from __future__ import annotations

import copy
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import backup_freshness_guard as bg  # noqa: E402
import backup_selbstheilung as bs  # noqa: E402

WORKFLOW = REPO / ".github" / "workflows" / "backup-frischwache.yml"
JETZT = dt.datetime(2026, 11, 7, 13, 0, tzinfo=dt.timezone.utc)

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover – CI installiert PyYAML
    yaml = None


def _releases(*familien: tuple[str, str, int]):
    """Baut eine API-Antwort: (tag, created_at, assets-Anzahl)."""
    aus = []
    for tag, created, assets in familien:
        aus.append({
            "tag_name": tag,
            "created_at": created,
            "draft": True,
            "assets": [{"name": f"datei-{i}.bin", "size": 1000} for i in range(assets)],
        })
    return aus


FRISCH = _releases(
    ("backup-20261107-0300", "2026-11-07T03:00:00Z", 2),
    ("kv-backup-20261107-0301", "2026-11-07T03:01:00Z", 1),
)
VERPASST = _releases(
    ("backup-20261106-0300", "2026-11-06T03:00:00Z", 2),
    ("kv-backup-20261106-0301", "2026-11-06T03:01:00Z", 1),
)


def welt(*, releases, laeufe=None, dispatch=204, messung_zwei=None, stoesse=None):
    """Fake-HTTP für den ganzen Kreis (Signatur wie backup_selbstheilung.HTTP)."""
    zustand = {"messen": 0, "stoesse": stoesse if stoesse is not None else []}
    antworten_laeufe = laeufe if laeufe is not None else []

    def http(methode, url, token, koerper=None):
        if "/releases" in url:
            zustand["messen"] += 1
            if zustand["messen"] > 1 and messung_zwei is not None:
                return 200, messung_zwei, ""
            return 200, releases, ""
        if url.endswith("/dispatches"):
            zustand["stoesse"].append({"methode": methode, "url": url, "koerper": koerper})
            return dispatch, ({"message": "Resource not accessible by integration"}
                              if dispatch >= 400 else None), ""
        if "/runs?" in url:
            return 200, {"workflow_runs": antworten_laeufe(zustand) if callable(antworten_laeufe)
                         else antworten_laeufe}, ""
        if "/actions/runs/" in url:
            return 200, {"id": 99, "status": "completed", "conclusion": "success",
                         "html_url": "https://x/runs/99"}, ""
        raise AssertionError(f"unerwarteter Endpunkt: {methode} {url}")

    http.zustand = zustand
    return http


def heile(seite, **kwargs):
    umgebung = {"BACKUP_REPO": "frank-hartung/franksfinanzcheck-backup",
                "GITHUB_REPOSITORY": "frank-hartung/franksfinanzcheck-blog",
                "GH_TOKEN": "ziel-token", "AKTION_TOKEN": "lauf-token"}
    # Beide Messungen auf DEMSELBEN Testzeitpunkt: sonst hinge das Ergebnis an
    # der Wanduhr des Testtages (scripts/selftest_clock.py, Lehre 18.09.2026).
    return bs.heile(umgebung, jetzt=JETZT, jetzt_neu=JETZT, http=seite,
                    schlaf=lambda _s: None, **kwargs)


class Selbsttest(unittest.TestCase):
    def test_selbsttest_ist_gruen_und_leckt_keine_annotationen(self):
        lauf = subprocess.run([sys.executable, str(SCRIPTS / "backup_selbstheilung.py"),
                               "--selftest"], capture_output=True, text=True, timeout=120)
        self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)
        self.assertIn("✅ backup_selbstheilung-Selbsttest", lauf.stdout)
        for zeile in (lauf.stdout + "\n" + lauf.stderr).splitlines():
            self.assertFalse(zeile.lstrip().startswith(("::error::", "::warning::")),
                             f"Selbsttest erzeugt eine echte Annotation: {zeile[:120]}")

    def test_kommandozeile_probe_ohne_eingaben(self):
        """Der CLI-Pfad selbst: `--probe --wartezeit N` muss laufen, ohne zu senden.

        Befund beim Live-Aufruf am 07.11.2026: `main` reichte `warte_s` an
        `heile()` weiter, das Argument heißt `warten_s` → TypeError. Der
        Selbsttest lief grün, weil er die Funktion direkt aufrief. Genau diese
        Lücke prüft dieser Test: der Aufruf über die Kommandozeile, mit leerer
        Umgebung, ohne Netz (leeres Ziel endet fail-closed).
        """
        from unittest import mock
        with mock.patch.dict(os.environ, {}, clear=True):
            rc = bs.main(["--probe", "--wartezeit", "0"])
        self.assertEqual(rc, 1, "ohne Ziel muss die Probe rot enden")

    def test_probe_ohne_netz_ist_rot_und_stoesst_nichts_an(self):
        """Ohne Ziel/Token/Historie darf die Probe nichts anstoßen – und nicht grün sein."""
        r = bs.heile({}, jetzt=JETZT, jetzt_neu=JETZT,
                     http=lambda *a, **k: (_ for _ in ()).throw(
                         AssertionError("Netzaufruf ohne Eingaben")),
                     schlaf=lambda _s: None)
        self.assertEqual(r["urteil"], "fehler")
        self.assertEqual(r["heilung"]["aktion"], "aufgeben")
        self.assertFalse(r["heilung"]["gestartet"])


class EntscheidungsVertrag(unittest.TestCase):
    """Die Tabelle entscheidet – nicht das Gefühl. Jede Zeile ist eine Zusage."""

    @staticmethod
    def _befunde(*alter):
        return [{"praefix": "backup-" if i == 0 else "kv-backup-", "alter_h": a,
                 "stufe": ("fehler" if a is None or a > bg.MAX_ALTER_ROT_H
                           else "warnung" if a > bg.MAX_ALTER_GELB_H else "ok")}
                for i, a in enumerate(alter)]

    def test_frisch_bedeutet_kein_anstioss(self):
        self.assertEqual(bs.entscheide(self._befunde(10, 11))["aktion"], "nichts")

    def test_verpasstes_tagesfenster_wird_geheilt_bevor_es_rot_wird(self):
        """26 h ist das Tagesfenster, 52 h die Meldung. Die Heilung greift FRÜHER."""
        self.assertEqual(bs.entscheide(self._befunde(bs.HEILUNG_AB_H, bs.HEILUNG_AB_H))["aktion"],
                         "nichts", "genau 26 h ist noch kein verpasstes Fenster")
        self.assertEqual(bs.entscheide(self._befunde(bs.HEILUNG_AB_H + 1,
                                                     bs.HEILUNG_AB_H + 1))["aktion"],
                         "anfordern", "27 h = Tagesfenster verpasst – 26 h vor der 52-h-Meldung")
        self.assertLess(bs.HEILUNG_AB_H, bg.MAX_ALTER_GELB_H,
                        "die Heilung muss vor der ersten Warnstufe greifen")

    def test_fehlende_familie_ist_bedarf(self):
        e = bs.entscheide(self._befunde(None, 3))
        self.assertEqual(e["aktion"], "anfordern")
        self.assertIn("backup-", e["bedarf"])

    def test_laufende_sicherung_wird_nicht_doppelt_gestartet(self):
        e = bs.entscheide(self._befunde(None, None), aktiver_lauf=True)
        self.assertEqual(e["aktion"], "warten")
        self.assertIn("kein zweiter Anstoß", e["grund"])

    def test_mindestabstand_verhindert_doppellauf(self):
        e = bs.entscheide(self._befunde(None, None), letzter_lauf_min=bs.MINDESTABSTAND_MIN - 1)
        self.assertEqual(e["aktion"], "warten")
        e = bs.entscheide(self._befunde(None, None), letzter_lauf_min=bs.MINDESTABSTAND_MIN)
        self.assertEqual(e["aktion"], "anfordern")

    def test_budget_beendet_das_dauerfeuer(self):
        e = bs.entscheide(self._befunde(None, None), versuche_24h=bs.MAX_VERSUCHE_24H)
        self.assertEqual(e["aktion"], "aufgeben")
        self.assertIn("Budget", e["grund"])
        self.assertEqual(bs.entscheide(self._befunde(None, None),
                                       versuche_24h=bs.MAX_VERSUCHE_24H - 1)["aktion"],
                         "anfordern")

    def test_reihenfolge_der_sicherungen(self):
        """Laufende Sicherung schlägt Budget – sonst würde ein laufender Lauf „aufgegeben“."""
        e = bs.entscheide(self._befunde(None, None), aktiver_lauf=True, versuche_24h=99)
        self.assertEqual(e["aktion"], "warten")

    def test_jede_entscheidung_begruendet_sich(self):
        for befunds, kwargs in (
                (self._befunde(5, 5), {}),
                (self._befunde(60, 60), {}),
                (self._befunde(None, None), {"aktiver_lauf": True}),
                (self._befunde(None, None), {"versuche_24h": 99})):
            with self.subTest(**{k: str(v) for k, v in kwargs.items()}):
                self.assertTrue(bs.entscheide(befunds, **kwargs)["grund"].strip())


class Heilungskreis(unittest.TestCase):
    def test_verpasster_tag_wird_geheilt_und_zweimal_gemessen(self):
        seite = welt(releases=[], laeufe=lambda z: ([] if not z["stoesse"] else
                                                    [{"id": 99, "status": "completed",
                                                      "conclusion": "success",
                                                      "event": "workflow_dispatch",
                                                      "created_at": "2026-11-07T13:00:05Z",
                                                      "html_url": "https://x/runs/99"}]),
                     messung_zwei=FRISCH)
        r = heile(seite)
        self.assertEqual(len(seite.zustand["stoesse"]), 1, "genau ein Anstoß je Lauf")
        self.assertEqual(seite.zustand["messen"], 2, "vor UND nach dem Anstoß messen")
        self.assertEqual(r["urteil"], "ok", "die zweite Messung entscheidet")
        self.assertTrue(r["heilung"]["gestartet"])
        self.assertEqual(r["heilung"]["lauf_url"], "https://x/runs/99")

    def test_anstioss_ist_ein_dispatch_auf_main(self):
        seite = welt(releases=[], laeufe=lambda z: ([] if not z["stoesse"] else
                                                    [{"id": 99, "status": "completed",
                                                      "conclusion": "success",
                                                      "event": "workflow_dispatch",
                                                      "created_at": "2026-11-07T13:00:05Z"}]),
                     messung_zwei=FRISCH)
        heile(seite)
        stoss = seite.zustand["stoesse"][0]
        self.assertEqual(stoss["methode"], "POST")
        self.assertTrue(stoss["url"].endswith("/actions/workflows/backup-offsite.yml/dispatches"))
        self.assertEqual(stoss["koerper"], {"ref": "main"})

    def test_gescheiterter_lauf_wird_nicht_gruen(self):
        seite = welt(releases=[],
                     laeufe=lambda z: ([] if not z["stoesse"] else
                                       [{"id": 99, "status": "completed", "conclusion": "failure",
                                         "event": "workflow_dispatch",
                                         "created_at": "2026-11-07T13:00:05Z",
                                         "html_url": "https://x/runs/99"}]))
        # Die Attrappe liefert bei der zweiten Messung weiterhin eine Hülle.
        r = heile(seite)
        self.assertEqual(r["urteil"], "fehler")
        self.assertIn("failure", r["heilung"]["grund"])
        self.assertTrue(r["heilung"]["gestartet"])

    def test_fehlt_das_recht_bleibt_es_rot_mit_grund(self):
        seite = welt(releases=[], laeufe=[], dispatch=403)
        r = heile(seite)
        self.assertEqual(r["urteil"], "fehler")
        self.assertFalse(r["heilung"]["gestartet"])
        self.assertIn("actions: write", r["heilung"]["grund"])

    def test_ohne_historie_kein_blinder_anstioss(self):
        def kaputt(methode, url, token, koerper=None):
            if "/releases" in url:
                return 200, [], ""
            return 500, None, "ServerError"

        r = heile(kaputt)
        self.assertEqual(r["heilung"]["aktion"], "aufgeben")
        self.assertFalse(r["heilung"]["gestartet"])

    def test_laufende_sicherung_verhindert_den_anstioss(self):
        laufend = [{"id": 5, "status": "in_progress", "event": "schedule",
                    "created_at": "2026-11-07T12:50:00Z", "html_url": "https://x/runs/5"}]
        seite = welt(releases=[], laeufe=laufend)
        r = heile(seite)
        self.assertEqual(r["heilung"]["aktion"], "warten")
        self.assertEqual(seite.zustand["stoesse"], [])

    def test_probe_stoesst_nie_an(self):
        seite = welt(releases=[], laeufe=[])
        r = heile(seite, anstossen=False)
        self.assertEqual(seite.zustand["stoesse"], [])
        self.assertIn("Probe", r["heilung"]["grund"])

    def test_frischer_bestand_beruehrt_die_lauf_api_nicht(self):
        def nur_releases(methode, url, token, koerper=None):
            if "/releases" in url:
                return 200, FRISCH, ""
            raise AssertionError(f"die Lauf-API darf ohne Bedarf nicht gerufen werden: {url}")

        r = heile(nur_releases)
        self.assertEqual(r["urteil"], "ok")
        self.assertEqual(r["heilung"]["aktion"], "nichts")

    def test_huelle_ist_kein_gruen(self):
        huelle = _releases(("backup-20261107-0300", "2026-11-07T03:00:00Z", 0),
                           ("kv-backup-20261107-0301", "2026-11-07T03:01:00Z", 1))
        seite = welt(releases=huelle, laeufe=[], messung_zwei=huelle)
        r = heile(seite)
        self.assertEqual(r["urteil"], "fehler")
        self.assertIn("Hülle", r["befunde"][0]["text"])


class EndpunktVertrag(unittest.TestCase):
    """Die Rechte-Erweiterung (actions: write) bleibt auf drei Aufrufe begrenzt."""

    def setUp(self):
        self.text = (SCRIPTS / "backup_selbstheilung.py").read_text(encoding="utf-8")

    def test_endpunktliste_ist_festgenagelt(self):
        self.assertEqual(bs.ENDPUNKTE, (
            "/repos/{quelle}/actions/workflows/{workflow}/runs?per_page=30",
            "/repos/{quelle}/actions/workflows/{workflow}/dispatches",
            "/repos/{quelle}/actions/runs/{lauf_id}",
        ))
        # Kein vierter Pfad, keine fremde API.
        self.assertNotIn("api.cloudflare.com", self.text)
        self.assertNotIn("graphql", self.text.lower())
        self.assertEqual(self.text.count("GH_API}"), 3,
                         "genau drei GitHub-Pfade – jeder weitere erweitert die Rechte")

    def test_anstioss_ist_post_und_sonst_nichts(self):
        self.assertIn('http("POST", url, token, {"ref": branch})', self.text)
        self.assertNotIn('"DELETE"', self.text)
        self.assertNotIn('"PUT"', self.text)
        self.assertNotIn('"PATCH"', self.text)

    def test_ziel_token_darf_nicht_anstiossen(self):
        """Der fein eingeschränkte Ziel-Token liest – er stößt nicht an."""
        self.assertEqual(bs.aktion_token({"BACKUP_REPO_TOKEN": "ziel", "GH_TOKEN": "ziel"}), "")
        self.assertEqual(bs.aktion_token({"AKTION_TOKEN": "lauf"}), "lauf")
        self.assertEqual(bs.lese_token({"BACKUP_REPO_TOKEN": "ziel", "AKTION_TOKEN": "lauf"}),
                         "ziel")


class WorkflowVertrag(unittest.TestCase):
    def setUp(self):
        if yaml is None:
            raise unittest.SkipTest("PyYAML lokal nicht installiert (CI installiert es)")
        self.daten = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        self.job = self.daten["jobs"]["frischwache"]
        self.schritte = {s.get("name", ""): s for s in self.job["steps"]}

    def _schritt(self, wort: str) -> dict:
        treffer = [s for s in self.job["steps"] if wort in s.get("name", "")]
        self.assertEqual(len(treffer), 1, f"erwartet genau einen Schritt mit „{wort}“")
        return treffer[0]

    def test_messung_urteilt_nicht_mehr_selbst(self):
        messung = self._schritt("Frische messen")
        self.assertEqual(messung.get("id"), "messung")
        run = messung["run"]
        self.assertIn('echo "urteil=$URTEIL" >> "$GITHUB_OUTPUT"', run)
        self.assertIn('echo "gemessen=true" >> "$GITHUB_OUTPUT"', run)
        # Kein rotes Urteil mehr im Messschritt: das fällt der Schluss-Schritt.
        self.assertIn("exit 0", run)

    def test_messung_bleibt_bei_fehlenden_eingaben_rot(self):
        run = self._schritt("Frische messen")["run"]
        self.assertIn("BACKUP_REPO oder BACKUP_REPO_TOKEN fehlt", run)
        self.assertIn("exit 1", run)

    def test_selbstheilung_ist_verdrahtet_und_begrenzt(self):
        heilung = self._schritt("Selbstheilung")
        bedingung = heilung.get("if", "")
        self.assertIn("steps.messung.outputs.gemessen == 'true'", bedingung)
        self.assertIn("steps.messung.outputs.urteil != 'ok'", bedingung)
        self.assertEqual(heilung.get("env", {}).get("AKTION_TOKEN"), "${{ github.token }}",
                         "nur der Heilungs-Schritt sieht das Lauf-Token")
        run = heilung["run"]
        self.assertIn("scripts/backup_selbstheilung.py --heilen", run)
        self.assertIn("--ausgabe /tmp/frische_final.json", run)

    def test_nur_der_heilungsschritt_hat_das_dispatch_recht(self):
        """Das Lauf-Token steht in genau zwei Schritten – beide mit eigenem Grund.

        „Voraussetzungen prüfen“ liest damit die Environment-Regeln (E8), die
        der Ziel-Token nicht sehen darf (#923); „Selbstheilung“ stößt damit den
        Lauf an. Die Messung dazwischen bleibt beim fein eingeschränkten
        Ziel-Token – sonst läge das Dispatch-Recht über dem ganzen Lauf.
        """
        self.assertEqual(self.job.get("permissions"), {"contents": "read", "actions": "write"})
        mit_lauf_token = [name for name, schritt in self.schritte.items()
                          if "github.token" in str(schritt.get("env", {}))]
        self.assertEqual(sorted(mit_lauf_token),
                         sorted([self._schritt("Voraussetzungen prüfen")["name"],
                                 self._schritt("Selbstheilung")["name"]]))
        self.assertNotIn("github.token", str(self._schritt("Frische messen").get("env", {})))

    def test_schlussurteil_ist_fail_closed_und_kommt_nach_der_heilung(self):
        namen = [s.get("name", "") for s in self.job["steps"]]
        urteil = self._schritt("Urteil fällen")
        self.assertEqual(namen[-1], urteil["name"], "das Urteil muss der letzte Schritt sein")
        self.assertGreater(namen.index(urteil["name"]), namen.index(self._schritt("Selbstheilung")["name"]))
        self.assertIn("always()", urteil.get("if", ""))
        run = urteil["run"]
        self.assertIn("/tmp/frische_final.json", run)
        self.assertIn("sys.exit(1)", run)
        self.assertIn("ohne Messung kein Gruen", run)

    def test_kein_schein_gruen_im_ganzen_job(self):
        for schritt in self.job["steps"]:
            self.assertNotIn("continue-on-error", str(schritt),
                             "kein Schritt darf einen roten Befund stillschweigend grün machen")
        run = self._schritt("Frische messen")["run"]
        # Der Auswertungspfad ist fail-closed: leeres Urteil → exit 1.
        self.assertIn('if [ -z "$URTEIL" ]; then', run)
        self.assertIn("ohne Messung kein Gruen", run)

    def test_trigger_wache_kennt_die_neue_datei(self):
        pfade = self.daten[True]["push"]["paths"] if True in self.daten else self.daten["on"]["push"]["paths"]
        self.assertIn("scripts/backup_selbstheilung.py", pfade)
        self.assertIn("scripts/tests/test_backup_selbstheilung.py", pfade)

    def test_anleitung_und_alerting_verweisen_auf_die_selbstheilung(self):
        anleitung = (REPO / bs.ANLEITUNG).read_text(encoding="utf-8")
        self.assertIn("Selbstheilung", anleitung)
        alarm = (REPO / ".github" / "workflows" / "alert-on-failure.yml").read_text(encoding="utf-8")
        self.assertIn("selbst", alarm.lower())
        # Der Rat der Klasse backup-frisch darf die Heilung nicht verschweigen.
        self.assertIn("stößt", alarm)


class FrischeHuelleVertrag(unittest.TestCase):
    """Die Frische-Wache zählt seit dem 07.11.2026 auch den INHALT."""

    @staticmethod
    def _pruefe(releases):
        return bg.pruefe_freshness("a/b", "tok", JETZT, lambda url: (200, releases, ""))

    def test_gefuellte_releases_sind_ok(self):
        self.assertEqual(self._pruefe(copy.deepcopy(FRISCH))["urteil"], "ok")

    def test_huelle_ohne_assets_ist_rot(self):
        huelle = _releases(("backup-20261107-0300", "2026-11-07T03:00:00Z", 0),
                           ("kv-backup-20261107-0301", "2026-11-07T03:01:00Z", 1))
        r = self._pruefe(huelle)
        self.assertEqual(r["urteil"], "fehler")
        self.assertIn("Hülle", r["befunde"][0]["text"])
        self.assertIn("0 Assets", r["befunde"][0]["text"])

    def test_fehlende_asset_liste_ist_kein_gruen(self):
        kaputt = copy.deepcopy(FRISCH)
        kaputt[0]["assets"] = None
        r = self._pruefe(kaputt)
        self.assertEqual(r["urteil"], "fehler")
        self.assertIn("Asset-Liste", r["befunde"][0]["text"])


if __name__ == "__main__":
    unittest.main()
