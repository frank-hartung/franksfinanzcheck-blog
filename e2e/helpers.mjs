// ============================================================
//  E2E-HELFER – gemeinsame Utilities der Playwright-Suite
//  ------------------------------------------------------------
//  · newestArticlePath(): ermittelt den neuesten Artikel über
//    den ersten Teaser der Startseite (robust gegen neue
//    Beiträge – kein hartkodierter Slug).
//  · watchErrors(): sammelt JS-Ausnahmen (pageerror → immer
//    fatal) und Console-Fehler (fatal nur bei Same-Origin –
//    Drittanbieter wie Pinterest/Analytics dürfen lokal
//    flackern, ohne den Build rot zu machen).
//  · scrollThrough(): scrollt die Seite komplett durch, damit
//    lazy-loadende Bilder (loading="lazy") tatsächlich laden
//    und die Bild-Checks nicht gegen ungeladene <img> laufen.
// ============================================================

import { expect } from '@playwright/test';

/** Kanonische Produktions-URL (für Canonical-/og-Checks). */
export const SITE_ORIGIN = 'https://franksfinanzcheck.de';

/** Externe Hosts, deren Console-/Netzfehler NICHT failen (Drittanbieter). */
export const EXTERNAL_NOISE = [
  'pinterest',
  'googletagmanager',
  'google-analytics',
  'analytics',
  'umami',
  'mastodon',
];

let cachedNewestArticle = null;

/**
 * Pfad des neuesten Artikels (z. B. /posts/2026-09-11-…/).
 * Wird pro Worker gecacht – alle Specs im Worker nutzen denselben.
 */
export async function newestArticlePath(page) {
  if (cachedNewestArticle) return cachedNewestArticle;
  await page.goto('/');
  const href = await page
    .locator('article.post-entry a[href*="/posts/"]')
    .first()
    .getAttribute('href');
  expect(href, 'Startseite muss mindestens einen Artikel-Teaser linken').toBeTruthy();
  cachedNewestArticle = href;
  return cachedNewestArticle;
}

/**
 * Registriert Fehler-Sammler auf einer Page.
 * Liefert Objekt für assertNoErrors() zurück.
 */
export function watchErrors(page) {
  const state = { pageErrors: [], consoleErrors: [] };
  page.on('pageerror', (err) => state.pageErrors.push(String(err)));
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const loc = msg.location() || {};
      state.consoleErrors.push({ text: msg.text(), url: loc.url || '' });
    }
  });
  return state;
}

/**
 * asserts: keine JS-Ausnahmen, keine same-origin Console-Fehler.
 * Externe/Drittanbieter-Fehler werden mitgeteilt, aber geduldet.
 */
export function assertNoErrors(state, kontext) {
  const external = state.consoleErrors.filter((e) =>
    EXTERNAL_NOISE.some((n) => e.url.includes(n) || e.text.toLowerCase().includes(n))
  );
  const local = state.consoleErrors.filter(
    (e) => !EXTERNAL_NOISE.some((n) => e.url.includes(n) || e.text.toLowerCase().includes(n))
  );
  expect(
    state.pageErrors,
    `${kontext}: keine unbehandelten JS-Fehler (pageerror)`
  ).toEqual([]);
  expect(
    local.map((e) => `${e.url}: ${e.text}`),
    `${kontext}: keine Console-Fehler von eigener Seite`
  ).toEqual([]);
  if (external.length) {
    console.log(`ℹ ${kontext}: ${external.length} ignorierte Drittanbieter-Fehler`);
  }
}

/**
 * Consent-Banner wegklären (01.10.2026, Cockpit-Reset-Test):
 * Der Banner liegt position:fixed über der kompletten unteren
 * Viewport-Kante und fängt sonst jeden Klick auf Seiteninhalt am
 * unteren Rand ab (Playwright-Hit-Target-Check dreht sich im Kreis).
 * Klickt – wenn sichtbar – „Nur notwendige“, wie ein echter Besucher.
 */
export async function consentAway(page) {
  const banner = page.locator('#ff-consent-banner');
  if (await banner.isVisible().catch(() => false)) {
    await banner.locator('.ff-consent-banner__btn-necessary').click();
    await page.waitForFunction(
      () => !document.querySelector('#ff-consent-banner') ||
        getComputedStyle(document.querySelector('#ff-consent-banner')).display === 'none',
      null,
      { timeout: 5_000 }
    ).catch(() => {});
  }
}

/** Seite einmal komplett durchscrollen (löst lazy-loading aus). */
export async function scrollThrough(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      // Blog-CSS nutzt `scroll-behavior: smooth` – das würde unsere Schritte
      // animieren und das spätere scrollTo(0,0) abbrechen, bevor unten
      // liegende lazy-Bilder ihren Fetch auslösen. Deshalb: temporär 'auto'.
      const html = document.documentElement;
      const vorher = html.style.scrollBehavior;
      html.style.scrollBehavior = 'auto';
      const step = () => {
        window.scrollBy(0, Math.round(window.innerHeight * 0.8));
        // Am Boden kurz verweilen, damit lazy-loader sicher feuern
        if (window.scrollY + window.innerHeight < document.body.scrollHeight - 2) {
          setTimeout(step, 110);
        } else {
          setTimeout(() => {
            window.scrollTo(0, 0);
            html.style.scrollBehavior = vorher;
            setTimeout(resolve, 150);
          }, 400);
        }
      };
      step();
    });
  });
}

/**
 * Wartet, bis alle <img> der Seite settled sind (complete).
 * Nach Timeout wird weitergemacht – die eigentliche Prüfung
 * (naturalWidth) meldet dann präzise, WELCHE Bilder hängen.
 */
export async function waitForImages(page, timeout = 15_000) {
  await page
    .waitForFunction(() => [...document.images].every((img) => img.complete), null, { timeout })
    .catch(() => {});
}

/** Macht eine beliebige URL (auch absolute Produktions-URL) lokal testbar.
    Härtung 2026-10 (Code-Scanning): exakter Origin-Vergleich statt
    startswith-Präfix – „https://franksfinanzcheck.de.böse.example“ würde
    sonst fälschlich als eigene Produktions-URL gelten. */
export function toLocal(url, baseURL) {
  try {
    const u = new URL(url);
    if (u.origin === SITE_ORIGIN) {
      return baseURL.replace(/\/$/, '') + u.pathname + u.search + u.hash;
    }
  } catch {
    /* relative URL – unverändert zurückgeben */
  }
  return url;
}
