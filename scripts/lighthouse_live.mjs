#!/usr/bin/env node
// ============================================================
//  LIGHTHOUSE LIVE – Laborwerte der AUSGELIEFERTEN Seite
//  ------------------------------------------------------------
//  WARUM ES DIESES SKRIPT GIBT (26.10.2026 · gehärtet 03.11.2026, #1026)
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
//  WARUM DIE LAUFZEIT-PAKETE DYNAMISCH GELADEN WERDEN (#1026, WF-0032)
//  Lauf 41456548199 starb im Schritt „Selbsttests der Messungen (ohne
//  Netz)" mit ERR_MODULE_NOT_FOUND ('lighthouse'), bevor eine einzige
//  Feld- oder Labormessung lief: Statische Top-Level-Imports zwangen
//  Node dazu, `lighthouse` und `playwright-core` schon beim Laden der
//  reinen Auswertungsfunktionen aufzulösen – vor `npm ci`. Der Rechen-
//  und Selbsttest-Kern nutzt deshalb ausschließlich die Node-Standard-
//  bibliothek; Browser und Lighthouse werden erst beim echten Messlauf
//  über `ladeLaufzeit()` geladen.
//
//  Aufruf:
//    node scripts/lighthouse_live.mjs                       # Ziele aus data/cwv/feld_ziele.json
//    node scripts/lighthouse_live.mjs --url https://…/x/    # einzelne URL
//    node scripts/lighthouse_live.mjs --laeufe 3 --schreiben
//    node scripts/lighthouse_live.mjs --json
//    node scripts/lighthouse_live.mjs --streng              # Befund ⇒ Exit 1
//    node scripts/lighthouse_live.mjs --selftest            # ohne Netz, ohne node_modules
//
//  Exit: 0 = gemessen (Befunde stehen im Bericht) bzw. Selbsttest grün
//        1 = Befund, nur mit `--streng`
//        2 = nicht messbar (Chromium, Netz, Konfiguration, Selbsttest rot)
//
//  Browser: derselbe Resolver wie die E2E-Suite (`e2e/browser.mjs`) –
//  gepinntes Chromium aus dem Lockfile, kein zweiter Browserweg.
// ============================================================

import assert from 'node:assert/strict';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HIER = path.dirname(fileURLToPath(import.meta.url));
const WURZEL = path.resolve(HIER, '..');
const ZIELE_DATEI = path.join(WURZEL, 'data', 'cwv', 'feld_ziele.json');
const ASSERTIONS = path.join(WURZEL, 'lighthouse', 'assertions.json');
const AUSGABE_JSON = path.join(WURZEL, 'data', 'cwv', 'labor', 'befund.json');
const AUSGABE_MD = path.join(WURZEL, 'data', 'cwv', 'labor', 'befund.md');
const BASIS = 'https://franksfinanzcheck.de';

const HILFE_TEXT =
  'node scripts/lighthouse_live.mjs [--url URL]… [--basis URL] [--laeufe N] [--schreiben] [--json] [--streng] [--selftest]';

function naechsterWert(argv, index, schalter) {
  const wert = argv[index + 1];
  if (wert === undefined || wert === '' || wert.startsWith('--')) {
    throw new Error(`${schalter} erwartet einen Wert`);
  }
  return wert;
}

function pruefeHttpUrl(wert, kontext) {
  let parsed;
  try {
    parsed = new URL(wert);
  } catch {
    throw new Error(`${kontext}: ungültige URL (${wert})`);
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new Error(`${kontext}: nur http:// oder https:// erlaubt (${wert})`);
  }
  return wert;
}

// ------------------------------------------------------------
//  Argumente (bewusst ohne Framework: ein Skript, keine Kette)
// ------------------------------------------------------------
export function argumente(argv) {
  const opt = {
    urls: [],
    laeufe: 1,
    schreiben: false,
    json: false,
    streng: false,
    selftest: false,
    hilfe: false,
    basis: BASIS,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const a = argv[i];
    if (a === '--url') {
      const ziel = naechsterWert(argv, i, '--url');
      i += 1;
      if (!ziel.startsWith('/')) pruefeHttpUrl(ziel, '--url');
      opt.urls.push(ziel);
    } else if (a === '--basis') {
      opt.basis = pruefeHttpUrl(naechsterWert(argv, i, '--basis'), '--basis');
      i += 1;
    } else if (a === '--laeufe') {
      opt.laeufe = Number(naechsterWert(argv, i, '--laeufe'));
      i += 1;
    } else if (a === '--schreiben') opt.schreiben = true;
    else if (a === '--json') opt.json = true;
    else if (a === '--streng') opt.streng = true;
    else if (a === '--selftest') opt.selftest = true;
    else if (a === '--hilfe' || a === '-h') opt.hilfe = true;
    else throw new Error(`Unbekanntes Argument: ${a}`);
  }
  if (!Number.isInteger(opt.laeufe) || opt.laeufe < 1 || opt.laeufe > 5) {
    throw new Error('--laeufe muss eine ganze Zahl von 1 bis 5 sein');
  }
  return opt;
}

