#!/usr/bin/env node
// ============================================================
//  LIGHTHOUSE LIVE – Laborwerte der AUSGELIEFERTEN Seite
//  ------------------------------------------------------------
//  WARUM ES DIESES SKRIPT GIBT (26.10.2026)
//
//  Das Haus hatte zwei Messungen und keine davon sah Produktion:
//    · `design-varianten.yml` misst VARIANTEN unter
//      `.cache/design-varianten/<id>/public` – also Entwürfe.
//    · `lighthouserc.cjs` bricht ohne Varianten-Build ab.
//  Die Seite, die Besucher wirklich laden (GitHub Pages hinter dem
//  Cloudflare-Proxy), wurde von keinem Gate gemessen. Dieses Skript
//  schließt die Lücke – mit denselben Schwellen wie das CI-Gate:
//  es liest `lighthouse/assertions.json`, die aus
//  `data/design/regelwerk.yaml` erzeugt werden. Keine zweite Zahl.
//
//  WARUM ES NICHT ROT MACHT (und das ist Absicht)
//  Ein Laborlauf durch CDN, über Mobilfunk-Drosselung, ist eine
//  Diagnose, kein Freigabe-Kriterium. Ein Befund hier heißt „schau
//  hin", nicht „Deploy blockieren". Verbindlich für die Wirklichkeit
//  sind die Felddaten (`scripts/cwv_feld_wache.py`): CrUX misst echte
//  Besucher. Dieses Skript liefert dafür die Ursachen-Hinweise
//  (welche Audit-Schwelle reißt) am selben Tag, an dem sie auffällt.
//
//  WARUM DER IMPORT ERST IM LAUF PASSIERT (04.11.2026, Vorgang WF-0032 / #1026)
//  Bis hierher standen `lighthouse`, `playwright-core` und
//  `../e2e/browser.mjs` als STATISCHE Importe am Modulkopf. Der
//  Wochenlauf startete den Offline-Selbsttest aber VOR `npm ci` –
//  und Node bricht einen Import, dessen Paket fehlt, mit
//  `ERR_MODULE_NOT_FOUND` ab, BEVOR eine einzige Zeile Prüflogik
//  läuft. Folge: Eine unverbindliche Labordiagnose nahm die
//  verbindliche Feldmessung mit ins Rot (Lauf 41456548199), und die
//  Meldung sprach von einem kaputten Selbsttest, obwohl der Selbsttest
//  nie Gelegenheit hatte, etwas zu prüfen.
//
//  Die Heilung ist keine Umgehung, sondern eine Trennung:
//    · Der Modulkopf braucht ausschließlich Node-Bordmittel
//      (`node:fs`, `node:net`, `node:path`, `node:url`). Importieren
//      ist damit immer möglich – auch in einem nackten Checkout.
//    · Laufzeitpakete lädt `ladeLaufzeit()` beim ersten echten Lauf.
//      Fehlt etwas, sagt die Meldung WAS fehlt und WIE es entsteht
//      (`npm ci --ignore-scripts`), statt eines nackten Stacktrace.
//    · `--selftest` prüft die gesamte Bewertungslogik offline und
//      ohne Browser. Ein Selbsttest, der Pakete braucht, kann genau
//      die Lage nicht prüfen, für die er existiert.
//
//  Aufruf:
//    node scripts/lighthouse_live.mjs                       # Ziele aus data/cwv/feld_ziele.json
//    node scripts/lighthouse_live.mjs --url https://…/x/    # einzelne URL
//    node scripts/lighthouse_live.mjs --laeufe 3 --schreiben
//    node scripts/lighthouse_live.mjs --json
//    node scripts/lighthouse_live.mjs --streng              # Befund ⇒ Exit 1
//    node scripts/lighthouse_live.mjs --selftest            # offline, ohne Pakete
//
//  Exit: 0 = gemessen (Befunde stehen im Bericht) · 1 = Befund, nur mit
//        `--streng` · 2 = nicht messbar (Chromium, Netz, Konfiguration,
//        fehlende Laufzeitpakete).
//
//  AUSGABEKANÄLE (und warum das getrennt ist)
//  `stdout` trägt im `--json`-Modus ausschließlich EIN JSON-Dokument.
//  Fortschritt und Warnungen gehen immer nach `stderr`. Ein Werkzeug,
//  dessen Ausgabe man parsen will, darf keine Fortschrittszeile in den
//  Datenstrom mischen – sonst scheitert jeder Aufrufer am ersten
//  `JSON.parse`, und niemand kann sagen, woran es lag.
//
//  Browser: derselbe Resolver wie die E2E-Suite (`e2e/browser.mjs`) –
//  gepinntes Chromium aus dem Lockfile, kein zweiter Browserweg.
// ============================================================

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HIER = path.dirname(fileURLToPath(import.meta.url));
const WURZEL = path.resolve(HIER, '..');
const ZIELE_DATEI = path.join(WURZEL, 'data', 'cwv', 'feld_ziele.json');
const ASSERTIONS = path.join(WURZEL, 'lighthouse', 'assertions.json');
const AUSGABE_JSON = path.join(WURZEL, 'data', 'cwv', 'labor', 'befund.json');
const AUSGABE_MD = path.join(WURZEL, 'data', 'cwv', 'labor', 'befund.md');
const BASIS = 'https://franksfinanzcheck.de';

