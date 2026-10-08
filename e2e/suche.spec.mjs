// ============================================================
//  SPEC: SUCHE (Pagefind) – die Suchseite /suche/ im echten Browser
//  ------------------------------------------------------------
//  Was hier gezählt wird – nicht „sieht nett aus“, sondern die Zusagen
//  der Suchseite (content/suche/index.md) und des Datenschutzhinweises:
//    1. Sie findet Inhalt: „Tagesgeld“ liefert Artikel oder Ratgeber
//       mit echten, internen Links.
//    2. Die Suchseite selbst und noindex-Seiten sind nie Treffer.
//    3. Die Eingabe bleibt im Browser: kein Seitenwechsel, kein ?q=,
//       keine Anfrage an fremde Hosts, nichts im Speicher.
//    4. Ohne JavaScript: Formular verborgen, Hinweis mit den Wegen
//       über das Menü (kein toter Knopf).
//    5. Leere Suche und Ein-Zeichen-Eingabe: konkrete Ansage.
//    6. Tastatur: Fokus sichtbar. Mobil: kein horizontales Scrollen.
//  Voraussetzung: der Suchindex ist gebaut (npm run build bzw.
//  npm run suchindex). Fehlt er, scheitert der Test mit Klartext.
// ============================================================

import { test, expect } from './fixtures.mjs';
import { watchErrors, assertNoErrors } from './helpers.mjs';

const EINGABE = '[data-ff-suche-eingabe]';
const FORMULAR = '[data-ff-suche-form]';
const STATUS = '[data-ff-suche-status]';
const TREFFER = '[data-ff-suche-liste] > li';
const TITEL_LINK = '[data-ff-suche-liste] a.ff-suche__titel';

/** Erlaubte Ursprünge für Anfragen während der Suche: nur die eigene Site. */
function eigeneUrsprunge(baseURL) {
  return new Set([new URL(baseURL).origin, 'https://franksfinanzcheck.de']);
}

