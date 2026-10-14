// Vertragstests für den Klick-Zähler (ohne Netz, ohne Cloudflare).
// Ausführen: cd cloudflare/klick-zaehler && npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import worker, {
  erfasse, pruefeEreignis, berlinDatum, MAX_BYTES,
  artikelAusSitemap, ladeArtikel, _artikelCacheLeeren,
} from "../worker.js";
import { GATEWAY_KEYS } from "../gateway-keys.mjs";

const HIER = dirname(fileURLToPath(import.meta.url));

// Tests laufen ohne Netz: Ein versehentlicher Sitemap-Abruf scheitert sofort
// (→ fail closed, Artikel "unbekannt") statt echte Anfragen zu schicken.
globalThis.fetch = async () => {
  throw new Error("kein Netz in Tests");
};
const ARTIKEL = new Set(["2026-10-02-gasabschlag-berechnen"]);
const bekannteArtikel = async () => ARTIKEL;

function fakeDb() {
  const aufrufe = [];
  return {
    aufrufe,
    prepare(sql) {
      return {
        bind(...werte) {
          return {
            async run() {
              aufrufe.push({ sql, werte });
              return { success: true };
            },
          };
        },
      };
    },
  };
}

function anfrage(body, kopf = {}) {
  const text = typeof body === "string" ? body : JSON.stringify(body);
  const headers = new Headers({
    Origin: "https://franksfinanzcheck.de",
    "Content-Type": "text/plain;charset=UTF-8",
    "Content-Length": String(new TextEncoder().encode(text).length),
    ...kopf,
  });
  return new Request("https://stats.franksfinanzcheck.de/e", { method: "POST", headers, body: text });
}

const JETZT = new Date("2026-10-11T10:00:00Z");

test("gültiger Klick wird als Tageszähler upserted und 204 beantwortet", async () => {
  const db = fakeDb();
  const r = await erfasse(anfrage({ k: "strom", s: "2026-10-02-gasabschlag-berechnen" }), { DB: db }, JETZT, bekannteArtikel);
  assert.equal(r.status, 204);
  assert.equal(db.aufrufe.length, 1);
  assert.match(db.aufrufe[0].sql, /ON CONFLICT\(tag, go_key, artikel\) DO UPDATE SET anzahl = anzahl \+ 1/);
  assert.deepEqual(db.aufrufe[0].werte, ["2026-10-11", "strom", "2026-10-02-gasabschlag-berechnen"]);
});

test("fremde Herkunft wird abgewiesen (403), nichts gezählt", async () => {
  const db = fakeDb();
  const r = await erfasse(anfrage({ k: "strom", s: "" }, { Origin: "https://spam.example" }), { DB: db }, JETZT);
  assert.equal(r.status, 403);
  assert.equal(db.aufrufe.length, 0);
});

test("ohne Origin wird abgewiesen", async () => {
  const db = fakeDb();
  const req = new Request("https://stats.franksfinanzcheck.de/e", {
    method: "POST",
    headers: { "Content-Length": "20" },
    body: JSON.stringify({ k: "strom" }),
  });
  const r = await erfasse(req, { DB: db }, JETZT);
  assert.equal(r.status, 403);
});

test("www-Variante ist erlaubt", async () => {
  const db = fakeDb();
  const r = await erfasse(anfrage({ k: "gas", s: "" }, { Origin: "https://www.franksfinanzcheck.de" }), { DB: db }, JETZT);
  assert.equal(r.status, 204);
});

test("Do-Not-Track und Global Privacy Control: nichts wird gezählt", async () => {
  for (const kopf of [{ DNT: "1" }, { "Sec-GPC": "1" }]) {
    const db = fakeDb();
    const r = await erfasse(anfrage({ k: "strom", s: "" }, kopf), { DB: db }, JETZT);
    assert.equal(r.status, 204, JSON.stringify(kopf));
    assert.equal(db.aufrufe.length, 0, JSON.stringify(kopf));
  }
});