// ------------------------------------------------------------
//  Laufzeitpakete (dynamisch – siehe Kopfkommentar)
// ------------------------------------------------------------
/** Fehler der Laufzeitbeschaffung: messbar unterscheidbar von einem Befund. */
export class LaufzeitFehler extends Error {
  constructor(meldung) {
    super(meldung);
    this.name = 'LaufzeitFehler';
  }
}

/**
 * Lädt Lighthouse, Playwright und den Browser-Resolver.
 * Absichtlich KEIN Top-Level-Import: Der Selbsttest und das Parsen der
 * Schwellen müssen in einem Checkout ohne `node_modules` funktionieren.
 * `lader` ist injizierbar, damit der Test den Fehlerweg ohne echtes
 * Paket-Installieren prüfen kann.
 */
export async function ladeLaufzeit(lader = (name) => import(name)) {
  try {
    const lighthouseModul = await lader('lighthouse');
    const playwrightModul = await lader('playwright-core');
    const browserModul = await lader('./e2e/browser.mjs');
    const lighthouse = lighthouseModul?.default ?? lighthouseModul;
    const chromium = playwrightModul?.chromium;
    const resolveLaunchOptions = browserModul?.resolveLaunchOptions;
    if (typeof lighthouse !== 'function') {
      throw new Error('lighthouse liefert keine aufrufbare Messfunktion');
    }
    if (!chromium || typeof chromium.launch !== 'function') {
      throw new Error('playwright-core liefert kein chromium.launch');
    }
    if (typeof resolveLaunchOptions !== 'function') {
      throw new Error('e2e/browser.mjs liefert kein resolveLaunchOptions');
    }
    return { lighthouse, chromium, resolveLaunchOptions };
  } catch (fehler) {
    const grund = fehler instanceof Error ? fehler.message : String(fehler);
    throw new LaufzeitFehler(
      `Laufzeitpakete fehlen oder sind unbrauchbar (${grund}). `
      + 'Abhilfe: npm ci --ignore-scripts && npm run browser:setup',
    );
  }
}

// ------------------------------------------------------------
//  Argumente (bewusst ohne Framework: ein Skript, keine Kette)
// ------------------------------------------------------------
const HILFE = 'node scripts/lighthouse_live.mjs [--url URL]… [--laeufe N] [--schreiben] '
  + '[--json] [--streng] [--selftest]';

