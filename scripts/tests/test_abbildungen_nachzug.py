"""Vertrag des Abbildungs-Nachzugs (Dauerheilung 30.10.2026).

DIE GESCHICHTE
--------------
Am 30.10.2026 war der Job `regression` auf JEDEM Branch rot – der Befund
(FF5: 21 Beiträge) entstand aber gar nicht im Code, sondern in der
täglichen Textpflege: Die Bildzeile der Top-20-Abbildungen wird aus Titel,
Kernsätzen und Abschnittsnamen ABGELEITET. Titel-Gate, Casing,
Keyword-Optimizer, Lesbarkeit, Affiliate-Deep-Links und Duplikat-Wache
schreiben genau diese Felder – die Bildzeile zog niemand nach. Der Befund
landete damit bei fremder Arbeit (Blastradius-Klasse #676, andersherum).

WAS HIER FESTGEHALTEN WIRD
--------------------------
1. Es gibt EINE Messung: `befund_je_slug()` ist die Wahrheit für das Gate
   (`--check`) und für den Heiler (`--nachzug`). Kein zweites, leicht
   abweichendes Kriterium.
2. Der Heiler schreibt AUSSCHLIESSLICH abgeleitete Dateien der betroffenen
   Beiträge – fremde Beiträge bleiben Byte für Byte unangetastet.
3. Er ist idempotent, er nennt jede geänderte Datei (`ÄNDERUNG <pfad>`),
   damit der Aufrufer nicht `git add -A` braucht, und er blockiert nie
   einen Commit (das harte Gate bleibt `--check`).
4. Die Verdrahtung ist Vertrag: `git_sync.sh` zieht nach, der tägliche
   Gesundheitslauf zieht nach UND prüft gegen. Fällt eine der beiden
   Zeilen weg, wird dieser Test rot – Rückfall ohne Alarm gibt es nicht.

Die Fixtures laufen gegen einen synthetischen Bestand (Temp-Verzeichnis),
nicht gegen die echten 20 Beiträge: Ein Test am Tagesgeschäft wäre
wetterabhängig (dieselbe Naht wie bei `duplikat_guard.check_article`).
"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import scripts.abbildungen_ableiten as abb

BLOG_DIR = Path(__file__).resolve().parents[2]

ARTIKEL = """---
title: "{titel}"
kurzantwort: "{kurzantwort}"
---

Einleitungssatz, der den Beitrag eröffnet.

## {h2a}

Inhalt A.

## {h2b}

Inhalt B.

## Fazit

