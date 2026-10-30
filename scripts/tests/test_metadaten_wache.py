"""Unit-Tests der Metadaten-Wache (scripts/metadaten_wache.py).

Die Fälle spiegeln die realen Befunde aus dem Audit #743 wider: zu lange
Pillar-Titel, zu lange Description, lastmod vor date, unbelegte Spar-Pillen
(„1.250 €“, „ab ca. 5 € im Monat“) und Entwürfe, die nicht bewertet werden.
"""
import unittest

import scripts.metadaten_wache as w

GOOD = """---
title: "Strom sparen: Ratgeber für den Alltag"
description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."
date: 2026-09-01T06:00:00Z
lastmod: 2026-09-02
draft: false
quellen:
  - titel: "Quelle"
    url: "https://example.org"
kurzantwort: "Kurze, belastbare Antwort."
faktencheck: "2026-10-01"
cover:
  image: "images/covers/gut.jpg"
  alt: "Titelbild Strom sparen"
---

Im Text stehen 360 € im Jahr als Beleg.
"""


def rules(text, pill_fn=None, cover_exists=None, rel="content/posts/x/index.md"):
    found = w.check_document(rel, text, cover_exists=cover_exists or (lambda p: True),
                             pill_fn=pill_fn)
    return sorted({f["rule"] for f in found})


class MetadatenWacheTests(unittest.TestCase):
    def test_sauberer_artikel_hat_keinen_befund(self):
        self.assertEqual(rules(GOOD), [])

    def test_titel_ueber_60_zeichen_ist_befund(self):
        text = GOOD.replace('title: "Strom sparen: Ratgeber für den Alltag"',
                            'title: "Strom sparen: Der sehr große Ratgeber für niedrige Energiekosten im Haushalt"')
        self.assertIn("M1", rules(text))

    def test_pillar_titel_mit_72_zeichen_ist_befund(self):
        # Realer Befund: Pillar „Frugalismus“ vor der Kürzung
        text = GOOD.replace('title: "Strom sparen: Ratgeber für den Alltag"',
                            'title: "Haushaltsbudget & Frugalismus: Der große Ratgeber für finanzielle Puffer"')
        self.assertIn("M1", rules(text))

    def test_description_zu_lang_und_zu_kurz(self):
        long_ = GOOD.replace("Mit einfachen Rechenbeispielen für jeden Haushalt.",
                             "Mit einfachen Rechenbeispielen für jeden Haushalt und noch mehr Details dazu.")
        self.assertIn("M2", rules(long_))
        short = GOOD.replace('description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
                             'description: "Zu kurz."')
        self.assertIn("M2", rules(short))

    def test_description_zu_breit_ist_befund(self):
        # 27.10.2026 (Screaming-Frog-Befund „über 985 Pixel"): 135 Zeichen
        # passen in M2, laufen in Arial 14 px aber über die Snippet-Breite.
        breit = ("Wohngebäude und Wärmewende: Warum Wärmeverlust, Wärmepumpe und Wartung "
                 "zusammengehören. Wer Wohnraum warm hält, spart mit Wärmedämmung.")
        text = GOOD.replace(
            'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
            f'description: "{breit}"')
        self.assertEqual(rules(text), ["M7"])
        self.assertLessEqual(len(breit), w.DESC_MAX)

    def test_description_mit_zeichen_ohne_breitenmass_ist_befund(self):
        text = GOOD.replace('für jeden Haushalt."', 'für jeden Haushalt. 💡"')
        self.assertEqual(rules(text), ["M7"])

    def test_grenzen_kommen_aus_der_ssot(self):
        # Keine zweite Zahl im Haus: metadaten_wache liest die Grenzen aus
        # scripts/serp_limits.py, das SEO-Cockpit prüft dieselben.
        import scripts.serp_limits as sl
        self.assertEqual((w.DESC_MIN, w.DESC_MAX), (sl.DESC_MIN_ZEICHEN, sl.DESC_MAX_ZEICHEN))

    def test_lastmod_vor_date_ist_befund(self):
        self.assertIn("M3", rules(GOOD.replace("lastmod: 2026-09-02", "lastmod: 2026-08-01")))

    def test_veroeffentlicht_ohne_quelle_und_kurzantwort(self):
        text = GOOD.replace('quellen:\n  - titel: "Quelle"\n    url: "https://example.org"\n', "quellen: []\n")
        text = text.replace('kurzantwort: "Kurze, belastbare Antwort."\n', "")
        self.assertEqual(rules(text), ["M4"])

    def test_entwurf_wird_nicht_als_veroeffentlicht_bewertet(self):
        text = GOOD.replace("draft: false", "draft: true").replace(
            'kurzantwort: "Kurze, belastbare Antwort."\n', "").replace("quellen:", "quellen_x:")
        self.assertEqual(rules(text), [])

    def test_cover_datei_fehlt(self):
        self.assertIn("M4", rules(GOOD, cover_exists=lambda p: False))

    def test_zahlenversprechen_ohne_einheit_im_text_ist_befund(self):
        # „Schritt 5“ im Text belegt kein „5 € im Monat“
        text = GOOD.replace('---\n\nIm Text stehen 360 € im Jahr als Beleg.',
                            '---\n\nSchritt 5 erklärt den Ablauf.')
        text = text.replace('title: "Strom sparen: Ratgeber für den Alltag"',
                            'title: "Strom sparen: Ratgeber für den Alltag"\nsavings: "ab ca. 5 € im Monat"')
        self.assertIn("M6", rules(text, pill_fn=lambda t, d, e: e))

    def test_zahlenversprechen_mit_einheit_im_text_ist_belegt(self):
        text = GOOD.replace('title: "Strom sparen: Ratgeber für den Alltag"',
                            'title: "Strom sparen: Ratgeber für den Alltag"\nsavings: "bis zu 360 € im Jahr sparen"')
        self.assertNotIn("M6", rules(text, pill_fn=lambda t, d, e: e))

    def test_claim_in_body_verlangt_einheit(self):
        self.assertTrue(w._claim_in_body("360", "bis zu 360 € sparen", "Du sparst 360 € im Jahr."))
        self.assertFalse(w._claim_in_body("5", "ab ca. 5 € im Monat", "Schritt 5 und 5 Fehler."))
        self.assertTrue(w._claim_in_body("40", "bis zu 40 % sparen", "bis zu **40&nbsp;%** sparst"))

    def test_eindeutigkeit_ueber_veroeffentlichte_dokumente(self):
        found = w.check_uniqueness([("a.md", "Gleich", "d1"), ("b.md", "Gleich", "d2")])
        self.assertEqual({f["rule"] for f in found}, {"M5"})
        self.assertEqual(len(found), 2)

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(w.run_selftest(), 0)


