// Regressionstest für den Rechenkern der Werkzeuge (static/premium/ff-werkzeuge.js).
// ===================================================================
// Zwei Ebenen, bewusst getrennt:
//
//   1. RECHENKERN ohne DOM. Jede Engine ist eine reine Funktion
//      logik[engine](felder, {heute}) – der Test baut die Felder direkt
//      und prüft Zahlen, Reihenfolge und Grenzfälle. Hier gehören die
//      Formeln aus data/werkzeuge.yaml hin, sonst nirgends.
//
//   2. DOM-ANBINDUNG mit jsdom. Das Test-DOM spiegelt die Struktur von
//      layouts/_partials/ff_werkzeug.html (nur data-*-Haken, keine
//      Klassen) – so fängt der Test auch Struktur-Regressionen.
//
// Zusätzlich prüft der erste Block, dass JS und SSOT dieselben Engines
// kennen: eine neue Engine in data/werkzeuge.yaml ohne Implementierung
// (oder umgekehrt) lässt den Test fehlschlagen.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SKRIPT = fs.readFileSync(path.join(ROOT, 'static/premium/ff-werkzeuge.js'), 'utf8');
const SSOT = fs.readFileSync(path.join(ROOT, 'data/werkzeuge.yaml'), 'utf8');

/** Lädt den Produktionscode ohne Browser – die Datei fasst document nur an, wenn es existiert. */
function ladeKern() {
  const sandbox = {};
  // eslint-disable-next-line no-new-func
  new Function('globalThis', `${SKRIPT}\n;return globalThis.FFWerkzeuge;`)(sandbox);
  return sandbox.FFWerkzeuge;
}

const FF = ladeKern();
const { logik, hilfen, exporte } = FF;

/** Baut einen Feld-Eintrag so, wie felderLesen() ihn aus dem Markup erzeugt. */
function f(id, wert, extra = {}) {
  const typ = extra.typ || 'euro';
  const eintrag = {
    id,
    label: extra.label || id,
    typ,
    einheit: extra.einheit || '',
    bucket: extra.bucket || '',
    korridor: extra.korridor || null,
    pflicht: extra.pflicht !== false,
    wert: wert == null ? '' : String(wert),
    zahl: typ === 'datum' || typ === 'auswahl' ? NaN : hilfen.zahl(wert),
  };
  if (typ === 'auswahl') {
    eintrag.auswahlLabel = extra.auswahlLabel || String(wert);
    eintrag.auswahlZahl = extra.auswahlZahl == null ? NaN : extra.auswahlZahl;
  }
  return eintrag;
}

/** Erste Zahl aus einem formatierten Text ("1.350,00 €" -> 1350). */
function betrag(text) {
  const treffer = String(text).match(/-?\d[\d.]*(?:,\d+)?/);
  return treffer ? Number(treffer[0].replace(/\./g, '').replace(',', '.')) : NaN;
}

function kennzahl(ergebnis, label) {
  const k = ergebnis.kennzahlen.find((e) => e.label.startsWith(label));
  assert.ok(k, `Kennzahl "${label}" fehlt – vorhanden: ${ergebnis.kennzahlen.map((e) => e.label).join(', ')}`);
  return k;
}

function zeile(ergebnis, label) {
  const z = (ergebnis.zeilen || []).find((e) => e.label.startsWith(label));
  assert.ok(z, `Zeile "${label}" fehlt`);
  return z;
}

const HEUTE = new Date(2026, 9, 2, 12, 0, 0, 0); // 02.10.2026, fester Testtag

// ===================================================================
// 0. Vertrag zwischen SSOT und Rechenkern
// ===================================================================

test('jede Engine aus data/werkzeuge.yaml ist implementiert – und keine mehr', () => {
  const ausSsot = [...SSOT.matchAll(/^\s*engine:\s*"?([a-z0-9_]+)"?\s*$/gm)].map((m) => m[1]).sort();
  const imKern = Object.keys(logik).sort();
  assert.equal(ausSsot.length, 8, 'Die SSOT soll genau acht Werkzeuge beschreiben.');
  assert.deepEqual(imKern, ausSsot);
});

test('die öffentliche API bleibt stabil', () => {
  assert.equal(typeof FF.felderLesen, 'function');
  assert.equal(typeof FF.start, 'function');
  for (const name of ['zahl', 'euro', 'nummer', 'prozent', 'datumLesen', 'datumFormat', 'iso', 'monatePlus', 'tagePlus', 'dauerText']) {
    assert.equal(typeof hilfen[name], 'function', `hilfen.${name} fehlt`);
  }
  for (const name of ['csv', 'pdf', 'ics', 'csvAusModell', 'pdfAusModell', 'modell']) {
    assert.equal(typeof exporte[name], 'function', `exporte.${name} fehlt`);
  }
});

test('der Produktionscode enthält keinen Netzaufruf', () => {
  // Der Kopfkommentar nennt die verbotenen Muster beim Namen – geprüft wird
  // deshalb der Code darunter, nicht die Dokumentation darüber.
  const code = SKRIPT.slice(SKRIPT.indexOf('(function ()'));
  for (const verboten of ['fetch(', 'XMLHttpRequest', 'sendBeacon', 'WebSocket', 'innerHTML', 'document.write']) {
    assert.ok(!code.includes(verboten), `Verbotenes Muster im Rechenkern: ${verboten}`);
  }
});

// ===================================================================
// 1. Zahlen und Datum
// ===================================================================

test('deutsche Zahleneingaben werden robust gelesen', () => {
  assert.equal(hilfen.zahl('1.234,56'), 1234.56);
  assert.equal(hilfen.zahl('1 234,56 €'), 1234.56);
  assert.equal(hilfen.zahl('36,8'), 36.8);
  assert.equal(hilfen.zahl('2.000'), 2000);
  assert.equal(hilfen.zahl('12'), 12);
  assert.ok(Number.isNaN(hilfen.zahl('')));
  assert.ok(Number.isNaN(hilfen.zahl('keine Zahl')));
  assert.ok(Number.isNaN(hilfen.zahl('99999999999')), 'Absurd große Beträge gelten als Tippfehler.');
});

