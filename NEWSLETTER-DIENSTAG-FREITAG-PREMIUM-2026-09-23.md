# Newsletter: Versandmodus Dienstag/Freitag vollständig eingerichtet, Texte auf Premium-Stand

Stand: 23.09.2026. Arbeitszweig `arena/01a0cef4-franksfinanzcheck-blog`. Es wurde
**kein** Newsletter versendet, kein Brevo-Konto angefasst und keine versiegelte
Kerndatei geändert (`python3 scripts/integrity_guard.py --drift-audit`:
„Kein Drift – 43 Kerndateien entsprechen dem signierten Stand“).

## 1. Ausgangslage: was schon stand und was fehlte

Der Kalendervertrag (Dienstag/Freitag, Cron `5 5 * * 2,5`, Nachhol-Wache
`11 8 * * 2,5`, Wochenjournal, Kadenz-Wache im Fehler-Alerting) war am
23.09.2026 bereits eingerichtet. **Eingerichtet war damit der Termin – nicht der
Versandmodus.** Vier gemessene Lücken:

| # | Befund | Beleg |
|---|---|---|
| 1 | **Locale-Falle.** `betreff_varianten()` unterschied die Tage mit `datum.strftime("%A")` und verglich gegen `"Montag"/"Dienstag"/"Mittwoch"/"Freitag"`. `strftime("%A")` liefert den Namen der **Prozess-Locale**; auf dem Runner und in dieser Umgebung ist das `Tuesday`. | `python3 -c "import datetime;print(datetime.date(2026,9,22).strftime('%A'))"` → `Tuesday`. Die Kadenz-Betreffvariante hat in CI also **nie** ausgelöst. |
| 2 | **Die Rotation rotierte nicht.** Die Variantenwahl war `datum.weekday() % len(varianten)`; bei drei Varianten ist `1 % 3 == 4 % 3 == 1` – Dienstag und Freitag bekamen **dieselbe** Variante. | Rechenweg im Code, nachgestellt im Test `test_beide_versandtage_bauen_eine_mail_mit_identitaet`. |
| 3 | **Die Mail trug die Kadenz nicht.** Kein Wochentag im Kopf, kein Ausgabenname, keine Zeile „nächste Ausgabe“ – der Leser sah nicht, warum diese Mail heute kommt und wann die nächste folgt. | `blocks_bauen()` vor der Änderung: Kopf = `22.09.2026 · Ausgabe 39/2026`. |
| 4 | **Textreste des alten Modus.** `docs/ANLEITUNG-NEWSLETTER-STUDIO.md` („Cron Mo–Fr 05:05 UTC“), `docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md` („Nightly-Cron (Mo–Fr)“), Preheader-Füllsatz in Schweizer Schreibweise („ausserdem“), und auf der Abmeldeseite die Zitierangabe **„§ 7 Abs. 1 DSGVO“** – diese Norm gibt es nicht (gemeint ist Art. 7 Abs. 1 DSGVO; die Einwilligungs-Pflicht für Werbe-Mails steht in § 7 UWG). | `grep -rn "Mo–Fr" docs/ANLEITUNG-NEWSLETTER*.md docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md` |

Zusätzlich fielen bei der Verifikation zwei Wachen auf, die unter
`hugo --minify` – dem Produktionsbuild von `deploy.yml` – rot werden, weil sie
`name="email"` bzw. `name="robots"` **mit** Anführungszeichen suchen:
`scripts/tests/test_newsletter_digest.py` und `e2e/newsletter.spec.mjs`. Beide
sind **vorbestehend**: am Basis-Commit `5eeb90a` in einem eigenen Worktree
nachgestellt, gleicher Fehler, gleiche Ursache.

## 2. Was jetzt eingerichtet ist

### 2.1 Ein Vertrag, eine Stelle

`scripts/newsletter_schedule.py` ist jetzt die einzige Quelle für die Fakten der
Kadenz – Website, Mail, Wache und Doku lesen dieselben Werte:

* `VERSANDTAGE`, `MAX_PRO_WOCHE`, `SEND_UHRZEIT` (07:05 Europe/Berlin = 05:05 UTC)
* `wochentag()`, `tag_kurz()`, `datum_lang()`, `datum_kurz()` – **locale-frei** als
  Tabelle, nicht über `strftime`
* `versandtage_text()` → „Dienstag und Freitag“, `versandtage_adverb()` →
  „dienstags und freitags“, `versandfenster_text()` → der ganze Satz