export function baueZielUrl(pfadOderUrl, basis = BASIS) {
  if (pfadOderUrl.startsWith('http://') || pfadOderUrl.startsWith('https://')) {
    return pruefeHttpUrl(pfadOderUrl, '--url');
  }
  return `${pruefeHttpUrl(basis, '--basis').replace(/\/+$/, '')}/${pfadOderUrl.replace(/^\/+/, '')}`;
}

export function zieleAusDatei(pfad = ZIELE_DATEI) {
  const roh = JSON.parse(readFileSync(pfad, 'utf8'));
  const ziele = roh?.ziele;
  if (!Array.isArray(ziele) || ziele.length === 0) {
    throw new Error(`${pfad}: 'ziele' fehlt oder ist leer`);
  }
  return ziele.map((z, idx) => {
    const zielPfad = typeof z?.pfad === 'string' ? z.pfad.trim() : '';
    if (!zielPfad.startsWith('/')) {
      throw new Error(`${pfad}: Ziel #${idx + 1} braucht einen absoluten Pfad mit '/' (${JSON.stringify(z)})`);
    }
    return zielPfad;
  });
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
export function ladeAssertions(pfad = ASSERTIONS) {
  const roh = JSON.parse(readFileSync(pfad, 'utf8'));
  const assertions = roh?.assertions;
  if (!assertions || typeof assertions !== 'object' || Array.isArray(assertions)
      || Object.keys(assertions).length === 0) {
    throw new Error(`${pfad}: 'assertions' fehlt oder ist leer`);
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
  if (!Array.isArray(werte) || werte.length === 0) {
    throw new Error('mittelwerte braucht mindestens einen Messwert');
  }
  const sortiert = [...werte].sort((a, b) => a - b);
  if (methode === 'pessimistic') return sortiert[sortiert.length - 1];
  if (methode === 'optimistic') return sortiert[0];
  const mitte = Math.floor(sortiert.length / 2);
  return sortiert.length % 2 ? sortiert[mitte] : (sortiert[mitte - 1] + sortiert[mitte]) / 2;
}

/** Prüft EINEN Lauf-Satz gegen die Schwellen und nennt jede gerissene Grenze. */
export function pruefeAssertions(laeufe, assertions) {
  if (!assertions || typeof assertions !== 'object' || Object.keys(assertions).length === 0) {
    throw new Error('pruefeAssertions braucht mindestens eine Assertion (kein Scheingrün)');
  }
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
//  Laufzeit (erst beim echten Messlauf geladen – nie im Selbsttest)
// ------------------------------------------------------------
export async function ladeLaufzeit() {
  const [{ default: lighthouse }, { chromium }, { resolveLaunchOptions }] = await Promise.all([
    import('lighthouse'),
    import('playwright-core'),
    import('../e2e/browser.mjs'),
  ]);
  return { lighthouse, chromium, resolveLaunchOptions };
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

export async function messeUrl(url, port, laeufe, lighthouseFn) {
  if (typeof lighthouseFn !== 'function') {
    throw new Error('messeUrl braucht eine Lighthouse-Funktion');
  }
  const ergebnisse = [];
  for (let i = 0; i < laeufe; i += 1) {
    const antwort = await lighthouseFn(url, {
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

// ------------------------------------------------------------
//  Selbsttest (ohne Netz, ohne node_modules, ohne Schreiben ins Repo)
// ------------------------------------------------------------
export async function selftest() {
  const fehler = [];
  const pruefe = async (name, fn) => {
    try {
      await fn();
    } catch (err) {
      fehler.push(`${name}: ${err.message}`);
    }
  };

  // 1. Echte Schwellen-SSOT lesbar und vollständig
  await pruefe('assertions-ssot', () => {
    const a = ladeAssertions();
    assert.ok(Object.keys(a).length >= 6);
    assert.equal(a['largest-contentful-paint'][1].maxNumericValue, 2500);
  });

  // 2. Sabotage: leere Schwellen dürfen nie Scheingrün liefern
  await pruefe('assertions-scheingruen-sperre', () => {
    const tmp = mkdtempSync(path.join(os.tmpdir(), 'lh-live-selftest-'));
    try {
      const leer = path.join(tmp, 'assertions.json');
      writeFileSync(leer, JSON.stringify({ assertions: {} }), 'utf8');
      assert.throws(() => ladeAssertions(leer), /leer/);
      assert.throws(() => pruefeAssertions([], {}), /Scheingrün/);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });

  // 3. Echte Zielliste lesbar + Sabotage gegen leere/relative Ziele
  await pruefe('ziele-ssot-und-sabotage', () => {
    const ziele = zieleAusDatei();
    assert.ok(ziele.length >= 1);
    assert.ok(ziele.every((p) => p.startsWith('/')));
    const tmp = mkdtempSync(path.join(os.tmpdir(), 'lh-ziele-selftest-'));
    try {
      const leer = path.join(tmp, 'leer.json');
      writeFileSync(leer, JSON.stringify({ ziele: [] }), 'utf8');
      assert.throws(() => zieleAusDatei(leer), /leer/);
      const relativ = path.join(tmp, 'relativ.json');
      writeFileSync(relativ, JSON.stringify({ ziele: [{ pfad: 'cockpit/' }] }), 'utf8');
      assert.throws(() => zieleAusDatei(relativ), /absoluten Pfad/);
    } finally {
      rmSync(tmp, { recursive: true, force: true });
    }
  });

  // 4. Messwert-Auflösung inkl. Lighthouse-13-Alias
  await pruefe('messwert-und-alias', () => {
    const lhr = {
      categories: { performance: { score: 0.94 } },
      audits: {
        'largest-contentful-paint': { numericValue: 1950, numericUnit: 'millisecond' },
        'dom-size-insight': { numericValue: 820, numericUnit: 'element' },
      },
    };
    assert.deepEqual(messwert(lhr, 'categories:performance'), { wert: 0.94, einheit: 'score' });
    assert.deepEqual(messwert(lhr, 'largest-contentful-paint'), { wert: 1950, einheit: 'millisecond' });
    assert.deepEqual(messwert(lhr, 'dom-size'), { wert: 820, einheit: 'element' });
    assert.equal(messwert(lhr, 'total-blocking-time'), null);
  });

  // 5. Aggregation (median gerade/ungerade, pessimistic, optimistic)
  await pruefe('aggregation', () => {
    assert.equal(mittelwerte([3000, 1000, 2000], 'median'), 2000);
    assert.equal(mittelwerte([3000, 1000], 'median'), 2000);
    assert.equal(mittelwerte([3000, 1000, 2000], 'pessimistic'), 3000);
    assert.equal(mittelwerte([3000, 1000, 2000], 'optimistic'), 1000);
    assert.throws(() => mittelwerte([], 'median'), /mindestens einen/);
  });

  // 6. Schwellenprüfung: Über-/Unterschreitung und NICHT_GEMESSEN
  await pruefe('schwellenpruefung', () => {
    const lauf = {
      categories: { accessibility: { score: 0.91 } },
      audits: { 'largest-contentful-paint': { numericValue: 3100, numericUnit: 'millisecond' } },
    };
    const befunde = pruefeAssertions([lauf], {
      'categories:accessibility': ['error', { minScore: 0.95 }],
      'largest-contentful-paint': ['error', { maxNumericValue: 2500, aggregationMethod: 'median' }],
      'total-blocking-time': ['error', { maxNumericValue: 200 }],
    });
    assert.deepEqual(befunde.map((b) => b.urteil), [
      'UNTER_SCHWELLE',
      'UEBER_SCHWELLE',
      'NICHT_GEMESSEN',
    ]);
  });

  // 7. Argumente, URL-Bau und Messe-Attrappe
  await pruefe('argumente-url-und-attrappe', async () => {
    assert.equal(baueZielUrl('/cockpit/', 'https://franksfinanzcheck.de/'), 'https://franksfinanzcheck.de/cockpit/');
    assert.throws(() => argumente(['--url']), /erwartet einen Wert/);
    assert.throws(() => argumente(['--url', '--json']), /erwartet einen Wert/);
    assert.throws(() => argumente(['--url', 'file:///etc/passwd']), /http/);
    assert.throws(() => argumente(['--basis', 'ftp://x.de']), /http/);
    assert.equal(argumente(['--selftest']).selftest, true);
    assert.equal(argumente(['--hilfe']).hilfe, true);

    const attrappe = async (_url, cfg) => ({ lhr: { port: cfg.port, categories: { seo: { score: 1 } }, audits: {} } });
    const ergebnisse = await messeUrl('https://x.de/', 9333, 2, attrappe);
    assert.equal(ergebnisse.length, 2);
    assert.equal(laborScores(ergebnisse[0]).seo, 100);
    await assert.rejects(() => messeUrl('https://x.de/', 9333, 1, async () => ({})), /kein Ergebnis/);
  });

  if (fehler.length > 0) {
    console.error('🛑 SELBSTTEST LIGHTHOUSE LIVE FEHLGESCHLAGEN:');
    for (const f of fehler) console.error(`  · ${f}`);
    return 2;
  }
  console.log('✅ Lighthouse Live: Selbsttest grün (SSOT-Schwellen, Scheingrün-Sperre, Alias, Aggregation, Argumente, Attrappe)');
  return 0;
}

export async function main(argv = process.argv.slice(2), laufzeitGeber = ladeLaufzeit) {
  let opt;
  try {
    opt = argumente(argv);
  } catch (fehler) {
    console.error(`🛑 ${fehler.message}`);
    return 2;
  }

  if (opt.hilfe) {
    console.log(HILFE_TEXT);
    return 0;
  }

  if (opt.selftest) {
    return selftest();
  }

  let pfade = opt.urls;
  if (!pfade.length) {
    try {
      pfade = zieleAusDatei();
    } catch (fehler) {
      console.error(`🛑 Zielliste nicht lesbar (${ZIELE_DATEI}): ${fehler.message}`);
      return 2;
    }
  }
  try {
    pfade = pfade.map((p) => baueZielUrl(p, opt.basis));
  } catch (fehler) {
    console.error(`🛑 Ungültige Ziel-URL: ${fehler.message}`);
    return 2;
  }

  let assertions;
  try {
    assertions = ladeAssertions();
  } catch (fehler) {
    console.error(`🛑 Schwellen nicht lesbar (${ASSERTIONS}): ${fehler.message}`);
    console.error('   Erzeugen: python3 scripts/design_variant_gate.py --lighthouse-export');
    return 2;
  }

  let laufzeit;
  try {
    laufzeit = await laufzeitGeber();
  } catch (fehler) {
    console.error(`🛑 Laufzeit-Pakete für Lighthouse fehlen: ${fehler.message}`);
    console.error('   Zuerst: npm ci --ignore-scripts && npm run browser:setup');
    return 2;
  }

  const port = await freierPort();
  const start = await laufzeit.resolveLaunchOptions();
  let browser;
  try {
    browser = await laufzeit.chromium.launch({
      headless: true,
      ...start,
      args: [...(start.args || []), `--remote-debugging-port=${port}`],
    });
  } catch (fehler) {
    console.error(`🛑 Chromium startet nicht: ${fehler.message}`);
    console.error('   Zuerst: npm ci --ignore-scripts && npm run browser:setup');
    return 2;
  }

  const seiten = [];
  try {
    for (const url of pfade) {
      const laeufe = await messeUrl(url, port, opt.laeufe, laufzeit.lighthouse);
      const befunde = pruefeAssertions(laeufe, assertions);
      // Anzeigename: Produktionsdomain abschneiden, lokale Läufe auf den Pfad
      // bringen. Der Bericht soll dieselbe Zeile zeigen, egal wo gemessen wurde.
      const basis = opt.basis.replace(/\/+$/, '');
      const pfad = url.startsWith(basis) ? url.slice(basis.length) || '/'
        : new URL(url).pathname + new URL(url).search;
      seiten.push({ pfad, url, scores: laborScores(laeufe[laeufe.length - 1]), befunde });
      const marke = befunde.length ? '⚠️' : '✅';
      const fortschritt = opt.json ? console.error : console.log;
      fortschritt(`${marke} ${pfad} ${JSON.stringify(laborScores(laeufe[laeufe.length - 1]))}`);
      for (const b of befunde) fortschritt(`   · ${b.text}`);
    }
  } catch (fehler) {
    console.error(`🛑 Messung gescheitert: ${fehler.message}`);
    return 2;
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
