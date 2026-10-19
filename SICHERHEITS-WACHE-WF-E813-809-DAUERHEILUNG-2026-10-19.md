# WF-E813 · #809 — belastbare Messung statt falschem Abschluss

**Stand:** 19.10.2026 · **Umfang:** Sicherheits-Wache, Meldung und Abschlussweg.
**Status:** Quellseitige Fehler korrigiert und lokal geprüft. Die produktive
Cloudflare-Einrichtung und eine neue vollständige Live-Abnahme sind damit
**nicht** durchgeführt. Keine Sicherheitsregel wurde abgeschaltet, kein Secret
verändert, kein produktiver Worker deployt und kein Issue manuell geschlossen.

## 1. Belegte Ursachen

### Wiederholung durch falschen Abschluss

Die Vorgängermeldung #798 wurde am 18.10.2026 mit Verweis auf den grünen Lauf
[39125154809](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/39125154809)
geschlossen. Die Jobs-API belegt: Ereignis `push`, Branch `main`, Quellseite
`success`, **Live-Messung `skipped`**. Der Abschluss bewies keinerlei Behebung
an der Edge. Der nächste tägliche Lauf eröffnete #809 erneut.

### Zwei rote Prüfpfade, aber nur ein Handlungsweg

Im zu #809 gehörenden Lauf
[39254264963](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/39254264963)
sind Header-Auswertung **und** Worker-Prüfung fehlgeschlagen. Die Check-API
belegt für F-01 fehlende/falsche Pflicht-Header und die Diagnose eines nicht
aktiven Cloudflare-Proxys. Die Worker-Annotation nannte lediglich `BEFUND`,
keine konkrete Abweichung. Das Alerting gab trotzdem ausschließlich den
Header-Handlungsweg aus.

### Reproduzierbarer Repo-Fehler in der Worker-Wache

`bewerte()` verlangte `Environments` in `cloudflare/edge-schutz.md`. Die echte
Datei enthielt aber keinen A4-Abschnitt dazu. Schon ein gesunder Worker-Stand
gegen den unveränderten Repo-Stand erzeugte deshalb einen Fehler; die
Offline-Prüfung derselben Vorlage blieb grün. Der Selbsttest verwendete eine
künstlich vollständige Vorlage und übersah den Widerspruch.

Die fehlende Vorlage ist nun ergänzt. Ihre Vollständigkeitsprüfung ist als
`vorlagen_fehler()` zwischen Offline- und Betriebsbewertung geteilt. Ein
Regressionstest verwendet ausdrücklich das **echte Repository** und sabotiert
anschließend jede verlangte Vorlagenkomponente. Die Regel wurde nicht entfernt.

### Ungeprüfte Health-Antwort konnte als sicherer Stand erscheinen

Der Worker liefert bei falschem/fehlendem Leseschlüssel bewusst eine öffentliche
HTTP-200-Antwort mit nur `ok`/`ts`. Alte Deploys kennen die Schutzfelder ebenfalls
nicht. Bisher ergänzte die Wache fehlende Budget-/Schutzwerte aus Defaults.
Außerdem wurde ein fehlender GitHub-Leseschlüssel im Workflow mit Exit 0
übersprungen. Beides war kein authentifizierter Betriebsnachweis.

## 2. Dauerhafte Korrekturen

- **Abschluss nur mit Live-Beweis:** `sicherheits_nachweis.py` verlangt einen
  erfolgreichen Live-Job und alle fünf ausgeführten Mess-/Auswerte-/Nachweisschritte.
  Push-/Offline-Läufe, übersprungene Schritte, alte grüne Läufe ohne neuen
  Nachweisschritt und eine nicht abrufbare Job-Lage schließen WF-E813 nicht.
  Die übrigen Workflows behalten ihren Schließpfad.
- **Messvertrag statt Shell-Raten:** JSON, Markdown und der echte Prozess-Exit
  müssen zusammenpassen. Fehlende/kaputte oder veraltete Dateien sind
  `WACHE-FEHLER`. Die echten Shellblöcke sind unter Bash `-e -o pipefail` geprüft;
  Mess-Exits werden gespeichert, Schreibfehler nicht verschluckt.
- **Vollständiges Betriebsbild:** Alle geschützten Health-Felder und ihre Typen
  werden geprüft. Fehlender Zugang, öffentliche/alte oder unlesbare Antworten
  sind `STOERUNG` (Exit 2), nicht `BEFUND` und nicht grün.
- **Belegte Fehler bleiben rot:** KV-Ausfall, widersprüchliches Turnstile,
  fehlender/abweichender Tagesdeckel und ein zu großes KV-Schreibbudget bleiben
  Befunde. Ein authentifiziertes 503-JSON mit KV-Ausfall bleibt auswertbar;
  eine 503-Antwort mit `ok:true` wird nicht als gesund akzeptiert.
