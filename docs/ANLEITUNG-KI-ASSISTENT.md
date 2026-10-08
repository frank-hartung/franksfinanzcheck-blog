# Anleitung: KI-Assistent

> Rollout 08.10.2026 · Gate `scripts/ki_assistent_gate.py` ·
> SSOT `data/ki_transportweg.yaml` · Cockpit `COCKPIT.md`

Diese Seite erklärt, wie der **benutzerfrontende KI-Assistent** von
FranksFinanzcheck funktioniert – das Chat-Widget, das Blog-Besucher direkt
auf jeder Seite nutzen können.

---

## 1. Was es ist

Ein Chat-Widget (Floating Button unten rechts), mit dem Besucher Fragen zu
Fixkosten, Versicherungen, Strom, Gas, DSL und Sparen stellen können. Der
Assistent antwortet kostenlos, ohne Anmeldung und ohne Tracking.

**Technisch:** Das Frontend (Hugo-Partial + JS + CSS) sendet Fragen an einen
Cloudflare Worker, der die Anfrage sicher an die kostenlosen LLM-Provider
weiterleitet (Groq → NVIDIA → Cloudflare Workers AI → Gemini). Alle
API-Schlüssel leben NUR im Worker – das Frontend sieht nie einen Key.

---

## 2. Architektur

```
Browser                   Cloudflare Worker              LLM-Provider
┌──────────┐  POST /chat  ┌──────────────┐  API-Call    ┌──────────────┐
│ Chat-UI  │──────────────│ ki-assistent  │─────────────│ Groq         │
│ (Hugo)   │  {question,  │ (Worker.js)  │  Failover   │ NVIDIA       │
│          │   history}   │              │  ↓           │ Cloudflare   │
│          │◄─────────────│ Rate-Limit   │─────────────│ Gemini       │
└──────────┘  {answer}    │ CORS         │              └──────────────┘
                          │ Key-Mgmt     │
                          └──────────────┘
```

**Warum ein Worker?** Die API-Schlüssel dürfen nie im Browser sichtbar sein.
Der Worker hält sie als Secrets und setzt CORS so, dass nur
franksfinanzcheck.de (+ pages.dev-Preview) den Aufruf darf.

---

## 3. Dateien

| Datei | Zweck |
|---|---|
| `cloudflare/ki-assistent/worker.js` | Serverless Proxy (API-Keys, Rate-Limit, CORS) |
| `cloudflare/ki-assistent/wrangler.toml` | Deploy-Konfiguration |
| `cloudflare/ki-assistent/package.json` | Dependencies |
| `layouts/_partials/ki_assistent.html` | Globaler Partial (auf jeder Seite) |
| `layouts/shortcodes/ki_assistent.html` | Shortcode (einzeln einbettbar) |
| `assets/css/extended/ki-assistent.css` | Styling (Dark Mode, A11y, responsive) |
| `static/premium/ki-assistent.js` | Client-Logik (Chat, Formatierung, A11y) |
| `scripts/ki_assistent_gate.py` | Gate (KA1–KA9, Selftest) |
| `docs/ANLEITUNG-KI-ASSISTENT.md` | Diese Datei |

---

## 4. Deployment

### 4.1 Worker deployen

```bash
cd cloudflare/ki-assistent
npm install
npx wrangler deploy
```

### 4.2 API-Schlüssel setzen

```bash
npx wrangler secret put GROQ_API_KEY
npx wrangler secret put NVIDIA_API_KEY
npx wrangler secret put CLOUDFLARE_API_TOKEN
npx wrangler secret put CLOUDFLARE_ACCOUNT_ID
npx wrangler secret put GEMINI_API_KEY
```

Alle Schlüssel sind **kostenlos** und brauchen **keine Kreditkarte**.
Details: [ANLEITUNG-KI-TRANSPORTWEG.md](ANLEITUNG-KI-TRANSPORTWEG.md)

### 4.3 Endpoint konfigurieren

In `hugo.toml`:

```toml
[params]
  kiAssistentEndpoint = "https://ki-assistent.DEIN-NAME.workers.dev/chat"
```

Oder pro Shortcode:

```html
{{</* ki-assistent endpoint="https://ki-assistent.DEIN-NAME.workers.dev/chat" */>}}
```

