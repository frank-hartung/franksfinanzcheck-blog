#!/usr/bin/env python3
"""Fassungsdrift bestehender YMYL-Siegel früh erkennen, auch bei Entwürfen.

Dies ist KEINE fachliche Freigabe: offene Entwürfe, Fristen und Quellen werden
weiter vom editorial_review_gate bzw. der Belegketten-Wache behandelt. Ein
bewusst zurückgezogenes Siegel (Status ausstehend, Hash entfernt) bleibt als
ungeprüfter Entwurf möglich; das Veröffentlichungs-Gate sperrt ihn weiterhin.
"""
import argparse
import subprocess
import sys
from pathlib import PurePosixPath

import editorial_review_gate as gate


def pruefe_pfad(path):
    try:
        fm, body, _ = gate.load_article(path)
        review = fm.get("redaktionelle_pruefung") or {}
        if not isinstance(review, dict):
            raise gate.ParseError("Prüfprotokoll ist kein Mapping")
        digest = review.get("inhalt_sha256")
        status = str(review.get("status") or "").strip().lower()
        if digest or status in gate.APPROVED_STATUSES:
            if not isinstance(digest, str) or digest.strip().lower() != gate.content_fingerprint(fm, body):
                return "E17: Siegel fehlt oder passt nicht zur Fassung; Fachprüfung oder geprüfte Fassung wiederherstellen"
    except Exception as exc:
        return f"nicht prüfbar ({type(exc).__name__}: {exc})"
    return None


def pruefe_rueckzug(old_raw, new_raw):
    """Ein früheres Siegel darf nicht still durch Entfernen des Blocks verschwinden."""
    try:
        yaml = gate._yaml_module()
        old_fm, _ = gate.split_article(old_raw)
        new_fm, _ = gate.split_article(new_raw)
        old, new = yaml.safe_load(old_fm), yaml.safe_load(new_fm)
        if not isinstance(old, dict) or not isinstance(new, dict):
            raise gate.ParseError("Frontmatter ist kein Mapping")
        previous = old.get('redaktionelle_pruefung') or {}
        current = new.get('redaktionelle_pruefung') or {}
        if not isinstance(previous, dict) or not isinstance(current, dict):
            raise gate.ParseError("Prüfprotokoll ist kein Mapping")
        was_protected = previous.get('inhalt_sha256') or str(previous.get('status') or '').strip().lower() in gate.APPROVED_STATUSES
        still_protected = current.get('inhalt_sha256') or str(current.get('status') or '').strip().lower() in gate.APPROVED_STATUSES
        if was_protected and not still_protected:
            if not (new.get('draft') is True and current.get('status') == 'ausstehend'
                    and not any(current.get(k) for k in ('pruefer', 'pruefdatum', 'naechste_pruefung'))):
                return ('Freigabe still entfernt: Rückzug braucht draft: true, status: ausstehend '
                        'und getrennte historische Prüferdaten/Termine')
    except Exception as exc:
        return f"Übergang nicht prüfbar ({type(exc).__name__}: {exc})"
    return None


def pruefe_base(base):
    """Geänderte Post-Bundles gegen die PR-Basis prüfen; gelöschte Dateien ausgenommen."""
    cmd = ['git', 'diff', '--name-only', '-z', '--diff-filter=M', '--no-renames', base, 'HEAD', '--', 'content/posts']
    names = subprocess.check_output(cmd, cwd=gate.ROOT).decode('utf-8').split('\0')
    errors = []
    for name in filter(None, names):
        parts = PurePosixPath(name).parts
        if len(parts) != 4 or parts[:2] != ('content', 'posts') or parts[-1] != 'index.md':
            continue
        previous = subprocess.check_output(['git', 'show', f'{base}:{name}'], cwd=gate.ROOT).decode('utf-8')
        current = (gate.ROOT / name).read_text(encoding='utf-8')
        if problem := pruefe_rueckzug(previous, current):
            errors.append((name, problem))
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', help='Git-Basis für die PR-Rückzugsprüfung')
    args = parser.parse_args(argv)
    paths = gate.all_post_paths()
    errors = [(str(path.relative_to(gate.ROOT)), problem)
              for path in paths if (problem := pruefe_pfad(path))]
    if args.base is not None:
        try:
            errors.extend(pruefe_base(args.base))
        except (OSError, subprocess.CalledProcessError, UnicodeError) as exc:
            errors.append(('PR-Basis', f'Übergangsprüfung nicht ausführbar: {exc}'))
    for path, problem in errors:
        print(f"🛑 {path}: {problem}")
    print(f"YMYL-Siegelwache: {len(paths)} Artikel · {len(errors)} Befunde (keine Fachfreigabe)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
