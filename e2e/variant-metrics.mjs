// ============================================================
//  VARIANTEN-MESSUNG (Tier B) – Playwright + Lighthouse
//  ------------------------------------------------------------
//  Rollout 26.09.2026 (Design-Varianten-Werkbank).
//  Runbook: docs/ANLEITUNG-DESIGN-VARIANTEN.md
//
//  Misst, was man einem HTML-Dokument NICHT ansehen kann und was
//  Tier A (scripts/design_variant_lab.py) deshalb nicht liefert:
//
//    tiers.gerendert   Kontraste (hell + dunkel), Tap-Ziele, Fokus-
//                      Sichtbarkeit, CLS, LCP  → Playwright
//    tiers.lighthouse  Kategorie-Scores + TBT  → Lighthouse (optional)
//
//  Beide Ebenen landen in .cache/design-varianten/<id>/messung.json;
//  bewertet werden sie von scripts/design_variant_gate.py.
//
//  FAIL-CLOSED
//  Fehlt der Browser, wird KEIN Ergebnis geschönt: Die Ebene bekommt
//  den Status "nicht_verfuegbar" samt Grund, das Gate zählt sie als
//  fehlend, und eine Freigabe ist damit unmöglich. Eine Messung, die
//  nicht sagt, dass sie nicht stattgefunden hat, ist schlimmer als
//  keine Messung.
//
//  AUFRUF
//    node e2e/variant-metrics.mjs --variante v-hero-conversion
//    node e2e/variant-metrics.mjs --variante alle
//    node e2e/variant-metrics.mjs --variante basis --port 4319
//
//  EXIT-CODES
//    0 = gemessen · 1 = Messfehler · 2 = Aufruf-/Baufehler
//    3 = kein Browser verfügbar (Ebene sauber als fehlend vermerkt)
// ============================================================

import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';
import { resolveLaunchOptions } from './browser.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const CACHE = join(ROOT, '.cache', 'design-varianten');

// ---------------------------------------------------------------
// Aufruf-Parameter
// ---------------------------------------------------------------
function argWert(name, standard = null) {
  const i = process.argv.indexOf(`--${name}`);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : standard;
}

const ZIEL = argWert('variante');
const PORT = Number(argWert('port', process.env.E2E_VARIANT_PORT || 4319));

if (!ZIEL) {
  console.error('Aufruf: node e2e/variant-metrics.mjs --variante <id|alle>');
  process.exit(2);
}

// ---------------------------------------------------------------
// Messdatei (teilt sich die Datei mit Tier A – niemals überschreiben)
// ---------------------------------------------------------------
function messdatei(id) {
  return join(CACHE, id, 'messung.json');
}

function schreibeTier(id, tier, daten) {
  const pfad = messdatei(id);
  mkdirSync(dirname(pfad), { recursive: true });
  let bestand = {};
  if (existsSync(pfad)) {
    try {
      bestand = JSON.parse(readFileSync(pfad, 'utf8'));
    } catch {
      bestand = {};
    }
  }
  bestand.variante ??= id;
  bestand.tiers ??= {};
  bestand.tiers[tier] = daten;
  bestand.aktualisiert = new Date().toISOString().replace(/\.\d+Z$/, 'Z');
  writeFileSync(pfad, `${JSON.stringify(bestand, null, 2)}\n`, 'utf8');
}

// ---------------------------------------------------------------
// Static-Server (der gehärtete aus e2e/server.mjs, anderer Wurzelpfad)
// ---------------------------------------------------------------
async function starteServer(wurzel, port) {
  const kind = spawn(process.execPath, [join(__dirname, 'server.mjs')], {
    env: { ...process.env, E2E_ROOT: wurzel, E2E_PORT: String(port) },
    stdio: ['ignore', 'ignore', 'pipe'],
  });
  let stderr = '';
  kind.stderr.on('data', (d) => {
    stderr += String(d);
  });

  const ende = Date.now() + 20_000;
  while (Date.now() < ende) {
    if (kind.exitCode !== null) {
      throw new Error(`Server beendet (Code ${kind.exitCode}): ${stderr.trim()}`);
    }
    try {
      const res = await fetch(`http://127.0.0.1:${port}/healthz`);
      if (res.ok) return kind;
    } catch {
      /* noch nicht bereit */
    }
    await new Promise((r) => setTimeout(r, 200));
  }
  kind.kill('SIGTERM');
  throw new Error(`Server nicht erreichbar auf Port ${port}. ${stderr.trim()}`);
}

