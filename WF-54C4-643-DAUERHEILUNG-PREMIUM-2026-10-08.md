# Veröffentlichung WF-54C4 · #643 – Dauerheilung

**Datum:** 08.10.2026
**Auslöser:** Der Deploy-Lauf **37755044113** (Push `11e65ea7`, 08.10.2026
09:12:29Z) starb im Schritt **„Build (für Publish-Gate + Publish)“** – der
Auto-Alert meldete das als Issue **#643** (`auto-report`, Alert-Key `WF-54C4`,
Bereich *Veröffentlichung*). Der jüngste rote Lauf ist 37757217250 auf
`654bda4`; die Job-Logs sind aus dieser Umgebung nicht abrufbar, die
Fehlerzeile steht dafür als Annotation an der Sache selbst (Check-Run
`113244890131`).

## Befund

### 1. Der Bau-Abbruch: ein doppelter Mapping-Schlüssel

    error building site: assemble: failed to create page from pageMetaSource
    /posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust:
    "content/posts/2026-10-07-campingurlaub-…/index.md:9:1":
    [8:1] mapping key "tags" already defined at [7:1]

Hugo liest Frontmatter mit **go-yaml** – und go-yaml bricht bei einem
wiederholten Mapping-Schlüssel **hart** ab. Der gesamte Build stirbt daran,
also auch Publish-Gate, Publish, Anker-Wache und Vorlesen: „ohne
Gate-Report, ohne verwertbares Alert, nur ein toter Deploy“ – genau die
Klasse, die das Frontmatter-Gate (#610-Nachbarschaft, deploy.yml:498) schon
einmal beschrieben hat.

**Fünf** Reserve-Artikel trugen je einen doppelten Schlüssel
(`content/posts/2026-10-07-<slug>/index.md`, alle `draft: true`+`reserve: true`):

| Datei (Slug) | doppelter Schlüssel |
|---|---|
| `campingurlaub-2026-clever-sparen-ohne-komfortverlust` | `tags` Z. 8 ← 7 (`["Campingurlaub","Reisekosten","Urlaub planen"]` vs. `["Mietwagen und Wohnmobil","Reisekosten sparen"]`) **und** `cover.image` Z. 25 ← 24 (`2026-10-06-…jpg` vs. `2026-10-07-…jpg`; beide Bilder liegen in `static/images/covers`) |
| `dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` | `tags` Z. 7 ← 6 |
| `handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` | `tags` Z. 7 ← 6 |
| `urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` | `tags` Z. 8 ← 7 |
| `wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` | `tags` Z. 8 ← 7 |

### 2. Warum alle Wachen grün waren

`yaml.safe_load` – und damit **jede** PyYAML-Prüfung im Haus (FM-Grenze,
Taxonomie, Publish-Gate, Publikationsvertrag) – akzeptiert doppelte
Schlüssel klaglos: der letzte Wert gewinnt. Die fünf Dateien parsten also
„sauber“, und der Deploy starb erst dort, wo niemand mehr heilen kann. Der
Punkt ist keine Hugo-Kuriosität, sondern eine **Blindstelle der Prüfmethode**:
Wer „der Block parst“ als „sauber“ liest, sieht diese Klasse nie.

### 3. Der Produzent

Die Doppel entstanden im **Merge von PR #634** (`654bda4 ← 11e65ea ← 149ea9a1`;
Zweig-Merges `7be5d47`/`028c4cd`), in dem beide `tags:`-Zeilen stehen blieben;
die Vorgänger-Referenzen tragen je genau eine Zeile (z. B. campingurlaub
`5b32db9` = `["Mietwagen und Wohnmobil", "Reisekosten sparen"]`, `24b8cc5` =
3-elementige Liste). Ein Merge ist kein Schreiber – deshalb reicht es nicht,
nur die fünf Dateien zu heilen; die **Klasse** braucht ein Gate, und die
Schreiber brauchen eine Schlussregel, die keinen zweiten Schlüssel hinterlässt.

### 4. Der zweite, verdeckte Blocker

Nach der FM-Heilung starb der Build an der **nächsten** Stelle – erst dort
sichtbar, weil Hugo am ersten Fehler stehen bleibt:

    render of "content/suche/index.md" failed: resources.Concat:
    resources in Concat must be of the same Media Type,
    got "text/javascript" and "application/javascript"

PR #644 hatte die neue Seite `/suche/` (`layout: search`) gebracht. Deren
`head.html`-Zweig baut den Fuse-Suchlauf per `js.Build` (Ergebnis:
`text/javascript`) und hängt ihn an rohe `.js`-Assets (in `hugo.toml` ist
`application/javascript` für `.js` registriert – wegen des Service-Worker-
Outputformats `SWJS`). Beide Welten trafen sich zum ersten Mal in **einem**
`resources.Concat` – und Hugo verlangt dort **einen** Typ. Ein Minimal-Repo
belegt es: `resources.Get`→`application/javascript`, `js.Build`→
`text/javascript`, `resources.FromString` auf ein `.js`-Ziel→
`application/javascript` (die Normalisierung, die den Typ wieder zusammenführt,
ohne Inhalt oder Reihenfolge zu ändern).

