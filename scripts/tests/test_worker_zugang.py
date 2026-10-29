"""Vertrag der Deploy-Zugangsprüfung (WF-829B / #922, 29.10.2026).

Der Vorfall: Lauf `40569123622` ließ BEIDE Deploy-Jobs im Schritt
„Produktive Ressource auflösen“ nach 0 Sekunden rot werden – mit der
ehrlichen, aber zu knappen Annotation „CF_WORKERS_DEPLOY_TOKEN fehlt“.
Fail-closed war richtig. Falsch war, dass jedes fehlende Feld eine eigene
Environment-Freigabe kostete und dass der Zugang nur über einen Deploy
prüfbar war.

Diese Datei prüft, dass `scripts/worker_zugang.py` die drei Zusagen
einhält, die daraus entstanden sind:

  1. SAMMELN statt kurzschließen – alle Befunde eines Laufs in einer Liste.
  2. NIE einen Wert verraten – keine Token-, Konto- oder Ressourcen-ID in
     Log, JSON, Dossier oder Annotation.
  3. NICHTS VERÄNDERN – nur zwei feste GET-Endpunkte, kein Deploy.

Dazu die Verdrahtung: Prüfung VOR Auflösung VOR Deploy, eigener
Prüf-Workflow ohne Deploy, und der Meldeweg (Runbook-Klasse) für beide.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import worker_zugang as wz  # noqa: E402

TOKEN = "GIFT_TOKEN_NIEMALS_LOGGEN_0123456789"
KONTO = "a" * 32
KV = "b" * 32
D1 = "12345678-1234-1234-1234-123456789abc"
ENVIRONMENT = {
    "CF_WORKERS_DEPLOY_TOKEN": TOKEN,
    "CLOUDFLARE_ACCOUNT_ID": KONTO,
}


def gesunder_transport(url: str, _token: str):
    if url.endswith("/user/tokens/verify"):
        return 200, {"success": True, "result": {"status": "active"}}
    if "ff-newsletter" in url:
        return 200, {"success": True, "result": {"bindings": [
            {"type": "kv_namespace", "name": "ABO", "namespace_id": KV}]}}
    return 200, {"success": True, "result": {"bindings": [
        {"type": "d1", "name": "DB", "id": D1}]}}


def klasse(befunde, pruefung: str) -> str | None:
    return next((b.klasse for b in befunde if b.pruefung == pruefung), None)


class Kernvertrag(unittest.TestCase):
    def setUp(self):
        self.netz = Mock(side_effect=AssertionError("Netzaufruf ohne Not"))
        self.frueher = wz._hole

    def tearDown(self):
        wz._hole = self.frueher

    def test_selbsttest(self):
        self.assertEqual(wz._selftest(), 0)

    def test_gesunder_zugang_ist_gruen_und_deploybar(self):
        befunde = wz.pruefen(ENVIRONMENT, hole=gesunder_transport)
        self.assertTrue(all(b.gruen for b in befunde), [b.text for b in befunde])
        self.assertTrue(wz.urteil(befunde)[0])

    def test_922_alle_fehlenden_voraussetzungen_auf_einmal(self):
        """Der Kern von #922: kein Kurzschluss beim ersten fehlenden Feld."""
        befunde = wz.pruefen({}, hole=self.netz)
        gefunden = {b.pruefung: b.klasse for b in befunde}
        self.assertEqual(gefunden.get("CF_WORKERS_DEPLOY_TOKEN"), wz.FEHLT)
        self.assertEqual(gefunden.get("CLOUDFLARE_ACCOUNT_ID"), wz.FEHLT)
        # Beide Worker erscheinen als nicht prüfbar – nicht als „in Ordnung“.
        self.assertEqual(gefunden.get("newsletter-worker · Ressource"), wz.OFFEN)
        self.assertEqual(gefunden.get("klick-zaehler · Ressource"), wz.OFFEN)
        self.assertFalse(wz.urteil(befunde)[0])
        self.netz.assert_not_called()

    def test_offen_ist_kein_beleg(self):
        """`OFFEN` darf nie als grün durchgehen: es ist die Folge eines Befunds."""
        befunde = wz.pruefen({}, hole=gesunder_transport)
        self.assertTrue(any(b.klasse == wz.OFFEN for b in befunde))
        self.assertFalse(wz.urteil(befunde)[0])
        self.assertIn("OFFEN", wz.urteil(befunde)[1])

    def test_konto_id_format_ist_eigene_klasse(self):
        aufrufe: list[str] = []

        def nur_verify(url, token):
            aufrufe.append(url)
            return 200, {"success": True, "result": {"status": "active"}}

        befunde = wz.pruefen(dict(ENVIRONMENT, CLOUDFLARE_ACCOUNT_ID="nicht-hex"),
                             hole=nur_verify)
        self.assertEqual(klasse(befunde, "CLOUDFLARE_ACCOUNT_ID"), wz.FORMAT)
        # Ohne gültige Konto-ID wird kein Worker-Endpunkt geraten.
        self.assertEqual(aufrufe, [f"{wz.CF_API}/user/tokens/verify"])
        self.assertEqual(klasse(befunde, "newsletter-worker · Ressource"), wz.OFFEN)

    def test_token_format_und_zu_kurz(self):
        for wert in ("mit leerzeichen im wert", "kurz"):
            befunde = wz.pruefen(dict(ENVIRONMENT, CF_WORKERS_DEPLOY_TOKEN=wert),
                                 hole=self.netz)
            self.assertEqual(klasse(befunde, "CF_WORKERS_DEPLOY_TOKEN"), wz.FORMAT, wert)
            # Ohne gültigen Token wird nichts geprüft – und nichts geraten.
            self.netz.assert_not_called()


