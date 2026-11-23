#!/usr/bin/env python3
"""Die Betreiber-Abzeichnung zur KI-Register-Einordnung dauerhaft bewachen.

Hintergrund
-----------
Am 23.11.2026 hat der Betreiber die Einordnung der 12 Altartikel unter
`maschinell` in `data/ki_kennzeichnung.yaml` abgezeichnet
(`ENTSCHEIDUNG-BETREIBER-KI-REGISTER-2026-11-23.md`, Abschnitt 8, Option A).
Bislang war diese Entscheidung nur Prosa — genau wie der Register-Kommentar,
der die Umfuhrung „Artikel unter `maschinell` dürfen NIE auf false gesetzt
werden, auch nicht über `menschlich`" nur schriftlich verbot, ohne sie zu
erzwingen.

Diese Wache macht die Abzeichnung maschinenprüfbar. Sie liest die
maschinenlesbare Fassung `data/betreiber_abzeichnung_ki_register.yaml` und
gleicht sie gegen den Bestand ab. Sie meldet rot, wenn Abzeichnung und
Bestand auseinanderlaufen:

  Z1  Datensatz vorhanden, lesbar, Pflichtfelder vollständig   (Werkzeug → Exit 2)
  Z2  alle 12 unter `maschinell`, keine unter `menschlich`     (Blocker  → Exit 1)
  Z3  Akte-Hash stimmt mit dem Datensatz überein               (Blocker  → Exit 1)
  Z4  KI-VO-Frist 2026-12-02: Ablauf ohne rechtzeitige
      Abzeichnung ist rot, sonst Abstand als Hinweis           (Blocker/Hinweis)
  Z5  Prüfvermerke mit ihrem Text-Hash weiterhin im Ledger     (Blocker  → Exit 1)
  Z6  Hochrisiko-Siegel gültig, nächste Prüfung nicht vorbei   (Blocker/Hinweis)

Grenzen
-------
Die Wache ist fail-closed und SCHREIBT NICHTS (weder Dateien noch Verzeichnisse).
Sie ersetzt weder das Register, noch die Akte, noch `ki_provenienz_gate.py`,
noch die Fassungsdrift-Prüfung der `ymyl_siegel_wache` — sie bindet die
unterzeichnete Entscheidung an den Bestand und meldet Drift. Ein Werkzeugfehler
(Exit 2) hat Vorrang vor einem Inhaltsbefund (Exit 1): Eine ausgefallene
Messung darf nicht wie ein grüner Bestand aussehen.

Der `--selftest` ist ein reiner Logik-Beweis: feste Daten, feste Termine, keine
Uhr, keine Datei, kein Netzwerk. Darum läuft er auch unter der vorgestellten
Uhr des Selftest-Runners (+97/+1461 Tage) und schreibfrei (C15) unverändert.
"""
import argparse
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:  # fail-closed: fehlendes PyYAML ist ein Werkzeugfehler, kein Grün
    yaml = None

DATENSATZ = "data/betreiber_abzeichnung_ki_register.yaml"
REGISTER = "data/ki_kennzeichnung.yaml"
LEDGER = "data/faktenfrische_entscheidungen.yaml"
AKTE_DEFAULT = "ENTSCHEIDUNG-BETREIBER-KI-REGISTER-2026-11-23.md"

BLOCKER = "blocker"
HINWEIS = "hinweis"
WERKZEUG = "werkzeug"


