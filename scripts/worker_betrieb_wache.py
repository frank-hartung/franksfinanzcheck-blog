#!/usr/bin/env python3
"""worker_betrieb_wache.py — Betriebszustand des Newsletter-Workers prüfen (F-02/F-03/F-08).

Warum diese Wache existiert
--------------------------
Mit dem Sicherheitsaudit vom 15.10.2026 hat der Worker drei neue Schutzschichten
bekommen, die **nur im Betrieb** wirken und dort auch still ausfallen können:

1. **Tagesbudget** (F-03) — schützt die 1.000 KV-Schreibzugriffe des Tages.
   Ist es aufgebraucht, nimmt der Worker keine Anmeldungen mehr an. Das fällt
   im Alltag nicht auf, solange sich niemand anmeldet.
2. **Turnstile** (F-02) — wirkt nur, wenn Site-Key (Website) **und** Secret
   (Worker) gesetzt sind. Ein einseitig gesetzter Wert ist der teuerste
   Fehlerzustand: entweder scheitert jede Anmeldung, oder der Schutz ist
   aus und niemand merkt es. Seit dem Paar-Vertrag vom 19.10.2026
   (WF-E813 / #809) kennt der Worker drei Zustände – `aktiv` (beide
   Werte, Prüfung erzwungen), `wartet` (nur Secret: Anmeldung läuft,
   Prüfung steht aus) und `inaktiv` – und diese Wache vergleicht sie mit
   dem **Spiegel** des Site-Keys in `hugo.toml` und
   `newsletter-worker/wrangler.toml`. Der halbgesetzte Zustand „nur
   Secret“ war der Anmelde-Ausfall vom 15.10.2026: jede Anmeldung
   scheiterte an einer Sicherheitsprüfung ohne Widget, fünf Tage lang.
3. **Getrennte Schlüsselrollen** (F-08) — Liest der Versand mit dem
   Schreibschlüssel, ist die Trennung wirkungslos; fehlt der Schreibschlüssel
   ganz, fällt der Worker auf den Standardschlüssel zurück.

Dazu die Exporte selbst: Wer die vollständige Liste gezogen hat, steht im
Protokoll (KV, 30 Tage, mit Schlüsselabdruck). Diese Wache liest beides —
den Zustand und die letzten Exporte — und vergleicht ihn mit dem Repository
(`hugo.toml`, `cloudflare/edge-schutz.md`).

Bauarten
--------
  --selftest   prüft die Prüfung (feste Stände, kein Netz)  → in CI vor dem Lauf
  --offline    prüft nur die Repo-Seite (Konfiguration/Vorlage)
  (Vorgabe)    fragt /healthz des Workers ab (Netz nötig, Schluessel aus Umgebung)

Umgebung: NEWSLETTER_WORKER_BASE, NEWSLETTER_WORKER_EXPORT_KEY
Exit 1 bei Befunden, die Handlung brauchen; Exit 0 mit Warnungen sonst.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]

# Standardwerte des Workers (newsletter-worker/src/index.js) — hier gespiegelt,
# damit die Wache auch ohne Deploy-Quelltext rechnen kann.
DECKEL_STANDARD = 100
FEEDBACK_STANDARD = 200
WARNSCHWELLE = 0.8  # ab 80 % Auslastung wird gemeldet (Handlungsspielraum)


def hole_healthz(base: str, key: str, *, timeout: float = 15.0) -> dict:
    anfrage = urllib.request.Request(f"{base.rstrip('/')}/healthz", headers={
        "accept": "application/json",
        "x-ff-key": key,
        "user-agent": "franksfinanzcheck-betriebswache/1.0",
    })
    try:
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            return json.loads(antwort.read().decode("utf-8"))
    except urllib.error.HTTPError as fehler:
        if fehler.code == 403:
            raise RuntimeError(
                "Der Worker hat den Schluessel abgelehnt (403). In der Regel ist "
                "NEWSLETTER_WORKER_EXPORT_KEY nicht gesetzt oder falsch — der "
                "Betriebsstand ist dann NICHT geprueft, nicht 'in Ordnung'."
            ) from fehler
        raise


def repo_stand() -> dict:
    """Was sagt das Repository: Turnstile-Site-Key, Edge-Vorlage, Worker-Variablen."""
    hugo = (WURZEL / "hugo.toml").read_text(encoding="utf-8")
    site_key = re.search(r'^\s*turnstileSiteKey\s*=\s*"([^"]*)"', hugo, re.M)
    wrangler_pfad = WURZEL / "newsletter-worker" / "wrangler.toml"
    wrangler = wrangler_pfad.read_text(encoding="utf-8") if wrangler_pfad.exists() else ""
    deckel = re.search(r'^ANMELDUNG_MAX_PRO_TAG\s*=\s*"(\d+)"', wrangler, re.M)
    spiegel = re.search(r'^TURNSTILE_SITEKEY\s*=\s*"([^"]*)"', wrangler, re.M)
    vorlage = (WURZEL / "cloudflare" / "edge-schutz.md")
    return {
        "site_key": (site_key.group(1).strip() if site_key else ""),
        "sitekey_spiegel": (spiegel.group(1).strip() if spiegel else None),
        "deckel": int(deckel.group(1)) if deckel else DECKEL_STANDARD,
        "edge_vorlage": vorlage.read_text(encoding="utf-8") if vorlage.exists() else "",
    }


def spiegel_fehler(site_key: str, spiegel: str | None) -> list[str]:
    """Paar-Vertrag (WF-E813 / #809): hugo.toml und wrangler.toml tragen
    denselben Site-Key. Zwei Quellen ohne Spiegelprüfung waren der
    Anmelde-Ausfall vom 15.10.2026 – der Schlüssel lag im Worker, das
    Widget in keiner einzigen ausgelieferten Seite."""
    if spiegel is None:
        return ["`TURNSTILE_SITEKEY` fehlt in newsletter-worker/wrangler.toml – "
                "ohne den Spiegel kann der Paar-Vertrag (Widget + Prüfung "
                "gemeinsam deployt) nicht greifen."]
    if spiegel != site_key:
        return ["Site-Key-Spiegel gebrochen: `hugo.toml` ("
                + (site_key or "leer") + ") ≠ `newsletter-worker/wrangler.toml` ("
                + (spiegel or "leer") + "). Beide tragen denselben Wert – "
                "sonst liefert die Website das Widget, ohne dass der Worker "
                "prüft (Fassade), oder umgekehrt (jede Anmeldung scheitert)."]
    return []


def bewerte(stand: dict, repo: dict) -> tuple[list[str], list[str], list[str]]:
    """Vergleicht Betriebsstand mit Repository. → (fehler, warnungen, ok)"""
    fehler: list[str] = []
    warnungen: list[str] = []
    ok: list[str] = []

    # 1. Erreichbarkeit überhaupt
    if not stand.get("ok"):
        fehler.append("Der Worker meldet **nicht in Ordnung** (`ok: false`) — KV nicht "
                      "erreichbar. Anmeldung, Bestätigung, Abmeldung und Tagespflege "
                      "liegen alle in KV; das ist ein Ausfall, nicht eine Warnung.")
        return fehler, warnungen, ok
    ok.append(f"Worker erreichbar, KV in Ordnung (Stand {stand.get('ts', '?')}).")

    # 2. Turnstile — Paar-Vertrag (F-02, WF-E813 / #809): Widget und Prüfung
    #    gehören zusammen. Zwei halbgesetzte Zustände, zwei verschiedene
    #    Schäden: „Secret ohne Widget“ ließ JEDEN Anmeldeversuch an einer
    #    nicht bestehbaren Prüfung scheitern (Ausfall 15.–19.10.2026);
    #    „Widget ohne Secret“ ist eine Fassade. Beides ist ein Fehler mit
    #    klarem nächsten Schritt, kein Bauchgefühl.
    turnstile = str(stand.get("turnstile", "inaktiv"))
    site_key = repo.get("site_key", "")
    if turnstile == "aktiv" and not site_key:
        fehler.append("**Turnstile-Zustand widersprüchlich:** Der Worker prüft "
                      "(`TURNSTILE_SECRET` und `TURNSTILE_SITEKEY` gesetzt), aber "
                      "`hugo.toml` liefert **kein** Widget (`turnstileSiteKey` "
                      "leer). Folge: Jede Anmeldung scheitert an der "
                      "Sicherheitsprüfung. Site-Key eintragen "
                      "(cloudflare/edge-schutz.md, A3, Schritt 2) oder "
                      "`TURNSTILE_SITEKEY` im Worker leeren, bis das Widget steht.")
    elif turnstile == "wartet" and site_key:
        fehler.append("**Turnstile-Zustand widersprüchlich:** Das Widget wird "
                      "ausgeliefert (Site-Key in `hugo.toml` gesetzt), aber der "
                      "Worker prüft nicht (`TURNSTILE_SITEKEY` dort fehlt, Secret "
                      "liegt bereit). Folge: Der Bot-Schutz ist nur Fassade. "
                      "Spiegel herstellen: `TURNSTILE_SITEKEY` in "
                      "newsletter-worker/wrangler.toml eintragen und deployen "
                      "(A3, Schritt 2).")
    elif turnstile == "wartet":
        warnungen.append("**Turnstile wartet auf seinen Site-Key:** Das Secret "
                         "liegt bereit, aber es gibt noch kein Widget – die "
                         "Anmeldung läuft OHNE Bot-Prüfung weiter (Honeypot, "
                         "Zeitfalle, Mengenklassen und Tagesbudget bleiben "
                         "aktiv). Paar vervollständigen: Widget anlegen, Site-Key "
                         "in `hugo.toml` UND `newsletter-worker/wrangler.toml` "
                         "eintragen, deployen (A3, Schritt 1–2).")
    elif turnstile == "inaktiv" and site_key:
        fehler.append("**Turnstile-Zustand widersprüchlich:** Das Widget wird "
                      "ausgeliefert (Site-Key gesetzt), aber der Worker prüft "
                      "nicht (kein `TURNSTILE_SECRET`). Folge: Der Bot-Schutz "
                      "ist nur Fassade. `npx wrangler secret put TURNSTILE_SECRET` "
                      "(A3, Schritt 3).")
    elif turnstile == "aktiv":
        ok.append("Turnstile aktiv: Widget ausgeliefert UND Prüfung erzwungen.")
    else:
        warnungen.append("**Turnstile inaktiv** — das Anmeldeformular ist nur durch "
                         "Honeypot, Zeitfalle, Mengenlimit und Tagesbudget geschützt. "
                         "Ein Bot mit vielen Adressen kann bis zum Tagesdeckel "
                         "Bestätigungsmails auslösen. Empfehlung: A3 in "
                         "`cloudflare/edge-schutz.md` abarbeiten (kostenlos, kein Cookie).")

    # 3. Tagesbudget (F-03)
    budget = stand.get("budget") or {}
    heute = int(budget.get("anmeldung_heute") or 0)
    # `0` ist ein GÜLTIGER gemeldeter Wert („kein Deckel") und darf nicht als
    # „nicht gemeldet" durchfallen – `or` würde genau das tun.
    roh_max = budget.get("anmeldung_max", None)
    maximum = (int(roh_max) if roh_max not in (None, "")
               else int(repo.get("deckel") or DECKEL_STANDARD))
    if maximum <= 0:
        fehler.append("**Kein Tagesdeckel gesetzt** (`ANMELDUNG_MAX_PRO_TAG` ≤ 0) — damit "
                      "kann jede Anmeldung vier KV-Schreibzugriffe verbrauchen, bis die "
                      "1.000 des Tages weg sind. Danach fallen Abmeldung (Art. 7 Abs. 3 "
                      "DSGVO) und Tagespflege aus.")
    elif heute >= maximum:
        warnungen.append(f"**Tagesbudget bereits ausgeschöpft** ({heute}/{maximum}) — "
                         "Anmeldungen werden bis 00:00 UTC abgelehnt (503). Ist das "
                         "plausibel (Kampagnentag)? Sonst im KV nach "
                         "`warn:anmeldung:*` sehen.")
    elif heute >= maximum * WARNSCHWELLE:
        warnungen.append(f"Tagesbudget zu {heute}/{maximum} verbraucht "
                         f"({heute * 100 // maximum} %) — heute Abend nachsehen.")
    else:
        ok.append(f"Tagesbudget im Rahmen: {heute}/{maximum} Anmeldungen.")

    # 4. Schlüsselrollen (F-08)
    rollen = str(stand.get("schluesselrollen", "gemeinsam"))
    if rollen == "getrennt":
        ok.append("Export-Schlüssel getrennt: Lesen und Schreiben sind verschiedene "
                  "Geheimnisse.")
    else:
        warnungen.append("**Nur EIN Export-Schlüssel** (`EXPORT_KEY_WRITE` nicht gesetzt): "
                         "Wer ihn liest, bekommt auch die Token aller Abonnenten und kann "
                         "sie abmelden. Trennung: "
                         "`npx wrangler secret put EXPORT_KEY_WRITE` + GitHub-Secret "
                         "`NEWSLETTER_WORKER_WRITE_KEY` (cloudflare/edge-schutz.md, A4).")

    # 5. Export-Protokoll (F-08) — wer hat wann die Liste gezogen?
    exporte = stand.get("exporte") or []
    if not isinstance(exporte, list):
        exporte = []
    ok.append(f"Export-Protokoll: {len(exporte)} Einträge im Aufbewahrungsfenster "
              "(30 Tage).")
    if exporte:
        letzte = exporte[0]
        ok.append(f"Letzter Export: {letzte.get('ts', '?')} · {letzte.get('route', '?')} · "
                  f"{letzte.get('umfang', '?')} Zeilen · Schlüssel "
                  f"{letzte.get('key', '?')} (Kurzabdruck) · HTTP {letzte.get('status', '?')}")
        boese = [e for e in exporte if int(e.get("status", 0)) == 403]
        if len(boese) >= 5:
            warnungen.append(f"**{len(boese)} abgewiesene Export-Versuche** im Fenster — "
                             "jemand probiert einen Schlüssel aus. Bei anhaltendem "
                             "Muster: Schlüssel rotieren (A4).")

    # 6. Die Edge-Vorlage muss die drei Regeln nennen (die Wache erdet sie)
    vorlage = repo.get("edge_vorlage", "")
    for stichwort, warum in (
        ("Rate limiting", "Mengenregeln an der Edge (F-03)"),
        ("Turnstile", "Bot-Schutz (F-02)"),
        ("Strict-Transport-Security", "Header-Regel (F-01)"),
        ("Environments", "Freigabe-Environments (F-07)"),
    ):
        if stichwort not in vorlage:
            fehler.append(f"`cloudflare/edge-schutz.md` nennt „{stichwort}“ nicht mehr — "
                          f"dann fehlt die Vorlage für {warum}.")
    return fehler, warnungen, ok


def offline_pruefen() -> tuple[int, str]:
    repo = repo_stand()
    zeilen = ["# Betriebs-Wache — Repo-Seite (offline)", ""]
    fehler: list[str] = []
    if not repo["edge_vorlage"]:
        fehler.append("`cloudflare/edge-schutz.md` fehlt (Vorlage für Header, "
                      "Mengenregeln, Turnstile und Environments).")
    if repo["deckel"] * 4 + FEEDBACK_STANDARD > 1000:
        fehler.append(f"Tagesdeckel {repo['deckel']} × 4 Schreibzugriffe + "
                      f"{FEEDBACK_STANDARD} Feedback sprengt die 1.000/Tag.")
    # Paar-Vertrag Turnstile (WF-E813 / #809): Der Site-Key hat ZUHAUSE zwei
    # Adressen (hugo.toml liefert das Widget, wrangler.toml spiegelt es dem
    # Worker). Ohne Spiegelprüfung rutschten sie auseinander – der halb-
    # gesetzte Zustand war fünf Tage lang ein Anmelde-Ausfall.
    fehler += spiegel_fehler(repo["site_key"], repo["sitekey_spiegel"])
    # Die Wache selbst muss die Standardwerte des Workers kennen.
    index = (WURZEL / "newsletter-worker" / "src" / "index.js").read_text(encoding="utf-8")
    for name in ("ANMELDUNG_MAX_PRO_TAG_DEFAULT", "TAGESBUDGET", "exportlog:",
                 "turnstile_zustand"):
        if name not in index:
            fehler.append(f"`{name}` fehlt im Worker — die Wache prüft Werte, die es "
                          "nicht mehr gibt.")
    if fehler:
        zeilen += ["## Befunde", ""] + [f"- ❌ {f}" for f in fehler]
        return 1, "\n".join(zeilen)
    zeilen.append(f"✅ Repo-Seite in Ordnung: Deckel {repo['deckel']}/Tag, "
                  f"Turnstile-Site-Key {'gesetzt' if repo['site_key'] else 'offen'}, "
                  "Edge-Vorlage vollständig.")
    return 0, "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Betriebszustand des Newsletter-Workers prüfen (F-02/F-03/F-08).")
    parser.add_argument("--selftest", action="store_true", help="prüft die Prüfung (ohne Netz)")
    parser.add_argument("--offline", action="store_true", help="nur Repo-Seite prüfen")
    parser.add_argument("--json", action="store_true", help="Bericht als JSON")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.offline:
        code, bericht = offline_pruefen()
    else:
        base = (os.environ.get("NEWSLETTER_WORKER_BASE") or "").rstrip("/")
        key = os.environ.get("NEWSLETTER_WORKER_EXPORT_KEY") or ""
        if not base or not key:
            print("❌ NEWSLETTER_WORKER_BASE und NEWSLETTER_WORKER_EXPORT_KEY müssen "
                  "gesetzt sein — ohne sie ist der Betriebsstand NICHT geprüft.",
                  file=sys.stderr)
            return 2
        try:
            stand = hole_healthz(base, key)
        except Exception as fehler:  # noqa: BLE001
            print(f"❌ Betriebsstand nicht abrufbar: {fehler}", file=sys.stderr)
            return 2
        fehler_liste, warnungen, ok = bewerte(stand, repo_stand())
        zeilen = ["# Betriebs-Wache — Live-Stand", ""]
        zeilen += [f"- ✅ {z}" for z in ok]
        zeilen += [f"- ⚠️ {z}" for z in warnungen]
        zeilen += [f"- ❌ {z}" for z in fehler_liste]
        bericht = "\n".join(zeilen)
        code = 1 if fehler_liste else 0
    if args.json:
        print(json.dumps({"exit": code, "bericht": bericht}, ensure_ascii=False, indent=2))
    else:
        print(bericht)
    return code


# ------------------------------------------------------------------ Selbsttest
def selftest() -> int:
    repo = {"site_key": "0x4AAA", "deckel": 100, "edge_vorlage":
            "Rate limiting\nTurnstile\nStrict-Transport-Security\nEnvironments\n"}
    faelle = 0

    gut = {"ok": True, "ts": "2026-10-15T04:00:00Z", "turnstile": "aktiv",
           "schluesselrollen": "getrennt", "budget": {"anmeldung_heute": 3, "anmeldung_max": 100},
           "exporte": [{"ts": "2026-10-15T03:00:00Z", "route": "/export/abonnenten",
                        "umfang": 12, "key": "a1b2c3d4", "status": 200}]}
    f, w, o = bewerte(gut, repo)
    assert not f, f"Gesunder Stand beanstandet: {f}"
    faelle += 1

    # Gegenprobe 1: Worker sagt „inaktiv", Website liefert Widget -> Fassade.
    f, _, _ = bewerte({**gut, "turnstile": "inaktiv"}, repo)
    assert any("Fassade" in x for x in f), "Einseitiges Turnstile (nur Site-Key) nicht erkannt"
    faelle += 1

    # Gegenprobe 2: Worker prüft, Website liefert nichts -> jede Anmeldung scheitert.
    f, _, _ = bewerte({**gut}, {**repo, "site_key": ""})
    assert any("scheitert" in x for x in f), "Einseitiges Turnstile (nur Secret) nicht erkannt"
    faelle += 1

    # Gegenprobe 2a (Paar-Vertrag WF-E813 / #809): „wartet“ OHNE Widget ist
    # KEIN Fehler mehr, sondern eine laute Warnung – die Anmeldung läuft.
    f, w, _ = bewerte({**gut, "turnstile": "wartet"}, {**repo, "site_key": ""})
    assert not f and any("wartet" in x.lower() for x in w), \
        "Zustand „wartet“ ohne Widget muss warnen, nicht scheitern"
    faelle += 1

    # Gegenprobe 2b: „wartet“ MIT Widget = Fassade (Spiegel gebrochen).
    f, _, _ = bewerte({**gut, "turnstile": "wartet"}, repo)
    assert any("Fassade" in x for x in f), "Widget ohne Prüfung (wartet) nicht als Fassade erkannt"
    faelle += 1

    # Gegenprobe 2c: Spiegel des Site-Keys (hugo.toml ↔ wrangler.toml).
    assert spiegel_fehler("0x4AAA", "0x4AAA") == []
    assert spiegel_fehler("", "") == []
    f = spiegel_fehler("0x4AAA", "")
    assert f and "Spiegel gebrochen" in f[0], "Abweichender Spiegel nicht erkannt"
    f = spiegel_fehler("", None)
    assert f and "fehlt" in f[0], "Fehlende Spiegel-Variable nicht erkannt"
    faelle += 1

    # Gegenprobe 3: KV tot ist ein Fehler, keine Warnung.
    f, _, _ = bewerte({**gut, "ok": False}, repo)
    assert any("Ausfall" in x for x in f), "KV-Ausfall nicht als Fehler erkannt"
    faelle += 1

    # Gegenprobe 4: Budget ausgeschöpft -> Warnung, kein Fehler.
    f, w, _ = bewerte({**gut, "budget": {"anmeldung_heute": 100, "anmeldung_max": 100}}, repo)
    assert not f and any("ausgeschöpft" in x for x in w), "Budgetdeckel nicht gemeldet"
    faelle += 1

    # Gegenprobe 5: kein Deckel -> Fehler (Rückfall in den Zustand vor dem Audit).
    f, _, _ = bewerte({**gut, "budget": {"anmeldung_heute": 5, "anmeldung_max": 0}}, repo)
    assert any("Tagesdeckel" in x for x in f), "Fehlender Deckel nicht als Fehler erkannt"
    faelle += 1

    # Gegenprobe 6: geteilter Schlüssel -> Warnung.
    f, w, _ = bewerte({**gut, "schluesselrollen": "gemeinsam"}, repo)
    assert not f and any("EXPORT_KEY_WRITE" in x for x in w), "Geteilter Schlüssel nicht gemeldet"
    faelle += 1

    # Gegenprobe 7: Brute-Force auf den Export -> Warnung.
    viele = [{"ts": f"2026-10-15T0{i}:00:00Z", "route": "/export/abonnenten", "umfang": 0,
              "key": "ffffffff", "status": 403} for i in range(9)] + gut["exporte"]
    f, w, _ = bewerte({**gut, "exporte": viele}, repo)
    assert any("abgewiesene Export-Versuche" in x for x in w), "Brute-Force nicht gemeldet"
    faelle += 1

    # Gegenprobe 8: Vorlage verloren -> Fehler.
    f, _, _ = bewerte(gut, {**repo, "edge_vorlage": ""})
    assert len(f) >= 4, "Fehlende Edge-Vorlage nicht erkannt"
    faelle += 1

    code, bericht = offline_pruefen()
    assert code == 0, f"Offline-Prüfung des echten Stands fehlgeschlagen:\n{bericht}"
    faelle += 1

    print(f"✅ SELBSTTEST OK — {faelle} Fälle grün (Budget, Turnstile-Widersprüche, "
          "Schlüsselrollen, Export-Protokoll, Edge-Vorlage).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
