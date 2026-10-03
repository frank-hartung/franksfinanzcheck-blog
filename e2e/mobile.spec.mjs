// ============================================================
//  SPEC: MOBILE (iPhone-14-Emulation)
//  Kein horizontaler Overflow, Bedienbarkeit von Header/Meta,
//  Tap-Ziel-Qualität der Haupt-Buttons.
//  Projekt: nur mobile
// ============================================================

import { test, expect } from './fixtures.mjs';
import { newestArticlePath, scrollThrough } from './helpers.mjs';

// Läuft ausschließlich im Mobile-Projekt
test.describe('Mobile (iPhone 14)', () => {
  test('Startseite: kein horizontaler Overflow', async ({ page }) => {
    await page.goto('/');
    await scrollThrough(page);
    const overflow = await page.evaluate(() => ({
      doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      body: document.body.scrollWidth - document.body.clientWidth,
    }));
    expect(overflow.doc, `document um ${overflow.doc}px zu breit`).toBeLessThanOrEqual(1);
    expect(overflow.body, `body um ${overflow.body}px zu breit`).toBeLessThanOrEqual(1);
  });

  test('Artikel: kein horizontaler Overflow (inkl. Tabellen)', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);
    await scrollThrough(page);
    const overflow = await page.evaluate(() => ({
      doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      body: document.body.scrollWidth - document.body.clientWidth,
    }));
    expect(overflow.doc, `document um ${overflow.doc}px zu breit`).toBeLessThanOrEqual(1);
    expect(overflow.body, `body um ${overflow.body}px zu breit`).toBeLessThanOrEqual(1);
  });

  test('Datenvisualisierung: mobil lesbar, Tabelle erreichbar, kein Seitenüberlauf', async ({ page }) => {
    await page.goto('/posts/2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich/');
    const chart = page.locator('[data-ff-chart]').first();
    await expect(chart).toBeVisible();
    const overflow = await page.evaluate(() => ({
      doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      body: document.body.scrollWidth - document.body.clientWidth,
    }));
    expect(overflow.doc).toBeLessThanOrEqual(1);
    expect(overflow.body).toBeLessThanOrEqual(1);
    await chart.locator('details summary').click();
    await expect(chart.locator('table')).toBeVisible();
    await expect(chart.locator('.ff-chart__table-scroll')).toHaveCSS('overflow-x', 'auto');
  });

  test('Header: Logo sichtbar, Navigation nutzbar', async ({ page }) => {
    await page.goto('/');
    const logo = page.locator('header.header a.ff-brand img');
    await expect(logo.first()).toBeVisible();
    expect(
      await logo.first().evaluate((el) => el.complete && el.naturalWidth > 0),
      'Logo-Bild geladen'
    ).toBe(true);

    // Navigation muss auf Mobile erreichbar sein: entweder direkt sichtbar
    // oder per Toggle. Beides fehlend = Sackgasse für Mobile-Nutzer.
    const nav = page.locator('header.header nav, header.header .header-nav');
    expect(await nav.count(), 'Header-Navigation im DOM').toBeGreaterThan(0);
    const navVisible = await nav.first().isVisible().catch(() => false);
    const toggle = page.locator('header.header button[aria-expanded], header.header .menu-toggle');
    const toggleCount = await toggle.count();
    expect(
      navVisible || toggleCount > 0,
      'Navigation sichtbar ODER Toggle vorhanden'
    ).toBe(true);
  });

  test('Kern-Tap-Ziele: sichtbar und >= 40px hoch (Thumb-Greifbarkeit)', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);

    const slot = page.locator('.ff-voice-slot');
    if ((await slot.count()) > 0) {
      const buttons = slot.first().locator('button:visible');
      const count = await buttons.count();
      for (let i = 0; i < count; i++) {
        const box = await buttons.nth(i).boundingBox();
        if (box) {
          // 40 px statt 44: bewusster Spielraum für Text-Buttons mit Padding
          expect(
            box.height,
            `Toolbar-Button ${i + 1} nur ${Math.round(box.height)}px hoch`
          ).toBeGreaterThanOrEqual(40);
        }
      }
    }
  });

  // ============================================================
  //  HERAUSGEBER-PILL (mobil) – Regressionswächter (27.09.2026)
  //  ------------------------------------------------------------
  //  Mobile-Schwester des Desktop-Tests in home.spec.mjs: Auf dem
  //  Handy bricht die Trust-Reihe horizontal um (kein Fakten-Panel),
  //  die zweizeilige Herausgeber-Angabe muss hier trotzdem strikt
  //  Struktur bleiben (Label ÜBER Autor) und vollständig in der
  //  Hero-Box liegen. Die tote-<br>-Bugklasse (Live-Befund 27.09.)
  //  wäre mobil genauso unauffällig kaputt gegangen.
  //  ============================================================
  test('Startseite: Kostenprofil mit Autor bleibt innerhalb der Markenbühne', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => document.fonts.ready);

    const geo = await page.evaluate(() => {
      const profil = document.querySelector('.ff-kostenprofil--home');
      const box = document.querySelector('.first-entry.home-info');
      const author = profil?.querySelector('.ff-kostenprofil__author');
      const label = author?.querySelector('small');
      const name = author?.querySelector('strong');
      if (!profil || !box || !author || !label || !name) return { fehlt: true };

      const p = profil.getBoundingClientRect();
      const b = box.getBoundingClientRect();
      const l = label.getBoundingClientRect();
      const n = name.getBoundingClientRect();
      const a = author.getBoundingClientRect();
      return {
        fehlt: false,
        zweiZeilen: n.top >= l.bottom - 2,
        abstand: +(n.top - l.bottom).toFixed(1),
        profilInBox: p.right <= b.right + 1 && p.left >= b.left - 1,
        innerlichSauber: profil.scrollWidth <= profil.clientWidth + 1,
        autorVerlinkt: author instanceof HTMLAnchorElement && /\/ueber\/?$/.test(author.pathname),
        autorHoehe: +a.height.toFixed(1),
      };
    });

    expect(geo.fehlt, 'Kostenprofil mit Autorenstruktur im Markup').toBe(false);
    expect(geo.zweiZeilen, `Autorenname muss unter dem Label stehen, Abstand war ${geo.abstand}px`).toBe(true);
    expect(geo.autorVerlinkt, 'Autoren-Entity bleibt auf /ueber/ verlinkt (E-E-A-T)').toBe(true);
    expect(geo.profilInBox, 'Kostenprofil muss innerhalb der Markenbühne liegen').toBe(true);
    expect(geo.innerlichSauber, 'Kostenprofil darf intern nicht horizontal überlaufen').toBe(true);
    expect(geo.autorHoehe, 'Autorenlink bleibt Thumb-gerecht hoch').toBeGreaterThanOrEqual(44);
  });
  // ============================================================
  //  SPAR-MATRIX MOBIL (Frank-Befund 30.09.2026)
  //  Fuenf Spalten passen in kein 390-px-Fenster. Unter 760 px
  //  stapelt die Matrix deshalb zu sechs Karten: Themenname als
  //  Kartenkopf, Feldname aus data-label, Knopf auf voller Breite.
  //  Ein zweites Markup gibt es bewusst NICHT (sonst zaehlte die
  //  Werbe-Offenlegung jeden Partnerlink doppelt) – die Karten
  //  entstehen rein aus CSS.
  // ============================================================
  test('Spar-Matrix: stapelt zu Karten statt quer zu scrollen', async ({ page }) => {
    await page.goto('/pillar/');
    const tabelle = page.locator('table.ff-spar-matrix-table');
    await expect(tabelle).toBeVisible();

    const befund = await page.evaluate(() => {
      const tab = document.querySelector('table.ff-spar-matrix-table');
      const wrap = document.querySelector('.ff-spar-matrix-scroll');
      const zeile = tab.querySelector('tbody tr');
      const zelle = zeile.querySelector('td[data-label]');
      const knopf = zeile.querySelector('.ff-table-btn');
      const label = getComputedStyle(zelle, '::before').content;
      return {
        zeileGestapelt: getComputedStyle(zeile).display === 'block',
        kopfVersteckt: getComputedStyle(tab.querySelector('thead')).position === 'absolute',
        labelSichtbar: label && label !== 'none' && label.includes(zelle.dataset.label),
        querScroll: wrap.scrollWidth - wrap.clientWidth,
        knopfBreite: knopf.getBoundingClientRect().width,
        kartenBreite: zeile.getBoundingClientRect().width,
        knopfHoehe: knopf.getBoundingClientRect().height,
        karten: tab.querySelectorAll('tbody tr').length,
      };
    });

    expect(befund.zeileGestapelt, 'jede Zeile wird zur Karte').toBe(true);
    expect(befund.kopfVersteckt, 'Spaltenkopf wandert in die Feldnamen').toBe(true);
    expect(befund.labelSichtbar, 'Feldname steht als Label in der Karte').toBe(true);
    expect(befund.querScroll, 'kein horizontales Scrollen mehr noetig').toBeLessThanOrEqual(1);
    expect(befund.karten, 'sechs Themenkarten').toBe(6);
    expect(befund.knopfHoehe, 'Tap-Ziel >= 44px').toBeGreaterThanOrEqual(44);
    expect(befund.knopfBreite, 'Knopf nutzt die Kartenbreite')
      .toBeGreaterThan(befund.kartenBreite * 0.7);

    const overflow = await page.evaluate(() => (
      document.documentElement.scrollWidth - document.documentElement.clientWidth
    ));
    expect(overflow, `document um ${overflow}px zu breit`).toBeLessThanOrEqual(1);
  });

  // ============================================================
  //  FIXKOSTEN-COCKPIT MOBIL (Premium-Nachtrag 01.10.2026, #507)
  //  Der Produktkern bringt ein Sechs-Zeilen-Grid mit Betrags-,
  //  Datumsfeldern und Ratgeber-Handoffs mit. Beim Merge von #507
  //  konnte der Browserlauf in der Sandbox nicht starten – die
  //  Ratgeber-Links fielen mobil auf 30px Tap-Höhe, ohne dass es
  //  ein Test bemerkte. Dieser Wächter hält die Seite auf dem
  //  Haus-Standard: kein Overflow, alle Ziele thumb-gerecht.
  // ============================================================
  test('Fixkosten-Cockpit: kein Overflow, alle Ziele thumb-gerecht', async ({ page }) => {
    await page.goto('/cockpit/');
    await scrollThrough(page);
    const overflow = await page.evaluate(() => ({
      doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      body: document.body.scrollWidth - document.body.clientWidth,
    }));
    expect(overflow.doc, `document um ${overflow.doc}px zu breit`).toBeLessThanOrEqual(1);
    expect(overflow.body, `body um ${overflow.body}px zu breit`).toBeLessThanOrEqual(1);

    const befund = await page.evaluate(() => {
      const zuKlein = [];
      document.querySelectorAll('.ff-cockpit input, .ff-cockpit button, .ff-cockpit a').forEach((el) => {
        // Die Opt-in-Checkbox hat ihre eigene Schwelle (24px, WCAG 2.5.8):
        // Ihr volles Label ist das klickbare Ziel, 40px Kästchen wären
        // optisch fremd. Alle anderen Ziele folgen dem 40px-Haus-Standard.
        if (el.matches('[data-ff-cockpit-remember]')) return;
        const r = el.getBoundingClientRect();
        if (r.height > 0 && r.height < 40) {
          zuKlein.push(`${el.tagName.toLowerCase()}${el.className ? '.' + String(el.className).split(' ')[0] : ''}=${Math.round(r.height)}px`);
        }
      });
      return {
        zuKlein,
        knobHoehen: [...document.querySelectorAll('.ff-cockpit__submit, .ff-cockpit__reset')].map(
          (el) => Math.round(el.getBoundingClientRect().height)
        ),
        checkbox: Math.round(document.querySelector('[data-ff-cockpit-remember]').getBoundingClientRect().height),
      };
    });

    expect(befund.zuKlein, 'kein Cockpit-Ziel unter 40px Tap-Höhe').toEqual([]);
    // Primäre Handlungen des Produktkerns: volle 44px (Haus-Standard,
    // gleiche Schwelle wie der Spar-Matrix-Knopf oben).
    for (const hoehe of befund.knobHoehen) {
      expect(hoehe, '„Mein Prüfplan“-/„Zurücksetzen“-Knopf >= 44px').toBeGreaterThanOrEqual(44);
    }
    // Opt-in-Checkbox: WCAG 2.5.8 verlangt mindestens 24px Zielfläche.
    expect(befund.checkbox, 'Opt-in-Checkbox >= 24px').toBeGreaterThanOrEqual(24);
  });

  // ============================================================
  //  WERKZEUGE (02.10.2026)
  //  Die eigenständigen Rechner sind ein Produkt für unterwegs:
  //  Wer mit dem Handy vor dem Vertrag steht, muss tippen können,
  //  ohne zu zoomen oder quer zu scrollen.
  // ============================================================
  test('Werkzeuge: Hub und Rechner ohne Overflow, Ziele thumb-gerecht', async ({ page }) => {
    for (const pfad of ['/werkzeuge/', '/werkzeuge/effektivpreis-rechner/']) {
      await page.goto(pfad);
      await scrollThrough(page);
      const overflow = await page.evaluate(() => ({
        doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        body: document.body.scrollWidth - document.body.clientWidth,
      }));
      expect(overflow.doc, `${pfad}: document um ${overflow.doc}px zu breit`).toBeLessThanOrEqual(1);
      expect(overflow.body, `${pfad}: body um ${overflow.body}px zu breit`).toBeLessThanOrEqual(1);
    }

    const befund = await page.evaluate(() => {
      const zuKlein = [];
      document.querySelectorAll('[data-ff-werkzeug] input, [data-ff-werkzeug] select, [data-ff-werkzeug] button, [data-ff-werkzeug] a').forEach((el) => {
        // Opt-in-Checkbox: eigene Schwelle nach WCAG 2.5.8 (24px),
        // ihr Label ist das eigentliche Ziel – wie im Cockpit.
        if (el.matches('[data-ff-wz-speichern]')) return;
        const r = el.getBoundingClientRect();
        if (r.height > 0 && r.height < 40) {
          zuKlein.push(`${el.tagName.toLowerCase()}=${Math.round(r.height)}px`);
        }
      });
      const knopf = document.querySelector('[data-ff-werkzeug] button[type="submit"]');
      return {
        zuKlein,
        knopf: knopf ? Math.round(knopf.getBoundingClientRect().height) : 0,
        checkbox: Math.round(document.querySelector('[data-ff-wz-speichern]').getBoundingClientRect().height),
      };
    });

    expect(befund.zuKlein, 'kein Werkzeug-Ziel unter 40px Tap-Höhe').toEqual([]);
    expect(befund.knopf, '„Berechnen“-Knopf >= 44px').toBeGreaterThanOrEqual(44);
    expect(befund.checkbox, 'Opt-in-Checkbox >= 24px').toBeGreaterThanOrEqual(24);
  });
});
