"""Vertragstests für den KI-Transportweg (Rollout 03.10.2026).

SSOT `data/ki_transportweg.yaml` · Gate `scripts/ki_transportweg.py` ·
Runbook `docs/ANLEITUNG-KI-TRANSPORTWEG.md`

WARUM DIESE DATEI EXISTIERT
Sie ist der Nachfolger von ``test_keine_puter_abhaengigkeit.py`` und
deckt dessen Zusicherungen vollständig mit ab – nur breiter und nicht
mehr an einen einzelnen Anbieter gebunden. Der alte Test verbot genau
eine Brücke (Puter). Dieser Test verbietet die ganze Bauweise:

  · keine Browser-Brücke, kein UI-Scraping, kein geteiltes Fremdkonto
    (auch nicht für ChatGPT) – `TransportwegVertrag`
  · gelöschte Brückendateien bleiben gelöscht – `TransportwegVertrag`
  · jeder Modell-Rufer nutzt den gemeinsamen Client – `GemeinsamerClient`
  · KI-Workflows reichen echte, kostenlose Schlüssel durch – und zwar
    mindestens zwei – `WorkflowSchluessel`

Dazu kommt, was es vorher nirgends gab: Kostenwahrheit (keine
Paid-Anbieter in automatischen Ketten), Redundanz (ein leeres
Tageskontingent darf die Produktion nicht anhalten) und die Garantie,
dass SSOT und Client nicht auseinanderdriften.

Läuft offline, ohne Netz und ohne Schlüssel.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import ki_transportweg as kt  # noqa: E402
import llm_client  # noqa: E402


class Selbsttest(unittest.TestCase):
    """Das Gate muss sich selbst sabotieren können."""

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(kt.selftest(), [],
                         "Der Gate-Selbsttest meldet Fehler – siehe Ausgabe "
                         "von `npm run test:ki`.")

    def test_echter_stand_haelt_den_vertrag(self):
        befunde = kt.pruefe_vertrag(kt.lade_ssot())
        gebrochen = {r: v for r, v in befunde.items() if v}
        self.assertEqual(gebrochen, {},
                         "Der Transportweg-Vertrag ist am echten Stand "
                         "gebrochen.")


class Kostenwahrheit(unittest.TestCase):
    """Geld ist der Punkt, an dem eine Automatik unbemerkt teuer wird."""

    def setUp(self):
        self.ssot = kt.lade_ssot()

    def test_keine_paid_anbieter_in_ketten(self):
        self.assertEqual(kt.t1_kostenregel(self.ssot), [])

    def test_kostenklassen_sind_deckungsgleich_mit_dem_client(self):
        for a in self.ssot["anbieter"]:
            self.assertEqual(
                llm_client.KOSTENKLASSE.get(a["id"]), a["kostenklasse"],
                f"Kostenklasse von {a['id']} driftet zwischen SSOT und "
                "llm_client – zwei Wahrheiten über Geld sind eine zu viel.")

    def test_jeder_anbieter_nennt_eine_quelle(self):
        for a in self.ssot["anbieter"]:
            self.assertTrue(str(a.get("quelle", "")).startswith("http"),
                            f"{a['id']} behauptet ein Kontingent ohne Quelle.")

    def test_es_gibt_keinen_kostenpflichtigen_weg_mehr(self):
        """Verschärft am 03.10.2026: Paid ist nicht mehr Opt-in, sondern weg.

        Vorher galt „kostenpflichtig erlaubt, aber nicht automatisch".
        Das war zu weich: Zwei nächtliche Workflows reichten Paid-
        Schlüssel durch, zwei Anbieter-Reihenfolgen begannen damit.
        Ein Opt-in, das man vergessen kann, ist eine Rechnung, die man
        vergisst.
        """
        self.assertEqual(kt.t1_kostenregel(self.ssot), [])
        self.assertEqual(set(llm_client.KOSTENKLASSE.values()), {"gratis"})
        for pid in kt.PAID_PROVIDER_IDS:
            self.assertNotIn(pid, llm_client.PROVIDERS)
            self.assertNotIn(pid, llm_client.ENV_KEYS)

    def test_alter_paid_aufruf_scheitert_laut_statt_still(self):
        """Ein vergessener Aufruf muss erklären, nicht schweigen.

        Stille Fehlschläge sind die Schadensklasse aus Issue #514.
        """
        for pid in ("openai", "claude"):
            self.assertIn(pid, llm_client.ENTFERNT)
            self.assertIsNone(llm_client.chat(pid, prompt="x"))

    def test_paid_erkenner_findet_schluessel_und_endpunkte(self):
        for text in ("OPENAI" + "_API_KEY", "ANTHROPIC" + "_API_KEY",
                     "https://api." + "openai.com/v1/chat/completions",
                     "https://api." + "anthropic.com/v1/messages"):
            self.assertTrue(kt.paid_spuren_in(text),
                            f"Paid-Spur nicht erkannt: {text}")

    def test_paid_erkenner_meldet_gratis_schluessel_nicht(self):
        self.assertEqual(
            kt.paid_spuren_in("GROQ_API_KEY NVIDIA_API_KEY "
                              "CLOUDFLARE_API_TOKEN GEMINI_API_KEY"), [])

    def test_kein_paid_endpunkt_in_code_und_ci(self):
        for pfad, text in kt._quelltexte():
            self.assertEqual(
                kt.paid_spuren_in(text), [],
                f"{pfad} enthält wieder einen kostenpflichtigen Weg.")


class Redundanz(unittest.TestCase):
    """Ein leeres Tageskontingent darf die Produktion nicht anhalten."""

    def setUp(self):
        self.ssot = kt.lade_ssot()

    def test_jede_kette_hat_mindestens_zwei_gratis_glieder(self):
        self.assertEqual(kt.t3_redundanz(self.ssot), [])

    def test_jede_kette_enthaelt_einen_kostenlosen_openai_hoster(self):
        self.assertEqual(kt.t4_openai_bahn(self.ssot), [])

    def test_openai_bahn_hat_drei_unabhaengige_hoster(self):
        """Drei Betreiber, ein Modell.

        Zwei wären ein Paar, drei sind eine Bahn: Groq, NVIDIA und
        Cloudflare teilen sich keine Infrastruktur und kein Kontingent.
        """
        self.assertEqual(len(llm_client.OPENAI_BAHN), 3)
        bahn = {a["id"] for a in self.ssot["anbieter"]
                if a.get("bahn") == "openai" and a["kostenklasse"] == "gratis"}
        self.assertEqual(bahn, set(llm_client.OPENAI_BAHN))

    def test_alle_bahn_hoster_liefern_dasselbe_offene_openai_modell(self):
        for a in self.ssot["anbieter"]:
            if a["id"] in llm_client.OPENAI_BAHN:
                self.assertIn("gpt-oss", a["modell"],
                              f"{a['id']} liefert nicht mehr OpenAIs offenes "
                              "Modell – dann ist es keine OpenAI-Bahn mehr.")


class TransportwegVertrag(unittest.TestCase):
    """Nachfolge von test_keine_puter_abhaengigkeit.py – breiter gefasst."""

    def test_keine_bruecken_spuren_in_skripten_und_workflows(self):
        self.assertEqual(kt.t5_keine_bruecken(kt.lade_ssot()), [])

    def test_geloeschte_bruecken_bleiben_geloescht(self):
        for rel in kt.GELOESCHTE_BRUECKEN:
            self.assertFalse(
                (ROOT / rel).exists(),
                f"{rel} ist zurück – der Transportweg ist llm_client.py.")

    def test_chatgpt_ui_scraping_ist_ausdruecklich_verboten(self):
        """Die naheliegende Abkürzung muss benannt und gesperrt sein.

        „ChatGPT Free" hat keine API. Der Weg, den Leute dann gehen –
        das Web-UI anzuzapfen – verstößt gegen die OpenAI-Bedingungen
        und bricht beim ersten Frontend-Update. Er darf nicht erst
        auffallen, wenn er schon im Repo steht.

        GEPRÜFT WIRD DAS VERHALTEN, NICHT DIE SCHREIBWEISE (03.10.2026).
        Vorher verglich dieser Test die Muster-Quelltexte per Teilstring.
        Das hatte zwei Mängel: Es prüfte die Rechtschreibung der Sperrliste
        statt ihrer Wirkung, und CodeQL las die Host-Vergleiche als
        unvollständige URL-Prüfung (2 Treffer, „high"). Jetzt werden echte
        Proben eingeschleust und die Wache muss anschlagen.
        """
        # Zur Laufzeit zusammengesetzt: Ein literaler Treffer in dieser
        # Datei wäre selbst eine Spur (siehe Kopfkommentar des Gates).
        host = "chat.openai" + ".com"
        proben = {
            "ui_anzapfung": f'URL = "https://{host}/backend-api/conversation"',
            "sitzungscookie": ('COOKIE = "__Secure-next-auth' + '.session-token"'),
        }
        for name, inhalt in proben.items():
            probe = SCRIPTS / f".vertragstest_{name}.py"
            probe.write_text(inhalt + "\n", encoding="utf-8")
            try:
                befunde = kt.t5_keine_bruecken(kt.lade_ssot())
            finally:
                probe.unlink(missing_ok=True)
            self.assertTrue(
                befunde,
                f"T5 übersieht die eingeschleuste Probe ‚{name}‘ – die "
                "ChatGPT-UI-Abkürzung wäre unbemerkt möglich.")

    def test_sperrliste_meldet_harmlosen_code_nicht(self):
        """Gegenprobe: Eine Wache, die immer anschlägt, schützt nichts."""
        probe = SCRIPTS / ".vertragstest_harmlos.py"
        probe.write_text('ANTWORT = "Die Rolle ChatGPT schreibt News."\n',
                         encoding="utf-8")
        try:
            befunde = kt.t5_keine_bruecken(kt.lade_ssot())
        finally:
            probe.unlink(missing_ok=True)
        self.assertEqual(
            befunde, [],
            "T5 meldet harmlosen Text als Brücke – Fehlalarme entwerten "
            "die Wache.")

    def test_sperrliste_schlaegt_auf_einer_echten_probe_an(self):
        probe = SCRIPTS / ".vertragstest_bruecke.py"
        spur = "PUTER" + "_AUTH_TOKEN"
        probe.write_text(f'TOK = os.environ.get("{spur}")\n', encoding="utf-8")
        try:
            befunde = kt.t5_keine_bruecken(kt.lade_ssot())
        finally:
            probe.unlink(missing_ok=True)
        self.assertTrue(befunde, "T5 übersieht eine eingeschleuste Brücke.")


class GemeinsamerClient(unittest.TestCase):
    """Ein Transportweg – ein Ort für Schlüssel, Retries und Kosten."""

    def test_alle_rufer_nutzen_llm_client(self):
        self.assertEqual(kt.t6_ein_transportweg(kt.lade_ssot()), [])

    def test_nebenstrecke_neben_dem_client_wird_gemeldet(self):
        """Sabotage: import llm_client plus direkter Endpunkt ist T6-Bruch."""
        probe = SCRIPTS / ".vertragstest_t6.py"
        spur = "https://api." + "groq.com/x"
        probe.write_text(f'import llm_client\nURL = "{spur}"\n',
                         encoding="utf-8")
        kt.RUFER.append("scripts/.vertragstest_t6.py")
        try:
            befunde = kt.t6_ein_transportweg(kt.lade_ssot())
        finally:
            kt.RUFER.remove("scripts/.vertragstest_t6.py")
            probe.unlink(missing_ok=True)
        self.assertTrue(any("T6" in b and "Endpunkt" in b for b in befunde),
                        "T6 übersieht einen direkten Modell-Endpunkt.")

    def test_alt_texte_sind_ueber_den_client_angebunden(self):
        """#647: Cover-Alt-Texte nutzen den gemeinsamen Weg, nicht Gemini direkt."""
        self.assertIn("scripts/alt_text_vorschlaege.py", kt.RUFER)
        text = (ROOT / "scripts" / "alt_text_vorschlaege.py").read_text(
            encoding="utf-8")
        self.assertIn("import llm_client", text)
        self.assertNotIn("generativelanguage.googleapis.com", text,
                         "kein zweiter Gemini-Endpunkt neben llm_client")

    def test_betroffene_skripte_haben_eine_nachvollziehbare_reihenfolge(self):
        for rel in ("scripts/faktenfrische.py",
                    "scripts/saisonaler_hero_refresh.py"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("import llm_client", text, rel)
            self.assertIn("PROVIDER_ORDER", text, rel)

    def test_gratis_steht_in_jeder_reihenfolge_vor_paid(self):
        """Ein versehentlich gesetzter Paid-Key darf nichts kosten."""
        for rel in ("scripts/faktenfrische.py",
                    "scripts/saisonaler_hero_refresh.py"):
            modul = __import__(Path(rel).stem)
            klassen = [llm_client.KOSTENKLASSE[p] for p in modul.PROVIDER_ORDER]
            if "paid" in klassen:
                self.assertNotIn(
                    "gratis", klassen[klassen.index("paid"):],
                    f"{rel}: Ein Gratis-Anbieter steht hinter einem "
                    "kostenpflichtigen.")

    def test_client_kennt_jeden_anbieter_der_ssot(self):
        for a in kt.lade_ssot()["anbieter"]:
            self.assertIn(a["id"], llm_client.PROVIDERS)
            self.assertIn(a["id"], llm_client.ENV_KEYS)

    def test_cloudflare_braucht_beide_angaben(self):
        """Ein halber Schlüssel ist keiner.

        Ohne Konto-ID gibt es keine URL. Würde `available()` trotzdem
        True sagen, liefe die Kette in einen garantierten Fehler statt
        zum nächsten Hoster.
        """
        sicherung = {k: os.environ.pop(k) for k in
                     ("CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID")
                     if k in os.environ}
        self.addCleanup(os.environ.update, sicherung)
        os.environ["CLOUDFLARE_API_TOKEN"] = "probe"
        self.addCleanup(os.environ.pop, "CLOUDFLARE_API_TOKEN", None)
        self.assertFalse(llm_client.available("cloudflare"))
        os.environ["CLOUDFLARE_ACCOUNT_ID"] = "konto"
        self.addCleanup(os.environ.pop, "CLOUDFLARE_ACCOUNT_ID", None)
        self.assertTrue(llm_client.available("cloudflare"))

    def test_denkspuren_landen_nie_im_artikel(self):
        """GPT-OSS denkt laut – das darf nicht in den Text.

        Groq schaltet das per Flag ab, NVIDIA und Cloudflare nicht
        immer. Ungefiltert stünde „analysis … assistantfinal" im
        Artikel: dieselbe Schadensklasse wie R16-PROMPT-ECHO (#521).
        """
        proben = [
            ("<think>intern</think>Sichtbarer Text.", "Sichtbarer Text."),
            ("analysis Überlegung assistantfinal Sichtbarer Text.",
             "Sichtbarer Text."),
            ("<reasoning>intern</reasoning>Sichtbarer Text.",
             "Sichtbarer Text."),
            ("Sauberer Text ohne Spur.", "Sauberer Text ohne Spur."),
        ]
        for roh, erwartet in proben:
            self.assertEqual(llm_client._ohne_denkspuren(roh), erwartet)


class WorkflowSchluessel(unittest.TestCase):
    """Die eigentliche Lehre aus Issue #514, als Vertrag.

    Dort lief eine Automatik gegen ein Konto, das es nicht gab, und
    meldete „übersprungen" statt rot zu werden. Ein Workflow mit nur
    einem Schlüssel ist derselbe Fall mit Verzögerung.
    """

    def setUp(self):
        self.ssot = kt.lade_ssot()

    def test_jeder_ki_workflow_reicht_zwei_gratis_schluessel_durch(self):
        self.assertEqual(kt.t9_schluessel_durchreichung(self.ssot), [])

    def test_kein_ki_workflow_reicht_einen_paid_schluessel_durch(self):
        paid_keys = [s for a in self.ssot["anbieter"]
                     if a["kostenklasse"] == "paid"
                     for s in (a.get("schluessel") or [])]
        for rel in kt.SCHLUESSEL_WORKFLOWS:
            text = (ROOT / rel).read_text(encoding="utf-8")
            for key in paid_keys:
                self.assertNotIn(
                    f"secrets.{key}", text,
                    f"{rel} reicht {key} durch – ein Zeitplan darf keine "
                    "kostenpflichtige API anrufen können.")

    def test_die_geprueften_workflows_existieren_wirklich(self):
        for rel in kt.SCHLUESSEL_WORKFLOWS:
            self.assertTrue((ROOT / rel).exists(),
                            f"{rel} fehlt – der Vertrag zeigt ins Leere.")


class WriterFlags(unittest.TestCase):
    """Die CLI darf keinen kostenpflichtigen Weg mehr anbieten."""

    def test_writer_bieten_nur_gratis_provider_an(self):
        for rel in ("scripts/claude_writer.py", "scripts/news_writer.py"):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertNotRegex(
                text, r'choices=\[[^\]]*"(openai|claude)"',
                f"{rel} bietet weiter einen kostenpflichtigen Provider an.")
            self.assertIn("llm_client.PROVIDERS", text,
                          f"{rel} soll die Auswahl aus dem Client ziehen – "
                          "eine zweite Liste läuft auseinander.")


class Routing(unittest.TestCase):
    def setUp(self):
        self.ssot = kt.lade_ssot()

    def test_jede_pflichtaufgabe_hat_eine_kette(self):
        self.assertEqual(kt.t7_routing_vollstaendig(self.ssot), [])

    def test_ki_redaktion_folgt_derselben_bahn(self):
        """Zwei Konfigurationsorte dürfen sich nicht widersprechen."""
        import ki_shared
        cfg = ki_shared.load_config()
        for schluessel, aufgabe in (("anbieter_kette_lang", "lang"),
                                    ("anbieter_kette_news", "news")):
            self.assertEqual(
                list(cfg[schluessel]),
                list(self.ssot["routing"][aufgabe]["kette"]),
                f"{schluessel} in data/ki_redaktion.yaml weicht von "
                f"routing.{aufgabe} in data/ki_transportweg.yaml ab.")

    def test_verdrahtung_steht(self):
        self.assertEqual(kt.t8_verdrahtung(self.ssot), [])


class Betriebslage(unittest.TestCase):
    """Standby ist ein Zustand, kein Fehler – aber kein stiller."""

    def test_ohne_schluessel_ist_offline_modus_und_kein_crash(self):
        alle = [k for a in kt.lade_ssot()["anbieter"]
                for k in (a.get("schluessel") or [])]
        sicherung = {k: os.environ.pop(k) for k in alle if k in os.environ}
        self.addCleanup(os.environ.update, sicherung)
        zustand = kt.lage(kt.lade_ssot())
        self.assertTrue(zustand["offline_modus"])
        self.assertEqual(zustand["gratis_bereit"], [])
        self.assertFalse(zustand["redundanz_erfuellt"])

    def test_ein_gesetzter_schluessel_hebt_den_offline_modus_auf(self):
        sicherung = os.environ.pop("GROQ_API_KEY", None)
        os.environ["GROQ_API_KEY"] = "probe"
        self.addCleanup(lambda: (os.environ.pop("GROQ_API_KEY", None),
                                 os.environ.update({"GROQ_API_KEY": sicherung})
                                 if sicherung else None))
        zustand = kt.lage(kt.lade_ssot())
        self.assertFalse(zustand["offline_modus"])
        self.assertIn("groq", zustand["gratis_bereit"])
        # Ein Hoster ist noch keine Redundanz.
        self.assertFalse(zustand["redundanz_erfuellt"])


if __name__ == "__main__":
    unittest.main()
