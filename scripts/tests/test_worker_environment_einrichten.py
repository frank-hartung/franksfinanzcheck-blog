#!/usr/bin/env python3
"""Vertragstests des Einrichtungswegs für das Produktions-Environment (WF-829B / #922, 30.10.2026).

Jeder Test läuft offline. Der Netzweg wird ausschließlich über die injizierte
Testgrenze `transport=` geprüft; die Endpunkt-Grenzen werden zusätzlich am
Quelltext festgenagelt, damit ein zweiter Weg nicht unbemerkt dazukommt.
"""
from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import worker_environment_einrichten as einrichten  # noqa: E402
import worker_environment_guard as guard  # noqa: E402

REPO = "frank-hartung/franksfinanzcheck-blog"
TOKEN = "GIFT_GITHUB_TOKEN_NEVER_LOG"
UMGEBUNG = einrichten.UMGEBUNG
REVIEWER = {"type": "User", "reviewer": {"id": 42, "login": "frank-hartung"}}

SICHER = {
    "protection_rules": [{"type": "required_reviewers", "reviewers": [REVIEWER]}],
    "can_admins_bypass": False,
    "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True},
}
REGELN_MAIN = [{"name": "main", "type": "branch"}]
LIVE_HEUTE = {"protection_rules": [], "can_admins_bypass": True, "deployment_branch_policy": None}


def antwort(status: int, body: object, kopf: dict | None = None):
    return status, kopf or {}, json.dumps(body).encode("utf-8")


class Transport:
    """Aufzeichnender Netzersatz: jeder Aufruf bleibt nachweisbar."""

    def __init__(self, umgebung=None, regeln=None, schreiben=200):
        self.umgebung = LIVE_HEUTE if umgebung is None else umgebung
        self.regeln = [] if regeln is None else regeln
        self.schreiben = schreiben
        self.rufe: list[tuple[str, str, object]] = []

    def __call__(self, methode, url, token, koerper):
        self.rufe.append((methode, url, json.loads(json.dumps(koerper))
                          if koerper is not None else None))
        if methode == "GET":
            if url.endswith("/deployment-branch-policies?per_page=100"):
                return antwort(200, {"total_count": len(self.regeln),
                                     "branch_policies": self.regeln})
            return antwort(200, self.umgebung)
        return antwort(self.schreiben, {})

    @property
    def koerper(self) -> list[object]:
        return [k for m, _u, k in self.rufe if m != "GET"]

    @property
    def texte(self) -> str:
        return json.dumps(self.koerper)


class Zielzustand(unittest.TestCase):
    def test_sicheres_environment_ist_vollstaendig_erfuellt(self):
        lagen = einrichten.planen(SICHER, REGELN_MAIN)
        self.assertEqual([l.klasse for l in lagen], [einrichten.KLASSE_ERFUELLT] * 3)
        self.assertEqual(einrichten.ZIELE, tuple(l.ziel for l in lagen))

    def test_heutiger_live_stand_zwei_machbar_eins_nur_oberflaeche(self):
        klassen = {l.ziel: l.klasse for l in einrichten.planen(LIVE_HEUTE, None)}
        self.assertEqual(klassen, {"reviewer": einrichten.KLASSE_MACHBAR,
                                   "bypass": einrichten.KLASSE_OBERFLAECHE,
                                   "branch": einrichten.KLASSE_MACHBAR})

    def test_admin_bypass_ist_niemals_machbar(self):
        for daten in ({**SICHER, "can_admins_bypass": True},
                      {**SICHER, "can_admins_bypass": None}, LIVE_HEUTE):
            with self.subTest(daten=daten):
                lage = next(l for l in einrichten.planen(daten, REGELN_MAIN)
                            if l.ziel == "bypass")
                self.assertEqual(lage.klasse, einrichten.KLASSE_OBERFLAECHE)
                self.assertIn("Dashboard", lage.massnahme)


