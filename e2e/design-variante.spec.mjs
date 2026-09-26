// ============================================================
//  SPEC: DESIGN-VARIANTEN – die Produktions-Sicherung
//  ------------------------------------------------------------
//  Rollout 26.09.2026 (Design-Varianten-Werkbank).
//  Runbook: docs/ANLEITUNG-DESIGN-VARIANTEN.md
//  Projekt: desktop
//
//  WAS HIER GETESTET WIRD – UND WARUM GERADE DAS
//  Die Werkbank erlaubt es, Layoutvarianten zu bauen und zu messen.
//  Der gefährliche Fall ist nicht die Variante selbst, sondern ihr
//  unbemerktes Durchsickern in den Produktionsbau. Diese Spec ist die
//  letzte Sicherung davor und prüft drei Wege, auf denen das passieren
//  könnte:
//
//    1. Der Parameter bleibt versehentlich gesetzt (hugo.toml/CI).
//    2. Jemand legt Varianten-CSS nach assets/css/extended/ – dort
//       wird ALLES bei jedem Build mitgebündelt.
//    3. Das Register behauptet etwas anderes als der Bau.
//
//  Die Tests laufen gegen den normalen public/-Bau der Suite, also
//  genau gegen das, was deployt würde.
// ============================================================

import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { test, expect } from './fixtures.mjs';
import { newestArticlePath } from './helpers.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');
const VARIANTEN_DIR = join(ROOT, 'assets', 'css', 'varianten');
const EXTENDED_DIR = join(ROOT, 'assets', 'css', 'extended');
const REGISTER = join(ROOT, 'data', 'design', 'varianten.yaml');

function variantenDateien() {
  if (!existsSync(VARIANTEN_DIR)) return [];
  return readdirSync(VARIANTEN_DIR).filter((f) => f.endsWith('.css'));
}

test.describe('Design-Varianten: Produktions-Sicherung', () => {
  test('der ausgelieferte Bau trägt keine Variantenmarke', async ({ page }) => {
    for (const pfad of ['/', '/posts/']) {
      await page.goto(pfad);
      const marken = await page.locator('style[data-ff-variante]').count();
      expect(marken, `Variantenmarke auf ${pfad}`).toBe(0);
    }

    const artikel = await newestArticlePath(page);
    await page.goto(artikel);
    expect(
      await page.locator('style[data-ff-variante]').count(),
      `Variantenmarke auf ${artikel}`
    ).toBe(0);
  });

  test('kein Varianten-Stylesheet liegt im immer gebündelten extended/', () => {
    // assets/css/extended/*.css wird von head.html per resources.Match
    // komplett in das eine ausgelieferte Stylesheet konkateniert. Eine
    // Varianten-Datei dort wäre sofort und dauerhaft in Produktion –
    // ohne Messung, ohne Freigabe, ohne dass es jemandem auffällt.
    const inExtended = existsSync(EXTENDED_DIR) ? readdirSync(EXTENDED_DIR) : [];
    for (const datei of variantenDateien()) {
      expect(
        inExtended.includes(datei),
        `${datei} darf NICHT in assets/css/extended/ liegen`
      ).toBe(false);
    }
  });

  test('CSS-Regeln der Varianten tauchen nicht im Produktions-CSS auf', async ({ page }) => {
    // Gegenprobe zum Dateitest: Selbst wenn der Inhalt auf anderem Weg
    // (Copy&Paste in custom.css) in die Basis wandert, fällt es hier auf.
    await page.goto('/');
    const ausgeliefert = await page.evaluate(() =>
      Array.from(document.querySelectorAll('style'))
        .map((s) => s.textContent || '')
        .join('\n')
    );

    for (const datei of variantenDateien()) {
      const quelle = readFileSync(join(VARIANTEN_DIR, datei), 'utf8');
      // Eine markante Deklaration aus der Datei suchen: die erste
      // Regel mit einem Wert, die nicht in einem Kommentar steht.
      const ohneKommentare = quelle.replace(/\/\*[\s\S]*?\*\//g, ' ');
      const treffer = ohneKommentare.match(/([a-z-]+)\s*:\s*([^;{}]+);/);
      if (!treffer) continue;
      const nadel = `${treffer[1]}:${treffer[2].trim()}`.replace(/\s+/g, '');
      const heuHaufen = ausgeliefert.replace(/\s+/g, '');
      expect(
        heuHaufen.includes(nadel),
        `Regel aus ${datei} ("${nadel}") darf nicht im Produktions-CSS stehen`
      ).toBe(false);
    }
  });

  test('der Test-Server komprimiert Text wie GitHub Pages', async ({ page }) => {
    // 26.09.2026: e2e/server.mjs lieferte Text unkomprimiert aus, Pages tut
    // das nicht. Auf Lighthouses simuliertem Mobilfunk kostete das rund
    // 0,7 s – und erschien als „LCP-Budget gerissen" (3179 ms). Mit
    // Kompression: 1760 ms. Eine Messumgebung, die pessimistischer ist als
    // die Wirklichkeit, erzeugt Befunde, die niemand beheben kann.
    const antwort = await page.goto('/');
    const kodierung = antwort.headers()['content-encoding'];
    expect(kodierung, 'HTML wird komprimiert ausgeliefert').toMatch(/br|gzip/);
  });

  test('das Register aktiviert keine Variante ohne Unterschrift', () => {
    // Bewusst als Rohtext-Prüfung: Ein YAML-Parser als Test-Abhängigkeit
    // wäre für eine einzige Zeile nicht zu rechtfertigen. Die
    // vollständige Registerprüfung macht scripts/design_variant_gate.py.
    expect(existsSync(REGISTER), 'data/design/varianten.yaml existiert').toBe(true);
    const text = readFileSync(REGISTER, 'utf8');
    const zeile = text.match(/^aktiv:\s*(.*)$/m);
    expect(zeile, '`aktiv:` steht im Register').not.toBeNull();

    const wert = (zeile[1] || '').trim().replace(/^["']|["']$/g, '');
    if (wert === '') return; // Basis – nichts zu prüfen

    // Ist eine Variante aktiv, MUSS ihr Eintrag eine Unterschrift tragen.
    const block = text.split(/^\s*-\s+id:\s*/m).find((b) => b.startsWith(wert));
    expect(block, `Eintrag für aktive Variante "${wert}" gefunden`).toBeTruthy();
    expect(
      /mensch:\s*true/.test(block),
      `aktive Variante "${wert}" hat freigabe.mensch: true`
    ).toBe(true);
  });
});
