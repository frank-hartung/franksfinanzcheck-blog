/**
 * ff_voice_repair_test.mjs — Reparatur-Pinne für den Befund 06.09.2026
 * ============================================================
 * Gemeldeter Fehler (Produktion): „Vorlesen gibt keinen Ton, die
 * Fortschrittsanzeige rennt zu schnell durch.“
 *
 * Ursachenkette (nachgewiesen am Live-Stand origin/gh-pages):
 *   G1 Der Generator übersprang fehlgeschlagene TTS-Segmente STILL —
 *      deployed standen Tonspuren aus reinen Pausen (85 Chunks, alle
 *      t0==t1, 33 s für einen Zehn-Minuten-Artikel; 63 MB WAV).
 *   C1 Der Reader prüfte Tonspuren nicht: Er spielte die Pausen-Spur
 *      stumm ab — Fortschritt auf 100 % in 33 s („Anzeige rennt“).
 *   C2 fallbackToSpeech() war während der Wiedergabe ein NO-OP
 *      (startReading kehrt bei reading===true sofort zurück): Bei
 *      Lade-/Codec-Fehlern hing die Leiste endlos auf „Studio-Tonspur
 *      läuft.“ — kein Ton, kein Fortschritt, kein Fallback.
 *   C3 Ohne nutzbare Synthese (keine Engine/Stimmen) FEGTE der Reader
 *      still durch alle Einheiten: kein Ton, Progress rannte, „beendet“.
 *   C4 Der Stimmen-Katalog traf lazy ein — die „keine Stimme“-Auflösung
 *      wurde für immer gecacht, die männliche Stimme band nie.
 *
 * Diese Suite läuft gegen die ECHTE Engine (static/premium/ff-voice.js)
 * in echter DOM (jsdom) und pingt jede einzelne Reparatur fest.
 *
 * Aufruf: node scripts/ff_voice_repair_test.mjs
 */

import { createRunner, loadPage, skeleton, mdToHtml, sleep } from './ff_voice_qa_lib.mjs';

const t = createRunner('Reparatur-Pinne Vorlesen (Befund 06.09.2026)');

/* ------------------------------------------------------------ */
/* Testbau: reichhaltige, steuerbare Sprach-Engine               */
/* ------------------------------------------------------------ */

/**
 * installRichSpeech — Web-Speech-Attrappe mit steuerbarem Verhalten:
 *   mode 'working'  onstart nach 3 ms, onend nach 14 ms (async wie echt)
 *   mode 'failing'  onerror('synthesis-failed') nach 4 ms
 *   mode 'silent'   speak() schluckt die Äußerung (keine Events)
 * voices: Start-Katalog; pushVoices() liefert den Katalog nach und
 * feuert voiceschanged — genau der Chromium-/Safari-Lazy-Fall.
 */
function installRichSpeech(win, { mode = 'working', voices = [] } = {}) {
  const log = [];
  const events = [];
  const listeners = {};
  let catalog = voices.slice();
  let gen = 0;

  class Utterance {
    constructor(text) {
      this.text = text; this.lang = ''; this.voice = null;
      this.rate = 1; this.pitch = 1; this.volume = 1;
      this.onstart = null; this.onend = null; this.onerror = null; this.onboundary = null;
    }
  }
  win.SpeechSynthesisUtterance = Utterance;
  win.speechSynthesis = {
    getVoices: () => catalog.slice(),
    addEventListener(type, fn) { (listeners[type] = listeners[type] || []).push(fn); },
    removeEventListener() {},
    speak(u) {
      const my = ++gen;
      log.push({ text: u.text, lang: u.lang, voice: u.voice ? u.voice.name : null, gen: my });
      if (mode === 'silent') return;
      if (mode === 'failing') {
        setTimeout(() => { if (my === gen && u.onerror) u.onerror({ error: 'synthesis-failed' }); }, 4);
        return;
      }
      events.push('speak');
      setTimeout(() => {
        if (my !== gen) return;
        if (typeof u.onstart === 'function') u.onstart();
      }, 3);
      setTimeout(() => {
        if (my !== gen) return;
        if (typeof u.onboundary === 'function') u.onboundary({ charIndex: u.text.length });
        if (typeof u.onend === 'function') u.onend();
      }, 14);
    },
    cancel() { gen += 1; events.push('cancel'); },
    pause() {}, resume() {},
  };
  return {
    log, events,
    pushVoices(list) {
      catalog = list.slice();
      (listeners.voiceschanged || []).forEach((fn) => { try { fn(); } catch (e) {} });
    },
  };
}

