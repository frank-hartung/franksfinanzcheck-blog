#!/usr/bin/env python3
"""Host-Wahrheit für URLs – eine Quelle statt Substring-Raten.

WARUM ES DIESES MODUL GIBT (Code-Scanning-Alert #83, 10.10.2026)
----------------------------------------------------------------
``"api.pinterest.com" in url`` ist keine Prüfung, sondern eine Vermutung.
Die Zeichenkette darf an **jeder** Stelle der URL stehen:

    https://api.pinterest.com.angreifer.example/v5/pins   → enthält sie
    https://angreifer.example/?ziel=api.pinterest.com     → enthält sie
    https://api.pinterest.com/v5/pins                     → gemeint war nur die

Dieselbe Lücke hat jedes ``startswith("https://host")`` (beliebige
Fortsetzung des Hostnamens) und jedes ``endswith("host.de")`` (beliebiger
Präfix – ``boese-host.de``). CodeQL nennt diese Klasse
``py/incomplete-url-substring-sanitization`` bzw.
``js/incomplete-url-substring-sanitization`` (Security-Severity 7.8).

Die Heilung ist immer dieselbe: **URL parsen, Host vergleichen.** Damit das
nicht in jedem Skript neu (und jedes Mal etwas anders) passiert, steht die
Wahrheit hier – mit Selbsttest und Umgehungsproben.

WAS HIER STEHT
--------------
``host_von(url)``                    – Hostname, klein, ohne Port/Benutzerteil
``ist_host(url, *hosts)``            – Schema + Host exakt (keine Suffix-Falle)
``ist_host_oder_subdomain(url, b)``  – Host == b ODER echte Subdomain von b
``nennt_host(text, host)``           – Host-Erwähnung in beliebigem TEXT mit
                                       Namensgrenzen (Code-/Textsuche, keine
                                       URL-Validierung)
``ruft_host_an(quelltext, host)``    – spricht dieser PYTHON-Quelltext wirklich
                                       mit dem Host? (URL-Literal im AST, nicht
                                       bloße Erwähnung in Doku oder Fixture)
``absolute_links(text)``             – alle absoluten http(s)-Links aus Text
``hat_link_auf_host(text, *hosts)``  – Host-exakte Antwort auf „steht in
                                       diesem Text ein Link auf X?“

ABGRENZUNG
----------
``nennt_host`` ist bewusst **keine** URL-Prüfung: Es beantwortet die Frage
„kommt dieser Hostname als eigenständiger Name im Text vor?“ (z. B. bei der
Quelltext-Suche der Governance-Wache). Für Entscheidungen über eine konkrete
URL ist ausschließlich ``ist_host`` / ``ist_host_oder_subdomain`` zuständig.

AUFRUF
------
    python3 scripts/url_host.py --selftest     # Eigenprüfung inkl. Umgehungen
"""
from __future__ import annotations

import ast
import re
import sys
from urllib.parse import urlsplit

__all__ = [
    "host_von",
    "ist_host",
    "ist_host_oder_subdomain",
    "nennt_host",
    "ruft_host_an",
    "absolute_links",
    "hat_link_auf_host",
    "selftest",
]

# http(s) ist die einzige Transportklasse, über die dieses Repo entscheidet.
STANDARD_SCHEMATA: tuple[str, ...] = ("https", "http")

# Zeichen, die Teil eines Hostnamens sein können. Steht links oder rechts der
# Fundstelle eines dieser Zeichen, ist der gefundene Name NICHT der gesuchte
# Host, sondern Teil eines längeren Namens (`boese-api.pinterest.com`,
# `api.pinterest.com.angreifer.example`).
_NAMENSZEICHEN = r"0-9A-Za-z.\-_"

# Absolute Links: bis zum ersten Zeichen, das in Fließtext/Markdown/HTML eine
# Grenze ist. Schluss-Satzzeichen werden danach abgeschnitten.
_LINK_MUSTER = re.compile(r"""https?://[^\s<>"'`)\]}\\]+""", re.IGNORECASE)
_LINK_SCHLUSS = ".,;:!?"

