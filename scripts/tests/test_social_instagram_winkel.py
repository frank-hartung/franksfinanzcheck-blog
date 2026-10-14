#!/usr/bin/env python3
"""Regressionstest: Instagram-Winkel sind eigenständig (#716-Familie).

Anlass (14.10.2026, CI `regression` rot seit PR #743): Der Ratgeber
„DNS-Server wechseln“ war auf Instagram in KEINEM Winkel sendbar. Zwei
Ursachen verstärkten sich:

  1. L7 (Geschrei) zählte die Fachkürzel DNS/HTTPS/TLS als Versalien-Geschrei
     – festgehalten in `test_social_gate_l9.TestL7Fachkuerzel`.
  2. Die Instagram-Caption war winkelBLIND: alle sechs Winkel lieferten Wort
     für Wort denselben Text. Ein Falschurteil traf damit jeden Winkel
     zugleich, das Nachrücken auf einen anderen Winkel lief ins Leere.

Dieser Test hält Punkt 2 fest – und die Nebenbefunde derselben Prüfung:
der FAQ-Leser fand nie eine Frage (fehlendes DOTALL), der Satzteiler riss
Daten ab („vom 1.“), die Rechenwege-Formel stand auch unter Ratgebern ohne
eine einzige Zahl, und „karussell“ versprach Folien, die der Adapter (ein
Einzelbild) nie sendet.
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import social_channels as sch     # noqa: E402
import social_copywriter as copy  # noqa: E402
import social_gate as gate        # noqa: E402

CFG = sch.load_config()
CHANNELS = sch.channel_map(CFG)
META = sch.meta_of(CFG)
IG = CHANNELS["instagram"]
WINKEL = list(IG.get("angles") or ["nutzen"])


def _artikel(**extra) -> dict:
    art = {
        "slug": "probe", "path": "", "title": "Router-Tarif prüfen: So gehst du vor",
        "description": "Wie du deinen Router-Tarif prüfst.",
        "kurzantwort": ("Ein Tarifcheck dauert 15 Minuten. Er zeigt dir, ob du zu viel "
                        "zahlst. Ein Wechsel ist nicht automatisch günstiger, wenn der "
                        "Bonus wegfällt. Prüfe deshalb den Effektivpreis."),
        "takeaways": ["Vergleiche den Effektivpreis über die volle Laufzeit.",
                      "Ein Wechselbonus zählt nur im ersten Vertragsjahr.",
                      "Kündige rechtzeitig vor der automatischen Verlängerung."],
        "faq_question": "Lohnt sich ein Wechsel jedes Jahr?",
        "faq_answer": "Meistens ja. Neukunden bekommen fast immer bessere Konditionen.",
        "tags": ["Internet", "Tarifwechsel"], "keywords": ["Router-Tarif prüfen"],
        "pillar": "internet-dsl", "pin_title": "", "cover": "", "cover_alt": "",
        "draft": False, "reserve": False, "published": "",
        "url": "https://franksfinanzcheck.de/posts/probe/", "raw_fm": "",
    }
    art.update(extra)
    art["hook_sentences"] = copy.sentences(art["kurzantwort"])
    art["hook"] = art["hook_sentences"][0] if art["hook_sentences"] else ""
    art["numbers"] = copy.extract_numbers(
        f"{art['kurzantwort']} {art['description']} {art['title']}")
    return art


def _caption(art: dict, winkel: str) -> str:
    return copy.compose(art, "instagram", IG, winkel, META, use_llm=False)["text"]


class TestWinkelSindEigenstaendig(unittest.TestCase):
    def test_jeder_winkel_hat_einen_eigenen_zugang(self):
        texte = {w: _caption(_artikel(), w) for w in WINKEL}
        self.assertEqual(len(set(texte.values())), len(WINKEL),
                         "zwei Winkel liefern denselben Text")

    def test_erste_zeile_passt_vor_das_mehr(self):
        for w in WINKEL:
            with self.subTest(winkel=w):
                erste = _caption(_artikel(), w).split("\n\n", 1)[0]
                self.assertLessEqual(len(erste), copy.VISUAL_OPENER_MAX + 2)

    def test_zahl_winkel_fuehrt_mit_einer_belegten_zahl(self):
        erste = _caption(_artikel(), "zahl").split("\n\n", 1)[0]
        self.assertIn("15 Minuten", erste)

    def test_zahl_winkel_erfindet_ohne_zahl_nichts(self):
        art = _artikel(kurzantwort="Ein Tarifcheck lohnt sich. Er zeigt Kostenfallen.",
                       description="Tarif prüfen.", title="Tarif prüfen")
        self.assertEqual(_caption(art, "zahl"), _caption(art, "nutzen"))

    def test_frage_winkel_zitiert_die_faq(self):
        text = _caption(_artikel(), "frage")
        self.assertTrue(text.startswith("Lohnt sich ein Wechsel jedes Jahr?"))
        self.assertIn("Neukunden bekommen", text)

    def test_mythos_kommt_aus_dem_artikel_wenn_er_korrigiert(self):
        text = _caption(_artikel(), "mythos")
        self.assertIn("nicht automatisch günstiger", text)
        self.assertNotIn(copy.MYTHS["internet-dsl"], text)

    def test_karussell_verspricht_keine_folien(self):
        text = _caption(_artikel(), "karussell")
        self.assertNotIn("Folie", text)
        self.assertIn("1. Vergleiche den Effektivpreis", text)

    def test_karussell_ohne_takeaways_faellt_ehrlich_zurueck(self):
        art = _artikel(takeaways=[])
        self.assertEqual(_caption(art, "karussell"), _caption(art, "nutzen"))

    def test_rechenwege_nur_wo_gerechnet_wird(self):
        mit = _caption(_artikel(), "nutzen")
        ohne = _caption(_artikel(kurzantwort="Ein Router braucht Updates. Sonst drohen Lücken.",
                                 description="Router absichern.", title="Router absichern"),
                        "nutzen")
        self.assertIn("Rechenwege", mit)
        self.assertNotIn("Rechenwege", ohne)
        self.assertIn("Link in der Bio", ohne)

    def test_alle_winkel_bestehen_das_gate(self):
        for w in WINKEL:
            with self.subTest(winkel=w):
                pkg = copy.compose(_artikel(), "instagram", IG, w, META, use_llm=False)
                pkg["media_url"] = "https://franksfinanzcheck.de/cover.jpg"
                ok, viol, _ = gate.check(pkg, IG, META, history=[])
                self.assertTrue(ok, viol)


class TestWinkelRedundanzImBestand(unittest.TestCase):
    """Frühwarnung VOR dem Vollausfall: Ein einzelnes Falschurteil darf nie
    alle Winkel eines Artikels treffen. Der Vorfall hatte genau 0 sendbare
    Instagram-Winkel; Bluesky stand im selben Bestand bei einem einzigen."""

    @classmethod
    def setUpClass(cls):
        cls.pool = copy.article_pool(base_url=str(META.get("base_url") or copy.DEFAULT_BASE))

    def test_instagram_jeder_artikel_mit_mehreren_eigenen_sendbaren_winkeln(self):
        self.assertTrue(self.pool)
        knapp = {}
        for art in self.pool:
            frei = set()
            for w in WINKEL:
                pkg = copy.compose(art, "instagram", IG, w, META, use_llm=False)
                pkg["media_url"] = "https://franksfinanzcheck.de/cover.jpg"
                ok, _v, _m = gate.check(pkg, IG, META, history=[])
                if ok:
                    frei.add(pkg["text"])
            if len(frei) < 3:
                knapp[art["slug"]] = len(frei)
        self.assertEqual(knapp, {}, "Artikel mit < 3 verschiedenen sendbaren Captions")

    def test_jeder_kanal_jeder_artikel_mindestens_zwei_sendbare_winkel(self):
        for cid, ch in CHANNELS.items():
            winkel = ch.get("angles") or ["nutzen"]
            if len(winkel) < 2:
                continue
            with self.subTest(kanal=cid):
                knapp = []
                for art in self.pool:
                    frei = 0
                    for w in winkel:
                        pkg = copy.compose(art, cid, ch, w, META, use_llm=False)
                        pkg["media_url"] = "https://franksfinanzcheck.de/cover.jpg"
                        if gate.check(pkg, ch, META, history=[])[0]:
                            frei += 1
                    if frei < 2:
                        knapp.append(art["slug"])
                self.assertEqual(knapp, [], f"{cid}: nur ein Winkel trägt")


class TestMaterialLeser(unittest.TestCase):
    def test_faq_antwort_blutet_nicht_in_die_naechste_frage(self):
        body = ("## Häufige Fragen\n\n### Erste Frage?\n\nNein. Die Begründung folgt hier.\n\n"
                "### Zweite Frage?\n\nAndere Antwort.\n")
        frage, antwort = copy.extract_faq(body)
        self.assertEqual(frage, "Erste Frage?")
        self.assertEqual(antwort, "Nein. Die Begründung folgt hier.")
        self.assertNotIn("Zweite", antwort)

    def test_faq_ohne_block_bleibt_leer(self):
        self.assertEqual(copy.extract_faq("## Fazit\n\nText."), ("", ""))

    def test_satzteiler_reisst_keine_daten_ab(self):
        saetze = copy.sentences("Verträge laufen vom 1. Januar bis 31. Dezember. "
                                "Danach z. B. kündigen. Rund 31. Ende.")
        self.assertEqual(saetze, ["Verträge laufen vom 1. Januar bis 31. Dezember.",
                                  "Danach z. B. kündigen.", "Rund 31.", "Ende."])

    def test_hashtag_kuerzel_folgen_dem_haus_kanon(self):
        self.assertEqual(copy.to_hashtag("DNS over HTTPS"), "DNSOverHTTPS")
        self.assertEqual(copy.to_hashtag("DNS over TLS"), "DNSOverTLS")
        self.assertEqual(copy.to_hashtag("DSL Vergleich"), "DSLVergleich")  # unverändert


if __name__ == "__main__":
    unittest.main()
