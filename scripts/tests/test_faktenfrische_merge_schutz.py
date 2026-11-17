"""Faktenfrische: echte Git-Konflikte statt stiller Text-Zusammenschnitte.

Die Zusammenführung 043978da/525d00c1 vermischte vier Elternartefakte, teils
ohne Konfliktmarker. Diese Tests betreiben Git in isolierten Test-Repositories;
sie prüfen nicht bloß, dass die Wörter ``merge=binary`` in einem Kommentar stehen.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import faktenfrische_befund_ledger as ledger  # noqa: E402


class FaktenfrischeMergeSchutz(unittest.TestCase):
    def test_auseinanderlaufende_ganzdateien_erzeugen_konflikt(self):
        attribute = (ROOT / ".gitattributes").read_text(encoding="utf-8")
        pfade = (
            "data/faktenfrische_queue.json",
            "data/faktenfrische_entscheidungen.yaml",
            "data/faktenfrische_befunde_1072.yaml",
            "data/faktenfrische_befunde_state.json",
            "data/faktenfrische_merge_quarantaene_2026-11-13.json",
            "BEFUND-AKTE.md",
            "F4-ENTSCHEIDUNGSVORLAGE.md",
            "content/posts/2026-11-13-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu/index.md",
            "content/posts/2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar/index.md",
            "content/posts/2026-11-11-kreditkarte-ohne-jahresgebuehr-die-besten-kostenlosen-karten/index.md",
        )
        for pfad in pfade:
            with self.subTest(pfad=pfad), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)

                def git(*args, check=True):
                    return subprocess.run(
                        ["git", *args], cwd=root, check=check, capture_output=True,
                        text=True, timeout=20, env=dict(os.environ,
                            GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1"))

                git("init", "-q", "-b", "base")
                git("config", "user.name", "Test")
                git("config", "user.email", "test@example.org")
                (root / ".gitattributes").write_text(attribute, encoding="utf-8")
                datei = root / pfad
                datei.parent.mkdir(parents=True, exist_ok=True)
                basis = "erste Zeile\nMitte\nletzte Zeile\n"
                version_a = "A-Änderung\nMitte\nletzte Zeile\n"
                version_b = "erste Zeile\nMitte\nB-Änderung\n"
                datei.write_text(basis, encoding="utf-8")
                git("add", ".")
                git("commit", "-qm", "Basis")
                git("branch", "other")
                datei.write_text(version_a, encoding="utf-8")
                git("commit", "-qam", "A")
                git("checkout", "-q", "other")
                datei.write_text(version_b, encoding="utf-8")
                git("commit", "-qam", "B")
                result = git("merge", "base", "--no-edit", check=False)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(pfad, git("diff", "--name-only", "--diff-filter=U").stdout)
                self.assertEqual(git("show", f":2:{pfad}").stdout, version_b)
                self.assertEqual(git("show", f":3:{pfad}").stdout, version_a)

    def test_gleiche_aenderungen_duerfen_zusammenfallen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")

            def git(*args):
                return subprocess.run(["git", *args], cwd=root, check=True,
                                      capture_output=True, text=True, env=env, timeout=20)

            git("init", "-q", "-b", "base")
            git("config", "user.name", "Test")
            git("config", "user.email", "test@example.org")
            (root / ".gitattributes").write_text((ROOT / ".gitattributes").read_text(), encoding="utf-8")
            p = root / "data/faktenfrische_queue.json"
            p.parent.mkdir()
            p.write_text('{"version": 1}\n')
            git("add", ".")
            git("commit", "-qm", "Basis")
            git("branch", "other")
            p.write_text('{"version": 2}\n')
            git("commit", "-qam", "A")
            git("checkout", "-q", "other")
            p.write_text('{"version": 2}\n')
            git("commit", "-qam", "B")
            git("merge", "base", "--no-edit")
            self.assertEqual(p.read_text(), '{"version": 2}\n')


class WiederhergestellteBelege(unittest.TestCase):
    def test_konkurrierende_ketten_bleiben_nachvollziehbar_und_inaktiv(self):
        archiv = json.loads((ROOT / "data/faktenfrische_merge_quarantaene_2026-11-13.json").read_text(encoding="utf-8"))
        self.assertIn("inaktiv", archiv["status"])
        self.assertEqual(archiv["zweigfassung"]["commit"], "0736e10fc6039bc45397fe616e3bd71133416db5")
        self.assertEqual(archiv["mainfassung"]["commit"], "becd6332cd5ef6d3e8c49d0955a14254897d4306")
        zweig = archiv["konkurrierende_entscheidungen"]
        self.assertEqual(len(zweig), 6)
        self.assertEqual(len(archiv["aeltere_registerfassungen"]), 14)
        self.assertEqual(len(archiv["aelterer_arbeitsvorrat_nicht_in_main"]), 7)
        self.assertEqual(len(archiv["aeltere_laeufe_nicht_in_main"]), 5)
        snapshot = archiv["aelterer_status_snapshot"]
        self.assertEqual(snapshot["stichtag"], "2026-11-11")
        self.assertEqual(snapshot["offen"], len(snapshot["befunde"]))
        self.assertEqual(snapshot["offen"], 148)
        # Nach Datums-Lifts steht derselbe Befund im Snapshot unter einem
        # anderen Slug als in der Queue. Die ID bleibt über alle Lifts stabil;
        # alle alten Snapshot-IDs müssen als Fachbefund erhalten sein.
        queue = json.loads((ROOT / "data/faktenfrische_queue.json").read_text(encoding="utf-8"))
        bekannte_ids = (
            {b["id"] for b in queue["fachbefunde"]}
            | {b["id"] for b in (queue.get("ausgemusterte_entwurfsbefunde") or [])}
        )
        self.assertTrue({b["id"] for b in snapshot["befunde"]} <= bekannte_ids)
        for lauf in archiv["aeltere_laeufe_nicht_in_main"]:
            for befund in lauf["befunde"]:
                self.assertIn(ledger.befund_id(lauf["slug"], befund), bekannte_ids)
        # Die archivierte Kette ist für sich gültig; sie ist NICHT durch einen
        # erfundenen Vorgänger mit der parallelen aktiven Kette verbunden.
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / "entscheidungen.yaml"
            datei.write_text(yaml.safe_dump({"entscheidungen": zweig}, allow_unicode=True), encoding="utf-8")
            self.assertEqual(len(ledger.entscheidungen_laden(datei)), 3)
        aktiv = ledger._laden_streng(ROOT / "data/faktenfrische_entscheidungen.yaml")["entscheidungen"]
        signatur = lambda e: (e["slug"], e["befund_id"], e["geprueft_fassung"])
        self.assertTrue({signatur(e) for e in zweig}.isdisjoint({signatur(e) for e in aktiv}))
        self.assertTrue({(e["slug"], e["befund_id"]) for e in zweig}
                        <= {(e["slug"], e["befund_id"]) for e in aktiv})

    def test_pr1205_heizoel_folgeentscheidungen_sind_belegt_wiederhergestellt(self):
        archiv = json.loads((ROOT / "data/faktenfrische_merge_quarantaene_2026-11-13.json").read_text(encoding="utf-8"))
        nachtrag = archiv["nachtrag_pr_1207"]
        self.assertEqual(nachtrag["belegte_vorversion_heizoel"],
                         "8c2c80ac6d72c0f84e326ab7b114533f4c2dbe88")
        alt = archiv["heizoel_vor_1205_registerfassungen"]
        self.assertEqual(len(alt), 5)
        self.assertEqual({e["entschieden_am"] for e in alt}, {"2026-11-05"})
        register = ledger._laden_streng(ROOT / "data/faktenfrische_befunde_1072.yaml")
        aktiv = {e["id"]: e for e in register["befunde"]}
        entscheidungen = ledger._laden_streng(ROOT / "data/faktenfrische_entscheidungen.yaml")["entscheidungen"]
        slug = "2026-11-13-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu"
        # #1214 brachte fünf spätere Fassungen für jeden Befund. Sie dürfen
        # ebenso wenig verloren gehen wie die ursprüngliche Entscheidung aus
        # #1205; zusätzliche künftige Folgeentscheidungen bleiben erlaubt.
        belegte_fassungen = [
            "ce7dd8c5ef0a596abbc4628c7be2878fc8ef9ded0c9acbbf3ff7cb29bc1ed602",
            "11998806d0a17653427b55e144556161f0f080b2d17274aa7e1ff84a931398be",
            "75aac42397b3ed6b4bbcd0d201682cd6df3d57d4965bd9b963cce808336857de",
            "9d2c211e9d46d3be43326a3cbd6317678d55cbf17dc5eb82680cc6fce2967849",
            "6ac3696f40db0786dbaf9e3d23eef5288b0fb2b7107d3de9b05cfbf5f7cb2c01",
            "28af839d6e5dfff3b780343158e19322fedeba4430e6e129604b41d566224229",
        ]
        letzte = ledger.entscheidungen_laden()
        queue = json.loads((ROOT / "data/faktenfrische_queue.json").read_text(encoding="utf-8"))
        for befund_id in {e["id"] for e in alt}:
            with self.subTest(befund_id=befund_id):
                kette = [e for e in entscheidungen if e.get("slug") == slug
                         and e.get("befund_id") == befund_id]
                self.assertEqual([e["geprueft_fassung"] for e in kette[:6]], belegte_fassungen)
                for index, eintrag in enumerate(kette[1:6], start=1):
                    self.assertIs(eintrag.get("folgeentscheidung"), True)
                    self.assertEqual(eintrag.get("vorgaenger_geprueft_fassung"),
                                     belegte_fassungen[index - 1])
                aktuell = aktiv[befund_id]
                self.assertEqual(aktuell["geprueft_fassung"],
                                 letzte[(slug, befund_id)]["geprueft_fassung"],
                                 "Die Registerfassung muss die letzte belegte Entscheidung nennen")
                # Die FINDUNG stammt von einer älteren Fassung als der zuletzt
                # geprüfte Text. #1214 überschrieb versehentlich den Queue-
                # Hash im Register mit dem Hash der Folgeentscheidung. Beide
                # Seiten der Provenienz müssen unabhängig erhalten bleiben.
                funde = [b for b in queue["fachbefunde"] if b["id"] == befund_id]
                self.assertEqual(len(funde), 1, "Befund muss eindeutig in der Queue stehen")
                self.assertEqual(funde[0]["slug"], kette[0]["befund_ursprung_slug"])
                ursprung = "c13cf12ed8da9b5f194b07f6e0788c810acaeedded9cd17db2b598bfc6b20546"
                self.assertEqual([e["befund_fassung"] for e in kette[:6]], [ursprung] * 6)
                self.assertEqual(aktuell["ledger_fassung_sha256"], funde[0]["fassung_sha256"],
                                 "Register-Befundfassung darf nicht mit Prüffassung verwechselt werden")
                if aktuell["geprueft_fassung"] == belegte_fassungen[0]:
                    self.assertEqual(aktuell["belegtyp"], "streichung")
                    self.assertIsNone(aktuell["beleg_url"])

    def test_aeltere_uebersichtsbefunde_bleiben_ueber_alias_erhalten(self):
        archiv = json.loads((ROOT / "data/faktenfrische_merge_quarantaene_2026-11-13.json").read_text(encoding="utf-8"))
        queue = json.loads((ROOT / "data/faktenfrische_queue.json").read_text(encoding="utf-8"))
        alte_slugs = {
            "2026-11-10-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu",
            "2026-11-10-strompreis-2026-herbst-check-fuer-deine-stromkosten",
        }
        alte_uebersicht = archiv["aelterer_queue_kopf"]["uebersicht"]["fachbefunde"]
        nachtraege = [b for b in alte_uebersicht if b["slug"] in alte_slugs]
        self.assertEqual(len(nachtraege), 10)
        aktuell = {b["id"]: b for b in queue["fachbefunde"]}
        _, aliases = ledger.bestand_identitaeten()
        for alt in nachtraege:
            with self.subTest(id=alt["id"]):
                self.assertIn(alt["id"], aktuell)
                top = aktuell[alt["id"]]
                self.assertEqual(top["slug"], alt["ursprungs_slug"])
                self.assertEqual(top["text"], alt["text"])
                self.assertEqual(top["fassung_sha256"], alt["fassung_sha256"])
                self.assertEqual(ledger.canonical_slug(top["slug"], aliases),
                                 ledger.canonical_slug(alt["slug"], aliases))

    def test_pr_workflows_laufen_auch_bei_reinen_faktenfrische_aenderungen(self):
        workflow = (ROOT / ".github/workflows/publication-reliability-tests.yml").read_text(encoding="utf-8")
        self.assertIn("'data/faktenfrische_*'", workflow)
        self.assertIn("'BEFUND-AKTE.md'", workflow)
        self.assertIn("'F4-ENTSCHEIDUNGSVORLAGE.md'", workflow)
        gate = (ROOT / ".github/workflows/integrity-lock.yml").read_text(encoding="utf-8")
        self.assertIn("scripts.tests.test_faktenfrische_merge_schutz", gate)


if __name__ == "__main__":
    unittest.main()
