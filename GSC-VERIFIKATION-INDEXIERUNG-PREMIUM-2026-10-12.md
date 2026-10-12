# Search Console: Verifikation und Indexierung auf Dauerbetrieb

**Datum:** 12.10.2026 · **Auftrag:** Frank – „Bitte dafür sorgen, dass die Google Search Console alle
Seiten meines Blogs verifiziert und indexiert, auf Premium-Level einer Profi-Agentur."

**Ergebnis:** Die technische Seite ist geschlossen und maschinell bewacht. Drei Handgriffe in deinem
Google-Konto kann kein Agent übernehmen – sie sind in Abschnitt 6 benannt und dauern zusammen keine
zehn Minuten.

---

## 1. Befund: Was vorher war

Die Site war **nicht** kaputt. Sitemap, robots.txt, Canonical, JSON-LD und Index-Hygiene waren
bereits auf einem Stand, den die meisten Agenturen nicht erreichen. Die Lücke lag an einer anderen
Stelle: Das Projekt konnte den Index **beobachten**, aber nicht **ansprechen**.

Drei Wege in den Google-Index waren vorhanden – Sitemap (Entdeckung), robots.txt (Erlaubnis) und
Warten (Zufall). Der vierte fehlte: die aktive Anfrage.

Dazu zwei messbare Befunde:

**Befund A – 20 von 74 indexierbaren Seiten wurden nie an eine Suchmaschine gemeldet.**
`scripts/submit_indexnow.py` arbeitete mit einer handgeschriebenen Namensliste: alle Posts, sechs
namentlich genannte Pillar-Slugs, drei Hubs, die Startseite. Gemessen am Build vom 12.10.2026:

```
74 indexierbare URLs in der Sitemap
54 URLs in der IndexNow-Meldeliste
20 indexierbare Seiten, die NIE gemeldet wurden
```

Darunter die acht Werkzeug-Rechner (`/werkzeuge/*/`), das Fixkosten-Cockpit (`/cockpit/`), die
Studien-Seite samt Fixkosten-Index, `/ueber/`, `/transparenz/`, `/impressum/`, `/datenschutz/`,
`/presse/` und `/aenderungsprotokoll/`. Also genau die Seiten, die Vertrauen und Umsatz tragen –
`/ueber/` und `/methodik/` sind die E-E-A-T-Träger der ganzen Domain, die acht Rechner das
Produktversprechen, das am 02.10.2026 extra in die Hauptnavigation gehoben wurde.

