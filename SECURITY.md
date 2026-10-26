# Sicherheitsrichtlinie

## Sicherheitslücken vertraulich melden

Bitte veröffentliche Sicherheitslücken **nicht** als öffentliches Issue.
Nutze stattdessen GitHubs private Sicherheitsmeldungen:

1. Öffne **Security → Advisories → New draft security advisory**.
2. Beschreibe Auswirkung, betroffene Dateien/Versionen und – soweit möglich – eine Reproduktion.
3. Teile keine Zugangsdaten, Tokens, personenbezogenen Daten oder Newsletter-Adressen in Logs oder Screenshots.

Falls private Meldungen auf GitHub nicht angeboten werden, kontaktiere den Betreiber über die im Impressum der Website genannte Adresse und kennzeichne die Nachricht mit „VERTRAULICH – SECURITY“.

## Reaktionsziel

- Eingangsbestätigung: möglichst innerhalb von 3 Werktagen
- Erste Risikobewertung: möglichst innerhalb von 7 Werktagen
- Veröffentlichung: erst nach Bereinigung oder abgestimmter Frist

## Unterstützte Version

Unterstützt wird ausschließlich der aktuelle Stand des Default-Branches `main` und die daraus veröffentlichte Website.

## Geheimnisse

GitHub-Tokens, API-Schlüssel und Newsletter-Geheimnisse gehören ausschließlich in GitHub Actions Secrets bzw. die dafür vorgesehene Betriebsumgebung. Ein versehentlich veröffentlichtes Geheimnis muss sofort widerrufen und ersetzt werden; das bloße Entfernen aus der Git-Historie genügt nicht.

## Prozessstarts

Produktive Python-Skripte starten externe Programme ausschließlich mit expliziten Argumentvektoren (`subprocess.run([...], shell=False)`). Shell-Ausführung (`shell=True`, `os.system`, `os.popen`) ist untersagt: dynamische Werte wie Slugs, Workflow-Namen und Pfade müssen jeweils ein einzelnes Argument bleiben und, wo sinnvoll, vorab validiert oder URL-kodiert werden.

Der Regressionstest `scripts/tests/test_command_execution_security.py` erzwingt diese Regel für alle produktiven Skripte. Änderungen an einem Prozessstart müssen diesen Test erweitern und dürfen keine Ausnahme von der Regel einführen.

### Externe Dateipfade (seit Meldung #559 / Code-Scanning-Alert 60, 04.10.2026)

Werden einem externen Programm Dateipfade aus offenen Eingängen (Webhook, CLI,
Inbox-Verzeichnis) übergeben, gilt ein verschärfter Vertrag, erzwungen durch
`WhisperEngineExternalPathContract` im selben Regressionstest:

1. Der Pfad wird vor der Übergabe zu einem absoluten Kanon aufgelöst und geprüft
   (reguläre Datei, keine NUL-Zeichen, kein Dateiname mit führendem „-“) und
   liegt zwingend innerhalb vertrauenswürdiger Verzeichnis-Wurzeln (Repo,
   System-Temp, optional `WHISPER_AUDIO_ROOTS`) — ein Webhook-Pfad kann damit
   keine beliebigen Host-Dateien als Eingabe missbrauchen.
2. Statt des Pfades selbst wird nur ein geöffneter Datei-Deskriptor durchgereicht
   (`-f /proc/self/fd/<n>` mit `pass_fds`): Die Prozesszeile enthält strukturell
   keinen extern kontrollierten Wert, und der Kindprozess liest exakt den
   geprüften Inode (kein Zeitfenster zwischen Prüfung und Ausführung).
3. Modell-, Sprach- und sonstige Optionswerte stammen ausschließlich aus
   Whitelists im Betreibercode — unbekannte Werte werden abgelehnt (fail-closed).
4. Kein „--“-Trennzeichen bei Tools, deren Parser unbekannte Argumente abbricht
   (whisper.cpp beendet sich dann mit Exit-Code 0 und Usage-Text); dort schützt
   die Kombination aus Kanonisierung und Deskriptor-Übergabe.


