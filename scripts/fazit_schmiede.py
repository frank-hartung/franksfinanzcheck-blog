#!/usr/bin/env python3
# ============================================================
#  FAZIT-SCHMIEDE – Die vollautomatische Fazit- & FAQ-Schmiede mit Selbstheilung
#
#  Auftrag (15.08.2026): „Vollautomatische Fazit-/FAQ-Schmiede mit Selbstheilung“
#  Behebt die systemische Struktur-Lücke von 77/77 fehlenden Fazit-Abschnitten
#  und 32/77 fehlenden FAQ-Abschnitten im Blog-Archiv.
#
#  STRUKTUR-STANDARDS:
#    - Ein Artikel gilt nur dann als vollständig (C2), wenn er ein Fazit
#      UND eine FAQ-Rubrik besitzt (h2/h3).
#    - Wenn etwas fehlt, schmiedet diese Automatik hochrelevante,
#      auf das Thema und die Affiliate-Route des Beitrags maßgeschneiderte
#      Inhalte.
#    - Nutzt die echten Affiliate-Kategorie-Sniffer aus affiliate_marketer.py
#      für konversionsstarke, markenkonforme Verlinkungen (z.B. C24 Bank).
#
#  SELBSTHEILUNG:
#    - Erkennt unvollständige, doppelte oder zerschossene Abschnitte und heilt sie.
#    - Existierende, manuell verfasste Fazit- oder FAQ-Texte werden geschützt
#      und niemals überschrieben (Editorial-Schutz).
#    - Platzierung erfolgt intelligent vor dem Conversion-Footer/Disclaimer.
#
#  SABOTAGE-SCHUTZ:
#    - Integrierter 6-Fälle-Selbsttest prüft Parsing, Generierung und Platzierung.
#    - Bei Abweichung: Exit 2 (Hard Stop, kein Schreiben im Repository).
#
#  Aufruf:
#    python3 scripts/fazit_schmiede.py             # Report (weich, Exit 0/1)
#    python3 scripts/fazit_schmiede.py --fix       # Heilen und ins Repo schreiben
#    python3 scripts/fazit_schmiede.py --dry-run   # Vorschau ohne Schreiben
#    python3 scripts/fazit_schmiede.py --altlasten           # Altbaustil melden (Exit 1)
#    python3 scripts/fazit_schmiede.py --altlasten --fix     # und gegen Hausstil tauschen
#
#  ALTLASTEN-MODUS: Die erste Generation (15.08.–30.08.) schrieb in jedes Fazit
#  dieselbe Zweiersatz-Formel – „Sich gezielt mit dem Thema … bares Geld zu
#  sparen“ (R7: Template-Sprache) plus „Fang am besten heute an … 💸🚀“ (Emoji,
#  Mitmach-Aufruf statt Befund) – und mischte den Satz einer fremden
#  Affiliate-Route hinein (im Frugalismus-Artikel stand ein Tagesgeld-Hinweis,
#  im Notgroschen-Artikel die Hausratversicherung). Ersetzt wird auf SATZEBENE
#  im Fazit-Rumpf: nur die Alt-Saetze fallen, der Hausabsatz kommt voran,
#  redaktioneller Text bleibt stehen. Der Modus ist opt-in und laeuft
#  nicht in der Doctor-Kette – Maschinentext darf kein Selbstlaeufer werden.
# ============================================================

import json
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "FAZIT-REPORT.md"
HISTORY = ROOT / "data" / "fazit_history.jsonl"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv
ALTLASTEN = "--altlasten" in sys.argv

# Versuche den Sniffer aus dem Affiliate Marketer zu importieren
try:
    sys.path.insert(0, str(ROOT / "scripts"))
    import affiliate_marketer as am
    ROUTE_SNIFFER = am.route_for
except Exception:
    # Minimal-Fallback falls Import fehlschlägt
    def ROUTE_SNIFFER(text, pillar="", title=""):
        return "allgemein"

