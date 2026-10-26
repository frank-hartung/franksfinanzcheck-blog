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
//  Aufruf:
//    node scripts/lighthouse_live.mjs                       # Ziele aus data/cwv/feld_ziele.json
//    node scripts/lighthouse_live.mjs --url https://…/x/    # einzelne URL
//    node scripts/lighthouse_live.mjs --laeufe 3 --schreiben
//    node scripts/lighthouse_live.mjs --json
//    node scripts/lighthouse_live.mjs --streng              # Befund ⇒ Exit 1
//
//  Exit: 0 = gemessen (Befunde stehen im Bericht) · 1 = Befund, nur mit
//        `--streng` · 2 = nicht messbar (Chromium, Netz, Konfiguration).
//
//  Browser: derselbe Resolver wie die E2E-Suite (`e2e/browser.mjs`) –
//  gepinntes Chromium aus dem Lockfile, kein zweiter Browserweg.
// ============================================================

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

import lighthouse from 'lighthouse';
import { chromium } from 'playwright-core';

import { resolveLaunchOptions } from '../e2e/browser.mjs';

const HIER = path.dirname(fileURLToPath(import.meta.url));
const WURZEL = path.resolve(HIER, '..');
const ZIELE_DATEI = path.join(WURZEL, 'data', 'cwv', 'feld_ziele.json');
const ASSERTIONS = path.join(WURZEL, 'lighthouse', 'assertions.json');
const AUSGABE_JSON = path.join(WURZEL, 'data', 'cwv', 'labor', 'befund.json');
const AUSGABE_MD = path.join(WURZEL, 'data', 'cwv', 'labor', 'befund.md');
const BASIS = 'https://franksfinanzcheck.de';

// ------------------------------------------------------------
//  Argumente (bewusst ohne Framework: ein Skript, keine Kette)
// ------------------------------------------------------------
export function argumente(argv) {
  const opt = { urls: [], laeufe: 1, schreiben: false, json: false, streng: false, basis: BASIS };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--url') opt.urls.push(argv[++i]);
    else if (a === '--basis') opt.basis = argv[++i];
    else if (a === '--laeufe') opt.laeufe = Number(argv[++i]);
    else if (a === '--schreiben') opt.schreiben = true;
    else if (a === '--json') opt.json = true;
    else if (a === '--streng') opt.streng = true;
    else if (a === '--hilfe' || a === '-h') {
      console.log('node scripts/lighthouse_live.mjs [--url URL]… [--laeufe N] [--schreiben] [--json] [--streng]');
      process.exit(0);
    } else throw new Error(`Unbekanntes Argument: ${a}`);
  }
  if (!Number.isInteger(opt.laeufe) || opt.laeufe < 1 || opt.laeufe > 5) {
    throw new Error('--laeufe muss eine ganze Zahl von 1 bis 5 sein');
  }
  return opt;
}

