# -*- coding: utf-8 -*-
"""Ein Befund, dessen Ursache niemand zuordnen kann, ist eine Behauptung.

DER BEFUND (21.11.2026)
=======================
Der Layout-Audit meldete auf jeder Seite:

    Layout-Audit: http://127.0.0.1:36989/posts/… (390x844): console:
    Loading the script 'https://static.cloudflareinsights.com/beacon.min.js'
    violates the following Content Security Policy directive:
    "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com"

DIE ERSTE ERKLÄRUNG WAR FALSCH
==============================
Zuerst stand hier: „Der lokale Messserver setzt keine CSP, die Meta-CSP hat
kein `script-src` – also stammt die Direktive aus der Runner-Umgebung." Der
letzte Satz war geraten. Der Beleg vom Folgelauf zeigt die echte Kette:

    Audit-Sample (lexikografisch letzte Verzeichnisse unter posts/)
      → `zahnzusatzversicherung-lohnt-sich`, `zinseszinseffekt-formel-erklaert`
      → beides Meta-Refresh-Seiten aus scripts/weiterleitungen.py
      → Refresh auf https://franksfinanzcheck.de/pillar/…
      → Chrome folgt, der Audit misst die PRODUKTION
      → dort: alte Edge-CSP (ohne Beacon-Domain) + Cloudflare-Beacon
      → Befund, obwohl in der Meldung 127.0.0.1 steht.

DIE REGEL, DIE HIER FESTGEHALTEN WIRD
=====================================
    1. Der Audit misst NUR den lokalen Bau. Hauptnavigationen zu fremden
       Herkünften werden abgebrochen; ein Verlassen der Herkunft ist ein
       Werkzeugfehler (Exit 3), kein Seitenbefund.
    2. Die CSP der Messung kommt aus `static/_headers` – der Sollstand des
       Repositories, nicht der Kopfzeilen-Zufall der Umgebung.
    3. Ein CSP-Verstoß ist nur dann ein Seitenbefund, wenn die EIGENE CSP im
       Dokument wiedergefunden wurde und keine fremde CSP dazukam. Sonst ist
       er „unbelegt" und wird als Frühwarnung mit Grund berichtet.

Das ist keine Entschuldigung, sondern eine Belegpflicht – dieselbe Logik wie
in `push_diagnose.py`: Klassifizieren statt raten.

Die CSP-Freigabe selbst (`static/_headers`, `cloudflare/edge-schutz.md`) ist
die zweite Hälfte derselben Entscheidung und wird von
`test_cloudflare_analytics_csp.py` bewacht.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "layout_browser_check.js"


class CspBrauchtEinenBelegTest(unittest.TestCase):
    """Die Belegpflicht – gelesen am Quelltext, nicht am Verhalten.

    Ein Verhaltens-Test bräuchte Chrome; die CI hat ihn, dieser Lauf nicht.
    Geprüft wird deshalb die Struktur: die Teile müssen zusammen existieren.
    Fehlt einer, ist die Regel wirkungslos.
    """

    def setUp(self):
        self.text = SCRIPT.read_text(encoding="utf-8")

    def test_kopfzeilen_werden_beobachtet(self):
        self.assertIn("cspBeobachtet", self.text,
                      "Ohne Beobachtung der CSP-Kopfzeile gibt es keinen Beleg")
        self.assertIn("content-security-policy", self.text.lower(),
                      "Der Audit muss die Kopfzeile beim Namen nennen")
        self.assertIn("r.headers()", self.text,
                      "Der Beleg stammt aus der ANTWORT (Kopfzeile), nicht aus "
                      "einer Annahme")

    def test_verstoss_ohne_eigene_csp_wird_unbelegt(self):
        """Die Bedingung, die den Unterschied macht: erst die Herkunft, dann
        die eigene CSP, dann die Fremd-CSP – erst danach ist es ein Befund."""
        zeilen = [z.strip() for z in self.text.splitlines()]
        self.assertIn("for (const text of cspMeldungen) {", zeilen)
        self.assertIn("if (!herkunftOk) {", zeilen,
                      "Eine fremde Herkunft ist ein Werkzeugfehler, kein Seitenbefund")
        self.assertIn("} else if (!traegtEigene) {", zeilen,
                      "Ohne eigene CSP im Dokument gibt es keinen Beleg")
        self.assertIn("unbelegt.push(", self.text)
        self.assertIn("errors.push('console: ' + text);", zeilen,
                      "Mit eigener, unverfälschter CSP bleibt der Verstoß ein Befund")

    def test_nur_die_dokument_antwort_ist_ein_beleg(self):
        """Die erste Fassung sammelte CSP-Kopfzeilen von JEDER Antwort.

        Ein Beleg aus der Antwort eines Skripts/Bildes sagt nichts darüber,
        ob DIESE Seite per CSP gesteuert wird.
        """
        self.assertIn("resourceType()", self.text,
                      "Der Beleg muss auf die Dokument-Antwort eingegrenzt sein")
        self.assertRegex(
            self.text, r"/\^\(document\|iframe\)\$/i",
            "Genau document|iframe sind die Typen, die eine Seite per CSP "
            "steuern – ein Skript-/Bild-Response ist es nicht")

    def test_beleg_wird_nach_dem_laden_ausgewertet(self):
        """Die Kopfzeile kann nach dem ersten Skriptfehler eintreffen.

        Bei einer Umleitung wäre die Dokument-Antwort beim Eintreffen der
        Konsolenzeile noch nicht gesehen – ein echter Befund würde
        stillschweigend zur Frühwarnung.
        """
        self.assertIn("cspMeldungen", self.text,
                      "CSP-Meldungen müssen vorgemerkt und NACH dem Laden "
                      "ausgewertet werden")
        reihenfolge = [
            self.text.index("const endUrl = page.url();"),
            self.text.index("const herkunftOk = istEigeneHerkunft(endUrl, eigeneHerkunft);"),
            self.text.index("const traegtEigene"),
            self.text.index("for (const text of cspMeldungen) {"),
        ]
        self.assertEqual(reihenfolge, sorted(reihenfolge),
                         "Die Entscheidung hängt am ENDZUSTAND von Herkunft "
                         "und beobachteter CSP")

    def test_unbelegt_landet_in_den_fruehwarnungen(self):
        self.assertIn("CSP-Meldung nicht dem Repository zuordenbar", self.text,
                      "Unbelegte Befunde müssen sichtbar bleiben – sonst ist "
                      "die Heilung ein Verschlucken")
        self.assertRegex(
            self.text, r"warnings\.push\('CSP-Meldung nicht dem Repository zuordenbar",
            "Sie gehören in `warnings`, nicht in `issues`: `issues` macht den "
            "Lauf rot und würde die alte Behauptung nur umbenennen")

    def test_beleg_wird_im_bericht_ausgewiesen(self):
        # Nachvollziehbarkeit: das JSON der Seite nennt, ob eine eigene CSP
        # beobachtet wurde und ob eine fremde dazukam.
        self.assertRegex(self.text, r"csp: \{[^}]*eigene",
                         "Der Seitenbericht muss die Beleglage ausweisen")
        self.assertIn("fremdherkunft", self.text,
                      "Die Herkunft einer fremden CSP muss im Bericht stehen")

    def test_die_meta_csp_hat_weiterhin_kein_script_src(self):
        """Der Grund, warum die alte Meldung nicht aus dem HTML kam.

        Ändert jemand die Meta-CSP und ergänzt `script-src`, ist die
        Beleglage eine andere – dann muss dieser Test mitwandern, nicht
        stillschweigend weiterlaufen.
        """
        head = (ROOT / "layouts" / "_partials" / "head.html").read_text(encoding="utf-8")
        zeilen = [z for z in head.splitlines() if "http-equiv" in z
                  and "Content-Security-Policy" in z]
        self.assertEqual(1, len(zeilen), "genau eine Meta-CSP erwartet")
        self.assertNotIn("script-src", zeilen[0],
                         "Steht hier künftig ein script-src, stammt eine "
                         "Blockade wieder aus dem Repo – dann ist die "
                         "Belegpflicht oben nicht mehr der richtige Hebel")


class DerBelegStehtImBerichtTest(unittest.TestCase):
    """Ohne den Beleg im Bericht ist die Unterscheidung nicht nachprüfbar."""

    def _notice(self, belege, **extra):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import layout_annotations as la
        b = {"domMetrics": {"maxChildren": 50, "maxChildrenElement": "x",
                            "maxHeadChildren": 50, "maxDepth": 12,
                            "maxElements": 1196},
             "cspBelege": belege}
        b.update(extra)
        return la.summary_notice({}, b)

    def test_notice_nennt_die_ausgelieferte_csp_und_fremdanteil(self):
        text = self._notice({"gesendet": "3f2a1c9d8e7b6a50",
                             "eigeneImDokument": 12, "fremd": 0,
                             "gesehen": ["default-src 'self'"],
                             "unbelegt": 0})
        self.assertIn("eigene CSP aus static/_headers", text)
        self.assertIn("3f2a1c9d8e7b6a50", text)
        self.assertIn("Fremd-CSP: 0", text)

    def test_notice_nennt_eine_fremde_herkunft(self):
        text = self._notice({"gesendet": "3f2a1c9d8e7b6a50",
                             "eigeneImDokument": 0, "fremd": 2,
                             "fremdherkunft": ["https://franksfinanzcheck.de"],
                             "unbelegt": 2})
        self.assertIn("Fremd-CSP von https://franksfinanzcheck.de", text)

    def test_notice_nennt_den_hermetik_zustand(self):
        text = self._notice(
            {"gesendet": "3f2a1c9d8e7b6a50", "eigeneImDokument": 12,
             "fremd": 0, "unbelegt": 0},
            hermetik={"fremdnavigationenBlockiert": ["https://franksfinanzcheck.de/pillar/"],
                      "herkunftsverletzungen": [],
                      "weiterleitungenAusgelassen": ["zinseszinseffekt-formel-erklaert"]})
        self.assertIn("Messung hermetisch", text)
        self.assertIn("1 Fremd-Navigation(en) blockiert", text)
        self.assertIn("1 Weiterleitungsseite(n) ausgelassen", text)

    def test_notice_faellt_auf_den_alten_weg_zurueck(self):
        text = self._notice({"gesehen": ["script-src 'self' https://beispiel.test"],
                             "unbelegt": 2})
        self.assertIn("CSP-Beleg: Dokument-Antwort führt", text)
        self.assertIn("https://beispiel.test", text)

    def test_notice_sagt_es_wenn_keine_kopfzeile_gemessen_wurde(self):
        text = self._notice({"gesehen": [], "unbelegt": 4})
        self.assertIn("keine CSP-Kopfzeile in dieser Messung", text)
        self.assertIn("Frühwarnung, nicht Befund", text)


class HermetikTest(unittest.TestCase):
    """Der Audit darf den lokalen Bau nicht verlassen.

    DER BEFUND: Zwei Meta-Refresh-Seiten aus scripts/weiterleitungen.py waren
    im Sample. Chrome folgte ihnen in die Produktion; die dort gemessene CSP
    und der Edge-Beacon wurden als Befund über 127.0.0.1 gemeldet. Diese Tests
    halten die Sperre und ihre Belege fest.
    """

    @classmethod
    def setUpClass(cls):
        cls.text = SCRIPT.read_text(encoding="utf-8")

    def test_hauptnavigationen_werden_abgebrochen(self):
        self.assertIn("page.setRequestInterception(true)", self.text,
                      "Ohne Request-Interception gibt es keine Sperre")
        self.assertIn("req.isNavigationRequest()", self.text)
        self.assertIn("istEigeneHerkunft(req.url(), eigeneHerkunft)", self.text)
        self.assertIn("req.abort('blockedbyclient')", self.text)

    def test_herkunftsverletzung_ist_werkzeugfehler(self):
        self.assertIn("const herkunftVerletzt = results.filter(r => r.herkunftOk === false);",
                      self.text)
        self.assertIn("process.exit(3);", self.text)
        self.assertIn("Die Hermetik-Sperre hat nicht gegriffen", self.text)

    def test_csp_kommt_aus_der_repo_vorlage(self):
        self.assertIn("function cspAusHeaders(", self.text)
        self.assertIn("path.join(BASE, '_headers')", self.text)
        self.assertIn("{ csp, cspDigest, nonce }", self.text,
                      "Der Messserver muss die CSP selbst ausliefern")
        self.assertIn("'Content-Security-Policy'", self.text)

    def test_weiterleitungsseiten_sind_keine_artikelprobe(self):
        self.assertIn("function istWeiterleitungsseite(", self.text)
        self.assertIn("ff-weiterleitung", self.text)
        self.assertIn("function neuesteArtikel(", self.text)
        self.assertIn("istWeiterleitungPfad(rel)", self.text,
                      "Auch Risiko-Seiten müssen gegen Weiterleitungen gefiltert werden")

    def test_die_beiden_incident_slugs_sind_weiterleitungen(self):
        """Der Datenbeleg: genau diese zwei Seiten schickten den Audit in die
        Produktion. Verschwindet ihr Meta-Refresh, darf dieser Test wandern –
        aber nicht stillschweigend."""
        for slug in ("zahnzusatzversicherung-lohnt-sich",
                     "zinseszinseffekt-formel-erklaert"):
            datei = ROOT / "static" / "posts" / slug / "index.html"
            self.assertTrue(datei.is_file(), f"{slug} fehlt – Test veraltet?")
            html = datei.read_text(encoding="utf-8")
            self.assertIn('name="ff-weiterleitung"', html)
            self.assertIn('http-equiv="refresh"', html)
            self.assertIn("https://franksfinanzcheck.de/", html,
                          "Genau dieses Ziel hat den Audit in die Produktion gezogen")

    @unittest.skipUnless(shutil.which("node"), "Node fehlt in dieser Umgebung")
    def test_selftest_beweist_die_entscheidungen_ohne_chrome(self):
        lauf = subprocess.run(["node", str(SCRIPT), "--selftest"],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(lauf.returncode, 0, lauf.stderr)
        daten = json.loads(lauf.stdout)
        self.assertEqual(daten["selftest"], "ok")
        self.assertGreaterEqual(daten["hermetikFaelle"], 10,
                               "Die Hermetik-Fälle müssen mit dem Selbsttest wachsen")


class KeinStillerAusfallTest(unittest.TestCase):
    """Die Gegenrichtung: Die Belegpflicht darf echte Befunde nicht kosten."""

    def test_js_fehler_bleiben_rot(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("errors.push('JS: ' + e.message)", text,
                      "Ein echter JavaScript-Fehler der Seite bleibt ein Befund")
        self.assertIn("errors.push('console: ' + m.text())", text,
                      "Ein Konsolenfehler OHNE CSP-Bezug bleibt ein Befund")

    def test_mit_belegter_direktive_bleibt_der_verstoss_rot(self):
        text = SCRIPT.read_text(encoding="utf-8")
        # Eine ODER-Verknüpfung würde jeden CSP-Verstoß entschärfen – auch
        # einen belegten. Die Prüfung ist bewusst als Kette gebaut.
        self.assertNotRegex(
            text, r"cspBefund\(m\.text\(\)\) \|\|",
            "ODER würde die Belegpflicht aushebeln")
        self.assertIn("} else {\n      errors.push('console: ' + text);", text)


if __name__ == "__main__":
    unittest.main()
