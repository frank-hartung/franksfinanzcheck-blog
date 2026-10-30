#!/usr/bin/env node
/**
 * dom_laufzeit_messung.mjs — wie viele Elemente hat eine Seite WIRKLICH?
 * ------------------------------------------------------------
 * Warum es diese Messung gibt (#900, 30.10.2026)
 *
 *   Der statische Audit (`scripts/dom_audit.py`) zählt die Elemente, die im
 *   ausgelieferten HTML stehen. Der Browser sieht mehr: `ff-premium.js`
 *   hängt an jede Überschrift einen Kopierknopf, an jede Seite ein
 *   Mini-Verzeichnis. Auf der längsten Artikelseite waren das 1033
 *   ausgelieferte und **1401** Laufzeit-Elemente – ein Element über der
 *   harten Lighthouse-Grenze (1400), 51 über der Frühwarnung (1350).
 *   Aufgefallen ist das erst im Browser-Lauf, also spät und teuer.
 *
 *   Diese Messung bildet den Laufzeit-DOM OHNE Browser nach: jsdom parst die
 *   gebaute Seite und führt genau die lokalen Skripte aus, die die Seite
 *   selbst einbindet. Das ist derselbe DOM-Zustand, den Chrome herstellt
 *   (es ist eine echte DOM-Implementierung, kein Modell) – nur ohne Layout.
 *
 * WARUM 1200 UND NICHT 1400
 *
 *   Die harte Grenze (1400, Lighthouse) bleibt, wo sie ist. Diese Messung
 *   prüft das *Ziel*: mindestens 200 Elemente Luft nach oben, damit ein
 *   neuer Absatz, eine neue Box oder ein neues UI-Element nicht sofort am
 *   Limit kratzt. Der Wert ist bewusst KEIN erhöhtes Budget – er ist
 *   strenger als die Frühwarnung (1350) und macht einen Rückfall sofort rot,
 *   statt ihn als gelbe Notiz zu verschlucken.
 *
 * Aufruf
 *   node scripts/dom_laufzeit_messung.mjs                  # public/, Limit 1200
 *   node scripts/dom_laufzeit_messung.mjs --dir public.site --top 12
 *   node scripts/dom_laufzeit_messung.mjs --limit 1350     # nur die Warnlinie
 *   node scripts/dom_laufzeit_messung.mjs --json .cache/layout/laufzeit.json
 *   node scripts/dom_laufzeit_messung.mjs --selftest       # ohne Bau, ohne DOM
 *
 * Rückgabe: 0 = alle Seiten unter dem Limit, 1 = mindestens eine darüber,
 *           2 = kein messbarer Bau (fail-closed, kein stilles Grün).
 */
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');
const DEFAULT_LIMIT = 1200;
const HARD_LIMIT = 1400;   // Lighthouse: harte Grenze, wird hier NICHT erhöht

/** jsdom liegt in tools/ff-voice-qa/node_modules (die Wurzel hält bewusst
 *  keine Node-Abhängigkeiten). Von `scripts/` aus findet die normale
 *  Auflösung es nicht – deshalb derselbe Fallback wie in ff_voice_qa_lib. */
function loadJsdom() {
  const kandidaten = [
    path.join(ROOT, 'node_modules', 'jsdom'),
    path.join(ROOT, 'tools', 'ff-voice-qa', 'node_modules', 'jsdom'),
  ];
  for (const dir of kandidaten) {
    if (fs.existsSync(path.join(dir, 'package.json'))) {
      const require = createRequire(path.join(dir, 'package.json'));
      const modul = require('jsdom');
      return modul.JSDOM || modul.default || modul;
    }
  }
  return null;
}

function seitenListe(basis) {
  const out = [];
  const lauf = (dir) => {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name);
      if (e.isDirectory()) {
        if (e.name === 'page') continue;         // Paginierung: Kopie der Vorlage
        lauf(p);
      } else if (e.name === 'index.html') {
        out.push(p);
      }
    }
  };
  lauf(basis);
  return out.sort();
}

function lokaleSkripte(doc, basis) {
  const out = [];
  for (const s of doc.querySelectorAll('script[src]')) {
    const src = s.getAttribute('src') || '';
    if (!src.startsWith('/')) continue;
    const datei = path.join(basis, decodeURIComponent(src.split('?')[0]));
    if (fs.existsSync(datei)) out.push(datei);
  }
  return out;
}

/** Misst eine Seite: ausgeliefert, zur Laufzeit, und was dazwischen liegt. */
async function messeSeite(datei, basis, JSDOM) {
  const rel = '/' + path.relative(basis, datei).replace(/index\.html$/, '');
  const dom = new JSDOM(fs.readFileSync(datei, 'utf8'), {
    url: 'https://franksfinanzcheck.de' + rel,
    runScripts: 'outside-only',      // nur die Skripte, die WIR laden
    pretendToBeVisual: true,
  });
  const { window } = dom;
  try {
    const statisch = window.document.querySelectorAll('*').length;
    for (const skript of lokaleSkripte(window.document, basis)) {
      try {
        window.eval(fs.readFileSync(skript, 'utf8'));
      } catch {
        /* Ein einzelnes defektes Skript ist ein eigener Befund (Browser-Audit),
           hier zählt die Seitenmasse. */
      }
    }
    // ff-premium.js initialisiert auf DOMContentLoaded; in jsdom ist das
    // Dokument beim Aufbau schon „complete“, das Ereignis feuert nicht mehr.
    if (!window.document.querySelector('.ff-heading-copy, .ff-mini-toc')) {
      window.document.dispatchEvent(new window.Event('DOMContentLoaded'));
    }
    await new Promise((r) => setTimeout(r, 10));
    const laufzeit = window.document.querySelectorAll('*').length;
    return {
      rel,
      statisch,
      laufzeit,
      zuwachs: laufzeit - statisch,
      ueberschriften: window.document.querySelectorAll(
        '.post-content h2[id], .post-content h3[id]').length,
      verzeichnis: window.document.querySelectorAll('.ff-mini-toc a').length,
    };
  } finally {
    window.close();
  }
}

