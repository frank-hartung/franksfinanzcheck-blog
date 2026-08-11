#!/usr/bin/env python3
# ============================================================
#  AFFILIATE-HEALTH (Wochenwache) – E2E-Gesundheit der Ziele
#  Profi-Level (haerteste Fassung, 11.08.2026)
#
#  Lektion aus dem Grossausfall 11.08. („Links funktionieren nicht,
#  falsch verlinkt"): Der alte H1 pruefte nur Hop 1 (Tracker 301 =
#  „gesund") und sah nie, dass die ENDSEITE 404 war. Deshalb:
#
#    H1  E2E-ERREICHBARKEIT: Redirect-Kette wird KOMPLETT verfolgt;
#        die finale Landeseite muss < 400 sein, im richtigen Netz
#        liegen und die richtige KATEGORIE zeigen (Keyword-Vertrag).
#    H2  PID-INTEGRITAET: exakt gepinnte Partner-Strings (s.u.).
#    H3  GATEWAY-DRIFT: static/go/<key>/ == Register-URL.
#    H4  CTA-ABDECKUNG: jeder Post hat einen Affiliate-Pfad.
#
#  SELBSTHEILUNG: „tot"/„falsche Kategorie"/„falsches Netz" ->
#  Route wird im Register auf den sicheren Homepage-Fallback
#  (PID bleibt!) umgebaut + Gateways neu generiert + Issue.
#  Nutzer klicken NIE wieder in einen 404. Transiente Netz-Fehler
#  heilen NICHT (nur Alarm) – kein Aktionismus bei Timeout.
#
#  SABOTAGE-SCHUTZ: SELFTEST (offline, laeuft IMMER zuerst):
#  15 eingefrorene Urteils-Faelle pruefen die verdict()-Logik
#  selbst. Wer an Kontrakt/Logging „herumverbessert", bricht jeden
#  Lauf mit Exit 2 ab, BEVOR etwas geschrieben wird.
#
#  Aufruf:
#    python3 scripts/affiliate_health.py            # E2E-Report (Netz)
#    python3 scripts/affiliate_health.py --no-net   # nur Offline-Checks
#    python3 scripts/affiliate_health.py --issue    # + Issue bei Fund
#
#  Workflow: .github/workflows/affiliate-health.yml (Mo 07:45 MESZ)
# ============================================================

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "scripts" / "check24_links.yaml"
GO_DIR = ROOT / "static" / "go"
REPORT = ROOT / "AFFILIATE-HEALTH-REPORT.md"
HISTORY = ROOT / "data" / "affiliate_health_history.jsonl"

NO_NET = "--no-net" in sys.argv
MAKE_ISSUE = "--issue" in sys.argv

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 FranksFinanzcheck-Health/2.0",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "de-DE,de;q=0.9"}

