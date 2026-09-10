# VORLESEN: Wortuhr-Schalter gesetzt — edge-tts 7.x braucht `boundary="WordBoundary"` (10.09.2026)

**Stand: 10.09.2026 · FranksFinanzcheck Lesehilfen · Nachbefund zur Edge-Reaktivierung (PR #255)**

Bei der Verifikation der Edge-Reaktivierung (PR #255, gemergt + live)
zeigte die installierte Bibliothek (edge-tts 7.2.8):

- `Communicate()` kennt **keinen `style`-Parameter** → der vorhandene
  TypeError-Rückzug auf neutrale Stimme greift (1 zusätzlicher,
  sofortiger Versuch je Segment, kein Hänger).
- Die Bibliothek hat **eigene Timeouts** (`connect_timeout=10`,
  `receive_timeout=60`) — der 120-s-Deckel aus PR #255 liegt als
  zweite Wand darüber.
- **Wortgrenzen gibt es nur mit `boundary="WordBoundary"`** (Standard
  ist Satzebene). Ohne den Schalter bliebe `boundaries` für immer
  leer — die Wortuhr (Gen 4, 07.09.) hätte in Produktion nie Daten
  bekommen. Sie war damit doppelt stillgelegt: toter Edge-Pfad
  (PR #255) UND fehlender Schalter (dieser PR).

## Reparatur

`_make()` in `synth_edge()` setzt `boundary="WordBoundary"`. Alte
Bibliotheken ohne den Schalter fallen weich zurück (TypeError ⇒
Retry ohne Schalter ⇒ Satzebene statt Wortuhr — Ton bleibt, gelogen
wird nie). Das Audio selbst ändert sich durch den Schalter nicht
(nur Telemetrie-Ebene).

## Neue Gates (2) — `ff_voice_backends.py --selftest` (88 → 90)

- Mitschreibende Attrappe: **jeder** Communicate-Aufruf (Stil- +
  Neutral-Versuch) trägt `boundary="WordBoundary"`,
- Uralt-Attrappe (TypeError bei `boundary`): weicher Rückzug ohne
  Schalter findet statt (Tonpfad bleibt begehbar).

## Kanarien: 3 echte Tippfehler als End-to-End-Beweis

Der Sandbox-Ausgang zu `speech.platform.bing.com:443` ist blockiert
(verifiziert: `ClientConnectorError` in 0,0 s — Fail-fast, kein
Hänger). Echte Wortgrenzen entstehen daher erst im CI-Deploy. Damit
der Beweis nicht auf Zufall wartet, fixen 3 Artikel je einen echten,
vom Lektor (L13) gemeldeten Tippfehler — je 1 Wort, sichtbare
Qualitätsverbesserung UND Fingerprint-Wechsel ⇒ Neuvertonung mit
Edge + Wortuhr im nächsten Deploy:

- `2026-09-10-5-einfache-frugalismus-tricks-fuer-den-alltag`
- `2026-09-10-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026`
- `2026-09-10-guenstig-durch-den-winter-heizungs-check-im-spaetsommer`

Verifikation nach dem Deploy: `chunk["w"]` in den frischen
`<slug>.track.json` auf `gh-pages` (API) + Live-Stichprobe.

## Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/ff_voice_backends.py` | `boundary="WordBoundary"` + weicher Rückzug · 2 neue Selftest-Checks |
| `content/posts/2026-09-10-*/index.md` (3×) | „Ddiebesten“ → „Die besten“ (Lektor L13, je 1 Wort) |
| `README.md` | Gate-Zahl 88 → 90 |
| `VORLESEN-WORTUHR-BOUNDARY-REPARATUR-2026-09-10.md` | neu — dieser Report |
