"""Maschinenlesbare KI-Kennzeichnung: Deckung, Kanaltreue, Heilung (#1028).

Art. 50 Abs. 2 KI-VO, Frist 02.12.2026 für Bestandssysteme.

Diese Tests pinnen die Befunde vom 07.11.2026 als Vertrag. Der
Selbsttest des Gates (`ki_provenienz_gate.py --selftest`) beweist, dass
die Regeln an einer künstlichen Fassung anschlagen; hier geht es um das,
was nur am ECHTEN Bestand messbar ist – und was bei einem Rückfall
stumm kippen würde:

  1. DECKUNG  Das Gate prüfte 78 Seiten aus `content/posts`, ausgeliefert
     werden 109 reguläre Seiten in 19 Abschnitten. Sechs Ratgeber-Säulen
     mit synthetischer Stimme erfasste keine Regel.
  2. QUELLE   Die Antwort „welche Modalität ist deklariert" steht genau
     einmal im Bestand (`_funcs/ki_modalitaeten.html`). Eine zweite
     Abschrift driftet – gemessen am 07.11.2026 lag dieselbe
     Audio-Bedingung dreimal im Bestand (Vorlage, Feed, Article-Schema).
  3. HEILUNG  Mechanisch Heilbares wird geheilt und belegt; was nur ein
     Mensch entscheiden kann, wird eskaliert und nie erfunden.
  4. UHR      Die Wache committet keinen Zustand, der sich nur durch das
     Datum ändert (Lehre aus der Befundakte, 06.11.2026).
  5. WERKZEUG Eine ausgefallene Messung ist kein Grün (C33) und kein
     Inhaltsbefund: Exit 2 statt 1, Meldung über C38 statt Traceback.

Tests, die einen Build brauchen, überspringen sich ohne `public/` – der
Bestand wird in CI immer vor dem Testlauf gebaut.
"""
from pathlib import Path
import re
import tempfile
import unittest

from scripts import ki_provenienz as kp
from scripts import ki_provenienz_gate as gate

ROOT = kp.ROOT
BAU_VERFUEGBAR = (ROOT / kp.BAU / "index.xml").is_file()


def _frontmatter(zeilen: list[str]) -> str:
    return "---\n" + "\n".join(zeilen) + "\n---\n"


class FrontmatterLeserTest(unittest.TestCase):
    """Der Leser ist die Grundlage jeder Regel – er darf nichts erfinden."""

    def test_verschachtelter_wert_bei_beliebiger_einrueckung(self):
        # Befund 07.11.2026: Die alte Fassung verglich auf „Elterneinzug + 1".
        # YAML rückt hier mit zwei Leerzeichen ein – damit war JEDER
        # verschachtelte Wert None, auch `cover.ki_pruefung.digital_source_type`.
        kopf = _frontmatter([
            "title: Beispiel",
            "cover:",
            "  image: images/covers/x.jpg",
            "  ai_generated: true",
            "  ki_pruefung:",
            "    digital_source_type: trainedAlgorithmicMedia",
            "    geprueft_am: 2026-11-07",
        ])
        self.assertEqual(kp.pfad_wert(kopf, ("cover", "image")), "images/covers/x.jpg")
        self.assertEqual(kp.pfad_wert(kopf, ("cover", "ai_generated")), "true")
        self.assertEqual(kp.pfad_wert(kopf, ("cover", "ki_pruefung",
                                             "digital_source_type")),
                         "trainedAlgorithmicMedia")
        self.assertIsNone(kp.pfad_wert(kopf, ("cover", "gibt_es_nicht")))
        self.assertIsNone(kp.pfad_wert(kopf, ("gibt_es_nicht", "auch_nicht")))

    def test_verschachteltes_feld_ist_kein_feld_auf_obenster_ebene(self):
        # `cover.ai_generated: true` darf nie als `ai_generated: true` der
        # Seite gelesen werden – sonst behauptet die Seite eine Text-Erzeugung,
        # die niemand belegt hat. Umgekehrt genauso.
        kopf = _frontmatter(["cover:", "  ai_generated: true"])
        self.assertEqual(kp.pfad_wert(kopf, ("cover", "ai_generated")), "true")
        self.assertIsNone(kp.pfad_wert(kopf, ("ai_generated",)))

    def test_liste_wird_nicht_als_schluessel_gelesen(self):
        kopf = _frontmatter(["ai_generated: false", "tags:", "- geld", "- sparen"])
        self.assertEqual(kp.pfad_wert(kopf, ("ai_generated",)), "false")
        self.assertIsNone(kp.pfad_wert(kopf, ("tags",)))

    def test_wahr_unterscheidet_false_von_fehlend(self):
        self.assertTrue(kp.wahr("true"))
        self.assertFalse(kp.wahr("false"))
        self.assertFalse(kp.wahr(""))
        self.assertFalse(kp.wahr(None))


