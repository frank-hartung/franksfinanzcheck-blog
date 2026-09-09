#!/usr/bin/env python3
# ============================================================
#  TAG-CASING – gemeinsamer Wortschatz-Kanon der Groß-/Kleinschreibung
#
#  WARUM EIGENE DATEI (Frank, 09.09.2026, Premium-Level der Blogautomatik):
#  Die Schreibweise von Tags, Kategorien, Pin-Texten und Fließtext lag an
#  DREI Orten:
#      · scripts/generate_drafts.py  – eigene NOMEN_SET (40 Woerter) + TAG_FIXES
#      · scripts/engine_generate.py  – schrieb tags als rohe Keyword-Liste (ungeprueft)
#      · scripts/casing_guard.py     – Akronyme/Marken nur im BODY, Front-Matter tabu
#  Folge (real gemessen 09.09.2026): Artikel ab 04.09. trugen komplett
#  kleingeschriebene Tags ("frugalismus tipps", "dns hack", "standby kosten"),
#  aeltere Artikel schrieben korrekt "Geld sparen im Alltag" – sichtbare
#  Casing-Fehler auf Tag-Chips, /tags/-Taxonomeseiten und Pinterest-Pins.
#  Ausserdem: "50-30-20-Regel" UND "50 30 20 Regel" im selben Artikel –
#  zwei Taxonomie-Terme fuer ein Thema (verwaessert interne Links und Signale).
#
#  DESHALB: EIN Lexikon, EINE Normalisierung, drei Nutzer (Draft-Generator,
#  Content-Engine, Guard). Neuer Wortschatz wird nur noch HIER ergaenzt.
#
#  ENTSCHEIDUNGSREGELN (Duden, Wortarten-Logik):
#    1. Satzanfang                    -> gross
#    2. Nomen / nominalisiertes Wort  -> gross   (NOUNS + Nomen-Suffixe)
#    3. Akronym                       -> kanonische Form (dsl -> DSL, nie "Dsl")
#    4. Marke                         -> kanonische Form (Fritzbox -> FRITZ!Box)
#    5. Verben, Adjektive, Partikeln, Pronomen, Zahlen -> klein
#    6. Unbekanntes Wort              -> bleibt stehen und wird gemeldet.
#       Der Klassifikator raet nicht: entschieden wird nur, was sicher ist.
#
#  Marken, die bewusst klein schreiben (congstar, otelo, idealo, ebay,
#  comdirect, pyur, lexoffice, flatex, smartbroker), werden NIE grossgezwungen.
#
#  Aufruf:
#    python3 scripts/tag_casing.py "frugalismus tipps" "dns hack"
#    python3 scripts/tag_casing.py --selftest
# ============================================================

from __future__ import annotations

import re
import sys

# ---------------------------------------------------------------------------
# 1. AKRONYME – kanonische Schreibweise (Schluessel klein, Wert = Kanon)
# ---------------------------------------------------------------------------
ACRONYMS = {
    "dsl": "DSL", "vdsl": "VDSL", "adsl": "ADSL", "wlan": "WLAN", "lan": "LAN",
    "vlan": "VLAN", "etf": "ETF", "etfs": "ETFs", "kfz": "Kfz", "pkw": "PKW",
    "lkw": "LKW", "sim": "SIM", "esim": "eSIM", "sms": "SMS",
    "pin": "PIN", "tan": "TAN", "mtan": "mTAN", "sepa": "SEPA", "iban": "IBAN",
    "bic": "BIC", "nfc": "NFC", "rfid": "RFID", "usb": "USB", "hdmi": "HDMI",
    "lte": "LTE", "5g": "5G", "4g": "4G", "3g": "3G",
    "ip": "IP", "ipv4": "IPv4", "ipv6": "IPv6", "dns": "DNS", "vpn": "VPN",
    "url": "URL", "http": "HTTP", "https": "HTTPS", "ssh": "SSH", "ntp": "NTP",
    "dhcp": "DHCP", "ssid": "SSID", "doh": "DoH", "dot": "DoT",
    "docsis": "DOCSIS", "ftth": "FTTH", "fttb": "FTTB", "ont": "ONT",
    "avm": "AVM", "dect": "DECT", "gps": "GPS", "led": "LED", "oled": "OLED",
    "lcd": "LCD", "tft": "TFT", "cat5": "CAT5", "cat6": "CAT6", "cat7": "CAT7",
    "oem": "OEM", "faq": "FAQ", "cta": "CTA", "seo": "SEO", "dslam": "DSLAM",
    "qos": "QoS", "voip": "VoIP", "tv": "TV", "hd": "HD", "fhd": "FHD",
    "qhd": "QHD", "uhd": "UHD", "hdr": "HDR", "cdn": "CDN", "api": "API",
    "ui": "UI", "ux": "UX", "pc": "PC", "it": "IT", "mwp": "MWP",
    "dsgvo": "DSGVO", "tdddg": "TDDDG", "vsbg": "VSBG", "vvg": "VVG",
    "mwst": "MwSt", "gb": "GB", "tb": "TB", "mb": "MB",
}

