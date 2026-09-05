#!/usr/bin/env node
/**
 * reader_table_progress_test.mjs — Regressionsschutz für die drei
 * gemeldeten Kernfehler der Vorlese-Funktion (v11, 05.09.2026):
 *
 *   1. Fett gedruckter Text wurde nicht an seiner Stelle gesprochen.
 *      Ursache: Der Generator der Tonspur (scripts/generate_reader_audio.py)
 *      sammelte den direkten Text eines Elements VOR seinen Kind-Elementen.
 *      Aus „<strong>Tarifwechsel als größter Hebel:</strong> Ein Wechsel …"
 *      wurde „Ein Wechsel … Tarifwechsel als größter Hebel:".
 *
 *   2. Zeilen und Spalten von Tabellen wurden nicht zuverlässig erkannt
 *      (kein <thead>, <tfoot>, colspan, role="table", Links in Zellen).
 *
 *   3. Die Fortschrittsanzeige lief nicht korrekt (kein 100 %-Stand,
 *      Rücksprünge, Ticker erst ab onstart, Restzeit aus anderem Rechenweg).
 *
 * Zusätzlich wird die PARITÄT zwischen Tonspur (Python) und Browser-Reader
 * (JS) Block für Block geprüft – beide müssen denselben Text liefern.
 *
 * Start: node scripts/reader_table_progress_test.mjs
 * Voraussetzung (einmalig): (cd tools/reader-qa && npm ci)
 */

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import {
  ROOT, READER_JS, buildPage, createPage, markdownToHtml,
  VOICE_CATALOGS, until, createRunner
} from './reader_qa_lib.mjs';
import { renderShortcodes } from './hugo_shortcodes.mjs';

const t = createRunner('Tabellen-, Fettdruck- & Fortschritts-Test (Vorlesen v11)');

/* ------------------------------------------------------------------ */
/* Helfer                                                             */
/* ------------------------------------------------------------------ */

function click(win, el) {
  if (win.__speechEngine) win.__speechEngine.__userGestureActive = true;
  el.dispatchEvent(new win.MouseEvent('click', { bubbles: true, cancelable: true, view: win }));
  if (win.__speechEngine) win.__speechEngine.__userGestureActive = false;
}

const norm = (s) => String(s || '')
  .replace(/[\u00ad\u200b-\u200d\ufeff]/g, '')
  .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/gu, '')
  .replace(/\u00a0/g, ' ')
  .toLowerCase()
  .replace(/[^a-z0-9äöüß]+/g, ' ')
  .replace(/\s+/g, ' ')
  .trim();

const ratioOf = (style) => {
  const m = /scaleX\(([\d.]+)\)/.exec(style || '');
  return m ? parseFloat(m[1]) : 0;
};

/**
 * Blockliste der BROWSER-Seite: die echte collectBlocks() aus
 * static/premium/ff-reader.js, über einen RAM-Hook exportiert – dasselbe
 * Verfahren wie scripts/reader_parity_probe.js. Die Produktivdatei bleibt
 * unangetastet.
 */
async function jsBlocksFor(html, { title = 'Testartikel', lang = 'de', readingTime = '1' } = {}) {
  const page = buildPage({
    title, description: 'Testseite', kurzantwort: '',
    readingTime, wordCount: 400, lang, bodyHtml: html, showKurzantwortBox: false
  });
  const { win } = await createPage({ html: page, catalog: VOICE_CATALOGS.macChrome, speech: true });
  const src = fs.readFileSync(READER_JS, 'utf8');
  const closeIdx = src.lastIndexOf('})();');
  const hook = '\n;(typeof globalThis!==\'undefined\')&&(globalThis.__FF_BLOCKS='
    + 'function(){return collectBlocks().map(function(b){'
    + 'return {type:b.type,lang:b.lang,text:b.text};});});\n';
  win.eval(src.slice(0, closeIdx) + hook + src.slice(closeIdx));
  const blocks = win.__FF_BLOCKS();
  // Titel/Intro werden von buildPage gesetzt – für Vergleichbarkeit fixieren.
  return blocks.map((b) => (b.type === 'intro'
    ? { ...b, text: b.text.replace(/^[^.]*\./, `${title}.`) }
    : b));
}

