#!/usr/bin/env python3
"""Regressionen für den Produktvertrag der Werkzeuge.

Der Test prüft drei Ebenen:
  1. Die echte SSOT und der echte Quellbaum sind grün.
  2. Jede Kernregel bricht, wenn man sie sabotiert (sonst wäre das Gate
     ein grüner Haken ohne Aussage).
  3. Die Wache ist in der CI tatsächlich verdrahtet – vor dem Build gegen
     die Quelle, nach dem Build gegen das Ergebnis.
"""
from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import werkzeuge_gate as guard  # noqa: E402


def seite(versprechen: str, werkzeug: str, engine: str, quellen: list[str]) -> str:
    """Minimale, vertragstreue Werkzeugseite für die Build-Prüfung."""
    quellen_html = "".join(
        f'<li data-ff-wz-quelle data-url="{url}"><a href="{url}">Quelle</a></li>' for url in quellen
    )
    return (
        '<article><noscript>Braucht JavaScript</noscript>'
        f'<section data-ff-werkzeug data-werkzeug="{werkzeug}" data-engine="{engine}">'
        f"<p>{versprechen}</p>"
        '<form novalidate><input data-feld="x"></form>'
        '<ol data-ff-wz-formel><li>Schritt eins</li><li>Schritt zwei</li></ol>'
        '<ul data-ff-wz-annahme><li>Eine Annahme</li></ul>'
        f"<ul>{quellen_html}</ul>"
        "</section>"
        '<script src="/premium/ff-werkzeuge.js"></script>'
        '<script type="application/ld+json">{"@type":"SoftwareApplication","isAccessibleForFree":true}</script>'
        "</article>"
    )


