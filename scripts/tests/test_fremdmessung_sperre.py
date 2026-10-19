#!/usr/bin/env python3
"""Regressionstest: die Fremdmessung-Sperre (Governance-Report #806, 19.10.2026).

Umami wurde am 11.10.2026 aus dem Frontend genommen – die Anbindung (Skripte,
Workflow-Schritte, Secret, Datenstände, Doku) lebte weiter und täuschte eine
Messung vor, die nicht stattfand. `scripts/fremdmessung_sperre.py` ist die
Wache dagegen. Dieser Test macht sie dauerhaft:

  1. Die Wache erkennt jede einzelne Spur (Sabotage-Proben je Merkmal) und
     bleibt bei Redaktion (Geschmacksrichtung), Fotos und Historie still.
  2. Der ECHTE Quelltext ist frei – derselbe Aufruf, den der Governance-Vertrag
     C40 und `npm run test:fremdmessung` machen.
  3. Der GEBAUTE Baum ist frei (nur nach einem Hugo-Bau: in der CI-Regression
     immer, lokal mit `FREMDMESSUNG_PUBLIC=1`).
  4. Verdrahtung: Vertrag C40, vertragliches Minimum (C6), npm-Skript,
     Dauervorgabe und Runbook existieren – eine Wache, die niemand verlangt,
     führt irgendwann niemand aus.
  5. Die Entfernung ist VOLLSTÄNDIG: kein Skript, kein Workflow-Schritt, keine
     Datei und kein Secret der alten Anbindung – an konkreten Stellen belegt,
     nicht nur über die Mustersuche.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


fs = _load("fremdmessung_sperre", SCRIPTS / "fremdmessung_sperre.py")
gc = _load("governance_contract_c40", SCRIPTS / "governance_contract.py")


def _baum(td: Path, dateien: dict):
    for rel, inhalt in dateien.items():
        p = td / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(inhalt, bytes):
            p.write_bytes(inhalt)
        else:
            p.write_text(inhalt, encoding="utf-8")


def _lies(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class SabotageProben(unittest.TestCase):
    """Jede Spur wird gefunden – einzeln, damit keine die andere verdeckt."""

    def _befunde(self, dateien: dict):
        with tempfile.TemporaryDirectory() as t:
            td = Path(t)
            _baum(td, dateien)
            return fs.befunde(td, nur_pfade=sorted(dateien))

    def test_jedes_anbindungsmerkmal_wird_gefunden(self):
        proben = {
            "script-host": '<script defer src="https://cloud.umami.is/script.js"></script>',
            "api-host": "requests.get('https://api.umami.is/v1/websites')",
            "ereignis-attribut": '<a data-umami-event="affiliate_click" href="/go/x/">x</a>',
            "website-id": '<script data-website-id="abc"></script>',
            "selbst-gehostet": '<script async src="https://stats.example.org/s.js" data-website-id="1b2c"></script>',
            "js-api": "umami.track('klick')",
            "js-objekt": "if (window.umami) {}",
            "secret": "UMAMI_API_TOKEN: ${{ secrets.UMAMI_API_TOKEN }}",
            "variable": "UMAMI_API_BASE=https://x",
            "hugo-konfig": '[params.umami]\nwebsiteId = ""',
            "hugo-zugriff": "{{ with site.Params.umami }}{{ end }}",
            "schalter": "umami_api_import_enabled: true",
            "provider": "provider: umami-only",
            "datenstand": "data/umami_clicks.json",
            "gate-kennung": "governance_gate.py --emit umami-views",
        }
        for name, text in proben.items():
            funde = self._befunde({"scripts/probe.py": f"# {text}\n"})
            self.assertEqual({f.klasse for f in funde}, {"F2-ANBINDUNG"}, f"{name}: {funde}")

    def test_anbindung_gilt_auch_in_redaktionellen_zonen(self):
        for rel in ("content/posts/a/index.md", "data/x.yaml", "data/research/brief.md"):
            funde = self._befunde({rel: '<script src="https://cloud.umami.is/script.js"></script>\n'})
            self.assertEqual({f.klasse for f in funde}, {"F2-ANBINDUNG"}, rel)

    def test_das_bloss_wort_ist_in_redaktion_erlaubt_in_technik_nicht(self):
        for rel in ("content/posts/kochen/index.md", "data/themen.yaml"):
            self.assertEqual(self._befunde({rel: "Umami, die fünfte Geschmacksrichtung.\n"}), [], rel)
        for rel in ("docs/X.md", ".github/workflows/x.yml", "layouts/_partials/x.html",
                    "static/premium/x.js", "scripts/x.py", "package.json", "README.md"):
            funde = self._befunde({rel: "# Umami wird gemessen\n"})
            self.assertEqual({f.klasse for f in funde}, {"F3-ERWAEHNUNG"}, rel)

    def test_dateinamen(self):
        for rel in ("scripts/umami_clicks.py", "data/umami_views.meta.json", "docs/ANLEITUNG-UMAMI-ANALYTICS.md",
                    ".github/workflows/umami-import.yml", "data/umami/x.json"):
            funde = self._befunde({rel: "{}\n"})
            self.assertIn("F1-DATEI", {f.klasse for f in funde}, rel)
        for rel in ("static/images/umami-pilze.webp", "static/images/umami-pilze.jpg", "scripts/umamiser.py"):
            self.assertEqual([f for f in self._befunde({rel: b"\xff\xd8\x00"}) if f.klasse == "F1-DATEI"], [], rel)

    def test_historie_wird_nicht_umgeschrieben(self):
        for rel in ("DATENSCHUTZ-AUDIT-2026-10-10.md", "docs/archiv/ALT.md", "docs/BERICHT-2026-09-26.md",
                    "docs/awin-entfernung-workflows.patch", "data/audit/2026-10-19.jsonl",
                    "data/governance_history.jsonl"):
            self.assertEqual(self._befunde({rel: "cloud.umami.is UMAMI_API_TOKEN Umami\n"}), [], rel)

    def test_generierte_momentaufnahmen_werden_nicht_gescannt(self):
        """Ein Lauf-Rückstand ist kein Befund: Die Ursache läge im Code, den die Wache prüft."""
        for rel in fs.GENERIERT:
            self.assertEqual(self._befunde({rel: "Umami UMAMI_API_TOKEN umami_clicks\n"}), [], rel)
        self.assertEqual({f.klasse for f in self._befunde({"docs/COCKPIT.md": "Umami\n"})},
                         {"F3-ERWAEHNUNG"}, "nur die genannten Pfade sind ausgenommen, nicht ähnliche")

    def test_binaer_und_zu_gross_ist_kein_quelltext(self):
        self.assertEqual(self._befunde({"data/x.bin": b"UMAMI_API_TOKEN\x00\x01"}), [])

    def test_ausnahmen_altern_und_brauchen_grund(self):
        with tempfile.TemporaryDirectory() as t:
            td = Path(t)
            _baum(td, {"a.py": "# Umami hier\n", "b.py": "# sauber\n", "c.py": "# Umami hier\n"})
            funde = fs.befunde(td, ausnahmen={"a.py": "Absenz-Test mit Grund", "b.py": "veraltet",
                                              "c.py": ""})
            self.assertEqual(sorted((f.pfad, f.klasse) for f in funde),
                             [("b.py", "F5-AUSNAHME"), ("c.py", "F5-AUSNAHME")])
            self.assertTrue(any("veraltet" in f.stelle for f in funde if f.pfad == "b.py"))
            ohne = fs.befunde(td, ausnahmen={})
            self.assertEqual({(f.pfad, f.klasse) for f in ohne},
                             {("a.py", "F3-ERWAEHNUNG"), ("c.py", "F3-ERWAEHNUNG")})

    def test_gebauter_baum(self):
        with tempfile.TemporaryDirectory() as t:
            td = Path(t)
            _baum(td, {"index.html": "<p>Umami im Essen</p>\n", "premium/ok.js": "var x = 1;\n"})
            self.assertEqual(fs.befunde_gebaut(td), [], "Redaktion im gebauten HTML ist erlaubt")
            _baum(td, {"premium/leck.js": "/* kein Umami */\n"})
            self.assertEqual({f.klasse for f in fs.befunde_gebaut(td)}, {"F4-GEBAUT"},
                             "ein Kommentar im ausgelieferten Skript landet im Browser der Besucher")
            os.remove(td / "premium/leck.js")
            _baum(td, {"x/index.html": '<script src="https://cloud.umami.is/script.js" data-website-id="1"></script>\n'})
            self.assertEqual({f.klasse for f in fs.befunde_gebaut(td)}, {"F4-GEBAUT"})
            self.assertEqual({f.klasse for f in fs.befunde_gebaut(td / "fehlt")}, {"F4-GEBAUT"})


class EchterBestand(unittest.TestCase):
    def test_selftest_gruen(self):
        self.assertEqual(fs._selftest(), 0)

    def test_quelltext_ist_frei(self):
        funde = fs.befunde(ROOT)
        self.assertEqual(funde, [], "Spur des entfernten Dienstes im Quelltext:\n"
                         + "\n".join(f"  {f.klasse} {f.pfad}:{f.stelle} – {f.meldung}" for f in funde[:20]))

    def test_gebauter_baum_ist_frei(self):
        public = ROOT / "public"
        if not (public / "index.html").is_file():
            self.skipTest("kein gebauter Baum (public/) – erst `hugo --minify` bauen")
        if not (os.environ.get("CI") or os.environ.get("FREMDMESSUNG_PUBLIC")):
            self.skipTest("lokaler public/ kann veraltet sein – mit FREMDMESSUNG_PUBLIC=1 prüfen "
                          "(in der CI-Regression läuft das nach einem frischen Hugo-Bau immer)")
        funde = fs.befunde_gebaut(public)
        self.assertEqual(funde, [], "Spur des entfernten Dienstes im GEBAUTEN Baum:\n"
                         + "\n".join(f"  {f.klasse} {f.pfad}:{f.stelle} – {f.meldung}" for f in funde[:20]))

    def test_alle_ausnahmen_sind_begruendet_einzeln_und_nicht_historisch(self):
        for rel, grund in fs.ERLAUBT.items():
            self.assertGreaterEqual(len(grund.strip()), 20, f"{rel}: Begründung zu dünn")
            self.assertFalse(any(c in rel for c in "*?[]"), f"{rel}: Wildcards sind verboten")
            self.assertFalse(fs._historisch(rel), f"{rel}: historische Pfade werden nie gescannt")
            self.assertTrue((ROOT / rel).is_file(), f"{rel}: Ausnahme für eine fehlende Datei")

    def test_generierte_zone_ist_begruendet_vorhanden_und_ohne_doppelung(self):
        for rel, grund in fs.GENERIERT.items():
            self.assertGreaterEqual(len(grund.strip()), 20, f"{rel}: Begründung zu dünn")
            self.assertTrue((ROOT / rel).is_file(), f"{rel}: generierte Datei fehlt")
            self.assertNotIn(rel, fs.ERLAUBT, f"{rel}: Doppelung mit ERLAUBT")

    def test_die_zwei_gesiegelten_kommentar_altlasten_sind_bekannt_und_gesiegelt(self):
        """Die beiden Ausnahmen mit Siegel-Grund müssen wirklich im Siegel stehen –
        sonst wäre der Grund erfunden und die Ausnahme ein Schlupfloch."""
        lock = json.loads(_lies("data/integrity_lock.json"))
        for rel in ("layouts/_default/_markup/render-link.html", "scripts/check24_links.yaml"):
            self.assertIn(rel, fs.ERLAUBT)
            self.assertIn(rel, lock["files"], f"{rel} steht nicht im Integritäts-Siegel – Ausnahme ohne Grund")


class Entfernung(unittest.TestCase):
    """Die Entfernung ist vollständig – an den Stellen, an denen es gelebt hat."""

    def test_keine_datei_der_alten_anbindung(self):
        for rel in ("scripts/umami_clicks.py", "scripts/umami_views.py", "data/umami_clicks.json",
                    "data/umami_clicks.meta.json", "data/umami_views.json", "data/umami_views.meta.json",
                    "data/umami_ctas.json", "data/umami_ctas.meta.json", "data/monetization.yaml",
                    "docs/ANLEITUNG-UMAMI-ANALYTICS.md"):
            self.assertFalse((ROOT / rel).exists(), f"{rel} ist zurück")
        namen = [p for p in fs.dateien(ROOT) if fs.NAME_RE.search(p.rsplit("/", 1)[-1])
                 and os.path.splitext(p)[1].lower() in fs.TEXT_ENDUNGEN]
        self.assertEqual(namen, [], f"Dateien mit dem Namen des entfernten Dienstes: {namen}")

    def test_workflows_nennen_weder_skript_noch_secret(self):
        for pfad in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
            text = pfad.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"(?i)umami", f"{pfad.name} trägt noch eine Spur")

    def test_gate_vertrag_und_wachen_kennen_den_dienst_nicht_mehr(self):
        gg = _load("governance_gate_c40", SCRIPTS / "governance_gate.py")
        self.assertEqual([k for k in gg.STEPS if "umami" in k], [])
        self.assertEqual([k for k in gc.STEP_SIGNATURES if "umami" in k], [])
        self.assertEqual([k for k in gc.MEASURE_STEPS if "umami" in k], [])
        self.assertEqual([g for g in gc.GUARDS if "umami" in g], [])

    def test_hugo_konfiguration_und_templates(self):
        import tomllib
        cfg = tomllib.loads(_lies("hugo.toml"))
        self.assertNotIn("umami", cfg.get("params", {}))
        for rel in ("layouts/baseof.html", "layouts/_partials/extend_head.html",
                    "layouts/_partials/extend_footer.html", "layouts/_partials/deferred_scripts.html"):
            if (ROOT / rel).is_file():
                self.assertNotRegex(_lies(rel), r"(?i)site\.Params\.umami|umami\.is|data-website-id", rel)

    def test_secrets_wache_kennt_das_secret_nicht_mehr(self):
        sa = _load("secrets_age_guard_c40", SCRIPTS / "secrets_age_guard.py")
        self.assertEqual([k for k in sa.SECRETS if "UMAMI" in k], [])
        self.assertEqual([k for k in sa.PROBES if k and "umami" in str(k)], [])

    def test_funnel_nennt_den_dienst_nicht_und_misst_keine_besuche(self):
        rf = _load("revenue_funnel_c40", SCRIPTS / "revenue_funnel.py")
        self.assertEqual([s[0] for s in rf.SOURCES], ["offline", "clicks"])
        self.assertTrue(rf.CLICKS.endswith("klicks_eigen.json"))
        self.assertFalse(hasattr(rf, "umami_api_import_enabled"))


class Verdrahtung(unittest.TestCase):
    def test_vertrag_c40_ist_scharf(self):
        self.assertIn("fremdmessung_sperre.py", gc.GUARDS, "ohne vertragliches Minimum läuft der Selbsttest nie")
        self.assertIn("C40", gc.LABEL)
        self.assertIn("C40", gc.RULE_TEXT)
        self.assertTrue(hasattr(gc, "c40_keine_fremdmessung"))

    def test_vertrag_c40_laeuft_im_qualitaets_gate(self):
        link_check = _lies(".github/workflows/link-check.yml")
        self.assertIn("governance_contract.py --quick", link_check,
                      "link-check.yml ruft den Vertrag nicht – dann läuft C40 in keinem Gate")

    def test_npm_skript(self):
        pkg = json.loads(_lies("package.json"))
        skript = pkg["scripts"].get("test:fremdmessung", "")
        for teil in ("fremdmessung_sperre.py --selftest", "fremdmessung_sperre.py", "test_fremdmessung_sperre"):
            self.assertIn(teil, skript)

    def test_dauervorgabe_und_runbook(self):
        claude = _lies("CLAUDE.md")
        self.assertRegex(claude, r"## Keine Fremdmessung")
        self.assertIn("scripts/fremdmessung_sperre.py", claude)
        runbook = _lies("docs/ANLEITUNG-FREMDMESSUNG-SPERRE.md")
        for klasse in ("F1-DATEI", "F2-ANBINDUNG", "F3-ERWAEHNUNG", "F4-GEBAUT", "F5-AUSNAHME"):
            self.assertIn(klasse, runbook, f"Runbook erklärt {klasse} nicht")
            self.assertIn(klasse, _lies("scripts/fremdmessung_sperre.py"))

    def test_regressions_workflow_baut_vor_der_suite(self):
        """Der Test oben prüft public/ nur, wenn gebaut wurde – hier der Beweis, dass
        die PR-Regression vor der Suite wirklich baut und die Suite wirklich startet."""
        wf = _lies(".github/workflows/publication-reliability-tests.yml")
        bau = wf.find("hugo-build")
        suite = wf.find("python3 -m unittest discover -s scripts/tests")
        self.assertGreater(bau, 0, "kein Hugo-Bau in der PR-Regression")
        self.assertGreater(suite, bau, "die Suite läuft nicht NACH dem Bau")
        # Der QUELLTEXT (auch static/) wird zusätzlich von Vertrag C40 im
        # Qualitäts-Gate geprüft, das ohne Pfadfilter auf jeden Push/PR läuft; die
        # Regression deckt alles ab, was Hugo erst im Bau erzeugt.
        for pfad in ("layouts/**", "assets/**", "content/**", "hugo.toml", "scripts/**"):
            self.assertIn(pfad, wf, f"{pfad} löst die Regression nicht aus")


if __name__ == "__main__":
    unittest.main(verbosity=2)