test('Monatsfristen werden kalendarisch gekappt', () => {
  // 31.05. minus 3 Monate ist der 28.02. – nicht der 31.02. und nicht der 03.03.
  const ende = hilfen.datumLesen('2027-05-31');
  assert.equal(hilfen.iso(hilfen.monatePlus(ende, -3)), '2027-02-28');
  const schaltjahr = hilfen.datumLesen('2028-05-31');
  assert.equal(hilfen.iso(hilfen.monatePlus(schaltjahr, -3)), '2028-02-29');
  assert.equal(hilfen.iso(hilfen.monatePlus(hilfen.datumLesen('2026-01-15'), 13)), '2027-02-15');
});

test('dauerText formuliert Monate menschlich', () => {
  assert.equal(hilfen.dauerText(1), '1 Monat');
  assert.equal(hilfen.dauerText(11), '11 Monate');
  assert.equal(hilfen.dauerText(12), '1 Jahr');
  assert.equal(hilfen.dauerText(25), '2 Jahre und 1 Monat');
});

// ===================================================================
// 2. Fixkosten-Scanner
// ===================================================================

test('Scanner summiert, rechnet hoch und sortiert nach Betrag', () => {
  const ergebnis = logik.scanner([
    f('wohnen', '1200', { label: 'Wohnen', korridor: [0, 0.02] }),
    f('energie', '150', { label: 'Energie', korridor: [0.08, 0.25] }),
    f('kommunikation', '60', { label: 'Kommunikation', korridor: [0.15, 0.4] }),
    f('einkommen', '3000', { label: 'Haushaltsnetto', optional: true }),
  ]);
  assert.ok(!ergebnis.fehler);
  assert.equal(betrag(kennzahl(ergebnis, 'Laufende Kosten').wert), 1410);
  assert.equal(betrag(kennzahl(ergebnis, 'Hochgerechnet').wert), 16920);
  assert.equal(betrag(kennzahl(ergebnis, 'Fixkostenquote').wert), 47);
  assert.deepEqual(ergebnis.liste.map((l) => l.label), ['Wohnen', 'Energie', 'Kommunikation']);
  // Spielraum: 1200*12*0 + 150*12*0,08 + 60*12*0,15 = 252 … 288 + 450 + 288 = 1026
  assert.equal(betrag(zeile(ergebnis, 'Spielraum untere').wert), 252);
  assert.equal(betrag(zeile(ergebnis, 'Spielraum obere').wert), 1026);
});

test('Scanner nennt Posten ohne Tarifhebel beim Namen', () => {
  const ergebnis = logik.scanner([
    f('wohnen', '1200', { label: 'Wohnen', korridor: [0, 0] }),
    f('energie', '150', { label: 'Energie', korridor: [0.08, 0.25] }),
  ]);
  assert.match(ergebnis.liste[0].zusatz, /Kein Tarifhebel/);
  assert.match(ergebnis.liste[1].zusatz, /Spielraum/);
});

test('Scanner ohne Posten verlangt eine Eingabe statt zu rechnen', () => {
  const ergebnis = logik.scanner([f('einkommen', '3000', { label: 'Haushaltsnetto' })]);
  assert.ok(Array.isArray(ergebnis.fehler));
  assert.equal(ergebnis.kennzahlen, undefined);
});

test('Scanner warnt ab 60 Prozent Fixkostenquote', () => {
  const ergebnis = logik.scanner([
    f('wohnen', '1500', { label: 'Wohnen', korridor: [0, 0.02] }),
    f('energie', '300', { label: 'Energie', korridor: [0.08, 0.25] }),
    f('mobilitaet', '300', { label: 'Mobilität', korridor: [0.05, 0.2] }),
    f('einkommen', '3000', { label: 'Haushaltsnetto' }),
  ]);
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'achtung'));
});

// ===================================================================
// 3. Effektivpreis
// ===================================================================

test('Effektivpreis verrechnet Aktion, Hardware, Einmalkosten und Bonus', () => {
  // 6×19,99 + 18×44,99 + 24×5 + 69,95 − 100 = 119,94 + 809,82 + 120 + 69,95 − 100 = 1019,71
  const ergebnis = logik.effektivpreis([
    f('laufzeit', '24', { typ: 'zahl' }),
    f('aktionsmonate', '6', { typ: 'zahl' }),
    f('aktionspreis', '19,99'),
    f('normalpreis', '44,99'),
    f('hardware', '5'),
    f('einmalkosten', '69,95'),
    f('bonus', '100'),
  ]);
  assert.equal(betrag(kennzahl(ergebnis, 'Gesamtkosten').wert), 1019.71);
  assert.equal(betrag(kennzahl(ergebnis, 'Effektivpreis').wert), 42.49); // 1019,71 / 24
  assert.equal(betrag(kennzahl(ergebnis, 'Preis nach der Aktion').wert), 49.99);
  assert.ok(ergebnis.hinweise.some((h) => /Ab Monat 7/.test(h.text)), 'Der Preissprung braucht einen eigenen Prüftermin.');
});

test('Effektivpreis kappt eine Aktion, die länger als die Laufzeit ist', () => {
  const ergebnis = logik.effektivpreis([
    f('laufzeit', '12', { typ: 'zahl' }),
    f('aktionsmonate', '24', { typ: 'zahl' }),
    f('aktionspreis', '10'),
    f('normalpreis', '30'),
  ]);
  assert.equal(betrag(kennzahl(ergebnis, 'Effektivpreis').wert), 10);
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'warnung' && /begrenzt/.test(h.text)));
});

