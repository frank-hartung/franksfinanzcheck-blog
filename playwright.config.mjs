// ============================================================
//  PLAYWRIGHT-KONFIGURATION – FranksFinanzcheck E2E-Suite
//  ------------------------------------------------------------
//  Rollout 12.09.2026 (Design-Skills-Premium-Integration).
//
//  Architektur (bewusst schlank & deterministisch):
//  · Kein Dev-Server-Stack: Hugo baut statisch nach public/,
//    e2e/server.mjs serviert die Dateien zero-dependency auf
//    127.0.0.1:4173 (gleiches Muster wie scripts/_design_shots.js).
//  · Service Worker werden in Tests BLOCKIERT – sonst serviert
//    der SW-Cache je nach HUGO_JSDELIVR_SHA evtl. alte Inhalte
//    und macht Tests nicht-deterministisch.
//  · Zwei Projekte: Desktop (Chromium 1280×720) und Mobile
//    (iPhone-14-Emulation) – deckt Layout/Overflow und Inter-
//    aktion ab, ohne vier Browser-Engines in CI zu ziehen.
//  · traces/screenshots nur bei Fehlern (schnelle Läufe,
//    volle Diagnose im Fehlerfall).
//
//  Lauf:   npm run test:e2e          (baut + testet)
//          npx playwright test       (nutzt vorhandenes public/)
//          npm run test:e2e:report   (HTML-Report öffnen)
// ============================================================

import { defineConfig, devices } from '@playwright/test';
import { resolveLaunchOptions } from './e2e/browser.mjs';

const PORT = Number(process.env.E2E_PORT || 4173);
const baseURL = process.env.E2E_BASE_URL || `http://127.0.0.1:${PORT}`;

// Browser-Resolver: Standard = Playwright-Chromium; Fallback siehe e2e/browser.mjs
const launchOptions = await resolveLaunchOptions();

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ['list'],
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
  ],

  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
    locale: 'de-DE',
    timezoneId: 'Europe/Berlin',
    serviceWorkers: 'block',
    actionTimeout: 10_000,
    navigationTimeout: 20_000,
    launchOptions,
  },

  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'] },
      // Mobile-Spezifikation läuft nur im Mobile-Projekt
      testIgnore: /mobile\.spec\.mjs/,
    },
    {
      name: 'mobile',
      // WICHTIG: browserName explizit auf chromium setzen! Ohne diese Zeile
      // leitet Playwright die Engine vom Device-Profil ab – devices['iPhone 14']
      // trägt defaultBrowserType 'webkit' und die Suite würde versuchen, den
      // WebKit-Treiber gegen den Chromium-Binary zu starten (hängt still).
      // iPhone-Emulation (isMobile) ist ohnehin Chromium-only.
      use: { ...devices['iPhone 14'], browserName: 'chromium' },
      // Mobile-Projekt läuft gezielt nur die Mobile-Spec
      testMatch: /mobile\.spec\.mjs/,
    },
  ],

  webServer: {
    command: 'node e2e/server.mjs',
    url: `http://127.0.0.1:${PORT}/healthz`,
    reuseExistingServer: true,
    timeout: 30_000,
    stdout: 'ignore',
    stderr: 'pipe',
  },
});
