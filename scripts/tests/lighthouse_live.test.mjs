// ============================================================
//  TESTS: LIGHTHOUSE LIVE (scripts/lighthouse_live.mjs)
//  ------------------------------------------------------------
//  Der Vertrag in sechs Sätzen (26.10.2026, erweitert 04.11.2026):
//    1. Schwellen kommen ausschließlich aus lighthouse/assertions.json –
//       es gibt keine zweite Zahl im Skript.
//    2. Aggregiert wird mit der Methode, die in der Assertion steht
//       (median / pessimistic / optimistic) – nicht mit der bequemsten.
//    3. Ein Audit, das der Lauf nicht liefert, ist ein Befund
//       (NICHT_GEMESSEN), kein stilles Grün.
//    4. Ein Befund macht den Lauf nur mit `--streng` rot: Laborwerte sind
//       Diagnose, verbindlich sind die Felddaten (cwv_feld_wache.py).
//    5. Das Modul ist in einem NACKTEN Checkout importierbar: keine
//       Laufzeitpakete am Modulkopf, `--selftest` läuft ohne `node_modules`.
//       (#1026: Daran starb der Wochenlauf VOR `npm ci`.)
//    6. `--json` schreibt ausschließlich JSON auf `stdout`; Fortschritt
//       gehört auf `stderr`, sonst kann niemand die Ausgabe parsen.
// ============================================================

import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  LaufzeitFehler,
  anzeigepfad,
  argumente,
  bericht,
  laborScores,
  ladeAssertions,
  ladeLaufzeit,
  messOptionen,
  messeUrl,
  messwert,
  mittelwerte,
  pruefeAssertions,
  zieleAusDatei,
} from '../lighthouse_live.mjs';

const HIER = path.dirname(fileURLToPath(import.meta.url));
const SKRIPT = path.resolve(HIER, '..', 'lighthouse_live.mjs');

/** Minimaler Lauf, wie ihn Lighthouse liefert (nur die gelesenen Felder). */
function lauf({ scores = {}, audits = {} } = {}) {
  const kategorien = {};
  for (const [name, score] of Object.entries(scores)) kategorien[name] = { score };
  return { categories: kategorien, audits };
}

const LCP = (ms) => ({ audits: { 'largest-contentful-paint': { numericValue: ms, numericUnit: 'millisecond' } } });

test('Schwellen sind die eine Wahrheit aus lighthouse/assertions.json', () => {
  const assertions = ladeAssertions();
  assert.ok(Object.keys(assertions).length >= 6, 'zu wenige Assertions gelesen');
  assert.deepEqual(assertions['categories:performance'][1], { minScore: 0.9 });
  assert.equal(assertions['largest-contentful-paint'][1].maxNumericValue, 2500);
});

test('kaputte Schwellendatei ist ein Klartext-Fehler, kein stilles Grün', () => {
  const leer = mkdtempSync(path.join(tmpdir(), 'lh-assertions-'));
  try {
    const datei = path.join(leer, 'assertions.json');
    assert.throws(() => ladeAssertions(path.join(leer, 'fehlt.json')), /ENOENT|no such file/i);
    writeFileSync(datei, JSON.stringify({ assertions: [] }), 'utf8');
    assert.throws(() => ladeAssertions(datei), /"assertions" fehlt oder ist kein Objekt/);
  } finally {
    rmSync(leer, { recursive: true, force: true });
  }
});

test('Zielliste aus der Datei trägt nur absolute Pfade', () => {
  const pfade = zieleAusDatei();
  assert.ok(pfade.length >= 3, 'zu wenige Ziele');
  for (const p of pfade) assert.ok(p.startsWith('/'), `Ziel ohne Schrägstrich: ${p}`);
});