/** Blockliste der TONSPUR (Python-Generator) über den Dump-Helfer. */
function pyBlocksFor(html, { title = 'Testartikel', lang = 'de', readingTime = '1' } = {}) {
  const page = buildPage({
    title, description: 'Testseite', kurzantwort: '',
    readingTime, wordCount: 400, lang, bodyHtml: html, showKurzantwortBox: false
  });
  const tmp = path.join(ROOT, 'tools', 'reader-qa', `.parity-${Date.now()}-${Math.random().toString(36).slice(2)}.html`);
  fs.writeFileSync(tmp, page, 'utf8');
  try {
    const out = execFileSync('python3', [
      path.join(ROOT, 'scripts', 'reader_blocks_dump.py'), tmp, title, lang, String(readingTime)
    ], { encoding: 'utf8', cwd: ROOT });
    return JSON.parse(out);
  } finally {
    try { fs.unlinkSync(tmp); } catch { /* bereits weg */ }
  }
}

/** Vollständiger Klickpfad: starten und bis zum Ende sprechen lassen. */
async function speakAll(html, opts = {}) {
  const page = buildPage({
    title: opts.title || 'Testartikel',
    description: 'Testseite für Vorlesen.',
    kurzantwort: '',
    readingTime: opts.readingTime || '3',
    wordCount: 600,
    lang: opts.lang || 'de',
    bodyHtml: html,
    showKurzantwortBox: false,
    audioCfg: opts.audioCfg || null
  });
  const env = await createPage({
    html: page,
    catalog: opts.catalog || VOICE_CATALOGS.macChrome,
    msPerChar: opts.msPerChar || 0.05,
    audioDuration: opts.audioDuration || 900
  });
  return env;
}

const spokenOf = (log) => log.map((u) => u.text).join(' ');

/* ================================================================== */
/* 1) Fett gedruckter Text an seiner Stelle                           */
/* ================================================================== */
t.group('1) Fettdruck & Inline-Reihenfolge');
{
  const fixture = `
<h2 id="blick">Das Wichtigste auf einen Blick</h2>
<ul>
  <li><strong>Tarifwechsel als größter Hebel:</strong> Ein Wechsel dauert online weniger als zehn Minuten und spart im Schnitt 300 € bis 800 € pro Jahr.</li>
  <li><strong>Heimliche Stromfresser eliminieren:</strong> Standby-Geräte verursachen bis zu 20 % deiner jährlichen Stromrechnung.</li>
</ul>
<p>💡 <strong>Schnell-Tipp von Frank:</strong> Lege dir für unter 15 € ein Strommessgerät zu.</p>
<ol>
  <li><strong>Zählerstand notieren:</strong> Nimm deine letzte Jahresabrechnung zur Hand.</li>
</ol>
<p>Details stehen im <a href="/ratgeber/">großen Ratgeber</a> und in der <em>Übersicht</em> unten.</p>
<table><thead><tr><th>Maßnahme</th><th>Ersparnis</th></tr></thead>
<tbody><tr><td><strong>Standby</strong> abschalten</td><td>90 €</td></tr></tbody></table>`;

  const env = await speakAll(fixture);
  click(env.win, env.doc.getElementById('ff-listen-btn'));
  await until(() => env.doc.getElementById('ff-listen-label').textContent.trim() === 'Vorlesen'
    && env.log.length > 5, 20000);
  const spoken = norm(spokenOf(env.log));

  t.ok(/tarifwechsel als größter hebel ein wechsel dauert/.test(spoken),
    'Fett gedruckte Einleitung wird VOR dem Satz gesprochen (Liste)',
    spoken.slice(0, 220));
  t.ok(/heimliche stromfresser eliminieren standby geräte/.test(spoken),
    'Fett gedruckte Einleitung wird VOR dem Satz gesprochen (2. Listenpunkt)');
  t.ok(/schnell tipp von frank lege dir für unter 15/.test(spoken),
    'Fett gedruckte Einleitung wird VOR dem Satz gesprochen (Absatz)');
  t.ok(/punkt 1 zählerstand notieren nimm deine letzte/.test(spoken),
    'Fett gedruckte Einleitung wird VOR dem Satz gesprochen (nummerierte Liste)');
  t.ok(/details stehen im großen ratgeber und in der übersicht unten/.test(spoken),
    'Links und <em> bleiben an ihrer Stelle im Satz');
  t.ok(/standby abschalten/.test(spoken),
    'Fettdruck in einer Tabellenzelle bleibt in der Zellreihenfolge');
  t.ok(!/ein wechsel dauert online weniger als zehn minuten[^.]*\. tarifwechsel/.test(spoken),
    'Kein Block endet mit einer nachgestellten Fetteinleitung');
  t.ok(!/nbsp|&amp|\bamp\b/.test(spoken),
    'Markup-Reste (Entities) werden nie gesprochen',
    (spoken.match(/.{0,40}nbsp.{0,40}/) || [''])[0]);
  t.eq(env.errors, [], 'Keine Laufzeitfehler in der Fettdruck-Fixture');
}

