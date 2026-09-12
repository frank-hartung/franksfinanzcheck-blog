// ============================================================
//  SPEC: STARTSEITE – Rendering, Teaser, Fehlerfreiheit, Bilder
//  Projekt: desktop + mobile
// ============================================================

import { test, expect } from './fixtures.mjs';
import { watchErrors, assertNoErrors, scrollThrough, waitForImages } from './helpers.mjs';

test.describe('Startseite', () => {
  test('rendert Kernstruktur: Titel, genau ein H1, Teaser, Footer-Rechtliches', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/FranksFinanzcheck/);

    const h1 = page.locator('h1');
    expect(await h1.count(), 'Startseite: genau ein H1').toBe(1);
    expect((await h1.first().textContent()).trim().length).toBeGreaterThan(10);

    // Teaser: Pager zeigt 8 Beiträge pro Seite – mindestens 6 erwartet
    const teasers = page.locator('article.post-entry');
    expect(await teasers.count(), 'Startseite: Artikel-Teaser sichtbar').toBeGreaterThanOrEqual(6);

    // Pflicht-Verlinkung (DSGVO-Üblichkeit): Impressum + Datenschutz erreichbar
    const impressum = page.locator('a[href*="/impressum"]');
    const datenschutz = page.locator('a[href*="/datenschutz"]');
    expect(await impressum.count(), 'Impressum-Link vorhanden').toBeGreaterThan(0);
    expect(await datenschutz.count(), 'Datenschutz-Link vorhanden').toBeGreaterThan(0);
  });

  test('lädt ohne JS-Fehler und ohne defekte Same-Origin-Anfragen', async ({ page }) => {
    const errors = watchErrors(page);
    const failedRequests = [];
    const externalFailures = [];
    const isLocal = (url) => /127\.0\.0\.1|localhost/.test(url);

    page.on('requestfailed', (req) => {
      const failure = req.failure()?.errorText || '';
      const entry = `${req.url()} (${failure})`;
      if (isLocal(req.url())) {
        if (!failure.includes('ERR_ABORTED')) failedRequests.push(entry);
      } else {
        externalFailures.push(entry);
      }
    });
    page.on('response', (res) => {
      if (res.status() >= 400 && isLocal(res.url())) {
        failedRequests.push(`${res.status()} ${res.url()}`);
      }
    });

    await page.goto('/', { waitUntil: 'load' });
    await scrollThrough(page);
    await waitForImages(page);
    await page.waitForLoadState('networkidle');

    assertNoErrors(errors, 'Startseite');
    expect(
      failedRequests,
      'Startseite: keine 4xx/5xx-Antworten und keine fehlgeschlagenen Anfragen'
    ).toEqual([]);
    if (externalFailures.length) {
      console.log(`ℹ Startseite: ${externalFailures.length} ignorierte Drittanbieter-Anfragen`);
    }
  });

  test('alle Bilder laden vollständig und tragen alt-Texte', async ({ page }) => {
    await page.goto('/', { waitUntil: 'load' });
    await scrollThrough(page);
    await waitForImages(page);

    const imgs = page.locator('img');
    const count = await imgs.count();
    expect(count, 'Startseite: Bilder vorhanden').toBeGreaterThan(3);

    const probleme = [];
    for (let i = 0; i < count; i++) {
      const img = imgs.nth(i);
      const src = await img.evaluate((el) => el.currentSrc || el.src);
      const ok = await img.evaluate((el) => el.complete && el.naturalWidth > 0);
      if (!ok) probleme.push(`nicht geladen: ${src}`);
      // Deko-Bilder (Logo, alt="") sind erlaubt – Inhaltsbilder brauchen alt
      const alt = await img.getAttribute('alt');
      const istDeko = (await img.getAttribute('aria-hidden')) === 'true' || (await img.evaluate((el) => el.closest('[aria-hidden="true"]') !== null));
      if ((alt === null || alt.trim() === '') && !istDeko) {
        probleme.push(`ohne alt-Text: ${src}`);
      }
    }
    expect(probleme, 'Startseite: Bilder geladen & barrierefrei').toEqual([]);
  });
});
