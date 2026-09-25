# Lektorat 25.09.2026 · „Gasrechnung senken: Deine Strategie für den Winter 2026“

**Auftrag:** Rechtschreibung und Grammatik auf Premium-Niveau (Profi-Agentur)
prüfen und beheben.

| | |
|---|---|
| **Artikel** | `content/posts/2026-09-20-gasrechnung-senken-deine-strategie-fuer-den-winter-2026/index.md` |
| **Live-URL** | <https://franksfinanzcheck.de/posts/2026-09-20-gasrechnung-senken-deine-strategie-fuer-den-winter-2026/> |
| **Umfang** | 246 Zeilen · 14.443 Zeichen · ~1.710 Wörter · 9 H2 · 5 H3 · 1 Tabelle · 2 FAQ-/Listenblöcke |
| **Änderungen** | **60 Korrektur-Regeln** (61 Textstellen – u. a. zweimal derselbe Komposita-Fehler) + Leerzeilen-Hygiene |
| **Riskante Zonen** | unangetastet (siehe „Schutzzonen-Beweis“) |

---

## 1. Was geprüft werden konnte – und was nicht

| Prüfweg | Status |
|---|---|
| `casing_guard.py` (C1–C17 + T1), `heading_guard.py`, `dash_guard.py`, `umbruch_guard.py`, `emoji_guard.py`, `table_guard.py` | ✅ gelaufen (offline lauffähig) |
| `profi_text_check.py`, `readability_check.py`, `quality_score.py`, `check_length.py`, `report_hygiene.py` | ✅ gelaufen |
| `textverstaendnis_guard.py` (R2–R9) | ✅ gelaufen – **0 Befunde** für diesen Artikel |
| `spellcheck.py` (Hunspell de_DE) | ⚠️ **nicht möglich** – in dieser Sandbox ist kein Hunspell-Dictionary installiert |
| `grammar_check.py` (LanguageTool-API) | ⚠️ **nicht möglich** – keine Netzanbindung aus der Sandbox |
| `hugo` (Build/DOM-Audit/Playwright) | ⚠️ **nicht möglich** – Hugo-Binary nicht installiert (offline) |

Konsequenz: Das eigentliche Lektorat wurde **manuell nach Duden-Regelwerk**
durchgeführt, jede Änderung vor dem Schreiben verifiziert (jede Ersetzung genau
einmal, sonst Abbruch ohne Schreibvorgang) und anschließend durch alle offline
lauffähigen Repo-Wachen gegengeprüft. Hunspell- und LanguageTool-Lauf holen die
CI-Workflows (`content-engine-v2.yml`, `seo-weekly.yml`) im Netzkontext nach.

---

## 2. Behobene Befunde (60 Korrektur-Regeln, nach Kategorie)

### 2.1 Rechtschreibung / Wortbildung (Duden)

| vorher | nachher | Fundstelle |
|---|---|---|
| „für die **Herbst Vorbereitung**“ | „für die **Herbstvorbereitung**“ | `description`, `pin_description` |
| „Die **Herbst Vorbereitung** ist daher …“ | „Die **Herbstvorbereitung** ist daher …“ | Fließtext |
| „## Die technische **Herbst Vorbereitung**: Heizung prüfen“ | „## Die technische **Herbstvorbereitung**: Heizung prüfen“ | H2-Überschrift |
| „Diese kommenden Änderungen machen deine **Herbst Vorbereitung** …“ | „… deine **Herbstvorbereitung** …“ | Fließtext |
| „**gesetzliche Lage:**“ | „**Gesetzliche Lage:**“ | Modul „Das Wichtigste in Kürze“ |

Komposita-Trennung (`Herbst Vorbereitung`) war der häufigste echte
Orthografie-Fehler: **6 Vorkommen** im sichtbaren Text (Überschrift, Fließtext,
Meta-Description, Pin-Text).

### 2.2 Grammatik, Syntax, Kongruenz

