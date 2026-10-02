"""Vertragstest: Die Blog-Automatik hängt an KEINER Puter-Brücke.

WARUM (Issue #514, Korrektur 02.10.2026):
Zwei Automatiken – der saisonale Startseiten-Hero und die Faktenfrische –
liefen über eine Puter.js-Brücke mit ``PUTER_AUTH_TOKEN``. Dieses Konto wird
im Betrieb nicht genutzt. Die Folge war kein Ausfall mit Ansage, sondern ein
Dauerzustand: Der Hero-Lauf fiel täglich rot aus und erzeugte Fehl-Issues, die
fachliche Prüfung der Faktenfrische meldete seit jeher „übersprungen". Eine
Automatik, die strukturell nie gelingen kann, ist schlimmer als keine.

Der Transportweg ist jetzt ``scripts/llm_client.py`` (GROQ_API_KEY /
GEMINI_API_KEY, optional ANTHROPIC_API_KEY / OPENAI_API_KEY) – derselbe Zugang,
den die KI-Redaktion produktiv nutzt. Dieser Test friert das ein:

  1. Kein Workflow und kein Skript darf ``PUTER_AUTH_TOKEN``, ``puter_chat``
     oder ``@heyputer`` wieder einführen.
  2. Die Brückendatei bleibt gelöscht.
  3. Wer ein Modell ruft, ruft es über den gemeinsamen Client – nachgewiesen
     an den beiden betroffenen Skripten.

Läuft offline, ohne Netz und ohne Schlüssel.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
SKRIPTE = sorted(ROOT.glob("scripts/*.py")) + sorted(ROOT.glob("scripts/*.mjs"))

# Verbotene Spuren der alten Brücke. Erlaubt bleibt der Begriff in
# Kommentaren/Dokumentation, die die Abschaltung erklären – deshalb wird auf
# ausführbare Spuren geprüft, nicht auf das bloße Wort.
VERBOTEN = (
    re.compile(r"secrets\.PUTER_AUTH_TOKEN"),
    re.compile(r"@heyputer/puter\.js"),
    re.compile(r"puter_chat\.mjs[\"']?\s*\]"),          # subprocess-Aufruf
    re.compile(r"os\.environ(?:\.get)?\(\s*[\"']PUTER_AUTH_TOKEN"),
    re.compile(r"environ\[[\"']PUTER_AUTH_TOKEN"),
)

NUTZER = ("scripts/saisonaler_hero_refresh.py", "scripts/faktenfrische.py")


class KeinePuterAbhaengigkeit(unittest.TestCase):
    def test_bruecke_ist_geloescht(self):
        self.assertFalse((ROOT / "scripts" / "puter_chat.mjs").exists(),
                         "scripts/puter_chat.mjs ist zurück – der Transportweg "
                         "läuft über scripts/llm_client.py")

    def test_kein_workflow_reicht_den_token_durch(self):
        for pfad in WORKFLOWS:
            text = pfad.read_text(encoding="utf-8")
            for muster in VERBOTEN:
                self.assertIsNone(
                    muster.search(text),
                    f"{pfad.relative_to(ROOT)} enthält wieder eine Puter-Abhängigkeit "
                    f"({muster.pattern})")

    def test_kein_skript_ruft_die_bruecke(self):
        for pfad in SKRIPTE:
            text = pfad.read_text(encoding="utf-8", errors="ignore")
            for muster in VERBOTEN:
                self.assertIsNone(
                    muster.search(text),
                    f"{pfad.relative_to(ROOT)} enthält wieder eine Puter-Abhängigkeit "
                    f"({muster.pattern})")

    def test_betroffene_skripte_nutzen_den_gemeinsamen_client(self):
        for rel in NUTZER:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("import llm_client", text,
                          f"{rel} muss den gemeinsamen LLM-Zugang verwenden")
            self.assertIn("PROVIDER_ORDER", text,
                          f"{rel} braucht eine nachvollziehbare Anbieter-Reihenfolge")

    def test_hero_workflow_reicht_die_echten_schluessel_durch(self):
        text = (ROOT / ".github" / "workflows" / "saisonaler-hero-refresh.yml").read_text(
            encoding="utf-8")
        for secret in ("GROQ_API_KEY", "GEMINI_API_KEY"):
            self.assertIn(f"secrets.{secret}", text,
                          f"Der Hero-Lauf braucht {secret} – sonst poliert er nie")

    def test_faktenfrische_workflow_reicht_die_echten_schluessel_durch(self):
        text = (ROOT / ".github" / "workflows" / "faktenfrische.yml").read_text(
            encoding="utf-8")
        for secret in ("GROQ_API_KEY", "GEMINI_API_KEY"):
            self.assertIn(f"secrets.{secret}", text,
                          f"Die Fachprüfung braucht {secret} – sonst bleibt sie "
                          "dauerhaft übersprungen")


if __name__ == "__main__":
    unittest.main()
