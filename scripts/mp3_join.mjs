#!/usr/bin/env node
/**
 * mp3_join.mjs — MP3-Teile zu einer Artikelfassung zusammenfügen + Zeitkarte.
 *
 * In dieser Umgebung ist kein ffmpeg/ffprobe verfügbar. MP3 ist aber ein
 * Rahmenstrom-Format: jeder Frame trägt Bitrate und Abtastrate im Kopf und
 * ist unabhängig abspielbar. Zusammenfügen heißt deshalb: ID3-Tags der
 * Folgeteile entfernen, Rahmenströme konkatenieren. Das Skript läuft die
 * Frames ab und misst dabei die EXAKTE Dauer je Teil — daraus entsteht die
 * Zeitkarte für die Abschnittssprünge im Player.
 *
 * Aufruf:
 *   node scripts/mp3_join.mjs <slug> <teil.mp3> <teil.mp3> ... -o <ziel.mp3>
 *
 * Erzeugt:
 *   static/audio/<slug>.mp3        (konkatenierter Rahmenstrom)
 *   data/audio/<slug>.timemap.json (Dauern, Zeitkarte je Abschnitt)
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');

/* ------------------------------------------------------------------ */
/* MP3-Rahmenanalyse                                                   */
/* ------------------------------------------------------------------ */

const BITRATES = {
  // Index 0 und 15 sind ungültig bzw. „free"; hier nur die nutzbaren.
  v1: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
  v2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]
};
const SAMPLERATES = {
  v1: [44100, 48000, 32000],
  v2: [22050, 24000, 16000],
  v25: [11025, 12000, 8000]
};

/** Überspringt einen ID3v2-Tag am Dateianfang, gibt den Datenoffset zurück. */
function skipId3v2(buf, offset = 0) {
  if (buf.length - offset < 10) return offset;
  if (buf.toString('latin1', offset, offset + 3) !== 'ID3') return offset;
  // Größe: 4 Byte synchsafe (jeweils 7 Bit)
  const size = ((buf[offset + 6] & 0x7f) << 21) | ((buf[offset + 7] & 0x7f) << 14)
    | ((buf[offset + 8] & 0x7f) << 7) | (buf[offset + 9] & 0x7f);
  return offset + 10 + size;
}

/** Entfernt einen ID3v1-Tag (128 Byte, „TAG") am Dateiende. */
function trimId3v1(buf, end) {
  if (end - 128 >= 0 && buf.toString('latin1', end - 128, end - 125) === 'TAG') return end - 128;
  return end;
}

/**
 * Läuft die MPEG-Audio-Frames ab.
 * Liefert { start, end, duration, frames, sampleRate, bitrateKbps }
 */
function analyse(buf, from, to) {
  let pos = from;
  let frames = 0;
  let duration = 0;
  let sampleRate = 0;
  let bitrateKbps = 0;

  while (pos + 4 <= to) {
    const b0 = buf[pos]; const b1 = buf[pos + 1]; const b2 = buf[pos + 2];
    // Sync: 11 gesetzte Bits
    if (b0 !== 0xff || (b1 & 0xe0) !== 0xe0) { pos++; continue; }

    const versionBits = (b1 >> 3) & 0x03;   // 00=2.5, 01=reserviert, 10=2, 11=1
    const layerBits = (b1 >> 1) & 0x03;     // 01=Layer III, 10=II, 11=I
    if (versionBits === 1 || layerBits === 0) { pos++; continue; }

    const bitrateIdx = (b2 >> 4) & 0x0f;
    const rateIdx = (b2 >> 2) & 0x03;
    const padding = (b2 >> 1) & 0x01;
    if (bitrateIdx === 0 || bitrateIdx === 15 || rateIdx === 3) { pos++; continue; }

    const isV1 = versionBits === 3;
    const br = (isV1 ? BITRATES.v1 : BITRATES.v2)[bitrateIdx];
    const srTable = isV1 ? SAMPLERATES.v1 : (versionBits === 2 ? SAMPLERATES.v2 : SAMPLERATES.v25);
    const sr = srTable[rateIdx];
    if (!br || !sr) { pos++; continue; }

    // Layer III: 1152 Samples (MPEG1) bzw. 576 (MPEG2/2.5)
    const samplesPerFrame = isV1 ? 1152 : 576;
    const coefficient = isV1 ? 144 : 72;
    const frameLen = Math.floor((coefficient * br * 1000) / sr) + padding;
    if (frameLen <= 0 || pos + frameLen > to) break;

    frames++;
    duration += samplesPerFrame / sr;
    sampleRate = sr;
    bitrateKbps = br;
    pos += frameLen;
  }

  return { start: from, end: pos, duration, frames, sampleRate, bitrateKbps };
}

/* ------------------------------------------------------------------ */
/* Hauptprogramm                                                       */
/* ------------------------------------------------------------------ */

