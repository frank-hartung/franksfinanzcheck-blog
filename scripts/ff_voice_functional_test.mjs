/**
 * ff_voice_functional_test.mjs — Funktionstest Vorlesen + Kurzfassung (echte DOM)
 * ------------------------------------------------------------
 * Läuft gegen eine ECHTE DOM (jsdom) mit der unveränderten
 * static/premium/ff-voice.js, dem echten Seiten-Skelett (wie
 * layouts/single.html es rendert) und echtem Inhalt aus content/posts.
 *
 * Aufruf: node scripts/ff_voice_functional_test.mjs
 *         (jsdom liegt in tools/ff-voice-qa/node_modules)
 */

import { createRunner, loadPage, skeleton, mdToHtml, listArticles, sleep } from './ff_voice_qa_lib.mjs';

const t = createRunner('Funktionstest Vorlesen + Kurzfassung (echte DOM)');

/* ============================================================
   1 · Toolbar & Beschriftung
   ============================================================ */
t.group('1) Toolbar, Rollen und Beschriftung');
{
  const { win, doc } = loadPage(skeleton({
    title: 'Gaspreisgarantie im Test',
    kurzantwort: 'Eine Gaspreisgarantie fixiert den Arbeitspreis für 12 bis 24 Monate.',
    bodyHtml: mdToHtml('## Erster Abschnitt\n\nDas ist ein Testabsatz mit 650 € Ersparnis.\n'),
  }));
  const api = win.__ffVoice;

  t.ok('Engine initialisiert', !!api, 'win.__ffVoice fehlt');
  t.ok('Toolbar vorhanden', !!doc.getElementById('ff-voice-bar'));
  t.ok('Slot reserviert (kein Layout-Sprung)', !!doc.getElementById('ff-voice-slot'));
  t.ok('Vorlesen-Knopf vorhanden', !!doc.getElementById('ff-voice-play'));
  t.ok('Kurzfassung-Knopf vorhanden', !!doc.getElementById('ff-voice-summary'));
  t.ok('Status ist eine Live-Region',
    doc.getElementById('ff-voice-status').getAttribute('aria-live') === 'polite');
  t.ok('Toolbar ist eine Region',
    doc.getElementById('ff-voice-bar').getAttribute('role') === 'region');
  t.ok('Fortschritt vorhanden', !!doc.getElementById('ff-voice-progress'));
  t.eq('Startbeschriftung DE', doc.getElementById('ff-voice-play-label').textContent, 'Vorlesen');
  t.eq('Kurzfassung DE', doc.getElementById('ff-voice-summary-label').textContent, 'Kurzfassung');
  t.ok('Ohne Tonspur läuft die Browser-Engine', api.mode === 'speech', 'mode=' + api.mode);
}

/* ============================================================
   2 · Lesereihenfolge (Vertrag mit dem Generator)
   ============================================================ */
t.group('2) Lesereihenfolge: Anmoderation → Vorab-Box → DOM → Abmoderation');
{
  const { win } = loadPage(skeleton({
    title: 'Heizkosten senken',
    kurzantwort: 'Mit einem Wechsel sparst du bis zu 650 € pro Jahr.',
    korrektur: 'Hinweis der Redaktion: Zahlen wurden am 02.01.2006 geprüft.',
    bodyHtml: mdToHtml([
      '## Warum wechseln',
      '',
      'Der Arbeitspreis liegt bei 12 ct/kWh.',
      '',
      '### Die drei Preisbestandteile',
      '',
      '- Arbeitspreis',
      '- Grundpreis',
      '',
      '> Ein Zitat aus der Branche.',
      '',
      '**Merksatz: Prüfe die Laufzeit genau.**',
    ].join('\n')),
  }));
  const blocks = win.__ffVoice.collectBlocks();
  const types = blocks.map((b) => b.type);
  const all = blocks.map((b) => b.text).join(' ');

  t.ok('Anmoderation an Position 1', types[0] === 'intro', 'erste Rolle: ' + types[0]);
  t.ok('Anmoderation nennt den Titel', /Heizkosten senken/.test(blocks[0].text));
  t.ok('Anmoderation nennt die Hördauer', /Hördauer/.test(blocks[0].text));
  t.ok('Abmoderation am Ende', types[types.length - 1] === 'outro');
  t.ok('Korrektur-Box wird gelesen', types.indexOf('warning') > 0);
  t.ok('Kurzantwort-Box wird gelesen', types.indexOf('callout') > 0);
  t.ok('Überschrift dabei', types.indexOf('h2') > 0);
  t.ok('Listenpunkte dabei', types.filter((x) => x === 'li').length === 2);
  t.ok('Zitat dabei', types.indexOf('blockquote') > 0);
  t.ok('Fettdruck dabei', types.indexOf('emphasis') > 0);
  t.ok('Kurzantwort-Cue gesetzt', /Kurzantwort:/.test(all));
  t.ok('Korrektur-Cue gesetzt', /Korrekturhinweis:/.test(all));
  t.ok('Überschrift endet mit Punkt', /Warum wechseln\./.test(all));
  t.ok('Dachzeile „Kurz & knapp“ wird nicht mitgesprochen',
    !/Kurz & knapp/.test(all), 'Dachzeile steht im Text');

  // Fettdruck genau einmal (kein Doppelt durch den umschließenden Absatz)
  const merksatz = blocks.filter((b) => /Merksatz/.test(b.text));
  t.eq('Fettdruck-Merksatz genau einmal', merksatz.length, 1);
}

