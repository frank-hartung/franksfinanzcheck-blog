// ============================================================
//  KLICK-ZÄHLER – cookieloser, aggregierter /go/-Zähler (Cloudflare Worker + D1)
//  ------------------------------------------------------------
//  Zweck:   Zählt, wie oft jede /go/-Übergabeseite aufgerufen wird
//           (= Klick auf einen Partnerlink), je Artikel und Tag.
//  Ort:     https://stats.franksfinanzcheck.de/e  (eigene Subdomain,
//           Cloudflare-Zone – die Hauptdomain bleibt unverändert)
//
//  WAS GESPEICHERT WIRD (und was nicht):
//    gespeichert:  Tag (Europe/Berlin), Gateway-Schlüssel (z. B. "strom"),
//                  Artikel-Slug aus ?subid=, Zähler.
//    NICHT:        IP-Adresse, User-Agent, Referrer, Cookie, Kennung,
//                  Zeitstempel je Klick. Nur tägliche Summen.
//    Respektiert:  Do-Not-Track (DNT: 1) und Global Privacy Control
//                  (Sec-GPC: 1) – dann wird nichts gezählt.
//    Kill-Switch:  Variable KLICKS_AUS = "1" → nichts wird gezählt.
//
//  SICHERHEIT:
//    - Nur Anfragen mit Origin franksfinanzcheck.de (ohne/mit www).
//    - Nur bekannte Gateway-Schlüssel (gateway-keys.mjs, generiert aus
//      scripts/check24_links.yaml – Drift prüft test/worker.test.mjs).
//    - Nur bekannte Artikel (Sicherheitsaudit 14.10.2026, N-05): Der
//      Artikel-Slug zählt nur, wenn er in der LIVE-Sitemap von
//      franksfinanzcheck.de steht (stündlich geladen, im Speicher gehalten).
//      Erfundene Slugs werden zu "unbekannt" – die D1-Tabelle lässt sich
//      nicht mehr mit Zufalls-Slugs fluten, und neue Artikel zählen ohne
//      erneuten Worker-Deploy, sobald sie in der Sitemap stehen.
//    - Max. 512 Bytes Payload, kein Lesen von Headern außer Origin/DNT/GPC
//      und – nur flüchtig, nie gespeichert – CF-Connecting-IP als Schlüssel
//      der Mengenbegrenzung.
//    - Rate-Limit: Binding KLICK_LIMITER (wrangler.toml, 30 Ereignisse je
//      60 s und Verbindung) + optional WAF-Regel im Dashboard (Runbook).
//      Die Origin-Prüfung allein ist per curl fälschbar – deshalb beides.
//
//  Deploy/Betrieb: docs/ANLEITUNG-KLICKMESSUNG-OHNE-COOKIES.md
// ============================================================

import { GATEWAY_KEYS } from "./gateway-keys.mjs";

export const ERLAUBTE_URSPRUNGE = new Set([
  "https://franksfinanzcheck.de",
  "https://www.franksfinanzcheck.de",
]);
export const MAX_BYTES = 512;
const KEY_RE = /^[a-z0-9][a-z0-9-]{1,39}$/;
const SLUG_RE = /^[a-z0-9][a-z0-9-]{2,119}$/;
export const SITEMAP_STANDARD = "https://franksfinanzcheck.de/sitemap.xml";
const ARTIKEL_TTL_MS = 60 * 60 * 1000; // Sitemap höchstens stündlich laden
const ARTIKEL_ALT_MS = 24 * 60 * 60 * 1000; // bei Ausfall: alte Liste ≤ 24 h weiter nutzen
const ARTIKEL_PAUSE_MS = 5 * 60 * 1000; // nach Fehlschlag: 5 min kein neuer Abruf
const SITEMAP_MAX_ZEICHEN = 5_000_000;
const SITEMAP_LOC_RE =
  /<loc>\s*https:\/\/(?:www\.)?franksfinanzcheck\.de\/posts\/([a-z0-9][a-z0-9-]{2,119})\/?\s*<\/loc>/g;

