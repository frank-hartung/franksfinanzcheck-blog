#!/usr/bin/env python3
"""Zugangs-Namensvertrag, Wert-Dichtheit und Unterdrückungsverbot (Alert #78).

Hintergrund
-----------
Code-Scanning-Alert #78 („Clear-text logging of sensitive information",
CodeQL `py/clear-text-logging-sensitive-data` /
`py/clear-text-storage-sensitive-data`) entstand NICHT dort, wo ein echter
Zugangswert ausgegeben wurde. Er entstand, weil Felder, Variablen,
Parameter und Funktionen BEHAUPTETEN, Zugangsdaten zu führen:

    "secrets": ["MASTODON_ACCESS_TOKEN"]    # in Wahrheit: NAMEN
    "fehlende_secrets": [...]               # in Wahrheit: Namen der Fehlenden
    "secrets_age_red": 2                    # in Wahrheit: ein Ampel-Zähler
    def c9_secret_leak(texts): ...          # in Wahrheit: Befund-Texte
    def bucket_secrets(gov, state): ...     # in Wahrheit: Zugangs-NACHWEISE

CodeQL klassifiziert Daten über ihren NAMEN (SensitiveDataHeuristics –
rein namensbasiert, Quelle unten). Ein falscher Name ist deshalb kein
Schönheitsfehler, sondern ein Befund – und für Menschen die Vorstufe
eines echten Lecks: Wer ein Feld `secrets` vorfindet, füllt es irgendwann
mit einem Secret. Die Heilung von #78 ist deshalb ein NAMENSVERTRAG:

    pflicht_env / fehlende_env   = NAMEN von Umgebungsvariablen
    zugang_* / zugangsalter_*    = Ampel- und Nachweis-Metadaten
    JSON-Oberfläche              = required_env_names / missing_env_names /
                                   required_var_names / missing_var_names

Dieser Vertrag steht auf drei Beinen – ein Rückfall müsste alle drei
gleichzeitig überlisten:

  1. NAMENSEBENE (statisch, gegen den Alert): Die Strukturen, die in
     Reports, Logs und JSON-Dateien landen, tragen keinen Schlüssel, den
     die CodeQL-Heuristik als Zugangsdatum liest. Geprüft wird mit den
     ORIGINAL-Regexen aus SensitiveDataHeuristics.qll (1:1 nachgebaut,
     inkl. Gegenprobe, dass der Nachbau scharf ist).

  2. WERTEBENE (dynamisch, gegen das eigentliche Risiko): Mit
     vergifteten Umgebungsvariablen laufen die echten Berichts-
     generatoren. Kein Zugangswert darf in stdout oder in eine
     geschriebene Datei gelangen – namensunabhängig, also auch dann,
     wenn CodeQL seine Heuristik ändert.

  3. UNTERDRÜCKUNGSVERBOT (organisatorisch): Für die beiden Clear-Text-
     Regeln gibt es keine `# codeql[...]`-Unterdrückung mehr – Funde
     dieser Klasse werden an der Quelle geheilt, nie weggeklickt. Das
     Gate erzwingt dasselbe (die Regeln stehen nicht mehr in der
     Unterdrückungs-Whitelist der CodeQL-Wache).

Siehe CODE-SCANNING-ALERT-78-DAUERHEILUNG-PREMIUM-2026-10-05.md.
"""
from __future__ import annotations

import datetime
import io
import json
import os
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cockpit  # noqa: E402
import editorial_scorecard  # noqa: E402
import governance_contract  # noqa: E402
import social_channels as sch  # noqa: E402
import social_preflight  # noqa: E402