/* ============================================================
   2b · Doppel-Lese-Schleuse: Pillar-Übersicht (Befund 05.09.2026)
   ------------------------------------------------------------
   Auf /pillar/strom-sparen/#das-wichtigste-auf-einen-blick
   erklang hinter „… 800 € pro Jahr“ erneut „Tarifwechsel als
   größter Hebel.“ — der Fettdruck-Lead-in wurde als zweiter
   Block gesprochen, weil die Knotenzahl-Regel in
   isStandaloneEmphasis() auf Textknoten hereinfiel. Diese
   Gruppe pinnt die Reparatur: Lead-in genau EINMAL, echte
   Merksätze weiterhin an ihrer Stelle.
   ============================================================ */
t.group('2b) Doppel-Lese-Schleuse: Fettdruck-Lead-ins einmal, Merksätze an ihrer Stelle');
{
  const pillar = mdToHtml(`### Das Wichtigste auf einen Blick

* **Tarifwechsel als größter Hebel:** Ein Wechsel des Strom- oder Gasanbieters dauert online weniger als zehn Minuten und spart im Schnitt 300&nbsp;€ bis 800&nbsp;€ pro Jahr.
* **Heimliche Stromfresser eliminieren:** Standby-Geräte, veraltete Kühltechnik und Dauerverbraucher verursachen bis zu 20&nbsp;% deiner jährlichen Stromrechnung.
* **Preisgarantien sichern:** Für Planungssicherheit sorgen Tarife mit einer Preisgarantie von mindestens zwölf Monaten.
* **Unterbrechungsfreie Versorgung:** Ein Versorgungsengpass beim Anbieterwechsel ist gesetzlich ausgeschlossen.

**Februar.** Jahresabrechnung lesen. Verbrauch, Preis, Abschlag.

👉 **Jetzt aktuellen Stromtarif prüfen und sparen:** [**→ Jetzt Stromtarife vergleichen**](/go/strom/)

**Merksatz: Prüfe die Laufzeit genau.**
`);
  const { win } = loadPage(skeleton({ title: 'Strom & Gas sparen', bodyHtml: pillar }), {});
  const api = win.__ffVoice;
  const blocks = api.collectBlocks();
  const full = blocks.map((b) => b.text).join('\n');

  t.eq('„Tarifwechsel als größter Hebel“ genau einmal',
    blocks.filter((b) => b.text.includes('Tarifwechsel als größter Hebel')).length, 1);
  t.eq('„Heimliche Stromfresser eliminieren“ genau einmal',
    blocks.filter((b) => b.text.includes('Heimliche Stromfresser eliminieren')).length, 1);
  t.eq('„Preisgarantien sichern“ genau einmal',
    blocks.filter((b) => b.text.includes('Preisgarantien sichern')).length, 1);
  t.eq('„Unterbrechungsfreie Versorgung“ genau einmal',
    blocks.filter((b) => b.text.includes('Unterbrechungsfreie Versorgung')).length, 1);
  t.eq('Absatz-Kurzdatum „Februar“ genau einmal',
    blocks.filter((b) => b.text.includes('Februar')).length, 1);
  t.eq('CTA-Linktext genau einmal (Absatz liest ihn, kein Zweiblock)',
    blocks.filter((b) => b.text.includes('Jetzt Stromtarife vergleichen')).length, 1,
    blocks.filter((b) => b.text.includes('Jetzt Stromtarife vergleichen')).map((b) => b.type + ':' + b.text).join(' | '));
  t.ok('Kein Lead-in erklingt als eigener Merksatz-Zweiblock',
    blocks.every((b) => b.type !== 'emphasis'
      || !/Tarifwechsel|Stromfresser eliminieren|Preisgarantien|Unterbrechungsfreie|Februar/.test(b.text)),
    blocks.filter((b) => b.type === 'emphasis').map((b) => b.text).join(' | '));
  t.eq('Echter Merksatz bleibt eigener Block',
    blocks.filter((b) => b.type === 'emphasis' && b.text.includes('Prüfe die Laufzeit genau')).length, 1);
  t.eq('Merksatz-Absatz wird nicht ZUSÄTZLICH gelesen',
    blocks.filter((b) => b.type !== 'emphasis' && b.text.includes('Prüfe die Laufzeit genau')).length, 0);
  t.ok('Keine doppelten Blocktexte',
    new Set(blocks.map((b) => b.text)).size === blocks.length);
  t.ok('Der vollständige Listensatz bleibt erhalten',
    /Tarifwechsel als größter Hebel: Ein Wechsel des Strom- oder Gasanbieters/.test(full));
}

/* ============================================================
   3 · Tabellen & Übersichten
   ============================================================ */
