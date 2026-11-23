# Design-Briefing 2026-11-23

> Erzeugt von `scripts/design_reach_briefing.py` um 2026-11-23 18:44 UTC.  
> Quelle: Agent-Reach-Sammellauf vom 2026-11-23 (5 Quelle(n) ok, 2 Fehler).

> **Status: Vorschlag.** Nichts hier ist eine Entscheidung. Dieses
> Briefing schlägt Varianten-Skizzen vor und nennt die Regeln, an
> denen sie gemessen würden. Ob eine Skizze gebaut wird, entscheidet
> ein Mensch und trägt sie dann von Hand in
> `data/design/varianten.yaml` ein. Die KI schreibt weder CSS noch
> Register noch Freigabe.

**1 von 24 Signalen** ließen sich dem
Hypothesen-Raster zuordnen.

## Barrierefreiheit

* **Oberfläche:** `alle`
* **ID-Vorschlag:** `v-a11y-*`
* **Würde gemessen an:** `barrierefreiheit.kontrast_fliesstext_min`, `barrierefreiheit.fokusring_sichtbar`, `barrierefreiheit.lighthouse_accessibility_min`

**Belege:**

* [AI Sped Up The Build: How Can Accessibility Testing Keep Up?](https://smashingmagazine.com/2026/11/ai-sped-up-build-how-can-accessibility-testing-keep-up/) — Smashing Magazine (UI/UX-Handwerk) · Tue, 17 Nov 2026  
  <sub>Treffer über: accessibility</sub>

**Nächster Schritt, falls angenommen:**

```bash
# 1. Eintrag in data/design/varianten.yaml anlegen (id: v-a11y-*)
# 2. assets/css/varianten/<id>.css schreiben (nur Marken-Tokens!)
python3 scripts/design_variant_gate.py --variante <id>   # Marke prüfen
python3 scripts/design_variant_lab.py --lauf <id>        # Tier A
node e2e/variant-metrics.mjs --variante <id>             # Tier B
```

---

## Bereits im Register

`basis`, `v-hero-conversion`, `v-hero-premium`

## Leitplanken dieses Briefings

* Agent Reach läuft **nur lesend** – keine Posts, keine Logins in CI.
* Kein Signal wird zur Tatsache: Quellen sind verlinkt und vor jeder
  Übernahme zu prüfen.
* Eine Variante entsteht erst durch einen **menschlichen** Eintrag im
  Register und wird erst durch eine **menschliche** Unterschrift live
  (`data/design/regelwerk.yaml` → `freigabe`).