# --------------------------------------------------------------------------
# Reine Regeln: nehmen bereits gelesene Daten + ein festes `heute`, geben
# Befunde als (code, schwere, text) zurück. Keine Uhr, keine Datei — dadurch
# im Selbsttest uhrfest und schreibfrei prüfbar.
# --------------------------------------------------------------------------
def z1_datensatz(ds):
    """Struktur des Datensatzes. Alles Weitere hängt an ihm → Werkzeugfehler."""
    if ds is None:
        return [("Z1", WERKZEUG, "Datensatz %s fehlt oder ist nicht lesbar" % DATENSATZ)]
    f = []
    for key, typ in (("abzeichnung", dict), ("entscheidung", dict),
                     ("artikel", list), ("pruefvermerke", list),
                     ("hochrisiko_siegel", list)):
        if not isinstance(ds.get(key), typ):
            f.append(("Z1", WERKZEUG, "Pflichtfeld '%s' fehlt oder hat den falschen Typ" % key))
    abz = ds.get("abzeichnung") if isinstance(ds.get("abzeichnung"), dict) else {}
    for k in ("datum", "unterzeichnet_von", "akte", "akte_sha256"):
        if not abz.get(k):
            f.append(("Z1", WERKZEUG, "abzeichnung.%s fehlt" % k))
    ent = ds.get("entscheidung") if isinstance(ds.get("entscheidung"), dict) else {}
    if ent.get("option") != "A":
        f.append(("Z1", WERKZEUG, "entscheidung.option ist %r — abgezeichnet war Option A"
                  % ent.get("option")))
    if not ent.get("frist_ki_vo"):
        f.append(("Z1", WERKZEUG, "entscheidung.frist_ki_vo fehlt"))
    art = ds.get("artikel") if isinstance(ds.get("artikel"), list) else []
    if len(art) != 12:
        f.append(("Z1", WERKZEUG, "artikel: %d Einträge, erwartet genau 12" % len(art)))
    elif len(set(art)) != 12:
        f.append(("Z1", WERKZEUG, "artikel: Doppeleintrag"))
    return f


def z2_register(ds, register):
    """Die 12 stehen unter der abgezeichneten Einordnung, nicht in der Gegenliste."""
    if register is None:
        return [("Z2", WERKZEUG, "Register %s nicht lesbar" % REGISTER)]
    reg = (ds.get("entscheidung", {}) or {}).get("register", {}) or {}
    erwartet = reg.get("erwartete_einordnung", "maschinell")
    gegen = reg.get("gegeneinordnung", "menschlich")
    in_erwartet = set(register.get(erwartet) or [])
    in_gegen = set(register.get(gegen) or [])
    f = []
    for slug in ds.get("artikel", []) or []:
        if slug in in_gegen:
            f.append(("Z2", BLOCKER,
                      "'%s' steht unter '%s' — die Abzeichnung (Option A) und die "
                      "Register-Doktrin verbieten das: nie auf false, auch nicht über "
                      "'%s' (Lehre aus 1a8a6d10)" % (slug, gegen, gegen)))
        elif slug not in in_erwartet:
            f.append(("Z2", BLOCKER,
                      "'%s' fehlt unter '%s' — läuft der Abzeichnung davon"
                      % (slug, erwartet)))
    return f


def z3_akte_hash(ds, akte_sha_ist, akte_existiert):
    """Die unterzeichnete Akte ist seit der Abzeichnung unverändert."""
    akte_rel = (ds.get("abzeichnung", {}) or {}).get("akte", AKTE_DEFAULT)
    if not akte_existiert:
        return [("Z3", WERKZEUG, "Akte '%s' nicht gefunden" % akte_rel)]
    soll = (ds.get("abzeichnung", {}) or {}).get("akte_sha256")
    if akte_sha_ist != soll:
        return [("Z3", BLOCKER,
                 "Akte-Hash weicht ab — die unterzeichnete Entscheidung wurde nach der "
                 "Abzeichnung geändert (datiert %s…, aktuell %s…)"
                 % (str(soll)[:12], str(akte_sha_ist)[:12]))]
    return []


