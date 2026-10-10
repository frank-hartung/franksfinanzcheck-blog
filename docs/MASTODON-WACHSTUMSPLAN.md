# Mastodon: Profil & organisches Wachstum für FranksFinanzcheck

**Stand: 10.10.2026 · Budget: 0 € Werbeausgaben · Umsetzung: Frank Hartung**

## 1. Status – vorbereitet ist nicht live

Profil: https://mastodon.social/@FranksFinanzcheck

Die Änderungen liegen im Repository. Das Live-Profil wurde in dieser Sitzung **nicht** abgerufen oder geändert: kein Mastodon-Connector und kein direkter Netzwerkzugang zur Instanz. Es wurden keine Beiträge veröffentlicht, Accounts automatisch gefolgt oder Nachrichten verschickt.

Befund aus vorhandenen Daten:

- Der bisherige Profil-Sync setzte „1.800 € sparen“, „25+ Guides“ und einen festen Veröffentlichungsrhythmus. Diese Claims sind für ein dauerhaftes Profil ungeeignet: Sparsumme unbelegt, Zähler/Zeiten veralten.
- `data/social/performance.yaml` vom 10.10.2026 enthält elf gemessene Beiträge mit jeweils Engagement-Score 0. Das ist **kein Nachweis für null Impressionen** und keine aktuelle Live-Prüfung.
- Der Bericht `SOCIAL-PERF-FEEDBACK-PREMIUM-2026-10-03.md` nennt null Follower am 03.10.; daraus darf keine heutige Followerzahl abgeleitet werden.
- Die Website hat schon `rel="me"` im Head und im Footer. Das wird nicht als neue Verbesserung verkauft. Die Über-Seite erhält zusätzlich einen direkten Austausch-Link.
- Die Nullwerte führten bisher allein wegen unterschiedlicher Stichproben zu ungleichen Themengewichten. Korrigiert: ohne Interaktionen neutrale Gewichte/Cooldowns, keine künstlichen Gewinner oder Flops. Auch der Planer bleibt bei gleichen Gewichten in seiner bisherigen Hash-Rotation, statt einen alphabetischen „Sieger“ zu bevorzugen.

**Strategische Entscheidung:** Erst Profilvertrauen und echte Gespräche, dann anhand ausreichender Daten optimieren. Mehr automatisierte Bloglinks allein lösen den Publikumsengpass nicht.

## 2. Profil zum Übernehmen

### Anzeigename

**Frank | FranksFinanzcheck**

Persönlicher Absender plus wiedererkennbare Marke, ohne unbewiesenes Sparversprechen.

### Bio – 470 Zeichen, ohne Codeblock-Markierung kopieren

> Ich bin Frank Hartung. Ich helfe dir, Fixkosten nachvollziehbar zu prüfen – mit Rechnungen und Checklisten statt Wechsel-Druck.
>
> Strom & Gas · Internet · Versicherungen · Konto · Budget · Mobilität
>
> Mein 4K-Kompass: Kosten sehen, Konditionen rechnen, Kündigungsfenster sichern, Kurs halten.
>
> KI-unterstützte Ratgeber. Der Blog enthält Affiliate-Links (Werbung). Keine individuelle Finanzberatung.
>
> Welche Fixkosten möchtest du als Nächstes prüfen? #Fixkosten #GeldSparen

### Vier Profilfelder

| Name | Wert |
|---|---|
| Fixkosten-Cockpit | https://franksfinanzcheck.de/cockpit/ |
| Ratgeber | https://franksfinanzcheck.de/pillar/ |
| Über Frank | https://franksfinanzcheck.de/ueber/ |
| Transparenz | https://franksfinanzcheck.de/transparenz/ |

Das Cockpit ist der konkrete nächste Schritt; Ratgeber liefern Tiefe, Autor und Transparenz Vertrauen. Keine Partner-/Kurzlinks im Profil.

### Bildsprache & Auffindbarkeit

