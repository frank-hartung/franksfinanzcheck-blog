#!/usr/bin/env python3
# ============================================================
#  SOCIAL-CLAIMS – unzulässige Versprechen: eine Sperre, eine Heilung
#  ------------------------------------------------------------
#  BEFUND 06.11.2026 (Fortsetzung von #716 und #1097):
#  `social_gate` L3 sperrt unzulässige Versprechen („garantiert",
#  „risikofrei", …) – sachlich richtig. Nur kam die Sperre zu spät: Der
#  Texter hatte den Satz vorher aus dem Artikel übernommen. Der
#  Ökostrom-Artikel sagt „… sodass eine lückenlose Versorgung garantiert
#  ist"; damit war JEDER Winkel auf Reddit unsendbar (drei von drei), der
#  Kanal fiel still aus – dieselbe Klasse wie #716, eine Ebene tiefer.
#  Eine Wache, die nur ablehnt, macht einen Kanal stumm; sie muss heilen.
#
#  ZWEI HEBEL, in dieser Reihenfolge:
#    1. QUELLE REINIGEN – Sätze mit unzulässigem Versprechen kommen gar
#       nicht erst in die Copy. Das geschieht auf SATZ-Ebene, nicht per
#       Wort-Umschreibung: „Diese Anlage ist risikofrei" wortweise zu
#       ersetzen zerlegt die deutsche Grammatik und erzeugt neue Fehler.
#    2. NOTFALL – bleibt nur der Titel (er lässt sich nicht weglassen),
#       wird er geglättet: eine kuratierte, grammatiksichere Ersetzung
#       („garantiert" → „gesichert", in allen Flexionen). Danach wird
#       erneut geprüft; bleibt ein Treffer, gilt der Text als unsauber
#       und wird NICHT verwendet (fail-closed, wie das Gate).
#
#  EINE QUELLE: Die Sperrliste steht in `data/social/channels.yaml`
#  unter `gate.blocked_terms` / `gate.forbidden_phrases`. Gate UND Texter
#  lesen sie über `sperrlisten()` – kein zweites Muster, das driftet.
#  (Genau das war die Lehre aus #716: Emoji-Muster in Texter und Gate
#  liefen auseinander, und das eine produzierte, was das andere ablehnte.)
#
#  NUTZUNG
#    import social_claims as claims
#    sperren = claims.sperrlisten(meta, channel_cfg)
#    artikel, entfernt = claims.material_saeubern(artikel, sperren)
#    text, entfernt = claims.haerten(text, sperren)
#
#    python3 scripts/social_claims.py --selftest
#      Exit 0 = grün, Exit 1 = Befund. Schreibt nichts (C15).
# ============================================================
from __future__ import annotations

import re
import sys
from dataclasses import dataclass

#: Satzgrenze. Bewusst schlicht: deutsche Abkürzungen („z. B.") zerlegen
#: den Text gelegentlich zu fein – das ist hier unschädlich, weil eine
#: zu feine Zerlegung nur kleinere Einheiten prüft, nie größere.
SATZ_RX = re.compile(r"(?<=[.!?:])\s+(?=[A-ZÄÖÜ„\"'*])|(?<=\n)")

#: Kuratierte Glättungen für den Notfall (Titel/Überschrift). Nur
#: grammatiksichere Wortersetzungen mit erhaltener Flexionsendung.
GLAETTUNGEN: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bgarantiert(e|er|es|en|em)?\b", re.I), r"gesichert\1"),
    (re.compile(r"\brisikofrei(e|er|es|en|em)?\b", re.I), r"risikoarm\1"),
    (re.compile(r"\bohne\s+(?:jedes\s+|jegliches\s+)?Risiko\b", re.I),
     "mit begrenztem Risiko"),
    (re.compile(r"\bschnell\s+reich\b", re.I), "finanziell unabhängig"),
    (re.compile(r"\bzu\s+100\s*%\s*sicher\b", re.I), "weitgehend sicher"),
)

