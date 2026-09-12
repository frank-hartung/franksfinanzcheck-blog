// ============================================================
//  SPEC: MOBILE (iPhone-14-Emulation)
//  Kein horizontaler Overflow, Bedienbarkeit von Header/Meta,
//  Tap-Ziel-Qualität der Haupt-Buttons.
//  Projekt: nur mobile
// ============================================================

import { test, expect } from './fixtures.mjs';
import { newestArticlePath, scrollThrough } from './helpers.mjs';

// Läuft ausschließlich im Mobile-Projekt
test.describe('Mobile (iPhone 14)', () => {
  test('Startseite: kein horizontaler Overflow', async ({ page }) => {
    await page.goto('/');
    await scrollThrough(page);
    const overflow = await page.evaluate(() => ({
      doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      body: document.body.scrollWidth - document.body.clientWidth,
    }));
    expect(overflow.doc, `document um ${overflow.doc}px zu breit`).toBeLessThanOrEqual(1);
    expect(overflow.body, `body um ${overflow.body}px zu breit`).toBeLessThanOrEqual(1);
  });

  test('Artikel: kein horizontaler Overflow (inkl. Tabellen)', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);
    await scrollThrough(page);
    const overflow = await page.evaluate(() => ({
      doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      body: document.body.scrollWidth - document.body.clientWidth,
    }));
    expect(overflow.doc, `document um ${overflow.doc}px zu breit`).toBeLessThanOrEqual(1);
    expect(overflow.body, `body um ${overflow.body}px zu breit`).toBeLessThanOrEqual(1);
  });

  test('Header: Logo sichtbar, Navigation nutzbar', async ({ page }) => {
    await page.goto('/');
    const logo = page.locator('header.header a.ff-brand img');
    await expect(logo.first()).toBeVisible();
    expect(
      await logo.first().evaluate((el) => el.complete && el.naturalWidth > 0),
      'Logo-Bild geladen'
    ).toBe(true);

    // Navigation muss auf Mobile erreichbar sein: entweder direkt sichtbar
    // oder per Toggle. Beides fehlend = Sackgasse für Mobile-Nutzer.
    const nav = page.locator('header.header nav, header.header .header-nav');
    expect(await nav.count(), 'Header-Navigation im DOM').toBeGreaterThan(0);
    const navVisible = await nav.first().isVisible().catch(() => false);
    const toggle = page.locator('header.header button[aria-expanded], header.header .menu-toggle');
    const toggleCount = await toggle.count();
    expect(
      navVisible || toggleCount > 0,
      'Navigation sichtbar ODER Toggle vorhanden'
    ).toBe(true);
  });

  test('Kern-Tap-Ziele: sichtbar und >= 40px hoch (Thumb-Greifbarkeit)', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);

    const slot = page.locator('.ff-voice-slot');
    if ((await slot.count()) > 0) {
      const buttons = slot.first().locator('button:visible');
      const count = await buttons.count();
      for (let i = 0; i < count; i++) {
        const box = await buttons.nth(i).boundingBox();
        if (box) {
          // 40 px statt 44: bewusster Spielraum für Text-Buttons mit Padding
          expect(
            box.height,
            `Toolbar-Button ${i + 1} nur ${Math.round(box.height)}px hoch`
          ).toBeGreaterThanOrEqual(40);
        }
      }
    }
  });
});