class Klassen(unittest.TestCase):
    """Jede Ursache hat ihre eigene Klasse – sonst ist der Rat geraten."""

    def _pruefen(self, transport, umgebung=None):
        return wz.pruefen(dict(umgebung or ENVIRONMENT), hole=transport)

    def test_http_401_ist_ungueltig(self):
        befunde = self._pruefen(lambda u, t: (401, None))
        self.assertEqual(klasse(befunde, "Token-Gültigkeit"), wz.UNGUELTIG)

    def test_http_403_ist_fehlendes_recht(self):
        def transport(url, _t):
            if url.endswith("/user/tokens/verify"):
                return 200, {"success": True, "result": {"status": "active"}}
            return 403, None
        befunde = self._pruefen(transport)
        self.assertEqual(klasse(befunde, "newsletter-worker · Ressource"), wz.RECHT)

    def test_http_404_ist_unbekannter_worker_ohne_ersatzspeicher(self):
        def transport(url, _t):
            if url.endswith("/user/tokens/verify"):
                return 200, {"success": True, "result": {"status": "active"}}
            return 404, None
        befunde = self._pruefen(transport)
        self.assertEqual(klasse(befunde, "newsletter-worker · Ressource"), wz.UNBEKANNT)
        self.assertIn("kein Ersatzspeicher", " ".join(b.text for b in befunde))

    def test_http_429_und_500_sind_netz_kein_zugangsfehler(self):
        for status in (429, 500, 503):
            befunde = self._pruefen(lambda u, t, s=status: (s, None))
            self.assertEqual(klasse(befunde, "Token-Gültigkeit"), wz.NETZ, status)
            self.assertFalse(any(b.klasse in (wz.UNGUELTIG, wz.RECHT) for b in befunde))

    def test_nicht_aktiver_token(self):
        befunde = self._pruefen(
            lambda u, t: (200, {"success": True, "result": {"status": "expired"}}))
        self.assertEqual(klasse(befunde, "Token-Gültigkeit"), wz.UNGUELTIG)
        self.assertIn("expired", " ".join(b.text for b in befunde))

    def test_netzstoerung_wird_netz_und_stuerzt_nicht_ab(self):
        def kaputt(url, _t):
            raise wz.Netzfehler("Timeout")
        befunde = self._pruefen(kaputt)
        self.assertEqual(klasse(befunde, "Token-Gültigkeit"), wz.NETZ)
        self.assertEqual(klasse(befunde, "newsletter-worker · Ressource"), wz.NETZ)

    def test_mehrdeutige_bindung_bleibt_gesperrt(self):
        def doppelt(url, _t):
            if url.endswith("/user/tokens/verify"):
                return 200, {"success": True, "result": {"status": "active"}}
            return 200, {"success": True, "result": {"bindings": [
                {"type": "kv_namespace", "name": "ABO", "namespace_id": "c" * 32},
                {"type": "kv_namespace", "name": "ABO", "namespace_id": "d" * 32}]}}
        befunde = self._pruefen(doppelt)
        self.assertEqual(klasse(befunde, "newsletter-worker · Ressource"), wz.BINDUNG)

    def test_falscher_bindungstyp_reicht_nicht(self):
        def falsch(url, _t):
            if url.endswith("/user/tokens/verify"):
                return 200, {"success": True, "result": {"status": "active"}}
            return 200, {"success": True, "result": {"bindings": [
                {"type": "plain_text", "name": "ABO", "namespace_id": KV}]}}
        befunde = self._pruefen(falsch)
        self.assertEqual(klasse(befunde, "newsletter-worker · Ressource"), wz.BINDUNG)


