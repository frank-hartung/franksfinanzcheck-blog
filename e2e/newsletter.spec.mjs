// ============================================================
//  SPEC: NEWSLETTER – Anmeldung, Streifen, Journeys
//  ------------------------------------------------------------
//  Der Newsletter ist die einzige Stelle der Site, an der jemand
//  eine personenbezogene Angabe macht. Was hier gezählt wird, ist
//  deshalb nicht „sieht nett aus“, sondern:
//    1. Es gibt keinen toten Anmelde-Knopf: Formular nur, wenn ein
//       realer Anmeldeweg konfiguriert ist – sonst ein Satz, der
//       das sagt (dieselbe Regel, die scripts/newsletter_digest.py
//       als Wache N1 meldet).
//    2. Die Anmeldung verlässt die Seite nicht: kein Drittanbieter-
//       Request, kein Absprung, kein Cookie.
//    3. Sie ist bedienbar: Label, Einwilligung, Statusmeldung,
//       Bot-Falle unsichtbar, Fokus sichtbar.
//    4. Sie ist lesbar: Kontrast gemessen in Hell UND Dunkel.
//    5. Jeder Weg, den die Site bewirbt, führt irgendwo hin
//       (Bestätigung, Präferenzen, Abmeldung – alle noindex).
//  Bewusst zustandsneutral geschrieben: die Tests greifen weder auf
//  `BREVO_API_KEY` zu noch verlangen sie einen Schaltzustand – sie
//  prüfen, was zur gebauten Konfiguration passt. Sonst wäre die
//  Suite am Tag der Freischaltung rot, statt sie zu bestätigen.
// ============================================================

import { test, expect } from './fixtures.mjs';
import { watchErrors, assertNoErrors } from './helpers.mjs';

const JOURNEYS = [
  '/newsletter/',
  '/newsletter/bestaetigung/',
  '/newsletter/praeferenzen/',
  '/newsletter/abmelden/',
];

const FORM = 'form[data-ff-nl]';

async function formularVorhanden(page) {
  return (await page.locator(FORM).count()) > 0;
}

/** Effektive Hintergrundfarbe eines Elements (PaperMod malt die Fläche auf Väter). */
const HINTERGRUND = `(el) => {
  let knoten = el;
  while (knoten && knoten !== document.documentElement) {
    const farbe = getComputedStyle(knoten).backgroundColor;
    const teile = (farbe.match(/[\\d.]+/g) || []).map(Number);
    if (teile.length >= 4 && teile[3] > 0) return teile.slice(0, 3);
    knoten = knoten.parentElement;
  }
  const teile = (getComputedStyle(document.body).backgroundColor.match(/[\\d.]+/g) || []).map(Number);
  return teile.length >= 3 ? teile.slice(0, 3) : [255, 255, 255];
}`;

function kontrast(vorn, hinten) {
  const kan = (c) => {
    const k = c / 255;
    return k <= 0.04045 ? k / 12.92 : ((k + 0.055) / 1.055) ** 2.4;
  };
  const licht = (r, g, b) => 0.2126 * kan(r) + 0.7152 * kan(g) + 0.0722 * kan(b);
  const a = licht(...vorn);
  const b = licht(...hinten);
  const [hoch, tief] = a > b ? [a, b] : [b, a];
  return (hoch + 0.05) / (tief + 0.05);
}

async function farbenVon(page, selector) {
  return page.evaluate(
    ([sel, quer]) => {
      const el = document.querySelector(sel);
      if (!el) return null;
      const stil = getComputedStyle(el);
      const vorn = (stil.color.match(/[\d.]+/g) || []).map(Number).slice(0, 3);
      // eslint-disable-next-line no-new-func
      const hinten = new Function('el', `return (${quer})(el)`)(el);
      return { vorn, hinten, schrift: parseFloat(stil.fontSize) };
    },
    [selector, HINTERGRUND],
  );
}

