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
import keyword_optimizer as ko  # noqa: E402
import pinterest_pin_text_sync as pin_sync  # noqa: E402
import tag_governance as tag_governance  # noqa: E402

# Der ECHTE Bestandsleser, bevor irgendein Test ihn umbiegt: Der
# Klassen-Wächter unten muss über den echten Inhalt laufen (nicht über Fixtures).
ECHTE_CONTENT_FILES = fm.content_files
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
        hart, _hin, _heil, unheilbar, residual, _g, _dups = fm.run(fix=True)
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
        (hart, kleber, heilungen, unheilbar, _residual, _geprueft,
         _doppel) = fm.run(fix=False)
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
        _hart, kleber, _heil, _unh, residual, _g, _dups = fm.run(fix=True)
        self.assertEqual(kleber, [])
        self.assertEqual(residual, [])
        self.assertEqual(self.datei.read_text(encoding="utf-8"), einmal)

    def test_prompt_geruest_verschwindet_und_der_einstieg_bleibt(self):
        self.datei.write_text(self.GERUEST, encoding="utf-8")
        _hart, kleber, _heil, _unh, _res, _g, _dups = fm.run(fix=True)
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


# ------------------------------------------------ F7 Doppelte Mapping-Schlüssel
class DoppelSchluesselTests(unittest.TestCase):
    """F7: doppelte Mapping-Schlüssel in EINER Ebene (Bau-Ursache 08.10.2026).

    Der Produktions-Build starb am 08.10.2026 (Issue #643, WF-54C4), weil fünf
    Reserve-Artikel aus einem MERGE je zwei `tags:`-Zeilen trugen. go-yaml bricht
    bei einem wiederholten Schlüssel HART ab (`mapping key "tags" already
    defined`), während jede PyYAML-Prüfung die Datei still parst (letzter Wert
    gewinnt) – die Wache lief grün und der Deploy starb erst im Bauschritt.
    Diese Tests halten die Klasse fest: Erkennen ohne Schreiben, verlustfreie
    Vereinigung bei Listen, YAML-Leseregel bei allem anderen, Konvergenz – und
    dass Sequenzlisten (`quellen: - id: …`) davon unberührt bleiben.
    """

    DOPPEL = ("---\n"
              'title: "Reisekasse: 7 Tipps"\n'
              "date: 2026-10-07T17:47:29Z\n"
              "draft: true\n"
              'tags: ["Urlaub planen", "Reisekosten"]\n'
              'tags: ["Reisebudget", "Geld sparen im Alltag"]\n'
              'categories: ["Ratgeber"]\n'
              "cover:\n"
              '  image: "images/covers/2026-10-06-x.jpg"\n'
              '  image: "images/covers/2026-10-07-x.jpg"\n'
              '  alt: "Alt"\n'
              "quellen:\n"
              '  - id: "Q1"\n'
              '    quelle: "A"\n'
              '  - id: "Q1"\n'
              '    quelle: "B"\n'
              "description: |\n"
              "  Beispieltext mit einer Zeile.\n"
              '  tags: ["kein", "Schluessel"]\n'
              "---\n\nBody.\n")
    VEREINIGUNG = 'tags: ["Urlaub planen", "Reisekosten", "Reisebudget", "Geld sparen im Alltag"]'

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="fmdup-"))
        self.dir = self.tmp / "content" / "posts" / "demo"
        self.dir.mkdir(parents=True)
        self.datei = self.dir / "index.md"
        self.datei.write_text(self.DOPPEL, encoding="utf-8")
        self._pf, self._rep = fm.content_files, fm.REPORT
        fm.content_files = lambda: sorted(
            str(q) for q in (self.tmp / "content").rglob("*.md"))
        fm.REPORT = str(self.tmp / "FM-GRENZEN-REPORT.md")

    def tearDown(self):
        fm.content_files, fm.REPORT = self._pf, self._rep
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_check_meldet_f7_baukritisch_und_schreibt_nicht(self):
        vorher = self.datei.read_text(encoding="utf-8")
        (hart, _kleber, _heil, _unh, _res, _g,
         (funde, heilungen)) = fm.run(fix=False)
        f7 = [h for h in hart if h[1] == "F7"]
        self.assertEqual(sorted(f[1] for f in funde), ["image", "tags"],
                         "top-level UND verschachtelte Doppel müssen auffallen")
        self.assertEqual(len(f7), 2, "ohne --fix ist jeder Doppel baukritisch")
        self.assertFalse(heilungen, "ein Prüflauf darf nie heilen (C15)")
        self.assertEqual(self.datei.read_text(encoding="utf-8"), vorher)

    def test_fix_vereinigt_listen_und_folgt_der_yaml_leseregel(self):
        _hart, _kleber, _heil, _unh, _res, _g, (_funde, heilungen) = fm.run(fix=True)
        text = self.datei.read_text(encoding="utf-8")
        self.assertEqual(text.count("\ntags:"), 1,
                         "nach der Heilung darf 'tags' nur noch einmal existieren")
        self.assertIn(self.VEREINIGUNG, text,
                      "die Vereinigung darf kein Element verlieren")
        self.assertNotIn("2026-10-06-x.jpg", text,
                         "Skalar-Doppel folgt der Leseregel: der letzte Wert gilt")
        self.assertIn("2026-10-07-x.jpg", text)
        self.assertIn('  - id: "Q1"\n', text)
        self.assertEqual(text.count('id: "Q1"'), 2,
                         "Sequenz-Einträge sind eigene Container – kein Fund")
        self.assertEqual(preher_body(text), preher_body(self.DOPPEL))
        notizen = [n for _r, _a, n in heilungen if n]
        self.assertTrue(any("vereinigt" in n for n in notizen),
                        "die Vereinigung muss im Report belegt sein")
        self.assertTrue(any("letzten Wert" in n for n in notizen),
                        "der verworfene Wert muss im Report stehen")

    def test_fix_ist_konvergent_und_yaml_liest_die_vereinigung(self):
        fm.run(fix=True)
        einmal = self.datei.read_text(encoding="utf-8")
        (_hart, _kleber, _heil, _unh, residual, _g, (funde, _h)) = fm.run(fix=True)
        self.assertEqual(funde, [])
        self.assertEqual(residual, [])
        self.assertEqual(self.datei.read_text(encoding="utf-8"), einmal)
        if yaml is not None:
            block = einmal.split("---\n", 2)[1]
            daten = yaml.safe_load(block)
            self.assertEqual(daten["tags"],
                             ["Urlaub planen", "Reisekosten", "Reisebudget",
                              "Geld sparen im Alltag"])
            self.assertEqual(daten["cover"]["image"],
                             "images/covers/2026-10-07-x.jpg")

    def test_blocklisten_werden_vereinigt(self):
        self.datei.write_text(
            '---\ntitle: x\ntags:\n  - "A"\n  - "B"\n'
            'tags:\n  - "B"\n  - "C"\n---\n\nBody.\n',
            encoding="utf-8")
        fm.run(fix=True)
        text = self.datei.read_text(encoding="utf-8")
        self.assertEqual(text.count("\ntags:"), 1,
                         "auch Blocklisten müssen zu EINEM Schlüssel werden")
        self.assertIn('- "A"', text)
        self.assertIn('- "C"', text)
        self.assertEqual(text.count('- "B"'), 1,
                         "Dubletten fallen bei der Vereinigung weg")
        if yaml is not None:
            self.assertEqual(
                yaml.safe_load(text.split("---\n", 2)[1])["tags"],
                ["A", "B", "C"])

    def test_staged_blob_heilt_nichts_auf_der_platte(self):
        vorher = self.datei.read_text(encoding="utf-8")
        rel = "content/posts/demo/index.md"
        (hart, _kleber, _heil, _unh, _res, _g,
         (funde, heilungen)) = fm.run(fix=True, quellen=[(rel, self.DOPPEL)])
        self.assertEqual(len(funde), 2,
                         "auch der Index-Blob muss geprüft werden (--staged)")
        self.assertFalse(heilungen)
        self.assertIn("F7", [h[1] for h in hart])
        self.assertEqual(self.datei.read_text(encoding="utf-8"), vorher,
                         "quellen=… ist ein Prüfpfad – er schreibt nie")

    def test_verschachtelter_schluessel_ist_kein_doppel(self):
        zeilen = ['tags: ["A"]', "cover:", '  tags: ["B"]', '  image: "x.jpg"']
        self.assertEqual(fm.doppelte_schluessel(zeilen), [],
                         "gleicher Name auf ANDERER Ebene ist kein Duplikat")

    def test_blockskalar_inhalt_ist_kein_schluessel(self):
        zeilen = ["description: |", '  tags: ["kein", "Schluessel"]',
                  'tags: ["A"]']
        self.assertEqual(fm.doppelte_schluessel(zeilen), [])

    def test_bestand_ist_doppelschluesselfrei(self):
        """Klassen-Wächter über den echten Bestand: kein Artikel trägt einen
        doppelten Mapping-Schlüssel – sonst stirbt der nächste Deploy."""
        if fm.content_files is not ECHTE_CONTENT_FILES:      # Fixture zur Seite
            alt = fm.content_files
            fm.content_files = ECHTE_CONTENT_FILES
            try:
                (_hart, _kleber, _heil, _unh, _res, _g,
                 (funde, _h)) = fm.run(fix=False)
            finally:
                fm.content_files = alt
        else:
            (_hart, _kleber, _heil, _unh, _res, _g,
             (funde, _h)) = fm.run(fix=False)
        self.assertEqual(funde, [],
                         "doppelte Schlüssel im Bestand – Hugo bricht hier ab")