class Wortschatzvertrag(unittest.TestCase):
    """Das Gate bleibt die einzige Quelle der Wahrheit – seine Sprache auch."""

    def test_jede_abweichung_des_gates_ist_einem_ziel_zugeordnet(self):
        faelle = [
            ({"protection_rules": [], "can_admins_bypass": True,
              "deployment_branch_policy": None}, None),
            ({**SICHER, "protection_rules": [{"type": "required_reviewers",
                                              "reviewers": []}]}, REGELN_MAIN),
            ({**SICHER, "protection_rules": []}, REGELN_MAIN),
            ({**SICHER, "protection_rules": [{"type": "required_reviewers",
                                              "reviewers": [{"type": "Bot", "id": 5}]}]},
             REGELN_MAIN),
            ({**SICHER, "can_admins_bypass": True}, REGELN_MAIN),
            ({**SICHER, "deployment_branch_policy": None}, None),
            ({**SICHER, "deployment_branch_policy": {"protected_branches": True,
                                                     "custom_branch_policies": False}}, None),
            (SICHER, [{"name": "main", "type": "branch"}, {"name": "release/*",
                                                           "type": "branch"}]),
            (SICHER, [{"name": "main", "type": "tag"}]),
            (SICHER, None),
            ("kein Objekt", None),
        ]
        for daten, regeln in faelle:
            with self.subTest(daten=daten if not isinstance(daten, str) else "Text"):
                for text in guard.abweichungen(daten, regeln):
                    self.assertNotEqual(einrichten.zuordnen(text), "unbekannt",
                                        f"Abweichung ohne Ziel: {text}")

    def test_unbekannter_text_wird_offen_gemeldet_und_nicht_angeschrieben(self):
        with patch.object(einrichten, "zuordnen", return_value="unbekannt"):
            lagen = einrichten.planen(LIVE_HEUTE, None)
        offen = [l for l in lagen if l.klasse == einrichten.KLASSE_UNBEKANNT]
        self.assertTrue(offen)
        self.assertIn("Dashboard", offen[0].massnahme) or self.assertIn(
            "prüfen", offen[0].massnahme)


class Endpunktgrenzen(unittest.TestCase):
    def test_nur_api_github_com_und_nur_vier_pfade(self):
        erlaubt = [
            f"https://api.github.com/repos/{REPO}/environments/{UMGEBUNG}",
            f"https://api.github.com/repos/{REPO}/environments/{UMGEBUNG}"
            "/deployment-branch-policies?per_page=100",
            f"https://api.github.com/repos/{REPO}/environments/{UMGEBUNG}"
            "/deployment-branch-policies?page=2&per_page=100",
            f"https://api.github.com/users/frank-hartung",
            f"https://api.github.com/repos/{REPO}/environments?per_page=100",
        ]
        for url in erlaubt:
            with self.subTest(url=url):
                einrichten._art(url, repo=REPO)

    def test_alles_andere_wird_abgewiesen(self):
        verboten = [
            "https://example.invalid/x",
            "http://api.github.com/repos/a/b/environments/" + UMGEBUNG,
            f"https://api.github.com/repos/andere/andere/environments/{UMGEBUNG}",
            f"https://api.github.com/repos/{REPO}/environments/backup",
            f"https://api.github.com/repos/{REPO}/environments/{UMGEBUNG}/secrets",
            f"https://api.github.com/repos/{REPO}/environments/{UMGEBUNG}"
            "/deployment-branch-policies/17",
            f"https://api.github.com/repos/{REPO}/environments/{UMGEBUNG}?per_page=100",
            f"https://api.github.com/repos/{REPO}/environments/{UMGEBUNG}#frag",
            f"https://api.github.com/users/has space",
            f"https://api.github.com/users/",
        ]
        for url in verboten:
            with self.subTest(url=url):
                with self.assertRaises(einrichten.WerkzeugFehler):
                    einrichten._art(url, repo=REPO)

    def test_loeschen_ist_ausgeschlossen(self):
        for methode in ("DELETE", "PATCH", "POST"):
            with self.subTest(methode=methode):
                with self.assertRaises(einrichten.WerkzeugFehler):
                    einrichten._senden(methode,
                                       f"https://api.github.com/repos/{REPO}"
                                       f"/environments/{UMGEBUNG}", TOKEN, repo=REPO)
        with self.assertRaises(einrichten.WerkzeugFehler):
            einrichten._senden("PUT", f"https://api.github.com/repos/{REPO}"
                                      f"/environments/{UMGEBUNG}"
                                      "/deployment-branch-policies", TOKEN, repo=REPO)

    def test_lesender_aufruf_traegt_keinen_koerper(self):
        with self.assertRaises(einrichten.WerkzeugFehler):
            einrichten._senden("GET", f"https://api.github.com/repos/{REPO}"
                                      f"/environments/{UMGEBUNG}", TOKEN, repo=REPO,
                               koerper={"reviewers": []})


