# #634 – sechs Premium-Reserveentwürfe dauerhaft abgesichert

**Stand:** 08.10.2026 · **Bezug:** bereits gemergter [PR #634](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/634) · **Ausgangsstand:** `a96825ed471f038038a95452ebc60f4974612d8a`.

## Ergebnis und Grenzen

- **Ziel 6, tatsächlich zertifiziert 6, Pool 15.** Frischer Vollbeleg: `data/reserve-readiness.json`, erzeugt **2026-10-08T14:28:25Z**.
- Die sechs Originaldateien wurden mit echter Hunspell/de_DE-Messung, Quality-Score und den echten Publikations-/Hugo-Gates in einer Veröffentlichungssimulation abgenommen. Anschließend wurden ihre Originalbytes wiederhergestellt und unabhängig gegen die SHA-256-Werte geprüft.
- Alle sechs bleiben `draft: true` und `reserve: true`. Es gab **keine Veröffentlichung, keine erfundene menschliche Freigabe und keine Absenkung der Schwellen** (Quality ≥ 0,85; Flesch ≥ 60; Lesbarkeits-Score ≥ 75; Zielbestand 6).
- Die anderen neun Kandidaten sind weiterhin ehrlich **nicht READY**. Ihre RS2-/RS3-/RS5-Funde stehen im Beleg; ein hoher Summenscore ersetzt keine belegten Zahlen, Modellannahmen oder passende Redaktion.
- Das ist ein technischer/redaktioneller Gate-Nachweis, keine fingierte Schlussfreigabe durch eine Person. Nach Verbrauch, Textänderung oder Ablauf der maximal 36 Stunden muss die reguläre Produktionslinie nachfüllen bzw. neu messen.

| Entwurf | Quality | Flesch | SHA-256 (Präfix) |
|---|---:|---:|---|
| 7 Gewohnheiten für finanzielle Freiheit | 0.96 | 61.5 | `3d426ed649a5` |
| Campingurlaub planen | 0.96 | 66.1 | `b4bd7156457a` |
| DSL-Anbieter wechseln | 0.95 | 63.3 | `10bcde7652f0` |
| Handyvertrag kündigen | 0.95 | 61.7 | `b826e3b0beec` |
| Urlaub sparen | 0.96 | 61.1 | `f3412b02755b` |
| Smart Home: Stromersparnis prüfen | 0.96 | 62.5 | `2eb4aaeeaba6` |

Die vollständigen 64-stelligen Hashes, Teilwerte und Gründe aller 15 Kandidaten liegen im versionierten Zertifikat. Keine Zertifizierung nur anhand dieser Tabelle.

## Ursache – warum die alte Reparatur nicht dauerhaft hielt

Git behandelte ganze Maschinenbelege und geprüfte Textfassungen als unabhängig kombinierbare Zeilen. Parallele Änderungen produzierten deshalb:

1. ein unlesbares Readiness-/Quarantäne-Dokument mit vermischten Laufständen;
2. doppelte Custody-Schlüssel (darunter `zuletzt_im_pool`) – Python hätte still nur den letzten Wert behalten;
3. gültiges, aber redaktionell beschädigtes Markdown: bei Camping und DSL wurden alte, unbelegte Textblöcke an die geprüfte Fassung angehängt; beim Urlaubstext kam ein zusätzlicher H1-Block zurück.

Die GitHub-Abnahmen zu #634 meldeten außerdem doppelte YAML-Schlüssel beim Campingtext. Die inzwischen vorhandene F1–F7-Frontmatter-Wache wird weiter genutzt, nicht durch einen eigenen toleranteren Parser umgangen.

**Wiederherstellungsquelle:** Die vollständige, belegbare Redaktion und die intakten Gedächtnisstände aus dem bereits gemergten [PR #638](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/638), Commit `05fb8ee26ad1260f8350125e10c0176245c8b4e8`. Wiederhergestellt wurden die drei beschädigten Textkörper (Camping, DSL, Urlaub); die neueren Metadaten des aktuellen Bestands blieben erhalten. Die drei anderen Premiumtexte wurden nicht umgeschrieben. Der alte Beleg wurde **nicht** als heutiger Nachweis ausgegeben: alle sechs aktuellen Bytefassungen wurden neu gemessen.

## Dauerhafte Schutzkette

### 1. Ein Parser, ein bytegebundener READY-Begriff

`scripts/reserve_artifacts.py` liefert striktes JSON und die gemeinsamen Quellenprüfungen:

- doppelte Schlüssel auf jeder Ebene, `NaN`/Infinity/überlaufende Zahlen und Nicht-Objekt-Wurzeln werden verworfen;
- eine beschädigte Kandidatenzeile, doppelte/unsichere Slugs, Nicht-Boolean-READY oder ein fehlender READY-SHA machen den ganzen Beleg ungültig;
- READY zählt nur bei tatsächlicher Datei im eigenen Pool, passendem **Rohbyte-Hash**, gültigem F1–F7-Frontmatter, echten Draft-/Reserve-Fahnen und ohne Blockiert-/Zurückgezogen-/Veröffentlicht-Marke;
- CRLF wird nur zur Metadatenprüfung normalisiert, nie zur Quellen-Hashbildung;
- Pool, End-Gate, Konvergenz, Finisher, Generator und Watchdog benutzen diesen gemeinsamen Nachweis. Der Summenzähler ist keine Autorität.

Auch die Randpfade sind eingeschlossen: Intake deutet korruptes Custody nicht als „herrenlos“; Ziel-Diagnose und Lesbarkeits-Heiler lesen strikt; das Cockpit zeigt überprüfte Quellenzahlen statt eines zusammengefügten `ready: 6`. Unlesbare oder abgelaufene Belege sind dort ausdrücklich **ungeprüft**, nicht grün.

### 2. Atomare vollständige Zustände

Readiness, Nachzertifizierung, Custody, Quarantäne und der Janitor schreiben vollständige Dokumente über denselben atomaren Writer: temporäre Datei auf demselben Dateisystem → Flush/fsync → strikte Rückleseprobe → Rechte bewahren → `os.replace`. Fehler vor dem Austausch lassen den bisherigen Beleg erhalten; temporäre Dateien werden aufgeräumt.

Auch ein syntaktisch intakter Readiness-Beleg wird bei beschädigtem benachbartem Custody-/Quarantäne-Gedächtnis nicht als gesund gezählt. Der Vollaufbau stoppt dann vor jeder Mutation; nur fehlende Erstlauf-Gedächtnisse dürfen neu entstehen.

Der Janitor überspringt beschädigte Pruning-Eingaben mit sichtbarer Warnung und verändert sie nicht. Fehlende Historie darf in erlaubten Erstlauf-Pfaden fehlen; **korrupte** Historie darf niemals als leeres Gedächtnis gelten.

### 3. Keine stillen Git-Textchimären

`.gitattributes` verwendet `merge=binary` für die drei Reserve-Snapshots und die sechs Premium-Textstämme, auch nach einem Datums-Lift. Das deaktiviert den Zeilen-Zusammenschnitt, nicht die lesbare Git-Diff-Anzeige.

`git_sync.sh` behandelt Konflikte nach Bedeutung:

- **Readiness:** eine ganze Laufversion auswählen; vor dem Staging striktes JSON prüfen. Die finalen Quellen-/Frische-Gates entscheiden weiterhin über ihre Gültigkeit.
- **Custody/Topic-Ledger:** schlüsselbasierte Gedächtnisvereinigung; jüngerer Eintrag gewinnt bei derselben Identität.
- **Quarantäne:** gleicher Fund vereinigt unterschiedliche Lauf-IDs, zählt keine Wiederholung desselben Laufs doppelt und bewahrt den ersten Fundzeitpunkt. Ein neuer Fund erbt keine alten Treffer.
- **Beschädigte Konfliktseite:** harter Stopp, niemals still `{}` einsetzen oder ein defektes Dokument stagen.
- LIVE- und menschliche Content-Konflikte bleiben ein manueller Stopp. Keine neuen Löschrechte.

### 4. Echte Werkzeuge und unveränderte Messlatte

Voll- und Nachzertifizierung nutzen denselben Werkzeug-Preflight. Ein vorhandener Hunspell-Pfad genügt nicht: `Haushalt` muss erkannt und `Fheler` als falsch gemeldet werden. Fehlendes Hugo, fehlendes de_DE-Wörterbuch, eine leere scheinbar fehlerfreie CLI-Ausgabe oder eine kaputte Analyse halten die Zertifizierung **vor jeder Mutation** an (Exit 3). Kein frischer Beleg aus `spelling=0.5` („unbekannt“).

Die Veröffentlichungssimulation hasht/restauriert die Originalbytes, einschließlich CRLF. Eine erst im Gate vorgeheilte andere Fassung kann die unveränderte Originalfassung nicht zertifizieren.

Der Produktions-End-Gate bleibt fail-closed: fehlender/defekter Zeitstempel, mehr als fünf Minuten Zukunft oder mehr als 36 Stunden Alter scheitern. Fehlerhafte Alters-Overrides fallen auf 36 Stunden zurück. Der billige Offline-PR-Check kontrolliert bewusst Struktur/Quellen/Redaktion, nicht das Wanduhralter des nächtlichen Belegs; ein alter PR muss nicht aus Datumsgründen seine Offline-Tests verlieren.

### 5. CI und Integrität

`publication-reliability-tests.yml` reagiert jetzt auch auf reine Reserve-State- oder `.gitattributes`-Änderungen und prüft den vollständigen Offline-Beleg **vor** der gesamten Unit-Suite. Die bestehenden Uhr-, KI-/Netz- und Ledger-Isolationsproben bleiben erhalten.

Der neue gemeinsame Helfer ist im Integrity-FEST-Kern registriert und zusammen mit dem reparierten Stand versiegelt: **48 geschützte Dateien**. Die Signatur gehört mit dem Code in denselben Commit; der entsprechende Repository-Test wird nicht abgeschwächt.

## Nachweise

| Prüfung | Ergebnis |
|---|---|
| Echte Vollzertifizierung + anschließender Quellen-End-Gate | **6/6**; weitere **9** bewusst nicht READY |
| `npm run reserve:check` | striktes JSON, vollständige Zählung, Originalhashes und Redaktionsvertrag grün |
| `npm run test:reserve` | **213 Tests bestanden** |
| Komplette Python-Suite (`unittest discover -s scripts/tests -q`) | **2.350 Tests bestanden**, keine Skips, 217,0 s |
| Komplette Suite unter `--offset 97` | **grün**: 2.350 Tests, davon 2.348 bestanden und 2 bestehende Echttags-Proben übersprungen, 208,2 s |
| Workflow-Selbsttests unter KI-/Netzsperre | **98 Selbsttests bestanden**, gleiche Ergebnisse mit/ohne Testschlüssel |
| Redaktionsstandard-Selbsttest | **31 eingefrorene Fälle bestanden** |
| Produktions-Hugo, danach Desktop-/Mobil-Playwright | **80 Seiten gebaut; 108 Browsertests bestanden** |
| Integritäts-Gate | **48 Dateien unverändert zum signierten Stand; 9 Selbsttests bestanden** |

Die beiden bereits vorgesehenen Uhr-Skips sind die Janitor-Echttagsprobe am realen Bestand und der Newsletter-Realfall aus den letzten 50 Tagen. Beide wurden in der Basissuite tatsächlich ausgeführt und bestanden; unter einer künstlichen Zukunftsuhr wäre derselbe historische Bestand keine passende Fixture. Keine neuen Skips hinzugefügt. Governance-Vertrag/-Gate, Workflow-Audit, Frontmatter-, Ledger-Isolations-, Reserve-Gate- und Konvergenz-Selbsttests sind ebenfalls grün. Die Tests hinterließen weder Einträge im versionierten Audit-Ledger noch Änderungen an den echten Templates.

**Bisheriger Prüfstand (Commit `132373c`):** Die oben genannten Abnahmen wurden im Sandbox-Checkout wirklich ausgeführt; bis zu diesem Stand gab es noch keinen Push oder Produktionsdeploy.

**Integration am 08.10.2026:** Der inzwischen hinzugekommene Main-Stand `f28ab9ae188d7e39ec73700cc53b7d001a2a9c5d` mit #655 (zentraler KI-Transport) und #656 (Newsletter-Unterpfade) wurde im selben Arbeitsbranch übernommen. Beide Heiler-Importe bleiben erhalten. Beim Ganzdatei-Konflikt des Siegels wurde die vollständige Main-Audit-Kette gewählt und der vereinte 48-Dateien-Kern neu signiert; der eigene Zwischenbeleg bleibt vollständig in Commit `132373c` erhalten. Die Originalbytes aller sechs Entwürfe sind unverändert, Offline-Beleg/Produktions-End-Gate/Driftprüfung sind grün; 61 Integrations-Regressionen sind bestanden. Die Übergabe erfolgt als separater Folge-PR, nicht als automatischer Produktionsmerge. Die abschließende Abnahme des integrierten Standes wird nach den Läufen ergänzt.

Neue Regressionen decken auch echte Zwei-Clone-/Bare-Remote-Konflikte ab: vollständige Readiness-Auswahl, Custody-Erhalt, idempotente Quarantäne-Zählung, neue Fundsignatur und Ablehnung beschädigter Konfliktseiten ohne Remote-Änderung. Weitere Sabotageproben prüfen falsche Hashes/Fahnen, LIVE-Ghosts, Pfadausbruch, CRLF-Restaurierung, Vorheilung, Doppel-JSON/YAML, unbekannte Messwerkzeuge und Schreib-/Rücklese-/Rename-Ausfälle.

`data/audit/2026-10-08.jsonl` erhielt sechs **echte** Affiliate-Wachen-Einträge aus den Veröffentlichungssimulationen, jeweils mit einem gemeldeten Befund (`status: issues`, keine erfundene grüne Quittung). Die Unit-Tests verändern das Beweis-Ledger nicht. Hunspell 1.7.2 mit echtem LibreOffice-de_DE-Wörterbuch und Hugo 0.164.0 Extended wurden lokal benutzt; Werkzeug-Builds, Browser und generierte Seiten sind nicht Bestandteil des Patches.

**Nebenbefund der Vollabnahme:** Ein vorhandener Saison-Integrationstest verglich einen mit der realen Herbstuhr gebauten `public/`-Cache mit der um 97 Tage vorgestellten Python-Winteruhr. Er baut nun isoliert in ein temporäres Verzeichnis mit echtem `hugo --clock` auf genau den geprüften Tag. Kein Saison-Gate wurde gelockert und kein vorhandener Build-Test absichtlich übersprungen. Die vollständige Basis- und Uhr-Suite werden **sequenziell** ausgeführt: die ältere Sitemap-Sabotageprobe ersetzt vorübergehend ein echtes Template und darf nicht mit einem zweiten Suite-Prozess am selben Checkout konkurrieren.

## Runbook – prüfen, bergen, neu zertifizieren

### Schnelle tägliche/PR-Diagnose (offline, keine Veröffentlichung)

```bash
npm run reserve:check
npm run test:reserve
python3 scripts/reserve_recert.py --check
python3 scripts/reserve_gate.py --cert data/reserve-readiness.json
```

`reserve:check` beweist Struktur, tatsächliche READY-Quellen und Redaktion. `reserve_recert --check` erklärt Byte-Drift. Das letzte Kommando ist der **harte**, zeitabhängige Produktions-End-Gate. Nicht aus dem grünen Offline-Check eine abgelaufene Produktionsfreigabe ableiten.

### Bei kaputtem JSON oder Textmerge

1. Automatische Korrekturen/Publikation anhalten. `git status`, `git diff` und die letzten vollständigen, nachweislich gesunden Fassungen prüfen. Bei Konflikten `git show :2:<pfad>` / `git show :3:<pfad>` vergleichen; bei Rebase die vertauschte Seitenbedeutung beachten.
2. Eine **ganze** belegbare Redaktion bzw. einen **ganzen** Snapshot bergen. Neuere korrekte Metadaten nicht blind mit einem älteren Textstand überschreiben. Niemals JSON-Zeilen vereinigen, Duplicate-Keys still ignorieren, Quarantäne/Custody leeren oder `ready`/`target` passend editieren.
3. `npm run reserve:check` ausführen. Änderungen an Text/Fahnen machen frühere Hashes zurecht ungültig: nicht die alten SHA-Werte an neue Inhalte „anpassen“.
4. Mit funktionierendem Hugo und Hunspell/de_DE die echten Produktionsgates neu durchlaufen:

   ```bash
   python3 scripts/reserve_readiness.py
   python3 scripts/reserve_gate.py --cert data/reserve-readiness.json
   npm run reserve:check
   ```

   Bei reiner belegter Byte-Drift kann `python3 scripts/reserve_recert.py --fix` gezielt nachmessen. Bei beschädigtem/fehlendem Gesamtbeleg ist der Vollaufbau notwendig. Werkzeugfehler sind keine redaktionelle Massenabwertung.
5. Nach Simulationen ein gewöhnliches Produktionsartefakt neu bauen, damit keine simulierten Draft-Seiten liegen bleiben:

   ```bash
   hugo --minify --cleanDestinationDir
   npm run test:e2e
   ```

6. Code, Inhalt, vollständige Belege und notwendiges Integrity-Siegel zusammen reviewen/committen. Menschliche Freigaben nicht fingieren, LIVE-Textkonflikte nicht automatisch gewinnen lassen. Erst anschließend den normalen PR-/Produktionsprozess verwenden.

**Wartungsregel:** Neue Reserve-State-Leser/Writer müssen den gemeinsamen Helfer benutzen. Ein neuer nachweisgebundener Premium-Textstamm braucht den gleichen Ganzdatei-Merge-Vertrag. Gesunde Entwürfe behalten, beschädigte Beweise sichtbar stoppen, nicht einen grünen Zähler herstellen.
