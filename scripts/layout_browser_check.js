#!/usr/bin/env node
/**
 * layout_browser_check.js – LAYOUT-AUTOMATISIERUNG (Browser-Teil)
 *
 * Lädt die Startseite, die 3 neuesten Artikel UND die nach dem statischen
 * DOM-Audit „schwersten" Seiten (Desktop UND Mobile) und prüft:
 *   - HTTP-Fehler (4xx/5xx) aller Ressourcen
 *   - JavaScript-Fehler (pageerror, console.error derselben Herkunft)
 *   - DOM-Budgets (Kinder je Element, Tiefe, Elemente, Kinder im <head>)
 *   - Title/H1 vorhanden
 *   - Ladezeit (networkidle0) als LCP-Näherung
 *
 * UMBau 21.09.2026 (Issue #338) – drei Lehren aus dem Fehlalarm:
 *
 *  1. EIN Budget, EINE Wahrheit. Die Schwellen kommen aus
 *     `.cache/layout/dom-audit.json` (geschrieben von layout_audit.py /
 *     dom_audit.py) – nicht mehr als zweite Zahlenkopie in dieser Datei.
 *     Ohne die Datei greifen eingefrorene Standardwerte (siehe FALLBACK).
 *  2. DAS SAMPLE FOLGT DEM RISIKO. Vorher: Startseite + 3 neueste Artikel.
 *     Die Tag-Übersicht mit 136 Kindern einer einzigen Liste lag damit nie
 *     im Blick. Jetzt kommen die Seiten mit den höchsten statischen Werten
 *     dazu – der schwere Fall wird gemessen, nicht der bequeme.
 *  3. DER PARSER WIRD MITGEPRÜFT. Der statische Audit baut den DOM ohne
 *     Browser nach (scripts/dom_audit.py). Hier wird gegengerechnet:
 *     weichen Browser- und Parser-Zahlen ab (Toleranz unten), ist der
 *     Parser falsch – dann ist der ganze statische Audit falsch. Das ist
 *     der Grund, warum diese Datei auch nach dem Umbau DOM misst.
 *
 * Zulässige Abweichung (TOLERANCE): Der Browser sieht zur Laufzeit mehr als
 * der Parser – der Umami-Loader hängt sich per JS als zusätzliches
 * `<script>` in den `<head>` (+1 Kind), Konsent-/Theme-Klassen ändern nur
 * Attribute. Unterschiede darüber hinaus sind Parser-Drift und werden als
 * Befund gemeldet.
 *
 * Ausgabe: JSON auf stdout + Exit 0 (ok) / 1 (Fehler oder Budget-Warnung).
 *
 * Aufruf:
 *   LAYOUT_BASE=/pfad/zum/public LAYOUT_PORT=8099 CHROME_PATH=... \
 *     node scripts/layout_browser_check.js
 */
const puppeteer = require('puppeteer-core');
const http = require('http');
const fs = require('fs');
const path = require('path');

const BASE = process.env.LAYOUT_BASE || path.join(__dirname, '..', 'public');
const PORT = parseInt(process.env.LAYOUT_PORT || '8099', 10);
const CHROME = process.env.CHROME_PATH || '';
const DOM_JSON = process.env.LAYOUT_DOM_JSON ||
  path.join(__dirname, '..', '.cache', 'layout', 'dom-audit.json');
const EXTRA_RISK_PAGES = parseInt(process.env.LAYOUT_RISK_PAGES || '3', 10);
// Laufzeit-Zugaben des Browsers (siehe Kopf): Umami-Loader im <head>, ggf.
// Sentinel-Div aus dem Top-Link-Skript (Body-Ebene, zählt nur in „elements").
const TOLERANCE = { headchildren: 2, maxChildren: 2, depth: 2, totalElements: 5 };

// Eingefrorene Standard-Budgets, falls kein statischer Audit vorliegt.
// Sie MÜSSEN den Werten in dom_audit.py entsprechen (dort steht die Wahrheit).
const FALLBACK = {
  budgets: {
    fruehwarnung: { children: 54, head_children: 52, depth: 28, elements: 1100 },
    lighthouse: { children: 60, head_children: 58, depth: 32, elements: 1400 },
  },
  rows: [],
};

function loadDomAudit() {
  try {
    const data = JSON.parse(fs.readFileSync(DOM_JSON, 'utf8'));
    if (!data || !data.budgets) throw new Error('Struktur unerwartet');
    return data;
  } catch (err) {
    console.error(
      `Hinweis: ${DOM_JSON} nicht lesbar (${err.message}) – ` +
      'es gelten die eingefrorenen Standard-Budgets.');
    return FALLBACK;
  }
}

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

