#!/usr/bin/env python3
# ============================================================
#  AFFILIATE-INTENT-CONTRACT – die zentrale Angebots-Wahrheit
#  (Premium-Reparatur 19.09.2026, Auftrag Frank: „Falsche Affiliate-
#   Ziele sofort reparieren … automatische Intent-Wache … dauerhaft
#   auf dem Niveau einer Profi-Agentur.")
#
#  ------------------------------------------------------------
#  WOFÜR DIESE DATEI DA IST
#
#  Bis 19.09.2026 wusste das System ZWAR, welche /go/-Route registriert
#  ist und ob sie technisch weiterleitet (affiliate_health.py H1–H4,
#  affiliate_integrity_gate.py AI1–AI5) – aber NICHT, welches ANGEBOT
#  hinter einer Route steht und welches Angebot ein Anker/Artikel
#  VERSPRICHT. Genau in dieser Lücke entstanden die Funde vom 19.09.:
#
#    · Kfz-Artikel, Top-CTA „Kfz-Versicherung vergleichen“ → /go/haftpflicht/
#    · Girokonto-Artikel, „Kostenlos vergleichen“          → /go/kredit/
#    · Kreditkarten-Artikel, „Tarifrechner starten“        → /go/reisekrankenversicherung/
#    · Mietwagen-Ratgeber, erster + letzter CTA            → /go/kfz-versicherung/
#    · „Tagesgeldvergleich“                                → C24 Bank (Einzelanbieter)
#    · „Flüge“                                             → Pauschalreise-Angebot
#    · Wohngebäudeversicherung                             → Hausrat
#
#  Jeder dieser Links war „grün“: registriert, 200, rel=sponsored,
#  im HTML bewiesen. Nur das VERSPRECHEN an den Besucher war falsch –
#  ein Interessent mit Kaufabsicht landete bei einem anderen Produkt.
#  Das ist die teuerste Affiliate-Sünde überhaupt (Trust, Conversion,
#  und rechtlich § 5a UWG: irreführende kommerzielle Handlung).
#
#  Dieser Kontrakt ist die EINZIGE Quelle für:
#    1. was hinter einer Route wirklich steht (Partner, Produkt,
#       Zielseite, Abweichung vom naheliegenden Namen),
#    2. welcher Anker/Artikel-Text zu welcher Route gehört (THEMEN_REIHE),
#    3. welche Anker-Texte ehrlich sind (ANKER je Slot),
#    4. welche Paare NIEMALS zusammen dürfen (NIE_PAARE),
#    5. welche Namen Gateway-Seite, Tooltip und Datendatei tragen
#       MÜSSEN (anzeige / gateway).
#
#  Verbraucher:
#    · scripts/affiliate_intent_guard.py  (Intent-Wache IW0–IW9)
#    · scripts/affiliate_marketer.py      (CTA-Erzeugung, DEEP_HINTS)
#    · scripts/affiliate_shield.py        (Gateway-Namen)
#    · scripts/affiliate_health.py        (ROUTE_CONTRACT-Erwartung)
#    · data/affiliate_ziele.yaml          (generiert, für Hugo-Templates)
#
#  Regeln für Änderungen (Profi-Agentur-Standard):
#    · Kein Produkt ohne Partner-Programm: Eine Route wird NUR angelegt,
#      wenn die Deep-Link-Kette E2E verifiziert ist (affiliate_health.py).
#      Erraten ist verboten – lieber ehrlich umbenennen (siehe „fluege“).
#    · Jede ABWEICHUNG zwischen Route-Namen und wirklichem Angebot muss
#      als `Abweichung` erfasst sein, mit Pflicht-Nennung im Anker.
#    · `python3 scripts/affiliate_intent_guard.py --selftest` und
#      `python3 scripts/affiliate_marketer.py --selftest`-Äquivalent
#      (run_selftest) müssen grün bleiben: Die eingefrorenen Vorfälle
#      sind Regressionstests, keine Deko.
# ============================================================

from __future__ import annotations

import re
from dataclasses import dataclass, field

# ------------------------------------------------------------
# Bausteine
# ------------------------------------------------------------


@dataclass(frozen=True)
class Abweichung:
    """Dokumentierte Lücke zwischen Route-Namen und wirklichem Angebot.

    art      : "einzelanbieter" – Route klingt nach Marktvergleich, landet
                                 aber bei EINER Bank/einem Anbieter.
               "buendelung"     – Route klingt nach Einzelprodukt, das
                                 Partnerprogramm bündelt es in ein Paket.
               "portal"         – Route ist der Portal-Fallback ohne Fach.
    ziel     : was der Besucher WIRKLICH bekommt (Klartext, für Report/Issue)
    pflicht  : Wörter, von denen MINDESTENS EINES im Anker bzw. in der
               CTA-Zeile stehen muss (Ehrlichkeits-Nennung, Frank-Regel
               11.08.: „Bei C24-Verlinkung immer C24 Bank nennen“).
    verbot   : Versprechen, die im Anker NICHT stehen dürfen, weil das
               Ziel sie nicht einlöst (z. B. reiner Flugvergleich).
    grund    : Herkunft/Beleg der Abweichung (Partnerprogramm-Fakt).
    """

    art: str
    ziel: str
    pflicht: tuple[str, ...] = ()
    verbot: tuple[str, ...] = ()
    grund: str = ""
    anhang: str = ""     # grammatisch sicherer Anhang für In-Text-Anker
    hinweis: str = ""    # Klartext für Report/Issue/Tooltip-Zusatz
    # satz_verbot: Wörter, die schon den UMGEBENDEN SATZ unehrlich machen,
    # selbst wenn der Anker den Partner korrekt nennt („Vergleiche jetzt
    # führende gebührenfreie Girokonten … C24 Bank" verspricht Auswahl,
    # die es nicht gibt). Bewusst NICHT für Bündel-Abweichungen: Der
    # CHECK24-Pauschalreise-Vergleich VERGLEICHT wirklich – dort wäre
    # „vergleich" ein Fehlalarm (Satz „Jetzt Pauschalreisen mit Flug
    # vergleichen" ist ehrlich).
    satz_verbot: tuple[str, ...] = ()


@dataclass(frozen=True)
class Ziel:
    """Ein registriertes Affiliate-Ziel – Angebots-Wahrheit pro Route."""

    key: str
    partner: str                       # CHECK24 | C24 Bank | Tarifcheck
    produkt: str                       # was beworben wird (Klartext)
    anzeige: str                       # Tooltip/Title im Render-Hook
    gateway: str                       # Name auf der /go/-Übergabeseite
    landing: str                       # Zielseite in Worten (Report/Issue)
    anker: dict[str, tuple[str, ...]] = field(default_factory=dict)
    abweichung: Abweichung | None = None
    netz: str = ""                     # check24 | tarifcheck (für Health-Check)
    saetze: dict[str, str] = field(default_factory=dict)
    # Dativ-Phrase für die Übergabeseite static/go/<route>/: „Weiter {phrase}".
    # Bewusst als Phrase und nicht als Name: „Weiter zu C24 Bank" ist
    # gebrochenes Deutsch, „Weiter zum Tagesgeld der C24 Bank" nicht. Die
    # Gateway-Seite sieht JEDER Affiliate-Klick – sie ist die teuerste
    # Textfläche des Blogs (Vertrauen im Moment des Klicks).
    weiter_zu: str = ""
    # ^ Ehrliche CTA-Sätze je Slot (top/mid/end). NUR bei Abweichung nötig:
    #   Dann verspricht schon der SATZ ein Angebot, das es so nicht gibt
    #   („Die besten Tarife findest du über unseren Partner-Vergleich“ auf
    #   einer Route, die zu EINER Bank führt). Die Wache ersetzt in dem Fall
    #   die ganze CTA-Zeile aus diesem Satz + `anker` – nie per Textflicken.

    def ziel_phrase(self) -> str:
        """Grammatisch fertige Übergabe-Phrase für die Gateway-Seite."""
        return self.weiter_zu or f"zu {self.gateway}"

    def anker_fuer(self, slot: str, stabilisator: str = "") -> str:
        """Ehrlicher Anker für einen CTA-Slot (top/mid/end/intext).

        `stabilisator` (Artikel-Slug) wählt deterministisch eine Variante:
        stabil über Läufe (kein täglicher Churn, Idempotenz der Wache) und
        trotzdem variantenreich über Artikel hinweg (AM4 „Christologie“:
        nicht überall dieselbe Phrase).
        """
        varianten = self.anker.get(slot) or self.anker.get("intext") or ()
        if not varianten:
            return f"Jetzt {self.produkt} ansehen"
        if len(varianten) == 1 or not stabilisator:
            return varianten[0]
        return varianten[sum(ord(c) for c in stabilisator) % len(varianten)]

    def satz_ehrlich(self, text: str) -> tuple[bool, str]:
        """Prüft den SATZ (ohne Haus-Marker) auf Versprechen, die das Ziel
        nicht einlöst – z. B. „Vergleich" bei einem Einzelanbieter-Angebot.

        Getrennt von `ehrlich()`, weil die Marker („Jetzt vergleichen und
        sparen:") Hausstil sind und von affiliate_integrity_gate.py (AI1/AI3),
        dash_guard und umbruch_guard erkannt werden: Ein Marker darf nicht
        umgeschrieben werden, ein Satz schon.
        """
        if not self.abweichung or not self.abweichung.satz_verbot:
            return True, ""
        low = (text or "").lower()
        for wort in self.abweichung.satz_verbot:
            if wort.lower() in low:
                return False, (f"Satz verspricht „{wort}“, das Ziel liefert "
                               f"aber {self.abweichung.ziel}")
        return True, ""

    def ehrlich(self, text: str) -> tuple[bool, str]:
        """Prüft einen Anker/eine CTA-Zeile auf Ehrlichkeit (Abweichung).

        Rückgabe: (ok, grund). Ohne Abweichung ist jeder Text ok – dann
        gilt die Produkt-Deckung (IW1) als Ehrlichkeitsbeweis.
        """
        if not self.abweichung:
            return True, ""
        low = (text or "").lower()
        for wort in self.abweichung.verbot:
            if wort.lower() in low:
                return False, (f"Anker verspricht „{wort}“, das Ziel liefert "
                               f"aber {self.abweichung.ziel}")
        if self.abweichung.pflicht and not any(
                w.lower() in low for w in self.abweichung.pflicht):
            namen = " / ".join(self.abweichung.pflicht)
            return False, (f"Ziel ist {self.abweichung.ziel} – der Anker muss "
                           f"das nennen ({namen})")
        return True, ""