test.describe('Suche auf /suche/', () => {
  test('Index ist ausgeliefert (sonst ist die Suche nur eine leere Hülle)', async ({ request }) => {
    const js = await request.get('/pagefind/pagefind.js');
    expect(js.status(), 'public/pagefind/pagefind.js fehlt – erst npm run build').toBe(200);
    const eintrag = await request.get('/pagefind/pagefind-entry.json');
    expect(eintrag.status(), 'pagefind-entry.json fehlt – erst npm run build').toBe(200);
  });

  test('Suchmaske ist beschriftet und erscheint mit JavaScript', async ({ page }) => {
    await page.goto('/suche/');
    await expect(page.locator(FORMULAR)).toBeVisible();
    const feld = page.getByLabel('Suchbegriff');
    await expect(feld).toBeVisible();
    await expect(feld).toHaveAttribute('type', 'search');
    await expect(page.getByRole('search')).toBeVisible();
  });

  test('„Tagesgeld“ liefert Artikel oder Ratgeber mit internen Links', async ({ page, baseURL }) => {
    const fehler = watchErrors(page);
    await page.goto('/suche/');
    const adresse = page.url();

    const anfragen = [];
    page.on('request', (r) => anfragen.push(r.url()));

    await page.locator(EINGABE).fill('Tagesgeld');
    await expect(page.locator(STATUS)).toContainText('Treffer für „Tagesgeld“', { timeout: 20_000 });
    await expect(page.locator(TREFFER).first()).toBeVisible();

    const ziele = await page.locator(TITEL_LINK).evaluateAll((as) => as.map((a) => a.getAttribute('href')));
    expect(ziele.length, 'mindestens ein Treffer').toBeGreaterThan(0);
    for (const ziel of ziele) {
      expect(ziel, `Treffer ist ein gleich-seitiger Pfad: ${ziel}`).toMatch(/^\/(?!\/)/);
    }
    expect(ziele.some((z) => z.startsWith('/posts/') || z.startsWith('/pillar/')),
      'Artikel oder Ratgeber unter den Treffern').toBeTruthy();
    expect(ziele.some((z) => z.startsWith('/suche')), 'die Suchseite ist nie Treffer').toBeFalsy();
    expect(ziele.some((z) => z.startsWith('/newsletter')), 'noindex-Seiten sind nie Treffer').toBeFalsy();

    expect(page.url(), 'kein Seitenwechsel während der Suche').toBe(adresse);

    const eigene = eigeneUrsprunge(baseURL);
    const fremd = anfragen.filter((u) => !eigene.has(new URL(u).origin));
    expect(fremd, 'während der Suche keine Anfrage an fremde Hosts').toEqual([]);

    const speicher = await page.evaluate(() => JSON.stringify({
      local: Object.entries(localStorage), session: Object.entries(sessionStorage),
    }));
    expect(speicher, 'der Suchbegriff landet in keinem Speicher').not.toContain('Tagesgeld');

    assertNoErrors(fehler, 'Suche Tagesgeld');
  });

  test('Enter sendet kein GET-Formular: URL bleibt ohne ?q=', async ({ page }) => {
    await page.goto('/suche/');
    const adresse = page.url();
    await page.locator(EINGABE).fill('Miete');
    await page.locator(EINGABE).press('Enter');
    await expect(page.locator(STATUS)).toContainText('Miete', { timeout: 20_000 });
    expect(page.url()).toBe(adresse);
    expect(page.url()).not.toContain('?');
  });

  test('Zu kurze Eingabe und leere Trefferliste bekommen je eine Ansage', async ({ page }) => {
    await page.goto('/suche/');
    await page.locator(EINGABE).fill('a');
    await expect(page.locator(STATUS)).toHaveText('Gib mindestens zwei Zeichen ein.');
    await page.locator(EINGABE).fill('Zyklotronbeschleuniger');
    await expect(page.locator(STATUS)).toContainText('Keine Treffer für „Zyklotronbeschleuniger“.', { timeout: 20_000 });
    await expect(page.locator(TREFFER)).toHaveCount(0);
  });

  test('Tastatur: Suchfeld hat sichtbaren Fokusrahmen', async ({ page }) => {
    await page.goto('/suche/');
    await page.keyboard.press('Tab');
    await page.locator(EINGABE).focus();
    await page.keyboard.press('Shift+Tab');
    await page.keyboard.press('Tab');
    const fokus = await page.locator(EINGABE).evaluate((el) => ({
      sichtbar: el.matches(':focus-visible'),
      rahmen: getComputedStyle(el).outlineStyle,
    }));
    expect(fokus.sichtbar, 'Suchfeld hat Tastaturfokus').toBeTruthy();
    expect(fokus.rahmen, 'Fokusrahmen ist nicht unterdrückt').not.toBe('none');
  });

  test('Mobil (375 px): kein horizontales Scrollen auf der Suchseite', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/suche/');
    await expect(page.locator(FORMULAR)).toBeVisible();
    const ueberlauf = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(ueberlauf, 'horizontaler Überlauf in px').toBeLessThanOrEqual(1);
  });

  test('Footer verlinkt die Suche auf jeder Seite', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('footer a[href$="/suche/"]')).toHaveCount(1);
  });
});

test.describe('Suche ohne JavaScript', () => {
  test.use({ javaScriptEnabled: false });

  test('Formular bleibt verborgen, der Hinweis nennt die Wege über das Menü', async ({ page }) => {
    await page.goto('/suche/');
    await expect(page.locator(FORMULAR)).toBeHidden();
    const hinweis = page.locator('.ff-suche__ohne-js');
    await expect(hinweis).toBeVisible();
    await expect(hinweis).toContainText('braucht JavaScript');
    await expect(hinweis.getByRole('link', { name: 'Blog' })).toBeVisible();
    // Jeder Weg aus dem Hinweis muss eine echte Seite sein – sonst ist es ein toter Link.
    const ziele = await hinweis.locator('a').evaluateAll((as) => as.map((a) => a.getAttribute('href')));
    expect(ziele.length, 'drei Wege: Blog, Ratgeber, Werkzeuge').toBe(3);
    for (const ziel of ziele) {
      const antwort = await page.request.get(ziel);
      expect(antwort.status(), `Weg ohne JavaScript erreichbar: ${ziel}`).toBeLessThan(400);
    }
  });
});
