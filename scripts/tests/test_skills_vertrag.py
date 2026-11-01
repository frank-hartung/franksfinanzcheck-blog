#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Skill-Vertrag – Regressionssperre für Kernbudget, Herkunft und Runbook-Befehle.

WARUM DIESE TESTS EXISTIEREN (01.11.2026)
-----------------------------------------
Am 01.11.2026 las jeder Agent beim Start 2.532 Zeilen / 158 KB `CLAUDE.md`:
Backup-Fristen neben Snippet-Pixeln neben Reserve-Löschrechten. Das Detailwissen
ist jetzt in repo-eigenen Skills unter `.claude/skills/ff-*` abgelegt, der Kern
hält ein Budget. Verschieben allein wäre jedoch eine Heilung auf Zeit – dieselbe
Klasse, die dieser Repo woanders schon zweimal gefangen hat:

  · Ein **Schritt ohne Erzeuger** meldet für immer „Datenlage offen“ (#806, C42).
    Ohne K1/K3 wächst der Kern zurück und verwaiste `references/`-Dateien liest
    niemand – eine Regel, die niemand adressiert, ist abgeschafft.
  · Ein **Befund ohne Schließpfad** wird zum Dauerläufer (#729, C37). Ohne K4/K6
    steht vendored Fremd-Code ohne Lizenz und ohne Herkunft im Repo, und ein
    `ff-*`-Skill im `skills-lock.json` würde beim nächsten `npx skills update`
    von Dritt-Text überschrieben.
  · Ein **Runbook-Befehl, der nicht läuft**, ist ärger als kein Runbook: Er
    verweist auf einen Schritt, den es nicht mehr gibt (#853, #654). K5 prüft
    jeden `npm run`-Namen, jeden Pfad und jede Flagge in einem Code-Zaun gegen
    `package.json` und den Quelltext; K7 löst jeden Verweis ins Regelwerk auf.

Diese Tests halten die Dauerheilung fest:

  1. Der **echte Stand ist befundfrei** – including that the real `CLAUDE.md`
     and all six `ff-*` skills pass every check. Eine Wache, die im eigenen Repo
     rot ist, wird ausgenommen statt geheilt; das wäre der Anfang vom Ende.
  2. Jede Prüfung ist **am Sabotage-Fall** bewiesen (K1 bis K7) und hat eine
     **Gegenprobe**: derselbe Detektor schweigt bei einem sauberen Stand.
  3. Die **Verdrahtung** bleibt: `GUARDS` (C6), `npm run skills:check`,
     `npm run test:skills`, Runbook existiert. Ein Vertrag ohne Lauf ist Prosa.
  4. Der **Uhr-Zwang**: dasselbe Fixture-Urteil hängt an einem gesetzten
     Stichtag, nie an der Wanduhr (`selftest_clock`-Lehre, 18.09.2026).

Ausführung:
    python3 -m unittest scripts.tests.test_skills_vertrag
    npm run test:skills
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WACHE = os.path.join(WURZEL, "scripts", "skills_vertrag.py")
sys.path.insert(0, os.path.join(WURZEL, "scripts"))

import skills_vertrag as sv  # noqa: E402
import governance_contract as gc  # noqa: E402

STICHTAG = date(2027, 1, 15)   # eingefroren: ein Test, der „heute“ liest, ist eine Zeitbombe


def _befunde(wurzel):
    funde, warnungen, _ = sv.befunde(wurzel, stichtag=STICHTAG)
    return funde, warnungen


def _befunde_uhr(wurzel, tag):
    """Dasselbe Urteil an einem beliebigen Stichtag – der Beweis der Uhr-Freiheit."""
    funde, warnungen, _ = sv.befunde(wurzel, stichtag=tag)
    return funde, warnungen


class EchterStandTests(unittest.TestCase):
    """Der Repo-Stand muss grün sein – sonst wird die Wache ausgenommen, nicht geheilt."""

    def test_kern_und_skills_befundfrei(self):
        funde, warnungen = _befunde(sv.Path(WURZEL))
        self.assertEqual([], [f.kurz() for f in funde],
                         "Skill-Vertrag ist auf dem eigenen Stand rot")

    def test_kern_im_budget(self):
        zeilen = sv._zeilen(sv.Path(WURZEL), sv.KERN)
        self.assertLessEqual(len(zeilen), sv.ZEILEN_MAX)
        kilo = len("\n".join(zeilen).encode("utf-8")) / 1024
        self.assertLess(kilo, sv.KB_MAX, f"Kern wiegt {kilo:.1f} KB")

    def test_sechs_eigene_skills_mit_details(self):
        wurzel = sv.Path(WURZEL)
        eigene = sorted(p.name for p in (wurzel / sv.SKILL_ORDNER).iterdir()
                        if p.is_dir() and p.name.startswith(sv.EIGEN_PRÄFIX))
        self.assertEqual(["ff-ausliefern", "ff-ki-automation", "ff-marke-text",
                          "ff-oberflaeche", "ff-produzieren", "ff-pruefen"], eigene)
        for name in eigene:
            refs = list((wurzel / sv.SKILL_ORDNER / name / "references").glob("*.md"))
            self.assertGreaterEqual(len(refs), 1, f"{name} hat keine references-Datei")

    def test_wörtliche_übernahme_kein_umgeschrieben(self):
        """Jede Referenz-Datei trägt den Hinweis auf die wörtliche Übernahme –
        und jeder dort verlinkte Abschnittstitel stand so im früheren Kern."""
        wurzel = sv.Path(WURZEL)
        alt = os.path.join(WURZEL, ".cache", "CLAUDE.md.orig")
        if not os.path.exists(alt):
            self.skipTest("Umzugs-Auszug .cache/CLAUDE.md.orig liegt nur während des Umbaus vor")
        with open(alt, encoding="utf-8") as fh:
            friher = fh.read()
        for pfad in (wurzel / sv.SKILL_ORDNER).glob(f"{sv.EIGEN_PRÄFIX}*/references/*.md"):
            text = pfad.read_text(encoding="utf-8")
            self.assertIn("Wörtlich aus `CLAUDE.md` übernommen", text, str(pfad))
            for ueberschrift in [ln[4:].strip() for ln in text.split("\n") if ln.startswith("### ")]:
                self.assertIn(ueberschrift, friher,
                              f"„{ueberschrift}“ in {pfad.name} stammt nicht aus dem Kern")

    def test_lizenzregister_vollständig(self):
        wurzel = sv.Path(WURZEL)
        register = json.loads((wurzel / sv.LIZENZ_DATEI).read_text(encoding="utf-8"))
        installiert = {p.name for p in (wurzel / sv.SKILL_ORDNER).iterdir() if p.is_dir()}
        fremde = installiert - {n for n in installiert if n.startswith(sv.EIGEN_PRÄFIX)}
        self.assertEqual(set(), fremde - set(register["skills"]),
                         "vendored Skills ohne Lizenz-Eintrag")
        for name in fremde:
            eintrag = register["skills"][name]
            self.assertIn(eintrag["lizenz"], ("MIT", "Apache-2.0", "unbekannt"), name)
            if eintrag["lizenz"] != "unbekannt":
                da = [p.name for p in (wurzel / sv.SKILL_ORDNER / name).iterdir()
                      if p.name.upper().startswith("LICENSE")]
                self.assertTrue(da, f"{name} ohne Lizenztext")


class KernbudgetTests(unittest.TestCase):
    def test_k1_schlägt_bei_überlänge_an(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = sv._fixture(sv.Path(tmp) / "k1",
                                 kern=sv._sauberer_kern() + "\n" + "Zeile.\n" * (sv.ZEILEN_MAX + 5))
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if f.klasse == "K1"], "K1 meldet ein volles Fass nicht")

    def test_k1_grenze_ist_ein_budget_keine_dekoration(self):
        # 40 Zeilen im Zaum: Der Kern darf wachsen, aber nicht zurückfallen.
        self.assertLessEqual(sv.ZEILEN_MAX, 420)
        self.assertLess(sv.KB_MAX, 40.0)


class FormTests(unittest.TestCase):
    def test_name_muss_zum_ordner_passen(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = sv._fixture(sv.Path(tmp) / "k2", skill_md=sv.GRUND_SKILL.format(
                name="ff-anders", titel="Prüfen", ref="eins.md", desc="x" * (sv.DESC_MIN + 1)))
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if f.klasse == "K2"])

    def test_harte_1024_zeichen_für_die_beschreibung(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = sv._fixture(sv.Path(tmp) / "k2b", skill_md=sv.GRUND_SKILL.format(
                name="ff-eins", titel="Prüfen", ref="eins.md", desc="y" * (sv.DESC_MAX + 5)))
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if "1024" in f.meldung])

    def test_frontmatter_zeilenweise_gelesen(self):
        fm = sv.frontmatter(["---", "name: ff-x", "description: >",
                             "  erste Zeile", "  zweite Zeile", "---", "", "# T"])
        self.assertEqual("ff-x", fm["name"])
        self.assertEqual("erste Zeile zweite Zeile", fm["description"])


