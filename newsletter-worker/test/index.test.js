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
import worker, {
  TAKT, takt_ausfuehren, takt_fuer, datenschutz_pflege, PFLEGE_CRON, feedback_aufrollen,
  limit_klasse, schluessel_pruefen, schreibschluessel_pruefen, tagesbudget_nehmen,
  tagesbudget_stand, schluessel_fingerabdruck, ANMELDUNG_MAX_PRO_TAG_DEFAULT,
  menge_speicher_pruefen, menge_speicher_zuruecksetzen, export_speicher_zuruecksetzen,
} from '../src/index.js';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const EXPORT_KEY = 'export-key-32-z------------';

function kvLeeren() {
  const daten = new Map();
  const optionen = new Map();
  return {
    map: daten,
    options: optionen,
    async get(schluessel, typ) {
      const roh = daten.get(schluessel);
      if (roh === undefined) return null;
      return typ === 'json' ? JSON.parse(roh) : roh;
    },
    async put(schluessel, wert, opts) {
      daten.set(schluessel, typeof wert === 'string' ? wert : JSON.stringify(wert));
      optionen.set(schluessel, opts || null);
    },
    async delete(schluessel) {
      daten.delete(schluessel);
      optionen.delete(schluessel);
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
test('healthz: KV erreichbar -> ok und Schlüsselrollen korrekt ausgewiesen', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv, { EXPORT_KEY_WRITE: 'schreib-key-32-z------------' });
  const antwort = await worker.fetch(new Request('http://abos.test/healthz'), env);
  assert.equal(antwort.status, 200);
  const daten = await antwort.json();
  assert.equal(daten.ok, true);
  assert.ok(!('schluesselrollen' in daten), 'öffentlich keine Betriebsdetails');
  const intern = await worker.fetch(export_request('/healthz', { key: EXPORT_KEY }), env);
  assert.equal(intern.status, 200);
  assert.equal((await intern.json()).schluesselrollen, 'getrennt');
});

// ------------------------------------------------------------------ anmeldung
test('anmeldung: neuer Absender -> pending + Token + Nachweis + Dispatch (ohne Token/Adresse)', async () => {
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
  assert.ok(eintrag.seit);
  assert.ok(!eintrag.ip && !eintrag.user_agent, 'IP/UA nur im befristeten Nachweis (Audit N-04)');

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
  assert.equal(body.inputs.aktion, 'nachgang');
  assert.equal(body.inputs.token, undefined, 'kein Token im Dispatch – er stuende im Actions-Log (Audit H-05)');
  assert.ok(!JSON.stringify(body).includes(eintrag.token), 'Token nirgends im Dispatch-Body');
  assert.ok(!JSON.stringify(body).includes('@beispiel.de'), 'keine Adresse im Dispatch-Body');
});

test('anmeldung: Themen ausserhalb der erlaubten IDs werden gefiltert', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'x@beispiel.de', consent: '1', themen: ['strom-sparen', 'geheim-thema', 'mietwagen'] });
  const eintrag = await kv.get('abo:x@beispiel.de', 'json');
  assert.deepEqual(eintrag.themen, ['strom-sparen', 'mietwagen']);
});

test('anmeldung: Feldname themen[] aus dem HTML-Formular wird gespeichert (kein stiller Datenverlust)', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'y@beispiel.de', consent: '1', 'themen[]': ['versicherungen', 'falsch-id'] });
  const eintrag = await kv.get('abo:y@beispiel.de', 'json');
  assert.deepEqual(eintrag.themen, ['versicherungen']);
});

test('anmeldung: Honeypot gefuellt -> still "ok", nichts gespeichert', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const antwort = await anmelden(kv, { email: 'bot@beispiel.de', consent: '1', website: 'http://spam.example' });
  assert.equal(antwort.status, 200);
  assert.equal((await antwort.json()).status, 'ok');
  assert.equal(await kv.get('abo:bot@beispiel.de', 'json'), null);
  assert.equal(dispatche.length, 0, 'Bot triggert keine Bestätigung');
  assert.ok(![...kv.map.keys()].some((k) => k.startsWith('metrik:')), 'Falle schreibt nichts ins KV (Schreibbudget, Audit H-03)');
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

test('anmeldung: bereits pending -> gleiche Antwort wie neu, kein zweiter Dispatch', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const erste = await anmelden(kv, { email: 'p@beispiel.de', consent: '1' });
  assert.equal((await erste.json()).status, 'angemeldet');
  const nachErstem = dispatche.length;
  assert.equal(nachErstem, 1, 'erster Lauf triggert genau ein Mal');
  const zweite = await anmelden(kv, { email: 'p@beispiel.de', consent: '1' });
  assert.equal((await zweite.json()).status, 'angemeldet', 'keine Enumeration (Audit M-01)');
  assert.equal(dispatche.length, nachErstem, 'zweiter Lauf triggert NICHT (kein Spam)');
});

test('anmeldung: bereits aktiv -> gleiche Antwort wie neu, Token bleibt unveraendert', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'a@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:a@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  const wieder = await anmelden(kv, { email: 'a@beispiel.de', consent: '1' });
  assert.equal((await wieder.json()).status, 'angemeldet', 'keine Enumeration (Audit M-01)');
  const nachher = await kv.get('abo:a@beispiel.de', 'json');
  assert.equal(nachher.token, eintrag.token);
  assert.equal(nachher.status, 'active');
});

test('anmeldung: Adresse war abgemeldet -> Wiederanmeldung mit NEUEM Token, gleiche Antwort', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'w@beispiel.de', consent: '1' });
  const alt = await kv.get('abo:w@beispiel.de', 'json');
  await worker.fetch(form_request('/abmeldung', { token: alt.token }), env_mit(kv));
  const wieder = await anmelden(kv, { email: 'w@beispiel.de', consent: '1' });
  assert.equal((await wieder.json()).status, 'angemeldet', 'keine Enumeration (Audit M-01)');
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

