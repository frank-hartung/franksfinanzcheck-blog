# Inhaltsqualität WF-1F8C – dauerhaft auf Premium-Level behoben

**Datum:** 2026-10-02
**Auslöser:** Issue #522 „🔧 Wartung · Inhaltsqualität · Vorgang WF-1F8C“ –
Kadenz-Endkontrolle (Mo/Mi/Fr) zweimal rot (Runs 37033328949 und 37063749560),
Schritt „Reconcile final source quota and deficit issue“.
**Sichtbares Symptom:** `test 'failure' = success` schlug an, Tagesquote 1/2,
Hugo-Build im Release-Gate tot.

---

## 1) Was wirklich kaputt war

Der rote Schritt war nur der Melder. Die echte Ursache stand im Hugo-Log des
Release-Gates:

```
ERROR rechner: unbekannter typ "[notgroschen](../../posts/2026-09-09-notgroschen-…/)"
       (erlaubt: notgroschen, budget-503020, strom-abschlag, gas-abschlag, dsl-effektiv)
ERROR error building site: logged 1 error(s)
```

**Tathergang, lückenlos belegt:**

1. Phase 2 der Content-Engine ruft `blog_doctor.py` → der ruft
   `link_density_guard.py --fix` → der wirft `internal_linker.py --apply` an.
2. `internal_linker.find_anchor()` sperrte Überschriften, Code-Blöcke und
   bestehende Links – **aber keine Hugo-Shortcodes**. Im Artikel
   `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` war das
   erste freie Vorkommen von „notgroschen“ ausgerechnet der Parameter in
   `{{</* rechner typ="notgroschen" … */>}}` (Beweis: altes Verhalten trifft
   Position 4729 = IM Shortcode; Artikelstand `c181d75^`).
3. Commit `c181d75` („content: Qualitäts-Fixes …“) schrieb
   `typ="[notgroschen](../../posts/…/)"` auf `main` – ab da baute **kein
   einziger Hugo-Lauf** mehr: Release-Gate rot, nur 1 statt 2 Artikel LIVE,
   beide Endkontrollen des Tages fehlgeschlagen → WF-1F8C.
4. `5c1ef03` (WF-D4E0, #530) hat den **Inhalt** repariert – die **Ursache**
   (shortcode-blinder Linker) blieb scharf. Ein erneuter Treffer war nur eine
   Frage der Läufe: „notgroschen“ ist weiterhin Keyword-Kandidat, und auch
   `budget-503020`-/`dsl-effektiv`-Artikel tragen Rechner-Shortcodes.

## 2) Die Reparatur (Ursache, nicht Symptom)

### A. Linker ist jetzt shortcode- und HTML-blind (Root-Cause-Fix)

`scripts/internal_linker.py`:

- Neue Sperrzonen in `find_anchor()`: `{{</* … */>}}` / `{{%/* … */%}}`
  (dotall, auch mehrzeilig) und Inline-HTML-Tags (`alt=`, `title=`,
  `aria-label=` sind Markup-Substanz, kein Fließtext).
- Neuer `--selftest`: beweist am realen WF-1F8C-Muster (bereits verlinkter
  Anker + nächstes Vorkommen im Shortcode), dass nur der freie Fließtext-Satz
  getroffen wird. Läuft ab sofort **vor jedem** `--apply`.

Regressionsbeweis am Original-Artikelstand `c181d75^`:
altes Verhalten → Treffer Pos 4729 (im Shortcode) · neues Verhalten →
Treffer Pos 4880 („Ein Notgroschen muss …“, freier Fließtext).

### B. Shortcode-Wache als Fangnetz (Defense in Depth)

Neu: `scripts/shortcode_guard.py` (unter Integritäts-Siegel, wie der Linker):

- findet Markdown-Links in Shortcode-Parametern blog-weit,
- `--fix` entlinkt deterministisch (Label bleibt, Link fliegt raus –
  stellt exakt den Zustand vor dem Schaden wieder her, byte-identisch
  verifiziert am echten Artikel),
- `--selftest` beweist Erkennung + Heilung + „kein False Positive auf
  sauberem Bestand“.

### C. Verdrahtung auf allen Schreibpfaden

| Pfad | Absicherung |
|---|---|
| `content-engine-v2.yml` Phase 2 (Doktor→Density→Linker) | Wache `--selftest` + `--fix` **vor dem Commit** |
| `content-engine-v2.yml` Phase 3 (Linker direkt) | Linker-`--selftest` vor `--apply`, Wache `--fix` danach |
| `seo-weekly.yml` (Linker direkt) | Linker-`--selftest` vor `--apply`, Wache `--fix` danach |
| `link_density_guard.py` (jeder Aufrufer, z. B. blog-health-daily) | Wache `--fix` direkt nach dem Linker-Subprozess |
| `kadenz-endkontrolle.yml` (Opferseite) | Wache `--selftest` + `--fix` im Recovery-Schritt – heilt auch **bereits committeten** Schaden, bevor das Release-Gate baut |

Damit gilt: Selbst wenn ein künftiger, heute unbekannter Heiler einen
Shortcode zerreißt, wird der Schaden (a) im selben Lauf entlinkt und
(b) spätestens von der Endkontrolle selbst geheilt statt als roter Run
gemeldet.

### D. Integritäts-Siegel

`internal_linker.py`, `link_density_guard.py` und die neue Wache sind im
selben Commit neu signiert (`integrity_guard.py --set-current`,
`data/integrity_lock.json`); die Wache ist als build-entscheidende Datei in
den Kernbestand aufgenommen.

## 3) Beweisläufe (lokal, deterministisch)

| Prüfung | Ergebnis |
|---|---|
| `internal_linker.py --selftest` | ✅ Sperrzonen greifen, nur Fließtext wird verlinkt |
| `shortcode_guard.py --selftest` | ✅ erkennt + heilt WF-1F8C-Muster, kein False Positive |
| Schaden-Injektion in den echten Artikel → `--fix` | ✅ byte-identisch zurückgeheilt (git-diff leer) |
| `internal_linker.py --dry-run` (ganzer Bestand) | ✅ 16 saubere Vorschläge, 0 in Shortcodes |
| `shortcode_guard.py` (ganzer Bestand) | ✅ 0 Funde – Bestand ist build-sicher |
| `integrity_guard.py` | ✅ Kern exakt im signierten Zustand |
| Workflow-YAML (3 Dateien) | ✅ parsebar |

## 4) Warum das dauerhaft ist

- **Ursache beseitigt:** Der einzige Schreiber, der je in Shortcodes
  hineingelinkt hat, kann die Zone technisch nicht mehr treffen.
- **Selbsttest als Wächter des Fixes:** Jeder produktive Linker-Lauf beweist
  die Sperrzonen erneut, bevor er schreiben darf – ein Regressionsrückbau
  fällt im selben Lauf auf, nicht erst im Build.
- **Zwei unabhängige Fangnetze:** Schreibpfad (vor dem Commit) und
  Endkontrolle (nach dem Commit) heilen deterministisch, ohne KI, ohne Netz.
- **Siegelpflicht:** Änderungen an Linker/Wache erfordern eine bewusste
  Neu-Signatur im selben Commit.