# ------------------------------------------- F7 Schreiber-Schlussregel
class SchreiberTests(unittest.TestCase):
    """Jeder FM-Schreiber endet mit GENAU EINEM Top-Level-Feld.

    Die F7-Falle entsteht nicht nur im Merge, sondern auch im Schreiber: Wer
    `count=1` ersetzt, lässt eine zweite Zeile stehen. Der Deploy-Gate-Heiler
    (`tag_governance.schreibe_feld`) hätte die fünf Artikel dann scheinbar
    geheilt – und der Build wäre weiter gestorben (WF-54C4 #643).
    """

    DOPPEL = ('---\ntitle: "Alt"\ntitle: "Älter"\ntags: ["A"]\n'
              'tags: ["B"]\ncover:\n  image: "x.jpg"\n---\n\nBody.\n')

    def test_post_utils_schlussregel(self):
        fm = 'title: "X"\ntags:\n  - "A"\ntags:\ntitle: "Y"'
        self.assertEqual(post_utils.doppel_freies_feld(fm, "tags"),
                         'title: "X"\ntags:\n  - "A"\ntitle: "Y"')
        self.assertEqual(post_utils.doppel_freies_feld("title: x\n", "tags"),
                         "title: x\n", "ohne Fund bleibt der Block bytegleich")
        self.assertEqual(post_utils.doppel_freies_feld("  tags: x\ntags: y\n", "tags"),
                         "  tags: x\ntags: y\n",
                         "verschachtelter Schlüssel ist kein Duplikat")
        self.assertEqual(post_utils.doppel_freies_feld("tagsx: 1\n", "tags"),
                         "tagsx: 1\n", "Präfix-Verwechslung ist kein Treffer")

    def test_keyword_optimizer_fm_set_laesst_kein_duplikat_zurueck(self):
        neu = ko.fm_set(self.DOPPEL, "title", "Neu")
        self.assertEqual(neu.count("\ntitle:"), 1, neu)
        self.assertIn('title: "Neu"', neu)
        self.assertIn('tags: ["A"]', neu)
        self.assertEqual(preher_body(neu), preher_body(self.DOPPEL))
        # Fixpunkt: der zweite Lauf ändert nichts mehr.
        self.assertEqual(ko.fm_set(neu, "title", "Neu"), neu)

    def test_keyword_optimizer_fm_set_list_laesst_kein_duplikat_zurueck(self):
        neu = ko.fm_set_list(self.DOPPEL, "tags", ["Neu1", "Neu2"])
        self.assertEqual(neu.count("\ntags:"), 1, neu)
        self.assertIn('tags: ["Neu1", "Neu2"]', neu)

    def test_tag_governance_schreibe_feld_raeumt_doppel_ab(self):
        aus = tag_governance.schreibe_feld(self.DOPPEL, "tags", ["B", "C"])
        self.assertEqual(aus.count("\ntags:"), 1, aus)
        self.assertIn('tags: ["B", "C"]', aus)

    def test_tag_governance_raeumt_auch_blocklisten_doppel_ab(self):
        text = ('---\ntags:\n  - "A"\n  - "B"\ntags:\n  - "C"\n'
                'cover:\n  image: "x.jpg"\n---\n\nBody.\n')
        aus = tag_governance.schreibe_feld(text, "tags", ["A", "B"])
        self.assertEqual(aus.count("\ntags:"), 1, aus)
        self.assertNotIn('- "C"', aus, "die Blockliste des Duplikats muss mit")
        self.assertIn("image:", aus, "Nachbarfelder bleiben unberührt")
        self.assertTrue(aus.endswith("\n\nBody.\n"))

    def test_pinterest_pin_text_sync_laesst_kein_duplikat_zurueck(self):
        text = ('---\npin_title: "Alt"\npin_title: "Älter"\n---\n\nBody.\n')
        aus = pin_sync.fm_set(text, "pin_title", "Neu")
        self.assertEqual(aus.count("\npin_title:"), 1, aus)
        self.assertIn("pin_title: Neu", aus)

    def test_bestand_schreiber_konvergiert(self):
        """Klassen-Wächter: Für jeden echten Artikel hinterlässt ein Schreib-
        vorgang keinen doppelten Schlüssel und ist beim zweiten Lauf Fixpunkt."""
        geprueft = 0
        for pfad in ECHTE_CONTENT_FILES():
            text = Path(pfad).read_text(encoding="utf-8")
            geprueft += 1
            einmal = ko.fm_set(text, "fm_test_feld", "Wert")
            zweimal = ko.fm_set(einmal, "fm_test_feld", "Wert")
            self.assertEqual(einmal, zweimal, f"nicht idempotent: {pfad}")
            fm_block = einmal.split("---\n", 2)[1]
            self.assertEqual(fm_block.count("\nfm_test_feld:"), 1)
        self.assertGreater(geprueft, 0, "kein Artikel gefunden – Test blind?")


