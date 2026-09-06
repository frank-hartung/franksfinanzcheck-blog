## Befund (Chefredaktion / Ops)

**Das war kein echter Fehlschlag.** Run `33520275782` wurde nach 5:05 Min. **von Hand abgebrochen** (Annotation: „The run was canceled by @frank-hartung"). Abbruchstelle: Schritt **„Keyword-Optimierungs-Audit + KI-LSI-Vorschläge"** – die KI-Schnittstelle (Groq/Gemini) antwortete nicht, und der Workflow hatte **kein Zeitlimit**, hätte also bis zu 6 Stunden weiterblockiert.

Inhaltlich ist **nichts beschädigt**: keine Artikel-, Link-, Cover- oder Affiliate-Änderung blieb halb angewandt. Der direkt danach gestartete Lauf hat die kritischen Schritte sauber passiert.

### Zwei Ursachen, beide behoben

| # | Ursache | Fix |
|---|---------|-----|
| A | `seo-weekly.yml` ohne `timeout-minutes` | Job 75 Min. + Schritt-Limits (SEO-Audit 15 · Keyword-KI 20 · Meta-KI 20 · Pinterest-Healer 20 · Rechtschreibung 20 · Grammatik 25 · IndexNow 10) |
| B | Alerting wertete **jedes** `cancelled` als Defekt | Handabbrüche/Concurrency werden über die Job-Annotationen erkannt und erzeugen **kein** Issue mehr; dafür meldet sich `timed_out` neu als echter Fehler – inklusive Nennung des betroffenen Schritts |

Nebenbei repariert: verrutschte Einrückung von `exit ${PIPESTATUS[0]}` im Meta-Schritt.

### Übernahme

Der Bot darf `.github/workflows/**` nicht pushen (GitHub-App ohne `workflows`-Recht). Fertig liegen auf Branch `arena/01a05e1c-franksfinanzcheck-blog`:

- `patches/seo-weekly-2026-09-01-ready.yml`
- `patches/alert-on-failure-2026-09-01-ready.yml`
- `patches/issue-141-2026-09-01-workflows.patch` (`git apply`)
- Vorfall-Bericht: `docs/INCIDENT-2026-09-01-seo-weekly-cancelled.md`

Sobald der laufende SEO-Lauf grün endet, schließt das Auto-Close dieses Issue von selbst.
