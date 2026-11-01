# Faktenfrische, Belegkette und Zahlenheiler

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Faktenfrische: Recherche pro Artikel (seit 27.09.2026)

`scripts/faktenfrische.py` ist die **artikelgenaue** Schwester der breiten
Signalsammlung: Agent-Reach-Recherche + Claude-Fachprüfung (Puter-Brücke, ohne
Anthropic-API) für jeden bestehenden und jeden neuen Artikel.

- Zwei Takte: **Erstellung** (`--neu --apply` in `content-engine-v2.yml`,
  Phase 3) und **Bestand** (`faktenfrische.yml`, Di + Do). Fälligkeit nach
  Risikoklasse: saisonal 30, YMYL 45, Standard 90 Tage
  (SSOT `data/agent_reach/faktenfrische.yaml`).
- **Schreibrecht ist eng:** nur die Frontmatter-Felder `faktencheck` und
  `quellen`. Artikeltext **nie** automatisch, `lastmod` **nie** (Frische-
  Inflation). Fachliche Befunde → Report/Queue/Issue, Mensch entscheidet.
- **Anti-Halluzination (doppelter Deckel):** Eine Quelle darf nur in einen
  Artikel, wenn ihre URL wörtlich im Recherche-Dossier steht **und** ihre
  Domain auf der Allowlist liegt. Affiliate-Partner sind nicht belegfähig.
  Eingefroren in `--selftest` (ST3) – nicht aufweichen.
- Sichtbar wird das über `layouts/_partials/ff_quellen_box.html` („Quellen &
  Faktenstand“) und als `citation`/`sdDatePublished` im Article-JSON-LD.
  **Eine Quelle, zwei Ausspielwege** – nie einen der beiden separat pflegen.
- Runbook: `docs/ANLEITUNG-FAKTENFRISCHE.md`.

### Der Geburtspunkt fährt denselben Heiler wie die Kette (Zahlen, seit #821, 25.10.2026)

Das harte RS5-Gate lehnt jeden Satz ab, der eine Zahl mit Einheit ohne
Quellenlink im selben Satz und ohne Modell-Kennzeichnung nennt. Am 25.10.2026
starben daran **vier frische Themen bei der Geburt** (16, 20 und 8 Sätze) –
drei Versuche je Thema, alle am selben Punkt, danach Cooldown. Verbrauchtes
Kontingent ohne einen Kandidaten.

Die Wiederholung war blind (Lehre #612), der vorhandene Heiler auch: Er kannte
die **Regel**, nicht die **Sätze**.

- `redaktions_standard.zahlen_beleg_heiler` repariert ausschließlich die
  abgelehnten Sätze, wörtlich im Prompt. Zwei erlaubte Wege: ohne Zahl
  formulieren oder die Zahl im selben Satz als Beispiel-/Modellrechnung mit
  genannter Annahme kennzeichnen. „ca./rund/etwa“ bleibt kein Beleg.
- Fail-closed mit Wirkungsprobe: Text nicht geschrumpft, Linkziele
  byte-identisch, H2-Anzahl gleich, RS5-Zahl **strikt gesunken**, kein neuer
  RS1–RS6-Befund. Ohne Befund kein Modellaufruf.
- `engine_generate.try_generate` ruft ihn **einmal** je Generierung und nur bei
  `_nur_zahlenbefund` (ausschließlich RS5). Längen-/Strukturdefekte brauchen
  eine neue Generierung, keine Satz-OP.
- Das Gate bleibt unverändert hart – der Text wird besser, nicht die Messung
  weicher. Tests: `scripts/tests/test_zahlen_heiler.py` (in
  `npm run test:reserve`). Vorgangsbericht:
  `WARTUNG-INHALTSQUALITAET-WF-D4E0-821-DAUERHEILUNG-PREMIUM-2026-10-25.md`.

### Ein Befund, der sich selbst falsch zählt (RS5-Messfehler, seit #821, 25.10.2026)

Am 25.10.2026 meldete der Reserve-Blocker `RS5: 9 Zahlenbehauptung(en) ohne
Satzbeleg` – gemessen waren es **5**. Vier „Funde" waren Artefakte des Zählers,
keine Aussagen des Textes: zwei **Kalenderjahre** („im Jahr 2026", „kein
Spartrend für 2026"), eine repo-interne **Issue-Nummer** (`#763`) und ein
Satz-Fragment („Oktober 2026**."), das ein **Fett-Marker** zerschnitten hatte.

Dieselbe Lehre wie bei der Diagnose (Abschnitt „Der Vorrat endet nicht"):
Nicht nur der Lauf kann lügen, auch die **Messung**. Wer einem zu hohen Befund
glaubt, schickt die Redaktion in die falsche Baustelle – hier: in eine
Zahlen-Korrektur an Sätzen, die gar keine Zahl enthalten.

- `redaktions_standard._reserve_numeric_claim_findings` entfernt Fett-/Kursiv-
  Marker **vor** der Satztrennung, zählt `#<Zahl>` nicht als Betrag und
  bewertet einen Satz erst, wenn nach dem Entfernen der **Jahreszahlen**
  (1900–2099) noch eine Zahl mit Einheit übrig bleibt.
- Die Schutzrichtung bleibt hart: „Reichen 120 € nicht, ändere den Plan."
  und „Drei Monate reichen zum Prüfen nicht." bleiben Befunde. Der Kandidat
  bleibt blockiert – mit der Wahrheit (5 statt 9).
- Verriegelt in `scripts/tests/test_zahlen_prompt_vertrag.py`
  (`test_kalenderjahr_ist_keine_zahlenbehauptung`,
  `test_repo_referenz_ist_keine_zahlenbehauptung`,
  `test_fettmarker_zerschneidet_keinen_satz`,
  `test_echte_unbelegte_zahl_bleibt_rot`).