class WerkzeugeVertragTests(unittest.TestCase):
    def setUp(self):
        self.data = yaml.safe_load((ROOT / "data" / "werkzeuge.yaml").read_text(encoding="utf-8"))

    # ---------------------------------------------------------- Positivprobe

    def test_quelle_selbsttest_und_inhalt_sind_gruen(self):
        self.assertEqual(guard.validate_data(self.data), [])
        self.assertEqual(guard.validate_content(self.data), [])
        self.assertEqual(guard.validate_source(), [])
        self.assertEqual(guard.selftest(), [])

    def test_acht_werkzeuge_mit_eindeutigen_ids_und_slugs(self):
        werkzeuge = self.data["werkzeuge"]
        self.assertEqual(len(werkzeuge), guard.ANZAHL_WERKZEUGE)
        self.assertEqual(len({w["id"] for w in werkzeuge}), guard.ANZAHL_WERKZEUGE)
        self.assertEqual(len({w["slug"] for w in werkzeuge}), guard.ANZAHL_WERKZEUGE)
        self.assertEqual(len({w["engine"] for w in werkzeuge}), guard.ANZAHL_WERKZEUGE)

    def test_jedes_werkzeug_hat_seite_und_jede_seite_ein_werkzeug(self):
        slugs = {w["slug"] for w in self.data["werkzeuge"]}
        seiten = {p.parent.name for p in (ROOT / "content" / "werkzeuge").glob("*/index.md")}
        self.assertEqual(slugs, seiten)

    # ---------------------------------------------------------- Sabotageproben

    def test_abgeschwaechtes_versprechen_blockiert(self):
        kaputt = copy.deepcopy(self.data)
        kaputt["versprechen"] = "Du kannst das Tool weitgehend ohne Affiliate-Link nutzen."
        self.assertTrue(any(f.startswith("W1") for f in guard.validate_data(kaputt)))

    def test_werkzeug_ohne_quelle_oder_formel_blockiert(self):
        ohne_quelle = copy.deepcopy(self.data)
        ohne_quelle["werkzeuge"][0]["quellen"] = []
        self.assertTrue(any(f.startswith("W5") for f in guard.validate_data(ohne_quelle)))

        ohne_formel = copy.deepcopy(self.data)
        ohne_formel["werkzeuge"][0]["formel"] = ["Nur ein Schritt"]
        self.assertTrue(any(f.startswith("W5") for f in guard.validate_data(ohne_formel)))

        quelle_ohne_stand = copy.deepcopy(self.data)
        quelle_ohne_stand["werkzeuge"][0]["quellen"][0]["stand"] = "neulich"
        self.assertTrue(any(f.startswith("W5") for f in guard.validate_data(quelle_ohne_stand)))

    def test_unsichere_oder_unbekannte_feldtypen_blockieren(self):
        kaputt = copy.deepcopy(self.data)
        kaputt["werkzeuge"][0]["felder"][0]["typ"] = "freitext"
        self.assertTrue(any(f.startswith("W2") for f in guard.validate_data(kaputt)))

        korridor = copy.deepcopy(self.data)
        korridor["werkzeuge"][0]["felder"][0]["sparkorridor"] = [0.6, 0.2]
        self.assertTrue(any("sparkorridor" in f for f in guard.validate_data(korridor)))

    def test_fehlende_seite_wird_erkannt(self):
        kaputt = copy.deepcopy(self.data)
        kaputt["werkzeuge"][0]["slug"] = "gibt-es-nicht"
        befunde = guard.validate_content(kaputt)
        self.assertTrue(any("gibt-es-nicht" in f for f in befunde))

    # ---------------------------------------------------------- W8 VERDRAHTUNG

    def _sandkasten(self, tmp: str, *, link: bool = True,
                    lastmod: bool = True) -> Path:
        """Minimaler Quellbaum: ein Pillar, ein Artikel, eine Werkzeugseite.

        validate_embedding liest nur `content/`, deshalb reicht dieser Rumpf –
        die echte SSOT bleibt der Maßstab für die IDs."""
        wurzel = Path(tmp)
        pillar = wurzel / "content" / "pillar" / self.PILLAR
        pillar.mkdir(parents=True)
        text = "## Rechner\n\n"
        if link:
            text += f"Siehe [Werkzeug](/werkzeuge/{self.SLUG}/).\n"
        (pillar / "index.md").write_text(text, encoding="utf-8")
        post = wurzel / "content" / "posts" / "2026-10-10-test"
        post.mkdir(parents=True)
        kopf = ("---\ntitle: Test\nlastmod: 2026-10-10\n---\n\n" if lastmod
                else "---\ntitle: Test\n---\n\n")
        (post / "index.md").write_text(kopf + "{{< werkzeug id=\"notgroschen\" >}}\n",
                                        encoding="utf-8")
        werkz = wurzel / "content" / "werkzeuge" / self.SLUG
        werkz.mkdir(parents=True)
        (werkz / "index.md").write_text("---\nwerkzeug: notgroschen\n---\n\n## Frage?\n\nFrage?\n",
                                        encoding="utf-8")
        return wurzel

    PILLAR = "frugalismus"
    SLUG = "notgroschen-rechner"

    def test_w8_verdrahtung_ist_im_echten_baum_gruen(self):
        self.assertEqual(guard.validate_embedding(self.data), [])

    def test_jedes_werkzeug_ist_seinem_pillar_verlinkt(self):
        for w in self.data["werkzeuge"]:
            seite = ROOT / "content" / "pillar" / w["pillar"] / "index.md"
            self.assertIn(f"/werkzeuge/{w['slug']}/", seite.read_text(encoding="utf-8"),
                          f"{w['slug']} hängt nicht in {seite.parent.name}")

    def test_w8_blockiert_verwaistes_werkzeug(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = self._sandkasten(tmp, link=False)
            befunde = guard.validate_embedding(self.data, wurzel)
            self.assertTrue(any(f.startswith("W8") and self.SLUG in f for f in befunde),
                            f"unverlinktes Werkzeug läuft durch: {befunde}")

    def test_w8_blockiert_unbekannte_und_nackte_einbettung(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = self._sandkasten(tmp)
            post = wurzel / "content" / "posts" / "2026-10-10-test" / "index.md"
            text = post.read_text(encoding="utf-8") + '{{< werkzeug id="phantom" >}}\n'
            post.write_text(text, encoding="utf-8")
            befunde = guard.validate_embedding(self.data, wurzel)
            self.assertTrue(any("phantom" in f for f in befunde), befunde)
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = self._sandkasten(tmp)
            post = wurzel / "content" / "posts" / "2026-10-10-test" / "index.md"
            post.write_text("---\ntitle: T\nlastmod: 2026-10-10\n---\n\n{{< werkzeug >}}\n",
                            encoding="utf-8")
            befunde = guard.validate_embedding(self.data, wurzel)
            self.assertTrue(any("ohne id=" in f for f in befunde), befunde)

    def test_w8_verlangt_lastmod_fuer_geaenderte_ratgeber(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = self._sandkasten(tmp, lastmod=False)
            befunde = guard.validate_embedding(self.data, wurzel)
            self.assertTrue(any("lastmod" in f for f in befunde), befunde)

    def test_w8_aendert_nichts_an_der_Werbefreiheit_der_werkzeugseiten(self):
        """Einbettungen sind der Weg ZUM Werkzeug – W3 bleibt unangetastet."""
        for seite in sorted((ROOT / "content" / "werkzeuge").glob("*/index.md")):
            self.assertNotIn("/go/", seite.read_text(encoding="utf-8"),
                            f"{seite} wirbt – W3 verbietet das")
        self.assertTrue(guard.einbettungen(), "ohne Einbettungen wäre W8 bloße Deko")

    def test_partnerlink_wird_in_jeder_spielart_erkannt(self):
        domains = guard.partner_domains() or {"check24.net"}
        beispiel = sorted(domains)[0]
        self.assertTrue(guard.partnerlinks('<a href="/go/strom/">x</a>', domains))
        self.assertTrue(guard.partnerlinks('<a rel="sponsored nofollow" href="https://x.test/">x</a>', domains))
        self.assertTrue(guard.partnerlinks(f'<a href="https://{beispiel}/dsl/">x</a>', domains))
        self.assertFalse(guard.partnerlinks('<a href="/pillar/strom-sparen/">Ratgeber</a>', domains))
        # Quellenlinks auf Gesetzestexte sind keine Partnerlinks.
        self.assertFalse(guard.partnerlinks('<a href="https://www.gesetze-im-internet.de/bgb/__130.html">§ 130</a>', domains))

    # ---------------------------------------------------------- Build-Vertrag

    def _build(self, tmp: str, mutieren=None) -> list[str]:
        public = Path(tmp)
        hub = ["<h1>Werkzeuge</h1>", f"<p>{guard.VERSPRECHEN}</p>"]
        (public / "werkzeuge").mkdir(parents=True)
        for w in self.data["werkzeuge"]:
            hub.append(f'<a href="/werkzeuge/{w["slug"]}/">{w["name"]}</a>')
            ordner = public / "werkzeuge" / w["slug"]
            ordner.mkdir()
            html = seite(guard.VERSPRECHEN, w["id"], w["engine"], [q["url"] for q in w["quellen"]])
            if mutieren:
                html = mutieren(w, html)
            (ordner / "index.html").write_text(html, encoding="utf-8")
        (public / "werkzeuge" / "index.html").write_text("".join(hub), encoding="utf-8")
        return guard.validate_build(public, self.data)

    def test_minimaler_vertragstreuer_build_ist_gruen(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self._build(tmp), [])

    def test_build_ohne_versprechen_blockiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            befunde = self._build(tmp, lambda w, html: html.replace(guard.VERSPRECHEN, "Jetzt vergleichen"))
            self.assertTrue(any(f.startswith("W1") for f in befunde))

    def test_build_mit_partnerlink_blockiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            befunde = self._build(tmp, lambda w, html: html.replace("</article>", '<a href="/go/dsl/">Angebot</a></article>'))
            self.assertEqual(len([f for f in befunde if f.startswith("W3")]), guard.ANZAHL_WERKZEUGE)

    def test_build_mit_formularziel_blockiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            befunde = self._build(tmp, lambda w, html: html.replace("<form novalidate>", '<form action="/api/rechnen">'))
            self.assertTrue(any(f.startswith("W6") for f in befunde))

    def test_build_mit_versteckter_methodik_blockiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            befunde = self._build(
                tmp,
                lambda w, html: html.replace("<ol data-ff-wz-formel>", "<details><summary>Methodik</summary><ol data-ff-wz-formel>")
                .replace("</ol>", "</ol></details>", 1),
            )
            self.assertTrue(any(f.startswith("W7") for f in befunde))

    def test_build_mit_externem_asset_blockiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            befunde = self._build(tmp, lambda w, html: html.replace("</article>", '<script src="https://cdn.example.test/x.js"></script></article>'))
            self.assertTrue(any(f.startswith("W6") for f in befunde))

    def test_build_ohne_quellenlink_blockiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            befunde = self._build(tmp, lambda w, html: html.replace(w["quellen"][0]["url"], "https://beliebig.test/"))
            self.assertTrue(any(f.startswith("W5") for f in befunde))

    # ---------------------------------------------------------- CI-Verdrahtung

    def test_deploy_prueft_quelle_vor_und_build_nach_dem_hugo_lauf(self):
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/werkzeuge_gate.py --selftest", workflow)
        self.assertIn("python3 scripts/werkzeuge_gate.py --source-only", workflow)
        self.assertIn("python3 scripts/werkzeuge_gate.py --public public", workflow)
        # Anker nachgezogen 03.10.2026 (gemeinsame hugo-build-Action).
        # Der Vertrag bleibt: Quelle vor dem Bau, Produkt nach dem Bau.
        self.assertLess(
            workflow.index("Werkzeuge – Quell- und Datenschutzvertrag"),
            workflow.index("uses: ./.github/actions/hugo-build"),
        )
        self.assertLess(
            workflow.index("Werkzeuge – finales Produkt-Gate"),
            workflow.index("- name: Deploy auf gh-pages"),
        )

    def test_npm_skripte_sind_vorhanden(self):
        paket = (ROOT / "package.json").read_text(encoding="utf-8")
        self.assertIn("python3 scripts/werkzeuge_gate.py --selftest", paket)
        self.assertIn("node --test tools/werkzeuge.test.mjs", paket)

    def test_rechenkern_bleibt_lokal_und_testbar(self):
        script = (ROOT / "static/premium/ff-werkzeuge.js").read_text(encoding="utf-8")
        code = script[script.index("(function ()"):]
        for verboten in ("fetch(", "XMLHttpRequest", "sendBeacon", "document.cookie", ".innerHTML ="):
            self.assertNotIn(verboten, code)
        self.assertIn("FFWerkzeuge", code)
        self.assertIn("merken.checked", code)
        for w in self.data["werkzeuge"]:
            self.assertIn(f"logik.{w['engine']} =", code)


if __name__ == "__main__":
    unittest.main()
