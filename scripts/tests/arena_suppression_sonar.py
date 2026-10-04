"""Diagnose-Datei (Arena, 2026-10-04, Runde 2): Welcher Python-Idiom bricht
den Taint-Flow von py/path-injection zuverlässig? Nach der Auswertung wird
der wirksame Kandidat in n8n_bridge.py übernommen und diese Datei entfernt.

Taint-Quelle: os.environ (von CodeQL als PathInjection-Quelle anerkannt).
Kandidaten (jeweils Sink: os.makedirs + open mit taint-abhängigem Pfad):
  K1 – dict-Lookup: taint steuert nur die Auswahl aus konstanten Pfaden
  K2 – re.fullmatch().group(0): validierter Teilstring als Pfadbestandteil
  K3 – Zeichen-Whitelist per Comprehension (nur [A-Za-z0-9-])
  K4 – Kontrolle: re.sub-Ersetzung wie im aktuellen n8n_bridge.py – diese
       Fundstelle ist die ERWARTETE Meldebestätigung (Test-Schärfe-Beweis).
"""
import json
import os
import re

_WURZEL = os.path.join(os.sep, "tmp", "arena-diagnose")

# Taint-Quelle (analog n8n: ungeparster Webhook-Body von außen).
_BODY = os.environ.get("ARENA_BODY") or '{"k1": "../boese", "k2": "mein-draft", "k3": "a/b", "k4": "../../etc"}'
payload = json.loads(_BODY)


def _kandidat1_dict_lookup(body):
    # K1: Der resultierende Pfad stammt IMMER aus der Konstante; der taint
    # geht nur in den Lookup-Schluessel (Vergleich), nicht in den Wert.
    katalog = {"mein-draft": "mein-draft", "a": "a", "b": "b"}
    slug = str(body.get("k1") or "entwurf")
    ordner = katalog.get(slug, "entwurf")
    ziel = os.path.join(_WURZEL, "k1", ordner)
    os.makedirs(ziel, exist_ok=True)
    with open(os.path.join(ziel, "index.md"), "w", encoding="utf-8") as fh:
        fh.write("K1")


def _kandidat2_fullmatch_group(body):
    # K2: Nur ein vollstaendig whitelisted Zeichenmuster darf in den Pfad.
    slug = str(body.get("k2") or "entwurf")
    treffer = re.fullmatch(r"[A-Za-z0-9_-]{1,80}", slug)
    ziel = os.path.join(_WURZEL, "k2", treffer.group(0) if treffer else "entwurf")
    os.makedirs(ziel, exist_ok=True)
    with open(os.path.join(ziel, "index.md"), "w", encoding="utf-8") as fh:
        fh.write("K2")


def _kandidat3_zeichenfilter(body):
    # K3: Jedes Zeichen einzeln gegen die Whitelist, dann Join.
    slug = str(body.get("k3") or "entwurf")
    sauber = "".join(c for c in slug if re.fullmatch(r"[A-Za-z0-9-]", c)) or "entwurf"
    ziel = os.path.join(_WURZEL, "k3", sauber)
    os.makedirs(ziel, exist_ok=True)
    with open(os.path.join(ziel, "index.md"), "w", encoding="utf-8") as fh:
        fh.write("K3")


def _kontrolle_re_sub(body):
    # K4 (Kontrolle): re.sub-Ersetzung – genau wie im aktuellen n8n_bridge.py;
    # diese Fundstelle ERWARTET sich als Meldebestaetigung.
    slug = re.sub(r"[^\w-]+", "-", str(body.get("k4") or "entwurf")).strip("-") or "entwurf"
    ziel = os.path.join(_WURZEL, "k4", slug)
    os.makedirs(ziel, exist_ok=True)
    with open(os.path.join(ziel, "index.md"), "w", encoding="utf-8") as fh:
        fh.write("K4")


if os.environ.get("ARENA_DIAGNOSE_AUSFUEHREN"):
    _kandidat1_dict_lookup(payload)
    _kandidat2_fullmatch_group(payload)
    _kandidat3_zeichenfilter(payload)
    _kontrolle_re_sub(payload)