test('abmeldung: GET mit Token fragt nur nach – erst der POST meldet ab (Audit M-03)', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'one@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:one@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  // Link-Scanner (Outlook Safe Links, Virenscanner) rufen GET auf – das darf
  // niemanden abmelden.
  const vorschau = await worker.fetch(
    new Request(`http://abos.test/abmeldung?token=${eintrag.token}`, { headers: { accept: 'application/json' } }),
    env_mit(kv),
  );
  assert.equal(vorschau.status, 200);
  assert.equal((await vorschau.json()).status, 'bestaetigen');
  assert.equal((await kv.get('abo:one@beispiel.de', 'json')).status, 'active', 'GET aendert nichts');
  // Der Klick auf „Abmelden“ (POST) meldet ab …
  const antwort = await worker.fetch(form_request('/abmeldung', { token: eintrag.token }), env_mit(kv));
  assert.equal((await antwort.json()).status, 'abgemeldet');
  // … und ein zweiter Klick bleibt idempotent.
  const wieder = await worker.fetch(form_request('/abmeldung', { token: eintrag.token }), env_mit(kv));
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

test('abmeldung: RFC 8058 POST liest Token aus der Query, nicht nur aus dem Body', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'rfc@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:rfc@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  const antwort = await worker.fetch(new Request(
    `http://abos.test/abmeldung?token=${eintrag.token}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
        accept: 'application/json',
        'cf-connecting-ip': '1.2.3.4',
      },
      body: 'List-Unsubscribe=One-Click',
    },
  ), env_mit(kv));
  assert.equal((await antwort.json()).status, 'abgemeldet');
  assert.equal((await kv.get('abo:rfc@beispiel.de', 'json')).status, 'unsubscribed');
});

test('abmeldung: POST mit E-Mail ohne Token meldet ab – unbekannte Adresse gleicher Erfolg', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'form@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:form@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  const ok = await worker.fetch(form_request('/abmeldung', { email: 'form@beispiel.de' }), env_mit(kv));
  assert.equal((await ok.json()).status, 'abgemeldet');
  assert.equal((await kv.get('abo:form@beispiel.de', 'json')).status, 'unsubscribed');
  const fremd = await worker.fetch(form_request('/abmeldung', { email: 'nie@beispiel.de' }), env_mit(kv));
  assert.equal(fremd.status, 200);
  assert.equal((await fremd.json()).status, 'abgemeldet');
});

test('abmeldung: GET ohne Token liefert das Formular, kein 404', async () => {
  const kv = kvLeeren();
  const html = await worker.fetch(get_request('/abmeldung'), env_mit(kv));
  assert.equal(html.status, 200);
  const text = await html.text();
  assert.ok(text.includes('method="post"'));
  assert.ok(text.includes('name="email"'));
  const jsonAntwort = await worker.fetch(
    new Request('http://abos.test/abmeldung', { headers: { accept: 'application/json' } }),
    env_mit(kv),
  );
  assert.equal(jsonAntwort.status, 200);
  assert.equal((await jsonAntwort.json()).status, 'formular');
});

test('export/kontakt: Schreib-Key-Pflicht, E-Mail nur im POST-Body', async () => {
  const kv = kvLeeren();
  const WRITE_KEY = 'schreib-key-32-z------------';
  const env = env_mit(kv, { EXPORT_KEY_WRITE: WRITE_KEY });
  await anmelden(kv, { email: 'look@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:look@beispiel.de', 'json');

  const ohne = await worker.fetch(export_request('/export/kontakt', {
    methode: 'POST', koerper: JSON.stringify({ email: 'look@beispiel.de' }),
  }), env);
  assert.equal(ohne.status, 403);
  const lesend = await worker.fetch(export_request('/export/kontakt', {
    key: EXPORT_KEY, methode: 'POST', koerper: JSON.stringify({ email: 'look@beispiel.de' }),
  }), env);
  assert.equal(lesend.status, 403, 'Leseschlüssel darf keine E-Mail zu Token auflösen');

  const alteGetRoute = await worker.fetch(export_request(
    '/export/kontakt?email=look@beispiel.de', { key: WRITE_KEY }), env);
  assert.equal(alteGetRoute.status, 405, 'E-Mail darf nicht mehr in der URL stehen');

  const mit = await worker.fetch(export_request('/export/kontakt', {
    key: WRITE_KEY, methode: 'POST', koerper: JSON.stringify({ email: 'look@beispiel.de' }),
  }), env);
  assert.equal(mit.status, 200);
  const daten = await mit.json();
  assert.equal(daten.status, 'pending');
  assert.equal(daten.token, eintrag.token);

  const unbekannt = await worker.fetch(export_request('/export/kontakt', {
    key: WRITE_KEY, methode: 'POST', koerper: JSON.stringify({ email: 'nie@beispiel.de' }),
  }), env);
  assert.equal(unbekannt.status, 404);

  const vorher = kv.map.size;
  const uebergross = await worker.fetch(export_request('/export/kontakt', {
    key: WRITE_KEY, methode: 'POST',
    koerper: JSON.stringify({ email: 'a'.repeat(65 * 1024) }),
  }), env);
  assert.equal(uebergross.status, 404, 'überdimensionierte Bodies werden vor dem Parsen verworfen');
  assert.equal(kv.map.size, vorher, 'abgewiesener Body darf keinen KV-Schreibzugriff auslösen');
  assert.equal((await kv.get('abo:look@beispiel.de', 'json')).token, eintrag.token,
    'bestehender Datensatz bleibt unverändert');
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

test('praferenzen: themen[] (HTML-Feldname) wird wie themen akzeptiert', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'th2@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:th2@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));
  const antwort = await worker.fetch(
    form_request('/praferenzen', { token: eintrag.token, 'themen[]': ['mietwagen'] }),
    env_mit(kv),
  );
  assert.equal((await antwort.json()).status, 'gespeichert');
  assert.deepEqual((await kv.get('abo:th2@beispiel.de', 'json')).themen, ['mietwagen']);
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
  assert.ok(
    html.includes('/newsletter/praeferenzen/?token=tok-PRÄF'),
    'Vollversions-Link auf die Website muss das Token tragen',
  );
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

test('GET /abmeldung: Bestaetigungsseite mit POST-Formular, Status unveraendert', async (t) => {
  const kv = kvLeeren();
  abo_sae(kv, 'marie@example.de', 'active', 'tok-OK');
  const antwort = await worker.fetch(get_request('/abmeldung?token=tok-OK'), env_mit(kv), {});
  assert.equal(antwort.status, 200);
  assert.match(antwort.headers.get('content-type'), /text\/html/);
  const html = await antwort.text();
  assert.match(html, /<form[^>]+method="post"/i);
  assert.match(html, /name="token" value="tok-OK"/);
  assert.equal(JSON.parse(kv.map.get('abo:marie@example.de')).status, 'active', 'GET meldet nicht ab');
  // Formular-Roundtrip ohne JavaScript
  const post = await worker.fetch(form_request('/abmeldung', { token: 'tok-OK' }, { akzept: 'text/html' }), env_mit(kv));
  assert.equal(post.status, 200);
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
function export_request(pfad, { key, token, koerper, methode = 'GET', ip = '' } = {}) {
  const header = { accept: 'application/json' };
  if (key) header['x-ff-key'] = key;
  if (ip) header['cf-connecting-ip'] = ip;
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

test('export/abonnenten: nur aktive, mit Themen – Token NUR mit Schreibschluessel (F-08)', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'akt@beispiel.de', consent: '1', themen: ['strom-sparen'] });
  await anmelden(kv, { email: 'offen@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:akt@beispiel.de', 'json');
  await worker.fetch(form_request('/bestaetigung', { token: eintrag.token }), env_mit(kv));

  // 1. Standardexport: Adresse und Themen, aber KEIN Token (Gegenprobe).
  const standard = await (await worker.fetch(
    export_request('/export/abonnenten', { key: EXPORT_KEY }), env_mit(kv))).json();
  assert.equal(standard.anzahl, 1);
  assert.equal(standard.abonnenten[0].email, 'akt@beispiel.de');
  assert.deepEqual(standard.abonnenten[0].themen, ['strom-sparen']);
  assert.equal(standard.mit_token, false);
  assert.ok(!('token' in standard.abonnenten[0]),
    'Token im Massenexport nur mit dem zweiten Schluessel');

  // 2. Getrennte Rollen: ?mit_token=1 mit dem LESESchluessel -> weiter ohne Token.
  const env_getrennt = env_mit(kv, { EXPORT_KEY_WRITE: 'schreib-key-32-z------------' });
  const lesend = await (await worker.fetch(
    export_request('/export/abonnenten?mit_token=1', { key: EXPORT_KEY }), env_getrennt)).json();
  assert.equal(lesend.mit_token, false);
  assert.ok(!('token' in lesend.abonnenten[0]), 'Leseschluessel oeffnet keine Token');

  // 3. Positivprobe: Schreibschluessel + ?mit_token=1 -> Token ist da.
  const schreibend = await (await worker.fetch(
    export_request('/export/abonnenten?mit_token=1', { key: 'schreib-key-32-z------------' }),
    env_getrennt)).json();
  assert.equal(schreibend.mit_token, true);
  assert.equal(schreibend.abonnenten[0].token, eintrag.token);

  // 4. Kein Rückfall: ohne getrenntes EXPORT_KEY_WRITE bleibt der
  //    Leseschlüssel auch bei mit_token=1 tokenfrei.
  const failClosed = await (await worker.fetch(
    export_request('/export/abonnenten?mit_token=1', { key: EXPORT_KEY }), env_mit(kv))).json();
  assert.equal(failClosed.mit_token, false);
  assert.ok(!('token' in failClosed.abonnenten[0]));

  // 5. Ein versehentlich gleicher Lese-/Schreibwert gilt ebenfalls nicht als Trennung.
  const gleicherSchluessel = env_mit(kv, { EXPORT_KEY_WRITE: EXPORT_KEY });
  const gleicheRolle = await (await worker.fetch(
    export_request('/export/abonnenten?mit_token=1', { key: EXPORT_KEY }), gleicherSchluessel)).json();
  assert.equal(gleicheRolle.mit_token, false);
});

test('export: erfolgreiche Aufrufe und begrenzte 403-Protokollierung (F-08)', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv);
  // Mengen- und Deny-Logger sind Prozesszustand; für reproduzierbare Proben leeren.
  menge_speicher_zuruecksetzen();
  export_speicher_zuruecksetzen();
  await worker.fetch(export_request('/export/abonnenten', { key: 'falsch-falsch-falsch' }), env);
  await worker.fetch(export_request('/export/pending', { key: 'weiterer-falscher-schluessel' }), env);
  await worker.fetch(export_request('/export/pending', { key: EXPORT_KEY }), env);
  const protokoll = [...kv.map.keys()].filter((k) => k.startsWith('exportlog:'));
  assert.equal(protokoll.length, 2,
    '403-Sturm erzeugt höchstens einen KV-Nachweis pro Stunde, erfolgreiche Abfrage bleibt sichtbar');
  const eintraege = protokoll.map((k) => JSON.parse(kv.map.get(k)));
  assert.equal(eintraege.filter((e) => e.status === 403).length, 1);
  assert.ok(eintraege.some((e) => e.route === '/export/pending' && e.status === 200));
  // Der Abdruck ist ein Kurz-Hash – NIE der Schluessel selbst.
  for (const e of eintraege) {
    assert.match(e.key, /^[0-9a-f]{8}$/);
    assert.ok(!JSON.stringify(e).includes(EXPORT_KEY));
  }
  // Sichtbar fuer den Betreiber (healthz mit Schluessel), verborgen fuer alle anderen.
  const oeffentlich = await (await worker.fetch(new Request('http://abos.test/healthz'), env)).json();
  assert.ok(!('exporte' in oeffentlich), 'Betriebsbild nur mit Schluessel');
  const intern = await (await worker.fetch(export_request('/healthz', { key: EXPORT_KEY }), env)).json();
  assert.equal(intern.exporte.length, 2);
  assert.equal(intern.schluesselrollen, 'gemeinsam');
});

test('Anmeldung: Tagesbudget deckelt die Schreibzugriffe (F-03)', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv, { ANMELDUNG_MAX_PRO_TAG: '2' });
  const freilass = fetch_sperr();
  const a = await worker.fetch(form_request('/anmeldung', { email: 'eins@beispiel.de', consent: '1' }), env);
  const b = await worker.fetch(form_request('/anmeldung', { email: 'zwei@beispiel.de', consent: '1' }), env);
  const c = await worker.fetch(form_request('/anmeldung', { email: 'drei@beispiel.de', consent: '1' }), env);
  freilass();
  assert.equal(a.status, 200);
  assert.equal(b.status, 200);
  assert.equal(c.status, 503, 'dritte Anmeldung wird fail-closed abgelehnt');
  assert.equal(await kv.get('abo:drei@beispiel.de', 'json'), null, 'nichts geschrieben');
  assert.equal(await kv.get('budget:anmeldung:' + new Date().toISOString().slice(0, 10)), '2');
  // Genau EINE laute Meldung je Stunde – der Melder darf das Budget nicht fressen.
  assert.ok(kv.map.has('warn:anmeldung:' + new Date().toISOString().slice(0, 10)));
  const text = await c.text();
  assert.ok(!text.includes('budget') && !text.includes('Kontingent'),
    'die Antwort verraet keine Betriebsinterna');
});

test('Mengenklassen: jede Route hat eine Klasse (F-03)', () => {
  assert.equal(limit_klasse('/bestaetigung', 'GET'), 'lesen');
  assert.equal(limit_klasse('/praferenzen', 'GET'), 'lesen');
  assert.equal(limit_klasse('/status', 'GET'), 'lesen');
  assert.equal(limit_klasse('/feedback', 'GET'), 'feedback');
  assert.equal(limit_klasse('/feedback', 'POST'), 'feedback');
  assert.equal(limit_klasse('/export/abonnenten', 'GET'), 'export');
  assert.equal(limit_klasse('/export/versuch', 'POST'), 'export');
  // Die POST-Routen mit eigener Pruefung bleiben bei ihren strengeren Limits.
  assert.equal(limit_klasse('/anmeldung', 'POST'), null);
  assert.equal(limit_klasse('/abmeldung', 'POST'), null);
});

test('Mengenbegrenzung greift auf den Token-Seiten (F-03, Limbus ohne Binding)', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv, { RATE_LIMIT_LESEN: '2' });
  const hole = () => worker.fetch(new Request('http://abos.test/status?token=egal', {
    headers: { accept: 'application/json', 'cf-connecting-ip': '203.0.113.9' },
  }), env);
  const eins = await hole();
  const zwei = await hole();
  const drei = await hole();
  assert.equal(eins.status, 404, 'unbekannter Token – aber die Anfrage wird bearbeitet');
  assert.equal(zwei.status, 404);
  assert.equal(drei.status, 429, 'ab der Grenze wird gebremst');
});

test('Log-Hygiene: die E-Mail-Adresse steht nie im Klartext-Log (F-05)', async () => {
  const kv = kvLeeren();
  // Defekter Bestand (unbekannter Status) ist genau der Pfad, der vorher loggte.
  await kv.put('abo:defekt@beispiel.de', JSON.stringify({
    email: 'defekt@beispiel.de', norm: 'defekt@beispiel.de', status: 'kaputt',
    token: 'x'.repeat(32), seit: new Date().toISOString(), themen: [],
  }));
  const meldungen = [];
  const zuvor = console.warn;
  console.warn = (...args) => meldungen.push(args.join(' '));
  try {
    const freilass = fetch_sperr();
    await worker.fetch(form_request('/anmeldung', { email: 'defekt@beispiel.de', consent: '1' }),
      env_mit(kv));
    freilass();
  } finally {
    console.warn = zuvor;
  }
  assert.ok(meldungen.length >= 1, 'der Fall wird gemeldet');
  const gesamt = meldungen.join('\n');
  assert.ok(!gesamt.includes('defekt@beispiel.de'), 'keine Adresse im Log');
  assert.match(gesamt, /sha256:[0-9a-f]{32}/);
});

test('export/pending + export/token: Leserechte getrennt, Token nur per POST/Write-Key', async () => {
  const kv = kvLeeren();
  const WRITE_KEY = 'schreib-key-32-z------------';
  const env = env_mit(kv, { EXPORT_KEY_WRITE: WRITE_KEY });
  await anmelden(kv, { email: 'off@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:off@beispiel.de', 'json');
  const liste = await worker.fetch(export_request('/export/pending', { key: EXPORT_KEY }), env);
  const ldaten = await liste.json();
  assert.equal(ldaten.anzahl, 1);
  assert.equal(ldaten.offen[0].email, 'off@beispiel.de');
  assert.ok(!('token' in ldaten.offen[0]), 'Leseschlüssel darf Pending-Tokens nicht liefern');

  const verweigert = await worker.fetch(export_request('/export/token', {
    key: EXPORT_KEY, methode: 'POST', koerper: JSON.stringify({ token: eintrag.token }),
  }), env);
  assert.equal(verweigert.status, 403, 'Leseschlüssel darf Einzel-Token nicht laden');
  const alteGetRoute = await worker.fetch(export_request(
    `/export/token?token=${eintrag.token}`, { key: WRITE_KEY }), env);
  assert.equal(alteGetRoute.status, 405, 'Token-Lookup per GET/Query ist nicht mehr unterstützt');

  const anfrage = export_request('/export/token', {
    key: WRITE_KEY, methode: 'POST', koerper: JSON.stringify({ token: eintrag.token }),
  });
  const detail = await worker.fetch(anfrage, env);
  const ddaten = await detail.json();
  assert.equal(detail.status, 200);
  assert.ok(!anfrage.url.includes(eintrag.token), 'Token darf nicht in die URL/Access-Logs');
  assert.equal(ddaten.email, 'off@beispiel.de');
  assert.equal(ddaten.status, 'pending');
  assert.equal(ddaten.token, eintrag.token);
});

test('export/versuch: Schreib-Key nötig; 3x gesendet -> abgelaufen; Bounce -> Unterdrueckung', async () => {
  const kv = kvLeeren();
  const WRITE_KEY = 'schreib-key-32-z------------';
  const env = env_mit(kv, { EXPORT_KEY_WRITE: WRITE_KEY });
  await anmelden(kv, { email: 'v@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:v@beispiel.de', 'json');
  const lesend = await worker.fetch(export_request('/export/versuch', {
    key: EXPORT_KEY, methode: 'POST',
    koerper: new URLSearchParams({ token: eintrag.token, ergebnis: 'bounce' }).toString(),
  }), env);
  assert.equal(lesend.status, 403, 'Leseschlüssel darf Statusänderungen nicht auslösen');
  assert.equal((await kv.get('abo:v@beispiel.de', 'json')).status, 'pending');

  for (let i = 1; i <= 2; i += 1) {
    await worker.fetch(export_request('/export/versuch', {
      key: WRITE_KEY, methode: 'POST',
      koerper: new URLSearchParams({ token: eintrag.token, ergebnis: 'gesendet' }).toString(),
    }), env);
  }
  let status = (await kv.get('abo:v@beispiel.de', 'json')).status;
  assert.equal(status, 'pending', 'nach 2 Versuchen noch offen');
  await worker.fetch(export_request('/export/versuch', {
    key: WRITE_KEY, methode: 'POST',
    koerper: new URLSearchParams({ token: eintrag.token, ergebnis: 'gesendet' }).toString(),
  }), env);
  assert.equal((await kv.get('abo:v@beispiel.de', 'json')).status, 'abgelaufen', 'nach 3 Versuchen abgelaufen');

  await anmelden(kv, { email: 'b@beispiel.de', consent: '1' });
  const zweiter = await kv.get('abo:b@beispiel.de', 'json');
  await worker.fetch(export_request('/export/versuch', {
    key: WRITE_KEY, methode: 'POST',
    koerper: new URLSearchParams({ token: zweiter.token, ergebnis: 'bounce' }).toString(),
  }), env);
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

test('wrangler.toml traegt die Schutzwariablen des Audits 15.10.2026 (F-03)', () => {
  const quelle = readFileSync(join(HIER, '..', 'wrangler.toml'), 'utf8');
  // Ohne diese Variablen faellt der Worker auf die Defaults zurueck – die
  // sind identisch, aber ein Deploy, der sie still verliert, soll auffallen.
  for (const name of ['ANMELDUNG_MAX_PRO_TAG', 'RATE_LIMIT_LESEN', 'RATE_LIMIT_FEEDBACK',
    'RATE_LIMIT_EXPORT', 'FEEDBACK_MAX_PRO_TAG']) {
    assert.match(quelle, new RegExp(`^${name} = "\\d+"(\\s*#.*)?$`, 'm'), `${name} fehlt in wrangler.toml`);
  }
  // Der Tagesdeckel muss unter dem Schreibkontingent bleiben: 100 Anmeldungen
  // x 4 Schreibzugriffe + 200 Feedback bleiben deutlich unter 1.000.
  const deckel = Number(/^ANMELDUNG_MAX_PRO_TAG = "(\d+)"/m.exec(quelle)[1]);
  const feedback = Number(/^FEEDBACK_MAX_PRO_TAG = "(\d+)"/m.exec(quelle)[1]);
  assert.ok(deckel * 4 + feedback <= 1000,
    `Tagesdeckel ${deckel} x 4 + ${feedback} Feedback sprengt die 1.000 Schreibzugriffe`);
  // workers_dev bleibt aus (WAF/Zone), das Rate-Limit-Binding bleibt da.
  assert.match(quelle, /workers_dev = false/);
  assert.match(quelle, /preview_urls = false/);
  assert.match(quelle, /\[\[ratelimits\]\]/);
});

