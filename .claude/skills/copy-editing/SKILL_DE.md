---
name: copy-editing-de
description: "Deutsches Copy-Editing für FranksFinanzcheck (YMYL-Finanzblog). Seven Sweeps auf Profi-Agentur-Niveau: Rechtschreibung, Grammatik, Zeichensetzung, Satzbau, Absatzstruktur, KI-Tell-Entfernung, menschlicher Ton, YMYL-Faktencheck. Nutzt die repo-eigene Offline-Engine-Kette (grammar_check LT1–LT4, sprachglatt DW1–DW9, hardcases_guard H1–H9, lektor_guard L1–L12, zeit_rechtschreibung, hemingway/readability) als automatisierten ersten Lektoratsdurchgang, gefolgt von menschlicher Endredaktion."
metadata:
  version: 3.0.0
  sprache: de-DE
  domain: finanzblog-ymyl
  stufe: highend-profi-agentur
---

# Copy Editing (Deutsch) – FranksFinanzcheck Highend-Level

> **Ziel:** Jeder Blogartikel muss sprachlich auf dem Niveau einer professionellen Finanzredaktion (mind. ZEIT-Niveau) sein: perfekte Rechtschreibung, Grammatik, Zeichensetzung, saubere Abstände und Zeilenabstände im Layout, menschlicher und verständlicher Ton, keine KI-Muster. YMYL-Themen („Your Money Your Life“) erfordern zusätzlich Belegpflicht und Konsistenz.

## Wann diese Skill gilt

- Ein bestehender Markdown-Artikel soll überarbeitet, poliert oder „menschlicher“ klingen.
- Vor der Veröffentlichung (Endredaktion) als verpflichtender Qualitätsdurchgang.
- Bei Wiederaufnahme älterer Artikel (Content Refresh / Dauerheilung).
- Nicht für völlig neue Texte – dafür gibt es die `copywriting`-Skill.

## Das Repo bereits installiert (SSOT – Single Source of Truth)

Diese Skill ersetzt keine bestehende Engine, sondern **orchestriert** sie in einem festen, wiederholbaren Prozess:

| Ebene | Skript | Was es prüft/heilt |
|---|---|---|
| Rechtschreibung | `scripts/zeit_rechtschreibung.py` | LanguageTool-kompatibel, ZEIT-Niveau, Premium/offline, Auto-Fix-Allowlist |
| Grammatik | `scripts/grammar_check.py` | LT1–LT4 (Partikel, Kollokationen, Kontext-Fälle, Fehlschreib-Kanon) |
| Glättung (Stil) | `scripts/sprachglatt.py` | DW1–DW9 (Bandagen raus, Nominalstil abbauen, Passiv reduzieren) + V1-Vorschläge |
| Fest-Fehler | `scripts/hardcases_guard.py` | H1–H9 (einzigste, dasselbe, darauf hin, seid/seit, Pleonasmen, ß/ss) |
| Verlags-Lektorat | `scripts/lektor_guard.py` | L1–L12 (Wortduplikate, Füllphrasen, Personenkonsistenz „du“, Ausrufezeichen, Echo-Wörter, Stale-Jahre, Nominalstil, Weichmacher, Satzanfangs-Echo, Zahlenschreibweise, Werbe-Intensiv, Long-Satz) |
| Lesbarkeit | `scripts/readability_check.py` / `hemingway_check.py` | Flesch-Amstad, Ø Satzlänge, lange Wörter, Schachtelsätze, Absätze, Passiv |

> **Vertrag:** Keine dieser Engines schreibt eigenmächtig Titel, Frontmatter-Anker, Shortcodes, URLs, Code-Blöcke oder Link-Texte um. Schutzzonen sind längentreu maskiert. Jeder Schreibvorgang läuft über `sprachkern.write_verified` (Link-/Shortcode-/Überschriften-Wächter) + Selbsttest vor jedem Lauf. Abweichung = Exit 2, keine Datei wird angefasst.

---

## Die Seven Sweeps (deutsch, YMYL-adaptiert)

Jeder Artikel durchläuft **sieben aufeinanderfolgende Lektorats-Pässe**. Nach jedem Pass wird zurückgeschleift, ob frühere Pässe nicht beschädigt wurden.

### Sweep 1: Klarheit (Verständlichkeit)

**Frage:** Kann der Leser sofort verstehen, was gesagt wird?

Prüfen:
- Verwirrende Satzstrukturen, Schachtelsätze (> 25 Wörter → Report)
- Unklare Pronomen-Bezüge
- Fachjargon ohne Erklärung (ETF, Dispo, Schufa, Girocard …)
- Ambigue Aussagen, versteckte Hauptaussage

**Prozess:** Erst lesen, markieren, dann konkret editieren. Einen Hauptgedanken pro Abschnitt („Rule of One“). „Du“-Regel: Der Text spricht den Leser direkt an.

> Highend-Regel: Bei Finanzartikeln (YMYL) muss jede Handlungsschritt-Anleitung so eindeutig sein, dass ein Laie sie fehlerfrei umsetzen kann.

