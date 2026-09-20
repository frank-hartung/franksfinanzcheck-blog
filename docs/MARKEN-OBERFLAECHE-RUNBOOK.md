# 🎯 Marken-Oberfläche – Befund, dauerhafter Fix und Admin-Fahrplan

**Stand:** 20.09.2026 · **Auftrag (Frank):** Bei einer Markensuche darf nicht die
Automatik über der persönlichen Expertenpositionierung stehen. Öffentliche
Backup-Releases stoppen bzw. privat speichern, das operative Repository möglichst
privat machen, mindestens dessen öffentliches README auf eine seriöse
Markenbeschreibung reduzieren.

**Zuständig:** Die Wache (`scripts/brand_surface_guard.py`) hält den Zustand
dauerhaft; der Admin-Fahrplan in Abschnitt 3 enthält die drei Griffe, die ein
Admin-Token braucht (das Automatik-Token hat `viewer_can_administer=false`).

---

## 1. Befund mit Belegen (20.09.2026)

| # | Befund | Beleg (nachprüfbar) |
|---|---|---|
| 1 | **14 öffentliche Backup-Releases** mit dem vollständigen Quellstand (`.bundle` + `worktree.zip`, zusammen ~158 MB je Release), Titel „Backup backup-2026…" | `gh api repos/frank-hartung/franksfinanzcheck-blog/releases --jq '.[]｜{tag_name,draft}'` → 14×`draft=false` |
| 2 | Diese Seiten waren **frei abrufbar und indexiert** – bei der Suche „FranksFinanzcheck Frank Hartung" standen sie ganz oben, mit dem Text „Automatisches Offsite-Backup … Getrackte Dateien: 2297" | anonyme Abfrage `…/releases/tag/backup-20260920-0809` → HTTP 200 mit genau diesem Inhalt; Asset-Download `…/releases/download/…/backup.bundle` → HTTP 302 auf eine signierte URL (kein Login nötig) |
| 3 | **14 öffentliche Git-Tags** `backup-2026…` auf der Tag-Seite | `…/tags` zeigte alle 14 Namen (inzwischen entfernt) |
| 4 | **Repo-Beschreibung** sagt „(Affiliate-Blog, Hugo)" – das Framing, das die Expertenpositionierung verdrängt | `gh api repos/… --jq .description` |
| 5 | **README (808 Zeilen, 63 KB)** erklärte die vollautomatische Content-Produktion im Detail (Bots, Gates, Kadenz, Social-Autopilot, Kanal-Tokens) | Prüflauf der Wache: 384 ROT-Befunde auf `README.md` |
| 6 | **Homepage-URL fehlt** im Repo-Kopf, **Wiki ist aktiv**, **keine Themen** | `gh api repos/… --jq '{homepage,has_wiki,topics}'` |
| 7 | **Öffentliche Issue-Titel aus dem Betrieb**, z. B. #329 „⚠️ Workflow fehlgeschlagen: Willkommenstext-Refresh (failure)" | `gh issue list --state open` |

**Kern des Problems:** Nicht ein hässliches README allein – die *Backup-Automation
schrieb jeden Nachtlauf absichtlich öffentlich* (GitHub-Free erlaubt Releases ohne
Limit). Aufräumen ohne Struktur-Fix hätte beim nächsten 03:00-UTC-Lauf dieselbe
Seite wieder aufgebaut.

---

## 2. Was jetzt dauerhaft steht (mit Beweis)

