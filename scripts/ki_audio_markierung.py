#!/usr/bin/env python3
# ============================================================
#  KI-AUDIO-MARKIERUNG – maschinenlesbare Herkunft IN der Tonspur (#1028)
#
#  WARUM ES DIESE DATEI GIBT (Befund 13.11.2026)
#  ---------------------------------------------
#  Die Betreiberebene der KI-Kennzeichnung lag am 13.11.2026 auf sieben
#  Kanälen – Dokumentkopf, schema.org, Bildattribut, IPTC-Feld im JPEG,
#  sichtbares Tonspur-Siegel, Feed und Bild-Ableitungen. Beim Nachmessen
#  fiel eine Lücke auf, die keine Regel bisher sehen konnte:
#
#    · `scripts/ff_voice_audio.py` erzeugt je Artikel eine synthetische
#      Tonspur (ElevenLabs/Edge/Piper → MP3 oder WAV). Die Seiten sagen
#      „maschinell erzeugte Stimme" – die DATEI selbst sagt nichts. Wer
#      die MP3 herunterlädt, weiterreicht oder in ein Podcast-Archiv
#      spiegelt, hält ein Stück synthetischer Sprache ohne jede Angabe
#      in der Hand. Genau das ist der Fall, für den der Verhaltenskodex
#      der Kommission vom 10.06.2026 Metadaten verlangt.
#    · Für Bilder gibt es diesen Weg seit dem 05.11.2026
#      (`scripts/ki_bild_markierung.py`, XMP/IPTC im JPEG). Für Ton fehlte
#      das Gegenstück – obwohl derselbe IPTC-Wert gilt und die Tonspur der
#      teuerste, am weitesten verbreitete Inhalt des Blogs ist.
#
#  WAS HIER GESCHRIEBEN WIRD
#  -------------------------
#  MP3: ID3v2.3-Tag mit `TXXX:IPTC:DigitalSourceType` (Vokabular-URI +
#       Wert), `TXXX:AISystemUsed`, `TXXX:Provenance` (Verweis auf den
#       menschenlesbaren Hinweis) und `TXXX:Software`. Der Tag steht VOR
#       dem ersten MPEG-Frame; die Audiodaten werden byteweise nicht
#       angefasst (kein Neukodieren, keine Pegeländerung).
#  WAV: RIFF-`LIST`/`INFO`-Chunk mit `ICMT` (Hinweis) und `ISFT` (Werkzeug).
#       Der `data`-Chunk bleibt unverändert; die Längenfelder werden
#       korrekt nachgezogen.
#
#  RECHTLICHE GRENZE (bitte nicht wegdiskutieren)
#  ----------------------------------------------
#  Art. 50 Abs. 2 KI-VO ist eine Pflicht des ANBIETERS des generativen
#  Systems; für vor dem 02.08.2026 in Verkehr gebrachte Systeme läuft die
#  Nachfrist bis 02.12.2026 (Art. 111 Abs. 4). Ein selbst gesetztes
#  ID3-Feld ist eine ANGABE DES BETREIBERS: nicht signiert, leicht
#  entfernbar, kein Herkunftsbeweis und kein Wasserzeichen. Es ersetzt
#  weder die Anbieter-Markierung noch eine C2PA-Signatur. Es macht die
#  eigene Erklärung dort auffindbar, wo die Datei sie noch trägt – auch
#  nach dem Herunterladen.
#
#  GRUNDSÄTZE
#  ----------
#  · Nichts erfinden: Geschrieben wird nur, was der Sidecar
#    (`<slug>.track.json`) belegt – er entsteht im selben Lauf wie die
#    Datei und nennt Engine, Stimme und Sprache.
#  · Fremdes nicht überschreiben: Trägt eine Datei bereits einen
#    ABWEICHENDEN `DigitalSourceType`, blockiert das Werkzeug (erst
#    prüfen, dann bewusst `--force`). Dieselbe Regel wie beim Bild.
#  · Idempotent: zweiter Lauf ändert keinen Byte.
#  · Wiederherstellbar: `--entfernen` nimmt genau die eigenen Frames
#    wieder heraus und stellt die Datei byteweise her.
#
#  Aufruf
#  ------
#      python3 scripts/ki_audio_markierung.py                     # Bericht
#      python3 scripts/ki_audio_markierung.py --gate              # Exit 1 bei Lücke
#      python3 scripts/ki_audio_markierung.py --write             # markieren
#      python3 scripts/ki_audio_markierung.py --entfernen         # zurücknehmen
#      python3 scripts/ki_audio_markierung.py --json
#      python3 scripts/ki_audio_markierung.py --selftest
#
#  Exit: 0 = alles markiert · 1 = Lücke (--gate/--write) · 2 = Fehler
# ============================================================
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: IPTC-Vokabular für die Erzeugungsart. Dieselbe Liste wie in
#: `scripts/ki_bild_markierung.py` – der Ton ist vollständig synthetisch,
#: also immer `trainedAlgorithmicMedia` (kein „composite": Es gibt keinen
#: aufgenommenen O-Ton, der bearbeitet worden wäre).
VOKABULAR = "http://cv.iptc.org/newscodes/digitalsourcetype/"
ERLAUBTE_TYPEN = ("trainedAlgorithmicMedia",)

