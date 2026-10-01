// Regressionstest für die lokale Interaktion des Fixkosten-Cockpits.
// Läuft ohne Browser-Binary: jsdom + der echte Produktionscode.
// Das Test-DOM spiegelt absichtlich die Struktur des Shortcodes
// (layouts/shortcodes/fixkosten-cockpit.html): Knöpfe LIEGEN im
// Formular, der Copy-Knopf im Ergebnisblock. Nur so fängt der Test
// auch Struktur-Regresssionen, nicht nur Logikfehler.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SCRIPT = fs.readFileSync(path.join(ROOT, 'static/premium/ff-fixkosten-cockpit.js'), 'utf8');

function documentForTest() {
  const html = `<!doctype html><html><body>
    <section data-ff-fixkosten-cockpit>
      <form class="ff-cockpit__form" novalidate>
        <div data-ff-cockpit-row data-category="energie"><div class="ff-cockpit__category"><strong>Strom &amp; Gas</strong></div><input id="energie" data-ff-cockpit-amount><input data-ff-cockpit-date type="date"></div>
        <div data-ff-cockpit-row data-category="internet"><div class="ff-cockpit__category"><strong>Internet &amp; Mobilfunk</strong></div><input id="internet" data-ff-cockpit-amount><input data-ff-cockpit-date type="date"></div>
        <div class="ff-cockpit__actions">
          <label class="ff-cockpit__remember"><input type="checkbox" data-ff-cockpit-remember> <span>auf diesem Gerät merken</span></label>
          <div class="ff-cockpit__buttons">
            <button type="button" data-ff-cockpit-reset>Zurücksetzen</button>
            <button type="submit" data-ff-cockpit-submit>Mein Prüfplan</button>
          </div>
        </div>
      </form>
      <section data-ff-cockpit-result hidden><button type="button" data-ff-cockpit-copy>Prüfplan kopieren</button><strong data-ff-cockpit-monthly></strong><strong data-ff-cockpit-yearly></strong><strong data-ff-cockpit-count></strong><ol data-ff-cockpit-priorities></ol><ul data-ff-cockpit-deadlines></ul></section>
    </section>
  </body></html>`;
  const dom = new JSDOM(html, { url: 'https://example.test/cockpit/', runScripts: 'outside-only' });
  const { window } = dom;
  window.confirm = () => true;
  window.eval(SCRIPT);
  window.document.dispatchEvent(new window.Event('DOMContentLoaded'));
  return window;
}

function einreichen(window) {
  window.document.querySelector('.ff-cockpit__form').dispatchEvent(
    new window.Event('submit', { bubbles: true, cancelable: true })
  );
}

test('wertet deutsche Eurobeträge aus, priorisiert und speichert erst nach Opt-in', () => {
  const window = documentForTest();
  const q = (selector) => window.document.querySelector(selector);
  q('#energie').value = '1.234,56';
  q('#internet').value = '45,50';
  einreichen(window);

  assert.equal(q('[data-ff-cockpit-result]').hidden, false);
  assert.match(q('[data-ff-cockpit-monthly]').textContent, /1\.280,06/);
  assert.match(q('[data-ff-cockpit-yearly]').textContent, /15\.360,72/);
  assert.match(q('[data-ff-cockpit-priorities] li').textContent, /Strom & Gas/);
  assert.equal(window.localStorage.getItem('ff_fixkosten_cockpit_v1'), null);

  q('[data-ff-cockpit-remember]').checked = true;
  q('[data-ff-cockpit-remember]').dispatchEvent(new window.Event('change', { bubbles: true }));
  assert.match(window.localStorage.getItem('ff_fixkosten_cockpit_v1'), /1\.234,56/);

  q('[data-ff-cockpit-remember]').checked = false;
  q('[data-ff-cockpit-remember]').dispatchEvent(new window.Event('change', { bubbles: true }));
  assert.equal(window.localStorage.getItem('ff_fixkosten_cockpit_v1'), null);
});

