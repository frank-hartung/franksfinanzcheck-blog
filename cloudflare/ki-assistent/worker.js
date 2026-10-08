// ============================================================
//  KI-ASSISTENT – Cloudflare Worker
//  ------------------------------------------------------------
//  Sichere API-Brücke zum kostenlosen LLM-Zugang.
//  Schlüssel leben NUR hier, das Frontend sieht nie einen Key.
//
//  ARCHITEKTUR
//    POST /chat  →  { question, history? }
//                 →  LLM-Kette (Groq → NVIDIA → CF Workers AI → Gemini)
//                 →  { answer, provider?, model? }
//
//  RATE LIMITING: In-Memory pro IP (15 Req/Min Default).
//  CORS: Nur franksfinanzcheck.de + pages.dev-Preview.
//  KOSTEN: 0 € – nur Gratis-Tiers.
// ============================================================

// ---- Rate Limiter (in-memory, pro IP, gleitendes Fenster) ----
const buckets = new Map();

function checkRateLimit(ip, rpm) {
  const now = Date.now();
  const windowMs = 60_000;
  let bucket = buckets.get(ip);
  if (!bucket) {
    bucket = { timestamps: [] };
    buckets.set(ip, bucket);
  }
  // Alte Einträge entfernen
  bucket.timestamps = bucket.timestamps.filter(t => now - t < windowMs);
  if (bucket.timestamps.length >= rpm) {
    return false; // Limit erreicht
  }
  bucket.timestamps.push(now);
  return true;
}

// Periodisch aufräumen (alle 5 Minuten)
let lastCleanup = 0;
function cleanupBuckets() {
  const now = Date.now();
  if (now - lastCleanup < 300_000) return;
  lastCleanup = now;
  for (const [ip, bucket] of buckets) {
    bucket.timestamps = bucket.timestamps.filter(t => now - t < 60_000);
    if (bucket.timestamps.length === 0) buckets.delete(ip);
  }
}

// ---- Provider-Definitionen (Spiegel von llm_client.py) ----
const PROVIDERS = [
  {
    id: "groq",
    url: "https://api.groq.com/openai/v1/chat/completions",
    model: "openai/gpt-oss-120b",
    headers: (key) => ({
      "Content-Type": "application/json",
      "Authorization": `Bearer ${key}`,
    }),
    body: (msgs, sys, maxTokens) => ({
      model: "openai/gpt-oss-120b",
      messages: sys ? [{ role: "system", content: sys }, ...msgs] : msgs,
      temperature: 0.4,
      max_tokens: maxTokens,
    }),
    extract: (data) => {
      const content = data?.choices?.[0]?.message?.content;
      return content ? stripThinking(content.trim()) : null;
    },
    envKey: "GROQ_API_KEY",
  },
  {
    id: "nvidia",
    url: "https://integrate.api.nvidia.com/v1/chat/completions",
    model: "openai/gpt-oss-120b",
    headers: (key) => ({
      "Content-Type": "application/json",
      "Authorization": `Bearer ${key}`,
    }),
    body: (msgs, sys, maxTokens) => ({
      model: "openai/gpt-oss-120b",
      messages: sys ? [{ role: "system", content: sys }, ...msgs] : msgs,
      temperature: 0.4,
      max_tokens: maxTokens,
    }),
    extract: (data) => {
      const content = data?.choices?.[0]?.message?.content;
      return content ? stripThinking(content.trim()) : null;
    },
    envKey: "NVIDIA_API_KEY",
  },
  {
    id: "cloudflare",
    // URL wird dynamisch gebaut (braucht Account-ID)
    url: null,
    model: "@cf/openai/gpt-oss-120b",
    headers: (key) => ({
      "Content-Type": "application/json",
      "Authorization": `Bearer ${key}`,
    }),
    body: (msgs, sys, maxTokens) => ({
      model: "@cf/openai/gpt-oss-120b",
      messages: sys ? [{ role: "system", content: sys }, ...msgs] : msgs,
      temperature: 0.4,
      max_tokens: maxTokens,
    }),
    extract: (data) => {
      const content = data?.choices?.[0]?.message?.content;
      return content ? stripThinking(content.trim()) : null;
    },
    envKey: "CLOUDFLARE_API_TOKEN",
    needsAccountId: true,
  },
  {
    id: "gemini",
    // Gemini-Format ist anders (nicht OpenAI-kompatibel)
    url: null, // dynamisch
    model: "gemini-3-flash-preview",
    envKey: "GEMINI_API_KEY",
    isGemini: true,
  },
];

// GPT-OSS Denkspuren entfernen (wie llm_client.py)
function stripThinking(text) {
  text = text.replace(/<think>[\s\S]*?<\/think>/gi, "");
  text = text.replace(/<reasoning>[\s\S]*?<\/reasoning>/gi, "");
  text = text.replace(/^\s*analysis\b[\s\S]*?assistantfinal\s*/im, "");
  text = text.replace(
    /^\s*<\|channel\|>analysis<\|message\|>[\s\S]*?<\|channel\|>final<\|message\|>/im,
    ""
  );
  return text.trim();
}