## Zugangs-Namensvertrag und Klartext-Wache (Code-Scanning-Alerts #78/#80, 05.10.2026)

Der Betrieb veröffentlicht laufend Statusberichte (Social-Preflight, Cockpit,
Redaktions-Scorecard, Governance-Kontrakt, Schaltwerk-Ereignisse) nach STDOUT,
in Markdown-Dateien und in JSON-Artefakte. Darin dürfen **Namen** von
Umgebungsvariablen stehen (`MASTODON_ACCESS_TOKEN`), **niemals deren Werte**.
Damit diese Trennung nicht nur gemeint, sondern lesbar und maschinell prüfbar
ist, gilt:

1. **Felder, die Variablennamen führen, heißen `pflicht_env` / `fehlende_env`**
   (in der stabilen JSON-Oberfläche: `required_env_names`, `missing_env_names`,
   `required_var_names`, `missing_var_names`). Felder, die Ampel- oder
   Nachweis-Metadaten führen, tragen das Präfix `zugang_` / `zugangsalter_`.
2. **Verboten als Namensbestandteil** in berichtsnahen Strukturen sind
   `secret`, `trusted`, `confidential`, `pass*` (`password`, `passcode`,
   `passphrase`, …), `oauth`, `api_key` / `api_tok` und `mfa` – das ist exakt
   die Menge, die CodeQLs `SensitiveDataHeuristics` als „führt Zugangsdaten“
   liest (reine Namensheuristik, auch für Funktionsnamen). Ein Name aus dieser
   Menge ist eine Behauptung über den Inhalt; wo nur Namen und Ampeln
   transportiert werden, ist sie falsch – für Menschen die Vorstufe eines
   echten Lecks, für die Analyse ein Befund.
3. **Werte bleiben draußen.** Kein Bericht darf den Inhalt einer
   Umgebungsvariablen in Ausgabe, Datei oder Artefakt tragen.
4. **Clear-Text-Funde werden nie unterdrückt.** Für die Regeln
   `py/clear-text-logging-sensitive-data` und
   `py/clear-text-storage-sensitive-data` gibt es keine `# codeql[...]`-
   Unterdrückung – sie stehen auch nicht in der Unterdrückungs-Whitelist der
   CodeQL-Wache. Funde dieser Klasse werden an der Quelle geheilt.

Erzwungen wird der Vertrag auf vier unabhängigen Ebenen:

- `scripts/tests/test_zugangs_namensvertrag.py` baut die CodeQL-Heuristik
  nach, prüft rekursiv die erzeugten Berichtsstrukturen, vergiftet alle
  Zugangsvariablen mit einem Marker und verbietet Clear-Text-Unterdrückungen.
- `scripts/clear_text_logging_guard.py` verfolgt sensible Quellen
  inhaltsbezogen bis zu Logging- und Klartext-Speichersenken über **alle**
  versionierten sowie neuen, nicht ignorierten Python-Dateien. Ein echter
  `# codeql[...]`-Kommentar für die beiden Regeln ist selbst ein Befund.
- `scripts/tests/test_clear_text_logging_security.py` verankert Eigenprüfung,
  Repository-Nullbefund und den Namen der geheilten #80-Fundstelle.
- Der eigenständige CI-Job `klartext-wache` läuft fail-closed und unabhängig
  von CodeQL-SARIF-Upload und GitHub-Default-Setup.

Jede Wache trägt Positiv- und Gegenproben; eine stumpf gewordene Kontrolle wird
somit selbst rot. Beweisführung und Runbook:
`CODE-SCANNING-ALERT-78-DAUERHEILUNG-PREMIUM-2026-10-05.md` und
`CODE-SCANNING-ALERT-80-PREMIUM-2026-10-05.md`.

## Host-Vertrag und URL-Wache (Code-Scanning-Alert #83, 10.10.2026)

Eine URL ist eine strukturierte Adresse, keine Zeichenkette mit Bedeutung. Wer
Herkunft, Ziel oder Zugehörigkeit einer Adresse mit `in`, `startswith`,
`endsWith` oder `includes` beurteilt, prüft Text statt Host – und lässt
`https://unser-host.de.angreifer.example/` passieren. Für dieses Repository
gilt deshalb:

