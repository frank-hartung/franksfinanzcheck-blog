import { test, expect } from './fixtures.mjs';

const ARTICLE = '/posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/';

test.describe('Datenvisualisierung', () => {
  test('SVG, Methodik und vollständige Datentabelle werden statisch ausgeliefert', async ({ page }) => {
    await page.goto(ARTICLE);
    const chart = page.locator('[data-ff-chart]').first();
    await expect(chart).toBeVisible();
    await expect(chart.locator('svg[role="img"]')).toBeVisible();
    await expect(chart.locator('figcaption')).toContainText('Datenstand');
    await expect(chart.locator('figcaption')).toContainText('Methodik');
    await chart.locator('details summary').click();
    await expect(chart.locator('table tbody tr')).toHaveCount(5);
  });

  test('Datenmarken sind per Tastatur fokussierbar und zugänglich benannt', async ({ page }) => {
    await page.goto(ARTICLE);
    const marks = page.locator('[data-ff-chart] .ff-chart__mark');
    await expect(marks).toHaveCount(5);
    await marks.first().focus();
    await expect(marks.first()).toBeFocused();
    await expect(marks.first()).toHaveAttribute('role', 'img');
    await expect(marks.first()).toHaveAttribute('aria-label', /Girokonto.*0,00.*€ pro Jahr/);
  });
});
