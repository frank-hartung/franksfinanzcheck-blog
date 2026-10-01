// ============================================================
// SPEC: FIXKOSTEN-COCKPIT – Produktkern, lokale Rechnung, Privatsphäre
// ============================================================

import { test, expect } from './fixtures.mjs';
import { consentAway } from './helpers.mjs';

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

  test('formuliert Prüftermine ehrlich: vergangene Termine drängen, ferne bleiben ruhig', async ({ page }) => {
    await page.goto('/cockpit/');
    const cockpit = page.locator('[data-ff-fixkosten-cockpit]');
    const heute = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Berlin' }).format(new Date());

    await page.locator('#ff-cockpit-energie-amount').fill('100');
    await page.locator('#ff-cockpit-energie-date').fill(heute);
    await page.locator('#ff-cockpit-versicherung-amount').fill('50');
    await page.locator('#ff-cockpit-versicherung-date').fill('2020-01-01');
    await page.locator('#ff-cockpit-mobilitaet-amount').fill('30');
    await page.locator('#ff-cockpit-mobilitaet-date').fill('2031-12-24');
    await cockpit.locator('form').evaluate((form) => form.requestSubmit());

    const deadlines = cockpit.locator('[data-ff-cockpit-deadlines] li');
    await expect(deadlines).toHaveCount(3);
    // Ältester Termin zuerst – vergangene Termine brauchen die dringendste Aufmerksamkeit.
    await expect(deadlines.nth(0)).toContainText(/Versicherungen: Termin vom 01\.01\.2020 liegt zurück – jetzt prüfen\./);
    await expect(deadlines.nth(1)).toContainText(/Strom & Gas: heute als nächsten Check vorgesehen\./);
    await expect(deadlines.nth(2)).toContainText(/Mobilität & Reisen: nächster Check am 24\.12\.2031\./);
  });

  test('kopiert den Prüfplan als vollständigen Klartext', async ({ page }) => {
    await page.context().grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.goto('/cockpit/');
    const cockpit = page.locator('[data-ff-fixkosten-cockpit]');

    await page.locator('#ff-cockpit-energie-amount').fill('100');
    await page.locator('#ff-cockpit-konto-amount').fill('9,90');
    await cockpit.locator('form').evaluate((form) => form.requestSubmit());

    // Ergebnis-Knopf kann je nach Viewport unter dem Consent-Banner liegen.
    await consentAway(page);
    await cockpit.locator('[data-ff-cockpit-copy]').click();
    await expect(cockpit.locator('[data-ff-cockpit-copy]')).toContainText('Kopiert');

    // toLocaleString('de-DE', currency) setzt geschützte Leerzeichen (U+00A0)
    // zwischen Betrag und € – normalisieren statt mit exotischen Regexes kämpfen.
    const klartext = (await page.evaluate(() => navigator.clipboard.readText())).replace(/\u00A0/g, ' ');
    expect(klartext, 'Titel des Prüfplans').toContain('Mein Fixkosten-Prüfplan');
    expect(klartext, 'Monatssumme').toContain('109,90');
    expect(klartext, 'Jahressumme').toContain('1.318,80');
    expect(klartext, 'Reihenfolge: größter Posten zuerst').toMatch(/1\. Strom & Gas: 100,00 € pro Monat/);
    expect(klartext, 'Herkunftsangabe').toContain('Fixkosten-Cockpit von FranksFinanzcheck');
  });

  test('Zurücksetzen räumt vollständig: Eingaben, Opt-in, lokaler Speicher, Ergebnis', async ({ page }) => {
    await page.goto('/cockpit/');
    const cockpit = page.locator('[data-ff-fixkosten-cockpit]');
    const storageKey = 'ff_fixkosten_cockpit_v1';
    // Dialog-Handler bewusst minimal (nur annehmen, Nachricht merken):
    // Assertion-Rückgaben sind undefined – ein „expect(...) && accept()“
    // würde den Accept-Kurzschluss nie erreichen und den Dialog offen
    // lassen. Geprüft wird danach, im regulären Testkontext.
    let dialogNachricht = null;
    page.on('dialog', async (dialog) => {
      dialogNachricht = dialog.message();
      await dialog.accept();
    });

    await page.locator('#ff-cockpit-energie-amount').fill('100');
    await page.locator('#ff-cockpit-energie-date').fill('2030-01-15');
    await cockpit.locator('form').evaluate((form) => form.requestSubmit());
    await expect(cockpit.locator('[data-ff-cockpit-result]')).toBeVisible();
    await cockpit.locator('[data-ff-cockpit-remember]').check();
    expect(await page.evaluate((key) => localStorage.getItem(key), storageKey)).toContain('100');

    // Der Consent-Banner (position:fixed, volle untere Kante) fängt sonst
    // den Klick auf den Reset-Knopf ab – wie ein echter Besucher klären.
    await consentAway(page);

    // Klick-Robustheit: Das Blog scrollt weich (CSS scroll-behavior: smooth)
    // und trägt einen Sticky-Header. Zusammen ließen sie Playwrights
    // Stabilitätsprüfung springen, bis das Klick-Budget verbraucht war.
    // Wie scrollThrough (helpers.mjs): temporär hart scrollen und den
    // Knopf gezielt unterhalb des Sticky-Headers platzieren.
    await page.addStyleTag({ content: 'html { scroll-behavior: auto !important; }' });
    const resetKnopf = cockpit.locator('[data-ff-cockpit-reset]');
    await resetKnopf.scrollIntoViewIfNeeded();
    await page.evaluate(() => window.scrollBy(0, -180));
    await resetKnopf.click();
    expect(dialogNachricht, 'Reset fragt nachdrücklich nach Bestätigung').toContain('zurücksetzen');
    await expect(cockpit.locator('[data-ff-cockpit-result]')).toBeHidden();
    await expect(page.locator('#ff-cockpit-energie-amount')).toHaveValue('');
    await expect(page.locator('#ff-cockpit-energie-date')).toHaveValue('');
    await expect(cockpit.locator('[data-ff-cockpit-remember]')).not.toBeChecked();
    expect(await page.evaluate((key) => localStorage.getItem(key), storageKey), 'Reset löscht den lokalen Speicher').toBeNull();

    await page.reload();
    await expect(page.locator('#ff-cockpit-energie-amount'), 'nach Reload bleibt alles leer').toHaveValue('');
    expect(await page.evaluate((key) => localStorage.getItem(key), storageKey)).toBeNull();
  });
});
