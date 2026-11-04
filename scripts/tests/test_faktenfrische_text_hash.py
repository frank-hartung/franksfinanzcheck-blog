#!/usr/bin/env python3
# ============================================================
#  LEDGER-TEXT-HASH (#1047-Ursache, 04.11.2026): `text_hash`
#  muss einen echten SHA-256 liefern.
#  ------------------------------------------------------------
#  Befund: In `faktenfrische_befund_ledger.text_hash` fehlte
#  die Rückgabe – die Funktion endete nach dem Material-Dict
#  und lieferte `None`. Folge: Jede per `--entscheiden`
#  geschriebene Entscheidung band an `geprueft_fassung: ''`,
#  die Datei war danach ungültig, und KEIN F4-Befund ließ
#  sich überhaupt per menschlicher Entscheidung schließen
#  (jeder Folgeaufruf starb an der Validierung der kaputten
#  Datei). Diese Tests pinnen den Vertrag der Funktion:
#  echter Hash, quellen-stabil, text-sensitiv, und der
#  komplette Entscheidungs-Rundlauf schließt einen Befund.
# ============================================================
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import faktenfrische_befund_ledger as ledger  # noqa: E402

FM = 'title: "T"\ndescription: "D"\nkurzantwort: "K"\n'


def _artikel(body="Text.", quellen=None, titel=None):
    fm = FM.replace('"T"', f'"{titel}"') if titel else FM
    if quellen is not None:
        fm += "quellen:\n" + "".join(f"  - {q}\n" for q in quellen)
    return {"fm": fm, "body": body}


class TextHashVertragTest(unittest.TestCase):
    def test_echter_sha256(self):
        h = ledger.text_hash(_artikel())
        self.assertIsInstance(h, str)
        self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", h), h)

    def test_quellen_aendern_den_hash_nicht(self):
        a = ledger.text_hash(_artikel(quellen=["https://a.example"]))
        b = ledger.text_hash(_artikel(quellen=["https://b.example", "x"]))
        self.assertEqual(a, b)

    def test_text_aenderung_aendert_den_hash(self):
        self.assertNotEqual(ledger.text_hash(_artikel(body="A")),
                            ledger.text_hash(_artikel(body="B")))
        self.assertNotEqual(ledger.text_hash(_artikel(titel="X")),
                            ledger.text_hash(_artikel(titel="Y")))


class EntscheidungsRundlaufTest(unittest.TestCase):
    def test_entscheidung_schliesst_befund(self):
        slug = "2099-01-01-rundlauf"
        artikel = _artikel(body="Geheilter Text.")
        fassungen = {slug: {"text": ledger.text_hash(artikel),
                            "pruef": ledger.pruef_hash(artikel)}}
        befund = {"typ": "luecke", "text": "Zahl ohne Quelle genannt."}
        bid = ledger.befund_id(slug, befund)
        queue = {"fachbefunde": [{
            "id": bid, "slug": slug,
            "fassung_sha256": fassungen[slug]["pruef"],
            "typ": befund["typ"], "text": befund["text"],
        }], "laeufe": []}
        with tempfile.TemporaryDirectory() as td:
            qp = Path(td) / "queue.json"
            dp = Path(td) / "entscheidungen.yaml"
            qp.write_text(json.dumps(queue), encoding="utf-8")
            entscheidung = ledger.entscheidung_anfuegen(
                bid, "Testperson",
                "Text geprüft und geheilt; Zahl mit Quelle belegt.",
                queue_path=qp, decisions_path=dp, fassungen=fassungen)
            self.assertEqual(entscheidung["geprueft_fassung"],
                             fassungen[slug]["text"])
            offen = ledger.offene_befunde(qp, dp, fassungen)
            self.assertEqual([], [e for e in offen if e["id"] == bid])


if __name__ == "__main__":
    unittest.main()
