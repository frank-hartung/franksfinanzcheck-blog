#!/usr/bin/env node
// ============================================================
//  READER-PARITY-PROBE — Datenlieferant für das Paritäts-Gate
//  (scripts/reader_prosody_parity_check.py)
// ------------------------------------------------------------
//  Führt static/premium/ff-reader.js in einem Stub-Browser aus und
//  gibt die Regie-Daten als JSON auf stdout aus:
//    · PROSODY-Tabelle (Rollen: Tempo, Tonlage, Lautstärke, Pausen)
//    · Sprach-Lexika EN_SNIFF/DE_SNIFF
//    · Sprach-Entscheidungen für die vom Gate übergebenen Fälle
//    · männliche Stimmenwahl für einen Edge-2026-Katalog
//
//  Aufruf (durch das Gate, nicht manuell):
//    node scripts/reader_parity_probe.js <faelle.json>
//  faelle.json: [{ "text": "...", "base": "de"|"en" }, …]
//
//  Die Produktivdatei bleibt unangetastet; der Test-Hook wird nur im
//  RAM angehängt (gleiches Verfahren wie reader_engine_check.js).
// ============================================================

'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const SRC = fs.readFileSync(path.join(ROOT, 'static', 'premium', 'ff-reader.js'), 'utf8');

const closeIdx = SRC.lastIndexOf('})();');
if (closeIdx < 0) {
  console.error('❌ IIFE-Abschluss nicht gefunden.');
  process.exit(1);
}
const hook = `
;(typeof globalThis !== 'undefined') && (globalThis.__FF_HOOKS = {
  PROSODY: PROSODY,
  EN_SNIFF: EN_SNIFF,
  DE_SNIFF: DE_SNIFF,
  GERMAN_ENDINGS: GERMAN_ENDINGS,
  MALE_KEYWORDS: MALE_KEYWORDS,
  KNOWN_MALE_VOICES: KNOWN_MALE_VOICES,
  FEMALE_KEYWORDS: FEMALE_KEYWORDS,
  STUDIO_VOICES: STUDIO_VOICES,
  PREMIUM_TIERS: PREMIUM_TIERS,
  sniffSentenceLang: sniffSentenceLang,
  speechNormalize: speechNormalize,
  scoreVoice: scoreVoice,
  premiumTierBonus: premiumTierBonus,
  isFemaleCandidate: isFemaleCandidate,
  explicitMale: explicitMale,
  resolveMaleVoice: resolveMaleVoice,
  refreshVoices: refreshVoices
});
`;
const code = SRC.slice(0, closeIdx) + hook + SRC.slice(closeIdx);

/* ---------- Minimaler Browser-/DOM-Stub ---------- */
function fakeEl(id) {
  const classes = new Set();
  return {
    id: id || '',
    tagName: 'DIV',
    textContent: '',
    innerHTML: '',
    style: {},
    classList: {
      add: (c) => classes.add(c),
      remove: (c) => classes.delete(c),
      toggle: (c, f) => { const on = f === undefined ? !classes.has(c) : !!f; if (on) { classes.add(c); } else { classes.delete(c); } return on; },
      contains: (c) => classes.has(c)
    },
    setAttribute(k, v) { this['attr_' + k] = String(v); },
    getAttribute(k) { return this['attr_' + k] !== undefined ? this['attr_' + k] : null; },
    addEventListener() {}, removeEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    appendChild(c) { return c; }, removeChild(c) { return c; },
    parentNode: null, parentElement: null,
    closest() { return null; }, contains() { return false; },
    focus() {}, scrollIntoView() {}
  };
}

const elems = {};
const getEl = (id) => { if (!elems[id]) { elems[id] = fakeEl(id); } return elems[id]; };
getEl('ff-reader-config').textContent = JSON.stringify({
  title: 'Stromvergleich 2026: So sparst du 420 Euro im Jahr',
  readingTime: '7', wordCount: '1200', lang: 'de'
});

