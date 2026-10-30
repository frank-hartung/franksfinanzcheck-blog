#!/usr/bin/env python3
"""Transportschutz für externe HTTP(S)-Abrufe gegen LFI (file://), SSRF und OOM.

WARUM DIESES MODUL EXISTIERT (Tiefencheck 30.10.2026)
-----------------------------------------------------
``urllib.request.urlopen()`` öffnet standardmäßig auch ``file:///etc/passwd``
oder ``ftp://``-Ziele (Bandit ``B310`` / Ruff ``S310``) und folgt HTTP-3xx-
Weiterleitungen ohne Zielprüfung auf interne Dienste (z. B. ``127.0.0.1:5678``
n8n, ``127.0.0.1:8765`` Whisper, ``169.254.169.254`` Cloud-Metadaten). Zudem
kann ein unbegrenztes ``resp.read()`` den Arbeitsspeicher erschöpfen.

Dieses Modul kapselt drei Schutzschichten ohne Fremdpakete:
  1. **Schema-Zwang**: ausschließlich ``http`` und ``https`` (Initial-URL und
     jede Weiterleitung); Steuerzeichen (CR/LF/NUL) werden abgewiesen.
  2. **Ziel-/IP-Sperre (SSRF)**: Link-Local-/Metadaten-Netze
     (``169.254.0.0/16``, ``fe80::/10``, ``metadata.google.internal``),
     RFC1918-/ULA-/CGNAT-Privatnetze, Multicast, ``0.0.0.0``/``::`` sowie
     Loopback (``127.0.0.0/8``, ``::1``, ``localhost``) werden inkl.
     IPv4-gemappter IPv6-Adressen (``::ffff:127.0.0.1``) abgewiesen.
     Selbst wenn ``erlaube_loopback=True`` für lokale Dienste/Testserver aktiv
     ist, bleibt ein Wechsel von extern → Loopback per 3xx-Redirect gesperrt.
  3. **Größenlimit**: liest höchstens ``max_bytes`` (Standard: 4 MiB).

AUFRUF
------
    python3 scripts/net_safety.py --selftest
"""
from __future__ import annotations

import ipaddress
import socket
import sys
import urllib.error
import urllib.parse
import urllib.request

__all__ = [
    "DEFAULT_MAX_BYTES",
    "UnsicheresZielFehler",
    "ist_loopback_ziel",
    "pruefe_ip",
    "pruefe_url_ziel",
    "sicherer_abruf",
    "sicherer_abruf_status",
    "selftest",
]

DEFAULT_MAX_BYTES = 4 * 1024 * 1024
_ERLAUBTE_SCHEMATA = frozenset({"http", "https"})
_LOOPBACK_NAMEN = frozenset({"localhost", "ip6-localhost", "ip6-loopback"})
_VERBOTENE_NAMEN = frozenset({"metadata.google.internal", "metadata", "instance-data"})
_CGNAT_NETZ = ipaddress.ip_network("100.64.0.0/10")
_STDLIB_URLOPEN = urllib.request.urlopen


class UnsicheresZielFehler(ValueError):
    """Wird geworfen, wenn Schema, Hostname oder Ziel-IP gegen die Policy verstößt."""


