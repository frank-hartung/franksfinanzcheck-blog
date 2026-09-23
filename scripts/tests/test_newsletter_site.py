#!/usr/bin/env python3
"""Regressionstest: die Hugo-Seite des Newsletters (Formular, Streifen, Journeys).

Das Studio baut Mails, dieses Set prüft den Teil, den Leser sehen: Shortcodes,
Partial, CSS, das eine JS und die drei Journey-Seiten. Ohne Hugo-Build ist das
kein Render-Test, sondern ein Verdrahtungs-Test – und gerade der fängt die
Fehlerarten, die dieses Repo kennen: eine Klasse ohne Regel (unsichtbares
Markup), ein Hook, den das JS liest, den aber kein Template setzt, ein Link auf
eine Seite, die es nicht gibt, und ein Versprechen, das der Leerzustand gar
nicht halten kann.

Bewusst ohne `public/-Ausgabe`: ein Test, der einen Build voraussetzt, wird im
Alltag übersprungen. Was hier steht, gilt auch ohne Hugo-Binary.
"""
from __future__ import annotations

import datetime
import glob
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPTS = os.path.join(ROOT, "scripts")

FORM = "layouts/shortcodes/newsletter_form.html"
STATUS = "layouts/shortcodes/newsletter_status.html"
WEG = "layouts/shortcodes/newsletter_weg.html"
THEMEN = "layouts/shortcodes/newsletter_themen.html"
MUSTER = "layouts/shortcodes/newsletter_muster.html"
STRIP = "layouts/_partials/newsletter_strip.html"
DATEN = "layouts/_partials/newsletter_studio_data.html"
PLAN = "layouts/_partials/newsletter_versandplan.html"
KADENZ = "data/newsletter_kadenz.json"
NEUE = [FORM, STATUS, WEG, THEMEN, MUSTER, STRIP, DATEN, PLAN]
CSS = "assets/css/extended/zz-newsletter.css"
JS = "static/premium/ff-newsletter.js"
JOURNEYS = ["content/newsletter/index.md", "content/newsletter-bestaetigung/index.md",
            "content/newsletter-praeferenzen/index.md", "content/newsletter-abmelden/index.md"]


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


studio = _load("newsletter_studio", os.path.join(SCRIPTS, "newsletter_studio.py"))
# Normaler Import: der Versandvertrag muss dieselbe Modulinstanz sein, die auch
# newsletter_digest hält – sonst laufen Zeit-Patches anderer Tests ins Leere.
sys.path.insert(0, SCRIPTS)
import newsletter_schedule as plan                        # noqa: E402
qa_modul = _load("newsletter_qa", os.path.join(SCRIPTS, "newsletter_qa.py"))
qa_pruefe = qa_modul.pruefe