let artikelCache = { liste: null, geladen: 0, pauseBis: 0 };

/** Nur für Tests: Zwischenspeicher der Artikelliste leeren. */
export function _artikelCacheLeeren() {
  artikelCache = { liste: null, geladen: 0, pauseBis: 0 };
}

/** Artikel-Slugs aus der Hugo-Sitemap (nur /posts/<slug>/ der eigenen Domain). */
export function artikelAusSitemap(xml) {
  const liste = new Set();
  for (const treffer of String(xml || "").matchAll(SITEMAP_LOC_RE)) liste.add(treffer[1]);
  return liste;
}

/**
 * Liste der veröffentlichten Artikel. Quelle ist die Live-Sitemap. Fällt sie
 * aus, gilt die letzte bekannte Liste bis zu 24 h weiter; ohne Liste zählt
 * jeder Klick nur noch für den Partner (Artikel "unbekannt") – fail closed.
 */
export async function ladeArtikel(env = {}, jetzt = Date.now(), holen = globalThis.fetch) {
  const { liste, geladen, pauseBis } = artikelCache;
  if (liste && jetzt - geladen < ARTIKEL_TTL_MS) return liste;
  if (jetzt >= pauseBis && typeof holen === "function") {
    try {
      const antwort = await holen(env.SITEMAP_URL || SITEMAP_STANDARD, {
        headers: { Accept: "application/xml,text/xml" },
        signal: AbortSignal.timeout(3000),
        cf: { cacheTtl: 900, cacheEverything: true },
      });
      if (antwort && antwort.ok) {
        const neu = artikelAusSitemap((await antwort.text()).slice(0, SITEMAP_MAX_ZEICHEN));
        if (neu.size > 0) {
          artikelCache = { liste: neu, geladen: jetzt, pauseBis: 0 };
          return neu;
        }
      }
    } catch {
      // Netzfehler/Zeitüberschreitung → unten weiter mit alter Liste
    }
    artikelCache = { ...artikelCache, pauseBis: jetzt + ARTIKEL_PAUSE_MS };
  }
  if (liste && jetzt - geladen < ARTIKEL_ALT_MS) return liste;
  return new Set();
}

/** Kalendertag in Europe/Berlin als YYYY-MM-DD (Geschäftstag, nicht UTC). */
export function berlinDatum(date = new Date()) {
  const teile = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Berlin",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const wert = (typ) => teile.find((t) => t.type === typ).value;
  return `${wert("year")}-${wert("month")}-${wert("day")}`;
}

/**
 * Prüft die Nutzlast. Gibt { ok, k, s } zurück. Unbekannte oder ungültige
 * Artikel-Slugs werden zu "unbekannt" – der Klick zählt trotzdem für den
 * Partner, nur ohne Artikelzuordnung. `bekannteArtikel` (Set) ist die
 * Allowlist; erfasse() übergibt sie immer (N-05). Ohne Set wird nur das
 * Format geprüft (reine Formatprüfung für Werkzeuge/Tests).
 */
export function pruefeEreignis(daten, bekannteSchluessel = GATEWAY_KEYS, bekannteArtikel = null) {
  if (!daten || typeof daten !== "object") return { ok: false, grund: "kein-objekt" };
  const k = typeof daten.k === "string" ? daten.k : "";
  if (!KEY_RE.test(k) || !bekannteSchluessel.includes(k)) {
    return { ok: false, grund: "unbekannter-schluessel" };
  }
  const s = typeof daten.s === "string" ? daten.s.trim() : "";
  const formatOk = SLUG_RE.test(s);
  const bekannt = bekannteArtikel instanceof Set ? bekannteArtikel.has(s) : true;
  const artikel = formatOk && bekannt ? s : "unbekannt";
  return { ok: true, k, s: artikel };
}

function leer(status) {
  return new Response(null, { status });
}

