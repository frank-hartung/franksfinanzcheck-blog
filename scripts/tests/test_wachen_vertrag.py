#!/usr/bin/env python3
"""Wachen-Vertrag – Regressionssperre gegen halbe Wachen (WF-6F7F / #783).

WARUM DIESE TESTS EXISTIEREN (16.10.2026)
-----------------------------------------
Am 15.10.2026 wurde PR #776 zusammengeführt. Seine Commit-Nachricht nennt den
Vorgang: „Rebased onto origin/main; Faustregel-Konflikte zugunsten der
themenspezifischen Varianten aufgelöst.“ In `scripts/redaktions_standard.py`
blieben Kopf und 14 eingefrorene Selbsttest-Fälle aus der neueren Fassung
(#766, Faustregel-POOL + Bestandsmessung), der RS3-Rumpf kam aus der älteren.
Die Datei war syntaktisch gültig und in sich widersprüchlich: `main()` rief
fünf Funktionen, die es nicht mehr gab, der Selbsttest las drei Konstanten,
die es nicht mehr gab. Folgen: `--selftest` Exit 2 (Lauf 38893209063, Meldung
#783), Qualitäts-Gate rot ab 15.10. 18:19, Regression rot, und der Heilpfad
der Redaktions-Wache war für jeden echten Lauf ein `NameError` – eine tote
Wache, die aussah, als wäre sie da.

Diese Tests halten die Dauerheilung fest:

  1. Der Vorfall selbst ist als Fall eingefroren: Die Miniatur wird erkannt,
     die vollständige Fassung bleibt still (keine Fehlalarme).
  2. Die Werkzeuge der Wache (Konfliktmarker mit Paar-Regel, Namens-Vertrag)
     sind gegen die typischen Rückfälle gesichert – insbesondere gegen die
     beiden echten Fälle dieses Repos: Docstring-Unterstreichung `=======`
     ist KEIN Konfliktmarker, und ein Name, der irgendwo in der Datei
     gebunden wird (Parameter, Zuweisung, Import), ist kein halber Aufruf.
  3. Der Vorfall #766 bleibt geschlossen: Die Redaktions-Wache ist vollständig
     (FAUSTREGEL-POOL-API vorhanden) und ihr Selbsttest läuft.
  4. Die Verdrahtung bleibt: GUARDS, Governance-Vertrag C39, Qualitäts-Gate.
     Ein Vertrag ohne Lauf ist Prosa – das war die Lehre des 18.09.2026
     (handgeschriebene Wachen-Liste) und sie gilt hier genauso.

Lauf: python3 -m unittest scripts.tests.test_wachen_vertrag
"""
from __future__ import annotations

import ast
import os
import importlib.util
import subprocess
import sys
import tempfile
import unittest

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WACHE = os.path.join(WURZEL, "scripts", "wachen_vertrag.py")
REDAKTION = os.path.join(WURZEL, "scripts", "redaktions_standard.py")
GATE = os.path.join(WURZEL, ".github", "workflows", "link-check.yml")

sys.path.insert(0, os.path.join(WURZEL, "scripts"))
import wachen_vertrag as wv  # noqa: E402
import governance_contract as gc  # noqa: E402

HALBE_WACHE = '''#!/usr/bin/env python3
"""Miniatur des Vorfalls #783: Selbsttest neu, Rumpf alt."""
SELFTEST = [("Pool-ist-gross", lambda: len(FAUSTREGEL_POOL) >= 12, True)]


def main():
    kontext = faustregel_kontext(_bestand_texte())
    if faustregel_vorrat(kontext) < FAUSTREGEL_VORRAT_WARNUNG:
        return False
    return True


main()
'''

