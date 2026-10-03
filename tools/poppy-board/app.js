/* Poppy-Werkbank – Board-Dashboard (offline, keine Netzwerk-Requests).
 * Liest die eingebetteten Daten aus #board-data und rendert das Board.
 * Muster wie tools/seo-cockpit/app.js: keine Abhängigkeiten, CSP-konform. */
(function () {
  'use strict';

  var PILLARS = { // lesbare Pillar-Namen für Badges
    'strom-sparen': 'Strom & Gas',
    'versicherungen': 'Versicherungen',
    'internet-dsl': 'Internet & DSL',
    'konto-karten': 'Konto & Karten',
    'mietwagen': 'Mobilität',
    'frugalismus': 'Budget & Frugalismus'
  };

  function $(sel, root) { return (root || document).querySelector(sel); }
  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function datumKurz(iso) {
    if (!iso) return '';
    var d = new Date(iso);
    if (isNaN(d)) return String(iso).slice(0, 10);
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: 'short', year: 'numeric' });
  }
  function zahl(n) { return Number(n || 0).toLocaleString('de-DE'); }

  // ---------- Daten laden (eingebettet, kein fetch) ----------
  function ladeDaten() {
    var roh = $('#board-data');
    if (!roh) throw new Error('Keine #board-data gefunden');
    return JSON.parse(roh.textContent);
  }

  // ---------- Clipboard mit Fallback ----------
  function kopieren(text, button) {
    var fertig = function () {
      var alt = button.textContent;
      button.textContent = 'Kopiert ✓';
      button.classList.add('ok');
      setTimeout(function () { button.textContent = alt; button.classList.remove('ok'); }, 1600);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(fertig, function () { fallback(); });
    } else { fallback(); }
    function fallback() {
      var f = document.createElement('textarea');
      f.value = text; f.setAttribute('readonly', '');
      f.style.position = 'fixed'; f.style.left = '-9999px';
      document.body.appendChild(f); f.select();
      try { document.execCommand('copy'); fertig(); } catch (e) { /* leer */ }
      document.body.removeChild(f);
    }
  }

  function copyBlock(label, text, mehrzeilig) {
    var wrap = el('div', 'copyblock');
    var kopf = el('div', 'copyblock-kopf');
    kopf.appendChild(el('span', '', label));
    var b = el('button', 'copy'); b.type = 'button'; b.textContent = 'Kopieren';
    b.addEventListener('click', function () { kopieren(text, b); });
    kopf.appendChild(b);
    wrap.appendChild(kopf);
    var inhalt = el(mehrzeilig ? 'pre' : 'p', 'copyblock-text', text || '–');
    wrap.appendChild(inhalt);
    return wrap;
  }

  // ---------- Karten ----------
  function kartenKopf(k) {
    var kopf = el('div', 'karte-kopf');
    var linke = el('div', 'karte-titelzeile');
    linke.appendChild(el('span', 'typ-badge', k.typ_icon + ' ' + typName(k.typ)));
    if (k.pillar) linke.appendChild(el('span', 'pillar-badge', PILLARS[k.pillar] || k.pillar));
    kopf.appendChild(linke);
    var titel = el('h3', 'karte-titel');
    if (k.url) {
      var a = el('a', '', k.titel); a.href = k.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
      titel.appendChild(a);
    } else { titel.textContent = k.titel; }
    kopf.appendChild(titel);
    var meta = el('p', 'karte-meta');
    var teile = [];
    if (k.autor) teile.push(esc(k.autor));
    if (k.datum) teile.push(datumKurz(k.datum));
    teile.push(zahl(k.inhalt_zeichen) + ' Zeichen Quelltext');
    if (k.inhalt_methode) teile.push('(' + k.inhalt_methode + ')');
    meta.innerHTML = teile.join(' · ');
    kopf.appendChild(meta);
    return kopf;
  }

  function typName(t) {
    return { youtube: 'YouTube', podcast: 'Podcast/Feed', artikel: 'Artikel',
             pdf: 'PDF', text: 'Notiz' }[t] || t;
  }

  function insightsBlock(k) {
    var box = el('div', 'insights');
    box.appendChild(el('h4', '', 'Insights'));
    var ul = el('ul');
    (k.insights && k.insights.length ? k.insights : ['(noch keine Insights)']).forEach(function (i) {
      ul.appendChild(el('li', '', i));
    });
    box.appendChild(ul);
    if (k.winkel) {
      var w = el('p', 'winkel');
      w.appendChild(el('strong', '', 'Artikel-Winkel: '));
      w.appendChild(document.createTextNode(k.winkel));
      box.appendChild(w);
    }
    if (k.hinweis) box.appendChild(el('p', 'hinweis', '⚠ ' + k.hinweis));
    return box;
  }

  function erzeugnisBlock(k) {
    var e = k.erzeugnisse || {};
    var box = el('div', 'erzeugnisse');
    box.appendChild(el('h4', '', 'Erzeugnisse'));
    if (e.blog_slug) {
      var blog = el('div', 'blog-entwurf');
      var zeile = el('p');
      zeile.appendChild(el('strong', '', 'Blog-Entwurf: '));
      zeile.appendChild(document.createTextNode(e.blog_slug));
      blog.appendChild(zeile);
      var detail = el('p', 'muted',
        (e.blog_provider ? 'via ' + e.blog_provider + ' · ' : '') +
        zahl(e.blog_zeichen) + ' Zeichen · draft: true');
      blog.appendChild(detail);
      if (e.freigabe) {
        blog.appendChild(copyBlock('Freigabe-Befehl (Terminal)', e.freigabe, false));
      }
      box.appendChild(blog);
    }
    if (e.kurzantwort) box.appendChild(copyBlock('Kurzantwort', e.kurzantwort, false));
    if (e.newsletter && e.newsletter.betreff) {
      var nl = 'Betreff: ' + e.newsletter.betreff + '\n\n' + (e.newsletter.text || '');
      box.appendChild(copyBlock('Newsletter', nl, true));
    }
    if (e.mastodon) {
      box.appendChild(copyBlock('Mastodon', e.mastodon + (e.artikel_url ? '\n' + e.artikel_url : ''), true));
    }
    if (e.pinterest && e.pinterest.titel) {
      var pin = 'Titel: ' + e.pinterest.titel + '\n\nBeschreibung: ' + (e.pinterest.beschreibung || '');
      box.appendChild(copyBlock('Pinterest-Pin', pin, true));
    }
    return box;
  }

  function karteAlsNode(k) {
    var card = el('article', 'karte');
    card.appendChild(kartenKopf(k));
    card.appendChild(insightsBlock(k));
    if (k.status === 'verwertet') card.appendChild(erzeugnisBlock(k));
    var status = el('span', 'status-badge ' + (k.status === 'verwertet' ? 'ok' : ''),
                    k.status === 'verwertet' ? 'verwertet' : 'neu');
    card.appendChild(status);
    return card;
  }

  // ---------- Board-Ansicht ----------
  function zeigeBoard(daten, filter) {
    var spalten = $('#spalten');
    spalten.textContent = '';
    var treffer = daten.karten.filter(function (k) {
      if (filter.status && k.status !== filter.status) return false;
      if (filter.typ && k.typ !== filter.typ) return false;
      if (filter.q) {
        var blob = [k.titel, k.autor, k.winkel, k.artikel_titel,
                    (k.insights || []).join(' ')].join(' ').toLowerCase();
        if (blob.indexOf(filter.q) === -1) return false;
      }
      return true;
    });

    var neue = treffer.filter(function (k) { return k.status !== 'verwertet'; });
    var fertige = treffer.filter(function (k) { return k.status === 'verwertet'; });

    [['Neu auf dem Board (' + neue.length + ')', neue],
     ['Verwertet (' + fertige.length + ')', fertige]].forEach(function (paar) {
      var spalte = el('section', 'spalte');
      spalte.appendChild(el('h2', 'spalten-titel', paar[0]));
      if (!paar[1].length) {
        spalte.appendChild(el('p', 'empty spalte-leer', 'Keine Karten.'));
      } else {
        paar[1].forEach(function (k) { spalte.appendChild(karteAlsNode(k)); });
      }
      spalten.appendChild(spalte);
    });
    $('#leer').hidden = treffer.length > 0;
  }

  function zeigeErzeugnisse(daten) {
    var ziel = $('#erzeugnisse-liste');
    ziel.textContent = '';
    var fertige = daten.karten.filter(function (k) { return k.status === 'verwertet'; });
    if (!fertige.length) {
      ziel.appendChild(el('p', 'empty', 'Noch keine Erzeugnisse. Verwerte zuerst eine Karte: python3 scripts/poppy_repurpose.py --auto'));
      return;
    }
    fertige.forEach(function (k) {
      var s = el('section', 'panel erzeugnis-panel');
      var h = el('h3', '', k.artikel_titel || k.titel);
      s.appendChild(h);
      s.appendChild(erzeugnisBlock(k));
      ziel.appendChild(s);
    });
  }

  function zeigeMetriken(daten) {
    var m = $('#metrics');
    m.textContent = '';
    var zeichen = daten.karten.reduce(function (sum, k) { return sum + (k.inhalt_zeichen || 0); }, 0);
    [[daten.gesamt, 'Karten gesamt', 'Quellen auf dem Board'],
     [daten.neu, 'Neu', 'warten auf Verwertung'],
     [daten.verwertet, 'Verwertet', 'Entwurf + Texte fertig'],
     [zeichen, 'Zeichen Quelltext', 'Transkripte, Artikel, Notizen']].forEach(function (metri) {
      var box = el('div', 'metric');
      box.appendChild(el('span', '', metri[1]));
      box.appendChild(el('strong', '', zahl(metri[0])));
      box.appendChild(el('small', '', metri[2]));
      m.appendChild(box);
    });
    $('#stamp-count').textContent = zahl(daten.gesamt);
    $('#stamp-date').textContent = 'Stand: ' + datumKurz(daten.stand);
    $('#nav-count').textContent = zahl(daten.neu);
    $('#nav-done').textContent = zahl(daten.verwertet);
  }

  // ---------- Navigation (Views) ----------
  function viewUmschalten(name) {
    ['board', 'erzeugnisse', 'ueber'].forEach(function (v) {
      var s = document.getElementById(v);
      if (s) s.hidden = v !== name;
    });
    document.querySelectorAll('nav a[data-view]').forEach(function (a) {
      if (a.dataset.view === name) a.setAttribute('aria-current', 'page');
      else a.removeAttribute('aria-current');
    });
  }

  // ---------- Theme ----------
  function themeInit() {
    var gespeichert = null;
    try { gespeichert = localStorage.getItem('poppy-theme'); } catch (e) { /* privat */ }
    if (gespeichert) document.documentElement.dataset.theme = gespeichert;
    var b = $('#theme');
    if (b) b.addEventListener('click', function () {
      var jetzt = document.documentElement.dataset.theme === 'dark' ||
        (!document.documentElement.dataset.theme &&
         window.matchMedia('(prefers-color-scheme: dark)').matches);
      var neu = jetzt ? 'light' : 'dark';
      document.documentElement.dataset.theme = neu;
      try { localStorage.setItem('poppy-theme', neu); } catch (e) { /* privat */ }
    });
  }

  // ---------- Start ----------
  document.addEventListener('DOMContentLoaded', function () {
    var daten;
    try { daten = ladeDaten(); } catch (e) {
      document.body.innerHTML = '<p class="empty">Board-Daten nicht lesbar – ' +
        'bitte <code>python3 scripts/poppy_board.py</code> ausführen.</p>';
      return;
    }
    var filter = { q: '', typ: '', status: '' };
    themeInit();
    zeigeMetriken(daten);
    zeigeBoard(daten, filter);
    zeigeErzeugnisse(daten);

    var suche = $('#suche');
    suche.addEventListener('input', function () {
      filter.q = suche.value.trim().toLowerCase(); zeigeBoard(daten, filter);
    });
    var ft = $('#filter-typ');
    ft.addEventListener('change', function () { filter.typ = ft.value; zeigeBoard(daten, filter); });
    document.querySelectorAll('#filter-status .chip').forEach(function (chip) {
      chip.addEventListener('click', function () {
        filter.status = chip.dataset.status;
        document.querySelectorAll('#filter-status .chip').forEach(function (c) {
          c.setAttribute('aria-pressed', c === chip ? 'true' : 'false');
        });
        zeigeBoard(daten, filter);
      });
    });
    document.querySelectorAll('nav a[data-view]').forEach(function (a) {
      a.addEventListener('click', function (ev) {
        ev.preventDefault();
        viewUmschalten(a.dataset.view);
      });
    });
    window.addEventListener('hashchange', function () {
      var h = location.hash.replace('#', '');
      if (['board', 'erzeugnisse', 'ueber'].indexOf(h) >= 0) viewUmschalten(h);
    });
    if (['#erzeugnisse', '#ueber'].indexOf(location.hash) >= 0) {
      viewUmschalten(location.hash.replace('#', ''));
    }
  });
})();