test("Kill-Switch KLICKS_AUS=1 zählt nichts", async () => {
  const db = fakeDb();
  const r = await erfasse(anfrage({ k: "strom", s: "" }), { DB: db, KLICKS_AUS: "1" }, JETZT);
  assert.equal(r.status, 204);
  assert.equal(db.aufrufe.length, 0);
});

test("unbekannter Gateway-Schlüssel wird abgewiesen (400)", async () => {
  const db = fakeDb();
  for (const k of ["unbekannt-xyz", "../admin", "", "STROM", "a"]) {
    const r = await erfasse(anfrage({ k, s: "" }), { DB: db }, JETZT);
    assert.equal(r.status, 400, k);
  }
  assert.equal(db.aufrufe.length, 0);
});

test("ungültiger Artikel-Slug wird zu 'unbekannt', der Klick zählt trotzdem", async () => {
  const db = fakeDb();
  await erfasse(anfrage({ k: "dsl", s: "../../etc/passwd" }), { DB: db }, JETZT);
  assert.equal(db.aufrufe[0].werte[2], "unbekannt");
  await erfasse(anfrage({ k: "dsl" }), { DB: db }, JETZT);
  assert.equal(db.aufrufe[1].werte[2], "unbekannt");
});

test("zu große Nutzlast wird abgewiesen (413)", async () => {
  const db = fakeDb();
  const gross = JSON.stringify({ k: "strom", s: "x".repeat(MAX_BYTES) });
  const r = await erfasse(anfrage(gross), { DB: db }, JETZT);
  assert.equal(r.status, 413);
  assert.equal(db.aufrufe.length, 0);
});

test("kaputtes JSON wird abgewiesen (400)", async () => {
  const db = fakeDb();
  const r = await erfasse(anfrage("{kaputt"), { DB: db }, JETZT);
  assert.equal(r.status, 400);
});

test("Tag wird in Europe/Berlin gebildet (nicht UTC)", () => {
  // 22:30 UTC am 11.10. ist 00:30 Uhr am 12.10. in Berlin
  assert.equal(berlinDatum(new Date("2026-10-11T22:30:00Z")), "2026-10-12");
  assert.equal(berlinDatum(new Date("2026-10-11T10:00:00Z")), "2026-10-11");
});

test("Routing: /healthz 200, falsche Pfade 404, GET auf /e 404", async () => {
  const env = { DB: fakeDb() };
  const h = await worker.fetch(new Request("https://stats.franksfinanzcheck.de/healthz"), env);
  assert.equal(h.status, 200);
  const x = await worker.fetch(new Request("https://stats.franksfinanzcheck.de/anders"), env);
  assert.equal(x.status, 404);
  const g = await worker.fetch(new Request("https://stats.franksfinanzcheck.de/e", { method: "GET" }), env);
  assert.equal(g.status, 404);
});

test("pruefeEreignis: Schlüssel muss in der Liste stehen", () => {
  assert.equal(pruefeEreignis({ k: "strom" }, ["strom"]).ok, true);
  assert.equal(pruefeEreignis({ k: "gas" }, ["strom"]).ok, false);
  assert.equal(pruefeEreignis(null).ok, false);
});

test("Liste enthält alle /go/-Schlüssel der Registry (Drift ist per klick_import.py --pruefe-keys prüfbar)", () => {
  const datei = readFileSync(join(HIER, "..", "gateway-keys.mjs"), "utf-8");
  assert.ok(GATEWAY_KEYS.length >= 10, "Liste ist ungewöhnlich kurz");
  for (const k of GATEWAY_KEYS) assert.match(datei, new RegExp(`"${k}"`));
});

test("schema.sql enthält die Tabelle und den Primärschlüssel", () => {
  const sql = readFileSync(join(HIER, "..", "schema.sql"), "utf-8");
  assert.match(sql, /CREATE TABLE IF NOT EXISTS klicks/);
  assert.match(sql, /PRIMARY KEY \(tag, go_key, artikel\)/);
});

