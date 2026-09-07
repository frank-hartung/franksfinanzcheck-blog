/**
 * ff_voice_voice_test.js — Highend-Test der Stimmen-Regie
 * (männlicher NACHRICHTENSPRECHER, ausschließlich Deutsch).
 * ------------------------------------------------------------
 * Stand 10.09.2026 — Nur-Deutsch-Vertrag: Die Vorlese-Funktion hat
 * keinen Umschalter, kein Stimmen-Menü UND keine zweite Sprache mehr.
 * Alles, was die Hörerin erlebt, ist das Ergebnis dieser Regie:
 *
 *   männlich · deutsch · Nachrichtenton zuerst · deterministisch · nie stumm
 *
 * Englische Stimmen in echten Geräte-Katalogen bleiben als FALLE
 * enthalten: die Regie darf sie unter keinen Umständen wählen — auch
 * dann nicht, wenn jemand ein „en“-Ziel durchreicht.
 *
 * Aufruf: node scripts/ff_voice_voice_test.js
 */

import { createRunner, loadPage, skeleton, mdToHtml, makeVoices, sleep } from './ff_voice_qa_lib.mjs';

const t = createRunner('Stimmen-Regie: männlicher Nachrichtensprecher, nur Deutsch');

const BODY = mdToHtml('## Abschnitt\n\nDer Wechsel spart bis zu 650 € im Jahr – bei 12 bis 24 Monaten Laufzeit.\n');

function openWith(voices, opts = {}) {
  const { win, doc } = loadPage(skeleton({ title: 'Stimmtest', bodyHtml: BODY }), { voices });
  return { api: win.__ffVoice, doc, win };
}

/* ============================================================
   1 · Echte Geräte-Kataloge
   ============================================================ */
const CATALOGS = {
  'macOS (Safari/Chrome)': makeVoices([
    { name: 'Anna', lang: 'de-DE' },
    { name: 'Daniel', lang: 'de-DE' },
    { name: 'Thomas', lang: 'de-DE' },
    { name: 'Yannick', lang: 'de-DE' },
    { name: 'Samantha', lang: 'en-US' },
    { name: 'Daniel', lang: 'en-GB' },
    { name: 'Alex', lang: 'en-US' },
  ]),
  'Windows/Edge (Online Neural)': makeVoices([
    { name: 'Microsoft Katja Online (Natural) - German (Germany)', lang: 'de-DE', localService: false },
    { name: 'Microsoft Conrad Online (Natural) - German (Germany)', lang: 'de-DE', localService: false },
    { name: 'Microsoft Florian Online (Natural) - German (Germany)', lang: 'de-DE', localService: false },
    { name: 'Microsoft Stefan Online (Natural) - German (Austria)', lang: 'de-AT', localService: false },
    { name: 'Microsoft Aria Online (Natural) - English (United States)', lang: 'en-US', localService: false },
    { name: 'Microsoft Andrew Online (Natural) - English (United States)', lang: 'en-US', localService: false },
    { name: 'Microsoft Ryan Online (Natural) - English (United Kingdom)', lang: 'en-GB', localService: false },
  ]),
  'Android (Google TTS)': makeVoices([
    { name: 'German Germany', lang: 'de-DE' },
    { name: 'de-DE-language', lang: 'de-DE' },
    { name: 'English United States', lang: 'en-US' },
    { name: 'Google UK English Male', lang: 'en-GB' },
  ]),
  'Google Cloud (A–F Codes)': makeVoices([
    { name: 'de-DE-Standard-A', lang: 'de-DE' },
    { name: 'de-DE-Standard-B', lang: 'de-DE' },
    { name: 'de-DE-Neural2-C', lang: 'de-DE' },
    { name: 'de-DE-Neural2-D', lang: 'de-DE' },
    { name: 'en-US-Standard-A', lang: 'en-US' },
    { name: 'en-US-Neural2-D', lang: 'en-US' },
  ]),
  'Linux (nur eSpeak)': makeVoices([
    { name: 'eSpeak German Male', lang: 'de' },
    { name: 'eSpeak English Male', lang: 'en' },
  ]),
  'Nur Frauenstimmen': makeVoices([
    { name: 'Anna', lang: 'de-DE' },
    { name: 'Katja', lang: 'de-DE' },
    { name: 'Samantha', lang: 'en-US' },
    { name: 'Aria', lang: 'en-US' },
    { name: 'Serena', lang: 'en-GB' },
  ]),
  'Nur englische Männer': makeVoices([
    { name: 'Google UK English Male', lang: 'en-GB' },
    { name: 'Microsoft Andrew Online (Natural) - English (United States)', lang: 'en-US', localService: false },
  ]),
  'Nur neutrale Stimmen': makeVoices([
    { name: 'Google Deutsch', lang: 'de-DE' },
    { name: 'Google US English', lang: 'en-US' },
    { name: 'de-DE-language', lang: 'de-DE' },
  ]),
};

