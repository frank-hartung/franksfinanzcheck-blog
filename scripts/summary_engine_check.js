#!/usr/bin/env node
// ============================================================
//  SUMMARY-ENGINE-CHECK – Dauerhafte Highend-Wache für „Kurzfassung“
//  (Kurzfassung v4: Verlagshaus-Standard Capital / WirtschaftsWoche /
//  Die Zeit – Kurzantwort, Kernaussagen, Zahlen auf einen Blick,
//  Inhaltsverzeichnis, Tabellen-Highlights, Byline, Fokus-Falle)
// ------------------------------------------------------------
//  Prüfgegenstand: static/premium/ff-reader.js – die ECHTEN Extraktoren
//  werden per temporärem Test-Hook in einer VM mit gestubbtem DOM
//  (inkl. künstlichem .post-content) ausgeführt. Die Produktivdatei
//  bleibt unangetastet.
//  Aufruf: node scripts/summary_engine_check.js  (Exit 0 = alles grün)
// ============================================================

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const SRC = fs.readFileSync(path.join(ROOT, 'static', 'premium', 'ff-reader.js'), 'utf8');

/* ---------- 1) Produktionscode mit Test-Hook versehen (nur im RAM) ---------- */
const closeIdx = SRC.lastIndexOf('})();');
if (closeIdx < 0) {
  console.error('❌ IIFE-Abschluss nicht gefunden – ff-reader.js Struktur unerwartet.');
  process.exit(1);
}
const hook = `
;(typeof globalThis !== 'undefined') && (globalThis.__FF_SUMMARY = {
  I18N: I18N,
  summarySentences: summarySentences,
  maskSentenceDots: maskSentenceDots,
  signalScore: signalScore,
  normalizeKey: normalizeKey,
  overlapRatio: overlapRatio,
  extractFigure: extractFigure,
  extractKeyBullets: extractKeyBullets,
  extractKeyFigures: extractKeyFigures,
  extractToc: extractToc,
  extractTables: extractTables,
  pickShortAnswer: pickShortAnswer,
  buildSummaryData: buildSummaryData,
  buildPlainText: buildPlainText,
  getCurrentLang: function () { return currentLang; }
});
`;
const code = SRC.slice(0, closeIdx) + hook + SRC.slice(closeIdx);

/* ---------- 2) Minimaler Fake-DOM (verschachtelungssicher) ---------- */
function makeNode(tag, opts) {
  opts = opts || {};
  const node = {
    tagName: String(tag || 'DIV').toUpperCase(),
    id: opts.id || '',
    _text: opts.text !== undefined ? String(opts.text) : '',
    children: opts.children ? opts.children.slice() : [],
    parentNode: null,
    open: false,
    style: {},
    disabled: false,
    className: ''
  };
  Object.defineProperty(node, 'textContent', {
    enumerable: true,
    get: function () {
      if (this.children.length) {
        return this.children.map(function (c) { return c.textContent; }).join(' ');
      }
      return this._text;
    },
    set: function (v) { this._text = String(v); }
  });
  node.cloneNode = function (deep) {
    const c = makeNode(this.tagName, { id: this.id, text: this._text });
    if (deep) {
      this.children.forEach(function (ch) {
        const cc = ch.cloneNode(true);
        cc.parentNode = c;
        c.children.push(cc);
      });
    }
    return c;
  };
  node.querySelectorAll = function () { return []; };
  node.querySelector = function () { return null; };
  node.closest = function () { return null; };
  node.getAttribute = function () { return null; };
  node.setAttribute = function () {};
  node.appendChild = function (c) { c.parentNode = node; node.children.push(c); return c; };
  node.removeChild = function (c) {
    const i = node.children.indexOf(c);
    if (i >= 0) node.children.splice(i, 1);
    return c;
  };
  node.addEventListener = function () {};
  node.removeEventListener = function () {};
  node.focus = function () {};
  node.scrollIntoView = function () {};
  node.contains = function (c) { return node === c; };
  return node;
}

