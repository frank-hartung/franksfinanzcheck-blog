# 🧬 Einzigartigkeits-Audit: Bestandsüberlappungen dauerhaft behoben

**Datum:** 01.10.2026 · **Bezug:** Issue #490 „📋 Einzigartigkeits-Audit:
Bestandsüberlappungen gefunden" (Quartals-Workflow, Einzigartigkeits-Gate) ·
**Auftrag:** „Bitte dauerhaft auf Premium-Level einer Profi-Agentur beheben."

---

## 1. Ausgangslage

Der Quartalslauf (`update-quarterly.yml`) meldete am 01.10.2026:

```
Ergebnis: Pin-Konflikte: 0 | Interne Überlappungen: 30 | Kritisch: 10 | Same-Day-Twins: 0
⚠️ KRITISCHE DUPLIKATE GEFUNDEN
```

Das Ticket schloss mit dem Satz, der solche Tickets alt werden lässt:
*„Betroffene Passagen bei Gelegenheit redaktionell umformulieren."* Zehn Funde,
kein Besitzer, keine Frist, nicht blockierend — und drei Monate bis zum nächsten
Lauf.

Die Prüfung der zehn Funde ergab **drei verschiedene Fehlerklassen in einer
Liste**. Das ist der eigentliche Befund: Eine Wache, die Messfehler und echte
Schäden gleich laut meldet, wird nicht abgearbeitet.

| Klasse | Funde | Was wirklich dahintersteckt |
|---|---|---|
| **A — Messfehler: Navigation** | 3 | Ankertexte interner Links. `internal_linker.py` setzt dort per Konstruktion den **Titel des Zielartikels**. Zwei Ratgeber, die denselben Pillar verlinken, „teilten" dadurch bis zu acht 7-Wort-Phrasen. Die Wache bestrafte **korrekte interne Verlinkung** — die naheliegende „Heilung" wäre gewesen, Ankertexte zu verstümmeln oder Links zu löschen. |
| **B — Messfehler: Entwürfe** | 3 | Paare, an denen ein `draft: true`-Artikel beteiligt ist. Hugo baut Entwürfe nicht (`buildDrafts = false`): keine URL, kein Index, keine Kannibalisierung. Ein Entwurf ist eine Aufgabe **vor** der Veröffentlichung, kein Bestandsschaden. |
| **C — echte Dopplung** | 4 | Gleiche Sätze, gleiche Tabellen, gleiche Kennzahl-Formulierungen in **veröffentlichten** Artikeln (Gas/Heizkosten-Cluster, Frugalismus-Cluster). Das ist der Teil, der Duplicate Content und Keyword-Kannibalisierung erzeugt. |

Dazu ein Fund, den das Audit nur indirekt sichtbar machte und der für sich
genommen gravierender ist als jede Überlappung:

> **Acht Live-Artikel begannen direkt unter der Überschrift mit
> `ARTIKEL-TITEL: …`, `KEYWORDS: …`, `ARTIKEL-TEXT:`.**

Das ist der Prompt-Kopf aus `scripts/update_articles.py`, den das Modell
zurückgespiegelt hat und den die Routine ungeprüft in den Body geschrieben hat.
Für den Leser Maschinenmüll, für Google ein Qualitätssignal — und im Audit
kollidierte der echo-te Titel mit den Ankertexten anderer Artikel.

## 2. Prinzip der Reparatur

Drei Ebenen, in dieser Reihenfolge — alles andere wäre Kosmetik:

1. **Richtig messen.** Ein Befund zählt nur, wenn er wirken kann.
2. **Echte Schäden redaktionell beheben.** Keine Maschine formuliert um.
3. **Quelle schließen und Takt erhöhen.** Sonst steht dasselbe Ticket im
   nächsten Quartal wieder da.

---

## 3. Ebene 1 — Messgenauigkeit

### 3.1 Navigation ist kein Fließtext

`scripts/template_boilerplate.py` (SSOT für `check_uniqueness.py` **und**
`quality_score.py` — eine Quelle, damit die Listen nie auseinanderlaufen):

```python
INTERNAL_LINK_RE = re.compile(r"\[[^\]]*\]\(\s*(?:\.{1,2}/|/)(?![/])[^)\s]*\)")

def strip_internal_link_anchors(text: str) -> str:
    """Entfernt interne Markdown-Links samt Ankertext (Navigation, kein Text)."""
```

Intern = relatives (`../../posts/…`) oder wurzel-relatives Ziel (`/posts/`,
`/pillar/`, `/go/`). **Externe** Linktexte bleiben in der Messung: Sie sind
redaktionelle Formulierung, und zwei Artikel mit identischem Satz um eine
Quellenangabe herum sind ein echter Befund. Eingefroren im Selbsttest
(Fälle 5–8, inklusive Gegenprobe und Idempotenz).

