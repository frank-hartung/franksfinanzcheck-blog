# 🔠 CASING-REPORT (Groß-/Kleinschreibung)

**Stand:** 2026-09-09 16:41 UTC · Modus: fix · new-only

Geprüfte Dateien: 5 · geprüfte Content-Wörter: 7.607 · Dateien mit Fund im Lauf: 2 · erkannte Funde: 10 · offene Befunde: 5 · hart (gate-würdig): 0 · automatisch geheilt: 10

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
| `content/posts/2026-09-09-5-einfache-frugalismus-tricks-fuer-den-alltag/index.md` | 8 | 8 |
| `content/posts/2026-09-09-guenstig-durch-den-winter-heizungs-check-im-spaetsommer/index.md` | 2 | 2 |

## Offene Befunde je Datei

### `content/posts/2026-09-09-5-einfache-frugalismus-tricks-fuer-den-alltag/index.md` – 5 Befund(e)

| Regel | Zeile | Zone | vorher → nachher |
|---|---|---|---|
| C12-guard | 168 | report | `Wie finde ich den günstigsten Stromtarif? Nutze Vergleichs` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 170 | report | `Muss ich bei einem Tarifwechsel sofort sparen? Der Wechsel` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 172 | report | `Wie oft sollte ich meine Versicherungen überprüfen? Mindes` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 174 | report | `Lohnt sich ein Budget‑Tool wirklich? Ja. Eine einfache App` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |
| C12-guard | 176 | report | `Was ist die praktischste Faustregel für Notgroschen? Drei ` → `Ueberschrift mit angeklebtem Text (Struktur prüfen)` |


**Trend:** 0 → 0 harte Befunde (+0) ↔️ stabil · Historie: `data/casing_history.jsonl`

---
_Zonen: `keywords`/Slugs/URLs/Code = unantastbar · `title`/`description` = nur Tippfehler · `tags`/`categories` = Tag-Kanon + Term-Dedupe · Pin-Felder = volle Regeln · Body = alles._
_Lexikon-Pflege: `scripts/tag_casing.py` (NOUNS/LOWER/BRANDS/ACRONYMS/FIXED_PHRASES) · geschützte Wörter: `data/casing_whitelist.txt`._