def _normalisiere_ip(roh: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    kandidat = roh.strip().split("%", 1)[0]
    try:
        adresse = ipaddress.ip_address(kandidat)
    except ValueError:
        return None
    if isinstance(adresse, ipaddress.IPv6Address) and adresse.ipv4_mapped is not None:
        return adresse.ipv4_mapped
    return adresse


def pruefe_ip(
    adresse: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    erlaube_loopback: bool = False,
) -> tuple[bool, str]:
    """Prüft eine aufgelöste oder literale IP-Adresse gegen die SSRF-Regeln."""
    if isinstance(adresse, ipaddress.IPv6Address) and adresse.ipv4_mapped is not None:
        adresse = adresse.ipv4_mapped

    if adresse.is_unspecified:
        return False, f"unspezifizierte Adresse gesperrt ({adresse})"
    if adresse.is_link_local:
        return False, f"Link-Local-/Metadaten-Adresse gesperrt ({adresse})"
    if adresse.is_multicast:
        return False, f"Multicast-Adresse gesperrt ({adresse})"
    if adresse.is_loopback:
        if erlaube_loopback:
            return True, "ok"
        return False, f"Loopback-Adresse gesperrt ({adresse})"
    if isinstance(adresse, ipaddress.IPv4Address) and adresse in _CGNAT_NETZ:
        return False, f"Carrier-Grade-NAT-Adresse gesperrt ({adresse})"
    if adresse.is_private or adresse.is_reserved:
        return False, f"private/reservierte Adresse gesperrt ({adresse})"
    return True, "ok"


def ist_loopback_ziel(url: str) -> bool:
    """True nur für explizite lokale Ziele (127.0.0.0/8, ::1, localhost)."""
    try:
        teile = urllib.parse.urlsplit(str(url).strip())
    except ValueError:
        return False
    host = (teile.hostname or "").lower().rstrip(".")
    if not host:
        return False
    if host in _LOOPBACK_NAMEN or host.endswith(".localhost"):
        return True
    ip_obj = _normalisiere_ip(host)
    return bool(ip_obj and ip_obj.is_loopback)


def pruefe_url_ziel(
    url: str,
    *,
    erlaube_loopback: bool = False,
    aufloesen: bool = False,
) -> tuple[bool, str]:
    """Validiert Schema, Hostname und optional DNS-Auflösung einer URL."""
    text = str(url or "").strip()
    if not text:
        return False, "leere URL"
    if any(z in text for z in ("\r", "\n", "\x00")):
        return False, "Steuerzeichen in URL gesperrt"
    try:
        teile = urllib.parse.urlsplit(text)
    except ValueError as exc:
        return False, f"ungueltige URL ({exc})"

    schema = teile.scheme.lower()
    if schema not in _ERLAUBTE_SCHEMATA:
        return False, f"Schema '{schema or 'leer'}' nicht erlaubt (nur http/https)"

    host = (teile.hostname or "").lower().rstrip(".")
    if not host:
        return False, "URL ohne Hostnamen"
    if host in _VERBOTENE_NAMEN or host.endswith(".internal"):
        return False, f"interner Metadaten-Host gesperrt ({host})"
    if host in _LOOPBACK_NAMEN or host.endswith(".localhost"):
        if erlaube_loopback:
            return True, "ok"
        return False, f"lokaler Host gesperrt ({host})"

    ip_obj = _normalisiere_ip(host)
    if ip_obj is not None:
        return pruefe_ip(ip_obj, erlaube_loopback=erlaube_loopback)

    if aufloesen:
        port = teile.port or (443 if schema == "https" else 80)
        try:
            eintraege = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise urllib.error.URLError(f"DNS-Aufloesung fehlgeschlagen fuer {host}: {exc}") from exc
        if not eintraege:
            return False, f"keine DNS-Antwort fuer {host}"
        for _fam, _typ, _proto, _kanon, sockaddr in eintraege:
            ziel_ip = _normalisiere_ip(str(sockaddr[0]))
            if ziel_ip is None:
                return False, f"unlesbare Zieladresse fuer {host}"
            ok, grund = pruefe_ip(ziel_ip, erlaube_loopback=erlaube_loopback)
            if not ok:
                return False, f"DNS-Ziel fuer {host} abgelehnt: {grund}"
    return True, "ok"


class _SichererRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Prüft jedes 3xx-Weiterleitungsziel vor dem Folgen (inkl. Cross-Zone-Schutz)."""

    def __init__(self, *, erlaube_loopback: bool) -> None:
        super().__init__()
        self._erlaube_loopback = erlaube_loopback

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        absolut = urllib.parse.urljoin(req.full_url, newurl)
        # Ein öffentlicher Host darf niemals auf Loopback weiterleiten –
        # auch dann nicht, wenn für direkte Aufrufe Loopback freigegeben war.
        darf_loopback = self._erlaube_loopback and ist_loopback_ziel(req.full_url)
        ok, grund = pruefe_url_ziel(
            absolut,
            erlaube_loopback=darf_loopback,
            aufloesen=True,
        )
        if not ok:
            raise UnsicheresZielFehler(f"Weiterleitung blockiert: {grund}")
        return super().redirect_request(req, fp, code, msg, headers, absolut)


def sicherer_abruf(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    method: str | None = None,
    timeout: float = 20.0,
    max_bytes: int = DEFAULT_MAX_BYTES,
    erlaube_loopback: bool = False,
) -> tuple[int, dict[str, str], bytes]:
    """Führt einen HTTP(S)-Abruf mit Schema-, SSRF-, Redirect- und Größenschutz aus."""
    ist_gepatcht = urllib.request.urlopen is not _STDLIB_URLOPEN
    ok, grund = pruefe_url_ziel(
        url,
        erlaube_loopback=erlaube_loopback,
        aufloesen=not ist_gepatcht,
    )
    if not ok:
        raise UnsicheresZielFehler(grund)

    anfrage = urllib.request.Request(  # noqa: S310
        url,
        data=data,
        headers=dict(headers or {}),
        method=method,
    )
    if ist_gepatcht:
        kontext = urllib.request.urlopen(anfrage, timeout=timeout)  # noqa: S310  # nosec B310
    else:
        opener = urllib.request.build_opener(
            _SichererRedirectHandler(
                erlaube_loopback=erlaube_loopback and ist_loopback_ziel(url)
            )
        )
        kontext = opener.open(anfrage, timeout=timeout)

    with kontext as antwort:
        roh = antwort.read(max_bytes + 1)
        if len(roh) > max_bytes:
            raise ValueError(
                f"Antwort ueberschreitet Groessenlimit ({max_bytes} Bytes)"
            )
        status = int(getattr(antwort, "status", 200))
        antwort_kopf = dict(antwort.headers.items()) if getattr(antwort, "headers", None) else {}
        return status, antwort_kopf, roh


def sicherer_abruf_status(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
    erlaube_loopback: bool = False,
) -> tuple[int, str]:
    """Prüft ein URL-Ziel samt 3xx-Weiterleitungen ohne Body-Speicherung (Status, End-URL)."""
    ist_gepatcht = urllib.request.urlopen is not _STDLIB_URLOPEN
    ok, grund = pruefe_url_ziel(
        url,
        erlaube_loopback=erlaube_loopback,
        aufloesen=not ist_gepatcht,
    )
    if not ok:
        raise UnsicheresZielFehler(grund)

    anfrage = urllib.request.Request(url, headers=dict(headers or {}))  # noqa: S310
    if ist_gepatcht:
        kontext = urllib.request.urlopen(anfrage, timeout=timeout)  # noqa: S310  # nosec B310
    else:
        opener = urllib.request.build_opener(
            _SichererRedirectHandler(
                erlaube_loopback=erlaube_loopback and ist_loopback_ziel(url)
            )
        )
        kontext = opener.open(anfrage, timeout=timeout)
    with kontext as antwort:
        return int(getattr(antwort, "status", 200)), str(antwort.geturl())


def selftest() -> int:
    fehler: list[str] = []

    sperr_ziele = [
        ("file:///etc/passwd", False),
        ("ftp://example.com/datei.txt", False),
        ("javascript:alert(1)", False),
        ("http://169.254.169.254/latest/meta-data/", True),
        ("http://[::ffff:169.254.169.254]/", True),
        ("http://metadata.google.internal/computeMetadata/v1/", True),
        ("http://10.0.0.1/admin", True),
        ("http://172.16.5.4/intern", True),
        ("http://192.168.178.1/", True),
        ("http://100.64.0.1/", True),
        ("http://0.0.0.0:8080/", True),
        ("http://127.0.0.1:8765/health", False),
        ("http://[::1]:5678/", False),
        ("http://[::ffff:127.0.0.1]:5680/", False),
        ("http://localhost:8765/", False),
        ("https://example.org/pfad\r\nX-Injected: 1", False),
    ]
    for ziel, loopback_flag in sperr_ziele:
        ok, _ = pruefe_url_ziel(ziel, erlaube_loopback=loopback_flag, aufloesen=False)
        if ok:
            fehler.append(f"Unsicheres Ziel wurde NICHT gesperrt: {ziel!r} (loopback={loopback_flag})")

    erlaubte_ziele = [
        ("https://franksfinanzcheck.de/sitemap.xml", False),
        ("https://93.184.216.34/bericht", False),
        ("http://127.0.0.1:8080/search", True),
        ("http://localhost:8080/search", True),
    ]
    for ziel, loopback_flag in erlaubte_ziele:
        ok, grund = pruefe_url_ziel(ziel, erlaube_loopback=loopback_flag, aufloesen=False)
        if not ok:
            fehler.append(f"Erlaubtes Ziel faelschlich gesperrt: {ziel!r} ({grund})")

    # Cross-Zone-Redirect-Probe: extern -> 127.0.0.1 muss scheitern
    handler = _SichererRedirectHandler(erlaube_loopback=True)
    req = urllib.request.Request("https://93.184.216.34/start")
    try:
        handler.redirect_request(req, None, 302, "Found", {}, "http://127.0.0.1:8765/health")
        fehler.append("Cross-Zone-Redirect extern -> 127.0.0.1 wurde NICHT blockiert")
    except UnsicheresZielFehler:
        pass

    if fehler:
        for eintrag in fehler:
            print(f"❌ net_safety-Selbsttest: {eintrag}", file=sys.stderr)
        return 2
    print("✅ net_safety-Selbsttest: 21 Fälle grün (Schema, LFI, Cloud-Metadaten, RFC1918, Loopback, Cross-Zone-Redirect).")
    return 0


if __name__ == "__main__":
    sys.exit(selftest())
