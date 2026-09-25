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
//  Mail-API-Keys zu noch verlangen sie einen Schaltzustand – sie
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
    if (teile.length >= 3 && (teile.length === 3 || teile[3] > 0)) return teile.slice(0, 3);
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
      const rgba = (stil.color.match(/[\d.]+/g) || []).map(Number);
      // eslint-disable-next-line no-new-func
      const hinten = new Function('el', `return (${quer})(el)`)(el);
      const alpha = rgba.length > 3 ? rgba[3] : 1;
      const vorn = rgba.slice(0, 3).map((c, i) => c * alpha + hinten[i] * (1 - alpha));
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
      // `hugo --minify` (so deployt deploy.yml) nimmt die Anführungszeichen aus
      // den Attributen: `<meta name=robots content=noindex, nofollow>`. Die
      // Prüfung muss beide Formen kennen – sonst prüft sie eine Fassung, die
      // in Produktion nie ausgeliefert wird.
      expect(text, `${weg} ohne noindex`).toMatch(/name=["']?robots["']?[^>]*noindex/i);
      expect(text, `${weg} ohne Newsletter-Bezug`).toMatch(/newsletter/i);
    }
    // utility-Seiten gehören nicht in die Sitemap
    const sitemap = await (await request.get('/sitemap.xml')).text();
    for (const weg of JOURNEYS) {
      expect(sitemap, `${weg} in der Sitemap`).not.toContain(`>${weg}<`);
    }
  });

  test('Abmeldeseite: Formular oder formloser Weg, kein toter Hinweis', async ({ page }) => {
    await page.goto('/newsletter/abmelden/');
    const text = await page.locator('body').innerText();
    expect(text, 'Seite behauptet, sie könne nicht abmelden').not.toMatch(
      /kann den Klick nicht ausführen/i,
    );
    const form = page.locator('form[action*="abmeldung"]');
    if ((await form.count()) > 0) {
      await expect(form.locator('input[type="email"]')).toHaveCount(1);
      await expect(form.locator('button[type="submit"]')).toBeVisible();
      const aktion = await form.getAttribute('action');
      expect(aktion.startsWith('https://'), `Abmelde-action über http: ${aktion}`).toBe(true);
    } else {
      await expect(page.locator('a[href^="mailto:kontakt@franksfinanzcheck.de"]')).toBeVisible();
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

  test('auf dem Anmeldepfad kommt kein Drittanbieter dazu, und die Adresse bleibt im Haus', async ({
    page,
  }) => {
    // Was hier zählt, ist die Eigenschaft, die der Newsletter wirklich betrifft:
    // Der Anmeldepfad darf KEINEN weiteren Fremdlader mitbringen als die Seiten
    // sonst auch haben (das Analytics-Skript der Site läuft überall – es hier zu
    // verbieten wäre eine Ausgabe über den Newsletter, nicht dafür), und in keiner
    // Anfrage darf die E-Mail-Adresse landen. Der Absende-Pfad selbst ist bewusst
    // nicht Teil dieses Tests: der POST geht an `capture.form_action`, also an den
    // Anbieter, für den die Seite gemacht ist.
    const heimisch = new URL(
      test.info().project.use.baseURL || 'http://127.0.0.1:4173',
    ).host;
    const dieFremden = async (weg) => {
      const treffer = [];
      const lauscher = (anfrage) => {
        const url = new URL(anfrage.url());
        if (url.host !== heimisch) treffer.push(url);
      };
      page.on('request', lauscher);
      await page.goto(weg);
      await page.waitForTimeout(400);
      page.off('request', lauscher);
      return treffer;
    };
    const basis = await dieFremden('/');
    const anmeldung = await dieFremden('/newsletter/');
    const bekannt = new Set(basis.map((u) => u.host));
    const neu = [...new Set(anmeldung.map((u) => u.host))].filter((h) => !bekannt.has(h));
    expect(neu, `neue Fremdlader nur auf der Anmeldeseite: ${neu.join(', ')}`).toEqual([]);
    const personen = anmeldung.filter((u) => /@|%40/i.test(u.search));
    expect(personen, `Adresse in einer Anfrage-URL: ${personen.map((u) => u.href).join(' ')}`).toEqual([]);
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

  test('Versandplan: beide Tage, berechneter Termin, ohne JS kein falsches Datum', async ({
    page,
    browser,
    baseURL,
  }) => {
    await page.goto('/newsletter/');
    test.skip(!(await formularVorhanden(page)), 'kein Formular geschaltet');
    const plan = page.locator('[data-ff-nl-plan]');
    await expect(plan).toHaveCount(1);
    // Beide Versandtage stehen als Kachel – die Namen kommen aus dem Vertrag.
    await expect(plan).toContainText('Dienstag');
    await expect(plan).toContainText('Freitag');
    await expect(plan).toContainText('Wochen-Check');
    await expect(plan).toContainText('Wochen-Abschluss');

    // Der nächste Termin ist gerechnet: kurzes Di/Fr-Datum, in den nächsten 7 Tagen.
    const termine = await plan.locator('[data-ff-nl-termin]').allInnerTexts();
    expect(termine.length).toBe(2);
    const heute = new Date(
      new Intl.DateTimeFormat('en-CA', {
        timeZone: 'Europe/Berlin',
        year: 'numeric', month: '2-digit', day: '2-digit',
      }).format(new Date()),
    );
    for (const text of termine) {
      const m = text.match(/^(Di|Fr), (\d{2})\.(\d{2})\.$/);
      expect(m, `unerwartetes Terminformat: ${text}`).toBeTruthy();
      const jahr = heute.getUTCFullYear();
      let datum = new Date(Date.UTC(jahr, Number(m[3]) - 1, Number(m[2])));
      if (datum < heute) datum = new Date(Date.UTC(jahr + 1, Number(m[3]) - 1, Number(m[2])));
      const wochentag = (datum.getUTCDay() + 6) % 7;
      const passtKuerzel = (m[1] === 'Di' && wochentag === 1) || (m[1] === 'Fr' && wochentag === 4);
      expect(passtKuerzel, `${text} ist kein Versandtag`).toBe(true);
      const tageBis = (datum - heute) / 86400000;
      expect(tageBis, `${text} liegt nicht in den nächsten 7 Tagen`).toBeLessThanOrEqual(7);
    }

    // Ohne JavaScript bleibt der ehrliche Satz ohne Kalenderdatum – kein Termin
    // von gestern, aber auch keine Lücke.
    const ohneJs = await browser.newContext({
      javaScriptEnabled: false,
      viewport: { width: 390, height: 844 },
    });
    try {
      const seite = await ohneJs.newPage();
      await seite.goto(`${baseURL}/newsletter/`);
      const roh = await seite.locator('[data-ff-nl-termin]').allInnerTexts();
      for (const text of roh) {
        expect(text, `ohne JS ein gedruckt aussehendes Datum: ${text}`).toMatch(/der kommende/);
        expect(text).not.toMatch(/\d{2}\.\d{2}\./);
      }
      await expect(seite.locator('[data-ff-nl-erster]')).toContainText(/Dienstag oder Freitag/);
    } finally {
      await ohneJs.close();
    }
  });

  test('Versandplan bleibt in Hell und Dunkel lesbar (gemessen, nicht geschätzt)', async ({
    page,
  }) => {
    await page.goto('/newsletter/');
    test.skip(!(await formularVorhanden(page)), 'kein Formular geschaltet');
    for (const modus of ['light', 'dark']) {
      await page.evaluate((m) => {
        try { localStorage.setItem('theme', m); } catch (e) { /* private Mode */ }
        document.documentElement.setAttribute('data-theme', m);
      }, modus);
      await page.waitForTimeout(120);
      for (const sel of [
        '.ff-nl__plan-kicker', '.ff-nl__plan-erste', '.ff-nl__plan-auftrag',
        '.ff-nl__plan-naechster', '.ff-nl__plan-sicher li', '.ff-nl__button-hinweis',
      ]) {
        const farben = await farbenVon(page, sel);
        expect(farben, `${sel} fehlt im ${modus}-Modus`).not.toBeNull();
        const wert = kontrast(farben.vorn, farben.hinten);
        expect(wert, `${sel} ${modus} nur ${wert.toFixed(2)}:1`).toBeGreaterThanOrEqual(4.5);
      }
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

// Der sichtbare Einstieg muss auch ohne Script und auf schmalen Displays tragen.
for (const breite of [320, 390, 768, 1280]) {
  test(`Blog-Kopf: sichtbarer Anmeldeweg, Kontrast und kein Overflow (${breite}px)`, async ({ page }) => {
    await page.setViewportSize({ width: breite, height: 900 });
    for (const modus of ['light', 'dark']) {
      await page.goto('/');
      await page.evaluate((m) => {
        localStorage.setItem('theme', m);
        document.documentElement.setAttribute('data-theme', m);
      }, modus);
      const box = page.locator('.ff-nl-top');
      await expect(box).toHaveCount(1);
      await expect(page.locator('.newsletter-footer')).toHaveCount(1);
      // Der Streifen trägt das Versandversprechen: die Obergrenze pro Woche und
      // beide Versandtage. Der Wortlaut ist Redaktion und darf sich ändern, das
      // Versprechen nicht – deshalb die Prüfung auf den Gehalt, nicht auf den Satz.
      await expect(box).toContainText(/zwei Mails pro Woche|2× pro Woche/i);
      await expect(box).toContainText('Dienstag & Freitag');
      const cta = box.locator('a');
      const rect = await cta.boundingBox();
      expect(rect.y + rect.height).toBeLessThan(900);
      expect(rect.height).toBeGreaterThanOrEqual(44);
      const position = await page.evaluate(() => ({
        banner: document.querySelector('.ff-nl-top').getBoundingClientRect().bottom,
        main: document.querySelector('main').getBoundingClientRect().top,
        overflow: document.documentElement.scrollWidth > innerWidth,
      }));
      expect(position.banner).toBeLessThanOrEqual(position.main);
      expect(position.overflow).toBe(false);
      for (const sel of ['.ff-nl-top__title', '.ff-nl-top__description', '.ff-nl-top__meta', '.ff-nl-top__cta']) {
        const farben = await farbenVon(page, sel);
        expect(kontrast(farben.vorn, farben.hinten), `${sel} ${modus}`).toBeGreaterThanOrEqual(4.5);
      }
      await cta.focus();
      expect(await cta.evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe('none');
      await cta.press('Enter');
      await expect(page).toHaveURL(/\/newsletter\/#newsletter-anmeldung$/);
      await expect(page.locator('#newsletter-anmeldung')).toBeInViewport();
      await expect(page.locator('.newsletter-footer')).toHaveCount(0);
    }
  });
}

test('Newsletter-Kopf auf Übersicht und Artikel, ohne JavaScript erreichbar', async ({ browser, baseURL }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  try {
    await page.goto(`${baseURL}/posts/`);
    await expect(page.locator('.ff-nl-top')).toHaveCount(1);
    const href = await page.locator('article.post-entry a[href*="/posts/"]').first().getAttribute('href');
    await page.goto(`${baseURL}${new URL(href, baseURL).pathname}`);
    await expect(page.locator('.ff-nl-top')).toHaveCount(1);
    await expect(page.locator('.newsletter-footer')).toHaveCount(1);
    await page.locator('.ff-nl-top__cta').click();
    await expect(page.locator('#newsletter-anmeldung')).toBeInViewport();
  } finally {
    await context.close();
  }
});
