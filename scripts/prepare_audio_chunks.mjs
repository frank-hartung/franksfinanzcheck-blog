#!/usr/bin/env node
/**
 * prepare_audio_chunks.mjs — Sprechtext für die First-Party-Audiofassungen.
 *
 * Warum dieser Weg:
 *   Die MP3-Fassungen müssen exakt denselben Text sprechen wie der
 *   Browser-Reader. Ein Nachbau der Logik würde unweigerlich auseinander-
 *   laufen. Deshalb lädt dieses Skript die UNVERÄNDERTE
 *   static/premium/ff-reader.js in jsdom und ruft deren Export-Hook auf —
 *   dieselbe Block-Sammlung, dasselbe DE/EN-Routing, dieselbe Aussprache-
 *   Normalisierung, dieselbe Atemgruppen-Bildung.
 *
 * Erzeugt je Artikel data/audio/<slug>.chunks.json:
 *   { slug, title, lang, parts: [ { index, text, units:[{i,type,lang,chars}] } ] }
 *
 * Die Teile sind auf <= MAX_CHARS Zeichen gepackt (Render-Limit der
 * Sprachausgabe), Schnitte fallen ausschließlich auf Einheitengrenzen des
 * Readers — es wird also nie mitten in einem Satz geschnitten.
 *
 * Aufruf:  node scripts/prepare_audio_chunks.mjs [slug ...]
 *          ohne Argument: alle Artikel aus content/posts
 */

import fs from 'node:fs';
import path from 'node:path';
import { ROOT, createPage, buildPage, loadArticle, listArticleSlugs, VOICE_CATALOGS } from './reader_qa_lib.mjs';

/** Hartes Render-Limit der Sprachausgabe. Sicherheitsabstand eingeplant. */
const MAX_CHARS = 1400;

const OUT_DIR = path.join(ROOT, 'data', 'audio');

function packParts(timeline) {
  const parts = [];
  let buf = '';
  let units = [];

  const flush = () => {
    if (!buf.trim()) return;
    parts.push({ index: parts.length, text: buf.trim(), units });
    buf = '';
    units = [];
  };

  timeline.forEach((u, i) => {
    const text = u.text.trim();
    if (!text) return;
    /* Zuerst entscheiden, DANN zuweisen. Die frühere Fassung berechnete
       `candidate` aus dem alten Puffer, rief flush() auf und wies danach
       trotzdem `candidate` zu – der geleerte Puffer war sofort wieder voll
       und die Teile liefen auf über 10.000 Zeichen auf. */
    if (buf && (buf.length + 1 + text.length) > MAX_CHARS) {
      flush();
      buf = text;
    } else {
      buf = buf ? buf + ' ' + text : text;
    }
    units.push({ i, type: u.type, lang: u.lang, chars: text.length });
  });
  flush();

  // Harte Selbstprüfung: kein Teil darf das Render-Limit verletzen.
  const tooLong = parts.filter((p) => p.text.length > MAX_CHARS);
  if (tooLong.length) {
    throw new Error(`${tooLong.length} Teil(e) über ${MAX_CHARS} Zeichen, längstes ${tooLong[0].text.length}`);
  }
  return parts;
}

export async function buildChunksFor(slug) {
  const a = loadArticle(slug);
  const page = await createPage({
    html: buildPage({
      title: a.title, description: a.description, kurzantwort: a.kurzantwort,
      readingTime: a.readingTime, wordCount: a.wordCount, author: a.author,
      bodyHtml: a.bodyHtml
    }),
    catalog: VOICE_CATALOGS.macChrome
  });
  if (page.errors.length) {
    throw new Error(`${slug}: Fehler beim Laden der Reader-Engine: ${page.errors[0].slice(0, 200)}`);
  }
  const ex = page.win.__ffReaderExport;
  if (!ex || typeof ex.buildTimeline !== 'function') {
    throw new Error(`${slug}: Export-Hook der Reader-Engine fehlt`);
  }
  const tl = ex.buildTimeline();
  if (!tl.timeline.length) throw new Error(`${slug}: leere Sprech-Zeitachse`);

  const parts = packParts(tl.timeline);
  return {
    slug,
    title: a.title,
    lang: tl.lang,
    quality: tl.quality,
    units: tl.timeline.length,
    chars: tl.timeline.reduce((s, u) => s + u.text.length, 0),
    parts
  };
}

const args = process.argv.slice(2);
const slugs = args.length ? args : listArticleSlugs();

fs.mkdirSync(OUT_DIR, { recursive: true });

let totalParts = 0;
const summary = [];
for (const slug of slugs) {
  let data;
  try {
    data = await buildChunksFor(slug);
  } catch (e) {
    console.error(`❌ ${slug}: ${e.message}`);
    summary.push({ slug, error: e.message });
    continue;
  }
  const file = path.join(OUT_DIR, `${slug}.chunks.json`);
  fs.writeFileSync(file, JSON.stringify(data, null, 1), 'utf8');
  const longest = Math.max(...data.parts.map((p) => p.text.length));
  totalParts += data.parts.length;
  summary.push({ slug, parts: data.parts.length, chars: data.chars, longest });
  console.log(`✅ ${slug}: ${data.parts.length} Teile, ${data.chars} Zeichen, längstes Teil ${longest}`);
}

fs.writeFileSync(
  path.join(OUT_DIR, '_summary.json'),
  JSON.stringify({ generated: new Date().toISOString(), maxChars: MAX_CHARS, totalParts, articles: summary }, null, 1),
  'utf8'
);

const failed = summary.filter((s) => s.error);
console.log(`\n${summary.length - failed.length} Artikel vorbereitet, ${totalParts} Render-Teile gesamt.`);
if (failed.length) {
  console.error(`${failed.length} Fehler:`);
  failed.forEach((f) => console.error(`  - ${f.slug}: ${f.error}`));
  process.exit(1);
}
