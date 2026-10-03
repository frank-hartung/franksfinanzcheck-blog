#!/usr/bin/env python3
# ============================================================
#  SCHALTWERK – AKTIONEN (die „dann …“-Seite des Zapier-Nachbaus)
#  ------------------------------------------------------------
#  Jede Aktion ist eine Funktion:
#
#      def aktion_xy(params: dict, daten: dict, ctx: dict) -> dict
#
#  Rückgabe:
#      {"status": "ok" | "standby" | "uebersprungen" | "fehler",
#       "meldung": "…", ...}
#
#  STATUS-VERTRAG (wichtig für die Betriebsruhe):
#    ok            Aktion ist wirklich passiert
#    standby       Kanal ist nicht eingerichtet → KEIN Fehler, KEIN Alarm
#    uebersprungen bewusst nichts getan (Probelauf, Gate, Sperrfrist)
#    fehler        echtes Problem → Exit 2 des Laufs → Alarmierung
#
#  HARTE REGELN:
#    · Kein Affiliate-Link verlässt je den Blog (social_gate prüft das).
#    · Jeder Social-Text läuft durch `social_gate.check` – fail-closed.
#    · Agent-Reach-Signale landen nur in der Kuratierungsablage,
#      nie direkt in einem Posting.
#    · Im Probelauf (`--dry-run`) wird NICHTS gesendet und NICHTS
#      geschrieben.
# ============================================================
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

VORSCHLAEGE_PATH = os.path.join(BLOG_DIR, "data", "agent_reach", "themen_vorschlaege.yaml")


# ----------------------------------------------------------------- Helfer
def ok(meldung: str, **extra) -> dict:
    return {"status": "ok", "meldung": meldung, **extra}


def standby(meldung: str, **extra) -> dict:
    return {"status": "standby", "meldung": meldung, **extra}


def uebersprungen(meldung: str, **extra) -> dict:
    return {"status": "uebersprungen", "meldung": meldung, **extra}


def fehler(meldung: str, **extra) -> dict:
    return {"status": "fehler", "meldung": meldung, **extra}


def _social_cfg() -> dict:
    import social_channels as sch

    return sch.load_config()


def kanal_zustand(cfg: dict | None = None) -> list[dict]:
    """Zustand aller Kanäle – Grundlage für Cockpit und Standby-Wache."""
    import social_channels as sch

    cfg = cfg if cfg is not None else _social_cfg()
    zeilen = []
    for cid, ch in sorted(sch.channel_map(cfg).items(),
                          key=lambda kv: int((kv[1] or {}).get("priority") or 99)):
        enabled = bool((ch or {}).get("enabled"))
        bereit, grund = False, "in channels.yaml deaktiviert"
        if enabled:
            adapter = sch.get_adapter(cid, cfg)
            if adapter is None:
                grund = "Adapter nicht ladbar"
            else:
                bereit, grund = adapter.configured()
        zeilen.append({
            "id": cid,
            "label": (ch or {}).get("label") or cid,
            "enabled": enabled,
            "bereit": bool(bereit),
            "grund": "" if bereit else grund,
            "secrets": list((ch or {}).get("secrets") or []),
            "vars": list((ch or {}).get("vars") or []),
        })
    return zeilen


def _artikel_laden(slug: str) -> dict | None:
    import social_copywriter as copy

    if not slug:
        return None
    for art in copy.article_pool():
        if art.get("slug") == slug:
            return art
    return None