test('taktgeber: wrangler.toml und TAKT decken sich (Wochentage als Namen, nicht 2,5)', () => {
  const crons = wrangler_crons();
  assert.deepEqual([...crons].sort(), [...Object.keys(TAKT), PFLEGE_CRON].sort());
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
  // Oeffentlich: nur lebendig/tot – keine Workflow-Namen, keine Fehlertexte.
  const offen = await (await worker.fetch(new Request('http://abos.test/healthz'), env_mit(kv))).json();
  assert.deepEqual(Object.keys(offen).sort(), ['ok', 'ts']);
  const antwort = await worker.fetch(new Request('http://abos.test/healthz', { headers: { 'X-FF-Key': EXPORT_KEY } }), env_mit(kv));
  const daten = await antwort.json();
  assert.deepEqual([...daten.takt.crons].sort(), Object.keys(TAKT).sort());
  assert.equal(daten.takt.letzte.digest.status, 'dispatched');
  assert.equal(daten.takt.letzte.digest.workflow, 'newsletter-daily.yml');
  assert.ok(!JSON.stringify(daten).includes('test-pat'), 'kein Secret im healthz');
});

// ---------------------------------------------------------------- FEEDBACK (H4)

function feedback_request(slug, hilfreich, ip = '203.0.113.7') {
  return new Request('http://abos.test/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'CF-Connecting-IP': ip },
    body: JSON.stringify({ slug, hilfreich }),
  });
}