class Vorrang_der_Repository_Variable(unittest.TestCase):
    def test_gueltige_variable_ersetzt_das_lesen_der_bindung(self):
        aufrufe: list[str] = []

        def transport(url, token):
            aufrufe.append(url)
            return gesunder_transport(url, token)

        befunde = wz.pruefen(dict(ENVIRONMENT, KV_NAMESPACE_ID_ABO=KV), hole=transport)
        self.assertEqual(klasse(befunde, "newsletter-worker · Ressource"), wz.OK)
        self.assertFalse(any("ff-newsletter" in url for url in aufrufe),
                         "Die Bindung wurde gelesen, obwohl die Variable gilt")

    def test_ungueltige_variable_faellt_nicht_auf_raten_zurueck(self):
        aufrufe: list[str] = []

        def transport(url, token):
            aufrufe.append(url)
            return gesunder_transport(url, token)

        befunde = wz.pruefen(dict(ENVIRONMENT, D1_DATABASE_ID="nicht-gültig"), hole=transport)
        self.assertEqual(klasse(befunde, "klick-zaehler · Ressource"), wz.FORMAT)
        # Die ungültige Variable wird gemeldet, nicht durch eine andere
        # Ressource ersetzt: klick-zaehler wird gar nicht erst gelesen.
        self.assertFalse(any("klick-zaehler" in url for url in aufrufe), aufrufe)