# ========================================================= 1 · Social posten
def aktion_social_post(params: dict, daten: dict, ctx: dict) -> dict:
    """Veröffentlicht EINEN Beitrag auf EINEM Kanal – mit Gate davor.

    params:
      kanal         Kanal-id aus data/social/channels.yaml (Pflicht)
      artikel_slug  Artikel, über den gepostet wird (optional; sonst aus Trigger)
      winkel        Erzählwinkel (nutzen|zahl|takeaway|frage|mythos|…)
      text          freier Text statt generierter Fassung (optional)
      mit_bild      Bild anhängen (Standard: ja, wenn der Kanal es kann)
    """
    import social_channels as sch
    import social_copywriter as copy
    import social_gate as gate

    kanal = str(params.get("kanal") or "").strip()
    if not kanal:
        return fehler("social_post ohne Kanal")

    cfg = _social_cfg()
    ch = sch.channel_map(cfg).get(kanal)
    if not ch:
        return fehler(f"Kanal {kanal!r} steht nicht in channels.yaml")
    if not ch.get("enabled"):
        return standby(f"{kanal}: in channels.yaml deaktiviert")

    adapter = sch.get_adapter(kanal, cfg)
    if adapter is None:
        return fehler(f"Kanal {kanal!r}: Adapter nicht ladbar")
    bereit, grund = adapter.configured()
    if not bereit:
        return standby(f"{kanal}: {grund} – Kanal wartet auf Zugangsdaten")

    meta = sch.meta_of(cfg)
    slug = str(params.get("artikel_slug")
               or (daten.get("artikel") or {}).get("slug") or "").strip()
    artikel = _artikel_laden(slug) if slug else None

    freitext = str(params.get("text") or "").strip()
    if artikel:
        winkel = str(params.get("winkel") or "nutzen")
        pkg = copy.compose(artikel, kanal, ch, winkel, meta,
                           use_llm=bool(params.get("ki_politur", True)))
        if freitext:
            pkg["text"] = freitext
    elif freitext:
        pkg = {"text": freitext, "url": str(params.get("url") or daten.get("url") or ""),
               "article": {}, "hashtags": [], "angle": "frei"}
    else:
        return fehler("social_post: weder Artikel noch Text vorhanden")

    # Bild (Kanäle mit Bildpflicht brauchen es zwingend)
    if params.get("mit_bild", True) and artikel:
        try:
            import social_studio as studio

            pfad, url = studio.resolve_media(artikel, ch, meta)
            pkg["media_path"] = pfad
            pkg["media_url"] = url if str(url).startswith("https://") else ""
        except Exception as exc:  # noqa: BLE001 – Bild ist nie kritisch
            pkg.setdefault("media_path", "")
            pkg.setdefault("media_url", "")
            if ctx.get("verbose"):
                print(f"   ⚠ Bildaufbereitung {kanal}: {exc}")

    # Hartes Gate – fail-closed
    try:
        import social_planner as planner

        verlauf = [e for e in (planner.load_state().get("history") or [])
                   if e.get("channel") == kanal]
    except Exception:  # noqa: BLE001
        verlauf = []
    freigabe, verstoesse, _ = gate.check(pkg, ch, meta, verlauf)
    if not freigabe:
        return uebersprungen(f"{kanal}: Gate hat abgelehnt – " + "; ".join(verstoesse[:3]))

    if ctx.get("dry_run"):
        vorschau = (pkg.get("text") or "").replace("\n", " ⏎ ")[:140]
        return uebersprungen(f"{kanal} (Probelauf): {vorschau}")

    res = adapter.publish(pkg)
    if getattr(res, "skipped", False):
        return standby(f"{kanal}: {res.error}")
    if not getattr(res, "ok", False):
        return fehler(f"{kanal}: {res.error}")

    # Erfolg im Social-State protokollieren (kein Doppelpost durch den Autopiloten)
    try:
        import social_planner as planner

        state = planner.load_state()
        planner.record_history(state, {
            "posted_at": planner.iso(planner.berlin_now()),
            "channel": kanal, "slug": slug, "title": (artikel or {}).get("title", ""),
            "angle": pkg.get("angle", ""), "url": res.url, "ok": True,
            "text": (pkg.get("text") or "")[:400], "ref": "schaltwerk",
        })
        planner.save_state(state)
    except Exception as exc:  # noqa: BLE001 – Protokoll darf den Post nicht entwerten
        if ctx.get("verbose"):
            print(f"   ⚠ Social-State nicht fortgeschrieben: {exc}")

    return ok(f"{kanal}: veröffentlicht → {res.url or 'ohne URL'}", url=res.url)


