#!/usr/bin/env python3
"""reader_voice_ab.py — A/B-Hörtest: welche kostenlose Stimme klingt am menschlichsten?

Zweck (04.09.2026)
  „Natürlicher" ist eine Hör-Entscheidung, keine Messgröße. Dieses Skript
  vertont denselben Text mit jeder verfügbaren kostenlosen Stimme und legt
  die Proben nebeneinander in `tmp/ab/` ab – inkl. einer Vergleichsseite
  `index.html`, in der man direkt reinhören kann (lokal öffnen, kein
  Server nötig). So entscheidest du mit den Ohren, welche Stimme ins
  Redaktionsprofil kommt, und trägst sie danach in den Deploy ein
  (`--profile narrator` oder `--voice-de …`).

Was verglichen wird
  · Backend  edge (Microsoft-Neural, ohne Key) vs. piper (lokal/offline)
             vs. groq (nur EN)
  · Profil   natural (Multilingual v2: Florian/Andrew – ein Sprecher auch
             für englische Fachbegriffe) vs. narrator (Conrad/Ryan – der
             klassische Erzähler)
  · Regie    mit Rollen-Prosodie/Pausen vs. ohne (--no-prosody-Variante),
             damit man hört, was die Regie bringt
  · Tempo    Standard vs. ruhiger (--rate 0.94)

Aufruf
  pip install edge-tts            # kostenlose Backend-Stufe 1
  python3 scripts/reader_voice_ab.py                       # alle verfügbaren
  python3 scripts/reader_voice_ab.py --profiles natural    # nur ein Profil
  python3 scripts/reader_voice_ab.py --sample gemischt --open
  python3 scripts/reader_voice_ab.py --text "Eigener Text mit 1.299,50 €."

Die Proben bleiben lokal (tmp/ ist in .gitignore) – nichts wird veröffentlicht.
"""
from __future__ import annotations

import argparse
import html as html_mod
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import reader_tts_backends as ttb  # noqa: E402
import generate_reader_audio as gen  # noqa: E402

# --------------------------------------------------------------------------
# Probetexte: bewusst so gewählt, dass sie die Schwachstellen von TTS zeigen
# (Zahlen, Währungen, Daten, Abkürzungen, englische Fachbegriffe im
# deutschen Satz, Aufzählungen, Warnboxen).
# --------------------------------------------------------------------------
SAMPLES: dict[str, list[tuple[str, str]]] = {
    "finanz": [
        ("de", "h2", "Stromkosten 2026: Was ein Wechsel wirklich bringt"),
        ("de", "p", "Wer seinen Tarif zum 12.08.2026 wechselt, spart im Schnitt "
                    "300 € pro Jahr. In der Grundversorgung kostet die Kilowattstunde "
                    "oft 42,9 Cent, ein Sondervertrag liegt bei 28,5 Cent."),
        ("de", "li", "Punkt 1: Zählerstand notieren und den Verbrauch der letzten "
                     "12 Monate prüfen."),
        ("de", "callout", "Kurzantwort: Ein ETF-Sparplan ab 25 € monatlich schlägt "
                          "das Sparbuch – bei 3,5 % Rendite sind nach 20 Jahren "
                          "rund 1.299,50 € mehr auf dem Konto."),
        ("de", "warning", "Achtung: Viele Preisgarantien enden nach 12 Monaten. "
                          "Danach darf der Anbieter erhöhen, z. B. um 8 %."),
    ],
    "gemischt": [
        ("de", "h2", "Was ein Smart-Home wirklich spart"),
        ("de", "p", "Der Bericht der Bafin zeigt: Die meisten Haushalte unterschätzen "
                    "ihr Sparpotenzial. The comparison shows lower fees for households "
                    "that switch their provider every two years."),
        ("de", "p", "Konkret heißt das: Wer Heizung, DSL und Strom bündelt, zahlt "
                    "monatlich 47,80 € statt 63,20 €. Das entspricht 184,40 € im Jahr – "
                    "bzw. 1.844 € in zehn Jahren."),
        ("de", "table-row", "Anbieter: Musterstrom AG. Grundpreis: 12,99 Euro. "
                            "Arbeitspreis: 31,4 Cent pro Kilowattstunde."),
        ("de", "outro", "Ende des Beitrags. Vielen Dank fürs Zuhören bei FranksFinanzcheck."),
    ],
    "english": [
        ("en", "h2", "How to compare energy tariffs in Germany"),
        ("en", "p", "If you switch your provider on 08/12/2026, you save around "
                    "€300 per year. The average price is 42.9 cents per kilowatt hour, "
                    "while special contracts cost about 28.5 cents."),
        ("en", "warning", "Attention: Most price guarantees expire after 12 months. "
                          "Providers may raise prices by 8% afterwards."),
    ],
}


