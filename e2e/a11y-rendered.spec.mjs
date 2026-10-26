// Gerenderte WCAG-Stichprobe für die Seitentypen, auf denen Lighthouse
// reale Kontrast-, Label- und Link-Erkennungsfehler gefunden hat.
// Axe misst auch color-mix()/transparente Hintergründe im Browser; die
// statische a11y_audit.py allein kann diese Fälle nicht abdecken.
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { test, expect } from './fixtures.mjs';

const require = createRequire(import.meta.url);
const axeSource = readFileSync(require.resolve('axe-core/axe.min.js'), 'utf8');
const rules = ['color-contrast', 'heading-order', 'label', 'label-content-name-mismatch', 'link-in-text-block'];
const pages = [
  ['Startseite', '/'],
  ['Blogliste', '/posts/'],
  ['Artikel mit Markdown-Checkliste', '/posts/2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks/'],
  ['Themen-Ratgeber', '/pillar/strom-sparen/'],
];

for (const scheme of ['light', 'dark']) {
  for (const [name, path] of pages) {
    test(`${name}: Kontrast, Überschriften, Labels und Link-Erkennbarkeit (${scheme})`, async ({ page }) => {
      await page.setViewportSize({ width: 412, height: 915 });
      await page.emulateMedia({ colorScheme: scheme });
      await page.goto(path);
      await page.addScriptTag({ content: axeSource });
      const violations = await page.evaluate(async (selected) => {
        const result = await window.axe.run(document, { runOnly: { type: 'rule', values: selected } });
        return result.violations.map(({ id, nodes }) => ({
          rule: id,
          targets: nodes.map(({ target, failureSummary }) => ({ target, failureSummary })),
        }));
      }, rules);
      expect(violations, `${name} (${scheme}): Axe-Verstöße`).toEqual([]);
    });
  }
}
