#!/usr/bin/env python3
"""Rückfallschutz: Die Schreiber der KI-Redaktion sind an die Snippet-SSOT gebunden.

Warum diese Datei existiert (Dauerheilung 04.11.2026, #1064):
Am 04.11.2026 um 12:38 UTC schrieb die Engine den Entwurf
„Günstigen Mietwagen für den Urlaub buchen“. Seine Description war
157 Zeichen lang und 1007 px breit – die Metadaten-Wache (M2/M7) war im
nächtlichen E2E-Lauf zu Recht rot, der Deploy-Heiler musste um 12:56 UTC
nachbessern. Die Ursache war NICHT die Wache, sondern ein Schreiber mit
eigenem Maß: `ki_shared.clip_text` kürzte auf 158 Zeichen, ohne Breiten-
kenntnis. Das ist exakt die Klasse, die WF-7B6B/#925 am 29.10.2026 für
keyword_optimizer/meta_optimizer geschlossen hatte – der Helfer der
Rollen-Writer (claude_writer, news_writer, poppy_repurpose, endredaktion)
war nie gebunden.

Diese Tests halten den Sollstand fest:
  · der Vorfall vom 04.11.2026 kann nicht wieder passieren (Vorlage + Titel),
  · `clip_text` reicht an `serp_limits.auf_snippet_kuerzen` durch (D18),
  · `build_frontmatter` stellt die Description an der letzten Writer-Grenze
    noch einmal ins Fenster (Defense in Depth, wie die Tags gegen das Register),
  · alle vier Writer-Vorlagen halten auch mit langem Titel das Fenster,
  · die Bindung steht im Quelltext (kein Aufrufer führt ein eigenes Maß),
  · Jasper (Messstelle + KI-Vorschlag) liest dieselben Grenzen.

Läuft ohne Netz, ohne Modell, ohne Bestand:
`python3 -m unittest scripts.tests.test_snippet_schreiber`
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import ki_shared as ks  # noqa: E402
import serp_limits as sl  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"

# Material des Vorfalls vom 04.11.2026 (#1064): genau so hat claude_writer
# die Description gebaut, die M2/M7 rot machte.
VORFALL_1064_TITEL = "Günstigen Mietwagen für den Urlaub buchen"
VORFALL_1064_DESCRIPTION = (
    "Günstigen Mietwagen für den Urlaub buchen – der große Ratgeber von "
    "FranksFinanzcheck: Schritt für Schritt erklärt, mit Rechenbeispielen, "
    "Checklisten und FAQ."
)

# Die Vorlagen der vier Writer (Spiegel des Quelltexts; die Bindung selbst
# prüft Klasse `SchreiberBindung` strukturell, damit eine neue Vorlage nicht
# unbemerkt am Fenster vorbeischreibt).
VORLAGE_CLAUDE = (
    "{title} – der große Ratgeber von FranksFinanzcheck: Schritt für "
    "Schritt erklärt, mit Rechenbeispielen, Checklisten und FAQ."
)
VORLAGE_NEWS = (
    "{title} – aktuelle Einordnung von FranksFinanzcheck: was "
    "passiert ist, was es für dich bedeutet und was du jetzt tun kannst."
)
VORLAGE_POPPY_ENDREDAKTION = (
    "{title} – so gehst du Schritt für Schritt vor, mit Rechenbeispiel "
    "und FAQ. Ehrlich, Zahlen statt Werbeversprechen."
)

# Ein Titel, der allein schon fast das halbe Fenster füllt – der Härtetest
# für jede Vorlage (die Engine kürzt Titel nicht vor dem Description-Bau).
LANGER_TITEL = (
    "Wärmepumpe versus Gasheizung im Altbau: Kosten, Förderung und "
    "Wirtschaftlichkeit im Vergleich"
)


class Vorfall1064(unittest.TestCase):
    """Der gemessene Vorfall – nicht nachgestellt, sondern im Original."""

    def test_vorfall_description_war_ausserhalb_des_fensters(self):
        # Der Befund war echt: 157 Zeichen, 1007 px. Wer diese Zeile
        # ändert, ändert die Geschichte, nicht den Test.
        codes = [code for code, _ in sl.befunde(VORFALL_1064_DESCRIPTION)]
        self.assertEqual(codes, ["zu-lang", "zu-breit"])

    def test_vorfall_description_wird_ins_fenster_gekuerzt(self):
        geheilt = ks.clip_text(VORFALL_1064_DESCRIPTION)
        self.assertTrue(sl.passt(geheilt), sl.befunde(geheilt))
        self.assertNotEqual(geheilt, VORFALL_1064_DESCRIPTION)

    def test_vorfall_titel_mit_claude_vorlage_bleibt_im_fenster(self):
        roh = VORLAGE_CLAUDE.format(title=VORFALL_1064_TITEL)
        self.assertEqual(roh, VORFALL_1064_DESCRIPTION)
        self.assertTrue(sl.passt(ks.clip_text(roh)))

    def test_altes_158er_mass_wuerde_den_vorfall_durchlassen(self):
        # Regressionssperre gegen die alte Zahl: 157 <= 158 – der frühere
        # clip_text hätte den Text UNVERÄNDERT gelassen. Seit der Bindung
        # muss er schneiden.
        self.assertLessEqual(len(VORFALL_1064_DESCRIPTION), 158)
        self.assertNotEqual(ks.clip_text(VORFALL_1064_DESCRIPTION),
                            VORFALL_1064_DESCRIPTION)


class ClipTextBindung(unittest.TestCase):
    """`clip_text` ist Durchreicher zur SSOT – kein zweites Maß."""

    def test_breite_wird_mitgeprueft(self):
        # Die #925-Klasse: Zeichenzahl passt, Breite nicht. Der Schnitt
        # muss BEIDE Grenzen prüfen (153 Zeichen, > 985 px).
        breit = ("Wohngebäude und Wärmewende: Warum Wärmeverlust, Wärmepumpe "
                 "und Wartung zusammengehören. Wer Wohnraum warm hält, spart "
                 "mit Wärmedämmung.")
        self.assertLessEqual(len(breit), sl.DESC_MAX_ZEICHEN)
        self.assertGreater(sl.breite_px(breit), sl.DESC_MAX_PX)
        geheilt = ks.clip_text(breit)
        self.assertTrue(sl.passt(geheilt), sl.befunde(geheilt))

    def test_schnitt_an_wortgrenze_mit_ehrlichem_ellipsis(self):
        geheilt = ks.clip_text(VORFALL_1064_DESCRIPTION)
        self.assertTrue(geheilt.endswith("…"))
        # Kein Schnitt mitten im Wort: das Zeichen vor dem Ellipsis ist
        # ein Wortende (die SSOT räumt Satzzeichen davor ab).
        self.assertNotIn("  ", geheilt)

    def test_passender_text_bleibt_unveraendert(self):
        gut = ("Gastarife vergleichen: So findest du einen fairen Tarif mit "
               "Preisgarantie und wechselst ohne Risiko.")
        self.assertTrue(sl.passt(gut))
        self.assertEqual(ks.clip_text(gut), gut)

    def test_kurzer_text_bleibt_unveraendert(self):
        # Unter 100 Zeichen ist „zu kurz“ ein Befund der Wache, aber
        # Kürzen macht ihn nicht besser – die SSOT gibt ihn unverändert
        # zurück (min_zeichen=0 im frühen Ausstieg).
        self.assertEqual(ks.clip_text("Kurzer Text."), "Kurzer Text.")
        self.assertEqual(ks.clip_text(""), "")

    def test_unmessbare_zeichen_bleiben_ehrlich(self):
        # Emoji hat keine Breitenmetrik: die SSOT kann nicht ehrlich
        # kürzen und gibt None. Der Schreiber erfindet dann keine Grenze,
        # sondern lässt den Text stehen – die Wache meldet „unmessbar“.
        text = "Strom sparen 💡 " + ("mit diesen einfachen Tipps " * 8)
        self.assertIsNone(sl.auf_snippet_kuerzen(text))
        self.assertEqual(ks.clip_text(text), text.strip())
        self.assertIn("unmessbar", [c for c, _ in sl.befunde(text)])

    def test_explizites_max_len_bleibt_wortgrenzen_schnitt(self):
        # Der explizite Weg ist für Text AUSSERHALB des Snippets gedacht
        # (z. B. Pin-Zeilen): Wortgrenze, ehrliches „ …“, kein Breitenanspruch.
        text = "eins zwei drei vier fünf sechs sieben acht"
        self.assertEqual(ks.clip_text(text, max_len=20), "eins zwei drei vier …")
        self.assertEqual(ks.clip_text("kurz", max_len=20), "kurz")

    def test_signatur_fuehrt_kein_eigenes_zahlenlimit(self):
        # Die 158 stand als DEFAULT in der Signatur – genau dort darf nie
        # wieder eine Zahl stehen. Geprüft wird der Quelltext, nicht das
        # Verhalten (ein künftiger Aufrufer könnte sie sonst übersehen).
        quelle = (SCRIPTS / "ki_shared.py").read_text(encoding="utf-8")
        zeilen = [z for z in quelle.splitlines() if z.startswith("def clip_text(")]
        self.assertEqual(len(zeilen), 1)
        self.assertIn("max_len: int | None = None", zeilen[0])


class WriterGrenze(unittest.TestCase):
    """`build_frontmatter` stellt die Description an der letzten Grenze ins Fenster."""

    def _fm_description(self, fm: str) -> str:
        for zeile in fm.splitlines():
            if zeile.startswith("description:"):
                # yaml_str schreibt doppelt quoted; Inhalt zwischen den Quotes.
                return zeile.split(":", 1)[1].strip().strip('"')
        self.fail("description-Zeile fehlt im Frontmatter")

    def test_rohe_description_wird_normalisiert(self):
        fm = ks.build_frontmatter(
            title="Stromfresser im Haushalt entlarven",
            description=VORFALL_1064_DESCRIPTION,
            tags=["Stromkosten senken"],
            keywords=["Strom sparen im Haushalt"],
            rolle="claude")
        desc = self._fm_description(fm)
        self.assertTrue(sl.passt(desc), sl.befunde(desc))

    def test_kurze_description_bleibt_erhalten(self):
        # Bestandsverhalten (Selbsttests der Fachfreigabe nutzen "Test"):
        # kurze Texte werden nicht weggeheilt.
        fm = ks.build_frontmatter(
            title="Stromfresser im Haushalt entlarven",
            description="Test",
            tags=["Stromkosten senken"],
            keywords=["Strom sparen im Haushalt"],
            rolle="claude")
        self.assertEqual(self._fm_description(fm), "Test")

    def test_alle_writer_vorlagen_mit_langem_titel_im_fenster(self):
        for name, vorlage in (
                ("claude_writer", VORLAGE_CLAUDE),
                ("news_writer", VORLAGE_NEWS),
                ("poppy_repurpose", VORLAGE_POPPY_ENDREDAKTION),
                ("endredaktion (E11)", VORLAGE_POPPY_ENDREDAKTION)):
            with self.subTest(writer=name):
                roh = vorlage.format(title=LANGER_TITEL)
                self.assertGreater(len(roh), sl.DESC_MAX_ZEICHEN)
                geheilt = ks.clip_text(roh)
                self.assertTrue(sl.passt(geheilt), sl.befunde(geheilt))


class SchreiberBindung(unittest.TestCase):
    """Die Bindung steht im Quelltext – strukturell, zeilenweise, ohne Ratespiel."""

    def test_clip_text_delegiert_an_die_ssot(self):
        quelle = (SCRIPTS / "ki_shared.py").read_text(encoding="utf-8")
        self.assertIn("import serp_limits", quelle)
        # Der Standardpfad ruft die EINE Kürzungsstelle auf.
        self.assertIn("serp_limits.auf_snippet_kuerzen(text)", quelle)

    def test_writer_rufen_clip_text_ohne_eigenes_mass(self):
        # Jeder Description-Schreiber geht durch ks.clip_text – und keiner
        # übergibt dort ein eigenes max_len (das wäre die zweite Grenze).
        erwartet = {
            "claude_writer.py": "description = ks.clip_text(",
            "news_writer.py": "description = ks.clip_text(",
            "poppy_repurpose.py": "description = ks.clip_text(",
            "endredaktion.py": "neu = ks.clip_text(",
        }
        for datei, marker in erwartet.items():
            with self.subTest(datei=datei):
                zeilen = (SCRIPTS / datei).read_text(encoding="utf-8").splitlines()
                treffer = [i for i, z in enumerate(zeilen) if marker in z]
                self.assertTrue(treffer, f"{marker} fehlt in {datei}")
                # Der Aufruf und seine zwei Folgezeilen dürfen kein
                # eigenes max_len führen.
                for i in treffer:
                    block = "\n".join(zeilen[i:i + 3])
                    self.assertNotIn("max_len", block,
                                     f"{datei}: eigenes Maß am clip_text-Aufruf")

    def test_build_frontmatter_normalisiert_description(self):
        quelle = (SCRIPTS / "ki_shared.py").read_text(encoding="utf-8")
        self.assertIn("description = clip_text(description)", quelle)

    def test_jasper_misst_mit_der_ssot(self):
        import jasper_seo  # noqa: E402  (Messstelle, kein Schreibzugriff beim Import)
        self.assertEqual(jasper_seo.META_MAX, sl.DESC_MAX_ZEICHEN)
        self.assertEqual(jasper_seo.META_MIN, sl.DESC_OPT_MIN_ZEICHEN)
        quelle = (SCRIPTS / "jasper_seo.py").read_text(encoding="utf-8")
        # Keine zweite Obergrenze als Literal im Score oder im KI-Prompt.
        self.assertNotIn("120–160", quelle)
        self.assertNotIn("META_MIN, META_MAX = 120, 160", quelle)

    def test_meta_report_lehrt_das_richtige_fenster(self):
        quelle = (SCRIPTS / "meta_report.py").read_text(encoding="utf-8")
        self.assertNotIn("optimal 120–160", quelle)
        self.assertIn("mo.DESC_OPT_MIN", quelle)


# Uhrfestigkeit: Alle Fixtures sind festgenagelt (keine Wanduhr-Arithmetik).
# Die ganze Suite läuft in CI zusätzlich unter der um 97 Tage vorgestellten
# Uhr (scripts/selftest_clock.py --trap-discover) – das ist der Zeitbomben-
# Schutz, nicht eine selbstreferenzielle Quelltext-Prüfung.


if __name__ == "__main__":
    unittest.main(verbosity=2)
