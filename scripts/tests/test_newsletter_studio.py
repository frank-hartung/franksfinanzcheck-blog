#!/usr/bin/env python3
"""Regressionstest: newsletter_studio – Design-System, Zahlwerk, E-Mail-Bau.

Warum dieser Test existiert: das Studio ist der einzige Teil der Newsletter-
Strecke, der Optik und Behauptung gleichzeitig erzeugt. Ein Fehler hier ist
nicht „hässlich“, sondern messbar falsch – eine Marke, die nicht zu den
Build-Tokens passt, eine Ersparnis, die kein Artikel hergibt, eine Mail, die beim
zweiten Bauen anders aussieht. Genau diese vier Dinge sind festgehalten:

  * Präzedenz hugo.toml > data/newsletter_studio.json (ein Zustand, zwei Orte;
    hugo.toml ist versiegelt, das JSON ist der Schalter des Betreibers);
  * Zahlen nur aus dem Quelltext, mit Tausenderpunkt, ohne erfundene Beträge;
  * deterministischer Bau: gleiches Material + gleiches Datum = gleiches HTML;
  * Marken- und Themen-Deckung mit dem echten Blog.
"""
from __future__ import annotations

import datetime
import glob
import importlib.util
import json
import os
import re
import shutil
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
gc = _load("governance_contract", os.path.join(SCRIPTS, "governance_contract.py"))
sr = _load("selftest_runner", os.path.join(SCRIPTS, "selftest_runner.py"))


def _miniroot(td: str, *, toml: str = "", studio_json: str = "") -> str:
    """Nachbau eines Blog-Ordners: nur die Dateien, die das Studio anfasst."""
    root = os.path.join(td, "blog")
    for sub in ("data", "assets/css/extended", "layouts/shortcodes",
                "themes/PaperMod/assets/css/core", "content/posts"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, "hugo.toml"), "w", encoding="utf-8") as fh:
        fh.write("[params]\n" + toml)
    for rel in ("data/themenwelten.json", "assets/css/extended/custom.css",
                "themes/PaperMod/assets/css/core/reset.css",
                "themes/PaperMod/assets/css/core/theme-vars.css"):
        quell = os.path.join(ROOT, rel)
        if os.path.exists(quell):
            shutil.copy(quell, os.path.join(root, rel))
    if studio_json:
        with open(os.path.join(root, "data/newsletter_studio.json"), "w",
                  encoding="utf-8") as fh:
            fh.write(studio_json)
    return root


MATERIAL = [
    {"slug": "strom-sparen-2026",
     "titel": "Strom: was 4.000 Wattstunden im Jahr wirklich kosten",
     "url": "https://franksfinanzcheck.de/posts/strom-sparen-2026/",
     "datum": "2026-09-21", "pillar": "strom-sparen",
     "beschreibung": "Ein Haushalt mit Wärmepumpe spart 1.120 € im Jahr.",
     "quelle_text": "Ein Haushalt mit Wärmepumpe spart 1.120 € im Jahr."},
    {"slug": "dsl-wechsel",
     "titel": "DSL: der Vertrag, der sich selbst verlängert",
     "url": "https://franksfinanzcheck.de/posts/dsl-wechsel/",
     "datum": "2026-09-20", "pillar": "internet-dsl",
     "beschreibung": "Wer nach 24 Monaten wechselt, spart 18 € im Monat.",
     "quelle_text": "Wer nach 24 Monaten wechselt, spart 18 € im Monat."},
]
DATUM = datetime.date(2026, 9, 22)


