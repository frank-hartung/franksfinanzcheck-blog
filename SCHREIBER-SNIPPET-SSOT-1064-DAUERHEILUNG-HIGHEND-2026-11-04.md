# Dauerheilung (Highend): Die Schreiber der KI-Redaktion messen jetzt mit dem Markt – Snippet-SSOT ohne zweites Maß

**Vorgang:** WF-7B6B · Issue #1064 (Metadaten-Wache, E2E-Lauf `41832869863`) · Klasse WF-7B6B/#925
**Datum:** 04.11.2026 · **Branch:** `arena/e05e59b1-franksfinanzcheck-blog`
**Auftrag:** „Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben“ (PR-Seite des Repos)

---

## 1. Befund – gemessen, nicht geraten

Am 04.11.2026 lief die Kette so:

| Zeit (UTC) | Ereignis | Beleg |
|---|---|---|
| 12:38 | Content-Engine schreibt Entwurf `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen` | `date:` im Frontmatter |
| 12:51 | Geplanter E2E-Lauf auf `main` (`4149a121`) wird rot: Schritt „Metadaten-Wache – Quelle (Titel, Description, Belege)“ | Lauf `41832869863`, Issue #1064 |
| 12:56 | Deploy-Heiler kürzt die Description vor Veröffentlichung | Commit `70f2744` |
| 13:5x | Lokale Nachmessung auf `main`: Metadaten-Wache grün, 0 Befunde | `python3 scripts/metadaten_wache.py` |

Die verletzte Description (Original, vor der Heilung):

> „Günstigen Mietwagen für den Urlaub buchen – der große Ratgeber von FranksFinanzcheck: Schritt für Schritt erklärt, mit Rechenbeispielen, Checklisten und FAQ.“

Nachmessung mit der SSOT (`scripts/serp_limits.py`):

```
Zeichen: 157   (Grenze: 155)  → zu-lang
Breite:  1007 px (Grenze: 985 px, Arial/Helvetica 14 px) → zu-breit
```

**Der Befund war echt.** Die Wache hat recht; der Deploy-Heiler hat nur das Symptom geheilt.

## 2. Ursache – ein Schreiber mit eigenem Maß

`scripts/ki_shared.py` enthielt:

```python
def clip_text(text: str, max_len: int = 158) -> str:
```

158 Zeichen, ohne Breitenkenntnis. Das ist **exakt die Klasse**, die WF-7B6B/#925 am
29.10.2026 für `keyword_optimizer` und `meta_optimizer` geschlossen hatte („Die
SCHREIBER waren nie gebunden“) – nur dass dieser Helfer der Rollen-Writer nie
gebunden wurde. Vier Schreiber hängen daran, alle bauen Descriptions:

| Schreiber | Stelle | Vorlage |
|---|---|---|
| `claude_writer.py` | 300 | „… der große Ratgeber von FranksFinanzcheck …“ |
| `news_writer.py` | 393 | „… aktuelle Einordnung von FranksFinanzcheck …“ |
| `poppy_repurpose.py` | 278 | „… so gehst du Schritt für Schritt vor …“ |
| `endredaktion.py` (E11) | 517 | dieselbe Vorlage |

157 ≤ 158 – der alte `clip_text` ließ den Text **unverändert** durchgehen. Jeder
Titel ab ~44 Zeichen sprengt mit diesen Vorlagen das Marktfenster. Das war kein
einmaliger Ausrutscher, sondern eine eingebaute Wiederkehr: Der nächste lange
Titel hätte wieder Rot produziert.

Zwei weitere Stellen führten ein zweites Maß:

- `scripts/jasper_seo.py`: `META_MIN, META_MAX = 120, 160` – die Messstelle
  bewertete Descriptions als „gut“, die die Wache verwirft; der KI-Vorschlags-
  prompt (`ai_variants`) lehrte das falsche Fenster gleich mit.
