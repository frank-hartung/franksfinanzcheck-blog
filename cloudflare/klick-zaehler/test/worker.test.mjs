// Vertragstests für den Klick-Zähler (ohne Netz, ohne Cloudflare).
// Ausführen: cd cloudflare/klick-zaehler && npm test
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import worker, { erfasse, pruefeEreignis, berlinDatum, MAX_BYTES } from "../worker.js";
import { GATEWAY_KEYS } from "../gateway-keys.mjs";

const HIER = dirname(fileURLToPath(import.meta.url));

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
  const r = await erfasse(anfrage({ k: "strom", s: "2026-10-02-gasabschlag-berechnen" }), { DB: db }, JETZT);
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