class Konfiguration(unittest.TestCase):
    def test_hugo_toml_schlaegt_json(self):
        with tempfile.TemporaryDirectory() as td:
            root = _miniroot(td, toml='newsletterFormAction = "https://toml.example/form"\n',
                             studio_json='{"capture": {"form_action": "https://json.example/f"}}')
            self.assertEqual("https://toml.example/form", studio.capture(root)["form_action"])

    def test_json_allein_reicht_als_schalter(self):
        with tempfile.TemporaryDirectory() as td:
            root = _miniroot(td, studio_json='{"capture": {"form_action": "https://j.example/f",'
                                             ' "versprechen": "1 Mail pro Werktag"}}')
            fang = studio.capture(root)
            self.assertEqual("https://j.example/f", fang["form_action"])
            self.assertEqual("1 Mail pro Werktag", fang["versprechen"])

    def test_beide_leer_ist_inert_ohne_absturz(self):
        with tempfile.TemporaryDirectory() as td:
            root = _miniroot(td)
            self.assertEqual("", studio.capture(root)["form_action"])

    def test_ohne_studiodatei_bricht_der_builder_hoerbar_ab(self):
        """Kein lautloses Fallen auf Codewerte: ohne Datei gäbe es ein Mail ohne eigene Marke."""
        with tempfile.TemporaryDirectory() as td:
            root = _miniroot(td, toml='newsletterFormAction = "https://nur.toml/form"\n')
            with self.assertRaises(SystemExit) as cm:
                studio.konfiguration(root)
            self.assertIn("fehlt", str(cm.exception))
            # Der Prüfer (newsletter_digest --check) darf trotzdem lesen: er
            # meldet den Zustand, er baut kein Mail.
            locker = studio.konfiguration(root, streng=False)
            self.assertEqual("https://nur.toml/form", locker["capture"]["form_action"])
            self.assertNotIn("design", locker)

    def test_kaputtes_json_ist_fehler_nicht_leerzustand(self):
        with tempfile.TemporaryDirectory() as td:
            root = _miniroot(td, studio_json='{"email": {"breite": 620},}')
            for streng in (True, False):
                with self.assertRaises(SystemExit) as cm:
                    studio.konfiguration(root, streng=streng)
                self.assertIn("kein gültiges JSON", str(cm.exception))

    def test_doku_felder_verlassen_die_konfiguration_nicht(self):
        with tempfile.TemporaryDirectory() as td:
            root = _miniroot(td, studio_json=json.dumps(
                {"_doku": "Kommentar für den Betreiber", "_dokuQuelle": "DESIGN.md §1",
                 "email": {"breite": 620}}))
            konf = studio.konfiguration(root, streng=False)
            self.assertEqual(620, konf["email"]["breite"])
            self.assertNotIn("_doku", json.dumps(konf, ensure_ascii=False))



class Zahlwerk(unittest.TestCase):
    def test_euro_mit_und_ohne_tausenderpunkt(self):
        self.assertEqual(2800, studio.zahl_aus_text("2.800 € pro Jahr gespart")["wert"])
        self.assertEqual(2800, studio.zahl_aus_text("2800 € pro Jahr gespart")["wert"])

    def test_beleg_wird_mitgegeben_nicht_umgeschrieben(self):
        fund = studio.zahl_aus_text("Wer wechselt, spart 2.800 € pro Jahr.")
        self.assertEqual("2.800 €", fund["beleg"],
                         "die Zeile in der Mail muss die Zeile aus dem Artikel sein")

    def test_kleingeld_und_plauderzahlen_sind_keine_tagesersparnis(self):
        self.assertIsNone(studio.zahl_aus_text("5 € Gebühr, die du sparst")["wert"])
        self.assertIsNone(studio.zahl_aus_text("Stand: 12.09.2026, gespart wird wenig")["wert"])

    def test_ohne_spar_kontext_zaehlt_kein_betrag(self):
        self.assertIsNone(studio.zahl_aus_text("Das Haus kostet 480.000 €.")["wert"],
                          "Vermögenszahlen sind keine Ersparnis – das ist der "
                          "Klassiker, den die Kontextpflicht verhindert")

    def test_prozent_wird_nicht_zu_euro(self):
        self.assertEqual(300, studio.zahl_aus_text("67 % der Haushalte sparen 300 €")["wert"])

    def test_zahlen_im_text_normalisiert_separatoren(self):
        mengen = studio.zahlen_im_text("2.800 € und 2 800 € und 118 €")
        self.assertIn("2800", mengen)
        self.assertIn("118", mengen)

    def test_spar_zahl_nimmt_die_redaktionellen_leitplanken(self):
        konf = studio.konfiguration(ROOT, streng=False)
        fund = studio.spar_zahl(MATERIAL, konf)
        self.assertEqual(1120, fund["wert"])
        self.assertIn("1.120", fund["beleg"])