- `scripts/meta_report.py`: Report-Zeile „optimal 120–160“ – ein lebender
  Erzeuger, der ein veraltetes Maß dokumentiert.

## 3. Heilung – eine Zahl, ein Ort (D18), Defense in Depth

1. **`ki_shared.clip_text` ist jetzt Durchreicher zur SSOT.** Der Standardpfad
   ruft `serp_limits.auf_snippet_kuerzen` – Grenzen (100–155 Zeichen), Breitenmaß
   (985 px) und der Wortgrenzen-Schnitt stehen nur dort. Kann die SSOT nicht
   ehrlich kürzen (unmessbare Zeichen, kein Präfix im Fenster), geht der Text
   unverändert zurück und die Wache meldet den Befund – der Schreiber erfindet
   keine neue Grenze. `max_len` bleibt als expliziter Weg für Text außerhalb des
   Snippets (z. B. Pin-Zeilen); kein Description-Aufrufer nutzt ihn.
2. **`ki_shared.build_frontmatter` normalisiert die Description an der letzten
   Writer-Grenze** – wie schon die Tags gegen das Register. Damit ist auch
   `ki_redaktion.py` und jede künftige Rolle gebunden, selbst wenn sie eine rohe
   Description übergibt.
3. **`jasper_seo.py` misst mit der SSOT** (`DESC_OPT_MIN_ZEICHEN`/`DESC_MAX_ZEICHEN`),
   Score-Label und KI-Prompt lesen dieselben Konstanten.
4. **`meta_report.py`** nennt das Fenster aus `meta_optimizer` (das die SSOT
   importiert) statt eines Literals.

Bewusst **nicht** geändert: `serp_limits.py` (die SSOT ist korrekt), die Wachen,
Schwellen oder Tests der Bestandspfade. Keine Lockerung, keine Unterdrückung.

## 4. Regressionsschutz – der Vorfall ist festgenagelt

Neu: `scripts/tests/test_snippet_schreiber.py` (19 Tests, ohne Netz/Modell/Bestand):

- **Vorfall 1064 im Original:** Titel + Vorlage ergeben die 157-Zeichen/1007-px-
  Description; sie muss ins Fenster gekürzt werden. Die 158er-Sperre prüft
  ausdrücklich, dass das alte Maß den Vorfall durchgelassen hätte.
- **#925-Klasse:** 153 Zeichen, die in der Breite reißen, werden geschnitten.
- **Ehrlichkeit:** passende/kurze Texte bleiben unverändert; unmessbare Zeichen
  werden nicht geschätzt (Passthrough + Wachen-Befund).
- **Writer-Grenze:** `build_frontmatter` normalisiert rohe Descriptions; kurze
  bleiben erhalten (Bestandsverhalten der Fachfreigabe-Selbsttests).
- **Alle vier Vorlagen** halten auch mit langem Titel (90 Zeichen) das Fenster.
- **Strukturelle Bindung:** Signatur ohne Zahlen-Default, Delegation an die SSOT,
  kein `max_len` an den vier Aufrufstellen, Jasper- und Report-Konstanten.

Die Suite läuft in CI zusätzlich unter der um 97 Tage vorgestellten Uhr
(`selftest_clock.py --trap-discover`) – die Fixtures sind festgenagelt.

