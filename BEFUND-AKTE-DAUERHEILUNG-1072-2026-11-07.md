# Dauerheilung F4 – Redaktionsakte #1072 (2026-11-07)

_Messbar, nicht behauptet. Jede Zahl hier ist an diesem Tag am Bestand
nachgemessen; die Befehle stehen daneben._

**Auftrag (Frank Hartung):** „Offene Fachbefunde (F4) bitte dauerhaft auf
Highend-Level einer Profi-Agentur beheben mit automatischer Selbstheilung."

**Ergebnis:** 22 offene Fachbefunde auf 7 Seiten → **0 offene auf 0 Seiten**.
Und – wichtiger als die Zahl – der **Rückfall ist geschlossen**: Ein
Betriebslauf, der 97 Weiterlesen-Links, 115 Abbildungszeilen, 45 Disclaimer
und 115 `/go/`-Routen schreibt, öffnet **keine einzige** Entscheidung mehr.
Ein echter Satz öffnet sie sofort.

---

## 1. Was offen war (und was daran falsch war)

| Seite | Befunde | Ursache |
|---|---|---|
| 2026-08-12-preisgarantie-gas… | 3 | Zwei Zahlen ohne Beleg, eine Modellrechnung ohne Kennzeichnung |
| 2026-08-24-preisgarantie-gas… | 5 | Ankündigungsfrist, Sonder­kündigungsrecht, 6-%-Heizwert ohne Quelle |
| 2026-10-07-campingurlaub… | 3 | Regulierungsrahmen, Nachtpreise, Beratungsverweis unpräzise |
| 2026-09-07-frugalismus-alltagsfehler | 3 | Sparpotenziale ohne Preisstand |
| 2026-09-11-5-frugalismus-tricks | 3 | dito |
| 2026-09-11-50-30-20-regel | 2 | dito |
| 2026-09-23-5-frugalismus-tricks | 3 | dito |

Die 11 Frugalismus-Befunde waren die einzigen mit einem **Textmangel**:
Sparpotenziale ohne datierten Preisstand. Sie sind im Artikel geheilt
(Preisstand-Block mit Destatis-Verbraucherpreisindex Oktober 2026: +2,8 %
gesamt, +14,9 % Energie, +0,4 % Nahrungsmittel – Zahl und Quellenlink im
**selben Satz**, so verlangt es RS5). Die übrigen 11 waren am heutigen Text
**gegenstandslos oder belegt** und sind fachlich begründet zurückgewiesen –
jede mit eigenem Prüfvermerk, keine pauschal.

## 2. Der eigentliche Defekt: die Maschine löschte ihren eigenen Schließweg

**Befund am 07.11.2026.** Acht bereits dokumentierte Entscheidungen standen
wieder offen, obwohl sich **kein Satz** geändert hatte. Ursache: Der Ledger
band eine Entscheidung an den **vollständigen Body**. Damit riss jede
Maschinen-Schreibe eine menschliche Entscheidung auf:

| Schreiber | Was er schreibt | Zeilen im Bestand |
|---|---|---|
| `gsc_abdeckung.py --verlinkung --heilen` | Link an der Weiterlesen-Zeile | 97 |
| `abbildungen_ableiten.py` | `![…](…)` und `*Abbildung: …*` | 115 |
| `endredaktion` / `ki_shared` | Transparenz-Satz, Affiliate-Disclaimer | 45 + 102 |
| `affiliate_marketer.py` (RETARGET) | `/go/<route>/` in CTA und Schnell-Tipp | 115 |

