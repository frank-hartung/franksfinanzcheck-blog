#!/usr/bin/env node
// ============================================================
//  PUTER-CHAT-BRÜCKE – optionaler Gratis-Zugang für Fach- und Hero-Checks
//  ------------------------------------------------------------
//  Diese Brücke wird nur von den ausdrücklich dafür vorgesehenen
//  Recherche-/Startseiten-Workflows genutzt. Die Hemingway-Lesbarkeitsprüfung
//  läuft davon unabhängig vollständig offline.
//
//  ZUGANG: Puter.js „Free, Unlimited Claude API" (User-Pays-Modell):
//    · KEINE Anthropic-API, KEIN ANTHROPIC_API_KEY, keine Kosten
//    · Auth nur über PUTER_AUTH_TOKEN (kostenloser Puter-Account,
//      monatliches Gratis-Kontingent – siehe docs.puter.com)
//    · Node-fähig & CI-fähig (GitHub Actions dokumentiert)
//
//  MODELL (Nachtrag Frank, 25.09.2026): AUSCHLIESSLICH
//  claude-sonnet-5 – „nur das Claude-Modell claude-sonnet-5".
//  Kein Fallback, kein anderes Modell (die jeweiligen Aufrufer pinnen das
//  jeweils selbst).
//
//  PROTOKOLL (Aufruf aus den Recherche-/Startseiten-Skripten):
//    stdin  = JSON: { "system": "…", "user": "…", "model": "…",
//                     "temperature": 0.5, "max_tokens": 8192 }
//    stdout = reiner Antworttext (kein JSON, kein Prompt-Echo)
//    stderr = Fehlermeldung · Exit 0 = ok, Exit 1 = Fehler/leer
//
//  Abhängigkeit (in Workflows transient installiert):
//    npm install --no-save @heyputer/puter.js   (Node.js 24+)
// ============================================================
import { readFileSync } from "node:fs";
import { init } from "@heyputer/puter.js/src/init.cjs";

const MODEL = "claude-sonnet-5";

let req;
try {
  req = JSON.parse(readFileSync(0, "utf8"));
} catch (err) {
  console.error(`puter_chat: ungültiges JSON (${err?.message || err})`);
  process.exit(1);
}
if (!req || !req.user) {
  console.error("puter_chat: Request braucht mindestens { user }");
  process.exit(1);
}
if (String(req.model || MODEL) !== MODEL) {
  console.error(`puter_chat: Modell-Mandat verletzt (erlaubt ist ausschließlich ${MODEL})`);
  process.exit(1);
}
if (!(process.env.PUTER_AUTH_TOKEN || "").trim()) {
  console.error("puter_chat: PUTER_AUTH_TOKEN fehlt (kein API- oder Modell-Fallback erlaubt)");
  process.exit(1);
}

let puter;
try {
  puter = init(process.env.PUTER_AUTH_TOKEN);
} catch (err) {
  console.error(`puter_chat [${MODEL}]: Puter.js konnte nicht initialisiert werden: ${err?.message || err}`);
  process.exit(1);
}
const messages = [];
if (req.system) messages.push({ role: "system", content: String(req.system) });
messages.push({ role: "user", content: String(req.user) });

const options = { model: MODEL, stream: true };
if (typeof req.temperature === "number") options.temperature = req.temperature;
if (typeof req.max_tokens === "number") options.max_tokens = req.max_tokens;

// Puter kann je nach SDK-/Gateway-Version native Anthropic-Blöcke,
// OpenAI-kompatible Delta-Blöcke oder einfache Text-Chunks liefern. Ein
// einziger normalisierter Parser verhindert, dass ein gültiger Rewrite als
// „leer“ verworfen wird, ohne jemals Inhalte aus einem Objekt zu String zu
// serialisieren.
function partsToText(content) {
  if (content == null) return "";
  if (typeof content === "string") return content;
  if (Array.isArray(content)) return content.map(partsToText).join("");
  if (typeof content !== "object") return "";
  if (typeof content.text === "string") return content.text;
  if (typeof content.content === "string" || Array.isArray(content.content)) {
    return partsToText(content.content);
  }
  if (content.delta) return partsToText(content.delta);
  if (content.message) return partsToText(content.message);
  if (Array.isArray(content.choices)) return content.choices.map(partsToText).join("");
  if (content.choice) return partsToText(content.choice);
  return "";
}

async function responseToText(resp) {
  if (!resp) return "";
  if (typeof resp[Symbol.asyncIterator] === "function") {
    let streamed = "";
    for await (const part of resp) streamed += partsToText(part);
    return streamed;
  }
  return partsToText(resp);
}

async function request(requestOptions) {
  // Streaming: dokumentiert für längere Anfragen – volle Artikel ohne
  // Zwischen-Puffer-Caps (Rewrites sind 5–6k Token).
  return responseToText(await puter.ai.chat(messages, false, requestOptions));
}

let text = "";
let firstError;
try {
  text = await request(options);
} catch (err) {
  firstError = err;
  // Optionen wie temperature/max_tokens sind nicht bei jedem Puter-Gateway
  // belegt. Ein zweiter Versuch nutzt weiterhin exakt dasselbe Modell und
  // entfernt nur optionale Parameter – niemals ein Ersatzmodell.
  try {
    text = await request({ model: MODEL, stream: true });
  } catch (err2) {
    const detail = err2?.message || firstError?.message || err2 || firstError;
    console.error(`puter_chat [${MODEL}]: ${detail}`);
    process.exit(1);
  }
}

text = (text || "").trim();
if (!text) {
  console.error(`puter_chat [${MODEL}]: leere Antwort`);
  process.exit(1);
}
process.stdout.write(text);
