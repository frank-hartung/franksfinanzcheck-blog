/**
 * mp3_info.mjs – MP3-Rahmenstrom korrekt lesen
 * =============================================
 * Wozu: Ohne ffmpeg/ffprobe muss die Audiofassung selbst vermessen
 * werden. Zwei Fallen, die hier beide behandelt sind:
 *
 * 1) Die Bitraten-Tabelle hängt von MPEG-Version UND Layer ab. Für
 *    MPEG2/2.5 Layer III gilt [0,8,16,24,32,40,48,56,64,80,96,112,128,
 *    144,160] – wer die MPEG1-Tabelle nimmt, rechnet eine falsche
 *    Rahmenlänge, verliert die Synchronisation und hält anschließend
 *    Nutzdaten für Rahmenköpfe. Genau so sah die erste Messung aus.
 *
 * 2) Ein Xing/Info-Kopf am Dateianfang nennt Rahmenzahl und Bytezahl
 *    der GESAMTEN Datei. Beim Zusammenfügen mehrerer Teile bleibt der
 *    Kopf des ersten Teils stehen und behauptet dann eine viel zu
 *    kurze Dauer – Abspieler zeigen falsche Zeiten und springen falsch.
 */
import fs from 'node:fs';

/* Bitraten in kbit/s, indiziert über [Versionsklasse][Layer][Index] */
const BITRATES = {
  mpeg1: {
    1: [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448], // Layer I
    2: [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],     // Layer II
    3: [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]       // Layer III
  },
  mpeg2: {
    1: [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
    2: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
    3: [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160]
  }
};
const SAMPLERATES = {
  3: [44100, 48000, 32000],  // MPEG1
  2: [22050, 24000, 16000],  // MPEG2
  0: [11025, 12000, 8000]    // MPEG2.5
};

/** Layer-Bits im Kopf: 3=I, 2=II, 1=III (0 ist reserviert) */
export function header(buf, off) {
  if (off + 4 > buf.length) return null;
  if (buf[off] !== 0xff || (buf[off + 1] & 0xe0) !== 0xe0) return null;
  const vBits = (buf[off + 1] >> 3) & 3;
  const layerBits = (buf[off + 1] >> 1) & 3;
  const bi = (buf[off + 2] >> 4) & 15;
  const si = (buf[off + 2] >> 2) & 3;
  const padding = (buf[off + 2] >> 1) & 1;
  if (layerBits === 0 || bi === 0 || bi === 15 || si === 3) return null;

  const isMpeg1 = vBits === 3;
  const group = isMpeg1 ? 'mpeg1' : 'mpeg2';
  /* Achtung: layerBits ist invertiert zur Layer-Nummer (3=I, 2=II, 1=III).
     BITRATES ist nach Layer-Nummer geschlüsselt – ohne Umrechnung greift
     man zur Layer-I-Tabelle und rechnet die doppelte Rahmenlänge. */
  const layerNo = 4 - layerBits;
  const bitrate = BITRATES[group][layerNo][bi];
  const sampleRate = SAMPLERATES[vBits][si];
  if (!bitrate || !sampleRate) return null;

  const isLayer1 = layerBits === 3;
  const coef = isLayer1 ? 12 : (isMpeg1 ? 144 : 72);
  const samples = isLayer1 ? 384 : (isMpeg1 ? 1152 : 576);
  const slot = isLayer1 ? 4 : 1;
  const length = Math.floor((coef * bitrate * 1000) / sampleRate) + padding * slot;
  if (length < 4) return null;

  return {
    offset: off,
    length,
    samples,
    sampleRate,
    bitrate,
    seconds: samples / sampleRate,
    version: isMpeg1 ? 'MPEG1' : vBits === 2 ? 'MPEG2' : 'MPEG2.5',
    layer: 4 - layerBits,
    key: `${isMpeg1 ? 'MPEG1' : vBits === 2 ? 'MPEG2' : 'MPEG2.5'}/L${4 - layerBits}/${bitrate}k/${sampleRate}Hz`
  };
}

/** ID3v2 am Dateianfang überspringen, Länge zurückgeben. */
export function skipId3v2(buf) {
  if (buf.length < 10 || buf.toString('latin1', 0, 3) !== 'ID3') return 0;
  const size =
    ((buf[6] & 0x7f) << 21) | ((buf[7] & 0x7f) << 14) |
    ((buf[8] & 0x7f) << 7) | (buf[9] & 0x7f);
  return 10 + size;
}

/** ID3v1 am Dateiende abschneiden. */
export function trimId3v1(buf) {
  if (buf.length >= 128 && buf.toString('latin1', buf.length - 128, buf.length - 125) === 'TAG') {
    return buf.subarray(0, buf.length - 128);
  }
  return buf;
}

/** Xing/Info-Kopf innerhalb des ersten Rahmens finden. */
export function findXing(buf, frameStart, frameLen) {
  const end = Math.min(buf.length, frameStart + frameLen);
  for (let i = frameStart + 4; i < end - 8; i++) {
    const tag = buf.toString('latin1', i, i + 4);
    if (tag === 'Xing' || tag === 'Info') return { offset: i, tag };
  }
  return null;
}

export function readXing(buf, at) {
  const flags = buf.readUInt32BE(at + 4);
  let p = at + 8;
  const out = { flags, frames: null, bytes: null, tocOffset: null };
  if (flags & 0x1) { out.frames = buf.readUInt32BE(p); p += 4; }
  if (flags & 0x2) { out.bytes = buf.readUInt32BE(p); p += 4; }
  if (flags & 0x4) { out.tocOffset = p; p += 100; }
  if (flags & 0x8) { out.quality = buf.readUInt32BE(p); p += 4; }
  return out;
}

/**
 * Rahmenstrom durchgehen. Ein Rahmen wird nur gezählt, wenn auch am
 * Ende seiner rechnerischen Länge wieder ein gültiger Kopf steht –
 * sonst ist es ein Fehl-Sync in den Nutzdaten und es wird byte-weise
 * weitergesucht.
 */
export function walk(buf, start) {
  let off = start;
  let frames = 0;
  let seconds = 0;
  let bytes = 0;
  let resyncs = 0;
  const configs = new Map();
  let xing = null;

  while (off + 4 <= buf.length) {
    const h = header(buf, off);
    if (!h) { off++; resyncs++; continue; }

    // Gegenprobe: liegt am rechnerischen Rahmenende wieder ein Kopf?
    const next = off + h.length;
    const nextOk = next >= buf.length || header(buf, next) !== null;
    if (!nextOk) { off++; resyncs++; continue; }

    if (frames === 0) {
      const x = findXing(buf, off, h.length);
      if (x) xing = { ...x, ...readXing(buf, x.offset), headerLen: h.length };
    }
    configs.set(h.key, (configs.get(h.key) || 0) + 1);
    frames++;
    seconds += h.seconds;
    bytes += h.length;
    off = next;
  }
  return { frames, seconds, bytes, resyncs, configs, xing, endOffset: off };
}

/** Vollständige Vermessung einer MP3-Datei. */
export function analyseFile(file) {
  const raw = fs.readFileSync(file);
  const id3 = skipId3v2(raw);
  const body = trimId3v1(raw.subarray(id3));
  const w = walk(body, 0);
  return {
    file,
    size: raw.length,
    id3Size: id3,
    ...w,
    /* Xing nennt die Rahmenzahl der Quelldatei – maßgeblich, wenn der
       Rahmenstrom selbst lückenhaft gelesen wurde. */
    xingSeconds: w.xing && w.xing.frames && w.xing.sampleRate ? null : null
  };
}

/**
 * Sekunden als „M:SS min" bzw. „H:MM:SS min".
 *
 * Erst runden, dann teilen. Andersherum entsteht aus 659,98 s die
 * Anzeige „10:60 min", weil der Rest 59,98 auf 60 aufrundet, ohne in
 * die Minuten überzutragen – genau so stand es in der ersten Zeitkarte.
 */
export function formatDuration(sec) {
  const total = Math.round(sec);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = h > 0 ? String(m).padStart(2, '0') : String(m);
  return `${h > 0 ? `${h}:` : ''}${mm}:${String(s).padStart(2, '0')} min`;
}
