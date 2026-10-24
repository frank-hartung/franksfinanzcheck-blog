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
 *   GET  /abmeldung      mit Token: Bestaetigungsseite (POST-Knopf) – Link-
 *                        Scanner von Mailprogrammen melden so niemanden ab;
 *                        ohne Token das Formular
 *   POST /praferenzen    Themenwahl pro Abo (Token + themen[])
 *   GET  /status         Token -> {status, themen} (ohne Adresse!)
 *   GET  /healthz        Lebendigkeits-Pruefung; Details (`takt`) nur mit
 *                        X-FF-Key (oeffentlich nur ok/ts)
 *   GET  /export/abonnenten, /export/pending: Leseschluessel im Header.
 *   POST /export/token, /export/kontakt, /export/versuch: getrennter
 *                        Schreibschluessel; Token/E-Mail nur im Request-Body.
 *                        Schreibzugriffe melden Versand-Versuche (Catch-up).
 *   scheduled()          TAKTGEBER (seit 25.09.2026): Cloudflare Cron
 *                        Triggers starten den Digest (Di/Fr 04:30 UTC),
 *                        die Kadenz-Wache (05:05 UTC) und den Nachgang
 *                        (stuendlich) per workflow_dispatch – weil GitHubs
 *                        eigener Scheduler an diesem Repo Stunden zu spaet
 *                        oder gar nicht feuert. Details: Abschnitt „Taktgeber“.
 *
 * DATEN (Workers KV, Binding `ABO`; Jurisdiktion im CF-Konto pruefen):
 *   abo:{email-norm}     Abo-Status, Token, Themen, Zeitstempel (aktive ohne TTL)
 *   token:{token}        Rueckweg Token -> email-norm (gleiche TTL wie Abo)
 *   nachweis:{sha256}    Einwilligungsnachweis (IP, UA, Zeitpunkt), TTL 3 Jahre
 *   rat:{sha256(ip)}     Rate-Limit-Zaehler (15 Min)
 *   budget:anmeldung:{tag}  Tagesbudget der Anmeldungen (Audit 15.10.2026, F-03)
 *   warn:{bereich}:{tag}    Sperr-Melder, 1 Schreibzugriff je Stunde
 *   exportlog:{ts}       Protokoll der Export-Aufrufe (TTL 30 Tage)
 *   metrik:falle        Bot-Fallen-Treffer (1 Tag)
 *
 * SCHUTZDECKEL (Sicherheitsaudit 15.10.2026, F-02/F-03/F-08):
 *   Der Free-Plan erlaubt 1.000 KV-SCHREIBZugriffe pro Tag und KONTO. Eine
 *   Anmeldung kostet vier. Ohne Deckel genuegten wenige hundert Anfragen, um
 *   das Kontingent zu leeren – danach fallen Anmeldung, Bestaetigung, Abmeldung
 *   (Art. 7 Abs. 3 DSGVO) und der Pflegelauf aus. Deshalb:
 *     1. JEDE Route hat ein Mengenlimit (Binding RATE_LIMITER, kostenlos;
 *        vorher nur /anmeldung und das Abmeldeformular).
 *     2. Die Anmeldung hat zusaetzlich ein TAGESBUDGET (ANMELDUNG_MAX_PRO_TAG,
 *        Standard 100). Ist es erschoepft, wird fail-closed abgelehnt und
 *        genau einmal je Stunde laut protokolliert.
 *     3. Jeder Zugang zu Token oder personenbezogenen Exportdaten braucht
 *        den ZWEITEN, vom Leseschluessel verschiedenen Schluessel
 *        (EXPORT_KEY_WRITE). Ohne den zweiten Schluessel sind diese Wege
 *        gesperrt; es gibt keinen Rueckfall. Token und E-Mail stehen bei
 *        Einzel-Lookups ausschliesslich im POST-Body, nie in der URL.
 *        Abgewiesene Exportversuche werden je Stunde begrenzt protokolliert,
 *        damit ein anonymer 403-Sturm das KV-Schreibbudget nicht aufbraucht.
 *   Restrisiko (bewusst, dokumentiert): Ein verteilter Lesesturm auf die
 *   Token-Seiten laesst sich im Worker nicht zuverlaessig zaehlen, ohne genau
 *   die Schreibzugriffe zu verbrauchen, die geschuetzt werden sollen. Dagegen
 *   steht die WAF-Mengenregel der Zone (siehe cloudflare/waf-mengenregeln.md)
 *   – sie zaehlt an der Edge, nicht im KV.

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
const TTL_NACHWEIS_SEK = 1095 * 24 * 60 * 60; // Nachweis: bis zu 3 Jahre
const TTL_UNSUB_SEK = 29 * 24 * 60 * 60; // KV-Fangnetz bei Cron-Ausfall (< 30 Tage)
const TTL_PENDING_SEK = 15 * 24 * 60 * 60; // DOI-Frist 14 Tage + Fangnetz
const TTL_EXPIRED_SEK = 24 * 60 * 60;
const PFLEGE_CRON = '13 2 * * *';
const TTL_RATE_SEK = 15 * 60;
const MAX_ANMELDUNGEN_PRO_IP = 5;
// FEEDBACK (H4, 28.09.2026): Leser-Stimmen je Artikel. Missbrauchsschutz =
// IP-Hash + Slug, 6 h genau EINE Stimme (Hash nur kurzlebig, keine Klartext-IP).
const TTL_FEEDBACK_RATE_SEK = 6 * 60 * 60;
const FEEDBACK_SLUG_RE = /^[a-z0-9][a-z0-9-]{0,119}$/;
// KV-Schreibbudget (Audit 14.10.2026, H-03): Der Free-Plan erlaubt 1.000
// KV-Schreibzugriffe pro Tag und KONTO. Feedback darf davon hoechstens
// FEEDBACK_MAX_PRO_TAG verbrauchen – Anmeldung und Abmeldung behalten immer
// den Rest. Eine Stimme = genau EIN Schreibzugriff (Tagesschluessel).
//
// NACHTRAG 15.10.2026 (F-03): „den Rest behalten" war eine Absicht ohne
// Deckel – die Anmeldung selbst hatte keine Obergrenze und konnte den Rest
// allein aufbrauchen (vier Schreibzugriffe je Anmeldung: abo, token,
// nachweis, budget). Jetzt gilt ein harter Tagesdeckel; ist er erreicht,
// wird fail-closed abgelehnt statt weitergeschrieben. 100 Anmeldungen/Tag
// = 400 der 1.000 Schreibzugriffe, 200 Feedback-Stimmen = 200, zusammen
// 600 – der Rest bleibt fuer Bestaetigungen, Abmeldungen und den Pflegelauf.
const ANMELDUNG_MAX_PRO_TAG_DEFAULT = 100;
const TTL_BUDGET_SEK = 48 * 60 * 60;
const TTL_WARN_SEK = 60 * 60;
const TTL_EXPORTLOG_SEK = 30 * 24 * 60 * 60;
const TTL_EXPORT_DENIED_LOG_SEK = 48 * 60 * 60;
const MAX_FORM_BODY_BYTES = 64 * 1024;
const FEEDBACK_MAX_PRO_TAG_DEFAULT = 200;
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
// Sicherheitskopf fuer jede Antwort (Audit 14.10.2026, N-03): keine Skripte,
// keine Einbettung in fremde Seiten, kein Referrer nach aussen (Token-URLs!).
// `same-origin` statt `no-referrer`: Bei `no-referrer` schickt der Browser
// fuer POST `Origin: null` – die eigenen Formulare scheiterten dann am
// CSRF-Schutz. Nach aussen geht so weiterhin kein Referrer.
const SICHERHEITS_KOPF = {
  'Content-Security-Policy': "default-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; base-uri 'none'",
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'same-origin',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
  'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
};

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
    Vary: 'Origin',
    ...SICHERHEITS_KOPF,
  };
}