VOLLSTAENDIGE_WACHE = '''#!/usr/bin/env python3
"""Dieselbe Wache, eine Fassung."""
FAUSTREGEL_POOL = (("strom", "Miss den Verbrauch."),)
FAUSTREGEL_VORRAT_WARNUNG = 2


def _bestand_texte():
    return {}


def faustregel_vorrat(kontext):
    return len(FAUSTREGEL_POOL)


def faustregel_kontext(texte):
    return {"belegung": set(), "index": {}, "vermeiden": set()}


def main():
    kontext = faustregel_kontext(_bestand_texte())
    return faustregel_vorrat(kontext) < FAUSTREGEL_VORRAT_WARNUNG


main()
'''


def _lies(pfad: str) -> str:
    with open(pfad, encoding="utf-8") as fh:
        return fh.read()


def _mini_baum(dateien: dict) -> str:
    """Wegwerf-Repo mit scripts/ (+ tests/, wenn verlangt). Nur für Tests."""
    wurzel = tempfile.mkdtemp(prefix="wachen-vertrag-test-")
    os.makedirs(os.path.join(wurzel, "scripts"), exist_ok=True)
    for name, inhalt in dateien.items():
        pfad = os.path.join(wurzel, name)
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(inhalt)
    return wurzel


class VorfallTest(unittest.TestCase):
    """Der Vorgang #783 als eingefrorener Fall – nicht als Erzählung."""

    def test_halbe_wache_wird_erkannt(self):
        wurzel = _mini_baum({"scripts/halbe.py": HALBE_WACHE})
        funde = wv.befunde(wurzel, ausnahmen={})
        klassen = {f.klasse for f in funde}
        self.assertIn("W2-HALBER-AUFRUF", klassen)
        self.assertIn("W3-HALBE-KONSTANTE", klassen)

    def test_erkannt_wird_der_gerufene_name(self):
        wurzel = _mini_baum({"scripts/halbe.py": HALBE_WACHE})
        meldungen = " ".join(f.meldung for f in wv.befunde(wurzel, ausnahmen={}))
        for name in ("faustregel_kontext", "_bestand_texte", "faustregel_vorrat"):
            self.assertIn(name, meldungen,
                          f"{name}() muss als halber Aufruf gemeldet werden")
        self.assertIn("FAUSTREGEL_POOL", meldungen)
        self.assertIn("FAUSTREGEL_VORRAT_WARNUNG", meldungen)

    def test_vollstaendige_wache_bleibt_still(self):
        wurzel = _mini_baum({"scripts/ganze.py": VOLLSTAENDIGE_WACHE})
        self.assertEqual([], wv.befunde(wurzel, ausnahmen={}))

    def test_pruefling_wird_nicht_ausgefuehrt(self):
        """Die Wache liest Quelltext – sie startet ihn nie (kein Netz, kein Schreiben)."""
        wurzel = _mini_baum({
            "scripts/scharf.py": "#!/usr/bin/env python3\n"
                                 "open('ICH_WAR_HIER', 'w').write('x')\n"
                                 "raise SystemExit(9)\n"})
        # Nur für den Eigentümer ausführbar (0o500): Die Wache muss auch an
        # einer ausführbaren Datei scheitern-frei bleiben – ohne dass die
        # Vorlage Rechte für Gruppe oder Andere bekommt (py/overly-permissive-file).
        os.chmod(os.path.join(wurzel, "scripts", "scharf.py"), 0o500)
        self.assertEqual([], wv.befunde(wurzel, ausnahmen={}))
        self.assertFalse(os.path.exists(os.path.join(wurzel, "ICH_WAR_HIER")))


