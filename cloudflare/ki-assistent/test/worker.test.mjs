/**
 * CORS-Vertrag des KI-Assistent-Workers (node --test, ohne Cloudflare-Login).
 *
 * WARUM DIESE DATEI EXISTIERT (Code-Scanning-Alert #83, 10.10.2026)
 * Die Freigabe fremder Herkünfte lief über `origin.endsWith(".pages.dev")` –
 * eine Prüfung auf der Zeichenkette statt auf dem Host (CodeQL-Regelklasse
 * `js/incomplete-url-substring-sanitization`). Diese Tests frieren die
 * host-genaue Entscheidung ein: Jede Zeile hier ist eine Umgehung, die vorher
 * funktioniert hätte oder künftig wieder funktionieren würde.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { corsHeaders, vorschauHost } from '../worker.js';

const ENV = { ALLOWED_ORIGIN: 'https://franksfinanzcheck.de' };
const erlaubt = (origin, env = ENV) =>
  corsHeaders(origin, env)['Access-Control-Allow-Origin'] === origin;

test('eigene Produktions-Herkunft wird exakt freigegeben', () => {
  assert.equal(erlaubt('https://franksfinanzcheck.de'), true);
  assert.equal(
    corsHeaders('https://franksfinanzcheck.de', ENV)['Access-Control-Allow-Origin'],
    'https://franksfinanzcheck.de',
  );
});

test('Vary: Origin bleibt gesetzt (Cache darf Herkünfte nicht mischen)', () => {
  assert.equal(corsHeaders('https://franksfinanzcheck.de', ENV).Vary, 'Origin');
});

test('echte Vorschau-Subdomains bleiben erlaubt', () => {
  assert.equal(erlaubt('https://vorschau.pages.dev'), true);
  assert.equal(erlaubt('https://3000-abc123.e2b.app'), true);
});

test('Zeichenketten-Umgehungen der Vorschau-Regel sind zu', () => {
  // „endet auf .pages.dev" – aber als Pfad/Query, nicht als Host
  assert.equal(erlaubt('https://angreifer.example/?x=.pages.dev'), false);
  assert.equal(erlaubt('https://angreifer.example/a.pages.dev'), false);
  // Host klebt am Vorschau-Namen, ist aber ein anderer
  assert.equal(erlaubt('https://boesepages.dev'), false);
  assert.equal(erlaubt('https://pages.dev.angreifer.example'), false);
  // Benutzerteil täuscht den Host vor
  assert.equal(erlaubt('https://vorschau.pages.dev@angreifer.example'), false);
  // unverschlüsselt ist keine Vorschau
  assert.equal(erlaubt('http://vorschau.pages.dev'), false);
});

test('fremde und leere Herkünfte bekommen die eigene Domain zurück', () => {
  for (const origin of ['https://angreifer.example', '', 'null', 'kein-origin']) {
    assert.equal(erlaubt(origin), false);
    assert.equal(
      corsHeaders(origin, ENV)['Access-Control-Allow-Origin'],
      'https://franksfinanzcheck.de',
      `Rückfall-Origin falsch für ${origin || '(leer)'}`,
    );
  }
});

test('ALLOWED_ORIGIN darf mehrere Herkünfte führen – exakt verglichen', () => {
  const env = { ALLOWED_ORIGIN: 'https://franksfinanzcheck.de, https://www.franksfinanzcheck.de' };
  assert.equal(erlaubt('https://www.franksfinanzcheck.de', env), true);
  assert.equal(erlaubt('https://franksfinanzcheck.de.angreifer.example', env), false);
});

test('vorschauHost urteilt über den Host, nicht über die Zeichenkette', () => {
  assert.equal(vorschauHost('https://a.b.pages.dev'), true);
  assert.equal(vorschauHost('https://pages.dev'), false); // Apex ist keine Vorschau
  assert.equal(vorschauHost('nonsense'), false);
  assert.equal(vorschauHost(undefined), false);
});
