"""Offline-Regression für die redaktionelle Korrektur von Issue #763.

Stand 16.10.2026: Die Tests prüfen BEDEUTUNGS-Invarianten statt starrer
Formulierungen. Grund: Nach der ersten Korrektur-runde (15.10.) hatten
Folge-Läufe (#766 Einzigartigkeit, Lesbarkeits-Glättung) den Wortlaut
unbedenklich umgeschrieben – und die alten Exaktzeichenketten-Assertions
wurden rot, ohne dass ein Sachfehler zurückgekehrt war. Ein Test, den jede
Umformung bricht, schützt nichts; er provoziert nur, dass jemand ihn löscht.

Was dadurch garantiert bleibt:
  * die neun gemeldeten Fehlbehauptungen dürfen (behauptend) nie zurückkehren;
  * Rechenwerte, Einheiten und Quellenabgrenzungen müssen stimmen;
  * Modellrechnungen müssen als Annahmen gekennzeichnet sein;
  * Werbung und fachliche Quelle müssen im selben Absatz getrennt bleiben;
  * die Publish-Gates (Zeichenlänge Floor, Lesbarkeits-Harte,
    Textverständnis-HART) müssen die zwei Artikel grün durchlassen – der
    Reisearikel war am 16.10. wegen Flesch 40 vom Kadenz-Gate gehalten.

Kein Ersatz für eine Fachprüfung: Dies ist ein Rückfall-Schutz, kein
allgemeiner Wahrheitsbeweis.
"""
import datetime as dt
from decimal import Decimal
from pathlib import Path
import re
import sys
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import faktenfrische  # noqa: E402

HEIZ = '2026-10-14-heizperiode-vorbereiten-im-spaetsommer'
REISE = '2026-10-14-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen'
KORRIGIERT_AM = dt.date(2026, 10, 15)
DASHES = {
    '\u2013': '-', '\u2014': '-', '\u2012': '-', '\u2011': '-',
    '\u00a0': ' ', '\u202f': ' ', '‑': '-',
}


def resolve(slug):
    """Slug über Lebenszyklus-Umbenennungen hinweg auflösen (Nachschärfung
    24.10.2026, Befund zu #823): Die Kadenz hat den Reiseartikel am 24.10.
    neu datiert veröffentlicht (Verzeichnis `2026-10-24-…`) – derselbe Text,
    anderes Datumspräfix. Ein Test, der am Präfix klebt, bricht bei jeder
    harmlosen Umbenennung; genau diese Lehre steht im Modulkopf. Deshalb:
    exakter Treffer gewinnt, sonst eindeutiger Fund über den Namens-Kern.
    """
    posts = ROOT / 'content' / 'posts'
    exact = posts / slug
    if (exact / 'index.md').is_file():
        return exact
    kern = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', slug)
    treffer = sorted(p for p in posts.glob(f'*-{kern}') if (p / 'index.md').is_file())
    if len(treffer) == 1:
        return treffer[0]
    raise FileNotFoundError(
        f'{slug}: weder exakt noch eindeutig als *-{kern} in content/posts '
        f'(Treffer: {[p.name for p in treffer]})')


def read(slug):
    text = (resolve(slug) / 'index.md').read_text(encoding='utf-8')
    _, fm, body = text.split('---', 2)
    return yaml.safe_load(fm), body


def norm(text):
    """Kleinschreibung, Euro-Zeichen, Trennstriche und Leerläufe glätten.

    Damit ist ein Test gegen Umformungen robust („39,42 €“ == „39,42 Euro“,
    „–“ == “-“), aber nicht gegen inhaltliche Änderungen.
    """
    for a, b in DASHES.items():
        text = text.replace(a, b)
    text = text.replace('€', ' euro')
    return re.sub(r'\s+', ' ', text.lower()).strip()


def sentences(text):
    """Fließtext-Sätze; Überschriften-/Tabellen-/Listenzeilen ausgenommen.

    Strukturelle Zeilen tragen die Botschaft der Absatz-Ebene nicht mit und
    würden sonst Scheinfunde erzeugen (z. B. die FAQ-Frage „Wie viel spare
    ich durch Entlüften?“).
    """
    flow = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s[0] in '#|*' or re.match(r'^[-+\d].{0,3}[.)]?\s', s):
            continue
        flow.append(s)
    return [s for s in re.split(r'(?<=[.!?])\s+', norm(' '.join(flow))) if s]


def paragraphs(text):
    return [norm(p) for p in re.split(r'\n\s*\n', text) if p.strip()]


