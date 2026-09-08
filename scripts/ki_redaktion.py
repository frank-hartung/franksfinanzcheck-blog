#!/usr/bin/env python3
# ============================================================
#  KI-REDAKTION – Orchestrator (Blog-Automatik nach dem Schema
#  „Claude für lange Artikel + ChatGPT für schnelle News +
#  Jasper für SEO")
#  ------------------------------------------------------------
#  Steuert die drei Rollen:
#
#    Rolle Claude   → scripts/claude_writer.py   (lange Premium-Artikel)
#    Rolle ChatGPT  → scripts/news_writer.py     (schnelle News-Kompakt)
#    Rolle Jasper   → scripts/jasper_seo.py      (SEO-Pass/-Fixes)
#
#  KOSTEN-REGEL (Dauervorgabe): Die Automatik nutzt ausschließlich
#  Gratis-Zugänge (Groq/Gemini – bereits im Repo etabliert). Paid-
#  APIs (Anthropic/OpenAI/Jasper) werden NIE automatisch angerufen.
#  Jasper selbst hat keine öffentliche API – die Rolle ist als
#  Funktions-Äquivalent an Bord (siehe KI-REDAKTION.md).
#
#  VERÖFFENTLICHUNG: Die KI-Redaktion schreibt ausschließlich
#  Entwürfe (draft: true, ohne cadence_wait). Live geht ein Artikel
#  erst, wenn er bewusst freigegeben wird:
#
#    python3 scripts/ki_redaktion.py --promote <slug>
#
#  → setzt den Artikel über den bewährten Park-Mechanismus in die
#    Re-Queue; cadence_guard hebt ihn am nächsten Publikationstag
#    (Mo/Mi/Fr, max. 2–3/Tag) ins Live-Blog. Die Gates der
#    Content-Engine v2 bleiben damit der einzige Veröffentlichungsweg.
#
#  Nutzung:
#    python3 scripts/ki_redaktion.py --run                # lang + SEO
#    python3 scripts/ki_redaktion.py --run --rolle news
#    python3 scripts/ki_redaktion.py --status
#    python3 scripts/ki_redaktion.py --promote <slug>
#    python3 scripts/ki_redaktion.py --selftest
# ============================================================
from __future__ import annotations

import argparse
import datetime
import os
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import ki_shared as ks  # noqa: E402
import post_utils  # noqa: E402

SCRIPTS = os.path.join(BLOG_DIR, "scripts")

ROLLEN = {
    "lang": ("claude_writer.py", "Rolle Claude (langer Premium-Artikel)"),
    "news": ("news_writer.py", "Rolle ChatGPT (schnelle News)"),
    "seo": ("jasper_seo.py", "Rolle Jasper (SEO-Pass)"),
}


def _run_script(script: str, extra: list) -> int:
    cmd = [sys.executable, os.path.join(SCRIPTS, script)] + extra
    print(f"\n▶ {script} {' '.join(extra)}")
    proc = subprocess.run(cmd, cwd=BLOG_DIR)
    return proc.returncode


def cmd_run(args) -> int:
    cfg = ks.load_config()
    rc_total = 0
    if args.rolle in (None, "alle", "lang"):
        rc = _run_script(ROLLEN["lang"][0],
                         (["--offline"] if args.offline else []))
        rc_total |= (rc != 0)
    if args.rolle in (None, "alle", "news"):
        rc = _run_script(ROLLEN["news"][0],
                         (["--offline"] if args.offline else []))
        rc_total |= (rc != 0)
    if args.rolle in (None, "alle", "seo"):
        rc = _run_script(ROLLEN["seo"][0],
                         ["--new-only"] + (["--fix"] if args.fix else []))
        rc_total |= (rc != 0)
    if cfg.get("auto_veroeffentlichen"):
        print("\n⚠ In data/ki_redaktion.yaml steht auto_veroeffentlichen: "
              "true – ignoriert (Dauervorgabe: Veröffentlichung NIE "
              "automatisch). Bitte Eintrag entfernen.")
    return 1 if rc_total else 0


def _ki_drafts() -> list:
    import re
    out = []
    for path in post_utils.list_post_paths():
        try:
            with open(path, encoding="utf-8") as fh:
                head = fh.read(3000)
        except OSError:
            continue
        if "ki_redaktion:" not in head:
            continue
        draft = bool(re.search(r"(?m)^draft:\s*true", head))
        m = re.search(r'(?m)^ki_redaktion:\s*"?([a-z]+)', head)
        out.append({"path": path,
                    "slug": post_utils.slug_of(path),
                    "draft": draft,
                    "rolle": m.group(1) if m else "?",
                    "todo": "TODO(KI-REDAKTION" in head})
    return out


def cmd_status(_args) -> int:
    drafts = _ki_drafts()
    if not drafts:
        print("Keine KI-Redaktions-Entwürfe vorhanden.")
        return 0
    print(f"KI-Redaktion – {len(drafts)} Beitrag/Beiträge im System:\n")
    for d in sorted(drafts, key=lambda x: x["slug"], reverse=True):
        zustand = ("ENTWURF" if d["draft"] else "live")
        if d["todo"]:
            zustand += " (Offline-Gerüst, Inhalt fehlt!)"
        print(f"  • [{d['rolle']:<7}] {d['slug']}  → {zustand}")
    print("\nFreigabe:  python3 scripts/ki_redaktion.py --promote <slug>")
    return 0


