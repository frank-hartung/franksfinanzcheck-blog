"""Rückfallschutz für die fachliche Kurzantwort und Quellen aus PR #1206.

Der Cover-Herkunfts-Merge #1207 setzte diese Fassung zurück. Der Test prüft
wichtige Aussagen und ihre konkreten Quellen, nicht die Wahrheit des gesamten
Artikels oder eine redaktionelle Freigabe.
"""
from __future__ import annotations

import copy
import hashlib
import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ARTICLE = (ROOT / "content/posts/2026-10-28-oekostrom-anbieter-wechseln-"
           "sicher-gruen-und-bezahlbar/index.md")
QUELLEN = {
    "Q1": "https://www.bundesnetzagentur.de/DE/Vportal/Energie/KuendigungLieferantenwechsel/Lieferantenwechsel/start.html",
    "Q2": "https://www.verbraucherzentrale.de/wissen/energie/preise-tarife-anbieterwechsel/ist-ein-tarif-mit-oekostrom-und-oekogas-ueberhaupt-sinnvoll-8207",
    "Q3": "https://www.bundesnetzagentur.de/DE/Vportal/Energie/Vertragsarten/Ersatzversorgung/start.html",
}


def pruefe(fm: dict, body: str) -> list[str]:
    """Meldet konkrete Verluste; bleibt auch bei fehlenden Feldern fail-closed."""
    fehler = []
    kurz = str(fm.get("kurzantwort") or "").casefold()
    if not ("technisch" in kurz and "24 stunden" in kurz
            and "kündigungsfrist" in kurz and "nicht" in kurz):
        fehler.append("Kurzantwort trennt technischen Wechsel und Vertragsfrist nicht")
    quellen = {q.get("id"): q.get("url") for q in fm.get("quellen", [])
               if isinstance(q, dict)}
    for ident, url in QUELLEN.items():
        if quellen.get(ident) != url:
            fehler.append(f"Quelle {ident} fehlt oder ist nicht spezifisch")
    frage = re.search(r"(?ms)^### Wie lange dauert ein Wechsel[^\n]*\n(.*?)(?=^### |^## |\Z)", body)
    antwort = frage.group(1).casefold() if frage else ""
    if not ("24 stunden" in antwort and "technisch" in antwort
            and "kündigungsfrist" in antwort and "nicht" in antwort):
        fehler.append("Wechsel-FAQ trennt technische und vertragliche Frist nicht")
    verbotene_rueckfaelle = (
        r"technisch\s+(?:nur\s+)?wenige\s+minuten",
        r"technische\s+umstellung\s+erfolgt\s+meist\s+zum\s+ersten",
        r"(?:strengsten\s+zertifikate|niemals\s+im\s+dunkeln)",
        r"je\s+mehr\s+menschen\s+dies\s+tun,?\s+desto\s+sauberer",
    )
    oberflaechen = kurz + "\n" + body.casefold()
    if any(re.search(muster, oberflaechen) for muster in verbotene_rueckfaelle):
        fehler.append("Zurückgesetzte pauschale Aussage wieder vorhanden")
    return fehler


class OekostromRueckfallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, frontmatter, cls.body = ARTICLE.read_text(encoding="utf-8").split("---", 2)
        cls.fm = yaml.safe_load(frontmatter)

    def test_korrigierte_fassung_und_quellen_bleiben_erhalten(self):
        self.assertIs(self.fm.get("draft"), False)
        self.assertEqual(pruefe(self.fm, self.body), [])

    def test_bildherkunft_bleibt_an_original_gebunden(self):
        cover = self.fm["cover"]
        image = ROOT / "static" / cover["image"]
        self.assertEqual(cover["ki_pruefung"]["digital_source_type"], "algorithmicMedia")
        self.assertEqual(cover["ki_pruefung"]["sha256"], hashlib.sha256(image.read_bytes()).hexdigest())

    def test_sabotage_alte_kurzantwort_und_quellenverlust_sind_rot(self):
        alt = copy.deepcopy(self.fm)
        alt["kurzantwort"] = "Der Wechsel dauert technisch nur wenige Minuten."
        self.assertTrue(pruefe(alt, self.body))
        alt = copy.deepcopy(self.fm)
        alt["quellen"] = [q for q in alt["quellen"] if q.get("id") != "Q2"]
        self.assertTrue(pruefe(alt, self.body))

    def test_sabotage_alte_wechsel_faq_ist_rot(self):
        body = re.sub(
            r"(?ms)(^### Wie lange dauert ein Wechsel[^\n]*\n).*?(?=^### |^## |\Z)",
            r"\1Die technische Umstellung erfolgt meist zum Ersten eines Monats.\n\n",
            self.body,
        )
        self.assertNotEqual(body, self.body)
        self.assertTrue(pruefe(self.fm, body))


if __name__ == "__main__":
    unittest.main()
