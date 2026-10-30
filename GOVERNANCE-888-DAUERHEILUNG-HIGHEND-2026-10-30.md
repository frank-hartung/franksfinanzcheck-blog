# Governance #888 – Dauerheilung auf Agentur-Niveau (Redaktion & Technik)

**Prüfdatum:** 30.10.2026 (UTC)
**Gegenstand:** Issue #888 · Fingerabdruck `65df3aa59195` (Stand 26.10.2026)
**Ergebnis:** Beide gemeldeten Befunde sind mit Primärbelegen erledigt. Zusätzlich sind zwei
Steuerungsfehler geheilt, die genau diese Klasse von Befund unsichtbar machen konnten –
veraltete Messwerte und ein Protokoll, das Handlungen behauptete, die nie stattfanden.

> Dieses Dokument behauptet kein pauschales „alles grün“. Was geprüft wurde, steht mit
> Befehl und Zahl unten. Was **nicht** geprüft wurde, steht unter „Abgrenzung“.

---

## 1. Befund „10 `<img>` ohne width/height/style“ (Core Web Vitals)

### Ursache

Der Markdown-Bild-Renderhook (`layouts/_markup/render-image.html`) setzt seit dem
Vorgänger-PR intrinsische Maße. Der Wächter misst nicht das Template, sondern den
**gebauten HTML-Baum**.

### Nachweis am gebauten Stand (30.10.2026)

| Prüfung | Ergebnis |
|---|---|
| Hugo-Build | `hugo v0.168.0+extended` – erfolgreich, 113 Seiten |
| HTML-Dateien in `public/` | **401** |
| `<img>`-Elemente im gebauten Baum (eigene Zählung, unabhängig vom Wächter) | **747** |
| davon ohne `width` **und** `height` | **0** |
| `python3 scripts/cwv_guard.py --public public/ --strict-build` | **GREEN**, Exit 0, `img_nosize: 0` |
| `python3 -m unittest scripts.tests.test_render_image_template` | 3 Tests, OK |

Der Befund „10 Bilder ohne Größenvorgabe“ ist damit **nicht reproduzierbar**. Dauerhaft
abgesichert ist er doppelt: über den Vertragstest des Renderhooks (Template-Ebene) und über
die CLS-Prüfung am gebauten Baum (Auslieferungsebene). Ein Rückfall in ein später
hinzugefügtes Partial fällt damit im nächsten Lauf auf, nicht erst bei Google.

## 2. Befund „Gastarif-Entwurf Flesch 51,5 < 60“ (Lesbarkeit)

### Nachweis am Bestand (30.10.2026)