def render_variant(label: str, backend: str, profile: str, blocks: list, article_lang: str,
                   prosody: bool, rate: float, out_dir: str, bitrate: int) -> dict | None:
    """Eine Variante (Backend × Profil × Regie × Tempo) als Hörprobe rendern."""
    engine = ttb.Engine(backend=backend, profile=profile, rate_scale=rate, verbose=True)
    if not engine.usable_langs():
        return {"label": label, "backend": backend, "profile": profile, "prosody": prosody,
                "rate": rate, "status": "unavailable", "detail": engine.describe() or "kein Backend"}
    need = "en" if article_lang == "en" else "de"
    if not engine.can(need):
        return {"label": label, "backend": backend, "profile": profile, "prosody": prosody,
                "rate": rate, "status": "no-lang", "detail": engine.describe()}
    units = ttb.build_units(blocks, article_lang, prosody=prosody)
    track = gen.synthesize_track(units, engine, dry_run=False)
    if track["failures"]:
        return {"label": label, "backend": backend, "profile": profile, "prosody": prosody,
                "rate": rate, "status": "failed",
                "detail": track["failures"][0].get("error", "")[:160]}
    wav = gen.polish_track(track["pcm"], track["rate"])
    stem = label.replace("/", "_").replace(" ", "-")
    path = os.path.join(out_dir, stem)
    final = path + ".wav"
    try:
        gen.encode_mp3(wav, path + ".mp3", bitrate=bitrate)
        final = path + ".mp3"
    except RuntimeError:
        with open(final, "wb") as f:
            f.write(wav)
    return {"label": label, "backend": backend, "profile": profile, "prosody": prosody,
            "rate": rate, "status": "ok", "file": os.path.basename(final),
            "seconds": round(track["duration_ms"] / 1000, 1),
            "kbyte": round(os.path.getsize(final) / 1024, 1),
            "voices": track["engines"], "units": len(units),
            "detail": engine.describe()}