test('feedback: zaehlt ja/nein je Slug und liest sie per GET', async () => {
  const kv = kvLeeren();
  await worker.fetch(feedback_request('2026-08-26-tagesgeld-zinsen', 'ja'), env_mit(kv));
  await worker.fetch(feedback_request('2026-08-26-tagesgeld-zinsen', 'ja', '198.51.100.9'), env_mit(kv));
  await worker.fetch(feedback_request('2026-08-26-tagesgeld-zinsen', 'nein', '198.51.100.10'), env_mit(kv));
  const antwort = await worker.fetch(
    new Request('http://abos.test/feedback?slug=2026-08-26-tagesgeld-zinsen', { headers: { Accept: 'application/json' } }), env_mit(kv));
  const daten = await antwort.json();
  assert.equal(antwort.status, 200);
  assert.equal(daten.ja, 2);
  assert.equal(daten.nein, 1);
});

test('feedback: Doppelklick gleiche IP zaehlt nur einmal (idempotent)', async () => {
  const kv = kvLeeren();
  const erster = await worker.fetch(feedback_request('pillar-strom-sparen', 'ja'), env_mit(kv));
  const zweiter = await worker.fetch(feedback_request('pillar-strom-sparen', 'ja'), env_mit(kv));
  assert.equal((await erster.json()).status, 'gezaehlt');
  assert.equal((await zweiter.json()).status, 'bereits-gezaehlt');
  const daten = await (await worker.fetch(
    new Request('http://abos.test/feedback?slug=pillar-strom-sparen', { headers: { Accept: 'application/json' } }), env_mit(kv))).json();
  assert.equal(daten.ja, 1);
});

test('feedback: andere IP darf erneut stimmen (Hash enthaelt den Slug)', async () => {
  const kv = kvLeeren();
  await worker.fetch(feedback_request('pillar-strom-sparen', 'ja', '203.0.113.7'), env_mit(kv));
  await worker.fetch(feedback_request('pillar-strom-sparen', 'ja', '203.0.113.8'), env_mit(kv));
  const daten = await (await worker.fetch(
    new Request('http://abos.test/feedback?slug=pillar-strom-sparen', { headers: { Accept: 'application/json' } }), env_mit(kv))).json();
  assert.equal(daten.ja, 2);
});

test('feedback: ungueltiger Slug und ungueltige Stimme -> 400', async () => {
  const kv = kvLeeren();
  const a = await worker.fetch(feedback_request('../evil', 'ja'), env_mit(kv));
  const b = await worker.fetch(feedback_request('guter-slug', 'vielleicht'), env_mit(kv));
  assert.equal(a.status, 400);
  assert.equal(b.status, 400);
});

