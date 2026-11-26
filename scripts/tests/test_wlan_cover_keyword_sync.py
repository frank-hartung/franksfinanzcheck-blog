#!/usr/bin/env python3
"""Regression: 2026-09-27 WLAN-Titel, Keyword und Cover-Herkunft synchron (Run 45374581619)."""
from __future__ import annotations

import contextlib
import datetime as dt
import hashlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import cover_render_check as crc  # noqa: E402
import editorial_review_gate as erg  # noqa: E402
import generate_covers as gc  # noqa: E402
import keyword_optimizer as ko  # noqa: E402
import ki_cover_herkunft as kh  # noqa: E402
import serp_limits as sl  # noqa: E402

SLUG = "2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich"
KANONISCHER_TITEL = "WLAN-Verstärker vs. Mesh-WLAN: Was brauchst du wirklich?"
YMYL_ENTWURF = "2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert"


def _lese_frontmatter(pfad: Path) -> dict:
    inhalt = pfad.read_text(encoding="utf-8")
    _, fm_text, _ = inhalt.split("---", 2)
    return yaml.safe_load(fm_text)


class WlanCoverKeywordSyncTest(unittest.TestCase):
    def setUp(self):
        self.artikel_pfad = ROOT / "content" / "posts" / SLUG / "index.md"
        self.fm = _lese_frontmatter(self.artikel_pfad)

    def test_frontmatter_und_kannibalisierung_synchron(self):
        self.assertEqual(self.fm["title"], KANONISCHER_TITEL)
        self.assertEqual(self.fm["cover"]["alt"], KANONISCHER_TITEL)
        self.assertEqual(self.fm["keywords"][0], "WLAN-Verstärker vs. Mesh-WLAN")
        self.assertNotIn("dsl hacks", ko.norm(" ".join(self.fm["keywords"])))
        self.assertNotIn("dsl hacks", ko.norm(self.fm["description"]))
        self.assertEqual(sl.befunde(self.fm["description"]), [])

        kmap = yaml.safe_load((ROOT / "data" / "kannibalisierung_map.yaml").read_text(encoding="utf-8"))
        eintrag = next(
            b
            for c in kmap["cluster"]
            for b in c["beitraege"]
            if b.get("slug") == SLUG
        )
        self.assertEqual(eintrag["titel"], self.fm["title"])

    def test_topics_eintrag_bereinigt(self):
        topics = yaml.safe_load((ROOT / "data" / "topics.yaml").read_text(encoding="utf-8"))["topics"]
        eintrag = next(t for t in topics if t.get("title") == KANONISCHER_TITEL)
        self.assertEqual(eintrag["keywords"][0], "WLAN-Verstärker vs. Mesh-WLAN")
        self.assertNotIn("dsl hacks", ko.norm(" ".join(eintrag["keywords"])))

    def test_keyword_optimizer_laesst_titel_unberuehrt(self):
        with tempfile.TemporaryDirectory() as tmp:
            kopie = Path(tmp) / "index.md"
            shutil.copy2(self.artikel_pfad, kopie)
            changed, actions = ko.heal_article_file(str(kopie))
        self.assertFalse(changed, f"Keyword-Optimizer dürfte nichts umschreiben: {actions}")

    def test_alle_beitraege_und_entwuerfe_haben_titelkonformes_hauptkeyword(self):
        abweichungen = []
        for pfad in sorted((ROOT / "content" / "posts").glob("*/index.md")):
            fm = _lese_frontmatter(pfad)
            kws = fm.get("keywords") or []
            if not kws:
                continue
            titel = (fm.get("title") or "").strip()
            nk = ko.norm(kws[0])
            nt = ko.norm(titel)
            core = next((t for t in nk.split() if len(t) >= 3), nk)
            ok = (nk in nt) or any(
                w == core or w.startswith(core) or (len(w) >= 4 and core.startswith(w))
                for w in nt.split()
            )
            if not ok:
                abweichungen.append((pfad.parent.name, kws[0], titel))
        self.assertEqual(abweichungen, [], f"Titel/Keyword-Drift bei Bestand/Entwürfen: {abweichungen}")

        ymyl_pfad = ROOT / "content" / "posts" / YMYL_ENTWURF / "index.md"
        ymyl_fm = _lese_frontmatter(ymyl_pfad)
        pruefdatum_roh = (ymyl_fm.get("redaktionelle_pruefung") or {}).get("pruefdatum")
        self.assertTrue(pruefdatum_roh, "YMYL-Entwurf braucht ein dokumentiertes pruefdatum")
        pruefdatum = dt.date.fromisoformat(str(pruefdatum_roh)[:10])
        ymyl_ergebnis = erg.evaluate_path(ymyl_pfad, today=pruefdatum)
        self.assertEqual(ymyl_ergebnis["status"], "freigegeben")
        self.assertEqual(ymyl_ergebnis["findings"], [])

    def test_deploy_workflow_reihenfolge_und_harte_herkunftswache(self):
        workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8"))
        steps = workflow["jobs"]["deploy"]["steps"]
        runs = [s.get("run", "") for s in steps]

        def pos(fragment: str) -> int:
            treffer = [i for i, cmd in enumerate(runs) if fragment in cmd]
            self.assertEqual(len(treffer), 1, f"{fragment} genau einmal erwartet, gefunden: {treffer}")
            return treffer[0]

        self.assertLess(pos("scripts/check_titles.py --fix"), pos("scripts/keyword_optimizer.py --fix"))
        self.assertLess(pos("scripts/keyword_optimizer.py --fix"), pos("scripts/check_covers.py --fix"))
        self.assertLess(pos("scripts/keyword_gate.py --fix"), pos("scripts/check_covers.py --fix"))
        self.assertLess(pos("scripts/check_covers.py --fix"), pos("scripts/ki_cover_herkunft.py --heilen"))
        self.assertLess(pos("scripts/ki_cover_herkunft.py --heilen"), pos("scripts/ki_cover_herkunft.py --pruefen"))

        wache = steps[pos("scripts/ki_cover_herkunft.py --pruefen")]
        self.assertEqual(wache["run"].strip(), "python3 scripts/ki_cover_herkunft.py --pruefen")
        self.assertNotIn("continue-on-error", wache)
        self.assertNotIn("if", wache)

    def test_reproduktionskette_alt_gegen_neu_im_wegwerf_repo(self):
        with tempfile.TemporaryDirectory(prefix="wlan-cover-sync-") as tmp:
            root = Path(tmp)
            shutil.copytree(ROOT / "scripts", root / "scripts", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            (root / "static" / "fonts").mkdir(parents=True)
            for font in (ROOT / "static" / "fonts").glob("*.ttf"):
                shutil.copy2(font, root / "static" / "fonts" / font.name)

            ziel_post = root / "content" / "posts" / SLUG / "index.md"
            ziel_post.parent.mkdir(parents=True)
            original = self.artikel_pfad.read_text(encoding="utf-8")
            # Provoziere exakt den alten Drift-Zustand ("DSL Hacks" statt WLAN-Keyword vorn)
            alt_text = original.replace(
                'keywords: ["WLAN-Verstärker vs. Mesh-WLAN",',
                'keywords: ["DSL Hacks", "WLAN-Verstärker vs. Mesh-WLAN",',
                1,
            )
            self.assertNotEqual(alt_text, original)
            ziel_post.write_text(alt_text, encoding="utf-8")

            covers_src = ROOT / "static" / "images" / "covers"
            for src in covers_src.rglob(SLUG + ".*"):
                if src.is_file():
                    dst = root / "static" / "images" / "covers" / src.relative_to(covers_src)
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

            manifest = json.loads((ROOT / "data" / "covers_manifest.json").read_text(encoding="utf-8"))
            (root / "data").mkdir()
            (root / "data" / "covers_manifest.json").write_text(
                json.dumps({SLUG: manifest[SLUG]}), encoding="utf-8"
            )

            def run(script: str, arg: str, expected: int = 0) -> str:
                res = subprocess.run(
                    [sys.executable, str(root / "scripts" / script), arg],
                    cwd=root,
                    text=True,
                    capture_output=True,
                    timeout=120,
                )
                self.assertEqual(res.returncode, expected, res.stdout + res.stderr)
                return res.stdout + res.stderr

            run("ki_cover_herkunft.py", "--pruefen", expected=0)
            run("keyword_optimizer.py", "--fix", expected=0)
            self.assertIn('title: "DSL Hacks:', ziel_post.read_text(encoding="utf-8"))
            # Ohne anschließendes check_covers --fix scheitert die unveränderte Herkunftswache hart
            befund = run("ki_cover_herkunft.py", "--pruefen", expected=1)
            self.assertIn("Bild weicht vom Renderer ab", befund)
            run("ki_cover_herkunft.py", "--heilen", expected=0)
            run("ki_cover_herkunft.py", "--pruefen", expected=1)
            # Neue Deploy-Reihenfolge: erst check_covers --fix, dann --heilen, dann --pruefen
            run("check_covers.py", "--fix", expected=0)
            run("ki_cover_herkunft.py", "--heilen", expected=0)
            run("ki_cover_herkunft.py", "--pruefen", expected=0)

    def test_cover_reproduziert_pixelgleich_ohne_ausnahme(self):
        self.assertNotIn(SLUG, kh.render_ausnahmen(ROOT))
        bild = ROOT / "static" / self.fm["cover"]["image"]
        self.assertTrue(bild.is_file(), f"Cover fehlt: {bild}")
        erwartet_sha = hashlib.sha256(bild.read_bytes()).hexdigest()
        self.assertEqual(self.fm["cover"]["ki_pruefung"]["sha256"], erwartet_sha)

        text = self.artikel_pfad.read_text(encoding="utf-8")
        _, titel, badge, spar = crc.expected_inputs(gc, str(self.artikel_pfad), text)
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "probe.jpg"
            with contextlib.redirect_stdout(io.StringIO()):
                crc.render_to(gc, titel, badge, spar, str(probe))
            self.assertTrue(
                crc.same_pixels(bild, probe),
                "Cover muss vom Renderer innerhalb der JPEG-/Raster-Toleranz reproduzierbar sein",
            )


if __name__ == "__main__":
    unittest.main()