t.group('3) Tabellen, Summen und Premium-Übersichten');
{
  const { win } = loadPage(skeleton({
    title: 'Tarife im Vergleich',
    bodyHtml: [
      '<div class="ff-tarifvergleich">',
      '<h3 class="ff-tv-title">Tarife im Vergleich</h3>',
      '<p class="ff-tv-sub">Stand 02.01.2006</p>',
      '<div class="ff-tv-tablewrap"><table>',
      '<thead><tr><th>Tarif</th><th>Preis</th><th>Laufzeit</th></tr></thead>',
      '<tbody>',
      '<tr><td>Basis</td><td>1.200 €</td><td>12 Monate</td></tr>',
      '<tr><td>Komfort</td><td>980 €</td><td colspan="2">24 Monate</td></tr>',
      '</tbody>',
      '<tfoot><tr><td>Summe</td><td>2.180 €</td><td></td></tr></tfoot>',
      '</table></div>',
      '<div class="ff-tv-cards"><p>Dieselbe Tabelle als Kartenstapel</p></div>',
      '<div class="ff-tv-footnote"><strong>Hinweis:</strong> Alle Angaben ohne Gewähr.</div>',
      '</div>',
    ].join('\n'),
  }));
  const blocks = win.__ffVoice.collectBlocks();
  const types = blocks.map((b) => b.type);
  const all = blocks.map((b) => b.text).join(' ');

  t.ok('Übersichtstitel wird angesagt', types.indexOf('overview-title') > 0);
  t.ok('Unterzeile/Fußnote wird gelesen', types.indexOf('overview-note') >= 2);
  t.ok('Tabellen-Anmoderation', types.indexOf('table-intro') > 0);
  t.ok('Spalten werden benannt', /Die Spalten lauten: Tarif, Preis, Laufzeit/.test(all));
  t.eq('Zwei Datenzeilen', types.filter((x) => x === 'table-row').length, 2);
  t.eq('Eine Summenzeile', types.filter((x) => x === 'table-sum').length, 1);
  t.ok('Summenzeile spricht „Zusammengerechnet“', /Zusammengerechnet: Preis: 2\.180/.test(all));
  t.ok('Summenwort fällt nicht doppelt', !/Zusammengerechnet: Tarif: Summe/.test(all));
  t.ok('Tabellen-Ende wird angesagt', /Ende der Tabelle Tarife im Vergleich/.test(all));
  t.ok('Zeilen sind durchnummeriert', /Zeile 1 von 2/.test(all) && /Zeile 2 von 2/.test(all));
  t.ok('Kopfzeilen-Werte gepaart', /Tarif: Basis, Preis: 1\.200/.test(all));
  t.ok('Kartenstapel bleibt stumm (kein Doppelt)',
    !/Kartenstapel/.test(all), 'Mobil-Variante wurde mitgesprochen');
  t.ok('colspan-Zelle spricht genau einmal',
    (all.match(/Laufzeit: 24 Monate/g) || []).length === 1);
  t.ok('colspan-Zeile ohne Geisterspalte', !/: ,/.test(all) && !/Spalte 4/.test(all));
}

/* ============================================================
   3b · Tabellen-Härtfälle: ARIA, Spannen, CTA, Titel, small
   ============================================================ */
t.group('3b) Tabellen vollständig: Zeilen, Spalten, ARIA, Werbelinks');
{
  const { win } = loadPage(skeleton({
    title: 'Tabellen-Härtfälle',
    bodyHtml: [
      '<h2 id="kosten">Kosten im Überblick</h2>',
      // Markdown-Tabelle wie aus render-table.html (Wrapper mit region-Rolle)
      '<div class="ff-table-scroll" role="region" aria-label="Tabelle">',
      '<table class="ff-tbl">',
      '<thead><tr><th scope="col">Posten</th><th scope="col">Betrag</th></tr></thead>',
      '<tbody><tr><td>Grundpreis</td><td>120 €</td></tr></tbody>',
      '</table></div>',
      // ARIA-Tabelle ohne <tr>
      '<div role="table" aria-label="Beispielhaushalt">',
      '<div role="rowgroup"><div role="row"><span role="columnheader">Posten</span><span role="columnheader">Kosten</span></div></div>',
      '<div role="rowgroup">',
      '<div role="row"><span role="rowheader">Miete</span><span role="gridcell">900 €</span></div>',
      '<div role="row"><span role="rowheader">Strom</span><span role="gridcell">120 €</span></div>',
      '</div></div>',
      // colspan/rowspan + mehrzeiliger Kopf
      '<table><thead>',
      '<tr><th colspan="2">Energie</th><th>Wasser</th></tr>',
      '<tr><th>Strom</th><th>Gas</th><th>Trinkwasser</th></tr>',
      '</thead><tbody>',
      '<tr><td rowspan="2">32 ct/kWh</td><td>12 ct/kWh</td><td>2 €</td></tr>',
      '<tr><td>14 ct/kWh</td><td>3 €</td></tr>',
      '</tbody></table>',
      // Premium-Einspartabelle: Emoji, small, Summe im tbody, Werbelink-Zeile
      '<div class="ff-einspar">',
      '<div class="ff-es-head"><h3 class="ff-es-title">💰 Einsparpotenziale</h3></div>',
      '<div class="ff-es-tablewrap"><table>',
      '<thead><tr><th>Maßnahme</th><th>❌ Vorher<br><small>Alter Verbraucher</small></th><th>🏆 Ersparnis</th></tr></thead>',
      '<tbody>',
      '<tr><td>Pumpe tauschen</td><td><strong>890 €</strong></td><td><strong>770 €</strong></td></tr>',
      '<tr class="ff-es-sum"><td><strong>Gesamt</strong></td><td><strong>1.500 €</strong></td><td><strong>900 €</strong></td></tr>',
      '<tr><td></td><td><small>teuer</small></td><td><a class="ff-es-btn" href="/go/strom/">Stromanbieter vergleichen →</a></td></tr>',
      '</tbody></table></div>',
      '</div>',
    ].join('\n'),
  }));
  const blocks = win.__ffVoice.collectBlocks();
  const types = blocks.map((b) => b.type);
  const all = blocks.map((b) => b.text).join(' ');

  t.ok('Markdown-Tabelle bekommt Titel der Überschrift davor',
    /Tabelle: Kosten im Überblick/.test(all));
  t.ok('Markdown-Tabelle: Zeile vollständig mit allen Spalten',
    /Zeile 1 von 1\. Posten: Grundpreis, Betrag: 120 €/.test(all));
  t.ok('ARIA-Tabelle wird erkannt', /Tabelle: Beispielhaushalt/.test(all));
  t.eq('ARIA-Tabelle: beide Zeilen gesprochen',
    types.filter((x) => x === 'table-row').length >= 4 && /Kosten: 900 €/.test(all)
      && /Kosten: 120 €/.test(all), true);
  t.ok('ARIA-Tabelle: Zeilentitel (rowheader) wird Zeilenname',
    blocks.some((b) => b.type === 'table-row' && /: Miete\./.test(b.text)));
  t.ok('colspan-Gruppierung wird angesagt', /Kopfzeile 1: Energie, Wasser/.test(all));
  t.ok('unterste Kopfzeile trägt die Spaltennamen',
    /Die Spalten lauten: Strom, Gas, Trinkwasser/.test(all));
  t.eq('rowspan-Wert spricht in beiden Zeilen',
    (all.match(/Strom: 32 ct\/kWh/g) || []).length, 2);
  t.ok('leere Tabellenzelle erzeugt keine Lücke', !/: ,/.test(all));
  t.ok('Emoji und Pfeile dringen nicht in Tabellen-Blöcke',
    !/💰|🏆|❌|→/.test(blocks.filter((b) => /^table-/.test(b.type)).map((b) => b.text).join(' ')));
  t.ok('small-Ziertext mit Komma angebunden', /Vorher, Alter Verbraucher/.test(all));
  t.ok('Summenzeile im tbody wird Zusammengerechnet',
    /Zusammengerechnet: Vorher, Alter Verbraucher: 1\.500 €, Ersparnis: 900 €/.test(all));
  t.eq('Werbelink-Zeile wird Empfehlung statt Datenzeile',
    types.filter((x) => x === 'table-cta').length, 1);
  t.ok('Werbelink wird als Partnerlink offengelegt',
    /Empfehlung: Stromanbieter vergleichen\. Hinweis: Dies ist ein Partnerlink/.test(all));
  t.ok('keine Datenzeile spricht den Werbelink als Wert',
    !/Ersparnis: Stromanbieter vergleichen/.test(all));
  t.ok('Anmoderation zählt nur echte Datenzeilen',
    /Übersicht mit 3 Spalten und 2 Zeilen/.test(all));
}