#: Namensraum der eigenen Angaben im Seitenkopf und im Feed. Ein Wahrheitsort
#: für den Verweis auf den menschenlesbaren Hinweis.
HINWEIS_URL = "https://franksfinanzcheck.de/impressum/#ki-hinweis"
HINWEIS_TEXT = ("Tonspur maschinell erzeugt (Text-zu-Sprache) – "
                "FranksFinanzcheck, Angabe des Betreibers, kein Herkunftsbeweis")
WERKZEUG = "franksfinanzcheck-blog/ki_audio_markierung"

#: Unsere eigenen Frame-/Feldnamen. Die Liste ist Vertrag: `pruefen()` sucht
#: genau diese, `entfernen()` nimmt genau diese wieder heraus.
FRAME_QUELLE = "IPTC:DigitalSourceType"
FRAME_SYSTEM = "AISystemUsed"
FRAME_PROVENIENZ = "Provenance"
FRAME_WERKZEUG = "Software"
EIGENE_FRAMES = (FRAME_QUELLE, FRAME_SYSTEM, FRAME_PROVENIENZ, FRAME_WERKZEUG)

#: ID3v2.3-Kennung. v2.4 wäre textlich einfacher (UTF-8), wird aber von
#: älteren Playern und Podcast-Werkzeugen schlechter gelesen. v2.3 mit
#: UTF-16 ist der kleinste gemeinsame Nenner.
ID3_KOPF = b"ID3"
ID3_VERSION = (3, 0)
ID3_FLAG_UNSYNC = 0x80
ID3_FLAG_EXTENDED = 0x40

#: Voreinstellung: `public/audio/articles` – dorthin schreibt der Generator.
STANDARD_VERZEICHNIS = "public/audio/articles"

_RE_SLUG = re.compile(r"^[A-Za-z0-9._-]+$")


class WerkzeugFehler(RuntimeError):
    """Die Datei ist nicht lesbar/änderbar – kein Inhaltsbefund."""


# --------------------------------------------------------------------------
#  Syncsafe-Größen (ID3): 4 Byte, je 7 Bit, höchstwertiges Bit immer 0
# --------------------------------------------------------------------------

def _syncsafe(zahl: int) -> bytes:
    if zahl < 0 or zahl >= 1 << 28:
        raise ValueError(f"Größe passt nicht in ein Syncsafe-Feld: {zahl}")
    return bytes(((zahl >> 21) & 0x7F, (zahl >> 14) & 0x7F,
                  (zahl >> 7) & 0x7F, zahl & 0x7F))


def _aus_syncsafe(daten: bytes) -> int:
    if len(daten) != 4 or any(b & 0x80 for b in daten):
        raise ValueError("kein Syncsafe-Feld")
    return (daten[0] << 21) | (daten[1] << 14) | (daten[2] << 7) | daten[3]


# --------------------------------------------------------------------------
#  ID3: schreiben, lesen, entfernen
# --------------------------------------------------------------------------

def _utf16(text: str) -> bytes:
    """ID3v2.3-Text mit BOM (Encoding-Byte wird vom Aufrufer gesetzt)."""
    return b"\xff\xfe" + text.encode("utf-16-le")


def _txxx(beschreibung: str, wert: str, version: int = ID3_VERSION[0]) -> bytes:
    """TXXX-Frame (benutzerdefinierter Text) – Beschreibung + Wert, UTF-16."""
    inhalt = b"\x01" + _utf16(beschreibung) + b"\x00\x00" + _utf16(wert)
    return _rahmen(b"TXXX", inhalt, version)


def _text_frame(frame_id: str, wert: str, version: int = ID3_VERSION[0]) -> bytes:
    inhalt = b"\x01" + _utf16(wert)
    return _rahmen(frame_id.encode("ascii"), inhalt, version)


def eigene_frames(typ: str, *, system: str | None = None,
                  quelle: str | None = None, version: int = ID3_VERSION[0]) -> bytes:
    """Die vier eigenen Frames – Reihenfolge ist stabil (Idempotenz)."""
    return b"".join((
        _txxx(FRAME_QUELLE, VOKABULAR + typ, version),
        _txxx(FRAME_SYSTEM, system or "unbekannt", version),
        _txxx(FRAME_PROVENIENZ, quelle or HINWEIS_URL, version),
        _txxx(FRAME_WERKZEUG, WERKZEUG, version),
    ))


def tag_bauen(frames: bytes, version: tuple[int, int] = ID3_VERSION) -> bytes:
    return (ID3_KOPF + bytes(version) + b"\x00"
            + _syncsafe(len(frames)) + frames)


def _rahmen(kennung: bytes, inhalt: bytes, version: int) -> bytes:
    """Ein Frame mit der GRÖSSENKODIERUNG seiner Tag-Version.

    ID3v2.3 schreibt die Frame-Größe als 32-Bit-Big-Endian, ID3v2.4 als
    Syncsafe. Wer ein v2.4-Tag liest und als v2.3 zurückschreibt, ändert
    nebenbei Kopfzeile und Größenfeld – die Datei ist dann nicht mehr
    bytegleich zum Ausgangsstand (gemessen am 13.11.2026 an einer
    ffmpeg-Datei: Tag v2.4, `--entfernen` stellte sie nicht wieder her).
    """
    groesse = _syncsafe(len(inhalt)) if version >= 4 else len(inhalt).to_bytes(4, "big")
    return kennung + groesse + b"\x00\x00" + inhalt


