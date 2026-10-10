#!/usr/bin/env node
/**
 * Chromium-Vorprüfung für alle gerenderten Projektprüfungen.
 *
 * Bewusst kein `playwright install`: Chromium liegt als gepinnte
 * @sparticuz/chromium-Abhängigkeit im Root-Lockfile. Damit benötigt
 * der Browser-Fallback keinen Zugriff auf cdn.playwright.dev.
 * `npm ci` muss vorher gelaufen sein; die Smoke-Prüfung entpackt den
 * Browser bei Bedarf und beweist echte JavaScript-Ausführung.
 */
import assert from 'node:assert/strict';
import { chromium } from 'playwright-core';
import { resolveLaunchOptions } from '../e2e/browser.mjs';

const mode = process.argv.includes('--check') ? 'check' : 'setup';
let browser;

try {
  const launchOptions = await resolveLaunchOptions();
  browser = await chromium.launch({ headless: true, ...launchOptions });

  const page = await browser.newPage();
  await page.setContent(`<!doctype html>
    <html lang="de"><head><title>Chromium-Smoke-Test</title></head>
    <body><main id="render-proof">statisch</main>
      <script>document.querySelector('#render-proof').textContent = 'JavaScript gerendert';</script>
    </body></html>`);
  const rendered = await page.locator('#render-proof').textContent();
  assert.equal(rendered, 'JavaScript gerendert', 'Chromium führte das Prüfskript nicht aus');

  const browserPath = launchOptions.executablePath || chromium.executablePath();
  console.log(
    `✅ Chromium bereit · ${browser.version()} · ${browserPath}\n` +
    '   JavaScript-Smoke-Test: bestanden · Playwright-CDN: nicht benötigt'
  );
} catch (error) {
  const platformHelp = process.platform === 'linux'
    ? ''
    : `   Auf ${process.platform} CHROME_PATH setzen oder einen passenden Playwright-Browser-Cache nutzen.\n`;
  console.error(
    `❌ Chromium ${mode === 'setup' ? 'konnte nicht eingerichtet/gestartet werden' : 'ist nicht startbar'}.\n` +
    '   Im Projekt zuerst `npm ci` ausführen; das gepinnte Chromium kommt aus registry.npmjs.org.\n' +
    '   Es ist kein Download von cdn.playwright.dev erforderlich.\n' +
    platformHelp +
    `   Ursache: ${String(error?.stack || error).split('\n').slice(0, 5).join('\n   ')}`
  );
  process.exitCode = 1;
} finally {
  await browser?.close().catch(() => {});
}
