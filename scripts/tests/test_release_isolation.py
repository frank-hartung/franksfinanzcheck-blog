#!/usr/bin/env python3
"""Vertragstests für scripts/release_isolation.py (Dauerheilung Issue #676).

GEPRÜFTER VERTRAG
-----------------
Ein blockierter Kandidat darf nicht die komplette öffentliche Auslieferung
einfrieren. Am 09.10.2026 tat er es: 13 Deploy-Fehlschläge in Folge, 42
Live-Artikel auf dem Vortagsstand eingefroren, der neueste Artikel HTTP 404.

Isolation heißt dabei NICHT „Gate abschalten":
  · der blockierte Artikel geht weiterhin nicht live (hold, nie park),
  · der Grund steht im Frontmatter (sichtbar, nie automatisch zurückgeholt),
  · gemessen wird über dieselbe Scorecard-Engine (keine zweite Messregel),
  · Werkzeugfehler werden nicht „isoliert" (fail-closed, C33),
  · der Deploy-Schritt reicht den Exit-Code durch (kein `|| true`).
"""

from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import release_isolation as ri

DEPLOY_YML = ROOT / ".github" / "workflows" / "deploy.yml"


def ergebnis(*, kandidaten, urteile, befunde=None):
    """Kunstbefund in der Form von release_scorecard.durchfuehren()."""
    befunde = befunde or {}
    return {
        "kandidaten": list(kandidaten),
        "artikel": {slug: {"urteil": urteile[slug],
                           "befunde": befunde.get(slug, [])}
                    for slug in urteile},
    }


BLOCK_BEFUND = [{"check": "RD1-duplikate", "wirkung": "blockiert",
                 "detail": "D3-X: Absatz wortgleich in 2 Artikeln",
                 "ausnahme": False, "werkzeugfehler": False}]
WARN_BEFUND = [{"check": "T1w-zeichenlaenge-optimum", "wirkung": "warnung",
                "detail": "unter Optimum (10.386 Zeichen)",
                "ausnahme": False, "werkzeugfehler": False}]
AUSNAHME_BEFUND = [{"check": "A2-intent", "wirkung": "blockiert",
                    "detail": "freigegeben", "ausnahme": True,
                    "werkzeugfehler": False}]
UNBEWEISBAR_BEFUND = [{"check": "T7-render-beweis", "wirkung": "blockiert",
                       "detail": "Artikel fehlt im Build",
                       "ausnahme": False, "werkzeugfehler": True}]


class AuswahlTests(unittest.TestCase):
    """Wer isoliert wird – und wer nicht."""

    def test_nur_blockiert_und_unbeweisbar(self):
        erg = ergebnis(
            kandidaten=["gruen", "rot", "unbeweisbar", "warnung"],
            urteile={"gruen": "freigabe-reif", "rot": "blockiert",
                     "unbeweisbar": "nicht beweisbar", "warnung": "warnung"},
            befunde={"rot": BLOCK_BEFUND, "unbeweisbar": UNBEWEISBAR_BEFUND,
                     "warnung": WARN_BEFUND})
        self.assertEqual(set(ri.blockierte_kandidaten(erg)),
                         {"rot", "unbeweisbar"})

    def test_warnung_ist_kein_isolationsgrund(self):
        """Sonst würde jede Optimum-Warnung den Bestand zurückstellen."""
        erg = ergebnis(kandidaten=["w"], urteile={"w": "warnung"},
                       befunde={"w": WARN_BEFUND})
        self.assertEqual(ri.blockierte_kandidaten(erg), {})

    def test_nicht_kandidaten_werden_nicht_isoliert(self):
        """Der Live-Bestand außerhalb des Tages-Scope bleibt unangetastet."""
        erg = ergebnis(kandidaten=["k"],
                       urteile={"k": "freigabe-reif", "alt": "blockiert"},
                       befunde={"alt": BLOCK_BEFUND})
        self.assertEqual(ri.blockierte_kandidaten(erg), {})

    def test_ssot_ausnahme_ist_kein_grund(self):
        """Eine menschliche Freigabe darf die Isolation nicht fortschreiben."""
        erg = ergebnis(kandidaten=["a"], urteile={"a": "blockiert"},
                       befunde={"a": AUSNAHME_BEFUND})
        gründe = ri.blockierte_kandidaten(erg).get("a", [])
        self.assertFalse(any("A2-intent" in g for g in gründe))

    def test_blockiert_ohne_detail_bekommt_trotzdem_grund(self):
        """Ein leerer cadence_grund macht den Zustand wieder mehrdeutig (#129)."""
        erg = ergebnis(kandidaten=["x"], urteile={"x": "blockiert"},
                       befunde={"x": []})
        gründe = ri.blockierte_kandidaten(erg).get("x") or []
        self.assertTrue(gründe and gründe[0].strip())

    def test_grund_traegt_check_id_und_ist_yaml_sicher(self):
        lang = ri.grund_text("x", ["RD1-duplikate: " + "y" * 900])
        self.assertNotIn("\n", lang)
        self.assertLessEqual(len(lang), 400)
        self.assertIn("RD1-duplikate", lang)
        self.assertIn("#676", lang)