def z4_frist(ds, heute):
    """Frist 2026-12-02: rechtzeitige Abzeichnung, Abstand, Ablauf."""
    ent = ds.get("entscheidung", {}) or {}
    abz = ds.get("abzeichnung", {}) or {}
    try:
        frist = date.fromisoformat(str(ent.get("frist_ki_vo")))
    except (TypeError, ValueError):
        return [("Z4", WERKZEUG, "frist_ki_vo ist kein gültiges ISO-Datum: %r"
                 % ent.get("frist_ki_vo"))]
    try:
        abz_datum = date.fromisoformat(str(abz.get("datum")))
    except (TypeError, ValueError):
        return [("Z4", WERKZEUG, "abzeichnung.datum ist kein gültiges ISO-Datum: %r"
                 % abz.get("datum"))]
    f = []
    if abz_datum > frist:
        f.append(("Z4", BLOCKER,
                  "Abzeichnung vom %s liegt NACH der KI-VO-Frist %s"
                  % (abz_datum, frist)))
    if heute > frist:
        if abz_datum <= frist:
            f.append(("Z4", HINWEIS,
                      "KI-VO-Frist %s ist verstrichen; die Abzeichnung lag rechtzeitig "
                      "vor (%s) — Bestand bleibt gekennzeichnet" % (frist, abz_datum)))
        else:
            f.append(("Z4", BLOCKER,
                      "KI-VO-Frist %s verstrichen ohne rechtzeitige Abzeichnung" % frist))
    else:
        f.append(("Z4", HINWEIS,
                  "noch %d Tage bis zur KI-VO-Frist %s; Abzeichnung vom %s liegt vor"
                  % ((frist - heute).days, frist, abz_datum)))
    return f


def _eintrag_slugs(e):
    s = set()
    for k in ("slug", "artikel", "pfad", "datei"):
        v = e.get(k)
        if isinstance(v, str):
            s.add(v.strip("/").split("/")[-1])
    for k in ("slugs", "artikel_liste"):
        if isinstance(e.get(k), list):
            s.update(str(x) for x in e[k])
    return s


def z5_pruefvermerke(ds, ledger):
    """Die Betreiber-Freigaben mit ihrem Text-Hash sind weiterhin im Ledger."""
    if ledger is None:
        return [("Z5", WERKZEUG, "Faktenfrische-Ledger %s nicht lesbar" % LEDGER)]
    f = []
    for pv in ds.get("pruefvermerke", []) or []:
        slug = pv.get("slug")
        h = pv.get("text_sha256")
        anz = pv.get("anzahl_freigaben") or 1
        treffer = [e for e in ledger
                   if isinstance(e, dict)
                   and "Betreiber-Freigabe" in str(e.get("entschieden_von") or "")
                   and str(e.get("geprueft_fassung") or "") == str(h)
                   and any(slug in x or x in slug for x in _eintrag_slugs(e))]
        if len(treffer) < anz:
            f.append(("Z5", BLOCKER,
                      "Prüfvermerk '%s': %d von %d Betreiber-Freigaben mit Text-Hash "
                      "%s… im Ledger — der Beleg ist ganz oder teilweise verschwunden"
                      % (str(slug)[:34], len(treffer), anz, str(h)[:12])))
    return f


def z6_siegel(ds, heute, ist_siegel):
    """Die zwei Hochrisiko-Siegel bleiben gültig; nächste Prüfung nicht vorbei.

    Pro Slug werden die Blocker zuerst gesammelt. Der „Siegel gültig"-Hinweis
    erscheint nur, wenn der Slug keinen Blocker trägt — sonst würde die Ausgabe
    sich selbst widersprechen (Blocker „Status ausstehend" neben Hinweis „gültig").
    """
    f = []
    for soll in ds.get("hochrisiko_siegel", []) or []:
        slug = str(soll.get("slug"))[:34]
        ist = (ist_siegel or {}).get(soll.get("slug"))
        if ist is None:
            f.append(("Z6", BLOCKER,
                      "'%s': kein redaktionelle_pruefung-Siegel mehr im Frontmatter"
                      % slug))
            continue
        blocker = []
        if ist.get("status") != "freigegeben":
            blocker.append("Siegel-Status '%s', erwartet 'freigegeben'"
                           % ist.get("status"))
        if ist.get("inhalt_sha256") != soll.get("inhalt_sha256"):
            blocker.append("inhalt_sha256 weicht ab — das Siegel wurde seit der "
                           "Abzeichnung neu geschnitten")
        if ist.get("pruefer") != soll.get("pruefer"):
            blocker.append("Prüfer '%s' ≠ abgezeichnet '%s'"
                           % (ist.get("pruefer"), soll.get("pruefer")))
        try:
            np = date.fromisoformat(str(ist.get("naechste_pruefung")
                                        or soll.get("naechste_pruefung")))
        except (TypeError, ValueError):
            f.append(("Z6", WERKZEUG,
                      "'%s': naechste_pruefung ist kein gültiges Datum: %r"
                      % (slug, ist.get("naechste_pruefung"))))
            continue
        if heute > np:
            blocker.append("nächste Fachprüfung %s ist verstrichen — Nachprüfung fällig" % np)
        for b in blocker:
            f.append(("Z6", BLOCKER, "'%s': %s" % (slug, b)))
        if not blocker:
            f.append(("Z6", HINWEIS,
                      "'%s': Siegel gültig (freigegeben %s), nächste Fachprüfung %s "
                      "in %d Tagen" % (slug, ist.get("pruefdatum"), np,
                                       (np - heute).days)))
    return f