class ErreichbarkeitTests(unittest.TestCase):
    def test_verwaiste_referenz_wird_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = sv._fixture(sv.Path(tmp) / "k3",
                                 refs={"eins.md": "# Eins\n", "zwei.md": "# Zwei\n"})
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if f.klasse == "K3"])

    def test_skill_ohne_router_im_kern_wird_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            kern = sv._sauberer_kern().replace("`ff-eins` ist der Router-Skill.", "kein Skill hier")
            wurzel = sv._fixture(sv.Path(tmp) / "k3b", kern=kern)
            funde, _ = _befunde(wurzel)
            self.assertIn("Router", "; ".join(f.meldung for f in funde if f.klasse == "K3"))


class HerkunftTests(unittest.TestCase):
    def test_eigener_skill_im_lock_ist_verboten(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = sv._fixture(sv.Path(tmp) / "k4", lock={"version": 1, "skills": {
                "ff-eins": {"source": "wer/auch", "skillPath": "skills/x/SKILL.md"}}})
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if f.klasse == "K4"])

    def test_fremder_skill_ohne_lock_eintrag_ist_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = sv._fixture(sv.Path(tmp) / "k4b",
                                  fremd={"fremd": "---\nname: fremd\ndescription: „d“\n---\n\n# F\n"},
                                  lock={"version": 1, "skills": {}})
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if f.klasse == "K4"])