/* Künstlicher Artikelkörper (wie .post-content) */
function buildContent() {
  const content = makeNode('DIV');
  content.className = 'post-content md-content';

  const h2a = makeNode('H2', { id: 'was-kostet-der-schutz', text: 'Was der Schutz kostet' });
  const p1 = makeNode('P', { text: 'Eine gute Hausratversicherung kostet für eine 70-Quadratmeter-Wohnung etwa 7 bis 12 Euro im Monat. Du solltest die Versicherungssumme realistisch planen, sonst droht die Unterversicherungsfalle.' });
  const p2 = makeNode('P', { text: 'Wer den Anbieter wechselt, spart bis zu 40 Prozent im Jahr. Die Faustregel lautet: mindestens 650 Euro je Quadratmeter Wohnfläche ansetzen.' });
  const li1 = makeNode('LI', { text: 'Achtung: Eine fehlende Elementarschutz-Klausel kann bei Starkregen teuer werden.' });

  const h2b = makeNode('H2', { id: 'sinnvolle-bausteine', text: 'Sinnvolle Bausteine' });
  const p3 = makeNode('P', { text: 'Elementarschutz kostet oft nur 30 bis 60 Euro im Jahr. Eine Fahrradklausel lohnt sich ab einem hochwertigen E-Bike.' });

  const table = makeNode('TABLE');
  const thead = makeNode('THEAD', { children: [makeNode('TR', { children: [makeNode('TH', { text: 'Anbieter' }), makeNode('TH', { text: 'Preis im Monat' })] })] });
  const tbody = makeNode('TBODY', { children: [
    makeNode('TR', { children: [makeNode('TD', { text: 'Anbieter A' }), makeNode('TD', { text: '7 €' })] }),
    makeNode('TR', { children: [makeNode('TD', { text: 'Anbieter B' }), makeNode('TD', { text: '9 €' })] }),
    makeNode('TR', { children: [makeNode('TD', { text: 'Anbieter C' }), makeNode('TD', { text: '12 €' })] })
  ] });
  table.children = [thead, tbody];

  content.children = [h2a, p1, p2, li1, h2b, p3, table];
  return content;
}

const content = buildContent();

const elems = {};
const getEl = (id) => {
  if (!elems[id]) elems[id] = makeNode('DIV', { id: id });
  return elems[id];
};
getEl('ff-reader-config').textContent = JSON.stringify({
  title: 'Hausratversicherung: Was sie kostet und wen sie schützt',
  readingTime: '7',
  wordCount: '1200',
  lang: 'de',
  author: 'Frank Hartung',
  date: '03.09.2026',
  updated: '03.09.2026',
  category: 'Ratgeber'
});

const synthStub = {
  _voices: [],
  getVoices() { return this._voices.slice(); },
  speaking: false, pending: false, paused: false,
  speak() {}, cancel() {}, pause() {}, resume() {},
  onvoiceschanged: null
};

const ctx = {
  console,
  setTimeout, clearTimeout, setInterval, clearInterval,
  __FF_VOICES: [],
  document: {
    getElementById: getEl,
    querySelector: (sel) => {
      if (sel === '.post-content' || sel === '.md-content') return content;
      return null;
    },
    querySelectorAll: () => [],
    createElement: (tag) => makeNode(tag),
    addEventListener() {}, removeEventListener() {},
    body: { innerText: '', style: {}, appendChild() {}, removeChild() {} },
    documentElement: { lang: 'de', style: {} },
    activeElement: null,
    title: 'Test'
  },
  navigator: { userAgent: 'SummaryEngineCheck (Desktop-Test)' },
  localStorage: {
    _m: {},
    getItem(k) { return this._m[k] !== undefined ? this._m[k] : null; },
    setItem(k, v) { this._m[k] = String(v); },
    removeItem(k) { delete this._m[k]; }
  }
};
ctx.window = {
  location: { pathname: '/hausratversicherung/', href: 'https://franksfinanzcheck.de/hausratversicherung/' },
  matchMedia: () => ({ matches: false }),
  navigator: ctx.navigator,
  localStorage: ctx.localStorage,
  speechSynthesis: synthStub,
  SpeechSynthesisUtterance: function SpeechSynthesisUtterance(text) { this.text = text; },
  addEventListener() {}, removeEventListener() {}
};
vm.createContext(ctx);

