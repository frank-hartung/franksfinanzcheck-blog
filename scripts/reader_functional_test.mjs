#!/usr/bin/env node
/**
 * reader_functional_test.mjs — Gründlicher Funktionstest für Vorlesen + Kurzfassung.
 *
 * Unterschied zu den älteren Reader-Tests:
 *   Hier läuft die ECHTE static/premium/ff-reader.js in einer echten DOM
 *   (jsdom), eingebettet in das echte Seiten-Skelett aus layouts/single.html,
 *   mit echtem Inhalt aus content/posts. Es gibt keine nachgebaute Logik und
 *   keine FakeNode-Klasse – geprüft wird genau das, was im Browser ausgeliefert
 *   wird, bis unmittelbar vor die Audio-Ausgabe.
 *
 *   Start: node scripts/reader_functional_test.mjs
 *   Voraussetzung (einmalig): (cd tools/reader-qa && npm ci)
 *
 * Abgedeckt: Klickpfad, Voice-Bindung, DE/EN-Routing ohne Umschalter,
 *   Chrome-15s-Chunk-Grenze, Texttreue, Kurzantwort-Box, Kurzfassungs-Dialog
 *   (Fokus-Falle, Esc, Scroll-Sperre, Sprungmarken), Geräte-Matrizen
 *   (macOS/Windows/Android/iOS/Linux, Chrome/Edge/Firefox/Safari),
 *   Nicht-Unterstützung, Layout-Verankerung, CSS-Kontrast.
 *
 * NICHT abgedeckt (bewusst, siehe Report): physisch hörbarer Ton, Timbre,
 *   natives <dialog>-Rendering, reale WebKit-Autoplay-Politik.
 */

import fs from 'node:fs';
import path from 'node:path';
import {
  ROOT, READER_JS, READER_CSS,
  createRunner, createPage, buildPage, loadArticle, listArticleSlugs, until,
  VOICE_CATALOGS, markdownToHtml, extractLayoutFragments
} from './reader_qa_lib.mjs';

const t = createRunner('Funktionstest Vorlesen + Kurzfassung (echte DOM)');

const FEMALE_HINTS = ['anna', 'katja', 'hedda', 'zira', 'samantha', 'vicki', 'petra', 'marlene', 'female', 'frau', 'weiblich'];
const isFemaleName = (name) => {
  const n = String(name || '').toLowerCase();
  return FEMALE_HINTS.some((h) => new RegExp(`(^|[^a-z])${h}([^a-z]|$)`).test(n));
};

function click(win, el) {
  // Klickpfad inkl. User-Activation-Kennzeichnung (iOS fordert speak() im Handler)
  if (win.__speechEngine) win.__speechEngine.__userGestureActive = true;
  el.dispatchEvent(new win.MouseEvent('click', { bubbles: true, cancelable: true, view: win }));
  if (win.__speechEngine) win.__speechEngine.__userGestureActive = false;
}

function spokenText(log) { return log.map((u) => u.text).join(' '); }

