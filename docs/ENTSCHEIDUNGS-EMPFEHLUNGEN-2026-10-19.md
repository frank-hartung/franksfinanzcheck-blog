# Entscheidungs-Empfehlungen (Stand 19.10.2026)

Dieses Dokument hält zu jedem offenen Punkt aus dem Entscheidungsregister (`data/entscheidungen.yaml`) fest:
die Empfehlung, die Begründung, die Schritte und das Kriterium, mit dem der Punkt als erledigt gilt.
Die Entscheidung trifft Frank Hartung. Punkte mit Außenwirkung führt die Agentur nicht selbst aus. Sie liegen als Vorlage bereit.

Legende: **Außenwirkung** = Veröffentlichung, Versand, Kontakt mit Dritten oder Änderung an Markenfläche. Das bleibt bei Frank.

---

## E-16 · Cloudflare-Proxy und echte 301-Weiterleitungen

**Empfehlung: Variante A (Proxy aktivieren), in genau dieser Reihenfolge.**

Begründung: GitHub Pages liefert keine echten 301-Antworten und keinen `cf-ray`-Header. Die 115 Ersatzseiten arbeiten als Meta-Refresh. Echte Weiterleitungen und der Schutz vor Einbettung (Frame-Schutz, HSTS, nosniff) brauchen den Proxy. Der Blog hat ein Anmeldeformular, deshalb ist ein fehlender Frame-Schutz die größere Lücke. `cloudflare/edge-schutz.md`, Abschnitt 5, kommt zum gleichen Ergebnis.

Der Proxy ändert die Rechtslage. Die Zugriffsdaten laufen dann über Cloudflare. Deshalb kommt der Schritt erst nach dem Datenschutz-Schritt.

| Schritt | Wer | Abnahme |
|---|---|---|
| 1. Datenschutztext B7 (Runbook) anpassen und Auftragsverarbeitung mit Cloudflare prüfen (AVV, Drittlandübermittlung) | Frank | Text und AVV liegen vor |
| 2. Proxy in Cloudflare aktivieren (orange Wolke), Regeln A1 (Header) und A2 (WAF) aus `cloudflare/edge-schutz.md` anlegen | Frank | Antwort trägt `cf-ray` |
| 3. `python3 scripts/weiterleitungen.py --proxy-check` | Frank | Ausgabe `aktiv` |
| 4. `python3 scripts/weiterleitungen.py --cloudflare` erzeugt die Bulk-CSV, Import ins Dashboard | Frank | CSV importiert |
| 5. Stichprobe: Alt-URL aus `data/weiterleitungen.yaml` liefert 301 mit `Location` | Frank | 5 von 5 Stichproben stimmen |
| 6. Die 115 Meta-Refresh-Seiten bleiben als Fallback im Build | Agentur | keine Änderung nötig |

**Vor dem Schritt 2 erwartet `--proxy-check` den Status `inaktiv`.** Das ist normal und kein Fehler.

**Erledigt, wenn:** `--proxy-check` `aktiv` meldet und die Stichprobe in Schritt 5 grün ist.

---

## E-17 · CI-Stufe Weiterleitungen (erledigt im Code, wirksam nach Merge)

**Empfehlung: Merge in `main` ist die Voraussetzung.** Der Schritt liegt in `deploy.yml`, greift aber nur auf `main`. Ein Pull Request ist dafür der richtige Weg, weil er die Prüfung vor dem Merge sichtbar macht.

---

## E-18 · Eigener Rechner für Internetkosten

**Empfehlung: nein, jetzt nicht.**

Begründung aus den Suchdaten (`data/gsc/top_suchbegriffe_28t.json`, 28 Tage): Vier Suchbegriffe, null Klicks, keiner betrifft Internetkosten. Der Fixkosten-Scanner führt die Kategorie „Internet, Mobilfunk & Streaming“ und deckt den Fall ab. Ein Werkzeug ohne Nachfrage kostet Pflegeaufwand (Formel, Quellen, Tests, Gates) und bringt keinen Traffic.

**Wiedervorlage-Auslöser:** In den nächsten 90 Tagen erreichen Suchbegriffe zu Internetkosten zusammen mindestens 30 Impressionen in der Search Console. Dann wird ein Werkzeug als Auftrag angelegt.

**Erledigt, wenn:** Die Wiedervorlage ist im Kalender eingetragen. Frank kann die Entscheidung jederzeit überstimmen.

---

## E-05 · Fachprüfung Konto und Karten

**Empfehlung: externe Fachprüfung durch eine namentlich benannte Person.** Der Auftrag mit Prüfkriterien, Reihenfolge und Protokoll liegt in `docs/FACHPRUEFUNG-AUFTRAG-2026-10-19.md`. Konto, Karten und Zinsen kommen zuerst (6 Beiträge).

