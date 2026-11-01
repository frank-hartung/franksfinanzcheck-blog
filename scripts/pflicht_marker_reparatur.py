#!/usr/bin/env python3
"""Repariert zerstückelte Pflicht-Kennzeichnungen im Bestand (#964).

DER BEFUND
----------
Der deterministische RS5-Heiler (`redaktions_standard._heal_rs5_block`) hat
über Monate Kennzeichnungen wie „ im Modellfall“ an die ERSTE Punkt-Fundstelle
eines Absatzes gesetzt – ohne zu prüfen, ob dieser Punkt eine Satzgrenze ist.
Bei „ca.“, „z. B.“, Ordnungszahlen und Datumsangaben entstand dadurch
zerstückeltes Deutsch, live und in den Snippets:

    „… spart ca im Modellfall. 500 € und 1.300 € …“
    „… bis zum 30 als Beispielwert. November lassen sich …“
    „… solltest du: 1 als Modellannahme. **Ca. 2 Monate vorher …“

Die Wurzel ist geheilt (`redaktions_standard._kennzeichnung_ans_satzende` +
`sprachkern.PFLICHT_MARKER_RUINEN` als R18 im Publish-Gate). Dieses Skript
repariert den Bestand: Es stellt die zerschnittene Stelle wieder her
(Abkürzung, Datum, Ordnungszahl) und hängt die Kennzeichnung als sauberen
Teilsatz an das Ende des betroffenen Satzes:

    „… fehlen am Ende über 460 € als Beispielwert. Rechne …“
      → „… fehlen am Ende über 460 €; das ist ein Beispielwert. Rechne …“

Die AUSSAGE bleibt unverändert: keine Zahl, kein Betrag und kein Satzinhalt
wird ersetzt. Nur die Kennzeichnung wandert an eine grammatisch tragfähige
Stelle.

Nutzung
  python3 scripts/pflicht_marker_reparatur.py            # Vorschau (Diff-Zähler)
  python3 scripts/pflicht_marker_reparatur.py --apply    # schreiben
  python3 scripts/pflicht_marker_reparatur.py --selftest

Fail-closed: Ein Artikel, dessen Reparatur eine NEUE Politur-Ruine
(R11–R14/R18) einführen würde, wird NICHT geschrieben. Artikel mit
YMYL-Siegel bleiben unangetastet – dort entscheidet die Redaktion.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import sprachkern as sk  # noqa: E402


def ziele() -> list[Path]:
    return sorted((ROOT / 'content').rglob('index.md'))


def _teile(text: str) -> tuple[str, str, str]:
    parts = text.split('---', 2)
    if len(parts) < 3:
        return '', '', text
    return parts[0], parts[1], parts[2]


def _inhalt(text: str) -> list[str]:
    """Wortfolge OHNE Kennzeichnungsfloskeln und ohne Satzzeichen.

    Das ist der Inhaltsbeweis der Reparatur: Zahl, Betrag und Aussage müssen
    byte-gleich erhalten bleiben, egal ob die Kennzeichnung als Teilsatz
    angehängt, gestrichen oder eine Klebstelle („ca.“, „30.“, „1.“)
    wiederhergestellt wird. Satzzeichen zählen nicht mit, weil genau sie
    wandern („.“ → „; das ist ein Modellwert.“).
    """
    ohne = schluessel = text
    for nomen in ('Modellwert', 'Beispielwert', 'Rechenfall', 'Rechenbeispiel',
                  'Modellfall', 'Modellannahme'):
        ohne = ohne.replace(f'als {nomen}', ' ')
        ohne = ohne.replace(f'im {nomen}', ' ')
        ohne = ohne.replace(f'das ist ein {nomen}', ' ')
        ohne = ohne.replace(f'das ist eine {nomen}', ' ')
        ohne = ohne.replace(f'Das ist ein {nomen}', ' ')
        ohne = ohne.replace(f'Das ist eine {nomen}', ' ')
    del schluessel
    return re.findall(r'[^\W_]+', ohne)


def repariere(text: str) -> tuple[str, int]:
    """Repariert NUR den Body; Frontmatter bleibt byte-identisch."""
    kopf, front, body = _teile(text)
    if not front:
        return text, 0
    neu, anzahl = sk.pflicht_marker_heilen(body)
    if anzahl == 0:
        return text, 0
    # Fail-closed: keine NEUE Ruine einführen (R11–R14/R18).
    alt_ruinen = set(sk.politur_ruine_funde(body))
    neu_ruinen = set(sk.politur_ruine_funde(neu)) - alt_ruinen
    if neu_ruinen:
        return text, 0
    # Fail-closed: Der Inhalt muss unverändert sein. Verglichen wird die
    # Wortfolge OHNE Kennzeichnungsfloskeln – die Kennzeichnung selbst darf
    # wandern, gestrichen oder ergänzt werden, die Aussage nicht.
    if _inhalt(neu) != _inhalt(body):
        return text, 0
    return f"{kopf}---{front}---{neu}", anzahl


def selftest() -> int:
    fehler = []
    proben = [
        # (Eingabe, erwartete Teilzeichenkette, verbotene Teilzeichenkette)
        ('Der Beitrag steigt als Modellwert. 500 € kommen dazu.',
         'Der Beitrag steigt. 500 €', 'als Modellwert.'),
        ('Kündige bis zum 30 als Beispielwert. November, sonst zahlst du.',
         '30. November', 'als Beispielwert.'),
        ('Der Preis liegt bei ca als Modellannahme. 11 Cent.',
         'ca. 11 Cent', 'als Modellannahme.'),
        ('Eine Garantie (z als Modellwert. B. 24 Monate) gilt.',
         'z. B. 24 Monate', 'als Modellwert.'),
    ]
    for eingabe, muss, darf_nicht in proben:
        _kopf, _front, body = _teile(f'---\ntitel: x\n---\n{eingabe}')
        neu, anzahl = sk.pflicht_marker_heilen(body)
        if anzahl != 1:
            fehler.append(f'{eingabe!r}: {anzahl} Reparaturen statt 1')
        if muss not in neu:
            fehler.append(f'{eingabe!r} → {neu!r}: „{muss}“ fehlt')
        if darf_nicht in neu:
            fehler.append(f'{eingabe!r} → {neu!r}: Ruine „{darf_nicht}“ bleibt')
        if sk.pflicht_marker_funde(neu):
            fehler.append(f'{eingabe!r} → {neu!r}: R18 bleibt')
    # Korrektes Deutsch darf NICHTS ändern.
    for sauber in ('Das ist eine Modellannahme.',
                   'Der Tarif kostet 460 € im Jahr; das ist ein Beispielwert.',
                   'Ein Haus braucht 18.000 kWh im Jahr; das ist ein Modellwert.'):
        neu, anzahl = sk.pflicht_marker_heilen(sauber)
        if (neu, anzahl) != (sauber, 0):
            fehler.append(f'Falsch-Positiv: {sauber!r} → {neu!r} ({anzahl})')
    if fehler:
        print('🛑 Selbsttest Pflicht-Kennzeichnung fehlgeschlagen:')
        for f in fehler:
            print(f'  • {f}')
        return 2
    print('✅ Pflicht-Kennzeichnung: 4 Realfälle repariert, 3 korrekte Sätze unberührt.')
    return 0


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--apply', action='store_true', help='Änderungen schreiben')
    p.add_argument('--selftest', action='store_true', help='nur Selbsttest')
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()
    if selftest() != 0:
        return 2

    betroffen, summe, gesperrt = [], 0, []
    for pfad in ziele():
        text = pfad.read_text(encoding='utf-8')
        if not sk.pflicht_marker_funde(text):
            continue
        neu, anzahl = repariere(text)
        rel = pfad.relative_to(ROOT)
        if anzahl == 0:
            gesperrt.append(str(rel))
            continue
        betroffen.append((rel, anzahl))
        summe += anzahl
        if args.apply:
            pfad.write_text(neu, encoding='utf-8')

    for rel, anzahl in betroffen:
        print(f'{"✍" if args.apply else "·"} {rel}: {anzahl} Reparatur(en)')
    for rel in gesperrt:
        print(f'⚠ {rel}: Reparatur verworfen (fail-closed, manuell prüfen)')
    print(f'\n{summe} Reparatur(en) in {len(betroffen)} Datei(en)'
          f'{" geschrieben" if args.apply else " gefunden (Vorschau)"}.')
    if gesperrt:
        print(f'{len(gesperrt)} Datei(en) brauchen eine redaktionelle Hand.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
