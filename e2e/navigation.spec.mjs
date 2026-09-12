// ============================================================
//  SPEC: NAVIGATION & SEITENGERÜST
//  Header/Footer-Links, Sektionen, Pagination, 404-Verhalten
//  Projekt: desktop + mobile
// ============================================================

import { test, expect } from './fixtures.mjs';
import { SITE_ORIGIN } from './helpers.mjs';

/** Interne Pfade aus einer Menge von <a>-Elementen extrahieren. */
async function internalPaths(page, selector, baseURL, limit = 40) {
  const hrefs = await page.locator(selector).evaluateAll(
    (els) => els.map((el) => el.getAttribute('href')),
    undefined
  );
  const paths = [];
  for (const href of hrefs) {
    if (!href) continue;
    if (href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:')) continue;
    if (href.startsWith(SITE_ORIGIN)) {
      paths.push(href.slice(SITE_ORIGIN.length));
    } else if (href.startsWith('/')) {
      paths.push(href);
    }
    if (paths.length >= limit) break;
  }
  return [...new Set(paths)];
}

test.describe('Navigation & Seitengerüst', () => {
  test('Header-Navigation: alle internen Ziele erreichbar (200)', async ({ page, request, baseURL }) => {
    await page.goto('/');
    const paths = await internalPaths(page, 'header.header a[href]', baseURL);
    expect(paths.length, 'Header enthält interne Links').toBeGreaterThan(0);

    for (const p of paths) {
      const res = await request.get(baseURL.replace(/\/$/, '') + p);
      expect(res.status(), `Header-Link ${p} → 200`).toBeLessThan(400);
    }
  });

  test('Footer: interne Ziele erreichbar (200)', async ({ page, request, baseURL }) => {
    await page.goto('/');
    const paths = await internalPaths(page, 'footer a[href], .site-footer a[href]', baseURL);
    expect(paths.length, 'Footer enthält interne Links').toBeGreaterThan(0);

    for (const p of paths) {
      const res = await request.get(baseURL.replace(/\/$/, '') + p);
      expect(res.status(), `Footer-Link ${p} → 200`).toBeLessThan(400);
    }
  });

  test('Sektionen: /posts/, eine Pillar-Page und Pagination laden', async ({ page, request, baseURL }) => {
    const get = (p) => request.get(baseURL.replace(/\/$/, '') + p);

    const posts = await get('/posts/');
    expect(posts.status(), '/posts/ erreichbar').toBe(200);

    // Pagination des Post-Archivs (31 Beiträge, pagerSize 8 → page/2 existiert)
    const page2 = await get('/posts/page/2/');
    expect(page2.status(), '/posts/page/2/ erreichbar').toBe(200);

    // mind. eine Themenwelt (Pillar) – Navigation in die Ratgeber-Welten
    const pillar = await page.goto('/');
    const pillarHref = await page
      .locator('a[href*="/pillar/"]')
      .first()
      .getAttribute('href');
    expect(pillarHref, 'Pillar-Link auf Startseite vorhanden').toBeTruthy();
    const pillarRes = await get(pillarHref.startsWith('/') ? pillarHref : pillarHref.replace(SITE_ORIGIN, ''));
    expect(pillarRes.status(), `Pillar ${pillarHref} erreichbar`).toBe(200);
  });

  test('404: unbekannte URL liefert Status 404 UND Fehlerseite mit Weg zurück', async ({ page }) => {
    const res = await page.goto('/diese-seite-gibt-es-nicht-e2e/');
    expect(res.status(), 'HTTP-Status 404 für unbekannte Seite').toBe(404);
    await expect(page.locator('h1')).toContainText(/404|nicht gefunden/i);
    // Leser zurückführen – Standard der Redaktion
    const homeLink = page.locator('a[href="/"], a[href="' + SITE_ORIGIN + '/"]');
    expect(await homeLink.count(), '404-Seite linkt zurück zur Startseite').toBeGreaterThan(0);
  });
});