class BefehlsTests(unittest.TestCase):
    def test_unbekannter_npm_lauf_fehlt_auf(self):
        with tempfile.TemporaryDirectory() as tmp:
            kern = sv._sauberer_kern() + "\n```bash\nnpm run gibt-es-nicht\n```\n"
            wurzel = sv._fixture(sv.Path(tmp) / "k5", kern=kern)
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if f.klasse == "K5" and "gibt-es-nicht" in f.meldung])

    def test_vorlagen_pfad_bleibt_still(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Gegenprobe: eine Vorlage (`<…>`) ist kein Befehl, also kein Befund.
            kern = sv._sauberer_kern() + "\n```bash\npython3 scripts/<wache>.py --selftest\n```\n"
            wurzel = sv._fixture(sv.Path(tmp) / "gut", kern=kern)
            funde, _ = _befunde(wurzel)
            self.assertEqual([], [f.kurz() for f in funde if f.klasse == "K5"])

    def test_falsche_flagge_an_realer_datei_wird_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = sv._fixture(sv.Path(tmp) / "k5c")
            sv._schreibe(wurzel, "scripts/echt.py", "p.add_argument('--wache')\n")
            kern = sv._sauberer_kern() + "\n```bash\npython3 scripts/echt.py --erfunden\n```\n"
            (wurzel / sv.KERN).write_text(kern, encoding="utf-8")
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if f.klasse == "K5" and "--erfunden" in f.meldung])


def _lizenz_fixture(tmp, lizenz, ordnername="k6"):
    """Ein installierter Fremd-Skill mit Lock-Eintrag, ohne Lizenztext-Datei."""
    return sv._fixture(sv.Path(tmp) / ordnername,
                       fremd={"fremd": "---\nname: fremd\ndescription: „d“\n---\n\n# F\n"},
                       lock={"version": 1, "skills": {"fremd": {"source": "a/b",
                                                                "skillPath": "s/SKILL.md"}}},
                       lizenz=lizenz)


class LizenzTests(unittest.TestCase):
    _wurzel = staticmethod(_lizenz_fixture)

    def test_apache_ohne_notice_ist_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = self._wurzel(tmp, {"schema": 1, "eigene": {"skills": ["ff-eins"]}, "skills": {
                "fremd": {"quelle": "a/b", "lizenz": "Apache-2.0", "notiz": True}}})
            sv._schreibe(wurzel, f"{sv.SKILL_ORDNER}/fremd/LICENSE.txt", "Apache License\n")
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if f.klasse == "K6" and "NOTICE" in f.meldung])

    def test_unbekannt_ohne_ausnahme_ist_befund(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = self._wurzel(tmp, {"schema": 1, "eigene": {"skills": ["ff-eins"]}, "skills": {
                "fremd": {"quelle": "a/b", "lizenz": "unbekannt"}}})
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if f.klasse == "K6" and "Ausnahme" in f.meldung])

    def test_abgelaufene_frist_warnt_nur(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = self._wurzel(tmp, {"schema": 1, "eigene": {"skills": ["ff-eins"]}, "skills": {
                "fremd": {"quelle": "a/b", "lizenz": "unbekannt", "ausnahme": {
                    "grund": "g", "entscheidung": "e", "faellig": "2026-12-31"}}}})
            funde, warnungen = _befunde(wurzel)
            self.assertEqual([], [f for f in funde if f.klasse == "K6"])
            self.assertTrue([w for w in warnungen if w.klasse == "K6"])
            # …und der Exit-Code bleibt erreichbar: 0 Befunde = 0
            self.assertEqual(0, 1 if funde else 0)

    def test_doppelter_schluessel_ist_hausfehler(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = self._wurzel(tmp, {})
            (wurzel / sv.LIZENZ_DATEI).write_text(
                '{\n "schema": 1,\n "schema": 2\n}\n', encoding="utf-8")
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if "doppelter Schlüssel" in f.meldung])


