"""Push-Wache: `git_sync.sh` ist der EINZIGE Push-Weg der Workflows.

Reparatur Issue #547 (Vorgang WF-C545, „Shorts-Schmiede“ rot im Schritt
„Stand sichern“, Run 37116487089):

`scripts/git_sync.sh` ist der zentrale Push-Weg aller Bots. Er bringt
Fetch-/Push-Retries, Rebase-Runden gegen parallele Bots und die Auto-Heilung
rein generierter Dateien mit. Bricht er ab, ist das eine BEWUSSTE,
fail-closed Entscheidung („Kein Push – Arbeitsstand bleibt lokal sauber“).

Diese Wache hält die komplette Fehlerklasse geschlossen. Sie kennt drei
Umgehungen, die alle denselben roten Lauf erzeugen:

1. BLIND-FALLBACK –

       scripts/git_sync.sh --push-only || git push

   Der rohe Push kann nichts gewinnen, was git_sync nicht schon versucht
   hat, wird als non-fast-forward abgelehnt und färbt den Schritt rot – mit
   einer Meldung, die die echte Ursache verdeckt. Genau so entstand WF-C545.
   Wird auch über Zeilenumbrüche hinweg erkannt (`||` bzw. `\\` am
   Zeilenende), damit das Muster nicht durch Umbrechen zurückkehrt.

2. VERSCHLUCKTES ERGEBNIS –

       scripts/git_sync.sh --push-only || true

   Der fail-closed-Abbruch verschwindet spurlos; ein nicht gepushter Stand
   bleibt unsichtbar liegen.

3. ROHER PUSH AM SYNC-KERN VORBEI –

       git push

   Die Variante, die am 04.10.2026 als Letzte im Bestand gefunden wurde
   (`design-varianten.yml`, `n8n-schaltwerk-bridge.yml`): gar kein
   git_sync, also kein Retry, kein Rebase, keine Heilung – dieselbe
   Fehlerklasse über einen anderen Workflow.

Begründete Ausnahmen sind möglich, aber sie müssen im Workflow stehen und
sich selbst erklären – siehe AUSNAHME_MARKER. Default ist fail-closed.

Geprüft wird IMMER der ganze Workflow-Bestand, nie nur die heute
bereinigten Dateien.
"""

import re
import unittest
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"

# Wer wirklich einen Sonderweg braucht, schreibt ihn sichtbar in den
# Workflow – auf dieselbe oder die vorangehende Zeile:
#
#     git push origin refs/tags/v1   # push-wache: ausnahme – Tag-Push, kein Branch-Sync
#
# Die Begründung ist Pflicht (>= 12 Zeichen). Damit bleibt die Wache
# fail-closed, ohne künftige Sonderfälle unmöglich zu machen; jede Ausnahme
# steht an der Fundstelle und ist im Review sichtbar.
AUSNAHME_MARKER = re.compile(r"push-wache:\s*ausnahme\s*[–\-:]\s*(?P<grund>.+)", re.I)

# `git_sync.sh ... || <irgendwas mit git push>`
BLIND_FALLBACK = re.compile(r"git_sync\.sh[^|]*\|\|[^\n]*git\s+push")

# `git_sync.sh ... || true`
VERSCHLUCKT = re.compile(r"git_sync\.sh[^|]*\|\|\s*true\b")

# Roher Push. `git_sync.sh` selbst ist der sanktionierte Pusher und steht
# nicht in diesem Verzeichnis – in Workflows ist jeder `git push` roh.
ROHER_PUSH = re.compile(r"(?<!_)\bgit\s+push\b")


def logische_zeilen(text):
    """Shell-Fortsetzungen zu je einer logischen Zeile zusammenfassen.

    Zusammengefasst wird bei `\\`, `||`, `&&` und `|` am Zeilenende – also
    genau dort, wo ein Blind-Fallback über einen Umbruch versteckt werden
    könnte:

        scripts/git_sync.sh --push-only ||
          git push

    Reine Kommentarzeilen fallen raus (die Workflows erklären das
    Anti-Muster ausführlich im Fließtext – das soll kein Treffer sein).
    Zurückgegeben wird (Zeilennummer des Anfangs, zusammengefügter Text).
    """
    ausgabe = []
    puffer = ""
    start = None
    for nr, roh in enumerate(text.splitlines(), start=1):
        zeile = roh.strip()
        if not puffer and (not zeile or zeile.startswith("#")):
            continue
        # Angehängte Kommentare erhalten (der Ausnahme-Marker lebt dort),
        # aber Fortsetzungs-Erkennung auf dem Code-Teil durchführen.
        if start is None:
            start = nr
        puffer = f"{puffer} {zeile}".strip() if puffer else zeile
        if re.search(r"(\\|\|\||&&|\|)$", zeile):
            continue
        ausgabe.append((start, puffer))
        puffer = ""
        start = None
    if puffer:
        ausgabe.append((start, puffer))
    return ausgabe