class WerkzeugTest(unittest.TestCase):
    """Die beiden Regeln, an denen eine naive Fassung scheitern würde."""

    def test_docstring_unterstreichung_ist_kein_konfliktmarker(self):
        self.assertEqual([], wv.konfliktmarker("NUTZUNG\n=======\n"))

    def test_echtes_marker_paar_ist_ein_konflikt(self):
        text = f"a = 1\n{'<' * 7} HEAD\nb = 2\n{'=' * 7}\nc = 3\n{'>' * 7} main\n"
        self.assertEqual([2, 4, 6], wv.konfliktmarker(text))

    def test_gebundene_namen_bleiben_still(self):
        quelle = ("import os\n\n\n"
                  "class Ding:\n    pass\n\n\n"
                  "def hilfe(parameter):\n"
                  "    for zaehler in range(3):\n"
                  "        with open('x') as griff:\n"
                  "            pass\n"
                  "    try:\n"
                  "        pass\n"
                  "    except ValueError as fehler:\n"
                  "        pass\n"
                  "    return os.sep, parameter, zaehler, griff, fehler\n\n\n"
                  "def main():\n"
                  "    if (zahl := hilfe(1)):\n"
                  "        return zahl, Ding\n\n\n"
                  "main()\n")
        funde = wv.namensbefunde("scripts/x.py", quelle)
        self.assertEqual([], funde, [f.kurz() for f in funde])

    def test_aufruf_eines_parameters_ist_kein_befund(self):
        quelle = "def ruf(callback):\n    return callback()\n"
        self.assertEqual([], wv.namensbefunde("scripts/x.py", quelle))


class AusnahmeTest(unittest.TestCase):
    """Ausnahmen sind begründet, datiert – und sie altern sichtbar."""

    def test_ausnahme_verdeckt_den_befund(self):
        wurzel = _mini_baum({"scripts/halbe.py": HALBE_WACHE})
        ausnahmen = {"scripts/halbe.py": {"grund": "Fremd-Einspielung",
                                         "seit": "2026-10-16"}}
        self.assertEqual([], wv.befunde(wurzel, ausnahmen=ausnahmen))

    def test_ausnahme_deckt_keinen_konfliktmarker(self):
        text = f"{'<' * 7} HEAD\na = 1\n{'=' * 7}\nb = 2\n{'>' * 7} main\n"
        wurzel = _mini_baum({"scripts/konflikt.py": text})
        ausnahmen = {"scripts/konflikt.py": {"grund": "egal", "seit": "2026-10-16"}}
        funde = wv.befunde(wurzel, ausnahmen=ausnahmen)
        self.assertIn("W1-KONFLIKT-MARKER", {f.klasse for f in funde})

    def test_abgelaufene_ausnahme_wird_gemeldet(self):
        wurzel = _mini_baum({"scripts/ganze.py": VOLLSTAENDIGE_WACHE})
        ausnahmen = {"scripts/ganze.py": {"grund": "war mal nötig",
                                         "seit": "2026-01-01"}}
        funde = wv.befunde(wurzel, ausnahmen=ausnahmen)
        self.assertTrue(any(f.klasse == "W4-AUSNAHME" for f in funde),
                        [f.kurz() for f in funde])

    def test_ausnahme_ohne_grund_ist_ein_befund(self):
        wurzel = _mini_baum({"scripts/halbe.py": HALBE_WACHE})
        funde = wv.ausnahmebefunde({"scripts/halbe.py": {"seit": "2026-10-16"}},
                                   set(), wv.Path(wurzel))
        self.assertTrue(any("ohne Begründung" in f.meldung for f in funde))

    def test_ausnahmedatei_fehlt_ist_kein_fehler(self):
        """Ohne Ausnahmedatei gibt es keine Ausnahmen – kein stilles Grün."""
        ausnahmen, fehler = wv.lade_ausnahmen(wv.Path("/gibt/es/nicht.yaml"))
        self.assertEqual(({}, ""), (ausnahmen, fehler))


class BestandTest(unittest.TestCase):
    """Der laufende Bestand – die Wache ist grün, und sie bleibt es."""

    def test_bestand_hat_keine_halben_wachen(self):
        funde = wv.befunde(wv.BLOG_DIR)
        self.assertEqual([], [f.kurz() for f in funde])

    def test_selbsttest_der_wache_laeuft(self):
        ergebnis = subprocess.run([sys.executable, WACHE, "--selftest"],
                                  cwd=WURZEL, capture_output=True, text=True,
                                  timeout=300)
        self.assertEqual(0, ergebnis.returncode, ergebnis.stdout + ergebnis.stderr)


