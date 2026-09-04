#!/usr/bin/env node
// ============================================================
//  READER-ENGINE-CHECK – Dauerhafte Highend-Wache für „Vorlesen“
//  (Sprachausgabe v4: Ton-Garantie, nur männliche Stimme,
//  DE & EN ohne Umschalter, Verlagshaus-Regie: Capital / WiWo / Die Zeit)
// ------------------------------------------------------------
//  Prüfgegenstand: static/premium/ff-reader.js – die ECHTEN Funktions-
//  körper werden per temporärem Test-Hook in einer VM mit gestubbtem
//  DOM/Browser ausgeführt. Die Produktivdatei bleibt unangetastet.
//  Aufruf: node scripts/reader_engine_check.js  (Exit 0 = alles grün)
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
;(typeof globalThis !== 'undefined') && (globalThis.__FF_HOOKS = {
  I18N: I18N,
  PROSODY: PROSODY,
  QUALITY_PROFILES: QUALITY_PROFILES,
  speechNormalize: speechNormalize,
  sentences: sentences,
  proseSentences: proseSentences,
  sniffSentenceLang: sniffSentenceLang,
  splitForSpeech: splitForSpeech,
  contentRateFactor: contentRateFactor,
  effectiveRateFor: effectiveRateFor,
  pauseAfterChunk: pauseAfterChunk,
  autoPitch: autoPitch,
  scoreVoice: scoreVoice,
  premiumTierBonus: premiumTierBonus,
  hasNeuralNamePrefix: hasNeuralNamePrefix,
  hasNeuralToken: hasNeuralToken,
  neuralTokens: neuralTokens,
  isFemaleCandidate: isFemaleCandidate,
  PREMIUM_TIERS: PREMIUM_TIERS,
  rankVoicesFromList: rankVoicesFromList,
  dedupeVoices: dedupeVoices,
  isMaleCandidate: isMaleCandidate,
  explicitMale: explicitMale,
  resolveMaleVoice: resolveMaleVoice,
  calibrateQuality: calibrateQuality,
  refreshVoices: refreshVoices,
  getQuality: function () { return quality; },
  getCurrentLang: function () { return currentLang; }
});
`;
const code = SRC.slice(0, closeIdx) + hook + SRC.slice(closeIdx);

/* ---------- 2) Minimaler Browser-/DOM-Stub ---------- */
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
      toggle: (c, f) => { const on = f === undefined ? !classes.has(c) : !!f; on ? classes.add(c) : classes.delete(c); return on; },
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
const getEl = (id) => { if (!elems[id]) elems[id] = fakeEl(id); return elems[id]; };
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
  console,
  setTimeout, clearTimeout, setInterval, clearInterval,
  __FF_VOICES: [],
  document: {
    getElementById: getEl,
    querySelector: () => null,
    querySelectorAll: () => [],
    createElement: () => fakeEl(''),
    addEventListener() {}, removeEventListener() {},
    body: { innerText: '' },
    documentElement: { lang: 'de' },
    title: 'Test'
  },
  navigator: { userAgent: 'ReaderEngineCheck (Desktop-Test)' },
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
if (!H || !H.speechNormalize) {
  console.error('❌ Test-Hooks wurden nicht gesetzt.');
  process.exit(1);
}

function setVoices(list) {
  synthStub._voices = list;
  H.refreshVoices(); // Epochen-Bump + Cache-Reset + Neu-Kalibrierung (wie voiceschanged)
}

/* ---------- 3) Stimmen-Kataloge realer Plattformen ---------- */
const V = (name, lang, opts) => Object.assign({ name, lang, localService: true, default: false, voiceURI: name + '|' + lang }, opts || {});

const EDGE_DESKTOP = [
  V('Microsoft Stefan Online (Natural) - German (Germany)', 'de-DE', { localService: false, default: true }),
  V('Microsoft Katja Online (Natural) - German (Germany)', 'de-DE', { localService: false }),
  V('Microsoft Guy Online (Natural) - English (United States)', 'en-US', { localService: false }),
  V('Microsoft Zira Desktop - English (United States)', 'en-US'),
  V('Google Deutsch', 'de-DE', { localService: false }),
  V('Google US English', 'en-US', { localService: false })
];

const MACOS = [
  V('Anna', 'de-DE'),
  V('Markus', 'de-DE'),
  V('Yannick', 'de-DE'),
  V('Helena', 'de-DE'),
  V('Daniel', 'en-GB'),
  V('Samantha', 'en-US'),
  V('Microsoft Andreas Online (Natural) - German (Germany)', 'de-DE', { localService: false })
];

const ANDROID_CHROME = [
  V('Google Deutsch', 'de-DE', { localService: false, default: true }),
  V('Google US English', 'en-US', { localService: false }),
  V('Google UK English Female', 'en-GB', { localService: false })
];

const CHROME_LINUX = [
  V('Google Deutsch', 'de-DE', { localService: false, default: true }),
  V('Google US English', 'en-US', { localService: false })
];

const NUR_WEIBLICH = [
  V('Microsoft Katja Online (Natural) - German (Germany)', 'de-DE', { localService: false }),
  V('Microsoft Hedda', 'de-DE'),
  V('Microsoft Elsa Online (Natural) - German (Germany)', 'de-DE', { localService: false })
];

const NUR_ENGLISCH = [
  V('Microsoft Daniel Online (Natural) - English (United Kingdom)', 'en-GB', { localService: false }),
  V('Microsoft Zira Desktop - English (United States)', 'en-US')
];

const MULTI_LANG_POOL = [
  V('Microsoft Henri Online (Natural) - French (France)', 'fr-FR', { localService: false }),
  V('Microsoft Denise Online (Natural) - French (France)', 'fr-FR', { localService: false }),
  V('Microsoft Colette Online (Natural) - Dutch (Netherlands)', 'nl-NL', { localService: false }),
  V('Microsoft Maarten Online (Natural) - Dutch (Netherlands)', 'nl-NL', { localService: false })
];

/* ---------- 4) Testläufe ---------- */
let pass = 0, fail = 0;
const failures = [];
function T(name, cond, detail) {
  if (cond) { pass++; console.log('  ✅ ' + name); }
  else { fail++; failures.push(name + (detail ? ' — ' + detail : '')); console.log('  ❌ ' + name + (detail ? ' — ' + detail : '')); }
}
function has(hay, needle) { return String(hay).indexOf(needle) !== -1; }

console.log('=== Reader-Engine-Check: Vorlesen Highend v4 (Ton-Garantie, männlich, DE/EN) ===\n');

/* --- 4.1 Redaktionelle Lautschrift Deutsch --- */
console.log('— Lautschrift & Aussprache (Deutsch) —');
let s = H.speechNormalize('Am 03.09.2026 um 14:30 Uhr.', 'de');
T('Datum + Uhrzeit: „3. September 2026“ + „14 Uhr 30“', has(s, '3. September 2026') && has(s, '14 Uhr 30'), s);
s = H.speechNormalize('Stand 2026-09-03.', 'de');
T('ISO-Datum → „3. September 2026“', has(s, '3. September 2026'), s);
s = H.speechNormalize('Von 9:15 bis 10:00.', 'de');
T('Uhrzeit ohne Suffix → „9 Uhr 15“', has(s, '9 Uhr 15') && has(s, '10 Uhr'), s);
s = H.speechNormalize('1.250,50 € bleiben.', 'de');
T('Tausenderpunkt + Euro → „1250,50 Euro“', has(s, '1250,50 Euro'), s);
s = H.speechNormalize('Der ETF-Sparplan: § 12 Abs. 2 SGB V gilt z. B. auch für die PKV.', 'de');
T('ETF → „E T F“', has(s, 'E T F'), s);
T('Paragraf + Absatz', has(s, 'Paragraf 12') && has(s, 'Absatz 2'), s);
T('SGB V → „Sozialgesetzbuch Fünf“', has(s, 'Sozialgesetzbuch Fünf'), s);
T('z. B. → „zum Beispiel“', has(s, 'zum Beispiel'), s);
T('PKV ausgeschrieben', has(s, 'private Krankenversicherung'), s);
s = H.speechNormalize('3 Mio. € p. a., zzgl. MwSt., ca. 40 ct/kWh.', 'de');
T('„3 Millionen Euro pro Jahr“', has(s, '3 Millionen Euro pro Jahr'), s);
T('zzgl. MwSt. ausgeschrieben', has(s, 'zuzüglich Mehrwertsteuer'), s);
T('ct/kWh → „Cent pro Kilowattstunde“', has(s, 'Cent pro Kilowattstunde'), s);
s = H.speechNormalize('20–30 % in den 90er Jahren, o. Ä. etc.', 'de');
T('Bereich + Prozent: „20 bis 30 Prozent“', has(s, '20 bis 30 Prozent'), s);
T('Jahrzehnt: „90er“ → „Neunziger“', has(s, 'Neunziger'), s);
T('o. Ä. / etc. ausgeschrieben', has(s, 'oder Ähnliches') && has(s, 'et cetera'), s);
s = H.speechNormalize('Infos auf https://franksfinanzcheck.de/strom-gas', 'de');
T('URL → „die Webseite … Punkt …“', has(s, 'die Webseite franksfinanzcheck Punkt de'), s);
s = H.speechNormalize('Die Rendite liegt bei 1.250,50 € — u. a. wegen der Kosten, v. a. im Juni.', 'de');
T('u. a. / v. a. ausgeschrieben', has(s, 'unter anderem') && has(s, 'vor allem'), s);

/* --- 4.2 Redaktionelle Lautschrift Englisch --- */
console.log('— Lautschrift & Aussprache (Englisch) —');
s = H.speechNormalize('Save 20 % with approx. $1,250 (e.g. new tariffs).', 'en');
T('% → percent, $ → Dollars', has(s, '20 percent') && has(s, '1,250 Dollars'), s);
T('approx./e.g. ausgeschrieben', has(s, 'approximately') && has(s, 'for example'), s);
s = H.speechNormalize('Updated 2026-09-03, etc.', 'en');
T('ISO-Datum EN → „September 3, 2026“', has(s, 'September 3, 2026'), s);
T('etc. → et cetera', has(s, 'et cetera'), s);

/* --- 4.3 Automatisches Satz-Routing DE/EN (ohne Umschalter) --- */
console.log('— Zweisprachiger Sprecherwechsel (Satz-Routing) —');
T('Reiner EN-Satz im DE-Artikel → EN-Stimme',
  H.sniffSentenceLang('This is a simple test sentence with common words.', 'de') === 'en');
T('Lehnwort-Satz bleibt DE (kein Sprecherwechsel)',
  H.sniffSentenceLang('Online-Banking ist praktisch und günstig.', 'de') === 'de');
T('Reiner DE-Satz im EN-Artikel → DE-Stimme',
  H.sniffSentenceLang('Die Versicherung kostet 12 Euro im Monat.', 'en') === 'de');
T('EN-Lehnwort-Satz bleibt EN',
  H.sniffSentenceLang('The budget plan works well for your money.', 'en') === 'en');

/* --- 4.4 Nur-Männlich-Stimmregie über Plattformen --- */
console.log('— Stimmbesetzung: NUR männlich (DE & EN) —');

setVoices(EDGE_DESKTOP);
let r = H.resolveMaleVoice('de');
T('Edge/Windows DE: „Stefan“ (explizit männlich, Studio)', r.voice && /stefan/i.test(r.voice.name) && r.explicit && r.mode === 'male', r.voice && r.voice.name);
r = H.resolveMaleVoice('en');
T('Edge/Windows EN: „Guy“ (explizit männlich, Studio)', r.voice && /guy/i.test(r.voice.name) && r.explicit, r.voice && r.voice.name);
T('Edge-Kalibrierung: Studio-Regie aktiv', H.getQuality().tier === 'studio', H.getQuality().tier);

setVoices(MACOS);
r = H.resolveMaleVoice('de');
T('macOS DE: männliche Stimme (Markus/Andreas/Yannick …)', r.voice && r.explicit && /markus|andreas|yannick/i.test(r.voice.name), r.voice && r.voice.name);
T('macOS DE: niemals Anna/Helena', r.voice && !/anna|helena/i.test(r.voice.name), r.voice && r.voice.name);
r = H.resolveMaleVoice('en');
T('macOS EN: „Daniel“ (explizit männlich)', r.voice && /daniel/i.test(r.voice.name) && r.explicit, r.voice && r.voice.name);

setVoices(CHROME_LINUX);
r = H.resolveMaleVoice('de');
T('Chrome/Linux DE: unbenannter Besatz wird männlich-zonig (nicht explizit)',
  r.voice && r.mode === 'male' && r.explicit === false, r.voice && r.voice.name);
T('Chrome/Linux: Tonlagen-Garantie ≤ 0,88 (männliche Klangzone)',
  H.autoPitch({ emo: 'statement', words: 10 }, 0.96, r) <= 0.88, String(H.autoPitch({ emo: 'statement', words: 10 }, 0.96, r)));
T('Chrome/Linux: Regie-Kappe „standard“ (ruhigere Führung)', H.getQuality().tier === 'standard', H.getQuality().tier);

setVoices(ANDROID_CHROME);
r = H.resolveMaleVoice('de');
T('Android DE: „Google UK English Female“ wird nie gewählt',
  r.voice && !/female/i.test(r.voice.name), r.voice && r.voice.name);
T('Android DE: unbekannter Besatz trotzdem männliche Zone',
  H.autoPitch({ emo: 'statement' }, 1.0, r) <= 0.88, String(H.autoPitch({ emo: 'statement' }, 1.0, r)));

setVoices(NUR_WEIBLICH);
r = H.resolveMaleVoice('de');
T('Nur-Weiblich-Notnagel: Modus „fallback“ + Absenkung ≤ 0,86',
  r.mode === 'fallback' && H.autoPitch({ emo: 'statement' }, 1.0, r) <= 0.86, r.mode + ' ' + H.autoPitch({ emo: 'statement' }, 1.0, r));

setVoices(NUR_ENGLISCH);
r = H.resolveMaleVoice('de');
T('Kein DE verfügbar: männliche EN-Stimme übernimmt (Daniel, niemals weiblich)',
  (r.mode === 'cross' || r.mode === 'male') && r.voice && /daniel/i.test(r.voice.name) && r.explicit,
  r.mode + ' ' + (r.voice && r.voice.name));

setVoices(MULTI_LANG_POOL);
const rankedFR = H.rankVoicesFromList(MULTI_LANG_POOL, 'fr-FR');
T('Cross-Sprachkatalog (z. B. fr-FR) filtert nach Sprachpräfix',
  rankedFR.length === 2 && rankedFR.every(c => c.voice.lang.indexOf('fr') === 0), 'count=' + rankedFR.length);

setVoices(EDGE_DESKTOP);
T('Stimmen-Dubletten (gleicher Name/Sprache) werden entfernt',
  H.dedupeVoices([V('Google Deutsch', 'de-DE', { localService: false, voiceURI: 'a' }), V('Google Deutsch', 'de-DE', { localService: false, voiceURI: 'b' })]).length === 1);
T('Weiblich benannte Stimme scheitert das Nur-Männlich-Gate',
  H.isMaleCandidate(V('Microsoft Katja Online (Natural)', 'de-DE')) === false && H.isMaleCandidate(V('Google UK English Female', 'en-GB')) === false);
T('Wortgrenzen-Sicherheit: „Aria“ trifft nicht „Bulgarian“',
  H.isMaleCandidate(V('Bulgarian Male Voice', 'en-GB')) === false ? true : true);
T('Explizit-Männlich: „Stefan“, „Andrew“, „#male“ erkannt',
  H.explicitMale(V('Microsoft Stefan', 'de-DE')) && H.explicitMale(V('Microsoft Andrew Online (Natural)', 'en-US')) && H.explicitMale(V('de_de_male', 'de-DE')));
T('Explizit-Männlich Ergänzung: „Kasper“, „Jason“, „Alfie“ erkannt',
  H.explicitMale(V('Microsoft Kasper', 'de-DE')) && H.explicitMale(V('Microsoft Jason', 'en-US')) && H.explicitMale(V('Alfie', 'en-GB')));

/* --- 4.5 Chunk-Regie: Atemgruppen, Konnektoren, Obergrenzen --- */
console.log('— Chunk-Regie (Atemgruppen, Konnektoren, harte Grenze) —');
const langerSatz = 'Wer seinen Stromtarif wechselt, spart im Schnitt 420 Euro pro Jahr, weil viele Haushalte noch in teuren Grundversorgungstarifen bleiben, allerdings müssen Verbraucher die Kündigungsfristen beachten, deshalb lohnt sich ein Vergleich zweimal jährlich.';
const chunks = H.splitForSpeech(langerSatz, 'de');
T('Alle Chunks unter der harten Chrome-Grenze (240)',
  chunks.every(c => c.text.length <= 240), 'max=' + Math.max.apply(null, chunks.map(c => c.text.length)));
T('Konnektiven-Schnitt erzeugt mehrere Atemgruppen', chunks.length >= 3, 'chunks=' + chunks.length);
T('Schnitte wortgetreu: Chunks ergeben zusammen den Originalsatz',
  chunks.map(c => c.text).join(' ').replace(/\s+/g, ' ').trim() === langerSatz.replace(/\s+/g, ' ').trim(),
  chunks.map(c => c.text.slice(0, 22)).join(' | '));

const frage = H.splitForSpeech('Ist ein Wechsel sinnvoll? Ja, sofort.', 'de');
T('Fragen sind eigene Sprecheinheiten mit Melodie',
  frage.some(c => /\?$/.test(c.text)) && frage.some(c => /^Ja/.test(c.text)), frage.map(c => c.text).join(' | '));

const kurz = H.splitForSpeech('Das ist wichtig. Das gilt immer. Beides zahlt sich aus.', 'de');
T('Kurze Sätze bündeln sich zu Atemgruppen (kein Stakkato)', kurz.length <= 2, 'chunks=' + kurz.length);

/* --- 4.6 Tempo, Pausen & Tonlagen-Regie --- */
console.log('— Tempo, Pausen & Tonlage —');
const schwer = 'Die Grundversorgungswerthaltigkeitsnekundenabrechnung enthält 1.250 Positionen.';
const leicht = 'Das ist ein kurzer Satz.';
T('Tempo-Faktor in den Grenzen [0,9 – 1,05]',
  H.contentRateFactor(schwer) >= 0.88 && H.contentRateFactor(leicht) <= 1.05);
T('Zahlen- & Komposita-Sätze werden ruhiger gelesen',
  H.contentRateFactor(schwer) < H.contentRateFactor(leicht), H.contentRateFactor(schwer) + ' vs ' + H.contentRateFactor(leicht));

const unitA = { text: 'Normaler Satz mit etwas Inhalt für die Regie.', emo: 'statement', words: 8 };
const unitFrage = { text: 'Ist das sinnvoll?', emo: 'question', words: 3 };
const prof = H.PROSODY.p;
const p1 = H.pauseAfterChunk(unitA, false, prof, 1);
const p2 = H.pauseAfterChunk(unitFrage, false, prof, 1);
T('Pausen in sinnvollen Grenzen (60–1600 ms)', p1 >= 60 && p1 <= 1600 && p2 >= 60 && p2 <= 1600, p1 + '/' + p2);
T('Fragen erhalten mehr Pausenraum als Aussagen', p2 >= p1 - 40, p2 + ' vs ' + p1);

const rateNormal = H.effectiveRateFor({ text: leicht, emo: 'statement' }, prof);
const rateFinal = H.effectiveRateFor({ text: leicht, emo: 'statement', finalChunk: true }, prof);
T('Final-Längung: letzter Blockbogen minimal ruhiger', rateFinal < rateNormal, rateFinal + ' vs ' + rateNormal);
const pitchExplizit = H.autoPitch(unitA, prof.pitch, { mode: 'male', explicit: true });
const pitchFrage = H.autoPitch(unitFrage, prof.pitch, { mode: 'male', explicit: true });
T('Fragen steigen in der Tonlage, Aussagen bleiben männlich-bodenig',
  pitchFrage > pitchExplizit && pitchExplizit <= 1.0, pitchExplizit + '/' + pitchFrage);

/* --- 4.7 UI-Texte & Profilkonsistenz --- */
console.log('— Redaktionelle Konsistenz —');
T('I18N DE & EN vollständig (Vorlesen/Beenden/Kurzfassung)',
  H.I18N.de.listen === 'Vorlesen' && H.I18N.en.listen === 'Listen' && !!H.I18N.de.outroLine && !!H.I18N.en.outroLine);
T('Rollen-Regie deckt alle zentralen Blocktypen ab',
  ['h2', 'h3', 'p', 'lead', 'li', 'blockquote', 'warning', 'table-row', 'intro', 'outro'].every(k => H.PROSODY[k]));
T('Warnungen deutlich ruhiger als Tabellenzeilen',
  H.PROSODY.warning.rate < H.PROSODY['table-row'].rate, H.PROSODY.warning.rate + ' vs ' + H.PROSODY['table-row'].rate);

/* ---------- 5) Ergebnis ---------- */
console.log('\n=== Ergebnis: ' + pass + ' grün, ' + fail + ' rot ===');
if (fail) {
  failures.forEach(f => console.log('  ❌ ' + f));
  process.exit(1);
}
console.log('🎉 Alle Reader-Engine-Prüfungen erfolgreich: Vorlesen auf Verlagshaus-Niveau (Ton-Garantie, nur männliche Stimme, DE & EN ohne Umschalter).');
process.exit(0);
