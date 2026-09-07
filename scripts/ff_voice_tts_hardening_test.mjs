/**
 * ff_voice_tts_hardening_test.mjs — Härtung der Vorlese-Funktion
 * ============================================================
 * Befund 07.09.2026 (Fortsetzung von VORLESEN-REPARATUR-2026-09-06.md):
 * Die Meldung „kein Ton, die Fortschrittsanzeige rennt“ hatte zwei
 * Wurzeln — eine auf dem Server, eine im Reader:
 *
 *   SERVER  `edge-tts` liefert einen MP3-Strom; die Kette schrieb ihn in
 *           eine .wav-Datei und las sie mit dem wave-Modul. JEDES Segment
 *           scheiterte, veröffentlicht wurden 34 Tonspuren aus reiner
 *           Digitalstille (peak = 0). Reparatur + Messung:
 *           scripts/ff_voice_backends.py, scripts/ff_voice_audio.py.
 *
 *   READER  Eine Engine, die onstart/onend meldet, ohne zu sprechen
 *           (Linux ohne speech-dispatcher, verwaltete Browser, einige
 *           Android-WebViews), fegte still durch den Artikel: kein Ton,
 *           Balken auf 100 %, falsches „Vorlesen beendet“.
 *
 * Diese Suite pinnt die Reader-Härtung gegen die ECHTE Engine-Datei in
 * echter DOM (jsdom) fest:
 *
 *   H1 Stumm-Sweep  → ehrlicher Stopp, Balken bleibt bei 0 %
 *   H2 Schnell, aber möglich → läuft normal weiter (kein Fehlalarm)
 *   H3 Physik-Deckel → der Balken kann der Wanduhr nicht davonlaufen
 *   H4 Weicher Neustart → verschlucktes speak() wird wiederholt
 *   H5 Pause/Fortsetzen → kein verschluckter Satz mehr
 *   H6 Chrome-Keep-Alive → pause()/resume()-Impuls gegen den 15-s-Frost
 *   H7 Hängende Tonspur → Gerätestimme übernimmt
 *   H8 Diagnose-Schnittstelle → Störungen am echten Gerät benennbar
 *
 * Aufruf: node scripts/ff_voice_tts_hardening_test.mjs
 */

import { createRunner, loadPage, skeleton, mdToHtml, sleep } from './ff_voice_qa_lib.mjs';

const t = createRunner('TTS-Härtung Vorlesen (Befund 07.09.2026)');

/* ------------------------------------------------------------------
   Steuerbare Sprach-Attrappe mit ECHTEN Zeiten
   cps = Zeichen pro Sekunde, die die Attrappe „spricht“.
     · 15   realistische Sprechgeschwindigkeit
     · 40   sehr schnell, aber physikalisch möglich
     · 5000 tonloses Durchfegen (das gemeldete Fehlerbild)
   ------------------------------------------------------------------ */