test('feedback: GET ohne Slug -> 400, unbekannter Slug -> 0/0', async () => {
  const kv = kvLeeren();
  const a = await worker.fetch(new Request('http://abos.test/feedback', { headers: { Accept: 'application/json' } }), env_mit(kv));
  const b = await worker.fetch(new Request('http://abos.test/feedback?slug=gibts-noch-nicht', { headers: { Accept: 'application/json' } }), env_mit(kv));
  assert.equal(a.status, 400);
  const daten = await b.json();
  assert.equal(daten.ja, 0);
  assert.equal(daten.nein, 0);
});

test('feedback: zaehlt nur, keine Klartext-IP im KV (Missbrauchschluessel gehasht)', async () => {
  const kv = kvLeeren();
  await worker.fetch(feedback_request('pillar-konto-karten', 'nein'), env_mit(kv));
  const schluessel = [...kv.map.keys()];
  for (const s of schluessel) {
    assert.ok(!s.includes('203.0.113.7'), `IP im Schluessel: ${s}`);
    assert.ok(!String(kv.map.get(s)).includes('203.0.113.7'), `IP im Wert: ${s}`);
  }
});

test('feedback: antwortet CORS nur fuer die Site-Origin', async () => {
  const kv = kvLeeren();
  const antwort = await worker.fetch(feedback_request('pillar-konto-karten', 'ja'), env_mit(kv));
  assert.equal(antwort.headers.get('Access-Control-Allow-Origin'), 'https://franksfinanzcheck.de');
});

// ------------------------------------------------------------------ Datenschutz-Pflege
test('Datenschutz-Pflege: abgemeldete Bestandsdaten nach 29 Tagen inkl. Token löschen, Nachweis getrennt erhalten', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'alt@beispiel.de', consent: '1' });
  const eintrag = await kv.get('abo:alt@beispiel.de', 'json');
  eintrag.status = 'unsubscribed';
  eintrag.abbestellt = '2026-09-01T00:00:00Z';
  await kv.put('abo:alt@beispiel.de', JSON.stringify(eintrag)); // Altbestand ohne TTL
  const env = env_mit(kv);
  const frueh = await datenschutz_pflege(env, Date.parse('2026-09-28T00:00:00Z'));
  assert.equal(frueh.geloescht, 0);
  const spaet = await worker.scheduled({ cron: PFLEGE_CRON, scheduledTime: Date.parse('2026-10-01T00:00:00Z') }, env, { waitUntil() {} });
  assert.equal(spaet.geloescht, 1);
  assert.equal(await kv.get('abo:alt@beispiel.de'), null);
  assert.equal(await kv.get(`token:${eintrag.token}`), null);
  assert.equal([...kv.map.keys()].filter((k) => k.startsWith('nachweis:')).length, 1);
});

test('Datenschutz-Pflege: aktive Abos bleiben, offene veraltete und alte Token verschwinden', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'aktiv@beispiel.de', consent: '1' });
  await anmelden(kv, { email: 'offen@beispiel.de', consent: '1' });
  const aktiv = await kv.get('abo:aktiv@beispiel.de', 'json');
  aktiv.status = 'active';
  await kv.put('abo:aktiv@beispiel.de', JSON.stringify(aktiv));
  const offen = await kv.get('abo:offen@beispiel.de', 'json');
  offen.seit = '2026-09-01T00:00:00Z';
  await kv.put('abo:offen@beispiel.de', JSON.stringify(offen));
  await kv.put('token:verwaist', 'aktiv@beispiel.de');
  const env = env_mit(kv);
  const erg = await datenschutz_pflege(env, Date.parse('2026-10-01T00:00:00Z'));
  assert.equal(erg.geloescht, 1);
  assert.ok(await kv.get('abo:aktiv@beispiel.de'));
  assert.equal(await kv.get('abo:offen@beispiel.de'), null);
  assert.equal(await kv.get('token:verwaist'), null);
  assert.equal(await kv.get(`token:${offen.token}`), null);
  assert.equal((await worker.fetch(new Request('http://abos.test/status?token=verwaist'), env)).status, 404);
});

test('Wiederanmeldung: alter Token verliert Berechtigung', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'neu@beispiel.de', consent: '1' });
  const erster = await kv.get('abo:neu@beispiel.de', 'json');
  erster.status = 'unsubscribed';
  erster.abbestellt = new Date().toISOString();
  await kv.put('abo:neu@beispiel.de', JSON.stringify(erster));
  await anmelden(kv, { email: 'neu@beispiel.de', consent: '1' });
  assert.equal(await kv.get(`token:${erster.token}`), null);
  const antwort = await worker.fetch(new Request(`http://abos.test/status?token=${erster.token}`), env_mit(kv));
  assert.equal(antwort.status, 404);
});

test('Abo und Token: TTL für pending/unsubscribed, aktives Abo ohne TTL', async () => {
  const kv = kvLeeren();
  await anmelden(kv, { email: 'ttl@beispiel.de', consent: '1' });
  const pending = await kv.get('abo:ttl@beispiel.de', 'json');
  assert.equal(kv.options.get('abo:ttl@beispiel.de').expirationTtl, 15 * 86400);
  assert.equal(kv.options.get(`token:${pending.token}`).expirationTtl, 15 * 86400);
  await worker.fetch(form_request('/bestaetigung', { token: pending.token }), env_mit(kv));
  assert.equal(kv.options.get('abo:ttl@beispiel.de'), null);
  assert.equal(kv.options.get(`token:${pending.token}`), null);
  await worker.fetch(form_request('/abmeldung', { token: pending.token }), env_mit(kv));
  assert.equal(kv.options.get('abo:ttl@beispiel.de').expirationTtl, 29 * 86400);
  assert.equal(kv.options.get(`token:${pending.token}`).expirationTtl, 29 * 86400);
});

// ------------------------------------------------------------------ Haertung (Audit 14.10.2026)
function mit_kopf(request, kopf) {
  const h = new Headers(request.headers);
  for (const [k, v] of Object.entries(kopf)) h.set(k, v);
  return new Request(request, { headers: h });
}

test('CSRF: POST aus fremdem Origin -> 403, nichts gespeichert (Audit M-02)', async () => {
  const kv = kvLeeren();
  dispatche = [];
  const freilass = fetch_sperr();
  const req = mit_kopf(form_request('/anmeldung', { email: 'csrf@beispiel.de', consent: '1' }), { Origin: 'https://boese.example' });
  const antwort = await worker.fetch(req, env_mit(kv));
  freilass();
  assert.equal(antwort.status, 403);
  assert.equal(await kv.get('abo:csrf@beispiel.de', 'json'), null);
  assert.equal(dispatche.length, 0);
});

test('CSRF: Abmeldung aus fremdem Origin -> 403, Abo bleibt aktiv', async () => {
  const kv = kvLeeren();
  abo_sae(kv, 'opfer@example.de', 'active', 'tok-OPFER');
  const req = mit_kopf(form_request('/abmeldung', { token: 'tok-OPFER' }), { Origin: 'https://boese.example' });
  const antwort = await worker.fetch(req, env_mit(kv));
  assert.equal(antwort.status, 403);
  assert.equal(JSON.parse(kv.map.get('abo:opfer@example.de')).status, 'active');
});

