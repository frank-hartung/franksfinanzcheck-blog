/**
 * reader_qa_lib.mjs — Echte DOM-Prüfumgebung für die Premium-Lesehilfen.
 *
 * Warum diese Datei existiert:
 *   Die älteren Reader-Tests (reader_engine_check.js, reader_playback_function_test.js)
 *   bauen eine handgeschriebene `FakeNode`-DOM nach. Damit laufen sie nicht gegen
 *   echtes DOM-Verhalten (querySelector-Selektoren, closest(), <dialog>,
 *   Event-Bubbling, classList, scrollIntoView) und übersehen genau die Fehler,
 *   die im echten Browser sichtbar werden.
 *
 *   Diese Bibliothek startet jsdom, lädt die ECHTE Datei
 *   static/premium/ff-reader.js unverändert aus dem Repo und bettet sie in das
 *   ECHTE Seiten-Skelett aus layouts/single.html + layouts/_partials/reader_toolbar.html
 *   ein. Der Inhalt stammt aus echten Artikeln unter content/posts/.
 *
 *   Die Web-Speech-API ist in jsdom nicht vorhanden, deshalb ist hier eine
 *   spec-nahe Implementierung enthalten, die JEDEN speak()-Aufruf mit
 *   voice / lang / rate / pitch / volume / text aufzeichnet. Der Test prüft
 *   damit den vollständigen Vertrag bis unmittelbar vor die Audio-Ausgabe.
 *
 *   Nicht abgedeckt (und im Report ausdrücklich als nicht geprüft markiert):
 *   physisch hörbarer Ton, echtes Timbre einer Stimme, iOS-Autoplay-Regeln
 *   des realen WebKit, natives <dialog>-Rendering.
 */

import fs from 'node:fs';
import path from 'node:path';
import { renderShortcodes } from './hugo_shortcodes.mjs';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(HERE, '..');

/* jsdom lebt in tools/reader-qa/node_modules (devDependency, nicht im Repo).
   createRequire löst ab dort auf, damit dieser Test aus scripts/ lauffähig
   bleibt und `npm ci` nur im QA-Verzeichnis nötig ist. */
const qaRequire = createRequire(path.join(ROOT, 'tools', 'reader-qa', 'package.json'));
let JSDOM; let VirtualConsole;
try {
  ({ JSDOM, VirtualConsole } = qaRequire('jsdom'));
} catch (e) {
  console.error('jsdom fehlt. Bitte einmalig ausführen:  (cd tools/reader-qa && npm ci)');
  throw e;
}
export const READER_JS = path.join(ROOT, 'static', 'premium', 'ff-reader.js');
export const READER_CSS = path.join(ROOT, 'assets', 'css', 'extended', 'ff-reader.css');

/* ------------------------------------------------------------------ */
/* 1) Minimaler, deterministischer Markdown -> HTML Konverter          */
/*    (Fixture-Bau, NICHT die geprüfte Logik: ff-reader.js liest nur   */
/*    fertiges DOM. Unterstützt werden genau die Konstrukte, die in    */
/*    content/posts tatsächlich vorkommen.)                            */
/* ------------------------------------------------------------------ */

