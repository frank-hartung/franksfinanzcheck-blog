#!/usr/bin/env python3
"""Sicherheitsvertrag gegen unvollständige URL-Substring-Prüfungen (Alert #83).

Geprüft wird auf fünf Ebenen:

1. **Die Wache selbst** – `scripts/url_substring_guard.py` besteht ihre
   Eigenprüfung (Positiv-, Gegen- und Musterproben) und ist fail-closed:
   nicht analysierbarer Quelltext liefert Exit 2, nie „sauber".
2. **Der Bestand** – Python, JavaScript und eingebettete HTML-Skripte sind
   frei von Substring-Prüfungen auf URL-Literalen; es gibt keine einzige
   `# codeql[...]`/`# lgtm[...]`-Unterdrückung für die beiden Regeln.
3. **Die geheilten Fundstellen** – `affiliate_marketer.py` und
   `governance_contract.py` urteilen host-exakt; die historischen Muster
   werden von der Wache zuverlässig wiedererkannt (Rückfall-Probe).
4. **Der Betriebsvertrag** – `.github/workflows/codeql.yml` erlaubt keine
   Regel-Unterdrückung mehr und fährt die URL-Wache als eigenen,
   upload-unabhängigen Job.
5. **Die Herkunftsprüfung des Workers** – der KI-Assistent entscheidet CORS
   über den geparsten Host, nicht über Zeichenketten-Enden.

Hintergrund: CODE-SCANNING-ALERT-83-DAUERHEILUNG-PREMIUM-2026-10-10.md.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import tokenize
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import url_host  # noqa: E402
import url_substring_guard as wache  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "codeql.yml"
WORKER = ROOT / "cloudflare" / "ki-assistent" / "worker.js"

# Die beiden Fundstellen, die Alert #83 ausgelöst haben – wortgleich wie vor
# der Heilung. Sie dienen als Rückfall-Probe: Die Wache muss sie erkennen.
RUECKFALL = {
    "affiliate_marketer": '''
def selftest(t3):
    return "https://franksfinanzcheck.de" in t3
''',
    "governance_contract": '''
def c10(text):
    return "api.pinterest.com" in text
''',
}


def _py_ohne_kommentare(pfad: Path) -> str:
    """Python-Quelltext ohne Kommentare.

    Die Begründung einer Heilung ZITIERT die alte, kranke Zeile – ein
    Kommentar darf einen Vertragstest deshalb weder bestehen lassen noch
    brechen. Geprüft wird ausschließlich ausführbarer Code.
    """
    quelle = pfad.read_text(encoding="utf-8")
    toks = tokenize.generate_tokens(io.StringIO(quelle).readline)
    return " ".join(t.string for t in toks if t.type != tokenize.COMMENT)


def _js_ohne_kommentare(pfad: Path) -> str:
    """JavaScript ohne Kommentare – über den Lexer der URL-Wache."""
    return " ".join(t.text for t in wache.js_lexen(pfad.read_text(encoding="utf-8"))
                    if t.art != "kommentar")


def _lauf(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "url_substring_guard.py"), *args],
        capture_output=True, text=True, cwd=str(ROOT), timeout=300, check=False)


class WacheIstScharf(unittest.TestCase):
    """Eine Wache ohne scharfe Proben wäre Scheinsicherheit."""

    def test_eigenpruefung_der_wache(self):
        erg = _lauf("--selftest")
        self.assertEqual(erg.returncode, 0,
                         f"Eigenprüfung der URL-Wache rot:\n{erg.stdout}\n{erg.stderr}")
        for begriff in ("Positivproben", "Gegenproben", "Musterproben",
                        "Fail-closed", "Scope-Proben"):
            self.assertIn(begriff, erg.stdout)

    def test_eigenpruefung_der_host_wahrheit(self):
        erg = subprocess.run([sys.executable, str(SCRIPTS / "url_host.py"), "--selftest"],
                             capture_output=True, text=True, cwd=str(ROOT), timeout=120,
                             check=False)
        self.assertEqual(erg.returncode, 0, erg.stdout + erg.stderr)

    def test_historische_fundstellen_werden_wiedererkannt(self):
        """Hätte diese Wache Alert #83 gefunden? Die Probe beantwortet es."""
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            for name, code in RUECKFALL.items():
                pfad = wurzel / f"{name}.py"
                pfad.write_text(code, encoding="utf-8")
                befunde, fehler = wache.pruefe([pfad], wurzel)
                self.assertEqual(fehler, [], f"{name}: Analysefehler {fehler}")
                self.assertTrue(befunde, f"Rückfall in {name} wurde NICHT erkannt")
                self.assertEqual(befunde[0].regel, wache.REGEL_PY)

    def test_unterdrueckung_zaehlt_als_befund(self):
        """Der Kernvertrag: Unterdrücken ist keine Heilung."""
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            pfad = wurzel / "unterdrueckt.py"
            pfad.write_text(
                "def harmlos():\n"
                "    # codeql[py/incomplete-url-substring-sanitization] Ausnahme\n"
                "    return 1\n", encoding="utf-8")
            befunde, _ = wache.pruefe([pfad], wurzel)
            self.assertEqual([b.art for b in befunde], ["unterdrueckung"])

    def test_nicht_analysierbarer_code_ist_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            kaputt = Path(tmp) / "kaputt.py"
            kaputt.write_text("def unvollstaendig(:\n", encoding="utf-8")
            erg = _lauf("--json", "--quiet", str(kaputt))
        self.assertEqual(erg.returncode, 2, erg.stderr)
        bericht = json.loads(erg.stdout)
        self.assertEqual(bericht["befunde"], [])
        self.assertEqual(len(bericht["fehler"]), 1)


