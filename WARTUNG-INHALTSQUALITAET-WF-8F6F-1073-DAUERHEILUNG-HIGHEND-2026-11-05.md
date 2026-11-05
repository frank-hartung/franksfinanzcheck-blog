# WF-8F6F / #1073 – ein Datums-Lift darf Fachbefunde nicht verwaisten lassen

Stand: 5. November 2026. Auftrag: „Bitte dauerhaft auf Highend-Level einer
Profi-Agentur beheben." Lokale Umsetzung auf dem Arbeitsbranch
`arena/c48b551c-franksfinanzcheck-blog`, Freigabe über Pull Request.
Der Vorgang **schließt sich nicht über „Closes #1073"**, sondern über den
ersten grünen Lauf von „Faktenfrische (Bestand)" auf `main` – das ist der
Schließpfad, den `alert_resolve_gate.py` verlangt (Job `recherche` grün).
Ein Merge ist kein Beweis; ein grüner Lauf ist einer.

## Ausgangslage

Der Alarm vom 05.11.2026, 13:41:48 UTC (Run
[42029331057](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/42029331057),
Commit `97b00832`, Event `schedule`) meldete:

> **Faktenfrische (Bestand) ist fehlgeschlagen**
> Job **„recherche"**
> ([Log](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/42029331057/job/127251432455))
> – „Unterdeckung oder Befund ohne Schließweg melden (roter Job)"

Die Annotation desselben Check-Runs nannte die Ursache beim Namen:

> Mindestens ein offener Fachbefund hat keinen Schließweg

Die Kapazitätswache war im selben Lauf grün (Deckung 143 %). Es ging also
nicht um Budget, Kadenz oder einen toten Kanal, sondern um die Aktenwache:
Ein offener Befund, den kein Mensch mehr entscheiden kann, ist ein
struktureller Fehler – und genau so war er gebaut.

## Beweisführung

| Beobachtung | Beleg |
|---|---|
| Fünf offene Befunde zeigten auf den Slug `2026-11-01-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu`, Fassungsanker `c13cf12ed8da…`, zuletzt gesehen `2026-11-03 12:18 UTC`. | `data/faktenfrische_queue.json` → `fachbefunde` (IDs `0b564f460c41218244bd`, `3ad2eefed314eb172c26`, `43788c2cdcdfda52e753`, `5eedec8afbdef6a4ca49`, `81881c5bc61824d25f5a`) |
| Dieser Ordner existiert seit dem 05.11.2026, 11:36:10 UTC nicht mehr. | Commit `8bd4e2e3` „content: unabhängige Redaktionsreserve auffüllen" (Content-Bot, Workflow `content-reserve.yml`), Renamenachweis `R058 content/posts/2026-11-01-heizoel-…/index.md → content/posts/2026-11-05-heizoel-…/index.md` |
| Der Artikel selbst ist unverändert weitergewandert: gleicher Text, `draft: true`, `reserve: true`, `redaktionelle_pruefung.status: ausstehend`, Risikoklasse `erhoeht`. | `content/posts/2026-11-05-heizoel-…/index.md` |
| Der Finisher hat **alles mitgenommen, was ihm gehört** – Cover-Manifest, Custody, Readiness, Quarantäne, Themen-Ledger, Historie – nur nicht die Befundidentität, die einem anderen Vertrag gehört. | Commit-Stat von `8bd4e2e3` (`data/covers_manifest.json`, `data/reserve-custody.json`, `data/reserve-readiness.json`, `data/reserve-quarantine.json`, `data/reserve-topic-ledger.json`, `data/reserve-history.jsonl`) |
| Das Ledger suchte die Fassung unter `fassungen[entry["slug"]]`, fand nichts und meldete `seite-fehlt` → „nicht entscheidbar". | `scripts/faktenfrische_befund_ledger.py`, `fassung_status()` (Stand vor der Heilung) |
| Die Akte druckte für alle fünf Befunde „Seite nicht lesbar – nicht entscheidbar" und nannte als Schließweg eine Entscheidung an einer Seite, die es nicht gibt. | `BEFUND-AKTE.md` und `data/faktenfrische_befunde_state.json` im Baum von `ff49235` (`seite_fehlt: 5`, `nicht_entscheidbar: 5`) |
| Es war kein Einzelfall: Im selben Commit wurde auch `2026-11-01-fenster-abdichten-…` auf `2026-11-05-…` gehoben (`R057`). Dort lagen nur keine offenen Befunde. | Commit-Stat von `8bd4e2e3` |