# ------------------------------------------------------------
# ROUTE_CONTRACT – eingefrorene Erwartung pro Route:
#   key: (netz, pid_mark, finale_keywords, allow_bot403, homepage_ok)
#   finale_keywords : EINES davon muss in der END-URL stecken
#                     (Beweis: richtige Kategorie, nicht nur „200 irgendwo")
#   allow_bot403    : tarifcheck.de sperrt Datacenter-Bots per WAF mit 403;
#                     fuer echte Nutzer ok (manuell verifiziert 11.08.).
#   homepage_ok     : Route darf bewusst auf der Portal-Startseite landen
#                     (z.B. fluege: kein funktionierender Flug-Deep am
#                     Tracker – dokumentierter Fallback, siehe YAML).
# ------------------------------------------------------------
CONTRACT = {
    "strom":       ("check24", "pid=80968&aid=18", ["strom"], False, False),
    "gas":         ("check24", "pid=80968&aid=18", ["gas"], False, False),
    "dsl":         ("check24", "pid=80968&aid=18", ["dsl"], False, False),
    "mietwagen":   ("check24", "pid=80968&aid=18", ["mietwagen"], False, False),
    "reisen":      ("check24", "pid=80968&aid=18", ["pauschalreisen"], False, False),
    "girokonto":   ("check24", "pid=80968&aid=18", ["c24bank"], False, False),
    "allgemein":   ("check24", "pid=80968&aid=18", [], False, True),
    "kredit":      ("check24", "pid=80968&aid=18", ["kredit"], False, False),
    "kfz-versicherung": ("check24", "pid=80968&aid=18", ["kfz"], False, False),
    "handytarife": ("check24", "pid=80968&aid=18", ["handy"], False, False),
    "kreditkarte": ("check24", "pid=80968&aid=18", ["kreditkarte"], False, False),
    "tagesgeld":   ("check24", "pid=80968&aid=18", ["c24bank"], False, False),
    # fluege: offizieller Flug-Deep IM PROGRAMM = pauschalreisen-vergleich&cat=9
    # (Frank, 11.08.). Homepage-Landung gilt hier als SABOTAGE/Fehlroute!
    "fluege":      ("check24", "pid=80968&aid=18&deep=pauschalreisen-vergleich&cat=9",
                    ["pauschalreisen"], False, False),
    "unfallversicherung": ("tarifcheck", "partner_id=47086&ad_id=15", ["unfall"], True, False),
    "haftpflicht": ("tarifcheck", "partner_id=47086&ad_id=15", ["haftpflicht"], True, False),
    "hausrat":     ("tarifcheck", "partner_id=47086&ad_id=15", ["hausrat"], True, False),
    "zahnzusatzversicherung": ("tarifcheck", "partner_id=47086&ad_id=15", ["zahnzusatz"], True, False),
    "reisekrankenversicherung": ("tarifcheck", "partner_id=47086&ad_id=15", ["reisekranken"], True, False),
}

# Sicherer Hafen pro Netz (PID bleibt vollstaendig erhalten):
SAFE_FALLBACK = {
    "check24": "https://a.check24.net/misc/click.php?pid=80968&aid=18",
    "tarifcheck": "https://a.partner-versicherung.de/click.php?partner_id=47086&ad_id=15",
}

# ------------------------------------------------------------
# SABOTAGE-SCHUTZ: eingefrorene Urteils-Faelle fuer verdict().
# (Basieren auf den REAL vermessenen Ketten vom 11.08.2026.)
# ------------------------------------------------------------
SELFTEST = [
    # (key, finale_url, code, erwartete_klasse)
    ("dsl", "https://www.check24.net/dsl-anbieterwechsel/", 200, "ok"),
    ("dsl", "https://www.check24.net/kreditvergleich/", 404, "tot"),
    ("dsl", "https://www.check24.net/kredit-vergleich/", 200, "kategorie"),
    ("strom", "https://www.check24.net/stromanbieter-wechseln/", 200, "ok"),
    ("kredit", "https://www.check24.net/kredit-vergleich/", 200, "ok"),
    ("tagesgeld", "https://www.check24.net/c24bank/?partner_id=80968&tracking_id=", 200, "ok"),
    ("girokonto", "https://www.check24.net/c24bank/?partner_id=80968&tracking_id=", 200, "ok"),
    ("allgemein", "https://www.check24.net/", 200, "ok"),
    ("fluege", "https://www.check24.net/pauschalreisen-vergleich/?pid=80968&ad_id=18&tid=&ref=&mode=", 200, "ok"),
    ("fluege", "https://www.check24.net/", 200, "kategorie"),  # Homepage = Sabotage-Falle!
    ("haftpflicht", "https://www.tarifcheck.de/haftpflichtversicherung/?partner_id=47086&ad_id=15&model=1", 403, "waf"),
    ("haftpflicht", "https://www.tarifcheck.de/hausratversicherung/?partner_id=47086", 200, "kategorie"),
    ("hausrat", "https://www.tarifcheck.de/hausratversicherung/", 200, "ok"),
    ("reisekrankenversicherung", "https://www.tarifcheck.de/reisekrankenversicherung.html?partner_id=47086&ad_id=15&model=1", 403, "waf"),
    ("unfallversicherung", "https://www.tarifcheck.de/unfallversicherung/?partner_id=47086&ad_id=15&model=1", 403, "waf"),
]