class LexerTeiltDivisionUndRegex(unittest.TestCase):
    """Die `/`-Mehrdeutigkeit – Befund vom 31.10.2026.

    Der Lexer entschied „Regex ab `/`“ mit einer ODER-Kette, in der das
    erste Glied bereits wahr war. Dadurch galt `/` nach `)` IMMER als
    Regex-Start: `Math.round((x / W) * 1000) / 10` verschluckte den Rest
    der Zeile, und die Wache meldete an fremden Dateien einen Lexfehler
    statt eines Befunds. Diese Tests halten beide Richtungen fest, damit
    die Verwechslung nicht zurückkommt – in keiner der beiden.

    WARUM DAS SICHERHEITSRELEVANT IST
    ---------------------------------
    Ein Lexer, der Code falsch zerlegt, prüft die falschen Zeichenketten.
    Wer `https://…` aus einem falsch gelesenen Ausdruck entfernt, sieht
    eine Lücke nicht mehr – und meldet „keine Befunde“.
    """

    def test_division_nach_klammer_bleibt_division(self):
        for probe in ("a = (b) / c;", "x = [1] / 2;", "f(a) / 2",
                      "n = Math.round((x / W) * 1000) / 10;"):
            with self.subTest(probe=probe):
                arten = [t.art for t in wache.js_lexen(probe)]
                self.assertNotIn("regex", arten, probe)

    def test_division_nach_zahl_und_zeichenkette(self):
        for probe in ("a = 4 / 2;", "a = 'x' / 2;"):
            with self.subTest(probe=probe):
                self.assertNotIn("regex", [t.art for t in wache.js_lexen(probe)], probe)

    def test_regex_nach_statement_klammer(self):
        for probe in ("if (a) /x/.test(b);", "while (a) /y/.test(b);"):
            with self.subTest(probe=probe):
                self.assertIn("regex", [t.art for t in wache.js_lexen(probe)], probe)

    def test_regex_nach_schluesselwort(self):
        for probe in ("return /re/;", "typeof /re/;"):
            with self.subTest(probe=probe):
                self.assertIn("regex", [t.art for t in wache.js_lexen(probe)], probe)

    def test_regex_mit_anfuehrungszeichen_in_der_klasse(self):
        # Genau diese Form steht in fremden Analyse-Skripten und war der
        # Auslöser des Fehlbefunds.
        probe = "s.split(',')[0].replace(/[\"']/g, '').trim()"
        arten = [t.art for t in wache.js_lexen(probe)]
        self.assertIn("regex", arten)


