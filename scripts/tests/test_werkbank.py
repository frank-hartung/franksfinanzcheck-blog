#!/usr/bin/env python3
"""Regressionen für die Werkbank (Antwortwerk, Crawl4AI, Playwright, Composio).

Der Test prüft vier Ebenen:
  1. Die echte SSOT und der echte Baum sind grün.
  2. Jede Vertragsregel bricht, wenn man sie sabotiert – sonst wäre das
     Gate ein grüner Haken ohne Aussage.
  3. Die Belegdisziplin hält auch gegen trickreiche URLs (Subdomains,
     Tarnhosts, Groß-/Kleinschreibung).
  4. Kein Pfad, der „verfügbar?" beantwortet, fasst das Netz an –
     sonst wäre weder der Selbsttest offline noch die CI reproduzierbar.

Rollout 03.10.2026, siehe docs/ANLEITUNG-WERKBANK.md
"""
from __future__ import annotations

import copy
import json
import os
import sys
import unittest
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import antwortwerk as aw  # noqa: E402
import werkbank_adapters as wa  # noqa: E402
import werkbank_gate as gate  # noqa: E402


def lade() -> dict:
    return yaml.safe_load((ROOT / "data" / "werkbank.yaml").read_text(encoding="utf-8"))


class SsotTests(unittest.TestCase):
    """Die Quelle der Wahrheit trägt, was der Auftrag verlangt."""

    def setUp(self):
        self.ssot = lade()

    def test_vier_gewerke_mit_eindeutigen_ids(self):
        ids = [g["id"] for g in self.ssot["gewerke"]]
        self.assertEqual(sorted(ids),
                         ["antwortwerk", "browser", "konnektor", "leser"])
        self.assertEqual(len(ids), len(set(ids)), "doppelte Gewerk-id")

    def test_jedes_gewerk_hat_zweck_und_zustandsregel(self):
        for g in self.ssot["gewerke"]:
            self.assertTrue(g.get("zweck", "").strip(), f"{g['id']} ohne Zweck")
            self.assertIn("pflicht", g, f"{g['id']} ohne Pflichtangabe")
            self.assertIn("schreibend", g, f"{g['id']} ohne Schreibrecht-Angabe")

    def test_kein_anbieter_kostet_geld(self):
        """Der Kern des Auftrags: kostenlos, nicht 'günstig'."""
        for a in self.ssot["antwortwerk"]["suche"]:
            self.assertFalse(a.get("kostenpflichtig"), f"{a['id']} kostet Geld")
        for s in self.ssot["antwortwerk"]["synthese"]:
            self.assertFalse(s.get("kostenpflichtig"), f"{s['id']} kostet Geld")

    def test_genau_ein_schluesselfreier_standardweg(self):
        standard = [s for s in self.ssot["antwortwerk"]["synthese"] if s.get("standard")]
        self.assertEqual(len(standard), 1)
        self.assertFalse(standard[0]["schluessel_noetig"])
        self.assertEqual(standard[0]["id"], "extraktiv")

    def test_ssot_nennt_nur_env_namen_keine_werte(self):
        roh = (ROOT / "data" / "werkbank.yaml").read_text(encoding="utf-8")
        self.assertEqual(gate.b6_keine_secrets(roh), [])

    def test_perplexity_ist_vollstaendig_raus(self):
        """Auftrag 03.10.2026: kostenlose Alternative statt Perplexity."""
        roh = (ROOT / "data" / "werkbank.yaml").read_text(encoding="utf-8").lower()
        # Erwähnung in Begründungen ist erlaubt – ein Anbietereintrag nicht.
        anbieter = [a["id"] for a in self.ssot["antwortwerk"]["suche"]]
        anbieter += [s["id"] for s in self.ssot["antwortwerk"]["synthese"]]
        self.assertNotIn("perplexity", anbieter)
        self.assertNotIn("api.perplexity.ai", roh)

    def test_fragenplan_ist_vollstaendig(self):
        self.assertGreaterEqual(len(self.ssot["fragen"]), 3)
        ids = set()
        for f in self.ssot["fragen"]:
            self.assertTrue(f["frage"].strip().endswith("?"), f"{f['id']}: keine Frage")
            self.assertGreaterEqual(int(f["takt_tage"]), 7, "Takt zu eng (Höflichkeit)")
            self.assertNotIn(f["id"], ids, "doppelte Frage-id")
            ids.add(f["id"])