def aktion_social_welle(params: dict, daten: dict, ctx: dict) -> dict:
    """Ein Artikel auf MEHREREN Kanälen (Launch-Welle, Standby wird übersprungen).

    params: kanaele [Liste] (leer = alle sendebereiten), winkel, artikel_slug
    """
    kanaele = params.get("kanaele")
    if not kanaele:
        kanaele = [k["id"] for k in kanal_zustand() if k["bereit"]]
    if isinstance(kanaele, str):
        kanaele = [k.strip() for k in kanaele.split(",") if k.strip()]

    gesendet, warten, probleme = [], [], []
    for kanal in kanaele:
        res = aktion_social_post({**params, "kanal": kanal}, daten, ctx)
        if res.get("status") == "ok":
            gesendet.append(kanal)
        elif res.get("status") == "standby":
            warten.append(kanal)
        elif res.get("status") == "fehler":
            probleme.append(f"{kanal} ({res.get('meldung')})")
        else:
            warten.append(f"{kanal}*")

    meldung = (f"gesendet: {', '.join(gesendet) or '–'} · "
               f"Standby/übersprungen: {', '.join(warten) or '–'}")
    if probleme:
        return fehler(meldung + " · Fehler: " + "; ".join(probleme))
    if gesendet:
        return ok(meldung)
    return standby(meldung or "kein sendebereiter Kanal")


def aktion_social_autopilot_lauf(params: dict, daten: dict, ctx: dict) -> dict:
    """Startet den bestehenden Social-Autopiloten (Plan → Text → Gate → Versand).

    So bleibt die Planungs-Intelligenz an EINER Stelle; das Schaltwerk
    entscheidet nur, WANN sie läuft.
    params: kanal (optional), limit (0 = alle fälligen), modus (run|plan)
    """
    try:
        import social_channels as sch
        import social_studio as studio
    except Exception as exc:  # noqa: BLE001
        return fehler(f"Social-Autopilot nicht ladbar: {exc}")

    cfg = sch.load_config()
    modus = str(params.get("modus") or "run")
    if modus == "plan":
        try:
            import social_copywriter as copy
            import social_planner as planner

            state = planner.load_state()
            pool = copy.article_pool()
            plan = planner.build_plan(cfg, pool, state)
            if ctx.get("dry_run"):
                return uebersprungen(f"Probelauf: Plan hätte {len(planner.planned_items(plan))} Posten")
            planner.prune(plan)
            planner.save_schedule(plan)
            return ok(f"Redaktionsplan erneuert: {len(planner.planned_items(plan))} Posten")
        except Exception as exc:  # noqa: BLE001
            return fehler(f"Planung gescheitert: {exc}")

    try:
        bericht = studio.run_once(cfg, dry_run=bool(ctx.get("dry_run")),
                                  channel=str(params.get("kanal") or ""),
                                  limit=int(params.get("limit") or 0))
    except Exception as exc:  # noqa: BLE001
        return fehler(f"Autopilot-Lauf gescheitert: {exc}")

    if isinstance(bericht, dict):
        gesendet = bericht.get("sent") or bericht.get("gesendet") or 0
        misslungen = bericht.get("failed") or bericht.get("fehler") or 0
        if misslungen:
            return fehler(f"Autopilot: {gesendet} gesendet, {misslungen} gescheitert")
        return ok(f"Autopilot: {gesendet} Beiträge verarbeitet")
    return ok("Autopilot-Lauf beendet")