Die Agentur nennt keinen Prüfer und fingiert keine Prüfung. Im Register steht „ausstehend“, bis ein schriftliches Protokoll vorliegt.

**Erledigt, wenn:** Ein Protokoll pro Konto-Beitrag liegt vor und `scripts/fachpruefung_register.py --check` ist grün.

---

## E-09 · README-Pauschalen (Markenfläche)

**Empfehlung: die beiden Pauschalen streichen oder konkret belegen.**

Betroffene Zeilen in `README.md`, Abschnitt „Wer dahintersteht“:
- „Über zehn Jahre Praxis mit Haushaltsbudgets …“
- „Hunderte selbst durchgeführte Tarifvergleiche …“

Beides sind Angaben über die Person. Das Repo kann sie nicht prüfen, und in einem Ratgeber mit Geldthemen zählt jede Erfahrungsaussage als Versprechen. Ein Vorschlag, der ohne Belege auskommt und trotzdem Vertrauen aufbaut:

> Ich vergleiche Tarife und Verträge selbst. Bei jedem Rechner stehen Annahmen, Quellen und Stand offen dabei, damit du nachrechnen kannst.

Das ist durch die Werkzeuge im Repo belegt (Gate W1 und W7). Falls Frank die Zehn-Jahre-Angabe belegen kann, bleibt sie als eigene Aussage erhalten.

**Außenwirkung:** Die README ist Markenfläche. Änderungen nur auf Frank's Auftrag.

**Erledigt, wenn:** Frank entscheidet, und die Änderung ist in der README umgesetzt.

---

## E-11 · Redaktionskontakt und Presse-Ansprechpartner

**Empfehlung: die vorhandene Adresse prüfen, dann einen Presse-Kontaktblock ergänzen.**

Die Adresse `kontakt@franksfinanzcheck.de` steht bereits in `data/authority_strategy.yaml`. Vor der Nutzung als Presse-Adresse zwei Fragen klären: Wird sie gelesen, und wie schnell wird geantwortet. Erst danach gehört sie in `content/presse/index.md`. Ein Name und eine Rolle gehören dazu, aber nur, wenn sie zutreffen. Die Agentur fügt keine erfundenen Ansprechpartner hinzu.

**Außenwirkung:** Kontaktdaten gehen an Dritte. Freigabe durch Frank.

**Erledigt, wenn:** Die Adresse ist als gelesen bestätigt und im Presseblock eingetragen.

---

## E-12 · Finanztip-Community-Profil

**Empfehlung: nicht als Kanal nutzen, solange die Forenregeln nicht vollständig gelesen sind.**

Die Recherche hat ergeben, dass Eigenwerbung und Affiliate-Verweise in den Regeln nicht erlaubt sind. Die Recherche war ein Ausschnitt. Vor einer Anmeldung liest Frank die aktuellen Regeln vollständig. Das Profil nur als Privatperson führen, ohne Link zur Seite, ohne Signatur mit Werbung. Ein Beitrag, der ein eigenes Angebot bewirbt, wird als Verstoß gewertet.

**Außenwirkung:** Ein Profil ist öffentlich. Entscheidung durch Frank.

**Erledigt, wenn:** Frank entscheidet nach Lesen der Regeln.

---

## E-13 · Verbraucherkredit-Neuregelung (20.11.2026)

**Empfehlung: keine Maßnahme im Bestand.** Laut Register ist kein bestehender Beitrag betroffen. Vor einem neuen Beitrag zum Thema wird die Rechtslage am Stichtag geprüft. Die Wiedervorlage liegt vor dem 20.11.2026.

**Erledigt, wenn:** Die Wiedervorlage im Kalender steht.

---

## E-20 · Versand des Pressepitches (Fixkosten-Index)

**Empfehlung: noch nicht senden.** Der Name ist entschieden (Umfang steht im Titel, siehe Register). Vor dem Versand müssen fünf Bedingungen erfüllt sein:

1. Ein echter Redaktionskontakt mit Namen liegt vor (E-11).
2. Der Umfang steht im Pitch: nur Strom und Gas, mit den Grenzen der Studie.
3. Die Strompreisbasis ist offengelegt (erledigt, E-19).
4. Die Wochengrenze von 5 Outreach-Aktionen ist eingehalten.
5. Frank gibt den Versand frei.

Erster Versand an genau eine Redaktion, dann Rückmeldung abwarten, dann entscheiden.

**Außenwirkung:** Versand an Dritte. Nur auf Frank's Freigabe.

**Erledigt, wenn:** Die Freigabe ist erteilt und der Versand dokumentiert.
