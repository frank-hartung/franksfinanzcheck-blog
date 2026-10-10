// ============================================================
//  BROWSER-RESOLVER – gemeinsame Chromium-Versorgung
//  --------------------------------------------------
//  Reihenfolge:
//    1. FF_BROWSER_PATH / CHROME_PATH (explizit verwalteter Browser)
//    2. Playwright-Browser-Cache (falls bereits installiert)
//    3. Gepinntes @sparticuz/chromium aus package-lock.json
//
//  Stufe 3 enthält Browser + nötige Kompatibilitätsbibliotheken und
//  wird über registry.npmjs.org installiert. Sie ersetzt den flüchtigen
//  `npm i --no-save`-Workaround und benötigt cdn.playwright.dev nicht.
//  Der tatsächlich genutzte Pfad wird protokolliert, damit keine
//  Browserabweichung still bleibt. Runbook: docs/ANLEITUNG-CHROMIUM.md.
// ============================================================

import { existsSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { chromium as pwChromium } from 'playwright-core';
import { prepareChromiumTemp, withChromiumExtractionLock } from '../scripts/chromium_cache.mjs';

/**
 * Liefert launchOptions für Playwright (leer = Standardverhalten).
 * Nebenwirkung: setzt bei Fallback LD_LIBRARY_PATH/FONTCONFIG_PATH.
 */
export async function resolveLaunchOptions() {
  // ---------- Weg 1: explizit gesetzter System-Browser ----------
  const explicitPath = process.env.FF_BROWSER_PATH || process.env.CHROME_PATH;
  if (explicitPath) {
    if (existsSync(explicitPath)) {
      console.error(`[E2E] Expliziter Chromium aktiv: ${explicitPath}`);
      return { executablePath: explicitPath };
    }
    console.warn(`[E2E] Browserpfad existiert nicht: ${explicitPath}; versuche die verwalteten Fallbacks.`);
  }

  // ---------- Weg 2: vorhandener Playwright-Browser ----------
  try {
    const exe = pwChromium.executablePath();
    if (existsSync(exe)) {
      console.error(`[E2E] Playwright-Chromium aktiv: ${exe}`);
      return {};
    }
  } catch {
    // Browser-Registry nicht verfügbar → gebündelten Browser versuchen.
  }

  // ---------- Weg 3: gepinntes Linux-Bundle aus node_modules ----------
  if (process.platform !== 'linux' || !['x64', 'arm64'].includes(process.arch)) {
    console.warn(
      `[E2E] @sparticuz/chromium ist nur für Linux x64/arm64 vorgesehen (${process.platform}/${process.arch}). ` +
      'Auf diesem System CHROME_PATH setzen oder einen passenden Playwright-Browser installieren.'
    );
    return {};
  }

  try {
    const entry = fileURLToPath(import.meta.resolve('@sparticuz/chromium'));
    const packageRoot = dirname(dirname(entry));
    const packageVersion = JSON.parse(readFileSync(join(packageRoot, 'package.json'), 'utf8')).version;

    // Sparticuz cacheert hart unter $TMPDIR/chromium. Ein früherer
    // Paketstand würde sonst nach einem Upgrade still weiterlaufen.
    // Versionsisolierung erzwingt einen passenden Binary-Cache je Pin.
    const versionedTmp = prepareChromiumTemp(packageVersion);
    const mod = await import('@sparticuz/chromium');
    const chromium = mod.default;

    // Kompat-Bibliotheken (libnspr4/libnss3/…): sparticuz entpackt sie
    // nur auf Amazon Linux 2023 automatisch – auf Debian/Ubuntu holen
    // wir sie selbst über die mitgelieferte inflate()-Funktion.
    const libDir = join(tmpdir(), 'al2023', 'lib');
    const exe = await withChromiumExtractionLock(versionedTmp, async () => {
      if (!existsSync(libDir)) {
        await mod.inflate(join(packageRoot, 'bin', 'al2023.tar.br'));
      }
      return chromium.executablePath();
    });
    process.env.LD_LIBRARY_PATH = [libDir, tmpdir(), process.env.LD_LIBRARY_PATH]
      .filter(Boolean)
      .join(':');
    process.env.FONTCONFIG_PATH ??= join(tmpdir(), 'fonts');

    // stderr statt stdout: Messskripte geben JSON auf stdout aus.
    console.error(`[E2E] Gebündelter Chromium aktiv: ${exe} (@sparticuz/chromium, versioniert im Root-Lockfile)`);
    return {
      executablePath: exe,
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
    };
  } catch (e) {
    console.warn(
      '[E2E] Kein startbarer Playwright- oder Projekt-Chromium gefunden.\n' +
        '      Bitte zuerst `npm ci` und danach `npm run browser:setup` ausführen.\n' +
        '      Dafür wird kein Zugriff auf cdn.playwright.dev benötigt.\n' +
        `      (Fallback-Fehler: ${String(e.message).slice(0, 200)})`
    );
    return {};
  }
}