| vorher | nachher |
|---|---|
| „Wer seine **gasrechnung senken senken** will, sollte …“ (Kleinschreibung + Wortdopplung) | „Wer seine **Gasrechnung senken** will, sollte …“ |
| „Deine **Gasrechnung senken** beginnt mit einem klugen Finanz-Check …“ (Infinitiv als Subjekt) | „Der Weg zu einer niedrigeren Gasrechnung beginnt mit einem klugen Finanz-Check …“ |
| „Wer **seine Heizkosten sparen** will, muss …“ (falscher Kasusbezug) | „Wer **Heizkosten sparen** will, muss …“ |
| „Wer **seine Heizkosten sparen** will, kombiniert Tarifwechsel …“ | „Wer **Heizkosten sparen** will, kombiniert einen Tarifwechsel mit technischen Maßnahmen.“ |
| „Möchtest du erfolgreich deinen **Gastarif wechseln**, achte auf …“ (Modalverb-Fehlkonstruktion) | „Wenn du deinen **Gastarif wechseln** willst, achte auf …“ |
| „Nutze den intensiven Wettbewerb … aktiv zu deinem Vorteil **aus**.“ (Trennverb-Kollision) | „Nutze den intensiven Wettbewerb der Versorger gezielt zu deinem Vorteil.“ |
| „Allerdings unterliegen Kessel **über 30 Jahren** oft einer … Austauschpflicht.“ (falscher Kasus) | „Allerdings gilt für Heizkessel, **die älter als 30 Jahre sind**, oft eine gesetzliche Austauschpflicht.“ |
| „Liegt der Druck **unter dem** markierten grünen Bereich …“ | „Liegt der Druck **unterhalb des** markierten grünen Bereichs …“ |
| „Dann musst du **diese** in vielen Fällen … ersetzen.“ | „Dann musst du **sie** in vielen Fällen … ersetzen.“ |
| „**Ein kurzes Zischen** aus dem Entlüftungsventil **stellt** die Wärmeeffizienz … wieder her.“ (Ursache/Wirkung vertauscht) | „**Zischt es** am Entlüftungsventil, entweicht die Luft – die Wärmeeffizienz steigt sofort wieder.“ |
| „Das Entlüften … ist eine einfache Maßnahme für dich –␣␣“ + Satzfortsetzung über Hard-Break | „Das Entlüften der Heizkörper erledigst du am besten selbst. Luft im System verhindert, …“ |
| „Vermeide Verluste **an die Atmosphäre oder in** ungenutzte Kellerräume.“ | „Vermeide **Wärmeverluste an die Atmosphäre und in** ungenutzte Kellerräume.“ |

### 2.3 Kollokationen und Anglizismen-Kalk (Wort, das so nicht steht)

