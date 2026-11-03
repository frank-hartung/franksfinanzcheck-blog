# Faktenfrische #996 – Dauerheilung auf Highend-Level

Stand: 3. November 2026. Auftrag: „Bitte dauerhaft auf Highend-Level einer
Profi-Agentur beheben.“ Umsetzung auf dem Arbeitsbranch
`arena/609a4bae-franksfinanzcheck-blog`, Freigabe über Pull Request.
**Dieser Vorgang schließt Issue #996 nicht automatisch** und enthält
bewusst **keine** „Closes #996“-Klausel: Die 16 Ledger-Befunde bleiben
bis zur dokumentierten menschlichen, fassungsgebundenen Entscheidung des
Inhabers offen (Wahl des Auftraggebers vom 03.11.2026:
„unterschriftsreif vorbereiten“). Die unterschriftsreife Akte steht in
Abschnitt 6 – ein Eintrag, ein Befehl, ein erneuter Gate-Lauf trennen den
Vorgang dann vom Abschluss. Eine Freigabe, ein Prüfsiegel oder eine
menschliche Fachentscheidung wurde nicht vorgegeben.

## 1. Ausgangslage: geheilt im Text, rot in der Regression

PR #1017 (02.11.2026, gemergt) hatte die 16 Befunde in den vier
Gasartikeln redaktionell bearbeitet; `FAKTENFRISCHE-996-2026-11-02.md`
dokumentiert das und benennt ehrlich die offene Signatur. Drei Befunde
blieben danach bestehen:

| # | Restbefund | Nachweis |
|---|---|---|
| R1 | **Regression auf `main` rot.** `test_faktenfrische_996` schlug mit 2 Fehlern fehl: Die `pin_description` der Artikel vom 14.08. und 24.08. warb weiter mit „beste Zeit für den Gaswechsel“ – exakt die saisonale Behauptungsklasse von Befund `db8a69f08dc0020adebd`. | Lokal reproduziert am 03.11.2026: `Ran 4 tests … FAILED (failures=2)`. Der Deploy-Gate führt diesen Test aus (`.github/workflows/deploy.yml`), jeder Deploy wäre an dieser Stelle rot. |
| R2 | **Werbefläche außerhalb der Fassung.** `pin_title`/`pin_description` gehörten weder zum Prüfauftrag der Fachprüfung noch zum Fassungs-Hash (`pruef_hash`). Ein Pin-Rückfall änderte die Fassung nicht – eine fassungsgebundene Entscheidung hätte ihn nicht gesehen. Genau so überlebte R1. | `scripts/faktenfrische_befund_ledger.py:pruef_hash` (alt: nur title/description/kurzantwort/quellen/body); Fachprüfungs-Prompt ohne Pin-Felder. |
| R3 | **Zwei Rückfälle derselben Klassen im Bestand.** Pin vom 10.08.: „sparst bis zu 650 Euro bei den Heizkosten“ (unbelegtes Euro-Versprechen, Klasse `124ff2c3…`). Pin vom 12.08.: „Vor der Heizsaison ziehen viele Anbieter die Preise an … Preissprünge einfach aussitzen“ (Preis-Trend + Wirkversprechen, Klasse `db8a69f0…`). Im Text des 10.08. zusätzlich: „Ein Bonus für Neukunden drückt den Preis im ersten Jahr stark“ – die in #911 (B2) bereits verbotene Behauptungsform. Plus: abgebrochene Meta-Description des 10.08. („…und welche.“). | Fundstellen in den vier `index.md`, siehe Diff dieses PR. |

## 2. Live-Quellenprüfung am 03.11.2026

Alle drei Belegseiten wurden nur lesend abgerufen und mit den Artikeln
abgeglichen (keine neue Marktzahle ohne Fundstelle übernommen):