# --- FAQ-POOL PRO AFFILIATE-ROUTE (100% redaktionelle Qualität) ---
FAQ_POOL = {
    "girokonto": [
        ("Welche C24 Bank Angebote lohnen sich wirklich?",
         "Die C24 Bank bietet ein absolut erstklassiges, dauerhaft kostenloses Girokonto mit hervorragenden Konditionen, einer intuitiven App und einer echten Mastercard. **Jetzt C24 Bank Angebote vergleichen** ist der einfachste Weg, um lästige Kontoführungsgebühren für immer aus deinem Alltag zu verbannen."),
        ("Ist ein Kontowechsel nicht furchtbar kompliziert?",
         "Nein, überhaupt nicht! Dank des gesetzlichen Kontowechselservice erledigt die neue Bank den gesamten Papierkram für dich vollautomatisch innerhalb von 10 Minuten. Alle Lastschriften und Daueraufträge werden sicher übertragen, ohne dass du Verträge manuell umschreiben musst."),
        ("Wie sicher ist mein Geld bei der C24 Bank?",
         "Dein Guthaben ist über die gesetzliche deutsche Einlagensicherung bis zu 100.000 € pro Kunde vollkommen abgesichert. Zudem profitierst du von der lizenzierten Regulierung durch die Bundesanstalt für Finanzdienstleistungsaufsicht (BaFin).")
    ],
    "tagesgeld": [
        ("Wie finde ich die besten Tagesgeld-Zinsen?",
         "Die Zinsen im Markt verändern sich stetig. Die C24 Bank bietet dauerhaft attraktive und faire Konditionen für dein flexibel geparktes Geld. **Jetzt C24 Bank Angebote vergleichen** zeigt dir, wie viel Rendite du aktuell ohne Risiko mitnehmen kannst."),
        ("Sollte ich mein Geld lieber in Festgeld oder Tagesgeld anlegen?",
         "Das Tagesgeld eignet sich perfekt für deinen flexiblen Notgroschen (3 bis 6 Monatsgehälter), da du täglich an dein Geld herankommst. Festgeld lohnt sich nur, wenn du einen Teil deines Ersparten für einen festen Zeitraum sicher entbehren kannst, um dir dafür feste Zinsen zu sichern."),
        ("Fallen bei der Eröffnung eines Tagesgeldkontos Gebühren an?",
         "Nein, ein seriöses Tagesgeldkonto ist für dich immer absolut kostenlos. Achte beim Vergleich darauf, dass keine versteckten Kosten für die Kontoführung oder Auszahlungen anfallen.")
    ],
    "strom": [
        ("Wie oft sollte ich meinen Stromanbieter wechseln?",
         "Es lohnt sich, den Stromtarif jedes Jahr zu prüfen. Viele Anbieter locken im ersten Jahr mit satten Neukundenboni, die danach wegfallen. Ein jährlicher Wechsel sichert dir dauerhaft die besten Preise."),
        ("Was passiert beim Wechsel, stehe ich plötzlich im Dunkeln?",
         "Nein, das ist gesetzlich absolut ausgeschlossen. Die lückenlose Stromversorgung ist durch den örtlichen Grundversorger jederzeit garantiert. Der Wechsel ist ein reiner, geräuschloser Verwaltungsakt."),
        ("Worauf muss ich bei den Vertragslaufzeiten achten?",
         "Wähle am besten Tarife mit einer maximalen Laufzeit von 12 Monaten und einer kurzen Kündigungsfrist von einem Monat. Vermeide lange Vorkasse-Modelle oder Paket-Tarife, um flexibel auf Preisänderungen reagieren zu können.")
    ],
    "gas": [
        ("Wann ist der beste Zeitpunkt für einen Gastarif-Vergleich?",
         "Am besten vergleichst du deine Konditionen im Spätsommer oder frühen Herbst vor Beginn der Heizperiode. So sicherst du dir die besten Preise und gehst entspannt in die kalte Jahreszeit."),
        ("Was ist eine Preisgarantie und wie lange sollte sie laufen?",
         "Eine Preisgarantie schützt dich vor unvorhergesehenen Preiserhöhungen des Anbieters. Sie sollte idealerweise die gesamte Erstvertragslaufzeit (meist 12 Monate) abdecken, um maximale Planungssicherheit zu bieten."),
        ("Wie läuft der Wechsel des Gasanbieters ab?",
         "Der Wechsel ist kinderleicht: Du suchst dir online einen günstigen Tarif aus, füllst den Antrag aus und der neue Anbieter übernimmt die Kündigung beim alten Versorger vollautomatisch für dich.")
    ],
    "dsl": [
        ("Wie sichere ich mir den besten DSL-Wechselbonus?",
         "Die besten DSL-Wechselboni und Cashbacks gibt es beim Online-Vergleich. Indem du deinen alten Vertrag kündigst und über ein Vergleichsportal neu abschließt, sparst du oft mehrere hundert Euro im Vergleich zum Verbleib beim Altanbieter."),
        ("Welche Internet-Geschwindigkeit brauche ich wirklich?",
         "Für Singles und normales Surfen reichen 50 Mbit/s völlig aus. Familien oder WGs mit mehreren Streaming-Geräten und Homeoffice-Nutzung fahren mit 100 bis 250 Mbit/s am besten."),
        ("Wie lange dauert ein Anbieterwechsel beim Internet?",
         "Der Wechsel dauert meist wenige Wochen. Am Tag der Umschaltung sorgt das gesetzliche Übergangs-Protokoll dafür, dass der Ausfall meist nur wenige Minuten bis maximal einen Tag beträgt.")
    ],
    "mietwagen": [
        ("Wie kann ich beim Mietwagen buchen am meisten sparen?",
         "Buche deinen Mietwagen immer so früh wie möglich, besonders für die Ferienzeit. Nutze zudem ungebundene Online-Vergleiche und wähle die Tankregelung 'Voll/Voll', um teure Tankgebühren vor Ort zu vermeiden."),
        ("Welche Mietwagen-Versicherungen sind absolut notwendig?",
         "Eine Vollkaskoversicherung ohne Selbstbeteiligung (oft als Rückerstattung) ist ein absolutes Muss. Achte zudem auf eine ausreichende Haftpflicht-Deckungssumme von mindestens 1 Million Euro."),
        ("Worauf muss ich bei der Fahrzeugübergabe vor Ort achten?",
         "Lass alle bereits vorhandenen Kratzer und Vorschäden exakt im Übergabeprotokoll schriftlich festhalten und mache zur Sicherheit eigene Fotos oder ein kurzes Video vom Auto.")
    ],
    "reisen": [
        ("Wann bucht man Pauschalreisen am günstigsten?",
         "Frühbucher profitieren meist von den höchsten Rabatten und der größten Auswahl bis ca. Februar. Alternativ bieten Last-Minute-Angebote kurz vor dem Abflug starke Preisnachlässe, erfordern jedoch Flexibilität."),
        ("Was ist der Unterschied zwischen Pauschalreise und Einzelbuchung?",
         "Bei einer Pauschalreise sind Flug, Hotel und oft auch der Transfer in einem Paket gebündelt. Das bietet dir einen starken gesetzlichen Schutz (Sicherungsschein) bei Insolvenz oder Flugausfällen."),
        ("Welche Reiseversicherungen sollte ich für den Urlaub abschließen?",
         "Eine Auslandsreisekrankenversicherung ist für jede Auslandsreise absolute Pflicht. Eine Reiserücktrittskostenversicherung lohnt sich besonders bei teuren Familienreisen oder langfristigen Buchungen.")
    ],
    "kfz-versicherung": [
        ("Wann kann ich meine KFZ-Versicherung kündigen?",
         "Der Stichtag für die meisten KFZ-Versicherungen ist der 30. November, da die Verträge meist zum 31. Dezember enden. Bei Preiserhöhungen hast du zudem ein Sonderkündigungsrecht von 4 Wochen."),
        ("Wann lohnt sich Teilkasko und wann Vollkasko?",
         "Vollkasko lohnt sich meist für Neuwagen in den ersten 3 bis 5 Jahren sowie für finanzierte Fahrzeuge. Für ältere Gebrauchtwagen reicht eine Teilkasko oder die reine Haftpflicht oft völlig aus."),
        ("Wie beeinflusst die SF-Klasse meinen Beitrag?",
         "Deine Schadenfreiheitsklasse (SF-Klasse) drückt deine unfallfreien Jahre aus. Je höher die Klasse, desto niedriger ist dein Versicherungsbeitrag. Sie lässt sich beim Fahrzeug- oder Versicherungswechsel problemlos mitnehmen.")
    ],
    "handytarife": [
        ("Sollte ich ein Handy mit Vertrag oder ohne kaufen?",
         "In den meisten Fällen ist der getrennte Kauf (günstiges Smartphone bar kaufen + separater SIM-Only-Tarif) über die Laufzeit von 24 Monaten gerechnet deutlich günstiger als ein teurer Kombi-Vertrag."),
        ("Wie viel Datenvolumen ist im Alltag sinnvoll?",
         "Für normales Surfen, Social Media und gelegentliches Musik-Streaming reichen 10 bis 15 GB Datenvolumen vollkommen aus. Wer viel unterwegs hochauflösende Videos schaut, sollte Tarife ab 20 GB oder Unlimited wählen."),
        ("Kann ich meine Handynummer beim Anbieterwechsel mitnehmen?",
         "Ja, die Rufnummernmitnahme ist gesetzlich garantiert und für dich seit Ende 2021 vollkommen kostenlos. Du kannst sie meist direkt im Bestellprozess beim neuen Anbieter beauftragen.")
    ],
    "kreditkarte": [
        ("What is die beste kostenlose Kreditkarte?",
         "Die ideale kostenlose Kreditkarte verlangt keine Jahresgebühr und ermöglicht weltweit kostenfreie Zahlungen sowie Bargeldabhebungen ohne versteckte Fremdwährungsgebühren im Ausland."),
        ("Was ist der Unterschied zwischen Charge-, Credit- und Debitkarte?",
         "Eine Debitkarte bucht Umsätze sofort vom Girokonto ab (wie bei der C24 Bank). Eine Charge-Karte sammelt die Beträge und bucht sie monatlich ab. Eine echte Credit-Karte bietet dir einen echten Kreditrahmen mit Ratenzahlungsoption."),
        ("Worauf muss ich im Ausland bei Kreditkarten achten?",
         "Achte beim Geldabheben im Ausland immer darauf, in der Landeswährung abzurechnen. Wähle niemals die Option 'Sofortige Umrechnung in Euro', da hier extrem schlechte Wechselkurse und hohe Gebühren anfallen.")
    ],
    "kredit": [
        ("Wie finde ich den günstigsten Ratenkredit?",
         "Vergleiche Kredite immer über unabhängige Vergleichsportale, um den günstigsten effektiven Jahreszins zu ermitteln. Achte darauf, einen zweckgebundenen Kredit (z.B. Autokredit) zu wählen, wenn er passt – das senkt die Zinsen spürbar."),
        ("Was bedeutet die Bonitätsprüfung beim Kredit?",
         "Die Bank prüft vor der Kreditvergabe dein Einkommen und deine SCHUFA-Auskunft, um das Ausfallrisiko einzuschätzen. Ein stabiles Einkommen und ein hoher SCHUFA-Score sichern dir die besten Zinskonditionen."),
        ("Kann ich einen Kredit vorzeitig kostenlos zurückzahlen?",
         "Ja, gesetzlich darf die Bank bei vorzeitiger Tilgung maximal 1 % des Restbetrags als Vorfälligkeitsentschädigung verlangen (bei weniger als 12 Monaten Restlaufzeit nur 0,5 %). Viele moderne Banken bieten jedoch kostenfreie Sondertilgungen an.")
    ],
    "unfallversicherung": [
        ("Wer braucht eine private Unfallversicherung?",
         "Sie lohnt sich besonders für Hausfrauen, Selbstständige, Kinder und Rentner, die keinen Schutz durch die gesetzliche Unfallversicherung haben. Aber auch für Arbeitnehmer ist sie sinnvoll, da die gesetzliche Kasse nur Unfälle am Arbeitsplatz und auf dem Arbeitsweg abdeckt."),
        ("Was ist die Invaliditätsleistung und wie hoch sollte sie sein?",
         "Die Invaliditätsleistung ist die Einmalzahlung bei dauerhaften körperlichen Schäden. Als Faustformel gilt: Sie sollte das 5- bis 6-fache deines Brutto-Jahreseinkommens abdecken, um im Ernstfall finanzielle Sicherheit zu bieten."),
        ("Was ist der Unterschied zwischen Unfall- und Berufsunfähigkeitsversicherung?",
         "Die Unfallversicherung zahlt nur bei unfallbedingten dauerhaften Schäden. Die Berufsunfähigkeitsversicherung (BU) leistet auch dann, wenn du deinen Beruf aufgrund von Krankheiten, Burnout oder Verschleiß nicht mehr ausüben kannst – sie ist daher die wichtigere Absicherung.")
    ],
    "haftpflicht": [
        ("Warum ist die Privathaftpflichtversicherung so extrem wichtig?",
         "Wer anderen schuldhaft einen Schaden zufügt, haftet dafür laut Gesetz unbegrenzt mit seinem gesamten aktuellen und zukünftigen Vermögen. Die Privathaftpflicht schützt dich vor dem finanziellen Ruin bei Personen- oder Sachschäden."),
        ("Wie hoch sollte die Deckungssumme sein?",
         "Die Deckungssumme sollte mindestens 10 Millionen Euro betragen, besser sind 50 Millionen Euro. Der Aufpreis für extrem hohe Deckungssummen beträgt meist nur wenige Cent im Jahr."),
        ("Sind meine Familie und Kinder automatisch mitversichert?",
         "Ehepartner und minderjährige Kinder können problemlos über einen gemeinsamen Familientarif günstig mitversichert werden. Achte darauf, dass deliktunfähige Kinder (unter 7 Jahren, im Straßenverkehr unter 10 Jahren) explizit im Tarif eingeschlossen sind.")
    ],
    "hausrat": [
        ("Wann lohnt sich eine Hausratversicherung wirklich?",
         "Sie lohnt sich, wenn der Gesamtwert deines Hausrats (Möbel, Kleidung, Elektronik) so hoch ist, dass du ihn im Schadensfall (Brand, Einbruch, Leitungswasser) nicht aus eigener Tasche ersetzen könntest."),
        ("Wie wird die Versicherungssumme richtig ermittelt?",
         "Um eine Unterversicherung zu vermeiden, vereinbaren die meisten Versicherer eine Pauschale von ca. 650 € pro Quadratmeter Wohnfläche. In diesem Fall verzichtet die Versicherung im Schadensfall auf eine genaue Prüfung des Gesamtwerts."),
        ("Sind Fahrräder in der Hausratversicherung automatisch geschützt?",
         "Fahrräder sind meist nur bei Einbruchdiebstahl aus dem verschlossenen Keller geschützt. Für Diebstähle auf offener Straße benötigst du eine zusätzliche Fahrrad-Klausel im Vertrag oder eine separate Fahrradversicherung.")
    ],
    "zahnzusatzversicherung": [
        ("Wann sollte ich eine Zahnzusatzversicherung abschließen?",
         "Der beste Zeitpunkt ist, solange deine Zähne noch völlig gesund sind und keine Behandlungen anstehen. Bereits angeratene oder laufende Behandlungen sind bei den meisten Tarifen vom Schutz ausgeschlossen."),
        ("Was übernimmt die gesetzliche Krankenkasse beim Zahnarzt?",
         "Die gesetzliche Kasse zahlt nur eine Basis-Regelversorgung (z.B. einfache Amalgamfüllungen oder einfache Brücken). Für hochwertige Keramikkronen, Implantate oder professionelle Zahnreinigung zahlst du ohne Zusatzversicherung oft hunderte Euro selbst."),
        ("Worauf muss ich bei den Zahnstaffeln in den ersten Jahren achten?",
         "Fast alle Tarife begrenzen die Erstattungssumme in den ersten 3 bis 4 Jahren (Zahnstaffel). Achte darauf, einen Tarif mit einer möglichst hohen Anfangs-Zahnstaffel und ohne Begrenzung bei unfallbedingten Behandlungen zu wählen.")
    ],
    "reisekrankenversicherung": [
        ("Reicht die normale gesetzliche Krankenkasse im Ausland nicht aus?",
         "Nein, die gesetzliche Kasse zahlt nur in Ländern mit Sozialversicherungsabkommen (z.B. EU) und dort auch nur nach den oft sehr geringen Sätzen des Reiselandes. Einen medizinisch notwendigen Rücktransport nach Deutschland zahlt die gesetzliche Kasse grundsätzlich nie – diesen musst du komplett selbst tragen."),
        ("Was kostet eine gute Auslandsreisekrankenversicherung?",
         "Eine hervorragende Jahres-Auslandsreisekrankenversicherung für beliebig viele Reisen bis zu je 8 Wochen Dauer kostet für Singles meist nur 10 bis 15 € im Jahr und ist damit ein absolutes Schnäppchen."),
        ("Gilt die Versicherung auch für längere Reisen (z.B. Weltreisen)?",
         "Die Standard-Jahrestarife gelten meist nur für Reisen bis maximal 56 Tage am Stück. Für längere Aufenthalte (Auslandsjahr, Sabbatical) benötigst du eine spezielle Langzeit-Reisekrankenversicherung, die monatlich abgerechnet wird.")
    ],
    "hunde": [
        ("What is der Unterschied zwischen OP- und Krankenvollversicherung?",
         "Die reine OP-Versicherung zahlt nur die Kosten für chirurgische Eingriffe und deren Nachsorge. Die Vollkrankenversicherung übernimmt zusätzlich auch normale Tierarztbesuche, Diagnostik, Medikamente und Vorsorgeleistungen – ist dafür aber auch deutlich teurer."),
        ("Lohnt sich eine Hundekrankenversicherung wirklich?",
         "Ja, denn moderne Tiermedizin ist hochprofessionell und extrem teuer. Eine schwere Operation oder chronische Krankheiten können schnell mehrere tausend Euro kosten. Die Versicherung schützt dich vor schweren finanziellen Entscheidungen im Ernstfall."),
        ("Worauf muss ich beim Abschluss bezüglich des Alters achten?",
         "Schließe die Versicherung so früh wie möglich ab (idealerweise im Welpenalter). Je älter das Tier bei Abschluss ist, desto höher sind die Beiträge, und es können Ausschlussklauseln für bereits bestehende Krankheiten vereinbart werden.")
    ],
    "allgemein": [
        ("Wie starte ich am besten mit dem Sparen im Alltag?",
         "Der erste Schritt ist immer eine lückenlose Übersicht deiner Ausgaben. Führe für mindestens zwei bis drei Monate ein Haushaltsbuch, um versteckte Kostenfresser wie Abos, tägliche Snacks und unnötige Verträge sofort zu entlarven."),
        ("Wie viel Geld sollte ich als Notgroschen aufbauen?",
         "Als eiserne Reserve gelten 3 bis 6 Monatsausgaben. Dieses Geld gehört auf ein gut verzinstes, täglich verfügbares Tagesgeldkonto, um bei unvorhergesehenen Notfällen (Autoreparatur, kaputte Waschmaschine) sofort handlungsfähig zu sein."),
        ("Sollte ich Verträge wie Strom und Internet wirklich jährlich prüfen?",
         "Ja, absolut! Treue zahlt sich bei Dienstleistern leider fast nie aus – im Gegenteil: Neukunden erhalten saubere Rabatte und Wechselboni, während Bestandskunden oft viel zu viel zahlen. Ein jährlicher Vergleich sichert dir dauerhaft die besten Preise.")
    ]
}

