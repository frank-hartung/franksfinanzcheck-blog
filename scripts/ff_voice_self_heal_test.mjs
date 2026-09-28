/**
 * ff_voice_self_heal_test.mjs — Selbstheilung der Vorlese-Laufzeit.
 *
 * Diese kleine Suite pinnt genau die Fehlerklasse, die ein normaler
 * „Start/Ende“-Test verfehlt: Web Speech kann onstart melden und danach
 * dauerhaft hängen. Die echte Engine muss dann einmal automatisch
 * wiederholen und darf beim zweiten Hänger weder Text überspringen noch
 * „Vorlesen beendet“ lügen.
 */

import { createRunner, loadPage, skeleton, sleep } from './ff_voice_qa_lib.mjs';

const t = createRunner('FF Voice Selbstheilung – Stall-Recovery');

function installSpeechFault(win, { finishOnAttempt = 2 } = {}) {
  const attempts = [];
  let generation = 0;
  let speaking = false;
  const voices = [
    { name: 'Microsoft Conrad Online (Natural) - German (Germany)', lang: 'de-DE', localService: false },
  ];

  win.speechSynthesis = {
    get speaking() { return speaking; },
    get paused() { return false; },
    get pending() { return false; },
    getVoices: () => voices.slice(),
    addEventListener() {},
    removeEventListener() {},
    speak(utterance) {
      const myGeneration = ++generation;
      const attempt = attempts.push({ utterance, generation: myGeneration });
      speaking = true;
      setTimeout(() => {
        if (myGeneration !== generation) return;
        utterance.onstart?.();
        if (attempt >= finishOnAttempt) {
          setTimeout(() => {
            if (myGeneration !== generation) return;
            speaking = false;
            utterance.onend?.();
          }, 8);
        }
      }, 2);
    },
    cancel() {
      generation += 1;
      speaking = false;
    },
    pause() {},
    resume() {},
  };
  return { attempts };
}

/* ------------------------------------------------------------ */
t.group('1) Ein onstart ohne onend wird automatisch geheilt');
{
  const { win, doc } = loadPage(skeleton({
    title: 'Selbstheilung – Satz hängt',
    speechStallTimeoutMs: 28,
    bodyHtml: '<h2>Stabiler Vorleseweg</h2><p>Dieser Satz wird beim ersten Versuch gestartet und bleibt danach hängen.</p>',
  }), {
    setup: (pageWin) => { pageWin.__fault = installSpeechFault(pageWin, { finishOnAttempt: 2 }); },
  });
  const api = win.__ffVoice;
  doc.getElementById('ff-voice-play').click();
  await sleep(280);

  t.ok('Lauf bleibt nach einer Heilung bedienbar', api.health.speechRecoveries >= 1,
    JSON.stringify(api.health));
  t.ok('Hänger wird messbar erkannt', api.health.speechStalls >= 1,
    JSON.stringify(api.health));
  t.ok('Satz wird mindestens einmal erneut angesetzt', win.__fault.attempts.length >= 2,
    'Versuche: ' + win.__fault.attempts.length);
  t.ok('Kein falsches Abschlussereignis während der Heilung',
    !/Vorlesen beendet/.test(doc.getElementById('ff-voice-status').textContent));
  api.stop();
}

/* ------------------------------------------------------------ */
t.group('2) Eine unerwartete Tonspur-Pause startet sich selbst neu');
{
  const { win, doc } = loadPage(skeleton({
    title: 'Selbstheilung – Tonspur-Pause',
    track: {
      src: '/audio/articles/recovery.wav',
      duration: 30000,
      chunks: [
        { b: 0, t0: 0, t1: 7500, lang: 'de' },
        { b: 1, t0: 7500, t1: 15000, lang: 'de' },
        { b: 2, t0: 15000, t1: 22500, lang: 'de' },
        { b: 3, t0: 22500, t1: 30000, lang: 'de' },
      ],
    },
    bodyHtml: '<h2>Stabile Tonspur</h2><p>Eine unerwartete Pause darf den Premium-Lauf nicht einfrieren.</p>',
  }));
  const api = win.__ffVoice;
  const media = doc.querySelector('audio');
  let paused = true;
  Object.defineProperty(media, 'paused', { configurable: true, get: () => paused });
  Object.defineProperty(media, 'duration', { configurable: true, value: 30 });
  doc.getElementById('ff-voice-play').click();
  media.dispatchEvent(new win.Event('pause'));
  await sleep(520);
  media.dispatchEvent(new win.Event('pause'));
  await sleep(620);

  t.ok('Tonspur-Recovery wird gezählt', api.health.trackRecoveries >= 2,
    JSON.stringify(api.health));
  t.eq('Nach wiederholter Pause übernimmt die Gerätestimme', api.mode, 'speech');
  t.ok('Lesen bleibt bedienbar', api.reading === true);
  t.ok('Grund der Übernahme bleibt sichtbar', /übernimmt|takes over/i.test(doc.getElementById('ff-voice-status').textContent),
    doc.getElementById('ff-voice-status').textContent);
  api.stop();
}

/* ------------------------------------------------------------ */
t.group('3) Ein dauerhafter Hänger endet ehrlich statt Text zu überspringen');
{
  const { win, doc } = loadPage(skeleton({
    title: 'Selbstheilung – dauerhaft stumm',
    speechStallTimeoutMs: 24,
    bodyHtml: '<h2>Grenze des Geräts</h2><p>Auch ein dauerhaft blockierter Sprachdienst darf die Seite nicht einfrieren.</p>',
  }), {
    setup: (pageWin) => { pageWin.__fault = installSpeechFault(pageWin, { finishOnAttempt: Infinity }); },
  });
  const api = win.__ffVoice;
  doc.getElementById('ff-voice-play').click();
  await sleep(620);

  t.eq('Lauf wird nach begrenzten Versuchen beendet', api.reading, false);
  t.ok('Mindestens zwei Stall-Zyklen erkannt', api.health.speechStalls >= 2,
    JSON.stringify(api.health));
  t.ok('Mindestens eine automatische Wiederholung', api.health.speechRecoveries >= 1,
    JSON.stringify(api.health));
  t.ok('Status benennt den Hänger', /hängt|hängt|stalled/i.test(doc.getElementById('ff-voice-status').textContent),
    doc.getElementById('ff-voice-status').textContent);
  t.ok('Kein falsches „Vorlesen beendet“',
    !/Vorlesen beendet/.test(doc.getElementById('ff-voice-status').textContent));
}

t.done();