### 5. Umfeld (ehrlich abgegrenzt)

* Das **Integritäts-Siegel** stand bereits auf `main` auf rot: PR #644 hatte
  `hugo.toml` (KRITISCH) ohne Neu-Signatur geändert. Die Signatur war also
  ohnehin fällig und wird in diesem Vorgang mit erledigt.
* Weiter rot und **nicht** Teil dieses Vorgangs: `Klartext-Wache`,
  `gate`/`bot_watchdog` (`selftest_clock`-Klasse), `navigation`,
  `reserve_readiness.py` (Syntaxfehler → drei Reserve-Testmodule laden nicht),
  `reserve_recert`, `test_workflow_yaml`. Alle sind als **Vorzustand**
  belegt (Vergleichslauf auf einem Worktree von `654bda4`) und nicht von
  diesem Vorgang erzeugt oder verschlechtert.

## Dauerhafte Reparatur

**1. Die Klasse ist jetzt eine Regel der Wache (F7).**
`scripts/fm_boundary_guard.py` scannt das Frontmatter **zeilenweise** über die
Mapping-Ebenen (`doppelte_schluessel`): derselbe Schlüssel zweimal auf
derselben Ebene – top-level **und** verschachtelt (`cover.image`) – ist
baukritisch. Sequenzeinträge (`quellen: - id: "Q1"`) sind eigene Container,
Block-Skalare (`|`/`>`) sind Inhalt: beides bleibt ruhig. **Wichtig:** die
Prüfung läuft **vor** dem PyYAML-Kurzschluss (`inspect_text`) – sonst wäre
genau dieser Fall für immer unsichtbar.

**2. Die Heilung ist verlustfrei und belegt.**
`heile_doppelte` vereinigt Listen (kein Element geht verloren) und folgt sonst
der YAML-Leseregel: der letzte Wert bleibt, das frühere Vorkommen fällt weg –
**jede** Änderung und jeder verworfene Wert stehen im `FM-GRENZEN-REPORT.md`.
Die Heilung läuft von unten nach oben (stabile Indizes), ist idempotent und
schreibt nur, wenn sie verbessert (`ok=False` → nichts wird angefasst).
Redaktionelle Autorität bleibt beim Register: direkt nach dem FM-Gate
kanonisiert `tag_governance.py --apply` die Tags (deploy.yml, gleicher Lauf).

**3. Verdrahtung – heilen VOR dem Build, prüfen im PR.**
Kein neuer Workflow nötig: die Wache läuft in `deploy.yml` bereits
selbstheilend **vor** dem Build (`--fix`, deploy.yml:512) und fail-closed im
PR (`publication-reliability-tests.yml`, `--check`), dazu als erster Schritt
der Content-Engine (`content-engine-v2.yml:188`). Ein Rückfall heilt damit im
selben Lauf, statt den Deploy zu töten. Neu: `--staged` prüft die **Blobs aus
dem Index** (nicht den Arbeitsbaum) und `--wirkungsprobe` beweist die Klasse
am Fixture (Erkennen, verlustfreies Heilen, Fixpunkt).

**4. Die Schreiber-Schlussregel (eine Regel, kein zweiter Schlüssel).**
`post_utils.doppel_freies_feld` ist die gemeinsame Schlussregel: nach dem
Schreiben existiert der Schlüssel genau einmal (Blockliste eines Duplikats
inklusive). `keyword_optimizer.fm_set/fm_set_list`, `tag_governance.
schreibe_feld` und `pinterest_pin_text_sync.fm_set` enden damit – ein Heiler
mit `count=1` hätte die Falle sonst nur **unsichtbar** gemacht.

**5. Der Vertrag (C32).**
`governance_contract.py` friert C32 ein: Wache vorhanden, F7 **vor** dem
Kurzschluss, Heilen **vor** dem Build, fail-closed im PR, Schreiber-Regel in
jedem FM-Schreiber – plus **lebende** Wirkung (`--selftest` **und**
`--wirkungsprobe` JETZT grün). Fünf Kunstbefunde werden im
Kontrakt-Selbsttest rot, der echte Baum bleibt still. (Haus-Nummern: C24 ist
die C24 Bank, C31 der Robustheits-Vertrag – C32 ist darum frei.) Dazu der
CLAUDE.md-Abschnitt und `docs/GOVERNANCE-KONTRAKT.md` (regeneriert).

