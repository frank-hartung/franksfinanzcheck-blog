/**
 * ff_voice_qa_lib.mjs — Gemeinsames Fundament der Lesehilfen-Tests.
 * ------------------------------------------------------------
 * Warum eine eigene QA-Bibliothek?
 *   Die alten Suiten liefen gegen eine handgebaute Fake-DOM und waren
 *   grün, obwohl die Funktion im Browser sichtbar fehlerhaft war.
 *   Diese Bibliothek lädt stattdessen:
 *     · eine ECHTE DOM (jsdom),
 *     · das UNVERÄNDERTE static/premium/ff-voice.js,
 *     · das echte Seiten-Skelett (wie layouts/single.html es rendert),
 *     · echten Inhalt aus content/posts.
 *
 *   Nur was hier grün ist, ist im Browser grün.
 */

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
export const ROOT = path.resolve(HERE, '..');
export const ENGINE_PATH = path.join(ROOT, 'static', 'premium', 'ff-voice.js');

/**
 * jsdom liegt in tools/ff-voice-qa/node_modules (die Repo-Wurzel hält
 * bewusst keine Node-Abhängigkeiten). Von `scripts/` aus findet die
 * normale Auflösung es nicht – deshalb dieser Fallback.
 */
function loadJsdom() {
  try {
    return createRequire(import.meta.url)('jsdom');
  } catch (e) {
    return createRequire(pathToFileURL(path.join(ROOT, 'tools', 'ff-voice-qa', 'package.json')))('jsdom');
  }
}
const { JSDOM, VirtualConsole } = loadJsdom();

/* ============================================================
   1 · Test-Runner
   ============================================================ */

export function createRunner(name) {
  const groups = [];
  let current = { title: '(ohne Gruppe)', checks: [] };
  groups.push(current);
  const runner = {
    group(title) {
      current = { title, checks: [] };
      groups.push(current);
    },
    ok(label, cond, detail) {
      current.checks.push({ label, ok: !!cond, detail: detail || '' });
      return !!cond;
    },
    eq(label, actual, expected) {
      const ok = actual === expected;
      current.checks.push({
        label, ok,
        detail: ok ? '' : `erwartet ${JSON.stringify(expected)}, erhalten ${JSON.stringify(actual)}`,
      });
      return ok;
    },
    done() {
      let pass = 0;
      let fail = 0;
      const lines = [];
      lines.push('');
      lines.push('  ' + name);
      lines.push('  ' + '='.repeat(Math.max(8, name.length)));
      for (const g of groups) {
        if (!g.checks.length) continue;
        const bad = g.checks.filter((c) => !c.ok);
        lines.push('');
        lines.push('  ' + g.title);
        for (const c of g.checks) {
          if (c.ok) { pass += 1; lines.push('    ✓ ' + c.label); }
          else { fail += 1; lines.push('    ✗ ' + c.label + (c.detail ? ' — ' + c.detail : '')); }
        }
      }
      lines.push('');
      lines.push(`  ${pass}/${pass + fail} Prüfungen bestanden`);
      const out = fail ? console.error : console.log;
      out(lines.join('\n'));
      if (fail) {
        console.error(`\n❌ ${name}: ${fail} Prüfung(en) fehlgeschlagen.`);
        process.exitCode = 1;
      } else {
        console.log(`\n✅ ${name}: grün.`);
      }
      return fail === 0;
    },
  };
  return runner;
}

/* ============================================================
   2 · Minimaler Markdown-Renderer (nur was die Artikel nutzen)
   ============================================================ */