class Keine_Werte_in_der_Ausgabe(unittest.TestCase):
    """Ein Befund ist eine Anweisung, kein Dump. Kein Wert verlässt den Lauf."""

    def _lauf(self, umgebung, transport, *, md=False, als_json=False):
        puffer = io.StringIO()
        md_datei = None
        if md:
            import tempfile
            pfad = Path(tempfile.mkdtemp()) / "dossier.md"
            md_datei = pfad
        with patch.object(wz.gk, "annotation", return_value=False), \
                contextlib.redirect_stdout(puffer):
            code = wz.ausgabe(wz.pruefen(umgebung, hole=transport), umgebung,
                              md_pfad=str(md_datei) if md_datei else None,
                              als_json=als_json)
        text = puffer.getvalue()
        if md_datei:
            text += md_datei.read_text(encoding="utf-8")
        return code, text

    def test_kein_wert_in_log_json_oder_dossier(self):
        for md, als_json in ((False, False), (False, True), (True, False)):
            code, text = self._lauf(dict(ENVIRONMENT, D1_DATABASE_ID=D1),
                                    gesunder_transport, md=md, als_json=als_json)
            self.assertEqual(code, 0)
            for wert in (TOKEN, KONTO, KV, D1):
                self.assertNotIn(wert, text, f"Wert {wert[:4]}… in der Ausgabe")

    def test_maskierung_greift_auch_bei_fremdtext(self):
        umgebung = dict(ENVIRONMENT)
        self.assertNotIn(TOKEN, wz._maskiere(f"Cloudflare sagt: {TOKEN}", umgebung))
        self.assertNotIn(KONTO, wz._maskiere(KONTO, umgebung))

    def test_json_ist_maschinenlesbar(self):
        with patch.object(wz.gk, "annotation", return_value=False), \
                contextlib.redirect_stdout(puffer := io.StringIO()):
            wz.ausgabe(wz.pruefen({}, hole=gesunder_transport), {}, md_pfad=None,
                       als_json=True)
        daten = json.loads(puffer.getvalue())
        self.assertFalse(daten["deploybar"])
        self.assertIsInstance(daten["befunde"], list)
        self.assertTrue(all({"pruefung", "klasse", "text", "massnahme"} <= set(b)
                            for b in daten["befunde"]))

    def test_eine_annotation_je_eigenstaendigem_befund(self):
        """`OFFEN` ist die Folge eines anderen Befunds – keine zweite Meldung."""
        meldungen: list[str] = []
        with patch.object(wz.gk, "annotation",
                          side_effect=lambda ebene, text, **_: meldungen.append(text)), \
                contextlib.redirect_stdout(io.StringIO()):
            wz.ausgabe(wz.pruefen({}, hole=gesunder_transport), {}, md_pfad=None,
                       als_json=False)
        self.assertEqual(len(meldungen), 2, meldungen)
        self.assertTrue(all("FEHLT" in m for m in meldungen))
        self.assertFalse(any("OFFEN" in m for m in meldungen))


class Dossier(unittest.TestCase):
    def setUp(self):
        self.bericht = wz.dossier(wz.pruefen({}, hole=gesunder_transport), {})

    def test_nennt_den_genauen_ablageort_und_die_rechte(self):
        self.assertIn("cloudflare-produktion", self.bericht)
        self.assertIn("Environment secrets", self.bericht)
        self.assertIn("Workers Scripts: Read", self.bericht)
        self.assertIn("Edit", self.bericht)

    def test_nennt_den_naechsten_schritt_und_die_grenze(self):
        self.assertIn("Cloudflare-Worker deployen", self.bericht)
        self.assertIn("Deploy-Zugang prüfen", self.bericht)
        self.assertIn("docs/SICHERHEIT-BETRIEB-RUNBOOK.md", self.bericht)
        self.assertIn("Grenzen dieser Prüfung", self.bericht)
        self.assertIn("kein", self.bericht.lower())

    def test_urteil_steht_oben_und_ist_nicht_beschoenigt(self):
        self.assertIn("❌", self.bericht.splitlines()[2])
        self.assertNotIn("Alle Voraussetzungen des Deploys sind belegt", self.bericht)

    def test_gesunder_zugang_ergibt_gruenes_dossier(self):
        bericht = wz.dossier(wz.pruefen(ENVIRONMENT, hole=gesunder_transport), ENVIRONMENT)
        self.assertIn("Alle Voraussetzungen des Deploys sind belegt", bericht)
        self.assertNotIn("## Was zu tun ist", bericht)


