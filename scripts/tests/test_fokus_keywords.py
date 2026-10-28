"""Hermetische Tests der Fokus-Keyword-Prüfung (scripts/fokus_keywords.py).

Die Fälle sind aus dem Redaktionsalltag abgeleitet: ein Begriff, der im
Titel steht und im Text fehlt; zwei Artikel, die um dieselbe Suchanfrage
konkurrieren; eine Dichte, die nach Stuffing klingt. Jede Regel hat eine
Sabotage-Probe und eine Gegenprobe.
"""
import unittest

import scripts.fokus_keywords as fk

FUELL = " ".join(["Wort"] * 100)


def dokument(*, titel="Strom sparen: Ratgeber für den Alltag",
             beschreibung="Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen "
                          "und Abschläge planen – mit Rechenbeispielen.",
             fokus='["Strom sparen", "Stromfresser finden"]',
             body=None, zusatz=""):
    body = body if body is not None else (
        f"Strom sparen beginnt mit dem Blick auf den Zähler. {FUELL}\n\n"
        f"## Strom sparen: wo die Kosten entstehen\n\n"
        f"Wer Stromfresser finden will, spart sofort. {FUELL}\n")
    fokus_zeile = f"keywords_fokus: {fokus}\n" if fokus is not None else ""
    return (f'---\ntitle: "{titel}"\ndescription: "{beschreibung}"\n'
            f'date: 2026-09-01\ndraft: false\n{fokus_zeile}{zusatz}---\n\n{body}')


def regeln(text, datei="content/posts/x/index.md"):
    befunde, stand = fk.pruefe_dokument(datei, text)
    return sorted({b.regel for b in befunde}), stand


class FokusKeywordTests(unittest.TestCase):
    def test_sauberer_artikel_ohne_befund(self):
        got, stand = regeln(dokument())
        self.assertEqual(got, [])
        self.assertEqual(stand.fokus[0], "Strom sparen")

    def test_fehlendes_feld_ist_empfehlung_nicht_gate(self):
        befunde, _ = fk.pruefe_dokument("x.md", dokument(fokus=None))
        self.assertEqual([(b.regel, b.schwere) for b in befunde], [("F9", "P3")])

    def test_primaer_keyword_muss_im_titel_stehen(self):
        got, _ = regeln(dokument(titel="Energie im Alltag",
                                 body=dokument().split("---\n\n", 1)[1].replace(
                                     "## Strom sparen:", "## Energie:")))
        self.assertIn("F2", got)

    def test_primaer_keyword_muss_im_ersten_absatz_stehen(self):
        got, _ = regeln(dokument(body=f"Der Zähler lohnt einen Blick. {FUELL}\n\n"
                                      f"## Strom sparen: Kosten\n\nStromfresser finden. {FUELL}\n"))
        self.assertIn("F3", got)

    def test_primaer_keyword_muss_in_einer_h2_stehen(self):
        got, _ = regeln(dokument(body=f"Strom sparen beginnt beim Zähler. {FUELL}\n\n"
                                      f"## Wo die Kosten entstehen\n\nStromfresser finden. {FUELL}\n"))
        self.assertIn("F4", got)

    def test_primaer_keyword_muss_in_der_description_stehen(self):
        got, _ = regeln(dokument(beschreibung="Energie im Alltag: Stromfresser finden, "
                                               "Tarife vergleichen und Abschläge planen."))
        self.assertIn("F5", got)

    def test_sekundaer_keyword_ohne_text_ist_ein_befund(self):
        got, _ = regeln(dokument(body=f"Strom sparen beginnt beim Zähler. {FUELL}\n\n"
                                      f"## Strom sparen: Kosten\n\nWer Verbraucher prüft, spart. {FUELL}\n"))
        self.assertIn("F6", got)

    def test_stuffing_wird_erkannt(self):
        got, _ = regeln(dokument(body=f"Strom sparen beginnt. {' '.join(['Strom sparen'] * 30)} {FUELL}\n\n"
                                      f"## Strom sparen: Kosten\n\nStromfresser finden.\n"))
        self.assertIn("F7", got)

    def test_strukturfehler_werden_erkannt(self):
        got, _ = regeln(dokument(fokus='["strom sparen", "strom sparen", "a", "b", "c", "d"]'))
        self.assertIn("F1", got)

    def test_doppelte_eintraege_zaehlen_als_strukturfehler(self):
        befunde, _ = fk.pruefe_dokument("x.md", dokument(fokus='["Strom sparen", "strom sparen"]'))
        self.assertTrue(any("doppelt" in b.text for b in befunde if b.regel == "F1"))

    def test_kannibalisierung_meldet_beide_seiten(self):
        _, a = fk.pruefe_dokument("a.md", dokument())
        _, b = fk.pruefe_dokument("b.md", dokument())
        befunde = fk.kannibalisierung([a, b])
        self.assertEqual({x.datei for x in befunde}, {"a.md", "b.md"})
        self.assertTrue(all(x.regel == "F8" and x.schwere == "P2" for x in befunde))
        self.assertIn("konkurriert", befunde[0].text)

    def test_umlaut_faltung_und_kein_teilwort(self):
        self.assertTrue(fk._enthaelt("Ein guenstiges Girokonto ohne Gebuehren", "günstiges Girokonto"))
        self.assertFalse(fk._enthaelt("Die Kontoführung ist kostenlos", "Konto"))

    def test_vorschlag_vermeidet_vergebene_primaer_keywords(self):
        fm = {"keywords": ["Strom sparen für Haushalte", "Tagesgeld Vergleich 2026"]}
        vergeben = {fk.normalisiere("Strom sparen für Haushalte")}
        vorschlag = fk.vorschlag_fokus(fm, vergeben)
        self.assertNotIn("Strom sparen für Haushalte", vorschlag)
        self.assertIn("Tagesgeld Vergleich 2026", vorschlag)

    def test_bericht_ohne_befund_macht_keine_ranking_aussage(self):
        _, stand = fk.pruefe_dokument("x.md", dokument())
        md = fk.bericht_md([], [stand])
        self.assertIn("keine Aussage über Inhalt oder Ranking", md)

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(fk.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