### 3.2 Befund-Klassen: live↔live ist der Bestand, Entwürfe sind Vorarbeit

Neu in `scripts/check_uniqueness.py`:

```python
KRITISCH_AB = 5          # ab so vielen geteilten Phrasen ist es Dopplung

def paar_klasse(overlap, a_draft, b_draft, max_sim=1) -> str:
    """ok | unkritisch | entwurf | kritisch"""
```

* **kritisch** → nur zwischen zwei veröffentlichten Artikeln; bestimmt allein
  den Exit-Code des Bestands-Audits.
* **entwurf** → eigener Report-Abschnitt „2b) Entwürfe mit Überlappung
  (nicht veröffentlicht)", mit Kennzeichnung `[live]` / `[Entwurf]` je Seite.
  Sichtbar, benannt, mit klarer Handlungsansage — aber ohne den Bestand rot zu
  färben.

Die Schwelle (5 geteilte 7-Wort-Phrasen) bleibt unverändert; neu ist nur, dass
sie einen **Namen** hat und im Test steht.

### 3.3 C7 — Generator-Gerüst (`content_audit.py`)

```
C7  GENERATOR-GERUEST: echo-te Prompt-Kopfzeilen der KI-Auffrischung
    („ARTIKEL-TITEL:", „KEYWORDS:", „ARTIKEL-TEXT:") → AUTO-FIX
```

Auto-Fix ist hier deterministisch sicher: Die Marke greift nur am
**Zeilenanfang mit Doppelpunkt**, das Frontmatter liegt in den Schutzzonen der
Maske, und es gibt keinen redaktionellen Grund für eine Zeile, die mit
`ARTIKEL-TEXT:` beginnt. Gegenprobe im Selbsttest: `## Keywords im Marketing`
und „Er sagte: Keywords: sind wichtig." bleiben unangetastet (Fall 13).

**Ergebnis:** 17 Gerüst-Zeilen in 8 Live-Artikeln entfernt.

---

## 4. Ebene 2 — Redaktion (die echten Dopplungen)

Leitregel für wiederkehrende Kennzahlen, ab sofort verbindlich:

> **Die Zahl darf überall stehen. Der Satz darum muss artikel-eigen sein.**

Der BDEW-Wert (11,93 ct/kWh, Einfamilienhaus, 2026) gehört in jeden
Gas-Ratgeber — er stand aber in vier Artikeln in nahezu identischer
Formulierung. Fakten bleiben unverändert; der Blick darauf ist jetzt je
Artikel ein anderer:

| Artikel | Neue Perspektive auf dieselbe Zahl |
|---|---|
| `2026-08-24-preisgarantie-gas-…` | „…beschreibt den Markt von gestern" — passend zum Thema Börsenpreis vs. Rechnung |
| `2026-09-07-heizkosten-senken-…` | Zahl zuerst, dann die Maßstab-Frage: „Liegt dein Arbeitspreis klar darüber, lohnt der Blick in den Vertrag." |
| `2026-09-20-gasrechnung-senken-so-bereitest-du-…` | „Messlatte" — passend zum Prüf- und Nachzahlungs-Thema |
| `2026-09-20-gasrechnung-senken-spaetsommer-check-…` | „Orientierungslinie": Postleitzahl, Jahresmenge, Vertrag entscheiden |

Weitere redaktionelle Auflösungen:

* **Gas-Paar vom 20.09.** (zwei Live-Artikel, gleicher Slug-Tag): geteilte
  Sicherheits- und Faustwert-Sätze neu gefasst („Brenner, Gasleitung und
  Abgasweg bleiben Sache einer Fachkraft"; 6 %-Faustregel als Satz vom
  Ergebnis her gedacht). **Keine Löschung, keine Umleitung** — beide Artikel
  haben eine eigene Aufgabe (Rechnung prüfen vs. Tarif-/Heizungs-Check), und
  jeder Auto-Draft eines etablierten Artikels wäre ein 404 für echte Leser.
* **Frugalismus-Paar (07.09. ↔ 11.09.):** Die geteilte Spar-Tabelle hat im
  jüngeren Artikel jetzt eine eigene Perspektive — **Monatssicht** statt
  Wochensicht, eigene Zeilenbezeichnungen, nachgerechnete Summe
  (110 € bis 205 €; `math_guard` grün). Auch die Wochenplan-Liste und der
  7-Tage-Einstieg sind entdoppelt.
* **Entwurf `2026-09-24-internet-dsl-update-…`:** Routermiete-Beispiel und
  Sparszenario auf einen eigenen Fall umgestellt (6,99 € / 9,99 € Mietrouter;
  Haushalt mit 39,99 €). So kann der Entwurf veröffentlicht werden, ohne den
  Live-Artikel vom 14.08. zu kannibalisieren — statt als Dauer-Entwurf im
  Bestand zu verfaulen.