def id3_bereich(daten: bytes) -> tuple[int, int, int, int] | None:
    """(Start, Ende, Frames-Ende, Version) des ID3v2-Tags, sonst None.

    `Start` ist immer 0 (ein ID3-Tag steht am Dateianfang). `Ende` schließt
    die Kopfzeile ein, `Frames-Ende` ist der Bereich ohne Padding.
    """
    if not daten.startswith(ID3_KOPF) or len(daten) < 10:
        return None
    version = daten[3]
    flags = daten[5]
    try:
        groesse = _aus_syncsafe(daten[6:10])
    except ValueError as exc:
        raise WerkzeugFehler(f"ID3-Kopfgröße nicht lesbar: {exc}") from exc
    if 10 + groesse > len(daten):
        raise WerkzeugFehler("ID3-Tag ragt über das Dateiende hinaus")
    if version not in (3, 4):
        raise WerkzeugFehler(f"ID3v2.{version} wird nicht angefasst "
                             "(nur v2.3/v2.4, sonst Neuschreiben nötig)")
    if flags & ID3_FLAG_UNSYNC:
        raise WerkzeugFehler("ID3-Tag ist unsynchronisiert – "
                             "wird nicht ohne Neukodierung angefasst")
    if flags & ID3_FLAG_EXTENDED:
        raise WerkzeugFehler("ID3-Tag hat einen erweiterten Kopf – "
                             "wird nicht ohne Neukodierung angefasst")
    return 0, 10 + groesse, 10 + groesse, version


def _frames_lesen(daten: bytes, start: int, ende: int,
                  version: int = 3) -> list[tuple[str, bytes]]:
    """(Frame-ID, Rohinhalt) aller Frames – bricht bei Padding ab."""
    frames: list[tuple[str, bytes]] = []
    pos = start
    while pos + 10 <= ende:
        kennung = daten[pos:pos + 4]
        if kennung[:1] == b"\x00":       # Padding beginnt
            break
        try:
            roh = daten[pos + 4:pos + 8]
            groesse = _aus_syncsafe(roh) if version >= 4 else int.from_bytes(roh, "big")
        except ValueError:
            break
        if groesse <= 0 or pos + 10 + groesse > ende:
            break
        try:
            name = kennung.decode("ascii")
        except UnicodeDecodeError:
            break
        frames.append((name, daten[pos + 10:pos + 10 + groesse]))
        pos += 10 + groesse
    return frames


def _utf16_teile(roh: bytes) -> tuple[bytes, bytes] | None:
    """Zwei UTF-16-Strings, getrennt durch ein AUSGERICHTETES Nullpaar.

    Der naive `split(b"\\x00\\x00")` ist hier falsch: Bei UTF-16LE ist jedes
    ASCII-Zeichen `XX 00`, ein Nullpaar entsteht also erst aus dem letzten
    Zeichen (High-Byte 0) PLUS dem Terminator. Ein unausgerichtetes Split
    schneidet dadurch ein Byte zu früh und verschiebt die Byte-Parität –
    aus „IPTC" wird dann CJK-Zeichensalat (gemessen am 13.11.2026 im
    Selbsttest). Deshalb wird in 2-Byte-Schritten gesucht: Ein Nullpaar
    zählt nur an gerader Position.
    """
    for pos in range(0, len(roh) - 1, 2):
        if roh[pos:pos + 2] == b"\x00\x00":
            return roh[:pos], roh[pos + 2:]
    return None


def _txxx_lesen(inhalt: bytes) -> tuple[str, str] | None:
    """(Beschreibung, Wert) eines TXXX-Inhalts – tolerant für v2.3/v2.4."""
    if not inhalt:
        return None
    kodierung = inhalt[0]
    rest = inhalt[1:]
    if kodierung == 0:                        # ISO-8859-1
        teile = rest.split(b"\x00", 1)
        if len(teile) != 2:
            return None
        return teile[0].decode("latin-1", "replace"), teile[1].decode("latin-1", "replace")
    if kodierung in (1, 2):                   # UTF-16 mit/ohne BOM
        teile = _utf16_teile(rest)
        if teile is None:
            return None
        return (teile[0].decode("utf-16", "replace").rstrip("\x00"),
                teile[1].decode("utf-16", "replace").rstrip("\x00"))
    if kodierung == 3:                        # UTF-8 (v2.4)
        teile = rest.split(b"\x00", 1)
        if len(teile) != 2:
            return None
        return teile[0].decode("utf-8", "replace"), teile[1].decode("utf-8", "replace")
    return None


def markierung_lesen(daten: bytes) -> dict:
    """Was sagt die DATEI selbst über ihre Herkunft? (ohne Audio-Decoder)

    Rückgabe nennt zusätzlich den Container, damit ein Bericht nicht
    behauptet, eine WAV sei eine MP3.
    """
    ergebnis = {"format": _format(daten), "markiert": False,
                "digital_source_type": None, "system": None,
                "provenienz": None, "fremd": []}
    if ergebnis["format"] == "mp3":
        bereich = id3_bereich(daten)
        if not bereich:
            return ergebnis
        for name, inhalt in _frames_lesen(daten, 10, bereich[2], bereich[3]):
            if name == "TXXX":
                paar = _txxx_lesen(inhalt)
                if not paar:
                    continue
                beschreibung, wert = paar
                if beschreibung == FRAME_QUELLE:
                    ergebnis["digital_source_type"] = wert
                elif beschreibung == FRAME_SYSTEM:
                    ergebnis["system"] = wert
                elif beschreibung == FRAME_PROVENIENZ:
                    ergebnis["provenienz"] = wert
                elif wert and VOKABULAR in wert:
                    ergebnis["fremd"].append(beschreibung)
    elif ergebnis["format"] == "wav":
        for chunk_id, inhalt, _offset in _riff_chunks(daten):
            if chunk_id != b"LIST":
                continue
            for kennung, wert in _info_eintraege(inhalt):
                if kennung == b"ICMT":
                    ergebnis["provenienz"] = wert
                    if VOKABULAR + "trainedAlgorithmicMedia" in wert:
                        ergebnis["digital_source_type"] = VOKABULAR + "trainedAlgorithmicMedia"
                elif kennung == b"ISBJ":
                    ergebnis["system"] = wert.removeprefix("KI-System: ")
    typ = ergebnis["digital_source_type"] or ""
    ergebnis["markiert"] = any(typ.endswith(t) for t in ERLAUBTE_TYPEN)
    return ergebnis