- **Netzfehler begrenzt wiederholen:** Worker-Netz-/429-/5xx-Störungen werden
  vor einem Alarm erneut gemessen. Header auf HTTP-Fehler-/Challenge-Seiten
  zählen nicht als erfolgreiche Seitenmessung; auch GET-5xx werden wiederholt.
- **Kein falscher Gesamtabschluss:** F-01 `TEILWEISE` behält den bisherigen
  Mess-CLI-Vertrag, reicht aber ausdrücklich nicht zum Live-Abschluss.
- **Beide Fehlerwege sichtbar:** Eigene Klassen für Header, Worker, gleichzeitige
  Fehler und unvollständigen Live-Nachweis; vorhandene Meldungen wechseln ohne
  Duplikat auf den passenden Handlungsweg.
- **Diagnose ohne sensible Rohdaten:** Einzelbefunde als geschützte
  Check-Annotationen, lesbare Zusammenfassungen und sieben Tage bereinigte
  Messartefakte. Keine rohen Export-Einträge, Adressen, Schlüssel oder Cookies.
  Der Leseschlüssel geht nur an die eigene HTTPS-Worker-Domain, nie über Redirects.
- **CI-Vertrag:** Änderungen an Prüfern, Regressionstests und Alerting lösen die
  Sicherheits-Wache aus. Alle neuen Tests laufen auch über `npm run test:sicherheit`;
  die Alert-Verhaltenssimulation benötigt im Offline-Job kein zusätzliches pip-Paket.

## 3. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `npm run test:sicherheit` (mit den gepinnten Python-Paketen) | **113 Unit-Tests grün**, fünf Selbsttests und alle Offline-Wachen grün |
| Playwright, Desktop + Mobile, vollständige Suite | **108/108 grün**, 3,6 Minuten, kein fehlgeschlagener Test |
| Hugo Extended 0.164.0 + Pagefind-Build | grün, 93 indexierbare Seiten im Index |
| Worker-Deploy- und Alert-Regressionen | 33 Tests grün (teilweise Überschneidung mit obiger Suite) |
| Alarm-Identität `--selftest` | 10 Fallgruppen grün, 59 eindeutige Workflow-Codes |
| Wachen-Vertrag | 319 Skripte geprüft, 0 Funde |
| Hugo-Bauvertrag `--selftest` | grün |
| Beide geänderten Workflows | YAML gültig, alle Shellblöcke mit `bash -n` geprüft |
| Manifest-Wache | grün; bestehende Warnung zum fehlenden KI-Assistenten-Lockfile unverändert |
| `git diff --check` | grün |

Die Abschluss-Regression führt den **echten** Workflow-Shellblock mit einer
lokalen `gh`-Attrappe aus: Offline-Grün schließt nicht, API-Ausfall/kaputtes JSON
schließt nicht, vollständiges Live-Grün schließt; andere Workflows bleiben
unverändert. Kein Test schreibt in GitHub oder produktives KV.

## 4. Was für die produktive Erledigung noch erforderlich ist

1. **Änderungen übernehmen.** Sie liegen im Arbeitsbranch; die grüne lokale
   Prüfung ist noch kein Deploy auf `main`.
2. **Cloudflare A1 einrichten/verifizieren:** beide DNS-Hosts `Proxied`,
   bevorzugt `Full (strict)` (mindestens `Full`, nie `Flexible`), Regel
   `FF Sicherheits-Header` mit acht Kopfzeilen. Datenschutzfolge B7 berücksichtigen.
   GitHub Pages ignoriert `static/_headers`; eine Änderung nur dort löst F-01 nicht.
3. **Worker-Betriebsbild verifizieren:** Falls der Deploy fehlt/veraltet ist,
   Einrichtung nach Runbook D2 erledigen. Der letzte geprüfte Deploy-Plan
   [38657279461](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/38657279461)
   war grün, der Deploy aber **skipped**. Seine Check-Annotation belegt am
   14.10.2026 die fehlende Variable `KV_NAMESPACE_ID_ABO`; das ist ausdrücklich
   keine Aussage über ihren heutigen, hier nicht einsehbaren Wert.
4. **Nach der Übernahme einmal live messen:**

   ```bash
   gh workflow run sicherheits-wache.yml --ref main
   ```

   Erst wenn beide Auswertungen und **„Live-Nachweis abschließen“** erfolgreich
   sind, ist der gemessene Zustand als behoben belegt. Die Automatik darf dann
   WF-E813 schließen — nicht schon beim ersten grünen Offline-Push.

**Konkretes Betriebs-Runbook:** `docs/SICHERHEIT-BETRIEB-RUNBOOK.md`, A1/A3/A4
und D1/D2. Ohne den produktiven Live-Nachweis wird hier keine vollständige
Behebung behauptet.