| Quelle | Trägt heute | Artikel-Folge |
|---|---|---|
| BNetzA „Preise und Abschläge“ | Monatsfrist für Haushaltskunden; Information über Grund, Voraussetzungen, Umfang + Sonderkündigungsrecht; Vertrag endet am Vortag; Ausnahme separierte Preisanpassungsklausel (hoheitlich); **kein** Sonderkündigungsrecht bei reiner Umsatzsteuer-Weitergabe (Erhöhung **und** Senkung); strengere Anforderungen in der Grundversorgung; keine staatliche Preisgenehmigung | Formulierungen in allen vier Artikeln entsprechen der Seite; `quellen` der Artikel vom 10.08. und 24.08. um genau diese Seite ergänzt (Belegkette zum Link im Text). |
| BNetzA „Arten der Energiebelieferung“ | Fall 2: eigene Kündigung/Vertragsende → Grundversorgung; Fall 5: kurze Wechselverzögerung (wenige Tage) → Ersatzversorgung; Fall 4: Insolvenz → Ersatzversorgung, drei Monate ohne Grundversorgungs-Anspruch | Fallbezogene Unterscheidung in 10.08./14.08. bestätigt; keine pauschale Versorgungs-Garantie. |
| Verbraucherzentrale „Heizung: 10 Tipps“ (Stand 24.09.2026) | „Schon ein Grad weniger Raumtemperatur reduziert den Verbrauch um 6 Prozent“; „Wenn Sie die Heizungsanlage richtig einstellen können Sie 10 bis 15 Prozent Energie einsparen“ | 6-%-Faustwert am Satz verlinkt (14.08., 24.08.); 10–15 % ausdrücklich nur Anlageneinstellung/Energie, „nicht pauschal deine gesamte Gasrechnung“ (14.08.). Der Maschinen-Stempel `faktencheck: 2026-11-01` bleibt unverändert – er ist kein Handarbeits-Datum. |

Alle Rechenwege der vier Artikel wurden nachgerechnet und stimmen:
18.000 × 0,4/0,8 ct = 72–144 €; 18.000 × 11,5 ct + 195 € = 2.265,00 €,
÷ 12 = 188,75 €; 18.000 × 0,118 € = 2.124 € + 180 € = 2.304 €;
20.000 × 1,5 ct = 300 €; 20.000 × 0,7 ct = 140 €;
10,8/11,3 ct-Tabelle = 2.340/2.440 €, 12.000 × 1,5 ct = 180 €;
18.000 × 1,5 ct = 270 €; 20.000 × 2 ct = 400 €. Wo die Artikel von
Annahmen sprechen, sind sie als Modell/fiktiv gekennzeichnet.

## 3. Heilung im Text (vier Artikel)

- **Pins neutralisiert** (alle vier): keine Jahreszeit als „beste Zeit“,
  kein Preis-Trend, kein Euro-Sparversprechen, kein „Aussitzen“ von
  Preissprüngen. Die Pins beschreiben jetzt den Prüfpfad des Artikels
  (Umfang/Laufzeit/Gesamtpreis, Bonus ausblenden, Klausel und
  Sonderkündigungsrecht abgleichen). `*Werbung`-Kennzeichnung bleibt.
