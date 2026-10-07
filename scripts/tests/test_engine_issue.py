"""Der Zustandskanal `engine-deficit` – Besitz, Kadenz, Schließpfad.

Vorfall WF-1F8C #608 (06.10.2026): Der 05.10. endete mit 1/2 LIVE. Das
Fach-Issue #601 existierte korrekt, wurde aber um 21:21 durch den
Reparatur-Merge #603 geschlossen („Closes #601“) – der gemessene Tag blieb
rot. Am 06.10. (Dienstag) übersprang `engine_issue.py` den Tag vollständig
(„Kein Publikationstag“), es gab also keinen offenen, frischen Fachkanal.
Der um 00:55 UTC nachgelieferte Montags-Slot der Kadenz-Endkontrolle meldete
daraufhin ehrlich rot („TAGESDEFIZIT – Fachmeldung engine-deficit ist
zuständig“), und das zentrale Fehler-Alerting musste fail-open ein
generisches Wartungs-Issue mit API-Key-Runbook anlegen: #608.

Diese Datei ist die Wache, dass die Reparatur nicht still zurückgebaut wird:

  A. MESSUNG: Gemessen wird immer der jüngste Publikationstag
     (`cadence_guard.letzter_publikationstag`) – an Ruhetagen wie an
     Publikationstagen. Kein Tagesausfall, kein „Kein Publikationstag“-Sprung.
  B. BESITZ: Der Kanal wird von seiner eigenen Messung geführt. Geschlossen
     wird nur, wenn das Ziel erreicht ist – und der Vermerk sagt, ob der
     Fehltag nachgeholt wurde (er wurde es nie) oder nicht.
  C. REOPEN: Ein Kanal, der rot geschlossen wurde, wird wieder geöffnet.
     Ein Zustand endet nicht durch einen Merge.
  D. KADENZ: Der Kanal wird an JEDEM Tag belegt – an Ruhetagen von der
     Produktions-Wache (20:00 UTC), an Publikationstagen von Engine und
     Kadenz-Endkontrolle.
  E. VERHALTEN: `abgleichen()` wird mit gestubbtem GitHub wirklich
     ausgeführt (öffnen, belegen, wieder öffnen, schließen, still bleiben).
"""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

import cadence_guard as cg          # noqa: E402
import engine_issue as ei           # noqa: E402

MO = dt.date(2026, 10, 5)   # Montag, Publikationstag (1/2 LIVE → Defizittag)
DI = dt.date(2026, 10, 6)   # Dienstag, Ruhetag
MI = dt.date(2026, 10, 7)   # Mittwoch, Publikationstag
DO = dt.date(2026, 10, 8)   # Donnerstag, Ruhetag


def posts(*tage):
    """Minimaler Bestand: ein LIVE-Post je Datum."""
    return [{"draft": False, "date": t, "slug": f"2026-10-{i:02d}-post"}
            for i, t in enumerate(tage)]


class KanalVertragLesen(unittest.TestCase):
    """Verträge am Quelltext – die Zusagen stehen im Code, nicht im Kommentar."""

    def setUp(self):
        self.quelle = (REPO / "scripts" / "engine_issue.py").read_text(
            encoding="utf-8")

    def test_messung_nutzt_die_kalender_ssot(self):
        self.assertIn("letzter_publikationstag", self.quelle,
                      "Die Messung muss den jüngsten Publikationstag der "
                      "Kalender-SSOT verwenden (#608)")

    def test_kein_ruhetag_sprung_mehr(self):
        """Der alte Kurzschluss („Kein Publikationstag – übersprungen“) darf
        nicht zurückkehren: Er war die Lücke, durch die #608 entstand."""
        self.assertNotIn("Kein Publikationstag – Defizit-Wache übersprungen",
                         self.quelle)
        self.assertNotIn("if today.weekday() not in cg.PUBLICATION_DAYS",
                         self.quelle)

    def test_reopen_pfad_ist_im_code(self):
        self.assertIn("wieder_oeffnen", self.quelle)
        self.assertIn("issue\", \"reopen\"", self.quelle.replace("'", '"'))

    def test_schliesspfad_ist_die_eigene_messung(self):
        self.assertIn("schluss_kommentar", self.quelle)
        self.assertIn("nachgeholt", self.quelle,
                      "Der Schließvermerk muss die Nicht-Nachholbarkeit "
                      "aussprechen (Ehrlichkeits-Doktrin)")

    def test_identitaet_bleibt_marker_und_label(self):
        # Das zentrale Fehler-Alerting dedupliziert über GENAU diese zwei
        # Signale; wer sie ändert, macht die Stummschaltung blind.
        self.assertIn('MARKER = "<!-- engine-deficit-id: tagesdefizit -->"',
                      self.quelle)
        self.assertIn('LABEL = "engine-deficit"', self.quelle)


