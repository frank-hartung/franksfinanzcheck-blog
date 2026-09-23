#!/usr/bin/env python3
"""Regressionstest für die Zustellbarkeits-Wache (23.09.2026, Lauf #21-Folge).

WARUM: Der Newsletter-Versand war im Repo hart verriegelt, die beiden Schichten
DAVOR aber ungemessen – und beide hatten an diesem Tag recht:

  * Die API-Kante (Cloudflare vor `api.brevo.com`) filterte die
    Standardkennung der Python-Bibliothek mit HTTP 403 / „Error 1010“. Der Lauf
    nannte das „Absender-Vorprüfung fehlgeschlagen“ und damit einen
    Betreiber-Befund für einen Client-Fehler.
  * Die Freischalt-Checkliste schrieb `include:spf.brevo.com` in die Zone als
    nächsten Schritt. Gemessen war etwas anderes: DKIM veröffentlicht
    (`brevo1`/`brevo2._domainkey`), DMARC auf `p=reject; adkim=s; aspf=s`. Ein
    SPF-Include hätte an der Zustellung nichts geändert – und eine Policy über
    der Authentifizierung ist der Weg zur HARTEN Ableitung bei jedem DKIM-Ausfall.

Dieser Test hält die Unterscheidungen fest, an denen beide Vorfälle
vorbeigingen: Kante vs. Anbieter, Messlücke vs. Fund, Policy vs. Beleg.
Alles ohne Netz – der Resolver ist eingesetzt.
"""
from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")


def _load(name: str, datei: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SCRIPTS, datei))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


nz = _load("newsletter_zustellbarkeit", "newsletter_zustellbarkeit.py")


def digest_modul():
    """Der `newsletter_digest`, den die Wache zur Laufzeit importiert.

    Nicht selbst unter einem Kunstnamen laden: die Wache holt das Modul über
    `import newsletter_digest`, und ein zweiter Test lädt es unter demselben
    Namen. Wer eine eigene Kopie patcht, patcht an der Wache vorbei – genau die
    Klasse „Test grün, Lauf rot“, die dieses Repo überall sonst ausschließt.
    """
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    import importlib
    return importlib.import_module("newsletter_digest")

ZONE = "probe.example"


def resolver(werte: dict):
    """Injizierte Zone: werte[name][typ] → (RCode, Antworten)."""
    def aufloeser(name: str, typ: str):
        return werte.get(name, {}).get(typ, (3, []))
    return aufloeser


GRUNDZONE = {
    ZONE: {"MX": (0, ["41 route1.mx.cloudflare.net.", "3 route3.mx.cloudflare.net."]),
           "TXT": (0, ["v=spf1 include:_spf.mx.cloudflare.net ~all",
                       "brevo-code:abcdef"])},
    f"_dmarc.{ZONE}": {"TXT": (0, ["v=DMARC1; p=none; rua=mailto:reports@probe.example;"])},
}