# ------------------------------------------------------------
# DIE ZIELE (Stand 19.09.2026)
#
# Reihenfolge ist alphabetisch nach Route; die SPEZIFITÄT steht in
# THEMEN_REIHE unten (dort entscheidet die Reihenfolge).
# ------------------------------------------------------------

_C24 = Abweichung(
    art="einzelanbieter",
    ziel="ein Angebot der C24 Bank (CHECK24-Tochter), kein Marktvergleich",
    pflicht=("C24",),
    grund=("CHECK24-Partnerprogramm hat keinen Girokonto-/Tagesgeld-Vergleich: "
           "der offizielle Deep ist c24bank&cat=14 (Frank, 11.08.2026)."),
    anhang=" der C24 Bank",
    hinweis=("Angebot der C24 Bank (CHECK24-Tochter) – kein Vergleich "
             "mehrerer Banken."),
    satz_verbot=("vergleich", "marktüberblick", "marktueberblick", "testsieger"),
)

_FLUG = Abweichung(
    art="buendelung",
    ziel="der CHECK24-Pauschalreise-Vergleich (Flug nur im Paket mit Hotel)",
    pflicht=("Pauschalreise", "Urlaubspaket", "Flug + Hotel", "Flug und Hotel"),
    verbot=("Flugvergleich", "Flüge vergleichen", "Flugtickets vergleichen",
            "Billigflüge", "Flugpreise vergleichen"),
    grund=("Es gibt im CHECK24-Partnerprogramm KEINEN Flug-Deep-Link: "
           "deep=fluege landet E2E auf check24.net/fluege/ = 404 (geprüft "
           "19.09.2026), offizieller Flug-Deep ist pauschalreisen-vergleich "
           "&cat=9 (Frank, 11.08.2026). Also: ehrlich als Paket benennen."),
    anhang=" (Flug im Paket)",
    hinweis=("Partner-Angebot ist der Pauschalreise-Vergleich – der Flug "
             "kommt im Paket mit dem Hotel, nicht als Einzel-Flugtarif."),
)

_PORTAL = Abweichung(
    art="portal",
    ziel="die CHECK24-Portalstartseite (alle Vergleiche, kein Fach-Rechner)",
    pflicht=(),
    verbot=(),
    grund=("Bewusster Fallback für Themen ohne eigenes Fach-Deep (z. B. "
           "Frugalismus/Budget). Der Anker darf dann KEIN Einzelprodukt "
           "nennen – sonst gilt IW1 (Anker nennt Produkt → Route falsch)."),
    anhang="",
    hinweis="CHECK24-Portalstartseite (kein Fach-Rechner).",
)