| vorher | nachher |
|---|---|
| „startet dann **in eine neue Phase**“ | „geht damit in eine neue Phase“ |
| „Bisher waren die Preise … fest vom Gesetzgeber **vorgeschrieben**.“ | „Bisher hat der Gesetzgeber den Preis pro Tonne CO2 fest **vorgegeben**.“ |
| „da Zertifikate knapper und **kostspieliger** werden“ | „Knappere und teurere Zertifikate treiben den Gaspreis tendenziell nach oben.“ |
| „eine häufig taktende Therme“ / „Zertifikate“ – Wortdopplung „teurer … teurer“ | siehe oben (eine Aussage, ein Satz) |
| „spart dir sofort **ca. 5 % deiner Energie**“ | „senkt deinen Verbrauch sofort um **rund 5 %**“ |
| „kostet dich nur wenige Minuten **deiner Zeit**“ | „kostet dich nur wenige Minuten“ |
| „Ein Vergleich dauert … nur wenige Minuten **deiner Zeit**.“ | „Der Vergleich dauert online meist nur wenige Minuten.“ |
| „**kaufmännische Cleverness**“ | „kluges Handeln“ |
| „arbeitet **hochgradig rentabel**“ | „kommt rechnerisch auf 600 € pro Stunde“ |
| „korrigieren **menschliche Heizfehler vollkommen** automatisch“ | „korrigieren typische Heizfehler automatisch“ |
| „die Heizung hinter dem Sofa unnötig **ballert**“ (umgangssprachlich, blogweit einmalig) | „… unnötig weiterläuft“ |
| „Isoliere … im **kühlen** Keller …“ | „Isoliere … im Keller …“ |
| „Vergleiche … **mit den neuen Marktangeboten online**.“ | „Vergleiche deinen aktuellen Arbeitspreis **online mit den Marktangeboten**.“ |
| „Vergleiche … deinen Arbeitspreis mit den **neuen** Marktangeboten“ (Wortstellung) | siehe oben |
| „Smarte Thermostate … **vollkommen** automatisch“ | „… automatisch“ |
| „Wer diese Checkliste abarbeitet, muss im Winter **garantiert** nicht frieren.“ | „… muss im Winter nicht frieren.“ (Werbeaussage entschärft) |
| „Diese Zahlen **beweisen**, dass …“ | „Diese Zahlen **zeigen**, dass sich kluges Handeln auszahlt.“ |

### 2.4 Terminologie-Konsistenz (R3-Logik: ein Konzept = ein Leitbegriff)

Der Artikel benutzte für dieselbe Sache fünf Begriffe: *Anlage, Therme,
Gastherme, Heizungsanlage, Kessel* – und für dieselbe Person *Fachmann,
Fachkraft, Profi, Heizungsbauer, Fachbetrieb*.

| vorher | nachher |
|---|---|
| „Eine schlecht eingestellte **Anlage** …“ / „Die **Anlage** arbeitet ruhiger …“ | „Eine schlecht eingestellte **Heizung** …“ / „**Deine Therme** arbeitet ruhiger …“ |
| „… nutzt den Brennwerteffekt deiner **Gastherme** optimal aus. Die **Therme** verwendet …“ | „… nutzt den Brennwerteffekt optimal aus. **Sie** verwendet …“ |
| „Prüfe … den Druck am **Kessel** erneut.“ | „… den Druck an der **Therme** erneut.“ |
| „Ein **Fachmann** stellt beim Abgleich … ein.“ | „Ein **Fachbetrieb** stellt beim Abgleich … ein.“ |
| „Aufwand: **Fachkraft**“ (Tabelle) | „Aufwand: **Fachbetrieb**“ |
| „Termin beim **Heizungsbauer** deines Vertrauens“ | „Termin beim **Fachbetrieb** deines Vertrauens“ |
| „Dabei stellt **der Profi** den Brenner optimal ein …“ | „Dabei stellt **die Fachkraft** den Brenner optimal ein …“ |
| kurzantwort: „die **Heizanlage** warten lässt“ | „die **Heizungsanlage** warten lässt“ |

### 2.5 Redundanz, Lesbarkeit, Textfluss

