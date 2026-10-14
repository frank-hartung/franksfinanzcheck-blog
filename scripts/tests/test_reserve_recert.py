"""Verträge der Zertifikats-Nachführung (Issue #462).

Der Bot-Watchdog meldete täglich „Automatisierung braucht Eingriff“, weil
zwei Zustände niemandem gehörten:

  1. ZERTIFIKATS-DRIFT: Heiler-Läufe (Stilpolitur, Rechtschreibung,
     Pinterest-SEO, Faktenfrische) fassen zertifizierte Reserve-Entwürfe an.
     Das Zertifikat ist bytegebunden – es verfiel, ohne dass es jemand
     erneuerte. Der Bestand sah leer aus, obwohl er voll war.
  2. MESSWERKZEUG-AUSFALL: Eine Nachzertifizierung ohne hunspell hätte den
     kompletten Bestand abgewertet (quality_score wertet fehlende
     Rechtschreibprüfung als 0.5) – ein Werkzeugmangel, der wie ein
     Qualitätseinbruch aussieht.

Beide Klassen werden hier festgenagelt.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reserve_recert as rr  # noqa: E402


def _cert(rows):
    return {"target": 6, "ready": sum(1 for r in rows if r.get("ready")),
            "pool_size": len(rows), "generated_at": "2026-09-29T15:49:57Z",
            "candidates": rows}


class DriftErkennung(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))
        self.posts = self.tmp / "content" / "posts"

    def _draft(self, slug, text="Inhalt"):
        d = self.posts / slug
        d.mkdir(parents=True, exist_ok=True)
        idx = d / "index.md"
        idx.write_text(f"---\ndraft: true\nreserve: true\n---\n{text}\n",
                       encoding="utf-8")
        return idx

    def test_selftest_ist_gruen(self):
        self.assertEqual(rr.selftest(), 0)

    def test_unveraenderter_entwurf_ist_kein_drift(self):
        idx = self._draft("a")
        cert = _cert([{"slug": "a", "ready": True,
                       "sha256": rr.file_digest(idx)}])
        self.assertEqual(rr.drift(cert, {"a": idx}), [])

    def test_heiler_lauf_erzeugt_drift_mit_verursacher(self):
        idx = self._draft("a")
        cert = _cert([{"slug": "a", "ready": True,
                       "sha256": rr.file_digest(idx)}])
        idx.write_text(idx.read_text(encoding="utf-8") + "geheilt\n",
                       encoding="utf-8")
        befunde = rr.drift(cert, {"a": idx})
        self.assertEqual([b["art"] for b in befunde], ["geaendert"])
        self.assertTrue(befunde[0]["ursache"])  # Befund ohne Besitzer = Rauschen

    def test_bericht_nennt_den_bestandsverlust(self):
        text = rr.bericht([{"slug": "a", "art": "geaendert", "ready": True,
                            "ursache": "x"}])
        self.assertIn("NICHT mehr zum Bestand", text)


class MesswerkzeugSicherheit(unittest.TestCase):
    """Eine Nachzertifizierung darf NIE aus Werkzeugmangel abwerten."""

    def test_fehlende_rechtschreibkette_blockiert_das_gate(self):
        with patch.object(rr, "messkette_rechtschreibung",
                          return_value=(False, "hunspell fehlt")):
            with patch("shutil.which", return_value="/usr/bin/hugo"):
                ok, grund = rr.gate_verfuegbar()
        self.assertFalse(ok)
        self.assertIn("hunspell", grund)

    def test_fehlendes_hugo_blockiert_das_gate(self):
        with patch("shutil.which", return_value=None):
            ok, grund = rr.gate_verfuegbar()
        self.assertFalse(ok)
        self.assertIn("hugo", grund)

    def test_vorhandenes_hunspell_ohne_woerterbuch_ist_keine_messkette(self):
        for code, stdout in ((1, ''), (0, ''), (0, 'Haushalt\nFheler\n')):
            with self.subTest(code=code, stdout=stdout), \
                    patch.object(rr.subprocess, 'run',
                                 return_value=rr.subprocess.CompletedProcess(
                                     ['hunspell'], code, stdout, '')):
                ok, grund = rr.messkette_rechtschreibung()
                self.assertFalse(ok)
                self.assertIn('Kontrollwörter', grund)

    def test_echte_kontrollwoerter_und_analyse_ergeben_messkette(self):
        import spellcheck
        with patch.object(rr.subprocess, 'run',
                          return_value=rr.subprocess.CompletedProcess(
                              ['hunspell'], 0, 'Fheler\n', '')), \
                patch.object(spellcheck, 'load_whitelist', return_value=set()), \
                patch.object(spellcheck, 'analyze_article', return_value={}):
            self.assertTrue(rr.messkette_rechtschreibung()[0])

    def test_vollzertifizierung_stoppt_vor_jeder_mutation_bei_werkzeugmangel(self):
        import reserve_readiness
        import reserve_custody
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            snapshot = root / 'data' / 'reserve-readiness.json'
            snapshot.parent.mkdir()
            snapshot.write_bytes(b'{"ready":6}\r\n')
            with patch.object(reserve_readiness, 'ROOT', root), \
                    patch.object(rr, 'gate_verfuegbar',
                                 return_value=(False, 'hunspell fehlt')), \
                    patch.object(reserve_custody, 'heal_quiet') as heal, \
                    patch.object(reserve_readiness.rp, 'reserve_drafts') as drafts:
                self.assertEqual(reserve_readiness.main(), 3)
                heal.assert_not_called()
                drafts.assert_not_called()
            self.assertEqual(snapshot.read_bytes(), b'{"ready":6}\r\n')

    def test_massenabwertung_mit_einem_muster_wird_gestoppt(self):
        alt = _cert([{"slug": s, "ready": True, "sha256": "x"}
                     for s in ("a", "b", "c", "d")])
        neu = [{"slug": s, "ready": False,
                "parts": {"spelling": 0.5, "meta": 1.0, "structure": 1.0}}
               for s in ("a", "b", "c", "d")]
        with self.assertRaises(rr.Abwertungsverdacht):
            rr._abwertungs_bremse(alt, neu)

    def test_echter_qualitaetseinbruch_bleibt_erlaubt(self):
        alt = _cert([{"slug": s, "ready": True, "sha256": "x"}
                     for s in ("a", "b", "c", "d")])
        neu = [
            {"slug": "a", "ready": False, "parts": {"spelling": 0.5, "meta": 1.0}},
            {"slug": "b", "ready": False, "parts": {"spelling": 1.0, "meta": 0.4}},
            {"slug": "c", "ready": True, "parts": {"spelling": 1.0, "meta": 1.0}},
            {"slug": "d", "ready": True, "parts": {"spelling": 1.0, "meta": 1.0}},
        ]
        rr._abwertungs_bremse(alt, neu)  # darf NICHT werfen


class NachzertifizierungMisstNurDasNoetige(unittest.TestCase):
    def test_nur_gedriftete_kandidaten_werden_neu_gemessen(self):
        gemessen = []

        def fake_certify(index):
            gemessen.append(index.parent.name)
            return {"slug": index.parent.name, "ready": True, "sha256": "neu"}

        tmp = Path(self.enterContext(__import__("tempfile").TemporaryDirectory()))
        drafts = {}
        for slug in ("a", "b"):
            d = tmp / slug
            d.mkdir(parents=True)
            (d / "index.md").write_text("x", encoding="utf-8")
            drafts[slug] = d / "index.md"
        cert = _cert([{"slug": "a", "ready": True, "sha256": "alt"},
                      {"slug": "b", "ready": True, "sha256": "alt"}])

        fake_rr = type("M", (), {"certify_one": staticmethod(fake_certify)})
        fake_econ = type("E", (), {"ziel": staticmethod(lambda: 6)})
        with patch.dict(sys.modules, {"reserve_readiness": fake_rr,
                                      "reserve_economy": fake_econ}):
            neu = rr.recertify(cert, drafts, ["a"])
        self.assertEqual(gemessen, ["a"])
        self.assertEqual(neu["recert"]["renewed"], ["a"])
        self.assertEqual(neu["ready"], 2)
        # Die unberührte Zeile bleibt bytegleich erhalten.
        self.assertEqual([r for r in neu["candidates"]
                          if r["slug"] == "b"][0]["sha256"], "alt")

    def test_veroeffentlichte_altlast_faellt_aus_dem_zertifikat(self):
        fake_rr = type("M", (), {"certify_one": staticmethod(
            lambda i: {"slug": "x", "ready": True, "sha256": "n"})})
        fake_econ = type("E", (), {"ziel": staticmethod(lambda: 6)})
        cert = _cert([{"slug": "weg", "ready": True, "sha256": "alt"}])
        with patch.dict(sys.modules, {"reserve_readiness": fake_rr,
                                      "reserve_economy": fake_econ}):
            neu = rr.recertify(cert, {}, [])
        self.assertEqual(neu["candidates"], [])
        self.assertEqual(neu["ready"], 0)


class VerbrauchIstKeinDrift(unittest.TestCase):
    """14.10.2026 (Folgeauftrag aus PR #747): Zwei zertifizierte Entwürfe vom
    07./09.10. gingen am selben Tag über die Quote-Nachfüllung live. Der
    Bericht nannte sie „verschwunden“ und verlangte eine Nachzertifizierung –
    für Artikel, die keine Reserve-Entwürfe mehr sind. Verbrauch wird seither
    erkannt, ehrlich benannt und OHNE Messung ausgebucht."""

    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.posts = self.tmp / "content" / "posts"

    def _post(self, slug, kopf):
        d = self.posts / slug
        d.mkdir(parents=True, exist_ok=True)
        idx = d / "index.md"
        idx.write_text(f"---\ntitle: \"T\"\n{kopf}---\nText\n", encoding="utf-8")
        return idx

    def _live(self, slug):
        return self._post(slug, "draft: false\nreserve_published: 2026-10-14\n")

    def test_veroeffentlichter_entwurf_ist_verbrauch_kein_drift(self):
        self._live("live")
        cert = _cert([{"slug": "live", "ready": True, "sha256": "a" * 64}])
        befunde = rr.drift(cert, {}, posts_dir=self.posts)
        self.assertEqual([b["art"] for b in befunde], ["veroeffentlicht"])
        self.assertIn("2026-10-14", befunde[0]["ursache"])
        text = rr.bericht(befunde)
        self.assertNotIn("NICHT mehr zum Bestand", text)
        self.assertIn("keine Nachzertifizierung", text)

    def test_ohne_verbrauchsmarke_bleibt_es_verschwunden(self):
        # draft: false allein ist kein belegter Verbrauch (z. B. Handarbeit).
        self._post("ohne-marke", "draft: false\n")
        cert = _cert([{"slug": "ohne-marke", "ready": True, "sha256": "a" * 64},
                      {"slug": "geloescht", "ready": True, "sha256": "b" * 64}])
        arten = {b["slug"]: b["art"] for b in rr.drift(cert, {}, posts_dir=self.posts)}
        self.assertEqual(arten, {"ohne-marke": "verschwunden", "geloescht": "verschwunden"})

    def test_geaenderter_entwurf_bleibt_messpflichtig(self):
        idx = self._post("entwurf", "draft: true\nreserve: true\n")
        cert = _cert([{"slug": "entwurf", "ready": True, "sha256": "c" * 64}])
        befunde = rr.drift(cert, {"entwurf": idx}, posts_dir=self.posts)
        self.assertEqual([b["art"] for b in befunde], ["geaendert"])
        self.assertIn("NICHT mehr zum Bestand", rr.bericht(befunde))

    def test_ausbuchung_verjuengt_keinen_nachweis(self):
        self._live("live")
        idx = self._post("bleibt", "draft: true\nreserve: true\n")
        bleibt = {"slug": "bleibt", "ready": True, "sha256": rr.file_digest(idx),
                  "measured_at": "2026-10-13T08:00:00Z"}
        cert = _cert([{"slug": "live", "ready": True, "sha256": "a" * 64}, bleibt])
        cert["measurement"] = {"kind": "full"}
        drafts = {"bleibt": idx}
        neu = rr.ausbuchen(cert, drafts, rr.drift(cert, drafts, posts_dir=self.posts))
        self.assertEqual([r["slug"] for r in neu["candidates"]], ["bleibt"])
        self.assertEqual(neu["candidates"][0], bleibt)          # bytegleich
        self.assertEqual((neu["ready"], neu["pool_size"]), (1, 1))
        self.assertEqual(neu["generated_at"], cert["generated_at"])
        self.assertEqual(neu["measurement"], {"kind": "full"})
        self.assertEqual(neu["ausgebucht"]["slugs"], ["live"])
        self.assertNotIn("recert", neu)    # keine Messung behauptet

    def test_nichts_auszubuchen_ergibt_none(self):
        idx = self._post("bleibt", "draft: true\nreserve: true\n")
        cert = _cert([{"slug": "bleibt", "ready": True, "sha256": rr.file_digest(idx)}])
        self.assertIsNone(rr.ausbuchen(cert, {"bleibt": idx}, []))

    def _main(self, cert, argv, gate=(False, "hunspell fehlt")):
        ziel = self.tmp / "data" / "reserve-readiness.json"
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(cert), encoding="utf-8")
        with patch.object(rr, "ROOT", self.tmp), \
                patch.object(rr, "CERT", ziel), \
                patch.object(rr, "load_cert", lambda *a, **k: json.loads(ziel.read_text())), \
                patch.object(rr, "draft_paths", lambda *a, **k: {}), \
                patch.object(rr, "gate_verfuegbar", lambda: gate):
            code = rr.main(argv)
        return code, json.loads(ziel.read_text(encoding="utf-8"))

    def test_reiner_verbrauch_ist_im_check_gruen(self):
        self._live("live")
        cert = _cert([{"slug": "live", "ready": True, "sha256": "a" * 64}])
        code, danach = self._main(cert, ["--check"])
        self.assertEqual(code, 0)
        self.assertEqual(danach, cert)       # --check schreibt nie

    def test_fix_bucht_ohne_messkette_aus(self):
        # Kein hunspell, kein hugo – die Ausbuchung braucht beides nicht.
        self._live("live")
        cert = _cert([{"slug": "live", "ready": True, "sha256": "a" * 64}])
        code, danach = self._main(cert, ["--fix"])
        self.assertEqual(code, 0)
        self.assertEqual(danach["candidates"], [])
        self.assertEqual(danach["ready"], 0)
        self.assertEqual(danach["generated_at"], cert["generated_at"])

    def test_messpflicht_bleibt_ohne_messkette_exit_3(self):
        # Ausbuchung läuft, die echte Nachmessung aber NICHT ohne Werkzeug.
        self._live("live")
        cert = _cert([{"slug": "live", "ready": True, "sha256": "a" * 64}])
        idx = self._post("neu", "draft: true\nreserve: true\n")
        ziel = self.tmp / "data" / "reserve-readiness.json"
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(cert), encoding="utf-8")
        with patch.object(rr, "ROOT", self.tmp), \
                patch.object(rr, "CERT", ziel), \
                patch.object(rr, "load_cert", lambda *a, **k: json.loads(ziel.read_text())), \
                patch.object(rr, "draft_paths", lambda *a, **k: {"neu": idx}), \
                patch.object(rr, "gate_verfuegbar", lambda: (False, "hunspell fehlt")):
            code = rr.main(["--fix"])
        danach = json.loads(ziel.read_text(encoding="utf-8"))
        self.assertEqual(code, 3)
        self.assertEqual(danach["candidates"], [])         # ausgebucht
        self.assertNotIn("recert", danach)                  # nichts erfunden


if __name__ == "__main__":
    unittest.main()