ZIELE: dict[str, Ziel] = {z.key: z for z in (
    Ziel(
        key="allgemein",
        partner="CHECK24",
        produkt="CHECK24-Vergleichsportal",
        anzeige="CHECK24-Vergleichsportal (Startseite)",
        gateway="CHECK24-Vergleichsportal",
        weiter_zu="zum CHECK24-Vergleichsportal (Startseite)",
        landing="check24.net – Portalstartseite",
        netz="check24",
        abweichung=_PORTAL,
        anker={
            "top": ("Jetzt Fixkosten auf CHECK24 prüfen",
                    "CHECK24-Vergleichsportal öffnen"),
            "mid": ("Fixkosten auf CHECK24 prüfen",),
            "end": ("→ Jetzt Fixkosten auf CHECK24 prüfen",),
            "intext": ("CHECK24-Vergleichsportal",),
        },
    ),
    Ziel(
        key="strom",
        partner="CHECK24",
        produkt="Stromtarife",
        anzeige="CHECK24 · Stromtarife",
        gateway="CHECK24",
        weiter_zu="zu den CHECK24-Stromtarifen",
        landing="check24.net/stromanbieter-wechseln/",
        netz="check24",
        anker={
            "top": ("Jetzt Stromtarife vergleichen",
                    "Stromanbieter vergleichen & wechseln"),
            "mid": ("Jetzt Stromtarife vergleichen",
                    "Stromanbieter vergleichen & sparen"),
            "end": ("→ Jetzt Stromtarife vergleichen",
                    "→ Stromanbieter vergleichen & wechseln"),
            "intext": ("Stromtarife vergleichen", "Stromanbieter vergleichen"),
        },
    ),
    Ziel(
        key="gas",
        partner="CHECK24",
        produkt="Gastarife",
        anzeige="CHECK24 · Gastarife",
        gateway="CHECK24",
        weiter_zu="zu den CHECK24-Gastarifen",
        landing="check24.net/gasanbieter-wechseln/",
        netz="check24",
        anker={
            "top": ("Jetzt Gastarife vergleichen",
                    "Gas-Anbieter vergleichen & wechseln"),
            "mid": ("Jetzt Gastarife vergleichen",
                    "Gas-Anbieter vergleichen & sparen"),
            "end": ("→ Jetzt Gastarife vergleichen",
                    "→ Gas-Anbieter vergleichen & wechseln"),
            "intext": ("Gastarife vergleichen", "Gasanbieter vergleichen"),
        },
    ),
    Ziel(
        key="dsl",
        partner="CHECK24",
        produkt="DSL- & Internettarife",
        anzeige="CHECK24 · DSL & Internet",
        gateway="CHECK24",
        weiter_zu="zum CHECK24-DSL- und Internetvergleich",
        landing="check24.net/dsl-anbieterwechsel/",
        netz="check24",
        anker={
            "top": ("Jetzt DSL-Tarife vergleichen",
                    "Internet & DSL vergleichen"),
            "mid": ("Jetzt DSL-Tarife vergleichen",
                    "DSL-Tarif prüfen & sparen"),
            "end": ("→ Jetzt DSL-Tarife vergleichen",
                    "→ Internet & DSL vergleichen"),
            "intext": ("DSL-Vergleich", "DSL-Tarife vergleichen"),
        },
    ),
    Ziel(
        key="handytarife",
        partner="CHECK24",
        produkt="Handytarife",
        anzeige="CHECK24 · Handytarife",
        gateway="CHECK24",
        weiter_zu="zu den CHECK24-Handytarifen",
        landing="check24.net/handytarife/",
        netz="check24",
        anker={
            "top": ("Jetzt Handytarife vergleichen",),
            "mid": ("Jetzt Handytarife vergleichen",),
            "end": ("→ Jetzt Handytarife vergleichen",),
            "intext": ("Handytarife vergleichen",),
        },
    ),
    Ziel(
        key="mietwagen",
        partner="CHECK24",
        produkt="Mietwagen",
        anzeige="CHECK24 · Mietwagen",
        gateway="CHECK24",
        weiter_zu="zum CHECK24-Mietwagenvergleich",
        landing="check24.net/mietwagen-preisvergleich/",
        netz="check24",
        anker={
            "top": ("Jetzt Mietwagen vergleichen",
                    "Mietwagen mit Vollkasko vergleichen"),
            "mid": ("Jetzt Mietwagen vergleichen",),
            "end": ("→ Jetzt Mietwagen vergleichen",
                    "→ Mietwagen mit Vollkasko ohne Selbstbeteiligung vergleichen"),
            "intext": ("Mietwagen vergleichen", "Mietwagen-Preisvergleich"),
        },
    ),
    Ziel(
        key="reisen",
        partner="CHECK24",
        produkt="Pauschalreisen",
        anzeige="CHECK24 · Pauschalreisen & Urlaub",
        gateway="CHECK24",
        weiter_zu="zu den CHECK24-Pauschalreisen",
        landing="check24.net/pauschalreisen-vergleich/",
        netz="check24",
        anker={
            "top": ("Jetzt Pauschalreisen vergleichen",
                    "Reiseangebote vergleichen"),
            "mid": ("Jetzt Pauschalreisen vergleichen",),
            "end": ("→ Jetzt Pauschalreisen vergleichen",
                    "→ Reiseangebote vergleichen"),
            "intext": ("Pauschalreisen vergleichen", "Reiseangebote vergleichen"),
        },
    ),
    Ziel(
        key="fluege",
        partner="CHECK24",
        produkt="Pauschalreisen mit Flug",
        anzeige="CHECK24 · Pauschalreisen (Flug im Paket)",
        gateway="CHECK24 Pauschalreisen (Flug im Paket)",
        weiter_zu="zu den CHECK24-Pauschalreisen (Flug im Paket)",
        landing="check24.net/pauschalreisen-vergleich/ (Flug nur im Paket)",
        netz="check24",
        abweichung=_FLUG,
        saetze={
            "top": ("Unser Partner vergleicht keine Einzelflüge, wohl aber "
                    "Pauschalreisen mit Flug und Hotel – im Paket oft "
                    "günstiger als getrennt gebucht"),
            "mid": ("Flug und Hotel als Paket buchst du in wenigen Minuten"),
            "end": ("Jetzt Pauschalreisen mit Flug vergleichen"),
        },
        anker={
            "top": ("Pauschalreise mit Flug vergleichen",
                    "Flug + Hotel im Paket vergleichen"),
            "mid": ("Pauschalreise mit Flug vergleichen",),
            "end": ("→ Pauschalreise mit Flug vergleichen",
                    "→ Flug + Hotel als Urlaubspaket vergleichen"),
            "intext": ("Pauschalreise mit Flug vergleichen",),
        },
    ),
    Ziel(
        key="girokonto",
        partner="C24 Bank",
        produkt="Girokonto der C24 Bank",
        anzeige="C24 Bank (CHECK24) · Girokonto",
        gateway="C24 Bank (von CHECK24)",
        weiter_zu="zum Girokonto der C24 Bank (CHECK24-Tochter)",
        landing="check24.net/c24bank/ – Girokonto der C24 Bank",
        netz="check24",
        abweichung=_C24,
        saetze={
            "top": ("Ein dauerhaft kostenloses Girokonto mit Verzinsung "
                    "bekommst du bei der C24 Bank (CHECK24-Tochter)"),
            "mid": ("Das kostenlose Girokonto der C24 Bank ist in Minuten "
                    "eröffnet"),
            "end": ("Jetzt das Girokonto der C24 Bank ansehen"),
        },
        anker={
            "top": ("Jetzt C24 Bank Girokonto ansehen",
                    "Kostenloses C24 Girokonto eröffnen"),
            "mid": ("Jetzt C24 Bank Girokonto ansehen",),
            "end": ("→ Jetzt C24 Bank Girokonto ansehen",
                    "→ Kostenloses Girokonto bei der C24 Bank eröffnen"),
            "intext": ("C24 Bank Girokonto", "Girokonto der C24 Bank"),
        },
    ),
    Ziel(
        key="tagesgeld",
        partner="C24 Bank",
        produkt="Tagesgeld der C24 Bank",
        anzeige="C24 Bank (CHECK24) · Tagesgeld",
        gateway="C24 Bank (von CHECK24)",
        weiter_zu="zum Tagesgeld der C24 Bank (CHECK24-Tochter)",
        landing="check24.net/c24bank/ – Tagesgeld/Konto der C24 Bank",
        netz="check24",
        abweichung=_C24,
        saetze={
            "top": ("Aktuelle Zinsen auf ein kostenloses Tagesgeldkonto gibt "
                    "es bei der C24 Bank (CHECK24-Tochter)"),
            "mid": ("Dein Tagesgeld liegt bei der C24 Bank verzinst und "
                    "täglich verfügbar"),
            "end": ("Jetzt das Tagesgeld-Angebot der C24 Bank ansehen"),
        },
        anker={
            "top": ("Jetzt C24 Bank Tagesgeld ansehen",
                    "Tagesgeldkonto der C24 Bank eröffnen"),
            "mid": ("Jetzt C24 Bank Tagesgeld ansehen",
                    "C24 Bank Tagesgeld-Zinsen ansehen"),
            "end": ("→ Jetzt C24 Bank Tagesgeld ansehen",
                    "→ Tagesgeld der C24 Bank eröffnen"),
            "intext": ("C24 Bank Tagesgeld", "Tagesgeld der C24 Bank"),
        },
    ),
    Ziel(
        key="kredit",
        partner="CHECK24",
        produkt="Ratenkredit",
        anzeige="CHECK24 · Kreditvergleich",
        gateway="CHECK24",
        weiter_zu="zum CHECK24-Kreditvergleich",
        landing="check24.net/kredit-vergleich/",
        netz="check24",
        anker={
            "top": ("Jetzt Kreditangebote prüfen", "Ratenkredit vergleichen"),
            "mid": ("Jetzt Kreditangebote prüfen",),
            "end": ("→ Jetzt Kreditangebote prüfen", "→ Ratenkredit vergleichen"),
            "intext": ("Kreditvergleich", "Kreditangebote prüfen"),
        },
    ),
    Ziel(
        key="kreditkarte",
        partner="CHECK24",
        produkt="Kreditkarten",
        anzeige="CHECK24 · Kreditkarten",
        gateway="CHECK24",
        weiter_zu="zum CHECK24-Kreditkartenvergleich",
        landing="check24.net/kreditkarte/",
        netz="check24",
        anker={
            "top": ("Jetzt Kreditkarten vergleichen",
                    "Kostenlose Kreditkarte finden"),
            "mid": ("Jetzt Kreditkarten vergleichen",),
            "end": ("→ Jetzt Kreditkarten vergleichen",
                    "→ Kostenlose Kreditkarte finden"),
            "intext": ("Kreditkarten vergleichen", "Kreditkarten-Vergleich"),
        },
    ),
    Ziel(
        key="kfz-versicherung",
        partner="CHECK24",
        produkt="Kfz-Versicherung",
        anzeige="CHECK24 · Kfz-Versicherung",
        gateway="CHECK24",
        weiter_zu="zum CHECK24-Kfz-Versicherungsvergleich",
        landing="check24.net/kfz-versicherung/",
        netz="check24",
        anker={
            "top": ("Jetzt Kfz-Versicherung vergleichen",
                    "Kfz-Versicherung prüfen & sparen"),
            "mid": ("Jetzt Kfz-Versicherung vergleichen",),
            "end": ("→ Jetzt Kfz-Versicherung vergleichen",
                    "→ Kfz-Versicherung 2026 vergleichen"),
            "intext": ("Kfz-Versicherung vergleichen", "Kfz-Versicherungs-Vergleich"),
        },
    ),
    Ziel(
        key="haftpflicht",
        partner="Tarifcheck",
        produkt="Privathaftpflicht",
        anzeige="Tarifcheck · Privathaftpflicht",
        gateway="Tarifcheck",
        weiter_zu="zum Tarifcheck-Privathaftpflichtvergleich",
        landing="tarifcheck.de/haftpflichtversicherung/",
        netz="tarifcheck",
        anker={
            "top": ("Jetzt Haftpflichtversicherung vergleichen",
                    "Privathaftpflicht prüfen & sparen"),
            "mid": ("Jetzt Haftpflichtversicherung vergleichen",),
            "end": ("→ Jetzt Haftpflichtversicherung vergleichen",
                    "→ Privathaftpflicht-Tarife vergleichen"),
            "intext": ("Haftpflichtversicherung vergleichen", "Privathaftpflicht vergleichen"),
        },
    ),
    Ziel(
        key="hausrat",
        partner="Tarifcheck",
        produkt="Hausratversicherung",
        anzeige="Tarifcheck · Hausratversicherung",
        gateway="Tarifcheck",
        weiter_zu="zum Tarifcheck-Hausratvergleich",
        landing="tarifcheck.de/hausratversicherung/",
        netz="tarifcheck",
        anker={
            "top": ("Jetzt Hausratversicherung vergleichen",
                    "Hausratversicherung prüfen & sparen"),
            "mid": ("Jetzt Hausratversicherung vergleichen",),
            "end": ("→ Jetzt Hausratversicherung vergleichen",
                    "→ Hausrat-Tarife vergleichen"),
            "intext": ("Hausratversicherung vergleichen",),
        },
    ),
    Ziel(
        key="wohngebaeudeversicherung",
        partner="Tarifcheck",
        produkt="Wohngebäudeversicherung",
        anzeige="Tarifcheck · Wohngebäudeversicherung",
        gateway="Tarifcheck",
        weiter_zu="zum Tarifcheck-Wohngebäudevergleich",
        landing="tarifcheck.de/wohngebaeudeversicherung/",
        netz="tarifcheck",
        anker={
            "top": ("Jetzt Wohngebäudeversicherung vergleichen",
                    "Gebäudeversicherung prüfen & sparen"),
            "mid": ("Jetzt Wohngebäudeversicherung vergleichen",),
            "end": ("→ Jetzt Wohngebäudeversicherung vergleichen",
                    "→ Wohngebäude-Tarife vergleichen"),
            "intext": ("Wohngebäudeversicherung vergleichen", "Gebäudeversicherung vergleichen"),
        },
    ),
    Ziel(
        key="unfallversicherung",
        partner="Tarifcheck",
        produkt="Unfallversicherung",
        anzeige="Tarifcheck · Unfallversicherung",
        gateway="Tarifcheck",
        weiter_zu="zum Tarifcheck-Unfallversicherungsvergleich",
        landing="tarifcheck.de/unfallversicherung/",
        netz="tarifcheck",
        anker={
            "top": ("Jetzt Unfallversicherung vergleichen",),
            "mid": ("Jetzt Unfallversicherung vergleichen",),
            "end": ("→ Jetzt Unfallversicherung vergleichen",),
            "intext": ("Unfallversicherung vergleichen",),
        },
    ),
    Ziel(
        key="reisekrankenversicherung",
        partner="Tarifcheck",
        produkt="Reisekrankenversicherung",
        anzeige="Tarifcheck · Reisekrankenversicherung",
        gateway="Tarifcheck",
        weiter_zu="zum Tarifcheck-Reisekrankenvergleich",
        landing="tarifcheck.de/reisekrankenversicherung/",
        netz="tarifcheck",
        anker={
            "top": ("Jetzt Reisekrankenversicherung vergleichen",),
            "mid": ("Jetzt Reisekrankenversicherung vergleichen",),
            "end": ("→ Jetzt Reisekrankenversicherung vergleichen",),
            "intext": ("Reisekrankenversicherung vergleichen",
                      "Auslandsreise-Absicherung vergleichen"),
        },
    ),
    Ziel(
        key="zahnzusatzversicherung",
        partner="Tarifcheck",
        produkt="Zahnzusatzversicherung",
        anzeige="Tarifcheck · Zahnzusatzversicherung",
        gateway="Tarifcheck",
        weiter_zu="zum Tarifcheck-Zahnzusatzvergleich",
        landing="tarifcheck.de/zahnzusatzversicherung/",
        netz="tarifcheck",
        anker={
            "top": ("Jetzt Zahnzusatzversicherung vergleichen",),
            "mid": ("Jetzt Zahnzusatzversicherung vergleichen",),
            "end": ("→ Jetzt Zahnzusatzversicherung vergleichen",),
            "intext": ("Zahnzusatzversicherung vergleichen",),
        },
    ),
    Ziel(
        key="hunde",
        partner="Tarifcheck",
        produkt="Tierkrankenversicherung",
        anzeige="Tarifcheck · Tierkrankenversicherung",
        gateway="Tarifcheck",
        weiter_zu="zum Tarifcheck-Tierkrankenvergleich",
        landing="tarifcheck.de/hundekrankenversicherung/",
        netz="tarifcheck",
        anker={
            "top": ("Jetzt Tierkrankenversicherung vergleichen",),
            "mid": ("Jetzt Tierkrankenversicherung vergleichen",),
            "end": ("→ Jetzt Tierkrankenversicherung vergleichen",),
            "intext": ("Tierkrankenversicherung vergleichen",
                      "Hundekrankenversicherung vergleichen"),
        },
    ),
)}

