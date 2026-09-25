/**
 * Tests für den ff-newsletter-Worker (node --test, ohne Cloudflare-Login).
 *
 * Der Worker wird direkt mit einem mocked `env` (KV + Config) gefüttert;
 * `fetch` (nur für den GitHub-Dispatch) wird ausgetauscht. Geprüft wird
 * das, was den Newsletter lebt hält:
 *   – Anmeldung: Validierung, Consent, Bot-Falle, Dedup, Rate-Limit,
 *     Themen-Filterung, Nachweis-TTL, Dispatch NUR mit Token (keine Adresse)
 *   – Double-Opt-In: Bestätigung, Idempotenz, Ablauf, unbekannte Tokens
 *   – Abmeldung: POST + GET (One-Klick), Idempotenz, offene Anmeldung
 *   – Journey-Seiten (GET /bestaetigung, /praferenzen): servergerendert,
 *     Token im HTML, Formular ohne JavaScript
 *   – Export: Secret-Pflicht (403), aktive List, Pending-List, Token-Lookup,
 *     Versuchszählung (3× gesendet → abgelaufen), Bounce → Unterdrückung
 *   – Taktgeber (scheduled): Cron → richtiger Workflow + richtige Inputs
 *     (planmaessig, nie live/test), Retry bei 5xx, kein Retry bei 401/403,
 *     unbekannter Cron dispatcht nichts, Protokoll im KV, healthz zeigt es,
 *     wrangler.toml und TAKT decken sich (Wochentags-Falle TUE,FRI)
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { TAKT, takt_ausfuehren, takt_fuer } from '../src/index.js';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const EXPORT_KEY = 'export-key-32-z------------';

function kvLeeren() {
  const daten = new Map();
  return {
    map: daten,
    async get(schluessel, typ) {
      const roh = daten.get(schluessel);
      if (roh === undefined) return null;
      return typ === 'json' ? JSON.parse(roh) : roh;
    },
    async put(schluessel, wert) {
      daten.set(schluessel, typeof wert === 'string' ? wert : JSON.stringify(wert));
    },
    async delete(schluessel) {
      daten.delete(schluessel);
    },
    async list({ prefix = '' } = {}) {
      const keys = [...daten.keys()].filter((k) => k.startsWith(prefix)).sort();
      return { keys: keys.map((name) => ({ name })), list_complete: true, cursor: undefined };
    },
  };
}

function env_mit(kv, extra = {}) {
  return {
    ABO: kv,
    SITE_ORIGIN: 'https://franksfinanzcheck.de',
    GITHUB_REPO: 'frank-hartung/franksfinanzcheck-blog',
    GITHUB_PAT: 'test-pat',
    GITHUB_WORKFLOW: 'newsletter-lifecycle.yml',
    GITHUB_REF: 'main',
    THEMEN_IDS: 'strom-sparen,internet-dsl,versicherungen,konto-karten,frugalismus,mietwagen',
    BESTAETIGUNG_TAGE: '14',
    EXPORT_KEY,
    ...extra,
  };
}

let dispatche = [];
function fetch_sperr(einstellen = () => new Response(null, { status: 204 })) {
  const zuvor = globalThis.fetch;
  globalThis.fetch = async (ziel, opt) => {
    dispatche.push({ ziel: String(ziel), opt });
    return einstellen(ziel, opt);
  };
  return () => { globalThis.fetch = zuvor; };
}

function form_request(pfad, daten, { akzept = 'application/json', ip = '1.2.3.4', quelle = '' } = {}) {
  const korper = new URLSearchParams();
  for (const [k, v] of Object.entries(daten || {})) {
    if (Array.isArray(v)) v.forEach((x) => korper.append(k, x));
    else korper.append(k, v);
  }
  const ziel = `http://abos.test${pfad}${quelle ? `?${quelle}` : ''}`;
  return new Request(ziel, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
      accept: akzept,
      'cf-connecting-ip': ip,
      'user-agent': 'TestAgent/0 (test)',
    },
    body: korper.toString(),
  });
}

function anmelden(kv, daten, extra = {}) {
  const freilass = fetch_sperr();
  return worker.fetch(form_request('/anmeldung', daten, extra), env_mit(kv, extra.env || {}))
    .then((antwort) => {
      freilass();
      return antwort;
    });
}

// ------------------------------------------------------------------ health
test('healthz: KV erreichbar -> ok', async () => {
  const kv = kvLeeren();
  const antwort = await worker.fetch(new Request('http://abos.test/healthz'), env_mit(kv));
  assert.equal(antwort.status, 200);
  const daten = await antwort.json();
  assert.equal(daten.ok, true);
});

// ------------------------------------------------------------------ anmeldung
test('anmeldung: neuer Absender -> pending + Token + Nachweis + Dispatch (nur Token)', async () => {
  const kv = kvLeeren();
  const antwort = await anmelden(kv, {
    email: 'Leser@Beispiel.DE', consent: '1', themen: ['strom-sparen', 'internet-dsl'],
  });
  assert.equal(antwort.status, 200);
  const daten = await antwort.json();
  assert.equal(daten.status, 'angemeldet');

  const eintrag = await kv.get('abo:leser@beispiel.de', 'json');
  assert.equal(eintrag.status, 'pending');
  assert.equal(eintrag.themen.length, 2);
  assert.match(eintrag.token, /^[A-Za-z0-9_-]{32}$/);
  assert.ok(eintrag.seit && eintrag.ip && eintrag.user_agent);

  // Token-Rueckweg und Nachweis (TTL 3 Jahre)
  assert.equal(await kv.get(`token:${eintrag.token}`), 'leser@beispiel.de');
  const nachweise = [...kv.map.keys()].filter((k) => k.startsWith('nachweis:'));
  assert.equal(nachweise.length, 1);
  const nachweis = JSON.parse(kv.map.get(nachweise[0]));
  assert.equal(nachweis.email, 'leser@beispiel.de');
  assert.equal(nachweis.ip, '1.2.3.4');
  assert.equal(nachweis.version, 1);

  // Dispatch: genau ein Aufruf, Ziel = Actions-Workflow, Body NUR mit Token
  assert.equal(dispatche.length, 1);
  assert.match(dispatche[0].ziel, /api\.github\.com\/repos\/frank-hartung\/franksfinanzcheck-blog\/actions\/workflows\/newsletter-lifecycle\.yml\/dispatches$/);
  const body = JSON.parse(dispatche[0].opt.body);
  assert.equal(body.ref, 'main');
  assert.equal(body.inputs.aktion, 'bestaetigung');
  assert.equal(body.inputs.token, eintrag.token);
  assert.ok(!JSON.stringify(body).includes('@beispiel.de'), 'keine Adresse im Dispatch-Body');
});

test('anmeldung: Themen ausserhalb der erlaubten IDs werden gefiltert', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'x@beispiel.de', consent: '1', themen: ['strom-sparen', 'geheim-thema', 'mietwagen'] });
  const eintrag = await kv.get('abo:x@beispiel.de', 'json');
  assert.deepEqual(eintrag.themen, ['strom-sparen', 'mietwagen']);
});

test('anmeldung: Honeypot gefuellt -> still "ok", nichts gespeichert', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const antwort = await anmelden(kv, { email: 'bot@beispiel.de', consent: '1', website: 'http://spam.example' });
  assert.equal(antwort.status, 200);
  assert.equal((await antwort.json()).status, 'ok');
  assert.equal(await kv.get('abo:bot@beispiel.de', 'json'), null);
  assert.equal(dispatche.length, 0, 'Bot triggert keine Bestätigung');
  assert.ok([...kv.map.keys()].some((k) => k === 'metrik:falle'), 'Falle wird gezählt');
});

test('anmeldung: Zeitfalle (Formular in < 1,5 s ausgefuellt) -> still ok, nichts gespeichert', async () => {
  const kv = kvLeeren();
  const antwort = await anmelden(kv, { email: 'schnell@beispiel.de', consent: '1', _zeit: String(Date.now() - 100) });
  assert.equal((await antwort.json()).status, 'ok');
  assert.equal(await kv.get('abo:schnell@beispiel.de', 'json'), null);
});

test('anmeldung: ohne Consent -> 400, ohne Speicherung', async () => {
  const kv = kvLeeren();
  const antwort = await anmelden(kv, { email: 'b@beispiel.de' });
  assert.equal(antwort.status, 400);
  assert.equal(await kv.get('abo:b@beispiel.de', 'json'), null);
});

test('anmeldung: ungueltige Adresse -> 400', async () => {
  const kv = kvLeeren();
  for (const adresse of ['kein-at', 'a@b', '@keine.domain.de', 'a @ b.de']) {
    const antwort = await anmelden(kv, { email: adresse, consent: '1' });
    assert.equal(antwort.status, 400, adresse);
  }
});

test('anmeldung: bereits pending -> bereits-pending, kein zweiter Dispatch', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const erste = await anmelden(kv, { email: 'p@beispiel.de', consent: '1' });
  assert.equal((await erste.json()).status, 'angemeldet');
  const nachErstem = dispatche.length;
  assert.equal(nachErstem, 1, 'erster Lauf triggert genau ein Mal');
  const zweite = await anmelden(kv, { email: 'p@beispiel.de', consent: '1' });
  assert.equal((await zweite.json()).status, 'bereits-pending');
  assert.equal(dispatche.length, nachErstem, 'zweiter Lauf triggert NICHT (kein Spam)');
});

test('anmeldung: bereits aktiv -> bereits-aktiv, Token bleibt unveraendert', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'a@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:a@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  const wieder = await anmelden(kv, { email: 'a@beispiel.de', consent: '1' });
  assert.equal((await wieder.json()).status, 'bereits-aktiv');
  const nachher = await kv.get('abo:a@beispiel.de', 'json');
  assert.equal(nachher.token, eintrag.token);
  assert.equal(nachher.status, 'active');
});

test('anmeldung: Adresse war abgemeldet -> Wiederanmeldung mit NEUEM Token', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'w@beispiel.de', consent: '1' });
  const alt = await kv.get('abo:w@beispiel.de', 'json');
  await worker.fetch(form_request('/abmeldung', { token: alt.token }), env_mit(kv));
  const wieder = await anmelden(kv, { email: 'w@beispiel.de', consent: '1' });
  assert.equal((await wieder.json()).status, 'wieder-angemeldet');
  const neu = await kv.get('abo:w@beispiel.de', 'json');
  assert.equal(neu.status, 'pending');
  assert.notEqual(neu.token, alt.token);
  assert.equal(neu.abbestellt, null);
});

test('anmeldung: mehr als 5 pro IP und 15 Min -> 429', async () => {
  const kv = kvLeeren();
  for (let i = 1; i <= 5; i += 1) {
    const antwort = await anmelden(kv, { email: `nr${i}@beispiel.de`, consent: '1' });
    assert.equal(antwort.status, 200, `Nr. ${i}`);
  }
  const sechste = await anmelden(kv, { email: 'nr6@beispiel.de', consent: '1' });
  assert.equal(sechste.status, 429);
  assert.equal(await kv.get('abo:nr6@beispiel.de', 'json'), null);
  // Eine andere IP ist davon unberührt.
  const fremd = await anmelden(kv, { email: 'fremd@beispiel.de', consent: '1' }, { ip: '9.9.9.9' });
  assert.equal(fremd.status, 200);
});

test('anmeldung: Dispatch-Ausfall verliert die Anmeldung nicht (Nachgang deckt ab)', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const freilass = fetch_sperr(() => new Response('fehlgeschlagen', { status: 422 }));
  const antwort = await worker.fetch(form_request('/anmeldung', { email: 'd@beispiel.de', consent: '1' }), env_mit(kv));
  freilass();
  assert.equal(antwort.status, 200);
  const eintrag = await kv.get('abo:d@beispiel.de', 'json');
  assert.equal(eintrag.status, 'pending');
  assert.equal(eintrag.bestaetigung_gesendet, null);
});

test('anmeldung: ohne JS (Accept text/html) -> HTML-Seite', async () => {
  const kv = kvLeeren();
  const antwort = await anmelden(kv, { email: 'html@beispiel.de', consent: '1' }, { akzept: 'text/html' });
  assert.match(antwort.headers.get('content-type'), /text\/html/);
  const roh = await antwort.text();
  assert.match(roh, /Fast geschafft/);
  assert.match(roh, /Double-Opt-In/);
});

// ------------------------------------------------------------------ bestaetigung
test('bestaetigung: pending -> active + Nachweis aktualisiert', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'best@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:best@beispiel.de', 'json');
  const antwort = await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  assert.equal(antwort.status, 200);
  assert.equal((await antwort.json()).status, 'bestaetigt');
  const nachher = await kv.get('abo:best@beispiel.de', 'json');
  assert.equal(nachher.status, 'active');
  assert.ok(nachher.bestaetigt);
});

test('bestaetigung: doppelter Klick -> bereits-bestaetigt (idempotent)', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'id@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:id@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  const zweiter = await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  assert.equal((await zweiter.json()).status, 'bereits-bestaetigt');
});

test('bestaetigung: unbekannter Token -> 404', async () => {
  const kv = kvLeeren();
  const antwort = await worker.fetch(form_request('/bestaetigung', { token: 'falsch-falsch-falsch' }), env_mit(kv));
  assert.equal(antwort.status, 404);
  assert.equal((await antwort.json()).status, 'unbekannt');
});

test('bestaetigung: aelter als 14 Tage -> abgelaufen + Status gesetzt', async () => {
  const kv = kvLeeren();
  const token = 'alt-alt-alt-alt';
  const alt = new Date(Date.now() - 15 * 24 * 60 * 60 * 1000).toISOString();
  kv.map.set('abo:alt@beispiel.de', JSON.stringify({
    email: 'alt@beispiel.de', norm: 'alt@beispiel.de', status: 'pending', token,
    themen: [], seit: alt, ip: null, user_agent: null, seite: '', bestaetigt: null,
    bestaetigung_gesendet: null, versuche: 0, abbestellt: null, grund: null,
  }));
  kv.map.set(`token:${token}`, 'alt@beispiel.de');
  const antwort = await worker.fetch(form_request('/bestaetigung', { token }), env_mit(kv));
  assert.equal(antwort.status, 410);
  assert.equal((await antwort.json()).status, 'abgelaufen');
  assert.equal((await kv.get('abo:alt@beispiel.de', 'json')).status, 'abgelaufen');
});

// ------------------------------------------------------------------ abmeldung
test('abmeldung: POST aktiv -> unsubscribed (inkl. Nachweis-Zustand)', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'ab@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:ab@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  const antwort = await worker.fetch(form_request('/abmeldung', { token: eintrag.token }), env_mit(kv));
  assert.equal((await antwort.json()).status, 'abgemeldet');
  const nachher = await kv.get('abo:ab@beispiel.de', 'json');
  assert.equal(nachher.status, 'unsubscribed');
  assert.ok(nachher.abbestellt);
});

test('abmeldung: GET (One-Klick-Link) entfernt ebenso – Token bleibt nachweisbar', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'one@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:one@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  const antwort = await worker.fetch(
    new Request(`http://abos.test/abmeldung?token=${eintrag.token}`, { headers: { accept: 'application/json' } }),
    env_mit(kv),
  );
  assert.equal((await antwort.json()).status, 'abgemeldet');
  // Zweiter Klick bleibt idempotent (kein Fehler, keine Datenverfälschung).
  const wieder = await worker.fetch(
    new Request(`http://abos.test/abmeldung?token=${eintrag.token}`, { headers: { accept: 'application/json' } }),
    env_mit(kv),
  );
  assert.equal((await wieder.json()).status, 'bereits-abgemeldet');
});

test('abmeldung: offene (pending) Anmeldung wird zurueckgenommen', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'offen@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:offen@beispiel.de', 'json');
  const antwort = await worker.fetch(form_request('/abmeldung', { token: eintrag.token }), env_mit(kv));
  assert.equal((await antwort.json()).status, 'abgemeldet');
  const nachher = await kv.get('abo:offen@beispiel.de', 'json');
  assert.equal(nachher.status, 'unsubscribed');
  assert.equal(nachher.bestaetigt, null);
});

test('abmeldung: unbekannter Token -> 404, nichts geaendert', async () => {
  const kv = kvLeeren();
  const antwort = await worker.fetch(
    new Request('http://abos.test/abmeldung?token=keiner', { headers: { accept: 'application/json' } }),
    env_mit(kv),
  );
  assert.equal(antwort.status, 404);
});

// ------------------------------------------------------------------ praferenzen
test('praferenzen: Themen speichert, unbekannte IDs fallen weg', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'th@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:th@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  const antwort = await worker.fetch(
    form_request('/praferenzen', { token: eintrag.token, themen: ['versicherungen', 'falsch-id'] }),
    env_mit(kv),
  );
  assert.equal((await antwort.json()).status, 'gespeichert');
  assert.deepEqual((await kv.get('abo:th@beispiel.de', 'json')).themen, ['versicherungen']);
});

test('praferenzen: abgemeldete Adresse -> 410', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'pg@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:pg@beispiel.de', 'json');
  await worker.fetch(form_request('/abmeldung', { token: eintrag.token }), env_mit(kv));
  const antwort = await worker.fetch(form_request('/praferenzen', { token: eintrag.token, themen: ['strom-sparen'] }), env_mit(kv));
  assert.equal(antwort.status, 410);
});


function get_request(pfad) {
  return new Request(`http://abos.test${pfad}`, {
    method: 'GET',
    headers: { accept: 'text/html' },
  });
}

function abo_sae(kv, email, status, token, { tag_alter = 0, themen = [] } = {}) {
  const seit = new Date(Date.now() - tag_alter * 24 * 60 * 60 * 1000).toISOString();
  const eintrag = {
    email, norm: email.toLowerCase().trim(), status, token, seit, themen, ip: '1.2.3.4', website: '', ua: '',
    consents: { website: '1', seit, ip: '1.2.3.4', ua: '' },
    nachweis: { ts: seit, ip: '1.2.3.4', ua: '' },
    version: 1,
  };
  kv.map.set(`abo:${email}`, JSON.stringify(eintrag));
  kv.map.set(`token:${token}`, email);
  return eintrag;
}

// ------------------------------------------------- Journey-Seiten (GET)
// Die GET-Seiten rendert der Worker pro Anfrage: Token im HTML, normales
// POST-Formular – der Klick funktioniert OHNE JavaScript. Genau das kann
// eine statische Hugo-Seite nicht (sie sieht Query-Strings beim Build nie).
test('GET /bestaetigung: pending -> HTML-Formular mit Token (ohne JS nutzbar)', async (t) => {
  const kv = kvLeeren();
  const env = env_mit(kv);
  abo_sae(kv, 'marie@example.de', 'pending', 'tok-GET', { themen: ['strom-sparen'] });
  const antwort = await worker.fetch(get_request('/bestaetigung?token=tok-GET'), env, {});
  assert.equal(antwort.status, 200);
  assert.ok((antwort.headers.get('content-type') || '').includes('text/html'));
  const html = await antwort.text();
  assert.ok(html.includes('method="post" action="/bestaetigung"'), 'Formular muss normal POSTen');
  assert.ok(html.includes('name="token" value="tok-GET"'), 'Token muss im HTML stecken');
  assert.ok(html.includes('Ja, ich möchte den Newsletter'), 'Button fehlt');
  const hersteller = globalThis.fetch;
  assert.equal(typeof hersteller, 'function');
});

test('GET /bestaetigung: Formular-Roundtrip ohne JS -> active', async (t) => {
  const kv = kvLeeren();
  const env = env_mit(kv);
  const hersteller = fetch_sperr();
  abo_sae(kv, 'marie@example.de', 'pending', 'tok-ROUND');
  const html = await (await worker.fetch(get_request('/bestaetigung?token=tok-ROUND'), env, {})).text();
  const token = /name="token" value="([^"]+)"/.exec(html)[1];
  assert.equal(token, 'tok-ROUND', 'Extracted Token aus dem HTML muss passen');
  const korper = new URLSearchParams({ token });
  const antwort = await worker.fetch(new Request('http://abos.test/bestaetigung', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded', accept: 'application/json' },
    body: korper,
  }), env, {});
  const daten = await antwort.json();
  assert.equal(daten.status, 'bestaetigt');
  const nach = JSON.parse(kv.map.get('abo:marie@example.de'));
  assert.equal(nach.status, 'active');
  hersteller();
});

test('GET /bestaetigung: active -> "Bereits bestätigt" ohne Formular', async (t) => {
  const kv = kvLeeren();
  abo_sae(kv, 'marie@example.de', 'active', 'tok-AKTIV');
  const antwort = await worker.fetch(get_request('/bestaetigung?token=tok-AKTIV'), env_mit(kv), {});
  const html = await antwort.text();
  assert.equal(antwort.status, 200);
  assert.ok(html.includes('Bereits bestätigt'));
  assert.ok(!html.includes('<form'), 'Kein Formular mehr nötig');
});

test('GET /bestaetigung: unbekannt -> 404, abgelaufenes pending -> 410 + Status gesetzt', async (t) => {
  const kv = kvLeeren();
  const env = env_mit(kv);
  assert.equal((await worker.fetch(get_request('/bestaetigung?token=nix'), env, {})).status, 404);
  abo_sae(kv, 'alter@example.de', 'pending', 'tok-ALT', { tag_alter: 20 });
  const antwort = await worker.fetch(get_request('/bestaetigung?token=tok-ALT'), env, {});
  assert.equal(antwort.status, 410);
  assert.ok((await antwort.text()).includes('abgelaufen'));
  assert.equal(JSON.parse(kv.map.get('abo:alter@example.de')).status, 'abgelaufen');
});

test('GET /praferenzen: active -> Formular, Checkboxen pre-checked, Labels aus THEMEN_LABELS', async (t) => {
  const kv = kvLeeren();
  const env = env_mit(kv, { THEMEN_LABELS: '{"strom-sparen":"Strom & Gas sparen","internet-dsl":"Internet & DSL"}' });
  abo_sae(kv, 'marie@example.de', 'active', 'tok-PRÄF', { themen: ['strom-sparen'] });
  const html = await (await worker.fetch(get_request('/praferenzen?token=tok-PRÄF'), env, {})).text();
  assert.ok(html.includes('value="strom-sparen" checked'), 'Gewählte Welt muss pre-checked sein');
  assert.ok(/value="internet-dsl"(?! checked)/.test(html), 'Ungewählte Welt darf NICHT pre-checked sein');
  assert.ok(html.includes('Strom &amp; Gas sparen'), 'Label aus THEMEN_LABELS fehlt (escapt)');
  assert.ok(html.includes('Internet &amp; DSL'), 'Label aus THEMEN_LABELS fehlt (2)');
  assert.ok(html.includes('name="token" value="tok-PRÄF"'), 'Token muss im Formular stehen');
  assert.ok(html.includes('method="post" action="/praferenzen"'), 'Formular muss POSTen');
});

test('GET /praferenzen: ohne THEMEN_LABELS -> Fallback auf die ID', async (t) => {
  const kv = kvLeeren();
  abo_sae(kv, 'marie@example.de', 'active', 'tok-FB', { themen: ['strom-sparen'] });
  const html = await (await worker.fetch(get_request('/praferenzen?token=tok-FB'), env_mit(kv), {})).text();
  assert.ok(/>\s*strom-sparen<\/label>/.test(html), 'ID muss als Label erscheinen');
});

test('GET /praferenzen: abgemeldet -> 410, unbekannt -> 404', async (t) => {
  const kv = kvLeeren();
  const env = env_mit(kv);
  abo_sae(kv, 'weg@example.de', 'unsubscribed', 'tok-WEG');
  assert.equal((await worker.fetch(get_request('/praferenzen?token=tok-WEG'), env, {})).status, 410);
  assert.equal((await worker.fetch(get_request('/praferenzen?token=nix'), env, {})).status, 404);
});

test('GET /abmelden: One-Klick unverändert (regressionsschirm für die Journey-GETs)', async (t) => {
  const kv = kvLeeren();
  abo_sae(kv, 'marie@example.de', 'active', 'tok-OK');
  const antwort = await worker.fetch(get_request('/abmeldung?token=tok-OK'), env_mit(kv), {});
  assert.equal(antwort.status, 200);
  assert.equal(JSON.parse(kv.map.get('abo:marie@example.de')).status, 'unsubscribed');
});

test('status: liefert Status+Themen, aber KEINE Adresse', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'st@beispiel.de', consent: '1', themen: ['konto-karten'] });
  const eintrag = await kv.get('abo:st@beispiel.de', 'json');
  const antwort = await worker.fetch(
    new Request(`http://abos.test/status?token=${eintrag.token}`, { headers: { accept: 'application/json' } }),
    env_mit(kv),
  );
  const daten = await antwort.json();
  assert.equal(daten.status, 'pending');
  assert.deepEqual(daten.themen, ['konto-karten']);
  assert.ok(!('email' in daten), 'keine Adresse im Status-Endpoint');
});

// ------------------------------------------------------------------ export
function export_request(pfad, { key, token, koerper, methode = 'GET' } = {}) {
  const header = { accept: 'application/json' };
  if (key) header['x-ff-key'] = key;
  return new Request(`http://abos.test${pfad}`, {
    method: methode, headers: header, body: methode === 'POST' ? koerper : undefined,
  });
}

test('export: ohne Secret -> 403, mit falschem Secret -> 403', async () => {
  const kv = kvLeeren();
  for (const key of [undefined, 'falsch-falsch-falsch']) {
    const antwort = await worker.fetch(export_request('/export/abonnenten', { key }), env_mit(kv));
    assert.equal(antwort.status, 403, `key=${key}`);
  }
});

test('export/abonnenten: nur aktive, mit Token und Themen', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'akt@beispiel.de', consent: '1', themen: ['strom-sparen'] });
  await anmelden(kv, { email: 'offen@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:akt@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  const antwort = await worker.fetch(export_request('/export/abonnenten', { key: EXPORT_KEY }), env_mit(kv));
  const daten = await antwort.json();
  assert.equal(daten.anzahl, 1);
  assert.equal(daten.abonnenten[0].email, 'akt@beispiel.de');
  assert.ok(daten.abonnenten[0].token);
  assert.deepEqual(daten.abonnenten[0].themen, ['strom-sparen']);
});

test('export/pending + export/token: offene Liste und Einzel-Lookup', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'off@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:off@beispiel.de', 'json');
  const liste = await worker.fetch(export_request('/export/pending', { key: EXPORT_KEY }), env_mit(kv));
  const ldaten = await liste.json();
  assert.equal(ldaten.anzahl, 1);
  assert.equal(ldaten.offen[0].email, 'off@beispiel.de');
  const detail = await worker.fetch(
    export_request(`/export/token?token=${eintrag.token}`, { key: EXPORT_KEY }), env_mit(kv));
  const ddaten = await detail.json();
  assert.equal(ddaten.email, 'off@beispiel.de');
  assert.equal(ddaten.status, 'pending');
});

test('export/versuch: 3x "gesendet" -> abgelaufen; "bounce" -> Unterdrueckung', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'v@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:v@beispiel.de', 'json');
  for (let i = 1; i <= 2; i += 1) {
    await worker.fetch(export_request('/export/versuch', {
      key: EXPORT_KEY, methode: 'POST',
      koerper: new URLSearchParams({ token: eintrag.token, ergebnis: 'gesendet' }).toString(),
    }), env_mit(kv));
  }
  let status = (await kv.get('abo:v@beispiel.de', 'json')).status;
  assert.equal(status, 'pending', 'nach 2 Versuchen noch offen');
  await worker.fetch(export_request('/export/versuch', {
    key: EXPORT_KEY, methode: 'POST',
    koerper: new URLSearchParams({ token: eintrag.token, ergebnis: 'gesendet' }).toString(),
  }), env_mit(kv));
  assert.equal((await kv.get('abo:v@beispiel.de', 'json')).status, 'abgelaufen', 'nach 3 Versuchen abgelaufen');

  await anmelden(kv, { email: 'b@beispiel.de', consent: '1' });
  const zweiter = await kv.get('abo:b@beispiel.de', 'json');
  await worker.fetch(export_request('/export/versuch', {
    key: EXPORT_KEY, methode: 'POST',
    koerper: new URLSearchParams({ token: zweiter.token, ergebnis: 'bounce' }).toString(),
  }), env_mit(kv));
  const abgeprueft = await kv.get('abo:b@beispiel.de', 'json');
  assert.equal(abgeprueft.status, 'unsubscribed');
  assert.equal(abgeprueft.grund, 'bounce');
});

// ------------------------------------------------------------------ CORS/Rest
test('OPTIONS: Preflight mit Site-Origin', async () => {
  const kv = kvLeeren();
  const antwort = await worker.fetch(new Request('http://abos.test/anmeldung', { method: 'OPTIONS' }), env_mit(kv));
  assert.equal(antwort.status, 204);
  assert.equal(antwort.headers.get('access-control-allow-origin'), 'https://franksfinanzcheck.de');
});

test('unbekannter Pfad -> 404', async () => {
  const kv = kvLeeren();
  const antwort = await worker.fetch(new Request('http://abos.test/sonstiges', { headers: { accept: 'application/json' } }), env_mit(kv));
  assert.equal(antwort.status, 404);
});

// ------------------------------------------------------------------ Taktgeber
const HIER = dirname(fileURLToPath(import.meta.url));

function wrangler_crons() {
  const toml = readFileSync(join(HIER, '..', 'wrangler.toml'), 'utf-8');
  const m = toml.match(/^\s*crons\s*=\s*\[([^\]]*)\]/m);
  assert.ok(m, 'wrangler.toml: [triggers] crons fehlt');
  return [...m[1].matchAll(/"([^"]+)"/g)].map((x) => x[1]);
}

test('taktgeber: wrangler.toml und TAKT decken sich (Wochentage als Namen, nicht 2,5)', () => {
  const crons = wrangler_crons();
  assert.deepEqual([...crons].sort(), Object.keys(TAKT).sort());
  for (const c of crons) {
    const wochentag = c.trim().split(/\s+/)[4];
    assert.ok(!/^\d/.test(wochentag) || wochentag === '*',
      `Cron „${c}“: Cloudflare zählt Wochentage 1=SO..7=SA – Namen (TUE,FRI) statt Ziffern verwenden`);
  }
  assert.ok(crons.length <= 5, 'Free-Plan: höchstens 5 Cron-Triggers pro Account');
});

test('taktgeber: 04:30 Di/Fr -> Newsletter-Daily mit planmaessig (nie live, nie test_adresse)', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const freilass = fetch_sperr();
  const erg = await worker.scheduled({ cron: '30 4 * * TUE,FRI', scheduledTime: Date.UTC(2026, 8, 25, 4, 30) }, env_mit(kv), { waitUntil() {} });
  freilass();
  assert.equal(erg.ok, true);
  assert.equal(erg.name, 'digest');
  assert.equal(dispatche.length, 1);
  assert.match(dispatche[0].ziel, /\/actions\/workflows\/newsletter-daily\.yml\/dispatches$/);
  const body = JSON.parse(dispatche[0].opt.body);
  assert.equal(body.ref, 'main');
  assert.equal(body.inputs.planmaessig, 'true');
  assert.equal(body.inputs.tage, '7');
  assert.equal(body.inputs.live, undefined, 'der Takt darf nie „live“ setzen – nur die Cron-Freigabestufe');
  assert.equal(body.inputs.test_adresse, undefined);
  assert.equal(dispatche[0].opt.headers.Authorization, 'Bearer test-pat');
  const protokoll = await kv.get('takt:digest', 'json');
  assert.equal(protokoll.status, 'dispatched');
  assert.equal(protokoll.http, 204);
  assert.equal(protokoll.versuche, 1);
  assert.equal(protokoll.geplant, '2026-09-25T04:30:00.000Z');
});

test('taktgeber: 05:05 -> Kadenz-Wache ohne Inputs; :17 -> Lifecycle nachgang', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const freilass = fetch_sperr();
  await worker.scheduled({ cron: '5 5 * * TUE,FRI' }, env_mit(kv), { waitUntil() {} });
  await worker.scheduled({ cron: '17 * * * *' }, env_mit(kv), { waitUntil() {} });
  freilass();
  assert.equal(dispatche.length, 2);
  assert.match(dispatche[0].ziel, /newsletter-cadence\.yml\/dispatches$/);
  assert.deepEqual(JSON.parse(dispatche[0].opt.body).inputs, {});
  assert.match(dispatche[1].ziel, /newsletter-lifecycle\.yml\/dispatches$/);
  assert.equal(JSON.parse(dispatche[1].opt.body).inputs.aktion, 'nachgang');
  assert.ok((await kv.get('takt:kadenz', 'json')).status === 'dispatched');
  assert.ok((await kv.get('takt:nachgang', 'json')).status === 'dispatched');
});

test('taktgeber: 5xx -> bis zu 3 Versuche, dann protokolliert fehlgeschlagen', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const freilass = fetch_sperr(() => new Response('unavailable', { status: 503 }));
  const pausen = [];
  const erg = await takt_ausfuehren(env_mit(kv), '30 4 * * TUE,FRI', null, async (ms) => { pausen.push(ms); });
  freilass();
  assert.equal(erg.ok, false);
  assert.equal(erg.versuche, 3);
  assert.equal(dispatche.length, 3);
  assert.deepEqual(pausen, [5000, 20000]);
  const protokoll = await kv.get('takt:digest', 'json');
  assert.equal(protokoll.status, 'fehlgeschlagen');
  assert.equal(protokoll.http, 503);
});

test('taktgeber: 5xx dann 204 -> zweiter Versuch gewinnt', async () => {
  const kv = kvLeeren();
  dispatche = [];
  let n = 0;
  const freilass = fetch_sperr(() => new Response(null, { status: (n += 1) === 1 ? 502 : 204 }));
  const erg = await takt_ausfuehren(env_mit(kv), '30 4 * * TUE,FRI', null, async () => {});
  freilass();
  assert.equal(erg.ok, true);
  assert.equal(erg.versuche, 2);
  assert.equal((await kv.get('takt:digest', 'json')).status, 'dispatched');
});

test('taktgeber: 403 (PAT ohne Actions:write) -> kein Retry, Grund im Protokoll', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const freilass = fetch_sperr(() => new Response('Resource not accessible', { status: 403 }));
  const erg = await takt_ausfuehren(env_mit(kv), '5 5 * * TUE,FRI', null, async () => { assert.fail('bei 403 wird nicht gewartet'); });
  freilass();
  assert.equal(erg.ok, false);
  assert.equal(dispatche.length, 1);
  const protokoll = await kv.get('takt:kadenz', 'json');
  assert.equal(protokoll.status, 'fehlgeschlagen');
  assert.equal(protokoll.warum, 'HTTP 403');
});

test('taktgeber: ohne PAT -> kein Netzaufruf, protokolliert kein-token', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const freilass = fetch_sperr();
  const erg = await takt_ausfuehren(env_mit(kv, { GITHUB_PAT: '' }), '30 4 * * TUE,FRI', null, async () => {});
  freilass();
  assert.equal(erg.ok, false);
  assert.equal(dispatche.length, 0);
  assert.equal((await kv.get('takt:digest', 'json')).warum, 'kein-token');
});

test('taktgeber: unbekannter Cron -> kein Dispatch (kein blinder Versand)', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const freilass = fetch_sperr();
  const erg = await worker.scheduled({ cron: '0 0 * * *' }, env_mit(kv), { waitUntil() {} });
  freilass();
  assert.equal(erg.ok, false);
  assert.equal(erg.name, 'unbekannt');
  assert.equal(dispatche.length, 0);
  assert.equal(takt_fuer('0 0 * * *'), null);
  assert.equal((await kv.get('takt:unbekannt', 'json')).status, 'ignoriert');
});

test('healthz: zeigt Cron-Takte und letzten Dispatch (ohne Adressen/Secrets)', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const freilass = fetch_sperr();
  await worker.scheduled({ cron: '30 4 * * TUE,FRI', scheduledTime: Date.UTC(2026, 8, 25, 4, 30) }, env_mit(kv), { waitUntil() {} });
  freilass();
  const antwort = await worker.fetch(new Request('http://abos.test/healthz'), env_mit(kv));
  const daten = await antwort.json();
  assert.deepEqual([...daten.takt.crons].sort(), Object.keys(TAKT).sort());
  assert.equal(daten.takt.letzte.digest.status, 'dispatched');
  assert.equal(daten.takt.letzte.digest.workflow, 'newsletter-daily.yml');
  assert.ok(!JSON.stringify(daten).includes('test-pat'), 'kein Secret im healthz');
});
