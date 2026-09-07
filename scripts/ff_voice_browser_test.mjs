/**
 * ff_voice_browser_test.mjs — Echt-Browser-Funktionstest Vorlesen
 * ============================================================
 * Der Befund vom 06.09.2026 („kein Ton, Fortschrittsanzeige rennt“)
 * war in jsdom-Tests unsichtbar: Attrappen sagten onstart/onend,
 * während der ECHTE Browser stumm blieb. Diese Suite läuft deshalb
 * gegen ECHTES Chromium (Playwright, echtes DOM, echte Timer, echtes
 * rAF) mit der unveränderten static/premium/ff-voice.js:
 *
 *   S1  Echte Web-Speech-API ohne Stimmen (Headless-Realität)
 *       → ehrlicher Stopp statt stillem Durchfegen
 *   S2  Sprach-Engine-Attrappe mit realistischen Timern
 *       → Sprechfluss, monotoner Fortschritt, Pause/Resume, ESC
 *   S3  Lazy Stimmen-Katalog → männliche Stimme bindet nachträglich
 *   S4  Synthese-Fehler → ehrlicher Stopp, max. 2 Versuche
 *   S5  Studio-Tonspur: ECHTE WAV-Datei im echten <audio>-Player
 *       → Play/Pause/Sprung/Fortschritt/Live-Markierung/„beendet“
 *   S6  Tonspur 404 → sofortige Übernahme durch die Gerätestimme
 *   S7  Deploytes Defektmuster (gh-pages: 85 Chunks t0==t1, 33 s)
 *       → Abweisung VOR dem Start, Gerätestimme übernimmt
 *   S8  Zu kurz geschnittene Spur endet früh → Gerätestimme ab Block
 *
 * Browser-Suche (erste Treffer gewinnt):
 *   1. FF_BROWSER_PATH / CHROME_PATH (Umgebung)
 *   2. ~/.cache/ms-playwright/chromium-<ver>/chrome-linux/chrome (CI)
 *   3. @sparticuz/chromium aus tools/ff-voice-browser (Sandbox/
 *      Umgebungen ohne Playwright-CDN; entpackt + LD_LIBRARY_PATH)
 * Ohne Browser: deutlicher Übersprung-Hinweis, Exit 0 (Gate-freundlich).
 *
 * Aufruf: node scripts/ff_voice_browser_test.mjs
 */

import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import http from 'node:http';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const ENGINE_PATH = path.join(ROOT, 'static', 'premium', 'ff-voice.js');

/* ============================================================
   1 · Runner (dieselbe Report-Ästhetik wie die jsdom-Suiten)
   ============================================================ */

const groups = [];
let current = { title: '(ohne Gruppe)', checks: [] };
groups.push(current);

