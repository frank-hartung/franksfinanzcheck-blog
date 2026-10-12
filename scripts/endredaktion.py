#!/usr/bin/env python3
# ============================================================
#  ENDREDAKTION – Prüfstand, Politur & Freigabe-Zentrale
#  ------------------------------------------------------------
#  Das fehlende Stück zwischen den Schreibern (Content-Engine,
#  KI-Redaktion, Poppy-Werkbank) und dem Live-Blog:
#
#    1) PRÜFEN      – eine Gate-Suite für ALLE wartenden Entwürfe
#                     (Länge, Struktur, Titel, Lesbarkeit, Grammatik,
#                     KI-Floskeln, URL-Hygiene, Offenlegung, Duplikate,
#                     TODO-Marker). Wiederverwendet die etablierten
#                     Wachen als Bibliothek (Single Source of Truth):
#                     length_policy, check_titles, readability_check,
#                     grammar_check, fix_url_hygiene, PROFI_FLOSKELN.
#    2) OPTIMIEREN  – deterministische Fixes zuerst (URLs, Titel,
#                     Offenlegung, Description), dann EINE KI-Politur
#                     (Gratis-Kette Groq → Gemini) mit hartem
#                     Sicherheitsvertrag: Links bleiben, Überschriften
#                     stabil, Länge ≥ 85 %, keine neuen Fakten.
#    3) FREIGEBEN   – vollautomatisch über den EINZIGEN bestehenden
#                     Weg: park_state.rearm() → cadence_guard hebt den
#                     Entwurf am nächsten Publikationstag (Mo/Mi/Fr,
#                     2–3 Artikel/Tag) ins Live-Blog. Es entsteht KEIN
#                     zweiter Veröffentlicher – die Endredaktion reiht
#                     nur ein, exakt wie ki_redaktion.py --promote.
#                     Dazu: Mastodon-Posting für freigegebene Poppy-
#                     Karten (nur wenn der Artikel wirklich live ist).
#
#  KOSTEN-REGEL (Dauervorgabe): nur Gratis-Zugänge (GROQ_API_KEY /
#  GEMINI_API_KEY via llm_client). Ohne Keys: prüfen + deterministische
#  Fixes laufen weiter, die Politur wird übersprungen – die Pipeline
#  bricht nie.
#
#  Newsletter: läuft bereits vollautomatisch (newsletter-daily:
#  digest → QA → Versand Di/Fr). Die Endredaktion meldet nur, wie
#  viel neuer Live-Content dort einfließt.
#
#  Nutzung:
#    python3 scripts/endredaktion.py                # komplett: prüfen+optimieren+freigeben
#    python3 scripts/endredaktion.py --nur-pruefen  # Bericht, keine Änderung
#    python3 scripts/endredaktion.py --slug <slug>  # nur einen Entwurf
#    python3 scripts/endredaktion.py --status       # Kurzübersicht
#    python3 scripts/endredaktion.py --selftest     # fail-closed (Exit 2)
#
#  Kill-Switch: data/endredaktion.yaml → modus: manuell
#  (dann wird NIE automatisch freigegeben, nur berichtet).
# ============================================================
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import yaml  # noqa: E402

import llm_client  # noqa: E402
import park_state  # noqa: E402
import post_utils  # noqa: E402

import check_titles  # noqa: E402
import grammar_check  # noqa: E402
import lesbarkeit_heiler  # noqa: E402  (Stufe A + Tor T1–T4, WACHE-609)
import length_policy  # noqa: E402
import readability_check  # noqa: E402

from generate_drafts import PROFI_FLOSKELN  # noqa: E402  (KI-Floskel-SSOT)
from plagiat_guard import hamming, normalize, simhash  # noqa: E402 (SSOT)

import ki_shared as ks  # noqa: E402

CONFIG_FILE = os.path.join(BLOG_DIR, "data", "endredaktion.yaml")
REPORT_FILE = os.path.join(BLOG_DIR, "ENDREDAKTION-REPORT.md")
SPAM_STATUS_FILE = os.path.join(BLOG_DIR, "data", "spam_schutz_status.json")

# Die Lesbarkeits-Schwelle ist IMPORTIERT (SSOT: readability_check R6) – keine
# zweite Zahl im Haus. Genau daran scheiterte die Nachsorge bis zum 12.10.2026:
# Der Lektor bekam die Fundliste, aber niemand maß nach der Politur, ob das
# harte Publish-Kriterium (Flesch ≥ 60) nun erreicht war. Ergebnis: Entwürfe
# pendelten Lauf für Lauf zwischen „optimiert“ und „optimiert“, die
# Lesbarkeits-Wache meldete dieselben Namen erneut (Issue #712) – dieselbe
# Bauart wie die Reserve-Deckung aus #609: **eine Heilung ohne Wirkungsnachweis
# ist Papier** (Governance-Regel C25).
LESBARKEITS_SCHWELLE = readability_check.NEW_FLESCH_MIN

ROLLE = "endredaktion"

DEFAULT_CONFIG = {
    # automatisch = grüne Entwürfe werden vollautomatisch in die
    # Re-Queue gelegt (cadence_guard veröffentlicht Mo/Mi/Fr).
    # manuell    = Kill-Switch: nur Bericht, NIE eine Freigabe.
    "modus": "automatisch",
    "max_freigaben_pro_lauf": 1,
    "max_politur_versuche": 2,
    "min_behalte_laenge_prozent": 85,
    "kanal_blog": True,
    "kanal_mastodon": True,
    "mastodon_max_pro_lauf": 1,
    # Spam-Schutz (Premium): rollendes Wochenbudget für Auto-Freigaben …
    "auto_freigaben_max_pro_woche": 3,
    # … Near-Duplicate-Grenzen (SimHash-Hamming, SSOT plagiat_guard)
    "near_dup_hamming_rot": 10,
    "near_dup_hamming_gelb": 14,
    # … und der Handshake mit der Spam-Schutz-Wache: Ohne gültig grünes/
    # gelbes Statusfile gibt es KEINE Auto-Freigabe (fail-closed).
    "spam_status_erforderlich": True,
}