def pruefe(ds, register, akte_sha_ist, akte_existiert, ledger, ist_siegel, heute):
    """Orchestriert die Regeln. Bei defektem Datensatz nur Z1 (fail-closed)."""
    funde = z1_datensatz(ds)
    if ds is None or any(s == WERKZEUG for _, s, _ in funde):
        return funde
    funde += z2_register(ds, register)
    funde += z3_akte_hash(ds, akte_sha_ist, akte_existiert)
    funde += z4_frist(ds, heute)
    funde += z5_pruefvermerke(ds, ledger)
    funde += z6_siegel(ds, heute, ist_siegel)
    return funde


def exit_code(funde):
    schweren = {s for _, s, _ in funde}
    if WERKZEUG in schweren:
        return 2
    if BLOCKER in schweren:
        return 1
    return 0


# --------------------------------------------------------------------------
# Ein/Ausgabe — nur im Echtlauf (--wache), nie im Selbsttest.
# --------------------------------------------------------------------------
def _lese_yaml(root, rel):
    pfad = root / rel
    if yaml is None:
        return None
    if not pfad.is_file():
        return None
    try:
        return yaml.safe_load(pfad.read_text(encoding="utf-8"))
    except Exception:
        return None


def lese_siegel(root, slug):
    """Frontmatter-Block `redaktionelle_pruefung` eines Artikels, oder None."""
    pfad = root / "content/posts" / slug / "index.md"
    if not pfad.is_file():
        return None
    t = pfad.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"(?ms)^redaktionelle_pruefung:\s*\n(.*?)(?=^\S|\Z)", t)
    if not m:
        return None
    blk = m.group(1)

    def hol(feld):
        mm = re.search(r'(?m)^\s+%s:\s*["\']?([^"\'\n]+)' % feld, blk)
        return mm.group(1).strip() if mm else None

    nm = re.search(r'(?m)^\s+name:\s*["\']?([^"\'\n]+)', blk)
    return {"status": hol("status"),
            "pruefer": (nm.group(1).strip() if nm else None),
            "pruefdatum": hol("pruefdatum"),
            "naechste_pruefung": hol("naechste_pruefung"),
            "inhalt_sha256": hol("inhalt_sha256")}


def laden(root, ds):
    """Liest Register, Akte-Hash, Ledger und die Hochrisiko-Siegel vom Bestand."""
    register = _lese_yaml(root, REGISTER)
    if isinstance(register, dict):
        register = {"maschinell": register.get("maschinell") or [],
                    "menschlich": register.get("menschlich") or []}
    else:
        register = None

    akte_rel = ((ds or {}).get("abzeichnung", {}) or {}).get("akte", AKTE_DEFAULT)
    akte_pfad = root / akte_rel
    akte_existiert = akte_pfad.is_file()
    akte_sha = hashlib.sha256(akte_pfad.read_bytes()).hexdigest() if akte_existiert else None

    led = _lese_yaml(root, LEDGER)
    if isinstance(led, list):
        ledger = led
    elif isinstance(led, dict):
        ledger = next((v for v in led.values() if isinstance(v, list)), [])
    else:
        ledger = None

    ist_siegel = {}
    for soll in ((ds or {}).get("hochrisiko_siegel", []) or []):
        slug = soll.get("slug")
        if slug:
            ist_siegel[slug] = lese_siegel(root, slug)
    return register, akte_sha, akte_existiert, ledger, ist_siegel


