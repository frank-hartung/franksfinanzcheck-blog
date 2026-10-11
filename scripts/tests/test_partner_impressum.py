#!/usr/bin/env python3
"""Die Tarifcheck-Anbieterkennzeichnung bleibt ein iframe mit der
Programm-URL – und die URL steht nicht im Markdown, wo der
Affiliate-Shield sie auf eine /go/-Route umbiegen würde.
"""
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = "https://a.partner-versicherung.de/filestore/ad/1166/index.php?partner_id=47086"


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
        return handle.read()


class TestPartnerImpressum(unittest.TestCase):
    def test_impressum_ruft_den_shortcode_auf_ohne_rohe_partner_url(self):
        text = read("content/impressum/index.md")
        self.assertIn("{{< partner_impressum >}}", text)
        self.assertIn("Verantwortliche für vermittelte Versicherungsangebote", text)
        self.assertNotIn("a.partner-versicherung.de", text)
        self.assertNotIn("https://a.check24.net", text)

    def test_shortcode_traegt_das_programmsnippet(self):
        text = read("layouts/shortcodes/partner_impressum.html")
        self.assertIn(f'src="{{{{ $src }}}}"', text)
        self.assertIn(SRC, text)
        for attr in ('width="100%"', 'scrolling="no"', 'border="0"', "title="):
            self.assertIn(attr, text)
        self.assertIn("ff-partner-impressum.js", text)

    def test_datenschutz_nennt_den_abruf_ohne_klick_url(self):
        text = read("content/datenschutz/index.md")
        self.assertIn('id="partner-kennzeichnung"', text)
        self.assertIn("a.partner-versicherung.de", text)
        self.assertNotIn(SRC, text)
        self.assertNotIn("erst nach einem Klick auf ihren Link", text)

    def test_css_deckt_hell_und_dunkel_ab(self):
        css = read("assets/css/extended/ff-partner-impressum.css")
        for selector in (
            ".ff-partner-impressum__frame",
            ':root[data-theme="dark"] .ff-partner-impressum__kicker',
            "@media print",
        ):
            self.assertIn(selector, css)
        self.assertIn("min-height", css)
        self.assertIn("kein CTA", css)
        self.assertIn(".ff-partner-impressum p.ff-partner-impressum__meta", css)


if __name__ == "__main__":
    unittest.main()