test("wrangler.toml: routes steht vor allen Tabellen (sonst wirkt die Domain-Bindung nicht)", () => {
  const toml = readFileSync(join(HIER, "..", "wrangler.toml"), "utf8");
  const zeilen = toml.split("\n").map((z) => z.trim());
  const routesIdx = zeilen.findIndex((z) => z.startsWith("routes ="));
  const ersteTabelle = zeilen.findIndex((z) => z.startsWith("["));
  assert.ok(routesIdx >= 0, "routes fehlt");
  assert.ok(ersteTabelle === -1 || routesIdx < ersteTabelle, "routes steht nach einer Tabelle");
  assert.match(toml, /pattern = "stats\.franksfinanzcheck\.de"/);
});

// --- Aufbewahrung (13 Monate) und Löschlauf -------------------------------

import { fristStichtag, bereinige } from "../worker.js";

test("fristStichtag: gleicher Kalendertag vor 13 Monaten (Europe/Berlin)", () => {
  assert.equal(fristStichtag(new Date("2026-10-11T12:00:00Z")), "2025-09-11");
  // 31.03. -> Februar: letzter Tag des Zielmonats
  assert.equal(fristStichtag(new Date("2026-03-31T12:00:00Z")), "2025-02-28");
  // Schaltjahr: 29.02.2028 -> 29.01.2027 existiert, 2028-02-29 -> 2027-02-28
  assert.equal(fristStichtag(new Date("2028-02-29T12:00:00Z")), "2027-01-29");
  // 23:30 UTC am 10.10. ist in Berlin bereits 01:30 am 11.10. -> Stichtag vom 11.
  // (Mit UTC-Tag wäre es 2025-09-10.)
  assert.equal(fristStichtag(new Date("2026-10-10T23:30:00Z")), "2025-09-11");
});

test("bereinige: löscht Zeilen vor dem Stichtag, auch bei KLICKS_AUS=1", async () => {
  const db = fakeDb();
  const env = { DB: db, KLICKS_AUS: "1" };
  const { stichtag } = await bereinige(env, new Date("2026-10-11T12:00:00Z"));
  assert.equal(stichtag, "2025-09-11");
  assert.equal(db.aufrufe.length, 1);
  assert.match(db.aufrufe[0].sql, /DELETE FROM klicks WHERE tag < \?/);
  assert.deepEqual(db.aufrufe[0].werte, ["2025-09-11"]);
});

test("scheduled-Handler ist exportiert und stößt den Löschlauf an", async () => {
  const db = fakeDb();
  let wartet = null;
  const ctx = { waitUntil(p) { wartet = p; } };
  await worker.scheduled({ scheduledTime: Date.now() }, { DB: db }, ctx);
  assert.ok(wartet, "waitUntil wurde nicht aufgerufen");
  await wartet;
  assert.equal(db.aufrufe.length, 1);
});

