/**
 * ff_heading_glyph_guard_test.mjs — „§“-Wache: Der Abschnitts-Copy-Button
 * darf NIEMALS in Kurzfassung, Klartext-Kopie oder Vorlesen durchrutschen
 * ------------------------------------------------------------
 * Befund 10.09.2026 (Issue #248): Der Abschnitts-Link-Kopierer von
 * ff-premium.js injizierte das Glyph „§“ als rohen Button-TEXT in jede
 * h2/h3. Alle Textextraktoren von ff-voice.js (readableText) lasen es
 * als Artikeltext — im gesamten Blog zeigte die Kurzfassung an jeder
 * Gliederung ein „§“, die Klartext-Kopie ebenso, und das Vorlesen
 * sprach „… Paragraph“ mit.
 *
 * Reparierter Zustand (fünf Wälle, s. ff-premium.js / ff-voice.js /
 * ff-summary-safety.js):
 *   1. Der Knopf trägt ein INLINE-SVG — kein Textknoten, kein „§“ im DOM,
 *   2. `data-ff-skip-read` + `aria-label` (Extraktor-Konvention, zugänglich),
 *   3. `.ff-heading-text` + `aria-labelledby` beschriftet die Überschrift
 *      nur mit dem redaktionellen Text (Screenreader, SEO),
 *   4. ff-voice.js::readableText() entfernt jegliche <button>-Knoten und
 *      Verstecktes vor JEDER Extraktion (Immunität gegen künftige
 *      UI-Injektionen — Gruppe 7 beweist das mit einer Feind-Injektion),
 *   5. ff-summary-safety.js kürzt angehängte Ankerreste im Dialog-Verzeichnis.
 *
 * Diese Wache lädt die ECHTEN Produktions-Dateien (ff-voice.js +
 * ff-premium.js + ff-summary-safety.js) gegen eine ECHTE DOM (jsdom)
 * und pinnt:
 *   · Button-Markup ist extraktionssicher (und die Funktion bleibt),
 *   · Kurzfassung-Dialog + Gliederung + Klartext-Kopie: kein „§“,
 *   · Gliederung ≡ sichtbarem Überschriftentext (Label-Vertrag),
 *   · TTS-Blöcke: kein „§“,
 *   · legitimes „§“ im Artikeltext („§ 8 EinSiG“) bleibt erhalten,
 *   · Mini-TOC (ff-premium.js) bleibt sauber,
 *   · ZUKUNFT: eine feindliche „§“-Injektion in eine Überschrift bleibt
 *     wirkungslos (Wand 4 + 5) — dauerhaft, nicht nur heute,
 *   · IM GESAMTEN BLOG: alle echten Artikel durchlaufen die Prüfung.
 *
 * Aufruf: node scripts/ff_heading_glyph_guard_test.mjs
 *         (jsdom liegt in tools/ff-voice-qa/node_modules)
 */

import { createRunner, loadPage, skeleton, mdToHtml, listArticles, fs, path, ROOT, sleep } from './ff_voice_qa_lib.mjs';

const PREMIUM_PATH = path.join(ROOT, 'static', 'premium', 'ff-premium.js');
const SAFETY_PATH = path.join(ROOT, 'static', 'premium', 'ff-summary-safety.js');

const t = createRunner('„§“-Wache: Kurzfassung, Klartext, Vorlesen bleiben §-frei');

/** Lädt die ECHTE ff-premium.js in eine geladene Seite.
    ff-premium.js initialisiert auf DOMContentLoaded; in jsdom ist das
    Dokument nach dem Aufbau schon „complete“ — dann feuert das Event
    nicht mehr von selbst und wird hier explizit ausgelöst. */
async function loadPremium(win) {
  win.eval(fs.readFileSync(PREMIUM_PATH, 'utf8'));
  if (!win.document.querySelector('.ff-heading-copy')) {
    win.document.dispatchEvent(new win.Event('DOMContentLoaded'));
  }
  await sleep(20); // Task-Flush (Reveal-Fallback & Co.)
}