#: Felder der Copy-Quelle, die aus Sätzen bestehen und gereinigt werden.
MATERIAL_FELDER: tuple[str, ...] = (
    "kurzantwort", "description", "faq_answer", "hook", "cover_alt", "pin_title",
)

#: Listenfelder der Copy-Quelle (jeder Eintrag ist ein Satz/Bullet).
MATERIAL_LISTEN: tuple[str, ...] = ("takeaways", "hook_sentences", "numbers")


@dataclass(frozen=True)
class Sperren:
    """Die wirksame Sperrliste eines Kanals (global + Kanal-Zusatz)."""

    begriffe: tuple[str, ...] = ()
    phrasen: tuple[str, ...] = ()

    def __bool__(self) -> bool:
        return bool(self.begriffe or self.phrasen)

    @property
    def alle(self) -> tuple[str, ...]:
        return self.begriffe + self.phrasen

    def treffer(self, text: str) -> list[str]:
        """Alle Sperr-Einträge, die im Text vorkommen (in Listenreihenfolge)."""
        heu = (text or "").lower()
        if not heu:
            return []
        return [w for w in self.alle if w and w.lower() in heu]

    def sauber(self, text: str) -> bool:
        return not self.treffer(text)


def sperrlisten(meta: dict | None, channel_cfg: dict | None = None) -> Sperren:
    """Liest die wirksame Sperrliste – EINE Quelle für Gate und Texter.

    `meta["gate"]` ist der Haus-Standard aus `data/social/channels.yaml`.
    Ein Kanal darf ihn über `channel_cfg["gate"]` ERWEITERN (nie ersetzen:
    eine kanalweise abgeschaltete Haus-Regel wäre eine Hintertür).
    """
    def _lies(cfg: dict | None) -> tuple[list[str], list[str]]:
        cfg = cfg or {}
        b = [str(x).strip() for x in (cfg.get("blocked_terms") or []) if str(x).strip()]
        p = [str(x).strip() for x in (cfg.get("forbidden_phrases") or []) if str(x).strip()]
        return b, p

    basis = (meta or {}).get("gate")
    kanal = (channel_cfg or {}).get("gate")
    b1, p1 = _lies(basis if isinstance(basis, dict) else {})
    b2, p2 = _lies(kanal if isinstance(kanal, dict) else {})
    begriffe: list[str] = []
    phrasen: list[str] = []
    for quelle in (b1 + b2,):
        for w in quelle:
            if w.lower() not in {x.lower() for x in begriffe}:
                begriffe.append(w)
    for w in p1 + p2:
        if w.lower() not in {x.lower() for x in phrasen}:
            phrasen.append(w)
    return Sperren(tuple(begriffe), tuple(phrasen))


def _gross(s: str, muster: str) -> str:
    """Übernimmt die Großschreibung des Fundes auf die Ersetzung."""
    if muster[:1].isupper():
        return s[:1].upper() + s[1:]
    if muster.isupper():
        return s.upper()
    return s


def glaetten(text: str, sperren: Sperren) -> tuple[str, list[str]]:
    """Notfall-Glättung: kuratierte Ersetzungen, grammatiksicher.

    Danach wird NICHT blind vertraut – der Aufrufer prüft erneut
    (`haerten`). Gibt (text, angewandte_ersetzungen) zurück.
    """
    angewandt: list[str] = []
    for rx, ersatz in GLAETTUNGEN:
        def _sub(m: re.Match[str], _ersatz: str = ersatz) -> str:
            try:
                neu = m.expand(_ersatz)
            except re.error:            # pragma: no cover – Tabelle ist fest
                neu = _ersatz
            neu = _gross(neu, m.group(0))
            if neu != m.group(0):
                angewandt.append(f"{m.group(0)} → {neu}")
            return neu
        text = rx.sub(_sub, text or "")
    return text, angewandt


