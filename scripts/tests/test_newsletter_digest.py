#!/usr/bin/env python3
"""Regressionstest: newsletter_digest (Empfehlung 1 des Premium-Audits 12.09.2026).

Der Ausgangszustand war die teuerste Sorte Fehler: ein Newsletter, den die
Dokumentation beschrieb (`Newsletter-AI`, `NEWSLETTER-STATUS.md`), den es aber
nie gab, ein Formular-Feld in hugo.toml, das leer war, und ein Footer-Block, der
genau daran hing – also unsichtbar, folgenlos, grün. Dieser Test hält fest:

  * der Leerzustand ist erlaubt, aber nie still (INERT muss gemeldet werden,
    `--strict-inert` macht daraus einen Fehler für Läufe, die senden wollen);
  * ein totes Versprechen (Werbung ohne Anmeldeweg) und ein http-Endpunkt für
    Adressdaten sind Funde;
  * die Datenschutzerklärung, die „kein Newsletter" behauptet, wird als
    Widerspruch gemeldet – erst als Vorwarnung, hart ab dem ersten Formular;
  * Versand ist dreifach verriegelt und berührt ohne Secrets/Bestätigung kein Netz.
"""
from __future__ import annotations

import datetime
import importlib.util
import os
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


nd = _load("newsletter_digest", os.path.join(SCRIPTS, "newsletter_digest.py"))
gc = _load("governance_contract", os.path.join(SCRIPTS, "governance_contract.py"))


class Baum:
    """Minimal-Repo: hugo.toml + public/-Ausgabe + Shortcode aus dem echten Baum."""

    def __init__(self, td: str, name: str = "repo", *, toml: str = "", seite: str = "",
                 footer: str = "", datenschutz: str = "", workflow: str = ""):
        self.root = os.path.join(td, name)
        for sub in ("layouts/shortcodes", "public/newsletter", "public/datenschutz",
                    "content/posts", "data", ".github/workflows"):
            os.makedirs(os.path.join(self.root, sub), exist_ok=True)
        with open(os.path.join(self.root, "hugo.toml"), "w", encoding="utf-8") as fh:
            fh.write("[params]\n" + toml)
        shutil.copy(os.path.join(ROOT, nd.SHORTCODE_REL),
                    os.path.join(self.root, nd.SHORTCODE_REL))
        if seite != "KEINE_SEITE":
            with open(os.path.join(self.root, "public/newsletter/index.html"), "w",
                      encoding="utf-8") as fh:
                fh.write(seite)
        with open(os.path.join(self.root, "public/index.html"), "w", encoding="utf-8") as fh:
            fh.write("<html><body>" + footer + "</body></html>")
        with open(os.path.join(self.root, "public/datenschutz/index.html"), "w",
                  encoding="utf-8") as fh:
            fh.write(datenschutz)
        with open(os.path.join(self.root, nd.WORKFLOW_REL), "w", encoding="utf-8") as fh:
            fh.write(workflow)

    def seite(self, *zusatz: str) -> str:
        return ('<div class="ff-newsletter">Double-Opt-In '
                '<a href="/datenschutz/">Datenschutz</a>' + "".join(zusatz) + "</div>")


