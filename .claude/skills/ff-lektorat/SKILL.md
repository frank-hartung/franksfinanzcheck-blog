---
name: ff-lektorat
description: "Deutsches Copy-Editing für FranksFinanzcheck (YMYL-Finanzblog). Seven Sweeps auf Profi-Agentur-Niveau: Rechtschreibung, Grammatik, Zeichensetzung, Satzbau, Absatzstruktur, KI-Tell-Entfernung, menschlicher Ton, YMYL-Faktencheck. Nutzt die repo-eigene Offline-Engine-Kette (grammar_check LT1–LT4, sprachglatt DW1–DW9, hardcases_guard H1–H9, lektor_guard L1–L12, zeit_rechtschreibung, hemingway/readability) als automatisierten ersten Lektoratsdurchgang, gefolgt von menschlicher Endredaktion."
metadata:
  version: 3.0.0
  sprache: de-DE
  domain: finanzblog-ymyl
  stufe: highend-profi-agentur
---

# Lektorat (Deutsch) – FranksFinanzcheck Highend-Level

> **Ziel:** Jeder Blogartikel muss sprachlich auf dem Niveau einer professionellen Finanzredaktion (mind. ZEIT-Niveau) sein: perfekte Rechtschreibung, Grammatik, Zeichensetzung, saubere Abstände und Zeilenabstände im Layout, menschlicher und verständlicher Ton, keine KI-Muster. YMYL-Themen („Your Money Your Life“) erfordern zusätzlich Belegpflicht und Konsistenz.

## Wo die Details liegen

| Frage | Datei |
|---|---|
| Was prüft jeder der sieben Pässe, in welcher Reihenfolge? | `references/seven-sweeps.md` |
| Welche KI-Muster verraten einen Text – und wie entfernt man sie? | `references/ai-tells.md` |
| Was ist der finale QA-Durchgang vor der Auslieferung? | `references/checkliste.md` |
| Welche Engine läuft in welcher Reihenfolge, mit welchen Schwellen? | `references/werkzeugkette.md` |
| Wie prüft ein YMYL-Panel den Artikel (mehrere Rollen)? | `references/ymyl-panel.md` |
| Eingefrorene Testfälle des Lektorats | `evals/evals.md` |

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

## Die Seven Sweeps in einem Satz

Die sieben Pässe – Klarheit, Stimme & Ton, „So What?", Belegpflicht (YMYL),
Spezifität, Emotion, Zero Risk – laufen **in dieser Reihenfolge** und werden
nach jedem Pass zurückgeschleift. Der vollständige Katalog mit Prüfpunkten je
Pass, der AI-Tell-Check und der Quick-Pass für schnelle Reviews stehen wörtlich
in `references/seven-sweeps.md`; der YMYL-Panel-Ablauf in `references/ymyl-panel.md`.

Ein Durchgang gilt erst als fertig, wenn **alle sieben** gelaufen sind: ein
Text, der nur auf Sweep 1 und 2 geprüft wurde, ist nicht lektoriert, sondern
gelesen.

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