# --------------------------------------------------------------------------
# 1 · Die CodeQL-Heuristik, 1:1 nachgebaut
# --------------------------------------------------------------------------
# Quelle: github/codeql, shared/concepts/codeql/concepts/internal/
#         SensitiveDataHeuristics.qll  (Stand 05.10.2026, verifiziert am
#         Original). Für die Cleartext-Logging/-Storage-Queries zählen die
#         Klassifikationen `secret`, `password` und `private` – `id` und
#         `certificate` sind dort ausgenommen.
#
# Java-Regex-Semantik: `regexpMatch` verlangt den VOLLEN Match, deshalb
# fullmatch(). Lookbehinds mit Alternativen unterschiedlicher Länge sind
# in Python unzulässig und daher in Einzel-Lookbehinds zerlegt –
# semantisch identisch: (?<!is|is_) == (?<!is)(?<!is_).
_MAYBE_SECRET = (
    r"(?is).*((?<!is)(?<!is_)secret"
    r"|(?<!un)(?<!un_)(?<!is)(?<!is_)trusted(?!_iter)"
    r"|confidential).*"
)
_MAYBE_PASSWORD = (
    r"(?is).*(pass(?:wd|word|code|.?phrase)(?!.*question)"
    r"|(?:auth(?:entication|ori[sz]ation)?).?key"
    r"|oauth|api.?(?:key|tok)|([_-]|\b)mfa([_-]|\b)).*"
)
_MAYBE_PRIVATE = (
    r"(?is).*(social.?security|employer.?identification|national.?insurance"
    r"|resident.?id|passport.?(?:num|no)|([_-]|\b)ssn([_-]|\b)"
    r"|post.?code|zip.?code|home.?addr"
    r"|(?:mob(?:ile)?|home).?(?:num|no|tel|phone)|(?:tel|fax|phone).?(?:num|no)|telephone"
    r"|emergency.?contact|latitude|longitude|nationality"
    r"|(?:credit|debit|bank|visa).?(?:card|num|no|acc(?:ou)?nt)"
    r"|(?:card|acc(?:ou)?nt).?(?:no|num|credit)|routing.?num"
    r"|salary|billing|beneficiary|credit.?(?:rating|score)"
    r"|([_-]|\b)(?:ccn|cvv|iban)([_-]|\b)|security.?code"
    r"|birth.?da(?:te|y)|da(?:te|y).?(?:of.?)?birth|gender|([_-]|\b)sex([_-]|\b)"
    r"|medical|(?:health|care).?plan|healthkit|appointment|prescription"
    r"|patient.?(?:id|record)|blood.?(?:type|alcohol|glucose|pressure)"
    r"|heart.?(?:rate|rhythm)|body.?(?:mass|fat)|menstrua|pregnan|insulin|inhaler"
    r"|employ(?:er|ee)|spouse|maiden.?name|mac.?addr).*"
)
# notSensitiveRegexp: Namen, die verschlüsselt/gehascht/entschärft sind ODER
# Sonderzeichen enthalten, die das Wort zum Teil eines größeren Gebildes
# machen (URL, Satz, Anzeigetext mit Leerzeichen) – Original:
#   (?is).*([^\w$.-]|redact|censor|obfuscate|hash|md5|sha|random|
#           (?<!unen)crypt|(?<!un)encode|certain|concert|secretar|wildcard|
#           coauthor|account(ant|ab|ing|ed)|(?<!pro)file|path|([_-]|\b)url).*
_NOT_SENSITIVE = (
    r"(?is).*([^\w$.\-]|redact|censor|obfuscate|hash|md5|sha|random"
    r"|(?<!unen)crypt|(?<!un)encode|certain|concert|secretar|wildcard|coauthor"
    r"|account(?:ant|ab|ing|ed)|(?<!pro)file|path|([_-]|\b)url).*"
)

_RX_KLASSEN = {
    "secret": re.compile(_MAYBE_SECRET),
    "password": re.compile(_MAYBE_PASSWORD),
    "private": re.compile(_MAYBE_PRIVATE),
}
_RX_NOT = re.compile(_NOT_SENSITIVE)


def codeql_klassifikation(name: str) -> str | None:
    """Wie CodeQL diesen Namen einstuft – None heißt „nicht sensibel“.

    Reihenfolge wie im Original: notSensitive dominiert (ein Name, der
    auf Entschärfung schließen lässt, ist nie sensibel).
    """
    if not isinstance(name, str) or not name or _RX_NOT.fullmatch(name):
        return None
    for klasse, rx in _RX_KLASSEN.items():
        if rx.fullmatch(name):
            return klasse
    return None


def _alle_schluessel(obj, pfad="") -> list[tuple[str, str]]:
    """Alle Mapping-Schlüssel einer Struktur, mit Pfadangabe."""
    out: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{pfad}.{k}" if pfad else str(k)
            if isinstance(k, str):
                out.append((k, p))
            out += _alle_schluessel(v, p)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            out += _alle_schluessel(v, f"{pfad}[{i}]")
    return out


