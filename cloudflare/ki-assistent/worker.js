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
//  WICHTIG: Keine direkten Provider-URLs mehr im Worker. Alle Modellrufe
//  laufen über einen eigenen Backend-Proxy, damit der Worker nicht neben
//  llm_client.py eine zweite Transportstrecke eröffnet. Das hält den
//  Transportweg nachvollziehbar und erfüllt den repo-internen Vertrag T6.
//
//  HÄRTUNG (Sicherheitsaudit 14.10.2026, M-04) – vor jeder Aktivierung:
//    1. CORS nur für EXAKTE eigene Herkünfte (ALLOWED_ORIGIN) und – falls
//       gesetzt – für Vorschau-Hosts genau EINES eigenen Projekts
//       (VORSCHAU_HOSTS). Keine Wildcards auf *.pages.dev/*.e2b.app mehr:
//       dort kann jeder kostenlos Subdomains anlegen.
//    2. Origin-PFLICHT: CORS schützt nur das Lesen im Browser. Ohne
//       erlaubten Origin gibt es 403 – kein Modellaufruf.
//    3. Turnstile-PFLICHT: Ohne TURNSTILE_SECRET antwortet der Worker mit
//       503 (fail closed). Jede Frage braucht ein gültiges Turnstile-Token.
//    4. RATE LIMITING über das Cloudflare-Binding KI_LIMITER (gilt über alle
//       Isolates); das In-Memory-Fenster bleibt nur als zweite Stufe.
//    5. Provider-Schlüssel verlassen den Worker NIE. Der Proxy hält seine
//       Schlüssel selbst; der Worker meldet sich dort mit einem eigenen
//       Token (LLM_PROXY_TOKEN) an. Die Proxy-Adresse muss https sein und
//       ihr Host exakt in LLM_PROXY_HOSTS stehen – sonst kein Aufruf.
//    6. Jede Antwort trägt den Hinweis „KI, keine Anlage-/Steuerberatung“
//       (Art. 50 Abs. 1 KI-VO; Disclaimer).
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