- Vorhandenes Markenlogo und 1500×500-Banner sind konsistent: dunkelgrün, gelber Haken, lesbare Marke. Beibehalten statt beliebiger KI-Stockbilder. Banner wurde lokal geprüft; Zuschnitt auf Mobilgeräten nach Übernahme kontrollieren.
- Vorhandene Bilddateien: `static/images/social/mastodon-avatar.png` und `mastodon-header.png`. Die Header-Beschreibung im Sync wurde an das tatsächliche Motiv angepasst. Ob die Instanz diese Beschreibungsfelder darstellt, muss live geprüft werden.
- Profil im Verzeichnis und Suchindex anbieten, wenn du dieser öffentlichen Auffindbarkeit zustimmst. Sichtbarkeit ist eine Voraussetzung, keine Reichweitengarantie.
- Öffentlich sichtbare Posts nutzen, wenn sie neue Leser erreichen sollen; Veröffentlichungssichtbarkeit und Sprache Deutsch im Editor kontrollieren. Keine privaten Vertragsdaten veröffentlichen.
- Der Sync lässt die vorhandene Bot-Kennzeichnung unverändert. Kennzeichne die tatsächliche Automatisierung ehrlich; das Entfernen eines Bot-Flags ist kein Wachstumstrick.
- Nach Übernahme die Link-Verifizierung prüfen. Ein grüner Link bestätigt Kontrolle über die Website, **keine** redaktionelle Zertifizierung oder Finanzqualifikation. Verifizierung kann verzögert erscheinen.

### Live-Übernahme: zwei Wege

**Ohne technische Freigabe:** In Mastodon → Profil bearbeiten Anzeigename, Bio und vier Felder kopieren; Auffindbarkeit kontrollieren; speichern. Anschließend veröffentlichte Darstellung und Link-Verifizierung prüfen.

**Mit vorhandenem GitHub-Workflow:** Änderungen auf dem gewünschten Stand bereitstellen; Actions → **Mastodon-Profil-Sync** → Branch mit diesen Änderungen auswählen → zunächst `dry_run=true`. Vorschau prüfen, dann ausdrücklich `dry_run=false` setzen. Der Standard ist jetzt Vorschau. Das bestehende GitHub-Secret muss `write:accounts` erlauben. Keine Tokens im Chat oder Repository hinterlegen. Ein fehlendes Token lässt den Sync jetzt fehlschlagen statt einen erfolgreichen Profilwechsel vorzutäuschen. Der Erfolg erscheint erst mit API-Antwort und Profil-Report als Workflow-Artefakt.

Lokale Vorschau (kein Token, kein Versand, kein Report-Schreibzugriff):

    python3 scripts/mastodon_profile_sync.py --dry-run

## 3. Drei angeheftete Beiträge – fertig formuliert

Alle Vorlagen passen ins 500-Zeichen-Standardlimit. Nach redaktioneller Prüfung öffentlich veröffentlichen und über das Beitragsmenü anheften. Nicht alte Beiträge wortgleich duplizieren; vorhandene passende Pins gegebenenfalls aktualisieren. Tatsächliche Pin-Anzahl/Limits der Instanz kontrollieren.

### Pin 1: Vorstellung und Einladung

```text
Hallo Fediverse, ich bin Frank Hartung und betreibe FranksFinanzcheck.

Hier geht es um Fixkosten ohne Wechsel-Druck: Strom, Internet, Versicherungen und Budget. Erst rechnen, dann entscheiden.

Welche laufende Ausgabe möchtest du besser verstehen? Themenwünsche sind willkommen – bitte keine persönlichen Vertragsdaten posten.

#Vorstellung #Fixkosten #GeldSparen
```

### Pin 2: Unmittelbar nutzbarer Einstieg

```text
Dein Fixkosten-Check beginnt nicht beim Tarifwechsel.

1. Laufende Kosten sammeln.
2. Preis und Leistung vergleichen.
3. Kündigungsfenster notieren.
4. Regelmäßig nachprüfen.

Mein kostenloses Fixkosten-Cockpit hilft dir beim Sortieren. Eingaben werden nicht an den Server übertragen.

https://franksfinanzcheck.de/cockpit/

#Fixkosten #Haushaltsbudget
```

### Pin 3: Wie Leser die Inhalte einordnen können

```text
So kannst du FranksFinanzcheck einordnen:

Ich betreibe den Blog; die Ratgeber sind KI-unterstützt. Quellen und Prüfnachweise stehen am jeweiligen Artikel. Der Blog finanziert sich über gekennzeichnete Affiliate-Links (Werbung).

Keine individuelle Finanz-, Steuer- oder Rechtsberatung. Hinweise auf Fehler sind willkommen.

https://franksfinanzcheck.de/transparenz/

#Finanzen #Transparenz
```