# ------------------------------------------------------------
# THEMEN_REIHE – Spezifitäts-geordnete Zuordnung Text → Route.
#
# Herkunft: DEEP_HINTS aus affiliate_marketer.py (seit 11.08.2026
# eingefroren, 23 Selbsttest-Fälle) – hierher gezogen, damit Artikel-
# thema, Anker-Intent und CTA-Erzeugung AUS EINER QUELLE kommen.
# affiliate_marketer.DEEP_HINTS ist jetzt eine Ableitung dieser Reihe
# (run_selftest() dort bleibt der Regressionstest).
#
# Reihenfolge = Spezifität (Supertrumpf zuerst). Kein übergreifendes
# Alltagswort darf vor einem Fachbegriff stehen.
# ------------------------------------------------------------

THEMEN_REIHE: tuple[tuple[str, str], ...] = (
    (r"unfall", "unfallversicherung"),
    (r"tierkranken|hundekranken|katzenkranken|pferdekranken|tierversicherung"
     r"|hundeversicherung|katzenversicherung|tier[- ]?op[- ]?versicherung", "hunde"),
    (r"reisekranken|auslandsreise|auslandskranken", "reisekrankenversicherung"),
    (r"zahn", "zahnzusatzversicherung"),
    # 19.09.2026 (Intent-Wache): Wohngebäude VOR Hausrat/Haftpflicht –
    # ein Wohngebäude-Artikel landete auf /go/hausrat/ und /go/haftpflicht/
    # (Fund 19.09.). „wohngebäude“ ist eindeutig; das bloße Wort „Haus“
    # bleibt bewusst draußen (Haushaltsbuch, Hausmittel, Hausarzt …).
    (r"wohngeb[aä]ude|wohngebaeude|geb[aä]udeversicherung|gebaeudeversicherung"
     r"|wohngeb[aä]udeschutz|hausversicherungsvergleich|immobilienversicherung",
     "wohngebaeudeversicherung"),
    (r"privathaftpflicht", "haftpflicht"),
    (r"hausrat", "hausrat"),
    (r"haftpflicht", "haftpflicht"),
    (r"kfz|kasko|sf-klasse", "kfz-versicherung"),
    (r"mietwagen|mietauto|autovermiet", "mietwagen"),
    (r"flug|fluege|flugzeug|flugticket", "fluege"),
    (r"pauschal|last.minute|urlaubskasse|all.inclusive|urlaub", "reisen"),
    # 15.09.2026 (#295): „flut“/„sturm“ ohne Kontext sind Alltagswörter.
    (r"elementar|starkregen|hochwasser|unwetter|sturmflut"
     r"|flutkatastroph|flutschaden|flutopfer|flutversicherung", "hausrat"),
    # 11.09.2026 (Reserve #5): Gas-Tarif mit Bindestrich, Gasrechnung …
    (r"gasanbieter|gaspreis|gas[-\u00a0\u202f\s]?tarif|gasheizung|gasrechnung"
     r"|gasvergleich|gaswechsel", "gas"),
    # 15.09.2026 (#295): Energiemarkt-Vokabular-Fallback.
    (r"strom|wärmepumpe|kühl|nachtspeicher|stromfresser|stromvergleich"
     r"|eigend|balkonkraft|e-auto|strompreis|grundversorger"
     r"|energiemarkt|energiekosten|energiepreis|energieanbieter"
     r"|energie-update", "strom"),
    (r"handy|mobilfunktarif|datenvolumen|sim.karte", "handytarife"),
    (r"breitband|glasfaser|router|fritz", "dsl"),
    (r"dsl", "dsl"),
    (r"internet", "dsl"),
    # 19.09.2026 (Intent-Wache): Vermögensaufbau-Vokabular ergänzt. Ein
    # Artikel über finanzielle Freiheit wurde durch EIN rhetorisches
    # „Kredit" im Intro als Ratenkredit-Thema gelesen und sein Schluss-CTA
    # sollte auf /go/kredit/ „geheilt" werden. Wohlstands-/Sparthemen
    # gehören zur Geldanlage-Route (C24 Tagesgeld) – nicht zum Kredit.
    (r"tagesgeld|festgeld|zinsgarantie|sparzinsen|etf|sparplan|aktie|börse"
     r"|boerse|depot|vermögensaufbau|zinseszins|sparquote|investieren|zinses"
     r"|vermögens|verm[öoe]gen[ -]?aufbau|finanzielle[ -]?freiheit"
     r"|sparroutine|wohlstand|geld[ -]?anlage|geld anlegen", "tagesgeld"),
    (r"kreditkarte", "kreditkarte"),
    (r"ratenkredit|kredit|umschuldung|dispo", "kredit"),
    (r"girokonto|bankkonto|kontoführung|wechselservice|kontowechsel", "girokonto"),
    (r"budget|haushaltsbuch|frugal|notgroschen|50.30.20|monatsbudget"
     r"|nebenverdienst|impulskaeufe", "allgemein"),
)

