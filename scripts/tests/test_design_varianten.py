"""Regressionstests für die Design-Varianten-Werkbank (26.09.2026).

Warum diese Tests existieren
---------------------------
Die Werkbank erlaubt einer KI, Layoutvarianten zu bauen und zu messen.
Ihr einziger Wert liegt in den Regeln, die verhindern, dass daraus ein
eigenmächtiger Designwechsel wird. Diese Regeln sind Code – und Code
fällt still zurück. Die Tests halten die vier Zusagen fest, auf denen
alles andere steht:

1) **Ohne Unterschrift kein Live.** Ein Register-Eintrag mit Status
   `freigegeben`/`live`, aber ohne menschliche Freigabe, muss einen
   P1-Befund erzeugen – nicht eine Warnung, die man wegklickt.
2) **Ohne Messung keine Freigabe.** Tier A, Tier B und Lighthouse sind
   Pflicht. Fehlt eine Ebene, ist die Freigabe ungültig.
3) **Bestand ≠ Regression.** Reißt schon die Basis ein Budget, darf
   die Variante dafür nicht angeklagt werden (Fehlalarm-Klasse aus
   Vorfall #343).
4) **Die Produktionswache greift.** Eine in hugo.toml aktivierte, aber
   nicht freigegebene Variante ist ein P1-Fund.

Zusätzlich: Das ausgelieferte Repository selbst muss den Regeln
genügen (Regelwerk-Schema, Register, Varianten-CSS, Hugo-Schalter).

Alle Tests laufen ohne Netz, ohne Hugo und ohne Browser.
"""
import datetime as dt
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import design_variant_gate as gate       # noqa: E402
import design_variant_lab as lab         # noqa: E402
import design_reach_briefing as briefing  # noqa: E402


def register(**kw):
    """Minimales, gültiges Register – Abweichungen je Test gezielt gesetzt."""
    variante = {
        "id": "v-test",
        "titel": "Test",
        "hypothese": "H" * 120,
        "oberflaeche": ["/"],
        "herkunft": "KI",
        "status": "entwurf",
        "css": "",
        "freigabe": {"mensch": False, "name": "", "datum": "", "kommentar": ""},
    }
    variante.update(kw)
    return {
        "aktiv": "",
        "varianten": [
            {"id": "basis", "titel": "Basis", "hypothese": "-",
             "oberflaeche": ["/"], "herkunft": "Bestand", "status": "live",
             "css": "", "freigabe": {"mensch": True, "name": "Frank Hartung",
                                     "datum": "2026-09-01", "kommentar": "ok"}},
            variante,
        ],
    }


REGELWERK = {
    "marke": {},
    "freigabe": {
        "erlaubte_status": ["entwurf", "gemessen", "freigegeben", "live", "verworfen"],
        "berechtigte": ["Frank Hartung"],
        "pflichtfelder": ["mensch", "name", "datum", "kommentar"],
        "messung_pflicht": ["statisch", "gerendert", "lighthouse"],
        "gueltigkeit_tage": 30,
    },
}
HEUTE = dt.date(2026, 9, 26)