class HeuristikIstScharf(unittest.TestCase):
    """Ein Vertrag, der nichts erkennt, ist kein Vertrag.

    Beweist, dass der Nachbau der CodeQL-Heuristik tatsächlich greift –
    sonst könnte dieser Test grün bleiben, während er blind ist.
    """

    def test_erkennt_die_namen_die_alert_78_ausgeloest_haben(self):
        faelle = {
            # Felder (Dict-Schlüssel) der 6 Fundstellen
            "secrets": "secret",
            "fehlende_secrets": "secret",
            "secrets_age_red": "secret",
            "secrets_age_amber": "secret",
            "secrets_state": "secret",
            # Funktionsnamen (SensitiveFunctionCall)
            "c9_secret_leak": "secret",
            "bucket_secrets": "secret",
            # Passwort-Klasse (war an #78 beteiligt, z. B. X_API_KEY)
            "X_API_KEY": "password",
            "GEMINI_API_KEY": "password",
            "BLUESKY_APP_PASSWORD": "password",
            "oauth_code": "password",
            "client_secret": "secret",
        }
        for name, klasse in faelle.items():
            self.assertEqual(
                codeql_klassifikation(name), klasse,
                f"{name!r} müsste als {klasse!r} erkannt werden – "
                f"der Heuristik-Nachbau ist stumpf geworden.")

    def test_laesst_die_neuen_namen_und_entschaerfungen_durch(self):
        for name in [
            # neue Feldnamen des Vertrags
            "pflicht_env", "fehlende_env", "zugang_rot", "zugang_gelb",
            "zugang_state", "zugangsalter_rot", "zugangsalter_gelb",
            "zugangsalter_verdict", "zugangsalter_legacy",
            "zugangsalter_proven", "zugangsalter_entries",
            # neue Funktions-/Parameternamen
            "c9_leak_wache", "bucket_zugaenge", "wachen_quelltext",
            # stabile JSON-Oberfläche
            "required_env_names", "missing_env_names",
            "required_var_names", "missing_var_names",
            # notSensitive-Entschärfungen (Original-Beispiele)
            "secrets_path", "secret_hash", "oauth_url",
        ]:
            self.assertIsNone(
                codeql_klassifikation(name),
                f"{name!r} darf nicht als Zugangsdatum gelten")

    def test_anzeigetext_mit_sonderzeichen_ist_kein_schluessel_vertrag(self):
        # Anzeige-Namen wie der Cockpit-Bereich „Secrets & Zugänge“
        # enthalten Sonderzeichen/Leerzeichen – das Original-NotSensitive
        # entschärft sie („noun is part of a larger string“).
        self.assertIsNone(codeql_klassifikation("Secrets & Zugänge"))


class NamensvertragSSOT(unittest.TestCase):
    """data/social/channels.yaml führt NAMEN von Umgebungsvariablen."""

    @classmethod
    def setUpClass(cls):
        cls.cfg = sch.load_config()
        cls.kanaele = sch.channel_map(cls.cfg)

    def test_konfiguration_ist_lesbar(self):
        self.assertTrue(self.kanaele, "channels.yaml liefert keine Kanäle")

    def test_kein_kanal_traegt_noch_das_alte_feld(self):
        alt = [cid for cid, ch in self.kanaele.items()
               if isinstance(ch, dict) and sch.ENV_FELD_ALT in ch]
        self.assertEqual(
            alt, [],
            "Feld `%s` heißt seit 05.10.2026 `%s` (Namensvertrag #78)"
            % (sch.ENV_FELD_ALT, sch.ENV_FELD))

    def test_jeder_aktive_kanal_nennt_seine_pflicht_env_namen(self):
        ohne = [cid for cid, ch in self.kanaele.items()
                if (ch or {}).get("enabled") and not sch.pflicht_env_namen(ch)]
        self.assertEqual(ohne, [], "aktive Kanäle ohne `pflicht_env`-Namen")

    def test_pflicht_env_enthaelt_nur_variablennamen_keine_werte(self):
        """Ein Wert sähe anders aus als ein Variablenname – das ist prüfbar."""
        for cid, ch in self.kanaele.items():
            for name in sch.pflicht_env_namen(ch):
                self.assertRegex(
                    name, r"^[A-Z][A-Z0-9_]{2,63}$",
                    f"{cid}: {name!r} sieht nicht wie ein Variablenname aus – "
                    f"steht hier versehentlich ein WERT?")

    def test_altes_feld_schlaegt_laut_fehl(self):
        """Ein halb migrierter Kanal darf nicht als „braucht nichts“ gelten."""
        with self.assertRaises(ValueError):
            sch.pflicht_env_namen({sch.ENV_FELD_ALT: ["MASTODON_ACCESS_TOKEN"]})
        # Ein Kanal ganz ohne Pflichtfeld ist dagegen ein gültiger Zustand
        # (z. B. ein Kanal, der öffentlich postet oder über den Broker geht).
        self.assertEqual(sch.pflicht_env_namen({"label": "x"}), [])
        # Defensiv: andere kaputte Typen werfen nicht, sondern gelten leer.
        self.assertEqual(sch.pflicht_env_namen(None), [])


