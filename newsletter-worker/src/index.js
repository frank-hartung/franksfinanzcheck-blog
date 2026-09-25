/**
 * ff-newsletter – der Newsletter-Hinterhof von franksfinanzcheck.de
 * ================================================================
 * Ein Cloudflare Worker (Free Plan) als EIGENER Endpunkt für den
 * Newsletter – ersetzt den Brevo-Server, an den das Formular bisher
 * POSTete. Alles, was hier passiert:
 *
 *   POST /anmeldung      Formular-Abgabe (Honeypot, Zeitfalle, Consent,
 *                        E-Mail-Prüfung, Deduplizierung, Rate-Limit)
 *   POST /bestaetigung   Double-Opt-In: Token bestaetigt die Adresse
 *   POST /abmeldung      Abmeldung per Token (Body ODER Query – RFC 8058
 *                        One-Click-POST traegt den Token in der URL) ODER
 *                        per E-Mail-Feld (Formular ohne Token, immer 200)
 *   GET  /abmeldung      One-Klick mit Token; ohne Token das Formular
 *   POST /praferenzen    Themenwahl pro Abo (Token + themen[])
 *   GET  /status         Token -> {status, themen} (ohne Adresse!)
 *   GET  /healthz        Lebendigkeits-Pruefung fuer die Wache (+ `takt`:
 *                        letzter Dispatch je Cron-Takt, ohne Adressen)
 *   GET  /export/…       NUR mit Secret (X-FF-Key / ?sluessel=):
 *                        Abonnenten-Liste, Pending-Liste, Eintrag nach
 *                        Token, Eintrag nach E-Mail (/export/kontakt),
 *                        Versand-Versuche melden (Catch-up).
 *   scheduled()          TAKTGEBER (seit 25.09.2026): Cloudflare Cron
 *                        Triggers starten den Digest (Di/Fr 04:30 UTC),
 *                        die Kadenz-Wache (05:05 UTC) und den Nachgang
 *                        (stuendlich) per workflow_dispatch – weil GitHubs
 *                        eigener Scheduler an diesem Repo Stunden zu spaet
 *                        oder gar nicht feuert. Details: Abschnitt „Taktgeber“.
 *
 * DATEN (Workers KV, Binding `ABO`, EU-Region in deinem CF-Account):
 *   abo:{email-norm}     Abo-Status, Token, Themen, Zeitstempel
 *   token:{token}        Rueckweg Token -> email-norm
 *   nachweis:{sha256}    Einwilligungsnachweis (IP, UA, Zeitpunkt), TTL 3 Jahre
 *   rat:{sha256(ip)}     Rate-Limit-Zaehler (15 Min)
 *   metrik:falle        Bot-Fallen-Treffer (1 Tag)
 *
 * BESTAETIGUNGS-MAIL: der Worker selbst versendet KEINE Mails (er hat
 * kein SMTP und soll keine Mail-Provider-Keys traegen). Er loest den
 * GitHub-Actions-Workflow `newsletter-lifecycle.yml` aus (workflow_dispatch,
 * Input = Token NUR – keine Adresse im Event). Der Workflow holt die
 * Adresse ueber /export/token und versendet ueber scripts/newsletter_versand.py.
 * Schlägt der Dispatch aus (Rate-Limit, GitHub-Wartung), geht nichts
 * verloren: der staendliche Nachgang (schedule) des Workflows versendet
 * offene Bestätigungen nach (max. 3 Versuche, dann abgelaufen).
 *
 * KEINE Abhaengigkeiten, KEIN Build-Schritt: purer ES-Module-Worker.
 * Tests: `node --test test/` (mockt env, kein Cloudflare-Login benoetigt).
 */

// ---------------------------------------------------------------- Konstanten
const TTL_NACHWEIS_SEK = 1095 * 24 * 60 * 60; // 3 Jahre (Art. 7 DSGVO)
const TTL_RATE_SEK = 15 * 60;
const MAX_ANMELDUNGEN_PRO_IP = 5;
const BESTAETIGUNG_TAGE_DEFAULT = 14;
const MAX_VERSEND_VERSUCHE = 3;
const TOKEN_LAENGE = 24; // 192 Bit, base64url
const STAND_ORIGIN = 'https://franksfinanzcheck.de';
const HTML_KOPF = '<!doctype html><html lang="de"><head><meta charset="utf-8">' +
  '<meta name="viewport" content="width=device-width,initial-scale=1">' +
  '<title>FranksFinanzcheck – Newsletter</title><style>' +
  'body{margin:0;background:#FAFCFB;color:#2E2E33;font:16px/1.55 system-ui,Segoe UI,Roboto,sans-serif}' +
  '.k{max-width:520px;margin:10vh auto 0;padding:0 20px}' +
  'h1{color:#0E5A43;font-size:22px;line-height:1.3}' +
  'a{color:#0E5A43}' +
  'form{margin:14px 0}' +
  '.btn{display:inline-block;background:#0E5A43;color:#fff;border:0;border-radius:8px;padding:12px 24px;font:600 15px/1.3 system-ui,Segoe UI,Roboto,sans-serif;cursor:pointer}' +
  'fieldset{border:1px solid #DCE6E1;border-radius:8px;margin:12px 0;padding:12px 14px}' +
  'legend{color:#0E5A43;font-weight:600;font-size:14px;padding:0 6px}' +
  '.chip{display:block;margin:8px 0;font-size:15px}' +
  '.chip input{margin-right:8px}' +
  '.hinweis{color:#6C6C6C;font-size:13px;margin:10px 0}' +
  '.ok{color:#0E5A43;font-weight:600}' +
  '.fehler{color:#8C2F39}' +
  '</style></head><body><div class="k">';
const HTML_FUSS = '</div></body></html>';

// ---------------------------------------------------------------- Helfer
/** CORS: nur die Site-Origin(s) dürfen mit dem Worker sprechen. */
function cors(umgebung) {
  const herkunft = String((umgebung && umgebung.SITE_ORIGIN) || STAND_ORIGIN).split(',')[0].trim();
  return {
    'Access-Control-Allow-Origin': herkunft,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Accept, X-FF-Key',
    'Access-Control-Max-Age': '86400',
    'Cache-Control': 'no-store',
  };
}