### Sweep 2: Stimme & Ton (Konsistenz)

**Frage:** Klingt der Text durchgängig nach einer Person / einer Marke?

Prüfen:
- Wechsel zwischen förmlich und locker („Sie“ vs. „du“ – Hausduktus ist „du“)
- Inkonsistente Markenpersönlichkeit
- Stimmungssprünge (witzig, dann corporate, dann warnend)

**Prozess:** Laut lesen, Tonbrüche markieren, glätten. Persönlichkeit erhalten, Klarheit verbessern.

### Sweep 3: „So What?“ (Relevanz)

**Frage:** Beantwortet jede Aussage die Frage „Warum sollte mir das etwas bedeuten?“

Prüfen:
- Features ohne Nutzen („Unsere Plattform nutzt KI-gestützte Analysen“ → „So was?: Sie sehen Einsparpotenziale, die Ihnen manuell entgehen – und entscheiden in halber Zeit besser.“)
- Claims ohne Konsequenz
- Aussagen, die nicht mit dem Leben des Lesers verknüpft sind

### Sweep 4: „Beweis es!“ (Belegpflicht, YMYL-kritisch)

**Frage:** Ist jede Behauptung belegt?

Besonders bei Finanzthemen (YMYL):
- „Sparen Sie X Euro“ → Quelle, Rechenbeispiel, Annahmen nennen
- „Die beste Versicherung“ → Laut wem? Nach welchen Kriterien?
- „Kunden lieben uns“ → Konkrete Testimonials mit Namen/Details oder streichen
- Superlative ohne Beleg → entschärfen oder belegen

**Prozess:** Jeden Claim identifizieren, Nachweis danebenlegen oder Aussage entschärfen.

### Sweep 5: Spezifität (Konkretheit)

**Frage:** Ist der Text konkret genug, um überzeugend zu sein?

| Vage | Spezifisch (Finanzblog-Beispiel) |
|---|---|
| Sparen Sie Zeit | Sparen Sie 4 Stunden pro Woche |
| Viele Kunden | 2.847 Leser |
| Schnelle Ergebnisse | Ergebnis in 14 Tagen |
| Guter Support | Antwort innerhalb von 2 Stunden |
| Hohe Rendite | 4–6 % p. a. (beispielhaft, mit Risikohinweis) |

Adjektive, die die Arbeit von Substantiven machen, streichen. Runden, erfühlt wirkenden Zahlen vermeiden.

### Sweep 6: Emotion (Authentizität)

**Frage:** Fühlt der Leser etwas – oder konsumiert er nur Information?

Prüfen:
- Flache, rein informative Sprache
- Schmerzpunkte genannt, aber nicht gespürt (Altersarmut, Dispo, Versicherungslücke)
- Wünsche genannt, aber nicht geweckt

Techniken: „Vorher“-Zustand vivid schildern, Mikro-Geschichten, geteilte Erfahrungen, reflektierende Fragen. Emotion dient der Botschaft – keine Manipulation.

### Sweep 7: Zero Risk (Handlungshemmnisse entfernen)

**Frage:** Gibt es noch Gründe, nicht zu handeln?

Prüfen (besonders bei CTAs, Produktvergleichen, Affiliate-Links):
- Offene Einwände („Ist das sicher?“, „Was kostet das wirklich?“), die unbeantwortet bleiben
- Fehlende Trust-Signale, keine klaren nächsten Schritte
- Versteckte Kosten, unklare Kündigungsbedingungen
- Keine Risikoumkehr (Geld-zurück, Kündigung jederzeit, keine Kreditkarte nötig)

**Prozess:** Fokus auf CTA-nahen Abschnitten. Jeden Zögern-Grund auflisten und im Text adressieren.

---

## AI-Tell-Check (Deutsch) – verpflichtend vor jeder Lieferung

Ein Leser, der ein KI-Muster erkennt, bezweifelt die Behauptungen darum. Der Satzbau verrät KI mehr als jedes Wort.

| Muster | Beispiel | Korrektur |
|---|---|---|
| Kontrast-Offenbarung | „Nicht X, sondern Y.“ | Y direkt nennen, mit Begründung |
| Verneinungs-Liste | „Kein Beratungstermin, keine Unterlagen, kein Warten.“ | Sagen, was geschieht; eine absence darf bleiben („Keine Kreditkarte nötig“) |
| Ausschweifendes Komma-Ende | „… die Daten, die Sie schon haben, ohne Exporte, ohne Tabellen.“ | Satz beim Anspruch beenden, Nutzen eigenen Satz geben |
| Selbstbeantwortete Frage | „Das Ergebnis? 3x schneller.“ | Frage löschen, Antwort behalten |
| Doppelpunkt-Offenbarung | „Das Beste daran: Es lernt.“ | Normaler Satz |
| Stock-Floskeln | „In der heutigen schnelllebigen Welt“, „Ob Sie X oder Y“, „Hier ist das Ding“, „Lebewohl, sagen Sie“ | Streichen, mit Leser-Problem oder Fakt beginnen |
| Em-Dash-Inflation | Headlines, Subheads, CTAs (mehr als 1–2 pro Seite) | Punkt, Komma, Doppelpunkt |

