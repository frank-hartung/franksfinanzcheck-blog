"""Regressions-Tests: Einzigartigkeits-Score muss INHALT messen, nicht Schablonen.

Reparatur 09.09.2026 (Reserve #4): `quality_score._strip_boilerplate` erkannte
die von der KI eingesetzten Affiliate-/CTA-Bausteine nur in Einzelvarianten.
Unkenntnis der übrigen Varianten liess den 7-Gramm-Vergleich die reine
Baustein-Repetition als echte Text-Dopplung zählen -> Reserve-Entwürfe wurden
fälschlich auf uniqueness = 0.00 gestuft und blieben tagelang unter dem Gate.

Diese Datei beweist die zwei Verträge des Fixed Strips gegen einen
synthetischen Korpus (nie gegen den Live-Bestand):
  1) Artikel, die NUR CTA-/Disclosure-Schablonen (in allen Format-Varianten)
     teilen, gelten weiterhin als einzigartig (uniqueness 1.0).
  2) Artikel, die echten Inhalt teilen, werden weiterhin als Überlappung
     erkannt (uniqueness < 1.0) - der Strip schluckt KEINE echte Dopplung.

Ausführung wie Bestands-Tests:  python3 -m unittest discover -s scripts/tests -v
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

# Wie im bestehenden test_publication_reliability.py: das Skripte-Verzeichnis
# (parents[1] = scripts/) muss importierbar sein, wenn via
# `unittest discover -s scripts/tests` gestartet wird.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import quality_score as qs

# Kanonischer Affiliate-Disclosure-Baustein, wie ihn die KI (nahezu wortgleich)
# in viele Artikel setzt - in den Format-Varianten, die der ALTE Strip verpasste.
DISCL_LOWER = ("**Transparenz:** dieser Artikel enthält Affiliate-Links "
               "(Werbung). Beim Abschluss über einen Link erhalten wir eine "
               "Provision - für dich entstehen keine Mehrkosten.")
DISCL_ITALIC = ("*Dieser Artikel enthält Affiliate-Links (Werbung). Beim "
                "Abschluss über einen Link erhalten wir eine Provision - für "
                "dich entstehen keine Mehrkosten.*")
SPARTIPP = ("> 💶 **Spar-Tipp zwischendurch:** faire Konditionen gibt es online "
            "in Minuten: [**Vergleichen & sparen**](/go/allgemein/)")

# Je Artikel eindeutige Inhalts-Zeilen - teilen untereinander KEINEN echten
# 7-Gramm, damit jede Übereinstimmung zwingend vom Baustein kommt.
PEER_ALPHA = ("Kaltes Wasser zirkuliert durch alte Kupferrohre im Nordwesten "
              "und lagert feine Kalkreste an den Ventilkörpern der Wohnungen ab.")
PEER_BETA = ("Ein Wanderpfad windet sich am Morgen durch feuchte Kiefernwälder "
             "und endet an einer schmalen Holzbrücke über den schäumenden Bach.")
PEER_GAMMA = ("Die Künstlerin mischt warme Erdtöne auf rauer Leinwand und "
              "verschenkt die fertigen Bilder an eine kleine Galerie im Hafen.")

# Echter, geteilter Inhalts-Block (kein Baustein) fuer den Duplikat-Fall.
REAL_SHARED = ("Der Holzhacker schleift jeden Morgen die blanke Axtklinge "
               "über den nassen Schleifstein im kühlen Werkstattraum am "
               "Flussufer und prüft danach die Schneide gegen das Licht.")


def _post(posts_dir: Path, slug: str, body: str) -> Path:
    bundle = posts_dir / slug
    bundle.mkdir(parents=True, exist_ok=True)
    index = bundle / "index.md"
    index.write_text(
        "---\n"
        'title: "' + slug + '"\n'
        'description: "Einzigartiger Testartikel."\n'
        "date: 2026-09-09T06:00:00Z\n"
        "draft: true\n"
        "---\n\n"
        + body + "\n",
        encoding="utf-8",
    )
    return index


class UniquenessBoilerplateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.posts = Path(self.tmp.name) / "content" / "posts"
        self.posts.mkdir(parents=True)
        # Kandidat "alpha" plus zwei Peers, die NUR den Baustein teilen
        # (je in einer anderen Format-Variante).
        self.alpha = _post(self.posts, "alpha", PEER_ALPHA + "\n\n" + DISCL_LOWER)
        _post(self.posts, "beta", PEER_BETA + "\n\n" + DISCL_ITALIC + "\n\n" + SPARTIPP)
        _post(self.posts, "gamma", PEER_GAMMA + "\n\n" + DISCL_LOWER)

    def _uniqueness(self, index: Path) -> float:
        # Der Score globt gegen quality_score.BLOG_DIR - auf den Temp-Korpus
        # umstellen (und danach zurueck), um nie den Live-Bestand zu beruehren.
        old = qs.BLOG_DIR
        qs.BLOG_DIR = str(Path(self.tmp.name))
        try:
            return qs.score_article(str(index))["parts"]["uniqueness"]
        finally:
            qs.BLOG_DIR = old

    def test_boilerplate_only_sharing_counts_as_unique(self):
        # Vor der Reparatur: der kleingeschriebene "dieser Artikel"-Vorspann
        # wurde nicht gestrippt -> alpha "kollidierte" mit beta/gamma (0.0-0.8).
        self.assertEqual(self._uniqueness(self.alpha), 1.0)

    def test_genuine_duplicate_still_detected(self):
        # Zwei Artikel teilen echten Inhalt -> MUSS weiterhin als Ueberlappung
        # zaehlen (der Fix darf keine echte Dopplung schlucken).
        a = _post(self.posts, "delta", REAL_SHARED + "\n\nFüllertext eins.")
        _post(self.posts, "epsilon", REAL_SHARED + "\n\nFüllertext zwei.")
        self.assertLess(self._uniqueness(a), 1.0)


# Kanonischer Fazit-/FAQ-Baustein der Fazit-Schmiede (scripts/fazit_schmiede.py):
# deterministic, nahezu wortgleich in jedem automatisch veredelten Artikel.
FAZIT_SCHMIEDE_BOILERPLATE = (
    "## Fazit: Testthema\n"
    "Sich gezielt mit dem Thema **Testthema** zu beschäftigen, ist einer der "
    "einfachsten Hebel, um deine Finanzen selbst in die Hand zu nehmen und "
    "bares Geld zu sparen. Fang am besten heute an, vergleiche die Angebote "
    "und sichere dir deine Ersparnis! 💸🚀\n\n"
    "## Häufige Fragen\n"
    "### Wie starte ich am besten?\n"
    "Genau jetzt und ohne Aufwand – der Einstieg ist in wenigen Minuten erledigt.\n"
)


class FazitSchmiedeBoilerplateTests(unittest.TestCase):
    """Issue #251: geteilte Fazit-/FAQ-Schablonen sind KEINE Text-Dopplung."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.posts = Path(self.tmp.name) / "content" / "posts"
        self.posts.mkdir(parents=True)

    def _uniqueness(self, index: Path) -> float:
        old = qs.BLOG_DIR
        qs.BLOG_DIR = str(Path(self.tmp.name))
        try:
            return qs.score_article(str(index))["parts"]["uniqueness"]
        finally:
            qs.BLOG_DIR = old

    def test_shared_fazit_faq_boilerplate_counts_as_unique(self):
        # Zwei Artikel mit EINZIGARTIGEM Fließtext, aber identischem
        # Fazit-Schmiede-Baustein -> vor #251: uniqueness 0.0 (Massen-Parking).
        alpha = _post(self.posts, "alpha", PEER_ALPHA + "\n\n" + FAZIT_SCHMIEDE_BOILERPLATE)
        _post(self.posts, "beta", PEER_BETA + "\n\n" + FAZIT_SCHMIEDE_BOILERPLATE)
        self.assertEqual(self._uniqueness(alpha), 1.0)

    def test_real_duplicate_inside_body_still_detected(self):
        # Teilt der FLIESSTEXT echten Inhalt, wird weiterhin erkannt – der
        # Fazit-Strip darf keine echte Dopplung im Artikelkörper schlucken.
        a = _post(self.posts, "delta", REAL_SHARED + "\n\n" + FAZIT_SCHMIEDE_BOILERPLATE)
        _post(self.posts, "epsilon", REAL_SHARED + "\n\n" + FAZIT_SCHMIEDE_BOILERPLATE)
        self.assertLess(self._uniqueness(a), 1.0)


if __name__ == "__main__":
    unittest.main()
