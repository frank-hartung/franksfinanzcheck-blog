#!/usr/bin/env python3
"""n8n_bridge.py — Schnittstelle zwischen self-hosted n8n & Blog-Ökosystem.

0 € LAUFENDE KOSTEN (Whisper lokal + n8n self-hosted + GitHub Pages)
    Dieses Modul verbindet das selbst gehostete n8n (Docker / Localhost / VPS)
    mit der bestehenden Blogautomatik (Schaltwerk, Content-Engine, GitHub Actions).

AUFGABEN:
    1. WEBHOOK-DISPATCHER (Blog → n8n):
       Sendet Ereignisse (neuer Artikel, Statuswechsel, Health-Check,
       Social-Media-Trigger) an n8n-Webhook-Endpunkte.

    2. WEBHOOK-EMPFÄNGER & INGEST (n8n → Blog):
       Nimmt Payloads von n8n entgegen (z. B. Sprachmemos vom Smartphone via
       Telegram/n8n-Formular, kuratierte Themen oder externe Trigger) und
       überträgt sie sicher in das Hugo-Dateisystem oder das Schaltwerk.

    3. INTEGRIERTER LOKALER HTTP-SERVER (Mock & Empfänger):
       Ermöglicht lokale Webhook-Tests ohne externe Tools (`--serve` / `--port`).

    4. STATUS- & SLA-ÜBERWACHUNG:
       Prüft Erreichbarkeit, Latenz und Antwortzeiten der n8n-Instanz.

AUFRUF:
    # Ereignis an n8n senden:
    python3 scripts/n8n_bridge.py --dispatch neuer_artikel --payload '{"slug":"2026-10-03-test","title":"Testartikel"}'

    # Eingehenden n8n-Payload verarbeiten (z.B. aus GitHub Action repository_dispatch):
    python3 scripts/n8n_bridge.py --receive-payload '{"typ":"voice_memo","audio_url":"...","titel":"Strom sparen"}'

    # n8n Health-Check & Latenz-Messung:
    python3 scripts/n8n_bridge.py --ping

    # Lokalen Test-Server starten (Port 5680):
    python3 scripts/n8n_bridge.py --serve --port 5680

    # Selbsttest (offline, fail-closed):
    python3 scripts/n8n_bridge.py --selftest
"""
from __future__ import annotations

import argparse
import contextlib
import datetime
import http.server
import json
import os
import re
import socketserver
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from typing import Any

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

BRIDGE_STATE_PATH = os.path.join(BLOG_DIR, "data", "n8n_bridge_state.json")
BRIDGE_LOG_PATH = os.path.join(BLOG_DIR, "data", "n8n_bridge_log.jsonl")

DEFAULT_N8N_URL = os.environ.get("N8N_URL", "http://127.0.0.1:5678")
DEFAULT_N8N_WEBHOOK_URL = os.environ.get(
    "N8N_WEBHOOK_URL",
    f"{DEFAULT_N8N_URL.rstrip('/')}/webhook/blog-events"
)
DEFAULT_WEBHOOK_TOKEN = os.environ.get("N8N_WEBHOOK_TOKEN", "")


# =====================================================================
#  HILFSFUNKTIONEN & PROTOKOLLIERUNG
# =====================================================================