function installTimedSpeech(win, {
  cps = 15, voices = null, swallowFirst = 0, userAgent = null,
} = {}) {
  const log = [];
  const calls = { pause: 0, resume: 0, cancel: 0 };
  let gen = 0;
  let swallowed = 0;

  if (userAgent) {
    try {
      Object.defineProperty(win.navigator, 'userAgent', { configurable: true, get: () => userAgent });
    } catch (e) { /* jsdom-Variante ohne Override – Test überspringt dann H6 */ }
  }

  class Utterance {
    constructor(text) {
      this.text = text; this.lang = ''; this.voice = null;
      this.rate = 1; this.pitch = 1; this.volume = 1;
      this.onstart = null; this.onend = null; this.onerror = null; this.onboundary = null;
    }
  }
  const state = { speaking: false, paused: false };
  win.SpeechSynthesisUtterance = Utterance;
  win.speechSynthesis = {
    get speaking() { return state.speaking; },
    get paused() { return state.paused; },
    get pending() { return false; },
    getVoices: () => (voices || [
      { name: 'Microsoft Conrad Online (Natural) - German (Germany)', lang: 'de-DE', voiceURI: 'conrad', localService: false, default: false },
      { name: 'Microsoft Andrew Online (Natural) - English (United States)', lang: 'en-US', voiceURI: 'andrew', localService: false, default: false },
    ]).slice(),
    addEventListener() {}, removeEventListener() {},
    speak(u) {
      const my = ++gen;
      log.push({ text: u.text, at: Date.now(), gen: my });
      if (swallowed < swallowFirst) { swallowed += 1; return; }   // Äußerung verschluckt
      state.speaking = true;
      const len = String(u.text).length;
      const dur = Math.max(4, (len / cps) * 1000);
      setTimeout(() => { if (my === gen && u.onstart) u.onstart(); }, 4);
      // Wortgrenzen wie im echten Browser: alle 150 ms rückt der Zeiger vor.
      const step = 150;
      const startedAt = Date.now();
      const ticker = setInterval(() => {
        if (my !== gen || state.paused) { if (my !== gen) clearInterval(ticker); return; }
        const done = Math.min(len, Math.round(((Date.now() - startedAt) / dur) * len));
        if (u.onboundary) u.onboundary({ name: 'word', charIndex: done });
      }, step);
      setTimeout(() => {
        clearInterval(ticker);
        if (my !== gen) return;
        state.speaking = false;
        if (u.onboundary) u.onboundary({ name: 'word', charIndex: len });
        if (u.onend) u.onend();
      }, dur);
    },
    cancel() { gen += 1; calls.cancel += 1; state.speaking = false; },
    pause() { calls.pause += 1; state.paused = true; },
    resume() { calls.resume += 1; state.paused = false; },
  };
  return { log, calls, state };
}

const BODY = mdToHtml(Array.from({ length: 10 }, (_, i) =>
  `## Abschnitt ${i + 1}\n\nDer Arbeitspreis liegt bei 12 ct/kWh und du sparst bis zu 650 Euro pro Jahr, wenn du den Anbieter wechselst und die Preisgarantie prüfst. Ein Wechsel dauert online weniger als zehn Minuten.`
).join('\n\n'));

function build(opts = {}, pageOpts = {}) {
  let handle = null;
  const out = loadPage(skeleton(Object.assign({ title: 'Gasanbieter wechseln', bodyHtml: BODY }, pageOpts)), {
    setup: (win) => { handle = installTimedSpeech(win, opts); },
  });
  out.speech = handle;
  return out;
}

const widthOf = (doc) => parseFloat(doc.getElementById('ff-voice-progress').style.width) || 0;
const statusOf = (doc) => doc.getElementById('ff-voice-status').textContent;

/* ============================================================ */
t.group('H1 · Stumm-Sweep: Engine meldet Sprechen, gibt aber keinen Ton');
{
  const { win, doc, speech } = build({ cps: 5000 });
  const api = win.__ffVoice;

  t.eq('Physik-Deckel aktiv (Standard 60 Zeichen/s)', api.speechFloorCps, 60);
  doc.getElementById('ff-voice-play').click();
  await sleep(1000);
  t.ok('Balken rennt NICHT davon', widthOf(doc) < 8, 'width=' + widthOf(doc) + '%');

  await sleep(3200);
  t.ok('Lauf wird ehrlich gestoppt', api.reading === false, 'reading=' + api.reading);
  t.ok('Als Stumm-Sweep erkannt', api.muteStop === true);
  t.ok('Status benennt den fehlenden Ton', /keinen Ton/.test(statusOf(doc)), 'status=' + statusOf(doc));
  t.ok('Kein falsches „Vorlesen beendet“', statusOf(doc) !== 'Vorlesen beendet.');
  t.ok('Fortschritt bleibt bei 0 %', widthOf(doc) === 0, 'width=' + widthOf(doc) + '%');
  t.eq('Knopf zurück auf Vorlesen', doc.getElementById('ff-voice-play-label').textContent, 'Vorlesen');
  t.ok('Es wurde tatsächlich gesprochen (Attrappe)', speech.log.length >= 3);
  const diag = api.diagnostics();
  t.ok('Diagnose weist die Messung aus', diag.measured.chars >= 400 && diag.measured.units >= 2,
    JSON.stringify(diag.measured));
}

