# FM-GRENZEN: Frontmatter-Quote repariert — Deploy-Bau war 3× tot (11.09.2026)

**Stand: 11.09.2026 · FranksFinanzcheck Bau-Infrastruktur · Root-Case: `hugo --minify`**

## 1 · Befund

`main` baute nicht mehr. Drei Deploy-Läufe in Folge starben nach 21–28 s im
Schritt **„Build (für Publish-Gate + Publish)"** (`hugo --minify`, Exit 1) –
und es sind inzwischen fünf, auf zwei verschiedenen Ständen:

| Run | head | Ergebnis |
|---|---|---|
| 34587113270 | `abfc359` | ✅ grün (23 m 15 s) — **letzter grüner Anker** |
| 34594479696 | `8e2a191` | ❌ failure · Build (15/29) |
| 34597633413 | `a8bb574` | ❌ failure · Build |
| 34598288171 | `3468217` | ❌ failure · Build (aktualisierter Stand) |
| 34611135439 · 34611158526 | `ccf1b29` | ❌ failure · Build — **main ist weiterhin rot** (11.09., 51 min nach den ersten Läufen; Bot-Commits ändern die FM-Zeile nicht) |

Hugo-Meldung (identisch in allen drei Läufen, hier lokal reproduziert):

```
ERROR error building site: assemble: failed to create page from pageMetaSource
/posts/2026-09-11-reisekasse-fuellen-praxistipps-fuer-dein-urlaubsbudget:
"[14:27] invalid header option: \" Der Traumurlaub scheitert am Budget? …\""
```

**Warum das so teuer ist:** Ein Frontmatter-Fehler ist die einzige Fehlerklasse,
die den Build **hart** beendet. Damit sterben alle nachgelagerten Stufen mit —
Spam-Gate, Publish-Gate, Anker-Wache, Vorlesen, Publish und Deploy-Catchup.
Es gibt keinen Report und kein verwertbares Alert, nur einen toten Build; die
Publizierkette (RSS → Pinterest) trocknet still aus.

## 2 · Ursache (eine Lücke in einer Funktion)

`content/posts/2026-09-11-reisekasse-fuellen-praxistipps-fuer-dein-urlaubsbudget/index.md:15`

```yaml
pin_description: *Werbung | Der Traumurlaub scheitert am Budget? …
```

Seit 31.08.2026 tragen alle Pin-Texte den UWG-Prefix `*Werbung |`
(Pinterest Ad-Policy, `clean_pin_description()`). In YAML eröffnet `*` jedoch
einen **Alias** → der Wert ist kein Plain-Scalar mehr → das Frontmatter ist
unparsbar.

Geschrieben hat die Zeile `scripts/engine_generate.py::yaml_quote()`. Ihre
Regel lautete: quotieren, wenn `":"` im Wert vorkommt, `#`, oder der Wert mit
`" "`, `-`, `?`, `!` beginnt. Ein `*` am Anfang war **nicht** dabei, und der
Text hatte kein `": "` — der Fall rutschte durchs Raster und wurde als
„gültig" in das Frontmatter geschrieben (Commit `85fdee4`, Content-Engine).

## 3 · Reparatur (drei Ebenen, eine Regel)

| Ebene | Datei | Was |
|---|---|---|
| **Bestand** | `content/posts/2026-09-11-reisekasse-…/index.md` | Wert gequotet — Text bytegleich, nur `"…"` herum (`--fix` der Wache, kein manueller Eingriff) |
| **Regel** | `scripts/engine_generate.py::yaml_quote()` | delegiert an `fm_boundary_guard.needs_quote/yaml_quote` → **eine** Wahrheit für Generator und Gate; deckt jetzt die komplette YAML-Indicator-Menge ab (`* & ! @ \` \| > % [ ] { } " ' # , - ? :`), Rand-Leerzeichen, `": "`, `":"` am Ende, ` #` und Umbrüche (mit Backslash-Escaping) |
| **Gate** | `scripts/fm_boundary_guard.py` (neu) + `deploy.yml` + `content-engine-v2.yml` | harte FM-Grenzen-Wache **vor** `hugo --minify` und **vor** jedem Engine-Publish — selbstheilend, konvergent, mit `--selftest` als Sabotage-Schutz |
| **Test** | `scripts/tests/test_fm_boundaries.py` (neu, 11 Fälle) + `publication-reliability-tests.yml` | `--selftest` **und** `--check` laufen jetzt bei jedem PR, der `scripts/**` oder Workflows ändert (42/42 grün) — die Klasse ist damit dauerhaft zugemauert |

