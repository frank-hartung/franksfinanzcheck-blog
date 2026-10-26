#!/usr/bin/env python3
"""Regression tests for the complete, fail-closed accessibility audit."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import a11y_audit as audit  # noqa: E402


class HTMLCoverageTests(unittest.TestCase):
    def _write(self, root: Path, rel: str, html: str = "<h1>Seite</h1>") -> Path:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        return path

    def test_scan_hat_keine_versteckten_verzeichnis_oder_substring_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)
            self._write(public, "assets/guide/index.html")
            self._write(public, "BingSiteAuth.html")
            self._write(public, "docs/google-example.html")
            self._write(public, "page/2/index.html")
            self._write(public, "posts/page/2/index.html")
            self._write(public, "go/strom/index.html")
            self._write(public, "pinterest-oauth/index.html")

            relative = {
                Path(path).relative_to(public).as_posix()
                for path in audit.collect_html_files(public)
            }
            self.assertIn("assets/guide/index.html", relative)
            self.assertIn("BingSiteAuth.html", relative)
            # Die Root-Verifikationsausnahme darf keine echte Unterseite treffen.
            self.assertIn("docs/google-example.html", relative)
            # Blätterseiten sind ECHTE, verlinkte Seiten – sie werden geprüft.
            # (Stufe 2, 08.10.2026: Bis dahin nahm die Ausnahme der H1-Wache
            # alle `page/N/`-Dateien pauschal aus und verdeckte damit, dass
            # /page/2/ … gar keine H1 trugen. Mit disableAliases = true gibt es
            # keine inhaltsleeren Blätter-Redirects mehr.)
            self.assertIn("page/2/index.html", relative)
            self.assertIn("posts/page/2/index.html", relative)
            # Nur die dokumentierten Redirects sind von diesem Voll-Audit befreit.
            self.assertNotIn("go/strom/index.html", relative)
            self.assertNotIn("pinterest-oauth/index.html", relative)

    def test_leere_oder_vollstaendig_ausgenommene_builds_sind_nicht_gruen(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp) / "public"
            public.mkdir()
            output = StringIO()
            with patch.object(audit, "PUBLIC_DIR", str(public)), redirect_stdout(output):
                status = audit.main(["--json"])

            report = json.loads(output.getvalue())
            self.assertEqual(status, 2)
            self.assertFalse(report["ok"])
            self.assertEqual(report["gesamt_probleme"], 1)
            self.assertIn("keine prüfbare HTML-Seite", report["fehler"][0])

    def test_fehlender_build_ist_exit_2_statt_stillem_skip(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "public-fehlt"
            output = StringIO()
            with patch.object(audit, "PUBLIC_DIR", str(missing)), redirect_stdout(output):
                status = audit.main(["--json"])

            report = json.loads(output.getvalue())
            self.assertEqual(status, 2)
            self.assertFalse(report["ok"])
            self.assertEqual(report["gesamt_probleme"], 1)
            self.assertIn("public/ fehlt", report["fehler"][0])


class HeadingAuditTests(unittest.TestCase):
    def _audit(self, html: str) -> list[str]:
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)
            path = public / "seite.html"
            path.write_text(html, encoding="utf-8")
            _, issues = audit.audit_page(path, public)
            return issues

    def test_echte_h1_werden_geprueft_und_skript_kommentar_ignoriert(self):
        issues = self._audit(
            '<html lang="de"><title>Seite</title><a class="skip-link" href="#main">Skip</a>'
            '<!-- <h1>Kommentar</h1> -->'
            '<script>const markup = "<h1>Skript</h1>";</script>'
            '<template><h1>Vorlage</h1></template>'
            '<h1>Finanzwissen &amp; <span>Orientierung</span></h1></html>'
        )
        self.assertFalse(any("h1" in issue.lower() for issue in issues), issues)

    def test_doppelte_h1_werden_mit_lesbarem_text_gemeldet(self):
        issues = self._audit(
            '<html lang="de"><title>Seite</title><a class="skip-link"></a>'
            '<h1>Wissen &amp; Klarheit</h1><h1>Zusatz</h1></html>'
        )
        h1_issue = next(issue for issue in issues if "h1" in issue.lower())
        self.assertIn("2 h1", h1_issue)
        self.assertIn("Wissen & Klarheit", h1_issue)
        self.assertIn("Zusatz", h1_issue)

    def test_eine_leere_h1_ist_ein_a11y_befund(self):
        issues = self._audit(
            '<html lang="de"><title>Seite</title><a class="skip-link"></a>'
            '<h1>&nbsp;&#160;&#xA0;</h1></html>'
        )
        self.assertTrue(any("H1 ist leer" in issue for issue in issues), issues)

    def test_unsichtbare_unicodezeichen_bestehen_nicht_als_h1_text(self):
        issues = self._audit(
            '<html lang="de"><title>Seite</title><a class="skip-link"></a>'
            '<h1>&#x200B;</h1></html>'
        )
        self.assertTrue(any("H1 ist leer" in issue for issue in issues), issues)

    def test_fehlende_h1_wache_bricht_fail_closed_ab(self):
        with patch.object(audit, "AUSNAHMEN", None), patch.object(audit, "h1_der_seite", None):
            with self.assertRaisesRegex(RuntimeError, "keine Ersatz-Ausnahmeliste"):
                audit.collect_html_files("/nicht-vorhanden")

    def test_main_meldet_fehlendes_h1_ssot_mit_exit_2(self):
        output = StringIO()
        with patch.object(audit, "AUSNAHMEN", None), patch.object(audit, "h1_der_seite", None), \
                redirect_stdout(output):
            status = audit.main(["--json"])

        report = json.loads(output.getvalue())
        self.assertEqual(status, 2)
        self.assertFalse(report["ok"])
        self.assertIn("H1-Wache scripts/h1_wache.py nicht ladbar", report["fehler"][0])


class LinkNameTests(unittest.TestCase):
    """WCAG 2.5.3 (Label in Name) – der Name muss den sichtbaren Text tragen.

    Die Befunde vom 26.10.2026 waren genau dieser Fehler: ein `aria-label`,
    das sichtbaren Text verschwieg. Deshalb prüfen die Tests die WIRKUNG
    (den zusammengesetzten sichtbaren Text), nicht die Existenz des Attributs.
    """

    def test_override_mit_vollstaendigem_sichtbarem_text_ist_sauber(self):
        html = (
            '<a class="ff-pin-float" aria-label="Pin It – diesen Artikel auf Pinterest pinnen">'
            '<svg aria-hidden="true"><path d="M0 0"/></svg><span>Pin It</span></a>'
        )
        self.assertEqual(audit.link_name_issues(html), [])

    def test_override_der_datum_und_anriss_verschweigt_ist_ein_befund(self):
        html = (
            '<a class="ff-related-card" aria-label="Weiterlesen: Zinsen 2026">'
            '<span class="ff-related-card__date">26.10.2026</span>'
            '<strong class="ff-related-card__heading">Zinsen 2026</strong>'
            '<span class="ff-related-card__snippet">Die besten Zinsen im Vergleich</span>'
            '</a>'
        )
        issues = audit.link_name_issues(html)
        self.assertEqual(len(issues), 1, issues)
        self.assertIn("WCAG 2.5.3", issues[0])
        self.assertIn("26.10.2026", issues[0])

    def test_leerer_overlay_link_ohne_eigenen_text_bleibt_sauber(self):
        # .entry-link ist eine leere Klickfläche über der Karte. Sie hat
        # keinen sichtbaren Text IN sich – der Name darf (und muss) dort aus
        # dem aria-label kommen.
        html = '<article><h2>Kartentitel</h2><a class="entry-link" aria-label="Weiterlesen: Kartentitel" href="/x/"></a></article>'
        self.assertEqual(audit.link_name_issues(html), [])

    def test_sr_only_text_muss_nicht_im_namen_stehen(self):
        html = (
            '<a aria-label="Zur Startseite" href="/">'
            '<span class="sr-only">FranksFinanzcheck</span>'
            '<img src="logo.svg" alt="">'
            '</a>'
        )
        self.assertEqual(audit.link_name_issues(html), [])

    def test_aria_hidden_unterbaum_zaehlt_nicht_als_sichtbar(self):
        html = (
            '<a aria-label="Zum Thema" href="/thema/">'
            '<span aria-hidden="true">→</span>Zum Thema'
            '</a>'
        )
        self.assertEqual(audit.link_name_issues(html), [])

    def test_markup_entities_und_umbrueche_werden_normalisiert(self):
        html = (
            '<a aria-label="Finanzen &amp; Freiheit   – Beratung" href="/x/">'
            '<strong>Finanzen &amp; Freiheit</strong>\n<span>– Beratung</span>'
            '</a>'
        )
        self.assertEqual(audit.link_name_issues(html), [])

    def test_verschachtelte_auszeichnung_wird_vollstaendig_gelesen(self):
        # Regression zur ersten Fassung: Ein Parser, der <picture> als
        # Void-Element behandelt, verliert den gesamten Text der Karte und
        # meldet fälschlich „sauber“ (am 26.10.2026 real passiert).
        html = (
            '<a aria-label="Weiterlesen: Titel" href="/x/">'
            '<span class="cover"><picture><source srcset="a.avif"><img src="a.jpg" alt=""></picture></span>'
            '<span class="body"><strong>Titel</strong><span>Anriss mit Substanz</span></span>'
            '</a>'
        )
        issues = audit.link_name_issues(html)
        self.assertEqual(len(issues), 1, issues)
        self.assertIn("Anriss mit Substanz", issues[0])

    def test_button_mit_override_wird_genauso_geprueft(self):
        html = '<button aria-label="Menü">Menü öffnen</button>'
        issues = audit.link_name_issues(html)
        self.assertEqual(len(issues), 1, issues)
        self.assertIn("Menü öffnen", issues[0])

    def test_audit_page_meldet_den_befund_im_seitenbericht(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp)
            path = public / "seite.html"
            path.write_text(
                '<html lang="de"><title>Seite</title><a class="skip-link" href="#main">Skip</a>'
                '<h1>Seite</h1>'
                '<a aria-label="Weiterlesen: Titel" href="/x/">Titel<span>Datum 26.10.2026</span></a>'
                '</html>',
                encoding="utf-8",
            )
            _, issues = audit.audit_page(path, public)
        self.assertTrue(any("WCAG 2.5.3" in issue for issue in issues), issues)


if __name__ == "__main__":
    unittest.main()