function json(ereignis, kod = 200, env = null, extra = {}) {
  return new Response(JSON.stringify(ereignis), {
    status: kod,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...cors(env), ...extra },
  });
}

function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

/** Themen-Labels fuer die Praeferenzsseite (Env als JSON id->Label;
 *  Fallback = die ID selbst – lesbar, aber nicht hübsch). */
function themen_label(env, id) {
  try {
    const roh = String((env && env.THEMEN_LABELS) || '').trim();
    if (roh) {
      const m = JSON.parse(roh);
      if (m && typeof m === 'object' && typeof m[id] === 'string' && m[id].trim()) {
        return m[id].trim();
      }
    }
  } catch (e) { /* Fallback unten */ }
  return String(id);
}

function themen_liste(env) {
  return String((env && env.THEMEN_IDS) || '').split(',').map((t) => t.trim()).filter(Boolean);
}

function htmlSeite(titel, text, url, env, kod = 200) {
  const e = (s) => String(s).replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const seite = HTML_KOPF +
    `<h1>${e(titel)}</h1><p>${e(text)}</p>` +
    `<p><a href="${e(url)}">Zur&uuml;ck zu FranksFinanzcheck</a></p>` +
    HTML_FUSS;
  return new Response(seite, {
    status: kod, headers: { 'Content-Type': 'text/html; charset=utf-8', ...cors(env) },
  });
}

function antwort_mit(status, text, env, request, kod = 200) {
  if (wantHtml(request)) {
    let titel = 'Deine Anmeldung';
    if (status === 'fehler') titel = 'Etwas ist schiefgelaufen';
    if (status === 'angemeldet' || status === 'wieder-angemeldet') titel = 'Fast geschafft';
    if (status === 'bestaetigt') titel = 'Bestätigt!';
    if (status === 'abgemeldet') titel = 'Abgemeldet';
    return htmlSeite(titel, text, STAND_ORIGIN + '/newsletter/', env, kod);
  }
  return json({ status, text }, kod, env);
}

function fehler(kod, text, env, request) {
  if (wantHtml(request)) {
    return htmlSeite('Etwas ist schiefgelaufen', text, STAND_ORIGIN + '/newsletter/', env, kod);
  }
  return json({ status: 'fehler', text }, kod, env);
}

/** Browser ohne JS senden Accept: text/html – dafür die HTML-Antwort. */
function wantHtml(request) {
  const accept = String(request.headers.get('accept') || '');
  if (accept.includes('application/json')) return false;
  return accept.includes('text/html') || accept === '' || accept === '*/*';
}

function vorabfrage(env) {
  return new Response(null, { status: 204, headers: cors(env) });
}

function token_neu() {
  const bytes = new Uint8Array(TOKEN_LAENGE);
  crypto.getRandomValues(bytes);
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

async function sha256_kurz(text) {
  const daten = new TextEncoder().encode(String(text));
  const digest = await crypto.subtle.digest('SHA-256', daten);
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, '0')).join('').slice(0, 32);
}

/** Konstantzeit-Vergleich fuer das Export-Secret (kein Zeitaugriff). */
async function schluessel_pruefen(env, angebot) {
  const sollen = String((env && env.EXPORT_KEY) || '');
  const ist = String(angebot || '');
  if (!sollen || !ist || sollen.length !== ist.length) return false;
  const a = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(sollen));
  const b = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(ist));
  const ua = new Uint8Array(a);
  const ub = new Uint8Array(b);
  let unterschied = ua.length ^ ub.length;
  for (let i = 0; i < Math.max(ua.length, ub.length); i += 1) {
    unterschied |= (ua[i % ua.length] || 0) ^ (ub[i % ub.length] || 0);
  }
  return unterschied === 0;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function email_norm(adresse) {
  return String(adresse || '').trim().toLowerCase();
}

/**
 * Formular-Koerper lesen: x-www-form-urlencoded (JS-Fetch UND der
 * klassische POST ohne JS) oder JSON (Tests/Dev). Wiederholte Felder
 * (themen[]) werden gesammelt.
 */
async function koerper_lesen(request) {
  const ct = String(request.headers.get('content-type') || '');
  const roh = await request.text();
  if (ct.includes('application/json') || roh.trimStart().startsWith('{')) {
    try {
      const daten = JSON.parse(roh);
      const aus = {};
      for (const [k, v] of Object.entries(daten || {})) {
        aus[k] = Array.isArray(v) ? v : [v];
      }
      return aus;
    } catch (e) {
      return null;
    }
  }
  const aus = {};
  for (const [k, v] of new URLSearchParams(roh)) {
    (aus[k] = aus[k] || []).push(v);
  }
  return aus;
}

const erstein = (dat, schl) => String((dat[schl] || [''])[0] || '').trim();

// ---------------------------------------------------------------- KV-Zugriff
async function abo_lesen(kv, norm) {
  return (await kv.get(`abo:${norm}`, 'json')) || null;
}

async function abo_schreiben(kv, eintrag) {
  await kv.put(`abo:${eintrag.norm}`, JSON.stringify(eintrag));
  await kv.put(`token:${eintrag.token}`, eintrag.norm);
}

async function nachweis_schreiben(kv, eintrag) {
  const haetti = await sha256_kurz(`ff-nl|${eintrag.norm}|v1`);
  await kv.put(`nachweis:${haetti}`, JSON.stringify({
    email: eintrag.email,
    ip: eintrag.ip || null,
    user_agent: eintrag.user_agent || null,
    seite: eintrag.seite || null,
    eingewilligt: eintrag.seit,
    bestaetigt: eintrag.bestaetigt || null,
    version: 1,
  }), { expirationTtl: TTL_NACHWEIS_SEK });
}

async function liste_mit_prefix(kv, prefix) {
  const alle = [];
  let cursor;
  do {
    const seite = await kv.list({ prefix, cursor });
    for (const key of seite.keys) alle.push(key.name);
    cursor = seite.list_complete ? undefined : seite.cursor;
  } while (cursor);
  return alle;
}