LEKTOR_SYSTEM = """Du bist der Lektor der Redaktion von FranksFinanzcheck \
(Verlagsniveau: Capital/WiWo/Zeit). Du überarbeitest einen fertigen \
Artikel-ENTWURF anhand einer konkreten Fundliste – behutsam, ohne neue \
Fakten zu erfinden.

HARTE REGELN:
1. Gib NUR den überarbeiteten Artikel-Body als Markdown zurück – ohne \
Frontmatter, ohne Titel-Zeile (# …), ohne Codezaun, ohne Vorrede.
2. Jeder Markdown-Link [text](url) bleibt exakt erhalten – auch \
Affiliate-Links. Füge keine Links hinzu, lösche keinen.
3. Die Anzahl der ## -Überschriften bleibt gleich; Überschriftentexte nur \
bei echten Fehlern anfassen. Überschriften enden nie mit Punkt.
4. Deutsche Satzschreibung (kein Title-Case), Aktiv statt Passiv, im Schnitt \
11–14 Wörter pro Satz, höchstens ein Nebensatz, kein Nominalstil, keine \
Kanzleiwörter („obligatorisch“, „im Rahmen von“), höchstens vier Sätze pro \
Absatz, Ziel Flesch-Amstad ≥ 60.
4a. DER STÄRKSTE HEBEL IST DIE SILBE, nicht die Satzlänge: Flesch-Amstad =
180 − Ø Satzlänge − 58,5 · Silben je Wort. Lange Komposita und \
Substantivierungen durch kurze Alltagswörter ersetzen \
(„Stromanbieterwechsel“ → „Wechsel“, „Vertragslaufzeit“ → „Laufzeit“, \
„Beitragsanpassung“ → „Anpassung“, „Haushaltsgeräte“ → „Geräte“, \
„Verbrauchsmuster“ → „Verbrauch“), Nominalstil in Verben auflösen \
(„die Übernahme der Kosten“ → „die Kasse zahlt die Kosten“). Jede Fassung \
wird gemessen: Bleibt sie unter der Schwelle, wird sie verworfen.
5. KEINE KI-Floskeln („In der heutigen schnelllebigen Welt“, „Zusammenfassend \
lässt sich sagen“, „Heutzutage“ …).
6. ERFINDE NICHTS: keine neuen Zahlen, Studien, Institute, Anbieter oder \
Daten. Zahlen nur aus dem Original übernehmen. Beim Ausformulieren darfst \
du vorhandene Stichpunkte ausschreiben und allgemeingültige Faustregeln \
(eindeutig als Faustregel gekennzeichnet) nennen – sonst nichts.
7. Wenn der Text unter der Mindestlänge liegt: forme vorhandene Inhalte aus \
(Beispiele sauber als Rechenbeispiel kennzeichnen, FAQ-Antworten runder \
machen) statt Neues zu erfinden."""

TODO_MARKER = re.compile(r"TODO\((KI-REDAKTION|POPPY)")
LINK_RX = re.compile(r"\[[^\]]*\]\([^)]+\)")
H2_RX = re.compile(r"^##\s", re.M)


# ---------------------------------------------------------------- Konfiguration
def lade_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, encoding="utf-8") as fh:
                geladen = yaml.safe_load(fh) or {}
            cfg.update({k: v for k, v in geladen.items() if k in DEFAULT_CONFIG})
    except Exception as e:  # noqa: BLE001 – Konfig darf nie crashen
        print(f"  ⚠ endredaktion.yaml nicht lesbar ({e}) – Defaults aktiv.")
    if cfg["modus"] not in ("automatisch", "manuell"):
        cfg["modus"] = "manuell"  # fail-closed
    return cfg


def now_utc_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def heute_iso() -> str:
    return datetime.date.today().isoformat()


# ---------------------------------------------------------------- Artikel laden
def artikel_laden(path: str) -> dict | None:
    """Post-Datei → {path, slug, fm, body, titel, description, ai_generated,
    draft, cadence_wait, endredaktion_status}."""
    try:
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return None
    prefix, fm, body = post_utils.split_article(text)

    def feld(key, default=""):
        m = re.search(rf'(?m)^{key}:\s*(.+)$', fm)
        return m.group(1).strip().strip('"').strip("'") if m else default

    return {
        "path": path,
        "slug": post_utils.slug_of(path),
        "prefix": prefix,
        "fm": fm,
        "body": body,
        "titel": feld("title"),
        "description": feld("description"),
        "ai_generated": re.search(r"(?m)^ai_generated:\s*true", fm) is not None,
        "draft": re.search(r"(?m)^draft:\s*true", fm) is not None,
        "cadence_wait": re.search(r"(?m)^cadence_wait:\s*true", fm) is not None,
        "endredaktion_status": feld("endredaktion_status"),
    }


def artikel_speichern(artikel: dict) -> None:
    with open(artikel["path"], "w", encoding="utf-8") as fh:
        fh.write(post_utils.join_article(artikel["fm"], artikel["body"],
                                         artikel.get("prefix", "")))


def wartende_entwuerfe() -> list[dict]:
    """Alle Posts mit draft: true (älteste zuerst – Fairness der Queue)."""
    entwuerfe = []
    for path in post_utils.list_post_paths():
        artikel = artikel_laden(path)
        if artikel and artikel["draft"]:
            entwuerfe.append(artikel)
    entwuerfe.sort(key=lambda a: a["slug"])
    return entwuerfe


# ---------------------------------------------------------------- Fund-Modell
def fund(code: str, schwere: str, text: str, fixbar: bool = False) -> dict:
    """schwere: 'rot' (blockiert) | 'gelb' (blockiert bis behoben) |
    'hinweis' (Bericht + Politur-Auftrag, blockiert nie).

    Hinweis-Stufe (z. B. Grammatik-Restfunde): Die Rechtschreib-Wache
    prüft Live-Artikel täglich selbst – hier würde ein harter Block nur
    die Freigabe lahmlegen, ohne die Qualität messbar zu erhöhen."""
    return {"code": code, "schwere": schwere, "text": text, "fixbar": fixbar}


def _fm_set(fm: str, key: str, wert: str) -> str:
    """Frontmatter-Feld ersetzen ODER (falls absent) nach dem Titel einfügen."""
    zeile = f"{key}: {json.dumps(wert, ensure_ascii=False)}"
    if re.search(rf"(?m)^{key}:", fm):
        return re.sub(rf"(?m)^{key}:.*$", zeile, fm)
    if re.search(r"(?m)^title:", fm):
        return re.sub(r"(?m)^(title:.*)$", r"\1\n" + zeile, fm, count=1)
    return fm + "\n" + zeile