// ---------------------------------------------------------------
// Browser-seitige Messfunktionen
// ---------------------------------------------------------------

// Kontrastrechnung – identisch zur Logik in e2e/design-metrics.mjs,
// damit Werkbank und Design-Audit nie zwei Wahrheiten liefern.
const KONTRAST_HELFER = `
var lum = function (r, g, b) {
  var f = function (c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
var parse = function (c) {
  var m = c.match(/rgba?\\((\\d+)[,\\s]+(\\d+)[,\\s]+(\\d+)(?:[,/\\s]+([\\d.]+))?\\)/);
  if (!m) return null;
  return { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] };
};
var blend = function (fg, bg) {
  return { r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a) };
};
var ratio = function (l1, l2) { var a = Math.max(l1, l2), b = Math.min(l1, l2); return (a + 0.05) / (b + 0.05); };
var effBg = function (el) {
  var node = el;
  while (node && node !== document.documentElement) {
    var bg = parse(window.getComputedStyle(node).backgroundColor);
    if (bg && bg.a > 0.85) return bg;
    node = node.parentElement;
  }
  var rootBg = parse(window.getComputedStyle(document.documentElement).backgroundColor);
  return rootBg && rootBg.a > 0 ? rootBg : { r: 255, g: 255, b: 255, a: 1 };
};
var contrastOf = function (el) {
  if (!el) return null;
  var cs = window.getComputedStyle(el);
  var fg = parse(cs.color);
  if (!fg) return null;
  var bg = effBg(el);
  var f = blend(fg, bg);
  return Math.round(ratio(lum(f.r, f.g, f.b), lum(bg.r, bg.g, bg.b)) * 100) / 100;
};
`;

const KONTRAST_BODY = `${KONTRAST_HELFER}
var proben = {};
var messe = function (name, sel) {
  var el = document.querySelector(sel);
  var v = contrastOf(el);
  if (v !== null) proben[name] = v;
};
messe('fliesstext', '.post-content p, .entry-content p, main p');
messe('link', '.post-content a[href], .entry-content a[href]');
messe('meta', '.post-meta, .entry-meta');
messe('cta_primaer', '.ff-home-ctas .ff-btn-primary');
messe('cta_sekundaer', '.ff-home-ctas .ff-btn-secondary');
messe('cta_outline', '.ff-home-ctas .ff-btn-outline');
messe('trust', '.ff-trust-pill');
return proben;
`;

// Tap-Ziele: die tatsächlich klickbare Fläche inklusive ::after-Ausdehnung
// (der Blog vergrößert kleine Controls bewusst per Pseudo-Element –
// siehe DESIGN.md §5, .ff-heading-copy).
const TAP_BODY = `
var ergebnis = { min: null, unter24: 0, unter44: 0, geprueft: 0, kleinstes: null };
var kandidaten = document.querySelectorAll('a[href], button, [role="button"], input, summary');
for (var i = 0; i < kandidaten.length; i++) {
  var el = kandidaten[i];
  var r = el.getBoundingClientRect();
  if (r.width === 0 || r.height === 0) continue;
  var style = window.getComputedStyle(el, '::after');
  var inset = 0;
  var top = style.getPropertyValue('inset') || style.getPropertyValue('top');
  var m = /(-?\\d+(?:\\.\\d+)?)px/.exec(top || '');
  if (m && Number(m[1]) < 0) inset = Math.abs(Number(m[1]));
  var w = r.width + inset * 2;
  var h = r.height + inset * 2;
  var kleiner = Math.min(w, h);
  ergebnis.geprueft++;
  if (kleiner < 24) ergebnis.unter24++;
  if (kleiner < 44) ergebnis.unter44++;
  if (ergebnis.min === null || kleiner < ergebnis.min) {
    ergebnis.min = Math.round(kleiner * 10) / 10;
    ergebnis.kleinstes = (el.tagName + '.' + (el.className || '')).slice(0, 80);
  }
}
return ergebnis;
`;

const FOKUS_BODY = `
var ziel = document.querySelector('.ff-home-ctas a[href], main a[href]');
if (!ziel) return { sichtbar: null, grund: 'kein fokussierbares Element gefunden' };
ziel.focus();
var cs = window.getComputedStyle(ziel);
var breite = parseFloat(cs.outlineWidth) || 0;
var stil = cs.outlineStyle;
var schatten = cs.boxShadow && cs.boxShadow !== 'none';
return {
  sichtbar: (breite > 0 && stil !== 'none') || schatten,
  outline: cs.outlineWidth + ' ' + cs.outlineStyle + ' ' + cs.outlineColor
};
`;