/* ============================================================ */
t.group('H2 · Schnell, aber möglich: kein Fehlalarm');
{
  const { win, doc } = build({ cps: 40 });   // 2,6× schneller als die Regie
  const api = win.__ffVoice;

  doc.getElementById('ff-voice-play').click();
  await sleep(4200);
  t.ok('Lesen läuft weiter', api.reading === true, 'reading=' + api.reading);
  t.ok('Kein Stumm-Stopp ausgelöst', api.muteStop === false);
  t.ok('Fortschritt wächst', widthOf(doc) > 0, 'width=' + widthOf(doc) + '%');
  t.ok('Engine gilt als lebendig', api.everStarted === true);
  api.stop();
}

/* ============================================================ */
t.group('H3 · Physik-Deckel: der Balken folgt der Wanduhr');
{
  const { win, doc } = build({ cps: 15 });
  const api = win.__ffVoice;

  doc.getElementById('ff-voice-play').click();
  await sleep(1200);
  const w1 = widthOf(doc);
  // In 1,2 s kann bei 60 Zeichen/s höchstens ein Bruchteil des Artikels
  // gesprochen sein — der Balken darf nie darüber hinausschießen.
  const totalChars = api.units.reduce((n, u) => n + String(u.text || '').length, 0);
  const ceiling = ((60 * 1.2 + 60) / Math.max(1, totalChars)) * 100 + 1;
  t.ok('Balken innerhalb der Physik', w1 <= ceiling, 'width=' + w1 + '% ceiling=' + ceiling.toFixed(1) + '%');
  t.ok('Balken bewegt sich überhaupt', w1 > 0, 'width=' + w1 + '%');
  api.stop();
}

/* ============================================================ */
t.group('H4 · Weicher Neustart: verschlucktes speak() (Chrome-Rennen)');
{
  const { win, doc, speech } = build({ cps: 15, swallowFirst: 1 });
  const api = win.__ffVoice;

  doc.getElementById('ff-voice-play').click();
  await sleep(300);
  t.ok('Kein sofortiger Abbruch', api.reading === true);
  t.eq('Erst ein Sprechversuch', speech.log.length, 1);

  await sleep(1900);   // weiche Wache nach 1,5 s + 120 ms Ruhe
  t.ok('Derselbe Text wird erneut gesprochen', speech.log.length >= 2, 'versuche=' + speech.log.length);
  t.eq('Wirklich derselbe Text', speech.log[1].text, speech.log[0].text);
  t.ok('Weicher Neustart gezählt', api.softStarts >= 1, 'softStarts=' + api.softStarts);
  t.ok('Engine läuft danach', api.everStarted === true && api.reading === true);
  t.ok('Kein „nicht verfügbar“-Fehlalarm', !/nicht verfügbar/.test(statusOf(doc)), 'status=' + statusOf(doc));
  api.stop();
}

/* ============================================================ */
t.group('H5 · Pause und Fortsetzen: kein verschluckter Satz');
{
  const { win, doc, speech } = build({ cps: 15 });
  const api = win.__ffVoice;

  doc.getElementById('ff-voice-play').click();
  await sleep(900);
  const spokenBefore = speech.log.map((l) => l.text);
  t.ok('Mindestens eine Einheit läuft', spokenBefore.length >= 1);

  doc.getElementById('ff-voice-play').click();      // Pause mitten im Satz
  t.ok('Pausiert', api.playing === false);
  const frozen = widthOf(doc);
  await sleep(300);
  t.ok('Fortschritt steht still', widthOf(doc) === frozen);

  doc.getElementById('ff-voice-play').click();      // Fortsetzen
  await sleep(400);
  const spokenAfter = speech.log.map((l) => l.text);
  const resumedText = spokenAfter[spokenBefore.length];
  t.ok('Fortsetzen spricht weiter', spokenAfter.length > spokenBefore.length);
  t.eq('Die unterbrochene Einheit wird wiederholt (nichts verschluckt)',
    resumedText, spokenBefore[spokenBefore.length - 1]);
  t.ok('Höchstens diese eine Wiederholung',
    new Set(spokenAfter).size >= spokenAfter.length - 1);
  api.stop();
}

