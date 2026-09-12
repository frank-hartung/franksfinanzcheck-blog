// ============================================================
//  DESIGN-SHOTS – Screenshot-Runner für Design-Reviews
//  ------------------------------------------------------------
//  Rollout 12.09.2026 (Design-Skills-Premium-Integration).
//
//  Playfair… nein – Playwright-Ablösung von scripts/_design_shots.js
//  (Puppeteer/Chrome-Download): nutzt dieselbe Browser-Auflösung
//  wie die E2E-Suite (inkl. @sparticuz/chromium-Fallback) und den
//  gleichen zero-dependency Static-Server (e2e/server.mjs).
//
//  Aufruf:
//    node e2e/design-shots.mjs                     # Standard-Seiten
//    node e2e/design-shots.mjs /posts/ /pillar/dsl/ # eigene Pfade
//    SHOTS_DIR=shots node e2e/design-shots.mjs     # Zielordner
//
//  Ausgabe: PNGs (Desktop 1280×800 + Mobile 390×844) in ./shots/
//  (Ordner ist gegittet nicht versioniert → .gitignore).
// ============================================================

import { spawn } from 'node:child_process';
import { existsSync, mkdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium as pwChromium } from 'playwright-core';
import { resolveLaunchOptions } from './browser.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const OUT_DIR = process.env.SHOTS_DIR || join(ROOT, 'shots');
const PORT = Number(process.env.E2E_SHOTS_PORT || 4317);
const BASE = `http://127.0.0.1:${PORT}`;

const DEFAULT_PATHS = [
  '/',
  '/posts/',
  '/pillar/versicherungen/',
];

// Neuesten Artikel dynamisch ermitteln (robust gegen neue Beiträge)
async function newestArticle(page) {
  await page.goto(`${BASE}/`);
  const href = await page
    .locator('article.post-entry a[href*="/posts/"]')
    .first()
    .getAttribute('href');
  return href;
}

async function waitForServer(url, timeoutMs = 20_000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url);
      if (res.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 300));
  }
  throw new Error(`Test-Server nicht erreichbar unter ${url}`);
}

(async () => {
  if (!existsSync(join(ROOT, 'public', 'index.html'))) {
    console.error('[Shots] public/ fehlt – zuerst `hugo --destination public` ausführen.');
    process.exit(1);
  }
  mkdirSync(OUT_DIR, { recursive: true });

  // Static-Server als Kindprozess starten (wird am Ende sauber beendet)
  const server = spawn(process.execPath, [join(__dirname, 'server.mjs')], {
    env: { ...process.env, E2E_PORT: String(PORT) },
    stdio: 'ignore',
  });
  try {
    await waitForServer(`${BASE}/healthz`);

    const launchOptions = await resolveLaunchOptions();
    const browser = await pwChromium.launch({ ...launchOptions, headless: true });

    const viewports = [
      { label: 'desktop', width: 1280, height: 800, isMobile: false, deviceScaleFactor: 1 },
      { label: 'mobile', width: 390, height: 844, isMobile: true, hasTouch: true, deviceScaleFactor: 3 },
    ];

    const page = await browser.newPage();
    const article = await newestArticle(page);
    await page.close();

    const targets = process.argv.slice(2).length
      ? process.argv.slice(2)
      : [...DEFAULT_PATHS, article];

    for (const path of targets) {
      for (const vp of viewports) {
        const context = await browser.newContext({
          viewport: { width: vp.width, height: vp.height },
          deviceScaleFactor: vp.deviceScaleFactor,
          isMobile: vp.isMobile,
          hasTouch: vp.hasTouch ?? vp.isMobile,
          locale: 'de-DE',
        });
        const page = await context.newPage();
        await page.goto(`${BASE}${path}`, { waitUntil: 'load' });
        // Lazy-Bilder nachziehen, damit der Screenshot vollständig ist
        await page.evaluate(async () => {
          await new Promise((resolve) => {
            const html = document.documentElement;
            html.style.scrollBehavior = 'auto';
            const step = () => {
              window.scrollBy(0, Math.round(window.innerHeight * 0.9));
              if (window.scrollY + window.innerHeight < document.body.scrollHeight - 2) {
                setTimeout(step, 90);
              } else {
                setTimeout(() => { window.scrollTo(0, 0); setTimeout(resolve, 250); }, 300);
              }
            };
            step();
          });
        });
        await page.evaluate(() =>
          Promise.all([...document.images].map((img) => img.decode().catch(() => {})))
        );
        const name =
          path === '/' ? 'home' : path.replace(/^\//, '').replace(/\/$/, '').replace(/\W+/g, '-');
        const file = join(OUT_DIR, `${name}--${vp.label}.png`);
        await page.screenshot({ path: file, fullPage: true });
        console.log(`[Shots] ${file}`);
        await context.close();
      }
    }
    await browser.close();
  } finally {
    server.kill('SIGTERM');
  }
})().catch((e) => {
  console.error('[Shots] FEHLER:', e.message);
  process.exit(1);
});