| vorher | nachher |
|---|---|
| „Scheue den Wechsel nicht, denn … ausgeschlossen.“ + „Die lückenlose Belieferung … garantiert.“ (2× dieselbe Aussage) | „Scheue den Wechsel nicht: In Deutschland ist die Belieferung gesetzlich gesichert, eine Versorgungslücke gibt es nicht.“ |
| „über die gesamte Heizperiode **hinweg** zu“ | „für die gesamte Heizperiode zu“ |
| „Scheue … / Betrachten wir ein Beispiel für einen Haushalt im Einfamilienhaus. Bei einem Jahresverbrauch von 20.000 kWh …“ | „Betrachten wir ein Einfamilienhaus mit einem Jahresverbrauch von 20.000 kWh. Bei dieser Menge …“ |
| „Es reicht nicht aus, das Thermostat lediglich ein Grad niedriger zu drehen.“ | „Es reicht nicht, nur das Thermostat um ein Grad niedriger zu stellen.“ |
| „Prüfe jetzt deine **Hardware** …“ | „Prüfe jetzt deine Heizung …“ |
| „Den kleinen Check wie Entlüften erledigst du einfach …“ | „Kleine Aufgaben wie das Entlüften erledigst du …“ |
| „Dauerhaft gekippte Fenster …“ · „dauerhaft frische Luft“ · „dauerhafter Höchstleistung“ (3× *dauerhaft* in 4 Sätzen) | nur noch 1× *dauerhaft*, sonst „frische Luft“ / „ständiger Höchstleistung“ |
| „In vielen Gebäuden werden **nahe** Heizkörper knallheiß …“ (Wortstellung/Wortwahl) | „Heizkörper **in der Nähe der Therme** sehr heiß …“ |
| „Gehe diese Punkte idealerweise … **konzentriert durch**.“ | „Gehe diese Punkte am besten … **in Ruhe durch**.“ |

**Struktur-Eingriff:** Die Einleitung war ein Absatz mit 5 Sätzen
(`readability_check`: „1 Absätze > 4 Sätze“). Der Einstieg ist jetzt in Lead
(2 Sätze) und Vorspann (3 Sätze) geteilt – Haus-Regel R5 erfüllt.

### 2.6 Typografie / Satzzeichen

| vorher | nachher |
|---|---|
| „| Anbieterwechsel (**aus Grundversorgung**) |“ (fehlender Artikel) | „(aus **der** Grundversorgung)“ |
| Trailing-Space hinter dem Schnell-Tipp-Link | entfernt |
| Hard-Break (`␣␣` am Zeilenende) mitten im Satz (Z. 80) | Satz geteilt, Hard-Break entfällt |
| 2 doppelte Leerzeilen vor „**Lesetipp:**“/„**Weiterlesen:**“ | je eine Leerzeile (Blog-Standard) |
| „ca. 5 %“ | „rund 5 %“ (RS5-konforme Einordnung, „ca.“ bleibt in der Tabelle) |

---

## 3. Schutzzonen-Beweis (maschinell geprüft)

| Prüfung | Ergebnis |
|---|---|
| Linkziele vor/nach | **byte-identisch** (5 Links, 3× `/go/gas/`) |
| Frontmatter-Schlüssel | **identisch** (19 Schlüssel, keine Strukturänderung) |
| H2 / H3 | **9 / 5 – unverändert** (Anker „herbstvorbereitung“ wird nirgends verlinkt – geprüft) |
| Tabelle | **7 Zeilen, gleiche Spalten/Ausrichtung** (`table_guard.py`: 0 Funde) |
| NBSP-Typografie vor `%`/`€`/`kWh`/`°C` | erhalten (35 → 36, keine Einheit ohne geschütztes Leerzeichen) |
| Emoji | 2 Touchpoints (💡, 👉) – `emoji_guard.py`: sauber |
| Weiche Trennstellen | `umbruch_guard.py`: 0 Funde |
| Strich-Typografie | `dash_guard.py`: keine neuen Funde |

---

## 4. Gate-Ergebnisse vorher → nachher

| Messgröße | vorher | nachher |
|---|---|---|
| `casing_guard --dry-run` | **1 harter Fund** (C15 `seine gasrechnung`) | ✅ 0 Funde |
| `readability_check` Score | 75 / 100 („1 Absatz > 4 Sätze“, Flesch 56,2) | **80 / 100** (0 lange Absätze, Flesch 57,9) |
| `quality_score` | 0,85 | **0,86** (Lesbarkeit 0,75 → 0,80) |
| `profi_text_check` | 100 / 100 | 100 / 100 |
| `textverstaendnis_guard` (R2–R9) | 0 Befunde | 0 Befunde |
| `check_length` | im Optimum (12.000–18.000 Zeichen) | im Optimum (14.443 Zeichen Quelle) |
| `report_hygiene --check` | ✅ | ✅ (dieses Dokument liegt bewusst in `docs/`) |

