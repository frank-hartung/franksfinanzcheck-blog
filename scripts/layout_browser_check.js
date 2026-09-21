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
 * ZWEI MESSUNGEN, ZWEI ZUSTÄNDIGKEITEN (Lehre aus dem ersten PR-Gate-Lauf,
 * 21.09.2026):
 *  1. Laufzeit-DOM (Seite normal geladen, inkl. `static/premium/*.js`):
 *     Das ist die Nutzerrealität – Mini-Inhaltsübersicht, Anker-Buttons,
 *     Fortschrittsleiste und Lesehilfen wachsen mit der Artikel-Länge
 *     (nachgemessen: 968 Elemente ausgeliefert → 1109 zur Laufzeit). Sie wird
 *     gegen die Laufzeit-Budgets geprüft (`fruehwarnung_runtime`, harte Grenze
 *     bleibt die Lighthouse-Grenze).
 *  2. Referenzmessung der ausgelieferten HTML: Die Datei wird gelesen und in
 *     einem Iframe mit `sandbox="allow-same-origin"` per `srcdoc` geparst –
 *     ein echter Parserlauf, aber ohne jede Skriptausführung und ohne Netz.
 *     Der Vergleich DIESER Zahlen mit `dom_audit.py` ist die
 *     Parser-Gegenrechnung – sonst meldet jede legitime Erweiterung „Drift"
 *     und die Prüfung wäre wertlos.
 *
 *     Warum nicht „Fremd-Skripte per Request-Interception ersetzen"? Zweimal
 *     am 21.09.2026 gemessen und verworfen: Erst kam das zweite Laden aus dem
 *     HTTP-Cache (Ersetzung wirkungslos, „Erweiterungsschicht +0"), dann
 *     zeigte sich, dass die Erweiterung nicht nur aus externen Dateien kommt –
 *     die Seiten bringen eigene Inline-Skripte mit, die kein Netzfilter
 *     aufhält. `srcdoc` im Sandbox-Iframe ist die einzige Messung, die
 *     garantiert nur die HTML sieht.
 *
 *     Bewusste Abweichung: Im Sandbox-Iframe ist Scripting aus, deshalb parst
 *     der Browser `<noscript>`-Inhalte als Markup (der statische Parser
 *     behandelt sie als Rohtext). Das erklärt einen kleinen, stabilen
 *     Mehrbetrag in der Referenzmessung – die Toleranz unten ist darauf
 *     begründet, nicht geraten (`staticVsHtml` im JSON zeigt jeden Delta).
 *
 * SEVERITY (Lehre aus #338): Ein Dauer-Alarm ist kein Alarm. Deshalb sind
 * die Stufen getrennt:
 *   - HARTER Befund → Exit 1: Lighthouse-Grenze überschritten, HTTP-/JS-Fehler,
 *     fehlender Titel/H1, Parser-Drift jenseits der Toleranz.
 *   - FRÜHWARNUNG → bleibt grün: Schwelle im Report/JSON, als `::warning::`
 *     sichtbar, aber ohne roten Lauf und ohne Issue. Sonst wäre jede
 *     ehrliche Vorwarnung ein Fehlalarm – genau das war #338.
 *
 * Ausgabe: JSON auf stdout + Exit 0 (ok oder nur Frühwarnungen) / 1 (harte
 * Befunde) / 2 (kein Chrome bzw. Werkzeugfehler).
 *
 * Aufruf:
 *   LAYOUT_BASE=/pfad/zum/public LAYOUT_PORT=8099 CHROME_PATH=... \
 *     node scripts/layout_browser_check.js
 */
const SELFTEST = process.argv.includes('--selftest');
// Nur im echten Lauf laden: der Selftest (Budget-/Severity-Vertrag) muss ohne
// installierten Browser und ohne Chrome laufen können – sonst prüft ihn nie
// jemand, weil die Testumgebung kein Puppeteer hat.
let puppeteer = null;
if (!SELFTEST) {
  try {
    puppeteer = require('puppeteer-core');
  } catch (err) {
    console.error('Werkzeugfehler: puppeteer-core nicht installiert (' + err.message
      + ') – Browser-Audit übersprungen (Exit 2, das statische DOM-Budget hat '
      + 'jede Seite vermessen).');
    process.exit(2);
  }
}
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
const TOLERANCE = {
  headchildren: 2,
  maxChildren: 2,
  depth: 2,
  // Elementsumme: der Sandbox-Iframe parst <noscript>-Inhalte als Markup
  // (Scripting aus) – jede Seite bringt zwei bis drei solche Blöcke mit
  // (Theme-Umschalter, Consent-Banner). Alles darüber ist Drift.
  totalElements: 12,
};

// Eingefrorene Standard-Budgets, falls kein statischer Audit vorliegt.
// Sie MÜSSEN den Werten in dom_audit.py entsprechen (dort steht die Wahrheit).
const FALLBACK = {
  budgets: {
    fruehwarnung: { children: 54, head_children: 52, depth: 28, elements: 1100 },
    fruehwarnung_runtime: { children: 54, head_children: 52, depth: 28,
                            elements: 1350 },
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

/**
 * Budget-Bewertung als reine Funktion (testbar ohne Browser).
 * Rückgabe: { issues, warnings } – nur `issues` machen den Lauf rot.
 */
function evaluateBudgets(metrics, budgets, runtime = false) {
  const issues = [];
  const warnings = [];
  const b = (runtime
    ? (budgets.fruehwarnung_runtime || budgets.fruehwarnung)
    : budgets.fruehwarnung);
  const l = budgets.lighthouse;
  const check = (value, warn, limit, make) => {
    if (value > limit) issues.push(make(limit, 'Lighthouse-Grenze'));
    else if (value > warn) warnings.push(make(warn, 'Frühwarnung'));
  };
  check(metrics.count, b.elements, l.elements,
    (g, kind) => `DOM ${metrics.count} > ${g} Elemente (${kind})`);
  check(metrics.depth, b.depth, l.depth,
    (g, kind) => `DOM-Tiefe ${metrics.depth} > ${g} (${kind})`);
  check(metrics.maxKids, b.children, l.children,
    (g, kind) => `Max. Kinder ${metrics.maxKids} > ${g} (${kind}) – `
      + `Element: ${metrics.maxKidsElement || 'unbekannt'}`);
  check(metrics.headKids, b.head_children, l.head_children,
    (g, kind) => `Head-Kinder ${metrics.headKids} > ${g} (${kind}) – `
      + 'Element: html > head');
  return { issues, warnings };
}

/** Selftest des Severity-Vertrags – läuft ohne Chrome und ohne Netz. */
function runSelftest() {
  const budgets = FALLBACK.budgets;
  // Basis: deutlich unter allen Schwellen – dann wird je Fall genau EINE
  // Metrik verschoben, und die Erwartung ist eindeutig.
  const basis = { count: 100, depth: 5, maxKids: 10, headKids: 20,
                  maxKidsElement: 'html > head' };
  const fall = (over) => ({ ...basis, ...over });
  const lighthouse = budgets.lighthouse;
  const frueh = budgets.fruehwarnung;
  const faelle = [
    ['unter allen Schwellen grün', basis, 0, 0],
    // Der Fall, der den ersten PR-Gate-Lauf rot machte: 1109 Elemente sind
    // zur Laufzeit normal (Erweiterungsschicht), ausgeliefert aber auffällig.
    ['Laufzeit 1109 Elemente ist kein Befund', fall({ count: 1109 }), 0, 0, true],
    ['ausgeliefert wären 1109 eine Frühwarnung', fall({ count: 1109 }), 0, 1, false],
    ['Laufzeit über der Lighthouse-Grenze ist rot',
      fall({ count: lighthouse.elements + 1 }), 1, 0, true],
    ['exakt an der Lighthouse-Grenze: Frühwarnung, nicht rot',
      fall({ count: lighthouse.elements }), 0, 1],
    ['ein Element über der Lighthouse-Grenze ist rot',
      fall({ count: lighthouse.elements + 1 }), 1, 0],
    ['Elemente in der Frühwarnung bleiben grün',
      fall({ count: frueh.elements + 1 }), 0, 1],
    ['Tiefe über der Lighthouse-Grenze ist rot',
      fall({ depth: lighthouse.depth + 1 }), 1, 0],
    ['Tiefe in der Frühwarnung bleibt grün',
      fall({ depth: frueh.depth + 1 }), 0, 1],
    ['Kinder über der Lighthouse-Grenze sind rot',
      fall({ maxKids: lighthouse.children + 1 }), 1, 0],
    ['Kinder in der Frühwarnung bleiben grün',
      fall({ maxKids: frueh.children + 1 }), 0, 1],
    ['Head über der Lighthouse-Grenze ist rot',
      fall({ headKids: lighthouse.head_children + 1 }), 1, 0],
    ['Head in der Frühwarnung bleibt grün',
      fall({ headKids: frueh.head_children + 1 }), 0, 1],
  ];
  let fehler = 0;
  for (const [name, metrics, wantIssues, wantWarnings, runtime] of faelle) {
    const { issues, warnings } = evaluateBudgets(metrics, budgets, !!runtime);
    if (issues.length !== wantIssues || warnings.length !== wantWarnings) {
      fehler++;
      console.error(`✗ ${name}: issues=${issues.length} (erwartet `
        + `${wantIssues}), warnings=${warnings.length} (erwartet ${wantWarnings})`);
    }
  }
  if (fehler) {
    console.error(`Selbsttest FEHLGESCHLAGEN (${fehler} von ${faelle.length})`);
    process.exit(1);
  }
  console.log(JSON.stringify({
    selftest: 'ok', cases: faelle.length,
    vertrag: 'nur Lighthouse-Grenzen und Fehler sind rot, Frühwarnungen grün; '
      + 'Laufzeit-DOM und ausgelieferte HTML haben eigene Frühwarnwerte',
  }));
  process.exit(0);
}

/** DOM-Kennzahlen der aktuell geladenen Seite (im Browserkontext). */
async function measureDom(page) {
  return page.evaluate(() => {
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
}

/** Die Seite laden und vermessen, wie Leser sie bekommen (Laufzeit-DOM). */
async function loadRuntime(browser, url, viewport) {
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
  const metrics = await measureDom(page);
  const title = await page.title();
  const h1 = await page.evaluate(() => {
    const el = document.querySelector('h1');
    return el ? el.textContent.trim().slice(0, 60) : null;
  });
  return { page, metrics, title, h1, errors, httpErrors, loadMs };
}

/** Die ausgelieferte HTML im Sandbox-Iframe parsen: echter Browserparser,
 *  keine Skriptausführung, kein Netz, kein Cache. */
async function measureShippedHtml(page, htmlText) {
  return page.evaluate(async (text) => {
    const iframe = document.createElement('iframe');
    // allow-same-origin ohne allow-scripts: Der Parent darf den DOM lesen,
    // im Iframe läuft nichts.
    iframe.setAttribute('sandbox', 'allow-same-origin');
    iframe.setAttribute('aria-hidden', 'true');
    iframe.style.cssText =
      'position:fixed;left:-9999px;top:0;width:320px;height:240px;border:0';
    const geladen = new Promise(res => iframe.addEventListener('load', res,
                                                               { once: true }));
    iframe.srcdoc = text;
    document.body.appendChild(iframe);
    await geladen;
    const doc = iframe.contentDocument;
    if (!doc || !doc.documentElement) return { fehler: 'kein Dokument' };
    const all = doc.querySelectorAll('*');
    let depth = 0, maxKids = 0, maxKidsNode = null;
    for (const el of all) {
      let d = 0, n = el;
      while (n && n !== doc.documentElement) { d++; n = n.parentElement; }
      if (d > depth) depth = d;
      if (el.children.length > maxKids) {
        maxKids = el.children.length;
        maxKidsNode = el;
      }
    }
    const chain = (el) => {
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
    const result = {
      count: all.length,
      depth,
      maxKids,
      maxKidsElement: chain(maxKidsNode),
      headKids: doc.head ? doc.head.children.length : 0,
      scriptsInHtml: doc.querySelectorAll('script[src]').length,
      noscriptBloecke: doc.querySelectorAll('noscript').length,
    };
    iframe.remove();
    return result;
  }, htmlText);
}

/** Datei zur URL (Pretty-URLs: /pfad/ → public/pfad/index.html). */
function fileForUrl(urlPath) {
  const rel = decodeURIComponent(urlPath.replace(/^\//, ''));
  const kandidaten = [
    path.join(BASE, rel, 'index.html'),
    path.join(BASE, rel),
    path.join(BASE, rel.replace(/\/$/, '') + '.html'),
  ];
  return kandidaten.find(p => { try { return fs.statSync(p).isFile(); }
                                catch (e) { return false; } }) || null;
}

async function auditPage(browser, url, viewport, ctx) {
  // 1) Laufzeit: die Seite, wie Leser sie bekommen.
  const laufzeit = await loadRuntime(browser, url, viewport);
  const metrics = laufzeit.metrics;
  const errors = laufzeit.errors;
  const httpErrors = laufzeit.httpErrors;
  const loadMs = laufzeit.loadMs;
  const title = laufzeit.title;
  const h1 = laufzeit.h1;

  // Instrumentenprüfung: Die Referenz ist nur brauchbar, wenn die Datei lesbar
  // war und der Sandbox-Parser Elemente gesehen hat. Eine stille Null würde
  // echte Parser-Fehler verstecken.
  const quelle = fileForUrl(new URL(url).pathname);
  let html = { fehler: 'Datei nicht gefunden' };
  if (quelle) {
    try {
      html = await measureShippedHtml(laufzeit.page, fs.readFileSync(quelle,
                                                                    'utf8'));
    } catch (err) {
      html = { fehler: 'srcdoc-Messung: ' + err.message };
    }
  }
  const instrumentOk = !html.fehler && html.count > 0;
  await laufzeit.page.close();

  const { issues, warnings } = evaluateBudgets(metrics, ctx.budgets, true);
  const drift = [];
  if (errors.length) issues.push(...errors.slice(0, 5));
  if (httpErrors.length) issues.push(...httpErrors.slice(0, 5));
  if (!title) issues.push('kein <title>');
  if (!h1) issues.push('kein <h1>');
  if (!instrumentOk) {
    issues.push('Referenzmessung unbrauchbar (' + (html.fehler
      || 'Sandbox-Parser sah 0 Elemente') + ') – die Parser-Gegenrechnung '
      + 'wäre wertlos, deshalb ist das ein harter Befund');
  }

  // ---------- Parser-Gegenrechnung (Issue #338, Lehre 3) ----------
  const stat = staticMetrics(ctx.domAudit, new URL(url).pathname);
  const deltas = {};
  if (stat) {
    // Referenz ist die HTML-Messung (Fremd-Skripte ersetzt), nicht die
    // Laufzeitmessung – Begründung im Kopf dieser Datei.
    const pairs = [
      ['headchildren', html.headKids, stat.headchildren],
      ['maxChildren', html.maxKids, stat.maxchildren],
      ['depth', html.depth, stat.depth],
      ['totalElements', html.count, stat.elements],
    ];
    for (const [key, browserValue, parserValue] of pairs) {
      const delta = Math.abs(browserValue - parserValue);
      deltas[key] = delta;
      if (delta > TOLERANCE[key]) {
        drift.push(`${key}: Referenz ${browserValue} vs. Parser ${parserValue} `
          + `(Δ${delta} > Toleranz ${TOLERANCE[key]})`);
      }
    }
  }

  if (drift.length) {
    issues.push(...drift.map(d => `Parser-Drift: ${d}`));
  }

  return {
    url,
    viewport: viewport.width + 'x' + viewport.height,
    // Laufzeit-DOM (Nutzerrealität, gegen die Laufzeit-Budgets geprüft)
    domCount: metrics.count,
    domDepth: metrics.depth,
    maxChildren: metrics.maxKids,
    maxChildrenElement: metrics.maxKidsElement,
    headChildren: metrics.headKids,
    // Referenzmessung: ausgelieferte HTML im Sandbox-Iframe (Parser-Vergleich)
    htmlOnly: instrumentOk ? {
      count: html.count,
      depth: html.depth,
      maxKids: html.maxKids,
      headKids: html.headKids,
      maxKidsElement: html.maxKidsElement,
      scriptsInHtml: html.scriptsInHtml,
      noscriptBloecke: html.noscriptBloecke,
    } : { count: -1, fehler: html.fehler || 'unbrauchbar' },
    instrumentOk,
    // Rohdeltas Referenz↔Parser, damit jede Toleranz nachmessbar ist
    staticVsHtml: deltas,
    staticMetrics: stat ? {
      elements: stat.elements, depth: stat.depth,
      maxChildren: stat.maxchildren, headChildren: stat.headchildren,
    } : null,
    parserDrift: drift,
    loadMs,
    title: title.slice(0, 60),
    h1,
    issues,
    warnings,
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

if (SELFTEST) {
  runSelftest();
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
  const warnPages = results.filter(r => r.warnings.length > 0);
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
  const erweiterung = results.map(r => r.domCount - r.htmlOnly.count);
  const htmlMax = (key) => Math.max(...results.filter(r => r.instrumentOk)
                                           .map(r => r.htmlOnly[key]));
  const summary = {
    checked: results.length,
    domMetricsHtmlOnly: {
      maxElements: htmlMax('count'),
      maxDepth: htmlMax('depth'),
      maxChildren: htmlMax('maxKids'),
      maxHeadChildren: htmlMax('headKids'),
    },
    // Nachgemessene Erweiterungsschicht (Laufzeit − HTML): dokumentiert, damit
    // die Zahlen im Report nicht als Widerspruch gelesen werden.
    erweiterungsschicht: {
      max: Math.max(...erweiterung),
      min: Math.min(...erweiterung),
      hinweis: 'Laufzeit-DOM minus HTML-Messung (Premium-Layer: '
        + 'Mini-Inhaltsübersicht, Anker, Fortschrittsleiste, Lesehilfen)',
    },
    sample: sample.urls.map(u => new URL(u).pathname),
    riskPages: sample.risk,
    budgets: ctx.budgets,
    domMetrics: agg,
    parserCheck: {
      compared: results.filter(r => r.staticMetrics).length,
      referenceUsable: results.every(r => r.instrumentOk),
      tolerance: TOLERANCE,
      maxDelta: results.reduce((max, r) => Math.max(max, ...Object.values(
        r.staticVsHtml || {}).concat(0)), 0),
      tolerated: TOLERANCE,
      drift: drift.map(r => ({ url: r.url, viewport: r.viewport, drift: r.parserDrift })),
    },
    criticalPages: critical.map(r => ({
      url: r.url, viewport: r.viewport, issues: r.issues,
    })),
    warningPages: warnPages.map(r => ({
      url: r.url, viewport: r.viewport, warnings: r.warnings,
    })),
    allOk: critical.length === 0,
    greenWithWarnings: critical.length === 0 && warnPages.length > 0,
  };
  console.log(JSON.stringify(summary, null, 2));
  process.exit(critical.length ? 1 : 0);
})();