def saeubern(text: str, sperren: Sperren) -> tuple[str, list[str]]:
    """Entfernt Sätze mit unzulässigem Versprechen – Satz-Ebene, nie Wort.

    Struktur bleibt erhalten: Absätze (`\\n\\n`) und Aufzählungen (`* `)
    werden zeilenweise behandelt; eine belastete Aufzählungszeile fällt
    ganz weg, statt halb stehen zu bleiben.
    """
    if not text or not sperren:
        return text or "", []
    entfernt: list[str] = []
    zeilen_out: list[str] = []
    for zeile in (text or "").split("\n"):
        if not zeile.strip():
            zeilen_out.append(zeile)
            continue
        teile = [t for t in SATZ_RX.split(zeile) if t]
        behalten: list[str] = []
        for teil in teile:
            if sperren.sauber(teil):
                behalten.append(teil)
            else:
                entfernt.append(teil.strip())
        neu = " ".join(p.strip() for p in behalten).strip()
        # Eine Aufzählungszeile ohne Inhalt fällt komplett weg.
        if neu and not re.fullmatch(r"[*\-\u2022]", neu):
            zeilen_out.append(neu)
    # Überzählige Leerzeilen zusammenziehen (die Struktur bleibt lesbar).
    ergebnis = re.sub(r"\n{3,}", "\n\n", "\n".join(zeilen_out)).strip("\n")
    return ergebnis, entfernt


def haerten(text: str, sperren: Sperren) -> tuple[str, list[str]]:
    """Macht einen fertigen Copy-Baustein sendbar – oder gibt "" zurück.

    Reihenfolge: Quelle säubern (Sätze) → falls nichts übrig bleibt,
    glätten → erneut prüfen. Ein Text, der danach noch sperrt, wird NICHT
    zurückgegeben: lieber ein fehlender Satz als ein unzulässiges
    Versprechen (fail-closed wie das Gate).
    """
    sauber, entfernt = saeubern(text, sperren)
    if sauber.strip() and sperren.sauber(sauber):
        return sauber, entfernt
    if text and text.strip():
        geglaettet, ersetzt = glaetten(text, sperren)
        if sperren.sauber(geglaettet):
            return geglaettet, entfernt + ersetzt
    return "", entfernt


def material_saeubern(artikel: dict, sperren: Sperren) -> tuple[dict, list[str]]:
    """Reinigt die Copy-Quelle, BEVOR der Texter daraus baut.

    Gibt (artikel_kopie, entfernte_saetze) zurück. Der Titel bleibt
    zunächst unangetastet (er ist die Identität des Beitrags) – er wird
    erst geglättet, wenn er selbst sperrt. Ein belasteter Satz wird
    zuerst geglättet („… Versorgung garantiert ist" → „… gesichert ist")
    und erst verworfen, wenn keine grammatiksichere Glättung greift.
    `takeaways` und `hook_sentences` verlieren die Einträge, die danach
    leer bleiben; ist eine Liste ganz leer, bleibt sie leer (der Texter
    fällt auf den nächsten Baustein zurück, statt Unsauberes zu verwenden).
    """
    if not sperren or not artikel:
        return dict(artikel or {}), []
    neu = dict(artikel)
    entfernt: list[str] = []
    for feld in MATERIAL_FELDER:
        wert = neu.get(feld)
        if not isinstance(wert, str) or not wert.strip():
            continue
        if sperren.sauber(wert):
            continue
        sauber, weg = haerten(wert, sperren)
        neu[feld] = sauber
        entfernt += weg
    for feld in MATERIAL_LISTEN:
        werte = neu.get(feld)
        if not isinstance(werte, list):
            continue
        behalten = []
        for eintrag in werte:
            if not isinstance(eintrag, str):
                behalten.append(eintrag)
                continue
            sauber, weg = haerten(eintrag, sperren)
            if sauber.strip():
                behalten.append(sauber)
            else:
                entfernt.append(eintrag.strip())
        neu[feld] = behalten
    titel = neu.get("title")
    if isinstance(titel, str) and not sperren.sauber(titel):
        sauber, ersetzt = glaetten(titel, sperren)
        if sperren.sauber(sauber):
            neu["title"] = sauber
            entfernt += ersetzt
    return neu, entfernt