**Cap-Regeln:** Maximal ein Fragment und eine Dreier-Liste pro Abschnitt. `nahtlos`, `robust`, `mächtig`, `straffen`, `befähigen` sind Platzhalter – durch Fakten ersetzen. Zwei solcher Platzhalter in einem Absatz = Absatz umschreiben.

**Unangetastet lassen:** FAQ-Fragen, ein einzelnes „Keine Kreditkarte“ am CTA, eine echte Dreier-Liste, ein Kommanebensatz, der eine neue Tatsache liefert.

---

## YMYL-Expert-Panel (Finanzartikel)

Für hochrelevante Finanzartikel (Versicherungen, Kredite, Anlagen, Steuern, Konten) nach den Seven Sweeps:

1. **3–5 Personas zusammenstellen:**
   - Finanzredakteur (Klarheit, CTA, Nutzenhierarchie)
   - UX-Writer (Scannability, kognitive Last, Nutzerführung)
   - Ziel-Kunden-Persona (spricht mich das an? vertraue ich?)
   - Compliance-/Hinweisgeber (Risikohinweise, Warnhinweise, Impressumspflichten, Affiliate-Offenlegung)
   - SEO-Spezialist (Keyword-Abdeckung, Suchintention)

2. **Jede Persona bewertet 1–10** in ihrem Fachgebiet + konkrete Kritik.
3. **Überarbeiten**, beginnend bei den niedrigsten Scores.
4. **Re-Score:** Alle Personas ≥ 7, Durchschnitt ≥ 8.

> Optional für Blogposts, Social, interne Docs. **Pflicht** für Cornerstone-Artikel, Produktvergleiche, YMYL-Hauptartikel.

---

## Quick-Pass (für schnellere Reviews, wenn kein Full-Sweep nötig)

### Wortelevel
**Streichen:** sehr, wirklich, extrem, unglaublich (schwache Intensierer); einfach, eigentlich, grundsätzlich (Füllwörter); um … zu (zu); das (oft unnötig); Dinge, Zeug (vage).

**Ersetzen:**
| Schwach | Stark |
|---|---|
| nutzen | verwenden / nutzen (konkret: was?) |
| implementieren | einrichten |
| nutzen (Leverage) | verwenden |
| erleichtern | helfen |

**Vorsicht bei:** Adverbien (meist unnötig), Passiv (aktiv umbauen), Nominalstil („eine Entscheidung treffen“ → „entscheiden“).

### Satzebene
- Eine Idee pro Satz
- Satzlänge variieren (kurz und lang mischen)
- Wichtige Information voranstellen
- Max. 3 Konjunktionen pro Satz
- Max. 25 Wörter (in der Regel)

### Absatzebene
- Ein Thema pro Absatz
- Kurze Absätze (2–4 Sätze für Web)
- Starke Einleitungssätze
- Logischer Fluss zwischen Absätzen
- Weißraum für Scannability (Zeilenabstand/Abstände sind Layout – siehe `assets/css/`, nicht Textbearbeitung)

---

## Copy-Editing-Checkliste (Final QA)

Vor jeder Auslieferung:

- [ ] Ziel des Textes verstanden (Awareness, Conversion, Retention)
- [ ] Zielgruppe und gewünschte Handlung bekannt
- [ ] Einmal gelesen, ohne zu editieren
- [ ] Sweep 1–7 alle durchlaufen und zurückgeschleift
- [ ] AI-Tell-Check bestanden
- [ ] YMYL-Belege gesetzt (falls zutreffend)
- [ ] Grammatik-Engine (`grammar_check`, `hardcases_guard`, `zeit_rechtschreibung`) läuft sauber (Exit 0)
- [ ] Glättungs-Engine (`sprachglatt`, `lektor_guard`) keine offenen kritischen Funde
- [ ] Lesbarkeit (`hemingway` / `readability`): Flesch-Amstad ≥ 60, Ø Satz ≤ 16 Wörter
- [ ] Kernbotschaft durch alle Edits erhalten
- [ ] Menschliche Endredaktion hat freigegeben (`endredaktion`)

---

## Verwandte Skills

- `copywriting`: Neue Texte von Grund auf schreiben (danach hier: `copy-editing` zum Polieren).
- `cro`: Strukturseitige Optimierung jenseits des Texts.
- `impeccable`: UI-/Design-Polish (Layout, Zeilenabstand, Abstände im CSS).
- `content-strategy`: Themenplanung und Refresh-Cadence.

---

## Aufgabe-spezifische Fragen

1. Was ist das Ziel dieses Artikels? (Awareness, Conversion, Retention)
2. Welche Handlung sollen Leser ausführen?
3. Gibt es spezielle Bedenken oder bekannte Probleme?
4. Welche Belege/Quellen stehen zur Verfügung? (besonders YMYL)
5. Neuer Text oder Refresh von bestehendem Inhalt?