class CaptureKette(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nl-test-")
        self.addCleanup(self.tmp.cleanup)

    def test_inert_wird_laut_gemeldet_und_bleiht_gruen(self):
        b = Baum(self.tmp.name, "leer", datenschutz="<h2>8. Newsletter</h2>")
        funde, note, zustand = nd.pruefe_capture(b.root)
        self.assertEqual("inert", zustand)
        self.assertEqual([], funde)
        self.assertTrue(any(c == "inert" for _, _, c in note))

    def test_werbung_ohne_weg_ist_ein_fund(self):
        b = Baum(self.tmp.name, "wirbt", footer="<a href='x'>Jetzt Newsletter abonnieren</a>",
                 datenschutz="<h2>8. Newsletter</h2>")
        funde, _, _ = nd.pruefe_capture(b.root)
        self.assertTrue(any(c == "config-widerspruch" for _, _, c in funde), funde)

    def test_http_endpunkt_und_platzhalter_sind_funde(self):
        b = Baum(self.tmp.name, "http-fall",
                 toml='newsletterFormAction = "http://l.brevo.com/x"\n',
                 datenschutz="<h2>Newsletter</h2>", workflow="BREVO_API_KEY\n--strict-inert\n")
        with open(os.path.join(b.root, "public/newsletter/index.html"), "w",
                  encoding="utf-8") as fh:
            fh.write('<div>Double-Opt-In <a href="/datenschutz/">DS</a>'
                     '<form action="http://l.brevo.com/x"><input name="email"></form></div>')
        with open(os.path.join(b.root, "public/index.html"), "w", encoding="utf-8") as fh:
            fh.write("<html>newsletter-footer</html>")
        funde, _, _ = nd.pruefe_capture(b.root)
        self.assertIn("form-http", {c for _, _, c in funde})

    def test_widerspruch_zur_datenschutzerklaerung(self):
        ds = "<h2>8. Newsletter / Kontaktaufnahme</h2><p>Diese Website bietet derzeit " \
             "<strong>keinen Newsletter</strong> an.</p>"
        inert = Baum(self.tmp.name, "inert-fall", datenschutz=ds)
        _, note, _ = nd.pruefe_capture(inert.root)
        self.assertTrue(any(c == "ds-widerspruch-vorstudie" for _, _, c in note), note)
        b = Baum(self.tmp.name, "aktiv-fall",
                 toml='newsletterFormAction = "https://l.brevo.com/x"\n',
                 datenschutz=ds, footer="newsletter-footer",
                 workflow="BREVO_API_KEY\n--strict-inert\n")
        with open(os.path.join(b.root, "public/newsletter/index.html"), "w",
                  encoding="utf-8") as fh:
            fh.write('<div>Double-Opt-In <a href="/datenschutz/">DS</a>'
                     '<form><input name="email"></form></div>')
        funde, _, zustand = nd.pruefe_capture(b.root)
        self.assertIn("ds-widerspruch", {c for _, _, c in funde}, funde)
        self.assertEqual("kaputt", zustand)

    def test_formular_ohne_cta_ist_halbe_sache(self):
        b = Baum(self.tmp.name, "gut-fall", toml='newsletterFormAction = "https://l.brevo.com/x"\n',
                 datenschutz="<h2>Newsletter</h2>", footer="",
                 workflow="BREVO_API_KEY\n--strict-inert\n")
        with open(os.path.join(b.root, "public/newsletter/index.html"), "w",
                  encoding="utf-8") as fh:
            fh.write('<div>Double-Opt-In <a href="/datenschutz/">DS</a>'
                     '<form><input name="email"></form></div>')
        funde, _, _ = nd.pruefe_capture(b.root)
        self.assertIn("cta-versteckt", {c for _, _, c in funde}, funde)

    def test_gesunde_kette_findet_nichts(self):
        b = Baum(self.tmp.name, toml='newsletterFormAction = "https://l.brevo.com/x"\n',
                 datenschutz='<h2 id="newsletter">Newsletter</h2>'
                             '<p>Double-Opt-In, Widerruf formlos, 30 Tage.</p>',
                 footer="newsletter-footer", workflow="BREVO_API_KEY\n--strict-inert\n")
        with open(os.path.join(b.root, "public/newsletter/index.html"), "w",
                  encoding="utf-8") as fh:
            fh.write('<div>Double-Opt-In <a href="/datenschutz/">DS</a>'
                     '<form><input name="email"></form></div>')
        funde, _, zustand = nd.pruefe_capture(b.root)
        self.assertEqual([], funde)
        self.assertEqual("aktiv", zustand)


class RechtstextQuelle(unittest.TestCase):
    """Stiller-Freispruch-Fix: Ohne Hugo-Build (leeres public/) muss die
    Wache die Markdown-Quelle lesen, Vorlagen-Reste als Fund melden – und
    Markdown-Links nicht als Platzhalter verwechseln."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nl-ds-")
        self.addCleanup(self.tmp.cleanup)

    def _baum(self, name: str, ds_md: str) -> "Baum":
        b = Baum(self.tmp.name, name,
                 toml='newsletterFormAction = "https://l.brevo.com/x"\n',
                 workflow="BREVO_API_KEY\n--strict-inert\n")
        # gebaute Seite entfernen = Sandbox ohne Hugo-Build
        os.remove(os.path.join(b.root, "public", "datenschutz", "index.html"))
        d = os.path.join(b.root, "content", "datenschutz")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as fh:
            fh.write(ds_md)
        return b

    def test_quelle_ersatzt_fehlenden_build(self):
        b = self._baum("quelle",
                       "## 8. Newsletter / Kontaktaufnahme\n\n"
                       "Double-Opt-In, Widerruf formlos, Löschung 30 Tage "
                       "nach Abmeldung.\n")
        funde, _, _ = nd.pruefe_capture(b.root)
        codes = {c for _, _, c in funde}
        for code in ("ds-fehlt", "rechtstext", "ds-leer"):
            self.assertNotIn(code, codes,
                             f"Quell-Fallback bricht ({code}): {funde}")

    def test_platzhalter_im_live_text_ist_fund(self):
        b = self._baum("platzhalter",
                       "## 8. Newsletter\n\n"
                       "Speicherdauer: [30] Tage, Widerruf an [deine Adresse].\n")
        funde, _, _ = nd.pruefe_capture(b.root)
        self.assertIn("ds-platzhalter", {c for _, _, c in funde}, funde)

    def test_markdown_links_sind_kein_platzhalter(self):
        b = self._baum("links",
                       "## 8. Newsletter\n\n"
                       "Anmeldung über [die Anmeldeseite](/newsletter/), "
                       "Widerruf formlos.\n")
        funde, _, _ = nd.pruefe_capture(b.root)
        self.assertNotIn("ds-platzhalter", {c for _, _, c in funde}, funde)


class DigestUndVersand(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="nl-digest-")
        self.addCleanup(self.tmp.cleanup)

    def test_nur_live_artikel_im_fenster(self):
        heute = datetime.date.today()
        b = Baum(self.tmp.name, "digest")
        root = b.root
        for slug, datum, draft in (("2026-09-11-frisch", heute.isoformat(), "false"),
                                   ("2026-01-01-uralt", "2026-01-01", "false"),
                                   ("2026-09-11-draft", heute.isoformat(), "true"),
                                   ("2099-01-01-zukunft", "2099-01-01", "false")):
            d = os.path.join(root, "content", "posts", slug)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as fh:
                fh.write(f"---\ntitle: {slug}\ndate: {datum}T08:00:00Z\n"
                         f"description: Text zu {slug}\ndraft: {draft}\n---\nBody\n")
        seit = heute - datetime.timedelta(days=3)
        slugs = [a["slug"] for a in nd.live_artikel(root, seit)]
        self.assertEqual(["2026-09-11-frisch"], slugs)
        html, text, n = nd.baue_digest(nd.live_artikel(root, seit), heute.isoformat(),
                                      "Versprechen")
        self.assertEqual(1, n)
        self.assertIn("{unsubscribe}", html)
        self.assertIn("{unsubscribe}", text)
        self.assertIn("franksfinanzcheck.de/posts/2026-09-11-frisch/", html)

    def test_versand_verriegelt_ohne_key_und_bestaetigung(self):
        aufgerufen = []
        echt = nd.TRANSPORT
        try:
            nd.TRANSPORT = lambda *a, **k: aufgerufen.append(a) or (201, '{"id": 9}')
            root = tempfile.mkdtemp()
            os.makedirs(os.path.join(root, "data"), exist_ok=True)
            self.assertEqual(1, nd.versende(root, "<p>x</p>", "x", "Betreff",
                                           dry_run=False, test_adresse=""))
            self.assertEqual([], aufgerufen)
            for var in ("BREVO_API_KEY", "BREVO_LIST_ID"):
                os.environ[var] = "1" if var.endswith("ID") else "key"
            self.assertEqual(1, nd.versende(root, "<p>x</p>", "x", "Betreff", dry_run=False))
            self.assertEqual([], aufgerufen, "ohne NEWSLETTER_SEND wird trotzdem gesendet")
            os.environ["NEWSLETTER_SEND"] = "ja"
            self.assertEqual(0, nd.versende(root, "<p>x</p>", "x", "Betreff", dry_run=False))
            # Kampagne anlegen + senden = zwei Transporte, kein dritter Weg
            self.assertEqual(2, len(aufgerufen), "freigegebener Versand läuft nicht")
            self.assertEqual(0, nd.versende(root, "<p>x</p>", "x", "Betreff", dry_run=True))
            self.assertEqual(2, len(aufgerufen), "dry-run berührt das Netz")
        finally:
            nd.TRANSPORT = echt
            for var in ("BREVO_API_KEY", "BREVO_LIST_ID", "NEWSLETTER_SEND"):
                os.environ.pop(var, None)
            shutil.rmtree(root, ignore_errors=True)

    def test_check_laeuft_im_echten_baum_ohne_schreibzugriff(self):
        """Der reale Lauf darf nichts verändern: nur lesen, dann Urteil."""
        vorher = {}
        for rel in ("data/newsletter_state.json", "hugo.toml"):
            p = os.path.join(ROOT, rel)
            vorher[rel] = os.path.getmtime(p) if os.path.isfile(p) else None
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "newsletter_digest.py"),
                             "--check", "--json"], cwd=ROOT, capture_output=True,
                            text=True)
        import json
        self.assertIn(rc.returncode, (0, 1),
                      "unerwarteter Fehlerlauf (2 = Absturz): " + rc.stdout + rc.stderr)
        dat = json.loads(rc.stdout)
        self.assertIn(dat["zustand"], ("inert", "aktiv", "kaputt"))
        # Der Zustand muss zu hugo.toml passen – sonst prüft die Wache an allem vorbei
        aktiv = bool(dat["params"].get("newsletterFormAction")
                     or dat["params"].get("newsletterFormUrl"))
        self.assertEqual(aktiv, dat["zustand"] in ("aktiv", "kaputt"))
        for rel, st in vorher.items():
            p = os.path.join(ROOT, rel)
            now = os.path.getmtime(p) if os.path.isfile(p) else None
            self.assertEqual(st, now, f"{rel} wurde beim Prüfen verändert")


class Verdrahtung(unittest.TestCase):
    def test_wache_ist_registriert_und_laeuft(self):
        self.assertIn("newsletter_digest.py", gc.GUARDS)
        wf = open(os.path.join(ROOT, ".github/workflows/newsletter-daily.yml"),
                  encoding="utf-8").read()
        for marke in ("newsletter_digest.py --selftest", "--check --strict-inert",
                      "BREVO_API_KEY", "BREVO_LIST_ID", "git add data/newsletter_state.json"):
            self.assertIn(marke, wf, f"Workflow enthält nicht: {marke}")
        # Kein Weg, ohne Absender zu senden – und kein roter Lauf ohne ihn
        self.assertIn("ARGS=\"${ARGS/--send/}\"", wf)
        lc = open(os.path.join(ROOT, ".github/workflows/link-check.yml"),
                  encoding="utf-8").read()
        self.assertIn("newsletter_digest", lc)

    def test_landingsseite_ist_gebaut_und_ohne_falsches_versprechen(self):
        seite = os.path.join(ROOT, "public/newsletter/index.html")
        if not os.path.isdir(os.path.join(ROOT, "public")):
            self.skipTest("kein public/-Build (lokal zuerst `hugo` laufen lassen)")
        with open(seite, encoding="utf-8") as fh:
            h = fh.read()
        self.assertIn("nicht geschaltet", h)          # Leerzustand ist ehrlich
        self.assertNotIn("<form", h)                  # und postet nirgends hin
        self.assertIn("noindex", h)                   # wirbt nicht in Suchmaschinen
        self.assertNotIn("/datenschutz/#newsletter", h)  # es gibt keinen solchen Anker
        with open(os.path.join(ROOT, "public/sitemap.xml"), encoding="utf-8") as fh:
            self.assertNotIn("/newsletter/", fh.read())

    def test_selbsttest_der_wache(self):
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS, "newsletter_digest.py"),
                             "--selftest"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)

    def test_footer_cta_traegt_beide_anmeldewege(self):
        """Die Anleitung verspricht: „Sobald eines der beiden Felder gefüllt
        ist: Footer-CTA auf allen Inhaltsseiten" – das Template muss also auf
        newsletterFormAction UND newsletterFormUrl reagieren, sonst bleibt
        das reine Inline-Formular bei N6/cta-versteckt liegen."""
        t = open(os.path.join(ROOT, "layouts", "_partials", "extend_footer.html"),
                 encoding="utf-8").read()
        self.assertIn("newsletterFormUrl", t)
        self.assertIn("newsletterFormAction", t,
                      "Footer-CTA reagiert nur auf newsletterFormUrl – "
                      "reines Inline-Formular (Action ohne URL) wird "
                      "unsichtbar")

    def test_anleitung_verspricht_keinen_erfundenen_workflow(self):
        doku = open(os.path.join(ROOT, "docs/ANLEITUNG-NEWSLETTER.md"), encoding="utf-8").read()
        for geist in ("Newsletter-AI", "NEWSLETTER-STATUS.md"):
            self.assertNotIn(geist, doku, f"{geist} existiert nicht und darf nicht "
                                          "als Weg angegeben werden")
        self.assertIn("newsletter-daily.yml", doku)
        self.assertIn("NEWSLETTER-RECHTSTEXT-VORLAGE.md", doku)


if __name__ == "__main__":
    unittest.main(verbosity=2)