/**
 * Zerlegt die Kommandozeile. Jeder Fehler ist ein WERT-Fehler mit Klartext:
 * Ein stillschweigend überlesenes Argument wäre ein Lauf mit den falschen
 * Zielen und würde als „gemessen" gemeldet.
 */
export function argumente(argv) {
  const opt = {
    urls: [], laeufe: 1, schreiben: false, json: false, streng: false,
    selftest: false, basis: BASIS, hilfe: false,
  };
  const wert = (i, flagge) => {
    const naechster = argv[i];
    if (naechster === undefined || naechster.startsWith('--')) {
      throw new Error(`${flagge} braucht einen Wert`);
    }
    return naechster;
  };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--url') opt.urls.push(wert(++i, '--url'));
    else if (a === '--basis') opt.basis = wert(++i, '--basis');
    else if (a === '--laeufe') opt.laeufe = Number(wert(++i, '--laeufe'));
    else if (a === '--schreiben') opt.schreiben = true;
    else if (a === '--json') opt.json = true;
    else if (a === '--streng') opt.streng = true;
    else if (a === '--selftest') opt.selftest = true;
    else if (a === '--hilfe' || a === '-h') opt.hilfe = true;
    else throw new Error(`Unbekanntes Argument: ${a}`);
  }
  if (!Number.isInteger(opt.laeufe) || opt.laeufe < 1 || opt.laeufe > 5) {
    throw new Error('--laeufe muss eine ganze Zahl von 1 bis 5 sein');
  }
  if (!/^https?:\/\//.test(opt.basis) || /\s/.test(opt.basis)) {
    throw new Error(`--basis muss eine absolute http(s)-URL sein: ${opt.basis}`);
  }
  for (const url of opt.urls) {
    if (!/^https?:\/\//.test(url) && !url.startsWith('/')) {
      throw new Error(`--url muss eine absolute URL oder ein Pfad ab "/" sein: ${url}`);
    }
  }
  return opt;
}

/** Ziele aus `data/cwv/feld_ziele.json` – fail-closed bei kaputter Liste. */
export function zieleAusDatei(datei = ZIELE_DATEI) {
  const roh = JSON.parse(readFileSync(datei, 'utf8'));
  const ziele = roh?.ziele;
  if (!Array.isArray(ziele) || ziele.length === 0) {
    throw new Error(`${datei}: "ziele" fehlt oder ist leer`);
  }
  const pfade = ziele.map((z) => String(z?.pfad ?? '').trim());
  const kaputt = pfade.filter((p) => !p.startsWith('/'));
  if (kaputt.length) {
    throw new Error(`${datei}: Ziel ohne absoluten Pfad: ${kaputt.join(', ')}`);
  }
  return pfade;
}

/** Freier TCP-Port für den DevTools-Endpunkt (kein festes 9222 in CI). */
export function freierPort() {
  return new Promise((aufloesen, ablehnen) => {
    const server = net.createServer();
    server.unref();
    server.on('error', ablehnen);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      server.close(() => aufloesen(port));
    });
  });
}

// ------------------------------------------------------------
//  Schwellen: EINE Wahrheit (lighthouse/assertions.json)
// ------------------------------------------------------------
export function ladeAssertions(datei = ASSERTIONS) {
  const roh = JSON.parse(readFileSync(datei, 'utf8'));
  const assertions = roh?.assertions;
  if (!assertions || typeof assertions !== 'object' || Array.isArray(assertions)) {
    throw new Error(`${datei}: "assertions" fehlt oder ist kein Objekt`);
  }
  return assertions;
}

// Lighthouse 13 hat einige Kern-Audits in „Insights" umbenannt. Die
// Schwellen im Repo tragen weiter die etablierten IDs (so stehen sie im
// Regelwerk); hier wird übersetzt – EINE Stelle statt zweier Wahrheiten.
const AUDIT_ALIAS = { 'dom-size': 'dom-size-insight' };