## 4. Redaktion: Nutzen im Beitrag, nicht nur hinter dem Link

Für die ersten 30 Tage als **Test**, nicht als Plattformgesetz:

- Drei redaktionell ausgewählte eigene Beiträge pro Woche, davon mindestens zwei mit vollständigem Mini-Nutzen direkt im Text. Ein hilfreicher Beitrag darf ohne Link auskommen.
- Blog-Autopilot und manuelle Posts gemeinsam zählen. Bestehendes Limit: maximal zwei automatische Mastodon-Posts/Tag; manuelle Editor-Posts werden vom Autopilot nicht mitgezählt. Nicht zwei automatische Linkposts plus einen manuellen Beitrag stapeln. An einem manuellen Veröffentlichungstag den automatischen Kanal bei Bedarf pausieren; Plan nicht zusätzlich mit Backfills auffüllen.
- Bestehende Recycling-Sperre nicht für Reichweite umgehen. Kein identisches Wiederholen oder Löschen/Neuversenden für einen vermeintlichen Feed-Vorteil.
- Pro Beitrag zwei bis drei passende CamelCase-Hashtags als Starttest, keine Trendlisten. Beispiele nach Thema: `#StromSparen`, `#EnergieSparen`, `#Internet`, `#Haushaltsbudget`, `#Fixkosten`. Erst im Hashtag-Feed ansehen, ob aktuelle deutschsprachige Gespräche passen. Es gibt hier keine Live-Bestätigung der Größe dieser Communities.
- Höchstens eine echte Frage; keine „Boost, wenn du zustimmst“-Ketten und kein Kauf-/Followerdruck.
- Medien nur wenn sie etwas erklären. Informative Alt-Texte für Postbilder; Zahlen auch im Beitrag nennen. Keine Screenshots mit Kundennummern, Adresse, IBAN oder Zähler-ID.
- Werbung im konkreten Beitrag bei Bedarf klar kennzeichnen. Ein Bio-Affiliate-Hinweis ersetzt keine Prüfung des einzelnen Posts. Keine Rendite-, Spargarantien oder pauschalen Kündigungs-/Wechselempfehlungen.

### Sechs Startbeiträge – jeweils vollständig kopierbar

**A · Rechenhilfe ohne Link**

```text
Ein kleiner Monatsbetrag kann im Jahresbudget groß werden.

Rechenbeispiel, kein Sparversprechen: Ein ungenutztes Abo für 8 € pro Monat kostet 96 € im Jahr.

Schau zuerst nach Nutzung, Kündigungsfrist und Alternativen. Nicht alles streichen, was dir wirklich hilft.

Welche Ausgabe hast du zuletzt bewusst behalten – und warum?

#Haushaltsbudget #Fixkosten
```

**B · Strom: rechnen statt locken**

```text
Beim Stromtarif reicht der Arbeitspreis allein nicht.

Für dieselbe Jahresmenge gilt: Verbrauch in kWh × Preis je kWh + jährlicher Grundpreis. Einmalige Boni getrennt betrachten; Laufzeit und Preisgarantie mitprüfen.

Ein günstiges erstes Jahr ist nicht automatisch ein günstiger Dauervertrag.

https://franksfinanzcheck.de/pillar/strom-sparen/

#StromSparen #Fixkosten
```

**C · Internet: Diagnose vor Kauf**

```text
Langsames WLAN heißt nicht automatisch: teurerer Internetvertrag nötig.

Teste, wenn möglich, einmal per Netzwerkkabel direkt am Router. Vergleiche das Ergebnis mit WLAN nahe am Router und im Problemzimmer. So grenzt du Anschluss und Funknetz besser voneinander ab.

Wo hakt es bei dir: überall oder nur in einem Raum?

#Internet #WLAN
```

**D · Budget: ein kleiner Start**

```text
Du brauchst nicht sofort eine perfekte Budgettabelle.

Beginne mit drei laufenden Verträgen: Monatskosten, nächster Prüftermin, Kündigungsfenster. Das schafft einen konkreten Startpunkt, ohne den ganzen Haushalt an einem Abend neu zu planen.

Mein kostenloses Cockpit hilft beim Ordnen:
https://franksfinanzcheck.de/cockpit/

#Haushaltsbudget #Fixkosten
```

