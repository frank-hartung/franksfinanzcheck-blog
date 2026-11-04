"""Tests der Pillar-Wiedervorlage (Vorgang WF-0032, 04.11.2026).

WARUM DIESE TESTS
-----------------
Am 04.11.2026 gingen zwei Artikel des Versicherungs-Clusters live; der
Pillar sagte weiter „(Ratgeber in Vorbereitung)“. Die Wiedervorlage dafür
gab es – `test_versicherungs_cluster_verlinkung.py` –, aber sie lief nur
bei Pull Requests. Der Artikel kam über einen Automatik-Commit auf main.

Diese Tests prüfen deshalb NICHT den Bestand (das tut `--check` täglich),
sondern das URTEIL: Sie frieren ein, dass die Wache anschlägt, wenn sie
soll, und schweigt, wenn nicht. Ein Test gegen den heutigen Bestand wäre
am nächsten Veröffentlichungstag grün und am übernächsten rot – und würde
nichts beweisen.

Die Fälle sind bewusst als Paare gebaut (Befund / Gegenprobe). Eine Wache,
die nur anschlägt, ist so unbrauchbar wie eine, die nie anschlägt.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import pillar_wiedervorlage as pw  # noqa: E402


def artikel(slug: str, titel: str, *, entwurf: bool = False,
            pillar: str = "versicherungen") -> pw.Artikel:
    return pw.Artikel(slug=slug, titel=titel, entwurf=entwurf, pillar=pillar,
                      pfad=f"content/posts/{slug}/index.md")


ZIEL = Path("content/pillar/versicherungen/index.md")


class PflichtlinkTests(unittest.TestCase):
    """R1 – DER VORFALL: Ein Pflicht-Artikel ist live und fehlt im Pillar."""

    def setUp(self) -> None:
        self.bestand = {
            "wohn-live": artikel("wohn-live", "Wohngebäudeversicherung Vergleich"),
            "kfz-entwurf": artikel("kfz-entwurf", "Kfz-Versicherung Vergleich",
                                   entwurf=True),
        }

    def test_live_ohne_link_wird_gemeldet(self):
        offen = pw.pruefe(ZIEL, self.bestand, "## Gebäude\n\nText.\n",
                          pflicht=["wohn-live"])
        self.assertEqual([b.klasse for b in offen], ["P1-PFLICHTLINK-FEHLT"])
        self.assertIn("wohn-live", offen[0].meldung.lower().replace(
            "wohngebäudeversicherung vergleich", "wohn-live"))

    def test_mit_link_ist_sauber(self):
        text = ("## Gebäude\n\nDer [Vergleich](../../posts/wohn-live/) zeigt "
                "Elementarschutz und Klauseln.\n")
        self.assertEqual(pw.pruefe(ZIEL, self.bestand, text,
                                   pflicht=["wohn-live"]), [])

    def test_entwurf_ist_keine_pflicht(self):
        """Ein Entwurf darf fehlen – er ist ja noch nicht live."""
        self.assertEqual(pw.pruefe(ZIEL, self.bestand, "## Kfz\n\nText.\n",
                                   pflicht=[]), [])

    def test_unbekannter_pflicht_slug_ist_werkzeugfehler(self):
        """Ein Vertrag, der ins Leere zeigt, ist ein Fehler – kein Befund."""
        with self.assertRaises(pw.WerkzeugFehler):
            pw.pruefe(ZIEL, self.bestand, "Text.", pflicht=["gibt-es-nicht"])


class EntwurfslinkTests(unittest.TestCase):
    """R2 – Ein verlinkter Entwurf ist sofort ein totes Linkziel (W11)."""

    def test_verlinkter_entwurf_wird_gemeldet(self):
        bestand = {"kfz-entwurf": artikel("kfz-entwurf", "Kfz-Vergleich",
                                          entwurf=True)}
        offen = pw.pruefe(ZIEL, bestand,
                          "## Kfz\n\n[Vergleich](../../posts/kfz-entwurf/)\n",
                          pflicht=[])
        self.assertEqual([b.klasse for b in offen], ["P2-ENTWURF-VERLINKT"])

    def test_fremder_live_artikel_ist_kein_toter_link(self):
        bestand = {"dsl-live": artikel("dsl-live", "DSL Tarif",
                                       pillar="internet-dsl")}
        offen = pw.pruefe(ZIEL, bestand,
                          "## DSL\n\n[DSL](../../posts/dsl-live/)\n", pflicht=[])
        self.assertNotIn("P2-ENTWURF-VERLINKT", [b.klasse for b in offen])


class PlatzhalterTests(unittest.TestCase):
    """R3 – „(Ratgeber in Vorbereitung)“ über einem ausgelieferten Ratgeber."""

    def setUp(self) -> None:
        self.bestand = {
            "wohn-live": artikel(
                "wohn-live",
                "Wohngebäudeversicherung Vergleich: Worauf du achten musst"),
            "vorsorge-live": artikel(
                "vorsorge-live",
                "Dein Haus sicher schützen: Das neue Vorsorge-Update 2026"),
            "kfz-entwurf": artikel("kfz-entwurf", "Kfz-Versicherung Vergleich",
                                   entwurf=True),
        }

    def test_platzhalter_trotz_live_wird_gemeldet(self):
        text = ("## Gebäude\n\nFür Eigentümer vertieft ein eigener "
                "Wohngebäudeversicherungs-Vergleich die Tarifwahl "
                "(Ratgeber in Vorbereitung).\n")
        offen = pw.pruefe(ZIEL, self.bestand, text, pflicht=["wohn-live"])
        self.assertIn("P3-PLATZHALTER-TROTZ-LIVE", [b.klasse for b in offen])

    def test_platzhalter_ohne_live_artikel_ist_kein_befund(self):
        text = "## Kfz\n\nDer Vergleich folgt (Ratgeber in Vorbereitung).\n"
        offen = pw.pruefe(ZIEL, self.bestand, text, pflicht=["kfz-entwurf"])
        self.assertNotIn("P3-PLATZHALTER-TROTZ-LIVE", [b.klasse for b in offen])

    def test_bezug_ist_der_satzteil_vor_dem_platzhalter(self):
        """Der Fehler, den diese Regel hatte: Die ZEILE ist zu breit.

        „… Wohngebäudeversicherungs-Vergleich die Tarifwahl (Ratgeber in
        Vorbereitung). Wer …, findet im [Vorsorge-Update] …“ – der
        Platzhalter gehört zum Wohngebäude-Vergleich. Eine Zeilen-
        Heuristik meldete das Vorsorge-Update, weil es in derselben Zeile
        steht und mehr Wortstämme teilt.
        """
        text = ("## Gebäude\n\nFür Eigentümer vertieft ein eigener "
                "Wohngebäudeversicherungs-Vergleich die Tarifwahl (Ratgeber in "
                "Vorbereitung). Wer Gebäude, Hausrat und Naturgefahren zusammen "
                "denken will, findet im [Vorsorge-Update]"
                "(../../posts/vorsorge-live/) den Überblick.\n")
        offen = pw.pruefe(ZIEL, self.bestand, text, pflicht=["wohn-live"])
        p3 = [b for b in offen if b.klasse == "P3-PLATZHALTER-TROTZ-LIVE"]
        self.assertEqual(len(p3), 1, f"genau ein Befund erwartet, nicht {len(p3)}")
        self.assertIn("Wohngebäudeversicherung", p3[0].meldung)
        self.assertNotIn("Vorsorge-Update", p3[0].meldung)


class QuerverbindungsTests(unittest.TestCase):
    """R4 – Eine Querverbindung in ein fremdes Themenfeld ist sichtbar."""

    def test_querverbindung_wird_gemeldet(self):
        bestand = {"dsl-live": artikel("dsl-live", "DSL Tarif",
                                       pillar="internet-dsl")}
        offen = pw.pruefe(ZIEL, bestand, "[DSL](../../posts/dsl-live/)\n",
                          pflicht=[])
        self.assertEqual([b.klasse for b in offen], ["P4-QUERVERBINDUNG"])

    def test_eigener_artikel_ist_keine_querverbindung(self):
        bestand = {"wohn-live": artikel("wohn-live", "Wohngebäude")}
        offen = pw.pruefe(ZIEL, bestand, "[W](../../posts/wohn-live/)\n",
                          pflicht=["wohn-live"])
        self.assertEqual(offen, [])


class LinkLesartTests(unittest.TestCase):
    """Welche Links zählen als Artikel-Link – dieselbe Lesart wie im Alttest."""

    def test_nur_relative_post_links_zaehlen(self):
        self.assertEqual(
            pw.PILLAR_LINK.findall(
                "[A](../../posts/a/) [B](/posts/b/) [C](/go/haftpflicht/)"),
            ["a"])

    def test_linktext_mit_klammern_bricht_nicht(self):
        self.assertEqual(
            pw.PILLAR_LINK.findall("[Vergleich (2026)](../../posts/wohn-live/)"),
            ["wohn-live"])


class FrontmatterTests(unittest.TestCase):
    """Die Frontmatter-Lesart muss mit Hugo übereinstimmen – nicht fast."""

    def test_draft_true_ist_entwurf(self):
        for wert in ("true", "True", "TRUE", "yes", "1"):
            self.assertTrue(pw.ist_entwurf({"draft": wert}), wert)

    def test_fehlendes_draft_ist_live(self):
        """Hugo-Default ist `false`. Ein fehlendes Feld ist kein Entwurf."""
        self.assertFalse(pw.ist_entwurf({}))
        self.assertFalse(pw.ist_entwurf({"draft": "false"}))

    def test_frontmatter_liest_flache_werte(self):
        text = '---\ntitle: "Ein: Titel"\ndraft: false\npillar: "versicherungen"\n---\n\nBody\n'
        fm = pw.frontmatter(text)
        self.assertEqual(fm["title"], "Ein: Titel")
        self.assertEqual(fm["pillar"], "versicherungen")
        self.assertEqual(fm["draft"], "false")

    def test_ohne_frontmatter_ist_live(self):
        self.assertEqual(pw.frontmatter("Nur Text."), {})


class VertragTests(unittest.TestCase):
    """Der Vertragsleser – die Stelle, an der ein Fehler still wäre."""

    def test_struktur_schluessel_halten_die_zuordnung(self):
        """`artikel:` ist ein Feld, kein Pillar: Die Slugs müssen bleiben."""
        self.assertIn("versicherungen", pw.vertrag_lesen())
        self.assertGreaterEqual(len(pw.vertrag_lesen()["versicherungen"]), 4)

    def test_echter_vertrag_ist_vollstaendig_gelesen(self):
        """Gegenprobe: Jeder Listenpunkt der Datei kommt auch an."""
        self.assertEqual(pw.vertrag_selbsttest(), [])

    def test_listenpunkt_ohne_pillar_ist_werkzeugfehler(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "vertrag.yaml"
            pfad.write_text("vertrag:\n  - 2026-01-01-ohne-pillar\n", encoding="utf-8")
            with self.assertRaises(pw.WerkzeugFehler):
                pw.vertrag_lesen(pfad)

    def test_fehlende_vertragsdatei_ist_werkzeugfehler(self):
        with self.assertRaises(pw.WerkzeugFehler):
            pw.vertrag_lesen(Path("/gibt/es/nicht.yaml"))


class BestandTests(unittest.TestCase):
    """Der echte Bestand – täglich geprüft, hier nur als eine Aussage.

    Dieser Test darf rot werden, wenn ein Pflicht-Artikel live geht und
    der Pillar ihn nicht verlinkt. Genau das ist seine Aufgabe: Er macht
    den Befund schon im Pull Request sichtbar, statt erst im Tageslauf.
    """

    def test_vertrag_ist_eingehalten(self):
        urteil, _seiten = pw.alle_pillars()
        meldungen = "\n".join(b.zeile() for b in urteil.befund)
        self.assertEqual(
            urteil.befund, [],
            "Die Pillar-Wiedervorlage ist fällig:\n" + meldungen)


class SelbsttestTests(unittest.TestCase):
    """Der eingebaute Selbsttest muss grün sein – sonst ist die Wache tot."""

    def test_selftest_gruen(self):
        self.assertEqual(pw.selftest(), 0)

    def test_werkzeugfehler_ist_eigene_klasse(self):
        self.assertTrue(issubclass(pw.WerkzeugFehler, RuntimeError))


if __name__ == "__main__":
    unittest.main()
