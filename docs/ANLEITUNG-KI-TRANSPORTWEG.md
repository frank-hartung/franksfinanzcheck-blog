# Anleitung: KI-Transportweg

> Rollout 03.10.2026 · SSOT `data/ki_transportweg.yaml` ·
> Gate `scripts/ki_transportweg.py` · Cockpit `KI-TRANSPORTWEG-STATUS.md`
> Hintergrund und Entscheidung: `CHATGPT-GRATIS-TRANSPORTWEG-PREMIUM-2026-10-03.md`

Diese Seite beantwortet drei Fragen: **Welches Modell schreibt hier
eigentlich? Was kostet es? Und was passiert, wenn es ausfällt?**

---

## 1. Die Kurzfassung

Die Blog-Automatik ruft an mehreren Stellen ein Sprachmodell: lange
Ratgeber, News-Artikel, Faktenprüfung, Hero-Politur. Alle diese Rufe
gehen durch **einen** Transportweg (`scripts/llm_client.py`) und folgen
**einer** Routing-Tabelle (`data/ki_transportweg.yaml`).

Das Modell ist `openai/gpt-oss-120b` – **OpenAIs eigenes offenes
Modell**. Es läuft kostenlos bei drei unabhängigen Hostern:

| Hoster | Modell-ID | Gratis-Kontingent | Schlüssel |
|---|---|---|---|
| Groq Cloud | `openai/gpt-oss-120b` | 30/Min · 1.000/Tag · 200k Token/Tag | `GROQ_API_KEY` |
| NVIDIA NIM | `openai/gpt-oss-120b` | ca. 40/Min, dauerhaft, ohne Karte | `NVIDIA_API_KEY` |
| Cloudflare Workers AI | `@cf/openai/gpt-oss-120b` | 10.000 Neuronen/Tag | `CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID` |
| Google Gemini (Gegenprobe) | `gemini-3-flash-preview` | Gratis-Tier | `GEMINI_API_KEY` |

Drei Hoster, ein Modell. Fällt einer aus oder ist sein Tageskontingent
leer, rückt der nächste nach – ohne dass ein Mensch eingreift.