/* ================================================================== */
/* 1b) Entity-Reste bleiben Markup                                    */
/* ================================================================== */
t.group('1b) Entity-Reste werden nicht gesprochen');
{
  // Zweite Escape-Stufe, wie sie aus CMS-Importen und Shortcode-Ausgaben
  // kommt: Der Text enthält dann wörtlich „&nbsp;" statt eines Leerzeichens.
  const fixture = '<p>Das Gerät kostet 300&amp;nbsp;&amp;euro; im Jahr &amp;amp; spart 20&amp;nbsp;% Strom.</p>';
  const env = await speakAll(fixture);
  click(env.win, env.doc.getElementById('ff-listen-btn'));
  await until(() => env.doc.getElementById('ff-listen-label').textContent.trim() === 'Vorlesen'
    && env.log.length > 2, 20000);
  const spoken = norm(spokenOf(env.log));
  t.ok(!/nbsp/.test(spoken), '„&nbsp;" erklingt nicht als Wort', spoken.slice(0, 200));
  t.ok(!/ euro euro/.test(spoken), '„&euro;" wird nicht doppelt gesprochen', spoken.slice(0, 200));
}

/* ================================================================== */
/* 2) Tabellen: Zeilen- und Spaltenerkennung                          */
/* ================================================================== */
t.group('2) Tabellen: Zeilen- und Spaltenerkennung');