def _iso_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def log_bridge_event(event_type: str, direction: str, payload: dict[str, Any], status: str, message: str = "") -> None:
    """Schreibt ein Ereignis in das n8n-Bridge-Protokoll."""
    os.makedirs(os.path.dirname(BRIDGE_LOG_PATH), exist_ok=True)
    entry = {
        "zeit": _iso_now(),
        "event_type": event_type,
        "richtung": direction,  # "outbound" (Blog->n8n) oder "inbound" (n8n->Blog)
        "status": status,
        "meldung": message,
        "payload_keys": list(payload.keys()) if isinstance(payload, dict) else [],
    }
    with open(BRIDGE_LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_bridge_state() -> dict[str, Any]:
    """Lädt den internen Zustand der Bridge."""
    try:
        with open(BRIDGE_STATE_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "version": 1,
            "letzter_dispatch": None,
            "letzter_empfang": None,
            "gesendete_events": 0,
            "empfangene_events": 0,
            "gescheiterte_events": 0,
        }


def save_bridge_state(state: dict[str, Any]) -> None:
    """Speichert den internen Zustand atomar."""
    os.makedirs(os.path.dirname(BRIDGE_STATE_PATH), exist_ok=True)
    tmp_path = f"{BRIDGE_STATE_PATH}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
    os.replace(tmp_path, BRIDGE_STATE_PATH)


# =====================================================================
#  OUTBOUND DISPATCHER (Blog → n8n)
# =====================================================================

def dispatch_event_to_n8n(
    event_type: str,
    payload: dict[str, Any],
    webhook_url: str | None = None,
    token: str | None = None,
    timeout: float = 10.0,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Sendet ein Ereignis über HTTP POST an einen n8n Webhook."""
    target_url = webhook_url or DEFAULT_N8N_WEBHOOK_URL
    auth_token = token or DEFAULT_WEBHOOK_TOKEN

    envelope = {
        "source": "franksfinanzcheck-blog",
        "event_type": event_type,
        "timestamp": _iso_now(),
        "data": payload,
    }

    if dry_run:
        print(f"🔍 [DRY-RUN] Sende Event '{event_type}' an {target_url}:")
        print(json.dumps(envelope, ensure_ascii=False, indent=2))
        return {"status": "dry_run", "url": target_url, "event_type": event_type}

    data_bytes = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "FranksFinanzcheck-n8n-Bridge/1.0",
    }
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
        headers["X-Webhook-Secret"] = auth_token

    req = urllib.request.Request(target_url, data=data_bytes, headers=headers, method="POST")

    state = load_bridge_state()
    try:
        start_time = time.time()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read().decode("utf-8")
            status_code = resp.status
            duration_ms = round((time.time() - start_time) * 1000, 1)

        state["gesendete_events"] = state.get("gesendete_events", 0) + 1
        state["letzter_dispatch"] = _iso_now()
        save_bridge_state(state)

        log_bridge_event(event_type, "outbound", payload, "success", f"HTTP {status_code} in {duration_ms}ms")
        return {
            "status": "success",
            "http_status": status_code,
            "duration_ms": duration_ms,
            "response": resp_body[:300],
        }

    except urllib.error.URLError as exc:
        state["gescheiterte_events"] = state.get("gescheiterte_events", 0) + 1
        save_bridge_state(state)
        error_msg = f"URLError: {exc}"
        log_bridge_event(event_type, "outbound", payload, "error", error_msg)
        return {"status": "error", "message": error_msg, "url": target_url}

    except Exception as exc:
        state["gescheiterte_events"] = state.get("gescheiterte_events", 0) + 1
        save_bridge_state(state)
        error_msg = f"{type(exc).__name__}: {exc}"
        log_bridge_event(event_type, "outbound", payload, "error", error_msg)
        return {"status": "error", "message": error_msg, "url": target_url}


# =====================================================================
#  INBOUND RECEIVER (n8n → Blog)
# =====================================================================

def handle_inbound_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Verarbeitet eingehende Payloads von n8n und leitet entsprechende Aktionen ein."""
    typ = payload.get("typ") or payload.get("event_type") or "unbekannt"
    daten = payload.get("data") or payload.get("daten") or payload
    state = load_bridge_state()

    print(f"📥 Verarbeite n8n-Payload: Typ='{typ}'...")

    if typ in ("voice_memo", "diktat", "audio_aufnahme"):
        import whisper_engine

        audio_text = daten.get("text")
        audio_file = daten.get("audio_file") or daten.get("file_path")
        kategorie = daten.get("kategorie", "spartipps")
        titel = daten.get("titel") or daten.get("title")

        # Eingangs-Wacht (Meldung #559 / Code-Scanning-Alert 60): Webhook-Pfade
        # sind externe Daten. Die Whisper-Engine validiert und kanonisiert sie
        # vor jeder Weitergabe; abgelehnte Aufnahmen fallen auf Text oder den
        # Fallback-Entwurf zurück, statt den Webhook mit einem Fehler zu kippen.
        # Härtung 2026-10 (py/path-injection): der rohe Webhook-Pfad wird hier
        # GAR NICHT mehr angefasst – pruefe_audio_pfad() liefert ausschließlich
        # einen geprüften Kanon innerhalb der erlaubten Wurzeln (oder None).
        transcript = None
        audio_kanon = whisper_engine.pruefe_audio_pfad(audio_file or "")
        if audio_kanon:
            try:
                engine = whisper_engine.WhisperEngine(backend="auto")
                transcript = engine.transcribe(audio_kanon)
            except (ValueError, FileNotFoundError, RuntimeError, OSError) as exc:
                print(f"⚠️  Sprachaufnahme von der Eingangs-Wacht abgelehnt: {exc}")
                transcript = None
        if transcript is None and audio_text:
            transcript = {"text": audio_text, "cleaned_text": whisper_engine.clean_transcript_text(audio_text)}
        elif transcript is None:
            # Fallback Text
            sample = daten.get("inhalt", "Automatisierter Entwurf aus n8n Workflow.")
            transcript = {"text": sample, "cleaned_text": sample}

        article = whisper_engine.transform_voice_to_article(
            transcript=transcript,
            kategorie=kategorie,
            custom_title=titel,
            audio_filename=os.path.basename(audio_kanon) if audio_kanon else "n8n_inbound.mp3",
        )

        # Slug-Wacht (Härtung 2026-10): der Slug wird zu einem Dateisystem-Pfad.
        # Whitelist statt Vertrauen: alles außer Wortzeichen und Bindestrich
        # wird ersetzt – Pfad-Segmente („../“, „/“) sind damit ausgeschlossen.
        slug_sicher = re.sub(r"[^\w-]+", "-", str(article.get("slug") or "entwurf")).strip("-") or "entwurf"
        drafts_dir = os.path.join(BLOG_DIR, "content", "drafts", slug_sicher)
        os.makedirs(drafts_dir, exist_ok=True)
        draft_file = os.path.join(drafts_dir, "index.md")
        with open(draft_file, "w", encoding="utf-8") as fh:
            fh.write(article["markdown"])

        state["empfangene_events"] = state.get("empfangene_events", 0) + 1
        state["letzter_empfang"] = _iso_now()
        save_bridge_state(state)
        log_bridge_event(typ, "inbound", daten, "success", f"Draft erstellt: {draft_file}")

        return {
            "status": "success",
            "action": "draft_created",
            "file": draft_file,
            "slug": article["slug"],
            "title": article["title"],
        }

    elif typ in ("schaltwerk_trigger", "sofortpost", "social_welle"):
        import schaltwerk

        print(f"🔌 Leite Ereignis an Schaltwerk weiter...")
        regeln = schaltwerk.load_regeln()
        schaltwerk_res = schaltwerk.run(regeln, dry_run=False, event_json=json.dumps(payload))
        state["empfangene_events"] = state.get("empfangene_events", 0) + 1
        state["letzter_empfang"] = _iso_now()
        save_bridge_state(state)
        log_bridge_event(typ, "inbound", daten, "success", "Schaltwerk ausgeführt")
        return {"status": "success", "action": "schaltwerk_executed", "result": schaltwerk_res}

    elif typ in ("health_check", "ping"):
        state["empfangene_events"] = state.get("empfangene_events", 0) + 1
        save_bridge_state(state)
        return {"status": "ok", "timestamp": _iso_now(), "message": "n8n_bridge alive"}

    else:
        log_bridge_event(typ, "inbound", daten, "warning", f"Unbehandelter Typ: {typ}")
        return {"status": "ignored", "message": f"Keine Routine für Typ '{typ}' definiert"}


# =====================================================================
#  LOKALER TEST- & MOCK-SERVER
# =====================================================================

class _BridgeHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON"}')
            return

        res = handle_inbound_payload(payload)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(res, ensure_ascii=False).encode("utf-8"))

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/health", "/healthz", "/ping"):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok", "service": "n8n_bridge"}')
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Unterdrückt die Standard-HTTP-Log-Meldungen im Terminal
        pass