class DeckungTest(unittest.TestCase):
    """Befund 1: Das Gate maß einen Ausschnitt, ausgeliefert wird der Baum."""

    def test_abschnitte_sind_nicht_auf_posts_verengt(self):
        abschnitte = {s.abschnitt for s in kp.seiten(ROOT)}
        self.assertIn("pillar", abschnitte,
                      "pillar/ war der blinde Fleck: sechs Säulen mit Stimme, "
                      "keine Regel dafür")
        self.assertGreaterEqual(len(abschnitte), 15,
                                f"nur {len(abschnitte)} Abschnitte erfasst")

    def test_alle_regularpages_ohne_entwurf_werden_geprueft(self):
        seiten = [s for s in kp.seiten(ROOT) if not s.entwurf]
        # Gemessen 07.11.2026: 109. Die Schwelle liegt bewusst darunter –
        # sie soll einen Rückfall auf 78 (nur posts) fangen, nicht jeden
        # neuen Artikel zum Testbruch machen.
        self.assertGreaterEqual(len(seiten), 100, f"nur {len(seiten)} Seiten")
        # Jenseits von posts/ muss messbar etwas erfasst sein.
        ausserhalb = [s for s in seiten if s.abschnitt != "posts"]
        self.assertGreaterEqual(len(ausserhalb), 20,
                                f"nur {len(ausserhalb)} Seiten außerhalb posts/ – "
                                "die Deckung ist wieder verengt")

    @unittest.skipUnless(BAU_VERFUEGBAR, "kein Build unter public/")
    def test_jede_regulaere_seite_hat_ein_bauprodukt(self):
        # Die Ableitung Inhalt → URL war der heikle Teil: `content/impressum/`
        # liefert `public/impressum/index.html`, nicht `impressum/…/`.
        fehlend = [s.slug for s in kp.seiten(ROOT)
                   if not s.entwurf and not (ROOT / s.bau_pfad).is_file()]
        self.assertEqual(fehlend, [], "Seiten ohne Bauprodukt – M1 wäre blind")

    @unittest.skipUnless(BAU_VERFUEGBAR, "kein Build unter public/")
    def test_bestand_ist_gruen(self):
        funde, geprueft, kenn = gate.pruefen(ROOT)
        self.assertEqual([f["text"] for f in funde], [])
        self.assertEqual(geprueft, kenn["seiten_live"],
                         "geprüfte Seiten ≠ ausgelieferte Seiten")
        # WARUM HIER KEINE 50 MEHR STEHT (Befund 08.11.2026, CI):
        # Die RSS-Vorlage kappt bei `services.rss.limit` = 50. Eine Schwelle
        # „≥ 50" ist damit eine Messung auf der Kante: Sobald EIN Item nicht
        # auf eine Seite zeigt (oder ein Artikel weniger ausgeliefert wird),
        # steht dort 49 – und der Test sagt nur „49 < 50", nicht WELCHES Item
        # fehlt. Genau so war der Job rot, ohne dass jemand die Ursache sehen
        # konnte. Die Blindheitsschwelle ist jetzt deutlich unter der Kappung,
        # und die eigentliche Zusage wird PRÄZISE geprüft: Jedes Item muss eine
        # Seite im Bestand haben (namentlich, nicht als Zahl).
        self.assertGreaterEqual(kenn["feed_items_geprueft"], 25,
                                f"nur {kenn['feed_items_geprueft']} Feed-Items – "
                                "M5 wäre fast blind")
        self.assertEqual(kenn["feed_items_ohne_seite"], [],
                         "Feed-Items ohne Seite im Bestand (M5 wäre für sie blind) – "
                         "Format: 'slug ← guid'")