try {
  vm.runInContext(code, ctx, { filename: 'ff-reader.js' });
} catch (e) {
  console.error('❌ ff-reader.js ließ sich im Stub-Browser nicht initialisieren:', e.message);
  process.exit(1);
}
const S = ctx.__FF_SUMMARY;
if (!S || !S.buildSummaryData) {
  console.error('❌ Test-Hooks wurden nicht gesetzt.');
  process.exit(1);
}

/* ---------- 3) Testläufe ---------- */
let pass = 0, fail = 0;
const failures = [];
function T(name, cond, detail) {
  if (cond) { pass++; console.log('  ✅ ' + name); }
  else { fail++; failures.push(name + (detail ? ' — ' + detail : '')); console.log('  ❌ ' + name + (detail ? ' — ' + detail : '')); }
}
function has(h, n) { return String(h).indexOf(n) !== -1; }

console.log('=== Summary-Engine-Check: Kurzfassung v4 (Capital / WiWo / ZEIT) ===\n');

/* --- 3.1 Abkürzungs- & zahlenfeste Satzsegmentierung --- */
console.log('— Satzsegmentierung (abkürzungs-/zahlenfest) —');
let seg = S.summarySentences('Das kostet z. B. 1.250,50 Euro. Es lohnt sich.');
T('„z. B.“ und Tausenderpunkt spalten NICHT', seg.length === 2, JSON.stringify(seg));
T('Erster Satz unversehrt („1.250,50 Euro“)', has(seg[0], '1.250,50 Euro'), seg[0]);
seg = S.summarySentences('Spare ca. 40 % p. a. und wechsle.');
T('„ca.“ spaltet nicht', seg.length >= 1 && has(seg[0], 'ca. 40'), JSON.stringify(seg));

/* --- 3.2 Signal-Ranking (redaktionell) --- */
console.log('— Redaktionelles Signal-Ranking —');
T('Signal-Satz wird höher gerankt als neutrale Passage',
  S.signalScore('Wer wechselt, spart bis zu 40 Prozent.', 'de') > S.signalScore('Das Wetter ist heute freundlich.', 'de'),
  S.signalScore('Wer wechselt, spart bis zu 40 Prozent.', 'de') + ' vs ' + S.signalScore('Das Wetter ist heute freundlich.', 'de'));

/* --- 3.3 Zahlen-Extraktion (Auf einen Blick) --- */
console.log('— Zahlen auf einen Blick —');
let fig = S.extractFigure('Eine gute Hausratversicherung kostet etwa 7 bis 12 Euro im Monat.', 'de');
T('Wert erkannt („7 bis 12 Euro im Monat“)', fig && has(fig.value, '7 bis 12') && has(fig.value, 'Euro'), fig && JSON.stringify(fig));
T('Label sauber getrennt (nicht leer, ohne Wert-Duplikat)', fig && fig.label && !has(fig.label, '7 bis 12') && !has(fig.label, 'Euro im Monat'), fig && fig.label);
let figs = S.extractKeyFigures(content, 'de');
T('Extraktor liefert 1–6 Zahlen', figs.length >= 1 && figs.length <= 6, 'count=' + figs.length);
T('Jede Zahl hat Wert + Label', figs.every(f => f.value && f.label), figs.map(f => f.value).join(' | '));
T('Prozent-Zahl enthalten', figs.some(f => has(f.value, '%') || has(f.value, 'Prozent')), figs.map(f => f.value).join(' | '));