# ---------------------------------------------------------------- Gate-Suite
def pruefe_artikel(artikel: dict, cfg: dict | None = None) -> list[dict]:
    """Die gesamte Gate-Suite für EINEN Entwurf. Funde sortiert nach Schwere."""
    cfg = cfg or lade_config()
    funde: list[dict] = []
    body, titel = artikel["body"], artikel["titel"]

    # E1 – TODO-Marker: Offline-Gerüste gehen nie live (Promote-Wache-Parität)
    if TODO_MARKER.search(body):
        funde.append(fund("E1", "rot",
                          "Offline-Gerüst mit TODO-Markern – erst fertigstellen"))

    # E2 – Länge (Floor der length_policy, gleiche Wahrheit wie --promote)
    woerter, zeichen = length_policy.measure(body)
    floor = length_policy.POSTS["target_min_chars"]
    if zeichen < floor:
        funde.append(fund("E2", "gelb",
                          f"Fließtext {zeichen:,} Zeichen – unter Floor "
                          f"{floor:,} (Politur kann ausformulieren)",
                          fixbar=True))

    # E3 – Struktur (Engine-Ebene-2-Maßstab: ≥ 3 H2)
    h2 = len(H2_RX.findall(body))
    if h2 < 3:
        funde.append(fund("E3", "rot",
                          f"nur {h2} H2-Abschnitte (Minimum: 3) – Struktur "
                          "muss handschriftlich ergänzt werden"))

    # E4 – KI-Floskeln (SSOT generate_drafts.PROFI_FLOSKELN)
    text_norm = re.sub(r"\s+", " ", body).lower()
    floskeln = [f for f in PROFI_FLOSKELN if f in text_norm]
    if floskeln:
        funde.append(fund("E4", "gelb",
                          "KI-Floskeln: " + ", ".join(floskeln[:2]),
                          fixbar=True))

    # E5 – Titel (check_titles-SSOT; R0 leer = rot, Rest fixbar)
    titel_funde = check_titles.check_title(titel)
    for regel, meldung in titel_funde:
        funde.append(fund("E5", "rot" if regel == "R0" else "gelb",
                          f"Titel {regel}: {meldung}", fixbar=regel != "R0"))

    # E6 – Lesbarkeit (readability_check-SSOT)
    try:
        les = readability_check.analyze(
            readability_check.load_article(artikel["path"]))
        flesch = les.get("flesch", 0)
        if flesch < 45:
            funde.append(fund("E6", "rot",
                              f"Flesch-Amstad {flesch:.0f} – deutlich zu "
                              "verschachtelt"))
        elif flesch < 60:
            funde.append(fund("E6", "gelb",
                              f"Flesch-Amstad {flesch:.0f} < 60 (Ziel der "
                              "Lesbarkeits-Wache)", fixbar=True))
    except Exception as e:  # noqa: BLE001 – ohne Mess KEIN grünes Urteil
        funde.append(fund("E6", "gelb",
                          f"Lesbarkeits-Prüfung nicht möglich ({e}) – "
                          "keine Freigabe ohne Messung"))

    # E7 – Grammatik/Zeichensetzung (grammar_check-SSOT, offline).
    # Hinweis-Stufe: fließt in den Politur-Auftrag, blockiert aber nicht
    # (die Rechtschreib-Wache prüft Live-Artikel täglich selbst).
    try:
        whitelist = grammar_check.load_whitelist()
        g_funde = grammar_check.analyze(
            {"body": body, "description": artikel["description"],
             "title": titel}, whitelist)
        if g_funde:
            funde.append(fund("E7", "hinweis",
                              f"{len(g_funde)} Grammatik-/Tippfund(e), z. B. "
                              f"„{g_funde[0].get('found', '?')}“",
                              fixbar=True))
    except Exception as e:  # noqa: BLE001 – Prüfung darf nie crashen
        funde.append(fund("E7", "hinweis",
                          f"Grammatik-Prüfung nicht möglich ({e})"))

    # E8 – URL-Hygiene (R8: Leerzeichen in URLs)
    if re.search(r"\]\([^)]*[ \t][^)]*\)", body):
        funde.append(fund("E8", "gelb",
                          "Markdown-Link(s) mit Leerzeichen in der URL",
                          fixbar=True))

    # E9 – Offenlegung: KI-Artikel brauchen CTA + Werbe-Kennzeichnung
    hat_offenlegung = ("Transparenz:" in body
                       or "Affiliate-Links (Werbung)" in body)
    hat_cta = ("check24" in body.lower() or "/go/" in body.lower())
    if artikel["ai_generated"] and not (hat_offenlegung and hat_cta):
        funde.append(fund("E9", "gelb",
                          "KI-Entwurf ohne vollständige Werbe-Offenlegung "
                          "(Transparenz-Block/CTA)", fixbar=True))

    # E10 – Duplikat-Titel gegen den Rest des Blogs. Bei zwei ENTWÜRFEN
    # mit gleichem Titel blockiert nur der NEUERE (der ältere hat Vorrang
    # in der Queue); gegen LIVE-Artikel blockiert immer.
    titel_norm = titel.strip().lower()
    for path in post_utils.list_post_paths():
        if path == artikel["path"]:
            continue
        try:
            with open(path, encoding="utf-8") as fh:
                kopf = fh.read(2500)
        except OSError:
            continue
        m = re.search(r'(?m)^title:\s*"?([^"\n]+)"?', kopf)
        if not (m and m.group(1).strip().lower() == titel_norm):
            continue
        anderer_lebt = not re.search(r"(?m)^draft:\s*true", kopf)
        anderer_slug = post_utils.slug_of(path)
        if anderer_lebt or anderer_slug < artikel["slug"]:
            funde.append(fund("E10", "rot",
                              f"Duplikat-Titel: schon in {anderer_slug}"))
            break

    # E11 – Description (120–158 Zeichen, Meta-Optimum)
    d_len = len(artikel["description"])
    if d_len < 100 or d_len > 158:
        funde.append(fund("E11", "gelb",
                          f"Description {d_len} Zeichen (Optimum 120–158)",
                          fixbar=True))

    # E12 – Near-Duplicate gegen den LIVE-Bestand (Spam-Schutz).
    # SimHash/Hamming aus plagiat_guard (SSOT): Ein Entwurf, der einem
    # Live-Artikel zu ähnlich ist, erzeugt Duplicate Content und
    # Keyword-Kannibalisierung – genau das, was Google als
    # „Scaled Content Abuse“ wertet. Er wird NIE automatisch freigegeben.
    try:
        eigener = simhash(normalize(body))
        for path in post_utils.list_post_paths():
            if path == artikel["path"]:
                continue
            try:
                with open(path, encoding="utf-8") as fh:
                    kopf = fh.read(2500)
            except OSError:
                continue
            if re.search(r"(?m)^draft:\s*true", kopf):
                continue  # nur LIVE-Artikel sind Referenz
            with open(path, encoding="utf-8") as fh:
                teile = fh.read().split("---", 2)
            if len(teile) < 3:
                continue
            abstand = hamming(eigener, simhash(normalize(teile[2])))
            if abstand <= int(cfg["near_dup_hamming_rot"]):
                funde.append(fund("E12", "rot",
                                  f"Near-Duplicate (SimHash-Abstand {abstand}) "
                                  f"zu LIVE-Artikel {post_utils.slug_of(path)} "
                                  "– eigenständigen Artikel schreiben"))
                break
            if abstand <= int(cfg["near_dup_hamming_gelb"]):
                funde.append(fund("E12", "gelb",
                                  f"Ähnlichkeit (SimHash-Abstand {abstand}) zu "
                                  f"{post_utils.slug_of(path)} – Politur muss "
                                  "eigenständige Formulierungen finden",
                                  fixbar=True))
    except Exception as e:  # noqa: BLE001 – ohne Mess KEIN grünes Urteil
        funde.append(fund("E12", "gelb",
                          f"Near-Dup-Prüfung nicht möglich ({e}) – "
                          "keine Freigabe ohne Messung"))

    funde.sort(key=lambda f: 0 if f["schwere"] == "rot" else 1)
    return funde


def urteil(funde: list[dict]) -> str:
    if any(f["schwere"] == "rot" for f in funde):
        return "blockiert"
    if any(f["schwere"] == "gelb" for f in funde):
        return "optimieren"
    return "gruen"


