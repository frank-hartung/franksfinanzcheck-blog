#!/usr/bin/env node
// ============================================================
//  READER-PLAYBACK-FUNCTION-TEST
//  Browser-nahe Funktionsprüfung der echten Vorlese-Engine:
//  Klick -> synchroner speak()-Aufruf, explizite DE/EN-Stimme,
//  automatischer Sprachwechsel ohne Umschalter und lazy Voice-Katalog.
//
//  Kein Audio kann in einer Node-VM physisch gehört werden. Der Test prüft
//  deshalb den vollständigen Web-Speech-Vertrag bis zum Audio-API-Aufruf:
//  Voice, Locale, Reihenfolge, Bedienzustand und Fallback-Verhalten.
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
    if (child && typeof child === 'object') {
      child.parentElement = this;
      child.parentNode = this;
      this.children.push(child);
    }
    return child;
  }
  removeChild(child) {
    const i = this.children.indexOf(child);
    if (i >= 0) this.children.splice(i, 1);
    return child;
  }
  addEventListener(type, handler) {
    (this.listeners[type] ||= []).push(handler);
  }
  dispatch(type, event = {}) {
    (this.listeners[type] || []).forEach((handler) => handler({ target: this, ...event }));
  }
  querySelector(selector) {
    if (selector === '.ff-reader-btn__icon') return this.icon || null;
    if (selector === '.ff-summary__close') return this.closeButton || null;
    return null;
  }
  querySelectorAll(selector) {
    if (selector.includes('ff-reader-toolbar')) return [];
    return [];
  }
  cloneNode() {
    const clone = new FakeNode(this.tagName, this.textContent);
    clone.attributes = { ...this.attributes };
    return clone;
  }
  closest() { return null; }
  contains(node) { return node === this || this.children.some((child) => child.contains(node)); }
  focus() { this.focused = true; }
  scrollIntoView() {}
}

function voice(name, lang, options = {}) {
  return Object.assign({
    name,
    lang,
    localService: true,
    default: false,
    voiceURI: `${name}|${lang}`
  }, options);
}

function createScenario(initialVoices) {
  const ids = {};
  const getById = (id) => (ids[id] ||= new FakeNode('div'));
  const config = getById('ff-reader-config');
  config.textContent = JSON.stringify({
    title: 'Stromtarif vergleichen und Geld sparen',
    description: 'Praktischer Ratgeber für den Tarifvergleich.',
    readingTime: '3',
    wordCount: '250',
    lang: 'de'
  });

  const toolbar = getById('ff-reader-toolbar');
  toolbar.parentElement = new FakeNode('div');
  toolbar.parentNode = toolbar.parentElement;
  const listen = getById('ff-listen-btn');
  const listenIcon = new FakeNode('span');
  listen.icon = listenIcon;
  getById('ff-listen-label').textContent = 'Vorlesen';
  const summary = getById('ff-summary-btn');
  const content = new FakeNode('div');
  content.innerText = [
    'Der Tarifvergleich zeigt, dass du mit einem Wechsel Geld sparst.',
    'This guide helps you compare tariffs and save 20 % with a better plan costing $50.',
    'Prüfe anschließend die Vertragslaufzeit und die Kündigungsfrist.'
  ].join(' ');
  content.textContent = content.innerText;
  const nodes = [
    new FakeNode('p', 'Der Tarifvergleich zeigt, dass du mit einem Wechsel Geld sparst.'),
    new FakeNode('p', 'This guide helps you compare tariffs and save 20 % with a better plan costing $50.'),
    new FakeNode('p', 'Prüfe anschließend die Vertragslaufzeit und die Kündigungsfrist.')
  ];
  nodes.forEach((node) => content.appendChild(node));
  content.querySelectorAll = (selector) => {
    if (/h2|h3|h4|p|li|blockquote|table|ff-table|ff-tarif|ff-einspar|ff-kurzantwort|ff-korrektur|callout/.test(selector)) return nodes;
    return [];
  };
  content.addEventListener('dblclick', () => {});
  content.addEventListener('click', () => {});

  const synth = {
    _voices: initialVoices.slice(),
    speakCalls: [],
    listeners: {},
    speaking: false,
    pending: false,
    paused: false,
    getVoices() { return this._voices.slice(); },
    addEventListener(type, handler) { (this.listeners[type] ||= []).push(handler); },
    emit(type) { (this.listeners[type] || []).forEach((handler) => handler()); },
    speak(utterance) {
      this.speakCalls.push(utterance);
      this.speaking = true;
      // Browser events are asynchronous; the initial call itself is still
      // made synchronously from the button click.
      if (utterance.onstart) utterance.onstart();
      setTimeout(() => {
        this.speaking = false;
        if (utterance.onend) utterance.onend();
      }, 1);
    },
    cancel() { this.speaking = false; this.pending = false; },
    pause() { this.paused = true; },
    resume() { this.paused = false; }
  };

  const navigator = { userAgent: 'ReaderPlaybackFunctionTest/1.0', hardwareConcurrency: 8 };
  const document = {
    getElementById: getById,
    querySelector(selector) {
      if (selector === '.post-content' || selector === '.md-content') return content;
      return null;
    },
    querySelectorAll() { return []; },
    createElement(tag) { return new FakeNode(tag); },
    addEventListener() {},
    body: { innerText: content.innerText, appendChild() {}, removeChild() {}, style: {} },
    documentElement: { lang: 'de', style: {} },
    scrollingElement: { style: {} },
    title: 'Testartikel'
  };
  const ctx = {
    console,
    setTimeout,
    clearTimeout,
    setInterval,
    clearInterval,
    Date,
    document,
    navigator,
    localStorage: {
      values: {},
      getItem(key) { return this.values[key] ?? null; },
      setItem(key, value) { this.values[key] = String(value); },
      removeItem(key) { delete this.values[key]; }
    },
    IntersectionObserver: function () { this.observe = () => {}; },
    matchMedia: () => ({ matches: false })
  };
  ctx.window = {
    location: { pathname: '/test-artikel/' },
    navigator,
    localStorage: ctx.localStorage,
    matchMedia: ctx.matchMedia,
    speechSynthesis: synth,
    SpeechSynthesisUtterance: function (text) {
      this.text = text;
      this.voice = null;
      this.lang = '';
      this.rate = 1;
      this.pitch = 1;
      this.volume = 1;
    },
    IntersectionObserver: ctx.IntersectionObserver,
    addEventListener() {}
  };
  vm.createContext(ctx);
  vm.runInContext(SRC, ctx, { filename: 'ff-reader.js' });
  return { ids, content, listen, synth };
}

