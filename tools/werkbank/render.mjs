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
//  SSRF-/LFI-SCHUTZ (Tiefencheck 30.10.2026)
//  Chromium führt JavaScript der Zielseite aus. Ohne Request-Filter
//  könnte eine fremde Seite per Redirect oder fetch()/img lokale
//  Dienste (n8n :5678, Whisper :8765, Bridge :5680) oder Cloud-Metadaten
//  (169.254.169.254) abtasten. Jede Anfrage wird vor dem Versand auf
//  http(s) sowie öffentliche Zieladressen geprüft.
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
//    node tools/werkbank/render.mjs --selftest
// ============================================================

import dns from 'node:dns/promises';
import net from 'node:net';

const VERBOTENE_HOSTS = new Set([
  'localhost',
  'ip6-localhost',
  'ip6-loopback',
  'metadata.google.internal',
  'metadata',
  'instance-data',
]);

export function istPrivateOderLokaleIp(rohIp) {
  let ip = String(rohIp || '').trim().toLowerCase();
  if (ip.startsWith('[') && ip.endsWith(']')) ip = ip.slice(1, -1);
  const prozent = ip.indexOf('%');
  if (prozent !== -1) ip = ip.slice(0, prozent);

  if (ip.startsWith('::ffff:')) {
    const rest = ip.slice('::ffff:'.length);
    if (net.isIPv4(rest)) {
      ip = rest;
    } else {
      const hexMatch = /^([0-9a-f]{1,4}):([0-9a-f]{1,4})$/.exec(rest);
      if (hexMatch) {
        const hi = parseInt(hexMatch[1], 16);
        const lo = parseInt(hexMatch[2], 16);
        ip = `${(hi >> 8) & 0xff}.${hi & 0xff}.${(lo >> 8) & 0xff}.${lo & 0xff}`;
      }
    }
  }

  const version = net.isIP(ip);
  if (version === 4) {
    const teile = ip.split('.').map((x) => Number(x));
    const [a, b] = teile;
    if (a === 0 || a === 10 || a === 127) return true;
    if (a === 169 && b === 254) return true; // Link-Local / Cloud-Metadaten
    if (a === 172 && b >= 16 && b <= 31) return true;
    if (a === 192 && b === 168) return true;
    if (a === 100 && b >= 64 && b <= 127) return true; // CGNAT
    if (a >= 224) return true; // Multicast / Reserviert
    return false;
  }
  if (version === 6) {
    if (ip === '::' || ip === '::1') return true;
    if (ip.startsWith('fe8') || ip.startsWith('fe9') || ip.startsWith('fea') || ip.startsWith('feb')) return true;
    if (ip.startsWith('fc') || ip.startsWith('fd')) return true; // ULA
    if (ip.startsWith('ff')) return true; // Multicast
    return false;
  }
  return true;
}

export async function pruefeZielUrl(zielUrl, { aufloesen = true } = {}) {
  let parsed;
  try {
    parsed = new URL(String(zielUrl || '').trim());
  } catch {
    return { ok: false, grund: 'ungueltige URL' };
  }
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    return { ok: false, grund: `Schema ${parsed.protocol} nicht erlaubt` };
  }
  const host = parsed.hostname.toLowerCase().replace(/^\[|\]$/g, '').replace(/\.$/, '');
  if (!host) return { ok: false, grund: 'leerer Hostname' };
  if (VERBOTENE_HOSTS.has(host) || host.endsWith('.localhost') || host.endsWith('.internal')) {
    return { ok: false, grund: `lokaler/interner Host gesperrt (${host})` };
  }
  if (net.isIP(host)) {
    if (istPrivateOderLokaleIp(host)) {
      return { ok: false, grund: `private/lokale IP gesperrt (${host})` };
    }
    return { ok: true, grund: 'ok' };
  }
  if (aufloesen) {
    try {
      const adressen = await dns.lookup(host, { all: true });
      if (!adressen.length) return { ok: false, grund: `keine DNS-Antwort (${host})` };
      for (const eintrag of adressen) {
        if (istPrivateOderLokaleIp(eintrag.address)) {
          return { ok: false, grund: `DNS-Ziel gesperrt (${host} -> ${eintrag.address})` };
        }
      }
    } catch {
      return { ok: false, grund: `DNS-Aufloesung fehlgeschlagen (${host})` };
    }
  }
  return { ok: true, grund: 'ok' };
}

async function runSelftest() {
  const sperrZiele = [
    'file:///etc/passwd',
    'javascript:alert(1)',
    'http://127.0.0.1:8765/health',
    'http://[::1]:5678/',
    'http://[::ffff:127.0.0.1]:5680/',
    'http://localhost:5678/',
    'http://169.254.169.254/latest/meta-data/',
    'http://metadata.google.internal/computeMetadata/v1/',
    'http://10.0.0.1/',
    'http://172.16.12.1/',
    'http://192.168.1.1/',
    'http://100.64.0.1/',
    'http://0.0.0.0:8080/',
  ];
  for (const ziel of sperrZiele) {
    const res = await pruefeZielUrl(ziel, { aufloesen: false });
    if (res.ok) {
      process.stderr.write(`❌ render.mjs-Selbsttest: unsicheres Ziel nicht gesperrt: ${ziel}\n`);
      process.exit(2);
    }
  }
  const okRes = await pruefeZielUrl('https://93.184.216.34/artikel', { aufloesen: false });
  if (!okRes.ok) {
    process.stderr.write(`❌ render.mjs-Selbsttest: oeffentliche IP faelschlich gesperrt (${okRes.grund})\n`);
    process.exit(2);
  }
  process.stdout.write('✅ render.mjs-Selbsttest: 14 SSRF-/Schema-Proben grün.\n');
}

// ------------------------------------------------------------ Argumente
function parseArgs(argv) {
  const out = {
    url: '',
    suche: [],
    timeout: 20000,
    selftest: false,
    viewport: { width: 1280, height: 900 },
  };
  for (let i = 0; i < argv.length; i += 1) {
    const flag = argv[i];
    const wert = argv[i + 1];
    if (flag === '--selftest') { out.selftest = true; }
    else if (flag === '--url') { out.url = wert; i += 1; }
    else if (flag === '--suche') { if (wert) out.suche.push(wert); i += 1; }
    else if (flag === '--timeout') { out.timeout = Number(wert) || 20000; i += 1; }
  }
  return out;
}

const args = parseArgs(process.argv.slice(2));
if (args.selftest) {
  await runSelftest();
  process.exit(0);
}

if (!args.url || !/^https?:\/\//.test(args.url)) {
  process.stderr.write('Fehlt: --url <http(s)-Adresse>\n');
  process.exit(2);
}

const vorabPruefung = await pruefeZielUrl(args.url, { aufloesen: true });
if (!vorabPruefung.ok) {
  process.stderr.write(`Ziel abgelehnt (SSRF-Schutz): ${vorabPruefung.grund}\n`);
  process.exit(2);
}

// ------------------------------------------------------------ Beweis
let browser;
try {
  const [{ chromium }, { resolveLaunchOptions }] = await Promise.all([
    import('playwright-core'),
    import('../../e2e/browser.mjs'),
  ]);
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
  await context.route('**/*', async (route) => {
    const ziel = route.request().url();
    const urteil = await pruefeZielUrl(ziel, { aufloesen: true });
    if (!urteil.ok) {
      await route.abort('accessdenied');
      return;
    }
    await route.continue();
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
