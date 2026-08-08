#!/usr/bin/env python3
"""Watchdog Check 4: Ist das GitHub-TLS-Zertifikat für franksfinanzcheck.de ausgestellt?

Prüft, ob GitHub Pages für die Custom-Domain bereits ein TLS-Zertifikat
ausgestellt hat (SAN enthält franksfinanzcheck.de). Sobald das der Fall ist,
kann Cloudflare von "Full" auf "Full (strict)" umgestellt werden.

Exit-Codes:
  0 = Ja, Zertifikat vorhanden (SAN enthält die Domain)
  1 = Nein, noch nicht vorhanden (oder Netzwerkfehler/Timeout)

Aufruf aus .github/workflows/bot-watchdog.yml:
  if python3 scripts/watchdog_check4_tls.py 2>/dev/null; then CERT_OK=1; fi
"""
import socket
import ssl
import sys

HOST = "franksfinanzcheck.de"
GITHUB_PAGES_IP = "185.199.108.153"  # einer der GitHub-Pages-A-Records
PORT = 443
TIMEOUT = 8


def main() -> int:
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((GITHUB_PAGES_IP, PORT), timeout=TIMEOUT) as sock:
            with ctx.wrap_socket(sock, server_hostname=HOST) as tls:
                cert = tls.getpeercert()
    except Exception:
        # Zertifikat (noch) nicht vorhanden, Timeout oder Netzwerkfehler:
        # wie "nicht ausgestellt" behandeln – kein falscher Alarm.
        return 1

    san = [v for k, v in cert.get("subjectAltName", [])]
    return 0 if any(HOST in s for s in san) else 1


if __name__ == "__main__":
    sys.exit(main())
