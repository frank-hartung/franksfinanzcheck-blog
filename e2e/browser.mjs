// ============================================================
//  E2E-BROWSER-RESOLVER – Chromium-Auffindung mit Fallback
//  ------------------------------------------------------------
//  Rollout 12.09.2026 (Design-Skills-Premium-Integration).
//
//  Weg 1 (Standard, CI + lokale Entwicklung):
//    Playwrights eigenen Chromium aus der Registry nutzen
//    (`npx playwright install chromium`). Wenn der vorhanden
//    ist, greift KEIN Spezialfall – 100 % Upstream-Verhalten.
//
//  Weg 2 (Fallback, nur wenn Weg 1 fehlt):
//    @sparticuz/chromium aus node_modules verwenden (npm-Paket
//    mit gebündeltem Chromium, kein CDN-Download nötig). Damit
//    laufen die Tests auch in Umgebungen mit blockiertem
//    cdn.playwright.dev (z. B. Sandboxen/air-gapped Runner).
//    Das Paket wird dort per `npm i --no-save @sparticuz/chromium`
//    bereitgestellt und NICHT in package.json gepinnt – CI soll
//    immer den offiziellen Weg gehen.
//
//  Der Fallback ist bewusst explizit geloggt – keine stillen
//  Abweichungen zwischen Umgebungen.
// ============================================================

import { existsSync, mkdirSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { chromium as pwChromium } from 'playwright-core';

/**
 * Liefert launchOptions für Playwright (leer = Standardverhalten).
 * Nebenwirkung: setzt bei Fallback LD_LIBRARY_PATH/FONTCONFIG_PATH.
 */
export async function resolveLaunchOptions() {
  // ---------- Weg 1: offizieller Playwright-Chromium ----------
  try {
    const exe = pwChromium.executablePath();
    if (existsSync(exe)) return {};
  } catch {
    // Registry nicht verfügbar → Weg 2 versuchen
  }

  // ---------- Weg 2: @sparticuz/chromium aus node_modules ----------
  try {
    const mod = await import('@sparticuz/chromium');
    const chromium = mod.default;
    const exe = await chromium.executablePath();

    // Kompat-Bibliotheken (libnspr4/libnss3/…): sparticuz entpackt sie
    // nur auf Amazon Linux 2023 automatisch – auf Debian/Ubuntu holen
    // wir sie selbst über die mitgelieferte inflate()-Funktion.
    const libDir = join(tmpdir(), 'al2023', 'lib');
    if (!existsSync(libDir)) {
      const binDir = join(exe, '..');
      await mod.inflate(join(binDir, 'al2023.tar.br'));
    }
    process.env.LD_LIBRARY_PATH = [libDir, tmpdir(), process.env.LD_LIBRARY_PATH]
      .filter(Boolean)
      .join(':');
    process.env.FONTCONFIG_PATH ??= join(tmpdir(), 'fonts');

    // stderr statt stdout: design-metrics.mjs gibt JSON auf stdout aus
    console.error(`[E2E] Fallback-Browser aktiv: ${exe} (Chromium aus @sparticuz/chromium)`);
    return {
      executablePath: exe,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    };
  } catch (e) {
    console.warn(
      '[E2E] Kein eigener Playwright-Chromium gefunden und kein @sparticuz/chromium-Fallback möglich.\n' +
        '      Bitte ausführen:  npx playwright install chromium\n' +
        `      (Fallback-Fehler: ${String(e.message).slice(0, 160)})`
    );
    return {};
  }
}