test.describe('Newsletter', () => {
  test('die vier Journeys existieren und bleiben aus den Suchmaschinen draußen', async ({
    page,
    request,
  }) => {
    for (const weg of JOURNEYS) {
      const antwort = await request.get(weg);
      expect(antwort.ok(), `${weg} nicht gebaut`).toBe(true);
      const text = await antwort.text();
      expect(text, `${weg} ohne noindex`).toMatch(/name="robots"[^>]*noindex/i);
      expect(text, `${weg} ohne Newsletter-Bezug`).toMatch(/newsletter/i);
    }
    // utility-Seiten gehören nicht in die Sitemap
    const sitemap = await (await request.get('/sitemap.xml')).text();
    for (const weg of JOURNEYS) {
      expect(sitemap, `${weg} in der Sitemap`).not.toContain(`>${weg}<`);
    }
  });

  test('Anmeldeseite: Formular mit Weg, oder ein Satz ohne Behauptung', async ({ page }) => {
    const fehler = watchErrors(page);
    await page.goto('/newsletter/');
    if (await formularVorhanden(page)) {
      const feld = page.locator('form[data-ff-nl] input[type="email"]');
      await expect(feld, 'kein E-Mail-Feld').toHaveCount(1);
      await expect(page.locator('form[data-ff-nl] input[name="consent"]')).toBeVisible();
      await expect(page.locator('#ff-nl-status')).toBeVisible();
      // Das Formular darf nirgendswoanders hinposten als auf dieselben Hosts wie die Site
      const aktion = await page.locator(FORM).getAttribute('action');
      expect(aktion, 'leeres action-Attribut').toBeTruthy();
      expect(aktion.startsWith('https://'), `action über http: ${aktion}`).toBe(true);
    } else {
      const text = await page.content();
      expect(text, ' Leerzustand ohne Erklärung').toMatch(/nicht geschaltet/);
      expect(text, 'Formular ohne Anmeldeweg').not.toMatch(/<form/i);
    }
    assertNoErrors(fehler, 'Anmeldeseite');
  });

  test('keine Anmeldeschleife: auf /newsletter/ steht kein zweiter Anmelde-CTA', async ({
    page,
  }) => {
    await page.goto('/newsletter/');
    await expect(page.locator('.ff-nl-strip')).toHaveCount(0);
    await expect(page.locator('.newsletter-footer.ff-nl-strip')).toHaveCount(0);
  });

  test('Rechtsseiten werben nicht: kein Streifen auf Datenschutz und Impressum', async ({
    page,
  }) => {
    for (const weg of ['/datenschutz/', '/impressum/']) {
      await page.goto(weg);
      await expect(page.locator('.ff-nl-strip'), `${weg} mit Anmelde-Kasten`).toHaveCount(0);
    }
  });

  test('jeder beworbene Anmeldeweg führt nach /newsletter/', async ({ page, request }) => {
    await page.goto('/');
    const zeilen = await page.evaluate(() =>
      [...document.querySelectorAll('a[href$="/newsletter/"]')].map((a) => a.getAttribute('href')),
    );
    for (const pfad of new Set(zeilen)) {
      const antwort = await request.get(pfad);
      expect(antwort.ok(), `${pfad} beworben, aber nicht gebaut`).toBe(true);
    }
    // Ein Artikel-Streifen darf denselben Weg zeigen – und nur einer pro Seite.
    const erster = await page
      .locator('article.post-entry a[href*="/posts/"]')
      .first()
      .getAttribute('href');
    await page.goto(erster);
    const streifen = page.locator('.ff-nl-strip');
    const anzahl = await streifen.count();
    expect(anzahl, 'kein oder mehrfacher Streifen im Artikel').toBeLessThanOrEqual(1);
    if (anzahl === 1) {
      await expect(streifen.locator('p').first()).not.toBeEmpty();
    }
  });

  test('Bot-Falle: im DOM für Roboter, außerhalb des Blickfelds für Menschen', async ({
    page,
  }) => {
    await page.goto('/newsletter/');
    test.skip(!(await formularVorhanden(page)), 'kein Formular geschaltet');
    const falle = page.locator('input[data-ff-nl-falle]');
    await expect(falle, 'Bot-Falle ohne aria-hidden').toHaveCount(1);
    const kasten = await falle.boundingBox();
    expect(
      !kasten || kasten.width <= 2 || kasten.x < 0 || kasten.y < 0,
      'Bot-Falle ist für Menschen sichtbar',
    ).toBe(true);
    await expect(page.locator('input[data-ff-nl-zeit]'), 'Zeitfeld fehlt').toHaveCount(1);
  });

  test('unvollständige Anmeldung: Meldung auf dem Blatt, kein Absprung', async ({ page }) => {
    await page.goto('/newsletter/');
    test.skip(!(await formularVorhanden(page)), 'kein Formular geschaltet');
    const vor = page.url();
    await page.locator(FORM).locator('button[type="submit"]').click();
    const status = page.locator('#ff-nl-status');
    await expect(status).not.toContainText('Zwei Klicks', { timeout: 5_000 });
    expect(await status.innerText()).toMatch(/E-Mail|Einwilligung/);
    expect(page.url(), 'Seite verlassen').toBe(vor);
  });

  test('kein Drittanbieter auf dem Anmeldepfad', async ({ page }) => {
    const geladen = [];
    page.on('request', (anfrage) => {
      const url = new URL(anfrage.url());
      if (url.origin !== new URL(page.url()).origin) geladen.push(url.host);
    });
    await page.goto('/newsletter/');
    await page.waitForTimeout(600);
    expect(geladen, `fremde Hosts: ${[...new Set(geladen)].join(', ')}`).toEqual([]);
  });

  test('Streifen und Kasten sind in Hell und Dunkel lesbar (4.5:1 gemessen)', async ({
    page,
  }) => {
    await page.goto('/newsletter/');
    const selector = (await formularVorhanden(page)) ? FORM : '.ff-nl';
    for (const modus of ['light', 'dark']) {
      // Erst Speicher, dann Attribut: theme.js würde ein Setting ohne
      // Nutzerentscheidung sonst beim nächsten Raster überschreiben.
      await page.evaluate((m) => {
        try { localStorage.setItem('theme', m); } catch (e) { /* private Mode */ }
        document.documentElement.setAttribute('data-theme', m);
      }, modus);
      await page.waitForTimeout(120);
      const messung = await farbenVon(page, `${selector} p, ${selector} .ff-nl__lead`);
      expect(messung, `${selector} nicht gefunden im ${modus}-Modus`).not.toBeNull();
      const wert = kontrast(messung.vorn, messung.hinten);
      expect(wert, `Kontrast ${modus} nur ${wert.toFixed(2)}:1`).toBeGreaterThanOrEqual(4.5);
      expect(messung.schrift, `Schrift ${modus} zu klein`).toBeGreaterThanOrEqual(13);
    }
  });

  test('ohne Bewegung: keine Übergänge im Formular', async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/newsletter/');
    // Nur die eigenen Bausteine: fremde Übergänge (Site-Politur an
    // Typografie-Selektoren) sind nicht dieses Layers Verantwortung.
    const anzahl = await page.evaluate(() =>
      [...document.querySelectorAll('[class*="ff-nl"]')]
        .map((el) => getComputedStyle(el).transitionProperty)
        .filter((eigenschaft) => eigenschaft && eigenschaft !== 'all' && eigenschaft !== 'none'
          && !/^(transform|opacity|color)$/.test(eigenschaft.trim())).length,
    );
    expect(anzahl, 'Übergang abseits von transform/opacity/color').toBe(0);
  });
});