test('Effektivpreis widerspricht, wenn der neue Tarif teurer ist als der alte', () => {
  const ergebnis = logik.effektivpreis([
    f('laufzeit', '24', { typ: 'zahl' }),
    f('aktionsmonate', '6', { typ: 'zahl' }),
    f('aktionspreis', '9,99'),
    f('normalpreis', '49,99'),
    f('vergleichspreis', '35'),
  ]);
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'achtung'));
});

test('Effektivpreis meldet fehlende Pflichtfelder statt zu raten', () => {
  const ergebnis = logik.effektivpreis([
    f('laufzeit', '', { typ: 'zahl', label: 'Laufzeit' }),
    f('aktionspreis', '19,99', { label: 'Aktionspreis' }),
    f('normalpreis', '', { label: 'Normalpreis' }),
  ]);
  assert.deepEqual(ergebnis.fehler, ['Laufzeit', 'Normalpreis']);
});

// ===================================================================
// 4. Energie
// ===================================================================

test('Energie rechnet fairen Abschlag und Nachzahlung', () => {
  // 2500 kWh × 36,8 ct = 920 € + 12 × 12 € = 1064 € -> 88,67 €/Monat
  const ergebnis = logik.energie([
    f('medium', 'strom', { typ: 'auswahl', auswahlLabel: 'Strom' }),
    f('verbrauch', '2500', { typ: 'zahl' }),
    f('arbeitspreis', '36,8', { typ: 'zahl' }),
    f('grundpreis', '12'),
    f('abschlag', '75'),
    f('monate', '6', { typ: 'zahl' }),
  ]);
  assert.equal(betrag(kennzahl(ergebnis, 'Jahreskosten').wert), 1064);
  assert.equal(betrag(kennzahl(ergebnis, 'Fairer Monatsabschlag').wert), 88.67);
  assert.equal(betrag(kennzahl(ergebnis, 'Erwartete Nachzahlung').wert), 164); // (88,67 − 75) × 12
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'nachzahlung'));
  assert.match(zeile(ergebnis, 'Bereits aufgelaufen').wert, /Nachzahlung/);
});

test('Energie erkennt einen zu hohen Abschlag als zinsloses Darlehen', () => {
  const ergebnis = logik.energie([
    f('medium', 'gas', { typ: 'auswahl', auswahlLabel: 'Gas' }),
    f('verbrauch', '12000', { typ: 'zahl' }),
    f('arbeitspreis', '10,2', { typ: 'zahl' }),
    f('grundpreis', '12'),
    f('abschlag', '160'),
  ]);
  assert.equal(betrag(kennzahl(ergebnis, 'Jahreskosten').wert), 1368); // 1224 + 144
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'warnung' && /zinslos/.test(h.text)));
  assert.ok(ergebnis.hinweise.some((h) => /Oktober und März/.test(h.text)), 'Gas bekommt den Saison-Hinweis.');
});

test('Energie ohne Abschlag zeigt nur den fairen Wert', () => {
  const ergebnis = logik.energie([
    f('verbrauch', '2000', { typ: 'zahl' }),
    f('arbeitspreis', '30', { typ: 'zahl' }),
    f('grundpreis', '10'),
  ]);
  assert.ok(!ergebnis.kennzahlen.some((k) => /Nachzahlung|Guthaben/.test(k.label)));
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'info'));
});

// ===================================================================
// 5. Selbstbehalt
// ===================================================================

test('Selbstbehalt liefert Break-even und Zehn-Jahres-Vergleich', () => {
  // 90 € Ersparnis gegen 300 € Selbstbehalt -> 0,3 Schäden pro Jahr, 3,0 in zehn Jahren
  const ergebnis = logik.selbstbehalt([
    f('beitrag_ohne', '390'),
    f('beitrag_mit', '300'),
    f('selbstbehalt', '300'),
    f('schaeden', '2', { typ: 'zahl' }),
  ]);
  assert.match(kennzahl(ergebnis, 'Break-even').wert, /^3,0 Schäden/);
  assert.equal(betrag(kennzahl(ergebnis, 'Beitragsersparnis').wert), 90);
  // 10 Jahre mit SB: 3000 + 2×300 = 3600 gegen 3900 ohne -> 300 Vorteil
  assert.equal(betrag(kennzahl(ergebnis, 'Vorteil mit Selbstbehalt').wert), 300);
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'gut'));
});

test('Selbstbehalt kippt oberhalb des Break-even', () => {
  const ergebnis = logik.selbstbehalt([
    f('beitrag_ohne', '390'),
    f('beitrag_mit', '300'),
    f('selbstbehalt', '300'),
    f('schaeden', '5', { typ: 'zahl' }),
  ]);
  assert.equal(kennzahl(ergebnis, 'Nachteil mit Selbstbehalt').label, 'Nachteil mit Selbstbehalt');
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'warnung'));
});

test('Selbstbehalt begrenzt den Eigenanteil auf die typische Schadenhöhe', () => {
  const ergebnis = logik.selbstbehalt([
    f('beitrag_ohne', '390'),
    f('beitrag_mit', '300'),
    f('selbstbehalt', '500'),
    f('schadenhoehe', '200'),
    f('schaeden', '1', { typ: 'zahl' }),
  ]);
  assert.equal(betrag(zeile(ergebnis, 'Wirksamer Eigenanteil').wert), 200);
  assert.ok(ergebnis.hinweise.some((h) => /unter dem Selbstbehalt/.test(h.text)));
});

test('Selbstbehalt ohne Beitragsvorteil ist ein klares Nein', () => {
  const ergebnis = logik.selbstbehalt([
    f('beitrag_ohne', '300'),
    f('beitrag_mit', '300'),
    f('selbstbehalt', '300'),
  ]);
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'achtung'));
});

