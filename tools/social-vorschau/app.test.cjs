const { test } = require('node:test');
const assert = require('node:assert/strict');
const { splitAt, befundeFuerKanal, filterSeiten, hatBefund, formatDatum } = require('./app.js');

const seite = (over = {}) => ({
  slug: 'a', url: 'https://franksfinanzcheck.de/posts/a/', titel: 'A',
  titel_og: 'A', beschreibung: 'B', bild_breite: 1200, bild_hoehe: 630,
  befunde: [{ kanal: '*', code: 'x', schwere: 'P3', detail: 'd', massnahme: 'm' },
            { kanal: 'x', code: 'y', schwere: 'P2', detail: 'd', massnahme: 'm' }],
  ...over,
});

test('splitAt: kurze Texte bleiben ganz, Zählung wie Python (Codepoints)', () => {
  assert.deepEqual(splitAt('Kurz', 10), { sichtbar: 'Kurz', rest: '', ueber: false, laenge: 4 });
  assert.equal(splitAt('😀😀😀😀', 2).sichtbar, '😀😀');
  assert.equal(splitAt('😀😀😀😀', 2).laenge, 4);
});
test('splitAt: zu langer Text wird an einer Wortgrenze geteilt', () => {
  const r = splitAt('Strom sparen im Haushalt', 12);
  assert.equal(r.ueber, true);
  // Grenze 12 liegt genau auf dem Leerzeichen: die sichtbare Zeile endet
  // mit dem vollständigen Wort, nicht mit einem halben.
  assert.equal(r.sichtbar, 'Strom sparen');
  assert.equal((r.sichtbar + r.rest).replace(/\s+/g, ' ').trim(), 'Strom sparen im Haushalt');
});
test('splitAt: kein Leerzeichen in Sichtweite → harte Grenze', () => {
  assert.equal(splitAt('Donaudampfschifffahrt', 6).sichtbar, 'Donaud');
});
test('Kanalfilter: kanalunabhängige und eigene Befunde, keine fremden', () => {
  const b = befundeFuerKanal(seite().befunde, 'x');
  assert.deepEqual(b.map(x => x.code), ['x', 'y']);
  assert.deepEqual(befundeFuerKanal(seite().befunde, 'linkedin').map(x => x.code), ['x']);
});
test('Kanalfilter: `ausser` schließt einen Kanal aus (Hochformat/Pinterest)', () => {
  const hochformat = [{ kanal: '*', code: 'social-bild-format', schwere: 'P3',
                        detail: 'Hochformat', massnahme: 'm', ausser: ['pinterest'] }];
  assert.equal(befundeFuerKanal(hochformat, 'x').length, 1);
  assert.equal(befundeFuerKanal(hochformat, 'pinterest').length, 0);
  assert.equal(hatBefund({ befunde: hochformat }, 'pinterest'), false);
});
test('Filter: Suche, nur Befunde (kanalspezifisch), ohne Bild', () => {
  const pages = [seite(), seite({ slug: 'b', titel_og: 'B', bild_breite: null, befunde: [] })];
  assert.equal(filterSeiten(pages, { suche: 'b' }).length, 1);
  assert.equal(filterSeiten(pages, { filter: 'ohne-bild' }).length, 1);
  assert.equal(filterSeiten(pages, { filter: 'befunde', kanal: 'linkedin' }).length, 1);
  assert.equal(filterSeiten(pages, { filter: 'befunde', kanal: 'linkedin' })[0].slug, 'a');
  assert.equal(hatBefund(pages[1], 'x'), false);
});
test('Datum: ungültige Werte werden nicht erfunden', () => {
  assert.equal(formatDatum('kein Datum'), 'unbekannt');
  assert.match(formatDatum('2026-10-28T09:00:00Z'), /\d{2}\./);
});