class Vorfall766BleibtGeheilt(unittest.TestCase):
    """Die #766-Dauerheilung darf nicht erneut still verschwinden."""

    def test_redaktions_wache_hat_die_pool_api(self):
        quelle = _lies(REDAKTION)
        for name in ("FAUSTREGEL_POOL", "FAUSTREGEL_LEGACY", "FAUSTREGEL_MARKER",
                     "faustregel_saetze", "faustregel_kontext", "faustregel_vorrat",
                     "_bestand_texte", "_kontext_aktualisieren", "_messung",
                     "waehle_faustregel", "ersetze_generische_faustregel"):
            self.assertIn(name, quelle, f"{name} fehlt – halbe Fassung (#783)")

    def test_selbsttest_unterscheidet_grundlage_von_defekt(self):
        """Die Diagnose darf kein Schlupfloch werden.

        Ohne PyYAML meldet der Selbsttest „Prüfgrundlage fehlt" (01.11.2026 –
        sonst hält ein Beitragender eine intakte Wache für kaputt und eine
        unvollständige Umgebung für einen Befund). Aber ein echter Logikfehler muss trotz
        installierter Grundlage weiter hart als „Wache defekt" beantwortet
        werden: Wer die Diagnose weichredet, hätte eine Unterdrückung im
        Selbsttest gebaut – genau das, was Regel 6 verbietet.
        """
        import contextlib
        import io
        import redaktions_standard as rs

        original = (rs.SELFTEST, rs._messgrundlage_fehlt)
        try:
            rs.SELFTEST = [("Sabotage-falsche-erwartung", lambda: False, True)]
            for grundlage, erwartet in ((False, "die Wache selbst ist defekt"),
                                        (True, "Prüfgrundlage fehlt")):
                rs._messgrundlage_fehlt = lambda fixed=grundlage: fixed
                ausgabe = io.StringIO()
                with contextlib.redirect_stdout(ausgabe):
                    ruckgabe = rs.selftest()
                text = ausgabe.getvalue()
                self.assertEqual(2, ruckgabe,
                                 f"Grundlage={grundlage}: Exit {ruckgabe}, erwartet 2 "
                                 "(keine Messung ist kein Grün)")
                self.assertIn(erwartet, text,
                              f"Grundlage={grundlage}: Urteil trifft nicht zu – " + text[:180])
                if not grundlage:
                    self.assertNotIn("Prüfgrundlage fehlt", text,
                                     "echter Defekt weggeredet")
        finally:
            rs.SELFTEST, rs._messgrundlage_fehlt = original

    def test_selbsttest_der_redaktions_wache_laeuft(self):
        # Die Wache parst im Selbsttest Frontmatter über den Publikations-Vertrag,
        # und der braucht PyYAML. Ohne Grundlage meldet er fail-closed Exit 2 –
        # das ist richtig so, aber es ist keine kaputte Wache, sondern eine
        # unvollständige Umgebung. Der Skip nennt den Grund und das Kommando,
        # damit die Unterscheidung nicht wieder denselben Umweg kostet
        # (01.11.2026: ein Agent hielt die Wache für logisch defekt und
        #  schrieb das in einen Bericht, statt in die Umgebung zu schauen).
        if importlib.util.find_spec("yaml") is None:
            self.skipTest("PyYAML fehlt im Interpreter des Tests – Selbsttest der "
                          "Redaktions-Wache braucht ihn (fail-closed ohne). Beheben: "
                          "python3 -m pip install -r requirements-ci.txt")
        ergebnis = subprocess.run([sys.executable, REDAKTION, "--selftest"],
                                  cwd=WURZEL, capture_output=True, text=True,
                                  timeout=600)
        self.assertEqual(0, ergebnis.returncode, ergebnis.stdout + ergebnis.stderr)