class ScopeHatKeineBlindenFlecken(unittest.TestCase):
    """Was eine Analyse nicht liest, hält sie für in Ordnung – Lehre aus #83."""

    def test_typescript_wird_gelesen(self):
        """CodeQLs JS-Extraktor liest .ts/.tsx – diese Wache muss es auch."""
        for endung in (".ts", ".tsx", ".mts", ".cts"):
            self.assertIn(endung, wache.JS_ENDUNGEN)
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            pfad = wurzel / "ziel.ts"
            pfad.write_text(
                "export const treffer = (u: string): boolean =>\n"
                '    u.includes("https://api.resend.com/emails");\n', encoding="utf-8")
            befunde, fehler = wache.pruefe([pfad], wurzel)
            self.assertEqual(fehler, [], f"TypeScript nicht lexbar: {fehler}")
            self.assertTrue(befunde, "TypeScript-Fundstelle wurde nicht erkannt")

    def test_ungelesene_endung_ist_ein_fehler_kein_gruen(self):
        """Der erste .vue-Baustein muss die Wache rot machen, nicht umgehen."""
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            (wurzel / "Komponente.vue").write_text("<template/>\n", encoding="utf-8")
            self.assertEqual(wache.scopeluecken(wurzel), ["Komponente.vue"])

    def test_repository_hat_heute_keine_ungelesene_endung(self):
        erg = _lauf("--json", "--quiet")
        bericht = json.loads(erg.stdout)
        self.assertEqual(
            bericht.get("scopeluecken"), [],
            "Es gibt Dateien, die CodeQL liest und diese Wache nicht – "
            "Leser in scripts/url_substring_guard.py ergänzen, nicht ignorieren.")


class BestandIstFrei(unittest.TestCase):
    """Der Regressionsschutz für den gesamten Quellbestand."""

    def test_repository_ohne_unvollstaendige_url_pruefung(self):
        erg = _lauf("--json", "--quiet")
        try:
            bericht = json.loads(erg.stdout)
        except json.JSONDecodeError as exc:
            self.fail(f"URL-Wache lieferte kein valides JSON ({exc}):\n{erg.stdout}\n{erg.stderr}")
        self.assertEqual(
            bericht.get("fehler"), [],
            "Fail-closed: mindestens eine Datei war nicht analysierbar – ein "
            "unlesbarer Quelltext ist kein grüner Quelltext: "
            f"{bericht.get('fehler')}")
        befunde = bericht.get("befunde", [])
        details = "\n".join(
            f"  {b['datei']}:{b['zeile']} [{b['regel']}] {b['form']} „{b['ziel']}“"
            for b in befunde)
        self.assertEqual(
            befunde, [],
            "URL-Substring-Prüfung oder verbotene Unterdrückung gefunden. "
            "URL parsen und den Host vergleichen (scripts/url_host.py) – "
            "nie unterdrücken:\n" + details)
        self.assertEqual(erg.returncode, 0, erg.stderr)
        self.assertGreater(bericht.get("geprueft", 0), 100,
                           "Dateiauswahl zu klein – die Wache prüft offenbar nicht "
                           "mehr den ganzen Bestand")


