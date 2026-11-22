import { test, expect } from './fixtures.mjs';

test('Kfz-Korrektur erreicht Leser vor dem Teaser der neuen Fassung', async ({ page }) => {
  await page.goto('/posts/2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen/');
  // H1 nur auf Substanz prüfen, nicht auf den exakten Titeltext: Der Titel
  // lebt im Frontmatter und wird redaktionell gepflegt (M1-Heilung 64 → 59
  // Zeichen am 22.11.2026). Ein hier festgeschriebener Titeltext macht aus
  // einer Redaktionsentscheidung einen Code-Test und bricht bei jeder
  // zulässigen Titeländerung – geprüft wird, was dieser Test wirklich
  // schützt: dass die richtige Seite geladen ist und die Korrektur trägt.
  const h1 = page.locator('h1');
  expect(await h1.count(), 'Kfz-Artikel: genau ein H1').toBe(1);
  await expect(h1).toContainText('Kfz-Versicherung vergleichen');
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