class FreigabeKontrakt(unittest.TestCase):
    """Zusage 1 + 2: keine Freigabe ohne Unterschrift und ohne Messung."""

    def test_status_live_ohne_unterschrift_ist_P1(self):
        b = gate.Bericht()
        gate.pruefe_register(register(status="live"), REGELWERK, b, HEUTE, None)
        treffer = [x for x in b.befunde if x.regel == "freigabe.mensch"]
        self.assertTrue(treffer, "Live ohne Unterschrift muss auffallen")
        self.assertEqual(treffer[0].schwere, "P1")
        self.assertEqual(treffer[0].besitzer, "human")

    def test_unterschrift_ohne_messung_ist_P1(self):
        with tempfile.TemporaryDirectory() as tmp:
            original, gate.MESSUNGEN = gate.MESSUNGEN, Path(tmp)
            try:
                b = gate.Bericht()
                gate.pruefe_register(
                    register(status="freigegeben",
                             freigabe={"mensch": True, "name": "Frank Hartung",
                                       "datum": "2026-09-26", "kommentar": "ok"}),
                    REGELWERK, b, HEUTE, None)
            finally:
                gate.MESSUNGEN = original
        fehlend = {x.text.split("`")[1] for x in b.befunde
                   if x.regel == "freigabe.messung"}
        self.assertEqual(fehlend, {"statisch", "gerendert", "lighthouse"})
        self.assertTrue(all(x.schwere == "P1" for x in b.befunde
                            if x.regel == "freigabe.messung"))

    def test_teilmessung_reicht_nicht(self):
        """Tier A allein sieht keine Farbe – Freigabe bleibt blockiert."""
        with tempfile.TemporaryDirectory() as tmp:
            original, gate.MESSUNGEN = gate.MESSUNGEN, Path(tmp)
            try:
                ziel = Path(tmp) / "v-test"
                ziel.mkdir()
                (ziel / "messung.json").write_text(json.dumps({
                    "tiers": {"statisch": {"status": "ok", "werte": {}},
                              "gerendert": {"status": "nicht_verfuegbar"},
                              "lighthouse": {"status": "nicht_verfuegbar"}}
                }), encoding="utf-8")
                b = gate.Bericht()
                gate.pruefe_register(
                    register(status="freigegeben",
                             freigabe={"mensch": True, "name": "Frank Hartung",
                                       "datum": "2026-09-26", "kommentar": "ok"}),
                    REGELWERK, b, HEUTE, None)
            finally:
                gate.MESSUNGEN = original
        fehlend = {x.text.split("`")[1] for x in b.befunde
                   if x.regel == "freigabe.messung"}
        self.assertEqual(fehlend, {"gerendert", "lighthouse"})

    def test_unbekannter_unterzeichner_ist_P1(self):
        b = gate.Bericht()
        gate.pruefe_register(
            register(status="live",
                     freigabe={"mensch": True, "name": "Fremde Person",
                               "datum": "2026-09-26", "kommentar": "ok"}),
            REGELWERK, b, HEUTE, None)
        self.assertTrue(any(x.regel == "freigabe.berechtigte" and x.schwere == "P1"
                            for x in b.befunde))

    def test_verfallene_freigabe_wird_gemeldet(self):
        b = gate.Bericht()
        gate.pruefe_register(
            register(status="freigegeben",
                     freigabe={"mensch": True, "name": "Frank Hartung",
                               "datum": "2026-06-01", "kommentar": "ok"}),
            REGELWERK, b, HEUTE, None)
        self.assertTrue(any(x.regel == "freigabe.verfall" for x in b.befunde))

    def test_freigabedatum_in_der_zukunft_ist_P1(self):
        b = gate.Bericht()
        gate.pruefe_register(
            register(status="live",
                     freigabe={"mensch": True, "name": "Frank Hartung",
                               "datum": "2027-01-01", "kommentar": "ok"}),
            REGELWERK, b, HEUTE, None)
        self.assertTrue(any(x.regel == "freigabe.datum" and x.schwere == "P1"
                            for x in b.befunde))

    def test_zwei_live_varianten_sind_P1(self):
        reg = register(status="live",
                       freigabe={"mensch": True, "name": "Frank Hartung",
                                 "datum": "2026-09-26", "kommentar": "ok"})
        reg["varianten"].append({
            "id": "v-zwei", "titel": "Zwei", "hypothese": "H" * 120,
            "oberflaeche": ["/"], "herkunft": "KI", "status": "live", "css": "",
            "freigabe": {"mensch": True, "name": "Frank Hartung",
                         "datum": "2026-09-26", "kommentar": "ok"}})
        reg["aktiv"] = "v-test"
        b = gate.Bericht()
        gate.pruefe_register(reg, REGELWERK, b, HEUTE, None)
        self.assertTrue(any(x.regel == "register.aktiv" and x.schwere == "P1"
                            for x in b.befunde))