### Erledigt: der Themen-Zwilling 50-30-20 (zusammengeführt)

`2026-09-25-die-50-30-20-regel-einfach-erklaert` **[Entwurf]** war ein zweiter
Anlauf auf dasselbe Hauptkeyword wie der Live-Artikel
`2026-09-11-50-30-20-regel-…` (26 geteilte Phrasen). Das war **kein
Formulierungsproblem**: Zwei Artikel auf ein Keyword kannibalisieren sich,
egal wie unterschiedlich sie geschrieben sind. Umschreiben hätte den Befund
nur versteckt.

Deshalb der redaktionelle Weg statt Textkosmetik — **zusammenführen und
zurückziehen**:

* **In den Live-Artikel übernommen** (neu formuliert, nicht kopiert):
  die Varianten-Tabelle „Vier Verteilungen, die im echten Leben vorkommen"
  (50-30-20 · 60-20-20 · 65-25-10 · 45-20-35) ersetzt das frühere
  Einzelbeispiel; die Gegenseite „für wen es schwieriger ist" (schwankendes
  Einkommen, hohe Wohnkosten, Schuldenabbau, Jahresposten) samt Auswegen;
  der konkrete Notgroschen-Zielwert **3 bis 6 Monatsausgaben** mit
  Reihenfolge und getrenntem Parken; der Sortier-Test für Pflicht- gegen
  Wunschkosten; die FAQ „Muss ich mich exakt an 50-30-20 halten?".
* **Bewusst nicht übernommen:** der „Mini-Plan für die nächsten 7 Tage"
  (hätte die Frugalismus-Artikel vom 07./11.09. kannibalisiert), das
  2.500-€-Rechenbeispiel (der Live-Artikel rechnet durchgängig mit 2.800 €)
  und der Jahreskosten-Block (im Live-Artikel bereits stärker vorhanden).
* **Entwurf zurückgezogen** über den vorgesehenen Repo-Pfad
  `publish_gate.discard_article()` — Content-Bundle **und** alle 15
  Cover-Varianten (jpg/webp/avif in allen Größen) entfernt, kein Artefakt
  bleibt liegen. Der Entwurf war nie veröffentlicht: keine URL im Pin-Plan,
  in `pins_upload.csv` oder im Newsletter-Stand, also kein 404-Risiko. Die
  Fassung bleibt über die Git-Historie jederzeit abrufbar.
* **Zwei interne Links umgehängt** (`2026-09-21-7-gewohnheiten-…`,
  `2026-09-23-5-einfache-frugalismus-tricks-…`) auf den Live-Artikel —
  `link_guard`: 0 Totstellen.
* Länge nach der Zusammenführung: **17.006 Zeichen** (Korridor für Posts:
  max. 18.000), keine neuen Mikro-Abschnitte, `quality_score`-Verdikt
  weiterhin `publish`.

---

## 5. Ebene 3 — Dauerhaftigkeit

| Leck | Vorher | Nachher |
|---|---|---|
| Prompt-Echo der KI-Auffrischung | ungeprüft in den Body geschrieben | `strip_prompt_echo()` **vor** Prüfung und Schreiben; `verify_update()` verwirft das Update fail-closed, falls eine unbekannte Variante durchkommt (wie bei verlorenen Affiliate-Links) |
| Prompt-Echo im News-Desk | `_strip_fences()` entfernte nur Code-Fences und H1 | zusätzlich `C7_SCAFFOLD_RE` — **dieselbe Marke**, importiert aus `content_audit.py`, kein zweites Muster |
| Bestand im Gerüst-Zustand | unentdeckt (8 Artikel, seit August) | `content_audit.py --fix` heilt C7 bei jedem Doktor-Lauf |
| Bestandsüberlappungen | nur im **Quartals**-Lauf sichtbar (bis zu 3 Monate) | `blog-health-daily.yml` führt `check_uniqueness.py` als **direkte tägliche Messung** aus |
| Offener Befund | Quartals-Issue blieb nach einer Heilung offen oder enthielt nur den alten Log | `uniqueness_issue_sync.py` aktualisiert genau einen Vorgang mit dem letzten Beleg und kommentiert/schließt ihn nach einem grünen Produktionslauf |
| Regel-Drift zwischen den Wachen | zwei Strip-Listen | `template_boilerplate.py` bleibt SSOT für `check_uniqueness` **und** `quality_score` |

### Nachschärfung: nicht nur dokumentiert, sondern tatsächlich verdrahtet

Die erste Fassung dieses Berichts hatte die Doktor-Kette als täglichen Takt
benannt. Die Workflow-Prüfung hat die Lücke aufgedeckt: `blog-health-daily.yml`
rief `blog_doctor.py` nicht auf und führte damit auch das Einzigartigkeits-Audit
nicht aus. Ein sauberer Grundsatz ohne ausführenden Schritt ist keine Wache.