export function mdToHtml(md) {
  const lines = String(md || '').split(/\r?\n/);
  const out = [];
  let inList = null;
  let inQuote = false;
  let paragraph = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    out.push('<p>' + inline(paragraph.join(' ').trim()) + '</p>');
    paragraph = [];
  };
  const closeList = () => {
    if (inList) { out.push('</' + inList + '>'); inList = null; }
  };
  const closeQuote = () => {
    if (inQuote) { out.push('</blockquote>'); inQuote = false; }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) { flushParagraph(); closeList(); closeQuote(); continue; }
    if (/^(---|\*\*\*|___)$/.test(trimmed)) { flushParagraph(); closeList(); closeQuote(); continue; }

    // Pipe-Tabellen
    if (/^\|/.test(trimmed) && i + 1 < lines.length && /^\|[\s:|-]+\|$/.test(lines[i + 1].trim())) {
      flushParagraph(); closeList(); closeQuote();
      const header = splitRow(trimmed);
      i += 2;
      const rows = [];
      while (i < lines.length && /^\|/.test(lines[i].trim())) {
        rows.push(splitRow(lines[i].trim()));
        i += 1;
      }
      i -= 1;
      out.push('<table><thead><tr>' + header.map((h) => `<th>${inline(h)}</th>`).join('') + '</tr></thead>');
      out.push('<tbody>' + rows.map((r) => '<tr>' + r.map((c) => `<td>${inline(c)}</td>`).join('') + '</tr>').join('') + '</tbody></table>');
      continue;
    }

    let m;
    if ((m = trimmed.match(/^(#{2,6})\s+(.*)$/))) {
      flushParagraph(); closeList(); closeQuote();
      const level = m[1].length;
      const text = inline(m[2]);
      const id = slugify(stripTags(text));
      out.push(`<h${level} id="${id}">${text}</h${level}>`);
      continue;
    }
    if (/^>\s?/.test(trimmed)) {
      flushParagraph(); closeList();
      if (!inQuote) { out.push('<blockquote>'); inQuote = true; }
      out.push('<p>' + inline(trimmed.replace(/^>\s?/, '')) + '</p>');
      continue;
    }
    if ((m = trimmed.match(/^[-*]\s+(.*)$/))) {
      flushParagraph(); closeQuote();
      if (inList !== 'ul') { closeList(); out.push('<ul>'); inList = 'ul'; }
      out.push('<li>' + inline(m[1]) + '</li>');
      continue;
    }
    if ((m = trimmed.match(/^\d+\.\s+(.*)$/))) {
      flushParagraph(); closeQuote();
      if (inList !== 'ol') { closeList(); out.push('<ol>'); inList = 'ol'; }
      out.push('<li>' + inline(m[1]) + '</li>');
      continue;
    }
    closeList(); closeQuote();
    paragraph.push(trimmed);
  }
  flushParagraph(); closeList(); closeQuote();
  return out.join('\n');
}

function splitRow(row) {
  return row.replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
}
function stripTags(s) { return String(s).replace(/<[^>]*>/g, ''); }
function slugify(s) {
  return String(s).toLowerCase().replace(/[^\wäöüß-]+/g, '-').replace(/^-+|-+$/g, '');
}
function inline(text) {
  let t = String(text);
  t = t.replace(/!\[([^\]]*)\]\([^)]*\)/g, '$1');
  t = t.replace(/\[([^\]]+)\]\([^)]*\)/g, '<a href="#">$1</a>');
  t = t.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  t = t.replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>');
  t = t.replace(/`([^`]+)`/g, '<code>$1</code>');
  return t;
}

/* ============================================================
   3 · Frontmatter & Artikel lesen
   ============================================================ */

export function parseFrontmatter(md) {
  const m = String(md).match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/);
  if (!m) return { data: {}, body: String(md) };
  const data = {};
  let key = null;
  for (const raw of m[1].split(/\r?\n/)) {
    const kv = raw.match(/^([A-Za-z0-9_]+):\s*(.*)$/);
    if (kv) {
      key = kv[1];
      let value = kv[2].trim();
      if (/^".*"$/.test(value) || /^'.*'$/.test(value)) value = value.slice(1, -1);
      data[key] = value;
    } else if (key && /^\s+/.test(raw)) {
      data[key] += ' ' + raw.trim();
    }
  }
  return { data, body: m[2] || '' };
}

export function listArticles() {
  const dirs = ['content/posts', 'content/pillar'];
  const found = [];
  for (const dir of dirs) {
    const abs = path.join(ROOT, dir);
    if (!fs.existsSync(abs)) continue;
    for (const entry of fs.readdirSync(abs, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const file = path.join(abs, entry.name, 'index.md');
      if (!fs.existsSync(file)) continue;
      const raw = fs.readFileSync(file, 'utf8');
      const { data, body } = parseFrontmatter(raw);
      if (data.draft === 'true') continue;
      found.push({ slug: entry.name, file, data, body });
    }
  }
  return found;
}

/* ============================================================
   4 · Seite bauen (Skelett wie layouts/single.html)
   ============================================================ */

/* Die Toolbar entspricht 1:1 dem Markup aus
   layouts/_partials/ff_voice_toolbar.html. ff_voice_toolbar_check.py
   überwacht, dass beide nicht auseinanderlaufen. */
export function toolbarHtml(lang) {
  return `
