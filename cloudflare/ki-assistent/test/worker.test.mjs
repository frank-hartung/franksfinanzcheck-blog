/**
 * CORS-Vertrag des KI-Assistent-Workers (node --test, ohne Cloudflare-Login).
 *
 * WARUM DIESE DATEI EXISTIERT (Code-Scanning-Alert #83, 10.10.2026)
 * Die Freigabe fremder Herkünfte lief über `origin.endsWith(".pages.dev")` –
 * eine Prüfung auf der Zeichenkette statt auf dem Host (CodeQL-Regelklasse
 * `js/incomplete-url-substring-sanitization`). Diese Tests frieren die
 * host-genaue Entscheidung ein: Jede Zeile hier ist eine Umgehung, die vorher
 * funktioniert hätte oder künftig wieder funktionieren würde.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  corsHeaders, vorschauHost, erlaubteHerkunft, proxyBaseUrl, turnstilePruefen, handle, HINWEIS,
} from '../worker.js';

const ENV = { ALLOWED_ORIGIN: 'https://franksfinanzcheck.de' };
const erlaubt = (origin, env = ENV) =>
  corsHeaders(origin, env)['Access-Control-Allow-Origin'] === origin;

test('eigene Produktions-Herkunft wird exakt freigegeben', () => {
  assert.equal(erlaubt('https://franksfinanzcheck.de'), true);
  assert.equal(
    corsHeaders('https://franksfinanzcheck.de', ENV)['Access-Control-Allow-Origin'],
    'https://franksfinanzcheck.de',
  );
});

test('Vary: Origin bleibt gesetzt (Cache darf Herkünfte nicht mischen)', () => {
  assert.equal(corsHeaders('https://franksfinanzcheck.de', ENV).Vary, 'Origin');
});

test('M-04: fremde Vorschau-Subdomains sind NICHT mehr erlaubt (jeder kann sie anlegen)', () => {
  assert.equal(erlaubt('https://vorschau.pages.dev'), false);
  assert.equal(erlaubt('https://3000-abc123.e2b.app'), false);
});

test('M-04: nur das eigene, konfigurierte Vorschau-Projekt ist erlaubt', () => {
  const env = { ...ENV, VORSCHAU_HOSTS: 'franksfinanzcheck.pages.dev' };
  assert.equal(erlaubt('https://franksfinanzcheck.pages.dev', env), true);
  assert.equal(erlaubt('https://a1b2c3.franksfinanzcheck.pages.dev', env), true);
  assert.equal(erlaubt('https://boese.pages.dev', env), false);
  assert.equal(erlaubt('https://franksfinanzcheck.pages.dev.angreifer.example', env), false);
  assert.equal(erlaubt('https://xfranksfinanzcheck.pages.dev', env), false);
  assert.equal(erlaubt('https://franksfinanzcheck.pages.dev:8443', env), false);
});

test('Zeichenketten-Umgehungen der Vorschau-Regel sind zu', () => {
  const ENV_V = { ...ENV, VORSCHAU_HOSTS: 'vorschau.pages.dev' };
  const erlaubt = (origin) => corsHeaders(origin, ENV_V)['Access-Control-Allow-Origin'] === origin;
  // „endet auf .pages.dev" – aber als Pfad/Query, nicht als Host
  assert.equal(erlaubt('https://angreifer.example/?x=.pages.dev'), false);
  assert.equal(erlaubt('https://angreifer.example/a.pages.dev'), false);
  // Host klebt am Vorschau-Namen, ist aber ein anderer
  assert.equal(erlaubt('https://boesepages.dev'), false);
  assert.equal(erlaubt('https://pages.dev.angreifer.example'), false);
  // Benutzerteil täuscht den Host vor
  assert.equal(erlaubt('https://vorschau.pages.dev@angreifer.example'), false);
  // unverschlüsselt ist keine Vorschau
  assert.equal(erlaubt('http://vorschau.pages.dev'), false);
});

test('fremde und leere Herkünfte bekommen die eigene Domain zurück', () => {
  for (const origin of ['https://angreifer.example', '', 'null', 'kein-origin']) {
    assert.equal(erlaubt(origin), false);
    assert.equal(
      corsHeaders(origin, ENV)['Access-Control-Allow-Origin'],
      'https://franksfinanzcheck.de',
      `Rückfall-Origin falsch für ${origin || '(leer)'}`,
    );
  }
});

test('ALLOWED_ORIGIN darf mehrere Herkünfte führen – exakt verglichen', () => {
  const env = { ALLOWED_ORIGIN: 'https://franksfinanzcheck.de, https://www.franksfinanzcheck.de' };
  assert.equal(erlaubt('https://www.franksfinanzcheck.de', env), true);
  assert.equal(erlaubt('https://franksfinanzcheck.de.angreifer.example', env), false);
});

test('vorschauHost urteilt über den Host, nicht über die Zeichenkette', () => {
  const env = { VORSCHAU_HOSTS: 'b.pages.dev' };
  assert.equal(vorschauHost('https://a.b.pages.dev', env), true);
  assert.equal(vorschauHost('https://pages.dev', env), false); // Apex ist keine Vorschau
  assert.equal(vorschauHost('https://a.b.pages.dev'), false); // ohne Konfiguration: nichts
  assert.equal(vorschauHost('nonsense', env), false);
  assert.equal(vorschauHost(undefined, env), false);
});

// ---- Sicherheitsaudit 14.10.2026, M-04: Handler-Vertrag ----

const BASIS_ENV = {
  ALLOWED_ORIGIN: 'https://franksfinanzcheck.de',
  TURNSTILE_SECRET: 'ts-geheim',
  LLM_PROXY_BASE_URL: 'https://llm.franksfinanzcheck.de',
  LLM_PROXY_HOSTS: 'llm.franksfinanzcheck.de',
  LLM_PROXY_TOKEN: 'proxy-token',
  GROQ_API_KEY: 'gsk_GEHEIM_DARF_NIE_RAUS',
  RATE_LIMIT_RPM: '1000',
};

function frage(body, kopf = {}) {
  return new Request('https://ki.franksfinanzcheck.de/chat', {
    method: 'POST',
    headers: { Origin: 'https://franksfinanzcheck.de', 'Content-Type': 'application/json', ...kopf },
    body: typeof body === 'string' ? body : JSON.stringify(body),
  });
}

function netz({ turnstile = true, antwort = 'Kurze Antwort.' } = {}) {
  const aufrufe = [];
  const holen = async (url, init = {}) => {
    aufrufe.push({ url: String(url), init });
    if (String(url).startsWith('https://challenges.cloudflare.com/')) {
      return new Response(JSON.stringify({ success: turnstile }), { status: 200 });
    }
    return new Response(JSON.stringify({ choices: [{ message: { content: antwort } }] }), { status: 200 });
  };
  return { holen, aufrufe };
}

const GUT = { question: 'Wie kündige ich meinen Stromvertrag?', turnstileToken: 'x'.repeat(40) };

test('M-04: ohne erlaubten Origin → 403 und KEIN Modellaufruf (curl-Schutz)', async () => {
  for (const kopf of [{ Origin: 'https://angreifer.example' }, { Origin: '' }, { Origin: 'https://vorschau.pages.dev' }]) {
    const n = netz();
    const r = await handle(frage(GUT, kopf), BASIS_ENV, n.holen);
    assert.equal(r.status, 403, JSON.stringify(kopf));
    assert.equal(n.aufrufe.length, 0);
  }
});

test('M-04: ohne TURNSTILE_SECRET bleibt der Assistent aus (503, fail closed)', async () => {
  const n = netz();
  const { TURNSTILE_SECRET, ...ohne } = BASIS_ENV;
  const r = await handle(frage(GUT), ohne, n.holen);
  assert.equal(r.status, 503);
  assert.equal(n.aufrufe.length, 0);
});

test('M-04: fehlendes oder ungültiges Turnstile-Token → 403, kein Modellaufruf', async () => {
  const ohneToken = netz();
  assert.equal((await handle(frage({ question: GUT.question }), BASIS_ENV, ohneToken.holen)).status, 403);
  assert.equal(ohneToken.aufrufe.length, 0);
  const falsch = netz({ turnstile: false });
  assert.equal((await handle(frage(GUT), BASIS_ENV, falsch.holen)).status, 403);
  assert.equal(falsch.aufrufe.filter((a) => a.url.startsWith('https://llm.')).length, 0);
});

test('M-04: Provider-Schlüssel verlassen den Worker nie – Proxy bekommt nur das eigene Token', async () => {
  const n = netz();
  const r = await handle(frage(GUT), BASIS_ENV, n.holen);
  assert.equal(r.status, 200);
  const proxy = n.aufrufe.filter((a) => a.url.startsWith('https://llm.franksfinanzcheck.de/'));
  assert.ok(proxy.length >= 1);
  for (const a of proxy) {
    assert.equal(a.init.headers.Authorization, 'Bearer proxy-token');
    assert.ok(!String(a.init.body).match(/gsk_GEHEIM|apiKey/), 'Schlüssel im Body');
    assert.equal(a.init.redirect, 'error');
  }
  const daten = await r.json();
  assert.equal(daten.hinweis, HINWEIS);
  assert.match(daten.hinweis, /keine Anlage-/);
  assert.equal(daten.ki, true);
});

test('M-04: Proxy nur mit https und exakt freigegebenem Host', () => {
  const env = { LLM_PROXY_HOSTS: 'llm.franksfinanzcheck.de' };
  assert.equal(proxyBaseUrl({ ...env, LLM_PROXY_BASE_URL: 'https://llm.franksfinanzcheck.de/' }), 'https://llm.franksfinanzcheck.de');
  assert.equal(proxyBaseUrl({ ...env, LLM_PROXY_BASE_URL: 'http://llm.franksfinanzcheck.de' }), null);
  assert.equal(proxyBaseUrl({ ...env, LLM_PROXY_BASE_URL: 'https://llm.franksfinanzcheck.de.angreifer.example' }), null);
  assert.equal(proxyBaseUrl({ ...env, LLM_PROXY_BASE_URL: 'https://user:pw@llm.franksfinanzcheck.de' }), null);
  assert.equal(proxyBaseUrl({ LLM_PROXY_BASE_URL: 'https://llm.franksfinanzcheck.de' }), null, 'ohne Freigabeliste nichts');
  assert.equal(proxyBaseUrl({ ...env, LLM_PROXY_BASE_URL: 'kein url' }), null);
});

test('M-04: Rate-Limit-Binding greift über alle Isolates (429 ohne Modellaufruf)', async () => {
  const n = netz();
  const env = { ...BASIS_ENV, KI_LIMITER: { async limit() { return { success: false }; } } };
  const r = await handle(frage(GUT, { 'CF-Connecting-IP': '198.51.100.9' }), env, n.holen);
  assert.equal(r.status, 429);
  assert.equal(n.aufrufe.length, 0);
});

test('M-04: Eingaben werden geprüft (Typ, Länge, Größe) – keine 500er', async () => {
  const n = netz();
  assert.equal((await handle(frage({ question: 42, turnstileToken: GUT.turnstileToken }), BASIS_ENV, n.holen)).status, 400);
  assert.equal((await handle(frage('null'), BASIS_ENV, n.holen)).status, 400);
  assert.equal((await handle(frage('{kaputt'), BASIS_ENV, n.holen)).status, 400);
  assert.equal((await handle(frage({ question: 'x'.repeat(2001), turnstileToken: GUT.turnstileToken }), BASIS_ENV, n.holen)).status, 400);
  assert.equal((await handle(frage({ question: 'y'.repeat(40000) }), BASIS_ENV, n.holen)).status, 413);
  assert.equal(n.aufrufe.length, 0);
});

test('M-04: Turnstile-Prüfung sendet Secret und Token an Cloudflare', async () => {
  const n = netz();
  const erg = await turnstilePruefen('t'.repeat(30), '198.51.100.9', { TURNSTILE_SECRET: 'ts' }, n.holen);
  assert.equal(erg.ok, true);
  assert.equal(n.aufrufe[0].url, 'https://challenges.cloudflare.com/turnstile/v0/siteverify');
  const form = n.aufrufe[0].init.body;
  assert.equal(form.get('secret'), 'ts');
  assert.equal(form.get('response'), 't'.repeat(30));
  assert.equal((await turnstilePruefen('t'.repeat(30), '', {}, n.holen)).ok, false);
});

test('M-04: erlaubteHerkunft ist exakt (kein Präfix/Suffix)', () => {
  assert.equal(erlaubteHerkunft('https://franksfinanzcheck.de', ENV), true);
  assert.equal(erlaubteHerkunft('https://franksfinanzcheck.de/', ENV), false);
  assert.equal(erlaubteHerkunft('http://franksfinanzcheck.de', ENV), false);
});