# Einheiten: eigenes Kanon (kleines k bei "kilo" ist Physik, kein Tippfehler)
UNITS = {
    "kwh": "kWh", "mwh": "MWh", "wh": "Wh", "kw": "kW", "mw": "MW",
    "mbit/s": "Mbit/s", "gbit/s": "Gbit/s", "kbit/s": "kbit/s",
    "mbit": "Mbit", "gbit": "Gbit", "kb/s": "kB/s", "mb/s": "MB/s",
    "km/h": "km/h", "°c": "°C", "°f": "°F",
}

# ---------------------------------------------------------------------------
# 2. MARKEN-KANON – normalisierte Variante -> kanonische Schreibweise
#    Schluessel = klein, ohne Sonderzeichen/Leerzeichen, Umlaute aufgelöst.
# ---------------------------------------------------------------------------
BRANDS = {
    # AVM – offizielle Schreibweise ohne Leerzeichen: "FRITZ!Box"
    "fritzbox": "FRITZ!Box", "fritzboxen": "FRITZ!Boxen",
    "fritzrepeater": "FRITZ!Repeater", "fritzpowerline": "FRITZ!Powerline",
    "fritzfon": "FRITZ!Fon", "fritzdect": "FRITZ!DECT", "fritzos": "FRITZ!OS",
    # Vergleichsportale / Affiliate-Partner (Hauskanon = data/brand_lock.yaml)
    "check24": "CHECK24", "verivox": "Verivox", "tarifcheck": "Tarifcheck",
    "tarifcheck24": "Tarifcheck24", "awin": "Awin", "idealo": "idealo",
    # TK-Markt
    "telekom": "Telekom", "vodafone": "Vodafone", "congstar": "congstar",
    "otelo": "otelo", "o2": "O2", "pyur": "pyur", "freenet": "Freenet",
    "drillisch": "Drillisch", "magentaeins": "MagentaEINS", "eplus": "E-Plus",
    "unitymedia": "Unitymedia",
    # Energie / Heizung / Smart Home
    "eon": "E.ON", "rwe": "RWE", "netatmo": "Netatmo",
    "homematic": "Homematic", "shelly": "Shelly", "eq3": "EQ3",
    "viessmann": "Viessmann", "vaillant": "Vaillant",
    # Plattformen / Geraete / Software
    "whatsapp": "WhatsApp", "instagram": "Instagram", "facebook": "Facebook",
    "youtube": "YouTube", "tiktok": "TikTok", "netflix": "Netflix",
    "paypal": "PayPal", "googlepay": "Google Pay", "applepay": "Apple Pay",
    "amazon": "Amazon", "amazonprime": "Amazon Prime", "google": "Google",
    "gmail": "Gmail", "microsoft": "Microsoft", "windows": "Windows",
    "office": "Office", "excel": "Excel", "word": "Word", "outlook": "Outlook",
    "iphone": "iPhone", "ipad": "iPad", "imac": "iMac", "apple": "Apple",
    "android": "Android", "samsung": "Samsung", "github": "GitHub",
    "linkedin": "LinkedIn", "pinterest": "Pinterest", "ebay": "eBay",
    "skyscanner": "Skyscanner", "bookingcom": "Booking.com",
    "tripadvisor": "Tripadvisor", "chrome": "Chrome", "firefox": "Firefox",
    "safari": "Safari", "openai": "OpenAI", "chatgpt": "ChatGPT",
    # Banken / Fintechs
    "n26": "N26", "c24bank": "C24 Bank",
    "traderepublic": "Trade Republic", "scalablecapital": "Scalable Capital",
    "ing": "ING", "ingdiba": "ING", "dkb": "DKB", "comdirect": "comdirect",
    "consorsbank": "Consorsbank", "postbank": "Postbank", "sparkasse": "Sparkasse",
    "volksbank": "Volksbank", "hypovereinsbank": "HypoVereinsbank",
    "payback": "PAYBACK", "ynab": "YNAB", "wiso": "WISO", "lexoffice": "lexoffice",
    "smartbroker": "smartbroker", "flatex": "flatex",
    "finanzfluss": "Finanzfluss", "verbraucherzentrale": "Verbraucherzentrale",
    # Karten / Bezahlen
    "mastercard": "Mastercard", "visa": "Visa", "girocard": "Girocard",
    # Auto / Versicherung / Reise
    "adac": "ADAC", "dekra": "DEKRA", "huk24": "HUK24", "huk": "HUK",
    "devk": "DEVK", "allianz": "Allianz", "ergo": "ERGO", "generali": "Generali",
    "sixt": "SIXT", "europcar": "Europcar", "enterprise": "Enterprise",
    "buchbinder": "Buchbinder", "avis": "Avis", "hertz": "Hertz",
    "googlemaps": "Google Maps",
}

# Normalisierungs-Schluessel fuer die Markenliste (einmal, beim Laden)
BRANDS = {re.sub(r"[^a-z0-9]", "", k.lower()): v for k, v in BRANDS.items()}

# Marken, die bewusst klein schreiben – nie gross erzwingen
BRANDS_LOWER = {v for v in BRANDS.values() if v[:1].islower()}