class Bau(unittest.TestCase):
    def test_gleiches_material_gibt_dasselbe_html(self):
        a = studio.baue_email(MATERIAL, datum=DATUM, root=ROOT)
        b = studio.baue_email(MATERIAL, datum=DATUM, root=ROOT)
        self.assertEqual(a["html"], b["html"],
                         "Nicht-Determinismus: eine Mail, die beim zweiten Bauen "
                         "anders aussieht, kann niemand abnehmen")
        self.assertEqual(a["betreff"], b["betreff"])

    def test_keine_versteckte_uhr_und_kein_zufall(self):
        quell = open(os.path.join(SCRIPTS, "newsletter_studio.py"), encoding="utf-8").read()
        for geist in ("random.", "datetime.datetime.now(", "time.time("):
            self.assertNotIn(geist, quell,
                             f"{geist} macht den Bau nicht wiederholbar – "
                             "nur das übergebene Datum darf zählen")

    def test_pflichten_eines_agentur_mails(self):
        h = studio.baue_email(MATERIAL, datum=DATUM, root=ROOT)["html"]
        self.assertIn("<!DOCTYPE html", h)
        self.assertIn("{{unsubscribe}}", h, "Einzelklammer {unsubscribe} ersetzt Brevo nie")
        self.assertNotIn("{unsubscribe}", h.replace("{{unsubscribe}}", ""))
        breite = studio.konfiguration(ROOT, streng=False)["email"]["breite"]
        self.assertIn(f"max-width:{breite}px", h,
                      "die Mail-Breite kommt aus der Konfiguration, nicht aus dem Kopf")
        self.assertIn("@media (prefers-color-scheme: dark)", h,
                      "ohne Dunkel-Modus ist eine Mail um 22 Uhr eine weiße Fläche")
        self.assertIn("schemas-microsoft-com:office:word", h,
                      "ohne VML ist der Knopf in Outlook eine Textstelle")
        for verboten in ("display:flex", "display: grid", "position:absolute", "<script",
                         "@import", "<form"):
            self.assertNotIn(verboten, h, f"{verboten} überlebt nicht jeden Mail-Client")
        for link in re.findall(r'href="([^"]+)"', h):
            self.assertTrue(link.startswith("https://") or link.startswith("mailto:")
                            or "{{" in link, f"kein absoluter HTTPS-Link: {link}")
        self.assertGreater(len(studio.baue_email(MATERIAL, datum=DATUM,
                                                root=ROOT)["text"]), 200,
                           "Textalternative zu dünn für Reader ohne HTML")

    def test_quelltext_reicht_bis_in_die_pruefung(self):
        email = studio.baue_email(MATERIAL, datum=DATUM, root=ROOT)
        self.assertEqual(2, len(email["material"]))
        self.assertIn("1120", " ".join(studio.zahlen_im_text(
            email["material"][0]["quelle_text"])),
            "ohne Quelle in `material` kann Q16 die Hero-Zahl nicht belegen")

    def test_betreff_varianzen_marke_und_laenge(self):
        var = studio.baue_email(MATERIAL, datum=DATUM, root=ROOT)["betreff_varianten"]
        self.assertGreaterEqual(len(var), 2, "eine Variante ist kein A/B-Test")
        for v in var:
            self.assertTrue(8 <= len(v["text"]) <= 78, v["text"])
            self.assertNotIn("AW:", v["text"])
            self.assertNotRegex(v["text"], r"<[a-z]", "Markup im Betreff")

    def test_ausgabe_nr_zaehlt_die_kalenderwoche(self):
        self.assertEqual("Ausgabe 39/2026", studio.ausgabe_nr(DATUM))

    def test_builder_und_vorschau_schreiben_nur_ins_temporaere(self):
        with tempfile.TemporaryDirectory() as td:
            rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "newsletter_studio.py"),
                                 "--build", "--vorschau", "--days", "400",
                                 "--datum", "2026-09-22", "--out", td],
                                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)
            geschrieben = sorted(os.path.basename(p) for p in glob.glob(os.path.join(td, "*")))
            # `--days 400` holt Material; ohne neuen Beitrag darf der Builder aber
            # leer ausgehen – und muss das sagen, statt alte Ausgaben neu zu verpacken.
            if not geschrieben:
                self.assertIn("kein Material", rc.stdout,
                              "Ausgabe leer, ohne Grund: " + rc.stdout + rc.stderr)
                return
            self.assertIn("vorschau.html", geschrieben)
            self.assertTrue(any(p.startswith("ausgabe-2026-09-22") and p.endswith(".html")
                                for p in geschrieben), geschrieben)
            self.assertTrue(any(p.endswith(".txt") for p in geschrieben), geschrieben)
        # Und nie in die Hugo-Ausgabe: public/ gehört dem Build, nicht dem Studio.
        quell = open(os.path.join(SCRIPTS, "newsletter_studio.py"), encoding="utf-8").read()
        self.assertNotIn('"public', quell, "das Studio schreibt in public/ – "
                                          "die Datei gehört dem Hugo-Build")