class KanalquelleTest(unittest.TestCase):
    """Befund 2: Eine Bedingung, die zweimal dasteht, driftet."""

    def _bereiche(self, datei: str) -> set[str]:
        text = (ROOT / datei).read_text(encoding="utf-8", errors="ignore")
        return set(re.findall(r'eq (?:\$seite)?\.(?:Section|Type) "([a-z]+)"', text))

    def test_audiobedingung_ist_in_beiden_stellen_deckungsgleich(self):
        # Die Ausspielung der Lesehilfe entscheidet ff_voice_toolbar.html, die
        # Frage „ist eine Tonspur deklariert" beantwortet _funcs/ki_modalitaeten
        # – zwei Stellen, dieselbe Bedingung. Erlaubt ist das nur, solange sie
        # nachweislich deckungsgleich sind: Driften sie, spielt die Seite eine
        # synthetische Stimme und der scope nennt sie nicht (Befund 4).
        leiste = "layouts/_partials/ff_voice_toolbar.html"
        funktion = "layouts/_partials/_funcs/ki_modalitaeten.html"
        self.assertEqual(self._bereiche(leiste), self._bereiche(funktion),
                         "die Bereichslisten der Lesehilfe und des scope driften")
        self.assertEqual(self._bereiche(funktion), {"posts", "pillar", "ratgeber"},
                         "ein Bereich kam hinzu oder fiel weg – M4 neu justieren")
        for datei in (leiste, funktion):
            text = (ROOT / datei).read_text(encoding="utf-8", errors="ignore")
            self.assertIn("hideReaderToolbar", text, f"{datei} ignoriert den Schalter")
            self.assertTrue(".IsPage" in text or 'eq .Kind "page"' in text,
                            f"{datei} beschränkt nicht auf reguläre Seiten")

    def test_verbraucher_entscheiden_nicht_selbst(self):
        # Feed und Article-Schema rufen die Funktion auf und tippen die
        # Bedingung nicht nach. Am 07.11.2026 lag sie dreimal im Bestand.
        for datei in ("layouts/rss.xml", "layouts/_default/rss.xml",
                      "layouts/_partials/schema_article.html",
                      "layouts/_partials/ki_provenienz.html"):
            text = (ROOT / datei).read_text(encoding="utf-8", errors="ignore")
            self.assertNotIn("hideReaderToolbar", text,
                             f"{datei} bildet die Audio-Bedingung selbst nach")

    def test_verbraucher_rufen_die_funktion_auf(self):
        for datei, nadelpaar in (
                ("layouts/_partials/ki_provenienz.html", "_funcs/ki_modalitaeten.html"),
                ("layouts/_partials/schema_article.html", "_funcs/ki_modalitaeten.html"),
                ("layouts/rss.xml", "_funcs/ki_modalitaeten.html")):
            text = (ROOT / datei).read_text(encoding="utf-8", errors="ignore")
            self.assertIn(nadelpaar, text, f"{datei} entscheidet wieder selbst")

    def test_vertragsnadeln_sind_erfuellt_und_werden_gelesen(self):
        vertraege = kp.kanal_vertrag(ROOT)
        # 13 Nadeln am 07.11.2026 – eine weniger heißt: ein Kanal ist wieder
        # ungeschützt entstanden.
        self.assertGreaterEqual(len(vertraege), 13)
        offen = []
        for v in vertraege:
            datei = ROOT / v.datei
            if not datei.is_file():
                offen.append(f"{v.datei} fehlt")
            elif v.nadel not in datei.read_text(encoding="utf-8", errors="ignore"):
                offen.append(f"{v.datei}: {v.nadel!r}")
        self.assertEqual(offen, [], f"Vertragsnadeln offen: {offen}")

    def test_regel_m6_prueft_die_vertragsnadel_nicht_eine_eigene(self):
        # Zwei Abschriften derselben Prüfung sind genau der Drift, den M2
        # verhindern soll: Die Regel liest `v.nadel` aus dem Vertrag.
        quelle = Path(gate.__file__).read_text(encoding="utf-8")
        self.assertIn("v.nadel not in datei.read_text", quelle)

    def test_feed_traegt_den_kanal_auf_beiden_ebenen(self):
        # Gemessen am gebauten Feed, nicht an der Vorlage: Die Vorlage kann
        # stimmen und der Build trotzdem leer sein (Bedingung, Namespace,
        # Item-Kontext). `bool(Element)` ist für ein kindloses Element False –
        # deshalb zählt feed_items() über `is None`.
        items = kp.feed_items(kp.feed_pfad(ROOT))
        self.assertGreaterEqual(len(items), 50, f"nur {len(items)} Feed-Items")
        ohne = [i.get("guid") or i.get("link") for i in items if not i.get("describedby")]
        self.assertEqual(ohne, [], "Items ohne ffki:describedby – Verweis läuft ins Leere")
        self.assertTrue(kp.feed_kanal_angabe(kp.feed_pfad(ROOT)),
                        "die Kanal-Ebene des Feeds nennt die Herkunftsangabe nicht")
        text = (ROOT / "layouts/rss.xml").read_text(encoding="utf-8", errors="ignore")
        self.assertIn(f'xmlns:ffki="{kp.NAMESPACE}"', text)