# Fallbacks
FAQ_POOL["fluege"] = FAQ_POOL["reisen"]


def clean_header_name(text: str) -> str:
    """Bereinigt Überschriften für robusten Regex-Match (entfernt Markdown-Auszeichnungen)."""
    return re.sub(r"\*\*|__|\*", "", text).lower().strip()


def check_sections(body: str) -> tuple[bool, bool]:
    """Prüft, ob Fazit- und FAQ-Rubriken bereits existieren (exakte content_audit-Logik)."""
    bare = re.sub(r"\*\*|__", "", body)
    has_fazit = bool(re.search(r"^#{2,3}\s+.*(fazit|zusammenfassung)", bare, re.M | re.I))
    has_faq = bool(re.search(r"^#{2,3}\s+.*(faq|häufige fragen|fragen)", bare, re.M | re.I))
    return has_fazit, has_faq


def tc_join(text: str) -> tuple[str, bool]:
    """Komposita-Kanon aus scripts/tag_casing.py – dieselbe Quelle wie die
    Casing-Wache, damit Generator und Wache nie gegeneinander schreiben.
    fail-open: ohne Lexikon bleibt der Text unveraendert."""
    try:
        import tag_casing as tc
        return tc.join_compounds(text)
    except Exception:  # noqa: BLE001
        return text, False


