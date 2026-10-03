# Inhaltsqualität WF-A535 – dauerhaft auf Premium-Level behoben

**Datum:** 2026-10-02
**Auslöser:** Issue #529 „🔧 Wartung · Inhaltsqualität · Vorgang WF-A535“ –
Content-Engine v2 am 02.10.2026 dreimal rot (Runs 37007043195, 37052950135,
37066812647), jeweils am Schritt „Do not report a quota deficit as success“.
**Sichtbares Symptom:** Endabnahme „fehlgeschlagen“, Tagesquote 1/2, Auto-Issue
rät zu API-Keys, GitHub-Status und „transient – einfach neu starten“.

---

## 1) Was wirklich kaputt war

Drei rote Läufe, **zwei verschiedene Ursachen** – und in der Klasse, die
Ticket #529 meldet (Lauf 19:15 UTC / 21:15 MESZ), war das Symptom gelogen:

| Lauf (UTC) | „Final publication acceptance“ | Dauer | Klasse |
|---|---|---:|---|
| 12:30 | 13:08:22 → 13:08:28 | 6 s | **echtes Defizit 0/2** – beide Maschinen-Texte fielen um 12:41 am Gate, Reserve-Pool leer (WF-D4E0-Vormittag, behoben via #530) |
| 19:15 (**#529**) | 19:50:14 → 19:50:17 | **3 s** | **Build-Crash** – kein Defizit-Urteil |
| 21:26 | 21:59:36 → 21:59:39 | **3 s** | **Build-Crash** – kein Defizit-Urteil |

Grüne Läufe zum Vergleich (28.09./30.09.): 12–19 s Endabnahme. Drei
Sekunden sind kein Defizit-Urteil, das ist ein **Crash vor der ersten
Tat**. Lokal am Originalzustand (Commit d404e75d) reproduzierbar:

```
ERROR rechner: unbekannter typ "[notgroschen](../../posts/2026-09-09-notgroschen-…/)"
       (erlaubt: notgroschen, budget-503020, strom-abschlag, gas-abschlag, dsl-effektiv)
ERROR error building site: logged 1 error(s)
subprocess.CalledProcessError: Command '('hugo', '--minify', …)' returned non-zero exit status 1.
```

**Tathergang, lückenlos belegt:**

1. **19:49:24** – Phase 2 des 19:15-Laufs committet c181d75 („content:
   Qualitäts-Fixes …“): Der shortcode-blinde `internal_linker` hatte
   „notgroschen“ *INNERHALB* von `{{</* rechner typ="notgroschen" … */>}}`
   zu `typ="[notgroschen](../../posts/…/)"` verlinkt. Ab da baute kein
   einziger Hugo-Lauf mehr. (Dass der 12:30-Lauf separat ein ehrliches
   0/2-Defizit meldete, ist die WF-D4E0-Geschichte des Vormittags: leerer
   Reserve-Pool, behoben in #530 – nicht Ursache dieses Vorgangs.)
2. **19:50:14** – Die Endabnahme des selben Laufs stirbt am ERSTEN Build
   mit rohem Traceback. `continue-on-error` schluckt den Schritt, der
   letzte Schritt macht ihn rot → WF-A535 (#529). **Der Reserve-Refill
   lief nie** – obwohl PR #530 den Pool Minuten später mit 6/6 zertifizierten
   Kandidaten füllte.
3. **21:26** – Der nächste Lauf checkt den korrumpierten Stand aus
   (f6fefea0), stirbt identisch; zusätzlich scheitert „Persist final
   acceptance corrections“ am Push-Rennen mit dem Deploy (cfbae924 löschte
   parallel urlaubskasse/stromfresser). Die Auslieferung des Tages
   rettete schließlich der **Deploy** selbst (preisswert-surfen, 22:52,
   über `publication_release.py --refill-only`).
4. **21:37 / 23:48** – PR #530 (WF-D4E0) heilt den *Inhalt* zufällig mit
   (Merge-Ergebnis ohne den zerrissenen Parameter); e7194aa (WF-1F8C
   #522) behebt die *Ursache*: Linker-Sperrzonen, `shortcode_guard.py`,
   Verdrahtung in Phase 2/3, seo-weekly, link_density_guard und – nur! –
   die **Kadenz-Endkontrolle**.

## 2) Die verbliebene Lücke (und warum #529 trotzdem offen war)

WF-1F8C schützte den **Schreiber** und die **Opfer-Seite Kadenz**. Die
**Endabnahme der Engine** blieb ungeschützt und stumm:

- `content-engine-v2.yml` rief `publication_release.py` direkt – ohne die
  Shortcode-Wache davor (die Kadenz-Endkontrolle hatte sie bereits).
- `publication_release.py` starb bei totem Build mit rohem Traceback und
  **Exit 1 – dem Code des ehrlichen Tagesdefizits**. Der Wächter-Schritt
  „Do not report a quota deficit as success“ konnte Crash und Defizit
  begrifflich gar nicht unterscheiden; das Auto-Issue riet in die
  falsche Richtung („API-Key? GitHub-Status?“).
- Ein schon committierter Schaden aus einem *ungedeckten* Schreibpfad
  (Politur, KI-Redaktion, manuelle Commits, Push-Rennen während des
  Laufs) erreicht die Engine-Endabnahme weiterhin ungefiltert.

Genau diese Kombination hat am 02.10. drei rote Läufe, ein irreführendes
Ticket und einen nie gelaufenen Reserve-Refill erzeugt.

## 3) Die Reparatur (Ursachen-Schutz für die Endabnahme, nicht Symptom)

### A. Eine Quelle der Heilung – alle Aufrufer (Defense in Depth)

`scripts/publication_release.py` ruft am Anfang **jedes** Laufs
(Engine-Endabnahme, Kadenz-Backstop, Deploy-Refill) die Shortcode-Wache
best-effort auf: `heal_shortcode_damage()` → `shortcode_guard.py --fix`.
Die deterministische Schadensklasse („Markdown-Link im Shortcode-
Parameter“) kann die Endabnahme damit gar nicht mehr erreichen – egal
welcher Schreiber sie verursacht hat. Best-Effort bewusst: Der Build
selbst bleibt die harte, fail-closed Instanz.

### B. Der Build diagnostiziert sich selbst

Neu `build_site()`: Der Hugo-Build läuft mit Ausgaben-Einfang. Stirbt er,
erscheint statt des Tracebacks eine strukturierte Diagnose – die echte
Hugo-Fehlerzeile, die bekannte Schadensklasse, der Reparaturpfad
(`shortcode_guard.py` / `--fix`) und der Hinweis, dass bei fortbestehendem
Rot eine *andere* Build-Ursache (Layout, Frontmatter, Theme) vorliegt.
Dazu ein Audit-Event (`publication_release`/`build_error`, fail_closed)
in `data/audit/` – die maschinenlesbare Spur, die am 02.10. fehlte.
Das gleiche gilt für alle übrigen Werkzeugaufrufe (`_report_tool_crash`).

### C. Exit-Codes als Vertrag: Defizit ≠ Crash

| Exit | Klasse | Bedeutung |
|---:|---|---|
| 0 | OK | Endabnahme bestanden / kein Publikationstag |
| 1 | **TAGESDEFIZIT** | ehrlich rot, unveränderte Semantik (`publication_check`) |
| 3 | **RELEASE-CRASH** | Build oder Gate-Werkzeug versagt – fail-closed, diagnostiziert |

### D. Verdrahtung: Engine bekommt das Kadenz-Muster + klassenklare Wache

- `content-engine-v2.yml`: Neuer Schritt **„Shortcode-Wache vor der
  Endabnahme (WF-A535 #529)“** – Selbsttest hart, `--fix` konvergent
  (Heilungen committet der bestehende „Persist final acceptance
  corrections“-Schritt). Spiegelt exakt die Kadenz-Endkontrolle.
- Der Schritt „Final publication acceptance“ schreibt seinen Exit-Code
  nach `$GITHUB_OUTPUT` (`rc`); der Wächter-Schritt am Ende benennt die
  Klasse als Annotation: `::error::TAGESDEFIZIT …` bzw.
  `::error::RELEASE-CRASH (WF-A535 #529) …`. Damit steht die Ursache
  sichtbar im Run und in den Check-Annotationen – nicht nur im Log-Leib,
  und das Fehler-Ticket verlinkt direkt auf den diagnostizierten Schritt.

### E. Tests & Selbsttest (Sabotage-Schutz)

- Neu **`scripts/tests/test_publication_release_wache.py`** (13 Fälle):
  Heilungs-Vertrag (ruft `--fix`, warnt statt zu blockieren), Diagnose
  am **echten** Hugo-Log des Laufs 37052950135, Crash → Exit 3 statt
  Traceback, Defizit bleibt Exit 1, und die **Workflow-Verdrahtung**
  (Wache vor Endabnahme, Klassennennung) als pinierter Vertrag – nach
  dem Vorbild des Deploy-Verdrahtungs-Tests (#287).
- `publication_release.py --selftest` um die WF-A535-Proben erweitert
  (offline, ohne Hugo/Netz, ohne Repo-Schreibzugriff; Audit gepatcht).
- Bestands-Suite: **1327 Tests, OK** (18 erwartete Skips) ·
  `integrity_guard --drift-audit`: Siegel unangetastet (44 Kerndateien,
  kein Drift – keine gesiegelte Datei geändert).

### F. Beweisläufe am Originalzustand (d404e75d, echtes Schadensbild)

| Prüfung | Ergebnis |
|---|---|
| Neuer Code **ohne** Wache im Baum (alter Stand) | 🛑 strukturierte Diagnose, **Exit 3**, statt Traceback Exit 1 |
| Neuer Code **mit** Wache | ✅ „geheilt: … [notgroschen](…) entlinkt“ → Hugo baut (74 Seiten) → Endabnahme **Exit 0** |
| `shortcode_guard.py` über den Bestand | ✅ 0 Funde – Parameters build-sicher |
| YAML der Engine-Workflow | ✅ parsebar, 19 Schritte, Reihenfolge Wache → Endabnahme → Wächter |

## 4) Was NICHT geändert wurde (Scope-Disziplin)

- **Keine Gate-Lockierung, kein Exit-Code-Weichspüler:** Ein toter Build
  bleibt rot (Exit 3) – er wird nur benennbar statt stumm. Ein echtes
  Tagesdefizit bleibt Exit 1, exakt wie vorher.
- **`alert-on-failure.yml` unangetastet:** Das zentrale Fehler-Alerting
  (Marken-Oberfläche, Dedupe, Auto-Close) trägt weiterhin Workflow-Name
  und Schritt-Link. Die Ursache steht jetzt im verlinkten Schritt-Log
  und als Annotation – ohne eine weitere Instanz, die Logs parsen müsste.
- **`git_sync.sh` unangetastet:** Das Push-Rennen am 21:26-Lauf war
  Symptom des gecrashten/überholten Laufs; git_sync hat die Klasse
  bereits strukturiert behandelt (Härtung #233/#295/#329).
- Keine gesiegelte Datei geändert (Linker, Wache, Dichte-Guard gehören
  zum Siegel-Kern); `publication_release.py` steht außerhalb und bleibt
  bewusst dort – die Endabnahme ist Orchestrator, kein Marken-Kern.

---

**Artefakte dieses Vorgangs:** `scripts/publication_release.py`
(Heilung + Diagnose + Exit-Vertrag), `scripts/tests/test_publication_release_wache.py`,
`content-engine-v2.yml` (Wachen-Schritt, rc-Ausgabe, klassenklare Endkontrolle),
Selbsttest-Erweiterung, dieser Report, CLAUDE.md-Vertrag.

**Vorgangs-Kette 02.10.2026:** WF-D4E0 (#513/#530, Reserve-Pool) ·
WF-1F8C (#522/#536, shortcode-blinder Linker) · **WF-A535 (#529, diese
Reparatur: Endabnahme immun + diagnostizierbar)**. Schließt #529.