/** Wert einer Assertion im Lauf-Ergebnis (Score oder numerische Größe). */
export function messwert(lhr, schluessel) {
  if (schluessel.startsWith('categories:')) {
    const kategorie = schluessel.slice('categories:'.length);
    const score = lhr?.categories?.[kategorie]?.score;
    return typeof score === 'number' ? { wert: score, einheit: 'score' } : null;
  }
  const audit = lhr?.audits?.[AUDIT_ALIAS[schluessel] || schluessel];
  if (!audit || typeof audit.numericValue !== 'number') return null;
  return { wert: audit.numericValue, einheit: audit.numericUnit || '' };
}

export function mittelwerte(werte, methode) {
  const sortiert = [...werte].sort((a, b) => a - b);
  if (methode === 'pessimistic') return sortiert[sortiert.length - 1];
  if (methode === 'optimistic') return sortiert[0];
  const mitte = Math.floor(sortiert.length / 2);
  return sortiert.length % 2 ? sortiert[mitte] : (sortiert[mitte - 1] + sortiert[mitte]) / 2;
}

/** Prüft EINEN Lauf-Satz gegen die Schwellen und nennt jede gerissene Grenze. */
export function pruefeAssertions(laeufe, assertions) {
  if (!Array.isArray(laeufe) || laeufe.length === 0) {
    throw new Error('pruefeAssertions braucht mindestens einen Lauf');
  }
  const befunde = [];
  for (const [schluessel, eintrag] of Object.entries(assertions || {})) {
    // Assertion-Form im Repo: ["error", { minScore | maxNumericValue, aggregationMethod }]
    const [, grenze] = Array.isArray(eintrag) ? eintrag : [null, eintrag];
    const werte = laeufe.map((lhr) => messwert(lhr, schluessel)).filter(Boolean);
    if (!werte.length) {
      befunde.push({
        schluessel,
        urteil: 'NICHT_GEMESSEN',
        stufe: Array.isArray(eintrag) ? eintrag[0] : 'error',
        text: `${schluessel}: vom Lauf nicht geliefert`,
      });
      continue;
    }
    const methode = grenze?.aggregationMethod || 'median';
    const wert = mittelwerte(werte.map((w) => w.wert), methode);
    if (typeof grenze?.minScore === 'number' && wert < grenze.minScore) {
      befunde.push({
        schluessel,
        urteil: 'UNTER_SCHWELLE',
        stufe: Array.isArray(eintrag) ? eintrag[0] : 'error',
        text: `${schluessel}: ${wert.toFixed(2)} < ${grenze.minScore} (minScore, ${methode})`,
      });
    }
    if (typeof grenze?.maxNumericValue === 'number' && wert > grenze.maxNumericValue) {
      befunde.push({
        schluessel,
        urteil: 'UEBER_SCHWELLE',
        stufe: Array.isArray(eintrag) ? eintrag[0] : 'error',
        text: `${schluessel}: ${Math.round(wert)} > ${grenze.maxNumericValue} `
          + `(${werte[0].einheit || 'ms'}, ${methode})`,
      });
    }
  }
  return befunde;
}

// ------------------------------------------------------------
//  Messung
// ------------------------------------------------------------
export function laborScores(lhr) {
  const k = lhr?.categories || {};
  const score = (n) => (typeof k[n]?.score === 'number' ? Math.round(k[n].score * 100) : null);
  return {
    performance: score('performance'),
    accessibility: score('accessibility'),
    'best-practices': score('best-practices'),
    seo: score('seo'),
  };
}

/**
 * Messoptionen für Lighthouse. Formfaktor und Emulation stehen hier, damit
 * ein Lauf reproduzierbar ist – ein „Handy" mit 1200 px wäre keine Messung.
 */
