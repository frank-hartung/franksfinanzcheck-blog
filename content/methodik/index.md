---
title: "So arbeiten wir: Redaktionsstandards, Recherche & Methodik"
description: "Transparenz bei FranksFinanzcheck: Internet-Recherche mit Agent Reach, Claude-Faktenprüfung, strenge Quell-Allowlist, Update-Rhythmus und unabhängige Empfehlungen."
draft: false
author: "Frank Hartung"
showToc: true
---

<p style="font-size:.9em; color:#555;">Stand: September 2026 · Verantwortlich: Frank Hartung (<a href="/ueber/">Über mich</a>) · Kontakt: kontakt@franksfinanzcheck.de</p>

Auf **FranksFinanzcheck** findest du Spar-Ratgeber und Tarifvergleiche, die du ohne Finanzstudium sofort im Alltag umsetzen kannst. Diese Seite dokumentiert transparent, **wie** unsere Inhalte entstehen, **womit** sie faktenbasiert belegt werden, **wie** wir moderne KI- und Recherche-Werkzeuge wie Agent Reach und Claude qualitätsgesichert einsetzen und **in welchen Abständen** alle Angaben überprüft werden.

## Der FranksFinanzcheck-Ansatz: Fixkosten-Kompass statt Tipp-Sammlung

FranksFinanzcheck ist kein allgemeiner Spartipps-Feed. Unser Produktkern ist der **Fixkosten-Kompass**: ein vierstufiger Prüfpfad, der alle Themen über dieselbe Frage verbindet – welche Entscheidung verbessert deinen Haushalt nach einer nachvollziehbaren Rechnung?

1. **Kosten sehen:** Wiederkehrende Beträge erfassen und nach Relevanz ordnen.
2. **Konditionen rechnen:** Preis, Leistung, Laufzeit, Bonus und Folgekosten gemeinsam bewerten.
3. **Kündigungsfenster sichern:** Vertragsdaten, Preisgarantien und persönliche Prüftermine sichtbar machen.
4. **Kurs halten:** Im festen Rhythmus neu prüfen und nur handeln, wenn die Rechnung dafür spricht.

Das kostenlose [Fixkosten-Cockpit](/cockpit/) setzt diese erste Orientierung direkt im Browser um. Es überträgt keine Eingaben an unseren Server und empfiehlt keinen Anbieter. Die einzelnen Ratgeber vertiefen anschließend genau den Schritt, der zu deinem Vertrag passt.

---

## 1. Recherche: Primärquellen und Multi-Kanal-Recherche

Jeder Ratgeber und jeder Blogartikel basiert auf verifizierten Daten. Wir stützen uns nicht auf Hörensagen, ungeprüfte Pressemitteilungen oder Werbeaussagen, sondern recherchieren an der Quelle:

1. **Amtliche Register und Bundesbehörden (Rang 1):** Bundesnetzagentur (BNetzA), Statistisches Bundesamt (Destatis), Bundesbank, BaFin, Bundesministerium der Finanzen und Bundesjustizministerium (gesetze-im-internet.de).
2. **Etablierte Verbraucherschutz- und Fachinstanzen (Rang 2):** Verbraucherzentralen der Bundesländer, Stiftung Warentest (test.de), BDEW (Bundesverband der Energie- und Wasserwirtschaft), GDV (Gesamtverband der Deutschen Versicherungswirtschaft), co2online und dena.
3. **Führende Fach- und Wirtschaftsredaktionen (Rang 3):** tagesschau, heise online, DER SPIEGEL.
4. **Eigene Praxistests:** Tarife buchen, Apps testen, Kündigungen und Wechsel selbst durchführen – echte Erfahrungswerte aus über 10 Jahren Praxis.

---

## 2. Automatisierte Recherche & Claude-Faktenprüfung