**E · Transparenz und Community-Nutzen**

```text
Ein guter Spartipp nennt auch seine Grenzen.

Bei Rechenbeispielen frage ich: Welche Annahmen gelten? Was ist einmalig? Welche Leistung geht verloren? Eine kleinere Rechnung hilft wenig, wenn der Vertrag danach nicht mehr passt.

Welche Angabe fehlt dir in Vergleichen am häufigsten?

#Verbraucherschutz #GeldSparen
```

**F · Wiedererkennbares Markenformat**

```text
Franks 4K-Check fürs Wochenende:

Kosten sehen: eine Rechnung öffnen.
Konditionen rechnen: Preis und Leistung prüfen.
Kündigungsfenster sichern: Termin notieren.
Kurs halten: nächsten Check einplanen.

Heute reicht ein Vertrag. Wechseln ist kein Muss.

https://franksfinanzcheck.de/cockpit/

#Fixkosten #GeldSparen
```

## 5. Kostenloser 30-Tage-Ablauf

| Zeitraum | Konkrete Arbeit | Erfolgskontrolle |
|---|---|---|
| Tage 1–3 | Profil übernehmen, Mobilansicht prüfen, bis zu drei Pins veröffentlichen. Ausgangszahlen notieren. | Profil-URL, Screenshots ohne private Daten, Pin-URLs, Follower-Basiswert |
| Tage 4–7 | Beiträge A–C auswählen. Zwei passende Hashtag-Feeds verfolgen; zehn thematisch passende Accounts lesen. Nur folgen, wenn du deren Inhalte wirklich lesen willst. | Welche Gespräche passen? Welche Antworten entstehen? Kein Follow-Quota. |
| Woche 2 | Beiträge D–F nutzen. Werktäglich 15–20 Minuten echte Gespräche; zwei bis drei hilfreiche Antworten, wenn passende Fragen vorliegen. Einen fremden guten Beitrag mit eigener Einordnung boosten. | Reaktionen nach festem Beobachtungsfenster protokollieren; Rückfragen beantworten. |
| Woche 3 | Ein Format aus bisherigen echten Fragen entwickeln. Einen komplementären Account individuell um einen gemeinsamen Check oder Erfahrungsaustausch bitten, ohne Seriennachricht. | Zusage/Absage, echte Diskussion, keine Pflicht zur Kooperation. |
| Woche 4 | Ein neues Rechenbeispiel, eine Checkliste, eine Leserfrage. Zwischenbilanz, gute Formate ausbauen, schwache überarbeiten. | Absolute Veränderungen und Rohzahlen, keine Sieger aus Nullwerten. |

### Tägliche Routine: maximal 20 Minuten

1. **5 Min:** Benachrichtigungen und Rückfragen lesen; nur selbst verantwortbare Aussagen beantworten. Unklarheiten kennzeichnen.
2. **10 Min:** In passenden Gesprächen helfen: Rechenschritt, sachlicher Hinweis, Quelle. Nicht jedes Mal den eigenen Blog verlinken.
3. **5 Min:** Themenidee und Messwerte notieren, nächste Veröffentlichung prüfen.

Muster für eine Antwort: „Für einen Vergleich brauchst du neben dem Monatsbetrag auch Laufzeit und enthaltene Leistung. Würde sich die Leistung beim günstigeren Angebot ändern?“ Nicht unaufgefordert Vertragsunterlagen oder persönliche Daten anfordern.

**Nicht delegieren an Bots:** automatisches Folgen/Entfolgen, Auto-Likes, Serien-DMs, ungeprüfte Finanzantworten, Kommentarspam. Keine gekauften Follower. Community-Regeln und Moderation respektieren.

## 6. Messplan – keine erfundenen Impressionen

Kostenloses Blatt/CSV oder Notiz genügt:

| Datum | Post-URL | Format | Thema | Uhrzeit Berlin | Alter beim Messen | Favoriten | Boosts | Antworten anderer | Followerstand | Websitebesuche* |
|---|---|---|---|---|---|---|---|---|---|---|
| Ausgangswert | – | – | – | – | – | – | – | – | live eintragen | unbekannt, falls nicht messbar |