test("wrangler.toml: täglicher Cron-Trigger für den Löschlauf ist gesetzt", () => {
  const toml = readFileSync(join(HIER, "..", "wrangler.toml"), "utf-8");
  assert.match(toml, /\[triggers\][\s\S]*crons\s*=\s*\["[^"]+"\]/);
});

// ---- Sicherheitsaudit 14.10.2026, N-05: Slug-Allowlist + Mengenbegrenzung ----

test("N-05: erfundener, formal gültiger Slug zählt nur als 'unbekannt' (keine Tabellenflut)", async () => {
  const db = fakeDb();
  for (const s of ["2099-01-01-zufall-a1b2c3", "aaa-bbb-ccc", "2026-10-02-gasabschlag-berechnen-x"]) {
    const r = await erfasse(anfrage({ k: "strom", s }), { DB: db }, JETZT, bekannteArtikel);
    assert.equal(r.status, 204, s);
  }
  assert.deepEqual(db.aufrufe.map((a) => a.werte[2]), ["unbekannt", "unbekannt", "unbekannt"]);
});

test("N-05: ohne erreichbare Sitemap zählt der Klick nur für den Partner (fail closed)", async () => {
  _artikelCacheLeeren();
  const db = fakeDb();
  const r = await erfasse(anfrage({ k: "gas", s: "2026-10-02-gasabschlag-berechnen" }), { DB: db }, JETZT);
  assert.equal(r.status, 204);
  assert.deepEqual(db.aufrufe[0].werte, ["2026-10-11", "gas", "unbekannt"]);
});

test("N-05: pruefeEreignis mit Allowlist – nur gelistete Slugs bleiben erhalten", () => {
  assert.equal(pruefeEreignis({ k: "strom", s: "aaa-bbb" }, ["strom"], new Set(["aaa-bbb"])).s, "aaa-bbb");
  assert.equal(pruefeEreignis({ k: "strom", s: "ccc-ddd" }, ["strom"], new Set(["aaa-bbb"])).s, "unbekannt");
  assert.equal(pruefeEreignis({ k: "strom", s: "aaa-bbb" }, ["strom"], new Set()).s, "unbekannt");
});

test("N-05: artikelAusSitemap nimmt nur /posts/<slug>/ der eigenen Domain", () => {
  const xml = `<urlset>
    <url><loc>https://franksfinanzcheck.de/posts/2026-08-10-dsl-wechselbonus-sichern/</loc></url>
    <url><loc>https://www.franksfinanzcheck.de/posts/zweiter-artikel/</loc></url>
    <url><loc>https://franksfinanzcheck.de/impressum/</loc></url>
    <url><loc>https://franksfinanzcheck.de.angreifer.example/posts/fremd-a/</loc></url>
    <url><loc>http://franksfinanzcheck.de/posts/ohne-tls/</loc></url>
    <url><loc>https://franksfinanzcheck.de/posts/GROSS-Buchstaben/</loc></url>
  </urlset>`;
  assert.deepEqual([...artikelAusSitemap(xml)].sort(), ["2026-08-10-dsl-wechselbonus-sichern", "zweiter-artikel"]);
  assert.equal(artikelAusSitemap("").size, 0);
  assert.equal(artikelAusSitemap(undefined).size, 0);
});

test("N-05: Sitemap wird höchstens stündlich geladen", async () => {
  _artikelCacheLeeren();
  let abrufe = 0;
  const holen = async () => {
    abrufe += 1;
    return new Response("<loc>https://franksfinanzcheck.de/posts/aaa-bbb/</loc>", { status: 200 });
  };
  const t0 = Date.parse("2026-10-14T10:00:00Z");
  assert.ok((await ladeArtikel({}, t0, holen)).has("aaa-bbb"));
  await ladeArtikel({}, t0 + 59 * 60 * 1000, holen);
  assert.equal(abrufe, 1);
  await ladeArtikel({}, t0 + 61 * 60 * 1000, holen);
  assert.equal(abrufe, 2);
});

test("N-05: Ausfall – alte Liste gilt bis 24 h weiter, Abruf pausiert 5 min, danach leer", async () => {
  _artikelCacheLeeren();
  let abrufe = 0;
  const gut = async () => new Response("<loc>https://franksfinanzcheck.de/posts/aaa-bbb/</loc>");
  const kaputt = async () => {
    abrufe += 1;
    throw new Error("Netz weg");
  };
  const t0 = Date.parse("2026-10-14T10:00:00Z");
  await ladeArtikel({}, t0, gut);
  const t1 = t0 + 2 * 60 * 60 * 1000;
  assert.ok((await ladeArtikel({}, t1, kaputt)).has("aaa-bbb"), "alte Liste weiter nutzen");
  await ladeArtikel({}, t1 + 60 * 1000, kaputt);
  assert.equal(abrufe, 1, "innerhalb der Pause kein neuer Abruf");
  assert.equal((await ladeArtikel({}, t0 + 25 * 60 * 60 * 1000, kaputt)).size, 0, "nach 24 h fail closed");
  const leer = async () => new Response("<urlset></urlset>");
  _artikelCacheLeeren();
  assert.equal((await ladeArtikel({}, t0, leer)).size, 0, "leere Sitemap ersetzt keine Liste");
});

test("N-05: Mengenbegrenzung – Limit erreicht → 429, nichts gezählt", async () => {
  const db = fakeDb();
  const schluessel = [];
  const env = {
    DB: db,
    KLICK_LIMITER: { async limit({ key }) { schluessel.push(key); return { success: false }; } },
  };
  const r = await erfasse(anfrage({ k: "strom", s: "" }, { "CF-Connecting-IP": "203.0.113.7" }), env, JETZT, bekannteArtikel);
  assert.equal(r.status, 429);
  assert.equal(db.aufrufe.length, 0);
  assert.deepEqual(schluessel, ["203.0.113.7"]);
});

test("N-05: Mengenbegrenzung – unter dem Limit wird gezählt, die IP landet nie in der Datenbank", async () => {
  const db = fakeDb();
  const env = { DB: db, KLICK_LIMITER: { async limit() { return { success: true }; } } };
  const r = await erfasse(anfrage({ k: "strom", s: "2026-10-02-gasabschlag-berechnen" }, { "CF-Connecting-IP": "203.0.113.7" }), env, JETZT, bekannteArtikel);
  assert.equal(r.status, 204);
  assert.equal(db.aufrufe.length, 1);
  assert.ok(db.aufrufe.every((a) => a.werte.every((w) => w !== "203.0.113.7")));
});

test("N-05: gestörter Limiter blockiert den Zähler nicht", async () => {
  const db = fakeDb();
  const env = { DB: db, KLICK_LIMITER: { async limit() { throw new Error("gestört"); } } };
  const r = await erfasse(anfrage({ k: "strom", s: "" }), env, JETZT, bekannteArtikel);
  assert.equal(r.status, 204);
  assert.equal(db.aufrufe.length, 1);
});

test("N-05: wrangler.toml – Rate-Limit-Binding und kein workers.dev", () => {
  const toml = readFileSync(join(HIER, "..", "wrangler.toml"), "utf-8");
  assert.match(toml, /^workers_dev\s*=\s*false/m);
  assert.match(toml, /\[\[ratelimits\]\][\s\S]*name\s*=\s*"KLICK_LIMITER"/);
});

test("F-10: D1-Fehler beim Schreiben -> trotzdem 204, kein 500 im Leserbrowser", async () => {
  // Vor dem Audit lief der Schreibpfad ungefangen: Ein volles Kontingent oder
  // eine gesperrte Datenbank erzeugte einen 500er – der Leser sah eine
  // Fehlermeldung im Weiterleitungsweg, obwohl der Klick selbst funktioniert.
  const db = {
    prepare() {
      return { bind() { return { async run() { throw new Error("D1_ERROR: quota exceeded"); } }; } };
    },
  };
  const r = await erfasse(anfrage({ k: "strom", s: "2026-10-02-gasabschlag-berechnen" }), { DB: db }, JETZT, bekannteArtikel);
  assert.equal(r.status, 204);
});

test("F-10: fehlende DB-Bindung bricht den Klick nicht", async () => {
  const r = await erfasse(anfrage({ k: "strom", s: "2026-10-02-gasabschlag-berechnen" }), {}, JETZT, bekannteArtikel);
  assert.equal(r.status, 204, "ohne Binding darf der Klick nicht scheitern");
});

test("F-10: gestörter Limiter zählt weiter, bremst aber nicht falsch", async () => {
  const db = fakeDb();
  const kaputt = { limit: async () => { throw new Error("limiter down"); } };
  const r = await erfasse(anfrage({ k: "strom", s: "2026-10-02-gasabschlag-berechnen" }),
    { DB: db, KLICK_LIMITER: kaputt }, JETZT, bekannteArtikel);
  assert.equal(r.status, 204);
  assert.equal(db.aufrufe.length, 1, "gezählt wird trotzdem");
});

test("F-10: Limiter greift, wenn er arbeitet (Gegenprobe)", async () => {
  const db = fakeDb();
  const streng = { limit: async () => ({ success: false }) };
  const r = await erfasse(anfrage({ k: "strom", s: "2026-10-02-gasabschlag-berechnen" }),
    { DB: db, KLICK_LIMITER: streng }, JETZT, bekannteArtikel);
  assert.equal(r.status, 429);
  assert.equal(db.aufrufe.length, 0, "geblockt wird nichts geschrieben");
});