async function messeSeite(browser, url, farbschema) {
  const context = await browser.newContext({
    colorScheme: farbschema,
    viewport: { width: 1280, height: 720 },
    locale: 'de-DE',
    timezoneId: 'Europe/Berlin',
    serviceWorkers: 'block',
  });
  const page = await context.newPage();

  // CLS/LCP müssen VOR dem Laden beobachtet werden.
  await page.addInitScript(() => {
    window.__ffCls = 0;
    window.__ffLcp = 0;
    try {
      new PerformanceObserver((list) => {
        for (const e of list.getEntries()) {
          if (!e.hadRecentInput) window.__ffCls += e.value;
        }
      }).observe({ type: 'layout-shift', buffered: true });
      new PerformanceObserver((list) => {
        const entries = list.getEntries();
        if (entries.length) window.__ffLcp = entries[entries.length - 1].startTime;
      }).observe({ type: 'largest-contentful-paint', buffered: true });
    } catch {
      /* Browser ohne diese Entry-Typen: Werte bleiben 0 */
    }
  });

  await page.goto(url, { waitUntil: 'load', timeout: 30_000 });
  await page.waitForTimeout(700);

  const kontraste = await page.evaluate(`(() => {${KONTRAST_BODY}})()`);
  const fokus = await page.evaluate(`(() => {${FOKUS_BODY}})()`);
  const cwv = await page.evaluate(
    '({ cls: Math.round((window.__ffCls || 0) * 1000) / 1000, lcp: Math.round(window.__ffLcp || 0) })'
  );

  await page.setViewportSize({ width: 390, height: 844 });
  await page.waitForTimeout(250);
  const tap = await page.evaluate(`(() => {${TAP_BODY}})()`);

  await context.close();
  return { kontraste, fokus, cwv, tap };
}

// ---------------------------------------------------------------
// Lighthouse (optional – niemals stillschweigend übersprungen)
// ---------------------------------------------------------------
// Messprofile. Die Reihenfolge ist die Reihenfolge der Läufe.
//
// WARUM ZWEI PROFILE – UND WARUM DAS HIER SO AUSFÜHRLICH STEHT
// Am 26.09.2026 lief diese Messung wochenlang falsch: Der Aufruf
// übergab `settings: { preset: 'desktop' }` an die Lighthouse-NODE-API.
// Die kennt `preset` nicht (das ist ein CLI-Begriff) und ignoriert es
// stillschweigend – gemessen wurde also MOBIL, während lighthouserc.cjs
// „desktop" deklarierte. Ergebnis: zwei Wahrheiten über dieselbe Zahl,
// LCP 3158 ms (mobil) gegen 622 ms (desktop).
// Profile werden deshalb nur noch über echte Config-Objekte gesetzt und
// das gemessene `formFactor` wird in die Messdatei geschrieben. Eine
// Messung, die nicht sagt, unter welchen Bedingungen sie entstand, ist
// keine Messung.
const PROFILE = [
  // Maßgeblich: Google bewertet Core Web Vitals am Feld – und das ist
  // bei einem Ratgeber-Blog überwiegend mobil.
  { name: 'mobil', config: undefined, massgeblich: true },
  { name: 'desktop', config: 'desktop', massgeblich: false },
];

// Wie oft je Profil gemessen wird. Der Median aus mehreren Läufen ist
// nicht Feinschliff, sondern Voraussetzung:
// Ein Einzellauf meldete am 26.09.2026 für die Basis TBT 1462 ms und
// Performance 0,73 – gegen 1, 46, 78 und 89 ms in allen anderen Läufen
// derselben Seite. Daraus wurde prompt ein Befund, den niemand hätte
// beheben können, weil es ihn nicht gab. lighthouserc.cjs nutzt aus
// demselben Grund numberOfRuns: 3; beide Werkzeuge messen jetzt gleich.
const LAEUFE = Math.max(1, Number(process.env.LH_LAEUFE || 3));

