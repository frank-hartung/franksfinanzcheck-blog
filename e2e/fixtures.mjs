// ============================================================
//  E2E-FIXTURES – hermetische Testumgebung für alle Specs
//  ------------------------------------------------------------
//  Rollout 12.09.2026 (Design-Skills-Premium-Integration).
//
//  Warum ein eigenes `test`?
//  Das Blog rendert einige Ressourcen mit ABSOLUTEN Produktions-
//  URLs (z. B. Autoren-Foto, og:image, Canonical-Referenzen).
//  Ohne Eingriff würden E2E-Tests gegen die LIVE-Seite laufen –
//  langsam, flaky und gefährlich (Tests messen Produktion statt
//  Build). Die Auto-Fixture leitet jede Anfrage an
//  https://franksfinanzcheck.de/** auf den lokalen Test-Server
//  um → die Suite ist vollständig hermetisch gegen den Build.
//
//  Alle Specs importieren deshalb:  import { test, expect } from './fixtures.mjs'
// ============================================================

import { test as base, expect } from '@playwright/test';

export const SITE_ORIGIN = 'https://franksfinanzcheck.de';

export const test = base.extend({
  page: async ({ page, baseURL }, use) => {
    await page.route(`${SITE_ORIGIN}/**`, async (route) => {
      const url = new URL(route.request().url());
      const local = (baseURL || 'http://127.0.0.1:4173').replace(/\/$/, '') + url.pathname + url.search;
      // Protokollwechsel (https→http) ist bei route.continue verboten –
      // deshalb fetchen wir die lokale Ressource und erfüllen die Anfrage.
      try {
        const response = await route.fetch({ url: local });
        return route.fulfill({ response });
      } catch {
        return route.abort();
      }
    });
    await use(page);
  },
});

export { expect };