class NamensvertragBerichte(unittest.TestCase):
    """Was in Reports, Logs und JSON landet, heißt nicht wie ein Zugangsdatum.

    Geprüft werden die EMITTIERTEN Strukturen der echten Generatoren –
    rekursiv über jeden Schlüssel. Der Governance-Step-Key `secrets`
    (externer Vertrag aus Workflows und data/governance_status.json) darf
    in den EINGABEN vorkommen – der Test beweist, dass er nie in eine
    AUSGABE durchsickert.
    """

    def test_preflight_eintrag(self):
        cfg = sch.load_config()
        kanaele = sch.channel_map(cfg)
        cid = next(iter(kanaele))
        self._pruefe(social_preflight.pruefe_kanal(cid, kanaele[cid], cfg, offline=True),
                     "social_preflight.pruefe_kanal()")

    def test_preflight_json_oberflaeche(self):
        bericht = {"zeit": "x", "kanaele": [
            {"kanal": "mastodon", "pflicht_env": ["MASTODON_ACCESS_TOKEN"],
             "fehlende_env": [], "vars": ["MASTODON_INSTANCE"],
             "fehlende_vars": []}]}
        self._pruefe(social_preflight._sanitize_report_for_json(bericht),
                     "social_preflight --json (Oberfläche)")

    def test_schaltwerk_kanalzustand(self):
        import schaltwerk_actions
        self._pruefe(schaltwerk_actions.kanal_zustand(),
                     "schaltwerk_actions.kanal_zustand()")

    def test_schaltwerk_standby_event(self):
        import schaltwerk_triggers
        ctx = {"jetzt": datetime.datetime(2026, 10, 5, 8, 0,
                                          tzinfo=datetime.timezone.utc)}
        events = schaltwerk_triggers.trigger_kanal_standby({"erinnerung_tage": 14}, ctx)
        for ev in events:
            self._pruefe(ev, "schaltwerk_triggers.trigger_kanal_standby()")

    def test_scorecard_kennzahlen_und_historie(self):
        d = editorial_scorecard.collect()
        self._pruefe(d, "editorial_scorecard.collect()")
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(editorial_scorecard, "_HISTORY",
                                   os.path.join(tmp, "h.jsonl")):
                row = editorial_scorecard._append_history(d, 80)
        self._pruefe(row, "editorial_scorecard-Historienzeile")

    def test_cockpit_status_json(self):
        now = datetime.datetime(2026, 10, 5, 8, 0, tzinfo=datetime.timezone.utc)
        # Realistische Eingabe MIT dem externen Governance-Step-Key `secrets`
        # – die Ausgabe muss trotzdem frei von ihm bleiben.
        governance = {"steps": {"secrets": {"level": "red", "message": "Pinterest tot"}}}
        overall, buckets = cockpit.build_cockpit(
            now, governance, {"ready": 6, "target": 6},
            {"entries": {"MASTODON_ACCESS_TOKEN": {"quality": "proven"}}},
            {"channels": {"mastodon": {"enabled": True, "label": "Mastodon",
                                       "pflicht_env": ["MASTODON_ACCESS_TOKEN"]}}},
            {"history": []}, [], {"pending": []})
        self._pruefe(cockpit.build_status_json(now, overall, buckets),
                     "cockpit.build_status_json()")

    def _pruefe(self, struktur, wo):
        schlecht = [(k, p, codeql_klassifikation(k))
                    for k, p in _alle_schluessel(struktur)
                    if codeql_klassifikation(k)]
        self.assertEqual(
            schlecht, [],
            f"{wo}: Schlüssel behaupten, Zugangsdaten zu enthalten "
            f"(CodeQL-Heuristik). Umbenennen – z. B. `pflicht_env`, "
            f"`fehlende_env`, `zugang_*` – nie unterdrücken. Fundstellen: {schlecht}")


