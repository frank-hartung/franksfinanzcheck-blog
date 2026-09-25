#!/usr/bin/env node
// ============================================================
//  PUTER-CHAT-BRÜCKE – Claude kostenlos, OHNE API (Claude-Stilpolitur)
//  ------------------------------------------------------------
//  AUFTRAG (Frank, 25.09.2026): „Claude sollte nur ohne API genutzt
//  werden. Dafür sollte das aktuell beste kostenlose Claude-Modell
//  gewählt werden."
//
//  ZUGANG: Puter.js „Free, Unlimited Claude API" (User-Pays-Modell):
//    · KEINE Anthropic-API, KEIN ANTHROPIC_API_KEY, keine Kosten
//    · Auth nur über PUTER_AUTH_TOKEN (kostenloser Puter-Account,
//      monatliches Gratis-Kontingent – siehe docs.puter.com)
//    · Node-fähig & CI-fähig (GitHub Actions dokumentiert)
//
//  MODELL (Nachtrag Frank, 25.09.2026): AUSCHLIESSLICH
//  claude-sonnet-5 – „nur das Claude-Modell claude-sonnet-5".
//  Kein Fallback, kein anderes Modell (der Aufrufer pinnt das
//  ebenfalls; Selbsttest ST3 in claude_stilpolitur.py).
//
//  PROTOKOLL (Aufruf aus scripts/claude_stilpolitur.py):
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

const req = JSON.parse(readFileSync(0, "utf8"));
if (!req || !req.user) {
  console.error("puter_chat: Request braucht mindestens { user }");
  process.exit(1);
}

const puter = init(process.env.PUTER_AUTH_TOKEN);
const messages = [];
if (req.system) messages.push({ role: "system", content: String(req.system) });
messages.push({ role: "user", content: String(req.user) });

const options = { model: req.model || "claude-sonnet-5", stream: true };
if (typeof req.temperature === "number") options.temperature = req.temperature;
if (typeof req.max_tokens === "number") options.max_tokens = req.max_tokens;

function partsToText(content) {
  if (content == null) return "";
  if (Array.isArray(content)) {
    return content.map((p) => (p && typeof p.text === "string" ? p.text : "")).join("");
  }
  if (typeof content === "string") return content;
  if (typeof content.text === "string") return content.text;
  return content.toString ? content.toString() : String(content);
}

let text = "";
try {
  // Streaming: dokumentiert für „longer queries" – volle Länge ohne
  // Zwischen-Puffer-Caps (Artikel-Rewrites sind 5–6k Token).
  const resp = await puter.ai.chat(messages, false, options);
  if (resp && typeof resp[Symbol.asyncIterator] === "function") {
    for await (const part of resp) {
      if (!part) continue;
      if (typeof part.text === "string") text += part.text;
      else if (part.type === "text" && typeof part.text === "string") text += part.text;
    }
  } else {
    text = partsToText(resp && resp.message ? resp.message.content : resp);
  }
} catch (err) {
  // Optionen wie temperature/max_tokens sind nicht überall belegt –
  // ein Rerun mit dem Kern-Set ist billiger als ein verlorener Lauf.
  try {
    const resp = await puter.ai.chat(messages, false,
      { model: options.model, stream: true });
    if (resp && typeof resp[Symbol.asyncIterator] === "function") {
      for await (const part of resp) {
        if (part && typeof part.text === "string") text += part.text;
      }
    } else {
      text = partsToText(resp && resp.message ? resp.message.content : resp);
    }
  } catch (err2) {
    console.error(`puter_chat [${options.model}]: ${err2 && err2.message ? err2.message : err2}`);
    process.exit(1);
  }
}

text = (text || "").trim();
if (!text) {
  console.error(`puter_chat [${options.model}]: leere Antwort`);
  process.exit(1);
}
process.stdout.write(text);