// ===================================================================
// 6. Notgroschen
// ===================================================================

test('Notgroschen rechnet Ziel, Fehlbetrag und Dauer ohne Zins', () => {
  const ergebnis = logik.notgroschen([
    f('ausgaben', '2000'),
    f('lage', 'angestellt', { typ: 'auswahl', auswahlZahl: 3, auswahlLabel: 'Unbefristet angestellt' }),
    f('erspartes', '1500'),
    f('sparrate', '250'),
  ], { heute: HEUTE });
  assert.equal(betrag(kennzahl(ergebnis, 'Zielbetrag').wert), 6000);
  assert.equal(betrag(kennzahl(ergebnis, 'Noch zu sparen').wert), 4500);
  assert.equal(kennzahl(ergebnis, 'Dauer bis zum Ziel').wert, '1 Jahr und 6 Monate'); // 4500 / 250 = 18
  assert.equal(kennzahl(ergebnis, 'Voraussichtlich erreicht').wert, '02.04.2028');
  assert.equal(ergebnis.liste.length, 3);
  // Erste Stufe = eine Monatsausgabe (2.000 €); mit 1.500 € Bestand fehlen 500 € = 2 Monate.
  assert.equal(ergebnis.liste[0].zusatz, 'noch 2 Monate');
  assert.equal(ergebnis.liste[2].zusatz, 'noch 1 Jahr und 6 Monate');
});

test('Notgroschen erkennt ein erreichtes Ziel', () => {
  const ergebnis = logik.notgroschen([
    f('ausgaben', '1500'),
    f('lage', 'angestellt', { typ: 'auswahl', auswahlZahl: 3 }),
    f('erspartes', '5000'),
    f('sparrate', '100'),
  ], { heute: HEUTE });
  assert.equal(kennzahl(ergebnis, 'Dauer bis zum Ziel').wert, 'Ziel erreicht');
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'gut'));
});

test('Notgroschen ohne Sparrate verschweigt das Problem nicht', () => {
  const ergebnis = logik.notgroschen([
    f('ausgaben', '2000'),
    f('lage', 'selbststaendig', { typ: 'auswahl', auswahlZahl: 6 }),
    f('erspartes', '0'),
    f('sparrate', '0'),
  ], { heute: HEUTE });
  assert.equal(betrag(kennzahl(ergebnis, 'Zielbetrag').wert), 12000);
  assert.equal(kennzahl(ergebnis, 'Dauer bis zum Ziel').wert, 'nicht erreichbar');
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'achtung'));
});

test('Notgroschen verkürzt mit Zins, aber nur geringfügig', () => {
  const felder = [
    f('ausgaben', '2000'),
    f('lage', 'angestellt', { typ: 'auswahl', auswahlZahl: 3 }),
    f('erspartes', '0'),
    f('sparrate', '300'),
  ];
  const ohne = logik.notgroschen(felder, { heute: HEUTE });
  const mit = logik.notgroschen([...felder, f('zins', '3', { typ: 'prozent' })], { heute: HEUTE });
  assert.equal(ohne.kennzahlen[2].wert, '1 Jahr und 8 Monate'); // 6000 / 300 = 20
  assert.equal(mit.kennzahlen[2].wert, '1 Jahr und 8 Monate');
  assert.ok(mit.zeilen.some((z) => z.label.startsWith('Zinsbeitrag')));
});

// ===================================================================
// 7. Kündigungsfristen
// ===================================================================

function fristFelder(ende, wert, einheit, verlaengerung = 1) {
  return [
    f('vertragsart', 'internet', { typ: 'auswahl', auswahlLabel: 'Internet & Mobilfunk' }),
    f('vertragsende', ende, { typ: 'datum' }),
    f('frist_wert', String(wert), { typ: 'zahl' }),
    f('frist_einheit', einheit, { typ: 'auswahl', auswahlLabel: einheit }),
    f('verlaengerung', String(verlaengerung), { typ: 'auswahl', auswahlZahl: verlaengerung, auswahlLabel: `${verlaengerung} Monate` }),
  ];
}

test('Fristen rechnet den letzten Kündigungstag kalendarisch', () => {
  const ergebnis = logik.fristen(fristFelder('2027-05-31', 3, 'monate'), { heute: HEUTE });
  assert.equal(kennzahl(ergebnis, 'Letzter Kündigungstag').wert, '28.02.2027');
  assert.equal(kennzahl(ergebnis, 'Vertragsende').wert, '31.05.2027');
  assert.match(zeile(ergebnis, 'Rechenweg').wert, /31\.05\.2027 minus 3 Monate = 28\.02\.2027/);
});

test('Fristen legt drei Termine mit festem Abstand an', () => {
  const ergebnis = logik.fristen(fristFelder('2027-05-31', 3, 'monate'), { heute: HEUTE });
  assert.deepEqual(ergebnis.termine.map((t) => t.id), ['vergleich', 'schreiben', 'frist']);
  assert.deepEqual(ergebnis.termine.map((t) => hilfen.iso(t.datum)), ['2027-01-17', '2027-02-14', '2027-02-28']);
  assert.match(ergebnis.termine[2].beschreibung, /§ 130 BGB/);
});

test('Fristen rechnet auch in Wochen und Tagen', () => {
  const wochen = logik.fristen(fristFelder('2027-03-01', 6, 'wochen'), { heute: HEUTE });
  assert.equal(kennzahl(wochen, 'Letzter Kündigungstag').wert, '18.01.2027');
  const tage = logik.fristen(fristFelder('2027-03-01', 14, 'tage'), { heute: HEUTE });
  assert.equal(kennzahl(tage, 'Letzter Kündigungstag').wert, '15.02.2027');
});

