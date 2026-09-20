// Lokales Cockpit, keine laufenden Server erforderlich: prüft auch file://.
// Vorher npm run seo:audit; npm run test:seo:browser.
import { before, after, test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { chromium } from 'playwright-core';
import { resolveLaunchOptions } from '../../e2e/browser.mjs';

let browser;
const url = process.env.SEO_COCKPIT_URL || pathToFileURL(resolve('.cache/seo-cockpit/index.html')).href;
before(async () => { browser = await chromium.launch({ ...(await resolveLaunchOptions()), headless: true }); });
after(async () => { await browser?.close(); });
async function open(t, options = {}) {
  const context = await browser.newContext({ viewport: { width: 1440, height: 1050 }, ...options });
  t.after(() => context.close());
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  t.after(() => assert.deepEqual(errors, []));
  await page.goto(url);
  await page.locator('#metrics .metric').first().waitFor();
  return page;
}

test('Überblick: echte Build-Daten, alle Arbeitsbereiche bedienbar', async t => {
  const p = await open(t);
  assert.equal(await p.locator('#metrics .metric').count(), 4);
  for (const view of ['massnahmen', 'seiten', 'suchdaten', 'snippet', 'ueberblick']) {
    await p.locator(`nav a[data-view="${view}"]`).click();
    await p.locator(`#${view}`).waitFor({ state: 'visible' });
    assert.equal(await p.locator('.view:visible').count(), 1);
  }
  mkdirSync('shots', { recursive: true });
  await p.screenshot({ path: 'shots/seo-cockpit-desktop.png', fullPage: true });
});
test('Seitenfilter, leere Suche und Snippet-Übernahme', async t => {
  const p = await open(t);
  await p.locator('[data-view=seiten]').click();
  await p.locator('#page-search').fill('gibtesnicht-9234');
  assert.match(await p.locator('#pages').textContent(), /Keine Seiten gefunden/);
  await p.locator('#page-search').fill('');
  await p.locator('#index-filter').selectOption('noindex');
  assert.match(await p.locator('#pages').textContent(), /Noindex/);
  await p.locator('#pages button').first().click();
  await p.locator('#snippet').waitFor({ state: 'visible' });
  await p.locator('#snippet-title').fill('Ein ehrlicher Testtitel');
  assert.equal(await p.locator('#preview-title').textContent(), 'Ein ehrlicher Testtitel');
  await p.evaluate(() => Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: async () => { throw new Error('Permission denied'); } } }));
  await p.locator('#copy-snippet').click();
  await p.waitForFunction(() => document.querySelector('#copy-message').textContent.length > 0);
  assert.match(await p.locator('#copy-message').textContent(), /Kopiert|Manuell übernehmen/);
});
test('GSC: Import, Filter, keine Netzwerkübertragung, keine HTML-Ausführung', async t => {
  const p = await open(t);
  await p.locator('[data-view=suchdaten]').click();
  const requests = []; p.on('request', r => requests.push(r.url()));
  await p.locator('#gsc-file').setInputFiles({ name: 'Suchanfragen.csv', mimeType: 'text/csv', buffer: Buffer.from('Häufigste Suchanfragen;Klicks;Impressionen;CTR;Position\nStrom sparen;20;1.000;2%;8,5\n<img src=x onerror=alert(1)>;1;200;0,5%;6,2\nanderes;2;10;20%;2,0') });
  await p.locator('#gsc-results').waitFor();
  assert.equal(await p.locator('#gsc-rows tr').count(), 2);
  assert.equal(await p.locator('#gsc-rows img').count(), 0);
  await p.locator('#gsc-filter').selectOption('all');
  assert.equal(await p.locator('#gsc-rows tr').count(), 3);
  assert.deepEqual(requests, []);
  await p.reload();
  await p.locator('#metrics .metric').first().waitFor({ state: 'attached' });
  assert.equal(await p.locator('#gsc-results').isVisible(), false);
  assert.match(await p.locator('#gsc-message').textContent(), /Noch keine Suchdaten/);
});
test('GSC: verständliche Importfehler, gültigen Import löschen', async t => {
  const p = await open(t); await p.locator('[data-view=suchdaten]').click();
  await p.locator('#gsc-file').setInputFiles({ name: 'falsch.csv', mimeType: 'text/csv', buffer: Buffer.from('A,B\nx,y') });
  await p.waitForFunction(() => document.querySelector('#gsc-message').textContent.includes('Import nicht möglich'));
  assert.equal(await p.locator('#gsc-results').isVisible(), false);
  await p.locator('#gsc-file').setInputFiles({ name: 'ok.csv', mimeType: 'text/csv', buffer: Buffer.from('Query,Clicks,Impressions,Position\nbudget,1,200,8') });
  await p.locator('#gsc-results').waitFor();
  await p.locator('#gsc-clear').click();
  assert.equal(await p.locator('#gsc-rows tr').count(), 0);
  assert.match(await p.locator('#gsc-message').textContent(), /Import gelöscht/);
});
test('Mobil 390px: kein horizontaler Seiten-Overflow, Dark Mode und Fokus', async t => {
  const p = await open(t, { viewport: { width: 390, height: 844 }, colorScheme: 'dark' });
  for (const view of ['ueberblick', 'seiten', 'suchdaten', 'snippet', 'massnahmen']) {
    await p.locator(`[data-view=${view}]`).click();
    assert.ok(await p.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), view);
  }
  await p.locator('[data-view=ueberblick]').click();
  assert.equal(await p.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(29, 30, 32)');
  mkdirSync('shots', { recursive: true });
  await p.screenshot({ path: 'shots/seo-cockpit-mobile-dark.png', fullPage: true });
});
