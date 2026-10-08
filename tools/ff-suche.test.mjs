// tools/ff-suche.test.mjs – Tests der Suchmaske (static/premium/ff-suche.js)
// Aufruf: node --test tools/ff-suche.test.mjs   (jsdom aus devDependencies)
//
// Geprüft wird der Vertrag, nicht die Optik:
//   · Auszüge werden nie als HTML eingesetzt (kein innerHTML, fremde Tags fallen weg)
//   · nur gleich-seitige Pfade werden verlinkt (kein javascript:, kein fremder Host)
//   · veraltete Antworten überschreiben keine neuere Suche
//   · ohne Index: sichtbare Fehlermeldung, kein stiller Ausfall

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { JSDOM } from 'jsdom';

const require = createRequire(import.meta.url);
const dom = new JSDOM('<!doctype html><html lang="de-DE"><body></body></html>', {
  url: 'https://franksfinanzcheck.de/suche/',
});
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const api = require('../static/premium/ff-suche.js');

const settle = () => new Promise((r) => setTimeout(r, 25));

function fixture() {
  document.body.innerHTML = `
    <div class="ff-suche" data-ff-suche data-ff-suche-pfad="/pagefind/pagefind.js">
      <form class="ff-suche__form" role="search" data-ff-suche-form hidden>
        <label for="ff-suche-eingabe">Suchbegriff</label>
        <input id="ff-suche-eingabe" type="search" data-ff-suche-eingabe>
        <button type="submit">Suchen</button>
      </form>
      <p data-ff-suche-status aria-live="polite"></p>
      <ol data-ff-suche-liste></ol>
    </div>`;
  return document.querySelector('[data-ff-suche]');
}

function sucheAbschicken(begriff) {
  document.querySelector('[data-ff-suche-eingabe]').value = begriff;
  document
    .querySelector('[data-ff-suche-form]')
    .dispatchEvent(new window.Event('submit', { cancelable: true }));
}

/* Fake-Index: liefert für jeden Begriff die vorgegebenen Treffer. */
function fakeIndex(treffer) {
  return {
    options: async () => {},
    init: async () => {},
    search: async (begriff) => ({
      results: (treffer[begriff] || []).map((t) => ({ data: async () => t })),
    }),
  };
}

test('entschluesseln löst nur bekannte und numerische Entities auf', () => {
  assert.equal(api.entschluesseln('Tom &amp; Jerry'), 'Tom & Jerry');
  assert.equal(api.entschluesseln('&amp;lt;'), '&lt;', 'einmal dekodieren, nicht doppelt');
  assert.equal(api.entschluesseln('&#65;&#x42;'), 'AB');
  assert.equal(api.entschluesseln('&unbekannt;'), '&unbekannt;');
  assert.equal(api.entschluesseln('&#99999999;'), '&#99999999;', 'ungültiger Codepunkt bleibt');
});

test('auszugSegmente trennt Markierungen und entfernt fremde Tags', () => {
  assert.deepEqual(api.auszugSegmente('Die <mark>Kündigungsfrist</mark> &amp; mehr'), [
    { text: 'Die ', markiert: false },
    { text: 'Kündigungsfrist', markiert: true },
    { text: ' & mehr', markiert: false },
  ]);
  const boese = api.auszugSegmente('<img src=x onerror="alert(1)"><script>x()</script>Text');
  assert.equal(boese.map((s) => s.text).join(''), 'x()Text', 'Tags weg, nur Text bleibt');
  assert.ok(boese.every((s) => !s.markiert));
  assert.deepEqual(api.auszugSegmente(''), []);
});

test('sichereUrl lässt nur gleich-seitige Pfade durch', () => {
  assert.equal(api.sichereUrl('/werkzeuge/kuendigungsfristen-kalender/'), '/werkzeuge/kuendigungsfristen-kalender/');
  assert.equal(api.sichereUrl('javascript:alert(1)'), null);
  assert.equal(api.sichereUrl('//fremd.example/x'), null, 'protokollrelativ ist fremd');
  assert.equal(api.sichereUrl('https://fremd.example/'), null);
  assert.equal(api.sichereUrl('/\\fremd.example'), null);
  assert.equal(api.sichereUrl(undefined), null);
});

test('trefferText formuliert 0, 1 und mehrere Treffer ohne Pluralfehler', () => {
  assert.equal(api.trefferText(0, 'Miete'), 'Keine Treffer für „Miete“.');
  assert.equal(api.trefferText(1, 'Miete'), '1 Treffer für „Miete“.');
  assert.equal(api.trefferText(7, 'Miete'), '7 Treffer für „Miete“.');
});