function esc(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/** Hugo/Goldmark-kompatible Slug-Bildung für Überschriften-IDs. */
export function hugoSlug(title) {
  return String(title)
    .toLowerCase()
    .replace(/[*_`]/g, '')
    .replace(/[äÄ]/g, 'ae').replace(/[öÖ]/g, 'oe').replace(/[üÜ]/g, 'ue').replace(/ß/g, 'ss')
    .replace(/[^\p{L}\p{N}\s-]/gu, '')
    .trim()
    .replace(/\s+/g, '-');
}

function inline(s) {
  let out = esc(s);
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
  out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
  out = out.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');
  return out;
}

function splitRow(line) {
  return line.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map((c) => c.trim());
}

export function markdownToHtml(md) {
  const lines = String(md).replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let i = 0;
  let para = [];
  let listStack = null; // { tag, indent }

  const flushPara = () => {
    if (para.length) {
      const first = para[0];
      const cls = /^>/.test(first) ? '' : '';
      out.push(`<p${cls}>${inline(para.join(' '))}</p>`);
      para = [];
    }
  };
  const closeList = () => { if (listStack) { out.push(`</${listStack.tag}>`); listStack = null; } };

  while (i < lines.length) {
    const raw = lines[i];
    const line = raw.trimEnd();

    if (!line.trim()) { flushPara(); closeList(); i++; continue; }

    // Tabelle
    if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1])) {
      flushPara(); closeList();
      const headers = splitRow(line);
      i += 2;
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) { rows.push(splitRow(lines[i])); i++; }
      let t = '<table><thead><tr>';
      headers.forEach((h) => { t += `<th>${inline(h)}</th>`; });
      t += '</tr></thead><tbody>';
      rows.forEach((r) => {
        t += '<tr>';
        r.forEach((c) => { t += `<td>${inline(c)}</td>`; });
        t += '</tr>';
      });
      t += '</tbody></table>';
      out.push(`<div class="ff-table-scroll">${t}</div>`);
      continue;
    }

    // Überschrift
    const h = line.match(/^(#{1,6})\s+(.*)$/);
    if (h) {
      flushPara(); closeList();
      const level = h[1].length;
      const title = h[2].trim();
      out.push(`<h${level} id="${hugoSlug(title)}">${inline(title)}</h${level}>`);
      i++; continue;
    }

    // Blockquote
    if (/^>\s?/.test(line)) {
      flushPara(); closeList();
      const buf = [];
      while (i < lines.length && /^>\s?/.test(lines[i].trimEnd())) {
        buf.push(lines[i].trimEnd().replace(/^>\s?/, '')); i++;
      }
      out.push(`<blockquote><p>${inline(buf.join(' '))}</p></blockquote>`);
      continue;
    }

    // Liste
    const ul = line.match(/^(\s*)[-*+]\s+(.*)$/);
    const ol = line.match(/^(\s*)(\d+)[.)]\s+(.*)$/);
    if (ul || ol) {
      flushPara();
      const tag = ul ? 'ul' : 'ol';
      if (!listStack || listStack.tag !== tag) { closeList(); out.push(`<${tag}>`); listStack = { tag }; }
      out.push(`<li>${inline(ul ? ul[2] : ol[3])}</li>`);
      i++; continue;
    }

    // Horizontal rule / Shortcodes überspringen
    if (/^\s*(-{3,}|\*{3,})\s*$/.test(line)) { flushPara(); closeList(); i++; continue; }
    if (/^\s*\{\{[<%]/.test(line)) { i++; continue; }

    closeList();
    para.push(line.trim());
    i++;
  }
  flushPara(); closeList();
  return out.join('\n');
}

/** Spiegelt layouts/_partials/sectioned_content.html (DOM-Budget-Chunks). */
export function sectionedContent(html) {
  if (!/<h2 id="[^"]+"/.test(html)) return html;
  const wrapped = html.replace(/(<h2 id="[^"]+"[^>]*>)/g, '</div><div class="ff-content-chunk">$1');
  return `<div class="ff-content-chunk">${wrapped}</div>`;
}

/* ------------------------------------------------------------------ */
/* 2) Echtes Seiten-Skelett aus den Layout-Dateien                     */
/* ------------------------------------------------------------------ */

/**
 * Baut die Artikelseite nach layouts/single.html.
 * Die statischen HTML-Bestandteile (Kurzantwort-Box, post-content,
 * ff-reader-slot, ff-reader-config) werden WORTGETREU aus den
 * Template-Dateien übernommen, damit der Test an der echten Vorlage hängt:
 * Ändert sich das Layout, schlägt extractLayoutFragments fehl.
 */
export function extractLayoutFragments() {
  const single = fs.readFileSync(path.join(ROOT, 'layouts', 'single.html'), 'utf8');
  const toolbar = fs.readFileSync(path.join(ROOT, 'layouts', '_partials', 'reader_toolbar.html'), 'utf8');

  const kurzantwort = single.match(/<div class="ff-kurzantwort"[\s\S]*?\n  <\/div>/);
  const toolbarDiv = toolbar.match(/<div class="ff-reader-slot">[\s\S]*?<\/div>\n<\/div>/);
  const configTag = toolbar.match(/<script type="application\/json" id="ff-reader-config">/);
  const scriptTag = toolbar.match(/<script defer src="[^>]*premium\/ff-reader\.js[^>]*"><\/script>/);

  return {
    single,
    toolbar,
    kurzantwortBlock: kurzantwort ? kurzantwort[0] : null,
    toolbarBlock: toolbarDiv ? toolbarDiv[0] : null,
    hasConfigTag: !!configTag,
    hasScriptTag: !!scriptTag,
    includesToolbarInSingle: /partial "reader_toolbar\.html"/.test(single)
  };
}

/**
 * Erzeugt die Toolbar + Config exakt wie reader_toolbar.html, nur mit
 * aufgelösten Hugo-Variablen.
 */
export function buildToolbarHtml(cfg) {
  const frag = extractLayoutFragments();
  if (!frag.toolbarBlock) throw new Error('reader_toolbar.html: ff-reader-slot nicht gefunden');
  return frag.toolbarBlock;
}

export function buildPage({ title, description, kurzantwort, readingTime, wordCount, lang = 'de', author = 'Frank Hartung', date = '03.09.2026', updated = '', category = 'Ratgeber', siteName = 'FranksFinanzcheck', bodyHtml, showKurzantwortBox = true, audio = '', audioMap = '' }) {
  const cfg = { title, kurzantwort: kurzantwort || '', description: description || '', readingTime, wordCount, lang, siteName, author, date, updated, category, audio, audioMap };

  /* Die Kurzantwort-Box wird WORTGETREU aus layouts/single.html geholt und
     nur um die Hugo-Aktionen aufgelöst. Ändert sich das Template, übernimmt
     der Test die Änderung automatisch – keine nachgebaute Kopie. */
  let kurzantwortBox = '';
  if (showKurzantwortBox && kurzantwort) {
    const raw = extractLayoutFragments().kurzantwortBlock || '';
    if (!raw) throw new Error('layouts/single.html: .ff-kurzantwort-Block nicht gefunden');
    kurzantwortBox = raw
      .replace(/\{\{-?\s*\/\*[\s\S]*?\*\/\s*-?\}\}/g, '')
      .replace(/\{\{\s*\.Params\.kurzantwort[^}]*\}\}/g, esc(kurzantwort))
      .replace(/\{\{\s*\.File\.UniqueID\s*\}\}/g, 'qa1')
      .replace(/\{\{[^}]*\}\}/g, '');
  }

  return `<!DOCTYPE html>
<html lang="${lang}" data-theme="light">
<head><meta charset="utf-8"><title>${esc(title)}</title></head>
<body>
<article class="post-single">
  <header class="post-header">
    <h1 class="post-title">${esc(title)}</h1>
    <div class="post-description">${esc(description || '')}</div>
  </header>
${kurzantwortBox}
${buildToolbarHtml(cfg)}
<script type="application/json" id="ff-reader-config">${JSON.stringify(cfg)}</script>
  <div class="post-content md-content">
${sectionedContent(bodyHtml)}
  </div>
</article>
</body>
</html>`;
}

/* ------------------------------------------------------------------ */
/* 3) Spec-nahe Web-Speech-Implementierung für jsdom                   */
/* ------------------------------------------------------------------ */

export const VOICE_CATALOGS = {
  /** macOS + Chrome: vollständiger Katalog inkl. männlicher DE/EN-Stimmen. */
  macChrome: [
    { name: 'Anna', lang: 'de-DE', localService: true },
    { name: 'Markus', lang: 'de-DE', localService: true },
    { name: 'Yannick', lang: 'de-DE', localService: true },
    { name: 'Google Deutsch', lang: 'de-DE', localService: false },
    { name: 'Samantha', lang: 'en-US', localService: true },
    { name: 'Alex', lang: 'en-US', localService: true },
    { name: 'Google US English', lang: 'en-US', localService: false },
    { name: 'Google UK English Male', lang: 'en-GB', localService: false },
    { name: 'Google UK English Female', lang: 'en-GB', localService: false }
  ],
  /** Chrome/Edge Windows: SAPI5 + (Edge) neuronale Stimmen. */
  winEdge: [
    { name: 'Microsoft Hedda Desktop - German (Germany)', lang: 'de-DE', localService: true },
    { name: 'Microsoft Stefan Desktop - German (Germany)', lang: 'de-DE', localService: true },
    { name: 'Microsoft Katja Online (Natural) - German (Germany)', lang: 'de-DE', localService: false },
    { name: 'Microsoft Conrad Online (Natural) - German (Germany)', lang: 'de-DE', localService: false },
    { name: 'Microsoft Killian Online (Natural) - German (Germany)', lang: 'de-DE', localService: false },
    { name: 'Microsoft Zira Desktop - English (United States)', lang: 'en-US', localService: true },
    { name: 'Microsoft David Desktop - English (United States)', lang: 'en-US', localService: true }
  ],
  /** Android/Chrome mit Google-TTS: genau EINE deutsche Stimme, kein Gender-Merkmal. */
  androidChrome: [
    { name: 'Google Deutsch', lang: 'de-DE', localService: false },
    { name: 'Google US English', lang: 'en-US', localService: false }
  ],
  /** iOS 17/18 Safari: Premium-Stimmen sind für Web Speech NICHT sichtbar. */
  iosSafari: [
    { name: 'Anna', lang: 'de-DE', localService: true },
    { name: 'Samantha', lang: 'en-US', localService: true }
  ],
  /** Linux/Firefox mit espeak: generische, namenlose Stimmen. */
  linuxFirefox: [
    { name: 'deutsch', lang: 'de-DE', localService: true },
    { name: 'english', lang: 'en-US', localService: true }
  ],
  femaleOnly: [
    { name: 'Katja', lang: 'de-DE', localService: true },
    { name: 'Anna', lang: 'de-DE', localService: true },
    { name: 'Zira', lang: 'en-US', localService: true }
  ],
  empty: []
};

export function installSpeechMock(win, { catalog = [], engine = 'chrome', msPerChar = 0.01 } = {}) {
  const log = [];
  let voices = catalog.map((v, idx) => Object.freeze({
    name: v.name,
    lang: v.lang,
    voiceURI: v.voiceURI || `${v.name}#${idx}`,
    localService: !!v.localService,
    default: idx === 0
  }));

  class SpeechSynthesisUtterance extends win.EventTarget {
    constructor(text) {
      super();
      this.text = text == null ? '' : String(text);
      this.lang = '';
      this.voice = null;
      this.volume = 1;
      this.rate = 1;
      this.pitch = 1;
      this.onstart = null; this.onend = null; this.onerror = null; this.onboundary = null; this.onpause = null; this.onresume = null;
    }
  }

  class SpeechSynthesisEvent extends win.Event {
    constructor(type, init = {}) { super(type, init); Object.assign(this, init); }
  }

  const synth = new win.EventTarget();
  const queue = [];
  let speaking = false;
  let paused = false;
  let pending = false;
  let current = null;
  let timer = null;

  function fire(u, type, extra) {
    const ev = new SpeechSynthesisEvent(type, extra || {});
    const handler = u[`on${type}`];
    if (typeof handler === 'function') handler.call(u, ev);
    u.dispatchEvent(ev);
  }

  let startedAt = 0;
  let remaining = 0;

  /* Spec-nah: pause() hält die laufende Utterance an (Restzeit merken),
     resume() setzt sie fort. Frühere Versionen warfen den Timer weg –
     dann feuerte onend nie und die Queue hing. Das wäre ein untreuer
     Mock gewesen und hätte einen echten Engine-Fehler verdeckt. */
  function armTimer(u, ms) {
    clearTimeout(timer);
    startedAt = Date.now();
    remaining = ms;
    timer = setTimeout(() => {
      if (current !== u || paused) return;
      if (u.onboundary) fire(u, 'boundary', { charIndex: Math.min(5, u.text.length), charLength: 5, elapsedTime: 1, name: 'word' });
      queue.shift();
      current = null;
      speaking = queue.length > 0;
      fire(u, 'end', { elapsedTime: 1 });
      pump();
    }, Math.max(1, ms));
  }

  function pump() {
    if (speaking || paused || !queue.length) return;
    current = queue[0];
    speaking = true;
    pending = false;
    const u = current;
    fire(u, 'start', { elapsedTime: 0 });
    armTimer(u, Math.round(u.text.length * msPerChar));
  }

  Object.defineProperties(synth, {
    speaking: { get: () => speaking },
    paused: { get: () => paused },
    pending: { get: () => pending }
  });

  synth.getVoices = () => voices.slice();
  synth.setCatalogForTest = (next) => {
    voices = (next || []).map((v, idx) => Object.freeze({
      name: v.name, lang: v.lang, voiceURI: v.voiceURI || `${v.name}#${idx}`,
      localService: !!v.localService, default: idx === 0
    }));
    synth.dispatchEvent(new win.Event('voiceschanged'));
  };

  synth.speak = (u) => {
    if (!(u instanceof SpeechSynthesisUtterance)) throw new TypeError('speak() erwartet eine SpeechSynthesisUtterance');
    log.push({
      text: u.text,
      lang: u.lang,
      voice: u.voice ? { name: u.voice.name, lang: u.voice.lang } : null,
      rate: u.rate,
      pitch: u.pitch,
      volume: u.volume,
      hadGesture: !!synth.__userGestureActive,
      stackDepth: synth.__callDepth || 0
    });
    pending = true;
    queue.push(u);
    pump();
  };

  synth.cancel = () => {
    const dropped = queue.splice(0, queue.length);
    const wasSpeaking = speaking;
    const cur = current;
    clearTimeout(timer);
    current = null;
    speaking = false;
    pending = false;
    if (wasSpeaking && cur) {
      if (engine === 'firefox') fire(cur, 'end', { elapsedTime: 0 });
      else fire(cur, 'error', { error: 'canceled', elapsedTime: 0 });
    } else {
      dropped.forEach((u) => fire(u, 'error', { error: 'canceled', elapsedTime: 0 }));
    }
  };

  synth.pause = () => {
    if (paused) return;
    paused = true;
    clearTimeout(timer);
    if (current) remaining = Math.max(1, remaining - (Date.now() - startedAt));
    if (current) fire(current, 'pause', { elapsedTime: 1 });
  };
  synth.resume = () => {
    if (!paused) return;
    paused = false;
    if (current) {
      const u = current;
      armTimer(u, remaining);
      fire(u, 'resume', { elapsedTime: 1 });
    } else {
      pump();
    }
  };

  win.SpeechSynthesisUtterance = SpeechSynthesisUtterance;
  win.speechSynthesis = synth;
  win.__speechLog = log;
  win.__speechEngine = synth;
  return { log, synth, SpeechSynthesisUtterance };
}