def _format(daten: bytes) -> str:
    if daten.startswith(ID3_KOPF) or (len(daten) > 1 and daten[0] == 0xFF
                                      and (daten[1] & 0xE0) == 0xE0):
        return "mp3"
    if len(daten) >= 12 and daten[:4] == b"RIFF" and daten[8:12] == b"WAVE":
        return "wav"
    return "unbekannt"


def schreiben(pfad: Path, typ: str, *, system: str | None = None,
              quelle: str | None = None, force: bool = False) -> str:
    """Markierung setzen. Rückgabe: ergaenzt · unveraendert · ersetzt · blockiert."""
    daten = pfad.read_bytes()
    art = _format(daten)
    if art == "mp3":
        return _mp3_schreiben(pfad, daten, typ, system=system, quelle=quelle, force=force)
    if art == "wav":
        return _wav_schreiben(pfad, daten, typ, system=system, force=force)
    raise WerkzeugFehler(f"{pfad.name}: {art} – für dieses Format ist kein "
                         "Markierungsweg hinterlegt (nur MP3 und WAV)")


def _mp3_schreiben(pfad: Path, daten: bytes, typ: str, *, system: str | None,
                   quelle: str | None, force: bool) -> str:
    """Eigene TXXX-Frames einsetzen – fremde Frames bleiben, wo sie standen.

    ZWEI BEFUNDE AUS DEM ECHTEN LAUF (13.11.2026, ffmpeg-Ausgabe):
    · `ffmpeg` legt ein Tag mit `TSSE` („Lavf…") und ein Null-Padding an.
      Wer das Padding wegwirft, verschiebt den ersten MPEG-Frame – die
      Audiodaten sind dann byteweise andere, obwohl kein Sample neu kodiert
      wurde. Der Beweis „unverändert" wäre nicht mehr führbar.
    · Fremde Frames (Encoder, Titel, Künstler) gehören nicht uns. Sie werden
      NICHT umsortiert und NICHT verworfen: unsere vier Frames ersetzen genau
      die vier gleichnamigen und stehen vorn.
    """
    bereich = id3_bereich(daten)
    version = bereich[3] if bereich else ID3_VERSION[0]
    neu_frames = eigene_frames(typ, system=system, quelle=quelle, version=version)
    if not bereich:
        tag = tag_bauen(neu_frames)
        pfad.write_bytes(tag + daten)
        return "ergaenzt"

    vorhanden = _frames_lesen(daten, 10, bereich[2], version)
    fremde_quelle = [wert for name, inhalt in vorhanden if name == "TXXX"
                     for beschreibung, wert in [_txxx_lesen(inhalt)]
                     if beschreibung == FRAME_QUELLE and wert != VOKABULAR + typ]
    behalten = b"".join(_rahmen(kennung.encode("ascii"), inhalt, version)
                        for kennung, inhalt in vorhanden
                        if not (kennung == "TXXX"
                                and (_txxx_lesen(inhalt) or ("", ""))[0] in EIGENE_FRAMES))
    altes_tag = daten[:bereich[1]]
    framebytes = neu_frames + behalten
    # Padding = alles hinter den Frames im alten Tag. Passt der neue Frame-
    # Satz hinein, bleibt der Tag GENAU so groß wie vorher – dann sind die
    # Audiodaten byteweise identisch und die Datei wächst nicht.
    altes_padding = altes_tag[10 + sum(len(i) + 10 for _, i in vorhanden):]
    # Das ORIGINAL-Padding bleibt unangetastet: Es ist Fremdbesitz (ffmpeg
    # legt es an), und nur so kann `--entfernen` die Datei byteweise
    # wiederherstellen. Der Tag wächst um unsere vier Frames – nie um mehr.
    framebytes += altes_padding
    neu = tag_bauen(framebytes, (version, 0)) + daten[bereich[1]:]
    if neu == daten:
        return "unveraendert"
    if fremde_quelle and not force:
        return "blockiert"
    pfad.write_bytes(neu)
    # Ein vorhandenes Tag heißt: eigene Angaben wurden aktualisiert (etwa
    # nach einem Engine-Wechsel). „ergänzt" ist nur der erste eigene Tag.
    return "ergaenzt" if not vorhanden else "ersetzt"