| Prüfung | Ergebnis |
|---|---|
| `readability_check.py --gate-bestand` | **GREEN**, Exit 0 |
| Live-Bestand | **72** Artikel, Ø Flesch **65,4** (Ziel ≥ 62) |
| Live-Artikel unter Floor 55 | **0** |
| Entwürfe | **28**, davon unter Publish-Schwelle 60: **0** |
| `2026-10-26-gastarife-vergleichen-vor-dem-herbst` | Flesch **60,5** (Schwelle 60) |
| `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | Flesch **60,9** (Schwelle 60) |

### Korrektur eines früheren Nachweises

Der Abschlussbericht vom 29.10.2026 nennt für den Gastarif-Entwurf **Flesch 73,8**. Dieser
Wert ist am 30.10.2026 **nicht reproduzierbar**; gemessen werden 60,5. Beide Werte liegen
über der Publish-Schwelle von 60, die Aussage „Befund erledigt“ bleibt also richtig – der
Belegwert war es nicht. Ein Abschluss, der eine Zahl nennt, muss sie beim nächsten Lauf
wiederfinden; deshalb steht die aktuelle Messung hier mit Datum und Befehl.

**Konsequenz für die Redaktion (kein Gate-Befund, offener Qualitätsauftrag):** Beide
Entwürfe liegen zwischen Publish-Schwelle (60) und Bestands-Ziel (62). Sie sind
veröffentlichungsfähig, würden den Live-Ø aber nicht heben. Vor der Freigabe ist ein
Lesbarkeits-Pass sinnvoll (`python3 scripts/readability_check.py --file <pfad>`), nicht
danach. Beide bleiben `draft: true`; hier wird nichts veröffentlicht.

## 3. Neu gefunden: das Cockpit zeigte eine 32 Tage alte Messung als aktuellen Befund

### Befund

`.casing_report.json` ist die Quelle der Casing-Zeile in der Chefredakteur-Scorecard.
Geschrieben wurde sie **nur** mit dem Schalter `--json` – und diesen Schalter rief kein
einziger Workflow auf. Der Zustand stammte deshalb vom **28.09.2026**.

Die Scorecard zeigte daraus am 30.10.2026:

```
| Groß-/Kleinschreibung – harte Befunde | 1 · 0,01/1.000 W. (110.338 W. geprüft) | 🟡 |
```

Der frische Lauf über 111 Dateien und 202.920 Wörter fand **0** Befunde. Die Gelb-Warnung
im Cockpit war also ein Archivstück – und im umgekehrten Fall (alter grüner Wert, neue
Regression) hätte sie eine echte Verschlechterung **verdeckt**. Das ist die gefährlichere
Richtung.

### Dauerheilung

1. **Der Zustand entsteht dort, wo gemessen wird.** `casing_guard.write_state()` ist jetzt
   die einzige Schreibstelle; jeder **Voll-Lauf** (Bestand) schreibt sie mit. `--new-only`
   bleibt ausgenommen: dort ist die Grundgesamtheit „heute geändert“, eine Deliktquote
   darauf wäre ein Scheinwert. `--dry-run` schreibt nie. Entscheidung als reine Funktion
   `schreibe_zustand()` – testbar, kein Kommentar-Vertrauen.
   Der Tageslauf `blog-health-daily` ruft `casing_guard.py --fix --plan` auf und committet
   mit `git add -A` – der Zustand ist damit ab jetzt **täglich** frisch, ohne Workflow-Änderung.
2. **Das Cockpit urteilt über die Frische, nicht nur über die Zahl.** Älter als 14 Tage
   (oder undatiert) ⇒ Datenlücke **⚪**, Wert-Spalte `n/a · Messung N Tage alt`, plus
   Handlungsempfehlung. Ein veralteter Befund färbt nicht mehr gelb, ein veralteter
   grüner Wert entwarnt nicht mehr.
3. **Blindflug kostet Punkte.** Eine veraltete Casing-Messung zieht 3 Punkte ab – dieselbe
   Regel, die für die Core Web Vitals schon gilt. „Nie mehr messen“ darf nicht die
   billigste Art sein, sauber auszusehen.
4. **Ein echter Restfund ist geheilt** (nicht nur weggerechnet): Im Live-Artikel
   `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` stand im Fließtext
   `DSL Tarif finden im Check:` – Akronym-Durchkopplung (Regel C2), jetzt `DSL-Tarif`.
   Die Suchphrase in `keywords` bleibt unangetastet: das ist die PROTECT-Zone, dort ist
   die getrennte Schreibweise SEO-Absicht.

**Stand nach der Heilung:** 111 Dateien, 202.920 Wörter, 0 Befunde, 0 harte Befunde,
Dichte 0,00 je 1.000 Wörter – Scorecard **100/100**, Casing-Zeile 🟢.

## 4. Neu gefunden: 25.713 Zeilen Protokoll, in denen „blog-fix“ stand, ohne dass etwas passierte

### Befund

`spam_guard.fix_blog()` schrieb bei **jedem** Lauf einen Audit-Eintrag `action: blog-fix`,
auch wenn die Wache nichts tat. Belegt in `data/spam_history.jsonl`: für den
Gastarif-Entwurf stehen am 29./30.10.2026 fünf Einträge – Grund jedes Mal `B5`
(Originalitäts-Quote 39,7 %, also **Warn**-Stufe), der Artikel war längst `draft: true`.
Kein Schreibvorgang, fünf Protokollzeilen. Bei rund 28 Entwürfen und mehreren Läufen am Tag
wächst daraus ein Protokoll, das als Beweismittel nichts mehr taugt: Aus „die Wache hat
gehandelt“ wird „die Wache war da“.

### Dauerheilung

`fix_blog()` auditiert nur noch, wenn es tatsächlich etwas geändert hat (B3-Disclosure,
B8-`*Werbung|`-Prefix, `draft: false` → `draft: true`). Ein Artikel, der schon Entwurf ist,
erzeugt keinen Eintrag mehr – die Demotion ist dann Zustand, nicht Handlung.

**Wichtig:** Das ist **keine** Abschwächung der Wache. Der Befund bleibt im Bericht, das
Gate-Verhalten ist unverändert (`spam_guard --selftest`: 24 eingefrorene Fälle grün). Es
ändert sich nur, was als *Ereignis* protokolliert wird.

## 5. Was das für #888 bedeutet

| #888-Befund | Stand 30.10.2026 | Dauerhafte Absicherung |
|---|---|---|
| CWV: Bilder ohne Größe | **erledigt** (0 von 747) | Renderhook-Vertragstest + CLS-Prüfung am Build |
| Lesbarkeit: Entwurf < 60 | **erledigt** (60,5 / 60,9 ≥ 60) | `--gate-bestand` wöchentlich, Publish-Gate im Endredaktions-Pfad |

Die beiden Zusatzbefunde (veraltetes Cockpit, inhaltsleeres Protokoll) waren nicht Teil des
Fingerabdrucks `65df3aa59195`. Sie sind hier ausgewiesen, weil sie die **Aussagekraft** der
Meldung betreffen – ein Report ist nur so gut wie die Frische seiner Messwerte.

## 6. Reproduzierbare Prüfsequenz

```sh
# Technik (Core Web Vitals am gebauten Stand)
hugo --minify --destination public
python3 scripts/cwv_guard.py --public public/ --strict-build        # GREEN, img_nosize 0
python3 -m unittest scripts.tests.test_render_image_template        # 3 OK