/* ============================================================
   3c · Innentabellen & leere Tabellen
   ============================================================ */
t.group('3c) Innentabellen einmal, leere Tabellen stumm');
{
  const { win } = loadPage(skeleton({
    title: 'Sonderfälle',
    bodyHtml: [
      '<h2 id="aussen">Außentabelle</h2>',
      '<table>',
      '<thead><tr><th>Plan</th><th>Details</th></tr></thead>',
      '<tbody><tr><td>Tarif A</td><td><table><tbody><tr><td>innen eins</td><td>innen zwei</td></tr></tbody></table></td></tr></tbody>',
      '</table>',
      '<table><tbody><tr><td></td><td></td></tr></tbody></table>',
    ].join('\n'),
  }));
  const blocks = win.__ffVoice.collectBlocks();
  const types = blocks.map((b) => b.type);
  const all = blocks.map((b) => b.text).join(' ');

  t.eq('Nur die Außentabelle wird angesagt (Innentabelle als Zelleninhalt)',
    types.filter((x) => x === 'table-intro').length, 1);
  t.eq('Innentabelle spricht genau einmal',
    (all.match(/innen eins/g) || []).length, 1);
  t.ok('Innentabelle mit hörbarem Abstand der Blöcke',
    /Details: innen eins innen zwei/.test(all));
  t.ok('Außentabelle zählt zwei Spalten (keine Geisterspalten)',
    /Übersicht mit 2 Spalten und einer Zeile/.test(all));
  t.ok('Außentabelle bekommt Titel der Überschrift davor',
    /Tabelle: Außentabelle/.test(all));
  t.ok('Leere Tabelle bleibt stumm', !/Übersichtstabelle/.test(all));
}

/* ============================================================
   4 · Aussprache-Regie DE
   ============================================================ */
