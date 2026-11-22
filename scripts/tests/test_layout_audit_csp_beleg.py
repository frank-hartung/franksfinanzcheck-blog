# -*- coding: utf-8 -*-
"""Ein Befund, dessen Ursache niemand zuordnen kann, ist eine Behauptung.

DER BEFUND (21.11.2026)
=======================
Der Layout-Audit meldete auf jeder Seite:

    Layout-Audit: http://127.0.0.1:36989/posts/… (390x844): console:
    Loading the script 'https://static.cloudflareinsights.com/beacon.min.js'
    violates the following Content Security Policy directive:
    "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com"

Der Befund war rot und blockierte den PR. Nachprüfbar war er nicht:

* Die **Meta-CSP** im gebauten HTML (`layouts/_partials/head.html`, Zeile 16)
  hat gar kein `script-src` – sie erlaubt `base-uri`, `object-src` und
  `form-action`. Ohne `script-src` ist der Beacon erlaubt.
* Der **lokale Messserver** (`serve()` in `layout_browser_check.js`) setzt
  `Content-Type` und sonst nichts – er kann `static/_headers` nicht
  ausliefern. Die Direktive im Text kann also nicht von dort kommen.
* Damit bleibt keine Repo-Quelle. Der Text stammt aus einer Kopfzeile, die
  außerhalb dieses Repositories gesetzt wird (Edge-Transform-Rule bzw. die
  Injektion selbst).

WARUM DAS EIN ECHTER FEHLER IM AUDIT WAR
========================================
Der Audit nahm jede Konsolenzeile vom Typ `error` als Seitenbefund. Er hat
nicht geprüft, ob die Bedingung, die die Seite angeblich verletzt, in SEINER
Messung überhaupt existiert. Ergebnis: ein roter Lauf mit einer Ursache, die
im Repo nicht liegt – und ein Rat („CSP ergänzen"), der am gemeldeten Objekt
vorbeigeht, weil die Messung die CSP nie gesehen hat.

DIE REGEL, DIE HIER FESTGEHALTEN WIRD
=====================================
    Ein CSP-Befund ist nur dann ein Seitenbefund, wenn die CSP in derselben
    Messung als Kopfzeile beobachtet wurde. Sonst ist er „unbelegt": Er wird
    berichtet (Frühwarnung, mit Grund), macht den Lauf aber nicht rot.

Das ist keine Entschuldigung, sondern eine Belegpflicht – dieselbe Logik wie
in `push_diagnose.py`: Klassifizieren statt raten.

Die CSP-Freigabe selbst (`static/_headers`, `cloudflare/edge-schutz.md`) ist
die zweite Hälfte derselben Entscheidung und wird von
`test_cloudflare_analytics_csp.py` bewacht.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "layout_browser_check.js"


class CspBrauchtEinenBelegTest(unittest.TestCase):
    """Die Belegpflicht – gelesen am Quelltext, nicht am Verhalten.

    Ein Verhaltens-Test bräuchte Chrome; die CI hat ihn, dieser Lauf nicht.
    Geprüft wird deshalb die Struktur: die drei Teile müssen zusammen
    existieren. Fehlt einer, ist die Regel wirkungslos.
    """

    def setUp(self):
        self.text = SCRIPT.read_text(encoding="utf-8")

    def test_kopfzeilen_werden_beobachtet(self):
        self.assertIn("cspQuelle", self.text,
                      "Ohne Beobachtung der CSP-Kopfzeile gibt es keinen Beleg")
        self.assertIn("content-security-policy", self.text.lower(),
                      "Der Audit muss die Kopfzeile beim Namen nennen")
        self.assertIn("r.headers()", self.text,
                      "Der Beleg stammt aus der ANTWORT (Kopfzeile), nicht aus "
                      "einer Annahme")

    def test_verstoss_ohne_direktive_wird_unbelegt(self):
        self.assertIn("cspBefund", self.text)
        self.assertIn("unbelegt", self.text)
        # Die Bedingung, die den Unterschied macht: Ein CSP-Verstoß wird
        # vorgemerkt und NACH dem Laden anhand der belegten Direktive
        # entweder Befund (`errors`) oder Belegmangel (`unbelegt`).
        # Zeilenweise geprüft statt mit mehrzeiligen Regexen (CLAUDE.md,
        # Regel 6). Der erste Anlauf scheiterte an doppelten Escapes im
        # Python-String – der Code war richtig, der Test falsch.
        zeilen = [z.strip() for z in self.text.splitlines()]
        self.assertIn("if (cspBefund(m.text())) {", zeilen,
                      "Ein CSP-Verstoß muss zunächst vorgemerkt werden – beim "
                      "Eintreffen der Konsolenzeile ist die Beleglage offen")
        self.assertIn("cspMeldungen.push(m.text());", zeilen)
        self.assertIn("if (cspQuelle.kopfzeile) {", zeilen,
                      "Mit belegter Direktive bleibt der Verstoß ein Befund")
        self.assertIn("errors.push('console: ' + text);", zeilen)
        self.assertIn("unbelegt.push(text);", zeilen,
                      "Ohne Beleg wandert er nach `unbelegt`")

    def test_nur_die_dokument_antwort_ist_ein_beleg(self):
        """Der Fehlversuch, den erst der CI-Lauf gezeigt hat.

        Die erste Fassung sammelte CSP-Kopfzeilen von JEDER Antwort. Der
        Browserfehler blieb dadurch als „belegt" stehen – obwohl der
        Messserver nie eine CSP setzt. Ein Beleg aus der Antwort eines
        FREMDEN Hosts sagt nichts über die Steuerung dieser Seite.
        """
        self.assertIn("resourceType()", self.text,
                      "Der Beleg muss auf die Dokument-Antwort eingegrenzt sein")
        self.assertRegex(
            self.text, r"/\^\(document\|iframe\)\$/i",
            "Genau document|iframe sind die Typen, die eine Seite per CSP "
            "steuern – ein Skript-/Bild-Response ist es nicht")

    def test_fremdes_iframe_ist_kein_beleg(self):
        """Die dritte Fassung – nach dem CI-Lauf vom 22.11.2026.

        Turnstile & Co. liefern eigene CSP-Kopfzeilen. Zählte der Audit die
        als Beleg, wurde aus jedem „unbelegt\" wieder ein roter Befund,
        obwohl der Messserver weiterhin keine CSP sendet. Belegt ist nur die
        Antwort des Hauptrahmens.
        """
        self.assertIn("page.mainFrame()", self.text,
                      "Der Beleg muss auf den Hauptrahmen eingegrenzt sein")
        self.assertRegex(
            self.text, r"r\.frame\(\) !== page\.mainFrame\(\)",
            "Eine iframe-Antwort darf die CSP der Seite nicht belegen")

    def test_beleg_wird_nach_dem_laden_ausgewertet(self):
        """Die Kopfzeile kann nach dem ersten Skriptfehler eintreffen.

        Die zweite Fassung entschied beim Eintreffen der Konsolenzeile. Bei
        einer Umleitung wäre die Dokument-Antwort da noch nicht gesehen –
        ein echter Befund wäre stillschweigend zur Frühwarnung geworden.
        """
        self.assertIn("cspMeldungen", self.text,
                      "CSP-Meldungen müssen vorgemerkt und NACH dem Laden "
                      "ausgewertet werden")
        self.assertRegex(
            self.text,
            r"for \(const text of cspMeldungen\) \{\s*\n\s*if \(cspQuelle\.kopfzeile\)",
            "Die Entscheidung hängt am ENDZUSTAND von cspQuelle")

    def test_unbelegt_landet_in_den_fruehwarnungen(self):
        self.assertIn("CSP ohne Belegquelle", self.text,
                      "Unbelegte Befunde müssen sichtbar bleiben – sonst ist "
                      "die Heilung ein Verschlucken")
        self.assertRegex(
            self.text, r"warnings\.push\('CSP ohne Belegquelle",
            "Sie gehören in `warnings`, nicht in `issues`: `issues` macht den "
            "Lauf rot und würde die alte Behauptung nur umbenennen")

    def test_beleg_wird_im_bericht_ausgewiesen(self):
        # Nachvollziehbarkeit: das JSON der Seite nennt, ob eine CSP
        # beobachtet wurde. Ohne dieses Feld ist die Unterscheidung im
        # Nachhinein nicht prüfbar.
        self.assertRegex(self.text, r"csp: \{[^}]*kopfzeile",
                         "Der Seitenbericht muss die Beleglage ausweisen")

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
    """Ohne den Beleg im Bericht ist die Unterscheidung nicht nachprüfbar.

    Der CI-Lauf von PR #1303 zeigte den Grenzfall: Der Befund nannte die alte
    Direktive, obwohl `static/_headers` sie längst nicht mehr führt. Ob diese
    Direktive in der Messung GESEHEN wurde oder nicht, ließ sich den
    Annotationen nicht entnehmen — genau diese Lücke schließt die Notice.
    """

    def test_notice_nennt_die_gesehene_direktive(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import layout_annotations as la
        b = {"domMetrics": {"maxChildren": 50, "maxChildrenElement": "x",
                            "maxHeadChildren": 50, "maxDepth": 12,
                            "maxElements": 1196},
             "cspBelege": {"gesehen": ["script-src 'self' https://beispiel.test"],
                           "unbelegt": 2}}
        text = la.summary_notice({}, b)
        self.assertIn("CSP-Beleg: Dokument-Antwort führt", text)
        self.assertIn("https://beispiel.test", text)

    def test_notice_sagt_es_wenn_keine_kopfzeile_gemessen_wurde(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import layout_annotations as la
        b = {"domMetrics": {"maxChildren": 50, "maxChildrenElement": "x",
                            "maxHeadChildren": 50, "maxDepth": 12,
                            "maxElements": 1196},
             "cspBelege": {"gesehen": [], "unbelegt": 4}}
        text = la.summary_notice({}, b)
        self.assertIn("keine CSP-Kopfzeile in dieser Messung", text)
        self.assertIn("Frühwarnung, nicht Befund", text)

    def test_browser_check_schreibt_die_direktive_mit(self):
        text = (ROOT / "scripts" / "layout_browser_check.js").read_text(encoding="utf-8")
        self.assertIn("cspBelege", text)
        self.assertIn("gesehen:", text)


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
        # Die Bedingung ist `&&`: nur wenn BEIDES zutrifft, wird aus dem
        # Befund eine Frühwarnung. Eine ODER-Verknüpfung würde jeden
        # CSP-Verstoß entschärfen – auch einen belegten.
        self.assertNotRegex(
            text, r"cspBefund\(m\.text\(\)\) \|\|",
            "ODER würde die Belegpflicht aushebeln")


if __name__ == "__main__":
    unittest.main()