class NurVerschaerfen(unittest.TestCase):
    def test_bestehende_reviewer_bleiben_und_der_neue_kommt_dazu(self):
        daten = {"protection_rules": [
            {"type": "required_reviewers", "reviewers": [{"type": "User",
                                                          "reviewer": {"id": 7}}]},
            {"type": "required_reviewers", "reviewers": [{"type": "Team",
                                                          "reviewer": {"id": 8}}]},
        ], "can_admins_bypass": True, "deployment_branch_policy": None}
        transport = Transport(umgebung=daten)
        lagen = einrichten.planen(daten, None)
        einrichten.schreiben(lagen, daten, repo=REPO, token=TOKEN, reviewer_id=42,
                             transport=transport)
        koerper = next(k for k in transport.koerper if isinstance(k, dict)
                       and "reviewers" in k)
        self.assertEqual({(e["type"], e["id"]) for e in koerper["reviewers"]},
                         {("User", 7), ("Team", 8), ("User", 42)})

    def test_schreiben_setzt_nie_bypass_wartezeit_oder_selbstfreigabe(self):
        transport = Transport(umgebung=LIVE_HEUTE)
        einrichten.schreiben(einrichten.planen(LIVE_HEUTE, None), LIVE_HEUTE,
                             repo=REPO, token=TOKEN, reviewer_id=42, transport=transport)
        for verboten in ("can_admins_bypass", "wait_timer", "prevent_self_review"):
            with self.subTest(verboten=verboten):
                self.assertNotIn(verboten, transport.texte)

    def test_branch_regel_wird_ergaenzt_nicht_ersetzt(self):
        transport = Transport(umgebung=LIVE_HEUTE)
        einrichten.schreiben(einrichten.planen(LIVE_HEUTE, None), LIVE_HEUTE,
                             repo=REPO, token=TOKEN, reviewer_id=42, transport=transport)
        self.assertIn(("POST", f"https://api.github.com/repos/{REPO}/environments/"
                               f"{UMGEBUNG}/deployment-branch-policies",
                       {"name": "main", "type": "branch"}),
                      [(m, u, k) for m, u, k in transport.rufe if m == "POST"])

    def test_idempotenz_erfuellter_zustand_schreibt_nichts(self):
        transport = Transport(umgebung=SICHER, regeln=REGELN_MAIN)
        lagen, schritte = einrichten.schreiben(
            einrichten.planen(SICHER, REGELN_MAIN), SICHER, repo=REPO, token=TOKEN,
            reviewer_id=42, transport=transport)
        self.assertEqual([m for m, _u, _k in transport.rufe if m != "GET"], [])
        self.assertEqual(schritte, [])

    def test_fehlender_reviewer_ohne_id_ist_ein_werkzeugfehler(self):
        with self.assertRaises(einrichten.WerkzeugFehler):
            einrichten.schreiben(einrichten.planen(LIVE_HEUTE, None), LIVE_HEUTE,
                                 repo=REPO, token=TOKEN, reviewer_id=None,
                                 transport=Transport())

    def test_zusaetzliche_branch_regeln_werden_gemeldet_und_nicht_geloescht(self):
        daten = {**SICHER, "deployment_branch_policy": {"protected_branches": False,
                                                        "custom_branch_policies": True}}
        regeln = [{"name": "main", "type": "branch"}, {"name": "release/*", "type": "branch"}]
        lagen = einrichten.planen(daten, regeln)
        lage = next(l for l in lagen if l.ziel == "branch")
        self.assertEqual(lage.klasse, einrichten.KLASSE_MACHBAR)
        transport = Transport(umgebung=daten, regeln=regeln)
        einrichten.schreiben(lagen, daten, repo=REPO, token=TOKEN, reviewer_id=42,
                             transport=transport)
        self.assertNotIn("DELETE", [m for m, _u, _k in transport.rufe])