/** Erlaubte Urspruenge fuer POST (CSRF-Schutz, Audit M-02): die Site-Origins
 *  aus SITE_ORIGIN plus der Worker selbst (seine eigenen Formulare). */
function herkunft_erlaubt(request, env, url) {
  const herkunft = String(request.headers.get('origin') || '').trim();
  // Fetch-Metadaten kann keine Webseite faelschen (verbotener Header).
  const seite = String(request.headers.get('sec-fetch-site') || '').trim().toLowerCase();
  // `Origin: null` (sandboxed iframe, data:-URL, Referrer-Policy no-referrer):
  // nur akzeptieren, wenn der Browser selbst same-origin bescheinigt.
  if (herkunft === 'null') return seite === 'same-origin';
  // Ohne Origin: kein Browser-Kontext (Mailprogramm-One-Click nach RFC 8058,
  // Skripte). CSRF setzt einen Browser voraus – der sendet bei POST immer
  // Origin; bescheinigt er trotzdem cross-site, wird abgelehnt.
  if (!herkunft) return seite !== 'cross-site';
  const erlaubt = String((env && env.SITE_ORIGIN) || STAND_ORIGIN).split(',')
    .map((o) => o.trim().replace(/\/$/, '')).filter(Boolean);
  erlaubt.push(url.origin);
  return erlaubt.includes(herkunft.replace(/\/$/, ''));
}

