/**
 * ff_toc_beweglich_test.mjs — Wache für das bewegliche, vollständige
 * Artikel-Inhaltsverzeichnis (static/premium/ff-premium.js).
 * ------------------------------------------------------------
 * Frank-Befund 26.09.2026:
 *   1. „Das Inhaltsverzeichnis der gesamten Blogartikel vollständig
 *       anzeigen“  → alle H2 UND H3, voller Überschriftentext.
 *   2. „nicht fest stehen, sondern beweglich“ → die Box lässt sich
 *       an der Kopfzeile ziehen (Zeiger), per Pfeiltasten schieben,
 *       merkt sich die Position und kehrt per „Home“ / Doppelklick /
 *       Knopf auf den Standardplatz zurück.
 *
 * Diese Wache prüft gegen die ECHTE Datei in einer echten DOM (jsdom) –
 * grün hier heißt grün im Browser.
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
  await sleep(20);
}

function pointer(win, type, x, y) {
  const ev = new win.MouseEvent(type, { bubbles: true, cancelable: true, clientX: x, clientY: y, button: 0 });
  Object.defineProperty(ev, 'pointerId', { value: 1 });
  return ev;
}

const { win, doc } = article();
await boot(win);

t.group('1) Vollständigkeit');
const nav = doc.querySelector('.ff-mini-toc');
t.ok('Navigation erzeugt', !!nav);
const links = [...doc.querySelectorAll('.ff-mini-toc__list a')];
const headings = [...doc.querySelectorAll('.post-content h2[id], .post-content h3[id]')];
t.eq('Ein Eintrag je Überschrift (H2 + H3)', links.length, headings.length);
t.ok('Unterabschnitte sind als solche markiert',
  links.filter((a) => a.classList.contains('ff-mini-toc--sub')).length === 2);
t.ok('Keine gekürzten Titel („…“)', links.every((a) => !a.textContent.includes('…')),
  links.map((a) => a.textContent).join(' | '));
t.ok('„Fazit“ und „Häufige Fragen“ enthalten',
  links.some((a) => a.textContent.startsWith('Fazit')) &&
  links.some((a) => a.textContent.includes('Häufige Fragen')));
t.ok('Zähler nennt die Gesamtzahl',
  (doc.querySelector('.ff-mini-toc__count') || {}).textContent.trim().endsWith('/ ' + headings.length));

t.group('2) Beweglichkeit');
const head = doc.querySelector('.ff-mini-toc__head');
t.ok('Kopfzeile ist Griff und fokussierbar', !!head && head.getAttribute('tabindex') === '0');
t.ok('Griff erklärt sich (aria-label)', !!head && /verschieben/i.test(head.getAttribute('aria-label') || ''));
t.ok('Standardzustand ist nicht „verschoben“', !nav.classList.contains('ff-mini-toc--moved'));

head.dispatchEvent(pointer(win, 'pointerdown', 900, 200));
head.dispatchEvent(pointer(win, 'pointermove', 700, 420));
head.dispatchEvent(pointer(win, 'pointerup', 700, 420));
t.ok('Nach dem Ziehen als „verschoben“ markiert', nav.classList.contains('ff-mini-toc--moved'));
t.ok('Inline-Position gesetzt (left/top statt fixem Platz)',
  !!nav.style.left && !!nav.style.top && nav.style.right === 'auto',
  `left=${nav.style.left} top=${nav.style.top} right=${nav.style.right}`);
const gemerkt = win.localStorage.getItem('ff:toc:pos:v1');
t.ok('Position wird gemerkt (localStorage)', !!gemerkt && /left/.test(gemerkt), String(gemerkt));

const vorTaste = nav.style.top;
head.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'ArrowDown', bubbles: true, cancelable: true }));
t.ok('Pfeiltaste verschiebt (Tastaturbedienung)', nav.style.top !== vorTaste,
  `${vorTaste} → ${nav.style.top}`);

head.dispatchEvent(new win.KeyboardEvent('keydown', { key: 'Home', bubbles: true, cancelable: true }));
t.ok('„Home“ stellt den Standardplatz wieder her',
  !nav.classList.contains('ff-mini-toc--moved') && !nav.style.left && !nav.style.top);
t.ok('Gemerkte Position ist gelöscht', !win.localStorage.getItem('ff:toc:pos:v1'));

const reset = doc.querySelector('.ff-mini-toc__reset');
t.ok('Zurücksetzen-Knopf vorhanden und beschriftet',
  !!reset && /zurücksetzen/i.test(reset.getAttribute('aria-label') || ''));
head.dispatchEvent(pointer(win, 'pointerdown', 900, 200));
head.dispatchEvent(pointer(win, 'pointermove', 400, 300));
head.dispatchEvent(pointer(win, 'pointerup', 400, 300));
reset.dispatchEvent(new win.MouseEvent('click', { bubbles: true, cancelable: true }));
t.ok('Knopf stellt den Standardplatz wieder her', !nav.classList.contains('ff-mini-toc--moved'));

t.group('3) Gemerkte Position überlebt den Seitenwechsel');
{
  const zweite = article();
  zweite.win.localStorage.setItem('ff:toc:pos:v1', JSON.stringify({ left: 120, top: 90 }));
  await boot(zweite.win);
  const nav2 = zweite.doc.querySelector('.ff-mini-toc');
  t.ok('Position wird beim nächsten Artikel wiederhergestellt',
    !!nav2 && nav2.classList.contains('ff-mini-toc--moved') && nav2.style.left === '120px',
    nav2 ? `${nav2.style.left}/${nav2.style.top}` : 'keine Navigation');
}

t.group('4) Kein Ausschluss: Position bleibt im Fenster');
{
  const dritte = article();
  dritte.win.localStorage.setItem('ff:toc:pos:v1', JSON.stringify({ left: 99999, top: 99999 }));
  await boot(dritte.win);
  const nav3 = dritte.doc.querySelector('.ff-mini-toc');
  const left = parseFloat(nav3.style.left);
  const top = parseFloat(nav3.style.top);
  t.ok('Außerhalb liegende Werte werden in den sichtbaren Bereich geholt',
    left >= 12 && left <= dritte.win.innerWidth && top >= 12 && top <= dritte.win.innerHeight,
    `${left}/${top} bei ${dritte.win.innerWidth}×${dritte.win.innerHeight}`);
}

t.done();
