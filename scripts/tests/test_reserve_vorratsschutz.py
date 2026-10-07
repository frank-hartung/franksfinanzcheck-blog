"""Regressionstests für den Vorratsschutz der Content-Reserve (BOT-WATCHDOG #614).

Warum diese Tests existieren
----------------------------
Am 07.10.2026 endete der Produktionslauf 37645894042 mit dem Zertifikat
„2 bereit, Pool 2" – zwölf Entwürfe waren in den Vorrat gegangen, zehn
Kandidaten hatten in EINEM Lauf ihre `reserve: true`-Fahne verloren. Die
Ursache war nicht der Inhalt, sondern die Politik der Automatik:

    `reserve_quarantine` zählte nur LÄUFE mit demselben Befund („zwei Läufe,
    dann ausmustern") und fragte nie nach der KLASSE. Alle zehn Befunde
    standen aber in `reserve_blocker_klassen.GATE_BEFUNDE` als heilbar –
    sechs davon allein am Lesbarkeits-Gate, für das die Kette inzwischen
    Heiler mit grüner Wirkungsprobe fährt.

Der Vorrat ist der Puffer der Redaktion. Wer ihn für eine Reparatur
bestraft, die die Automatik selbst noch vor sich hat, verliert genau dann
Material, wenn es gebraucht wird. Genau diese Klasse frieren die Tests ein:

1) **Der Vorfall als Vertrag** – die zehn Original-Befunde (Wortlaut aus dem
   Lauf) dürfen in zwei Läufen keine Fahne kosten. Vorher: 10 von 10
   ausgemustert. Nachher: 0 von 10 – und der Pool bleibt vollständig.
2) **Ausmusterung nur für Unheilbares** – Dubletten/Torsi verlieren die Fahne
   weiterhin (die Zusage #295 bleibt scharf), unbekannte Befunde bleiben
   fail-closed im Pool.
3) **Rückholung mit Beweis** – ein ausgemusterter Kandidat kehrt zurück, wenn
   seine Befund-Klasse heilbar ist UND ein Heiler dieser Klasse mit grünem
   Wirkungsnachweis in der Kette läuft. Ohne Nachweis bleibt er ausgemustert;
   ein Trockenlauf schreibt nichts; die Rückholung ist idempotent.
4) **Verdrahtung** – der Satz-Heiler heilt die Lesbarkeits-Klasse satzweise
   (Kettenglied vor dem Lesbarkeits-Heiler), die Deckung kennt ihn, das
   Regelwerk verlangt ihn, und der Maschinenbeweis läuft grün.

Alle Tests laufen ohne Netz, ohne hugo, ohne KI-Schlüssel und schreiben
ausschließlich in temporäre Verzeichnisse.
"""
import datetime as dt
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import reserve_blocker_klassen as bk  # noqa: E402
import reserve_custody as cu  # noqa: E402
import reserve_finisher as fin  # noqa: E402
import reserve_healer_coverage as rhc  # noqa: E402
import reserve_quarantine as rq  # noqa: E402

# Die zehn `reserve_blocked`-Gründe des Vorfalls, wörtlich von `main`
# (Lauf 37645894042, 07.10.2026). Sie sind Beweismittel, keine Beispiele.
VORFALL_GRUENDE = (
    'Lesbarkeits-Gate nicht bestanden: Flesch 58.0 (Mindestwert 60) – ein '
    'Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach '
    'unten (#585)',
    'Lesbarkeits-Gate nicht bestanden: Flesch 59.4 (Mindestwert 60) – ein '
    'Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach '
    'unten (#585)',
    'Lesbarkeits-Gate nicht bestanden: Flesch 59.9 (Mindestwert 60) – ein '
    'Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach '
    'unten (#585)',
    'Lesbarkeits-Gate nicht bestanden: Flesch 58.8 (Mindestwert 60) – ein '
    'Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach '
    'unten (#585)',
    'Lesbarkeits-Gate nicht bestanden: Flesch 55.8 (Mindestwert 60) – ein '
    'Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach '
    'unten (#585)',
    'Lesbarkeits-Gate nicht bestanden: Flesch 53.1 (Mindestwert 60) – ein '
    'Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach '
    'unten (#585)',
    'Lesbarkeits-Gate nicht bestanden: Lesbarkeits-Score 70/100 (Mindestwert '
    '75): Flesch 52 (Ziel ≥ 60); 2 Absätze > 4 Sätze; 9 '
    'Passiv-Formulierungen; Flesch 52.3 (Mindestwert 60) – ein',
    'Zeichenlänge (check_length.py) nicht bestanden',
    'quality-score 0.839 < 0.85 (schwach: structure 0.70, readability 0.75, '
    'typography 0.84)',
    'Textverständnis-Gate nicht bestanden: R14-MARKER-RUINE: Politur-Ruine '
    '„SATZ:“ – Überrest eines automatisierten Politur-Laufs, manuell '
    'reparieren',
)