ICON = {BLOCKER: "🛑", HINWEIS: "⚠️", WERKZEUG: "🔧"}


def wache(root):
    if yaml is None:
        print("🔧 Z1 PyYAML fehlt — Messung ausgefallen (kein Grün). "
              "Siehe C33/C38: Eine ausgefallene Messung ist kein Bestand.")
        return 2
    ds = _lese_yaml(root, DATENSATZ)
    register, akte_sha, akte_existiert, ledger, ist_siegel = laden(root, ds)
    funde = pruefe(ds, register, akte_sha, akte_existiert, ledger, ist_siegel,
                   date.today())
    for code, schwere, text in funde:
        print("%s %s %s" % (ICON.get(schwere, "•"), code, text))
    n_block = sum(1 for _, s, _ in funde if s == BLOCKER)
    n_werk = sum(1 for _, s, _ in funde if s == WERKZEUG)
    n_hin = sum(1 for _, s, _ in funde if s == HINWEIS)
    code = exit_code(funde)
    zustand = {0: "GRÜN", 1: "ROT (Inhaltsbefund)", 2: "ROT (Werkzeugfehler)"}[code]
    print("ki_abzeichnung_wache: %s — %d Blocker, %d Werkzeug, %d Hinweis(e)"
          % (zustand, n_block, n_werk, n_hin))
    return code


