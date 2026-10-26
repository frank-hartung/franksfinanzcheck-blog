// ============================================================
//  TESTS: LIGHTHOUSE LIVE (scripts/lighthouse_live.mjs)
//  ------------------------------------------------------------
//  Der Vertrag in vier Sätzen (26.10.2026):
//    1. Schwellen kommen ausschließlich aus lighthouse/assertions.json –
//       es gibt keine zweite Zahl im Skript.
//    2. Aggregiert wird mit der Methode, die in der Assertion steht
//       (median / pessimistic / optimistic) – nicht mit der bequemsten.
//    3. Ein Audit, das der Lauf nicht liefert, ist ein Befund
//       (NICHT_GEMESSEN), kein stilles Grün.
//    4. Ein Befund macht den Lauf nur mit `--streng` rot: Laborwerte sind
//       Diagnose, verbindlich sind die Felddaten (cwv_feld_wache.py).
// ============================================================

import assert from 'node:assert/strict';
import { test } from 'node:test';

import {
  argumente,
  bericht,
  laborScores,
  ladeAssertions,
  messwert,
  mittelwerte,
  pruefeAssertions,
} from '../lighthouse_live.mjs';

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

test('Argumente: Ziele, Läufe, Schalter – und Klartext bei Unsinn', () => {
  const opt = argumente(['--url', 'https://x.de/', '--laeufe', '3', '--streng', '--json']);
  assert.deepEqual(opt.urls, ['https://x.de/']);
  assert.equal(opt.laeufe, 3);
  assert.equal(opt.streng, true);
  assert.equal(opt.json, true);
  assert.throws(() => argumente(['--laeufe', '0']), /1 bis 5/);
  assert.throws(() => argumente(['--unfug']), /Unbekanntes Argument/);
});
