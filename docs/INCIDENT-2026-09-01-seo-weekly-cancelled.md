# Vorfall-Bericht: „Wöchentliche SEO-Optimierung (cancelled)" — Issue #141

**Datum:** 01.09.2026 · **Status:** behoben · **Schweregrad:** niedrig (Falsch-Alarm + Hänger)

## Was gemeldet wurde
Issue #141: „⚠️ Workflow fehlgeschlagen: Wöchentliche SEO-Optimierung (cancelled)",
Run [33520275782](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/33520275782),
Branch `main`, Commit `e7238f7d`, 01.09.2026 16:33 Uhr.

## Was tatsächlich passiert ist
1. Der Lauf **ist nicht abgestürzt** — er wurde nach 5:05 Minuten **von Hand abgebrochen**
   (Annotation im Run: „The run was canceled by @frank-hartung").
2. Abbruch-Zeitpunkt war der Schritt **„Keyword-Optimierungs-Audit + KI-LSI-Vorschläge"**.
   Der Schritt hing an einer nicht antwortenden KI-Schnittstelle (Groq/Gemini).
   Es gab **kein Job-Zeitlimit**, der Lauf hätte theoretisch bis zum GitHub-Maximum
   (6 Stunden) blockiert — deshalb der manuelle Abbruch.
3. Das Fehler-Alerting behandelte `conclusion == 'cancelled'` pauschal wie einen Defekt
   und legte deshalb ein Fehler-Issue an, obwohl ein Mensch bewusst abgebrochen hatte.
4. Der direkt danach manuell gestartete Lauf lief durch — es liegt **kein Content-,
   SEO- oder Affiliate-Schaden** vor. Kein Artikel, kein Link, kein Cover ist betroffen.

## Ursachen (2 unabhängige)
| # | Ursache | Wirkung |
|---|---------|---------|
| A | `seo-weekly.yml` ohne `timeout-minutes` (Job und KI-Schritte) | Hänger blockiert den Lauf, nur manueller Abbruch hilft |
| B | `alert-on-failure.yml` wertet jedes `cancelled` als Fehlschlag | Falsch-Alarm-Issues nach jedem Handabbruch |

## Behebung
**A — Zeitlimits (`.github/workflows/seo-weekly.yml`)**
- Job: `timeout-minutes: 75` (der Regel-Lauf braucht ca. 15–25 Min.)
- Schritt-Limits: SEO-Audit 15 · Keyword-KI 20 · Meta-KI 20 · Pinterest-SEO-Healer 20 ·
  Rechtschreibung 20 · Grammatik (LanguageTool) 25 · IndexNow 10
- Nebenbei repariert: verrutschte Einrückung von `exit ${PIPESTATUS[0]}` im Meta-Schritt.

**B — Falsch-Alarm-Filter (`.github/workflows/alert-on-failure.yml`)**
- `cancelled` löst nur noch dann ein Issue aus, wenn der Abbruch **nicht** von einem
  Menschen bzw. der Concurrency-Regel kam (Prüfung der Job-Annotationen
  „canceled by @…", „higher priority waiting request").
- `timed_out` neu als Auslöser aufgenommen (echte Hänger werden künftig gemeldet).
- Issue-Text nennt jetzt den **konkret gescheiterten Schritt** (Job → Schritt → Grund),
  dazu Berechtigungen `actions: read`, `checks: read` und `timeout-minutes: 10` je Job.

## Was das im Alltag bedeutet
- Hängt eine KI-Schnittstelle, bricht **der Workflow selbst** nach dem Zeitlimit ab —
  du musst nicht mehr eingreifen. Der Abbruch heißt dann `timed_out` und meldet sich
  ehrlich als Fehler.
- Brichst du selbst ab, bleibt es still: kein Issue, kein Rauschen.
- Fehlermeldungen sagen ab sofort direkt, **welcher** Schritt betroffen ist.

## Empfehlung fürs nächste Mal
Bei einem hängenden Lauf: abbrechen ist völlig in Ordnung, danach einmal
Actions → „Wöchentliche SEO-Optimierung" → *Run workflow*. Kommt derselbe Schritt
zweimal in Folge nicht durch, sind die Secrets `GROQ_API_KEY` / `GEMINI_API_KEY` zu prüfen.

## Übernahme der Workflow-Änderungen (ein Schritt, 1 Minute)
Der Automat darf `.github/workflows/**` nicht selbst pushen (GitHub-App ohne
`workflows`-Recht). Die fertigen Dateien liegen deshalb im Repo bereit:

- `patches/seo-weekly-2026-09-01-ready.yml` → nach `.github/workflows/seo-weekly.yml`
- `patches/alert-on-failure-2026-09-01-ready.yml` → nach `.github/workflows/alert-on-failure.yml`
- Alternativ als Diff: `patches/issue-141-2026-09-01-workflows.patch`

**Lokal übernehmen:**
```bash
git apply patches/issue-141-2026-09-01-workflows.patch
git commit -am "fix(ci): Zeitlimits + Falsch-Alarm-Filter (Issue #141)"
git push
```
**Oder im Browser:** die beiden `*-ready.yml` öffnen, Inhalt kopieren, in die
gleichnamige Datei unter `.github/workflows/` einfügen, „Commit changes".