# ---------------------------------------------------------------------------
# 3. NOMEN des Blogwortschatzes (Tags, Kategorien, Fließtext)
# ---------------------------------------------------------------------------
NOUNS = set("""
ratgeber vergleich geld alltag spartipps budget budgetplanung fixkosten
nebenkosten kosten preis preise preisgarantie preisalarm preisbremse
kostenfalle gebuehren gebuehren bankgebuehren kontogebuehren sparrate
sparmethoden sparmöglichkeit haushaltsbuch haushaltsbudget haushalt
ausgaben einnahmen vermögen vermoegen notgroschen mindset freiheit
kontowechsel konto girokonto tagesgeld tagesgeldkonto tagesgeldzinsen
zinsen zinssatz zinssätze kredit kreditkarte ratenkredit dispokredit
bank karte karten cashback bonus gutschein deal deals angebot angebote
sparpotenzial verträge vertraege vertrag vertragslaufzeit kündigungsfrist
kuendigungsfrist selbstbeteiligung deckung deckungsumfang leistung
leistungen vorteil nachteil vorteile nachteile irrtümer mythen fehler
fallen tipp tipps trick tricks hack hacks check checks checkliste
rechnung abrechnung gasrechnung stromrechnung heizkosten beleg nachweis
antrag formular frist fristen termin termine stichtag jahr monat woche tag
nacht sommer winter herbst frühling fruehling spätsommer spaetsommer
januar februar märz april mai juni juli august september oktober november
dezember weihnachten ostern pfingsten silvester neujahr advent urlaub reise
reisen roadtrip flug flüge fluege flugtickets flugvergleich billigfluege
billigflüge mietwagen auto fahrzeug versicherung versicherungen haftpflicht
privathaftpflicht hausrat hausratversicherung gebäudeversicherung
gebaeudeversicherung wohngebäudeversicherung elementarschadenversicherung
kasko vollkasko teilkasko schutz schäden schaeden schaden
schadenfreiheitsklasse typklasse regionalklasse beitrag prämie praemie
tarif tarife gastarif stromtarif handytarif datentarif handyvertrag
internetvertrag wechselbonus anschlusspreis bereitstellungskosten router
routermiete routerfreiheit repeater mesh empfang speed gigaspeed bandbreite
breitband glasfaser kabel anschluss server browser modem dns-server
stromverbrauch energieverbrauch stromkosten gaskosten energiekosten
energiekrise energie stromfresser energiediebe heizung heizungscheck
vorlauftemperatur heizkurve thermostat heizkörper kessel wärme dämmung
zugluft fenster tür wohnung haus immobilie immobilien miete kaution
betriebskosten energieausweis vorsorge existenzschutz risiko chance option
optionen plan planung strategie strategien methode methoden regel regeln
faustregel beispiel beispiele übersicht uebersicht schrittfolge schritte
anleitung guide frage fragen antwort antworten unterschied auswahl
vorbereitung wartung prüfung pruefung test tests vergleichsportal
vergleichsrechner tarifrechner rechner tool tools app apps software cloud
kontoauszug umsatz konsum verzicht genuss qualität lebensqualität minimum
maximum bedarf wünsche wunsch zielziele ziel traum leben tagespreis
monatspreis jahresverbrauch grundgebühr grundpreis arbeitspreis
netzentgelte messstelle zähler ablesung ablesung verbrauch verbraucherzentrale
datenschutz privatsphäre tracker cookie cookies passwort zugangsdaten
sicherheit phishing malware spam update updates funktion funktionen
eigenschaft baustein bausteine klausel klauseln bedingungen voraussetzung
service kundenservice hotline chatbot support garantie geschäft
kostenstelle zahlung rücklage reserve quote spenderquote spender
sparziel notfallfonds budgetrahmen budgetformel monatsbudget jahresbudget
vergleichsrechner Spartipp Monatssparplan Dauerauftrag Festgeld Depot
Sparplan Anbieter Anbieterwechsel Sonderkündigung Grundversorgung
Sondertarif Neukunde Bestandskunde Preisvergleich Strompreis Gaspreis
Abschlag Vorauszahlung Nebenkostenabrechnung Mietnebenkosten Kaution
Rückzahlung Schriftform Zugang Frist Ablauf Fristende Fristbeginn
Vertragsstrafe Rücktrittsrecht Widerrufsrecht Widerspruch
Widerrufsjahr Police Policendaten Versicherungsnummer Schadensmeldung
Gutachten Schätzung Sanierung Modernisierung Dämmmaßnahme
Heizkörperthermostat programmierung zeitplan ablauf zeitfenster
""".split())

# Nachfuehren: Eintraege immer klein (der Klassifikator vergleicht lowercase),
# plus die Woerter, die im Tag-Bestand des Blogs haeufig sind.
NOUNS = {w.lower() for w in NOUNS if w}
NOUNS |= {
    "internet", "wlan", "smart-home", "smartphone", "tablet", "laptop",
    "tarifdschungel", "kleinvieh", "grossvieh", "haustier", "haustiere",
    "tierversicherung", "hundeversicherung", "katzenversicherung",
    "gebaeude", "gebäude", "nebenkosten", "wasser", "heizöl", "pellet",
    "hackschnitzel", "wärmepumpe", "photovoltaik", "balkonkraftwerk",
    "speicher", "e-auto", "elektroauto", "ladesäule", "fahrrad", "kraftrad",
    "motorrad", "anhänger", "wohnmobil", "camper", "wohnwagen",
    "strassenbahn", "bahncard", "ticket", "tickets", "abo", "abos",
    "mitgliedschaft", "zahlung", "lastschrift", "überweisung",
    "monatsuebersicht", "monatsübersicht", "jahresuebersicht",
    "jahresübersicht", "quartal", "bilanz", "kassensturz", "controlling",
    "auswertung", "statistik", "analyse", "report", "protokoll", "notiz",
    "notizen", "memory", "erinnerung", "kalender", "terminplan", "fahrplan",
    "route", "strecke", "zone", "gebiet", "region", " bundesland",
    "postleitzahl", "netz", "netze", "ausbau", "verfuegbarkeit",
    "verfügbarkeit", "leitung", "anschlussdose", "dose", "kabelanschluss",
    "satellit", "antenne", "empfangsgebiet", "latenz", "ping", "download",
    "upload", "datenvolumen", "flatrate", "flat", "minuten", "min",
    "sekunden", "einheit", "einheiten", "rechenbeispiel", "beispielrechnung",
    "spanne", "bereich", "wert", "werte", "quote", "anteil", "anteil",
    "summe", "betrag",
}
NOUNS = {w.strip() for w in NOUNS if w and w.strip() and " " not in w.strip()}