test('Fristen benennt bei verpasster Frist den nächsten Ausstieg', () => {
  const ergebnis = logik.fristen(fristFelder('2026-10-31', 3, 'monate', 12), { heute: HEUTE });
  assert.equal(kennzahl(ergebnis, 'Verbleibende Zeit').wert, 'Frist verstrichen');
  assert.equal(kennzahl(ergebnis, 'Nächster Ausstieg').wert, '31.10.2027');
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'achtung' && /nächste Ausstieg/.test(h.text)));
});

test('Fristen drängt im Endspurt und bleibt früh ruhig', () => {
  const knapp = logik.fristen(fristFelder('2027-01-05', 3, 'monate'), { heute: HEUTE }); // 05.10.2026
  assert.ok(knapp.hinweise.some((h) => /§ 312k BGB/.test(h.text)));
  const frueh = logik.fristen(fristFelder('2028-01-31', 3, 'monate'), { heute: HEUTE });
  assert.ok(frueh.hinweise.some((h) => h.art === 'gut'));
});

test('Fristen braucht ein gültiges Datum', () => {
  const ergebnis = logik.fristen(fristFelder('', 3, 'monate'), { heute: HEUTE });
  assert.ok(Array.isArray(ergebnis.fehler));
});

// ===================================================================
// 8. Entscheidungsbaum – die Regelreihenfolge ist der Vertrag
// ===================================================================

function baum(werte) {
  const standard = { kosten_bekannt: 'ja', bindung: 'frei', konditionen: 'garantie', vorkasse: 'nein', ersparnis: '200' };
  const w = { ...standard, ...werte };
  return logik.entscheidung([
    f('kosten_bekannt', w.kosten_bekannt, { typ: 'auswahl', auswahlLabel: w.kosten_bekannt }),
    f('bindung', w.bindung, { typ: 'auswahl', auswahlLabel: w.bindung }),
    f('konditionen', w.konditionen, { typ: 'auswahl', auswahlLabel: w.konditionen }),
    f('vorkasse', w.vorkasse, { typ: 'auswahl', auswahlLabel: w.vorkasse }),
    f('ersparnis', w.ersparnis, { typ: 'euro' }),
  ]);
}

test('Regel 1: ohne bekannte Jahreskosten wird nicht entschieden', () => {
  const ergebnis = baum({ kosten_bekannt: 'nein', ersparnis: '500' });
  assert.equal(ergebnis.empfehlung, 'Erst rechnen, dann entscheiden');
});

test('Regel 2: Vorkasse sticht jede Ersparnis', () => {
  const ergebnis = baum({ vorkasse: 'ja', ersparnis: '900' });
  assert.equal(ergebnis.empfehlung, 'Dieses Angebot nicht');
  assert.ok(ergebnis.hinweise.some((h) => /Ausfallrisiko/.test(h.text)));
});

test('Regel 3: unter der Aufwandsgrenze bleibt man', () => {
  assert.equal(baum({ ersparnis: '45' }).empfehlung, 'Bleiben und Termin setzen');
  assert.equal(baum({ ersparnis: '60' }).empfehlung, 'Wechseln', 'Genau auf der Grenze zählt als tragfähig.');
});

test('Regel 4: Bindung verschiebt die Entscheidung auf einen Termin', () => {
  assert.equal(baum({ bindung: 'gebunden' }).empfehlung, 'Termin setzen, jetzt nicht kündigen');
  assert.equal(baum({ bindung: 'bald' }).empfehlung, 'Jetzt vorbereiten, zum Fristbeginn wechseln');
});

test('Regel 5: Bonusmodelle werden nach Höhe der Ersparnis getrennt', () => {
  assert.equal(baum({ konditionen: 'bonuslastig', ersparnis: '250' }).empfehlung, 'Wechseln – und das Folgejahr sofort vormerken');
  assert.equal(baum({ konditionen: 'bonuslastig', ersparnis: '90' }).empfehlung, 'Nur wechseln, wenn du den Folgetermin wirklich hältst');
  assert.equal(baum({ konditionen: 'ohne' }).empfehlung, 'Wechseln, aber mit kurzer Laufzeit');
});

test('Entscheidungsbaum begründet jede Empfehlung und nennt einen nächsten Schritt', () => {
  for (const fall of [{}, { vorkasse: 'ja' }, { bindung: 'gebunden' }, { konditionen: 'ohne' }, { kosten_bekannt: 'nein' }]) {
    const ergebnis = baum(fall);
    assert.ok(ergebnis.hinweise.length >= 3, 'Schritt + mindestens zwei Begründungen');
    assert.ok(ergebnis.hinweise.every((h) => h.text.length > 40));
  }
});

test('Entscheidungsbaum verlangt die Ersparnis, wenn sie entscheidend wird', () => {
  const ergebnis = baum({ ersparnis: '' });
  assert.deepEqual(ergebnis.fehler, ['die rechnerische Ersparnis pro Jahr']);
});

// ===================================================================
// 9. Haushaltsbudget
// ===================================================================

function budgetFelder() {
  return [
    f('einkommen', '3000', { bucket: 'einnahme', label: 'Haushaltsnetto' }),
    f('wohnen', '1200', { bucket: 'bedarf', label: 'Wohnen' }),
    f('energie', '150', { bucket: 'bedarf', label: 'Energie' }),
    f('lebensmittel', '450', { bucket: 'bedarf', label: 'Lebensmittel' }),
    f('freizeit', '300', { bucket: 'wunsch', label: 'Freizeit' }),
    f('sparen', '400', { bucket: 'sparen', label: 'Sparen' }),
  ];
}