const TABLE_CASES = {
  thead_tbody: {
    html: `<table><thead><tr><th>Maßnahme</th><th>Ersparnis</th></tr></thead><tbody>
      <tr><td>Strom wechseln</td><td>300 €</td></tr><tr><td>Gas wechseln</td><td>400 €</td></tr></tbody></table>`,
    intro: /mit 2 Spalten und 2 Zeilen/,
    rows: 2,
    expect: [/Strom wechseln\. Zeile 1 von 2\. Ersparnis: 300/, /Gas wechseln\. Zeile 2 von 2\. Ersparnis: 400/]
  },
  ohne_thead: {
    html: `<div class="ff-table-scroll"><table>
      <tr><th>Anbieter</th><th>Preis</th><th>Bonus</th></tr>
      <tr><td>EON</td><td>32 ct</td><td>50 €</td></tr>
      <tr><td>Vattenfall</td><td>30 ct</td><td>80 €</td></tr></table></div>`,
    intro: /mit 3 Spalten und 2 Zeilen/,
    rows: 2,
    expect: [/EON\. Zeile 1 von 2\. Preis: 32/, /Vattenfall\. Zeile 2 von 2\. Preis: 30/],
    forbid: [/Anbieter\. Zeile 1 von/, /Preis: Preis/]
  },
  aria_grid: {
    html: `<div role="table" aria-label="Kostenübersicht">
      <div role="row"><div role="columnheader">Posten</div><div role="columnheader">Betrag</div></div>
      <div role="row"><div role="cell">Strom</div><div role="cell">120 €</div></div>
      <div role="row"><div role="cell">Gas</div><div role="cell">240 €</div></div></div>`,
    intro: /Kostenübersicht\. Übersicht mit 2 Spalten und 2 Zeilen/,
    rows: 2,
    expect: [/Strom\. Zeile 1 von 2\. Betrag: 120/, /Gas\. Zeile 2 von 2\. Betrag: 240/]
  },
  aria_grid_mit_rowgroup: {
    html: `<div role="table" aria-label="Raster mit Gruppe">
      <div role="rowgroup"><div role="row"><div role="columnheader">Tarif</div><div role="columnheader">Preis</div></div></div>
      <div role="rowgroup"><div role="row"><div role="cell">Öko</div><div role="cell">31 ct</div></div>
      <div role="row"><div role="cell">Basic</div><div role="cell">29 ct</div></div></div></div>`,
    intro: /mit 2 Spalten und 2 Zeilen/,
    rows: 2,
    expect: [/Öko\. Zeile 1 von 2\. Preis: 31/, /Basic\. Zeile 2 von 2\. Preis: 29/]
  },
  colspan_titelzeile: {
    html: `<table><thead><tr><th colspan="2">Vergleich 2026</th><th>Test</th></tr>
      <tr><th>Tarif</th><th>Preis</th><th>Note</th></tr></thead>
      <tbody><tr><td>Öko</td><td>31 ct</td><td>1,5</td></tr></tbody></table>`,
    intro: /mit 3 Spalten und einer Zeile/,
    rows: 1,
    expect: [/Öko\. Preis: 31 ct\. Note: 1,5/],
    forbid: [/Test: 31/, /Tarif: 1,5/, /Spalte 3/]
  },
  link_in_erster_zelle: {
    html: `<table><thead><tr><th>Tarif</th><th>Preis</th></tr></thead><tbody>
      <tr><td><a href="/go/strom/">Check24</a></td><td>29 ct</td></tr>
      <tr><td><a href="/go/gas/">Verivox</a></td><td>31 ct</td></tr></tbody></table>`,
    intro: /mit 2 Spalten und 2 Zeilen/,
    rows: 2,
    expect: [/Check24\. Zeile 1 von 2\. Preis: 29/, /Verivox\. Zeile 2 von 2\. Preis: 31/]
  },
  aktionszeile: {
    html: `<table><thead><tr><th>Tarif</th><th>Preis</th></tr></thead><tbody>
      <tr><td>Grundversorger</td><td>38 ct</td></tr>
      <tr><td colspan="2"><a class="ff-tv-btn" href="/go/">Jetzt vergleichen</a></td></tr></tbody></table>`,
    intro: /mit 2 Spalten und einer Zeile/,
    rows: 1,
    expect: [/Grundversorger\. Preis: 38/],
    forbid: [/Jetzt vergleichen/]
  },
  leere_zellen: {
    html: `<table><thead><tr><th>Gerät</th><th>Standby</th><th>Kosten</th></tr></thead><tbody>
      <tr><td>TV</td><td></td><td>12 €</td></tr><tr><td>Router</td><td>8 W</td><td></td></tr></tbody></table>`,
    intro: /mit 3 Spalten und 2 Zeilen/,
    rows: 2,
    expect: [/TV\. Zeile 1 von 2\. Kosten: 12/, /Router\. Zeile 2 von 2\. Standby: 8 W/]
  },
  tfoot_summe: {
    html: `<table><thead><tr><th>Posten</th><th>Betrag</th></tr></thead>
      <tbody><tr><td>Strom</td><td>120 €</td></tr></tbody>
      <tfoot><tr><td>Summe</td><td>360 €</td></tr></tfoot></table>`,
    intro: /mit 2 Spalten und 2 Zeilen/,
    // Die Summenzeile zählt als table-sum, nicht als table-row: Sie wird
    // angekündigt („Zusammengerechnet:") statt als „Zeile 2 von 2".
    rows: 1,
    sums: 1,
    expect: [/Strom\. Zeile 1 von 2\. Betrag: 120/, /Zusammengerechnet: 360 €/]
  },
  th_scope_row: {
    html: `<table><thead><tr><th>Jahr</th><th>Verbrauch</th></tr></thead><tbody>
      <tr><th scope="row">2024</th><td>3500 kWh</td></tr>
      <tr><th scope="row">2025</th><td>3200 kWh</td></tr></tbody></table>`,
    intro: /und 2 Zeilen/,
    rows: 2,
    expect: [/2024\. Zeile 1 von 2\. Verbrauch: 3500/, /2025\. Zeile 2 von 2\. Verbrauch: 3200/]
  },
  mehrere_tbody: {
    html: `<table><thead><tr><th>Gruppe</th><th>Wert</th></tr></thead>
      <tbody><tr><td>A</td><td>1</td></tr></tbody><tbody><tr><td>B</td><td>2</td></tr></tbody></table>`,
    intro: /und 2 Zeilen/,
    rows: 2,
    expect: [/A\. Zeile 1 von 2\. Wert: 1/, /B\. Zeile 2 von 2\. Wert: 2/]
  },
  einspar_uebersicht: {
    html: `<div class="ff-einspar"><div class="ff-es-head"><h3 class="ff-es-title">Einsparübersicht</h3></div>
      <div class="ff-es-tablewrap"><table class="ff-es-table"><thead><tr><th>Maßnahme</th><th>Ersparnis</th></tr></thead>
      <tbody><tr><td>Standby</td><td>90 €</td></tr><tr class="ff-es-sum"><td>Gesamt</td><td>450 €</td></tr></tbody></table></div>
      <div class="ff-es-footnote">Hinweis: Werte sind Durchschnittswerte.</div></div>`,
    intro: /Tabelle: Einsparübersicht\. Übersicht mit 2 Spalten und 2 Zeilen/,
    rows: 1,
    sums: 1,
    expect: [/Standby\. Zeile 1 von 2\. Ersparnis: 90/, /Zusammengerechnet: 450 €/]
  },
  titel_aus_ueberschrift: {
    html: `<h2 id="potenziale">Die Spar-Potenziale im Energie-Bereich</h2>
      <div class="ff-table-scroll"><table><thead><tr><th>Maßnahme</th><th>Ersparnis</th></tr></thead>
      <tbody><tr><td>LED</td><td>90 €</td></tr></tbody></table></div>`,
    intro: /Tabelle: Die Spar-Potenziale im Energie-Bereich\./,
    rows: 1,
    expect: [/Ende der Tabelle Die Spar-Potenziale im Energie-Bereich/],
    forbid: [/Übersichtstabelle/]
  }
};