test('kaputte Zielliste ist ein Klartext-Fehler', () => {
  const leer = mkdtempSync(path.join(tmpdir(), 'lh-ziele-'));
  try {
    const datei = path.join(leer, 'ziele.json');
    writeFileSync(datei, JSON.stringify({ ziele: [{ pfad: 'cockpit/' }] }), 'utf8');
    assert.throws(() => zieleAusDatei(datei), /ohne absoluten Pfad/);
    writeFileSync(datei, JSON.stringify({ ziele: [] }), 'utf8');
    assert.throws(() => zieleAusDatei(datei), /fehlt oder ist leer/);
  } finally {
    rmSync(leer, { recursive: true, force: true });
  }
});

test('Kategorie-Score wird als 0…1 gelesen, nicht als Prozentwert', () => {
  const lhr = lauf({ scores: { performance: 0.93 } });
  assert.deepEqual(messwert(lhr, 'categories:performance'), { wert: 0.93, einheit: 'score' });
});

test('numerische Audits liefern Wert und Einheit', () => {
  assert.deepEqual(messwert(LCP(1800), 'largest-contentful-paint'),
    { wert: 1800, einheit: 'millisecond' });
});

test('fehlendes Audit ist null – kein erfundenes Grün', () => {
  assert.equal(messwert(lauf(), 'largest-contentful-paint'), null);
  assert.equal(messwert(lauf(), 'categories:seo'), null);
});

test('Lighthouse-13-Umbenennung dom-size → dom-size-insight wird übersetzt', () => {
  const lhr = lauf({ scores: {}, audits: { 'dom-size-insight': { numericValue: 900, numericUnit: 'element' } } });
  assert.deepEqual(messwert(lhr, 'dom-size'), { wert: 900, einheit: 'element' });
});

test('Aggregation: median, pessimistic, optimistic', () => {
  assert.equal(mittelwerte([3000, 1000, 2000], 'median'), 2000);
  assert.equal(mittelwerte([3000, 1000], 'median'), 2000);
  assert.equal(mittelwerte([3000, 1000, 2000], 'pessimistic'), 3000);
  assert.equal(mittelwerte([3000, 1000, 2000], 'optimistic'), 1000);
});

test('gerissene Grenze wird benannt (Wert, Grenze, Methode)', () => {
  const befunde = pruefeAssertions([LCP(4200)], {
    'largest-contentful-paint': ['error', { maxNumericValue: 2500, aggregationMethod: 'median' }],
  });
  assert.equal(befunde.length, 1);
  assert.equal(befunde[0].urteil, 'UEBER_SCHWELLE');
  assert.match(befunde[0].text, /4200 > 2500/);
  assert.match(befunde[0].text, /median/);
});

test('eingehaltene Grenze ergibt keinen Befund', () => {
  assert.deepEqual(pruefeAssertions([LCP(1200)],
    { 'largest-contentful-paint': ['error', { maxNumericValue: 2500 }] }), []);
});

test('Score unter minScore ist ein Befund', () => {
  const befunde = pruefeAssertions([lauf({ scores: { accessibility: 0.91 } })],
    { 'categories:accessibility': ['error', { minScore: 0.95 }] });
  assert.equal(befunde.length, 1);
  assert.equal(befunde[0].urteil, 'UNTER_SCHWELLE');
});

test('nicht geliefertes Audit ist NICHT_GEMESSEN – und niemals grün', () => {
  const befunde = pruefeAssertions([lauf()], { 'total-blocking-time': ['error', { maxNumericValue: 200 }] });
  assert.equal(befunde.length, 1);
  assert.equal(befunde[0].urteil, 'NICHT_GEMESSEN');
});

test('pruefeAssertions ohne Lauf ist ein Fehler, kein leeres Grün', () => {
  assert.throws(() => pruefeAssertions([], {}), /mindestens einen Lauf/);
});

test('Labor-Scores werden als ganze Prozentpunkte gelesen', () => {
  const scores = laborScores(lauf({ scores: {
    performance: 0.99, accessibility: 1, 'best-practices': 1, seo: 1,
  } }));
  assert.deepEqual(scores, { performance: 99, accessibility: 100, 'best-practices': 100, seo: 100 });
});