def _riff_chunks(daten: bytes):
    """(Chunk-ID, Inhalt, Offset) ab dem 'WAVE'-Kopf; bricht an kaputten Längen ab."""
    pos = 12
    while pos + 8 <= len(daten):
        kennung = daten[pos:pos + 4]
        laenge = int.from_bytes(daten[pos + 4:pos + 8], "little")
        if pos + 8 + laenge > len(daten):
            break
        yield kennung, daten[pos + 8:pos + 8 + laenge], pos
        pos += 8 + laenge + (laenge & 1)


def _info_eintraege(inhalt: bytes) -> tuple[tuple[bytes, str], ...]:
    """(Kennung, Text) der Einträge eines LIST-INFO-Chunks – leer, wenn fremd.

    Rückgabe ist ein Tupel, kein Generator: Ein `LIST`-Chunk kann auch
    `adtl`/`strl` enthalten (Marker, Regions). Ein Generator, der dort `None`
    liefert, macht aus einer Prüfung einen Absturz – und ein Absturz im
    Prüfpfad ist ein Werkzeugbefund, kein Inhaltsbefund.
    """
    if not inhalt.startswith(b"INFO"):
        return ()
    eintraege: list[tuple[bytes, str]] = []
    pos = 4
    while pos + 8 <= len(inhalt):
        kennung = inhalt[pos:pos + 4]
        laenge = int.from_bytes(inhalt[pos + 4:pos + 8], "little")
        if pos + 8 + laenge > len(inhalt):
            break
        eintraege.append((kennung,
                          inhalt[pos + 8:pos + 8 + laenge].decode("utf-8", "replace").rstrip("\x00")))
        pos += 8 + laenge + (laenge & 1)
    return tuple(eintraege)


EIGENE_WERTE = (b"ICMT", b"ISFT", b"ISBJ", b"IENG")


def _ist_eigen(feld: bytes, wert: str) -> bool:
    """Gehört dieser INFO-Eintrag uns? Entscheidet der WERT, nicht die Kennung.

    Befund 13.11.2026: `ISFT` ist die Standardkennung für „Software". Ein
    pauschales „ISFT ist unseres" hat das `Lavf…` des Encoders gelöscht –
    also fremde Herkunftsangabe überschrieben, genau das, was der Bildpfad
    ausdrücklich verbietet.
    """
    if feld == b"ICMT":
        return wert.startswith(HINWEIS_TEXT)
    if feld == b"ISFT":
        return wert == WERKZEUG
    if feld == b"ISBJ":
        return wert.startswith("KI-System:")
    if feld == b"IENG":
        return wert.startswith("Frank Hartung")
    return False


def _eigenes_info(typ: str, system: str | None) -> bytes:
    """Unser LIST-INFO-Chunk. `ISFT` ist die SOFTWARE, nicht das KI-System –
    welches System die Stimme erzeugt hat, steht in `ICMT`."""
    return _info_bauen([
        (b"ICMT", f"{HINWEIS_TEXT} · {VOKABULAR}{typ}"),
        (b"ISFT", WERKZEUG),
        (b"IENG", "Frank Hartung (Betreiber)"),
        (b"ISBJ", f"KI-System: {system or 'unbekannt'}"),
    ])


def _info_bauen(eintraege: list[tuple[bytes, str]]) -> bytes:
    teile = [b"INFO"]
    for kennung, wert in eintraege:
        roh = wert.encode("utf-8") + b"\x00"
        teile.append(kennung + len(roh).to_bytes(4, "little") + roh
                     + (b"\x00" if len(roh) % 2 else b""))
    return b"".join(teile)


def _wav_schreiben(pfad: Path, daten: bytes, typ: str, *,
                   system: str | None = None, force: bool = False) -> str:
    """Eigenen INFO-Chunk ANHÄNGEN – jeder fremde Chunk bleibt Byte für Byte.

    BEFUNDE 13.11.2026 (echte ffmpeg-WAV):
    · Ein pauschaler Neuaufbau der Chunk-Kette hat die REIHENFOLGE verändert
      (`LIST` von Position 2 hinter `data`) und damit die Datei strukturell
      umgeschrieben – obwohl nur eine Angabe hinzukommen sollte.
    · Ein „ISFT gehört uns" hat das `Lavf…` des Encoders gelöscht.
    Deshalb: nichts umsortieren, nichts neu bauen. Nur ein vorhandener
    EIGENER INFO-Chunk wird entfernt (er wird ohnehin neu angehängt),
    alles andere wird wörtlich übernommen.
    """
    eigene = _eigenes_info(typ, system)
    fremd = False
    hatte_eigenes = False
    koerper = bytearray()
    for kennung, inhalt, _offset in _riff_chunks(daten):
        if kennung == b"LIST" and inhalt.startswith(b"INFO"):
            eintraege = _info_eintraege(inhalt)
            reste = []
            for feld, wert in eintraege:
                if _ist_eigen(feld, wert):
                    hatte_eigenes = True
                    if feld == b"ICMT" and VOKABULAR in wert and not wert.endswith(typ):
                        fremd = True
                    continue
                reste.append((feld, wert))
            if len(reste) == len(eintraege):
                # Kein eigener Eintrag: der Chunk wird WÖRTLICH übernommen.
                koerper += b"LIST" + len(inhalt).to_bytes(4, "little") + inhalt
                if len(inhalt) % 2:
                    koerper += b"\x00"
            elif reste:
                fremdchunk = _info_bauen(reste)
                koerper += b"LIST" + len(fremdchunk).to_bytes(4, "little") + fremdchunk
                if len(fremdchunk) % 2:
                    koerper += b"\x00"
            continue
        koerper += kennung + len(inhalt).to_bytes(4, "little") + inhalt
        if len(inhalt) % 2:
            koerper += b"\x00"
    if fremd and not force:
        return "blockiert"
    koerper += b"LIST" + len(eigene).to_bytes(4, "little") + eigene
    if len(eigene) % 2:
        koerper += b"\x00"
    neu = b"RIFF" + (len(koerper) + 4).to_bytes(4, "little") + b"WAVE" + bytes(koerper)
    if neu == daten:
        return "unveraendert"
    pfad.write_bytes(neu)
    return "ersetzt" if hatte_eigenes else "ergaenzt"