test('Treffer werden als Text gerendert – fremdes HTML wird nie ausgeführt', async () => {
  const root = fixture();
  api.ffSucheStarten(root, async () =>
    fakeIndex({
      Tagesgeld: [
        {
          url: '/posts/tagesgeld/',
          meta: { title: 'Tagesgeld-Zinsen <b>2026</b>' },
          excerpt: 'Die besten <mark>Tagesgeld</mark>-Zinse &amp; mehr <img src=x onerror="alert(1)">',
        },
        { url: 'javascript:alert(1)', meta: { title: 'Böse' }, excerpt: '' },
      ],
    }),
  );
  assert.equal(root.querySelector('[data-ff-suche-form]').hidden, false, 'Formular erst mit JavaScript sichtbar');

  sucheAbschicken('Tagesgeld');
  await settle();

  const status = root.querySelector('[data-ff-suche-status]').textContent;
  assert.equal(status, '2 Treffer für „Tagesgeld“.');
  const zeilen = root.querySelectorAll('[data-ff-suche-liste] > li');
  assert.equal(zeilen.length, 2);

  const erste = zeilen[0];
  assert.equal(erste.querySelector('a').getAttribute('href'), '/posts/tagesgeld/');
  assert.equal(erste.querySelector('a').textContent, 'Tagesgeld-Zinsen <b>2026</b>', 'Titel als Text');
  assert.equal(erste.querySelector('b'), null, 'kein echtes <b> im Titel');
  assert.equal(erste.querySelector('img'), null, 'kein <img> aus dem Auszug');
  assert.equal(erste.querySelector('mark').textContent, 'Tagesgeld');
  assert.match(erste.querySelector('.ff-suche__auszug').textContent, /Zinse & mehr/);

  const zweite = zeilen[1];
  assert.equal(zweite.querySelector('a'), null, 'unsicherer Pfad wird nicht verlinkt');
  assert.equal(zweite.querySelector('span').textContent, 'Böse');
  assert.equal(document.querySelector('[data-ff-suche-liste]').innerHTML.includes('<img'), false);
});

test('eine veraltete Antwort überschreibt die neuere Suche nicht', async () => {
  const root = fixture();
  let freigeben;
  const langsam = new Promise((r) => { freigeben = r; });
  const pf = {
    options: async () => {},
    init: async () => {},
    search: (begriff) => (begriff === 'langsam'
      ? langsam.then(() => ({ results: [] }))
      : Promise.resolve({ results: [{ data: async () => ({ url: '/x/', meta: { title: 'Schnell' }, excerpt: '' }) }] })),
  };
  api.ffSucheStarten(root, async () => pf);
  sucheAbschicken('langsam');
  sucheAbschicken('schnell');
  await settle();
  freigeben();
  await settle();
  assert.equal(root.querySelector('[data-ff-suche-status]').textContent, '1 Treffer für „schnell“.');
});

test('ein Zeichen löst keine Suche aus, sondern eine Hinweiszeile', async () => {
  const root = fixture();
  let aufrufe = 0;
  api.ffSucheStarten(root, async () => ({
    options: async () => {},
    init: async () => {},
    search: async () => { aufrufe += 1; return { results: [] }; },
  }));
  sucheAbschicken('a');
  await settle();
  assert.equal(aufrufe, 0);
  assert.equal(root.querySelector('[data-ff-suche-status]').textContent, 'Gib mindestens zwei Zeichen ein.');
});

test('ohne Treffer kommt ein konkreter Hinweis statt eines leeren Bildschirms', async () => {
  const root = fixture();
  api.ffSucheStarten(root, async () => fakeIndex({}));
  sucheAbschicken('Zyklotron');
  await settle();
  const status = root.querySelector('[data-ff-suche-status]').textContent;
  assert.match(status, /^Keine Treffer für „Zyklotron“\./);
  assert.match(status, /allgemeineren Begriff/);
});

test('fehlt der Index, erscheint eine sichtbare Fehlermeldung', async () => {
  const root = fixture();
  api.ffSucheStarten(root, async () => { throw new Error('404'); });
  sucheAbschicken('Tagesgeld');
  await settle();
  assert.match(root.querySelector('[data-ff-suche-status]').textContent, /konnte gerade nicht geladen werden/);
  assert.equal(root.querySelectorAll('[data-ff-suche-liste] > li').length, 0);
});

test('der Index wird erst bei der ersten Suche geladen, nicht schon beim Aufruf', async () => {
  const root = fixture();
  let geladen = 0;
  api.ffSucheStarten(root, async () => { geladen += 1; return fakeIndex({}); });
  await settle();
  assert.equal(geladen, 0, 'kein Index-Abruf ohne Eingabe');
  sucheAbschicken('Miete');
  await settle();
  sucheAbschicken('Strom');
  await settle();
  assert.equal(geladen, 1, 'ein Index, wiederverwendet');
});
