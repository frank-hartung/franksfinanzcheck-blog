/*!
 * ff-robust.js – Resilienzschicht der Website (Vertrag C31, 07.10.2026)
 * ============================================================
 * ZWEITE STUFE. Die erste Stufe ist der Bootstrap im <head>
 * (layouts/_partials/extend_head.html): Er sieht jeden Fehler der Seite,
 * auch den der Inline-Skripte, und stellt `FFRobust.hole()` bereit – den
 * Fetch mit Zeitlimit, der nie ein Promise im Regen stehen lässt.
 *
 * Diese Datei ergänzt, was Zeit hat (defer, Fuß des Body):
 *
 *   insel()          Fehlergrenze um jeden interaktiven Baustein. Ein
 *                    Rechner, der beim Initialisieren stirbt, darf nicht
 *                    die sieben anderen mitreißen – und er darf nicht
 *                    stumm bleiben: Der Leser bekommt einen Satz, der
 *                    sagt, was geht und was nicht.
 *   ablage           localStorage/sessionStorage mit Fangnetz. Safari im
 *                    privaten Modus, blockierte Cookies und ein voller
 *                    Speicher werfen – ein Werkzeug, das deshalb nicht
 *                    mehr rechnet, ist ein Ausfall, den niemand sieht.
 *   zwischenablage   Kopieren mit Rückfall auf die alte DOM-Methode und
 *                    ehrlicher Antwort (true/false) statt eines
 *                    abgelehnten Promises in der Konsole.
 *   bericht()        Diagnose für Menschen und Prüfungen: Welche Insel
 *                    lief, welche nicht, welche Fehler fielen an, steht
 *                    der Service Worker, ist die Seite offline.
 *
 * VERTRAG (PRODUCT.md / CLAUDE.md):
 *   · Keine dritte Domain, kein Tracking, kein Cookie, kein Versand der
 *     Fehler nach außen. `bericht()` bleibt im Browser.
 *   · Kein innerHTML, kein eval, kein document.write – jeder Text geht
 *     durch textContent/createElement.
 *   · Vanilla ES5, kein Build, keine Abhängigkeit. Läuft die Datei nicht,
 *     fällt jeder Baustein auf sein eigenes Fangnetz zurück.
 *   · Barrierefrei: Hinweise sind `role="status"` (aria-live polite),
 *     sie nehmen niemandem den Fokus weg.
 *
 * Wache: scripts/robustheits_gate.py · Test: tools/robust.test.mjs
 * Runbook: docs/ANLEITUNG-ROBUSTHEIT.md
 */
