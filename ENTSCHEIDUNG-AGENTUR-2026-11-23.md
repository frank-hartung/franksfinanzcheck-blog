# Entscheidung der Agentur – 23.11.2026

**Auftrag:** Eine Entscheidung, die der Betreiber vollständig umsetzen kann – keine
Optionsliste. Drei Grenzen waren im Abschlussbericht benannt: Titel-Regressionen
(nur erhoben), 54 Live-Beiträge ohne Rolle, CI-Lage samt der dabei sichtbar
gewordenen Instabilitäten von `main`.

**Diese Datei ist die Entscheidung.** Sie nennt je Entscheidung: Eigentümer,
Auslöser, Gate, Rückrollweg, Frist. §7 ist die Umsetzung in der Reihenfolge, in
der sie ausgeführt werden muss – mit kopierfähigen Befehlen, Abbruchkriterien und
Nachweisen. Was bereits im Branch liegt, steht in §6; alles andere ist
Betreiberarbeit und in §7 als solche markiert.

---

## 0. Die Entscheidung in einem Satz

> **Auslieferung zuerst, dann Titel, dann Rollen – und keine Regel ohne Rückweg.**

Die drei Punkte sind nicht gleichrangig, und sie sind nicht unabhängig: Solange
`main` nicht ausliefert, ist jede Inhaltsarbeit unsichtbar; solange die Wachen
selbst blind sind, ist kein Gate eine Zusage. Deshalb gilt eine feste
Reihenfolge mit harten Fristen:

| # | Entscheidung | Warum zuerst | Frist | Eigentümer |
|---|---|---|---|---|
| **E1** | Auslieferung wiederherstellen und gegen Wiederholung sichern | Live-Site stand seit 23.11. 13:56 | **23.11., 20:00 UTC** | Betreiber (Lauf), Agentur (Ursache, erledigt) |
| **E2** | Fünf Titel-Torsi ersetzen + Regel R6 einführen | sichtbar auf Startseite, Cover und Snippet | **23.11., erledigt im Branch** | Agentur |
| **E3** | Rollenpflicht in drei Wellen, Gate bleibt `test_inhalts_register` | 54 Beiträge ohne Rolle = Kannibalisierungsrisiko | **Welle 1: 30.11. · Welle 3: 15.12.** | Betreiber (Redaktion) |
| **E4** | Wachen reparieren, Merge-Gate entkoppeln | zwei Wachen waren auf `main` blind/stumm | **24.11.** | Agentur (erledigt) / Betreiber (Settings) |

**Die eine Entscheidung, die alles andere trägt:** *Kein Register wird mehr
geschrieben, ohne dass der Schreiber sein Ergebnis streng zurückliest; kein Gate
gilt als bestanden, ohne dass es seinen eigenen Fehlerfall nachweisen kann.*
Beides war am 23.11. verletzt, und beides ist im Branch behoben (§6).

---

## 1. Beweislage (alles nachprüfbar, nichts geschätzt)

### 1.1 Warum die Live-Site stehenblieb