t.group('4) Aussprache-Regie Deutsch (Zahlen, Währung, Datum, Einheiten)');
{
  const { win } = loadPage(skeleton({ title: 'Test', bodyHtml: '<p>x</p>' }));
  const n = (text) => win.__ffVoice.speechNormalize(text, 'de');

  t.eq('Euro-Zeichen', n('bis zu 650 €'), 'bis zu 650 Euro');
  t.eq('Prozent', n('rund 3,5 %'), 'rund 3,5 Prozent');
  t.eq('Prozent ohne Leerzeichen', n('rund 30%'), 'rund 30 Prozent');
  t.eq('Paragraph', n('§ 12 EnWG'), 'Paragraph 12 EnWG');
  t.eq('Zahlenbereich mit Gedankenstrich', n('12 – 24 Monate'), '12 bis 24 Monate');
  t.eq('Zahlenbereich mit Bindestrich', n('12-24 Monate'), '12 bis 24 Monate');
  t.eq('Kilowattstunden', n('20.000 kWh'), '20.000 Kilowattstunden');
  t.eq('Cent pro kWh', n('12 ct/kWh'), '12 Cent pro Kilowattstunde');
  t.eq('Quadratmeter', n('80 m²'), '80 Quadratmeter');
  t.eq('Millionen', n('1,5 Mio. €'), '1,5 Millionen Euro');
  t.eq('Datum', n('Stand 02.01.2006'), 'Stand 2. Januar 2006');
  t.eq('Uhrzeit', n('um 14:30 Uhr'), 'um 14 Uhr 30');
  t.eq('Uhrzeit glatt', n('um 14:00 Uhr'), 'um 14 Uhr');
  t.eq('z. B.', n('z. B. Strom'), 'zum Beispiel Strom');
  t.eq('bzw.', n('Strom bzw. Gas'), 'Strom beziehungsweise Gas');
  t.eq('ca.', n('ca. 400 Euro'), 'circa 400 Euro');
  t.eq('Und-Zeichen', n('Strom & Gas'), 'Strom und Gas');
  t.eq('Tausender ohne Silbentrennung', n('20 000 kWh'), '20.000 Kilowattstunden');
  t.ok('Dezimalzahl bleibt erhalten', /1\.234,56/.test(n('1.234,56 Euro')));
  t.ok('Domain wird buchstabiert', /Punkt/.test(n('siehe franksfinanzcheck.de')));
}

/* ============================================================
   5 · Aussprache-Regie EN
   ============================================================ */
t.group('5) Aussprache-Regie Englisch');
{
  const { win } = loadPage(skeleton({ title: 'Test', lang: 'en', bodyHtml: '<p>x</p>' }));
  const n = (text) => win.__ffVoice.speechNormalize(text, 'en');

  t.eq('Dollar', n('Save $1,200'), 'Save 1,200 dollars');
  t.eq('Prozent', n('about 20%'), 'about 20 percent');
  t.eq('e. g.', n('e. g. gas'), 'for example gas');
  t.eq('etc.', n('tariffs etc.'), 'tariffs and so on');
  t.eq('Kilowattstunden', n('20,000 kWh'), '20,000 kilowatt hours');
  t.eq('Datum (MM/TT)', n('on 02/01/2006'), 'on 1. February 2006');
  t.eq('Und-Zeichen', n('gas and oil'.replace('and', '&')), 'gas and oil');
}

/* ============================================================
   6 · Zweisprachigkeit ohne Umschalter
   ============================================================ */
t.group('6) Deutsch & Englisch vollautomatisch (kein Umschalter)');
{
  const deBody = mdToHtml('## Strom sparen\n\nMit einem Wechsel sparst du jedes Jahr mehrere hundert Euro bei den Kosten.');
  const enBody = mdToHtml('## Save Money on Electricity\n\nSwitching your tariff can save you several hundred pounds every year on your energy costs and comparison shows it.');

  const de = loadPage(skeleton({ title: 'Strom sparen', bodyHtml: deBody }));
  const en = loadPage(skeleton({ title: 'Save Money on Electricity', lang: 'en', bodyHtml: enBody }));

  t.eq('Deutscher Artikel → de', de.win.__ffVoice.lang, 'de');
  t.eq('Englischer Artikel → en', en.win.__ffVoice.lang, 'en');
  t.eq('EN-Beschriftung Vorlesen', en.doc.getElementById('ff-voice-play-label').textContent, 'Listen');
  t.eq('EN-Beschriftung Kurzfassung', en.doc.getElementById('ff-voice-summary-label').textContent, 'Summary');
  t.ok('EN-Blöcke sind englisch',
    en.win.__ffVoice.collectBlocks().every((b) => b.lang === 'en'));

  // Satzweises Routing: englischer Satz im deutschen Artikel
  const mixed = loadPage(skeleton({
    title: 'Tarifwechsel leicht gemacht',
    bodyHtml: '<h2>Was du beachten solltest</h2>'
      + '<p>Der Wechsel ist einfach. This sentence is clearly written in English and should be read by the English voice.</p>',
  }));
  const blocks = mixed.win.__ffVoice.collectBlocks();
  const units = mixed.win.__ffVoice.buildTimeline().units;
  const langs = new Set(units.map((u) => u.lang));
  t.ok('Blöcke vorhanden', blocks.length > 2);
  t.ok('Beide Sprachen im Sprechplan', langs.has('de'), 'de fehlt');
  t.ok('Englischer Satz bekommt die EN-Stimme', langs.has('en'), 'en fehlt');
}

/* ============================================================
   7 · Männliche Stimme (Garantie-Kern)
   ============================================================ */