def serve_local_bridge(port: int = 5680) -> None:
    """Startet einen lokalen HTTP-Server für Webhook-Empfang."""
    server_address = ("127.0.0.1", port)
    print(f"🚀 Starte lokalen n8n-Bridge-Server auf http://127.0.0.1:{port}...")
    print("   Empfängt Webhooks auf POST / und Health-Checks auf GET /health")
    with socketserver.TCPServer(server_address, _BridgeHTTPRequestHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 n8n-Bridge-Server beendet.")


# =====================================================================
#  HEALTH & SLA PING
# =====================================================================

def ping_n8n(url: str | None = None) -> dict[str, Any]:
    """Prüft Erreichbarkeit und Latenz der n8n-Instanz."""
    target = url or DEFAULT_N8N_URL
    health_url = f"{target.rstrip('/')}/healthz"
    start_time = time.time()
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "n8n_bridge/1.0"})
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            latency_ms = round((time.time() - start_time) * 1000, 1)
            return {
                "status": "online",
                "url": target,
                "latency_ms": latency_ms,
                "http_status": resp.status,
            }
    except Exception as exc:
        latency_ms = round((time.time() - start_time) * 1000, 1)
        return {
            "status": "offline_or_standby",
            "url": target,
            "latency_ms": latency_ms,
            "message": str(exc),
        }


# =====================================================================
#  SELBSTTEST (Offline & hermetisch)
# =====================================================================