# ---------------------------------------------------------------------------
# 4. Was mitten im Ausdruck klein bleibt: Verben, Adjektive, Partikeln,
#    Pronomen, Konjunktionen, Adverbien, Präpositionen, Abkuerzungen.
#    (Bewusst kein Vollständigkeitsanspruch – nur der Kern des Blogs und
#     die haeufigen KI-Formen; Unbekanntes wird gemeldet, nie geraten.)
# ---------------------------------------------------------------------------
LOWER = set("""
der die das ein eine einem einen einer eines kein keine keinem keinen aller
alle alles etwas nichts viel wenig mehr meiste beide manche einige ich du dir
dich dein deine deinem deiner mein meine unser unsere euer euere sein ihre
ihren ihnen sie es wir man sich wer was wie wo wann warum weshalb ob dass
damit wenn als also aber oder sondern doch jedoch außerdem ausserdem
schließlich schliesslich nur schon noch wieder selbst gerade zusammen etwa
fast wirklich eigentlich natürlich übrigens grundsätzlich pauschal generell
aktuell insgesamt zusätzlich dauerhaft langfristig kurzfristig monatlich
jährlich einmalig täglich wöchentlich
im am an auf aus bei beim mit von zu zur zum nach vor über unter ohne durch
für gegen um bis je pro per via gegenüber wegen trotz dank zwecks inklusive
ausschließlich
sparen senken wechseln vergleichen finden führen machen buchen planen rechnen
zahlen bezahlen einzahlen abheben überweisen absichern sichern heizen schützen
verbessern stoppen tracken ändern anlegen mieten kaufen verkaufen erreichen
aufbauen anwenden nutzen benutzen testen prüfen kündigen verlängern
optimieren reduzieren vermeiden umsetzen einrichten anpassen eintragen
auswählen abwägen kassieren verzichten verlieren gewinnen starten öffnen
schließen entlüften dämmen messen lesen schreiben zeigen erklären bewerten
empfehlen kalkulieren verhandeln warten reparieren tauschen sortieren
aufräumen putzen tippen pinnen folgen drosseln staunen löschen drucken
kopieren scannen streamen loggen mailen chatten posten teilen suchen klicken
scrollen mitnehmen runterladen updaten installieren koppeln verbinden trennen
günstig guenstig günstiger billig billigste teuer teurer kostenlos
kostenloser kostenlose sicher sichere sicherer einfach schnelle schnell
schneller langsam klug clever smart digital privat persönlich finanziell
flexibel transparent ehrlich wichtig wichtigste sinnvoll praktisch
interessant neu neue neues erster erste ersten letzte letzten nächsten
zweiten dritte großen kleine volle volle richtige beste ganzen offene
freie winterfest sparsam effizient spürbar extrem besonders allgemein
speziell wesentlich erforderliche empfehlenswert unverzichtbar verfügbar
abgelaufen
vs usw etc bzw inkl exkl zzgl vgl sog resp ff min max std sek
oben unten hier dort heute morgen gestern jetzt sofort bald später früh oft
immer niemals einmal weiter zurück hinzu heraus vorbei allein gemeinsam
lieber eher sowohl weder entweder beziehungsweise kennen lernen merken mögen müssen sollen wollen können dürfen helfen treffen
passen gelten bleiben kommen gehen brauchen schaffen anrufen abholen
mitmachen teilnehmen aufpassen nachlesen nachrechnen sichergehen abwarten
loslegen anfangen beginnen weitermachen dabeibleiben vorbeikommen vorbeischauen
reinhalten sauberhalten freihalten warmhalten abgeben abgeben zusteigen umsteigen
einsteigen aussteigen nachfüllen auffüllen nachrüsten abreißen abrechnen abzahlen
abholen anlehnen anrechnen aufstocken nachzahlen einzahlen auszahlen abzocken
""".split())

LOWER = {w.lower() for w in LOWER if w}

# ---------------------------------------------------------------------------
# 5. Nomen-Suffixe (erkennen Wortfamilien ohne Einzelfall-Pflege)
# ---------------------------------------------------------------------------
# Endungen, die IMMER ein Nomen anzeigen und nie eine Verbform sind.
# („-chen" ist bewusst nicht dabei: „rutschen"/„überwachen" enden darauf.)
NOUN_SUFFIXES = (
    "ung", "heit", "keit", "schaft", "tum", "ling", "ismus", "tion", "sion",
    "ment", "ität", "itaet",
)