class ErwartungTest(unittest.TestCase):
    """Was eine Seite deklarieren MUSS – und was sie nie behaupten darf."""

    #: Lesehilfe ausgeliefert – wie sie `kp.signale()` aus dem Bau liest.
    MIT_LESEHILFE = {"toolbar": True, "meta": False, "bereiche": (),
                     "describedby": False, "anker": {}, "credit": "",
                     "bild_attribut": False}
    OHNE_LESEHILFE = dict(MIT_LESEHILFE, toolbar=False)

    def _seite(self, kopf: str, **kw) -> kp.Seite:
        return kp.Seite(pfad=Path("content/posts/beispiel.md"),
                        abschnitt=kw.pop("abschnitt", "posts"),
                        slug="beispiel", basis="posts/beispiel",
                        ki_text=kp.wahr(kp.pfad_wert(kopf, ("ai_generated",))),
                        ki_bild=kp.wahr(kp.pfad_wert(kopf, ("cover", "ai_generated"))),
                        quellentyp="", entwurf=False, kopf=kopf,
                        lesehilfe_aus=kw.pop("lesehilfe_aus", False), **kw)

    def test_text_und_bild_aus_dem_frontmatter(self):
        seite = self._seite(_frontmatter(["ai_generated: true", "cover:",
                                          "  ai_generated: true"]))
        self.assertEqual(kp.erwartet(seite, self.MIT_LESEHILFE),
                         ("text", "image", "audio"))

    def test_audio_folgt_der_auslieferung_nicht_dem_frontmatter(self):
        # Die Tonspur wird aus dem BAUPRODUKT abgeleitet (Lesehilfe sichtbar)
        # und nicht aus einer nachgebauten Template-Bedingung: Ändert jemand
        # die Ausspielung, folgt die Erwartung – ein zweiter Pflegeort wäre
        # genau der Fehler, den M4 verhindern soll.
        kopf = _frontmatter(["ai_generated: true"])
        self.assertIn("audio", kp.erwartet(self._seite(kopf), self.MIT_LESEHILFE))
        self.assertEqual(kp.erwartet(self._seite(kopf), self.OHNE_LESEHILFE), ("text",))
        self.assertEqual(kp.erwartet(self._seite(kopf, lesehilfe_aus=True),
                                     self.MIT_LESEHILFE), ("text",))

    def test_ohne_ki_angabe_entsteht_kein_signal(self):
        # `ai_generated: false` darf keine Behauptung „rein menschlich"
        # erzeugen – überkennzeichnet ist rechtlich harmlos, erfunden nicht.
        seite = self._seite(_frontmatter(["ai_generated: false"]))
        self.assertEqual(kp.erwartet(seite, self.OHNE_LESEHILFE), ())

    def test_scope_ist_ein_geordnetes_vokabular(self):
        self.assertEqual(tuple(kp.MODALITAETEN), ("text", "image", "audio"))


