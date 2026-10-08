// Verhaltenstest des KI-Assistenten-Clients (static/premium/ki-assistent.js).
// ===================================================================
// Geprüft wird das Verhalten im echten DOM (jsdom), nicht der Text:
//
//   1. Markup aus einer Antwort wird NIE ausgeführt oder eingebaut (R7):
//      ein <img onerror> bleibt Text, Auszeichnung wird als Elemente gebaut.
//   2. Ein Request hat ein Zeitlimit (R4): der Fetch bekommt ein Signal,
//      und läuft das Limit ab, bricht er ab und der Leser bekommt einen Satz.
//   3. Das Zeitlimit deckt die Worst-Case-Kette des Workers ab
//      (4 Provider × 30 s, cloudflare/ki-assistent/worker.js).
//
// Der Tag-Filter für Skripte folgt dem Muster aus tools/robust.test.mjs.
//
// Aufruf: node --test tools/ki-assistent.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const QUELLE = fs.readFileSync(path.join(ROOT, 'static/premium/ki-assistent.js'), 'utf8');

const ZEITLIMIT_ERWARTET_MS = 130000;

const WIDGET = `
  <script type="application/json" id="ff-ki-config">{"endpoint":"https://worker.example/ask","slug":"test"}</script>
  <button id="ff-ki-trigger" aria-expanded="false"></button>
  <div id="ff-ki-panel" aria-hidden="true">
    <button id="ff-ki-close"></button>
    <div id="ff-ki-messages"></div>
    <textarea id="ff-ki-input-field"></textarea>
    <button id="ff-ki-send"></button>
  </div>`;

/** Frische Seite mit Widget und geladenem Client. `timer` fängt das
    Zeitlimit ab, damit der Test nicht 130 Sekunden wartet. */
function seite(fetchStub) {
  const dom = new JSDOM(`<!doctype html><html><body>${WIDGET}</body></html>`, {
    runScripts: 'outside-only',
    url: 'https://franksfinanzcheck.de/posts/beispiel/',
    pretendToBeVisual: true,
  });
  const win = dom.window;
  const echtesTimeout = win.setTimeout.bind(win);
  const timer = { fn: null, ms: null };
  win.setTimeout = (fn, ms, ...rest) => {
    if (ms === ZEITLIMIT_ERWARTET_MS) {
      timer.fn = fn;
      timer.ms = ms;
      return 1;
    }
    return echtesTimeout(fn, ms, ...rest);
  };
  win.fetch = fetchStub;
  win.eval(QUELLE);
  const doc = win.document;
  return {
    win,
    doc,
    timer,
    nachricht(text) {
      doc.getElementById('ff-ki-input-field').value = text;
      doc.getElementById('ff-ki-send').click();
    },
    meldungen: () => doc.getElementById('ff-ki-messages'),
  };
}

/** Wartet, bis die asynchrone Sendekette (Fetch, JSON, Rendering) durch ist. */
const ruhe = () => new Promise((r) => setTimeout(r, 25));

test('Quelle: kein innerHTML-Schreiben, Fetch mit Signal', () => {
  assert.doesNotMatch(QUELLE, /\.innerHTML\s*=/, 'innerHTML darf nicht zugewiesen werden (R7)');
  assert.doesNotMatch(QUELLE, /\bouterHTML\s*=/);
  assert.doesNotMatch(QUELLE, /insertAdjacentHTML|document\.write/);
  assert.match(QUELLE, /signal:\s*steuerung\.signal/, 'fetch braucht ein Abbruchsignal (R4)');
  assert.match(QUELLE, /clearTimeout\(zeitlimit\)/, 'das Zeitlimit muss nach jeder Anfrage gelöst werden');
});

test('Markup in der Antwort bleibt Text – nichts wird eingebaut oder ausgeführt', async () => {
  const boese = '<img src=x onerror="window.__xss=1"> **fett** und `code`\n\n- erster Punkt\n- zweiter Punkt';
  const s = seite(async () => ({ ok: true, json: async () => ({ answer: boese }) }));
  s.nachricht('Was kostet Strom?');
  await ruhe();

  const box = s.meldungen();
  assert.equal(box.querySelector('img'), null, 'ein eingeschleustes <img> darf nicht im DOM landen');
  assert.equal(s.win.__xss, undefined, 'das onerror-Attribut darf nicht laufen');
  assert.ok(box.textContent.includes('<img src=x'), 'der Markup-Text soll als Text sichtbar bleiben');
  assert.equal(box.querySelector('strong')?.textContent, 'fett');
  assert.equal(box.querySelector('code')?.textContent, 'code');
  assert.ok(box.textContent.includes('• erster Punkt'), 'Listenpunkte werden als • gerendert');
  assert.ok(box.textContent.includes('• zweiter Punkt'));
});

test('Normale Antwort wird als Absatz mit Zeilenumbruch gerendert', async () => {
  const s = seite(async () => ({ ok: true, json: async () => ({ answer: 'Zeile eins\nZeile zwei' }) }));
  s.nachricht('Frage?');
  await ruhe();

  const bot = s.meldungen().querySelector('.ff-ki-msg--bot');
  assert.ok(bot, 'Bot-Nachricht fehlt');
  assert.equal(bot.querySelector('p')?.querySelectorAll('br').length, 1);
  assert.match(bot.textContent, /Zeile eins\s*Zeile zwei/);
});

test('Zeitlimit: Fetch bekommt ein Signal und bricht mit klarer Meldung ab', async () => {
  let signal = null;
  const s = seite((url, opts) => {
    signal = opts.signal;
    return new Promise((_, ablehnen) => {
      opts.signal.addEventListener('abort', () => {
        const e = new Error('abgebrochen');
        e.name = 'AbortError';
        ablehnen(e);
      });
    });
  });
  s.nachricht('Wie hoch ist der Grundfreibetrag?');
  await ruhe();

  assert.ok(signal instanceof s.win.AbortSignal, 'fetch muss ein AbortSignal bekommen');
  assert.equal(signal.aborted, false, 'vor Ablauf des Limits läuft der Request');
  assert.ok(s.timer.fn, 'Zeitlimit wurde nicht mit 130 s gesetzt');
  assert.ok(s.timer.ms >= 4 * 30000, 'Limit liegt unter der Worker-Kette (4 × 30 s)');

  s.timer.fn();
  await ruhe();

  assert.equal(signal.aborted, true, 'nach Ablauf muss der Request abgebrochen sein');
  assert.match(s.meldungen().textContent, /zu lange gebraucht/);
  assert.equal(s.doc.getElementById('ff-ki-send').disabled, false, 'Senden muss danach wieder frei sein');
  assert.equal(s.doc.getElementById('ff-ki-input-field').disabled, false);
});

test('Verbindungsfehler ohne Abbruch bleibt bei der Verbindungs-Meldung', async () => {
  const s = seite(async () => {
    throw new TypeError('network down');
  });
  s.nachricht('Frage bitte?');
  await ruhe();
  assert.match(s.meldungen().textContent, /Verbindungsfehler/);
  assert.doesNotMatch(s.meldungen().textContent, /zu lange/);
});