| Maßnahme | Beweis |
|---|---|
| **14 Backup-Releases → Entwurf** (privat, Assets erhalten, jederzeit wieder veröffentlichbar) | Wache `--fix`: „14 Backup-Release(s) auf Entwurf gestuft", jede Umstellung nachgelesen (`draft=true`); anonyme Release-Seite liefert nur noch die 404-Seite |
| **14 Backup-Tags entfernt** (nur Referenzen – der Inhalt lag ohnehin öffentlich in `main`) | Wache `--fix`, Nachzählung über `GET /tags`; Tag-Seite anonym: 0 Treffer |
| **README auf Markenbeschreibung reduziert** (808 → ~100 Zeilen: Positionierung, Themen, Person, Grundsätze, Transparenz, Kontakt) | `python3 scripts/brand_surface_guard.py --only readme --gate` → ROT=0 |
| **Backup-Automation schreibt nie wieder öffentlich** | `.github/workflows/backup-offsite.yml`: Backup geht als **Artefakt** (privat) oder in ein **privates** Ziel-Repo; Ziel wird **vor** dem Upload auf Privatheit geprüft (fail-closed); dauerhafte Ablage nur verschlüsselt (AES-256/PBKDF2 mit Entschlüsselungs-Probe); Releases immer `--draft`; Nachprüfung von Assets **und** `draft=true`; Regelprüfung am Ende jedes Laufs |
| **Wache mit Tageslauf** | `scripts/brand_surface_guard.py` (Selbsttest 14 Fallgruppen, heilt Releases und Tags nur mit Nachprüfung) + `.github/workflows/brand-surface-guard.yml` (täglich 04:20 UTC, bei jedem veröffentlichten Release, manuell „heilen/prüfen") |
| **Admin-Werkzeug** | `scripts/repo_brand_switch.py`: zeigt den Plan (Standard), schreibt mit `--apply`, liest jede Änderung zurück, prüft nach `--privat` die Live-Website und **rollt bei Ausfall selbst zurück** |
| **Ausnahmen mit Begründung** | `data/brand_surface_allowlist.txt` (eine Regex pro Zeile, Kommentar = Begründung; greift nur, wenn die Ausnahme die Fundstelle überdeckt) |

**Kontrolle in 30 Sekunden:**

```bash
python3 scripts/brand_surface_guard.py --selftest    # Detektor-Beweis (14 Fälle)
python3 scripts/brand_surface_guard.py --gate        # Befund; Exit 1 = Markenfläche verletzt
python3 scripts/repo_brand_switch.py                 # Admin-Plan (schreibt nichts)
gh api repos/frank-hartung/franksfinanzcheck-blog/releases \
  --jq '[.[] | select(.draft==false)] | length'      # muss 0 sein (außer bewussten Releases)
```

---

## 3. Admin-Fahrplan (die drei Griffe, die nur du kannst)

### Schritt 0 – Repo-Kopf auf Marke (30 Sekunden)

```bash
python3 scripts/repo_brand_switch.py            # Plan ansehen
python3 scripts/repo_brand_switch.py --apply    # schreiben: Beschreibung, Homepage,
                                               # Wiki aus, Marken-Themen – mit Nachprüfung
```

Das setzt: Beschreibung = *„FranksFinanzcheck – unabhängiger Finanz-Ratgeber von
Frank Hartung: Strom, Gas, DSL, Versicherungen, Sparen."*, Homepage =
`https://franksfinanzcheck.de/`, Wiki aus, Themen = `geld-sparen, finanzen,
frugalismus, stromvergleich, versicherungen, ratgeber`.

**Wichtig:** Dieses Skript braucht ein Admin-Token (`gh auth login` als
`frank-hartung`). Ohne Admin-Recht zeigt es nur den Plan und bricht einen
Schreibversuch sauber ab – die Automatik darf den Repo-Kopf bewusst nicht ändern.

### Schritt 1 – Repository privat: erst prüfen, welcher Weg trägt

> **Achtung, das ist der kritische Punkt:** GitHub Pages aus einem **privaten**
> Repository gibt es erst mit **GitHub Pro/Team**. Auf dem kostenlosen Plan geht
> `franksfinanzcheck.de` offline, sobald das Repo privat wird. Deshalb: Weg
> wählen, **dann** umschalten – nicht umgekehrt.

#### Weg A – GitHub Pro/Team (einfachste Variante, ~4 US$/Monat)

```bash
python3 scripts/repo_brand_switch.py --apply --privat
```

Das Skript prüft danach live `https://franksfinanzcheck.de/`:
* **HTTP 2xx/3xx** → Website läuft weiter, Umschaltung bleibt aktiv. Fertig.
* **HTTP 404/403** → Pages trägt den privaten Plan nicht: Das Skript **rollt
  automatisch zurück** auf öffentlich und verweist auf Weg B1/B2.
* **Netzfehler** → Umschaltung bleibt aktiv, aber mit Warnung; bitte in den
  nächsten Minuten selbst prüfen (Rückweg steht im Log).

**Zwei Nebenwirkungen einplanen:**
1. **Actions-Minuten:** In öffentlichen Repos sind Actions gratis, in privaten
   zählen sie gegen das Monatskontingent (Free 2.000 min, Pro 3.000 min).
   Bei ~48 Workflows vorher in *Settings → Billing → Actions* den Verbrauch
   prüfen – sonst wird aus „privat" eine Monatsrechnung.
2. **Sichtbarkeit der Läufe:** Action-Logs und Artefakte sind privat; die
   Website bleibt öffentlich (so gewollt).

#### Weg B1 – privates Quell-Repo + öffentliches Veröffentlichungs-Repo (0 €)

Für alle ohne Pro-Plan – der Betrieb bleibt komplett in GitHub:

1. Neues **öffentliches** Repo anlegen, z. B. `frank-hartung/franksfinanzcheck-site`
   (nur veröffentlichte Website, keine Dokumentation, keine Skripte).
2. In `deploy.yml` das Ziel ändern: statt `gh-pages` im eigenen Repo dorthin
   pushen (`peaceiris/actions-gh-pages` mit `external_repository` und Deploy-Key
   bzw. PAT in `SITE_DEPLOY_TOKEN`).
3. Die eigene Domain vom alten Repo lösen und im Site-Repo setzen
   (DNS bleibt wie in `docs/DNS-CLOUDFLARE-GITHUB-PAGES.md`).
4. Erst wenn `franksfinanzcheck.de` aus dem neuen Repo sauber ausgeliefert wird:
   Quell-Repo privat stellen (`--apply --privat`).
5. Commit-Titel im Veröffentlichungs-Repo neutral halten
   („Veröffentlichung 2026-09-21"), damit dort keine Betriebssprache steht.

#### Weg B2 – Cloudflare Pages, Direct Upload (0 €, kein zweites öffentliches Repo)

Für „privat ohne zweiten Auftritt": DNS liegt bereits bei Cloudflare, die
Website wird aus dem privaten Repo als Verzeichnis hochgeladen
(`npx wrangler pages deploy public --project-name franksfinanzcheck`), Secrets
`CLOUDFLARE_API_TOKEN` + `CLOUDFLARE_ACCOUNT_ID`. Danach den DNS-Eintrag von
GitHub Pages auf das Pages-Projekt umstellen. Der Deploy-Workflow bleibt
unverändert (Hugo-Build wie bisher, nur das Ausliefern wechselt).
**Vorteil:** Nichts über die Marke ist öffentlich außer der Website selbst.

#### Weg C – bewusst öffentlich bleiben (Mindeststandard, 0 €)

Genau der Zustand nach diesem Fix: README, Releases, Tags und Sichtbarkeit sind
sauber; es bleiben die Betriebsdokumentation unter `docs/`, die
Commit-Titel der 328 Vorgänger-Commits und die Issue-Titel öffentlich. Das ist
der Zustand „Marke oben, Maschine dahinter" – tragfähig, aber nicht dauerhaft
der Königszug. **Empfehlung: Weg A, sonst B2.**

### Schritt 2 – Backup dauerhaft machen (5 Minuten, unabhängig vom Weg)

Ohne Zielspeicher lebt das Backup 90 Tage als Artefakt (privat, aber nicht
dauerhaft). Für die volle Offsite-Kette:

```bash
gh repo create frank-hartung/franksfinanzcheck-backup --private \
  --description "Privates Offsite-Backup (Quelle: franksfinanzcheck-blog)"
gh variable set BACKUP_REPO --body "frank-hartung/franksfinanzcheck-backup" \
  --repo frank-hartung/franksfinanzcheck-blog
gh secret set BACKUP_REPO_TOKEN --repo frank-hartung/franksfinanzcheck-blog   # PAT, nur dieses Repo, Contents RW
gh secret set BACKUP_PASSPHRASE --repo frank-hartung/franksfinanzcheck-blog   # lange Passphrase, in den Passwortmanager
```

Danach: `gh workflow run "Offsite-Backup"` und im Lauf prüfen, dass
„Dauerhaftes Ziel: … (privat, Entwurf, nachgeprüft)" steht. **Die Passphrase ist
der einzige Schlüssel zum Backup – ohne sie sind die `.enc`-Dateien verloren.**

---

## 4. Restrisiken (ehrlich benannt)

| Restrisiko | Was hilft |
|---|---|
| Suchmaschinen-Caches der alten Release-Seiten laufen nach | Nach dem Privatstellen in der Google Search Console (Property `github.com/frank-hartung/franksfinanzcheck-blog/releases/*`) „Entfernen" beantragen; Wartezeit meist Tage |
| Archiv-Dienste (z. B. Wayback Machine) können die Seiten gespiegelt haben | Exklusionsantrag beim jeweiligen Dienst; die Originale sind privat, die Kopie bleibt fremdgehostet |
| Commit-Titel der Vergangenheit sind Teil der Story („fix(gate): …") | Nur über ein neues Repository bzw. `filter-repo` änderbar – Aufwand/Nutzen prüfen; Weg A/B2 nimmt sie aus dem öffentlichen Blick |
| Öffentliche Issue-Titel des Betriebs (#329 u. a.) | Seit dem Fix meldet die Wache sie als GELB; nach Weg A/B sind sie privat. Neue Titel neutral fassen („Willkommenstext prüfen" statt „Workflow fehlgeschlagen") |
| Das Pinterest-Video-Release (`pinterest-video-strom-sparen-20260828`) ist öffentlich, aber ohne Assets und markenkonform | Bewusst so gelassen; löschen nur, wenn es keinen Nutzen mehr hat (`gh release delete pinterest-video-strom-sparen-20260828 --yes --cleanup-tag`) |

---

## 5. Betriebsregeln (damit es nicht zurückkommt)

1. **Backups sind nie öffentlich.** Artefakt oder privates Ziel, immer Entwurf,
   immer mit Nachprüfung. Der Workflow prüft das am Ende jedes Laufs selbst.
2. **Kein Release ohne Markenprüfung.** Öffentliche Releases sind Markenfläche;
   Titel und Notizen gehören in Markensprache.
3. **README ist Markenfläche, nicht Betriebshandbuch.** Betriebsdoku gehört nach
   `docs/` – genau die Trennung, die diesen Befund ausgelöst hat.
4. **Ausnahmen brauchen eine Begründung** in `data/brand_surface_allowlist.txt`.
   Eine Ausnahme ohne Grund ist ein stillgelegtes Gate.
5. **Admin-Griffe bleiben Admin-Griffe.** Die Wache meldet sie (GELB) mit
   Befehl, sie führt sie nicht aus – ein Automatik-Token mit Repo-Admin-Recht
   wäre selbst ein Risiko.
6. **Nicht grün stellen, was ungeprüft ist.** Ist die API nicht erreichbar,
   meldet die Wache „nicht prüfbar" (`::warning::`) – `--strict` macht daraus
   einen Befund, wenn du es hart brauchst.