test('CSRF: Site-Origin, Worker-Origin und Mailprogramm (ohne Origin) bleiben erlaubt', async () => {
  const kv = kvLeeren();
  const site = await worker.fetch(mit_kopf(form_request('/anmeldung', { email: 's1@beispiel.de', consent: '1' }), { Origin: 'https://franksfinanzcheck.de' }), env_mit(kv));
  assert.equal(site.status, 200);
  abo_sae(kv, 'o1@example.de', 'active', 'tok-O1');
  const eigen = await worker.fetch(mit_kopf(form_request('/abmeldung', { token: 'tok-O1' }), { Origin: 'http://abos.test' }), env_mit(kv));
  assert.equal(eigen.status, 200);
  abo_sae(kv, 'o2@example.de', 'active', 'tok-O2');
  const mua = await worker.fetch(form_request('/abmeldung', { token: 'tok-O2' }), env_mit(kv));
  assert.equal(mua.status, 200, 'RFC-8058-One-Click aus dem Mailprogramm sendet keinen Origin');
  assert.equal(JSON.parse(kv.map.get('abo:o2@example.de')).status, 'unsubscribed');
});

test('CSRF: Origin "null" nur bei Sec-Fetch-Site same-origin', async () => {
  const kv = kvLeeren();
  abo_sae(kv, 'n1@example.de', 'active', 'tok-N1');
  const fremd = await worker.fetch(mit_kopf(form_request('/abmeldung', { token: 'tok-N1' }), { Origin: 'null' }), env_mit(kv));
  assert.equal(fremd.status, 403, 'sandboxed iframe / data:-URL');
  const eigen = await worker.fetch(mit_kopf(form_request('/abmeldung', { token: 'tok-N1' }), { Origin: 'null', 'Sec-Fetch-Site': 'same-origin' }), env_mit(kv));
  assert.equal(eigen.status, 200);
});

test('Enumeration: neu, pending, aktiv und abgemeldet liefern denselben Antwortkoerper (Audit M-01)', async () => {
  const kv = kvLeeren();
  const neu = await (await anmelden(kv, { email: 'e1@beispiel.de', consent: '1' })).text();
  const pending = await (await anmelden(kv, { email: 'e1@beispiel.de', consent: '1' })).text();
  abo_sae(kv, 'e2@beispiel.de', 'active', 'tok-E2');
  const aktiv = await (await anmelden(kv, { email: 'e2@beispiel.de', consent: '1' })).text();
  abo_sae(kv, 'e3@beispiel.de', 'unsubscribed', 'tok-E3');
  const ab = await (await anmelden(kv, { email: 'e3@beispiel.de', consent: '1' })).text();
  assert.equal(pending, neu);
  assert.equal(aktiv, neu);
  assert.equal(ab, neu);
});

test('Export: Schluessel per Query wird abgelehnt – nur Header (Audit N-01)', async () => {
  const kv = kvLeeren();
  const query = await worker.fetch(new Request(`http://abos.test/export/abonnenten?sluessel=${EXPORT_KEY}`), env_mit(kv));
  assert.equal(query.status, 403);
  const kopf = await worker.fetch(new Request('http://abos.test/export/abonnenten', { headers: { 'X-FF-Key': EXPORT_KEY } }), env_mit(kv));
  assert.equal(kopf.status, 200);
});

test('Sicherheitskopf: CSP, nosniff, DENY, Referrer-Policy auf JSON und HTML', async () => {
  const kv = kvLeeren();
  abo_sae(kv, 'h@example.de', 'active', 'tok-H');
  const antworten = [
    await worker.fetch(new Request('http://abos.test/healthz'), env_mit(kv)),
    await worker.fetch(get_request('/praferenzen?token=tok-H'), env_mit(kv)),
    await worker.fetch(get_request('/abmeldung?token=tok-H'), env_mit(kv)),
    await worker.fetch(new Request('http://abos.test/export/abonnenten'), env_mit(kv)),
  ];
  for (const a of antworten) {
    assert.match(a.headers.get('content-security-policy') || '', /frame-ancestors 'none'/);
    assert.equal(a.headers.get('x-content-type-options'), 'nosniff');
    assert.equal(a.headers.get('x-frame-options'), 'DENY');
    assert.equal(a.headers.get('referrer-policy'), 'same-origin');
  }
});

test('Rate-Limit: Binding RATE_LIMITER entscheidet ohne KV-Schreibzugriff (Audit H-03)', async () => {
  const kv = kvLeeren();
  const schluessel = [];
  const RATE_LIMITER = { async limit({ key }) { schluessel.push(key); return { success: false }; } };
  const antwort = await anmelden(kv, { email: 'rl@beispiel.de', consent: '1' }, { env: { RATE_LIMITER } });
  assert.equal(antwort.status, 429);
  assert.equal(schluessel.length, 1);
  assert.ok(!schluessel[0].includes('1.2.3.4'), 'Schluessel gehasht');
  assert.equal(kv.map.size, 0, 'kein KV-Schreibzugriff');
});

test('Turnstile: Paar aus Secret UND Site-Key prueft – ohne/mit falschem Token abgelehnt, mit gueltigem angemeldet', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv, { TURNSTILE_SECRET: 'ts-geheim', TURNSTILE_SITEKEY: '0x4AAA' });
  let geprueft = null;
  const freilass = fetch_sperr((ziel, opt) => {
    if (new URL(String(ziel)).hostname === 'challenges.cloudflare.com') {
      geprueft = new URLSearchParams(opt.body.toString());
      return new Response(JSON.stringify({ success: geprueft.get('response') === 'gut' }), { status: 200 });
    }
    return new Response(null, { status: 204 });
  });
  const ohne = await worker.fetch(form_request('/anmeldung', { email: 't@beispiel.de', consent: '1' }), env);
  const falsch = await worker.fetch(form_request('/anmeldung', { email: 't@beispiel.de', consent: '1', 'cf-turnstile-response': 'schlecht' }), env);
  assert.equal(await kv.get('abo:t@beispiel.de', 'json'), null);
  const gut = await worker.fetch(form_request('/anmeldung', { email: 't@beispiel.de', consent: '1', 'cf-turnstile-response': 'gut' }), env);
  freilass();
  assert.ok(ohne.status >= 400 && ohne.status < 500);
  assert.ok(falsch.status >= 400 && falsch.status < 500);
  assert.equal(gut.status, 200);
  assert.equal(geprueft.get('secret'), 'ts-geheim');
  assert.equal((await kv.get('abo:t@beispiel.de', 'json')).status, 'pending');
});

test('Turnstile (Paar-Vertrag WF-E813/#809): nur Secret ohne Site-Key heisst „wartet“ – Anmeldung laeuft, Pruefung bleibt aus', async () => {
  // Der Zustand „Secret ohne Widget“ war der Anmelde-Ausfall vom 15.10.2026:
  // JEDER Anmeldeversuch scheiterte an einer Pruefung, die ohne Widget kein
  // Mensch bestehen konnte. Seitdem gilt das Paar als ein Vertrag – der
  // halbgesetzte Zustand darf die Anmeldung NICHT mehr abwürgen, aber er
  // meldet sich laut (healthz „wartet“, Betriebs-Wache, Tagesbudget-Warnung).
  const kv = kvLeeren();
  const env = env_mit(kv, { TURNSTILE_SECRET: 'ts-geheim' });
  let geprueft = false;
  const freilass = fetch_sperr((ziel, opt) => {
    if (new URL(String(ziel)).hostname === 'challenges.cloudflare.com') geprueft = true;
    return new Response(JSON.stringify({ success: false }), { status: 200 });
  });
  const antwort = await worker.fetch(form_request('/anmeldung', { email: 'wartet@beispiel.de', consent: '1' }), env);
  freilass();
  assert.equal(antwort.status, 200, 'Anmeldung darf im Zustand „wartet“ nicht scheitern');
  assert.equal(geprueft, false, 'ohne Site-Key wird keine siteverify-Pruefung ausgeloest');
  assert.equal((await kv.get('abo:wartet@beispiel.de', 'json')).status, 'pending');
  const intern = await (await worker.fetch(export_request('/healthz', { key: EXPORT_KEY }), env)).json();
  assert.equal(intern.turnstile, 'wartet');
  // Und der umgekehrte Halbzustand bleibt sichtbar: Widget ohne Secret.
  const intern2 = await (await worker.fetch(export_request('/healthz', { key: EXPORT_KEY }),
    env_mit(kvLeeren(), { TURNSTILE_SITEKEY: '0x4AAA' }))).json();
  assert.equal(intern2.turnstile, 'inaktiv');
  // Beide Werte zusammen: aktiv.
  const intern3 = await (await worker.fetch(export_request('/healthz', { key: EXPORT_KEY }),
    env_mit(kvLeeren(), { TURNSTILE_SECRET: 'ts-geheim', TURNSTILE_SITEKEY: '0x4AAA' }))).json();
  assert.equal(intern3.turnstile, 'aktiv');
});