class SpiegelTest(unittest.TestCase):
    """Befund: Zwei RSS-Vorlagen – welche gilt, hängt an der Hugo-Version."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.kanal = f'<rss xmlns:ffki="{kp.NAMESPACE}">'
        for rel in (kp.RSS_QUELLE, kp.RSS_SPIEGEL):
            datei = self.root / rel
            datei.parent.mkdir(parents=True, exist_ok=True)
            datei.write_text(self.kanal + "<ffki:ai-generated-scope/></rss>",
                             encoding="utf-8")

    def _schreiben(self, rel: str, inhalt: str) -> None:
        (self.root / rel).write_text(inhalt, encoding="utf-8")

    def test_bytgleich_ist_kein_befund(self):
        self.assertEqual(kp.rss_spiegel_abweichung(self.root), "")

    def test_drift_in_eine_richtung_ist_heilbar(self):
        self._schreiben(kp.RSS_SPIEGEL, "<rss>ohne Kanal</rss>")
        self.assertEqual(kp.rss_spiegel_abweichung(self.root), "quelle")
        ergebnis = kp.heilen(self.root)
        self.assertEqual([e["art"] for e in ergebnis["eingriffe"]], ["spiegel"])
        self.assertEqual((self.root / kp.RSS_QUELLE).read_bytes(),
                         (self.root / kp.RSS_SPIEGEL).read_bytes())
        self.assertEqual(kp.rss_spiegel_abweichung(self.root), "")

    def test_beidseitiger_kanal_ist_entscheidung_nicht_heilung(self):
        # Tragen BEIDE Fassungen einen Kanal, aber verschiedene, darf die
        # Wache nicht raten – sie würde eine redaktionelle Fassung löschen.
        self._schreiben(kp.RSS_QUELLE, self.kanal + "<ffki:ai-generated-scope/>A</rss>")
        self._schreiben(kp.RSS_SPIEGEL, self.kanal + "<ffki:ai-generated-scope/>B</rss>")
        self.assertEqual(kp.rss_spiegel_abweichung(self.root), "beide")
        ergebnis = kp.heilen(self.root)
        self.assertEqual(ergebnis["eingriffe"], [])
        self.assertTrue(ergebnis["eskalation"], "eine Entscheidung muss eskalieren")

    def test_anker_wird_bytreu_wiederhergestellt(self):
        # Geprüft am echten Text der Überschrift (07.11.2026: „Hinweis zu
        # KI-unterstützten Inhalten") – die Formulierung ist redaktionell, die
        # Heilung darf sie nicht umtexten.
        impressum = self.root / kp.IMPRESSUM
        impressum.parent.mkdir(parents=True, exist_ok=True)
        ursprung = ("---\ntitle: Impressum\n---\n\n## Kontakt\n\nText\n\n"
                    "## Hinweis zu KI-unterstützten Inhalten\n\nMehr Text\n")
        impressum.write_text(ursprung, encoding="utf-8")
        geheilt = kp._anker_einsetzen(ursprung)
        self.assertIn(kp.IMPRESSUM_ANKER, geheilt)
        self.assertIn("## Hinweis zu KI-unterstützten Inhalten {#ki-hinweis}", geheilt)
        # Zweiter Lauf: idempotent, keine zweite Ankerung.
        self.assertEqual(kp._anker_einsetzen(geheilt), geheilt)
        # Der übrige Text bleibt unberührt.
        self.assertIn("## Kontakt", geheilt)
        self.assertIn("Mehr Text", geheilt)


class WacheTest(unittest.TestCase):
    """Dauerhaft heißt: heilen, belegen, Altern führen – und nicht die Uhr."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "content/posts").mkdir(parents=True)
        (self.root / "content/posts/a.md").write_text(
            _frontmatter(["title: A", "ai_generated: true"]), encoding="utf-8")

    def test_zweiter_lauf_schreibt_keinen_zustand(self):
        erster = gate.wache(self.root, nur_quelle=True)
        self.assertTrue(erster["state_geaendert"], "erster Lauf muss den Zustand anlegen")
        (self.root / "data" / "ki_provenienz_state.json").write_text(
            __import__("json").dumps(erster["state"], ensure_ascii=False, indent=2),
            encoding="utf-8")
        zweiter = gate.wache(self.root, nur_quelle=True)
        self.assertFalse(zweiter["state_geaendert"],
                         "die Wache würde täglich committen, was nur die Uhr ist")
        self.assertEqual(zweiter["lage"]["ungeklaert"], erster["lage"]["ungeklaert"])
        self.assertEqual(zweiter["state"], erster["state"],
                         "derselbe Bestand erzeugt nicht denselben Zustand")

    def test_abgeleitete_zahlen_stehen_nicht_im_dauerzustand(self):
        # Alter und Restfrist ändern sich täglich, ohne dass sich am Bestand
        # etwas ändert. Gespeichert wird nur, was der Bestand vorgibt.
        ergebnis = gate.wache(self.root, nur_quelle=True)
        for feld in ("tage_bis_frist", "aeltester_alter_tage", "ungeklaert"):
            self.assertNotIn(feld, ergebnis["state"],
                             f"{feld} im Dauerzustand erzeugt tägliche Commits")
            self.assertIn(feld, ergebnis["lage"], f"{feld} fehlt im Bericht")
        # „zuletzt" heißt hier: zuletzt GEÄNDERT. Ein Feld, das bei jedem Lauf
        # kippt, würde den Commit-Takt der Wache diktieren.
        self.assertIn("zuletzt_geaendert", ergebnis["state"])

    def test_heilung_schreibt_eine_belegzeile(self):
        (self.root / kp.RSS_QUELLE).parent.mkdir(parents=True, exist_ok=True)
        (self.root / kp.RSS_QUELLE).write_text(
            f'<rss xmlns:ffki="{kp.NAMESPACE}"><ffki:ai-generated-scope/></rss>',
            encoding="utf-8")
        (self.root / kp.RSS_SPIEGEL).parent.mkdir(parents=True, exist_ok=True)
        (self.root / kp.RSS_SPIEGEL).write_text("<rss/>", encoding="utf-8")
        ergebnis = gate.heilen(self.root, nur_quelle=True)
        self.assertEqual([e["art"] for e in ergebnis["eingriffe"]], ["spiegel"])
        beleg = self.root / kp.LEDGER
        self.assertTrue(beleg.is_file(), "eine Heilung ohne Beleg ist nicht prüfbar")
        zeile = beleg.read_text(encoding="utf-8").strip().splitlines()[-1]
        self.assertIn("spiegel", zeile)
        self.assertIn("revision", zeile)

    def test_trockenlauf_veraendert_nichts(self):
        (self.root / kp.RSS_QUELLE).parent.mkdir(parents=True, exist_ok=True)
        (self.root / kp.RSS_QUELLE).write_text(
            f'<rss xmlns:ffki="{kp.NAMESPACE}"><ffki:ai-generated-scope/></rss>',
            encoding="utf-8")
        (self.root / kp.RSS_SPIEGEL).parent.mkdir(parents=True, exist_ok=True)
        (self.root / kp.RSS_SPIEGEL).write_text("<rss/>", encoding="utf-8")
        ergebnis = gate.heilen(self.root, trocken=True, nur_quelle=True)
        self.assertEqual((self.root / kp.RSS_SPIEGEL).read_text(encoding="utf-8"),
                         "<rss/>", "ein Trockenlauf darf nicht schreiben")
        self.assertFalse((self.root / kp.LEDGER).exists())
        self.assertTrue(ergebnis["eingriffe"] or ergebnis["funde"],
                        "ein Trockenlauf muss trotzdem sagen, was er täte")