* `naechster_termin()`, `naechste_ausgabe_text()`, `datum_lang_erkennen()` – der
  nächste Termin wird **gerechnet** und eine gedruckte Terminzeile zurückgelesen,
  damit die Wache sie gegen den Vertrag prüfen kann

### 2.2 Redaktionsrahmen: zwei Termine, zwei Aufträge

`data/newsletter_studio.json` → `creative.kadenz`, geschlüsselt mit
`datetime.weekday()` (`"1"`, `"4"`) – keine Wochentagsnamen, genau wegen Befund 1:

| | **Dienstag** | **Freitag** |
|---|---|---|
| Ausgabe (Kicker im Mail-Kopf) | Wochen-Check | Wochen-Abschluss |
| Auftrag (Aufmacher, Hero ohne Zahl) | „Die Woche beginnt mit Zahlen: was sich bei Strom, Gas, Internet und Konto seit Freitag bewegt hat – und welche Frist in den nächsten 14 Tagen Geld kostet, wenn sie verstreicht.“ | „Zum Wochenende die Rechnung, die sich noch jetzt auszahlt: eine Frist, ein Tarifkorridor, ein Rechner – nachgerechnet in einer Viertelstunde.“ |
| Betreff-Variante | `FranksFinanzcheck: Dein Wochen-Check` (36 Z.) | `FranksFinanzcheck: Fristen vor dem Wochenende` (45 Z.) |
| Zweiter Satz der Inbox-Vorschau | „Preisgarantien, die auslaufen, und Rechner mit neuen Zahlen“ | „Was sich bis Montag erledigen lässt, mit Zahl und Frist“ |
| Grußzeile | „Wenn eine Rechnung bei dir anders aufgeht, schreib mir – ich lese jede Antwort und korrigiere offen, was falsch war.“ | „Wenn eine Zahl bei dir anders herauskommt, schreib mir – ich rechne nach und korrigiere offen, was falsch war.“ |

Die Variantenwahl ist jetzt redaktionell gesetzt (`VORZUG_VARIANTE`): Dienstag
führt die Zahl, Freitag die Frist – mit Rückfall, damit kein Tag ohne Betreff
dasteht. Betreff und Preheader sind komponiert statt abgeschnitten: Der Preheader
beginnt mit dem Auftrag des Tages und reicht so weit in den Aufmacher, wie das
120-Zeichen-Budget trägt.

**Jede Mail nennt jetzt den nächsten Termin**, z. B.
`Nächste Ausgabe: Freitag, 25. September – und nur, wenn es etwas zu rechnen gibt.`
Erwartung statt Funkstille; der Zusatz hält das Versprechen ehrlich, weil eine
Woche ohne neue Inhalte keine Ausgabe erzeugt.

### 2.3 Wache Q21 (Kadenz) – 21 Regeln statt 20

`scripts/newsletter_qa.py` prüft vor jedem Versand zusätzlich:

1. kein überholtes Werktag-Versprechen in Betreff, Preheader oder sichtbarem Text
   („pro Werktag“, „werktäglich“, „Mo–Fr“, „Montag bis Freitag“, „1 Mail/Tag“ …);
2. das Versandversprechen der Konfiguration nennt **beide** Versandtage;
3. an einem Versandtag nennt der Mail-Kopf diesen Wochentag;
4. die Zeile „Nächste Ausgabe“ ist lesbar, liegt auf einem Versandtag und ist
   derselbe Termin, den der Vertrag rechnet.

Selbsttest: fünf gezielte Manipulationen, jede liefert Q21 – 40 Fälle grün.

### 2.4 Wache auf der Website: `Kadenz` in `scripts/tests/test_newsletter_site.py`

Fünf neue Tests, damit die Kadenz nicht halb umzieht:

* keine der zwölf Leser- und Betriebsflächen verspricht noch den alten Versand;
* Landingpage, Streifen, Bestätigungs- und Präferenzseite nennen beide Tage;
* `creative.kadenz` deckt **genau** die Versandtage ab, und jeder Kadenz-Betreff
  bleibt im Längen-Gate (Q8);
* beide Versandtage bauen durchs Studio eine Mail mit eigener Identität, und beide
  bestehen die QA mit 100/100;
* die Crons beider Newsletter-Workflows tragen dieselbe Tagesliste wie der Vertrag.

### 2.5 Texte auf Premium-Stand