# Abkuerzungen, die einen Satz NICHT beenden (wichtig fuer Satzanfang-Regel)
ABBREVIATIONS = [
    "z. B.", "z.B.", "u. a.", "u.a.", "d. h.", "d.h.", "i. V. m.", "i.V.m.",
    "bzw.", "etc.", "usw.", "ca.", "circa", "Nr.", "Abs.", "Art.", "Mio.",
    "Mrd.", "Tsd.", "Std.", "Min.", "Sek.", "inkl.", "exkl.", "zzgl.", "vgl.",
    "sog.", "resp.", "ff.", "a. D.", "a.D.", "n. Chr.", "u. U.", "u.U.", "ggs.",
    "GmbH", "e. V.", "e.V.", "HGB", "BGB", "VVG", "USt", "MwSt", "i. O.",
    "i.O.", "lt.", "s. ", "vgl", "vs.", "vs", "bzw", "usw", "etc",
]

MONTHDAYS = {
    "januar", "februar", "märz", "maerz", "april", "mai", "juni", "juli",
    "august", "september", "oktober", "november", "dezember", "montag",
    "dienstag", "mittwoch", "donnerstag", "freitag", "samstag", "sonntag",
    "weihnachten", "ostern", "pfingsten", "silvester", "neujahr",
    "ostermontag", "pfingstmontag", "halloween", "fasching", "advent",
    "weihnachtsferien", "sommerferien", "herbstferien", "winterferien",
    "frühlingsferien", "fruehlingsferien",
}

# Nomen in festen Wendungen: Wendung (klein) -> kanonische Form
FIXED_PHRASES = {
    "in der regel": "in der Regel",
    "in der lage": "in der Lage",
    "in der tat": "in der Tat",
    "in der nähe": "in der Nähe",
    "in der folge": "in der Folge",
    "in der regel nicht": "in der Regel nicht",
    "im allgemeinen": "im Allgemeinen",
    "im einzelnen": "im Einzelnen",
    "im wesentlichen": "im Wesentlichen",
    "im großen und ganzen": "im Großen und Ganzen",
    "im folgenden": "im Folgenden",
    "im nachhinein": "im Nachhinein",
    "im zweifel": "im Zweifel",
    "im ernsten": "im Ernst",
    "im klaren": "im Klaren",
    "im reinen": "im Reinen",
    "im flusse": "im Fluss",
    "im grunde": "im Grunde",
    "im stande": "im Stande",
    "zum beispiel": "zum Beispiel",
    "zum fall": "zum Fall",
    "zumuten": "zumuten",
    "aufs neue": "aufs Neue",
    "zu recht": "zu Recht",
    "zu unrecht": "zu Unrecht",
    "zu gute": "zu Gute",
    "zu schulden": "zu Schulden",
    "mit sicherheit": "mit Sicherheit",
    "mit nachdruck": "mit Nachdruck",
    "mit vergnügen": "mit Vergnügen",
    "von zeit zu zeit": "von Zeit zu Zeit",
    "am leben": "am Leben",
    "am werk": "am Werk",
    "am herzen": "am Herzen",
    "am ehesten": "am ehesten",
    "des öfteren": "des Öfteren",
    "jeden fall": "jeden Fall",
    "einen schlussstrich": "einen Schlussstrich",
    "recht haben": "Recht haben",
    "im falle": "im Falle",
    "aus dem grunde": "aus dem Grunde",
    "erster mai": "Erster Mai",
    "am ersten mai": "am Ersten Mai",
}

# Nominalisierungen: nach diesen Präpositionalartikeln steht ein Nomen (gross)
NOMINAL_PREPS = ("zum", "zur", "beim", "ins", "ans", "aufs", "übers", "ums", "vom")

# Haueufige nominalisierte Verben (Infinitiv als Nomen)
VERBAL_NOUNS = set("""
sparen vergleichen wechseln rechnen buchen bestellen kündigen zahlen lesen
lernen wohnen leben essen trinken fahren heizen planen investieren anlegen
testen optimieren nutzen bezahlen überweisen teilen suchen finden bewerten
empfehlen kalkulieren verhandeln warten reparieren tauschen sortieren
aufräumen putzen tippen pinnen folgen drosseln vermeiden reduzieren erhöhen
abschließen beantragen verlängern umrüsten abheben einzahlen verzinsen
spitzen auswählen abwägen einrichten anpassen abwarten nachrüsten
""".split())

# Nominalisierte Adjektive (nach etwas/nichts/alles/dem/das … gross)
ADJ_NOMINAL_ENDINGS = ("es", "e", "er", "en", "em")


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------
def norm_brand_key(word: str) -> str:
    """Marken-Schluessel: klein, ohne Sonderzeichen/Leerzeichen, Umlaute aufgelöst."""
    w = word.lower().strip()
    w = (w.replace("ü", "ue").replace("ö", "oe").replace("ä", "ae")
         .replace("ß", "ss"))
    return re.sub(r"[^a-z0-9]", "", w)


def is_number_token(word: str) -> bool:
    return bool(re.fullmatch(r"[+\-]?[\d.,:/\-–%€$°]+", word.strip()))


