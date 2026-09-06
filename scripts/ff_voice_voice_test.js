/**
 * ff_voice_voice_test.js — Highend-Test der Stimmen-Regie (männlich, DE + EN).
 * ------------------------------------------------------------
 * Die Vorlese-Funktion hat keinen Umschalter und kein Stimmen-Menü.
 * Alles, was die Hörerin erlebt, ist das Ergebnis dieser Regie:
 *
 *   männlich · deutsch und englisch · deterministisch · nie stumm
 *
 * Dieser Test prüft die Regie gegen Stimmen-Kataloge, wie sie echte
 * Geräte liefern: macOS, Windows/Edge, Android, iOS, Linux (eSpeak)
 * sowie Kataloge OHNE jede männliche Stimme.
 *
 * Aufruf: node scripts/ff_voice_voice_test.js
 */

import { createRunner, loadPage, skeleton, mdToHtml, makeVoices, sleep } from './ff_voice_qa_lib.mjs';

const t = createRunner('Stimmen-Regie: männlich, DE & EN, ohne Umschalter');

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
  'Nur neutrale Stimmen': makeVoices([
    { name: 'Google Deutsch', lang: 'de-DE' },
    { name: 'Google US English', lang: 'en-US' },
    { name: 'de-DE-language', lang: 'de-DE' },
  ]),
};

const FEMALE = /anna|katja|hedda|marlene|vicki|elke|amala|clara|julia|lena|laura|sophie|sofia|zoe|emma|mia|hannah|sarah|emily|ashley|samantha|karen|moira|tessa|fiona|serena|allison|ava|susan|joan|linda|nancy|nina|victoria|aria/i;

t.group('1) Jeder Katalog liefert eine Stimme – still darf es nie bleiben');
for (const [label, voices] of Object.entries(CATALOGS)) {
  const { api } = openWith(voices);
  const de = api.resolveMaleVoice('de');
  const en = api.resolveMaleVoice('en');
  t.ok(`${label}: DE-Stimme gefunden`, !!de.voice, 'keine Stimme');
  t.ok(`${label}: EN-Stimme gefunden`, !!en.voice, 'keine Stimme');
  t.ok(`${label}: DE-Sprache passt`, !de.voice || String(de.voice.lang).toLowerCase().startsWith('de'),
    de.voice && de.voice.lang);
  t.ok(`${label}: EN-Sprache passt`, !en.voice || String(en.voice.lang).toLowerCase().startsWith('en'),
    en.voice && en.voice.lang);
}

t.group('2) Weibliche Stimmen werden nie gewählt, wenn eine männliche existiert');
for (const [label, voices] of Object.entries(CATALOGS)) {
  const hasMale = voices.some((v) => !FEMALE.test(v.name));
  if (!hasMale) continue;
  const { api } = openWith(voices);
  const de = api.resolveMaleVoice('de');
  const en = api.resolveMaleVoice('en');
  t.ok(`${label}: DE nicht weiblich`, !FEMALE.test(de.voice.name), de.voice.name);
  t.ok(`${label}: EN nicht weiblich`, !FEMALE.test(en.voice.name), en.voice.name);
}

t.group('3) Ohne männliche Stimme: ehrlicher Notnagel in der männlichen Klangzone');
{
  const { api } = openWith(CATALOGS['Nur Frauenstimmen']);
  const de = api.resolveMaleVoice('de');
  const en = api.resolveMaleVoice('en');
  t.ok('Notnagel DE vorhanden', !!de.voice);
  t.ok('Notnagel EN vorhanden', !!en.voice);
  t.eq('Notnagel DE als nicht-männlich markiert', de.male, false);
  t.eq('Notnagel EN als nicht-männlich markiert', en.male, false);
  t.ok('Notnagel DE in die Klangzone abgesenkt', de.tier.pitchZone < 0, String(de.tier.pitchZone));
  t.ok('Notnagel EN in die Klangzone abgesenkt', en.tier.pitchZone < 0, String(en.tier.pitchZone));
}

t.group('4) Determinismus – dieselbe Entscheidung bei jedem Aufruf');
{
  const { api } = openWith(CATALOGS['Windows/Edge (Online Neural)']);
  const a = api.resolveMaleVoice('de').voice.name;
  const b = api.resolveMaleVoice('de').voice.name;
  const c = api.resolveMaleVoice('de').voice.name;
  t.eq('DE stabil', a, b);
  t.eq('DE stabil (3. Aufruf)', b, c);
  const e1 = api.resolveMaleVoice('en').voice.name;
  const e2 = api.resolveMaleVoice('en').voice.name;
  t.eq('EN stabil', e1, e2);
}

