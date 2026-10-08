/*!
 * ff-suche.js – Suchmaske der Site (Pagefind, 08.10.2026)
 * ============================================================
 * Erstkontakt: layouts/shortcodes/suche.html (rendert [data-ff-suche]).
 * Index:       /pagefind/ – im Deploy aus dem fertigen public/-Stand gebaut.
 *
 * DATENSCHUTZ: Die Suche läuft vollständig im Browser. Die Eingabe steht
 * weder in der URL noch in einem Speicher über die Sitzung hinaus. Es gibt
 * keinen Suchdienst, kein Cookie und kein Analytics-Ereignis mit dem Begriff.
 *
 * SICHERHEIT: Treffer werden nie per innerHTML gesetzt. Die Auszüge kommen
 * als HTML-Fragment mit <mark>; sie werden hier zerlegt und als Text über
 * textContent eingesetzt. Verlinkt wird nur gleich-seitiger Pfad (/…).
 *
 * TREFFER: Ein Treffer zählt nur mit sichtbarer, passender Fundstelle oder Titel
 *  (Pagefind liefert sonst Teilstücke wie einzelne Buchstaben).
 * LADEN: Der Index wird erst bei der ersten Eingabe geladen, nicht schon
 * beim Seitenaufruf (Bandbreite, Lighthouse).
 *
 * KEIN ABHÄNGIGKEITS-VERTRAG: Vanilla JS, kein Build, keine CDN-Assets.
 * Tests: tools/ff-suche.test.mjs (node --test, jsdom).
 */
