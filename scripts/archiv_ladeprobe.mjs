// Lokaler Hugo-Build, kalter Cache pro Navigation. Keine CDN-/Felddaten.
// node scripts/archiv_ladeprobe.mjs http://127.0.0.1:4173 > messung.json
import { chromium } from 'playwright-core';
import { resolveLaunchOptions } from '../e2e/browser.mjs';
const origin = new URL(process.argv[2]).origin;
const sitemap = await (await fetch(`${origin}/sitemap.xml`)).text();
const paths = [...new Set([...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => new URL(m[1]).pathname).filter(p => /^\/posts\/\d[^/]+\/$/.test(p)))].sort();
if (!paths.length) throw Error('Keine Archivartikel in der Sitemap');
const browser = await chromium.launch(await resolveLaunchOptions());
try {
  const results = [];
  for (const path of ['/', '/posts/', '/cockpit/', ...paths]) {
    const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, serviceWorkers: 'block' });
    await ctx.route('**/*', r => new URL(r.request().url()).origin === origin ? r.continue() : r.abort());
    const page = await ctx.newPage();
    const response = await page.goto(origin + path, { waitUntil: 'load' });
    if (response.status() !== 200) throw Error(path + ': ' + response.status());
    const timing = await page.evaluate(() => {
      const n = performance.getEntriesByType('navigation')[0];
      return { ttfb_ms: Math.round(n.responseStart - n.requestStart), load_ms: Math.round(n.loadEventEnd - n.startTime) };
    });
    results.push({ path, ...timing });
    await ctx.close();
  }
  console.log(JSON.stringify({ chromium: browser.version(), results }, null, 2));
} finally { await browser.close(); }