Die Ursache ist keine Nachlässigkeit, sondern eine **Konstruktionsklasse**: Eine Namensliste bricht
bei jedem Wachstum. Dieselbe Klasse hatte `layouts/sitemap.xml` am 01.10.2026 schon einmal erledigt
(dort stand die Begründung: „Vorher stand hier eine Namensliste. Jede neue Seite fiel damit aus der
Sitemap, bis jemand den Namen nachtrug"). Beim Einreichungsweg war sie stehen geblieben.

**Befund B – 32 tote URLs im IndexNow-Zustand.** `.indexnow_submitted.json` führte 32 Einträge der
alten github.io-Auslieferung (`https://frank-hartung.github.io/franksfinanzcheck-blog/…`). IndexNow
prüft, ob die gemeldete URL zum Host des Schlüssels passt – diese Einträge waren totes Gewicht, und
sie machten den Zustand als Beleg unbrauchbar: „135 eingereichte URLs" klang nach mehr Abdeckung,
als es war.

**Befund C – die Zugangsschicht zur Search Console war unbewacht.** Zwei Wachen maßen bereits
wertvoll: `index_hygiene_gate.py` die **Menge** der Crawl-Fläche (H1–H8), `schema_seo_gate.py` die
**Auszeichnung** der einzelnen Seite. Keine prüfte die dritte Ebene – ob Google die Site überhaupt
verifizieren kann:

- Liegt der Besitznachweis im Build, **und stimmt sein Inhalt mit dem Dateinamen überein**? Eine
  `google8f0cd9537348f066.html`, in der ein anderer Token steht, verifiziert nichts. Der Fehler
  fällt nicht im Build auf, sondern Wochen später als „Property nicht bestätigt".
- Sperrt `robots.txt` versehentlich Googlebot aus? Die Datei enthält Cloudflare-Managed-Content mit
  zehn User-agent-Blöcken. Ein `Disallow: /` im `User-agent: *`-Block kostet die gesamte
  Sichtbarkeit – und der Build bleibt grün.
- Ist die Sitemap protokollgültig? Google lehnt bei über 50.000 URLs, über 50 MiB, Duplikaten oder
  fremden Hosts ab; die Wache dafür gab es nicht.
- Hat **jede** noindex-Seite einen erklärten Grund? „Gefunden – derzeit nicht indexiert" ist der
  häufigste GSC-Befund überhaupt, und seine Ursache ist fast immer ein `noindex`, das niemand mehr
  kennt.

## 2. Reparatur: eine Quelle statt drei Wahrheiten

### 2.1 `scripts/indexierbare_seiten.py` – die gemeinsame Quelle

Beantwortet die Frage „welche Seiten sollen in den Index?" **einmal**, aus der Sitemap. Daraus lesen
beide Einreichungswege: `gsc_indexierung.py` (Google) und `submit_indexnow.py` (Bing/Yandex/Naver/
Seznam – Google nimmt an IndexNow nicht teil).

Die Regel ist dieselbe wie für die Sitemap selbst: **ableiten, nicht aufzählen.** Eine Seite, die
indexierbar ist, steht in der Queue. Eine Seite, die auf noindex geht, verschwindet von selbst. Ein
neuer Seitentyp braucht keine Code-Änderung mehr.

Das Modul liest wahlweise den Build (`public/sitemap.xml`) oder die **ausgelieferte** Sitemap
(`--live`). Letzteres ist für die Einreichung der ehrlichere Weg: Eingereicht wird, was Google auch
sehen kann – nicht, was ein lokaler Build zufällig enthält.

Fail-closed: Eine leere oder unerreichbare Sitemap ist ein Fehler (Exit 2), kein Leerlauf. Ein
Einreichen mit null URLs sähe aus wie Erfolg und wäre keiner.

### 2.2 `scripts/gsc_indexierung.py` – die aktive Anfrage

Die URL Inspection API ist derselbe Knopf wie „Indexierung beantragen" in der Oberfläche. Ein neuer
Artikel ist damit nicht „irgendwann" geprüft, sondern in der Regel binnen Stunden – und die Antwort
nennt den **Grund**, falls Google ablehnt.

Was das Skript mitliefert, weil eine Automatik ohne Haushalt eine Plage ist:

- **Berechtigungs-Vorcheck.** Vor der ersten Anfrage wird die Property-Liste gelesen. Ist die Stufe
  „Eingeschränkt" statt „Vollständig", meldet das Skript `keine_berechtigung` mit der konkreten
  Abhilfe – statt 74-mal HTTP 403 zu sammeln und als „kein Zugriff" zu verschlucken.
- **Kontingent-Haushalt.** 200 Anfragen je Property und Tag sind hart. Das Skript führt ein
  Gedächtnis (`data/gsc_indexierung_state.json`), hält 5 Anfragen Sicherheitsabstand und bricht bei
  HTTP 429 ab, statt die übrige Queue weiter zu traktieren.
- **Wiedervorlage statt Dauerfeuer.** Indexiert → 28 Tage. Noch nicht indexiert → 7 Tage. Inhalt
  geändert (`lastmod`) → sofort. Unveränderte URLs täglich einzureichen ist genau das, wovor Google
  in den Richtlinien warnt; ohne Fristen hätte der tägliche Lauf nach einer Woche nichts mehr frei.
- **Reihenfolge nach Wichtigkeit.** Die Sitemap trägt die redaktionelle Gewichtung bereits
  (`priority` je Seitentyp). Zusammen mit `lastmod` ergibt das eine Queue ohne Namenseinträge.
- **API-Drift sichtbar.** Unbekannte Felder in Googles Antwort werden als Schlüsselnamen notiert.
  Ein Feldwechsel wird damit zum Befund statt zum stillen Datenverlust.
- **Getrennte Scopes.** Der Lese-Import behält `webmasters.readonly`; die Anfrage nutzt
  `webmasters`. Bewusst zwei Funktionen statt eines Parameters: Der Lese-Import soll niemals
  versehentlich mit Schreibrechten laufen. Die Signatur-Kette (JWT/RS256 über `openssl`) bleibt
  dieselbe – ein Ort für eine Wahrheit.

**Abgrenzung, die wichtig ist:** Die URL Inspection API ist **nicht** die „Google Indexing API".
Diese gilt ausschließlich für `JobPosting`- und `BroadcastEvent`-Seiten; sie für einen
Ratgeber-Blog zu benutzen wäre ein Richtlinienverstoß und würde die Property riskieren. Für eine
normale Website ist die URL Inspection API der einzige offizielle maschinelle Weg.

### 2.3 `scripts/gsc_verifikations_guard.py` – V1–V13

Prüft die Zugangsschicht. Bewusst **kein `--fix`**: Jeder Fund ist eine Entscheidung über Zugang,
Index oder Architektur – die trifft die Redaktion, nicht eine Wache.

| Regel | Prüfung |
|---|---|
| V1 | Besitznachweis liegt im Build **und** sein Inhalt passt zum Dateinamen |
| V2 | robots.txt sperrt Googlebot nicht aus (Trainings-Bots wie `Google-Extended` dürfen zu bleiben) |
| V3 | Sitemap-Hinweis: absolut, eigener Host, Datei vorhanden |
| V4 | Sitemap-Protokoll: XML, ≤ 50.000 URLs, ≤ 50 MiB, keine Duplikate, kein fremder Host, keine Query, Kind-Reihenfolge, Bild-Tag nach `priority` |
| V5 | Sitemap ↔ gebaute Wahrheit in beide Richtungen |
| V6 | Canonical selbstreferenziell |
| V7 | Keine Verifikationsdatei, keine `/go/`-Weiterleitung, kein Pager in der Sitemap |
| V8 | Startseite trägt WebSite- und Organization-JSON-LD |
| V9 | Jede noindex-Seite hat einen erklärten Grund |
| V10 | Ein in `hugo.toml` gesetzter Meta-Token kommt auch im Build an |
| V11/V12 | Hinweise: fehlendes `lastmod`, fehlender Bild-Eintrag, Waisen |
| V13 | **live**: Besitznachweis, robots.txt und Sitemap erreichbar, inhaltsgleich zum Build, ohne Weiterleitung; Stichprobe auf 200, `index`, korrektes Canonical |

Zwei Entscheidungen in V9, die ohne Begründung wie Fehler aussehen:

- **Funktionsflächen aus `static/` zählen nicht als Inhalt.** Der Veröffentlichungskalender
  (`static/kalender/index.html`) und die Pinterest-Autorisierung (`static/pinterest-oauth.html`)
  tragen ihr `noindex` selbst und bewusst. Von ihnen ein Frontmatter-Feld zu verlangen hieße, eine
  Redaktion zu erfinden, die es für diese Dateien nicht gibt. Die erste Fassung der Wache meldete
  beide als Fund – das war ein Fehlalarm der Wache, nicht der Site.
- **Rechtsseiten ohne `lastmod` sind Redaktionspolitik, kein Defekt.** `sitemap_lastmod.html` setzt
  nur belegte Redaktionsdaten: Impressum, Datenschutz und Über-mich sollen kein künstliches „heute
  geändert" tragen. V11 meldet ein fehlendes `lastmod` deshalb nur für Seiten, deren Aktualität ein
  Versprechen ist (Artikel, Ratgeber, Rechner, Studien, Startseite).

### 2.4 `scripts/submit_indexnow.py` – von der Liste auf die Quelle

Umgestellt auf `indexierbare_seiten.py`, damit IndexNow denselben Bestand meldet wie Google. Dazu:

- **Zustands-Hygiene:** Die 32 github.io-Altlasten werden beim ersten Lauf entfernt und im Bericht
  gezählt. Ein Zustand, der tote URLs führt, taugt nicht als Beleg.
- **Schlüsselvertrag:** Schlüssel und `static/<schlüssel>.txt` werden auf Übereinstimmung geprüft.
  IndexNow antwortet bei fehlender Datei mit 422 („Bad parameter") – eine Meldung, aus der niemand
  die Ursache liest.
- **Batch-Grenze:** höchstens 10.000 URLs je Anfrage, wie das Protokoll es vorschreibt.
- **`--kein-llms` für den Tageslauf:** `generate_llms_txt.py` schreibt `date.today()` in den Kopf,
  die Datei ändert sich also jeden Tag. Da `static/llms.txt` zu Recht deploy-relevant ist (es ist
  eine ausgelieferte Datei), hätte ein täglicher Commit jeden Tag einen vollständigen Deploy
  ausgelöst – genau Befund F1 des Premium-Audits. Die wöchentliche Pflege bleibt bei
  `seo-weekly.yml`, der Tageslauf reicht URLs ein und fasst keine Inhaltsdatei an.

## 3. Verdrahtung

Eine Wache, die niemand verlangt, führt irgendwann niemand aus. Deshalb:

| Wo | Was | Wirkung |
|---|---|---|
| `deploy.yml` | V1–V12 **nach** dem Build, **vor** der Auslieferung | hart: eine Site, die ihren Besitznachweis verliert oder sich selbst aussperrt, geht nicht live |
| `gsc-import.yml` (neu, täglich 05:17 UTC) | Selbsttests → V13 live → Leistungsdaten → Indexierungs-Anfrage → IndexNow → Zustand sichern → PR | Dauerbetrieb |
| `governance_contract.GUARDS` | alle vier Skripte | C6: ihr `--selftest` läuft in jedem Qualitäts-Gate mit |
| `deploy.yml` / `deploy-catchup.yml` | `data/gsc_indexierung_state.json`, `data/gsc/.*` in `STATE_ONLY` | ein tägliches Lebenszeichen löst keinen Livegang aus |
| `package.json` | `gsc:bestand`, `gsc:verifikation`, `gsc:verifikation:live`, `gsc:plan`, `gsc:indexieren`, `gsc:daten`, `gsc:setup`, `indexnow`, `test:gsc` | ein Befehl je Frage |

**Zwei Wege im Tageslauf, bewusst getrennt.** Der **Zustand** wird direkt auf `main` gesichert:
Ohne ihn weiß der nächste Lauf nicht, was er schon angefragt hat, und verbrennt das
Tageskontingent. Ein Zustand, der auf einen PR wartet, ist kein Zustand. Die **Leistungsdaten**
gehen als PR: Das sind Kennzahlen, die Frank liest und einordnet; ein automatischer Merge würde
unbemerkt Zahlen in den Bestand schreiben, die niemand geprüft hat. So stand es bereits in der
Vorlage vom 11.10.2026, und so bleibt es.

Die Vorlage `docs/workflow-vorlagen/gsc-import.yml` ist entfernt: Ein scharfer Workflow und seine
Vorlage nebeneinander sind zwei Wahrheiten über denselben Ablauf.

## 4. Nachweis

```
npm run test:gsc
  ✅ indexierbare_seiten    Parsing, Bild-Sitemap, Reihenfolge, Frische, 6 Fehlerpfade, 3 Sabotage-Proben
  ✅ gsc_verifikations_guard V1–V10 am Fixture-Build: 22 Sabotage-Proben, 4 Gegenproben; V13 ohne Netz
  ✅ gsc_indexierung        13 Fallgruppen: Token-Scope, Berechtigungs-Vorcheck, Queue, Kontingent,
                            Wiedervorlage, 403/429, Zustands-Hygiene, Fail-closed
  ✅ gsc_import             JWT/RS256 mit openssl verifiziert, Paginierung, Merge, Geheimnisschutz
  ✅ submit_indexnow        Schlüsselvertrag, Queue aus der Sitemap, Batch-Grenze, Zustands-Hygiene
  ✅ 54 Regressionstests (scripts/tests/test_gsc_indexierung_kette.py)
```

Jede Regel hat eine Sabotage-Probe (muss anschlagen) und, wo es eine gültige Variante gibt, eine
Gegenprobe (muss still bleiben). Ohne Gegenproben meldet eine Wache alles und ist damit wertlos –
deshalb sind sie Teil des Vertrags, nicht ein Anhang.

Weitere Läufe, alle grün:

```
scripts/selftest_runner.py            190 Wachen · 380 Uhr-Proben (+97/+1461 Tage) · 132 s
scripts/selftest_ki.py --trap-workflows  113 Selbsttests, keiner hängt an KI oder Netz (#138)
scripts/governance_contract.py        33 Regeln, beide Richtungen
scripts/index_hygiene_gate.py         115 HTML-URLs · 76 indexierbar · Verhältnis 0,51 (Budget 1,0)
scripts/schema_seo_gate.py            115 Seiten, 50 Money-Pages · 0 harte Funde
scripts/manifest_guard.py             grün
scripts/actions_version_guard.py      keine Drift
python3 -W error::ResourceWarning …   alle fünf Selbsttests ohne offene Datei-Handles
```

**Gemessen am echten Build vom 12.10.2026:**

| Kennzahl | Vorher | Nachher |
|---|---|---|
| Indexierbare Seiten in der Sitemap | 74 | 74 |
| Davon je an eine Suchmaschine gemeldet | 54 (73 %) | 74 (100 %) |
| Tote github.io-URLs im Zustand | 32 | 0 |
| Aktive Indexierungs-Anfrage an Google | nicht vorhanden | täglich, bis 195/Tag |
| Bewachte Regeln der Zugangsschicht | 0 | 13 (V1–V13) |
| Regressionstests der Kette | 2 | 54 |

Die 74 Seiten selbst sind unverändert – es wurden keine neuen erfunden und keine abgeschaltet.
Geändert hat sich, was mit ihnen passiert.

## 5. Was die Wache heute meldet

Der Lauf gegen den aktuellen Build ist grün:

```
Besitznachweise (Datei) .... google8f0cd9537348f066.html
robots.txt-Sitemap-Hinweise  1
Sitemap-Einträge ........... 74   (mit Bild-Sitemap: 50)
Indexierbare Seiten im Build 76
Noindex ohne erklärten Grund 0
Noindex-Funktionsflächen ..... 23 (/go/*, /kalender/, pinterest-oauth)
✓ Verifikation und Indexierbarkeit sind sauber belegt.
```

76 indexierbare Seiten gegen 74 Sitemap-Einträge ist **kein** Widerspruch: Die Differenz sind die
zwei Besitznachweise (`google8f0cd9537348f066.html` und die IndexNow-Schlüsseldatei). Sie sind
indexierbar, aber kein Inhalt – deshalb stehen sie zu Recht nicht in der Sitemap, und V7 prüft, dass
sie nie hineingeraten.

## 6. Die drei Handgriffe, die nur du machen kannst

Ein Agent kann sich nicht in dein Google-Konto anmelden, und er legt keine Geheimnisse an. Alles
andere läuft automatisch.

1. **Property verifizieren** – Domain-Property `franksfinanzcheck.de` über einen DNS-TXT-Eintrag in
   Cloudflare. Empfehlung Domain statt URL-Präfix: Sie fasst Protokolle und Subdomains zusammen
   (`abos.franksfinanzcheck.de`) und ist die Voraussetzung dafür, dass die URL Inspection API für
   jede URL der Domain funktioniert. Der zweite Weg (HTML-Datei für die URL-Präfix-Property) ist
   bereits ausgeliefert und bewacht. → Runbook Abschnitt 1.
2. **Sitemap einreichen** – Search Console → Sitemaps → `https://franksfinanzcheck.de/sitemap.xml`.
   Einmalig. → Runbook Abschnitt 2.
3. **Dienstkonto auf „Vollständig" setzen** – ohne diese Stufe läuft der Tageslauf grün, meldet aber
   dauerhaft `keine_berechtigung`, und die Site bliebe im Zustand „Sitemap hinlegen und warten".
   → [ANLEITUNG-GSC-API-ZUGRIFF.md](docs/ANLEITUNG-GSC-API-ZUGRIFF.md), Schritt 5.

Danach, einmalig:

```bash
npm run gsc:setup                              # sieht das Dienstkonto die Property? (erwartet: siteOwner)
python3 scripts/gsc_import.py --backfill       # 480 Tage Leistungsdaten nachholen
python3 scripts/gsc_indexierung.py --live --plan   # 74 Seiten wären fällig – passen in EIN Tageskontingent
```

## 7. Ehrliche Grenzen

- **Verifizierung und Indexierung kann niemand garantieren.** Google entscheidet selbst. Was hier
  gebaut ist, stellt sicher, dass jede Seite angeboten, angefragt und – falls Google ablehnt – der
  **Grund** protokolliert wird. Das ist der Unterschied zwischen „warten" und „steuern", nicht
  zwischen „vielleicht" und „sicher".
- **Der Live-Befund V13 konnte in dieser Arbeitskopie nicht laufen.** Die Sandbox hat keinen Zugang
  zu `franksfinanzcheck.de`. Der Build-Befund (V1–V12) ist gemessen und grün; V13 ist mit
  injiziertem HTTP gegen Sabotage-Proben getestet und läuft erstmals im Tageslauf. Ein lokaler
  grüner Audit ist keine Aussage über den veröffentlichten Stand – dieser Satz steht seit dem
  20.09.2026 im Runbook, und er gilt auch für diesen Bericht.
- **Bis zu den ersten API-Antworten ist der Indexierungs-Zustand unbekannt.** `data/gsc/` ist leer,
  `data/gsc_indexierung_state.json` entsteht beim ersten Lauf. Die Zahlen in Abschnitt 4 sind
  Build-Messungen, keine Search-Console-Daten.
- **200 Anfragen pro Tag sind ein echtes Limit.** Bei 74 Seiten ist es heute komfortabel. Wächst die
  Site darüber, entscheidet die Reihenfolge (Wichtigkeit, dann Frische) – die Money-Pages kommen
  zuerst, der lange Schwanz über die Sitemap. Das ist gewollt und im Skript dokumentiert.

## 8. Geänderte Dateien

**Neu**

- `scripts/indexierbare_seiten.py` – eine Quelle für „welche Seiten sollen in den Index?"
- `scripts/gsc_indexierung.py` – aktive Indexierungs-Anfrage (URL Inspection API)
- `scripts/gsc_verifikations_guard.py` – V1–V13
- `scripts/tests/test_gsc_indexierung_kette.py` – 54 Regressionstests
- `.github/workflows/gsc-import.yml` – täglicher Lauf (Daten + Anfragen)

**Geändert**

- `scripts/submit_indexnow.py` – von der Namensliste auf die Sitemap; Zustands-Hygiene,
  Schlüsselvertrag, Batch-Grenze, `--kein-llms`
- `.github/workflows/deploy.yml` – GSC-Verifikations-Gate vor der Auslieferung; `STATE_ONLY` ergänzt
- `.github/workflows/deploy-catchup.yml` – `STATE_ONLY` ergänzt (decktgleich zu deploy.yml)
- `scripts/governance_contract.py` – vier Wachen in `GUARDS` (C6)
- `scripts/tests/test_deploy_gate_paths.py` – Vertrag: GSC-Zustand löst keinen Deploy aus
- `package.json` – neun Befehle für die Kette
- `docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md` – neu gefasst: Verifikation, Anfrage, Wache, Grenzen
- `docs/ANLEITUNG-GSC-API-ZUGRIFF.md` – Schreib-Scope, Stufe „Vollständig", API-Grenzen, Tageslauf

**Entfernt**

- `docs/workflow-vorlagen/gsc-import.yml` – vom scharfen Workflow abgelöst

Runbook: [`docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md`](docs/ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md)

---

## 9. Nachtrag 12.10.2026 – ein eigener Fehler, den erst CI gefunden hat

Abschnitt 4 stand zuerst mit anderen Zahlen da, und `_selftest()` in
`scripts/gsc_indexierung.py` trug den Docstring *„Offline-Selbsttest mit Fake-API: kein
Netz, keine Uhr, keine Schreiberei."* Der erste Teil war falsch. Die KI-Probe des
Regressions-Jobs (`scripts/selftest_ki.py --trap-workflows`, Vertrag aus #138) hat es
gemeldet:

```
🛑 scripts/gsc_indexierung.py (0.2s) – NETZ
     ↳ create_connection → x:443 aus scripts/indexierbare_seiten.py:287 (_hole_http)
```

**Ursache.** `lauf()` ersetzte den API-Transport über `http=`, reichte aber keinen
Transport für das Holen der Sitemap durch. `hole_seiten()` hat seit jeher einen
injizierbaren `http`-Parameter – `lauf()` nutzte ihn nicht. Zwei Folgen:

1. Der Selbsttest griff für die Fälle 1 und 2 wirklich ins Netz (Ziel `https://x/sitemap.xml`).
2. Die beiden Prüfungen waren dadurch **verstellt**. Fall 1 sollte „kein Zugang →
   `nicht_konfiguriert`" beweisen; tatsächlich kam der Netzwerk-Fehlschlag zuerst, also
   wurde `werkzeugfehler` geprüft. Fall 2 trug die Assertion
   `b2["status"] in ("werkzeugfehler", "ok")` – eine Prüfung, die beide Ausgänge
   akzeptiert, ist keine Prüfung. Der Docstring „alle Zugänge sind injizierbar → offline
   testbar" war ein Wunsch, kein Vertrag.

**Heilung.** `lauf()` bekommt `sitemap_http` und reicht es an beide `hole_seiten`-Aufrufe
durch. Die zwei getrennten Transporte sind jetzt im Docstring benannt, weil sie
verschiedene Signaturen haben (`(method, url, headers, body)` gegen `(url) -> (status,
text)`) – wer nur einen ersetzt, greift trotzdem ins Netz.

Die Selbsttest-Fälle sind seither scharf statt verstellt:

| Fall | Vorher | Nachher |
|---|---|---|
| 1 | `werkzeugfehler` durch Netzabbruch | Sitemap antwortet 404 → `werkzeugfehler`, **und** es wird nichts angefragt |
| 2 | `in ("werkzeugfehler", "ok")` – wertlos | intakte Sitemap, kein Zugang → exakt `nicht_konfiguriert`, Bestand 3 Seiten, **keine** Anfrage |
| 3 | voller Lauf über den `--urls`-Notweg | voller Lauf über die **injizierte Sitemap** – der Regelweg, mit Gewichtung 1.0/0.9/0.8 |

**Beweis, dass die Wache greift.** Die Durchreichung wurde probehalber wieder entfernt:
Der neue Test `test_sitemap_transport_ist_injizierbar` schlägt an mit *„der echte
Sitemap-Transport wurde erreicht"*, der Selbsttest bricht ab. Die Gegenprobe
`test_ohne_injektion_bleibt_der_echte_transport_zustaendig` bleibt dabei grün – sie
nagelt die andere Richtung fest: Ohne Injektion muss weiter `_hole_http` zuständig sein,
sonst „heilt" die Naht dadurch, dass der Tageslauf mit `--live` nie die ausgelieferte
Sitemap sähe und still einen erfundenen Bestand anfragte. Grünes Gate, falsche Wirklichkeit.

**Zahlen danach.** KI-Probe 113/113 ohne Netz · Regressionstests der Kette 54 statt 52 ·
Gesamtsuite 2815 Tests, 0 Fehler · Selbsttest-Runner 190 Wachen, 380 Uhr-Proben, grün.

**Was das lehrt.** Ein Selbsttest, der „kein Netz" behauptet, ist keine Zusage, sondern
eine Behauptung – und dieses Repository hat mit der KI-Probe eine Wache, die sie prüft.
Der Fund kam nicht aus dem Code-Review, sondern aus dem zweiten, upload-unabhängigen Gate.
Er hätte ohne CI unbemerkt bleiben können, weil alle 52 Tests grün waren: Sie liefen über
den `--urls`-Pfad und berührten die Sitemap-Naht nie.