DEEP_HINTS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(muster, re.I), route) for muster, route in THEMEN_REIHE)

# Produkt-Wörter, mit denen die Wache ANKER-Texte einer Route zuordnet.
# Bewusst KNAPP und eindeutig gehalten: Nur Begriffe, die ein Besucher
# als Angebotsname liest. Mehrdeutiges („C24“ → girokonto ODER tagesgeld,
# „Versicherung“ allein) gehört hier NICHT hinein – bei Mehrdeutigkeit
# heilt die Wache nicht (IW1 verlangt einen eindeutigen Treffer).
ANKER_WORTE: dict[str, tuple[str, ...]] = {
    "kfz-versicherung": ("kfz-versicherung", "kfz versicherung", "kfzversicherung",
                         "autoversicherung", "kfz-tarif"),
    "haftpflicht": ("haftpflicht", "privathaftpflicht"),
    "hausrat": ("hausrat",),
    "wohngebaeudeversicherung": ("wohngebäudeversicherung", "wohngebaeudeversicherung",
                                 "gebäudeversicherung", "gebaeudeversicherung",
                                 "wohngebäude", "wohngebaeude"),
    "unfallversicherung": ("unfallversicherung",),
    "reisekrankenversicherung": ("reisekranken", "auslandsreise-absicherung",
                                 "auslandskranken", "reisekrankenversicherung"),
    "zahnzusatzversicherung": ("zahnzusatz",),
    "hunde": ("tierkranken", "hundekranken", "tierversicherung", "katzenkranken"),
    "mietwagen": ("mietwagen", "mietauto", "autovermietung"),
    "fluege": ("pauschalreise", "urlaubspaket", "flug + hotel", "flug und hotel"),
    "reisen": ("pauschalreisen", "reiseangebote", "urlaubspaket"),
    "dsl": ("dsl", "internettarif", "internet-tarif", "glasfaser", "breitband"),
    "handytarife": ("handytarif", "handytarife", "mobilfunktarif"),
    "strom": ("stromtarif", "stromtarife", "stromanbieter", "stromvergleich",
              "stromanbieter wechseln"),
    "gas": ("gastarif", "gastarife", "gasanbieter", "gasvergleich",
            "gas-anbieter", "gaspreis"),
    "kredit": ("kreditangebot", "kreditangebote", "ratenkredit", "kreditvergleich",
               "umschuldung"),
    "kreditkarte": ("kreditkarte", "kreditkarten"),
    "girokonto": ("girokonto", "bankkonto", "kontowechsel", "konto ohne gebühren"),
    "tagesgeld": ("tagesgeld", "festgeld", "zinskonto"),
    "allgemein": ("check24", "vergleichsportal"),
}

# ------------------------------------------------------------
# NIE_PAARE – was unter keinen Umständen zusammen darf.
#
# Semantik: (ARTIKEL-THEMA, ROUTE) ist verboten, wenn der Link das
# Hauptangebot des Artikels bewirbt ODER der Anker generisch ist (also
# nicht selbst ehrlich das andere Produkt nennt). Ehrliches Cross-
# Selling bleibt erlaubt: Im Mietwagen-Ratgeber darf „gebührenfreies
# Kreditkarten-Konto" → /go/kreditkarte/ stehen, weil der Anker das
# Ziel selbst benennt.
#
# Jeder Eintrag trägt den BELEG (Fund) mit – ein Verbot ohne Herkunft
# ist Willkür und wird im Report nicht erklärt.
# ------------------------------------------------------------

NIE_PAARE: tuple[tuple[str, str, str], ...] = (
    ("kfz-versicherung", "haftpflicht",
     "Fund 19.09.2026: Kfz-Vergleichsartikel, Top-CTA „Kfz-Versicherung "
     "vergleichen“ → /go/haftpflicht/ (Tarifcheck Privathaftpflicht)."),
    ("haftpflicht", "kfz-versicherung",
     "Spiegelbild: Haftpflicht-Interesse darf nicht im Kfz-Rechner landen."),
    ("mietwagen", "kfz-versicherung",
     "Fund 19.09.2026: Mietwagen-Ratgeber, erster UND letzter CTA "
     "„Mietwagen vergleichen“ → /go/kfz-versicherung/."),
    ("kfz-versicherung", "mietwagen",
     "Spiegelbild: Kfz-Versicherungs-Interesse ist kein Mietwagen-Angebot."),
    ("kreditkarte", "reisekrankenversicherung",
     "Fund 19.09.2026: Kreditkartenvergleich, Top-CTA „Tarifrechner "
     "starten“ → /go/reisekrankenversicherung/."),
    ("reisekrankenversicherung", "kreditkarte",
     "Spiegelbild des Funds vom 19.09.2026."),
    ("girokonto", "kredit",
     "Fund 19.09.2026: Girokonto-Artikel, Top-CTA „Kostenlos "
     "vergleichen“ → /go/kredit/ (Ratenkredit statt Konto)."),
    ("kredit", "girokonto",
     "Spiegelbild: Kredit-Interesse darf nicht beim Girokonto landen."),
    ("wohngebaeudeversicherung", "hausrat",
     "Fund 19.09.2026: Wohngebäude-Vergleich, Top-CTA → /go/hausrat/ "
     "(Gebäude ≠ Hausrat: zwei verschiedene Policen)."),
    ("wohngebaeudeversicherung", "haftpflicht",
     "Fund 19.09.2026: derselbe Artikel, Schluss-CTA → /go/haftpflicht/."),
    ("hausrat", "wohngebaeudeversicherung",
     "Spiegelbild: Hausrat-Interesse ist keine Gebäudepolice."),
    ("tagesgeld", "kredit",
     "Geldanlage-Interesse darf nicht im Ratenkredit-Rechner landen."),
    ("kredit", "tagesgeld",
     "Spiegelbild: Kredit-Interesse ist keine Geldanlage."),
    ("fluege", "mietwagen",
     "Fund 19.09.2026: Flugticket-Ratgeber, ALLE drei CTAs → /go/mietwagen/ "
     "(Pillar-Fallback „mietwagen“ überstimmte das Artikelthema)."),
    ("mietwagen", "fluege",
     "Spiegelbild: Mietwagen-Buchungsabsicht ist kein Reise-/Flugpaket."),
    ("gas", "strom",
     "Fund 19.09.2026: Gas-Rechnungsartikel mit Anker „Gasvergleich“ "
     "→ /go/strom/ – Gas und Strom sind getrennte Rechner; der "
     "Haupt-CTA eines Gas-Artikels gehört auf Gas."),
    ("strom", "gas",
     "Spiegelbild: Haupt-CTA eines Strom-Artikels gehört auf Strom."),
)

_NIE_INDEX: dict[str, set[str]] = {}
for _thema, _route, _grund in NIE_PAARE:
    _NIE_INDEX.setdefault(_thema, set()).add(_route)

NIE_GRUND: dict[tuple[str, str], str] = {
    (t, r): g for t, r, g in NIE_PAARE}

# ------------------------------------------------------------
# GENERISCHE ANKER – Phrasen, die KEIN Produkt nennen.
#
# Sie sind die Wurzel des 19.09.-Schadensbilds: Ein Anker ohne Produkt
# kann nicht gegen die Route geprüft werden, und der Leser erfährt erst
# NACH dem Klick, was er bekommt. Profi-Regel: Jeder Affiliate-Anker
# nennt das Angebot. Die Wache heilt generische Anker auf den ehrlichen
# Anker aus dem Kontrakt (IW3/IW2).
# ------------------------------------------------------------