export function messOptionen(port, extra = {}) {
  return {
    port,
    output: 'json',
    logLevel: 'error',
    formFactor: 'mobile',
    screenEmulation: {
      mobile: true, width: 390, height: 844, deviceScaleFactor: 3, disabled: false,
    },
    ...extra,
  };
}

/** Standard-Messer: genau ein Lighthouse-Lauf gegen den DevTools-Port. */
export function erzeugeMesser(lighthouse) {
  return async (url, port) => lighthouse(url, messOptionen(port));
}

/**
 * Misst eine URL `laeufe`-mal. `messer` ist injizierbar – die Tests
 * beweisen damit Anzahl, Reihenfolge und Fehlerweg ohne Browser.
 */
export async function messeUrl(url, port, laeufe, messer) {
  if (typeof messer !== 'function') {
    throw new LaufzeitFehler('messeUrl braucht eine Messfunktion (messer)');
  }
  if (!Number.isInteger(laeufe) || laeufe < 1) {
    throw new Error(`laeufe muss eine ganze Zahl ≥ 1 sein: ${laeufe}`);
  }
  const ergebnisse = [];
  for (let i = 0; i < laeufe; i += 1) {
    const antwort = await messer(url, port);
    if (!antwort?.lhr) throw new Error(`${url}: Lighthouse lieferte kein Ergebnis`);
    ergebnisse.push(antwort.lhr);
  }
  return ergebnisse;
}

function zeile(pfad, seite) {
  const s = seite.scores;
  const wert = (n) => (n === null ? '–' : n);
  const zustand = seite.befunde.length ? `${seite.befunde.length} Befund(e)` : 'im Rahmen';
  return `| \`${pfad}\` | ${zustand} | ${wert(s.performance)} | ${wert(s.accessibility)} `
    + `| ${wert(s['best-practices'])} | ${wert(s.seo)} |`;
}

export function bericht(seiten, datum) {
  const zeilen = [
    '# Lighthouse LIVE – Laborwerte der ausgelieferten Seite',
    '',
    `**Stand:** ${datum} · **Gerät:** Mobile-Emulation (390 × 844, gedrosselt)`,
    '',
    '> Schwellen aus `lighthouse/assertions.json` (erzeugt aus `data/design/regelwerk.yaml`) –',
    '> dieselben wie im Varianten-Gate. Ein Befund hier ist eine DIAGNOSE, kein',
    '> Deploy-Blocker: verbindlich für die Wirklichkeit sind die Felddaten',
    '> (`data/cwv/feld/befund.md`).',
    '',
    '| Seite | Zustand | Perf | A11y | Best-Practices | SEO |',
    '|---|---|---|---|---|---|',
  ];
  for (const s of seiten) zeilen.push(zeile(s.pfad, s));
  const offen = seiten.flatMap((s) => s.befunde.map((b) => `\`${s.pfad}\` – ${b.text}`));
  if (offen.length) {
    zeilen.push('', '## Gerissene Schwellen', '');
    for (const o of offen) zeilen.push(`- ${o}`);
  }
  return `${zeilen.join('\n')}\n`;
}

/** Anzeigename: Produktionsdomain abschneiden, lokale Läufe auf den Pfad bringen. */
export function anzeigepfad(url, basis) {
  const wurzel = String(basis).replace(/\/$/, '');
  if (url.startsWith(wurzel)) return url.slice(wurzel.length) || '/';
  try {
    const teile = new URL(url);
    return teile.pathname + teile.search;
  } catch {
    return url;
  }
}

// ------------------------------------------------------------
//  Selbsttest (offline, ohne Laufzeitpakete, ohne Browser)
// ------------------------------------------------------------
/**
 * Beweist die Bewertungslogik und die Ausgabekanäle OHNE Netz, ohne
 * Chromium und ohne `node_modules`. Genau das ist der Punkt: Der Lauf
 * prüft dieses Werkzeug VOR `npm ci`; ein Selbsttest, der Pakete
 * braucht, wäre an dieser Stelle blind.
 */
