// ============================================================
//  TESTS: LIGHTHOUSE LIVE (scripts/lighthouse_live.mjs)
//  ------------------------------------------------------------
//  Der Vertrag in fünf Sätzen (26.10.2026 · gehärtet 03.11.2026, #1026):
//    1. Schwellen kommen ausschließlich aus lighthouse/assertions.json –
//       es gibt keine zweite Zahl im Skript, und eine leere Datei ist ein
//       Fehler (nie Scheingrün).
//    2. Aggregiert wird mit der Methode, die in der Assertion steht
//       (median / pessimistic / optimistic) – nicht mit der bequemsten.
//    3. Ein Audit, das der Lauf nicht liefert, ist ein Befund
//       (NICHT_GEMESSEN), kein stilles Grün.
//    4. Ein Befund macht den Lauf nur mit `--streng` rot: Laborwerte sind
//       Diagnose, verbindlich sind die Felddaten (cwv_feld_wache.py).
//    5. Import, Auswertung und `--selftest` laufen ohne Netz und ohne
//       `node_modules` – Browser und Lighthouse werden erst beim echten
//       Messlauf dynamisch geladen (#1026).
// ============================================================

import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';

import {
  argumente,
  baueZielUrl,
  bericht,
  laborScores,
  ladeAssertions,
  main,
  messeUrl,
  messwert,
  mittelwerte,
  pruefeAssertions,
  selftest,
  zieleAusDatei,
} from '../lighthouse_live.mjs';

const SKRIPT_PFAD = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'lighthouse_live.mjs');

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

