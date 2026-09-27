/**
 * Wache für die vollständige, bewegliche Artikel-Navigation.
 * Der Positionszustand bleibt ausdrücklich nur in der aktuellen Seite:
 * keinerlei localStorage, Cookies oder sonstige Persistenz.
 */
import { createRunner, loadPage, skeleton, mdToHtml, fs, path, ROOT, sleep } from './ff_voice_qa_lib.mjs';

const PREMIUM_PATH = path.join(ROOT, 'static', 'premium', 'ff-premium.js');
const t = createRunner('Bewegliches, vollständiges Inhaltsverzeichnis');

function article() {
  return loadPage(skeleton({
    title: 'Stromvergleich 2026',
    kurzantwort: 'Ein Wechsel spart im Schnitt mehrere hundert Euro im Jahr.',
    bodyHtml: mdToHtml([
      '## Das Wichtigste in Kürze', '', 'Kurz und sachlich.', '',
      '### So liest du die Tabelle', '', 'Ein Unterabschnitt.', '',
      '## Wie der Wechsel Schritt für Schritt abläuft', '', 'Der Ablauf.', '',
      '### Welche Unterlagen du brauchst', '', 'Die Unterlagen.', '',
      '## Fazit: Der Vergleich lohnt sich jedes Jahr aufs Neue', '', 'Das Fazit.', '',
      '## Häufige Fragen', '', 'Die Fragen.',
    ].join('\n')),
  }));
}

async function boot(win) {
  win.eval(fs.readFileSync(PREMIUM_PATH, 'utf8'));
  if (!win.document.querySelector('.ff-mini-toc')) {
    win.document.dispatchEvent(new win.Event('DOMContentLoaded'));
  }
  await sleep(30);
}

function pointer(win, type, x, y) {
  const ev = new win.MouseEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0 });
  Object.defineProperties(ev, {
    pointerId: { value: 1 },
    pointerType: { value: 'mouse' },
  });
  return ev;
}

const { win, doc } = article();
await boot(win);

const nav = doc.querySelector('.ff-mini-toc');
const head = doc.querySelector('.ff-mini-toc__head');
const links = [...doc.querySelectorAll('.ff-mini-toc__list a')];
const headings = [...doc.querySelectorAll('.post-content h2[id], .post-content h3[id]')];

t.group('1) Vollständigkeit');
t.ok('Navigation erzeugt', !!nav);
t.eq('Ein Eintrag je Überschrift (H2 + H3)', links.length, headings.length);
t.ok('Semantische, nummerierte Liste (ol/li)',
  doc.querySelector('.ff-mini-toc__list')?.tagName === 'OL'
  && doc.querySelectorAll('.ff-mini-toc__list > li').length === headings.length);
t.eq('Unterabschnitte hierarchisch markiert',
  links.filter((a) => a.classList.contains('ff-mini-toc--sub')).length, 2);
t.ok('Keine gekürzten Titel („…“)', links.every((a) => !a.textContent.includes('…')));
t.ok('Zähler nennt die Gesamtzahl',
  (doc.querySelector('.ff-mini-toc__count') || {}).textContent.trim().endsWith('/ ' + headings.length));

t.group('2) Beweglichkeit und Datenschutz');
t.ok('Kopfzeile ist Griff und fokussierbar', !!head && head.getAttribute('tabindex') === '0');
t.ok('Griff erklärt sich (aria-label)', !!head && /verschieben/i.test(head.getAttribute('aria-label') || ''));
t.ok('Griff-Signet ist dekorativ', !!nav?.querySelector('.ff-mini-toc__grip[aria-hidden="true"]'));
t.ok('Kein persistierender Reset-Knopf', !nav?.querySelector('.ff-mini-toc__reset'));
t.ok('Quellcode verwendet keine Positions-Persistenz',
  !fs.readFileSync(PREMIUM_PATH, 'utf8').includes('ff:toc:pos:v1'));

const dock = { left: nav.style.left, top: nav.style.top, right: nav.style.right };
head.dispatchEvent(pointer(win, 'pointerdown', 900, 200));
head.dispatchEvent(pointer(win, 'pointermove', 700, 420));
await sleep(30);
head.dispatchEvent(pointer(win, 'pointerup', 700, 420));
t.ok('Nach dem Ziehen ist eine Inline-Position gesetzt',
  !!nav.style.left && !!nav.style.top && nav.style.right === 'auto',
  `left=${nav.style.left} top=${nav.style.top} right=${nav.style.right}`);
t.ok('Drag-Ende räumt Klasse ab', !nav.classList.contains('ff-mini-toc--dragging'));
t.ok('localStorage bleibt unberührt', !win.localStorage.getItem('ff:toc:pos:v1'));

const beforeKey = nav.style.top;
head.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, cancelable: true }));
t.ok('Pfeiltaste verschiebt die Navigation', nav.style.top !== beforeKey,
  `${beforeKey} → ${nav.style.top}`);
head.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'Home', bubbles: true, cancelable: true }));
t.eq('Pos1 löst die Inline-Position', nav.style.left, dock.left);
t.eq('Pos1 stellt die Standardhöhe wieder her', nav.style.top, dock.top);
t.eq('Pos1 stellt die Standard-Rechtskante wieder her', nav.style.right, dock.right);

t.done();