@contextlib.contextmanager
def _ablage_im_sandkasten():
    """Lenkt Log und Zustand der Bruecke waehrend des Selbsttests in einen
    Wegwerf-Ordner.

    WARUM (03.10.2026, Gate rot auf main · Schritt "Governance-Selbsttests"):
    `selftest()` schrieb echte Zeilen nach data/n8n_bridge_log.jsonl und
    verbog data/n8n_bridge_state.json. Der Selbsttest-Runner meldet das als
    C15-Bruch – zu Recht: Ein Pruef-Aufruf heilt nicht und hinterlaesst
    nichts. Nebenwirkung in der Praxis: Jeder lokale Testlauf erzeugte
    Diff-Rauschen, das versehentlich mitcommittet werden konnte.

    Die Pfade sind Modul-Globale und werden erst beim Schreiben gelesen –
    Umbiegen auf Zeit genuegt, der Rueckbau steht im finally.

    NACHTRAG (03.10.2026, Lauf 37149404892): Der Entwurfs-Teil des Tests legt
    content/drafts/<slug>/ an und raeumte nur den <slug>-Ordner wieder weg.
    Der LEERE Elternordner content/drafts/ blieb liegen. Git zeigt leere
    Verzeichnisse nicht an, also sah ihn weder `git status` noch die C15-Wache
    – Hugo dagegen schon: Der Build starb danach mit einem Typfehler in der
    Sitemap. Deshalb merkt sich dieser Kontext auch, welche Entwurfs-Ordner es
    VOR dem Test gab, und entfernt nur das, was der Test selbst erzeugt hat.
    """
    global BRIDGE_STATE_PATH, BRIDGE_LOG_PATH
    echt_state, echt_log = BRIDGE_STATE_PATH, BRIDGE_LOG_PATH
    entwuerfe = os.path.join(BLOG_DIR, "content", "drafts")
    entwuerfe_gab_es = os.path.isdir(entwuerfe)
    with tempfile.TemporaryDirectory(prefix="n8n-bridge-selftest-") as sandkasten:
        # Den echten Zustand hineinkopieren, damit der Test denselben
        # Ausgangspunkt sieht wie der Normalbetrieb.
        kopie = os.path.join(sandkasten, "n8n_bridge_state.json")
        if os.path.exists(echt_state):
            with open(echt_state, encoding="utf-8") as quelle:
                with open(kopie, "w", encoding="utf-8") as ziel:
                    ziel.write(quelle.read())
        BRIDGE_STATE_PATH = kopie
        BRIDGE_LOG_PATH = os.path.join(sandkasten, "n8n_bridge_log.jsonl")
        try:
            yield sandkasten
        finally:
            BRIDGE_STATE_PATH, BRIDGE_LOG_PATH = echt_state, echt_log
            # Nur wegraeumen, was der Test angelegt hat – und nur, wenn leer.
            # Ein Ordner mit echten Entwuerfen darf hier NIE verschwinden.
            if not entwuerfe_gab_es and os.path.isdir(entwuerfe):
                try:
                    os.rmdir(entwuerfe)
                except OSError:
                    pass  # nicht leer: fremder Inhalt, bleibt unangetastet


def selftest() -> bool:
    """Selbsttest, der den Arbeitsbaum nicht anfasst (C15)."""
    with _ablage_im_sandkasten():
        return _selftest_kern()