def _text(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def _ohne_kommentare(t: str) -> str:
    t = re.sub(r"\{\{-?\s*/\*.*?\*/\s*-?\}\}", " ", t, flags=re.S)
    return re.sub(r"\{\{/\*.*?\*/\}\}", " ", t, flags=re.S)


def _klammern(t: str) -> int:
    tiefe = 0
    for m in re.finditer(r"\{\{-?\s*(if|range|with|block|define|end)\b", _ohne_kommentare(t)):
        tiefe += 1 if m.group(1) != "end" else -1
    return tiefe


class Vorlagen(unittest.TestCase):
    def test_alle_bloecke_sind_geschlossen(self):
        for rel in NEUE + ["layouts/single.html", "layouts/_default/single.html",
                          "layouts/_partials/footer.html"]:
            self.assertEqual(0, _klammern(_text(rel)), f"{rel}: {{ if }} ohne {{ end }}")

    def test_kein_site_data_zugriff(self):
        """Ein einziges `site.Data` zwingt Hugo, data/audit/*.jsonl zu parsen –
        der Build stirbt an einer Datei, die mit dem Newsletter nichts zu tun hat."""
        for rel in NEUE:
            t = _ohne_kommentare(_text(rel))
            self.assertNotRegex(t, r"\bsite\.Data\b|\bhugo\.Data\b",
                                f"{rel} muss Daten über os.ReadFile laden")

    def test_keine_harte_farbe_im_markup(self):
        for rel in NEUE + JOURNEYS:
            self.assertNotRegex(_text(rel), r"#\d[0-9A-Fa-f]{5}\b",
                                f"{rel} setzt eine Farbe im Template – Token in der CSS-Schicht")

    def test_jedes_partial_und_jeder_shortcode_existiert(self):
        for rel in NEUE + JOURNEYS:
            t = _text(rel)
            for m in re.finditer(r'partial(?:Cached)?\s+"([^"]+)"', t):
                ziel = m.group(1)
                pfade = [os.path.join(ROOT, "layouts/_partials", ziel),
                         os.path.join(ROOT, "themes/PaperMod/layouts/_partials", ziel)]
                self.assertTrue(any(os.path.exists(p) for p in pfade),
                                f"{rel} ruft fehlendes Partial {ziel}")
            for m in re.finditer(r"\{\{<\s*([a-zA-Z0-9_-]+)", t):
                self.assertTrue(os.path.exists(
                    os.path.join(ROOT, "layouts/shortcodes", m.group(1) + ".html")),
                    f"{rel} ruft fehlenden Shortcode {m.group(1)}")

    def test_js_haenges_sind_im_formular_da(self):
        """Was das Skript liest, muss das Template auch setzen – sonst ist die
        Bot-Falle ein Kommentar und die Zeitfalle ein leeres Feld.

        Geprüft wird gegen Formular UND Versandplan: Der Baustein steht vor dem
        <form> und trägt die Haken für die Terminrechnung (`data-ff-nl-plan`,
        `-tage`, `-uhrzeit`, `-tag`, `-tag-kurz`, `-termin`, `-erster`)."""
        js = _text(JS)
        template = _text(FORM) + _text(PLAN)
        for hook in set(re.findall(r"data-ff-nl[-a-zäöü]*", js)):
            self.assertIn(hook, template, f"{hook} wird im JS gelesen, ist aber nirgends im Formular")
        self.assertIn('id="ff-nl-status"', template)
        self.assertIn("role=\"status\"", template, "Meldungen müssen einem Screenreader gemeldet werden")

    def test_formular_ohne_js_und_mit_js_gleich(self):
        template = _text(FORM)
        self.assertIn('method="post"', template)
        self.assertRegex(template, r'<button[^>]+type="submit"')
        # Kein Anbieter wird ins Template zementiert – der Weg kommt aus der Konfig.
        self.assertNotRegex(template, r"https?://[a-z0-9.-]*(brevo|sendinblue)",
                            "Anbieter-URL im Shortcode – der Schalter gehört in data/")
        self.assertIn("capture.form_action", template.replace(" ", "").replace(
            "$nl.capture.form_action", "capture.form_action"))

    def test_der_leerzustand_wirbt_nicht(self):
        template = _text(FORM)
        self.assertIn("nicht geschaltet", template,
                      "ohne Anmeldeweg muss das Formular das sagen, statt zu schweigen")
        self.assertIn("consent", template)
        self.assertRegex(template, r'name="consent"[^>]*required|required[^>]*name="consent"')

    def test_status_kurz_und_ohne_erfindnis(self):
        t = _text(STATUS)
        self.assertIn("nicht geschaltet", t)
        self.assertIn("Double-Opt", t)
        self.assertNotIn("https://", _ohne_kommentare(t),
                         "die Statusmeldung erfindet keinen Anbieter-Link")


class Aussehen(unittest.TestCase):
    def test_jede_klasse_hat_eine_regel(self):
        benutzt = set()
        for rel in [FORM, STATUS, WEG, THEMEN, MUSTER, STRIP, PLAN]:
            benutzt |= set(re.findall(r'class="([^"]+)"', _ohne_kommentare(_text(rel))))
        flach = {k.strip() for gruppe in benutzt for k in gruppe.split()
                 if (k.startswith("ff-nl") or k.startswith("newsletter-footer"))
                 and "{{" not in k and "}}" not in k}
        css = _text(CSS)
        fehlend = sorted(k for k in flach if k not in css)
        self.assertEqual([], fehlend,
                         "gerenderte Klassen ohne Regel – unsichtbares Markup: "
                         + ", ".join("." + k for k in fehlend))

    def test_drei_breiten_und_politur_uebersteht(self):
        css, polier = _text(CSS), _text("assets/css/extended/zzz-agency-polish.css")
        self.assertLess(os.path.basename(CSS), os.path.basename(
            "assets/css/extended/zzz-agency-polish.css"),
            "extended/-Dateien werden alphabetisch geladen – danach verliert alles")
        # extend_footer (versiegelt) und die Politur kennen .newsletter-footer;
        # gleiches Recht gewinnt, wer spezifischer schreibt.
        for klassen in re.findall(r"^\.newsletter-footer[a-z0-9_.-]*", polier, flags=re.M):
            token = klassen.strip(".").split(".")
            if len(token) > 1 and token[1] in css:
                self.assertRegex(css, r"\.newsletter-footer\.ff-nl-strip",
                                 f"{klassen} in der Politur – ohne zusammengesetzten "
                                 "Selektor verliert der Streifen")

    def test_dark_mode_und_tokens(self):
        css = _text(CSS)
        self.assertGreaterEqual(len(re.findall(r'data-theme="dark"', css)), 8,
                                "jede Farbe braucht eine Dunkel-Variante (DESIGN.md §8)")
        for token in ("--ff-nl-fehler", "--ff-nl-erfolg"):
            self.assertEqual(2, len(re.findall(re.escape(token) + r"\s*:", css)),
                             f"{token} muss in hell UND dunkel definiert sein")
        self.assertNotRegex(css, r"transition:\s*(?!none)(?!(transform|opacity|color)\b)[a-z-]+",
                            "DESIGN.md §7: Übergänge nur auf transform/opacity/color")

    def test_bilder_haben_breite_und_hoehe(self):
        for rel in [FORM, STATUS, WEG, THEMEN, MUSTER, STRIP]:
            for img in re.findall(r"<img[^>]*>", _ohne_kommentare(_text(rel))):
                self.assertIn("width", img, f"{rel}: <img> ohne width → Layout-Sprung")
                self.assertIn("height", img, f"{rel}: <img> ohne height → Layout-Sprung")


class Skript(unittest.TestCase):
    def test_first_party_und_kein_tracking(self):
        js = _text(JS)
        self.assertEqual([], re.findall(r"https?://", js),
                         "das Anmelde-Skript darf keine dritte Domain laden")
        for gefahr in ("eval(", "document.write", "localStorage.setItem('", "innerHTML"):
            if gefahr == "localStorage.setItem('":
                self.assertIn("localStorage.setItem", js, "der Angemeldet-Merker ist Absicht")
                continue
            self.assertNotIn(gefahr, js, f"{gefahr} gehört nicht in ein Anmelde-Skript")

    def test_kein_erfolgsversprechen(self):
        js = _text(JS)
        self.assertNotRegex(js, r"(erfolgreich (abonniert|angemeldet))",
                            "ein no-cors-Fetch weiß nichts über den Erfolg – "
                            "die Meldung darf nur den ausgelösten Mailversand behaupten")

    def test_syntax_wenn_node_da_ist(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("kein node im Prüf-Container")
        rc = subprocess.run([node, "--check", os.path.join(ROOT, JS)],
                            capture_output=True, text=True)
        self.assertEqual(0, rc.returncode, rc.stdout + rc.stderr)


class Streifen(unittest.TestCase):
    def test_nur_bei_konfiguriertem_weg_und_nicht_auf_sich_selbst(self):
        strip = _text(STRIP)
        for pfad in ('"/newsletter"', '"/impressum"', '"/datenschutz"'):
            self.assertIn(pfad, strip, f"kein CTA auf {pfad}")
        self.assertIn("$nl.aktiv", strip, "ohne Anmeldeweg darf kein Kasten stehen")

    def test_doppel_cta_wird_verhindert(self):
        self.assertNotIn('<div class="newsletter-footer">', _text("layouts/_partials/extend_footer.html"))
        self.assertNotIn('partial "newsletter_strip.html"', _text("layouts/_default/single.html"))

    def test_blog_streifen_steht_vor_dem_hauptinhalt(self):
        base = _text("layouts/baseof.html")
        self.assertLess(base.index('partial "header.html"') if 'partial "header.html"' in base
                        else base.index('partialCached "header.html"'), base.index('partial "newsletter_strip.html"'))
        self.assertLess(base.index('partial "newsletter_strip.html"'), base.index('<main'))

    def test_genau_ein_streifen_pro_artikelseite(self):
        strip = _ohne_kommentare(_text(STRIP))
        self.assertIn('eq $seite.Section "posts"', strip)
        self.assertIn('and $blog (eq $ort "kopf")', strip)
        self.assertIn('and (not $blog) (eq $ort "footer")', strip)

    def test_kein_set_in_den_templates(self):
        """Hugo kennt kein `set`/`unset`: ein einziger Aufruf bricht den Build ab
        (…function "set" not defined…) und legt die ganze Site lahm. Karten von id
        auf Eintrag baut man hier mit `merge` – das ist die einzige Zuweisung Hugo."""
        for rel in NEUE + JOURNEYS + [STRIP, "layouts/_default/single.html"]:
            t = _ohne_kommentare(_text(rel))
            for m in re.finditer(r"(?<![\w.$-])(set|unset)\s+\$", t):
                self.fail(f"{rel}: `{m.group(0).strip()} …` – Hugo hat keine {m.group(1)}-Funktion "
                          "(Build bricht ab); Bitte `merge`/Zuweisung mit `=`")


class Daten(unittest.TestCase):
    def test_capture_schluessel_sind_hinterlegt(self):
        keys = set()
        for rel in [FORM, STATUS, STRIP, WEG, DATEN]:
            keys |= set(re.findall(r"capture\.([a-z_äöü]+)", _ohne_kommentare(_text(rel))))
        vorhanden = set(studio.capture(ROOT)) | set(json.loads(
            _text("data/newsletter_studio.json"))["capture"])
        self.assertEqual(set(), keys - vorhanden,
                         f"Templates lesen Capture-Schlüssel ohne Wert: {sorted(keys - vorhanden)}")

    def test_partial_gibt_alles_zurueck_was_gelesen_wird(self):
        daten = _text(DATEN).split("return")[-1]
        zurueck = set(re.findall(r'"([a-z_äöü]+)"', daten))
        gebr = set()
        for rel in [FORM, STATUS, STRIP, WEG, THEMEN, MUSTER]:
            gebr |= {t.split(".")[0] for t in re.findall(r"\$nl\.([a-z_äöü]+)",
                                                          _ohne_kommentare(_text(rel)))}
        self.assertEqual(set(), gebr - zurueck,
                         f"$nl.{sorted(gebr - zurueck)} wird gelesen, aber nicht zurückgegeben")

    def test_jede_newsletter_url_ist_eine_echte_seite(self):
        urls = set()
        quellen = ["data/newsletter_studio.json", FORM, STATUS, STRIP, MUSTER] + JOURNEYS
        for rel in quellen:
            for m in re.finditer(r'"(/newsletter[a-z0-9_/-]*)"|href="(/newsletter[a-z0-9_/-]*)"',
                                 _text(rel)):
                urls.add(m.group(1) or m.group(2))
        self.assertTrue(urls, "keine Journey-URL gefunden – Prüfkern fehlt")
        vorhanden = set()
        for index in glob.glob(os.path.join(ROOT, "content/**/index.md"), recursive=True):
            text = _text(os.path.relpath(index, ROOT))
            m = re.search(r'(?m)^url:\s*"?(/[^"\n]+)"?', text)
            vorhanden.add(m.group(1) if m else "/" + os.path.relpath(
                os.path.dirname(index), os.path.join(ROOT, "content")).replace(os.sep, "/") + "/")
        for url in sorted(urls):
            self.assertIn(url.rstrip("/") + "/", {u.rstrip("/") + "/" for u in vorhanden},
                          f"{url} wird verlinkt, gehört aber zu keiner Seite")


class Kadenz(unittest.TestCase):
    """Ein Versprechen, mehrere Oberflächen.

    „Zweimal pro Woche, dienstags und freitags“ steht im Anmeldeformular, im
    Streifen, auf der Landingpage, in der Datenschutzerklärung, im Studio-JSON und
    in der Betriebsanleitung. Wenn eine dieser Stellen noch den alten werktäglichen
    Versand verspricht, ist die Kadenz nicht eingerichtet, sondern halb umgezogen –
    und der Leser erfährt den Widerspruch im Postfach.
    """

    OBERFLAECHEN = JOURNEYS + [STRIP, FORM, MUSTER, "data/newsletter_studio.json",
                               "content/datenschutz/index.md",
                               "docs/ANLEITUNG-NEWSLETTER.md",
                               "docs/ANLEITUNG-NEWSLETTER-STUDIO.md",
                               "docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md",
                               "docs/NEWSLETTER-RECHTSTEXT-VORLAGE.md"]
    UEBERHOLT = ("pro Werktag", "1 Mail/Tag", "werktäglich", "an jedem Werktag",
                 "jeden Werktag", "Mo–Fr", "Mo-Fr", "Montag bis Freitag",
                 "eine Mail pro Tag")

    def test_kein_ueberholtes_versandsversprechen(self):
        for rel in self.OBERFLAECHEN:
            text = _ohne_kommentare(_text(rel))
            for alt in self.UEBERHOLT:
                self.assertNotIn(alt, text,
                                 f"{rel} verspricht noch „{alt}“ – der Vertrag ist "
                                 f"{plan.versandtage_text()}, höchstens "
                                 f"{plan.MAX_PRO_WOCHE} pro Kalenderwoche")

    def test_leserflaeche_nennt_beide_versandtage(self):
        for rel in ["content/newsletter/index.md", STRIP,
                    "content/newsletter-bestaetigung/index.md",
                    "content/newsletter-praeferenzen/index.md"]:
            text = _ohne_kommentare(_text(rel)).lower()
            for tag in plan.VERSANDTAGE:
                self.assertIn(plan.WOCHENTAGE[tag].lower(), text,
                              f"{rel} nennt {plan.WOCHENTAGE[tag]} nicht")

    def test_kadenzkonfiguration_deckt_genau_die_versandtage_ab(self):
        konf = json.loads(_text("data/newsletter_studio.json"))
        kadenz = konf["creative"]["kadenz"]
        for feld in ("ausgabe", "aufmacher", "betreff", "preheader_hinweis", "gruss"):
            self.assertEqual(sorted(int(k) for k in kadenz[feld]), list(plan.VERSANDTAGE),
                             f"creative.kadenz.{feld} deckt nicht genau die Versandtage ab")
        marke = konf["creative"]["marke_kurz"]
        grenze = konf["creative"]["betreff"]
        for tag, text in kadenz["betreff"].items():
            laenge = len(f"{marke}: {text}")
            self.assertGreaterEqual(laenge, grenze["min_zeichen"],
                                    f"Kadenz-Betreff für Wochentag {tag} ist zu kurz (Q8)")
            self.assertLessEqual(laenge, grenze["max_zeichen"],
                                 f"Kadenz-Betreff für Wochentag {tag} sprengt das "
                                 f"Längen-Gate (Q8): {laenge} > {grenze['max_zeichen']}")

    def test_beide_versandtage_bauen_eine_mail_mit_identitaet(self):
        """End-to-End durchs Studio: Dienstag und Freitag liefern verschiedene
        Ausgaben – Name, Kopfzeile, Betreff und nächsten Termin."""
        material = studio.material_aus_artikel(ROOT, studio._artikel_suchen(ROOT, 50))
        self.assertTrue(material, "kein Material im Bestand – Prüfkern fehlt")
        konf = studio.konfiguration(ROOT)
        dienstag = datetime.date(2026, 9, 22)
        freitag = datetime.date(2026, 9, 25)
        ausgaben = {}
        for tag in (dienstag, freitag):
            email = studio.baue_email(material, datum=tag, root=ROOT)
            kopf = next(b for b in email["blocks"] if b["typ"] == "kopf")
            fuss = next(b for b in email["blocks"] if b["typ"] == "fuss")
            self.assertIn(plan.wochentag(tag), kopf["zeile"], "Kopf ohne Versandtag")
            erkannt = plan.datum_lang_erkennen(fuss["naechste"])
            soll = plan.naechster_termin(tag)
            self.assertEqual((soll.day, soll.month), (erkannt["tag"], erkannt["monat"]),
                             "nächste Ausgabe stimmt nicht mit dem Vertrag überein")
            er = qa_pruefe(email, konf=konf, materiale=material, root=ROOT)
            self.assertEqual([], er["funde"],
                             f"QA-Funde am {plan.wochentag(tag)}: "
                             + json.dumps(er["funde"], ensure_ascii=False))
            ausgaben[tag] = (kopf.get("ausgabe"), email["betreff"])
        self.assertNotEqual(ausgaben[dienstag], ausgaben[freitag],
                            "beide Versandtage bauen dieselbe Ausgabe")

    def test_cron_und_vertrag_sind_dieselbe_kadenz(self):
        for name in ("newsletter-daily.yml", "newsletter-cadence.yml"):
            workflow = _text(os.path.join(".github/workflows", name))
            crons = re.findall(r'cron:\s*"([0-9*,\s-]+)"', workflow)
            self.assertTrue(crons, f"{name} ohne Cron")
            for cron in crons:
                tage = cron.split()[4]
                self.assertEqual({int(x) for x in tage.split(",")},
                                 {d + 1 for d in plan.VERSANDTAGE},
                                 f"{name}: Cron {cron} weicht vom Versandvertrag ab")


class Versandplan(unittest.TestCase):
    """Der Takt im Anmeldekasten: zwei Tage, ein Auftrag je Tag, ein Termin.

    Wer sich einträgt, kauft einen Kalender – also steht der Kalender VOR dem
    Feld, nicht als Kleingedrucktes danach. Die Fakten liest der Baustein aus
    data/newsletter_kadenz.json (Snapshot des Versandvertrags), die Redaktion
    aus creative.kadenz. Was hier geprüft wird: dass er sie liest, dass der
    Snapshot der Vertrag ist, und dass kein Termin im HTML steht, der über
    Nacht altert.
    """

    def snapshot(self) -> dict:
        return json.loads(_text(KADENZ))

    def test_snapshot_ist_der_vertrag(self):
        self.assertEqual(plan.site_kadenz_text(), _text(KADENZ),
                         f"{KADENZ} weicht vom Versandvertrag ab – "
                         "`python3 scripts/newsletter_schedule.py --export-site`")

    def test_baustein_liest_die_fakten_statt_sie_zu_tippen(self):
        t = _ohne_kommentare(_text(PLAN))
        for feld in ("versandtage_text", "versandtage_oder", "uhrzeit_zeile",
                     "max_pro_woche", "tage", "tag_kurz", "schluessel"):
            self.assertIn(feld, t, f"{PLAN} tippt {feld} ab, statt es zu lesen")
        for name in plan.WOCHENTAGE:
            self.assertNotIn(name, t,
                             f"{PLAN} nennt {name} wörtlich – Wochentage kommen aus dem Snapshot")
        self.assertNotRegex(t, r"\b\d{2}:\d{2}\b",
                            f"{PLAN} trägt eine Uhrzeit im Markup – sie kommt aus dem Snapshot")

    def test_fallbacks_im_formular_stimmen_mit_dem_vertrag(self):
        """Die Defaults des Shortcodes sind ein Sicherheitsnetz, kein zweiter Vertrag."""
        t = _text(FORM)
        self.assertIn(f'default "{plan.versandtage_oder_text()}"', t)
        self.assertIn(f'default "{plan.uhrzeit_zeile()}"', t)
        self.assertIn(f"default {plan.MAX_PRO_WOCHE}", t)

    def test_redaktion_je_versandtag_ist_hinterlegt(self):
        kadenz = json.loads(_text("data/newsletter_studio.json"))["creative"]["kadenz"]
        for eintrag in self.snapshot()["tage"]:
            for feld in ("ausgabe", "preheader_hinweis"):
                self.assertIn(eintrag["schluessel"], kadenz[feld],
                              f"creative.kadenz.{feld} hat keinen Eintrag für "
                              f"{eintrag['tag']} – die Kachel bliebe stumm")

    def test_kein_termin_im_html(self):
        """Den nächsten Termin rechnet ff-newsletter.js in Europe/Berlin.

        Ein gedruckter Termin ist am Tag nach dem Bau falsch – und eine
        Landingpage, die gestern ankündigt, bricht dasselbe Versprechen, das
        sie verkauft. Ohne Skript bleibt der kadenzrichtige Satz ohne Datum.
        """
        t = _ohne_kommentare(_text(PLAN))
        self.assertNotRegex(t, r"\d{1,2}\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|"
                               r"August|September|Oktober|November|Dezember)")
        self.assertIn("der kommende", t, "ohne Skript fehlt der kadenzrichtige Ersatzsatz")
        js = _text(JS)
        self.assertIn("Europe/Berlin", js, "gerechnet wird in der Taktzone des Versands")
        self.assertIn("data-ff-nl-uhrzeit", js,
                      "die Versanduhrzeit liest das Skript aus dem Baustein, nicht aus dem Code")

    def test_plan_steht_nur_bei_geschaltetem_weg(self):
        """Kein Versandplan im Leerzustand: ein Takt ohne Anmeldung ist Werbung."""
        t = _text(FORM)
        self.assertEqual(2, t.count('partial "newsletter_versandplan.html"'),
                         "der Plan gehört zum Inline-Formular UND zum Button-Weg")
        leerzustand = t.split("{{- else -}}")[-1]
        self.assertNotIn("newsletter_versandplan.html", leerzustand,
                         "der Leerzustand bewirbt einen Takt, den er nicht hält")


class Journeys(unittest.TestCase):
    def test_utility_seiten_sind_abgemeldet(self):
        for rel in JOURNEYS:
            text = _text(rel)
            schuppe = text.split("---")[1]
            self.assertRegex(schuppe, r"(?m)^robotsNoIndex:\s*true\s*$", f"{rel}: indexierbar")
            self.assertRegex(schuppe, r"(?m)^\s+disable:\s*true", f"{rel}: in der Sitemap")
            self.assertNotRegex(schuppe, r"(?m)^draft:\s*true", f"{rel}: Draft in der Strecke")

    def test_url_und_ordner_passen_zusammen(self):
        for rel in JOURNEYS:
            text = _text(rel)
            ordner = os.path.basename(os.path.dirname(rel))
            url = re.search(r'(?m)^url:\s*"(/[^"]+)"', text).group(1)
            selbst = "/newsletter/" if ordner == "newsletter" else "/newsletter/" + \
                ordner[len("newsletter-"):] + "/"
            self.assertEqual(selbst, url, f"{rel}: url {url} passt nicht zum Ordner {ordner}")

    def test_datenschutz_meldet_den_zustatt_der_vermutung(self):
        text = _text("content/datenschutz/index.md")
        self.assertIn("{{< newsletter_status >}}", text,
                      "der Abschnitt schreibt einen Zustand, statt ihn aus dem Studio zu lesen")
        self.assertNotIn("Sie wird erst aktiv, wenn der Auftragsverarbeitungsvertrag",
                         text.replace("{{< newsletter_status >}}", ""),
                         "der alte bedingte Satz beschreibt einen Zustand, den "
                         "die Datenschutzerklärung nicht kennen kann")
        abschnitt = text[text.lower().find("newsletter"):]
        for pflicht in ("Double-Opt", "Auftragsverarbeitungsvertrag", "Widerruf"):
            self.assertIn(pflicht, abschnitt[:4000], f"Datenschutz-Abschnitt ohne {pflicht}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