Die Kette ist damit lückenlos: **`reserve_finisher.lift_to_today()` ändert den
Ordner-Slug, die Befundidentität bleibt absichtlich historisch.** `befund_id()`
wird aus Slug und Beanstandung gebildet – sie ist ein Beweisanker, kein
URL-Schmuck. Beide Seiten hatten recht; es fehlte die Verbindung zwischen
ihnen. Das Ergebnis war kein falscher Befund, sondern ein **unentscheidbarer**
Befund: Die Wache blieb rot, und der angezeigte Schließweg war unmöglich.

## Warum das kein „nochmal starten" ist

Ein Neustart hätte dieselben fünf Einträge in derselben Queue gefunden und
dieselbe rote Aktenwache geschrieben. Drei Schichten waren zu trennen:

1. **Der Schreibvorgang** (Reserve-Finisher) kennt den alten Slug nur im
   Moment des Umbenennens – danach ist er weg.
2. **Die Befundidentität** (Faktenfrische-Ledger, Vertrag #912) darf sich
   nicht mit dem Datum mitbewegen, sonst würde ein Re-Dating Befunde
   stillschweigend neu erzeugen oder – schlimmer – entschärfen.
3. **Die Sicht für Menschen** (`BEFUND-AKTE.md`, Publish-Gate) muss den
   Befund am Artikel zeigen, den die Redaktion heute öffnen kann.

## Heilung

### 1. Der Finisher trägt die Herkunft mit – atomar

Neu in `scripts/reserve_finisher.py`:

```python
def mit_faktenfrische_alias(text: str, alter_slug: str) -> str:
    """Alten Ordner-Slug idempotent als interne Befund-Herkunft eintragen."""
```

`lift_to_today()` ruft sie nach dem Datums-/`lastmod`-Sync auf. Der alte Slug
landet als `faktenfrische_aliases` im Frontmatter **desselben Artikels**:

```yaml
faktenfrische_aliases:
  - "2026-11-01-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu"
```

- **Idempotent:** Ein zweiter Lift am selben Tag schreibt nichts (kein
  zweiter Hash, keine neue Dateiversion, kein Zertifikats-Drift).
- **Kettenfähig:** Ein weiterer Lift auf ein neues Datum ergänzt den
  Zwischen-Slug und behält die früheren Einträge – die Kette bleibt lesbar.
- **Rollback-sicher:** Frontmatter und Artikelkörper sind dieselbe Datei und
  liegen damit im selben Finisher-Snapshot. `restore_snapshots()` stellt bei
  einem katastrophalen Abbruch beides gemeinsam wieder her; es kann kein
  Alias ohne Artikel und kein Artikel ohne Alias entstehen.
- **Kein Eingriff in den Text:** Der Artikelkörper, alle übrigen Metadaten und
  der Prüfstatus bleiben exakt unangetastet. Das Feld ist interne Herkunft,
  **keine** öffentliche Weiterleitung – `data/weiterleitungen.yaml` ist dafür
  unverändert geblieben, und kein Template liest das Feld.

### 2. Das Ledger projiziert – ohne zu entscheiden

Neu in `scripts/faktenfrische_befund_ledger.py`:

- `bestand_identitaeten()` liest Fassungen **und** Alias-Karte aus demselben
  Bestands-Schnappschuss (ein Importfehler bleibt Werkzeugfehler, kein
  stilles „keine Seiten").
- `canonical_slug()` löst die Kette auf den aktuellen Slug auf und ist
  fail-closed: Schleife, Selbstreferenz, leeres Ziel → `LedgerFehler`.
- `offene_eintraege()` projiziert jeden Befund auf den aktuellen Slug,
  behält `id`, `fassung_sha256`, `text_sha256`, Beanstandung und Beleg
  unverändert und führt die Herkunft als `ursprungs_slug` mit.
- Entscheidungen werden **am alten und am neuen Slug** gesucht, aber weiter
  fassungsgebunden geprüft: Eine Entscheidung, deren geprüfte Fassung nicht
  mehr die heutige ist, schließt nichts. Neue Entscheidungen dokumentieren
  `befund_ursprung_slug`.
- `fassung_status()` prüft jetzt zuerst, ob die Seite überhaupt lesbar ist,
  und erst danach, ob ein Fassungsanker fehlt. Damit kann ein Altbestand
  ohne Hash nicht mehr durch Löschen der Seite „erledigt" aussehen.
- Kollisionen sind Werkzeugfehler: Ein Alias, der auf einen lebenden Slug
  zeigt, oder ein Alias mit zwei Zielartikeln, bricht den Lauf ab – eine
  Mehrdeutigkeit darf niemals einen Befund auf den falschen Artikel
  projizieren.

### 3. Akte, Zustand und Publish-Gate folgen derselben Identität

- `BEFUND-AKTE.md` zeigt die Befunde unter dem aktuellen Artikel, nennt die
  Herkunft ausdrücklich („Befund-ID und Fassungsanker bleiben unverändert;
  das Re-Dating ist keine fachliche Entscheidung") und druckt die fertigen
  `--entscheiden`-Befehle für die fünf IDs.
- `data/faktenfrische_befunde_state.json` führt `ursprungs_slug` nur dort,
  wo eine Herkunft existiert – das Siegel bleibt schlank und vergleichbar.
- `publish_gate.fakten_befund_failures()` arbeitet auf der Projektion: Der
  Kandidat `2026-11-05-heizoel-…` ist mit denselben fünf IDs blockiert.

## Datenheilung: fünf Befunde waren unentscheidbar

| Kennzahl (`faktenfrische_befund_akte.py --wache`) | vorher | nachher |
|---|---|---|
| Offene Befunde | 47 | **47** (unverändert – nichts wurde geschlossen) |
| Seiten betroffen | 11 | 11 |
| Seite fehlt | 5 | **0** |
| Nicht entscheidbar | 5 | **0** |
| Text seit dem Befund geändert | 13 | 18 |
| Altbestand ohne Fassungs-Hash | 15 | 15 |
| Aktenwache | 🛑 rot | ✅ grün |

Nachweis im echten Bestand (kein Mock):

```
$ python3 scripts/faktenfrische_befund_ledger.py --wache
✅ Jeder offene Befund hat einen dokumentierten Schließweg …
$ python3 scripts/faktenfrische_befund_akte.py --wache
Offene Fachbefunde: 47 auf 11 Seiten · überholte Fassung: 18 · ohne Fassung: 15
$ publish_gate.fakten_befund_failures(["2026-11-05-heizoel-…kaufzeitpu"])
→ blockiert mit 0b564f460c41218244bd, 3ad2eefed314eb172c26, 43788c2cdcdfda52e753,
  5eedec8afbdef6a4ca49, 81881c5bc61824d25f5a  (tool_error=False, warning=None)
```

**Was das bedeutet:** F4 (offener Fachbefund) blockiert den Heizöl-Entwurf
weiter – das ist der Vertrag aus #912, kein neuer Fehler. Der Artikel ist ein
Reserve-Entwurf (`draft: true`) mit ausstehender redaktioneller Prüfung
(Risikoklasse `erhoeht`). Es wurde **kein** Artikeltext geändert, **kein**
Befund geschlossen, **keine** Entscheidung erfunden und **kein** Stempel
gesetzt. Die fünf Befunde warten auf genau die menschliche Entscheidung, die
die Akte jetzt wieder erreichbar macht.

## Was ausdrücklich nicht angefasst wurde

- `data/faktenfrische_queue.json` und `data/research/artikel/…`: unverändert
  (Diff leer). Historische Befunde behalten ihren historischen Slug und ihre
  IDs; die Nachlese ergänzt weiterhin nichts ohne echten Fassungs-Hash.
- Entscheidungslogik: Die Bindungsregeln aus #912 (zwei Hashes, Textänderung
  öffnet erneut, Quellenpflege öffnet nicht) gelten unverändert.
- Intervalle, Fälligkeitsregel, Budget, Kadenz, Allowlist, KI-Routing und das
  Anti-Halluzinations-Gate: unverändert.
- Keine öffentliche URL-Änderung, kein Redirect, keine Sitemap-, Cover- oder
  Template-Änderung; `data/integrity_lock.json` berührt keine der geänderten
  Dateien.

## Tests und Nachweise

| Prüfung | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_faktenfrische_slug_identitaet` | **9 Tests grün** (neu; vor der Implementierung 2 Failures + 5 Errors) |
| `python3 scripts/faktenfrische_befund_ledger.py --selftest` | grün (neu: Re-Dating-Aliasse, Kette, Schleife, Löschschutz) |
| `python3 scripts/faktenfrische_befund_akte.py --selftest` | grün |
| `python3 scripts/reserve_finisher.py --selftest` | grün (neu: Alias-Pflege, Idempotenz, Kette) |
| `npm run test:faktenfrische` | **124 Tests grün** (Suite um die neue Regression erweitert) |
| `npm run test:reserve` | 329 Tests grün (Finisher, Snapshots, Zertifikate, Heiler-Deckung) |
| Frontmatter-, Publish-Gate- und YMYL-Regressionen | 73 Tests grün |
| `python3 scripts/faktenfrische_kapazitaet.py --wache` | grün, Deckung 143 % |
| `python3 scripts/faktenfrische_befund_ledger.py --nachlese` | Trockenlauf: nichts ergänzt, Queue unverändert |
| `python3 scripts/selftest_runner.py --ohne-uhr-probe` | 268 Wachen, 267 gelaufen, **1 roter Punkt – identisch zur Basis**: `cover_render_check.py` ohne installiertes `pillow` (Umgebung, nicht dieser Vorgang) |
| `git diff --check` | sauber |

Die neue Regression ist als Sabotagetest gebaut: Sie verlangt Projection,
Kette, Kollision, echte Löschung, fassungsgebundene Alt-Entscheidung,
menschliche Entscheidung am neuen Text und die Publish-Gate-Blockade – und
sie lief **vor** der Implementierung rot.

## Grenzen (ehrlich)

- **Rückwirkend gilt der Vertrag nicht automatisch.** Renames vor dieser
  Heilung tragen kein `faktenfrische_aliases`. Aktuell ist keine Seite
  betroffen (`seite_fehlt: 0`); sollte je ein Befund auf einen verschwundenen
  Slug zeigen, bleibt die Wache absichtlich rot und die Redaktion trägt den
  alten Slug von Hand nach – genau das ist der fail-closed-Pfad.
- **Eine manuelle Ordner-Umbenennung** (ohne Finisher) muss den alten Slug
  ebenfalls in `faktenfrische_aliases` aufnehmen. Der Vertrag steht in
  `scripts/FAKTENFRISCHE.md`.
- **Löschen bleibt Löschen.** Verschwindet die Seite wirklich, ist der Befund
  nicht entscheidbar und die Wache rot – der Alias heilt keine Löschung, und
  ein Altbestand ohne Fassungs-Hash braucht weiterhin eine reale Seite.
- **Kein Fachurteil.** Diese Heilung macht Entscheidungen wieder möglich; sie
  trifft keine. Die fünf Heizöl-Befunde (saisonale Preisprognose, 10–20 %
  Einsparung, Modellrechnung mit 0,80 €/Liter, 15 % Mehrkosten, Vier-Wochen-
  Faustregel) sind inhaltlich offen und gehören vor eine menschliche Prüfung
  des **heutigen** Textes.
- `faktenfrische_aliases` ist interne Herkunft. Wer öffentliche URLs sichern
  will, braucht weiterhin `data/weiterleitungen.yaml`.

## Schließpfad

1. Review und Merge dieses Zweigs nach `main`.
2. Der nächste Lauf von **Faktenfrische (Bestand)** muss grün sein
   (Job `recherche`, Schritt „Unterdeckung oder Befund ohne Schließweg
   melden"). Erst dieser Lauf schließt #1073.
3. Die fünf Heizöl-Befunde bleiben offen, bis Herausgeber/Redaktion sie mit
   `scripts/faktenfrische_befund_ledger.py --entscheiden <ID> --von … --begruendung …`
   fassungsgebunden entscheidet. Die fertigen Befehle stehen in
   `BEFUND-AKTE.md`.

Regeln: `scripts/FAKTENFRISCHE.md` (Abschnitt „Datums-Lift und
Befundidentität (#1073)"), `scripts/faktenfrische_befund_ledger.py`,
Governance C46.