(function () {
  'use strict';

  var MAX_TREFFER = 10;
  var WARTEZEIT_MS = 180;
  var MIN_ZEICHEN = 2;
  var ENTITAETEN = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: '\u00a0' };

  /* Entities auflösen – nur die, die Pagefind erzeugt, plus numerische. */
  function entschluesseln(text) {
    return String(text).replace(/&(#x[0-9a-fA-F]+|#[0-9]+|[a-zA-Z]+);/g, function (treffer, code) {
      if (code.charAt(0) === '#') {
        var zahl = (code.charAt(1) === 'x' || code.charAt(1) === 'X')
          ? parseInt(code.slice(2), 16)
          : parseInt(code.slice(1), 10);
        return (zahl > 0 && zahl <= 0x10ffff) ? String.fromCodePoint(zahl) : treffer;
      }
      var name = code.toLowerCase();
      return Object.prototype.hasOwnProperty.call(ENTITAETEN, name) ? ENTITAETEN[name] : treffer;
    });
  }

  /* Auszug (HTML mit <mark>) → Liste aus { text, markiert }. Fremde Tags fallen weg. */
  function auszugSegmente(auszug) {
    var teile = String(auszug || '').split(/(<\/?mark\b[^>]*>)/i);
    var segmente = [];
    var markiert = false;
    teile.forEach(function (teil) {
      if (!teil) { return; }
      if (/^<mark\b/i.test(teil)) { markiert = true; return; }
      if (/^<\/mark\b/i.test(teil)) { markiert = false; return; }
      var text = entschluesseln(teil.replace(/<[^>]*>/g, ''));
      if (text) { segmente.push({ text: text, markiert: markiert }); }
    });
    return segmente;
  }

  /* Nur gleich-seitige Pfade werden verlinkt – nie javascript:, nie fremde Hosts. */
  function sichereUrl(url) {
    var u = String(url || '');
    return (u.charAt(0) === '/' && u.charAt(1) !== '/' && u.charAt(1) !== '\\') ? u : null;
  }

  /* Vergleichsform: klein, ohne Umlaut-Punkte und ß (Kündigung = kundigung). */
  function normalisieren(text) {
    return String(text || '').toLowerCase().replace(/ß/g, 'ss')
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }

  /* Pagefind bestätigt bei unbekannten Begriffen auch Teilstücke (z. B. das
     einzelne Zeichen „z.“ aus „z.B.“). Ein Treffer zählt deshalb nur, wenn
     eine markierte Fundstelle oder der Titel den Anfang eines Suchworts trägt
     (die ersten fünf Buchstaben). Flexion (Kündigungsfristen) bleibt treffbar. */
  function fundstelleTrifft(d, begriff) {
    var woerter = normalisieren(begriff).split(/\s+/).filter(function (w) { return w.length >= 2; });
    if (!woerter.length) { return false; }
    var quellen = auszugSegmente(d.excerpt || '').filter(function (s) { return s.markiert; })
      .map(function (s) { return s.text; });
    if (d.meta && d.meta.title) { quellen.push(String(d.meta.title)); }
    var texte = quellen.map(normalisieren);
    return woerter.some(function (w) {
      var wurzel = w.slice(0, 5);
      return texte.some(function (t) { return t.indexOf(wurzel) !== -1; });
    });
  }

  /* Zählzeile in ganzen Sätzen – ohne Pluralfehler. */
  function trefferText(anzahl, begriff) {
    if (anzahl === 0) { return 'Keine Treffer für „' + begriff + '“.'; }
    if (anzahl === 1) { return '1 Treffer für „' + begriff + '“.'; }
    return anzahl + ' Treffer für „' + begriff + '“.';
  }

  function ladeModulStandard(pfad) {
    return import(pfad);
  }

  /* Eine Suchmaske an ein Wurzelelement hängen. `ladeModul` ist für Tests
     austauschbar; im Browser lädt es /pagefind/pagefind.js per import(). */
  function ffSucheStarten(root, ladeModul) {
    var form = root.querySelector('[data-ff-suche-form]');
    var eingabe = root.querySelector('[data-ff-suche-eingabe]');
    var status = root.querySelector('[data-ff-suche-status]');
    var liste = root.querySelector('[data-ff-suche-liste]');
    if (!form || !eingabe || !status || !liste) { return null; }

    var pfad = root.getAttribute('data-ff-suche-pfad') || '/pagefind/pagefind.js';
    var indexZusage = null;
    var laufendeNummer = 0;
    var timer = null;

    function index() {
      if (!indexZusage) {
        indexZusage = Promise.resolve(ladeModul(pfad)).then(function (pf) {
          var basis = pfad.replace(/pagefind\.js$/, '');
          var optionen = (typeof pf.options === 'function')
            ? Promise.resolve(pf.options({ basePath: basis }))
            : Promise.resolve();
          return optionen.then(function () {
            return (typeof pf.init === 'function') ? pf.init() : null;
          }).then(function () { return pf; });
        }).catch(function (fehler) {
          indexZusage = null; // beim nächsten Versuch erneut laden
          throw fehler;
        });
      }
      return indexZusage;
    }

    function trefferZeile(d) {
      var li = document.createElement('li');
      li.className = 'ff-suche__treffer';
      var url = sichereUrl(d.url);
      var titel = (d.meta && d.meta.title) ? String(d.meta.title) : String(url || '');
      var kopf = document.createElement(url ? 'a' : 'span');
      kopf.className = 'ff-suche__titel';
      if (url) { kopf.setAttribute('href', url); }
      kopf.textContent = titel;
      li.appendChild(kopf);
      if (d.excerpt) {
        var absatz = document.createElement('p');
        absatz.className = 'ff-suche__auszug';
        auszugSegmente(d.excerpt).forEach(function (s) {
          if (s.markiert) {
            var mark = document.createElement('mark');
            mark.textContent = s.text;
            absatz.appendChild(mark);
          } else {
            absatz.appendChild(document.createTextNode(s.text));
          }
        });
        li.appendChild(absatz);
      }
      return li;
    }

    function zeigeErgebnis(ergebnis, begriff) {
      liste.textContent = '';
      if (ergebnis.gesamt === 0) {
        status.textContent = trefferText(0, begriff) +
          ' Probiere einen allgemeineren Begriff, zum Beispiel Frist oder Rechner.';
        return;
      }
      var hinweis = ergebnis.gesamt > ergebnis.daten.length
        ? ' Die ersten ' + ergebnis.daten.length + ' werden angezeigt.'
        : '';
      status.textContent = trefferText(ergebnis.gesamt, begriff) + hinweis;
      ergebnis.daten.forEach(function (d) { liste.appendChild(trefferZeile(d)); });
    }

    function zeigeFehler() {
      liste.textContent = '';
      status.textContent = 'Die Suche konnte gerade nicht geladen werden. Bitte die Seite neu laden oder Artikel und Werkzeuge über das Menü öffnen.';
    }

    function suche(begriff) {
      var nummer = ++laufendeNummer;
      liste.textContent = '';
      status.textContent = 'Suche läuft …';
      index().then(function (pf) {
        return pf.search(begriff).then(function (antwort) {
          var kandidaten = antwort.results || [];
          return Promise.all(kandidaten.map(function (t) { return t.data(); })).then(function (alle) {
            var echte = alle.filter(function (d) { return fundstelleTrifft(d, begriff); });
            return { gesamt: echte.length, daten: echte.slice(0, MAX_TREFFER) };
          });
        });
      }).then(function (ergebnis) {
        if (nummer !== laufendeNummer) { return; } // veraltete Antwort verwerfen
        zeigeErgebnis(ergebnis, begriff);
      }).catch(function () {
        if (nummer !== laufendeNummer) { return; }
        zeigeFehler();
      });
    }

    function aktualisiere() {
      var begriff = eingabe.value.replace(/\s+/g, ' ').trim();
      if (begriff.length < MIN_ZEICHEN) {
        laufendeNummer++; // laufende Suche verwerfen
        liste.textContent = '';
        status.textContent = begriff ? 'Gib mindestens zwei Zeichen ein.' : '';
        return;
      }
      suche(begriff);
    }

    eingabe.addEventListener('input', function () {
      window.clearTimeout(timer);
      timer = window.setTimeout(aktualisiere, WARTEZEIT_MS);
    });
    form.addEventListener('submit', function (ereignis) {
      ereignis.preventDefault(); // kein GET-Submit: die Eingabe bleibt aus der URL
      window.clearTimeout(timer);
      aktualisiere();
    });

    form.hidden = false; // ohne JavaScript bleibt das Formular verborgen
    return { suche: suche, aktualisiere: aktualisiere };
  }

  function beimLaden() {
    var wurzeln = document.querySelectorAll('[data-ff-suche]');
    Array.prototype.forEach.call(wurzeln, function (wurzel) {
      ffSucheStarten(wurzel, ladeModulStandard);
    });
  }

  var api = {
    entschluesseln: entschluesseln,
    auszugSegmente: auszugSegmente,
    sichereUrl: sichereUrl,
    trefferText: trefferText,
    fundstelleTrifft: fundstelleTrifft,
    normalisieren: normalisieren,
    ffSucheStarten: ffSucheStarten
  };

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', beimLaden);
    } else {
      beimLaden();
    }
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api; // nur für node --test
  }
})();
