// Regressionstest der Resilienzschicht (Vertrag C31, 07.10.2026).
// ===================================================================
// Zwei Ebenen, wie bei den übrigen Produktkernen dieses Repos:
//
//   1. BOOTSTRAP aus dem <head> (layouts/_partials/extend_head.html) –
//      die einzige Stelle, die JEDEN Fehler der Seite sieht, auch den der
//      Inline-Skripte. Wird hier in ein echtes jsdom-DOM evaluiert.
//   2. SCHICHT (static/premium/ff-robust.js) – Fehlergrenzen, Speicher-
//      Fangnetz, Zwischenablage, Diagnose. Ergänzt den Bootstrap.
//
// Geprüft wird das Verhalten, nicht der Text: fängt der Fehler-Horcher,
// beendet das Zeitlimit einen hängenden Fetch, wiederholt `hole` genau
// einmal, fällt der Speicher auf den Tab zurück, wenn localStorage wirft,
// sagt eine fehlgeschlagene Insel einen Satz (role="status"), und bleibt
// die Zwischenablage ehrlich, wenn die Erlaubnis fehlt.
//
// Zusätzlich: der Vertrag aus PRODUCT.md/CLAUDE.md – keine fremde Domain,
// kein innerHTML, kein eval, kein document.write in der Schicht.
//
// Aufruf: node --test tools/robust.test.mjs
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';
import { JSDOM } from 'jsdom';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const HEAD = fs.readFileSync(path.join(ROOT, 'layouts/_partials/extend_head.html'), 'utf8');
const SCHICHT = fs.readFileSync(path.join(ROOT, 'static/premium/ff-robust.js'), 'utf8');

/** Den Skript-Block mit dem Bootstrap aus dem Template schneiden.
    Hugo-Kommentare vorher entfernen: Sie dürfen `<script>` als Wort
    enthalten (diese Datei tut es, weil sie erklärt, warum der Bootstrap
    kein eigenes Tag bekommt) – sonst schneidet der Schnitt Prosa. */
function ohneHugoKommentare(text) {
  return text.replace(/\{\{-?\s*\/\*[\s\S]*?\*\/\s*-?\}\}/g, '');
}

function bootstrapQuelltext() {
  const sauber = ohneHugoKommentare(HEAD);
  const bloecke = [...sauber.matchAll(/<script(?![^>]*\btype=)[^>]*>([\s\S]*?)<\/script>/g)]
    .map((m) => m[1]);
  const block = bloecke.find((b) => b.includes('FFRobust'));
  assert.ok(block, 'Bootstrap im <head> nicht gefunden');
  assert.ok(block.includes('ff_cookie_consent'),
    'Der Bootstrap muss sich das vorhandene Head-Skript teilen (DOM-Budget 58)');
  return block;
}

/** Frische Seite mit Bootstrap + Schicht, Fetch-Stub vor dem Laden gesetzt. */
function seite({ fetch: fetchStub, ohneAbort = false, ohneStorage = false } = {}) {
  const dom = new JSDOM('<!doctype html><html><body><main></main></body></html>', {
    runScripts: 'outside-only',
    url: 'https://franksfinanzcheck.de/posts/beispiel/',
    pretendToBeVisual: true,
  });
  const win = dom.window;
  // jsdom liefert kein fetch. Die Schicht bindet `hole` nur, wenn es eines
  // gibt (Feature-Erkennung) – also bekommt jede Testseite eines.
  win.fetch = fetchStub || (async () => antwort({}));
  if (!ohneAbort) win.AbortController = AbortController;
  if (ohneStorage) {
    Object.defineProperty(win, 'localStorage', {
      configurable: true,
      get() { throw new win.Error('SecurityError: Speicher gesperrt'); },
    });
  }
  win.eval(bootstrapQuelltext());
  win.eval(SCHICHT);
  return { dom, win, R: win.FFRobust };
}