class RechteUndStoerung(unittest.TestCase):
    def test_http_403_beim_schreiben_ist_ein_rechtebefund(self):
        transport = Transport(umgebung=LIVE_HEUTE, schreiben=403)
        with self.assertRaises(einrichten.BefundFehler) as ctx:
            einrichten.schreiben(einrichten.planen(LIVE_HEUTE, None), LIVE_HEUTE,
                                 repo=REPO, token=TOKEN, reviewer_id=42,
                                 transport=transport)
        text = str(ctx.exception)
        self.assertIn("Recht", text)
        self.assertIn("Inhaber", text)
        self.assertEqual(ctx.exception.exit_code, 1)

    def test_http_403_beim_lesen_ist_nicht_belegbar(self):
        def verweigert(methode, url, token, koerper):
            return antwort(403, {})

        with self.assertRaises(einrichten.WerkzeugFehler) as ctx:
            einrichten.stand(REPO, TOKEN, transport=verweigert)
        self.assertEqual(ctx.exception.exit_code, 2)
        self.assertIn("Recht", str(ctx.exception))

    def test_umgebung_vorhanden_aber_unerreichbar_ist_klasse_zwei(self):
        def kaputt(methode, url, token, koerper):
            raise OSError("netz weg")

        with self.assertRaises(einrichten.WerkzeugFehler) as ctx:
            einrichten.stand(REPO, TOKEN, transport=kaputt)
        self.assertEqual(ctx.exception.exit_code, 2)

    def test_fehlendes_environment_wird_als_anlegbar_gemeldet(self):
        def vier(methode, url, token, koerper):
            return antwort(404, {})

        umgebung, regeln = einrichten.stand(REPO, TOKEN, transport=vier)
        self.assertIsNone(umgebung)
        self.assertIsNone(regeln)

    def test_antworttexte_erscheinen_in_keiner_meldung(self):
        def body(methode, url, token, koerper):
            return 500, {"x-geheim": "wert"}, b'{"message":"token abc123 ist abgelaufen"}'

        with self.assertRaises(einrichten.WerkzeugFehler) as ctx:
            einrichten.stand(REPO, TOKEN, transport=body)
        self.assertNotIn("abc123", str(ctx.exception))
        self.assertIn("HTTP 500", str(ctx.exception))


class Geheimnisfreiheit(unittest.TestCase):
    def test_bericht_enthält_kein_token_und_kein_feld_mit_werten(self):
        text = einrichten.als_md(einrichten.planen(LIVE_HEUTE, None),
                                 schritte=["Environment geschrieben"])
        self.assertNotIn(TOKEN, text)
        self.assertNotIn("Bearer", text)

    def test_json_ausgabe_enthält_kein_token(self):
        with patch.object(einrichten, "_repo", return_value=REPO), \
             patch.object(einrichten, "_token", return_value=TOKEN), \
             patch.object(einrichten, "stand", return_value=(LIVE_HEUTE, None)):
            puffer = io.StringIO()
            with patch.object(sys, "stdout", puffer):
                code = einrichten.main(["--pruefen", "--json"])
        self.assertEqual(code, 1)
        self.assertNotIn(TOKEN, puffer.getvalue())
        daten = json.loads(puffer.getvalue())
        self.assertEqual(daten["offen"], 3)
        self.assertEqual([l["klasse"] for l in daten["lagen"]],
                         [einrichten.KLASSE_MACHBAR, einrichten.KLASSE_OBERFLAECHE,
                          einrichten.KLASSE_MACHBAR])

    def test_warnstufe_annotiert_als_warnung_statt_fehler(self):
        umgebung = {"GITHUB_KOMMANDOS": "an"}
        with patch.dict("os.environ", umgebung), \
             patch.object(einrichten, "_repo", return_value=REPO), \
             patch.object(einrichten, "_token", return_value=TOKEN), \
             patch.object(einrichten, "stand", return_value=(LIVE_HEUTE, None)):
            for flag, erwartet in (("--warnstufe", "::warning "), (None, "::error ")):
                with self.subTest(flag=flag):
                    puffer = io.StringIO()
                    argumente = ["--pruefen"] + ([flag] if flag else [])
                    with patch.object(sys, "stdout", puffer):
                        code = einrichten.main(argumente)
                    self.assertEqual(code, 1)
                    self.assertIn(erwartet, puffer.getvalue())

    def test_token_wird_nie_ausgegeben_nur_benutzt(self):
        self.assertEqual(einrichten._token({"GITHUB_TOKEN": TOKEN}), TOKEN)
        with self.assertRaises(einrichten.WerkzeugFehler):
            einrichten._token({})
        with self.assertRaises(einrichten.WerkzeugFehler):
            einrichten._token({"GITHUB_TOKEN": "zeile\nzwei"})