# --------------------------------------------------------------------------
# Selbsttest: reiner Logik-Beweis, feste Daten, feste Termine, keine Uhr,
# keine Datei, kein Netzwerk. Uhrfest und schreibfrei.
# --------------------------------------------------------------------------
def selftest():
    probes = 0

    def ok(bedingung, label):
        nonlocal probes
        probes += 1
        assert bedingung, "Probe fehlgeschlagen: " + label

    slugs = ["artikel-%02d" % i for i in range(12)]
    hash_akte = "a" * 64
    ds_ok = {
        "schema_version": 1,
        "abzeichnung": {"datum": "2026-11-23", "unterzeichnet_von": "Frank Hartung",
                        "akte": AKTE_DEFAULT, "akte_sha256": hash_akte},
        "entscheidung": {"option": "A", "frist_ki_vo": "2026-12-02",
                         "register": {"datei": REGISTER,
                                      "erwartete_einordnung": "maschinell",
                                      "gegeneinordnung": "menschlich"}},
        "artikel": list(slugs),
        "pruefvermerke": [{"slug": slugs[0], "text_sha256": "h" * 64,
                           "anzahl_freigaben": 2,
                           "entschieden_von":
                               "Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)"}],
        "hochrisiko_siegel": [{"slug": slugs[1], "status": "freigegeben",
                               "pruefer": "Redaktion", "pruefdatum": "2026-11-21",
                               "naechste_pruefung": "2027-01-05",
                               "inhalt_sha256": "i" * 64}],
    }

    # Z1 — Struktur
    ok(z1_datensatz(ds_ok) == [], "Z1 gültiger Datensatz ist befundfrei")
    ok(any(s == WERKZEUG for _, s, _ in z1_datensatz(None)), "Z1 fehlender Datensatz → Werkzeug")
    ok(any(s == WERKZEUG for _, s, _ in z1_datensatz({"abzeichnung": {}})),
       "Z1 unvollständiger Datensatz → Werkzeug")
    ds_11 = dict(ds_ok, artikel=slugs[:11])
    ok(any(s == WERKZEUG for _, s, _ in z1_datensatz(ds_11)), "Z1 nur 11 Artikel → Werkzeug")
    ds_optb = dict(ds_ok, entscheidung=dict(ds_ok["entscheidung"], option="B"))
    ok(any(s == WERKZEUG for _, s, _ in z1_datensatz(ds_optb)), "Z1 option B → Werkzeug")

    # Z2 — Register-Einordnung (beide Richtungen)
    reg_ok = {"maschinell": list(slugs), "menschlich": []}
    ok(z2_register(ds_ok, reg_ok) == [], "Z2 alle 12 unter maschinell → befundfrei")
    reg_einer_menschlich = {"maschinell": slugs[1:], "menschlich": [slugs[0]]}
    f = z2_register(ds_ok, reg_einer_menschlich)
    ok(any(c == "Z2" and s == BLOCKER and "menschlich" in t for c, s, t in f),
       "Z2 ein Slug unter menschlich → Blocker")
    reg_leer = {"maschinell": [], "menschlich": []}
    ok(len([1 for c, s, _ in z2_register(ds_ok, reg_leer) if c == "Z2"]) == 12,
       "Z2 leeres Register → 12 Blocker")
    ok(any(s == WERKZEUG for _, s, _ in z2_register(ds_ok, None)),
       "Z2 Register unlesbar → Werkzeug")

    # Z3 — Akte-Hash
    ok(z3_akte_hash(ds_ok, hash_akte, True) == [], "Z3 Hash stimmt → befundfrei")
    ok(any(c == "Z3" and s == BLOCKER for c, s, _ in z3_akte_hash(ds_ok, "0" * 64, True)),
       "Z3 Hash weicht ab → Blocker")
    ok(any(c == "Z3" and s == WERKZEUG for c, s, _ in z3_akte_hash(ds_ok, None, False)),
       "Z3 Akte fehlt → Werkzeug")

    # Z4 — Frist (vorher/nachher, rechtzeitig/verspätet)
    f = z4_frist(ds_ok, date(2026, 11, 23))
    ok(any(c == "Z4" and s == HINWEIS for c, s, _ in f)
       and not any(s == BLOCKER for _, s, _ in f),
       "Z4 vor der Frist, rechtzeitig abgezeichnet → Hinweis, kein Blocker")
    f = z4_frist(ds_ok, date(2026, 12, 3))
    ok(any(c == "Z4" and s == HINWEIS for c, s, _ in f)
       and not any(s == BLOCKER for _, s, _ in f),
       "Z4 nach der Frist, Abzeichnung lag vor → Hinweis, kein Blocker")
    ds_late = dict(ds_ok, abzeichnung=dict(ds_ok["abzeichnung"], datum="2026-12-05"))
    ok(any(c == "Z4" and s == BLOCKER for c, s, _ in z4_frist(ds_late, date(2026, 12, 3))),
       "Z4 Abzeichnung nach der Frist → Blocker")
    ok(any(s == WERKZEUG for _, s, _ in
           z4_frist(dict(ds_ok, entscheidung=dict(ds_ok["entscheidung"],
                                                  frist_ki_vo="ungültig")),
                    date(2026, 11, 23))),
       "Z4 ungültige Frist → Werkzeug")

    # Z5 — Prüfvermerke im Ledger
    ledger_ok = [{"entschieden_von":
                  "Frank Hartung (Betreiber-Freigabe über Arena-Session, 23.11.2026)",
                  "geprueft_fassung": "h" * 64, "slug": slugs[0]} for _ in range(2)]
    ok(z5_pruefvermerke(ds_ok, ledger_ok) == [], "Z5 beide Freigaben mit Hash → befundfrei")
    ok(any(c == "Z5" and s == BLOCKER for c, s, _ in z5_pruefvermerke(ds_ok, ledger_ok[:1])),
       "Z5 nur eine von zwei Freigaben → Blocker")
    ok(any(c == "Z5" and s == BLOCKER for c, s, _ in z5_pruefvermerke(ds_ok, [])),
       "Z5 leerer Ledger → Blocker")
    ledger_falscher_hash = [dict(e, geprueft_fassung="x" * 64) for e in ledger_ok]
    ok(any(c == "Z5" and s == BLOCKER for c, s, _ in
           z5_pruefvermerke(ds_ok, ledger_falscher_hash)),
       "Z5 Freigaben mit falschem Hash → Blocker")
    ok(any(s == WERKZEUG for _, s, _ in z5_pruefvermerke(ds_ok, None)),
       "Z5 Ledger unlesbar → Werkzeug")

    # Z6 — Hochrisiko-Siegel (gültig / abgelaufen / Drift / weg / Status)
    ist_ok = {slugs[1]: {"status": "freigegeben", "pruefer": "Redaktion",
                         "pruefdatum": "2026-11-21", "naechste_pruefung": "2027-01-05",
                         "inhalt_sha256": "i" * 64}}
    f = z6_siegel(ds_ok, date(2026, 11, 23), ist_ok)
    ok(any(c == "Z6" and s == HINWEIS for c, s, _ in f)
       and not any(s == BLOCKER for _, s, _ in f),
       "Z6 gültiges Siegel → Hinweis, kein Blocker")
    ist_alt = {slugs[1]: dict(ist_ok[slugs[1]], naechste_pruefung="2026-01-01")}
    ok(any(c == "Z6" and s == BLOCKER for c, s, _ in z6_siegel(ds_ok, date(2026, 11, 23), ist_alt)),
       "Z6 nächste Prüfung verstrichen → Blocker")
    ist_drift = {slugs[1]: dict(ist_ok[slugs[1]], inhalt_sha256="x" * 64)}
    ok(any(c == "Z6" and s == BLOCKER for c, s, _ in z6_siegel(ds_ok, date(2026, 11, 23), ist_drift)),
       "Z6 inhalt_sha256 gedriftet → Blocker")
    ist_status = {slugs[1]: dict(ist_ok[slugs[1]], status="ausstehend")}
    ok(any(c == "Z6" and s == BLOCKER for c, s, _ in z6_siegel(ds_ok, date(2026, 11, 23), ist_status)),
       "Z6 Status nicht freigegeben → Blocker")
    ist_pruefer = {slugs[1]: dict(ist_ok[slugs[1]], pruefer="Jemand Anders")}
    ok(any(c == "Z6" and s == BLOCKER for c, s, _ in z6_siegel(ds_ok, date(2026, 11, 23), ist_pruefer)),
       "Z6 Prüfer geändert → Blocker")
    ok(any(c == "Z6" and s == BLOCKER for c, s, _ in z6_siegel(ds_ok, date(2026, 11, 23), {})),
       "Z6 Siegel ganz verschwunden → Blocker")

    # Exit-Vorrang: Werkzeug (2) > Blocker (1) > Hinweis/grün (0)
    ok(exit_code([]) == 0, "exit_code: keine Befunde → 0")
    ok(exit_code([("Z4", HINWEIS, "x")]) == 0, "exit_code: nur Hinweis → 0")
    ok(exit_code([("Z2", BLOCKER, "x")]) == 1, "exit_code: Blocker → 1")
    ok(exit_code([("Z1", WERKZEUG, "x"), ("Z2", BLOCKER, "y")]) == 2,
       "exit_code: Werkzeug hat Vorrang vor Blocker → 2")

    # Orchestrierung: gültiger Bestand → grün; defekter Datensatz → nur Z1, fail-closed
    gesamt = pruefe(ds_ok, reg_ok, hash_akte, True, ledger_ok, ist_ok, date(2026, 11, 23))
    ok(exit_code(gesamt) == 0, "pruefe: gültiger Bestand → Exit 0")
    ok(exit_code(pruefe(None, None, None, False, None, {}, date(2026, 11, 23))) == 2,
       "pruefe: Datensatz fehlt → Exit 2, fail-closed")

    print("ki_abzeichnung_wache --selftest: %d Proben, alle grün" % probes)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Betreiber-Abzeichnung zur KI-Register-Einordnung bewachen.")
    ap.add_argument("--wache", action="store_true",
                    help="Echtlauf: Datensatz gegen Register, Akte, Ledger und "
                         "Frontmatter prüfen (Exit 0/1/2).")
    ap.add_argument("--selftest", action="store_true",
                    help="Reiner Logik-Beweis ohne Uhr, Datei und Netzwerk.")
    ap.add_argument("--root", default=None,
                    help="Repository-Wurzel (Vorgabe: aus dem Skriptort abgeleitet).")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    if args.wache:
        return wache(root)

    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
