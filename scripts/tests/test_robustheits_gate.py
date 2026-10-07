#!/usr/bin/env python3
"""Regressionen für das Robustheits-Gate (Vertrag C31, 07.10.2026).

Vier Ebenen, wie bei den übrigen Produktverträgen dieses Repos:

  1. Der echte Quellbaum ist grün – und der Selbsttest des Gates besteht
     (ein Detektor, der sich nicht selbst beweist, ist kein Detektor).
  2. Jede Kernregel bricht, wenn man sie sabotiert. Ohne diese Probe wäre
     das Gate ein grüner Haken ohne Aussage.
  3. Der Aufruf-Vertrag zwischen den Bausteinen stimmt: Was ein Skript an
     `FFRobust.<name>` abruft, muss die Schicht auch anbieten – sonst
     verläuft sich die Härtung im Leeren (stiller Ausfall, genau die Klasse,
     die dieses Gate jagt).
  4. Die Wache ist in der CI verdrahtet (Deploy + eigener Lauf) und die
     Ausnahmen sind begründet, datiert und fällig.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import robustheits_gate as gate  # noqa: E402


def pruefbaum() -> Path:
    """Kopie der Dateien, die das Gate liest – zum Sabotieren ohne Risiko."""
    sandbox = Path(tempfile.mkdtemp(prefix="robustheit-test-"))
    rels = ([gate.SCHICHT, gate.BOOTSTRAP, gate.EINBINDUNG, gate.SW, gate.FUSS,
             gate.CSS, gate.AUSNAHMEN]
            + gate.erstpartei_js(ROOT) + gate.layout_dateien(ROOT))
    for rel in rels:
        original = ROOT / rel
        if not original.exists():
            continue
        kopie = sandbox / rel
        kopie.parent.mkdir(parents=True, exist_ok=True)
        kopie.write_text(original.read_text(encoding="utf-8"), encoding="utf-8")
    return sandbox


def funde_von(root: Path) -> list[str]:
    funde: list[str] = []
    for _, _, pruefung in gate.REGELN:
        funde.extend(pruefung(root))
    return funde


class EchterStandTests(unittest.TestCase):
    def test_quellbaum_ist_gruen(self):
        self.assertEqual([], funde_von(ROOT),
                         "Der echte Stand verletzt den Robustheits-Vertrag – "
                         "das Gate wäre ab dem ersten Lauf rot")

    def test_selbsttest_besteht(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/robustheits_gate.py"),
                               "--selftest"], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("SELBSTTEST OK", proc.stdout)

    def test_quellenmodus_ist_exit_null(self):
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/robustheits_gate.py"),
                               "--source-only", "--json", "--no-report"],
                              capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        daten = json.loads(proc.stdout)
        self.assertTrue(daten["ok"])
        self.assertEqual(12, len(daten["regeln"]), "zwölf Regeln sind der Vertrag")

    def test_public_modus_meldet_fehlenden_build(self):
        """Ohne Build darf die Prüfung der gebauten Wahrheit nicht grün tun."""
        proc = subprocess.run([sys.executable, str(ROOT / "scripts/robustheits_gate.py"),
                               "--public", "/tmp/gibt-es-nicht-robustheit", "--json",
                               "--no-report"], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(1, proc.returncode)
        daten = json.loads(proc.stdout)
        self.assertTrue(any("public/" in f for f in daten["funde"]))


class SabotageTests(unittest.TestCase):
    """Jede Kernregel muss ansprechen, wenn ihr Gegenstand verschwindet."""

    def sabotage(self, rel: str, alt: str, neu: str, regel: str, alle: bool = False) -> None:
        root = pruefbaum()
        pfad = root / rel
        self.assertTrue(pfad.exists(), f"{rel} fehlt im Prüfbaum")
        inhalt = pfad.read_text(encoding="utf-8")
        self.assertIn(alt, inhalt, f"Anker für die Sabotage nicht in {rel}")
        pfad.write_text(inhalt.replace(alt, neu) if alle else inhalt.replace(alt, neu, 1),
                        encoding="utf-8")
        funde = funde_von(root)
        self.assertTrue(any(f.startswith(regel) for f in funde),
                        f"{regel} schlägt nicht an: {[f[:70] for f in funde][:3]}")

    def test_schicht_ohne_api_wird_gemeldet(self):
        """Verschwindet ein API-Baustein aus dem CODE, ist die Schicht eine andere.
        Auch die Docstring wird umbenannt: R1 prüft seit C31 gegen den Code ohne
        Kommentare – eine Erwähnung im Text erfüllt den Vertrag nicht."""
        self.sabotage(gate.SCHICHT, "ablage", "ablageWeg", "R1", alle=True)

    def test_bootstrap_als_eigenes_head_kind_wird_gemeldet(self):
        """Das Head-Budget ist der Grund, warum der Bootstrap kein eigenes Tag ist."""
        self.sabotage(gate.BOOTSTRAP, "})();\n\n/* ---- Robustheits-Bootstrap",
                      "})();\n</script>\n<script>\n/* ---- Robustheits-Bootstrap", "R2")

    def test_bootstrap_ohne_capture_phase_wird_gemeldet(self):
        self.sabotage(gate.BOOTSTRAP, "  }, true);", "  });", "R2")

    def test_sw_ohne_fail_open_wird_gemeldet(self):
        self.sabotage(gate.SW,
                      "  try {\n    if (typeof caches === 'undefined') return null;\n"
                      "    return await caches.open(CACHE);\n  } catch (e) {\n    return null;\n  }",
                      "  return await caches.open(CACHE);", "R5")

    def test_sw_ohne_offline_fangnetz_wird_gemeldet(self):
        self.sabotage(gate.SW, "  OFFLINE_PFAD\n];", "];", "R5")

    def test_sw_ohne_range_umgehung_wird_gemeldet(self):
        self.sabotage(gate.SW, "  try { if (req.headers.get('range')) return; } catch (e) {}",
                      "  /* Range-Umgehung entfernt */", "R5")

    def test_sw_ohne_selbstbefreiung_wird_gemeldet(self):
        self.sabotage(gate.SW, "'SKIP_WAITING'", "'IRGENDWAS'", "R5")

    def test_inselfangnetz_wird_gemeldet(self):
        self.sabotage("static/premium/ff-summary-safety.js", "FEHLER_LIMIT",
                      "GRENZE_ENTFERNT", "R6", alle=True)

    def test_dynamisches_innerhtml_wird_gemeldet(self):
        self.sabotage("static/premium/ff-feedback.js", "(function () {\n  'use strict';",
                      "(function () {\n  'use strict';\n"
                      "  function boese(t) { var d = document.createElement('p'); d.innerHTML = t; return d; }",
                      "R7")

    def test_document_write_wird_gemeldet(self):
        self.sabotage("static/premium/ff-feedback.js", "(function () {\n  'use strict';",
                      "(function () {\n  'use strict';\n  document.write('<p>x</p>');", "R7")

    def test_speicher_ohne_fangnetz_wird_gemeldet(self):
        self.sabotage("static/premium/ff-newsletter.js",
                      "    try { bereits = localStorage.getItem(SCHLUESSEL) === 'angemeldet'; } catch (e) { bereits = false; }",
                      "    bereits = localStorage.getItem(SCHLUESSEL) === 'angemeldet';", "R8")

    def test_schicht_ohne_einbindung_wird_gemeldet(self):
        self.sabotage(gate.EINBINDUNG,
                      '<script defer src="{{ partial "asset_url.html" "premium/ff-robust.js" }}"></script>',
                      '<!-- Schicht entfernt -->', "R12")

    def test_dunkelvariante_des_hinweises_wird_gemeldet(self):
        self.sabotage(gate.CSS, ':root[data-theme="dark"] .ff-robust-hinweis {',
                      ".ff-robust-hinweis--egal {", "R9")

    def test_fremde_domain_in_der_schicht_wird_gemeldet(self):
        root = pruefbaum()
        pfad = root / gate.SCHICHT
        inhalt = pfad.read_text(encoding="utf-8")
        pfad.write_text(inhalt + "\n/* https://fremd.example.com/x.js */\n", encoding="utf-8")
        self.assertTrue(any(f.startswith("R11") for f in funde_von(root)))


class GegenprobenTests(unittest.TestCase):
    """Das Gate darf nicht schärfer sein als der Vertrag – sonst wird es
    abgeschaltet (Lehre aus Issue #338: Dauer-Alarme töten Wachen)."""

    def test_statisches_innerhtml_ist_erlaubt(self):
        root = pruefbaum()
        pfad = root / "static/premium/ff-feedback.js"
        inhalt = pfad.read_text(encoding="utf-8")
        pfad.write_text(inhalt.replace(
            "(function () {\n  'use strict';",
            "(function () {\n  'use strict';\n  var x = document.createElement('p');"
            " x.innerHTML = '<span class=\"a\"></span>';", 1), encoding="utf-8")
        self.assertEqual([], [f for f in funde_von(root) if f.startswith("R7")])

    def test_konstante_icons_sind_erlaubt(self):
        """ff-premium.js setzt Icons aus statischen Konstanten – kein Befund."""
        self.assertEqual([], [f for f in funde_von(ROOT) if f.startswith("R7")
                              and "ff-premium.js" in f])

    def test_prefetch_ist_kein_fetch(self):
        """`prefetch(` enthält die Zeichenfolge `fetch(` – und ist kein Netzaufruf."""
        self.assertEqual([], [f for f in funde_von(ROOT) if f.startswith("R4")
                              and "ff-premium.js" in f])

    def test_durchgereichtes_zeitlimit_ist_erlaubt(self):
        root = pruefbaum()
        (root / "static/premium/ff-pruef-durchreich.js").write_text(
            "(function () {\n  'use strict';\n"
            "  function anfragen(ziel, optionen) {\n"
            "    var robust = window.FFRobust;\n"
            "    if (robust && typeof robust.hole === 'function') return robust.hole(ziel, optionen);\n"
            "    return window.fetch(ziel, optionen).catch(function () { return null; });\n  }\n"
            "  window.__x = anfragen('/a', { zeitlimit: 5000 });\n})();\n", encoding="utf-8")
        self.assertEqual([], [f for f in funde_von(root) if f.startswith("R4")])


class AufrufVertragTests(unittest.TestCase):
    """Was die Bausteine abrufen, muss die Schicht anbieten (Drift-Schutz)."""

    def test_alle_abgerufenen_bausteine_existieren(self):
        angeboten = set(gate.API) | {"hole", "warte", "boot", "fassung", "fehler",
                                     "status", "max", "zaehler", "offline", "voll"}
        abgerufen: set[str] = set()
        dateien = gate.erstpartei_js(ROOT) + gate.layout_dateien(ROOT)
        for rel in dateien:
            inhalt = gate.text(ROOT, rel)
            for m in re.finditer(r"FFRobust\.([A-Za-z_][\w]*)", inhalt):
                abgerufen.add(m.group(1))
            # (?<![-\w./]) trennt den Aufruf `robust.hole(` von Dateinamen
            # („ff-robust.js", „tools/robust.test.mjs") – sonst prüft der Test
            # Pfadteile statt API.
            for m in re.finditer(r"(?<![-\w./])robust\.([A-Za-z_][\w]*)", inhalt):
                abgerufen.add(m.group(1))
        fehlen = {a for a in abgerufen if a not in angeboten}
        self.assertEqual(set(), fehlen,
                         "Ein Baustein ruft etwas ab, das die Schicht nicht "
                         "anbietet – die Härtung liefe still ins Leere")

    def test_bootstrap_und_schicht_teilen_den_namensraum(self):
        self.assertIn("global.FFRobust = global.FFRobust || {}",
                      gate.text(ROOT, gate.SCHICHT),
                      "Die zweite Stufe muss die erste ergänzen, nicht ersetzen")
        self.assertIn("R.boot", gate.text(ROOT, gate.BOOTSTRAP))

    def test_schicht_ist_idempotent(self):
        inhalt = gate.text(ROOT, gate.SCHICHT)
        self.assertIn("if (!R.boot)", inhalt,
                      "Ohne boot-Prüfung meldet die zweite Stufe jeden Fehler doppelt")

    def test_hole_lehnt_nie_ab(self):
        """Vertrag der Schicht: `hole` liefert immer ein Ergebnisobjekt."""
        bootstrap = gate.text(ROOT, gate.BOOTSTRAP)
        self.assertIn("R.hole = function", bootstrap)
        self.assertIn("unbekannt: true", bootstrap,
                      "Eine opaque Antwort (no-cors) ist durchgekommen, nicht "
                      "gescheitert – sonst meldet die Anmeldung Fehler, die keine sind")
        self.assertNotIn("throw", bootstrap.split("R.hole = function", 1)[1],
                         "hole() darf nicht werfen: Ein vergessenes .catch() "
                         "wäre sonst wieder ein stiller Ausfall")


class AusnahmenTests(unittest.TestCase):
    def test_ausnahmen_sind_begruendet_und_faellig(self):
        eintraege = gate.ausnahmen_laden(ROOT)
        self.assertTrue(eintraege, "die Ausnahmen-Datei ist leer oder unlesbar")
        heute = date.today()
        for e in eintraege:
            for feld in ("pfad", "regel", "grund", "entscheidung", "faellig"):
                self.assertTrue(str(e.get(feld, "")).strip(),
                                f"Ausnahme für {e.get('pfad')} ohne `{feld}` – "
                                "eine Ausnahme ohne Begründung ist eine Abschaffung")
            self.assertRegex(str(e["regel"]), r"^R\d+$")
            jahr, monat, tag = (int(x) for x in str(e["faellig"]).split("-"))
            self.assertGreaterEqual(date(jahr, monat, tag), heute,
                                    f"Ausnahme für {e['pfad']} ist überfällig "
                                    "(data/robustheit_ausnahmen.yaml prüfen)")
            self.assertTrue((ROOT / str(e["pfad"])).exists(),
                            f"Ausnahme für {e['pfad']} zeigt auf eine Datei, die es nicht gibt")

    def test_ausnahme_befreit_versiegelte_datei(self):
        """head.html ist KRITISCH-versiegelt: Das Gate darf sie nicht dauerrot melden."""
        self.assertIn("layouts/_partials/head.html", gate.ausnahmen(ROOT, "R8"))
        self.assertEqual([], [f for f in funde_von(ROOT) if "head.html" in f])

    def test_rueckfall_parser_liest_struktur(self):
        """Ohne PyYAML muss das Gate dieselben Entscheidungen treffen können."""
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "ausnahmen.yaml"
            pfad.write_text("ausnahmen:\n  - pfad: layouts/x.html\n    regel: R8\n"
                            "    grund: >-\n      Text\n"
                            "    entscheidung: Mensch, 07.10.2026\n"
                            '    faellig: "2027-01-07"\n', encoding="utf-8")
            sandbox = Path(tmp)
            ziel = sandbox / gate.AUSNAHMEN
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(pfad.read_text(encoding="utf-8"), encoding="utf-8")
            gate._AUSNAHMEN_PUFFER.pop(str(sandbox), None)
            self.assertEqual({"layouts/x.html"}, gate.ausnahmen(sandbox, "R8"))


class VerdrahtungTests(unittest.TestCase):
    """Eine Wache, die niemand ruft, ist eine Meinung."""

    def test_deploy_pruft_vor_dem_build(self):
        deploy = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
        self.assertIn("robustheits_gate.py --selftest", deploy,
                      "Der Deploy muss den Detektor erst beweisen, dann prüfen")
        self.assertIn("robustheits_gate.py --source-only", deploy)

    def test_eigener_lauf_existiert(self):
        lauf = ROOT / ".github/workflows/robustheit.yml"
        self.assertTrue(lauf.exists(), "der Robustheits-Lauf fehlt")
        inhalt = lauf.read_text(encoding="utf-8")
        for pflicht in ("pull_request", "schedule", "timeout-minutes", "permissions"):
            self.assertIn(pflicht, inhalt, f"robustheit.yml ohne `{pflicht}`")
        self.assertIn("contents: read", inhalt, "minimale Rechte sind Pflicht")

    def test_npm_skripte_existieren(self):
        paket = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        for name in ("robustheit:check", "robustheit:strict", "test:robustheit"):
            self.assertIn(name, paket["scripts"], f"npm run {name} fehlt")
        self.assertIn("robustheits_gate.py --selftest", paket["scripts"]["test:robustheit"])

    def test_dokumentation_ist_verlinkt(self):
        self.assertTrue((ROOT / "docs/ANLEITUNG-ROBUSTHEIT.md").exists(),
                        "Runbook fehlt")
        claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("robustheits_gate.py", claude,
                      "Der Leitfaden für Agenten nennt die Wache nicht")


if __name__ == "__main__":
    unittest.main()