// ---- LLM-Call: einen Provider versuchen ----
async function callProvider(provider, messages, systemPrompt, maxTokens, env) {
  const key = env[provider.envKey];
  if (!key) return null;

  let url, headers, body;

  if (provider.isGemini) {
    // Gemini-Format
    url = `https://generativelanguage.googleapis.com/v1beta/models/${provider.model}:generateContent?key=${key}`;
    headers = { "Content-Type": "application/json" };
    const contents = messages.map((m) => ({
      role: m.role === "assistant" ? "model" : "user",
      parts: [{ text: m.content || "" }],
    }));
    body = JSON.stringify({
      contents,
      systemInstruction: systemPrompt
        ? { parts: [{ text: systemPrompt }] }
        : undefined,
      generationConfig: { temperature: 0.4, maxOutputTokens: maxTokens },
    });
  } else if (provider.needsAccountId) {
    const accountId = env.CLOUDFLARE_ACCOUNT_ID;
    if (!accountId) return null;
    url = `https://api.cloudflare.com/client/v4/accounts/${accountId}/ai/v1/chat/completions`;
    headers = provider.headers(key);
    body = JSON.stringify(provider.body(messages, systemPrompt, maxTokens));
  } else {
    url = provider.url;
    headers = provider.headers(key);
    body = JSON.stringify(provider.body(messages, systemPrompt, maxTokens));
  }

  const resp = await fetch(url, {
    method: "POST",
    headers,
    body,
    signal: AbortSignal.timeout(30_000),
  });

  if (!resp.ok) return null;

  const data = await resp.json();

  if (provider.isGemini) {
    const parts = data?.candidates?.[0]?.content?.parts;
    if (!parts) return null;
    const text = parts.map((p) => p.text || "").join("").trim();
    return text || null;
  }

  return provider.extract(data);
}

// ---- Failover-Kette (wie data/ki_transportweg.yaml: lang) ----
async function callLLMChain(messages, systemPrompt, maxTokens, env) {
  for (const provider of PROVIDERS) {
    try {
      const answer = await callProvider(
        provider,
        messages,
        systemPrompt,
        maxTokens,
        env
      );
      if (answer) return { answer, provider: provider.id, model: provider.model };
    } catch {
      // Nächster Provider
      continue;
    }
  }
  return null;
}

// ---- CORS ----
function corsHeaders(origin, env) {
  const allowed = (env.ALLOWED_ORIGIN || "https://franksfinanzcheck.de").split(",").map(s => s.trim());
  // pages.dev-Preview erlauben
  const isAllowed = allowed.includes(origin) || 
    (origin && origin.endsWith(".pages.dev")) ||
    (origin && origin.endsWith(".e2b.app")); // Arena-Preview
  return {
    "Access-Control-Allow-Origin": isAllowed ? origin : allowed[0],
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

// ---- Main Handler ----
export default {
  async fetch(request, env) {
    cleanupBuckets();

    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(origin, env);
    const rateLimitRpm = parseInt(env.RATE_LIMIT_RPM || "15", 10);

    // Preflight
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    // Nur POST
    if (request.method !== "POST") {
      return new Response(
        JSON.stringify({ error: "Method not allowed" }),
        { status: 405, headers: { ...cors, "Content-Type": "application/json" } }
      );
    }

    // Rate Limit
    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    if (!checkRateLimit(ip, rateLimitRpm)) {
      return new Response(
        JSON.stringify({
          error: "Zu viele Anfragen. Bitte warte eine Minute.",
          retryAfter: 60,
        }),
        { status: 429, headers: { ...cors, "Content-Type": "application/json", "Retry-After": "60" } }
      );
    }

    // Request parsen
    let body;
    try {
      body = await request.json();
    } catch {
      return new Response(
        JSON.stringify({ error: "Ungültige Anfrage." }),
        { status: 400, headers: { ...cors, "Content-Type": "application/json" } }
      );
    }

    const question = (body.question || "").trim();
    if (!question || question.length < 3) {
      return new Response(
        JSON.stringify({ error: "Die Frage ist zu kurz." }),
        { status: 400, headers: { ...cors, "Content-Type": "application/json" } }
      );
    }

    if (question.length > 2000) {
      return new Response(
        JSON.stringify({ error: "Die Frage ist zu lang (max. 2.000 Zeichen)." }),
        { status: 400, headers: { ...cors, "Content-Type": "application/json" } }
      );
    }

    // Nachrichten aufbauen
    const messages = [];
    const history = Array.isArray(body.history) ? body.history : [];
    // Max. 10 Nachrichten aus der Historie (Token-Budget)
    for (const msg of history.slice(-10)) {
      if (msg.role && msg.content && typeof msg.content === "string") {
        messages.push({
          role: msg.role === "assistant" ? "assistant" : "user",
          content: msg.content.slice(0, 2000),
        });
      }
    }
    messages.push({ role: "user", content: question });

    const systemPrompt = env.SYSTEM_PROMPT || "";

    // LLM-Kette aufrufen
    const result = await callLLMChain(messages, systemPrompt, 1500, env);

    if (!result) {
      return new Response(
        JSON.stringify({
          error: "Der Assistent ist gerade nicht erreichbar. Bitte versuch es später erneut.",
          offline: true,
        }),
        { status: 503, headers: { ...cors, "Content-Type": "application/json" } }
      );
    }

    return new Response(
      JSON.stringify({
        answer: result.answer,
        provider: result.provider,
        model: result.model,
      }),
      {
        status: 200,
        headers: {
          ...cors,
          "Content-Type": "application/json",
          "Cache-Control": "no-store",
        },
      }
    );
  },
};