# KI-Transportweg und Kostensperre

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Kostensperre: Geldflächen sind verriegelt, nicht gelöscht

**SSOT `data/kostensperre.yaml` · Wache `scripts/kostensperre.py` · Vertrag T10**

Zwei Flächen außerhalb der Textkette können Geld kosten: die
Vorlese-Stimme (ElevenLabs) und die Rechtschreibung auf ZEIT-Niveau.
Beide bleiben im Code, sind aber **fail-closed verriegelt**: Ein
gesetztes Secret allein löst nichts mehr aus. Entsichern geht nur über
einen Commit in der SSOT – mit `grund` und `datum`, sonst wirkt die
Freigabe nicht.

```bash
npm run kosten:sperre     # Bericht
npm run kosten:pruefen    # Wache (CI)
npm run test:kosten       # Selbsttest + Vertragstests
```

Regel: **Neue Geldfläche → Eintrag in `data/kostensperre.yaml` und
Aufruf von `kostensperre.wache(<id>)` an der Engstelle.** T10 wird sonst
rot. Runbook: `docs/ANLEITUNG-KOSTENSPERRE.md`.

### KI-Transportweg: ein Modell, drei Wege, 0 € (seit 03.10.2026)

Jeder Modell-Ruf des Blogs geht durch **einen** Zugang
(`scripts/llm_client.py`) und folgt **einer** Routing-Tabelle
(`data/ki_transportweg.yaml`). Gate: `scripts/ki_transportweg.py` (T1–T9,
fail-closed, Selbsttest mit zehn Sabotage-Proben).

- **„ChatGPT (Free)" ist keine Option – nicht aus Sparzwang, sondern
  weil es sie nicht gibt.** Keine API; die OpenAI-API hat keinen
  nutzbaren Gratis-Tier; das Web-UI zu automatisieren verstößt gegen die
  Nutzungsbedingungen; **GitHub Models ist seit 30.07.2026
  abgeschaltet**. Wer das „nur mal eben" nachrüstet, baut Issue #514 neu.
  Begründung: `CHATGPT-GRATIS-TRANSPORTWEG-PREMIUM-2026-10-03.md`.
- **Die OpenAI-Bahn:** `openai/gpt-oss-120b` – OpenAIs eigenes offenes
  Modell – bei **drei** unabhängigen Gratis-Hostern (Groq → NVIDIA NIM →
  Cloudflare Workers AI), danach Gemini als Gegenprobe aus einem anderen
  Modellhaus. Ein leeres Tageskontingent hält damit keine Automatik mehr an.
- **T1 ist eine Dauersperre (verschärft 03.10.2026):** Es gibt **keinen**
  kostenpflichtigen Weg mehr – die Provider `openai`/`claude` sind samt
  Endpunkten, Schlüsseln und `--provider`-Flags aus dem Repo entfernt.
  T1 prüft SSOT, Client, **alle** Skripte und **alle** Workflows auf
  Rückkehr (Schlüsselnamen *und* Endpunkte); T9 bewacht zusätzlich die
  vier KI-Workflows. Ein alter `chat("openai", …)`-Aufruf scheitert
  **laut** mit Klartext-Ansage, nicht still. Wer wieder eine Paid-API
  anschließen will, ändert zuerst diesen Vertrag – nicht nebenbei ein
  Skript.
- **T3/T4 sind Verfügbarkeitsregeln:** mindestens zwei Gratis-Glieder und
  mindestens ein OpenAI-Hoster je Kette. Eine Kette mit einem Glied ist
  ein Vertragsbruch, kein Betriebszustand.
- **T5 verbietet die Bauweise, nicht einen Namen:** keine Browser-Brücke,
  kein UI-Scraping (auch nicht von ChatGPT), kein geteiltes Fremdkonto –
  in Skripten **und** Workflows. Diese Regel hat am 03.10.2026 die
  anbieterspezifische Datei `test_keine_puter_abhaengigkeit.py` abgelöst.
- **Denkspuren-Filter:** GPT-OSS denkt laut. `llm_client._ohne_denkspuren()`
  entfernt `<think>`/`analysis…assistantfinal` zentral für alle Hoster –
  sonst landet es als R16-PROMPT-ECHO im Frontmatter (#521).
- **Standby ist grün, aber nicht still.** Kein Schlüssel = Offline-Gerüste,
  und das Cockpit sagt es laut. Genau diese Ehrlichkeit fehlte bei #514.
- **Vor jedem Umbau:** `npm run test:ki`, danach `npm run ki:transportweg`.
- Cockpit: `KI-TRANSPORTWEG-STATUS.md` · Anleitung:
  `docs/ANLEITUNG-KI-TRANSPORTWEG.md`.