**6. Bestand geheilt, Build-Pfad wieder frei.**
Die fünf Artikel sind geheilt (doppelter Schlüssel entfernt; beim Campingurlaub
gilt das Bild vom 07.10., beide Bilder liegen im Bestand) und durch das
Taxonomie-Gate kanonisiert. Der zweite Blocker ist an der Wurzel behoben:
`head.html` normalisiert das `js.Build`-Ergebnis auf den registrierten
`.js`-Medientyp, bevor konkateniert wird (`resources.FromString`) – gleicher
Inhalt, gleiche Reihenfolge, gleiches Fingerprint-/Integrity-Verhalten.
`head.html` ist **KRITISCH** versiegelt; die Änderung ist deshalb mit
`integrity_guard.py --set-current` signiert (Akte im Lock; dieselbe Signatur
nimmt die offene `hugo.toml`-Drift aus #644 mit).

**7. Regressionen, die die Klasse halten.**
`scripts/tests/test_fm_boundaries.py`: 7 neue F7-Tests (erkennen ohne
Schreiben, Vereinigung, YAML-Leseregel, Blocklisten, Index-Blob-Pfad,
Verschachtelung/Skalar-Schutz, Klassen-Wächter über den **echten** Bestand)
und 7 Schreiber-Tests (SSOT-Regel, drei Schreiber, Idempotenz über den ganzen
Bestand).

## Nachweis

* `python3 scripts/fm_boundary_guard.py --check` → **grün**: „FM-Grenzen
  sauber (108 Dateien) – Grenzen stehen allein, kein Schlüssel doppelt …“.
* `python3 scripts/fm_boundary_guard.py --selftest` → grün, u. a.
  „18 Wert-Fälle + 4 Grenz-Fälle + F7-Doppelschlüssel (erkennen, vereinigen,
  YAML-Leseregel, Sequenz-/Skalar-Schutz) …“.
* `python3 scripts/fm_boundary_guard.py --wirkungsprobe` → „F7 erkannt (tags +
  cover.image), verlustfrei geheilt (5 Tags vereinigt, letztes Bild gilt),
  Body bytegleich, Sequenzlisten unberührt, zweiter Lauf ein Fixpunkt“.
* `python3 scripts/fm_boundary_guard.py --staged` → grün über die gestageten
  Content-Dateien („dieser Commit kann den Hugo-Build nicht am Frontmatter
  töten“).
* `hugo --minify` (Extended v0.164.0) → **rc=0, 80 Seiten** – der Build, an dem
  der Produktions-Deploy starb, läuft wieder; `/suche/` rendert mit
  fingerprintedem `assets/js/search.…js` (+ `integrity`), `sw.js` unverändert.
* `python3 scripts/tag_governance.py --check` → „✓ Taxonomie sauber“;
  `--selftest` → 23/23.
* `python3 scripts/governance_contract.py --selftest` → **bestanden
  (C1–C32 …)**; `--quick --md docs/GOVERNANCE-KONTRAKT.md` → „alle 30 Regeln
  prüfen in beide Richtungen“, Dokument neu erzeugt.
* `python3 scripts/integrity_guard.py --gate` → **Exit 0** (Siegel rein,
  Signatur mit Akte im Lock); `--selftest` → grün.
* `python3 -m unittest scripts.tests.test_fm_boundaries` → **Ran 35, OK**
  (14 neue Tests).
* `python3 -m unittest discover -s scripts/tests` → **Ran 2067**. Es bleiben
  7 Fehler + 5 Fehler(Setup), **identisch zum Vorzustand**: derselbe Lauf auf
  einem Worktree von `654bda4` (ohne diese Änderungen) liefert exakt dieselben
  zwölf Einträge (`reserve_readiness.py`-Syntaxfehler → 3 Lade-Fehler,
  Klartext-Wache 2, `reserve_recert` 1, `test_workflow_yaml` 3,
  `publication_reliability` 1, `command_execution_security` 1,
  `test_integrity_guard` 1 = das ohnehin offene Siegel). Diese Änderung
  erzeugt **keinen** neuen roten Test – und keiner dieser Fälle wird hier
  „grün geredet“.
* Pull Request: Branch `arena/07a63207-franksfinanzcheck-blog`, Text mit
  `Closes #643`. Der Abschluss-Vermerk am Issue setzt `vorgangs-abschluss.yml`
  (Hausregel: nie von Hand).

**Ergebnis:** Der Deploy kann an einem doppelten Mapping-Schlüssel nicht mehr
sterben – er wird vor dem Build erkannt und verlustfrei geheilt, im PR
fail-closed gemeldet, von keinem Schreiber mehr erzeugt und von Vertrag C32
dauerhaft bewacht. Der zweite, verdeckte Blocker (Medientyp im Suchlauf) ist
an der Wurzel behoben und der Build lokal bewiesen grün. Keine Prüfung wurde
abgeschwächt, nichts rückdatiert; die im Vorzustand offenen Nachbar-Baustellen
sind benannt und bleiben sichtbar.