# ------------------------------- R15-Stempel (BOT-WATCHDOG #614, 07.10.2026)
class StempelIdempotenzTests(unittest.TestCase):
    """#614: Der Keyword-Stempel darf sich nicht stapeln.

    Die R15-PHrasen-Doppel-Ruine des Reserve-Vorrats („Dein Weg zu geringeren
    im Check: … ×3") war kein Inhaltsfehler, sondern ein Automatik-Defekt:
    Prüfung und Heilung benutzten ZWEI Fenster. `check_article` sah die ersten
    350 ZEICHEN, `heal_first_paragraph` stempelte den ersten FLIESSABSATZ.
    Im realen Entwurf beginnt dieser bei Zeichen 357 (Divider, Schnell-Tipp
    und Überschrift stehen davor) – der Stempel lag damit dauerhaft außerhalb
    des Prüffensters: Jeder Lauf meldete „Keyword fehlt" und stempelte erneut.
    Diese Tests halten den Realfall fest: Zielabsatz hinter dem Prüffenster,
    zweiter Lauf ist Fixpunkt, die Prüfung sieht den Stempel – und der ganze
    Bestand bleibt stempelfest.
    """

    # Reale Kopfstruktur eines Reserve-Entwurfs (gekürzt, Länge gewahrt):
    # Divider + Schnell-Tipp-Kasten + Einleitungs-Überschrift davor.
    KOPF = ("\n\n---\n\n"
            "💡 **Schnell-Tipp von FranksFinanzcheck:** Die besten Tarife findest "
            "du über unseren Partner-Vergleich: [**Jetzt Stromtarife vergleichen**]"
            "(/go/strom/)\n_(Dieser Artikel enthält Affiliate-Links (Werbung). "
            "Beim Abschluss über einen Link erhalten wir eine Provision – für dich "
            "entstehen keine Mehrkosten.)_\n\n"
            "## Einleitung – der Moment, der alles ändert\n\n")
    INTRO = ("Stell dir vor, du könntest jeden Monat 50 € oder mehr im Portemonnaie "
             "haben, ohne dafür mehr arbeiten zu müssen.\n")

    def test_fixture_bildet_den_realfall_ab(self):
        """Der Stempelabsatz MUSS hinter Zeichen 350 beginnen – sonst prüft
        dieser Test die Ursache nicht mehr (dann greift schon der alte Kopf-Wächter)."""
        self.assertGreater(len(self.KOPF), 350)

    def test_stempel_ist_nach_dem_ersten_lauf_fixpunkt(self):
        body = self.KOPF + self.INTRO
        einmal = ko.heal_first_paragraph(body, "Dein Weg zu geringeren")
        self.assertEqual(einmal.count("Dein Weg zu geringeren im Check"), 1)
        for lauf in range(2, 6):
            einmal = ko.heal_first_paragraph(einmal, "Dein Weg zu geringeren")
            self.assertEqual(einmal.count("Dein Weg zu geringeren im Check"), 1,
                             f"Lauf {lauf} hat erneut gestempelt (R15-Ruine)")

    def test_pruefung_sieht_den_stempel_im_zielabsatz(self):
        geheilt = ko.heal_first_paragraph(self.KOPF + self.INTRO,
                                          "Dein Weg zu geringeren")
        artikel = {"file": "x.md", "path": None, "slug": "dein-weg",
                   "title": "Dein Weg zu geringeren", "description": "",
                   "keywords": ["Dein Weg zu geringeren"], "body": geheilt}
        self.assertNotIn("Keyword nicht in: Erster Absatz",
                         ko.check_article(artikel)["issues"],
                         "der Stempel steht im ersten Fließabsatz – die Prüfung "
                         "muss ihn dort sehen, sonst stempelt der nächste Lauf erneut")

    def test_bestand_stempelt_sich_nicht_erneut(self):
        """Klassen-Wächter: Für JEDEN Artikel im Bestand ist die Heilung ein
        Fixpunkt. Vor dem Fix fiel dieser Test am realen Reserve-Entwurf."""
        geprueft = 0
        for a in ko.load_articles(include_drafts=True):
            if not a["keywords"]:
                continue
            geprueft += 1
            einmal = ko.heal_first_paragraph(a["body"], a["keywords"][0])
            zweimal = ko.heal_first_paragraph(einmal, a["keywords"][0])
            self.assertEqual(einmal, zweimal, f"nicht idempotent: {a['file']}")
        self.assertGreater(geprueft, 0, "kein Artikel gefunden – Test blind?")

if __name__ == "__main__":
    unittest.main()
