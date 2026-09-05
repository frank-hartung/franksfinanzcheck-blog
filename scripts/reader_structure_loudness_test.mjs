#!/usr/bin/env node
/**
 * reader_structure_loudness_test.mjs — Dauerwache für die v10-Stufe:
 *   1. VOLLSTÄNDIGKEIT: Überschriften (h2–h6), Teil-Überschriften,
 *      Tabellen und Übersichten (Tarifvergleich/Einspartabelle inkl.
 *      Kopfzeile, Unterzeile und Fußnote) werden vollständig gesprochen.
 *   2. KEINE DOPPELUNG: Die mobile Kartenansicht der Übersichten
 *      (.ff-tv-cards / .ff-es-cards) enthält denselben Inhalt wie die
 *      Tabelle und darf NICHT zusätzlich gelesen werden.
 *   3. AUTOMATISCHE LAUTSTÄRKENANPASSUNG: kein Pegelsprung zwischen
 *      benachbarten Einheiten, nichts unhörbar, nichts übersteuert –
 *      in Deutsch UND Englisch, ohne Umschalter.
 *
 * Diese Datei prüft die ECHTE static/premium/ff-reader.js in echter DOM
 * (jsdom) über den echten Klickpfad – keine nachgebaute Logik.
 *
 * Start: node scripts/reader_structure_loudness_test.mjs
 * Voraussetzung (einmalig): (cd tools/reader-qa && npm ci)
 */

import { createRunner, createPage, buildPage, VOICE_CATALOGS, until } from './reader_qa_lib.mjs';

const t = createRunner('Struktur- & Lautheits-Test (Vorlesen v10)');

/* Ein Artikel mit allen kritischen Bauteilen: Gliederung bis h6,
   eine Markdown-Tabelle, eine Tarif-Übersicht und eine Einspartabelle
   (jeweils mit Desktop-Tabelle UND mobiler Kartenansicht). */
const BODY = `
<p class="ff-lead">Lead-Absatz mit der Einordnung des Themas.</p>
<h2>Kosten im Überblick</h2>
<p>Ein normaler Absatz mit Inhalt.</p>
<h3>Teilüberschrift zweiter Ebene</h3>
<h4>Teilüberschrift dritter Ebene</h4>
<h5>Teilüberschrift vierter Ebene</h5>
<h6>Teilüberschrift fünfter Ebene</h6>
<p>Text unter den Teilüberschriften.</p>

<div class="ff-tarifvergleich">
  <div class="ff-tv-head">
    <h3 class="ff-tv-title">Stromtarife im Vergleich</h3>
    <p class="ff-tv-sub">Drei Anbieter für einen Haushalt mit 3500 Kilowattstunden</p>
  </div>
  <div class="ff-tv-tablewrap"><table class="ff-tv-table">
    <thead><tr><th class="ff-tv-corner">Merkmal</th><th class="ff-tv-col">Anbieter Nord</th><th class="ff-tv-col">Anbieter Süd</th></tr></thead>
    <tbody>
      <tr><td class="ff-tv-corner">Grundpreis</td><td>29 Euro</td><td>35 Euro</td></tr>
      <tr><td class="ff-tv-corner">Bonus</td><td>120 Euro</td><td>80 Euro</td></tr>
      <tr><td class="ff-tv-corner"></td><td class="ff-tv-cta"><a class="ff-tv-btn" href="/go/strom/">Jetzt vergleichen</a></td><td class="ff-tv-cta"><a class="ff-tv-btn" href="/go/strom/">Jetzt vergleichen</a></td></tr>
    </tbody>
  </table></div>
  <div class="ff-tv-cards">
    <div class="ff-tv-card"><div class="ff-tv-card-head"><h4 class="ff-tv-card-name">Anbieter Nord Kartenansicht</h4></div>
      <div class="ff-tv-card-grid"><div class="ff-tv-card-item"><div class="ff-tv-card-label">Grundpreis</div><div class="ff-tv-card-value">29 Euro</div></div></div>
    </div>
  </div>
  <div class="ff-tv-footnote"><strong>Hinweis:</strong> Alle Preise gelten für das erste Vertragsjahr.</div>
</div>

<div class="ff-einspar">
  <div class="ff-es-head"><h3 class="ff-es-title">Einsparpotenziale im Haushalt</h3></div>
  <div class="ff-es-tablewrap"><table class="ff-es-table">
    <thead><tr><th>Maßnahme</th><th>Vorher<br><small>Alter Verbrauch</small></th><th>Nachher</th><th>Ersparnis</th></tr></thead>
    <tbody>
      <tr><td>Strom</td><td>1200 Euro<br><small>pro Jahr</small></td><td>900 Euro</td><td>300 Euro</td></tr>
      <tr><td>Gas</td><td>1400 Euro</td><td>1100 Euro</td><td>300 Euro</td></tr>
      <tr class="ff-es-sum"><td><strong>Summe</strong></td><td>2600 Euro</td><td>2000 Euro</td><td>600 Euro</td></tr>
    </tbody>
  </table></div>
  <div class="ff-es-cards"><div class="ff-es-card"><h4 class="ff-es-card-label">Strom</h4><div class="ff-es-card-sum">300 Euro</div></div></div>
  <div class="ff-es-footnote"><strong>Hinweis:</strong> Werte beruhen auf einem Musterhaushalt.</div>
</div>

<h2>Fazit für dich</h2>
<p>Abschließender Absatz.</p>
`;