def cmd_promote(args) -> int:
    import re
    import park_state
    slug = args.promote
    path = post_utils.post_path(slug)
    if not os.path.exists(path):
        print(f"❌ Artikel nicht gefunden: {slug}")
        return 1
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    if "ki_redaktion:" not in content:
        print("❌ Dieser Artikel stammt nicht aus der KI-Redaktion – "
              "Promote nur für KI-Entwürfe (Frank-Schutz).")
        return 1
    if not re.search(r"(?m)^draft:\s*true", content):
        print("ℹ Artikel ist bereits live bzw. nicht mehr Entwurf.")
        return 0
    if "TODO(KI-REDAKTION" in content:
        print("❌ Offline-Gerüst ohne Inhalt – erst fertigstellen, "
              "dann promoten.")
        return 1
    try:
        import length_policy
        _, chars = length_policy.measure(content)
        if chars < length_policy.POSTS["target_min_chars"]:
            print(f"❌ Fließtext {chars:,} Zeichen – unter Floor "
                  f"({length_policy.POSTS['target_min_chars']:,}). "
                  "Erst verlängern (Engine heilt sonst beim nächsten Lauf).")
            return 1
    except Exception:  # noqa: BLE001
        pass

    today = datetime.date.today()
    if not park_state.rearm(path, "KI-Redaktion: bewusst freigegeben "
                            f"({today.isoformat()})",
                            park_state.now_utc_iso()):
        print("❌ Park-Mechanismus konnte den Artikel nicht einreihen.")
        return 1
    park_state.set_field(path, "ki_redaktion_status", "freigegeben")
    print(f"✅ {slug} ist jetzt in der Re-Queue (cadence_wait: true).")
    print("   cadence_guard veröffentlicht ihn am nächsten Publikationstag "
          "(Mo/Mi/Fr) innerhalb des Tageslimits (2–3 Artikel).")
    ks.write_report([
        f"- **Freigabe:** `{slug}` bewusst in die Re-Queue gelegt "
        f"({today.isoformat()}). Publikation über cadence_guard.",
    ])
    return 0


def cmd_selftest(_args) -> int:
    """Fail-closed-Selbsttest (Konvention des Repos): Exit 2 bei Defekt."""
    print("KI-Redaktion – Selbsttest")
    ok = True

    for script, label in ROLLEN.values():
        p = os.path.join(SCRIPTS, script)
        if not os.path.exists(p):
            print(f"  ❌ fehlt: {script} ({label})")
            ok = False
        else:
            print(f"  ✅ {script} vorhanden")

    cfg = ks.load_config()
    for key in ("anbieter_kette_lang", "anbieter_kette_news"):
        chain = cfg.get(key) or []
        paid_only = all(p in ("claude", "openai") for p in chain)
        if paid_only:
            print(f"  ❌ {key} enthält nur Paid-Provider – Kosten-Regel "
                  "verletzt!")
            ok = False
        elif chain:
            print(f"  ✅ {key}: {' → '.join(chain)}")
        else:
            print(f"  ❌ {key} leer")
            ok = False
    if cfg.get("auto_veroeffentlichen"):
        print("  ❌ auto_veroeffentlichen darf nicht true sein "
              "(Dauervorgabe)")
        ok = False
    else:
        print("  ✅ auto_veroeffentlichen: false (Veröffentlichung nie "
              "automatisch)")

    try:
        import llm_client
        provs = llm_client.available_providers()
        print(f"  ✅ llm_client lädt – aktive Provider: "
              f"{', '.join(provs) if provs else '(keine Keys – Offline-/Gerüst-Modus)'}")
        if any(p in provs for p in ("claude", "openai")):
            print("     Hinweis: Paid-Key gefunden. Er wird NUR verwendet, "
                  "wenn er in der Anbieter-Kette steht (Default: nein).")
    except Exception as e:  # noqa: BLE001
        print(f"  ❌ llm_client defekt: {e}")
        ok = False

    try:
        t = ks.pick_topic()
        print(f"  ✅ Themenpool lesbar (nächstes freies Thema: "
              f"„{(t or {}).get('title', '– Pool leer –')}“)")
    except Exception as e:  # noqa: BLE001
        print(f"  ❌ Themenpool defekt: {e}")
        ok = False

    print("\nErgebnis:", "ALLE PRÜFUNGEN OK ✅" if ok else "FEHLER ❌")
    return 0 if ok else 2


def main() -> int:
    ap = argparse.ArgumentParser(
        description="KI-Redaktion: Orchestrator der Blog-Automatik "
                    "(Claude/ChatGPT/Jasper-Schema, nur Gratis-Zugänge)")
    ap.add_argument("--run", action="store_true", help="Produktion starten")
    ap.add_argument("--rolle", choices=["alle", "lang", "news", "seo"],
                    default="alle", help="welche Rolle laufen soll")
    ap.add_argument("--offline", action="store_true",
                    help="Writer ohne KI-API testen (Gerüst-Entwürfe)")
    ap.add_argument("--fix", action="store_true",
                    help="dem SEO-Pass sichere Auto-Fixes erlauben")
    ap.add_argument("--status", action="store_true",
                    help="alle KI-Entwürfe auflisten")
    ap.add_argument("--promote", metavar="SLUG",
                    help="Entwurf bewusst in die Re-Queue legen")
    ap.add_argument("--selftest", action="store_true",
                    help="Bausteine prüfen (Exit 2 = Defekt)")
    args = ap.parse_args()

    if args.selftest:
        return cmd_selftest(args)
    if args.status:
        return cmd_status(args)
    if args.promote:
        return cmd_promote(args)
    if args.run:
        return cmd_run(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