class WerkzeugTest(unittest.TestCase):
    """C33/C38: Ausgefallene Messung ist weder grün noch ein Inhaltsbefund."""

    def test_fehlendes_messwerkzeug_ist_exit_2_nicht_exit_1(self):
        # Bewusst `gate.kp`: Läuft das Gate als Skript, ist sein Kern das
        # Modul `ki_provenienz`, unter unittest `scripts.ki_provenienz`. Wer
        # das falsche Objekt patcht, testet eine Kopie (Befund: zwei Objekte
        # desselben Codes). Nach der Import-Härtung ist beides dasselbe.
        self.assertIs(gate.kp, kp, "CLI und Tests nutzen zwei Modulobjekte")
        original = gate.kp.abhaengigkeiten
        gate.kp.abhaengigkeiten = lambda root=None: ["pillow (Probe)"]
        self.addCleanup(lambda: setattr(gate.kp, "abhaengigkeiten", original))
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "content/posts").mkdir(parents=True)
            (root / "content/posts/a.md").write_text(
                _frontmatter(["title: A"]), encoding="utf-8")
            funde, _geprueft, kenn = gate.pruefen(root, nur_quelle=True)
            self.assertEqual(kenn.get("werkzeug_blind"), ["pillow (Probe)"])
            self.assertTrue(any(f["regel"] == "W0" for f in funde),
                            "Blindheit muss als W0 sichtbar sein")

    def test_werkzeugbefund_geht_ueber_den_einen_meldeweg(self):
        # `melden` gibt IMMER 0 zurück und wirft nie (#227) – sonst tötet der
        # Melder den Schritt, den er melden soll.
        with tempfile.TemporaryDirectory() as temp:
            datei = Path(temp) / "befunde.txt"
            import os
            alt = os.environ.get("WERKZEUGBEFUNDE_DATEI")
            os.environ["WERKZEUGBEFUNDE_DATEI"] = str(datei)
            self.addCleanup(lambda: (os.environ.pop("WERKZEUGBEFUNDE_DATEI", None),
                                     alt and os.environ.__setitem__(
                                         "WERKZEUGBEFUNDE_DATEI", alt)))
            self.assertEqual(kp.werkzeugbefund_melden("probe", "Text"), None)
            self.assertIn("Text", datei.read_text(encoding="utf-8"))


