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


if __name__ == "__main__":
    unittest.main()
