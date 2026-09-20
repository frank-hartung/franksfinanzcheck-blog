// ============================================================
//  SPEC: SAISONALE STARTSEITE – Hero-Badge, Saison-Hinweis,
//        „Saison-Fokus"-Block (data/saisons.yaml)
//  ------------------------------------------------------------
//  Rollout 20.09.2026. Läuft im Desktop-Projekt und emuliert für
//  die LCP-/Overflow-Prüfungen zusätzlich 390×844 (Mobile).
//
//  Was hier bewusst NICHT steht: die Auswahl-Logik (Relevanz über
//  `keywords`, Fallback-Stufen) und die analytische WCAG-Prüfung der
//  YAML-Farben – das macht scripts/saisonale_startseite_guard.py
//  (deterministisch, ohne Browser). Diese Spec beweist die andere
//  Hälfte: was der BROWSER wirklich sieht (gerenderte Kontraste,
//  Geometrie, erreichbare Links, Messkette, Mobile-Reihenfolge).
//
//  Zeit-Toleranz: Hugo baut mit der Uhr der Build-Maschine (CI: UTC),
//  die Tests laufen in Europe/Berlin (playwright.config.mjs). Am
//  Saison-Grenztag können beide Tage auseinanderliegen – deshalb wird
//  die Saison aus einem Toleranzfenster (gestern/heute/morgen)
//  akzeptiert statt auf ein Datum festgenagelt. Kein Flaky-Test für
//  ein Vierteljahr im Voraus.
// ============================================================

import { readFileSync } from 'node:fs';
import { test, expect } from './fixtures.mjs';
import { scrollThrough } from './helpers.mjs';

const SAISON_IDS = ['herbst', 'winter', 'fruehling', 'sommer'];