class Messung(unittest.TestCase):
    """Vertrag A: gemessener Tag und Zustand – an jedem Wochentag."""

    def test_publikationstag_offen_und_erfuellt(self):
        offen = ei.quoten_lage(MO, posts(MO), 2)
        self.assertEqual((offen["tag"], offen["n"], offen["zustand"]),
                         (MO, 1, ei.ZUSTAND_OFFEN))
        gruen = ei.quoten_lage(MO, posts(MO, MO), 2)
        self.assertEqual(gruen["zustand"], ei.ZUSTAND_ERFUELLT)

    def test_ruhetag_misst_den_letzten_publikationstag(self):
        """Der Kernfall #608: Dienstag, Montag rot → verbucht, nicht „kein Tag“."""
        lage = ei.quoten_lage(DI, posts(MO), 2)
        self.assertEqual(lage["tag"], MO)
        self.assertEqual(lage["zustand"], ei.ZUSTAND_VERBUCHT)
        self.assertFalse(lage["publikationstag_heute"])

    def test_ruhetag_nach_gruenem_tag_ist_erfuellt(self):
        self.assertEqual(ei.quoten_lage(DI, posts(MO, MO), 2)["zustand"],
                         ei.ZUSTAND_ERFUELLT)
        self.assertEqual(ei.quoten_lage(DO, posts(MI, MI), 2)["zustand"],
                         ei.ZUSTAND_ERFUELLT)

    def test_ruhetag_nach_rotem_tag_bleibt_verbucht(self):
        self.assertEqual(ei.quoten_lage(DO, posts(MI), 2)["zustand"],
                         ei.ZUSTAND_VERBUCHT)
        self.assertEqual(ei.quoten_lage(DO, posts(MI), 2)["tag"], MI)

    def test_kein_backdating_im_modell(self):
        """Ein später gemessener Tag darf den Fehltag nicht ersetzen: Am
        Mittwoch mit 2/2 verschwindet der rote Montag nicht aus dem Report."""
        lage = dict(ei.quoten_lage(MI, posts(MI, MI), 2), _posts=posts(MI, MI))
        tage = [t for t, _ in ei.rueckstand_zeilen(lage)]
        self.assertIn(MO, tage)

    def test_zustand_ist_unabhaengig_von_der_wanduhr(self):
        """Zweimal messen = zweimal dasselbe (Selbsttest-Uhr-Vertrag)."""
        a = ei.quoten_lage(DI, posts(MO), 2)
        b = ei.quoten_lage(DI, posts(MO), 2)
        self.assertEqual(a, b)