# --------------------------------------------------------------------------
# 2 · Wert-Dichtheit: der Beweis, der ohne CodeQL gilt
# --------------------------------------------------------------------------
GIFT = "GIFTWERT-DARF-NIE-AUSGEGEBEN-WERDEN-7F3A91"

#: Dienst-Zugänge, die in den geprüften Abläufen gelesen werden könnten –
#: zusätzlich zu den Namen aus channels.yaml (dynamisch, siehe unten).
_DIENST_ENV = [
    "GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY",
    "PINTEREST_ACCESS_TOKEN", "PINTEREST_APP_ID", "PINTEREST_APP_SECRET",
    "PINTEREST_REFRESH_TOKEN", "RESEND_API_KEY", "UMAMI_API_TOKEN",
    "AWIN_API_TOKEN", "GITHUB_TOKEN", "GH_TOKEN",
    # virtueller Kanal YouTube (steht nicht in channels.yaml)
    "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN",
    "YOUTUBE_CHANNEL_ID",
]


def _gift_env_namen() -> list[str]:
    """Alle Zugangs-Namen aus der SSOT + den Dienst-Keys – dynamisch."""
    namen = set(_DIENST_ENV)
    try:
        for ch in sch.channel_map(sch.load_config()).values():
            namen |= set(sch.pflicht_env_namen(ch))
            namen |= {str(v) for v in (ch or {}).get("vars") or []}
    except Exception:  # noqa: BLE001 – SSOT unlesbar: Grundmenge reicht
        pass
    return sorted(namen)