def entfernen(pfad: Path) -> str:
    """Nur die EIGENEN Angaben herausnehmen – byteweise, ohne Neuaufbau.

    Der Unterschied ist wichtig: Wer beim Entfernen die ganze Chunk- oder
    Tag-Kette neu schreibt, verändert die Datei auch dort, wo er nichts zu
    suchen hat (gemessen am 13.11.2026: eine WAV kam nach `--entfernen` nicht
    bytegleich zurück). Hier werden ausschließlich die eigenen Frames bzw.
    der eigene INFO-Chunk ausgeschnitten; alle übrigen Bytes bleiben an
    ihrem Platz.
    """
    daten = pfad.read_bytes()
    art = _format(daten)
    if art == "mp3":
        bereich = id3_bereich(daten)
        if not bereich:
            return "unveraendert"
        version = bereich[3]
        vorhanden = _frames_lesen(daten, 10, bereich[2], version)
        eigene = [k for k, i in vorhanden
                  if k == "TXXX" and (_txxx_lesen(i) or ("", ""))[0] in EIGENE_FRAMES]
        if not eigene:
            return "unveraendert"
        behalten = b"".join(_rahmen(kennung.encode("ascii"), inhalt, version)
                            for kennung, inhalt in vorhanden
                            if not (kennung == "TXXX"
                                    and (_txxx_lesen(inhalt) or ("", ""))[0] in EIGENE_FRAMES))
        if behalten:
            # Fremde Frames bleiben, das Original-Padding bleibt: Nur unsere
            # vier Frames fallen heraus – die Datei ist danach bytegleich zu
            # dem Stand, der vor dem Markieren hier lag.
            altes_tag = daten[:bereich[1]]
            padding = altes_tag[10 + sum(len(i) + 10 for _, i in vorhanden):]
            pfad.write_bytes(tag_bauen(behalten + padding, (version, 0))
                             + daten[bereich[1]:])
        else:
            # Kein fremder Frame: der Tag fällt ganz weg – die Audiodaten
            # beginnen dann wieder an Byte 0, exakt wie vor dem Markieren.
            pfad.write_bytes(daten[bereich[1]:])
        return "entfernt"
    if art == "wav":
        # Byteweise arbeiten: Ein eigener LIST-Chunk (das ist der zuletzt
        # angehängte, weil `_wav_schreiben` nie sortiert) wird ausgeschnitten.
        # Fremde Chunks und fremde INFO-Einträge werden NICHT neu gebaut –
        # sonst ändert sich beim Entfernen mehr als das Entfernte.
        for kennung, inhalt, offset in reversed(list(_riff_chunks(daten))):
            if kennung != b"LIST" or not inhalt.startswith(b"INFO"):
                continue
            if not any(_ist_eigen(f, w) for f, w in _info_eintraege(inhalt)):
                continue
            laenge = 8 + len(inhalt) + (len(inhalt) & 1)
            daten = daten[:offset] + daten[offset + laenge:]
            daten = (daten[:4] + (len(daten) - 8).to_bytes(4, "little") + daten[8:])
        if daten == pfad.read_bytes():
            return "unveraendert"
        pfad.write_bytes(daten)
        return "entfernt"
    return "unveraendert"


# --------------------------------------------------------------------------
#  Bestand: Sidecar → Erwartung, Datei → Ist
# --------------------------------------------------------------------------

def sidecar_von(datei: Path) -> Path:
    return datei.with_suffix(".track.json").with_suffix(".json") \
        if datei.suffix == ".track" else datei.with_suffix(".track.json")


def sidecar_lesen(datei: Path) -> dict:
    """Beleg des Erzeugerlaufs – ohne ihn wird NICHT markiert."""
    pfad = datei.with_name(datei.stem + ".track.json")
    if not pfad.is_file():
        return {}
    try:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return daten if isinstance(daten, dict) else {}


def dateien(verzeichnis: Path) -> list[Path]:
    """Alle ausgelieferten Tonspuren (MP3/WAV) – sortiert, ohne Sidecars."""
    if not verzeichnis.is_dir():
        return []
    return sorted(p for p in verzeichnis.iterdir()
                  if p.is_file() and p.suffix.lower() in (".mp3", ".wav"))


