#!/usr/bin/env python3
"""Ticket-Text der Release-Scorecard – die Ursache, nicht das Symptom (#912).

WARUM DIESE DATEI EXISTIERT
---------------------------
Der Ticket-Text entstand bis zum 03.11.2026 als Heredoc mitten im Workflow
`release-scorecard.yml`. Er hatte drei Fehler, die zusammen das Ticket
unschließbar machten:

  1. **Falsche Ursache.** Bei jedem blockierten `faktenalter` stand der
     Satz, es gehe allein um die Faktenfrische – ein Kadenz-Befund, kein
     Inhaltsbefund. Am 02.11.2026 war F1 grün (0 überfällig, 146 %
     Deckung) und F4 (offener Fachbefund) blockierte zehn Artikel. Das
     Ticket behauptete also das Gegenteil der Messung.
  2. **Falscher Schließpfad.** „Danach schließt sich dieses Ticket selbst“
     stimmt nur für einen Rückstand, der per Kadenz abgebaut wird. Für F4
     schließt es sich nie von selbst – dort muss ein Mensch entscheiden.
  3. **Kein Ort zum Arbeiten.** Keine Befund-IDs, keine Frist, keine
     Arbeitsdatei, kein Befehl.

Jetzt gilt: Das Ticket ist eine reine Funktion des Siegels
(`data/release_scorecard_state.json`). Es nennt je Check, wer entscheidet,
wie viele Artikel betroffen sind, wie alt die Befunde sind, wo die
Arbeitsdatei liegt und welcher Befehl schließt. Ein Satz wie „kein
Inhaltsbefund“ wird nur noch geschrieben, wenn er gemessen wahr ist.

NUTZUNG
  python3 scripts/scorecard_ticket.py --state data/release_scorecard_state.json \\
      [--ergebnis success|failure] [--run-url URL]
  python3 scripts/scorecard_ticket.py --selftest
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "data" / "release_scorecard_state.json"

MARKER = "<!-- wache-id: release-scorecard -->"
ENTSCHEIDEN = ("python3 scripts/faktenfrische_befund_ledger.py --entscheiden <ID> "
               "--von \"<Name>\" --begruendung \"<was geprüft/geändert wurde>\"")


def _de_zahl(wert, stellen: int = 2) -> str:
    try:
        return (f"{float(wert):.{stellen}f}").replace(".", ",")
    except (TypeError, ValueError):
        return "–"


def _schlechte_dimensionen(art: dict) -> str:
    schlecht = [d for d, s in sorted((art.get("dimensionen") or {}).items())
                if s in ("blockiert", "nicht beweisbar")]
    return ", ".join(schlecht) or "–"


def _schlechte_checks(art: dict) -> str:
    checks = [c["check"] for c in (art.get("checks") or [])
              if c.get("wirkung") == "blockiert"]
    return ", ".join(f"`{c}`" for c in sorted(set(checks))) or "–"


def ticket_body(state: dict, *, ergebnis: str = "failure", run_url: str = "") -> str:
    """Reine Funktion: Siegel → Ticket-Markdown (deterministisch, testbar)."""
    artikel = state.get("artikel") or {}
    rot = {s: a for s, a in artikel.items()
           if a.get("urteil") in ("blockiert", "nicht beweisbar")}
    warn = sum(1 for a in artikel.values() if a.get("urteil") == "warnung")
    frei = sum(1 for a in artikel.values() if a.get("urteil") == "freigabe-reif")
    modus = "grün" if ergebnis == "success" else "rot"
    zeilen: list[str] = [
        f"## Release-Scorecard: Bestand {modus}",
        "",
        f"**{frei}/{len(artikel)}** Live-Artikel freigabe-reif · "
        f"**{len(rot)}** blockiert/nicht beweisbar · **{warn}** mit Warnungen.",
        "",
    ]
    if not rot:
        zeilen += ["Alle Live-Artikel frei von blockierenden Funden. "
                   "Details: `RELEASE-SCORECARD.md`.", ""]
        return "\n".join(zeilen)

    zeilen += ["| Artikel | Urteil | Risikoklasse | Blockierende Prüfung(en) | Dimension |",
               "|---|---|---|---|---|"]
    for slug, a in sorted(rot.items()):
        zeilen.append(f"| `{slug}` | {a['urteil']} | {a.get('risikoklasse')} | "
                      f"{_schlechte_checks(a)} | {_schlechte_dimensionen(a)} |")
    zeilen.append("")

    ursachen = state.get("ursachen") or []
    befundlage = state.get("befundlage") or {}
    kap = state.get("kapazitaet") or {}
    fakten_checks = {u.get("check") for u in ursachen
                     if u.get("dimension") in ("faktenalter", "revision")}
    f4_rot = "F4-fachbefund" in fakten_checks
    f1_rot = "F1-faktenfrische" in fakten_checks

    if ursachen:
        zeilen += ["### Warum? Die Prüfung, die blockiert", "",
                   "| Prüfung | Dimension | Entscheidet | Artikel |", "|---|---|---|---|"]
        for u in ursachen:
            wer = ("Mensch (Herausgeber/Redaktion)" if u.get("entscheidung") == "human"
                   else "Maschine (deterministisch)")
            zeilen.append(f"| **{u.get('check')}** | {u.get('dimension')} | {wer} | "
                          f"{u.get('anzahl')} |")
        zeilen.append("")

    if f4_rot:
        zeilen += ["### Ursache: offene Fachbefunde (F4)", ""]
        if befundlage.get("nicht_beweisbar"):
            zeilen += [f"❔ **nicht beweisbar:** {befundlage['nicht_beweisbar']}", ""]
        else:
            zeilen += [
                f"- **{befundlage.get('offen')}** offene Fachbefunde auf "
                f"**{befundlage.get('live_seiten')}** Live-Artikeln · ältester "
                f"**{_de_zahl(befundlage.get('aeltester_tage'), 0)} Tage** · "
                f"Frist **{befundlage.get('frist_tage')}** Tage · über der Frist: "
                f"**{befundlage.get('ueber_frist')}**",
                f"- Davon an einem älteren Text erhoben (Text seither geändert): "
                f"**{befundlage.get('ueberholt', 0)}** – entschieden wird der "
                "HEUTIGE Text, fassungsgebunden.",
                "- Arbeitsdatei: `BEFUND-AKTE.md` "
                "(`python3 scripts/faktenfrische_befund_akte.py --schreiben`)",
                "- Schließweg (eine Zeile je Befund):",
                "",
                "```bash",
                ENTSCHEIDEN,
                "```",
                "",
                "**Ein Prüfdatum schließt keinen Fachbefund.** Die Maschine "
                "entscheidet hier nie fachlich; ein neues `faktencheck`-Datum "
                "lässt F4 offen.",
            ]
            if befundlage.get("ueber_frist"):
                zeilen += ["", f"🔴 **Eskalation:** {befundlage['ueber_frist']} "
                               f"Befunde älter als {befundlage.get('frist_tage')} Tage – "
                               "fachliche Entscheidung beim Herausgeber."]
            zeilen.append("")

    if f1_rot:
        zeilen += ["### Ursache: Kadenz der Faktenfrische (F1)", ""]
        if kap.get("nicht_beweisbar"):
            zeilen += [f"❔ **nicht beweisbar:** {kap['nicht_beweisbar']}", ""]
        else:
            zeilen += [
                f"- Bedarf: **{_de_zahl(kap.get('bedarf_je_woche', 0), 1)}** "
                f"Prüfungen/Woche ({_de_zahl(kap.get('bedarf_je_tag', 0))}/Tag) · "
                f"Angebot: **{_de_zahl(kap.get('kapazitaet_je_tag', 0))}**/Tag "
                f"(Budget {kap.get('budget')} × "
                f"{_de_zahl(kap.get('laeufe_je_tag', 0))} Läufe/Tag) · Deckung "
                f"**{_de_zahl(kap.get('deckung_prozent', 0), 0)} %**",
                f"- Fällig heute: **{kap.get('faellig')}** · überfällig: "
                f"**{kap.get('ueberfaellig')}**",
            ]
            if kap.get("abbau_tage") is not None:
                zeilen.append(f"- Rückstand abgebaut in **{kap['abbau_tage']} Tagen** "
                              f"(Frist {kap.get('nachhol_frist_tage')} Tage) – "
                              "danach schließt sich dieser Teil selbst.")
            elif kap.get("faellig"):
                zeilen.append("- ❌ **Rückstand nicht fristgerecht abbaubar** – Kadenz "
                              "oder Intervall in `data/agent_reach/faktenfrische.yaml` "
                              "entscheiden (Herausgeber).")
            if kap.get("empfehlung_erreicht") is False:
                zeilen.append(f"- ❌ Strukturell unterdeckt: selbst das harte Limit "
                              f"({kap.get('hartes_limit')} je Lauf) reicht nicht.")
        zeilen.append("")

    if not f4_rot and not f1_rot:
        zeilen += ["### Ursache: fachliche Einzelfunde (kein Kadenz-Befund)", "",
                   "_Die übrigen blockierenden Prüfungen sind Einzelfunde. "
                   "Besitz und Schließweg stehen je Check in "
                   "`data/release_scorecard.yaml`; Details in "
                   "`RELEASE-SCORECARD.md`._", ""]

    # Der Schließpfad in einem Satz – und nur die Teile, die wirklich gelten.
    schliess: list[str] = []
    if f1_rot:
        schliess.append("F1 schließt sich durch den Kadenz-Abbau (Deckung ≥ 100 % "
                        "und kein überfälliger Artikel).")
    if f4_rot:
        schliess.append("F4 schließt **nur** durch dokumentierte menschliche "
                        "Entscheidungen (`BEFUND-AKTE.md`) – nie durch einen "
                        "weiteren Recherche-Lauf.")
    if not f1_rot and not f4_rot:
        schliess.append("Die Einzelfunde schließen sich durch ihre jeweilige "
                        "Heilung bzw. dokumentierte Ausnahme.")
    zeilen += ["### Was dieses Ticket schließt", ""] + [f"- {s}" for s in schliess]
    zeilen += ["",
               "**Wer entscheidet was:** Besitz je Check steht in "
               "`data/release_scorecard.yaml` (`entscheidung: auto|human`), "
               "Eskalationsmatrix im Runbook. Fachliche Konflikte entscheidet "
               "der Herausgeber – die Maschine nie.",
               "",
               "Details: `RELEASE-SCORECARD.md` im Repo (Schritt-Log und Artefakt)."]
    return "\n".join(zeilen)


def ticket(state_path: Path = STATE, ergebnis: str = "failure",
           run_url: str = "") -> str:
    state = json.loads(Path(state_path).read_text(encoding="utf-8"))
    body = ticket_body(state, ergebnis=ergebnis, run_url=run_url)
    return body + "\n\n" + MARKER


def selftest() -> int:
    def art(urteil="blockiert", risikoklasse="standard", dim=None, checks=()):
        return {"urteil": urteil, "risikoklasse": risikoklasse,
                "dimensionen": dim or {"faktenalter": "blockiert",
                                       "technik": "bestanden"},
                "checks": [{"check": c, "dimension": "faktenalter",
                            "wirkung": "blockiert"} for c in checks]}

    f4_state = {
        "artikel": {"a": art(checks=("F4-fachbefund",)),
                    "b": art(urteil="freigabe-reif")},
        "ursachen": [{"check": "F4-fachbefund", "dimension": "faktenalter",
                      "wirkung": "blockiert", "entscheidung": "human", "anzahl": 1}],
        "befundlage": {"offen": 57, "seiten": 13, "live_befunde": 42,
                       "live_seiten": 10, "aeltester_tage": 4, "frist_tage": 14,
                       "ueber_frist": 0, "ueberholt": 21, "nicht_entscheidbar": 0},
        "kapazitaet": {"faellig": 3, "ueberfaellig": 0, "deckung_prozent": 146,
                       "bedarf_je_tag": 2.73, "bedarf_je_woche": 19.1,
                       "kapazitaet_je_tag": 4.0, "budget": 4,
                       "laeufe_je_tag": 1.0, "abbau_tage": 0},
    }
    body = ticket_body(f4_state)
    # (a) F4 wird als Ursache genannt, mit Zahl, Frist, Akte und Befehl.
    assert "offene Fachbefunde (F4)" in body, body
    assert "57** offene Fachbefunde" in body, body
    assert "BEFUND-AKTE.md" in body and "--entscheiden" in body
    assert "Ein Prüfdatum schließt keinen Fachbefund" in body
    assert "F4 schließt **nur**" in body
    # (b) Kein Kadenz-Befund, wenn F1 nicht blockiert – das war der Fehler.
    assert "Kadenz der Faktenfrische (F1)" not in body, body
    assert "kein Inhaltsbefund" not in body, body
    # Die alte Fehlbehauptung darf nicht zurückkehren (C46 prüft dasselbe).
    assert "allein um die Faktenfrische" not in body, body
    assert "danach schließt sich dieses Ticket selbst" not in body, body
    # (c) Der Schließpfad ist je Check benannt.
    assert "F1 schließt sich" not in body, body

    f1_state = {
        "artikel": {"a": art(checks=("F1-faktenfrische",))},
        "ursachen": [{"check": "F1-faktenfrische", "dimension": "faktenalter",
                      "wirkung": "blockiert", "entscheidung": "auto", "anzahl": 1}],
        "befundlage": {"offen": 0, "seiten": 0, "live_befunde": 0, "live_seiten": 0,
                       "aeltester_tage": None, "frist_tage": 14, "ueber_frist": 0,
                       "ueberholt": 0, "nicht_entscheidbar": 0},
        "kapazitaet": f4_state["kapazitaet"],
    }
    body1 = ticket_body(f1_state)
    assert "Kadenz der Faktenfrische (F1)" in body1, body1
    assert "Deckung **146 %**" in body1, body1
    assert "F1 schließt sich" in body1 and "F4 schließt" not in body1, body1
    assert "offene Fachbefunde (F4)" not in body1, body1

    # (d) Grün: kein Ursachen-Teil, keine Schuldzuweisung.
    gruen = {"artikel": {"a": art(urteil="freigabe-reif")}, "ursachen": [],
             "befundlage": {}, "kapazitaet": {}}
    bodyg = ticket_body(gruen, ergebnis="success")
    assert "Bestand grün" in bodyg and "Blockierende Prüfung" not in bodyg, bodyg

    # (e) Der Marker bleibt im Ticket (C4-Wiedererkennung).
    assert MARKER.startswith("<!-- wache-id:") and "wache-id" in MARKER
    print("✅ Scorecard-Ticket: Ursache je Check, F4 ohne Kadenz-Behauptung, "
          "Frist/Akte/Befehl, ehrlicher Schließpfad, Grün ohne Schuldzuweisung.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", default=str(STATE))
    parser.add_argument("--ergebnis", default="failure",
                        choices=("success", "failure", "cancelled", "skipped"))
    parser.add_argument("--run-url", default="")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    try:
        print(ticket(Path(args.state), args.ergebnis, args.run_url))
    except (OSError, ValueError) as exc:
        print(f"❌ Ticket nicht erzeugbar: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