for (const [name, c] of Object.entries(TABLE_CASES)) {
  const blocks = await jsBlocksFor(c.html);
  const tableBlocks = blocks.filter((b) => /^table-/.test(b.type));
  const intro = tableBlocks.find((b) => b.type === 'table-intro');
  const rows = tableBlocks.filter((b) => b.type === 'table-row');
  const sums = tableBlocks.filter((b) => b.type === 'table-sum');

  t.ok(!!intro, `[${name}] Tabelle wird mit Intro angekündigt`);
  if (c.intro) t.ok(c.intro.test(intro ? intro.text : ''), `[${name}] Intro nennt Spalten und Zeilen korrekt`, intro ? intro.text : '');
  t.eq(rows.length, c.rows, `[${name}] ${c.rows} Datenzeile(n) gesprochen`);
  if (typeof c.sums === 'number') t.eq(sums.length, c.sums, `[${name}] Summenzeile(n) erkannt`);
  (c.expect || []).forEach((re, i) => {
    const all = tableBlocks.map((b) => b.text).join(' | ');
    t.ok(re.test(all), `[${name}] Erwarteter Inhalt ${i + 1}`, re.source);
  });
  (c.forbid || []).forEach((re) => {
    const all = tableBlocks.map((b) => b.text).join(' | ');
    t.ok(!re.test(all), `[${name}] Fehlermuster tritt nicht auf: ${re.source}`);
  });
  // Zeilenmarkierung muss auf echten <tr>/<div role=row>-Elementen sitzen.
  t.ok(tableBlocks.every((b) => b.type === 'table-intro' || b.type === 'table-outro' || b.text.length > 5),
    `[${name}] Keine leeren Tabellenblöcke`);
}