def write_index(out_dir: str, rows: list[dict], sample_name: str, blocks: list) -> str:
    """Vergleichsseite: Proben nebeneinander, mit Text zum Mitlesen."""
    ok = [r for r in rows if r["status"] == "ok"]
    body = []
    for r in rows:
        if r["status"] == "ok":
            player = (f'<audio controls preload="none" src="{html_mod.escape(r["file"])}"></audio>'
                      f'<span class="meta">{r["seconds"]} s · {r["kbyte"]} kB · '
                      f'{html_mod.escape(", ".join(sorted(set(r["voices"].values()))))}</span>')
        else:
            player = f'<span class="off">nicht verfügbar ({html_mod.escape(r.get("detail", r["status"]))})</span>'
        body.append(
            f'<li><div class="label">{html_mod.escape(r["label"])}'
            f'<small>Regie {"an" if r["prosody"] else "aus"} · Tempo {r["rate"]}</small></div>'
            f'<div class="player">{player}</div></li>')
    text_html = "".join(
        f"<p><b>{html_mod.escape(t)}:</b> {html_mod.escape(x)}</p>"
        for _l, t, x in blocks)
    page = f"""<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>A/B-Hörtest – {html_mod.escape(sample_name)}</title>
<style>
 body{{font:16px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0 auto;max-width:60rem;padding:1.5rem;color:#1a1a1a}}
 h1{{font-size:1.5rem;margin:0 0 .25rem}} .sub{{color:#666;margin:0 0 1.5rem}}
 ul{{list-style:none;padding:0;margin:0 0 2rem}}
 li{{display:flex;gap:1rem;align-items:center;padding:.75rem 0;border-bottom:1px solid #eee;flex-wrap:wrap}}
 .label{{flex:0 0 16rem;font-weight:600}} .label small{{display:block;font-weight:400;color:#666}}
 .player{{flex:1 1 20rem;display:flex;align-items:center;gap:.75rem;flex-wrap:wrap}}
 audio{{width:100%;max-width:26rem}} .meta{{color:#666;font-size:.85rem}} .off{{color:#a33;font-size:.9rem}}
 .text{{background:#f7f7f7;border-radius:.5rem;padding:1rem}}
 .text p{{margin:.35rem 0}}
</style></head><body>
<h1>A/B-Hörtest: welche kostenlose Stimme klingt am menschlichsten?</h1>
<p class="sub">Probe „{html_mod.escape(sample_name)}" · {len(ok)} von {len(rows)} Varianten erzeugt.
Alle Proben sind männlich, Deutsch und Englisch ohne Umschalter – identischer Text, identische
Aussprache-Normalisierung, nur Stimme/Regie/Tempo unterscheiden sich.</p>
<ul>
{''.join(body)}
</ul>
<div class="text"><h2 style="font-size:1.1rem;margin:0 0 .5rem">Mitlesetext (normalisiert gesprochen)</h2>
{text_html}</div>
</body></html>
"""
    path = os.path.join(out_dir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path


def main() -> int:
    ap = argparse.ArgumentParser(description="A/B-Hörtest für die kostenlose Vorlese-Stimme.")
    ap.add_argument("--out", default=os.path.join(ROOT, "tmp", "ab"))
    ap.add_argument("--sample", default="gemischt", choices=sorted(SAMPLES),
                    help="Probetext (finanz | gemischt | english)")
    ap.add_argument("--text", default=None, help="eigener Text (überschreibt --sample)")
    ap.add_argument("--backends", default="edge,piper",
                    help="zu vergleichende Backends (Kommata; auto = alle verfügbaren)")
    ap.add_argument("--profiles", default="natural,narrator",
                    help="zu vergleichende Stimmen-Profile (Kommata)")
    ap.add_argument("--rates", default="1.0,0.94", help="zu vergleichende Tempi (Kommata)")
    ap.add_argument("--no-prosody-variant", action="store_true",
                    help="zusätzlich eine Variante ohne Rollen-Regie erzeugen (hörbarer Unterschied)")
    ap.add_argument("--bitrate", type=int, default=64, help="MP3-Bitrate der Probe (64 = gut hörbar)")
    ap.add_argument("--lang", default="de", help="Artikelsprache der Probe (de|en)")
    ap.add_argument("--open", action="store_true", help="Vergleichsseite nach dem Lauf öffnen")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    blocks = SAMPLES[args.sample]
    if args.text:
        blocks = [("de", "p", args.text)]

    backends = [b.strip() for b in args.backends.split(",") if b.strip()]
    if backends == ["auto"]:
        backends = list(ttb.BACKEND_ORDER)
    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    rates = [float(r) for r in args.rates.split(",") if r.strip()]

    print(f"🎧 A/B-Hörtest: {len(blocks)} Blöcke · Backends {backends} · Profile {profiles} · "
          f"Tempi {rates} → {args.out}")
    rows: list[dict] = []
    for backend in backends:
        for profile in profiles:
            if profile not in ttb.VOICE_PRESETS:
                print(f"  ⚠ unbekanntes Profil „{profile}“ → übersprungen")
                continue
            for rate in rates:
                for prosody in ([True, False] if args.no_prosody_variant else [True]):
                    label = f"{backend} · {profile}" + ("" if prosody else " · ohne Regie")
                    if rate != 1.0:
                        label += f" · {rate:.2f}x"
                    print(f"  ▶ {label}")
                    row = render_variant(label, backend, profile, blocks, args.lang,
                                         prosody, rate, args.out, args.bitrate)
                    if row:
                        rows.append(row)
                        mark = "✅" if row["status"] == "ok" else "⊘"
                        print(f"    {mark} {row['status']}"
                              + (f" · {row.get('seconds')} s · {row.get('kbyte')} kB" if row["status"] == "ok" else ""))

    with open(os.path.join(args.out, "ab-result.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    page = write_index(args.out, rows, args.sample if not args.text else "eigener Text", blocks)

    ok = [r for r in rows if r["status"] == "ok"]
    print(f"\n{len(ok)} von {len(rows)} Proben erzeugt. Vergleichsseite: {page}")
    if not ok:
        failed = [r for r in rows if r["status"] in ("failed", "no-lang")]
        if failed:
            print("⊘ Keine Probe möglich: Backend gefunden, die Synthese schlug aber fehl.")
            for r in failed[:3]:
                print(f"    – {r['label']}: {r.get('detail', r['status'])}")
            print("  Häufigste Ursachen: kein ffmpeg (edge-tts braucht es fürs MP3),\n"
                  "  kein Zugang zum Edge-Dienst, oder die Piper-Stimme ließ sich\n"
                  "  nicht laden (Hugging Face blockiert?).\n"
                  "  Offline-Abhilfe: pip install piper-tts und FF_PIPER_VOICES=<Pfad>\n"
                  "  auf ein Verzeichnis mit vorab geladenen .onnx-Dateien zeigen lassen.")
        else:
            print("⊘ Keine Probe möglich: es ist kein kostenloses Backend installiert.\n"
                  "  Abhilfe (beides kostenlos, ohne Konto):\n"
                  "    pip install edge-tts      # Neuralstimmen DE/EN (braucht ffmpeg)\n"
                  "    pip install piper-tts     # lokale OFFLINE-Stimmen (Thorsten/Ryan)")
        return 1
    if args.open:
        import webbrowser
        webbrowser.open("file://" + os.path.abspath(page))
    print("💡 Entscheidung getroffen? Dann im Deploy hinterlegen:\n"
          "   .github/workflows/deploy.yml → audio_profile / --voice-de / --voice-en\n"
          "   oder lokal: python3 scripts/generate_reader_audio.py --profile narrator --force")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
