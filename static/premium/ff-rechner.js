/*!
 * ff-rechner.js – Interaktive Ratgeber-Rechner (H6, 28.09.2026)
 * ============================================================
 * Erstkontakt: layouts/shortcodes/rechner.html (rendert je `typ`
 * ein Formular mit data-ff-rechner, data-typ, Pflichtfeldern mit
 * data-feld und einem Ergebnisbereich data-ff-rechner-ergebnis).
 *
 * DREI TYPEN (Konkurrenz-Parität Finanztip /rechner/, in Franks
 * Kern-Nischen):
 *   notgroschen    – 3–6 Monatsausgaben als Ziel + Sparraten
 *   strom-abschlag – fairer Monatsabschlag aus Verbrauch + Preisen
 *   dsl-effektiv   – Effektivpreis über die Laufzeit inkl. Bonus
 *
 * QUALITÄTS-VERTRAG (CLAUDE.md / PRODUCT.md):
 *   * Kein Tracking, keine Cookies, kein localStorage, kein Netz –
 *     alles rechnet lokal im Browser (100 % lokale Berechnung).
 *   * Keine Frameworks, kein Build. Skript lädt deferred.
 *   * Barrierefrei: echtes <form>, <label>, Enter funktioniert,
 *     Ergebnis landet in aria-live="polite".
 *   * Eingaben: deutsche Notation („1.500" und „37,5" verstehen).
 *   * Ausgaben NIEMALS als innerHTML aus Nutzereingaben – alle Werte
 *     laufen durch Number() und toLocaleString('de-DE').
 *
 * Die Rechenkern LOGIK ist absichtlich DOM-frei und hängt an
 * globalThis.FFRechnerLogik – damit ist sie ohne Browser testbar
 * (Quickcheck: siehe docs/ANLEITUNG-RECHNER.md).
 */