/* ------------------------------------------------------------------ */
/* 4) jsdom-Boot mit allen benötigten Browser-APIs                     */
/* ------------------------------------------------------------------ */

export async function createPage({ html, catalog = VOICE_CATALOGS.macChrome, engine = 'chrome', speech = true, darkMode = false, reducedMotion = false, userAgent, fastTimers = true, msPerChar = 0.01, audioDuration = 900 }) {
  const errors = [];
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', (e) => errors.push(String(e && e.message ? e.message : e)));
  virtualConsole.on('error', (...a) => errors.push(a.join(' ')));
  virtualConsole.on('warn', (...a) => errors.push('warn: ' + a.join(' ')));

  const dom = new JSDOM(html, {
    runScripts: 'outside-only',
    pretendToBeVisual: true,
    url: 'https://franksfinanzcheck.de/posts/test-artikel/',
    virtualConsole
  });
  const win = dom.window;

  // matchMedia
  win.matchMedia = (q) => ({
    matches: /prefers-reduced-motion/.test(q) ? reducedMotion : (/prefers-color-scheme:\s*dark/.test(q) ? darkMode : false),
    media: q,
    addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {},
    onchange: null
  });

  // IntersectionObserver: Toolbar ist sichtbar
  win.IntersectionObserver = class {
    constructor(cb) { this.cb = cb; }
    observe(el) { this.cb([{ isIntersecting: true, target: el }], this); }
    unobserve() {} disconnect() {} takeRecords() { return []; }
  };

  // scrollIntoView
  win.Element.prototype.scrollIntoView = function () { win.__scrolledTo = this; };
  win.scrollTo = () => {};

  // MediaSession / MediaMetadata
  win.MediaMetadata = class { constructor(d) { Object.assign(this, d); } };
  Object.defineProperty(win.navigator, 'mediaSession', {
    configurable: true,
    value: { metadata: null, playbackState: 'none', setActionHandler(name) { win.__mediaHandlers = win.__mediaHandlers || {}; win.__mediaHandlers[name] = true; } }
  });

  // Clipboard
  win.navigator.clipboard = { writeText: async () => { win.__copied = true; } };

  // <dialog>: jsdom unterstützt showModal je nach Version nur teilweise
  const doc = win.document;
  const origCreate = doc.createElement.bind(doc);
  doc.createElement = function (tag, opts) {
    const el = origCreate(tag, opts);
    const lower = String(tag).toLowerCase();

    /* <audio>: jsdom implementiert HTMLMediaElement nicht (play() wirft
       „Not implemented"). Hier eine spec-nahe Umsetzung mit laufender
       currentTime, damit Pause/Weiter/Sprung/Fortschritt pruefbar sind. */
    if (lower === 'audio') {
      let cur = 0;
      const dur = audioDuration;
      let isPaused = true;
      let ticker = null;
      /* readyState/paused/currentTime/duration sind in jsdom Getter-only –
         direktes Zuweisen wirft. Deshalb über defineProperty. */
      Object.defineProperty(el, 'readyState', { get: () => (el.getAttribute('src') ? 2 : 0), configurable: true });
      Object.defineProperty(el, 'currentTime', {
        get: () => cur,
        set: (v) => { cur = Math.max(0, Number(v) || 0); },
        configurable: true
      });
      Object.defineProperty(el, 'duration', { get: () => dur, configurable: true });
      Object.defineProperty(el, 'paused', { get: () => isPaused, configurable: true });
      const stopTicker = () => { if (ticker) { clearInterval(ticker); ticker = null; } };
      el.play = () => {
        if (!el.getAttribute('src')) {
          setTimeout(() => el.dispatchEvent(new win.Event('error')), 0);
          return Promise.resolve();
        }
        isPaused = false;
        setTimeout(() => el.dispatchEvent(new win.Event('play')), 0);
        stopTicker();
        ticker = setInterval(() => {
          cur += 0.25;
          el.dispatchEvent(new win.Event('timeupdate'));
          if (cur >= dur) {
            stopTicker();
            isPaused = true;
            el.dispatchEvent(new win.Event('ended'));
          }
        }, 5);
        return Promise.resolve();
      };
      el.pause = () => {
        if (isPaused) return;
        isPaused = true;
        stopTicker();
        el.dispatchEvent(new win.Event('pause'));
      };
      el.load = () => { stopTicker(); cur = 0; };
      // loadedmetadata feuern, sobald eine Quelle gesetzt wird
      const origSetAttr = el.setAttribute.bind(el);
      el.setAttribute = function (k, v) {
        origSetAttr(k, v);
        if (String(k).toLowerCase() === 'src') {
          setTimeout(() => el.dispatchEvent(new win.Event('loadedmetadata')), 0);
        }
      };
      win.__audioEl = el;
    }

    if (lower === 'dialog') {
      el.open = false;
      el.showModal = function () {
        if (el.open) throw new win.DOMException('already open', 'InvalidStateError');
        el.open = true;
        el.setAttribute('open', '');
        el.dispatchEvent(new win.Event('cancel'));
      };
      el.close = function () {
        if (!el.open) return;
        el.open = false;
        el.removeAttribute('open');
        el.dispatchEvent(new win.Event('close'));
      };
      el.addEventListener('keydown', () => {});
    }
    return el;
  };

  if (speech) installSpeechMock(win, { catalog, engine, msPerChar });
  if (userAgent) Object.defineProperty(win.navigator, 'userAgent', { configurable: true, value: userAgent });

  /* Redaktionelle Atempausen sind 100–600 ms lang. Damit ein ganzer Artikel
     im Test nicht Minuten läuft, werden Timeout-Verzögerungen gedeckelt.
     Reihenfolge und Logik bleiben unverändert – nur die Wartezeit schrumpft. */
  if (fastTimers) {
    const origSetTimeout = win.setTimeout.bind(win);
    win.setTimeout = (fn, ms, ...rest) => origSetTimeout(fn, Math.min(ms == null ? 0 : ms, 8), ...rest);
  }

  // Echte Engine-Datei laden und ausführen
  const src = fs.readFileSync(READER_JS, 'utf8');
  const runErr = [];
  try {
    win.eval(src);
  } catch (e) {
    runErr.push(String(e && e.stack ? e.stack : e));
  }

  return { dom, win, doc, errors: [...errors, ...runErr], log: win.__speechLog || [] };
}