class Faktenfrische763Tests(unittest.TestCase):
    """Die neun Befunde aus dem Report vom 15.10.2026 – je einer pro Art.

    Nummerierung wie im Issue: B1–B4 Heizartikel, B5–B9 Reiseartikel.
    """

    # --- B1: „Entlüften spart pauschal 5 %“ -------------------------------
    def test_b1_entiueften_ohne_sparquoten_behauptung(self):
        _, body = read(HEIZ)
        for sent in sentences(body):
            if 'entl' in sent and ('spar' in sent or 'prozent' in sent or '%' in sent):
                if '?' in sent:
                    continue  # erlaubte Leserfrage (die Antwort verneint)
                if not re.search(r'(nicht|kein|ohne)', sent):
                    self.fail(f'behauptende Sparquote beim Entlüften kehrt zurück: {sent!r}')
        joined = norm(body)
        # Sicherung: die Einschränkung muss ebenfalls im Text stehen.
        self.assertTrue(
            re.search(r'(keine|nicht|kein)\w*[^.]{0,60}(festen prozente|feste summe'
                      r'|sichere ersparnis|garantierte sparquote|fester gewinn)', joined),
            'Die Entwarnung „keine garantierte Ersparnis beim Entlüften“ fehlt.')

    # --- B2: Raumthermostat pauschal 20 °C ---------------------------------
    def test_b2_raumtemperatur_nur_als_orientierung(self):
        _, body = read(HEIZ)
        for sent in sentences(body):
            if '20' in sent and ('grad' in sent or '°c' in sent):
                if re.match(r'(stelle|setz)\w*', sent) or re.search(r'muss \w{0,12}(auf )?20', sent):
                    self.fail(f'20 °C wieder als Pauschal-Vorgabe: {sent!r}')
        self.assertTrue(re.search(
            r'20 grad[^.]{0,90}(kann|orientierung|start|hilfe|grob)', norm(body)),
            '20 Grad müssen als möglicher Ausgangspunkt stehen (Befund 2).')

    # --- B3: Router „im Standby mit 5 W“ -----------------------------------
    def test_b3_keine_geraetewatt_behauptung(self):
        _, body = read(HEIZ)
        for sent in sentences(body):
            if 'router' in sent and re.search(r'\d+\s*(watt|w\b)', sent):
                self.fail(f'Router mit festem Watt-Wert behauptet: {sent!r}')
        # Die 5 W dürfen nur als gekennzeichnete Rechenannahme vorkommen.
        for para in paragraphs(body):
            if para.lstrip().startswith(('|', '#', '-', '1.', '2.', '3.', '4.')):
                continue  # Tabellen-/Listen-/Heading-Zeilen hängen am Textabsatz davor
            if re.search(r'\b5 watt', para):
                self.assertTrue(
                    re.search(r'(annahmen|angenommen|frei gewählt)', para),
                    f'5-Watt-Wert ohne Annahmen-Kennzeichnung: {para[:160]}')

    # --- B4: CHECK24 durch Behördenquelle gestützt -------------------------
    # Haus-CTA-Marker (Nachschärfung 24.10.2026): Die Affiliate-Pipeline setzt
    # „Spar-Tipp zwischendurch“-Blöcke als Blockzitat mit 💶 – ein sanktioniertes
    # Hausmuster, das die affiliate_integrity_gate (AI1–AI5, CTA_MARKERS) selbst
    # bewacht. Für sie gilt die Prosa-Offenlegungspflicht dieses Tests nicht;
    # ein /go/-Absatz ist nur dann ausgenommen, wenn er einen Hausmarker trägt.
    # Der Global-Check (Transparenz-Hinweis VOR dem ersten /go/-Link) bleibt für
    # alle Absätze scharf – auch für Haus-CTAs.
    HAUS_CTA = ('spar-tipp zwischendurch', 'schnell-tipp von franksfinanzcheck',
                'jetzt vergleichen und sparen', 'sparend zuerst vergleichen')

    def test_b4_werbung_von_fachquelle_getrennt(self):
        for slug in (HEIZ, REISE):
            with self.subTest(slug=slug):
                _, body = read(slug)
                joined = norm(body)
                # a) Jeder PROSA-Absatz mit Affiliate-/Go-Link: Werbung benennen,
                #    Fachlichkeit absprechen, Offenlegung VOR dem ersten Link.
                go_para = [p for p in paragraphs(body)
                           if ('/go/' in p or 'preisvergleich' in p and 'werbung' in p)
                           and not any(m in p for m in self.HAUS_CTA)]
                self.assertTrue(go_para, 'CTA-Absatz nicht gefunden')
                for para in go_para:
                    self.assertTrue(
                        ('werbung' in para or 'provision' in para)
                        and re.search(r'kein\w*[^.]{0,60}(beleg|empfehlung)', para),
                        f'Werbeabsatz ohne Trennung zur Fachlichkeit ({slug}): {para[:140]}')
                self.assertTrue(joined.index('transparenz') < joined.index('/go/'),
                                'Die Offenlegung muss vor dem ersten /go/-Link stehen.')
                # b) Satz-Ebene: Portal + Behörde/Verbraucherzentrale im selben
                #    Satz darf nur mit Verneinung stehen (keine Behördenweiheihung).
                for sent in sentences(body):
                    portal = re.search(r'check24|mietwagen[- ]?vergleich|vergleichsportal', sent)
                    behörde = re.search(r'(behörde|amt|verbraucherschutz'
                                        r'|bundesnetzagentur|verbraucherzentrale'
                                        r'|empfehlung)', sent)
                    if portal and behörde:
                        self.assertTrue(re.search(r'(nicht|keine|kein|weder)', sent),
                                        f'Portal ohne Abgrenzung zur Fachquelle: {sent!r}')

    # --- B5: „Reiseangebote 2026 preislich stabilisiert“ -------------------
    def test_b5_keine_unbelegte_marktbehauptung(self):
        _, body = read(REISE)
        joined = norm(body)
        self.assertNotIn('stabilisiert', joined)
        self.assertNotIn('preislich stabil', joined)
        for sent in sentences(body):
            if 'stabilisierung' in sent:
                self.assertIn('nicht', sent, f'Stabilisierung ohne Verneinung: {sent!r}')
        self.assertTrue(re.search(r'echte[n]? angebote|angebote für dein datum', joined),
                        'Konkrete Angebote müssen als Weg genannt sein (Befund 5).')

    # --- B6: Bank-Cashback als wesentliche Budgetquelle --------------------
    def test_b6_cashback_nur_optional(self):
        _, body = read(REISE)
        joined = norm(body)
        self.assertNotIn('viele banken bieten', joined)
        self.assertTrue(re.search(r'(wir|behaupten) [^.]{0,60}nicht, dass jede bank', joined),
                        'Die availability-Verneinung (Befund 6) fehlt.')
        for need in ('höchstbetrag', 'gebühren', 'datenschutz', 'ausgezahlt'):
            self.assertIn(need, joined, f'Cashback-Bedingung „{need}“ fehlt im Prüfkasten.')

    # --- B7: Gesponserter Mietwagenvergleich als fachlich belegt -----------
    def test_b7_sponsored_link_als_werbung_getrennt(self):
        _, body = read(REISE)
        joined = norm(body)
        self.assertIn('/go/mietwagen/', body)
        self.assertTrue(re.search(r'(verbraucherzentrale [^.]{0,60}empfiehlt[^.]{0,60}weder'
                                  r'|empfehlung der verbraucherzentrale[^.]{0,60}nicht)', joined),
                        'Die Abgrenzung Werbelink vs. Verbraucherzentrale fehlt (Befund 7).')
        self.assertNotIn('vollständige marktü', joined)
        self.assertNotIn('bestpreisgarantie', joined)
        # Kein Satz über Portale darf ohne Verneinung Vollständigkeit,
        # Bestpreis oder „garantiert“ behaupten (Befunde 4 + 7 invariabel).
        for sent in sentences(body):
            if re.search(r'(portal|mietwagen[- ]?vergleich|vergleichsportal|check24)', sent):
                if re.search(r'(alle|jeden) anbieter|bestpreis|garantiert|vollständig', sent):
                    self.assertTrue(re.search(r'(nicht|keine?|weder)', sent),
                                    f'Portal-Überlegenheit ohne Dämpfung: {sent!r}')

    # --- B8: Digitale Vertragstransparenz als Trend 2026 -------------------
    def test_b8_zeitgebundener_trend_enthoben(self):
        _, body = read(REISE)
        for sent in sentences(body):
            if 'trend' in sent and '2026' in sent:
                self.assertTrue('kein' in sent or 'nicht' in sent,
                                f'Trend-Jahresbehauptung zurück: {sent!r}')
        self.assertTrue(re.search(r'frist', norm(body)),
                        'Praktische Fristenübersicht muss den Trend-Ersatz bilden.')

    # --- B9: Pauschale Cashback-Rate 2 % ------------------------------------
    def test_b9_keine_cashback_rate_und_korrekte_rechnik(self):
        _, body = read(REISE)
        joined = norm(body)
        self.assertFalse(re.search(r'(?<!\d)2 ?(prozent|%)', joined),
                         'Eine pauschale 2-%-Cashback-Rate wurde wieder eingeführt.')
        self.assertNotIn('620', joined, 'Die alte Hochrechnung über 620 € ist zurück.')
        self.assertEqual(Decimal(1800) - Decimal(600), Decimal(1200))
        self.assertEqual((Decimal(1800) - Decimal(600)) / 10, Decimal('120'))
        self.assertEqual(Decimal(120) + 12 * Decimal(25) + Decimal(80), Decimal(500))
        for need in (r'120 (euro|€)', r'500 (euro|€)', r'150 euro statt 300 euro',
                     r'frei gewählte annahmen'):
            self.assertTrue(re.search(need, joined), f'Budget-Anker „{need}“ fehlt.')


