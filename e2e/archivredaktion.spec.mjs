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
  // 23.11.2026: Der Artikel sagt es inzwischen schärfer („Alle Zahlen sind
  // freie Modellwerte, keine echten Angebote") – der Test prüft die
  // Aussage, nicht den alten Wortlaut. Der Anker bleibt unverändert.
  //
  // #1345: Aber auch der NEUE Wortlaut ist hier eingefroren, und genau das
  // war die Ursache des Ausfalls – derselbe Test hing zuvor an „frei
  // gewählte Modellannahmen", bis der Redaktionslauf aus #1329 die Passage
  // glättete; die Suite war darauf auf JEDEM Zweig rot, `main`
  // eingeschlossen (182 bestanden, 2 fehlgeschlagen). Dieses Repo fährt
  // automatische Sprachläufe über den Bestand (`40affb7 redaktion:
  // ZEIT-Niveau-Rechtschreibung (Premium-Wache)`, `d57924e Copy-Editing-
  // Highend`), der nächste Lauf kann die Formulierung wieder verschieben.
  // Der Kfz-Test oben nennt die Regel: „Ein hier festgeschriebener Titeltext
  // macht aus einer Redaktionsentscheidung einen Code-Test und bricht bei
  // jeder zulässigen Titeländerung."
  //
  // Darum zweigeteilt: (1) Muster, die beide Wortlaute zulassen, die das Haus
  // für Modellrechnungen kennt (`scripts/ki_shared.py:163` und
  // `scripts/generate_drafts.py:749`: „frei gewählte, als solche markierte"
  // Annahmen) – fällt die Kennzeichnung weg, bleibt der Test rot; nur eine
  // zulässige Umformulierung bricht ihn nicht mehr. Und (2) eine
  // Vorlagen-Konstante, die gar nicht im Artikel steht.
  const inhalt = page.locator('.post-content');
  await expect(inhalt, 'Modellrechnung als frei gewählt gekennzeichnet')
    .toContainText(/frei(?:e| gewählte)\s+Modell(?:werte|annahmen)/i);
  await expect(inhalt, 'ausdrücklich keine Marktangebote')
    .toContainText(/keine (?:echten )?Angebote/i);
  // `layouts/shortcodes/chart.html:38` setzt diese Zeile unter jedes
  // Datenblatt: „Modellrechnung: Die Werte gelten nur für die genannten
  // Annahmen." Kein Redaktionslauf fasst sie an, weil sie nicht im Artikel
  // steht – der stabile Anker dieses Tests. Genau ein Element, innerhalb von
  // `.post-content` (gemessen am Bauprodukt, sonst kippt der strict mode).
  await expect(inhalt.locator('.ff-chart__status'),
    'Datenblatt nennt sich Modellrechnung und bindet die Werte an Annahmen')
    .toContainText('Modellrechnung');
  // Bestehendes Sprungziel aus dem Beweisregister.
  await expect(page.locator('#rechenbeispiel-was-bringt-das-tagesgeld-konkret')).toHaveCount(1);
});
