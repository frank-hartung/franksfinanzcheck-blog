# Code-Scanning · Suchradar (PR #709) – sechs URL-Substring-Fundstellen · Dauerheilung auf Agentur-Niveau, 12.10.2026

**Ausgangslage:** Am 12.10.2026 um 13:05 MESZ kam PR #709 („Suchradar: Google-Suchergebnis-Erfassung ohne API") auf `main`. Seitdem ist die Security-Wache des Repositories **rot** – und zwar auf `main` selbst, nicht nur auf nachfolgenden Pull Requests:

| Lauf | Ereignis | Commit | Ergebnis |
|---|---|---|---|
| CodeQL-Sicherheitswache | `push` auf main | `0d58ec0` | ❌ failure |
| CodeQL-Sicherheitswache | `schedule` (Montag 03:30 UTC) | `9c31b93` | ❌ failure |
| CodeQL-Sicherheitswache | `pull_request` (#711) | Merge-Zustand | ❌ failure |

Zwei Jobs scheiterten, beide an derselben Wurzel: **`CodeQL (python)`** im Schritt „Sicherheits-Gate (null Security-Fundstellen)" und **`URL-Wache (unabhängig vom SARIF-Upload)`** im Schritt „Python, JavaScript und HTML auf URL-Substring-Prüfungen abklopfen". Regelklasse: `py/incomplete-url-substring-sanitization` (Security-Severity 7.8) – genau die Klasse aus Alert #83.

**Ergebnis:** Alle sechs Fundstellen **konstruktiv im Code geheilt** – kein Dismiss, keine Inline-Unterdrückung, keine Ausnahme-Whitelist (das verbietet Alert #83 ausdrücklich: *„Unterdrücken gilt nicht"*). Dazu **zwei neue Regressionstests mit Feindproben**, die am alten Code nachweislich scheitern. URL-Wache: **718 Dateien, 0 Befunde**. Suchradar-Tests: **80 statt 78, alle grün**. Gesamtsuite: **2813 Tests, 0 Fehler**.

> Dieser Bericht ist der Wahrheitsort für diese Heilung. Vorgeschichte und Regelwerk: `CODE-SCANNING-ALERT-83-DAUERHEILUNG-PREMIUM-2026-10-10.md` (Warum Unterdrückung keine Heilung ist), `CODE-SCANNING-HEILUNG-PREMIUM-2026-10-04.md` (Gesamtstrategie), `CODE-SCANNING-ALERT-78-DAUERHEILUNG-PREMIUM-2026-10-05.md` (Diff-Blindheit).

---

## 1 · Die sechs Fundstellen

Gemessen mit `python3 scripts/url_substring_guard.py` am Stand `2cf8b93` (main):

```
❌ URL-WACHE: 6 Befund(e) in 714 Dateien
   scripts/serp_anbieter.py:682        in     „duckduckgo.com“
   scripts/serp_anbieter.py:770        not in „duckduckgo.com“
   scripts/serp_anbieter.py:829        in     „mojeek.com“
   scripts/serp_html.py:340            not in „duckduckgo.com“
   scripts/suchradar.py:1001           not in „duckduckgo.com“
   scripts/tests/test_suchradar.py:583 not in „mojeek.com“
```

Alle sechs gehören zu **einer** Entscheidung: *„Ist dieser Treffer ein Link der Suchmaschine selbst (dann gehört er nicht ins Ranking) – oder ein echtes organisches Ziel?"* Das Suchradar filtert damit Eigenlinks (`mojeek.com/about`) und Anzeigen-Umleitungen (`duckduckgo.com/y.js`) aus und packt DuckDuckGo-Umleitungen (`/l/?uddg=…`) auf ihr Ziel aus.

Die Absicht war richtig. Die **Prüfung** war es nicht: Sie entschied über eine Teilzeichenkette statt über den Host.

---

## 2 · Warum das keine Formalie ist – der Beweis an der Fundstelle

Die schärfste der sechs Stellen war `serp_html.py:340` (`uddg_entpacken`). Dort stand:

```python
parsed = urlparse(url)
if "duckduckgo.com" not in parsed.netloc or not parsed.path.startswith("/l/"):
    return url
```

`parsed.netloc` ist schon ein Fortschritt gegenüber der rohen URL – aber es bleibt eine **Teilzeichenketten-Suche im Hostnamen**. Gemessen, alter gegen neuen Code, dieselben fünf Eingaben:

| Eingabe | ALT (Substring) | NEU (host-exakt) | |
|---|---|---|---|
| `https://duckduckgo.com/l/?uddg=…example.com%2Fa` | `https://example.com/a` | `https://example.com/a` | gleich |
| `//duckduckgo.com/l/?uddg=…example.com%2Fa` | `https://example.com/a` | `https://example.com/a` | gleich |
| `https://duckduckgo.com.angreifer.example/l/?uddg=…evil.example` | **`https://evil.example`** | URL bleibt unverändert | **geheilt** |
| `https://angreifer.example/l/?x=duckduckgo.com&uddg=…` | unverändert | unverändert | gleich |
| `https://example.com/b` | unverändert | unverändert | gleich |

Zeile 3 ist der Fund: Eine Domain, die ein Angreifer registrieren kann (`duckduckgo.com.angreifer.example`), wurde für eine DuckDuckGo-Umleitung gehalten. Die Funktion lieferte `https://evil.example` als **Ziel-URL des Treffers** zurück. Damit wäre eine fremde, konstruierte Adresse als organisches Suchergebnis in den Suchradar-Bericht, in die Rang-Verfolgung und in den Wettbewerbs-Radar gewandert – also genau in die Artefakte, die im Suchradar redaktionelle Entscheidungen begründen.

Die Gegenrichtung ist derselbe Fehler mit umgekehrtem Vorzeichen, bei den drei Filtern in `serp_anbieter.py`:

* `https://beispiel.example/?quelle=mojeek.com` – ein **echter fremder Treffer**, der den Hostnamen nur als Query-Parameter trägt – wurde von `"mojeek.com" in ziel` als Eigenlink **weggeworfen**. Stiller Trefferverlust, im Bericht nicht sichtbar.
* `https://mojeek.com.einbrecher.example/x` – wurde umgekehrt **nicht** gefiltert, obwohl der Host nichts mit Mojeek zu tun hat.

Beide Richtungen sind mit denselben zwei Tests festgenagelt (Abschnitt 4).

---

## 3 · Die Heilung

Der Weg ist derselbe wie bei Alert #83 und steht im Repository bereit: **URL parsen, Host vergleichen** – über `scripts/url_host.py`, nicht neu erfunden.

```python
from url_host import ist_host_oder_subdomain   # noqa: E402  (Host-exakte URL-Wahrheit)
```

| Datei | Vorher | Nachher |
|---|---|---|
| `serp_anbieter.py` (DuckDuckGo-Vollversion) | `"duckduckgo.com" in url` | `ist_host_oder_subdomain(url, "duckduckgo.com")` |
| `serp_anbieter.py` (DuckDuckGo Lite) | `"duckduckgo.com" not in url` | `not ist_host_oder_subdomain(url, "duckduckgo.com")` |
| `serp_anbieter.py` (Mojeek) | `"mojeek.com" in ziel` | `ist_host_oder_subdomain(ziel, "mojeek.com")` |
| `serp_html.py` (`uddg_entpacken`) | `"duckduckgo.com" not in parsed.netloc` | `not ist_host_oder_subdomain(url, "duckduckgo.com", schemata=("https", "http", ""))` |
| `suchradar.py` (Selbsttest-Prüfblock 11) | `all("duckduckgo.com" not in t["url"] …)` | `all(not ist_host_oder_subdomain(t["url"], "duckduckgo.com") …)` |
| `tests/test_suchradar.py` | `all("mojeek.com" not in t["url"] …)` | `all(not ist_host_oder_subdomain(t["url"], "mojeek.com") …)` |

**Subdomain, nicht Host-Exaktheit.** Gewählt ist `ist_host_oder_subdomain`, nicht `ist_host`: DuckDuckGo liefert die Lite-Variante unter `html.duckduckgo.com`, Mojeek unter `www.mojeek.com`. Eine exakte Prüfung hätte die echten Eigenlinks durchgelassen – der Filter wäre still ausgefallen. Die Punkt-Grenze des Helfers (`name == basis or name.endswith("." + basis)`) ist der Teil, der `mojeek.com.einbrecher.example` abweist und `www.mojeek.com` behält.

**Eine bewusste Abweichung, begründet.** `uddg_entpacken` ist die einzige Stelle, die `schemata` um das **leere Schema** erweitert. Der Grund steht als Kommentar im Code: DuckDuckGo liefert Treffer schema-relativ als `//duckduckgo.com/l/?uddg=…` (so beschreibt es der Docstring der Funktion, so steht es in der HTML-Probe). `url_saeubern` setzt zwar `https:` davor, `uddg_entpacken` ist aber über `__all__` **öffentlich exportiert** und darf am rohen Attribut nicht anders entscheiden als am gesäuberten. Ohne das leere Schema wäre die schema-relative Form still nicht mehr ausgepackt worden – ein Funktionsverlust, den kein Test bemerkt hätte, weil alle Tests über `url_saeubern` gehen.

---

## 4 · Der Beweis, dass die Tests scharf sind

Ein Test, der am fehlerhaften Code besteht, ist Dekoration. Deshalb wurden die beiden neuen Tests **gegen den alten Stand zurückgeprüft**: `scripts/serp_html.py` und `scripts/serp_anbieter.py` per `git checkout origin/main --` auf die verwundbare Fassung gesetzt, Tests laufen lassen, geheilte Fassung zurückgespielt.

```
AssertionError: 'https://evil.example' != 'https://duckduckgo.com.angreifer.example/l/?uddg=…'
 : Suffix-Domain wurde als DuckDuckGo-Umleitung entpackt
AssertionError: 'https://beispiel.example/?quelle=mojeek.com' not found in ['https://franksfinanzcheck.de/strom-sparen/']
 : Query-Parameter wurde als Mojeek-Host fehlgedeutet
Ran 2 tests in 0.002s
FAILED (failures=2)
```

Beide Tests scheitern am alten Code – jeder an genau der Flanke, die er bewachen soll. Am geheilten Code: `Ran 80 tests … OK`.

Neu in `scripts/tests/test_suchradar.py`, Klasse `TestParser`:

* **`test_umleitung_auspacken_ist_host_exakt`** – 2 legitime Formen (absolut, schema-relativ), 1 echte Subdomain, **2 Feindproben** (Suffix-Domain, Hostname als Query-Parameter), 1 Gegenprobe (fremde URL bleibt unangetastet).
* **`test_eigenlink_filter_ist_host_exakt`** – Mojeek-Filter in **beide** Richtungen: fremder Treffer mit Hostname im Query muss **bleiben**, Suffix-Domain muss **bleiben**, echter Eigenlink muss **fallen**.

---

## 5 · Messung nach der Heilung

Alle Zahlen am Arbeitsbaum vom 12.10.2026, main-Stand `2cf8b93` plus diese Heilung.

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| URL-Wache, ganzer Bestand | `python3 scripts/url_substring_guard.py` | ✅ **718 Dateien, 0 Befunde** |
| URL-Wache, Eigenprüfung | `… url_substring_guard.py --selftest` | ✅ 20 Positiv-, 16 Gegen-, 23 Muster-, 2 Fail-closed-, 2 Scope-Proben |
| Host-Wahrheit, Eigenprüfung | `python3 scripts/url_host.py --selftest` | ✅ 42 Proben |
| Sicherheitsvertrag Alert 83 | `python3 -m unittest scripts.tests.test_url_substring_security` | ✅ 17 Tests |
| Suchradar | `python3 -m unittest scripts.tests.test_suchradar` | ✅ **80 Tests** (vorher 78) |
| Suchradar-Selbsttest | (läuft in der Suite mit) | ✅ 13 Prüfblöcke, offline |
| Anbieter-Selbsttest | (läuft in der Suite mit) | ✅ 10 Anbieter, 11 Prüfblöcke, 10 Ausführer |
| KI-Assistent-Gate | `python3 scripts/ki_assistent_gate.py --selftest` | ✅ alle Sabotage-Proben erkannt |
| CORS-Vertrag des Workers | `node --test cloudflare/ki-assistent/test/worker.test.mjs` | ✅ 7 von 7 |
| Gesamtsuite | `python3 -m unittest discover -s scripts/tests` | ✅ **2813 Tests, 0 Fehler** (22 übersprungen) |
| Alle Selbsttests, uhrfest | `python3 scripts/selftest_runner.py` | ✅ **190 Wachen**, 380 Uhr-Proben (+97/+1461 Tage) |
| Governance-Vertrag | `python3 scripts/governance_contract.py --quick` | ✅ 33 Regeln, beide Richtungen |
| Actions-Versionskanon | `python3 scripts/actions_version_guard.py --gate` | ✅ keine Drift |
| Hugo-Bauvertrag | `python3 scripts/hugo_build_vertrag.py` | ✅ H1–H8 |
| Root-Hygiene | `python3 scripts/report_hygiene.py --check` | ✅ sortenrein |

Zusatzbefund: Der vorher bekannte, **vorbestehende** Fehler in `test_reserve_artifacts` (zwei Artikel mit SHA-256 außerhalb des Reserve-Entwurfs) ist durch einen main-Commit zwischenzeitlich selbst geheilt – die Gesamtsuite ist damit erstmals seit dem 12.10. wieder fehlerfrei.

---

## 6 · Was dieser Fall lehrt

**Eine neue Kette erbt die Regeln nicht automatisch.** PR #709 brachte 4.850 neue Zeilen, davon 3.611 Zeilen Python, mit eigenem Selbsttest, Unit-Tests, SSRF-Schutz, robots.txt-Auswertung und Kostensperre – handwerklich stark. Die sechs Fundstellen sind keine Nachlässigkeit, sondern ein **Übersehen der Hausregel**: Dieses Repository hat seit Alert #83 eine fertige Host-Wahrheit, und jede URL-Entscheidung muss durch sie hindurch. Wer `"host" in url` schreibt, baut dieselbe Lücke zum fünften Mal.

**Die Wache hat funktioniert – das ist die gute Nachricht.** Nicht CodeQL allein, sondern die zweite, upload-unabhängige Wache hat den Fund in 5 Sekunden gemeldet, offline und reproduzierbar, mit dem Heilungshinweis direkt in der Ausgabe. Genau dafür existiert sie seit Alert #83.

**Ein rotes `main` blockiert jeden unbeteiligten Pull Request.** Weil das Gate den gesamten Bestand prüft (`CODEQL_ACTION_DIFF_INFORMED_QUERIES: false` – Lehre aus Alert #78), war PR #711 (Google Search Console) rot, ohne eine einzige Zeile beizutragen. Das ist die gewollte Zusage des Gates („ein PR ist nur grün, wenn das Repository als Ganzes sauber ist"), aber es heißt auch: **Eine Security-Fundstelle auf `main` ist ein Sofort-Fall**, kein „machen wir nächste Woche". Sie wurde hier deshalb im Zuge von PR #711 mitgeheilt.

**Offen, und nicht per Code lösbar:** Solange das GitHub-Default-Setup parallel aktiv ist, stammen die Alert-Nummern in der Security-Tab von einer zweiten Engine. Der Klick-Weg zum Deaktivieren steht am Kopf von `.github/workflows/codeql.yml` und im Workflow-Schritt „Upload-Ergebnis sichtbar machen". Diese Heilung macht die Fundstellen in **beiden** Sichten verschwinden – der Betreiber-Handgriff bleibt trotzdem ausstehend.