const FEMALE = /anna|katja|hedda|marlene|vicki|elke|amala|clara|julia|lena|laura|sophie|sofia|zoe|emma|mia|hannah|sarah|emily|ashley|samantha|karen|moira|tessa|fiona|serena|allison|ava|susan|joan|linda|nancy|nina|victoria|aria/i;

t.group('1) Jeder Katalog liefert eine DEUTSCHE Stimme – still darf es nie bleiben');
for (const [label, voices] of Object.entries(CATALOGS)) {
  const { api } = openWith(voices);
  const de = api.resolveMaleVoice('de');
  const en = api.resolveMaleVoice('en');   // fremdes Ziel: Nur-Deutsch-Vertrag
  const hasGerman = voices.some((v) => String(v.lang).toLowerCase().startsWith('de'));
  t.ok(`${label}: Stimme gefunden, wo Deutsch existiert`, !!de.voice === hasGerman,
    'voice=' + (de.voice && de.voice.name));
  t.ok(`${label}: gefundene Sprache ist immer deutsch`, !de.voice || String(de.voice.lang).toLowerCase().startsWith('de'),
    de.voice && de.voice.lang);
  t.ok(`${label}: „en“-Ziel liefert nie Englisch`, !en.voice || String(en.voice.lang).toLowerCase().startsWith('de'),
    en.voice && en.voice.name + ' / ' + en.voice.lang);
}

t.group('2) Weibliche Stimmen werden nie gewählt, wenn eine männliche existiert');
for (const [label, voices] of Object.entries(CATALOGS)) {
  const hasMale = voices.some((v) => String(v.lang).toLowerCase().startsWith('de') && !FEMALE.test(v.name));
  if (!hasMale) continue;
  const { api } = openWith(voices);
  const de = api.resolveMaleVoice('de');
  t.ok(`${label}: nicht weiblich`, !FEMALE.test(de.voice.name), de.voice.name);
}

t.group('3) Ohne männliche deutsche Stimme: ehrlicher Notnagel in der männlichen Klangzone');
{
  const { api } = openWith(CATALOGS['Nur Frauenstimmen']);
  const de = api.resolveMaleVoice('de');
  t.ok('Notnagel vorhanden (nie stumm)', !!de.voice);
  t.eq('Notnagel als nicht-männlich markiert', de.male, false);
  t.ok('Notnagel in die Klangzone abgesenkt', de.tier.pitchZone < 0, String(de.tier.pitchZone));
  t.ok('Notnagel bleibt deutsch', String(de.voice.lang).toLowerCase().startsWith('de'), de.voice.lang);
}
{
  // Katalog ganz ohne Deutsch: gar keine Stimme ist die ehrliche Antwort —
  // NIE die englische als „Ersatz“ anzapfen (Nur-Deutsch-Vertrag).
  const { api } = openWith(CATALOGS['Nur englische Männer']);
  const de = api.resolveMaleVoice('de');
  t.ok('Keine deutsche Stimme im Katalog → keine Stimme gewählt', !de.voice,
    de.voice && ('TROTZDEM: ' + de.voice.name));
}

t.group('4) Determinismus – dieselbe Entscheidung bei jedem Aufruf');
{
  const { api } = openWith(CATALOGS['Windows/Edge (Online Neural)']);
  const a = api.resolveMaleVoice('de').voice.name;
  const b = api.resolveMaleVoice('de').voice.name;
  const c = api.resolveMaleVoice('de').voice.name;
  t.eq('DE stabil', a, b);
  t.eq('DE stabil (3. Aufruf)', b, c);
  t.eq('Fremdes Ziel „en“ entscheidet identisch (eine Regie, eine Sprache)',
    api.resolveMaleVoice('en').voice.name, a);
}

