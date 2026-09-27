// ============================================================
//  SPEC: STARTSEITE – Rendering, Teaser, Fehlerfreiheit, Bilder
//  Projekt: desktop + mobile
// ============================================================

import { test, expect } from './fixtures.mjs';
import { watchErrors, assertNoErrors, scrollThrough, waitForImages } from './helpers.mjs';

test.describe('Startseite', () => {
  test('rendert Kernstruktur: Titel, genau ein H1, Teaser, Footer-Rechtliches', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/FranksFinanzcheck/);

    const h1 = page.locator('h1');
    expect(await h1.count(), 'Startseite: genau ein H1').toBe(1);
    expect((await h1.first().textContent()).trim().length).toBeGreaterThan(10);

    // Teaser: Pager zeigt 8 Beiträge pro Seite – mindestens 6 erwartet
    const teasers = page.locator('article.post-entry');
    expect(await teasers.count(), 'Startseite: Artikel-Teaser sichtbar').toBeGreaterThanOrEqual(6);

    // Pflicht-Verlinkung (DSGVO-Üblichkeit): Impressum + Datenschutz erreichbar
    const impressum = page.locator('a[href*="/impressum"]');
    const datenschutz = page.locator('a[href*="/datenschutz"]');
    expect(await impressum.count(), 'Impressum-Link vorhanden').toBeGreaterThan(0);
    expect(await datenschutz.count(), 'Datenschutz-Link vorhanden').toBeGreaterThan(0);
  });

  test('lädt ohne JS-Fehler und ohne defekte Same-Origin-Anfragen', async ({ page }) => {
    const errors = watchErrors(page);
    const failedRequests = [];
    const externalFailures = [];
    const isLocal = (url) => /127\.0\.0\.1|localhost/.test(url);

    page.on('requestfailed', (req) => {
      const failure = req.failure()?.errorText || '';
      const entry = `${req.url()} (${failure})`;
      if (isLocal(req.url())) {
        if (!failure.includes('ERR_ABORTED')) failedRequests.push(entry);
      } else {
        externalFailures.push(entry);
      }
    });
    page.on('response', (res) => {
      if (res.status() >= 400 && isLocal(res.url())) {
        failedRequests.push(`${res.status()} ${res.url()}`);
      }
    });

    await page.goto('/', { waitUntil: 'load' });
    await scrollThrough(page);
    await waitForImages(page);
    await page.waitForLoadState('networkidle');

    assertNoErrors(errors, 'Startseite');
    expect(
      failedRequests,
      'Startseite: keine 4xx/5xx-Antworten und keine fehlgeschlagenen Anfragen'
    ).toEqual([]);
    if (externalFailures.length) {
      console.log(`ℹ Startseite: ${externalFailures.length} ignorierte Drittanbieter-Anfragen`);
    }
  });

  test('alle Bilder laden vollständig und tragen alt-Texte', async ({ page }) => {
    await page.goto('/', { waitUntil: 'load' });
    await scrollThrough(page);
    await waitForImages(page);

    const imgs = page.locator('img');
    const count = await imgs.count();
    expect(count, 'Startseite: Bilder vorhanden').toBeGreaterThan(3);

    const probleme = [];
    for (let i = 0; i < count; i++) {
      const img = imgs.nth(i);
      const src = await img.evaluate((el) => el.currentSrc || el.src);
      const ok = await img.evaluate((el) => el.complete && el.naturalWidth > 0);
      if (!ok) probleme.push(`nicht geladen: ${src}`);
      // Deko-Bilder (Logo, alt="") sind erlaubt – Inhaltsbilder brauchen alt
      const alt = await img.getAttribute('alt');
      const istDeko = (await img.getAttribute('aria-hidden')) === 'true' || (await img.evaluate((el) => el.closest('[aria-hidden="true"]') !== null));
      if ((alt === null || alt.trim() === '') && !istDeko) {
        probleme.push(`ohne alt-Text: ${src}`);
      }
    }
    expect(probleme, 'Startseite: Bilder geladen & barrierefrei').toEqual([]);
  });

  // ============================================================
  //  HERAUSGEBER-PILL – Regressionswächter (27.09.2026)
  //  ------------------------------------------------------------
  //  Anlass: „Herausgegeben von Frank Hartung ragte über die innere
  //  Box im Willkommenstext“ (Live-Befund 27.09.2026). Zwei Ursachen:
  //  ein <br> erzeugt in einem Flex-Item KEINEN Umbruch (wird selbst
  //  nullbreites Flex-Item), und white-space:nowrap verbot jeden
  //  Textumbruch → eine unumbrechbare Zeile, breiter als das Fakten-
  //  Panel der Hero-Variante. Repariert durch Struktur: Label und
  //  Autoren-Link als Flex-Spalte (.ff-trust-editorial).
  //  Dieser Test hält BEIDE Eigenschaften fest – die zweizeilige
  //  Verantwortungsangabe (fängt die tote-<br>-Bugklasse) und die
  //  geometrische Enthaltsamkeit in Panel und Hero (fängt die
  //  Overflow-Bugklasse). Läuft in beiden Projekten (Desktop-Panel
  //  und Mobile-Wrap-Reihe).
  //  ============================================================
  test('Herausgeber-Pill: zweizeilig und vollständig innerhalb der inneren Box', async ({ page }) => {
    await page.goto('/', { waitUntil: 'load' });
    // Fonts einbeziehen, damit Zeilen-/Breitenmessung nicht am
    // Fallback-Font vorbeigeht (font-display:optional → ready abwarten).
    await page.evaluate(() => document.fonts.ready);

    const pill = page.locator('.ff-trust-pill--editorial');
    await expect(pill, 'Herausgeber-Pill existiert').toHaveCount(1);

    const geo = await page.evaluate(() => {
      const pill = document.querySelector('.ff-trust-pill--editorial');
      const row = document.querySelector('.ff-trust-row');
      const box = document.querySelector('.first-entry.home-info');
      const label = pill?.querySelector('.ff-trust-editorial-label');
      const author = pill?.querySelector('.ff-trust-author');
      if (!pill || !row || !box || !label || !author) return { fehlt: true };

      const p = pill.getBoundingClientRect();
      const r = row.getBoundingClientRect();
      const b = box.getBoundingClientRect();
      const l = label.getBoundingClientRect();
      const a = author.getBoundingClientRect();

      // Jede einzelne Pill muss in Reihe UND Hero-Box enthalten sein und
      // darf intern nichts überlaufen lassen (scrollWidth-Schuld).
      const pills = [...document.querySelectorAll('.ff-trust-row .ff-trust-pill')].map((el) => {
        const q = el.getBoundingClientRect();
        return {
          txt: el.textContent.replace(/\s+/g, ' ').trim(),
          inRow: q.right <= r.right + 1 && q.left >= r.left - 1,
          inBox: q.right <= b.right + 1 && q.left >= b.left - 1,
          innerlichSauber: el.scrollWidth <= el.clientWidth + 1,
        };
      });

      return {
        fehlt: false,
        // Kern-Struktur: Autor-Link liegt UNTER dem Label (2. Zeile),
        // nicht daneben. Toleranz 2px deckt Subpixel/Zeilenhöhen-Rundung.
        zweiZeilen: a.top >= l.bottom - 2,
        abstand: +(a.top - l.bottom).toFixed(1),
        pillInRow: p.right <= r.right + 1 && p.left >= r.left - 1,
        pillInBox: p.right <= b.right + 1 && p.left >= b.left - 1,
        pillUeberPanel: +(p.right - r.right).toFixed(1),
        autorVerlinkt: author instanceof HTMLAnchorElement && /\/ueber\/?$/.test(author.pathname),
        docOverflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        pills,
      };
    });

    expect(geo.fehlt, 'Editorial-Struktur (Label + Autor) im Markup').toBe(false);
    expect(geo.zweiZeilen, `Autoren-Name muss UNTER dem Label stehen (2. Zeile), Abstand war ${geo.abstand}px`).toBe(true);
    expect(geo.autorVerlinkt, 'Autoren-Entity bleibt auf /ueber/ verlinkt (E-E-A-T)').toBe(true);
    expect(geo.pillInRow, `Herausgeber-Pill muss innerhalb der Trust-Reihe enden (Übertretung: ${geo.pillUeberPanel}px)`).toBe(true);
    expect(geo.pillInBox, 'Herausgeber-Pill muss innerhalb des Hero-Willkommenstextes liegen').toBe(true);
    expect(geo.docOverflowX, 'Startseite darf keinen horizontalen Dokument-Overflow haben').toBeLessThanOrEqual(1);

    const verletzt = (geo.pills || []).filter((q) => !q.inRow || !q.inBox || !q.innerlichSauber);
    expect(verletzt, 'Keine Trust-Pill ragt aus Reihe/Hero oder überläuft intern').toEqual([]);
  });
});