class VertragTests(unittest.TestCase):
    """Positivprobe plus Sabotage: Jede Regel muss beißen können."""

    def setUp(self):
        self.ssot = lade()
        self.text = (ROOT / "data" / "werkbank.yaml").read_text(encoding="utf-8")

    def test_echter_vertrag_ist_gruen(self):
        befunde = gate.pruefe_vertrag(self.ssot, self.text)
        self.assertEqual({r: v for r, v in befunde.items() if v}, {})

    def test_b1_bricht_bei_bezahlanbieter(self):
        s = copy.deepcopy(self.ssot)
        s["antwortwerk"]["suche"].append(
            {"id": "teuer", "kostenpflichtig": True, "schluessel_noetig": True})
        self.assertTrue(gate.b1_kostenregel(s))

    def test_b2_bricht_ohne_schluesselfreie_suche(self):
        s = copy.deepcopy(self.ssot)
        for a in s["antwortwerk"]["suche"]:
            a["schluessel_noetig"] = True
        self.assertTrue(gate.b2_schluesselfreier_weg(s))

    def test_b2_bricht_wenn_leser_rueckfall_verliert(self):
        s = copy.deepcopy(self.ssot)
        wa.gewerk(s, "leser")["rueckfall"] = []
        self.assertTrue(gate.b2_schluesselfreier_weg(s))

    def test_b3_bricht_wenn_standby_verboten(self):
        s = copy.deepcopy(self.ssot)
        wa.gewerk(s, "konnektor")["standby_ok"] = False
        self.assertTrue(gate.b3_standby_ist_kein_fehler(s))

    def test_b4_bricht_bei_schreibrecht_fuer_recherche(self):
        for gid in ("antwortwerk", "leser", "browser"):
            s = copy.deepcopy(self.ssot)
            wa.gewerk(s, gid)["schreibend"] = True
            self.assertTrue(gate.b4_leseregel(s), f"{gid} darf nicht schreiben")

    def test_b4_bricht_ohne_trockenlaufpflicht(self):
        s = copy.deepcopy(self.ssot)
        wa.gewerk(s, "konnektor")["freigabe"]["trockenlauf_pflicht"] = False
        self.assertTrue(gate.b4_leseregel(s))

    def test_b5_bricht_ohne_abrufdatum(self):
        s = copy.deepcopy(self.ssot)
        s["antwortwerk"]["belege"]["abrufdatum_pflicht"] = False
        self.assertTrue(gate.b5_belegpflicht(s))

    def test_b6_erkennt_eingeschleusten_schluessel(self):
        for gift in ('api_key: "sk-0123456789abcdefghij"',
                     'token: "gsk_0123456789abcdefghijklmn"',
                     "schluessel: pplx-0123456789abcdefghij"):
            self.assertTrue(gate.b6_keine_secrets(self.text + "\n" + gift),
                            f"nicht erkannt: {gift}")

    def test_b6_gibt_keinen_fehlalarm_auf_env_namen(self):
        harmlos = self.text + "\n  env: PERPLEXITY_API_KEY\n  env: COMPOSIO_API_KEY\n"
        self.assertEqual(gate.b6_keine_secrets(harmlos), [])

    def test_b8_bricht_wenn_workflow_den_selbsttest_verliert(self):
        """Ein Workflow ohne fail-closed-Prüfung ist Scheingrün."""
        wf = (ROOT / ".github" / "workflows" / "werkbank.yml").read_text(encoding="utf-8")
        self.assertIn("--selftest", wf)
        self.assertIn("werkbank_gate.py", wf)

    def test_b8_npm_skripte_existieren(self):
        skripte = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["scripts"]
        for name in gate.NPM_PFLICHT:
            self.assertIn(name, skripte)

    def test_b9_bricht_wenn_partner_entsperrt_wird(self):
        s = copy.deepcopy(self.ssot)
        s["antwortwerk"]["belege"]["sperrliste"] = ["franksfinanzcheck.de"]
        self.assertTrue(gate.b9_domain_disziplin(s))