t.group('7) Männliche Stimme – deterministisch, DE und EN');
{
  const { win } = loadPage(skeleton({ title: 'Test', bodyHtml: '<p>x</p>' }));
  const api = win.__ffVoice;
  const de = api.resolveMaleVoice('de');
  const en = api.resolveMaleVoice('en');

  t.ok('DE: eine Stimme gefunden', !!de.voice, 'keine Stimme');
  t.ok('EN: eine Stimme gefunden', !!en.voice, 'keine Stimme');
  t.ok('DE: männlich erkannt', de.male === true, 'Stimme: ' + (de.voice && de.voice.name));
  t.ok('EN: männlich erkannt', en.male === true, 'Stimme: ' + (en.voice && en.voice.name));
  t.ok('DE: keine Frauenstimme',
    !/anna|katja|hedda|marlene|vicki|elke|amala|clara|julia/i.test(de.voice.name));
  t.ok('EN: keine Frauenstimme',
    !/aria|samantha|karen|moira|tessa|fiona|serena|allison|ava|susan/i.test(en.voice.name));
  t.ok('DE: Neural-/Studio-Qualität bevorzugt',
    /natural|neural|premium|enhanced/i.test(de.voice.name), de.voice.name);
  t.ok('EN: Neural-/Studio-Qualität bevorzugt',
    /natural|neural|premium|enhanced/i.test(en.voice.name), en.voice.name);
  t.ok('DE: Locale passt', (de.voice.lang || '').toLowerCase().indexOf('de') === 0);
  t.ok('EN: Locale passt', (en.voice.lang || '').toLowerCase().indexOf('en') === 0);
}

t.group('7b) Keine männliche Stimme im Katalog – ehrlicher Notnagel');
{
  const { win } = loadPage(skeleton({ title: 'Test', bodyHtml: '<p>x</p>' }), {
    voices: [
      { name: 'Anna', lang: 'de-DE' },
      { name: 'Samantha', lang: 'en-US' },
    ],
  });
  const api = win.__ffVoice;
  const de = api.resolveMaleVoice('de');
  t.ok('Es wird trotzdem eine Stimme geliefert', !!de.voice);
  t.eq('Notnagel ist als nicht-männlich gekennzeichnet', de.male, false);
  t.ok('Notnagel wird in die männliche Klangzone abgesenkt',
    de.tier && de.tier.pitchZone < 0, 'pitchZone=' + (de.tier && de.tier.pitchZone));
}

/* ============================================================
   8 · Atemgruppen & Sprechplan
   ============================================================ */
