# 🔠 CASING-REPORT (Groß-/Kleinschreibung)

**Stand:** 2026-09-12 00:17 UTC · Modus: report · Bestand

Geprüfte Dateien: 59 · geprüfte Content-Wörter: 99.857 · Dateien mit Fund im Lauf: 4 · erkannte Funde: 11 · offene Befunde: 11 · hart (gate-würdig): 0 · automatisch geheilt: 0

**Casing-Deliktquote:** 0.00 harte Befunde je 1.000 Wörter – Zielwert 0,00 (Redaktions-Standard Capital/WiWo/ZEIT).

| Regel | Bedeutung | offene Befunde |
|---|---|---|
| C12 | Title-Case-Leak Heading | 1 |
| C12-guard | Title-Case-Leak Heading – **nur melden**, entscheidet die Redaktion | 10 |

## ⚠ Struktur-Hinweis (außerhalb des Casing-Kanons)

10 Überschriftenzeile(n) tragen Absatztext direkt hinter dem Titel – Hugo baut daraus eine **fette Überschrift über dem ganzen Absatz** (sichtbar auf der Live-Seite). Die Wache biegt dort bewusst nichts: die Großbuchstaben danach sind korrekte Satzanfänge, der Fehler ist die fehlende Absätzebene. Trennen: Zeile nach dem Titel mit `

` aufbrechen (oder `python3 scripts/casing_guard.py --split-headglue` heilt die eindeutigen Faelle (Fettkoerper / Folgesatz), mehrdeutige bleiben hier stehen).

## Offene Befunde je Datei

### `content/posts/2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden/index.md` – 3 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 75 | report | `4. Smart‑Plug‑Analyse Smart‑Plugs mit integriertem Messwer` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 197 | report | `Welche Geräte verbrauchen im Standby am meisten Strom? * A` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 215 | report | `Wie erkenne ich, ob ein Gerät im Standby mehr als 5 W verb` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |

### `content/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/index.md` – 5 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 76 | report | `1. Die 72‑Stunden‑Regel gegen Impulskäufe Möchtest du etwa` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 82 | report | `3. Vorkochen (Meal Prep) & smarter Wocheneinkauf Essen aus` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 84 | report | `4. Den Notgroschen zuerst aufbauen Investiere erst, wenn d` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 86 | report | `5. Das Prinzip „Pay Yourself First“ Zahle dich zuerst selb` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 207 | report | `Wie kann ich Frugalismus im Familienhaushalt umsetzen, ohn` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |

### `content/posts/2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen/index.md` – 1 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12 | 110 | body | `Kennen` → `kennen` |

### `content/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/index.md` – 2 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 186 | report | `Wie viel Geld muss ich monatlich sparen, um frei zu sein? ` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 192 | report | `Welches Risiko gehe ich beim Vermögensaufbau ein? Jede Anl` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |


**Trend:** 0 → 0 harte Befunde (+0) ↔️ stabil · Historie: `data/casing_history.jsonl`

---
_Zonen: `keywords`/Slugs/URLs/Code = unantastbar · `title`/`description` = nur Tippfehler · `tags`/`categories` = Tag-Kanon + Term-Dedupe · Pin-Felder = volle Regeln · Body = alles._
_Lexikon-Pflege: `scripts/tag_casing.py` (NOUNS/LOWER/BRANDS/ACRONYMS/FIXED_PHRASES) · geschützte Wörter: `data/casing_whitelist.txt`._