# ---------------------------------------------------------------------------
#  Heilung an der Quelle (WF-7B6B / #925, 29.10.2026)
# ---------------------------------------------------------------------------
VORFALL_925 = (
    "DSL Hacks: WLAN-Verstärker oder Mesh-WLAN? So findest du 2026 heraus, "
    "was dein Zuhause wirklich braucht – mit klaren Kosten und einer "
    "Entscheidungshilfe."
)


class SnippetHeilungTests(unittest.TestCase):
    """Der Heiler darf die SSOT nicht verletzen – und muss nicht können,
    was er nicht kann (verlängern, unmessbar in der Satzmitte)."""

    def test_vorfall_925_wird_geheilt(self):
        text = GOOD.replace(
            'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
            f'description: "{VORFALL_925}"')
        self.assertIn("M7", rules(text))  # vorher: über 985 px
        geheilt, meldung = w.heile_snippet("content/posts/x/index.md", text)
        self.assertTrue(meldung, "der #925-Befund wurde nicht geheilt")
        self.assertNotIn("M7", rules(geheilt))
        self.assertNotIn("M2", rules(geheilt))
        # idempotent
        self.assertEqual(w.heile_snippet("content/posts/x/index.md", geheilt)[1], [])
        # nur die Description-Zeile ist berührt
        self.assertEqual(
            geheilt.count("\n"), text.count("\n"),
            "die Heilung hat Zeilen verändert")

    def test_passende_description_bleibt_unberuehrt(self):
        self.assertEqual(w.heile_snippet("x.md", GOOD)[1], [])

    def test_zu_kurze_description_wird_nicht_verlaengert(self):
        text = GOOD.replace(
            'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
            'description: "Zu kurz."')
        self.assertEqual(w.heile_snippet("x.md", text)[1], [])
        self.assertIn("M2", rules(text))

    def test_unmessbar_in_der_mitte_bleibt_liegen(self):
        text = GOOD.replace(
            'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
            'description: "Strom sparen \U0001F4A1 im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge planen. Mit einfachen Rechenbeispielen für den Haushalt."')
        self.assertEqual(w.heile_snippet("x.md", text)[1], [])
        self.assertIn("M7", rules(text))

    def test_lastmod_vor_date_wird_auf_publikationstag_gehoben(self):
        text = GOOD.replace("lastmod: 2026-09-02", "lastmod: 2026-08-01")
        self.assertIn("M3", rules(text))
        geheilt, meldung = w.heile_lastmod("x.md", text)
        self.assertTrue(meldung)
        self.assertIn("lastmod: 2026-09-01", geheilt)
        self.assertNotIn("M3", rules(geheilt))
        self.assertEqual(w.heile_lastmod("x.md", geheilt)[1], [])

    def test_entwurf_wird_nicht_geheilt(self):
        text = GOOD.replace("draft: false", "draft: true").replace(
            "lastmod: 2026-09-02", "lastmod: 2026-08-01")
        self.assertEqual(w.heile_lastmod("x.md", text)[1], [])

    def test_fix_heilt_den_baum_und_konvergiert(self):
        """Dateischreibtest in einem isolierten Bestand, niemals im Checkout."""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        text = GOOD.replace(
            'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
            f'description: "{VORFALL_925}"')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "content/posts/test/index.md"
            path.parent.mkdir(parents=True)
            path.write_text(text, encoding="utf-8")
            with patch.object(w, "_pill_fn", return_value=lambda *_: None):
                findings, _, healed = w.run(root=tmp, heilen=True)
                self.assertTrue(healed)
                self.assertFalse(any(f["rule"] in ("M2", "M7") for f in findings))
                self.assertFalse(w.run(root=tmp, heilen=True)[2])

    def test_versiegelter_entwurf_bleibt_unveraendert_und_befund_sichtbar(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        text = GOOD.replace("draft: false", "draft: true").replace(
            'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
            f'description: "{VORFALL_925}"').replace(
            "---\n\nIm Text", "redaktionelle_pruefung:\n  status: freigegeben\n  inhalt_sha256: kaputt\n---\n\nIm Text")
        import editorial_review_gate as gate
        fm_text, body = gate.split_article(text)
        fm = gate._yaml_module().safe_load(fm_text)
        digest = gate.content_fingerprint(fm, body)
        # Beide Fälle schützen: ein gültiges Siegel und ein bereits kaputtes.
        for version in (text, text.replace('inhalt_sha256: kaputt', f'inhalt_sha256: {digest}')):
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "content/posts/test/index.md"
                path.parent.mkdir(parents=True)
                path.write_text(version, encoding="utf-8")
                with patch.object(w, "_pill_fn", return_value=lambda *_: None):
                    findings, _, healed = w.run(root=tmp, heilen=True)
                self.assertEqual(path.read_text(encoding="utf-8"), version)
                self.assertFalse(healed)
                self.assertTrue(any(f["rule"] == "M7" for f in findings))

    def test_ausfall_des_schreibvertrags_verhindert_snippet_heilung(self):
        from unittest.mock import patch
        import editorial_review_gate as gate
        text = GOOD.replace(
            'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
            f'description: "{VORFALL_925}"')
        with patch.object(gate, 'automatic_change_findings', side_effect=RuntimeError('Ausfall')):
            self.assertEqual(w.heile_snippet('x.md', text), (text, []))

    def test_lastmod_bleibt_trotz_siegelschutz_heilbar(self):
        text = GOOD.replace("lastmod: 2026-09-02", "lastmod: 2026-08-01").replace(
            'description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge richtig planen. Mit einfachen Rechenbeispielen für jeden Haushalt."',
            f'description: "{VORFALL_925}"').replace(
            "---\n\nIm Text", "redaktionelle_pruefung:\n  status: freigegeben\n  inhalt_sha256: kaputt\n---\n\nIm Text")
        healed, messages = w.heile_datei("content/posts/x/index.md", text)
        self.assertIn(f'description: "{VORFALL_925}"', healed)
        self.assertIn("lastmod: 2026-09-01", healed)
        self.assertEqual(len(messages), 1)


if __name__ == "__main__":
    unittest.main()