class BelegdisziplinTests(unittest.TestCase):
    """Die Regel, an der alles hängt: Wer darf Beleg sein?"""

    def setUp(self):
        self.ssot = lade()
        self.sperre = self.ssot["antwortwerk"]["belege"]["sperrliste"]
        self.allow = aw.lade_allowlist(self.ssot)

    def test_allowlist_wird_wirklich_geladen(self):
        self.assertGreater(len(self.allow), 5, "Allowlist leer – nichts wäre belegfähig")
        self.assertIn("bundesnetzagentur.de", self.allow)

    def test_amtliche_quelle_ist_belegfaehig(self):
        treffer = aw.belegfaehig("https://www.bundesnetzagentur.de/x",
                                 self.allow, self.sperre)
        self.assertIsNotNone(treffer)
        self.assertEqual(treffer["rang"], 1)

    def test_affiliate_partner_ist_nie_belegfaehig(self):
        for url in ("https://www.check24.de/strom/",
                    "https://a.check24.net/go?x=1",
                    "https://m.check24.de/",
                    "https://www.tarifcheck.de/",
                    "https://a.partner-versicherung.de/klick"):
            self.assertIsNone(aw.belegfaehig(url, self.allow, self.sperre), url)

    def test_kein_selbstbeleg(self):
        for url in ("https://franksfinanzcheck.de/strom/",
                    "https://www.franksfinanzcheck.de/cockpit/"):
            self.assertIsNone(aw.belegfaehig(url, self.allow, self.sperre), url)

    def test_tarnhost_wird_nicht_faelschlich_erlaubt(self):
        """`test.de.evil.example` ist nicht `test.de`."""
        self.assertIsNone(
            aw.belegfaehig("https://test.de.evil.example/x", self.allow, self.sperre))

    def test_tarnhost_umgeht_die_sperre_nicht(self):
        """Umgekehrt: Eine Subdomain eines Partners bleibt gesperrt."""
        self.assertIsNone(
            aw.belegfaehig("https://werbung.check24.de/x", self.allow, self.sperre))

    def test_port_umgeht_die_sperre_nicht(self):
        """Regression: `domain_von` behielt den Port – `check24.de:443`
        rutschte dadurch an der Sperrliste vorbei."""
        self.assertEqual(wa.domain_von("https://www.check24.de:443/x"), "check24.de")
        self.assertIsNone(
            aw.belegfaehig("https://check24.de:443/strom", self.allow, self.sperre))

    def test_zugangsdaten_im_host_taeuschen_die_sperre_nicht(self):
        """`https://test.de@check24.de/` ist check24.de, nicht test.de."""
        self.assertEqual(wa.domain_von("https://test.de@check24.de/x"), "check24.de")
        self.assertIsNone(
            aw.belegfaehig("https://test.de@check24.de/x", self.allow, self.sperre))

    def test_unbekannte_domain_ist_nicht_belegfaehig(self):
        """Allowlist ist eine Allowlist – nicht 'alles außer Sperrliste'."""
        self.assertIsNone(
            aw.belegfaehig("https://irgendein-blog.example/x", self.allow, self.sperre))


class VerschwiegenheitTests(unittest.TestCase):
    """Nichts aus der Umgebung darf im Klartext ins Cockpit sickern.

    WERKBANK-STATUS.md wird eingecheckt. Eine SearXNG-Instanz hinter
    Basic-Auth steht als https://nutzer:geheim@host in SEARXNG_URL –
    landete sie ungekürzt im Cockpit, stünde das Passwort im Repo.
    Von CodeQL auf PR #548 gemeldet, hier eingefroren.
    """

    GEHEIM = "s3hr-geheim"

    def test_anzeige_url_entfernt_zugangsdaten(self):
        gekuerzt = wa.anzeige_url(f"https://nutzer:{self.GEHEIM}@searx.example.org/search?q=x")
        self.assertEqual(gekuerzt, "https://searx.example.org")
        self.assertNotIn(self.GEHEIM, gekuerzt)
        self.assertNotIn("nutzer", gekuerzt)

    def test_anzeige_url_behaelt_port_und_vertraegt_muell(self):
        self.assertEqual(wa.anzeige_url("http://127.0.0.1:8080/search"),
                         "http://127.0.0.1:8080")
        for muell in ("", "   ", "kein-schema", "http://"):
            self.assertIsInstance(wa.anzeige_url(muell), str)

    def test_cockpit_grund_zeigt_das_passwort_nicht(self):
        anbieter = {"id": "searxng", "env_url": "WERKBANK_TEST_SEARXNG"}
        os.environ["WERKBANK_TEST_SEARXNG"] = f"https://nutzer:{self.GEHEIM}@searx.example.org"
        try:
            zustand = wa.such_status(anbieter)
        finally:
            os.environ.pop("WERKBANK_TEST_SEARXNG", None)
        self.assertEqual(zustand["zustand"], wa.BEREIT)
        self.assertNotIn(self.GEHEIM, zustand["grund"])
        self.assertIn("searx.example.org", zustand["grund"])

    def test_abruffehler_zitiert_die_zugangsdaten_nicht(self):
        # Kaputtes Schema -> ValueError, deren Text die URL wörtlich enthält.
        _, fehler = wa._hole(f"httpx://nutzer:{self.GEHEIM}@host.example/pfad", timeout=1)
        self.assertIsNotNone(fehler)
        self.assertNotIn(self.GEHEIM, fehler)

    def test_schluessel_steht_nie_in_einer_rueckgabe(self):
        ssot = wa.lade_ssot()
        env = (wa.gewerk(ssot, "konnektor") or {}).get("env") or "COMPOSIO_API_KEY"
        os.environ[env] = self.GEHEIM
        try:
            texte = [
                json.dumps(wa.konnektor_status(ssot), ensure_ascii=False),
                json.dumps(wa.konnektor_ausfuehren(ssot, "GMAIL_SEND_EMAIL",
                                                   {"an": "x@example.org"},
                                                   trocken=True), ensure_ascii=False),
                json.dumps(wa.gesamtlage(ssot), ensure_ascii=False),
            ]
        finally:
            os.environ.pop(env, None)
        for text in texte:
            self.assertNotIn(self.GEHEIM, text)


