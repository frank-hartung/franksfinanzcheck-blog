#!/usr/bin/env node
// ============================================================
//  READER-V7-FUNCTION-TEST — Highend-Funktionstest v7
//  Prüft die Reparaturen & Erweiterungen der Vorlese-Engine auf
//  Verlagshaus-Niveau (Die Zeit als Maßstab):
//
//   1) Universelles Pause/Resume (kein stilles Safari-/Android-
//      Resume mehr): Pause = Cancel + Positions-Merken,
//      Resume = Neu-Sprechen der aktuellen Einheit.
//   2) Gehärteter Start-Watchdog: bricht eine langsam anlaufende
//      Stimme NICHT ab; feuert nur bei nachweislich stiller Engine.
//   3) Keep-Alive-Wache: kein Doppel-Speak während laufender Einheit.
//   4) ZEIT-Audioplayer (HTML5 <audio>): vorab vertonte Tonspur,
//      zeitbasierte Live-Markierung, Pause/Resume/Stop/Sprung,
//      sauberer Fallback auf Web Speech bei Ladefehler.
// ============================================================
'use strict';

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const SRC = fs.readFileSync(path.join(ROOT, 'static', 'premium', 'ff-reader.js'), 'utf8');

function makeClassList(initial) {
  const set = new Set(initial || []);
  return {
    add(...names) { names.forEach((n) => set.add(n)); },
    remove(...names) { names.forEach((n) => set.delete(n)); },
    toggle(name, force) {
      const on = force === undefined ? !set.has(name) : !!force;
      on ? set.add(name) : set.delete(name);
      return on;
    },
    contains(name) { return set.has(name); }
  };
}

class FakeNode {
  constructor(tagName, text, classes) {
    this.tagName = String(tagName || 'div').toUpperCase();
    this.textContent = text || '';
    this.innerText = this.textContent;
    this.children = [];
    this.parentElement = null;
    this.parentNode = null;
    this.style = {};
    this.classList = makeClassList(classes);
    this.attributes = {};
    this.listeners = {};
    this.offsetHeight = 60;
  }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key] === undefined ? null : this.attributes[key]; }
  appendChild(child) {
    if (child && typeof child === 'object') { child.parentElement = this; child.parentNode = this; this.children.push(child); }
    return child;
  }
  removeChild(child) {
    const i = this.children.indexOf(child);
    if (i >= 0) this.children.splice(i, 1);
    return child;
  }
  addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); }
  dispatch(type, event = {}) { (this.listeners[type] || []).forEach((handler) => handler({ target: this, ...event })); }
  querySelector(selector) {
    if (selector === '.ff-reader-btn__icon') return this.icon || null;
    if (selector === '.ff-summary__close') return this.closeButton || null;
    return null;
  }
  querySelectorAll() { return []; }
  cloneNode() { const c = new FakeNode(this.tagName, this.textContent); c.attributes = { ...this.attributes }; return c; }
  closest() { return null; }
  contains(node) { return node === this || this.children.some((child) => child.contains(node)); }
  focus() { this.focused = true; }
  scrollIntoView() {}
}

// FakeAudio: HTMLAudioElement-Ersatz für den ZEIT-Audioplayer.
class FakeAudio extends FakeNode {
  constructor() {
    super('audio');
    this.paused = true;
    this.currentTime = 0;
    this.duration = NaN;
    this.playCalls = 0;
    this.pauseCalls = 0;
  }
  play() {
    this.playCalls += 1;
    this.paused = false;
    if (Number.isNaN(this.duration)) this.duration = 30;
    this.dispatch('play');
    return undefined; // wie ältere Browser (kein Promise nötig)
  }
  pause() { this.pauseCalls += 1; this.paused = true; this.dispatch('pause'); }
}

function voice(name, lang, options = {}) {
  return Object.assign({ name, lang, localService: true, default: false, voiceURI: `${name}|${lang}` }, options);
}
const STEFAN = voice('Microsoft Stefan Online (Natural) - German (Germany)', 'de-DE', { localService: false, default: true });
const GUY = voice('Microsoft Guy Online (Natural) - English (United States)', 'en-US', { localService: false });
const KATJA = voice('Microsoft Katja Online (Natural) - German (Germany)', 'de-DE', { localService: false });