Wird von der Gliederung bewusst übersprungen.
"""


def _artikel(titel, kurzantwort, h2a="Kosten sehen", h2b="Kontingente prüfen"):
    return ARTIKEL.format(titel=titel, kurzantwort=kurzantwort, h2a=h2a, h2b=h2b)


class Fixture:
    """Synthetischer Bestand: Wurzel, Liste, zwei Beiträge."""

    def __init__(self, tmp: Path, slugs=("2026-01-01-erster-beitrag",
                                        "2026-01-02-zweiter-beitrag")):
        self.root = tmp
        self.slugs = list(slugs)
        (tmp / "data").mkdir(parents=True, exist_ok=True)
        (tmp / "content" / "posts").mkdir(parents=True, exist_ok=True)
        zeilen = ["beitraege:"]
        for slug in self.slugs:
            zeilen.append(f'  - slug: "{slug}"')
        (tmp / "data" / "top20_abbildungen.yaml").write_text(
            "\n".join(zeilen) + "\n", encoding="utf-8")
        self.pfade = {}
        for i, slug in enumerate(self.slugs):
            ordner = tmp / "content" / "posts" / slug
            ordner.mkdir(parents=True, exist_ok=True)
            pfad = ordner / "index.md"
            pfad.write_text(
                _artikel(f"Beitrag Nummer {i + 1}",
                         f"Kurzantwort fuer Beitrag Nummer {i + 1}.",
                         h2a=f"Kosten sehen {i + 1}",
                         h2b=f"Kontingente pruefen {i + 1}"),
                encoding="utf-8")
            self.pfade[slug] = pfad

    def __enter__(self):
        self._patches = [
            mock.patch.object(abb, "BLOG_DIR", str(self.root)),
            mock.patch.object(abb, "LIST_PATH",
                              str(self.root / "data" / "top20_abbildungen.yaml")),
        ]
        for p in self._patches:
            p.start()
        for slug in self.slugs:          # Grundstand: alles artikelgenau
            abb.render(str(self.pfade[slug]), write=True)
        return self

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.stop()
        return False

    def baue(self):
        out = io.StringIO()
        with redirect_stdout(out):
            gezogen = abb.nachzug(abb.load_slugs())
        return gezogen, out.getvalue()

    def bytes(self):
        return {p.name: p.read_bytes() for s in self.slugs
                for p in (self.pfade[s],
                          self.pfade[s].parent / abb.MERK,
                          self.pfade[s].parent / abb.ABLAUF)}


class NachzugTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="abbildungen-"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _titel_aendern(self, fx, slug, neuer_titel):
        pfad = fx.pfade[slug]
        text = pfad.read_text(encoding="utf-8")
        alt = [z for z in text.splitlines() if z.startswith("title: ")][0]
        pfad.write_text(text.replace(alt, f'title: "{neuer_titel}"'),
                        encoding="utf-8")

    def test_grundstand_ist_befundfrei(self):
        with Fixture(self.tmp) as fx:
            self.assertEqual(abb.befund_je_slug(abb.load_slugs()), {})
            self.assertEqual(abb.check(abb.load_slugs()), [])

    def test_titelwechsel_macht_die_bildzeile_veraltet(self):
        # Der Kern der Dauerheilung: eine Textpflege (hier: Titel-Gate)
        # verändert den abgeleiteten Text, ohne die Abbildung anzufassen.
        with Fixture(self.tmp) as fx:
            self._titel_aendern(fx, "2026-01-01-erster-beitrag",
                                "Beitrag Nummer 1 – neu zugeschnitten")
            befund = abb.befund_je_slug(abb.load_slugs())
            self.assertEqual(list(befund), ["2026-01-01-erster-beitrag"], befund)
            self.assertTrue(any("Unterschrift" in p for p in befund[
                "2026-01-01-erster-beitrag"]), befund)

    def test_nachzug_heilt_nur_den_betroffenen_beitrag(self):
        with Fixture(self.tmp) as fx:
            vorher = fx.bytes()
            self._titel_aendern(fx, "2026-01-01-erster-beitrag",
                                "Beitrag Nummer 1 – neu zugeschnitten")
            gezogen, ausgabe = fx.baue()
            self.assertEqual(gezogen, ["2026-01-01-erster-beitrag"])
            self.assertEqual(abb.check(abb.load_slugs()), [],
                             "nach dem Nachzug muss das Gate grün sein")
            # Der fremde Beitrag ist Byte für Byte unangetastet.
            zweiter = "2026-01-02-zweiter-beitrag"
            for name in (fx.pfade[zweiter].name, abb.MERK, abb.ABLAUF):
                self.assertEqual(
                    (fx.pfade[zweiter].parent / name).read_bytes(),
                    vorher[name],
                    f"{name} des unbeteiligten Beitrags wurde angefasst")
            self.assertIn("ÄNDERUNG", ausgabe)

    def test_nachzug_meldet_genau_die_geaenderten_pfade(self):
        # git_sync.sh stagt nur diese Zeilen – kein `git add -A`.
        with Fixture(self.tmp) as fx:
            self._titel_aendern(fx, "2026-01-01-erster-beitrag",
                                "Beitrag Nummer 1 – neu zugeschnitten")
            _gezogen, ausgabe = fx.baue()
            gemeldet = [z.split(" ", 1)[1] for z in ausgabe.splitlines()
                        if z.startswith("ÄNDERUNG ")]
            self.assertEqual(sorted(gemeldet), sorted([
                "content/posts/2026-01-01-erster-beitrag/index.md",
                f"content/posts/2026-01-01-erster-beitrag/{abb.MERK}",
                f"content/posts/2026-01-01-erster-beitrag/{abb.ABLAUF}",
            ]))
            for pfad in gemeldet:
                self.assertTrue((fx.root / pfad).is_file(), pfad)
            self.assertNotIn("2026-01-02-zweiter-beitrag", ausgabe)

    def test_nachzug_ist_idempotent(self):
        with Fixture(self.tmp) as fx:
            self._titel_aendern(fx, "2026-01-01-erster-beitrag",
                                "Beitrag Nummer 1 – neu zugeschnitten")
            self.assertEqual(len(fx.baue()[0]), 1)
            vorher = fx.bytes()
            gezogen, _ausgabe = fx.baue()
            self.assertEqual(gezogen, [], "zweiter Lauf darf nichts mehr ändern")
            self.assertEqual(fx.bytes(), vorher)

    def test_kurzantwort_aendert_die_merkkarte(self):
        with Fixture(self.tmp) as fx:
            pfad = fx.pfade["2026-01-02-zweiter-beitrag"]
            text = pfad.read_text(encoding="utf-8")
            neu = text.replace("Kurzantwort fuer Beitrag Nummer 2.",
                               "Neue Kernaussage mit klarerem Zuschnitt.")
            pfad.write_text(neu, encoding="utf-8")
            self.assertEqual(fx.baue()[0], ["2026-01-02-zweiter-beitrag"])
            svg = (pfad.parent / abb.MERK).read_text(encoding="utf-8")
            self.assertIn("Neue Kernaussage mit klarerem Zuschnitt", svg)

    def test_veraltete_grafik_ist_ein_befund_auch_ohne_neue_unterschrift(self):
        # Die Unterschrift nennt bewusst nur den Titel. Ändert sich die
        # `kurzantwort`, standen bis 30.10.2026 die ALTEN Zahlen im Bild –
        # und niemand hat es gemerkt, weil `--check` nur Text prüfte. Ein
        # veralteter Betrag in einer Grafik sieht aus wie ein Beleg; deshalb
        # wird die Grafik jetzt gegen die Ableitung geprüft.
        with Fixture(self.tmp) as fx:
            svg = fx.pfade["2026-01-01-erster-beitrag"].parent / abb.MERK
            svg.write_text('<svg aria-label="alt"><text>alte Zahlen</text></svg>',
                           encoding="utf-8")
            befund = abb.befund_je_slug(abb.load_slugs())
            self.assertIn("2026-01-01-erster-beitrag", befund)
            self.assertTrue(
                any("aktuellen Text" in p for p in befund["2026-01-01-erster-beitrag"]),
                befund)
            self.assertEqual(fx.baue()[0], ["2026-01-01-erster-beitrag"])
            self.assertEqual(abb.check(abb.load_slugs()), [])

    def test_fehlende_svg_dateien_werden_wiederhergestellt(self):
        with Fixture(self.tmp) as fx:
            pfad = fx.pfade["2026-01-01-erster-beitrag"]
            (pfad.parent / abb.MERK).unlink()
            self.assertEqual(fx.baue()[0], ["2026-01-01-erster-beitrag"])
            self.assertTrue((pfad.parent / abb.MERK).is_file())
            self.assertEqual(abb.check(abb.load_slugs()), [])

    def test_nicht_nachziehbarer_beitrag_blockiert_den_rest_nicht(self):
        # Ein Beitrag mit nur einem Abschnitt kann keine Gliederung tragen.
        # Der Heiler meldet das, zieht den anderen nach und bleibt Exit 0 –
        # blockieren darf nur das Gate (`--check`).
        with Fixture(self.tmp) as fx:
            kaputt = fx.pfade["2026-01-01-erster-beitrag"]
            kaputt.write_text(
                '---\ntitle: "Nur ein Abschnitt"\n'
                'kurzantwort: "Eine Kurzantwort."\n---\n\n'
                "## Einziger Abschnitt\n\nText.\n", encoding="utf-8")
            (kaputt.parent / abb.MERK).unlink()
            (kaputt.parent / abb.ABLAUF).unlink()
            gezogen, ausgabe = fx.baue()
            self.assertIn("nicht nachziehbar", ausgabe)
            self.assertNotIn("2026-01-01-erster-beitrag", gezogen)


class HakenTests(unittest.TestCase):
    """Der git_sync-Haken selbst – gegen ein echtes Mini-Repository.

    Die Verdrahtungstests oben prüfen, dass die Zeilen existieren. Hier wird
    die Funktion aus `git_sync.sh` ausgeführt: Stagt sie genau die
    nachgezogenen Dateien – und schweigt sie, wenn der Commit keinen Inhalt
    anfasst? Ein Haken, der fremde Arbeit mitstagt, wäre schlimmer als keiner.
    """

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="git-sync-haken-"))
        self.repo = self.tmp / "repo"
        (self.repo / "scripts").mkdir(parents=True)
        shutil.copy(BLOG_DIR / "scripts" / "abbildungen_ableiten.py",
                    self.repo / "scripts" / "abbildungen_ableiten.py")
        (self.repo / "data").mkdir()
        (self.repo / "data" / "top20_abbildungen.yaml").write_text(
            'beitraege:\n  - slug: "2026-01-01-erster-beitrag"\n', encoding="utf-8")
        ordner = self.repo / "content" / "posts" / "2026-01-01-erster-beitrag"
        ordner.mkdir(parents=True)
        self.post = ordner / "index.md"
        self.post.write_text(
            _artikel("Ein Beitrag", "Eine Kurzantwort."), encoding="utf-8")
        self._git("init", "-q")
        self._git("config", "user.name", "Test")
        self._git("config", "user.email", "test@example.invalid")
        self._python("scripts/abbildungen_ableiten.py")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "Grundstand")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _git(self, *args):
        out = subprocess.run(["git", *args], cwd=self.repo, text=True,
                             capture_output=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def _python(self, *args):
        out = subprocess.run([sys.executable, *args], cwd=self.repo, text=True,
                             capture_output=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        return out.stdout

    def _haken(self):
        """Führt die FUNKTION aus git_sync.sh aus (kein Nachbau)."""
        text = (BLOG_DIR / "scripts" / "git_sync.sh").read_text(encoding="utf-8")
        start = text.index("abbildungen_nachziehen() {")
        ende = text.index("\n}\n", start) + len("\n}\n")
        skript = ("set -Eeuo pipefail\n" + text[start:ende]
                  + "\nabbildungen_nachziehen staged\n")
        return subprocess.run(["bash", "-c", skript], cwd=self.repo, text=True,
                              capture_output=True)

    def test_haken_stagt_die_nachgezogenen_dateien(self):
        self.post.write_text(
            self.post.read_text(encoding="utf-8").replace(
                'title: "Ein Beitrag"', 'title: "Ein Beitrag – neuer Titel"'),
            encoding="utf-8")
        self._git("add", "content/posts/2026-01-01-erster-beitrag/index.md")
        out = self._haken()
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertIn("nachgezogen", out.stdout)
        gestagt = self._git("diff", "--cached", "--name-only").split()
        self.assertEqual(sorted(gestagt), sorted([
            "content/posts/2026-01-01-erster-beitrag/index.md",
            "content/posts/2026-01-01-erster-beitrag/abbildung-merkkarte.svg",
            "content/posts/2026-01-01-erster-beitrag/abbildung-ablauf.svg",
        ]), gestagt)

    def test_haken_schweigt_ohne_inhalt_im_commit(self):
        (self.repo / "data" / "notiz.json").write_text("{}\n", encoding="utf-8")
        self.post.write_text(
            self.post.read_text(encoding="utf-8").replace(
                'title: "Ein Beitrag"', 'title: "Ein Beitrag – neuer Titel"'),
            encoding="utf-8")
        self._git("add", "data/notiz.json")
        out = self._haken()
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertNotIn("nachgezogen", out.stdout)
        self.assertEqual(
            self._git("diff", "--cached", "--name-only").split(),
            ["data/notiz.json"],
            "Der Haken darf fremde Arbeit nicht stagen")


class VerdrahtungTests(unittest.TestCase):
    """Ein Heiler, der nirgends läuft, heilt nichts.

    Dieselbe Bauart wie `test_measurement_chain` für hunspell: Wer die
    Zeile entfernt, macht diesen Test rot – die Verdrahtung ist Vertrag.
    """

    @classmethod
    def setUpClass(cls):
        cls.git_sync = (BLOG_DIR / "scripts" / "git_sync.sh").read_text(
            encoding="utf-8")
        cls.tageslauf = (BLOG_DIR / ".github" / "workflows" /
                         "blog-health-daily.yml").read_text(encoding="utf-8")

    def test_git_sync_zieht_nach(self):
        self.assertIn("abbildungen_nachziehen()", self.git_sync,
                      "Die Funktion fehlt in git_sync.sh")
        self.assertIn("abbildungen_ableiten.py --nachzug", self.git_sync)
        self.assertIn("abbildungen_nachziehen staged", self.git_sync,
                      "Vollbedienung zieht nicht nach")
        self.assertIn("abbildungen_nachziehen push", self.git_sync,
                      "Fremd-Workflows (--push-only) ziehen nicht nach")

    def test_git_sync_stagt_nur_gemeldete_pfade(self):
        self.assertIn("s/^ÄNDERUNG //p", self.git_sync,
                      "Der Haken muss die gemeldeten Pfade stagen, "
                      "nicht `git add -A` benutzen")
        self.assertNotIn("git add -A -- content", self.git_sync)

    def test_tageslauf_zieht_nach_und_prueft_gegen(self):
        for zeile in ("abbildungen_ableiten.py --selftest",
                      "abbildungen_ableiten.py --nachzug",
                      "abbildungen_ableiten.py --check"):
            self.assertIn(zeile, self.tageslauf, f"{zeile} fehlt im Tageslauf")
        # Reihenfolge ist Vertrag: erst sehen, dann heilen, dann gegenprüfen.
        selftest = self.tageslauf.index("abbildungen_ableiten.py --selftest")
        nachzug = self.tageslauf.index("abbildungen_ableiten.py --nachzug")
        pruefung = self.tageslauf.index("abbildungen_ableiten.py --check")
        self.assertLess(selftest, nachzug)
        self.assertLess(nachzug, pruefung)

    def test_der_live_bestand_ist_befundfrei(self):
        # Kein Schreiben: nur die Messung. Dieser Test ist der Grund, warum
        # ein Nachziehfall gar nicht erst auf main landen soll.
        with mock.patch.object(abb, "BLOG_DIR", str(BLOG_DIR)), \
             mock.patch.object(abb, "LIST_PATH",
                               str(BLOG_DIR / "data" / "top20_abbildungen.yaml")):
            self.assertEqual(abb.befund_je_slug(abb.load_slugs()), {})


if __name__ == "__main__":
    unittest.main()
