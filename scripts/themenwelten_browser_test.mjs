/**
 * Echte Chromium-Prüfung des gebauten Blogs, keine nachgebaute Test-UI.
 * npm ci --prefix tools/ff-voice-browser
 * node scripts/themenwelten_browser_test.mjs --public public [--base-path /blog/]
 * Optional: FF_BROWSER_PATH, THEMENWELTEN_SCREENSHOTS (nur lokale QA-Artefakte).
 * Fehlender Browser/Build = Exit 1. Externe Dienste sind für diesen Test gesperrt.
 */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import http from 'node:http';
import os from 'node:os';
import path from 'node:path';
import zlib from 'node:zlib';
import { execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const arg = (key, fallback) => {
  const i = process.argv.indexOf(key);
  return i === -1 ? fallback : process.argv[i + 1];
};
const PUBLIC = path.resolve(arg('--public', path.join(ROOT, 'public')));
const prefix = arg('--base-path', '/').replace(/^\/+|\/+$/g, '');
const BASE_PATH = prefix ? `/${prefix}/` : '/';
const DATA = JSON.parse(fs.readFileSync(path.join(ROOT, 'data/themenwelten.json'), 'utf8'));
assert.ok(fs.existsSync(path.join(PUBLIC, 'posts/index.html')), 'Hugo-Build fehlt.');
const require = createRequire(path.join(ROOT, 'tools/ff-voice-browser/package.json'));
const { chromium } = require('playwright-core');
const mod = require('@sparticuz/chromium');
const bundled = mod.default || mod;

// Das vorhandene Browser-Paket enthält auch libnss/libnspr für schlanke
// Sandboxes. Kein apt, Browser-CDN oder stilles Überspringen erforderlich.
let libDir;
let browser;
let server;
let assertions = 0;
function check(condition, label) {
  assert.ok(condition, label);
  assertions += 1;
}

try {
  let executablePath = process.env.FF_BROWSER_PATH;
  if (!executablePath) {
    executablePath = await bundled.executablePath();
    const archive = path.join(ROOT, 'tools/ff-voice-browser/node_modules/@sparticuz/chromium/bin/al2023.tar.br');
    if (fs.existsSync(archive)) {
      libDir = fs.mkdtempSync(path.join(os.tmpdir(), 'ff-topics-libs-'));
      const tar = path.join(libDir, 'libs.tar');
      fs.writeFileSync(tar, zlib.brotliDecompressSync(fs.readFileSync(archive)));
      execFileSync('tar', ['-xf', tar, '-C', libDir]);
      process.env.LD_LIBRARY_PATH = [process.env.LD_LIBRARY_PATH, path.join(libDir, 'lib')].filter(Boolean).join(':');
    }
  }
  browser = await chromium.launch({
    executablePath,
    headless: true,
    // single-process ist für Serverless-Einzelaufrufe gedacht und kann beim
    // Schließen/Öffnen isolierter Test-Kontexte hängen. Hier echte Prozesse.
    args: bundled.args.filter(a => a !== '--single-process' && !a.includes('disable-web-security') && !a.includes('allow-running-insecure-content')),
  });

  const mime = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css',
    '.woff2': 'font/woff2', '.svg': 'image/svg+xml', '.jpg': 'image/jpeg', '.png': 'image/png',
    '.avif': 'image/avif', '.webp': 'image/webp', '.json': 'application/json', '.ico': 'image/x-icon' };
  server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://preview.invalid');
    const pathname = decodeURIComponent(url.pathname);
    if (!pathname.startsWith(BASE_PATH)) { res.writeHead(404); res.end(); return; }
    let file = path.resolve(PUBLIC, pathname.slice(BASE_PATH.length));
    if (file !== PUBLIC && !file.startsWith(PUBLIC + path.sep)) { res.writeHead(403); res.end(); return; }
    if (fs.existsSync(file) && fs.statSync(file).isDirectory()) file = path.join(file, 'index.html');
    if (!fs.existsSync(file)) { res.writeHead(404); res.end(); return; }
    res.writeHead(200, { 'Content-Type': mime[path.extname(file)] || 'application/octet-stream' });
    fs.createReadStream(file).pipe(res);
  });
  await new Promise(resolve => server.listen(0, '0.0.0.0', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const url = suffix => origin + BASE_PATH + suffix;

  async function newPage(options = {}) {
    const context = await browser.newContext({
      viewport: { width: 1440, height: 1000 }, colorScheme: 'light', reducedMotion: 'reduce',
      serviceWorkers: 'block', ...options,
    });
    await context.route('**/*', route => {
      const target = new URL(route.request().url());
      return target.origin === origin ? route.continue() : route.abort();
    });
    const page = await context.newPage();
    return { context, page };
  }

  const cases = [
    { name: 'Desktop', width: 1440, height: 1000, columns: 3, reducedMotion: 'no-preference' },
    { name: 'Tablet', width: 834, height: 1112, columns: 2 },
    { name: 'Mobil', width: 390, height: 844, columns: 1 },
    { name: '320px-Reflow', width: 320, height: 740, columns: 1 },
    { name: 'Dunkelmodus', width: 1280, height: 900, columns: 3, colorScheme: 'dark' },
    { name: 'Ohne-JavaScript', width: 390, height: 844, columns: 1, javaScriptEnabled: false },
    { name: 'Dunkel-ohne-JavaScript', width: 390, height: 844, columns: 1, javaScriptEnabled: false, colorScheme: 'dark' },
    { name: '200-Prozent-Text', width: 1280, height: 900, columns: 2, textZoom: true },
    { name: 'Reduzierte-Bewegung', width: 1440, height: 1000, columns: 3 },
  ];
  for (const test of cases) {
    const { page, context } = await newPage({
      viewport: { width: test.width, height: test.height },
      colorScheme: test.colorScheme || 'light',
      javaScriptEnabled: test.javaScriptEnabled !== false,
      reducedMotion: test.reducedMotion || 'reduce',
    });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(url('posts/'), { waitUntil: 'networkidle' });
    if (test.javaScriptEnabled !== false) {
      const consent = page.getByRole('button', { name: 'Nur notwendige', exact: true });
      if (await consent.isVisible()) await consent.click();
    }
    if (test.textZoom) await page.evaluate(() => { document.documentElement.style.fontSize = '200%'; });
    check(await page.getByRole('heading', { name: DATA.title, exact: true, level: 2 }).count() === 1, `${test.name}: korrekte H2`);
    check(await page.locator('.ff-topic-card').count() === 6, `${test.name}: sechs Karten`);
    check(await page.locator('.ff-mini-toc').count() === 0, `${test.name}: keine überlagernde Artikel-Navigation`);
    for (const topic of DATA.topics) {
      const card = page.getByRole('link', { name: topic.title, exact: true });
      check(await card.count() === 1 && await card.isVisible(), `${test.name}: zugänglicher Name ${topic.id}`);
      check(await card.getAttribute('href') === `${BASE_PATH}pillar/${topic.id}/`, `${test.name}: URL ${topic.id}`);
    }
    const metrics = await page.evaluate(() => {
      const cards = [...document.querySelectorAll('.ff-topic-card')];
      const visible = el => {
        for (let node = el; node; node = node.parentElement) {
          const s = getComputedStyle(node);
          if (s.display === 'none' || s.visibility === 'hidden' || Number(s.opacity) === 0) return false;
        }
        return true;
      };
      const luminance = rgb => {
        const channels = rgb.match(/[\d.]+/g).slice(0, 3).map(n => {
          const c = Number(n) / 255;
          return c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4;
        });
        return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
      };
      const contrast = (a, b) => {
        const x = luminance(a), y = luminance(b);
        return (Math.max(x, y) + .05) / (Math.min(x, y) + .05);
      };
      return {
        overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
        columns: getComputedStyle(document.querySelector('.ff-topics-grid')).gridTemplateColumns.split(' ').length,
        cards: cards.map(card => {
          const rect = card.getBoundingClientRect();
          const desc = card.querySelector('.ff-topic-description');
          const count = card.querySelector('.ff-topic-count');
          return {
            visible: visible(card), width: rect.width, height: rect.height,
            clipped: [card, card.querySelector('h3'), desc].some(el => el.scrollWidth > el.clientWidth + 1),
            contrast: Math.min(
              contrast(getComputedStyle(desc).color, getComputedStyle(card).backgroundColor),
              contrast(getComputedStyle(count).color, getComputedStyle(count).backgroundColor),
              contrast(getComputedStyle(card.querySelector('h3')).color, getComputedStyle(card).backgroundColor)),
            transition: getComputedStyle(card).transitionProperty,
          };
        }),
        menuHeight: document.querySelector('.menu a[title="Über mich"]').getBoundingClientRect().height,
      };
    });
    check(!metrics.overflow, `${test.name}: kein horizontaler Seiten-Overflow`);
    check(metrics.columns === test.columns, `${test.name}: ${test.columns} Spalte(n), tatsächlich ${metrics.columns}`);
    for (const [i, card] of metrics.cards.entries()) {
      check(card.visible && !card.clipped && card.width >= 44 && card.height >= 44, `${test.name}: Karte ${i + 1} sichtbar, unbeschnitten und ausreichend groß`);
      check(card.contrast >= 4.5, `${test.name}: Textkontrast Karte ${i + 1} ≥ 4,5:1 (ist ${card.contrast.toFixed(2)})`);
      if (test.name === 'Reduzierte-Bewegung') check(card.transition === 'none', 'Reduzierte Bewegung: keine Karten-Transition');
    }
    check(metrics.menuHeight <= 61, `${test.name}: „Über mich“ bleibt einzeilig`);
    check(errors.length === 0, `${test.name}: JavaScript-Fehler: ${errors.join('; ')}`);
    if (process.env.THEMENWELTEN_SCREENSHOTS) {
      fs.mkdirSync(process.env.THEMENWELTEN_SCREENSHOTS, { recursive: true });
      await page.screenshot({ path: path.join(process.env.THEMENWELTEN_SCREENSHOTS, `${test.name}.png`) });
    }
    console.log(`✓ ${test.name}: Layout, Namen, Links und Kontrast`);
    await context.close();
  }

  const { page, context } = await newPage();
  await page.goto(url('posts/'), { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: 'Nur notwendige', exact: true }).click();
  await page.locator('.ff-posts-jump').focus();
  for (const topic of DATA.topics) {
    await page.keyboard.press('Tab');
    const focus = await page.evaluate(() => ({
      topic: document.activeElement.dataset.topic,
      outline: getComputedStyle(document.activeElement).outlineStyle,
      width: parseFloat(getComputedStyle(document.activeElement).outlineWidth),
    }));
    check(focus.topic === topic.id && focus.outline !== 'none' && focus.width >= 3, `Tastatur: ${topic.title} in Reihenfolge mit sichtbarem Fokus`);
  }
  await page.keyboard.press('Enter');
  await page.waitForURL(url('pillar/mietwagen/'));
  check(await page.locator('main h1').count() === 1, 'Enter öffnet den Ratgeber');

  for (const topic of DATA.topics) {
    await page.goto(url('posts/'), { waitUntil: 'networkidle' });
    await page.locator(`.ff-topic-card[data-topic="${topic.id}"] .ff-topic-description`).click();
    await page.waitForURL(url(`pillar/${topic.id}/`));
    check(await page.locator('main h1').count() === 1, `Ganze Karte klickbar, Ziel erreichbar: ${topic.id}`);
  }
  for (const anchor of ['deine-6-themenwelten', 'ddeine6-themenwelten']) {
    await page.goto(url(`posts/#${anchor}`), { waitUntil: 'networkidle' });
    const heading = await page.locator('#deine-6-themenwelten').boundingBox();
    const header = await page.locator('.header').boundingBox();
    check(heading.y >= header.y + header.height - 1 && heading.y < 400, `Abschnittslink ${anchor} landet unter dem Sticky-Header`);
  }
  await page.goto(url('posts/'), { waitUntil: 'networkidle' });
  await page.locator('.ff-posts-jump').click();
  await page.waitForURL(url('posts/#neueste-artikel'));
  check((await page.locator('#neueste-artikel').boundingBox()).y >= 60, 'Sprung zur Artikelliste nicht vom Header verdeckt');
  const firstArticle = await page.locator('.ff-posts-feed .entry-link').first().getAttribute('href');
  await page.locator('.pagination .next').click();
  await page.waitForURL(url('posts/page/2/'));
  check(await page.locator('.ff-topics, .ff-posts-guide, .ff-filter-bar').count() === 0, 'Seite 2 ohne duplizierte Themen/Einleitung');
  check(await page.locator('.ff-posts-feed .entry-link').count() > 0, 'Seite 2 enthält ältere Artikel');
  await page.locator('.ff-posts-jump').click();
  await page.waitForURL(url('posts/#deine-6-themenwelten'));
  check(await page.locator('.ff-topic-card').count() === 6, 'Rückweg von Seite 2 zu allen Themen');

  await page.goto(url(''), { waitUntil: 'networkidle' });
  check(await page.locator('.ff-topics .ff-topic-card').count() === 6, 'Startseite nutzt dieselben sechs Themen');
  check((await page.locator('main').boundingBox()).width <= 800, 'Startseite nicht versehentlich verbreitert');
  await page.goto(new URL(firstArticle, origin).href, { waitUntil: 'networkidle' });
  check(await page.locator('.ff-mini-toc').count() === 1, 'Artikel behalten ihre Mini-Navigation');
  check(await page.locator('.ff-posts-index').count() === 0, 'Einzelartikel behalten ihr Layout');
  await context.close();
  console.log(`✓ Themenwelten-Browserprüfung: ${assertions} Prüfungen bestanden (${BASE_PATH}).`);
} finally {
  if (browser) await browser.close();
  if (server) await new Promise(resolve => server.close(resolve));
  if (libDir) fs.rmSync(libDir, { recursive: true, force: true });
}