function html_antwort(seite, kod, env) {
  return new Response(seite, {
    status: kod, headers: { 'Content-Type': 'text/html; charset=utf-8', ...cors(env) },
  });
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

/**
 * Konstantzeit-Vergleich fuer ein Export-Secret (kein Zeitaugriff).
 * `EXPORT_KEY` ist ausschliesslich lesend und liefert keine Bearer-Token.
 * Token- und personenbezogene Endpunkte verlangen `EXPORT_KEY_WRITE`, das
 * gesetzt und vom Leseschluessel verschieden sein MUSS. Kein Rueckfall:
 * fehlt die zweite Rolle oder ist sie gleich dem Leseschluessel, bleibt der
 * schreibende Export gesperrt (F-08).
 */
async function schluessel_pruefen(env, angebot) {
  return konstantzeit_gleich(String((env && env.EXPORT_KEY) || ''), String(angebot || ''));
}

async function schreibschluessel_pruefen(env, angebot) {
  const lesen = String((env && env.EXPORT_KEY) || '');
  const schreiben = String((env && env.EXPORT_KEY_WRITE) || '');
  if (!lesen || !schreiben || lesen === schreiben) return false;
  return konstantzeit_gleich(schreiben, String(angebot || ''));
}

async function konstantzeit_gleich(sollen, ist) {
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

/** Fingerabdruck eines Schluessels fuer das Export-Protokoll – nie der Wert. */
async function schluessel_fingerabdruck(angebot) {
  return (await sha256_kurz(`ff-key|${String(angebot || '')}`)).slice(0, 8);
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

/** Heutiger Kalendertag (UTC) – Bezug der Tagesbudgets. */
function tagesstempel(zeit = Date.now()) {
  return new Date(zeit).toISOString().slice(0, 10);
}

/**
 * Tagesbudget (F-03): zieht EINEN Schreibzugriff, wenn noch Platz ist.
 * Gibt { ok, stand, maximum } zurueck. KV ist letztlich konsistent, nicht
 * streng atomar – zwei gleichzeitige Anfragen koennen denselben Stand lesen.
 * Fuer einen Missbrauchsdeckel ist das ausreichend genau (die Alternative
 * waere ein Durable Object oder D1 – bewusst nicht noetig).
 */
async function tagesbudget_nehmen(env, bereich, maximum, zeit = Date.now()) {
  const schluessel = `budget:${bereich}:${tagesstempel(zeit)}`;
  const stand = Number((await env.ABO.get(schluessel)) || 0);
  if (maximum > 0 && stand >= maximum) return { ok: false, stand, maximum };
  await env.ABO.put(schluessel, String(stand + 1), { expirationTtl: TTL_BUDGET_SEK });
  return { ok: true, stand: stand + 1, maximum };
}

/** Tagesbudget lesen, ohne zu schreiben (fuer /healthz und Melder). */
async function tagesbudget_stand(env, bereich, zeit = Date.now()) {
  return Number((await env.ABO.get(`budget:${bereich}:${tagesstempel(zeit)}`)) || 0);
}

/**
 * Laut, aber nicht teuer: Meldet ein Ereignis hoechstens EINMAL je Stunde
 * (ein KV-Schreibzugriff). Ohne diese Daempfung wuerde der Melder selbst
 * das Budget verbrauchen, das er schuetzt.
 */
async function warnen_einmal(env, bereich, meldung, zeit = Date.now()) {
  const schluessel = `warn:${bereich}:${tagesstempel(zeit)}`;
  try {
    if (await env.ABO.get(schluessel)) return false;
    await env.ABO.put(schluessel, new Date(zeit).toISOString(), { expirationTtl: TTL_WARN_SEK });
  } catch (e) { /* Melder darf nie den Betrieb brechen */ }
  console.warn(`ff-newsletter alarm ${bereich}: ${meldung}`);
  return true;
}

// Fehlversuche sind global je Stunde zusammengefasst (zusaetzlich per Isolat
// dedupliziert). So bleibt der Nachweis erhalten, ohne dass anonyme 403er pro
// Anfrage einen KV-Schreibzugriff ausloesen koennen.
const EXPORT_DENIED_LOGGED = new Set();

async function export_vermerken(env, route, umfang, angebot, status = 200, zeit = Date.now()) {
  const ts = new Date(zeit).toISOString();
  const abgewiesen = status === 403;
  const stunden_key = abgewiesen ? `exportlog:denied:${ts.slice(0, 13)}` : null;
  if (stunden_key && EXPORT_DENIED_LOGGED.has(stunden_key)) return;
  if (stunden_key) {
    if (EXPORT_DENIED_LOGGED.size >= 24) EXPORT_DENIED_LOGGED.clear();
    // Vor dem ersten await markieren: auch parallele Requests in derselben
    // Worker-Instanz koennen so nicht je einen KV-Write ausloesen.
    EXPORT_DENIED_LOGGED.add(stunden_key);
  }
  try {
    if (stunden_key && await env.ABO.get(stunden_key)) return;
    const eintrag = {
      ts,
      route,
      umfang,
      status,
      key: await schluessel_fingerabdruck(angebot),
    };
    const key = stunden_key || `exportlog:${ts}`;
    await env.ABO.put(key, JSON.stringify(eintrag), {
      expirationTtl: abgewiesen ? TTL_EXPORT_DENIED_LOG_SEK : TTL_EXPORTLOG_SEK,
    });
    if (!abgewiesen) console.log(`ff-newsletter export ${route}: ${umfang} (${status})`);
  } catch (e) {
    if (stunden_key) EXPORT_DENIED_LOGGED.delete(stunden_key);
    // Das Protokoll ist Nachweis, nicht Betriebsvoraussetzung. Insbesondere
    // darf ein KV-Fehler die Export-Antwort nicht veraendern.
  }
}

function export_speicher_zuruecksetzen() {
  EXPORT_DENIED_LOGGED.clear();
}

/** Protokoll der Exporte – nur mit Schluessel (in /healthz). */
async function export_log_lesen(env) {
  const aus = [];
  for (const key of await liste_mit_prefix(env.ABO, 'exportlog:')) aus.push(key.slice('exportlog:'.length));
  return aus.sort().reverse().slice(0, 20);
}


/**
 * Rate-Limit je Schluessel. Bevorzugt das Cloudflare-Rate-Limiting-Binding
 * `RATE_LIMITER` (wrangler.toml [[ratelimits]]) – es kostet KEINE
 * KV-Schreibzugriffe (Audit H-03). Ohne Binding: der bisherige KV-Zaehler
 * (15-Min-Fenster) als Rueckfall.
 */
async function rate_erlaubt(env, ip, bereich = 'anmeldung') {
  const roh = `${bereich}|${ip || 'unbekannt'}`;
  if (env && env.RATE_LIMITER && typeof env.RATE_LIMITER.limit === 'function') {
    try {
      const { success } = await env.RATE_LIMITER.limit({ key: await sha256_kurz(roh) });
      return success !== false;
    } catch (e) { /* Binding gestoert: KV-Rueckfall unten */ }
  }
  const ip_key = `rat:${await sha256_kurz(ip || 'unbekannt')}`;
  const rate = (await env.ABO.get(ip_key, 'json')) || { z: 0 };
  if (rate.z >= MAX_ANMELDUNGEN_PRO_IP) return false;
  await env.ABO.put(ip_key, JSON.stringify({ z: rate.z + 1, ts: Date.now() }), { expirationTtl: TTL_RATE_SEK });
  return true;
}

/**
 * Cloudflare Turnstile (Audit M-02; Paar-Vertrag 19.10.2026, WF-E813 / #809):
 * Die Pruefung haengt an BEIDEN Werten – Secret (Worker) UND Site-Key
 * (Website, params.turnstileSiteKey in hugo.toml, gespiegelt als Variable
 * TURNSTILE_SITEKEY). Der halbgesetzte Zustand war der teuerste Fehler:
 * „Secret gesetzt, aber kein Widget ausgeliefert“ liess JEDEN
 * Anmeldeversuch an einer Sicherheitspruefung scheitern, die kein Mensch
 * bestehen konnte – seit 15.10.2026, laut gemeldet von der taeglichen
 * Betriebs-Wache („jede Anmeldung scheitert“), aber ohne Behebung im Code.
 * Gegengelesen: Secret ohne Site-Key war bis dahin als fail-closed gedacht;
 * fail-closed gegen MENSCHEN ist kein Schutz, sondern ein Ausfall.
 *
 * Deshalb das Paar als EIN Vertrag: erst wenn BEIDE gesetzt sind, wird
 * fail-closed geprueft (wie beim KI-Assistenten). Der halbgesetzte Zustand
 * heisst jetzt „wartet“: die Anmeldung laeuft weiter (Honeypot, Zeitfalle,
 * Mengenklassen, Tagesbudget bleiben), /healthz meldet den Zustand laut,
 * und scripts/worker_betrieb_wache.py meldet ihn taeglich, bis das Paar
 * komplett ist. Site-Key und Secret gehoeren in einem Deploy zusammen –
 * die Wache prueft den Spiegel (hugo.toml == TURNSTILE_SITEKEY).
 */
function turnstile_zustand(env) {
  const geheim = String((env && env.TURNSTILE_SECRET) || '').trim();
  const sitekey = String((env && env.TURNSTILE_SITEKEY) || '').trim();
  if (geheim && sitekey) return 'aktiv';
  if (geheim) return 'wartet';
  return 'inaktiv';
}

async function turnstile_ok(env, antwort_token, ip) {
  if (turnstile_zustand(env) !== 'aktiv') return true;
  const geheim = String((env && env.TURNSTILE_SECRET) || '').trim();
  const token = String(antwort_token || '').trim();
  if (!token || token.length > 2048) return false;
  try {
    const form = new URLSearchParams({ secret: geheim, response: token });
    if (ip) form.set('remoteip', ip);
    const r = await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
      method: 'POST', body: form,
    });
    const d = await r.json();
    return !!(d && d.success === true);
  } catch (e) {
    return false;
  }
}

/** `quelle` (Herkunftsseite) nur als eigene Site-URL, gekuerzt (Audit N-04). */
function quelle_pruefen(roh, env) {
  const basis = String((env && env.SITE_ORIGIN) || STAND_ORIGIN).split(',')[0].trim();
  const q = String(roh || '').trim().slice(0, 300);
  return q.startsWith(basis + '/') || q === basis ? q : basis;
}

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
  // Formulare brauchen nur wenige KiB. Cappe den Stream selbst statt nur
  // Content-Length zu vertrauen (kann fehlen oder falsch sein), damit ein
  // beliebig großer POST nicht den Worker-Isolate-Speicher belegt.
  const laenge = request.headers.get('content-length');
  if (laenge !== null && /^\d+$/.test(laenge) && Number(laenge) > MAX_FORM_BODY_BYTES) {
    try { await request.body?.cancel(); } catch (e) { /* Body wird verworfen. */ }
    return null;
  }
  const reader = request.body?.getReader();
  const teile = [];
  let bytes = 0;
  if (reader) {
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        bytes += value.byteLength;
        if (bytes > MAX_FORM_BODY_BYTES) {
          try { await reader.cancel(); } catch (e) { /* Body wird verworfen. */ }
          return null;
        }
        teile.push(value);
      }
    } catch (e) {
      return null;
    }
  }
  const rohBytes = new Uint8Array(bytes);
  let versatz = 0;
  for (const teil of teile) { rohBytes.set(teil, versatz); versatz += teil.byteLength; }
  let roh;
  try {
    roh = new TextDecoder('utf-8', { fatal: true }).decode(rohBytes);
  } catch (e) {
    return null;
  }
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
  const bisher = await abo_lesen(kv, eintrag.norm);
  // Neu-Anmeldung darf keinen zweiten gültigen Token zurücklassen.
  if (bisher && bisher.token && bisher.token !== eintrag.token) {
    await kv.delete(`token:${bisher.token}`);
  }
  const ttl = eintrag.status === 'unsubscribed' ? TTL_UNSUB_SEK
    : eintrag.status === 'pending' ? TTL_PENDING_SEK
      : eintrag.status === 'abgelaufen' ? TTL_EXPIRED_SEK : null;
  const optionen = ttl ? { expirationTtl: ttl } : undefined;
  await kv.put(`abo:${eintrag.norm}`, JSON.stringify(eintrag), optionen);
  await kv.put(`token:${eintrag.token}`, eintrag.norm, optionen);
}