class Inventur(unittest.TestCase):
    def test_alle_environments_mit_ihrem_haertungsstand(self):
        def transport(methode, url, token, koerper):
            self.assertEqual(methode, "GET")
            return antwort(200, {"environments": [
                {"name": "cloudflare-produktion", "can_admins_bypass": True,
                 "protection_rules": [], "deployment_branch_policy": None},
                {"name": "github-pages", "can_admins_bypass": False,
                 "protection_rules": [{"type": "required_reviewers", "reviewers": [REVIEWER]}],
                 "deployment_branch_policy": {"protected_branches": False,
                                              "custom_branch_policies": True}},
            ]})

        zeilen = einrichten.inventur(REPO, TOKEN, transport=transport)
        self.assertEqual([z["name"] for z in zeilen],
                         ["cloudflare-produktion", "github-pages"])
        self.assertEqual(zeilen[0], {"name": "cloudflare-produktion", "reviewer": 0,
                                     "bypass": True, "branch_policy": "keine"})
        self.assertEqual(zeilen[1]["reviewer"], 1)
        self.assertFalse(zeilen[1]["bypass"])

    def test_paginierung_wird_vollstaendig_gelesen(self):
        seiten = [
            antwort(200, {"environments": [{"name": "a", "can_admins_bypass": True,
                                            "protection_rules": [],
                                            "deployment_branch_policy": None}]},
                    {"link": f'<https://api.github.com/repos/{REPO}'
                             '/environments?per_page=100&page=2>; rel="next"'}),
            antwort(200, {"environments": [{"name": "b", "can_admins_bypass": False,
                                            "protection_rules": [],
                                            "deployment_branch_policy": None}]}),
        ]
        rufe = []

        def transport(methode, url, token, koerper):
            rufe.append(url)
            return seiten[len(rufe) - 1]

        zeilen = einrichten.inventur(REPO, TOKEN, transport=transport)
        self.assertEqual([z["name"] for z in zeilen], ["a", "b"])
        self.assertEqual(len(rufe), 2)


class Verdrahtung(unittest.TestCase):
    WORKFLOW = ROOT / ".github" / "workflows" / "sicherheits-wache.yml"

    def test_sicherheits_wache_prueft_skript_und_vertrag_in_beiden_listen(self):
        text = self.WORKFLOW.read_text(encoding="utf-8")
        push, pull = text.split("  pull_request:\n", 1)
        for teil, name in ((push, "push"), (pull, "pull_request")):
            with self.subTest(teil=name):
                self.assertIn("scripts/worker_environment_einrichten.py", teil)
                self.assertIn("scripts/tests/test_worker_environment_einrichten.py", teil)

    def test_selbsttest_laeuft_ohne_netz(self):
        self.assertEqual(einrichten._selftest(), 0)

    def test_ki_transportweg_kennt_die_ausnahme(self):
        quelle = (ROOT / "scripts" / "ki_transportweg.py").read_text(encoding="utf-8")
        self.assertIn('Path("scripts/worker_environment_einrichten.py")', quelle)

    def test_nur_api_github_com_im_quelltext(self):
        quelle = (ROOT / "scripts" / "worker_environment_einrichten.py").read_text(
            encoding="utf-8")
        self.assertIn('API = "https://api.github.com"', quelle)
        self.assertNotIn("api.cloudflare.com", quelle)
        self.assertNotIn("api.anthropic.com", quelle)
        # Genau EIN `http://` steht im Skript: die Sabotage-Probe des
        # Selbsttests, die ein unverschlüsseltes API-Ziel abweisen muss.
        self.assertEqual(quelle.count("http://"), 1)


if __name__ == "__main__":
    unittest.main()
