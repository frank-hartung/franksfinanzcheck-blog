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
#  Gratis-Zugänge. Die Rolle „ChatGPT" läuft seit 03.10.2026 auf
#  OpenAIs offenem Modell openai/gpt-oss-120b bei drei Gratis-Hostern
#  (Groq → NVIDIA → Cloudflare), Gemini als Gegenprobe. Paid-
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
#  FACHFREIGABE-VERTRAG (seit 13.10.2026, Dauerheilung #734): Die Writer
#  schreiben YMYL-Hochrisiko nur auf ausdrückliche Beauftragung
#  (`--fachfreigabe`, WIP-Limit der Bahn) und immer mit Prüfgerüst;
#  `--promote` verweigert Hochrisiko-Entwürfe ohne gültige redaktionelle
#  Freigabe. Ein `--run` beauftragt nie – der Vertrag sitzt in ki_shared.
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


def _fachfreigabe_fehlt(path: str) -> str:
    """Leer, wenn der Entwurf promotet werden darf – sonst der Grund.

    Fail-closed: Ist das Redaktions-Gate nicht ausführbar oder der Artikel
    nicht lesbar, gilt das als fehlende Freigabe.
    """
    try:
        import editorial_review_gate as erg
        urteil = erg.evaluate_path(path)
    except Exception as exc:  # noqa: BLE001 – ohne Messung keine Freigabe
        return (f"Redaktions-Gate nicht ausführbar ({exc.__class__.__name__}: "
                f"{exc}) – fail-closed, keine Freigabe.")
    risiko = urteil.get("risk")
    befunde = urteil.get("findings") or []
    if urteil.get("approved") or risiko not in (erg.RISK_HIGH, "unbekannt"):
        return ""
    if risiko == "unbekannt":
        detail = "; ".join(str(f.get("detail", "")) for f in befunde) or "–"
        return (f"Redaktions-Gate kann den Entwurf nicht lesen ({detail}) – "
                "Risikoklasse unbekannt, fail-closed, keine Freigabe.")
    codes = ", ".join(sorted({f.get("code", "?") for f in befunde})) or "–"
    return (f"YMYL-Hochrisiko ohne gültige redaktionelle Freigabe ({codes}). "
            "Die KI-Redaktion legt solche Entwürfe nicht in die Re-Queue: "
            "Das Publish-Gate würde sie dort nur fail-closed halten.")


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
    # DOPPELBESITZ-SPERRE (05.10.2026, WF-B594/#594): Seit der
    # Reserve-Bestandsaufnahme kann ein KI-Entwurf bewusst in den Vorrat
    # übernommen worden sein (`reserve: true`). Würde er zusätzlich in die
    # Kadenz-Queue wandern, hätten zwei Fließbänder denselben Artikel – genau
    # die Geisterzustände, die #387 gekostet haben.
    if re.search(r"(?m)^reserve:\s*true\s*$", content):
        print("❌ Dieser Entwurf gehört bereits dem Content-Vorrat "
              "(reserve: true). Entweder die Reserve veröffentlicht ihn "
              "regulär – oder du nimmst ihm zuerst die Fahne.")
        print("   Bestand ansehen: python3 scripts/reserve_intake.py --md")
        return 1
    if "TODO(KI-REDAKTION" in content:
        print("❌ Offline-Gerüst ohne Inhalt – erst fertigstellen, "
              "dann promoten.")
        return 1
    # FACHFREIGABE-SPERRE (13.10.2026, Dauerheilung #734): Ein Hochrisiko-
    # Entwurf ohne gültige redaktionelle Freigabe hätte in der Re-Queue nur
    # einen Publikationsslot belegt, bis das Publish-Gate ihn fail-closed
    # hält. Gemessen wird mit der Messfunktion des Gates selbst
    # (`evaluate_path`) – keine zweite Regel (C19).
    ymyl_grund = _fachfreigabe_fehlt(path)
    if ymyl_grund:
        print(f"❌ {ymyl_grund}")
        print("   Ablauf: Prüfer, Belegkette, Zahlenprotokoll, dann "
              "`python3 scripts/editorial_review_gate.py --seal --file "
              f"content/posts/{slug}/index.md` – siehe "
              "docs/ANLEITUNG-REDAKTIONELLE-YMYL-PRUEFUNG.md.")
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
    import llm_client as _lc
    for key in ("anbieter_kette_lang", "anbieter_kette_news"):
        chain = cfg.get(key) or []
        # Kostenklasse kommt aus EINER Quelle (llm_client.KOSTENKLASSE),
        # damit ein neuer Anbieter nicht versehentlich als gratis gilt.
        bezahlt = [p for p in chain if not _lc.ist_gratis(p)]
        if chain and bezahlt:
            print(f"  ❌ {key} enthält kostenpflichtige Provider "
                  f"({', '.join(bezahlt)}) – Kosten-Regel verletzt!")
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
        if t and ks.bahn_fuer(t.get("title"), t.get("keywords"),
                              t.get("pillar")) != ks.BAHN_AUTO:
            print(f"  ❌ Themenpool liefert ohne Beauftragung ein YMYL-Thema "
                  f"(„{t.get('title')}“) – AUTO-Filter wirkungslos (#734)")
            ok = False
        else:
            print(f"  ✅ Themenpool lesbar (nächstes freies AUTO-Thema: "
                  f"„{(t or {}).get('title', '– Pool leer –')}“)")
    except Exception as e:  # noqa: BLE001
        print(f"  ❌ Themenpool defekt: {e}")
        ok = False

    ok = _selbsttest_fachfreigabe() and ok

    print("\nErgebnis:", "ALLE PRÜFUNGEN OK ✅" if ok else "FEHLER ❌")
    return 0 if ok else 2