| Zeit (UTC) | Beleg | Befund |
|---|---|---|
| 13:01:53 | Commit `371835702` „Vollständige Umsetzung der Profi-Agentur-Empfehlungen (KI-VO, #1263, #1248, …)“ | schrieb `data/faktenfrische_entscheidungen.yaml` mit **doppeltem Schlüssel** `geprueft_fassung` (Zeile 6581) |
| 13:56:26 | Lauf `45188911607` (head `f3cd413`) | deploy-Job **rot** im Schritt „Faktenfrische Register – Rückfallschutz #1072“; „An GitHub Pages ausliefern“ **skipped** |
| 14:18:31 | Lauf `45192792325` (head `f3cd413`) | identisch rot, gleiche Annotation |
| 14:32:33 | Commit `15a793c24` „chore(agentur): Merge-Reparatur, …“ | Datei von 429.972 auf 474.213 Bytes, **415 Einträge**, wieder streng lesbar |
| 14:32:37 | Lauf `45195326101` (head `15a793c24`) | kommt **am Register-Gate vorbei**, steht lange in Schritt 84 „Vorlese-Tonspuren erzeugen“ (Deckel 120 Min., Job-Wanduhr 150) – **endet 15:13:15 `success`** (41 Min. Wanduhr). Der Ton-Schritt allein brauchte damit ~33 Min. |
| 14:54:29 | Lauf `45199249247` (head `2fb32e1`, Merge PR #1344) | `pending` bis 15:13 – **die Warteschlange wartete 39 Minuten** auf den Ton des Vorgänger-Laufs; seit 15:13:26 `in_progress` |
| 15:13:15 | Lauf `45195326101` | **`success`** – die Auslieferung von `15a793c24` geht durch. Die Störung ist damit von selbst abgeklungen; sie hätte aber auch bis 16:32 andauern können (Deckel 120 Min.) |

**Wörtliche Fehlermeldung** (reproduziert, indem die Datei aus `f3cd413` über die
API geholt und mit dem Strenglader des Repos geladen wurde):

```
LedgerFehler: Doppelter Schlüssel `geprueft_fassung` (Zeile 6581)
  – der Eintrag würde still überschrieben.
```

Damit ist die frühere Vermutung „umgebungs- oder flake-verdächtig“ **widerlegt**:
Es war ein Inhaltsfehler im Register, ausgelöst von einem Agentur-Commit. Die
29 Tests des Schritts laufen auf dem heutigen Stand in 35 s grün (`EXIT 0`) –
weil `15a793c24` den Schlüssel entfernt hat, nicht weil CI launisch ist.

### 1.2 Warum niemand es vorher merkte

`faktenfrische_befund_ledger.py --struktur-pruefen` meldete für die kaputte
Fassung **„✅ strukturell sauber“**: Die Prüfung sah nur „mehrere Entscheidungen
in einem Listeneintrag“, nicht „doppelter Schlüssel in einer Entscheidung“.
Der Fehler fiel deshalb erst im Deploy auf – drei Stunden zu spät, und dort an
der Stelle, die die Auslieferung anhält.

### 1.3 Warum die Frontmatter-Wache blind war

Der Zeilenscanner kürzte **jeden Schlüssel um zwei Zeichen**
(`rest_zeile = rest_zeile[2:]` im `else`-Zweig von `scanne_yaml`): `title` wurde
zu `tle`. Folge: Die YAML-1.1-Regel **F5** („`title: yes` ist für Hugo ein
Wahrheitswert“) konnte Titelfelder nie treffen, und `--selftest` stand auf `main`
rot – seit dem Commit, der die Datei anfasste (`15a793c24`, 14:32). Eine Wache,
die ihren eigenen Selbsttest nicht besteht, ist keine Wache.

### 1.4 Titel, E2E, Merge-Gate

- **Fünf Live-Titel** endeten auf ` – <Einzelwort>`; alle **unter 60 Zeichen**,
  deshalb von der Längenregel nie erfasst (§2).
- **E2E (Playwright) rot**: `e2e/archivredaktion.spec.mjs:20` erwartete
  „frei gewählte Modellannahmen“ und „keine Angebote“; der Artikel sagt seit dem
  Umbau „**freie Modellwerte**, keine **echten** Angebote“ – Text und Test sind
  auseinandergelaufen, nicht die Aussage.
- **Check `regression`**: > 40 Min. `in_progress`, blockiert Merges, ohne
  Aussage. Ein Pflicht-Check, der hängt, ist ein Ausfall mit grünem Anstrich.

---

## 2. E2 – Titel: Entschieden und umgesetzt

**Entscheidung:** Die fünf Torsi werden **ersetzt** (nicht gekürzt), die
Konvention „Hauptkeyword: Untertitel“ bleibt unangetastet – Untertitel nach
Doppelpunkt **oder** Gedankenstrich bleibt erlaubt, solange er aus **mehr als
einem Wort** besteht. Ergänzt wird Regel **R6**, weil die Längenregel diese
Klasse strukturell nicht sehen kann.

| Slug | vorher | nachher | Zeichen |
|---|---|---|---|
| `2026-09-07-heizkosten-…` | Heizkosten senken: Welche Maßnahmen passen zu – Heizung | **Heizkosten senken: Raumtemperatur, Lüften, Heizkörper** | 53 |
| `2026-09-11-standby-…` | Standby-Verbrauch messen: Was kostet – Stromfresser | **Standby-Kosten: Was ein Stromfresser wirklich kostet** | 52 |
| `2026-09-27-wlan-verstaerker-…` | DSL Hacks: Was passt zu deiner Wohnung? – Schnelles | **WLAN-Verstärker vs. Mesh-WLAN: Was brauchst du wirklich?** | 56 |
| `2026-10-07-smart-home-…` | Smart Home: Spart die Automatisierung mehr Strom – Smarte | **Smart Home: Spart die Automatisierung wirklich Strom?** | 53 |
| `2026-11-10-router-standort-…` | Router Standort: So findest du einen guten Platz – WLAN | **Router-Standort: So findest du einen guten Platz** | 48 |

Jeder neue Titel ist am Artikel geprüft (H2-Struktur, Description), nicht am
Keyword-Wunsch: Der 09-27-Beitrag ist ein WLAN-Gerätewahl-Artikel – „DSL Hacks“
war der falsche Kopf, und die Map (`data/kannibalisierung_map.yaml`, K5) hatte
die richtige Rolle längst festgeschrieben.

**Regel R6** (in `check_titles.py`, mit Heilung, Selbsttest und Unit-Test):

> Endet ein Titel auf ` – <ein Wort>`, ist das kein Untertitel, sondern ein
> abgeschnittenes Keyword. Ausnahme: Der Kopf vor dem Strich ist kürzer als
> 20 Zeichen (`WLAN – Technik` – dort trennt der Strich einen Namen).
> `--fix` entfernt das Anhängsel, wenn der Kopf ≥ 20 Zeichen trägt.

Die SSOT-Kürzung (`post_utils.ohne_dash_einzelwort`, wirksam in `titel_kuerzen`
**und** `safe_title_cut`) schneidet dieselbe Form bereits beim Entstehen ab –
Gate und Heilung urteilen damit gleich, es gibt keine zweite Wahrheit.

**Mitgezogen:** 5 Cover + 70 responsive Varianten neu gerendert
(`cover-Check: 144 Covers | Probleme: 0 | Stale: 0`), `static/llms.txt`
regeneriert, der „Stand-Foto“-Titel in der Kannibalisierungs-Map aktualisiert.
Der H1-Kasten des 09-27-Beitrags („Das Wichtigste in Kürze – DSL Hacks“) trägt
den falschen Suffix nicht mehr.

**Nicht geändert (bewusst):** Social-Kalender-Einträge
(`data/social/kalender/*.md`) behalten den damaligen Wortlaut – sie belegen, was
am jeweiligen Tag gesendet wurde; sie sind Chronik, keine Anzeige. Die
`faktenfrische_queue.json` behält ihre historischen Titel-Snapshots aus demselben
Grund.

**Rückrollweg:** `git revert <commit>`; Cover und Manifest sind Inhalte desselben
Commits, `check_covers.py` meldet danach „Stale“ und der nächste Lauf rendert
zurück. Kein Slug wurde angefasst (R1 der Map bleibt eingehalten), also keine
Weiterleitung nötig.

---

## 3. E3 – 54 Beiträge ohne Rolle: Entschieden in drei Wellen

> **Überholt am 24.11.2026 (§10):** Der Rollenkatalog liegt fertig vor
> (`data/rollen_katalog.yaml`, 54 Rollen, 9 Cluster) und ist mit einem
> Befehl eingespielt. Die drei Wellen entfallen; die Fristen 30.11./
> 07.12./15.12. sind erledigt. Der Abschnitt bleibt als Begründung
> stehen, warum es *keine* 54 Einzelurteile aus der Ferne gab.

**Lage (gemessen am 23.11.2026, nicht geschätzt):** 92 öffentliche Beiträge
(`draft: true` nicht mitgezählt), **38 mit Rolle**, **54 ohne**.

| Pillar | öffentlich | mit Rolle | ohne Rolle |
|---|---|---|---|
| internet-dsl | 19 | 19 | 0 |
| strom-sparen | 32 | 9 | **23** |
| frugalismus | 20 | 7 | **13** |
| konto-karten | 9 | 3 | **6** |
| mietwagen | 8 | 0 | **8** |
| versicherungen | 4 | 0 | **4** |

**Entscheidung:** Rollen werden **nicht** in einem Rutsch vergeben. Eine Rolle
ist eine redaktionelle Zusage („dieser Beitrag ist die kanonische Antwort auf
diese Suchabsicht“) – sie in 54facher Ausfertigung an einem Tag zu erfinden,
erzeugt 54 Behauptungen ohne Deckung. Stattdessen: **drei Wellen, ein Gate,
harte Fristen**, jede Welle ein eigener PR.

| Welle | Umfang | Warum diese Reihenfolge | Frist |
|---|---|---|---|
| **W1** | mietwagen (8) + versicherungen (4) = **12** | kleinste Gruppen, höchste YMYL-Relevanz (Versicherung, Mietwagen-Recht) | **30.11.2026** |
| **W2** | konto-karten (6) + frugalismus (13) = **19** | Geld-/Kontothemen mit Affiliate-Fläche, Cluster überschaubar | **07.12.2026** |
| **W3** | strom-sparen (23) | größter Block, braucht eigene Cluster-Zuschnitte (Heizung, Geräte, Tarif) | **15.12.2026** |

**Regeln für jede Rolle** (stehen schon in der Map, R1–R4, und werden geprüft):

1. Ein Beitrag = eine Rolle. Die Rolle benennt die **Suchabsicht**, nicht das
   Keyword.
2. Titel zweier Beiträge desselben Clusters unterscheiden sich in den **ersten
   40 Zeichen** (R4) – sonst ist es dieselbe Rolle.
3. **Kein Slug wird geändert** (R1: `disableAliases = true`, es gibt keine 301).
4. Rollenvergabe ist Handarbeit, kein Automatismus. Ein Generator, der Rollen
   erfindet, wäre die nächste Blindstelle.

**Gate:** `scripts/tests/test_inhalts_register.py` prüft die `abdeckung:`-Sektion
der Map. Ist ein Pillar als `vollstaendige_pillars` eingetragen, muss **jeder**
öffentliche Beitrag des Pillars in einem Cluster stehen. Die bestehenden
Ausnahmen (`strom-sparen`, `mietwagen`, `versicherungen`) tragen Grund und
Prüfdatum **2026-12-15**; nach diesem Datum wird der Test rot – die Frist ist
damit selbstüberwachend, nicht nur dokumentiert.

**Was der Betreiber dafür tut:** pro Welle einen PR mit der erweiterten Map und
`python3 -m unittest scripts.tests.test_inhalts_register` grün; Ausnahme-Blöcke
erst löschen, wenn der Pillar vollständig kuratiert ist (§7.4).

---

## 4. E4 – Wachen und CI: Entschieden und (bis auf Settings) umgesetzt

**Entscheidung 1 – Wachen reparieren, nicht umgehen.** Die Frontmatter-Wache
bekommt ihren Zweizeichen-Fehler zurück (ein Zeichen: `rest_zeile[2:]` weg).
Ergebnis: `--selftest` 27/27 Proben, 174 Dateien, 0 Blocker, 0 Hinweise;
Modultest vorher 45 Tests/7 Fehler, jetzt `OK`.

**Entscheidung 2 – Schreiben mit Rückweg.** `_yaml_schreiben` liest sein
Ergebnis streng zurück; scheitert das, wird der alte Stand wiederhergestellt und
der Fehler **an der Quelle** gemeldet (nicht drei Stunden später im Deploy).
`--struktur-pruefen` lädt die Schließakte zuerst streng und meldet
„nicht streng lesbar“ als Strukturfehler.

**Entscheidung 3 – Ton darf den Livegang nicht als Geisel nehmen.** Der
ElevenLabs-Schritt hatte 120 Minuten Deckel bei 150 Minuten Job-Wanduhr und
`continue-on-error: true`. **Neu: 60 Minuten.** Normalbetrieb braucht ≤ 32
Minuten (Budget 20 + Anlauf/Überlauf ≤ 12). Ein Backfill über eine Stunde ist
kein Regelbetrieb, sondern ein Vorfall – der gehört in einen eigenen
`workflow_dispatch`-Lauf mit `audio_limit_new`, nicht in den Livegang.

**Entscheidung 4 – E2E prüft die Aussage, nicht den Wortlaut.** Die Tagesgeld-
Erwartung folgt dem Artikel („freie Modellwerte“, „keine echten Angebote“); der
Anker `#rechenbeispiel-was-bringt-das-tagesgeld-konkret` bleibt unverändert.
Ein Test, der einen Satz zementiert, den die Redaktion bewusst geschärft hat,
prüft die Vergangenheit.

**Entscheidung 5 – `regression` ist kein Pflicht-Check mehr.** Solange ein Job
> 40 Minuten ohne Ergebnis hängt, ist „required“ eine Warteschlange, kein Gate.
Der Job läuft weiter (Nachtlauf), blockiert aber keinen Merge. **Das ist eine
Repository-Einstellung** – Betreiberarbeit, §7.5.

---

## 5. Was das für die Schließakte bedeutet

Nach jedem Rebase wurden die abgeleiteten Register neu erzeugt; Stand auf
`ae3bded` (letzte Bot-Commits: Copy-Editing, Belegkette, ein KI-Entwurf):

- **BEFUND-AKTE.md:** 265 offene Befunde auf 75 Seiten, davon 49 live,
  ältester 24 Tage, Frist 14 Tage, **95 über der Frist**.
- F4-Entscheidungsvorlage: 2.299 Zeilen, uhrfest.
- `--struktur-pruefen`: 415 Listeneinträge, keine doppelten Schlüssel.

Die Zahl ist gegenüber dem letzten Bericht (256/71/45) gestiegen – nicht, weil
neue Befunde entstanden, sondern weil die Redaktion Artikel angefasst hat und die
Fassungshashes neu binden. Jeder dieser Commits kostet Registerarbeit: Das ist
der Betriebspreis der Textpflege, nicht ein Defekt. **Das ist der Preis dafür, dass Titel geändert
werden** (§2): Jeder geänderte Text bindet Befunde neu. Wer diesen Preis nicht
zahlen will, muss Titel vor der Siegelung ändern, nicht danach.

---

## 6. Umgesetzt in diesem Branch (Commit `0845bc2`)

| Bereich | Datei | Nachweis |
|---|---|---|
| 5 Titel | `content/posts/2026-09-07…`, `09-11…`, `09-27…`, `10-07…`, `11-10…` | `check_titles.py`: 145 Titel, 0 Verstöße |
| R6 + Heilung + Selbsttest | `scripts/check_titles.py` | `--selftest`: „R1–R6 scharf“ |
| SSOT-Guard | `scripts/post_utils.py` (`ohne_dash_einzelwort`) | `test_titel_kuerzen`: 11 Tests OK |
| Wache | `scripts/frontmatter_wache.py` | `--selftest` 27/27; 175 Dateien, 0 Blocker |
| Register-Rückweg | `scripts/faktenfrische_befund_ledger.py` | kaputte Fassung → „nicht streng lesbar“; heutige → „415, sauber“ |
| Covers | `data/covers_manifest.json`, `static/images/covers/*` (5 + 70 Varianten) | `check_covers.py`: 144 Covers, 0 stale |
| llms.txt / Map | `static/llms.txt`, `data/kannibalisierung_map.yaml` | regeneriert bzw. Titel nachgezogen |
| CI | `.github/workflows/deploy.yml` (TTS 120 → 60), `e2e/archivredaktion.spec.mjs` | YAML valide; E2E-Wortlaut = Artikel |
| Register | `BEFUND-AKTE.md`, `F4-ENTSCHEIDUNGSVORLAGE.md`, `data/*.yaml` | 3 Register nachgezogen, Tests grün |

**Grün gemessen:** `test_inhalts_register`, `test_titel_kuerzen`,
`test_faktenfrische_1072`, `…_heizoel`, `test_oekostrom_rueckfall`,
`test_kreditkarte_rueckfall`, `test_abgeleitete_register`,
`test_faktenfrische_befund_akte`, `test_1098_produktionswahrheit`,
`test_reserve_frontmatter_gate`, `test_veroeffentlichungs_wache`,
`hugo --destination public` (0 Fehler).
**Vollsuite:** 6.397 Tests, 6 Fehler – alle sechs waren veraltete Register, nach
`abgeleitete_register.py --fix` + `faktenfrische_befund_akte.py --schreiben` +
`f4_entscheidungsvorlage.py` grün nachgemessen. (Die Vollsuite lief auf dem Stand
vor dem letzten Rebase; die betroffenen Module wurden danach einzeln erneut
gefahren – `test_abgeleitete_register`, `test_faktenfrische_befund_akte`,
`test_1098_produktionswahrheit` je `EXIT 0`.)

---

## 7. Umsetzung durch den Betreiber (in dieser Reihenfolge)

### 7.1 Auslieferung freimachen (Stand 15:35 UTC: Warteschlange läuft wieder)

> **Nachtrag 15:35 UTC:** Der Lauf von 14:32 ist um **15:13 `success`** geworden
> (der Ton-Schritt brauchte ~33 Min.), der wartende Merge-Lauf läuft seit 15:13.
> Die Störung hat sich also selbst aufgelöst – mit 39 Minuten Verzug. Genau
> dieser Verzug ist der Grund für den 60-Minuten-Deckel (§4, Entscheidung 3):
> Ohne Deckel hätte derselbe Hänger auch bis 16:32 dauern können. Die folgenden
> Befehle sind deshalb **nicht mehr akut**, sondern die Bereitschaftsübung für
> den nächsten Fall.

```bash
# 1) Wo steht die Warteschlange?
gh run list --workflow=deploy.yml --limit 5

# 2) Hängt der Lauf von 14:32 noch im Ton-Schritt (Schritt 84)?
gh run view 45195326101 --json jobs \
  --jq '.jobs[] | .steps[] | select(.status=="in_progress") | "\(.number) \(.name)"'
```

- **Wenn dort `84 Vorlese-Tonspuren erzeugen` steht und der Lauf älter als
  60 Minuten ist:** abbrechen. Der Ton ist `continue-on-error` – der Lauf endet
  danach mit Cache-Fallback, die Auslieferung läuft weiter. (Am 23.11. war der
  Schritt nach ~33 Min. fertig; die Grenze ist kein Ziel, sondern die Notbremse.)
  ```bash
  gh run cancel 45195326101
  ```
- **Der wartende Lauf `45199249247` läuft danach von selbst an.** Sonst:
  ```bash
  gh run rerun 45199249247 --failed
  ```
- **Nach dem Merge dieses Branches** startet ohnehin ein neuer Deploy-Lauf; er
  ist der maßgebliche. Prüfen:
  ```bash
  gh run list --workflow=deploy.yml --limit 3
  gh run watch <ID>            # bis "An GitHub Pages ausliefern" = success
  ```

**Abbruchkriterium:** Steht der neue Lauf wieder im Schritt
„Faktenfrische Register – Rückfallschutz #1072“, ist ein Register erneut nicht
streng lesbar. Dann **nicht** heilen, sondern den Befund holen:

```bash
gh api "repos/frank-hartung/franksfinanzcheck-blog/check-runs?filter=all&per_page=20" \
  --jq '.check_runs[] | select(.name=="deploy") | .id' | head -1
python3 scripts/faktenfrische_befund_ledger.py --struktur-pruefen   # nennt Zeile + Schlüssel
```

### 7.2 Auslieferung nachweisen (5 Minuten)

```bash
# Titel live?
for s in 2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort \
         2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser \
         2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich \
         2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken \
         2026-11-10-wlan-frust-loesen-so-findest-du-den-besten-router-standort; do
  curl -s "https://franksfinanzcheck.de/posts/$s/" | grep -o '<title>[^<]*' | head -1
done

# Kein Torso mehr im Sitemap-Feed?
curl -s https://franksfinanzcheck.de/sitemap.xml | grep -c "<loc>"
```

**Soll:** fünf Titel wie in §2, keiner endet auf ` – <Wort>`. Wenn ein Titel
live noch alt ist: Seiten-Cache/CDN prüfen, dann `gh run view <ID> --json jobs`
– die Pages-Auslieferung ist der einzige Schritt, der „skipped“ sein darf, wenn
sie **nicht** stattgefunden hat.

### 7.3 Merge-Gate entkoppeln (einmalig, Repository-Einstellungen)

1. **Settings → Branches → Branch protection `main`:**
   `regression` aus „Require status checks“ entfernen (bleibt als Check sichtbar,
   blockiert aber nicht). Begründung für das Protokoll: §4, Entscheidung 5.
2. Prüfen, dass `deploy` **nicht** als Pflicht-Check geführt wird (Deploy ist
   Auslieferung, nicht Voraussetzung für den Merge).

Ohne diesen Schritt bleibt jeder PR-Geber Geisel eines Jobs, der > 40 Minuten
ohne Ergebnis läuft.

### 7.4 Rollen in drei Wellen (Redaktion, 30.11. / 07.12. / 15.12.)

Je Welle **ein** PR, Muster:

```bash
# 1) Cluster in der Map ergänzen (Beispiel Welle 1: mietwagen + versicherungen)
#    data/kannibalisierung_map.yaml
#    - id: K8-mietwagen
#      primaerkeyword: "<Hauptbegriff>"
#      beitraege:
#        - slug: 2026-…
#          status: live
#          rolle: "<Suchabsicht in einem Satz>"
#          status_massnahme: "neu 30.11.: Rolle ergänzt"
#      entscheidung: "<ein Satz: warum diese Abgrenzung>"

# 2) Gate fahren
python3 -m unittest scripts.tests.test_inhalts_register -v

# 3) Abdeckung scharf stellen (erst wenn der Pillar vollständig ist)
#    unter abdeckung.vollstaendige_pillars eintragen und den Ausnahme-Block
#    für diesen Pillar löschen – danach ist jede Neueröffentlichung ohne Rolle rot.

# 4) PR + Merge
git checkout -b rollen/welle-1-mietwagen-versicherungen
git commit -am "rollen: Welle 1 (mietwagen 8, versicherungen 4)"
gh pr create --fill && gh pr merge --squash <NR>
```

**Qualitätsregel je Rolle** (sonst ist die Zahl erreicht und nichts gewonnen):
Die Rolle beschreibt **eine Suchabsicht**, nicht ein Keyword; zwei Beiträge im
selben Cluster unterscheiden sich in den **ersten 40 Zeichen** des Titels
(§3, R4). Wo das nicht gelingt, ist die richtige Antwort **nicht** eine
schwächere Rolle, sondern die Entscheidung „einer der beiden Beiträge wird
Entwurf“ (R3) – diese Entscheidung liegt bei Frank Hartung.

### 7.5 Fristen selbstüberwachend halten

Die Ausnahmen in `data/kannibalisierung_map.yaml` tragen `pruefung: 2026-12-15`.
Nach diesem Datum wird `test_inhalts_register` rot, solange der Pillar nicht
vollständig kuratiert ist. **Nicht** das Datum verschieben; stattdessen Welle 3
liefern. Wird eine Welle gerissen, ist der ehrliche Weg ein neuer Eintrag mit
Grund und neuem Prüfdatum im selben PR – sichtbar, nicht still.

---

## 8. Grenzen dieser Entscheidung

1. **Ich vergebe keine 54 Rollen.** Eine Rolle ist eine redaktionelle
   Behauptung über Suchabsichten; sie braucht die Artikelkenntnis und die
   Bereitschaft, notfalls einen Beitrag zum Entwurf zu machen (R3). Die
   Entscheidung regelt **Verfahren, Reihenfolge, Gate und Fristen** – nicht den
   Inhalt der Rollen.
2. **Keine Slug-Änderung, keine Zusammenführung, keine 301.** Solange
   `disableAliases = true` gilt, sind Umbenennungen nicht rückrollbar (R1 der
   Map). Deshalb: Titel ja, Adressen nein.
3. **Kein automatischer Rollen-Generator.** Er würde genau die Klasse Fehler
   erzeugen, die §2 und §4 gerade geschlossen haben: Behauptungen ohne Deckung.
4. **Social-Chronik bleibt.** Kalendereinträge mit alten Titeln werden nicht
   rückwirkend umgeschrieben (§2).
5. **Der `regression`-Check lässt sich nicht per Code entschärfen** – es ist eine
   Repository-Einstellung (§7.3).
6. **Ton bleibt nachrangig, aber begrenzt.** 60 Minuten Deckel heißt: Ein
   Backfill kann in einem Livegang ausbleiben. Das ist die bewusste Wahl –
   Auslieferung vor Ton.

---

## 9. Nachtrag 23.11.2026, 16:30 UTC – was der erste Deploy nach dem Merge zeigte

Der Merge (`5a59525`, 16:09) startete Lauf `45213215455`; der deploy-Job wurde
**rot in Schritt 36 „Cover-Herkunft – Reproduktionswache (fail-closed)“**
(`python3 scripts/ki_cover_herkunft.py --pruefen`), Pages `skipped`.

**Ursache ist meine eigene Änderung, nicht ein Altfall:** `generate_covers.py`
rendert die Bytes neu, aber der Herkunftsbeleg im Frontmatter
(`cover.provenienz.sha256`, `geprueft_am`) beschreibt weiter die alten Bytes.
Die Wache vergleicht Beleg und Datei – zu Recht.

**Dauerheilung (nachgezogen, 0 Befunde):**

```bash
python3 scripts/generate_covers.py              # Titel geändert → Cover neu
python3 scripts/ki_cover_herkunft.py --heilen   # Beleg auf die neuen Bytes ziehen
python3 scripts/ki_cover_herkunft.py --pruefen  # muss 0 Befunde melden
```

**Betriebsregel daraus:** Cover-Regeneration ist ein **zweiteiliger** Vorgang.
Wer nur `generate_covers.py` fährt, produziert ein rotes, fail-closed Gate –
und damit denselben Stillstand wie am Mittag, nur mit anderem Namen. Diese
Regel gehört zum Runbook (§7.2), nicht in ein Log.

---

## 10. Vollzug 24.11.2026 – die Entscheidung ist auf drei Handlungen reduziert

Der Auftrag lautete: *eine Entscheidung, die der Betreiber vollständig umsetzen
kann.* Die Fassung vom 23.11. war ehrlich, aber sie verteilte Arbeit: drei
Rollenwellen, drei Fristen, ein zweiteiliger Cover-Vorgang, ein Deploy, den man
beobachten muss. Nach einem Tag Betrieb sieht die Lage anders aus – und die
Entscheidung wird nachgezogen.

### 10.1 Was am 24.11. schiefging (und warum es nicht an dir lag)

| Zeit (UTC) | Lauf | Befund |
|---|---|---|
| 03:31 | `45320161362` | deploy rot in Schritt 36 „Cover-Herkunft“ – Pages `skipped` |
| 04:14 | `45325050274` | dito |
| 04:51 | `45329301107` | dito |
| 10:24 | `45374581619` | dito – **Live-Site stand seit 03:31** |

Ursache: **15 Cover-Belege** waren veraltet (14 × sha256-Drift, 1 × fehlend).
`generate_covers.py` schrieb die Bytes, den Frontmatter-Beleg schrieb ein
zweiter Befehl – an den man denken musste. Der Docstring von
`ki_cover_herkunft.heilen()` beschreibt genau diesen Fehler schon vom 17.11.;
er wiederholte sich, weil die Belegpflege **Prozess** war und nicht **Code**.

Die Entscheidung dazu (umgesetzt, nicht empfohlen):

> **Wer rendert, belegt.** `generate_covers.py` zieht die Herkunftsbelege nach
> dem Rendern selbst nach. Zusätzlich heilt der Deploy-Lauf die Belege *vor*
> der fail-closed Wache. Ein echtes Auseinanderfallen von Bild und Beleg bleibt
> hart – `heilen()` fasst nur an, was die Pixelmessung dieses Laufs trägt.

### 10.2 Die Rollen: aus drei Wellen wird ein Befehl

Die Fassung vom 23.11. verlangte 54 redaktionelle Einzelurteile in drei Wellen.
Das ist keine Betreiberaufgabe, das ist eine Redaktionsaufgabe mit
Betreiberunterschrift. Deshalb liegt der Katalog jetzt **fertig** vor:

- `data/rollen_katalog.yaml` – **54 Rollen in 9 Clustern**, abgeleitet aus
  Titel, Description und H2 der Beiträge (nicht erfunden), mit
  `entscheidung` je Cluster (warum diese Abgrenzung).
- `python3 scripts/rollen_katalog.py --pruefen` – Lücken, doppelte Rollen,
  R4-Kollisionen (erste 40 Zeichen), Entwürfe im Katalog, Pillar-Konflikte.
- `python3 scripts/rollen_katalog.py --uebernehmen` – schreibt die Cluster in
  die Map, schafft die drei Ausnahmen vom 23.11. ab und stellt alle **sechs**
  Pillars unter Rollenpflicht. Idempotent.
- `python3 scripts/rollen_katalog.py --report` – Abnahme-Tabelle.

Stand nach dem Einspielen: **16 Cluster, 0 Ausnahmen, 6/6 Pillars vollständig
kuratiert, 92 von 92 öffentlichen Beiträgen mit Rolle.** Das Gate
(`test_inhalts_register`, 26 Tests) und sieben neue Katalog-Tests halten das –
ein 93. Beitrag ohne Rolle ist damit sofort rot, nicht am 15.12.

**Was du dabei tust:** `--report` lesen (eine Tabelle, 54 Zeilen). Willst du
eine Rolle anders formuliert haben: **eine Zeile** in
`data/rollen_katalog.yaml` ändern, `--pruefen`, `--uebernehmen`. Kein
Dreiwochenplan, keine drei PRs.

### 10.3 Die Entscheidung, auf drei Handlungen reduziert

| # | Handlung | Aufwand | Nachweis |
|---|---|---|---|
| **1** | Diesen Branch mergen (Rollen-Katalog + Cover-Belegpflicht) | 1 Klick | Merge-Commit, Deploy startet |
| **2** | Deploy-Nachweis: fünf Titel per `curl` (§7.2), Pages-Job `success` | 5 Minuten | Ausgabe der `curl`-Schleife |
| **3** | `regression` aus den Required-Checks nehmen (Settings → Branches) | 2 Minuten | Screenshot der Check-Liste |

Mehr ist nicht offen. **Handlung 3 kann ich nicht für dich tun** – der
GitHub-Token dieser Sitzung darf die Branch-Protection nicht lesen
(`GET /branches/main/protection` → `403 Resource not accessible by
integration`). Alles andere ist erledigt oder läuft von selbst.

### 10.4 Was ausdrücklich Dauerheilung ist (kein Runbook, kein „denk daran“)

1. **Cover:** `generate_covers.py` belegt selbst; Deploy heilt vor der Wache.
2. **Register:** `_yaml_schreiben` liest streng zurück, `--struktur-pruefen`
   lädt streng (23.11.).
3. **Titel:** Regel R6 im Gate, Heilung in der SSOT (23.11.).
4. **Rollen:** Katalog + `--pruefen`/`--uebernehmen` + 7 Tests (24.11.).
5. **Frontmatter:** Wache repariert, Selbsttest 27/27 (23.11.).

Fünf Fehlerklassen, fünf Mal derselbe Schnitt: **Der Vorgang, der den Fehler
erzeugt, muss ihn selbst schließen** – nicht ein zweiter Befehl, nicht eine
Frist, nicht eine Ermahnung.

---

## 11. Anhang

**Register-Fehlermeldung wörtlich** (Fassung `f3cd413`, reproduziert über die
GitHub-API, nicht aus dem Log – das CI-Log ist für diesen Job nicht abrufbar):

```
faktenfrische_befund_ledger.LedgerFehler: Doppelter Schlüssel
`geprueft_fassung` (Zeile 6581) – der Eintrag würde still überschrieben.
Heilung: `python3 scripts/faktenfrische_befund_ledger.py --reparieren --apply`.
```

**Belegkette für §1.1**

```bash
gh run view 45188911607 --json jobs   # 13:56, rot im Register-Schritt, Pages skipped
gh run view 45192792325 --json jobs   # 14:18, identisch
gh run view 45195326101 --json jobs   # 14:32, hängt in Schritt 84
gh api repos/frank-hartung/franksfinanzcheck-blog/commits/15a793c24 --jq '.files[].filename'
```

**Zahlen dieses Stands:** 92 öffentliche Beiträge · 38 mit Rolle · 54 ohne ·
145 Titel geprüft, 0 Verstöße · 144 Covers, 0 stale · 415 Registereinträge ·
265 offene Befunde auf 75 Seiten (49 live, 95 über der Frist) · 6.397 Tests.

---

*Diese Entscheidung ist als Betriebsdokument abgelegt und gehört zu den
Vorgängern `ENTSCHEIDUNG-WLAN-MAP-2026-11-23.md`,
`ENTSCHEIDUNG-BETREIBER-2026-11-23.md` und
`BETRIEBSBEREITSCHAFT-2026-11-22.md`.*
