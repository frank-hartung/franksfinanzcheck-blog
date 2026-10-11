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
//    - Max. 512 Bytes Payload, kein Lesen von Headern außer Origin/DNT/GPC.
//    - Rate-Limit: im Cloudflare-Dashboard als WAF-Regel (siehe Runbook).
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
 * Partner, nur ohne Artikelzuordnung.
 */
export function pruefeEreignis(daten, bekannteSchluessel = GATEWAY_KEYS) {
  if (!daten || typeof daten !== "object") return { ok: false, grund: "kein-objekt" };
  const k = typeof daten.k === "string" ? daten.k : "";
  if (!KEY_RE.test(k) || !bekannteSchluessel.includes(k)) {
    return { ok: false, grund: "unbekannter-schluessel" };
  }
  const s = typeof daten.s === "string" ? daten.s.trim() : "";
  const artikel = SLUG_RE.test(s) ? s : "unbekannt";
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
export async function erfasse(request, env, now = new Date()) {
  if (env.KLICKS_AUS === "1") return leer(204);
  if (request.headers.get("DNT") === "1" || request.headers.get("Sec-GPC") === "1") {
    return leer(204);
  }
  const origin = request.headers.get("Origin") || "";
  if (!ERLAUBTE_URSPRUNGE.has(origin)) return leer(403);

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
  const ev = pruefeEreignis(daten);
  if (!ev.ok) return leer(400);

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