// ---------------------------------------------------------------- Trigger
/**
 * Ein GitHub-Actions-Workflow per `workflow_dispatch` starten. Der PAT
 * braucht dafuer die feingranulare Berechtigung **Actions: Read and
 * write** (NICHT „Workflows“ – das ist das Recht, Workflow-DATEIEN zu
 * aendern, und reicht fuer den Dispatch nicht; Quelle:
 * docs.github.com/rest/actions/workflows#create-a-workflow-dispatch-event).
 * Antwort 204 = angenommen. Alles andere wird als {ok:false, status}
 * zurueckgegeben – nie geworfen: der Aufrufer entscheidet, was ein
 * Ausfall bedeutet (Anmeldung: Nachgang deckt ab; Takt: Retry + Protokoll).
 */
async function github_dispatch(env, workflow, inputs) {
  if (!env.GITHUB_PAT || !env.GITHUB_REPO) return { ok: false, status: 0, warum: 'kein-token' };
  const ziel = `https://api.github.com/repos/${env.GITHUB_REPO}/actions/workflows/${workflow}/dispatches`;
  try {
    const antwort = await fetch(ziel, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.GITHUB_PAT}`,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json',
        'User-Agent': 'ff-newsletter-worker',
      },
      body: JSON.stringify({ ref: env.GITHUB_REF || 'main', inputs }),
    });
    return { ok: antwort.status === 204, status: antwort.status };
  } catch (e) {
    return { ok: false, status: 0, warum: String((e && e.message) || e) };
  }
}

async function dispatch_bestuerung(env, token) {
  // NUR der Token – keine Adresse im Event
  return github_dispatch(env, env.GITHUB_WORKFLOW || 'newsletter-lifecycle.yml',
    { aktion: 'bestaetigung', token });
}

// ---------------------------------------------------------------- Taktgeber
// WARUM (Freitag, 25.09.2026 – gemessen, nicht vermutet): GitHubs
// `schedule`-Ereignisse kamen an diesem Repo 5–5,5 Stunden zu spaet oder
// GAR NICHT. Der 04:30-Cron des Newsletter-Daily blieb aus; die Kadenz-
// Wache (08:11 UTC), die genau das auffangen sollte, hatte seit ihrer
// Erstellung NULL Laeufe – sie hing am selben Scheduler. Dienstag 23.09.
// dasselbe Bild. Ein Netz, das am selben Haken haengt wie die Last, ist
// kein Netz.
//
// Cloudflare Cron Triggers feuern auf die Minute (UTC). Der Worker ist
// deshalb der TAKTGEBER des Newsletters: er startet die Workflows per
// workflow_dispatch – mit EXAKT der Freigabestufe des GitHub-Crons
// (`planmaessig=true`), nicht mehr. Er versendet weiterhin keine Mail,
// kennt keine Adressen im Dispatch und keinen Mail-Key.
//
// Drei Netze uebereinander, alle idempotent (der Digest bucht den Termin
// und meldet „Termin belegt“, kommt ein zweiter Lauf):
//   1. 04:30 UTC Di/Fr  → newsletter-daily.yml (planmaessig)  – der Versand
//   2. 05:05 UTC Di/Fr  → newsletter-cadence.yml              – zaehlt nach,
//      holt nach, wird laut (Fehler-Alerting), wenn Nachholen unmoeglich ist
//   3. GitHubs eigene Crons bleiben stehen (kommen sie verspaetet, finden
//      sie einen belegten Termin vor)
// Dazu stuendlich :17 der Nachgang offener Bestaetigungen (Lifecycle) –
// derselbe Takt, den der GitHub-Cron verspricht und selten haelt.
//
// Cloudflare-Wochentage sind 1=SO..7=SA (Quartz), NICHT Unix (0/7=SO).
// „2,5“ waere hier Mo/Do. Deshalb stehen die Tage als Namen: TUE,FRI.
// wrangler.toml [triggers].crons muss EXAKT diese Schluessel tragen – der
// Test `taktgeber: wrangler.toml und TAKT decken sich` haelt beides
// deckungsgleich. Ein Cron, der feuert, aber hier keinen Eintrag hat,
// wird protokolliert und ignoriert (kein blinder Dispatch).
const TAKT = {
  '30 4 * * TUE,FRI': {
    name: 'digest', workflow: 'newsletter-daily.yml',
    inputs: { planmaessig: 'true', tage: '7' },
  },
  '5 5 * * TUE,FRI': {
    name: 'kadenz', workflow: 'newsletter-cadence.yml',
    inputs: {},
  },
  '17 * * * *': {
    name: 'nachgang', workflow: 'newsletter-lifecycle.yml',
    inputs: { aktion: 'nachgang', token: '' },
  },
};
const TAKT_VERSUCHE = 3;
const TAKT_PAUSEN_MS = [5000, 20000]; // Wartezeit zaehlt nicht als CPU-Zeit
const TAKT_TTL_SEK = 45 * 24 * 60 * 60; // 45 Tage: die Wache liest den letzten Takt

function takt_fuer(cron) {
  return TAKT[String(cron || '').trim()] || null;
}

async function takt_protokoll(env, name, eintrag) {
  try {
    await env.ABO.put(`takt:${name}`, JSON.stringify(eintrag), { expirationTtl: TAKT_TTL_SEK });
  } catch (e) { /* Protokoll darf den Takt nicht brechen */ }
}

async function takt_lesen(env) {
  const aus = {};
  for (const t of Object.values(TAKT)) {
    try {
      const roh = await env.ABO.get(`takt:${t.name}`, 'json');
      if (roh) aus[t.name] = roh;
    } catch (e) { /* fehlender Eintrag = nie gefeuert */ }
  }
  return aus;
}

/**
 * Ein Takt-Ereignis ausfuehren: Workflow dispatchen, bis zu 3 Versuche
 * (GitHub-API-Hänger, 5xx, Rate-Limit), Ergebnis im KV protokollieren.
 * `schlafen` ist injizierbar (Tests warten nicht wirklich).
 */
async function takt_ausfuehren(env, cron, geplant, schlafen = (ms) => new Promise((r) => setTimeout(r, ms))) {
  const takt = takt_fuer(cron);
  const jetzt = new Date().toISOString();
  if (!takt) {
    console.warn(`ff-newsletter takt: unbekannter Cron „${cron}“ – kein Dispatch`);
    await takt_protokoll(env, 'unbekannt', { ts: jetzt, cron: String(cron || ''), status: 'ignoriert' });
    return { ok: false, status: 0, name: 'unbekannt', warum: 'unbekannter-cron' };
  }
  let ergebnis = { ok: false, status: 0 };
  let versuche = 0;
  for (let i = 0; i < TAKT_VERSUCHE; i += 1) {
    versuche = i + 1;
    ergebnis = await github_dispatch(env, takt.workflow, takt.inputs);
    if (ergebnis.ok) break;
    // 401/403/404 wiederholen sich nicht von allein (PAT, Rechte, Pfad) –
    // sofort protokollieren statt sinnlos warten.
    if ([401, 403, 404].includes(ergebnis.status)) break;
    if (i + 1 < TAKT_VERSUCHE) await schlafen(TAKT_PAUSEN_MS[Math.min(i, TAKT_PAUSEN_MS.length - 1)]);
  }
  const eintrag = {
    ts: jetzt,
    geplant: geplant ? new Date(geplant).toISOString() : null,
    cron,
    workflow: takt.workflow,
    status: ergebnis.ok ? 'dispatched' : 'fehlgeschlagen',
    http: ergebnis.status,
    versuche,
    warum: ergebnis.ok ? null : (ergebnis.warum || `HTTP ${ergebnis.status}`),
  };
  await takt_protokoll(env, takt.name, eintrag);
  if (!ergebnis.ok) {
    console.warn(`ff-newsletter takt ${takt.name}: Dispatch fehlgeschlagen (${eintrag.warum}, ${versuche} Versuche)`);
  }
  return { ...ergebnis, name: takt.name, versuche };
}

async function falle_zahlen(env) {
  try {
    const roh = await env.ABO.get('metrik:falle', 'json');
    const z = (roh && Number(roh.z)) || 0;
    await env.ABO.put('metrik:falle', JSON.stringify({ z: z + 1, ts: Date.now() }), { expirationTtl: 86400 });
  } catch (e) { /* Zählen darf die Anmeldung nie brechen */ }
}

// ---------------------------------------------------------------- Routen
async function health(env) {
  let kv_ok = false;
  try {
    await env.ABO.get('healthz');
    kv_ok = true;
  } catch (e) { kv_ok = false; }
  // `takt`: der letzte Dispatch je Takt (digest/kadenz/nachgang) – ohne
  // Adressen, ohne Secrets. Die Zustellbarkeits-Wache (C8) liest hier, ob
  // der Taktgeber am letzten Versandtag wirklich gefeuert hat. Fehlt der
  // Schluessel ganz, laeuft eine Worker-Version ohne Cron-Triggers.
  const takt = kv_ok ? await takt_lesen(env) : {};
  return json({
    ok: kv_ok, ts: new Date().toISOString(), kv: kv_ok ? 'ok' : 'fehler',
    takt: { crons: Object.keys(TAKT), letzte: takt },
  }, kv_ok ? 200 : 503, env, { 'Cache-Control': 'no-store' });
}

async function anmeldung(request, env, url) {
  const daten = await koerper_lesen(request);
  if (!daten) return fehler(400, 'Der Formularinhalt war nicht lesbar – bitte erneut versuchen.', env, request);

  const email = email_norm(erstein(daten, 'email'));
  const consent = erstein(daten, 'consent') === '1' || erstein(daten, 'consent') === 'true';
  const felle = erstein(daten, 'website');
  const zeitfalle = Number(erstein(daten, '_zeit') || 0);
  // `themen[]` ist der Feldname im HTML des Anmelde-Formulars (Hugo rendert
  // `name="{{ feld_themen }}[]"`), `themen` der reine POST-Weg. Beides muss
  // ankommen – sonst verliert die Anmeldung die Themenwahl still.
  const themen_r = (daten.themen || daten['themen[]'] || [])
    .map((t) => String(t).trim()).filter(Boolean);
  const seite = url.searchParams.get('quelle') || String(env.SITE_ORIGIN || STAND_ORIGIN).split(',')[0].trim();
  const ip = String(request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for') || '').split(',')[0].trim();
  const ua = String(request.headers.get('user-agent') || '').slice(0, 300);

  // Bot-Falle und Zeitfalle: still „ok“, aber nichts speichern – ein
  // Angreifer soll aus der Rueckmeldung nicht mehr lernen als ein Mensch.
  if (felle || (zeitfalle > 0 && Date.now() - zeitfalle < 1500)) {
    await falle_zahlen(env);
    return antwort_mit('ok', 'Danke – bitte sieh in dein Postfach.', env, request);
  }
  if (!EMAIL_RE.test(email) || email.length > 254) {
    return antwort_mit('fehler', 'Die E-Mail-Adresse sieht nicht gültig aus – bitte Adresse prüfen (z. B. du@beispiel.de).', env, request, 400);
  }
  if (!consent) {
    return antwort_mit('fehler', 'Ohne das Einverstaendnis-Haekchen duerfen wir keine Mail schicken – bitte haekchen setzen und erneut absenden.', env, request, 400);
  }

  // Rate-Limit pro IP (KV, 15-Min-Fenster): mehr als 5 = Botmuster.
  const ip_key = `rat:${await sha256_kurz(ip || 'unbekannt')}`;
  const rate = (await env.ABO.get(ip_key, 'json')) || { z: 0 };
  if (rate.z >= MAX_ANMELDUNGEN_PRO_IP) {
    return antwort_mit('fehler', 'Zu viele Anmelde-Versuche in kurzer Zeit. Bitte in ein paar Minuten erneut versuchen – oder schreib eine Mail an kontakt@franksfinanzcheck.de.', env, request, 429);
  }
  await env.ABO.put(ip_key, JSON.stringify({ z: rate.z + 1, ts: Date.now() }), { expirationTtl: TTL_RATE_SEK });

  const jetzt = new Date().toISOString();
  const bestehend = await abo_lesen(env.ABO, email);
  let eintrag;
  let status;
  let text;

  if (!bestehend) {
    eintrag = {
      email, norm: email, status: 'pending', token: token_neu(), themen: themen_r,
      seit: jetzt, ip, user_agent: ua, seite, bestaetigt: null,
      bestaetigung_gesendet: null, versuche: 0, abbestellt: null, grund: null,
    };
    status = 'angemeldet';
    text = 'Fast geschafft – die Bestätigungsmail ist in den nächsten Minuten bei dir. Öffne den Link darin, um die Anmeldung abzuschließen (Double-Opt-In).';
  } else if (bestehend.status === 'active') {
    return antwort_mit('bereits-aktiv', 'Diese Adresse ist schon angemeldet und bestätigt – es kommt keine weitere Bestätigungsmail. Jede Ausgabe kommt wie vereinbart dienstags und freitags.', env, request);
  } else if (bestehend.status === 'unsubscribed' || bestehend.status === 'abgelaufen') {
    // Neu- oder Wiederanmeldung: neuer Token, frischer Nachweis, frische Themen.
    eintrag = { ...bestehend, status: 'pending', token: token_neu(), themen: themen_r,
      seit: jetzt, ip, user_agent: ua, seite, bestaetigt: null,
      bestaetigung_gesendet: null, versuche: 0, abbestellt: null, grund: null };
    status = 'wieder-angemeldet';
    text = 'Willkommen zurück – die neue Bestätigungsmail ist in den nächsten Minuten bei dir. Öffne den Link darin, um die Anmeldung abzuschließen.';
  } else if (bestehend.status === 'pending') {
    // Bereits offen: nicht neu triggern (kein Spam) – der Nachgang deckt ab.
    return antwort_mit('bereits-pending', 'Für diese Adresse ist eine Bestätigungsmail bereits unterwegs. Bitte Postfach und Spam-Ordner prüfen – ein erneutes Absenden ist nicht nötig.', env, request);
  } else {
    // Unbekannter Status (defekte Daten): fail-closed, laut melden.
    console.warn(`ff-newsletter: unbekannter Abo-Status "${bestehend.status}" für ${email}`);
    return fehler(500, 'Unbekannter Zustand – bitte erneut versuchen oder kontakt@franksfinanzcheck.de schreiben.', env, request);
  }

  eintrag.themen = filtere_themen(themen_r, env);
  await abo_schreiben(env.ABO, eintrag);
  await nachweis_schreiben(env.ABO, eintrag);

  // Bestätigung auslösen. Scheitert der Dispatch, geht nichts verloren:
  // der Nachgang (schedule) sendet offene Bestätigungen nach.
  const trigg = await dispatch_bestuerung(env, eintrag.token);
  if (!trigg.ok) {
    console.warn(`ff-newsletter: Dispatch fehlgeschlagen (Status ${trigg.status || trigg.warum}) – Nachgang holt die Bestätigung nach.`);
  }
  return antwort_mit(status, text, env, request);
}

function filtere_themen(themen, env) {
  const erlaubt = String((env && env.THEMEN_IDS) || '').split(',').map((t) => t.trim()).filter(Boolean);
  return themen.filter((t) => erlaubt.includes(t));
}

function bestaetigung_tage(env) {
  const n = Number((env && env.BESTAETIGUNG_TAGE) || BESTAETIGUNG_TAGE_DEFAULT);
  return Number.isFinite(n) && n > 0 ? n : BESTAETIGUNG_TAGE_DEFAULT;
}

async function token_eintrag(env, token) {
  const norm = await env.ABO.get(`token:${String(token || '').trim()}`);
  if (!norm) return null;
  return abo_lesen(env.ABO, norm);
}

async function bestaetigung(request, env) {
  const daten = await koerper_lesen(request);
  const token = String((daten && daten.token && daten.token[0]) || '').trim();
  const eintrag = await token_eintrag(env, token);
  if (!eintrag) {
    return antwort_mit('unbekannt', 'Dieser Link ist unbekannt oder wurde bereits verbraucht. Melde dich einfach neu an – das dauert einen Moment.', env, request, 404);
  }
  const ablauf_millis = bestaetigung_tage(env) * 24 * 60 * 60 * 1000;
  const ist_abgelaufen = eintrag.status === 'pending' && (Date.now() - new Date(eintrag.seit).getTime() > ablauf_millis);
  if (ist_abgelaufen) {
    eintrag.status = 'abgelaufen';
    await abo_schreiben(env.ABO, eintrag);
    return antwort_mit('abgelaufen', `Die Bestätigung ist abgelaufen (${bestaetigung_tage(env)} Tage). Melde dich bitte erneut an – das dauert einen Moment.`, env, request, 410);
  }
  if (eintrag.status === 'pending') {
    eintrag.status = 'active';
    eintrag.bestaetigt = new Date().toISOString();
    await abo_schreiben(env.ABO, eintrag);
    await nachweis_schreiben(env.ABO, eintrag);
    return antwort_mit('bestaetigt', 'Bestätigt! Ab jetzt bekommst du den Newsletter dienstags und freitags – die erste Ausgabe kommt am nächsten Versandtermin. Abmelden geht jederzeit mit einem Klick in jeder Mail.', env, request);
  }
  if (eintrag.status === 'active') {
    return antwort_mit('bereits-bestaetigt', 'Diese Adresse ist bereits bestätigt – du bist auf der Liste. Danke!', env, request);
  }
  return antwort_mit('unbekannt', 'Dieser Link passt nicht zum aktuellen Zustand der Anmeldung (z. B. bereits abgemeldet). Wenn du den Newsletter wieder möchtest: neu anmelden unter franksfinanzcheck.de/newsletter/', env, request, 410);
}

const ABMELDE_OK = 'Abgemeldet – ab sofort kommt keine Ausgabe mehr. Formlos geht es auch an kontakt@franksfinanzcheck.de.';

function abmelde_formular(env) {
  const html = HTML_KOPF
    + '<h1>Newsletter abmelden</h1>'
    + '<p>Ein Klick, keine Verhandlung. Adresse eintragen – du bist von der Liste. Wir fragen nicht nach dem Grund.</p>'
    + '<form method="post" action="/abmeldung">'
    + '<p><label for="mail">E-Mail-Adresse</label><br>'
    + '<input id="mail" type="email" name="email" required autocomplete="email" '
    + 'style="width:100%;padding:10px;margin:8px 0;font:inherit;border:1px solid #DCE6E1;border-radius:8px"></p>'
    + '<p aria-hidden="true" style="position:absolute;left:-9999px">'
    + '<label>Bitte dieses Feld freilassen</label>'
    + '<input type="text" name="website" tabindex="-1" autocomplete="off"></p>'
    + '<button class="btn" type="submit">Newsletter abmelden</button>'
    + '</form>'
    + '<p class="hinweis">Formlos geht es auch an '
    + '<a href="mailto:kontakt@franksfinanzcheck.de?subject=Newsletter%20abmelden">kontakt@franksfinanzcheck.de</a>.</p>'
    + HTML_FUSS;
  return new Response(html, {
    status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8', ...cors(env) },
  });
}

async function abmeldung(request, env, url) {
  // Token aus der URL ZUERST: RFC 8058 (Gmail/Yahoo) POSTet an die
  // List-Unsubscribe-URL, der Token steht in der Query, der Body ist
  // "List-Unsubscribe=One-Click". Wer nur den Body liest, sieht keinen
  // Token – und der One-Click-Knopf im Postfach ist tot.
  let token = String(url.searchParams.get('token') || '').trim();
  let email = '';
  let falle = '';
  if (request.method !== 'GET') {
    const daten = await koerper_lesen(request);
    if (!token) token = String((daten && daten.token && daten.token[0]) || '').trim();
    email = email_norm(erstein(daten || {}, 'email'));
    falle = erstein(daten || {}, 'website');
  }

  if (token) {
    const eintrag = await token_eintrag(env, token);
    if (!eintrag) {
      return antwort_mit('unbekannt', 'Dieser Link ist unbekannt – es wurde nichts geändert. Kürzester Weg: das Formular unter franksfinanzcheck.de/newsletter/abmelden/ oder formlos per Mail an kontakt@franksfinanzcheck.de.', env, request, 404);
    }
    if (eintrag.status === 'unsubscribed') {
      return antwort_mit('bereits-abgemeldet', 'Diese Adresse ist bereits abgemeldet – du bekommst keine Ausgabe mehr. Weitere Schritte sind nicht nötig.', env, request);
    }
    eintrag.status = 'unsubscribed';
    eintrag.abbestellt = new Date().toISOString();
    eintrag.grund = 'link';
    await abo_schreiben(env.ABO, eintrag);
    const text = eintrag.bestaetigt
      ? ABMELDE_OK
      : 'Deine (noch nicht bestätigte) Anmeldung wurde zurückgenommen – es kommt keine Bestätigungsmail und keine Ausgabe mehr.';
    return antwort_mit('abgemeldet', text, env, request);
  }

  if (request.method === 'GET') {
    if (wantHtml(request)) return abmelde_formular(env);
    return json({ status: 'formular', text: 'Bitte E-Mail-Adresse per POST senden oder den Link aus der Mail verwenden.' }, 200, env);
  }

  // Formular ohne Token. Honeypot und unbekannte Adressen liefern
  // dieselbe Erfolgsmeldung – kein Enumerationsleck, kein Captcha.
  if (falle) {
    await falle_zahlen(env);
    return antwort_mit('abgemeldet', ABMELDE_OK, env, request);
  }
  const ip = String(request.headers.get('cf-connecting-ip') || request.headers.get('x-forwarded-for') || '').split(',')[0].trim();
  const ip_key = `rat:${await sha256_kurz(ip || 'unbekannt')}`;
  const rate = (await env.ABO.get(ip_key, 'json')) || { z: 0 };
  if (rate.z >= MAX_ANMELDUNGEN_PRO_IP) {
    return antwort_mit('fehler', 'Zu viele Versuche in kurzer Zeit. Bitte in ein paar Minuten erneut versuchen – oder schreib eine Mail an kontakt@franksfinanzcheck.de.', env, request, 429);
  }
  await env.ABO.put(ip_key, JSON.stringify({ z: rate.z + 1, ts: Date.now() }), { expirationTtl: TTL_RATE_SEK });
  if (!EMAIL_RE.test(email) || email.length > 254) {
    return antwort_mit('fehler', 'Die E-Mail-Adresse sieht nicht gültig aus – bitte Adresse prüfen (z. B. du@beispiel.de).', env, request, 400);
  }
  const eintrag = await abo_lesen(env.ABO, email);
  if (eintrag && eintrag.status !== 'unsubscribed') {
    eintrag.status = 'unsubscribed';
    eintrag.abbestellt = new Date().toISOString();
    eintrag.grund = 'formular';
    await abo_schreiben(env.ABO, eintrag);
  }
  return antwort_mit('abgemeldet', ABMELDE_OK, env, request);
}

async function praferenzen(request, env) {
  const daten = await koerper_lesen(request);
  const token = String((daten && daten.token && daten.token[0]) || '').trim();
  const roh = (daten && (daten.themen || daten['themen[]']) || [])
    .flatMap((t) => String(t).split(',')).map((t) => t.trim()).filter(Boolean);
  const eintrag = await token_eintrag(env, token);
  if (!eintrag) {
    return antwort_mit('unbekannt', 'Dieser Link ist unbekannt – bitte den Link aus der Mail verwenden.', env, request, 404);
  }
  if (eintrag.status !== 'active' && eintrag.status !== 'pending') {
    return antwort_mit('unbekannt', 'Diese Anmeldung ist nicht (mehr) aktiv – eine Praeferenz-Änderung ist nicht moeglich.', env, request, 410);
  }
  eintrag.themen = filtere_themen(roh, env);
  await abo_schreiben(env.ABO, eintrag);
  const text = eintrag.themen.length
    ? `Gespeichert: ${eintrag.themen.length} Thema(n) – die Auswahl gilt ab der nächsten Ausgabe.`
    : 'Gespeichert: ohne Auswahl kommen alle Themen – aber nie mehr als zwei Mails pro Woche.';
  return antwort_mit('gespeichert', text, env, request);
}

async function status_sehen(env, url) {
  const token = String(url.searchParams.get('token') || '').trim();
  const eintrag = await token_eintrag(env, token);
  if (!eintrag) return json({ status: 'unbekannt' }, 404, env);
  // bewusst OHNE E-Mail-Adresse: der Token ist die Legitimation, die
  // Adresse ist kein Informationsbedarf der Praeferenzsseite.
  return json({ status: eintrag.status, themen: eintrag.themen || [], seit: eintrag.seit }, 200, env);
}

// ------------------------------------------------- Journey-Seiten (GET)
// GET rendert PRO ANFRAGE: das Token darf in das HTML, weil der Worker
// serverseitig rendert – das Formular ist ein normales POST und braucht
// kein JavaScript. Das ist der Grund, warum die Journey-HOME hier steht
// und nicht im statischen Hugo-Build (der sieht Query-Strings nie):
// ohne JS muss der Weg trotzdem funktionieren.
async function bestaetigung_seite(env, url) {
  const token = String(url.searchParams.get('token') || '').trim();
  const eintrag = await token_eintrag(env, token);
  if (!eintrag) {
    return htmlSeite('Link unbekannt', 'Dieser Link ist unbekannt oder wurde bereits verbraucht. Melde dich einfach neu an – das dauert einen Moment.', STAND_ORIGIN + '/newsletter/', env, 404);
  }
  const ablauf_millis = bestaetigung_tage(env) * 24 * 60 * 60 * 1000;
  const ist_abgelaufen = eintrag.status === 'pending' && (Date.now() - new Date(eintrag.seit).getTime() > ablauf_millis);
  if (ist_abgelaufen) {
    eintrag.status = 'abgelaufen';
    await abo_schreiben(env.ABO, eintrag);
    return htmlSeite('Bestätigung abgelaufen', `Die Bestätigung ist abgelaufen (${bestaetigung_tage(env)} Tage). Melde dich bitte erneut an – das dauert einen Moment.`, STAND_ORIGIN + '/newsletter/', env, 410);
  }
  if (eintrag.status === 'active') {
    return htmlSeite('Bereits bestätigt', 'Diese Adresse ist bereits bestätigt – du bist auf der Liste. Danke! Abmelden geht jederzeit mit einem Klick in jeder Mail.', STAND_ORIGIN + '/newsletter/', env);
  }
  if (eintrag.status !== 'pending') {
    return htmlSeite('Link passt nicht', 'Dieser Link passt nicht zum aktuellen Zustand der Anmeldung (z. B. bereits abgemeldet). Wenn du den Newsletter wieder möchtest: neu anmelden unter franksfinanzcheck.de/newsletter/.', STAND_ORIGIN + '/newsletter/', env, 410);
  }
  const html = HTML_KOPF +
    '<h1>Noch ein Klick: Newsletter bestätigen</h1>' +
    '<p>Du hast dich für den Spar-Newsletter von FranksFinanzcheck angemeldet – dienstags die Zahlen der Woche, freitags die Fristen davor, nie mehr als zwei Mails pro Woche. Klicke jetzt, damit deine Adresse auf die Liste kommt (Double-Opt-In):</p>' +
    '<form method="post" action="/bestaetigung">' +
    '<input type="hidden" name="token" value="' + esc(token) + '">' +
    '<button class="btn" type="submit">Ja, ich möchte den Newsletter</button>' +
    '</form>' +
    '<p class="hinweis">Der Link ist ' + bestaetigung_tage(env) + ' Tage gültig. Wenn du dich nicht angemeldet hast: keine Aktion nötig – diese Seite bleibt ohne Wirkung.</p>' +
    '<p><a href="/abmeldung?token=' + esc(token) + '">Jetzt abmelden</a> · <a href="' + STAND_ORIGIN + '/datenschutz/">Datenschutz</a> · <a href="' + STAND_ORIGIN + '/impressum/">Impressum</a></p>' +
    HTML_FUSS;
  return new Response(html, { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8', ...cors(env) } });
}

async function praferenzen_seite(env, url) {
  const token = String(url.searchParams.get('token') || '').trim();
  const eintrag = await token_eintrag(env, token);
  if (!eintrag) {
    return htmlSeite('Link unbekannt', 'Dieser Link ist unbekannt – bitte den Link aus der Mail verwenden.', STAND_ORIGIN + '/newsletter/', env, 404);
  }
  if (eintrag.status !== 'active' && eintrag.status !== 'pending') {
    return htmlSeite('Nicht (mehr) aktiv', 'Diese Anmeldung ist nicht (mehr) aktiv – eine Präferenz-Änderung ist nicht möglich. Wenn du den Newsletter wieder möchtest: neu anmelden unter franksfinanzcheck.de/newsletter/.', STAND_ORIGIN + '/newsletter/', env, 410);
  }
  const aktiv_themen = Array.isArray(eintrag.themen) ? eintrag.themen : [];
  const chips = themen_liste(env).map((id) =>
    '<label class="chip"><input type="checkbox" name="themen" value="' + esc(id) + '"' +
    (aktiv_themen.includes(id) ? ' checked' : '') + '> ' + esc(themen_label(env, id)) + '</label>'
  ).join('');
  const html = HTML_KOPF +
    '<h1>Themenauswahl ändern</h1>' +
    '<p>Wähle, welche Themen in deine Ausgabe reinkommen – die Änderung gilt ab der <strong>nächsten</strong> Ausgabe und kannst du jederzeit hier (oder mit dem Link in jeder Mail) ändern.</p>' +
    '<form method="post" action="/praferenzen">' +
    '<input type="hidden" name="token" value="' + esc(token) + '">' +
    '<fieldset><legend>Was soll drinstehen?</legend>' +
    chips +
    '<p class="hinweis">Ohne Auswahl kommen alle Themen – aber nie mehr als zwei Mails pro Woche. Wer keine Artikel seiner gewählten Welten vorfindet, wird nicht mit einer leeren Mail bedient.</p>' +
    '</fieldset>' +
    '<button class="btn" type="submit">Auswahl speichern</button>' +
    '</form>' +
    '<p class="hinweis">Bequemer im Browser: dieselbe Auswahl in der Vollversion auf der Website – ' +
    'sie lädt deine Häkchen und speichert sie ohne Seitenwechsel. ' +
    '<a href="' + STAND_ORIGIN + '/newsletter/praeferenzen/?token=' + esc(token) + '">Vollversion öffnen</a></p>' +
    '<p class="hinweis"><a href="/abmeldung?token=' + esc(token) + '">Abmelden</a> · <a href="' + STAND_ORIGIN + '/newsletter/praeferenzen/">Details zur Auswahl</a></p>' +
    HTML_FUSS;
  return new Response(html, { status: 200, headers: { 'Content-Type': 'text/html; charset=utf-8', ...cors(env) } });
}

// ---------------------------------------------------------------- Export (geschuetzt)
async function exportiert(request, env, p, url) {
  const angebot = request.headers.get('x-ff-key') || url.searchParams.get('sluessel') || '';
  if (!await schluessel_pruefen(env, angebot)) {
    return new Response(JSON.stringify({ status: 'verboten' }), {
      status: 403, headers: { 'Content-Type': 'application/json; charset=utf-8' },
    });
  }
  if (p === '/export/abonnenten') {
    const keys = await liste_mit_prefix(env.ABO, 'abo:');
    const aktiv = [];
    for (const key of keys) {
      const eintrag = await env.ABO.get(key, 'json');
      if (eintrag && eintrag.status === 'active') {
        aktiv.push({ email: eintrag.email, token: eintrag.token, themen: eintrag.themen || [], bestaetigt: eintrag.bestaetigt });
      }
    }
    return json({ ts: new Date().toISOString(), anzahl: aktiv.length, abonnenten: aktiv }, 200, env);
  }
  if (p === '/export/pending') {
    const keys = await liste_mit_prefix(env.ABO, 'abo:');
    const offen = [];
    for (const key of keys) {
      const eintrag = await env.ABO.get(key, 'json');
      if (eintrag && eintrag.status === 'pending') {
        offen.push({ email: eintrag.email, token: eintrag.token, seit: eintrag.seit, bestaetigung_gesendet: eintrag.bestaetigung_gesendet, versuche: eintrag.versuche || 0 });
      }
    }
    return json({ ts: new Date().toISOString(), anzahl: offen.length, offen }, 200, env);
  }
  if (p === '/export/token') {
    const eintrag = await token_eintrag(env, url.searchParams.get('token') || '');
    if (!eintrag) return json({ status: 'unbekannt' }, 404, env);
    return json({
      status: eintrag.status, email: eintrag.email, token: eintrag.token,
      themen: eintrag.themen || [], seit: eintrag.seit, bestaetigt: eintrag.bestaetigt,
      abbestellt: eintrag.abbestellt, grund: eintrag.grund || null,
    }, 200, env);
  }
  if (p === '/export/kontakt') {
    const email = email_norm(url.searchParams.get('email') || '');
    const eintrag = email ? await abo_lesen(env.ABO, email) : null;
    if (!eintrag) return json({ status: 'unbekannt' }, 404, env);
    return json({
      status: eintrag.status, email: eintrag.email, token: eintrag.token,
      themen: eintrag.themen || [],
    }, 200, env);
  }
  if (p === '/export/versuch' && request.method === 'POST') {
    const daten = await koerper_lesen(request);
    const token = String((daten && daten.token && daten.token[0]) || '').trim();
    const ergebnis = String((daten && daten.ergebnis && daten.ergebnis[0]) || 'gesendet');
    const eintrag = await token_eintrag(env, token);
    if (!eintrag) return json({ status: 'unbekannt' }, 404, env);
    const jetzt = new Date().toISOString();
    if (ergebnis === 'gesendet' && eintrag.status === 'pending') {
      eintrag.versuche = (eintrag.versuche || 0) + 1;
      eintrag.bestaetigung_gesendet = jetzt;
      if (eintrag.versuche >= MAX_VERSEND_VERSUCHE) eintrag.status = 'abgelaufen';
    } else if (ergebnis === 'abgelaufen') {
      eintrag.status = 'abgelaufen';
    } else if (ergebnis === 'bounce') {
      // Harte Bounce: Unterdruckung, keine Weiterleitung, kein Retry.
      eintrag.status = 'unsubscribed';
      eintrag.abbestellt = jetzt;
      eintrag.grund = 'bounce';
    }
    await abo_schreiben(env.ABO, eintrag);
    return json({ status: 'ok', abo_status: eintrag.status, versuche: eintrag.versuche || 0 }, 200, env);
  }
  return new Response(JSON.stringify({ status: 'unbekannt' }), { status: 404, headers: { 'Content-Type': 'application/json; charset=utf-8' } });
}

// ---------------------------------------------------------------- Einstieg
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const p = url.pathname;
    if (request.method === 'OPTIONS') return vorabfrage(env);
    try {
      if (p === '/' || p === '/healthz') return await health(env);
      if (p === '/anmeldung' && request.method === 'POST') return await anmeldung(request, env, url);
      if (p === '/bestaetigung' && request.method === 'GET') return await bestaetigung_seite(env, url);
      if (p === '/bestaetigung' && request.method === 'POST') return await bestaetigung(request, env);
      if (p === '/abmeldung') return await abmeldung(request, env, url);
      if (p === '/praferenzen' && request.method === 'GET') return await praferenzen_seite(env, url);
      if (p === '/praferenzen' && request.method === 'POST') return await praferenzen(request, env);
      if (p === '/status' && request.method === 'GET') return await status_sehen(env, url);
      if (p.startsWith('/export/')) return await exportiert(request, env, p, url);
      return fehler(404, 'Unbekannter Pfad.', env, request);
    } catch (e) {
      console.warn(`ff-newsletter: ${(e && e.message) || e}`);
      return fehler(500, 'Interner Fehler – bitte erneut versuchen.', env, request);
    }
  },

  /**
   * Cron Trigger (wrangler.toml [triggers].crons). `controller.cron` ist
   * der Ausdruck, der gefeuert hat – er waehlt den Takt aus TAKT.
   * Lokal testen: `wrangler dev` → curl
   * "http://localhost:8787/cdn-cgi/local/scheduled?cron=30+4+*+*+TUE,FRI".
   */
  async scheduled(controller, env, ctx) {
    const arbeit = takt_ausfuehren(env, controller && controller.cron, controller && controller.scheduledTime);
    if (ctx && typeof ctx.waitUntil === 'function') ctx.waitUntil(arbeit);
    return arbeit;
  },
};

// Fuer Tests (node --test): die Takt-Tabelle und der Ausfuehrer ohne Cloudflare.
export { TAKT, takt_ausfuehren, takt_fuer };