/* ================================================================== */
/* 3) Grammatik: Zahlwort-Kongruenz                                    */
/* ================================================================== */
t.group('3) Grammatik (Zahlwort-Kongruenz)');
{
  const one = await jsBlocksFor('<p>Ein kurzer Absatz mit genügend Text für die Erkennung.</p>', { readingTime: '1' });
  const many = await jsBlocksFor('<p>Ein kurzer Absatz mit genügend Text für die Erkennung.</p>', { readingTime: '9' });
  t.ok(/Hördauer etwa eine Minute\./.test(one[0].text), 'Eine Minute Lesezeit klingt nicht nach „1 Minuten"', one[0].text);
  t.ok(/Hördauer etwa 9 Minuten\./.test(many[0].text), 'Mehrere Minuten bleiben im Plural', many[0].text);

  const single = await jsBlocksFor('<table><thead><tr><th>Tarif</th></tr></thead><tbody><tr><td>Öko</td></tr></tbody></table>');
  const singleIntro = single.find((b) => b.type === 'table-intro');
  t.ok(/mit 1 Spalte und einer Zeile/.test(singleIntro.text), '„1 Spalte" statt „1 Spalten"', singleIntro.text);
  t.ok(!/1 Spalten|1 Zeilen|1 Minuten/.test(singleIntro.text), 'Kein Plural nach der Eins');
}

/* ================================================================== */
/* 4) Fortschrittsanzeige                                             */
/* ================================================================== */
t.group('4) Fortschrittsanzeige');
{
  const body = [];
  for (let i = 0; i < 14; i++) {
    body.push(`<h2 id="kap-${i}">Kapitel ${i + 1}</h2><p>Absatz ${i + 1} mit ausreichend Text, damit die Sprachsynthese eine realistische Einheit bildet und der Fortschritt messbar wird.</p>`);
  }
  const html = body.join('\n');
  const env = await speakAll(html, { msPerChar: 0.25 });
  const bar = env.doc.getElementById('ff-reader-progress-bar');
  const label = env.doc.getElementById('ff-listen-label');

  let maxRatio = 0; let backward = 0; let last = 0;
  const samples = [];
  const watch = setInterval(() => {
    const r = ratioOf(bar.style.transform);
    if (r > maxRatio) maxRatio = r;
    const playing = label.textContent.trim() !== 'Vorlesen';
    if (playing && r < last - 0.0005) backward++;
    last = r;
    samples.push(r);
  }, 2);

  click(env.win, env.doc.getElementById('ff-listen-btn'));
  await until(() => ratioOf(bar.style.transform) > 0.05, 6000);
  t.ok(ratioOf(bar.style.transform) > 0.05, 'Fortschritt startet unmittelbar nach dem Klick');
  t.ok(/noch ca\. \d+ Min\./.test(env.doc.getElementById('ff-reader-remaining').textContent),
    'Restzeit wird während der Wiedergabe angezeigt',
    env.doc.getElementById('ff-reader-remaining').textContent);

  // Pause: Der Stand muss eingefroren bleiben (kein Weiterlaufen, kein Rücksprung).
  click(env.win, env.doc.getElementById('ff-listen-btn'));   // Pause
  await new Promise((r) => setTimeout(r, 60));
  const atPause = ratioOf(bar.style.transform);
  await new Promise((r) => setTimeout(r, 220));
  const afterPauseWait = ratioOf(bar.style.transform);
  t.ok(Math.abs(afterPauseWait - atPause) < 0.001,
    'In der Pause läuft die Fortschrittsanzeige nicht weiter',
    `${atPause.toFixed(4)} → ${afterPauseWait.toFixed(4)}`);

  click(env.win, env.doc.getElementById('ff-listen-btn'));   // Weiter
  await until(() => ratioOf(bar.style.transform) > atPause + 0.01, 6000);
  t.ok(ratioOf(bar.style.transform) >= atPause,
    'Nach dem Fortsetzen springt die Anzeige nicht zurück');

  // Abschnittssprung (vor) ist eine Benutzeraktion und muss den Stand setzen.
  click(env.win, env.doc.getElementById('ff-listen-next'));
  await new Promise((r) => setTimeout(r, 80));
  t.ok(ratioOf(bar.style.transform) > 0, 'Abschnittssprung setzt die Fortschrittsanzeige');

  await until(() => label.textContent.trim() === 'Vorlesen' && env.log.length > 20, 30000);
  clearInterval(watch);

  t.ok(maxRatio >= 0.999, 'Fortschritt erreicht am Ende exakt 100 %', `Höchstwert ${maxRatio.toFixed(4)}`);
  t.eq(backward, 0, 'Keine Rückwärtssprünge während der Wiedergabe');
  t.eq(env.errors, [], 'Keine Laufzeitfehler im Fortschritts-Durchlauf');
  await until(() => ratioOf(bar.style.transform) === 0, 4000);
  t.ok(ratioOf(bar.style.transform) === 0, 'Nach dem Ende kehrt die Anzeige in den Ruhezustand zurück');
}