/* ------------------------------------------------------------------ */
/* 5) Fixture: echte Artikel aus content/posts                         */
/* ------------------------------------------------------------------ */

export function loadArticle(slug) {
  const file = path.join(ROOT, 'content', 'posts', slug, 'index.md');
  const raw = fs.readFileSync(file, 'utf8');
  const m = raw.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  if (!m) throw new Error('Kein Frontmatter in ' + file);
  const fm = m[1];
  const body = m[2];
  const get = (key) => {
    const r = fm.match(new RegExp('^' + key + ':\\s*(.*)$', 'm'));
    if (!r) return '';
    return r[1].trim().replace(/^"|"$/g, '');
  };
  const words = body.split(/\s+/).filter(Boolean).length;
  return {
    slug,
    title: get('title'),
    description: get('description'),
    kurzantwort: get('kurzantwort'),
    author: get('author') || 'Frank Hartung',
    readingTime: Math.max(1, Math.round(words / 200)),
    wordCount: words,
    /* Shortcodes vor dem Markdown-Durchlauf rendern: Ohne Hugo würden
       ihre Parameter („title=", „cta_url=“) wörtlich vorgelesen. */
    bodyHtml: markdownToHtml(renderShortcodes(body))
  };
}

export function listArticleSlugs() {
  const dir = path.join(ROOT, 'content', 'posts');
  return fs.readdirSync(dir).filter((d) => {
    try { return fs.statSync(path.join(dir, d)).isDirectory(); } catch { return false; }
  }).sort();
}

