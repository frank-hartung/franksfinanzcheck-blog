// ============================================================
//  DESIGN-METRICS – messbarer Design-Audit gegen Skill-Standards
//  ------------------------------------------------------------
//  Rollout 12.09.2026 (Design-Skills-Premium-Integration).
//
//  Misst im GERENDERTEN Zustand (nicht im Quelltext), was die
//  Skills als Qualitätsfloor definieren (Impeccable craft-floor,
//  taste-skill Typografie-/Layout-Disziplin, Web Interface
//  Guidelines):
//    · Kontraste (WCAG) – Body, Links, Meta, Home-Info, Dark Mode
//    · Typo-Skala (h1–h4 Größe/Gewicht)
//    · Rhythmus (Abstand über/unter Überschriften), Messweite (ch)
//    · Fokus-Sichtbarkeit (echtes Tastatur-Fokussieren)
//    · Tap-Ziele (Mobile, 44px-Empfehlung)
//    · Easing-/Dauer-Inventar der Übergänge
//
//  Aufruf:   node e2e/design-metrics.mjs
//  Ausgabe:  JSON nach stdout (für Reports/CI)
// ============================================================

import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium as pwChromium } from 'playwright-core';
import { resolveLaunchOptions } from './browser.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const PORT = Number(process.env.E2E_SHOTS_PORT || 4318);
const BASE = 'http://127.0.0.1:' + PORT;

async function waitForServer(url, timeoutMs = 20_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error('Test-Server nicht erreichbar unter ' + url);
}

// ---------- Browser-seitiger Code (Body einer Funktion) ----------