test('Budget rechnet Saldo und 50-30-20-Verteilung', () => {
  const ergebnis = logik.budget(budgetFelder());
  assert.equal(betrag(kennzahl(ergebnis, 'Ausgaben gesamt').wert), 2500);
  assert.equal(betrag(kennzahl(ergebnis, 'Überschuss').wert), 500);
  assert.equal(betrag(kennzahl(ergebnis, 'Sparquote').wert), 13.3);
  assert.deepEqual(ergebnis.liste.map((l) => l.label), ['Bedarf (50 %)', 'Wünsche (30 %)', 'Sparen & Tilgung (20 %)']);
  assert.equal(Math.round(ergebnis.liste[0].anteil), 60); // 1800 von 3000
  assert.ok(ergebnis.hinweise.some((h) => /Bedarfsanteil/.test(h.text)));
});

test('Budget nennt eine Unterdeckung beim Namen', () => {
  const felder = budgetFelder();
  felder[0] = f('einkommen', '2200', { bucket: 'einnahme', label: 'Haushaltsnetto' });
  const ergebnis = logik.budget(felder);
  assert.equal(kennzahl(ergebnis, 'Unterdeckung').label, 'Unterdeckung');
  assert.ok(ergebnis.hinweise.some((h) => h.art === 'achtung' && /Fixkostenproblem/.test(h.text)));
});

test('Budget zählt Einnahmen nicht zu den Ausgaben', () => {
  const ergebnis = logik.budget([
    f('einkommen', '1000', { bucket: 'einnahme' }),
    f('wohnen', '400', { bucket: 'bedarf' }),
  ]);
  assert.equal(betrag(kennzahl(ergebnis, 'Ausgaben gesamt').wert), 400);
  assert.equal(betrag(kennzahl(ergebnis, 'Überschuss').wert), 600);
});

test('Budget ohne jede Eingabe fragt nach, statt null auszuweisen', () => {
  const ergebnis = logik.budget([f('einkommen', '', { bucket: 'einnahme' })]);
  assert.ok(Array.isArray(ergebnis.fehler));
});

// ===================================================================
// 10. Export – CSV, PDF, ICS entstehen vollständig lokal
// ===================================================================

test('CSV ist Excel-tauglich: BOM, Semikolon, CRLF', () => {
  const csv = exporte.csv([['Posten', 'Betrag'], ['Wohnen; Nebenkosten', '1.200,00 €']]);
  assert.ok(csv.startsWith('\ufeff'), 'BOM fehlt – Excel liest sonst keine Umlaute.');
  assert.ok(csv.endsWith('\r\n'));
  assert.match(csv, /Posten;Betrag\r\n/);
  assert.match(csv, /"Wohnen; Nebenkosten";1\.200,00 €/, 'Semikolon im Text muss maskiert werden.');
});

test('PDF ist eine gültige, mehrseitige Datei mit Euro-Zeichen', () => {
  const abschnitte = [];
  for (let i = 0; i < 12; i++) {
    abschnitte.push({
      titel: `Abschnitt ${i}`,
      zeilen: [['Betrag', '1.234,56 €'], ['Zeichen', 'Größe – „Test" • ä ö ü ß']],
      absaetze: ['Ein längerer Absatz, der über die Zeilenbreite hinausgeht und deshalb umbrochen werden muss, damit der Text nicht aus der Seite läuft.'],
    });
  }
  const pdf = exporte.pdf({ titel: 'Werkzeug', untertitel: 'Test', abschnitte, fusszeile: 'Ohne Affiliate-Link nutzbar.' });
  assert.ok(pdf instanceof Uint8Array);
  const roh = Buffer.from(pdf).toString('latin1');
  assert.ok(roh.startsWith('%PDF-1.4'));
  assert.ok(roh.trimEnd().endsWith('%%EOF'));
  assert.match(roh, /\/Type\s*\/Catalog/);
  assert.match(roh, /WinAnsiEncoding/);
  assert.ok(roh.includes('\x80'), 'Das Euro-Zeichen muss nach WinAnsi (0x80) übersetzt sein.');
  const seiten = (roh.match(/\/Type\s*\/Page[^s]/g) || []).length;
  assert.ok(seiten > 1, `Mehrseitigkeit erwartet, gefunden: ${seiten}`);
  const xref = roh.search(/(^|\n)xref\r?\n/);
  assert.ok(xref > 0, 'xref-Tabelle fehlt');
  assert.ok(roh.indexOf('startxref') > xref, 'startxref muss nach der xref-Tabelle stehen');
  assert.match(roh, /\n0000000000 65535 f/, 'Der freie Eintrag 0 gehört in jede xref-Tabelle.');
});

test('ICS erzeugt ganztägige Termine mit Erinnerung', () => {
  const ergebnis = logik.fristen(fristFelder('2027-05-31', 3, 'monate'), { heute: HEUTE });
  const ics = exporte.ics(ergebnis.termine, { jetzt: HEUTE });
  assert.ok(ics.startsWith('BEGIN:VCALENDAR\r\nVERSION:2.0'));
  assert.ok(ics.trimEnd().endsWith('END:VCALENDAR'));
  assert.equal((ics.match(/BEGIN:VEVENT/g) || []).length, 3);
  assert.match(ics, /DTSTART;VALUE=DATE:20270228/);
  assert.match(ics, /DTEND;VALUE=DATE:20270301/, 'Ganztägig heißt: Ende am Folgetag.');
  assert.match(ics, /UID:20270228-frist@franksfinanzcheck\.de/);
  assert.equal((ics.match(/TRIGGER:-PT9H/g) || []).length, 3);
  for (const zeile of ics.split('\r\n')) {
    // RFC 5545 zählt Oktette, nicht Zeichen – Umlaute belegen zwei.
    assert.ok(Buffer.byteLength(zeile, 'utf8') <= 75, `Zeile zu lang für RFC 5545: ${zeile}`);
  }
  // Die Faltung darf nie innerhalb eines Zeichens trennen.
  assert.ok(!ics.includes('\ufffd'));
});