test('Zurücksetzen räumt vollständig: Eingaben, Opt-in, Speicher, Ergebnis', () => {
  const window = documentForTest();
  const q = (selector) => window.document.querySelector(selector);
  q('#energie').value = '100';
  q('[data-ff-cockpit-date]').value = '2030-01-15';
  einreichen(window);
  assert.equal(q('[data-ff-cockpit-result]').hidden, false);

  q('[data-ff-cockpit-remember]').checked = true;
  q('[data-ff-cockpit-remember]').dispatchEvent(new window.Event('change', { bubbles: true }));
  assert.notEqual(window.localStorage.getItem('ff_fixkosten_cockpit_v1'), null);

  q('[data-ff-cockpit-reset]').click();

  assert.equal(q('#energie').value, '', 'Betragsfeld geleert');
  assert.equal(q('[data-ff-cockpit-date]').value, '', 'Datumsfeld geleert');
  assert.equal(q('[data-ff-cockpit-remember]').checked, false, 'Opt-in-Häkchen entfernt');
  assert.equal(q('[data-ff-cockpit-result]').hidden, true, 'Ergebnis ausgeblendet');
  assert.equal(window.localStorage.getItem('ff_fixkosten_cockpit_v1'), null, 'lokaler Speicher gelöscht');
});

test('formuliert Prüftermine nach Dringlichkeit statt pauschal', () => {
  const window = documentForTest();
  const logic = window.FFFixkostenCockpitLogik;
  // Node-realm-Date: genau der Weg, auf dem `instanceof Date` im Skript
  // realm-übergreifend brach – der exportierte Kern muss ihn vertragen.
  const jetzt = new Date(2030, 5, 15); // 15.06.2030, 00:00 lokal
  const text = (date) => logic.deadlineText({ label: 'Strom & Gas', date }, jetzt);

  assert.match(text('2020-01-01'), /liegt zurück – jetzt prüfen\./);
  assert.match(text('2030-06-14'), /liegt zurück/);
  assert.match(text('2030-06-15'), /heute als nächsten Check vorgesehen\./);
  assert.match(text('2030-06-16'), /nächster Check morgen\./);
  assert.match(text('2030-07-15'), /nächster Check in 30 Tagen \(15\.07\.2030\)\./);
  assert.match(text('2030-07-30'), /nächster Check in 45 Tagen \(30\.07\.2030\)\./);
  assert.match(text('2030-09-15'), /nächster Check am 15\.09\.2030\./);
  assert.equal(logic.deadlineText({ label: 'X', date: 'kaputt' }, jetzt), null);
});

test('exportiert einen DOM-freien, testbaren Rechenkern', () => {
  const window = documentForTest();
  const logic = window.FFFixkostenCockpitLogik;
  assert.equal(logic.amount('1.234,56'), 1234.56);
  assert.equal(logic.amount('45,50 €'), 45.5);
  assert.equal(Number.isNaN(logic.amount('nicht-zahl')), true);
  const result = logic.evaluate([
    { id: 'internet', label: 'Internet', amount: '45,50', date: '' },
    { id: 'energie', label: 'Strom & Gas', amount: '100', date: '2030-01-15' },
  ]);
  assert.equal(result.monthly, 145.5);
  assert.equal(result.items[0].id, 'energie');
  assert.equal(result.deadlineTexts.length, 1);
});

test('kopiert den Prüfplan als vollständigen, ehrlichen Klartext', () => {
  const window = documentForTest();
  const q = (selector) => window.document.querySelector(selector);
  q('#energie').value = '100';
  q('#internet').value = '9,90';
  q('[data-ff-cockpit-date]').value = '2030-01-15';
  einreichen(window);

  // toLocaleString('de-DE', currency) setzt geschützte Leerzeichen (U+00A0)
  // zwischen Betrag und € – für die Prüfung normalisieren, nicht mitfummeln.
  const plan = window.FFFixkostenCockpitLogik.copyPlan(q('[data-ff-fixkosten-cockpit]')).replace(/\u00A0/g, ' ');
  assert.match(plan, /^Mein Fixkosten-Prüfplan/);
  assert.match(plan, /109,90 € pro Monat/);
  assert.match(plan, /1\.318,80 € pro Jahr/);
  assert.match(plan, /1\. Strom & Gas: 100,00 € pro Monat/);
  assert.match(plan, /2\. Internet & Mobilfunk: 9,90 € pro Monat/);
  assert.match(plan, /Nächste Checks:/);
  assert.match(plan, /Erstellt mit dem Fixkosten-Cockpit von FranksFinanzcheck\.$/);
});
