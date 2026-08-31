# BRANCH-RETENTION – Arena-Session-Branches, Bestand & Bergung (Stand 31.08.2026)

Wurde angelegt, als fünf `arena/01a0…-franksfinanzcheck-blog`-Branches aufräumt werden sollten.
Kurzform der Regeln: **ein Branch darf weg, wenn seine Spitze Vorfahr von `main` ist.**

> Zum Nachrechnen in einer Arena-Sandbox: der Klon ist **shallow**. Erst
> `git fetch --unshallow`, sonst meldet `git merge-base` „no merge base" und es sieht aus,
> als hätte `main` nur 4 Commits.

## Bewertung

| Branch | Spitze | eigene Commits | Einzigartig | Status |
|---|---|---|---|---|
| `01a019c8` | `9d91b80c` (19.08) | 0, Vorfahr von main | – | **gelöscht** |
| `01a0435e` | `3b2e04ee` (27.08) | 0, Vorfahr von main | – (identisch mit Tag `pinterest-video-strom-sparen-20260828`) | **gelöscht** |
| `01a03408` | `08c97ab8` (24.08) | 1 | `scripts/pinterest_trust_shield.py` (540 Z.), §6 SPIELBUCH, Report | **gelöscht** – Skript/§6/Report via #132 auf main (Blob identisch), T9-Haken via #133 |
| `01a04371` | `cae7703e` (27.08) | 6 | `docs/DNS-CLOUDFLARE-GITHUB-PAGES.md`, `PINTEREST-SPAM-SPERRE-AKTIONSPLAN.md`, `data/pins_upload.csv` | behalten (Doku nie gemergt; CSV generierbar: `python3 scripts/spam_guard.py --gen-csv --max 50`) |
| `01a045c8` | `f1e74ab1` (28.08) | 1 | `strom-sparen-pinterest.mp4` (2 668 390 bytes, Blob `b90652b0…`) | behalten – zusätzlich durch Tag `retention-pinterest-video-20260828` festgehalten |

## Bergung (Blob-Hash ist der Integritätsbeweis: `git hash-object` muss denselben Wert liefern)

```bash
# Video (2,7 MB) – Blob-API, funktioniert auch ohne Token (getestet: HTTP 200)
curl -fsSL -H "Accept: application/vnd.github.raw" \
  https://api.github.com/repos/frank-hartung/franksfinanzcheck-blog/git/blobs/b90652b0dff3b97e4931437c4df35d1dede787a0 \
  -o strom-sparen-pinterest.mp4 && git hash-object strom-sparen-pinterest.mp4   # → b90652b0…

# oder bequem über den Sicherungs-Tag, solange der Branch existiert gar nicht nötig:
git fetch origin 'refs/tags/retention-pinterest-video-20260828:refs/tags/retention-pinterest-video-20260828'
git show --stat retention-pinterest-video-20260828
```

## Löschen, wenn gesichert ist

```bash
# Vorfahren-Test zuerst – der ist das eigentliche Sicherheitsnetz:
git fetch origin && git merge-base --is-ancestor origin/arena/<id>-franksfinanzcheck-blog origin/main \
  && echo "kann weg" || echo "ENTHÄLT EIGENE ARBEIT – erst sichern"

gh api -X DELETE "repos/frank-hartung/franksfinanzcheck-blog/git/refs/heads/arena/<id>-franksfinanzcheck-blog"
```

Die Ref-API (`create`/`delete`) darf die Arena-App **sehr wohl** – `403 Resource not accessible
by integration` kommt dort vom `.github/workflows/`-Gate (ein Ziel-Commit, der eine Workflow-Datei
anfasst, darf die App nicht referenzieren), nicht von fehlendem Contents-Zugriff.

## Nebenbefund, der hier dokumentiert blieb

`08c97ab8` (24.08. 14:12) lag **vier Minuten nach** dem Merge von #66 (14:08) und erreichte `main`
nie – `git grep -i trust_shield origin/main` ergab 0 Treffer. Deshalb jetzt #132. Offener
Folgepunkt: `scripts/pinterest_engine.py` importiert `time` (Zeile 39) ohne ein einziges
`time.sleep` und postet `unpinned[:10]` in drei Schleifen (440/453/489) – das
`time.sleep(PIN_PAUSE_S)`-Rate-Limit (Branch-Zeile 276, `PIN_PAUSE_S = max(45, env)`) fehlt auf
`main`. Nicht automatisch geändert werden, sondern als kleiner Folge-PR.

## Nachtrag (31.08., 15:47 UTC) – #132 und #133 sind gemergt

* **#132** `615e52ee` – Trust-Shield-Skript + §6 + Report auf main (Blob `86f09eae…` identisch).
* **#133** `bf5dd6bc` – T9-Haken in der Engine nachgebaut (`PINS_PRO_TAG` Cap 2/Lauf,
  `time.sleep(PIN_PAUSE_S)` nach echter Erstellung, Queue auf denselben Cap). Trust-Shield meldet
  seither `Probleme=0`. Bewusst **kein** Watchdog-Aufruf in `.github/workflows/pinterest-ai.yml`:
  die App darf dort nicht schreiben, eine Zeile rechtfertigt keinen Web-Editor-Eingriff.
* **`01a03408` gelöscht.** Vorher die zwei Dateien geprüft, die auf `main` *fehlten*
  (`content/posts/2026-08-21-haushaltsbuch…md`, `…mietwagen…md`): das sind keine Verluste, sondern
  Flat-Dateien, die `main` bewusst in `content/posts/<slug>/index.md` umgezogen hat
  (`eca8a015` angelegt → `9f8991cf`/`8ee961d4` gelöscht → `d874f5fe` als Ordner neu angelegt,
  176 bzw. 166 Zeilen statt 147/151). `git cherry` meldet den Commit wegen der Umbenennung als
  „nicht übernommen" – der Datei-Vergleich widerlegt das.
* Offene Follow-ups: Watchdog-Aufruf des Shields (Workflow, braucht `workflows`-Recht der App),
  `01a04371` (Doku) und `01a045c8` (Video, zusätzlich durch Tag
  `retention-pinterest-video-20260828` gesichert) bleiben bis zur Entscheidung stehen.