LESBARKEIT_GRUND = VORFALL_GRUENDE[0]
UNHEILBAR_GRUND = ('Dublette: identischer Inhalt zu '
                   '2026-09-01-energie-update-tarife (0.97)')


def _post(posts: Path, slug: str, frontmatter: str) -> Path:
    ordner = posts / slug
    ordner.mkdir(parents=True, exist_ok=True)
    ziel = ordner / "index.md"
    ziel.write_text(f"---\n{frontmatter}\n---\n\nText.\n", encoding="utf-8")
    return ziel


def _pool_post(posts: Path, slug: str) -> Path:
    return _post(posts, slug, 'title: "Kandidat"\ndate: 2026-10-07\n'
                              'draft: true\nreserve: true')


def _ausgemustert(posts: Path, slug: str, grund: str) -> Path:
    return _post(posts, slug,
                 'title: "Ausgemustert"\ndate: 2026-10-07\ndraft: true\n'
                 f'reserve_blocked: "{grund}"\n'
                 'reserve_blocked_at: 2026-10-07T16:07:55Z')


class VorfallTests(unittest.TestCase):
    """Der 07.10.2026 darf sich nicht wiederholen – als Maschinenvertrag."""

    def test_zehn_original_befunde_kosten_keine_fahne(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            zustand = Path(tmp) / "quarantaene.json"
            for i, grund in enumerate(VORFALL_GRUENDE):
                _pool_post(posts, f"kandidat-{i}")
                blockiert, geschont = [], []
                for lauf in ("run:37645894042", "run:37645894043"):
                    blockiert += rq.record(
                        [{"slug": f"kandidat-{i}", "ready": False,
                          "reason": grund}], zustand, posts, apply=True,
                        run_key=lauf, geschont_out=geschont)
                self.assertEqual(blockiert, [],
                                 f"Fahne verloren für: {grund[:60]}")
                text = (posts / f"kandidat-{i}" / "index.md").read_text("utf-8")
                self.assertIn("reserve: true", text, grund[:60])
                self.assertNotIn("reserve_blocked", text, grund[:60])
                self.assertTrue(geschont, f"Schonung nicht begründet: {grund[:60]}")

    def test_pool_bleibt_vollstaendig_statt_12_auf_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            zustand = Path(tmp) / "quarantaene.json"
            for i in range(len(VORFALL_GRUENDE)):
                _pool_post(posts, f"kandidat-{i}")
            for lauf in ("run:a", "run:b"):
                rq.record([{"slug": f"kandidat-{i}", "ready": False,
                            "reason": VORFALL_GRUENDE[i]}
                           for i in range(len(VORFALL_GRUENDE))],
                          zustand, posts, apply=True, run_key=lauf)
            im_pool = [p for p in posts.glob("*/index.md")
                       if "reserve: true" in p.read_text(encoding="utf-8")]
            self.assertEqual(len(im_pool), len(VORFALL_GRUENDE),
                             "Der Vorfall darf den Pool nicht mehr leeren")

    def test_jeder_vorfall_grund_ist_einer_klasse_zugeordnet(self):
        for grund in VORFALL_GRUENDE:
            bewertung = bk.gate_befund_klasse(grund)
            self.assertTrue(bewertung["bekannt"],
                            f"Vorfall-Befund ohne Klasse: {grund[:60]}")
            self.assertEqual(bewertung["klasse"], bk.HEILBAR, grund[:60])


class KlassenTorTests(unittest.TestCase):
    """Ausmustern ist die Ausnahme – und sie braucht einen Grund."""

    def test_unheilbarer_befund_mustert_weiterhin_aus(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            _pool_post(posts, "torso")
            gemeldet = []
            for lauf in ("run:1", "run:2"):
                gemeldet += rq.record([{"slug": "torso", "ready": False,
                                        "reason": UNHEILBAR_GRUND}],
                                      Path(tmp) / "q.json", posts, apply=True,
                                      run_key=lauf)
            self.assertEqual(len(gemeldet), 1)
            text = (posts / "torso" / "index.md").read_text("utf-8")
            self.assertIn("reserve_blocked:", text)
            self.assertNotIn("reserve: true", text)

    def test_unbekannter_befund_bleibt_fail_closed_im_pool(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            _pool_post(posts, "raetsel")
            for lauf in ("run:1", "run:2"):
                rq.record([{"slug": "raetsel", "ready": False,
                            "reason": "brandneuer Befund ohne Klasse"}],
                          Path(tmp) / "q.json", posts, apply=True, run_key=lauf)
            text = (posts / "raetsel" / "index.md").read_text("utf-8")
            self.assertIn("reserve: true", text)
            self.assertNotIn("reserve_blocked", text)

    def test_geschonter_kandidat_zaehlt_weiter_und_ist_sichtbar(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            zustand = Path(tmp) / "q.json"
            _pool_post(posts, "kandidat")
            geschont: list[dict] = []
            for lauf in ("run:1", "run:2", "run:3"):
                rq.record([{"slug": "kandidat", "ready": False,
                            "reason": LESBARKEIT_GRUND}], zustand, posts,
                          apply=True, run_key=lauf, geschont_out=geschont)
            eintrag = rq.load_state(zustand)["kandidat"]
            self.assertEqual(int(eintrag["hits"]), 3)
            self.assertTrue(eintrag["geschont"])
            self.assertEqual(eintrag["klasse"], "heilbar")
            self.assertTrue(eintrag["heiler"], "Heiler-Namen fehlen")
            self.assertTrue(rq.geschonte(zustand), "Schonung nicht abrufbar")

    def test_geheilter_kandidat_verliert_den_zaehler(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            zustand = Path(tmp) / "q.json"
            _pool_post(posts, "kandidat")
            for lauf in ("run:1", "run:2"):
                rq.record([{"slug": "kandidat", "ready": False,
                            "reason": LESBARKEIT_GRUND}], zustand, posts,
                          apply=True, run_key=lauf)
            rq.record([{"slug": "kandidat", "ready": True}], zustand, posts,
                      apply=True, run_key="run:3")
            self.assertNotIn("kandidat", rq.load_state(zustand))


class RueckholungTests(unittest.TestCase):
    """Rückholung braucht einen Wirkungsnachweis – sonst bleibt sie aus."""

    def test_heilbare_klasse_mit_nachweis_kehrt_zurueck(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            pfad = Path(tmp) / "custody.json"
            ziel = _ausgemustert(posts, "rueckhol-kandidat", LESBARKEIT_GRUND)
            lage = cu.bestandsaufnahme(posts, pfad=pfad)
            zurueck = cu.rueckholen(lage, posts, jetzt=dt.date(2026, 10, 7))
            self.assertEqual([e["slug"] for e in zurueck], ["rueckhol-kandidat"])
            text = ziel.read_text(encoding="utf-8")
            self.assertIn("reserve: true", text)
            self.assertNotIn("reserve_blocked", text)
            self.assertNotIn("reserve_blocked_at", text)
            self.assertIn("reserve_reaktiviert:", text)
            self.assertIn("Wirkungsnachweis", text)
            self.assertIn("Text.", text, "Inhalt wurde angetastet")
            # Fahne steht direkt hinter draft (SSOT-Platz), nicht am Kopf-Ende
            zeilen = text.split("---")[1].strip().splitlines()
            i_draft = next(i for i, z in enumerate(zeilen)
                           if z.startswith("draft:"))
            self.assertTrue(zeilen[i_draft + 1].startswith("reserve: true"))

    def test_ohne_wirkungsnachweis_bleibt_er_ausgemustert(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            ziel = _ausgemustert(posts, "opfer", LESBARKEIT_GRUND)
            echte = fin.HEALER_CHAIN
            try:
                fin.HEALER_CHAIN = tuple(
                    e for e in echte
                    if e[0] not in ("lesbarkeit_heiler.py", "satz_heiler.py"))
                lage = cu.bestandsaufnahme(posts, pfad=Path(tmp) / "c.json")
                zurueck = cu.rueckholen(lage, posts)
            finally:
                fin.HEALER_CHAIN = echte
            self.assertEqual(zurueck, [])
            text = ziel.read_text(encoding="utf-8")
            self.assertNotIn("reserve: true", text)
            self.assertIn("reserve_blocked", text)
            self.assertEqual(lage["nicht_reaktiviert"][0]["klasse"], "heilbar")

    def test_unheilbare_klasse_bleibt_ausgemustert(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            ziel = _ausgemustert(posts, "dublette", UNHEILBAR_GRUND)
            lage = cu.bestandsaufnahme(posts, pfad=Path(tmp) / "c.json")
            self.assertEqual(cu.rueckholen(lage, posts), [])
            self.assertNotIn("reserve: true", ziel.read_text(encoding="utf-8"))

    def test_trockenlauf_schreibt_nichts(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            ziel = _ausgemustert(posts, "trocken", LESBARKEIT_GRUND)
            vorher = ziel.read_text(encoding="utf-8")
            lage = cu.bestandsaufnahme(posts, pfad=Path(tmp) / "c.json")
            zurueck = cu.rueckholen(lage, posts, dry_run=True)
            self.assertEqual(len(zurueck), 1)
            self.assertEqual(ziel.read_text(encoding="utf-8"), vorher)

    def test_rueckholung_ist_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "posts"
            _ausgemustert(posts, "einmalig", LESBARKEIT_GRUND)
            pfad = Path(tmp) / "c.json"
            lage = cu.bestandsaufnahme(posts, pfad=pfad)
            cu.rueckholen(lage, posts)
            stand = (posts / "einmalig" / "index.md").read_text("utf-8")
            lage2 = cu.bestandsaufnahme(posts, pfad=pfad)
            self.assertEqual(cu.rueckholen(lage2, posts), [])
            self.assertEqual((posts / "einmalig" / "index.md")
                             .read_text("utf-8"), stand)

    def test_produktions_bestand_wird_nicht_angefasst(self):
        """Der Wächter ohne Argumente darf den ECHTEN Bestand nur lesen."""
        vorher = (ROOT / "data" / "reserve-custody.json").read_text("utf-8")
        lage = cu.bestandsaufnahme()
        self.assertIn("pool", lage)
        nachher = (ROOT / "data" / "reserve-custody.json").read_text("utf-8")
        self.assertEqual(vorher, nachher)


class VerdrahtungTests(unittest.TestCase):
    """Eine Deckung, die niemand fährt, ist Papier (#614)."""

    def _lauf(self, script: str, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPTS / script), *args],
                              cwd=ROOT, capture_output=True, text=True,
                              timeout=600)

    def test_kette_faehrt_den_satz_heiler_vor_dem_lesbarkeits_heiler(self):
        namen = [e[0] for e in fin.HEALER_CHAIN]
        self.assertIn("satz_heiler.py", namen)
        self.assertLess(namen.index("satz_heiler.py"),
                        namen.index("lesbarkeit_heiler.py"))

    def test_deckung_kennt_den_heiler_und_beweist_ihn(self):
        self.assertIn("satz_heiler.py", rhc.REGEL_HEILER["readability_failures"])
        self.assertIn("satz_heiler.py", rhc.WIRKUNGS_PROBEN)

    def test_heiler_selbsttests_gruen(self):
        for script in ("satz_heiler.py", "reserve_quarantine.py",
                       "reserve_custody.py"):
            r = self._lauf(script, "--selftest")
            self.assertEqual(r.returncode, 0, f"{script}: {r.stdout}{r.stderr}")

    def test_wirkungsprobe_des_satz_heilers_ist_maschinenvertrag(self):
        r = self._lauf("satz_heiler.py", "--wirkungsprobe")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Flesch", r.stdout)

    def test_vorratsschutz_beweis_ist_gruen(self):
        b = rhc.vorratsschutz()
        self.assertTrue(b["ok"], b["fehler"])
        self.assertEqual(b["geprueft"]["vorfall_befunde"], 7)
        self.assertEqual(b["geprueft"]["rueckgeholt"], 1)
        self.assertEqual(b["geprueft"]["rueckholung_verweigert"], 1)

    def test_workflow_faehrt_die_kette_und_das_gate(self):
        text = (ROOT / ".github" / "workflows" / "content-reserve.yml"
                ).read_text(encoding="utf-8")
        self.assertIn("reserve_finisher.py", text)
        self.assertIn("reserve_gate.py", text)

    def test_quarantaene_zustand_bleibt_versioniert(self):
        """Das Gedächtnis der Ausmusterung reist im Commit mit (#349)."""
        guard = (SCRIPTS / "reserve_stage_guard.py").read_text(encoding="utf-8")
        self.assertIn("reserve-quarantine.json", guard)


if __name__ == "__main__":
    unittest.main()