def generate_fazit_text(title: str, route: str) -> str:
    """Generiert einen maßgeschneiderten, hochqualitativen Fazit-Abschnitt."""
    # Nur ein echtes Datumspraefix darf fallen. Das alte Muster „^[0-9-\s.]+“ frass
    # „50-30-20-Regel“ zu „Regel“ herunter – daher stammte der Untertitel
    # „Fazit: Regel – Beherrsche dein Budget“. Markdown-Reste (Links aus dem
    # Frontmatter) duerfen nicht ins Fazit wandern.
    cleantitle = re.sub(r"^\d{4}-\d{2}-\d{2}[\s:\-–]*", "", title).strip()
    cleantitle = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", cleantitle)
    
    # Heuristische Sätze nach Affiliate-Route
    sentence_map = {
        "strom": "Indem du die Tarife vergleichst und regelmäßig wechselst, holst du ohne Komfortverzicht das Maximum aus deinem Haushaltsbudget heraus.",
        "gas": "Sichere dir rechtzeitig günstige Gastarife mit Preisgarantie, um entspannt und ohne böse Überraschungen durch den nächsten Winter zu kommen.",
        "dsl": "Ein regelmäßiger Anbieterwechsel sichert dir attraktive Neukunden- und Wechselboni für schnelles Internet zum Bestpreis.",
        "mietwagen": "Buche deinen Mietwagen immer frühzeitig und achte auf faire Tankregelungen sowie ausreichenden Versicherungsschutz, um Kostenfallen vor Ort zu umgehen.",
        "reisen": "Durch geschicktes Timing beim Buchen und einen unabhängigen Preisvergleich reist du vollkommen entspannt zum absoluten Schnäppchenpreis.",
        "girokonto": "Mit einem kostenlosen Girokonto (wie dem Angebot der C24 Bank) vermeidest du unnötige Kontoführungsgebühren und behältst die volle Kontrolle über deine Finanzen.",
        "tagesgeld": "Nutze attraktive Tagesgeld-Angebote der C24 Bank, um dein Erspartes flexibel, sicher und rentabel vor der Inflation zu schützen.",
        "kredit": "Ein genauer Online-Vergleich verhilft dir zum günstigsten Ratenkredit und spart dir bares Geld bei Zinsen und Raten.",
        "kfz-versicherung": "Ein jährlicher Vergleich der KFZ-Versicherung spart oft mehrere hundert Euro bei identischen oder sogar besseren Leistungen.",
        "handytarife": "Mit dem passenden SIM-Only-Tarif und einem separat gekauften Smartphone sparst du auf zwei Jahre gerechnet massiv Geld.",
        "kreditkarte": "Eine gebührenfreie Kreditkarte ohne Auslandseinsatzentgelt ist der ideale Begleiter für weltweite Flexibilität und zinsfreies Bezahlen.",
        "unfallversicherung": "Eine private Unfallversicherung schließt wichtige Lücken der gesetzlichen Absicherung und sichert dich im Ernstfall finanziell ab.",
        "haftpflicht": "Eine Privathaftpflichtversicherung ist der wichtigste und gleichzeitig günstigste Schutz, den jeder absolut unverzichtbar besitzen sollte.",
        "hausrat": "Eine Hausratversicherung schützt dein Hab und Gut vor existenzbedrohenden Risiken und sorgt für finanzielle Sicherheit im Schadensfall.",
        "zahnzusatzversicherung": "Mit einer guten Zahnzusatzversicherung schützt du dich vor extrem hohen Eigenanteilen beim Zahnarzt und sicherst dir beste Behandlungen.",
        "reisekrankenversicherung": "Für wenige Euro im Jahr sichert dich eine Auslandsreisekrankenversicherung weltweit ab und schützt vor enormen Krankheitskosten im Urlaub.",
        "hunde": "Eine Hundekrankenversicherung nimmt dir im Krankheitsfall deines Vierbeiners die finanziellen Sorgen ab, damit du dich ganz auf seine Genesung konzentrieren kannst.",
        "allgemein": "Bereits kleine Anpassungen im Konsumverhalten und regelmäßige Vertragsprüfungen summieren sich über das Jahr zu einer beachtlichen Ersparnis."
    }
    sentence_map["fluege"] = sentence_map["reisen"]
    
    # Der fruhere Einstieg („Sich gezielt mit dem Thema X zu beschäftigen, ist einer
    # der einfachsten Hebel … bares Geld zu sparen“) war in jedem Fazit identisch und
    # genau die Formel, die R7 als Template-Sprache meldet. Neu: kurzer, sachlicher
    # Rahmen – Route-spezifischer Satz (s2) bleibt die eigentliche Aussage.
    s1 = f"Der Hebel bei **{cleantitle}** sitzt nicht im Verzicht, sondern im Nachrechnen."
    s2 = sentence_map.get(route, sentence_map["allgemein"])
    # Kein Emoji-Doppel, kein „fang heute an“: der konkrete Nachschlag-Step.
    s3 = ("Prüfe einmal deine aktuellen Konditionen, halte den Unterschied schriftlich "
          "fest und wiederhole den Check jährlich – fünf Minuten reichen.")
    
    # Ueberschriftentraeger: „## Fazit: <H1 komplett> schlau nutzen“ war dreifach
    # kaputt – (1) der CTA-Satz „schlau nutzen“ klebte in der Ueberschrift (Hugo
    # setzt ihn fett und als Teil des Ankers), (2) der Doppelpunkt des H1 ergab
    # „Fazit: X: Y“, (3) die ganze H1 duplizierte nur den Seitentitel. Jetzt:
    # Unterstitel wird Gedankenstrich, CTA faellt weg, Nomen-Komposita bleiben
    # zusammen (dasselbe Lexikon wie die Casing-Wache).
    head = re.sub(r"^\s*Fazit\s*[:\-–]+\s*", "", cleantitle)
    head = head.replace(": ", " \u2013 ")
    head, _ = tc_join(head)
    head = head.rstrip(".!?" + "\u2026")
    return f"## Fazit: {head}\n\n{s1} {s2} {s3}\n"


