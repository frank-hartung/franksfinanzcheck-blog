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
 *   - Max. Kinder pro Knoten (nur <body>-Inhalt; <head>-Metadaten sind
 *     by-design und werden nicht als Budget-Verstoß gewertet)
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
 * der Parser – Skripte hängen Knoten in den `<head>` (z. B. das
 * `<link rel="prefetch">` des Hover-Prefetch in static/premium/ff-premium.js,
 * +1 Kind), Theme-Klassen ändern nur Attribute. Unterschiede darüber hinaus
 * sind Parser-Drift und werden als Befund gemeldet.
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
 * Ausgabe: JSON auf stdout + Exit-Codes (Meldung #900, 30.10.2026 – die
 * Bedeutung von 2 und 3 war vorher vermischt):
 *   0 = grün (oder nur Frühwarnungen)
 *   1 = harte Befunde auf den geprüften Seiten
 *   2 = WEICH übersprungen: kein Chrome / kein puppeteer-core. Das ist eine
 *       Umgebungsgrenze, kein Befund – das statische DOM-Budget hat trotzdem
 *       JEDE Seite vermessen.
 *   3 = WERKZEUGFEHLER (fail-closed): der Bau ist leer/unvollständig, die
 *       Seite ließ sich nicht messen oder das JSON ist unbrauchbar. Früher
 *       lief der Audit in diesem Fall gegen ein leeres `public/` und meldete
 *       „404 /, kein <title>, kein <h1>" als Layout-Befunde (Meldung #900) –
 *       eine Fehldiagnose, die den Blick auf den toten Bau verstellte.
 *
 * Aufruf:
 *   LAYOUT_BASE=/pfad/zum/public CHROME_PATH=... \
 *     node scripts/layout_browser_check.js
 *   LAYOUT_PORT wird nur noch für Sonderfälle gesetzt; Standard ist ein
 *   freier Port (0), damit ein belegter Port keinen Werkzeugfehler erzeugt.
 */
const SELFTEST = process.argv.includes('--selftest');
const http = require('http');
const crypto = require('crypto');
const os = require('os');
const fs = require('fs');
const path = require('path');

// Erst laden, wenn wirklich gemessen wird: Der Selftest (Budget-/Severity-
// Vertrag) und die Bau-Vorprüfung müssen OHNE Puppeteer laufen können –
// sonst meldet eine Umgebung ohne Browser immer „übersprungen" (Exit 2),
// selbst wenn der eigentliche Fehler ein leerer Bau ist (Exit 3).
function ladePuppeteer() {
  try {
    return require('puppeteer-core');
  } catch (err) {
    console.error('Werkzeugfehler: puppeteer-core nicht installiert ('
      + err.message + ') – Browser-Audit übersprungen (Exit 2, das statische '
      + 'DOM-Budget hat jede Seite vermessen).');
    return null;
  }
}

const BASE = process.env.LAYOUT_BASE || path.join(__dirname, '..', 'public');
// 0 = freier Port. Ein fester Port (früher 8099) kollidierte mit jedem
// zweiten Lauf auf demselben Rechner und endete als Werkzeugfehler.
const PORT = parseInt(process.env.LAYOUT_PORT || '0', 10);
// Mindestumfang eines messbaren Baus – identisch zu scripts/layout_audit.py.
// Eine Messung über 0 Seiten darf nie grün sein (Meldung #900).
const MIN_SEITEN = 20;
const MIN_ARTIKEL = 1;
const CHROME = process.env.CHROME_PATH || '';
const DOM_JSON = process.env.LAYOUT_DOM_JSON ||
  path.join(__dirname, '..', '.cache', 'layout', 'dom-audit.json');
// EINE Quelle für die CSP der Messung: die Datei, die auch ausgeliefert würde.
// Sie liegt nach dem Bau unter <BASE>/_headers (Hugo kopiert static/ dorthin);
// im Quellbaum ist es static/_headers. Beide werden in dieser Reihenfolge
// gelesen – so misst der Audit den Sollstand des Repositories, nicht den
// Kopfzeilen-Zufall der Umgebung.
const HEADERS_DATEI = path.join(__dirname, '..', 'static', '_headers');
const EXTRA_RISK_PAGES = parseInt(process.env.LAYOUT_RISK_PAGES || '3', 10);
// Laufzeit-Zugaben des Browsers (siehe Kopf): nachträglich eingehängte
// Prefetch-Links im <head>, ggf. Sentinel-Div aus dem Top-Link-Skript
// (Body-Ebene, zählt nur in „elements").
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

/**
 * CSP aus einer `_headers`-Datei lesen (Format Cloudflare Pages / Netlify).
 *
 * WARUM DAS HIER STEHT (21.11.2026): Der Audit hat bisher GAR KEINE CSP
 * gesetzt. Was der Browser an CSP sah, kam von außen – und war damit nicht die
 * CSP dieses Repositories. Genau das war der offene Widerspruch: „die CSP der
 * Umgebung ist veraltet, sie ist nur nicht die dieses Repositories“.
 *
 * Jetzt liefert der Messserver die CSP aus `static/_headers` selbst aus. Die
 * Messung prüft damit den Sollstand des Repos und kann von einer fremden
 * Kopfzeile nur noch ERGÄNZT, nicht mehr ersetzt werden – und genau diese
 * Ergänzung wird als Fremdquelle ausgewiesen (siehe `cspQuelle` unten).
 *
 * Rückgabe: der Wert der Regel `/*` oder null (dann fail-closed in `main`).
 */