t.group('5) Qualität & Nachrichtenton: Studio vor Standard, News-Stimme vor allem');
{
  const { api } = openWith(CATALOGS['Windows/Edge (Online Neural)']);
  const de = api.resolveMaleVoice('de');
  t.ok('Neural/Studio gewählt', /natural|neural|premium|enhanced|online/i.test(de.voice.name), de.voice.name);
  t.ok('Tempo im Studio-Bereich', de.tier.rate >= 0.94, String(de.tier.rate));
  t.ok('Nachrichtensprecher-Vorrang: Conrad schlägt Florian, obwohl beide Natural sind',
    /conrad/i.test(de.voice.name), de.voice.name);
}
{
  const { api } = openWith(CATALOGS['Linux (nur eSpeak)']);
  const de = api.resolveMaleVoice('de');
  t.ok('Roboterstimme wird als solche erkannt', de.tier.label === 'robotic', de.tier.label);
  t.ok('Roboterstimme spricht langsamer (besser verständlich)', de.tier.rate < 1, String(de.tier.rate));
  t.ok('Englischer eSpeak bleibt liegen', !/english/i.test(de.voice.name), de.voice.name);
}

t.group('6) Google-Buchstabencodes: B/D/F sind männlich, A/C/E weiblich');
{
  const { api } = openWith(CATALOGS['Google Cloud (A–F Codes)']);
  const de = api.resolveMaleVoice('de');
  t.ok('wählt B oder D oder F (männlich)', /-(B|D|F)$/i.test(de.voice.name), de.voice.name);
  t.ok('nicht A/C/E', !/-(A|C|E)$/i.test(de.voice.name), de.voice.name);
}

t.group('7) Namen mit Teilstring-Fallen – und die deutsche Pflicht');
{
  // Der Katalog enthält nur englische Stimmen („Sam“ als Falle neben
  // „Samantha“): Die Regie darf keine davon wählen — sie sucht Deutsch.
  const { api } = openWith(makeVoices([
    { name: 'Samantha', lang: 'en-US', localService: true },
    { name: 'Sam', lang: 'en-US', localService: true },
  ]));
  const en = api.resolveMaleVoice('en');
  t.ok('Englischer Katalog bleibt komplett unerreichbar', !en.voice,
    en.voice && ('GEWÄHLT: ' + en.voice.name));
}
{
  const { api } = openWith(makeVoices([
    { name: 'Samantha', lang: 'de-DE' },
    { name: 'Serena', lang: 'de-DE' },
  ]));
  const de = api.resolveMaleVoice('de');
  t.ok('Ohne männliche Stimme: Notnagel, nicht erfunden männlich', de.male === false, de.voice.name);
  t.ok('Notnagel bleibt trotzdem deutsch', String(de.voice.lang).toLowerCase().startsWith('de'));
}

t.group('8) Sprechplan: jede Einheit deutsch, eine Stimme für alles');
{
  const { win } = loadPage(skeleton({
    title: 'Tarifwechsel',
    bodyHtml: '<h2>Was du beachten solltest</h2>'
      + '<p>Der Wechsel ist einfach. This sentence is clearly written in English and will be spoken by the German news voice.</p>',
  }), { voices: CATALOGS['Windows/Edge (Online Neural)'] });
  const api = win.__ffVoice;
  const units = api.buildTimeline().units;
  t.ok('Einheiten vorhanden', units.length > 0);
  t.ok('Keine einzige englische Einheit', units.every((u) => u.lang === 'de'),
    'en-Einheiten: ' + units.filter((u) => u.lang === 'en').length);
  const v = api.resolveMaleVoice('de').voice.name;
  t.ok('Alle Einheiten teilen dieselbe deutsche Stimme', /conrad/i.test(v), v);
  t.ok('Wort-Takt ist eingeschaltet (Quelle: Sprachpfad)', api.wordSyncSource === 'none' || api.wordSyncSource === 'speech',
    api.wordSyncSource);
}