const MALE_VOICES = [
  { name: 'Microsoft Conrad Online (Natural) - German (Germany)', lang: 'de-DE', voiceURI: 'conrad', localService: false, default: false },
  { name: 'Microsoft Andrew Online (Natural) - English (United States)', lang: 'en-US', voiceURI: 'andrew', localService: false, default: false },
  { name: 'Anna', lang: 'de-DE', voiceURI: 'anna', localService: true, default: true },
  { name: 'Katja', lang: 'de-DE', voiceURI: 'katja', localService: true, default: false },
  { name: 'Samantha', lang: 'en-US', voiceURI: 'samantha', localService: true, default: false },
];

function page(opts) {
  let handle = null;
  const out = loadPage(skeleton(opts.body ? opts.body : opts), {
    setup: (win) => { handle = installRichSpeech(win, opts.speech || { mode: 'working' }); },
  });
  out.speech = handle;
  return out;
}

/** Liefert das <audio>-Element der Engine (auch display:none). */
function audioOf(doc) { return doc.querySelector('audio'); }

/** Artikel-Innenleben für die Dauer-Plausibilität. */
const bigBody = mdToHtml([
  '## Warum ein Wechsel sich lohnt', '',
  'Der Arbeitspreis liegt bei 12 ct/kWh. Bei 20.000 kWh sparst du bis zu 650 € pro Jahr, wenn du den Anbieter wechselst und die Preisgarantie prüfst.', '',
  '### Die drei Preisbestandteile', '',
  '- Arbeitspreis pro Kilowattstunde', '- Grundpreis pro Monat', '- Verbrauchspreis im Winter', '',
  '> Ein Zitat aus der Branche: Die Tarife unterscheiden sich stark.', '',
  '## Schritt für Schritt zum Tarif', '',
  'Vergleiche die Tarife in der Tabelle, prüfe Laufzeit und Preisgarantie und kündige rechtzeitig. Ein Wechsel dauert online weniger als zehn Minuten und ist beim neuen Anbieter komplett digital. Der neue Versorger kümmert sich um die Kündigung beim alten Anbieter und um den Liefertermin.', '',
  '**Merksatz: Prüfe die Laufzeit genau.**',
].join('\n'));

/* ============================================================ */
t.group('C1 · Defekte Tonspur wird VOR dem Start abgewiesen');
{
  const { win, doc, speech } = page({
    title: 'Gasanbieter wechseln',
    bodyHtml: bigBody,
    // Exakt das deployte Defektmuster: alle Chunks t0==t1, 33 s.
    track: {
      src: '/audio/articles/defekt.wav',
      version: 'ff-voice-2026.09.05-b',
      duration: 32980,
      chunks: Array.from({ length: 40 }, (_, i) => ({ b: i, t0: i * 420, t1: i * 420, lang: 'de' })),
    },
  });
  const api = win.__ffVoice;
  t.ok('Engine initialisiert', !!api);
  t.ok('Track-Element existiert (initTrack ok)', !!audioOf(doc));
  t.ok('Plausibilitäts-Wache erkennt Pausen-Spur', api.trackPlausible() === false);

  doc.getElementById('ff-voice-play').click();
  t.ok('Kein Track-Modus nach Klick', api.mode === 'speech', 'mode=' + api.mode);
  t.ok('Status nennt die defekte Spur', /unbrauchbar/.test(doc.getElementById('ff-voice-status').textContent),
    'status=' + doc.getElementById('ff-voice-status').textContent);
  t.ok('„Studio-Tonspur läuft“ erscheint NICHT', !/Studio-Tonspur/.test(doc.getElementById('ff-voice-status').textContent));
  t.ok('Browser-Engine übernimmt (speak gerufen)', speech.log.length >= 1);
  t.ok('Lesen läuft', api.reading === true);
  api.stop();
}

