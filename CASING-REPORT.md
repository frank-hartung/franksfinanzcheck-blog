# 🔠 CASING-REPORT (Groß-/Kleinschreibung)

**Stand:** 2026-09-11 10:00 UTC · Modus: fix · Bestand · +Pinterest-Plan

Geprüfte Dateien: 56 · geprüfte Content-Wörter: 92.543 · Dateien mit Fund im Lauf: 4 · erkannte Funde: 15 · offene Befunde: 15 · hart (gate-würdig): 0 · automatisch geheilt: 0

**Casing-Deliktquote:** 0.00 harte Befunde je 1.000 Wörter – Zielwert 0,00 (Redaktions-Standard Capital/WiWo/ZEIT).

| Regel | Bedeutung | offene Befunde |
|---|---|---|
| C12-guard | Title-Case-Leak Heading – **nur melden**, entscheidet die Redaktion | 15 |

## ⚠ Struktur-Hinweis (außerhalb des Casing-Kanons)

15 Überschriftenzeile(n) tragen Absatztext direkt hinter dem Titel – Hugo baut daraus eine **fette Überschrift über dem ganzen Absatz** (sichtbar auf der Live-Seite). Die Wache biegt dort bewusst nichts: die Großbuchstaben danach sind korrekte Satzanfänge, der Fehler ist die fehlende Absätzebene. Trennen: Zeile nach dem Titel mit `

` aufbrechen (oder `python3 scripts/casing_guard.py --split-headglue` heilt die eindeutigen Faelle (Fettkoerper / Folgesatz), mehrdeutige bleiben hier stehen).

## Offene Befunde je Datei

### `content/posts/2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden/index.md` – 3 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 74 | report | `4. Smart‑Plug‑Analyse Smart‑Plugs mit integriertem Messwer` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 196 | report | `Welche Geräte verbrauchen im Standby am meisten Strom? * A` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 214 | report | `Wie erkenne ich, ob ein Gerät im Standby mehr als 5 W verb` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |

### `content/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/index.md` – 5 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 73 | report | `1. Die 72‑Stunden‑Regel gegen Impulskäufe Möchtest du etwa` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 79 | report | `3. Vorkochen (Meal Prep) & smarter Wocheneinkauf Essen aus` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 81 | report | `4. Den Notgroschen zuerst aufbauen Investiere erst, wenn d` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 83 | report | `5. Das Prinzip „Pay Yourself First“ Zahle dich zuerst selb` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 204 | report | `Wie kann ich Frugalismus im Familienhaushalt umsetzen, ohn` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |

### `content/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/index.md` – 2 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 186 | report | `Wie viel Geld muss ich monatlich sparen, um frei zu sein? ` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 192 | report | `Welches Risiko gehe ich beim Vermögensaufbau ein? Jede Anl` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |

### `content/posts/2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag/index.md` – 5 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 166 | report | `Wie finde ich den günstigsten Stromtarif? Nutze Vergleichs` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 168 | report | `Muss ich bei einem Tarifwechsel sofort sparen? Der Wechsel` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 170 | report | `Wie oft sollte ich meine Versicherungen überprüfen? Mindes` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 172 | report | `Lohnt sich ein Budget‑Tool wirklich? Ja. Eine einfache App` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 174 | report | `Was ist die praktischste Faustregel für Notgroschen? Drei ` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |


**Trend:** 0 → 0 harte Befunde (+0) ↔️ stabil · Historie: `data/casing_history.jsonl`

---
_Zonen: `keywords`/Slugs/URLs/Code = unantastbar · `title`/`description` = nur Tippfehler · `tags`/`categories` = Tag-Kanon + Term-Dedupe · Pin-Felder = volle Regeln · Body = alles._
_Lexikon-Pflege: `scripts/tag_casing.py` (NOUNS/LOWER/BRANDS/ACRONYMS/FIXED_PHRASES) · geschützte Wörter: `data/casing_whitelist.txt`._