GENERISCHE_ANKER: tuple[str, ...] = (
    "jetzt angebote vergleichen",
    "angebote vergleichen",
    "angebote prüfen",
    "jetzt angebote prüfen",
    "angebote ansehen",
    "passende angebote ansehen",
    "angebote in deiner region sehen",
    "vergleichen & sparen",
    "vergleichen und sparen",
    "vergleichen und sparen",
    "kostenlos vergleichen",
    "kostenlos prüfen",
    "tarifrechner starten",
    "jetzt prämie berechnen",
    "tarife vergleichen",
    "jetzt tarife vergleichen",
    "versicherungsvergleich starten",
    "vergleich starten",
    "jetzt vergleichen",
    "jetzt vergleichen und sparen",
    "zum vergleich",
    "mehr erfahren",
    "weiter",
    "hier entlang",
    "angebot sichern",
    "jetzt sparen",
    "vergleichen",
)

# Marker der kanonischen CTA-Boxen (aus affiliate_marketer.py /
# affiliate_integrity_gate.py). Die Wache behandelt sie als PRIMÄR-CTA:
# Dort gilt das Artikelthema, nicht Cross-Selling.
CTA_MARKER: dict[str, str] = {
    "Schnell-Tipp von FranksFinanzcheck": "top",
    "Spar-Tipp von FranksFinanzcheck": "mid",
    "Spar-Tipp zwischendurch": "mid",
    "Jetzt vergleichen und sparen": "end",
    "Sparend zuerst vergleichen": "end",
    "Jetzt Angebote vergleichen": "end",
}


