#!/usr/bin/env python3
"""Regressionstest: newsletter_qa – die Vor-Versand-Wache (Q1..Q20).

Der Selbsttest des Moduls (``--selftest``) prüft die Regeln gegeneinander. Dieser
Test prüft die Wache gegen das, was sie im Ernstfall sieht: ein echt gebautes
Mail aus dem Bestand und danach ein Dutzend kaputter Varianten. Entscheidend
ist dabei nicht „irgendein Fund“, sondern **der richtige Code** – eine Wache,
die bei jedem Fehler Q1 meldet, ist eine Wache, die niemand abbestellt, weil
sie nie etwas specificates sagt. Und eine Wache, die bei Warnungen den Versand
blockiert, wird am ersten Montag um 05:05 Uhr abgeschaltet.
"""
from __future__ import annotations

import re

import datetime
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


studio = _load("newsletter_studio", os.path.join(SCRIPTS, "newsletter_studio.py"))
qa = _load("newsletter_qa", os.path.join(SCRIPTS, "newsletter_qa.py"))

DATUM = datetime.date(2026, 9, 22)
MATERIAL = studio.material_aus_artikel(ROOT, studio._artikel_suchen(ROOT, 400))


def _basis():
    material = MATERIAL or [{
        "slug": "test-ratgeber", "titel": "Test: 240 € pro Jahr sparen",
        "url": "https://franksfinanzcheck.de/posts/test-ratgeber/",
        "datum": DATUM.isoformat(), "pillar": "strom-sparen",
        "beschreibung": "Wer den Tarif wechselt, spart 240 € im Jahr.",
        "quelle_text": "Wer den Tarif wechselt, spart 240 € im Jahr."}]
    email = studio.baue_email(material, datum=DATUM, root=ROOT)
    return email, material