class VerdrahtungTest(unittest.TestCase):
    """Ein Vertrag, den niemand ausführt, ist Prosa (Lehre 18.09.2026)."""

    def test_wache_steht_im_vertraglichen_minimum(self):
        self.assertIn("wachen_vertrag.py", gc.GUARDS)

    def test_redaktions_wache_steht_jetzt_im_minimum(self):
        self.assertIn("redaktions_standard.py", gc.GUARDS)

    def test_c39_ist_im_vertrag_und_beschrieben(self):
        quelle = _lies(os.path.join(WURZEL, "scripts", "governance_contract.py"))
        self.assertIn("c39_wache_ist_ganz_oder_gar_nicht(", quelle)
        self.assertIn("checks += c39_wache_ist_ganz_oder_gar_nicht(", quelle)
        texte = {name: _lies(os.path.join(WURZEL, "scripts", name))
                 for name in gc.GUARDS
                 if os.path.exists(os.path.join(WURZEL, "scripts", name))}
        self.assertEqual([], gc.c39_wache_ist_ganz_oder_gar_nicht(
            texte, {GATE: _lies(GATE)}, root=WURZEL))

    def test_qualitaets_gate_ruft_den_vertrag(self):
        self.assertIn("governance_contract.py --quick", _lies(GATE))

    def test_c39_meldet_die_halbe_wache_im_mini_baum(self):
        wurzel = _mini_baum({"scripts/halbe.py": HALBE_WACHE})
        texte = {"wachen_vertrag.py": _lies(WACHE)}
        funde = gc.c39_wache_ist_ganz_oder_gar_nicht(texte, {GATE: ""},
                                                     root=wurzel, live=True)
        self.assertTrue(any("W2-HALBER-AUFRUF" in f[1] for f in funde),
                        [f[1] for f in funde])

    def test_c39_bleibt_still_im_echten_bestand(self):
        funde = gc.c39_wache_ist_ganz_oder_gar_nicht(
            {"wachen_vertrag.py": _lies(WACHE)}, {GATE: _lies(GATE)}, root=WURZEL)
        self.assertEqual([], funde)

    def test_wache_ist_dauerhaft_unter_siegel_verankert(self):
        """Ein `--add` allein hält nicht: `signieren()` baut die Map aus FEST.

        Am 16.10.2026 belegt (WF-6F7F): `--add scripts/wachen_vertrag.py`
        meldete „in den Lock aufgenommen“, und die nächste Signatur nahm den
        Eintrag wieder heraus, weil der Pfad nicht in KRITISCH|FEST stand.
        Deshalb steht die Wache in der Quelle – nicht nur in der Akte.
        """
        baum = ast.parse(_lies(os.path.join(WURZEL, "scripts", "integrity_guard.py")))
        gruppen = {}
        for knoten in baum.body:
            if (isinstance(knoten, ast.Assign)
                    and isinstance(knoten.targets[0], ast.Name)
                    and knoten.targets[0].id in ("KRITISCH", "FEST")):
                gruppen[knoten.targets[0].id] = {
                    ast.literal_eval(e) for e in knoten.value.elts}
        self.assertIn("wachen_vertrag.py", {p.split("/")[-1] for p in gruppen["FEST"]},
                      "die Wache muss in integrity_guard.FEST stehen")
        self.assertIn("scripts/wachen_vertrag.py", gruppen["FEST"])

    def test_add_ist_fail_closed_ohne_quelle(self):
        """`--add` auf einen Pfad ohne FEST/KRITISCH-Eintrag: laut Nein, nichts geschrieben."""
        vorher = _lies(os.path.join(WURZEL, "data", "integrity_lock.json"))
        ergebnis = subprocess.run(
            [sys.executable, os.path.join(WURZEL, "scripts", "integrity_guard.py"),
             "--add", "package.json"],
            cwd=WURZEL, capture_output=True, text=True, timeout=300)
        self.assertEqual(2, ergebnis.returncode, ergebnis.stdout + ergebnis.stderr)
        self.assertIn("steht nicht in KRITISCH oder FEST", ergebnis.stdout)
        self.assertEqual(vorher, _lies(os.path.join(WURZEL, "data", "integrity_lock.json")))


if __name__ == "__main__":
    unittest.main()