# --------------------------------------------------------------- Selbsttest
def _fixture_meta() -> dict:
    return {"gate": {"blocked_terms": ["garantiert", "risikofrei", "schnell reich",
                                       "ohne Risiko", "zu 100 % sicher"],
                     "forbidden_phrases": ["In der heutigen schnelllebigen Welt"]}}


def _fixture_artikel() -> dict:
    return {
        "title": "Ökostrom wechseln: sicher und bezahlbar",
        "description": "So prüfst du Ökotarife.",
        "kurzantwort": "Ein Wechsel ist jederzeit möglich und die Versorgung ist garantiert.",
        "takeaways": [
            "Ein Wechsel dauert nur wenige Minuten.",
            "Der Wechselprozess ist gesetzlich abgesichert, sodass eine lückenlose Versorgung garantiert ist.",
            "Echte Ökotarife erkennst du an Siegeln.",
        ],
        "hook_sentences": ["Du willst wechseln?", "Die Anlage ist risikofrei."],
        "numbers": ["350 € im Jahr"],
        "faq_answer": "In der heutigen schnelllebigen Welt zählt jeder Euro.",
    }


def selbsttest() -> int:
    """Prüft Sperrquelle, Satz-Heilung, Glättung, Notfall und Reinheit."""
    faelle = 0
    rot: list[str] = []

    def pruefe(name: str, bedingung: bool) -> None:
        nonlocal faelle
        faelle += 1
        if not bedingung:
            rot.append(name)

    sperren = sperrlisten(_fixture_meta())

    # K1 Sperrliste wird gelesen und ist vollständig
    pruefe("K1 Sperrliste", set(sperren.begriffe) == {"garantiert", "risikofrei",
                                                      "schnell reich", "ohne Risiko",
                                                      "zu 100 % sicher"}
           and sperren.phrasen == ("In der heutigen schnelllebigen Welt",))

    # K2 Kanal-Zusatz erweitert, ersetzt nicht
    erweitert = sperrlisten(_fixture_meta(), {"gate": {"blocked_terms": ["abzocke"]}})
    pruefe("K2 Erweiterung", "abzocke" in erweitert.begriffe and "garantiert" in erweitert.begriffe)

    # K3 Treffer-Erkennung (case-insensitiv, Teilwort)
    pruefe("K3 Treffer", sperren.treffer("Das ist GARANTIERT sicher") == ["garantiert"])
    pruefe("K3b sauber", sperren.sauber("Das ist gesichert."))

    # K4 Satz-Heilung: belasteter Satz fällt, Struktur bleibt
    text = ("Ein Wechsel dauert Minuten.\n\n* Siegel helfen.\n"
            "* Die Versorgung ist garantiert.\n* Preise prüfen.")
    sauber, weg = saeubern(text, sperren)
    pruefe("K4 Satz entfernt", "garantiert" not in sauber and len(weg) == 1)
    pruefe("K4b Struktur", sauber.startswith("Ein Wechsel") and "* Siegel helfen." in sauber
           and "* Preise prüfen." in sauber)
    pruefe("K4c Rest sauber", sperren.sauber(sauber))

    # K5 Glättung: Flexionen bleiben grammatisch
    for eingabe, erwartet in (
        ("gesetzlich garantiert", "gesetzlich gesichert"),
        ("garantierte Rendite", "gesicherte Rendite"),
        ("garantiertem Ertrag", "gesichertem Ertrag"),
        ("risikofreie Anlage", "risikoarme Anlage"),
        ("Anlegen ohne Risiko", "Anlegen mit begrenztem Risiko"),
        ("wirst schnell reich", "wirst finanziell unabhängig"),
        ("zu 100 % sicher", "weitgehend sicher"),
    ):
        geglaettet, _ = glaetten(eingabe, sperren)
        pruefe(f"K5 Glättung {eingabe!r}", geglaettet == erwartet
               and sperren.sauber(geglaettet))

    # K6 Grossschreibung bleibt erhalten
    pruefe("K6 Grossschreibung", glaetten("Garantiert!", sperren)[0] == "Gesichert!")

    # K7 Notfall: alles belastet → Glättung, nie Unsauberes
    hart, _ = haerten("Die Versorgung ist garantiert.", sperren)
    pruefe("K7 Notfall-Glättung", hart == "Die Versorgung ist gesichert."
           and sperren.sauber(hart))

    # K8 Kein Ausweg: unglättbare Sperre → leerer Text (fail-closed)
    eigen = Sperren(("unmöglich",), ())
    leer, _ = haerten("Das ist unmöglich.", eigen)
    pruefe("K8 fail-closed", leer == "")

    # K9 Material: belastete Takeaways/Hooks verschwinden, Titel bleibt
    artikel, weg = material_saeubern(_fixture_artikel(), sperren)
    pruefe("K9 Takeaways", not any(sperren.treffer(t) for t in artikel["takeaways"])
           and len(artikel["takeaways"]) == 3
           and "gesichert" in " ".join(artikel["takeaways"]))
    pruefe("K9b Hook", all("risikofrei" not in h for h in artikel["hook_sentences"]))
    pruefe("K9c Kurzantwort", "garantiert" not in artikel["kurzantwort"])
    pruefe("K9d FAQ", "schnelllebigen" not in artikel["faq_answer"])
    pruefe("K9e Titel unangetastet", artikel["title"] == "Ökostrom wechseln: sicher und bezahlbar")
    pruefe("K9f Belege", len(weg) >= 3)

    # K10 Titel-Glättung nur bei Bedarf
    titel_artikel, _ = material_saeubern(
        {"title": "Garantiert schnell reich werden", "takeaways": []}, sperren)
    pruefe("K10 Titel geglättet",
           titel_artikel["title"] == "Gesichert finanziell unabhängig werden")

    # K11 Ohne Sperren keine Veränderung (kein Kollateralschaden)
    unveraendert, weg0 = material_saeubern(_fixture_artikel(), Sperren())
    pruefe("K11 unverändert", unveraendert["kurzantwort"].endswith("garantiert.")
           and weg0 == [] and haerten("Alles gut.", Sperren()) == ("Alles gut.", []))

    # K12 Leerer Text / None bleiben leer (keine Ausnahme)
    pruefe("K12 leer", haerten("", sperren) == ("", []) and saeubern("", sperren) == ("", []))

    # K13 Quellen-Vertrag: die Sperrliste kommt aus der YAML des Hauses
    try:
        import os
        import social_channels as sch
        cfg = sch.load_config(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "data", "social", "channels.yaml"))
        haus = sperrlisten(sch.meta_of(cfg))
        pruefe("K13 Haus-Liste", "garantiert" in haus.begriffe and haus.phrasen)
    except Exception as fehler:      # pragma: no cover – Umgebung ohne YAML
        rot.append(f"K13 Haus-Liste nicht lesbar: {fehler}")
        faelle += 1

    if rot:
        print("🛑 SOCIAL-CLAIMS SELBSTTEST – Befunde:")
        for name in rot:
            print(f"   ✗ {name}")
        return 1
    print(f"✅ SOCIAL-CLAIMS SELBSTTEST: {faelle} Fälle grün "
          "(Sperrquelle, Satz-Heilung, Glättung, Notfall, Material, fail-closed).")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selbsttest()
    print(__doc__ or "")
    print("Nutzung: python3 scripts/social_claims.py --selftest")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