class Saubere_Ausgabe(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.email, cls.material = _basis()
        cls.konf = studio.konfiguration(ROOT)
        cls.ergebnis = qa.pruefe(cls.email, konf=cls.konf, materiale=cls.material,
                                zustand={}, root=ROOT)

    def test_volles_regelwerk_und_hundert_punkte(self):
        self.assertEqual(20, len(qa.REGELN))
        self.assertGreaterEqual(self.ergebnis["regeln_geprueft"], 20)
        self.assertEqual([], self.ergebnis["funde"],
                         "das eigene Studio-Mail darf nicht durchfallen: "
                         + json.dumps(self.ergebnis["funde"], ensure_ascii=False))
        self.assertEqual(100, self.ergebnis["score"])
        self.assertTrue(self.ergebnis["bestanden"])

    def test_messwerte_sind_keine_dekoration(self):
        mess = self.ergebnis["messwerte"]
        for schluessel in ("woerter", "html_bytes", "links", "bilder",
                           "min_kontrast_hell", "min_kontrast_dunkel"):
            self.assertIn(schluessel, mess, list(mess))
        self.assertGreater(mess["woerter"], 100)
        # WCAG 4.5:1 für Fließtext – der Wert kommt aus der Messung, nicht aus dem Kopf
        self.assertGreaterEqual(mess["min_kontrast_hell"], 4.5)
        self.assertGreaterEqual(mess["min_kontrast_dunkel"], 4.5)


class Fundrichtigkeit(unittest.TestCase):
    """Jede Mutation muss den Satz verletzen, der geprüft wird – nicht nur irgendwas."""

    @classmethod
    def setUpClass(cls):
        cls.email, cls.material = _basis()
        cls.konf = studio.konfiguration(ROOT)

    def _codes(self, html=None, *, betreff=None, preheader=None, konf=None, zustand=None,
                text=None):
        email = dict(self.email)
        if html is not None:
            email["html"] = html
        if text is not None:
            email["text"] = text
        if betreff is not None:
            email["betreff"] = betreff
        if preheader is not None:
            email["preheader"] = preheader
        er = qa.pruefe(email, konf=konf or self.konf, materiale=self.material,
                       zustand=zustand or {}, root=ROOT)
        return {f["regel"] for f in er["funde"]}, {w["regel"] for w in er["warnungen"]}, er

    def test_einzelklammer_ist_kein_abmeldelink(self):
        funde, _, _ = self._codes(self.email["html"].replace("{{unsubscribe}}", "{unsubscribe}"))
        self.assertIn("Q3", funde)

    def test_script_und_flex_verlassen_die_tabelle_nicht(self):
        funde, _, _ = self._codes(self.email["html"].replace(
            "<body", '<script>alert(1)</script><body style="display:flex"'))
        self.assertIn("Q2", funde)

    def test_relativer_link_ist_in_einer_mail_tot(self):
        funde, _, _ = self._codes(self.email["html"].replace(
            "https://franksfinanzcheck.de/posts/", "/posts/"))
        self.assertIn("Q4", funde)

    def test_fehtender_abmeldelink_ist_rechtspflicht(self):
        """Nur der Text „Abmelden“ reicht nicht: weg ist die Pflichtangabe."""
        kaputt = re.sub(r"<a href=\"\{\{unsubscribe\}\}\"[^>]*>Abmelden</a>", "",
                        self.email["html"])
        self.assertNotEqual(kaputt, self.email["html"], "die Mutation muss etwas ändern")
        funde, _, er = self._codes(kaputt)
        self.assertIn("Q10", funde)
        self.assertIn("Q3", funde, "ohne Marker bleibt die Vorlage eine leere Zeile")
        self.assertFalse(er["bestanden"])

    def test_viewport_wird_nicht_nachgesehen_sondern_gemessen(self):
        funde, _, _ = self._codes(self.email["html"].replace(
            '<meta name="viewport"', '<meta name="x-viewport"'))
        self.assertIn("Q13", funde)

    def test_dokumentkopf_hartes_und_weiches_getrennt(self):
        """`lang` fehlt ist ein Fund, ein Doctype in Kurzform nur eine Warnung –
        die Unterscheidung ist der Grund, warum die Wache morgens nicht abstellt."""
        funde, warnen, _ = self._codes(self.email["html"].replace('<html lang="de"', "<html"))
        self.assertIn("Q14", funde)
        ohne_doctype = re.sub(r"<!DOCTYPE[^>]*>\s*", "", self.email["html"], count=1)
        funde2, warnen2, er2 = self._codes(ohne_doctype)
        self.assertIn("Q14", warnen2 | funde2)
        meldungen = " ".join(e["meldung"] for e in er2["warnungen"] + er2["funde"])
        self.assertIn("Quirks", meldungen,
                      "eine Meldung ohne Folge ist kein Befund, sondern Rauschen")

    def test_ersparnis_ohne_beleg_im_betreff(self):
        funde, _, _ = self._codes(betreff="4.712 € sparen – nur heute")
        self.assertIn("Q16", funde)

    def test_preheader_der_den_betreff_wiederholt(self):
        betreff = self.email["betreff"]
        funde, _, _ = self._codes(betreff=betreff, preheader=betreff)
        self.assertIn("Q9", funde)

    def test_tracking_pixel_ist_ein_datenschutzfund(self):
        funde, _, _ = self._codes(self.email["html"].replace(
            "</body>",
            '<img src="https://franksfinanzcheck.de/open?t=1" width="1" height="1" '
            'alt="" border="0"></body>'))
        self.assertIn("Q19", funde)

    def test_grosse_ausgabe_clippt_in_gmail(self):
        prall = self.email["html"] + ('<p style="margin:0">Wort</p>' * 9000)
        self.assertGreater(len(prall.encode("utf-8")), qa.GMAIL_CLIP_BYTES)
        funde, _, _ = self._codes(prall)
        self.assertIn("Q1", funde)

    def test_mojibake_aus_der_pipeline(self):
        funde, _, _ = self._codes(self.email["html"].replace("Double-Opt-In", "Double-Opt-InÃ¼ber"))
        self.assertIn("Q18", funde)

    def test_betreff_wiederverwendung_aus_dem_zustand(self):
        funde, _, _ = self._codes(zustand={"zuletzt_betreff": [self.email["betreff"]]})
        self.assertIn("Q15", funde)

    def test_kontrast_drift_wird_in_beiden_modi_gemessen(self):
        kaputt = json.loads(json.dumps(self.konf))
        kaputt["design"]["dunkel"]["text"] = "#404040"
        funde, _, _ = self._codes(konf=kaputt)
        self.assertIn("Q11", funde)

    def test_warnung_bremst_nicht_aber_die_Politur_nach_ihr(self):
        """Ein Warnfund darf den Versand nicht sperren – sonst wird die Wache
        beim ersten Montag abgeschaltet, an dem nichts kaputt war."""
        html = self.email["html"].replace(
            "<body class=", '<div style="background-image:url(https://franksfinanzcheck.de/x.png)">'
            "</div><body class=")
        funde, warnen, er = self._codes(html)
        self.assertIn("Q5", warnen | funde)
        if "Q5" not in funde:
            self.assertTrue(er["bestanden"], "eine reine Warnung darf nicht blockieren")

    def test_leere_ausgabe_ist_ein_fund_und_kein_erfolg(self):
        er = qa.pruefe({"html": "", "text": "", "betreff": "", "preheader": "",
                        "blocks": [], "material": []}, konf=self.konf, materiale=[],
                       zustand={}, root=ROOT)
        self.assertFalse(er["bestanden"])
        self.assertGreaterEqual(len(er["funde"]), 3)
        self.assertEqual(0, max(0, er["score"]), "Score wird nicht negativ gerechnet")


class Kommandozeile(unittest.TestCase):
    def test_build_am_bestand_gruen(self):
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "newsletter_qa.py"),
                             "--build", "--days", "400"], cwd=ROOT,
                            capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)
        self.assertIn("100/100", rc.stdout)
        self.assertIn("Versand frei", rc.stdout)
        self.assertNotIn("❌", rc.stdout)

    def test_mutierte_datei_gibt_exit_eins(self):
        email, _ = _basis()
        with tempfile.TemporaryDirectory() as td:
            pfad = os.path.join(td, "kaputt.html")
            with open(pfad, "w", encoding="utf-8") as fh:
                fh.write(email["html"].replace("{{unsubscribe}}", "{unsubscribe}"))
            rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "newsletter_qa.py"),
                                 "--datei", pfad], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(1, rc.returncode, rc.stdout + rc.stderr)
            self.assertIn("[Q3]", rc.stdout)

    def test_unlesbare_quelle_ist_ausgefallen_nicht_bestanden(self):
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "newsletter_qa.py"),
                             "--datei", os.path.join(tempfile.gettempdir(), "gibt-es-nicht-qa")],
                            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(2, rc.returncode, rc.stdout + rc.stderr)
        self.assertIn("ausgefallen", rc.stdout)

    def test_json_und_md_bericht(self):
        er = qa.pruefe(*_basis()[:1], konf=studio.konfiguration(ROOT),
                       materiale=_basis()[1], zustand={}, root=ROOT)
        json.dumps(er, ensure_ascii=False)   # der Report muss serialisierbar sein
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "newsletter_qa.py"),
                             "--build", "--days", "400", "--json"], cwd=ROOT,
                            capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stderr)
        out = json.loads(rc.stdout)
        self.assertEqual(100, out["score"])
        self.assertIn("regeln_geprueft", out)
        self.assertEqual(20, len(qa.REGELN))
        rc_md = subprocess.run([sys.executable, os.path.join(SCRIPTS, "newsletter_qa.py"),
                                "--build", "--days", "400", "--md"], cwd=ROOT,
                               capture_output=True, text=True)
        self.assertIn("|", rc_md.stdout, "Markdown für die CI-Summary")


if __name__ == "__main__":
    unittest.main(verbosity=2)