## 5. Nachweis

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_snippet_schreiber` | 19 Tests, OK |
| Gezielte Suites (serp_limits, ki_redaktion_fachfreigabe, endredaktion, news_writer_lesbarkeit, poppy_werkbank, metadaten_wache, keyword_optimizer, meta_optimizer) | 182 Tests, OK |
| `python3 -m unittest discover -s scripts/tests` (volle Suite, mit Änderung) | **5199 Tests, OK (6 skipped), 404 s** |
| `python3 scripts/skript_syntax_wache.py` | grün (636 Dateien) |
| `hugo --minify --destination public --cleanDestinationDir` | baut (Extended 0.168.0) |
| `python3 scripts/metadaten_wache.py` | 114 Dateien, 0 Befunde |
| Integritäts-Siegel | geänderte Dateien sind nicht im Lock (`ki_shared`, `jasper_seo`, `meta_report` frei; `serp_limits` unverändert) |

## 6. PR-Backlog – bereinigt (Auftrag: PR-Seite)

Die offenen PRs wurden einzeln vermessen (Basis, Checks, Ersetzungsverhältnis):

| PR | Zustand vorher | Entscheidung | Begründung |
|---|---|---|---|
| #1052 | rot (CodeQL, Klartext, URL, Regression) | **geschlossen** | Ersetzt durch #1055 (gemergt); dort ausdrücklich dokumentiert, Funde an der Wurzel geheilt |
| #1035 | rot (Siegel, Gate, Regression) | **geschlossen** | Ersetzt durch #1057 (gemergt, `4149a121`): 3-Tupel-Transport #1024 |
| #1051 (Draft) | ersetzt | **geschlossen** | Übernommen in #1056 (gemergt, `8156d4ab5`) |
| #1043 | ältere Iteration | **geschlossen** | Ersetzt durch #1060 (dort selbst dokumentiert) |
| #1039 | Konflikt (Add/Add) | **geschlossen** | Einzige Datei liegt auf `main` – mit Nachtrag 04.11. via #1061 |
| #1056 | rot (alte Basis) | **gemergt** (`8156d4ab5`) | Eigene Session hat Basis aktualisiert; CI grün |
| #1062 | rot (alte Basis) | **Basis aktualisiert** | Regressions-Rot war Artefakt der alten Basis; `main` ist grün (5180 Tests lokal nachgewiesen); CI läuft auf neuem Stand |
| #1060 | rot + Siegel-Konflikt | **offen, Diagnose kommentiert** | `data/integrity_lock.json` (merge=binary) kollidiert mit #1056; Auflösung = main-Fassung nehmen, `integrity_guard.py --heal`, `--gate`. Inhaltliche Review (Einzigartigkeit #1027) bleibt beim Herausgeber |
| #1065 | ohne Checks | **unberührt** | GSC-Datenlauf der Automatik |

**Wichtig:** Das Regressions-Rot auf den PRs war ganz überwiegend ein
**Basis-Artefakt**. Die volle Suite ist auf aktuellem `main` grün (lokal
nachgewiesen, 5180 Tests vor dieser Änderung). Die Bestandbefunde #1041/#1036
waren bereits über #1059/#1037 geheilt; die offenen Issues dazu sind der
Wache-Abschlusslogik überlassen (D2: kein Hand-Abschlussvermerk).

## 7. Grenzen dieser Heilung (ehrlich)

- **F4-Fachbefunde (Release-Scorecard #1047)** bleiben offen: 88 Befunde auf 15
  Artikeln entscheiden Menschen, keine Maschine (D13/C19). Diese Heilung rührt
  daran nicht.
- **#1060** (Einzigartigkeit #1027) ist inhaltliche Arbeit mit redaktioneller
  Wertung; sie wird hier nicht gemergt, sondern mit Auflösungs-Runbook
  zurückgegeben.
- Der Deploy-Heiler bleibt als Sicherheitsnetz bestehen – er ist jetzt die
  zweite Linie, nicht die erste.

## 8. Einordnung

Eine Grenze, die in zwei Dateien steht, läuft auseinander (D18). Die Heilung
vom 29.10. hatte die bekannten Heiler gebunden, aber den Helfer der Rollen-
Writer übersehen. Jetzt ist die Kette geschlossen: **Schreiber → Writer-Grenze
→ Wache → Deploy-Heiler** messen alle mit demselben Maß. Der Rückfallschutz
prüft den Vorfall im Original und die Bindung im Quelltext – nicht nur das
Wohlverhalten von heute.
