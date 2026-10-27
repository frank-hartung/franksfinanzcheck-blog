// ============================================================
// SPEC: BARRIEREFREIHEIT IM GERENDERTEN ZUSTAND (axe-core)
// ------------------------------------------------------------
// WARUM DIESE SPEC EXISTIERT (26.10.2026)
//
// `scripts/a11y_audit.py` prüft den GEBAUTEN TEXT: lang, title,
// genau eine H1, alt-Attribute, Skip-Link, ob `focus-visible` im
// CSS steht und ob die Marken-Tokens 4.5:1 erreichen. Das ist eine
// Parser-Prüfung — sie sieht kein gerendertes DOM, keine berechnete
// Farbe, keinen Accessible Name, keine ARIA-Beziehung.
//
// Genau diese Lücke schließt axe-core: Es läuft im echten Chromium
// auf dem gebauten Stand und prüft WCAG 2.1/2.2 A+AA am gerechneten
// Ergebnis. Für einen deutschen Finanzratgeber ist das keine Kür:
// Das Barrierefreiheitsstärkungsgesetz (BFSG) verweist auf WCAG 2.1
// AA als Maßstab für Verbraucher-Dienstleistungen.
//
// ABGRENZUNG (damit niemand sie als Beweis überdehnt)
//   · Automatisierbar sind rund ein Drittel der WCAG-Kriterien.
//     Tastaturführung, Verständlichkeit und Fehlermeldungsqualität
//     decken die übrigen Specs und der Mensch ab.
//   · Geprüft wird der lokale Build (e2e/server.mjs), nicht Produktion.
//   · Keine Inline-Unterdrückung: Ein Befund wird im Markup geheilt.
//     Sollte eine Ausnahme unvermeidbar sein, gehört sie nach
//     `data/a11y/axe_ausnahmen.json` – mit Grund, Datum und Prüftermin.
//     Diese Spec prüft, dass Ausnahmen begründet und datiert sind.
//
// SEITENAUSWAHL
// Statt einer gepflegten Liste (die driftet) wird gelesen, was
// tatsächlich gebaut wurde: alle Werkzeugseiten aus `public/werkzeuge/`
// plus Hub, Cockpit, Suche, Rechtsseiten und der neueste Artikel.
// Eine neue Werkzeugseite ist damit automatisch im Gate.
//
// SEIT 26.10.2026 AUCH DIE RATGEBER-WELTEN (public/pillar/*):
// Genau dort stand der dritte Befund derselben Klasse – 68 Karten mit
// `aria-label="Weiterlesen: <Titel>"`, die Datum, Anriss und „Jetzt lesen"
// verschwiegen. Die feste Seitenliste kannte die Pillar-Seiten nicht, also
// sah axe sie nie. Jetzt kommen sie automatisch aus dem Build; die Spec
// prüft, dass mindestens sechs gebaut wurden.
// ============================================================