function createScenario(initialVoices, audioConfig, opts) {
  const ids = {};
  const getById = (id) => (ids[id] ||= new FakeNode('div'));
  const config = getById('ff-reader-config');
  const cfgJson = {
    title: 'Stromtarif vergleichen und Geld sparen',
    description: 'Praktischer Ratgeber für den Tarifvergleich.',
    readingTime: '3', wordCount: '250', lang: 'de'
  };
  if (audioConfig) {
    if (opts && opts.separateAudio) {
      // v7-Injektionspfad: eigenes <script id="ff-reader-audio-config">.
      getById('ff-reader-audio-config').textContent = JSON.stringify({ audio: audioConfig });
    } else {
      cfgJson.audio = audioConfig;
    }
  }
  config.textContent = JSON.stringify(cfgJson);

  const toolbar = getById('ff-reader-toolbar');
  toolbar.parentElement = new FakeNode('div');
  toolbar.parentNode = toolbar.parentElement;
  const listen = getById('ff-listen-btn');
  const listenIcon = new FakeNode('span');
  listen.icon = listenIcon;
  getById('ff-listen-label').textContent = 'Vorlesen';
  getById('ff-summary-btn');
  const content = new FakeNode('div');
  const p1 = new FakeNode('p', 'Der Tarifvergleich zeigt, dass du mit einem Wechsel Geld sparst.');
  const p2 = new FakeNode('p', 'Prüfe anschließend die Vertragslaufzeit und die Kündigungsfrist.');
  content.appendChild(p1); content.appendChild(p2);
  content.innerText = [p1.textContent, p2.textContent].join(' ');
  content.textContent = content.innerText;
  content.querySelectorAll = (selector) => (/h2|h3|h4|p|li|blockquote|table|ff-|callout/.test(selector) ? [p1, p2] : []);
  content.addEventListener('dblclick', () => {});
  content.addEventListener('click', () => {});

  const synth = {
    _voices: initialVoices.slice(),
    speakCalls: [], cancelCalls: 0, pauseCalls: 0, resumeCalls: 0,
    listeners: {}, speaking: false, pending: false, paused: false,
    autoStart: true,
    acceptsSpeech: true,
    getVoices() { return this._voices.slice(); },
    addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
    emit(type) { (this.listeners[type] || []).forEach((handler) => handler()); },
    speak(utterance) {
      this.speakCalls.push(utterance);
      // Real browser behavior: an accepted speak() marks the engine busy.
      if (this.acceptsSpeech !== false) this.speaking = true;
      if (this.autoStart) {
        if (utterance.onstart) utterance.onstart();
        setTimeout(() => { this.speaking = false; if (utterance.onend) utterance.onend(); }, 1);
      }
    },
    cancel() { this.cancelCalls += 1; this.speaking = false; this.pending = false; },
    pause() { this.pauseCalls += 1; this.paused = true; },
    resume() { this.resumeCalls += 1; this.paused = false; }
  };

  const audioEl = new FakeAudio();

  const navigator = { userAgent: 'ReaderV7FunctionTest/1.0', hardwareConcurrency: 8 };
  const document = {
    getElementById: getById,
    querySelector(selector) {
      if (selector === '.post-content' || selector === '.md-content') return content;
      return null;
    },
    querySelectorAll() { return []; },
    createElement(tag) { return tag === 'audio' ? audioEl : new FakeNode(tag); },
    addEventListener() {},
    body: { innerText: content.innerText, appendChild() {}, removeChild() {}, style: {} },
    documentElement: { lang: 'de', style: {} },
    scrollingElement: { style: {} },
    title: 'Testartikel'
  };
  const ctx = {
    console, setTimeout, clearTimeout, setInterval, clearInterval, Date,
    document, navigator,
    localStorage: { values: {}, getItem(k) { return this.values[k] ?? null; }, setItem(k, v) { this.values[k] = String(v); }, removeItem(k) { delete this.values[k]; } },
    IntersectionObserver: function () { this.observe = () => {}; },
    matchMedia: () => ({ matches: false })
  };
  ctx.window = {
    location: { pathname: '/test-artikel/' }, navigator, localStorage: ctx.localStorage,
    matchMedia: ctx.matchMedia, speechSynthesis: synth,
    SpeechSynthesisUtterance: function (text) { this.text = text; this.voice = null; this.lang = ''; this.rate = 1; this.pitch = 1; this.volume = 1; },
    IntersectionObserver: ctx.IntersectionObserver, addEventListener() {}
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx, { filename: 'ff-reader.js' });
  return { ids, content, listen, synth, audioEl };
}