# ---- Funktionswörter: Präpositionen, Artikel, Pronomen, Konjunktionen,
# Adverbien. Sie sind im Deutschen MID-SATZ immer klein und niemals ein Nomen –
# diese Liste ist der Grundstock fuer Regel C12 (Title-Case-Leak in
# Ueberschriften) und fuer die Konjugations-Ableitung unten.
FUNCTION_WORDS = """
als also an auf aus bei bis durch fuer für gegen hinter in im ins interim mit
nach neben ohne seit um unter von vor zu zum zur über überm zwischen
der die das dem den des ein eine einem einen einer eines kein keine keinen
keinem keiner keine mein meine meinen meinem meiner dein deine deinen deinem
deiner sein seine seinen seinem ihrer ihre ihren unser unsere euer eure
ihr ihre ihnen ich du er sie es wir ihr mich dich sich uns euch ihnen
jemand niemand man weder weder entweder oder aber und doch sondern jedoch
allerdings außerdem zudem deshalb daher darum dennoch trotzdem zwar nur schon
noch auch sogar selbst ebenso genauso beispielsweise nämlich eben halt mal
wenn dass damit sodass weil obwohl sofern falls während
wer was wann wo wohin woher warum weshalb wieso welcher welche welches
wie sohier hier dort draußen drinnen links rechts oben unten hinten vorne
zusammen allein gemeinsam lieber eher schnell langsam direkt sofort wirklich
natürlich eventuellen möglicherweise wahrscheinlich übrigens ebenso
alle beide mehrere etwas nichts viel wenig genug jeder jede jedes
immer niemals nie oft selten meist meistens insgesamt insgesamt insgesamt
heute morgen gestern jetzt damals später früher bald gerade eben
diesem dieser dieses diesen jener jenem welche solchen
aehnlich ähnlich gleichermaßen gleichermassen besonders vor allem
""".split()
LOWER |= {w for w in FUNCTION_WORDS if w.islower()}


VERBS = """
wirken behalten funktionieren gelingen erledigen eintragen austragen nachfragen
nachsehen nachschauen vergleichen abwägen abrechnen anzahlen einzahlen auszahlen
beantragen widersprechen kündigen verlängern reduzieren erhöhen prüfen testen
vergleichen wechseln sichern nutzen benötigen brauchen vermeiden reduzieren
optimieren starten stoppen verbinden trennen einrichten konfigurieren aktivieren
deaktivieren aktualisieren installieren herunterladen hochladen speichern
loslegen anfangen beginnen fortfahren aufhören einstellen vorbereiten nachrüsten
austauschen ersetzen reparieren warten prüfen kontrollieren dokumentieren
notieren festhalten feststellen überprüfen nachvollziehen berücksichtigen
einhalten durchführen durchführen sparen rechnen kalkulieren planen organisieren
kommunizieren vereinbaren abschließen schliessen öffnen schließen klicken
tippen halten geben nehmen sehen lesen schreiben sagen zeigen erklären
verstehen erinnern empfehlen raten lassen machen tun werden sein haben
""".split()
IRREGULAR = """
kann können muss müssen will wollen soll sollen mag mögen darfst sollst
hast hat habe bist seid bin wird werden wird wurde wurden geht gehen steht
stehen bringt bringen hilft finden sieht sehen liesst lesen fährt fahren
schläft schlafen trägt tragen nimmt nimm gib gibst
""".split()
LOWER |= set(VERBS) | {w for w in IRREGULAR if w.islower()}


def _fold(s: str) -> str:
    return (s.replace("\u00e4", "a").replace("\u00f6", "o")
             .replace("\u00fc", "u").replace("\u00df", "ss"))


def _verb_stems() -> set:
    """Stämme aus den INFINITIVEN der LOWER-Liste, damit konjugierte Formen
    („behältst“, „spart“, „vergleicht“) ebenfalls als Verb erkannt werden."""
    stems = set()
    for w in LOWER | set(VERBS):
        if len(w) < 4 or not w.endswith("n"):
            continue
        for cut in (0, 1, 2, 3):
            base = w[:len(w) - cut] if cut else w
            if len(base) >= 4:
                stems.add(_fold(base))
    return stems


VERB_STEMS = {s for s in _verb_stems() if len(s) >= 4}


def classify(word: str) -> tuple[str, str]:
    """(entscheidung, kanon) – entscheidung in {keep, upper, lower, acronym, brand, unknown}."""
    w = word.strip()
    if not w:
        return "keep", w
    lw = w.lower()
    if is_number_token(w):
        return "keep", w
    if lw in ACRONYMS:
        return "acronym", ACRONYMS[lw]
    key = norm_brand_key(w)
    if key in BRANDS:
        return "brand", BRANDS[key]
    if lw in UNITS:
        return "acronym", UNITS[lw]
    if lw in MONTHDAYS:
        return "upper", w[0].upper() + w[1:]
    if lw in LOWER:
        return "lower", lw
    # Konjugationen werden bewusst HIER nicht abgebogen: „Mieter“, „Wechsel“
    # und „Buchung“ sind Deverbativ-Nomen, die wie eine 2. Person aussehen.
    # Die schmale -st-Ableitung lebt in casing_guard (Regel C12), weil dort
    # zusaetzlich Nomen-Veto und Kontextregeln greifen.
    if lw in NOUNS:
        return "upper", w[0].upper() + w[1:]
    for suf in NOUN_SUFFIXES:
        if len(lw) >= len(suf) + 3 and lw.endswith(suf):
            return "upper", w[0].upper() + w[1:]
    return "unknown", w