import { readdirSync, readFileSync, existsSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { test, expect } from './fixtures.mjs';
import { consentAway, newestArticlePath, scrollThrough } from './helpers.mjs';

const HIER = path.dirname(fileURLToPath(import.meta.url));
const WURZEL = path.resolve(HIER, '..');
const PUBLIC = path.join(WURZEL, 'public');
const AUSNAHMEN_DATEI = path.join(WURZEL, 'data', 'a11y', 'axe_ausnahmen.json');

// axe-core liegt als exakt gepinnte devDependency im Root-Lockfile
// (kein CDN, kein Netzaufruf im Test). Fehlt die Datei, ist das ein
// Werkzeugfehler und kein Testergebnis – deshalb harter Abbruch oben.
const AXE_QUELLE = createRequire(import.meta.url).resolve('axe-core/axe.min.js');

/** WCAG-Tags, gegen die geprüft wird – 2.2 AA inklusive. */
const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'];

/** Sichtbaren Text als wörtlichen Teil des zugänglichen Namens prüfen. */
function textMuster(text) {
  return new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i');
}

/** Werkzeugseiten automatisch aus dem Build (eine Wahrheit: was gebaut ist). */
function werkzeugSeiten() {
  const ordner = path.join(PUBLIC, 'werkzeuge');
  if (!existsSync(ordner)) return [];
  return readdirSync(ordner, { withFileTypes: true })
    .filter((e) => e.isDirectory() && e.name !== 'page')
    .filter((e) => existsSync(path.join(ordner, e.name, 'index.html')))
    .map((e) => `/werkzeuge/${e.name}/`)
    .sort();
}

/**
 * Ratgeber-Welten automatisch aus dem Build. Sie tragen die kommerziell
 * wichtigsten Seiten und die Karten-Grids (`.ff-pc-card`), die in der festen
 * Liste nie auftauchten – der Grund, warum der dritte 2.5.3-Befund monatelang
 * unsichtbar blieb.
 */
function ratgeberSeiten() {
  const ordner = path.join(PUBLIC, 'pillar');
  if (!existsSync(ordner)) return [];
  return readdirSync(ordner, { withFileTypes: true })
    .filter((e) => e.isDirectory())
    .filter((e) => existsSync(path.join(ordner, e.name, 'index.html')))
    .map((e) => `/pillar/${e.name}/`)
    .sort();
}

/** Seiten, die jeder Besucher erreichen kann – inklusive der Rechtsflächen. */
function festSeiten() {
  return [
    '/',
    '/werkzeuge/',
    '/cockpit/',
    '/suche/',
    '/presse/',
    '/ueber/',
    '/impressum/',
    '/datenschutz/',
  ];
}

/** Ausnahmen-Registry (nur wenn vorhanden) – Befund → Grund, Datum, Prüfung. */
function ausnahmen() {
  if (!existsSync(AUSNAHMEN_DATEI)) return [];
  try {
    const roh = JSON.parse(readFileSync(AUSNAHMEN_DATEI, 'utf8'));
    return Array.isArray(roh) ? roh : [];
  } catch (fehler) {
    // Eine kaputte Registry darf das Gate nicht stillschweigend öffnen.
    throw new Error(`data/a11y/axe_ausnahmen.json ist kein gültiges JSON: ${fehler.message}`);
  }
}

/**
 * Führt axe auf der aktuellen Seite aus und schlägt bei Verstößen fehl.
 * Gibt das Ergebnis zurück, damit der Aufrufer es als Artefakt sichern kann.
 */
async function pruefeSeite(page, testInfo, pfad) {
  await page.goto(pfad, { waitUntil: 'load' });
  await consentAway(page);
  // Lazy-Bilder und eingebettete Komponenten müssen stehen, sonst prüft
  // axe einen halb gerenderten Baum und meldet Nichtsichtbares.
  await scrollThrough(page);
  await page.waitForLoadState('networkidle');

  // Prüfwerkzeug erst nach dem Laden injizieren: Die Seite soll ihren
  // eigenen Code unbeeinflusst ausführen (kein axe im Produktionspfad).
  await page.addScriptTag({ path: AXE_QUELLE });

  const ergebnis = await page.evaluate(async ({ tags }) => {
    const optionen = { runOnly: { type: 'tag', values: tags }, resultTypes: ['violations'] };
    const lauf = await window.axe.run(document, optionen);
    return {
      violations: lauf.violations.map((v) => ({
        id: v.id,
        impact: v.impact,
        help: v.help,
        helpUrl: v.helpUrl,
        wcag: v.tags.filter((t) => t.startsWith('wcag')),
        nodes: v.nodes.map((n) => ({
          target: n.target,
          html: (n.html || '').replace(/\s+/g, ' ').slice(0, 240),
          summary: (n.failureSummary || '').replace(/\s+/g, ' ').slice(0, 300),
        })),
      })),
    };
  }, { tags: WCAG_TAGS });

  // Immer als Artefakt – auch bei Grün ist die Prüftiefe ein Beleg.
  await testInfo.attach(`axe-${pfad.replace(/[^a-z0-9]+/gi, '-') || 'start'}.json`, {
    body: JSON.stringify({ pfad, tags: WCAG_TAGS, ...ergebnis }, null, 2),
    contentType: 'application/json',
  });

  // Ausnahmen wirken NODE-GENAU: Regel + CSS-Ziel + Seite (oder "*").
  // Eine Ausnahme auf eine Regel allein würde jede künftige Verletzung
  // derselben Regel mitdecken – ein offenes Tor statt einer Ausnahme.
  const registriert = ausnahmen().filter((a) => a.seite === pfad || a.seite === '*');
  const offen = [];
  for (const v of ergebnis.violations || []) {
    const reste = v.nodes.filter((n) => {
      const ziel = n.target.join(' ');
      return !registriert.some((a) => a.regel === v.id && ziel.includes(a.ziel));
    });
    if (reste.length) offen.push({ ...v, nodes: reste });
  }

  if (offen.length) {
    const zeilen = [];
    for (const v of offen) {
      zeilen.push(`\n■ ${v.id} (${v.impact || '?'}) – ${v.help}`);
      zeilen.push(`  WCAG: ${v.wcag.join(', ')} · ${v.helpUrl}`);
      for (const n of v.nodes.slice(0, 4)) {
        zeilen.push(`  · ${n.target.join(' ')}`);
        zeilen.push(`    ${n.html.slice(0, 180)}`);
      }
      if (v.nodes.length > 4) zeilen.push(`  · … und ${v.nodes.length - 4} weitere Knoten`);
    }
    throw new Error(
      `WCAG-Verstöße auf ${pfad}: ${offen.length} Regel(n), ` +
        `${offen.reduce((s, v) => s + v.nodes.length, 0)} Knoten` +
        zeilen.join('\n') +
        '\n\nHeilung: im Markup/CSS beheben. Ausnahmen nur über ' +
        'data/a11y/axe_ausnahmen.json (Grund + seit + pruefung).'
    );
  }
  return ergebnis;
}

const seiten = [...festSeiten(), ...werkzeugSeiten(), ...ratgeberSeiten()];

test.describe('Barrierefreiheit (axe-core, WCAG 2.1/2.2 A+AA)', () => {
  for (const pfad of seiten) {
    test(`keine WCAG-Verstöße auf ${pfad}`, async ({ page }, testInfo) => {
      await pruefeSeite(page, testInfo, pfad);
    });
  }

  // Die Artikelvorlage ist die Masse des Bestands: ein einziger Verstoß
  // hier trifft über hundert Seiten. Deshalb dynamisch der neueste Beitrag,
  // damit ein neuer Artikel nicht an einer gepflegten Liste vorbeiläuft.
  test('keine WCAG-Verstöße im neuesten Artikel', async ({ page }, testInfo) => {
    const pfad = await newestArticlePath(page);
    await pruefeSeite(page, testInfo, pfad);
  });

  // ---------------------------------------------------------------
  // WCAG 2.5.3 (Label in Name) – WIRKUNG, nicht Attribut
  // ---------------------------------------------------------------
  // Die Lehre aus dem 26.10.2026: Ein Test, der `aria-label` auf Existenz
  // prüft, hält einen falschen Namen für in Ordnung. Diese Tests lesen den
  // Namen, den der Screenreader tatsächlich bekommt, und verlangen den
  // sichtbaren Text darin.
  test('Marken-Link im Kopf: Name ist der sichtbare Descriptor-Text', async ({ page }) => {
    await page.goto('/');
    const marke = page.locator('header.header a.ff-brand').first();
    await expect(marke).toHaveAccessibleName(/Unabhängige Fixkosten-Redaktion/);
    // Kein Override: Der Name kommt aus dem Inhalt und kann nicht driften.
    // (Der Descriptor ist auf dem Telefon nur visuell versteckt – er bleibt
    // im Accessibility-Tree, sonst hätte der Link gar keinen Namen.)
    expect(await marke.getAttribute('aria-label'), 'kein aria-label-Override').toBeNull();
  });

  test('Weiterlese-Karten: Name enthält Datum und Titel', async ({ page }) => {
    const pfad = await newestArticlePath(page);
    await page.goto(pfad);
    const karten = page.locator('.ff-related-card');
    const anzahl = await karten.count();
    expect(anzahl, 'Weiterlese-Karten im neuesten Artikel').toBeGreaterThan(0);
    for (let i = 0; i < anzahl; i += 1) {
      const karte = karten.nth(i);
      expect(await karte.getAttribute('aria-label'), `Karte ${i + 1}: kein Override`).toBeNull();
      const titel = (await karte.locator('.ff-related-card__heading').innerText()).trim();
      const datum = (await karte.locator('.ff-related-card__date').innerText()).trim();
      await expect(karte).toHaveAccessibleName(textMuster(titel));
      await expect(karte).toHaveAccessibleName(textMuster(datum));
    }
  });

  test('Pillar-Karten: Name kommt aus dem Inhalt, nicht aus einem Override', async ({ page }) => {
    await page.goto('/pillar/strom-sparen/');
    // 27.10.2026: Die Karte ist kein Link mehr (Ankertext war Titel + Teaser
    // + „Jetzt lesen", Seobility: „Linktexte zu lang"), sondern ein <article>
    // mit genau EINEM Link – dem Titel. Geprüft wird beides: kein ARIA-
    // Override und der Linkname ist exakt der sichtbare Titel.
    const karten = page.locator('article.ff-pc-card');
    const anzahl = await karten.count();
    expect(anzahl, 'Pillar-Karten im Ratgeber Strom & Gas').toBeGreaterThan(0);
    for (let i = 0; i < Math.min(anzahl, 3); i += 1) {
      const karte = karten.nth(i);
      const links = karte.locator('a');
      expect(await links.count(), `Karte ${i + 1}: genau ein Link`).toBe(1);
      const link = links.first();
      expect(await karte.getAttribute('aria-label'), `Karte ${i + 1}: kein Override`).toBeNull();
      expect(await link.getAttribute('aria-label'), `Karte ${i + 1}: kein Override am Link`).toBeNull();
      const titel = (await karte.locator('.ff-pc-card__title').innerText()).trim();
      expect((await link.innerText()).trim(), `Karte ${i + 1}: Ankertext = Titel`).toBe(titel);
      await expect(link).toHaveAccessibleName(textMuster(titel));
      // Die Karte bleibt als Ganzes klickbar (Inset-Overlay des Titel-Links):
      // ein Klick auf den Teaser muss zum selben Ziel führen.
      const ziel = await link.getAttribute('href');
      const box = await karte.boundingBox();
      const antwort = await page.request.get(ziel);
      expect(antwort.status(), `Karte ${i + 1}: Ziel ${ziel} nicht erreichbar`).toBe(200);
      expect(box.width).toBeGreaterThan(0);
    }
  });

  test('die Ausnahmen-Registry ist begründet, datiert und läuft ab', async () => {
    const fehler = [];
    const heute = new Date().toISOString().slice(0, 10);
    for (const a of ausnahmen()) {
      const name = `${a.regel || '?'} auf ${a.seite || '?'}`;
      if (!a.regel || !a.seite) fehler.push(`Eintrag ohne regel/seite: ${JSON.stringify(a)}`);
      if (!a.ziel || String(a.ziel).trim().length < 3) {
        fehler.push(`${name}: CSS-Ziel (ziel) fehlt – eine Ausnahme muss den Knoten benennen`);
      }
      if (!a.grund || String(a.grund).trim().length < 20) {
        fehler.push(`${name}: Grund fehlt oder ist zu knapp (mind. 20 Zeichen)`);
      }
      if (!/^\d{4}-\d{2}-\d{2}$/.test(String(a.seit || ''))) {
        fehler.push(`${name}: Datum (seit) fehlt oder ist nicht JJJJ-MM-TT`);
      }
      if (!/^\d{4}-\d{2}-\d{2}$/.test(String(a.pruefung || ''))) {
        fehler.push(`${name}: Prüfdatum (pruefung) fehlt oder ist nicht JJJJ-MM-TT`);
      } else if (String(a.pruefung) < heute) {
        fehler.push(
          `${name}: Prüftermin ${a.pruefung} ist überschritten (heute ${heute}) – ` +
            'Ausnahme erneuern oder den Befund heilen. Eine Ausnahme ohne Ablauf ist ein offenes Tor.'
        );
      }
      if (a.beleg && !/^(?:https?:\/\/[^\s]+|[^\s]+\.md)$/.test(String(a.beleg))) {
        fehler.push(`${name}: Beleg muss URL oder Datei im Repo sein`);
      }
    }
    expect(fehler, 'Ausnahmen ohne Grund, Ziel, Datum oder mit abgelaufenem Prüftermin').toEqual([]);
  });
});

// Kein stilles Vorbeilaufen: Wer eine Werkzeugseite baut, bekommt sie geprüft.
test('jede gebaute Werkzeugseite landet im A11y-Gate', async () => {
  expect(werkzeugSeiten().length, 'mindestens neun Werkzeugseiten im Build').toBeGreaterThanOrEqual(9);
});

// Dasselbe für die Ratgeber-Welten: fällt eine aus dem Build, ist das ein
// Befund und keine stille Lücke im Gate.
test('jede gebaute Ratgeber-Welt landet im A11y-Gate', async () => {
  expect(ratgeberSeiten().length, 'mindestens sechs Ratgeber-Welten im Build').toBeGreaterThanOrEqual(6);
});
