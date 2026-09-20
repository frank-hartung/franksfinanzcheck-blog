const { test } = require('node:test');
const assert = require('node:assert/strict');
const { parseCSV, parseGSC } = require('./app.js');

test('CSV: BOM, Semikolon, escaped quotes, mehrzeilige Felder', () => {
  assert.deepEqual(parseCSV('\uFEFFA;B\r\n"a;""b""\nc";2\r\n'), [['A', 'B'], ['a;"b"\nc', '2']]);
});
test('CSV: ungeschlossene und ungültige Quotes ablehnen', () => {
  assert.throws(() => parseCSV('A,B\n"offen,2'), /Anführungszeichen/);
  assert.throws(() => parseCSV('A,B\n"zu"kaputt,2'), /Ungültige CSV/);
});
test('GSC Deutsch: Tausender und Dezimalkomma, CTR selbst berechnen', () => {
  const [r] = parseGSC('Häufigste Suchanfragen;Klicks;Impressionen;CTR;Position\n"strom; sparen";12;1.234;99%;7,5');
  assert.equal(r.impressions, 1234); assert.equal(r.position, 7.5); assert.equal(r.ctr, 12 / 1234);
});
test('GSC Englisch: Pages export', () => {
  const [r] = parseGSC('Top pages,Clicks,Impressions,CTR,Position\nhttps://example.org/,15,"1,234",1%,8.2');
  assert.equal(r.kind, 'page'); assert.equal(r.impressions, 1234); assert.equal(r.position, 8.2);
});
test('GSC: Tabs und Nullklicks', () => {
  assert.equal(parseGSC('Query\tClicks\tImpressions\tPosition\nabc\t0\t100\t10')[0].ctr, 0);
});
test('GSC: falscher Export und fehlende Spalten', () => {
  assert.throws(() => parseGSC('Date,Clicks,Impressions,Position\n2026-09-01,1,100,10'), /Benötigt/);
  assert.throws(() => parseGSC('Query,Clicks\nabc,1'), /Benötigt/);
});
test('GSC: leere Exporte', () => {
  assert.throws(() => parseGSC('Query,Clicks,Impressions,Position\n'), /keine Datenzeilen/);
});
test('GSC: fehlerhafte Zahlen, zu viele Klicks und Spaltenzahl', () => {
  for (const row of ['abc,-1,100,8', 'abc,,100,8', 'abc,NaN,100,8', 'abc,101,100,8', 'abc,1,100,0', 'abc,1.5,100,8', 'abc,1,100,8,extra', ',1,100,8', 'abc,1,100,Infinity']) {
    assert.throws(() => parseGSC('Query,Clicks,Impressions,Position\n' + row));
  }
});
test('Import bewahrt Text unverändert; UI rendert ausschließlich textContent', () => {
  assert.equal(parseGSC('Query,Clicks,Impressions,Position\n<img src=x onerror=alert(1)>,1,100,8')[0].label, '<img src=x onerror=alert(1)>');
});
