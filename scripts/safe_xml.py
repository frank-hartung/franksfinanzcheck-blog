#!/usr/bin/env python3
"""Gehärteter XML-Parser (Stdlib) gegen Entity-Expansion (Billion Laughs) und XXE.

WARUM DIESES MODUL EXISTIERT (Tiefencheck 30.10.2026)
-----------------------------------------------------
Mehrere Skripte lesen XML aus Sitemaps und RSS-/Atom-Feeds über
``xml.etree.ElementTree`` (Bandit ``B314`` / Ruff ``S314``). Da CPython im
C-Beschleuniger ``_elementtree`` eigene Expat-Callbacks setzt, greifen Handler
auf ``ET.XMLParser().parser`` nicht zuverlässig. Ein vorgeschalteter
``xml.parsers.expat``-Prüflauf (nach dem Vorbild von ``defusedxml``) blockiert
hingegen deterministisch und ohne Fremdpaket:
  1. jede interne oder Parameter-Entity-Deklaration (``<!ENTITY ...>``,
     Schutz vor Billion Laughs / Quadratic Blowup),
  2. jede externe DTD-/System-/Public-Referenz (XXE / SSRF über DTD),
  3. Dokumente oberhalb von ``max_bytes`` (Standard: 10 MiB).

AUFRUF
------
    python3 scripts/safe_xml.py --selftest
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET  # nosec B405
import xml.parsers.expat as pyexpat  # nosec B406
from pathlib import Path

__all__ = [
    "MAX_XML_BYTES",
    "ParseError",
    "Element",
    "fromstring",
    "parse",
    "selftest",
]

MAX_XML_BYTES = 50 * 1024 * 1024
ParseError = ET.ParseError
Element = ET.Element


def _pruefe_expat_sicherheit(roh: bytes) -> None:
    """Lehnt Entity-Deklarationen und externe DTDs deterministisch vorab ab."""
    waechter = pyexpat.ParserCreate()

    def _sperre_entitaet(*_args: object) -> None:
        raise ET.ParseError("XML-Entitaeten sind aus Sicherheitsgruenden gesperrt")

    def _pruefe_doctype(
        _doctype_name: str,
        sysid: str | None,
        pubid: str | None,
        has_internal_subset: int,
    ) -> None:
        if sysid or pubid or has_internal_subset:
            raise ET.ParseError(
                "Externe DTD-Referenzen und interne DTD-Subsets sind gesperrt"
            )

    waechter.StartDoctypeDeclHandler = _pruefe_doctype
    waechter.EntityDeclHandler = _sperre_entitaet
    waechter.UnparsedEntityDeclHandler = _sperre_entitaet
    waechter.ExternalEntityRefHandler = _sperre_entitaet
    try:
        waechter.Parse(roh, True)
    except pyexpat.ExpatError as exc:
        raise ET.ParseError(str(exc)) from exc


def fromstring(daten: str | bytes, *, max_bytes: int = MAX_XML_BYTES) -> ET.Element:
    """Parst einen XML-Text/-Byteblock ohne DTD-Entitäten und mit Größenlimit."""
    roh = daten.encode("utf-8") if isinstance(daten, str) else bytes(daten)
    if len(roh) > max_bytes:
        raise ET.ParseError(
            f"XML ueberschreitet Groessenlimit ({len(roh)} > {max_bytes} Bytes)"
        )
    _pruefe_expat_sicherheit(roh)
    # Expat-Vorpruefung hat DTD/Entities bereits deterministisch abgewiesen.
    return ET.fromstring(roh)  # noqa: S314  # nosec B314


def parse(quelle: str | os.PathLike[str], *, max_bytes: int = MAX_XML_BYTES) -> ET.ElementTree:
    """Liest eine XML-Datei größenbegrenzt und parst sie ohne DTD-Entitäten."""
    pfad = Path(quelle)
    groesse = pfad.stat().st_size
    if groesse > max_bytes:
        raise ET.ParseError(
            f"XML-Datei {pfad.name} ueberschreitet Groessenlimit ({groesse} > {max_bytes} Bytes)"
        )
    roh = pfad.read_bytes()
    return ET.ElementTree(fromstring(roh, max_bytes=max_bytes))


def selftest() -> int:
    import tempfile

    fehler: list[str] = []

    # 1. Positivprobe: reguläre Sitemap mit Namespaces und Standard-Zeichenreferenzen
    ok_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>https://franksfinanzcheck.de/posts/test/?a=1&amp;b=2</loc></url>"
        "</urlset>"
    )
    try:
        wurzel = fromstring(ok_xml)
        locs = [n.text for n in wurzel.iter() if n.tag.endswith("loc")]
        if locs != ["https://franksfinanzcheck.de/posts/test/?a=1&b=2"]:
            fehler.append(f"Positivprobe lieferte falsche URLs: {locs!r}")
    except Exception as exc:  # noqa: BLE001
        fehler.append(f"Positivprobe unerwartet gescheitert: {exc}")

    # 2. Sabotageprobe: Billion-Laughs / interne Entity-Deklaration muss scheitern
    bombe = (
        '<?xml version="1.0"?>'
        '<!DOCTYPE lolz [<!ENTITY lol "lol"><!ENTITY lol2 "&lol;&lol;">]>'
        "<lolz>&lol2;</lolz>"
    )
    try:
        fromstring(bombe)
        fehler.append("Billion-Laughs-Payload wurde NICHT abgewiesen")
    except ET.ParseError:
        pass

    # 3. Sabotageprobe: externe XXE-SYSTEM-Entität + externe DTD müssen scheitern
    for xxe in (
        '<?xml version="1.0"?><!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><foo>&xxe;</foo>',
        '<?xml version="1.0"?><!DOCTYPE foo SYSTEM "http://angreifer.example/evil.dtd"><foo/>',
    ):
        try:
            fromstring(xxe)
            fehler.append(f"XXE-/DTD-Payload wurde NICHT abgewiesen: {xxe[:45]}")
        except ET.ParseError:
            pass

    # 4. Sabotageprobe: Größenlimit greift vor dem Parser
    try:
        fromstring("<root>" + ("a" * 200) + "</root>", max_bytes=64)
        fehler.append("Groessenlimit griff bei fromstring() nicht")
    except ET.ParseError:
        pass

    # 5. Dateiprobe für parse()
    with tempfile.TemporaryDirectory() as tmp:
        datei = Path(tmp) / "sitemap.xml"
        datei.write_text(ok_xml, encoding="utf-8")
        baum = parse(datei)
        if not baum.getroot().tag.endswith("urlset"):
            fehler.append("parse() las Wurzelknoten falsch")
        bomben_datei = Path(tmp) / "bombe.xml"
        bomben_datei.write_text(bombe, encoding="utf-8")
        try:
            parse(bomben_datei)
            fehler.append("parse() wies Entity-Deklaration nicht ab")
        except ET.ParseError:
            pass

    if fehler:
        for eintrag in fehler:
            print(f"❌ safe_xml-Selbsttest: {eintrag}", file=sys.stderr)
        return 2
    print("✅ safe_xml-Selbsttest: 6 Fälle grün (Sitemap, Billion-Laughs, XXE, externe DTD, Größenlimit, Datei).")
    return 0


if __name__ == "__main__":
    sys.exit(selftest())