# Material des Vorfalls vom 13.10.2026 (Issue #734): genau so hat der
# News-Writer den Entwurf gebaut, der als E03 in der Prüfqueue landete.
VORFALL_734 = {
    "title": "Versicherung-Update: Was sich jetzt für dich ändert",
    "keywords": ["Versicherung-Update: Was sich jetzt für dich ändert"],
    "pillar": "versicherungen",
    "tags": ["Versicherungen vergleichen"],
}


def _selbsttest_fachfreigabe() -> bool:
    """Fachfreigabe-Vertrag der Writer – funktional, offline, ohne Bestand.

    Die WIP-Lage wird für die Probe festgenagelt; der echte Bestand spielt
    keine Rolle (uhrfest und unabhängig davon, wie voll der Prüfstapel ist).
    """
    v = VORFALL_734
    fehler: list[str] = []

    def frontmatter(beauftragt: bool) -> str:
        return ks.build_frontmatter(
            title=v["title"], description="Selbsttest Fachfreigabe-Vertrag",
            tags=v["tags"], pillar=v["pillar"], keywords=v["keywords"],
            rolle="chatgpt", news=True, kategorie="versicherung",
            fachfreigabe=beauftragt)

    try:
        if ks.bahn_fuer(v["title"], v["keywords"], v["pillar"]) \
                != ks.BAHN_FACHFREIGABE:
            fehler.append("der Vorfall vom 13.10.2026 würde als AUTO "
                          "eingestuft")
        if ks.bahn_fuer("Stromfresser im Haushalt entlarven", [],
                        "strom-sparen") != ks.BAHN_AUTO:
            fehler.append("ein Spar-Thema landet fälschlich in der "
                          "Fachfreigabe-Bahn")

        # 1) Ohne Beauftragung entsteht kein YMYL-Frontmatter.
        try:
            frontmatter(False)
            fehler.append("build_frontmatter schreibt YMYL ohne Beauftragung")
        except ks.FachfreigabeErforderlich:
            pass

        # 2) Beauftragt + offene Bahn: Prüfgerüst hoch/ausstehend, nie
        #    „freigegeben“ – die Freigabe bleibt beim Menschen.
        alt = ks.fachfreigabe_lage
        ks.fachfreigabe_lage = lambda: {"geoeffnet": True,
                                        "grund": "Selbsttest"}
        try:
            fm = frontmatter(True)
        finally:
            ks.fachfreigabe_lage = alt
        if ('risikoklasse: "hoch"' not in fm
                or 'status: "ausstehend"' not in fm
                or 'status: "freigegeben"' in fm):
            fehler.append("beauftragter YMYL-Entwurf ohne korrektes "
                          "Prüfgerüst (hoch/ausstehend)")

        # 3) Geschlossene Bahn sperrt auch die Beauftragung (WIP-Limit).
        try:
            ks.fachfreigabe_pruefen(
                title=v["title"], keywords=v["keywords"], pillar=v["pillar"],
                beauftragt=True,
                lage={"geoeffnet": False, "grund": "Selbsttest: Limit"})
            fehler.append("WIP-Limit der Fachfreigabe-Bahn wirkungslos")
        except ks.FachfreigabeErforderlich:
            pass
    except Exception as e:  # noqa: BLE001
        fehler.append(f"Vertrag nicht prüfbar ({e.__class__.__name__}: {e})")

    if fehler:
        for f in fehler:
            print(f"  ❌ Fachfreigabe-Vertrag (#734): {f}")
        return False
    print("  ✅ Fachfreigabe-Vertrag (#734): YMYL nur auf Beauftragung, mit "
          "Prüfgerüst, WIP-Limit wirkt")
    return True


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
