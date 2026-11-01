# claude-seo: 26 Skills mit eigener Runtime aufgenommen (Highend, 01.11.2026)

> Auftrag: `npx skills add AgriciDaniel/claude-seo`. Runbook und dauerhafte
> Ablage: `docs/ANLEITUNG-SKILLS.md`, Abschnitt „Im Bestand: `claude-seo`".
> Wache: `python3 scripts/skills_vertrag.py` (K1–K8).

## Ausgangslage (gemessen, nicht geschätzt)

| Befund | Wert am 01.11.2026 |
|---|---|
| Skills vor der Aufnahme | 25 (6 `ff-*`, 19 fremd) |
| Upstream-Paket | 26 Skills, 194 Dateien, 811 KB |
| Namenskollision | `seo-audit` existierte bereits (`coreyhaines31/marketingskills`, MIT) |
| Skills mit `${CLAUDE_PLUGIN_ROOT}`-Aufruf | 19 von 26 |
| Vom `skills`-CLI mitgelieferte Runtime | **keine** – der CLI kopiert nur den Skill-Ordner |
| Bestandslage der Wache vor dem Eingriff | **1 Befund**: `.claude/skills/animate` ohne Lizenztext und ohne Registerzeile |

Entscheidung des Betreibers vor der Ausführung: **alle 26 inklusive Runtime**,
und `seo-audit` geht von `coreyhaines31` an `claude-seo` über. Beides ist unten
umgesetzt; ohne die zweite Entscheidung wäre ein `--skill '*'` stillschweigend
zur Herkunftsfälschung geworden.

## Was jetzt im Repo liegt

```
.claude/skills/seo/          Hub + Runtime (241 Dateien, 1,3 MB)
  SKILL.md                   325 Zeilen · 17 references
  scripts/                   61 Dateien (60 .py + Launcher) · 1,1 MB
  schema/templates.json
  data/google-updates.json
  hooks/                     3 Dateien (hooks.json, run-validator, validate-schema.py)
  requirements.txt
  LICENSE.txt                MIT-Volltext
.claude/skills/seo-*/        25 Unterskills (SKILL.md + references/ + LICENSE.txt)
```

Aufnahmeumfang: **252 neue Dateien** (241 im Hub, 11 in den 25 Unterskills
zuzüglich Lizenz- und Referenzdateien). Upstream-Stand: `claude-seo` 2.5.0,
Commit `6be93f4`, abgerufen am 01.11.2026.

## Drei Entscheidungen, die man nicht raten kann

1. **Runtime in den Hub-Ordner, nicht nach `scripts/`.** `runtime.py` löst seinen
   Wurzelpfad als `Path(__file__).parent.parent` auf und erwartet `schema/` und
   `data/` als Geschwister von `scripts/`. Genau das Layout baut auch das
   Upstream-`install.sh`. Ein Ablegen unter dem Repo-`scripts/` hätte die
   mitgelieferten 60 Python-Dateien in den Wachen-Vertrag gezogen und die
   Pfadauflösung gebrochen.