/** Statische Messwerte einer Seite (oder null, wenn nicht im Audit). */
function staticMetrics(domAudit, urlPath) {
  const row = (domAudit.rows || []).find(r => r.rel === urlPath);
  return row || null;
}

function describe(el) {
  const parts = [];
  while (el && el.nodeType === 1 && parts.length < 5) {
    let part = el.tagName.toLowerCase();
    if (el.id) part += '#' + el.id;
    else if (el.classList && el.classList.length) {
      part += '.' + Array.from(el.classList).slice(0, 2).join('.');
    }
    parts.unshift(part);
    el = el.parentElement;
  }
  return parts.join(' > ');
}

async function auditPage(browser, url, viewport, ctx) {
  const page = await browser.newPage();
  await page.setViewport(viewport);
  const errors = [];
  const httpErrors = [];
  page.on('pageerror', e => errors.push('JS: ' + e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
  page.on('response', r => { if (r.status() >= 400) httpErrors.push(r.status() + ' ' + r.url()); });

  const t0 = Date.now();
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 45000 })
    .catch(e => errors.push('load: ' + e.message));
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
    const describe = (el) => {
      const parts = [];
      while (el && el.nodeType === 1 && parts.length < 5) {
        let part = el.tagName.toLowerCase();
        if (el.id) part += '#' + el.id;
        else if (el.classList.length) {
          part += '.' + Array.from(el.classList).slice(0, 2).join('.');
        }
        parts.unshift(part);
        el = el.parentElement;
      }
      return parts.join(' > ');
    };
    return {
      count: all.length,
      depth,
      maxKids,
      maxKidsElement: describe(maxKidsNode),
      headKids: document.head ? document.head.children.length : 0,
    };
  });
  const title = await page.title();
  const h1 = await page.evaluate(() => {
    const el = document.querySelector('h1');
    return el ? el.textContent.trim().slice(0, 60) : null;
  });
  await page.close();

  const issues = [];
  const drift = [];
  if (errors.length) issues.push(...errors.slice(0, 5));
  if (httpErrors.length) issues.push(...httpErrors.slice(0, 5));

  const b = ctx.budgets.fruehwarnung;
  const l = ctx.budgets.lighthouse;
  if (metrics.count > l.elements) {
    issues.push(`DOM ${metrics.count} > ${l.elements} Elemente (Lighthouse-Grenze)`);
  } else if (metrics.count > b.elements) {
    issues.push(`DOM ${metrics.count} > ${b.elements} Elemente (Frühwarnung)`);
  }
  if (metrics.depth > l.depth) {
    issues.push(`DOM-Tiefe ${metrics.depth} > ${l.depth} (Lighthouse-Grenze)`);
  } else if (metrics.depth > b.depth) {
    issues.push(`DOM-Tiefe ${metrics.depth} > ${b.depth} (Frühwarnung)`);
  }
  if (metrics.maxKids > l.children) {
    issues.push(`Max. Kinder ${metrics.maxKids} > ${l.children} (Lighthouse-Grenze) – `
      + `Element: ${metrics.maxKidsElement || 'unbekannt'}`);
  } else if (metrics.maxKids > b.children) {
    issues.push(`Max. Kinder ${metrics.maxKids} > ${b.children} (Frühwarnung) – `
      + `Element: ${metrics.maxKidsElement || 'unbekannt'}`);
  }
  if (metrics.headKids > l.head_children) {
    issues.push(`Head-Kinder ${metrics.headKids} > ${l.head_children} (Lighthouse-Grenze) – Element: html > head`);
  } else if (metrics.headKids > b.head_children) {
    issues.push(`Head-Kinder ${metrics.headKids} > ${b.head_children} (Frühwarnung) – Element: html > head`);
  }
  if (!title) issues.push('kein <title>');
  if (!h1) issues.push('kein <h1>');

  // ---------- Parser-Gegenrechnung (Issue #338, Lehre 3) ----------
  const stat = staticMetrics(ctx.domAudit, new URL(url).pathname);
  if (stat) {
    const pairs = [
      ['headchildren', metrics.headKids, stat.headchildren],
      ['maxChildren', metrics.maxKids, stat.maxchildren],
      ['depth', metrics.depth, stat.depth],
      ['totalElements', metrics.count, stat.elements],
    ];
    for (const [key, browserValue, parserValue] of pairs) {
      const delta = Math.abs(browserValue - parserValue);
      if (delta > TOLERANCE[key]) {
        drift.push(`${key}: Browser ${browserValue} vs. Parser ${parserValue} `
          + `(Δ${delta} > Toleranz ${TOLERANCE[key]})`);
      }
    }
  }

  return {
    url,
    viewport: viewport.width + 'x' + viewport.height,
    domCount: metrics.count,
    domDepth: metrics.depth,
    maxChildren: metrics.maxKids,
    maxChildrenElement: metrics.maxKidsElement,
    headChildren: metrics.headKids,
    staticMetrics: stat ? {
      elements: stat.elements, depth: stat.depth,
      maxChildren: stat.maxchildren, headChildren: stat.headchildren,
    } : null,
    parserDrift: drift,
    loadMs,
    title: title.slice(0, 60),
    h1,
    issues,
  };
}

