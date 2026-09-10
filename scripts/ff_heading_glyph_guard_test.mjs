/**
 * ff_heading_glyph_guard_test.mjs — „§“-Wache: Abschnitts-Copy-Button
 * darf nie in Kurzfassung, Klartext-Kopie oder Vorlesen durchrutschen
 * ------------------------------------------------------------
 * Befund 10.09.2026: Der von ff-premium.js in jede Überschrift
 * injizierte „§“-Copy-Button wurde als Text gelesen. In der Folge
 * zeigte JEDER Artikel im gesamten Blog in der Kurzfassung ein „§“
 * an jeder Gliederung (und das Vorlesen sprach „§“ mit).
 *
 * Reparierter Zustand (dreifach abgesichert, s. ff-premium.js /
 * ff-voice.js):
 *   1. Glyph lebt in <span aria-hidden="true"> (dekorativ),
 *   2. Button trägt data-ff-skip-read (etablierte Konvention),
 *   3. ff-voice.js::readableText() strippt jegliche <button>-Knoten,
 *      buildToc() wäscht zusätzlich §/¶/# aus den Labels.
 *
 * Diese Wache lädt die ECHTE Produktions-Dateien (ff-voice.js +
 * ff-premium.js) gegen eine ECHTE DOM (jsdom) und pinnt:
 *   · Button-Markup ist extraktionssicher (und die Funktion bleibt),
 *   · Kurzfassung-Dialog + Gliederung + Klartext-Kopie: kein „§“,
 *   · Gliederung ≡ sichtbarem Überschriftentext (Label-Vertrag),
 *   · TTS-Blöcke: kein „§“,
 *   · legitimes „§“ im Artikeltext („§ 8 EinSiG“) bleibt erhalten,
 *   · Mini-TOC (ff-premium.js) bleibt sauber,
 *   · IM GESAMTEN BLOG: alle echten Artikel durchlaufen die Prüfung.
 *
 * Aufruf: node scripts/ff_heading_glyph_guard_test.mjs
 *         (jsdom liegt in tools/ff-voice-qa/node_modules)
 */

import { createRunner, loadPage, skeleton, mdToHtml, listArticles, fs, path, ROOT, sleep } from './ff_voice_qa_lib.mjs';

const PREMIUM_PATH = path.join(ROOT, 'static', 'premium', 'ff-premium.js');

const t = createRunner('„§“-Wache: Kurzfassung, Klartext, Vorlesen bleiben §-frei');

/** Lädt die ECHTE ff-premium.js.
    Die Initialisierung läuft auf DOMContentLoaded (ready()-Muster); in
    jsdom ist der readyState beim Eval noch „loading“ und das Event
    kommt als Task — deshalb kurz warten, bis die Buttons stehen. */
async function loadPremium(win) {
  win.eval(fs.readFileSync(PREMIUM_PATH, 'utf8'));
  const doc = win.document;
  if (doc.readyState !== 'complete') {
    await new Promise((resolve) => {
      doc.addEventListener('DOMContentLoaded', resolve, { once: true });
      setTimeout(resolve, 150); // Fallback, falls das Event schon gefeuert hat
    });
  }
  await sleep(20); // Task-Flush (Reveal-Fallback & Co.)
}

/** Gleiche Label-Konvention wie buildToc()/ff-mini-toc: UI-Schmuck weg. */
function cleanLabel(text) {
  return String(text == null ? '' : text)
    .replace(/[\u00a0]+/g, ' ')
    .replace(/[§¶#]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Der sichtbare Überschriftentext (ohne UI-Button) — das Label,
    das die Gliederung zeigen muss (Vertrag mit buildToc()). */
function visibleHeadingLabels(doc) {
  return [...doc.querySelectorAll('.post-content h2, .md-content h2, .post-content h3, .md-content h3')]
    .map((h) => {
      const clone = h.cloneNode(true);
      clone.querySelectorAll('.ff-heading-copy').forEach((b) => b.remove());
      return cleanLabel(clone.textContent || '');
    })
    .filter((label) => label.length > 2);
}

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

let fixture = null;   // wird in Gruppe 1 geladen, in 2–4 und 6 weitergenutzt

/* ============================================================
   1 · Injection: Echte ff-premium.js, extraktionssicheres Markup
   ============================================================ */
t.group('1) ff-premium.js injiziert den „§“-Button extraktionssicher');
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
    const glyph = b.querySelector('span[aria-hidden="true"]');
    const okGlyph = !!glyph && glyph.textContent === '§';
    const okAttrs = b.getAttribute('data-ff-skip-read') !== null
      && b.type === 'button'
      && b.getAttribute('aria-label') === 'Link zu diesem Abschnitt kopieren';
    const okPosition = b === b.parentElement.lastElementChild;
    if (!okGlyph || !okAttrs || !okPosition) { markupOk = false; detail = 'Button #' + i; }
  });
  t.ok('Glyph „§“ ist sichtbar (Funktion bleibt erhalten)', markupOk, detail);
  t.ok('Glyph ist dekorativ (aria-hidden-Span)', markupOk, detail);
  t.ok('Button trägt data-ff-skip-read (Extraktor-Konvention)', markupOk, detail);
  t.ok('Button bleibt zugänglich (aria-label)', markupOk, detail);
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
        clone.querySelectorAll('.ff-heading-copy').forEach((b) => b.remove());
        return cleanLabel(clone.textContent || '');
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
   6 · IM GESAMTEN BLOG: alle echten Artikel
   ============================================================ */
t.group('6) Alle echten Artikel: Kurzfassung §-frei, Labels treu');
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
