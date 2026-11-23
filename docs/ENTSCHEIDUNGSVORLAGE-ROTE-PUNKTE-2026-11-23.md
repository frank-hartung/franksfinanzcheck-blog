# Entscheidungsvorlage: die roten Punkte

**Stand:** 23.11.2026 · **Basis:** `main` @ `566cd39` ·
**Messung:** Lauf [`45181319212`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/45181319212)
(`sicherheits-wache.yml`, `workflow_dispatch`, 23.11.2026 13:10Z) — Befund
unverändert gegenüber [`45151875836`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/45151875836)

**Die Entscheidung:** Der Code ist auf Soll. **A und B werden in einem
Durchgang erledigt — heute, 45 Minuten, nach dem Ablauf in Abschnitt 0.** C
(Titel) und D (Texte) sind damit ausdrücklich **nicht** Teil dieses Durchgangs;
sie bekommen Termine und Verantwortliche, weil ein Siegel und ein Artikeltext
nicht von einem Werkzeug-PR entschieden werden. Punkt 5a ist keine Aufgabe,
sondern eine Störung: der Tageslauf, der sie beheben sollte, ist selbst tot.

Kein Punkt dieser Vorlage ist ein Programmierauftrag. Wer hier Code ändert,
ändert am falschen Ende.

---

## 0. Der Durchgang — die Entscheidung, die Sie jetzt umsetzen

**Entschieden wird nicht mehr, *was* — sondern dass A und B in **einem**
Durchgang erledigt werden, in dieser Reihenfolge, mit diesen Befehlen.** 45
Minuten, zwei Zugänge (Cloudflare-Zone, GitHub), danach ist der Live-Nachweis
grün oder der Durchgang ist an einer benannten Stelle abgebrochen. C und D sind
**nicht** Teil des Durchgangs (Termine in Abschnitt 4 und 5).

**Warum A und B zusammen:** Nach jedem der beiden allein bleibt der Lauf rot
(Schritt 4 bzw. Schritt 6), und ein halb grüner Nachweis wird erfahrungsgemäß
nicht zu Ende geführt. Beide sind Betreiberhandlungen ohne Redaktionsanteil —
also ein Termin, nicht zwei.

### Vorbereitung (einmal, 5 Minuten)

| Was | Wo |
|---|---|
| Zone-Token `FF Edge Freigabe`, Rechte `Zone.DNS:Edit`, `Zone.Settings:Edit`, `Zone.Transform Rules:Edit`, Zone `franksfinanzcheck.de` | Cloudflare → My Profile → API Tokens → Create Token |
| Neuer Zufallswert für den Leseschlüssel | `openssl rand -hex 32` → in den Passwortmanager, **nicht** in den Chat |

### A — Edge-Regel (20 Minuten)

1. **Messen** (schreibt nichts), in einem **frischen** Terminal — der Name
   `CLOUDFLARE_API_TOKEN` wird auch vom Worker-Deploy benutzt, ein alter Wert in
   der Shell würde die falsche Zone treffen:
   ```bash
   CLOUDFLARE_API_TOKEN=<zone-token> npm run edge:freigabe
   ```
   *Erwartet:* Zeilen mit `✅ Zone erreichbar` und `✅ DNS …: proxied`, dazu
   `❌` bei der Regel/den Herkünften. Steht dort `❌ DNS … nicht vollständig
   proxied` → **Stop** (siehe Stop-Regeln unten); eine Transform Rule kann auf
   einer unproxied Zone nichts bewirken.
2. **Herstellen:**
   ```bash
   CLOUDFLARE_API_TOKEN=<zone-token> npm run edge:freigabe:apply
   ```
   *Erwartet:* „kontrollierte Herstellung“, Regel `FF Sicherheits-Header`
   angelegt/aktualisiert, SSL-Modus unverändert oder strenger — **nie**
   herabgestuft. Meldet das Skript eine mehrdeutige Zone oder einen
   SSL-Konflikt: **Stop**, nicht erzwingen.
