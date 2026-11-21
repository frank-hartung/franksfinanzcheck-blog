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

    def test_bei_inaktiver_manueller_einbindung_wird_nichts_geladen(self):
        if _manual_aktiv():
            self.skipTest("manuelle Einbindung ist aktiv – die CSP-Regel unten "
                          "greift dann und muss grün sein")
        # Der ruhige Zustand: kein Beacon im gebauten HTML, also keine
        # CSP-Verletzung. Genau das stellt das Partial über seine Bedingung
        # sicher.
        text = PARTIAL.read_text(encoding="utf-8")
        self.assertIn('eq $cfMode "manual"', text,
                      "das Partial rendert ohne mode=manual – dann lädt es "
                      "den Beacon immer und die CSP-Regel wird zwingend")
        self.assertNotIn(BEACON_DOMAIN, _csp_direktive("script-src"),
                         "CSP erlaubt den Beacon, obwohl er nicht geladen wird – "
                         "das ist eine unnötige Angriffsfläche")

    def test_wenn_geladen_dann_in_der_csp_erlaubt(self):
        """Der Kern: manual + Token gesetzt ⇒ script-src MUSS die Domain tragen."""
        if _manual_aktiv():
            self.assertIn(BEACON_DOMAIN, _csp_direktive("script-src"),
                          "Der Beacon wird ausgeliefert, aber die CSP verbietet "
                          "ihn – der Browser blockt ihn (Layout-Audit-Befund "
                          "vom 21.11.2026). Ergänze die Domain in "
                          "static/_headers (script-src UND connect-src) und in "
                          "cloudflare/edge-schutz.md.")
            self.assertIn(BEACON_DOMAIN, _csp_direktive("connect-src"))
        else:
            self.assertNotIn(BEACON_DOMAIN, _csp_direktive("script-src"))

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