1. **Host parsen, nicht Zeichenkette vergleichen.** Die einzige Wahrheit ist
   `scripts/url_host.py` (`ist_host`, `ist_host_oder_subdomain`, `nennt_host`,
   `ruft_host_an`, `hat_link_auf_host`). Eigene Host-Logik wird nicht gebaut.
2. **Subdomains nur über die Punkt-Grenze.** `ist_host_oder_subdomain()` –
   niemals `endsWith(".beispiel.de")`, das erlaubt `boeseebeispiel.de`.
3. **Erwähnung ist kein Aufruf.** Prüft eine Regel den Quelltext anderer
   Skripte, zählt nur ein echtes URL-Literal im AST (`ruft_host_an()`), nicht
   die Nennung in Kommentar, Dokumentation oder Fixture.
4. **Herkunftsprüfungen zur Laufzeit parsen.** CORS-Freigaben im
   Cloudflare-Worker entscheiden über `new URL()`, erzwingen `https:` und
   prüfen den Hostnamen – bewacht von Regel KA10 in
   `scripts/ki_assistent_gate.py`.
5. **URL-Funde werden nie unterdrückt.** Für
   `py/incomplete-url-substring-sanitization` und
   `js/incomplete-url-substring-sanitization` gibt es keine
   `# codeql[...]`-Unterdrückung – und seit dem 10.10.2026 gibt es in der
   CodeQL-Wache überhaupt **keine Unterdrückungs-Whitelist mehr**: Jede
   unterdrückte Fundstelle lässt den Lauf scheitern.

Erzwungen wird der Vertrag auf vier unabhängigen Ebenen:

- `scripts/url_substring_guard.py` prüft **Python, JavaScript und HTML** (AST,
  echter JS-Lexer, eingebettete `<script>`-Blöcke) fail-closed: Nicht
  analysierbarer Quelltext ist ein Fehler, kein „sauber“.
- `scripts/tests/test_url_substring_security.py` verankert Eigenprüfung,
  Repository-Nullbefund, die geheilten Fundstellen, die Umgehungstabelle und
  das Verbot der Whitelist – inklusive Rückfall-Probe mit den historischen
  Mustern.
- `cloudflare/ki-assistent/test/worker.test.mjs` prüft die CORS-Entscheidung
  gegen sechs Umgehungsversuche.
- Der eigenständige CI-Job `url-wache` läuft fail-closed und unabhängig von
  CodeQL-SARIF-Upload und GitHub-Default-Setup.

Beweisführung und Runbook:
`CODE-SCANNING-ALERT-83-DAUERHEILUNG-PREMIUM-2026-10-10.md`.

## Reguläre Ausdrücke mit begrenzter Komplexität (Code-Scanning-Alert Nr. 87, 26.10.2026)

CodeQL meldete in `scripts/gsc_abdeckung.py` einen `py/redos`-Fund: Ein
mehrzeiliges Muster für `sitemap.disable` kombinierte `\s+`, `.*` und einen
weiteren `\s+` so, dass Eingaben aus `sitemap:\n` und vielen `\t\n`-Paaren
exponentiell viele Zerlegungen erzeugten. `py/redos` trägt
`security-severity 7.5` – die Regel ist ein Sicherheitsfund, kein
Qualitätshinweis. Seitdem gilt:

1. **Strukturierte Formate werden gelesen, nicht erraten.** Frontmatter,
   CSV-Blöcke und eingerückte Konfigurationen werden zeilenweise und mit
   klaren Bereichsgrenzen geparst. `scripts/gsc_abdeckung.py` benutzt dafür
   `sitemap_deaktiviert()` – ohne `re.*`, in linearer Zeit.
2. **Alle ReDoS-Regeln sind hart.** `py/redos`, `py/polynomial-redos`,
   `js/redos` und `js/polynomial-redos` stehen namentlich im Security-Gate von
   `.github/workflows/codeql.yml`. Ein fehlendes SARIF-Metadatum darf sie nicht
   zu einem Qualitätshinweis herabstufen.