3. **Gegenmessen ohne Token** (misst die echte Auslieferung, drei Ziele):
   ```bash
   npm run header:check:live
   ```
   *Erwartet:* grün auf `https://franksfinanzcheck.de/`, `/methodik/` **und**
   `https://www.franksfinanzcheck.de/`.
4. **Selbstheilung scharfschalten** — erst jetzt, nicht vorher:
   GitHub → Settings → Secrets → `CF_EDGE_HEAL_TOKEN` = derselbe Zonentoken ·
   Settings → Variables → `CF_EDGE_AUTOHEAL` = `true`.

### B — Worker-Leseschlüssel (10 Minuten)

**Korrektur meiner früheren Empfehlung:** „den aktuellen Wert aus dem Worker
ziehen“ geht nicht — Cloudflare-Worker-Secrets sind write-only, `wrangler secret
list` zeigt nur Namen. Der einzige ausführbare Weg ist die **Rotation**, und sie
ist hier unbedenklich: den Leseschlüssel konsumieren ausschließlich drei
GitHub-Workflows (`newsletter-daily`, `newsletter-lifecycle`,
`sicherheits-wache`) über **ein** Secret.

1. **Ziel prüfen, nicht raten:** Cloudflare → Workers & Pages → der Worker, der
   die Route `abos.franksfinanzcheck.de` bedient. Dort → Settings → Variables
   and Secrets. (CLI-Alternative: `cd newsletter-worker && npx wrangler secret
   list` — der Name kommt aus `wrangler.toml`, das ist `ff-newsletter`. Passt
   der nicht zur Route, im Dashboard arbeiten.)
2. **Worker-Seite:** `EXPORT_KEY` auf den neuen Zufallswert setzen (Encrypt /
   `printf '%s' "<wert>" | npx wrangler secret put EXPORT_KEY`).
   `EXPORT_KEY_WRITE` **nicht** anfassen — die Rollen müssen verschieden bleiben.
3. **GitHub-Seite, direkt danach** (das Fenster, in dem der alte Wert ungültig
   ist, soll Minuten dauern, nicht Tage):
   ```bash
   gh secret set NEWSLETTER_WORKER_EXPORT_KEY --body "<wert>"
   ```
4. **Gegenprobe** (ohne den Schlüssel irgendwohin zu schreiben):
   ```bash
   NEWSLETTER_WORKER_BASE=https://abos.franksfinanzcheck.de \
   NEWSLETTER_WORKER_EXPORT_KEY="<wert>" npm run betrieb:check:live
   ```
   *Erwartet:* `schluesselrollen: getrennt`, kein `403` in den Exporten.

### Abschluss (5 Minuten)

```bash
gh workflow run sicherheits-wache.yml --ref main
gh run watch
```
*Erwartet:* Schritt 4 (Header) `success`, Schritt 6 (Worker) `success`,
Schritt 7 (Live-Nachweis) `success`, Schritt 10 (Selbstheilung) `success` oder
`warning`.

### Stop-Regeln (lieber abbrechen als erzwingen)

| Meldung | Bedeutung | Was dann |
|---|---|---|
| `Zone … nicht eindeutig im Konto des Tokens` | Token sieht mehrere Zonen | Token auf **eine** Zone einschränken, neu messen — keine Ersatzzone |
| `❌ DNS … nicht vollständig proxied` | orangene Wolke fehlt | erst DNS (Runbook A1, Schritt 1), dann erneut |
| SSL-Modus würde sinken | Schutzverlust | Apply verweigert das selbst — nichts umgehen, melden |
| `betrieb:check:live` weiter `403` | Werte auf beiden Seiten ungleich | Schritt 2 und 3 wiederholen, **nicht** `EXPORT_KEY_WRITE` als Ersatz nehmen |

### Was ich von Ihnen zurückbrauche