**Verhalten ohne Endpoint:** Solange kein Endpoint gesetzt ist, rendert die
globale Partial (`layouts/_partials/ki_assistent.html`) das Widget nicht – der
Leser sieht keinen Knopf, der ins Leere läuft. Sobald der Endpoint in
`hugo.toml` steht, erscheint das Widget auf allen Seiten ohne weitere Änderung.

**Zeitlimit:** Der Client bricht eine Anfrage nach 130 s ab (Konstante
`ANTWORT_ZEITLIMIT_MS` in `static/premium/ki-assistent.js`). Der Worker
probiert bis zu vier Provider nacheinander mit je 30 s Timeout – 130 s
decken diese Worst-Case-Kette ab. Wer die Provider-Liste ändert, zieht das
Limit mit.

### 4.4 Verifizieren

```bash
python3 scripts/ki_assistent_gate.py
python3 scripts/ki_assistent_gate.py --selftest
python3 scripts/ki_assistent_gate.py --strict
```

---

## 5. Integration

### Auf jeder Seite (automatisch)

Der Partial `ki_assistent.html` ist in `baseof.html` eingebunden. Er zeigt
das Widget auf allen Seiten, außer wenn im Frontmatter steht:

```yaml
hideAssistent: true
```

### Auf einzelnen Seiten (Shortcode)

```markdown
{{</* ki-assistent */>}}

{{</* ki-assistent endpoint="https://..." */>}}

{{</* ki-assistent */>}}
  Meine custom Frage 1
  Meine custom Frage 2
{{</* /ki-assistent */>}}
```

---

## 6. DSGVO / Datenschutz

| Aspekt | Entscheidung |
|---|---|
| Cookies | Keine. |
| Tracking | Keins. Kein Google Analytics, kein Sentry, kein Hotjar. |
| Session-Speicher | Nur im Arbeitsspeicher (RAM). Seite schließen = Daten weg. |
| Externe Requests | Erst wenn der Nutzer eine Frage stellt. |
| API-Schlüssel | Leben nur im Cloudflare Worker (Secrets). |
| Logdaten | Cloudflare Workers Logs (Standard), keine personenbezogenen Daten außer IP. |
| Einwilligung | Nicht nötig: keine personenbezogenen Daten werden dauerhaft gespeichert. |

**Hinweis:** Der Datenschutz-Link im Widget-Footer verweist auf die
Datenschutzerklärung des Blogs.

---

## 7. Gate-Regeln (KA1–KA9)

| Regel | Inhalt |
|---|---|
| KA1 | Endpoint konfiguriert (hugo.toml oder Shortcode) |
| KA2 | CSS-Datei vorhanden und nicht leer |
| KA3 | JS-Datei vorhanden und nicht leer |
| KA4 | Shortcode existiert |
| KA5 | Globaler Partial existiert |
| KA6 | DSGVO-Hinweis (Datenschutz-Link) im Widget |
| KA7 | Keine hardcoded API-Schlüssel im Frontend |
| KA8 | Keine Tracking-Pixel oder externen Requests vor Nutzeraktion |
| KA9 | Worker-Code vorhanden und konsistent |

---

## 8. Rate Limiting

| Ebene | Limit | Mechanismus |
|---|---|---|
| Cloudflare Worker | 15 Req/Minute pro IP | In-Memory Bucket (konfigurierbar) |
| Browser | Kein Senden während läuft | `isSending`-Flag |
| Maximale Fragenlänge | 2.000 Zeichen | Client + Worker |

---

## 9. Barrierefreiheit (A11y)

- Trigger-Button: `aria-label`, `aria-expanded`, `aria-controls`
- Panel: `role="dialog"`, `aria-hidden`, Fokus-Trap
- Nachrichten: `role="log"`, `aria-live="polite"`
- Eingabefeld: `<label>`, `maxlength`, `placeholder`
- Senden: `aria-label`, disabled-Zustand
- Schließen: Escape-Taste, Click-außerhalb
- Dark Mode: `prefers-color-scheme` + `data-theme="dark"`
- Reduced Motion: `prefers-reduced-motion` deaktiviert Animationen
- Tap-Ziele: ≥ 44px (Button-Größen)
- Fokusring: Sichtbar auf allen interaktiven Elementen