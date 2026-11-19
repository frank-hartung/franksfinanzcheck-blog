import { test, expect } from './fixtures.mjs';

test('Kfz-Korrektur erreicht Leser vor dem Teaser der neuen Fassung', async ({ page }) => {
  await page.goto('/posts/2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen/');
  await expect(page.locator('h1')).toHaveText('Kfz-Versicherung vergleichen: Was ändert sich außer dem Beitrag?');
  const korrektur = page.locator('.ff-korrektur');
  await expect(korrektur).toContainText('Kündigungsfrist');
  await expect(korrektur).toContainText('keine durchschnittliche Ersparnis');
  await expect(page.locator('.ff-korrektur ~ .post-description')).toHaveCount(1);
});

test('Tagesgeld-Modell bleibt als Rechnung und nicht als Marktangebot erkennbar', async ({ page }) => {
  await page.goto('/posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/');
  await expect(page.locator('.post-content')).toContainText('frei gewählte Modellannahmen');
  await expect(page.locator('.post-content')).toContainText('keine Angebote');
  // Bestehendes Sprungziel aus dem Beweisregister.
  await expect(page.locator('#rechenbeispiel-was-bringt-das-tagesgeld-konkret')).toHaveCount(1);
});
