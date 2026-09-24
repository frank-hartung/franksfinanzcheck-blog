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

import contextlib
import datetime
import importlib.util
import io
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
sr = _load("selftest_runner", os.path.join(SCRIPTS, "selftest_runner.py"))


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
                 datenschutz=ds, footer='<div class="newsletter-footer">anmelden</div>',
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

    def test_css_nennung_ist_kein_cta_und_keine_werbung(self):
        """Der Streifen heißt `.newsletter-footer`, und die Extended-CSS wird inline in
        jede Seite eingebettet – ein Selektor ist kein Kasten. Sonst meldet N1 einen
        Fund, wo nichts beworben wird, und N6 wäre wegen derselben Zeile grün."""
        b = Baum(self.tmp.name, "css-fall",
                 toml='newsletterFormAction = "https://l.brevo.com/x"\n',
                 datenschutz='<h2 id="newsletter">Newsletter</h2><p>Double-Opt-In.</p>',
                 footer="<style>.newsletter-footer.ff-nl-strip{margin:0}</style>",
                 workflow="BREVO_API_KEY\n--strict-inert\n")
        with open(os.path.join(b.root, "public/newsletter/index.html"), "w",
                  encoding="utf-8") as fh:
            fh.write('<div>Double-Opt-In <a href="/datenschutz/">DS</a>'
                     '<form><input name="email"></form></div>')
        funde, _, _ = nd.pruefe_capture(b.root)
        self.assertIn("cta-versteckt", {c for _, _, c in funde}, funde)

    def test_anmeldeseite_erklaren_ist_keine_werbung(self):
        b = Baum(self.tmp.name, "erklaerung", datenschutz="<h2>Newsletter</h2>")
        with open(os.path.join(b.root, "public/newsletter/index.html"), "w",
                  encoding="utf-8") as fh:
            fh.write("<div>Newsletter-Anmeldung ist noch nicht geschaltet.</div>")
        funde, _, zustand = nd.pruefe_capture(b.root)
        self.assertEqual("inert", zustand)
        self.assertEqual([], [f for f in funde if f[2] == "config-widerspruch"], funde)

    def test_gesunde_kette_findet_nichts(self):
        b = Baum(self.tmp.name, toml='newsletterFormAction = "https://l.brevo.com/x"\n',
                 datenschutz='<h2 id="newsletter">Newsletter</h2>'
                             '<p>Double-Opt-In, Widerruf formlos, 30 Tage.</p>',
                 footer='<div class="newsletter-footer">anmelden</div>', workflow="BREVO_API_KEY\n--strict-inert\n")
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
        from unittest.mock import patch
        for target in ("kadenz_pruefen", "termin_reservieren"):
            mock = patch.object(nd, target, return_value="")
            mock.start()
            self.addCleanup(mock.stop)
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
        echt_get = nd.TRANSPORT_GET

        def spy_get(api_key, pfad):
            if pfad == "senders":
                return 200, '{"senders": [{"email": "news@franksfinanzcheck.de", "active": true}]}'
            return 200, '{"id": 7, "totalSubscribers": 3}'
        try:
            nd.TRANSPORT = lambda *a, **k: aufgerufen.append(a) or (201, '{"id": 9}')
            nd.TRANSPORT_GET = spy_get
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
            nd.TRANSPORT_GET = echt_get
            for var in ("BREVO_API_KEY", "BREVO_LIST_ID", "NEWSLETTER_SEND"):
                os.environ.pop(var, None)
            shutil.rmtree(root, ignore_errors=True)

    def test_versand_payload_spricht_brevos_schema(self):
        """Lauf #14 (23.09.2026) scheiterte am ersten echten Netz-Call: Der
        Payload nannte das Feld `preheader`, das in CreateEmailCampaign nicht
        existiert (offiziell: `previewText`), und der Absender war hart codiert.
        Dieser Test hält den Schema-Vertrag fest."""
        aufgerufen = []
        echt = nd.TRANSPORT
        echt_get = nd.TRANSPORT_GET

        def spy(api_key, pfad, payload):
            aufgerufen.append(payload)
            return 201, '{"id": 5}'

        def spy_get(api_key, pfad):
            if pfad == "senders":
                return 200, '{"senders": [{"email": "ssot@franksfinanzcheck.de", "active": true}]}'
            return 200, '{"id": 7, "totalSubscribers": 2}'
        try:
            nd.TRANSPORT = spy
            nd.TRANSPORT_GET = spy_get
            root = tempfile.mkdtemp()
            os.makedirs(os.path.join(root, "data"), exist_ok=True)
            with open(os.path.join(root, "data", "newsletter_studio.json"), "w",
                      encoding="utf-8") as fh:
                fh.write('{"email": {"absender": {"name": "Frank SSOT",'
                         ' "email": "ssot@franksfinanzcheck.de"},'
                         ' "antwort_an": "reply@franksfinanzcheck.de"}}')
            os.environ["BREVO_API_KEY"] = "key"
            os.environ["BREVO_LIST_ID"] = "7"
            os.environ["NEWSLETTER_SEND"] = "ja"
            os.environ.pop("NEWSLETTER_ABSENDER", None)
            self.assertEqual(0, nd.versende(root, "<p>x</p>", "x", "Betreff",
                                           dry_run=False, preheader="Vorschau"))
            payload = aufgerufen[0]
            self.assertIn("previewText", payload)
            self.assertNotIn("preheader", payload)
            self.assertNotIn("textContent", payload)
            self.assertNotIn("status", payload)
            self.assertEqual("Vorschau", payload["previewText"])
            self.assertEqual(("Frank SSOT", "ssot@franksfinanzcheck.de"),
                             (payload["sender"]["name"], payload["sender"]["email"]))
            # CreateEmailCampaign: replyTo ist ein String, kein Transaktions-Objekt.
            # Lauf 35904226864 starb an genau diesem Objekt (HTTP 400).
            self.assertIsInstance(payload["replyTo"], str)
            self.assertEqual("reply@franksfinanzcheck.de", payload["replyTo"])
            self.assertEqual([], nd.kampagnen_schema_verstoesse(payload))
            self.assertIsNone(aufgerufen[1], "sendNow trägt im Schema keinen Body")
            historisch = dict(payload, replyTo={"email": payload["replyTo"]},
                              textContent="x", status="draft", preheader="x")
            self.assertTrue(any("replyTo" in v for v in nd.kampagnen_schema_verstoesse(historisch)))
        finally:
            nd.TRANSPORT = echt
            nd.TRANSPORT_GET = echt_get
            for var in ("BREVO_API_KEY", "BREVO_LIST_ID", "NEWSLETTER_ABSENDER",
                        "NEWSLETTER_SEND"):
                os.environ.pop(var, None)
            shutil.rmtree(root, ignore_errors=True)

    def test_replyto_absage_faellt_zurueck_test_und_live_teilen_die_kampagne(self):
        """Lauf 35904226864: Objekt-replyTo stirbt vor sendTest und vor sendNow.

        Nach der Heilung ist replyTo ein String. Lehnt Brevo die konfigurierte
        Antwortadresse trotzdem ab, gibt es genau einen zweiten Anlauf mit dem
        verifizierten Absender – die Kampagne war beim 400 noch nicht angelegt.
        Ein anderer 400 wird nicht wiederholt. Eine kaputte Testadresse legt
        nichts an und fällt nicht auf den Listenversand zurück.
        """
        aufgerufen = []
        echt = nd.TRANSPORT
        echt_get = nd.TRANSPORT_GET

        def post(api_key, pfad, payload):
            aufgerufen.append((pfad, payload))
            if (pfad == "emailCampaigns" and isinstance(payload, dict)
                    and payload.get("replyTo") == "reply@franksfinanzcheck.de"):
                return 400, ('{"code":"invalid_parameter",'
                             '"message":"ReplyTo email should be valid"}')
            if pfad == "emailCampaigns":
                return 201, '{"id": 9}'
            return 204, ""

        def get(api_key, pfad):
            if pfad == "senders":
                return 200, ('{"senders": [{"email": "ssot@franksfinanzcheck.de",'
                             ' "active": true}]}')
            return 200, '{"id": 7, "totalSubscribers": 2}'

        try:
            nd.TRANSPORT = post
            nd.TRANSPORT_GET = get
            root = tempfile.mkdtemp()
            os.makedirs(os.path.join(root, "data"), exist_ok=True)
            with open(os.path.join(root, "data", "newsletter_studio.json"), "w",
                      encoding="utf-8") as fh:
                fh.write('{"email": {"absender": {"name": "Frank SSOT",'
                         ' "email": "ssot@franksfinanzcheck.de"},'
                         ' "antwort_an": "reply@franksfinanzcheck.de"}}')
            os.environ["BREVO_API_KEY"] = "key"
            os.environ["BREVO_LIST_ID"] = "7"
            os.environ["NEWSLETTER_SEND"] = ""
            self.assertEqual(0, nd.versende(root, "<p>x</p>", "x", "Betreff",
                                            dry_run=False,
                                            test_adresse="Frank <Probe@Beispiel.de>, probe@beispiel.de"))
            kampagnen = [p for pfad, p in aufgerufen if pfad == "emailCampaigns"]
            self.assertEqual(2, len(kampagnen))
            self.assertEqual("reply@franksfinanzcheck.de", kampagnen[0]["replyTo"])
            self.assertEqual("ssot@franksfinanzcheck.de", kampagnen[1]["replyTo"])
            self.assertEqual([{"emailTo": ["probe@beispiel.de"]}],
                             [p for pfad, p in aufgerufen if str(pfad).endswith("/sendTest")])
            self.assertFalse(any(str(pfad).endswith("/sendNow") for pfad, _ in aufgerufen))

            aufgerufen.clear()
            nd.TRANSPORT = lambda *a: aufgerufen.append(a[1]) or (400, '{"message":"htmlContent is too short"}')
            self.assertEqual(1, nd.versende(root, "<p>x</p>", "x", "Betreff",
                                            dry_run=False, test_adresse="probe@beispiel.de"))
            self.assertEqual(["emailCampaigns"], aufgerufen)

            aufgerufen.clear()
            self.assertEqual(1, nd.versende(root, "<p>x</p>", "x", "Betreff",
                                            dry_run=False, test_adresse="keine-adresse"))
            self.assertEqual([], aufgerufen, "ungültige Testadresse darf nicht live senden")
        finally:
            nd.TRANSPORT = echt
            nd.TRANSPORT_GET = echt_get
            for var in ("BREVO_API_KEY", "BREVO_LIST_ID", "NEWSLETTER_SEND"):
                os.environ.pop(var, None)
            shutil.rmtree(root, ignore_errors=True)

    def test_vorflug_verriegelt_bevor_kampagne_entsteht(self):
        """Absender fehlt / nicht verifiziert / Liste leer: der Versand bricht
        ab, BEVOR bei Brevo etwas angelegt wird – mit lautsprachlichem Befund,
        nicht erst mit der Fehlermeldung des Anbieters (Lauf #14)."""
        aufgerufen = []
        echt = nd.TRANSPORT
        echt_get = nd.TRANSPORT_GET
        try:
            nd.TRANSPORT = lambda *a, **k: aufgerufen.append(a) or (201, '{"id": 1}')
            root = tempfile.mkdtemp()
            os.makedirs(os.path.join(root, "data"), exist_ok=True)
            os.environ["BREVO_API_KEY"] = "key"
            os.environ["BREVO_LIST_ID"] = "7"
            os.environ["NEWSLETTER_SEND"] = "ja"

            nd.TRANSPORT_GET = lambda a, p: (
                (200, '{"senders": [{"email": "news@franksfinanzcheck.de", "active": false}]}')
                if p == "senders" else (200, '{"totalSubscribers": 5}'))
            self.assertEqual(1, nd.versende(root, "<p>x</p>", "x", "B", dry_run=False),
                             "unverifizierter Absender ging durch")
            self.assertEqual([], aufgerufen, "trotz Befund wurde eine Kampagne angelegt")

            nd.TRANSPORT_GET = lambda a, p: (
                (200, '{"senders": []}') if p == "senders"
                else (200, '{"totalSubscribers": 5}'))
            self.assertEqual(1, nd.versende(root, "<p>x</p>", "x", "B", dry_run=False),
                             "fehlender Absender ging durch")

            nd.TRANSPORT_GET = lambda a, p: (
                (200, '{"senders": [{"email": "news@franksfinanzcheck.de", "active": true}]}')
                if p == "senders" else (200, '{"totalSubscribers": 0}'))
            self.assertEqual(1, nd.versende(root, "<p>x</p>", "x", "B", dry_run=False),
                             "leere Liste ging bei live durch")
            # Der Testversand ist von der leeren Liste bewusst NICHT betroffen:
            # er braucht zwar eine Kampagne (sendTest), trifft aber nie die Liste.
            os.environ["NEWSLETTER_SEND"] = ""
            self.assertEqual(0, nd.versende(root, "<p>x</p>", "x", "B", dry_run=False,
                                            test_adresse="probe@beispiel.de"))
            self.assertEqual(2, len(aufgerufen),
                             "Testversand: Kampagne anlegen + sendTest erwartet")
        finally:
            nd.TRANSPORT = echt
            nd.TRANSPORT_GET = echt_get
            for var in ("BREVO_API_KEY", "BREVO_LIST_ID", "NEWSLETTER_SEND"):
                os.environ.pop(var, None)
            shutil.rmtree(root, ignore_errors=True)

    def test_lesen_wird_wiederholt_schreiben_niemals(self):
        """Der Kernsatz der Versand-Härtung (23.09.2026, Lauf #21-Audit).

        LESANFRAGEN: 429/5xx/Netz bis zu dreimal – eine Störung ist eine Störung.
        SCHREIBANFRAGEN: genau einmal. Ein `POST …/sendNow`, das der Anbieter
        annahm und dessen Antwort verloren ging, ist keine unterbliebene Handlung,
        sondern eine ausgeführte. Sie zu wiederholen, schickt dieselbe Ausgabe
        zweimal an die ganze Liste – der Schaden, den der Duplikatsschutz
        (Q15, `versandene_artikel`) mit allem Aufwand verhindert. Ein 400 ist
        ohnehin ein Befund, keine Störung.
        """
        aufgerufen = []
        echt = nd.TRANSPORT
        echt_get = nd.TRANSPORT_GET
        http_echt = nd._http_request
        alte_pause = nd.PAUSE_SEKUNDEN
        try:
            nd.PAUSE_SEKUNDEN = (0.0, 0.0)

            def flaky(api_key, pfad, payload, methode):
                aufgerufen.append(pfad)
                if methode == "GET":
                    return 502, "Bad Gateway"
                return 201, '{"id": 3}'
            nd._http_request = flaky
            nd.TRANSPORT = nd.brevo
            nd.TRANSPORT_GET = nd.brevo_get
            root = tempfile.mkdtemp()
            os.makedirs(os.path.join(root, "data"), exist_ok=True)
            os.environ["BREVO_API_KEY"] = "key"
            os.environ["BREVO_LIST_ID"] = "7"
            os.environ["NEWSLETTER_SEND"] = ""      # Testversand, ohne Listen-Freigabe
            rc = nd.versende(root, "<p>x</p>", "x", "B", dry_run=False,
                             test_adresse="probe@beispiel.de")
            self.assertEqual(1, rc, "Vorflug-Netzstörung ließ den Versand trotzdem laufen")
            self.assertEqual(3, aufgerufen.count("senders"),
                             "LESANfrage bei 502 nicht dreimal probiert")
            self.assertEqual(0, aufgerufen.count("emailCampaigns"),
                             "trotz ungeprüfter Vorprüfung wurde geschrieben")

            aufgerufen.clear()
            os.environ["NEWSLETTER_SEND"] = "ja"

            def hart(api_key, pfad, payload, methode):
                aufgerufen.append(pfad)
                return (200, '{"senders": [{"email": "news@franksfinanzcheck.de",'
                             ' "active": true}]}') if methode == "GET" and pfad == "senders" \
                    else (200, '{"totalSubscribers": 4}') if methode == "GET" \
                    else (400, '{"code": "invalid_parameter", "message": "nope"}')
            nd._http_request = hart
            self.assertEqual(1, nd.versende(root, "<p>x</p>", "x", "B", dry_run=False))
            self.assertEqual(1, aufgerufen.count("emailCampaigns"),
                             "400 wurde wiederholt statt gemeldet")
        finally:
            nd._http_request = http_echt
            nd.TRANSPORT = echt
            nd.TRANSPORT_GET = echt_get
            nd.PAUSE_SEKUNDEN = alte_pause
            for var in ("BREVO_API_KEY", "BREVO_LIST_ID", "NEWSLETTER_SEND"):
                os.environ.pop(var, None)
            shutil.rmtree(root, ignore_errors=True)

    def test_client_kennung_und_kanten_blockage(self):
        """Lauf #21 (23.09.2026): „Absender-Vorprüfung nicht möglich (HTTP 403:
        … Error 1010: Access denied …)". Das war Brevos Kante, nicht Brevos
        Konto – urllib sandte die Standardkennung der Bibliothek. Drei Zusagen:

          1. Der Client nennt sich selbst (Projekt + URL), nie `Python-urllib`.
          2. Eine Signaturblockage wird als Kanten-Befund ausgesprochen, nicht
             als Absender-Befund – und mit zweiter, weiterhin ehrlicher Kennung
             versucht (kein Browser-Imitat).
          3. `BREVO_API_HOST` auf einer fremden Domain löst KEINEN Netzversuch
             aus, denn der api-key reiste dorthin mit.
        """
        self.assertTrue(nd.IDENTITÄTEN, "keine Client-Kennung definiert")
        for kennung in nd.IDENTITÄTEN:
            self.assertNotIn("Python-urllib", kennung)
            self.assertTrue(kennung.startswith("franksfinanzcheck")
                            or kennung.startswith("Mozilla/5.0 (compatible;"),
                            f"Kennung ist keine Selbstauskunft: {kennung}")
        self.assertGreaterEqual(len(set(nd.IDENTITÄTEN)), 2,
                                "zweite Kennung für den Reservefall fehlt")
        block = ('{"title":"Error 1010: Access denied","status":403,"detail":"The '
                 'site owner has blocked access based on your browser\'s signature."}')
        self.assertTrue(nd.kanten_block(403, block), "1010-Blockage nicht erkannt")
        self.assertFalse(nd.kanten_block(403, '{"code":"invalid_api_key",'
                                             '"message":"bad key"}'),
                         "Brevos echte Absage als Kanten-Block fehlgedeutet")
        for text in (nd.brevo_fehler(403, block),):
            self.assertIn("Kante blockiert", text)
            self.assertNotIn("existiert im Brevo-Konto nicht", text)
        # Host-Guard: unbekannte Domain → Befund, keine Anfrage
        vorher = os.environ.get("BREVO_API_HOST", "")
        try:
            os.environ["BREVO_API_HOST"] = "key-faenger.example"
            self.assertIn("kein freigegebener Brevo-Host", nd.api_host_fehler())
            os.environ["BREVO_API_HOST"] = "api.brevo.com"
            self.assertEqual("", nd.api_host_fehler())
        finally:
            if vorher:
                os.environ["BREVO_API_HOST"] = vorher
            else:
                os.environ.pop("BREVO_API_HOST", None)

    def test_unklarer_sendeausgang_wird_nachgelesen_nicht_wiederholt(self):
        """Geht die Antwort auf `sendNow` verloren, wird die Kampagnen-Akte
        gelesen – nie erneut gesendet. Belegt sie die Sendung, heißt der Befund
        „VERSAND ERFOLGT“ (und der Duplikatsschutz schreibt); ist sie unklar,
        hält eine Sperre den nächsten LISTEN-Versand an (der Testversand bleibt
        möglich, weil er genau eine Adresse trifft)."""
        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "data"), exist_ok=True)
        nd.speichere_state(root, {"pending": ["2026-09-20-a"]})
        echt, echt_get, http_echt = nd.TRANSPORT, nd.TRANSPORT_GET, nd._http_request
        pfade: list = []
        try:
            os.environ["BREVO_API_KEY"] = "key"
            os.environ["BREVO_LIST_ID"] = "7"
            os.environ["NEWSLETTER_SEND"] = "ja"

            def antwortende_api(api_key, pfad, payload, methode):
                pfade.append((methode, pfad))
                if methode == "GET" and pfad == "senders":
                    return 200, ('{"senders": [{"email": "news@franksfinanzcheck.de",'
                                 ' "active": true}]}')
                if methode == "GET" and pfad.startswith("contacts/lists/"):
                    return 200, '{"totalSubscribers": 4}'
                if methode == "GET" and pfad.startswith("emailCampaigns/"):
                    return 200, '{"status": "in_process", "statistics": {"deliveredCount": 4}}'
                if pfad == "emailCampaigns":
                    return 201, '{"id": 55}'
                return 502, "Bad Gateway"          # Antwort auf sendNow verloren
            nd._http_request = antwortende_api
            nd.TRANSPORT = nd.brevo
            nd.TRANSPORT_GET = nd.brevo_get
            with contextlib.redirect_stdout(io.StringIO()) as puffer:
                rc = nd.versende(root, "<p>x</p>", "text", "Betreff", dry_run=False)
            self.assertEqual(1, rc, "belegter Versand nach verlorener Antwort nicht gemeldet")
            self.assertIn("VERSAND ERFOLGT", puffer.getvalue())
            self.assertEqual(1, sum(1 for m, p in pfade if p.endswith("/sendNow")),
                             "sendNow wurde wiederholt – Doppelzustellung!")
            self.assertEqual(["2026-09-20-a"],
                             nd.lade_state(root).get("versandene_artikel"),
                             "belegter Versand nicht im Duplikatsschutz")

            # jetzt dieselbe Lage OHNE Beleg in der Akte → Sperre
            os.environ.pop("NEWSLETTER_SEND", None)
            os.environ["NEWSLETTER_SEND"] = "ja"
            nd.speichere_state(root, {"pending": ["2026-09-20-b"]})
            pfade.clear()

            def ungeklärte_api(api_key, pfad, payload, methode):
                pfade.append((methode, pfad))
                if methode == "GET" and pfad == "senders":
                    return 200, ('{"senders": [{"email": "news@franksfinanzcheck.de",'
                                 ' "active": true}]}')
                if methode == "GET" and pfad.startswith("contacts/lists/"):
                    return 200, '{"totalSubscribers": 4}'
                if methode == "GET":
                    # Die Akte kennt einen Status, den weder „raus“ noch „nicht
                    # raus“ belegt – genau der Fall, der einen Menschen braucht.
                    return 200, '{"id": 56, "status": "in_aenderung"}'
                if pfad == "emailCampaigns":
                    return 201, '{"id": 56}'
                if pfad.endswith("/sendTest"):
                    return 201, "{}"
                return 0, "URLError: timed out"
            nd._http_request = ungeklärte_api
            with contextlib.redirect_stdout(io.StringIO()):
                rc2 = nd.versende(root, "<p>x</p>", "text", "Betreff 2", dry_run=False)
            state = nd.lade_state(root)
            self.assertEqual(1, rc2)
            self.assertEqual(56, state.get("versand_unklar", {}).get("kampagne_id"),
                             f"unklarer Ausgang ohne Sperre: {state}")
            pfade.clear()
            rc3 = nd.versende(root, "<p>x</p>", "text", "Betreff 3", dry_run=False)
            self.assertEqual(1, rc3, "Sperre ließ den nächsten Listen-Versand zu")
            self.assertFalse([p for m, p in pfade if p == "emailCampaigns"],
                             "trotz Sperre eine Kampagne angelegt")
            rc4 = nd.versende(root, "<p>x</p>", "text", "Betreff 4", dry_run=False,
                              test_adresse="probe@beispiel.de")
            self.assertEqual(0, rc4, "Sperre blockiert zu Unrecht den Testversand")
        finally:
            nd.TRANSPORT, nd.TRANSPORT_GET, nd._http_request = echt, echt_get, http_echt
            for var in ("BREVO_API_KEY", "BREVO_LIST_ID", "NEWSLETTER_SEND",
                        "BREVO_API_HOST"):
                os.environ.pop(var, None)
            shutil.rmtree(root, ignore_errors=True)

    def test_testversand_mit_bestaetigung_blockiert_nicht_an_leerer_liste(self):
        """Verdrahtung (23.09.2026): der Testversand ist der vorgesehene Probe-
        lauf, BEVOR die Liste Abonnenten hat. Die Leere-Liste-Verriegelung gilt
        nur dem echten Listen-Versand – auch dann, wenn NEWSLETTER_SEND=ja
        gesetzt ist (z. B. Kadenz-Wache + Testadresse in einem Lauf)."""
        aufgerufen = []
        echt = nd.TRANSPORT
        echt_get = nd.TRANSPORT_GET
        try:
            nd.TRANSPORT = lambda *a, **k: aufgerufen.append(a) or (201, '{"id": 8}')

            def leer_liste_get(api_key, pfad):
                if pfad == "senders":
                    return 200, ('{"senders": [{"email": "news@franksfinanzcheck.de",'
                                 ' "active": true}]}')
                return 200, '{"id": 7, "totalSubscribers": 0}'
            nd.TRANSPORT_GET = leer_liste_get
            root = tempfile.mkdtemp()
            os.makedirs(os.path.join(root, "data"), exist_ok=True)
            os.environ["BREVO_API_KEY"] = "key"
            os.environ["BREVO_LIST_ID"] = "7"
            os.environ["NEWSLETTER_SEND"] = "ja"
            self.assertEqual(0, nd.versende(root, "<p>x</p>", "x", "B", dry_run=False,
                                            test_adresse="probe@beispiel.de"))
            pfade = [a[1] for a in aufgerufen]
            self.assertTrue(any(p.endswith("/sendTest") for p in pfade), pfade)
            self.assertFalse(any(p.endswith("/sendNow") for p in pfade), pfade)
        finally:
            nd.TRANSPORT = echt
            nd.TRANSPORT_GET = echt_get
            for var in ("BREVO_API_KEY", "BREVO_LIST_ID", "NEWSLETTER_SEND"):
                os.environ.pop(var, None)
            shutil.rmtree(root, ignore_errors=True)

    def test_status_schreibfehler_nach_versand_luegt_nicht(self):
        """Ist die Kampagne RAUS und scheitert erst das Status-Schreiben, bleibt
        der Lauf rot – aber der Befund trägt VERSAND ERFOLGT. Ein „es ist nichts
        versandt“ wäre eine Lüge, die der Empfänger widerlegen kann."""
        aufgerufen = []
        echt = nd.TRANSPORT
        echt_get = nd.TRANSPORT_GET
        speicher_echt = nd.speichere_state
        try:
            nd.TRANSPORT = lambda *a, **k: aufgerufen.append(a) or (201, '{"id": 11}')
            nd.TRANSPORT_GET = lambda a, p: (
                (200, '{"senders": [{"email": "news@franksfinanzcheck.de", "active": true}]}')
                if p == "senders" else (200, '{"totalSubscribers": 4}'))

            def kaputt(root, state):
                raise OSError("Permission denied (Test)")
            nd.speichere_state = kaputt
            root = tempfile.mkdtemp()
            os.makedirs(os.path.join(root, "data"), exist_ok=True)
            os.environ["BREVO_API_KEY"] = "key"
            os.environ["BREVO_LIST_ID"] = "7"
            os.environ["NEWSLETTER_SEND"] = "ja"
            puffer = io.StringIO()
            with contextlib.redirect_stdout(puffer):
                rc = nd.versende(root, "<p>x</p>", "x", "B", dry_run=False)
            self.assertEqual(1, rc, "Status-Fehler nach Versand darf nicht grün sein")
            self.assertTrue(any(a[1].endswith("/sendNow") for a in aufgerufen),
                            "der Versand soll in diesem Szenario erfolgt sein")
            self.assertIn("VERSAND ERFOLGT", puffer.getvalue())
        finally:
            nd.TRANSPORT = echt
            nd.TRANSPORT_GET = echt_get
            nd.speichere_state = speicher_echt
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
                      "BREVO_API_KEY", "BREVO_LIST_ID", "git add data/newsletter_state.json",
                      "TEST_ADRESSE_GESETZT"):
            self.assertIn(marke, wf, f"Workflow enthält nicht: {marke}")
        self.assertNotIn("TEST_ADRESE_GESETZT", wf,
                         "Tippfehler macht die Testversand-Ausnahme der Zustellbarkeits-Wache tot")
        # Kein Weg, ohne Absender zu senden – und kein roter Lauf ohne ihn
        self.assertIn("ARGS=\"${ARGS/--send/}\"", wf)
        # Qualitäts-Gate: `assertIn("newsletter_digest", link-check.yml)` war bis
        # zum 18.09.2026 der Verdrahtungs-Beweis – und fiel aus, als die
        # abgetippte Bash-Wachen-Liste durch scripts/selftest_runner.py ersetzt
        # wurde (Run 35312783057). Dieselbe Prüfung als Textsuche wäre außerdem
        # mit einem bloßen Kommentar zufrieden. Deshalb: Mechanismus prüfen.
        self.assertEqual([], sr.verdrahtet("newsletter_digest.py"),
                         "newsletter_digest läuft nicht im Qualitäts-Gate")

    def test_landingsseite_ist_gebaut_und_ohne_falsches_versprechen(self):
        """Was die Anmeldeseite im JEDES Zustand zu liefern hat – und was nur im Leeren.

        Der Test war bis hierher eine Zustands-Behauptung („kein <form>“), kein
        Invariante: am Tag, an dem Frank den Schalter legt, wäre er rot geworden –
        und zwar wegen des Erfolgs. Also wird der Konfigurationszustand erst
        gelesen und dann je Zweig geprüft; die gemeinsamen Sätze (noindex, kein
        Anker, keine Sitemap) gelten in beiden.
        """
        seite = os.path.join(ROOT, "public/newsletter/index.html")
        if not os.path.isdir(os.path.join(ROOT, "public")):
            self.skipTest("kein public/-Build (lokal zuerst `hugo` laufen lassen)")
        with open(seite, encoding="utf-8") as fh:
            h = fh.read()
        p = nd.params(ROOT)
        geschaltet = bool(p.get("newsletterFormAction") or p.get("newsletterFormUrl"))
        if geschaltet:
            # Das Contract-Ziel der Wache: ein Formular, das wirklich postet,
            # und eine Seite, die den Weg danach erklärt.
            self.assertIn("<form", h)
            # `hugo --minify` (der Build des Versand-Workflows) nimmt die
            # Anführungszeichen aus den Attributen: `name=email`. Die Prüfung
            # muss beide Formen kennen, sonst ist sie nur im unminifizierten
            # Build grün – nachgestellt am Basis-Commit 5eeb90a am 23.09.2026.
            self.assertRegex(h, r'name=["\']?email')
            self.assertRegex(h, r"Double-Opt|Bestätigungsmail")
            self.assertIn("/datenschutz/", h)
            self.assertNotIn("nicht geschaltet", h)
        else:
            self.assertIn("nicht geschaltet", h)      # Leerzustand ist ehrlich
            self.assertNotIn("<form", h)              # und postet nirgends hin
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

    def test_doku_und_vorflug_nennen_dieselbe_authentifizierungslehre(self):
        """SPF ist nicht der Hebel – weder in der Doku noch im Vorflug-Befund.

        Beide Texte schrieben, „SPF/DKIM auf verifiziert bringen“ bzw. das
        Brevo-Include im SPF sei der nächste Schritt. Gemessen am 23.09.2026
        trägt nur das Domain-DKIM (`brevo1`/`brevo2._domainkey`); auf Brevos
        geteiltem Weg alignt die eigene SPF-Zeile nie, und ein zweiter
        SPF-TXT-Eintrag hätte die ganze Domain auf `permerror` gesetzt. Ein
        Befund, der an der falschen Schicht arbeiten lässt, kostet einen Tag –
        und eine Doku-Anweisung, die in eine laufende Zone greifen lässt, mehr.
        Deshalb hängt diese Erwartung jetzt am Test, nicht am Goodwill.
        """
        quell = open(os.path.join(ROOT, "scripts/newsletter_digest.py"),
                     encoding="utf-8").read()
        self.assertNotIn("SPF/DKIM auf ", quell,
                         "der Vorflug-Befund schickt den Betreiber zum SPF")
        self.assertIn("ist hier nicht der Hebel", quell)
        anleitung = open(os.path.join(ROOT, "docs/ANLEITUNG-NEWSLETTER.md"),
                         encoding="utf-8").read()
        checkliste = open(os.path.join(ROOT, "docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md"),
                          encoding="utf-8").read()
        for text, name in ((anleitung, "ANLEITUNG-NEWSLETTER"),
                           (checkliste, "FREISCHALTUNG-NEWSLETTER-CHECKLISTE")):
            self.assertIn("korrigiert", text.lower(),
                          f"{name}: die falsche SPF-Anweisung steht weiter als Anweisung")
            self.assertIn("newsletter_zustellbarkeit.py", text,
                          f"{name}: die Wache, die das nachmisst, ist nicht verlinkt")
            self.assertIn("brevo1._domainkey", text,
                          f"{name}: DKIM wird weiter als TXT-Schlüssel beschrieben")


if __name__ == "__main__":
    unittest.main(verbosity=2)