const CONTRAST_HELPERS = `
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

const PAGE_BODY = CONTRAST_HELPERS + `
var r = {};
var probe = function (sel) {
  var els = document.querySelectorAll(sel);
  return els.length ? contrastOf(els[0]) : null;
};
r.kontraste = {
  body: probe('main p, .post-entry p, .home-info p'),
  homeInfoLink: probe('.home-info .entry-content a'),
  homeInfoEm: probe('.home-info .entry-content em'),
  metaSekundaer: probe('.post-entry .entry-footer, .post-meta, footer .terms'),
  teaserSekundaer: probe('.post-entry .entry-content'),
};
r.typo = {};
['h1', 'h2', 'h3', 'h4'].forEach(function (h) {
  var el = document.querySelector('main ' + h + ', article ' + h + ', ' + h);
  if (el) {
    var cs = window.getComputedStyle(el);
    r.typo[h] = { px: Math.round(parseFloat(cs.fontSize) * 10) / 10, gewicht: cs.fontWeight, familie: cs.fontFamily.split(',')[0] };
  }
});
return r;
`;

const ARTICLE_BODY = CONTRAST_HELPERS + `
var r = {};
r.kontraste = {
  body: contrastOf(document.querySelector('.post-content p')),
  link: contrastOf(document.querySelector('.post-content a')),
  metaSekundaer: contrastOf(document.querySelector('.post-meta, .post-header .breadcrumbs')),
  h2: contrastOf(document.querySelector('.post-content h2')),
};
var p = document.querySelector('.post-content p');
if (p) {
  var cs = window.getComputedStyle(p);
  var span = document.createElement('span');
  span.style.cssText = 'position:absolute;visibility:hidden;font:' + cs.font;
  span.textContent = new Array(101).join('0');
  document.body.appendChild(span);
  var ch = span.getBoundingClientRect().width / 100;
  span.remove();
  r.messweite = { px: Math.round(p.clientWidth), ch: Math.round(p.clientWidth / ch) };
}
r.rhythmus = {};
['h2', 'h3'].forEach(function (h) {
  var el = document.querySelector('.post-content ' + h);
  if (el) {
    var prev = el.previousElementSibling, next = el.nextElementSibling;
    var gap = function (a, b) {
      if (!a || !b) return null;
      var ca = window.getComputedStyle(a), cb = window.getComputedStyle(b);
      return Math.round(parseFloat(cb.marginTop) + parseFloat(ca.marginBottom));
    };
    r.rhythmus[h] = { ueber: gap(prev, el), unter: gap(el, next) };
  }
});
var dauen = {}, easings = {};
document.querySelectorAll('a, button, .post-entry, .ff-voice-slot button, nav *').forEach(function (el) {
  var t = window.getComputedStyle(el).transition;
  if (t && t !== 'all 0s ease 0s' && t !== 'none') {
    t.split(',').forEach(function (part) {
      var m = part.trim().match(/([\\d.]+m?s)\\s+([^\\s(]+)/);
      if (m) { dauen[m[1]] = 1; easings[m[2]] = 1; }
    });
  }
});
r.uebergaenge = { dauer: Object.keys(dauen).sort(), easing: Object.keys(easings) };
return r;
`;

const FOCUS_BODY = `
var el = document.activeElement;
if (!el || el === document.body) return { aktiv: false };
var cs = window.getComputedStyle(el);
var outline = cs.outlineStyle !== 'none' ? cs.outlineStyle + ' ' + cs.outlineWidth + ' ' + cs.outlineColor : null;
var shadow = cs.boxShadow !== 'none' ? cs.boxShadow : null;
return {
  aktiv: true,
  element: el.tagName + '.' + String(el.className || '').split(' ')[0],
  outline: outline,
  boxShadow: shadow,
  sichtbar: !!(outline || shadow)
};
`;

const TAP_BODY = `
var targets = document.querySelectorAll('button, a[href], [role="button"]');
var AA_MIN = 24, BP = 40;
var verstoss = [], hinweis = [], erweitert = 0;
targets.forEach(function (el) {
  var rect = el.getBoundingClientRect();
  if (rect.width === 0 || rect.height === 0) return;
  var klein = rect.height < AA_MIN || rect.width < AA_MIN;
  var unterBP = rect.height < BP || rect.width < BP;
  if (!klein && !unterBP) return;
  var label = (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 40);
  var eintrag = el.tagName.toLowerCase() + ' "' + label + '" ' + Math.round(rect.width) + 'x' + Math.round(rect.height) + 'px';
  if (klein) { verstoss.push(eintrag); return; }
  // Unter Best Practice (44px), aber über AA-Minimum: wurde die
  // Trefferfläche per Pseudo-Element erweitert? Echter Hit-Test
  // (elementFromPoint wirkt nur im Viewport → erst einscrollen):
  var nachbar = getComputedStyle(el, '::after');
  var hitTest = function () {
    // behavior:'instant' – html hat scroll-behavior:smooth, das würde
    // die Messung ins Leere laufen lassen (Animation läuft async).
    el.scrollIntoView({ block: 'center', behavior: 'instant' });
    var r2 = el.getBoundingClientRect();
    // Testpunkt HORIZONTAL vom Zentrum aus (nicht diagonal in die Ecke:
    // ::after trägt border-radius:999px → die Kreisrunde trifft die
    // Diagonale nicht mehr).
    var px = r2.left - 5, py = r2.top + r2.height / 2;
    var hit = document.elementFromPoint(px, py);
    return hit === el || (el.contains ? el.contains(hit) : false);
  };
  if (nachbar && nachbar.content !== 'none' && nachbar.content !== 'normal' && hitTest()) {
    erweitert += 1;
  } else {
    hinweis.push(eintrag);
  }
});
return {
  geprueft: targets.length,
  aaVerstoss: verstoss.slice(0, 12),
  hinweisUnter44px: hinweis.slice(0, 12),
  erweitertAuf44px: erweitert
};
`;

// Funktionen kompilieren (Fehler fallen sofort mit Namen auf)
const probes = {
  seite: new Function(PAGE_BODY),
  artikel: new Function(ARTICLE_BODY),
  fokus: new Function(FOCUS_BODY),
  tapziele: new Function(TAP_BODY),
};

(async () => {
  if (!existsSync(join(ROOT, 'public', 'index.html'))) {
    console.error('[Metrics] public/ fehlt – zuerst `hugo --destination public`.');
    process.exit(1);
  }

  const server = spawn(process.execPath, [join(__dirname, 'server.mjs')], {
    env: { ...process.env, E2E_PORT: String(PORT) },
    stdio: 'ignore',
  });

  const report = { generiert: new Date().toISOString(), seiten: {} };
  try {
    await waitForServer(BASE + '/healthz');
    const launchOptions = await resolveLaunchOptions();
    const browser = await pwChromium.launch({ ...launchOptions, headless: true });

    for (const scheme of ['light', 'dark']) {
      const context = await browser.newContext({
        viewport: { width: 1280, height: 800 },
        colorScheme: scheme,
        locale: 'de-DE',
      });
      const page = await context.newPage();

      await page.goto(BASE + '/');
      const articlePath = await page
        .locator('article.post-entry a[href*="/posts/"]')
        .first()
        .getAttribute('href');

      report.seiten['startseite-' + scheme] = await page.evaluate(probes.seite);

      await page.goto(BASE + articlePath);
      report.seiten['artikel-' + scheme] = await page.evaluate(probes.artikel);

      // Fokus-Sichtbarkeit: erstes interaktives Element per Tastatur ansteuern
      await page.goto(BASE + articlePath);
      await page.keyboard.press('Tab');
      report.seiten['fokus-' + scheme] = await page.evaluate(probes.fokus);

      // Mobile: Tap-Ziele
      const mobi = await browser.newContext({
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
        deviceScaleFactor: 3,
        colorScheme: scheme,
      });
      const mp = await mobi.newPage();
      await mp.goto(BASE + articlePath);
      report.seiten['tapziele-' + scheme] = await mp.evaluate(probes.tapziele);

      await context.close();
      await mobi.close();
    }
    await browser.close();
  } finally {
    server.kill('SIGTERM');
  }

  console.log(JSON.stringify(report, null, 2));
})().catch((e) => {
  console.error('[Metrics] FEHLER:', e.message);
  process.exit(1);
});