def _selftest_kern() -> bool:
    """Führt Offline-Prüfungen der n8n-Bridge-Logik durch."""
    print("🔬 Starte n8n-Bridge Selbsttest...")

    # 1. State-Verwaltung
    st = load_bridge_state()
    assert isinstance(st, dict), "State ist kein Dictionary"
    assert "version" in st, "State hat keine Versionsangabe"
    print("  ✅ State-Verwaltung funktionsfähig.")

    # 2. Outbound Dispatch im Dry-Run
    dry_res = dispatch_event_to_n8n(
        event_type="test_event",
        payload={"msg": "Hallo n8n"},
        dry_run=True,
    )
    assert dry_res["status"] == "dry_run", "Dry-Run Dispatch fehlerhaft"
    print("  ✅ Outbound Webhook Dispatcher (Dry-Run) verifiziert.")

    # 3. Inbound Payload Handling (Voice-Memo Simulation)
    sample_payload = {
        "typ": "voice_memo",
        "data": {
            "titel": "Stromkosten im Herbst senken",
            "inhalt": "Hier ist eine Aufnahme über Stromspartipps für den Herbst 2026.",
            "kategorie": "strom-gas",
        },
    }
    inbound_res = handle_inbound_payload(sample_payload)
    assert inbound_res["status"] == "success", "Inbound Handling fehlgeschlagen"
    assert inbound_res["action"] == "draft_created", "Kein Entwurf erstellt"
    assert os.path.exists(inbound_res["file"]), f"Entwurfsdatei nicht gefunden: {inbound_res['file']}"
    
    # Temporären Entwurf nach Test aufräumen
    if os.path.exists(os.path.dirname(inbound_res["file"])):
        import shutil
        shutil.rmtree(os.path.dirname(inbound_res["file"]))
    print("  ✅ Inbound Payload Handler (Voice-to-Draft) erfolgreich verifiziert.")

    # 4. Lokaler Server Kurz-Probe über dynamischen Port
    class _ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = _ReusableTCPServer(("127.0.0.1", 0), _BridgeHTTPRequestHandler)
    test_port = httpd.server_address[1]
    srv_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    srv_thread.start()

    try:
        # GET /health testen
        req = urllib.request.Request(f"http://127.0.0.1:{test_port}/health")
        with urllib.request.urlopen(req, timeout=2.0) as resp:
            assert resp.status == 200, "Health Check antwortet nicht mit 200"

        # POST Webhook testen
        post_data = json.dumps({"typ": "ping"}).encode("utf-8")
        req_post = urllib.request.Request(
            f"http://127.0.0.1:{test_port}/",
            data=post_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req_post, timeout=2.0) as resp:
            assert resp.status == 200, "POST Webhook antwortet nicht mit 200"
            body = json.loads(resp.read().decode("utf-8"))
            assert body["status"] == "ok", "Inbound ping fehlerhaft"
        print("  ✅ Lokaler HTTP Bridge Server & Webhook Handler erfolgreich getestet.")
    finally:
        httpd.shutdown()
        httpd.server_close()

    print("🎉 Alle n8n-Bridge Selbsttests BESTANDEN (0 € laufende Kosten gesichert)!")
    return True


# =====================================================================
#  HAUPTPROGRAMM (CLI)
# =====================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="n8n-Bridge — 0 € Workflow-Verdrahtung zwischen Blog & n8n."
    )
    parser.add_argument("--dispatch", help="Ereignistyp zum Senden an n8n (z.B. neuer_artikel)")
    parser.add_argument("--payload", help="JSON-Payload als String")
    parser.add_argument("--payload-file", help="Pfad zu einer JSON-Datei mit Payload")
    parser.add_argument("--webhook-url", help="Ziel-Webhook-URL von n8n")
    parser.add_argument("--receive-payload", help="Verarbeitet einen eingehenden n8n-JSON-Payload direkt")
    parser.add_argument("--ping", action="store_true", help="Prüft Erreichbarkeit und Latenz der n8n-Instanz")
    parser.add_argument("--serve", action="store_true", help="Startet den lokalen Webhook-Empfänger-Server")
    parser.add_argument("--port", type=int, default=5680, help="Port für den lokalen Bridge-Server")
    parser.add_argument("--dry-run", action="store_true", help="Simuliert Aktionen ohne Netzaufrufe")
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    parser.add_argument("--selftest", action="store_true", help="Führt den Offline-Selbsttest aus")

    args = parser.parse_args()

    if args.selftest:
        success = selftest()
        return 0 if success else 1

    if args.ping:
        res = ping_n8n(args.webhook_url)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            status_symbol = "✅" if res["status"] == "online" else "⏸"
            print(f"{status_symbol} n8n Instanz ({res['url']}): {res['status'].upper()} ({res.get('latency_ms', 0)}ms)")
        return 0 if res["status"] == "online" else 0

    if args.serve:
        serve_local_bridge(port=args.port)
        return 0

    if args.receive_payload:
        try:
            p = json.loads(args.receive_payload)
        except json.JSONDecodeError as exc:
            print(f"❌ Ungültiges JSON im Payload: {exc}")
            return 1
        res = handle_inbound_payload(p)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"📥 Verarbeitet: {res}")
        return 0

    if args.dispatch:
        payload_data = {}
        if args.payload:
            try:
                payload_data = json.loads(args.payload)
            except json.JSONDecodeError as exc:
                print(f"❌ Ungültiges JSON in --payload: {exc}")
                return 1
        elif args.payload_file:
            with open(args.payload_file, encoding="utf-8") as fh:
                payload_data = json.load(fh)

        res = dispatch_event_to_n8n(
            event_type=args.dispatch,
            payload=payload_data,
            webhook_url=args.webhook_url,
            dry_run=args.dry_run,
        )
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"📤 Dispatch '{args.dispatch}': {res.get('status')}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