Seit dieser Nachschärfung gilt deshalb ein expliziter Betriebsvertrag:

1. Der tägliche Gesundheitslauf misst nach seinen deterministischen Heilungen
   den ganzen Bestand. **Exit 1** (echte Live-Überlappung) wird nicht als
   `|| echo` verschluckt: Ein dedupliziertes Issue erhält den vollständigen
   Audit-Beleg. Die übrigen sicheren Tagesheilungen dürfen trotzdem committen.
2. **Exit ≥ 2** bedeutet einen defekten Audit-Selbsttest, nicht einen
   redaktionellen Fund. Der Lauf stoppt hart vor dem Commit und fällt in das
   bestehende Fehler-Alerting.
3. Nur `main` darf den Produktionsvorgang erzeugen, aktualisieren oder schließen
   (Workflow-Ref **und** Skript prüfen das). Ein manueller Lauf auf einem
   Arbeitsbranch kann folglich niemals einen echten Befund still schließen.
4. Der Quartalslauf nutzt dieselbe Skript-SSOT als zweite, unabhängige Messung
   direkt nach der KI-Aktualisierung. Kein zweiter Titel, kein zweiter
   Dedupe-Algorithmus, kein schleichender Lifecycle-Drift.
5. Die Befundklasse folgt jetzt `post_utils.build_state()` statt nur dem
   `draft:`-Regex: Zukunfts- und abgelaufene Posts sind nicht auslieferbar und
   erscheinen als Vorab-Aufgabe, nie als falscher Live-Bestandsschaden.

### Beweise (alle lokal grün)

```
python3 scripts/check_uniqueness.py --selftest       # 6 Twin-Fälle + Klassen + Anker-Pinne
python3 scripts/template_boilerplate.py              # Fazit/FAQ, Marketing, interne Anker, Idempotenz
python3 scripts/content_audit.py --selftest          # 13 Fälle (inkl. C7 + Falsch-Positiv-Gegenprobe)
python3 scripts/uniqueness_issue_sync.py --selftest  # Ref-Scope, Dedupe, Beleg, Schlusskommentar
python3 -m unittest discover -s scripts/tests        # Regressionen inkl. Workflow-Vertrag
python3 scripts/check_uniqueness.py                  # Bestand: Exit 0
```

Neue Regressionstests: `scripts/tests/test_check_uniqueness.py` (10 Fälle gegen
einen **synthetischen** Korpus, nie gegen den Live-Bestand — sonst hinge der
Test am Tagesgeschäft). Sie halten beide Richtungen fest: Navigation zählt
nicht, **und** echte Textdopplung wird weiterhin gefunden (Gegenprobe
`EchteDopplungBleibtSichtbarTests`).

Unverändert geprüft, ohne neue Funde gegenüber `main`: `math_guard`,
`table_guard`, `unit_guard`, `dash_guard`, `repetition_guard`, `lektor_guard`,
`hardcases_guard`, `stil_guard`, `listen_guard`, `heading_guard`,
`length_guard`.

---

## 6. Ergebnis

| Messgröße | Vorher (Issue #490) | Nachher |
|---|---|---|
| Interne Überlappungen gesamt | 30 | **9** (nur unkritische Standardformulierungen) |
| **Kritisch (live↔live)** | **10** (gemischt) | **0** |
| Nicht-Live-Paare (eigene Klasse) | – (in „kritisch" versteckt) | **0** (Entwurf/Zukunft/Ablauf vor Veröffentlichung sichtbar) |
| Pin-Konflikte | 0 | 0 |
| Same-Day-Zwillinge | 0 | 0 |
| Generator-Gerüst in Live-Artikeln | 17 Zeilen in 8 Artikeln | 0 |
| Exit-Code `check_uniqueness.py` | 1 | **0 — „✅ Audit bestanden"** |
| Prüftakt des Bestands | quartalsweise | **täglich, direkt im Gesundheitslauf** + Quartals-Gegenmessung |
| Befund-Lebenszyklus | offenes Quartals-Issue ohne Schlussbeweis | ein deduplizierter Vorgang, automatisch aktualisiert und nach Grün geschlossen |

Der Bestand ist sauber, die Wache misst, was sie messen soll, und die Quelle
des Gerüst-Lecks ist an beiden Enden geschlossen. Der letzte offene Punkt —
der Themen-Zwilling 50-30-20 — ist nicht umformuliert, sondern redaktionell
aufgelöst: eine starke Seite statt zweier halber. Alle zehn Paare aus
Issue #490 sind damit erledigt, und zwar jedes auf die Art, die zu seiner
Fehlerklasse passt.