class Entscheidung(unittest.TestCase):
    """Vertrag B/C: was mit einem Kanal geschieht."""

    def setUp(self):
        self.rot = ei.quoten_lage(DI, posts(MO), 2)
        self.gruen = ei.quoten_lage(MI, posts(MI, MI), 2)
        self.offen = {"nummer": 601, "tag": MO}
        self.geschlossen = {"nummer": 601, "tag": MO}

    def test_kein_defizit_kein_betrieb(self):
        beschluss = ei.urteil(self.gruen, None, None)
        self.assertEqual(beschluss["aktion"], "nichts")

    def test_rot_mit_offenem_kanal_wird_belegt(self):
        self.assertEqual(ei.urteil(self.rot, self.offen, None)["aktion"],
                         "kommentieren")

    def test_rot_ohne_kanal_legt_an(self):
        self.assertEqual(ei.urteil(self.rot, None, None)["aktion"], "oeffnen")

    def test_rot_geschlossen_wird_wieder_geoeffnet(self):
        """Genau #601: geschlossen am 21:21, gemessener Tag blieb rot."""
        self.assertEqual(ei.urteil(self.rot, None, self.geschlossen)["aktion"],
                         "wieder_oeffnen")

    def test_geschlossener_altkanal_wird_nicht_wiederbelebt(self):
        alt = {"nummer": 500, "tag": dt.date(2026, 9, 30)}
        self.assertEqual(ei.urteil(self.rot, None, alt)["aktion"], "oeffnen")

    def test_erfuellt_schliesst_mit_dem_richtigen_vermerk(self):
        am_tag = ei.urteil(dict(self.gruen, tag=MI), {"nummer": 1, "tag": MI}, None)
        self.assertEqual(am_tag["aktion"], "schliessen")
        self.assertFalse(am_tag["wieder_erreicht"])
        spaeter = ei.urteil(dict(self.gruen, tag=MI), {"nummer": 1, "tag": MO}, None)
        self.assertTrue(spaeter["wieder_erreicht"],
                        "Ein Kanal zu einem ÄLTEREN Fehltag ist ein verbuchtes "
                        "Defizit – der Vermerk muss das sagen")


class Wortlaut(unittest.TestCase):
    """Vertrag B: der Text ist Teil des Vertrags (Marker, Titel, Vermerke)."""

    def setUp(self):
        self.lage = dict(ei.quoten_lage(DI, posts(MO), 2), _posts=posts(MO))

    def test_body_traegt_den_tagesmarker(self):
        body = ei.koerper(self.lage)
        self.assertIn(ei.TAG_MARKER.format(tag=MO.isoformat()), body)
        self.assertEqual(ei.tag_aus_body(body), MO)

    def test_altbestand_ohne_marker_wird_erkannt(self):
        """#601 wurde von der Vorgängerversion angelegt – ohne Marker wäre das
        Wiederöffnen ein zweiter Kanal geworden."""
        alt = (f"{ei.MARKER}\n\n## Content-Engine: LIVE unter Mindestziel\n\n"
               f"- **Tag:** 2026-10-05\n- **LIVE heute:** 1 (Ziel ≥ 2)\n")
        self.assertEqual(ei.tag_aus_body(alt), MO)

    def test_titel_nennt_tag_quote_und_zustand(self):
        self.assertEqual(ei.titel(self.lage),
                         "Content-Engine: Tagesdefizit 2026-10-05 (1/2 LIVE) "
                         "– nicht nachholbar")
        gruen = dict(ei.quoten_lage(MO, posts(MO), 2))
        self.assertEqual(ei.titel(gruen),
                         "Content-Engine: Tagesdefizit 2026-10-05 (1/2 LIVE)")

    def test_schliessvermerk_verspricht_kein_nachholen(self):
        lage = dict(ei.quoten_lage(MI, posts(MI, MI), 2), _posts=posts(MI, MI),
                    _offen_tag=MO)
        text = ei.schluss_kommentar(lage)
        self.assertIn("nicht", text)
        self.assertIn("nachgeholt", text)
        self.assertIn("verbucht", text)

    def test_schliessvermerk_am_tag_selbst(self):
        lage = dict(ei.quoten_lage(MO, posts(MO, MO), 2), _posts=posts(MO, MO),
                    _offen_tag=MO)
        self.assertIn("Ziel erreicht", ei.schluss_kommentar(lage))

    def test_reopen_vermerk_begruendet_und_markiert(self):
        text = ei.reopen_kommentar(self.lage, "21:21")
        self.assertIn(ei.REOPEN_MARKER.format(tag=MO.isoformat()), text)
        self.assertIn("Wieder offen", text)
        self.assertIn("Messwert", text,
                      "Der Vermerk muss erklären, dass ein Merge keinen "
                      "Messwert heilt")

    def test_zustandszeile_ist_ein_frischebeweis_mit_inhalt(self):
        zeile = ei.zustandszeile(self.lage)
        for erwartet in ("2026-10-06", "2026-10-05", "1/2 LIVE", "verbucht"):
            self.assertIn(erwartet, zeile)