class TransportVertrag(unittest.TestCase):
    """Enge T6-Ausnahme: nur Cloudflare-Verwaltung, niemals Modellverkehr."""

    def setUp(self):
        self.quelltext = (ROOT / "scripts" / "worker_zugang.py").read_text(encoding="utf-8")

    def test_ausnahme_ist_im_gate_eingetragen(self):
        gate = (ROOT / "scripts" / "ki_transportweg.py").read_text(encoding="utf-8")
        self.assertIn('Path("scripts/worker_zugang.py")', gate)

    def test_nur_cloudflare_und_kein_modellaufruf(self):
        hosts = set(re.findall(r"https://([a-z0-9.-]+)", self.quelltext))
        self.assertEqual(hosts, {"api.cloudflare.com"})
        self.assertIn('CF_API = "https://api.' + 'cloudflare.com/client/v4"', self.quelltext)
        for erlaubt in ("/user/tokens/verify", "/workers/scripts/"):
            self.assertIn(erlaubt, self.quelltext)
        for verboten in ("/ai/run", "/ai/", "generativelanguage", "api.groq.com",
                         "nvidia", "pollinations", "llm_client", "/chat/completions",
                         "workers.ai"):
            self.assertNotIn(verboten, self.quelltext)

    def test_nur_feste_endpunktformen(self):
        """Beide Aufrufe sind aus Konstanten gebaut – kein Freitext-Endpunkt."""
        aufrufe: list[str] = []

        def sammeln(url, _t):
            aufrufe.append(url)
            return gesunder_transport(url, _t)

        wz.pruefen(dict(ENVIRONMENT, KV_NAMESPACE_ID_ABO=""), hole=sammeln)
        self.assertEqual(len(aufrufe), 3, aufrufe)
        self.assertEqual(aufrufe[0], f"{wz.CF_API}/user/tokens/verify")
        for url in aufrufe[1:]:
            self.assertRegex(url, r"^" + re.escape(wz.CF_API) +
                             r"/accounts/[0-9a-f]{32}/workers/scripts/(ff-newsletter|"
                             r"klick-zaehler)/settings$")
            self.assertNotIn("?", url)