- **Bonus-Satz (10.08.)** an Höhe und Bedingungen gebunden statt
  „drückt stark“ (Klasse #911-B2).
- **Meta-Description (10.08.)** vervollständigt (157 Zeichen, Korridor
  70–165 wird jetzt von der Regression geprüft).
- **`lastmod: 2026-11-03`** für die wesentlichen Textänderungen;
  `faktencheck` bleibt Maschinenstand 2026-11-01 (keine Frische-Inflation).

## 4. Dauerhafte Absicherung (die eigentliche Heilung)

1. **Schließakte nach #911-Vertrag:** `data/faktenfrische_befunde_996.yaml`
   mit allen 16 Befunden – `ledger_id` + Queue-Fassung, Entscheidung,
   Status `behoben`, ehrlichem Feld `ledger_signatur: ausstehend`,
   Beleg (Allowlist **und** Artikelquelle, `null` nur bei Streichung),
   Bedeutungsankern, `verboten_behauptend` und Restrisiko je Befund.
2. **Regression von 4 auf 12 Tests** (`npm run test:faktenfrische:996`,
   weiterhin in `test:faktenfrische` und im Deploy-Gate):
   Register-Vertrag (genau die 16 Queue-Befunde, Fassungsbindung,
   Anker tragen, Verbotenes bleibt draußen), Pin-Neutralität,
   Bonus-Formulierung, Metadaten-Korridor, Prompt-Vertrag und
   Hash-Vertrag. Vorher rote Fälle sind jetzt Teil der Suite.
3. **Prüfauftrag Regel 11** im `SYSTEM_PROMPT` von
   `scripts/faktenfrische.py`: Übersichtsseite ≠ Beleg für konkrete
   Werte; Referenzpreise mit Absender ohne Fundstelle; saisonale
   Prognosen; Verbrauch nur als Annahme; Heiz-Faustwerte mit Quelle und
   Geltungsbereich; Grund-/Ersatzversorgung fallbezogen; Garantie nur
   vertraglich, Aufpreis nie „üblich“; **Werbeflächen sind
   Aussageflächen.**
4. **Werbeflächen sind jetzt Prüfgegenstand und Fassung:**
   Die Fachprüfung erhält `PIN-TITEL`/`PIN-BESCHREIBUNG`, und
   `pruef_hash` bindet beide Felder ein (Ledger-Doku im Code). Ältere
   Queue-/Dossier-Hashes bleiben gespeicherte Historie; der nächste
   Lauf bindet die Fassungen mit dem erweiterten Material neu – offene
   Altbefunde gehen dabei nicht verloren (Ledger dedupliziert, schließt
   nie still).
5. **Betriebsdoku:** `scripts/FAKTENFRISCHE.md` führt #996 als zweites
   Register-Beispiel und hält den Grundsatz fest: redaktionelle Heilung
   ist keine Ledger-Signatur.

**Sabotage-Probe (03.11.2026):** Drei wiederinjizierte Rückfälle
(Pin „beste Zeit … mehrere hundert Euro Ersparnis“, „BDEW-Durchschnitt
11,93“ im Text, entfernter 6-%-Anker) machten **9 Tests rot**. Nach
Rückstellung aus dem Backup: 12/12 grün, Arbeitsbaum exakt im
geheilten Stand.

## 5. Nachweise

- `python -m unittest scripts.tests.test_faktenfrische_996`: **12/12 OK**
  (vorher auf `main`: 2 Fehler).
- Faktenfrische-Suite gesamt: Selbsttests 29/29, Ledger-Selbsttest,
  Kapazität 36/36; `test_faktenfrische_kapazitaet`,
  `_befund_ledger`, `_robustheit`, `_911`, `_763`, `_823`:
  **114 Tests OK** (1 Skip: historisches #823-Dossier).
- `git diff --check`: wird im PR-Lauf mitgeprüft.

## 6. Unterschriftsreife Schließakte (der eine offene Schritt)

Warum hier Schluss ist: `data/faktenfrische_entscheidungen.yaml` trägt
den Vertrag „Nie automatisch ergänzen“, und die Anleitung hält fest,
dass eine Maschine die Entscheidung nicht stellvertretend erfinden
darf. Der Auftraggeber hat am 03.11.2026 „unterschriftsreif
vorbereiten“ gewählt. **Zu entscheiden ist je Befund an der Fassung,
an der er gesehen wurde** (Queue-Hash) – nicht an der heutigen Datei.
Deshalb stehen hier die Queue-Hashes; `--fassung` (heutige Datei)
läge daneben falsch. Zur Einordnung die heutigen Datei-Hashes (neues
Hash-Material inkl. Pins): 10.08. `a5a72b18…27d8d3`, 12.08. `76f69a8b…c3a3`,
14.08. `cc4616f2…7f31`, 24.08. `5cfa88ca…53f`.

Nach eigener Sichtung der korrigierten Artikel diesen Block – mit
echtem Namen und Datum – in `data/faktenfrische_entscheidungen.yaml`
unter `entscheidungen:` eintragen (Begründungen je Befund stehen im
Register `data/faktenfrische_befunde_996.yaml`):

```yaml
  - slug: "2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas"
    befund_id: "7bdec96c0329769bebe6"
    fassung_sha256: "98a213340f9575bbf5467cc47ce3fe215a6b35fdff87c861ec458c2dd958076b"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N01>"
  - slug: "2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas"
    befund_id: "a56734aa032e0ed9e0c4"
    fassung_sha256: "98a213340f9575bbf5467cc47ce3fe215a6b35fdff87c861ec458c2dd958076b"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N02>"
  - slug: "2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas"
    befund_id: "124ff2c3cd3917c274aa"
    fassung_sha256: "98a213340f9575bbf5467cc47ce3fe215a6b35fdff87c861ec458c2dd958076b"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N03>"
  - slug: "2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026"
    befund_id: "c583efe1ce02df3ca2d7"
    fassung_sha256: "17a0305ffcc14a51833aa7d16cfcef85c7d0b8ecdf1f03dd67df176eede114af"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N04>"
  - slug: "2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026"
    befund_id: "30caa57be394afb62947"
    fassung_sha256: "17a0305ffcc14a51833aa7d16cfcef85c7d0b8ecdf1f03dd67df176eede114af"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N05>"
  - slug: "2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026"
    befund_id: "32a3ea879f2cf126b3a7"
    fassung_sha256: "17a0305ffcc14a51833aa7d16cfcef85c7d0b8ecdf1f03dd67df176eede114af"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N06>"
  - slug: "2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden"
    befund_id: "db8a69f08dc0020adebd"
    fassung_sha256: "8735136fa5f58b5ea7c4db767e0cc5c460e24368611498e5a6801a9a48fcd316"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N07>"
  - slug: "2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden"
    befund_id: "e834f4702e87194affe7"
    fassung_sha256: "8735136fa5f58b5ea7c4db767e0cc5c460e24368611498e5a6801a9a48fcd316"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N08>"
  - slug: "2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden"
    befund_id: "9fbacd9942c2dfa1447f"
    fassung_sha256: "8735136fa5f58b5ea7c4db767e0cc5c460e24368611498e5a6801a9a48fcd316"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N09>"
  - slug: "2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden"
    befund_id: "da30cbb5fbc8c801daf0"
    fassung_sha256: "8735136fa5f58b5ea7c4db767e0cc5c460e24368611498e5a6801a9a48fcd316"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N10>"
  - slug: "2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden"
    befund_id: "437b809ffbf41e5af434"
    fassung_sha256: "8735136fa5f58b5ea7c4db767e0cc5c460e24368611498e5a6801a9a48fcd316"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N11>"
  - slug: "2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen"
    befund_id: "252413dcc16cea146beb"
    fassung_sha256: "d672bc8e4ec87074bdad74b3013c4a007b5d097501cbe52d3b362956e2edea51"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N12>"
  - slug: "2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen"
    befund_id: "ab4d084fd367c8e4d518"
    fassung_sha256: "d672bc8e4ec87074bdad74b3013c4a007b5d097501cbe52d3b362956e2edea51"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N13>"
  - slug: "2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen"
    befund_id: "d215addd22dea72c44df"
    fassung_sha256: "d672bc8e4ec87074bdad74b3013c4a007b5d097501cbe52d3b362956e2edea51"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N14>"
  - slug: "2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen"
    befund_id: "9326152f4d788cff56bd"
    fassung_sha256: "d672bc8e4ec87074bdad74b3013c4a007b5d097501cbe52d3b362956e2edea51"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N15>"
  - slug: "2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen"
    befund_id: "48a0a962046c8315270e"
    fassung_sha256: "d672bc8e4ec87074bdad74b3013c4a007b5d097501cbe52d3b362956e2edea51"
    entschieden_von: "<Name des Inhabers>"
    begruendung: "<eigene Begründung, s. Register 996-N16>"
```

Danach messen, nicht behaupten:

```bash
python3 scripts/faktenfrische_befund_ledger.py   # 16 Befunde dieser Slugs weg, 41 Altbefunde bleiben
npm run test:faktenfrische
```

Erst wenn Publish-Gate/Scorecard für diese vier Slugs F4-frei messen und
der nächste grüne Faktenfrische-Lauf die neuen Fassungen gebunden hat,
ist #996 über seinen eigenen Schließpfad zu schließen. Die übrigen
41 offenen Befunde des Issues (andere Artikel) sind nicht Gegenstand
dieser Heilung und bleiben offen.

## 7. Ehrliche Grenzen

- **Kein Hugo-Build/Browsernachweis in dieser Umgebung** (kein Hugo,
  Netzsperre); Markdown, Frontmatter, Links und Gates sind geprüft,
  nicht das gerenderte HTML.
- **Keine neue Fachprüfung durch die Maschine:** Der nächste echte
  Faktenfrische-Lauf (Netz + Schlüssel) muss die neuen Fassungen
  binden; erst dann ist sichtbar, ob die Fachprüfung neue Befunde sieht.
- **Die Regression ist Rückfallschutz, kein Wahrheitsbeweis.** Sie
  fängt die 16 Klassen und ihre Formulierungen; eine neu formulierte
  falsche Marktbehauptung erkennt nur Recherche + Redaktion.
- **Historie bleibt Historie:** `FAKTENFRISCHE-996-2026-11-02.md`,
  Queue und Dossiers wurden nicht umgeschrieben.

## 8. Geänderte Dateien

- `content/posts/2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas/index.md` (Pin, Bonus-Satz, Description, Quelle, `lastmod`)
- `content/posts/2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026/index.md` (Pin-Titel/-Text, `lastmod`)
- `content/posts/2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden/index.md` (Pin, `lastmod`)
- `content/posts/2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen/index.md` (Pin, Quelle, `lastmod`)
- `data/faktenfrische_befunde_996.yaml` (neu, Schließakte)
- `scripts/tests/test_faktenfrische_996.py` (4 → 12 Tests)
- `scripts/faktenfrische.py` (SYSTEM_PROMPT Regel 11, Pin-Flächen im Prüfauftrag)
- `scripts/faktenfrische_befund_ledger.py` (`pruef_hash` inkl. Werbeflächen)
- `scripts/FAKTENFRISCHE.md`, `package.json` (`test:faktenfrische:996`)
- diese Datei (Heilungs- und Signaturakte)

## 9. Nachtrag 03.11.2026: Drei rote PR-Checks – zwei geheilt, einer Altlast

Der PR-Lauf meldete drei rote Checks. Aufgeklärt und getrennt:

| Check | Ursache | Heilung |
|---|---|---|
| Snippet-Gate (Playwright) | **Dieser PR:** Die neue Description des 10.08. hatte 157 Zeichen / 991 px (SSOT `serp_limits.py`: 155 / 985). | Auf 139 Zeichen / 868 px gekürzt; Test-Korridor von 70–165 auf die SSOT 70–155 nachgezogen. Alle vier Descriptions messen jetzt befundfrei. |
| Integritäts-Siegel | **Altlast auf `main`, nicht dieser PR:** `data/integrity_lock.json` ist seit `c2c83bfce` (02.11.2026) zerstörtes JSON (ineinander geschobene Signaturen); letzte gültige Fassung `8af76b55` (01.11.2026). Kein Faktenfrische-File ist Kern des Locks. | Belegter Reparaturpfad des Guards selbst: `--repair-lock` stellte das Siegel aus der Git-Historie wieder her (55 Dateien); der Restdrift waren exakt die vier in PR #1021 (`cf1b80786`) committeten Vertragsdateien – `--heal` hat nur diesen belegten, committeten Drift der Klasse FEST neu signiert. Gate lokal grün: „55 Kerndateien entsprechen exakt dem signierten Stand“. Herkunft steht in Lock-Audit und `integrity_history.jsonl`. |
| Governance-Vertrag C1–C18 (Qualitäts-Gate) | **Altlast:** Derselbe Schritt ist auf `main` (Run 41599569588, SHA e984f26) vor diesem PR rot; lokal ist `--quick` grün (43 Regeln). | Kein Eingriff ohne Log-Beweis (CI-Logs waren nicht abrufbar, EOF – der aus #984 bekannte Blob-Befund). Ehrlich als offene Altlast benannt, nicht wegretuschiert. |

Die Siegel-Heilung liegt als eigener Commit im PR, damit Herkunft und
Verantwortung getrennt lesbar bleiben: Sie heilt das Gate, ändert aber
keine der 16 #996-Entscheidungen.