class FeedTests(unittest.TestCase):
    """Der Themenpool ist die letzte Rückfallebene – er muss beide Formate können."""

    def test_rss_und_atom_werden_beide_gelesen(self):
        """Regression: Ein Parser nur für <item> übersah die Atom-Feeds
        des Hausplans (tagesschau) und ließ den Probelauf leer ausgehen."""
        rss = ("<rss><channel><item><title>RSS-Titel</title>"
               "<link>https://a.example/1</link></item></channel></rss>")
        atom = ('<feed><entry><title>Atom-Titel</title>'
                '<link href="https://b.example/2" rel="alternate"/></entry></feed>')
        self.assertEqual(wa._feed_eintraege(rss),
                         [("RSS-Titel", "https://a.example/1")])
        self.assertEqual(wa._feed_eintraege(atom),
                         [("Atom-Titel", "https://b.example/2")])

    def test_cdata_titel_wird_entpackt(self):
        roh = ("<rss><item><title><![CDATA[Strom & Gas]]></title>"
               "<link>https://a.example/1</link></item></rss>")
        self.assertEqual(wa._feed_eintraege(roh)[0][0], "Strom & Gas")

    def test_themenplan_des_hauses_hat_lesbare_feeds(self):
        """Die echte SSOT muss zur echten Parser-Erwartung passen."""
        plan = yaml.safe_load(
            (ROOT / "data" / "agent_reach" / "themenplan.yaml").read_text(encoding="utf-8"))
        feeds = [e["url"] for e in (plan.get("rss") or [])
                 if isinstance(e, dict) and e.get("url")]
        self.assertGreaterEqual(len(feeds), 1,
                                "Themenpool-Rückfall wäre tot: keine RSS-Quelle gefunden")


