#!/usr/bin/env python3
"""Publikationsschutz für Weiterleitungsquellen.

Eine URL aus ``data/weiterleitungen.yaml`` ist ein Alias-Ziel, keine
Publikationsfläche. Das Deploy-Gate prüft diese Invariante bereits vor dem
Build. Dieser kleine, gemeinsame Lesepfad schützt zusätzlich die beiden
Automatiken, die Artikel direkt auf ``draft: false`` setzen können:

* Reserve-Nachfüllung (`reserve_pool.py`)
* Re-Queue-Promotion (`cadence_guard.py` und `publication_release.py`)

Die Weiterleitungsdatei bleibt die einzige Quelle. Dieses Modul kopiert weder
deren YAML-Schema noch entscheidet es über Ziele; es liest ausschließlich die
bereits geprüfte Quelle über ``scripts.weiterleitungen``. Fehlt die Quelle im
echten Repository, ist das ein Werkzeugfehler und die Veröffentlichung wird
fail-closed gestoppt. Isolierte Testbäume ohne Produktionsdaten gelten als
weiterleitungsfrei.
"""
from __future__ import annotations

from pathlib import Path
import sys
import tempfile

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class WeiterleitungsquelleFehler(RuntimeError):
    """Die Weiterleitungs-SSOT ist im Produktionsbaum nicht messbar."""


def _repo_root(posts_dir: str | Path | None = None) -> Path:
    """Leitet die Repository-Wurzel aus einem Posts-Verzeichnis ab.

    Produktionspfad: ``<root>/content/posts``. Die Testwerkbänke des Repos
    verwenden teils direkt ``<tmp>/`` als Posts-Verzeichnis; dort ist der
    übergebene Ordner selbst die Wurzel des isolierten Baums.
    """
    if posts_dir is None:
        return PROJECT_ROOT
    path = Path(posts_dir).resolve()
    if path.name == "posts" and path.parent.name == "content":
        return path.parent.parent
    return path


def weiterleitungsquellen(posts_dir: str | Path | None = None) -> set[str]:
    """Liefert die Slugs, die in der Weiterleitungs-SSOT als ``von`` stehen.

    Ein echter Produktionsbaum mit fehlender SSOT ist kein leerer Bestand:
    Dann wird ``WeiterleitungsquelleFehler`` ausgelöst, damit keine Automation
    versehentlich eine Alias-URL veröffentlicht. Ein isolierter Testbaum ohne
    ``data/`` darf dagegen leer sein.
    """
    root = _repo_root(posts_dir)
    ssot = root / "data" / "weiterleitungen.yaml"
    entfallen = root / "data" / "url_entfallen.yaml"

    if not ssot.is_file() or not entfallen.is_file():
        if root != PROJECT_ROOT:
            return set()
        fehlend = ssot if not ssot.is_file() else entfallen
        raise WeiterleitungsquelleFehler(
            f"Weiterleitungs-SSOT nicht lesbar: {fehlend}")

    scripts_dir = str(PROJECT_ROOT / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    try:
        import weiterleitungen as wl  # noqa: PLC0415 – gemeinsamer SSOT-Parser
        eintraege, _ = wl.lade_quelle(str(root))
    except (ImportError, OSError, ValueError, SystemExit) as exc:
        raise WeiterleitungsquelleFehler(
            f"Weiterleitungs-SSOT nicht lesbar: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 – kein stilles Publizieren ohne SSOT
        raise WeiterleitungsquelleFehler(
            f"Weiterleitungs-SSOT nicht lesbar: {exc}") from exc

    out: set[str] = set()
    for eintrag in eintraege:
        if not isinstance(eintrag, dict):
            raise WeiterleitungsquelleFehler(
                "Weiterleitungs-SSOT enthält einen ungültigen Eintrag")
        von = str(eintrag.get("von") or "").strip().strip("/")
        if von.startswith("posts/"):
            slug = von.removeprefix("posts/").strip("/")
            if slug:
                out.add(slug)
    return out


def selbsttest() -> int:
    """Kleiner, schreibender Sandkastentest für den gemeinsamen SSOT-Leser."""
    slug = "2026-10-24-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu"
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        data = root / "data"
        data.mkdir()
        (data / "weiterleitungen.yaml").write_text(
            "eintraege:\n"
            f"  - von: \"/posts/{slug}/\"\n"
            "    nach: \"/pillar/strom-sparen/\"\n"
            "    regel: \"C\"\n"
            "    grund: \"Selbsttest-Quelle\"\n",
            encoding="utf-8")
        (data / "url_entfallen.yaml").write_text(
            "eintraege: []\n", encoding="utf-8")
        gefunden = weiterleitungsquellen(root)
        if gefunden != {slug}:
            raise AssertionError(f"unerwartete Quellen: {gefunden!r}")
        (data / "weiterleitungen.yaml").write_text(
            "eintraege: [\n", encoding="utf-8")
        try:
            weiterleitungsquellen(root)
        except WeiterleitungsquelleFehler:
            pass
        else:
            raise AssertionError("kaputte SSOT wurde nicht fail-closed erkannt")
    print("✅ Publikations-Weiterleitungsschutz-Selbsttest grün (SSOT + Fail-Closed).")
    return 0


if __name__ == "__main__":  # pragma: no cover - Bibliotheksmodul
    if "--selftest" in sys.argv[1:]:
        raise SystemExit(selbsttest())
    print(f"{len(weiterleitungsquellen())} Weiterleitungsquellen")