<div class="ff-voice-slot" id="ff-voice-slot">
  <div class="ff-voice-bar" id="ff-voice-bar" role="region" aria-label="Lesehilfen: Vorlesen und Kurzfassung" data-page-lang="${lang || 'de'}">
    <span class="ff-voice-bar__label" aria-hidden="true">Lesen &amp; Verstehen</span>

    <button type="button" class="ff-voice-btn ff-voice-btn--primary" id="ff-voice-play" aria-pressed="false" aria-label="Artikel vorlesen">
      <span class="ff-voice-btn__icon" aria-hidden="true">
        <svg class="ff-voice-ico ff-voice-ico--play"></svg>
        <svg class="ff-voice-ico ff-voice-ico--pause"></svg>
      </span>
      <span class="ff-voice-btn__text" id="ff-voice-play-label">Vorlesen</span>
    </button>

    <div class="ff-voice-bar__nav" role="group" aria-label="Abschnittsnavigation beim Vorlesen">
      <button type="button" class="ff-voice-btn ff-voice-btn--icon" id="ff-voice-prev" aria-label="Vorheriger Abschnitt"></button>
      <button type="button" class="ff-voice-btn ff-voice-btn--icon" id="ff-voice-next" aria-label="Nächster Abschnitt"></button>
      <button type="button" class="ff-voice-btn ff-voice-btn--icon" id="ff-voice-stop" aria-label="Vorlesen beenden"></button>
    </div>

    <button type="button" class="ff-voice-btn ff-voice-btn--summary" id="ff-voice-summary" aria-haspopup="dialog" aria-label="Kurzfassung des Artikels anzeigen">
      <span class="ff-voice-btn__icon" aria-hidden="true"></span>
      <span class="ff-voice-btn__text" id="ff-voice-summary-label">Kurzfassung</span>
    </button>

    <div class="ff-voice-bar__meta">
      <span class="ff-voice-bar__remaining" id="ff-voice-remaining" aria-hidden="true"></span>
      <span class="ff-voice-bar__status" id="ff-voice-status" role="status" aria-live="polite"></span>
    </div>

    <span class="ff-voice-progress" aria-hidden="true"><span class="ff-voice-progress__bar" id="ff-voice-progress"></span></span>
  </div>
</div>`;
}

/**
 * Ergänzt eine Seiten-HTML um die Toolbar, falls sie fehlt (Fixtures und
 * echte Seiten tragen sie unterschiedlich bei).
 */
export function ensureToolbar(html, lang) {
  if (/id="ff-voice-bar"/.test(html)) return html;
  if (/<\/body>/i.test(html)) {
    return html.replace(/<\/body>/i, toolbarHtml(lang) + '\n</body>');
  }
  return html + toolbarHtml(lang);
}

export function skeleton({ title, description, kurzantwort, lang, readingTime, wordCount,
  author, date, updated, category, slug, bodyHtml, korrektur, track, hideToolbar }) {
  const cfg = {
    title: title || 'Testartikel',
    kurzantwort: kurzantwort || '',
    description: description || '',
    readingTime: readingTime == null ? 5 : readingTime,
    wordCount: wordCount == null ? 900 : wordCount,
    lang: lang || 'de',
    siteName: 'FranksFinanzcheck',
    author: author || 'Frank Hartung',
    date: date || '05.09.2026',
    updated: updated || '',
    category: category || 'Ratgeber',
    slug: slug || 'testartikel',
    permalink: '/posts/' + (slug || 'testartikel') + '/',
  };
  const trackBlock = track
    ? `<script type="application/json" id="ff-voice-track-config">${JSON.stringify(track)}</script>`
    : '';
  const korrekturBlock = korrektur
    ? `<div class="ff-korrektur" role="note">${korrektur}</div>`
    : '';
  const kurzBlock = kurzantwort
    ? `<div class="ff-kurzantwort"><div class="ff-kurzantwort__head"><span class="ff-kurzantwort__icon">💡</span><span class="ff-kurzantwort__eyebrow">Kurz &amp; knapp – die Antwort</span></div><p class="ff-kurzantwort__text">${kurzantwort}</p></div>`
    : '';

  return `<!doctype html>
