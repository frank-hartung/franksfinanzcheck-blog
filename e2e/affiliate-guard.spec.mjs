// ============================================================
//  SPEC: AFFILIATE-INTEGRITÄT (E2E-Wache)
//  ------------------------------------------------------------
//  Das Herzstück der Affiliate-Compliance des Blogs, bisher nur
//  statisch geprüft (scripts/affiliate_link_check.py) – hier als
//  Browser-Wahrheit gegen den gerenderten Build:
//    1. Jeder /go/-Redirect-Link: rel="sponsored nofollow noopener"
//       + target="_blank" (Pflicht seit Google-Link-Spam-Policy
//       2025 / DSGVO-Üblichkeit).
//    2. Jeder verlinkte /go/-Stumpf existiert im Build (200).
//    3. Externe target="_blank"-Links generell: noopener vorhanden
//       (Tabnabbing-Schutz – auch der Pinterest-Pin-Button).
//  Projekt: desktop (Markup identisch auf Mobile – dort läuft der
//  Layout-Aspekt in mobile.spec)
// ============================================================

import { test, expect } from './fixtures.mjs';
import { newestArticlePath, toLocal } from './helpers.mjs';

const REQUIRED_REL = ['sponsored', 'nofollow', 'noopener'];

/**
 * Neuester Artikel MIT Affiliate-Links: durchsucht die Startseiten-
 * Teaser der Reihe nach (per request-API, schnell) und liefert den
 * Pfad des ersten Artikels mit /go/-Links. So bleibt der Guard auch
 * dann scharf, wenn der allerneueste Beitrag keine Partner-Links hat.
 */
async function newestAffiliateArticle(page, request, baseURL) {
  await page.goto('/');
  const hrefs = await page
    .locator('article.post-entry a[href*="/posts/"]')
    .evaluateAll((els) => [...new Set(els.map((el) => el.getAttribute('href')))]);
  for (const href of hrefs.slice(0, 8)) {
    const res = await request.get(toLocal(href, baseURL));
    if (!res.ok()) continue;
    if ((await res.text()).includes('/go/')) return href;
  }
  return null;
}

test.describe('Affiliate-Integrität', () => {
  test('alle /go/-Links: sponsored + nofollow + noopener + _blank + subid', async ({ page, request, baseURL }) => {
    const articlePath = await newestAffiliateArticle(page, request, baseURL);
    test.skip(!articlePath, 'Kein aktueller Artikel mit Affiliate-Links auf der Startseite');
    await page.goto(articlePath);

    const goLinks = page.locator('a[href*="/go/"]');
    const count = await goLinks.count();

    const verstoesse = [];
    for (let i = 0; i < count; i++) {
      const link = goLinks.nth(i);
      const href = await link.getAttribute('href');
      const rel = (await link.getAttribute('rel')) || '';
      const target = await link.getAttribute('target');
      const relParts = rel.toLowerCase().split(/\s+/);

      for (const needed of REQUIRED_REL) {
        if (!relParts.includes(needed)) {
          verstoesse.push(`${href}: rel="${rel}" (fehlt: ${needed})`);
        }
      }
      if (target !== '_blank') verstoesse.push(`${href}: target="${target}" statt _blank`);
      // Awin-SubID-Attribution (01.09.2026): /go/-Links am Artikel tragen ?subid=<slug>
      if (!/[?&]subid=/.test(href)) verstoesse.push(`${href}: keine ?subid= (Awin-Attribution)`);
    }
    expect(verstoesse, 'Affiliate-Links sind vollständig ausgezeichnet').toEqual([]);
  });

  test('jeder verlinkte /go/-Redirect-Stumpf existiert (200, noindex)', async ({ page, request, baseURL }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);

    const hrefs = await page
      .locator('a[href*="/go/"]')
      .evaluateAll((els) => [...new Set(els.map((el) => el.getAttribute('href')))]);

    for (const href of hrefs) {
      const res = await request.get(baseURL.replace(/\/$/, '') + href);
      expect(res.status(), `Redirect-Stumpf ${href} existiert`).toBe(200);
      const html = await res.text();
      expect(html, `${href}: noindex gegen Indexierung`).toMatch(/noindex/i);
      expect(html, `${href}: leitet zu Partner (meta refresh)`).toMatch(/http-equiv="refresh"/i);
    }
  });

  test('externe target="_blank"-Links: immer noopener (Tabnabbing-Schutz)', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);
    // Hinweis: läuft bewusst auf dem NEUESTEN Artikel – hier landen die
    // Social/Pinterest-Buttons, die am häufigsten übersehen werden.

    const external = page.locator('a[target="_blank"]');
    const count = await external.count();
    expect(count, 'Artikel hat externe Links').toBeGreaterThan(0);

    const probleme = [];
    for (let i = 0; i < count; i++) {
      const link = external.nth(i);
      const href = await link.getAttribute('href');
      if (!/^https?:\/\//.test(href)) continue; // interne Anker ignorieren
      const rel = ((await link.getAttribute('rel')) || '').toLowerCase();
      if (!rel.split(/\s+/).includes('noopener') && !rel.split(/\s+/).includes('noreferrer')) {
        probleme.push(`${href}: rel="${rel}"`);
      }
    }
    expect(probleme, 'Externe _blank-Links schützen mit noopener').toEqual([]);
  });
});