/* ------------------------------------------------------------------ */
/* 6) Winziger Test-Runner                                             */
/* ------------------------------------------------------------------ */

export function createRunner(label) {
  const results = [];
  let group = '';
  const api = {
    group(name) { group = name; results.push({ group: name }); },
    ok(cond, name, detail) {
      results.push({ pass: !!cond, name, detail: cond ? '' : (detail || ''), group });
      if (cond) { console.log(`  \u2705 ${name}`); }
      else { console.log(`  \u274c ${name}${detail ? '\n     \u2192 ' + detail : ''}`); api.failures.push({ group, name, detail: detail || '' }); }
    },
    eq(actual, expected, name) {
      const pass = JSON.stringify(actual) === JSON.stringify(expected);
      api.ok(pass, name, pass ? '' : `erwartet ${JSON.stringify(expected)}, erhalten ${JSON.stringify(actual)}`);
    },
    failures: [],
    results,
    report() {
      let pass = 0; let fail = 0;
      for (const r of results) {
        if (r.group && r.pass === undefined) continue;
        if (r.pass) pass++; else fail++;
      }
      console.log(`\n=== ${label} — Ergebnis: ${pass} grün, ${fail} rot ===`);
      if (fail) {
        console.log('\nFehlgeschlagene Prüfungen:');
        api.failures.forEach((f) => console.log(`  ❌ [${f.group}] ${f.name}${f.detail ? ' → ' + f.detail : ''}`));
      }
      return fail;
    }
  };
  return api;
}

/** Wartet, bis eine Bedingung erfüllt ist (max. timeout ms). */
export async function until(fn, timeout = 4000, step = 5) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (fn()) return true;
    await new Promise((r) => setTimeout(r, step));
  }
  return fn();
}