<html lang="${lang || 'de'}">
<head><meta charset="utf-8"><title>${title || 'Testartikel'}</title></head>
<body>
<header class="header"><nav class="nav">Navigation</nav></header>
${korrekturBlock}
${kurzBlock}
<main class="main">
<article class="post-single">
<header class="post-header"><h1 class="post-title">${title || 'Testartikel'}</h1></header>
${toolbarHtml(lang)}
<div class="post-content">
${bodyHtml || ''}
</div>
</article>
</main>
<footer class="footer">Impressum · Datenschutz</footer>
<script type="application/json" id="ff-voice-config">${JSON.stringify(cfg)}</script>
${trackBlock}
</body></html>`;
}

/* ============================================================
   5 · Sprach-Synthesizer-Attrappe (steuerbar, deterministisch)
   ============================================================ */

export function makeVoices(list) {
  return list.map((v, i) => ({
    name: v.name,
    lang: v.lang,
    voiceURI: v.voiceURI || v.name,
    localService: v.localService !== false,
    default: i === 0,
  }));
}

export const DEFAULT_VOICES = makeVoices([
  { name: 'Google Deutsch', lang: 'de-DE' },
  { name: 'Google deutsch', lang: 'de-DE' },
  { name: 'Anna', lang: 'de-DE' },
  { name: 'Katja', lang: 'de-DE' },
  { name: 'Hedda', lang: 'de-DE' },
  { name: 'Microsoft Conrad Online (Natural) - German (Germany)', lang: 'de-DE', localService: false },
  { name: 'Microsoft Florian Online (Natural) - German (Germany)', lang: 'de-DE', localService: false },
  { name: 'Microsoft Katja Online (Natural) - German (Germany)', lang: 'de-DE', localService: false },
  { name: 'Microsoft Stefan Online (Natural) - German (Austria)', lang: 'de-AT', localService: false },
  { name: 'Google UK English Male', lang: 'en-GB' },
  { name: 'Microsoft Andrew Online (Natural) - English (United States)', lang: 'en-US', localService: false },
  { name: 'Microsoft Ryan Online (Natural) - English (United Kingdom)', lang: 'en-GB', localService: false },
  { name: 'Microsoft Aria Online (Natural) - English (United States)', lang: 'en-US', localService: false },
  { name: 'Samantha', lang: 'en-US' },
  { name: 'eSpeak German', lang: 'de' },
]);

/**
 * Installiert eine steuerbare Web-Speech-Attrappe.
 * `speak()` ruft onstart synchron und onend asynchron auf; damit lassen
 * sich Start, Fortschritt, Pause und Fortsetzen deterministisch prüfen.
 */
export function installSpeech(win, { voices = DEFAULT_VOICES, support = true } = {}) {
  const log = [];
  const state = { cancelled: 0, speaking: false, paused: false };
  if (!support) {
    win.speechSynthesis = undefined;
    win.SpeechSynthesisUtterance = undefined;
    return { log, state };
  }
  class Utterance {
    constructor(text) {
      this.text = text;
      this.lang = '';
      this.voice = null;
      this.rate = 1;
      this.pitch = 1;
      this.volume = 1;
      this.onstart = null;
      this.onend = null;
      this.onerror = null;
      this.onboundary = null;
    }
  }
  win.SpeechSynthesisUtterance = Utterance;
  win.speechSynthesis = {
    get speaking() { return state.speaking; },
    get paused() { return state.paused; },
    get pending() { return false; },
    getVoices: () => voices.slice(),
    speak(u) {
      state.speaking = true;
      log.push({
        text: u.text, lang: u.lang, rate: u.rate, pitch: u.pitch, volume: u.volume,
        voice: u.voice ? u.voice.name : null,
      });
      if (typeof u.onstart === 'function') u.onstart();
      setTimeout(() => {
        if (state.cancelled > 0 && log.cancelGuard === state.cancelled) return;
        state.speaking = false;
        if (typeof u.onboundary === 'function') u.onboundary({ charIndex: u.text.length });
        if (typeof u.onend === 'function') u.onend();
      }, 0);
    },
    cancel() { state.cancelled += 1; state.speaking = false; },
    pause() { state.paused = true; },
    resume() { state.paused = false; },
    addEventListener() {},
    removeEventListener() {},
  };
  return { log, state };
}

/* ============================================================
   6 · Seite + Engine laden
   ============================================================ */

export function loadPage(html, { voices = DEFAULT_VOICES, support = true, runScripts = true } = {}) {
  const virtualConsole = new VirtualConsole();
  virtualConsole.on('jsdomError', () => {});
  virtualConsole.on('error', () => {});
  virtualConsole.on('warn', () => {});

  const dom = new JSDOM(html, {
    url: 'https://franksfinanzcheck.de/posts/testartikel/',
    pretendToBeVisual: true,
    runScripts: 'outside-only',
    virtualConsole,
  });
  const win = dom.window;
  const doc = win.document;

  installSpeech(win, { voices, support });

  if (runScripts) {
    const code = fs.readFileSync(ENGINE_PATH, 'utf8');
    win.eval(code);
  }
  return { dom, win, doc };
}

export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/** Lässt die Engine n Einheiten abspielen (jede Pause ist ein echter Timer). */
export async function playUnits(win, count, { maxMs = 4000 } = {}) {
  const start = Date.now();
  let last = -1;
  while (Date.now() - start < maxMs) {
    const api = win.__ffVoice;
    if (!api) break;
    const spoken = win.__ffVoiceSpokenCount ? win.__ffVoiceSpokenCount() : null;
    if (spoken != null) {
      if (spoken >= count) break;
      last = spoken;
    }
    await sleep(10);
    if (!api.reading) break;
  }
  return last;
}

export { fs, path };
