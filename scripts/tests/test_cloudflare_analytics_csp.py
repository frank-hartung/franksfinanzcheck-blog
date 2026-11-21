# -*- coding: utf-8 -*-
"""Layout-Audit-Befund vom 21.11.2026: Beacon geladen, CSP verbietet ihn.

DER BEFUND
==========
Das Layout-Audit (Playwright, gebautes HTML) meldete auf jeder betroffenen
Seite dieselbe Konsolenzeile:

    Loading the script 'https://static.cloudflareinsights.com/beacon.min.js'
    violates the following Content Security Policy directive:
    "script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com"

`static/_headers` erlaubt Cloudflare nur für Turnstile
(`challenges.cloudflare.com`). Der Web-Analytics-Beacon läuft über
`static.cloudflareinsights.com` – eine ANDERE Domain.

DIE KLASSE, DIE DIESER TEST SCHLIESST
=====================================
Das Partial `layouts/_partials/cloudflare_analytics.html` rendert den Beacon
nur, wenn `mode = "manual"` UND `website` UND `token` gesetzt sind – in
`hugo.toml` steht nichts davon. Das Skript im Messlauf kann also nur über
Cloudflares automatische Injektion ins ausgelieferte HTML gekommen sein.
Wer das liest, schaltet den Beacon ab oder ergänzt die CSP. Beides ist eine
Entscheidung, keine Vermutung – deshalb steht der Vertrag hier:

    Wer den Beacon lädt, erlaubt seine Domain in der CSP.

Der Test ist bewusst KEIN Gate auf „manuell aktiviert": Er prüft die
Kombination, nicht die Einstellung. Fehlt der Beacon, ist alles gut.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HEADERS = ROOT / "static" / "_headers"
PARTIAL = ROOT / "layouts" / "_partials" / "cloudflare_analytics.html"
HUGO = ROOT / "hugo.toml"

BEACON_DOMAIN = "static.cloudflareinsights.com"
TURNSTILE_DOMAIN = "challenges.cloudflare.com"


def _csp() -> str:
    """Der CSP-WERT aus `static/_headers` (nach dem Header-Namen).

    Bewusst nur der Wert: Die Zeile lautet
    `  Content-Security-Policy: default-src 'self'; script-src …`. Nimmt man
    sie ganz, hängt am ersten Header-Namen ein `: ` – und die Direktiven-
    Suche findet `default-src` nie, weil dort `: default-src` steht. Genau
    daran ist die erste Fassung dieses Tests gescheitert (der Test war
    falsch, nicht die CSP).
    """
    for zeile in HEADERS.read_text(encoding="utf-8").splitlines():
        if "Content-Security-Policy" in zeile:
            return zeile.split("Content-Security-Policy", 1)[1].lstrip(": ")
    return ""


def _csp_direktive(name: str) -> str:
    """Eine einzelne Direktive aus der CSP (z. B. `script-src`)."""
    treffer = re.search(rf"(?:^|;\s*){re.escape(name)}\s+([^;]+)", _csp())
    return treffer.group(1) if treffer else ""


def _manual_aktiv() -> bool:
    """Steht in `hugo.toml` eine AKTIVE manuelle Einbindung?

    Auskommentierte Zeilen sind ausdrücklich nicht aktiv – das ist der
    aktuelle Zustand und der Grund, warum das Partial still bleibt.
    """
    text = HUGO.read_text(encoding="utf-8")
    block = re.search(r"\[params\.analytics\.cloudflare\](.*?)(?=\n\[|\Z)",
                      text, re.S)
    if not block:
        return False
    rumpf = block.group(1)
    aktiv = {}
    for zeile in rumpf.splitlines():
        roh = zeile.strip()
        if not roh or roh.startswith("#"):
            continue
        m = re.match(r"([a-z_]+)\s*=\s*\"?([^\"]*)\"?", roh)
        if m:
            aktiv[m.group(1)] = m.group(2).strip()
    return (aktiv.get("mode") == "manual"
            and bool(aktiv.get("website"))
            and bool(aktiv.get("token")))


class CspDecktDenBeaconTest(unittest.TestCase):
    """Die eine Regel: Wer den Beacon lädt, erlaubt seine Domain."""

    def test_der_beacon_ist_erlaubt_obwohl_das_partial_schweigt(self):
        """Der am 21.11.2026 belegte Betriebszustand.

        Das Partial rendert ohne `mode="manual"` + Token KEIN Skript – und
        trotzdem stand der Beacon im ausgelieferten HTML und wurde von der
        CSP geblockt. Der Ursprung ist keine Repo-Quelle, sondern Cloudflares
        automatische Injektion an der Edge (Dashboard-Einstellung). Ein Repo
        kann diesen Zustand weder herstellen noch abstellen – es kann ihn nur
        ERLAUBEN. Genau das ist hier festgehalten: Bleibt die Injektion aktiv,
        ist die CSP die einzige Stelle, an der das Repo den Browserfehler
        verhindern kann.

        Das ist bewusst keine „unnötige Angriffsfläche": Die Domain ist
        dieselbe Organisation, die den Beacon ohnehin ins HTML schreibt;
        ein CSP-Verbot verhindert nicht die Auslieferung, sondern nur die
        Ausführung – und erzeugt auf jeder Seite einen Konsolenfehler.
        """
        if _manual_aktiv():
            self.skipTest("manuelle Einbindung aktiv – test_wenn_geladen… prüft sie")
        text = PARTIAL.read_text(encoding="utf-8")
        self.assertIn('eq $cfMode "manual"', text,
                      "das Partial rendert ohne mode=manual – dann lädt es "
                      "den Beacon immer und die CSP-Regel wird zwingend")
        self.assertIn(BEACON_DOMAIN, _csp_direktive("script-src"),
                      "Der Beacon wird an der Edge injiziert (belegt am "
                      "21.11.2026: er stand im ausgelieferten HTML, obwohl das "
                      "Partial nichts rendert). Fehlt die Domain in script-src, "
                      "blockt der Browser ihn auf JEDER Seite.")
        self.assertIn(BEACON_DOMAIN.split("static.")[-1], _csp_direktive("connect-src"),
                      "Der Beacon sendet seine Messung per fetch/beacon an "
                      "cloudflareinsights.com – ohne connect-src-Freigabe "
                      "scheitert die Übertragung lautlos.")

    def test_wenn_das_partial_rendert_dann_ist_die_csp_gedeckt(self):
        """Kernregel, beide Richtungen – auch für den manuellen Weg B.

        Rendert das Partial (mode=manual + Token), MUSS die CSP die Domain
        tragen. Rendert es nicht, ist die Domain trotzdem erlaubt, weil die
        Edge-Injektion unabhängig davon stattfindet (siehe Test darüber).
        """
        csp_script = _csp_direktive("script-src")
        self.assertEqual(_manual_aktiv(),
                         bool(re.search(r"^\s*mode\s*=\s*\"manual\"",
                                        HUGO.read_text(encoding="utf-8"), re.M)))
        self.assertIn(BEACON_DOMAIN, csp_script)

    def test_turnstile_bleibt_erlaubt(self):
        """Gegenprobe: Die Reparatur darf den Pflicht-Dienst nicht verlieren."""
        self.assertIn(TURNSTILE_DOMAIN, _csp_direktive("script-src"),
                      "Turnstile braucht script-src – das ist die Challenge "
                      "beim Newsletter, kein Analytics")
        self.assertIn(TURNSTILE_DOMAIN, _csp_direktive("frame-src"))

    def test_partial_nennt_den_csp_vertrag(self):
        """Die Falle darf nicht wieder nur im Bericht stehen."""
        text = PARTIAL.read_text(encoding="utf-8")
        self.assertIn(BEACON_DOMAIN, text,
                      "das Partial lädt den Beacon – es muss seine Domain nennen")
        self.assertIn("_headers", text,
                      "der CSP-Vertrag (static/_headers) muss AM ORT DER "
                      "Einbindung stehen, nicht nur in einem Bericht")


class CspStrukturTest(unittest.TestCase):
    def test_headers_setzt_genau_eine_csp(self):
        self.assertTrue(_csp().strip(), "keine CSP in static/_headers")

    def test_direktiven_sind_nicht_leer(self):
        for name in ("default-src", "script-src", "connect-src"):
            with self.subTest(direktive=name):
                self.assertTrue(_csp_direktive(name).strip(),
                                f"{name} fehlt – dann greift default-src und "
                                "die Regel oben prüft ins Leere")


if __name__ == "__main__":
    unittest.main()