def cap_first(word: str) -> str:
    return word[0].upper() + word[1:] if word else word


# ---------------------------------------------------------------------------
# Deppenleerzeichen: Nomen + Nomen werden im Deutschen zusammengeschrieben
# oder mit Bindestrich gekoppelt. Bewusst ENDE Liste (Kanonteile aus diesem
# Blog) – ein generisches Biegen wuerde legitime Fuegungen zerstoeren:
# „Strom sparen im Haushalt“, „Mietwagen vergleichen“, „Geld sparen am Monatsende“
# sind Verbwendungen und bleiben, wie sie sind. Akronytpaare („DSL Vergleich“)
# stehen nicht hier – die koppelt der Casing-Guard bereits ueber C3.
# ---------------------------------------------------------------------------
COMPOUND_JOIN = {
    "frugalismus tipps": "Frugalismus-Tipps",
    "frugalismus trick": "Frugalismus-Trick",
    "frugalismus tricks": "Frugalismus-Tricks",
    "heizung wartung": "Heizungswartung",
    "strom fresser": "Stromfresser",
    "mietwagen kaution": "Mietwagen-Kaution",
    "handytarif vergleich": "Handytarif-Vergleich",
    "gas rechnung": "Gasrechnung",
    "strom rechnung": "Stromrechnung",
}
_JOIN_RE = re.compile("|".join(re.escape(k) for k in
                               sorted(COMPOUND_JOIN, key=len, reverse=True)), re.I)


def join_compounds(text: str):
    """Komposita-Kanon einsetzen -> (text, geaendert).

    Idempotent: die Kanonform traegt kein Leerzeichen mehr im Treffermuster und
    wird deshalb nicht nochmals getroffen. Tags/Kategorien werden bewusst
    NICHT gebogen – dort ist die Leerzeichenform der Suchbegriff.
    """
    if not text:
        return text, False
    out = _JOIN_RE.sub(lambda m: COMPOUND_JOIN[m.group(0).lower()], text)
    return out, out != text


def slug_of(term: str) -> str:
    """Hugo-Taxonomie-Slug (naeherungsweise) – erkennt Term-Kollisionen."""
    s = (term.lower().replace("ä", "ae").replace("ö", "oe")
         .replace("ü", "ue").replace("ß", "ss"))
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def _segment(seg: str, first: bool) -> tuple[str, str | None]:
    """Ein Wort-/Kompositum-Segment; liefert (kanon, unbekannt|None)."""
    dec, kan = classify(seg)
    if dec == "unknown":
        return (cap_first(kan) if first else kan), kan
    if dec in ("acronym", "brand", "upper"):
        return kan, None
    if first and dec == "lower":
        return cap_first(kan), None
    return kan, None


def normalize_phrase(text: str, *, sentence_start: bool = True) -> tuple[str, list[str]]:
    """Einzelner Ausdruck (Tag, Kategorie, Pin-Titel-Segment) -> deutsche
    Schreibweise. Rueckgabe (text, notizen); notizen = unbekannte Woerter."""
    notes: list[str] = []
    if not text or not text.strip():
        return text, notes
    tokens = re.split(r"(\s+)", text.strip())
    out: list[str] = []
    wi = -1
    for tok in tokens:
        if tok == "" or tok.isspace():
            out.append(tok)
            continue
        wi += 1
        first = (wi == 0 and sentence_start)
        wrap = "()\"„“”'’«»,;:.!?[]{}"
        lead = len(tok) - len(tok.lstrip(wrap))
        trail_i = len(tok) - len(tok.rstrip(wrap))
        glue = tok[:lead]
        trail = tok[len(tok) - trail_i:] if trail_i else ""
        bare = tok[lead:len(tok) - trail_i] if trail_i else tok[lead:]
        if looks_like_slug(bare) or slug_is_file(bare):
            out.append(tok)                              # Pfade/URLs: heilig
            continue
        if "-" in bare:
            segs = re.split(r"(-)", bare)
            rebuilt: list[str] = []
            for seg in segs:
                if seg == "-":
                    rebuilt.append(seg)
                    continue
                if not seg:
                    continue
                val, note = _segment(seg, first and not rebuilt)
                if note:
                    notes.append(note)
                rebuilt.append(val)
            out.append(glue + "".join(rebuilt) + trail)
            continue
        val, note = _segment(bare, first)
        if note:
            notes.append(note)
        out.append(glue + val + trail)
    return "".join(out), notes


def slug_is_file(word: str) -> bool:
    return bool(re.search(r"\.(jpg|jpeg|png|webp|avif|svg|gif|mp4|pdf|html?)$", word, re.I))


def looks_like_slug(word: str) -> bool:
    """Post-Slugs/Dateinamen/Hostnamen erkennen („2026-08-19-dsl-vergleich-…").
    Veroeffentlichte URLs und Hostnamen sind sakrosankt: dort darf die
    Gross-/Kleinschreibung NIEMALS geaendert werden (404-Gefahr, Link-Gates)."""
    w = word.strip()
    if not w or "/" in w or w.startswith(("http", "@", ".")):
        return True
    if re.fullmatch(r"[a-z0-9äöüß]+(?:-[a-z0-9äöüß]+){2,}", w):
        return True
    if re.fullmatch(r"[a-z0-9äöüß-]+\.(?:de|com|net|org|io|eu|app|cloud|box|one)", w, re.I):
        return True
    return False


