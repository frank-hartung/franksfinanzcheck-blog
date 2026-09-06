#!/usr/bin/env node
/**
 * audio_render_next.mjs — Welche Teile fehlen noch, und in welchem Wortlaut?
 * =========================================================================
 * Die Audiofassung entsteht in zwei getrennten Schritten:
 *
 *   1. Sprache rendern   → static/audio/parts/<slug>/NNN.mp3
 *      (extern, mit Limits pro Durchlauf – deshalb häppchenweise)
 *   2. Teile verbinden   → node scripts/mp3_join.mjs <slug> <teile…>
 *
 * Dieses Skript ist das Gedächtnis dazwischen. Es prüft für jeden
 * Artikel, welche Teile schon als MP3 vorliegen, und gibt die fehlenden
 * mit ihrem exakten Sprechtext aus – fertig zum Weiterrendern, ohne dass
 * man Teilnummern von Hand abzählen oder Texte neu zusammensuchen muss.
 *
 * Aufruf:
 *   node scripts/audio_render_next.mjs              # Überblick + nächster Artikel
 *   node scripts/audio_render_next.mjs <slug>       # nur dieser Artikel
 *   node scripts/audio_render_next.mjs --text       # Sprechtexte ausgeben
 *   node scripts/audio_render_next.mjs --join       # fertige Join-Befehle
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, '..');

const argv = process.argv.slice(2);
const wantText = argv.includes('--text');
const wantJoin = argv.includes('--join');
const onlySlug = argv.find((a) => !a.startsWith('--')) || null;

const chunksDir = path.join(ROOT, 'data', 'audio');
const partsRoot = path.join(ROOT, 'static', 'audio', 'parts');
const outRoot = path.join(ROOT, 'static', 'audio');

const summary = JSON.parse(fs.readFileSync(path.join(chunksDir, '_summary.json'), 'utf8'));
const slugs = (onlySlug ? [onlySlug] : summary.articles.map((a) => a.slug)).filter((s) =>
  fs.existsSync(path.join(chunksDir, `${s}.chunks.json`))
);

let totalParts = 0;
let renderedParts = 0;
let doneArticles = 0;
const report = [];

for (const slug of slugs) {
  const chunks = JSON.parse(fs.readFileSync(path.join(chunksDir, `${slug}.chunks.json`), 'utf8'));
  const partsDir = path.join(partsRoot, slug);
  const finalMp3 = path.join(outRoot, `${slug}.mp3`);
  const isJoined = fs.existsSync(finalMp3);

  const missing = [];
  chunks.parts.forEach((part, i) => {
    totalParts++;
    const f = path.join(partsDir, String(i + 1).padStart(3, '0') + '.mp3');
    if (fs.existsSync(f) && fs.statSync(f).size > 0) renderedParts++;
    else missing.push({ index: i + 1, text: part.text });
  });

  if (isJoined) doneArticles++;
  report.push({ slug, total: chunks.parts.length, missing, isJoined });
}

/* ---------------- Ausgabe ---------------- */

if (wantJoin) {
  /* Join-Befehle für Artikel, deren Teile vollständig sind, die aber
     noch nicht verbunden wurden. */
  const ready = report.filter((r) => r.missing.length === 0 && !r.isJoined);
  if (!ready.length) {
    console.log('Kein Artikel wartet auf das Verbinden.');
  }
  for (const r of ready) {
    console.log(`node scripts/mp3_join.mjs ${r.slug} static/audio/parts/${r.slug}/*.mp3 -o static/audio/${r.slug}.mp3`);
  }
  process.exit(0);
}

console.log('—— Audiofassung: Fortschritt ————————————————————————');
console.log(`Artikel verbunden : ${doneArticles} / ${slugs.length}`);
console.log(`Teile gerendert   : ${renderedParts} / ${totalParts}`);
const openParts = totalParts - renderedParts;
console.log(`Teile offen       : ${openParts}`);
if (openParts) console.log(`Bei 10 Clips/Runde: ~${Math.ceil(openParts / 10)} Runden`);
console.log('');

const inProgress = report.filter((r) => r.missing.length > 0 && r.missing.length < r.total);
const notStarted = report.filter((r) => r.missing.length === r.total);

if (inProgress.length) {
  console.log('Angefangen:');
  for (const r of inProgress) console.log(`  ${r.total - r.missing.length}/${r.total} Teile  ${r.slug}`);
  console.log('');
}

/* Nächster zu rendernder Artikel: erst angefangene fertig machen, dann
   der kürzeste offene – so wird früh ein vollständiger Artikel fertig. */
const queue = [...inProgress, ...notStarted.sort((a, b) => a.missing.length - b.missing.length)];
const next = queue[0];

if (!next) {
  console.log('✅ Alle Teile sind gerendert.');
  process.exit(0);
}

console.log(`Nächster Artikel: ${next.slug}  (${next.missing.length} Teile offen)`);
console.log('');

if (wantText) {
  for (const m of next.missing) {
    console.log(`### static/audio/parts/${next.slug}/${String(m.index).padStart(3, '0')}.mp3`);
    console.log(m.text);
    console.log('');
  }
} else {
  console.log('Sprechtexte anzeigen mit:  node scripts/audio_render_next.mjs --text');
  console.log('Join-Befehle anzeigen mit: node scripts/audio_render_next.mjs --join');
}