1. Die Ausgabe von `npm run edge:freigabe` (vorher) und `:apply` (nachher).
2. Die Ausgabe von `npm run header:check:live`.
3. Das Ergebnis von `npm run betrieb:check:live` — **ohne** Schlüsselwert.
4. Die Lauf-ID des Abschlusslaufs.

Damit prüfe ich gegen die Artefakte (`f01-live.md`, `worker-live.md`) und melde
zurück, ob der Nachweis wirklich vollständig ist — nicht nur der Exit-Code.

---

## 1. Lage — gemessen, nicht behauptet

| Befund | Quelle | Ergebnis |
|---|---|---|
| F-01 Sicherheits-Header | Lauf `45151875836`, Schritt 4 „Sicherheits-Header auswerten“ | **BEFUND** auf allen drei Zielen (`/`, `/methodik/`, `https://www.…/`) |
| Fehlende CSP-Herkünfte | dito, Diagnose | `https://static.cloudflareinsights.com` fehlt in `script-src`, `https://cloudflareinsights.com` fehlt in `connect-src` — je Ziel, also **6 Meldungen** |
| Proxy | dito (`cf-ray` vorhanden) | **aktiv** → die Ursache ist die Transform Rule, kein DNS- oder Proxy-Problem |
| Worker | Schritt 6 „Worker-Zustand auswerten“ | **STOERUNG**: `NEWSLETTER_WORKER_EXPORT_KEY` (GitHub) ≠ `EXPORT_KEY` (live laufender Worker `ff-newsletter-2026-10-24`) |
| F-01 Selbstheilung | Schritt 10 | **failure** — sie ist absichtlich gesperrt (fail-closed), solange `CF_EDGE_HEAL_TOKEN` und `CF_EDGE_AUTOHEAL=true` fehlen; sie hat den Befund korrekt **nicht** grün gemacht |
| Repo-Soll | `python3 scripts/blog_header_gate.py --offline` (Selbsttest + Prüfung) | **grün** — `static/_headers` enthält beide Beacon-Domains bereits |
| B7 Datenschutz | `python3 scripts/cloudflare_edge_freigabe.py --b7-check` | **✅ erfüllt** („Datenschutz B7 bereits auf Cloudflare-Proxy umgestellt“) |
| Frontmatter-Bestand | `python3 scripts/frontmatter_wache.py --pfad content --json` | 174 Dateien, **0 Blocker, 0 Hinweise** |
| Inhaltsbefunde | `unittest` der drei Module (unten) | **3 rot, auf `main` reproduziert** — Textbefunde, kein Code-Befund |
| Verwaiste Seiten | `unittest scripts.tests.test_gsc_abdeckung` auf `main` (48da9e8) | war **rot** (zwei Seiten ohne Inlink), inzwischen auf `main` geheilt — die Ursache nicht (Nachtrag, Abschnitt 5a) |

**Wichtig für die Einordnung:** Das Repo beschreibt den Sollzustand bereits
exakt (`cloudflare/edge-schutz.md` A1, `static/_headers`, Dieselbigkeit wird
offline geprüft). Die Lücke liegt ausschließlich zwischen Sollstand und
Cloudflare-Zone. Deshalb ist der erste Schritt keine Entwicklung, sondern eine
Freigabe.

---

## 2. Entscheidung A — Edge-Regel `FF Sicherheits-Header`

**Risiko:** hoch (CSP ohne Beacon = Web Analytics stumm; ohne Regel = gar keine
Sicherheits-Header auf `www`) · **Aufwand:** ~15 Minuten · **Wirkung:** F-01 auf allen drei
Zielen, plus Schritt 10 wird erstmals überhaupt arbeitsfähig.

**Entscheidung:** Die Regel wird **per Skript** hergestellt, nicht per Hand
getippt — und die Selbstheilung wird danach scharfgeschaltet, damit derselbe
Befund nicht in vier Wochen wieder auftaucht.