---

## 5. Bewusst nicht geändert (mit Begründung)

1. **`tags` / `keywords`: „Herbst Vorbereitung“.** Die Wache schützt
   Suchbegriff-Schreibweisen ausdrücklich (`keywords` = unantastbare Zone; Tags
   sind der gesuchte Term). Der Begriff läuft über **10 Artikel** als Taxonomie-Term –
   eine Umbenennung nur hier würde die Tag-Seite spalten. Empfehlung: einmalige
   Blog-weite Entscheidung „Herbstvorbereitung“ (Term-Dedupe über T1) statt
   Einzelkorrektur.
2. **`CO2` statt `CO₂`.** Haus-Schreibweise: 37× `CO2` zu 6× `CO₂` – keine
   Einzelabweichung eingeführt.
3. **Fakten und Zahlen.** Rechnung (12 → 9 Cent, 20.000 → 17.000 kWh,
   2.400 € → 1.530 € = 870 € Ersparnis) ist rechnerisch korrekt und blieb
   unangetastet. Ebenso die rechtlichen Aussagen (Ersatzversorgung,
   Austauschpflicht, CO2-Preiskorridor ab 2026).
4. **Boilerplate** (Schnell-Tipp, Affiliate-Disclaimer, Lesetipp/Weiterlesen,
   Schluss-CTA) – nur die Rechtschreibung im angrenzenden Fließtext wurde
   angepasst.
5. **Kurzantwort-Sachverhalt** (Wärmebrücken, Vorlauftemperatur 55 °C) bleibt als
   inhaltlicher Punkt offen: Diese beiden Empfehlungen kommen im Artikel selbst
   nicht vor. Das ist eine **redaktionelle** Ergänzung, keine Sprachkorrektur –
   gemeldet, nicht eigenmächtig geändert.

---

## 6. Offene (weiche) Kennzahl

`readability_check`: **Flesch-Amstad 57,9** (Zielhorizont ≥ 62 · Floor 55).
Der Artikel liegt damit über dem Floor, aber unter dem Ziel. Ursache ist die
**Wortlänge** (Ø 5,8 Buchstaben; „Wärmeeffizienz“, „Brennwerteffekt“,
„Emissionszertifikate“): Die Amstad-Formel bestraft Silben, nicht Satzbau – die
Ø Satzlänge ist mit 10,8 Wörtern bereits sehr gut. Eine Hebung auf ≥ 60 wäre nur
durch Ersatz von Fachbegriffen möglich (Substanzverlust). **Empfehlung:** beim
nächsten inhaltlichen Update 2–3 Fachbegriffe bei Ersterwähnung durch einfachere
Wendungen ersetzen, statt den Fachwortschatz zu opfern.

---

## 7. Verifikationskommandos

```bash
F=content/posts/2026-09-20-gasrechnung-senken-deine-strategie-fuer-den-winter-2026/index.md
python3 scripts/casing_guard.py --dry-run --file $F
python3 scripts/dash_guard.py --file $F
python3 scripts/umbruch_guard.py --file $F
python3 scripts/emoji_guard.py --file $F
python3 scripts/table_guard.py --file $F
python3 scripts/heading_guard.py --file $F
python3 scripts/profi_text_check.py --file $F
python3 scripts/readability_check.py --file $F
python3 scripts/quality_score.py --file $F
python3 scripts/check_length.py --file $F
python3 scripts/textverstaendnis_guard.py   # R2–R9, blogweit
python3 scripts/spellcheck.py --file $F     # braucht Hunspell (CI/Netzkontext)
python3 scripts/grammar_check.py --file $F  # braucht LanguageTool-API (CI/Netzkontext)
hugo --destination public && npm run test:e2e   # Rendering + 25 E2E-Tests (CI)
```