\* Nur aus einer bereits zulässigen, tatsächlich verfügbaren Websiteanalyse. Keine neue Trackinglösung ohne Datenschutzprüfung installieren. Consent-bedingt unvollständige Zahlen als solche kennzeichnen. Fehlende Daten als **unbekannt**, nicht 0, eintragen.

- Jeden eigenen Beitrag nach etwa **48 Stunden** und noch einmal nach **7 Tagen** vergleichen. Ein fünf Minuten alter Post ist kein fairer Gegenpart zu einem siebentägigen.
- Primäre Signale: Boosts und Antworten anderer, wiederkehrende Gesprächspartner, Follower-Nettoänderung pro Woche. Followeränderung nicht einem einzelnen Post kausal zuschreiben.
- Favoriten sind Interesse, keine zugesicherte Verteilung an ein weiteres Publikum. Favoriten/Boosts/Antworten sind Engagement, **nicht gemessene Reichweite**.
- Keine „Engagementrate nach Impressionen“, wenn die Impressionen fehlen. Prozentwachstum bei Ausgangswert 0 nicht berechnen.
- Erst nach mindestens sechs vergleichbaren Beiträgen pro getesteter Variante eine vorsichtige Entscheidung treffen; kleine Stichproben bleiben ein Hinweis, kein statistischer Nachweis.
- Uhrzeiten zunächst zwischen 07:30 und 20:00 Berlin abwechseln; **keine** Behauptung, dies seien universelle Bestzeiten. Möglichst dasselbe Format vergleichen; bei zu wenigen Daten nur einen Test fortführen.
- Ziel nach 30 Tagen: verlässliche Umsetzung und erste echte Gespräche. Mehr Follower/Boosts sind erwünschte Ergebnisse, keine zugesicherte Zahl. Wenn es keine Reaktionen gibt: Relevanz, Sprache/Sichtbarkeit und Gesprächsbeteiligung prüfen, nicht die Frequenz verdoppeln.

Optionaler Linktest zum Cockpit: `https://franksfinanzcheck.de/cockpit/?utm_source=mastodon&utm_medium=social&utm_campaign=profil_30tage`. Nur verwenden, wenn UTM-Auswertung tatsächlich verfügbar und zulässig ist. Die Profilfelder bleiben saubere URLs; UTMs nicht als Link-Verifizierung voraussetzen.

## 7. Technische Qualitätssicherung

- Profiltexte, Zeichengrenzen und Vorschau ohne Netzwerk werden durch `scripts/tests/test_mastodon_profile_sync.py` geprüft.
- Die neun Beitragstexte werden auf 500 Zeichen, interne Zielseiten und fehlende `/go/`-Links geprüft.
- Null-Engagement-Neutralität, keine Schein-Sieger und unveränderte Cooldowns werden in `scripts/tests/test_social_perf_feedback.py` geprüft.
- Testaufruf: `python3 -m unittest scripts.tests.test_mastodon_profile_sync scripts.tests.test_social_perf_feedback scripts.tests.test_social_autopilot` (Umgebung mit PyYAML).
- Live-Profil, Live-Verifizierung und tatsächliche Reichweitenentwicklung bleiben separate Nachweise nach dem Rollout.

### Prüfergebnis dieser Sitzung

- **79 fokussierte Tests ausgeführt: 78 bestanden, 1 übersprungen** (Profil, Rückkanal, Autopilot, Social-Gate L6).
- `social_perf_feedback.py --selftest` und `social_studio.py --selftest`: bestanden.
- Profil-Vorschau: 25 Zeichen Anzeigename, 470 Zeichen Bio, vier Felder, vorhandene Bilder; kein Versand.
- Rückkanal aus vorhandenem Cache neu berechnet: elf gemessene Beiträge, alle Gewichte und Cooldown-Faktoren 1.0, `has_signal: false`, keine Top-/Flop-Liste. Historie protokolliert ausdrücklich keinen Sieger. Keine neuen Mastodon-Kennzahlen abgerufen.
- `git diff --check`: bestanden.
- Vorhandene `ResourceWarning`-Hinweise im Kalender-Selbsttest (nicht geschlossene YAML-Dateien) bleiben außerhalb dieser Änderung. Kein vollständiger Hugo-/Browser-Build: Hugo ist in dieser Arbeitsumgebung nicht installiert.