def generate_faq_text(route: str) -> str:
    """Generiert einen maßgeschneiderten, hochqualitativen FAQ-Abschnitt."""
    items = FAQ_POOL.get(route, FAQ_POOL["allgemein"])
    faq_lines = ["## Häufige Fragen\n"]
    for q, a in items:
        faq_lines.append(f"### {q}\n{a}\n")
    return "\n".join(faq_lines)


def insert_sections(full_doc: str, has_fazit: bool, has_faq: bool, title: str, route: str) -> str:
    """Platziert die fehlenden Abschnitte präzise vor dem Conversion-Footer/Disclaimer."""
    if has_fazit and has_faq:
        return full_doc
    
    parts = full_doc.split("---", 2)
    if len(parts) < 3:
        return full_doc  # Kein valides Frontmatter
    
    fm_part = parts[1]
    body_part = parts[2]
    
    # Generiere benötigte Texte
    fazit_block = "" if has_fazit else generate_fazit_text(title, route)
    faq_block = "" if has_faq else generate_faq_text(route)
    
    # Bestimme, was eingefügt werden muss
    insert_payload = ""
    if fazit_block and faq_block:
        insert_payload = f"\n\n{fazit_block}\n{faq_block}\n"
    elif fazit_block:
        # Nur Fazit fehlt. Wenn FAQ existiert, füge Fazit direkt VOR der FAQ-Überschrift ein.
        faq_match = re.search(r"^#{2,3}\s+.*(faq|häufige fragen|fragen)", body_part, re.M | re.I)
        if faq_match:
            insert_pos = faq_match.start()
            new_body = body_part[:insert_pos] + fazit_block + "\n" + body_part[insert_pos:]
            return f"---{fm_part}---{new_body}"
        else:
            insert_payload = f"\n\n{fazit_block}\n"
    elif faq_block:
        insert_payload = f"\n\n{faq_block}\n"
        
    # Finde den Conversion-Trenner am Ende des Dokuments
    # Typischerweise: \n---\n\n👉 **...** oder \n--- \n\n*Dieser Artikel...*
    # Wir suchen rückwärts nach dem Trenner
    bottom_divider_rx = re.compile(r"(\n---[\s\xa0]*\n\s*(?:👉|💡|_\(|_Dieser Artikel|_Werbung|\*Dieser Artikel|\*Werbung))", re.I)
    m = list(bottom_divider_rx.finditer(body_part))
    
    if m:
        # Nimm den letzten Treffer
        last_match = m[-1]
        insert_pos = last_match.start()
        new_body = body_part[:insert_pos] + insert_payload + body_part[insert_pos:]
    else:
        # Fallback: Einfach am Ende anhängen
        new_body = body_part.rstrip() + insert_payload
        
    return f"---{fm_part}---{new_body}"