# ------------------------------------------------------------
# Hilfsfunktionen (die Wache nutzt NUR diese – keine eigene Logik)
# ------------------------------------------------------------
def norm(text: str) -> str:
    """Vergleichs-Normalform: weiche Bindestriche (U+00AD), Unicode-
    Bindestriche (U+2010…U+2015/U+2212), geschützte Leerzeichen und
    Markdown-Schmuck entfernen. „Hausrat­versicherung“ (U+00AD) und
    „Spar‑Tipp“ (U+2011) müssen als das erkannt werden, was sie sind."""
    s = (text or "").lower()
    s = s.replace("\u00ad", "")
    s = s.replace("\u00a0", " ").replace("\u202f", " ")
    for z in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2015",
              "\u2212", "\u02d7"):
        s = s.replace(z, "-")
    s = re.sub(r"[*_`>]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def ziel(key: str) -> Ziel | None:
    return ZIELE.get(key)


def anker_routes(text: str) -> list[str]:
    """Alle Routen, deren Angebots-Wörter im Text vorkommen (normiert).

    Rückgabe ist eine MENGE-Reihenfolge nach Spezifität (längstes Wort
    zuerst), damit „wohngebäudeversicherung“ vor „versicherung“ trifft.
    """
    low = norm(text)
    treffer: list[tuple[int, str]] = []
    for route, worte in ANKER_WORTE.items():
        for w in worte:
            if w in low:
                treffer.append((-len(w), route))
                break
    treffer.sort()
    seen, out = set(), []
    for _, r in treffer:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out


PARTNER_WORTE: tuple[str, ...] = ("check24", "c24", "tarifcheck")


def nennt_ziel(text: str, key: str) -> bool:
    """True, wenn der Text das Angebot ODER den Partner des Ziels nennt.

    Das ist der Ehrlichkeits-Mindeststandard für Cross-Selling: Ein Leser,
    der im Wohngebäude-Artikel auf „Jetzt Hausratversicherung vergleichen"
    klickt, wird nicht getäuscht – er weiß, was er bekommt. Ein Leser, der
    auf „Jetzt Angebote vergleichen" klickt, weiß es nicht (deshalb ist ein
    generischer Anker auf einer themenfremden Route ein harter Fund).
    """
    z = ZIELE.get(key)
    low = norm(text)
    if not low:
        return False
    if key in anker_routes(low):
        return True
    if z and z.partner and z.partner.lower() in low:
        return True
    return any(w in low for w in PARTNER_WORTE) and bool(z)


def anker_ist_generisch(text: str) -> bool:
    """True, wenn der Anker KEIN Angebot nennt.

    Profi-Regel (19.09.2026): Ein Anker ohne Produktname kann nicht gegen
    die Route geprüft werden – der Leser erfährt erst NACH dem Klick, was
    er bekommt. Genau so entstanden die Fehlrouten vom 19.09. („Tarifrechner
    starten" → Reisekrankenversicherung im Kreditkarten-Artikel).
    Wer nur einen ANBIETER nennt („C24 Bank“), nennt kein Produkt: Das ist
    für IW1 (Anker → Route) wertlos, erfüllt aber die Ehrlichkeits-Nennung
    IW3 (Pflichtwort „C24“) – beide Prüfungen bleiben getrennt.
    """
    low = norm(text)
    if not low:
        return True
    return not anker_routes(low)


def nie_paar(thema: str, route: str) -> str:
    """Beleg-Grund, wenn (Artikelthema, Route) verboten ist – sonst ""."""
    if not thema or not route or thema == route:
        return ""
    if route in _NIE_INDEX.get(thema, set()):
        return NIE_GRUND.get((thema, route), "verbotenes Paar (ohne Beleg)")
    return ""


def ist_verboten(thema: str, route: str) -> bool:
    return bool(nie_paar(thema, route))


VERB_WORTE: tuple[str, ...] = (
    "prüfen", "pruefen", "vergleichen", "vergleich", "ansehen", "eröffnen",
    "oeffnen", "sichern", "starten", "finden", "holen", "buchen", "wechseln",
    "sparen", "entdecken", "nutzen", "testen", "abschließen", "abschliessen",
    "berechnen", "anbieten", "anschauen", "klicken",
)


def anhang_sicher(z: Ziel, anchor: str) -> bool:
    """Darf der Kontrakt-Anhang grammatisch sicher angehängt werden?

    Nur bei reinen Nominalankern („verzinstes Tagesgeldkonto" → „… der C24
    Bank"). Verben oder ein Vergleichs-Versprechen machen daraus kaputtes
    Deutsch („Tagesgeld jetzt prüfen der C24 Bank") – dann meldet die Wache
    mit Vorschlag statt halb zu heilen (Ehrlichkeit schlägt Automatik).
    """
    if not z.abweichung or not z.abweichung.anhang:
        return False
    low = norm(anchor)
    if len(low) > 60 or not low:
        return False
    if any(w in low for w in z.abweichung.verbot):
        return False
    if z.abweichung.art == "einzelanbieter" and "vergleich" in low:
        return False          # „Tagesgeldvergleich der C24 Bank" bleibt ein
                              # Vergleichs-Versprechen, das es nicht gibt
    return not any(w in low for w in VERB_WORTE)


# ------------------------------------------------------------
# CTA-Bausteine für Generatoren (affiliate_marketer.py)
# ------------------------------------------------------------
# Hausstil-Sätze je Slot. Sie gelten NUR für Routen ohne Abweichung –
# bei einer Abweichung (C24 Bank, Pauschalreise) liefert `saetze` des
# Ziels den ehrlichen Satz, sonst verspricht schon der Satz einen
# Marktvergleich, den es nicht gibt.
# Die MARKER („Schnell-Tipp von FranksFinanzcheck:", „Spar-Tipp
# zwischendurch:", „Sparend zuerst vergleichen:") bleiben unberührt:
# Sie sind Hausstil und werden von affiliate_integrity_gate.py (AI1/AI3),
# dash_guard und umbruch_guard erkannt – ein umbenannter Marker wäre ein
# toter CTA für alle Wächter.
CTA_SAETZE_DEFAULT: dict[str, str] = {
    "top": "Die besten Tarife findest du über unseren Partner-Vergleich",
    "mid": "faire Konditionen gibt es online in Minuten",
    "end": "",
}


def cta_bausteine(key: str, slot: str, slug: str = "") -> tuple[str, str]:
    """(Satz, Anker) für einen neu erzeugten CTA – dieselbe Wahrheit,
    die die Intent-Wache (IW0–IW9) im Bestand prüft.

    Ohne diese Funktion erzeugte affiliate_marketer.py seine Anker aus
    einem generischen Pool, ausgewählt über `date.today().day`:
    „Jetzt Angebote vergleichen", „Tarifrechner starten" – keiner nannte
    das Produkt. Das war die Quelle der Fehlrouten vom 19.09.2026, denn
    ein Anker, der nichts verspricht, konnte auch nie falsch wirken.
    """
    z = ziel(key) or ziel("allgemein")
    if z is None:                       # Register ohne Kontrakt – nie still
        return CTA_SAETZE_DEFAULT.get(slot, ""), "Jetzt Angebote ansehen"
    anker = z.anker_fuer(slot, slug)
    satz = ""
    if z.abweichung and z.abweichung.art != "portal":
        satz = z.saetze.get(slot) or z.saetze.get("top") or ""
    if not satz:
        satz = CTA_SAETZE_DEFAULT.get(slot, "")
    return satz, anker


def route_fuer_text(text: str, titel: str = "", pillar: str = "") -> str:
    """Angebots-Route aus Titel/Text (Spezifitäts-Reihe) – reine Kontrakt-
    Logik ohne Pillar-Fallback. Der Marketer ergänzt den Fallback."""
    for quelle in (titel, text):
        if not quelle:
            continue
        for pat, route in DEEP_HINTS:
            if pat.search(quelle):
                return route
    return ""


def themen_reihe_als_hints() -> list[tuple[re.Pattern[str], str]]:
    """Für affiliate_marketer.DEEP_HINTS (eine Quelle, zwei Verbraucher)."""
    return [(pat, route) for pat, route in DEEP_HINTS]


# ------------------------------------------------------------
# Daten-Datei für Hugo (site.Data.affiliate_ziele)
# ------------------------------------------------------------
def _yaml_text(wert: str) -> str:
    return '"' + (wert or "").replace("\\", "\\\\").replace('"', '\\"') + '"'


def bake_yaml() -> str:
    """Generiert data/affiliate_ziele.yaml (Hugo + Mensch, aus dem Kontrakt).

    Die Templates lesen `anzeige` (Tooltip) und `gateway` (Name auf der
    Übergabeseite). Generiert statt handgepflegt: eine Wahrheit, keine
    Drift – affiliate_intent_guard.py IW0 beweist, dass die Datei zum
    Kontrakt passt (sonst Exit 2).
    """
    L = [
        "# ============================================================",
        "#  AFFILIATE-ZIELE – Angebots-Wahrheit pro /go/-Route",
        "#",
        "#  ⚠️ GENERIERT aus scripts/affiliate_intent_contract.py – NICHT",
        "#     von Hand ändern. Änderung am Kontrakt, dann:",
        "#       python3 scripts/affiliate_intent_guard.py --bake",
        "#     Die Intent-Wache (IW0) prüft bei jedem Lauf, ob diese Datei",
        "#     zum Kontrakt passt; Drift = Exit 2 (fail-closed).",
        "#",
        "#  Verbraucher: layouts/_default/_markup/render-link.html und",
        "#  layouts/_partials/affiliate_anchor_attrs.html lesen `anzeige`",
        "#  (Tooltip = ehrlicher Zielname), die /go/-Gateway-Seiten lesen",
        "#  `gateway` (Name auf der Übergabeseite).",
        "# ============================================================",
        "",
        "ziele:",
    ]
    for key in sorted(ZIELE):
        z = ZIELE[key]
        L.append(f"  {key}:")
        L.append(f"    partner: {_yaml_text(z.partner)}")
        L.append(f"    produkt: {_yaml_text(z.produkt)}")
        L.append(f"    anzeige: {_yaml_text(z.anzeige)}")
        L.append(f"    gateway: {_yaml_text(z.gateway)}")
        L.append(f"    landing: {_yaml_text(z.landing)}")
        L.append(f"    netz: {_yaml_text(z.netz)}")
        abw = z.abweichung
        L.append(f"    abweichung: {_yaml_text(abw.art if abw else '')}")
        L.append(f"    abweichung_ziel: {_yaml_text(abw.ziel if abw else '')}")
        L.append(f"    pflicht_nennung: {_yaml_text(', '.join(abw.pflicht) if abw else '')}")
    L.append("")
    return "\n".join(L)


def selftest() -> list[str]:
    """Eingefrorene Beweise, dass der Kontrakt die Vorfälle vom 19.09.2026
    abbildet. Exit 2 in der Wache, wenn hier etwas bricht."""
    fehler: list[str] = []

    def muss(bedingung: bool, meldung: str) -> None:
        if not bedingung:
            fehler.append(meldung)

    # 1) Jede Route hat ehrliche Namen + Anker für alle Slots.
    for key, z in ZIELE.items():
        for slot in ("top", "mid", "end", "intext"):
            muss(bool(z.anker.get(slot)), f"{key}: Anker-Slot „{slot}“ fehlt")
        muss(bool(z.anzeige) and z.partner.split()[0] in z.anzeige,
             f"{key}: `anzeige` muss den Partner nennen ({z.anzeige})")
        for slot, varianten in z.anker.items():
            for a in varianten:
                ok, grund = z.ehrlich(a)
                muss(ok, f"{key}/{slot}: Anker „{a}“ ist unehrlich ({grund})")

    # 1b) Jedes Abweichungs-Ziel hat ehrliche CTA-Sätze für alle Slots.
    for key, z in ZIELE.items():
        if z.abweichung and z.abweichung.art != "portal":
            for slot in ("top", "mid", "end"):
                muss(bool(z.saetze.get(slot)),
                     f"{key}: ehrlicher CTA-Satz für „{slot}“ fehlt "
                     "(Abweichung darf nicht aus dem Standard-Satz werben)")
                satz = z.saetze[slot]
                ok, grund = z.ehrlich(satz)
                muss(ok, f"{key}/{slot}: CTA-Satz ist unehrlich ({grund})")

    # 2) Abweichungen sind erfasst (die drei Fonds vom 19.09.).
    muss(ZIELE["tagesgeld"].abweichung is not None
         and "C24" in ZIELE["tagesgeld"].abweichung.pflicht,
         "tagesgeld: C24-Pflichtnennung fehlt (Fund 19.09.)")
    muss(ZIELE["girokonto"].abweichung is not None
         and "C24" in ZIELE["girokonto"].abweichung.pflicht,
         "girokonto: C24-Pflichtnennung fehlt")
    muss(ZIELE["fluege"].abweichung is not None
         and any("pauschalreise" in w.lower() for w in ZIELE["fluege"].abweichung.pflicht),
         "fluege: Pauschalreise-Pflichtnennung fehlt (Fund 19.09.)")

    # 3) Ehrlichkeitsprüfung greift (Beispiele aus dem Bestand).
    ok, _ = ZIELE["tagesgeld"].ehrlich("Jetzt Tagesgeld vergleichen")
    muss(not ok, "tagesgeld: „Jetzt Tagesgeld vergleichen“ muss als unehrlich gelten")
    ok, _ = ZIELE["tagesgeld"].ehrlich("Jetzt C24 Bank Tagesgeld ansehen")
    muss(ok, "tagesgeld: C24-Nennung muss als ehrlich gelten")
    ok, _ = ZIELE["fluege"].ehrlich("Flüge vergleichen")
    muss(not ok, "fluege: „Flüge vergleichen“ muss als unehrlich gelten (404-Ziel)")
    ok, _ = ZIELE["fluege"].ehrlich("Pauschalreise mit Flug vergleichen")
    muss(ok, "fluege: „Pauschalreise mit Flug vergleichen“ muss ehrlich sein")

    # 4) Nie-Paare: die vier prominenten Fehlrouten sind verboten.
    for thema, route in (("kfz-versicherung", "haftpflicht"),
                         ("mietwagen", "kfz-versicherung"),
                         ("kreditkarte", "reisekrankenversicherung"),
                         ("girokonto", "kredit"),
                         ("wohngebaeudeversicherung", "hausrat"),
                         ("wohngebaeudeversicherung", "haftpflicht"),
                         ("fluege", "mietwagen"),
                         ("gas", "strom")):
        muss(ist_verboten(thema, route),
             f"NIE_PAARE: ({thema} → {route}) muss verboten sein")
        muss(bool(nie_paar(thema, route)),
             f"NIE_PAARE: ({thema} → {route}) braucht einen Beleg-Grund")
    muss(not ist_verboten("mietwagen", "kreditkarte"),
         "ehrliches Cross-Selling (Mietwagen → Kreditkarte) darf nicht verboten sein")
    muss(not ist_verboten("gas", "gas"), "gleiches Thema ist nie ein Nie-Paar")

    # 5) Anker-Erkennung: eindeutig, generisch, mehrdeutig.
    muss(anker_routes("Kfz-Versicherung vergleichen") == ["kfz-versicherung"],
         "Anker „Kfz-Versicherung vergleichen“ muss eindeutig kfz sein")
    muss(anker_routes("Jetzt Mietwagen vergleichen") == ["mietwagen"],
         "Anker „Jetzt Mietwagen vergleichen“ muss eindeutig mietwagen sein")
    muss(anker_routes("→ Mietwagen mit Vollkasko ohne Selbstbeteiligung "
                      "vergleichen") == ["mietwagen"],
         "„Vollkasko“ darf den Mietwagen-Anker nicht mehrdeutig machen "
         "(Fund 19.09.: letzter CTA des Mietwagen-Ratgebers)")
    muss("wohngebaeudeversicherung" in anker_routes("Wohngebäude­versicherung vergleichen"),
         "weicher Bindestrich (U+00AD) darf die Erkennung nicht brechen")
    muss(anker_routes("C24 Bank") == [],
         "„C24 Bank“ ist mehrdeutig (girokonto/tagesgeld) → keine Heilung")
    muss(anker_ist_generisch("Jetzt Angebote vergleichen"),
         "„Jetzt Angebote vergleichen“ muss als generisch gelten")
    must_not = anker_ist_generisch("Jetzt Gastarife vergleichen")
    muss(not must_not, "„Jetzt Gastarife vergleichen“ ist nicht generisch")
    muss(anker_ist_generisch("Tarifrechner starten"),
         "„Tarifrechner starten“ muss als generisch gelten")

    # 5a2) Gateway-Phrase: grammatisch (Präposition) und ehrlich (Partner)
    for key, z in ZIELE.items():
        ph = z.ziel_phrase()
        muss(ph.split(" ")[0] in ("zu", "zum", "zur", "zu den".split()[0])
             or ph.startswith("zu den "),
             f"{key}: Gateway-Phrase ohne Präposition: „{ph}“")
        muss(z.partner.lower().replace("check24", "check24") in ph.lower()
             or "c24" in ph.lower(),
             f"{key}: Gateway-Phrase nennt den Partner nicht: „{ph}“")
        ok, grund = z.ehrlich(ph)
        muss(ok, f"{key}: Gateway-Phrase unehrlich: {grund}")
    muss(ZIELE["tagesgeld"].ziel_phrase() ==
         "zum Tagesgeld der C24 Bank (CHECK24-Tochter)",
         "Tagesgeld-Phrase muss das Einzelanbieter-Ziel nennen")

    # 5b) Transparenz + Anhang-Sicherheit (Cross-Selling-Grenze, 19.09.)
    muss(nennt_ziel("Jetzt Hausratversicherung vergleichen", "hausrat"),
         "produkt-exakter Anker ist transparent")
    muss(nennt_ziel("Jetzt C24 Bank-Angebote vergleichen", "tagesgeld"),
         "Partner-Nennung (C24) ist transparent")
    muss(not nennt_ziel("Jetzt Angebote vergleichen", "tagesgeld"),
         "generischer Anker ist NICHT transparent")
    muss(anhang_sicher(ZIELE["tagesgeld"], "verzinstes Tagesgeldkonto"),
         "Nominalanker darf den C24-Anhang bekommen")
    muss(not anhang_sicher(ZIELE["tagesgeld"], "Tagesgeld jetzt prüfen"),
         "Verben-Anker darf nicht angehängt werden (Grammatik)")
    muss(not anhang_sicher(ZIELE["tagesgeld"], "Tagesgeldvergleich"),
         "Vergleichs-Versprechen darf nicht per Anhang geheilt werden")

    # 5b2) Satz-Ehrlichkeit: Die eigenen Kontrakt-Sätze müssen bestehen
    #      (sonst wäre die Heilung nicht idempotent), fremde Vergleichs-
    #      Versprechen auf Einzelanbieter-Routen müssen auffallen.
    for key, z in ZIELE.items():
        for slot, satz in z.saetze.items():
            ok, grund = z.satz_ehrlich(satz)
            muss(ok, f"Kontrakt-Satz {key}/{slot} verletzt satz_verbot: {grund}")
    ok, _ = ZIELE["girokonto"].satz_ehrlich(
        "Vergleiche jetzt führende gebührenfreie Girokonten")
    muss(not ok, "Vergleichs-Satz auf C24-Route muss auffallen")
    ok, _ = ZIELE["girokonto"].satz_ehrlich(
        "Ein dauerhaft kostenloses Girokonto bekommst du bei der C24 Bank")
    muss(ok, "ehrlicher C24-Satz darf nicht auffallen")
    ok, _ = ZIELE["fluege"].satz_ehrlich("Jetzt Pauschalreisen mit Flug vergleichen")
    muss(ok, "Pauschalreise-Vergleich ist echt – kein Fehlalarm bei Bündelung")
    ok, _ = ZIELE["fluege"].satz_ehrlich("Unser Partner vergleicht keine Einzelflüge")
    muss(ok, "ehrliche Flug-Einordnung darf nicht auffallen")

    # 5c) Jeder Kontrakt-Anker erfüllt den Maßstab der Wache selbst:
    #     produkt-exakt (nicht generisch, IW8) und ehrlich (IW3).
    for key, z in ZIELE.items():
        for slot, varianten in z.anker.items():
            for anker in varianten:
                muss(not anker_ist_generisch(anker),
                     f"Kontrakt-Anker {key}/{slot} ist generisch: „{anker}“")
                ok, grund = z.ehrlich(anker)
                muss(ok, f"Kontrakt-Anker {key}/{slot} unehrlich: {grund}")

    # 5d) CTA-Bausteine für den Generator (IW6): produkt-exakt, ehrlich,
    #     deterministisch über den Slug (kein Tages-Churn).
    for key, z in ZIELE.items():
        for slot in ("top", "mid", "end"):
            satz, anker = cta_bausteine(key, slot, "artikel-slug-2026")
            ok, grund = z.ehrlich(satz + " " + anker)
            muss(ok, f"cta_bausteine({key},{slot}) unehrlich: {grund}")
            muss(bool(anker), f"cta_bausteine({key},{slot}) ohne Anker")
            if key != "allgemein":
                muss(not anker_ist_generisch(anker),
                     f"cta_bausteine({key},{slot}) generisch: „{anker}“")
    a1 = cta_bausteine("tagesgeld", "top", "slug-a")[1]
    a2 = cta_bausteine("tagesgeld", "top", "slug-a")[1]
    muss(a1 == a2, "cta_bausteine ist nicht deterministisch (Tages-Churn)")
    muss("C24" in cta_bausteine("tagesgeld", "top", "x")[0]
         + cta_bausteine("tagesgeld", "top", "x")[1],
         "C24-Satz/Anker muss die Bank nennen")
    muss("Pauschalreise" in cta_bausteine("fluege", "top", "x")[0],
         "Flug-Satz muss Pauschalreise nennen")

    # 6) Themen-Reihe: Titel-Route der sieben Fund-Artikel.
    faelle = [
        ("Kfz-Versicherung Vergleich 2026: Bis zu 800 € sparen", "kfz-versicherung"),
        ("Kostenloses Girokonto: So findest du ein Konto ohne Gebühren", "girokonto"),
        ("Kreditkarte vergleichen: Kostenlos und sicher zahlen", "kreditkarte"),
        ("Mietwagen ohne Kautionsfallen: So sparst du im Urlaub", "mietwagen"),
        ("Wohngebäudeversicherung Vergleich: Worauf du achten musst",
         "wohngebaeudeversicherung"),
        ("Flugtickets günstig buchen: Strategien für deine Reise", "fluege"),
        ("Gasrechnung senken: Spätsommer-Check spart hunderte Euro", "gas"),
        # Regression: bestehende eingefrorene Fälle dürfen nicht kippen.
        ("Hausratversicherung: Was sie kostet und wen sie schützt", "hausrat"),
        ("Privathaftpflicht: Warum so wichtig und was sie kostet", "haftpflicht"),
        ("Depot 2026: Dein smarter Start in den Vermögensaufbau mit ETF-Sparplan",
         "tagesgeld"),
        ("Haushaltsbuch führen: App, Excel oder Stift im Vergleich", "allgemein"),
        ("Elementarschadenversicherung: Schutz bei Hochwasser und Starkregen", "hausrat"),
    ]
    for titel, want in faelle:
        got = route_fuer_text("", titel)
        muss(got == want, f"Titel-Route „{titel[:45]}…“: erwartet {want}, bekam {got}")

    # 7) YAML-Bake: vollständig und parse-bar (Schlüssel zählen).
    yaml_text = bake_yaml()
    muss(yaml_text.count("\n  ") >= len(ZIELE), "bake_yaml: Routen fehlen")
    for key in ZIELE:
        muss(f"\n  {key}:" in yaml_text, f"bake_yaml: {key} fehlt in der Daten-Datei")
        muss(f"{ZIELE[key].anzeige}" in yaml_text, f"bake_yaml: Anzeige {key} fehlt")

    return fehler


if __name__ == "__main__":
    import sys

    fehler = selftest()
    if fehler:
        print("🛑 INTENT-CONTRACT-SELFTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        sys.exit(2)
    print(f"✅ Intent-Kontrakt: {len(ZIELE)} Ziele, {len(NIE_PAARE)} Nie-Paare, "
          f"{len(THEMEN_REIHE)} Themen-Muster – Selbsttest grün.")
