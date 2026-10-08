"""Regressionstests: defekter Reserve-Nachweis (#661, 08.10.2026).

Der Bot-Watchdog meldete „Content-Reserve niedrig … Nachweis fehlt“, obwohl
15 Entwürfe im Pool lagen und sechs davon zertifiziert waren. Unlesbar war
allein der NACHWEIS. Drei Zusagen werden hier festgehalten:

  1. Ein defekter Snapshot ist eine EIGENE Befundklasse – der nächste Schritt
     muss die Ursache treffen (Snapshot neu ziehen), nicht „Kandidaten
     produzieren“.
  2. Die Heilung erfindet keine Reife: jedes rekonstruierte Zertifikat trägt
     den echten SHA-256 der Datei und `ready: false`.
  3. Beweismaterial (Quarantäne) wird vor dem Zurücksetzen BELEGT – die Spur
     liegt in der append-only Historie, nichts verschwindet lautlos.

Alle Tests laufen gegen Wegwerf-Verzeichnisse (nie gegen das Live-Repo).
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import reserve_artifacts as artifacts  # noqa: E402
import reserve_snapshot_heiler as heiler  # noqa: E402

ENTWURF = ('---\ntitle: "{titel}"\ndate: 2026-10-08T10:00:00Z\n'
           "draft: true\nreserve: true\n---\n\nText.\n")


class SnapshotHeilerBasis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir(parents=True)
        for slug, titel in (("2026-10-08-alpha", "Alpha"),
                            ("2026-10-08-beta", "Beta")):
            index = self.root / "content" / "posts" / slug / "index.md"
            index.parent.mkdir(parents=True, exist_ok=True)
            index.write_text(ENTWURF.format(titel=titel), encoding="utf-8")

    def kaputt(self, name, inhalt):
        (self.root / "data" / name).write_text(inhalt, encoding="utf-8")


class SnapshotHeilerTests(SnapshotHeilerBasis):
    def test_selftest_laeuft_gruen(self):
        self.assertEqual(0, heiler.run_selftest())

    def test_intakter_snapshot_ist_kein_befund(self):
        self.assertEqual([], heiler.pruefe(self.root))

    def test_defektes_zertifikat_wird_erkannt_und_geheilt(self):
        # Genau die Klasse aus #661: mitten in der Datei abgeschnitten.
        self.kaputt("reserve-readiness.json",
                    '{\n  "target": 6,\n  "ready": 6,\n  "candidates": [\n'
                    '    {\n      "slug": "2026-10-08-alpha",\n    },\n')
        befunde = heiler.pruefe(self.root)
        self.assertEqual(1, len(befunde), befunde)
        self.assertIn("reserve-readiness.json", befunde[0])

        protokoll = heiler.repariere(self.root)
        self.assertEqual([], protokoll["fehler"], protokoll)
        self.assertEqual([], protokoll["restbefunde"])
        self.assertEqual("reserve-readiness.json",
                         protokoll["geheilt"][0]["datei"])

        # Der Beweis ist wieder lesbar – und ehrlich.
        zertifikat = artifacts.read_certificate(
            self.root / "data" / "reserve-readiness.json")
        zeilen = zertifikat["candidates"]
        self.assertEqual(2, len(zeilen))
        self.assertTrue(all(z["ready"] is False for z in zeilen),
                        "Rekonstruktion darf keine Reife behaupten")
        for zeile in zeilen:
            echt = (self.root / "content" / "posts" / zeile["slug"]
                    / "index.md").read_bytes()
            self.assertEqual(hashlib_sha256(echt), zeile["sha256"])
        self.assertEqual(0, zertifikat["ready"])
        self.assertEqual(2, zertifikat["pool_size"])

    def test_heilung_ist_idempotent(self):
        self.kaputt("reserve-readiness.json", '{"target": 6, "candidates": [')
        heiler.repariere(self.root)
        vorher = (self.root / "data" / "reserve-readiness.json").read_text(
            encoding="utf-8")
        nochmal = heiler.repariere(self.root)
        self.assertEqual([], nochmal["geheilt"])
        self.assertEqual(vorher, (self.root / "data"
                                  / "reserve-readiness.json").read_text(
                                      encoding="utf-8"))

    def test_gedaechtnis_wird_aus_dem_bestand_neu_gebaut(self):
        self.kaputt("reserve-custody.json", '{"alpha": {"zustand": "pool",')
        self.assertEqual(1, len(heiler.pruefe(self.root)))
        self.assertEqual([], heiler.repariere(self.root)["fehler"])
        ledger = artifacts.read_object(self.root / "data"
                                       / "reserve-custody.json")
        self.assertIn("alpha", ledger)
        self.assertIn("beta", ledger)

    def test_quarantaene_verliert_ihren_schaden_nicht_lautlos(self):
        schaden = '{"2026-10-08-alpha": {"hits": 2,'
        self.kaputt("reserve-quarantine.json", schaden)
        self.assertEqual([], heiler.repariere(self.root)["fehler"])
        self.assertEqual({}, artifacts.read_object(
            self.root / "data" / "reserve-quarantine.json"))
        historie = (self.root / "data" / "reserve-history.jsonl").read_text(
            encoding="utf-8")
        self.assertIn("snapshot_reparatur", historie)
        self.assertIn("reserve-quarantine.json", historie)
        # Der Fingerabdruck beweist, WELCHE Bytes ersetzt wurden.
        self.assertIn(hashlib_sha256(schaden.encode("utf-8")), historie)

    def test_kommandozeile_check_und_fix(self):
        self.kaputt("reserve-readiness.json", '{"target": 6,')
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "reserve_snapshot_heiler.py"),
             "--check", "--root", str(self.root)],
            capture_output=True, text=True)
        self.assertEqual(1, proc.returncode, proc.stdout)
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "reserve_snapshot_heiler.py"),
             "--fix", "--root", str(self.root)],
            capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("geheilt", proc.stdout)

    def test_leerer_pool_ergibt_gueltiges_zertifikat(self):
        leer = self.root / "leer"
        (leer / "data").mkdir(parents=True)
        zertifikat = heiler.zertifikat_neu(leer)
        self.assertEqual([], zertifikat["candidates"])
        self.assertEqual(0, zertifikat["ready"])
        artifacts.certificate_rows(zertifikat)      # muss nicht platzen


def hashlib_sha256(daten) -> str:
    import hashlib
    return hashlib.sha256(daten).hexdigest()


class WatchdogBefundKlasseTests(SnapshotHeilerBasis):
    """Der Melder muss den Schritt nennen, der die URSACHE trifft (#661)."""

    def setUp(self):
        super().setUp()
        import bot_watchdog
        self.bw = bot_watchdog
        self.alt = bot_watchdog.BLOG_DIR
        bot_watchdog.BLOG_DIR = self.root
        self.addCleanup(setattr, bot_watchdog, "BLOG_DIR", self.alt)

    def test_defekter_nachweis_ist_eine_eigene_befundklasse(self):
        self.kaputt("reserve-readiness.json",
                    '{\n  "target": 6,\n  "candidates": [\n    {\n'
                    '      "slug": "2026-10-08-alpha",\n    },\n')
        ok, meldung = self.bw.check_content_reserve()
        self.assertFalse(ok)
        self.assertIn("Reserve-Nachweis beschädigt", meldung)
        self.assertEqual(1, len(self.bw.RESERVE_DIAGNOSE.get("beschädigt", [])))

        befund = self.bw.reserve_finding(str(meldung))
        self.assertEqual("reserve-nachweis", befund.id)
        self.assertEqual("auto", befund.owner)
        self.assertIn("reserve_snapshot_heiler.py", befund.next_step)
        # Die falsche Heilung darf nicht mehr im Ticket stehen.
        self.assertNotIn("mindestens 4 zertifizierte Kandidaten",
                         befund.next_step)

    def test_gesunder_nachweis_bleibt_beim_alten_befund(self):
        # Ohne Schaden gilt weiterhin die #462-Logik: das Zertifikat fehlt
        # ganz, also ist es ein Bestands-, kein Nachweis-Problem.
        (self.root / "data" / "reserve-readiness.json").unlink(missing_ok=True)
        ok, meldung = self.bw.check_content_reserve()
        self.assertFalse(ok)
        self.assertNotIn("Reserve-Nachweis beschädigt", meldung)
        self.assertEqual("content-reserve",
                         self.bw.reserve_finding(str(meldung)).id)


if __name__ == "__main__":
    unittest.main()