class BildAbleitungTest(unittest.TestCase):
    """Befund 5: Der Optimizer kannte deklarierte KI-Originale nicht."""

    def test_ableitungspfade_entsprechen_den_erwarteten_varianten(self):
        pfade = kp.abgeleitete_pfade("images/covers/x.jpg")
        self.assertTrue(any(p.endswith(".webp") for p in pfade), pfade)
        self.assertTrue(any("webp" in p for p in pfade), pfade)
        self.assertTrue(all(not p.startswith("/") for p in pfade))

    def test_breiten_stimmen_mit_dem_optimizer_ueberein(self):
        quelle = (ROOT / "scripts/image_optimizer.py").read_text(encoding="utf-8",
                                                                errors="ignore")
        for breite in kp.BREITEN:
            self.assertIn(str(breite), quelle,
                          f"{breite}px wird erzeugt, aber nicht als Ableitung erkannt")

    def test_optimizer_verweigert_ableitungen_von_ki_originalen(self):
        quelle = (ROOT / "scripts/image_optimizer.py").read_text(encoding="utf-8",
                                                                errors="ignore")
        self.assertIn("def ki_originale(", quelle)
        self.assertIn("KI_ORIGINAL_UEBERSPRUNGEN", quelle)
        self.assertIn("KI_ABLEITUNG_UNMARKIERT", quelle)
        # Fail-closed: Ohne Kernbibliothek darf der Optimizer nicht still
        # jedes Original für menschlich halten.
        self.assertIn("SystemExit", quelle)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
