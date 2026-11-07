# 🧬 Einzigartigkeits-Audit #1099: Der Generator schrieb das Duplikat – jetzt heilt die Struktur sich selbst

**Datum:** 07.11.2026 · **Bezug:** Issue #1099 „📋 Einzigartigkeits-Audit:
Bestandsüberlappungen gefunden" (Workflow-Lauf 42223848659) · **Auftrag:**
„Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben mit
automatischer Selbstheilung." · **Vorgänger:** #766
(`EINZIGARTIGKEIT-BESTAND-766-…`), #714, #1027 (Diff-Tor).

---

## 1. Befund – zwei verschiedene Krankheiten, ein Symptom

### 1.1 Das kritische Live-Paar (Destatis-Faktenpassage)

```
🚨 2026-09-04-finanzielle-freiheit-erreichen ↔ 2026-09-07-frugalismus-tipps:
   6 gleiche 7-Wort-Phrasen (alle aus einer Destatis-Fakten-/Quellenpassage)
```

Im aktuellen Bestand ist dieses Paar bereits unter der Schwelle (Nachmessung
auf HEAD: **0 geteilte Phrasen** – die Faktenpassagen sind inzwischen
unterschiedlich formuliert). Was bleibt, ist die Lehre: Geteilte
Fakten-Einschübe sind der wiederkehrende Auslöser dieser Issue-Familie
(#1017/#1027: BNetzA-Absatz in drei Gas-Artikeln). Die Gegenmittel existieren
bereits und greifen: das Diff-Tor (`bestand_einzigartigkeit_gate.py`, V4)
blockiert jede **neue** kritische Überlappung in jedem Diff – egal, welches
Werkzeug schreibt.

### 1.2 Das Entwurfs-Paar: reines Generator-Gerüst (der neue, dauerhafte Fix)

```
📝 2026-10-19-urlaubskasse-clever-aufbessern ↔ 2026-11-06-guenstige-fluege:
   5 gleiche 7-Wort-Phrasen – Rest ohne Strukturzeilen: 0
```

Alle fünf Phrasen stammen aus **zwei Zeilen**, die kein Redakteur geschrieben
hat, sondern die Generatoren vorschreiben (`claude_writer.py`,
`poppy_repurpose.py`):

```
## Häufige Fehler und wie du sie vermeidest
| Fehler | Warum er teuer wird | Wie du ihn vermeidest |
```

Stehen Überschrift und Tabellenkopf hintereinander, ergeben sie allein exakt
`KRITISCH_AB = 5` Phrasen. Zehn Bestandsartikel tragen diese Überschrift –
jeder künftige Artikel aus denselben Generatoren hätte den Befund erneut
erzeugt. Das ist die Bauart von #766 („der Heiler schreibt den Massensatz"),
nur eine Ebene früher: diesmal schrieb ihn der **Generator**.

## 2. Dauerheilung (drei Ebenen, eine Messung)

Alle Ebenen nutzen dieselbe Messung aus `check_uniqueness`
(`clean_body`, `ngrams`, `KRITISCH_AB`). Keine neue Schwelle, kein
Stummschalten, keine Allow-List für Artikel.

### 2.1 Quelle abgestellt – die Generatoren

- `claude_writer.py` / `poppy_repurpose.py`: Die Strukturvorgabe verlangt
  jetzt eine **themenspezifische** Fehler-Überschrift und einen
  themenspezifischen Tabellenkopf; das Offline-Gerüst trägt das Thema bereits
  in der Überschrift. Das generische Gerüst wird nie wieder vorgeschrieben.

### 2.2 Automatische Selbstheilung – `einzigartigkeit_struktur_heiler.py`

Neuer deterministischer Heiler (kein KI-Rewriting, keine Prosa-Erfindung):

- **Diagnose statt Verdacht:** Ein Paar ist nur dann „Struktur", wenn die
  Überlappung nach Entfernen der registrierten Strukturzeilen aus beiden
  Texten unter `KRITISCH_AB` fällt (Nachweis am Echtbefund: 5 → 0).
  Bleibt echte Prosa-Dopplung übrig, meldet er sie nur – geheilt wird nichts
  (Freibrief-Schutz, Selbsttest Fall 3).
- **Heilung aus audit-sicherem Pool:** 8 Überschriften-/Tabellenkopf-
  Varianten, paarweise und gegen das Original unter der Schwelle bewiesen
  (Selbsttest Fall 2, Muster des Faustregel-Pools aus #766). Gewählt wird
  die erste Variante, die gegen den **gesamten Bestand** sicher ist; die
  Nachmessung läuft vor dem Schreiben in-memory – schlägt sie fehl, bleibt
  die Datei unverändert.
- **Schutzregeln:** Geheilt wird der jüngere/nicht-live Artikel. Live nur
  mit `--auch-live`, versiegelte Artikel (`inhalt_sha256`) nie. Jede Heilung
  wird in `data/einzigartigkeit_struktur_history.jsonl` protokolliert.
  Idempotent (zweiter `--fix`-Lauf: 0 Heilungen).
- **Sabotage-Schutz:** 8 eingefrorene Selbsttest-Fälle (Erkennung,
  Pool-Sicherheit, Freibrief-Schutz, Live-/Siegel-Schutz, Leerzeilen-Treue)
  laufen vor jedem Einsatz; Rot = Exit 2.

### 2.3 Verdrahtung – Selbstheilung in der täglichen Visite

`blog-health-daily.yml`: `--selftest` + `--fix` laufen jetzt **vor** dem
Einzigartigkeits-Audit (im selben, bereits committenden Tageslauf wie
Duplikat-Wache und Keyword-Gate). Ablauf: Heiler heilt → Audit misst den
geheilten Bestand → der bestehende Issue-Lifecycle
(`uniqueness_issue_sync.py`) kommentiert/schließt #1099 beim nächsten
sauberen Lauf automatisch. Vertragstests frieren die Reihenfolge ein.

### 2.4 Bestandsheilung (einmalig, nachvollziehbar)

`2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden` (Entwurf, jüngerer
Artikel des Paares): Überschrift → „Diese Fehler kosten dich unnötig Geld –
so vermeidest du sie", Tabellenkopf → „Stolperfalle | Was sie dich kostet |
So gehst du ihr aus dem Weg". Kein Fließtext geändert, kein Siegel berührt
(Artikel trägt kein `inhalt_sha256`). Protokoll:
`data/einzigartigkeit_struktur_history.jsonl` (1 Eintrag).

## 3. Was bewusst NICHT passiert ist

- **Keine Schwellenänderung:** `KRITISCH_AB = 5`, 7-Gramm-Messung und die
  28 verbleibenden unkritischen Standard-Formulierungen bleiben sichtbar.
- **Kein Auto-Rewriting von Prosa:** Echte Dopplung bleibt Redaktionsarbeit;
  der Heiler ersetzt ausschließlich zwei registrierte Strukturzeilen.
- **Keine Allow-List:** Die generische Überschrift wird nicht aus der
  Messung ausgenommen – sie wird ersetzt bzw. gar nicht mehr erzeugt.
  Zehn Alt-Artikel mit der Überschrift allein (je 1 Phrase) bleiben unter
  der Schwelle und unverändert; rückt einer je an einen Zwilling heran,
  heilt der Heiler in der nächsten Visite.

## 4. Beweise

```
python3 scripts/einzigartigkeit_struktur_heiler.py --selftest   # ✅ 8 Fälle
python3 scripts/einzigartigkeit_struktur_heiler.py              # 🧱 STRUKTUR 5 (Rest: 0)
python3 scripts/einzigartigkeit_struktur_heiler.py --fix        # 🩹 1 geheilt, nachher: 0
python3 scripts/einzigartigkeit_struktur_heiler.py --fix        # idempotent: 0 geheilt
python3 scripts/check_uniqueness.py
  → Pin: 0 | Kritisch (live↔live): 0 | Nicht-Live-Paare: 0 | Same-Day-Twins: 0 · ✅ bestanden
python3 scripts/bestand_einzigartigkeit_gate.py --basis HEAD    # ✅ keine NEUE Überlappung
python3 scripts/governance_contract.py                          # 🔒 46 Regeln erfüllt
python3 scripts/integrity_guard.py                              # 🎉 Kern signiert
python3 -m unittest scripts.tests.test_einzigartigkeit_struktur_heiler \
                    scripts.tests.test_check_uniqueness \
                    scripts.tests.test_uniqueness_workflow_contract \
                    scripts.tests.test_einzigartigkeit_bestand  # 24 Tests OK
```

## 5. Dateien

- `scripts/einzigartigkeit_struktur_heiler.py` (neu) – Diagnose, Pool,
  Heilung, History, 8 Selbsttest-Fälle
- `scripts/claude_writer.py`, `scripts/poppy_repurpose.py` – Generatoren
  schreiben das generische Gerüst nicht mehr vor
- `scripts/tests/test_einzigartigkeit_struktur_heiler.py` (neu) – 6
  Vertragstests inkl. Bestands-Sweep und Workflow-Reihenfolge
- `.github/workflows/blog-health-daily.yml` – Heiler vor dem Audit
- `content/posts/2026-11-06-guenstige-fluege…/index.md` – 1 Entwurfsartikel
  geheilt (nur Überschrift + Tabellenkopf)
- `data/einzigartigkeit_struktur_history.jsonl` – Heilungsprotokoll
- dieser Bericht

Der Vorgang #1099 wird vom nächsten sauberen Produktionslauf automatisch
kommentiert und geschlossen (`uniqueness_issue_sync.py`); der Pull Request
trägt `Closes #1099` für den Abschlussvermerk.