**Prüfprinzip der Wache** (bewusst anders als die Text-Wachen): der ganze
Frontmatter-**Block** wird geparst — Hugo-Sicht. Parst er, ist Ruhe. Deshalb
meldet die Wache legale Konstrukte wie
`tags: ["Energie-Update: was sich jetzt ändert", …]` **nicht** (ein frührer
Entwurf der Regelkette hätte diese Liste zu einem String gemacht — genau die
Regression, die der Block-Parse ausschließt). Gefunden und gemeldet werden:
F1 Grenze oben, F2 Grenze unten, F3 Block/Zeile nicht YAML-parbar,
F4 Quote/Flow nicht geschlossen. Geheilt wird **nur**, wenn der Block nach der
Heilung nachweislich parst — sonst bleibt die Datei unangetastet.

**Hugo-Semantik gespiegelt:** Hugo schließt das Frontmatter an der *ersten* Zeile ab
Index 1, die mit `---` **beginnt** — auch wenn der erste Absatz anklebt
(`---Warum zahlen Millionen …`). Die Wache mirrornt das (Präfix statt
Volltreffer) und meldet solche Kleber nur als Hinweis: 11 Dateien, zuständig
ist die Umbruch-/Casing-Wache (`casing_guard.py --split-headglue`), **kein**
Eingriff hier.

## 4 · Verifikationsanker

Lokal in der Sandbox, mit **derselben Hugo-Version wie der CI** (0.164.0
extended — aus dem PyPI-Zweig der `install-hugo`-Action, weil der
Release-Asset-Host aus der Sandbox blockiert ist):

```
$ hugo version
hugo v0.164.0-…+extended+withdeploy linux/amd64 … VendorInfo=hugo-python-distributions

$ python3 scripts/fm_boundary_guard.py --selftest
✅ FM-Grenzen-Selbsttest: 18 Wert-Fälle + 4 Grenz-Fälle + Kleber/Quote/Schema-Schutz grün (inkl. Regression '*Werbung |').
EXIT=0

$ python3 -m unittest discover -s scripts/tests      # inkl. 11 neuer FM-Fälle
Ran 42 tests · OK
EXIT=0

$ python3 scripts/fm_boundary_guard.py --check          # Bestand (geheilt)
✅ FM-Grenzen sauber (59 Dateien, 11 Kleber-Hinweis(e) gemeldet) – der Build kann am Frontmatter nicht mehr sterben.
EXIT=0

$ python3 scripts/fm_boundary_guard.py --check          # Bestand (zurückgedreht, 1 kaputte Zeile)
⚠ FM-Grenze F3: content/posts/2026-09-11-reisekasse-…/index.md – Zeile ist kein gültiges Top-Level-YAML-Paar – Hugo verliert hier das Frontmatter
❌ 1 baukritische(r) FM-Fund/Funde (--fix heilt deterministisch). Report: FM-GRENZEN-REPORT.md
EXIT=1

$ hugo --minify   (nach --fix)
Pages 257 · Paginator pages 9 · Static files 877 · Aliases 106 · Total in 1199 ms
EXIT=0     ← vorher: EXIT=1 mit "invalid header option"
```

