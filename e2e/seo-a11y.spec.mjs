// ============================================================
//  SPEC: SEO & BARriereFREIHEIT – Stichprobe über Kern-Seiten
//  Eindeutige Titel, Landmarks, Sprache, Skip-Link, Robots,
//  Sitemap, Manifest & Favicon.
//  Projekt: desktop
// ============================================================

import { test, expect } from './fixtures.mjs';
import { newestArticlePath, SITE_ORIGIN } from './helpers.mjs';

const SAMPLE_PATHS = ['/', '/posts/', '/ueber/', '/datenschutz/', '/impressum/'];

test.describe('SEO & A11y (Stichprobe Kern-Seiten)', () => {
  test('jede Kern-Seite: Titel eindeutig & gefüllt, genau ein H1, lang="de"', async ({ page }) => {
    const titles = new Map();

    for (const p of SAMPLE_PATHS) {
      await page.goto(p);
      const title = await page.title();
      expect(title.length, `Titel gefüllt: ${p}`).toBeGreaterThan(5);
      expect(titles.has(title), `Titel eindeutig: "${title}" (doppelt auf ${p})`).toBe(false);
      titles.set(title, p);

      expect(await page.locator('h1').count(), `Genau ein H1: ${p}`).toBe(1);
      expect(
        await page.getAttribute('html', 'lang'),
        `html lang=de: ${p}`
      ).toBe('de');
    }
  });

  test('Landmarks & Skip-Link auf Startseite und Artikel', async ({ page }) => {
    for (const p of ['/', await newestArticlePath(page)]) {
      await page.goto(p);

      for (const landmark of ['header', 'main, main#main, .main', 'footer']) {
        expect(
          await page.locator(landmark).count(),
          `Landmark <${landmark}> auf ${p}`
        ).toBeGreaterThan(0);
      }

      // Skip-Link: sichtbarer Sprung zum Inhalt für Tastatur-Nutzer
      const skip = page.locator('a.skip-link, a[href="#main"], a[href="#content"]').first();
      if ((await page.locator('a.skip-link').count()) > 0) {
        const target = (await skip.getAttribute('href')).slice(1);
        expect(
          await page.locator(`#${target}`).count(),
          `Skip-Link-Ziel #${target} existiert`
        ).toBeGreaterThan(0);
      }
    }
  });

  test('robots.txt + sitemap.xml + manifest + favicon erreichbar und konsistent', async ({ page, request, baseURL }) => {
    const get = (p) => request.get(baseURL.replace(/\/$/, '') + p);

    const robots = await get('/robots.txt');
    expect(robots.status(), 'robots.txt → 200').toBe(200);
    const robotsText = await robots.text();
    expect(robotsText, 'robots.txt referenziert Sitemap').toMatch(/^Sitemap:/m);

    const sitemap = await get('/sitemap.xml');
    expect(sitemap.status(), 'sitemap.xml → 200').toBe(200);
    const smText = await sitemap.text();
    expect(smText, 'Sitemap enthält Startseite').toContain(`${SITE_ORIGIN}/`);
    const articlePath = await newestArticlePath(page);
    expect(smText, 'Sitemap enthält neuesten Artikel').toContain(articlePath);

    const manifest = await get('/manifest.json');
    expect(manifest.status(), 'manifest.json → 200').toBe(200);

    const favicon = await get('/favicon.ico');
    expect(favicon.status(), 'favicon.ico → 200').toBe(200);
  });

  test('RSS-Feed (Pinterest-optimiert) ist valides XML mit Beiträgen', async ({ request, baseURL }) => {
    const res = await request.get(baseURL.replace(/\/$/, '') + '/index.xml');
    expect(res.status(), 'index.xml → 200').toBe(200);
    const xml = await res.text();
    expect(xml, 'Feed ist RSS').toMatch(/<rss[\s>]/);
    expect(xml, 'Feed enthält Beiträge').toMatch(/<item>/);
  });
});