/* ============================================================ */
t.group('C2 · Tonspur-Fehler zur Laufzeit: Fallback ist keine Blockade mehr');
{
  const { win, doc, speech } = page({
    title: 'Strom sparen im Haushalt',
    bodyHtml: bigBody,
    track: {
      src: '/audio/articles/404.wav',
      version: 'ff-voice-2026.09.06',
      duration: 90000,   // ehrliche Angabe passend zum Artikel — Datei selbst 404-t
      chunks: Array.from({ length: 12 }, (_, i) => ({ b: i, t0: Math.round(i * 7500), t1: Math.round((i + 1) * 7500), lang: 'de' })),
    },
  });
  const api = win.__ffVoice;
  const audio = audioOf(doc);
  t.ok('Plausible Spur wird akzeptiert', api.trackPlausible() === true);

  doc.getElementById('ff-voice-play').click();
  t.ok('Start im Track-Modus', api.mode === 'track', 'mode=' + api.mode);
  t.eq('Status „Studio-Tonspur läuft.“', doc.getElementById('ff-voice-status').textContent, 'Studio-Tonspur läuft.');

  // Der Fehler, der vorher endlos hing: <audio> meldet Lade-Fehler.
  audio.dispatchEvent(new win.Event('error'));
  t.ok('Fallback schaltet auf Browser-Engine', api.mode === 'speech', 'mode=' + api.mode);
  t.ok('Lesen läuft weiter (kein Einfrieren)', api.reading === true);
  t.ok('Browser-Engine spricht sofort', speech.log.length >= 1);
  t.ok('Status nennt den Grund der Übernahme', /Gerätestimme|übernimmt/.test(doc.getElementById('ff-voice-status').textContent),
    'status=' + doc.getElementById('ff-voice-status').textContent);
  t.ok('Knopf bleibt bedienbar (Pausieren)', doc.getElementById('ff-voice-play-label').textContent === 'Pausieren');
  api.stop();
}

/* ============================================================ */
t.group('C2b · Tonspur endet viel zu früh: Gerätestimme übernimmt ab Block');
{
  const { win, doc, speech } = page({
    title: 'Preisgarantie Gas',
    bodyHtml: bigBody,
    track: {
      src: '/audio/articles/zukurz.wav',
      version: 'ff-voice-2026.09.06',
      duration: 90000,
      chunks: Array.from({ length: 12 }, (_, i) => ({ b: i, t0: Math.round(i * 7500), t1: Math.round((i + 1) * 7500), lang: 'de' })),
    },
  });
  const api = win.__ffVoice;
  const audio = audioOf(doc);

  doc.getElementById('ff-voice-play').click();
  t.ok('Start im Track-Modus', api.mode === 'track');
  // Abspielposition mitten im Artikel vortäuschen, dann „ended“:
  Object.defineProperty(audio, 'duration', { configurable: true, value: 9 });   // 9 s statt ~90 s Karte
  Object.defineProperty(audio, 'currentTime', { configurable: true, value: 8.2 });
  audio.dispatchEvent(new win.Event('ended'));
  t.ok('Kein falsches „beendet“ — Engine übernimmt', api.mode === 'speech' && api.reading === true,
    'mode=' + api.mode + ' reading=' + api.reading);
  t.ok('Status nennt frühes Ende', /zu früh/.test(doc.getElementById('ff-voice-status').textContent),
    'status=' + doc.getElementById('ff-voice-status').textContent);
  t.ok('Browser-Engine spricht ab dem zuletzt gehörten Block', speech.log.length >= 1);
  api.stop();
}

/* ============================================================ */
t.group('C2c · Ehrliche Spur endet normal mit „beendet“');
{
  const { win, doc } = page({
    title: 'Kostenloses Girokonto',
    bodyHtml: mdToHtml('## Kurz\r\n\r\nDas ist ein kurzer Absatz für den Funktionstest.\r\n'),
    track: {
      src: '/audio/articles/gut.wav',
      version: 'ff-voice-2026.09.06',
      duration: 8000,
      chunks: [{ b: 0, t0: 0, t1: 1200, lang: 'de' }, { b: 1, t0: 1200, t1: 5000, lang: 'de' },
               { b: 2, t0: 5000, t1: 6400, lang: 'de' }, { b: 3, t0: 6400, t1: 8000, lang: 'de' }],
    },
  });
  const api = win.__ffVoice;
  const audio = audioOf(doc);
  t.ok('Kurze, ehrliche Spur besteht das Gate', api.trackPlausible() === true);

  doc.getElementById('ff-voice-play').click();
  t.ok('Start im Track-Modus', api.mode === 'track');
  Object.defineProperty(audio, 'duration', { configurable: true, value: 8 });
  Object.defineProperty(audio, 'currentTime', { configurable: true, value: 7.9 });
  audio.dispatchEvent(new win.Event('timeupdate'));
  audio.dispatchEvent(new win.Event('ended'));
  t.ok('Normales Ende gemeldet', api.reading === false
    && doc.getElementById('ff-voice-status').textContent === 'Vorlesen beendet.',
    'reading=' + api.reading + ' status=' + doc.getElementById('ff-voice-status').textContent);
  t.ok('Fortschritt bei 100 %', (parseFloat(doc.getElementById('ff-voice-progress').style.width) || 0) > 99);
  t.eq('Knopf zurück auf Vorlesen', doc.getElementById('ff-voice-play-label').textContent, 'Vorlesen');
}