async function nachweis_schreiben(kv, eintrag, kontext = null) {
  // Einwilligungsnachweis (Art. 7 Abs. 1 DSGVO). IP und User-Agent stehen
  // NUR hier (befristet), nicht im aktiven Abo-Datensatz (Audit N-04).
  // Ohne `kontext` (Bestaetigung) bleiben die Anmeldedaten erhalten.
  const haetti = await sha256_kurz(`ff-nl|${eintrag.norm}|v1`);
  const bisher = (await kv.get(`nachweis:${haetti}`, 'json')) || {};
  const k = kontext || {};
  await kv.put(`nachweis:${haetti}`, JSON.stringify({
    email: eintrag.email,
    ip: kontext ? (k.ip || null) : (bisher.ip || eintrag.ip || null),
    user_agent: kontext ? (k.ua || null) : (bisher.user_agent || eintrag.user_agent || null),
    seite: kontext ? (k.seite || null) : (bisher.seite || eintrag.seite || null),
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

// Einmal täglich: auch Bestandsdaten ohne TTL bereinigen. Kein API-Endpunkt:
// nur der Cloudflare-Cron darf diese Operation starten. Wiederholbar; aktive
// Abos und separat befristete Nachweise bleiben erhalten.
async function datenschutz_pflege(env, zeit = Date.now()) {
  const grenze = (tage) => zeit - tage * 24 * 60 * 60 * 1000;
  let geloescht = 0;
  for (const key of await liste_mit_prefix(env.ABO, 'abo:')) {
    const eintrag = await env.ABO.get(key, 'json');
    if (!eintrag || !['unsubscribed', 'abgelaufen', 'pending'].includes(eintrag.status)) continue;
    const datum = eintrag.status === 'unsubscribed' ? eintrag.abbestellt
      : eintrag.status === 'pending' ? eintrag.seit : (eintrag.abgelaufen_am || eintrag.seit);
    const stichtag = eintrag.status === 'unsubscribed' ? grenze(29) : grenze(14);
    if (!datum || !Number.isFinite(Date.parse(datum)) || Date.parse(datum) > stichtag) continue;
    // Recheck unmittelbar vor dem Löschen; Keys sind im Produktionsbestand
    // bereits vorhanden und können zwischen list() und get() geändert werden.
    const aktuell = await env.ABO.get(key, 'json');
    if (!aktuell || aktuell.status !== eintrag.status || aktuell.token !== eintrag.token ||
        aktuell.abbestellt !== eintrag.abbestellt || aktuell.seit !== eintrag.seit) continue;
    await env.ABO.delete(key);
    if (eintrag.token) await env.ABO.delete(`token:${eintrag.token}`);
    geloescht += 1;
  }
  // Altbestand (vor 14.10.2026) trug IP/UA im aktiven Abo – entfernen (N-04).
  // Der Einwilligungsnachweis (nachweis:{hash}) behaelt sie befristet.
  const PERSONENFELDER = ['ip', 'user_agent', 'ua'];
  const bereinigen = (obj) => {
    let geaendert = false;
    if (!obj || typeof obj !== 'object') return false;
    for (const feld of PERSONENFELDER) {
      if (Object.prototype.hasOwnProperty.call(obj, feld)) { delete obj[feld]; geaendert = true; }
    }
    return geaendert;
  };
  // Hoechstens 50 Datensaetze (= 100 KV-Schreibzugriffe) je Lauf: ein grosser
  // Altbestand verteilt sich auf mehrere Tage statt das Tagesbudget zu leeren.
  let umgeschrieben = 0;
  for (const key of await liste_mit_prefix(env.ABO, 'abo:')) {
    if (umgeschrieben >= 50) break;
    const eintrag = await env.ABO.get(key, 'json');
    if (!eintrag) continue;
    let geaendert = bereinigen(eintrag);
    for (const unter of ['consents', 'nachweis']) geaendert = bereinigen(eintrag[unter]) || geaendert;
    if (geaendert) { await abo_schreiben(env.ABO, eintrag); umgeschrieben += 1; }
  }
  await feedback_aufrollen(env, zeit);
  // Alte Token-Versionen und Waisen aus früheren Deploys beseitigen.
  for (const key of await liste_mit_prefix(env.ABO, 'token:')) {
    const norm = await env.ABO.get(key);
    const eintrag = norm && await abo_lesen(env.ABO, norm);
    if (!eintrag || key !== `token:${eintrag.token}`) await env.ABO.delete(key);
  }
  return { geloescht };
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

async function dispatch_bestuerung(env) {
  // KEIN Token und keine Adresse im Event (Audit H-05): workflow_dispatch-
  // Eingaben landen in oeffentlichen Logs. Der Nachgang holt offene
  // Anmeldungen selbst ueber /export/pending (geschuetzt per X-FF-Key) und
  // sendet frische Bestaetigungen sofort.
  return github_dispatch(env, env.GITHUB_WORKFLOW || 'newsletter-lifecycle.yml',
    { aktion: 'nachgang' });
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
    inputs: { aktion: 'nachgang' },
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
  // Nur Log (Workers Logs), KEIN KV-Schreibzugriff: Bots duerfen das
  // Tagesbudget nicht ueber die Falle aufbrauchen (Audit H-03).
  console.log('ff-newsletter: Bot-Falle ausgeloest');
}

// ---------------------------------------------------------------- Feedback (H4)
/**
 * POST /feedback – „War dieser Ratgeber hilfreich?" (Ja/Nein) je Artikel.
 *
 * Datenschutz by design: Body nur { slug, hilfreich: 'ja'|'nein' }.
 * Gespeichert wird AUSSCHLIESSLICH ein aggregierter Zählerstand je Slug
 * (feedback:<slug> → { ja, nein, letzte }) – keine IPs, keine Cookies,
 * kein Fingerprinting. Missbrauchsschutz: ein gekürzter Hash aus IP und
 * Slug liegt im Tagesschlüssel (fbtag:<datum>) und verhindert Doppelzählen
 * am selben Tag; der tägliche Cron rollt den Tag auf und löscht ihn samt
 * Hashes (spätestens TTL 8 Tage). Erneuter Klick ist idempotent
 * (200, „bereits-gezaehlt").
 */
function feedback_tag(zeit = Date.now()) {
  return `fbtag:${new Date(zeit).toISOString().slice(0, 10)}`;
}

function feedback_max(env) {
  const n = Number((env && env.FEEDBACK_MAX_PRO_TAG) || FEEDBACK_MAX_PRO_TAG_DEFAULT);
  return Number.isFinite(n) && n >= 0 ? n : FEEDBACK_MAX_PRO_TAG_DEFAULT;
}

async function feedback(request, env) {
  // Eigene Mengenklasse (F-03): Der Router deckelt Feedback-Anfragen mit
  // 30/Minute und Verbindung, der Slug-Zaehler bleibt der zweite Riegel.
  const daten = await koerper_lesen(request);
  if (!daten) return fehler(400, 'Unverständlicher Anfragekörper.', env, request);
  const slug = erstein(daten, 'slug').toLowerCase();
  const roh = erstein(daten, 'hilfreich').toLowerCase();
  if (!FEEDBACK_SLUG_RE.test(slug)) {
    return fehler(400, 'Unbekannter Artikel.', env, request);
  }
  const stimme = ['ja', 'true', '1'].includes(roh) ? 'ja'
    : ['nein', 'false', '0'].includes(roh) ? 'nein' : null;
  if (!stimme) {
    return fehler(400, 'Feedback muss „ja" oder „nein" sein.', env, request);
  }
  const ip = request.headers.get('CF-Connecting-IP') || '';
  // EIN Schluessel pro UTC-Tag: Zaehler, Stimmen je Slug und die (gehashten)
  // Doppelklick-Marker liegen zusammen – eine Stimme kostet genau einen
  // KV-Schreibzugriff, und ab FEEDBACK_MAX_PRO_TAG wird nichts mehr
  // geschrieben. So kann Feedback das Newsletter-Budget nie aufbrauchen.
  const marke = await sha256_kurz(`${ip}|${slug}`);
  const tag_key = feedback_tag();
  const tag = (await env.ABO.get(tag_key, 'json')) || { n: 0, s: {}, d: {} };
  if (tag.d && tag.d[marke]) {
    return json({ ok: true, status: 'bereits-gezaehlt' }, 200, env);
  }
  if (Number(tag.n || 0) >= feedback_max(env)) {
    // Budget erschoepft: freundlich annehmen, nichts schreiben.
    return json({ ok: true, status: 'angenommen' }, 200, env);
  }
  tag.s = tag.s || {};
  tag.d = tag.d || {};
  const stand = tag.s[slug] || { ja: 0, nein: 0 };
  stand[stimme] = Number(stand[stimme] || 0) + 1;
  tag.s[slug] = stand;
  tag.d[marke] = 1;
  tag.n = Number(tag.n || 0) + 1;
  try {
    await env.ABO.put(tag_key, JSON.stringify(tag), { expirationTtl: 8 * 24 * 60 * 60 });
  } catch (e) {
    // KV begrenzt Schreibzugriffe auf denselben Schluessel (1/s) – eine
    // verlorene Stimme ist hinnehmbar, ein Fehler fuer den Leser nicht.
    console.warn(`ff-newsletter feedback: Stimme nicht gespeichert (${(e && e.message) || e})`);
  }
  return json({ ok: true, status: 'gezaehlt' }, 200, env);
}

/** Cron (taeglich): abgeschlossene Tagesschluessel in die Summen je Slug
 *  uebertragen und loeschen. Wiederholbar; der heutige Tag bleibt liegen. */
async function feedback_aufrollen(env, zeit = Date.now()) {
  const heute = feedback_tag(zeit);
  for (const key of await liste_mit_prefix(env.ABO, 'fbtag:')) {
    if (key >= heute) continue;
    const tag = await env.ABO.get(key, 'json');
    for (const [slug, st] of Object.entries((tag && tag.s) || {})) {
      if (!FEEDBACK_SLUG_RE.test(slug)) continue;
      const summe = (await env.ABO.get(`feedback:${slug}`, 'json')) || { ja: 0, nein: 0 };
      summe.ja = Number(summe.ja || 0) + Number(st.ja || 0);
      summe.nein = Number(summe.nein || 0) + Number(st.nein || 0);
      summe.letzte = new Date(zeit).toISOString();
      await env.ABO.put(`feedback:${slug}`, JSON.stringify(summe));
    }
    await env.ABO.delete(key);
  }
}

/** GET /feedback?slug=… – aggregierte Zähler (Summe + heutiger Tag). */
async function feedback_lesen(request, env, url) {
  const slug = String(url.searchParams.get('slug') || '').toLowerCase();
  if (!FEEDBACK_SLUG_RE.test(slug)) {
    return fehler(400, 'Unbekannter Artikel.', env, request);
  }
  const stand = (await env.ABO.get(`feedback:${slug}`, 'json')) || { ja: 0, nein: 0 };
  const tag = (await env.ABO.get(feedback_tag(), 'json')) || {};
  const heute = (tag.s && tag.s[slug]) || { ja: 0, nein: 0 };
  return json({
    ok: true, slug,
    ja: Number(stand.ja || 0) + Number(heute.ja || 0),
    nein: Number(stand.nein || 0) + Number(heute.nein || 0),
  }, 200, env, { 'Cache-Control': 'no-store' });
}

// ---------------------------------------------------------------- Routen
async function health(request, env) {
  let kv_ok = false;
  try {
    await env.ABO.get('healthz');
    kv_ok = true;
  } catch (e) { kv_ok = false; }
  // `takt`: der letzte Dispatch je Takt (digest/kadenz/nachgang) – ohne
  // Adressen, ohne Secrets. Die Zustellbarkeits-Wache (C8) liest hier, ob
  // der Taktgeber am letzten Versandtag wirklich gefeuert hat. Fehlt der
  // Schluessel ganz, laeuft eine Worker-Version ohne Cron-Triggers.
  const angebot = request ? request.headers.get('x-ff-key') : '';
  if (!angebot || !await schluessel_pruefen(env, angebot)) {
    // Oeffentlich nur lebendig/tot – keine Cron-Namen, Workflows, Fehlertexte.
    return json({ ok: kv_ok, ts: new Date().toISOString() }, kv_ok ? 200 : 503, env,
      { 'Cache-Control': 'no-store' });
  }
  const takt = kv_ok ? await takt_lesen(env) : {};
  // Betriebsbild (F-03/F-08, 15.10.2026): Budgetstand, Turnstile-Zustand und
  // die letzten Exporte. Alles NUR mit Schluessel – und ohne Personenbezug
  // (der Export-Abdruck ist ein Kurz-Hash, keine Adresse).
  const heute = kv_ok ? await tagesbudget_stand(env, 'anmeldung') : 0;
  const exporte = kv_ok ? await export_log_lesen(env) : [];
  const leseschluessel = String((env && env.EXPORT_KEY) || '');
  const schreibschluessel = String((env && env.EXPORT_KEY_WRITE) || '');
  const rollenGetrennt = Boolean(leseschluessel && schreibschluessel
    && leseschluessel !== schreibschluessel);
  return json({
    ok: kv_ok, ts: new Date().toISOString(), kv: kv_ok ? 'ok' : 'fehler',
    takt: { crons: Object.keys(TAKT), letzte: takt },
    budget: {
      anmeldung_heute: heute,
      anmeldung_max: Number(env.ANMELDUNG_MAX_PRO_TAG || ANMELDUNG_MAX_PRO_TAG_DEFAULT),
      feedback_max: feedback_max(env),
    },
    turnstile: turnstile_zustand(env),
    schluesselrollen: rollenGetrennt ? 'getrennt' : 'gemeinsam',
    exporte: exporte,
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
  const seite = quelle_pruefen(url.searchParams.get('quelle'), env);
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

  if (!await turnstile_ok(env, erstein(daten, 'cf-turnstile-response'), ip)) {
    return antwort_mit('fehler', 'Die Sicherheitsprüfung hat nicht geklappt – bitte Seite neu laden und erneut absenden.', env, request, 400);
  }
  // Rate-Limit pro IP: mehr als 5 in 15 Min = Botmuster.
  if (!await rate_erlaubt(env, ip, 'anmeldung')) {
    return antwort_mit('fehler', 'Zu viele Anmelde-Versuche in kurzer Zeit. Bitte in ein paar Minuten erneut versuchen – oder schreib eine Mail an kontakt@franksfinanzcheck.de.', env, request, 429);
  }

  // TAGESBUDGET (F-03, 15.10.2026): Der Deckel sitzt VOR jedem Schreibzugriff.
  // Ist er erreicht, wird nichts angelegt, kein Nachweis geschrieben und kein
  // Bestaetigungs-Dispatch ausgeloest. Die Meldung sagt einem Menschen die
  // Wahrheit („ausgelastet, bitte spaeter oder per Mail") und verraet einem
  // Angreifer nichts, was er nicht schon weiss: der Deckel erneuert sich um
  // 00:00 UTC, also taeglich zu einer oeffentlich bekannten Zeit.
  const budget = await tagesbudget_nehmen(
    env, 'anmeldung',
    Number((env && env.ANMELDUNG_MAX_PRO_TAG) || ANMELDUNG_MAX_PRO_TAG_DEFAULT));
  if (!budget.ok) {
    await warnen_einmal(env, 'anmeldung',
      `Tagesbudget erreicht (${budget.stand}/${budget.maximum}) – weitere Anmeldungen werden bis 00:00 UTC nicht angenommen.`);
    return antwort_mit('fehler',
      'Der Anmeldedienst ist heute ausgelastet – bitte versuch es in ein paar Stunden erneut. ' +
      'Ohne Wartezeit geht es formlos an kontakt@franksfinanzcheck.de.',
      env, request, 503);
  }

  const jetzt = new Date().toISOString();
  const bestehend = await abo_lesen(env.ABO, email);
  let eintrag;
  let status;
  let text;

  // EINE Antwort fuer alle Faelle (Audit M-01): Ob eine Adresse schon
  // angemeldet, offen oder neu ist, darf von aussen nicht erkennbar sein.
  status = 'angemeldet';
  text = ANMELDE_ANTWORT;
  if (!bestehend) {
    eintrag = {
      email, norm: email, status: 'pending', token: token_neu(), themen: themen_r,
      seit: jetzt, seite, bestaetigt: null,
      bestaetigung_gesendet: null, versuche: 0, abbestellt: null, grund: null,
    };
  } else if (bestehend.status === 'active' || bestehend.status === 'pending') {
    // Aktiv: nichts tun. Offen: nicht neu triggern (kein Spam) – der
    // Nachgang deckt ab. Antwort identisch zur Neuanmeldung.
    return antwort_mit(status, text, env, request);
  } else if (bestehend.status === 'unsubscribed' || bestehend.status === 'abgelaufen') {
    // Neu- oder Wiederanmeldung: neuer Token, frischer Nachweis, frische Themen.
    eintrag = { ...bestehend, status: 'pending', token: token_neu(), themen: themen_r,
      seit: jetzt, seite, bestaetigt: null,
      bestaetigung_gesendet: null, versuche: 0, abbestellt: null, grund: null };
    delete eintrag.ip;
    delete eintrag.user_agent;
  } else {
    // Unbekannter Status (defekte Daten): fail-closed, laut melden.
    // F-05 (15.10.2026): KEINE Adresse im Log – die Betriebszusage lautet
    // „keine Adressen, keine Tokens, keine IPs". Zur Nachvollziehbarkeit
    // genuegt der Kurz-Hash (derselbe Schluessel wie beim Nachweis).
    console.warn(`ff-newsletter: unbekannter Abo-Status "${String(bestehend.status).slice(0, 24)}" ` +
      `für sha256:${await sha256_kurz(`ff-nl|${email}|v1`)}`);
    return fehler(500, 'Unbekannter Zustand – bitte erneut versuchen oder kontakt@franksfinanzcheck.de schreiben.', env, request);
  }

  eintrag.themen = filtere_themen(themen_r, env);
  await abo_schreiben(env.ABO, eintrag);
  await nachweis_schreiben(env.ABO, eintrag, { ip, ua, seite });

  // Bestätigung auslösen. Scheitert der Dispatch, geht nichts verloren:
  // der Nachgang (schedule) sendet offene Bestätigungen nach.
  const trigg = await dispatch_bestuerung(env);
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
  const sauber = String(token || '').trim();
  if (!sauber) return null;
  const norm = await env.ABO.get(`token:${sauber}`);
  if (!norm) return null;
  const eintrag = await abo_lesen(env.ABO, norm);
  // Auch alte, bereits ausgegebene und verwaiste Tokens nicht akzeptieren.
  return eintrag && eintrag.token === sauber ? eintrag : null;
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
    eintrag.abgelaufen_am = new Date().toISOString();
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
const ANMELDE_ANTWORT = 'Fast geschafft – bitte sieh in dein Postfach. Ist die Adresse noch nicht bestätigt, kommt in den nächsten Minuten eine Bestätigungsmail (Double-Opt-In; auch im Spam-Ordner nachsehen).';

/** GET /abmeldung?token=… zeigt nur eine Bestaetigungsseite (Audit M-03):
 *  Link-Scanner von Mailprogrammen rufen Links per GET auf – sie duerfen
 *  niemanden abmelden. Abgemeldet wird erst per POST (Knopf oder RFC 8058). */
function abmelde_bestaetigung_seite(env, token) {
  const html = HTML_KOPF
    + '<h1>Newsletter abmelden?</h1>'
    + '<p>Ein Klick genügt – danach kommt keine Ausgabe mehr.</p>'
    + '<form method="post" action="/abmeldung">'
    + '<input type="hidden" name="token" value="' + esc(token) + '">'
    + '<button class="btn" type="submit">Ja, abmelden</button>'
    + '</form>'
    + '<p class="hinweis">Formlos geht es auch an '
    + '<a href="mailto:kontakt@franksfinanzcheck.de?subject=Newsletter%20abmelden">kontakt@franksfinanzcheck.de</a>.</p>'
    + HTML_FUSS;
  return html_antwort(html, 200, env);
}

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

  if (token && request.method === 'GET') {
    // Token raten ist aussichtslos (24 Byte Zufall), aber NICHT kostenlos:
    // Jeder Rateversuch ist ein KV-Lesevorgang. Deshalb eigenes Limit für den
    // token-tragenden GET-Weg (F-03, Nachtrag 15.10.2026).
    const ip_token = String(request.headers.get('cf-connecting-ip')
      || request.headers.get('x-forwarded-for') || '').split(',')[0].trim();
    if (!await rate_erlaubt(env, ip_token, 'abmeldung_token')) {
      return antwort_mit('fehler', 'Zu viele Versuche in kurzer Zeit. Bitte in ein paar Minuten erneut versuchen.', env, request, 429);
    }
    const eintrag = await token_eintrag(env, token);
    if (!eintrag) {
      return antwort_mit('unbekannt', 'Dieser Link ist unbekannt – es wurde nichts geändert. Kürzester Weg: das Formular unter franksfinanzcheck.de/newsletter/abmelden/ oder formlos per Mail an kontakt@franksfinanzcheck.de.', env, request, 404);
    }
    if (eintrag.status === 'unsubscribed') {
      return antwort_mit('bereits-abgemeldet', 'Diese Adresse ist bereits abgemeldet – du bekommst keine Ausgabe mehr. Weitere Schritte sind nicht nötig.', env, request);
    }
    if (wantHtml(request)) return abmelde_bestaetigung_seite(env, token);
    return json({ status: 'bestaetigen', text: 'Abmeldung bitte per POST bestätigen (Knopf auf der Seite oder RFC-8058-One-Click).' }, 200, env);
  }

  if (token) {
    // Auch der POST-Weg mit Token wird gezählt (F-03): Der Token steht in der
    // Mail, der Weg ist ohnehin nur für echte Empfänger gedacht.
    const ip_token = String(request.headers.get('cf-connecting-ip')
      || request.headers.get('x-forwarded-for') || '').split(',')[0].trim();
    if (!await rate_erlaubt(env, ip_token, 'abmeldung_token')) {
      return antwort_mit('fehler', 'Zu viele Versuche in kurzer Zeit. Bitte in ein paar Minuten erneut versuchen.', env, request, 429);
    }
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
  if (!await rate_erlaubt(env, ip, 'abmeldung')) {
    return antwort_mit('fehler', 'Zu viele Versuche in kurzer Zeit. Bitte in ein paar Minuten erneut versuchen – oder schreib eine Mail an kontakt@franksfinanzcheck.de.', env, request, 429);
  }
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
  // Der API-Schluessel steht ausschliesslich im Header. Tokens und E-Mail-
  // Adressen fuer Einzel-Lookups werden nur im POST-Body angenommen.
  const angebot = request.headers.get('x-ff-key') || '';
  const schreib_route = ['/export/token', '/export/kontakt', '/export/versuch'].includes(p);
  const darfLesen = await schluessel_pruefen(env, angebot);
  const darfSchreiben = await schreibschluessel_pruefen(env, angebot);
  if (schreib_route ? !darfSchreiben : (!darfLesen && !darfSchreiben)) {
    await export_vermerken(env, p, 0, angebot, 403);
    return new Response(JSON.stringify({ status: 'verboten' }), {
      status: 403, headers: { 'Content-Type': 'application/json; charset=utf-8', ...SICHERHEITS_KOPF },
    });
  }
  if ((p === '/export/abonnenten' || p === '/export/pending') && request.method !== 'GET'
      || (schreib_route && request.method !== 'POST')) {
    return new Response(JSON.stringify({ status: 'methode-nicht-erlaubt' }), {
      status: 405,
      headers: { 'Allow': schreib_route ? 'POST' : 'GET',
        'Content-Type': 'application/json; charset=utf-8', ...SICHERHEITS_KOPF },
    });
  }
  // Mengenbegrenzung auch auf den geschuetzten Exporten (F-08): Ein
  // abgeflossener Schluessel darf die Liste nicht in Sekunden leeren.
  if (!await rate_erlaubt(env, String(request.headers.get('cf-connecting-ip') || 'export'), 'export')) {
    await export_vermerken(env, p, 0, angebot, 429);
    return new Response(JSON.stringify({ status: 'zu-viele-anfragen' }), {
      status: 429, headers: { 'Content-Type': 'application/json; charset=utf-8', ...SICHERHEITS_KOPF },
    });
  }
  if (p === '/export/abonnenten') {
    // Der Leseschluessel liefert Adressen/Themen, aber nie Token. Auch bei
    // ausdruecklichem `mit_token=1` ist der zweite, getrennte Schluessel Pflicht.
    const darfToken = url.searchParams.get('mit_token') === '1' && darfSchreiben;
    const keys = await liste_mit_prefix(env.ABO, 'abo:');
    const aktiv = [];
    for (const key of keys) {
      const eintrag = await env.ABO.get(key, 'json');
      if (eintrag && eintrag.status === 'active') {
        const zeile = { email: eintrag.email, themen: eintrag.themen || [], bestaetigt: eintrag.bestaetigt };
        if (darfToken) zeile.token = eintrag.token;
        aktiv.push(zeile);
      }
    }
    await export_vermerken(env, p, aktiv.length, angebot, 200);
    return json({
      ts: new Date().toISOString(), anzahl: aktiv.length,
      mit_token: darfToken, abonnenten: aktiv,
    }, 200, env);
  }
  if (p === '/export/pending') {
    const darfToken = url.searchParams.get('mit_token') === '1' && darfSchreiben;
    const keys = await liste_mit_prefix(env.ABO, 'abo:');
    const offen = [];
    for (const key of keys) {
      const eintrag = await env.ABO.get(key, 'json');
      if (eintrag && eintrag.status === 'pending') {
        const zeile = {
          email: eintrag.email, seit: eintrag.seit,
          bestaetigung_gesendet: eintrag.bestaetigung_gesendet, versuche: eintrag.versuche || 0,
        };
        if (darfToken) zeile.token = eintrag.token;
        offen.push(zeile);
      }
    }
    await export_vermerken(env, p, offen.length, angebot, 200);
    return json({ ts: new Date().toISOString(), anzahl: offen.length, mit_token: darfToken, offen }, 200, env);
  }
  if (p === '/export/token') {
    const daten = await koerper_lesen(request);
    const token = String((daten && daten.token && daten.token[0]) || '').trim();
    const eintrag = token ? await token_eintrag(env, token) : null;
    if (!eintrag) return json({ status: 'unbekannt' }, 404, env);
    await export_vermerken(env, p, 1, angebot, 200);
    return json({
      status: eintrag.status, email: eintrag.email, token: eintrag.token,
      themen: eintrag.themen || [], seit: eintrag.seit, bestaetigt: eintrag.bestaetigt,
      abbestellt: eintrag.abbestellt, grund: eintrag.grund || null,
    }, 200, env);
  }
  if (p === '/export/kontakt') {
    const daten = await koerper_lesen(request);
    const email = email_norm(String((daten && daten.email && daten.email[0]) || ''));
    const eintrag = email ? await abo_lesen(env.ABO, email) : null;
    if (!eintrag) return json({ status: 'unbekannt' }, 404, env);
    await export_vermerken(env, p, 1, angebot, 200);
    return json({
      status: eintrag.status, email: eintrag.email, token: eintrag.token,
      themen: eintrag.themen || [],
    }, 200, env);
  }
  if (p === '/export/versuch') {
    const daten = await koerper_lesen(request);
    const token = String((daten && daten.token && daten.token[0]) || '').trim();
    const ergebnis = String((daten && daten.ergebnis && daten.ergebnis[0]) || 'gesendet');
    if (!['gesendet', 'abgelaufen', 'bounce'].includes(ergebnis)) {
      return new Response(JSON.stringify({ status: 'ungueltiges-ergebnis' }), {
        status: 400, headers: { 'Content-Type': 'application/json; charset=utf-8', ...SICHERHEITS_KOPF },
      });
    }
    const eintrag = token ? await token_eintrag(env, token) : null;
    if (!eintrag) return json({ status: 'unbekannt' }, 404, env);
    const jetzt = new Date().toISOString();
    if (ergebnis === 'gesendet' && eintrag.status === 'pending') {
      eintrag.versuche = (eintrag.versuche || 0) + 1;
      eintrag.bestaetigung_gesendet = jetzt;
      if (eintrag.versuche >= MAX_VERSEND_VERSUCHE) { eintrag.status = 'abgelaufen'; eintrag.abgelaufen_am = jetzt; }
    } else if (ergebnis === 'abgelaufen') {
      eintrag.status = 'abgelaufen';
      eintrag.abgelaufen_am = jetzt;
    } else if (ergebnis === 'bounce') {
      // Harte Bounce: Unterdruckung, keine Weiterleitung, kein Retry.
      eintrag.status = 'unsubscribed';
      eintrag.abbestellt = jetzt;
      eintrag.grund = 'bounce';
    }
    await abo_schreiben(env.ABO, eintrag);
    await export_vermerken(env, p, 1, angebot, 200);
    return json({ status: 'ok', abo_status: eintrag.status, versuche: eintrag.versuche || 0 }, 200, env);
  }
  return new Response(JSON.stringify({ status: 'unbekannt' }), {
    status: 404, headers: { 'Content-Type': 'application/json; charset=utf-8', ...SICHERHEITS_KOPF },
  });
}

// ---------------------------------------------------------------- Einstieg
/**
 * Mengenbegrenzung je Route-Klasse (F-03, 15.10.2026): VORHER liefen
 * `/bestaetigung`, `/praeferenzen`, `/status`, `/feedback` (GET) und der
 * Export voellig ungebremst – 50.000 Anfragen genuegten, um das KV-Lesekontingent
 * des Free-Plans zu leeren; danach fielen Anmeldung, Bestaetigung, Abmeldung
 * und der Pflegelauf aus. Jetzt hat JEDE Route eine Klasse:
 *   · lesen  – die Token-Seiten (GET): Standard 60 Anfragen je Minute
 *   · feedback – Stimmen und Zaehlerstand: Standard 30 je Minute
 *   · export – geschuetzte Exporte: Standard 20 je Minute
 * Ohne Binding faellt die Pruefung auf den KV-Zaehler zurueck (Altverhalten);
 * die Grenzen sind per Env-Variable justierbar (RATE_LIMIT_<KLASSE>).
 */
const LIMIT_KLASSEN = {
  lesen: { standard: 60, env: 'RATE_LIMIT_LESEN' },
  feedback: { standard: 30, env: 'RATE_LIMIT_FEEDBACK' },
  export: { standard: 20, env: 'RATE_LIMIT_EXPORT' },
};

function limit_klasse(pfad, methode) {
  if (pfad.startsWith('/export/')) return 'export';
  if (pfad === '/feedback') return 'feedback';
  if (methode === 'GET') return 'lesen';
  return null; // POST-Routen haben ihre eigenen, strengeren Limits
}

/**
 * Rueckfall-Zaehler im Speicher der Worker-Instanz (F-03).
 * Kostenlos (kein KV-Schreibzugriff) und ohne Zustand zwischen Aufrufen –
 * dafür gilt er nur je Instanz und nur für eine Minute. Genau dafür reicht er:
 * Ein einzelner Absender trifft in der Regel dieselbe Instanz am selben Ort,
 * und dort greift der Deckel sofort. Gegen einen verteilten Sturm steht die
 * WAF-Mengenregel der Zone an der Edge (cloudflare/edge-schutz.md, A2) –
 * die zaehlt, bevor ueberhaupt eine Instanz startet.
 */
const MENGE_SPEICHER = new Map();
const MENGE_MAX_EINTRAEGE = 5000;

function menge_speicher_pruefen(schluessel, grenze, jetzt = Date.now()) {
  const fenster = Math.floor(jetzt / 60000);
  const stand = MENGE_SPEICHER.get(schluessel);
  if (!stand || stand.fenster !== fenster) {
    if (MENGE_SPEICHER.size >= MENGE_MAX_EINTRAEGE) MENGE_SPEICHER.clear();
    MENGE_SPEICHER.set(schluessel, { fenster, zaehler: 1 });
    return true;
  }
  stand.zaehler += 1;
  return stand.zaehler <= grenze;
}

/** Nur fuer Tests: Der Rueckfall-Zaehler ist Prozesszustand, kein KV-Wert. */
function menge_speicher_zuruecksetzen() {
  MENGE_SPEICHER.clear();
}

async function menge_erlaubt(env, klasse, request) {
  if (!klasse) return true;
  const grenze = Number((env && env[LIMIT_KLASSEN[klasse].env]) || 0)
    || LIMIT_KLASSEN[klasse].standard;
  const ip = String(request.headers.get('cf-connecting-ip')
    || request.headers.get('x-forwarded-for') || 'unbekannt').split(',')[0].trim();
  if (env && env.RATE_LIMITER && typeof env.RATE_LIMITER.limit === 'function') {
    try {
      const { success } = await env.RATE_LIMITER.limit({
        key: await sha256_kurz(`menge|${klasse}|${ip}`),
      });
      return success !== false;
    } catch (e) { /* Binding gestoert → Rueckfall unten */ }
  }
  return menge_speicher_pruefen(`${klasse}|${ip}`, grenze);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const p = url.pathname;
    if (request.method === 'OPTIONS') return vorabfrage(env);
    try {
      if (p === '/' || p === '/healthz') return await health(request, env);
      // CSRF-Schutz (Audit M-02): POST aus fremden Browser-Urspruengen ablehnen.
      // Server-zu-Server-Exporte ohne Origin bleiben erlaubt; Browser-Aufrufe
      // aus fremden Origins werden auch dort vor der Schluesselpruefung gestoppt.
      if (request.method === 'POST' && !herkunft_erlaubt(request, env, url)) {
        return fehler(403, 'Anfrage von einer fremden Seite abgelehnt.', env, request);
      }
      // Mengenbegrenzung (F-03) – greift fuer lesende Routen und den Export.
      const klasse = limit_klasse(p, request.method);
      if (!await menge_erlaubt(env, klasse, request)) {
        return fehler(429, 'Zu viele Anfragen in kurzer Zeit – bitte einen Moment warten.',
          env, request);
      }
      if (p === '/anmeldung' && request.method === 'POST') return await anmeldung(request, env, url);

      if (p === '/feedback' && request.method === 'POST') return await feedback(request, env);
      if (p === '/feedback' && request.method === 'GET') return await feedback_lesen(request, env, url);
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
    const arbeit = controller && controller.cron === PFLEGE_CRON
      ? datenschutz_pflege(env, controller.scheduledTime || Date.now())
      : takt_ausfuehren(env, controller && controller.cron, controller && controller.scheduledTime);
    if (ctx && typeof ctx.waitUntil === 'function') ctx.waitUntil(arbeit);
    return arbeit;
  },
};

// Fuer Tests (node --test): die Takt-Tabelle und der Ausfuehrer ohne Cloudflare.
export {
  TAKT, takt_ausfuehren, takt_fuer, datenschutz_pflege, PFLEGE_CRON, feedback_aufrollen,
  // Sicherheitsrelevante Entscheidungen werden direkt geprueft, nicht ueber
  // Umwege (Audit 15.10.2026): Schluesselrollen, Tagesbudget, Mengenklassen.
  schluessel_pruefen, schreibschluessel_pruefen, tagesbudget_nehmen, tagesbudget_stand,
  limit_klasse, warnen_einmal, schluessel_fingerabdruck, ANMELDUNG_MAX_PRO_TAG_DEFAULT,
  menge_speicher_pruefen, menge_speicher_zuruecksetzen, export_speicher_zuruecksetzen,
  // Paar-Vertrag Turnstile (WF-E813 / #809): der Zustand ist eine eigene
  // sicherheitsrelevante Entscheidung und wird direkt geprueft.
  turnstile_zustand,
};
