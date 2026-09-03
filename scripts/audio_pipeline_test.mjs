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
console.log(`\n=== Audio-Pipeline — Ergebnis: ${pass} grün, ${fails.length} rot ===`);
if (fails.length) {
  console.log('\nFehlgeschlagene Prüfungen:');
  fails.forEach((f) => console.log(`  ❌ ${f}`));
  console.log(`\n💥 ${fails.length} Prüfung(en) fehlgeschlagen.`);
  process.exit(1);
}
console.log('\n🎉 Audio-Pipeline bestanden: Sprechtext sauber, Rahmenstrom lückenlos, Zeitkarte korrekt.');