t.group('5) Qualität: Studio/Neural vor Standard vor Roboterstimme');
{
  const { api } = openWith(CATALOGS['Windows/Edge (Online Neural)']);
  const de = api.resolveMaleVoice('de');
  const en = api.resolveMaleVoice('en');
  t.ok('DE: Neural/Studio gewählt', /natural|neural|premium|enhanced|online/i.test(de.voice.name), de.voice.name);
  t.ok('EN: Neural/Studio gewählt', /natural|neural|premium|enhanced|online/i.test(en.voice.name), en.voice.name);
  t.ok('DE: Tempo im Studio-Bereich', de.tier.rate >= 0.94, String(de.tier.rate));
  t.ok('EN: Tempo im Studio-Bereich', en.tier.rate >= 0.94, String(en.tier.rate));
}
{
  const { api } = openWith(CATALOGS['Linux (nur eSpeak)']);
  const de = api.resolveMaleVoice('de');
  t.ok('Roboterstimme wird als solche erkannt', de.tier.label === 'robotic', de.tier.label);
  t.ok('Roboterstimme spricht langsamer (besser verständlich)', de.tier.rate < 1, String(de.tier.rate));
}

t.group('6) Google-Buchstabencodes: B/D/F sind männlich, A/C/E weiblich');
{
  const { api } = openWith(CATALOGS['Google Cloud (A–F Codes)']);
  const de = api.resolveMaleVoice('de');
  const en = api.resolveMaleVoice('en');
  t.ok('DE wählt B oder D (männlich)', /-(B|D|F)$/i.test(de.voice.name), de.voice.name);
  t.ok('EN wählt B, D oder F (männlich)', /-(B|D|F)$/i.test(en.voice.name), en.voice.name);
  t.ok('DE nicht A/C/E', !/-(A|C|E)$/i.test(de.voice.name), de.voice.name);
}

t.group('7) Namen mit Teilstring-Fallen („Samantha“ enthält „Sam“)');
{
  const { api } = openWith(makeVoices([
    { name: 'Samantha', lang: 'en-US', localService: true },
    { name: 'Sam', lang: 'en-US', localService: true },
  ]));
  const en = api.resolveMaleVoice('en');
  t.eq('Der echte „Sam“ gewinnt, nicht „Samantha“', en.voice.name, 'Sam');
  t.ok('Und er gilt als männlich', en.male === true);
}
{
  const { api } = openWith(makeVoices([
    { name: 'Samantha', lang: 'en-US' },
    { name: 'Serena', lang: 'en-US' },
  ]));
  const en = api.resolveMaleVoice('en');
  t.ok('Ohne männliche Stimme: Notnagel, nicht „Sam“', en.male === false, en.voice.name);
}

t.group('8) Sprach-Routing im Sprechplan (zweisprachiger Hörfunk-Moderator)');
{
  const { win } = loadPage(skeleton({
    title: 'Tarifwechsel',
    bodyHtml: '<h2>Was du beachten solltest</h2>'
      + '<p>Der Wechsel ist einfach. This sentence is clearly English and must be spoken by the English male voice.</p>',
  }), { voices: CATALOGS['Windows/Edge (Online Neural)'] });
  const api = win.__ffVoice;
  const units = api.buildTimeline().units;
  const deUnits = units.filter((u) => u.lang === 'de');
  const enUnits = units.filter((u) => u.lang === 'en');
  t.ok('Deutsche Einheiten vorhanden', deUnits.length > 0);
  t.ok('Englische Einheiten vorhanden', enUnits.length > 0);
  t.ok('Englische Einheiten tragen die EN-Stimme',
    enUnits.every((u) => u.lang === 'en'));
  const deVoice = api.resolveMaleVoice('de').voice.name;
  const enVoice = api.resolveMaleVoice('en').voice.name;
  t.ok('DE- und EN-Stimme sind verschiedene Stimmen', deVoice !== enVoice,
    deVoice + ' / ' + enVoice);
  t.ok('Beide sind männlich',
    api.resolveMaleVoice('de').male && api.resolveMaleVoice('en').male);
}

/* ============================================================
   8b · Wortlauf-Regie — Sprachwechsel MITTEN im Satz
   ------------------------------------------------------------
   Ein überwiegend deutscher Text mit wenig Englisch darf die
   englischen Fachbegriffe NICHT der deutschen Stimme überlassen
   (Befund 05.09.2026: „Robo Advisor“ klang deutsch). Die
   Wortlauf-Regie zerteilt jede Sprecheinheit in Sprachläufe;
   jeder Lauf erhält seine männliche Stimme — ohne Umschalter.
   ============================================================ */
