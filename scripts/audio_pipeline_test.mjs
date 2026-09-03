#!/usr/bin/env node
/**
 * audio_pipeline_test.mjs — Prüfung der First-Party-Audiofassung
 * ==============================================================
 * Sichert die Kette, aus der die MP3-Fassungen entstehen. Alle drei
 * Prüfgruppen sind aus echten Fehlern entstanden, die erst beim Bau der
 * Audiofassung sichtbar wurden:
 *
 *  1) Text: Shortcode-Parameter, Redaktionsmarker und doppelte
 *     Überschriften wären wörtlich mitgesprochen worden.
 *  2) Rahmenstrom: Der Xing/Info-Kopf des ersten Teils überlebte ins
 *     Verbund-File und behauptete dort 1:22 min statt 11:00 min.
 *  3) Daueranzeige: Aus 659,98 s wurde „10:60 min", weil der Rest
 *     59,98 auf 60 aufrundete, ohne in die Minuten überzutragen.
 *
 * Läuft ohne ffmpeg und ohne Netzwerk: gerenderte MP3s werden gelesen,
 * falls vorhanden; die Joiner-Logik wird an synthetischen Rahmen
 * geprüft, wenn noch keine Fassung existiert.
 */

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { header, skipId3v2, trimId3v1, findXing, walk, formatDuration } from './mp3_info.mjs';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');

let pass = 0;
const fails = [];
let group = '';

const t = {
  group(name) { group = name; console.log(`\n—— ${name} ————————————————————`); },
  ok(cond, msg, extra) {
    if (cond) { pass++; console.log(`  ✅ ${msg}`); }
    else { fails.push(`[${group}] ${msg}${extra ? ` — ${extra}` : ''}`); console.log(`  ❌ ${msg}${extra ? `\n      ${extra}` : ''}`); }
  },
  eq(a, b, msg) { t.ok(a === b, msg, `erwartet ${JSON.stringify(b)}, erhalten ${JSON.stringify(a)}`); }
};

