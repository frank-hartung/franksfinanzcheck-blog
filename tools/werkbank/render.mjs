#!/usr/bin/env node
// ============================================================
//  WERKBANK-BRÜCKE – Browser-Beweis mit Playwright
//  ------------------------------------------------------------
//  Rollout 03.10.2026. Teil der Werkbank (data/werkbank.yaml, Gewerk
//  `browser`). Runbook: docs/ANLEITUNG-WERKBANK.md
//
//  WOZU DAS GUT IST
//  Eine Such-API liefert einen Schnipsel und behauptet, die Seite
//  trage die Aussage. Diese Brücke rendert die Seite wirklich – mit
//  demselben Chromium, mit dem auch die E2E-Suite läuft – und meldet
//  nüchtern: Statuscode, Titel, Textlänge, Konsolenfehler und ob die
//  gesuchten Begriffe im sichtbaren Text tatsächlich vorkommen.
//  Genau das kann Perplexity nicht: Es zeigt Quellen, aber niemand
//  prüft, ob die Quelle die Behauptung deckt.
//
//  BROWSER-AUFFINDUNG: über e2e/browser.mjs – offizieller
//  Playwright-Chromium, sonst @sparticuz/chromium (CDN-Sperren).
//
//  AUSGABE: JSON auf stdout, Diagnose auf stderr. Exit 0 = Beweis
//  erbracht, Exit 2 = kein Browser/kein Beweis.
//
//  AUFRUF:
//    node tools/werkbank/render.mjs --url https://example.org \
//         --suche "Strompreis" --suche "2026" --timeout 20000
// ============================================================

import { chromium } from 'playwright-core';
import { resolveLaunchOptions } from '../../e2e/browser.mjs';

// ------------------------------------------------------------ Argumente
function parseArgs(argv) {
  const out = { url: '', suche: [], timeout: 20000, viewport: { width: 1280, height: 900 } };
  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    const wert = argv[i + 1];
    if (flag === '--url') { out.url = wert; i += 1; }
    else if (flag === '--suche') { if (wert) out.suche.push(wert); i += 1; }
    else if (flag === '--timeout') { out.timeout = Number(wert) || 20000; i += 1; }
  }
  return out;
}

const args = parseArgs(process.argv.slice(2));

if (!args.url || !/^https?:\/\//.test(args.url)) {
  process.stderr.write('Fehlt: --url <http(s)-Adresse>\n');
  process.exit(2);
}

// ------------------------------------------------------------ Beweis
let browser;
try {
  const launchOptions = await resolveLaunchOptions();
  browser = await chromium.launch({ headless: true, ...launchOptions });
} catch (e) {
  process.stderr.write(`Kein startbarer Chromium: ${e.message}\n`);
  process.exit(2);
}

const konsolenfehler = [];
let status = 0;
let geladen = false;

try {
  const context = await browser.newContext({
    viewport: args.viewport,
    locale: 'de-DE',
    // Ehrlich sein: Wir geben uns als das aus, was wir sind.
    userAgent:
      'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
      'Chrome/126.0.0.0 Safari/537.36 franksfinanzcheck-werkbank/1.0',
  });
  const page = await context.newPage();

  page.on('console', (msg) => {
    if (msg.type() === 'error') konsolenfehler.push(msg.text().slice(0, 200));
  });
  page.on('pageerror', (err) => konsolenfehler.push(String(err.message).slice(0, 200)));

  const antwort = await page.goto(args.url, {
    waitUntil: 'domcontentloaded',
    timeout: args.timeout,
  });
  status = antwort ? antwort.status() : 0;
  geladen = true;

  // Netzwerk kurz zur Ruhe kommen lassen – aber nie daran scheitern.
  await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

  const titel = (await page.title()).trim();
  const text = await page.evaluate(() => {
    // Nur sichtbarer Fließtext, kein Navigations- und Fußzeilenrauschen.
    document.querySelectorAll('script,style,noscript,nav,footer,aside').forEach((n) => n.remove());
    return (document.body?.innerText || '').replace(/\s+/g, ' ').trim();
  });

  const kleintext = text.toLowerCase();
  const treffer = args.suche.map((begriff) => ({
    begriff,
    gefunden: kleintext.includes(begriff.toLowerCase()),
  }));

  // Ein Beleg trägt nur, wenn mindestens ein gesuchter Begriff vorkommt.
  const belegt = treffer.length === 0 ? null : treffer.some((t) => t.gefunden);

  process.stdout.write(
    `${JSON.stringify(
      {
        url: args.url,
        endstand_url: page.url(),
        status,
        titel,
        text_laenge: text.length,
        auszug: text.slice(0, 600),
        treffer,
        belegt,
        konsolenfehler: konsolenfehler.slice(0, 5),
        gemessen_am: new Date().toISOString(),
      },
      null,
      0,
    )}\n`,
  );
} catch (e) {
  process.stderr.write(`Beweis gescheitert (${geladen ? 'nach' : 'vor'} Laden): ${e.message}\n`);
  process.exitCode = 2;
} finally {
  await browser.close().catch(() => {});
}