3. **Keine Unterdrückung.** Funde werden an der Quelle geheilt; Inline-Kommentare
   oder Ausnahmelisten sind kein Schließpfad.
4. **Lokale Rückfallsperre.** `scripts/redos_guard.py` analysiert den Python-AST
   und die Struktur statischer Muster. Regel R0 meldet unlesbaren Quelltext,
   Regel R1 die historische Newline-Pumpe. Der Job `redos-wache` läuft ohne
   SARIF-Upload und ohne Alert-API. CodeQL bleibt bewusst der Generalist für
   neue ReDoS-Klassen.

```bash
npm run redos:wache     # Wache + Bestand
npm run test:redos      # Wache + 98 Vertragstests
npm run redos:wache:json
```

Beweisführung und Runbook:
`CODE-SCANNING-ALERT-87-REDAUERHEILUNG-HIGHEND-2026-10-26.md`.

## Abhängigkeiten: Pin, Audit, Wache (24.10.2026)

GitHub meldete am 24.10.2026 **58 offene Schwachstellen** auf `main`
(7 kritisch, 30 hoch, 18 mäßig, 3 niedrig), während der ausgelieferte Bestand
im selben Moment nach vollständiger Prüfung gegen dieselbe Advisory-Datenbank
**0 Fundstellen** hatte. Zwei Lehren stehen seitdem als Vertrag:

1. **Ein Pin ist eine Aussage, ein Bereich ist eine Hoffnung.** Jede
   Anforderung in `requirements*.txt` und `requirements-ci.in` nennt eine
   exakte Version (`==`). Ein Bereich (`>=`, `~=`, `*`) löst Dependabot
   **einmal** auf und hält das Ergebnis fest – Änderungen an der
   Hash-Sperrdatei lösen keine neue Auflösung aus. Genau so überlebten
   Alarme ihre eigene Heilung. Erzwungen von `scripts/abhaengigkeits_wache.py`
   (Regel A1) bei jedem Push.
2. **Die Alarmtabelle ist ein Cache, kein Beweis.** Der Sicherheitsstatus
   wird am **Bestand** gemessen, nicht an GitHubs Anzeige. Die
   Abhängigkeits-Wache prüft bei jedem Push offline (Pins, Quelle ↔
   Hash-Lock, Lockfiles, Action-SHAs, Image-Tags) und im Tageslauf online
   (jede ausgelieferte Version gegen die GitHub Advisory Database).

**Betrieb**

```bash
npm run deps:check    # offline, Sekunden, blockiert bei Struktur-Befund
npm run deps:audit    # online, ~300 Abfragen, Exit 1 bei Fundstelle
npm run test:deps     # Selbsttest (Sabotage + Gegenproben) und Vertragstests
```

Exit-Codes sind Klassen, keine Stimmungen – dieselbe Systematik wie bei der
Sicherheits-Wache (Vertrag C34):

| Exit | Bedeutung | richtige Reaktion |
|---|---|---|
| 0 | sauber | – |
| 1 | Befund | Version auf `first_patched_version` pinnen, PR, Wache erneut laufen lassen |
| 2 | Störung | Netz/API nicht erreichbar – **kein** Freibrief: ungeprüft ist nicht sauber |

**Kein Dismiss ohne Messung.** Ein GitHub-Alert darf erst geschlossen werden,
wenn die Wache dieselbe Aussage stützt: Entweder nennt sie die Fundstelle
(dann wird sie geheilt), oder sie weist nach, dass die betroffene Version im
Bestand nicht mehr vorkommt. „Sieht alt aus“ ist keine Begründung.

Regressionstests: `scripts/tests/test_abhaengigkeits_wache.py` (33 Verträge,
u. a. der Dauervertrag „der Bestand hat keine Struktur-Fehler“). CI:
`.github/workflows/sicherheits-wache.yml`, Job **Abhängigkeiten (Pins offline ·
Audit online)** – offline bei jedem Push, online im Tageslauf.
Beweisführung: `ABHAENGIGKEITS-SICHERHEIT-PREMIUM-2026-10-24.md`.