function median(werte) {
  const sauber = werte.filter((v) => typeof v === 'number' && Number.isFinite(v));
  if (!sauber.length) return null;
  const s = [...sauber].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

async function messeLighthouse(url, launchOptions) {
  let lighthouse;
  let desktopConfig;
  try {
    ({ default: lighthouse } = await import('lighthouse'));
    ({ default: desktopConfig } = await import('lighthouse/core/config/desktop-config.js'));
  } catch (e) {
    return {
      status: 'nicht_verfuegbar',
      grund:
        'Paket `lighthouse` nicht installiert (npm i -D lighthouse). ' +
        'Ohne Lighthouse fehlt der Freigabe eine Pflichtmessung.',
      details: String(e.message).slice(0, 160),
    };
  }

  const werte = { profile: {} };
  let port = 9222;

  for (const profil of PROFILE) {
    const laeufe = [];
    let browser;
    try {
      for (let n = 0; n < LAEUFE; n += 1) {
        browser = await chromium.launch({
          ...launchOptions,
          args: [...(launchOptions.args || []), `--remote-debugging-port=${port}`],
        });
        const { lhr } = await lighthouse(
          url,
          { port, output: 'json', logLevel: 'error',
            onlyCategories: ['performance', 'accessibility', 'best-practices', 'seo'] },
          profil.config === 'desktop' ? desktopConfig : undefined
        );
        laeufe.push(lhr);
        await browser.close();
        browser = undefined;
        port += 1;
      }

      const lhr = laeufe[laeufe.length - 1];
      const score = (k) =>
        median(laeufe.map((l) => (l.categories[k] ? l.categories[k].score : null)));
      const auditWert = (k) =>
        median(laeufe.map((l) => l.audits[k]?.numericValue ?? null));
      const runden = (v, n = 0) =>
        v === null ? null : Math.round(v * 10 ** n) / 10 ** n;
      const t = lhr.configSettings.throttling || {};
      const messung = {
        // Selbstauskunft der Messung – ohne sie ist jede Zahl deutbar.
        formFactor: lhr.configSettings.formFactor,
        cpu_faktor: t.cpuSlowdownMultiplier ?? null,
        netz_kbps: t.throughputKbps ?? null,
        laeufe: LAEUFE,
        verfahren: 'median',
        benchmark_index: runden(median(
          laeufe.map((l) => l.environment?.benchmarkIndex ?? null))),
        lighthouse: {
          performance: runden(score('performance'), 2),
          accessibility: runden(score('accessibility'), 2),
          seo: runden(score('seo'), 2),
          'best-practices': runden(score('best-practices'), 2),
        },
        tbt_ms: runden(auditWert('total-blocking-time')),
        lcp_ms: runden(auditWert('largest-contentful-paint')),
        fcp_ms: runden(auditWert('first-contentful-paint')),
        cls: runden(auditWert('cumulative-layout-shift'), 3),
        ungenutztes_css_kb: Math.round(
          (lhr.audits['unused-css-rules']?.details?.overallSavingsBytes ?? 0) / 1024),
        // Streuung sichtbar machen: Wer den Median liest, soll erkennen,
        // wie verlässlich er ist.
        streuung: {
          lcp_ms: laeufe.map((l) =>
            Math.round(l.audits['largest-contentful-paint']?.numericValue ?? 0)),
          tbt_ms: laeufe.map((l) =>
            Math.round(l.audits['total-blocking-time']?.numericValue ?? 0)),
        },
      };
      werte.profile[profil.name] = messung;
      if (profil.massgeblich) {
        // Die maßgebliche Messung steht zusätzlich flach da – das Gate
        // bewertet sie, und `profil_massgeblich` sagt, welche es ist.
        Object.assign(werte, messung, { profil_massgeblich: profil.name });
      }
      const sp = (a) => `${Math.min(...a)}–${Math.max(...a)}`;
      console.log(
        `  ✓ ${profil.name.padEnd(7)} ${messung.formFactor} · cpu×${messung.cpu_faktor} · ` +
        `Median aus ${LAEUFE}: LCP ${messung.lcp_ms}ms (${sp(messung.streuung.lcp_ms)}) · ` +
        `TBT ${messung.tbt_ms}ms (${sp(messung.streuung.tbt_ms)}) · ` +
        `perf ${messung.lighthouse.performance} · a11y ${messung.lighthouse.accessibility}`
      );
    } catch (e) {
      return { status: 'fehler', grund: `Profil ${profil.name}: ${String(e.message).slice(0, 260)}` };
    } finally {
      await browser?.close();
    }
  }

  return {
    status: 'ok',
    gemessen: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
    werte,
  };
}

// ---------------------------------------------------------------
// Ein Lauf je Variante
// ---------------------------------------------------------------
async function messeVariante(id, launchOptions, browserVerfuegbar) {
  const wurzel = join(CACHE, id, 'public');
  if (!existsSync(join(wurzel, 'index.html'))) {
    console.error(
      `✗ ${id}: kein Build unter ${wurzel}\n` +
        `  Zuerst: python3 scripts/design_variant_lab.py --lauf ${id}`
    );
    return 2;
  }

  if (!browserVerfuegbar) {
    const grund =
      'Kein Chromium verfügbar (npx playwright install chromium). ' +
      'Tier B bleibt ungemessen – eine Freigabe ist damit ausgeschlossen.';
    schreibeTier(id, 'gerendert', { status: 'nicht_verfuegbar', grund });
    schreibeTier(id, 'lighthouse', { status: 'nicht_verfuegbar', grund });
    console.error(`✗ ${id}: ${grund}`);
    return 3;
  }

  const server = await starteServer(wurzel, PORT);
  const url = `http://127.0.0.1:${PORT}/`;
  let code = 0;

  try {
    const browser = await chromium.launch(launchOptions);
    try {
      const hell = await messeSeite(browser, url, 'light');
      const dunkel = await messeSeite(browser, url, 'dark');

      const alleKontraste = [
        ...Object.values(hell.kontraste),
        ...Object.values(dunkel.kontraste),
      ].filter((v) => typeof v === 'number');

      schreibeTier(id, 'gerendert', {
        status: 'ok',
        gemessen: new Date().toISOString().replace(/\.\d+Z$/, 'Z'),
        werte: {
          kontrast_min: alleKontraste.length ? Math.min(...alleKontraste) : null,
          kontraste_hell: hell.kontraste,
          kontraste_dunkel: dunkel.kontraste,
          tap_min_px: hell.tap.min,
          tap_unter_24: hell.tap.unter24,
          tap_unter_44: hell.tap.unter44,
          tap_kleinstes: hell.tap.kleinstes,
          fokusring_sichtbar: hell.fokus.sichtbar,
          fokus_outline: hell.fokus.outline,
          cls: Math.max(hell.cwv.cls, dunkel.cwv.cls),
          lcp_ms: Math.max(hell.cwv.lcp, dunkel.cwv.lcp),
        },
      });

      const k = alleKontraste.length ? Math.min(...alleKontraste) : '?';
      console.log(
        `  ✓ ${id}: Kontrast min ${k} · Tap min ${hell.tap.min}px · ` +
          `CLS ${Math.max(hell.cwv.cls, dunkel.cwv.cls)} · ` +
          `LCP ${Math.max(hell.cwv.lcp, dunkel.cwv.lcp)}ms`
      );
    } finally {
      await browser.close();
    }

    console.log(`  Lighthouse (${id}):`);
    const lh = await messeLighthouse(url, launchOptions);
    schreibeTier(id, 'lighthouse', lh);
    if (lh.status !== 'ok') {
      console.warn(`  ⚠ ${id}: Lighthouse ${lh.status} – ${lh.grund}`);
    }
  } catch (e) {
    schreibeTier(id, 'gerendert', { status: 'fehler', grund: String(e.message).slice(0, 300) });
    console.error(`✗ ${id}: ${e.message}`);
    code = 1;
  } finally {
    server.kill('SIGTERM');
  }
  return code;
}

// ---------------------------------------------------------------
// main
// ---------------------------------------------------------------
const launchOptions = await resolveLaunchOptions();
let browserVerfuegbar = true;
try {
  const test = await chromium.launch(launchOptions);
  await test.close();
} catch (e) {
  browserVerfuegbar = false;
  console.error(`[Tier B] Browser-Start fehlgeschlagen: ${String(e.message).slice(0, 200)}`);
}

let ids = [ZIEL];
if (ZIEL === 'alle') {
  const register = join(ROOT, 'data', 'design', 'varianten.yaml');
  const text = existsSync(register) ? readFileSync(register, 'utf8') : '';
  // Bewusst schlicht: nur die `- id:`-Zeilen. Ein YAML-Parser als
  // Abhängigkeit wäre für diese eine Liste nicht zu rechtfertigen.
  ids = [...text.matchAll(/^\s*-\s+id:\s*([a-z0-9-]+)\s*$/gm)].map((m) => m[1]);
  if (!ids.length) {
    console.error('Keine Varianten im Register gefunden.');
    process.exit(2);
  }
}

let exitCode = 0;
for (const id of ids) {
  const code = await messeVariante(id, launchOptions, browserVerfuegbar);
  if (code !== 0) exitCode = exitCode === 0 ? code : exitCode;
}
process.exit(exitCode);