/** Reine Bewertung – ohne DOM testbar (--selftest). */
export function bewerte(zeilen, limit = DEFAULT_LIMIT) {
  const ueber = zeilen.filter((z) => z.laufzeit > limit);
  ueber.sort((a, b) => b.laufzeit - a.laufzeit);
  const worst = zeilen.reduce((a, b) => (b.laufzeit > a.laufzeit ? b : a),
    { laufzeit: 0, rel: '—', statisch: 0, zuwachs: 0 });
  return {
    ueber, worst, limit,
    luft: limit - worst.laufzeit,              // Luft bis zur Zielmarke
    luft_hart: HARD_LIMIT - worst.laufzeit,    // Luft bis zur harten Grenze
  };
}

function selftest() {
  const faelle = [
    // [Zeilen, Limit, erwartete Zahl über dem Limit]
    [[{ rel: '/a', laufzeit: 1199, statisch: 1000, zuwachs: 199 }], 1200, 0],
    [[{ rel: '/a', laufzeit: 1200, statisch: 1000, zuwachs: 200 }], 1200, 0],
    [[{ rel: '/a', laufzeit: 1201, statisch: 1000, zuwachs: 201 }], 1200, 1],
    [[{ rel: '/a', laufzeit: 900, statisch: 800, zuwachs: 100 },
      { rel: '/b', laufzeit: 1300, statisch: 900, zuwachs: 400 },
      { rel: '/c', laufzeit: 1250, statisch: 900, zuwachs: 350 }], 1200, 2],
  ];
  let fehler = 0;
  for (const [zeilen, limit, erwartet] of faelle) {
    const erg = bewerte(zeilen, limit);
    const ok = erg.ueber.length === erwartet;
    if (!ok) fehler += 1;
    console.log(`${ok ? '✓' : '✗'} ${erg.ueber.length}/${erwartet} über ${limit}`);
  }
  console.log(fehler ? `\n❌ ${fehler} Fall/Fälle falsch` : '\n✅ Selbsttest grün.');
  return fehler ? 1 : 0;
}

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  return i >= 0 && process.argv[i + 1] ? process.argv[i + 1] : fallback;
}

async function main() {
  if (process.argv.includes('--selftest')) return selftest();

  const basis = path.resolve(ROOT, arg('--dir', 'public'));
  const limit = Number(arg('--limit', String(DEFAULT_LIMIT)));
  const top = Number(arg('--top', '10'));
  const jsonPfad = arg('--json', '');

  if (!fs.existsSync(path.join(basis, 'index.html'))) {
    console.error(`🛑 Kein messbarer Bau unter ${basis} – erst bauen (hugo --destination public).`);
    return 2;
  }
  const JSDOM = loadJsdom();
  if (!JSDOM) {
    console.error('🛑 jsdom fehlt (tools/ff-voice-qa: npm ci) – ohne DOM keine Messung, kein stilles Grün.');
    return 2;
  }

  const zeilen = [];
  for (const datei of seitenListe(basis)) {
    zeilen.push(await messeSeite(datei, basis, JSDOM));
  }
  const erg = bewerte(zeilen, limit);
  erg.zeilen = zeilen.sort((a, b) => b.laufzeit - a.laufzeit);

  console.log(`Laufzeit-DOM: ${zeilen.length} Seiten gemessen (Bau: ${path.relative(ROOT, basis)})`);
  for (const z of erg.zeilen.slice(0, top)) {
    console.log(`  ${String(z.laufzeit).padStart(5)}  ${z.rel}  `
      + `(ausgeliefert ${z.statisch}, +${z.zuwachs}, ${z.ueberschriften} Überschriften)`);
  }
  if (jsonPfad) {
    fs.mkdirSync(path.dirname(path.resolve(ROOT, jsonPfad)), { recursive: true });
    fs.writeFileSync(path.resolve(ROOT, jsonPfad), JSON.stringify({
      generated_at: new Date().toISOString(),
      limit, luft: erg.luft, worst: erg.worst, zeilen: erg.zeilen,
    }, null, 2) + '\n', 'utf8');
    console.log(`  Bericht: ${jsonPfad}`);
  }

  if (erg.ueber.length) {
    console.error(`\n❌ ${erg.ueber.length} Seite(n) über ${limit} Laufzeit-Elementen`
      + ` (Ziel: 200 Elemente Luft unter der harten Grenze 1400):`);
    for (const z of erg.ueber.slice(0, 20)) {
      console.error(`   ${z.laufzeit}  ${z.rel}`);
    }
    console.error('   Heilung: Elemente aus dem DOM nehmen, nicht das Budget erhöhen'
      + ' (Symbol per CSS-Maske, Textknoten statt <span>, s. ff-premium.js).');
    return 1;
  }
  console.log(`\n✅ Alle Seiten unter ${limit} Laufzeit-Elementen – `
    + `schwerste Seite ${erg.worst.laufzeit} (${erg.worst.rel}): `
    + `${erg.luft} Elemente Luft bis zur Zielmarke, `
    + `${erg.luft_hart} bis zur harten Grenze ${HARD_LIMIT}.`);
  return 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(fileURLToPath(import.meta.url))) {
  main().then((code) => process.exit(code)).catch((exc) => {
    console.error('🛑 Messung fehlgeschlagen:', exc && exc.stack ? exc.stack : exc);
    process.exit(3);
  });
}