**A/B-Gegenprobe im selben Arbeitsverzeichnis** (beweist Ursache UND Wirkung,
Hugo 0.164.0 extended = CI-Version, PyPI-Zweig der `install-hugo`-Action, weil
der Release-Asset-Host aus der Sandbox blockiert ist):

```
$ git worktree add /tmp/maincheck ccf1b29          ← main, unverändert
ERROR error building site: assemble: failed to create page from pageMetaSource
/posts/2026-09-11-reisekasse-…: "index.md:15:27": [14:27] invalid header option:
" Der Traumurlaub scheitert am Budget? …"
MAIN_HUGO_EXIT=1

$ git checkout arena/01a090ba-franksfinanzcheck-blog   ← main + Reparatur
Pages 257 · Total in 1199 ms
HUGO_EXIT=0
```

Der einzige inhaltliche Unterschied zwischen rot und grün ist **eine
Zeile**: der Wert von `pin_description` steht in Guillemets.

**Anker-Set (identische Prüfreihenfolge nach dem Merge):**

1. Deploy-Run auf `main` zeigt die zwei neuen Schritte **grün**:
   `FM-Grenzen-Selbsttest (Wache muss lauffähig sein, sonst kein Build)` und
   `FM-Gate (Frontmatter-Grenzen – selbstheilend, VOR dem Build)` — direkt vor
   `Build (für Publish-Gate + Publish)`.
2. `Build` endet mit `Pages │ 257` (± Artikelzahl des Tages) statt
   `invalid header option`; alle Stufen nach dem Build laufen wieder an.
3. Der Anker-Fallback, falls CI-Logs wieder nicht abrufbar sind (wie am
   11.09. beobachtet: Log-Host `productionresultssa*.blob.core.windows.net`
   lieferte `EOF`): `SELFTEST_EXIT=0` + `CHECK_EXIT=0` + `HUGO_EXIT=0`.

## 5 · Stand der Dinge und Dubletten-Frage

**`ddab74d` ist nicht auf GitHub.** Nach der (wieder funktionierenden)
GitHub-Verbindung geprüft: `gh api repos/…/commits/ddab74d` → 422 „No commit
found for SHA", `git ls-remote origin` → `arena/01a09045-franksfinanzcheck-blog`
steht unverändert auf `081d4ff`. Der Commit lebt ausschließlich in der Sandbox
der Parallel-Session – von hier weder pushbar noch verifizierbar.

**Diese Session hat die Bau-Ursache deshalb selbst gefunden, repariert und
A/B-verifiziert.** Ein Commit auf `arena/01a090ba-franksfinanzcheck-blog`,
frisch auf das aktuelle `main` (`ccf1b29`) gesetzt, Betreff
`fix(fm): FM-Grenzen repariert – Build-Ursache + harte Vor-Bau-Wache`. Der Hash
wird hier bewusst nicht zitiert (jedes Amendieren würde die Aussage des Reports
verändern) – die Wahrheit ist

    git log -1 --format=%H arena/01a090ba-franksfinanzcheck-blog

**Dubletten-Frage:** Die Content-Zeile ist in beiden Varianten derselbe
Zustand (Wert in Guillemets, Text bytegleich) → der Merge ist idempotent,
egal welche Fassung zuerst in `main` landet. Zu prüfen bleibt nur, ob
`ddab74d` eigenen Gate-Code mitbringt; dann eine Wache behalten und die
andere auf Regressionstests reduzieren (beide `--selftest`-Paare laufen
schon jetzt in `publication-reliability-tests.yml`).

**Rollenaufteilung:** Reparatur dieser Session →
`arena/01a090ba-franksfinanzcheck-blog` (gepushen), `ddab74d` →
`arena/01a09045-franksfinanzcheck-blog` (nur aus deren Sandbox möglich). Für `main` genügt einer der beiden – der
zweite ist dann ein leerer Merge.

---
_Report der Wache: `FM-GRENZEN-REPORT.md` (läuft bei jedem Deploy und bei jedem
Engine-Slot mit)._