const synthStub = {
  _voices: [],
  getVoices() { return this._voices.slice(); },
  speaking: false, pending: false, paused: false,
  speak() {}, cancel() {}, pause() {}, resume() {},
  onvoiceschanged: null
};

const ctx = {
  console: { log() {}, warn() {}, error() {} },
  setTimeout, clearTimeout, setInterval, clearInterval,
  document: {
    getElementById: getEl,
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: () => fakeEl(''),
    addEventListener() {}, removeEventListener() {},
    body: { innerText: '' },
    documentElement: { lang: 'de' },
    title: 'Parity-Probe'
  },
  navigator: { userAgent: 'ReaderParityProbe (Desktop-Test)' },
  localStorage: {
    _m: {},
    getItem(k) { return this._m[k] !== undefined ? this._m[k] : null; },
    setItem(k, v) { this._m[k] = String(v); },
    removeItem(k) { delete this._m[k]; }
  }
};
ctx.window = {
  location: { pathname: '/test-artikel/' },
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
const H = ctx.__FF_HOOKS;
if (!H || !H.PROSODY) {
  console.error('❌ Test-Hooks fehlen.');
  process.exit(1);
}

/* ---------- Fälle einlesen ---------- */
let cases = [];
const arg = process.argv[2];
if (arg && fs.existsSync(arg)) {
  try { cases = JSON.parse(fs.readFileSync(arg, 'utf8')); } catch (e) { cases = []; }
}

const V = (name, lang, opts) => Object.assign(
  { name, lang, localService: true, default: false, voiceURI: name + '|' + lang }, opts || {});

// Edge-Katalog 2026: Multilingual-v2-Stimmen (männlich/weiblich gemischt).
const EDGE_2026 = [
  V('Microsoft FlorianMultilingual Online (Natural) - German (Germany)', 'de-DE', { localService: false }),
  V('Microsoft Conrad Online (Natural) - German (Germany)', 'de-DE', { localService: false }),
  V('Microsoft Stefan Online (Natural) - German (Germany)', 'de-DE', { localService: false }),
  V('Microsoft Katja Online (Natural) - German (Germany)', 'de-DE', { localService: false }),
  V('Microsoft EmmaMultilingual Online (Natural) - German (Germany)', 'de-DE', { localService: false }),
  V('Microsoft AndrewMultilingual Online (Natural) - English (United States)', 'en-US', { localService: false }),
  V('Microsoft AvaMultilingual Online (Natural) - English (United States)', 'en-US', { localService: false }),
  V('de-DE-ConradNeural', 'de-DE', { localService: false }),
  V('de-DE-KatjaNeural', 'de-DE', { localService: false })
];
synthStub._voices = EDGE_2026;
H.refreshVoices();
const pickDe = H.resolveMaleVoice('de');
const pickEn = H.resolveMaleVoice('en');

const out = {
  prosody: H.PROSODY,
  lex: {
    en: Object.keys(H.EN_SNIFF),
    de: Object.keys(H.DE_SNIFF),
    germanEndings: H.GERMAN_ENDINGS
  },
  male: {
    keywords: H.MALE_KEYWORDS,
    known: H.KNOWN_MALE_VOICES,
    female: H.FEMALE_KEYWORDS,
    studio: H.STUDIO_VOICES
  },
  lang: {},
  norm: {},
  picks: {
    de: pickDe && pickDe.voice ? pickDe.voice.name : null,
    deMode: pickDe ? pickDe.mode : null,
    deExplicit: pickDe ? !!pickDe.explicit : false,
    en: pickEn && pickEn.voice ? pickEn.voice.name : null
  }
};

cases.forEach((c) => {
  const key = c.base + '|' + c.text;
  out.lang[key] = H.sniffSentenceLang(c.text, c.base);
  out.norm[key] = H.speechNormalize(c.text, c.base);
});

process.stdout.write(JSON.stringify(out) + '\n');
process.exit(0);
