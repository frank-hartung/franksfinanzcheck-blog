# Report-Schritte brauchen einen lebenden Erzeuger

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Jeder Schritt hat einen lebenden Erzeuger (DAUERVORGABE, seit #806, 24.10.2026)

Der Report #806 führte unter „Datenlagen & Status“ zwei Zeilen mit
„Datenlage offen“ – aus Gate-Schritten, deren Messquelle es nicht (mehr) gab
(der Reichweiten-Dienst war am 19.10.2026 restlos entfernt). Ein Schritt ohne
Erzeuger ist ein Schritt, der **immer** „Datenlage offen“ meldet: er sieht nie,
wird nie grün und beendet die Meldung nie. Das ist die Report-Form von „Deckung
ohne Wirkung“.

- **Jeder Report-Schritt braucht einen benannten Erzeuger, dessen Skript
  existiert.** Schritte ohne Report sind namentliche Ausnahmen
  (`C42_OHNE_ERZEUGER` in `scripts/governance_contract.py`) – kein stiller
  Sammelplatz für Schritte, die nichts messen. Der Vertrag prüft die Schritte
  des Governance-Gates gegen ihre Signaturen: heute 12 Schritte, davon 10 mit
  Report – alle 10 mit existierendem Skript.
- **Ein Befund darf nicht seine eigene Spur erzeugen.** Die
  Fremdmessung-Sperre schwärzt den Namen des entfernten Dienstes in ihren
  Fundstellen (Pfad, Zeile und Klasse bleiben lesbar), und der Vertrags-Report
  `docs/GOVERNANCE-KONTRAKT.md` steht als **generierte Zone** in der Sperre:
  Er wird bei jedem Lauf vollständig neu geschrieben und stammt aus den
  gescannten Quellen. Ohne diese beiden Regeln trägt der Report die Spur, die
  er meldet – der Befund „Datenlage offen“ wäre eine Selbstverstärkung, die
  niemand mehr beenden kann.
- **Was das für den Report heißt:** Die beiden Zeilen aus dem Issue-Body waren
  ein **Snapshot vom 19.10.2026**. Sie beschreiben keinen heutigen Zustand –
  die Schritte, die sie erzeugt haben, gibt es nicht mehr. Wer einen Report
  liest, prüft den Fingerabdruck und den Laufdatum, nicht die Zeile von
  damals.