class SyntheseTests(unittest.TestCase):
    """Die extraktive Synthese darf nie etwas erfinden."""

    def test_ohne_belege_kein_text(self):
        erg = aw.synthese_extraktiv("Wie hoch ist der Strompreis?", [])
        self.assertEqual(erg["text"], "")
        self.assertEqual(erg["aussagen"], [])

    def test_zitiert_woertlich_und_nummeriert(self):
        satz = ("Der Grundversorgungstarif kostete im Januar 2026 durchschnittlich "
                "43,2 Cent je Kilowattstunde.")
        belege = [{"url": "https://www.bundesnetzagentur.de/x",
                   "herausgeber": "Bundesnetzagentur", "rang": 1,
                   "passagen": [{"satz": satz, "punkte": 40}]}]
        erg = aw.synthese_extraktiv("Wie hoch ist der Strompreis 2026?", belege)
        self.assertIn(satz, erg["text"], "Satz wurde umformuliert")
        self.assertTrue(erg["text"].strip().endswith("[1]"))

    def test_belegnummern_zeigen_auf_vorhandene_belege(self):
        belege = [
            {"url": "https://a.test", "herausgeber": "A", "rang": 1,
             "passagen": [{"satz": "A" * 80 + " Strompreis 2026.", "punkte": 20}]},
            {"url": "https://b.test", "herausgeber": "B", "rang": 2,
             "passagen": [{"satz": "B" * 80 + " Strompreis 2026.", "punkte": 30}]},
        ]
        erg = aw.synthese_extraktiv("Strompreis?", belege)
        for a in erg["aussagen"]:
            self.assertIn(a["beleg"], range(1, len(belege) + 1))

    def test_passagen_filtern_navigationsrauschen(self):
        text = ("Cookies akzeptieren. Zum Hauptinhalt springen. "
                "Der Strompreis lag 2026 laut Erhebung bei 41,5 Cent je "
                "Kilowattstunde für Haushaltskunden in Deutschland. "
                "Impressum Datenschutz Kontakt.")
        p = aw.passagen(text, aw.begriffe_aus("Wie hoch war der Strompreis 2026?"))
        self.assertEqual(len(p), 1)
        self.assertIn("41,5 Cent", p[0]["satz"])

    def test_passagen_bevorzugen_saetze_mit_zahlen(self):
        mit = "Der Strompreis lag 2026 bei 41,5 Cent je Kilowattstunde im Mittel."
        ohne = "Der Strompreis ist in diesem Jahr erneut ein wichtiges Thema gewesen."
        p = aw.passagen(f"{ohne} {mit}", aw.begriffe_aus("Strompreis 2026?"))
        self.assertEqual(p[0]["satz"], mit, "Zahlensatz nicht bevorzugt")

    def test_llm_prompt_bindet_an_das_material(self):
        belege = [{"url": "https://x.test", "herausgeber": "X", "rang": 1,
                   "passagen": [{"satz": "Ein Satz mit Substanz.", "punkte": 10}]}]
        prompt = aw._llm_prompt("Frage?", belege)
        self.assertIn("AUSSCHLIESSLICH", prompt)
        self.assertIn("Kein Wissen aus deinem Gedächtnis", prompt)
        self.assertIn("https://x.test", prompt)


class StandbyTests(unittest.TestCase):
    """Fehlende Voraussetzung ist ein Zustand, kein Absturz."""

    def setUp(self):
        self.ssot = lade()

    def test_statuspfad_macht_keinen_netzaufruf(self):
        original = urllib.request.urlopen

        def verboten(*_a, **_k):
            raise AssertionError("Netzaufruf im Statuspfad")

        urllib.request.urlopen = verboten
        try:
            lage = wa.gesamtlage(self.ssot)
        finally:
            urllib.request.urlopen = original
        self.assertEqual(len(lage["gewerke"]), 4)

    def test_jedes_gewerk_meldet_einen_bekannten_zustand(self):
        for g in wa.gesamtlage(self.ssot)["gewerke"]:
            self.assertIn(g["zustand"], {wa.BEREIT, wa.STANDBY, wa.DEFEKT})
            self.assertTrue(g["grund"].strip(), f"{g['id']} ohne Begründung")

    def test_konnektor_ohne_schluessel_ist_standby_nicht_defekt(self):
        import os

        alt = os.environ.pop("COMPOSIO_API_KEY", None)
        try:
            self.assertEqual(wa.konnektor_status(self.ssot)["zustand"], wa.STANDBY)
        finally:
            if alt is not None:
                os.environ["COMPOSIO_API_KEY"] = alt

    def test_leser_ist_immer_bereit_weil_rueckfall_existiert(self):
        self.assertEqual(wa.leser_status(self.ssot)["zustand"], wa.BEREIT)

    def test_offline_lauf_erzeugt_keine_belege(self):
        lauf = aw.beantworte("Testfrage", self.ssot, mit_browser=False, offline=True)
        self.assertEqual(lauf["belege"], [])
        self.assertEqual(lauf["antwort"]["text"], "")


