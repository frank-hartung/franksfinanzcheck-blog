# Taxonomie-Gate von der Reserve-Rotation entkoppelt (Premium-Fix, 01.10.2026)

## Vorfall

- **Run:** KI-Redaktion · main (`2ed9d76`) · [36853928089](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/36853928089)
- **Schritt:** „Taxonomie-Gate nach Writer-Lauf" → `tag_governance.py --check` Exit 1
- **Fund:** `[T4] Tag 'Haftpflichtversicherung' hat nur 1 Artikel (mind. 2)`
- **Folgeschaden:** Auch „Deploy auf GitHub Pages" (36854253830) brach am selben
  Gate – main wurde nicht mehr ausgeliefert.

## Ursachenkette (drei Ebenen)

1. **Auslöser:** Die Reserve-Rotation (`bd245bbb`, „unabhängige Redaktionsreserve
   auffüllen") löschte den E-Bike-Reserveentwurf – den einzigen zweiten Träger
   des Tags `Haftpflichtversicherung`.
2. **Messfehler (der eigentliche Defekt):** `tag_governance.py` zählte Entwürfe
   mit `reserve: true` in der Wirksamkeits-Zählung (T4/T8) mit. Die Reserve
   rotiert aber frei – das Gate hing damit an einer Zufallsgröße. Dazu kommt:
   Drafts werden nicht gebaut, Hugos Related-Matching sieht sie nie. Ein
   Reserve-Entwurf kann einen Ein-Artikel-Tag also nur auf dem Papier „gesund"
   rechnen, nie auf der Live-Seite. `Girokonto` und `Kreditkarte und Kredit`
   hingen zum Zeitpunkt des Vorfalls ebenso an Entwürfen – dieselbe Mine,
   nur noch nicht explodiert.
3. **Redaktioneller Befund:** `Haftpflichtversicherung` trug live tatsächlich
   nur EINEN Artikel – nach Hausregel (T4-Meldung, Präzedenzfall
   Tierkrankenversicherung im Register) gehört so ein Tag in den breiteren Tag
   überführt.

## Dauerhafte Behebung

### 1. Messgenauigkeit: Reserve zählt nicht (scripts/tag_governance.py)

- Artikel mit `reserve: true` haben **kein Gewicht mehr in T4/T8**. Gezählt
  werden Live-Artikel und geplante Pipeline-Entwürfe – Bestand, der wirklich
  auf die Live-Seite zuläuft.
- Ein Register-Tag, den **nur** die Reserve trägt, ist ein **Hinweis (weich)**
  statt einer Blockade – die Rotation kann das Gate in keine Richtung mehr
  kippen.
- Reserve-Entwürfe behalten die **volle Hygiene** (T2/T3/T5/T6/T7) samt
  `--apply`-Heilung.
- `--report` weist Reserve-Nutzung jetzt separat aus (`(+n Reserve)`),
  `--json` liefert `reserve_nutzung`.

### 2. Redaktion: Tag überführt (data/seo/tag_register.yaml)

- `Haftpflichtversicherung` ist – wie zuvor die Tierkrankenversicherung – als
  Synonymblock unter `Versicherungen vergleichen` überführt (inkl.
  Privathaftpflicht/Rechtsschutz-Synonyme), mit datiertem Kommentar und
  dokumentiertem Rückweg (≥ 2 zählbare Artikel → wieder eigener Tag).
- `--apply` hat den einen Trägerartikel geheilt:
  `tags: ["Versicherungen vergleichen", "Gesundheit und Vorsorge"]`.
- Künftige Artikel aus `data/topics.yaml` (Keywords „Privathaftpflicht",
  „Rechtsschutzversicherung" …) mappen über die Synonyme automatisch korrekt.

### 3. Sabotage-Schutz: 4 neue Selbsttests (19 → 23)

- **20** Ein Reserve-Entwurf rechnet einen Ein-Artikel-Tag NICHT gesund (T4 bleibt).
- **21** Zwei zählbare Artikel bleiben grün – egal, was die Reserve tut.
- **22** Reserve-only-Tag ⇒ Hinweis (weich), keine Blockade.
- **23** `--apply` heilt Synonyme auch in Reserve-Entwürfen (Hygiene unberührt).

## Beweis

- `tag_governance.py --selftest`: **23 bestanden, 0 fehlgeschlagen**
- `tag_governance.py --apply`: 1 Datei normalisiert, danach grün
- `tag_governance.py --check`: **„Taxonomie sauber"**, Exit 0
- Gesamte Testsuite: **1143 passed, 23 skipped, 1224 subtests** – keine Regression
- Kein Tag unter `min_artikel_pro_tag` in der zählbaren Nutzung; `Girokonto`
  (3 zählbar) und `Kreditkarte und Kredit` (3 zählbar) stehen auch ohne
  Reserve stabil.

## Warum das dauerhaft ist

Das Gate misst jetzt dieselbe Realität, die es schützt: die Live-Seite und
ihre geplante Pipeline. Die Reserve kann rotieren, auffüllen und löschen, ohne
die Taxonomie-Wache zu berühren – weder KI-Redaktion noch Deploy können durch
eine Reserve-Rotation erneut auf Rot springen. Der verbleibende redaktionelle
Hebel (Tag unter Minimum durch echte Live-Änderungen) bleibt bewusst hart und
fail-closed, mit dokumentiertem Überführungs-Muster im Register.
