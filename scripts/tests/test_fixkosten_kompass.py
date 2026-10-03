#!/usr/bin/env python3
"""Regressionen für den Produktvertrag des Fixkosten-Kompasses."""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import fixkosten_kompass_guard as guard  # noqa: E402


class FixkostenKompassContractTests(unittest.TestCase):
    def setUp(self):
        self.data = yaml.safe_load((ROOT / "data" / "fixkosten_kompass.yaml").read_text(encoding="utf-8"))

    def test_product_data_and_source_contract_are_green(self):
        self.assertEqual(guard.validate_data(self.data), [])
        self.assertEqual(guard.validate_source(), [])
        self.assertEqual(guard.selftest(), [])

    def test_missing_step_and_pillar_are_blocking(self):
        missing_step = copy.deepcopy(self.data)
        missing_step["stages"].pop()
        self.assertTrue(guard.validate_data(missing_step))

        missing_target = copy.deepcopy(self.data)
        missing_target["categories"][0]["pillar"] = "nicht-vorhanden"
        self.assertTrue(guard.validate_data(missing_target))

    def test_html_entity_encoding_does_not_break_the_build_contract(self):
        # Hugo/minify serialisiert „&“ als „&amp;“. Der Produktvertrag prüft
        # sichtbaren Text, nicht die konkrete Serializer-Schreibweise.
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)
            categories = " ".join(
                category["label"].replace("&", "&amp;") for category in self.data["categories"]
            )
            stages = " ".join(stage["title"] for stage in self.data["stages"])
            (public / "cockpit").mkdir()
            (public / "cockpit" / "index.html").write_text(
                f'<form data-ff-fixkosten-cockpit></form>{categories} {stages} '
                '<script src="/premium/ff-fixkosten-cockpit.js"></script><a href=/cockpit/>Cockpit</a>',
                encoding="utf-8",
            )
            (public / "index.html").write_text(
                '<section data-ff-fixkosten-kompass></section><a href=/cockpit/>Cockpit</a>',
                encoding="utf-8",
            )
            for category in self.data["categories"]:
                target = public / "pillar" / category["pillar"]
                target.mkdir(parents=True)
                (target / "index.html").write_text("Pillar", encoding="utf-8")
            self.assertEqual(guard.validate_build(public, self.data), [])

    def test_deploy_checks_source_and_final_build(self):
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/fixkosten_kompass_guard.py --selftest", workflow)
        self.assertIn("python3 scripts/fixkosten_kompass_guard.py --source-only", workflow)
        self.assertIn("python3 scripts/fixkosten_kompass_guard.py --public public", workflow)
        # Anker nachgezogen 03.10.2026: Der Bau läuft jetzt über die
        # gemeinsame Action. Der VERTRAG ist unverändert – der Quellvertrag
        # muss VOR dem Bau greifen, sonst baut Hugo bereits Defektes.
        self.assertLess(
            workflow.index("Fixkosten-Kompass – Quell- und Datenschutzvertrag"),
            workflow.index("uses: ./.github/actions/hugo-build"),
        )
        self.assertLess(
            workflow.index("Fixkosten-Kompass – finales Produkt-Gate"),
            workflow.index("- name: Deploy auf gh-pages"),
        )

    def test_cockpit_script_has_no_network_or_cookie_path(self):
        script = (ROOT / "static/premium/ff-fixkosten-cockpit.js").read_text(encoding="utf-8")
        self.assertNotIn("fetch(", script)
        self.assertNotIn("XMLHttpRequest", script)
        self.assertNotIn("document.cookie", script)
        self.assertIn("remember.checked", script)
        self.assertIn("safeStorageRemove", script)


if __name__ == "__main__":
    unittest.main()