class Messprotokoll(unittest.TestCase):
    """Eine Freigabe muss auf einen DAUERHAFTEN Beleg zeigen.

    Messungen entstehen in .cache/ – gitignored und flüchtig (im
    Arbeitsumfeld am 26.09.2026 zweimal zwischen zwei Sitzungen
    verschwunden). Läge der Beleg nur dort, wäre jede unterschriebene
    Variante nach einem frischen Checkout „freigegeben ohne Messung":
    ein P1 in jedem CI-Lauf, den niemand verursacht hat und niemand
    beheben kann.
    """

    AKTE = {"mensch": True, "name": "Frank Hartung", "datum": "2026-09-26",
            "kommentar": "ok",
            "messprotokoll": "design/messungen/v-test-2026-09-26.json"}

    def _protokoll(self, tmp: str, variante: str = "v-test", tiers=None):
        ziel = Path(tmp) / "design" / "messungen"
        ziel.mkdir(parents=True)
        (ziel / "v-test-2026-09-26.json").write_text(json.dumps({
            "variante": variante,
            "erstellt": "2026-09-26T10:00:00Z",
            "tiers": tiers or {t: {"status": "ok", "werte": {}}
                               for t in ("statisch", "gerendert", "lighthouse")},
        }), encoding="utf-8")
        return Path(tmp)

    def test_protokoll_ersetzt_den_fluechtigen_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig_p, orig_m = gate.PROTOKOLLE, gate.MESSUNGEN
            gate.PROTOKOLLE = self._protokoll(tmp)
            gate.MESSUNGEN = Path(tmp) / "kein-cache"
            try:
                for tier in ("statisch", "gerendert", "lighthouse"):
                    self.assertTrue(
                        gate.messung_vorhanden("v-test", tier, self.AKTE),
                        f"{tier} müsste aus dem Protokoll kommen")
            finally:
                gate.PROTOKOLLE, gate.MESSUNGEN = orig_p, orig_m

    def test_protokoll_einer_anderen_variante_zaehlt_nicht(self):
        with tempfile.TemporaryDirectory() as tmp:
            orig_p, orig_m = gate.PROTOKOLLE, gate.MESSUNGEN
            gate.PROTOKOLLE = self._protokoll(tmp, variante="v-andere")
            gate.MESSUNGEN = Path(tmp) / "kein-cache"
            try:
                self.assertFalse(
                    gate.messung_vorhanden("v-test", "statisch", self.AKTE))
            finally:
                gate.PROTOKOLLE, gate.MESSUNGEN = orig_p, orig_m

    def test_halbes_protokoll_reicht_nicht(self):
        tiers = {"statisch": {"status": "ok"},
                 "gerendert": {"status": "nicht_verfuegbar"},
                 "lighthouse": {"status": "nicht_verfuegbar"}}
        with tempfile.TemporaryDirectory() as tmp:
            orig_p, orig_m = gate.PROTOKOLLE, gate.MESSUNGEN
            gate.PROTOKOLLE = self._protokoll(tmp, tiers=tiers)
            gate.MESSUNGEN = Path(tmp) / "kein-cache"
            try:
                self.assertTrue(gate.messung_vorhanden("v-test", "statisch", self.AKTE))
                self.assertFalse(gate.messung_vorhanden("v-test", "gerendert", self.AKTE))
            finally:
                gate.PROTOKOLLE, gate.MESSUNGEN = orig_p, orig_m

    def test_verwaister_verweis_ist_P1(self):
        reg = register(status="freigegeben",
                       freigabe=dict(self.AKTE,
                                     messprotokoll="design/messungen/gibt-es-nicht.json"))
        b = gate.Bericht()
        gate.pruefe_register(reg, REGELWERK, b, HEUTE, None)
        treffer = [x for x in b.befunde if x.regel == "freigabe.messprotokoll"]
        self.assertTrue(treffer)
        self.assertEqual(treffer[0].schwere, "P1")