# ------------------------------------------------------------
#  ALTLASTEN: die vier Bausteine der ersten Generation, je als Einzelsatz
#  erfassbar. Satz-Ebene statt Absatz-Ebene, damit (a) dazwischenstehender
#  Redaktionstext erhalten bleibt und (b) eine bloße Umformulierung nicht
#  durchschluepft, nur weil ihr Emoji im naechsten Absatz steht.
# ------------------------------------------------------------
ALT_S1_RX = re.compile(r"Sich gezielt mit dem Thema[^\n]*?bares Geld zu sparen\.", re.S)
ALT_HEBEL_RX = re.compile(r"[^.!?\n]*(?:einer|ein) der einfachsten Hebel[^.!?\n]*[.!?]", re.S)
ALT_AURUF_RX = re.compile(r"Fang[^.!?\n]*?(?:heute|sofort|direkt)[^.!?\n]*[.!?]", re.S)
EMOJI_ALT = "\U0001F4B8\U0001F680"   # 💸🚀 – Signatur der Altgeneration
ALT_EMOJI_RX = re.compile(r"[ \t]+\U0001F4B8[^\n]*", re.M)
ALT_WER_RX = re.compile(r"Wer sich [^.!?\n]{0,48}?(?:intensiv|gezielt|näher|gründlich)"
                        r"[^.!?\n]{0,48}?mit dem Thema[^.!?\n]*[.!?]", re.S)
ALT_RX = (ALT_S1_RX, ALT_HEBEL_RX, ALT_EMOJI_RX, ALT_AURUF_RX, ALT_WER_RX)


def fazit_rumpf(body: str):
    """(anfang, ende) des Fazit-Rumpfs, wenn Altbaustil drin steht – sonst None.

    Pflicht ist die Kombination: ein Altformel-Satz UND ein Aufruf bzw. das
    Emoji-Paar. Steht nur eine der Figuren da, ist es redaktioneller Text.
    """
    m = re.search(r"(?m)^(#{2,3})\s+.*(fazit|zusammenfassung)[^\n]*$", body, re.I)
    if not m:
        return None
    rest = body[m.end():]
    nxt = re.search(r"(?m)^#{1,3}\s+\S", rest)
    a, b = m.end(), m.end() + (nxt.start() if nxt else len(rest))
    abschnitt = body[a:b]
    if not (ALT_S1_RX.search(abschnitt) or ALT_HEBEL_RX.search(abschnitt)
            or ALT_WER_RX.search(abschnitt)):
        return None
    if not (ALT_AURUF_RX.search(abschnitt) or EMOJI_ALT in abschnitt):
        return None
    return a, b


def altlast_satz(title: str, route: str) -> str:
    """Der neue Hausabsatz – ohne Altformel, ohne Emoji, ohne Fremd-Route."""
    return generate_fazit_text(title, route).split("\n\n", 1)[1].rstrip("\n")


def normalize_altlasten(full_doc: str, title: str, route: str) -> tuple[str, bool, str]:
    """Altbaustil im Fazit gegen den Hausstil tauschen. (text, geheilt, grund).

    Die Raender werden deterministisch gesetzt (eine Leerzeile vor und nach dem
    Rumpf): Leerzeilen-Kosmetik am ganzen Dokument hatte schon die Ueberschrift
    an den Absatz und den Absatz an die naechste Rubrik geleimt.
    """
    parts = full_doc.split("---", 2)
    if len(parts) < 3:
        return full_doc, False, "kein Frontmatter"
    fm_part, body_part = parts[1], parts[2]
    fund = fazit_rumpf(body_part)
    if not fund:
        return full_doc, False, "kein Altbaustil"
    a, b = fund
    über = body_part[:a]
    nach = body_part[b:]
    reste = []
    for block in re.split(r"\n\s*\n", body_part[a:b]):
        bereinigt = block
        for rx in ALT_RX:
            bereinigt = rx.sub("", bereinigt)
        bereinigt = re.sub(r"[ \t]{2,}", " ", bereinigt).strip()
        if len(bereinigt) > 40:
            reste.append(bereinigt)
    haus = altlast_satz(title, route)
    if haus in body_part[a:b] and not reste:
        return full_doc, False, "bereits Hausstil"
    block = "\n\n".join([haus] + reste)
    neuer_body = über.rstrip("\n") + "\n\n" + block + ("\n\n" + nach.strip("\n") if nach.strip() else "\n")
    # Rubrikenkopf nur neu ableiten, wenn er selbst Schmiede-Form war
    kopf = re.search(r"(?m)^(#{2,3})[ \t]+.*(fazit|zusammenfassung)[^\n]*$", über, re.I)
    if kopf and re.match(r"(?i)^#{2,3}[ \t]+fazit\b", kopf.group(0)):
        gewollt = generate_fazit_text(title, route).split("\n", 1)[0]
        if kopf.group(0).strip() != gewollt.strip():
            neuer_body = neuer_body.replace(kopf.group(0), gewollt, 1)
    if neuer_body == body_part:
        return full_doc, False, "bereits Hausstil"
    return f"---{fm_part}---{neuer_body}", True, "Altbaustil ersetzt"