test('Feedback: Tagesobergrenze schuetzt das KV-Schreibbudget (Audit H-03)', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv, { FEEDBACK_MAX_PRO_TAG: '2' });
  for (const ip of ['198.51.100.1', '198.51.100.2', '198.51.100.3', '198.51.100.4']) {
    const a = await worker.fetch(feedback_request('pillar-strom-sparen', 'ja', ip), env);
    assert.equal(a.status, 200, 'der Leser sieht nie einen Fehler');
  }
  const stand = await (await worker.fetch(new Request('http://abos.test/feedback?slug=pillar-strom-sparen'), env)).json();
  assert.equal(stand.ja, 2, 'nur bis zur Obergrenze gezaehlt');
  assert.equal([...kv.map.keys()].filter((k) => k.startsWith('fbtag:')).length, 1, 'genau EIN Tagesschluessel');
});

test('Feedback: Cron rollt Vortage in die Summe, Lesen bleibt gleich', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv);
  await worker.fetch(feedback_request('pillar-versicherungen', 'ja', '198.51.100.9'), env);
  await worker.fetch(feedback_request('pillar-versicherungen', 'nein', '198.51.100.10'), env);
  const vorher = await (await worker.fetch(new Request('http://abos.test/feedback?slug=pillar-versicherungen'), env)).json();
  await feedback_aufrollen(env, Date.now() + 36 * 60 * 60 * 1000);
  assert.equal([...kv.map.keys()].filter((k) => k.startsWith('fbtag:')).length, 0, 'Tagesschluessel geloescht');
  const summe = JSON.parse(kv.map.get('feedback:pillar-versicherungen'));
  assert.equal(summe.ja, 1);
  assert.equal(summe.nein, 1);
  const nachher = await (await worker.fetch(new Request('http://abos.test/feedback?slug=pillar-versicherungen'), env)).json();
  assert.equal(nachher.ja, vorher.ja);
  assert.equal(nachher.nein, vorher.nein);
  // Wiederholbar: ein zweiter Lauf zaehlt nichts doppelt.
  await feedback_aufrollen(env, Date.now() + 36 * 60 * 60 * 1000);
  assert.equal(JSON.parse(kv.map.get('feedback:pillar-versicherungen')).ja, 1);
});

test('Datenschutz-Pflege: Alt-IP/UA im Abo-Datensatz werden entfernt, Nachweis bleibt (Audit N-04)', async () => {
  const kv = kvLeeren();
  abo_sae(kv, 'alt@example.de', 'active', 'tok-ALT');
  await datenschutz_pflege(env_mit(kv), Date.now());
  const nachher = JSON.parse(kv.map.get('abo:alt@example.de'));
  assert.equal(nachher.status, 'active');
  assert.ok(!nachher.ip, 'keine IP mehr im Abo');
  assert.ok(!JSON.stringify(nachher).includes('1.2.3.4'), 'IP auch nicht in Unterobjekten');
});

// ------------------------------------------------- Schutzwachen (Audit 15.10.2026)
test('export: erfolgreiche Aufrufe und begrenzte 403-Protokollierung (F-08)', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv);
  menge_speicher_zuruecksetzen();
  export_speicher_zuruecksetzen();
  await worker.fetch(export_request('/export/abonnenten', { key: 'falsch-falsch-falsch' }), env);
  await worker.fetch(export_request('/export/pending', { key: 'noch-ein-falscher-schluessel' }), env);
  await worker.fetch(export_request('/export/pending', { key: EXPORT_KEY }), env);
  const protokoll = [...kv.map.keys()].filter((k) => k.startsWith('exportlog:'));
  assert.equal(protokoll.length, 2, 'Deny-Bucket je Stunde plus erfolgreicher Export');
  const eintraege = protokoll.map((k) => JSON.parse(kv.map.get(k)));
  assert.equal(eintraege.filter((e) => e.status === 403).length, 1,
    '403-Sturm darf nicht pro Anfrage KV schreiben');
  assert.ok(eintraege.some((e) => e.route === '/export/pending' && e.status === 200));
  // Der Abdruck ist ein Kurz-Hash – NIE der Schluessel selbst.
  for (const e of eintraege) {
    assert.match(e.key, /^[0-9a-f]{8}$/);
    assert.ok(!JSON.stringify(e).includes(EXPORT_KEY));
  }
  // Sichtbar fuer den Betreiber (healthz mit Schluessel), verborgen fuer alle anderen.
  const oeffentlich = await (await worker.fetch(new Request('http://abos.test/healthz'), env)).json();
  assert.ok(!('exporte' in oeffentlich), 'Betriebsbild nur mit Schluessel');
  assert.ok(!('budget' in oeffentlich), 'Budgetstand nur mit Schluessel');
  const intern = await (await worker.fetch(export_request('/healthz', { key: EXPORT_KEY }), env)).json();
  assert.equal(intern.exporte.length, 2);
  assert.equal(intern.schluesselrollen, 'gemeinsam');
  assert.equal(intern.turnstile, 'inaktiv');
  assert.equal(intern.budget.anmeldung_heute, 0);
});

test('Export-Schluessel: Konstantzeitvergleich, getrennte Rollen, kein Rueckfall (F-08)', async () => {
  const kv = kvLeeren();
  const nur_lesen = env_mit(kv);
  const getrennt = env_mit(kv, { EXPORT_KEY_WRITE: 'schreib-key-32-z------------' });
  const gleicher_schluessel = env_mit(kv, { EXPORT_KEY_WRITE: EXPORT_KEY });
  assert.equal(await schluessel_pruefen(nur_lesen, EXPORT_KEY), true);
  assert.equal(await schluessel_pruefen(nur_lesen, EXPORT_KEY.slice(0, -1)), false,
    'ein Zeichen weniger ist nicht der Schluessel');
  assert.equal(await schluessel_pruefen(nur_lesen, ''), false);
  assert.equal(await schluessel_pruefen(env_mit(kv), 'kurz'), false);
  // Ohne separaten Schreibschluessel ist die Write-Rolle gesperrt.
  assert.equal(await schreibschluessel_pruefen(nur_lesen, EXPORT_KEY), false);
  // Identische Secrets zaehlen ebenfalls nicht als Trennung.
  assert.equal(await schreibschluessel_pruefen(gleicher_schluessel, EXPORT_KEY), false);
  // Getrennt: der Leseschluessel oeffnet den Schreibweg NICHT.
  assert.equal(await schreibschluessel_pruefen(getrennt, EXPORT_KEY), false);
  assert.equal(await schreibschluessel_pruefen(getrennt, 'schreib-key-32-z------------'), true);
  // Der Abdruck ist stabil, kurz und verraet den Wert nicht.
  const abdruck = await schluessel_fingerabdruck(EXPORT_KEY);
  assert.match(abdruck, /^[0-9a-f]{8}$/);
  assert.ok(!EXPORT_KEY.includes(abdruck));
  assert.equal(abdruck, await schluessel_fingerabdruck(EXPORT_KEY));
  assert.notEqual(abdruck, await schluessel_fingerabdruck('anderer-schluessel-32-z------'));
});