def verdict(key: str, final_url: str, code: int) -> dict:
    """Kernlogik – beurteilt eine E2E-Kette. Klassen:
    ok | waf | tot | kategorie | netzwerk | fehler"""
    netz, _pid, kws, allow403, home_ok = CONTRACT[key]
    url_l = final_url.lower()
    net_ok = netz in url_l
    if code == 0:
        return {"klasse": "fehler", "ok": False, "detail": "Netz-Fehler/Timeout"}
    if not net_ok:
        return {"klasse": "netzwerk", "ok": False,
                "detail": f"Kette landet ausserhalb {netz}: {final_url[:80]}"}
    if code >= 400:
        if code == 403 and allow403:
            return {"klasse": "waf", "ok": True,
                    "detail": "WAF-Bot-403 (Datacenter) – Nutzer ok, Kette sauber"}
        return {"klasse": "tot", "ok": False, "detail": f"Endseite HTTP {code}: {final_url[:80]}"}
    if kws and not any(k in url_l for k in kws):
        return {"klasse": "kategorie", "ok": False,
                "detail": f"falsche Kategorie: {final_url[:80]} (erwartet: {'/'.join(kws)})"}
    if not kws and home_ok:
        if not re.match(rf"^https://www\.{netz}\.(net|de)/?(\?.*)?$", url_l):
            return {"klasse": "kategorie", "ok": False,
                    "detail": f"kein sauberer Homepage-Fallback: {final_url[:80]}"}
    return {"klasse": "ok", "ok": True, "detail": final_url[:80]}


def run_selftest() -> list[str]:
    fehler = []
    for i, (key, url, code, want) in enumerate(SELFTEST, 1):
        got = verdict(key, url, code)["klasse"]
        if got != want:
            fehler.append(f"  Fall {i} ({key}): erwartet „{want}“, bekam „{got}“  ← {url[:60]} [{code}]")
    return fehler


def load_registry() -> dict:
    reg = {}
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        ls = line.strip()
        if ls and not ls.startswith("#") and ": " in ls and '"' in ls:
            key = ls.split(":")[0].strip()
            url = ls.split('"')[1]
            if url.startswith("http"):
                reg[key] = url
    return reg


# ------------------------------------------------------- H1: E2E mit Kette

def follow_chain(url: str, versuch: int = 1) -> tuple[str, int]:
    """Verfolgt die KOMPLETTE Redirect-Kette. Liefert (final_url, code)."""
    try:
        req = urllib.request.Request(url, headers=UA, method="GET")
        resp = urllib.request.urlopen(req, timeout=25)
        code = resp.status
        final = resp.geturl()
        try:
            resp.close()
        except Exception:
            pass
        return final, code
    except urllib.error.HTTPError as e:
        return e.geturl() or url, e.code
    except Exception as e:
        if versuch < 2:  # genau ein Retry – Rest bleibt ehrlich „fehler"
            return follow_chain(url, versuch + 1)
        print(f"    ⚠ {type(e).__name__}: {str(e)[:60]}")
        return url, 0


# ------------------------------------------------------------ H2/H3/H4

def check_pids(reg: dict) -> list[str]:
    wrong = []
    for key, url in reg.items():
        want = CONTRACT.get(key, (None, "", None, None, None))[1]
        if want and want not in url:
            wrong.append(f"{key}: PID-Markierung „{want}“ fehlt/fremd! ({url[:70]})")
    return wrong


def check_gateway(reg: dict) -> list[str]:
    problems = []
    for key, url in reg.items():
        f = GO_DIR / key / "index.html"
        if not f.exists():
            problems.append(f"/go/{key}/: Weiterleitungsseite fehlt (shield ausfuehren)")
            continue
        if url not in f.read_text(encoding="utf-8"):
            problems.append(f"/go/{key}/: zeigt von Register abweichend")
    return problems