2. **`${CLAUDE_PLUGIN_ROOT}` auf den Repo-Pfad umgeschrieben.** Außerhalb eines
   Plugins ist die Variable leer; die Skills hätten Befehle auf einen nicht
   existierenden Pfad geschickt (K5-Klasse „Schritt ohne Erzeuger"). Ersetzt in
   32 `.md`-Dateien (151 Token), Reihenfolge längste Form zuerst:
   `scripts/claude-seo` → `.claude/skills/seo/scripts/claude-seo`,
   `skills/` → `.claude/skills/`, `hooks|schema|data/` → `.claude/skills/seo/…`.
   Der Absatz „Runtime" im Hub-`SKILL.md` beschreibt jetzt dieses Layout statt
   der Plugin-Variable. Python-Quellen bleiben unberührt – dort steht der Token
   nur in Docstrings, und `runtime.py` liest die Umgebungsvariable bewusst.
3. **Lizenz: Volltext statt Zeiger.** Upstream legt je Skill 143 Bytes ab („MIT
   License – see repository root LICENSE file"), fünf Ordner ganz ohne. Ein
   Verweis führt die Permission Notice nicht mit, die MIT für jede Kopie
   verlangt. In allen 26 Ordnern liegt deshalb der **unveränderte** MIT-Volltext
   der Root-Lizenz (1.069 Bytes), ergänzt um 5 fehlende Dateien.

## Kosten (die Zahl, die bleibt)

| Posten | Wert |
|---|---|
| Beschreibungen der 26 Skills, ab jetzt bei **jedem** Agenten-Start | ≈ **2.039 Tokens** |
| Bisheriger Bestand (18 Skills) | ≈ 3.335 Tokens |
| Neue Dauerlast | ≈ 5.374 Tokens (**+61 %**) |
| Versionierter Zuwachs | 1,3 MB, 252 Dateien |
| Python-Abhängigkeiten (nicht installiert, nicht versioniert) | Playwright, WeasyPrint, google-api-*, Pillow 13 |

Die Dauerlast ist der eigentliche Preis, nicht die Megabyte. Sie wird in
`ff-*`-Sprache nirgends „kostenlos" genannt.

## Nebenbefunde (belegt, nicht vermutet)

### `npx skills check` schreibt – es prüft nicht

Der Befehl steht im Runbook als Prüfschritt. Tatsächlich hat er **zehn
vorhandene Skills aktualisiert**, `agent-reach` durch einen Symlink nach
`.agents/skills/` ersetzt, `agent/skills/` und `data/skills/` angelegt und zehn
`computedHash`-Werte in `skills-lock.json` neu geschrieben. Dieses Repo
versioniert echte Ordner mit inline-`LICENSE.txt`, keine Symlink-Farm; der Lauf
wurde deshalb **vollständig zurückgerollt**:

* `git checkout -- .claude/skills` (echte Ordner statt Symlink),
* `rm -rf .agents agent data/skills`,
* die zehn Lock-Hashes zurück auf den HEAD-Stand (CLI-geschriebene Werte, keine
  erfundenen Hashes) – `git diff skills-lock.json` enthält danach nur noch
  `claude-seo`-Einträge.

Lehre, im Runbook hinterlegt: `check` ist ein Update. Wer nur aufnehmen will,
nutzt `add … --skill '*' -a claude-code -y`.

### Der Bestandsbefund ist geheilt, nicht zugedeckt

`.claude/skills/animate` stand im Lock (`emilkowalski/skills`), hatte aber weder
`LICENSE.txt` noch Registerzeile – K6 meldete das bei jedem Lauf und blockierte
damit die Abnahme dieser Arbeit. Das Upstream führt eine MIT-Lizenz; der
unveränderte Volltext (1.070 Bytes) liegt jetzt im Ordner, das Register führt
`quelle` und `lizenz`. Die Wache steht dadurch auf **0 Befunde**.

### Offen und absichtlich offen: der Siegelstand (K8)

`scripts/skills_vertrag.py` und `data/skill_lizenzen.json` stehen weder in
`KRITISCH`/`FEST` noch im Integritätsschloss. Das war vorher so und bleibt so:
Zeichnen ist ein Betreiberakt (`integrity_guard.py --set-current`), kein
Agentenschritt. K8 meldet es als Warnung, nie als Befund – wie vorgesehen.

### Nicht getan: Python-Umgebung

Der Runtime-Code liegt bei, die Abhängigkeiten sind **nicht** installiert und
nicht versioniert (Playwright-Browser, WeasyPrint-Systemlibs). Das ist der
Upstream-Weg: `.claude/skills/seo/scripts/claude-seo setup` baut die venv
lokal. Ohne sie laufen Analyse-Skills, die reines Modellwissen nutzen, weiter;
die messenden Skripte (PageSpeed, GSC, Agentic-Lighthouse) erst nach `setup`.

## Nachweis (lokal, 01.11.2026)

```
python3 scripts/skills_vertrag.py            ✅ 50 Skills, 0 Befunde, 2 Warnungen (K8, Bestand)
python3 scripts/skills_vertrag.py --selftest  ✅ Sabotage-Fälle grün
python3 scripts/redos_guard.py               ✅ 704 Python-Dateien, 0 Funde
python3 scripts/skript_syntax_wache.py       ✅ 623 Dateien grün
python3 scripts/wachen_vertrag.py            ✅ 370 Skripte, 0 Funde
python3 scripts/fremdmessung_sperre.py       ✅ keine Spur
python3 scripts/manifest_guard.py            ✅ GRÜN (13 Manifeste)
```

Die beiden Fremd-Code-Wachen haben ihren Prüfumfang durch diese Aufnahme
erweitert (REDOS 634 → 704, Syntax unverändert 623, weil `.claude` dort nicht
im Korb liegt) und bleiben grün – die 60 Upstream-Skripte sind also kein
blinder Fleck, sie sind geprüft.

## Nachlauf nach jedem `npx skills update`

Der CLI kennt die beiden Eingriffe unten nicht und kopiert wieder den
Upstream-Stand: die Plugin-Variable kehrt zurück, die Lizenzdateien werden
wieder Zeiger. Dafür liegt ein Erzeuger im Repo – keine Prosa-Anleitung:

```bash
python3 tools/nachlauf_claude_seo_pfade.py            # schreiben
python3 tools/nachlauf_claude_seo_pfade.py --check    # nur melden (Exit 1 bei Plugin-Token)
python3 scripts/skills_vertrag.py                     # Vertrag
```

Das Skript ist idempotent (zweiter Lauf: „0 Dokument(e) umgeschrieben · 0
Lizenztext(e) gesetzt"), holt sich Runtime und MIT-Volltext aus einem flachen
Upstream-Klon und prüft am Ende selbst, ob noch ein Plugin-Token steht. Es
benutzt `shutil.copytree(..., dirs_exist_ok=True)`, weil `cp -r quelle/scripts
ziel/scripts` beim zweiten Lauf `scripts/scripts` anlegen würde.

`--check` ist die Variante für ein Gate: sie findet nach einem Update sofort,
dass 32 Dokumente wieder auf einen Pfad zeigen, den es nicht gibt – der Fehler
ist sonst stumm, weil keine Wache Markdown-Dateien fremder Skills prüft.

