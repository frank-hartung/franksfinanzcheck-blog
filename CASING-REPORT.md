# 🔠 CASING-REPORT (Groß-/Kleinschreibung)

**Stand:** 2026-09-11 18:17 UTC · Modus: fix · new-only

Geprüfte Dateien: 26 · geprüfte Content-Wörter: 48.898 · Dateien mit Fund im Lauf: 2 · erkannte Funde: 6 · offene Befunde: 5 · hart (gate-würdig): 0 · automatisch geheilt: 1

**Casing-Deliktquote:** 0.00 harte Befunde je 1.000 Wörter – Zielwert 0,00 (Redaktions-Standard Capital/WiWo/ZEIT).

| Regel | Bedeutung | offene Befunde |
|---|---|---|
| C12-guard | Title-Case-Leak Heading – **nur melden**, entscheidet die Redaktion | 5 |

## ⚠ Struktur-Hinweis (außerhalb des Casing-Kanons)

5 Überschriftenzeile(n) tragen Absatztext direkt hinter dem Titel – Hugo baut daraus eine **fette Überschrift über dem ganzen Absatz** (sichtbar auf der Live-Seite). Die Wache biegt dort bewusst nichts: die Großbuchstaben danach sind korrekte Satzanfänge, der Fehler ist die fehlende Absätzebene. Trennen: Zeile nach dem Titel mit `

` aufbrechen (oder `python3 scripts/casing_guard.py --split-headglue` heilt die eindeutigen Faelle (Fettkoerper / Folgesatz), mehrdeutige bleiben hier stehen).

## ✅ In diesem Lauf geheilt

| Datei | erkannte Funde | Korrekturen |
|---|---:|---:|
| `content/posts/2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer/index.md` | 1 | 1 |

## Offene Befunde je Datei

### `content/posts/2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps/index.md` – 5 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 76 | report | `1. Die 72‑Stunden‑Regel gegen Impulskäufe Möchtest du etwa` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 82 | report | `3. Vorkochen (Meal Prep) & smarter Wocheneinkauf Essen aus` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 84 | report | `4. Den Notgroschen zuerst aufbauen Investiere erst, wenn d` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 86 | report | `5. Das Prinzip „Pay Yourself First“ Zahle dich zuerst selb` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 207 | report | `Wie kann ich Frugalismus im Familienhaushalt umsetzen, ohn` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |


**Trend:** 0 → 0 harte Befunde (+0) ↔️ stabil · Historie: `data/casing_history.jsonl`

---
_Zonen: `keywords`/Slugs/URLs/Code = unantastbar · `title`/`description` = nur Tippfehler · `tags`/`categories` = Tag-Kanon + Term-Dedupe · Pin-Felder = volle Regeln · Body = alles._
_Lexikon-Pflege: `scripts/tag_casing.py` (NOUNS/LOWER/BRANDS/ACRONYMS/FIXED_PHRASES) · geschützte Wörter: `data/casing_whitelist.txt`._
