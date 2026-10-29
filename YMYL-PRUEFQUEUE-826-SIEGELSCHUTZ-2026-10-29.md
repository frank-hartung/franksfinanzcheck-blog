# Prüfqueue #826: Wiederherstellung und Schreibschutz

Stand: 29.10.2026. Ergänzung zu den Berichten vom 24./25.10.; keine neue
fachliche Freigabe und keine Bescheinigung einer Online-Quellenprüfung.

## Tatsächlicher Ausgangsbefund

Im Checkout: 100 Artikel, 10 Hochrisiko, nur 3 gültige Freigaben,
7 blockiert. Das Ticket vom 28.10. nennt noch 4 offene Entwurfs-Reviews.
Zusätzlich betroffen waren inzwischen Wohngebäude, Kfz und Saison-Update.
Der veröffentlichte Scope enthält derzeit 70 Artikel, keinen Hochrisiko-Artikel.

Die Hashprüfung arbeitete korrekt. Nach der Freigabe wurden Titel bzw.
Descriptions, interne Links, Großschreibung sowie `Euro`/`Prozent` verändert.
Bei Kfz und Saison-Update waren dadurch zusätzlich protokollierte
Zahlenfundstellen nicht mehr wortgleich vorhanden (E13/E19).

## Wiederherstellung ohne Neusiegel

Alle sieben geprüften Fassungen wurden in der Git-Historie gefunden und gegen
den **bereits vorhandenen vollständigen Hash** abgeglichen. Wiederhergestellt
wurden ausschließlich die betroffenen gebundenen Titel/Descriptions und Bodies.
Betriebsmetadaten, Entwurfsstatus, Kadenz, Prüfer, Prüfdatum, Quellen,
Review-Termine und Siegel bleiben unverändert. Kein Aufruf von `--seal`,
kein neuer Audit-Eintrag, keine automatische Wiederveröffentlichung.

Historische Referenzen (jeweils `git show <commit>:<artikelpfad>`):

- Haus / Privathaftpflicht: `bb4d3560b6`
- Wohngebäude: `e83a4b1af3`
- Kfz / Saison-Update: `a5586fbeeb`
- Tierkranken / Zahnzusatz: `490d5b460b`

Auch nicht optimale alte SEO-Formulierungen werden bewusst nicht heimlich
verbessert. Eine neue Fassung braucht eine neue redaktionelle Freigabe.

### Unveränderte, wieder passende Siegel

| Artikel | SHA-256 |
| --- | --- |
| `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | `a7cab88bd880291c9574671aa125b97ce1773f53f20f15f29959d4a08fa476cf` |
| `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | `d10320380068bed39ca060945330801d3868a0794581db6debef193dfcb099d3` |
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | `3d15a0a3c9904002c08218c771558c56bc0ff5df3efd4ccf869977f997bf6fcc` |
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | `746d37806d03c6ccbb510b0399f7079e6cb89d619bd479eb43a6cbb88fb4a909` |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | `94d7967a468ff8d6203172d3b34f76a67dc9b7729c3861cc78389b2bb40f5d93` |
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | `dd4a3d7633e9a13067eb3dad473037f6dbabe6b13e956f2780b09962200aff2f` |
| `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` | `742e8e3d615752e6f5069208c3ea46c6a7230acd788253bfb792a6eaee95ee6b` |

## Prävention

Die bestehenden zentralen Regeln aus `editorial_review_gate` werden jetzt auch
an sieben bislang ungeschützten Wartungswegen verwendet:

- `meta_optimizer.fix_meta`: Prüfung vor Mutation des Arbeitsspeichers.
- `profi_polish.write_polished`: Prüfung vor dem Schreiben.
- `check_titles`: geschützte Titel bleiben unverändert; offene Titelbefunde
  bleiben sichtbar und beeinflussen weiter den Exit-Code.
- `internal_linker`: keine Link-Inserts in geschützte Fassungen.
- `unit_guard`: keine Symbolumwandlung in geschützten Fassungen; übersprungene
  Dateien werden im Bericht ausdrücklich als nicht stilistisch freigegeben geführt.
- `spellcheck`: differenzieller Schreibvertrag unmittelbar vor Dateizugriff.
- `fix_spaces`: differenzieller Schreibvertrag; die etablierte reine
  Leerzeichennormalisierung bleibt möglich, inhaltliche Änderungen nicht.

Der Schutz gilt auch für bereits ungültige oder abgelaufene Siegel. Die
Hashnormalisierung wird nicht erweitert: Euro/€ und Prozent/% bleiben
unterschiedliche Fassungen. Das verhindert, dass Änderungen an Zahlenankern
oder Links als vermeintliche reine Typografie verschwinden.

Neue Regressionen `test_ymyl_maintenance_writers.py` sind im planmäßigen
YMYL-Workflow eingebunden. Sie prüfen echte temporäre Dateien, unveränderten
Arbeitsspeicher, kaputte/abgelaufene Siegel, sichtbare Restbefunde und die
Bindung von Symbolen/Links an die Freigabe.

## Ausgeführte Nachweise

- `editorial_review_gate.py --all --strict`: **100 Artikel, 10 Hochrisiko,
  10 freigegeben, 0 blockiert**, Exit 0.
- `editorial_review_gate.py --published --strict`: 70 Artikel, 0 blockiert.
- Gate-Selbsttest bestanden.
- 17 Gate-, 10 Schreibvertrags-, 5 neue Wartungsschreiber- und 14
  Belegketten-Tests: **46 bestanden** (Belegketten mit simulierten Abrufen).
- Fix-Spaces- und Titel-Selbsttest bestanden.
- Syntaxprüfung der sieben geänderten Schreiber und `git diff --check`: bestanden.

## Verbleibende externe Abnahme

Die vier unklaren Gesetzesquellen aus dem Ticket können hier aufgrund der
Netzfreigaben der Sandbox nicht online nachgeprüft werden. Es wurde weder ein
HTTP-Erfolg noch eine fachliche Neuprüfung behauptet. Der bestehende Workflow
verlangt weiterhin `--require-complete`: Unklare Abrufe verhindern die
Queue-Erledigung. HTTP-Erreichbarkeit allein beweist keine Inhaltsrichtigkeit.
Issue #826 bleibt deshalb offen. Übernahme in main, anschließender realer
Workflow-Lauf und gegebenenfalls inhaltliche Quellen-Nachprüfung stehen noch aus.