test('Sabotage-Schutz: leere oder fehlende Schwellen werfen statt Scheingrün zu liefern', () => {
  const tmp = mkdtempSync(path.join(os.tmpdir(), 'lh-assertions-test-'));
  try {
    const leer = path.join(tmp, 'leer.json');
    writeFileSync(leer, JSON.stringify({ assertions: {} }), 'utf8');
    assert.throws(() => ladeAssertions(leer), /leer/);
    const ohne = path.join(tmp, 'ohne.json');
    writeFileSync(ohne, JSON.stringify({}), 'utf8');
    assert.throws(() => ladeAssertions(ohne), /fehlt oder ist leer/);
    assert.throws(() => pruefeAssertions([LCP(1200)], {}), /Scheingrün/);
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
});

test('Zielliste liest data/cwv/feld_ziele.json und lehnt leere oder relative Pfade ab', () => {
  const ziele = zieleAusDatei();
  assert.ok(ziele.length >= 3);
  assert.ok(ziele.every((p) => p.startsWith('/')));

  const tmp = mkdtempSync(path.join(os.tmpdir(), 'lh-ziele-test-'));
  try {
    const leer = path.join(tmp, 'leer.json');
    writeFileSync(leer, JSON.stringify({ ziele: [] }), 'utf8');
    assert.throws(() => zieleAusDatei(leer), /leer/);

    const relativ = path.join(tmp, 'relativ.json');
    writeFileSync(relativ, JSON.stringify({ ziele: [{ pfad: 'werkzeuge/' }] }), 'utf8');
    assert.throws(() => zieleAusDatei(relativ), /absoluten Pfad/);
  } finally {
    rmSync(tmp, { recursive: true, force: true });
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

test('Aggregation: median, pessimistic, optimistic – und Fehler bei leerem Satz', () => {
  assert.equal(mittelwerte([3000, 1000, 2000], 'median'), 2000);
  assert.equal(mittelwerte([3000, 1000], 'median'), 2000);
  assert.equal(mittelwerte([3000, 1000, 2000], 'pessimistic'), 3000);
  assert.equal(mittelwerte([3000, 1000, 2000], 'optimistic'), 1000);
  assert.throws(() => mittelwerte([], 'median'), /mindestens einen/);
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

test('Argumente: Ziele, Läufe, Schalter – und Klartext bei fehlendem Wert oder Fremdschema', async () => {
  const opt = argumente(['--url', 'https://x.de/', '--url', '/cockpit/', '--laeufe', '3', '--streng', '--json']);
  assert.deepEqual(opt.urls, ['https://x.de/', '/cockpit/']);
  assert.equal(opt.laeufe, 3);
  assert.equal(opt.streng, true);
  assert.equal(opt.json, true);
  assert.equal(baueZielUrl('/cockpit/', 'https://x.de/'), 'https://x.de/cockpit/');
  assert.throws(() => argumente(['--laeufe', '0']), /1 bis 5/);
  assert.throws(() => argumente(['--laeufe']), /erwartet einen Wert/);
  assert.throws(() => argumente(['--url']), /erwartet einen Wert/);
  assert.throws(() => argumente(['--url', '--streng']), /erwartet einen Wert/);
  assert.throws(() => argumente(['--basis']), /erwartet einen Wert/);
  assert.throws(() => argumente(['--url', 'file:///etc/passwd']), /http/);
  assert.throws(() => argumente(['--basis', 'javascript:alert(1)']), /http/);
  assert.throws(() => argumente(['--unfug']), /Unbekanntes Argument/);
  assert.equal(await main(['--unfug']), 2);
  assert.equal(await main(['--hilfe']), 0);
});

test('messeUrl ruft die übergebene Lighthouse-Funktion je Lauf auf und lehnt leere Antworten ab', async () => {
  const aufrufe = [];
  const attrappe = async (url, cfg) => {
    aufrufe.push({ url, port: cfg.port, formFactor: cfg.formFactor });
    return { lhr: lauf({ scores: { performance: 0.96 } }) };
  };
  const ergebnisse = await messeUrl('https://franksfinanzcheck.de/', 9444, 2, attrappe);
  assert.equal(ergebnisse.length, 2);
  assert.equal(aufrufe.length, 2);
  assert.equal(aufrufe[0].port, 9444);
  assert.equal(aufrufe[0].formFactor, 'mobile');
  await assert.rejects(() => messeUrl('https://franksfinanzcheck.de/', 9444, 1, async () => null), /kein Ergebnis/);
});

test('#1026 Regressionsschutz: keine statischen Top-Level-Imports auf Fremdpakete, Selbsttest grün', async () => {
  const codeOhneKommentare = readFileSync(SKRIPT_PFAD, 'utf8')
    .split('\n')
    .filter((zeile) => !zeile.trimStart().startsWith('//') && !zeile.trimStart().startsWith('#!'))
    .join('\n');
  for (const zeile of codeOhneKommentare.split('\n')) {
    if (/^\s*import\s+.*from\s+/.test(zeile)) {
      assert.match(zeile, /from\s+['"]node:/,
        `Statischer Top-Level-Import außerhalb der Node-Standardbibliothek gefunden (#1026): ${zeile}`);
    }
  }
  assert.equal(await selftest(), 0);
  assert.equal(await main(['--selftest']), 0);
});

test('--json liefert reines JSON auf stdout – Fortschritt geht auf stderr', async () => {
  const logs = [];
  const errs = [];
  const origLog = console.log;
  const origErr = console.error;
  console.log = (...a) => logs.push(a.join(' '));
  console.error = (...a) => errs.push(a.join(' '));
  try {
    const code = await main(
      ['--url', 'https://franksfinanzcheck.de/werkzeuge/', '--laeufe', '1', '--json'],
      async () => ({
        resolveLaunchOptions: async () => ({}),
        chromium: { launch: async () => ({ close: async () => {} }) },
        lighthouse: async () => ({ lhr: lauf({ scores: { performance: 0.99, accessibility: 1, 'best-practices': 1, seo: 1 } }) }),
      }),
    );
    assert.equal(code, 0);
    const geparst = JSON.parse(logs.join('\n'));
    assert.equal(geparst.seiten.length, 1);
    assert.equal(geparst.seiten[0].pfad, '/werkzeuge/');
    assert.ok(errs.some((z) => z.includes('/werkzeuge/')));
  } finally {
    console.log = origLog;
    console.error = origErr;
  }
});