export function selftest() {
  const fehler = [];
  let geprueft = 0;
  const muss = (bedingung, text) => {
    geprueft += 1;
    if (!bedingung) fehler.push(text);
  };
  const wirft = (fn, muster, text) => {
    try {
      fn();
      fehler.push(`${text} (kein Fehler geworfen)`);
    } catch (ausnahme) {
      if (muster && !muster.test(String(ausnahme.message))) {
        fehler.push(`${text} (${
          String(ausnahme.message).slice(0, 120)
        })`);
      }
    }
  };
  const lauf = (scores = {}, audits = {}) => {
    const kategorien = {};
    for (const [name, score] of Object.entries(scores)) kategorien[name] = { score };
    return { categories: kategorien, audits };
  };
  const lcp = (ms) => ({ audits: { 'largest-contentful-paint': { numericValue: ms, numericUnit: 'millisecond' } } });

  // 1. Schwellen: eine Wahrheit, aus der Datei, nicht aus dem Kopf.
  const assertions = ladeAssertions();
  muss(Object.keys(assertions).length >= 6, 'zu wenige Assertions gelesen');
  muss(assertions['categories:performance']?.[1]?.minScore === 0.9,
    'Performance-Schwelle ist nicht 0.9');

  // 2. Messwert-Leser: Score 0…1, numerische Audits mit Einheit, Alias.
  muss(messwert(lauf({ performance: 0.93 }), 'categories:performance')?.wert === 0.93,
    'Kategorie-Score wird nicht als 0…1 gelesen');
  muss(messwert(lcp(1800), 'largest-contentful-paint')?.wert === 1800,
    'numerisches Audit liefert keinen Wert');
  muss(messwert(lauf(), 'largest-contentful-paint') === null,
    'fehlendes Audit muss null sein');
  muss(messwert(lauf({}, { 'dom-size-insight': { numericValue: 900, numericUnit: 'element' } }),
    'dom-size')?.wert === 900, 'Lighthouse-13-Alias dom-size fehlt');

  // 3. Aggregation: die Methode aus der Assertion, nicht die bequemste.
  muss(mittelwerte([3000, 1000, 2000], 'median') === 2000, 'Median falsch');
  muss(mittelwerte([3000, 1000], 'median') === 2000, 'Median bei gerader Anzahl falsch');
  muss(mittelwerte([3000, 1000, 2000], 'pessimistic') === 3000, 'pessimistic falsch');
  muss(mittelwerte([1000, 3000], 'optimistic') === 1000, 'optimistic falsch');

  // 4. Gerissene Grenzen werden benannt – und geschonte nicht.
  const gerissen = pruefeAssertions([lcp(4200)],
    { 'largest-contentful-paint': ['error', { maxNumericValue: 2500 }] });
  muss(gerissen.length === 1 && gerissen[0].urteil === 'UEBER_SCHWELLE',
    'gerissene Grenze wird nicht erkannt');
  muss(/4200 > 2500/.test(gerissen[0]?.text || ''), 'Befundtext nennt Wert und Grenze nicht');
  muss(pruefeAssertions([lcp(1200)],
    { 'largest-contentful-paint': ['error', { maxNumericValue: 2500 }] }).length === 0,
  'eingehaltene Grenze ergab einen Befund');
  muss(pruefeAssertions([lauf()],
    { 'total-blocking-time': ['error', { maxNumericValue: 200 }] })[0]?.urteil === 'NICHT_GEMESSEN',
  'nicht geliefertes Audit ist nicht NICHT_GEMESSEN');

  // 5. CLI: Klartext bei Unsinn statt stiller Fehlbelegung.
  const opt = argumente(['--url', '/x/', '--laeufe', '2', '--json']);
  muss(opt.laeufe === 2 && opt.json === true && opt.urls[0] === '/x/', 'Argumente falsch gelesen');
  wirft(() => argumente(['--laeufe', '0']), /1 bis 5/, '--laeufe 0 muss abgelehnt werden');
  wirft(() => argumente(['--unfug']), /Unbekanntes Argument/, 'unbekanntes Argument muss auffallen');
  wirft(() => argumente(['--url', '--json']), /braucht einen Wert/, '--url ohne Wert muss auffallen');
  wirft(() => argumente(['--basis', 'javascript:alert(1)']), /absolute http/, 'unsinnige Basis muss auffallen');

  // 6. Anzeigepfad und Bericht bleiben ortsunabhängig lesbar.
  muss(anzeigepfad('https://franksfinanzcheck.de/werkzeuge/', 'https://franksfinanzcheck.de') === '/werkzeuge/',
    'Anzeigepfad schneidet die Basis nicht ab');
  const text = bericht([
    { pfad: '/', scores: { performance: 99, accessibility: 100, 'best-practices': 100, seo: 100 }, befunde: [] },
    { pfad: '/werkzeuge/', scores: { performance: 71, accessibility: 100, 'best-practices': 100, seo: 100 },
      befunde: [{ text: 'categories:performance: 0.71 < 0.9 (minScore, median)' }] },
  ], '2026-11-04');
  muss(/## Gerissene Schwellen/.test(text), 'Bericht ohne Abschnitt „Gerissene Schwellen"');
  muss(/im Rahmen/.test(text), 'Bericht ohne Zustand „im Rahmen"');

  // Die Zahl ist GEZÄHLT, nicht behauptet: Eine Meldung „27 Prüfungen“,
  // die nicht mit dem Code wächst, ist eine Zahl ohne Deckung.
  return { fehler, geprueft };
}

async function selftestLauf() {
  let ergebnis;
  try {
    ergebnis = selftest();
  } catch (fehler) {
    console.error(`🛑 Selbsttest nicht ausführbar: ${fehler.message}`);
    return 2;
  }
  // 8. Laufzeitfehler sind ein KLARTEXT-Fehler, kein Stacktrace.
  try {
    await ladeLaufzeit(async () => { throw new Error('Cannot find package "lighthouse"'); });
    ergebnis.fehler.push('fehlendes Laufzeitpaket wurde nicht als LaufzeitFehler gemeldet');
  } catch (fehler) {
    if (!(fehler instanceof LaufzeitFehler)) {
      ergebnis.fehler.push(`Laufzeitfehler hat die falsche Klasse (${fehler?.name || typeof fehler})`);
    } else if (!/npm ci --ignore-scripts/.test(fehler.message)) {
      ergebnis.fehler.push('Laufzeitfehler nennt die Abhilfe nicht');
    }
  }
  // 9. Ein Messer, das nichts liefert, darf nicht als „gemessen" durchgehen.
  try {
    await messeUrl('https://x.de/', 9222, 1, async () => ({}));
    ergebnis.fehler.push('fehlendes lhr wurde nicht als Fehler gemeldet');
  } catch (fehler) {
    if (!/kein Ergebnis/.test(String(fehler.message))) {
      ergebnis.fehler.push('fehlendes lhr meldet nicht „kein Ergebnis"');
    }
  }
  if (ergebnis.fehler.length) {
    console.error('🛑 LIGHTHOUSE-LIVE-SELBSTTEST FEHLGESCHLAGEN:');
    for (const eintrag of ergebnis.fehler) console.error(`  · ${eintrag}`);
    return 2;
  }
  console.log(`✅ Lighthouse-LIVE: Selbsttest grün (${ergebnis.geprueft} Prüfungen, `
    + 'ohne Netz, ohne Browser, ohne node_modules)');
  return 0;
}

// ------------------------------------------------------------
//  Hauptlauf
// ------------------------------------------------------------
/** Fortschritt und Warnungen – immer `stderr`, nie in den Datenstrom. */
function protokoll(text) {
  console.error(text);
}

async function lauf(opt) {
  let pfade = opt.urls;
  if (!pfade.length) {
    try {
      pfade = zieleAusDatei();
    } catch (fehler) {
      protokoll(`🛑 Zielliste nicht lesbar (${ZIELE_DATEI}): ${fehler.message}`);
      return 2;
    }
  }
  const basis = opt.basis.replace(/\/$/, '');
  const urls = pfade.map((p) => (p.startsWith('http') ? p : `${basis}/${p.replace(/^\//, '')}`));

  let assertions;
  try {
    assertions = ladeAssertions();
  } catch (fehler) {
    protokoll(`🛑 Schwellen nicht lesbar (${ASSERTIONS}): ${fehler.message}`);
    protokoll('   Erzeugen: python3 scripts/design_variant_gate.py --lighthouse-export');
    return 2;
  }

  let laufzeit;
  let port;
  try {
    laufzeit = await ladeLaufzeit();
    port = await freierPort();
  } catch (fehler) {
    protokoll(`🛑 ${fehler.message}`);
    return 2;
  }

  let browser;
  try {
    const start = await laufzeit.resolveLaunchOptions();
    browser = await laufzeit.chromium.launch({
      headless: true,
      ...start,
      args: [...(start.args || []), `--remote-debugging-port=${port}`],
    });
  } catch (fehler) {
    protokoll(`🛑 Chromium startet nicht: ${fehler.message}`);
    protokoll('   Zuerst: npm ci && npm run browser:setup');
    return 2;
  }

  const messer = erzeugeMesser(laufzeit.lighthouse);
  const seiten = [];
  try {
    for (const url of urls) {
      const laeufe = await messeUrl(url, port, opt.laeufe, messer);
      const befunde = pruefeAssertions(laeufe, assertions);
      const pfad = anzeigepfad(url, basis);
      const scores = laborScores(laeufe[laeufe.length - 1]);
      seiten.push({ pfad, url, scores, befunde });
      const marke = befunde.length ? '⚠️' : '✅';
      protokoll(`${marke} ${pfad} ${JSON.stringify(scores)}`);
      for (const b of befunde) protokoll(`   · ${b.text}`);
    }
  } catch (fehler) {
    protokoll(`🛑 Messung gescheitert: ${fehler.message}`);
    return 2;
  } finally {
    await browser.close().catch(() => {});
  }

  const datum = new Date().toISOString().slice(0, 10);
  const ergebnis = { datum, laeufe: opt.laeufe, seiten };
  const text = bericht(seiten, datum);

  if (opt.schreiben) {
    mkdirSync(path.dirname(AUSGABE_JSON), { recursive: true });
    writeFileSync(AUSGABE_JSON, `${JSON.stringify(ergebnis, null, 2)}\n`, 'utf8');
    writeFileSync(AUSGABE_MD, text, 'utf8');
  }
  if (opt.json) {
    // stdout trägt ausschließlich das JSON-Dokument.
    process.stdout.write(`${JSON.stringify(ergebnis, null, 2)}\n`);
  } else {
    process.stdout.write(`\n${text}`);
  }

  const gesamt = seiten.reduce((summe, s) => summe + s.befunde.length, 0);
  return gesamt && opt.streng ? 1 : 0;
}

export async function main(argv = process.argv.slice(2)) {
  let opt;
  try {
    opt = argumente(argv);
  } catch (fehler) {
    console.error(`🛑 ${fehler.message}`);
    console.error(`   ${HILFE}`);
    return 2;
  }
  if (opt.hilfe) {
    console.log(HILFE);
    return 0;
  }
  if (opt.selftest) return selftestLauf();
  return lauf(opt);
}

// Direkt aufgerufen misst das Skript und setzt den Exit-Code. Importiert
// (Tests) passiert nichts – eine Messung, die beim Import startet, wäre
// nicht prüfbar.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(await main());
}