class KonnektorTests(unittest.TestCase):
    """Das einzige schreibende Gewerk – doppelt verriegelt."""

    def setUp(self):
        self.ssot = lade()

    def test_freigabeliste_ist_ab_werk_leer(self):
        freigabe = wa.gewerk(self.ssot, "konnektor")["freigabe"]
        self.assertEqual(freigabe["erlaubte_aktionen"], [],
                         "Konnektor darf ab Werk nichts ausführen")
        self.assertEqual(freigabe["modus"], "mensch")

    def test_nicht_freigegebene_aktion_wird_verweigert(self):
        erg = wa.konnektor_ausfuehren("GITHUB_CREATE_AN_ISSUE", {}, self.ssot,
                                      trocken=False)
        self.assertEqual(erg["zustand"], "verweigert")

    def test_freigegebene_aktion_bleibt_ohne_schluessel_im_standby(self):
        import os

        s = copy.deepcopy(self.ssot)
        wa.gewerk(s, "konnektor")["freigabe"]["erlaubte_aktionen"] = ["TEST_SLUG"]
        alt = os.environ.pop("COMPOSIO_API_KEY", None)
        try:
            erg = wa.konnektor_ausfuehren("TEST_SLUG", {}, s, trocken=False)
            self.assertEqual(erg["zustand"], wa.STANDBY)
        finally:
            if alt is not None:
                os.environ["COMPOSIO_API_KEY"] = alt

    def test_trockenlauf_fuehrt_nichts_aus(self):
        s = copy.deepcopy(self.ssot)
        wa.gewerk(s, "konnektor")["freigabe"]["erlaubte_aktionen"] = ["TEST_SLUG"]
        original = urllib.request.urlopen

        def verboten(*_a, **_k):
            raise AssertionError("Trockenlauf hat gesendet")

        urllib.request.urlopen = verboten
        try:
            erg = wa.konnektor_ausfuehren("TEST_SLUG", {"a": 1}, s, trocken=True)
        finally:
            urllib.request.urlopen = original
        self.assertEqual(erg["zustand"], "trockenlauf")


class BrueckeTests(unittest.TestCase):
    """Die Playwright-Brücke muss existieren und den Hausresolver nutzen."""

    def test_bruecke_existiert_und_nutzt_e2e_resolver(self):
        pfad = ROOT / "tools" / "werkbank" / "render.mjs"
        self.assertTrue(pfad.is_file())
        quelle = pfad.read_text(encoding="utf-8")
        self.assertIn("resolveLaunchOptions", quelle,
                      "Brücke umgeht den E2E-Browser-Resolver")
        self.assertIn("playwright-core", quelle)

    def test_bruecke_meldet_pflichtfelder(self):
        quelle = (ROOT / "tools" / "werkbank" / "render.mjs").read_text(encoding="utf-8")
        for feld in lade()["browser"]["pflichtfelder"]:
            self.assertIn(feld, quelle, f"Brücke liefert '{feld}' nicht")