# Redaktion (Lesbarkeit)
python3 scripts/readability_check.py --selftest
python3 scripts/readability_check.py --gate-bestand                 # GREEN, 0 unter Floor
python3 scripts/readability_check.py --file content/posts/2026-10-26-gastarife-vergleichen-vor-dem-herbst/index.md

# Messfrische & Protokoll (neu abgesichert)
python3 scripts/casing_guard.py --selftest
python3 scripts/casing_guard.py --fix --plan                        # schreibt .casing_report.json
python3 scripts/spam_guard.py --selftest
python3 -m unittest scripts.tests.test_governance_messfrische       # 17 OK
python3 scripts/editorial_scorecard.py                              # 100/100, Casing 🟢
```

## 7. Abgrenzung – was hier ausdrücklich nicht behauptet wird

- **Keine Feldmessung.** Der CWV-Wächter misst deterministisch den gebauten Baum, nicht
  CrUX/RUM. „0 Bilder ohne Größe“ ist ein CLS-Risiko-Nachweis, keine LCP-Zusage.
- **Keine Veröffentlichung.** Beide Entwürfe bleiben `draft: true`. Lesbarkeit ≥ 60 ist die
  Publish-Schwelle, keine inhaltliche oder rechtliche Freigabe (YMYL).
- **Keine Prognose über den nächsten Governance-Lauf.** Er bewertet seine eigenen Schritte;
  neue Befunde außerhalb dieser beiden Klassen sind damit nicht ausgeschlossen.
- **28 Entwürfe sind Vorrat, kein Fehler.** Die Scorecard zeigt die Warteschlange rot, weil
  sie ab 9 Stück Arbeit bedeutet – die Redaktionsentscheidung (veröffentlichen, nachschärfen,
  verwerfen) trifft kein Skript.
- **Die B5-Warnung des Gastarif-Entwurfs (39,7 % Originalität) bleibt offen.** Sie ist eine
  Stil-/Originalitätswarnung, kein Gate-Blocker; sie braucht redaktionelle Hand, nicht Code.