def check_coverage() -> list[str]:
    gaps = []
    for p in sorted((ROOT / "content" / "posts").glob("*/index.md")):
        t = p.read_text(encoding="utf-8")
        if re.search(r"^draft:\s*true", t[:2500], re.M):
            continue
        if re.search(r"/go/[\w-]+/", t) is None and not re.search(r"a\.(check24\.net|partner-versicherung\.de)", t):
            gaps.append(p.parent.name)
    return gaps


# ------------------------------------------------------------ SELBSTHEILUNG

def heal_route(key: str, grund: str) -> bool:
    """Baut die Register-Zeile auf den sicheren Homepage-Fallback um
    (PID bleibt!). Nutzer landen nie wieder im 404; Frank liefert den
    echten Deep-Link spaeter nach – Issue sagt es ihm."""
    netz = CONTRACT[key][0]
    fallback = SAFE_FALLBACK[netz]
    src = REGISTRY.read_text(encoding="utf-8")
    pat = re.compile(rf'(?m)^(\s+{re.escape(key)}:\s*)"[^"]+"')
    m = pat.search(src)
    if not m:
        return False
    if m.group(0).endswith(f'"{fallback}"'):
        return False  # schon auf Fallback (z.B. fluege) – nichts zu heilen
    alt = m.group(0).split('"')[1]
    neu = (f'{m.group(1)}"{fallback}"  # ↩ auto-geheilt {date.today().isoformat()}: '
           f'{grund} (war: {alt[:60]}…). TODO Frank: echten Deep-Link aus dem Dashboard!')
    REGISTRY.write_text(pat.sub(neu, src, count=1), encoding="utf-8")
    return True