t.group('8) Atemgruppen, Tempo und harte Chunk-Grenze');
{
  const long = 'Und ' + 'weil der Arbeitspreis in diesem Tarif über die gesamte Laufzeit konstant bleibt, '.repeat(8);
  const { win } = loadPage(skeleton({ title: 'Langtext', bodyHtml: `<p>${long}</p>` }));
  const api = win.__ffVoice;
  const pieces = api.splitForSpeech(long, 'de');

  t.ok('Langer Satz wird geteilt', pieces.length >= 3, 'Teile: ' + pieces.length);
  t.ok('Harte Grenze eingehalten (Chrome-Abbruch)',
    pieces.every((p) => p.text.length <= 220), 'max=' + Math.max(...pieces.map((p) => p.text.length)));
  t.ok('Sinnzusammenhang erhalten (kein Wort abgeschnitten)',
    pieces.every((p) => /^[\w„"(ÄÖÜäöü]/.test(p.text) && /[\w.,!?:;%€)]$/.test(p.text)));

  const plan = api.buildTimeline();
  t.ok('Sprechplan gefüllt', plan.units.length > 0);
  t.ok('Jede Einheit hat Tempo', plan.units.every((u) => u.effRate > 0.5 && u.effRate <= 1.3));
  t.ok('Jede Einheit hat Tonlage', plan.units.every((u) => u.effPitch > 0.5 && u.effPitch < 1.5));
  t.ok('Jede Einheit hat Lautstärke', plan.units.every((u) => u.effVolume > 0.4 && u.effVolume <= 1));
  t.ok('Überschrift ruhiger als Fließtext',
    plan.units.filter((u) => u.type === 'h2').every((u) => u.profile.rate < 1));
  t.ok('Pause zwischen Blöcken gesetzt',
    plan.units.some((u) => u.before > 0) && plan.units.some((u) => u.after > 0));
}

/* ============================================================
   9 · Wiedergabe, Pause, Fortsetzen, Sprung
   ============================================================ */
t.group('9) Wiedergabe: Start, Pause, Fortsetzen, Abschnittssprung');
{
  const { win, doc } = loadPage(skeleton({
    title: 'Wiedergabe-Test',
    kurzantwort: 'Kurz und knapp.',
    readingTime: 1,
    bodyHtml: mdToHtml('## Eins\n\nErster Absatz mit genug Text für eine eigene Sprecheinheit.\n\n## Zwei\n\nZweiter Absatz mit ebenfalls genug Text.\n\n## Drei\n\nDritter Absatz, wiederum lang genug.\n'),
  }));
  const api = win.__ffVoice;

  doc.getElementById('ff-voice-play').click();
  t.ok('Lesen gestartet', api.reading === true);
  t.ok('Status gemeldet', /gestartet|Stimme/.test(doc.getElementById('ff-voice-status').textContent));
  t.eq('Knopf zeigt Pausieren', doc.getElementById('ff-voice-play-label').textContent, 'Pausieren');
  t.ok('data-state=playing', doc.getElementById('ff-voice-bar').getAttribute('data-state') === 'playing');
  await sleep(120);
  t.ok('Erste Einheit gesprochen', api.units.length > 0);

  const before = doc.getElementById('ff-voice-progress').style.width;
  doc.getElementById('ff-voice-play').click();     // Pause
  t.ok('Pause gesetzt', api.playing === false);
  t.eq('Knopf zeigt Weiterlesen', doc.getElementById('ff-voice-play-label').textContent, 'Weiterlesen');
  t.ok('Status „pausiert“', /pausiert/.test(doc.getElementById('ff-voice-status').textContent));
  t.ok('Fortschritt bleibt stehen', doc.getElementById('ff-voice-progress').style.width === before);

  doc.getElementById('ff-voice-play').click();     // Fortsetzen
  t.ok('Fortgesetzt', api.playing === true);
  await sleep(120);

  doc.getElementById('ff-voice-next').click();
  await sleep(60);
  t.ok('Weitersprung ohne Abbruch', api.reading === true);
  doc.getElementById('ff-voice-prev').click();
  await sleep(60);
  t.ok('Rücksprung ohne Abbruch', api.reading === true);

  doc.getElementById('ff-voice-stop').click();
  t.ok('Beenden setzt zurück', api.reading === false);
  t.eq('Knopf zeigt wieder Vorlesen', doc.getElementById('ff-voice-play-label').textContent, 'Vorlesen');
  t.ok('data-state=idle', doc.getElementById('ff-voice-bar').getAttribute('data-state') === 'idle');
}

/* ============================================================
   10 · Tonspur (ZEIT-Standard) und Fallback
   ============================================================ */
t.group('10) Studio-Tonspur wird bevorzugt – Fallback greift nie ins Leere');
{
  const track = {
    src: '/audio/articles/test.mp3',
    version: '2026.09.05-a',
    voice: { de: 'de-DE-FlorianMultilingualNeural', en: 'en-US-AndrewMultilingualNeural' },
    duration: 60000,
    chunks: [
      { b: 0, t0: 0, t1: 3000, lang: 'de' },
      { b: 1, t0: 3200, t1: 8000, lang: 'de' },
      { b: 2, t0: 8200, t1: 20000, lang: 'de' },
      { b: 3, t0: 20400, t1: 60000, lang: 'de' },
    ],
  };
  const { win, doc } = loadPage(skeleton({
    title: 'Tonspur-Test',
    kurzantwort: 'Kurz und knapp.',
    bodyHtml: mdToHtml('## Eins\n\nAbsatz eins.\n\n## Zwei\n\nAbsatz zwei.\n'),
    track,
  }));
  const api = win.__ffVoice;
  t.ok('Tonspur erkannt', api.trackReady === true);
  t.eq('Modus ist Tonspur', api.mode, 'track');

  doc.getElementById('ff-voice-play').click();
  t.ok('Tonspur startet', api.reading === true);
  t.ok('Status nennt die Tonspur', /Tonspur/.test(doc.getElementById('ff-voice-status').textContent));
  doc.getElementById('ff-voice-stop').click();
  t.ok('Stoppen möglich', api.reading === false);

  // Tonspur kaputt → Browser-Engine übernimmt, nie Stille
  const audio = doc.querySelector('audio');
  if (audio) {
    api.start();
    Object.defineProperty(audio, 'error', { value: { code: 4 }, configurable: true });
    audio.dispatchEvent(new win.Event('error'));
    await sleep(30);
    t.ok('Defekte Tonspur fällt auf die Browser-Engine zurück',
      api.mode === 'speech' || api.reading === false, 'mode=' + api.mode);
    api.stop();
  } else {
    t.ok('Defekte Tonspur fällt zurück (Audio-Element vorhanden)', false, 'kein <audio> erzeugt');
  }
}

/* ============================================================
   11 · Kurzfassung
   ============================================================ */
t.group('11) Kurzfassung: Aufbau, Barrierefreiheit, Kopieren');
{
  const { win, doc } = loadPage(skeleton({
    title: 'Heizkosten senken 2026',
    kurzantwort: 'Ein Tarifwechsel spart bis zu 650 € pro Jahr.',
    readingTime: 7,
    wordCount: 1450,
    author: 'Frank Hartung',
    date: '10.08.2026',
    updated: '02.09.2026',
    bodyHtml: mdToHtml([
      '## Warum jetzt wechseln',
      '',
      'Die Beschaffungspreise schwanken saisonal stark, deshalb lohnt der Vergleich jedes Jahr aufs Neue für Haushalte.',
      '',
      '## So findest du den besten Tarif',
      '',
      'Vergleiche Arbeitspreis, Grundpreis und Laufzeit – nur zusammen ergeben sie die echte Ersparnis von 650 €.',
      '',
      '## Checkliste',
      '',
      'Prüfe Kündigungsfrist, Preisgarantie und Bonusbedingungen, bevor du den Vertrag unterschreibst.',
      '',
      '| Tarif | Preis |',
      '| --- | --- |',
      '| Basis | 1.200 € |',
      '| Komfort | 980 € |',
    ].join('\n')),
  }));
  const api = win.__ffVoice;

  doc.getElementById('ff-voice-summary').click();
  const dlg = doc.getElementById('ff-voice-dialog');
  t.ok('Dialog erzeugt', !!dlg);
  t.ok('Rolle dialog', dlg.getAttribute('role') === 'dialog');
  t.ok('aria-modal gesetzt', dlg.getAttribute('aria-modal') === 'true');
  t.ok('Dialog beschriftet', !!dlg.getAttribute('aria-label'));
  t.ok('Scroll-Sperre aktiv', doc.body.style.overflow === 'hidden');
  t.ok('Fokus im Dialog', dlg.contains(doc.activeElement));
  t.ok('Kurzantwort sichtbar', /650 €/.test(dlg.textContent));
  t.ok('Byline: Lesezeit', /7 Min/.test(dlg.textContent));
  t.ok('Byline: Wörter', /1\.?450/.test(dlg.textContent.replace(/\u00a0/g, ' ')));
  t.ok('Byline: Autor', /Frank Hartung/.test(dlg.textContent));
  t.ok('Byline: Stand', /10\.08\.2026/.test(dlg.textContent));
  t.ok('Byline: Aktualisiert', /02\.09\.2026/.test(dlg.textContent));
  t.ok('Kernaussagen gefüllt', dlg.querySelectorAll('.ff-voice-list--plain li').length >= 2);
  t.ok('Zahlen-Karten gefüllt', dlg.querySelectorAll('.ff-voice-figure').length >= 1);
  t.ok('Tabellen im Fokus', dlg.querySelectorAll('.ff-voice-tablecard').length >= 1);
  // Mini-Vorschau: Kopfzeile + Datenzeilen, für Screenreader verborgen
  const preview = dlg.querySelector('.ff-voice-tablecard__preview');
  t.ok('Tabellen-Vorschau gerendert', !!preview);
  if (preview) {
    t.ok('Vorschau trägt Kopfzeile', preview.querySelectorAll('thead th').length >= 2);
    t.ok('Vorschau trägt Datenzeilen', preview.querySelectorAll('tbody tr').length >= 1);
    t.ok('Vorschau ist für Vorlesemodell verborgen (kein Doppelt)',
      preview.getAttribute('aria-hidden') === 'true');
  }
  t.ok('Inhaltsverzeichnis gefüllt', dlg.querySelectorAll('.ff-voice-toc a').length >= 3);

  // Kopieren
  let copied = null;
  win.__ff_voice_copied = (text) => { copied = text; };
  doc.getElementById('ff-voice-copy').click();
  t.ok('Klartext-Kurzfassung kopiert', typeof copied === 'string' && copied.length > 40);
  t.ok('Kopie enthält den Titel', /Heizkosten senken/.test(copied || ''));
  t.ok('Kopie enthält Kernaussagen', /Kernaussagen/.test(copied || ''));
  t.ok('Kopie enthält die Tabelle', /Tarif/.test(copied || '') && /Komfort/.test(copied || ''));
  t.ok('Kopie ist reiner Text (kein HTML)', !/</.test(copied || ''));

  // Fokus-Falle & Schließen
  doc.getElementById('ff-voice-dialog').querySelector('.ff-voice-dialog__close').click();
  t.ok('Dialog geschlossen', !dlg.open);
  t.ok('Scroll-Sperre aufgehoben', doc.body.style.overflow === '');
}

/* ============================================================
   12 · Robuste Verarbeitung aller echten Artikel
   ============================================================ */
t.group('12) Alle echten Artikel – kein Absturz, vollständige Ausbeute');
{
  const articles = listArticles();
  t.ok('Artikel gefunden', articles.length > 0, 'gefunden: ' + articles.length);

  let crashed = 0;
  let empty = 0;
  let totalBlocks = 0;
  let totalUnits = 0;
  let female = 0;
  let tooLong = 0;
  const failures = [];

  for (const article of articles) {
    try {
      const { win, doc } = loadPage(skeleton({
        title: article.data.title || article.slug,
        description: article.data.description || '',
        kurzantwort: article.data.kurzantwort || article.data.description || '',
        readingTime: parseInt(article.data.readingTime || '5', 10) || 5,
        wordCount: 1200,
        author: article.data.author || 'Frank Hartung',
        date: article.data.date ? String(article.data.date).slice(0, 10) : '05.09.2026',
        slug: article.slug,
        bodyHtml: mdToHtml(article.body),
      }));
      const api = win.__ffVoice;
      const blocks = api.collectBlocks();
      if (!blocks.length) { empty += 1; failures.push(article.slug + ' (keine Blöcke)'); }
      totalBlocks += blocks.length;
      const plan = api.buildTimeline();
      totalUnits += plan.units.length;
      if (plan.units.some((u) => u.text.length > 220)) {
        tooLong += 1;
        failures.push(article.slug + ' (Chunk > 220)');
      }
      const de = api.resolveMaleVoice('de');
      const en = api.resolveMaleVoice('en');
      if (de.voice && /anna|katja|hedda|marlene|vicki|elke/i.test(de.voice.name)) female += 1;
      if (en.voice && /aria|samantha|karen|moira/i.test(en.voice.name)) female += 1;
      // Kurzfassung muss auf jeder Seite funktionieren
      doc.getElementById('ff-voice-summary').click();
      if (!doc.getElementById('ff-voice-dialog')) { failures.push(article.slug + ' (Dialog fehlt)'); }
    } catch (e) {
      crashed += 1;
      failures.push(article.slug + ' (' + e.message + ')');
    }
  }

  t.eq('Kein Artikel stürzt ab', crashed, 0, failures.slice(0, 4).join(' | '));
  t.eq('Kein Artikel bleibt stumm', empty, 0, failures.slice(0, 4).join(' | '));
  t.eq('Keine Frauenstimme gewählt', female, 0);
  t.eq('Keine Einheit über der Chrome-Grenze', tooLong, 0, failures.slice(0, 4).join(' | '));
  t.ok('Blöcke insgesamt', totalBlocks > articles.length * 5, 'Blöcke: ' + totalBlocks);
  t.ok('Sprecheinheiten insgesamt', totalUnits > articles.length * 5, 'Einheiten: ' + totalUnits);
  console.log(`    · ${articles.length} Artikel → ${totalBlocks} Blöcke, ${totalUnits} Sprecheinheiten`);
}

t.done();