def normalize_terms(items: list[str]) -> tuple[list[str], bool, list[str]]:
    """Tags/Kategorien: normalisieren, danach Duplikate (gleicher Slug) entfernen."""
    notes: list[str] = []
    seen: dict[str, str] = {}
    for it in items:
        norm, n = normalize_phrase(it)
        notes += n
        key = slug_of(norm)
        if key and key not in seen:
            seen[key] = norm
    out = list(seen.values())
    return out, (out != [i.strip() for i in items]), notes


# ---------------------------------------------------------------------------
# Selbsttest: der Klassifikator muss die im Bestand bereits KORREKT
# geschriebenen Ausdruecke exakt reproduzieren – sonst ist das Lexikon kaputt.
# ---------------------------------------------------------------------------
SELFTEST_CASES = [
    ("geld sparen im alltag", "Geld sparen im Alltag"),
    ("Geld sparen im Alltag", "Geld sparen im Alltag"),
    ("frugalismus tipps", "Frugalismus Tipps"),
    ("stromfresser finden", "Stromfresser finden"),
    ("50 30 20 Regel", "50 30 20 Regel"),
    ("Haushaltsbuch App", "Haushaltsbuch App"),
    ("haushaltsbuch führen", "Haushaltsbuch führen"),
    ("fritzbox", "FRITZ!Box"),
    ("dsl vergleich", "DSL Vergleich"),
    # Tag = Suchbegriff: Nomen werden gross, aber das Komposita wird nicht
    # zusammengeschrieben (Leerzeichen-Form bleibt, URL und IndexNow ruhen).
    ("heizung wartung", "Heizung Wartung"),
    ("flugtickets günstig", "Flugtickets günstig"),
    ("heizung warten", "Heizung warten"),
    ("handytarif vergleichen", "Handytarif vergleichen"),
    ("congstar", "congstar"),
    ("idealo", "idealo"),
    ("zinsen vergleichen", "Zinsen vergleichen"),
    ("Checkliste Herbst", "Checkliste Herbst"),
    ("winter vorbereitung wohnung", "Winter Vorbereitung Wohnung"),
    ("standby kosten", "Standby Kosten"),
    ("dns hack", "DNS Hack"),
    ("vermögen aufbauen", "Vermögen aufbauen"),
    ("günstiges internet", "Günstiges Internet"),
    ("kostenloses girokonto", "Kostenloses Girokonto"),
    ("solaranlage", "Solaranlage"),
]
JOIN_CASES = [
    ("Frugalismus Tipps für den Einstieg", "Frugalismus-Tipps für den Einstieg"),
    ("Heizung wartung: So bereitest du dein Heim vor",
     "Heizungswartung: So bereitest du dein Heim vor"),
    ("frugalismus tipps", "Frugalismus-Tipps"),
    ("Strom sparen im Haushalt", "Strom sparen im Haushalt"),
    ("Mietwagen vergleichen und Kaution prüfen", "Mietwagen vergleichen und Kaution prüfen"),
    ("Welche weiteren Strom sparen Tipps helfen sofort?",
     "Welche weiteren Strom sparen Tipps helfen sofort?"),
]

PROTECT_CASES = [
    "https://www.check24.de/dsl",
    "images/covers/2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier.jpg",
    "/go/dsl/",
    "2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet",
]


def selftest() -> list[str]:
    """Liste der Fehler; leer = alles gruen."""
    fehler: list[str] = []
    for src, want in SELFTEST_CASES:
        got, _ = normalize_phrase(src)
        if got != want:
            fehler.append(f"Tag-Kanon: {src!r} -> {got!r}, erwartet {want!r}")
        again, _ = normalize_phrase(got)
        if again != got:
            fehler.append(f"Nicht idempotent: {src!r} -> {got!r} -> {again!r}")
    for src in PROTECT_CASES:
        got, _ = normalize_phrase(src)
        if got != src:
            fehler.append(f"Schutzverletzung: {src!r} -> {got!r}")
    for src, want in JOIN_CASES:
        got, _ = join_compounds(src)
        if got != want:
            fehler.append(f"Komposita: {src!r} -> {got!r}, erwartet {want!r}")
        again, _ = join_compounds(got)
        if again != got:
            fehler.append(f"Komposita nicht idempotent: {src!r}")
    return fehler


def main() -> int:
    if "--selftest" in sys.argv:
        f = selftest()
        if f:
            print("🛑 TAG-CASING-SELBSTTEST FEHLGESCHLAGEN:")
            print("\n".join("   " + x for x in f))
            return 2
        print(f"✅ Tag-Casing-Selbsttest: {len(SELFTEST_CASES)} Faelle gruen, "
              f"{len(PROTECT_CASES)} Schutzfaelle + {len(JOIN_CASES)} "
              "Komposita-Faelle gruen.")
        return 0
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        return 0
    for a in args:
        out, notes = normalize_phrase(a)
        tail = f"   (unbekannt: {', '.join(sorted(set(notes)))})" if notes else ""
        print(f"{a!r:44} -> {out!r}{tail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
