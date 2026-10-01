// ============================================================
// SPEC: FIXKOSTEN-COCKPIT – Produktkern, lokale Rechnung, Privatsphäre
// ============================================================

import { test, expect } from './fixtures.mjs';

test.describe('Fixkosten-Cockpit', () => {
  test('ist über die Navigation erreichbar und rendert den vollständigen 4K-Prüfpfad', async ({ page }) => {
    await page.goto('/');
    const navTarget = page.locator('nav a[href*="/cockpit/"]').first();
    await expect(navTarget, 'Hauptnavigation führt zum Fixkosten-Cockpit').toBeVisible();

    await navTarget.click();
    await expect(page).toHaveURL(/\/cockpit\/?$/);
    await expect(page.locator('h1')).toHaveCount(1);
    await expect(page.locator('[data-ff-fixkosten-cockpit]')).toHaveCount(1);
    await expect(page.locator('[data-ff-fixkosten-kompass]')).toHaveCount(1);

    const text = await page.locator('[data-ff-fixkosten-kompass]').innerText();
    for (const step of ['Kosten sehen', 'Konditionen rechnen', 'Kündigungsfenster sichern', 'Kurs halten']) {
      expect(text, `4K-Schritt sichtbar: ${step}`).toContain(step);
    }
  });

  test('rechnet lokal, sortiert die Priorität und speichert nur nach Opt-in', async ({ page }) => {
    await page.goto('/cockpit/');
    const cockpit = page.locator('[data-ff-fixkosten-cockpit]');
    const storageKey = 'ff_fixkosten_cockpit_v1';

    expect(await page.evaluate((key) => localStorage.getItem(key), storageKey), 'kein Speicher ohne Opt-in').toBeNull();

    await page.locator('#ff-cockpit-energie-amount').fill('100,00');
    await page.locator('#ff-cockpit-internet-amount').fill('45,50');
    await page.locator('#ff-cockpit-energie-date').fill('2030-01-15');
    await cockpit.locator('form').evaluate((form) => form.requestSubmit());

    const result = cockpit.locator('[data-ff-cockpit-result]');
    await expect(result).toBeVisible();
    await expect(result.locator('[data-ff-cockpit-monthly]')).toContainText(/145,50/);
    await expect(result.locator('[data-ff-cockpit-yearly]')).toContainText(/1\.746,00/);
    await expect(result.locator('[data-ff-cockpit-priorities] li').first()).toContainText('Strom & Gas');
    expect(await page.evaluate((key) => localStorage.getItem(key), storageKey), 'Eingaben liegen noch nicht lokal vor').toBeNull();

    await cockpit.locator('[data-ff-cockpit-remember]').check();
    expect(await page.evaluate((key) => localStorage.getItem(key), storageKey), 'Speichern erst nach aktivem Häkchen').toContain('100,00');

    await page.reload();
    await expect(page.locator('#ff-cockpit-energie-amount')).toHaveValue('100,00');
    await expect(page.locator('#ff-cockpit-internet-amount')).toHaveValue('45,50');

    await page.locator('[data-ff-cockpit-remember]').uncheck();
    expect(await page.evaluate((key) => localStorage.getItem(key), storageKey), 'Opt-out löscht lokale Eingaben').toBeNull();
  });
});