test('ICS maskiert Sonderzeichen in Titel und Beschreibung', () => {
  const ics = exporte.ics([{
    id: 'test',
    titel: 'Kündigung; Vertrag, Teil 1',
    datum: hilfen.datumLesen('2027-01-02'),
    beschreibung: 'Zeile eins\nZeile zwei',
  }], { jetzt: HEUTE });
  assert.match(ics, /SUMMARY:Kündigung\\; Vertrag\\, Teil 1/);
  assert.match(ics, /\\n/);
});

// ===================================================================
// 11. DOM-Anbindung (jsdom) – Struktur wie in ff_werkzeug.html
// ===================================================================

const DOM_HTML = `<!doctype html><html lang="de"><body>
  <section data-ff-werkzeug
           data-werkzeug="notgroschen"
           data-engine="notgroschen"
           data-name="Notgroschen-Rechner"
           data-dateipraefix="franksfinanzcheck"
           data-herkunft="https://franksfinanzcheck.de/"
           data-versprechen="Du kannst das Tool vollständig nutzen, ohne einen Affiliate-Link anzuklicken.">
    <noscript><p>Dieses Werkzeug rechnet im Browser.</p></noscript>
    <form novalidate>
      <div>
        <label for="ff-wz-notgroschen-ausgaben">Notwendige Ausgaben</label>
        <input id="ff-wz-notgroschen-ausgaben" type="text" data-feld="ausgaben" data-typ="euro" data-label="Notwendige Ausgaben" data-einheit="€ pro Monat" data-pflicht>
        <select id="ff-wz-notgroschen-lage" data-feld="lage" data-typ="auswahl" data-label="Deine Lage" data-standard="angestellt" data-pflicht>
          <option value="angestellt" data-zahl="3">Unbefristet angestellt</option>
          <option value="selbststaendig" data-zahl="6">Selbstständig</option>
        </select>
        <input id="ff-wz-notgroschen-erspartes" type="text" data-feld="erspartes" data-typ="euro" data-label="Bereits verfügbar">
        <input id="ff-wz-notgroschen-sparrate" type="text" data-feld="sparrate" data-typ="euro" data-label="Monatliche Sparrate">
      </div>
      <label><input type="checkbox" data-ff-wz-speichern> <span>Eingaben auf diesem Gerät merken</span></label>
      <button type="button" data-ff-wz-reset>Zurücksetzen</button>
      <button type="submit">Berechnen</button>
    </form>
    <div data-ff-wz-ergebnis aria-live="polite">
      <p data-ff-wz-leer>Noch nichts gerechnet.</p>
      <div data-ff-wz-fehler hidden></div>
      <div data-ff-wz-ausgabe hidden>
        <div data-ff-wz-kennzahlen></div>
        <div data-ff-wz-liste hidden></div>
        <div data-ff-wz-termine hidden></div>
        <div data-ff-wz-zeilen hidden></div>
        <div data-ff-wz-hinweise></div>
        <button type="button" data-ff-wz-export-format="csv">Als CSV</button>
        <button type="button" data-ff-wz-export-format="pdf">Als PDF</button>
      </div>
    </div>
    <div>
      <ol data-ff-wz-formel><li>Zielbetrag = Monatsausgaben × Monate der Lage</li></ol>
      <ul data-ff-wz-annahme><li>Der Zins bleibt über die Laufzeit konstant.</li></ul>
      <ul><li data-ff-wz-quelle data-url="https://www.bundesbank.de/de/statistiken">Zinsstatistik <span>Bundesbank · Stand 2026-09</span></li></ul>
    </div>
  </section>
</body></html>`;

function werkzeugFenster(vorbelegung) {
  const dom = new JSDOM(DOM_HTML, { url: 'https://franksfinanzcheck.de/werkzeuge/notgroschen-rechner/', runScripts: 'outside-only' });
  const { window } = dom;
  const heruntergeladen = [];
  // Ein früherer Besuch: der Speicher steht, BEVOR das Skript verdrahtet.
  if (vorbelegung) window.localStorage.setItem('ff_werkzeug_notgroschen_v1', vorbelegung);
  window.URL.createObjectURL = (blob) => {
    heruntergeladen.push(blob);
    return 'blob:test';
  };
  window.URL.revokeObjectURL = () => {};
  window.eval(SKRIPT);
  window.document.dispatchEvent(new window.Event('DOMContentLoaded'));
  return { window, heruntergeladen };
}

function eintragen(window, werte) {
  for (const [id, wert] of Object.entries(werte)) {
    const el = window.document.querySelector(`[data-feld="${id}"]`);
    el.value = wert;
  }
}

function rechnen(window) {
  window.document.querySelector('form').dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));
}

test('DOM: Ergebnis erscheint erst nach dem Rechnen', () => {
  const { window } = werkzeugFenster();
  const ausgabe = window.document.querySelector('[data-ff-wz-ausgabe]');
  assert.equal(ausgabe.hidden, true);
  eintragen(window, { ausgaben: '2000', erspartes: '1500', sparrate: '250' });
  rechnen(window);
  assert.equal(ausgabe.hidden, false);
  assert.equal(window.document.querySelector('[data-ff-wz-leer]').hidden, true);
  assert.match(window.document.querySelector('[data-ff-wz-kennzahlen]').textContent, /Zielbetrag6\.000\s€/);
  assert.match(window.document.querySelector('[data-ff-wz-hinweise]').textContent, /Dauerauftrag|Stufe/);
});

test('DOM: Pflichtfeld fehlt – Fehlerbox statt Ergebnis', () => {
  const { window } = werkzeugFenster();
  rechnen(window);
  const fehler = window.document.querySelector('[data-ff-wz-fehler]');
  assert.equal(fehler.hidden, false);
  assert.equal(window.document.querySelector('[data-ff-wz-ausgabe]').hidden, true);
  assert.match(fehler.textContent, /Notwendige Ausgaben/);
});