function cspAusHeaders(text) {
  const zeilen = String(text || '').split(/\r?\n/);
  let imBlock = false;
  for (const zeile of zeilen) {
    const ohneKommentar = zeile.replace(/\s+#.*$/, '');
    const kern = ohneKommentar.trim();
    if (!kern) continue;
    // Regelkopf beginnt in Spalte 0. `/*` ist die Regel für alle Pfade.
    if (!/^\s/.test(ohneKommentar)) {
      imBlock = kern === '/*';
      continue;
    }
    if (!imBlock) continue;
    const treffer = ohneKommentar.match(
      /^\s{2,}Content-Security-Policy:\s*(.+?)\s*$/i);
    if (treffer) return treffer[1];
  }
  return null;
}

/**
 * Die CSP, die der Messserver ausliefert – ohne `frame-ancestors`.
 *
 * WARUM (21.11.2026): `frame-ancestors` ist eine reine Header-Direktive. Sie
 * regelt, WER die Seite einbetten darf, und wird bei `about:srcdoc` vom
 * Eltern-Dokument geerbt. Im Audit würde sie damit die eigene
 * Referenzmessung (Sandbox-Iframe) blockieren, ohne etwas über Skripte,
 * Stile oder Verbindungen der Seite zu sagen. Sie bleibt im Sollstand und
 * wird von `blog_header_gate.py` (offline S1, live) geprüft – ausgeliefert
 * für die Messung wird sie nicht.
 */
function cspFuerMessung(csp) {
  return String(csp || '').split(';')
    .map(teil => teil.trim())
    .filter(teil => teil && !/^frame-ancestors\b/i.test(teil))
    .join('; ');
}

/** Liegt die URL auf der Herkunft der Messung (Schema + Host + Port)? */
function istEigeneHerkunft(url, herkunft) {
  try {
    return new URL(url).origin === herkunft;
  } catch (e) {
    return false;
  }
}

/**
 * Ist die Datei eine Weiterleitungsseite (Meta-Refresh auf eine fremde URL)?
 *
 * DER BEFUND (21.11.2026): `buildSampleUrls` nahm die lexikografisch letzten
 * drei Verzeichnisse unter `posts/`. Das sind keine neuen Artikel, sondern
 * Altlasten ohne Datumspräfix – 251 Meta-Refresh-Seiten aus
 * `scripts/weiterleitungen.py`. Chrome folgt dem Refresh nach
 * `https://franksfinanzcheck.de/...`; der Audit misst dann die PRODUKTION,
 * obwohl in der Meldung `http://127.0.0.1:…` steht. Die dort beobachtete CSP
 * (ohne die beiden Beacon-Domains) und der von Cloudflare injizierte Beacon
 * stammen aus der Edge-Regel – nicht aus dem Runner. Deshalb wird eine solche
 * Seite gar nicht erst als Artikelprobe verwendet.
 */
function istWeiterleitungsseite(html) {
  if (typeof html !== 'string' || !html) return false;
  if (/<meta\b[^>]*\bname\s*=\s*["']ff-weiterleitung["']/i.test(html)) return true;
  return /<meta\b[^>]*\bhttp-equiv\s*=\s*["']refresh["'][^>]*\bcontent\s*=\s*["'][^"']*url\s*=\s*https?:/i
    .test(html);
}

/** `2026-11-21-slug` → `2026-11-21`; alles ohne Datumspräfix → null. */
function slugDatum(name) {
  const treffer = /^(\d{4}-\d{2}-\d{2})-/.exec(String(name || ''));
  return treffer ? treffer[1] : null;
}

/**
 * Die wirklich neuesten Artikel – nicht die alphabetisch letzten.
 *
 * Sortiert nach Datumspräfix (absteigend), prüft jeden Kandidaten auf die
 * Weiterleitungs-Marke und überspringt Altlasten wie `…(1)`. Es werden so
 * viele Dateien gelesen, bis `anzahl` echte Artikel beisammen sind.
 */
function neuesteArtikel(postsDir, anzahl) {
  let eintraege = [];
  try {
    eintraege = fs.readdirSync(postsDir, { withFileTypes: true })
      .filter(d => d.isDirectory()
        && fs.existsSync(path.join(postsDir, d.name, 'index.html')))
      .map(d => ({ name: d.name, datum: slugDatum(d.name) }))
      .filter(x => x.datum && /^[a-z0-9][a-z0-9-]{0,159}$/.test(x.name))
      .sort((a, b) => b.datum.localeCompare(a.datum)
        || b.name.localeCompare(a.name));
  } catch (e) {
    return { artikel: [], weiterleitungen: [] };
  }
  const artikel = [];
  const weiterleitungen = [];
  for (const k of eintraege) {
    if (artikel.length >= anzahl) break;
    let text = '';
    try {
      text = fs.readFileSync(path.join(postsDir, k.name, 'index.html'), 'utf8');
    } catch (e) {
      continue;
    }
    if (istWeiterleitungsseite(text)) {
      weiterleitungen.push(k.name);
      continue;
    }
    artikel.push(k.name);
  }
  return { artikel, weiterleitungen };
}

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

function serve(baseDir, port, optionen = {}) {
  const csp = optionen.csp || '';
  const nonce = optionen.nonce || '';
  const cspDigest = optionen.cspDigest || '';
  const server = http.createServer((req, res) => {
    let p = decodeURIComponent(req.url.split('?')[0]);
    if (p.endsWith('/')) p += 'index.html';
    let file = path.normalize(path.join(baseDir, p));
    if (file !== baseDir && !file.startsWith(baseDir + path.sep)) {
      res.writeHead(403); res.end(); return;
    }
    fs.readFile(file, (err, data) => {
      if (err) { res.writeHead(404); res.end('not found'); return; }
      const ext = path.extname(file);
      const types = {'.html': 'text/html', '.css': 'text/css', '.js': 'application/javascript',
                     '.jpg': 'image/jpeg', '.png': 'image/png', '.webp': 'image/webp',
                     '.avif': 'image/avif', '.woff2': 'font/woff2', '.svg': 'image/svg+xml',
                     '.xml': 'application/xml', '.txt': 'text/plain', '.json': 'application/json'};
      // Die Herkunft ist der Audit selbst. Deshalb kann er genau sagen, welche
      // Kopfzeilen ER gesetzt hat – jede zusätzliche CSP ist damit als fremd
      // belegbar (Nonce + Digest reisen mit).
      const kopf = {
        'Content-Type': types[ext] || 'application/octet-stream',
        'X-FF-Audit-Nonce': nonce,
        'Cache-Control': 'no-store',
      };
      if (ext === '.html' && csp) {
        kopf['Content-Security-Policy'] = csp;
        kopf['X-FF-Audit-CSP'] = cspDigest;
      }
      res.writeHead(200, kopf);
      res.end(data);
    });
  });
  // EADDRINUSE ist kein Audit-Befund: Lieber auf einem freien Port messen als
  // den Lauf mit einem Werkzeugfehler beenden.
  return new Promise((resolve, reject) => {
    server.once('error', (err) => {
      if (err && err.code === 'EADDRINUSE' && port !== 0) {
        // WICHTIG: Optionen (CSP, Nonce, Digest) müssen mitwandern. Sonst
        // lieferte der Ausweich-Port Seiten ohne eigene CSP – und der Audit
        // hielte jede CSP-Meldung für unbelegt (Frühwarnung statt Befund).
        serve(baseDir, 0, optionen).then(resolve, reject);
        return;
      }
      reject(err);
    });
    server.listen(port, '127.0.0.1', () => resolve(server));
  });
}

/**
 * Ist der Bau überhaupt messbar? (Meldung #900, 30.10.2026)
 *
 * Am 26.10.2026 lief der Browser-Audit gegen ein `public/` mit Bruchstücken
 * und meldete „404 http://127.0.0.1:8099/, kein <title>, kein <h1>" als
 * LAYOUT-BEFUNDE. Das war keine Messung, sondern eine Fehldiagnose: Der Fehler
 * lag im Bau. Rückgabe: null = messbar, sonst Klartext-Grund (Exit 3).
 */
function pruefeBaubasis() {
  let stat = null;
  try { stat = fs.statSync(BASE); } catch (err) { stat = null; }
  if (!stat || !stat.isDirectory()) {
    return `Bauverzeichnis ${BASE} fehlt – erst \`hugo\` bauen`;
  }
  const index = path.join(BASE, 'index.html');
  if (!fs.existsSync(index)) return `${index} fehlt (kein Bau)`;
  const posts = path.join(BASE, 'posts');
  if (!fs.existsSync(posts)) return `${posts} fehlt (kein Bau)`;
  let seiten = 0;
  let artikel = 0;
  try {
    seiten = fs.readdirSync(BASE, { recursive: true })
      .filter(f => String(f).endsWith('.html')).length;
    artikel = fs.readdirSync(posts, { withFileTypes: true })
      .filter(d => d.isDirectory()
        && fs.existsSync(path.join(posts, d.name, 'index.html'))).length;
  } catch (err) {
    return `Bau nicht lesbar (${err.message})`;
  }
  if (seiten < MIN_SEITEN) {
    return `nur ${seiten} HTML-Seiten gefunden (Mindestumfang ${MIN_SEITEN})`;
  }
  if (artikel < MIN_ARTIKEL) return 'keine Artikel-Seite unter posts/ gefunden';
  return null;
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

  // ---- Hermetik-Vertrag (21.11.2026) ---------------------------------
  // Diese Fälle brauchen KEIN Chrome: Es sind die Entscheidungen, an denen
  // der Fehlbefund vom 21.11.2026 hing (Weiterleitung → Produktion).
  const hermetik = [];
  const pruefe = (name, ist, soll) => hermetik.push([name, ist, soll]);

  let csp = null;
  try { csp = cspAusHeaders(fs.readFileSync(HEADERS_DATEI, 'utf8')); }
  catch (e) { csp = null; }
  pruefe('CSP aus static/_headers lesbar', !!csp, true);
  pruefe('CSP nennt script-src', /(^|;)\s*script-src\s/.test(csp || ''), true);
  pruefe('CSP nennt Beacon-Skript-Domain',
    /static\.cloudflareinsights\.com/.test(csp || ''), true);
  pruefe('CSP nennt Beacon-Messdomain',
    /(^|[\s;])https:\/\/cloudflareinsights\.com/.test(csp || ''), true);
  pruefe('_headers ohne CSP ergibt null',
    cspAusHeaders('/*\n  X-Test: 1\n\n/images/*\n  Cache-Control: max-age=1\n'), null);
  pruefe('CSP in Kommentarzeile zählt nicht',
    cspAusHeaders('# Content-Security-Policy: default-src *\n/*\n  X-Test: 1\n'), null);
  const fuerMessung = cspFuerMessung(csp);
  pruefe('frame-ancestors wird für die Messung entfernt',
    /frame-ancestors/i.test(fuerMessung), false);
  pruefe('default-src bleibt erhalten',
    /(^|;)\s*default-src\s/.test(fuerMessung), true);
  pruefe('script-src bleibt erhalten',
    /(^|;)\s*script-src\s/.test(fuerMessung), true);
  pruefe('fehlende CSP bleibt leer', cspFuerMessung(null), '');

  pruefe('gleiche Herkunft ist eigene',
    istEigeneHerkunft('http://127.0.0.1:1234/a', 'http://127.0.0.1:1234'), true);
  pruefe('Produktion ist fremde Herkunft',
    istEigeneHerkunft('https://franksfinanzcheck.de/x', 'http://127.0.0.1:1234'), false);
  pruefe('unparsebare URL ist nicht eigene',
    istEigeneHerkunft('keine-url', 'http://127.0.0.1:1'), false);

  const stubDatei = path.join(__dirname, '..', 'static', 'posts',
    'zinseszinseffekt-formel-erklaert', 'index.html');
  if (fs.existsSync(stubDatei)) {
    pruefe('echte Alt-Seite ist eine Weiterleitung',
      istWeiterleitungsseite(fs.readFileSync(stubDatei, 'utf8')), true);
  }
  pruefe('normale Seite ist keine Weiterleitung',
    istWeiterleitungsseite('<html><head><title>x</title></head><body><h1>x</h1></body></html>'),
    false);

  // Sample-Regel an einem künstlichen Bau: Datum gewinnt, Weiterleitung
  // und Altlast ohne Datum fallen raus.
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'ff-layout-'));
  try {
    const anlegen = (name, html) => {
      const d = path.join(tmp, name);
      fs.mkdirSync(d);
      fs.writeFileSync(path.join(d, 'index.html'), html, 'utf8');
    };
    const normal = '<html><head><title>x</title></head><body><h1>x</h1></body></html>';
    anlegen('2026-01-01-normal', normal);
    anlegen('2026-01-02-neuer', normal);
    anlegen('2025-12-31-alt', '<meta name="ff-weiterleitung" content="regel-C">'
      + '<meta http-equiv="refresh" content="0; url=https://franksfinanzcheck.de/x/">');
    anlegen('z-altlast', '<meta http-equiv="refresh" '
      + 'content="0; url=https://franksfinanzcheck.de/y/">');
    const gewaehlt = neuesteArtikel(tmp, 3);
    pruefe('Sample nimmt den neuesten datierten Artikel zuerst',
      gewaehlt.artikel[0], '2026-01-02-neuer');
    pruefe('Weiterleitung ist nicht im Sample',
      gewaehlt.artikel.includes('2025-12-31-alt'), false);
    pruefe('Altlast ohne Datumspräfix ist nicht im Sample',
      gewaehlt.artikel.includes('z-altlast'), false);
    pruefe('Weiterleitung wird ausgewiesen',
      gewaehlt.weiterleitungen.includes('2025-12-31-alt'), true);
  } finally {
    try { fs.rmSync(tmp, { recursive: true, force: true }); } catch (e) {}
  }

  for (const [name, ist, soll] of hermetik) {
    if (JSON.stringify(ist) !== JSON.stringify(soll)) {
      fehler++;
      console.error(`✗ ${name}: ${JSON.stringify(ist)} (erwartet ${JSON.stringify(soll)})`);
    }
  }

  if (fehler) {
    console.error(`Selbsttest FEHLGESCHLAGEN (${fehler} von `
      + `${faelle.length + hermetik.length})`);
    process.exit(1);
  }
  console.log(JSON.stringify({
    selftest: 'ok', cases: faelle.length + hermetik.length,
    budgetFaelle: faelle.length, hermetikFaelle: hermetik.length,
    vertrag: 'nur Lighthouse-Grenzen und Fehler sind rot, Frühwarnungen grün; '
      + 'Laufzeit-DOM und ausgelieferte HTML haben eigene Frühwarnwerte; '
      + 'CSP kommt aus static/_headers, fremde Herkünfte werden abgebrochen, '
      + 'Weiterleitungsseiten sind keine Artikelprobe',
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
      // Kinder werden für ALLE Elemente gezählt – auch für <head>. Genau
      // dieser Wert war der Befund in Issue #338 („Max. Kinder 59 > 58,
      // Element: html > head"), und die Antwort darauf war, den Head
      // strukturell zu verkleinern (60 → 49: article:tag, doppelte
      // hreflang-Zeile, Apple-Status-Bar, Skripte ans Body-Ende), nicht die
      // Metrik zu verengen. Eine Prüfung, die ihren eigenen Befund
      // ausblendet, wird beim nächsten Wachstum still – deshalb bleibt der
      // Head im Budget (Frühwarnung 52, harte Grenze 58).
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

/** Die Seite laden und vermessen, wie Leser sie bekommen (Laufzeit-DOM).
 *
 *  HERMETISCH SEIT 21.11.2026
 *  --------------------------
 *  Der Audit misst NUR den lokalen Bau. Jede Hauptnavigation, die die eigene
 *  Herkunft (127.0.0.1:<port>) verlassen will, wird abgebrochen. Grund: Der
 *  Bericht vom 21.11.2026 zeigte `http://127.0.0.1:43437/posts/…` als
 *  Befund-URL, die gemessene CSP und der blockierte Beacon kamen aber aus
 *  der PRODUKTION. Ursache waren Meta-Refresh-Seiten aus
 *  `scripts/weiterleitungen.py`, die der Browser still verfolgt hat.
 *
 *  Was der Browser tatsächlich sieht, wird belegt: Nonce und CSP-Digest
 *  reisen mit jeder Antwort des Messservers. Stimmt die beobachtete
 *  Dokument-CSP nicht mit der ausgelieferten überein, ist sie als
 *  FREMDQUELLE ausgewiesen – und ein CSP-Verstoß daraus ist kein Befund
 *  über diese Seite.
 */
async function loadRuntime(browser, url, viewport, ctx) {
  const page = await browser.newPage();
  await page.setViewport(viewport);
  // Kein HTTP-Cache: Ein Dokument aus dem Cache kann ohne seine Kopfzeilen
  // zurückkommen. Genau diese Kopfzeilen sind hier der Beleg – der Audit muss
  // sie vom Messserver sehen, nicht aus einem Zwischenspeicher erraten.
  try { await page.setCacheEnabled(false); } catch (e) { /* alt genug: egal */ }
  const eigeneHerkunft = ctx.herkunft || new URL(url).origin;
  const gesendet = ctx.csp || '';
  const errors = [];
  const httpErrors = [];
  const fremdnav = [];
  // Sammel-Schalter: Nach dem Laden wird die Referenzmessung im Sandbox-Iframe
  // erzeugt. Chrome protokolliert dabei „Blocked script execution in
  // 'about:srcdoc' … (sandbox)" als Konsolenfehler – das ist ein Artefakt
  // MEINES Messinstruments, kein Fehler der Seite. Es darf deshalb weder als
  // Befund noch als Fehlalarm durchschlagen: erst aufhören zu sammeln, und
  // ersatzweise nur Botschaften ignorieren, die eindeutig zur iframe-Sandbox
  // gehören (about:srcdoc UND sandbox/allow-scripts).
  const sammlung = { aktiv: true };
  const sandboxArtefakt = (text) => /about:srcdoc/.test(text)
    && /sandbox|allow-scripts/i.test(text);
  // Eigene Abbrüche erzeugen ebenfalls Konsolenzeilen. Sie sind der Beweis,
  // dass die Hermetik greift – kein Seitenfehler.
  const eigenerAbbruch = (text) => fremdnav.length > 0
    && /ERR_BLOCKED_BY_CLIENT|ERR_ABORTED|blockedbyclient/i.test(text);

  // ---- Hermetik: keine Hauptnavigation verlässt die eigene Herkunft ----
  await page.setRequestInterception(true);
  page.on('request', req => {
    let eigene = true;
    try {
      const istHauptnavigation = req.isNavigationRequest()
        && req.frame() === page.mainFrame()
        && /^https?:/i.test(req.url());
      if (istHauptnavigation && !istEigeneHerkunft(req.url(), eigeneHerkunft)) {
        eigene = false;
      }
    } catch (e) {
      eigene = true;   // nicht entscheidbar → dem Browser nicht in den Weg stellen
    }
    if (!eigene) {
      fremdnav.push(req.url());
      ctx.fremdnav.push(req.url());
      req.abort('blockedbyclient').catch(() => {});
      return;
    }
    req.continue().catch(() => {});
  });

  const cspBefund = (text) => /Content Security Policy/i.test(text);
  page.on('pageerror', e => {
    if (sammlung.aktiv && !sandboxArtefakt(e.message) && !eigenerAbbruch(e.message)) {
      errors.push('JS: ' + e.message);
    }
  });
  const cspMeldungen = [];      // vorläufig: CSP-Verstoß, Beleg noch offen
  const unbelegt = [];
  page.on('console', m => {
    if (!sammlung.aktiv || m.type() !== 'error' || sandboxArtefakt(m.text())) return;
    if (eigenerAbbruch(m.text())) return;
    if (cspBefund(m.text())) {
      // Die CSP-Kopfzeile kann NACH dem ersten Skriptfehler eintreffen
      // (z. B. bei Umleitungen). Ob sie existiert, entscheidet sich erst
      // am Ende der Messung – siehe die Auswertung nach page.goto().
      cspMeldungen.push(m.text());
      return;
    }
    errors.push('console: ' + m.text());
  });
  const cspBeobachtet = [];     // {wert, url, eigene}
  page.on('response', r => {
    if (r.status() >= 400) httpErrors.push(r.status() + ' ' + r.url());
    // NUR die Dokument-Antwort kann eine Seite per CSP steuern. Die erste
    // Fassung sammelte Kopfzeilen von JEDER Antwort – ein Beleg aus der
    // Antwort eines Skripts/Bildes sagt nichts über diese Seite.
    if (!/^(document|iframe)$/i.test(String(r.request().resourceType()))) return;
    try {
      const wert = (r.headers() || {})['content-security-policy'];
      if (!wert) return;
      cspBeobachtet.push({
        wert: String(wert),
        url: r.url(),
        eigene: istEigeneHerkunft(r.url(), eigeneHerkunft),
      });
    } catch (e) { /* Kopfzeilen nicht lesbar: kein Beleg, kein Befund */ }
  });

  const t0 = Date.now();
  await page.goto(url, { waitUntil: 'networkidle0', timeout: 45000 })
    .catch(e => errors.push('load: ' + e.message));
  const loadMs = Date.now() - t0;

  // Wo steht die Messung am Ende – und welche CSP hat sie wirklich gesehen?
  const endUrl = page.url();
  const herkunftOk = istEigeneHerkunft(endUrl, eigeneHerkunft);
  const normal = (s) => String(s || '').replace(/\s+/g, ' ').trim();
  const eigeneCsp = cspBeobachtet.filter(e => e.eigene);
  const fremdeCsp = cspBeobachtet.filter(e => !e.eigene);
  const traegtEigene = !!gesendet
    && eigeneCsp.some(e => normal(e.wert).includes(normal(gesendet)));
  const fremdherkunft = [...new Set(fremdeCsp.map(e => {
    try { return new URL(e.url).origin; } catch (x) { return e.url; }
  }))];
  const cspQuelle = {
    kopfzeile: cspBeobachtet.length > 0,
    beobachtet: cspBeobachtet.length,
    eigene: traegtEigene,
    // Warum die eigene CSP (nicht) wiedergefunden wurde – für den Bericht.
    // Ohne diesen Grund wäre „0 von 14" eine Zahl ohne Beleg.
    grund: !cspBeobachtet.length ? 'keine-kopfzeile'
      : traegtEigene ? 'eigene'
      : (fremdeCsp.length ? 'fremd' : 'abweichend'),
    fremd: fremdeCsp.length > 0 || (eigeneCsp.length > 0 && !traegtEigene),
    fremdherkunft,
    herkunft: endUrl,
    herkunftOk,
  };

  // Jetzt steht fest, woher die CSP stammt. Erst hier wird aus einem
  // CSP-Verstoß ein Befund oder ein Belegmangel.
  for (const text of cspMeldungen) {
    if (!herkunftOk) {
      unbelegt.push('Dokument kam von ' + endUrl
        + ' (Herkunft außerhalb der Messung): ' + text);
    } else if (!traegtEigene) {
      unbelegt.push('keine eigene CSP-Kopfzeile beobachtet'
        + (fremdherkunft.length ? ' (Fremd-CSP von ' + fremdherkunft.join(', ') + ')'
                                : '') + ': ' + text);
    } else if (fremdherkunft.length || (eigeneCsp.length > 0 && !traegtEigene)) {
      unbelegt.push('Fremd-CSP ergänzt die eigene ('
        + (fremdherkunft.join(', ') || 'unbekannte Herkunft') + '): ' + text);
    } else {
      errors.push('console: ' + text);
    }
  }
  const metrics = await measureDom(page);
  const title = await page.title();
  const h1 = await page.evaluate(() => {
    const el = document.querySelector('h1');
    return el ? el.textContent.trim().slice(0, 60) : null;
  });
  return { page, metrics, title, h1, errors, httpErrors, loadMs, sammlung,
           herkunftOk, endUrl, fremdnav,
           csp: { direktiven: cspBeobachtet.map(e => e.wert),
                  quelle: cspQuelle,
                  unbelegt: unbelegt.slice(0, 3) } };
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

/** Liegt unter diesem Pfad im Bau eine Weiterleitungsseite? */
function istWeiterleitungPfad(rel) {
  const datei = fileForUrl(String(rel || '/'));
  if (!datei) return false;
  try {
    return istWeiterleitungsseite(fs.readFileSync(datei, 'utf8'));
  } catch (e) {
    return false;
  }
}

async function auditPage(browser, url, viewport, ctx) {
  // 1) Laufzeit: die Seite, wie Leser sie bekommen.
  const laufzeit = await loadRuntime(browser, url, viewport, ctx);
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
    // Ab hier wird das Sandbox-Iframe gebaut: die Konsole der Seite ist
    // abgehört genug, Artefakte der eigenen Messung würden sonst zu Befunden.
    laufzeit.sammlung.aktiv = false;
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

  // CSP-Befunde OHNE Beleg wandern in die Frühwarnungen, nicht in `issues`.
  // Sie machen den Lauf nicht rot, weil sie keine Seite beschreiben, die das
  // Repo ausliefert – aber sie verschwinden auch nicht: Der Bericht nennt sie
  // samt Grund (keine CSP-Kopfzeile in dieser Messung).
  const csp = laufzeit.csp || { direktiven: [], quelle: {}, unbelegt: [] };
  for (const text of csp.unbelegt || []) {
    warnings.push('CSP-Meldung nicht dem Repository zuordenbar – kein Befund '
      + 'über diese Seite: ' + String(text).slice(0, 220));
  }
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
    // HERMETIK: Herkunft der Messung. `herkunftOk === false` heißt, die
    // Seite hat die eigene Herkunft verlassen – dann ist die Messung
    // unbrauchbar (Werkzeugfehler in main()), kein Seitenbefund.
    herkunftOk: laufzeit.herkunftOk !== false,
    herkunft: laufzeit.endUrl || url,
    fremdnav: (laufzeit.fremdnav || []).slice(0, 3),
    // Woher stammt eine CSP in dieser Messung?
    // `gesendet` = Digest der CSP aus static/_headers (die eigene),
    // `quelle.eigene` = im Dokument wiedergefunden,
    // `quelle.fremd`/`fremdherkunft` = zusätzliche/abweichende Kopfzeile.
    csp: { direktiven: (csp.direktiven || []).length,
           kopfzeile: !!(csp.quelle && csp.quelle.kopfzeile),
           eigene: !!(csp.quelle && csp.quelle.eigene),
           fremd: !!(csp.quelle && csp.quelle.fremd),
           fremdherkunft: (csp.quelle && csp.quelle.fremdherkunft) || [],
           grund: (csp.quelle && csp.quelle.grund) || 'unbekannt',
           gesendet: ctx.cspDigest || '',
           unbelegt: (csp.unbelegt || []).length,
           gesehen: (csp.direktiven || []).slice(0, 1)
             .map(d => String(d).slice(0, 200)) },
  };
}

/**
 * Sample: Startseite + 3 neueste Artikel + die statisch schwersten Seiten.
 *
 * KORREKTUR 21.11.2026: „neueste" stand hier, war aber `sort().slice(-3)` –
 * alphabetisch. Damit bestand das Sample aus Altlasten ohne Datumspräfix,
 * zuletzt zwei Meta-Refresh-Seiten, die den Browser in die Produktion
 * schickten. Jetzt: Datumspräfix absteigend, Weiterleitungsseiten raus –
 * auch aus den Risiko-Seiten des statischen Audits.
 */
function buildSampleUrls(domAudit, basisUrl) {
  const postsDir = path.join(BASE, 'posts');
  const neueste = neuesteArtikel(postsDir, 3);
  const slugs = neueste.artikel;
  const ausgelassen = [...neueste.weiterleitungen];
  const urls = [basisUrl + '/'];
  const seen = new Set(['/']);
  // Slugs und Pfade stammen aus Dateien des Builds und gehen in Anfragen.
  const SLUG_SICHER = /^[a-z0-9][a-z0-9-]{0,159}$/;
  const PFAD_SICHER = /^\/[a-z0-9][a-z0-9\/._-]{0,239}$/;
  for (const s of slugs) {
    if (!SLUG_SICHER.test(s)) continue;
    urls.push(`${basisUrl}/posts/${s}/`);
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
  const risk = [];
  for (const r of ranked) {
    if (risk.length >= Math.max(0, EXTRA_RISK_PAGES)) break;
    const rel = typeof r.rel === 'string' ? r.rel : '';
    if (!PFAD_SICHER.test(rel) || /\.\./.test(rel)) continue;
    // DER BEFUND: Auch eine Risiko-Seite kann eine Weiterleitung sein.
    if (istWeiterleitungPfad(rel)) { ausgelassen.push(rel); continue; }
    risk.push(r);
  }
  for (const r of risk) urls.push(`${basisUrl}${r.rel}`);
  return { urls, slugs, risk: risk.map(r => r.rel),
           weiterleitungenAusgelassen: [...new Set(ausgelassen)] };
}

if (SELFTEST) {
  runSelftest();
}

(async () => {
  // Reihenfolge = Wahrheitsreihenfolge: erst „gibt es etwas zu messen?",
  // dann „können wir messen?". Ein leerer Bau ist ein Werkzeugfehler (3) und
  // kein Layout-Befund (1) und keine weiche Überspringung (2).
  const bauProblem = pruefeBaubasis();
  if (bauProblem) {
    console.error('Werkzeugfehler: ' + bauProblem
      + ' – der Browser-Audit hat NICHTS gemessen (Exit 3, fail-closed).');
    process.exit(3);
  }
  if (!CHROME) {
    console.error('CHROME_PATH nicht gesetzt – Browser-Audit übersprungen '
      + '(Exit 2, das statische DOM-Budget hat jede Seite vermessen).');
    process.exit(2);
  }
  const puppeteer = ladePuppeteer();
  if (!puppeteer) process.exit(2);
  const domAudit = loadDomAudit();

  // ---- CSP des Repositories: EINE Quelle, fail-closed ------------------
  // Gemessen wird der Sollstand aus `static/_headers` (im Bau: `_headers`).
  // Fehlt er, wird NICHT gemessen: eine Messung ohne bekannten Sollstand
  // wäre wieder eine Behauptung über eine Kopfzeile, die niemand gesetzt hat.
  const headersDatei = fs.existsSync(path.join(BASE, '_headers'))
    ? path.join(BASE, '_headers') : HEADERS_DATEI;
  let cspSoll = null;
  try {
    cspSoll = cspAusHeaders(fs.readFileSync(headersDatei, 'utf8'));
  } catch (err) {
    cspSoll = null;
  }
  const csp = cspFuerMessung(cspSoll);
  if (!csp || !/(^|;)\s*default-src\s/.test(csp)) {
    console.error('Werkzeugfehler: keine brauchbare Content-Security-Policy in '
      + headersDatei + ' gefunden (' + (cspSoll ? 'ohne default-src' : 'keine CSP')
      + ') – ohne Sollstand misst der Audit nichts (Exit 3, fail-closed).');
    process.exit(3);
  }
  const cspDigest = crypto.createHash('sha256').update(csp).digest('hex').slice(0, 16);
  const nonce = crypto.randomBytes(8).toString('hex');
  const ctx = { domAudit, budgets: domAudit.budgets || FALLBACK.budgets,
                csp, cspDigest, nonce, herkunft: null, fremdnav: [] };
  let server;
  try {
    server = await serve(BASE, PORT, { csp, cspDigest, nonce });
  } catch (err) {
    console.error('Werkzeugfehler: lokaler Messserver nicht startbar ('
      + err.message + ') – Exit 3, fail-closed.');
    process.exit(3);
  }
  const basisUrl = 'http://127.0.0.1:' + server.address().port;
  ctx.herkunft = new URL(basisUrl).origin;
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu'],
  });

  const sample = buildSampleUrls(domAudit, basisUrl);
  const results = [];
  for (const u of sample.urls) {
    results.push(await auditPage(browser, u, { width: 1280, height: 800 }, ctx));
    results.push(await auditPage(browser, u, { width: 390, height: 844 }, ctx));
  }

  await browser.close();
  server.close();

  const critical = results.filter(r => r.issues.length > 0);
  const herkunftVerletzt = results.filter(r => r.herkunftOk === false);
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
    hermetik: {
      herkunft: ctx.herkunft,
      fremdnavigationenBlockiert: [...new Set(ctx.fremdnav)],
      herkunftsverletzungen: herkunftVerletzt.map(r => ({
        url: r.url, herkunft: r.herkunft,
      })),
      weiterleitungenAusgelassen: sample.weiterleitungenAusgelassen || [],
      hinweis: 'Der Audit misst ausschließlich den lokalen Bau '
        + '(127.0.0.1). Hauptnavigationen zu fremden Herkünften werden '
        + 'abgebrochen; Weiterleitungsseiten aus scripts/weiterleitungen.py '
        + 'werden gar nicht erst als Probe verwendet.',
    },
    cspBelege: {
      gesendet: cspDigest,
      gruende: results.reduce((n, r) => {
        const g = (r.csp && r.csp.grund) || 'unbekannt';
        n[g] = (n[g] || 0) + 1;
        return n;
      }, {}),
      quelle: 'static/_headers, Regel /* (EINE Quelle; frame-ancestors '
        + 'wird separat geprüft, weil sie nur als Kopfzeile wirkt)',
      seitenMitKopfzeile: results.filter(r => r.csp && r.csp.kopfzeile).length,
      seitenGemessen: results.length,
      eigeneImDokument: results.filter(r => r.csp && r.csp.eigene).length,
      fremd: results.reduce((n, r) => n + (r.csp && r.csp.fremd ? 1 : 0), 0),
      fremdherkunft: [...new Set(results.flatMap(
        r => (r.csp && r.csp.fremdherkunft) || []))],
      gesehen: [...new Set(results.flatMap(r => (r.csp && r.csp.gesehen) || []))],
      unbelegt: results.reduce((n, r) => n + ((r.csp && r.csp.unbelegt) || 0), 0),
      hinweis: 'gesendet = SHA-256-Kurzform der ausgelieferten CSP aus '
        + 'static/_headers. eigeneImDokument = im Dokument wiedergefunden; '
        + 'fremd = zusätzliche oder abweichende Kopfzeile einer anderen '
        + 'Herkunft. Nur eine eigene, unverfälschte CSP macht einen '
        + 'CSP-Verstoß zum Seitenbefund.',
    },
    allOk: critical.length === 0 && herkunftVerletzt.length === 0,
    greenWithWarnings: critical.length === 0 && warnPages.length > 0,
  };
  console.log(JSON.stringify(summary, null, 2));
  // Eine Messung, die die eigene Herkunft verlassen hat, ist kein Befund
  // über die Seite, sondern ein Werkzeugfehler (Exit 3, fail-closed).
  if (herkunftVerletzt.length) {
    console.error('Werkzeugfehler: ' + herkunftVerletzt.length
      + ' Messung(en) haben die eigene Herkunft verlassen ('
      + herkunftVerletzt.map(r => r.herkunft).join(', ')
      + ') – Exit 3, fail-closed. Die Hermetik-Sperre hat nicht gegriffen.');
    process.exit(3);
  }
  process.exit(critical.length ? 1 : 0);
})();
