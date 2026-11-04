"""Regressionstests zum Bestands-Einzigartigkeit-Gate (Meldung #1027, PR #1043).

ANLASS
------
Die Heilung von #1027 hat zwei Ebenen: den BESTAND (Absätze eigenständig
formuliert) und den VERTRAG (V4 misst eine geplante Änderung vor dem
Schreiben). Beides zusammen deckt aber nur die Schreiber ab, die den Vertrag
aufrufen – und den Fall, der #1027 ausgelöst hat, deckt es gar nicht:
Commit 69f08c40 (#1017) hat den BNetzA-Absatz von HAND in drei Live-Artikel
gesetzt. Kein Schreiber, kein Vertrag, kein Gate.

`scripts/bestand_einzigartigkeit_gate.py` schließt diese Lücke: Es misst
jeden GEÄNDERTEN Artikel gegen den Bestand – egal wer ihn geschrieben hat –
und meldet nur, was der Diff NEU erzeugt.

WAS HIER FESTGEHALTEN WIRD
--------------------------
1. Die Regel: erzeugen/verstärken = Befund, abbauen/unverändert = still.
2. Die Messung ist die des Audits (clean_body + ngrams + KRITISCH_AB).
3. Der ECHTE Vorfall: gegen 69f08c40~1 meldet das Gate genau die zwei
   live↔live-Paare, die das Tagesaudit zwei Tage später als #1027 meldete.
4. Das Gate läuft im Qualitäts-Gate (CI) – eine Wache ohne Aufrufer ist
   ein Protokoll (Lehre aus #585).

Ausführung:  python3 -m unittest scripts.tests.test_bestand_einzigartigkeit_gate -v
"""
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = str(ROOT / "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import bestand_einzigartigkeit_gate as gate  # noqa: E402
import check_uniqueness as cu  # noqa: E402

# Der Absatz, den #1017 wörtlich in drei Live-Artikel gesetzt hat.
BNETZA = (
    "Bei einer einseitigen Preisänderung können Verbraucher grundsätzlich ohne "
    "Frist zum Zeitpunkt der Änderung kündigen; der Vertrag endet am Vortag. "
    "Ausnahmen gelten insbesondere bei einer vereinbarten separierten Klausel "
    "für bestimmte hoheitliche Änderungen oder einer reinen Weitergabe einer "
    "Umsatzsteueränderung. Prüfe dein Schreiben und die Klausel."
)
EIGEN = (
    "Ein Router gehört selten an den besten Platz. Wer ihn vom Boden auf das "
    "Regal hebt, gewinnt oft mehr als ein neuer Tarif verspricht. Miss das "
    "WLAN in jedem Zimmer, bevor du den Vertrag anfasst."
)
DRITT = (
    "Die Schlussrechnung kommt meist dann, wenn niemand mehr hinsieht. Notiere "
    "den Endstand am letzten Liefertag und vergleiche ihn mit dem Foto vom "
    "Zähler; so bleibt jede Position nachprüfbar."
)


def _rohtext(body: str) -> str:
    return '---\ntitle: "X"\ndraft: false\n---\n\n' + body + "\n"


def _bestand() -> dict:
    return {
        "/k/posts/2026-10-01-fremd/index.md": {
            "slug": "2026-10-01-fremd", "title": "Fremd",
            "body": cu.clean_body(_rohtext(BNETZA)),
            "live": True, "grund": "", "date": "2026-10-01T08:00:00Z"},
        "/k/posts/2026-10-02-eigen/index.md": {
            "slug": "2026-10-02-eigen", "title": "Eigen",
            "body": cu.clean_body(_rohtext(EIGEN)),
            "live": True, "grund": "", "date": "2026-10-02T08:00:00Z"},
    }


class RegelTests(unittest.TestCase):
    """Die Regel selbst – ohne Dateizugriff, ohne Uhr, ohne Git."""

    def setUp(self):
        self.grams = gate._grams_bestand(_bestand())
        self.slug = "2026-11-01-probe"

    def test_uebernommene_passage_ist_ein_befund(self):
        treffer = gate.dubletten_einer_aenderung(
            self.slug, _rohtext(EIGEN), _rohtext(BNETZA), self.grams)
        self.assertEqual(len(treffer), 1, treffer)
        self.assertIn("2026-10-01-fremd", treffer[0]["paar"])
        self.assertEqual(treffer[0]["vorher"], 0)
        self.assertGreaterEqual(treffer[0]["nachher"], cu.KRITISCH_AB)
        self.assertEqual(treffer[0]["art"], "erzeugt")
        self.assertTrue(treffer[0]["beispiel"], "der Befund nennt kein Beispiel")

    def test_eigener_text_bleibt_still(self):
        self.assertEqual(gate.dubletten_einer_aenderung(
            self.slug, _rohtext(EIGEN), _rohtext(EIGEN + " Ein weiterer Satz."),
            self.grams), [])

    def test_altlast_wird_nicht_angelastet(self):
        """Stand schon vorher über der Schwelle und wächst nicht → kein Befund."""
        self.assertEqual(gate.dubletten_einer_aenderung(
            self.slug, _rohtext(BNETZA), _rohtext(BNETZA + " Zusatz."),
            self.grams), [])

    def test_abbau_wird_nicht_bestraft(self):
        """Wer eine Dublette abbaut, erzeugt keine neue – und wird nicht rot."""
        self.assertEqual(gate.dubletten_einer_aenderung(
            self.slug, _rohtext(BNETZA), _rohtext(DRITT), self.grams), [])

    def test_eigener_artikel_ist_keine_gegenseite(self):
        self.assertEqual(gate.dubletten_einer_aenderung(
            "2026-10-01-fremd", _rohtext(EIGEN), _rohtext(BNETZA),
            self.grams), [])

    def test_verstaerkung_ist_ein_befund(self):
        """Eine bestehende Dublette, die wächst, ist ein Befund – kein Freispruch."""
        # 12 Wörter ⇒ 6 geteilte 7-Gramme: schon über der Schwelle (5),
        # also eine Altlast – die neue Fassung wächst auf 37. Das ist
        # „verstärkt", nicht „erzeugt".
        kurz = " ".join(BNETZA.split()[:12])
        lang = BNETZA
        treffer = gate.dubletten_einer_aenderung(
            self.slug, _rohtext(kurz), _rohtext(lang), self.grams)
        self.assertEqual(len(treffer), 1, treffer)
        self.assertEqual(treffer[0]["art"], "verstärkt")
        self.assertGreater(treffer[0]["nachher"], treffer[0]["vorher"])

    def test_paar_wird_einmal_gemeldet(self):
        """Beide Seiten geändert = EIN Befund, nicht zwei (Paar-Identität).

        Der Vorfall hatte genau diese Form: 08-10 war die QUELLE der
        Übernahme, 08-12 hat sie ebenfalls erhalten. Ohne kanonisches Paar
        stünde dieselbe Dublette zweimal im Bericht – und ein doppelter
        Befund ist ein halbierter Befund (die Redaktion sucht zwei Fehler).
        """
        # A übernimmt die Passage von B; B übernimmt sie von A – und BEIDE
        # sind Teil des Diffs. Genau so sah #1017 aus.
        # Der Bestand trägt die Passage, die beide gleichzeitig übernehmen –
        # sonst gäbe es keine Gegenseite und der Fall prüfte nichts.
        beide = {
            "/k/posts/2026-11-01-a/index.md": {
                "slug": "2026-11-01-a", "title": "A",
                "body": cu.clean_body(_rohtext(BNETZA)),
                "live": True, "grund": "", "date": "2026-11-01T08:00:00Z"},
            "/k/posts/2026-11-02-b/index.md": {
                "slug": "2026-11-02-b", "title": "B",
                "body": cu.clean_body(_rohtext(BNETZA)),
                "live": True, "grund": "", "date": "2026-11-02T08:00:00Z"},
        }
        grams = gate._grams_bestand(beide)
        a = gate.dubletten_einer_aenderung("2026-11-01-a", _rohtext(EIGEN),
                                           _rohtext(BNETZA), grams)
        b = gate.dubletten_einer_aenderung("2026-11-02-b", _rohtext(EIGEN),
                                           _rohtext(BNETZA), grams)
        self.assertTrue(a and b, (a, b))
        self.assertEqual(a[0]["paar"], b[0]["paar"],
                         "beide Richtungen müssen dasselbe kanonische Paar ergeben")
        self.assertEqual(a[0]["paar"], ("2026-11-01-a", "2026-11-02-b"))

class MessungsSSTests(unittest.TestCase):
    """Keine zweite Wahrheit: dieselbe Größe wie das Tagesaudit."""

    def test_schwelle_ist_importiert(self):
        self.assertEqual(cu.KRITISCH_AB, 5)
        quelle = (SCRIPTS + "/bestand_einzigartigkeit_gate.py")
        with open(quelle, encoding="utf-8") as fh:
            eigene = [z for z in fh if re.match(r"\s*KRITISCH_AB\s*=", z)]
        self.assertEqual(eigene, [], "das Gate definiert eine eigene Schwelle")

    def test_nutzt_die_audit_funktionen(self):
        quelle = open(SCRIPTS + "/bestand_einzigartigkeit_gate.py",
                      encoding="utf-8").read()
        for name in ("cu.clean_body", "cu.ngrams", "cu.KRITISCH_AB",
                     "cu.lade_bestand"):
            self.assertIn(name, quelle,
                          f"das Gate benutzt {name} nicht – zweite Messung")

    def test_leerer_bestand_ist_fail_closed(self):
        with self.assertRaises(ValueError):
            gate.pruefe_diff("HEAD", bestand={})


class VorfallTests(unittest.TestCase):
    """Der ECHTE Vorfall vom 02.11.2026 – eingefroren, nicht nacherzählt."""

    def test_gate_faengt_den_vorfall_1017(self):
        """Gegen 69f08c40~1 meldet das Gate die zwei live↔live-Paare aus #1027.

        Vor der Heilung stand der BNetzA-Absatz wörtlich in drei Live-Artikeln.
        Das Tagesaudit fand es zwei Tage später; ein PR-Gate hätte es am Tag
        der Änderung gefunden. Genau diese Zeitdifferenz ist der Schaden.
        """
        try:
            subprocess.run(["git", "cat-file", "-e", "69f08c40~1"],
                           cwd=ROOT, check=True, capture_output=True)
        except (subprocess.CalledProcessError, OSError):
            self.skipTest("Vorfall-Commit 69f08c40 nicht im Klon (shallow)")

        # Der Arbeitsbaum ist heute GEHEILT. Für die Vorfallprobe wird
        # deshalb genau der Stand gemessen, der am 02.11.2026 im PR stand:
        # Vorfassung aus `69f08c40~1`, Nachfassung aus `69f08c40` – der
        # Bestand (die Gegenseite) ebenfalls aus `69f08c40`. Sonst verglich
        # der Test die geheilte Fassung mit sich selbst und wäre grün,
        # obwohl das Gate blind ist.
        geaendert = [p for p in subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=M", "--no-renames",
             "69f08c40~1", "69f08c40", "--", "content/posts"],
            cwd=ROOT).decode().splitlines() if p.endswith("/index.md")]
        self.assertTrue(geaendert, "der Vorfall-Commit ändert keine Artikel")
        inhalte = {p: subprocess.check_output(
            ["git", "show", f"69f08c40:{p}"], cwd=ROOT).decode() for p in geaendert}
        # Bestand = alle Artikel des Vorfall-Stands, aus Git geholt.
        vorfall_bestand = {}
        for pfad in subprocess.check_output(
                ["git", "ls-tree", "-r", "--name-only", "69f08c40", "content/posts"],
                cwd=ROOT).decode().splitlines():
            if not pfad.endswith("/index.md"):
                continue
            raw = subprocess.check_output(["git", "show", f"69f08c40:{pfad}"],
                                          cwd=ROOT).decode()
            sichtbar, grund = cu.audit_publication_state(raw)
            vorfall_bestand[pfad] = {
                "slug": cu._slug(os.path.join(str(ROOT), pfad)),
                "title": pfad, "body": cu.clean_body(raw), "live": sichtbar,
                "grund": "" if sichtbar else grund, "date": ""}
        self.assertGreater(len(vorfall_bestand), 50,
                           "der Vorfall-Bestand ist unvollständig")
        befunde = gate.pruefe_diff("69f08c40~1", bestand=vorfall_bestand,
                                   aenderungen_liste=geaendert, inhalte=inhalte)
        paare = " | ".join(befunde)
        self.assertIn("2026-08-10-sicher-heizen", paare)
        # Die 16-Phrasen-Dublette ist der Kernfall: sie war live↔live.
        self.assertTrue(
            any("2026-08-24-preisgarantie-gas" in b and "16 " in b for b in befunde),
            f"die 16-Phrasen-Dublette 08-10 ↔ 08-24 fehlt: {befunde}")

    def test_kein_befund_fuer_den_geheilten_bestand(self):
        """Der heutige Stand erzeugt keine neue Dublette (die Heilung hält)."""
        befunde = gate.pruefe_diff("HEAD", bestand=cu.lade_bestand())
        self.assertEqual(befunde, [], f"HEAD erzeugt Befunde: {befunde}")


class VerdrahtungTests(unittest.TestCase):
    """Eine Wache ohne Aufrufer ist ein Protokoll (Lehre aus #585)."""

    def test_laeuft_im_qualitaets_gate(self):
        wf = (ROOT / ".github/workflows/link-check.yml").read_text(encoding="utf-8")
        self.assertIn("bestand_einzigartigkeit_gate.py", wf,
                      "das Gate läuft in keinem CI-Schritt – es würde nie messen")

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(gate.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
