"""Versandvertrag unabhängig von Systemzeit/Netz: Kalender, Journal, echter Sendepfad."""
import datetime as dt
import json
import re
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import newsletter_schedule as ns
import newsletter_digest as nd
import newsletter_cadence as nc

ROOT = Path(__file__).resolve().parents[2]


def zeit(tag, stunde=7):
    return dt.datetime.fromisoformat(f"{tag}T{stunde:02}:05:00+02:00")


class Kalender(unittest.TestCase):
    def test_exakt_zwei_versandtage(self):
        start = zeit("2026-09-21")
        erlaubt = [i for i in range(7) if not ns.versandpause({}, start + dt.timedelta(days=i))]
        self.assertEqual([1, 4], erlaubt)

    def test_zweiter_lauf_am_selben_tag_bleibt_aus(self):
        self.assertIn("bereits", ns.versandpause(
            {"versand_termine": [zeit("2026-09-22").isoformat()]}, zeit("2026-09-22", 12)))

    def test_wochenlimit_auch_mit_altem_werktagsversand(self):
        state = {"versand_termine": [zeit("2026-09-21").isoformat(), zeit("2026-09-22").isoformat()]}
        self.assertIn("Kalenderwoche", ns.versandpause(state, zeit("2026-09-25")))
        self.assertEqual("", ns.versandpause(state, zeit("2026-09-29")))

    def test_jahreswechsel_iso_woche(self):
        state = {"versand_termine": ["2026-12-29T07:00:00+01:00", "2026-12-30T07:00:00+01:00"]}
        self.assertIn("Kalenderwoche", ns.versandpause(state, dt.datetime.fromisoformat("2027-01-01T07:00:00+01:00")))

    def test_sommer_und_winterzeit_berlin(self):
        for tag in ("2026-03-31", "2026-10-27"):
            with self.subTest(tag=tag):
                self.assertEqual("", ns.versandpause({}, dt.datetime.fromisoformat(tag + "T05:05:00+00:00")))
        # UTC-Montag, in Berlin bereits Dienstag: lokaler Kalendertag entscheidet.
        self.assertEqual("", ns.versandpause({}, dt.datetime.fromisoformat("2026-09-21T22:05:00+00:00")))

    def test_migration_und_kaputtes_journal(self):
        self.assertIn("bereits", ns.versandpause({"zuletzt_versandt": zeit("2026-09-22").isoformat()}, zeit("2026-09-22", 9)))
        for wert in (None, {}, ["kaputt"], ["2026-09-22T07:00:00"], ["2027-01-01T07:00:00+01:00"]):
            with self.subTest(wert=wert), self.assertRaises((ValueError, TypeError)):
                ns.versandpause({"versand_termine": wert}, zeit("2026-09-22"))

    def test_wache_nur_an_versandtagen_und_nach_faelligkeit(self):
        for tag in ("2026-09-21", "2026-09-23", "2026-09-24", "2026-09-26", "2026-09-27"):
            self.assertEqual("ruhetag", nc.entscheide([], zeit(tag, 12))["handlung"])
        self.assertEqual("ruhetag", nc.entscheide([], zeit("2026-09-22"))["handlung"])
        self.assertEqual("nachholen", nc.entscheide([], zeit("2026-09-22", 12))["handlung"])

    def test_workflows_und_nachholen_haben_dieselbe_kadenz(self):
        for name, cron in (("newsletter-daily.yml", '5 5 * * 2,5'), ("newsletter-cadence.yml", '11 8 * * 2,5')):
            self.assertIn(f'cron: "{cron}"', (ROOT / '.github/workflows' / name).read_text())
        with patch.object(nc, '_gh') as gh:
            gh.return_value.returncode = 0
            nc.hole_nach('org/repo', 'branch')
            self.assertIn('tage=7', gh.call_args.args[0])