class Grenzen(unittest.TestCase):
    def test_kein_fremder_endpunkt_erreicht_das_netz(self):
        with self.assertRaises(wz.Werkzeugfehler):
            wz._hole("https://example.invalid/steal", TOKEN)

    def test_keine_weiterleitung_mit_token(self):
        handler = wz._KeineWeiterleitung()
        with self.assertRaises(OSError):
            handler.redirect_request(None, None, 302, "Found", {}, "https://x")

    def test_unbekannter_worker_ist_kein_stillschweigen(self):
        with self.assertRaises(wz.Werkzeugfehler):
            wz.pruefen(ENVIRONMENT, hole=gesunder_transport, worker="ki-assistent")

    def test_nur_die_beiden_automatischen_worker(self):
        self.assertEqual(wz.AUTOMATISCHE_WORKER, ("newsletter-worker", "klick-zaehler"))

    def test_cli_pruefen_ist_fail_closed_ohne_umgebung(self):
        with patch.object(wz.gk, "annotation", return_value=False), \
                patch.dict(wz.os.environ, {}, clear=True), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(wz.main(["--pruefen"]), 1)

    def test_cli_ohne_schalter_zeigt_hilfe(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(wz.main([]), 0)

    def test_transport_ausnahme_wird_zu_netzfehler(self):
        with patch("urllib.request.OpenerDirector.open", side_effect=OSError("kaputt")):
            with self.assertRaises(wz.Netzfehler):
                wz._hole(f"{wz.CF_API}/user/tokens/verify", TOKEN)

    def test_http_fehlerantwort_wird_nicht_zum_dump(self):
        fehler = urllib.error.HTTPError(f"{wz.CF_API}/user/tokens/verify", 403,
                                        "Forbidden", {}, io.BytesIO(b'{"secret":"x"}'))
        with patch("urllib.request.OpenerDirector.open", side_effect=fehler):
            status, koerper = wz._hole(f"{wz.CF_API}/user/tokens/verify", TOKEN)
        self.assertEqual(status, 403)
        self.assertEqual(koerper, {"secret": "x"})
        # Der Körper wird nur für die Bindungs-Auswertung gelesen und niemals
        # in einen Befund übernommen.
        befunde = wz.pruefen(ENVIRONMENT,
                             hole=lambda u, t: (403, {"secret": "x"}))
        self.assertNotIn("secret", " ".join(b.text for b in befunde))


class Verdrahtung(unittest.TestCase):
    """Ein Befund ohne Meldeweg ist die nächste stille Lücke."""

    def setUp(self):
        self.deploy = (ROOT / ".github" / "workflows" / "worker-deploy.yml").read_text(encoding="utf-8")
        self.pruef = (ROOT / ".github" / "workflows" / "worker-zugang-pruefen.yml").read_text(encoding="utf-8")
        self.alert = (ROOT / ".github" / "workflows" / "alert-on-failure.yml").read_text(encoding="utf-8")

    def test_pruefung_laeuft_vor_aufloesung_und_deploy(self):
        pruefung = self.deploy.index("worker_zugang.py --pruefen")
        aufloesung = self.deploy.index("worker_ressourcen.py --aufloesen")
        deploy = self.deploy.index("wrangler deploy --config")
        self.assertLess(pruefung, aufloesung)
        self.assertLess(aufloesung, deploy)

    def test_pruefung_laeuft_im_geschuetzten_environment(self):
        deploy_job = self.deploy.split("  deploy:\n", 1)[1]
        self.assertIn("name: cloudflare-produktion", deploy_job)
        self.assertIn("secrets.CF_WORKERS_DEPLOY_TOKEN", deploy_job)
        self.assertIn('worker_zugang.py --pruefen --worker "$WORKER"', deploy_job)

    def test_eigener_pruefworkflow_deployt_nicht(self):
        self.assertIn("workflow_dispatch:", self.pruef)
        # Kommentare dürfen das Wort nennen – ausgeführt werden darf es nicht.
        self.assertNotIn("wrangler deploy", self.pruef.lower())
        self.assertNotIn("node_modules/.bin/wrangler", self.pruef)
        self.assertNotIn("worker_deploy_vorbereiten.py --vorbereiten", self.pruef)
        self.assertIn("name: cloudflare-produktion", self.pruef)
        self.assertIn("worker_zugang.py --pruefen", self.pruef)
        self.assertIn("GITHUB_STEP_SUMMARY", self.pruef)

    def test_pruefworkflow_ist_ueberwacht(self):
        import alert_issue_identity as ident
        self.assertIn("Deploy-Zugang prüfen", ident.wacht_liste())

    def test_beide_wege_tragen_den_zugangs_rat(self):
        # Beide Wege (Deploy-Vorprüfung und eigener Prüf-Workflow) landen in
        # derselben Runbook-Klasse; der Selbsttest behält seine eigene Klasse
        # und steht VOR dem Zugangs-Rat.
        zugang = self.alert.index("(workerZugangFailed || zugangsPruefungFailed)")
        catch_all = self.alert.index(": (isWorkerDeploy && !workerTestsFailed) ? 'worker-deploy'")
        selbsttest = self.alert.index(": selbsttestFailed ? 'selbsttest'")
        self.assertLess(zugang, catch_all)
        # Genau EIN Name pro Klasse – sonst bleibt der Rat in offenen Meldungen
        # stehen (Schaden aus WF-9E5A/#761).
        self.assertEqual(self.alert.count("? 'selbsttest'"), 1)
        self.assertLess(selbsttest, self.alert.index("const runbookMarker"))
        # Der Zugangs-Rat nennt den Prüfknopf und die Selbsttests.
        self.assertIn("„Deploy-Zugang prüfen“", self.alert)
        self.assertIn("worker_zugang.py --selftest", self.alert)

    def test_umgezogene_pruefung_behaelt_ihren_meldeweg(self):
        """#922: Der Befund entsteht jetzt VOR dem Resolver – der Rat muss folgen."""
        self.assertIn("String(s).includes('Zugang prüfen (alle Befunde'", self.alert)

    def test_deploy_kette_ist_in_der_sicherheitswache_verdrahtet(self):
        wache = (ROOT / ".github" / "workflows" / "sicherheits-wache.yml").read_text(encoding="utf-8")
        self.assertIn('"scripts/worker_zugang.py"', wache)
        self.assertIn("scripts.tests.test_worker_zugang", wache)
        self.assertIn("scripts/worker_zugang.py --selftest", wache)

    def test_paketskript_prueft_den_vertrag(self):
        paket = (ROOT / "package.json").read_text(encoding="utf-8")
        self.assertIn("scripts/worker_zugang.py --selftest", paket)
        self.assertIn("scripts.tests.test_worker_zugang", paket)


if __name__ == "__main__":
    unittest.main()
