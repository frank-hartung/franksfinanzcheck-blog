// ============================================================
// SPEC: WERKZEUGE – eigenständige Rechner, lokal und werbefrei
// ------------------------------------------------------------
// Geprüft wird das Produktversprechen im echten Browser, nicht
// die Rechenlogik: die deckt tools/werkzeuge.test.mjs ab.
// Hier zählt, was ein Besucher erlebt – Hub, Ergebnis ohne
// Seitenwechsel, Export als Datei, Opt-in-Speicher, Methodik
// ohne Klick und: kein Netzaufruf, kein Partnerlink.
// ============================================================

import { test, expect } from './fixtures.mjs';
import { consentAway, EXTERNAL_NOISE } from './helpers.mjs';

const VERSPRECHEN = 'Du kannst das Tool vollständig nutzen, ohne einen Affiliate-Link anzuklicken.';

/** Rechnen auslösen, ohne mit dem Consent-Banner um Klicks zu ringen. */
async function rechnen(werkzeug) {
  await werkzeug.locator('form').evaluate((form) => form.requestSubmit());
}

test.describe('Werkzeuge', () => {
  test('der Hub ist über die Navigation erreichbar und führt zu allen acht Werkzeugen', async ({ page }) => {
    await page.goto('/');
    const navLink = page.locator('nav a[href*="/werkzeuge/"]').first();
    await expect(navLink, 'Hauptnavigation führt zu den Werkzeugen').toBeVisible();

    await navLink.click();
    await expect(page).toHaveURL(/\/werkzeuge\/?$/);
    await expect(page.locator('h1')).toHaveCount(1);
    await expect(page.getByText(VERSPRECHEN).first()).toBeVisible();

    const karten = page.locator('.ff-wz-raster a[href*="/werkzeuge/"]');
    await expect(karten, 'acht Werkzeuge im Raster').toHaveCount(8);

    const ziele = await karten.evaluateAll((nodes) => nodes.map((n) => new URL(n.href).pathname));
    expect(new Set(ziele).size, 'jede Karte führt woanders hin').toBe(8);
    for (const ziel of ziele) {
      const antwort = await page.request.get(ziel);
      expect(antwort.status(), `${ziel} ist erreichbar`).toBe(200);
    }
  });

  test('rechnet im Browser, ohne die Seite zu verlassen und ohne einen Netzaufruf', async ({ page }) => {
    // Jede aktive Anfrage mitschreiben – inklusive Rumpf, denn die eigentliche
    // Zusage lautet: Die eingetippten Zahlen verlassen das Gerät nicht.
    // Die seitenweite Reichweitenmessung (EXTERNAL_NOISE, z. B. umami) gehört
    // nicht zum Rechner; sie läuft auf jeder Seite und hat ihre eigene
    // Einwilligung. Sie wird hier getrennt, aber nicht ignoriert: Auch sie
    // darf keine Eingabe tragen.
    const anfragen = [];
    page.on('request', (request) => {
      if (!['xhr', 'fetch', 'websocket'].includes(request.resourceType())) return;
      anfragen.push({ url: request.url(), rumpf: request.postData() || '' });
    });
    const istFremd = (url) => EXTERNAL_NOISE.some((host) => url.includes(host));

    await page.goto('/werkzeuge/notgroschen-rechner/');
    const werkzeug = page.locator('[data-ff-werkzeug]');
    await expect(werkzeug).toHaveCount(1);
    await expect(werkzeug.locator('form')).not.toHaveAttribute('action', /./);
    await expect(werkzeug.locator('[data-ff-wz-ausgabe]')).toBeHidden();

    await page.locator('#ff-wz-notgroschen-ausgaben').fill('2000');
    await page.locator('#ff-wz-notgroschen-erspartes').fill('1500');
    await page.locator('#ff-wz-notgroschen-sparrate').fill('250');
    await rechnen(werkzeug);

    const ausgabe = werkzeug.locator('[data-ff-wz-ausgabe]');
    await expect(ausgabe).toBeVisible();
    await expect(werkzeug.locator('[data-ff-wz-leer]')).toBeHidden();
    // 3 Monatsausgaben × 2.000 € = 6.000 €, davon fehlen noch 4.500 € = 18 Monate.
    await expect(ausgabe.locator('[data-ff-wz-kennzahlen]')).toContainText(/6\.000/);
    await expect(ausgabe.locator('[data-ff-wz-kennzahlen]')).toContainText('1 Jahr und 6 Monate');
    await expect(page).toHaveURL(/\/werkzeuge\/notgroschen-rechner\/$/);

    expect(
      anfragen.filter((a) => !istFremd(a.url)).map((a) => a.url),
      'der Rechner selbst schickt nichts ins Netz'
    ).toEqual([]);

    const verraeter = anfragen.filter((a) => /\b(2000|1500|250)\b/.test(a.url + a.rumpf));
    expect(verraeter, 'keine Anfrage trägt die eingetippten Zahlen').toEqual([]);
  });

  test('zeigt Formel, Annahmen und Quellen ohne einen einzigen Klick', async ({ page }) => {
    await page.goto('/werkzeuge/abschlag-nachzahlung-rechner/');
    const werkzeug = page.locator('[data-ff-werkzeug]');

    await expect(werkzeug.locator('[data-ff-wz-formel] li').first()).toBeVisible();
    await expect(werkzeug.locator('[data-ff-wz-annahme] li').first()).toBeVisible();
    const quellen = werkzeug.locator('[data-ff-wz-quelle]');
    expect(await quellen.count()).toBeGreaterThan(0);
    await expect(quellen.first()).toBeVisible();
    await expect(quellen.first().locator('a')).toHaveAttribute('href', /^https:\/\//);
    await expect(page.locator('details')).toHaveCount(0);
  });

  test('enthält keinen Partnerlink – das Versprechen steht auf jeder Seite', async ({ page }) => {
    for (const pfad of ['/werkzeuge/', '/werkzeuge/fixkosten-scanner/', '/werkzeuge/tarifwechsel-entscheidungsbaum/']) {
      await page.goto(pfad);
      await expect(page.getByText(VERSPRECHEN).first(), `Versprechen auf ${pfad}`).toBeVisible();
      await expect(page.locator('a[href*="/go/"]'), `kein /go/-Link auf ${pfad}`).toHaveCount(0);
      await expect(page.locator('a[rel*="sponsored"]'), `kein sponsored-Link auf ${pfad}`).toHaveCount(0);
    }
  });

  test('exportiert das Ergebnis als CSV – erzeugt im Browser, mit Quellen und Versprechen', async ({ page }) => {
    await page.goto('/werkzeuge/fixkosten-scanner/');
    const werkzeug = page.locator('[data-ff-werkzeug]');
    await page.locator('#ff-wz-fixkosten-scanner-wohnen').fill('1200');
    await page.locator('#ff-wz-fixkosten-scanner-energie').fill('150');
    await page.locator('#ff-wz-fixkosten-scanner-kommunikation').fill('60');
    await rechnen(werkzeug);
    await expect(werkzeug.locator('[data-ff-wz-ausgabe]')).toBeVisible();

    await consentAway(page);
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      werkzeug.locator('[data-ff-wz-export-format="csv"]').click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/^franksfinanzcheck-fixkosten-scanner-\d{4}-\d{2}-\d{2}\.csv$/);

    const datei = await download.createReadStream();
    const inhalt = await new Promise((resolve, reject) => {
      const teile = [];
      datei.on('data', (chunk) => teile.push(chunk));
      datei.on('end', () => resolve(Buffer.concat(teile).toString('utf8')));
      datei.on('error', reject);
    });
    expect(inhalt.charCodeAt(0), 'BOM für Excel').toBe(0xfeff);
    expect(inhalt).toContain(';');
    expect(inhalt).toContain('Eingaben');
    expect(inhalt).toContain('Quellen');
    expect(inhalt).toContain(VERSPRECHEN);
  });

  test('legt Kündigungstermine als Kalenderdatei ab', async ({ page }) => {
    await page.goto('/werkzeuge/kuendigungsfristen-kalender/');
    const werkzeug = page.locator('[data-ff-werkzeug]');
    await page.locator('#ff-wz-kuendigungsfristen-vertragsende').fill('2027-05-31');
    await page.locator('#ff-wz-kuendigungsfristen-frist_wert').fill('3');
    await rechnen(werkzeug);

    const ausgabe = werkzeug.locator('[data-ff-wz-ausgabe]');
    await expect(ausgabe).toBeVisible();
    // 31.05. minus drei Monate wird kalendarisch gekappt.
    await expect(ausgabe.locator('[data-ff-wz-kennzahlen]')).toContainText('28.02.2027');
    await expect(ausgabe.locator('[data-ff-wz-termine] li')).toHaveCount(3);

    await consentAway(page);
    const [download] = await Promise.all([
      page.waitForEvent('download'),
      werkzeug.locator('[data-ff-wz-export-format="ics"]').click(),
    ]);
    expect(download.suggestedFilename()).toMatch(/\.ics$/);
    const datei = await download.createReadStream();
    const ics = await new Promise((resolve, reject) => {
      const teile = [];
      datei.on('data', (chunk) => teile.push(chunk));
      datei.on('end', () => resolve(Buffer.concat(teile).toString('utf8')));
      datei.on('error', reject);
    });
    expect(ics).toContain('BEGIN:VCALENDAR');
    expect(ics).toContain('DTSTART;VALUE=DATE:20270228');
    expect(ics).toContain('TRIGGER:-PT9H');
  });

  test('speichert das Haushaltsbudget nur nach Opt-in und räumt beim Zurücksetzen auf', async ({ page }) => {
    const schluessel = 'ff_werkzeug_haushaltsbudget_v1';
    await page.goto('/werkzeuge/haushaltsbudget/');
    const werkzeug = page.locator('[data-ff-werkzeug]');

    expect(await page.evaluate((k) => localStorage.getItem(k), schluessel), 'kein Speicher ohne Opt-in').toBeNull();

    await page.locator('#ff-wz-haushaltsbudget-einkommen').fill('3000');
    await page.locator('#ff-wz-haushaltsbudget-wohnen').fill('1200');
    await page.locator('#ff-wz-haushaltsbudget-sparen').fill('400');
    await rechnen(werkzeug);
    await expect(werkzeug.locator('[data-ff-wz-ausgabe]')).toBeVisible();
    await expect(werkzeug.locator('[data-ff-wz-liste]')).toContainText('Bedarf');
    expect(await page.evaluate((k) => localStorage.getItem(k), schluessel), 'Rechnen allein speichert nichts').toBeNull();

    await consentAway(page);
    await werkzeug.locator('[data-ff-wz-speichern]').check();
    expect(await page.evaluate((k) => localStorage.getItem(k), schluessel)).toContain('3000');

    await page.reload();
    await expect(page.locator('#ff-wz-haushaltsbudget-einkommen')).toHaveValue('3000');
    await expect(page.locator('[data-ff-wz-speichern]')).toBeChecked();
    await expect(page.locator('[data-ff-wz-ausgabe]')).toBeVisible();

    await consentAway(page);
    await page.addStyleTag({ content: 'html { scroll-behavior: auto !important; }' });
    const reset = page.locator('[data-ff-wz-reset]');
    await reset.scrollIntoViewIfNeeded();
    await page.evaluate(() => window.scrollBy(0, -180));
    await reset.click();
    await expect(page.locator('#ff-wz-haushaltsbudget-einkommen')).toHaveValue('');
    await expect(page.locator('[data-ff-wz-speichern]')).not.toBeChecked();
    await expect(page.locator('[data-ff-wz-ausgabe]')).toBeHidden();
    expect(await page.evaluate((k) => localStorage.getItem(k), schluessel), 'Zurücksetzen löscht lokal').toBeNull();
  });

  test('verlangt fehlende Pflichtangaben, statt eine Zahl zu erfinden', async ({ page }) => {
    await page.goto('/werkzeuge/selbstbehalt-rechner/');
    const werkzeug = page.locator('[data-ff-werkzeug]');
    await rechnen(werkzeug);

    await expect(werkzeug.locator('[data-ff-wz-fehler]')).toBeVisible();
    await expect(werkzeug.locator('[data-ff-wz-ausgabe]')).toBeHidden();
    await expect(werkzeug.locator('[data-ff-wz-fehler]')).toContainText(/Beitrag/i);
  });

  test('der Rechenkern bleibt ohne JavaScript ehrlich: noscript statt leerer Hülle', async ({ browser }) => {
    const kontext = await browser.newContext({ javaScriptEnabled: false });
    const seite = await kontext.newPage();
    await seite.goto('/werkzeuge/notgroschen-rechner/');
    await expect(seite.locator('[data-ff-werkzeug] noscript')).toHaveCount(1);
    await expect(seite.getByText(VERSPRECHEN).first()).toBeVisible();
    await expect(seite.locator('[data-ff-wz-formel] li').first()).toBeVisible();
    await kontext.close();
  });
});