# ================================================== 2 · Kuratierung (lesend)
def aktion_themen_vorschlag(params: dict, daten: dict, ctx: dict) -> dict:
    """Legt ein Agent-Reach-Signal zur MENSCHLICHEN Kuratierung ab.

    Bewusst kein Auto-Post: Der Brief ist eine Signalsammlung, kein Inhalt
    (docs/ANLEITUNG-AGENT-REACH.md, Abschnitt 6). Von hier übernimmt die
    Redaktion nach Quellenprüfung in data/topics.yaml bzw.
    data/aktuelle_entwicklungen.yaml.
    """
    import yaml

    titel = str(params.get("titel") or daten.get("titel") or "").strip()
    if not titel:
        return uebersprungen("Signal ohne Titel")
    eintrag = {
        "titel": titel[:300],
        "url": str(params.get("url") or daten.get("url") or "")[:500],
        "quelle": str(params.get("quelle") or daten.get("quelle") or "")[:200],
        "erfasst": str(daten.get("jetzt") or "")[:19],
        "brief": str(daten.get("brief") or ""),
        "status": "offen",      # offen | uebernommen | verworfen
        "notiz": str(params.get("notiz") or ""),
    }
    if ctx.get("dry_run"):
        return uebersprungen(f"Probelauf: Vorschlag „{titel[:60]}“")

    os.makedirs(os.path.dirname(VORSCHLAEGE_PATH), exist_ok=True)
    try:
        with open(VORSCHLAEGE_PATH, encoding="utf-8") as fh:
            bestand = yaml.safe_load(fh) or {}
    except (OSError, Exception):  # noqa: BLE001
        bestand = {}
    if not isinstance(bestand, dict):
        bestand = {}
    bestand.setdefault("version", 1)
    liste = bestand.setdefault("vorschlaege", [])
    if any(str((v or {}).get("url")) == eintrag["url"] and eintrag["url"] for v in liste):
        return uebersprungen(f"Vorschlag liegt bereits vor: {titel[:50]}")
    liste.insert(0, eintrag)
    bestand["vorschlaege"] = liste[:150]
    bestand["zuletzt_ergaenzt"] = str(daten.get("jetzt") or "")[:19]

    kopf = (
        "# ============================================================\n"
        "#  THEMEN-VORSCHLÄGE aus Agent Reach (LESEND erfasst)\n"
        "#  ------------------------------------------------------------\n"
        "#  Automatisch befüllt von scripts/schaltwerk.py – das ist eine\n"
        "#  SIGNALSAMMLUNG, kein freigegebener Inhalt. Übernahme nur nach\n"
        "#  Quellenprüfung durch einen Menschen in data/topics.yaml bzw.\n"
        "#  data/aktuelle_entwicklungen.yaml (KI-Redaktions-Statut).\n"
        "#  status: offen → uebernommen | verworfen\n"
        "# ============================================================\n"
    )
    with open(VORSCHLAEGE_PATH, "w", encoding="utf-8") as fh:
        fh.write(kopf)
        yaml.safe_dump(bestand, fh, allow_unicode=True, sort_keys=False, width=100)
    return ok(f"Themen-Vorschlag abgelegt: {titel[:70]}")


# ======================================================= 3 · Benachrichtigen
def aktion_telegram_nachricht(params: dict, daten: dict, ctx: dict) -> dict:
    """Direkte Telegram-Nachricht (Betriebsmeldung, nicht der Redaktionskanal)."""
    import social_channels as sch

    text = str(params.get("text") or "").strip()
    if not text:
        return uebersprungen("leere Nachricht")
    cfg = _social_cfg()
    adapter = sch.get_adapter("telegram", cfg)
    if adapter is None:
        return fehler("Telegram-Adapter nicht ladbar")
    bereit, grund = adapter.configured()
    if not bereit:
        return standby(f"telegram: {grund}")
    if ctx.get("dry_run"):
        return uebersprungen(f"Probelauf Telegram: {text[:90]}")
    res = adapter.publish({"text": text, "url": str(params.get("url") or "")})
    if getattr(res, "ok", False):
        return ok("Telegram-Nachricht zugestellt")
    if getattr(res, "skipped", False):
        return standby(f"telegram: {res.error}")
    return fehler(f"telegram: {res.error}")


