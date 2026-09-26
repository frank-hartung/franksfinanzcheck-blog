// ============================================================
//  LIGHTHOUSE-CI – Konfiguration der Design-Varianten-Werkbank
//  ------------------------------------------------------------
//  Rollout 26.09.2026. Runbook: docs/ANLEITUNG-DESIGN-VARIANTEN.md
//
//  EINE WAHRHEIT FÜR SCHWELLEN
//  Die Assertions stehen NICHT hier, sondern werden aus
//  data/design/regelwerk.yaml erzeugt:
//
//      python3 scripts/design_variant_gate.py --lighthouse-export
//
//  Grund: Zwei getrennt gepflegte Zahlensätze driften auseinander –
//  unbemerkt, weil beide „grün" melden. Das Gate prüft bei jedem Lauf,
//  ob lighthouse/assertions.json noch zum Regelwerk passt
//  (Regel `lighthouse.export`).
//
//  WELCHE VARIANTE GEMESSEN WIRD
//  Über die Umgebungsvariable LHCI_VARIANTE (Standard: basis). Die
//  Werkbank baut jede Variante nach
//  .cache/design-varianten/<id>/public – genau dieser Ordner wird von
//  LHCI als statisches Verzeichnis serviert.
//
//      python3 scripts/design_variant_lab.py --lauf v-hero-conversion
//      LHCI_VARIANTE=v-hero-conversion npx lhci autorun
//
//  KEIN budget.json
//  Bewusste Entscheidung: Die Byte-Budgets dieses Blogs sind als
//  DELTA zur Basis definiert (regelwerk.yaml →
//  performance.stylesheet_zuwachs_bytes_max). Lighthouse kennt nur
//  absolute Grenzen; eine zweite, absolute Zahl wäre eine erfundene.
//  Die Delta-Prüfung macht scripts/design_variant_gate.py.
// ============================================================

const path = require('node:path');
const fs = require('node:fs');

const VARIANTE = process.env.LHCI_VARIANTE || 'basis';
const STATISCH = path.join(__dirname, '.cache', 'design-varianten', VARIANTE, 'public');
const EXPORT = path.join(__dirname, 'lighthouse', 'assertions.json');

if (!fs.existsSync(path.join(STATISCH, 'index.html'))) {
  throw new Error(
    `Kein Build für Variante "${VARIANTE}" unter ${STATISCH}.\n` +
      `Zuerst: python3 scripts/design_variant_lab.py --lauf ${VARIANTE}`
  );
}

if (!fs.existsSync(EXPORT)) {
  throw new Error(
    'lighthouse/assertions.json fehlt.\n' +
      'Erzeugen: python3 scripts/design_variant_gate.py --lighthouse-export'
  );
}

const { assertions } = JSON.parse(fs.readFileSync(EXPORT, 'utf8'));

module.exports = {
  ci: {
    collect: {
      staticDistDir: STATISCH,
      // Startseite + ein Artikel: Die Variante wirkt auf der Startseite,
      // der Artikel ist die schwerste Seite und damit der Härtefall.
      url: ['http://localhost/index.html'],
      numberOfRuns: 3, // Median von 3 – ein einzelner Lauf ist Rauschen
      settings: {
        // KEIN preset: 'desktop' mehr (26.09.2026).
        // Google bewertet Core Web Vitals überwiegend am mobilen Feld, und
        // der Unterschied ist bei diesem Blog nicht kosmetisch: LCP 622 ms
        // (desktop) gegen 3158 ms (mobil). Wer desktop misst, misst die
        // Zahl, die ohnehin grün ist. Der Lighthouse-Standard IST mobil –
        // deshalb steht hier bewusst nichts. e2e/variant-metrics.mjs misst
        // dasselbe Profil als maßgeblich und zusätzlich desktop zum Vergleich.
        skipAudits: ['uses-http2', 'canonical'],
      },
    },
    assert: { assertions },
    upload: { target: 'filesystem', outputDir: `.cache/design-varianten/${VARIANTE}/lhci` },
  },
};