class PushWache(unittest.TestCase):
    def workflow_dateien(self):
        dateien = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
        self.assertTrue(dateien, "Keine Workflow-Dateien gefunden.")
        return dateien

    def _treffer(self, muster):
        """Alle Fundstellen des Musters im gesamten Workflow-Bestand."""
        treffer = []
        for datei in self.workflow_dateien():
            inhalt = datei.read_text(encoding="utf-8")
            for nr, zeile in logische_zeilen(inhalt):
                if not muster.search(zeile):
                    continue
                if AUSNAHME_MARKER.search(zeile):
                    continue
                treffer.append(f"{datei.name}:{nr}: {zeile}")
        return treffer

    def test_kein_blinder_git_push_fallback_hinter_git_sync(self):
        treffer = self._treffer(BLIND_FALLBACK)
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
        treffer = self._treffer(VERSCHLUCKT)
        self.assertEqual(
            [],
            treffer,
            "Ergebnis von git_sync.sh wird mit `|| true` verschluckt "
            "(Issue #547) – ein nicht gepushter Stand muss sichtbar bleiben "
            "(mindestens als ::warning::).\n" + "\n".join(treffer),
        )

    def test_kein_roher_git_push_am_sync_kern_vorbei(self):
        """Jeder Push eines Workflows läuft über scripts/git_sync.sh.

        Ein roher `git push` hat weder Retry noch Rebase: Ein einziger
        paralleler Bot-Push nach main lässt ihn als non-fast-forward
        auflaufen – dieselbe Fehlerklasse wie WF-C545, nur über einen
        anderen Workflow. Zuletzt gefunden am 04.10.2026 in
        `design-varianten.yml` (roh) und `n8n-schaltwerk-bridge.yml`
        (roh + `|| echo`, also zusätzlich unsichtbar).
        """
        treffer = self._treffer(ROHER_PUSH)
        self.assertEqual(
            [],
            treffer,
            "Roher `git push` in einem Workflow gefunden (Issue #547). "
            "Pushes laufen ausnahmslos über `scripts/git_sync.sh` "
            "(Fetch-/Push-Retry, Rebase-Runden, Auto-Heilung). Braucht eine "
            "Stelle wirklich einen Sonderweg, muss sie ihn an Ort und Stelle "
            "begründen: `# push-wache: ausnahme – <Grund>`.\n"
            + "\n".join(treffer),
        )


class LogischeZeilenTest(unittest.TestCase):
    """Die Wache muss das Muster auch über Zeilenumbrüche hinweg sehen."""

    def test_umbrochener_blind_fallback_wird_erkannt(self):
        text = "        scripts/git_sync.sh --push-only ||\n          git push\n"
        verbunden = [z for _, z in logische_zeilen(text)]
        self.assertEqual(1, len(verbunden))
        self.assertTrue(BLIND_FALLBACK.search(verbunden[0]))

    def test_backslash_fortsetzung_wird_erkannt(self):
        text = "        scripts/git_sync.sh --push-only \\\n          || git push\n"
        verbunden = [z for _, z in logische_zeilen(text)]
        self.assertEqual(1, len(verbunden))
        self.assertTrue(BLIND_FALLBACK.search(verbunden[0]))

    def test_kommentare_sind_keine_treffer(self):
        text = "        # Hier stand `scripts/git_sync.sh --push-only || git push`.\n"
        self.assertEqual([], list(logische_zeilen(text)))

    def test_roher_push_wird_erkannt(self):
        self.assertTrue(ROHER_PUSH.search("git push"))
        self.assertTrue(ROHER_PUSH.search('git push origin HEAD:${{ github.ref }}'))
        # `git_sync.sh` ist der sanktionierte Weg und darf nicht anschlagen.
        self.assertIsNone(ROHER_PUSH.search("scripts/git_sync.sh --push-only"))

    def test_begruendete_ausnahme_wird_akzeptiert(self):
        zeile = "git push origin refs/tags/v1  # push-wache: ausnahme – Tag-Push"
        self.assertTrue(ROHER_PUSH.search(zeile))
        self.assertTrue(AUSNAHME_MARKER.search(zeile))


if __name__ == "__main__":
    unittest.main()