/* ============================================================ */
t.group('H6 · Chrome-Keep-Alive gegen den 15-Sekunden-Frost');
{
  const { win, doc, speech } = build({
    cps: 15,
    userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
  });
  const api = win.__ffVoice;
  const isChrome = api.diagnostics().chromeKeepAlive;
  t.ok('Chrome-Erkennung greift', isChrome === true);

  doc.getElementById('ff-voice-play').click();
  await sleep(9600);        // Keep-Alive-Takt: 9 s
  t.ok('pause()/resume()-Impuls gesendet', speech.calls.pause >= 1 && speech.calls.resume >= 1,
    'pause=' + speech.calls.pause + ' resume=' + speech.calls.resume);
  t.ok('Wiedergabe läuft ungestört weiter', api.reading === true && api.muteStop === false);
  api.stop();
  await sleep(50);
  const pausesAfterStop = speech.calls.pause;
  await sleep(400);
  t.eq('Nach dem Ende kein Impuls mehr', speech.calls.pause, pausesAfterStop);
}

/* ============================================================ */
t.group('H7 · Hängende Tonspur: Gerätestimme übernimmt');
{
  const { win, doc, speech } = build({ cps: 15 }, {
    track: {
      src: '/audio/articles/haengt.wav',
      version: 'ff-voice-2026.09.07',
      duration: 180000,
      chunks: Array.from({ length: 20 }, (_, i) => ({ b: i, t0: i * 9000, t1: (i + 1) * 9000, lang: 'de' })),
    },
  });
  const api = win.__ffVoice;
  const audio = doc.querySelector('audio');
  t.ok('Spur besteht das Metadaten-Gate', api.trackPlausible() === true);

  // Der Player „läuft“, aber seine Uhr steht — genau das Bild bei
  // hängendem Netz oder blockiertem Codec.
  Object.defineProperty(audio, 'paused', { configurable: true, get: () => false });
  Object.defineProperty(audio, 'readyState', { configurable: true, get: () => 4 });
  Object.defineProperty(audio, 'duration', { configurable: true, get: () => 180 });
  Object.defineProperty(audio, 'currentTime', { configurable: true, get: () => 3, set: () => {} });

  doc.getElementById('ff-voice-play').click();
  t.eq('Start im Tonspur-Modus', api.mode, 'track');
  audio.dispatchEvent(new win.Event('play'));

  await sleep(7000);        // Hänger-Wache: 6 s
  t.eq('Gerätestimme hat übernommen', api.mode, 'speech');
  t.ok('Lesen läuft weiter', api.reading === true);
  t.ok('Status nennt den Hänger', /hängt|geladen|übernimmt/.test(statusOf(doc)), 'status=' + statusOf(doc));
  t.ok('Browser-Engine spricht', speech.log.length >= 1);
  api.stop();
}

/* ============================================================ */
t.group('H8 · Diagnose-Schnittstelle für den Störungsfall');
{
  const { win, doc } = build({ cps: 15 });
  const api = win.__ffVoice;
  const d = api.diagnostics();
  const keys = ['version', 'mode', 'reading', 'trackReady', 'speechSupported', 'voiceCount',
    'maleVoice', 'everStarted', 'muteStop', 'speechFloorCps', 'measured', 'chromeKeepAlive', 'trackProbe'];
  keys.forEach((k) => t.ok('Diagnose kennt „' + k + '“', Object.prototype.hasOwnProperty.call(d, k)));
  t.eq('Version geführt', d.version, '2026.09.10');
  t.eq('Ohne Tonspur: Browser-Pfad', d.mode, 'speech');
  t.ok('Stille-Sonde ohne Web Audio still deaktiviert', d.trackProbe.attached === false);
  t.ok('Männliche Stimme gebunden', d.maleVoice.de === true);
  doc.getElementById('ff-voice-play').click();
  await sleep(200);
  t.ok('Diagnose kennt den laufenden Zustand', api.diagnostics().reading === true);
  api.stop();
}

t.done();