class BestandGegenRegression(unittest.TestCase):
    """Zusage 3: Vorfall #343 darf sich nicht wiederholen."""

    def test_bestandswert_wird_der_variante_nicht_angelastet(self):
        b = gate.Bericht()
        gate._budget(b, "v", "performance.dom_kinder_max", 58, 54, "max",
                     basis_wert=58)
        self.assertEqual(b.befunde, [])

    def test_verbesserung_gegenueber_bestand_ist_kein_befund(self):
        b = gate.Bericht()
        gate._budget(b, "v", "performance.dom_kinder_max", 55, 54, "max",
                     basis_wert=58)
        self.assertEqual(b.befunde, [])

    def test_verschaerfung_eines_bestandsbefunds_wird_gemeldet(self):
        b = gate.Bericht()
        gate._budget(b, "v", "performance.dom_kinder_max", 62, 54, "max",
                     basis_wert=58)
        self.assertEqual(len(b.befunde), 1)
        self.assertIn("verschärft", b.befunde[0].text)

    def test_echte_regression_wird_gemeldet(self):
        b = gate.Bericht()
        gate._budget(b, "v", "performance.dom_kinder_max", 55, 54, "max",
                     basis_wert=50)
        self.assertEqual(len(b.befunde), 1)
        self.assertIn("im Budget", b.befunde[0].text)

    def test_bestandsbefund_blockiert_nicht(self):
        """P3 heißt: sichtbar, aber es hält keine Variante auf."""
        b = gate.Bericht()
        b.melde(regel="bestand.x", variante="basis", schwere="P3",
                besitzer="human", text="x")
        self.assertEqual(b.blockierend, [])


class Produktionswache(unittest.TestCase):
    """Zusage 4: Was in hugo.toml steht, muss erlaubt sein."""

    def _hugo_toml(self, tmp: str, wert: str | None) -> Path:
        pfad = Path(tmp) / "hugo.toml"
        inhalt = '[params]\n  title = "x"\n'
        if wert is not None:
            inhalt += f'  designVariante = "{wert}"\n'
        pfad.write_text(inhalt, encoding="utf-8")
        return pfad

    def test_leerer_parameter_ist_die_basis(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                gate.hugo_param_variante(self._hugo_toml(tmp, None)), "")

    def test_parameter_wird_gelesen(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                gate.hugo_param_variante(self._hugo_toml(tmp, "v-test")), "v-test")

    def test_unfreigegebene_variante_in_hugo_toml_ist_P1(self):
        with tempfile.TemporaryDirectory() as tmp:
            original, gate.HUGO_TOML = gate.HUGO_TOML, self._hugo_toml(tmp, "v-test")
            try:
                b = gate.Bericht()
                gate.produktionswache(register(), b)
            finally:
                gate.HUGO_TOML = original
        regeln = {x.regel for x in b.befunde}
        self.assertIn("produktionswache.status", regeln)
        self.assertIn("produktionswache.freigabe", regeln)
        self.assertTrue(all(x.schwere == "P1" for x in b.befunde))

    def test_drift_zwischen_hugo_toml_und_register_ist_P1(self):
        with tempfile.TemporaryDirectory() as tmp:
            original, gate.HUGO_TOML = gate.HUGO_TOML, self._hugo_toml(tmp, "v-test")
            try:
                b = gate.Bericht()
                gate.produktionswache(register(), b)   # aktiv: "" im Register
            finally:
                gate.HUGO_TOML = original
        self.assertTrue(any(x.regel == "produktionswache.drift" for x in b.befunde))