test('Bericht nennt jede Seite und jede gerissene Schwelle', () => {
  const text = bericht([
    { pfad: '/', scores: { performance: 99, accessibility: 100, 'best-practices': 100, seo: 100 }, befunde: [] },
    { pfad: '/werkzeuge/', scores: { performance: 71, accessibility: 100, 'best-practices': 100, seo: 100 },
      befunde: [{ text: 'categories:performance: 0.71 < 0.9 (minScore, median)' }] },
  ], '2026-10-26');
  assert.match(text, /\| `\/` \| im Rahmen \| 99 \| 100 \| 100 \| 100 \|/);
  assert.match(text, /1 Befund\(e\)/);
  assert.match(text, /## Gerissene Schwellen/);
  assert.match(text, /0\.71 < 0\.9/);
});

test('Anzeigepfad ist ortsunabhängig (Basis, lokal, fremde URL)', () => {
  assert.equal(anzeigepfad('https://franksfinanzcheck.de/werkzeuge/', 'https://franksfinanzcheck.de'), '/werkzeuge/');
  assert.equal(anzeigepfad('https://franksfinanzcheck.de/', 'https://franksfinanzcheck.de/'), '/');
  assert.equal(anzeigepfad('http://127.0.0.1:1313/cockpit/?x=1', 'https://franksfinanzcheck.de'), '/cockpit/?x=1');
});

test('Argumente: Ziele, Läufe, Schalter – und Klartext bei Unsinn', () => {
  const opt = argumente(['--url', 'https://x.de/', '--laeufe', '3', '--streng', '--json']);
  assert.deepEqual(opt.urls, ['https://x.de/']);
  assert.equal(opt.laeufe, 3);
  assert.equal(opt.streng, true);
  assert.equal(opt.json, true);
  assert.equal(opt.selftest, false);
  assert.throws(() => argumente(['--laeufe', '0']), /1 bis 5/);
  assert.throws(() => argumente(['--laeufe', 'zwei']), /1 bis 5/);
  assert.throws(() => argumente(['--unfug']), /Unbekanntes Argument/);
  assert.throws(() => argumente(['--url', '--json']), /braucht einen Wert/);
  assert.throws(() => argumente(['--basis', 'ftp://x.de']), /absolute http/);
  assert.throws(() => argumente(['--url', 'kein/pfad']), /absolute URL oder ein Pfad/);
  assert.equal(argumente(['--selftest']).selftest, true);
});

test('Messoptionen sind reproduzierbar (Mobile-Emulation, DevTools-Port)', () => {
  const opt = messOptionen(9222);
  assert.equal(opt.port, 9222);
  assert.equal(opt.formFactor, 'mobile');
  assert.equal(opt.screenEmulation.width, 390);
  assert.equal(opt.output, 'json');
});

test('messeUrl zählt die Läufe, misst genau diese URL und gibt lhr weiter', async () => {
  const gesehen = [];
  const messer = async (url, port) => {
    gesehen.push([url, port]);
    return { lhr: { marker: gesehen.length } };
  };
  const laeufe = await messeUrl('https://x.de/', 4711, 3, messer);
  assert.equal(laeufe.length, 3);
  assert.deepEqual(laeufe.map((l) => l.marker), [1, 2, 3]);
  assert.deepEqual(gesehen, [
    ['https://x.de/', 4711], ['https://x.de/', 4711], ['https://x.de/', 4711],
  ]);
});

test('messeUrl ohne Ergebnis ist ein Fehler – niemals ein leeres Grün', async () => {
  await assert.rejects(() => messeUrl('https://x.de/', 1, 1, async () => ({})), /kein Ergebnis/);
  await assert.rejects(() => messeUrl('https://x.de/', 1, 0, async () => ({ lhr: {} })), /ganze Zahl/);
  await assert.rejects(() => messeUrl('https://x.de/', 1, 1, undefined), /Messfunktion/);
});

test('fehlende Laufzeitpakete werden als Klartext-Fehler mit Abhilfe gemeldet', async () => {
  const fehler = await ladeLaufzeit(async () => {
    throw new Error('Cannot find package \'lighthouse\'');
  }).then(() => null, (e) => e);
  assert.ok(fehler instanceof LaufzeitFehler, 'kein LaufzeitFehler');
  assert.match(fehler.message, /npm ci --ignore-scripts/);
  assert.match(fehler.message, /lighthouse/);
});

test('Laufzeit lässt sich vollständig injizieren (kein Paket nötig)', async () => {
  const laufzeit = await ladeLaufzeit(async (name) => {
    if (name === 'lighthouse') return { default: async () => ({ lhr: {} }) };
    if (name === 'playwright-core') return { chromium: { launch: async () => ({ close: async () => {} }) } };
    return { resolveLaunchOptions: async () => ({}) };
  });
  assert.equal(typeof laufzeit.lighthouse, 'function');
  assert.equal(typeof laufzeit.chromium.launch, 'function');
  assert.equal(typeof laufzeit.resolveLaunchOptions, 'function');
});

test('Der Modulkopf verkauft keine Laufzeitpakete als Voraussetzung (#1026)', () => {
  // Der eigentliche #1026-Beweis steht in der Struktur: Waeren 'lighthouse',
  // 'playwright-core' oder '../e2e/browser.mjs' statisch am Modulkopf
  // importiert, haette Node diese Testdatei in einem Checkout ohne
  // `node_modules` gar nicht erst laden koennen – mit ERR_MODULE_NOT_FOUND,
  // genau wie im Wochenlauf 41456548199. Der Test beweist die Gegenwart des
  // Fehlers, der Struktur-Test unten die Abwesenheit des Musters.
  assert.equal(typeof ladeLaufzeit, 'function');
  const quelle = readFileSync(SKRIPT, 'utf8');
  const statisch = quelle
    .split('\n')
    .filter((zeile) => /^\s*import\s/.test(zeile))
    .join('\n');
  assert.doesNotMatch(statisch, /from\s+['"]lighthouse['"]/, 'lighthouse wird statisch importiert');
  assert.doesNotMatch(statisch, /from\s+['"]playwright-core['"]/, 'playwright-core wird statisch importiert');
  assert.doesNotMatch(statisch, /from\s+['"]\.\.\/e2e\/browser\.mjs['"]/, 'e2e/browser.mjs wird statisch importiert');
  for (const zeile of statisch.split('\n').filter(Boolean)) {
    assert.match(zeile, /from\s+['"](node:|\.[^'"]*lighthouse_live)/,
      `Fremdpaket am Modulkopf: ${zeile.trim()}`);
  }
});

test('--selftest läuft offline, ohne Pakete und ohne Browser (Exit 0)', () => {
  const ergebnis = spawnSync(process.execPath, [SKRIPT, '--selftest'], {
    encoding: 'utf8', timeout: 60_000,
  });
  assert.equal(ergebnis.status, 0, `${ergebnis.stdout}\n${ergebnis.stderr}`);
  assert.match(ergebnis.stdout, /Selbsttest grün/);
});

test('--json schreibt ausschließlich JSON auf stdout (ohne Browser: Exit 2, stderr)', () => {
  // Ohne Chromium ist der Lauf nicht durchführbar – der Fehler muss auf
  // stderr landen und Exit 2 tragen; stdout bleibt ein leerer Datenstrom
  // bzw. reines JSON. Eine Fortschrittszeile auf stdout wäre der Befund.
  const ergebnis = spawnSync(process.execPath, [SKRIPT, '--json', '--url', '/', '--laeufe', '1'], {
    encoding: 'utf8', timeout: 120_000,
  });
  assert.ok([0, 2].includes(ergebnis.status), `unerwarteter Exit ${ergebnis.status}`);
  const ausgabe = ergebnis.stdout.trim();
  if (ausgabe) {
    assert.doesNotThrow(() => JSON.parse(ausgabe), 'stdout ist kein reines JSON');
  }
  if (ergebnis.status === 2) {
    assert.match(ergebnis.stderr, /🛑/);
  }
});
