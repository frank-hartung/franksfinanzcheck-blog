# Entscheidungsvorlage: die vier roten Punkte

**Stand:** 23.11.2026 · **Basis:** `main` @ `f405f49` (Squash-Merge #1307) ·
**Messung:** Lauf [`45151875836`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/45151875836)
(`sicherheits-wache.yml`, `workflow_dispatch`, 23.11.2026 09:58Z)

**Die Empfehlung in einem Satz:** Der Code ist auf Soll — es fehlen vier
Betreiber-/Redaktionshandlungen. Sie werden **in dieser Reihenfolge** erledigt:
Edge-Regel (behebt 6 von 8 Live-Befunden mit einer Änderung), Worker-Leseschlüssel,
M1-Titel, dann die drei Textbefunde als datierte Redaktionsaufgaben.

Kein Punkt dieser Vorlage ist ein Programmierauftrag. Wer hier Code ändert,
ändert am falschen Ende.

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

**Wichtig für die Einordnung:** Das Repo beschreibt den Sollzustand bereits
exakt (`cloudflare/edge-schutz.md` A1, `static/_headers`, Dieselbigkeit wird
offline geprüft). Die Lücke liegt ausschließlich zwischen Sollstand und
Cloudflare-Zone. Deshalb ist der erste Schritt keine Entwicklung, sondern eine
Freigabe.

---

## 2. Entscheidung A — Edge-Regel `FF Sicherheits-Header`

**Risiko:** hoch (CSP ohne Beacon = Web Analytics stumm; ohne Regel = gar keine
Sicherheits-Header auf `www`) · **Aufwand:** ~15 Minuten · **Wirkung:** 6 der
8 Live-Befunde, plus Schritt 10 wird erstmals überhaupt arbeitsfähig.

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
   `CF_API_TOKEN=… npm run edge:freigabe`
   Erwartet in der Ausgabe: die drei fehlenden Herkünfte und der Host-Filter
   ohne `www`.
3. Herstellen:
   `CF_API_TOKEN=… npm run edge:freigabe:apply`
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

## 3. Entscheidung B — Worker-Leseschlüssel abgleichen

**Risiko:** mittel (Exporte schlagen fehl; die Wache kann Schlüsselrollen nicht
bestätigen) · **Aufwand:** ~10 Minuten.

**Entscheidung:** Den **GitHub-Wert an den laufenden Worker anpassen**, nicht
umgekehrt.

**Begründung:** `EXPORT_KEY` ist das Secret, mit dem der laufende Worker
`ff-newsletter-2026-10-24` bereits arbeitet. Ihn zu drehen hieße: Worker neu
deployen, alle Aufrufer mitziehen, in der Zwischenzeit fail-closed. Der
GitHub-Wert ist ein Verbraucher, kein Vertragspartner — er wird nachgezogen.

**Schritte (Betreiber):**

1. Den aktuellen Wert von `EXPORT_KEY` aus dem Worker ziehen
   (`cd newsletter-worker && npx wrangler secret list` zeigt nur Namen; den
   Wert nur aus dem eigenen Secret-Store, nie im Chat, nie im Repo).
2. GitHub → Settings → Secrets and variables → Actions →
   `NEWSLETTER_WORKER_EXPORT_KEY` auf genau diesen Wert setzen.
3. **Nicht** `EXPORT_KEY_WRITE` / `NEWSLETTER_WORKER_WRITE_KEY` mitziehen —
   die beiden Rollen müssen verschieden bleiben (Runbook A4).
4. Gegenprobe:
   ```bash
   NEWSLETTER_WORKER_BASE=https://abos.franksfinanzcheck.de \
   NEWSLETTER_WORKER_EXPORT_KEY=… python3 scripts/worker_betrieb_wache.py
   ```
   Erwartet: kein 401/403, `schluesselrollen: getrennt`.

**Abnahmekriterium:** Neuer Wache-Lauf, Schritt 6 `success`; `worker-live.md`
enthält `OK` statt `STOERUNG`. Erst dann ist der Live-Nachweis (Schritt 7)
überhaupt grün werden **können**.

**Verantwortlich:** Betreiber (Secrets). Ein Abgleich „irgendwie gleich“ ist
kein Nachweis — der Nachweis ist der grüne Schritt 6.

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

## 6. Warum diese Reihenfolge

1. **A zuerst**, weil eine Änderung sechs Befunde schließt und den
   Selbstheilungsmechanismus erstmals benutzbar macht. Solange die Regel fehlt,
   ist jede andere Diskussion über „grün“ gegenstandslos — der Live-Nachweis
   kann nicht grün werden.
2. **B danach**, weil sie unabhängig ist, aber den zweiten roten Schritt
   schließt. Beide zusammen machen den Live-Nachweis (Schritt 7) grün.
3. **C** ist eine Textentscheidung mit Siegel-Folge. Sie darf warten, bis A und B
   stehen — sie ändert nichts an der Live-Sicherheit.
4. **D** läuft parallel in der Redaktion und ist bewusst **nicht** Teil des
   Live-Nachweises: Textqualität ist kein Sicherheitsbefund.

## 7. Abgrenzung (was hier nicht entschieden wird)

- **Kein** neues Werkzeug für #1313: Die Wache prüft doppelte YAML-Schlüssel
  seit diesem Zweig in **jeder** Ebene (Scanner ohne Parser + strenger
  PyYAML-Loader als Gegenprobe). Belegt: 42 Tests, Mutationsprobe rot,
  174 Bestandsdateien ohne Fehlalarm.
- **Keine** Änderung an Artikeln, Titeln oder Siegeln durch mich.
- **Keine** Behauptung über Livezustände: Alles, was Dashboard, Zone oder
  Secrets betrifft, steht hier als Abnahmeschritt, nicht als Ergebnis.