Um die fachliche Aktualität bei der Content-Erstellung und im gesamten Artikelbestand dauerhaft auf **Premium-Level einer Profi-Agentur** zu sichern, nutzen wir ein mehrstufiges, automatisiertes Qualitäts- und Recherche-System:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. Signalsammlung & Web-Recherche (Agent Reach)                        │
│    Automatisierte Erfassung von Preisänderungen, Gesetzen & Urteilen    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. Fachtechnische Prüfung & Synthese (Claude)                          │
│    Abgleich von Rechenbeispielen, Fristen & Konditionen                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. Anti-Halluzinations-Schutz (Strikte Allowlist)                      │
│    Quellen werden nur akzeptiert, wenn die Domain auf der Freigabe-    │
│    Liste liegt und der Link wörtlich im Recherche-Dossier steht        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 4. Menschliche Endabnahme (Frank Hartung)                              │
│    Freigabe, finale Redaktion und Veröffentlichung                     │
└────────────────────────────────────────────────────────────────────────┘
```

- **Recherche bei Content-Erstellung:** Jeder neue Artikel durchläuft vor Veröffentlichung eine gezielte Faktenrecherche mit Agent Reach und wird mit aktuellen Daten angereichert.
- **Doppelter Anti-Halluzinations-Filter:** Eine Quelle darf nur in einen Artikel übernommen werden, wenn ihre URL nachweisbar im Recherche-Dossier existiert **und** die Domain auf unserer kuratierten Allowlist liegt. Affiliate-Partnerseiten sind als Belege grundsätzlich ausgeschlossen.
- **GEO- und LLM-Zitierbarkeit:** Jeder belegte Artikel spiegelt seine Faktenbasis doppelt aus: als sichtbare Box **„Quellen & Faktenstand“** für Leser und als semantisches `schema.org/citation`-Markup für KI-Antwortmaschinen (ChatGPT Search, Perplexity, Google AI Overviews, Apple Intelligence).

---

## 3. Aktualität: Systematischer Revisions-Rhythmus

Preise, Zinsen und Gesetze ändern sich. Deshalb wird unser Bestand in festen, risikobasierten Intervallen nachrecherchiert und aktualisiert:

| Risikoklasse | Prüfintervall | Themenbereiche |
|---|---|---|
| **Saisonale Schwerpunkte** | alle 30 Tage | Heizung/Gas vor der Heizperiode, Kfz-Wechsel zum 30.11., Jahreswechsel |
| **YMYL (Your Money, Your Life)** | alle 45 Tage | Zinsen, Kredite, Versicherungsverträge, gesetzliche Kündigungsfristen |
| **Standard-Ratgeber** | alle 90 Tage | Budget-Methoden, Haushaltsgewohnheiten, Frugalismus-Tipps |

- **Sichtbare Datums-Transparenz:** Artikel mit inhaltlicher Überarbeitung tragen eine explizite Stand-Zeile. Ein rein technisches Deployment verändert das redaktionelle Datum niemals.
- **Korrektur-Kultur (WiWo-Standard):** Sollte sich trotz doppelter Prüfung ein Fehler einschleichen, wird er transparent korrigiert und im Artikel als gut sichtbarer Korrekturhinweis ausgewiesen.

---

## 4. Finanzierung: Unabhängigkeit & Affiliate-Transparenz

Damit FranksFinanzcheck dauerhaft kostenfrei und ohne Bezahlschranken für alle Leser zugänglich bleibt, finanzieren wir den redaktionellen Betrieb über Partnerschaften mit renommierten Vergleichsportalen (z. B. CHECK24, Tarifcheck über das Awin-Netzwerk):

- **Strikte Trennung von Redaktion und Provision:** Wir empfehlen ausschließlich Tarife, Verträge und Strategien, die rechnerisch überzeugen und die Frank Hartung selbst nutzt oder der eigenen Familie empfehlen würde.
- **Keine Mehrkosten für dich:** Wenn du über einen unserer Empfehlungslinks wechselst, zahlst du exakt denselben Preis wie direkt beim Anbieter.
- **Eindeutige Kennzeichnung:** Alle Partnerlinks sind transparent als Werbung gekennzeichnet und technisch über gesicherte `/go/`-Weiterleitungen mit `rel="sponsored nofollow"` standardisiert.
- **Vollständige Nutzbarkeit ohne Klick:** Jeder Ratgeber bietet alle Rechenwege, Kriterien und Tipps, um den Wechsel auch völlig eigenständig und ohne Klick auf einen Partnerlink durchzuführen.
- **Artikelgenaue Offenlegung (seit 28.09.2026):** Jeder Ratgeber nennt bereits **über** dem Text, wie viele Partnerlinks er enthält und zu welchen Partnern sie führen – Artikel ohne Partnerlinks sind sichtbar als werbefrei gekennzeichnet. Welche Partner es gibt, wie die Provision funktioniert und was sie nicht beeinflusst, steht vollständig unter [Transparenz & Werbung](/transparenz/).

---

## 5. Was FranksFinanzcheck bewusst nicht ist

- **Keine individuelle Rechts- oder Steuerberatung:** Unsere Leitfäden bieten praxisnahe Orientierung und sorgfältig recherchierte Allgemein-Informationen, ersetzen jedoch keine persönliche Rechts- oder Finanzberatung.
- **Keine Schein-Rankings:** Wir verkaufen keine redaktionellen Testsiege an den Meistbietenden.
- **Kein Tracking-Missbrauch:** Wir respektieren deine Privatsphäre. Die Website nutzt keine zustimmungspflichtigen Werbetracker von Drittanbietern.

---

## 6. Kontakt für Leser und Fachinstanzen

Du hast eine inhaltliche Anmerkung, eine veraltete Angabe entdeckt oder möchtest eine methodische Frage stellen? Schreib uns direkt an:

📧 **E-Mail:** kontakt@franksfinanzcheck.de<br>
👤 **Verantwortlicher Autor:** Frank Hartung · [Über mich & Werdegang](/ueber/)<br>
📜 **Rechtliches:** [Impressum](/impressum/) · [Datenschutzerklärung](/datenschutz/)
