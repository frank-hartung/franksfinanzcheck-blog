"""Regressionstests des Edge-Freigabe-Werkzeugs (WF-E813 / #809).

Zwei Verträge:

  1. TRANSPORTWEG (Ausgleich für die T6-Ausnahme in scripts/ki_transportweg.py):
     Das Werkzeug spricht die Cloudflare-VERWALTUNGS-API an (Zone, DNS, SSL,
     Transform Rules) – nie ein Modell, nie einen zweiten Anbieter. Genau das
     ist der Handel hinter dem Ausnahmeeintrag: Die Ausnahme gilt nur, solange
     dieser Vertrag sie deckt. Vorbild: test_backup_einrichtung.TransportVertrag
     (Sicherheitsaudit 14.10.2026, M-11).
  2. SELBSTSTAND: Der Selbsttest des Werkzeugs ist grün, der Sollstand kommt
     aus der Vorlage (eine Quelle), und die Werkzeugfehler laufen fail-safe
     (Exit 2, nie „alles im Soll“ ohne Messung).

Ausführung:  python3 -m unittest scripts.tests.test_cloudflare_edge_freigabe -v
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"

import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "_edge_freigabe", SCRIPTS / "cloudflare_edge_freigabe.py")
edge = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(edge)


class TransportVertrag(unittest.TestCase):
    """Ausgleich für die T6-Ausnahme: Verwaltungs-Pfade ja, Modell nie."""

    def test_ausnahme_ist_im_gate_eingetragen(self):
        gate = (SCRIPTS / "ki_transportweg.py").read_text(encoding="utf-8")
        self.assertIn('Path("scripts/cloudflare_edge_freigabe.py")', gate)

    def test_nur_verwaltungspfade_kein_modellaufruf(self):
        quelltext = (SCRIPTS / "cloudflare_edge_freigabe.py").read_text(encoding="utf-8")
        hosts = set(re.findall(r"https://([a-z0-9.-]+)", quelltext))
        self.assertLessEqual(hosts, {"api.cloudflare.com"},
                             f"unerwartete Hosts: {hosts}")
        for verboten in ("/ai/run", "/ai/", "generativelanguage", "api.groq.com",
                         "nvidia", "pollinations", "llm_client",
                         "/chat/completions", "workers.ai"):
            self.assertNotIn(verboten, quelltext,
                             f"Modellbezug im Edge-Werkzeug: {verboten}")
        pfade = set(re.findall(r"_api\(\s*token,\s*f?[\"']([^\"']+)[\"']", quelltext))
        self.assertTrue(pfade, "keine API-Pfade gefunden – der Vertrag wäre blind")
        for pfad in pfade:
            self.assertTrue(pfad.startswith("/zones"),
                            f"Pfad ausserhalb der Zonen-Verwaltung: {pfad}")

    def test_kein_schreibzugriff_ohne_apply(self):
        """--pruefen (Standard) darf nur GET senden; Schreiben hängt an --apply."""
        quelltext = (SCRIPTS / "cloudflare_edge_freigabe.py").read_text(encoding="utf-8")
        self.assertIn('parser.add_argument("--apply"', quelltext)
        # PATCH/POST/PUT tauchen nur in anwenden() auf – und das Skript
        # verzweigt dort ausschliesslich auf --apply.
        self.assertIn("anwenden if args.apply else pruefen", quelltext)


class Selbststand(unittest.TestCase):
    """Der Sollstand hat eine Quelle, und der Selbsttest deckt die Fehlerfälle."""

    def test_selbsttest_gruen(self):
        self.assertEqual(edge.selftest(), 0)

    def test_sollstand_kommt_aus_der_vorlage(self):
        kopfzeilen = edge.vorlage_kopfzeilen()
        self.assertEqual(len(kopfzeilen), 8)
        namen = [n for n, _ in kopfzeilen]
        self.assertIn("Strict-Transport-Security", namen)
        self.assertIn("Content-Security-Policy", namen)

    def test_ohne_token_ist_explizit_nichts_behauptet(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "cloudflare_edge_freigabe.py"), "--pruefen"],
            capture_output=True, text=True, timeout=30,
            env={"PATH": "/usr/bin:/bin", "HOME": "/tmp"})
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("CLOUDFLARE_API_TOKEN", proc.stderr)


if __name__ == "__main__":
    unittest.main()
