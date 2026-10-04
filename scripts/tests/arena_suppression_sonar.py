"""Diagnose-Datei (Arena, 2026-10-04): Welches Inline-Suppressionsformat
wirkt in der eingesetzten CodeQL-Version? Nach der Auswertung wieder entfernen.
Erzeugt kontrolliert Alerts für py/clear-text-logging-sensitive-data."""
import os

_T = os.environ.get("RESEND_API_KEY", "")

# Variante A: codeql[] auf der eigenen Zeile direkt darueber
# codeql[py/clear-text-logging-sensitive-data]
print(f"A: {_T}")

# Variante B: codeql[] am Zeilenende der Fundstelle
print(f"B: {_T}")  # codeql[py/clear-text-logging-sensitive-data]

# Variante C: lgtm[] auf der eigenen Zeile direkt darueber (Legacy)
# lgtm[py/clear-text-logging-sensitive-data]
print(f"C: {_T}")

# Variante D: Kontrolle ohne Suppression
print(f"D: {_T}")

# Variante E: codeql[] direkt ueber mehrzeiligem print-Statement
# codeql[py/clear-text-logging-sensitive-data]
print(
    f"E: {_T}"
)