| Fläche | Änderung |
|---|---|
| `content/newsletter/` | Neu aufgebaut: Versprechen in drei Sätzen, Abschnitt „Was du bekommst“ mit den beiden Ausgabentagen, Anmeldung, Musterausgabe, „drin/nicht drin“, drei Schritte nach der Anmeldung, **fünf FAQ** (Kosten, Frequenz, Themen, Daten, Abmeldung), Verwaltung. Titel und Beschreibung neu. |
| `content/newsletter-bestaetigung/` | Klarer Auftakt („ein Klick fehlt noch“), Nennung des ersten Versandtermins, Prüfliste mit Grund je Punkt. |
| `content/newsletter-praeferenzen/` | Bezug auf die beiden Ausgaben, was die Auswahl ist **und** was nicht (kein Verhaltens-Tracking, keine Weitergabe). |
| `content/newsletter-abmelden/` | „Kein Bist-du-sicher, keine Umfrage“; Datenfolgen mit Fristen; **Zitierangabe korrigiert** auf Art. 7 Abs. 1 DSGVO + § 7 UWG. |
| Streifen (`newsletter_strip.html`) | „Zwei Mails pro Woche, jede mit Rechnung“ / „Dienstags die Zahlen der Woche, freitags die Fristen davor. Keine Rabatt-Post.“ / „Dienstag & Freitag · kostenlos · ein Klick zum Abmelden“. |
| Formular (`newsletter_form.html`) | Legende ohne Auswahl und Statuszeile mit Nennung des ersten Versandtermins. |
| Musterausgabe (`newsletter_muster.html`) | Bildunterschrift benennt die Regel der Ausgabe (höchstens fünf Artikel, Zahl/Stand/Frist) statt einer Wiederholung. |
| Mail (Studio) | Kicker mit Ausgabenname, Wochentag in der Kopfzeile, Aufmacher je Tag, Gruß je Tag, Nächste-Ausgabe-Zeile im Fuß – in HTML **und** Textalternative. |

## 3. Geänderte Dateien

```
content/newsletter/index.md                     (Text neu)
content/newsletter-abmelden/index.md            (Text + Zitierangabe)
content/newsletter-bestaetigung/index.md        (Text)
content/newsletter-praeferenzen/index.md        (Text)
data/newsletter_studio.json                     (creative.kadenz neu)
docs/ANLEITUNG-NEWSLETTER.md                    (Redaktionsrahmen, 21 Regeln)
docs/ANLEITUNG-NEWSLETTER-STUDIO.md             (kadenz-Block, Q21, „Mo–Fr“ entfernt)
docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md     („Mo–Fr“ → Di/Fr + Kadenz-Wache)
e2e/newsletter.spec.mjs                          (Versprechen statt Wortlaut; minify-fest)
layouts/_partials/newsletter_strip.html         (Text)
layouts/shortcodes/newsletter_form.html         (Text)
layouts/shortcodes/newsletter_muster.html       (Text)
scripts/newsletter_qa.py                        (Q21 + 5 Selbsttestfälle)
scripts/newsletter_schedule.py                  (Kalendertext, nächster Termin, Rücklesen)
scripts/newsletter_studio.py                    (kadenz_rahmen, Betreff/Preheader/Blöcke)
scripts/tests/test_newsletter_digest.py         (minify-feste Formularprüfung)
scripts/tests/test_newsletter_qa.py             (21 Regeln, zwei Q21-Tests)
scripts/tests/test_newsletter_schedule.py       (Klasse Redaktionsrahmen, 5 Tests)
scripts/tests/test_newsletter_site.py           (Klasse Kadenz, 5 Tests)
```

## 4. Verifikation

Hugo Extended 0.164.0 (aus PyPI, weil der GitHub-Asset-Host in dieser Umgebung
TLS-Fehler 35 liefert), Chromium aus dem dokumentierten
`@sparticuz/chromium`-Fallback.