class MarkenAudit(unittest.TestCase):
    """Das CSS-Gate darf weder blind noch überempfindlich sein."""

    MARKE = {
        "farben_erlaubt": ["#0E5A43", "#FFB300"],
        "variablen_praefixe_erlaubt": ["--ff-"],
        "rgba_basen_erlaubt": [[0, 0, 0]],
        "radien_px_erlaubt": [8, 12, 16, 999],
        "uebergang_dauer_s_erlaubt": [0.16, 0.3],
        "easing_erlaubt": ["ease-out"],
        "css_budget_bytes": 2048,
        "verbote": {"wichtig": {"muster": "!important", "begruendung": "x"}},
        "pflichten": {},
    }

    def test_kommentare_werden_nicht_angeklagt(self):
        b = gate.Bericht()
        gate.pruefe_css("v", "/* niemals !important und nie #ABCDEF */\n.a{opacity:1}",
                        self.MARKE, b)
        self.assertEqual(b.befunde, [])

    def test_fremdfarbe_faellt_auf(self):
        b = gate.Bericht()
        gate.pruefe_css("v", ".a{color:#ABCDEF}", self.MARKE, b)
        self.assertTrue(any(x.regel == "marke.farben_erlaubt" for x in b.befunde))

    def test_kurzform_hex_wird_normalisiert(self):
        marke = dict(self.MARKE, farben_erlaubt=["#333"])
        b = gate.Bericht()
        gate.pruefe_css("v", ".a{color:#333333}", marke, b)
        self.assertEqual(b.befunde, [])

    def test_css_budget_greift(self):
        b = gate.Bericht()
        gate.pruefe_css("v", ".a{opacity:1}" + " " * 3000, self.MARKE, b)
        self.assertTrue(any(x.regel == "marke.css_budget_bytes" for x in b.befunde))

    def test_regel_ohne_muster_ist_selbst_ein_befund(self):
        """Eine Regel, die nichts prüft, darf nicht still grün sein."""
        marke = dict(self.MARKE, verbote={"leer": {"begruendung": "x"}})
        b = gate.Bericht()
        gate.pruefe_css("v", ".a{opacity:1}", marke, b)
        self.assertTrue(any(x.regel == "marke.verbote.leer" for x in b.befunde))


class RepositoryZustand(unittest.TestCase):
    """Das ausgelieferte Repository muss seinen eigenen Regeln genügen."""

    def test_regelwerk_entspricht_dem_schema(self):
        rw = gate.lade_yaml(gate.REGELWERK, "Regelwerk")
        self.assertEqual(gate.pruefe_regelwerk_schema(rw), [])

    def test_register_und_marken_audit_sind_sauber(self):
        rw = gate.lade_yaml(gate.REGELWERK, "Regelwerk")
        reg = gate.lade_yaml(gate.REGISTER, "Register")
        b = gate.Bericht()
        gate.pruefe_register(reg, rw, b, dt.date.today(), None)
        blockierend = [x.zeile() for x in b.blockierend]
        self.assertEqual(blockierend, [], "\n".join(blockierend))

    def test_lighthouse_export_passt_zum_regelwerk(self):
        rw = gate.lade_yaml(gate.REGELWERK, "Regelwerk")
        b = gate.Bericht()
        gate.pruefe_lighthouse_export(rw, b)
        self.assertEqual([x.zeile() for x in b.befunde], [])

    def test_jede_registrierte_css_datei_existiert(self):
        reg = gate.lade_yaml(gate.REGISTER, "Register")
        for eintrag in reg["varianten"]:
            pfad = (eintrag.get("css") or "").strip()
            if pfad:
                self.assertTrue((ROOT / "assets" / pfad).exists(),
                                f"{eintrag['id']}: assets/{pfad} fehlt")

    def test_hugo_schalter_ist_verdrahtet(self):
        """Ohne den Aufruf in extend_head.html wäre die Werkbank wirkungslos."""
        head = (ROOT / "layouts" / "_partials" / "extend_head.html").read_text(
            encoding="utf-8")
        self.assertIn("design_variante.html", head)
        self.assertIn("partialCached", head)

    def test_variantenschalter_liest_register_ohne_site_data(self):
        """site.Data würde den ganzen data/-Baum parsen und den Build töten."""
        partial = (ROOT / "layouts" / "_partials" / "design_variante.html").read_text(
            encoding="utf-8")
        self.assertNotIn("site.Data", partial.replace("site.Data/", ""))
        self.assertIn("design_varianten_data.html", partial)

    def test_jede_freigabe_hat_ein_vorhandenes_protokoll(self):
        """Der Beleg jeder unterschriebenen Variante liegt im Repo."""
        reg = gate.lade_yaml(gate.REGISTER, "Register")
        for eintrag in reg["varianten"]:
            if eintrag["id"] == "basis":
                continue
            akte = eintrag.get("freigabe") or {}
            if str(eintrag.get("status")) not in ("freigegeben", "live"):
                continue
            with self.subTest(variante=eintrag["id"]):
                verweis = str(akte.get("messprotokoll") or "").strip()
                self.assertTrue(verweis, "Freigabe ohne Messprotokoll.")
                datei = ROOT / "data" / verweis
                self.assertTrue(datei.exists(), f"data/{verweis} fehlt.")
                protokoll = json.loads(datei.read_text(encoding="utf-8"))
                self.assertEqual(protokoll["variante"], eintrag["id"])
                for tier in ("statisch", "gerendert", "lighthouse"):
                    self.assertEqual(
                        protokoll["tiers"][tier]["status"], "ok",
                        f"{tier} im Protokoll nicht grün.")

    def test_produktion_aktiviert_keine_variante(self):
        self.assertEqual(gate.hugo_param_variante(), "",
                         "hugo.toml aktiviert eine Design-Variante – nur nach "
                         "Freigabe zulässig (siehe Runbook).")

    def test_selbsttests_der_werkzeuge_laufen(self):
        for skript in ("design_variant_gate.py", "design_variant_lab.py",
                       "design_reach_briefing.py"):
            with self.subTest(skript=skript):
                r = subprocess.run(
                    [sys.executable, str(ROOT / "scripts" / skript), "--selftest"],
                    capture_output=True, text=True, timeout=120)
                self.assertEqual(r.returncode, 0,
                                 f"{skript}: {r.stdout}\n{r.stderr}")