/** Der sichtbare Überschriftentext (ohne UI-Knoten) — exakt die Semantik
    von ff-voice.js::headingTextOf(): UI weg, Whitespace einebnen, ange-
    hängte Ankerreste rasieren. Ein „§“ MITTEN im Text bleibt (Inhaltsschutz). */
function visibleHeadingLabels(doc) {
  return [...doc.querySelectorAll('.post-content h2, .md-content h2, .post-content h3, .md-content h3')]
    .map((h) => {
      const clone = h.cloneNode(true);
      clone.querySelectorAll('button, .anchor, [data-ff-skip-read], [aria-hidden="true"], [hidden]')
        .forEach((n) => n.remove());
      return String(clone.textContent || '')
        .replace(/[\u00a0]+/g, ' ')
        .replace(/\s+/g, ' ')
        .replace(/[\s#§]+$/g, '')
        .trim();
    })
    .filter((label) => label.length > 2);
}

/** Die Gliederungs-Zeilen aus dem Klartext (nach „In diesem Artikel“). */
function plainTocLines(plain) {
  const lines = String(plain || '').split('\n');
  const idx = lines.findIndex((l) => l.trim() === 'In diesem Artikel');
  if (idx === -1) return [];
  return lines.slice(idx + 1).filter((l) => l.trim());
}

/* ============================================================
   Fixtures: ein typischer Ratgeber mit 4 H2 + 1 H3
   ============================================================ */
const FIXTURE_MD = [
  '## Was ist Tagesgeld',
  '',
  'Ein Tagesgeldkonto ist ein Sparkonto ohne Laufzeit und ohne Kündigungsfrist.',
  '',
  '## Warum 2026 sinnvoll',
  '',
  'Die Zinsen liegen 2026 deutlich über dem Niveau des Girokontos.',
  '',
  '### Auswahlkriterien',
  '',
  '- Zinssatz und Zinsgarantie',
  '- Einlagensicherung',
  '',
  '## Rechenbeispiel',
  '',
  'Auf 10.000 € bringt 2,0 % Zinsen genau 200 € pro Jahr.',
  '',
  '## Fazit',
  '',
  'Tagesgeld ist der unterschätzte Basis-Baustein des Notgroschens.',
].join('\n');

let fixture = null;   // wird in Gruppe 1 geladen, in 2–3 und 5–7 weitergenutzt

/* ============================================================
   1 · Injection: Echte ff-premium.js, extraktionssicheres Markup
   ============================================================ */
t.group('1) ff-premium.js injiziert die Abschnitts-Knöpfe extraktionssicher');
{
  fixture = loadPage(skeleton({
    title: 'Tagesgeld-Zinsen 2026: Die besten Zinssätze im Vergleich',
    kurzantwort: 'Tagesgeld zahlt 2026 zwischen 1,8 und 3,2 Prozent pro Jahr.',
    bodyHtml: mdToHtml(FIXTURE_MD),
  }));
  await loadPremium(fixture.win);
  const doc = fixture.doc;

  const headings = doc.querySelectorAll('.post-content h2[id], .post-content h3[id]');
  const buttons = [...doc.querySelectorAll('.ff-heading-copy')];
  t.eq('Copy-Button an jeder Abschnitts-Überschrift', buttons.length, headings.length,
    `erwartet ${headings.length}, gefunden ${buttons.length}`);

  let markupOk = buttons.length > 0;
  let detail = '';
  buttons.forEach((b, i) => {
    const okSvg = !!b.querySelector('svg');
    const okNoText = (b.textContent || '').trim() === '';
    const okAttrs = b.getAttribute('data-ff-skip-read') !== null
      && b.type === 'button'
      && b.getAttribute('aria-label') === 'Link zu diesem Abschnitt kopieren';
    const okPosition = b === b.parentElement.lastElementChild;
    if (!okSvg || !okNoText || !okAttrs || !okPosition) { markupOk = false; detail = 'Button #' + i; }
  });
  t.ok('Knopf trägt ein Symbol (Inline-SVG)', markupOk, detail);
  t.ok('Knopf trägt KEIN Textzeichen (kein „§“ im DOM)', markupOk, detail);
  t.ok('Knopf trägt data-ff-skip-read (Extraktor-Konvention)', markupOk, detail);
  t.ok('Knopf bleibt zugänglich (type, aria-label)', markupOk, detail);

  // Überschriften-Name: nur der redaktionelle Text beschriftet die Überschrift
  const labelled = [...headings].filter((h) => h.getAttribute('aria-labelledby'));
  t.ok('Jede Überschrift ist sauber beschriftet (aria-labelledby)',
    labelled.length === headings.length, labelled.length + '/' + headings.length);
  let labelOk = labelled.length === headings.length;
  let labelDetail = '';
  [...headings].forEach((h, i) => {
    const label = h.querySelector('.ff-heading-text');
    const ref = label ? doc.getElementById(h.getAttribute('aria-labelledby')) : null;
    if (!label || ref !== label) { labelOk = false; labelDetail = 'Überschrift #' + i; }
  });
  t.ok('aria-labelledby zeigt auf das redaktionelle Etikett (.ff-heading-text)', labelOk, labelDetail);
}

/* ============================================================
   2 · Kurzfassung-Dialog & Klartext: nirgends ein „§“
   ============================================================ */
t.group('2) Kurzfassung-Dialog, Gliederung und Klartext-Kopie sind §-frei');
{
  const { win, doc } = fixture;
  const api = win.__ffVoice;

  const plain = api.summaryPlainText();
  t.ok('Klartext-Kopie enthält kein „§“', !plain.includes('§'),
    'Auszug: ' + plainTocLines(plain).slice(0, 3).join(' | '));
  t.ok('Gliederung-Sektion vorhanden', plainTocLines(plain).length >= 4);

  doc.getElementById('ff-voice-summary').click();
  const dlg = doc.getElementById('ff-voice-dialog');
  t.ok('Dialog erzeugt', !!dlg);
  t.ok('Dialog-Text enthält kein „§“', dlg && !dlg.textContent.includes('§'));

  const tocLinks = [...doc.querySelectorAll('.ff-voice-toc a')];
  const expected = visibleHeadingLabels(doc);
  const actual = tocLinks.map((a) => a.textContent.replace(/\s+/g, ' ').trim());
  t.eq('Gliederung so lang wie sichtbare Überschriften', actual.length, expected.length,
    `erwartet ${expected.length}, gefunden ${actual.length}`);
  t.ok('Gliederung ≡ sichtbarem Überschriftentext (Label-Vertrag)',
    JSON.stringify(actual) === JSON.stringify(expected),
    `erwartet ${JSON.stringify(expected)}, erhalten ${JSON.stringify(actual)}`);
  t.ok('Kein Link in der Gliederung enthält „§“',
    tocLinks.every((a) => !a.textContent.includes('§')));

  let copied = null;
  win.__ff_voice_copied = (text) => { copied = text; };
  doc.getElementById('ff-voice-copy').click();
  t.ok('Kopie erfolgte', typeof copied === 'string' && copied.length > 40);
  t.ok('Kopie enthält kein „§“', typeof copied === 'string' && !copied.includes('§'));

  dlg.querySelector('.ff-voice-dialog__close').click();
  t.ok('Dialog geschlossen', !dlg.open);
}

/* ============================================================
   3 · Vorlesen: TTS-Blöcke und Anmoderation lesen kein „§“
   ============================================================ */
t.group('3) Vorlesen: keine TTS-Blöcke mit „§“');
{
  const { win } = fixture;
  const blocks = win.__ffVoice.collectBlocks();
  const dirty = blocks.filter((b) => (b.text || '').includes('§'));
  t.eq('Kein Sprechblock enthält „§“', dirty.length, 0,
    dirty.slice(0, 2).map((b) => b.type + ': ' + b.text).join(' | '));
  const h2 = blocks.filter((b) => b.type === 'h2');
  t.ok('H2-Blöcke vorhanden', h2.length >= 4, 'H2: ' + h2.length);
  t.ok('Jeder H2-Block endet sauber mit Punkt (kein „§“ am Satzende)',
    h2.every((b) => /[.?]$/.test(b.text)),
    h2.map((b) => '…' + b.text.slice(-12)).join(' | '));
}

/* ============================================================
   4 · Legitimes „§“ im Artikeltext bleibt erhalten
   ============================================================ */
t.group('4) Redaktioneller „§“-Text (Rechtsgrundlage) bleibt im Inhalt');
{
  const { win, doc } = loadPage(skeleton({
    title: 'Einlagensicherung einfach erklärt',
    kurzantwort: '100.000 € sind in der EU gesetzlich abgesichert.',
    bodyHtml: mdToHtml([
      '## Gesetzliche Absicherung',
      '',
      'Bis zu 100.000 € pro Kunde und Bank sind abgesichert (§ 8 EinSiG).',
      '',
      '## Wechseln',
      '',
      'Der Anbieterwechsel ist jederzeit möglich, beachte die Frist laut § 5 der AGB.',
      '',
      '## Fazit',
      '',
      'Die gesetzliche Einlagensicherung ist die Basis jeder Geldanlage.',
    ].join('\n')),
  }));
  await loadPremium(win);
  const api = win.__ffVoice;

  const plain = api.summaryPlainText();
  t.ok('Kernaussagen behalten „§ 8 EinSiG“', /§ 8 EinSiG/.test(plain),
    'Klartext enthält die Rechtsgrundlage nicht mehr');
  t.ok('Gliederung trotz Rechtsgrundlage §-frei',
    plainTocLines(plain).every((l) => !l.includes('§')),
    'Auszug: ' + plainTocLines(plain).join(' | '));

  const blocks = api.collectBlocks();
  const headings = blocks.filter((b) => /^H[23]$/.test(b.type));
  const paragraphs = blocks.filter((b) => b.type === 'p');
  t.ok('Kein Überschriften-Block enthält „§“',
    headings.every((b) => !b.text.includes('§')));
  t.ok('Absatz-Block behält „§ 8 EinSiG“',
    paragraphs.some((b) => b.text.includes('§ 8 EinSiG')));

  doc.getElementById('ff-voice-summary').click();
  const tocLinks = [...doc.querySelectorAll('.ff-voice-toc a')];
  t.ok('Dialog-Gliederung §-frei', tocLinks.every((a) => !a.textContent.includes('§')));
  t.eq('Dialog-Gliederung ≡ sichtbarem Überschriftentext',
    tocLinks.map((a) => a.textContent.replace(/\s+/g, ' ').trim()).join('␟'),
    visibleHeadingLabels(doc).join('␟'));
}

/* ============================================================
   5 · Mini-TOC (ff-premium.js) bleibt sauber
   ============================================================ */
t.group('5) ff-premium.js Mini-TOC zeigt keine „§“-Labels');
{
  const { doc } = fixture;
  const miniToc = doc.querySelector('.ff-mini-toc');
  t.ok('Mini-TOC erzeugt (≥ 3 H2)', !!miniToc);
  if (miniToc) {
    const links = [...miniToc.querySelectorAll('a')];
    t.ok('Mini-TOC-Links vorhanden', links.length >= 3, 'Links: ' + links.length);
    t.ok('Kein Mini-TOC-Label enthält „§“ oder „#“',
      links.every((a) => !/[§#]/.test(a.getAttribute('aria-label') || a.textContent)));
    // Mini-TOC listet bewusst nur H2-Abschnitte (Design-Vertrag)
    const expected = [...doc.querySelectorAll('.post-content h2[id]')]
      .map((h) => {
        const clone = h.cloneNode(true);
        clone.querySelectorAll('button, .anchor, [data-ff-skip-read], [aria-hidden="true"], [hidden]')
          .forEach((n) => n.remove());
        return String(clone.textContent || '')
          .replace(/[\u00a0]+/g, ' ')
          .replace(/\s+/g, ' ')
          .replace(/[\s#§]+$/g, '')
          .trim();
      })
      .filter((label) => label.length > 2)
      .slice(0, 9);
    const actual = links.map((a) => (a.getAttribute('aria-label') || a.textContent)
      .replace(/\s+/g, ' ').trim());
    t.ok('Mini-TOC ≡ sichtbarem Überschriftentext (Label-Vertrag)',
      JSON.stringify(actual) === JSON.stringify(expected),
      `erwartet ${JSON.stringify(expected)}, erhalten ${JSON.stringify(actual)}`);
  }
}

/* ============================================================
   6 · ZUKUNFTS-IMMUNITÄT: Eine feindliche „§“-Injektion bleibt
       wirkungslos (Wand 4: Button-Strip + Wand 5: Sicherheitsnetz)
   ============================================================ */
t.group('6) Feind-Injektion: „§“-Button einer künftigen Erweiterung wird weggefiltert');
{
  const { win, doc } = loadPage(skeleton({
    title: 'Girokonto ohne Gebühren',
    kurzantwort: 'Kostenlose Girokonten gibt es 2026 bei mehreren Direktbanken.',
    bodyHtml: mdToHtml([
      '## Kontoführung',
      '',
      'Viele Banken verzichten 2026 auf die Kontoführungsgebühr.',
      '',
      '## Karten und Abhebungen',
      '',
      'Kostenlose Girokonten ermöglichen meist drei Abhebungen pro Monat.',
      '',
      '## Fazit',
      '',
      'Der Wechsel lohnt sich ab rund 60 Euro Ersparnis im Jahr.',
    ].join('\n')),
  }));
  await loadPremium(win);
  const api = win.__ffVoice;

  // Feind-Szenario A: eine KÜNFTIGE Erweiterung setzt einen „§“-Knopf
  // INS redaktionelle Etikett — ohne data-ff-skip-read, ohne bekannte Klasse.
  const firstHeading = doc.querySelector('.post-content h2[id] .ff-heading-text');
  const hostile = doc.createElement('button');
  hostile.className = 'future-extension-glyph';
  hostile.textContent = '§';
  firstHeading.appendChild(hostile);
  // Feind-Szenario B: roher „§“-Textknoten am Ende der Überschrift.
  doc.querySelector('.post-content h2[id]').appendChild(doc.createTextNode('§'));

  const plain = api.summaryPlainText();
  t.ok('Klartext-Gliederung bleibt trotz Feind-Injektion §-frei',
    plainTocLines(plain).every((l) => !l.includes('§')),
    'Auszug: ' + plainTocLines(plain).join(' | '));
  const blocks = api.collectBlocks();
  t.ok('Vorlese-Blöcke bleiben trotz Feind-Injektion §-frei',
    blocks.filter((b) => /^H[23]$/.test(b.type)).every((b) => !b.text.includes('§')),
    blocks.filter((b) => /^H[23]$/.test(b.type) && b.text.includes('§')).map((b) => b.text).join(' | '));

  doc.getElementById('ff-voice-summary').click();
  const dlg = doc.getElementById('ff-voice-dialog');
  t.ok('Dialog trotz Feind-Injektion geöffnet', !!dlg);
  const tocLinks = [...doc.querySelectorAll('.ff-voice-toc a')];
  t.ok('Dialog-Gliederung bleibt trotz Feind-Injektion §-frei',
    tocLinks.every((a) => !a.textContent.includes('§')),
    tocLinks.filter((a) => a.textContent.includes('§')).map((a) => a.textContent).join(' | '));

  // Feind-Szenario C (Wand 5 — ff-summary-safety.js): angelblich harmlose
  // Erweiterung hängt ein „§“ DIREKT an einen Verzeichnis-Eintrag im Dialog.
  win.eval(fs.readFileSync(SAFETY_PATH, 'utf8'));
  const victim = tocLinks[0];
  victim.appendChild(doc.createTextNode('§'));
  await sleep(60); // MutationObserver der Wache laufen lassen
  t.ok('Sicherheitsnetz kürzt den feindlichen Ankerrest im Dialog',
    !/[§]$/.test(victim.textContent), 'steht noch: „' + victim.textContent + '“');
}

/* ============================================================
   7 · IM GESAMTEN BLOG: alle echten Artikel
   ============================================================ */
t.group('7) Alle echten Artikel: Kurzfassung §-frei, Labels treu');
{
  const articles = listArticles();
  t.ok('Artikel gefunden', articles.length > 0, 'gefunden: ' + articles.length);

  let crashed = 0;
  let missingBtn = 0;
  let dirtyToc = 0;
  let labelMismatch = 0;
  const failures = [];

  for (const article of articles) {
    const slug = article.slug;
    try {
      const { win, doc } = loadPage(skeleton({
        title: article.data.title || slug,
        description: article.data.description || '',
        kurzantwort: article.data.kurzantwort || article.data.description || '',
        readingTime: parseInt(article.data.readingTime || '5', 10) || 5,
        wordCount: 1200,
        author: article.data.author || 'Frank Hartung',
        date: article.data.date ? String(article.data.date).slice(0, 10) : '05.09.2026',
        slug: slug,
        bodyHtml: mdToHtml(article.body),
      }));
      await loadPremium(win);
      const api = win.__ffVoice;

      // 1 · Button an jeder Abschnitts-Überschrift (Funktion intakt)
      const headings = doc.querySelectorAll('.post-content h2[id], .post-content h3[id]');
      const buttons = doc.querySelectorAll('.ff-heading-copy');
      if (buttons.length !== headings.length) {
        missingBtn += 1;
        failures.push(slug + ` (Copy-Button: ${buttons.length}/${headings.length})`);
      }

      // 2 · Dialog-Gliederung: kein „§“, Label-Vertrag
      doc.getElementById('ff-voice-summary').click();
      const dlg = doc.getElementById('ff-voice-dialog');
      if (!dlg) { failures.push(slug + ' (Dialog fehlt)'); continue; }
      const tocLinks = [...dlg.querySelectorAll('.ff-voice-toc a')];
      if (tocLinks.some((a) => a.textContent.includes('§'))) {
        dirtyToc += 1;
        failures.push(slug + ' (Dialog-Gliederung mit §)');
      }
      const expected = visibleHeadingLabels(doc);
      const actual = tocLinks.map((a) => a.textContent.replace(/\s+/g, ' ').trim());
      if (JSON.stringify(actual) !== JSON.stringify(expected)) {
        labelMismatch += 1;
        failures.push(slug + ` (Label-Vertrag: ${actual.length} vs ${expected.length})`);
      }

      // 3 · Klartext-Kopie: Gliederungssektion §-frei
      const plain = api.summaryPlainText();
      if (plainTocLines(plain).some((l) => l.includes('§'))) {
        dirtyToc += 1;
        failures.push(slug + ' (Klartext-Gliederung mit §)');
      }
    } catch (e) {
      crashed += 1;
      failures.push(slug + ' (' + e.message + ')');
    }
  }

  t.eq('Kein Artikel stürzt ab', crashed, 0, failures.slice(0, 4).join(' | '));
  t.eq('Copy-Button an jeder Überschrift (Funktion intakt)', missingBtn, 0,
    failures.filter((f) => f.includes('Copy-Button')).slice(0, 4).join(' | '));
  t.eq('Kein „§“ in Dialog- oder Klartext-Gliederung', dirtyToc, 0,
    failures.filter((f) => f.includes('§')).slice(0, 4).join(' | '));
  t.eq('Gliederung ≡ sichtbarem Überschriftentext in jedem Artikel', labelMismatch, 0,
    failures.filter((f) => f.includes('Label-Vertrag')).slice(0, 4).join(' | '));
  console.log(`    · ${articles.length} Artikel geprüft (Dialog, Klartext, Button-Markup)`);
}

t.done();