function wait(ms) { return new Promise((r) => setTimeout(r, ms)); }
async function waitFor(predicate, timeout = 6000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) { if (predicate()) return true; await wait(15); }
  return false;
}

let pass = 0, fail = 0;
const failures = [];
function test(name, cond, detail = '') {
  if (cond) { pass += 1; console.log(`  ✅ ${name}`); }
  else { fail += 1; failures.push(name + (detail ? ` — ${detail}` : '')); console.log(`  ❌ ${name}${detail ? ` — ${detail}` : ''}`); }
}

(async () => {
  console.log('=== Reader v7 Funktionstest (Die-Zeit-Standard) ===\n');

  console.log('— 1) Universelles Pause/Resume (kein stilles Resume) —');
  const s = createScenario([STEFAN, KATJA, GUY]);
  s.listen.dispatch('click');
  test('Start: erster speak()-Aufruf im Klickpfad', s.synth.speakCalls.length === 1);
  const pauseBefore = s.synth.pauseCalls;
  const cancelBefore = s.synth.cancelCalls;
  s.listen.dispatch('click'); // pausieren
  test('Pause nutzt Cancel statt synth.pause()',
    s.synth.pauseCalls === pauseBefore && s.synth.cancelCalls === cancelBefore + 1,
    `pause=${s.synth.pauseCalls} cancel=${s.synth.cancelCalls}`);
  test('Pause invalidiert alte Callbacks & setzt Zustand', s.ids['ff-listen-label'].textContent === 'Weiterlesen');
  const callsAtPause = s.synth.speakCalls.length;
  const resumeBefore = s.synth.resumeCalls;
  s.listen.dispatch('click'); // fortsetzen
  test('Resume spricht die aktuelle Einheit neu (kein synth.resume())',
    s.synth.resumeCalls === resumeBefore && s.synth.speakCalls.length === callsAtPause + 1,
    `resume=${s.synth.resumeCalls} calls=${s.synth.speakCalls.length}`);
  test('Resume-Zustand wieder aktiv', s.ids['ff-listen-label'].textContent === 'Pausieren');

  console.log('\n— 1b) Tempo-synchrone gelbe Fortschrittsanzeige —');
  const progress = createScenario([STEFAN, KATJA, GUY]);
  progress.synth.autoStart = false; // keine Boundary-Events und kein automatisches Ende
  progress.listen.dispatch('click');
  const firstUtterance = progress.synth.speakCalls[0];
  if (firstUtterance && firstUtterance.onstart) firstUtterance.onstart();
  await wait(450);
  const progressWidth = progress.ids['ff-reader-progress-bar'].style.transform ? parseFloat(progress.ids['ff-reader-progress-bar'].style.transform.replace(/[^0-9.]/g, '')) : 0;
  test('Fortschrittsleiste läuft auch ohne Boundary-Events sichtbar mit',
    progressWidth > 0,
    `transform=${progress.ids['ff-reader-progress-bar'].style.transform || 'scaleX(0)'}`);
  test('Fortschritt nutzt das automatisch gesetzte Sprechtempo',
    firstUtterance && firstUtterance.rate > 0 && firstUtterance.rate !== 1,
    `rate=${firstUtterance && firstUtterance.rate}`);

  console.log('\n— 2) Gehärteter Start-Watchdog —');
  // 2a: Engine „schluckt“ speak() stumm (meldet weder onstart noch busy).
  const silent = createScenario([STEFAN, KATJA, GUY]);
  silent.synth.autoStart = false;       // kein onstart/onend
  silent.synth.acceptsSpeech = false;   // sprechend bleibt false
  silent.listen.dispatch('click');
  test('Stille Engine: erster Aufruf erfolgt', silent.synth.speakCalls.length === 1);
  const retried = await waitFor(() => silent.synth.speakCalls.length >= 2, 5000);
  test('Stille Engine wird nach Watchdog erneut angesprochen', retried, `calls=${silent.synth.speakCalls.length}`);

  // 2b: Engine arbeitet (speaking) aber onstart fehlt -> NICHT abbrechen.
  const busy = createScenario([STEFAN, KATJA, GUY]);
  busy.synth.autoStart = false;   // kein onstart, aber sprechend bleibt true
  busy.listen.dispatch('click');
  await wait(2700); // erster Watchdog-Zeitpunkt (2200 ms) überschritten
  test('Arbeitende Engine wird NICHT abgewürgt (kein Extra-Cancel, kein Doppel-Speak)',
    busy.synth.cancelCalls === 1 && busy.synth.speakCalls.length === 1,
    `cancel=${busy.synth.cancelCalls} calls=${busy.synth.speakCalls.length}`);

  console.log('\n— 3) ZEIT-Audioplayer (HTML5 <audio>, vorab vertont) —');
  const audioCfg = {
    src: '/audio/stromtarif-vergleichen.mp3',
    chunks: [
      { b: 0, t0: 0, t1: 5000, lang: 'de' },
      { b: 1, t0: 5000, t1: 15000, lang: 'de' },
      { b: 2, t0: 15000, t1: 30000, lang: 'de' }
    ]
  };
  const a = createScenario([STEFAN, KATJA, GUY], audioCfg);
  a.listen.dispatch('click');
  test('Audiomodus: HTML5-Player statt Web Speech genutzt', a.audioEl.playCalls === 1 && a.synth.speakCalls.length === 0);
  a.audioEl.currentTime = 6; a.audioEl.dispatch('timeupdate');
  test('Zeitbasierte Live-Markierung: Block 1 markiert', a.content.children[0].classList.contains('ff-reader-active'));
  a.listen.dispatch('click'); // pausieren
  test('Audio-Pause pausiert das <audio>-Element', a.audioEl.pauseCalls === 1 && a.audioEl.paused === true);
  a.listen.dispatch('click'); // fortsetzen
  test('Audio-Resume spielt das <audio>-Element weiter', a.audioEl.playCalls === 2);
  const jumpBtn = a.ids['ff-listen-next'];
  jumpBtn.dispatch('click'); // nächster Abschnitt (aktuell Block 1 -> Block 2)
  test('Abschnittssprung setzt currentTime an den Block-Anfang', a.audioEl.currentTime === 15);

  // Fehlerfall: Tonspur fehlt -> sauberer Fallback auf Web Speech.
  const broken = createScenario([STEFAN, KATJA, GUY], { src: '/audio/fehlt.mp3', chunks: [] });
  broken.listen.dispatch('click');
  broken.audioEl.dispatch('error');
  await waitFor(() => broken.synth.speakCalls.length >= 1, 3000);
  test('Audiopfehler fällt sauber auf Web Speech zurück', broken.synth.speakCalls.length >= 1);

  console.log('\n— 4) Injektionspfad: eigenes ff-reader-audio-config-Element —');
  const injected = createScenario([STEFAN, KATJA, GUY], audioCfg, { separateAudio: true });
  injected.listen.dispatch('click');
  test('Injizierte Tonspur wird erkannt → HTML5-Player (kein Web Speech)',
    injected.audioEl.playCalls === 1 && injected.synth.speakCalls.length === 0,
    `play=${injected.audioEl.playCalls} speak=${injected.synth.speakCalls.length}`);

  console.log(`\n=== Ergebnis: ${pass} grün, ${fail} rot ===`);
  if (fail) { failures.forEach((f) => console.log('  ❌ ' + f)); }
  else console.log('🎉 Vorlesen v7 auf Verlagshaus-Niveau (Die Zeit): universelles Pause/Resume, gehärteter Watchdog, ZEIT-Audioplayer bestanden.');
  // VM-Intervalle (Watchdog/KeepAlive) abschneiden, damit der Prozess sauber endet.
  process.exit(fail ? 1 : 0);
})();