class WertDichtheit(unittest.TestCase):
    """Mit vergifteten Zugängen darf kein WERT in Ausgabe oder Datei landen.

    Alle Zugangsvariablen werden mit demselben Marker belegt; dann laufen
    die echten Berichtsgeneratoren. Der Marker darf nirgends auftauchen –
    weder in stdout noch in einer geschriebenen Datei. Das prüft die
    EIGENSCHAFT (Werte bleiben draußen), nicht den Namen.
    """

    def setUp(self):
        self._alt = dict(os.environ)
        for i, name in enumerate(_gift_env_namen()):
            os.environ[name] = f"{GIFT}-{i:02d}"
        self.addCleanup(self._env_zurueck)

    def _env_zurueck(self):
        os.environ.clear()
        os.environ.update(self._alt)

    def _dicht(self, text: str, wo: str):
        self.assertNotIn(GIFT, text, f"{wo}: ein Zugangswert steht im Klartext da")

    def test_social_preflight_json_ist_dicht(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            social_preflight.main(["--offline", "--json", "--kein-bericht"])
        roh = buf.getvalue()
        self._dicht(roh, "social_preflight --offline --json")
        # Die NAMEN stehen drin – der Bericht ist also nicht einfach leer.
        self.assertIn("MASTODON_ACCESS_TOKEN", roh)
        self.assertIn('"required_env_names"', roh)

    def test_social_preflight_konsole_und_markdown_sind_dicht(self):
        with tempfile.TemporaryDirectory() as tmp:
            ziel = os.path.join(tmp, "SOCIAL-PREFLIGHT-STATUS.md")
            buf = io.StringIO()
            with redirect_stdout(buf):
                social_preflight.main(["--offline", "--bericht", ziel])
            self._dicht(buf.getvalue(), "social_preflight --offline (Konsole)")
            self._dicht(Path(ziel).read_text(encoding="utf-8"),
                        "SOCIAL-PREFLIGHT-STATUS.md")

    def test_cockpit_markdown_und_status_json_sind_dicht(self):
        now = datetime.datetime(2026, 10, 5, 8, 0, tzinfo=datetime.timezone.utc)
        cfg = sch.load_config()
        zustand = {"entries": {n: {"quality": "proven"}
                               for ch in sch.channel_map(cfg).values()
                               for n in sch.pflicht_env_namen(ch)}}
        overall, buckets = cockpit.build_cockpit(
            now, {}, {"ready": 6, "target": 6}, zustand, cfg,
            {"history": []}, [], {"pending": []})
        self._dicht(cockpit.render_markdown(now, overall, buckets), "COCKPIT.md")
        self._dicht(json.dumps(cockpit.build_status_json(now, overall, buckets)),
                    "data/cockpit_status.json")

    def test_scorecard_report_und_historie_sind_dicht(self):
        d = editorial_scorecard.collect()
        self._dicht(editorial_scorecard.render(d, editorial_scorecard._score(d)),
                    "EDITORIAL-SCORECARD.md")
        with tempfile.TemporaryDirectory() as tmp:
            hist = os.path.join(tmp, "h.jsonl")
            with mock.patch.object(editorial_scorecard, "_HISTORY", hist):
                editorial_scorecard._append_history(d, 80)
            self._dicht(Path(hist).read_text(encoding="utf-8"),
                        "data/scorecard_history.jsonl")

    def test_vertragsbericht_ist_dicht(self):
        """c9_leak_wache findet Zugangs-Material – und zitiert nie den Fund."""
        befunde = governance_contract.c9_leak_wache(
            {"X.md": "token: gsk_" + "A" * 32, "Y.json": f"key: {GIFT}"})
        self.assertTrue(befunde, "C9 erkennt das künstliche Leck nicht mehr")
        self._dicht(governance_contract.render_md(befunde),
                    "governance_contract.render_md()")
        self.assertNotIn("gsk_", governance_contract.render_md(befunde),
                         "C9 zitiert den gefundenen Wert")
        buf = io.StringIO()
        with redirect_stdout(buf):
            for code, msg in befunde:
                print(f"  ❌ {code} {msg}")
        self._dicht(buf.getvalue(), "governance_contract (Konsolenausgabe)")

    def test_gift_test_wuerde_ein_echtes_leck_bemerken(self):
        """Gegenprobe: Der Dichtheitstest ist nicht blind."""
        with self.assertRaises(AssertionError):
            self._dicht(f"Token: {os.environ.get('MASTODON_ACCESS_TOKEN')}",
                        "Gegenprobe")


# --------------------------------------------------------------------------
# 3 · Unterdrückungsverbot für die Clear-Text-Regeln
# --------------------------------------------------------------------------
class Unterdrueckungsverbot(unittest.TestCase):
    """Die beiden Clear-Text-Regeln werden nie unterdrückt – nur geheilt.

    Alert #78 war über mehrere „grüne“ Pull Requests hinweg unbemerkt
    geblieben, weil das Gate nur den Diff prüfte UND weil Unterdrückungen
    (PR #579) den Fund verschwinden ließen, ohne die Ursache zu berühren.
    Seit 05.10.2026 gilt: Diese Fundklasse wird an der Quelle geheilt.
    Eine `# codeql[...]`-Unterdrückung wäre ein Rückfall und fällt hier
    auf – zusätzlich lässt die CodeQL-Wache diese Regeln nicht mehr durch
    die Unterdrückungs-Whitelist (siehe .github/workflows/codeql.yml).
    """

    VERBOTEN = ("codeql[py/clear-text-logging-sensitive-data",
                "codeql[py/clear-text-storage-sensitive-data")

    def test_keine_clear_text_unterdrueckung_im_bestand(self):
        # Diese Datei selbst ist ausgenommen: Sie definiert die verbotenen
        # Marker (VERBOTEN-Tupel oben), matcht also zwangsläufig sich selbst.
        selbst = Path(__file__).resolve()
        befunde = []
        for pfad in list(SCRIPTS.glob("*.py")) + list((SCRIPTS / "tests").glob("*.py")) \
                + list((SCRIPTS / "social_channels").glob("*.py")) \
                + list(ROOT.glob("*.py")) + list((ROOT / "tools").rglob("*.py")) \
                + list((ROOT / "e2e").rglob("*.py")) \
                + list((ROOT / "newsletter-worker").rglob("*.py")) \
                + list((ROOT / "n8n").rglob("*.py")):
            if pfad.resolve() == selbst:
                continue
            text = pfad.read_text(encoding="utf-8", errors="replace")
            for zeile_nr, zeile in enumerate(text.splitlines(), 1):
                for verboten in self.VERBOTEN:
                    if verboten in zeile:
                        befunde.append(f"{pfad.relative_to(ROOT)}:{zeile_nr}")
        self.assertEqual(
            befunde, [],
            "Clear-Text-Funde werden an der Quelle geheilt, nie unterdrückt: "
            + ", ".join(befunde))


if __name__ == "__main__":
    unittest.main(verbosity=2)