async function speakAll({ lang = 'de', catalog = VOICE_CATALOGS.macChrome, bodyHtml = BODY, title = 'Strom sparen im Haushalt' } = {}) {
  const html = buildPage({
    title, description: 'Testartikel', kurzantwort: 'Vergleiche die Anbieter.',
    readingTime: 6, wordCount: 900, lang, bodyHtml
  });
  const page = await createPage({ html, catalog });
  const { win, doc } = page;
  const btn = doc.getElementById('ff-listen-btn');
  win.__speechEngine.__userGestureActive = true;
  btn.dispatchEvent(new win.MouseEvent('click', { bubbles: true, cancelable: true, view: win }));
  win.__speechEngine.__userGestureActive = false;
  await until(() => win.__speechLog.length > 3, 4000);
  // Auslaufen lassen, bis nichts Neues mehr dazukommt (Artikel zu Ende).
  let last = -1;
  for (let i = 0; i < 60 && last !== win.__speechLog.length; i++) {
    last = win.__speechLog.length;
    await new Promise((r) => setTimeout(r, 120));
  }
  return { win, doc, log: win.__speechLog };
}

const norm = (s) => String(s || '').toLowerCase().replace(/\s+/g, ' ').trim();
const joined = (log) => norm(log.map((u) => u.text).join(' '));
const count = (hay, needle) => (hay.match(new RegExp(needle.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;

/* ================================================================== */
t.group('1) Vollständigkeit: Überschriften & Teil-Überschriften');
const de = await speakAll();
const deText = joined(de.log);

t.ok(de.log.length > 10, 'Der Artikel wird in mehreren Einheiten gesprochen', `nur ${de.log.length}`);
t.ok(deText.includes('kosten im überblick'), 'h2 wird vorgelesen');
t.ok(deText.includes('teilüberschrift zweiter ebene'), 'h3 (Teil-Überschrift) wird vorgelesen');
t.ok(deText.includes('teilüberschrift dritter ebene'), 'h4 (Teil-Überschrift) wird vorgelesen');
t.ok(deText.includes('teilüberschrift vierter ebene'), 'h5 (Teil-Überschrift) wird vorgelesen');
t.ok(deText.includes('teilüberschrift fünfter ebene'), 'h6 (Teil-Überschrift) wird vorgelesen');
t.ok(deText.includes('fazit für dich'), 'Abschließende h2 wird vorgelesen');

/* ================================================================== */
t.group('2) Vollständigkeit: Tabellen');
t.ok(deText.includes('29 euro') && deText.includes('35 euro'), 'Tabellenwerte der Tarifübersicht werden gesprochen');
t.ok(deText.includes('120 euro') && deText.includes('80 euro'), 'Zweite Tabellenzeile wird gesprochen');
t.ok(deText.includes('grundpreis') && deText.includes('bonus'), 'Zeilenbeschriftungen werden gesprochen');
t.ok(deText.includes('anbieter nord') && deText.includes('anbieter süd'), 'Spaltenköpfe werden zugeordnet');
t.ok(deText.includes('1200 euro pro jahr'),
  'Zeilenumbruch in einer Zelle trennt Wörter („1200 Euro pro Jahr“, nicht „Europro“)',
  deText.slice(deText.indexOf('1200') - 20, deText.indexOf('1200') + 60));
t.ok(!/europro|eurpro/.test(deText), 'Keine verschmolzenen Wörter durch <br>');
t.ok(deText.includes('vorher alter verbrauch'), 'Mehrzeiliger Tabellenkopf wird sauber gelesen');

/* ================================================================== */
t.group('3) Vollständigkeit: Übersichten (Kopf, Unterzeile, Fußnote, Summe)');
t.ok(deText.includes('stromtarife im vergleich'), 'Titel der Tarif-Übersicht wird vorgelesen');
t.ok(deText.includes('drei anbieter für einen haushalt'), 'Unterzeile der Übersicht wird vorgelesen');
t.ok(deText.includes('alle preise gelten für das erste vertragsjahr'), 'Fußnote der Tarif-Übersicht wird vorgelesen');
t.ok(deText.includes('einsparpotenziale im haushalt'), 'Titel der Einspartabelle wird vorgelesen');
t.ok(deText.includes('werte beruhen auf einem musterhaushalt'), 'Fußnote der Einspartabelle wird vorgelesen');
t.ok(deText.includes('zusammengerechnet'), 'Summenzeile wird als Summe angekündigt');
t.ok(deText.includes('600 euro'), 'Summenwert wird gesprochen');

// Die Tabelle trägt jetzt ihren echten Namen statt „Übersichtstabelle“.
t.ok(deText.includes('tabelle: stromtarife im vergleich'),
  'Tabelle wird mit ihrem echten Titel angekündigt');
t.ok(deText.includes('tabelle: einsparpotenziale im haushalt'),
  'Einspartabelle wird mit ihrem echten Titel angekündigt');

/* ================================================================== */
t.group('4) Keine Doppelung durch die mobile Kartenansicht');
/* Der Kartenstapel trägt hier eine eindeutige Kennung. Taucht sie im
   Sprechtext auf, wurde derselbe Inhalt doppelt vorgelesen. Die Spalten-
   und Zeilennamen der TABELLE dürfen dagegen mehrfach vorkommen – die
   Zuordnung „Spaltenname: Wert“ je Zeile ist barrierefrei gewollt. */
t.ok(!deText.includes('kartenansicht'),
  'Mobile Kartenansicht wird nicht zusätzlich zur Tabelle vorgelesen',
  deText.includes('kartenansicht') ? 'Kartenstapel wurde mitgelesen' : '');
t.ok(count(deText, 'anbieter nord') === 3,
  'Spaltenzuordnung bleibt vollständig (Kopfzeile + je Datenzeile)',
  `„anbieter nord“ ${count(deText, 'anbieter nord')}× (erwartet 3: 1 Kopf + 2 Zeilen)`);
t.ok(count(deText, '29 euro') === 1,
  'Jeder Tabellenwert wird genau einmal gesprochen',
  `„29 euro“ ${count(deText, '29 euro')}×`);
t.ok(count(deText, '300 euro') === 2,
  'Einsparwerte werden nicht durch die Kartenansicht verdoppelt',
  `„300 euro“ ${count(deText, '300 euro')}× (erwartet 2: Strom + Gas)`);
t.ok(!/jetzt vergleichen/.test(deText),
  'Reine Button-Zeile („Jetzt vergleichen“) wird nicht als Tabellenzeile vorgelesen');
t.ok(!/zeile 3 von 3/.test(deText),
  'Die entfernte Button-Zeile verfälscht die Zeilenzählung nicht');

/* ================================================================== */
t.group('5) Sprachliche Sauberkeit der Ansagen');
t.ok(!/\b1 zeilen\b/.test(deText), 'Kein „1 Zeilen“ (Zahlwort-Kongruenz)');
t.ok(!/\b1 spalten\b/.test(deText), 'Kein „1 Spalten“ (Zahlwort-Kongruenz)');

/* ================================================================== */
t.group('6) Automatische Lautstärkenanpassung (Auto-Gain)');
const vols = de.log.map((u) => u.volume);
t.ok(vols.every((v) => typeof v === 'number' && v > 0 && v <= 1),
  'Jede Einheit hat einen gültigen Pegel (0 < v ≤ 1)');
t.ok(vols.every((v) => v >= 0.72),
  'Keine Einheit wird unhörbar leise (≥ 0.72)', `min=${Math.min(...vols)}`);
t.ok(vols.every((v) => v <= 1.0),
  'Keine Einheit übersteuert (≤ 1.0)', `max=${Math.max(...vols)}`);

// Der eigentliche Kern: keine hörbaren Lautstärkesprünge.
let maxStep = 0; let stepAt = '';
for (let i = 1; i < vols.length; i++) {
  const d = Math.abs(vols[i] - vols[i - 1]);
  if (d > maxStep) { maxStep = d; stepAt = `${de.log[i - 1].text.slice(0, 30)} → ${de.log[i].text.slice(0, 30)}`; }
}
t.ok(maxStep <= 0.061,
  'Kein hörbarer Lautstärkesprung zwischen benachbarten Einheiten (≤ 0.06)',
  `größter Sprung ${maxStep.toFixed(3)} bei: ${stepAt}`);

// Die Automatik muss tatsächlich regeln – nicht einfach alles auf 1.0 lassen.
t.ok(new Set(vols.map((v) => v.toFixed(3))).size > 3,
  'Die Automatik regelt tatsächlich (mehrere unterschiedliche Pegel)',
  JSON.stringify([...new Set(vols)].slice(0, 8)));

// Tabellenzeilen und Überschriften dürfen nicht auseinanderdriften.
const volOf = (needle) => {
  const u = de.log.find((x) => norm(x.text).includes(needle));
  return u ? u.volume : null;
};
const vHeading = volOf('kosten im überblick');
const vRow = volOf('grundpreis');
t.ok(vHeading != null && vRow != null && Math.abs(vHeading - vRow) <= 0.09,
  'Überschrift und Tabellenzeile sind ähnlich laut (kein Lautheitsloch)',
  `Überschrift ${vHeading} vs Tabellenzeile ${vRow}`);

/* ================================================================== */
t.group('7) Englisch ohne Umschalter: gleiche Regie, gleiche Lautheit');
const EN_BODY = `
<p class="ff-lead">This guide explains how much you can save every year.</p>
<h2>What the tariff costs</h2>
<h3>The details you should compare</h3>
<h5>A deeper heading level</h5>
<div class="ff-tarifvergleich">
  <div class="ff-tv-head"><h3 class="ff-tv-title">Electricity tariffs compared</h3>
  <p class="ff-tv-sub">Three providers for a household with 3500 kilowatt hours</p></div>
  <div class="ff-tv-tablewrap"><table class="ff-tv-table">
    <thead><tr><th>Feature</th><th>Provider North</th><th>Provider South</th></tr></thead>
    <tbody><tr><td>Base price</td><td>29 euros</td><td>35 euros</td></tr>
    <tr><td>Bonus</td><td>120 euros</td><td>80 euros</td></tr></tbody>
  </table></div>
  <div class="ff-tv-footnote">All prices apply to the first contract year.</div>
</div>
<p>The comparison shows lower fees for the first provider.</p>
`;
const en = await speakAll({ lang: 'en', bodyHtml: EN_BODY, title: 'How to compare electricity tariffs' });
const enText = joined(en.log);

t.ok(enText.includes('what the tariff costs'), 'EN: h2 wird vorgelesen');
t.ok(enText.includes('the details you should compare'), 'EN: h3 wird vorgelesen');
t.ok(enText.includes('a deeper heading level'), 'EN: h5 wird vorgelesen');
t.ok(enText.includes('electricity tariffs compared'), 'EN: Titel der Übersicht wird vorgelesen');
t.ok(enText.includes('three providers for a household'), 'EN: Unterzeile wird vorgelesen');
t.ok(enText.includes('all prices apply to the first contract year'), 'EN: Fußnote wird vorgelesen');
t.ok(enText.includes('29 euros') && enText.includes('35 euros'), 'EN: Tabellenwerte werden gesprochen');
t.ok(/table: electricity tariffs compared/.test(enText), 'EN: Tabelle wird mit echtem Titel angekündigt');
t.ok(!/\b1 rows\b/.test(enText), 'EN: Kein „1 rows“ (Zahlwort-Kongruenz)');

const enVols = en.log.map((u) => u.volume);
t.ok(enVols.every((v) => v >= 0.72 && v <= 1.0), 'EN: Pegel bleiben im gültigen Fenster');
let enMaxStep = 0;
for (let i = 1; i < enVols.length; i++) enMaxStep = Math.max(enMaxStep, Math.abs(enVols[i] - enVols[i - 1]));
t.ok(enMaxStep <= 0.061, 'EN: Kein hörbarer Lautstärkesprung', `größter Sprung ${enMaxStep.toFixed(3)}`);

// Beide Sprachen müssen im selben Lautheitsfenster liegen – sonst wird ein
// englischer Satz im deutschen Artikel hörbar leiser oder lauter.
const avg = (a) => a.reduce((x, y) => x + y, 0) / a.length;
t.ok(Math.abs(avg(vols) - avg(enVols)) <= 0.05,
  'DE und EN liegen im selben Lautheitsfenster (ohne Umschalter)',
  `DE ⌀${avg(vols).toFixed(3)} vs EN ⌀${avg(enVols).toFixed(3)}`);

/* ================================================================== */
t.group('8) Einfache Stimmen (Basic-Katalog) bleiben verständlich laut');
const basic = await speakAll({ catalog: VOICE_CATALOGS.androidChrome || VOICE_CATALOGS.macChrome });
const bVols = basic.log.map((u) => u.volume);
t.ok(bVols.every((v) => v >= 0.72 && v <= 1.0),
  'Auch mit einfachem Stimmenkatalog bleibt der Pegel im Fenster',
  `min=${Math.min(...bVols)} max=${Math.max(...bVols)}`);
t.ok(joined(basic.log).includes('teilüberschrift fünfter ebene'),
  'Auch mit einfachem Katalog werden alle Ebenen gelesen');

process.exit(t.report() ? 1 : 0);
