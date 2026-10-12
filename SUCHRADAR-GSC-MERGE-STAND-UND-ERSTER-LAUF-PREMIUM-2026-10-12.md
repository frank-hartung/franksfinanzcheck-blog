# Suchradar und GSC-Import: Übergabestand, Verifikation und der ausstehende erste Lauf

**Datum:** 12.10.2026 · **Auftrag:** Frank – „Der Branch `arena/1524b7b2-franksfinanzcheck-blog` hat
vier ungepushte Commits (Suchradar + GSC-Import). Bitte main hereinholen, alles verifizieren und
einen PR daraus machen. Danach die Vorlage `docs/workflow-vorlagen/gsc-import.yml` nach
`.github/workflows/` verschieben und den ersten Lauf beobachten."

**Ergebnis:** Beim Nachsehen war der Auftrag bereits erledigt. Beide Ketten liegen seit dem
12.10.2026 auf `main` (#709 Suchradar, #711 Search Console), die Vorlage ist im selben Merge-Commit
gewandert, und beide Workflows sind in Actions scharf. Es gab nichts zu pushen, keinen PR zu öffnen
und nichts zu verschieben. Neu ist dieser Befund – plus eine Entscheidung, die bewusst **nicht**
getroffen wurde: der erste Lauf wurde nicht von Hand ausgelöst (Abschnitt 5).

---

## 1. Wie geprüft wurde

Kein Befund aus dem Gedächtnis, jeder Satz unten ist nachvollzogen:

| Frage | Werkzeug |
|---|---|
| Existiert der Branch noch? | `git ls-remote origin`, GitHub-API `branches/arena%2F1524b7b2-…` |
| Was war auf welchem Branch? | `gh pr view 709/711 --json commits,mergedAt,mergeCommit` |
| Wann ist die Vorlage gewandert? | Commit-Historie beider Pfade (`commits?path=…`) |
| Läuft der Code? | `npm run test:suchradar`, `npm run test:gsc` auf dem gemergten Stand |
| Sind die Workflows scharf? | `gh workflow list`, `gh api …/actions/workflows/<id>`, `gh run list` |
| Ist das Dienstkonto eingerichtet? | API-Versuch `actions/secrets` + `actions/variables`, dazu alle repo-seitigen Spuren |

Arbeitskopie: `6e984d6` (Klon-Basis), `origin/main` zum Prüfzeitpunkt `f15d367`, 19:43 UTC.

## 2. Befund A – es lag nichts Ungepushtes herum

| Kette | Branch | PR | Commits | Gemerged | Merge-Commit |
|---|---|---|---|---|---|
| Suchradar | `arena/1524b7b2-…` | [#709](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/709) | 3 | 12.10., 11:06 UTC | `0d58ec0` |
| Search Console / GSC-Import | `arena/11d70b63-…` | [#711](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/711) | 4 | 12.10., 13:45 UTC | `4bffca7` |
| Nachlauf IndexNow-Probelauf | `arena/11d70b63-…` | [#715](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/715) | 1 | 12.10., 16:24 UTC | `be0a3df` |

Drei Klarstellungen zum Auftrag:

1. **Der Branch existiert nicht mehr.** `arena/1524b7b2-franksfinanzcheck-blog` antwortet mit
   `404 Branch not found` – nach dem Merge gelöscht. Auf ihm lagen drei Commits, nicht vier.
2. **Die vier Commits gehören zum GSC-Zweig.** `arena/11d70b63-…` hatte vier Commits (Feature,
   Merge von `main`, Sicherheitsheilung der Suchradar-URL-Prüfung, Sitemap-Transport injizierbar).
   Beide Aufträge sind also im gleichen Zeitraum gelaufen, aber auf zwei Branches – die Erinnerung
   „ein Branch, vier Commits" vermischt sie.
3. **„main hereinholen" entfällt.** Beide Zweige sind in `main` aufgegangen; `main` ist seither
   durch die Automatik weitergewandert (`f15d367`). Zum Prüfzeitpunkt gab es repo-weit **null
   offene PRs** und keinen Zweig mit Vorsprung auf `origin/main`.

Ein PR wäre damit kein Arbeitsschritt gewesen, sondern ein leerer: Dieselbe Arbeit zweimal zu
mergen hätte entweder nichts geändert oder – bei einem neu aufgesetzten Zweig – die Gefahr
gebracht, eine bereits geheilte Fassung durch eine ältere zu ersetzen.

## 3. Befund B – die Vorlage ist gewandert, im selben Commit

Der Auftrag „Vorlage nach `.github/workflows/` verschieben" ist Bestandteil von #711. Beleg über
die Commit-Historie der beiden Pfade:

```
.github/workflows/gsc-import.yml
  4bffca7  12.10.2026 13:45 UTC  feat(seo): Search Console auf Dauerbetrieb … (#711)   ← angelegt

docs/workflow-vorlagen/gsc-import.yml
  4bffca7  12.10.2026 13:45 UTC  feat(seo): Search Console auf Dauerbetrieb … (#711)   ← entfernt
  90f4afab 11.10.2026 19:14 UTC  Datenschutzerklärung nach Code-Prüfung … (#705)       ← angelegt
```

Heutiger Bestand: `.github/workflows/gsc-import.yml` (15.657 Bytes) ist scharf,
`docs/workflow-vorlagen/` enthält nur noch `klick-import.yml`. Die Doku sagt es ausdrücklich:

> „Die Vorlage `docs/workflow-vorlagen/gsc-import.yml` ist entfernt: Ein scharfer Workflow und
> seine Vorlage dürfen nicht auseinanderlaufen." — `GSC-VERIFIKATION-INDEXIERUNG-PREMIUM-2026-10-12.md:184`

> „Die frühere Vorlage unter `docs/workflow-vorlagen/gsc-import.yml` ist damit überholt und
> entfernt." — `docs/ANLEITUNG-GSC-API-ZUGRIFF.md:181`

Genau deshalb wäre ein zweiter PR schädlich gewesen: Er hätte die Doppelhaltung
(Vorlage **und** scharfer Workflow) wiederhergestellt, also die Drift, die #711 gerade beseitigt
hat. Wer heute die Vorlage sucht, findet den Workflow selbst – er ist die einzige Wahrheit.

## 4. Verifikation auf dem gemergten Stand – nachgeholt, grün

Die Commits behaupten grüne Tests. Behauptungen wurden geprüft, nicht übernommen:

```
npm run test:suchradar
  Suchradar-Selbsttest bestanden: 13 Prüfblöcke, offline, ohne Netz.
  serp_anbieter-Selbsttest bestanden: 10 Anbieter, 11 Prüfblöcke, 10 Ausführer.
  Ran 80 tests in 0.667s — OK

npm run test:gsc
  Ran 57 tests in 0.474s — OK
  ✅ indexierbare_seiten   ✅ gsc_verifikations_guard (V1–V10 + V13 injiziert)
  ✅ gsc_indexierung (13 Fallgruppen, fail-closed)
  ✅ gsc_import (JWT/RS256 mit openssl verifiziert)   ✅ submit_indexnow
```

Dazu strukturell:

- Beide Workflow-Dateien sind gültiges YAML, Trigger `schedule` + `workflow_dispatch`,
  Rechte `contents: write` (GSC zusätzlich `pull-requests: write`, Suchradar `issues: write`).
- Alle acht referenzierten Skripte existieren: `gsc_import.py`, `gsc_indexierung.py`,
  `gsc_verifikations_guard.py`, `indexierbare_seiten.py`, `submit_indexnow.py`, `suchradar.py`,
  `serp_anbieter.py`, `selftest_ki.py`.
- Actions kennt beide Workflows als `active`: Suchradar ID 382062472 (angelegt 11:06 UTC),
  GSC-Tageslauf ID 382193288 (angelegt 13:45 UTC).

## 5. Der erste Lauf steht aus – und wurde bewusst nicht ausgelöst

**Beide Workflows haben null Läufe** (`total_count: 0`). Die Ursache ist banal: Beide sind heute
**nach** ihrem Cron-Slot gemerged worden.

| Workflow | Cron | Erster planmäßiger Lauf |
|---|---|---|
| GSC-Tageslauf | `17 5 * * *` | 13.10.2026, 05:17 UTC (07:17 Berlin) |
| Suchradar | `52 5 * * *` | 13.10.2026, 05:52 UTC (07:52 Berlin) |

Beide hätten per `workflow_dispatch` sofort laufen können. Vor dem Auslösen war der Secret-Status
zu klären – mit folgendem Ergebnis.

**Direkt nicht lesbar.** `GET /actions/secrets` und `/actions/variables` antworten mit
`403 Resource not accessible by integration`: Der Agent-Token darf den Geheimnisbestand des Repos
nicht einsehen. Eine Auskunft „Secret X ist gesetzt" ist damit nicht möglich – weder ja noch nein.

**Indirekt eindeutig: Das Dienstkonto ist noch nicht eingerichtet.** Vier unabhängige Spuren:

1. `data/gsc/` existiert nicht, `data/gsc_indexierung_state.json` existiert nicht – beides
   entsteht beim ersten Lauf. Nichts davon ist da.
2. `GSC_SERVICE_ACCOUNT_JSON` kommt im Kanal-Inventar der Secrets-Alters-Wache nicht vor:
   `data/secrets_state.json` und `data/monetization.yaml` kennen Pinterest, Mastodon, Umami und
   die KI-Keys – kein GSC-Eintrag.
3. `GSC-VERIFIKATION-INDEXIERUNG-PREMIUM-2026-10-12.md`, Abschnitt 6, führt die drei Handgriffe
   (Property verifizieren, Sitemap einreichen, Dienstkonto auf „Vollständig") als **offen**.
4. `docs/ANLEITUNG-GSC-API-ZUGRIFF.md`: „Das Anlegen dieser Werte machst du selbst. Der Agent
   legt keine Geheimnisse an."

Erwartbarer Ausgang eines Laufs ohne Secret: Status `nicht_konfiguriert`, Lauf bleibt grün,
kein Google-Kontingent wird verbraucht – so ist er gebaut, und die Selbsttest-Fallgruppe 2
(„intakte Sitemap, kein Zugang → exakt `nicht_konfiguriert`, keine Anfrage") nagelt das fest.

**Aber der Lauf ist nicht folgenlos.** Der IndexNow-Schritt braucht kein Google-Geheimnis:
`scripts/indexnow_key.txt` und `static/6t77zzoan6sl5i4b9jwcvx073202rgm9.txt` liegen bereit, der
Schlüsselvertrag ist geprüft. Ein manueller Lauf heute würde also

- die Live-Sitemap von `franksfinanzcheck.de` lesen und melden, was noch nicht im Zustand steht
  (`.indexnow_submitted.json` zählt 135 Einträge, davon 103 auf der Domain – gegen 74 indexierbare
  Seiten wäre die erste Live-Meldung wahrscheinlich klein oder leer; sicher ist das erst, wenn der
  Lauf die wirklich ausgelieferte Sitemap sieht),
- 32 `github.io`-Altlasten aus dem Zustand bereinigen,
- den Zustand **direkt auf `main`** schreiben (Absicht: ohne Kontingent-Gedächtnis verbrennt der
  nächste Lauf das Tageslimit von 200 Anfragen),
- die Live-Prüfung V13 gegen die ausgelieferte Site fahren und bei Abweichung warnen.

Das ist echte Außenwirkung an Bing, Yandex, Naver und Seznam plus ein Commit auf `main` – für
einen Lauf, dessen Google-Teil mangels Dienstkonto zwangsläufig `nicht_konfiguriert` meldet.
Deshalb: **nicht ausgelöst.** Der planmäßige Lauf morgen früh kostet nichts, was ein manueller
Lauf heute nicht auch kosten würde – und bis dahin können die drei Handgriffe erledigt sein, womit
der erste Lauf gleich den vollen Wert bringt statt eines Zustandsberichts.

## 6. Was jetzt zu tun ist

Drei Handgriffe im Google-Konto (kein Agent kann sie übernehmen, zusammen unter zehn Minuten):

1. Domain-Property `franksfinanzcheck.de` per DNS-TXT in Cloudflare verifizieren.
2. Sitemap `https://franksfinanzcheck.de/sitemap.xml` in der Search Console einreichen.
3. Dienstkonto in der Search Console auf Stufe „Vollständig" setzen, dazu
   `GSC_SERVICE_ACCOUNT_JSON` (Secret) und `GSC_SITE_URL` = `sc-domain:franksfinanzcheck.de`
   (Variable) hinterlegen – Anleitung: `docs/ANLEITUNG-GSC-API-ZUGRIFF.md`, Schritte 5 und 6.

Danach einmalig:

```bash
npm run gsc:setup                            # erwartet: siteOwner
python3 scripts/gsc_import.py --backfill     # 480 Tage Leistungsdaten nachholen
python3 scripts/gsc_indexierung.py --live --plan   # fällige Seiten – passen in EIN Tageskontingent
```

**Den ersten Lauf beobachten:** Actions → „GSC-Tageslauf (Daten + Indexierungs-Anfragen)", Lauf vom
13.10.2026 05:17 UTC öffnen. Die Lauf-Zusammenfassung trägt vier Blöcke: Verifikation/Indexierbarkeit
LIVE (V13), fällige Seiten als Plan, Indexierungs-Anfragen mit Kontingentstand, Einordnung der drei
Kanäle. Zwei Statuswerte sind dabei erwartbar und beide kein Defekt: `nicht_konfiguriert`
(Secret fehlt) und `keine_berechtigung` (Dienstkonto nur „Eingeschränkt"). Leistungsdaten kommen
als PR, Zustand geht direkt auf `main` – ein reines Lebenszeichen löst keinen Deploy aus, beide
Pfade stehen in der STATE_ONLY-Negativliste des Deploy-Gates.

Wer den Suchradar-Lauf sehen will: Actions → „Suchradar – Suchergebnis-Erfassung", 05:52 UTC.
Erster Anlaufpunkt bei Fragen ist `docs/ANLEITUNG-SUCHRADAR.md`; die Anbieter-Probe beantwortet,
welcher schlüssellose Kanal an diesem Tag antwortet.

## 7. Ehrliche Grenzen

- **Der Secret-Status ist ein Indizienbeweis, keine API-Auskunft.** Vier unabhängige Spuren
  sprechen gegen ein eingerichtetes Dienstkonto, lesen lässt sich der Bestand mit diesem Token
  nicht. Ein Blick in Repo → Settings → Secrets and variables → Actions beantwortet es in zehn
  Sekunden endgültig.
- **V13 (live) ist hier nicht gelaufen.** Die Sandbox erreicht `franksfinanzcheck.de` nicht; der
  Build-Befund V1–V12 ist grün, die Live-Prüfung läuft erstmals im Tageslauf. Dieser Satz steht
  seit dem 20.09.2026 im Runbook und gilt für diesen Bericht genauso.
- **Die Suchradar-Parser sind gegen echte HTML-Proben getestet, nicht gegen Live-Antworten.**
  Auch das ist im Bericht zu #709 so dokumentiert und bleibt so stehen: Erster Lauf = `--probe`.
- **Dieser Report ändert keinen Code.** Er hält einen Übergabestand fest, der sonst nur über
  PR-Historie und Actions rekonstruierbar wäre.

## 8. Geänderte Dateien

**Neu**

- `SUCHRADAR-GSC-MERGE-STAND-UND-ERSTER-LAUF-PREMIUM-2026-10-12.md` – dieser Befund

**Unverändert**

- `.github/workflows/gsc-import.yml`, `.github/workflows/suchradar.yml` – seit #709/#711 scharf
- `docs/workflow-vorlagen/` – enthält weiterhin nur `klick-import.yml`; die GSC-Vorlage bleibt
  entfernt, und das ist richtig so