export function zieleAusDatei() {
  const roh = JSON.parse(readFileSync(ZIELE_DATEI, 'utf8'));
  return (roh.ziele || []).map((z) => z.pfad);
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
export function ladeAssertions() {
  const { assertions } = JSON.parse(readFileSync(ASSERTIONS, 'utf8'));
  return assertions || {};
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
  const befunde = [];
  for (const [schluessel, [stufe, grenze]] of Object.entries(assertions)) {
    const werte = laeufe.map((lhr) => messwert(lhr, schluessel)).filter(Boolean);
    if (!werte.length) {
      befunde.push({ schluessel, urteil: 'NICHT_GEMESSEN', stufe,
        text: `${schluessel}: vom Lauf nicht geliefert` });
      continue;
    }
    const methode = grenze?.aggregationMethod || 'median';
    const wert = mittelwerte(werte.map((w) => w.wert), methode);
    if (typeof grenze?.minScore === 'number' && wert < grenze.minScore) {
      befunde.push({ schluessel, urteil: 'UNTER_SCHWELLE', stufe,
        text: `${schluessel}: ${wert.toFixed(2)} < ${grenze.minScore} (minScore, ${methode})` });
    }
    if (typeof grenze?.maxNumericValue === 'number' && wert > grenze.maxNumericValue) {
      befunde.push({ schluessel, urteil: 'UEBER_SCHWELLE', stufe,
        text: `${schluessel}: ${Math.round(wert)} > ${grenze.maxNumericValue} (${werte[0].einheit || 'ms'}, ${methode})` });
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

async function messeUrl(url, port, laeufe) {
  const ergebnisse = [];
  for (let i = 0; i < laeufe; i += 1) {
    const antwort = await lighthouse(url, {
      port,
      output: 'json',
      logLevel: 'error',
      formFactor: 'mobile',
      screenEmulation: { mobile: true, width: 390, height: 844, deviceScaleFactor: 3, disabled: false },
    });
    if (!antwort?.lhr) throw new Error(`${url}: Lighthouse lieferte kein Ergebnis`);
    ergebnisse.push(antwort.lhr);
  }
  return ergebnisse;
}

function zeile(pfad, seite, befunde) {
  const s = seite.scores;
  const wert = (n) => (n === null ? '–' : n);
  const zustand = befunde.length ? `${befunde.length} Befund(e)` : 'im Rahmen';
  return `| \`${pfad}\` | ${zustand} | ${wert(s.performance)} | ${wert(s.accessibility)} | ${wert(s['best-practices'])} | ${wert(s.seo)} |`;
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
  for (const s of seiten) zeilen.push(zeile(s.pfad, s, s.befunde));
  const offen = seiten.flatMap((s) => s.befunde.map((b) => `\`${s.pfad}\` – ${b.text}`));
  if (offen.length) {
    zeilen.push('', '## Gerissene Schwellen', '');
    for (const o of offen) zeilen.push(`- ${o}`);
  }
  return `${zeilen.join('\n')}\n`;
}

export async function main() {
  let opt;
  try {
    opt = argumente(process.argv.slice(2));
  } catch (fehler) {
    console.error(`🛑 ${fehler.message}`);
    process.exit(2);
  }

  let pfade = opt.urls;
  if (!pfade.length) {
    try {
      pfade = zieleAusDatei();
    } catch (fehler) {
      console.error(`🛑 Zielliste nicht lesbar (${ZIELE_DATEI}): ${fehler.message}`);
      process.exit(2);
    }
  }
  pfade = pfade.map((p) => (p.startsWith('http') ? p : opt.basis.replace(/\/$/, '') + '/' + p.replace(/^\//, '')));

  let assertions;
  try {
    assertions = ladeAssertions();
  } catch (fehler) {
    console.error(`🛑 Schwellen nicht lesbar (${ASSERTIONS}): ${fehler.message}`);
    console.error('   Erzeugen: python3 scripts/design_variant_gate.py --lighthouse-export');
    process.exit(2);
  }

  const port = await freierPort();
  const start = await resolveLaunchOptions();
  let browser;
  try {
    browser = await chromium.launch({
      headless: true,
      ...start,
      args: [...(start.args || []), `--remote-debugging-port=${port}`],
    });
  } catch (fehler) {
    console.error(`🛑 Chromium startet nicht: ${fehler.message}`);
    console.error('   Zuerst: npm ci && npm run browser:setup');
    process.exit(2);
  }

  const seiten = [];
  try {
    for (const url of pfade) {
      const laeufe = await messeUrl(url, port, opt.laeufe);
      const befunde = pruefeAssertions(laeufe, assertions);
      // Anzeigename: Produktionsdomain abschneiden, lokale Läufe auf den Pfad
      // bringen. Der Bericht soll dieselbe Zeile zeigen, egal wo gemessen wurde.
      const basis = opt.basis.replace(/\/$/, '');
      const pfad = url.startsWith(basis) ? url.slice(basis.length) || '/'
        : new URL(url).pathname + new URL(url).search;
      seiten.push({ pfad, url, scores: laborScores(laeufe[laeufe.length - 1]), befunde });
      const marke = befunde.length ? '⚠️' : '✅';
      console.log(`${marke} ${pfad} ${JSON.stringify(laborScores(laeufe[laeufe.length - 1]))}`);
      for (const b of befunde) console.log(`   · ${b.text}`);
    }
  } catch (fehler) {
    console.error(`🛑 Messung gescheitert: ${fehler.message}`);
    process.exit(2);
  } finally {
    await browser.close().catch(() => {});
  }

  const datum = new Date().toISOString().slice(0, 10);
  const text = bericht(seiten, datum);

  if (opt.schreiben) {
    mkdirSync(path.dirname(AUSGABE_JSON), { recursive: true });
    writeFileSync(AUSGABE_JSON, `${JSON.stringify({ datum, laeufe: opt.laeufe, seiten }, null, 2)}\n`, 'utf8');
    writeFileSync(AUSGABE_MD, text, 'utf8');
  }
  if (opt.json) {
    console.log(JSON.stringify({ datum, laeufe: opt.laeufe, seiten }, null, 2));
  } else if (!process.stdout.isTTY || opt.schreiben) {
    console.log(`\n${text}`);
  }

  const gesamt = seiten.reduce((summe, s) => summe + s.befunde.length, 0);
  if (gesamt && opt.streng) return 1;
  return 0;
}

// Direkt aufgerufen misst das Skript und setzt den Exit-Code. Importiert
// (Tests) passiert nichts – eine Messung, die beim Import startet, wäre
// nicht prüfbar.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  process.exit(await main());
}