| Prüfung | Ergebnis |
|---|---|
| `hugo --minify --destination public` | erfolgreich (Build: 205 Seiten; das SEO-Cockpit zählt 213 Ausgaben inkl. Sonderseiten) |
| `python3 -m unittest discover -s scripts/tests -p 'test_newsletter*.py'` | **159 Tests grün** (vorher 147, +12), 1 Skip |
| `python3 scripts/newsletter_studio.py --selftest` | 41 Fälle grün |
| `python3 scripts/newsletter_digest.py --selftest` | 55 Fälle grün |
| `python3 scripts/newsletter_qa.py --selftest` | **40 Fälle grün (21 Regeln)** |
| `python3 scripts/newsletter_cadence.py --selftest` | 14 Fälle grün |
| `python3 scripts/newsletter_zustellbarkeit.py --selftest` | 40 Fälle grün |
| `python3 scripts/newsletter_qa.py --build --days 400` | **100/100 · 21 Regeln · 0 Funde, 0 Warnungen** (14 719 Bytes, 323 Wörter, 13 Links) |
| `python3 scripts/newsletter_digest.py --check` | `aktiv` – Anmeldeweg, Landingpage, Rechtstext und Footer-CTA greifen ineinander |
| `python3 scripts/newsletter_studio.py --brand` | 28 Farbrollen hergeleitet, 6 Themenwelten deckungsgleich |
| `npx playwright test` (volle Suite, 4 Breiten, hell/dunkel) | **51 Tests grün** |
| `python3 scripts/layout_audit.py` | keine Funde, DOM-Budget eingehalten (max. 976 Elemente, Grenze 1400) |
| `python3 scripts/dom_audit.py --top 5` | alle vier Grenzen im Budget |
| `python3 scripts/seo_cockpit.py --strict` | 213 Seiten, P1: 0, P2: 0, P3: 0 |
| `python3 scripts/integrity_guard.py --drift-audit` | **kein Drift**, 43 Kerndateien signiert |
| `git diff --check` | sauber |

Gebaut und geprüft für beide Versandtage (Beispiel aus dem Bestand, 5 Artikel):

```
Dienstag, 22.09.2026 · Wochen-Check
  Betreff  : FranksFinanzcheck: 3.000 € heute prüfen (39 Z., Variante „zahl“)
  Preheader: Preisgarantien, die auslaufen, und Rechner mit neuen Zahlen –
             Reduziere die Raumtemperatur um 1 °C und spare bis zu 6 % (119 Z.)
  Fuß      : Nächste Ausgabe: Freitag, 25. September – und nur, wenn es etwas zu rechnen gibt.

Freitag, 25.09.2026 · Wochen-Abschluss
  Betreff  : FranksFinanzcheck: Fristen vor dem Wochenende (45 Z., Variante „kadenz“)
  Preheader: Was sich bis Montag erledigen lässt, mit Zahl und Frist –
             Reduziere die Raumtemperatur um 1 °C und spare bis zu 6 % (115 Z.)
  Fuß      : Nächste Ausgabe: Dienstag, 29. September – und nur, wenn es etwas zu rechnen gibt.
```

Beide Ausgaben: QA 100/100, keine Funde, keine Warnungen. Auch die leere Ausgabe
(kein Material) trägt Rahmen, Betreff und nächsten Termin und besteht das Gate.

`python3 scripts/newsletter_zustellbarkeit.py --pruefen` meldet aus dieser
Umgebung `hinweis 4, nicht messbar 2, nicht gemessen 2`: DNS-Over-HTTPS und
`api.brevo.com` sind hier teilweise nicht erreichbar (C0, C5, C6, B0). Das ist
eine Messlücke der Sandbox, **kein** Kontobefund – die Zone ist vor einem
Live-Versand aus dem Workflow oder lokal nachzumessen.

## 5. Offen – Entscheidungen, die ein Mensch trifft

**Owner: human · Severity: P2 · Channel: Produktionsfreigabe / Newsletter-Betrieb**

1. **`params.newsletterPromise` in `hugo.toml` ist versiegelt** und trägt weiter
   den Satz „Zweimal pro Woche: Spartipps und Rechner – dienstags und freitags.“
   Er ist korrekt, aber kürzer als der neue Rahmentext. Eine Änderung braucht die
   bewusste Freigabe über `python3 scripts/integrity_guard.py --set-current` –
   hier **nicht** vorgenommen.
2. **Erster Live-Versand bleibt aus** bis die Checkliste durch ist
   (`docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md`): Absender in Brevo verifizieren,
   `BREVO_API_KEY`/`BREVO_LIST_ID` als Secrets, Testversand über `test_adresse`,
   dann `live`.
3. **Journal-Abgleich:** `data/newsletter_state.json` enthält zwei wartende Artikel
   (`2026-09-20-finanzieller-puffer-…`, `2026-09-20-gasrechnung-senken-…`) und
   keine Versandhistorie. Vor dem ersten planmäßigen Lauf die Brevo-Kampagnen-
   historie gegenprüfen; eine eventuell bereits versendete Ausgabe dieser Woche
   muss als `versand_termine` (ISO mit Zeitzone) eingetragen werden.
4. **Unabhängige Brevo-Automationen** wurden nicht geprüft – der Vertrag gilt für
   den Versand aus diesem Repo.