class WerkbankMessung(unittest.TestCase):
    """Tier A muss zählen, was zählt – und die Messkette schützen."""

    def test_affiliate_ohne_noopener_faellt_auf(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp) / "public"
            public.mkdir()
            (public / "index.html").write_text(
                '<html><head><link rel="canonical" href="/"></head><body><h1>x</h1>'
                '<a href="/go/strom/" rel="sponsored nofollow">P</a></body></html>',
                encoding="utf-8")
            m = lab.messen_statisch("v", public, {})
        self.assertEqual(m["werte"]["affiliate_rel_fehler"], 1)

    def test_cta_ohne_umami_faellt_auf(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp) / "public"
            public.mkdir()
            (public / "index.html").write_text(
                '<html><body><a class="ff-btn ff-btn-primary" href="/a/">A</a>'
                '</body></html>', encoding="utf-8")
            m = lab.messen_statisch("v", public, {})
        self.assertEqual(m["werte"]["cta_ohne_umami"], 1)

    def test_fehlende_variantenmarke_wird_erkannt(self):
        """Sonst vermisst man die Basis und hält sie für die Variante."""
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp) / "public"
            public.mkdir()
            (public / "index.html").write_text("<html><body>x</body></html>",
                                               encoding="utf-8")
            m = lab.messen_statisch("v", public, {})
        self.assertFalse(m["werte"]["variante_im_markup"])


class BriefingRaster(unittest.TestCase):
    """Falsche Belege sind schlimmer als keine."""

    RASTER = [{"thema": "A11y", "oberflaeche": "alle", "id_vorschlag": "v-a11y-*",
               "signale": ["aria"], "pruefen_mit": ["x"]}]

    def test_teilwort_loest_nicht_aus(self):
        z = briefing.ordne_zu(
            [{"kanal": "github", "quelle": "q", "datum": "",
              "titel": "design-tokens-css-variables", "url": "u"}], self.RASTER)
        self.assertEqual(z["A11y"], [])

    def test_ganzes_wort_loest_aus(self):
        z = briefing.ordne_zu(
            [{"kanal": "rss", "quelle": "q", "datum": "",
              "titel": "Using ARIA landmarks", "url": "u"}], self.RASTER)
        self.assertEqual(len(z["A11y"]), 1)

    def test_jedes_thema_nennt_seine_pruefregeln(self):
        plan = briefing._yaml().safe_load(
            briefing.PLAN.read_text(encoding="utf-8")) or {}
        for thema in plan.get("hypothesen_raster") or []:
            with self.subTest(thema=thema.get("thema")):
                self.assertTrue(thema.get("pruefen_mit"),
                                "Ein Vorschlag ohne Messregel ist eine Meinung.")


if __name__ == "__main__":
    unittest.main()