# ---------------------------------------------------------------- Deterministische Fixes
def _flesch_body(body: str, slug: str = "pruefling") -> float | None:
    """Flesch-Amstad eines Bodys – über die Mess-SSOT (readability_check).

    `parse_article` braucht Frontmatter-Grenzen; gemessen wird der Body.
    None = nicht messbar (Aufrufer entscheidet fail-closed).
    """
    rohtext = "---\ntitle: \"Messung\"\n---\n" + (body or "")
    try:
        satz = readability_check.parse_article(rohtext, f"{slug}/index.md")
        if not satz:
            return None
        return readability_check.analyze(satz)["flesch"]
    except Exception:  # noqa: BLE001 – ohne Messung kein Urteil
        return None


def _lesbarkeit_deterministisch(artikel: dict) -> str | None:
    """E6 ohne KI: Stufe A des Lesbarkeits-Heilers, Tor T1–T4 entscheidet.

    Warum als BIBLIOTHEK und nicht als eigener Satzschnitt: Der Heiler ist
    unter Siegel und trägt die Wirkungsprobe (`--wirkungsprobe`, Governance C25).
    Eine zweite Satz-Zerlegung im Haus wäre eine zweite Wahrheit – genau die
    Bauart, die den Bestand schon einmal in zwei Messungen gespalten hat (#585).

    Rückgabe: Beschreibung des Fixes oder None (nichts geschrieben).
    """
    try:
        with open(artikel["path"], encoding="utf-8") as fh:
            alt = fh.read()
    except OSError:
        return None
    slug = artikel["slug"]
    try:
        neu, protokoll = lesbarkeit_heiler.stufe_a(alt)
    except Exception as exc:  # noqa: BLE001 – Werkzeugfehler heilt nichts
        print(f"  ⚠ Lesbarkeits-Heiler nicht ausführbar ({exc.__class__.__name__})")
        return None
    if neu == alt:
        return None
    gruende = lesbarkeit_heiler.verifiziere(slug, alt, neu)
    if gruende:
        print(f"  ⚠ Lesbarkeits-Heiler (Stufe A) verworfen: {gruende[0]}")
        return None
    teile = neu.split("---", 2)
    if len(teile) < 3:
        return None
    neu_body = teile[2]
    vorher, nachher = _flesch_body(artikel["body"], slug), _flesch_body(neu_body, slug)
    artikel["body"] = neu_body
    artikel_speichern(artikel)
    return (f"Lesbarkeits-Heiler Stufe A (Lexikon {protokoll.get('lexikon', 0)}, "
            f"Satzschnitte {protokoll.get('saetze', 0)}, "
            f"Absätze {protokoll.get('absaetze', 0)}) – Flesch "
            f"{vorher if vorher is not None else float('nan'):.1f} → "
            f"{nachher if nachher is not None else float('nan'):.1f}")


def deterministische_fixes(artikel: dict, funde: list[dict]) -> list[str]:
    """Sichere Reparaturen ohne KI. Rückgabe: Liste der angewandten Fixes."""
    angewandt = []
    codes = {f["code"] for f in funde}

    if "E6" in codes:  # Lesbarkeit → Stufe A des Heilers (kein zweiter Splitter)
        fix = _lesbarkeit_deterministisch(artikel)
        if fix:
            angewandt.append(fix)
    if "E8" in codes:  # Leerzeichen-URLs → Bindestrich (R8-Konvention)
        neu = re.sub(r"(\]\([^)\s]*)([ ])([^)]*\))", r"\1-\3", artikel["body"])
        if neu != artikel["body"]:
            artikel["body"] = neu
            angewandt.append("URL-Leerzeichen → Bindestrich")

    if "E5" in codes:  # Titel fixen (check_titles-SSOT + Wortgrenzen-Kürzung)
        neu = check_titles.fix_title(artikel["titel"])
        neu = post_utils.safe_title_cut(neu, 60)
        if neu != artikel["titel"]:
            artikel["fm"] = _fm_set(artikel["fm"], "title", neu)
            artikel["titel"] = neu
            angewandt.append(f"Titel → „{neu}“")

    if "E9" in codes and artikel["ai_generated"]:
        artikel["body"] = (artikel["body"].rstrip()
                           + "\n\n" + ks.cta_block()
                           + "\n" + ks.DISCLAIMER + "\n")
        angewandt.append("CTA-Block + Werbe-Offenlegung angehängt")

    if "E11" in codes:
        neu = ks.clip_text(
            f"{artikel['titel']} – so gehst du Schritt für Schritt vor, "
            "mit Rechenbeispiel und FAQ. Ehrlich, Zahlen statt "
            "Werbeversprechen.")
        if neu != artikel["description"]:
            artikel["fm"] = _fm_set(artikel["fm"], "description", neu)
            artikel["description"] = neu
            angewandt.append(f"Description → {len(neu)} Zeichen")

    if angewandt:
        artikel_speichern(artikel)
    return angewandt


# ---------------------------------------------------------------- KI-Politur
def _laenge(body: str) -> int:
    """Fließtext-Zeichen des Bodys – dieselbe Messung wie E2 (length_policy)."""
    try:
        return length_policy.measure(body)[1]
    except Exception:  # noqa: BLE001
        return len(body)


def politur_auftrag(artikel: dict, funde: list[dict]) -> str:
    fundliste = "\n".join(f"- [{f['code']}] {f['text']}" for f in funde)
    floor = length_policy.POSTS["target_min_chars"]
    ist_zeichen = _laenge(artikel["body"])
    # Ziel-Länge: unter dem Floor muss die Politur den Floor erreichen (sonst
    # bleibt E2 gelb und der Entwurf wird nie freigegeben – der Auftrag muss
    # also dieselbe Zahl nennen, die das Gate prüft). Oberhalb des Floors gilt
    # die Behalte-Regel (max. 15 % Kürzung).
    ziel_zeichen = floor if ist_zeichen < floor else int(len(artikel["body"]) * 0.9)
    min_zeichen = max(int(floor * 0.97),
                      int(len(artikel["body"]) * 0.9)) \
        if len(artikel["body"]) < floor else int(len(artikel["body"]) * 0.85)
    # IST-Lage mitliefern (Muster `lesbarkeit_heiler._ki_prompt`): Ein Auftrag
    # ohne Zahlen lässt das Modell „schöner“ schreiben statt messbar besser.
    flesch = _flesch_body(artikel["body"], artikel["slug"])
    try:
        satz = readability_check.parse_article(
            "---\ntitle: \"Messung\"\n---\n" + artikel["body"],
            f"{artikel['slug']}/index.md")
        masse = readability_check.analyze(satz) if satz else {}
    except Exception:  # noqa: BLE001
        masse = {}
    lage = (f"LESBARKEIT IST (gemessen): Flesch-Amstad "
            f"{flesch if flesch is not None else float('nan'):.1f} · "
            f"Ø Satzlänge {masse.get('wps', 0):.1f} Wörter · "
            f"Ø Wortlänge {masse.get('word_len', 0):.1f} Zeichen · "
            f"{masse.get('long_pct', 0):.1f} % lange Wörter. "
            f"ZIEL: Flesch-Amstad ≥ {LESBARKEITS_SCHWELLE:g} – diese Zahl wird "
            "nach deiner Fassung gemessen; liegt sie darunter, wird deine "
            "Fassung verworfen (die Datei bleibt dann unverändert).")
    laenge_lage = (
        f"LÄNGE IST (gemessen): {ist_zeichen:,} Zeichen Fließtext. "
        f"ZIEL: mindestens {ziel_zeichen:,} Zeichen"
        + (f" – es fehlen {ziel_zeichen - ist_zeichen:,} Zeichen. Forme die "
           "vorhandenen Inhalte aus (Beispiele als Rechenbeispiel "
           "kennzeichnen, FAQ-Antworten runder, Faustregeln als solche "
           "gekennzeichnet) statt Neues zu erfinden."
           if ist_zeichen < floor else "")
        + " Diese Zahl wird nach deiner Fassung gemessen; liegt sie darunter, "
          "wird deine Fassung verworfen.")
    return (
        "FUNDLISTE (diese Punkte beheben):\n" + fundliste
        + "\n\n" + lage + "\n\n" + laenge_lage
        + f"\n\nSICHERHEITSVERTRAG: Behalte jede Markdown-Verlinkung exakt, "
        f"die Zahl der ## -Überschriften bleibt gleich, Mindestlänge "
        f"{min_zeichen:,} Zeichen, keine neuen Fakten oder Zahlen.\n\n"
        f"ARTIKEL-ENTWURF:\n{artikel['body']}\n\n"
        "Gib jetzt NUR den überarbeiteten Artikel-Body zurück.")


