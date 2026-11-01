# Werbe-Offenlegung ist artikelgenau

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Werbe-Offenlegung ist artikelgenau (Wache seit 28.09.2026)

Der ZEIT-Vergleich bewertete „Unabhängigkeit/Kommerz" mit 4 statt 5: Die
Offenlegung stand pauschal („kann Affiliate-Links enthalten") und bei 56 % der
Seiten **hinter** dem ersten Partnerlink. Jetzt gilt: Jede Seite nennt **über**
dem Text die echte Zahl ihrer Partnerlinks samt Partner und Produkt, werbefreie
Artikel sagen das aktiv.

**Eine Quelle:** `data/affiliate_ziele.yaml` → `_funcs/affiliate_offenlegung.html`
→ Kopf-Kennzeichnung (`ff_offenlegung.html`), Abbinder (`trust_box.html`),
Partnerregister (`/transparenz/`). Nie eine zweite Partnerliste anlegen.

**Beim Layout-Arbeiten:** Die Kennzeichnung hängt in **drei** Stellen
(`_partials/artikel_einzeln.html`, `pillar/single.html`,
`pillar/list.html` – letzteres mit `extraKeys`, weil Template-CTAs nicht in
`.Content` stehen). Bis zur Dauerheilung #623 (07.10.2026) hing sie in
*vier* Dateien, weil die Artikel-Ansicht doppelt lag (`single.html` und
`_default/single.html`); seitdem binden beide Templates denselben Baustein
ein – eine Änderung gehört dorthin, nie in eine zweite Kopie. Sie muss im `<header>` bleiben: `python3
scripts/offenlegung_gate.py` (O1–O7, fail-closed) prüft Position **vor** dem
ersten Partnerlink, Zahl/Partner artikelgenau, Pflichtangaben und
Sichtbarkeit (kein `hidden`/`display:none`/`font-size:0`/`aria-hidden`).
Läuft in Publish-Gate (Gate 6), Bestands-Gate, `npm run test:offenlegung` und
E2E. **Ohne `--fix`** – die Kennzeichnung erzeugt das Template, ein Befund ist
ein Layout-/Registerdefekt für einen Menschen (C15). Runbuch:
`docs/ANLEITUNG-OFFENLEGUNG.md`.