class Redaktionsrahmen(unittest.TestCase):
    """Die Texte und Termine der Kadenz – locale-frei und gegen den Vertrag."""

    def test_wochentagsnamen_haengen_nicht_an_der_locale(self):
        # strftime("%A") liefert „Tuesday“ auf dem Runner: die Tabelle ist der
        # Grund, warum die Kadenz-Logik trotzdem funktioniert.
        self.assertEqual("Dienstag", ns.wochentag(dt.date(2026, 9, 22)))
        self.assertEqual("Freitag", ns.wochentag(dt.date(2026, 9, 25)))
        self.assertEqual("Samstag", ns.wochentag(dt.date(2026, 9, 26)))
        self.assertEqual("Di", ns.tag_kurz(dt.date(2026, 9, 22)))
        self.assertEqual("Dienstag, 22. September 2026", ns.datum_lang(dt.date(2026, 9, 22)))
        self.assertEqual("Di, 22.09.", ns.datum_kurz(dt.date(2026, 9, 22)))

    def test_naechster_termin_ist_immer_ein_versandtag(self):
        start = dt.date(2026, 9, 20)
        for i in range(60):
            d = start + dt.timedelta(days=i)
            n = ns.naechster_termin(d)
            with self.subTest(datum=d.isoformat()):
                self.assertIn(n.weekday(), ns.VERSANDTAGE)
                self.assertGreater(n, d, "eine Ausgabe kündigt nie sich selbst an")
                # Freitag → Dienstag sind vier Tage: die längste Lücke des Vertrags.
                self.assertLessEqual((n - d).days, 4)
                self.assertTrue(ns.ist_versandtag(n))

    def test_dienstag_kuendigt_freitag_an_und_freitag_dienstag(self):
        self.assertIn("Freitag, 25. September", ns.naechste_ausgabe_text(dt.date(2026, 9, 22)))
        self.assertIn("Dienstag, 29. September", ns.naechste_ausgabe_text(dt.date(2026, 9, 25)))
        self.assertNotIn("2026", ns.naechste_ausgabe_text(dt.date(2026, 9, 22)),
                         "das Jahr ist in der Fußzeile Rauschen")

    def test_terminzeile_ist_ruecklesbar(self):
        start = dt.date(2026, 12, 25)   # über den Jahreswechsel
        for i in range(14):
            d = start + dt.timedelta(days=i)
            erkannt = ns.datum_lang_erkennen("Nächste Ausgabe: " + ns.datum_lang(d))
            with self.subTest(datum=d.isoformat()):
                self.assertEqual((ns.wochentag(d), d.day, d.month, d.year),
                                 (erkannt["wochentag"], erkannt["tag"],
                                  erkannt["monat"], erkannt["jahr"]))
        self.assertIsNone(ns.datum_lang_erkennen("demnächst"))
        self.assertIsNone(ns.datum_lang_erkennen(""))

    def test_versandtexte_kommen_aus_dem_vertrag(self):
        self.assertEqual("Dienstag und Freitag", ns.versandtage_text())
        self.assertEqual("dienstags und freitags", ns.versandtage_adverb())
        fenster = ns.versandfenster_text()
        self.assertIn("dienstags und freitags", fenster)
        self.assertIn(ns.SEND_UHRZEIT.strftime("%H:%M"), fenster)
        self.assertIn("höchstens zwei Ausgaben", fenster)
        self.assertIn("dienstags und freitags", ns.versandpause({}, zeit("2026-09-23")))