def pruefen(verzeichnis: Path) -> tuple[list[dict], list[str]]:
    """Befund je Tonspur: markiert, mit welchem Typ, mit welchem Beleg."""
    befunde: list[dict] = []
    fehler: list[str] = []
    for datei in dateien(verzeichnis):
        try:
            daten = datei.read_bytes()
        except OSError as exc:
            fehler.append(f"{datei.name}: nicht lesbar ({exc}) – Markierung ungeprüft")
            continue
        stand = markierung_lesen(daten)
        stand["datei"] = datei.name
        beleg = sidecar_lesen(datei)
        stand["engine"] = beleg.get("engine") or ""
        stand["belegt"] = bool(beleg)
        befunde.append(stand)
        if not stand["markiert"]:
            grund = ("keine Markierung im Container" if stand["format"] != "unbekannt"
                     else "Format ohne Markierungsweg")
            fehler.append(f"{datei.name}: {grund} – "
                          "scripts/ki_audio_markierung.py --write")
        if beleg and stand["system"] and beleg.get("engine") \
                and stand["system"] != beleg["engine"]:
            fehler.append(f"{datei.name}: Tag nennt Engine „{stand['system']}“, "
                          f"der Beleg „{beleg.get('engine')}“ – Angabe widersprüchlich")
    return befunde, fehler


def markieren(verzeichnis: Path, *, force: bool = False) -> tuple[list[dict], list[str]]:
    """Jede Tonspur markieren, deren Erzeugerlauf belegt ist."""
    getan: list[dict] = []
    fehler: list[str] = []
    for datei in dateien(verzeichnis):
        beleg = sidecar_lesen(datei)
        if not beleg:
            # Ohne Sidecar ist der Erzeugerlauf nicht belegt. Dann wird nichts
            # behauptet – genau wie beim Bild („ohne belegte Erzeugungsart
            # wird nichts markiert").
            fehler.append(f"{datei.name}: kein Erzeugerbeleg "
                          f"({datei.stem}.track.json fehlt) – nichts geschrieben")
            continue
        engine = str(beleg.get("engine") or "").strip()
        try:
            ergebnis = schreiben(datei, ERLAUBTE_TYPEN[0], system=engine or None, force=force)
        except (OSError, WerkzeugFehler) as exc:
            fehler.append(f"{datei.name}: {exc}")
            continue
        if ergebnis == "blockiert":
            fehler.append(f"{datei.name}: trägt bereits eine abweichende "
                          "DigitalSourceType-Angabe – fremde Herkunft wird nicht "
                          "still überschrieben (Einzelfall prüfen, dann --force)")
            continue
        getan.append({"datei": datei.name, "ergebnis": ergebnis})
    return getan, fehler


# --------------------------------------------------------------------------
#  Selbsttest: echter Rundlauf auf erzeugten Dateien
# --------------------------------------------------------------------------

def _mini_mp3() -> bytes:
    """MP3 ohne ID3-Kopf: Frame-Sync + Füllbytes (kein Dekoder nötig)."""
    return b"\xff\xfb\x90\x00" + b"\x00" * 2048