/**
 * Hauptlogik. `db` ist ein D1-Binding (prepare/bind/run).
 * Gibt immer 204 zurück, wenn eine gültige Anfrage verarbeitet wurde,
 * damit ein Browser nichts über die Zählung erfährt.
 */
export async function erfasse(request, env, now = new Date(), artikelQuelle = ladeArtikel) {
  if (env.KLICKS_AUS === "1") return leer(204);
  if (request.headers.get("DNT") === "1" || request.headers.get("Sec-GPC") === "1") {
    return leer(204);
  }
  const origin = request.headers.get("Origin") || "";
  if (!ERLAUBTE_URSPRUNGE.has(origin)) return leer(403);

  // Mengenbegrenzung (N-05): Origin ist per curl fälschbar. Der Schlüssel
  // (Verbindungs-IP) wird nur flüchtig im Rate-Limiter gezählt, nie gespeichert.
  if (env.KLICK_LIMITER && typeof env.KLICK_LIMITER.limit === "function") {
    const schluessel = request.headers.get("CF-Connecting-IP") || "ohne-ip";
    try {
      const { success } = await env.KLICK_LIMITER.limit({ key: schluessel });
      if (!success) return leer(429);
    } catch {
      // Limiter gestört → zählen erlaubt (Zähler ist nicht sicherheitskritisch)
    }
  }

  const laenge = Number(request.headers.get("Content-Length") || 0);
  if (laenge > MAX_BYTES) return leer(413);
  const text = await request.text();
  if (text.length > MAX_BYTES) return leer(413);

  let daten;
  try {
    daten = JSON.parse(text);
  } catch {
    return leer(400);
  }
  if (!pruefeEreignis(daten).ok) return leer(400);
  const ev = pruefeEreignis(daten, GATEWAY_KEYS, await artikelQuelle(env));

  await env.DB.prepare(
    `INSERT INTO klicks (tag, go_key, artikel, anzahl) VALUES (?, ?, ?, 1)
     ON CONFLICT(tag, go_key, artikel) DO UPDATE SET anzahl = anzahl + 1`,
  )
    .bind(berlinDatum(now), ev.k, ev.s)
    .run();
  return leer(204);
}

/**
 * Aufbewahrungsfrist: Tageszähler werden höchstens 13 Monate gespeichert
 * (so steht es in der Datenschutzerklärung, Abschnitt 5). Stichtag ist derselbe
 * Kalendertag vor 13 Monaten (Europe/Berlin); gibt es ihn im Zielmonat nicht,
 * gilt dessen letzter Tag. Zeilen mit tag < Stichtag werden gelöscht.
 */
export function fristStichtag(now = new Date(), monate = 13) {
  const [j, m, t] = berlinDatum(now).split("-").map(Number);
  const gesamt = j * 12 + (m - 1) - monate;
  const zielJahr = Math.floor(gesamt / 12);
  const zielMonat = (gesamt % 12) + 1;
  const letzterTag = new Date(Date.UTC(zielJahr, zielMonat, 0)).getUTCDate();
  const tag = Math.min(t, letzterTag);
  return `${zielJahr}-${String(zielMonat).padStart(2, "0")}-${String(tag).padStart(2, "0")}`;
}

/**
 * Löschlauf (Cron-Trigger in wrangler.toml). Läuft auch bei KLICKS_AUS = "1":
 * Der Kill-Switch stoppt das Zählen, nicht die Einhaltung der Löschfrist.
 */
export async function bereinige(env, now = new Date()) {
  const stichtag = fristStichtag(now);
  const ergebnis = await env.DB.prepare("DELETE FROM klicks WHERE tag < ?")
    .bind(stichtag)
    .run();
  return { stichtag, ergebnis };
}

export default {
  async scheduled(_event, env, ctx) {
    ctx.waitUntil(bereinige(env));
  },
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname === "/healthz" && request.method === "GET") {
      return new Response("ok", { status: 200, headers: { "Content-Type": "text/plain" } });
    }
    if (url.pathname === "/e" && request.method === "POST") {
      return erfasse(request, env);
    }
    return leer(404);
  },
};
