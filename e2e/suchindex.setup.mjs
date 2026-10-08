// ============================================================
//  E2E-GLOBAL-SETUP – der Suchindex gehört zum Build
//  ------------------------------------------------------------
//  Die Suchspezifikation (e2e/suche.spec.mjs) braucht public/pagefind/.
//  Der E2E-Job baut die Site mit der Hugo-Action, nicht mit `npm run build`.
//  Ohne diesen Schritt fehlte der Index, und die Suche wäre im Test leer
//  (CI-Lauf 08.10.2026: „public/pagefind/pagefind.js fehlt“).
//  Darum baut die Suite den Index vor dem ersten Test neu – mit demselben
//  Befehl wie der Deploy: `npm run suchindex` (Ordner leeren, Pagefind,
//  Wache). Idempotent, wenige Sekunden. Scheitert er, scheitert der Lauf laut.
//  Mit E2E_ROOT (Design-Varianten) wird nichts gebaut: dieser Index gehört
//  zur Produktions-Site unter public/.
// ============================================================
import { execFileSync } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const WURZEL = resolve(dirname(fileURLToPath(import.meta.url)), '..');

export default async function globalSetup() {
  if (process.env.E2E_ROOT) return;
  execFileSync('npm', ['run', '--silent', 'suchindex'], { cwd: WURZEL, stdio: 'inherit' });
}