test('Anmeldung: Tagesbudget deckelt die Schreibzugriffe (F-03)', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv, { ANMELDUNG_MAX_PRO_TAG: '2' });
  const freilass = fetch_sperr();
  const a = await worker.fetch(form_request('/anmeldung', { email: 'eins@beispiel.de', consent: '1' }), env);
  const b = await worker.fetch(form_request('/anmeldung', { email: 'zwei@beispiel.de', consent: '1' }), env);
  const c = await worker.fetch(form_request('/anmeldung', { email: 'drei@beispiel.de', consent: '1' }), env);
  freilass();
  assert.equal(a.status, 200);
  assert.equal(b.status, 200);
  assert.equal(c.status, 503, 'die dritte Anmeldung wird fail-closed abgelehnt');
  assert.equal(await kv.get('abo:drei@beispiel.de', 'json'), null, 'nichts geschrieben');
  const heute = new Date().toISOString().slice(0, 10);
  assert.equal(await kv.get(`budget:anmeldung:${heute}`), '2');
  // Genau EINE laute Meldung je Stunde – der Melder darf das Budget nicht fressen.
  assert.ok(kv.map.has(`warn:anmeldung:${heute}`));
  const text = await c.text();
  assert.ok(!text.includes('budget') && !text.includes('Kontingent') && !text.includes('KV'),
    'die Antwort verraet keine Betriebsinterna');
  assert.match(text, /ausgelastet/);
  // Die Abmeldung bleibt erreichbar (Art. 7 Abs. 3 DSGVO) – sie hat kein Budget.
  await kv.put('abo:eins@beispiel.de', JSON.stringify({
    email: 'eins@beispiel.de', norm: 'eins@beispiel.de', status: 'active',
    token: 't'.repeat(32), themen: [], seit: new Date().toISOString(),
  }));
  await kv.put(`token:${'t'.repeat(32)}`, 'eins@beispiel.de');
  const weg = await worker.fetch(form_request('/abmeldung', { token: 't'.repeat(32) }), env);
  assert.equal(weg.status, 200, 'Abmeldung darf nie am Tagesbudget scheitern');
});

test('Tagesbudget: zaehlt, kappt bei 0 nicht und kommt ohne Zahl klar (F-03)', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv);
  const erster = await tagesbudget_nehmen(env, 'anmeldung', 2);
  const zweiter = await tagesbudget_nehmen(env, 'anmeldung', 2);
  const dritter = await tagesbudget_nehmen(env, 'anmeldung', 2);
  assert.deepEqual([erster.ok, zweiter.ok, dritter.ok], [true, true, false]);
  assert.equal(dritter.stand, 2);
  assert.equal(dritter.maximum, 2);
  assert.equal(await tagesbudget_stand(env, 'anmeldung'), 2);
  // maximum = 0 heisst „kein Deckel" – dann darf das Budget nie blocken.
  const ohne = await tagesbudget_nehmen(env, 'ohne-deckel', 0);
  assert.equal(ohne.ok, true);
  // Der Standarddeckel muss deutlich unter dem Schreibkontingent liegen:
  // eine Anmeldung kostet vier Schreibzugriffe.
  assert.ok(ANMELDUNG_MAX_PRO_TAG_DEFAULT * 4 <= 1000,
    'Standarddeckel sprengt das KV-Schreibkontingent des Free-Plans');
});

test('Mengenklassen: jede Route hat eine Klasse (F-03)', () => {
  assert.equal(limit_klasse('/bestaetigung', 'GET'), 'lesen');
  assert.equal(limit_klasse('/praferenzen', 'GET'), 'lesen');
  assert.equal(limit_klasse('/status', 'GET'), 'lesen');
  assert.equal(limit_klasse('/feedback', 'GET'), 'feedback');
  assert.equal(limit_klasse('/feedback', 'POST'), 'feedback');
  assert.equal(limit_klasse('/export/abonnenten', 'GET'), 'export');
  assert.equal(limit_klasse('/export/versuch', 'POST'), 'export');
  // Die POST-Routen mit eigener, strengerer Pruefung bleiben bei ihren Limits.
  assert.equal(limit_klasse('/anmeldung', 'POST'), null);
  assert.equal(limit_klasse('/abmeldung', 'POST'), null);
});

test('Mengenzaehler im Speicher: je Verbindung eigenes Fenster (F-03)', () => {
  const jetzt = 1_760_000_000_000;
  assert.equal(menge_speicher_pruefen('probe|1.2.3.4', 2, jetzt), true);
  assert.equal(menge_speicher_pruefen('probe|1.2.3.4', 2, jetzt), true);
  assert.equal(menge_speicher_pruefen('probe|1.2.3.4', 2, jetzt), false, 'dritter Aufruf gebremst');
  assert.equal(menge_speicher_pruefen('probe|5.6.7.8', 2, jetzt), true,
    'andere Verbindung, eigenes Fenster');
  assert.equal(menge_speicher_pruefen('probe|1.2.3.4', 2, jetzt + 60_001), true,
    'neues Minutenfenster beginnt wieder bei eins');
});

test('Mengenbegrenzung greift auch ohne Binding (Notpfad, F-03)', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv, { RATE_LIMIT_LESEN: '2' });
  menge_speicher_zuruecksetzen();
  const hole = () => worker.fetch(new Request('http://abos.test/status?token=egal', {
    headers: { accept: 'application/json', 'cf-connecting-ip': '203.0.113.9' },
  }), env);
  const eins = await hole();
  const zwei = await hole();
  const drei = await hole();
  assert.equal(eins.status, 404, 'unbekannter Token – die Anfrage wird aber bearbeitet');
  assert.equal(zwei.status, 404);
  assert.equal(drei.status, 429, 'ab der Grenze wird gebremst');
  // Eine andere Verbindung hat ihr eigenes Fenster.
  const andere = await worker.fetch(new Request('http://abos.test/status?token=egal', {
    headers: { accept: 'application/json', 'cf-connecting-ip': '198.51.100.4' },
  }), env);
  assert.equal(andere.status, 404);
});

test('Log-Hygiene: die E-Mail-Adresse steht nie im Klartext-Log (F-05)', async () => {
  const kv = kvLeeren();
  // Defekter Bestand (unbekannter Status) ist genau der Pfad, der vorher loggte.
  await kv.put('abo:defekt@beispiel.de', JSON.stringify({
    email: 'defekt@beispiel.de', norm: 'defekt@beispiel.de', status: 'kaputt',
    token: 'x'.repeat(32), seit: new Date().toISOString(), themen: [],
  }));
  const meldungen = [];
  const zuvor = console.warn;
  console.warn = (...args) => meldungen.push(args.join(' '));
  try {
    const freilass = fetch_sperr();
    const antwort = await worker.fetch(
      form_request('/anmeldung', { email: 'defekt@beispiel.de', consent: '1' }), env_mit(kv));
    freilass();
    assert.equal(antwort.status, 500, 'unbekannter Zustand bleibt fail-closed');
  } finally {
    console.warn = zuvor;
  }
  assert.ok(meldungen.length >= 1, 'der Fall wird gemeldet');
  const gesamt = meldungen.join('\n');
  assert.ok(!gesamt.includes('defekt@beispiel.de'), 'keine Adresse im Log');
  assert.match(gesamt, /sha256:[0-9a-f]{32}/);
});

test('Abmeldung mit Token: eigener Mengenzaehler (F-03)', async () => {
  const kv = kvLeeren();
  const env = env_mit(kv, { RATE_LIMITER: undefined });
  const stoesse = [];
  for (let i = 0; i < 8; i += 1) {
    stoesse.push(await worker.fetch(new Request(
      `http://abos.test/abmeldung?token=${'a'.repeat(32)}`,
      { headers: { 'cf-connecting-ip': '203.0.113.77', accept: 'application/json' } }), env));
  }
  const zuviele = stoesse.filter((r) => r.status === 429);
  assert.ok(zuviele.length >= 1, 'nach fuenf Rateversuchen wird gebremst');
  // Ein anderer Token-Rater-Kanal (POST aus dem Formular) hat sein eigenes Limit.
  const form = await worker.fetch(form_request('/abmeldung', { email: 'niemand@beispiel.de' },
    { ip: '203.0.113.77' }), env);
  assert.ok([200, 429].includes(form.status), 'Formularweg bleibt funktionsfaehig');
});
