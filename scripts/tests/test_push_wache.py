"""Push-Wache: kein Workflow darf den Sync-Kern blind überstimmen.

Reparatur Issue #547 (Vorgang WF-C545, „Shorts-Schmiede“ rot im Schritt
„Stand sichern“, Run 37116487089):

`scripts/git_sync.sh` ist der EINZIGE erlaubte Push-Weg der Bots. Er bringt
Fetch-/Push-Retries, Rebase-Runden gegen parallele Bots und die Auto-Heilung
rein generierter Dateien mit. Bricht er ab, ist das eine BEWUSSTE,
fail-closed Entscheidung („Kein Push – Arbeitsstand bleibt lokal sauber“).

Das Muster

    scripts/git_sync.sh --push-only || git push

hebelt genau diese Entscheidung aus: Der rohe Push kann nichts gewinnen, was
git_sync nicht schon versucht hat, wird als non-fast-forward abgelehnt und
färbt den Schritt rot – mit einer Meldung, die die echte Ursache verdeckt.
Genau so entstand WF-C545.

Dieser Test hält die Klasse dauerhaft geschlossen: Er prüft ALLE Workflows,
nicht nur die drei heute bereinigten (social-video, social-dialog, werkbank).
"""

import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"

# `git_sync.sh ... || <irgendwas mit git push>` – Zeilenbasiert, weil die
# Workflows diesen Fallback immer in einer Zeile schreiben.
BLIND_FALLBACK = re.compile(r"git_sync\.sh[^\n|]*\|\|[^\n]*git\s+push")

# Erlaubte Ausnahme: Brücken-Workflow ohne git_sync (eigener, dokumentierter
# Weg) – wird hier nicht geprüft, weil er git_sync gar nicht erst aufruft.


class PushWache(unittest.TestCase):
    def workflow_dateien(self):
        dateien = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
        self.assertTrue(dateien, "Keine Workflow-Dateien gefunden.")
        return dateien

    def test_kein_blinder_git_push_fallback_hinter_git_sync(self):
        treffer = []
        for datei in self.workflow_dateien():
            for nr, zeile in enumerate(
                datei.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if zeile.lstrip().startswith("#"):
                    continue
                if BLIND_FALLBACK.search(zeile):
                    treffer.append(f"{datei.name}:{nr}: {zeile.strip()}")
        self.assertEqual(
            [],
            treffer,
            "Blind-Fallback auf rohen `git push` hinter git_sync.sh gefunden "
            "(Issue #547): git_sync.sh bricht bei echtem Konflikt bewusst ab; "
            "ein roher Push danach wird nur abgelehnt und macht den Lauf rot.\n"
            + "\n".join(treffer),
        )

    def test_kein_verschlucktes_git_sync_ergebnis(self):
        """`git_sync.sh ... || true` würde den fail-closed-Abbruch verschlucken."""
        muster = re.compile(r"git_sync\.sh[^\n|]*\|\|\s*true\b")
        treffer = []
        for datei in self.workflow_dateien():
            for nr, zeile in enumerate(
                datei.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if zeile.lstrip().startswith("#"):
                    continue
                if muster.search(zeile):
                    treffer.append(f"{datei.name}:{nr}: {zeile.strip()}")
        self.assertEqual(
            [],
            treffer,
            "Ergebnis von git_sync.sh wird mit `|| true` verschluckt "
            "(Issue #547) – ein nicht gepushter Stand muss sichtbar bleiben "
            "(mindestens als ::warning::).\n" + "\n".join(treffer),
        )


if __name__ == "__main__":
    unittest.main()
