"""Regressionstests für die FM-Grenzen-Wache (Bau-Ursache 11.09.2026).

Ein unquotierter Wert, der mit '*' beginnt (UWG-Prefix '*Werbung | …' in
pin_description), wird von YAML als Alias gelesen – Hugo verliert das
Frontmatter und der gesamte Deploy stirbt im Bauschritt. Diese Tests halten
drei Dinge fest: (1) die Wache findet genau diese Klasse, (2) die Heilung
verändert ausschließlich die Quote-Ebene und ist konvergent, (3) legale
Konstrukte (Flow-Sequences mit Doppelpunkt im Element) bleiben unangetastet.

Seit 18.09.2026 zusätzlich: Regel F6 (geklebte Schlussgrenze `---Text`).
Ursache waren zwei echte Produzenten – `keyword_optimizer.heal_first_paragraph`
verlor den führenden Umbruch des ersten Absatzes (Commit 6c772fd, 9 Dateien),
`redaktions_standard` schrieb die KI-Antwort samt Prompt-Gerüst („TITEL: … /
ARTIKEL:") zurück (7b51187). Der Bestand ist geheilt; diese Tests halten fest,
dass die Klasse erkannt, ohne `--fix` baukritisch gemeldet und mit `--fix`
bytegleich bis auf die Naht geheilt wird – und dass die Naht-SSOT
(`post_utils.join_article`/`split_article`) nicht mehr kleben kann.
"""
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import fm_boundary_guard as fm  # noqa: E402
import post_utils  # noqa: E402  – Naht-SSOT (join/split/heal)

try:
    import yaml
except Exception:                                        # pragma: no cover
    yaml = None


BAD_PIN = 'pin_description: *Werbung | Der Traumurlaub scheitert am Budget?'
GOOD_PIN = 'pin_description: "*Werbung | Der Traumurlaub scheitert am Budget?"'


class WertEbeneTests(unittest.TestCase):
    def test_werbung_alias_wird_erkannt(self):
        if yaml is not None:
            self.assertTrue(fm.find_defects([BAD_PIN]),
                            "Hugo-Bau-Abbruch muss als baukritisch gelten")

    def test_heilung_quotet_nur_den_wert(self):
        self.assertEqual(fm.heal_line(BAD_PIN), GOOD_PIN)

    def test_heilung_ist_konvergent(self):
        self.assertFalse(fm.find_defects([GOOD_PIN]))

    def test_flow_sequence_mit_doppelpunkt_ruht(self):
        zeile = 'tags: ["Energie-Update: was sich jetzt ändert", "Strom"]'
        self.assertFalse(fm.find_defects([zeile]),
                         "legale Liste darf nicht umgeschrieben werden – "
                         "sonst wird sie durch die Heilung zu einem String")

    def test_plain_scalar_ruht(self):
        for zeile in ("pillar: mietwagen", "draft: false",
                      "date: 2026-09-11T11:17:28Z",
                      "pinwand: Günstig reisen | Reisebudget & Mietwagen"):
            self.assertFalse(fm.find_defects([zeile]), zeile)

    @unittest.skipIf(yaml is None, "Gegenprüfung braucht PyYAML")
    def test_round_trip_jedes_haesslichen_werts(self):
        for wert in ('*Werbung | Test: 500 €', ': führend', '- listig',
                     'a: b', 'text # Kommentar', 'sagt "hi" \\back',
                     'mehr\nzeilig', '  lead', 'trail ', '', 'normal'):
            quotiert = fm.yaml_quote(wert)
            geladen = yaml.safe_load("key: " + quotiert + "\n")
            self.assertEqual(geladen.get("key"), wert,
                             f"{wert!r} → {quotiert!r} → {geladen!r}")


# ---------------------------------------------------------------- Grenzen
class GrenzeTests(unittest.TestCase):
    def test_geschlossener_block(self):
        zeilen, begin, ende = fm.split_fm("---\ntitle: x\n---\nBody\n")
        self.assertEqual((begin, ende), (1, 2))
        self.assertEqual(zeilen, ["title: x"])

    def test_hugo_moegliche_kleber_grenze_ruht(self):
        # Hugo schließt an der ERSTEN Zeile, die mit --- beginnt.
        zeilen, _begin, ende = fm.split_fm("---\ntitle: x\n---Warum zahlen…\n")
        self.assertIsNotNone(ende)
        self.assertEqual(fm.closing_glue("---\ntitle: x\n---Warum zahlen…\n"),
                         "Warum zahlen…")

    def test_fehtende_grenzen_melden(self):
        self.assertEqual(fm.split_fm("title: x\n---\nBody\n")[0], None)
        self.assertIsNone(fm.split_fm("---\ntitle: x\nBody\n")[2])


