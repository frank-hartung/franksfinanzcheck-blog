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

  // ============================================================
  //  HERAUSGEBER-PILL (mobil) – Regressionswächter (27.09.2026)
  //  ------------------------------------------------------------
  //  Mobile-Schwester des Desktop-Tests in home.spec.mjs: Auf dem
  //  Handy bricht die Trust-Reihe horizontal um (kein Fakten-Panel),
  //  die zweizeilige Herausgeber-Angabe muss hier trotzdem strikt
  //  Struktur bleiben (Label ÜBER Autor) und vollständig in der
  //  Hero-Box liegen. Die tote-<br>-Bugklasse (Live-Befund 27.09.)
  //  wäre mobil genauso unauffällig kaputt gegangen.
  //  ============================================================
  test('Startseite: Herausgeber-Pill zweizeilig und innerhalb der Hero-Box', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => document.fonts.ready);

    const geo = await page.evaluate(() => {
      const pill = document.querySelector('.ff-trust-pill--editorial');
      const box = document.querySelector('.first-entry.home-info');
      const row = document.querySelector('.ff-trust-row');
      const label = pill?.querySelector('.ff-trust-editorial-label');
      const author = pill?.querySelector('.ff-trust-author');
      if (!pill || !box || !row || !label || !author) return { fehlt: true };

      const p = pill.getBoundingClientRect();
      const b = box.getBoundingClientRect();
      const l = label.getBoundingClientRect();
      const a = author.getBoundingClientRect();

      const pills = [...document.querySelectorAll('.ff-trust-row .ff-trust-pill')].map((el) => {
        const q = el.getBoundingClientRect();
        return {
          txt: el.textContent.replace(/\s+/g, ' ').trim(),
          inBox: q.right <= b.right + 1 && q.left >= b.left - 1,
          innerlichSauber: el.scrollWidth <= el.clientWidth + 1,
        };
      });

      return {
        fehlt: false,
        zweiZeilen: a.top >= l.bottom - 2,
        abstand: +(a.top - l.bottom).toFixed(1),
        pillInBox: p.right <= b.right + 1 && p.left >= b.left - 1,
        autorVerlinkt: author instanceof HTMLAnchorElement && /\/ueber\/?$/.test(author.pathname),
        pillHoehe: +p.height.toFixed(1),
        pills,
      };
    });

    expect(geo.fehlt, 'Editorial-Struktur (Label + Autor) im Markup').toBe(false);
    expect(geo.zweiZeilen, `Autoren-Name muss UNTER dem Label stehen (2. Zeile), Abstand war ${geo.abstand}px`).toBe(true);
    expect(geo.autorVerlinkt, 'Autoren-Entity bleibt auf /ueber/ verlinkt (E-E-A-T)').toBe(true);
    expect(geo.pillInBox, 'Herausgeber-Pill muss innerhalb der Hero-Box liegen').toBe(true);
    // Zweizeilige Pill darf die Thumb-freundliche Mindesthöhe nicht
    // unterlaufen (Basis-Mindesthöhe der Pills: 40px mobil).
    expect(geo.pillHoehe, 'Herausgeber-Pill bleibt Thumb-gerecht hoch').toBeGreaterThanOrEqual(40);

    const verletzt = (geo.pills || []).filter((q) => !q.inBox || !q.innerlichSauber);
    expect(verletzt, 'Keine Trust-Pill ragt aus der Hero-Box oder überläuft intern').toEqual([]);
  });
});
