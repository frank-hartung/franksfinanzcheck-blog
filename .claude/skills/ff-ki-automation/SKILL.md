---
name: ff-ki-automation
description: "Benutzen für jeden Zugang nach außen und jede Automatik, die nicht der Hugo-Bau ist: Modellaufruf, LLM, API-Key/Secret, ChatGPT/Claude/Groq/Gemini/NIM, 'kann man da nicht schnell eine API nehmen', Antwortwerk/Werkbank, Recherche über Netz oder Suchmaschine, Perplexity-Ersatz, RSS/Social-Signale, Schaltwerk-Ablauf, n8n, Whisper-Sprachaufnahme, Suchradar/SERP-Erfassung, Kostensperre, 'das kostet was', neuer Dienst, Zapier. Dieser Skill enthält die Transportweg-Verträge T1–T9, die Werkbank-Verträge B1–B9, die Kostensperre und die Leitplanken aller Automationen. Nicht für die redaktionelle Bewertung der Ergebnisse (ff-produzieren) und nicht für CI-Auslieferung (ff-ausliefern)."
metadata:
  version: 1.0.0
  besitz: repo-eigen – kein Eintrag in skills-lock.json, nie von `npx skills update` anfassen
  quelltext: CLAUDE.md-Kernregeln, wörtliche Details in references/
---

# KI und Automation: ein Weg nach draußen, und er ist kostenlos

Dieser Blog betreibt **keinen** bezahlten Modellweg und **keine**
Browser-Brücke. Das ist keine Sparsamkeit, sondern ein Vertrag, der zweimal
fast gebrochen wurde (#514, #521-R16). Jeder neue Dienst, jedes Secret und jeder
Automationsschritt läuft durch diesen Skill. Alles hier ist wörtlich aus
`CLAUDE.md` übernommen.

## Wann dieser Skill zählt

- Etwas soll ein Modell, eine Suchmaschine, eine Plattform oder einen API-Endpunkt
  ansprechen.
- Ein Skript braucht Recherche, Belege oder Signale.
- Ein Ablauf soll regelmäßig laufen (Workflow, Cron, Dispatch).
- Ein Dienst, ein Plan oder ein Ticket könnte Geld kosten.
- Jemand (auch du) erwägt „nur kurz“ einen Paid-Tier, einen geteilten Zugang
  oder ein UI-Scraping.

## Die harten Kernregeln

1. **Ein Modell-Ruf, ein Zugang:** alles über `scripts/llm_client.py` und die
   Routing-Tabelle `data/ki_transportweg.yaml`. Kein Skript, kein Workflow ruft
   einen Endpunkt direkt.
2. **T1 ist eine Dauersperre:** es gibt keinen kostenpflichtigen Weg mehr.
   Provider `openai`/`claude` samt Endpunkten, Schlüsseln und `--provider`-Flags
   sind entfernt; T1/T9 prüfen das Repo und die vier KI-Workflows auf Rückkehr.
   Wer eine Paid-API will, ändert zuerst diesen Vertrag – nicht nebenbei ein
   Skript.
3. **„ChatGPT (Free)“ gibt es nicht:** keine API, kein Gratis-Tier, das Web-UI
   ist ToS-widrig, GitHub Models ist seit 30.07.2026 abgeschaltet. Die Bahn ist
   `openai/gpt-oss-120b` über drei unabhängige Gratis-Hoster (Groq → NVIDIA NIM
   → Cloudflare Workers AI), danach Gemini als Gegenprobe.
4. **Verfügbarkeit ist Teil des Vertrags:** mindestens zwei Gratis-Glieder und
   mindestens ein OpenAI-Hoster je Kette (T3/T4). Standby ist grün, aber nicht
   still.
5. **T5 verbietet die Bauweise, nicht einen Namen:** keine Browser-Brücke, kein
   UI-Scraping, kein geteiltes Fremdkonto – in Skripten **und** Workflows.
6. **Ohne Beleg kein Satz:** das Antwortwerk arbeitet ohne Schlüssel extraktiv
   (wörtliche Passagen mit `[1]`), kein Sprachmodell, keine erfundene Zahl.
   Eigene Domain und alle Partnerdomains aus `scripts/check24_links.yaml` sind
   als Quelle gesperrt (B9, nicht verhandelbar).
7. **Neue Geldfläche = Eintrag + Engstelle:** `data/kostensperre.yaml` und
   Aufruf von `kostensperre.wache(<id>)`. Ein gesetztes Secret entsichert nichts
   (T10).
8. **Ad-hoc-Recherche läuft über den Skill `agent-reach`** – lesen, nie senden;
   vor Login-/Multi-Backend-Plattformen erst `agent-reach doctor --json`.
   Facts aus Briefs erreichen den Bestand nur nach menschlicher Prüfung.
9. **Jede sendende Schaltwerk-Regel braucht `dedupe_key` und `throttle`;**
   Agent-Reach-Signale werden nie direkt gepostet, `--dry-run` schreibt nichts,
   eine gescheiterte Kette gilt nicht als erledigt.
10. **Denkspuren bleiben draußen:** `llm_client._ohne_denkspuren()` filtert
    zentral – sonst landet `TITLE:`/`DESCRIPTION:` im Frontmatter (R16).

## Katalog

| Deine Frage | Antwort im Detail |
|---|---|
| Welche Kette, welche Verbote, wie prüfe ich das? | `references/ki-transportweg.md` (T1–T9, T10, Kostensperre) |
| Wie arbeitet die Werkbank, was darf als Quelle gelten, wie recherchiere ich richtig? | `references/werkbank-recherche.md` (B1–B9, Agent Reach) |
| Wie erfasse ich Suchergebnisse ohne API und ohne CAPTCHA-Falle? | `references/suchradar.md` |
| Wie baue ich einen Automationsschritt im Schaltwerk? | `references/schaltwerk.md` |

## Kommando-Notausgang

```bash
npm run ki:status                    # welche Gratis-Hoster sind gerade erreichbar?
npm run ki:transportweg              # Vertrag T1–T9 + Cockpit
npm run test:ki                      # Gate-Selbsttest (10 Sabotage-Proben) + 28 Vertragstests
npm run werkbank                     # B1–B9-Vertrag der Antwortmaschine
npm run test:werkbank                # Antwortwerk + Werkbank-Gate (je --selftest)
npm run kosten:pruefen               # Kostensperre, fail-closed
npm run suchradar:probe              # welcher Anbieter antwortet heute? (schlüssellos)
python3 scripts/schaltwerk.py --dry-run
```

## Nicht zuständig für

- **Ob ein Artikel veröffentlichbar wird** → `ff-produzieren`
- **Welcher Workflow wann läuft und was blockieren darf** → `ff-ausliefern`
- **Wie der Nachweis für einen Umbau aussieht** → `ff-pruefen`