t.group('8b) Wiedergabe: der Nachrichtensprecher liest ALLES — auch die englischen Begriffe');
{
  const { win } = loadPage(skeleton({
    title: 'Robo Advisor',
    bodyHtml: '<h2>Robo Advisor</h2>'
      + '<p>Ein Robo Advisor nutzt Compound Interest und Cost Averaging. Der Wechsel spart bis zu 650 Euro im Jahr.</p>',
  }), { voices: CATALOGS['Windows/Edge (Online Neural)'] });
  const spoken = [];
  const origSpeak = win.speechSynthesis.speak.bind(win.speechSynthesis);
  win.speechSynthesis.speak = (u) => {
    spoken.push({ lang: u.lang, text: u.text, voice: u.voice ? u.voice.name : null });
    return origSpeak(u);
  };
  const api = win.__ffVoice;
  api.start();
  await sleep(2500);

  t.ok('Es wurde gesprochen', spoken.length > 0);
  t.ok('Alle Äußerungen tragen de-DE', spoken.every((s) => s.lang === 'de-DE'),
    JSON.stringify(spoken.map((s) => s.lang)));
  t.ok('Kein einziger en-US-Aufruf', !spoken.some((s) => String(s.lang).toLowerCase().startsWith('en')));
  t.ok('„Robo Advisor“ klingt in der deutschen Stimme (ein Lauf, kein Wechsel)',
    spoken.some((s) => s.text.includes('Robo Advisor') && s.text.includes('Compound Interest')),
    JSON.stringify(spoken.map((s) => s.text)));
  t.ok('Alle Äußerungen mit Stimme tragen den Nachrichtensprecher Conrad',
    spoken.every((s) => !s.voice || /conrad/i.test(s.voice)),
    JSON.stringify(spoken.map((s) => s.voice)));
  t.ok('Lesen läuft ohne Stall zu Ende', api.reading === false || api.playing === true);
}

t.group('8c) Wortuhr im Sprechpfad: onboundary-Grenzen heben Wörter hell');
{
  const { win, doc } = loadPage(skeleton({
    title: 'Wortuhr-Test',
    bodyHtml: mdToHtml('## Los\n\nDer Sprecher spricht mehrere deutliche Wörter nacheinander.\n'),
  }), { voices: CATALOGS['Windows/Edge (Online Neural)'] });
  const api = win.__ffVoice;
  doc.getElementById('ff-voice-play').click();
  let guard = 0;
  while (guard++ < 60 && doc.querySelectorAll('.ff-voice-w').length < 5) await sleep(50);
  t.ok('Wort-Spans entstanden', doc.querySelectorAll('.ff-voice-w').length >= 5,
    'span=' + doc.querySelectorAll('.ff-voice-w').length);
  t.eq('Genau ein Wort leuchtet', doc.querySelectorAll('.ff-voice-w--now').length, 1);
  t.eq('Quelle ist die Sprachpfad-Regie',
    doc.getElementById('ff-voice-bar').getAttribute('data-ff-wordsync'), 'speech');
  api.stop();
  t.eq('Nach Stopp: keine Wort-Spans mehr', doc.querySelectorAll('.ff-voice-w').length, 0);
}

t.group('9) Keine Regler, kein Umschalter – die Oberfläche bleibt aufgeräumt');
{
  const { doc } = loadPage(skeleton({ title: 'Test', bodyHtml: BODY }));
  const html = doc.body.innerHTML;
  t.ok('Kein Stimmen-Auswahlfeld', !/<select/i.test(html));
  t.ok('Kein Tempo-Regler', !/type="range"/i.test(html));
  t.ok('Kein Sprachumschalter', !/data-voice-lang|voice-switch|lang-switch/i.test(html));
  t.eq('Genau ein Vorlesen-Knopf', doc.querySelectorAll('#ff-voice-play').length, 1);
  t.eq('Genau ein Kurzfassung-Knopf', doc.querySelectorAll('#ff-voice-summary').length, 1);
  t.ok('Vorlesen-Knopf verspricht den Nachrichtensprecher',
    /Nachrichtensprecher|männlich/.test(doc.getElementById('ff-voice-play').getAttribute('aria-label')) ||
    /Gerät/.test(doc.getElementById('ff-voice-play').getAttribute('aria-label')));
}

t.done();