/** Antwort-Attrappe mit den Feldern, die `hole` wirklich liest. */
function antwort({ ok = true, status = 200, type = 'basic', daten = {} } = {}) {
  return {
    ok, status, type,
    json: async () => daten,
    text: async () => JSON.stringify(daten),
    clone() { return this; },
  };
}

// ---------------------------------------------------------------- Vertrag

test('Die Schicht ist first-party und schreibt kein Markup aus Text', () => {
  assert.deepEqual([], [...SCHICHT.matchAll(/https?:\/\//g)].map((m) => m[0]),
    'Die Resilienzschicht darf keine fremde Domain nennen');
  for (const verbot of ['innerHTML', 'document.write', 'insertAdjacentHTML']) {
    const treffer = SCHICHT.split('\n').filter((z) => z.includes(verbot)
      && !z.trim().startsWith('*') && !z.trim().startsWith('//'));
    assert.deepEqual([], treffer, `${verbot} gehört nicht in die Schicht`);
  }
  assert.ok(!/(^|[^.\w])eval\s*\(/.test(SCHICHT), 'eval() gehört nicht in die Schicht');
});

test('Bootstrap und Schicht teilen sich einen Namensraum und sind idempotent', () => {
  const { win, R } = seite();
  assert.equal(true, R.boot, 'Bootstrap hat sich nicht angemeldet');
  assert.equal(true, R.voll, 'Schicht hat sich nicht angemeldet');
  for (const baustein of ['melden', 'sicher', 'hole', 'insel', 'hinweis',
    'zwischenablage', 'bericht', 'bereit', 'warte']) {
    assert.equal('function', typeof R[baustein], `FFRobust.${baustein} fehlt`);
  }
  for (const baustein of ['verfuegbar', 'lesen', 'schreiben', 'loeschen', 'json', 'merke']) {
    assert.equal('function', typeof R.ablage[baustein], `FFRobust.ablage.${baustein} fehlt`);
  }
  // Zweites Laden darf nichts verdoppeln.
  win.eval(bootstrapQuelltext());
  win.eval(SCHICHT);
  const vorher = R.zaehler;
  R.melden({ quelle: 'probe' });
  assert.equal(vorher + 1, R.zaehler, 'Doppelte Einbindung zählt Befunde doppelt');
});

// ---------------------------------------------------------------- Fehler-Horcher

test('Der Fehler-Horcher fängt Skript-, Ressourcen- und Promise-Fehler', () => {
  const { win, R } = seite();
  win.dispatchEvent(new win.ErrorEvent('error', { message: 'kaputt', filename: 'x.js', lineno: 7 }));
  // Ein Ressourcen-Fehler bubble't nicht – er kommt nur in der Capture-Phase
  // am Fenster an, und nur, wenn das Element im Dokument hängt.
  const bild = win.document.createElement('img');
  Object.defineProperty(bild, 'src', { value: '/images/fehlt.jpg', configurable: true });
  win.document.body.appendChild(bild);
  bild.dispatchEvent(new win.Event('error'));
  win.dispatchEvent(new win.Event('unhandledrejection'));

  const quellen = R.fehler.map((f) => f.quelle);
  assert.ok(quellen.includes('skript'), 'Skript-Fehler nicht gefangen');
  assert.ok(quellen.includes('ressource'),
    'Ressourcen-Fehler nicht gefangen – dafür braucht es die Capture-Phase');
  assert.ok(quellen.includes('promise'), 'Nicht abgefangenes Promise nicht gefangen');
  assert.ok(R.fehler.every((f) => f.zeit && f.pfad), 'Jeder Befund trägt Zeit und Pfad');
});

test('Fünf Befunde kennzeichnen die Seite als belastet und funken ff:fehler', () => {
  const { win, R } = seite();
  let gehoert = 0;
  win.document.addEventListener('ff:fehler', () => { gehoert += 1; });
  for (let i = 0; i < 5; i++) R.melden({ quelle: 'probe', text: `Fall ${i}` });
  assert.equal('belastet', win.document.documentElement.getAttribute('data-ff-robust'));
  assert.equal(5, gehoert, 'Bausteine müssen sich an den Befund hängen können');
});

test('Der Ringpuffer wächst nicht über sein Limit', () => {
  const { R } = seite();
  for (let i = 0; i < R.max + 40; i++) R.melden({ quelle: 'probe', text: String(i) });
  assert.equal(R.max, R.fehler.length, 'Ein Dauerfehler würde den Speicher füllen');
  assert.equal(String(R.max + 39), R.fehler[R.fehler.length - 1].text,
    'Der jüngste Befund muss erhalten bleiben');
});

test('Die Wache wird nie selbst zur Fehlerquelle', () => {
  const { R } = seite();
  assert.doesNotThrow(() => R.melden(null));
  assert.doesNotThrow(() => R.melden({ get quelle() { throw new Error('boese'); } }));
  assert.equal(undefined, R.sicher(() => { throw new Error('x'); }, undefined, 'probe'));
  assert.equal('ersatz', R.sicher(() => { throw new Error('x'); }, 'ersatz', 'probe'));
});

// ---------------------------------------------------------------- Fetch mit Zeitlimit

test('hole() liefert Erfolg, HTTP-Fehler und opaque Antwort ehrlich', async () => {
  const ok = seite({ fetch: async () => antwort({ status: 201, daten: { fein: true } }) });
  const erfolg = await ok.R.hole('/x', { zeitlimit: 50 });
  assert.equal(true, erfolg.ok);
  assert.equal(201, erfolg.status);
  assert.equal('{"fein":true}', JSON.stringify(await erfolg.antwort.json()));

  const schlecht = seite({ fetch: async () => antwort({ ok: false, status: 503 }) });
  const fehler = await schlecht.R.hole('/x', { zeitlimit: 50 });
  assert.equal(false, fehler.ok);
  assert.equal('http-503', fehler.fehler, 'Ein 503 muss als Fehler erkennbar sein');

  // no-cors: opaque heißt „durchgekommen, Inhalt nicht lesbar" – KEIN Fehler.
  const opak = seite({ fetch: async () => antwort({ ok: false, status: 0, type: 'opaque' }) });
  const unbekannt = await opak.R.hole('/anmeldung', { zeitlimit: 50, mode: 'no-cors' });
  assert.equal(true, unbekannt.ok,
    'Eine opaque Antwort als Fehler zu deuten hieße, ehrliche Anmeldungen zu melden');
  assert.equal(true, unbekannt.unbekannt);
});

test('hole() beendet einen hängenden Dienst über das Zeitlimit', async () => {
  const { R } = seite({
    fetch: (_url, opts) => new Promise((_loesen, ablehnen) => {
      if (opts && opts.signal) {
        opts.signal.addEventListener('abort', () => {
          const fehler = new Error('abgebrochen');
          fehler.name = 'AbortError';
          ablehnen(fehler);
        });
      }
      // sonst: niemals antworten – genau der Befund aus dem Newsletter-Formular
    }),
  });
  const start = Date.now();
  const ergebnis = await R.hole('/haengt', { zeitlimit: 30 });
  assert.equal(false, ergebnis.ok);
  assert.equal('zeitlimit', ergebnis.fehler);
  assert.ok(Date.now() - start < 2000, 'Das Zeitlimit muss greifen, nicht der Browser');
});

test('hole() wiederholt einmal mit Rückenwind und gibt dann ehrlich auf', async () => {
  let aufrufe = 0;
  const { R } = seite({
    fetch: async () => {
      aufrufe += 1;
      if (aufrufe === 1) throw new Error('netz zuckt');
      return antwort({ daten: { ok: true } });
    },
  });
  const ergebnis = await R.hole('/zickt', { zeitlimit: 500, versuche: 2, warte: 1 });
  assert.equal(true, ergebnis.ok);
  assert.equal(2, ergebnis.versuche, 'Der zweite Versuch muss gezählt werden');
  assert.equal(2, aufrufe);

  let dauer = 0;
  const hoffnungslos = seite({ fetch: async () => { dauer += 1; throw new Error('weg'); } });
  const ende = await hoffnungslos.R.hole('/weg', { zeitlimit: 500, versuche: 3, warte: 1 });
  assert.equal(false, ende.ok);
  assert.equal('netz', ende.fehler);
  assert.equal(3, dauer, 'Bei drei Versuchen muss Schluss sein – kein Kreislauf');
});

test('hole() lehnt nie ab – ein vergessenes .catch() ist kein Ausfall mehr', async () => {
  const { R } = seite({ fetch: async () => { throw new TypeError('netz'); } });
  await assert.doesNotReject(R.hole('/x', { zeitlimit: 50, versuche: 1 }));
});

test('hole() ohne AbortController im Browser läuft trotzdem (kein Zeitlimit, kein Absturz)', async () => {
  const { R } = seite({ fetch: async () => antwort({}), ohneAbort: true });
  const ergebnis = await R.hole('/x', { zeitlimit: 10 });
  assert.equal(true, ergebnis.ok);
});

// ---------------------------------------------------------------- Speicher

test('ablage() schreibt und liest, und fällt auf den Tab zurück, wenn Storage wirft', () => {
  const { R } = seite();
  assert.equal(true, R.ablage.verfuegbar());
  assert.equal(true, R.ablage.schreiben('ff_probe', 'wert'));
  assert.equal('wert', R.ablage.lesen('ff_probe'));
  R.ablage.loeschen('ff_probe');
  assert.equal(null, R.ablage.lesen('ff_probe'));

  const gesperrt = seite({ ohneStorage: true });
  assert.equal(false, gesperrt.R.ablage.verfuegbar(),
    'Ein gesperrter Speicher muss erkennbar sein, nicht still');
  assert.equal(true, gesperrt.R.ablage.schreiben('ff_probe', 'wert'),
    'Die Seite bleibt bedienbar – die Erinnerung endet mit dem Tab');
  assert.equal('wert', gesperrt.R.ablage.lesen('ff_probe'));
  assert.equal(true, gesperrt.R.ablage.ersatz());
});

test('ablage.json() gibt bei kaputtem JSON den Rückfall, nicht den Absturz', () => {
  const { win, R } = seite();
  win.localStorage.setItem('ff_kaputt', '{kein json');
  assert.equal('{"leer":true}', JSON.stringify(R.ablage.json('ff_kaputt', { leer: true })),
    'Kaputtes JSON muss den Rückfall liefern (jsdom-Objekte sind cross-realm)');
  assert.equal(true, R.fehler.some((f) => f.quelle === 'ablage'),
    'Kaputtes JSON ist ein Befund – sonst bleibt es unbemerkt');
  assert.equal(true, R.ablage.merke('ff_merke', { a: 1 }));
  assert.equal('{"a":1}', JSON.stringify(R.ablage.json('ff_merke', null)));
});

// ---------------------------------------------------------------- Inseln

test('insel() hält den Ausfall beim Baustein und sagt einen Satz', () => {
  const { win, R } = seite();
  const ziel = win.document.querySelector('main');

  const wert = R.insel('rechner:gut', () => 42);
  assert.equal(42, wert);
  assert.equal('ok', R.status['rechner:gut']);

  const ausfall = R.insel('rechner:kaputt', () => { throw new Error('DOM unerwartet'); }, { ziel });
  assert.equal(null, ausfall);
  assert.equal('fehler', R.status['rechner:kaputt']);
  assert.equal('rechner:kaputt',
    win.document.documentElement.getAttribute('data-ff-insel-fehler'));
  const hinweis = ziel.querySelector('.ff-robust-hinweis');
  assert.ok(hinweis, 'Ohne sichtbaren Satz bleibt der Ausfall ein toter Knopf');
  assert.equal('status', hinweis.getAttribute('role'),
    'role=status ist Pflicht – der Satz muss angekündigt werden (WCAG 4.1.3)');
  assert.ok(hinweis.textContent.length > 20);
  assert.ok(R.fehler.some((f) => f.quelle === 'insel:rechner:kaputt'));
});

test('insel() meldet sich ab, wenn nichts zu tun ist – und wirft nie', () => {
  const { win, R } = seite();
  const ziel = win.document.querySelector('main');
  assert.equal(null, R.insel('leer', null));
  assert.equal('uebersprungen', R.status.leer);
  // text: false = der Baustein zeigt bewusst keinen Satz (z. B. weil er
  // seinen eigenen hat). Der Ausfall bleibt trotzdem gemeldet.
  assert.equal(null, R.insel('still', () => { throw new Error('x'); }, { text: false, ziel }));
  assert.equal(null, ziel.querySelector('.ff-robust-hinweis'),
    'Mit text:false darf kein Satz erscheinen');
  assert.ok(R.fehler.some((f) => f.quelle === 'insel:still'));
});

test('bereit() läuft sofort oder zum DOMContentLoaded – immer im Fangnetz', async () => {
  const { R } = seite();
  let lief = 0;
  R.bereit(() => { lief += 1; });
  R.bereit(() => { throw new Error('kaputter Baustein'); }, 'probe');
  // Ist das Dokument noch am Laden, läuft beides zum DOMContentLoaded.
  await new Promise((loesen) => setTimeout(loesen, 10));
  assert.equal(1, lief, 'Der Baustein muss genau einmal laufen');
  assert.ok(R.fehler.some((f) => f.quelle === 'probe'),
    'Ein werfender Baustein darf die übrigen nicht mitreißen');
});

// ---------------------------------------------------------------- Zwischenablage

test('zwischenablage() bleibt ehrlich, wenn die Erlaubnis fehlt', async () => {
  const { win, R } = seite();
  win.navigator.clipboard = { writeText: async () => { throw new Error('verweigert'); } };
  win.document.execCommand = () => false;
  assert.equal(false, await R.zwischenablage('Text'),
    'Ohne Kopieren kein „copied!" – der Knopf darf nichts versprechen');

  let kopiert = '';
  win.navigator.clipboard = { writeText: async (t) => { kopiert = t; return undefined; } };
  assert.equal(true, await R.zwischenablage('Betrag 1.234 €'));
  assert.equal('Betrag 1.234 €', kopiert);
});

test('zwischenablage() nutzt den alten Weg, wenn es die API nicht gibt', async () => {
  const { win, R } = seite();
  delete win.navigator.clipboard;
  let versucht = false;
  win.document.execCommand = () => { versucht = true; return true; };
  assert.equal(true, await R.zwischenablage('x'));
  assert.equal(true, versucht);
});

// ---------------------------------------------------------------- Diagnose

test('bericht() nennt Zustand, Inseln und die letzten Befunde – und sendet nichts', () => {
  const { win, R } = seite();
  R.insel('rechner:eins', () => true);
  R.melden({ quelle: 'probe', text: 'Fall' });
  const b = R.bericht();
  assert.equal('/posts/beispiel/', b.pfad);
  assert.equal(true, b.speicher);
  assert.equal('ok', b.inseln['rechner:eins']);
  assert.equal(1, b.fehlerGesamt);
  assert.equal(1, b.fehlerLetzte.length);
  assert.equal(false, b.offline);
  assert.equal('boolean', typeof b.dienstaktiv, 'dienstaktiv ist Teil des Berichts');
  assert.equal('string', typeof b.fassung);
});

test('Offline-Zustand steht am Dokument, nicht im Verborgenen', () => {
  const { win, R } = seite();
  Object.defineProperty(win.navigator, 'onLine', { value: false, configurable: true });
  win.dispatchEvent(new win.Event('offline'));
  assert.equal(true, R.offline);
  assert.equal('1', win.document.documentElement.getAttribute('data-ff-offline'));
  win.dispatchEvent(new win.Event('online'));
  assert.equal(false, R.offline);
  assert.equal(null, win.document.documentElement.getAttribute('data-ff-offline'));
});
