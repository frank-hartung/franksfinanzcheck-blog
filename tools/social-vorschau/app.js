/* Social-Vorschau – reine Anzeige.
   Keine Fetch-Aufrufe, kein Analytics, keine Speicherung. Alle Daten stehen
   im <script type="application/json">-Block der Seite; gerendert wird
   ausschließlich über textContent (nie innerHTML mit Daten). */
'use strict';

/** Text an einer Zeichengrenze teilen – ohne Wörter zu zerschneiden.
 *  Zählt Codepoints wie Python (Array.from), damit Anzeige und Bericht
 *  dieselbe Zahl nennen. */
function splitAt(text, limit) {
  const value = String(text ?? '');
  const zeichen = Array.from(value);
  if (zeichen.length <= limit) return { sichtbar: value, rest: '', ueber: false, laenge: zeichen.length };
  let schnitt = limit;
  const naechstes = zeichen.slice(schnitt).findIndex(c => c === ' ');
  if (naechstes > -1 && naechstes < 24) schnitt += naechstes;
  return {
    sichtbar: zeichen.slice(0, schnitt).join(''),
    rest: zeichen.slice(schnitt).join(''),
    ueber: true,
    laenge: zeichen.length,
  };
}

/** Befunde, die für den gewählten Kanal gelten: kanalunabhängige ("*") und
 *  eigene – außer der Befund nennt den Kanal ausdrücklich als Ausnahme
 *  (`ausser`). Beispiel: Ein Hochformat-Cover ist für Pinterest richtig und
 *  für Feed-Karten beschnitten; auf der Pinterest-Karte wäre der Hinweis falsch. */
function befundeFuerKanal(befunde, kanal) {
  return (befunde || []).filter(b =>
    (b.kanal === '*' || b.kanal === kanal) && !(b.ausser || []).includes(kanal));
}

function hatBefund(page, kanal) {
  return befundeFuerKanal(page.befunde, kanal).length > 0;
}

/** Suche + Auswahlfilter. Kanalspezifisch, damit „nur Befunde“ zum Kanal passt. */
function filterSeiten(pages, { suche = '', filter = 'alle', kanal = '' } = {}) {
  const q = String(suche).toLocaleLowerCase('de-DE').trim();
  return (pages || []).filter(page => {
    const heu = `${page.titel_og} ${page.titel} ${page.url} ${page.slug}`.toLocaleLowerCase('de-DE');
    if (q && !heu.includes(q)) return false;
    if (filter === 'ohne-bild' && page.bild_breite) return false;
    if (filter === 'befunde' && !hatBefund(page, kanal)) return false;
    return true;
  });
}

/** Datum als kurze, deutsche Zeitangabe; ungültige Werte werden nicht erfunden. */
function formatDatum(iso) {
  const datum = new Date(iso);
  if (Number.isNaN(datum.getTime())) return 'unbekannt';
  return datum.toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' });
}

if (typeof module !== 'undefined') module.exports = { splitAt, befundeFuerKanal, filterSeiten, hatBefund, formatDatum };

