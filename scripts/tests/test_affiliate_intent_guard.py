"""Regressionstests für die Intent-Wache (Auftrag Frank, 19.09.2026).

Der Vorfall: Sieben Live-Artikel lieferten über ihren prominentesten CTA ein
ANDERES Produkt, als Anker und Artikelthema versprachen –

  · Kfz-Versicherungsvergleich      → /go/haftpflicht/       (Privathaftpflicht)
  · Kostenloses Girokonto           → /go/kredit/            (Ratenkredit)
  · Kreditkartenvergleich           → /go/reisekrankenversicherung/
  · Mietwagen-Ratgeber (1. + letzter CTA) → /go/kfz-versicherung/
  · Wohngebäudeversicherung         → /go/hausrat/           (andere Police)
  · Flugticket-Ratgeber             → /go/mietwagen/         (Pillar-Fallback)
  · Tagesgeldvergleich              → C24 Bank, ohne sie zu nennen

und drei Angebote wichen vom naheliegenden Namen ab (Tagesgeld/Girokonto sind
Angebote der C24 Bank, „Flüge" ist der CHECK24-Pauschalreise-Vergleich).

Warum das lange niemand sah: Die Anker stammten aus einem generischen Pool
(„Jetzt Angebote vergleichen", „Tarifrechner starten"), gezogen über
`date.today().day`. Ein Anker, der nichts verspricht, widerspricht sich nie –
er fiel durch jede Prüfung, während der Besucher auf einem fremden Produkt
landete. Genau deshalb prüft diese Wache drei Dinge GETRENNT:
Anker ↔ Route (IW1), CTA ↔ Artikelthema (IW2/IW4), Name ↔ wirkliches
Angebot (IW3/IW8) – und bewacht mit IW6 auch die QUELLE (den Generator).

Diese Tests sind die zweite Brille neben `--selftest`: Sie rufen die Wache
über ihre öffentliche API auf (nicht über den Selbsttest), damit ein
kaputter Selbsttest nicht seine eigene Grünheit beweist.

Laufbar über die Repo-Konvention (kein pytest nötig):
    python3 -m unittest discover -s scripts/tests
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import affiliate_intent_contract as vk  # noqa: E402
import affiliate_intent_guard as aig  # noqa: E402


# --------------------------------------------------------------------- #
# Helfer: Artikel-Fixture ohne Festplatte
# --------------------------------------------------------------------- #
def artikel(slug: str, title: str, body: str, tags=None, pillar: str = "") -> dict:
    fm = f'title: "{title}"\n'
    if tags:
        fm += "tags: [" + ", ".join(f'"{t}"' for t in tags) + "]\n"
    if pillar:
        fm += f'pillar: "{pillar}"\n'
    fm += "draft: false\n"
    text = f"---\n{fm}---\n{body}"
    prefix, fm_raw, body_raw = aig.split_article(text)
    return {
        "slug": slug, "path": ROOT / "content" / "posts" / slug / "index.md",
        "rel": f"content/posts/{slug}/index.md", "prefix": prefix,
        "fm": fm_raw, "body": body_raw, "text": text,
        "title": aig.fm_value(fm_raw, "title"),
        "tags": aig.fm_list(fm_raw, "tags"),
        "pillar": aig.fm_value(fm_raw, "pillar"),
        "draft": False, "section": "posts",
    }


def funde(art, reg=None, titel_pfad=None):
    return aig.pruefe_artikel(art, reg or aig.load_registry(), titel_pfad or {})


def heilen(art, reg=None, titel_pfad=None):
    reg = reg or aig.load_registry()
    titel_pfad = titel_pfad or {}
    funde_auto = [f for f in funde(art, reg, titel_pfad)
                  if f["owner"] == "auto" and f.get("blocking")]
    body, _ = aig.heile_artikel(art, funde_auto, reg, titel_pfad)
    return body


DISCLAIMER = ("_(Dieser Artikel enthält Affiliate-Links (Werbung). Beim "
              "Abschluss über einen Link erhalten wir eine Provision – für "
              "dich entstehen keine Mehrkosten.)_")


def top_cta(satz: str, anker: str, route: str) -> str:
    return (f"\n💡 **Schnell-Tipp von FranksFinanzcheck:** {satz}: "
            f"[**{anker}**](/go/{route}/)  \n{DISCLAIMER}\n")


def end_cta(anker: str, route: str) -> str:
    return (f"\n---\n\n👉 **Jetzt vergleichen und sparen:** "
            f"[**{anker}**](/go/{route}/)\n")


# --------------------------------------------------------------------- #
# 1) Die sieben Live-Funde vom 19.09.2026 müssen auffallen UND heilen
# --------------------------------------------------------------------- #
VORFAELLE = [
    # (Name, Titel, Anker, falsche Route, erwartete Route, erwarteter Code)
    ("kfz", "Kfz-Versicherung Vergleich 2026: Bis zu 800 € sparen",
     "Kfz-Versicherung vergleichen", "haftpflicht", "kfz-versicherung", "IW1"),
    ("girokonto", "Kostenloses Girokonto: So findest du ein Konto ohne Gebühren",
     "Kostenlos vergleichen", "kredit", "girokonto", "IW4"),
    ("kreditkarte", "Kreditkarte vergleichen: Kostenlos und sicher bezahlen",
     "Tarifrechner starten", "reisekrankenversicherung", "kreditkarte", "IW4"),
    ("mietwagen", "Mietwagen buchen ohne Kaution: Fallen im Urlaub",
     "Jetzt Mietwagen vergleichen", "kfz-versicherung", "mietwagen", "IW1"),
    ("wohngebaeude", "Wohngebäudeversicherung Vergleich: Worauf du achten musst",
     "Versicherungsvergleich starten", "hausrat", "wohngebaeudeversicherung", "IW4"),
    ("fluege", "Flugtickets günstig buchen: Strategien für deine Reise",
     "Kostenlos vergleichen", "mietwagen", "fluege", "IW4"),
    ("gas", "Gasrechnung senken: Spätsommer-Check spart hunderte Euro",
     "Gasvergleich", "strom", "gas", "IW1"),
]


class VorfaelleVom19September(unittest.TestCase):
    """Jeder einzelne Live-Fund: erkannt → geheilt → und dann ruhig."""

    def test_vorfall_wird_erkannt(self):
        for name, titel, anker, falsch, richtig, code in VORFAELLE:
            with self.subTest(vorfall=name):
                art = artikel(name, titel,
                              "\nIntro.\n" + top_cta("Jetzt prüfen", anker, falsch))
                codes = {f["code"] for f in funde(art)}
                self.assertIn(code, codes, f"{name}: {code} fehlt in {codes}")

    def test_vorfall_heilt_auf_die_richtige_route(self):
        for name, titel, anker, falsch, richtig, code in VORFAELLE:
            with self.subTest(vorfall=name):
                body = ("\nIntro.\n" + top_cta("Jetzt prüfen", anker, falsch)
                        + end_cta("→ Jetzt Angebote vergleichen", falsch))
                neu = heilen(artikel(name, titel, body))
                self.assertNotIn(f"/go/{falsch}/", neu,
                                 f"{name}: falsche Route blieb stehen:\n{neu}")
                self.assertIn(f"/go/{richtig}/", neu,
                              f"{name}: richtige Route fehlt:\n{neu}")

    def test_heilung_ist_idempotent(self):
        """Zweiter Lauf: keine harten Funde, keine weitere Änderung.

        Ohne Idempotenz würde die Wache jeden Tag denselben Artikel neu
        „heilen" – Churn im Diff und kein stabiler Beweis.
        """
        for name, titel, anker, falsch, richtig, code in VORFAELLE:
            with self.subTest(vorfall=name):
                neu1 = heilen(artikel(
                    name, titel, "\nIntro.\n" + top_cta("Jetzt prüfen", anker, falsch)))
                # heilen() liefert den GESAMTEN Body zurück – nicht noch einmal
                # ein Intro vorsetzen, sonst prüft der Test sein eigenes Echo.
                art2 = artikel(name, titel, neu1)
                rest = [f for f in funde(art2) if f.get("blocking") and f["owner"] == "auto"]
                self.assertEqual([], rest, f"{name}: Restfunde nach Heilung")
                self.assertEqual(neu1, heilen(art2), f"{name}: Heilung nicht idempotent")

    def test_tagesgeld_muss_c24_nennen(self):
        """Abweichung Einzelanbieter: ohne Nennung der C24 Bank ist der CTA
        ein Marktvergleich, den es nicht gibt (Frank-Regel 11.08.2026)."""
        art = artikel("tagesgeld", "Tagesgeld Zinsen 2026: Die besten Zinssätze",
                      "\nIntro.\n" + top_cta("Sichere dir die Spitzenzinsen",
                                             "Jetzt Tagesgeld vergleichen", "tagesgeld"))
        self.assertTrue(any(f["code"] == "IW3" for f in funde(art)))
        neu = heilen(art)
        self.assertIn("C24", neu, f"C24-Nennung fehlt nach der Heilung:\n{neu}")
        self.assertIn("Tagesgeld", neu)

    def test_fluege_muss_pauschalreise_nennen(self):
        """Es gibt im CHECK24-Partnerprogramm keinen Flug-Deep-Link (deep=fluege
        endet E2E auf einer 404, geprüft 19.09.2026) – also ehrlich als Paket."""
        art = artikel("fluege2", "Flüge vergleichen: So findest du günstige Tickets",
                      "\nIntro.\n" + top_cta("Jetzt günstig fliegen",
                                             "Flüge vergleichen", "fluege"))
        neu = heilen(art)
        self.assertTrue("Pauschalreise" in neu or "Paket" in neu,
                        f"ehrliche Benennung als Pauschalreise fehlt:\n{neu}")
        self.assertNotIn("Flüge vergleichen**]", neu)


# --------------------------------------------------------------------- #
# 2) Was die Wache NICHT antasten darf
# --------------------------------------------------------------------- #
class SchutzVorUeberheilung(unittest.TestCase):
    """Eine Ehrlichkeits-Wache, die ehrliche Werbung killt, ist schlimmer
    als gar keine Wache: Sie erzeugt Druck, sie abzuschalten."""

    def test_ehrliches_cross_selling_bleibt_stehen(self):
        """Im Mietwagen-Ratgeber darf ein Kreditkarten-/Reisekranken-Angebot
        stehen, wenn der Anker es selbst nennt – sonst wäre die Wache ein
        Umsatz-Vernichter statt ein Ehrlichkeits-Werkzeug."""
        body = ("\nWer keine Karte hat, braucht ein [gebührenfreies "
                "Kreditkarten-Konto](/go/kreditkarte/) oder eine "
                "[Auslandsreise-Absicherung](/go/reisekrankenversicherung/).\n")
        art = artikel("cross", "Mietwagen ohne Kautionsfallen: So sparst du im Urlaub", body)
        self.assertEqual([], funde(art), "ehrliches Cross-Selling als Fund gemeldet")
        self.assertEqual(body, heilen(art), "ehrliches Cross-Selling wurde verändert")

    def test_prosa_mit_partnernennung_bleibt_stehen(self):
        """„Bei der [C24 Bank](/go/girokonto/) sind Kategorien integriert" ist
        ehrlich UND Teil der Satzgrammatik. Ein CTA-Anker daraus zu machen
        ergab am 19.09.2026 „Bei der C24 Bank Girokonto sind …" – kaputtes
        Deutsch. Deshalb: Prosa mit Ziel-Nennung ist kein IW8-Fund."""
        body = ("\nBei der [C24 Bank](/go/girokonto/) sind Kategorien und "
                "Haushaltsbuch direkt im Girokonto integriert.\n")
        art = artikel("prosa", "Haushaltsbuch führen: App, Excel oder Papier", body)
        self.assertEqual([], [f for f in funde(art) if f["code"] == "IW8"])
        self.assertEqual(body, heilen(art))

    def test_ehrlicher_zweit_cta_im_falschen_thema_ist_nur_hinweis(self):
        """Wohngebäude-Artikel mit Hausrat-CTA: Der Anker nennt die Hausrat-
        versicherung, der Besucher wird nicht getäuscht → Hinweis (nicht
        blockierend), kein harter Fund. Ein generischer Anker („Jetzt Angebote
        vergleichen") auf derselben Route bleibt hart."""
        intro = "\nIntro zur Wohngebäudeversicherung.\n"
        ehrlich = top_cta("Prüfe die Elementardeckung",
                          "Jetzt Hausratversicherung vergleichen", "hausrat")
        art = artikel("haus", "Dein Haus sicher schützen: Das Vorsorge-Update 2026",
                      intro + ehrlich)
        alle = funde(art)
        self.assertTrue(alle, "Nie-Paar blieb unbemerkt")
        self.assertTrue(all(not f.get("blocking") for f in alle),
                        f"ehrlich benanntes Zweitangebot blockiert: {alle}")
        self.assertEqual(intro + ehrlich, heilen(art))

        generisch = top_cta("Prüfe die Elementardeckung",
                            "Jetzt Angebote vergleichen", "hausrat")
        art2 = artikel("haus2", "Dein Haus sicher schützen: Das Vorsorge-Update 2026",
                       intro + generisch)
        self.assertTrue([f for f in funde(art2) if f.get("blocking")],
                        "generischer Anker auf fremder Route muss blockieren")
        self.assertIn("/go/wohngebaeudeversicherung/", heilen(art2))

    def test_heilung_fasst_nur_die_kranke_zeile_an(self):
        """Byte-Exaktheit: Leerzeilen hinter der Frontmatter und alle übrigen
        Zeilen müssen unverändert bleiben (Fund 19.09.2026: 59 Leerzeilen in
        25 Artikeln im Diff, obwohl nur Anker geheilt wurden)."""
        body = "\n\n\n\nIntro.\n\n" + end_cta("→ Jetzt Angebote vergleichen", "strom")
        neu = heilen(artikel("naht", "Stromtarife vergleichen: So sparst du 2026", body))
        self.assertTrue(neu.startswith("\n\n\n\nIntro.\n\n"), "Naht/Leerzeilen gefressen")
        alt, jetzt = body.split("\n"), neu.split("\n")
        self.assertEqual(len(alt), len(jetzt), "Zeilenanzahl verändert")
        unterschiede = [i for i, (a, b) in enumerate(zip(alt, jetzt)) if a != b]
        self.assertTrue(unterschiede, "die kranke Zeile wurde nicht geheilt")
        for i in unterschiede:
            self.assertIn("/go/", alt[i], f"Zeile ohne Affiliate-Link verändert: {i}")


# --------------------------------------------------------------------- #
# 3) Eine Wahrheit: Kontrakt, Register, Daten, Templates, Generator
# --------------------------------------------------------------------- #
class EineWahrheit(unittest.TestCase):
    """Der teure Fehler war nicht ein falscher Link, sondern dass fünf Orte
    je ihre eigene Meinung über Routen, Namen und Versprechen hatten."""

    def test_kontrakt_und_register_decken_sich(self):
        reg = aig.load_registry()
        self.assertTrue(reg, "Register lieferte keine Routen (Wache wäre blind)")
        self.assertEqual(set(), set(reg) - set(vk.ZIELE),
                         "Routen ohne Kontrakt-Eintrag")
        self.assertEqual(set(), set(vk.ZIELE) - set(reg),
                         "Kontrakt-Routen ohne Partner-URL")

    def test_health_kontrakt_deckt_alle_routen(self):
        import affiliate_health as ah
        self.assertEqual(set(), set(aig.load_registry()) - set(ah.CONTRACT),
                         "affiliate_health.py kennt nicht alle Routen")

    def test_datendatei_ist_aus_dem_kontrakt_gebacken(self):
        daten = ROOT / "data" / "affiliate_ziele.yaml"
        self.assertTrue(daten.is_file(),
                        "data/affiliate_ziele.yaml fehlt (Hugo-Tooltip-Fallback)")
        self.assertEqual(vk.bake_yaml(), daten.read_text(encoding="utf-8"),
                         "data/affiliate_ziele.yaml weicht vom Kontrakt ab – "
                         "python3 scripts/affiliate_intent_guard.py --bake")

    def test_templates_lesen_die_datendatei(self):
        """Tooltip-Namen dürfen keine zweite Wahrheit sein: Die Templates lesen
        data/affiliate_ziele.yaml über das Hausmuster-Partial, ihr Fallback-Dict
        trägt exakt die Kontrakt-Namen (IW0 prüft Zeichen für Zeichen)."""
        for template in ("layouts/_default/_markup/render-link.html",
                         "layouts/_partials/affiliate_anchor_attrs.html"):
            with self.subTest(template=template):
                text = (ROOT / template).read_text(encoding="utf-8")
                self.assertIn('partialCached "affiliate_ziele_data.html"', text,
                              f"{template} lädt die Zieldatei nicht über das Partial")
                for key, z in vk.ZIELE.items():
                    self.assertIn(key, text, f"{template}: Route {key} fehlt im Fallback")
                    self.assertIn(z.anzeige, text,
                                  f"{template}: Anzeigename für {key} driftet")

    def test_datenpfad_ist_build_sicher(self):
        """Build-Killer 19.09.2026: EIN `site.Data`-Zugriff in einem Layout lässt
        Hugo den ganzen data/-Baum parsen – inklusive der *.jsonl-Bot-Protokolle
        (data/audit/ u. a.). Folge: `failed to load data: … unmarshal of format
        "" is not supported`, die Seite baut nicht, kein Deploy, drei CI-Checks
        rot. Der Datenpfad muss deshalb über os.ReadFile laufen."""
        import yaml

        partial = ROOT / "layouts" / "_partials" / "affiliate_ziele_data.html"
        self.assertTrue(partial.is_file(),
                        "affiliate_ziele_data.html fehlt – Templates müssten "
                        "über hugo.Data gehen (Build-Killer)")
        ptext = partial.read_text(encoding="utf-8")
        self.assertEqual([], aig.datenpfad_fehler(ptext),
                         "Datenpfad-Partial wäre ein Build-Killer")
        self.assertIn('os.ReadFile "data/affiliate_ziele.yaml"', ptext)
        self.assertIn("transform.Unmarshal", ptext)
        # Ohne explizites Format rät Hugo bei dem #-Kommentarkopf TOML:
        # „_stream.toml:16:6: toml: expected '=' after key" (19.09.2026).
        self.assertIn('"format" "yaml"', ptext)

        griffe = []
        for datei in sorted((ROOT / "layouts").rglob("*.html")):
            for zeile, treffer in aig.datenbaum_griffe(
                    datei.read_text(encoding="utf-8")):
                griffe.append(f"{datei.relative_to(ROOT)}:{zeile} {treffer}")
        self.assertEqual([], griffe,
                         "diese Layouts killen den Hugo-Build: " + "; ".join(griffe))

        # Und was das Partial zur Build-Zeit wirklich liest, muss der Kontrakt sein
        daten = yaml.safe_load((ROOT / "data" / "affiliate_ziele.yaml")
                               .read_text(encoding="utf-8"))["ziele"]
        self.assertEqual(set(vk.ZIELE), set(daten), "Datendatei ≠ Kontrakt-Routen")
        for key, z in vk.ZIELE.items():
            with self.subTest(route=key):
                # `anzeige` ist das Feld, das die Templates zur Build-Zeit
                # wirklich lesen (Tooltip). `weiter_zu` bleibt bewusst im
                # Kontrakt und wird auf die Gateway-Seiten gebacken – dafür
                # gibt es test_gateway_seiten_sind_ehrlich_und_dicht.
                self.assertEqual(z.anzeige, daten[key]["anzeige"])
                self.assertEqual(z.gateway, daten[key]["gateway"])
                self.assertEqual(z.partner, daten[key]["partner"])

    def test_datenpfad_detektor_sieht_sabotage_und_keine_kommentare(self):
        """Der Detektor muss die Tat sehen, nicht ihre Beschreibung – sonst ist
        er entweder blind oder ein Dauer-Alarm, den jemand abschaltet."""
        self.assertTrue(aig.datenbaum_griffe('{{- with site.Data.x -}}{{- end -}}'))
        self.assertTrue(aig.datenbaum_griffe('{{ $a := hugo.Data.x }}'))
        self.assertEqual([], aig.datenbaum_griffe(
            '{{/* site.Data und hugo.Data sind hier verboten */}}\n'
            '<!-- .Site.Data ebenso -->'))

    def test_gateway_seiten_sind_ehrlich_und_dicht(self):
        for route, url in aig.load_registry().items():
            with self.subTest(route=route):
                seite = ROOT / "static" / "go" / route / "index.html"
                self.assertTrue(seite.is_file(), f"/go/{route}/ fehlt – Klick läuft ins Leere")
                html = seite.read_text(encoding="utf-8")
                self.assertIn(url, html, f"/go/{route}/ leitet nicht auf die Register-URL")
                self.assertIn("noindex", html, f"/go/{route}/ ist nicht auf noindex gesetzt")
                z = vk.ziel(route)
                self.assertIn(z.ziel_phrase(), html,
                              f"/go/{route}/ nennt das echte Ziel nicht "
                              f"(erwartet „Weiter {z.ziel_phrase()}“)")

    def test_generator_erzeugt_konforme_ctas(self):
        """IW6: Die Quelle mitbewachen. Ohne diesen Test wäre die Wache ein
        Eimer unter einem laufenden Hahn – neue Artikel entstünden weiter mit
        generischen Ankern und Pillar-Fallbacks."""
        import affiliate_marketer as am
        reg = aig.load_registry()
        for route, z in vk.ZIELE.items():
            probe = f"{z.produkt} – {z.anker_fuer('intext')} im Test"
            if route == "allgemein":
                probe = "Budget und Haushaltsbuch im Alltag, ganz ohne Fachprodukt"
            text = probe if route == "allgemein" else f"{probe} [Test](/go/{route}/)"
            for bau, slot in ((am.build_top_cta, "top"), (am.mid_cta, "mid"),
                              (am.end_cta, "end")):
                with self.subTest(route=route, bau=bau.__name__, slot=slot):
                    cta = bau("", reg, text, "test-slug")
                    m = aig.MD_GO_LINK.search(cta)
                    self.assertIsNotNone(m, f"{bau.__name__}({route}) erzeugt keinen Link")
                    self.assertEqual(route, m.group("key"),
                                     f"{bau.__name__}({route}) liefert /go/{m.group('key')}/")
                    anker = m.group("anchor").strip("*").strip()
                    self.assertFalse(vk.anker_ist_generisch(anker),
                                     f"{bau.__name__}({route},{slot}) generisch: „{anker}“")
                    self.assertTrue(z.ehrlich(anker)[0],
                                    f"{bau.__name__}({route},{slot}) unehrlich: „{anker}“")

    def test_generator_ist_deterministisch(self):
        """Kein Tages-Churn mehr: Vorher wählte `date.today().day` den Anker –
        derselbe Artikel bekam an verschiedenen Tagen verschiedene CTAs."""
        import affiliate_marketer as am
        reg = aig.load_registry()
        text = "Stromtarife 2026 – Stromanbieter wechseln im Test [x](/go/strom/)"
        self.assertEqual(am.build_top_cta("", reg, text, "artikel-slug"),
                         am.build_top_cta("", reg, text, "artikel-slug"))

    def test_pillar_fallback_ueberstimmt_den_artikel_nicht(self):
        """Root-Cause des Flug-Funds: `pillar: mietwagen` im Front-Matter
        überstimmte das Artikelthema. Der Titel muss gewinnen."""
        import affiliate_marketer as am
        titel = "Flugtickets günstig buchen: Strategien für deine Reise"
        route = am.route_for(titel, "mietwagen", titel)
        self.assertEqual("fluege", route, f"Pillar-Fallback überstimmt das Thema: {route}")


# --------------------------------------------------------------------- #
# 4) Bestand, Fail-Closed, Selbsttests
# --------------------------------------------------------------------- #
class BestandUndWerkzeugfehler(unittest.TestCase):
    """Die Wache muss über den echten Bestand laufen UND bei eigener
    Blindheit laut scheitern – nie grün schweigen."""

    def test_bestand_ist_intent_sauber(self):
        """Der geheilte Bestand darf nicht zurückdriften: keine harten Funde.

        Hinweis-Funde (ehrliches Cross-Selling) sind erlaubt und werden im
        Report gezeigt – sie blockieren weder CI noch Deploy.
        """
        alt = aig.DRY_RUN
        aig.DRY_RUN = True          # Beweislauf schreibt nichts ins Repo
        try:
            res = aig.run(do_heal=False)
        finally:
            aig.DRY_RUN = alt
        self.assertEqual([], res["errors"], f"Werkzeugfehler: {res['errors']}")
        hart = [f for f in res["findings"] if f.get("blocking")]
        self.assertEqual([], hart, "\n".join(
            f"{f['code']} {f['path']}:{f['line_datei']} /go/{f['route']}/ "
            f"«{f['anchor']}» – {f['problem']}" for f in hart[:20]))

    def test_wache_ist_fail_closed_bei_kaputtem_register(self):
        """Ohne Register kein Beweis – dann Exit 2 (Werkzeugfehler), niemals
        „grün". Eine Wache, die bei eigener Blindheit grün meldet, ist die
        teuerste Art von Sicherheit (Vorfall 01.09.2026)."""
        tmp = Path(tempfile.mkdtemp(prefix="intent-wache-"))
        alt = aig.DRY_RUN
        try:
            (tmp / "scripts").mkdir()
            (tmp / "scripts" / "check24_links.yaml").write_text(
                "# leeres Register\n", encoding="utf-8")
            aig.DRY_RUN = True      # Beweislauf schreibt nichts ins Repo
            res = aig.run(root=tmp, do_heal=False)
            self.assertEqual(aig.EXIT_TOOL, res["exit_code"])
        finally:
            aig.DRY_RUN = alt
            shutil.rmtree(tmp, ignore_errors=True)

    def test_selbsttests_von_kontrakt_und_wache(self):
        self.assertEqual([], vk.selftest())
        self.assertEqual([], aig.run_selftest())

    def test_wache_laueft_als_skript(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "affiliate_intent_guard.py"), "--selftest"],
            capture_output=True, text=True, cwd=ROOT, timeout=300)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