/* --- 3.4 Kernaussagen (3–5 Bullets, dublettenfrei, lesbar) --- */
console.log('— Kernaussagen —');
let bullets = S.extractKeyBullets(content, 'de');
T('3–5 Kernaussagen', bullets.length >= 3 && bullets.length <= 5, 'count=' + bullets.length);
T('Jede Kernaussage 24–260 Zeichen', bullets.every(b => b.text.length >= 24 && b.text.length <= 260), bullets.map(b => b.text.length).join(','));
T('Kernaussagen sind eindeutig (keine Dubletten)', new Set(bullets.map(b => S.normalizeKey(b.text))).size === bullets.length, JSON.stringify(bullets.map(b => b.text.slice(0, 30))));
T('Mindestens eine Aussage mit Spar-/Kosten-Signal', bullets.some(b => /spar|kost|euro|prozent|lohnt|solltest/i.test(b.text)), JSON.stringify(bullets.map(b => b.text.slice(0, 40))));
T('Sprungmarken gesetzt (Anker vorhanden)', bullets.some(b => b.anchor), JSON.stringify(bullets.map(b => b.anchor)));

/* --- 3.5 Inhaltsverzeichnis --- */
console.log('— In diesem Artikel —');
let toc = S.extractToc(content);
T('Inhaltsverzeichnis erfasst alle H2 mit id', toc.length === 2, JSON.stringify(toc.map(t => t.title)));
T('Abschnitts-Teaser vorhanden', toc.every(t => t.lead), JSON.stringify(toc.map(t => t.lead.slice(0, 20))));

/* --- 3.6 Tabellen-Highlights --- */
console.log('— Tabellen & Übersichten —');
let tables = S.extractTables(content, 'de');
T('Genau 1 Tabelle erkannt', tables.length === 1, 'count=' + tables.length);
T('Spaltenköpfe extrahiert', tables[0].headers.join('|') === 'Anbieter|Preis im Monat', tables[0].headers.join('|'));
T('Zeilenanzahl korrekt (3)', tables[0].rowCount === 3, String(tables[0].rowCount));
T('Tabellen-Titel vergeben', !!tables[0].title, tables[0].title);

/* --- 3.7 Gesamtdatensatz + Klartext --- */
console.log('— Kurzantwort, Gesamtdatensatz, Klartext —');
let data = S.buildSummaryData();
T('Kurzantwort vorhanden (> 40 Zeichen)', data.short && data.short.length > 40, data.short && data.short.slice(0, 50));
T('Gesamtdatensatz vollständig (short/bullets/figures/toc/tables)', !!(data.short && data.bullets.length && data.figures.length && data.toc.length && data.tables.length), JSON.stringify({ b: data.bullets.length, f: data.figures.length, t: data.toc.length, tb: data.tables.length }));
T('Byline-Daten durchgereicht (Autor/Stand)', data.author === 'Frank Hartung' && data.updated === '03.09.2026', data.author + '/' + data.updated);
let plain = S.buildPlainText(data);
T('Klartext enthält Titel, Quelle & Struktur', has(plain, 'KURZFASSUNG') && has(plain, 'https://franksfinanzcheck.de/') && has(plain, 'Kernaussagen') && has(plain, 'Auf einen Blick'), plain.slice(0, 120));
T('Klartext enthält Byline (Autor · Stand)', has(plain, 'Frank Hartung') && has(plain, '03.09.2026'), '');

/* --- 3.8 I18N-Konsistenz --- */
console.log('— Redaktionelle Konsistenz (DE/EN) —');
T('I18N DE & EN vollständig (Kurzfassung v4)',
  ['summaryQuick30', 'summaryKeypoints', 'summaryNumbers', 'summaryTables', 'summaryToc', 'summaryJump', 'summaryJumpTable', 'summaryAuthor', 'summaryStand', 'summaryEmpty', 'summaryRowCount'].every(k => S.I18N.de[k] && S.I18N.en[k]),
  JSON.stringify(Object.keys(S.I18N.de).filter(k => /summary/.test(k))));

/* ---------- 4) Ergebnis ---------- */
console.log('\n=== Ergebnis: ' + pass + ' grün, ' + fail + ' rot ===');
if (fail) {
  failures.forEach(f => console.log('  ❌ ' + f));
  process.exit(1);
}
console.log('🎉 Alle Kurzfassungs-Prüfungen erfolgreich: Kurzfassung v4 auf Verlagshaus-Niveau (Capital / WirtschaftsWoche / Die Zeit).');
process.exit(0);