class Faktenfrische763MetaTests(unittest.TestCase):
    """Metadaten, Geometrie und Gates – damit der Fix nicht wegfaulen kann."""

    def test_metadaten_dauerhaft_korrekt(self):
        for slug in (HEIZ, REISE):
            with self.subTest(slug=slug):
                fm, body = read(slug)
                self.assertGreaterEqual(fm['lastmod'], KORRIGIERT_AM,
                                        'lastmod muss den tatsächlichen Texteingriff dokumentieren.')
                # Untergrenze: seit der #763-Korrektur muss ein Prüfstamp stehen.
                # Die Obergrenze ist kein Testthema: faktenfrische.py selbst setzt
                # den Stamp nur nach echten Recherchelaufen (und rührt lastmod
                # nie an); ein harter Deckel würde legitime Folgeprüfungen
                # entwerten und den Test-Deckel zum Papier machen.
                self.assertGreaterEqual(fm['faktencheck'], KORRIGIERT_AM)
                self.assertIn('Oktober 2026', body, 'Sichtbare redaktionelle Einordnung fehlt.')
                self.assertNotRegex(body, r'1\.\s*Januar 2024|2024-01-01',
                                    'Erfundenes Publikationsdatum der Bundesnetzagentur zurück.')
                for q in fm['quellen']:
                    self.assertNotIn('datum', {k.lower() for k in q},
                                     'Quellen-Publikationsdaten dürfen nicht erfunden werden.')
                self.assertTrue(fm['kurzantwort'])
                self.assertTrue(70 <= len(fm['description']) <= 165,
                                'description muss in den SEO-Korridor (70–165 Zeichen).')
                self.assertFalse(re.search(r':\s*[^:|]*:', fm['description']),
                                 'Doppel-Doppelpunkt-Muster in der description (Maschinen-Klebe).')
                geo = faktenfrische.geo_reife(dict(
                    body=body, kurzantwort=fm['kurzantwort'],
                    quellen_vorhanden=bool(fm['quellen']), faktencheck=fm['faktencheck']))
                self.assertEqual(geo['prozent'], 100, f'GEO-Kriterien offen: {geo["offen"]}')
                self.assertIn('kein fachlicher beleg', norm(body))

    @staticmethod
    def _zahl(text):
        """Letzte Zahl einer Zelle, deutsche Schreibweise, als Decimal."""
        m = re.findall(r'\d{1,3}(?:\.\d{3})+,\d+|\d{1,3}(?:\.\d{3})+|\d+,\d+|\d+', text)
        assert m, f'keine Zahl in Zelle: {text!r}'
        return Decimal(m[-1].replace('.', '').replace(',', '.'))

    def _folge_aus_zellen(self, zelle):
        """„15 watt mal 24 stunden mal 365 tage durch 1.000“ → 131.4 als Decimal.

        Rechnet deutsche Rechenzellen der Modellrechnungs-Tabelle nach, damit
        Zahlenwerte an die Rechnung gebunden bleiben – nicht an eine
        Einzelzeichenkette (umformungssicher, Fälschung sicher).
        """
        wert = None
        op = None
        for token in re.findall(r'([\d.,]+|mal|durch)', zelle.lower().replace('.', '')):
            if token == 'mal':
                op = 'mal'; continue
            if token == 'durch':
                op = 'durch'; continue
            z = Decimal(token.replace(',', '.'))
            if wert is None:
                wert = z
            elif op == 'mal':
                wert *= z
            elif op == 'durch':
                wert /= z
            else:
                self.fail(f'Zelle ohne Operator: {zelle!r}')
        return wert

    def test_tabellenarithmetik_der_modellrechnungen(self):
        """Jede Ergebnis-Zeile der Modellrechnungs-Tabelle muss aus ihrer
        Rechen-Zelle folgen. Wer die 131,4 auf 1.314 kWh verrutscht, macht
        hier rot – unabhängig davon, ob die Zahl auch im Fließtext steht."""
        _, body = read(HEIZ)
        zeilen = re.findall(r'^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$',
                            body, re.M)
        paare = {norm(a): (b, c) for a, b, c in zeilen if norm(a) not in ('schritt der rechnung',)}
        verbrauch = paare.get('verbrauch im jahr')
        self.assertIsNotNone(verbrauch, 'Verbrauchszeile fehlt')
        self.assertEqual(self._folge_aus_zellen(verbrauch[0]), self._zahl(verbrauch[1]),
                         'Verbrauchs-Zeile rechnet nicht auf')
        kosten = paare.get('kosten im jahr bei 0,30 euro pro kwh')
        self.assertIsNotNone(kosten, 'Kostenzeile fehlt')
        kwh_zeile = self._zahl(verbrauch[1])
        self.assertEqual(kwh_zeile * self._zahl(kosten[0]), self._zahl(kosten[1]),
                         'Kosten-Zeile rechnet nicht auf (131,4 × 0,30 = 39,42)')
        _, rbody = read(REISE)
        # Nachschärfung 24.10.2026: Die Euro-/Dash-Heiler verteilen schmale
        # Leerzeichen (U+202F/U+00A0) vor dem € – harmlose Typografie, an der
        # die Summenformel nicht brechen darf (Bedeutung vor Schreibweise).
        rbody = rbody.translate({0x202F: ' ', 0x00A0: ' '})
        m = re.search(r'\|\s*\*\*summe\*\*\s*\|\s*\*\*([^*]+)\*\*\s*\|\s*\*\*(\d+) ?(?:€|euro)\*\*',
                      rbody, re.IGNORECASE)
        self.assertIsNotNone(m, 'Summenzeile der Reise-Modellrechnung fehlt')
        summanden = re.findall(r'(\d+)(?: ?(?:€|euro))? ?(?:\+|×|\*)? ?(\d+)?', m.group(1))
        teile = [Decimal(x) for x in re.findall(r'\d+', m.group(1))]
        # 120 + 12 × 25 + 80: „12 × 25“ als Multiplikation auflösen
        self.assertEqual(teile, [120, 12, 25, 80], 'Summenformel unverändert erwartet')
        self.assertEqual(Decimal(120) + 12 * Decimal(25) + Decimal(80), self._zahl(m.group(2)),
                         'Reise-Summenzelle rechnet nicht auf')
        del summanden

    def test_heiz_rechnik_einheiten_unabhaengig_vom_wortlaut(self):
        _, body = read(HEIZ)
        kwh = Decimal(3 * 5 * 24 * 365) / 1000
        self.assertEqual(kwh, Decimal('131.4'))  # Faktor-10-Fehler darf nicht zurück
        self.assertEqual(kwh * Decimal('0.30'), Decimal('39.420'))
        joined = norm(body)
        self.assertIn('131,4', joined)
        self.assertIn('39,42', joined)
        self.assertIn('13,14', joined)
        self.assertIn('105', joined)
        self.assertTrue(re.search(r'nur bei gleichem grundpreis|'
                                  r'wenn der grundpreis gleich bleibt', joined))
        # Strom-Modell: 3500·0,30=1050; 3500·0,27=945; Differenz = 10 % der Verbrauchskosten
        self.assertEqual(Decimal('3500') * Decimal('0.30'), Decimal('1050.00'))
        self.assertEqual(Decimal('3500') * (Decimal('0.30') - Decimal('0.27')), Decimal('105.00'))
        self.assertEqual((Decimal(105) / Decimal(1050) * 100), Decimal('10'))
        # Gas-Modell: 12000·0,09=1080; 12000·0,08=960; Differenz 120 − 60 Grundpreis = 60
        self.assertEqual(Decimal('12000') * (Decimal('0.09') - Decimal('0.08')), Decimal('120.00'))
        self.assertEqual(Decimal(120) - Decimal(60), Decimal(60))

    def test_sicherheitshinweise_bleiben_stehen(self):
        joined = norm(read(HEIZ)[1])
        self.assertIn('legionellen', joined)
        self.assertTrue(re.search(r'(brenner|gas)[^.]{0,140}(profis|fachkundige|fachbetrieb'
                                  r'|nie selbst|nicht selbst)', joined),
                        'Fachzuständigkeit an Brenner/Gas fehlt – kein Heimwerker-Tipp!')
        self.assertTrue(re.search(r'keine vorgabe von einem amt', joined),
                        'Die Klarstellung „kein behördlicher Grenzwert“ fehlt (Befund 2).')
        reise = norm(read(REISE)[1])
        self.assertTrue(re.search(r'kündige keine lebensversicherung', reise),
                        'Lebensversicherungs-Schutzsatz fehlt (Nachlesung 15.10.).')
        self.assertTrue(re.search(r'schutz[^.]{0,80}(verloren|nachteil)|'
                                  r'nachteile[^.]{0,60}(entstehen|möglich)', reise))

    def test_publish_gates_fuer_beide_entwuerfe_gruen(self):
        """Gate-Parität: Ein #763-Fix, der am Lesbarkeits- oder Längen-Gate
        scheitert, wird von der Kadenz gehalten – der Artikel verrottet im
        Hold. Deshalb prüfen wir genau hier mit (keine Netzzugriffe)."""
        sys.path.insert(0, str(ROOT / 'scripts'))
        import readability_check as rc
        import length_policy as lp
        from textverstaendnis_guard import (
            split_body, load_terminologie, check_article, frontmatter_keywords)
        try:
            from publish_gate import HARTE_REGELN
        except Exception:  # pragma: no cover - Fallback, falls Refactor
            HARTE_REGELN = {'R2-KEYWORD-DUMP', 'R3-TERMINOLOGIE', 'R5-ABSATZ-HART',
                            'R7-INTRO-FORMEL', 'R8-URL-LEERZEICHEN', 'R8-NESTED-LINK',
                            'R9-KLEBEWORT', 'R10-DOPPELWORT', 'R11-JAHRESZAHL-SPLIT',
                            'R12-ZAHL-RUINE', 'R13-DATUM-PUNKT', 'R14-MARKER-RUINE',
                            'R15-PHRASEN-DOPPEL', 'R17-KEYWORD-KASUS', 'R17-KEYWORD-DOPPEL'}
        floor, ceiling = lp.POSTS['target_min_chars'], lp.POSTS['fat_chars']
        term = load_terminologie()
        for slug in (HEIZ, REISE):
            with self.subTest(slug=slug):
                path = resolve(slug) / 'index.md'
                raw = path.read_text(encoding='utf-8')
                res = rc.analyze(rc.parse_article(raw, slug))
                self.assertGreaterEqual(res['score'], 75, f"Score: {res['issues']}")
                self.assertGreaterEqual(res['flesch'], rc.NEW_FLESCH_MIN,
                                        f"Flesch {res['flesch']} < {rc.NEW_FLESCH_MIN}")
                _, chars = lp.measure(raw)
                self.assertTrue(floor <= chars <= ceiling,
                                f'{chars} Zeichen außerhalb Korridor {floor}–{ceiling}')
                finds = [f for f in check_article(str(path), split_body(raw), term,
                                                  frontmatter_keywords(raw))
                         if f[1] in HARTE_REGELN]
                self.assertFalse(finds, f'Harte Textverständnis-Regeln: {finds}')

    def test_faktenfrische_queue_haelt_befunde_geschlossen(self):
        """Der offene-Queue-Eintrag darf die zwei Slugs nicht mehr führen.
        Ein neuer Lauf, der dieselben Fehler zurückmeldet, macht hier rot."""
        queue = json_load(ROOT / 'data' / 'faktenfrische_queue.json')
        for eintrag in queue.get('offen', []):
            self.assertNotIn(eintrag.get('slug'), (HEIZ, REISE),
                             f'Queue meldet offene Befunde für {eintrag.get("slug")}')

    def test_systemprompt_trennt_modell_tatsache_und_werbung(self):
        prompt = faktenfrische.SYSTEM_PROMPT
        for rule in ('Modellannahmen sind keine Marktdaten',
                     'Fehlende Erwähnung ist kein Gegenbeweis',
                     'keine behördliche Empfehlung', 'Quellen-Publikationsdatum'):
            self.assertIn(rule, prompt)


def json_load(path):
    import json
    try:
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}


if __name__ == '__main__':
    unittest.main()