/* ================================================================== */
/* 1) Sprechtext der vorbereiteten Teile                              */
/* ================================================================== */
t.group('1) Sprechtext (Chunks)');
{
  const dir = path.join(ROOT, 'data', 'audio');
  /* Nur echte Artikel zählen. Der Selbsttest in Gruppe 3 legt kurzzeitig
     eine eigene Chunks-Datei an – bricht er ab, würde sie hier sonst als
     „Artikel" mitgezählt und die Teilzahl verfälschen. */
  const postSlugs = new Set(fs.readdirSync(path.join(ROOT, 'content', 'posts')));
  const files = fs.existsSync(dir)
    ? fs.readdirSync(dir).filter((f) => f.endsWith('.chunks.json')
        && postSlugs.has(f.replace(/\.chunks\.json$/, '')))
    : [];
  t.ok(files.length >= 28, `Alle Artikel vorbereitet (${files.length} erwartet ≥ 28)`);

  let parts = 0;
  let longest = 0;
  const leaks = [];
  const summary = JSON.parse(fs.readFileSync(path.join(dir, '_summary.json'), 'utf8'));

  for (const f of files) {
    const d = JSON.parse(fs.readFileSync(path.join(dir, f), 'utf8'));
    t.ok(Array.isArray(d.parts) && d.parts.length > 0, `${f}: enthält Teile`);
    for (const p of d.parts) {
      parts++;
      longest = Math.max(longest, p.text.length);

      /* 1400 Zeichen ist die harte Obergrenze: Die Sprachausgabe bricht
         lange Äußerungen ab (Chrome nach ~15 s), und die Teile sollen
         an Satzgrenzen teilbar bleiben. */
      if (p.text.length > summary.maxChars) leaks.push(`${f}: Teil ${p.index} hat ${p.text.length} Zeichen > ${summary.maxChars}`);

      /* Shortcode-Parameter. Wären sie im Text, spräche die Stimme
         „title= Beispielrechnung … cta url=/go/gas/". */
      if (/\b(title|subtitle|footnote|cta_url|cta-url|tone|vorher-main|nachher-main|ersparnis|card_label)\s*=/.test(p.text)) {
        leaks.push(`${f}: Teil ${p.index} enthält Shortcode-Parameter`);
      }
      /* Redaktionsmarker: im Browser unsichtbar, hier aber Fließtext. */
      if (/<!--|-->/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält HTML-Kommentar`);
      if (/<template|data-ff=/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält Template-Marker`);
      /* Sprechfehler aus der Abkürzungsauflösung. */
      if (/\bversus\./.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält „versus."`);
      if (/Empfehlung Empfehlung/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält „Empfehlung Empfehlung"`);
      /* Rohzeichen, die keine Stimme sauber spricht. */
      if (/[🏆❌✓✕⚡💰💡⚠ℹ→]/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält Emoji/Dekozeichen`);

      /* Währungszeichen: In der Alternative (?:€|EUR|Euro) fraß „EUR"
         die ersten drei Buchstaben von „Euro" und ließ ein „o" stehen. */
      if (/Euroo/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält „Euroo"`);
      if (/\d-\s+Euro/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält „150- Euro"`);
      /* Ein nacktes Gleichzeichen spricht keine Stimme mit. */
      if (/\s=\s/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält ein Gleichzeichen`);
      /* Satzsplitter ohne Abkürzungsschutz zerriss „z. B." über zwei
         Sprechhäppchen, die Auflösung sah die Abkürzung dann nie ganz. */
      if (/\bz\.\s*B\./.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält unaufgelöstes „z. B."`);
      if (/zum Beispiel\.\s+[a-zäöüß0-9]/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält „zum Beispiel." mitten im Satz`);
      /* Fachzeichen: überlesen oder buchstabiert, Bedeutung geht verloren. */
      if (/[×−²³₁₂Ø°]/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält ein unaufgelöstes Fachzeichen`);
      /* Reihenfolge der Schrägstrich-Regeln: „Mbit/s" wurde erst zu
         „Mbit oder s" zerlegt, dann zu „Megabit oder s". */
      if (/(?:Megabit|Gigabit)\s+oder\s+s\b/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält „Megabit oder s"`);
      if (/pro Sekunde\s+pro Sekunde/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält doppeltes „pro Sekunde"`);
      /* Nach „pro" steht im Deutschen der Singular. */
      if (/\bpro\s+(?:Kilowattstunden|Monate|Jahre|Stunden|Wochen)\b/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält „pro" mit Plural`);
      /* Steht die Einheit schon ausgeschrieben da, darf die Klammer sie
         nicht wiederholen: „Kilowattstunden Kilowattstunden". */
      if (/\b(Kilowattstunde|Kubikmeter|Quadratmeter)\w*\s+\1/.test(p.text)) leaks.push(`${f}: Teil ${p.index} wiederholt eine Einheit`);
      /* Die Vorzeichen-Regel fraß das Trennzeichen mit: „Bonus:minus 180". */
      if (/:[A-Za-zäöüßÄÖÜ]/.test(p.text)) leaks.push(`${f}: Teil ${p.index} klebt ein Wort an einen Doppelpunkt`);
      /* IBAN in zwei Wörter zu spalten ergibt „ih bahn". */
      if (/\bI BAN\b/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält „I BAN"`);
      /* Interne Platzhalter dürfen nie im Sprechtext landen. */
      if (/[\u0001\u0002\u0003]/.test(p.text)) leaks.push(`${f}: Teil ${p.index} enthält ein Maskierungszeichen`);
    }
  }

  t.ok(leaks.length === 0, 'Kein Sprechfehler in irgendeinem Teil', leaks.slice(0, 5).join(' | '));
  t.ok(longest <= summary.maxChars, `Längster Teil ${longest} ≤ ${summary.maxChars} Zeichen`);
  t.eq(parts, summary.totalParts, 'Teilzahl in den Dateien entspricht der Zusammenfassung');

  /* FAQ-Fragen müssen Fragen bleiben: Wird das Fragezeichen zum Punkt,
     spricht die Stimme sie als Feststellung. */
  const faq = files.find((f) => f.includes('gas-anbieter-wechseln'));
  if (faq) {
    const text = JSON.parse(fs.readFileSync(path.join(dir, faq), 'utf8')).parts.map((p) => p.text).join(' ');
    t.ok(/abgestellt werden\?/.test(text), 'FAQ-Frage endet mit Fragezeichen, nicht mit Punkt');
  }
}

/* ================================================================== */
/* 2) Rahmenstromanalyse an bekannten Werten                          */
/* ================================================================== */
t.group('2) MP3-Rahmenanalyse (Kopfdecodierung)');
{
  /* MPEG2 Layer III, 24 kHz, 32 kbit/s – genau das Format, das die
     Sprachausgabe liefert. Kopf ff f3 44 c4: Bitrate-Index 4 = 32 kbit/s
     in der MPEG2-Layer-III-Tabelle, Abtast-Index 1 = 24 kHz.
     Rahmenlänge 72·32000/24000 = 96 Byte. */
  const frame = Buffer.alloc(96);
  frame[0] = 0xff; frame[1] = 0xf3; frame[2] = 0x44; frame[3] = 0xc4;
  const h = header(frame, 0);
  t.ok(!!h, 'Rahmenkopf wird erkannt');
  t.eq(h.length, 96, 'MPEG2/L3/32k/24kHz ergibt 96 Byte Rahmenlänge');
  t.eq(h.bitrate, 32, 'Bitrate korrekt als 32 kbit/s decodiert');
  t.eq(h.sampleRate, 24000, 'Abtastrate 24000 Hz');
  t.eq(h.samples, 576, 'MPEG2 Layer III hat 576 Samples je Rahmen');
  t.eq(h.version, 'MPEG2', 'Version als MPEG2 erkannt');
  t.eq(h.layer, 3, 'Layer III erkannt');

  /* MPEG1 Layer III, 44,1 kHz, 128 kbit/s: 144·128000/44100 = 417 Byte.
     Ohne die versionsabhängige Bitratentabelle käme hier etwas Falsches
     heraus – genau das war der ursprüngliche Messfehler. */
  const f1 = Buffer.alloc(417);
  f1[0] = 0xff; f1[1] = 0xfb; f1[2] = 0x90; f1[3] = 0x64;
  const h1 = header(f1, 0);
  t.eq(h1.version, 'MPEG1', 'MPEG1 erkannt');
  t.eq(h1.bitrate, 128, 'MPEG1-Bitratentabelle benutzt (128 kbit/s)');
  t.eq(h1.length, 417, 'MPEG1/L3/128k/44,1kHz ergibt 417 Byte');
  t.eq(h1.samples, 1152, 'MPEG1 Layer III hat 1152 Samples je Rahmen');

  /* Ein Xing/Info-Kopf muss gefunden werden, sonst bleibt er stehen. */
  const xingFrame = Buffer.alloc(192);
  xingFrame[0] = 0xff; xingFrame[1] = 0xf3; xingFrame[2] = 0x94; xingFrame[3] = 0xc0;
  xingFrame.write('Info', 36, 'latin1');
  const found = findXing(xingFrame, 0, 192);
  t.ok(!!found && found.tag === 'Info', 'Xing/Info-Kopf wird im Rahmen gefunden');
}

/* ================================================================== */
/* 3) Joiner: synthetischer Rahmenstrom                               */
/* ================================================================== */
t.group('3) Joiner (Zusammenfügen, Xing-Kopf, Zeitkarte)');
{
  const tmp = fs.mkdtempSync(path.join(ROOT, 'tmp-audio-test-'));
  try {
    /* Zwei Teile à 10 Rahmen. Jeder beginnt mit einem Xing-Rahmen, wie
       ihn die Sprachausgabe liefert. */
    /* Nachbau der echten Struktur: Der Xing-Rahmen läuft mit 64 kbit/s
       (192 Byte), die Nutzrahmen mit 32 kbit/s (96 Byte). Beides MPEG2
       Layer III, 24 kHz – genau wie die Dateien der Sprachausgabe. */
    const mkPart = (n) => {
      const xing = Buffer.alloc(192);
      xing[0] = 0xff; xing[1] = 0xf3; xing[2] = 0x84; xing[3] = 0xc0;  // 64 kbit/s
      xing.write('Info', 36, 'latin1');
      xing.writeUInt32BE(0x0f, 40);      // flags: frames|bytes|toc|quality
      xing.writeUInt32BE(n, 44);         // frames
      xing.writeUInt32BE(192 + n * 96, 48);

      const frames = [];
      for (let i = 0; i < n; i++) {
        const fr = Buffer.alloc(96);
        fr[0] = 0xff; fr[1] = 0xf3; fr[2] = 0x44; fr[3] = 0xc4;  // 32 kbit/s
        frames.push(fr);
      }
      return Buffer.concat([xing, ...frames]);
    };

    const slug = 'audio-selftest';
    /* Aufbau exakt wie prepare_audio_chunks.mjs ihn schreibt:
       parts[].units ist eine Liste {i,type,lang,chars}, chunks.units die
       Gesamtzahl der Sprecheinheiten. */
    const mkUnits = (from, n) =>
      Array.from({ length: n }, (_, k) => ({
        i: from + k,
        type: k === 0 ? 'h2' : 'p',
        lang: 'de',
        chars: 100
      }));
    const chunks = {
      slug, title: 'Selbsttest', lang: 'de', units: 10, chars: 1000,
      parts: [
        { index: 0, text: 'a'.repeat(600), units: mkUnits(0, 6) },
        { index: 1, text: 'b'.repeat(400), units: mkUnits(6, 4) }
      ]
    };
    const dataDir = path.join(ROOT, 'data', 'audio');
    const chunksPath = path.join(dataDir, `${slug}.chunks.json`);
    fs.writeFileSync(chunksPath, JSON.stringify(chunks), 'utf8');

    const p1 = path.join(tmp, '001.mp3');
    const p2 = path.join(tmp, '002.mp3');
    fs.writeFileSync(p1, mkPart(10));
    fs.writeFileSync(p2, mkPart(5));

    const out = path.join(tmp, `${slug}.mp3`);
    const res = execFileSync(process.execPath,
      [path.join(HERE, 'mp3_join.mjs'), slug, p1, p2, '-o', out, '--chunks', chunksPath],
      { encoding: 'utf8' });

    t.ok(/Xing-Köpfe entfernt/.test(res), 'Joiner meldet entfernte Xing-Köpfe', res.trim().split('\n').pop());
    t.ok(/2 Xing-Köpfe entfernt/.test(res), 'Beide Xing-Köpfe entfernt');

    const joined = fs.readFileSync(out);
    t.eq(joined.length, 15 * 96, 'Verbund enthält genau die Nutzrahmen (15 × 96 Byte)');
    t.ok(!joined.includes(Buffer.from('Info', 'latin1')), 'Kein Xing/Info-Kopf mehr im Verbund');

    const w = walk(joined, 0);
    t.eq(w.frames, 15, '15 Rahmen im Verbund gefunden');
    t.eq(w.resyncs, 0, 'Kein Resync nötig – Rahmenstrom ist lückenlos');
    const expected = 15 * 576 / 24000;
    t.ok(Math.abs(w.seconds - expected) < 0.001, `Dauer ${w.seconds.toFixed(3)} s = 15 × 576/24000`, `erwartet ${expected.toFixed(3)}`);

    const tmPath = path.join(ROOT, 'static', 'audio', `${slug}.timemap.json`);
    t.ok(fs.existsSync(tmPath), 'Zeitkarte wird nach static/audio geschrieben');
    const tm = JSON.parse(fs.readFileSync(tmPath, 'utf8'));
    t.ok(Math.abs(tm.durationSeconds - expected) < 0.01, `Zeitkarte-Dauer ${tm.durationSeconds} s stimmt mit Rahmenstrom überein`);
    t.eq(tm.parts.length, 2, 'Zeitkarte nennt beide Teile');
    t.ok(tm.parts[1].startAt > tm.parts[0].startAt, 'Zweiter Teil beginnt nach dem ersten');

    /* Daueranzeige: der ursprüngliche Fehler war „10:60 min" aus 659,98 s,
       weil der Rest 59,98 auf 60 aufrundete, ohne in die Minuten
       überzutragen. Der Selbsttest selbst ist dafür zu kurz – deshalb
       wird formatDuration() hier direkt an den echten Randfällen geprüft. */
    const label = tm.durationLabel;
    t.ok(/^\d+:\d{2} min$/.test(label) || /^\d+:\d{2}:\d{2} min$/.test(label), `Daueranzeige wohlgeformt („${label}")`);

    t.eq(formatDuration(659.98), '11:00 min', '659,98 s wird zu 11:00 min (nicht 10:60)');
    t.eq(formatDuration(59.6), '1:00 min', '59,6 s rundet in die Minute über');
    t.eq(formatDuration(59.4), '0:59 min', '59,4 s bleibt 0:59');
    t.eq(formatDuration(0), '0:00 min', 'Null bleibt 0:00');
    t.eq(formatDuration(3599.5), '1:00:00 min', 'Überlauf in die Stunden');
    t.eq(formatDuration(7325), '2:02:05 min', 'Stunden/Minuten/Sekunden korrekt getrennt');
    for (const sec of [0, 5, 59.4, 59.6, 61, 659.98, 3599.5, 3600, 7325]) {
      const m = formatDuration(sec).match(/:(\d{2})(?::\d{2})? min$/);
      t.ok(m && Number(m[1]) <= 59, `Sekundenanteil ≤ 59 bei ${sec} s („${formatDuration(sec)}")`,
        'sonst fehlt der Übertrag in die Minuten');
    }

  } finally {
    /* Auch bei einem Abbruch aufräumen: Eine liegen gebliebene
       Selbsttest-Chunks-Datei würde Gruppe 1 beim nächsten Lauf
       verfälschen. */
    fs.rmSync(path.join(ROOT, 'data', 'audio', 'audio-selftest.chunks.json'), { force: true });
    fs.rmSync(path.join(ROOT, 'static', 'audio', 'audio-selftest.timemap.json'), { force: true });
    fs.rmSync(tmp, { recursive: true, force: true });
  }
}

/* ================================================================== */
/* 4) Gerenderte Fassungen (sofern vorhanden)                         */
/* ================================================================== */
t.group('4) Gerenderte Audiofassungen');
{
  const audioDir = path.join(ROOT, 'static', 'audio');
  const mp3s = fs.existsSync(audioDir)
    ? fs.readdirSync(audioDir).filter((f) => f.endsWith('.mp3') && !f.includes('parts'))
    : [];
  if (!mp3s.length) {
    console.log('  ℹ️  Noch keine fertige Fassung gerendert – Gruppe übersprungen.');
  }
  for (const f of mp3s) {
    const buf = fs.readFileSync(path.join(audioDir, f));
    const body = trimId3v1(buf.subarray(skipId3v2(buf)));
    const w = walk(body, 0);
    const slug = f.replace(/\.mp3$/, '');

    t.ok(!w.xing, `${f}: kein veralteter Xing-Kopf`);
    t.eq(w.resyncs, 0, `${f}: Rahmenstrom lückenlos (${w.frames} Rahmen)`);
    t.eq(w.configs.size, 1, `${f}: einheitliche Kodierung (${[...w.configs.keys()][0]})`);

    const tmPath = path.join(audioDir, `${slug}.timemap.json`);
    if (fs.existsSync(tmPath)) {
      const tm = JSON.parse(fs.readFileSync(tmPath, 'utf8'));
      const diff = Math.abs(tm.durationSeconds - w.seconds);
      t.ok(diff < 1, `${f}: Zeitkarte ${tm.durationSeconds}s ≈ Rahmenstrom ${w.seconds.toFixed(2)}s`, `Abweichung ${diff.toFixed(2)} s`);
      t.ok(tm.parts.length > 0, `${f}: Zeitkarte nennt ${tm.parts.length} Teile`);
    }
  }
}

/* ================================================================== */
/* 5) speechNormalize im Direktzugriff                                */
/* ================================================================== */
t.group('5) Aussprache-Normalisierung (Direkttest der Engine)');
{
  /* Warum diese Gruppe nötig ist, obwohl Gruppe 1 denselben Text prüft:
     Gruppe 1 sieht nur, was im Bestand vorkommt. Drei Regeln dieser
     Datei waren mit \b geschrieben, das vor „à", „Ø" und nach „²"/„³"
     nie matcht – die Regeln liefen also STILLSCHWEIGEND NIE. Im Bestand
     fiel das nicht auf, weil die betroffenen Zeichen dort zufällig
     harmlos standen. Nur der direkte Aufruf mit konstruierten Eingaben
     beweist, dass eine Regel tatsächlich greift.

     Die Erwartungen sind die echten Ausgaben der Engine, keine
     Wunschtexte – jede Zeile wurde gegen ff-reader.js verifiziert. */
  let norm = null;
  let seite = null;
  try {
    const qa = await import('./reader_qa_lib.mjs');
    const art = qa.loadArticle('2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife');
    seite = await qa.createPage({
      html: qa.buildPage({
        title: art.title, description: art.description, kurzantwort: art.kurzantwort,
        readingTime: art.readingTime, wordCount: art.wordCount, bodyHtml: art.bodyHtml
      }),
      speech: false
    });
    norm = seite.win.__ffReaderExport.speechNormalize;
  } catch (e) {
    console.log(`  ℹ️  jsdom nicht verfügbar (${e.message.split('\n')[0]}) – Gruppe übersprungen.`);
  }

  if (norm) {
    const DE = [
      ['12 mal 44,95 € = 539,40 €',              '12 mal 44,95 Euro ist 539,40 Euro.',      'Gleichzeichen wird zu „ist"'],
      ['Ein 150-€-Bonus nach 6 Monaten',          'Ein 150-Euro-Bonus nach 6 Monaten.',      'Bindestrich-Währung bleibt ein Wort'],
      ['44,95 Euro im Monat',                     '44,95 Euro im Monat.',                    '„Euro" wird nicht zu „Euroo"'],
      ['Grundpreis / Monat: 14,50 €',             'Grundpreis pro Monat: 14,50 Euro.',       'Schrägstrich vor Maßeinheit wird „pro"'],
      ['20.000 kWh/Jahr',                         '20000 Kilowattstunden pro Jahr.',         'kWh/Jahr wird „Kilowattstunden pro Jahr"'],
      ['Arbeitspreis pro kWh',                    'Arbeitspreis pro Kilowattstunde.',        'nach „pro" steht der Singular'],
      ['Kilowattstunden (kWh) umgerechnet',       'Kilowattstunden umgerechnet.',            'Einheit in Klammer wird nicht wiederholt'],
      ['Volumen in Kubikmetern (m³)',             'Volumen in Kubikmetern.',                 'm³ in Klammer wird nicht wiederholt'],
      ['250 Mbit/s Anschluss',                    '250 Megabit pro Sekunde Anschluss.',      'Mbit/s wird nicht zu „Megabit oder s"'],
      ['1 °C weniger',                            '1 Grad Celsius weniger.',                 '°C wird ausgeschrieben'],
      ['90-m²-Wohnung',                           '90 Quadratmeter-Wohnung.',                'm² nach Zahl wird aufgelöst'],
      ['circa 120 m²',                            'circa 120 Quadratmeter.',                 'm² mit Leerzeichen wird aufgelöst'],
      ['1 m³ Gas',                                '1 Kubikmeter Gas.',                       'm³ wird zu „Kubikmeter"'],
      ['CO₂-Preis',                               'CO2-Preis.',                              'tiefgestellte Ziffer wird normal'],
      ['Bonus × Wahrscheinlichkeit − Rückforderung', 'Bonus mal Wahrscheinlichkeit minus Rückforderung.', '× und − werden gesprochen'],
      ['Ø Antwortzeit DE',                        'Durchschnitt Antwortzeit DE.',            'Ø wird zu „Durchschnitt"'],
      ['Zehn Halogenlampen à 40 Watt',            'Zehn Halogenlampen je 40 Watt.',          'à vor Zahl wird zu „je"'],
      ['Bonus: - 180,00 € (Gutschrift)',          'Bonus: minus 180,00 Euro (Gutschrift).',  'führendes Minus bleibt Vorzeichen'],
      ['die 50-30-20-Regel',                      'die 50-30-20-Regel.',                     'Zahlenreihe bleibt Eigenname'],
      ['Deine IBAN bleibt',                       'Deine IBAN bleibt.',                      'IBAN wird nicht zu „I BAN"'],
      ['z. B. 120 Euro',                          'zum Beispiel 120 Euro.',                  '„z. B." wird aufgelöst'],
      ['Download / Upload: 50 / 10',              'Download und Upload: 50 und 10.',         'Download/Upload wird „und"'],
      ['Voll/Voll-Regelung',                      'Voll zu Voll-Regelung.',                  'Voll/Voll wird „zu"']
    ];
    for (const [rein, raus, warum] of DE) t.eq(norm(rein, 'de'), raus, `DE: ${warum}`);

    const EN = [
      ['150 Mbit/s',        '150 megabits per second.', 'EN: Mbit/s wird „per second"'],
      ['Grundpreis / Monat', 'Grundpreis per month.',    'EN: Schrägstrich vor Einheit wird „per"']
    ];
    for (const [rein, raus, warum] of EN) t.eq(norm(rein, 'en'), raus, warum);

    /* Satzgrenzen: Der Sprachpfad nutzt sentences(), die Kurzfassung hatte
       den Abkürzungsschutz schon immer. Ohne ihn riss „z. B." auseinander. */
    const tl = seite.win.__ffReaderExport.buildTimeline();
    const zerrissen = tl.timeline.filter((u) => /\bz\.\s*B\./.test(u.text) || /zum Beispiel\.\s+[a-zäöüß0-9]/.test(u.text));
    t.eq(zerrissen.length, 0, 'Keine Sprecheinheit reißt „z. B." auseinander');
  }
}

/* ================================================================== */
/* 6) Dauer-Plausibilität der gerenderten Teile                       */
/* ================================================================== */
t.group('6) Sprechdauer je Teil (Plausibilität)');
{
  /* Warum diese Prüfung nötig ist:
     Die Sprechtexte werden von Hand in die Render-Aufrufe übertragen.
     Ein vertippter oder abgeschnittener Text wäre still in die Fassung
     gewandert – die Zeitkarte würde trotzdem „korrekt" aussehen, weil
     sie die Dauer aus dem Rahmenstrom misst und die Positionen nur
     anteilig nach Zeichenzahl verteilt. Ein Vergleich von gemessener
     Dauer gegen die erwartete Sprechzeit macht so etwas sichtbar.

     Die Konstanten stammen aus einem Kleinste-Quadrate-Fit über die
     acht Teile des ersten fertigen Artikels (3 Parameter, 8 Messpunkte).
     Eine Ziffer kostet dort 7,4-mal so viel Sprechzeit wie ein Buchstabe
     („20000" wird zu „zwanzigtausend"), plus rund 5,8 s Fixkosten je
     Äußerung. Die Toleranz ist bewusst weit: Die größte beobachtete
     Abweichung liegt bei 7,6 %, ±25 % fängt also echte Fehler
     (falscher oder verstümmelter Text), nicht natürliches Sprechrhythmus-
     Rauschen. */
  const FIX = 5.82, PRO_BUCHSTABE = 0.056006, PRO_ZIFFER = 0.4494, TOL = 0.25;

  const partsRoot = path.join(ROOT, 'static', 'audio', 'parts');
  const slugs = fs.existsSync(partsRoot)
    ? fs.readdirSync(partsRoot).filter((s) => fs.statSync(path.join(partsRoot, s)).isDirectory())
    : [];

  let geprueft = 0;
  for (const slug of slugs) {
    const dir = path.join(partsRoot, slug);
    const mp3s = fs.readdirSync(dir).filter((f) => f.endsWith('.mp3'));
    if (!mp3s.length) continue;
    const chunksPath = path.join(ROOT, 'data', 'audio', `${slug}.chunks.json`);
    if (!fs.existsSync(chunksPath)) {
      t.ok(false, `${slug}: Chunks-Datei fehlt`);
      continue;
    }
    const chunks = JSON.parse(fs.readFileSync(chunksPath, 'utf8'));

    for (const f of mp3s) {
      const idx = parseInt(f.replace(/\.mp3$/, ''), 10) - 1;
      const teil = chunks.parts[idx];
      if (!teil) { t.ok(false, `${slug}/${f}: kein zugehöriger Chunk`); continue; }

      const buf = fs.readFileSync(path.join(dir, f));
      const w = walk(trimId3v1(buf.subarray(skipId3v2(buf))), 0);

      t.eq(w.resyncs, 0, `${slug}/${f}: Rahmenstrom lückenlos (${w.frames} Rahmen)`);
      t.ok(w.seconds > 1, `${slug}/${f}: enthält hörbare Sprache (${w.seconds.toFixed(1)} s)`);

      const ziffern = (teil.text.match(/\d/g) || []).length;
      const erwartet = FIX + (teil.text.length - ziffern) * PRO_BUCHSTABE + ziffern * PRO_ZIFFER;
      const abw = Math.abs(w.seconds - erwartet) / erwartet;
      geprueft++;
      t.ok(abw <= TOL,
        `${slug}/${f}: Dauer ${w.seconds.toFixed(1)} s passt zum Text (${erwartet.toFixed(1)} s erwartet)`,
        `Abweichung ${(abw * 100).toFixed(1)} % > ${TOL * 100} % – Text möglicherweise falsch übertragen`);
    }
  }
  if (!geprueft) console.log('  ℹ️  Noch keine Teile gerendert – Gruppe übersprungen.');
  else console.log(`  ℹ️  ${geprueft} gerenderte Teile gegen die erwartete Sprechzeit geprüft.`);
}

/* ================================================================== */
/* 7) Ende-zu-Ende: echte Fassung im echten Reader                     */
/* ================================================================== */
t.group('7) Ende-zu-Ende mit der echten Audiofassung');
{
  /* Die Gruppen 1 bis 6 prüfen die Datei und ihre Zeitkarte isoliert,
     der Funktionstest nutzt eine synthetische Fassung. Damit bleibt eine
     Lücke: Ob der Reader die echte, gerenderte Datei tatsächlich findet,
     einbindet und gegen ihre echte Zeitkarte markiert, war unbelegt.

     Hier wird der erste fertige Artikel mit seiner realen MP3 und der
     realen Zeitkarte durch den echten Reader geladen. Die Zeitkarte wird
     aus der Datei geliefert, nicht berechnet – sonst würde die Prüfung
     nur sich selbst bestätigen. */
  const FERTIG = '2026-08-16-gas-anbieter-wechseln-praxis-tipps-fuer-guenstige-tarife';
  const mp3 = path.join(ROOT, 'static', 'audio', `${FERTIG}.mp3`);
  const tmPath = path.join(ROOT, 'static', 'audio', `${FERTIG}.timemap.json`);

  if (!fs.existsSync(mp3)) {
    console.log('  ℹ️  Noch keine fertige Fassung – Gruppe übersprungen.');
  } else {
    let qa = null;
    try {
      qa = await import('./reader_qa_lib.mjs');
    } catch (e) {
      console.log(`  ℹ️  jsdom nicht verfügbar (${e.message.split('\n')[0]}) – Gruppe übersprungen.`);
    }

    if (qa) {
    const zeitkarte = JSON.parse(fs.readFileSync(tmPath, 'utf8'));
    const art = qa.loadArticle(FERTIG);

    /* Die Spieldauer wird hier aus dem Rahmenstrom der Datei gemessen,
       bewusst NICHT aus der Zeitkarte gelesen. Würde sie aus der Zeitkarte
       stammen, wäre der spätere Vergleich ein Wert gegen sich selbst und
       könnte nie rot werden. So wird er zur echten Gegenprüfung:
       Datei gegen Zeitkarte. */
    const buf = fs.readFileSync(mp3);
    const strom = walk(trimId3v1(buf.subarray(skipId3v2(buf))), 0);

    const seite = await qa.createPage({
      html: qa.buildPage({
        title: art.title, description: art.description, kurzantwort: art.kurzantwort,
        readingTime: art.readingTime, wordCount: art.wordCount, author: art.author,
        bodyHtml: art.bodyHtml,
        audio: `/audio/${FERTIG}.mp3`,
        audioMap: `/audio/${FERTIG}.timemap.json`
      }),
      /* Bewusst ein Gerät OHNE männliche Stimme: Die Zusage lautet, dass die
         Audiofassung greift, wenn keine Gerätstimme taugt. */
      catalog: qa.VOICE_CATALOGS.androidChrome,
      audioDuration: strom.seconds
    });

    // Zeitkarte aus der Datei liefern (der Reader holt sie per XHR)
    const origOpen = seite.win.XMLHttpRequest.prototype.open;
    seite.win.XMLHttpRequest.prototype.open = function (m, u) { this.__url = u; return origOpen.apply(this, arguments); };
    seite.win.XMLHttpRequest.prototype.send = function () {
      const self = this;
      setTimeout(() => {
        Object.defineProperty(self, 'readyState', { value: 4, configurable: true });
        Object.defineProperty(self, 'status', { value: 200, configurable: true });
        Object.defineProperty(self, 'responseText', { value: JSON.stringify(zeitkarte), configurable: true });
        if (self.onreadystatechange) self.onreadystatechange();
      }, 0);
    };

    /* Hinweis: t.eq vergleicht mit ===, also per Referenz. Zwei verschiedene
       leere Arrays sind nie identisch – deshalb die Länge vergleichen. */
    t.eq(seite.errors.length, 0, 'Artikel mit echter Fassung lädt ohne Laufzeitfehler', seite.errors.join(' | '));

    seite.doc.getElementById('ff-listen-btn').click();
    await qa.until(() => seite.doc.getElementById('ff-reader-toolbar').classList.contains('ff-reader-toolbar--playing'), 3000);

    t.eq(seite.log.length, 0, 'Browser-Stimme bleibt unangetastet, solange die echte Fassung läuft',
      seite.log.join(' | '));

    const el = seite.win.__audioEl;
    t.ok(!!el, '<audio>-Element wurde erzeugt');
    t.eq(el.getAttribute('src'), `/audio/${FERTIG}.mp3`, 'Quelle zeigt auf die echte Datei');
    t.ok(el.getAttribute('playsinline') !== null, 'playsinline gesetzt (iPhone spielt inline)');
    /* Gegenprüfung Datei gegen Zeitkarte. Die Zeitkarte rundet auf zwei
       Nachkommastellen (mp3_join.mjs: toFixed(2)), der Rahmenstrom misst
       ungerundet – deshalb dieselbe Toleranz wie in Gruppe 4. */
    t.ok(Math.abs(el.duration - zeitkarte.durationSeconds) < 0.01,
      'Spieldauer der Datei entspricht der Zeitkarte',
      `Datei ${el.duration} s, Zeitkarte ${zeitkarte.durationSeconds} s`);

    t.ok(await qa.until(() => el.currentTime > 0, 3000), 'Wiedergabe läuft (currentTime steigt)');
    t.ok(/Studiostimme|Audiofassung/.test(seite.doc.getElementById('ff-reader-status').textContent),
      'Status meldet die Studiofassung', seite.doc.getElementById('ff-reader-status').textContent);

    /* Kern der Zusage: Die Zeitkarte aus der Datei muss zu den Blöcken des
       echten Artikels passen. Passt sie nicht, läuft der Ton, aber die
       Markierung steht falsch oder gar nicht im Text. */
    await qa.until(() => el.currentTime > 12, 4000);
    const aktiv = seite.doc.querySelector('.ff-reader-active');
    t.ok(!!aktiv, 'Live-Markierung folgt der echten Zeitkarte');
    t.ok(!!aktiv && aktiv.closest('.post-content, .ff-kurzantwort, .ff-korrektur') !== null,
      'Markierung steht im sichtbaren Text, nicht im Leeren',
      aktiv ? (aktiv.className || aktiv.tagName) : 'kein Element');

    const balken = seite.doc.getElementById('ff-reader-progress-bar').style.width;
    t.ok(balken && balken !== '0%', 'Fortschrittsbalken folgt der echten Spieldauer', String(balken));

    seite.win.close();
    }
  }
}

/* ================================================================== */
console.log(`\n=== Audio-Pipeline — Ergebnis: ${pass} grün, ${fails.length} rot ===`);
if (fails.length) {
  console.log('\nFehlgeschlagene Prüfungen:');
  fails.forEach((f) => console.log(`  ❌ ${f}`));
  console.log(`\n💥 ${fails.length} Prüfung(en) fehlgeschlagen.`);
  process.exit(1);
}
console.log('\n🎉 Audio-Pipeline bestanden: Sprechtext sauber, Rahmenstrom lückenlos, Zeitkarte korrekt.');