/* ================================================================== */
/* 5) Parität: Tonspur (Python) ↔ Browser-Reader (JS)                 */
/* ================================================================== */
t.group('5) Parität Tonspur ↔ Browser-Reader');
{
  const parityFixtures = [
    ['Einfacher Artikel', '<h2 id="a">Überschrift</h2><p>Ein <strong>wichtiger</strong> Satz mit <a href="/x/">Link</a>.</p>'],
    ['Liste mit Fetteinleitung', '<ul><li><strong>Erstens:</strong> Text eins.</li><li><strong>Zweitens:</strong> Text zwei.</li></ul>'],
    ['Tabelle ohne thead', '<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>'],
    ['ARIA-Tabelle', '<div role="table" aria-label="X"><div role="row"><div role="columnheader">A</div></div><div role="row"><div role="cell">1</div></div></div>'],
    ['Summenzeile', '<table><thead><tr><th>P</th><th>B</th></tr></thead><tbody><tr><td>A</td><td>1 €</td></tr></tbody><tfoot><tr><td>Summe</td><td>2 €</td></tr></tfoot></table>'],
    ['Freistehender Fettdruck', '<div><strong>Wichtige Kostenbremse sofort prüfen</strong></div>'],
    ['Nummerierte Liste', '<ol><li><strong>Eins:</strong> a.</li><li><strong>Zwei:</strong> b.</li></ol>']
  ];
  for (const [name, html] of parityFixtures) {
    const js = await jsBlocksFor(html, { title: name });
    const py = pyBlocksFor(html, { title: name });
    t.eq(js.length, py.length, `[${name}] gleiche Blockanzahl`);
    const diffs = [];
    for (let i = 0; i < Math.max(js.length, py.length); i++) {
      const a = js[i] ? js[i].text : '(fehlt)';
      const b = py[i] ? py[i].text : '(fehlt)';
      if (a !== b) diffs.push(`#${i}\n   JS: ${a}\n   PY: ${b}`);
    }
    t.eq(diffs, [], `[${name}] identischer Text in Tonspur und Browser`);
  }

  // Echter Ratgeber-Artikel (die gemeldete Seite).
  const pillarFile = path.join(ROOT, 'content', 'pillar', 'strom-sparen', 'index.md');
  if (fs.existsSync(pillarFile)) {
    const raw = fs.readFileSync(pillarFile, 'utf8');
    const m = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
    const body = m[2];
    const title = 'Strom & Gas sparen: Der große Ratgeber für niedrige Energiekosten';
    const html = markdownToHtml(renderShortcodes(body));
    const js = await jsBlocksFor(html, { title, readingTime: '9' });
    const py = pyBlocksFor(html, { title, readingTime: '9' });
    t.eq(js.length, py.length, 'pillar/strom-sparen: gleiche Blockanzahl');
    const diffs = [];
    for (let i = 0; i < Math.max(js.length, py.length); i++) {
      const a = js[i] ? js[i].text : '(fehlt)';
      const b = py[i] ? py[i].text : '(fehlt)';
      if (a !== b) diffs.push(`#${i}\n   JS: ${a.slice(0, 140)}\n   PY: ${b.slice(0, 140)}`);
    }
    t.eq(diffs, [], 'pillar/strom-sparen: Tonspur und Browser lesen denselben Text');

    const leadIn = js.find((b) => /Tarifwechsel als größter Hebel/.test(b.text));
    t.ok(!!leadIn && /^Tarifwechsel als größter Hebel:/.test(leadIn.text),
      '„Tarifwechsel als größter Hebel:" steht am Satzanfang',
      leadIn ? leadIn.text.slice(0, 120) : 'Block fehlt');
  }
}

const failed = t.report();
if (failed === 0) {
  console.log('\n🎉 Tabellen, Fettdruck und Fortschritt auf Agentur-Niveau: Zeilen/Spalten korrekt, '
    + 'Fettdruck an seiner Stelle, Fortschritt monoton bis 100 %, Tonspur und Browser identisch.');
}
process.exit(failed === 0 ? 0 : 1);