function wait(ms) { return new Promise((resolve) => setTimeout(resolve, ms)); }
async function waitFor(predicate, timeout = 5000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (predicate()) return true;
    await wait(10);
  }
  return false;
}

const STEFAN = voice('Microsoft Stefan Online (Natural) - German (Germany)', 'de-DE', { localService: false, default: true });
const GUY = voice('Microsoft Guy Online (Natural) - English (United States)', 'en-US', { localService: false });
const KATJA = voice('Microsoft Katja Online (Natural) - German (Germany)', 'de-DE', { localService: false });
const ZIRA = voice('Microsoft Zira Desktop - English (United States)', 'en-US');

let pass = 0;
let fail = 0;
const failures = [];
function test(name, condition, detail = '') {
  if (condition) { pass += 1; console.log(`  ✅ ${name}`); }
  else { fail += 1; failures.push(`${name}${detail ? ` — ${detail}` : ''}`); console.log(`  ❌ ${name}${detail ? ` — ${detail}` : ''}`); }
}

(async () => {
  console.log('=== Reader Playback Function Test ===\n');
  console.log('— 1) Vollständiger DE/EN-Klickpfad —');
  const scenario = createScenario([KATJA, ZIRA, STEFAN, GUY]);
  const beforeClick = scenario.synth.speakCalls.length;
  scenario.listen.dispatch('click');
  test('Vorlesen startet direkt im Klickpfad', scenario.synth.speakCalls.length === beforeClick + 1);
  test('Erster Aufruf bindet männliche DE-Stimme explizit',
    scenario.synth.speakCalls[0] && scenario.synth.speakCalls[0].voice === STEFAN && scenario.synth.speakCalls[0].lang === 'de-DE');

  const finished = await waitFor(() => scenario.ids['ff-reader-status'].textContent === 'Vorlesen beendet.', 5000);
  test('Artikel läuft bis zum Ende ohne Abbruch', finished, scenario.ids['ff-reader-status'].textContent);
  const englishCall = scenario.synth.speakCalls.find((u) => /This guide/.test(u.text));
  test('Englischer Absatz wird automatisch erkannt', !!englishCall);
  test('Englischer Absatz nutzt männliche EN-Stimme ohne Umschalter',
    !!englishCall && englishCall.voice === GUY && englishCall.lang === 'en-US', englishCall && englishCall.lang);
  test('Englische Aussprache bleibt sprachrichtig normalisiert',
    !!englishCall && /percent/i.test(englishCall.text) && /Dollars/i.test(englishCall.text) && !/Prozent|Euro/i.test(englishCall.text), englishCall && englishCall.text);
  test('Weibliche Stimmen werden in keinem Aufruf verwendet',
    scenario.synth.speakCalls.every((u) => u.voice !== KATJA && u.voice !== ZIRA));
  test('Keine doppelte oder übersprungene Audio-Einheit', scenario.synth.speakCalls.length === 5,
    `Aufrufe=${scenario.synth.speakCalls.length}`);

  console.log('\n— 2) Lazy Voice-Katalog / Zero-Latency-Fallback —');
  const lazy = createScenario([]);
  lazy.listen.dispatch('click');
  test('Leerer Voice-Katalog blockiert den ersten speak()-Aufruf nicht', lazy.synth.speakCalls.length === 1);
  test('Fallback setzt die gewünschte DE-Locale statt eines zufälligen Sprachdefaults',
    lazy.synth.speakCalls[0] && lazy.synth.speakCalls[0].lang === 'de-DE');

  // Voice catalog arrives after the click, as on Chromium/Safari mobile.
  lazy.synth._voices = [STEFAN, KATJA, GUY, ZIRA];
  lazy.synth.emit('voiceschanged');
  const upgraded = await waitFor(() => lazy.synth.speakCalls.some((u) => u.voice === STEFAN), 2500);
  test('Nachträglich geladener Katalog wird übernommen', upgraded);
  test('Lazy-Katalog verwendet weiterhin ausschließlich männliche DE-Stimme',
    lazy.synth.speakCalls.filter((u) => u.lang === 'de-DE').every((u) => !u.voice || u.voice === STEFAN));

  console.log(`\n=== Ergebnis: ${pass} grün, ${fail} rot ===`);
  if (fail) {
    failures.forEach((failure) => console.log(`  ❌ ${failure}`));
    process.exitCode = 1;
  } else {
    console.log('🎉 Klickpfad, DE/EN-Routing, männliche Stimmbindung und Lazy-Katalog bestanden.');
  }
})();
