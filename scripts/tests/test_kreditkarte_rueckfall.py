"""Schützt die korrigierten Aussagen im Kreditkarten-Entwurf nach #1207.

Das sind gezielte Rückfallproben, kein allgemeiner Faktencheck und keine
redaktionelle Freigabe. Die früheren vier Fachbefunde bleiben im Ledger.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import sys
import unittest
from decimal import Decimal
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import faktenfrische_befund_ledger as ledger  # noqa: E402
import ki_bild_markierung  # noqa: E402
import publish_gate  # noqa: E402

SLUG = "2026-11-11-kreditkarte-ohne-jahresgebuehr-die-besten-kostenlosen-karten"
POSTS = ROOT / "content" / "posts"
FINDING_IDS = {
    "228c9da3c42ee90e34bf", "7728690d5c2f7c141d8d",
    "cc0de46a82ad90851506", "d553d0d6c7706a69ad13",
}
QUELLEN = {
    "Q1": "https://www.verbraucherzentrale.de/wissen/reise-mobilitaet/urlaub-buchen/bargeld-karten-reiseschecks-das-richtige-zahlungsmittel-im-ausland-10715",
    "Q2": "https://www.verbraucherzentrale.de/wissen/geld-versicherungen/kredit-schulden-insolvenz/kreditkarte-oder-debitkarte-das-sind-die-unterschiede-65038",
    "Q3": "https://www.bafin.de/DE/Verbraucher/KrediteImmobilien/Kredite/EchteKreditkarten/EchteKreditkarten_node.html",
    "Q4": "https://www.verbraucherzentrale.de/wissen/geld-versicherungen/sparen-und-anlegen/bankgebuehren-nicht-alle-gebuehren-beim-girokonto-sind-zulaessig-5185",
}


def artikelpfad() -> Path:
    """Auch nach einem Datums-Lift eindeutig zur selben Seite auflösen."""
    exakt = POSTS / SLUG / "index.md"
    if exakt.is_file():
        return exakt
    kern = SLUG[11:]
    treffer = sorted(POSTS.glob(f"*-{kern}/index.md"))
    if len(treffer) != 1:
        raise FileNotFoundError(f"Kreditkarten-Artikel nicht eindeutig: {treffer}")
    return treffer[0]


def pruefe(fm: dict, body: str) -> list[str]:
    fehler = []
    text = re.sub(r"\s+", " ", body.casefold().replace("\u202f", " ")
                  .replace("\u00a0", " ").replace("‑", "-"))
    # Das aktuelle Beispiel darf später auch ganz entfallen. Solange Zahlen
    # daraus stehen, dürfen Annahmen, Rechenweg und Kostengrenze nicht fehlen.
    if any(wert in text for wert in ("1.200 €", "1 %", "12 €")):
        if "frei gewählte annahmen" not in text or "keine marktdaten" not in text:
            fehler.append("Gebührenbeispiel ohne Kennzeichnung als Annahme")
        if "1.200 € × 1 % = 12 €" not in text or "nicht eingerechnet" not in text:
            fehler.append("Gebührenbeispiel ohne Rechnung oder Kostengrenze")
    if not all(w in text for w in ("wechselkurs", "automatenbetreiber", "teilzahlung", "zinsen")):
        fehler.append("Wesentliche andere Kosten fehlen")
    frage = re.search(r"(?ms)^### Ist eine Karte ohne Jahresgebühr vollständig kostenlos\?\s*(.*?)(?=^### |^## |\Z)", body)
    if not frage or not re.search(r"nicht zwingend|nein", frage.group(1), re.I):
        fehler.append("FAQ behauptet pauschale Kostenfreiheit")
    if ("/go/allgemein/" in body or
            ("Karten vergleichen (Werbung)" in body and "/go/kreditkarte/" not in body)):
        fehler.append("Kartenvergleich verlinkt nicht das passende Werbeziel")
    quellen = {q.get("id"): q for q in fm.get("quellen", []) if isinstance(q, dict)}
    for ident, url in QUELLEN.items():
        if quellen.get(ident, {}).get("url") != url or not quellen.get(ident, {}).get("recherchiert_am"):
            fehler.append(f"Konkrete Quelle {ident} oder ihr Recherchezeitpunkt fehlt")
    rueckfaelle = (
        r"eine typische auslandseinsatzgebühr liegt bei 1\s*%",
        r"sparst im schnitt 5\s*minuten pro anbieter",
        r"einer monatsmiete von etwa 300\s*€ entspricht",
        r"ja, wenn die karte ausdrücklich .{0,100}keine auslandseinsatzgebühr",
        r"kostenlose karten haben meist keine mindesteinkommensvorgabe",
    )
    meta = " ".join(str(fm.get(feld) or "") for feld in
                    ("title", "description", "kurzantwort", "pin_title", "pin_description"))
    oberflaechen = text + " " + re.sub(r"\s+", " ", meta.casefold())
    if any(re.search(muster, oberflaechen) for muster in rueckfaelle):
        fehler.append("Alte unbelegte oder falsche Pauschalaussage zurückgekehrt")
    return fehler


def _ersetze_robust(text: str, alt: str, neu: str) -> str:
    """Ersetzt eine Zeichenkette unabhängig von der Typografie des Bestands.

    `fix_spaces` setzt vor `%` und `€` ein geschütztes Leerzeichen
    (U+00A0/U+202F). Ein Test, der `"= 12 €"` wörtlich ersetzt, sabotiert
    dann NICHTS – er bleibt grün, obwohl er rot sein müsste. Genau so stand es
    am 17.11.2026 im Bestand: Der Sabotage-Fall unten lief ins Leere.
    """
    teile = re.split(r"\s+", alt.strip())
    muster = r"[\s\u00a0\u202f]+".join(re.escape(t) for t in teile)
    neu_text, treffer = re.subn(muster, neu, text, count=1)
    if treffer != 1:
        raise AssertionError(f"Sabotage traf nicht (Typografie geändert?): {alt!r}")
    return neu_text


class KreditkarteRueckfallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, frontmatter, cls.body = artikelpfad().read_text(encoding="utf-8").split("---", 2)
        cls.fm = yaml.safe_load(frontmatter)

    def test_korrigierte_fassung_behaelt_sachliche_abgrenzungen(self):
        self.assertEqual(pruefe(self.fm, self.body), [])
        self.assertEqual(Decimal("1200") * Decimal("0.01"), Decimal("12"))
        if "/go/" in self.body:
            self.assertLess(self.body.index("Transparenz"), self.body.index("/go/"))

    def test_fruehere_befunde_bleiben_im_ledger_und_offene_in_der_akte(self):
        queue = json.loads((ROOT / "data/faktenfrische_queue.json").read_text(encoding="utf-8"))
        vorhanden = {e.get("id") for e in queue.get("fachbefunde", [])}
        self.assertTrue(FINDING_IDS <= vorhanden, "Historische Befunde wurden aus dem Ledger gelöscht")
        offen = {e["id"] for e in ledger.offene_befunde()}
        zustand = json.loads((ROOT / "data/faktenfrische_befunde_state.json").read_text(encoding="utf-8"))
        akte = {e["id"] for e in zustand["befunde"]}
        self.assertTrue((FINDING_IDS & offen) <= akte, "Offene Befunde fehlen in der Akte")
        # Solange alte Befunde offen sind, muss das echte Publish-Gate sie
        # blockieren. Eine spätere belegte F4-Entscheidung darf sie schließen;
        # der Regressionstest friert weder den Draft-Status noch F4 ewig ein.
        fehler, warnung, werkzeugfehler = publish_gate.fakten_befund_failures()
        self.assertFalse(werkzeugfehler, warnung)
        gate_text = "\n".join(meldung for meldungen in fehler.values() for meldung in meldungen)
        for ident in FINDING_IDS & offen:
            self.assertIn(ident, gate_text, "Offener Befund fehlt im Publish-Gate")

    def test_cover_attestation_bindet_an_die_markierte_datei(self):
        cover = self.fm["cover"]
        image = ROOT / "static" / cover["image"]
        self.assertEqual(cover["ki_pruefung"]["sha256"], hashlib.sha256(image.read_bytes()).hexdigest())
        self.assertEqual(ki_bild_markierung.lesen(image)["digital_source_type"],
                         cover["ki_pruefung"]["digital_source_type"])

    def test_sabotage_urspruengliche_fehler_und_quellenverlust_sind_rot(self):
        proben = (
            "Eine typische Auslandseinsatzgebühr liegt bei 1 % des Umsatzes.",
            "Du sparst im Schnitt 5 Minuten pro Anbieter.",
            "Das ist unzutreffend, was einer Monatsmiete von etwa 300 € entspricht.",
            "Kostenlose Karten haben meist keine Mindesteinkommensvorgabe.",
        )
        for text in proben:
            with self.subTest(text=text):
                self.assertTrue(pruefe(self.fm, self.body + "\n" + text))
        self.assertTrue(pruefe(self.fm, self.body.replace("frei gewählte Annahmen", "sichere Fakten")))
        alt = copy.deepcopy(self.fm)
        alt["quellen"] = [q for q in alt["quellen"] if q["id"] != "Q1"]
        self.assertTrue(pruefe(alt, self.body))
        alt = copy.deepcopy(self.fm)
        alt["pin_description"] = "Kostenlose Karten haben meist keine Mindesteinkommensvorgabe."
        self.assertTrue(pruefe(alt, self.body))
        # Typografie-robust: der Bestand trägt NBSP vor `€` (fix_spaces).
        self.assertTrue(pruefe(self.fm, _ersetze_robust(
            self.body, "= 12 €", "= 120 €")))
        alt_body = self.body.replace("Nicht zwingend.", "Ja, immer.", 1)
        self.assertNotEqual(alt_body, self.body)
        self.assertTrue(pruefe(self.fm, alt_body))
        self.assertTrue(pruefe(self.fm, self.body.replace("/go/kreditkarte/", "/go/allgemein/")))


if __name__ == "__main__":
    unittest.main()