class KetteTests(unittest.TestCase):
    """Ende-zu-Ende-Beweis der ganzen Kette – hermetisch auf localhost.

    Kein echter Netzaufruf: Ein Fixture-Server spielt SearXNG und eine
    Quellseite. Damit ist belegt, dass suchen → filtern → lesen →
    Passagen → Synthese → Dossier wirklich zusammenspielt. Genau das
    hätte der erste Probelauf sonst nur geraten.
    """

    SATZ = ("Der durchschnittliche Strompreis für Haushaltskunden lag im Jahr "
            "2026 bei 41,8 Cent je Kilowattstunde.")

    @classmethod
    def setUpClass(cls):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

        satz = cls.SATZ

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_a):  # Testlauf nicht zumüllen
                pass

            def do_GET(self):  # noqa: N802
                if self.path.startswith("/search"):
                    hafen = self.server.server_address[1]
                    koerper = json.dumps({"results": [
                        # belegfähig (Allowlist wird im Test gesetzt)
                        {"title": "Monitoringbericht", "engine": "bing",
                         "url": f"http://127.0.0.1:{hafen}/amt",
                         "content": "Auszug"},
                        # muss an der Sperrliste scheitern
                        {"title": "Stromvergleich", "engine": "bing",
                         "url": "https://www.check24.de/strom/", "content": "Werbung"},
                        # muss an der Allowlist scheitern
                        {"title": "Irgendein Blog", "engine": "bing",
                         "url": "https://irgendwo.example/strom", "content": "Meinung"},
                    ]}).encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                elif self.path.startswith("/amt"):
                    koerper = (
                        "<html><body><nav>Navigation Menü</nav>"
                        "<p>Cookies akzeptieren.</p>"
                        f"<p>{satz}</p>"
                        "<footer>Impressum</footer></body></html>").encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                else:
                    self.send_response(404)
                    koerper = b""
                self.send_header("Content-Length", str(len(koerper)))
                self.end_headers()
                self.wfile.write(koerper)

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.hafen = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def setUp(self):
        import os

        self.ssot = lade()
        self.alt_url = os.environ.get("SEARXNG_URL")
        os.environ["SEARXNG_URL"] = f"http://127.0.0.1:{self.hafen}"

        # Die Fixture-Domain belegfähig machen – sonst prüfen wir nur,
        # dass die Allowlist alles verwirft (das tut der Nachbartest).
        self.alt_allow = aw.lade_allowlist
        aw.lade_allowlist = lambda _ssot: {
            "127.0.0.1": {"herausgeber": "Fixture-Behörde", "rang": 1}}

        # Jina nie aus einem Unit-Test heraus anrufen: direkt auf urllib.
        self.alt_jina = wa._lies_jina
        wa._lies_jina = lambda *_a, **_k: {}

    def tearDown(self):
        import os

        aw.lade_allowlist = self.alt_allow
        wa._lies_jina = self.alt_jina
        if self.alt_url is None:
            os.environ.pop("SEARXNG_URL", None)
        else:
            os.environ["SEARXNG_URL"] = self.alt_url

    def test_volle_kette_liefert_belegte_antwort(self):
        lauf = aw.beantworte("Wie hoch ist der Strompreis 2026?", self.ssot,
                             mit_browser=False)

        self.assertEqual(lauf["suche"]["anbieter"], "searxng")
        self.assertEqual(len(lauf["belege"]), 1, lauf["verworfen"])

        beleg = lauf["belege"][0]
        self.assertEqual(beleg["herausgeber"], "Fixture-Behörde")
        self.assertEqual(beleg["abgerufen_am"], aw.heute().isoformat())
        self.assertIn(beleg["leseweg"], {"crawl4ai", "urllib"})

        # Die Antwort zitiert wörtlich und nennt die Belegnummer.
        self.assertIn(self.SATZ, lauf["antwort"]["text"])
        self.assertIn("[1]", lauf["antwort"]["text"])

    def test_affiliate_und_unbekannte_domain_werden_verworfen(self):
        lauf = aw.beantworte("Wie hoch ist der Strompreis 2026?", self.ssot,
                             mit_browser=False)
        verworfen = " ".join(v["url"] for v in lauf["verworfen"])
        self.assertIn("check24.de", verworfen, "Affiliate-Treffer nicht verworfen")
        self.assertIn("irgendwo.example", verworfen, "Unbekannte Domain nicht verworfen")

    def test_navigationsrauschen_landet_nicht_in_der_antwort(self):
        """Regression: Die unterste Leseebene schleppte <nav>/<footer>/<title>
        in die zitierte Passage – ein Beleg mit 'Navigation Impressum' darin
        ist als Zitat wertlos."""
        lauf = aw.beantworte("Wie hoch ist der Strompreis 2026?", self.ssot,
                             mit_browser=False)
        for muell in ("Cookies akzeptieren", "Impressum", "Navigation",
                      "Monitoringbericht"):
            self.assertNotIn(muell, lauf["antwort"]["text"], f"Beiwerk: {muell}")
        self.assertTrue(lauf["antwort"]["text"].startswith(f"- {self.SATZ}"),
                        lauf["antwort"]["text"][:160])

    def test_dossier_wird_vollstaendig_geschrieben(self):
        import tempfile

        lauf = aw.beantworte("Wie hoch ist der Strompreis 2026?", self.ssot,
                             mit_browser=False)
        alt = aw.AUSGABE_DIR
        with tempfile.TemporaryDirectory() as tmp:
            aw.AUSGABE_DIR = Path(tmp)
            try:
                pfad = aw.dossier_schreiben(lauf, self.ssot)
                md = pfad.read_text(encoding="utf-8")
                daten = json.loads(pfad.with_suffix(".json").read_text(encoding="utf-8"))
            finally:
                aw.AUSGABE_DIR = alt

        self.assertIn("## Antwort", md)
        self.assertIn("## Belege", md)
        self.assertIn("## Suchlage", md)
        self.assertIn(self.SATZ, md)
        self.assertIn("abgerufen am", md)
        self.assertEqual(daten["belege"][0]["url"], lauf["belege"][0]["url"])


class SelbsttestTests(unittest.TestCase):
    """Die Selbsttests selbst müssen grün und offline sein."""

    def test_antwortwerk_selbsttest_gruen(self):
        self.assertEqual(aw.selftest(), [])

    def test_gate_selbsttest_gruen(self):
        self.assertEqual(gate.selftest(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