class AbgleichVerhalten(unittest.TestCase):
    """Vertrag E: die Zustandsmaschine wird wirklich ausgeführt (GitHub gestubbt)."""

    def setUp(self):
        self.aufrufe: list[tuple] = []

    def _stub(self, offen=None, geschlossen=None):
        def gh(*args):
            self.aufrufe.append(args)
            if args[:2] == ("label", "list"):
                return subprocess.CompletedProcess(args, 0, "engine-deficit\n", "")
            if args[:2] == ("issue", "list"):
                zustand = args[args.index("--state") + 1]
                eintrag = offen if zustand == "open" else geschlossen
                daten = [] if eintrag is None else [eintrag]
                return subprocess.CompletedProcess(args, 0, json.dumps(daten), "")
            if args[0] == "issue" and args[1] == "view":
                return subprocess.CompletedProcess(args, 0, '{"title": "alt"}', "")
            if args[0] == "issue" and args[1] == "create":
                return subprocess.CompletedProcess(
                    args, 0, "https://github.com/x/y/issues/700", "")
            return subprocess.CompletedProcess(args, 0, "", "")
        return gh

    def _eintrag(self, nummer, tag):
        return {"number": nummer, "title": "t",
                "body": (f"{ei.MARKER}\n"
                         f"{ei.TAG_MARKER.format(tag=tag.isoformat())}\n")}

    def _aktionen(self):
        return [a[:2] for a in self.aufrufe if a[0] == "issue"
                and a[1] in ("create", "comment", "close", "reopen")]

    def test_ruhiger_zustand_erzeugt_keinen_betrieb(self):
        lage = dict(ei.quoten_lage(MI, posts(MI, MI), 2), _posts=posts(MI, MI))
        rc, meldung = ei.abgleichen(lage, gh=self._stub())
        self.assertEqual(rc, 0)
        self.assertEqual(self._aktionen(), [])
        self.assertIn("Kein Defizit", meldung)

    def test_ruhetag_belegt_den_offenen_kanal(self):
        """Ohne diesen Kommentar findet das Fehler-Alerting keinen FRISCHEN
        Fachkanal und meldet wieder generisch (#608)."""
        lage = dict(ei.quoten_lage(DI, posts(MO), 2), _posts=posts(MO))
        rc, _ = ei.abgleichen(lage, gh=self._stub(offen=self._eintrag(601, MO)))
        self.assertEqual(rc, 0)
        self.assertIn(("issue", "comment"), self._aktionen())
        self.assertNotIn(("issue", "create"), self._aktionen())

    def test_rot_geschlossen_wird_wieder_geoeffnet(self):
        lage = dict(ei.quoten_lage(DI, posts(MO), 2), _posts=posts(MO))
        rc, meldung = ei.abgleichen(
            lage, gh=self._stub(geschlossen=self._eintrag(601, MO)))
        self.assertEqual(rc, 0)
        self.assertEqual(self._aktionen(), [("issue", "reopen")])
        self.assertIn("wieder geöffnet", meldung)

    def test_neuer_defizittag_legt_neuen_kanal_an(self):
        lage = dict(ei.quoten_lage(DO, posts(MI), 2), _posts=posts(MI))
        rc, _ = ei.abgleichen(
            lage, gh=self._stub(geschlossen=self._eintrag(601, MO)))
        self.assertEqual(rc, 0)
        self.assertIn(("issue", "create"), self._aktionen())

    def test_erfuellter_tag_schliesst_den_kanal(self):
        lage = dict(ei.quoten_lage(MI, posts(MI, MI), 2), _posts=posts(MI, MI))
        rc, _ = ei.abgleichen(lage, gh=self._stub(offen=self._eintrag(601, MO)))
        self.assertEqual(rc, 0)
        self.assertIn(("issue", "close"), self._aktionen())

    def test_werkzeugfehler_ist_laut_und_nicht_gruen(self):
        """Kann der Kanal NICHT belegt werden, ist das ein Befund (C12-Klasse):
        Dann muss der Aufrufer es melden – sonst bleibt nur der generische
        Alarm, und niemand weiß warum."""
        def gh(*args):
            if args[:2] == ("label", "list"):
                return subprocess.CompletedProcess(args, 0, "engine-deficit\n", "")
            if args[:2] == ("issue", "list"):
                return subprocess.CompletedProcess(args, 0, "[]", "")
            return subprocess.CompletedProcess(args, 1, "", "API kaputt")
        lage = dict(ei.quoten_lage(DI, posts(MO), 2), _posts=posts(MO))
        rc, meldung = ei.abgleichen(lage, gh=gh)
        self.assertEqual(rc, 2)
        self.assertIn("nicht angelegt", meldung)

    def test_selbsttest_laeuft_gruen(self):
        r = subprocess.run([sys.executable, str(REPO / "scripts" / "engine_issue.py"),
                            "--selftest"], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_lage_trockenlauf_ohne_token(self):
        """`--lage` darf nie schreiben (kein Token nötig) – der Betreiber
        braucht den Zustand auch ohne Zugangsrecht."""
        r = subprocess.run([sys.executable, str(REPO / "scripts" / "engine_issue.py"),
                            "--lage"], capture_output=True, text=True, timeout=120,
                           env={"PATH": "/usr/bin:/bin"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('"zustand"', r.stdout)


class KadenzDurchAlleTage(unittest.TestCase):
    """Vertrag D: der Kanal wird JEDEN Tag belegt – sonst entsteht wieder #608."""

    def _workflow(self, name: str) -> str:
        return (REPO / ".github" / "workflows" / name).read_text(encoding="utf-8")

    def test_produktions_wache_belegt_den_kanal_taeglich(self):
        text = self._workflow("produktions-wache.yml")
        self.assertIn("engine_issue.py --deficit", text,
                      "Ohne den täglichen Beleg bleibt der Fachkanal an "
                      "Ruhetagen unbesetzt (#608)")
        self.assertRegex(text, r'cron:\s*"0 20 \* \* \*"',
                         "Der Beleg braucht einen täglichen Takt, nicht Mo/Mi/Fr")
        self.assertIn("env.LEVEL != 'WARTEND'", text,
                      "In der Fallback-Frist (WARTEND) darf nicht alarmiert "
                      "werden – die Slots laufen noch")

    def test_kadenz_endkontrolle_belegt_vor_der_klassifikation(self):
        text = self._workflow("kadenz-endkontrolle.yml")
        pos_beleg = text.find("engine_issue.py --deficit")
        pos_messung = text.find("publication_check.py")
        self.assertGreater(pos_beleg, -1)
        self.assertLess(pos_beleg, pos_messung,
                        "Der Kanal muss belegt sein, BEVOR der Lauf rot wird – "
                        "das Alerting liest ihn nach dem Lauf")

    def test_engine_phase4_ruft_die_wache_weiterhin(self):
        text = self._workflow("content-engine-v2.yml")
        self.assertIn("engine_issue.py --deficit", text)

    def test_wache_steht_in_gutachten_des_vertrags(self):
        governance = (REPO / "scripts" / "governance_contract.py").read_text(
            encoding="utf-8")
        self.assertIn("engine_issue.py", governance,
                      "Eine Wache, die niemand verlangt, führt irgendwann "
                      "niemand mehr aus (C6/C23)")


class KalenderSSOT(unittest.TestCase):
    """Die zweite Wahrheit ist verboten: Alle Melder fragen dieselbe Quelle."""

    def test_letzter_publikationstag_fuer_jeden_wochentag(self):
        erwartet = {MO: MO, DI: MO, MI: MI, DO: MI,
                    dt.date(2026, 10, 9): dt.date(2026, 10, 9),
                    dt.date(2026, 10, 10): dt.date(2026, 10, 9),
                    dt.date(2026, 10, 11): dt.date(2026, 10, 9)}
        for heute, soll in erwartet.items():
            self.assertEqual(cg.letzter_publikationstag(heute), soll)

    def test_publication_check_und_produktions_wache_nutzen_die_ssot(self):
        pc = (REPO / "scripts" / "publication_check.py").read_text(encoding="utf-8")
        self.assertIn("letzter_publikationstag", pc,
                      "publication_check darf keine zweite Kalenderlogik haben")

    def test_kalender_selbsttest_bleibt_gruen(self):
        r = subprocess.run([sys.executable, str(REPO / "scripts" / "cadence_guard.py"),
                            "--selftest"], capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Kalender-SSOT", r.stdout)


if __name__ == "__main__":
    unittest.main()