def politur_pruefen(alt: str, neu: str, cfg: dict) -> str | None:
    """Sicherheitsvertrag verifizieren. Rückgabe: Fehlermeldung oder None.

    Seit 12.10.2026 (Issue #712) gehört der WIRKUNGSNACHWEIS dazu: Die
    Lesbarkeit der neuen Fassung wird gemessen. Vorher prüfte der Vertrag
    Links, Überschriften, Länge und Floskeln – nur nicht die Kennzahl, wegen
    der die Politur überhaupt lief. Ein Entwurf mit Flesch 47 kam so als
    „poliert“ zurück, blieb gelb, wurde nie freigegeben und stand im nächsten
    Governance-Report wieder als Befund (dieselbe Lehre wie #609: eine
    Heilung ohne Wirkung ist Papier). Fail-closed: ohne Messung kein Freispruch.
    """
    if not neu or not neu.strip():
        return "leere Antwort"
    neu = neu.strip()
    neu = re.sub(r"^```(?:markdown|md)?\s*|\s*```$", "", neu).strip()
    if neu.startswith("---"):
        return "Antwort enthält Frontmatter (verboten)"
    if len(LINK_RX.findall(neu)) != len(LINK_RX.findall(alt)):
        return (f"Linkanzahl geändert "
                f"({len(LINK_RX.findall(alt))} → {len(LINK_RX.findall(neu))})")
    if sorted(LINK_RX.findall(alt)) != sorted(LINK_RX.findall(neu)):
        return "Links wurden verändert (Text oder URL)"
    if len(H2_RX.findall(neu)) < len(H2_RX.findall(alt)):
        return (f"H2-Anzahl reduziert ({len(H2_RX.findall(alt))} → "
                f"{len(H2_RX.findall(neu))})")
    if len(neu) < len(alt) * (cfg["min_behalte_laenge_prozent"] / 100):
        return (f"zu kurz ({len(neu):,} < "
                f"{int(len(alt) * cfg['min_behalte_laenge_prozent'] / 100):,})")
    floor = length_policy.POSTS["target_min_chars"]
    alt_zeichen, neu_zeichen = _laenge(alt), _laenge(neu)
    if alt_zeichen < floor and neu_zeichen < floor:
        return (f"Länge nicht erreicht: {neu_zeichen:,} < Floor {floor:,} "
                f"(vorher {alt_zeichen:,}) – ein Entwurf unter dem Floor bleibt "
                "unpublizierbar (E2), die Politur muss ihn anheben")
    text_norm = re.sub(r"\s+", " ", neu).lower()
    if [f for f in PROFI_FLOSKELN if f in text_norm]:
        return "KI-Floskeln noch enthalten"
    alt_f, neu_f = _flesch_body(alt), _flesch_body(neu)
    if alt_f is None or neu_f is None:
        return "Lesbarkeit nicht messbar – fail-closed (keine Freigabe ohne Messung)"
    if alt_f < LESBARKEITS_SCHWELLE:
        if neu_f < LESBARKEITS_SCHWELLE:
            return (f"Lesbarkeit nicht erreicht: Flesch {neu_f:.1f} < "
                    f"Schwelle {LESBARKEITS_SCHWELLE:g} "
                    f"(vorher {alt_f:.1f}) – die Politur hat das Publish-Kriterium "
                    "nicht bewegt")
        if neu_f <= alt_f:
            return (f"Lesbarkeit nicht verbessert ({alt_f:.1f} → {neu_f:.1f}) – "
                    "ohne Bewegung ist die Politur wirkungslos")
    elif neu_f < alt_f - 1.0:
        return (f"Lesbarkeit verschlechtert ({alt_f:.1f} → {neu_f:.1f}) – "
                "die Politur darf nichts kaputt machen")
    return None


def ki_politur(artikel: dict, funde: list[dict], cfg: dict) -> tuple[bool, str]:
    """Eine Politur-Runde mit Verifikation. (ok, provider|grund)."""
    kette = [p for p in os.environ.get("ENDREDAKTION_KETTE", "groq,gemini")
             .split(",") if p.strip()]
    for versuch, provider in enumerate(kette[:max(1, len(kette))]):
        antwort = llm_client.chat(
            provider, politur_auftrag(artikel, funde),
            system=LEKTOR_SYSTEM, temperature=0.35, max_tokens=8000)
        if not antwort:
            continue
        fehler = politur_pruefen(artikel["body"], antwort, cfg)
        if fehler:
            print(f"  ⚠ Politur ({provider}) verworfen: {fehler}")
            continue
        artikel["body"] = antwort.strip()
        artikel_speichern(artikel)
        return True, provider
    return False, "kein Anbieter bestand den Sicherheitsvertrag"


# ---------------------------------------------------------------- Freigabe (der EINE Weg)
def gib_frei(artikel: dict) -> bool:
    """Reiht einen grünen Entwurf in die Re-Queue ein (wie --promote).

    cadence_guard (Content-Engine-Lauf) veröffentlicht ihn am nächsten
    Publikationstag (Mo/Mi/Fr) bis zum Tageslimit. Die Endredaktion
    veröffentlicht NIE selbst – sie bleibt Einreicher, nie Veröffentlicher.
    """
    if not park_state.rearm(
            artikel["path"],
            "Endredaktion: alle Gates grün – automatisch freigegeben "
            f"({heute_iso()})", park_state.now_utc_iso()):
        print(f"  ⚠ Park-Mechanismus konnte {artikel['slug']} nicht einreihen.")
        return False
    park_state.set_field(artikel["path"], "endredaktion_status", "freigegeben")
    return True