**Warum nicht per Hand:** Die Regel hat acht Kopfzeilen, davon eine CSP mit
23 Direktiven. Ein Tippfehler darin ist unsichtbar (der Browser warnt bei
fehlenden Kopfzeilen nicht) und die Wache meldet ihn erst am nächsten Morgen.
Das Skript liest den Sollstand aus der Tabelle in `cloudflare/edge-schutz.md`
und schreibt idempotent; es stuft ein bestehendes `Full (strict)` **nie** herab.

**Schritte (Betreiber, in dieser Reihenfolge):**

1. Zone-Token mit genau diesen Rechten auf **diese eine** Zone anlegen:
   `Zone.DNS:Edit`, `Zone.Settings:Edit`, `Zone.Transform Rules:Edit`.
   Nicht den Worker-Deploy-Token wiederverwenden (Runbook A1c, Punkt 2).
2. Ist gegen Soll messen:
   `CLOUDFLARE_API_TOKEN=… npm run edge:freigabe`
   Erwartet in der Ausgabe: die drei fehlenden Herkünfte und der Host-Filter
   ohne `www`.
3. Herstellen:
   `CLOUDFLARE_API_TOKEN=… npm run edge:freigabe:apply`
4. Datenschutz unmittelbar danach erneut prüfen (der Apply aktualisiert B7):
   `npm run edge:b7` → grün.
5. Selbstheilung scharfschalten (erst nach Schritt 3, sonst heilt sie ins
   Nichts): GitHub → Settings → Secrets → neues Secret `CF_EDGE_HEAL_TOKEN`
   (derselbe Zonentoken) · Settings → Variables → `CF_EDGE_AUTOHEAL` = `true`.
6. Live nachmessen: `gh workflow run sicherheits-wache.yml --ref main`, dann
   `gh run watch`.

**Ohne API-Token (Fallback, gleiche Sitzung):** die kopierfertige
Dashboard-Anleitung ausgeben lassen und die Regel einmal einfügen —
`python3 scripts/cloudflare_edge_freigabe.py --dashboard`. Der Filter muss
**beide** Hosts nennen:
`(http.host eq "franksfinanzcheck.de" or http.host eq "www.franksfinanzcheck.de")`.

**Abnahmekriterium:** Im neuen Lauf ist Schritt 4 `success` (Klassifikation
`OK` auf allen drei Zielen), Schritt 10 `success` oder `warning`, und
`curl -sI https://www.franksfinanzcheck.de/ | grep -i content-security-policy`
zeigt `static.cloudflareinsights.com` und `cloudflareinsights.com`.
Zusätzlich muss der Befund in `f01-live.md` (Artefakt
`sicherheits-live-nachweis`) leer sein — nicht nur der Exit-Code.

**Verantwortlich:** Betreiber (Zugang zur Zone). Ich kann weder Dashboard noch
Zone erreichen und behaupte deshalb **nicht**, dass die Regel jetzt stimmt.

---

## 3. Entscheidung B — Worker-Leseschlüssel rotieren

**Risiko:** mittel (Exporte schlagen fehl; die Wache kann die Schlüsselrollen
nicht bestätigen) · **Aufwand:** ~10 Minuten.

**Entscheidung:** **Rotieren** — neuen Wert auf beiden Seiten setzen. Nicht
„angleichen“.

**Begründung (Korrektur meiner ersten Fassung):** Der dort beschriebene Weg —
„aktuellen Wert aus dem Worker ziehen und in GitHub eintragen“ — ist **nicht
ausführbar**. Cloudflare-Worker-Secrets sind write-only; `wrangler secret list`
nennt nur Namen, die Werte sind weder über CLI noch über die API lesbar. Bleibt
die Rotation. Sie ist hier unkritisch, weil den Leseschlüssel ausschließlich
drei GitHub-Workflows über **ein** Secret konsumieren (`newsletter-daily.yml`,
`newsletter-lifecycle.yml`, `sicherheits-wache.yml`) — kein n8n-Lauf, kein
externer Dienst, keine Browser-Erweiterung.

