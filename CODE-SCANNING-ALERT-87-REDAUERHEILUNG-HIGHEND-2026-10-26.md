# Code-Scanning-Alert Nr. 87 – „Inefficient regular expression“ · Dauerheilung auf Highend-Niveau, 26.10.2026

**Ausgangslage:** CodeQL meldete `py/redos` in `scripts/gsc_abdeckung.py:566`. Die Annotation des Check-Runs `121522888461` (Lauf `40308321174`) nennt die Pumpe wörtlich: *„This part of the regular expression may cause exponential backtracking on strings starting with `sitemap:\n` and containing many repetitions of `\t\n`.“* Die Query [`python/ql/src/Security/CWE-730/ReDoS.ql`](https://github.com/github/codeql/blob/main/python/ql/src/Security/CWE-730/ReDoS.ql) trägt `security-severity 7.5` – der Fund ist ein Sicherheitsfund, kein Kosmetikhinweis. · **Ergebnis:** Der mehrzeilige Ausdruck ist vollständig entfernt. Ein zeilenweiser, bereichsscharfer Parser liest `sitemap.disable` in linearer Zeit. Eine eigene, upload-unabhängige Wache, 98 Unit-Tests in den beiden betroffenen Vertragsmodulen, 109 Selbsttestfälle, ein harter CI-Vertrag und eine Betriebsdokumentation verhindern die Rückkehr derselben Fehlerklasse.

> Dieser Bericht ist der Wahrheitsort für Alert Nr. 87. Er ergänzt `CODE-SCANNING-ALERT-83-DAUERHEILUNG-PREMIUM-2026-10-10.md` (URL-Host-Wahrheit), `CODE-SCANNING-ALERT-80-PREMIUM-2026-10-05.md` (Klartext-Wache) und `GSC-ABDECKUNG-HIGHEND-2026-10-26.md` (Fachmodul der Search Console). Was hier steht, gilt bis ein neuer datierter Abschnitt es ablöst.

---

## 1 · Der Befund war echt – und die Workflow-Beschreibung war falsch

Der betroffene Code gehörte zur Gegenrechnung der Search-Console-Abdeckung. Für jedes `index.md`/`_index.md` sollte er aus dem Hugo-Frontmatter nur eine Frage beantworten:

> Hat diese Seite `sitemap.disable: true` und gehört deshalb nicht zur erwarteten Menge der indexierbaren Seiten?

Dafür stand ein einziger Ausdruck über mehrere Zeilen:

```python
# vorher – scripts/gsc_abdeckung.py:566
re.search(r"^sitemap:\s*\n(?:\s+.*\n)*?\s+disable:\s*true", fm, re.M)
```

Drei Eigenschaften erzeugen zusammen die exponentielle Zerlegung:

| Teil | Bedeutung im Muster | Warum er kippt |
|---|---|---|
| `^sitemap:\s*\n` | Der Schlüssel `sitemap:` und ein Zeilenende. | `\s*` darf selbst Zeilenumbrüche fressen; das folgende `\n` ist dadurch nicht eindeutig. |
| `(?:\s+.*\n)*?` | „Beliebig viele eingerückte Zeilen“. | In der Gruppe treffen `\s+` und `.*` auf dieselben Leerzeichen und Tabulatoren. Beide sind unbegrenzt. |
| `\s+disable:\s*true` | Der gesuchte Wert. | Der schließende `\s+` überlappt erneut mit der Gruppe. Für `\t\n\t\n…` gibt es viele Zerlegungen, aber kein `disable: true`. |

Python muss all diese Zerlegungen ausprobieren, bevor es „kein Treffer“ sagen darf. Genau das ist ein Denial-of-Service-Muster: Die Eingabe ist klein, die Laufzeit wächst exponentiell. Dazu kam ein **Prozessfehler**: Der Kopf von `.github/workflows/codeql.yml` beschrieb `py/redos` noch als reinen Qualitätsfund, der „berichtet, aber nicht blockiert“. Tatsächlich lieferte die `security-extended`-Suite die Regel mit `security-severity 7.5`; das Gate lief rot. Eine Wache, deren Kommentar das Gegenteil ihrer eigenen Regel behauptet, ist auf Dauer keine verlässliche Wache.

---

## 2 · Heilung statt Dosisanpassung am Regex

Ein Possessiv-Quantor, ein `.*?` mehr oder ein `re.DOTALL`-Flag wären Scheinreparaturen: Sie ändern die Zerlegungsreihenfolge, aber nicht die Struktur. Die Agentur-Lösung trennt **Syntax** von **Bedeutung**: Frontmatter ist ein zeilenbasiertes Format; ein zeilenbasierter Parser ist die passende Maschine.

### `sitemap_deaktiviert(fm)` – die eine Wahrheit

`scripts/gsc_abdeckung.py` besitzt jetzt eine eigene Funktion mit klarer Zusage:

1. **Nur oberste Ebene.** Ein `sitemap:` am Zeilenanfang öffnet den Block; eingerückte oder fremde Schlüssel werden ignoriert.
2. **Nur direkte Kinder.** Die erste eingerückte Zeile definiert die Kind-Ebene. `disable: true` zählt nur auf genau dieser Ebene; ein verschachteltes `disable` in `meta:` zählt nicht.
3. **Nur ein echter Bool.** `true` (auch `TRUE`) zählt. `"true"`, `false`, `trueish`, `yes` und `sitemap: false` zählen nicht.
4. **Kommentare sind Kommentare.** `# …` wird außerhalb von Anführungszeichen entfernt; CRLF wird korrekt gelesen. Inline-Abbildungen wie `sitemap: {disable: true, priority: 0.5}` werden unterstützt.
5. **Der Block endet an der nächsten obersten Ebene.** Ein `disable: true` in einem späteren, fremden Block kann nicht mehr in `sitemap` hineinwirken – eine Falschpositiv-Klasse des alten Ausdrucks.
6. **Linear.** `splitlines()` und eine Schleife über die Zeilen sind O(n). Es gibt keinen Backtracking-Zustand.

`inhalts_seiten()` ruft jetzt `sitemap_deaktiviert(fm)` auf. Damit ist die Fachbedeutung unverändert – fünf dokumentierte noindex-Seiten, 99 indexierbare Seiten im echten Bestand –, aber die Implementierung besitzt keine Angriffsfläche mehr. Der Selbsttest des Moduls hält 30.000 `\t\n`-Wiederholungen unter zwei Sekunden bei gleichzeitig korrektem `False` fest.

---

## 3 · Die Wache: `scripts/redos_guard.py`

Die lokale Wache ist bewusst **kein** zweiter CodeQL. Sie hat eine engere, dafür beweisbare Aufgabe: Die Struktur aus Alert Nr. 87 darf nie wieder in einem `re.*`-Aufruf auftauchen – unabhängig davon, ob GitHub gerade SARIF hochlädt oder die Alert-API erreichbar ist.

| Regel | Prüfung |
|---|---|
| **R0-SYNTAX** | Eine Python-Datei ist nicht parsebar. Unlesbar ist fail-closed ein Fund, niemals „sauber“. |
| **R1-NEWLINE-PUMP** | Eine unbegrenzte Gruppe enthält einen Whitespace-Quantor und einen breiten Zeilen-Quantor ohne eindeutiges Pflichttrennzeichen, dazu ein Zeilenumbruch-Literal; hinter der Gruppe folgt ein weiterer unbegrenzter Whitespace-Quantor. |

Die Analyse läuft über den **Python-AST** und den Parser `re._parser` – nicht über Textsuche. Sie erkennt Muster in `re.search`, `re.compile`, `re.sub` usw., in Modul- und Funktionsaliasen, in Musterkonstanten, in verketteten Literalen und in f-Strings mit statischem Gerüst. Kommentare, unbekannte Laufzeitmuster und possessive Quantoren erzeugen keine Fehlalarme. Es gibt **keine Whitelist und keine Inline-Unterdrückung**.

`--selftest` beweist 12 Fälle: fünf Positive (direkter Aufruf, Konstante, Modulalias, Funktionsalias, f-String) und sieben Gegen- bzw. Fail-closed-Proben. Der Bestandslauf prüft **539 Python-Dateien** und meldet **0 Funde**. Die bewusste Grenze steht im Modulkopf: Vollständig zur Laufzeit gebaute Muster bleiben CodeQLs Datenflussanalyse überlassen; diese Wache ersetzt den Generalisten nicht, sie ergänzt ihn um eine lokale Rückfallsperre.

---

## 4 · Der Dauerschutz: fünf unabhängige Ebenen

| Ebene | Was eingefroren ist |
|---|---|
| **Produktcode** | `sitemap_deaktiviert()` ist regexfrei, linear und bereichsscharf; `inhalts_seiten()` benutzt sie nachweislich per AST-Vertrag. |
| **Wache** | `redos_guard.py` erkennt R0/R1, läuft ohne Netz und ohne SARIF, ist fail-closed und besitzt Positiv-/Gegenproben. |
| **Regressionstests** | `scripts/tests/test_redos_security.py` (14 Tests) prüft Schärfe, Rückfall im Wegwerf-Repo, Bestand, Unterdrückungsverbot, Heilung, CI-Verdrahtung, npm-Skripte, `GUARDS` und Dokumentation. `scripts/tests/test_gsc_abdeckung.py` ist auf **84 Tests** gewachsen; der Modul-Selbsttest auf **97 Fälle**. |
| **CI** | `.github/workflows/codeql.yml`: `py/redos`, `py/polynomial-redos`, `js/redos` und `js/polynomial-redos` stehen namentlich in `DOKU_SEC` und sind damit auch ohne SARIF-Metadaten hart. Der neue Job `redos-wache` ruft Wache, Verträge und GSC-Selbsttest auf. `redos_guard.py` steht zusätzlich im vertraglichen Minimum `GUARDS` (C6) und wird vom `selftest_runner` automatisch entdeckt. |
| **Dokumentation** | `SECURITY.md`, `docs/ENTWICKLER-WERKZEUGE.md`, `CLAUDE.md` und dieser Bericht tragen die Hausregel; `package.json` bietet `npm run redos:wache` und `npm run test:redos`. |

Die Fehlbeschreibung „ReDoS ist Quality“ ist aus dem Workflow-Kopf entfernt. Damit widerspricht die Betriebsanleitung nicht mehr dem eigenen Gate.

---

## 5 · Verifikationsmatrix

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/gsc_abdeckung.py --selftest` | ✅ **97 Fälle grün** (inkl. 30.000-facher Angriffseingabe) |
| `python3 -m unittest scripts.tests.test_gsc_abdeckung` | ✅ **84 Tests** |
| `python3 scripts/redos_guard.py --selftest` | ✅ **12 Fälle grün** |
| `python3 scripts/redos_guard.py` | ✅ **539 Python-Dateien, 0 Funde** |
| `python3 -m unittest scripts.tests.test_redos_security` | ✅ **14 Tests** |
| `python3 scripts/governance_contract.py --selftest` | ✅ C1–C44, Positiv- und Gegenproben |
| `python3 -m py_compile scripts/*.py scripts/tests/*.py` | ✅ keine Syntaxfehler |
| `python3 scripts/url_substring_guard.py --selftest` | ✅ 20/16/23/2/2 Proben, Bestand 926 Dateien grün |
| `python3 scripts/clear_text_logging_guard.py --selftest` | ✅ 10/6/19 Proben, Bestand 539 Dateien grün |
| `python3 scripts/wachen_vertrag.py --selftest` | ✅ 16 eingefrorene Fälle, Bestand 335 Skripte grün |
| `python3 -m unittest scripts.tests.test_wachen_vertrag scripts.tests.test_url_substring_security scripts.tests.test_clear_text_logging_security scripts.tests.test_zugangs_namensvertrag scripts.tests.test_konsolidierung` | ✅ 106 Tests |
| `python3 scripts/actions_version_guard.py --gate` | ✅ keine Action-Versionsdrift |
| `python3 scripts/selftest_runner.py` | ✅ **232 Wachen, 464 Uhr-Proben**, 0 Fehler |
| `npm run test:redos` | ✅ Wache + Bestand + **98 Tests** |
| `python3 -m unittest discover -s scripts/tests -p 'test_*.py'` | **3.912 Tests, 14 übersprungen**; 12 Altbefunde aus `main` (siehe unten) |
| **CodeQL auf dem Pull Request** | nach dem Merge/Lauf auf `main` maßgeblich; lokale Vorprüfung oben ersetzt nicht den Scanner |

### Rebase auf `main` `60d38ea` und die Altbefunde des Basisstands

Während der Arbeit lief auf `main` eine parallele SEO-/Analytics-Runde. Der Branch wurde deshalb auf den aktuellen Stand `60d38ea` rebase’d; beide Heilungen bleiben erhalten. Beim Rebase fiel eine zusätzliche Zeitbombe auf: Der GSC-Selbsttest K66–K68 las den echten Verlauf und die Wanduhr und kippte unter der Uhr-Probe. Er ist jetzt mit festem Probetag, leerem Verlauf und leerem Register hermetisch – **232 Wachen inklusive beider Uhr-Proben sind wieder grün**.

Andere Befunde gehören nachweislich **nicht** zu dieser Lieferung. Sie wurden in einem isolierten Worktree auf dem unveränderten `origin/main` (`60d38ea`) mit denselben Kommandos reproduziert:

* `governance_contract.py --quick` meldet C40-Funde aus der neu eingeführten Analytics-Dokumentation und `hugo.toml`.
* `integrity_guard.py --gate` meldet `hugo.toml` und `layouts/_partials/head.html` als geändert, aber nicht neu signiert.
* `artefakt_waechter.py` meldet fünf Frontmatter-Dateien mit `mapping values are not allowed here`.
* Die Vollsuite trägt daraus 11 Failures und 1 Error weiter, u. a. `test_fremdmessung_sperre`, `test_datenschutz_freigabe`, `test_integrity_guard` und den Reserve-Snapshot-SHA-Drift. Alle zwölf wurden einzeln auf dem sauberen `main`-Stand wiederholt und scheitern dort identisch.

Diese Altbefunde betreffen Analytics-/Content-Dateien, die dieser PR nicht anfasst. Eine Heilung gehört in deren eigenen Vorgang; hier wurden sie bewusst **nicht** durch Ausnahmen, Unterschriften oder ein `|| true` maskiert. Alle **98 direkt betroffenen Tests** dieser Lieferung sind grün.

*Hinweis zur Alert-Schließung:* GitHub aktualisiert die Security-Tab erst mit einer Analyse des gemergten Stands auf `main`. Der Branch liefert die Code- und Vertragsheilung; der anschließende `CodeQL-Sicherheitswache`-Lauf auf `main` ist der öffentliche Nachweis, dass `py/redos` dort 0 Funde hat. Kein Dismiss, keine Unterdrückung.

---

## 6 · Bedienung im Betrieb

```bash
# lokaler Schnellcheck vor jedem Commit an Frontmatter-Parsern
npm run redos:wache

# vollständiger Vertrag (Wache + Bestand + beide Testmodule)
npm run test:redos

# maschinenlesbarer Bericht für CI oder ein Ticket
npm run redos:wache:json

# nur die GSC-Fachprüfung
python3 scripts/gsc_abdeckung.py --selftest
python3 -m unittest scripts.tests.test_gsc_abdeckung
```

**Wenn R1 anschlägt:** Nicht freisprechen, nicht unterdrücken, nicht `# noqa` setzen. Die betroffene Stelle zeilenweise parsen oder das Muster so umschreiben, dass zwischen zwei unbegrenzten Quantoren ein eindeutiges Pflichtzeichen steht. Danach `npm run test:redos` erneut laufen lassen. **Wenn R0 anschlägt:** Die Datei ist kaputt; erst Syntax heilen, dann weiter – ein unlesbarer Baum ist kein grüner Baum.

---

## 7 · Geänderte und neue Dateien

| Datei | Art | Inhalt |
|---|---|---|
| `scripts/gsc_abdeckung.py` | geheilt | `sitemap_deaktiviert()` als linearer YAML-Zeilenparser; K66–K68 hermetisch gegen die Uhr-Probe; 97 Selbsttestfälle |
| `scripts/redos_guard.py` | neu | AST-basierte R0/R1-Wache mit 12 Eigenproben |
| `scripts/tests/test_redos_security.py` | neu | 14 Vertragstests über Schärfe, Bestand, Heilung, CI und Doku |
| `scripts/tests/test_gsc_abdeckung.py` | erweitert | 8 neue Parser- und Linearitätsproben (84 Tests gesamt) |
| `.github/workflows/codeql.yml` | gehärtet | vier ReDoS-Regeln in `DOKU_SEC`, korrekte Security-Einstufung, Job `redos-wache` |
| `scripts/governance_contract.py` | erweitert | `redos_guard.py` im vertraglichen Minimum `GUARDS` |
| `package.json` | erweitert | `redos:wache`, `redos:wache:json`, `test:redos` |
| `SECURITY.md`, `docs/ENTWICKLER-WERKZEUGE.md`, `CLAUDE.md` | erweitert | Hausregel, Befehle, Agenten-Leitplanke |
| `GSC-ABDECKUNG-HIGHEND-2026-10-26.md` | nachgezogen | aktuelle Test- und Selbsttestzahlen |

---

## 8 · Restisiko, bewusst benannt

Die lokale Wache deckt die **Strukturklasse von Alert Nr. 87** ab. Neue, anders geformte ReDoS-Muster bleiben Aufgabe von CodeQL `security-extended`; deshalb sind alle vier ReDoS-Regeln zusätzlich hart im SARIF-Gate verdrahtet. F-Strings, deren gesamtes Muster erst zur Laufzeit entsteht, können von einer statischen Wache nicht vollständig beurteilt werden – CodeQLs Datenflussanalyse bleibt hier der Generalist. Für den konkreten Fall ist das Risiko jedoch beseitigt: Der Produktivpfad enthält gar keinen regulären Ausdruck mehr.