def baum(state: dict | None = None) -> str:
    root = tempfile.mkdtemp(prefix="zustell-test-")
    os.makedirs(os.path.join(root, "data"), exist_ok=True)
    with open(os.path.join(root, "data", "newsletter_studio.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"capture": {"feld_themen": "themen"},
                   "email": {"absender": {"name": "Frank", "email": f"news@{ZONE}"},
                             "antwort_an": f"kontakt@{ZONE}"},
                   "themen": [{"id": "strom-sparen", "label": "Strom & Gas"}]}, fh)
    if state is not None:
        with open(os.path.join(root, "data", "newsletter_state.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(state, fh)
    return root


class CloudflareSeite(unittest.TestCase):
    def setUp(self):
        self.root = baum()
        self.wirkl = nz.AUFLOESER
        self.nd = digest_modul()
        self.echt_get = self.nd.TRANSPORT_GET
        nz.AUFLOESER = resolver(GRUNDZONE)
        # hermetisch: kein Netz, auch nicht versehentlich über die Brevo-Regeln
        self.nd.TRANSPORT_GET = lambda key, pfad: (0, "URLError: Testbaum ohne Netz")
        self.alt = os.environ.get("NEWSLETTER_MAILZONE", "")
        os.environ["NEWSLETTER_MAILZONE"] = ZONE

    def tearDown(self):
        nz.AUFLOESER = self.wirkl
        self.nd.TRANSPORT_GET = self.echt_get
        if self.alt:
            os.environ["NEWSLETTER_MAILZONE"] = self.alt
        else:
            os.environ.pop("NEWSLETTER_MAILZONE", None)
        shutil.rmtree(self.root, ignore_errors=True)

    def _regeln(self):
        return {r["regel"]: r for r in nz.pruefe_cloudflare(self.root)[0]}

    def test_ein_traeger_spf_ist_ok_und_zwei_sind_ein_fund(self):
        self.assertEqual("ok", self._regeln()["C1"]["gewicht"])
        zwei = json.loads(json.dumps(GRUNDZONE))
        zwei[ZONE]["TXT"] = (0, ["v=spf1 include:_spf.mx.cloudflare.net ~all",
                                  "v=spf1 include:spf.brevo.com ~all", "brevo-code:abcdef"])
        nz.AUFLOESER = resolver(zwei)
        self.assertEqual("fund", self._regeln()["C1"]["gewicht"],
                         "zwei SPF-Einträge = permerror, nicht „einer davon passt“")

    def test_dkim_entscheidet_ueber_die_dmarc_schaerfe(self):
        """p=reject ist OHNE eigenes Domain-DKIM eine Zustellungsverhinderung,
        MIT ihm zulässig – die Wache darf den Befund nicht an der Policy allein
        festmachen (sonst meldet sie jede gesunde, scharf konfigurierte Zone rot)."""
        reg = self._regeln()
        self.assertEqual("fund", reg["C3"]["gewicht"])          # kein DKIM gefunden
        self.assertEqual("ok", reg["C5"]["gewicht"])            # p=none: scharf wäre falsch
        scharf = json.loads(json.dumps(GRUNDZONE))
        scharf[f"_dmarc.{ZONE}"]["TXT"] = (0, ["v=DMARC1; p=reject; adkim=s; aspf=s; "
                                              "rua=mailto:x@y.de;"])
        nz.AUFLOESER = resolver(scharf)
        self.assertEqual("fund", self._regeln()["C5"]["gewicht"],
                         "p=reject ohne DKIM-Beleg bleibt unbemerkt")
        mit_dkim = json.loads(json.dumps(scharf))
        mit_dkim[f"mail._domainkey.{ZONE}"] = {"TXT": (0, ["k=rsa; p=MIGf…"])}
        nz.AUFLOESER = resolver(mit_dkim)
        reg2 = self._regeln()
        self.assertEqual("ok", reg2["C3"]["gewicht"])
        self.assertEqual("ok", reg2["C5"]["gewicht"],
                         "p=reject MIT Domain-DKIM darf kein Fund sein")

    def test_brevo_include_ist_hinweis_nicht_fund(self):
        """Die Checklisten-Anweisung war zu pauschal; die Wache meldet die wahre
        Lage: kein Alignment-Gewinn auf geteilter IP, also Hinweis mit Begründung."""
        reg = self._regeln()["C2"]
        self.assertEqual("hinweis", reg["gewicht"])
        self.assertIn("Alignement", reg["grund"])

    def test_netzfehler_ist_messluecke_und_nie_gruen(self):
        """Totalausfall der Abfrage: kein Grün, kein Befund – aber eine
        Lückenzeile pro Schicht. Schweigen wäre die alte Schwäche (ein
        nicht gestellter Blick darf nie wie „geprüft“ aussehen, und er darf
        umgekehrt auch nicht die erreichbaren Schichten verschlucken)."""
        nz.AUFLOESER = lambda name, typ: (-1, ["dns.google: URLError"])
        funde = nz.pruefe_cloudflare(self.root)[0]
        reg = {f["regel"]: f["gewicht"] for f in funde}
        self.assertEqual("nicht messbar", reg["C0"])
        for zeile in funde:
            if zeile["regel"] == "C7":
                continue          # Rein Repo-Herkunft (Studio-SSOT), braucht kein DNS
            self.assertIn(zeile["gewicht"], ("nicht messbar", "nicht gemessen"),
                          f"{zeile['regel']} erfindet bei Netzausfall ein Ergebnis: "
                          f"{zeile['gewicht']}")
        for verpasst in ("C1", "C3", "C4", "C5", "C6"):
            self.assertEqual("nicht gemessen", reg.get(verpasst),
                             f"{verpasst} fehlt als Lückenzeile")
        erg = nz.pruefe(self.root, mit_netz=True)
        self.assertEqual(0, erg["rc"], "eine Messlücke ist kein Versand-Fund")
        self.assertTrue(erg["zählung"]["nicht messbar"] + erg["zählung"]["nicht gemessen"])

    def test_txt_fetzen_werden_zusammengelesen(self):
        self.assertEqual("v=spf1 include:a ~all",
                         nz._txt_fetzen('"v=spf1 include:a" " ~all"'))

    def test_null_mx_ist_ein_fund_fuer_den_reply_to_kanal(self):
        zone = json.loads(json.dumps(GRUNDZONE))
        zone[ZONE]["MX"] = (0, ["0 ."])
        nz.AUFLOESER = resolver(zone)
        reg = self._regeln()
        self.assertEqual("fund", reg["C6"]["gewicht"],
                         "Null-MX lässt Antworten und Rückläufer im Nichts landen")

    def test_teilausfall_blindes_record_ist_luecke_der_rest_laeuft(self):
        """Ein blindes Record darf die erreichbaren Schichten nicht verschlucken.

        Vorbedingung für den Wert der ganzen Wache: Der frühe Totalabbruch machte
        aus einem wackelnden DoH-Endpunkt „nichts geprüft“ – inklusive der
        DMARC-Antwort, die längst da war. Agenturwürdig ist nur beides zusammen:
        Lücke benennen UND berichten, was messbar war.
        """
        zone = json.loads(json.dumps(GRUNDZONE))
        zone[ZONE]["TXT"] = (-1, ["dns.google: URLError"])     # nur TXT @ blind
        zone[f"brevo1._domainkey.{ZONE}"] = {"CNAME": (0, ["b1.probe-de.dkim.brevo.com."])}
        zone[f"brevo2._domainkey.{ZONE}"] = {"CNAME": (0, ["b2.probe-de.dkim.brevo.com."])}
        nz.AUFLOESER = resolver(zone)
        reg = self._regeln()
        self.assertEqual("nicht messbar", reg["C0"]["gewicht"])
        self.assertIn("TXT @", reg["C0"]["ist"].split("blind:")[-1])
        self.assertNotIn("TXT _dmarc", reg["C0"]["ist"].split("blind:")[-1])
        self.assertEqual("nicht gemessen", reg["C1"]["gewicht"],
                         "ungelesener SPF darf weder ok noch Fund sein")
        self.assertNotIn("C2", reg, "ohne gelesenen SPF gibt es kein Include-Urteil")
        self.assertEqual("nicht gemessen", reg["C4"]["gewicht"])
        self.assertEqual("ok", reg["C3"]["gewicht"],
                         "DKIM war messbar – die TXT-Lücke darf es nicht löschen")
        self.assertEqual("ok", reg["C5"]["gewicht"],
                         "DMARC war messbar – Lücke hinnehmen, Ergebnis verschlucken")
        self.assertEqual("ok", reg["C6"]["gewicht"])

    def test_halbe_dkim_delegation_ist_hinweis_nicht_fund(self):
        """Eine sichtbare von zwei CNAME-Delegationen ist kein „DKIM fehlt“.

        Der Fund-Text schrie previously nach einem DNS-Griff in eine laufende
        Zone, obwohl das Alignement trug – und die zweite Delegation war hier nur
        nicht abfragbar. Genau diese Verwechslung (Lücke = Befund) ist die
        Fehlerklasse hinter Lauf #21.
        """
        zone = json.loads(json.dumps(GRUNDZONE))
        zone[f"brevo1._domainkey.{ZONE}"] = {"CNAME": (0, ["b1.probe-de.dkim.brevo.com."])}
        zone[f"brevo2._domainkey.{ZONE}"] = {"CNAME": (-1, ["cloudflare-dns.com: URLError"])}
        nz.AUFLOESER = resolver(zone)
        reg = self._regeln()
        self.assertEqual("hinweis", reg["C3"]["gewicht"])
        self.assertIn("nicht abfragbar", reg["C3"]["soll"])
        self.assertNotEqual("fund", reg["C5"]["gewicht"],
                            "scharfe Policy bei sichtbarem DKIM ist kein Fund")
        self.assertNotIn("C5c", reg, "adkim=s-Hinweis läuft trotz Beleg")

    def test_txt_dkim_und_volstaendige_delegation_zaehlen_beide(self):
        """Beide publish-Formen sind korrekt – die Wache muss beide kennen."""
        zone = json.loads(json.dumps(GRUNDZONE))
        zone[f"mail._domainkey.{ZONE}"] = {"TXT": (0, ["v=DKIM1; k=rsa; p=MIGfpublic"])}
        nz.AUFLOESER = resolver(zone)
        self.assertEqual("ok", self._regeln()["C3"]["gewicht"])
        zone = json.loads(json.dumps(GRUNDZONE))
        for nr, host in (("brevo1", "b1"), ("brevo2", "b2")):
            zone[f"{nr}._domainkey.{ZONE}"] = {"CNAME": (0, [f"{host}.probe-de.dkim.brevo.com."])}
        nz.AUFLOESER = resolver(zone)
        reg = self._regeln()
        self.assertEqual("ok", reg["C3"]["gewicht"])
        self.assertNotIn("C5c", reg)

    def test_md_und_json_nennen_jeden_naechsten_schritt(self):
        erg = nz.pruefe(self.root, mit_netz=True)
        md = nz.als_md(erg)
        self.assertIn("Weg:", md)
        self.assertIn("C3", md)
        json.dumps(erg, ensure_ascii=False)         # muss serialisierbar sein
        for f in erg["funde"]:
            if f["gewicht"] == "fund":
                self.assertTrue(f["soll"] and f["soll"] != "—",
                                f"Fund {f['regel']} ohne Soll-Zustand")


class BrevoSeite(unittest.TestCase):
    def setUp(self):
        self.root = baum({"zuletzt_versandt": "2026-09-23T07:05:00+00:00",
                          "kampagne_id": 3})
        self.nd = digest_modul()
        self.echt_get, self.echt_post = self.nd.TRANSPORT_GET, self.nd.TRANSPORT
        self.key = os.environ.get("BREVO_API_KEY", "")
        os.environ["BREVO_API_KEY"] = "k"
        os.environ["BREVO_LIST_ID"] = "7"

    def tearDown(self):
        self.nd.TRANSPORT_GET, self.nd.TRANSPORT = self.echt_get, self.echt_post
        for var in ("BREVO_API_KEY", "BREVO_LIST_ID"):
            os.environ.pop(var, None)
        if self.key:
            os.environ["BREVO_API_KEY"] = self.key
        shutil.rmtree(self.root, ignore_errors=True)

    def test_kantenblock_wird_zum_b0_fund(self):
        """Genau die Antwort, die Lauf #21 rot machte, muss als Kanten-Befund
        enden – mit Client-Kennung im Text, nicht als Absender-Befund."""
        def kante(api_key, pfad):
            return 403, ('{"title":"Error 1010: Access denied","status":403,'
                         '"detail":"blocked based on your browser\'s signature"}')
        self.nd.TRANSPORT_GET = kante
        reg = {r["regel"]: r for r in nz.pruefe_brevo(self.root, mit_netz=True)}
        self.assertEqual("fund", reg["B0"]["gewicht"])
        self.assertIn("1010", json.dumps(reg["B0"], ensure_ascii=False))
        self.assertNotIn("B1", reg, "nach einer Blockage darf kein Konto-Befund folgen")

    def test_gesunde_antwort_prueft_absender_liste_und_plan(self):
        def gesund(api_key, pfad):
            if pfad == "senders":
                return 200, json.dumps({"senders": [
                    {"email": f"news@{ZONE}", "active": True, "id": 1}]})
            if pfad.startswith("contacts/lists/"):
                return 200, json.dumps({"id": 7, "name": "Blog-Abonnenten",
                                        "totalSubscribers": 512})
            if pfad == "account":
                return 200, json.dumps({"plan": [{"name": "Free",
                                                  "allowSentEmails": 300}]})
            return 200, "{}"
        self.nd.TRANSPORT_GET = gesund
        reg = {r["regel"]: r for r in nz.pruefe_brevo(self.root, mit_netz=True)}
        self.assertEqual("ok", reg["B0"]["gewicht"])
        self.assertEqual("ok", reg["B1"]["gewicht"])
        self.assertEqual("fund", reg["B3"]["gewicht"],
                         "512 Abonnenten über einer 300/Tag-Grenze ist kein grüner Lauf")
        self.assertIn("Plan & Billing", reg["B3"]["weg"])

    def test_themenfeld_ohne_brevo_pfad_wird_gemeldet(self):
        def gesund(api_key, pfad):
            if pfad == "senders":
                return 200, json.dumps({"senders": [
                    {"email": f"news@{ZONE}", "active": True, "id": 1}]})
            return 200, json.dumps({"id": 7, "totalSubscribers": 10})
        self.nd.TRANSPORT_GET = gesund
        reg = {r["regel"]: r for r in nz.pruefe_brevo(self.root, mit_netz=True)}
        self.assertEqual("hinweis", reg["B4"]["gewicht"],
                         "Themen-Chips, die bei Brevo nirgends ankommen, müssen genannt werden")
        # … und schweigt, wenn das Feld nachweislich im Attributpfad liegt
        with open(os.path.join(self.root, "data", "newsletter_studio.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"capture": {"feld_themen": "attributes[THEMEN]"},
                       "email": {"absender": {"email": f"news@{ZONE}"}},
                       "themen": [{"id": "x", "label": "X"}]}, fh)
        reg2 = {r["regel"]: r for r in nz.pruefe_brevo(self.root, mit_netz=True)}
        self.assertNotIn("B4", reg2)

    def test_halt_aus_dem_status_ist_ein_fund(self):
        root = baum({"versand_unklar": {"kampagne_id": 12, "zeitpunkt": "x"}})
        try:
            funde = nz.pruefe_state(root)
            self.assertEqual("fund", funde[0]["gewicht"])
            self.assertIn("versand_unklar", funde[0]["soll"])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class Verdrahtung(unittest.TestCase):
    def test_selbsttest_der_wache(self):
        rc = subprocess.run([sys.executable, os.path.join(SCRIPTS,
                            "newsletter_zustellbarkeit.py"), "--selftest"],
                            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)

    def test_wache_ist_im_governance_minimum(self):
        with open(os.path.join(SCRIPTS, "governance_contract.py"),
                  encoding="utf-8") as fh:
            quelle = fh.read()
        self.assertIn("newsletter_zustellbarkeit.py", quelle,
                      "eine Wache außerhalb des vertraglichen Minimums kann still veralten")

    def test_drei_newsletter_laeufe_ziehen_mit(self):
        with open(os.path.join(ROOT, ".github", "workflows",
                               "newsletter-daily.yml"), encoding="utf-8") as fh:
            workflow = fh.read()
        self.assertIn("newsletter_zustellbarkeit.py --selftest", workflow)
        self.assertIn("newsletter_zustellbarkeit.py --pruefen", workflow)
        self.assertIn("VERSAND-STATUS UNKLAR", workflow,
                      "die dritte Wahrheit (unklar statt fehlgeschlagen) muss in der "
                      "Annotation stehen – sie verbietet den sofortigen zweiten Run")
        self.assertIn("if: ${{ always() && !cancelled() }}", workflow,
                      "der Versandstatus ist der Duplikatsschutz – er muss auch nach "
                      "einem roten Schritt in main landen")

    def test_transport_kennt_seine_kennung(self):
        """Der Transport selbst (nicht nur die Wache) darf nie die
        Bibliotheks-Standardkennung senden – das war Lauf #21."""
        nd = digest_modul()
        for kennung in nd.IDENTITÄTEN:
            self.assertNotIn("Python-urllib", kennung)
        self.assertTrue(nd.kanten_block(403, "error code: 1010"))
        self.assertFalse(nd.kanten_block(401, '{"code":"invalid_api_key"}'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