if (typeof document !== 'undefined') {
  const $ = id => document.getElementById(id);
  const daten = JSON.parse($('vorschau-data').textContent);
  const nf = new Intl.NumberFormat('de-DE');
  let kanal = (daten.kanaele[0] || {}).id || 'x';

  const el = (tag, text, cls) => {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (cls) node.className = cls;
    return node;
  };

  function kennzahl(label, wert, hinweis) {
    const box = el('div', undefined, 'kennzahl');
    box.append(el('span', label), el('strong', nf.format(wert)), el('small', hinweis));
    $('kennzahlen').append(box);
  }

  const summe = daten.summary;
  $('stempel-zeit').textContent = formatDatum(daten.generated_at);
  $('stempel-quelle').textContent = `Quelle: ${daten.herkunft}`;
  kennzahl('Seiten geprüft', summe.seiten, `Grenzstand ${daten.stand}`);
  kennzahl('Ohne Vorschaubild', summe.ohne_bild, 'Karte bleibt bildlos');
  kennzahl('Befunde gesamt', summe.befunde, 'über alle Kanäle');
  kennzahl('Kanäle', daten.kanaele.length, 'Richtwerte, keine Messung');

  // Kanalwahl
  function zeichneKanaele() {
    $('kanaele').replaceChildren();
    for (const k of daten.kanaele) {
      const b = el('button', k.name, 'wahl');
      b.type = 'button';
      b.setAttribute('aria-pressed', String(k.id === kanal));
      b.addEventListener('click', () => {
        kanal = k.id;
        zeichneKanaele();
        zeichne();
      });
      $('kanaele').append(b);
    }
    const gewaehlt = daten.kanaele.find(k => k.id === kanal) || {};
    $('kanal-notiz').textContent = gewaehlt.notiz
      ? `${gewaehlt.notiz} Quelle des Richtwerts: ${gewaehlt.quelle}.`
      : '';
  }

  function karte(page) {
    const grenze = daten.kanaele.find(k => k.id === kanal) || { titel_max: 70, beschreibung_max: 200 };
    const artikel = el('article', undefined, page.bild_breite ? 'karte' : 'karte bild-fehlt');
    const flaeche = el('div', undefined, 'bild-fläche');
    if (page.bild_datei) {
      const bild = el('img');
      bild.src = page.bild_datei;
      bild.alt = page.bild ? page.bild.alt || '' : '';
      bild.loading = 'lazy';
      bild.decoding = 'async';
      bild.addEventListener('error', () => {
        flaeche.replaceChildren(el('span', 'Bild nicht ladbar – Pfad prüfen', 'fehlt'));
        if (page.bild_breite) flaeche.append(el('span', 'Maße aus Datei', 'bild-maß'));
      });
      flaeche.append(bild);
    } else {
      flaeche.append(el('span', 'Kein Vorschaubild hinterlegt', 'fehlt'));
    }
    if (page.bild_breite && page.bild_hoehe) {
      flaeche.append(el('span', `${page.bild_breite}×${page.bild_hoehe}`, 'bild-maß'));
    }
    artikel.append(flaeche);

    const inhalt = el('div', undefined, 'inhalt');
    let host = page.url;
    try { host = new URL(page.url).host + new URL(page.url).pathname; } catch { /* Rohtext */ }
    inhalt.append(el('p', host, 'herkunft'));

    const kopf = el('h3');
    const titel = splitAt(page.titel_og, grenze.titel_max);
    kopf.append(document.createTextNode(titel.sichtbar));
    if (titel.ueber) kopf.append(el('span', titel.rest, 'rest'));
    inhalt.append(kopf);

    const text = el('p', undefined, 'text');
    const beschreibung = splitAt(page.beschreibung, grenze.beschreibung_max);
    if (beschreibung.sichtbar) {
      text.append(document.createTextNode(beschreibung.sichtbar));
      if (beschreibung.ueber) text.append(el('span', beschreibung.rest, 'rest'));
    } else {
      text.append(document.createTextNode('Keine Beschreibung hinterlegt.'));
    }
    inhalt.append(text);

    const zaehler = el('div', undefined, 'zaehler');
    const titelZahl = el('span', `Titel ${titel.laenge}/${grenze.titel_max}`);
    if (titel.ueber) titelZahl.className = 'ueber';
    const textZahl = el('span', `Text ${beschreibung.laenge}/${grenze.beschreibung_max}`);
    if (beschreibung.ueber) textZahl.className = 'ueber';
    zaehler.append(titelZahl, textZahl);
    inhalt.append(zaehler);

    const liste = befundeFuerKanal(page.befunde, kanal);
    if (liste.length) {
      const ul = el('ul', undefined, 'befunde');
      for (const b of liste) {
        const li = el('li');
        li.append(el('span', b.schwere, `marke-schwere ${b.schwere.toLowerCase()}`),
                  el('span', `${b.detail} ${b.massnahme}`));
        ul.append(li);
      }
      inhalt.append(ul);
    } else {
      inhalt.append(el('p', 'Kein Befund für diesen Kanal.', 'ohne-befund'));
    }

    const fuss = el('footer');
    const link = el('a', 'Seite in neuem Tab öffnen');
    // Wie im SEO-Cockpit: nur geprüfte http(s)-Ziele verlinken. Ohne die
    // Prüfung wäre ein `javascript:`-Ziel aus dem Inhalt im lokalen Bericht
    // ein Klick-XSS (CodeQL js/xss-through-dom, Lauf vom 28.10.2026).
    try {
      const ziel = new URL(page.url);
      if (ziel.protocol === 'https:' || ziel.protocol === 'http:') link.href = ziel.href;
    } catch { /* Rohtext statt unsicherem Link */ }
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    fuss.append(link, el('span', page.sektion === 'pillar' ? 'Pillar' : page.sektion === 'build' ? 'Build' : 'Artikel'));
    inhalt.append(fuss);
    artikel.append(inhalt);
    return artikel;
  }

  function zeichne() {
    const seiten = filterSeiten(daten.pages, {
      suche: $('suche').value,
      filter: $('filter').value,
      kanal,
    });
    const behaelter = $('karten');
    behaelter.replaceChildren();
    if (!seiten.length) {
      behaelter.append(el('p', 'Keine Seite passt zu dieser Auswahl. Suche leeren oder Filter ändern.', 'leer'));
    } else {
      const grenze = 240;
      for (const page of seiten.slice(0, grenze)) behaelter.append(karte(page));
      if (seiten.length > grenze) {
        behaelter.append(el('p', `Nur die ersten ${grenze} von ${seiten.length} Seiten werden angezeigt. Nutze die Suche, um einzugrenzen.`, 'leer'));
      }
    }
    const mitBefund = seiten.filter(p => hatBefund(p, kanal)).length;
    $('treffer').textContent = `${nf.format(seiten.length)} von ${nf.format(daten.pages.length)} Seiten · `
      + `${nf.format(mitBefund)} mit Befund im Kanal · ${nf.format(summe.ohne_bild)} ohne Bild insgesamt`;
  }

  $('suche').addEventListener('input', zeichne);
  $('filter').addEventListener('change', zeichne);
  $('theme').addEventListener('click', () => {
    const dunkel = document.documentElement.dataset.theme === 'dark'
      || (!document.documentElement.dataset.theme && matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.dataset.theme = dunkel ? 'light' : 'dark';
  });

  zeichneKanaele();
  zeichne();
}
