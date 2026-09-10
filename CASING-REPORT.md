# 🔠 CASING-REPORT (Groß-/Kleinschreibung)

**Stand:** 2026-09-10 10:03 UTC · Modus: fix · Bestand · +Pinterest-Plan

Geprüfte Dateien: 55 · geprüfte Content-Wörter: 90.294 · Dateien mit Fund im Lauf: 5 · erkannte Funde: 32 · offene Befunde: 30 · hart (gate-würdig): 0 · automatisch geheilt: 2

**Casing-Deliktquote:** 0.00 harte Befunde je 1.000 Wörter – Zielwert 0,00 (Redaktions-Standard Capital/WiWo/ZEIT).

| Regel | Bedeutung | offene Befunde |
|---|---|---|
| C12-guard | Title-Case-Leak Heading – **nur melden**, entscheidet die Redaktion | 30 |

## ⚠ Struktur-Hinweis (außerhalb des Casing-Kanons)

30 Überschriftenzeile(n) tragen Absatztext direkt hinter dem Titel – Hugo baut daraus eine **fette Überschrift über dem ganzen Absatz** (sichtbar auf der Live-Seite). Die Wache biegt dort bewusst nichts: die Großbuchstaben danach sind korrekte Satzanfänge, der Fehler ist die fehlende Absätzebene. Trennen: Zeile nach dem Titel mit `

` aufbrechen (oder `python3 scripts/casing_guard.py --split-headglue` heilt die eindeutigen Faelle (Fettkoerper / Folgesatz), mehrdeutige bleiben hier stehen).

## ✅ In diesem Lauf geheilt

| Datei | erkannte Funde | Korrekturen |
|---|---:|---:|
| `content/posts/2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen/index.md` | 1 | 1 |
| `content/posts/2026-09-10-energie-update-was-sich-jetzt-fuer-dich-aendert/index.md` | 1 | 1 |

## Offene Befunde je Datei

### `content/posts/2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden/index.md` – 11 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 61 | report | `1. Digitales Strommessgerät einsetzen Ein Zwischenstecker‑` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 63 | report | `2. Zähler‑Nachttest durchführen * **Schritt 1:** Notiere d` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 66 | report | `3. Wärmebild‑Check an Netzteilen Ein Infrarot‑Thermometer ` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 68 | report | `4. Smart‑Plug‑Analyse Smart‑Plugs mit integriertem Messwer` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 184 | report | `Wie viel Strom verbraucht ein typischer 3‑Personen‑Haushal` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 186 | report | `Welche Geräte verbrauchen im Standby am meisten Strom? * A` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 190 | report | `Lohnt sich der Austausch eines funktionierenden Altgeräts?` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 192 | report | `Woher bekomme ich ein kostenloses Strommessgerät? Viele St` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 194 | report | `Wie wechsle ich den Stromanbieter? Der Wechsel läuft kompl` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 198 | report | `Wie erkenne ich, ob ein Gerät im Standby mehr als 5 W verb` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 200 | report | `Kann ich meine Stromrechnung mit einem einfachen Excel‑She` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |

### `content/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/index.md` – 12 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 73 | report | `1. Die 72‑Stunden‑Regel gegen Impulskäufe Möchtest du etwa` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 75 | report | `2. Der monatliche Abo‑ und Vertrags‑Audit Prüfe die Kontoa` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 77 | report | `3. Vorkochen (Meal Prep) & smarter Wocheneinkauf Essen aus` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 79 | report | `4. Den Notgroschen zuerst aufbauen Investiere erst, wenn d` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 81 | report | `5. Das Prinzip „Pay Yourself First“ Zahle dich zuerst selb` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 178 | report | `Was unterscheidet Frugalismus von Knausrigkeit? Knausrigke` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 180 | report | `Wie viel Geld brauche ich als Notgroschen? Als Faustregel ` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 182 | report | `Kann jeder Mensch Frugalist werden? Ja. Frugalismus beginn` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 184 | report | `Wie fange ich am besten mit Frugalismus an? Führe zwei bis` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 186 | report | `Was mache ich mit dem ersparten Geld? Zuerst füllst du dei` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 188 | report | `Wie wirkt sich Inflation auf meine Frugalismus‑Strategie a` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 190 | report | `Wie kann ich Frugalismus im Familienhaushalt umsetzen, ohn` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |

### `content/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/index.md` – 7 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 186 | report | `Wie viel Geld muss ich monatlich sparen, um frei zu sein? ` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 188 | report | `Kann man auch mit Schulden investieren? Nein, meist nicht.` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 190 | report | `Welches Risiko gehe ich beim Vermögensaufbau ein? Jede Anl` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 192 | report | `Muss ich auf alles verzichten, um finanzielle Freiheit zu ` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 194 | report | `Reicht ein Sparkonto für den langfristigen Aufbau aus? Mei` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 196 | report | `Wie kann ich meine Ausgaben tracken, ohne viel Aufwand? Nu` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 198 | report | `Welchen ETF sollte ich für den ersten Sparplan wählen? Ein` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |


**Trend:** 0 → 0 harte Befunde (+0) ↔️ stabil · Historie: `data/casing_history.jsonl`

---
_Zonen: `keywords`/Slugs/URLs/Code = unantastbar · `title`/`description` = nur Tippfehler · `tags`/`categories` = Tag-Kanon + Term-Dedupe · Pin-Felder = volle Regeln · Body = alles._
_Lexikon-Pflege: `scripts/tag_casing.py` (NOUNS/LOWER/BRANDS/ACRONYMS/FIXED_PHRASES) · geschützte Wörter: `data/casing_whitelist.txt`._