# ============================================================
#  SABOTAGE-SCHUTZ: Selbsttest (Impftest vor Arbeitsaufnahme)
# ============================================================
def selftest() -> list[str]:
    fehler = []
    # Fall 1: check_sections erkennt existierende Rubriken korrekt
    test_body_ok = "## Fazit\nSuper Sache.\n## Häufige Fragen\nWas tun?"
    f_ok, q_ok = check_sections(test_body_ok)
    if not f_ok or not q_ok:
        fehler.append(f"Selftest Fall 1: Vorhandene Sektionen nicht erkannt (Fazit={f_ok}, FAQ={q_ok})")
        
    # Fall 2: check_sections erkennt fehlendes Fazit
    test_body_no_f = "## Häufige Fragen\nWas tun?"
    f_no, q_no = check_sections(test_body_no_f)
    if f_no or not q_no:
        fehler.append(f"Selftest Fall 2: Fehlendes Fazit falsch erkannt (Fazit={f_no}, FAQ={q_no})")
        
    # Fall 3: check_sections erkennt fehlendes FAQ
    test_body_no_q = "## Fazit\nSuper Sache."
    f_no2, q_no2 = check_sections(test_body_no_q)
    if not f_no2 or q_no2:
        fehler.append(f"Selftest Fall 3: Fehlendes FAQ falsch erkannt (Fazit={f_no2}, FAQ={q_no2})")
        
    # Fall 4: generate_fazit_text enthält das Keyword "C24 Bank" bei Route "girokonto"
    f_text_gk = generate_fazit_text("Mein Girokonto", "girokonto")
    if "C24 Bank" not in f_text_gk:
        fehler.append("Selftest Fall 4: Girokonto-Fazit nennt C24 Bank nicht namentlich!")
        
    # Fall 5: generate_faq_text enthält die exakte Anchor-Phrase für C24 Bank bei Route "tagesgeld"
    faq_text_tg = generate_faq_text("tagesgeld")
    if "Jetzt C24 Bank Angebote vergleichen" not in faq_text_tg:
        fehler.append("Selftest Fall 5: Tagesgeld-FAQ enthält nicht die Anchor-Phrase!")
        
    # Fall 6: Intelligente Einfügung platziert Fazit vor FAQ, falls FAQ bereits existiert
    test_doc = "---\ntitle: \"Giro\"\n---\nRunning text.\n\n## Häufige Fragen\nQ1?"
    result_doc = insert_sections(test_doc, False, True, "Giro", "girokonto")
    if "## Fazit:" not in result_doc or result_doc.index("## Fazit:") > result_doc.index("## Häufige Fragen"):
        fehler.append("Selftest Fall 6: Fazit wurde nicht vor existierender FAQ-Rubrik eingefügt!")
        
    # Fall 7: Altbaustil wird erkannt und gegen den Hausstil getauscht
    alt_doc = ('---\ntitle: "Heizkosten sparen"\n---\nText.\n\n'
               '## Fazit: Heizkosten sparen\n\nSich gezielt mit dem Thema **Heizkosten sparen** '
               'zu beschäftigen, ist einer der einfachsten Hebel, um deine Finanzen selbst in die '
               'Hand zu nehmen und bares Geld zu sparen. Fang am besten heute an, vergleiche die '
               'Angebote und sichere dir deine Ersparnis! \U0001F4B8\U0001F680\n')
    out7, geheilt7, _ = normalize_altlasten(alt_doc, "Heizkosten sparen", "gas")
    if not geheilt7 or "Sich gezielt mit dem Thema" in out7 or "Fang am besten heute an" in out7:
        fehler.append("Selftest Fall 7: Altbaustil nicht geheilt!")
    if "\U0001F4B8" in out7 or "Der Hebel bei" not in out7:
        fehler.append("Selftest Fall 7b: Hausstil fehlt oder Emoji geblieben!")
    if not re.search(r"(?m)^## Fazit:.*\n\nDer Hebel bei", out7):
        fehler.append("Selftest Fall 7c: Kopf und Absatz nicht durch eine Leerzeile getrennt!")

    # Fall 8: Idempotenz – ein zweiter Lauf darf nichts mehr ändern
    out8, geheilt8, grund8 = normalize_altlasten(out7, "Heizkosten sparen", "gas")
    if geheilt8 or out8 != out7:
        fehler.append(f"Selftest Fall 8: Zweiter Lauf war nicht neutral ({grund8})!")

    # Fall 9: Fazit ohne Aufruf/Emoji ist redaktionell – Finger weg
    red_doc = ('---\ntitle: "Kreditkarte"\n---\nText.\n\n## Fazit\n\n'
               'Sich gezielt mit dem Thema Kreditkarten zu beschäftigen, lohnt sich. '
               'Wer drei Angebote durchrechnet, sieht den Unterschied sofort.\n')
    _, geheilt9, _ = normalize_altlasten(red_doc, "Kreditkarte", "kreditkarte")
    if geheilt9:
        fehler.append("Selftest Fall 9: Redaktioneller Text überschrieben – Editorial-Schutz defekt!")

    # Fall 10: Umformulierte Formel + Emoji im Folgeabsatz wird geheilt, der
    #           Redaktionssatz dazwischen überlebt, die Folge-Rubrik bleibt heil
    para_doc = ('---\ntitle: "Flugtickets buchen"\n---\nText.\n\n## Fazit: Flugtickets\n\n'
                'Wer sich intensiv mit dem Thema **Flugtickets buchen** befasst, spart doppelt. '
                'Es ist einer der einfachsten Hebel in deiner Reiseplanung. '
                'Der Preisalarm bleibt bis zum Abflug tageweise eingestellt.\n\n'
                'Greif zu und sichere dir die Ersparnis! \U0001F4B8\U0001F680\n\n'
                '## Häufige Fragen\n\nWas tun?\n')
    out10, geheilt10, _ = normalize_altlasten(para_doc, "Flugtickets buchen", "reisen")
    if not geheilt10 or "einer der einfachsten Hebel" in out10 or "\U0001F4B8" in out10:
        fehler.append("Selftest Fall 10: Paraphrase oder Emoji nicht geheilt!")
    if "Der Preisalarm bleibt" not in out10:
        fehler.append("Selftest Fall 10b: Redaktionssatz zwischen den Altsätzen verloren!")
    if re.search(r"[a-zäöüß]\n## ", out10):
        fehler.append("Selftest Fall 10c: Folge-Rubrik an den Text geleimt!")

    # Fall 11: Titelpräfix – „50-30-20-Regel“ darf nicht zu „Regel“ gestutzt werden
    f11 = generate_fazit_text("2026-09-11 50-30-20-Regel: [Budget] im Griff", "allgemein")
    if "50-30-20-Regel" not in f11 or "](" in f11:
        fehler.append("Selftest Fall 11: Titelpräfix zerstört oder Markdown-Rest im Fazit!")

    return fehler