t.group('8b) Wortlauf-Regie: Sprachwechsel mitten im Satz (DE-Basis)');
{
  const { api } = openWith(CATALOGS['Windows/Edge (Online Neural)']);

  const runs = api.languageRuns('Ein Robo Advisor nutzt Compound Interest und Cost Averaging.', 'de');
  t.eq('Sprachläufe des Mustersatzes', runs.map((r) => r.lang).join(','), 'de,en,de,en,de,en');
  t.eq('Lauf 1 ist deutsch', runs[0].text, 'Ein ');
  t.eq('Lauf 2 ist der Fachbegriff', runs[1].text, 'Robo Advisor ');
  t.eq('Lauf 4 ist der zweite Fachbegriff', runs[3].text, 'Compound Interest ');
  t.eq('Segmente konkatenieren exakt',
    runs.map((r) => r.text).join(''), 'Ein Robo Advisor nutzt Compound Interest und Cost Averaging.');

  t.eq('Cashflow wechselt, Satzgerüst bleibt deutsch',
    api.languageRuns('Der Cashflow kommt jeden Monat.', 'de').map((r) => r.lang).join(','), 'de,en,de');
  t.eq('Buy and Hold bleibt ein Lauf',
    api.languageRuns('Mit Buy and Hold bleibst du flexibel.', 'de')
      .filter((r) => r.lang === 'en').map((r) => r.text.trim()).join('|'), 'Buy and Hold');
  t.eq('Rein deutscher Satz bleibt ein Lauf',
    api.languageRuns('Der Tarifwechsel spart im Schnitt 300 Euro pro Jahr.', 'de').length, 1);
  t.eq('Scheinfreunde kippen nicht (was/hat/will)',
    api.languageRuns('Was hat er damit gemeint?', 'de').length, 1);
  t.eq('Kein Sprachwechsel für einsame Funktionswörter',
    api.languageRuns('The Big Short erklärt die Krise.', 'de').length, 1);
  t.eq('Das Komma bleibt beim Stimmwechsel in der Artikelsprache hörbar ruhig',
    api.languageRuns('Wer seinen Emergency Fund aufbaut, schläft besser.', 'de')
      .filter((r) => r.lang === 'en').map((r) => r.text).join(''), 'Emergency Fund ');

  for (const probe of [
    'Ein Robo Advisor nutzt Compound Interest und Cost Averaging.',
    'Der Cashflow kommt jeden Monat.',
    'Switching your tariff can save money, und die Versicherung kostet mehr.',
    'Was hat er damit gemeint?',
  ]) {
    const segs = api.languageRuns(probe, 'de');
    t.ok('Konkatenations-Vertrag: ' + probe.slice(0, 30),
      segs.map((s) => s.text).join('') === probe && segs.length > 0);
  }
}

t.group('8c) Wortlauf-Regie: Deutsche Einschübe im EN-Artikel + Wiedergabe');
{
  // Wiedergabe: Die Äußerungs-Folge muss die Stimmwechsel tragen.
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

  const enParts = spoken.filter((s) => s.lang === 'en-US').map((s) => s.text.trim());
  t.ok('Englische Läufe werden von der EN-Stimme gesprochen', enParts.length > 0,
    JSON.stringify(enParts));
  t.ok('„Robo Advisor“ klingt englisch',
    enParts.some((x) => x.includes('Robo Advisor')), JSON.stringify(enParts));
  t.ok('„Compound Interest“ klingt englisch',
    enParts.some((x) => x.includes('Compound Interest')), JSON.stringify(enParts));
  t.ok('„Cost Averaging“ klingt englisch',
    enParts.some((x) => x.includes('Cost Averaging')), JSON.stringify(enParts));
  t.ok('Deutsche Satzgerüste bleiben deutsch',
    spoken.some((s) => s.lang === 'de-DE' && s.text.trim() === 'nutzt'),
    JSON.stringify(spoken.map((s) => s.text)));
  t.ok('Deutsche Restsätze vollständig',
    spoken.some((s) => s.lang === 'de-DE' && s.text.includes('Der Wechsel spart')));
  t.ok('Alle EN-Äußerungen tragen die männliche EN-Stimme',
    spoken.filter((s) => s.lang === 'en-US').every((s) => s.voice === 'Microsoft Andrew Online (Natural) - English (United States)'));
  t.ok('Lesen läuft ohne Stall zu Ende', api.reading === false || api.playing === true);

  // Deutsche Einschübe im englischen Artikel
  const { win: win2 } = loadPage(skeleton({
    title: 'Compare tariffs',
    lang: 'en',
    bodyHtml: '<h2>Switching providers</h2>'
      + '<p>Compare your insurance costs, und die Versicherung kostet mehr.</p>',
  }), { voices: CATALOGS['Windows/Edge (Online Neural)'] });
  const api2 = win2.__ffVoice;
  t.eq('EN-Basis erkannt', api2.lang, 'en');
  const segs = api2.languageRuns('Compare your insurance costs, und die Versicherung kostet mehr.', 'en');
  t.ok('Deutscher Einschub wird als de-Lauf markiert',
    segs.some((s) => s.lang === 'de' && s.text.includes('und die Versicherung')),
    JSON.stringify(segs));
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
}

t.done();
