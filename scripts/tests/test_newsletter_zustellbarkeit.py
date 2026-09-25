#!/usr/bin/env python3
"""Unit-Tests: newsletter_zustellbarkeit.py – die DNS/Worker/Resend-Wache.

Hermetisch: `AUFLOESER` (DoH) und `NETZ_RUF` (HTTP) werden gegen ein
gesundes bzw. mutiertes Zonendbild eingespiegelt – kein echtes Netz.
Geprüft wird die WACHE, nicht das Internet: jede Regel muss die mutierte
Situation als Fund melden und die gesunde als Grün – und ohne Messung
gibt es kein Grün („nicht gemessen“ statt stiller Bestätigung).
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ZONE = "beispiel.blog"
ANTWORT_DOMAIN = "antwort.blog"
WERKER_HOST = "abos." + ZONE
WERKER = "https://" + WERKER_HOST


def _load(name: str, rel: str):
    pfad = os.path.join(ROOT, "scripts", rel)
    spec = importlib.util.spec_from_file_location(name, pfad)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


zust = _load("newsletter_zustellbarkeit", "newsletter_zustellbarkeit.py")


def _tmp_root():
    """Temp-Root mit hugo.toml (Zone = baseURL) – kein echtes Repo dabei."""
    td = tempfile.mkdtemp(prefix="zust-")
    open(os.path.join(td, "hugo.toml"), "w", encoding="utf-8").write(
        f'baseURL = "https://{ZONE}/"\n\n[params]\n'
        f'  newsletterFormAction = "{WERKER}/anmeldung"\n')
    os.makedirs(os.path.join(td, "data"), exist_ok=True)
    return td


def _gesunde_zone(mutation: dict | None = None):
    """AUFLOESER-Stub: (name, typ) → (RCode, Antworten).

    RCode 0 = gemessen, 3 = NXDOMAIN, -1 = nicht erreichbar.
    `mutation` überschreibt einzelne Abfragen (z. B. DKIM → NXDOMAIN).
    """
    tabelle = {
        (ZONE, "TXT"): (0, ["v=spf1 include:_spf.mx.cloudflare.net -all"]),
        ("send." + ZONE, "CNAME"): (0, ["send.forge.rmta.net"]),
        ("send." + ZONE, "TXT"): (3, []),
        ("send." + ZONE, "MX"): (3, []),
        ("_dmarc." + ZONE, "TXT"): (0, ["v=DMARC1; p=reject; rua=mailto:post@ex.de"]),
        ("resend._domainkey." + ZONE, "TXT"): (0, ["k=rsa; p=AAAA"]),
        (ZONE, "CNAME"): (0, [WERKER_HOST + ".workers.dev"]),
        (ZONE, "MX"): (0, ["10 mx.ex.de"]),
        (WERKER_HOST, "CNAME"): (0, [WERKER_HOST + ".workers.dev"]),
        (ANTWORT_DOMAIN, "MX"): (0, ["10 mx.antwort.blog"]),
    }
    for schluessel, wert in (mutation or {}).items():
        tabelle[schluessel] = wert

    def stub(name: str, typ: str):
        if (name, typ) in tabelle:
            return tabelle[(name, typ)]
        return 3, []  # NXDOMAIN: alles andere existiert nicht

    return stub


def _netz(*Antworten):
    """NETZ_RUF-Stub: ruft auf, liefert der Reihe nach (code, körper)."""
    warte = list(Antworten)

    def stub(url: str, *, headers: dict | None = None, timeout: int = 15):
        return warte.pop(0) if warte else (0, "stub: keine Antwort mehr vorbereitet")

    return stub


class KantenBlockTest(unittest.TestCase):
    """Der 403-Unterschied: Kante (1010) ≠ Absage des Anbieters."""

    def test_1010_marker_ist_kante(self):
        self.assertTrue(zust.kanten_block(403, 'Error 1010: The owner of this website has blocked...'))

    def test_sigaturtext_ist_kante(self):
        self.assertTrue(zust.kanten_block(403, "Access denied - browser's signature invalid"))

    def test_klarer_403_ist_keine_kante(self):
        self.assertFalse(zust.kanten_block(403, "forbidden"))

    def test_anderer_code_ist_keine_kante(self):
        self.assertFalse(zust.kanten_block(200, "Error 1010"))
        self.assertFalse(zust.kanten_block(0, "whatever"))


class CloudflareRegelnTest(unittest.TestCase):
    """C1–C6: gesunde Zone grün, jede Mutation als Fund sichtbar."""

    def setUp(self):
        self.td = _tmp_root()
        self.echt = zust.AUFLOESER
        self.env = {k: os.environ.get(k) for k in
                    ("NEWSLETTER_MAILZONE", "NEWSLETTER_ABSENDER")}
        for k in self.env:
            os.environ.pop(k, None)
        os.environ["NEWSLETTER_ABSENDER"] = "news@" + ANTWORT_DOMAIN

    def _restore(self):
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def tearDown(self):
        zust.AUFLOESER = self.echt
        self._restore()
        self.teardown_tmp()

    def teardown_tmp(self):
        import shutil
        shutil.rmtree(self.td, ignore_errors=True)

    def _funde(self, mutation: dict | None = None):
        zust.AUFLOESER = _gesunde_zone(mutation)
        funde, _messwerte = zust.pruefe_cloudflare(self.td)
        return {f["regel"]: f for f in funde}

    def test_gesunde_zone_trag_t_gelb_gruen(self):
        r = self._funde()
        for nummer in ("C1", "C2", "C3", "C4", "C5", "C6"):
            self.assertIn(nummer, r, f"Regel {nummer} fehlt")
            self.assertEqual(r[nummer]["gewicht"], "ok",
                             f"{nummer}: {r[nummer]['titel']}")

    def test_kein_spf_ist_fund(self):
        r = self._funde({(ZONE, "TXT"): (0, [])})
        self.assertEqual(r["C1"]["gewicht"], "fund")

    def test_zwei_spf_eintraege_sind_fund(self):
        r = self._funde({(ZONE, "TXT"): (0,
                      ["v=spf1 include:_spf.mx.cloudflare.net -all",
                       "v=spf1 -all"])})
        self.assertEqual(r["C1"]["gewicht"], "fund")

    def test_apex_spf_braucht_kein_resend_include(self):
        # Regression: das alte Modell verlangte include:resend.net an der
        # Spitze – das SES-Modell berührt die Apex-SPF nicht.
        r = self._funde({(ZONE, "TXT"): (0,
                      ["v=spf1 include:_spf.mx.cloudflare.net -all"])})
        self.assertEqual(r["C1"]["gewicht"], "ok")
        self.assertEqual(r["C2"]["gewicht"], "ok")

    def test_send_cname_fehlt_ist_fund_c2(self):
        r = self._funde({("send." + ZONE, "CNAME"): (3, [])})
        self.assertEqual(r["C2"]["gewicht"], "fund")

    def test_send_cname_fremdes_ziel_ist_fund_c2(self):
        r = self._funde({("send." + ZONE, "CNAME"):
                         (0, ["anderes.example.net"])})
        self.assertEqual(r["C2"]["gewicht"], "fund")

    def test_send_ses_ohne_mx_ist_fund_c2(self):
        # SES-Form unvollstaendig: keine CNAME, SPF-TXT da, Bounce-MX fehlt
        r = self._funde({("send." + ZONE, "CNAME"): (3, []),
                         ("send." + ZONE, "TXT"): (0,
                          ["v=spf1 include:amazonses.com ~all"])})
        self.assertEqual(r["C2"]["gewicht"], "fund")

    def test_send_ses_form_ist_ok_c2(self):
        # Altes Modell (SPF-TXT + Bounce-MX direkt auf send.) bleibt gueltig
        r = self._funde({("send." + ZONE, "CNAME"): (3, []),
                         ("send." + ZONE, "TXT"): (0,
                          ["v=spf1 include:amazonses.com ~all"]),
                         ("send." + ZONE, "MX"): (0,
                          ["10 feedback-smtp.us-east-1.amazonses.com"])})
        self.assertEqual(r["C2"]["gewicht"], "ok")

    def test_fehlendes_dkim_ist_fund(self):
        r = self._funde({("resend._domainkey." + ZONE, "TXT"): (3, [])})
        self.assertEqual(r["C3"]["gewicht"], "fund")

    def test_dmarc_ohne_berichtsweg_ist_fund(self):
        r = self._funde({("_dmarc." + ZONE, "TXT"): (0, ["v=DMARC1; p=reject"])})
        self.assertEqual(r["C4"]["gewicht"], "fund")

    def test_dmarc_p_none_widerspricht_dkim_strategie(self):
        r = self._funde({("_dmarc." + ZONE, "TXT"):
                         (0, ["v=DMARC1; p=none; rua=mailto:post@ex.de"])})
        self.assertEqual(r["C4"]["gewicht"], "hinweis")

    def test_kein_mx_ist_fund(self):
        r = self._funde({(ZONE, "MX"): (3, [])})
        self.assertEqual(r["C5"]["gewicht"], "fund")

    def test_absender_domain_ohne_mx_ist_hinweis(self):
        r = self._funde({(ANTWORT_DOMAIN, "MX"): (3, [])})
        self.assertEqual(r["C6"]["gewicht"], "hinweis")

    def test_unerreichbare_dns_ist_kein_gruen(self):
        def tot(name, typ):
            return -1, ["resolver: Timeout"]
        zust.AUFLOESER = tot
        funde, _ = zust.pruefe_cloudflare(self.td)
        gewichte = {f["regel"]: f["gewicht"] for f in funde}
        self.assertNotIn("C1", gewichte)  # C0-Fallback, keine einzelnen Regeln
        self.assertEqual(funde[0]["regel"], "C0")
        self.assertEqual(funde[0]["gewicht"], "nicht messbar")


class WorkerRegelTest(unittest.TestCase):
    """C7: der Hahn der Kette – CNAME, Antwort, Kanten-Block."""

    def setUp(self):
        self.td = _tmp_root()
        self.echt_a, self.echt_n = zust.AUFLOESER, zust.NETZ_RUF
        os.environ.pop("NEWSLETTER_WORKER_BASE", None)
        os.environ.pop("NEWSLETTER_MAILZONE", None)

    def tearDown(self):
        zust.AUFLOESER, zust.NETZ_RUF = self.echt_a, self.echt_n
        import shutil
        shutil.rmtree(self.td, ignore_errors=True)

    def _c7(self, mutation: dict | None = None, antwort=(200, "<html>…</html>")):
        zust.AUFLOESER = _gesunde_zone(mutation)
        zust.NETZ_RUF = _netz(antwort)
        funde = zust.pruefe_worker(self.td, mit_netz=True)
        # Ein lebender Endpunkt bringt seit 25.09.2026 die Takt-Messung (C8)
        # mit; jeder andere Ausgang bleibt ein einzelner C7-Befund.
        assert funde[0]["regel"] == "C7"
        assert len(funde) == (2 if funde[0]["gewicht"] == "ok" else 1)
        return funde[0]

    def _c8(self, koerper: str, jetzt=None):
        return zust.pruefe_taktgeber(koerper, jetzt)

    def test_ohne_netz_kein_gruen(self):
        f = zust.pruefe_worker(self.td, mit_netz=False)
        self.assertEqual(f[0]["regel"], "C7")
        self.assertEqual(f[0]["gewicht"], "nicht gemessen")

    def test_gesunder_endpunkt_lebt(self):
        f = self._c7()
        self.assertEqual((f["regel"], f["gewicht"]), ("C7", "ok"))

    # ---- C8: der Taktgeber (Worker-Cron startet den Digest) ------------
    def _health(self, **digest):
        eintrag = {"ts": "2026-09-25T04:30:06+00:00", "cron": "30 4 * * TUE,FRI",
                   "workflow": "newsletter-daily.yml", "status": "dispatched",
                   "http": 204, "versuche": 1, "warum": None}
        eintrag.update(digest)
        return json.dumps({"ok": True, "kv": "ok",
                           "takt": {"crons": ["30 4 * * TUE,FRI", "5 5 * * TUE,FRI",
                                              "17 * * * *"],
                                    "letzte": {"digest": eintrag}}})

    def test_alter_worker_ohne_takt_ist_fund(self):
        f = self._c8('{"ok": true, "kv": "ok"}')
        self.assertEqual((f["regel"], f["gewicht"]), ("C8", "fund"))
        self.assertIn("wrangler deploy", f["weg"])

    def test_lebender_endpunkt_alter_version_meldet_c7_ok_und_c8_fund(self):
        zust.AUFLOESER = _gesunde_zone(None)
        zust.NETZ_RUF = _netz((200, '{"ok": true, "kv": "ok"}'))
        funde = zust.pruefe_worker(self.td, mit_netz=True)
        self.assertEqual([(f["regel"], f["gewicht"]) for f in funde],
                         [("C7", "ok"), ("C8", "fund")])

    def test_frischer_takt_am_versandtag_ist_ok(self):
        freitag_spaeter = dt.datetime(2026, 9, 25, 9, 0, tzinfo=dt.timezone.utc)
        f = self._c8(self._health(), freitag_spaeter)
        self.assertEqual((f["regel"], f["gewicht"]), ("C8", "ok"))

    def test_verpasster_versandtag_ist_fund(self):
        freitag_spaeter = dt.datetime(2026, 9, 25, 9, 0, tzinfo=dt.timezone.utc)
        f = self._c8(self._health(ts="2026-09-22T04:30:06+00:00"), freitag_spaeter)
        self.assertEqual(f["gewicht"], "fund")
        self.assertIn("verpasst", f["titel"])

    def test_403_nennt_die_pat_berechtigung(self):
        f = self._c8(self._health(status="fehlgeschlagen", http=403, warum="HTTP 403"))
        self.assertEqual(f["gewicht"], "fund")
        self.assertIn("Actions: Read and write", f["soll"])

    def test_nie_gefeuert_vor_dem_ersten_termin_ist_hinweis(self):
        roh = json.loads(self._health())
        roh["takt"]["letzte"] = {}
        f = self._c8(json.dumps(roh))
        self.assertEqual(f["gewicht"], "hinweis")

    def test_kein_json_ist_nicht_messbar(self):
        self.assertEqual(self._c8("<html>Formular</html>")["gewicht"], "nicht messbar")

    def test_faelliger_takt_rechnet_di_fr_mit_zehn_minuten_gnade(self):
        fr_0435 = dt.datetime(2026, 9, 25, 4, 35, tzinfo=dt.timezone.utc)
        fr_0441 = dt.datetime(2026, 9, 25, 4, 41, tzinfo=dt.timezone.utc)
        so = dt.datetime(2026, 9, 27, 12, 0, tzinfo=dt.timezone.utc)
        self.assertEqual(zust.letzter_faelliger_takt(fr_0435).date(), dt.date(2026, 9, 22))
        self.assertEqual(zust.letzter_faelliger_takt(fr_0441).date(), dt.date(2026, 9, 25))
        self.assertEqual(zust.letzter_faelliger_takt(so).date(), dt.date(2026, 9, 25))

    def test_nxdomain_ist_fund(self):
        f = self._c7({(WERKER_HOST, "CNAME"): (3, [])})
        self.assertEqual((f["regel"], f["gewicht"]), ("C7", "fund"))
        self.assertIn("NXDOMAIN", f["ist"])

    def test_keine_antwort_ist_nicht_messbar(self):
        f = self._c7(antwort=(0, "URLError: Timeout"))
        self.assertEqual(f["gewicht"], "nicht messbar")

    def test_kantenblock_ist_fund_mit_erkenntnis(self):
        f = self._c7(antwort=(403, "Error 1010: The owner of this website has blocked..."))
        self.assertEqual(f["gewicht"], "fund")
        self.assertIn("Signaturfilter", f["titel"])

    def test_500_ist_fund(self):
        f = self._c7(antwort=(500, "interner fehler"))
        self.assertEqual(f["gewicht"], "fund")

    def test_ohne_basis_ist_hinweis(self):
        # Wurzel ohne Formulare-Endpunkt (frische Zone, noch kein Worker)
        open(os.path.join(self.td, "hugo.toml"), "w", encoding="utf-8").write(
            f'baseURL = "https://{ZONE}/"\n')
        zust.AUFLOESER = _gesunde_zone()
        f = zust.pruefe_worker(self.td, mit_netz=True)
        self.assertEqual((f[0]["regel"], f[0]["gewicht"]), ("C7", "hinweis"))


class ResendRegelnTest(unittest.TestCase):
    """B0–B3: zwei Systeme (Resend-API, Worker-Export), keine gegenseitige Stummschaltung."""

    def setUp(self):
        self.td = _tmp_root()
        self.echt_a, self.echt_n = zust.AUFLOESER, zust.NETZ_RUF
        self.env = {k: os.environ.get(k) for k in
                    ("RESEND_API_KEY", "NEWSLETTER_RESEND_KEY",
                     "NEWSLETTER_WORKER_BASE", "NEWSLETTER_WORKER_EXPORT_KEY")}
        for k in self.env:
            os.environ.pop(k, None)

    def tearDown(self):
        zust.AUFLOESER, zust.NETZ_RUF = self.echt_a, self.echt_n
        for k, v in self.env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import shutil
        shutil.rmtree(self.td, ignore_errors=True)

    def _b(self, antworten, mit_netz=True):
        zust.AUFLOESER = _gesunde_zone()
        zust.NETZ_RUF = _netz(*antworten)
        funde = zust.pruefe_resend(self.td, mit_netz=mit_netz)
        return {f["regel"]: f for f in funde}

    def test_ohne_netz_kein_gruen(self):
        r = self._b([], mit_netz=False)
        self.assertEqual(r["B0"]["gewicht"], "nicht gemessen")

    def test_b0_key_los_401_ist_info_kein_gruen(self):
        # 401 von api.resend.com = Kante durchlässig, Konto nicht geprüft
        r = self._b([(401, '{"message":"unauthorized"}')])
        self.assertEqual(r["B0"]["gewicht"], "info")

    def test_b0_key_mit_401_ist_fund(self):
        os.environ["RESEND_API_KEY"] = "re_test"
        r = self._b([(401, '{"message":"unauthorized"}')])
        self.assertEqual(r["B0"]["gewicht"], "fund")

    def test_b1_domain_verifiziert(self):
        os.environ["RESEND_API_KEY"] = "re_test"
        antwort = (200, json.dumps(
            {"data": [{"domain": ZONE, "verified": True}]}))
        r = self._b([antwort])
        self.assertEqual(r["B1"]["gewicht"], "ok")

    def test_b1_domain_unverifiziert_ist_fund(self):
        os.environ["RESEND_API_KEY"] = "re_test"
        antwort = (200, json.dumps(
            {"data": [{"domain": ZONE, "verified": False}]}))
        r = self._b([antwort])
        self.assertEqual(r["B1"]["gewicht"], "fund")

    @staticmethod
    def _b1_records(recs):
        return (
            (200, json.dumps({"data": [
                {"domain": ZONE, "id": "dom_test", "verified": True}]})),
            (200, json.dumps({"records": recs})),
        )

    def _b1_rec(self, record, status):
        return {"record": record, "name": "send", "type": "CNAME",
                "status": status}

    def test_b1_records_verifiziert_ist_ok(self):
        os.environ["RESEND_API_KEY"] = "re_test"
        recs = [self._b1_rec("SPF", "verified"),
                self._b1_rec("DKIM", "verified"),
                self._b1_rec("Tracking", "verified")]
        r = self._b(self._b1_records(recs))
        self.assertEqual(r["B1"]["gewicht"], "ok")

    def test_b1_spf_record_offen_ist_fund(self):
        os.environ["RESEND_API_KEY"] = "re_test"
        recs = [self._b1_rec("SPF", "pending"),
                self._b1_rec("DKIM", "verified"),
                self._b1_rec("Tracking", "verified")]
        r = self._b(self._b1_records(recs))
        self.assertEqual(r["B1"]["gewicht"], "fund")

    def test_b1_tracking_offen_ist_nur_hinweis(self):
        # Tracking ist bei uns ausgeschaltet (click_tracking=false)
        os.environ["RESEND_API_KEY"] = "re_test"
        recs = [self._b1_rec("SPF", "verified"),
                self._b1_rec("DKIM", "verified"),
                self._b1_rec("Tracking", "pending")]
        r = self._b(self._b1_records(recs))
        self.assertEqual(r["B1"]["gewicht"], "hinweis")

    def test_b2_ohne_export_key_bleibt_hinweis(self):
        # B0 grün, B2 ungemessen – die zwei Systeme stummschalten einander nicht
        r = self._b([(200, json.dumps({"data": []}))])
        self.assertEqual(r["B2"]["gewicht"], "hinweis")
        self.assertEqual(r["B3"]["gewicht"], "nicht gemessen")

    def test_b2_liste_aus_worker_unabhaengig_von_resend(self):
        os.environ["NEWSLETTER_WORKER_BASE"] = WERKER
        os.environ["NEWSLETTER_WORKER_EXPORT_KEY"] = "export-key"
        netz = _netz(
            (200, json.dumps({"data": [{"domain": ZONE, "verified": True}]})),
            (200, json.dumps({"anzahl": 3, "abonnenten": [
                {"email": "a@b.de", "token": "t1"},
                {"email": "c@d.de", "token": "t2"},
                {"email": "e@f.de", "token": "t3"}]})))
        zust.AUFLOESER = _gesunde_zone()
        zust.NETZ_RUF = netz
        funde = zust.pruefe_resend(self.td, mit_netz=True)
        r = {f["regel"]: f for f in funde}
        self.assertEqual(r["B2"]["gewicht"], "ok")
        self.assertIn("3 aktive", r["B2"]["titel"])
        self.assertEqual(r["B3"]["gewicht"], "ok")  # 3 ≤ 100/Tag

    def test_b2_falscher_key_ist_fund(self):
        os.environ["NEWSLETTER_WORKER_BASE"] = WERKER
        os.environ["NEWSLETTER_WORKER_EXPORT_KEY"] = "falsch"
        r = self._b([(403, "unauthorized")])
        self.assertEqual(r["B2"]["gewicht"], "fund")

    def test_b3_ueber_tagesgrenze_ist_hinweis(self):
        os.environ["NEWSLETTER_WORKER_BASE"] = WERKER
        os.environ["NEWSLETTER_WORKER_EXPORT_KEY"] = "export-key"
        netz = _netz(
            (200, json.dumps({"data": []})),
            (200, json.dumps({"anzahl": 150, "abonnenten": []})))
        zust.AUFLOESER = _gesunde_zone()
        zust.NETZ_RUF = netz
        funde = zust.pruefe_resend(self.td, mit_netz=True)
        r = {f["regel"]: f for f in funde}
        self.assertEqual(r["B3"]["gewicht"], "hinweis")


class StateRegelnTest(unittest.TestCase):
    """S1–S3: der Status im Repo – Halt, Pendende, letzte Ausgabe."""

    def _tmp(self):
        return _tmp_root()

    def test_letzte_ausgabe_bezegt_ok(self):
        td = self._tmp()
        open(os.path.join(td, "data", "newsletter_state.json"), "w").write(
            json.dumps({"letzte_ausgabe": {"datum": "2026-09-22",
                                           "betreff": "Der Wochen-Check",
                                           "transport": "resend"}}))
        r = {f["regel"]: f for f in zust.pruefe_state(td)}
        self.assertEqual(r["S3"]["gewicht"], "ok")

    def test_halt_wird_gemeldet(self):
        td = self._tmp()
        open(os.path.join(td, "data", "newsletter_state.json"), "w").write(
            json.dumps({"versand_unklar": {"kennung": "2026-09-22|Betreff",
                                           "zeitpunkt": "2026-09-22T07:10:00Z"}}))
        r = {f["regel"]: f for f in zust.pruefe_state(td)}
        self.assertEqual(r["S1"]["gewicht"], "fund")

    def test_kaputtes_json_ist_fund(self):
        td = self._tmp()
        open(os.path.join(td, "data", "newsletter_state.json"), "w").write("{kaputt")
        r = {f["regel"]: f for f in zust.pruefe_state(td)}
        self.assertEqual(r["S1"]["gewicht"], "fund")

    def test_noch_kein_versand_ist_hinweis(self):
        td = self._tmp()
        r = {f["regel"]: f for f in zust.pruefe_state(td)}
        self.assertEqual(r["S3"]["gewicht"], "hinweis")


class GesamtlaufTest(unittest.TestCase):
    """`pruefe` + `als_md`: der Lauf als Ganzes."""

    def setUp(self):
        self.td = _tmp_root()
        self.echt_a, self.echt_n = zust.AUFLOESER, zust.NETZ_RUF
        for k in ("RESEND_API_KEY", "NEWSLETTER_RESEND_KEY",
                  "NEWSLETTER_WORKER_BASE", "NEWSLETTER_WORKER_EXPORT_KEY",
                  "NEWSLETTER_MAILZONE", "NEWSLETTER_ABSENDER"):
            os.environ.pop(k, None)
        os.environ["NEWSLETTER_ABSENDER"] = "news@" + ANTWORT_DOMAIN

    def tearDown(self):
        zust.AUFLOESER, zust.NETZ_RUF = self.echt_a, self.echt_n
        import shutil
        shutil.rmtree(self.td, ignore_errors=True)

    def test_vollstaendig_gesund_liefert_rc_0(self):
        os.environ["NEWSLETTER_WORKER_BASE"] = WERKER
        os.environ["NEWSLETTER_WORKER_EXPORT_KEY"] = "k"
        open(os.path.join(self.td, "data", "newsletter_state.json"), "w").write(
            json.dumps({"letzte_ausgabe": {"datum": "2026-09-22", "betreff": "B",
                                           "transport": "resend"}}))
        zust.AUFLOESER = _gesunde_zone()
        zust.NETZ_RUF = _netz(
            (200, "<html>formular</html>"),                 # C7 Endpunkt
            (200, json.dumps({"data": [{"domain": ZONE, "verified": True}]})),  # B0/B1
            (200, json.dumps({"anzahl": 2, "abonnenten": []})))                # B2
        erg = zust.pruefe(self.td, mit_netz=True)
        self.assertEqual(erg["rc"], 0, erg["funde"])
        md = zust.als_md(erg)
        self.assertIn("[C1", md)
        self.assertIn("[C7", md)
        self.assertIn("[B2", md)

    def test_mutierter_lauf_liefert_rc_1(self):
        # Gesundes Zonenbild, aber die API antwortet 500 → B0-Fund → rc 1
        # (mit Key: ein 500er ist eine Aussage, ohne Key wäre es nur „Kante“.)
        os.environ["RESEND_API_KEY"] = "re_test"
        zust.AUFLOESER = _gesunde_zone()
        zust.NETZ_RUF = _netz((200, "<html>formular</html>"), (500, "kaputt"))
        erg = zust.pruefe(self.td, mit_netz=True)
        self.assertEqual(erg["rc"], 1)
        self.assertTrue(any(f["regel"] == "B0" and f["gewicht"] == "fund"
                            for f in erg["funde"]))

    def test_ohne_netz_ist_ehrlich_nicht_gemessen(self):
        erg = zust.pruefe(self.td, mit_netz=False)
        self.assertFalse(erg["gemessen"])
        md = zust.als_md(erg)
        self.assertIn("ohne Netz", md)
        for f in erg["funde"]:
            self.assertNotEqual(f["gewicht"], "ok",
                                f"ohne Netz darf nichts grün sein: {f}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