def regenerate_gateways() -> int:
    """Baut static/go/* aus dem (ggf. geheilten) Register neu."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import affiliate_shield  # noqa: WPS433 – bewusster lokaler Import
    return affiliate_shield.generate_go_pages(load_registry())


# ------------------------------------------------------------ Issue (Dedupe)

def create_issue(title: str, body: str) -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("ℹ Kein GITHUB_TOKEN – Issue wird uebersprungen:", title); return
    api = f"https://api.github.com/repos/{repo}/issues"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    req = urllib.request.Request(f"{api}?state=open&labels=affiliate-health&per_page=10", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            for i in json.loads(r.read().decode()):
                if i["title"] == title:
                    print(f"ℹ Dedupe: Issue existiert: #{i['number']}"); return
        data = json.dumps({"title": title, "body": body, "labels": ["affiliate-health"]}).encode()
        urllib.request.urlopen(urllib.request.Request(api, data=data, headers=headers, method="POST"), timeout=20)
        print("✔ Issue erstellt:", title)
    except Exception as e:
        print(f"⚠ Issue-Fehler: {e}")


# ------------------------------------------------------------ main

def main() -> None:
    # SABOTAGE-SCHUTZ zuerst: Urteils-Logik testet sich selbst (offline),
    # BEVOR irgendetwas geschrieben oder geheilt wird.
    fehler = run_selftest()
    if fehler:
        print("🛑 SELBSTTEST FEHLGESCHLAGEN – Health-Waechter blockiert Sabotage.")
        print("   Kein Lauf, keine Heilung, kein Report geschrieben:")
        print("\n".join(fehler))
        sys.exit(2)
    print(f"✅ Selbsttest: {len(SELFTEST)} Urteils-Faelle stimmen.")

    reg = load_registry()
    h1 = []          # (key, url, final, code, verdict-dict)
    healed, unhealed = [], []
    if not NO_NET:
        for key, url in sorted(reg.items()):
            final, code = follow_chain(url)
            v = verdict(key, final, code)
            h1.append((key, url, final, code, v))
            ikon = {"ok": "🟢", "waf": "🟡"}.get(v["klasse"], "🔴")
            print(f"  {ikon} {key}: [{v['klasse']}] {v['detail'][:70]}")
        # SELBSTHEILUNG bei echten Schaeden (nicht bei transienten Fehlern)
        for key, _url, _final, _code, v in h1:
            if v["klasse"] in ("tot", "kategorie", "netzwerk"):
                if heal_route(key, f"{v['klasse']}: {v['detail'][:60]}"):
                    healed.append(f"{key} ({v['klasse']}) → Homepage-Fallback")
                else:
                    unhealed.append(f"{key}: {v['detail']}")
        if healed:
            n = regenerate_gateways()
            print(f"🛠️ Geheilt: {len(healed)} Route(n), {n} Gateways neu generiert.")
            reg = load_registry()  # geheiltes Register nachladen

    h2 = check_pids(reg)
    h3 = check_gateway(reg)
    h4 = check_coverage()

    kritisch = ([f"{k}: {v['detail']}" for k, _u, _f, _c, v in h1 if not v["ok"]]
                + h2 + h3 + unhealed)
    waf = [k for k, _u, _f, _c, v in h1 if v["klasse"] == "waf"]
    today = date.today().isoformat()

    L = ["# 🩺 AFFILIATE-HEALTH-REPORT (E2E)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC",
         f"**Routen:** {len(reg)} · **E2E geprüft:** {len(h1) if h1 else 'offline-Modus'} "
         f"**· WAF-Hinweise:** {len(waf)}",
         f"**Status:** {'🟢 Alles gesund' if not kritisch and not h4 else '🔴 ' + str(len(kritisch)) + ' kritisch, ' + str(len(h4)) + ' Lücken'}",
         ""]
    if h1:
        ok_keys = [k for k, _u, _f, _c, v in h1 if v["ok"]]
        L += [f"**E2E ok:** {len(ok_keys)}/{len(h1)} "
              f"(Redirect-Kette bis zur Endseite, Kategorie per Keyword bewiesen)", ""]
    if healed:
        L += ["## 🛠️ Automatisch geheilt (Homepage-Fallback, PID erhalten)", ""]
        L += [f"- ✅ {h}" for h in healed]
        L += ["", "> ⚠️ Frank: Bitte echte Deep-Links aus dem Partner-Dashboard nachtragen –",
              "> die Routen funktionieren sofort wieder, konvertieren mit Deep-Link aber besser.", ""]
    if kritisch:
        L += ["## 🔴 Kritische Funde", ""]
        L += [f"- **{k}**" for k in kritisch]
    if waf:
        L += ["", "## 🟡 WAF-Bot-403 (beobachtet, fuer Nutzer ok)", ""]
        L += [f"- `{k}`" for k in waf]
    if h4:
        L += ["", f"## ⚠️ CTA-Lücken ({len(h4)} Artikel ohne Affiliate-Link)", ""]
        L += [f"- `{g}`" for g in h4[:20]]
    if not kritisch and not healed and not h4:
        L += ["🎉 Alle Routen end-to-end gesund – Kette, Kategorie, PID, Gateways."]
    L += ["", "---",
          "_Wochenwache E2E: komplette Redirect-Kette, Kategorien-Vertrag (Keyword), "
          "PID-Pins, Gateway-Drift, CTA-Luecken. Tote/falsche Ziele -> Auto-Heilung "
          "auf Homepage-Fallback + Issue. Selbsttest laeuft vor jedem Einsatz._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:30]))

    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": today, "kritisch": len(kritisch),
                             "geheilt": len(healed), "luecken": len(h4)}) + "\n")

    if (kritisch or healed) and MAKE_ISSUE:
        zeilen = ([f"GEHEILT: {h}" for h in healed] + kritisch)
        body = ("```\n" + "\n".join(zeilen) + "\n```\n\n"
                "_Details: AFFILIATE-HEALTH-REPORT.md. Tote/falsch geroutete Ziele wurden "
                "automatisch auf den sicheren Homepage-Fallback umgebaut – bitte im "
                "Partner-Dashboard echte Deep-Links besorgen und in "
                "scripts/check24_links.yaml nachtragen (der Waechter verifiziert sie E2E)._")
        create_issue(f"🚨 Affiliate-Health E2E: {len(kritisch)} kritisch, {len(healed)} geheilt ({today})", body)
    sys.exit(2 if kritisch else 0)


if __name__ == "__main__":
    main()