class HeilungBleibtBestehen(unittest.TestCase):
    """Die beiden Fundstellen von Alert #83 – inhaltlich festgenagelt."""

    def test_affiliate_marketer_urteilt_host_exakt(self):
        pfad = SCRIPTS / "affiliate_marketer.py"
        code = _py_ohne_kommentare(pfad)
        self.assertNotIn('"https://franksfinanzcheck.de" in t3', code)
        self.assertIn("hat_link_auf_host(t3, BLOG_HOST, mit_subdomains=True)",
                      pfad.read_text(encoding="utf-8"))
        self.assertNotIn("codeql[py/incomplete-url-substring-sanitization]", code)

    def test_governance_contract_prueft_echte_transportstrecke(self):
        pfad = SCRIPTS / "governance_contract.py"
        code = _py_ohne_kommentare(pfad)
        self.assertNotIn('"api.pinterest.com" in text', code)
        self.assertNotIn('"api.pinterest.com" not in text', code)
        self.assertIn("ruft_host_an(text, PINTEREST_API_HOST)",
                      pfad.read_text(encoding="utf-8"))
        self.assertNotIn("codeql[py/incomplete-url-substring-sanitization]", code)

    def test_host_wahrheit_haelt_den_umgehungen_stand(self):
        """Die Umgehungen, die eine Substring-Prüfung durchgelassen hätte."""
        self.assertTrue(url_host.ist_host("https://api.resend.com/emails", "api.resend.com"))
        for umgehung in ("https://api.resend.com.angreifer.example/emails",
                         "https://boese-api.resend.com/emails",
                         "https://angreifer.example/?ziel=api.resend.com",
                         "https://api.resend.com@angreifer.example/"):
            self.assertFalse(url_host.ist_host(umgehung, "api.resend.com"),
                             f"Umgehung akzeptiert: {umgehung}")
        self.assertTrue(url_host.ist_host_oder_subdomain("https://a.pages.dev", "pages.dev"))
        self.assertFalse(url_host.ist_host_oder_subdomain("https://boesepages.dev", "pages.dev"))
        self.assertFalse(url_host.nennt_host("https://fake-api.pinterest.com/v5",
                                             "api.pinterest.com"))
        self.assertFalse(url_host.ruft_host_an('TEXT = "siehe api.pinterest.com"\n',
                                               "api.pinterest.com"))
        self.assertTrue(url_host.ruft_host_an('BASIS = "https://api.pinterest.com/v5"\n',
                                              "api.pinterest.com"))


class BetriebsvertragCI(unittest.TestCase):
    """Was nicht im Lauf steht, passiert nicht."""

    def setUp(self):
        self.workflow = WORKFLOW.read_text(encoding="utf-8")

    def test_keine_regel_ist_mehr_unterdrueckbar(self):
        self.assertNotIn("ERLAUBT=", self.workflow,
                         "Die Unterdrückungs-Whitelist ist zurück – genau sie hat "
                         "Alert #83 sechs Tage lang unsichtbar gemacht.")
        self.assertIn("Unterdrückungen sind selbst ein Befund", self.workflow)

    def test_url_wache_laeuft_als_eigener_job(self):
        self.assertIn("url-wache:", self.workflow)
        for aufruf in ("python3 scripts/url_substring_guard.py --selftest",
                       "python3 scripts/url_substring_guard.py",
                       "python3 -m unittest scripts.tests.test_url_substring_security",
                       "node --test cloudflare/ki-assistent/test/worker.test.mjs"):
            self.assertIn(aufruf, self.workflow, f"CI ruft `{aufruf}` nicht auf")

    def test_beide_regeln_bleiben_sicherheitsrelevant(self):
        for regel in (wache.REGEL_PY, wache.REGEL_JS):
            self.assertIn(regel, self.workflow,
                          f"{regel} fehlt in der Security-Severity-Liste des Gates")


class WorkerHerkunftIstHostGenau(unittest.TestCase):
    """CORS des KI-Assistenten: Host-Urteil statt Zeichenketten-Ende."""

    def test_worker_prueft_den_host(self):
        roh = WORKER.read_text(encoding="utf-8")
        code = _js_ohne_kommentare(WORKER)
        self.assertIn("function vorschauHost(", roh)
        self.assertRegex(code, r"new\s+URL\s*\(")
        self.assertNotRegex(
            code, r"origin\s*\.\s*(endsWith|startsWith|includes|indexOf)\s*\(",
            "Die Herkunft wird wieder über eine Zeichenkette beurteilt (Alert #83)")

    def test_gate_bewacht_den_worker(self):
        gate = (SCRIPTS / "ki_assistent_gate.py").read_text(encoding="utf-8")
        self.assertIn("def pruefe_ka10(", gate)
        self.assertIn("CORS_ZEICHENKETTE", gate)
        erg = subprocess.run([sys.executable, str(SCRIPTS / "ki_assistent_gate.py"), "--selftest"],
                             capture_output=True, text=True, cwd=str(ROOT), timeout=120,
                             check=False)
        self.assertEqual(erg.returncode, 0, erg.stdout + erg.stderr)
        self.assertIn("KA10 erkennt Zeichenketten-Prüfung der Herkunft", erg.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