/** data/saisons.yaml minimal auswerten (id, ab, bis, min_artikel). */
function saisonsAusDatei() {
  const pfad = new URL('../data/saisons.yaml', import.meta.url);
  const text = readFileSync(pfad, 'utf8');
  const saisons = [];
  let aktuell = null;
  for (const rohZeile of text.split('\n')) {
    const zeile = rohZeile.replace(/#.*$/, '');
    let m = zeile.match(/^\s*-\s+id:\s*"?([a-z]+)"?\s*$/);
    if (m) {
      aktuell = { id: m[1], ab: null, bis: null, min_artikel: 3 };
      saisons.push(aktuell);
      continue;
    }
    if (!aktuell) continue;
    m = zeile.match(/^\s*(ab|bis):\s*"?(\d{2}-\d{2})"?\s*$/);
    if (m) { aktuell[m[1]] = m[2]; continue; }
    m = zeile.match(/^\s*min_artikel:\s*(\d+)\s*$/);
    if (m) { aktuell.min_artikel = Number(m[1]); }
  }
  return saisons;
}

function saisonFuer(datum, saisons) {
  const md = datum.getMonth() * 100 + datum.getDate() + 100; // (Monat+1)*100+Tag
  for (const s of saisons) {
    if (!s.ab || !s.bis) continue;
    const [abM, abT] = s.ab.split('-').map(Number);
    const [bisM, bisT] = s.bis.split('-').map(Number);
    const ab = abM * 100 + abT;
    const bis = bisM * 100 + bisT;
    const treffer = bis >= ab ? (md >= ab && md <= bis) : (md >= ab || md <= bis);
    if (treffer) return s;
  }
  return null;
}

function tolerierteSaisons() {
  const saisons = saisonsAusDatei();
  const heute = new Date();
  const ids = new Set();
  for (const versatz of [-1, 0, 1]) {
    const tag = new Date(heute);
    tag.setDate(tag.getDate() + versatz);
    const s = saisonFuer(tag, saisons);
    if (s) ids.add(s.id);
  }
  return { saisons, ids: [...ids], erwartet: saisonFuer(heute, saisons) };
}

// Kontrast-Messung im gerenderten Zustand – gleiche Formel wie
// e2e/design-metrics.mjs (WCAG 2.x, effektive Hintergrundfarbe durch
// Aufwärts-Suche nach einer deckenden Fläche).
const KONTRAST_QUELLE = `
var lum = function (r, g, b) {
  var f = function (c) { c /= 255; return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4); };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
};
var parse = function (c) {
  var m = c.match(/rgba?\\((\\d+)[,\\s]+(\\d+)[,\\s]+(\\d+)(?:[,/\\s]+([\\d.]+))?\\)/);
  if (!m) return null;
  return { r: +m[1], g: +m[2], b: +m[3], a: m[4] === undefined ? 1 : +m[4] };
};
var blend = function (fg, bg) {
  return { r: fg.r * fg.a + bg.r * (1 - fg.a), g: fg.g * fg.a + bg.g * (1 - fg.a), b: fg.b * fg.a + bg.b * (1 - fg.a) };
};
var ratio = function (l1, l2) { var a = Math.max(l1, l2), b = Math.min(l1, l2); return (a + 0.05) / (b + 0.05); };
var effBg = function (el) {
  var node = el;
  while (node && node !== document.documentElement) {
    var bg = parse(window.getComputedStyle(node).backgroundColor);
    if (bg && bg.a > 0.85) return bg;
    node = node.parentElement;
  }
  var rootBg = parse(window.getComputedStyle(document.documentElement).backgroundColor);
  return rootBg && rootBg.a > 0 ? rootBg : { r: 255, g: 255, b: 255, a: 1 };
};
var contrastOf = function (sel) {
  var el = document.querySelector(sel);
  if (!el) return null;
  var fg = parse(window.getComputedStyle(el).color);
  if (!fg) return null;
  var bg = effBg(el);
  var f = blend(fg, bg);
  return Math.round(ratio(lum(f.r, f.g, f.b), lum(bg.r, bg.g, bg.b)) * 100) / 100;
};
return {
  badge: contrastOf('.ff-saison-badge'),
  hinweis: contrastOf('.ff-saison-hinweis'),
  eyebrow: contrastOf('.ff-saison-eyebrow'),
  ueberschrift: contrastOf('.ff-saison-head h2'),
  kartentitel: contrastOf('.ff-saison-card-titel'),
  kartenCta: contrastOf('.ff-saison-card-cta'),
  kartenMeta: contrastOf('.ff-saison-card-meta'),
  ratgeberLink: contrastOf('.ff-saison-pillar'),
  tipp: contrastOf('.ff-saison-tipp'),
  tippLabel: contrastOf('.ff-saison-tipp-label'),
};
`;

const TEXT_MINDEST_KONTRAST = 4.5;

test.describe('Saisonale Startseite', () => {
  test('Hero: Saison-Badge über dem H1, Saison-Hinweis darunter, beides kohärent zum Block', async ({ page }) => {
    await page.goto('/');
    const { ids } = tolerierteSaisons();

    const badge = page.locator('article.first-entry.home-info .ff-saison-badge');
    await expect(badge, 'Saison-Badge fehlt im Hero').toHaveCount(1);
    const hinweis = page.locator('article.first-entry.home-info .ff-saison-hinweis');
    await expect(hinweis, 'Saison-Hinweis fehlt im Hero').toHaveCount(1);

    // Badge VOR dem H1 (Eyebrow-Position), Hinweis NACH dem Willkommenstext
    const reihenfolge = await page.evaluate(() => {
      const hero = document.querySelector('article.first-entry.home-info');
      return [...hero.querySelectorAll('.ff-saison-badge, h1, .entry-content, .ff-saison-hinweis')]
        .map((el) => (el.classList.contains('ff-saison-badge') ? 'badge'
          : el.tagName === 'H1' ? 'h1'
          : el.classList.contains('entry-content') ? 'text' : 'hinweis'));
    });
    expect(reihenfolge, 'Hero-Reihenfolge: Badge → H1 → Willkommenstext → Hinweis')
      .toEqual(['badge', 'h1', 'text', 'hinweis']);

    const badgeSaison = await badge.getAttribute('data-ff-saison');
    expect(SAISON_IDS, `Saison ${badgeSaison} ist keine bekannte Saison`).toContain(badgeSaison);
    expect(ids, `Badge zeigt ${badgeSaison}, erwartet am Stichtag eine von ${ids.join('/')}`)
      .toContain(badgeSaison);

    const block = page.locator('section.ff-saison');
    await expect(block, 'genau ein Saison-Fokus-Block').toHaveCount(1);
    expect(await block.getAttribute('data-ff-saison'), 'Block und Badge zeigen verschiedene Saisons')
      .toBe(badgeSaison);
    expect(await hinweis.getAttribute('data-ff-saison')).toBe(badgeSaison);

    await expect(page.locator('#saison-fokus'), 'Block braucht die Anker-Überschrift #saison-fokus')
      .toHaveCount(1);
    expect((await badge.innerText()).trim().length, 'Badge-Text ist leer').toBeGreaterThan(8);
    expect((await hinweis.innerText()).trim().length, 'Hinweis-Text ist leer').toBeGreaterThan(40);
  });

  test('Saison-Fokus: genug Karten, alle Ziele erreichbar, Messkette vollständig', async ({ page }) => {
    await page.goto('/');
    const { erwartet } = tolerierteSaisons();
    const block = page.locator('section.ff-saison');
    const saison = await block.getAttribute('data-ff-saison');
    const minKarten = (erwartet && erwartet.id === saison) ? erwartet.min_artikel : 3;

    const karten = page.locator('a.ff-saison-card');
    const anzahl = await karten.count();
    expect(anzahl, `Saison-Block zeigt ${anzahl} Karten, min_artikel verlangt ${minKarten}`)
      .toBeGreaterThanOrEqual(minKarten);

    // Auswahl-Quelle muss dokumentiert sein (keywords = Stufe 1, pillar/neueste = Fallback)
    const quelle = await block.getAttribute('data-ff-saison-quelle');
    expect(['keywords', 'pillar', 'neueste'], `unbekannte Auswahl-Quelle ${quelle}`).toContain(quelle);

    for (let i = 0; i < anzahl; i++) {
      const karte = karten.nth(i);
      const href = await karte.getAttribute('href');
      expect(href, `Karte ${i + 1} ohne Ziel`).toBeTruthy();
      const antwort = await page.request.get(href);
      expect(antwort.status(), `Karte ${i + 1} (${href}) nicht erreichbar`).toBe(200);

      const titel = (await karte.locator('.ff-saison-card-titel').innerText()).trim();
      expect(titel.length, `Karte ${i + 1} ohne Titel`).toBeGreaterThan(10);

      const zeit = await karte.locator('time').getAttribute('datetime');
      expect(zeit, `Karte ${i + 1}: <time datetime> fehlt`).toMatch(/^\d{4}-\d{2}-\d{2}$/);

      // Messkette (scripts/revenue_funnel.py aggregiert cta_click per Slug)
      expect(await karte.getAttribute('data-umami-event'), `Karte ${i + 1}: Event fehlt`).toBe('cta_click');
      expect(await karte.getAttribute('data-umami-event-placement')).toBe('start-saison');
      expect(await karte.getAttribute('data-umami-event-saison')).toBe(saison);
      expect(await karte.getAttribute('data-umami-event-slug')).toMatch(new RegExp(`^saison-${saison}-`));
      expect(await karte.getAttribute('aria-labelledby'), `Karte ${i + 1}: aria-labelledby fehlt`)
        .toBeTruthy();
    }

    // Keine Dubletten im Block
    const ziele = [];
    for (let i = 0; i < anzahl; i++) ziele.push(await karten.nth(i).getAttribute('href'));
    expect(new Set(ziele).size, 'Saison-Block zeigt denselben Artikel mehrfach').toBe(ziele.length);

    const ratgeber = page.locator('a.ff-saison-pillar');
    await expect(ratgeber, 'Ratgeber-Link im Block-Kopf fehlt').toHaveCount(1);
    const ratgeberHref = await ratgeber.getAttribute('href');
    expect((await page.request.get(ratgeberHref)).status(), `Ratgeber ${ratgeberHref} nicht erreichbar`).toBe(200);
    expect(await ratgeber.getAttribute('data-umami-event-slug')).toBe(`saison-${saison}-ratgeber`);
  });

  test('Seitengerüst bleibt intakt: ein H1, Block ist Kind von main, kein toter Anker', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('h1'), 'Startseite: genau ein H1 (Bestands-Vertrag)').toHaveCount(1);
    const istKindVonMain = await page.evaluate(() => {
      const block = document.querySelector('section.ff-saison');
      return !!block && !!block.parentElement && block.parentElement.matches('main.main');
    });
    expect(istKindVonMain, 'Der Block muss direktes Kind von <main> sein, sonst greift die '
      + 'Mobile-Reihenfolge (order) aus custom.css/zz-saisonale-startseite.css nicht').toBe(true);

    const sprunziel = await page.evaluate(() => {
      const ueberschrift = document.getElementById('saison-fokus');
      const block = document.querySelector('section.ff-saison');
      return !!ueberschrift && block?.getAttribute('aria-labelledby') === 'saison-fokus';
    });
    expect(sprunziel, 'aria-labelledby muss auf die existente Überschrift #saison-fokus zeigen').toBe(true);
  });

  test.describe('Kontraste hell', () => {
    test.use({ colorScheme: 'light' });
    test('alle Saison-Texte ≥ 4.5:1 (WCAG AA)', async ({ page }) => {
      await page.goto('/');
      const werte = await page.evaluate(new Function(KONTRAST_QUELLE));
      for (const [name, wert] of Object.entries(werte)) {
        expect(wert, `${name} fehlt im Build (Kontrast nicht messbar)`).not.toBeNull();
        expect(wert, `${name}: ${wert}:1 im hellen Modus`).toBeGreaterThanOrEqual(TEXT_MINDEST_KONTRAST);
      }
    });
  });

  test.describe('Kontraste dunkel', () => {
    test.use({ colorScheme: 'dark' });
    test('alle Saison-Texte ≥ 4.5:1 (WCAG AA, Dark-Varianten wirksam)', async ({ page }) => {
      await page.goto('/');
      const werte = await page.evaluate(new Function(KONTRAST_QUELLE));
      for (const [name, wert] of Object.entries(werte)) {
        expect(wert, `${name} fehlt im Build (Kontrast nicht messbar)`).not.toBeNull();
        expect(wert, `${name}: ${wert}:1 im dunklen Modus`).toBeGreaterThanOrEqual(TEXT_MINDEST_KONTRAST);
      }
    });
  });

  test.describe('Mobile 390×844 (LCP-Schutz)', () => {
    test.use({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true });

    test('LCP-Cover bleibt im Viewport – der Saison-Block steht hinter den Karten', async ({ page }) => {
      await page.goto('/');
      await scrollThrough(page);
      const messung = await page.evaluate(() => {
        const karte = document.querySelector('article.post-entry.lcp-card');
        const bild = karte ? karte.querySelector('img') : null;
        const block = document.querySelector('section.ff-saison');
        const rb = bild ? bild.getBoundingClientRect() : null;
        return {
          bildTop: rb ? Math.round(rb.top) : null,
          bildHoehe: rb ? Math.round(rb.height) : null,
          viewport: window.innerHeight,
          orderBlock: block ? getComputedStyle(block).order : null,
          orderKarte: karte ? getComputedStyle(karte).order : null,
          blockTop: block ? Math.round(block.getBoundingClientRect().top) : null,
        };
      });
      expect(messung.bildTop, 'LCP-Cover fehlt auf der Startseite').not.toBeNull();
      expect(messung.bildTop, `LCP-Cover liegt bei top ${messung.bildTop}px unter dem Fold`)
        .toBeLessThan(messung.viewport);
      expect(Number(messung.orderBlock), 'Saison-Block braucht eine order ≥ 2 (Karten haben order: 1)')
        .toBeGreaterThanOrEqual(2);
      expect(Number(messung.orderKarte), 'Artikel-Karten müssen order: 1 behalten').toBe(1);
    });

    test('kein horizontaler Overflow durch den Saison-Block, Tap-Ziele groß genug', async ({ page }) => {
      await page.goto('/');
      await scrollThrough(page);
      const overflow = await page.evaluate(() => {
        const block = document.querySelector('section.ff-saison');
        return {
          doc: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          block: block ? block.scrollWidth - block.clientWidth : 0,
        };
      });
      expect(overflow.doc, `document um ${overflow.doc}px zu breit`).toBeLessThanOrEqual(1);
      expect(overflow.block, `Saison-Block läuft horizontal über (${overflow.block}px`)
        .toBeLessThanOrEqual(1);

      const hoehen = await page.evaluate(() => [...document.querySelectorAll('a.ff-saison-card, a.ff-saison-pillar')]
        .map((el) => Math.round(el.getBoundingClientRect().height)));
      expect(hoehen.length, 'keine Saison-Links gefunden').toBeGreaterThan(0);
      for (const h of hoehen) {
        expect(h, `Tap-Ziel nur ${h}px hoch (AA-Minimum 24px, Best Practice 44px)`).toBeGreaterThanOrEqual(44);
      }
    });
  });
});