def _mini_wav() -> bytes:
    """Kurze stille WAV-Datei – über das `wave`-Modul, also echt."""
    import io
    import wave
    puffer = io.BytesIO()
    with wave.open(puffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(b"\x00\x00" * 480)
    return puffer.getvalue()


def selbsttest() -> int:
    import tempfile

    fehler: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        ordner = Path(tmp)

        # --- MP3 -------------------------------------------------------
        mp3 = ordner / "probe.mp3"
        original = _mini_mp3()
        mp3.write_bytes(original)
        stand = markierung_lesen(mp3.read_bytes())
        if stand["markiert"] or stand["format"] != "mp3":
            fehler.append(f"unmarkierte MP3 nicht erkannt: {stand}")

        if schreiben(mp3, ERLAUBTE_TYPEN[0], system="edge") != "ergaenzt":
            fehler.append("erste Markierung nicht ergänzt")
        markiert = mp3.read_bytes()
        if not markiert.endswith(original):
            fehler.append("Audiodaten wurden verändert statt ergänzt")
        stand = markierung_lesen(markiert)
        if not stand["markiert"]:
            fehler.append(f"Markierung nicht lesbar: {stand}")
        if stand["digital_source_type"] != VOKABULAR + "trainedAlgorithmicMedia":
            fehler.append("DigitalSourceType nicht im IPTC-Vokabular")
        if stand["system"] != "edge":
            fehler.append("Engine nicht im Tag")
        if stand["provenienz"] != HINWEIS_URL:
            fehler.append("Verweis auf den Hinweis fehlt")
        if schreiben(mp3, ERLAUBTE_TYPEN[0], system="edge") != "unveraendert":
            fehler.append("Markierung nicht idempotent")
        # Gegenprobe: fremde Angabe wird nicht still überschrieben.
        if schreiben(mp3, ERLAUBTE_TYPEN[0], system="piper") != "ersetzt":
            fehler.append("eigene Angabe wurde nicht aktualisiert")
        fremd = ordner / "fremd.mp3"
        fremd.write_bytes(tag_bauen(_txxx(FRAME_QUELLE,
                                          VOKABULAR + "compositeWithTrainedAlgorithmicMedia"))
                          + original)
        if schreiben(fremd, ERLAUBTE_TYPEN[0]) != "blockiert":
            fehler.append("fremde DigitalSourceType-Angabe wurde ohne --force überschrieben")
        if entfernen(fremd) == "unveraendert":
            fehler.append("fremder Frame wurde als eigener entfernt")
        if entfernen(mp3) != "entfernt":
            fehler.append("Markierung nicht entfernbar")
        if mp3.read_bytes() != original:
            fehler.append("Entfernen stellt den Ausgangszustand nicht her")

        # Unsynchronisiertes Tag: nicht anfassen (kein Neukodieren).
        unsync = ordner / "unsync.mp3"
        unsync.write_bytes(ID3_KOPF + b"\x03\x00" + bytes([ID3_FLAG_UNSYNC])
                           + _syncsafe(0) + original)
        try:
            schreiben(unsync, ERLAUBTE_TYPEN[0])
        except WerkzeugFehler:
            pass
        else:
            fehler.append("unsynchronisiertes Tag wurde geschrieben statt abgelehnt")

        # --- WAV -------------------------------------------------------
        wav = ordner / "probe.wav"
        wav_original = _mini_wav()
        wav.write_bytes(wav_original)
        if schreiben(wav, ERLAUBTE_TYPEN[0]) not in ("ergaenzt", "ersetzt"):
            fehler.append("WAV nicht markiert")
        stand = markierung_lesen(wav.read_bytes())
        if not stand["markiert"]:
            fehler.append(f"WAV-Markierung nicht lesbar: {stand}")
        if b"\x00\x00" * 480 not in wav.read_bytes():
            fehler.append("WAV-Audiodaten wurden verändert")
        if schreiben(wav, ERLAUBTE_TYPEN[0]) != "unveraendert":
            fehler.append("WAV-Markierung nicht idempotent")

        # --- Bestand über Sidecars ------------------------------------
        bestand = ordner / "articles"
        bestand.mkdir()
        (bestand / "artikel.mp3").write_bytes(original)
        (bestand / "artikel.track.json").write_text(
            json.dumps({"engine": "elevenlabs", "src": "/audio/articles/artikel.mp3"}),
            encoding="utf-8")
        (bestand / "ohne-beleg.mp3").write_bytes(original)
        befunde, funde = pruefen(bestand)
        if len(funde) != 2:
            fehler.append(f"Bestand: {len(funde)} statt 2 Lücken gemeldet ({funde})")
        getan, rest = markieren(bestand)
        if len(getan) != 1 or not rest:
            fehler.append("Bestand: belegte Spur nicht markiert oder unbelegte "
                          f"Spur stillschweigend markiert ({getan}, {rest})")
        befunde, funde = pruefen(bestand)
        if len(funde) != 1:
            fehler.append(f"Bestand nach Heilung: {len(funde)} statt 1 Lücke ({funde})")
        markiert = next(b for b in befunde if b["datei"] == "artikel.mp3")
        if not markiert["markiert"] or markiert["system"] != "elevenlabs":
            fehler.append(f"Engine aus dem Beleg nicht übernommen: {markiert}")

    for f in fehler:
        print(f"❌ {f}")
    if fehler:
        return 2
    print("✅ KI-Audio-Markierung: ID3/RIFF-Angabe lesbar, Audiodaten byteweise "
          "unverändert, idempotent, fremde Herkunft geschützt, unbelegte Spur "
          "bleibt unangetastet.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    gruppe = parser.add_mutually_exclusive_group()
    gruppe.add_argument("--gate", action="store_true",
                        help="Exit 1, wenn eine ausgelieferte Tonspur nicht markiert ist")
    gruppe.add_argument("--write", action="store_true", help="Markierung setzen")
    gruppe.add_argument("--entfernen", action="store_true", help="eigene Angaben entfernen")
    gruppe.add_argument("--selftest", action="store_true")
    parser.add_argument("--dir", default=STANDARD_VERZEICHNIS,
                        help=f"Verzeichnis der Tonspuren (Vorgabe: {STANDARD_VERZEICHNIS})")
    parser.add_argument("--force", action="store_true",
                        help="abweichende fremde Herkunftsangabe bewusst ersetzen")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selbsttest()

    verzeichnis = Path(args.dir)
    if not verzeichnis.is_absolute():
        verzeichnis = ROOT / verzeichnis

    try:
        getan: list[dict] = []
        if args.write:
            getan, fehler = markieren(verzeichnis, force=args.force)
            befunde, prueffehler = pruefen(verzeichnis)
            fehler = prueffehler + fehler
        elif args.entfernen:
            getan = [{"datei": p.name, "ergebnis": entfernen(p)} for p in dateien(verzeichnis)]
            befunde, fehler = pruefen(verzeichnis)
        else:
            befunde, fehler = pruefen(verzeichnis)
    except (OSError, WerkzeugFehler) as exc:
        print(f"KI-Audio-Markierung nicht ausführbar: {exc}")
        return 2

    if args.json:
        print(json.dumps({"markiert": getan, "bestand": befunde, "fehler": fehler},
                         ensure_ascii=False, indent=2))
    else:
        anz = len(befunde)
        markiert = sum(1 for b in befunde if b["markiert"])
        print(f"KI-Audio-Markierung: {anz} Tonspur(en) im Verzeichnis "
              f"{verzeichnis.relative_to(ROOT) if str(verzeichnis).startswith(str(ROOT)) else verzeichnis}, "
              f"{markiert} maschinenlesbar markiert, {len(fehler)} Befund(e).")
        for eintrag in getan:
            print(f"::notice title=KI-Tonspur markiert::{eintrag['datei']}: {eintrag['ergebnis']}")
        for f in fehler:
            print(f"::error title=KI-Audio-Markierung::{f}")
        if anz == 0:
            print("Hinweis: in diesem Lauf liegt keine Tonspur vor (Audio ist "
                  "Zusatzfläche, kein Veröffentlichungsgrund). Die Markierung "
                  "greift beim nächsten Vertonungslauf.")
    if args.entfernen:
        return 0 if not fehler else 1
    if (args.gate or args.write) and fehler:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