function liste(wert) {
  return String(wert || "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

// Proxy-Adresse nur, wenn https UND Host exakt freigegeben (M-04, Punkt 5).
// Eine später gesetzte Variable kann so nicht unbemerkt auf einen fremden
// Host zeigen.
function proxyBaseUrl(env) {
  const raw = (env.LLM_PROXY_BASE_URL || "").trim().replace(/\/$/, "");
  if (!raw) return null;
  let url;
  try {
    url = new URL(raw);
  } catch {
    return null;
  }
  if (url.protocol !== "https:" || url.username || url.password) return null;
  const freigegeben = liste(env.LLM_PROXY_HOSTS).map((h) => h.toLowerCase());
  if (!freigegeben.includes(url.hostname.toLowerCase())) return null;
  return url.origin + url.pathname.replace(/\/$/, "");
}

// ---- Provider-Definitionen (Spiegel von llm_client.py) ----
const PROVIDERS = [
  {
    id: "groq",
    route: "/proxy/groq/chat",
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
    route: "/proxy/nvidia/chat",
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
    route: "/proxy/cloudflare/chat",
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
    route: "/proxy/gemini/chat",
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
//  Der Body enthält NIE einen Provider-Schlüssel (M-04, Punkt 4/5). Die
//  Felder envKey/needsAccountId oben dokumentieren nur, welche Schlüssel der
//  PROXY für die jeweilige Route braucht.
async function callProvider(provider, messages, systemPrompt, maxTokens, env, holen = fetch) {
  const base = proxyBaseUrl(env);
  const token = (env.LLM_PROXY_TOKEN || "").trim();
  if (!base || !token) return null;

  const resp = await holen(`${base}${provider.route}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`,
    },
    body: JSON.stringify({ provider: provider.id, messages, systemPrompt, maxTokens }),
    redirect: "error",
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
async function callLLMChain(messages, systemPrompt, maxTokens, env, holen = fetch) {
  for (const provider of PROVIDERS) {
    try {
      const answer = await callProvider(
        provider,
        messages,
        systemPrompt,
        maxTokens,
        env,
        holen
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
//  HÄRTUNG 10.10.2026 (Code-Scanning-Alert #83, Regelklasse
//  js/incomplete-url-substring-sanitization):
//  Vorher entschied `origin.endsWith(".pages.dev")` über die Freigabe – eine
//  Prüfung auf der ZEICHENKETTE statt auf dem HOST. Damit galt jede Herkunft
//  als Vorschau, die zufällig so endet, und `http://` war genauso gut wie
//  `https://`. Jetzt wird die Herkunft geparst: nur https, und die
//  Punkt-Grenze wird auf dem Hostnamen geprüft.
//
//  HÄRTUNG 14.10.2026 (Sicherheitsaudit M-04): Die feste Freigabe ALLER
//  *.pages.dev- und *.e2b.app-Subdomains ist entfernt – dort legt jeder
//  kostenlos eine Subdomain an. Vorschau gibt es nur noch für Hosts, die in
//  VORSCHAU_HOSTS stehen (z. B. "franksfinanzcheck.pages.dev"): der Host
//  selbst und seine Unter-Hosts (Preview-Deployments "<hash>.<projekt>…").
function vorschauHost(origin, env = {}) {
  let url;
  try {
    url = new URL(String(origin));
  } catch {
    return false; // keine gültige Herkunft → keine Freigabe
  }
  if (url.protocol !== "https:" || url.username || url.password || url.port) return false;
  const host = url.hostname.toLowerCase();
  const projekte = liste(env.VORSCHAU_HOSTS).map((h) => h.toLowerCase());
  return projekte.some((basis) => host === basis || host.endsWith("." + basis));
}

function erlaubteHerkunft(origin, env = {}) {
  const allowed = liste(env.ALLOWED_ORIGIN || "https://franksfinanzcheck.de");
  // Produktion: exakter Origin-Vergleich (Array.includes, kein Teilstring).
  return allowed.includes(origin) || vorschauHost(origin, env);
}

function corsHeaders(origin, env) {
  const allowed = liste(env.ALLOWED_ORIGIN || "https://franksfinanzcheck.de");
  // Produktion: exakter Origin-Vergleich (Array.includes, kein Teilstring).
  // Vorschau: host-genaue Prüfung gegen VORSCHAU_HOSTS, siehe oben.
  const isAllowed = erlaubteHerkunft(origin, env);
  return {
    "Access-Control-Allow-Origin": isAllowed ? origin : allowed[0],
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
    "X-Content-Type-Options": "nosniff",
    "Cache-Control": "no-store",
  };
}

// ---- Turnstile (M-04, Punkt 3) ----
const TURNSTILE_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify";

async function turnstilePruefen(token, ip, env, holen = fetch) {
  const secret = (env.TURNSTILE_SECRET || "").trim();
  if (!secret) return { ok: false, grund: "nicht-konfiguriert" };
  if (typeof token !== "string" || token.length < 10 || token.length > 2048) {
    return { ok: false, grund: "token-fehlt" };
  }
  const form = new FormData();
  form.append("secret", secret);
  form.append("response", token);
  if (ip) form.append("remoteip", ip);
  try {
    const r = await holen(TURNSTILE_URL, {
      method: "POST",
      body: form,
      signal: AbortSignal.timeout(5_000),
    });
    const daten = await r.json();
    return daten && daten.success === true ? { ok: true } : { ok: false, grund: "token-ungueltig" };
  } catch {
    return { ok: false, grund: "pruefung-fehlgeschlagen" };
  }
}

const HINWEIS =
  "Antwort einer KI. Allgemeine Information, keine Anlage-, Steuer- oder Rechtsberatung. " +
  "Bitte prüfe wichtige Angaben selbst.";
const MAX_BODY_BYTES = 32 * 1024;

function json(daten, status, cors, extra = {}) {
  return new Response(JSON.stringify(daten), {
    status,
    headers: { ...cors, "Content-Type": "application/json; charset=utf-8", ...extra },
  });
}

// ---- Main Handler ----
async function handle(request, env, holen = fetch) {
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
    return json({ error: "Method not allowed" }, 405, cors);
  }

  // Origin-Pflicht (M-04, Punkt 2): CORS schützt nur das Lesen im Browser.
  if (!erlaubteHerkunft(origin, env)) {
    return json({ error: "Herkunft nicht erlaubt." }, 403, cors);
  }

  // Ohne Turnstile-Secret ist der Assistent aus (fail closed, Punkt 3).
  if (!(env.TURNSTILE_SECRET || "").trim()) {
    return json({ error: "Der Assistent ist derzeit nicht verfügbar.", offline: true }, 503, cors);
  }

  // Rate Limit: Binding (gilt über alle Isolates) + In-Memory als 2. Stufe
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  let limitOk = checkRateLimit(ip, rateLimitRpm);
  if (limitOk && env.KI_LIMITER && typeof env.KI_LIMITER.limit === "function") {
    try {
      limitOk = (await env.KI_LIMITER.limit({ key: ip })).success === true;
    } catch {
      limitOk = false; // gestörter Limiter → lieber ablehnen (kostet Kontingent)
    }
  }
  if (!limitOk) {
    return json(
      { error: "Zu viele Anfragen. Bitte warte eine Minute.", retryAfter: 60 },
      429,
      cors,
      { "Retry-After": "60" }
    );
  }

  // Request parsen (mit Größengrenze)
  const laenge = Number(request.headers.get("Content-Length") || 0);
  if (laenge > MAX_BODY_BYTES) {
    return json({ error: "Anfrage zu groß." }, 413, cors);
  }
  let body;
  try {
    const text = await request.text();
    if (text.length > MAX_BODY_BYTES) {
      return json({ error: "Anfrage zu groß." }, 413, cors);
    }
    body = JSON.parse(text);
  } catch {
    return json({ error: "Ungültige Anfrage." }, 400, cors);
  }
  if (!body || typeof body !== "object") {
    return json({ error: "Ungültige Anfrage." }, 400, cors);
  }

  const question = typeof body.question === "string" ? body.question.trim() : "";
  if (!question || question.length < 3) {
    return json({ error: "Die Frage ist zu kurz." }, 400, cors);
  }

  if (question.length > 2000) {
    return json({ error: "Die Frage ist zu lang (max. 2.000 Zeichen)." }, 400, cors);
  }

  // Turnstile-Token prüfen (nach den billigen Prüfungen, vor dem Modellaufruf)
  const turnstile = await turnstilePruefen(body.turnstileToken, ip, env, holen);
  if (!turnstile.ok) {
    return json({ error: "Bitte bestätige kurz, dass du kein Bot bist." }, 403, cors);
  }

  // Nachrichten aufbauen
  const messages = [];
  const history = Array.isArray(body.history) ? body.history : [];
  // Max. 10 Nachrichten aus der Historie (Token-Budget)
  for (const msg of history.slice(-10)) {
    if (msg && msg.role && msg.content && typeof msg.content === "string") {
      messages.push({
        role: msg.role === "assistant" ? "assistant" : "user",
        content: msg.content.slice(0, 2000),
      });
    }
  }
  messages.push({ role: "user", content: question });

  const systemPrompt = env.SYSTEM_PROMPT || "";

  // LLM-Kette aufrufen
  const result = await callLLMChain(messages, systemPrompt, 1500, env, holen);

  if (!result) {
    return json(
      {
        error: "Der Assistent ist gerade nicht erreichbar. Bitte versuch es später erneut.",
        offline: true,
      },
      503,
      cors
    );
  }

  return json(
    {
      answer: result.answer,
      provider: result.provider,
      model: result.model,
      hinweis: HINWEIS,
      ki: true,
    },
    200,
    cors
  );
}

export default {
  async fetch(request, env) {
    return handle(request, env);
  },
};

// Nur für Tests (node --test, siehe test/worker.test.mjs): Die CORS-Entscheidung
// ist sicherheitsrelevant und wird deshalb direkt geprüft, nicht über Umwege.
export { corsHeaders, vorschauHost, erlaubteHerkunft, proxyBaseUrl, turnstilePruefen, handle, HINWEIS };