# ---------------------------------------------------------------- Heilung im Bestand
class BestandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fmtest-"))
        self.alt_dir = self.tmp / "content" / "posts" / "demo"
        self.alt_dir.mkdir(parents=True)
        (self.tmp / "content" / "posts" / "demo" / "index.md").write_text(
            "---\ntitle: Reisekasse: 7 Tipps\n" + BAD_PIN +
            "\ndraft: true\n---\n\nText.\n", encoding="utf-8")
        self._pf, self._rep = fm.content_files, fm.REPORT
        fm.content_files = lambda: sorted(
            str(q) for q in (self.tmp / "content").rglob("*.md"))
        fm.REPORT = str(self.tmp / "FM-GRENZEN-REPORT.md")

    def tearDown(self):
        fm.content_files, fm.REPORT = self._pf, self._rep
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_fix_heilt_bei_gleichem_text(self):
        datei = self.alt_dir / "index.md"
        vorher = datei.read_text(encoding="utf-8")
        fm.run(fix=True)
        nachher = datei.read_text(encoding="utf-8")
        self.assertIn('title: "Reisekasse: 7 Tipps"', nachher)
        self.assertIn(GOOD_PIN, nachher)
        self.assertIn("\n\nText.\n", nachher)          # Body bytegleich
        self.assertEqual(preher_body(nachher), preher_body(vorher))
        # zweiter Lauf: nichts mehr zu tun (Konvergenz)
        fm.run(fix=True)
        self.assertEqual(datei.read_text(encoding="utf-8"), nachher)

    def test_unheilbarer_grenzfehler_wird_nicht_angefasst(self):
        (self.alt_dir / "kaputt.md").write_text(
            "---\ntitle: ohne schluss\nBody, der zum Frontmatter wird\n",
            encoding="utf-8")
        datei = self.alt_dir / "kaputt.md"
        vorher = datei.read_text(encoding="utf-8")
        hart, _hin, _heil, unheilbar, residual, _g = fm.run(fix=True)
        self.assertEqual([h[1] for h in hart if h[1] == "F2"], ["F2"])
        self.assertEqual(datei.read_text(encoding="utf-8"), vorher)
        self.assertTrue(residual or unheilbar)


# ---------------------------------------------------------------- F6 Klebefuge
class KleberFugeTests(unittest.TestCase):
    """F6: geklebte Schlussgrenze erkennen, hart melden, mit --fix heilen.

    Die Fixtures sind die zwei REALEN Produzenten-Muster des Bestands:
    `keyword_optimizer` („Du willst x? …" direkt an der Grenze) und
    `redaktions_standard` (KI-Antwort mit Prompt-Gerüst „TITEL: …/ARTIKEL:").
    """

    KLEBER = ("---\ntitle: Klebefuge\ndraft: true\n---Du willst gaspreis "
              "sparen? So geht's.\n\nZweiter Absatz steht.\n")
    GERUEST = ("---\ntitle: Turbolader\ndraft: true\n---TITEL: Turbolader\n\n"
               "ARTIKEL:\n\nKlickst du auf einen Link?\n\nMehr Text.\n")

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fmfuge-"))
        self.dir = self.tmp / "content" / "posts" / "demo"
        self.dir.mkdir(parents=True)
        self.datei = self.dir / "index.md"
        self.datei.write_text(self.KLEBER, encoding="utf-8")
        self._pf, self._rep = fm.content_files, fm.REPORT
        fm.content_files = lambda: sorted(
            str(q) for q in (self.tmp / "content").rglob("*.md"))
        fm.REPORT = str(self.tmp / "FM-GRENZEN-REPORT.md")

    def tearDown(self):
        fm.content_files, fm.REPORT = self._pf, self._rep
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_check_meldet_f6_baukritisch_und_laesst_die_datei_ruhen(self):
        vorher = self.datei.read_text(encoding="utf-8")
        hart, kleber, heilungen, unheilbar, _residual, _geprueft = fm.run(fix=False)
        self.assertIn("F6", [h[1] for h in hart],
                      "ohne --fix muss der Kleber baukritisch sein (Exit 1)")
        self.assertEqual([k[1] for k in kleber], ["F6"])
        self.assertFalse(heilungen and unheilbar)
        self.assertEqual(self.datei.read_text(encoding="utf-8"), vorher,
                         "ein Prüflauf darf nie schreiben (Vertragsregel C15)")

    def test_fix_trennt_die_naht_und_erhaelt_den_text(self):
        fm.run(fix=True)
        text = self.datei.read_text(encoding="utf-8")
        self.assertIsNone(post_utils.glued_close(text)[0])
        self.assertTrue(text.startswith(
            "---\ntitle: Klebefuge\ndraft: true\n---\n\n"
            "Du willst gaspreis sparen? So geht's.\n\nZweiter Absatz steht.\n"))
        # Bytegleich bis auf die Naht: keine Zeile verloren, keine erfunden.
        self.assertEqual(text.replace("---\n\n", "---", 1), self.KLEBER)

    def test_fix_ist_konvergent(self):
        fm.run(fix=True)
        einmal = self.datei.read_text(encoding="utf-8")
        _hart, kleber, _heil, _unh, residual, _g = fm.run(fix=True)
        self.assertEqual(kleber, [])
        self.assertEqual(residual, [])
        self.assertEqual(self.datei.read_text(encoding="utf-8"), einmal)

    def test_prompt_geruest_verschwindet_und_der_einstieg_bleibt(self):
        self.datei.write_text(self.GERUEST, encoding="utf-8")
        _hart, kleber, _heil, _unh, _res, _g = fm.run(fix=True)
        self.assertTrue(kleber and kleber[0][3],
                        "die Gerüst-Entfernung muss im Befund belegt sein")
        text = self.datei.read_text(encoding="utf-8")
        self.assertNotIn("TITEL:", text)
        self.assertNotIn("ARTIKEL:", text)
        self.assertIn("Klickst du auf einen Link?", text)

    def test_naht_ssot_klebt_nie_und_verliert_nie(self):
        for fragment in ("Text.", "\nText.", "\n\n\nText.", "Text.\n",
                         "\n\n  Text mit Einzug."):
            datei = post_utils.join_article("title: x", fragment)
            self.assertIsNone(post_utils.glued_close(datei)[0],
                              f"join_article klebt bei {fragment!r}")
            self.assertEqual(post_utils.split_article(datei)[2].lstrip("\n"),
                             fragment.lstrip("\n"),
                             f"join/split verliert Text bei {fragment!r}")


def preher_body(text):
    """Alles ab der Schlussgrenze (Body) – muss durch Heilung gleich bleiben."""
    _zeilen, _begin, ende = fm.split_fm(text)
    return "\n".join(text.split("\n")[ende:]) if ende else text


if __name__ == "__main__":
    unittest.main()