class Deckung_mit_dem_Blog(unittest.TestCase):
    def test_marke_und_themen_stimmen_mit_dem_letzten_Stand(self):
        funde, gepruefte = studio.marken_abgleich(ROOT)
        self.assertEqual([], list(funde), "Design-Tokens drifteten aus dem Build-CSS")
        self.assertGreater(len(gepruefte), 6, "zu wenige Farbrollen haben eine Herleitung")
        self.assertEqual([], studio.themen_abgleich(ROOT),
                         "Newsletter-Themen sind nicht mehr die Themenwelten der Site")

    def test_erfundenes_thema_wird_gemerkt(self):
        with tempfile.TemporaryDirectory() as td:
            root = _miniroot(td)
            shutil.copy(os.path.join(ROOT, "data/newsletter_studio.json"),
                        os.path.join(root, "data/newsletter_studio.json"))
            pfad = os.path.join(root, "data/newsletter_studio.json")
            text = open(pfad, encoding="utf-8").read().replace(
                '"themen": [\n',
                '"themen": [\n    {"id": "erfunden", "label": "Erfunden"},\n', 1)
            with open(pfad, "w", encoding="utf-8") as fh:
                fh.write(text)
            funde = studio.themen_abgleich(root)
            self.assertTrue(any("erfunden" in f for f in funde),
                            f"Thema ohne Themenwelt müsste ein Fund sein: {funde}")

    def test_fremde_farbe_ohne_herleitung_wird_gemerkt(self):
        with tempfile.TemporaryDirectory() as td:
            root = _miniroot(td)
            shutil.copy(os.path.join(ROOT, "data/newsletter_studio.json"),
                        os.path.join(root, "data/newsletter_studio.json"))
            pfad = os.path.join(root, "data/newsletter_studio.json")
            data = json.loads(open(pfad, encoding="utf-8").read())
            data["design"]["hell"]["seite"] = "#123456"          # ohne Herleitung, ohne Grund
            data["design"]["hell"].pop("herleitung", None)
            with open(pfad, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(data, ensure_ascii=False))
            funde, _ = studio.marken_abgleich(root)
            self.assertTrue(funde, "eine Farbe, die kein Token der Site kennt, "
                                   "muss als Befund zurückkommen")

    def test_kontrast_wird_gemessen_nicht_geschaetzt(self):
        messung = studio.kontrast_pruefung(studio.konfiguration(ROOT, streng=False))
        self.assertGreaterEqual(len(messung), 12, "beide Modi × Pflichtpaare")
        for eintrag in messung:
            self.assertTrue(eintrag["ok"], f"{eintrag['modus']}/{eintrag['paar']}: "
                                           f"{eintrag.get('wert')} < {eintrag.get('mindest')}")
            self.assertGreater(eintrag["wert"], 1.0)


class Verdrahtung(unittest.TestCase):
    def test_selbsttest_der_wache(self):
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "newsletter_studio.py"),
                             "--selftest"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)

    def test_brand_pruefung_gruen(self):
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "newsletter_studio.py"),
                             "--brand"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)

    def test_beide_wachen_im_qualitaets_gate(self):
        for name in ("newsletter_studio.py", "newsletter_qa.py"):
            self.assertIn(name, gc.GUARDS, f"{name} fehlt in den Guards")
            self.assertEqual([], sr.verdrahtet(name), f"{name} läuft nicht im Gate")

    def test_studio_json_ist_der_einzige_ort_fuer_markenwerte(self):
        """Kein Hex-Wert in den Templates, die das Studio gebaut hat (DESIGN.md §7)."""
        for rel in ("layouts/shortcodes/newsletter_form.html",
                    "layouts/_partials/newsletter_strip.html",
                    "layouts/shortcodes/newsletter_muster.html"):
            text = open(os.path.join(ROOT, rel), encoding="utf-8").read()
            self.assertNotRegex(text, r"#[0-9A-Fa-f]{6}\b",
                                f"{rel} enthält eine harte Farbe – Token oder nothing")


if __name__ == "__main__":
    unittest.main(verbosity=2)