# Ein Hostname besteht aus Buchstaben, Ziffern, Punkt und Bindestrich (IDN
# kommen als Punycode an); IPv6-Adressen liefert `urlsplit` ohne Klammern.
# `urlsplit` ist absichtlich nachsichtig und gibt z. B. für "kein:// ding"
# noch " ding" zurück – solche Gebilde sind hier kein Host.
_HOST_ERLAUBT = re.compile(r"\A(?:[0-9a-z\-]+(?:\.[0-9a-z\-]+)*|[0-9a-f:]+)\Z", re.IGNORECASE)


def host_von(url: object) -> str:
    """Hostname einer URL – klein geschrieben, ohne Port und Benutzerteil.

    Liefert "" für alles, was keine brauchbare absolute URL ist. Der
    Benutzerteil wird von ``urlsplit`` korrekt abgetrennt: Bei
    ``https://api.resend.com@angreifer.example/`` ist der Host
    ``angreifer.example`` – genau das, was der Browser ansteuert.
    """
    try:
        teile = urlsplit(str(url))
    except ValueError:
        return ""
    name = (teile.hostname or "").lower().rstrip(".")
    return name if _HOST_ERLAUBT.match(name) else ""


def ist_host(url: object, *hosts: str, schemata: tuple[str, ...] = STANDARD_SCHEMATA) -> bool:
    """True, wenn ``url`` ein erlaubtes Schema UND exakt einen der Hosts hat.

    Der Vergleich ist exakt – ``api.resend.com.angreifer.example`` ist nicht
    ``api.resend.com``. Subdomains gelten hier NICHT als Treffer; dafür gibt es
    ``ist_host_oder_subdomain``.
    """
    try:
        teile = urlsplit(str(url))
    except ValueError:
        return False
    if teile.scheme.lower() not in {s.lower() for s in schemata}:
        return False
    name = host_von(url)
    if not name:
        return False
    return name in {str(h).lower().rstrip(".") for h in hosts if h}


def ist_host_oder_subdomain(url: object, basis: str,
                            schemata: tuple[str, ...] = STANDARD_SCHEMATA) -> bool:
    """True für ``basis`` selbst und für echte Subdomains von ``basis``.

    Die Punkt-Grenze ist der ganze Trick: ``endswith("pages.dev")`` würde auch
    ``boesepages.dev`` akzeptieren, ``endswith(".pages.dev")`` immerhin nur
    echte Subdomains – aber beide prüfen die ZEICHENKETTE statt den HOST und
    akzeptieren daher auch ``https://angreifer.example/?x=a.pages.dev``.
    """
    basis = str(basis).lower().strip().lstrip(".").rstrip(".")
    if not basis:
        return False
    try:
        teile = urlsplit(str(url))
    except ValueError:
        return False
    if teile.scheme.lower() not in {s.lower() for s in schemata}:
        return False
    name = host_von(url)
    if not name:
        return False
    return name == basis or name.endswith("." + basis)


def nennt_host(text: object, host: str) -> bool:
    """Kommt ``host`` als eigenständiger Name in ``text`` vor? (Text-/Codesuche)

    Für Quelltext- und Textsuchen, NICHT für Entscheidungen über eine konkrete
    URL. Gegenüber ``host in text`` prüft diese Funktion die Namensgrenzen:
    ``fake-api.pinterest.com`` und ``api.pinterest.com.angreifer.example``
    sind andere Namen und zählen nicht als Treffer.
    """
    name = str(host).strip().strip(".")
    if not name:
        return False
    muster = re.compile(
        r"(?<![" + _NAMENSZEICHEN + r"])" + re.escape(name) + r"(?![" + _NAMENSZEICHEN + r"])",
        re.IGNORECASE)
    return bool(muster.search(str(text)))


def ruft_host_an(quelltext: object, host: str,
                 schemata: tuple[str, ...] = STANDARD_SCHEMATA) -> bool:
    """Spricht dieser **Python-Quelltext** mit dem Host – oder nennt er ihn nur?

    Geprüft werden die Zeichenketten-Literale des AST: Nur ein Literal, das
    selbst eine URL auf diesen Host IST (`"https://api.example.com/v5"`),
    zählt. Eine Erwähnung in Doku, Kommentar, Fehlermeldung oder Test-Fixture
    (`'requests.get("https://api.example.com/v5")'` als Beispieltext) zählt
    nicht – sonst meldet eine Governance-Regel Lärm statt Befunden.

    Nicht parsbarer Quelltext fällt auf ``nennt_host`` zurück: lieber einmal
    zu viel melden als eine echte Transportstrecke übersehen.
    """
    text = str(quelltext)
    try:
        baum = ast.parse(text)
    except (SyntaxError, ValueError, RecursionError):
        return nennt_host(text, host)
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str) \
                and ist_host(knoten.value, host, schemata=schemata):
            return True
    return False


