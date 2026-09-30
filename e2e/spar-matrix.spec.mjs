// ============================================================
//  SPEC: SPAR-MATRIX (/pillar/) – LESBARKEIT DER TABELLE
//  ------------------------------------------------------------
//  Anlass (Frank-Befund 30.09.2026): Die Matrix stand ausserhalb
//  von `.post-content`; das Premium-Tabellen-System war komplett
//  dorthin gescopt, die einzige eigene Regel zeigte auf einen
//  nicht mehr existierenden Klassennamen. Live blieb der
//  PaperMod-Reset uebrig: `table{display:block}`, kein
//  Zellpolster, kein Kopfkontrast – fuenf Spalten als Textband.
//
//  `scripts/tabellen_lesbarkeit_guard.py` beweist die Lieferung
//  statisch (Klassen, Scope, Floor, Markup-Vertrag). Was es nicht
//  sehen kann, ist der Browser: ob nach Kaskade und Minifizierung
//  wirklich eine Tabelle mit Polster, Kopf-Flaeche und
//  Zeilentrennern auf dem Schirm steht. Genau das steht hier.
//  Projekt: desktop (die mobile Kartenansicht prueft mobile.spec.mjs)
// ============================================================

import { test, expect } from './fixtures.mjs';

const px = (wert) => Number.parseFloat(wert) || 0;

test.describe('Spar-Matrix (/pillar/)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/pillar/');
  });

  test('ist eine echte Tabelle – nicht der display:block-Reset', async ({ page }) => {
    const table = page.locator('table.ff-spar-matrix-table');
    await expect(table).toBeVisible();
    await expect(table).toHaveCSS('display', 'table');

    const zeilen = await table.locator('tbody tr').count();
    expect(zeilen, 'sechs Themenwelten in der Matrix').toBe(6);

    // Kopfzellen semantisch ausgezeichnet (scope) + Spaltenmass via colgroup
    expect(await table.locator('thead th[scope="col"]').count()).toBe(5);
    expect(await table.locator('colgroup col').count()).toBe(5);
    expect(await table.locator('tbody th[scope="row"]').count()).toBe(6);
  });

  test('Zellen atmen: Polster, Zeilentrenner, ruhige Zahlen', async ({ page }) => {
    const zelle = page.locator('table.ff-spar-matrix-table tbody td').first();
    const stil = await zelle.evaluate((el) => {
      const s = getComputedStyle(el);
      return {
        oben: s.paddingTop, unten: s.paddingBottom,
        links: s.paddingLeft, rechts: s.paddingRight,
        trenner: s.borderBottomWidth, trennerFarbe: s.borderBottomColor,
        ziffern: s.fontVariantNumeric,
      };
    });
    expect(px(stil.oben), 'Zellpolster oben >= 10px').toBeGreaterThanOrEqual(10);
    expect(px(stil.unten), 'Zellpolster unten >= 10px').toBeGreaterThanOrEqual(10);
    expect(px(stil.links), 'Zellpolster links >= 12px').toBeGreaterThanOrEqual(12);
    expect(px(stil.rechts), 'Zellpolster rechts >= 12px').toBeGreaterThanOrEqual(12);
    expect(px(stil.trenner), 'sichtbarer Zeilentrenner').toBeGreaterThan(0);
    expect(stil.trennerFarbe).not.toBe('rgba(0, 0, 0, 0)');
    expect(stil.ziffern, 'Geldspalte mit tabellarischen Ziffern').toContain('tabular-nums');
  });

  test('Kopfzeile traegt die Marke und bleibt beim Scrollen stehen', async ({ page }) => {
    const kopf = page.locator('table.ff-spar-matrix-table thead th').first();
    const stil = await kopf.evaluate((el) => {
      const s = getComputedStyle(el);
      return { bg: s.backgroundColor, farbe: s.color, position: s.position, gewicht: s.fontWeight };
    });
    expect(stil.bg, 'Kopfzeile mit eigener Flaeche').not.toBe('rgba(0, 0, 0, 0)');
    expect(stil.position, 'Sticky-Kopf').toBe('sticky');
    expect(Number(stil.gewicht)).toBeGreaterThanOrEqual(700);

    // Kontrast Kopftext gegen Kopfflaeche (WCAG AA fuer Fliesstext)
    const kontrast = await kopf.evaluate((el) => {
      const s = getComputedStyle(el);
      const lum = (farbe) => {
        const [r, g, b] = farbe.match(/\d+(\.\d+)?/g).slice(0, 3).map(Number);
        const k = [r, g, b].map((v) => {
          const c = v / 255;
          return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
        });
        return 0.2126 * k[0] + 0.7152 * k[1] + 0.0722 * k[2];
      };
      const a = lum(s.color);
      const b = lum(s.backgroundColor);
      return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    });
    expect(kontrast, 'Kopfzeilen-Kontrast >= 4.5:1').toBeGreaterThanOrEqual(4.5);
  });

  test('Aktionsspalte: sechs Knoepfe mit echtem Tap-Ziel', async ({ page }) => {
    const knoepfe = page.locator('table.ff-spar-matrix-table .ff-table-btn');
    await expect(knoepfe).toHaveCount(6);
    for (let i = 0; i < 6; i += 1) {
      const box = await knoepfe.nth(i).boundingBox();
      expect(box.height, `Knopf ${i + 1} mindestens 44px hoch`).toBeGreaterThanOrEqual(44);
    }
  });

  test('kein Seitenueberlauf durch die Matrix', async ({ page }) => {
    const overflow = await page.evaluate(() => ({
      doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      body: document.body.scrollWidth - document.body.clientWidth,
    }));
    expect(overflow.doc, `document um ${overflow.doc}px zu breit`).toBeLessThanOrEqual(1);
    expect(overflow.body, `body um ${overflow.body}px zu breit`).toBeLessThanOrEqual(1);
  });
});