test('DOM: das Formular hat kein Ziel und lädt die Seite nicht neu', () => {
  const { window } = werkzeugFenster();
  const form = window.document.querySelector('form');
  assert.equal(form.getAttribute('action'), null);
  assert.equal(form.getAttribute('method'), null);
  eintragen(window, { ausgaben: '2000' });
  const ereignis = new window.Event('submit', { bubbles: true, cancelable: true });
  form.dispatchEvent(ereignis);
  assert.equal(ereignis.defaultPrevented, true);
});

test('DOM: Änderungen rechnen nach dem ersten Ergebnis automatisch neu', () => {
  const { window } = werkzeugFenster();
  eintragen(window, { ausgaben: '2000', sparrate: '250' });
  rechnen(window);
  const vorher = window.document.querySelector('[data-ff-wz-kennzahlen]').textContent;
  eintragen(window, { ausgaben: '3000' });
  window.document.querySelector('form').dispatchEvent(new window.Event('input', { bubbles: true }));
  const nachher = window.document.querySelector('[data-ff-wz-kennzahlen]').textContent;
  assert.notEqual(vorher, nachher);
  assert.match(nachher, /Zielbetrag9\.000\s€/);
});

test('DOM: gespeichert wird nur nach Häkchen, Zurücksetzen löscht sofort', () => {
  const { window } = werkzeugFenster();
  const schluessel = 'ff_werkzeug_notgroschen_v1';
  eintragen(window, { ausgaben: '2000', sparrate: '250' });
  rechnen(window);
  assert.equal(window.localStorage.getItem(schluessel), null, 'Ohne Häkchen wird nichts gespeichert.');

  const haken = window.document.querySelector('[data-ff-wz-speichern]');
  haken.checked = true;
  haken.dispatchEvent(new window.Event('change', { bubbles: true }));
  const gespeichert = JSON.parse(window.localStorage.getItem(schluessel));
  assert.equal(gespeichert.ausgaben, '2000');

  window.document.querySelector('[data-ff-wz-reset]').dispatchEvent(new window.Event('click', { bubbles: true }));
  assert.equal(window.localStorage.getItem(schluessel), null);
  assert.equal(haken.checked, false);
  assert.equal(window.document.querySelector('[data-feld="ausgaben"]').value, '');
  assert.equal(window.document.querySelector('[data-feld="lage"]').value, 'angestellt', 'data-standard wird wiederhergestellt.');
  assert.equal(window.document.querySelector('[data-ff-wz-ausgabe]').hidden, true);
});

test('DOM: gespeicherte Werte kommen beim nächsten Besuch zurück', () => {
  const erste = werkzeugFenster();
  eintragen(erste.window, { ausgaben: '2000', sparrate: '250' });
  rechnen(erste.window);
  const haken = erste.window.document.querySelector('[data-ff-wz-speichern]');
  haken.checked = true;
  haken.dispatchEvent(new erste.window.Event('change', { bubbles: true }));
  const inhalt = erste.window.localStorage.getItem('ff_werkzeug_notgroschen_v1');

  const zweite = werkzeugFenster(inhalt); // zweiter Seitenaufruf, Speicher liegt vor
  assert.equal(zweite.window.document.querySelector('[data-feld="ausgaben"]').value, '2000');
  assert.equal(zweite.window.document.querySelector('[data-ff-wz-speichern]').checked, true);
  assert.equal(zweite.window.document.querySelector('[data-ff-wz-ausgabe]').hidden, false);
});

test('DOM: Export erzeugt eine Datei im Browser, ohne Netzaufruf', () => {
  const { window, heruntergeladen } = werkzeugFenster();
  eintragen(window, { ausgaben: '2000', sparrate: '250' });
  rechnen(window);
  window.document.querySelector('[data-ff-wz-export-format="csv"]').dispatchEvent(new window.Event('click', { bubbles: true }));
  assert.equal(heruntergeladen.length, 1);
  window.document.querySelector('[data-ff-wz-export-format="pdf"]').dispatchEvent(new window.Event('click', { bubbles: true }));
  assert.equal(heruntergeladen.length, 2);
});

test('DOM: das Exportmodell übernimmt Formel, Annahmen, Quellen und das Versprechen', () => {
  const { window } = werkzeugFenster();
  eintragen(window, { ausgaben: '2000', sparrate: '250' });
  rechnen(window);
  const wurzel = window.document.querySelector('[data-ff-werkzeug]');
  const felder = FF.felderLesen(wurzel);
  const modell = exporte.modell(wurzel, felder, logik.notgroschen(felder, { heute: HEUTE }));
  assert.equal(modell.name, 'Notgroschen-Rechner');
  assert.equal(modell.formel.length, 1);
  assert.equal(modell.annahmen.length, 1);
  assert.match(modell.quellen[0], /Zinsstatistik .* – https:\/\/www\.bundesbank\.de/);
  assert.match(modell.versprechen, /ohne einen Affiliate-Link anzuklicken/);
  assert.ok(modell.eingaben.some(([label, wert]) => label === 'Notwendige Ausgaben' && wert === '2000 € pro Monat'));

  const csv = exporte.csvAusModell(modell);
  assert.match(csv, /Quellen/);
  assert.match(csv, /ohne einen Affiliate-Link anzuklicken/);
  assert.ok(exporte.pdfAusModell(modell) instanceof Uint8Array);
});

test('DOM: die Ausgabe entsteht als Text, nicht als HTML', () => {
  const { window } = werkzeugFenster();
  const eingabe = window.document.querySelector('[data-feld="ausgaben"]');
  eingabe.setAttribute('data-label', '<img src=x onerror=alert(1)>');
  eintragen(window, { ausgaben: '2000', sparrate: '250' });
  rechnen(window);
  const zeilen = window.document.querySelector('[data-ff-wz-zeilen]');
  assert.equal(zeilen.querySelectorAll('img').length, 0);
});