/* ============================================================ */
t.group('C3 · Tote Synthese: ehrlicher Stopp statt stillem Durchfegen');
{
  const { win, doc, speech } = page({
    title: 'Heizkosten', bodyHtml: bigBody,
    speech: { mode: 'failing' },
  });
  const api = win.__ffVoice;

  doc.getElementById('ff-voice-play').click();
  await sleep(700);   // 1. Fehler → 1 Wiederholung → ehrlicher Stopp
  t.ok('Lesen endet ehrlich (kein Dauerschleifen)', api.reading === false);
  t.ok('Status nennt die Grenze des Geräts', /nicht verfügbar/.test(doc.getElementById('ff-voice-status').textContent),
    'status=' + doc.getElementById('ff-voice-status').textContent);
  t.ok('Maximal 2 Sprechversuche (Start + 1 Wiederholung)', speech.log.length <= 2, 'versuche=' + speech.log.length);
  t.ok('Fortschritt bleibt ehrlich bei 0 %', (parseFloat(doc.getElementById('ff-voice-progress').style.width) || 0) === 0);
  t.ok('Kein falsches „Vorlesen beendet“', doc.getElementById('ff-voice-status').textContent !== 'Vorlesen beendet.');
  t.eq('Knopf zurück auf Vorlesen', doc.getElementById('ff-voice-play-label').textContent, 'Vorlesen');
  t.ok('everStarted bleibt false', api.everStarted === false);
}

/* ============================================================ */
t.group('C3b · Stumme Engine (keine Events): Anti-Stall-Wache stoppt ehrlich');
{
  const { win, doc } = page({
    title: 'DSL wechseln', bodyHtml: bigBody,
    speech: { mode: 'silent' },
  });
  const api = win.__ffVoice;

  doc.getElementById('ff-voice-play').click();
  t.ok('Läuft zunächst (wartet auf onstart)', api.reading === true);
  await sleep(4300);   // 4-s-Wache
  t.ok('Wache beendet ehrlich nach 4 s', api.reading === false);
  t.ok('Status nennt die Grenze des Geräts', /nicht verfügbar/.test(doc.getElementById('ff-voice-status').textContent));
  t.ok('Fortschritt bleibt 0 %', (parseFloat(doc.getElementById('ff-voice-progress').style.width) || 0) === 0);
}

/* ============================================================ */
t.group('C4 · Lazy Stimmen-Katalog: männliche Stimme bindet nachträglich');
{
  const { win, doc, speech } = page({
    title: 'Haushaltsbuch', bodyHtml: bigBody,
    speech: { mode: 'working', voices: [] },
  });
  const api = win.__ffVoice;

  t.ok('Start ohne Katalog', win.speechSynthesis.getVoices().length === 0);
  t.ok('Idle-aria-label verspricht Gerätestimme (Katalog leer)',
    /Geräts|device/i.test(doc.getElementById('ff-voice-play').getAttribute('aria-label')));
  doc.getElementById('ff-voice-play').click();
  await sleep(40);
  t.ok('Erste Einheit spricht ohne Stimme (lang-only, nie stumm)', speech.log.length >= 1
    && speech.log[0].voice === null && speech.log[0].lang === 'de-DE',
    'log0=' + JSON.stringify(speech.log[0] || {}));

  speech.pushVoices(MALE_VOICES);   // Katalog trifft ein (voiceschanged)
  await sleep(900);
  const withVoice = speech.log.filter((l) => l.voice && /Conrad|Andrew/.test(l.voice));
  t.ok('Nachfolgende Einheiten binden die männliche Stimme', withVoice.length >= 1,
    'voices=' + JSON.stringify(speech.log.map((l) => l.voice)));
  t.ok('Weibliche Stimmen werden nie gewählt',
    speech.log.every((l) => !l.voice || !/Anna|Katja|Samantha/.test(l.voice)));
  api.stop();
  t.ok('Nach Stopp: Idle-aria-label verspricht die männliche Stimme',
    /männliche Stimme/.test(doc.getElementById('ff-voice-play').getAttribute('aria-label')),
    'aria=' + doc.getElementById('ff-voice-play').getAttribute('aria-label'));
}

