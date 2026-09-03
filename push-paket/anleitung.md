# Option B – Fix-Paket selbst pushen (PAT bleibt auf deinem Rechner)

> **Wichtig zuerst:** Der Branch `arena/01a0668b-franksfinanzcheck-blog` steht inzwischen
> **teilweise auf GitHub** (Code/Content/Report + dieses `push-paket/`).
> Es fehlen dort **nur die 5 Workflow-Dateien** unter `.github/workflows/`, weil die
> Sandbox-GitHub-App keine `workflows`-Schreibrechte hat. Genau diese Lücke schließt
> dein Push mit PAT (`repo` + `workflow`). Deshalb findest du den Ordner auf GitHub unter:
> **github.com/frank-hartung/franksfinanzcheck-blog → Branch `arena/01a0668b-franksfinanzcheck-blog` → `push-paket/`**

---

## Vorbereitung: PAT erstellen (einmalig, ~2 Minuten)

1. github.com → Profilbild → **Settings** → **Developer settings** → **Personal access
   tokens → Tokens (classic)** → **Generate new token (classic)**
2. Note z. B. `ffc-push-2026-09`, Ablauf z. B. 7 Tage.
3. **Zwei Häkchen sind Pflicht:**
   - ☑ `repo` (bzw. bei öffentlichem Repo genügt `public_repo`)
   - ☑ `workflow` ← **dieser Haken entscheidet!** Ohne ihn schlägt der Push mit genau
     demselben Fehler fehl wie in der Sandbox.
4. **Generate token** → Token wird einmal angezeigt → sicher ablegen (Passwortmanager).
   **Nie in den Chat schreiben, nie in der Sandbox eingeben.**

Feingranular-Alternative: *Fine-grained tokens* → Repository: nur
`frank-hartung/franksfinanzcheck-blog` → Permissions: **Contents: Read and write** +
**Workflows: Read and write**.

---

## Weg 1 (empfohlen): `push-fix-all.sh` – eine Datei, alles automatisch

1. Datei von GitHub laden: **Branch `arena/01a0668b-franksfinanzcheck-blog`** → Ordner
   `push-paket/` → Datei `push-fix-all.sh` → Download-Symbol (oder „Raw“ → Rechtsklick →
   Speichern unter). Die Datei ist ~160 KB und in sich vollständig.
2. Terminal öffnen (macOS/Linux; Windows: „Git Bash“) und ausführen:
   ```bash
   bash ~/Downloads/push-fix-all.sh
   ```
3. Das Skript klont frisch, erzeugt den Branch aus `origin/main`, wendet **alle**
   Änderungen an (Code + Content + Workflows) und pusht mit `--force` (sicher: auf dem
   GitHub-Branch liegt nur der Teil-Push dieser Fixes, kein fremder Commit).
   Git fragt nach **Username** (= GitHub-Name) und **Passwort** (= PAT).
4. Danach: GitHub → Banner **„Compare & pull request“** → PR gegen `main` → **Merge**.

## Weg 2 (ohne Skript, nur die fehlenden Workflow-Dateien ergänzen)

Falls der Branch-Teil-Push schon auf GitHub ist, genügt es, die 5 Workflow-Dateien zu
ergänzen. Dafür gibt es zwei Unterwege:

**2a) Mit Patch (Terminal):** `push-paket/workflows-only-diff.patch` herunterladen, dann
```bash
git clone https://github.com/frank-hartung/franksfinanzcheck-blog.git
cd franksfinanzcheck-blog
git checkout arena/01a0668b-franksfinanzcheck-blog
git apply push-paket/workflows-only-diff.patch   # bzw. Pfad zur Datei
git add -A && git commit -m "fix(ci): URL-Hygiene + Kadenz-Endkontrolle (Workflow-Teil)"
git push
```

**2b) Ohne Terminal (GitHub-Webeditor):** Die **fertigen** Dateien liegen unter
`push-paket/workflow-dateien/` (`deploy.yml`, `content-engine-v2.yml`,
`blog-health-daily.yml`, `produktions-wache.yml`, `kadenz-endkontrolle.yml`).
Im Webeditor von `.github/workflows/…` jeweils den Inhalt ersetzen bzw. die neue Datei
`kadenz-endkontrolle.yml` anlegen, auf dem Branch committen, dann PR öffnen + mergen.

---

## Nach dem Merge (Fr 04.09.2026!)

- Der Merge löst automatisch den **Deploy** aus (neue URL-Hygiene-Gates in `deploy.yml`).
- Freitag: Engine-Slots 06:10/14:10/17:40 UTC füllen 2–3 LIVE; um **21:05 UTC** läuft
  erstmals die **Kadenz-Endkontrolle** (letztes Netz: füllt bei Unterschreitung aus dem
  Reserve-Pool, stößt Deploy an, meldet/schließt Defizit-Issues).
- Manueller Test jederzeit: Actions → „Kadenz-Endkontrolle“ → Run workflow.

## Fehlerbehebung

| Fehler | Lösung |
|---|---|
| Push abgelehnt: *„refusing to allow … without `workflows` permission“* | PAT ohne `workflow`-Scope → neuen PAT mit ☑ `repo` + ☑ `workflow` erzeugen |
| *„Permission to frank-hartung/… denied“* | PAT hat keinen Zugriff auf dieses Repo → feingranularen PAT wählen |
| `git apply` schlägt fehl | Vorher `git pull` auf dem Branch (Teil-Push kann inzwischen ergänzt worden sein) oder Weg 1 (frisches Klon) nutzen |

## Dateien in `push-paket/`

| Datei | Zweck |
|---|---|
| `push-fix-all.sh` | **Weg 1** – eine Datei, kompletter Fix (Diff eingebettet), Force-Push |
| `0001-…` bis `0005-….patch` | die 5 Original-Commits als Patch-Serie |
| `gesamt-diff.patch` | alle Änderungen in einer Patch-Datei |
| `workflows-only-diff.patch` | nur die `.github/workflows/`-Änderungen (Weg 2a) |
| `workflow-dateien/` | die 5 fertigen Workflow-Dateien als Kopien (Weg 2b) |
| `uebersicht.txt` | Diff-Statistik |
| `anleitung.md` | diese Datei |
