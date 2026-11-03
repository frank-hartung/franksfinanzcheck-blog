#!/usr/bin/env python3
"""Vergleicht Cover-Originale mit einem deterministischen Pillow-Nachbau.

Kein KI-Detektor: identische Bytes belegen nur, dass der aktuelle Generator
mit den Manifestdaten dieselbe Datei erzeugen kann; Abweichungen sind offen.
Originale, Varianten, Manifest und Content werden niemals verändert.

    python3 scripts/ki_cover_render_audit.py --json > /tmp/cover-audit.json
"""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
from contextlib import redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import tempfile

import PIL
import ki_cover_provenienz as provenance

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render_one(task: tuple[str, dict]) -> dict:
    image, entry = task
    result = {"image": image, "status": "unbekannt"}
    try:
        original = provenance.local_cover(ROOT, image)
        if not original.is_file():
            result['grund'] = 'Original fehlt'
            return result
        result['sha256'] = sha256(original)
        if not isinstance(entry, dict) or not isinstance(entry.get('design'), dict):
            result['grund'] = 'Manifest-Eintrag oder Design fehlt'
            return result
        design = entry['design']
        if not isinstance(entry.get('title'), str) or not isinstance(design.get('badge'), str) or not isinstance(design.get('savings'), str):
            result['grund'] = 'Manifest-Eingaben unvollständig'
            return result
        # Keine Ausgabe des Renderers auf stdout; keine Dateien im Repository.
        with tempfile.TemporaryDirectory(prefix='ki-cover-audit-') as tmp, redirect_stdout(io.StringIO()):
            import cover_render_check as checker
            generated = Path(tmp) / 'cover.jpg'
            checker.render_to(checker._gc(), entry['title'], design['badge'], design['savings'], str(generated))
            result['vergleich_sha256'] = sha256(generated)
            if result['sha256'] == result['vergleich_sha256']:
                result['status'] = 'byte_identisch'
            elif checker.same_pixels(original, generated):
                result['status'] = 'pixel_identisch'
            else:
                result['status'] = 'abweichend'
    except Exception as exc:
        result['status'] = 'fehler'
        result['grund'] = str(exc)
    return result


def run(workers: int = 4) -> dict:
    records, errors = provenance.audit()
    if errors:
        raise ValueError('Provenienz-Gate: ' + '; '.join(errors))
    manifest_path = ROOT / 'data/covers_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    images = {}
    for record in records:
        name = record['image']
        if not isinstance(name, str):
            raise ValueError(f"{record['content']}: Bildpfad ist kein String")
        entry = images.setdefault(name, {'content': [], 'entwuerfe': 0})
        entry['content'].append(record['content'])
        entry['entwuerfe'] += int(record['draft'])
    tasks = [(name, manifest.get(Path(name).stem)) for name in sorted(images)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(render_one, tasks))
    for result in results:
        result.update(images[result['image']])
    return {
        'stand_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'verfahren': 'Byte-/Pixelvergleich mit Pillow-Reproduktion anhand des Cover-Manifests; kein Herkunfts- oder KI-Beweis',
        'referenzen': len(records),
        'dateien': len(results),
        'umgebung': {'pillow': PIL.__version__, 'generator_sha256': sha256(ROOT / 'scripts/generate_covers.py'),
                     'schrift_sha256': sha256(ROOT / 'static/fonts/Inter-Bold.ttf'), 'manifest_sha256': sha256(manifest_path)},
        'ergebnisse': results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--json', action='store_true', help='vollständiger JSON-Bericht')
    parser.add_argument('--workers', type=int, default=4, choices=range(1, 9), help='parallele Renderer (1–8)')
    args = parser.parse_args()
    try:
        report = run(args.workers)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f'Cover-Audit fehlgeschlagen: {exc}')
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        counts = {key: sum(x['status'] == key for x in report['ergebnisse'])
                  for key in ('byte_identisch', 'pixel_identisch', 'abweichend', 'unbekannt', 'fehler')}
        print(f"{report['referenzen']} Referenzen, {report['dateien']} Dateien: {counts}")
        print('Gleichheit ist keine Herkunftsbestätigung; Abweichungen sind offen.')
    return 1 if any(x['status'] == 'fehler' for x in report['ergebnisse']) else 0


if __name__ == '__main__':
    raise SystemExit(main())