/* ============================================================ */
t.group('C4b · Sofortiger Katalog: männliche Stimme ab der ersten Einheit');
{
  const { win, doc, speech } = page({
    title: 'Kfz-Versicherung', bodyHtml: bigBody,
    speech: { mode: 'working', voices: MALE_VOICES },
  });
  doc.getElementById('ff-voice-play').click();
  await sleep(60);
  t.ok('Männliche Stimme ab Einheit 1', speech.log.length >= 1 && /Conrad/.test(speech.log[0].voice || ''),
    'log0=' + JSON.stringify(speech.log[0] || {}));
  t.ok('Meldung „Männliche Stimme aktiv.“', /Männliche Stimme/.test(doc.getElementById('ff-voice-status').textContent));
  win.__ffVoice.stop();
}

/* ============================================================ */
t.group('Regression · Pause/Resume/Sprung bleiben intakt');
{
  const { win, doc, speech } = page({
    title: 'Mietwagen buchen', bodyHtml: bigBody,
    speech: { mode: 'working', voices: MALE_VOICES },
  });
  const api = win.__ffVoice;

  doc.getElementById('ff-voice-play').click();
  await sleep(120);
  const before = speech.log.length;
  t.ok('Mehrere Einheiten gesprochen', before >= 2, 'gesprochen=' + before);

  doc.getElementById('ff-voice-play').click();          // Pause
  t.eq('Pause-Label', doc.getElementById('ff-voice-play-label').textContent, 'Weiterlesen');
  t.ok('Engine abgebrochen', speech.events.includes('cancel'));
  await sleep(60);
  doc.getElementById('ff-voice-play').click();          // Resume
  await sleep(120);
  t.ok('Nach Resume geht es weiter', speech.log.length > before,
    'log=' + speech.log.length + ' vorher=' + before);
  t.ok('Keine Einheit doppelt (max. die durch Pause unterbrochene)',
    new Set(speech.log.map((l) => l.text)).size >= speech.log.length - 1);

  doc.getElementById('ff-voice-next').click();          // Abschnitt vor
  await sleep(80);
  t.ok('Nach Sprung weiter am Lesen', api.reading === true);

  doc.getElementById('ff-voice-stop').click();          // Stopp
  t.ok('Stopp beendet sauber', api.reading === false);
  t.eq('Label zurück', doc.getElementById('ff-voice-play-label').textContent, 'Vorlesen');
  const w = parseFloat(doc.getElementById('ff-voice-progress').style.width) || 0;
  t.ok('Fortschritt nach Stopp konsistent', w >= 0 && w <= 100);
}

/* ============================================================ */
t.group('Produktions-Blick · deployte Defektmuster werden abgewiesen');
{
  // Struktur der echten gh-pages-Spuren: alle Chunks t0==t1, 33 s gesamt.
  const deployed = {
    src: '/audio/articles/live.wav', version: 'ff-voice-2026.09.05-b',
    duration: 32980,
    chunks: Array.from({ length: 85 }, (_, i) => ({ b: i, t0: i * 420, t1: i * 420, lang: 'de' })),
  };
  const a = page({ title: 'Gas wechseln', bodyHtml: bigBody, track: deployed });
  t.ok('Deploytes Defektmuster abgewiesen (Chunks ohne Sprechdauer)',
    a.win.__ffVoice.trackPlausible() === false);

  // Auch ohne degenerate Chunks: 34 s für einen Langartikel ist eine
  // Dauer-Lüge — die Wache rechnet gegen die erwartete Hörzeit.
  const longBody = mdToHtml(Array.from({ length: 12 }, (_, i) =>
    `## Abschnitt ${i + 1}\n\n${'Der Arbeitspreis liegt bei 12 ct/kWh und du sparst bis zu 650 Euro pro Jahr, wenn du rechtzeitig kündigst und die Tarife vergleichst. '.repeat(3)}`).join('\n\n'));
  const b = page({
    title: 'Gas wechseln', bodyHtml: longBody,
    track: { ...deployed, duration: 34000, chunks: deployed.chunks.map((c) => ({ ...c, t1: c.t0 + 400 })) },
  });
  t.ok('Dauer-Lüge (34 s für Langartikel) abgewiesen', b.win.__ffVoice.trackPlausible() === false);
}

t.done();