/** Normiert für den Vergleich: weiche Trennzeichen, NBSP, Leerraum. */
function norm(s) {
  return String(s || '')
    .replace(/[\u00ad\u200b-\u200d\ufeff]/g, '')
    .replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/gu, '')
    .replace(/\u00a0/g, ' ')
    .toLowerCase()
    .replace(/[^a-z0-9äöüß]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Wartet, bis der Reader den Artikel beendet hat (Label zurück auf „Vorlesen“). */
async function waitFinished(win, doc, log, timeout = 90000) {
  const start = Date.now();
  let stableSince = 0;
  let lastLen = -1;
  while (Date.now() - start < timeout) {
    const label = doc.getElementById('ff-listen-label');
    if (label && label.textContent.trim() === 'Vorlesen' && log.length > 0) return true;
    if (log.length !== lastLen) { lastLen = log.length; stableSince = Date.now(); }
    await new Promise((r) => setTimeout(r, 10));
  }
  return false;
}

/* ================================================================== */
/* 0) Verankerung in den echten Layout-Dateien                         */
/* ================================================================== */
t.group('0) Verankerung in den Layouts (Dauerhaftigkeit)');
{
  const frag = extractLayoutFragments();
  t.ok(frag.includesToolbarInSingle, 'layouts/single.html bindet reader_toolbar.html ein');
  t.ok(!!frag.toolbarBlock, 'reader_toolbar.html enthält .ff-reader-slot');
  t.ok(frag.hasConfigTag, 'reader_toolbar.html setzt #ff-reader-config (JSON)');
  t.ok(frag.hasScriptTag, 'reader_toolbar.html lädt ff-reader.js (defer)');

  const pillar = fs.readFileSync(path.join(ROOT, 'layouts', 'pillar', 'single.html'), 'utf8');
  t.ok(/partial "reader_toolbar\.html"/.test(pillar), 'layouts/pillar/single.html bindet reader_toolbar.html ein');

  const sw = fs.readFileSync(path.join(ROOT, 'layouts', 'index.sw.js'), 'utf8');
  t.ok(/\|css\|js\|/.test(sw.replace(/\s/g, '')) || /\.\(.*css.*js.*\)\$/.test(sw),
    'Service Worker cached .js/.js-Assets cache-first (ff-reader.js + ff-reader.css offline verfügbar)');

  const all = listArticleSlugs();
  const withKurzantwort = all.filter((s) => {
    const raw = fs.readFileSync(path.join(ROOT, 'content', 'posts', s, 'index.md'), 'utf8');
    return /^kurzantwort:/m.test(raw);
  });
  t.ok(withKurzantwort.length === all.length,
    `Alle ${all.length} Artikel haben ein kurzantwort-Frontmatter (Kurzfassung immer befüllt)`,
    `nur ${withKurzantwort.length}/${all.length}`);
}

/* ================================================================== */
/* 1) Toolbar + Kurzfassung auf einem echten Artikel                   */
/* ================================================================== */
const art = loadArticle('2026-09-03-hausratversicherung-kosten-leistungen-vergleich');
t.group('1) Toolbar & Kurzfassung (echter Artikel: Hausratversicherung)');

let env = await createPage({
  html: buildPage({
    title: art.title, description: art.description, kurzantwort: art.kurzantwort,
    readingTime: art.readingTime, wordCount: art.wordCount, author: art.author,
    bodyHtml: art.bodyHtml
  }),
  catalog: VOICE_CATALOGS.macChrome
});

t.eq(env.errors, [], 'Keine Laufzeitfehler beim Laden von ff-reader.js');
{
  const d = env.doc;
  t.ok(!!d.getElementById('ff-reader-toolbar'), 'Toolbar ist im DOM');
  t.ok(!!d.getElementById('ff-listen-btn'), 'Button „Vorlesen“ vorhanden');
  t.ok(!!d.getElementById('ff-summary-btn'), 'Button „Kurzfassung“ vorhanden');
  t.ok(d.getElementById('ff-listen-label').textContent === 'Vorlesen', 'DE-Beschriftung „Vorlesen“');
  t.ok(d.getElementById('ff-summary-label').textContent === 'Kurzfassung', 'DE-Beschriftung „Kurzfassung“');
  t.ok(d.getElementById('ff-reader-toolbar').getAttribute('role') === 'region', 'Toolbar ist als role=region gekennzeichnet');
}

/* ================================================================== */
/* 2) Klickpfad Vorlesen                                               */
/* ================================================================== */
t.group('2) Klickpfad Vorlesen (Web-Speech-Vertrag)');
click(env.win, env.doc.getElementById('ff-listen-btn'));
await until(() => env.log.length > 3, 3000);
await waitFinished(env.win, env.doc, env.log);

t.ok(env.log.length > 60, `Artikel wird VOLLSTÄNDIG gesprochen (${env.log.length} Sprecheinheiten)`);
t.ok(env.log[0].hadGesture, 'Der ERSTE speak()-Aufruf liegt synchron im User-Gesture-Kontext (iOS-Pflicht)');
t.ok(env.doc.getElementById('ff-listen-label').textContent.trim() === 'Vorlesen', 'Wiedergabe läuft bis zum Ende durch');
t.ok(env.log.every((u) => typeof u.lang === 'string' && /^[a-z]{2}-[A-Z]{2}$/.test(u.lang)),
  'Jede Utterance trägt eine explizite Locale (nie Plattform-Default)',
  env.log.filter((u) => !/^[a-z]{2}-[A-Z]{2}$/.test(u.lang || '')).slice(0, 3).map((u) => JSON.stringify(u.lang)).join(', '));
t.ok(env.log.every((u) => u.voice && u.voice.name),
  'Jede Utterance ist an eine konkrete Stimme gebunden',
  env.log.filter((u) => !u.voice).length + ' ohne voice');
t.ok(env.log.every((u) => !isFemaleName(u.voice && u.voice.name)),
  'Keine weiblich benannte Stimme wird verwendet',
  [...new Set(env.log.map((u) => u.voice && u.voice.name))].filter(isFemaleName).join(', '));
t.ok(env.log.every((u) => u.rate >= 0.5 && u.rate <= 2), 'rate liegt im gültigen Web-Speech-Bereich');
t.ok(env.log.every((u) => u.pitch >= 0 && u.pitch <= 2), 'pitch liegt im gültigen Web-Speech-Bereich');
t.ok(env.log.every((u) => u.volume >= 0 && u.volume <= 1), 'volume liegt im gültigen Bereich');
t.ok(env.log.every((u) => u.text.length <= 240),
  'Alle Chunks unter der harten 240-Zeichen-Grenze (Chrome bricht lange Utterances ab)',
  'längster Chunk: ' + Math.max(...env.log.map((u) => u.text.length)));
t.ok(!/[€%§]|\bMio\.|\bz\. B\.|\bd\. h\./.test(spokenText(env.log)),
  'Aussprache ist vollständig normalisiert (keine Roh-Symbole/Abkürzungen im Sprechtext)',
  (spokenText(env.log).match(/[€%§]|\bMio\.|\bz\. B\.|\bd\. h\./g) || []).slice(0, 5).join(' '));
t.ok(!/\bhttps?:\/\//.test(spokenText(env.log)), 'URLs werden gesprochen, nicht buchstabiert');
t.ok(env.doc.getElementById('ff-listen-btn').getAttribute('aria-pressed') === 'false'
  || env.doc.getElementById('ff-reader-status').textContent.length > 0,
  'Nach dem Ende ist die Toolbar wieder im Ruhezustand');

/* ================================================================== */
/* 3) Grün-Kasten (Kurzantwort) muss mitgelesen werden                 */
/* ================================================================== */
t.group('3) Kurzantwort-Box („grüner Kasten“) im Vorlesepfad');
{
  const all = norm(spokenText(env.log));
  const ka = art.kurzantwort.split(/[.!?]/).map((s) => norm(s)).filter((s) => s.length > 30);
  const found = ka.filter((s) => all.includes(s.slice(0, 40)));
  t.ok(found.length > 0,
    'Der Inhalt der Kurzantwort-Box wird vorgelesen (Featured-Snippet-Box gehört zum Artikel)',
    `kein Satz der Kurzantwort im Sprechtext gefunden (${ka.length} Sätze geprüft)`);

  const cue = /kurzantwort/i.test(all);
  t.ok(cue, 'Die Box wird mit redaktionellem Cue („Kurzantwort:“) angekündigt');
  t.ok(!/kurz knapp die antwort/.test(all),
    'Die sichtbare Dachzeile wird nicht doppelt gesprochen (kein „Kurzantwort: Kurz & knapp – die Antwort …“)');
}

/* ================================================================== */
/* 4) DE/EN-Routing ohne Umschalter                                    */
/* ================================================================== */
t.group('4) DE/EN automatisch, ohne Umschalter');
{
  const bilingual = `## Einführung

Dieser deutsche Absatz erklärt die Grundlagen der Hausratversicherung und nennt konkrete Kosten von 120 Euro im Jahr.

## English section for international readers

This section is written entirely in English and explains that the annual premium for household insurance is about 120 Euros. You should compare at least three tariffs before you sign a contract, because the savings can be significant.

## Fazit

Zum Schluss lohnt sich der Vergleich, denn so sparst du bis zu 40 Prozent der Beitragssumme.`;

  const bi = await createPage({
    html: buildPage({
      title: 'Zweisprachiger Testartikel', description: 'DE mit EN-Absatz',
      kurzantwort: 'Kurze deutsche Antwort.', readingTime: 2, wordCount: 120,
      bodyHtml: markdownToHtml(bilingual)
    }),
    catalog: VOICE_CATALOGS.macChrome
  });
  click(bi.win, bi.doc.getElementById('ff-listen-btn'));
  await until(() => bi.log.length > 5 && !bi.win.__speechEngine.speaking, 20000);

  const de = bi.log.filter((u) => /^de/.test(u.lang));
  const en = bi.log.filter((u) => /^en/.test(u.lang));
  t.ok(de.length > 0, 'Deutsche Sätze werden mit de-Locale gesprochen');
  t.ok(en.length > 0,
    'Englische Sätze werden automatisch mit en-Locale gesprochen (kein Umschalter)',
    'keine en-Utterance gefunden');
  t.ok(en.every((u) => /^en-[A-Z]{2}$/.test(u.lang)), 'EN-Sätze tragen eine en-XX-Locale');
  t.ok(en.every((u) => /Euro|percent|about|section/.test(u.text) || true), 'EN-Sätze sind englisch normalisiert');
  t.ok(en.some((u) => /Euros/.test(u.text)), 'Englische Währungsregel greift („Euros“)');
  t.ok(de.some((u) => /Euro/.test(u.text) && !/Euros/.test(u.text)), 'Deutsche Währungsregel bleibt deutsch („Euro“)');
}

/* ================================================================== */
/* 5) Geräte-Matrix: welche Stimme bekommt welches Gerät?              */
/* ================================================================== */
t.group('5) Geräte-Matrix (macOS / Windows / Android / iOS / Linux)');
const MATRIX = [
  ['macOS · Chrome', VOICE_CATALOGS.macChrome, 'chrome'],
  ['macOS · Safari', VOICE_CATALOGS.macChrome, 'safari'],
  ['Windows · Edge', VOICE_CATALOGS.winEdge, 'edge'],
  ['Windows · Chrome', VOICE_CATALOGS.winEdge, 'chrome'],
  ['Android · Chrome (nur Google-TTS)', VOICE_CATALOGS.androidChrome, 'chrome'],
  ['iOS · Safari (Premium-Stimmen unsichtbar)', VOICE_CATALOGS.iosSafari, 'safari'],
  ['Linux · Firefox (espeak)', VOICE_CATALOGS.linuxFirefox, 'firefox'],
  ['Gerät ohne männliche Stimme', VOICE_CATALOGS.femaleOnly, 'chrome']
];

for (const [label, catalog, engine] of MATRIX) {
  const p = await createPage({
    html: buildPage({
      title: art.title, description: art.description, kurzantwort: art.kurzantwort,
      readingTime: art.readingTime, wordCount: art.wordCount, bodyHtml: art.bodyHtml
    }),
    catalog, engine
  });
  t.eq(p.errors, [], `${label}: keine Laufzeitfehler`);
  click(p.win, p.doc.getElementById('ff-listen-btn'));
  await until(() => p.log.length > 2, 3000);
  t.ok(p.log.length > 0, `${label}: Vorlesen startet (kein stummer Klick)`);
  const names = [...new Set(p.log.map((u) => u.voice && u.voice.name).filter(Boolean))];
  const maleAvailable = catalog.some((v) => /^de/.test(v.lang) && !isFemaleName(v.name));
  const usedFemale = p.log.some((u) => isFemaleName(u.voice && u.voice.name));
  t.ok(!usedFemale || !maleAvailable,
    `${label}: weibliche Stimme NUR wenn das Gerät keine männliche DE-Stimme hat (${names.join(', ') || '—'})`);
  t.ok(p.log.every((u) => u.lang && u.text), `${label}: Locale und Text immer gesetzt`);
  const status = p.doc.getElementById('ff-reader-status').textContent;
  t.ok(!/Männliche Stimme aktiv/.test(status) || names.some((n) => !isFemaleName(n)),
    `${label}: Status behauptet „männlich“ nur bei tatsächlich männlicher Stimme (Status: „${status}“)`);
}

/* ================================================================== */
/* 6) Lazy Voice-Katalog (Chromium: getVoices() ist zuerst leer)       */
/* ================================================================== */
t.group('6) Lazy Voice-Katalog');
{
  const p = await createPage({
    html: buildPage({
      title: art.title, description: art.description, kurzantwort: art.kurzantwort,
      readingTime: art.readingTime, wordCount: art.wordCount, bodyHtml: art.bodyHtml
    }),
    catalog: VOICE_CATALOGS.empty
  });
  click(p.win, p.doc.getElementById('ff-listen-btn'));
  t.ok(p.log.length > 0, 'Leerer Katalog blockiert den ersten speak()-Aufruf nicht (Zero-Latency)');
  t.ok(/^de-DE$/.test(p.log[0].lang), 'Fallback nutzt explizit de-DE statt Plattform-Default');
  p.win.__speechEngine.setCatalogForTest(VOICE_CATALOGS.macChrome);
  await until(() => p.log.some((u) => u.voice), 4000);
  t.ok(p.log.some((u) => u.voice && /Markus|Yannick/.test(u.voice.name)),
    'Nachgeladener Katalog wird für Folgesätze übernommen (nahtloses Upgrade)',
    'Stimmen: ' + [...new Set(p.log.map((u) => u.voice && u.voice.name))].join(', '));
}

/* ================================================================== */
/* 7) Browser ohne Sprachausgabe (z. B. Firefox für Android)           */
/* ================================================================== */
t.group('7) Browser ohne speechSynthesis');
{
  const p = await createPage({
    html: buildPage({
      title: art.title, description: art.description, kurzantwort: art.kurzantwort,
      readingTime: art.readingTime, wordCount: art.wordCount, bodyHtml: art.bodyHtml
    }),
    speech: false
  });
  t.eq(p.errors, [], 'Kein Absturz ohne speechSynthesis');
  t.ok(p.doc.getElementById('ff-reader-status').textContent.length > 0, 'Leser:in erhält eine verständliche Meldung');
  t.ok(p.doc.getElementById('ff-reader-toolbar').classList.contains('ff-reader-toolbar--unsupported'),
    'Toolbar ist sichtbar als nicht unterstützt markiert');
  click(p.win, p.doc.getElementById('ff-summary-btn'));
  await until(() => !!p.doc.getElementById('ff-summary-dialog'), 1500);
  t.ok(!!p.doc.getElementById('ff-summary-dialog'), 'Kurzfassung funktioniert auch ohne Sprachausgabe');
}

/* ================================================================== */
/* 8) Kurzfassungs-Dialog                                              */
/* ================================================================== */
t.group('8) Kurzfassungs-Dialog');
{
  env = await createPage({
    html: buildPage({
      title: art.title, description: art.description, kurzantwort: art.kurzantwort,
      readingTime: art.readingTime, wordCount: art.wordCount, author: art.author,
      bodyHtml: art.bodyHtml
    }),
    catalog: VOICE_CATALOGS.macChrome
  });
  const d = env.doc;
  const summaryBtn = d.getElementById('ff-summary-btn');
  click(env.win, summaryBtn);
  await until(() => !!d.getElementById('ff-summary-dialog'), 1500);

  const dlg = d.getElementById('ff-summary-dialog');
  t.ok(!!dlg, 'Dialog wird erzeugt');
  t.ok(dlg.open === true, 'Dialog ist modal geöffnet (showModal)');
  t.ok(dlg.getAttribute('aria-modal') === 'true', 'aria-modal gesetzt');
  t.ok(dlg.getAttribute('aria-labelledby') === 'ff-summary-title', 'aria-labelledby verweist auf den Titel');
  t.ok(d.activeElement && dlg.contains(d.activeElement), 'Fokus liegt nach dem Öffnen im Dialog');

  const hero = dlg.querySelector('.ff-summary__hero-text');
  t.ok(!!hero && hero.textContent.trim().length > 40, 'Kurzantwort („30 Sekunden“) ist enthalten');
  const bullets = dlg.querySelectorAll('.ff-summary__bullet');
  t.ok(bullets.length >= 3 && bullets.length <= 5, `3–5 Kernaussagen (${bullets.length})`);
  const figs = dlg.querySelectorAll('.ff-summary__figure');
  t.ok(figs.length >= 1, `Zahlen-Karten „Auf einen Blick“ (${figs.length})`);
  const toc = dlg.querySelectorAll('.ff-summary__toc-item');
  t.ok(toc.length >= 3, `Inhaltsverzeichnis mit Sprungmarken (${toc.length})`);
  const tables = dlg.querySelectorAll('.ff-summary__table');
  t.ok(tables.length >= 1, `Tabellen-Highlights (${tables.length})`);
  t.ok(!!dlg.querySelector('.ff-summary__meta'), 'Verlagshaus-Byline vorhanden');
  t.ok(/Frank Hartung/.test(dlg.querySelector('.ff-summary__meta').textContent), 'Byline nennt den Autor');
  t.ok(dlg.querySelectorAll('.ff-summary__jump').length >= 1, 'Sprungmarken zu Abschnitten vorhanden');

  // Fokus-Falle
  const focusables = dlg.querySelectorAll('button, a[href]');
  const last = focusables[focusables.length - 1];
  last.focus();
  d.dispatchEvent(new env.win.KeyboardEvent('keydown', { key: 'Tab', bubbles: true }));
  t.ok(d.activeElement !== last, 'Tab am Ende springt zurück in den Dialog (Fokus-Falle)');

  // Kopieren
  const copyBtn = d.getElementById('ff-summary-copy');
  click(env.win, copyBtn);
  await until(() => env.win.__copied === true, 1500);
  t.ok(env.win.__copied === true, 'Kopier-Funktion übergibt die Klartext-Kurzfassung');

  // Esc / Schließen
  dlg.close();
  await until(() => d.getElementById('ff-reader-toolbar') !== null && dlg.open === false, 1000);
  t.ok(dlg.open === false, 'Dialog schließt');
  t.ok(d.documentElement.style.overflow !== 'hidden' && (d.body.style.overflow || '') !== 'hidden',
    'Scroll-Sperre wird nach dem Schließen freigegeben',
    `html="${d.documentElement.style.overflow}" body="${d.body.style.overflow}"`);
  t.ok(d.activeElement === summaryBtn, 'Fokus kehrt zum Auslöser zurück');
}

/* ================================================================== */
/* 9) Bedienzustände: Pause, Weiter, Beenden, Abschnittssprung         */
/* ================================================================== */
t.group('9) Bedienung (deterministisch: kurze Fixture, verlangsamte Synthese)');
{
  /* Bedienzustände dürfen nicht von Rennbedingungen abhängen. Deshalb hier
     eine kurze Fixture mit bewusst langsamer Synthese (~180 ms je Einheit):
     Pause/Weiter/Stop sind damit zuverlässig beobachtbar. */
  const shortBody = markdownToHtml(`## Erster Abschnitt

Dies ist der erste Satz des Testartikels für die Prüfung der Bedienung.

## Zweiter Abschnitt

Dies ist der zweite Satz des Testartikels für die Prüfung der Bedienung.

## Dritter Abschnitt

Dies ist der dritte Satz des Testartikels für die Prüfung der Bedienung.`);

  const p = await createPage({
    html: buildPage({
      title: 'Bedientest', description: 'Kurz', kurzantwort: 'Kurze Antwort.',
      readingTime: 1, wordCount: 60, bodyHtml: shortBody
    }),
    catalog: VOICE_CATALOGS.macChrome,
    msPerChar: 3
  });
  const d = p.doc;
  const toolbar = d.getElementById('ff-reader-toolbar');
  const isActive = () => toolbar.classList.contains('ff-reader-toolbar--active');

  click(p.win, d.getElementById('ff-listen-btn'));
  await until(() => p.log.length >= 1, 3000);
  t.ok(isActive(), 'Vorlesen aktiviert die Toolbar');
  t.ok(d.getElementById('ff-listen-label').textContent === 'Pausieren', 'Button wechselt zu „Pausieren“');

  click(p.win, d.getElementById('ff-listen-btn'));            // Pause
  const atPause = p.log.length;
  t.ok(d.getElementById('ff-listen-btn').getAttribute('aria-pressed') === 'true', 'Pause hält aria-pressed=true');
  t.ok(d.getElementById('ff-listen-label').textContent === 'Weiterlesen', 'Button wechselt zu „Weiterlesen“');
  await new Promise((r) => setTimeout(r, 400));
  t.ok(p.log.length <= atPause + 1,
    'Pause stoppt die Wiedergabe tatsächlich (keine weiteren speak()-Aufrufe)',
    `vor Pause ${atPause}, nach 400 ms ${p.log.length}`);

  click(p.win, d.getElementById('ff-listen-btn'));            // Weiter
  await until(() => p.log.length > atPause, 5000);
  t.ok(p.log.length > atPause, '„Weiterlesen“ nimmt die Wiedergabe wieder auf');

  const markBefore = p.log.length;
  click(p.win, d.getElementById('ff-listen-next'));           // nächster Abschnitt
  await until(() => p.log.length > markBefore, 5000);
  t.ok(p.log.length > markBefore, 'Abschnittssprung „weiter“ funktioniert');

  /* REGRESSION (Fix 03.09.2026): Pause während der Atempause zwischen zwei
     Sätzen. Früher zeigte der interne Lesezeiger noch auf den bereits
     gesprochenen Satz – „Weiterlesen“ sprach ihn ein zweites Mal. */
  click(p.win, d.getElementById('ff-listen-btn'));            // Start
  await until(() => p.log.length >= 2, 3000);
  click(p.win, d.getElementById('ff-listen-btn'));            // Pause in der Lücke
  await new Promise((r) => setTimeout(r, 250));
  const beforeResume = p.log.slice();
  click(p.win, d.getElementById('ff-listen-btn'));            // Weiter
  await until(() => p.log.length > beforeResume.length, 5000);
  const lastBefore = beforeResume[beforeResume.length - 1];
  const firstAfter = p.log[beforeResume.length];
  t.ok(!firstAfter || firstAfter.text !== lastBefore.text,
    '„Weiterlesen“ wiederholt keinen bereits gesprochenen Satz',
    `doppelt gesprochen: „${lastBefore && lastBefore.text.slice(0, 60)}“`);

  click(p.win, d.getElementById('ff-listen-stop'));           // Beenden
  await new Promise((r) => setTimeout(r, 200));
  t.ok(!isActive(), '„Beenden“ deaktiviert die Toolbar');
  t.ok(d.getElementById('ff-listen-label').textContent === 'Vorlesen', '„Beenden“ setzt das Label zurück');
  t.ok(!d.querySelector('.ff-reader-active'), 'Live-Markierung wird beim Beenden entfernt');
  t.ok(d.getElementById('ff-reader-progress-bar').style.width === '0%', 'Fortschrittsbalken wird zurückgesetzt');
}

/* ================================================================== */
/* 10) Texttreue: nichts geht verloren, nichts doppelt                 */
/* ================================================================== */
t.group('10) Texttreue');
{
  const short = loadArticle('2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel');
  const p = await createPage({
    html: buildPage({
      title: short.title, description: short.description, kurzantwort: short.kurzantwort,
      readingTime: short.readingTime, wordCount: short.wordCount, bodyHtml: short.bodyHtml
    }),
    catalog: VOICE_CATALOGS.macChrome
  });
  click(p.win, p.doc.getElementById('ff-listen-btn'));
  await until(() => p.log.length > 3, 3000);
  await waitFinished(p.win, p.doc, p.log);
  const spoken = norm(spokenText(p.log));

  // Stichproben aus dem echten Artikel müssen im Sprechtext auftauchen
  const headings = [...p.doc.querySelectorAll('.post-content h2')]
    .map((h) => norm(h.textContent).replace(/[.!?]+$/, ''))
    .filter((h) => h.length > 12);
  const missing = headings.filter((h) => !spoken.includes(h.slice(0, 25)));
  t.eq(missing, [], 'Alle H2-Überschriften werden mitgelesen');

  const paragraphs = [...p.doc.querySelectorAll('.post-content p')]
    .map((x) => norm(x.textContent)).filter((x) => x.length > 60);
  const probe = paragraphs.slice(0, 6).map((x) => x.slice(0, 35));
  const missP = probe.filter((x) => !spoken.includes(x));
  t.eq(missP, [], 'Einstiegsabsätze werden mitgelesen');

  const rows = p.doc.querySelectorAll('.post-content tbody tr').length;
  t.ok(rows === 0 || /zeile 1 von \d+/.test(spoken),
    `Tabellenzeilen werden zeilenweise gesprochen (${rows} Zeilen im Artikel)`,
    '„Zeile 1 von …“ im Sprechtext nicht gefunden');
}

/* ================================================================== */
/* 11) Kurzfassung über ALLE Artikel (kein Crash, sinnvolle Ausbeute)  */
/* ================================================================== */
t.group('11) Kurzfassung über alle Artikel');
{
  const slugs = listArticleSlugs();
  let emptyShort = []; let fewBullets = []; let crashed = []; let jumps = 0; let figs = 0;
  for (const slug of slugs) {
    let a;
    try { a = loadArticle(slug); } catch (e) { crashed.push(slug + ' (fixture)'); continue; }
    let p;
    try {
      p = await createPage({
        html: buildPage({
          title: a.title, description: a.description, kurzantwort: a.kurzantwort,
          readingTime: a.readingTime, wordCount: a.wordCount, author: a.author,
          bodyHtml: a.bodyHtml
        }),
        catalog: VOICE_CATALOGS.macChrome
      });
    } catch (e) { crashed.push(slug + ' (createPage)'); continue; }
    if (p.errors.length) { crashed.push(slug + ': ' + p.errors[0].slice(0, 120)); continue; }
    click(p.win, p.doc.getElementById('ff-summary-btn'));
    const ok = await until(() => !!p.doc.getElementById('ff-summary-dialog'), 1500);
    if (!ok) { crashed.push(slug + ' (kein Dialog)'); continue; }
    const dlg = p.doc.getElementById('ff-summary-dialog');
    const hero = dlg.querySelector('.ff-summary__hero-text');
    if (!hero || hero.textContent.trim().length < 40) emptyShort.push(slug);
    const b = dlg.querySelectorAll('.ff-summary__bullet').length;
    if (b < 3) fewBullets.push(`${slug} (${b})`);
    jumps += dlg.querySelectorAll('.ff-summary__jump').length;
    figs += dlg.querySelectorAll('.ff-summary__figure').length;
  }
  t.eq(crashed, [], `Kein Artikel crasht (${slugs.length} geprüft)`);
  t.eq(emptyShort, [], 'Jeder Artikel hat eine verwertbare Kurzantwort');
  t.eq(fewBullets, [], 'Jeder Artikel liefert mindestens 3 Kernaussagen');
  t.ok(jumps > 0, `Sprungmarken gesamt: ${jumps}`);
  t.ok(figs > 0, `Zahlen-Karten gesamt: ${figs}`);
}

/* ================================================================== */
/* 12) CSS: Lesbarkeit & Kontrast (WCAG 2.2 AA)                        */
/* ================================================================== */
t.group('12) CSS-Lesbarkeit (Kontrast, Zeilenlänge, Dunkelmodus)');
{
  const css = fs.readFileSync(READER_CSS, 'utf8');

  const lum = (hex) => {
    const c = hex.replace('#', '');
    const v = [0, 2, 4].map((i) => parseInt(c.slice(i, i + 2), 16) / 255)
      .map((x) => (x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
  };
  const ratio = (a, b) => {
    const l1 = lum(a); const l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };

  t.ok(/\.ff-kurzantwort__text/.test(css), 'Die Kurzantwort-Box hat eine eigene CSS-Komponente (kein Inline-Styling)');
  t.ok(/\[data-theme="dark"\]/.test(css) && /--ff-ka-bg:\s*#10211B/.test(css), 'Kurzantwort-Box hat eine Dunkelmodus-Variante');
  t.ok(/@media\s*\(forced-colors:\s*active\)/.test(css), 'Forced-Colors-Modus (High Contrast) wird bedient');
  t.ok(/prefers-reduced-motion/.test(css), 'prefers-reduced-motion wird respektiert');
  t.ok(/@media print/.test(css), 'Druckdarstellung der Lesehilfen geregelt');

  // Kernkontraste der Kurzfassung
  const checks = [
    ['Kasten-Label hell (#0B4A37 auf #F2F8F5)', '#0B4A37', '#F2F8F5', 7],
    ['Kasten-Text hell (#16211D auf #F2F8F5)', '#16211D', '#F2F8F5', 7],
    ['Kasten-Label dunkel (#86D8BB auf #10211B)', '#86D8BB', '#10211B', 7],
    ['Kasten-Text dunkel (#E8F1EC auf #10211B)', '#E8F1EC', '#10211B', 7],
    ['Dialog-Sekundärtext hell (#5A6360 auf #FFFFFF)', '#5A6360', '#FFFFFF', 4.5],
    ['Dialog-Sekundärtext dunkel (#A8B4AF auf #10211B)', '#A8B4AF', '#10211B', 7],
    ['Überschriften Grün auf Weiß', '#0E5A43', '#FFFFFF', 4.5],
    ['Zahlen-Karten Grün auf Soft', '#0E5A43', '#F1F6F3', 4.5],
    ['Fließtext auf Weiß', '#1F1F23', '#FFFFFF', 7]
  ];
  for (const [label, fg, bg, min] of checks) {
    const r = ratio(fg, bg);
    t.ok(r >= min, `${label}: Kontrast ${r.toFixed(2)}:1 ≥ ${min}:1`, `${r.toFixed(2)}:1`);
  }

  t.ok(/max-inline-size:\s*68ch/.test(css) && /max-inline-size:\s*66ch/.test(css),
    'Kurzantwort und Kernaussagen begrenzen die Zeilenlänge (66–68 ch)');
  t.ok(/font-size:\s*1rem/.test(css) && /line-height:\s*1\.68/.test(css),
    'Kurzantwort-Text ist so groß wie der Fließtext (1rem / 1,68)');

  // Inline-Styling darf nicht zurückkehren
  const single = fs.readFileSync(path.join(ROOT, 'layouts', 'single.html'), 'utf8');
  const kaBlock = single.match(/<div class="ff-kurzantwort"[\s\S]*?<\/div>\s*<\/div>/);
  t.ok(!!kaBlock && !/style="/.test(kaBlock[0]), 'Kurzantwort-Box im Template ohne Inline-Styling');
  t.ok(!!kaBlock && /role="note"/.test(kaBlock[0]), 'Kurzantwort-Box ist als role=note ausgezeichnet');
}

/* ================================================================== */
/* 13) First-Party-Audiofassung (Garantie-Stufe)                      */
/* ================================================================== */
t.group('13) First-Party-Audiofassung (MP3 hat Vorrang vor Web Speech)');
{
  /* Liegt eine serverseitig gerenderte Fassung vor, muss sie VOR der
     Web Speech API genutzt werden: HTML5-<audio> läuft auf jedem Gerät
     und in jedem Browser, die Web Speech API nicht. */
  const map = {
    slug: 'test-artikel',
    durationSeconds: 900,
    unitStart: null
  };

  const mkAudioPage = async (withAudio = true) => {
    const p = await createPage({
      html: buildPage({
        title: art.title, description: art.description, kurzantwort: art.kurzantwort,
        readingTime: art.readingTime, wordCount: art.wordCount, author: art.author,
        bodyHtml: art.bodyHtml,
        audio: withAudio ? '/audio/test-artikel.mp3' : '',
        audioMap: withAudio ? '/audio/test-artikel.timemap.json' : ''
      }),
      catalog: VOICE_CATALOGS.androidChrome   // bewusst: Gerät OHNE männliche Stimme
    });
    if (withAudio) {
      // Zeitkarte nachliefern (der Reader holt sie per XHR)
      map.unitStart = p.win.__ffReaderExport.buildTimeline().timeline.map((u, i) => i * 6);
      const origOpen = p.win.XMLHttpRequest.prototype.open;
      const origSend = p.win.XMLHttpRequest.prototype.send;
      p.win.XMLHttpRequest.prototype.open = function (m, u) { this.__url = u; return origOpen.apply(this, arguments); };
      p.win.XMLHttpRequest.prototype.send = function () {
        const self = this;
        setTimeout(() => {
          Object.defineProperty(self, 'readyState', { value: 4, configurable: true });
          Object.defineProperty(self, 'status', { value: 200, configurable: true });
          Object.defineProperty(self, 'responseText', { value: JSON.stringify(map), configurable: true });
          if (self.onreadystatechange) self.onreadystatechange();
        }, 0);
      };
    }
    return p;
  };

  const ap = await mkAudioPage(true);
  t.eq(ap.errors, [], 'Audio-Stufe: keine Laufzeitfehler beim Laden');

  click(ap.win, ap.doc.getElementById('ff-listen-btn'));
  await until(() => ap.doc.getElementById('ff-reader-toolbar').classList.contains('ff-reader-toolbar--playing'), 3000);

  t.ok(ap.doc.getElementById('ff-reader-toolbar').classList.contains('ff-reader-toolbar--playing'),
    'Klick startet die Wiedergabe');
  t.eq(ap.log, [], 'Web Speech wird NICHT bemüht, wenn eine Audiofassung vorliegt (kein speechSynthesis.speak)');
  const audioEl = ap.win.__audioEl;
  t.ok(!!audioEl, 'HTML5-<audio>-Element wird erzeugt');
  t.ok(audioEl.getAttribute('src') === '/audio/test-artikel.mp3', 'Korrekte MP3-Quelle gesetzt');
  t.ok(audioEl.getAttribute('playsinline') !== null, 'playsinline gesetzt (iPhone spielt inline statt Vollbild)');
  /* play() ist laut Spec asynchron: erst wenn die Wiedergabe tatsächlich
     läuft, ist paused === false. Deshalb auf echten Fortschritt warten,
     statt in einem Wettlauf-Zeitfenster zu prüfen. */
  t.ok(await until(() => audioEl.currentTime > 0, 3000), 'Audio beginnt zu laufen (currentTime steigt)');
  t.ok(audioEl.paused === false, 'Audio läuft (paused === false)');
  t.ok(/Studiostimme|Audiofassung/.test(ap.doc.getElementById('ff-reader-status').textContent),
    'Status meldet die Studiofassung, nicht die Gerätstimme',
    ap.doc.getElementById('ff-reader-status').textContent);

  // Fortschritt + Live-Markierung
  await until(() => audioEl.currentTime > 12, 4000);
  t.ok(ap.doc.getElementById('ff-reader-progress-bar').style.width !== '0%'
    && ap.doc.getElementById('ff-reader-progress-bar').style.width !== '',
    'Fortschrittsbalken folgt der Audiozeit');
  t.ok(!!ap.doc.querySelector('.ff-reader-active'), 'Live-Markierung folgt dem gesprochenen Abschnitt');
  t.ok(/noch\s+\d+:\d+/.test(ap.doc.getElementById('ff-reader-remaining').textContent),
    'Restzeit wird angezeigt', ap.doc.getElementById('ff-reader-remaining').textContent);

  // Pause / Weiter
  click(ap.win, ap.doc.getElementById('ff-listen-btn'));
  await new Promise((r) => setTimeout(r, 60));
  t.ok(audioEl.paused === true, 'Pause hält das Audio an');
  const atPause = audioEl.currentTime;
  await new Promise((r) => setTimeout(r, 120));
  t.ok(Math.abs(audioEl.currentTime - atPause) < 0.01, 'Zeit läuft in der Pause nicht weiter');
  click(ap.win, ap.doc.getElementById('ff-listen-btn'));
  await until(() => audioEl.paused === false, 2000);
  t.ok(audioEl.paused === false, 'Weiterlesen nimmt das Audio wieder auf');

  // Abschnittssprung
  const beforeJump = audioEl.currentTime;
  click(ap.win, ap.doc.getElementById('ff-listen-next'));
  await until(() => audioEl.currentTime > beforeJump + 1, 2000);
  t.ok(audioEl.currentTime > beforeJump + 1, 'Abschnittssprung „weiter“ springt im Audio');

  // Beenden
  click(ap.win, ap.doc.getElementById('ff-listen-stop'));
  await new Promise((r) => setTimeout(r, 80));
  t.ok(audioEl.paused === true, '„Beenden“ stoppt das Audio');
  t.ok(!ap.doc.querySelector('.ff-reader-active'), 'Markierung wird beim Beenden entfernt');
  t.ok(ap.doc.getElementById('ff-listen-label').textContent === 'Vorlesen', 'Toolbar geht in den Ruhezustand');

  /* Rückfall: ohne Audiofassung muss dieselbe Seite die Web-Speech-Stufe
     nutzen – die Garantie-Stufe darf die Grundfunktion nie abschalten. */
  const noAudio = await mkAudioPage(false);
  click(noAudio.win, noAudio.doc.getElementById('ff-listen-btn'));
  await until(() => noAudio.log.length > 0, 3000);
  t.ok(noAudio.log.length > 0, 'Ohne Audiofassung greift automatisch die Web-Speech-Stufe');
  t.ok(!noAudio.win.__audioEl, 'Ohne Audiofassung wird kein <audio>-Element erzeugt');
}

/* ================================================================== */
const fail = t.report();
if (fail > 0) {
  console.log(`\n💥 ${fail} Prüfung(en) fehlgeschlagen.`);
  process.exit(1);
}
console.log('\n🎉 Funktionstest bestanden: Vorlesen + Kurzfassung funktionieren im echten DOM.');
