"""Wiedervorlage: Der Versicherungs-Pillar muss seine Artikel verlinken, sobald sie live sind.

WARUM DIESER TEST (27.10.2026)
------------------------------
Am 27.10.2026 wurden die vier toten Linkziele im Versicherungs-Cluster
bereinigt: Privathaftpflicht, Wohngebäude-Vergleich, Haus-Vorsorge und
Kfz-Vergleich waren `draft: true`, ihre Verlinkungen liefen ins Leere
(Befund W11, 14 Quellen). Die Links wurden entlinkt bzw. auf den Pillar
umgehängt – richtig, solange die Ziele Entwürfe sind.

Zurückholen darf man sie erst, wenn die Artikel ausgeliefert werden, sonst
stehen sofort wieder vier tote Linkziele im Abdeckungsbefund. Genau dieser
Zeitpunkt ist die Lücke: Niemand merkt, dass die Artikel live gegangen sind –
der Befund bleibt grün, der Pillar verlinkt weiter nichts.

Dieser Test ist die Wiedervorlage. Er ist heute grün (alle vier sind Entwurf)
und wird rot, sobald einer der vier live ist und im Pillar fehlt. Er prüft
beide Richtungen:

  * live  → muss im Pillar verlinkt sein (sonst Aufgabe aus
            GSC-OPTIMIERUNGSPLAN-2026-10-27.md, Abschnitt 14.4)
  * Entwurf → darf NICHT im Pillar verlinkt sein (sonst W11 wieder da)

Die Logik steckt in `fehlende_verlinkungen()` / `verlinkte_entwuerfe()`, damit
die Wache selbst prüfbar ist (`FehlendeVerlinkungTest`) und nicht nur auf dem
heutigen Zufallszustand grün steht.
"""
from __future__ import annotations

import os
import re
import unittest

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PILLAR = os.path.join(BLOG_DIR, "content", "pillar", "versicherungen", "index.md")
POSTS = os.path.join(BLOG_DIR, "content", "posts")

# Die vier Artikel aus GSC-OPTIMIERUNGSPLAN-2026-10-27.md, Abschnitt 14.2.
CLUSTER = {
    "2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026": "Haus-Vorsorge 2026",
    "2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet": "Privathaftpflicht",
    "2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst": "Wohngebäude-Vergleich",
    "2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen": "Kfz-Vergleich",
}

POST_LINK = re.compile(r"\]\(\.\./\.\./posts/([^)/]+)/?\)")


def ist_entwurf(index_md: str) -> bool:
    """`draft: true` im Frontmatter? Dieselbe Lesart wie Hugo (nur die Zeile)."""
    with open(index_md, encoding="utf-8") as fh:
        text = fh.read()
    kopf = text.split("---")[1] if text.startswith("---") else ""
    return bool(re.search(r"(?m)^draft:\s*true\s*$", kopf))


def pillar_ziele(pillar_text: str) -> set[str]:
    """Alle Post-Slugs, auf die der Pillar verlinkt (ohne Anker/End-Schrägstrich)."""
    return {m.group(1) for m in POST_LINK.finditer(pillar_text)}


def fehlende_verlinkungen(pillar_text: str,
                          live: set[str],
                          kandidaten: dict[str, str]) -> list[str]:
    """Live-Artikel aus `kandidaten`, die im Pillar NICHT verlinkt sind."""
    ziele = pillar_ziele(pillar_text)
    return [f"{name} ({slug})" for slug, name in sorted(kandidaten.items())
            if slug in live and slug not in ziele]


def verlinkte_entwuerfe(pillar_text: str,
                        entwuerfe: set[str],
                        kandidaten: dict[str, str]) -> list[str]:
    """Artikel aus `kandidaten`, die noch Entwurf sind, aber im Pillar verlinkt werden."""
    ziele = pillar_ziele(pillar_text)
    return [f"{name} ({slug})" for slug, name in sorted(kandidaten.items())
            if slug in entwuerfe and slug in ziele]


class FehlendeVerlinkungTest(unittest.TestCase):
    """Die Wache muss anschlagen, wenn sie soll – sonst ist sie kein Beweis."""

    def test_live_aber_nicht_verlinkt_wird_gemeldet(self):
        live = {"a-live", "b-live"}
        pillar = "Text mit [A](../../posts/a-live/) und sonst nichts."
        self.assertEqual(
            fehlende_verlinkungen(pillar, live, {"a-live": "A", "b-live": "B"}),
            ["B (b-live)"])

    def test_verlinkter_entwurf_wird_gemeldet(self):
        pillar = "[B](../../posts/b-draft/)"
        self.assertEqual(
            verlinkte_entwuerfe(pillar, {"b-draft"}, {"b-draft": "B"}),
            ["B (b-draft)"])

    def test_entwurf_ohne_link_ist_kein_befund(self):
        """Ein Entwurf ist nicht live – fehlender Pillar-Link ist dort korrekt."""
        self.assertEqual(fehlende_verlinkungen("ohne Links", set(), {"x": "X"}), [])

    def test_absoluter_link_zaehlt_nicht_als_pillar_link(self):
        """Der Pillar-Link muss relativ sein; `/go/`-Gateways sind keine Artikel."""
        pillar = "[A](/posts/a-live/) und [B](/go/haftpflicht/)"
        self.assertEqual(pillar_ziele(pillar), set())


class BestandTest(unittest.TestCase):
    """Der echte Bestand: heute grün, ab der Promotion eine Aufgabe."""

    @classmethod
    def setUpClass(cls):
        with open(PILLAR, encoding="utf-8") as fh:
            cls.pillar_text = fh.read()
        cls.entwuerfe, cls.live = set(), set()
        for slug in CLUSTER:
            pfad = os.path.join(POSTS, slug, "index.md")
            if not os.path.exists(pfad):
                continue
            (cls.entwuerfe if ist_entwurf(pfad) else cls.live).add(slug)

    def test_jeder_live_artikel_ist_im_pillar_verlinkt(self):
        offen = fehlende_verlinkungen(self.pillar_text, self.live, CLUSTER)
        self.assertEqual(
            offen, [],
            "Diese Artikel sind live, der Versicherungs-Pillar verlinkt sie aber "
            "nicht mehr. Die Links wurden am 27.10.2026 entlinkt, weil die Ziele "
            "Entwürfe waren – jetzt gehören sie zurück (Abschnitt 14.4 in "
            f"GSC-OPTIMIERUNGSPLAN-2026-10-27.md): {offen}")

    def test_pillar_verlinkt_keinen_entwurf(self):
        offen = verlinkte_entwuerfe(self.pillar_text, self.entwuerfe, CLUSTER)
        self.assertEqual(
            offen, [],
            "Der Pillar verlinkt einen Entwurf – das erzeugt sofort wieder ein "
            f"totes Linkziel (Befund W11): {offen}")


if __name__ == "__main__":
    unittest.main()