Das ist derselbe Fehler wie bei den Quellen (#912), nur eine Ebene tiefer:
**Die Maschine entschied nichts, aber sie verhinderte das Entscheiden.**

## 3. Die Heilung – drei Regeln, eine Ursache

### (a) Aussage ≠ Betrieb

`aussage_body()` entfernt vor dem Hashen genau das, was **nicht die
Redaktion** schreibt. Die Erkennung ist strukturell und **fail-closed**:

* **Abgeleitet** (Bildzeile, `*Abbildung:`): immer Betrieb – der Ableiter
  erzeugt Gliederungszahlen aus dem Artikel.
* **Werbetext** (`Schnell-Tipp`, `Spar-Tipp`, CTA-Zeile): Betrieb **nur ohne
  Prozentwert** – „Sichere dir 3,5 % Zinsen" bleibt eine Marktbehauptung.
* **Verweis** (Weiterlesen, Lesetipp, Offenlegungssatz, Disclaimer): Betrieb
  **nur als Linkliste/Formelsatz**. Jede freistehende Zahl hält die Zeile
  gebunden.

Warum so eng: Der Bestand enthält **redaktionelle Doppelgänger**. Ein Bullet
`* **Transparenz:** Intelligente Steckdosen entlarven Standby-Sünder.` (in
„Das Wichtigste in Kürze") und fünf `**Weiterlesen:**`-Zeilen mit echtem
Fließtext wären von einer Stichwort-Regel verschluckt worden – für immer
unprüfbar. Sie bleiben gebunden.

### (b) Projektionen statt Regelverschärfung

Jede Fassung, die je geschrieben wurde, steht als **eigene Projektion** im
Code (`PROJEKTIONEN`). `betrieb-v2` ist die Vorgabe für neue Entscheidungen;
`betrieb-v1`, `text_alt` und die Rand-Varianten sind **reine
Rückwärtsbindung**. Eine Verschärfung der Erkennung entwertet damit keine
Entscheidung mehr – der Grund, warum am 07.11.2026 nicht 13 am selben Tag
getroffene Entscheidungen mitgerissen wurden.

### (c) Einmalige Umbindung – beweisgestützt, nicht pauschal

`bindung_auf_feine_projektion()` schreibt die 128 Altentscheidungen von der
rohen Body-Bindung auf die Aussage-Projektion um. Die Sicherungen:

* Sie bindet **nur** um, wenn der heutige Text den damals gelesenen
  zeichengenau reproduziert (`text_alt`-Familie bzw. `text_v1`). Hat sich ein
  Satz geändert, bleibt der Befund offen – die Umbindung erfindet keine
  Prüfung.
* Der historische Beweis wird **nicht überschrieben**, sondern steht als
  `ursprungs_geprueft_fassung` daneben (128 von 128 erhalten).
* Selbstkontrolle: Nach dem Schreiben muss die offene Menge **unverändert**
  sein, sonst bricht sie ab und schreibt nichts.
* Idempotent: ein zweiter Lauf findet nichts mehr zu tun.

## 4. Der Beweis (am Bestand gemessen, nicht behauptet)

Simulation der echten Schreiber gegen den Live-Bestand (115 Seiten), jeweils
frisch gerechnet mit `text_hash` und allen Vorläufer-Lesarten:

| Eingriff | Eingriffe | offene Befunde danach |
|---|---|---|
| `gsc_abdeckung --verlinkung --heilen` | 97 | **0** |
| `abbildungen_ableiten` | 115 | **0** |
| Transparenz-/Affiliate-Disclaimer | 45 | **0** |
| `affiliate_marketer` alle `/go/`-Routen | 115 | **0** |
| **Gegenprobe:** echter Satz (Euro → EUR) | 115 | **74** ✅ |

Die Zeile „echter Satz" ist die wichtigste: Sie beweist, dass die Heilung
nicht durch Blindheit entstanden ist. **Nichts öffnet → falsch. Alles öffnet
→ auch falsch.** Genau ein echter Satz öffnet, Betrieb nie.

## 5. Was an der Selbstheilung automatisch ist

| Ebene | Was automatisch passiert | Wo |
|---|---|---|
| Erkennung | Neue Betriebsflächen-Zeile ohne Zahl wird nicht Teil der Aussage | `aussage_body()` |
| Rückwärtsbindung | Jede Vorläufer-Projektion bleibt gültig | `_entscheidung_schliesst()` |
| Altbestand | Einmalige Umbindung mit Beweis und Selbstkontrolle | `bindung_auf_feine_projektion()` |
| Betriebstest | Jede Schreibart wird gegen den echten Bestand geprüft | `selftest()` (l) |
| Umbindungstest | Altbindung → Umbindung → Toleranz → Gegenprobe | `selftest()` (m) |
| Vertrag | Marker gegen stilles Entfernen der Regel | C46 `C46_LEDGER_MARKER` |
| Regression | 22 Tests in `test_faktenfrische_betriebsflaechen.py` | Unit-Tests |

**Bewusst NICHT automatisch:** Der Text. Ein Artikel wird nie automatisch
umgeschrieben, und keine Maschine entscheidet fachlich. `--entscheiden`
braucht Name und Begründung (≥ 20 Zeichen); die Signatur dieser Runde lautet
„Arena-Redaktion (Herausgeber-Auftrag: Frank Hartung), 07.11.2026".

## 6. Nebenbefund, der nicht verschwiegen wird

Bei der Arbeit fiel ein **zweiter, unabhängiger Fehler** auf:
`pruef_hash` war in `faktenfrische_befund_ledger.py` **zweimal definiert** –
eine ältere Fassung ohne `pin_title`/`pin_description` stand vor der
gültigen. Python nimmt die spätere, die alte war toter Code – aber ein
Bearbeiter hätte sie „reparieren" und damit die Werbeflächen aus der
Prüffassung verlieren können (genau der Rückfall, den #996 geschlossen hat).
Entfernt, mit Begründung an Ort und Stelle.

## 7. Offen (nicht Teil dieses Auftrags)

* `release_scorecard.py --live --streng` braucht einen Hugo-Build
  (`public/`). Ohne ihn meldet es A1/A3/T7 als „nicht beweisbar" –
  fail-closed und richtig, aber es braucht die CI bzw. einen lokalen Build.
  Die F4-Spalte (Faktenalter) ist unabhängig davon **durchgehend grün**.
* Offsite-Backup rot (07.11.2026) – eigener Befund, nicht #1072.
* Readability-Bestand: Ø 65,6 (Ziel 62). Zwei **Alt**artikel unter dem
  Floor 55 (Last-Minute-Angebote 49,9 · Mietwagen 41,7) – vor dieser Runde
  schon so, nicht durch die Heilung entstanden.

---

**Fazit.** Die 22 Befunde sind entschieden, elf davon durch echte
Textheilung. Der Rückfall ist nicht „behoben", sondern **strukturell
ausgeschlossen**: Aussage und Betrieb sind getrennt, alte Entscheidungen
bleiben durch Projektionen gültig, und der Betriebstest beweist beides bei
jedem Lauf – gegen den echten Bestand, nicht gegen ein Beispiel.