**Schritte (Betreiber):**

1. Neuen Wert erzeugen: `openssl rand -hex 32` → Passwortmanager.
2. Ziel verifizieren, nicht raten: In Cloudflare → Workers & Pages der Worker,
   der die Route `abos.franksfinanzcheck.de` bedient (Dashboard → Settings →
   Variables and Secrets). Der Name in `wrangler.toml` ist `ff-newsletter`;
   weicht die Route davon ab, im Dashboard arbeiten.
3. Worker-Seite: `EXPORT_KEY` auf den neuen Wert setzen.
   `EXPORT_KEY_WRITE` **nicht** anfassen — die Rollen müssen verschieden
   bleiben (Runbook A4).
4. GitHub-Seite, unmittelbar danach:
   `gh secret set NEWSLETTER_WORKER_EXPORT_KEY --body "<wert>"`.
5. Gegenprobe ohne Schlüssel im Klartext:
   ```bash
   NEWSLETTER_WORKER_BASE=https://abos.franksfinanzcheck.de \
   NEWSLETTER_WORKER_EXPORT_KEY="<wert>" npm run betrieb:check:live
   ```

**Wichtig zur Reihenfolge:** Zwischen Schritt 3 und 4 sind Exporte kurzzeitig
gesperrt (fail-closed). Deshalb beide Schritte in einer Sitzung, nicht über
Tage verteilt — und nicht am Monatsanfang, wenn `newsletter-lifecycle` läuft.

**Abnahmekriterium:** `betrieb:check:live` meldet `schluesselrollen: getrennt`
und keinen `403` in den Exporten; der Wache-Lauf hat Schritt 6 auf `success`
und `worker-live.md` sagt `OK` statt `STOERUNG`. Erst dann kann Schritt 7
(Live-Nachweis) überhaupt grün werden.

**Verantwortlich:** Betreiber (Secrets). Ein „irgendwie gleich“ ist kein
Nachweis — der Nachweis ist der grüne Schritt 6.

---

## 4. Entscheidung C — M1-Titel (Textentscheidung, nicht meiner)

**Risiko:** niedrig (Metadaten, keine Aussage) · **Aufwand:** 20 Minuten
inklusive Siegel.

**Befund:** `content/posts/2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen/index.md`
— Titel 64 Zeichen, Grenze 60 (`M1`, `scripts/metadaten_wache.py`).

**Entscheidung:** Ich empfehle diesen Titel, **ändere ihn aber nicht**:

> `Kfz-Versicherung vergleichen: Was ändert sich am Beitrag?` — 57 Zeichen

**Warum ich ihn nicht selbst setze:** Der Titel ist die Überschrift eines
fremden Artikels; der Grundsatz dieses Repos ist, Fremdinhalte zu melden statt
sie umzuschreiben. Und: Die Änderung ist **nicht** harmlos — das Frontmatter
ist Teil des `content_fingerprint`, ein Titelwechsel entwertet das bestehende
redaktionelle Siegel. Wer den Titel ändert, muss die Fachfreigabe tragen und
**neu siegeln** (`editorial_review_gate.py --seal`, nur mit Freigabe). Ein
Siegel ohne erneute Textprüfung wäre genau die „gefälschte Freigabe“, die das
Repo an anderer Stelle verbietet.

**Schritte (Betreiber/Redaktion):**

1. Titel übernehmen (oder anders entscheiden — dann muss er ≤ 60 Zeichen sein).
2. `python3 scripts/editorial_review_gate.py --seal` **nur** mit Freigabe.
3. `python3 scripts/editorial_review_gate.py --published --strict` →
   `4 freigegeben · 0 blockiert`.
4. `python3 scripts/metadaten_wache.py` → 0 Befunde; der Test
   `scripts.tests.test_metadaten_wache` wird grün.