class WebsiteSnapshot(unittest.TestCase):
    """Der Snapshot für die Website ist der Vertrag – keine vierte Fassung.

    `layouts/_partials/newsletter_versandplan.html` druckt die Fakten der
    Kadenz (Tage, Uhrzeit, Obergrenze) in den Anmeldekasten. Hugo kann den
    Vertrag nicht aufrufen, also schreibt der Vertrag eine Datei. Zwei Prüfungen
    halten sie ehrlich: Inhalt == Vertrag, und kein Kalenderdatum darin – ein
    gedruckter „nächster Termin“ wäre am Tag nach dem Bau falsch.
    """

    def test_snapshot_ist_der_vertrag(self):
        self.assertEqual(ns.site_kadenz_text(),
                         (ROOT / ns.SITE_KADENZ_REL).read_text(encoding="utf-8"),
                         "data/newsletter_kadenz.json weicht vom Versandvertrag ab – "
                         "`python3 scripts/newsletter_schedule.py --export-site`")

    def test_snapshot_nennt_genau_die_versandtage(self):
        roh = json.loads(ns.site_kadenz_text())
        self.assertEqual([int(t["schluessel"]) for t in roh["tage"]], list(ns.VERSANDTAGE))
        for eintrag in roh["tage"]:
            tag = int(eintrag["schluessel"])
            self.assertEqual(ns.WOCHENTAGE[tag], eintrag["tag"])
            self.assertEqual(ns.WOCHENTAGE[tag][:2], eintrag["tag_kurz"])
            self.assertEqual(ns.WOCHENTAGE_ADVERB[tag], eintrag["adverb"])
        self.assertEqual(ns.MAX_PRO_WOCHE, roh["max_pro_woche"])
        self.assertEqual(ns.SEND_UHRZEIT.strftime("%H:%M"), roh["uhrzeit"])
        self.assertEqual(ns.versandfenster_text(), roh["versandfenster"])

    def test_uhrzeiten_sind_gerechnet_nicht_abgeschrieben(self):
        """05:05 UTC ist 07:05 MESZ und 06:05 MEZ – derselbe Termin, zwei Zonen."""
        self.assertEqual(dt.time(5, 5), ns.send_uhrzeit_utc())
        self.assertEqual(dt.time(6, 5), ns.send_uhrzeit_winter())
        self.assertIn("07:05", ns.uhrzeit_zeile())
        self.assertIn("06:05", ns.uhrzeit_zeile())

    def test_snapshot_traegt_kein_kalenderdatum(self):
        roh = json.dumps(json.loads(ns.site_kadenz_text()), ensure_ascii=False)
        # Selbsttest der Prüfung: ein ISO-Datum MUSS gefunden werden.
        self.assertRegex('"datum": "2026-09-29"', r"\d{4}-\d{2}-\d{2}")
        self.assertNotRegex(roh, r"\d{4}-\d{2}-\d{2}",
                            "ein ISO-Datum im Snapshot altert über Nacht")
        self.assertNotRegex(roh, r"Nächste Ausgabe|Nächster Termin",
                            "den nächsten Termin rechnet der Browser, nicht der Build")

    def test_cli_schreibt_und_prueft(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(1, ns.main(["--root", tmp, "--pruefen-site"]),
                             "fehlender Snapshot muss ein Befund sein")
            self.assertEqual(0, ns.main(["--root", tmp, "--export-site"]))
            self.assertEqual(0, ns.main(["--root", tmp, "--pruefen-site"]))
            pfad = Path(tmp) / ns.SITE_KADENZ_REL
            self.assertEqual(ns.site_kadenz_text(), pfad.read_text(encoding="utf-8"))
            pfad.write_text("{kaputt", encoding="utf-8")
            self.assertEqual(1, ns.main(["--root", tmp, "--pruefen-site"]),
                             "Drift muss rot werden, sonst sendet die Site einen anderen Takt")


class Versandpfad(unittest.TestCase):
    """Die Fail-Closed-Tore des neuen Versands (Worker + Actions):

    * Halt („versand_unklar“) blockiert den Listen-Versand – nicht die Suche
      nach dem Beleg (Testversand),
    * Terminreservierung verbräucht den Tag, doppelte Ausführung bleibt aus,
    * ein unlesbarer Versandstatus sperrt statt zu raten,
    * Ruhtage senden nichts und rühren keinen Zustand an.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        nd.speichere_state(self.root, {})
        self.env = patch.dict('os.environ', {'RESEND_API_KEY': 'test-key',
                                             'NEWSLETTER_TRANSPORT': 'dryrun'})
        self.env.start()
        self.addCleanup(self.env.stop)
        # Temp-Root ist kein Git-Worktree – der Schutz gilt im echten Lauf,
        # hier wird er ausgesetzt, damit die TORE (Halt/Kadenz/Status) gemessen
        # werden können.
        self.aw = patch.object(nd, 'assert_worktree')
        self.aw.start()
        self.addCleanup(self.aw.stop)

    def test_halt_blokt_den_listenversand(self):
        """Ein unbelegbarer Sende-Aufruf darf keine zweite Liste auslösen."""
        nd.sperre_setzen(self.root, "2026-09-22|Betreff", "Betreff")
        self.assertIn("versand_unklar", nd.sperre_pruefen(self.root))
        mit_zu = patch.object(ns, 'jetzt', return_value=zeit('2026-09-22', 12))
        with mit_zu, patch.object(nd.versand, 'sende_datei') as sende, \
             patch.object(nd.versand, 'worker_abfrage') as abfrage:
            self.assertEqual(1, nd.main(['--root', self.root, '--build', '--send',
                                         '--live', '--trotz-qa']))
            sende.assert_not_called()
            abfrage.assert_not_called()

    def test_halt_blokt_keinen_testversand(self):
        """Die Suche nach dem Beleg darf der Halt nicht verbieten."""
        nd.sperre_setzen(self.root, "2026-09-22|Betreff", "Betreff")
        artikel = [{'slug': 's1', 'titel': 'T', 'beschreibung': 'B',
                    'url': '/posts/s1/', 'path': '', 'datum': '2026-09-22',
                    'pillar': 'strom-sparen', 'quelle_text': 'Q'}]
        ausgabe = {'html': '<p>x</p>', 'text': 'x', 'anzahl': 1,
                   'betreff': 'Betreff', 'preheader': '', 'material': artikel}
        konf = {'email': {}, 'capture': {'form_action': 'https://abos.test'},
                'design': {'hell': {}, 'dunkel': {}}}
        pruef = {'bestanden': True, 'score': 100, 'regeln_geprueft': 21,
                 'funde': [], 'warnungen': []}
        with patch.object(nd, 'live_artikel', return_value=artikel), \
             patch.object(nd, 'baue_ausgabe', return_value=ausgabe), \
             patch.object(nd.studio, 'konfiguration', side_effect=lambda *a, **k: konf), \
             patch.object(nd.qa, 'pruefe', return_value=pruef), \
             patch.object(nd.versand, 'sende_datei', return_value=0) as sende:
            self.assertEqual(0, nd.main(['--root', self.root, '--build', '--send',
                                         '--test-adresse', 'probe@example.test',
                                         '--trotz-qa']))
            sende.assert_called_once()
        # und nach dem Testversand ist der Halt nach wie vor gesetzt –
        # auflösen ist eine MENSCHENAufgabe, kein Seiteneffekt.
        self.assertIn("versand_unklar", nd.sperre_pruefen(self.root))

    def test_reservierung_verbraucht_den_termin(self):
        """Selbst ein abgebrochener Lauf darf den Tag nicht zurückgeben."""
        mit_zu = patch.object(ns, 'jetzt', return_value=zeit('2026-09-22'))
        mit_zu.start()
        self.addCleanup(mit_zu.stop)
        nd.termin_reservieren(self.root)
        nd.termin_reservieren(self.root)
        state = nd.lade_state(self.root)
        self.assertEqual(2, len(state['versand_termine']))
        self.assertIn("bereits", ns.versandpause(state, zeit('2026-09-22', 12)))

    def test_ruhetag_sendet_nichts_und_ruhrt_keinen_zustand_an(self):
        vorher = (Path(self.root) / nd.STATE_REL).read_text()
        with patch.object(ns, 'jetzt', return_value=zeit('2026-09-23')), \
             patch.object(nd.versand, 'sende_datei') as sende, \
             patch.object(nd.versand, 'worker_abfrage') as abfrage:
            self.assertEqual(0, nd.main(['--root', self.root, '--build', '--send',
                                         '--live', '--trotz-qa']))
            sende.assert_not_called()
            abfrage.assert_not_called()
        self.assertEqual(vorher, (Path(self.root) / nd.STATE_REL).read_text())

    def test_defekter_status_sperrt_den_liveversand(self):
        pfad = Path(self.root) / nd.STATE_REL
        pfad.write_text('{kaputt', encoding='utf-8')
        with patch.object(nd.versand, 'sende_datei') as sende:
            self.assertEqual(1, nd.main(['--root', self.root, '--build', '--send',
                                         '--live', '--trotz-qa']))
            sende.assert_not_called()
        # und der defekte Status bleibt defekt – still reparieren wäre ein
        # Versteck, in dem der Duplikatsschutz stirbt.
        self.assertEqual('{kaputt', pfad.read_text(encoding='utf-8'))

    def test_fehlender_status_sperrt_den_liveversand(self):
        (Path(self.root) / nd.STATE_REL).unlink()
        with patch.object(nd.versand, 'sende_datei') as sende:
            self.assertEqual(1, nd.main(['--root', self.root, '--build', '--send',
                                         '--live', '--trotz-qa']))
            sende.assert_not_called()

    def test_kadenz_pruefen_liest_strikt(self):
        nd.speichere_state(self.root, {'versand_termine': [zeit('2026-09-22').isoformat()]})
        with patch.object(ns, 'jetzt', return_value=zeit('2026-09-22', 12)):
            self.assertIn("bereits", nd.kadenz_pruefen(self.root) or "")
        (Path(self.root) / nd.STATE_REL).write_text('[]', encoding='utf-8')
        with self.assertRaises(ValueError):
            nd.kadenz_pruefen(self.root)

    def test_sperre_setzen_und_aeufern(self):
        nd.sperre_setzen(self.root, "kennung-x", "Betreff X")
        meldung = nd.sperre_pruefen(self.root)
        self.assertIn("kennung-x", meldung)
        state = nd.lade_state(self.root)
        del state['versand_unklar']
        nd.speichere_state(self.root, state)
        self.assertEqual('', nd.sperre_pruefen(self.root))

if __name__ == '__main__':
    unittest.main()