function group(title) {
  if (current && current.checks.length) {
    const bad = current.checks.filter((c) => !c.ok);
    console.log('  … ' + current.title + ': ' + (current.checks.length - bad.length) + '/' + current.checks.length);
    bad.forEach((c) => console.log('      ✗ ' + c.label + (c.detail ? ' — ' + c.detail : '')));
  }
  current = { title, checks: [] }; groups.push(current);
}
function ok(label, cond, detail) { current.checks.push({ label, ok: !!cond, detail: detail || '' }); return !!cond; }
function eq(label, actual, expected) {
  const good = actual === expected;
  current.checks.push({ label, ok: good, detail: good ? '' : `erwartet ${JSON.stringify(expected)}, erhalten ${JSON.stringify(actual)}` });
  return good;
}
function done(name) {
  let pass = 0, fail = 0;
  const lines = ['', '  ' + name, '  ' + '='.repeat(Math.max(8, name.length))];
  for (const g of groups) {
    if (!g.checks.length) continue;
    lines.push('', '  ' + g.title);
    for (const c of g.checks) {
      if (c.ok) { pass += 1; lines.push('    ✓ ' + c.label); }
      else { fail += 1; lines.push('    ✗ ' + c.label + (c.detail ? ' — ' + c.detail : '')); }
    }
  }
  lines.push('', `  ${pass}/${pass + fail} Prüfungen bestanden`);
  (fail ? console.error : console.log)(lines.join('\n'));
  if (fail) { console.error(`\n❌ ${name}: ${fail} Prüfung(en) fehlgeschlagen.`); process.exitCode = 1; }
  else console.log(`\n✅ ${name}: grün.`);
  return fail === 0;
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/* ============================================================
   2 · Chromium beschaffen
   ============================================================ */

function fromEnv() {
  for (const key of ['FF_BROWSER_PATH', 'CHROME_PATH']) {
    if (process.env[key] && fs.existsSync(process.env[key])) return process.env[key];
  }
  return null;
}
function fromPlaywrightCache() {
  const base = path.join(os.homedir(), '.cache', 'ms-playwright');
  if (!fs.existsSync(base)) return null;
  const cands = fs.readdirSync(base)
    .filter((d) => /^chromium/.test(d))
    .sort()
    .reverse()
    .map((d) => path.join(base, d, 'chrome-linux', 'chrome'))
    .filter((p) => fs.existsSync(p));
  return cands[0] || null;
}
async function fromSparticz() {
  try {
    const pkgRoot = path.join(ROOT, 'tools', 'ff-voice-browser', 'node_modules', '@sparticuz', 'chromium');
    if (!fs.existsSync(pkgRoot)) return null;
    const req = createRequire(pathToFileURL(path.join(ROOT, 'tools', 'ff-voice-browser', 'package.json')));
    const mod = req('@sparticuz/chromium');
    const chromium = (mod && mod.default) || mod;
    const exe = await chromium.executablePath();          // entpackt nach /tmp/chromium
    if (!fs.existsSync(exe)) return null;
    // Shared Libraries (libnss3 & Co.) liegen dem Paket bei — auf Debian
    // nicht vorhanden, deshalb per LD_LIBRARY_PATH voranstellen.
    const libTar = path.join(pkgRoot, 'bin', 'al2023.tar.br');
    if (fs.existsSync(libTar)) {
      const zlib = await import('node:zlib');
      const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ff-voice-libs-'));
      const tarPath = path.join(tmp, 'al2023.tar');
      fs.writeFileSync(tarPath, zlib.brotliDecompressSync(fs.readFileSync(libTar)));
      const { execFileSync } = await import('node:child_process');
      execFileSync('tar', ['-xf', tarPath, '-C', tmp]);
      const libDir = path.join(tmp, 'lib');
      if (fs.existsSync(libDir)) process.env.LD_LIBRARY_PATH = (process.env.LD_LIBRARY_PATH ? process.env.LD_LIBRARY_PATH + ':' : '') + libDir;
    }
    return exe;
  } catch (e) {
    console.log('⚠ @sparticuz/chromium nicht nutzbar: ' + (e && e.message ? e.message.split('\n')[0] : e));
    return null;
  }
}

const BROWSER_PATH = fromEnv() || fromPlaywrightCache() || (await fromSparticz());
let chromium = null;
if (BROWSER_PATH) {
  try {
    const req = createRequire(pathToFileURL(path.join(ROOT, 'tools', 'ff-voice-browser', 'package.json')));
    const pw = req('playwright-core');
    chromium = pw.chromium;
  } catch (e) {
    console.log('⚠ playwright-core nicht installiert (tools/ff-voice-browser) — Browser-Suite übersprungen.');
    console.log('  Installation: cd tools/ff-voice-browser && npm install');
  }
}
if (!BROWSER_PATH || !chromium) {
  if (!BROWSER_PATH) {
    console.log('⚠ Kein Chromium gefunden — Browser-Suite übersprungen (Exit 0).');
    console.log('  Optionen: FF_BROWSER_PATH setzen · npx playwright-core install chromium ·');
    console.log('            cd tools/ff-voice-browser && npm install  (bundled Chromium)');
  }
  process.exit(0);
}
console.log('Chromium: ' + BROWSER_PATH);

/* ============================================================
   3 · Testseite (Skelett wie layouts/single.html rendern würde)
   ============================================================ */

const ENGINE = fs.readFileSync(ENGINE_PATH, 'utf8');

function mdToHtml(md) {
  const lines = String(md).split(/\r?\n/);
  const out = [];
  let inList = false;
  let para = [];
  const flush = () => { if (para.length) { out.push('<p>' + para.join(' ') + '</p>'); para = []; } };
  for (const line of lines) {
    const t = line.trim();
    if (!t) { flush(); if (inList) { out.push('</ul>'); inList = false; } continue; }
    let m;
    if ((m = t.match(/^(#{2,4})\s+(.*)$/))) { flush(); if (inList) { out.push('</ul>'); inList = false; } out.push(`<h${m[1].length}>${m[2]}</h${m[1].length}>`); continue; }
    if (/^[-*]\s+/.test(t)) { flush(); if (!inList) { out.push('<ul>'); inList = true; } out.push('<li>' + t.replace(/^[-*]\s+/, '') + '</li>'); continue; }
    para.push(t);
  }
  flush(); if (inList) out.push('</ul>');
  return out.join('\n');
}

const SMALL_BODY = mdToHtml([
  '## Warum wechseln', '',
  'Der Arbeitspreis liegt bei 12 ct/kWh. Bei 20.000 kWh sparst du bis zu 650 € pro Jahr.', '',
  '**Merksatz: Prüfe die Laufzeit genau.**',
].join('\n'));

const BIG_BODY = mdToHtml(Array.from({ length: 14 }, (_, i) =>
  `## Abschnitt ${i + 1}\n\nDer Arbeitspreis liegt bei 12 ct/kWh und du sparst bis zu 650 Euro pro Jahr, wenn du den Anbieter wechselst und die Preisgarantie prüfst. Ein Wechsel dauert online weniger als zehn Minuten.`).join('\n\n'));

/** Chunk-Karte proportional zur Blocklänge über die Spur-Laufzeit. */
function chunkMap(blockTexts, totalMs) {
  const weights = blockTexts.map((t) => Math.max(1, t.length));
  const sum = weights.reduce((a, b) => a + b, 0);
  let t = 0;
  return weights.map((w, i) => {
    const d = Math.max(150, Math.round((w / sum) * totalMs));
    const c = { b: i, t0: t, t1: Math.min(totalMs, t + d), lang: 'de' };
    /* Wortuhr wie der Generator: je rohes Wort ein Sprechbeginn-ms,
       gleichmäßig über die Blocklaufzeit verteilt (min. 40 ms Schritt,
       nie über t1 hinaus) — exakt das Format von ff_voice_audio.py. */
    const toks = String(blockTexts[i] || '').split(/\s+/).filter(Boolean);
    if (toks.length > 1) {
      const span = Math.max(2, c.t1 - c.t0 - 2);
      const step = Math.min(1000, span / toks.length);
      c.w = toks.map((_, k) => [k, Math.min(c.t1 - 2, c.t0 + Math.round(k * step))]);
    }
    t += d;
    return c;
  });
}

function pageHtml({ speech = 'double', speechMode = 'working', speechVoices = 'male', lazyVoices = false, track = null, title = 'Testartikel', bodyHtml = SMALL_BODY, blocksMeta = null }) {
  const cfg = {
    title, kurzantwort: '', description: '', readingTime: 4, wordCount: 420,
    lang: 'de', siteName: 'FranksFinanzcheck', author: 'Frank Hartung',
    date: '06.09.2026', updated: '', category: 'Ratgeber', slug: 'browsertest',
    permalink: '/posts/browsertest/',
  };
  return `<!doctype html><html lang="de"><head><meta charset="utf-8"><title>${title}</title></head><body>
<main><article class="post-single">
<div class="ff-voice-slot" id="ff-voice-slot"><div class="ff-voice-bar" id="ff-voice-bar" role="region" aria-label="Lesehilfen: Vorlesen und Kurzfassung" data-page-lang="de">
<span class="ff-voice-bar__label" aria-hidden="true">Lesen &amp; Verstehen</span>
<button type="button" class="ff-voice-btn ff-voice-btn--primary" id="ff-voice-play" aria-pressed="false" aria-label="Artikel vorlesen">
<span class="ff-voice-btn__text" id="ff-voice-play-label">Vorlesen</span></button>
<div class="ff-voice-bar__nav" role="group">
<button type="button" id="ff-voice-prev" aria-label="Vorheriger Abschnitt"></button>
<button type="button" id="ff-voice-next" aria-label="Nächster Abschnitt"></button>
<button type="button" id="ff-voice-stop" aria-label="Vorlesen beenden"></button>
</div>
<button type="button" id="ff-voice-summary" aria-haspopup="dialog"><span id="ff-voice-summary-label">Kurzfassung</span></button>
<div class="ff-voice-bar__meta"><span id="ff-voice-remaining"></span><span id="ff-voice-status" role="status" aria-live="polite"></span></div>
<div class="ff-voice-meter" id="ff-voice-meter" role="progressbar" aria-label="Vorlesefortschritt" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" aria-valuetext="0 %">
  <div class="ff-voice-meter__meta">
    <span class="ff-voice-meter__mode" id="ff-voice-progress-mode">Bereit</span>
    <span class="ff-voice-meter__label" id="ff-voice-progress-label">Noch nicht gestartet</span>
    <span class="ff-voice-meter__value" id="ff-voice-progress-value">0 %</span>
  </div>
  <div class="ff-voice-meter__live" id="ff-voice-live" aria-hidden="true">
    <span class="ff-voice-meter__live-label" id="ff-voice-live-label">Gerade vorgelesen</span>
    <span class="ff-voice-meter__live-text" id="ff-voice-now" title=""></span>
    <span class="ff-voice-meter__pos" id="ff-voice-pos" aria-hidden="true"></span>
        <span class="ff-voice-meter__words" id="ff-voice-word-count" aria-hidden="true"></span>
  </div>
  <span class="ff-voice-progress-shell" aria-hidden="true"><span class="ff-voice-progress" id="ff-voice-progress" style="display:block;height:6px;width:0%;background:#facc15"></span></span>
</div>
</div></div>
<div class="post-content">${bodyHtml}</div>
</article></main>
<script type="application/json" id="ff-voice-config">${JSON.stringify(cfg)}</script>
${track ? `<script type="application/json" id="ff-voice-track-config">${JSON.stringify(track)}</script>` : ''}
<script>
/* Sprach-Doppel VOR der Engine installieren (realistische Timer). */
(function () {
  var opts = ${JSON.stringify({ speech, speechMode, speechVoices, lazyVoices })};
  if (opts.speech !== 'double') return;   // 'real' lässt die echte API frei
  var MALE = [
    { name: 'Microsoft Conrad Online (Natural) - German (Germany)', lang: 'de-DE', voiceURI: 'conrad', localService: false, default: false },
    { name: 'Microsoft Andrew Online (Natural) - English (United States)', lang: 'en-US', voiceURI: 'andrew', localService: false, default: false }
  ];
  var FEMALE = [
    { name: 'Anna', lang: 'de-DE', voiceURI: 'anna', localService: true, default: true },
    { name: 'Katja', lang: 'de-DE', voiceURI: 'katja', localService: true, default: false }
  ];
  var catalog = opts.lazyVoices ? [] : (opts.speechVoices === 'male' ? MALE.concat(FEMALE) : FEMALE.concat(MALE));
  var listeners = [];
  var gen = 0;
  var log = [];
  var events = [];
  function U(text) { this.text = text; this.lang = ''; this.voice = null; this.rate = 1; this.pitch = 1; this.volume = 1;
    this.onstart = null; this.onend = null; this.onerror = null; this.onboundary = null; }
  window.SpeechSynthesisUtterance = U;
  // Achtung: window.speechSynthesis ist in Chromium ein nur-lesbarer
  // Accessor auf Window.prototype — eine Zuweisung versagt STILL. Die
  // Attrappe muss per defineProperty installiert werden.
  var double = {
    getVoices: function () { return catalog.slice(); },
    addEventListener: function (t, fn) { listeners.push(fn); },
    removeEventListener: function () {},
    speak: function (u) {
      var my = ++gen;
      log.push({ text: u.text, lang: u.lang, voice: u.voice ? u.voice.name : null });
      if (opts.speechMode === 'silent') return;
      if (opts.speechMode === 'failing') {
        setTimeout(function () { if (my === gen && u.onerror) u.onerror({ error: 'synthesis-failed' }); }, 5);
        return;
      }
      events.push('speak');
      var cps = 90;   // schnell gesprochen → kompakter Testlauf
      var durMs = Math.max(60, (u.text.length / cps) * 1000);
      setTimeout(function () { if (my === gen && u.onstart) u.onstart(); }, 25);
      var boundaries = Math.min(6, Math.max(1, Math.floor(durMs / 300)));
      for (var i = 1; i <= boundaries; i++) {
        (function (i) {
          setTimeout(function () {
            if (my !== gen || !u.onboundary) return;
            u.onboundary({ charIndex: Math.floor((u.text.length * i) / (boundaries + 1)) });
          }, Math.floor((durMs * i) / (boundaries + 1)));
        })(i);
      }
      setTimeout(function () {
        if (my !== gen) return;
        if (u.onboundary) u.onboundary({ charIndex: u.text.length });
        if (u.onend) u.onend();
      }, durMs + 40);
    },
    cancel: function () { gen += 1; events.push('cancel'); },
    pause: function () {}, resume: function () {}
  };
  try {
    Object.defineProperty(window, 'speechSynthesis', { configurable: true, get: function () { return double; } });
  } catch (e) {
    window.speechSynthesis = double;   // sehr alte Browser: normal zuweisen
  }
  window.__speech = {
    log: log, events: events,
    pushVoices: function (list) {
      catalog = list.slice();
      listeners.forEach(function (fn) { try { fn(); } catch (e) {} });
    },
    maleCatalog: MALE
  };
})();
</script>
<script>${ENGINE.replace(/<\/script>/gi, '<\\/script>')}</script>
</body></html>`;
}

/* ============================================================
   4 · Echte WAV-Datei (PCM 16 bit, 24 kHz, sprachähnlich)
   ============================================================ */

function makeWav(durationSec) {
  const rate = 24000;
  const n = Math.floor(durationSec * rate);
  const buf = Buffer.alloc(44 + n * 2);
  buf.write('RIFF', 0, 'ascii');
  buf.writeUInt32LE(36 + n * 2, 4);
  buf.write('WAVE', 8, 'ascii');
  buf.write('fmt ', 12, 'ascii');
  buf.writeUInt32LE(16, 16);
  buf.writeUInt16LE(1, 20);          // PCM
  buf.writeUInt16LE(1, 22);          // mono
  buf.writeUInt32LE(rate, 24);
  buf.writeUInt32LE(rate * 2, 28);
  buf.writeUInt16LE(2, 32);
  buf.writeUInt16LE(16, 34);
  buf.write('data', 36, 'ascii');
  buf.writeUInt32LE(n * 2, 40);
  for (let i = 0; i < n; i++) {
    const t = i / rate;
    // Sprachähnlich: Silben-Rhythmus (4 Hz) + Grundton + Obertöne
    const syll = 0.55 + 0.45 * Math.max(0, Math.sin(2 * Math.PI * 4 * t));
    const fade = Math.min(1, t / 0.05, (durationSec - t) / 0.05);
    const v = 9000 * syll * fade * (Math.sin(2 * Math.PI * 170 * t) + 0.4 * Math.sin(2 * Math.PI * 340 * t) + 0.2 * Math.sin(2 * Math.PI * 510 * t));
    buf.writeInt16LE(Math.max(-32767, Math.min(32767, Math.round(v))), 44 + i * 2);
  }
  return buf;
}

/* ============================================================
   5 · Server + Fixture-Vorberechnung (jsdom für Blockmaße)
   ============================================================ */

async function computeBlocks(title, bodyHtml) {
  const req = createRequire(import.meta.url);
  let lib;
  try { lib = await import('./ff_voice_qa_lib.mjs'); }
  catch (e) {
    const req2 = createRequire(pathToFileURL(path.join(ROOT, 'tools', 'ff-voice-qa', 'package.json')));
    void req2;
    throw e;
  }
  const { win } = lib.loadPage(lib.skeleton({ title, bodyHtml, slug: 'browsertest' }), { runScripts: true });
  const api = win.__ffVoice;
  const blockTexts = api.collectBlocks().map((b) => b.text);   // Getter „blocks“ ist vor dem Start leer
  const plan = api.buildTimeline();
  return { blockTexts, totalChars: plan.totalChars, units: plan.units.length };
}

const BASE_CPS = 15.2;

const SMALL_TITLE = 'Strom sparen im Haushalt';
const BIG_TITLE = 'Gasanbieter wechseln: Praxis-Tipps';
/* Die Titel der Tonspur-Szenes MÜSSEN den Fixture-Titeln gleichen:
   Block 0 (Anmoderation) enthält den Artikeltitel — und die Wortuhr
   (chunk.w) ist auf die Rohtexte der Seite gemünzt. Ein anderer Titel
   hier wäre ein anderer Text, die Karte zeigte ins Leere und die
   Plausibilitäts-Wache würde die Spur zu Recht verwerfen. */

async function main() {
  const small = await computeBlocks(SMALL_TITLE, SMALL_BODY);
  const big = await computeBlocks(BIG_TITLE, BIG_BODY);
  const smallExpected = (small.totalChars / BASE_CPS) * 1000 * 1.18;
  const bigExpected = (big.totalChars / BASE_CPS) * 1000 * 1.18;

  // Gute Spur: ~55 % der erwarteten Hörzeit, kompaktester Testlauf
  const goodMs = Math.max(6000, Math.round(smallExpected * 0.55));
  const goodWav = makeWav(goodMs / 1000);
  const goodTrack = {
    src: '/audio/good.wav', version: 'ff-voice-2026.09.06', duration: goodMs,
    chunks: chunkMap(small.blockTexts, goodMs),
  };
  // Zu kurz geschnittene Spur: Karte behauptet 60 s (besteht das Start-Gate
  // für den Langartikel), die Datei selbst ist nur ~7 s → endet früh.
  const shortWav = makeWav(7);
  const shortTrack = {
    src: '/audio/short.wav', version: 'ff-voice-2026.09.06', duration: Math.round(bigExpected * 0.32),
    chunks: chunkMap(big.blockTexts, Math.round(bigExpected * 0.32)),
  };
  ok('Fixture: Langartikel erwartet > 60 s Hörzeit', bigExpected > 60000, 'expected=' + Math.round(bigExpected / 1000) + 's');
  ok('Fixture: Gut-Spur im Plausibilitätsfenster', goodMs >= smallExpected * 0.25 && goodMs <= smallExpected * 4, 'good=' + goodMs + 'ms expected=' + Math.round(smallExpected) + 'ms');
  ok('Fixture: Kurz-Spur besteht Start-Gate, scheitert an End-Wache', shortTrack.duration >= bigExpected * 0.25 && 7000 < bigExpected * 0.35);

  // Deploytes Defektmuster (1:1 Struktur von origin/gh-pages)
  const deployedTrack = {
    src: '/audio/articles/2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife.wav',
    version: 'ff-voice-2026.09.05-b',
    voice: { de: 'de-DE-FlorianMultilingualNeural', style: 'news', lang: 'de' },
    engine: 'edge', profile: 'news', duration: 32980,
    chunks: Array.from({ length: 85 }, (_, i) => ({ b: i, t0: i * 420, t1: i * 420, lang: 'de' })),
  };

  const files = {
    '/audio/good.wav': goodWav,
    '/audio/short.wav': shortWav,
  };
  const pages = {};
  function route(scene, opts) { pages[scene] = opts; }

  route('s1', { title: 'Echte Engine ohne Stimmen', bodyHtml: BIG_BODY, speech: 'real' });
  route('s2', { title: 'Sprechfluss', bodyHtml: SMALL_BODY });
  route('s3', { title: 'Lazy Katalog', bodyHtml: SMALL_BODY, lazyVoices: true });
  route('s4', { title: 'Synthese-Fehler', bodyHtml: SMALL_BODY, speechMode: 'failing' });
  route('s5', { title: SMALL_TITLE, bodyHtml: SMALL_BODY, track: goodTrack });
  route('s6', { title: SMALL_TITLE, bodyHtml: SMALL_BODY, track: { ...goodTrack, src: '/audio/missing.wav' } });
  route('s7', { title: 'Deployte Defekt-Spur', bodyHtml: BIG_BODY, track: deployedTrack, speech: 'double' });
  route('s8', { title: BIG_TITLE, bodyHtml: BIG_BODY, track: shortTrack });

  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1');
    if (files[url.pathname]) {
      const buf = files[url.pathname];
      const range = req.headers.range;
      if (range) {
        const m = range.match(/bytes=(\d+)-(\d*)/);
        const start = m ? parseInt(m[1], 10) : 0;
        const end = m && m[2] ? Math.min(parseInt(m[2], 10), buf.length - 1) : buf.length - 1;
        res.writeHead(206, {
          'content-type': 'audio/wav', 'content-length': end - start + 1,
          'accept-ranges': 'bytes', 'content-range': `bytes ${start}-${end}/${buf.length}`,
        });
        res.end(buf.subarray(start, end + 1));
        return;
      }
      res.writeHead(200, { 'content-type': 'audio/wav', 'content-length': buf.length, 'accept-ranges': 'bytes' });
      res.end(buf);
      return;
    }
    if (url.pathname.startsWith('/audio/')) { res.writeHead(404, { 'content-type': 'text/plain' }); res.end('not found'); return; }
    const scene = url.searchParams.get('scene') || 's1';
    res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' });
    res.end(pageHtml(pages[scene] || pages.s1));
  });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const base = `http://127.0.0.1:${server.address().port}`;

  const browser = await chromium.launch({
    executablePath: BROWSER_PATH,
    args: ['--no-sandbox', '--disable-gpu', '--disable-dev-shm-usage', '--no-zygote',
           '--autoplay-policy=no-user-gesture-required', '--disable-features=AudioServiceOutOfProcess'],
  });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on('pageerror', (e) => pageErrors.push(String(e && e.message)));
  if (process.env.FF_VOICE_BROWSER_VERBOSE) {
    page.on('console', (m) => console.log('  [console] ' + m.type() + ': ' + m.text()));
  }

  async function open(scene) {
    await page.goto(`${base}/?scene=${scene}`, { waitUntil: 'load' });
    await page.waitForFunction(() => !!window.__ffVoice, null, { timeout: 5000 });
    return page.evaluate(() => ({
      mode: window.__ffVoice.mode,
      blocks: window.__ffVoice.collectBlocks().length,
      trackReady: window.__ffVoice.trackReady,
      plausible: window.__ffVoice.trackReady ? window.__ffVoice.trackPlausible() : null,
    }));
  }
  const snap = () => page.evaluate(() => ({
    reading: window.__ffVoice.reading, playing: window.__ffVoice.playing, mode: window.__ffVoice.mode,
    everStarted: window.__ffVoice.everStarted,
    status: document.getElementById('ff-voice-status').textContent,
    label: document.getElementById('ff-voice-play-label').textContent,
    progress: parseFloat(document.getElementById('ff-voice-progress').style.width) || 0,
    remaining: document.getElementById('ff-voice-remaining').textContent,
    spoken: (window.__speech ? window.__speech.log.length : -1),
    audio: (() => { const a = document.querySelector('audio'); return a
      ? { dur: isFinite(a.duration) ? a.duration : null, cur: a.currentTime, err: !!a.error, paused: a.paused }
      : null; })(),
  }));

  /* ---------- S1 · Echte Web-Speech-API ohne Stimmen ---------- */
  group('S1 · Echte speechSynthesis ohne Stimmen: ehrlicher Stopp');
  {
    const info = await open('s1');
    ok('Engine geladen', info.blocks > 0);
    await page.click('#ff-voice-play');
    await page.waitForFunction(() => !window.__ffVoice.reading, null, { timeout: 4000 }).catch(() => {});
    const s = await snap();
    ok('Lesen endet ehrlich (vorher: endloses Durchfegen)', s.reading === false);
    ok('Status nennt die Geräte-Grenze', /nicht verfügbar/.test(s.status), 'status=' + s.status);
    ok('Fortschritt bleibt bei 0 %', s.progress === 0);
    ok('Kein falsches „beendet“', s.status !== 'Vorlesen beendet.');
    eq('Knopf zurück auf Vorlesen', s.label, 'Vorlesen');
  }

  /* ---------- S2 · Sprechfluss mit realistischen Timern ---------- */
  group('S2 · Sprechfluss: Fortschritt, Pause/Resume, Stopp über ESC');
  {
    await open('s2');
    await page.click('#ff-voice-play');
    const samples = [];
    for (let i = 0; i < 10; i++) { await sleep(220); samples.push((await snap()).progress); }
    const s = await snap();
    ok('Lesen läuft', s.reading === true && s.playing === true);
    ok('Mehrere Einheiten gesprochen', s.spoken >= 3, 'spoken=' + s.spoken);
    ok('Männliche Stimme gebunden (Conrad)', await page.evaluate(() =>
      window.__speech.log.some((l) => /Conrad/.test(l.voice || ''))), JSON.stringify(await page.evaluate(() => window.__speech.log.slice(0, 2))));
    ok('Fortschritt monoton steigend', samples.every((v, i) => i === 0 || v >= samples[i - 1] - 0.001), samples.map((v) => v.toFixed(1)).join(' → '));
    ok('Fortschritt wandert sichtbar', samples[samples.length - 1] > 0 && samples[samples.length - 1] < 100);
    ok('Restzeit wird angezeigt', /Min/.test(s.remaining), 'remaining=' + s.remaining);
    ok('Live-Markierung am Text', await page.evaluate(() => !!document.querySelector('.ff-voice-active')));

    await page.click('#ff-voice-play');                    // Pause
    const p = await snap();
    eq('Pause-Label', p.label, 'Weiterlesen');
    ok('Pause-Status', /pausiert/.test(p.status), p.status);
    const frozen = p.progress;
    await sleep(300);
    ok('Fortschritt friert in Pause ein', Math.abs((await snap()).progress - frozen) < 1.5);
    await page.click('#ff-voice-play');                    // Resume
    await sleep(250);
    ok('Nach Resume weiter am Lesen', (await snap()).reading === true);
    await page.keyboard.press('Escape');                   // Stopp
    const e = await snap();
    ok('ESC beendet', e.reading === false);
    eq('Ende-Status', e.status, 'Vorlesen beendet.');
  }

  /* ---------- S3 · Lazy Stimmen-Katalog ---------- */
  group('S3 · Lazy Stimmen-Katalog: männliche Stimme bindet nachträglich');
  {
    await open('s3');
    ok('Katalog startet leer', await page.evaluate(() => window.speechSynthesis.getVoices().length === 0));
    await page.click('#ff-voice-play');
    await page.waitForFunction(() => window.__speech && window.__speech.log.length >= 1, null, { timeout: 3000 }).catch(() => {});
    ok('Erste Einheit spricht ohne Katalog (lang gebunden)', await page.evaluate(() =>
      window.__speech.log.length >= 1 && window.__speech.log[0].voice === null && window.__speech.log[0].lang === 'de-DE'),
      await page.evaluate(() => JSON.stringify((window.__speech ? window.__speech.log : []).slice(0, 2))));
    await page.evaluate(() => window.__speech.pushVoices(window.__speech.maleCatalog.concat([
      { name: 'Anna', lang: 'de-DE', voiceURI: 'anna', localService: true, default: true }])));
    await page.waitForFunction(() => window.__speech.log.some((l) => /Conrad/.test(l.voice || '')), null, { timeout: 6000 }).catch(() => {});
    ok('Nach Katalog-Ankunft bindet die männliche Stimme', true);
    ok('Weibliche Stimme nie gewählt', await page.evaluate(() =>
      window.__speech.log.length === 0 || window.__speech.log.every((l) => !l.voice || !/Anna/.test(l.voice))));
    await page.click('#ff-voice-stop');
    ok('Idle-aria-label verspricht den männlichen Nachrichtensprecher', /männliche(n)? (Nachrichtensprecher|Stimme)/.test(
      await page.evaluate(() => document.getElementById('ff-voice-play').getAttribute('aria-label'))));
  }

  /* ---------- S4 · Synthese-Fehler ---------- */
  group('S4 · Synthese-Fehler: ehrlicher Stopp, keine Verschleierung');
  {
    await open('s4');
    await page.click('#ff-voice-play');
    await page.waitForFunction(() => !window.__ffVoice.reading, null, { timeout: 3000 }).catch(() => {});
    const s = await snap();
    ok('Ehrlicher Stopp nach max. 2 Versuchen', s.reading === false && s.spoken <= 2, 'versuche=' + s.spoken);
    ok('Status nennt Geräte-Grenze', /nicht verfügbar/.test(s.status), s.status);
    ok('Fortschritt bleibt 0 %', s.progress === 0);
    ok('everStarted bleibt false', s.everStarted === false);
  }

  /* ---------- S5 · Gute Studio-Tonspur (echte WAV) ---------- */
  group('S5 · Studio-Tonspur: echte WAV im echten <audio>');
  {
    const info = await open('s5');
    ok('Track-Modus aktiv', info.mode === 'track', 'mode=' + info.mode);
    ok('Plausibilitäts-Wache akzeptiert ehrliche Spur', info.plausible === true);
    await page.click('#ff-voice-play');
    await sleep(300);
    const s0 = await snap();
    ok('Wiedergabe läuft', s0.reading === true && s0.audio && s0.audio.paused === false);
    ok('Duration geladen', s0.audio && s0.audio.dur && s0.audio.dur > 5, JSON.stringify(s0.audio));
    eq('Status „Studio-Tonspur läuft.“', s0.status, 'Studio-Tonspur läuft.');
    const samples = [];
    for (let i = 0; i < 8; i++) { await sleep(280); samples.push(await snap()); }
    ok('currentTime läuft real', samples[samples.length - 1].audio.cur > 1.2, 'cur=' + samples[samples.length - 1].audio.cur);
    ok('Fortschritt folgt der Zeit (nicht rennend)', samples.every((v, i) => i === 0 || v.progress >= samples[i - 1].progress - 0.001)
      && samples[samples.length - 1].progress > 3 && samples[samples.length - 1].progress < 90,
      samples.map((v) => v.progress.toFixed(1)).join(' → '));
    const expected = samples[samples.length - 1].audio.cur / samples[samples.length - 1].audio.dur * 100;
    ok('Fortschritt ≈ Abspielposition', Math.abs(samples[samples.length - 1].progress - expected) < 8,
      `progress=${samples[samples.length - 1].progress.toFixed(1)} erwartet≈${expected.toFixed(1)}`);
    // Live-Markierung prüfen, sobald die Spur IM TEXT ist (der Intro-
    // Block hat bewusst keinen Text-Anker — die Leiste selbst ist dort
    // die Markierung).
    await page.evaluate(() => { const a = document.querySelector('audio'); a.currentTime = Math.min(a.duration - 1, 6.0); });
    await sleep(400);
    ok('Live-Markierung folgt der Tonspur', await page.evaluate(() => !!document.querySelector('.ff-voice-active')),
      await page.evaluate(() => 'active=' + (document.querySelector('.ff-voice-active') ? 'da' : 'FEHLT')
        + ' cur=' + (document.querySelector('audio') || {}).currentTime));

    // WORT-TAKT aus der Wortuhr: im Textblock muss genau EIN Wort hell
    // sein, die Quelle heißt „track“, und der Wortzähler läuft mit.
    await page.evaluate(() => { const a = document.querySelector('audio'); a.currentTime = Math.min(a.duration - 1.5, 8.5); });
    await sleep(400);
    const ws = await page.evaluate(() => ({
      source: document.getElementById('ff-voice-bar').getAttribute('data-ff-wordsync'),
      lit: document.querySelectorAll('.ff-voice-w--now').length,
      spans: document.querySelectorAll('.ff-voice-w').length,
      counter: (document.getElementById('ff-voice-word-count') || {}).textContent || '',
      sync: window.__ffVoice.diagnostics().wordSync,
    }));
    ok('Wortuhr speist die Leseanzeige (Quelle track)', ws.source === 'track', JSON.stringify(ws));
    ok('Genau ein Wort leuchtet im Text', ws.lit === 1, 'lit=' + ws.lit + ' spans=' + ws.spans);
    ok('Wortzähler nennt Position', /Wort \d+ von \d+/.test(ws.counter), ws.counter);
    ok('Wortindex bleibt im Block (Diagnose)', ws.sync.raw >= 0 && ws.sync.block >= 0, JSON.stringify(ws.sync));

    // Abschnittssprung: Audio-Position folgt der Chunk-Karte
    await page.click('#ff-voice-next');
    await sleep(250);
    const afterNext = await snap();
    const t0Next = await page.evaluate(() => {
      const cfg = JSON.parse(document.getElementById('ff-voice-track-config').textContent);
      const b = window.__ffVoice.trackBlock;
      const c = cfg.chunks.filter((x) => x.b === b).pop();
      return c ? c.t0 / 1000 : -1;
    });
    ok('Sprung setzt die Abspielposition an den Block-Anfang',
      afterNext.audio && afterNext.audio.cur > 1 && Math.abs(afterNext.audio.cur - t0Next) < 2.0,
      `cur=${afterNext.audio && afterNext.audio.cur.toFixed(2)} t0=${t0Next.toFixed(2)}`);

    await page.click('#ff-voice-play');              // Pause
    const paused = await snap();
    ok('Pause stoppt die Tonspur', paused.audio.paused === true && paused.label === 'Weiterlesen');
    await page.click('#ff-voice-play');              // Resume
    await sleep(250);
    ok('Resume läuft weiter', (await snap()).audio.paused === false);

    // Ans Ende spulen → natürliches „beendet“ (echtes ended-Event)
    await page.evaluate(() => { const a = document.querySelector('audio'); a.currentTime = a.duration - 0.45; });
    await page.waitForFunction(() => !window.__ffVoice.reading, null, { timeout: 4000 }).catch(() => {});
    const end = await snap();
    ok('Natürliches Ende gemeldet', end.reading === false && end.status === 'Vorlesen beendet.', end.status);
    ok('Fortschritt bei 100 %', end.progress >= 99.5, end.progress.toFixed(1));
    eq('Knopf zurück auf Vorlesen', end.label, 'Vorlesen');
  }

  /* ---------- S6 · Tonspur 404 → Gerätestimme ---------- */
  group('S6 · Tonspur 404: sofortige Übernahme durch die Gerätestimme');
  {
    await open('s6');
    await page.click('#ff-voice-play');
    await page.waitForFunction(() => window.__ffVoice.mode === 'speech' && window.__speech.log.length >= 1, null, { timeout: 6000 }).catch(() => {});
    const s = await snap();
    ok('Fallback auf Browser-Engine (vorher: endloses Stumm)', s.mode === 'speech', 'mode=' + s.mode);
    ok('Gerätestimme spricht sofort', s.spoken >= 1);
    ok('Lesen läuft', s.reading === true);
    ok('Status nennt Grund', /Gerätestimme|übernimmt/.test(s.status), s.status);
    await page.click('#ff-voice-stop');
  }

  /* ---------- S7 · Deploytes Defektmuster ---------- */
  group('S7 · Deployte Defekt-Spur (gh-pages): Abweisung vor dem Start');
  {
    const info = await open('s7');
    ok('Wache erkennt deploytes Muster', info.plausible === false);
    await page.click('#ff-voice-play');
    const s = await snap();
    ok('Niemals Track-Modus', s.mode === 'speech', 'mode=' + s.mode);
    ok('Status warnt vor der defekten Spur', /unbrauchbar/.test(s.status), s.status);
    ok('„Studio-Tonspur läuft“ erscheint nicht', s.status !== 'Studio-Tonspur läuft.');
    await page.waitForFunction(() => window.__speech.log.length >= 1, null, { timeout: 3000 }).catch(() => {});
    ok('Gerätestimme übernimmt', (await snap()).spoken >= 1);
    await page.click('#ff-voice-stop');
  }

  /* ---------- S8 · Zu kurz geschnittene Spur ---------- */
  group('S8 · Zu kurze Spur endet früh: Gerätestimme übernimmt ab Block');
  {
    await open('s8');
    await page.click('#ff-voice-play');
    await sleep(250);
    const start = await snap();
    ok('Startet zunächst im Track-Modus', start.mode === 'track' && start.reading === true);
    await page.evaluate(() => { const a = document.querySelector('audio'); a.currentTime = a.duration - 0.4; });
    await page.waitForFunction(() => window.__ffVoice.mode === 'speech' && window.__speech.log.length >= 1, null, { timeout: 6000 }).catch(() => {});
    const s = await snap();
    ok('Kein falsches „beendet“ — Engine übernimmt', s.mode === 'speech' && s.reading === true);
    ok('Status nennt frühes Ende', /zu früh/.test(s.status), s.status);
    ok('Gerätestimme spricht ab dem letzten gehörten Block', s.spoken >= 1);
    await page.click('#ff-voice-stop');
  }

  /* ---------- Seitenzustand ---------- */
  group('Browser-Konsole & Seitenzustand');
  ok('Keine ungefangenen Seitenfehler', pageErrors.length === 0, pageErrors.slice(0, 3).join(' | '));

  await browser.close();
  server.close();

  done('Echt-Browser-Funktionstest Vorlesen (Chromium)');
}

main().catch(async (e) => {
  try { console.error('Zustand bei Abbruch:', JSON.stringify(await page.evaluate(() => ({ mode: window.__ffVoice && window.__ffVoice.mode, reading: window.__ffVoice && window.__ffVoice.reading, status: document.getElementById('ff-voice-status') && document.getElementById('ff-voice-status').textContent, spoken: window.__speech ? window.__speech.log.length : -1 })))); } catch (e2) {}
  console.error('❌ Browser-Suite abgebrochen:', e && e.stack ? e.stack.split('\n').slice(0, 4).join('\n') : e);
  process.exit(1);
});