const argv = process.argv.slice(2);
if (argv.length < 3) {
  console.error('Aufruf: node scripts/mp3_join.mjs <slug> <teil.mp3> [...] -o <ziel.mp3> [--chunks <chunks.json>]');
  process.exit(2);
}

const slug = argv[0];
let outArg = null;
let chunksArg = null;
const inputs = [];
for (let i = 1; i < argv.length; i++) {
  if (argv[i] === '-o' || argv[i] === '--out') { outArg = argv[++i]; continue; }
  if (argv[i] === '--chunks') { chunksArg = argv[++i]; continue; }
  inputs.push(argv[i]);
}
if (!inputs.length) { console.error('Keine MP3-Teile übergeben.'); process.exit(2); }

const outPath = outArg || path.join(ROOT, 'static', 'audio', `${slug}.mp3`);
const chunksPath = chunksArg || path.join(ROOT, 'data', 'audio', `${slug}.chunks.json`);

if (!fs.existsSync(chunksPath)) {
  console.error(`Chunk-Datei fehlt: ${chunksPath}\nZuerst: node scripts/prepare_audio_chunks.mjs ${slug}`);
  process.exit(2);
}
const chunks = JSON.parse(fs.readFileSync(chunksPath, 'utf8'));
if (chunks.parts.length !== inputs.length) {
  console.error(`Teilzahl passt nicht: Chunk-Datei erwartet ${chunks.parts.length}, übergeben wurden ${inputs.length}.`);
  process.exit(2);
}

const pieces = [];
const partDurations = [];
let totalBytes = 0;

for (const file of inputs) {
  const buf = fs.readFileSync(file);
  const start = skipId3v2(buf, 0);
  const end = trimId3v1(buf, buf.length);
  const info = analyse(buf, start, end);
  if (!info.frames) {
    console.error(`❌ ${file}: keine gültigen MPEG-Audio-Frames gefunden`);
    process.exit(1);
  }
  pieces.push(buf.subarray(info.start, info.end));
  partDurations.push(info.duration);
  totalBytes += info.end - info.start;
}

fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, Buffer.concat(pieces));

/* ---------- Zeitkarte: Abschnitt -> Startsekunde ----------
   Innerhalb eines Teils ist die genaue Position einer Einheit nicht
   messbar (die Sprachausgabe liefert hier keine Wortzeitstempel).
   Sie wird deshalb anteilig nach Zeichenlänge verteilt – auf
   Abschnittsebene (H2) ist das für Sprungmarken ausreichend genau. */
let cursor = 0;
const unitStart = new Array(chunks.units).fill(null);
chunks.parts.forEach((part, pi) => {
  const dur = partDurations[pi];
  const totalChars = part.units.reduce((s, u) => s + u.chars, 0) || 1;
  let acc = 0;
  part.units.forEach((u) => {
    unitStart[u.i] = cursor + (acc / totalChars) * dur;
    acc += u.chars;
  });
  cursor += dur;
});

// Zeitstempel je Sprecheinheit (ein Eintrag je fortlaufendem Einheiten-Index)
const sectionTimes = [];
{
  let lastUnit = null;
  chunks.parts.forEach((part) => {
    part.units.forEach((u) => {
      if (u.i !== lastUnit && unitStart[u.i] != null) {
        sectionTimes.push({ unit: u.i, type: u.type, at: Number(unitStart[u.i].toFixed(2)) });
        lastUnit = u.i;
      }
    });
  });
}

const timemap = {
  slug,
  title: chunks.title,
  lang: chunks.lang,
  file: `/audio/${slug}.mp3`,
  durationSeconds: Number(cursor.toFixed(2)),
  durationLabel: fmt(cursor),
  parts: chunks.parts.map((p, i) => ({
    index: p.index,
    seconds: Number(partDurations[i].toFixed(2)),
    startAt: Number(chunks.parts.slice(0, i).reduce((s, _, k) => s + partDurations[k], 0).toFixed(2)),
    chars: p.text.length,
    units: p.units.length
  })),
  unitStart: unitStart.map((v) => (v == null ? null : Number(v.toFixed(2)))),
  sectionTimes
};

/* Die Zeitkarte liegt in static/audio/, damit Hugo sie zusammen mit der
   MP3 veroeffentlicht und das Template sie per asset_url referenzieren kann. */
fs.mkdirSync(path.join(ROOT, 'static', 'audio'), { recursive: true });
fs.writeFileSync(path.join(ROOT, 'static', 'audio', `${slug}.timemap.json`), JSON.stringify(timemap), 'utf8');

const sizeMb = (fs.statSync(outPath).size / (1024 * 1024)).toFixed(2);
console.log(`✅ ${slug}: ${inputs.length} Teile → ${outPath}`);
console.log(`   Dauer ${timemap.durationLabel} · ${sizeMb} MB · ${sectionTimes.length} Zeitstempel`);

function fmt(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  return `${m}:${String(s).padStart(2, '0')} min`;
}