(function () {
  'use strict';

  /* ---------- Zahl-Helfer (deutsche Notation) ---------- */

  function zuZahl(roh) {
    if (typeof roh === 'number') return isFinite(roh) ? roh : NaN;
    var s = String(roh == null ? '' : roh).trim();
    if (!s) return NaN;
    // „1.500" (Tausender) und „37,5" (Komma) verstehen:
    s = s.replace(/\./g, '').replace(',', '.');
    var n = Number(s);
    return isFinite(n) ? n : NaN;
  }

  function euro(n, nachkommastellen) {
    if (!isFinite(n)) return '–';
    var stellen = typeof nachkommastellen === 'number' ? nachkommastellen
      : (Math.abs(n) < 10 ? 2 : 0);
    return n.toLocaleString('de-DE', {
      minimumFractionDigits: stellen, maximumFractionDigits: stellen,
    }) + ' €';
  }

  function zahl(n, suffix) {
    if (!isFinite(n)) return '–';
    return n.toLocaleString('de-DE', { maximumFractionDigits: 2 }) + (suffix || '');
  }

  /* ---------- Rechenkerne (DOM-frei, testbar) ---------- */

  var LOGIK = {

    /** Notgroschen: Ziel = Reserve × notwendige Monatsausgaben, Lücke, Sparraten. */
    notgroschen: function (w) {
      var ausgaben = zuZahl(w.ausgaben);
      var erspartes = zuZahl(w.erspartes);
      var reserve = zuZahl(w.reserve);
      if (!(ausgaben > 0) || !(reserve >= 1)) return null;
      if (!(erspartes >= 0)) erspartes = 0;
      var ziel = reserve * ausgaben;
      var luecke = Math.max(0, ziel - erspartes);
      return {
        ziel: ziel,
        luecke: luecke,
        rate12: luecke / 12,
        rate24: luecke / 24,
        fertig: luecke <= 0,
      };
    },

    /** 50-30-20-Budget: 50 % Grundbedürfnisse, 30 % Wünsche, 20 % Sparen/Puffer. */
    'budget-503020': function (w) {
      var netto = zuZahl(w.netto);
      var fixkosten = zuZahl(w.fixkosten);
      if (!(netto > 0)) return null;
      var fixSoll = netto * 0.50;
      var wunschSoll = netto * 0.30;
      var sparSoll = netto * 0.20;
      var fixQuote = null;
      var fixDifferenz = null;
      var hinweis = '';
      var ampel = 'passend';
      if (isFinite(fixkosten) && fixkosten > 0) {
        fixQuote = (fixkosten / netto) * 100;
        fixDifferenz = fixkosten - fixSoll;
        if (fixQuote > 55) {
          ampel = 'nachzahlung';
          hinweis = 'Deine Fixkosten liegen bei ' + zahl(fixQuote) + ' % deines Nettoeinkommens (Empfehlung: max. 50 %). ' +
            'Das bedeutet ' + euro(fixDifferenz) + ' pro Monat über dem Richtwert – durch Fixkosten-Optimierung kannst du diesen Betrag für Freizeit oder Notgroschen freisetzen.';
        } else if (fixQuote <= 50) {
          ampel = 'gut';
          hinweis = 'Hervorragend: Deine Fixkosten liegen bei sparsamen ' + zahl(fixQuote) + ' % deines Einkommens. Du hast vollen Spielraum für Lebensqualität und Vermögensaufbau.';
        } else {
          hinweis = 'Deine Fixkosten liegen mit ' + zahl(fixQuote) + ' % leicht über der 50-%-Marke, aber im soliden Korridor.';
        }
      }
      return {
        fixSoll: fixSoll,
        wunschSoll: wunschSoll,
        sparSoll: sparSoll,
        fixQuote: fixQuote,
        fixDifferenz: fixDifferenz,
        hinweis: hinweis,
        ampel: ampel,
      };
    },

    /** Strom-Abschlag: fairer Monatsabschlag + Nachzahlungswarnung. */
    'strom-abschlag': function (w) {
      var verbrauch = zuZahl(w.verbrauch);
      var preis = zuZahl(w.preis);
      var grundpreis = zuZahl(w.grundpreis);
      var aktuell = zuZahl(w.aktuell);
      if (!(verbrauch > 0) || !(preis > 0) || !(grundpreis >= 0)) return null;
      var jahreskosten = (verbrauch * preis) / 100 + grundpreis * 12;
      var fair = jahreskosten / 12;
      var ampel = 'passend';
      var hinweis = '';
      if (isFinite(aktuell) && aktuell > 0) {
        if (aktuell < fair * 0.85) {
          ampel = 'nachzahlung';
          hinweis = 'Dein Abschlag liegt über 15 % unter dem fairen Betrag – ' +
            'das ist ein klassisches Nachzahlungsrisiko (Nachzahlung ≈ ' +
            euro((fair - aktuell) * 12) + ' pro Jahr).';
        } else if (aktuell > fair * 1.15) {
          ampel = 'zu-hoch';
          hinweis = 'Dein Abschlag liegt über 15 % über dem fairen Betrag – ' +
            'du leihst deinem Versorger ≈ ' + euro((aktuell - fair) * 12) +
            ' pro Jahr zinslos.';
        } else {
          hinweis = 'Dein Abschlag passt – Abweichung unter 15 % ist normal.';
        }
      }
      return { jahreskosten: jahreskosten, fair: fair, ampel: ampel, hinweis: hinweis };
    },

    /** Gas-Abschlag: fairer Monatsabschlag + Nachzahlungswarnung für Gas. */
    'gas-abschlag': function (w) {
      var verbrauch = zuZahl(w.verbrauch);
      var preis = zuZahl(w.preis);
      var grundpreis = zuZahl(w.grundpreis);
      var aktuell = zuZahl(w.aktuell);
      if (!(verbrauch > 0) || !(preis > 0) || !(grundpreis >= 0)) return null;
      var jahreskosten = (verbrauch * preis) / 100 + grundpreis * 12;
      var fair = jahreskosten / 12;
      var ampel = 'passend';
      var hinweis = '';
      if (isFinite(aktuell) && aktuell > 0) {
        if (aktuell < fair * 0.85) {
          ampel = 'nachzahlung';
          hinweis = 'Dein Gasabschlag liegt über 15 % unter dem fairen Betrag – ' +
            'das ist ein klassisches Nachzahlungsrisiko (Nachzahlung ≈ ' +
            euro((fair - aktuell) * 12) + ' pro Jahr nach der Heizperiode).';
        } else if (aktuell > fair * 1.15) {
          ampel = 'zu-hoch';
          hinweis = 'Dein Gasabschlag liegt über 15 % über dem fairen Betrag – ' +
            'du leihst deinem Gasversorger ≈ ' + euro((aktuell - fair) * 12) +
            ' pro Jahr zinslos.';
        } else {
          hinweis = 'Dein Gasabschlag passt gut zum angegebenen Verbrauch und Preis.';
        }
      }
      return { jahreskosten: jahreskosten, fair: fair, ampel: ampel, hinweis: hinweis };
    },

    /** DSL-Effektivpreis: (Grundgebühr × Laufzeit − Bonus + Kosten) ÷ Laufzeit. */
    'dsl-effektiv': function (w) {
      var grundgebuehr = zuZahl(w.grundgebuehr);
      var laufzeit = zuZahl(w.laufzeit);
      var bonus = zuZahl(w.bonus);
      var kosten = zuZahl(w.kosten);
      var aktuell = zuZahl(w.aktuell);
      if (!(grundgebuehr > 0) || !(laufzeit >= 1)) return null;
      if (!(bonus >= 0)) bonus = 0;
      if (!(kosten >= 0)) kosten = 0;
      var summe = grundgebuehr * laufzeit - bonus + kosten;
      var effektiv = summe / laufzeit;
      var ersparnis = null;
      if (isFinite(aktuell) && aktuell > 0) {
        ersparnis = (aktuell - effektiv) * laufzeit;
      }
      return {
        summe: summe,
        effektiv: effektiv,
        ersparnis: ersparnis,
        gut: bonus > 0 && bonus <= grundgebuehr * laufzeit * 0.5,
      };
    },
  };

  /* ---------- DOM-Bindung ---------- */

  function werteLesen(container) {
    var w = {};
    container.querySelectorAll('[data-feld]').forEach(function (el) {
      w[el.getAttribute('data-feld')] = el.value;
    });
    return w;
  }

  function zeile(label, wert, stark) {
    var z = document.createElement('div');
    z.className = 'ff-rechner__zeile' + (stark ? ' ff-rechner__zeile--stark' : '');
    var l = document.createElement('span');
    l.className = 'ff-rechner__label';
    l.textContent = label;
    var v = document.createElement('span');
    v.className = 'ff-rechner__wert';
    v.textContent = wert;
    z.appendChild(l); z.appendChild(v);
    return z;
  }

  function rendere(typ, erg, container) {
    var ziel = container.querySelector('[data-ff-rechner-ergebnis]');
    if (!ziel) return;
    ziel.textContent = '';
    if (!erg) {
      var hinweis = document.createElement('p');
      hinweis.className = 'ff-rechner__leer';
      hinweis.textContent = 'Bitte fülle die fett markierten Felder aus – dann rechnet der Rechner sofort.';
      ziel.appendChild(hinweis);
      return;
    }
    if (typ === 'notgroschen') {
      var reserveAnzeige = zuZahl(werteLesen(container).reserve);
      ziel.appendChild(zeile('Dein Notgroschen-Ziel (' + zahl(reserveAnzeige) + ' Monatsausgaben)', euro(erg.ziel), true));
      if (erg.fertig) {
        var glueck = document.createElement('p');
        glueck.className = 'ff-rechner__hinweis ff-rechner__hinweis--gut';
        glueck.textContent = '🎉 Ziel bereits erreicht – dein Notgroschen ist komplett. Übrigens: Alles über dem Ziel kannst du höher verzinst anlegen (z. B. Tagesgeld).';
        ziel.appendChild(glueck);
      } else {
        ziel.appendChild(zeile('Noch fehlen', euro(erg.luecke)));
        ziel.appendChild(zeile('Sparrate für 12 Monate', euro(erg.rate12, 2)));
        ziel.appendChild(zeile('Sparrate für 24 Monate', euro(erg.rate24, 2)));
      }
    } else if (typ === 'budget-503020') {
      ziel.appendChild(zeile('50 % für Grundbedürfnisse & Fixkosten (Soll)', euro(erg.fixSoll), true));
      ziel.appendChild(zeile('30 % für Wünsche & Freizeit (Soll)', euro(erg.wunschSoll), true));
      ziel.appendChild(zeile('20 % für Notgroschen & Sparen (Soll)', euro(erg.sparSoll), true));
      if (erg.fixQuote !== null) {
        ziel.appendChild(zeile('Deine aktuelle Fixkostenquote', zahl(erg.fixQuote) + ' %'));
      }
      if (erg.hinweis) {
        var pBudget = document.createElement('p');
        pBudget.className = 'ff-rechner__hinweis ff-rechner__hinweis--' + erg.ampel;
        pBudget.textContent = erg.hinweis;
        ziel.appendChild(pBudget);
      }
    } else if (typ === 'strom-abschlag') {
      ziel.appendChild(zeile('Voraussichtliche Jahreskosten Strom', euro(erg.jahreskosten), true));
      ziel.appendChild(zeile('Fairer Monatsabschlag Strom', euro(erg.fair, 2), true));
      if (erg.hinweis) {
        var p = document.createElement('p');
        p.className = 'ff-rechner__hinweis ff-rechner__hinweis--' + erg.ampel;
        p.textContent = erg.hinweis;
        ziel.appendChild(p);
      }
    } else if (typ === 'gas-abschlag') {
      ziel.appendChild(zeile('Voraussichtliche Jahreskosten Gas', euro(erg.jahreskosten), true));
      ziel.appendChild(zeile('Fairer Monatsabschlag Gas', euro(erg.fair, 2), true));
      if (erg.hinweis) {
        var pGas = document.createElement('p');
        pGas.className = 'ff-rechner__hinweis ff-rechner__hinweis--' + erg.ampel;
        pGas.textContent = erg.hinweis;
        ziel.appendChild(pGas);
      }
    } else if (typ === 'dsl-effektiv') {
      ziel.appendChild(zeile('Gesamtkosten über die Laufzeit', euro(erg.summe)));
      ziel.appendChild(zeile('Echter Effektivpreis pro Monat', euro(erg.effektiv, 2), true));
      if (erg.ersparnis !== null) {
        ziel.appendChild(zeile(erg.ersparnis >= 0 ? 'Ersparnis über die Laufzeit' : 'Mehrkosten über die Laufzeit', euro(Math.abs(erg.ersparnis))));
      }
      if (!erg.gut) {
        var warn = document.createElement('p');
        warn.className = 'ff-rechner__hinweis ff-rechner__hinweis--achtung';
        warn.textContent = 'Achtung Rabattfalle: Ein Bonus über der Hälfte der Laufzeitkosten (oder ohne Bonus gerechnet) verändert den Effektivpreis stark – prüfe auch Grundgebühr nach dem Aktionszeitraum.';
        if (zuZahl(werteLesen(container).bonus) > 0 && !erg.gut) {
          warn.textContent = 'Achtung Rabattfalle: Der Bonus ist ungewöhnlich hoch (über 50 % der Laufzeitkosten) – solche Angebote ändern oft nach dem ersten Jahr die Grundgebühr. Rechne sicherheitshalber mit der regulären Grundgebühr.';
        }
        ziel.appendChild(warn);
      }
    }
  }

  function initialisiere() {
    document.querySelectorAll('[data-ff-rechner]').forEach(function (container) {
      var typ = container.getAttribute('data-typ');
      var logik = LOGIK[typ];
      if (!logik) return;
      var form = container.querySelector('form');
      if (!form) return;
      var rechnen = function () { rendere(typ, logik(werteLesen(container)), container); };
      form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        rechnen();
      });
      form.querySelectorAll('input, select').forEach(function (el) {
        el.addEventListener('change', rechnen);
      });
      // Slider-Wert live daneben zeigen
      var slider = container.querySelector('[data-feld="reserve"]');
      if (slider) {
        var anzeige = container.querySelector('[data-ff-rechner-slider-wert]');
        var sync = function () { if (anzeige) anzeige.textContent = slider.value + '×'; };
        slider.addEventListener('input', sync);
        sync();
      }
      rechnen(); // Anfangszustand (meist „Bitte ausfüllen")
    });
  }

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', initialisiere);
    } else {
      initialisiere();
    }
  }

  /* ---------- Export für Tests (kein Browser nötig) ---------- */
  if (typeof globalThis !== 'undefined') {
    globalThis.FFRechnerLogik = LOGIK;
    globalThis.FFRechnerHelfer = { zuZahl: zuZahl, euro: euro };
  }
})();