def absolute_links(text: object) -> list[str]:
    """Alle absoluten http(s)-Links aus Fließtext, Markdown oder HTML."""
    gefunden: list[str] = []
    for roh in _LINK_MUSTER.findall(str(text)):
        link = roh.rstrip(_LINK_SCHLUSS)
        if link:
            gefunden.append(link)
    return gefunden


def hat_link_auf_host(text: object, *hosts: str,
                      mit_subdomains: bool = False,
                      schemata: tuple[str, ...] = STANDARD_SCHEMATA) -> bool:
    """Steht in ``text`` ein absoluter Link auf einen dieser Hosts?

    Host-exakt: Ein erwähnter Hostname ohne Link (`franksfinanzcheck.de` als
    Wort im Satz) ist kein Treffer, ein Link auf
    ``https://franksfinanzcheck.de.angreifer.example/`` ebenso wenig.
    """
    for link in absolute_links(text):
        if mit_subdomains:
            if any(ist_host_oder_subdomain(link, h, schemata=schemata) for h in hosts if h):
                return True
        elif ist_host(link, *hosts, schemata=schemata):
            return True
    return False


# --------------------------------------------------------------------------- #
#  Eigenprüfung – jede Zeile davon ist eine Umgehung, die früher funktioniert hätte
# --------------------------------------------------------------------------- #
def selftest() -> int:
    fehler: list[str] = []
    proben = 0

    def pruefe(name: str, ist, soll) -> None:
        nonlocal proben
        proben += 1
        if ist != soll:
            fehler.append(f"{name}: erwartet {soll!r}, bekam {ist!r}")

    # host_von
    pruefe("host_von/einfach", host_von("https://api.resend.com/emails"), "api.resend.com")
    pruefe("host_von/port", host_von("https://api.resend.com:443/x"), "api.resend.com")
    pruefe("host_von/gross", host_von("HTTPS://API.Resend.COM/"), "api.resend.com")
    pruefe("host_von/benutzerteil",
           host_von("https://api.resend.com@angreifer.example/"), "angreifer.example")
    pruefe("host_von/punkt_am_ende", host_von("https://api.resend.com./x"), "api.resend.com")
    pruefe("host_von/relativ", host_von("/go/gas/"), "")
    pruefe("host_von/muell", host_von("kein:// ding"), "")
    pruefe("host_von/none", host_von(None), "")

    # ist_host – die klassischen Umgehungen
    pruefe("ist_host/treffer", ist_host("https://api.resend.com/emails", "api.resend.com"), True)
    pruefe("ist_host/suffixfalle",
           ist_host("https://api.resend.com.angreifer.example/x", "api.resend.com"), False)
    pruefe("ist_host/praefixfalle",
           ist_host("https://boese-api.resend.com/x", "api.resend.com"), False)
    pruefe("ist_host/query",
           ist_host("https://angreifer.example/?ziel=api.resend.com", "api.resend.com"), False)
    pruefe("ist_host/benutzerteil",
           ist_host("https://api.resend.com@angreifer.example/", "api.resend.com"), False)
    pruefe("ist_host/schema_falsch",
           ist_host("http://api.resend.com/x", "api.resend.com", schemata=("https",)), False)
    pruefe("ist_host/schema_erlaubt",
           ist_host("http://api.resend.com/x", "api.resend.com"), True)
    pruefe("ist_host/mehrere",
           ist_host("https://www.franksfinanzcheck.de/go/gas/",
                    "franksfinanzcheck.de", "www.franksfinanzcheck.de"), True)
    pruefe("ist_host/leer", ist_host("", "api.resend.com"), False)

    # ist_host_oder_subdomain
    pruefe("subdomain/basis", ist_host_oder_subdomain("https://pages.dev/", "pages.dev"), True)
    pruefe("subdomain/echt",
           ist_host_oder_subdomain("https://vorschau.pages.dev/", "pages.dev"), True)
    pruefe("subdomain/klebrig",
           ist_host_oder_subdomain("https://boesepages.dev/", "pages.dev"), False)
    pruefe("subdomain/suffixfalle",
           ist_host_oder_subdomain("https://pages.dev.angreifer.example/", "pages.dev"), False)
    pruefe("subdomain/im_pfad",
           ist_host_oder_subdomain("https://angreifer.example/a.pages.dev", "pages.dev"), False)
    pruefe("subdomain/punkt_in_basis",
           ist_host_oder_subdomain("https://vorschau.pages.dev/", ".pages.dev"), True)

    # nennt_host – Text-/Codesuche mit Namensgrenzen
    pruefe("nennt/treffer",
           nennt_host('requests.get("https://api.pinterest.com/v5/pins")', "api.pinterest.com"),
           True)
    pruefe("nennt/praefix",
           nennt_host('url = "https://fake-api.pinterest.com/v5"', "api.pinterest.com"), False)
    pruefe("nennt/suffix",
           nennt_host('url = "https://api.pinterest.com.angreifer.example/"',
                      "api.pinterest.com"), False)
    pruefe("nennt/wortgrenze_pfad",
           nennt_host("api.pinterest.com/v5/boards", "api.pinterest.com"), True)
    pruefe("nennt/leer", nennt_host("egal", ""), False)

    # ruft_host_an – Transportstrecke vs. bloße Erwähnung
    pruefe("ruft_an/literal",
           ruft_host_an('BASIS = "https://api.pinterest.com/v5"\n', "api.pinterest.com"), True)
    pruefe("ruft_an/f_string",
           ruft_host_an('url = f"https://api.pinterest.com/v5/{board}"\n', "api.pinterest.com"),
           True)
    pruefe("ruft_an/nur_erwaehnt",
           ruft_host_an('# Doku: api.pinterest.com braucht den Token-Broker\nX = 1\n',
                        "api.pinterest.com"), False)
    pruefe("ruft_an/fixture_text",
           ruft_host_an('PROBE = \'requests.get("https://api.pinterest.com/v5")\'\n',
                        "api.pinterest.com"), False)
    pruefe("ruft_an/fremder_host",
           ruft_host_an('BASIS = "https://api.pinterest.com.angreifer.example/v5"\n',
                        "api.pinterest.com"), False)
    pruefe("ruft_an/kaputt_faellt_zurueck",
           ruft_host_an('def kaputt(:\n  api.pinterest.com\n', "api.pinterest.com"), True)

    # absolute_links / hat_link_auf_host
    text = ("Siehe [Gas](https://franksfinanzcheck.de/go/gas/) und "
            "<a href=\"https://www.pinterest.de/franksfinanzcheck/\">Pin</a>. "
            "Mehr unter https://franksfinanzcheck.de/newsletter/.")
    pruefe("links/anzahl", len(absolute_links(text)), 3)
    pruefe("links/schlusspunkt",
           absolute_links("Ende: https://franksfinanzcheck.de/newsletter/.")[0],
           "https://franksfinanzcheck.de/newsletter/")
    pruefe("linkauf/treffer", hat_link_auf_host(text, "franksfinanzcheck.de"), True)
    pruefe("linkauf/www_ist_anderer_host",
           hat_link_auf_host("[P](https://www.franksfinanzcheck.de/go/gas/)",
                             "franksfinanzcheck.de"), False)
    pruefe("linkauf/www_mit_subdomains",
           hat_link_auf_host("[P](https://www.franksfinanzcheck.de/go/gas/)",
                             "franksfinanzcheck.de", mit_subdomains=True), True)
    pruefe("linkauf/suffixfalle",
           hat_link_auf_host("[B](https://franksfinanzcheck.de.angreifer.example/go/gas/)",
                             "franksfinanzcheck.de", mit_subdomains=True), False)
    pruefe("linkauf/nur_erwaehnt",
           hat_link_auf_host("Mehr dazu auf franksfinanzcheck.de im Ratgeber.",
                             "franksfinanzcheck.de"), False)
    pruefe("linkauf/relativ",
           hat_link_auf_host("[Gas](/go/gas/)", "franksfinanzcheck.de"), False)

    if fehler:
        print("❌ URL-HOST-SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print(f"✅ url_host: {proben} Proben bestanden (Host-Exaktheit, Subdomain-Grenze, "
          f"Namensgrenze, Linkauslese).")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv[1:]:
        sys.exit(selftest())
    print(__doc__)
    sys.exit(0)
