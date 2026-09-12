// ============================================================
//  SPEC: ARTIKEL-SEITE – SEO-Meta, Schema, Bilder, Vorlese-Toolbar
//  Getestet wird der NEUESTE Artikel (dynamisch von der Startseite
//  ermittelt) – robust gegen neue Veröffentlichungen.
//  Projekt: desktop + mobile
// ============================================================

import { test, expect } from './fixtures.mjs';
import { watchErrors, assertNoErrors, scrollThrough, waitForImages, newestArticlePath, SITE_ORIGIN } from './helpers.mjs';

test.describe('Artikel-Seite (neuester Beitrag)', () => {
  test('rendert Titel, H1, Meta und Breadcrumbs', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);

    await expect(page).toHaveTitle(/.+/);
    const h1 = page.locator('h1');
    expect(await h1.count(), 'Artikel: genau ein H1').toBe(1);
    expect((await h1.first().textContent()).trim().length).toBeGreaterThan(10);

    // Meta-Zeile (Datum · Lesezeit · Autor) – Redaktions-Standard
    const header = page.locator('header.post-header');
    await expect(header).toBeVisible();
    const metaText = (await header.textContent()) || '';
    expect(metaText, 'Artikel-Meta enthält Datum/Autor').toMatch(/\d{2}\.\d{2}\.\d{4}|Frank Hartung/);

    // Breadcrumbs (Schema + UX-Standard der Redaktion)
    expect(await page.locator('nav[aria-label*="readcrumb"], .breadcrumbs, nav.breadcrumbs').count()).toBeGreaterThan(0);
  });

  test('SEO-Meta: Description, Canonical, Open Graph, Twitter Card', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);

    // Meta-Description: vorhanden und sinnvoll dimensioniert
    const desc = await page
      .locator('meta[name="description"]')
      .getAttribute('content');
    expect(desc, 'Meta-Description vorhanden').toBeTruthy();
    expect(desc.length, 'Meta-Description 50–200 Zeichen').toBeGreaterThanOrEqual(50);
    expect(desc.length, 'Meta-Description nicht überladen (>200)').toBeLessThanOrEqual(200);

    // Canonical zeigt auf die kanonische Produktions-URL
    const canonical = await page.locator('link[rel="canonical"]').getAttribute('href');
    expect(canonical, 'Canonical vorhanden').toBeTruthy();
    expect(canonical.startsWith(SITE_ORIGIN), 'Canonical ist absolut auf Produktions-Domain').toBe(true);
    expect(
      canonical.replace(SITE_ORIGIN, '').replace(/\/$/, ''),
      'Canonical entspricht dem Artikel-Pfad'
    ).toBe(articlePath.replace(/\/$/, ''));

    // Open Graph (Social/Pinterest-Pflicht)
    for (const prop of ['og:title', 'og:description', 'og:image', 'og:url', 'og:type']) {
      const val = await page.locator(`meta[property="${prop}"]`).getAttribute('content');
      expect(val, `${prop} gesetzt`).toBeTruthy();
    }

    // Twitter Card
    const tw = await page.locator('meta[name="twitter:card"]').getAttribute('content');
    expect(tw, 'twitter:card gesetzt').toBeTruthy();
  });

  test('og:image ist lokal auflösbar (Cover existiert im Build)', async ({ page, request, baseURL }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);
    const ogImage = await page.locator('meta[property="og:image"]').getAttribute('content');
    const res = await request.get(ogImage.replace(SITE_ORIGIN, baseURL.replace(/\/$/, '')));
    expect(res.status(), `og:image erreichbar: ${ogImage}`).toBe(200);
    expect((await res.headers())['content-type'] || '').toContain('image/');
  });

  test('JSON-LD: valider Article-Graph mit FAQ/Breadcrumbs', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);

    const blocks = await page.locator('script[type="application/ld+json"]').allTextContents();
    expect(blocks.length, 'mindestens ein JSON-LD-Block').toBeGreaterThan(0);

    const types = new Set();
    for (const b of blocks) {
      const parsed = JSON.parse(b); // wirft → Test failt bei kaputtem Schema
      const collect = (node) => {
        if (!node || typeof node !== 'object') return;
        if (Array.isArray(node)) return node.forEach(collect);
        if (node['@type']) {
          (Array.isArray(node['@type']) ? node['@type'] : [node['@type']]).forEach((t) => types.add(t));
        }
        Object.values(node).forEach(collect);
      };
      collect(parsed);
    }
    expect(types.has('Article') || types.has('BlogPosting') || types.has('NewsArticle'),
      'Article-Schema vorhanden').toBe(true);
    expect(types.has('BreadcrumbList'), 'BreadcrumbList-Schema vorhanden').toBe(true);
  });

  test('Bilder: geladen, alt-Texte, width/height (CLS-Schutz)', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath, { waitUntil: 'load' });
    await scrollThrough(page);
    await waitForImages(page);

    // Gesamter Artikelbereich: Cover (LCP), Autoren-Foto, Lazy-Teaser
    const imgs = page.locator('article.post-single img');
    const count = await imgs.count();
    expect(count, 'Artikel enthält Bilder (mind. Cover)').toBeGreaterThan(0);

    const probleme = [];
    for (let i = 0; i < count; i++) {
      const img = imgs.nth(i);
      const src = await img.evaluate((el) => el.currentSrc || el.src);
      if (!(await img.evaluate((el) => el.complete && el.naturalWidth > 0))) {
        probleme.push(`nicht geladen: ${src}`);
      }
      const alt = await img.getAttribute('alt');
      const istDeko = (await img.getAttribute('aria-hidden')) === 'true';
      if ((alt === null || alt.trim() === '') && !istDeko) probleme.push(`ohne alt: ${src}`);
      // Layout-Stabilität (CWV-Gate des Blogs): dimensionierte Bilder
      if (!(await img.getAttribute('width')) || !(await img.getAttribute('height'))) {
        probleme.push(`ohne width/height (CLS-Risiko): ${src}`);
      }
    }
    expect(probleme, 'Artikelbilder: geladen, alt + dimensioniert').toEqual([]);
  });

  test('Vorlese-Toolbar (FF Voice Studio): vorhanden & bedienbar', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);

    const slot = page.locator('.ff-voice-slot');
    if ((await slot.count()) === 0) {
      test.skip(true, 'Dieser Artikel hat keine Vorlese-Toolbar');
      return;
    }
    await expect(slot.first()).toBeVisible();

    // Alle Buttons der Toolbar brauchen zugängliche Namen (WCAG 2.2 AA+,
    // Selbstanspruch der ff-voice.css)
    const buttons = slot.first().locator('button');
    const count = await buttons.count();
    expect(count, 'Toolbar hat Bedienelemente').toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      const name = await buttons.nth(i).evaluate((el) => {
        const label = el.getAttribute('aria-label') || el.textContent || '';
        return label.trim();
      });
      expect(name.length, `Toolbar-Button ${i + 1} hat zugänglichen Namen`).toBeGreaterThan(0);
    }
  });

  test('lädt ohne JS-Fehler (ganze Seite durchscrollen)', async ({ page }) => {
    const errors = watchErrors(page);
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath, { waitUntil: 'load' });
    await scrollThrough(page);
    await page.waitForLoadState('networkidle');
    assertNoErrors(errors, 'Artikel');
  });
});