**Das ist die vollständige Liste.** Kostenpflichtige Anbieter existieren
im Repo nicht mehr (siehe „T1 ist eine Dauersperre"). Es gibt keinen
Schalter, kein Flag und keinen Schlüssel, mit dem versehentlich eine
Rechnung entstehen könnte.

---

## 2. Warum kein echtes ChatGPT-Konto

Die naheliegende Idee – „nimm doch einfach ChatGPT Free" – ist technisch
nicht umsetzbar. Nicht aus Sparzwang, sondern aus drei harten Gründen:

1. **ChatGPT Free hat keine Schnittstelle.** Es ist eine Chat-Oberfläche
   für Menschen. Eine Pipeline kann dort nichts abholen.
2. **Die OpenAI-API hat keinen nutzbaren Gratis-Tier.** Die automatischen
   Startguthaben wurden Mitte 2025 abgeschafft; Abrechnung erfolgt pro
   Token. Das verletzt die Kosten-Regel des Repos.
3. **Das Web-UI zu automatisieren ist verboten und zerbricht.** Es
   verstößt gegen die OpenAI-Nutzungsbedingungen und wäre exakt die
   Bauweise, die dieses Repo am 02.10.2026 mit Issue #514
   (Puter-Brücke) herausgeworfen hat: eine Automatik, die strukturell
   nie gelingen kann und trotzdem grün meldet.

Der eine offizielle Gratis-Weg zu echten GPT-Modellen – **GitHub
Models** – ist **seit dem 30.07.2026 vollständig abgeschaltet**
(Playground, Modellkatalog, Inference-API und BYOK). Er ist keine
Option mehr.

Geblieben ist der bessere Weg: nicht das Produkt ChatGPT, sondern das
Modell dahinter. `gpt-oss-120b` ist von OpenAI veröffentlicht, frei
lizenziert und bei mehreren Hostern kostenlos abrufbar – mit echter
API, eigenem Schlüssel und sauberen Nutzungsbedingungen.

---

## 3. Bedienung

```bash
npm run ki:transportweg     # Vertrag T1–T10 prüfen + Cockpit schreiben
npm run ki:status           # nur Betriebslage (wer ist erreichbar?)
npm run ki:json             # maschinenlesbar, ohne Cockpit-Schreiben
npm run ki:ping             # echte Live-Probe (verbraucht Kontingent!)
npm run ki:strict           # Standby wird rot – für die Wochenwache
npm run test:ki             # Selbsttest + Unit-Tests (offline)
```

Exit-Codes sind Vertrag:

| Exit | Bedeutung |
|---|---|
| 0 | Vertrag gehalten |
| 1 | Vertragsbruch (bzw. `--strict`: zu wenig Hoster erreichbar) |
| 2 | Das Gate selbst ist defekt (SSOT unlesbar, Selbsttest rot) |

---

## 4. Der Vertrag T1–T10

| Regel | Inhalt | Warum |
|---|---|---|
| **T1** | **Kein kostenpflichtiger Weg existiert** – nicht in SSOT, Client, Code oder CI | Dauervorgabe Frank; verschärft 03.10.2026 |
| **T2** | Nur implementierte Anbieter, Kostenklassen deckungsgleich mit `llm_client` | Zwei Wahrheiten über Geld sind eine zu viel |
| **T3** | Mindestens zwei Gratis-Glieder je Kette | Ein leeres Tageskontingent darf die Produktion nicht anhalten |
| **T4** | Mindestens ein kostenloser OpenAI-Modell-Hoster je Kette | Das ist die eingelöste Fassung von „ChatGPT einbauen" |
| **T5** | Keine Browser-Brücke, kein UI-Scraping, kein geteiltes Fremdkonto | Issue #514 |
| **T6** | Bekannte Rufer importieren `scripts/llm_client.py`; repo-weiter Scan aller Code-/Konfigurationsquellen findet direkte Modell-Endpunkte | Ein Ort für Schlüssel, Retries, Kosten; neue Rufer können die Liste nicht umgehen |
| **T7** | Jede Pflicht-Aufgabe hat eine Kette | Eine Aufgabe ohne Kette fällt still aus |
| **T8** | Runbook, Cockpit und npm-Skripte existieren | Eine Wache ohne Bedienung ist keine |
| **T9** | Jeder KI-Workflow reicht mindestens zwei passende Gratis-Schlüssel durch | Keine Aufgabe hängt an einem erschöpften Kontingent |
| **T10** | Kostenpflichtige Nebenpfade sind durch die Kostensperre verriegelt | Auch Bild-, Audio- und andere Geldflächen bleiben kostenfrei |

Der Selbsttest sabotiert das Gate **selbst**: Er schmuggelt einen
Paid-Anbieter in eine Kette, lügt eine Kostenklasse um, setzt einen
Phantom-Provider ein, kürzt eine Kette auf ein Glied, entfernt die
OpenAI-Bahn, löscht eine Pflicht-Aufgabe, unterversorgt einen Workflow
und schleust Brücken-, Paid- und direkte Modell-Endpunkt-Spuren in
Dateien ein. Die T6-Endpunkt-Probe liegt absichtlich außerhalb der
Ruferliste: Nur der repo-weite Scan kann sie finden. Bemerkt das Gate
eine dieser Sabotagen nicht, ist der Selbsttest rot. Eine Wache, die
nur verspricht, ist keine Wache.

### T6-Rollout 08.10.2026

Alle 18 vereinbarten Altdateien wurden geprüft: `compound_guard.py`,
`dash_guard.py`, `extend_articles.py`, `fix_linebreaks.py`,
`generate_drafts.py`, `groq_config.py`, `keyword_optimizer.py`,
`lektor_guard.py`, `length_guard.py`, `lesbarkeit_heiler.py`,
`meta_optimizer.py`, `poppy_lib.py`, `profi_polish.py`,
`redaktions_standard.py`, `secrets_age_guard.py`, `selftest_ki.py`,
`spellcheck.py` und `update_articles.py`. Produktive Chat-Aufrufe,
Audiotranskription und Groq-/Gemini-Modellschlüsselproben laufen nun über
den Client; `selftest_ki.py` enthält nur eine
synthetische Netzwerk-Sandbox-Fixture, keinen produktiven Modellaufruf.
Zusätzlich wurde der zuvor
dynamisch aus der Werkbank-Konfiguration gebaute Aufruf in
`antwortwerk.py` zentralisiert; Gemini-/Groq-Endpunkte stehen nicht mehr
in `data/werkbank.yaml`. Der nicht mehr betriebene Pollinations-Fallback
in `generate_drafts.py` ist entfernt.

### T1 ist eine Dauersperre, kein Hinweis

Bis zum 03.10.2026 galt: kostenpflichtige Anbieter sind erlaubt, nur
nicht automatisch. Das war zu weich – zwei nächtliche Workflows reichten
Paid-Schlüssel durch, und zwei Anbieter-Reihenfolgen begannen sogar
damit. **Ein Opt-in, das man vergessen kann, ist eine Rechnung, die man
vergisst.**

Seither sind die kostenpflichtigen Wege nicht abgeschaltet, sondern
**entfernt**: Provider, Endpunkte, Schlüssel und CLI-Flags. T1 prüft an
vier Orten, ob einer zurückkehrt – SSOT, `llm_client`, alle Skripte und
alle Workflows. Ein alter Aufruf wie `llm_client.chat("openai", …)`
liefert kein stilles `None`, sondern eine Klartext-Ansage auf stderr.

---

## 5. Schlüssel einrichten (je 0 €)

Alle drei Hoster sind kostenlos und brauchen **keine Kreditkarte**.

### Groq (bereits im Betrieb)
1. <https://console.groq.com> → API Keys → Create
2. Als Repository-Secret `GROQ_API_KEY` hinterlegen.

### NVIDIA NIM
1. <https://build.nvidia.com> mit E-Mail registrieren (keine Karte).
2. Modell `openai/gpt-oss-120b` öffnen → *Get API Key*.
   Der Schlüssel beginnt mit `nvapi-`.
3. Als Repository-Secret `NVIDIA_API_KEY` hinterlegen.

### Cloudflare Workers AI
1. <https://dash.cloudflare.com> → Workers & Pages (Free-Plan genügt).
2. Konto-ID aus der URL bzw. der Übersicht kopieren →
   Secret `CLOUDFLARE_ACCOUNT_ID`.
3. My Profile → API Tokens → Create Token → Vorlage
   **Workers AI (Read)** → Secret `CLOUDFLARE_API_TOKEN`.

Danach prüfen:

```bash
npm run ki:status     # zeigt, welche Hoster erreichbar sind
npm run ki:ping       # fragt jeden erreichbaren Hoster wirklich
```

> **Secrets setzen ist Menschenarbeit (Governance C15).** Agenten
> hinterlegen keine Schlüssel und fordern sie nicht im Chat an.

---

## 6. Betriebszustände – und was sie bedeuten

| Zustand | Anzeige | Bedeutung | Handlung |
|---|---|---|---|
| Redundant | ✅ | ≥ 2 Gratis-Hoster erreichbar | nichts |
| Dünn | ⚠️ | nur 1 Hoster erreichbar | zweiten Schlüssel nachrüsten |
| Standby | ⏸ | kein Schlüssel gesetzt | kein Fehler, aber auch kein Betrieb: die Writer erzeugen nur Offline-Gerüste |
| Vertragsbruch | ❌ | T1–T10 verletzt | nach dieser Anleitung reparieren |

**Standby ist grün, aber nicht still.** Das Cockpit sagt deutlich, dass
kein Text entsteht. Genau diese Ehrlichkeit fehlte bei Issue #514, wo
ein struktureller Dauerausfall als „übersprungen" durchlief.

---

## 7. Eine Kette ändern

1. `data/ki_transportweg.yaml` → `routing.<aufgabe>.kette` anpassen.
2. `npm run test:ki` – der Selbsttest prüft T1–T10 gegen den neuen Stand.
3. `npm run ki:transportweg` – Cockpit neu schreiben.

Wer einen **neuen Anbieter** aufnimmt, braucht drei Schritte:

1. Implementierung in `scripts/llm_client.py`
   (`ENV_KEYS`, `KOSTENKLASSE`, ggf. `OPENAI_BAHN`, Aufruf in `chat`).
2. Eintrag unter `anbieter:` in der SSOT – mit **ehrlicher**
   Kostenklasse und Quelle.
3. `npm run test:ki`. T2 vergleicht SSOT und Client; eine geschönte
   Kostenklasse fällt sofort auf.

---

## 8. Was dieses Gate **nicht** tut

- Es **veröffentlicht nichts**. Die KI-Redaktion schreibt ausschließlich
  Entwürfe; der Weg ins Live-Blog führt weiter nur über die Gates der
  Content-Engine v2.
- Es **verbraucht kein Kontingent** im Normallauf. Nur `--ping` schickt
  echte Anfragen.
- Es **ersetzt keine inhaltliche Prüfung**. Anti-Halluzination,
  Belegpflicht und YMYL-Freigabe bleiben unverändert bei den
  bestehenden Wachen.