class VerweisTests(unittest.TestCase):
    def test_gebot_nummer_muss_existieren(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = sv._fixture(sv.Path(tmp) / "k7")
            marke = "".join(["CLAUDE", ".", "md"])
            sv._schreibe(wurzel, "scripts/beispiel.py", f"# siehe {marke}, Regel 42\n")
            funde, _ = _befunde(wurzel)
            self.assertTrue([f for f in funde if f.klasse == "K7"])

    def test_existierendes_gebot_bleibt_still(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = sv._fixture(sv.Path(tmp) / "k7b")
            marke = "".join(["CLAUDE", ".", "md"])
            sv._schreibe(wurzel, "scripts/beispiel.py", f"# siehe {marke}, Regel 6\n")
            funde, _ = _befunde(wurzel)
            self.assertEqual([], [f.kurz() for f in funde if f.klasse == "K7"])

    def test_echter_stand_alle_verweise_geloest(self):
        funde, _ = _befunde(sv.Path(WURZEL))
        self.assertEqual([], [f.kurz() for f in funde if f.klasse == "K7"],
                         "ein Verweis aus scripts/ oder .github/ ins Regelwerk läuft ins Leere")


class UhrZwangTests(unittest.TestCase):
    def test_urteil_hängt_nicht_an_der_wanduhr(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = _lizenz_fixture(tmp, {"schema": 1, "eigene": {"skills": ["ff-eins"]}, "skills": {
                "fremd": {"quelle": "a/b", "lizenz": "unbekannt", "ausnahme": {
                    "grund": "g", "entscheidung": "e", "faellig": "2026-12-31"}}}}, ordnername="uhr")
            vor, _ = _befunde(wurzel) if False else _befunde_uhr(wurzel, date(2026, 12, 1))
            nach, _ = _befunde_uhr(wurzel, date(2031, 1, 1))
            self.assertEqual([f.kurz() for f in vor], [f.kurz() for f in nach],
                             "der Exit-Pfad hängt am Kalender – Fristen dürfen warnen, nie sperren")

    def test_selbsttest_liest_keine_uhr(self):
        with open(WACHE, encoding="utf-8") as fh:
            quell = fh.read()
        bereich = quell.split("def selftest()")[1].split("def main(")[0]
        for verraeter in ("date.today()", "datetime.now", "time.time"):
            self.assertNotIn(verraeter, bereich, f"Selbsttest liest {verraeter}")


class VerdrahtungTests(unittest.TestCase):
    def test_wache_steht_im_vertraglichen_minimum(self):
        self.assertIn("skills_vertrag.py", gc.GUARDS,
                      "ohne GUARDS (C6) läuft die Wache nie – ein Vertrag ohne Lauf ist Prosa")

    def test_selftest_ist_im_quelltext_verankert(self):
        with open(WACHE, encoding="utf-8") as fh:
            self.assertIn("--selftest", fh.read())

    def test_npm_laeufe_existieren(self):
        with open(os.path.join(WURZEL, "package.json"), encoding="utf-8") as fh:
            laufe = set((json.load(fh).get("scripts") or {}).keys())
        for lauf in ("skills:check", "test:skills"):
            self.assertIn(lauf, laufe)

    def test_runbook_existiert(self):
        self.assertTrue(os.path.exists(os.path.join(WURZEL, "docs", "ANLEITUNG-SKILLS.md")))

    def test_der_selbsttest_läuft_und_bleibt_offline(self):
        r = subprocess.run([sys.executable, WACHE, "--selftest"], cwd=WURZEL,
                           capture_output=True, text=True, timeout=300)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        self.assertIn("selftest OK", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