/** Sample: Startseite + 3 neueste Artikel + die statisch schwersten Seiten. */
function buildSampleUrls(domAudit) {
  const slugs = fs.readdirSync(path.join(BASE, 'posts'))
    .filter(d => fs.existsSync(path.join(BASE, 'posts', d, 'index.html')))
    .sort().slice(-3).reverse();
  const urls = ['http://127.0.0.1:' + PORT + '/'];
  const seen = new Set(['/']);
  for (const s of slugs) {
    urls.push(`http://127.0.0.1:${PORT}/posts/${s}/`);
    seen.add(`/posts/${s}/`);
  }
  // Risiko-Seiten: größte gemessene Werte zuerst, Paginierung/Vorlagen raus
  const rows = (domAudit.rows || [])
    .filter(r => !r.rel.startsWith('/page/') && !/-report/i.test(r.rel));
  const ranked = [];
  const push = (r) => { if (!seen.has(r.rel)) { ranked.push(r); seen.add(r.rel); } };
  [...rows].sort((a, b) => b.headchildren - a.headchildren).forEach(push);
  [...rows].sort((a, b) => b.maxchildren - a.maxchildren).forEach(push);
  [...rows].sort((a, b) => b.elements - a.elements).forEach(push);
  const risk = ranked.slice(0, Math.max(0, EXTRA_RISK_PAGES));
  for (const r of risk) urls.push(`http://127.0.0.1:${PORT}${r.rel}`);
  return { urls, slugs, risk: risk.map(r => r.rel) };
}

(async () => {
  if (!CHROME) { console.error('CHROME_PATH nicht gesetzt'); process.exit(2); }
  const domAudit = loadDomAudit();
  const ctx = { domAudit, budgets: domAudit.budgets || FALLBACK.budgets };
  const server = await serve(BASE, PORT);
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
  });

  const sample = buildSampleUrls(domAudit);
  const results = [];
  for (const u of sample.urls) {
    results.push(await auditPage(browser, u, { width: 1280, height: 800 }, ctx));
    results.push(await auditPage(browser, u, { width: 390, height: 844 }, ctx));
  }

  await browser.close();
  server.close();

  const critical = results.filter(r => r.issues.length > 0);
  const drift = results.filter(r => r.parserDrift.length > 0);
  const maxChildrenResult = results.reduce((max, cur) =>
    cur.maxChildren > max.maxChildren ? cur : max, results[0]);
  const agg = {
    maxElements: Math.max(...results.map(r => r.domCount)),
    maxDepth: Math.max(...results.map(r => r.domDepth)),
    maxChildren: maxChildrenResult.maxChildren,
    maxChildrenElement: maxChildrenResult.maxChildrenElement,
    maxHeadChildren: Math.max(...results.map(r => r.headChildren)),
    avgLoadMs: Math.round(results.reduce((s, r) => s + r.loadMs, 0) / results.length),
  };
  const summary = {
    checked: results.length,
    sample: sample.urls.map(u => new URL(u).pathname),
    riskPages: sample.risk,
    budgets: ctx.budgets,
    domMetrics: agg,
    parserCheck: {
      compared: results.filter(r => r.staticMetrics).length,
      tolerated: TOLERANCE,
      drift: drift.map(r => ({ url: r.url, viewport: r.viewport, drift: r.parserDrift })),
    },
    criticalPages: critical.map(r => ({
      url: r.url, viewport: r.viewport, issues: r.issues,
    })),
    allOk: critical.length === 0,
  };
  console.log(JSON.stringify(summary, null, 2));
  process.exit(critical.length ? 1 : 0);
})();