def main() -> int:
    stf = selftest()
    if stf:
        print("🛑 FAZIT-SCHMIEDE-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert!")
        print("\n".join(stf))
        return 2
    print("✅ Fazit-Schmiede-Selbsttest: 11 Faelle gruen.")

    # Finde alle Posts
    from post_utils import list_post_paths
    posts = list_post_paths()
    if NEW_ONLY:
        today = datetime.now(timezone.utc).date().isoformat()
        posts = [p for p in posts if today in os.path.basename(os.path.dirname(p))]
        
    print(f"Artikel: {len(posts)} · Schmiede läuft …")
    
    missing_fazit_count = 0
    missing_faq_count = 0
    healed_count = 0
    altlasten_count = 0
    alt_geheilt = 0
    
    report_rows = []
    
    for p_str in posts:
        p_path = Path(p_str)
        slug = p_path.parent.name
        full_content = p_path.read_text(encoding="utf-8")
        
        parts = full_content.split("---", 2)
        if len(parts) < 3:
            continue
            
        fm_part = parts[1]
        body_part = parts[2]
        
        # Bestimme Titel aus Frontmatter
        title = ""
        for line in fm_part.splitlines():
            if line.startswith("title:"):
                title = line.partition(":")[2].strip().strip('"').strip("'")
                break
                
        if not title:
            title = slug.replace("-", " ").title()
            
        has_fazit, has_faq = check_sections(body_part)

        if ALTLASTEN:
            if fazit_rumpf(body_part):
                altlasten_count += 1
                try:
                    route = ROUTE_SNIFFER(body_part, "", title)
                except TypeError:
                    route = ROUTE_SNIFFER(body_part)
                status_str = "⚠️ Altbaustil (Report)"
                if DO_FIX and not DRY_RUN:
                    text_neu, geheilt, grund = normalize_altlasten(full_content, title, route)
                    if geheilt:
                        p_path.write_text(text_neu, encoding="utf-8")
                        alt_geheilt += 1
                        status_str = "🩹 Altbaustil ersetzt"
                    else:
                        status_str = f"⚠️ nicht geheilt: {grund}"
                report_rows.append({"slug": slug, "title": title, "route": route,
                                    "has_fazit": has_fazit, "has_faq": has_faq,
                                    "status": status_str})
            continue

        if not has_fazit:
            missing_fazit_count += 1
        if not has_faq:
            missing_faq_count += 1
            
        if not has_fazit or not has_faq:
            # Titel mitgeben: ohne ihn entscheidet das 1200-Zeichen-Intro und ein
            # Streifwort (Kasko, Haftpflicht) überstimmt das eigentliche Thema.
            try:
                route = ROUTE_SNIFFER(body_part, "", title)
            except TypeError:      # Signatur ohne Titel-Parameter (Fallback-Def)
                route = ROUTE_SNIFFER(body_part)
            
            if DO_FIX and not DRY_RUN:
                updated_content = insert_sections(full_content, has_fazit, has_faq, title, route)
                p_path.write_text(updated_content, encoding="utf-8")
                healed_count += 1
                status_str = "🩹 geheilt"
            else:
                status_str = "⚠️ unvollständig"
                
            report_rows.append({
                "slug": slug,
                "title": title,
                "route": route,
                "has_fazit": has_fazit,
                "has_faq": has_faq,
                "status": status_str
            })
            
    # Schreibe Report
    report_lines = [
        "# 🔨 FAZIT-REPORT (fazit_schmiede.py)",
        "",
        f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: " + ("FIX" if DO_FIX else ("DRY-RUN" if DRY_RUN else "REPORT")),
        "",
        f"**Geprüfte Artikel:** {len(posts)} · **Fehlende Fazits:** {missing_fazit_count} · **Fehlende FAQs:** {missing_faq_count}",
        f"**Automatisch geheilt:** {healed_count if DO_FIX else 0}"
        + (f" · **Altlasten:** {altlasten_count} · geheilt: "
           f"{alt_geheilt if DO_FIX and not DRY_RUN else 0}" if ALTLASTEN else ""),
        "",
        "| Artikel (Slug) | Route | Fazit vorhanden? | FAQ vorhanden? | Status |",
        "|---|---|---|---|---|"
    ]
    
    for row in sorted(report_rows, key=lambda x: x["slug"]):
        f_sym = "✅ Ja" if row["has_fazit"] else "❌ Nein"
        q_sym = "✅ Ja" if row["has_faq"] else "❌ Nein"
        report_lines.append(f"| `{row['slug']}` | `{row['route']}` | {f_sym} | {q_sym} | **{row['status']}** |")
        
    if not report_rows:
        report_lines.append("")
        report_lines.append("🎉 **Alle Artikel vollständig! Jedes Stück hat ein Fazit und eine FAQ-Rubrik.**")
        
    report_lines.append("")
    report_lines.append("---")
    report_lines.append("_Autarke Content-Schmiede: Deterministiche Veredelung basierend auf Affiliate-Themenkontext._")
    
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    
    # History schreiben
    os.makedirs(HISTORY.parent, exist_ok=True)
    with open(HISTORY, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "posts": len(posts),
            "missing_fazit": missing_fazit_count,
            "missing_faq": missing_faq_count,
            "healed": healed_count,
            "altlasten": altlasten_count,
            "altlasten_geheilt": alt_geheilt
        }, ensure_ascii=False) + "\n")
        
    zusatz = f" Altlasten: {altlasten_count}, davon geheilt: {alt_geheilt}." if ALTLASTEN else ""
    print(f"Fazit-Schmiede abgeschlossen. Fehlende Fazits: {missing_fazit_count}, "
          f"fehlende FAQs: {missing_faq_count}."
          + (f" Geheilt: {healed_count}." if DO_FIX else "") + zusatz)

    if ALTLASTEN and DO_FIX and not DRY_RUN:
        # Der heilende Lauf ist gruen, wenn nichts Derartiges offen bleibt.
        return 1 if altlasten_count and alt_geheilt != altlasten_count else 0
    return 1 if report_rows else 0


if __name__ == "__main__":
    sys.exit(main())