def aktion_github_issue(params: dict, daten: dict, ctx: dict) -> dict:
    """Legt ein GitHub-Issue an (Duplikate werden erkannt). Braucht `gh` + Token."""
    titel = str(params.get("titel") or "").strip()
    if not titel:
        return uebersprungen("Issue ohne Titel")
    body = str(params.get("text") or params.get("body") or "")
    label = str(params.get("label") or "schaltwerk")
    repo = os.environ.get("GITHUB_REPOSITORY") or ""
    if ctx.get("dry_run"):
        return uebersprungen(f"Probelauf Issue: {titel[:80]}")
    if not (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")):
        return standby("GH_TOKEN fehlt – Issue nicht erstellt")

    def gh(*argv) -> tuple[int, str]:
        try:
            p = subprocess.run(["gh", *argv], capture_output=True, text=True, timeout=60)
            return p.returncode, (p.stdout or "") + (p.stderr or "")
        except (OSError, subprocess.SubprocessError) as exc:
            return 1, str(exc)

    repo_args = ["--repo", repo] if repo else []
    gh("label", "create", label, *repo_args, "--color", "1d76db",
       "--description", "Schaltwerk: automatische Meldungen", "--force")
    rc, out = gh("issue", "list", *repo_args, "--state", "open",
                 "--search", f'in:title "{titel}"')
    if rc == 0 and titel[:40] in out:
        return uebersprungen("Issue existiert bereits – kein Duplikat")
    rc, out = gh("issue", "create", *repo_args, "--title", titel,
                 "--label", label, "--body", body or titel)
    if rc != 0:
        return fehler(f"Issue nicht erstellt: {out.strip()[:200]}")
    return ok(f"Issue erstellt: {titel[:70]}")


def aktion_workflow_starten(params: dict, daten: dict, ctx: dict) -> dict:
    """Startet einen anderen GitHub-Workflow (Multi-Step über Workflow-Grenzen).

    params: workflow (Dateiname, z. B. "pinterest-ai.yml"), felder {k: v}
    """
    wf = str(params.get("workflow") or "").strip()
    if not wf:
        return uebersprungen("kein Workflow angegeben")
    if ctx.get("dry_run"):
        return uebersprungen(f"Probelauf: Workflow {wf} würde starten")
    if not (os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")):
        return standby("GH_TOKEN fehlt – Workflow nicht gestartet")
    argv = ["gh", "workflow", "run", wf]
    repo = os.environ.get("GITHUB_REPOSITORY") or ""
    if repo:
        argv += ["--repo", repo]
    for key, wert in (params.get("felder") or {}).items():
        argv += ["-f", f"{key}={wert}"]
    try:
        p = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return fehler(f"Workflow-Start gescheitert: {exc}")
    if p.returncode != 0:
        return fehler(f"Workflow {wf}: {(p.stderr or '').strip()[:200]}")
    return ok(f"Workflow {wf} gestartet")


# ============================================================== 4 · Ablage
def aktion_datei_anhaengen(params: dict, daten: dict, ctx: dict) -> dict:
    """Hängt eine Zeile an eine Datei (JSONL-Journal, Merkliste, Report)."""
    rel = str(params.get("datei") or "").strip()
    text = str(params.get("text") or "")
    if not rel or not text:
        return uebersprungen("datei_anhaengen ohne Datei oder Text")
    if ".." in rel or rel.startswith("/"):
        return fehler("Pfad verlässt das Repository – abgelehnt")
    if ctx.get("dry_run"):
        return uebersprungen(f"Probelauf: {rel} ← {text[:70]}")
    voll = os.path.join(BLOG_DIR, rel)
    os.makedirs(os.path.dirname(voll), exist_ok=True)
    with open(voll, "a", encoding="utf-8") as fh:
        fh.write(text.rstrip("\n") + "\n")
    return ok(f"{rel}: Zeile ergänzt")


def aktion_protokoll(params: dict, daten: dict, ctx: dict) -> dict:
    """Reine Notiz in der Task-History (Zapiers „Only continue if“-Protokoll)."""
    text = str(params.get("text") or "").strip() or "(ohne Text)"
    print(f"   📝 {text[:200]}")
    return ok(text[:300])


# ============================================================== 5 · Whisper & n8n (0 € Stack)
def aktion_n8n_webhook(params: dict, daten: dict, ctx: dict) -> dict:
    """Sendet ein Ereignis per HTTP an einen n8n-Webhook."""
    import n8n_bridge

    event_typ = str(params.get("event_typ") or daten.get("typ") or "schaltwerk_event")
    webhook_url = params.get("webhook_url")
    dry_run = bool(ctx.get("dry_run"))

    res = n8n_bridge.dispatch_event_to_n8n(
        event_type=event_typ,
        payload=daten,
        webhook_url=webhook_url,
        dry_run=dry_run,
    )
    if res.get("status") == "success" or res.get("status") == "dry_run":
        return ok(f"n8n Webhook '{event_typ}' erfolgreich ausgelöst")
    elif res.get("status") == "standby":
        return standby(f"n8n nicht erreichbar: {res.get('message')}")
    else:
        return standby(f"n8n Webhook {res.get('status')}: {res.get('message', 'Keine Verbindung')}")


def aktion_whisper_transkribieren(params: dict, daten: dict, ctx: dict) -> dict:
    """Transkribiert eine Audiodatei lokal und erzeugt einen Blog-Entwurf."""
    import whisper_engine

    pfad = str(params.get("datei_pfad") or daten.get("pfad") or "")
    kategorie = str(params.get("kategorie") or daten.get("kategorie") or "spartipps")
    titel = params.get("titel") or daten.get("titel")

    if not pfad:
        return fehler("whisper_transkribieren: kein Dateipfad angegeben")

    if ctx.get("dry_run"):
        return uebersprungen(f"Probelauf: Whisper-Transkription für {pfad}")

    engine = whisper_engine.WhisperEngine(backend="auto")
    try:
        transcript = engine.transcribe(pfad)
        article = whisper_engine.transform_voice_to_article(
            transcript=transcript,
            kategorie=kategorie,
            custom_title=titel,
            audio_filename=os.path.basename(pfad),
        )
        drafts_dir = os.path.join(BLOG_DIR, "content", "drafts", article["slug"])
        os.makedirs(drafts_dir, exist_ok=True)
        draft_file = os.path.join(drafts_dir, "index.md")
        with open(draft_file, "w", encoding="utf-8") as fh:
            fh.write(article["markdown"])

        # Untertitel
        whisper_engine.export_vtt(transcript, os.path.join(drafts_dir, "transcript.vtt"))
        return ok(f"Entwurf aus Whisper-Aufnahme erzeugt: {draft_file}")
    except Exception as exc:  # noqa: BLE001
        return fehler(f"Whisper-Transkription gescheitert: {exc}")


def aktion_indexnow_ping(params: dict, daten: dict, ctx: dict) -> dict:
    """Sendet publizierte URLs an die IndexNow API (Bing/Yandex) – 0 € Kosten."""
    url = str(params.get("url") or daten.get("url") or "")
    if not url:
        slug = str(params.get("slug") or daten.get("artikel_slug") or daten.get("slug") or "")
        if slug:
            url = f"https://franksfinanzcheck.de/posts/{slug}/"
    if not url:
        return uebersprungen("indexnow_ping: keine URL vorhanden")

    if ctx.get("dry_run"):
        return uebersprungen(f"Probelauf: IndexNow Ping für {url}")

    key = "f009361665a54db687353f8680e6f5c7"
    body = {
        "host": "franksfinanzcheck.de",
        "key": key,
        "keyLocation": f"https://franksfinanzcheck.de/{key}.txt",
        "urlList": [url],
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = resp.status
        return ok(f"IndexNow Ping erfolgreich ({code}): {url}")
    except Exception as exc:  # noqa: BLE001
        return standby(f"IndexNow Ping fehlgeschlagen ({exc}) – unkritisch")


# ------------------------------------------------------------- Registrierung
AKTION = {
    "social_post": aktion_social_post,
    "social_welle": aktion_social_welle,
    "social_autopilot_lauf": aktion_social_autopilot_lauf,
    "themen_vorschlag": aktion_themen_vorschlag,
    "telegram_nachricht": aktion_telegram_nachricht,
    "github_issue": aktion_github_issue,
    "workflow_starten": aktion_workflow_starten,
    "datei_anhaengen": aktion_datei_anhaengen,
    "protokoll": aktion_protokoll,
    "n8n_webhook": aktion_n8n_webhook,
    "whisper_transkribieren": aktion_whisper_transkribieren,
    "indexnow_ping": aktion_indexnow_ping,
}


if __name__ == "__main__":  # pragma: no cover – Handprobe
    for k in kanal_zustand():
        zeichen = "✅" if k["bereit"] else ("⏸" if k["enabled"] else "⏹")
        print(f"{zeichen} {k['label']:22s} {k['grund']}")
