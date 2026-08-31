#!/usr/bin/env node
/**
 * layout_browser_check.js – LAYOUT-AUTOMATISIERUNG (Browser-Teil)
 *
 * Lädt Startseite + die 3 neuesten Artikel in Desktop UND Mobile und prüft:
 *   - HTTP-Fehler (4xx/5xx) aller Ressourcen
 *   - JavaScript-Fehler (pageerror, console.error)
 *   - DOM-Größe (Schwellwert: 1400 Elemente – Perf-Budget)
 *   - Title/H1 vorhanden
 *   - Ladezeit (networkidle0) als LCP-Näherung
 *
 * Ausgabe: JSON auf stdout + Exit 0 (ok) / 1 (Fehler oder Budget-Warnung).
 *
 * Aufruf:
 *   LAYOUT_BASE=/pfad/zum/public LAYOUT_PORT=8099 CHROME_PATH=... node scripts/layout_browser_check.js
 */
const puppeteer = require('puppeteer-core');
const http = require('http');
const fs = require('fs');
const path = require('path');

const BASE = process.env.LAYOUT_BASE || path.join(__dirname, '..', 'public');
const PORT = parseInt(process.env.LAYOUT_PORT || '8099', 10);
const CHROME = process.env.CHROME_PATH || '';

function serve(baseDir, port) {
  const server = http.createServer((req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0]);
    if (p.endsWith('/')) p += 'index.html';
    let file = path.normalize(path.join(baseDir, p));
    if (!file.startsWith(baseDir)) { res.writeHead(403); res.end(); return; }
    fs.readFile(file, (err, data) => {
      if (err) { res.writeHead(404); res.end('not found'); return; }
      const ext = path.extname(file);
      const types = {'.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript',
                     '.jpg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp',
                     '.avif': 'image/avif', '.woff2': 'font/woff2', '.svg': 'image/svg+xml',
                     '.xml': 'application/xml', '.txt': 'text/plain', '.json': 'application/json'};
      res.writeHead(200, {'Content-Type': types[ext] || 'application/octet-stream'});
      res.end(data);
    });
  });
  return new Promise(resolve => server.listen(port, '127.0.0.1', () => resolve(server)));
}

async function auditPage(browser, url, viewport) {
  const page = await browser.newPage();
  await page.setViewport(viewport);
  const errors = [];
  const httpErrors = [];
  let domCount = 0;
  let domDepth = 0;
  let maxChildren = 0;
  let maxChildrenElement = '';
  page.on('pageerror', e => errors.push('JS: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('response', r => { if (r.status() >= 400) httpErrors.push(r.status() + ' ' + r.url()); });

  const t0 = Date.now();
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 45000 }).catch(e => errors.push('load: ' + e.message));
  const loadMs = Date.now() - t0;
  const metrics = await page.evaluate(() => {
    const all = document.querySelectorAll('*');
    let depth = 0, maxKids = 0, maxKidsNode = null;
    for (const el of all) {
      let d = 0, n = el;
      while (n && n !== document.documentElement) { d++; n = n.parentElement; }
      if (d > depth) depth = d;
      if (el.children.length > maxKids) {
        maxKids = el.children.length;
        maxKidsNode = el;
      }
    }

    // Kompakter, stabiler DOM-Pfad: macht den Report direkt reparierbar,
    // statt pauschal (und bei langen Artikeln oft falsch) den <head> zu nennen.
    const describe = (el) => {
      const parts = [];
      while (el && el.nodeType === 1 && parts.length < 5) {
        let part = el.tagName.toLowerCase();
        if (el.id) {
          part += '#' + el.id;
        } else if (el.classList.length) {
          part += '.' + Array.from(el.classList).slice(0, 2).join('.');
        }
        parts.unshift(part);
        el = el.parentElement;
      }
      return parts.join(' > ');
    };
    return { count: all.length, depth, maxKids, maxKidsElement: describe(maxKidsNode) };
  });
  domCount = metrics.count;
  domDepth = metrics.depth;
  maxChildren = metrics.maxKids;
  maxChildrenElement = metrics.maxKidsElement;
  const title = await page.title();
  const h1 = await page.evaluate(() => document.querySelector('h1') ? document.querySelector('h1').textContent.trim().slice(0, 60) : null);
  await page.close();

  const issues = [];
  if (errors.length) issues.push(...errors.slice(0, 5));
  if (httpErrors.length) issues.push(...httpErrors.slice(0, 5));
  // DOM-Performance-Budgets (Lighthouse-Schwellen: 1400/32/60 – wir warnen
  // deutlich früher als Frühwarnsystem, damit nie ein Problem entsteht):
  if (domCount > 900) issues.push(`DOM ${domCount} > 900 Elemente (Budget: <900, Lighthouse-Warnung: 1400)`);
  if (domDepth > 28) issues.push(`DOM-Tiefe ${domDepth} > 28 (Lighthouse-Warnung: 32)`);
  if (maxChildren > 58) issues.push(`Max. Kinder ${maxChildren} > 58 (Lighthouse-Warnung: 60) – Element: ${maxChildrenElement || 'unbekannt'}`);
  if (!title) issues.push('kein <title>');
  if (!h1) issues.push('kein <h1>');

  return { url, viewport: viewport.width + 'x' + viewport.height, domCount, domDepth, maxChildren, maxChildrenElement, loadMs, title: title.slice(0, 60), h1, issues };
}

(async () => {
  if (!CHROME) { console.error('CHROME_PATH nicht gesetzt'); process.exit(2); }
  const server = await serve(BASE, PORT);
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
  });

  const slugs = fs.readdirSync(path.join(BASE, 'posts'))
    .filter(d => fs.existsSync(path.join(BASE, 'posts', d, 'index.html')))
    .sort().slice(-3).reverse(); // 3 neueste
  const urls = ['http://127.0.0.1:' + PORT + '/'];
  for (const s of slugs) urls.push(`http://127.0.0.1:${PORT}/posts/${s}/`);

  const results = [];
  for (const u of urls) {
    results.push(await auditPage(browser, u, { width: 1280, height: 800 }));
    results.push(await auditPage(browser, u, { width: 390, height: 844 }));
  }

  await browser.close();
  server.close();

  const critical = results.filter(r => r.issues.length > 0);
  // Aggregierte DOM-Messwerte für den Log (Frühwarn-Dashboard)
  const maxChildrenResult = results.reduce((max, current) =>
    current.maxChildren > max.maxChildren ? current : max
  );
  const agg = {
    maxElements: Math.max(...results.map(r => r.domCount)),
    maxDepth: Math.max(...results.map(r => r.domDepth)),
    maxChildren: maxChildrenResult.maxChildren,
    maxChildrenElement: maxChildrenResult.maxChildrenElement,
    avgLoadMs: Math.round(results.reduce((s, r) => s + r.loadMs, 0) / results.length),
  };
  const summary = {
    checked: results.length,
    domMetrics: agg,
    criticalPages: critical.map(r => ({ url: r.url, viewport: r.viewport, issues: r.issues })),
    allOk: critical.length === 0,
  };
  console.log(JSON.stringify(summary, null, 2));
  process.exit(critical.length ? 1 : 0);
})();
