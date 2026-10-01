// Regressionstest für die lokale Interaktion des Fixkosten-Cockpits.
// Läuft ohne Browser-Binary: jsdom + der echte Produktionscode.
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
      <form class="ff-cockpit__form">
        <div data-ff-cockpit-row data-category="energie"><div class="ff-cockpit__category"><strong>Strom &amp; Gas</strong></div><input id="energie" data-ff-cockpit-amount><input data-ff-cockpit-date type="date"></div>
        <div data-ff-cockpit-row data-category="internet"><div class="ff-cockpit__category"><strong>Internet &amp; Mobilfunk</strong></div><input id="internet" data-ff-cockpit-amount><input data-ff-cockpit-date type="date"></div>
        <input type="checkbox" data-ff-cockpit-remember>
      </form>
      <button data-ff-cockpit-reset></button><button data-ff-cockpit-copy></button>
      <section data-ff-cockpit-result hidden><strong data-ff-cockpit-monthly></strong><strong data-ff-cockpit-yearly></strong><strong data-ff-cockpit-count></strong><ol data-ff-cockpit-priorities></ol><ul data-ff-cockpit-deadlines></ul></section>
    </section>
  </body></html>`;
  const dom = new JSDOM(html, { url: 'https://example.test/cockpit/', runScripts: 'outside-only' });
  const { window } = dom;
  window.confirm = () => true;
  window.eval(SCRIPT);
  window.document.dispatchEvent(new window.Event('DOMContentLoaded'));
  return window;
}

test('wertet deutsche Eurobeträge aus, priorisiert und speichert erst nach Opt-in', () => {
  const window = documentForTest();
  const q = (selector) => window.document.querySelector(selector);
  q('#energie').value = '1.234,56';
  q('#internet').value = '45,50';
  q('.ff-cockpit__form').dispatchEvent(new window.Event('submit', { bubbles: true, cancelable: true }));

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