**Verantwortlich:** Redaktion (Text) + Fachfreigabe (Siegel).

---

## 5. Entscheidung D — die drei Textbefunde: Termine, kein Aufräumen

Diese drei sind **keine** Code-Befunde und **keine** Nebengeräusche. Sie sind
auf `main` reproduziert. Sie laufen im PR-Gate
`publication-reliability-tests.yml` (Schritt „Code-Regression“) mit — jeder PR
an `scripts/**`, `content/**` oder `layouts/**` macht sie sichtbar —, sie
blockieren den Merge aber nicht: Der Stand ist auf `main` identisch, und #1307
wurde mit genau diesen drei Befunden bewusst und dokumentiert gemergt. Sie
bleiben rot, bis sie redaktionell erledigt sind. Deshalb bekommen sie ein
Datum und keine Ausnahme.

```bash
python3 -m unittest scripts.tests.test_einzigartigkeit_1027 \
  scripts.tests.test_einzigartigkeit_bestand scripts.tests.test_faktenfrische_763
# → Ran 46 tests, FAILED (failures=3)
```

| # | Befund | Datei | Aufgabe | Termin (Vorschlag) |
|---|---|---|---|---|
| D1 | Flesch **59,9** < Schwelle 60 (R6) | `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` | Zwei bis drei Sätze teilen, ohne Inhalt zu verlieren; Messung erneut ausführen | 30.11.2026 |
| D2 | **5 gleiche Phrasen** im Live-Paar | `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` ↔ `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | Eine der beiden Passagen eigenständig umformulieren (nicht die andere löschen) | 07.12.2026 |
| D3 | Rechtliche Pauschalaussage **entfernt** | `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen`, FAQ „Sind Cashback-Apps sicher für meine Daten?“ — der Satz „Das lässt sich nicht pauschal zusagen.“ fehlt | Satz zurückholen; er ist der Grund, warum die Antwort nicht als Zusage gelesen werden kann | 30.11.2026 |

**Abnahmekriterium je Punkt:** das obige Kommando nennt den Befund nicht mehr;
alle 46 Tests grün. **Verantwortlich:** Redaktion. **Nicht** delegierbar an die
Automatik: D2 und D3 sind Aussagen über Recht und Inhalt, D1 ist Stil — kein
Skript darf sie erfinden.

---

## 5a. Nachtrag (23.11.2026) — ein fünfter Befund, und er ist eine Störung

Beim Abschluss dieses PRs gemessen, **auf `main` ohne meine Änderung**
(Worktree auf `origin/main` @ `48da9e8`):

```
python3 -m unittest scripts.tests.test_gsc_abdeckung
→ FAIL: BestandOhneInseln.test_keine_inhaltsseite_ohne_redaktionellen_inlink
```

Zwei Inhaltsseiten haben keinen redaktionellen Inlink:

* `/posts/2026-11-13-geschirrspueler-voll-so-sparst-du-wasser-und-strom/`
* `/posts/2026-11-20-mehrwegflaschen-pfand-so-optimierst-du-deine-fixkosten/`

**Nachtrag zum Nachtrag (23.11., 10:49Z):** Der *Befund* ist auf `main`
inzwischen weggeheilt (`5f12dcc`) — die beiden Seiten haben wieder Inlinks, der
Test ist grün. Die **Ursache** steht unverändert: `gsc-import.yml` ist seit dem
19.11. in jedem Lauf rot (vier Läufe, immer derselbe Schritt). Der nächste
Automatik-Artikel, der vor dem Heiler erscheint, erzeugt denselben Befund neu.
Deshalb bleibt der Punkt auf der Liste — als Störung, nicht als Textaufgabe.

**Das ist kein Redaktionsbefund, obwohl es wie einer aussieht.** Das Repo heilt
verwaiste Seiten selbst (`gsc_abdeckung.py --verlinkung --heilen`, im
Tageslauf `gsc-import.yml`, Schritt 8). Dieser Schritt wurde aber seit
mindestens drei Tagen **übersprungen**, weil der Lauf vorher stirbt:

| Lauf | Datum | Ergebnis | Tödlicher Schritt |
|---|---|---|---|
| `45026814884` | 22.11. | failure | 6 „Leistungsdaten holen (searchAnalytics, nur lesend)“ |
| `44908881174` | 21.11. | failure | dito |
| `44749084253` | 20.11. | failure | dito |

Schritt 6 rot → Schritt 8 „Selbstheilung – verwaiste Seiten verlinken“
**skipped** → die beiden Seiten bleiben unverlinkt → der Regressionstest bleibt
rot. Die Kette ist gemessen, nicht vermutet (Job-Steps über die Actions-API).

**Entscheidung:** Das ist eine **Störung** (Zugangsdaten/Abruf der
Search-Console-Leistungsdaten), keine Textaufgabe — und sie heilt sich nicht
selbst, weil der Heiler hinter dem toten Schritt steht.

**Schritte (Betreiber):** Re-Run von `gsc-import.yml` mit Blick auf Schritt 6
(`gh run view 45026814884 --log` bzw. Re-Run → Schrittprotokoll). Ist es der
GSC-Zugang: Zugangsdaten erneuern, Lauf wiederholen. Danach läuft Schritt 8
automatisch und setzt die Inlinks; die Redaktion muss nichts schreiben.

**Abnahmekriterium:** `gsc-import.yml` grün bis Schritt 8; danach
`python3 -m unittest scripts.tests.test_gsc_abdeckung` → 119 Tests OK. Der
ReDoS-Job des PR-Gates wird damit ebenfalls grün — er prüft diese Suite mit.

**Verantwortlich:** Betreiber (Zugang). **Nicht** die Redaktion: einen Inlink
von Hand zu setzen wäre das Symptom, nicht die Ursache — und beim nächsten
Automatik-Artikel stünde derselbe Befund wieder da.

## 6. Warum diese Reihenfolge

1. **A zuerst**, weil eine Änderung F-01 auf allen drei Zielen schließt und den
   Selbstheilungsmechanismus erstmals benutzbar macht. Solange die Regel fehlt,
   ist jede andere Diskussion über „grün“ gegenstandslos — der Live-Nachweis
   kann nicht grün werden.
2. **B danach**, weil sie unabhängig ist, aber den zweiten roten Schritt
   schließt. Beide zusammen machen den Live-Nachweis (Schritt 7) grün.
3. **C** ist eine Textentscheidung mit Siegel-Folge. Sie darf warten, bis A und B
   stehen — sie ändert nichts an der Live-Sicherheit.
4. **D** läuft parallel in der Redaktion und ist bewusst **nicht** Teil des
   Live-Nachweises: Textqualität ist kein Sicherheitsbefund.
5. **5a** steht am Ende, weil es die geringste Wirkung auf die Sicherheit hat —
   aber es ist die einzige Position, die einen *toten Automatikschritt*
   offenlegt. Bleibt sie liegen, wächst die Zahl verwaister Seiten mit jedem
   Automatik-Artikel.

## 7. Abgrenzung (was hier nicht entschieden wird)

- **Kein** neues Werkzeug für #1313: Die Wache prüft doppelte YAML-Schlüssel
  seit diesem Zweig in **jeder** Ebene (Scanner ohne Parser + strenger
  PyYAML-Loader als Gegenprobe). Belegt: 42 Tests, Mutationsprobe rot,
  174 Bestandsdateien ohne Fehlalarm.
- **Keine** Änderung an Artikeln, Titeln oder Siegeln durch mich.
- **Keine** Behauptung über Livezustände: Alles, was Dashboard, Zone oder
  Secrets betrifft, steht hier als Abnahmeschritt, nicht als Ergebnis.