# ---------------------------------------------------------------- Mastodon (Poppy-Karten)
def _mastodon_post(text: str) -> tuple[bool, str]:
    """Direkter Post über MASTODON_ACCESS_TOKEN (Muster: social_dialog)."""
    token = os.environ.get("MASTODON_ACCESS_TOKEN", "").strip()
    if not token:
        return False, "MASTODON_ACCESS_TOKEN fehlt"
    instanz = (os.environ.get("MASTODON_INSTANCE")
               or "https://mastodon.social").rstrip("/")
    daten = json.dumps({"status": text[:500]}).encode("utf-8")
    req = urllib.request.Request(
        f"{instanz}/api/v1/statuses", data=daten, method="POST",
        headers={"Authorization": f"Bearer {token}",
                 "Content-Type": "application/json",
                 "User-Agent": "FranksFinanzcheck-Endredaktion/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        return bool(payload.get("url")), payload.get("url", "")
    except Exception as e:  # noqa: BLE001 – Posting darf nie crashen
        return False, f"{type(e).__name__}: {e}"


def mastodon_lauf(cfg: dict) -> list[str]:
    """Veröffentlicht fertige Poppy-Social-Texte, sobald der Artikel LIVE ist."""
    if not cfg["kanal_mastodon"]:
        return ["Kanal Mastodon in der Konfiguration deaktiviert."]
    try:
        import poppy_lib
    except Exception as e:  # noqa: BLE001 – Poppy ist optionaler Zulieferer
        return [f"Poppy-Werkbank nicht verfügbar ({e})"]
    zeilen, gesendet = [], 0
    for karte in poppy_lib.lade_karten():
        if gesendet >= int(cfg["mastodon_max_pro_lauf"]):
            break
        erg = karte.get("erzeugnisse") or {}
        text = (erg.get("mastodon") or "").strip()
        slug = (erg.get("blog") or {}).get("slug", "")
        if (karte.get("status") != "verwertet" or not text or not slug
                or erg.get("mastodon_gesendet")):
            continue
        # Nur posten, wenn der Artikel wirklich live ist (draft weg)
        pfad = post_utils.post_path(slug)
        if not os.path.exists(pfad):
            continue
        with open(pfad, encoding="utf-8") as fh:
            kopf = fh.read(1500)
        if re.search(r"(?m)^draft:\s*true", kopf):
            continue  # noch nicht veröffentlicht
        url = erg.get("artikel_url") or \
            f"https://franksfinanzcheck.de/posts/{slug}/"
        ok, info = _mastodon_post(f"{text}\n{url}")
        if ok:
            erg["mastodon_gesendet"] = now_utc_iso()
            karte["erzeugnisse"] = erg
            poppy_lib.protokolliere(karte, f"Mastodon-Post automatisch "
                                   f"veröffentlicht: {info}")
            poppy_lib.speichere_karte(karte)
            zeilen.append(f"- **Mastodon:** {karte['id']} → {info}")
            gesendet += 1
        else:
            zeilen.append(f"- **Mastodon übersprungen** ({karte['id']}): {info}")
    if not zeilen:
        zeilen = ["Keine neuen Mastodon-Posts fällig "
                  "(Artikel live + Karte verwertet + noch nicht gesendet)."]
    return zeilen


# ---------------------------------------------------------------- Spam-Schutz-Handshake
def spam_status_pruefen(cfg: dict) -> tuple[bool, str]:
    """Auto-Freigabe nur mit gültigem (nicht-rotem) Spam-Status.

    Fail-closed: kein Statusfile oder rot → keine Auto-Freigabe.
    Die Spam-Schutz-Wache (scripts/spam_schutz_wache.py) schreibt das
    File täglich VOR diesem Lauf. Notbremsen setzen zusätzlich direkt
    modus: manuell – dieser Check ist die zweite Verteidigungslinie."""
    if not os.path.exists(SPAM_STATUS_FILE):
        if cfg.get("spam_status_erforderlich", True):
            return False, ("kein Spam-Statusfile (Wache noch nicht gelaufen?) "
                           "– Auto-Freigabe gesperrt (fail-closed)")
        return True, "kein Spam-Statusfile (nicht erforderlich)"
    try:
        with open(SPAM_STATUS_FILE, encoding="utf-8") as fh:
            status = json.load(fh)
        urteil = str(status.get("urteil", "")).lower()
    except Exception as e:  # noqa: BLE001 – unlesbares File = gesperrt
        return False, f"Spam-Statusfile nicht lesbar ({e}) – gesperrt"
    if urteil == "rot":
        probleme = "; ".join(status.get("probleme") or [])[:200]
        return False, (f"Spam-Schutz-Wache ROT ({probleme}) – "
                       "Auto-Freigabe gesperrt, Notbremse prüfen")
    return True, f"Spam-Schutz-Wache {urteil} – Auto-Freigabe erlaubt"


def wochenbudget_status(cfg: dict) -> tuple[int, bool]:
    """(belegt, voll) – Auto-Freigaben der letzten 7 Tage gegen das Budget.

    Signal: endredaktion_status: freigegeben + Veröffentlichungsdatum im
    7-Tage-Fenster (cadence_guard setzt das Datum bei der Promotion)."""
    vor7 = (datetime.date.today()
            - datetime.timedelta(days=6)).isoformat()
    heute = datetime.date.today().isoformat()
    belegt = 0
    for path in post_utils.list_post_paths():
        try:
            with open(path, encoding="utf-8") as fh:
                kopf = fh.read(2500)
        except OSError:
            continue
        if not re.search(r"(?m)^endredaktion_status:\s*freigegeben", kopf):
            continue
        m = re.search(r"(?m)^date:\s*(\d{4}-\d{2}-\d{2})", kopf)
        if m and vor7 <= m.group(1) <= heute:
            belegt += 1
    return belegt, belegt >= int(cfg["auto_freigaben_max_pro_woche"])


# ---------------------------------------------------------------- Lauf
def lauf(cfg: dict, *, nur_pruefen: bool = False,
         slug_filter: str | None = None) -> dict:
    """Ein kompletter Lauf. Rückgabe: Zusammenfassung für Report/CLI."""
    entwuerfe = wartende_entwuerfe()
    if slug_filter:
        entwuerfe = [a for a in entwuerfe if a["slug"] == slug_filter]
    summary = {"geprueft": len(entwuerfe), "gruen": 0, "optimiert": 0,
               "blockiert": 0, "freigaben": 0, "details": []}
    if not entwuerfe:
        return summary

    # Lauf-Vorbedingungen (Premium-Spam-Schutz): Spam-Status + Wochenbudget
    spam_ok, spam_hinweis = spam_status_pruefen(cfg)
    budget_belegt, budget_voll = wochenbudget_status(cfg)
    if not spam_ok or budget_voll:
        print(f"  ⚠ Auto-Freigabe gesperrt: {spam_hinweis}"
              + (f" | Wochenbudget {budget_belegt}/"
                 f"{cfg['auto_freigaben_max_pro_woche']} ausgeschöpft"
                 if budget_voll else ""))

    freigaben = 0
    for artikel in entwuerfe:
        funde = pruefe_artikel(artikel, cfg)
        zustand = urteil(funde)
        zeile = {"slug": artikel["slug"], "zustand": zustand, "funde": funde,
                 "fixes": [], "freigabe": False}

        # 1) Deterministische Fixes (auch im Prüf-Modus: nein – nur berichten)
        if zustand != "gruen" and not nur_pruefen:
            fixes = deterministische_fixes(artikel, funde)
            zeile["fixes"] = fixes
            if fixes:
                funde = pruefe_artikel(artikel, cfg)  # neu bewerten
                zustand = urteil(funde)
                zeile["zustand"] = zustand

        # 2) KI-Politur für verbleibende gelbe Funde – UND für die
        #    Lesbarkeits-Klasse in Rot (Flesch < 45). Bis zum 12.10.2026 war
        #    genau das eine Sackgasse: E6 rot → „blockiert“ → keine Politur →
        #    der Entwurf blieb für immer liegen und die Lesbarkeits-Wache
        #    meldete ihn Lauf für Lauf erneut (#712, Artikel energie-update
        #    mit Flesch 38,2). Die Klasse gilt als heilbar, weil der Heiler
        #    eine Wirkungsprobe trägt (Governance C25) und der Vertrag
        #    fail-closed schreibt: nichts Halbfertiges.
        rote_codes = {f["code"] for f in funde if f["schwere"] == "rot"}
        heilbares_rot = bool(rote_codes) and rote_codes <= {"E6"}
        if (zustand == "optimieren" or heilbares_rot) and not nur_pruefen:
            for runde in range(max(1, int(cfg["max_politur_versuche"]))):
                ok, provider = ki_politur(artikel, funde, cfg)
                if ok:
                    funde = pruefe_artikel(artikel, cfg)
                    zustand = urteil(funde)
                    zeile["politur"] = provider
                    if zustand != "optimieren":
                        break
                else:
                    zeile["politur"] = provider
                    break
            zeile["zustand"] = zustand

        # 3) Freigabe (nur grün + Modus automatisch + Spam-Schutz + Budget
        #    + Deckel – die Premium-Kette gegen Scaled Content Abuse)
        if (zustand == "gruen" and not nur_pruefen
                and cfg["modus"] == "automatisch" and cfg["kanal_blog"]
                and not artikel["cadence_wait"]
                and freigaben < int(cfg["max_freigaben_pro_lauf"])):
            if not spam_ok:
                zeile["freigabe_grund"] = "Spam-Schutz: " + spam_hinweis
            elif budget_voll:
                zeile["freigabe_grund"] = (
                    f"Wochenbudget ausgeschöpft ({budget_belegt}/"
                    f"{cfg['auto_freigaben_max_pro_woche']})")
            elif gib_frei(artikel):
                zeile["freigabe"] = True
                freigaben += 1
                summary["freigaben"] += 1

        summary[zustand if zustand in ("gruen", "blockiert") else "optimiert"] \
            += 1
        summary["details"].append(zeile)

    return summary


def schreibe_report(cfg: dict, summary: dict, mastodon: list[str]) -> None:
    stamp = datetime.datetime.now(datetime.timezone.utc)
    _, spam_hinweis = spam_status_pruefen(cfg)
    budget_belegt, _ = wochenbudget_status(cfg)
    zeilen = [
        "# ENDREDAKTION-REPORT",
        "",
        f"_Stand: {stamp.strftime('%d.%m.%Y %H:%M UTC')} – automatisch durch "
        "scripts/endredaktion.py erzeugt._",
        "",
        f"- **Modus:** {cfg['modus']} | Freigaben diesen Lauf: "
        f"{summary['freigaben']} (Deckel {cfg['max_freigaben_pro_lauf']}/Lauf, "
        f"{cfg['auto_freigaben_max_pro_woche']}/Woche)",
        f"- **Entwürfe geprüft:** {summary['geprueft']} – "
        f"{summary['gruen']} grün, {summary['optimiert']} optimiert, "
        f"{summary['blockiert']} blockiert",
        f"- **Spam-Schutz:** {spam_hinweis} | Wochenbudget: {budget_belegt}/"
        f"{cfg['auto_freigaben_max_pro_woche']} belegt",
        "- **Veröffentlichung:** ausschließlich über die Re-Queue → "
        "cadence_guard (Mo/Mi/Fr, 2–3 Artikel/Tag) – nie direkt.",
        "- **Newsletter:** läuft eigenständig über newsletter-daily "
        "(Di/Fr: Digest → QA → Versand); neuer Live-Content fließt "
        "automatisch ein.",
        "",
        "## Entwürfe im Einzelnen",
        "",
    ]
    if not summary["details"]:
        zeilen.append("_Keine wartenden Entwürfe – nichts zu tun._")
    for z in summary["details"]:
        zeilen.append(f"### {z['slug']} – {z['zustand'].upper()}")
        if z.get("fixes"):
            zeilen.append("- Fixes: " + "; ".join(z["fixes"]))
        if z.get("politur"):
            zeilen.append(f"- KI-Politur: {z['politur']}")
        if z["freigabe"]:
            zeilen.append("- ✅ **In der Re-Queue** – cadence_guard "
                          "veröffentlicht ihn am nächsten Publikationstag.")
        if z.get("freigabe_grund"):
            zeilen.append(f"- ⛔ Freigabe gesperrt: {z['freigabe_grund']}")
        for f in z["funde"]:
            zeichen = {"rot": "🔴", "gelb": "🟡", "hinweis": "🔵"}[
                f["schwere"]]
            zeilen.append(f"- {zeichen} {f['code']}: {f['text']}")
        zeilen.append("")
    zeilen += ["## Mastodon", ""] + mastodon
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(zeilen).rstrip() + "\n")


def cmd_status() -> int:
    entwuerfe = wartende_entwuerfe()
    if not entwuerfe:
        print("Keine wartenden Entwürfe. Alles veröffentlicht oder leer.")
        return 0
    print(f"Endredaktion – {len(entwuerfe)} wartende(r) Entwurf/Entwürfe:\n")
    for artikel in entwuerfe:
        funde = pruefe_artikel(artikel)
        zustand = urteil(funde)
        warte = " (bereits in Re-Queue)" if artikel["cadence_wait"] else ""
        icon = {"gruen": "✅", "optimieren": "🟡", "blockiert": "🔴"}[zustand]
        print(f"  {icon} [{zustand:<10}] {artikel['slug']}{warte}")
        for f in funde[:3]:
            print(f"       {f['code']}: {f['text']}")
    print("\nLauf: python3 scripts/endredaktion.py  |  Kill-Switch: "
          "data/endredaktion.yaml → modus: manuell")
    return 0


# ---------------------------------------------------------------- Selbsttest
def _selbsttest() -> int:
    print("Endredaktion – Selbsttest (offline)")
    fehler = []

    # Politur-Sicherheitsvertrag
    cfg = dict(DEFAULT_CONFIG)
    # Floor-lange, gut lesbare Fassung: Ein Body unter dem Längen-Floor ist
    # unpublizierbar (E2) – der Selbsttest misst deshalb mit realistischer
    # Länge, sonst prüfte er einen Zustand, den es im Betrieb nicht gibt.
    lesbar = ("Du prüfst den Vertrag. Der Preis steigt. Du wechselst den "
              "Tarif. Das spart Geld. ")
    gut = (("## A\n\n" + lesbar * 150 + "\n[Link](https://a.de/x)\n\n## B\n\n"
            + lesbar * 80))
    if politur_pruefen(gut, gut, cfg) is not None:
        fehler.append("Politur verwirft identischen Text")
    if politur_pruefen(gut, gut.replace("[Link]", "[Weg]"), cfg) is None:
        fehler.append("Politur lässt geänderten Link-Text/URL durch")
    if politur_pruefen(gut, "kurz", cfg) is None:
        fehler.append("Politur lässt radikal gekürzten Text durch")
    if politur_pruefen(gut, "---\ntitle: x\n---\n" + gut, cfg) is None:
        fehler.append("Politur lässt Frontmatter durch")
    if politur_pruefen(gut, gut + " Heutzutage ist alles besser.", cfg) is None:
        fehler.append("Politur lässt KI-Floskel durch")

    # Wirkungsnachweis der Politur (Issue #712): Die Lesbarkeit der neuen
    # Fassung wird GEMESSEN. Ein Lektor, der die Kennzahl nicht bewegt, für
    # die er gerufen wurde, ist keine Heilung – er ist eine Wiederholung.
    schlecht = ("## A\n\nIm Rahmen von umfangreichen Vertragsbedingungen "
                "erfolgt eine Berücksichtigung der Verbrauchsmuster der "
                "Verbraucher, und die Tarifberatung dokumentiert die "
                "Vereinbarung der Zahlungsmodalitäten für die Folgejahre. "
                * 70)
    gut_lesbar = ("## A\n\n" + ("Du zahlst zu viel. Der Anbieter prüft den "
                  "Preis. Ein Wechsel lohnt sich. Das dauert nur Minuten. "
                  "So sparst du Geld. " * 130))
    alt_f = _flesch_body(schlecht)
    neu_f = _flesch_body(gut_lesbar)
    if alt_f is None or neu_f is None:
        fehler.append("Politur-Wirkungsprobe nicht messbar (fail-closed)")
    else:
        if alt_f >= LESBARKEITS_SCHWELLE:
            fehler.append("Politur-Probe startet nicht unter der Schwelle")
        if neu_f < LESBARKEITS_SCHWELLE:
            fehler.append("Politur-Probe erreicht die Schwelle nicht")
        # (a) Fassung, die die Schwelle NICHT bewegt, wird verworfen.
        if politur_pruefen(schlecht, schlecht, cfg) is None:
            fehler.append("Politur lässt eine unveränderte Textverstümmelung "
                          "unter der Schwelle durch (#712)")
        # (b) Fassung, die die Schwelle erreicht, wird angenommen.
        if politur_pruefen(schlecht, gut_lesbar, cfg) is not None:
            fehler.append("Politur verwirft eine messbar bessere Fassung "
                          "(Wirkungsnachweis blockiert den Heiler)")
        # (c) Verschlechterung eines guten Textes wird verworfen.
        if politur_pruefen(gut_lesbar, schlecht, cfg) is None:
            fehler.append("Politur lässt eine Verschlechterung durch")
    # (d) Die Schwelle ist IMPORTIERT (eine Zahl im Haus, Lehre #585).
    if LESBARKEITS_SCHWELLE != readability_check.NEW_FLESCH_MIN:
        fehler.append("Endredaktion führt eine eigene Lesbarkeits-Schwelle")
    # (e) Der Auftrag nennt IST und ZIEL – sonst schreibt das Modell „schöner“
    #     statt messbar besser.
    auftrag = politur_auftrag(
        {"body": schlecht, "slug": "probe", "titel": "Probe",
         "path": os.path.join(BLOG_DIR, "content", "posts", "probe", "index.md")},
        [fund("E6", "rot", "Flesch 38 < 60")])
    for marke in ("LESBARKEIT IST", "ZIEL: Flesch-Amstad", "LÄNGE IST"):
        if marke not in auftrag:
            fehler.append(f"Politur-Auftrag ohne Ist-Lage („{marke}“ fehlt)")
    # (f) Der Heiler ist als Bibliothek verdrahtet (eine Satz-Zerlegung im
    #     Haus, nicht zwei – die SSOT-Regel aus #585).
    if not hasattr(lesbarkeit_heiler, "stufe_a") or not hasattr(
            lesbarkeit_heiler, "verifiziere"):
        fehler.append("Lesbarkeits-Heiler ist nicht als Bibliothek nutzbar")

    # Urteils-Logik
    if urteil([]) != "gruen" or urteil([fund("X", "gelb", "y")]) != "optimieren" \
            or urteil([fund("X", "rot", "y")]) != "blockiert":
        fehler.append("Urteils-Logik falsch")

    # Modus fail-closed
    if lade_config()["modus"] not in ("automatisch", "manuell"):
        fehler.append("Konfig-Modus nicht fail-closed")

    if "ERFINDE NICHTS" not in LEKTOR_SYSTEM:
        fehler.append("Lektor-Prompt ohne Anti-Halluzinations-Regel")
    if fehler:
        print("  ✗ " + "\n  ✗ ".join(fehler))
        return 2
    print("  ✓ Sicherheitsvertrag, Urteils-Logik, Konfig-Wache, "
          "Lektor-Prompt: in Ordnung.")
    return 0


# ---------------------------------------------------------------- CLI
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Endredaktion: Entwürfe prüfen, optimieren, freigeben")
    ap.add_argument("--nur-pruefen", action="store_true",
                    help="nur Bericht – keine Fixes, keine Politur, keine Freigabe")
    ap.add_argument("--slug", help="nur diesen Entwurf bearbeiten")
    ap.add_argument("--status", action="store_true",
                    help="Kurzübersicht der wartenden Entwürfe")
    ap.add_argument("--selftest", action="store_true",
                    help="fail-closed-Selbsttest (Exit 2 bei Defekt)")
    args = ap.parse_args()

    if args.selftest:
        return _selbsttest()
    if args.status:
        return cmd_status()

    cfg = lade_config()
    summary = lauf(cfg, nur_pruefen=args.nur_pruefen, slug_filter=args.slug)
    mastodon = ["(übersprungen – Prüf-Modus)"] if args.nur_pruefen \
        else mastodon_lauf(cfg)
    schreibe_report(cfg, summary, mastodon)

    print(f"Endredaktion: {summary['geprueft']} geprüft – "
          f"{summary['gruen']} grün, {summary['optimiert']} optimiert, "
          f"{summary['blockiert']} blockiert, "
          f"{summary['freigaben']} Freigabe(n) in die Re-Queue.")
    print(f"Report: {os.path.relpath(REPORT_FILE, BLOG_DIR)}")
    if cfg["modus"] == "manuell":
        print("ℹ Modus „manuell“ (Kill-Switch aktiv) – es wurde nichts "
              "automatisch freigegeben.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