(function (global) {
  'use strict';

  var R = global.FFRobust = global.FFRobust || {};
  R.fassung = R.fassung || '1.0.0';
  R.fehler = R.fehler || [];
  R.status = R.status || {};
  R.max = R.max || 25;
  R.zaehler = R.zaehler || 0;

  var dok = global.document || null;
  var wurzel = dok ? dok.documentElement : null;

  /* ---------- Fehlt die erste Stufe, übernimmt diese ----------
     Normalfall: Der Bootstrap im <head> hat die Horcher längst gesetzt.
     Dieser Zweig greift nur, wenn eine Seite ohne ihn ausgeliefert wurde
     (alter Cache, fremde Einbindung) – die Wache soll nie von der
     Ladereihenfolge abhängen. */
  if (!R.boot) {
    R.boot = true;
    R.offline = (global.navigator && 'onLine' in global.navigator)
      ? global.navigator.onLine === false : false;
    R.melden = function (eintrag) {
      try {
        if (!eintrag) return eintrag;
        if (R.fehler.length >= R.max) R.fehler.shift();
        R.fehler.push(eintrag);
        R.zaehler += 1;
      } catch (e) {}
      return eintrag;
    };
    R.sicher = function (fn, rueckfall, quelle) {
      try { return fn(); } catch (fehler) {
        R.melden({ quelle: quelle || 'sicher', text: String((fehler && fehler.message) || fehler || '') });
        return rueckfall;
      }
    };
    if (global.addEventListener) {
      global.addEventListener('error', function (ev) {
        var ziel = ev && ev.target;
        if (ziel && ziel !== global && (ziel.src || ziel.href)) {
          R.melden({ quelle: 'ressource', tag: String(ziel.tagName || ''),
                     text: String(ziel.src || ziel.href || '').slice(0, 200) });
          return;
        }
        R.melden({ quelle: 'skript', text: String((ev && ev.message) || '').slice(0, 200) });
      }, true);
      global.addEventListener('unhandledrejection', function (ev) {
        var grund = ev && ev.reason;
        R.melden({ quelle: 'promise', text: String((grund && grund.message) || grund || '').slice(0, 200) });
      });
    }
  }

  /* ---------- Bereit: DOM-Freigabe mit Fangnetz ---------- */
  R.bereit = function (cb, quelle) {
    if (typeof cb !== 'function') return;
    function laufen() { R.sicher(cb, null, quelle || 'bereit'); }
    if (!dok) { laufen(); return; }
    if (dok.readyState === 'loading') {
      dok.addEventListener('DOMContentLoaded', laufen, { once: true });
    } else {
      laufen();
    }
  };

  /* ---------- Hinweis: sichtbarer Satz statt stummer Lücke ---------- */
  var HINWEIS_TEXT = 'Dieses Bedienelement ist gerade nicht verfügbar. ' +
    'Der Inhalt dieser Seite bleibt vollständig lesbar – bitte lade die Seite neu.';

  R.hinweis = function (text, opts) {
    if (!dok || !dok.createElement) return null;
    opts = opts || {};
    return R.sicher(function () {
      var p = dok.createElement('p');
      p.className = 'ff-robust-hinweis';
      /* role="status" = aria-live polite: Der Satz wird vorgelesen, ohne
         jemandem den Fokus zu stehlen (WCAG 4.1.3). */
      p.setAttribute('role', 'status');
      p.textContent = text || HINWEIS_TEXT;
      if (opts.ziel && opts.ziel.appendChild) opts.ziel.appendChild(p);
      return p;
    }, null, 'hinweis');
  };

  /* ---------- Insel: Fehlergrenze um einen interaktiven Baustein ----------
     `init` läuft im Fangnetz. Schlägt es fehl, wird der Zustand gemerkt,
     der Fehler gemeldet und – wenn ein Ziel angegeben ist – ein Satz
     eingeblendet, der den Rest der Seite freigibt. */
  R.insel = function (name, init, opts) {
    opts = opts || {};
    var schluessel = String(name || 'unbenannt');
    try {
      if (typeof init !== 'function') {
        R.status[schluessel] = 'uebersprungen';
        return null;
      }
      var ergebnis = init();
      R.status[schluessel] = 'ok';
      return ergebnis;
    } catch (fehler) {
      R.status[schluessel] = 'fehler';
      R.melden({ quelle: 'insel:' + schluessel,
                 text: String((fehler && fehler.message) || fehler || '') });
      if (wurzel) {
        R.sicher(function () { wurzel.setAttribute('data-ff-insel-fehler', schluessel); }, null, 'insel-markierung');
      }
      if (opts.text !== false) R.hinweis(opts.text, { ziel: opts.ziel || null });
      return null;
    }
  };

  /* ---------- Ablage: Speicher mit Fangnetz und Gedächtnis-Ersatz ----------
     Drei reale Ausfälle, alle still:
       1. Safari privat / blockierte Cookies → jeder Zugriff wirft.
       2. QuotaExceededError → Schreiben wirft mitten im Speichern.
       3. Kaputtes JSON aus einer älteren Fassung → JSON.parse wirft.
     Hier fällt jeder Fall auf einen Speicher im Tab zurück: Die Seite
     bleibt bedienbar, nur die Erinnerung endet mit dem Tab. */
  var ersatz = {};
  var ersatzAktiv = false;

  function zugriff(art) {
    try {
      var speicher = global[art];
      if (!speicher) return null;
      var probe = '__ff_robust_probe__';
      speicher.setItem(probe, '1');
      speicher.removeItem(probe);
      return speicher;
    } catch (e) {
      return null;
    }
  }

  R.ablage = {
    /** true, wenn dauerhaft gespeichert werden kann (sonst Tab-Ersatz). */
    verfuegbar: function () { return zugriff('localStorage') !== null; },
    /** true, wenn der Speicher im Tab als Ersatz dient – ehrliche Diagnose. */
    ersatz: function () { return ersatzAktiv; },

    lesen: function (schluessel) {
      var speicher = zugriff('localStorage');
      if (speicher) {
        try { return speicher.getItem(schluessel); } catch (e) { /* unten weiter */ }
      }
      ersatzAktiv = true;
      return Object.prototype.hasOwnProperty.call(ersatz, schluessel) ? ersatz[schluessel] : null;
    },

    schreiben: function (schluessel, wert) {
      var speicher = zugriff('localStorage');
      if (speicher) {
        try { speicher.setItem(schluessel, wert); return true; } catch (e) {
          /* QuotaExceededError oder Schreibverbot → Ersatz, kein Abbruch. */
          R.melden({ quelle: 'ablage', text: 'Speichern fehlgeschlagen: ' + schluessel });
        }
      }
      ersatzAktiv = true;
      try { ersatz[schluessel] = wert; return true; } catch (e2) { return false; }
    },

    loeschen: function (schluessel) {
      var speicher = zugriff('localStorage');
      if (speicher) { try { speicher.removeItem(schluessel); } catch (e) {} }
      delete ersatz[schluessel];
    },

    /** JSON lesen, das auch kaputt sein darf – mit geprüftem Rückfall. */
    json: function (schluessel, rueckfall) {
      var roh = R.ablage.lesen(schluessel);
      if (!roh) return rueckfall;
      try {
        var wert = global.JSON ? global.JSON.parse(roh) : null;
        return (wert === null || wert === undefined) ? rueckfall : wert;
      } catch (e) {
        R.melden({ quelle: 'ablage', text: 'JSON unlesbar: ' + schluessel });
        return rueckfall;
      }
    },

    /** JSON schreiben; scheitert es, bleibt die Seite bedienbar. */
    merke: function (schluessel, wert) {
      if (!global.JSON) return false;
      try { return R.ablage.schreiben(schluessel, global.JSON.stringify(wert)); }
      catch (e) { return false; }
    }
  };

  /* ---------- Zwischenablage: zwei Wege, eine ehrliche Antwort ----------
     navigator.clipboard gibt es nur in sicherem Kontext und mit Erlaubnis;
     ein abgelehntes Promise landete bisher als roter Konsoleneintrag und
     zeigte dem Leser „kopiert“, obwohl nichts kopiert war. */
  R.zwischenablage = function (text) {
    var inhalt = String(text == null ? '' : text);
    function altWeg() {
      if (!dok || !dok.createRange || !global.getSelection) return false;
      try {
        var flaeche = dok.createElement('textarea');
        flaeche.value = inhalt;
        flaeche.setAttribute('readonly', '');
        /* Aus dem Sichtfeld, aber nicht `display:none` – sonst nimmt
           keine Auswahl den Inhalt auf. */
        flaeche.style.position = 'fixed';
        flaeche.style.top = '-1000px';
        flaeche.style.opacity = '0';
        dok.body.appendChild(flaeche);
        var bereich = dok.createRange();
        bereich.selectNodeContents(flaeche);
        var auswahl = global.getSelection();
        auswahl.removeAllRanges();
        auswahl.addRange(bereich);
        var ok = dok.execCommand ? dok.execCommand('copy') : false;
        auswahl.removeAllRanges();
        dok.body.removeChild(flaeche);
        return !!ok;
      } catch (e) {
        return false;
      }
    }

    if (global.navigator && global.navigator.clipboard && global.navigator.clipboard.writeText) {
      try {
        return global.navigator.clipboard.writeText(inhalt).then(function () {
          return true;
        }, function () {
          return altWeg();
        });
      } catch (e) { /* synchroner Wurf → alter Weg */ }
    }
    if (typeof global.Promise === 'function') {
      return global.Promise.resolve(altWeg());
    }
    return altWeg();
  };

  /* ---------- Diagnose: was lief, was nicht, was fiel an ----------
     Bewusst ohne Versand. Wer einen Fall melden will, kopiert diese
     Zeilen aus der Konsole – mehr Daten braucht niemand. */
  R.bericht = function () {
    var sw = false;
    try {
      sw = !!(global.navigator && global.navigator.serviceWorker &&
              global.navigator.serviceWorker.controller);
    } catch (e) {}
    return {
      fassung: R.fassung,
      pfad: (global.location && global.location.pathname) || '',
      offline: !!R.offline,
      speicher: R.sicher(function () { return R.ablage.verfuegbar(); }, false, 'bericht'),
      speicherErsatz: ersatzAktiv,
      dienstaktiv: sw,
      inseln: R.status,
      fehlerGesamt: R.zaehler,
      fehlerLetzte: R.fehler.slice(-10)
    };
  };

  R.voll = true;

  /* Prüf-Haken: `node --test tools/robust.test.mjs` lädt diese Datei ohne
     Browser und ruft die Schicht über dieses Feld ab. */
  if (typeof globalThis !== 'undefined') globalThis.FFRobustSchicht = R;
}(typeof window !== 'undefined' ? window : (typeof globalThis !== 'undefined' ? globalThis : this)));