class GriffTests(unittest.TestCase):
    """hold, nicht park – und niemals Inhalt."""

    def test_trockenlauf_schreibt_nichts(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "posts" / "a" / "index.md"
            pfad.parent.mkdir(parents=True)
            pfad.write_text("---\ntitle: t\ndraft: false\n---\n\nText.",
                            encoding="utf-8")
            vorher = pfad.read_text(encoding="utf-8")
            with patch.object(ri, "POSTS", Path(tmp) / "posts"):
                self.assertTrue(ri.isoliere("a", ["RD1: Fund"], trockenlauf=True))
            self.assertEqual(pfad.read_text(encoding="utf-8"), vorher)

    def test_hold_setzt_draft_und_grund_ohne_body_aenderung(self):
        body = "Der redaktionelle Text bleibt unangetastet, egal was passiert."
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "posts" / "a" / "index.md"
            pfad.parent.mkdir(parents=True)
            pfad.write_text(f'---\ntitle: t\ndraft: false\n---\n\n{body}',
                            encoding="utf-8")
            with patch.object(ri, "POSTS", Path(tmp) / "posts"):
                self.assertTrue(ri.isoliere("a", BLOCK_BEFUND[0]["detail"]
                                            and ["RD1-duplikate: D3-X"]))
            inhalt = pfad.read_text(encoding="utf-8")
        self.assertIn("draft: true", inhalt)
        self.assertIn("cadence_grund", inhalt)
        self.assertNotIn("cadence_wait: true", inhalt)   # hold, nicht park
        self.assertIn(body, inhalt)                      # kein Content-Verlust

    def test_fehlender_artikel_ist_kein_stiller_erfolg(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(ri, "POSTS", Path(tmp) / "posts"):
                self.assertFalse(ri.isoliere("gibt-es-nicht", ["RD1: x"]))


class KonvergenzTests(unittest.TestCase):
    """Begrenzte Runden, ehrliche Exit-Codes."""

    def test_gruener_scope_isoliert_nichts(self):
        erg = ergebnis(kandidaten=["g"], urteile={"g": "freigabe-reif"})
        with patch.object(ri, "verdict", return_value=(ri.EXIT_OK, erg)):
            self.assertEqual(ri.lauf(runden=3), ri.EXIT_OK)

    def test_werkzeugfehler_wird_nicht_isoliert(self):
        """Eine ausgefallene Messung ist kein Grün – und kein Inhalt (C33)."""
        erg = ergebnis(kandidaten=["k"], urteile={"k": "nicht beweisbar"},
                       befunde={"k": UNBEWEISBAR_BEFUND})
        erg["tool_fehler"] = {"A1-link-integritaet": "public/ fehlt"}
        with patch.object(ri, "verdict", return_value=(ri.EXIT_WERKZEUGFEHLER, erg)):
            with patch.object(ri, "isoliere") as isoliert:
                code = ri.lauf(runden=3)
        self.assertEqual(code, ri.EXIT_WERKZEUGFEHLER)
        isoliert.assert_not_called()

    def test_isolation_konvergiert_ueber_runden(self):
        """Runde 1 rot → Kandidat auf hold → Runde 2 grün → Exit 0."""
        rot = ergebnis(kandidaten=["k"], urteile={"k": "blockiert"},
                       befunde={"k": BLOCK_BEFUND})
        gruen = ergebnis(kandidaten=[], urteile={})
        with patch.object(ri, "verdict",
                          side_effect=[(ri.EXIT_BLOCKIERT, rot),
                                       (ri.EXIT_OK, gruen)]):
            with patch.object(ri, "isoliere", return_value=True) as isoliert:
                with patch.object(ri, "quote_nachfuellen", return_value=[]):
                    with patch.object(ri, "neu_bauen", return_value=True) as bau:
                        code = ri.lauf(runden=3)
        self.assertEqual(code, ri.EXIT_OK)
        isoliert.assert_called_once()
        bau.assert_called_once()

    def test_dauerrot_bleibt_rot(self):
        """Kein Still-Schalter: nach allen Runden Exit 1, nicht Exit 0."""
        rot = ergebnis(kandidaten=["k"], urteile={"k": "blockiert"},
                       befunde={"k": BLOCK_BEFUND})
        with patch.object(ri, "verdict", return_value=(ri.EXIT_BLOCKIERT, rot)):
            with patch.object(ri, "isoliere", return_value=True):
                with patch.object(ri, "quote_nachfuellen", return_value=[]):
                    with patch.object(ri, "neu_bauen", return_value=True):
                        code = ri.lauf(runden=2)
        self.assertEqual(code, ri.EXIT_BLOCKIERT)

    def test_isolationsobergrenze_bremst_strukturelle_funde(self):
        """Nicht den ganzen Vorrat leer räumen, während der Deploy wartet."""
        slugs = [f"k{i}" for i in range(ri.MAX_ISOLATIONEN_PRO_LAUF + 3)]
        rot = ergebnis(kandidaten=slugs,
                       urteile={s: "blockiert" for s in slugs},
                       befunde={s: BLOCK_BEFUND for s in slugs})
        with patch.object(ri, "verdict", return_value=(ri.EXIT_BLOCKIERT, rot)):
            with patch.object(ri, "isoliere", return_value=True) as isoliert:
                with patch.object(ri, "quote_nachfuellen", return_value=[]):
                    with patch.object(ri, "neu_bauen", return_value=True):
                        code = ri.lauf(runden=1)
        self.assertEqual(code, ri.EXIT_BLOCKIERT)
        self.assertLessEqual(isoliert.call_count, ri.MAX_ISOLATIONEN_PRO_LAUF)

    def test_toter_build_stoppt_statt_blind_auszuliefern(self):
        """Ohne Render-Beweis keine zweite Messung (C33)."""
        rot = ergebnis(kandidaten=["k"], urteile={"k": "blockiert"},
                       befunde={"k": BLOCK_BEFUND})
        with patch.object(ri, "verdict", return_value=(ri.EXIT_BLOCKIERT, rot)):
            with patch.object(ri, "isoliere", return_value=True):
                with patch.object(ri, "quote_nachfuellen", return_value=[]):
                    with patch.object(ri, "neu_bauen", return_value=False):
                        code = ri.lauf(runden=3)
        self.assertEqual(code, ri.EXIT_WERKZEUGFEHLER)

    def test_selftest_des_moduls_ist_gruen(self):
        with patch.dict("os.environ", {"FF_ISOLATION_OHNE_BUILD": "1"}):
            self.assertEqual(ri.run_selftest(), [])


class DeployVerdrahtungTests(unittest.TestCase):
    """Die Kette muss den Vertrag halten, nicht nur das Modul."""

    def setUp(self):
        self.text = DEPLOY_YML.read_text(encoding="utf-8")

    def test_isolation_laeuft_vor_der_finalen_scorecard(self):
        iso = self.text.index("release_isolation.py --commit-sha")
        scorecard = self.text.index(
            'release_scorecard.py --kandidaten --commit-sha "$GITHUB_SHA"\n          status=$?')
        self.assertLess(iso, scorecard,
                        "Isolation muss VOR der finalen Scorecard laufen, "
                        "sonst friert der Deploy weiter ein (#676)")

    def test_isolation_laeuft_nach_dem_ersten_build(self):
        """Render-Beweise brauchen public/ – die Isolation misst ja mit."""
        build = self.text.index("Produktions-Build (Publish-Gate)")
        iso = self.text.index("release_isolation.py --commit-sha")
        self.assertLess(build, iso)

    def test_kein_still_schalter(self):
        for zeile in self.text.splitlines():
            if "release_isolation.py" in zeile:
                self.assertNotIn("|| true", zeile)
                self.assertNotIn("continue-on-error", zeile)

    def test_exit_code_wird_durchgereicht(self):
        self.assertIn('exit "$iso"', self.text)

    def test_selbsttest_blockiert_den_einsatz(self):
        """Eine sabotierte Isolation darf nicht blind greifen."""
        self.assertIn("release_isolation.py --selftest", self.text)


if __name__ == "__main__":
    unittest.main()
