/*!
 * ff-werkzeuge.js – Franks Werkzeuge (eigenständige Finanz-Rechner)
 * =================================================================
 * PRODUKTVERTRAG (Quelle: data/werkzeuge.yaml, Wache: scripts/werkzeuge_gate.py)
 *
 *   1. LOKAL.      Kein fetch, kein XMLHttpRequest, kein sendBeacon, kein
 *                  WebSocket, kein Formularziel. Jede Rechnung, jeder Export
 *                  entsteht in diesem Browser. Es gibt keine Stelle in dieser
 *                  Datei, die Eingaben irgendwohin schickt.
 *   2. OHNE DATEN. Es werden keine personenbezogenen Daten erhoben, erzeugt
 *                  oder benötigt. Die Werkzeuge kennen Beträge und Termine.
 *   3. OPT-IN.     localStorage ausschließlich nach aktivem Häkchen. Häkchen
 *                  entfernen oder „Zurücksetzen" löscht den Eintrag sofort.
 *   4. OHNE KLICK. Kein Ergebnis, keine Zeile und kein Export hängt an einem
 *                  Affiliate-Link. Diese Datei kennt keine Partner-URL.
 *   5. TEXT STATT HTML. Nutzereingaben gehen nie durch innerHTML; jede
 *                  Ausgabe entsteht über textContent/createElement.
 *   6. TESTBAR.    Der Rechenkern hängt unter globalThis.FFWerkzeuge.logik
 *                  und läuft ohne Browser (tools/werkzeuge.test.mjs).
 *
 * Die Feld-Metadaten (Label, Typ, Korridor, Gruppe) stehen NICHT hier,
 * sondern kommen aus dem gerenderten Markup (data-*). Damit gibt es genau
 * eine Quelle – die YAML – und keine zweite Kopie im Skript.
 */
(function () {
  'use strict';

  var SPEICHER_PRAEFIX = 'ff_werkzeug_';
  var SPEICHER_VERSION = '_v1';
  var MAX_BETRAG = 10000000;
  var AUFWANDSGRENZE = 60;        // € pro Jahr – Entscheidungsbaum, Regel 3
  var MAX_MONATE = 600;           // Abbruch der Notgroschen-Fortschreibung

  // =================================================================
  // 1. ZAHLEN, GELD, DATUM
  // =================================================================

  /** Deutsche Eingabe („1.234,56", „1 234,56 €") zu Number. NaN = unbrauchbar. */
  function zahl(roh) {
    if (typeof roh === 'number') return isFinite(roh) ? roh : NaN;
    var text = String(roh == null ? '' : roh).trim()
      .replace(/\s/g, '')
      .replace(/\u00a0/g, '')
      .replace(/€|%/g, '');
    if (!text) return NaN;
    if (text.indexOf(',') !== -1) {
      text = text.replace(/\./g, '').replace(',', '.');
    } else if (/^-?\d{1,3}(\.\d{3})+$/.test(text)) {
      text = text.replace(/\./g, '');
    }
    var wert = Number(text);
    if (!isFinite(wert)) return NaN;
    if (Math.abs(wert) > MAX_BETRAG) return NaN;
    return wert;
  }

  function euro(wert, stellen) {
    if (!isFinite(wert)) return '–';
    var n = typeof stellen === 'number' ? stellen : 2;
    return wert.toLocaleString('de-DE', {
      style: 'currency', currency: 'EUR',
      minimumFractionDigits: n, maximumFractionDigits: n
    });
  }

  function nummer(wert, stellen) {
    if (!isFinite(wert)) return '–';
    var n = typeof stellen === 'number' ? stellen : 0;
    return wert.toLocaleString('de-DE', {
      minimumFractionDigits: n, maximumFractionDigits: n
    });
  }

  function prozent(wert, stellen) {
    if (!isFinite(wert)) return '–';
    return nummer(wert, typeof stellen === 'number' ? stellen : 1) + ' %';
  }

  function datumLesen(wert) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(String(wert || ''))) return null;
    var teile = String(wert).split('-').map(Number);
    var d = new Date(teile[0], teile[1] - 1, teile[2], 12, 0, 0, 0);
    if (d.getFullYear() !== teile[0] || d.getMonth() !== teile[1] - 1 || d.getDate() !== teile[2]) return null;
    return d;
  }

  function heuteMittag(jetzt) {
    var z = jetzt && typeof jetzt === 'object' && typeof jetzt.getTime === 'function'
      ? new Date(jetzt.getTime()) : new Date();
    return new Date(z.getFullYear(), z.getMonth(), z.getDate(), 12, 0, 0, 0);
  }

  function datumFormat(d) {
    if (!d) return '–';
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
  }

  function iso(d) {
    if (!d) return '';
    var m = String(d.getMonth() + 1), t = String(d.getDate());
    return d.getFullYear() + '-' + (m.length < 2 ? '0' + m : m) + '-' + (t.length < 2 ? '0' + t : t);
  }

  function tagePlus(d, n) {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n, 12, 0, 0, 0);
  }

  /** Monate addieren/abziehen mit kalendarischer Kappung (31.05. − 3 Monate = 28.02.). */
  function monatePlus(d, n) {
    var tag = d.getDate();
    var ziel = new Date(d.getFullYear(), d.getMonth() + n, 1, 12, 0, 0, 0);
    var letzter = new Date(ziel.getFullYear(), ziel.getMonth() + 1, 0, 12, 0, 0, 0).getDate();
    ziel.setDate(Math.min(tag, letzter));
    return ziel;
  }

  function tageDifferenz(a, b) {
    return Math.round((a.getTime() - b.getTime()) / 86400000);
  }

  function dauerText(monate) {
    if (!isFinite(monate) || monate < 0) return '–';
    if (monate === 0) return 'erreicht';
    var jahre = Math.floor(monate / 12), rest = monate % 12;
    if (jahre === 0) return monate + (monate === 1 ? ' Monat' : ' Monate');
    if (rest === 0) return jahre + (jahre === 1 ? ' Jahr' : ' Jahre');
    return jahre + (jahre === 1 ? ' Jahr' : ' Jahre') + ' und ' + rest + (rest === 1 ? ' Monat' : ' Monate');
  }

  // =================================================================
  // 2. FELD-ZUGRIFF
  // =================================================================

  function feld(felder, id) {
    for (var i = 0; i < felder.length; i++) {
      if (felder[i].id === id) return felder[i];
    }
    return null;
  }

  function wertVon(felder, id) {
    var f = feld(felder, id);
    return f ? f.zahl : NaN;
  }

  function wertOder(felder, id, ersatz) {
    var w = wertVon(felder, id);
    return isFinite(w) ? w : ersatz;
  }

  function auswahl(felder, id) {
    var f = feld(felder, id);
    return f ? String(f.wert || '') : '';
  }

  function auswahlZahl(felder, id, ersatz) {
    var f = feld(felder, id);
    return f && isFinite(f.auswahlZahl) ? f.auswahlZahl : ersatz;
  }

  function auswahlLabel(felder, id) {
    var f = feld(felder, id);
    return f && f.auswahlLabel ? f.auswahlLabel : '';
  }

  function kennzahl(label, wert, stark) {
    return { label: label, wert: wert, stark: !!stark };
  }

  function hinweis(art, text) {
    return { art: art, text: text };
  }

  function fehlt(liste) {
    return { fehler: liste.slice() };
  }

  /** Pflichtfelder prüfen; liefert null (alles da) oder ein Fehlerobjekt. */
  function pflicht(felder, ids) {
    var offen = [];
    for (var i = 0; i < ids.length; i++) {
      var f = feld(felder, ids[i]);
      if (!f) { offen.push(ids[i]); continue; }
      if (f.typ === 'datum') {
        if (!datumLesen(f.wert)) offen.push(f.label || f.id);
      } else if (f.typ === 'auswahl') {
        if (!f.wert) offen.push(f.label || f.id);
      } else if (!isFinite(f.zahl)) {
        offen.push(f.label || f.id);
      }
    }
    return offen.length ? fehlt(offen) : null;
  }

  // =================================================================
  // 3. RECHENKERN – ein Werkzeug, eine reine Funktion
  // =================================================================

  var logik = {};

  // ---------------------------------------------------------------- Scanner
  logik.scanner = function (felder) {
    var posten = [];
    var summe = 0;
    for (var i = 0; i < felder.length; i++) {
      var f = felder[i];
      if (f.id === 'einkommen') continue;
      if (!isFinite(f.zahl) || f.zahl <= 0) continue;
      posten.push(f);
      summe += f.zahl;
    }
    if (!posten.length) {
      return fehlt(['mindestens einen laufenden Posten']);
    }
    var einkommen = wertOder(felder, 'einkommen', 0);
    var jahr = summe * 12;
    var quote = einkommen > 0 ? (summe / einkommen) * 100 : NaN;

    posten.sort(function (a, b) { return b.zahl - a.zahl; });

    var potenzialMin = 0, potenzialMax = 0;
    var liste = posten.map(function (f) {
      var k = f.korridor || [0, 0];
      var min = f.zahl * 12 * k[0];
      var max = f.zahl * 12 * k[1];
      potenzialMin += min;
      potenzialMax += max;
      return {
        label: f.label,
        wert: euro(f.zahl),
        anteil: summe > 0 ? (f.zahl / summe) * 100 : 0,
        zusatz: max > 0
          ? 'Spielraum ' + euro(min, 0) + ' bis ' + euro(max, 0) + ' im Jahr'
          : 'Kein Tarifhebel – nur durch eine andere Entscheidung veränderbar'
      };
    });

    var kennzahlen = [
      kennzahl('Laufende Kosten', euro(summe) + ' pro Monat', true),
      kennzahl('Hochgerechnet', euro(jahr, 0) + ' pro Jahr', false),
      kennzahl('Rechnerischer Spielraum', euro(potenzialMin, 0) + ' bis ' + euro(potenzialMax, 0) + ' pro Jahr', false)
    ];
    if (isFinite(quote)) {
      kennzahlen.splice(2, 0, kennzahl('Fixkostenquote', prozent(quote), false));
    }

    var hinweise = [];
    if (posten.length < 3) {
      hinweise.push(hinweis('info', 'Erst ab drei erfassten Bereichen zeigt die Reihenfolge ein belastbares Bild. Ergänze die fehlenden Posten aus deinem Kontoauszug.'));
    }
    if (isFinite(quote)) {
      if (quote >= 60) {
        hinweise.push(hinweis('achtung', 'Deine Fixkostenquote liegt bei ' + prozent(quote) + '. Ab etwa 60 Prozent bleibt kaum Spielraum für Rücklagen – die beiden größten Posten verdienen zuerst eine vollständige Rechnung.'));
      } else if (quote >= 50) {
        hinweise.push(hinweis('warnung', 'Mit ' + prozent(quote) + ' liegen deine Fixkosten im oberen Bereich. Das ist kein Alarm, aber ein Grund, den größten Posten jährlich zu prüfen.'));
      } else {
        hinweise.push(hinweis('gut', 'Mit ' + prozent(quote) + ' bleibt dir Luft für Rücklagen. Prüfe trotzdem den größten Posten – gerade dort fallen Erhöhungen lange nicht auf.'));
      }
    }
    var top = liste[0];
    hinweise.push(hinweis('info', 'Starte bei „' + top.label + '". Dieser Posten trägt ' + prozent(top.anteil, 0) + ' deiner laufenden Kosten – nicht weil er zu hoch ist, sondern weil dort jede Veränderung am stärksten wirkt.'));
    hinweise.push(hinweis('info', 'Der Spielraum ist ein Erfahrungsrahmen aus Tarifvergleichen, keine Zusage. Was davon bei dir ankommt, zeigt erst die Rechnung im jeweiligen Werkzeug.'));

    return {
      kennzahlen: kennzahlen,
      liste: liste,
      listeTitel: 'Prüfreihenfolge nach Betrag',
      zeilen: [
        { label: 'Erfasste Bereiche', wert: nummer(posten.length) },
        { label: 'Größter Posten', wert: top.label + ' (' + top.wert + ')' },
        { label: 'Spielraum untere Grenze', wert: euro(potenzialMin, 0) + ' pro Jahr' },
        { label: 'Spielraum obere Grenze', wert: euro(potenzialMax, 0) + ' pro Jahr' }
      ],
      hinweise: hinweise
    };
  };

  // --------------------------------------------------------- Effektivpreis
  logik.effektivpreis = function (felder) {
    var fehler = pflicht(felder, ['laufzeit', 'aktionspreis', 'normalpreis']);
    if (fehler) return fehler;

    var laufzeit = Math.round(wertVon(felder, 'laufzeit'));
    if (!(laufzeit > 0)) return fehlt(['eine Laufzeit größer als null']);
    if (laufzeit > 120) laufzeit = 120;

    var aktionspreis = wertVon(felder, 'aktionspreis');
    var normalpreis = wertVon(felder, 'normalpreis');
    var hardware = wertOder(felder, 'hardware', 0);
    var einmal = wertOder(felder, 'einmalkosten', 0);
    var bonus = wertOder(felder, 'bonus', 0);
    var vergleich = wertVon(felder, 'vergleichspreis');

    var aktionsmonate = Math.round(wertOder(felder, 'aktionsmonate', 0));
    var gekappt = false;
    if (!(aktionsmonate >= 0)) aktionsmonate = 0;
    if (aktionsmonate > laufzeit) { aktionsmonate = laufzeit; gekappt = true; }

    var restmonate = laufzeit - aktionsmonate;
    var grundkosten = aktionspreis * aktionsmonate + normalpreis * restmonate;
    var zusatz = hardware * laufzeit;
    var gesamt = grundkosten + zusatz + einmal - bonus;
    var effektiv = gesamt / laufzeit;
    var nachAktion = normalpreis + hardware;
    var sprung = nachAktion - effektiv;

    var kennzahlen = [
      kennzahl('Effektivpreis', euro(effektiv) + ' pro Monat', true),
      kennzahl('Gesamtkosten über ' + laufzeit + ' Monate', euro(gesamt), false),
      kennzahl('Preis nach der Aktion', euro(nachAktion) + ' pro Monat', false)
    ];

    var zeilen = [
      { label: 'Aktionsphase', wert: aktionsmonate + ' × ' + euro(aktionspreis) + ' = ' + euro(aktionspreis * aktionsmonate) },
      { label: 'Reguläre Phase', wert: restmonate + ' × ' + euro(normalpreis) + ' = ' + euro(normalpreis * restmonate) }
    ];
    if (hardware > 0) zeilen.push({ label: 'Zusatz je Monat', wert: laufzeit + ' × ' + euro(hardware) + ' = ' + euro(zusatz) });
    if (einmal > 0) zeilen.push({ label: 'Einmalkosten', wert: '+ ' + euro(einmal) });
    if (bonus > 0) zeilen.push({ label: 'Bonus', wert: '− ' + euro(bonus) });
    zeilen.push({ label: 'Summe über die Laufzeit', wert: euro(gesamt) });

    var hinweise = [];
    if (gekappt) {
      hinweise.push(hinweis('warnung', 'Die Aktionsphase war länger als die Laufzeit und wurde auf ' + laufzeit + ' Monate begrenzt. Prüfe beide Angaben im Tarifblatt.'));
    }
    if (isFinite(vergleich) && vergleich > 0) {
      var diff = vergleich - effektiv;
      var jahr = diff * 12;
      kennzahlen.push(kennzahl('Unterschied zu heute', (diff >= 0 ? '− ' : '+ ') + euro(Math.abs(jahr), 0) + ' pro Jahr', false));
      zeilen.push({ label: 'Dein heutiger Preis', wert: euro(vergleich) + ' pro Monat' });
      zeilen.push({
        label: diff >= 0 ? 'Ersparnis über die Laufzeit' : 'Mehrkosten über die Laufzeit',
        wert: euro(Math.abs(diff * laufzeit))
      });
      if (diff <= 0) {
        hinweise.push(hinweis('achtung', 'Der neue Tarif ist über die volle Laufzeit teurer als dein heutiger Preis. Der beworbene Einstiegspreis täuscht hier über die Gesamtrechnung hinweg.'));
      } else if (jahr < AUFWANDSGRENZE) {
        hinweise.push(hinweis('warnung', 'Die Ersparnis liegt bei ' + euro(jahr, 0) + ' im Jahr. Das trägt den Aufwand eines Wechsels erfahrungsgemäß nicht – es sei denn, du verbesserst zusätzlich Leistung oder Laufzeit.'));
      } else {
        hinweise.push(hinweis('gut', 'Über die volle Laufzeit sparst du ' + euro(diff * laufzeit) + '. Diese Zahl ist belastbar, weil sie Bonus, Aktionsphase und Einmalkosten enthält.'));
      }
    }
    if (bonus > 0 && gesamt > 0 && bonus / (grundkosten + zusatz + einmal) >= 0.15) {
      hinweise.push(hinweis('warnung', 'Rund ' + prozent(bonus / (grundkosten + zusatz + einmal) * 100, 0) + ' des günstigen Schnitts stammen aus dem Bonus. Er wirkt genau einmal – ab dem zweiten Jahr zählt der reguläre Preis.'));
    }
    if (sprung > 0.5 && aktionsmonate > 0) {
      hinweise.push(hinweis('info', 'Ab Monat ' + (aktionsmonate + 1) + ' zahlst du ' + euro(nachAktion) + ' statt ' + euro(effektiv) + '. Trag dir diesen Monat als nächsten Prüftermin ein, nicht erst das Vertragsende.'));
    }

    return {
      kennzahlen: kennzahlen,
      zeilen: zeilen,
      hinweise: hinweise
    };
  };

  // ----------------------------------------------------------- Energie
  logik.energie = function (felder) {
    var fehler = pflicht(felder, ['verbrauch', 'arbeitspreis', 'grundpreis']);
    if (fehler) return fehler;

    var medium = auswahl(felder, 'medium') || 'strom';
    var verbrauch = wertVon(felder, 'verbrauch');
    var arbeitspreis = wertVon(felder, 'arbeitspreis');
    var grundpreis = wertVon(felder, 'grundpreis');
    var abschlag = wertOder(felder, 'abschlag', 0);
    var monate = Math.round(wertOder(felder, 'monate', 0));
    if (!(monate >= 0)) monate = 0;
    if (monate > 12) monate = 12;

    var verbrauchskosten = verbrauch * arbeitspreis / 100;
    var grundkosten = grundpreis * 12;
    var jahr = verbrauchskosten + grundkosten;
    var fair = jahr / 12;
    var delta = (fair - abschlag) * 12;
    var aufgelaufen = (fair - abschlag) * monate;
    var grundanteil = jahr > 0 ? (grundkosten / jahr) * 100 : NaN;

    var kennzahlen = [
      kennzahl('Fairer Monatsabschlag', euro(fair), true),
      kennzahl('Jahreskosten', euro(jahr, 0), false)
    ];

    var zeilen = [
      { label: 'Verbrauchskosten', wert: nummer(verbrauch) + ' kWh × ' + nummer(arbeitspreis, 2) + ' ct = ' + euro(verbrauchskosten, 0) },
      { label: 'Grundpreis im Jahr', wert: '12 × ' + euro(grundpreis) + ' = ' + euro(grundkosten) },
      { label: 'Anteil Grundpreis', wert: prozent(grundanteil) },
      { label: 'Jahreskosten gesamt', wert: euro(jahr) }
    ];

    var hinweise = [];
    if (abschlag > 0) {
      var abweichung = (abschlag - fair) / fair;
      kennzahlen.push(kennzahl(
        delta > 0 ? 'Erwartete Nachzahlung' : 'Erwartetes Guthaben',
        euro(Math.abs(delta), 0) + ' im Jahr', false
      ));
      zeilen.push({ label: 'Dein Abschlag', wert: euro(abschlag) + ' pro Monat' });
      zeilen.push({ label: 'Differenz je Monat', wert: euro(Math.abs(fair - abschlag)) + (delta > 0 ? ' zu wenig' : ' zu viel') });
      if (monate > 0) {
        zeilen.push({
          label: 'Bereits aufgelaufen nach ' + monate + ' Monaten',
          wert: euro(Math.abs(aufgelaufen), 0) + (aufgelaufen > 0 ? ' Nachzahlung' : ' Guthaben')
        });
      }
      if (abweichung < -0.1) {
        hinweise.push(hinweis('nachzahlung', 'Dein Abschlag liegt ' + prozent(Math.abs(abweichung) * 100, 0) + ' unter dem rechnerisch fairen Wert. Bei gleichem Verbrauch läuft eine Nachzahlung von rund ' + euro(delta, 0) + ' auf. Erhöhe den Abschlag jetzt freiwillig – das verteilt denselben Betrag auf zwölf Monate statt auf einen.'));
      } else if (abweichung > 0.15) {
        hinweise.push(hinweis('warnung', 'Du zahlst ' + prozent(abweichung * 100, 0) + ' mehr als nötig. Das Geld liegt bis zur Jahresabrechnung zinslos beim Versorger. Eine Anpassung nach unten ist ohne Begründung möglich, solange die Rechnung trägt.'));
      } else {
        hinweise.push(hinweis('gut', 'Dein Abschlag passt zur Rechnung: Die Abweichung bleibt unter zehn Prozent. Prüfe ihn erneut nach jeder Preisanpassung und nach jeder Jahresabrechnung.'));
      }
    } else {
      hinweise.push(hinweis('info', 'Ohne deinen aktuellen Abschlag zeigt das Werkzeug nur den fairen Wert. Trag den Betrag von deinem Kontoauszug ein, um Nachzahlung oder Guthaben zu sehen.'));
    }

    if (medium === 'gas') {
      hinweise.push(hinweis('info', 'Gasverbrauch verteilt sich nicht gleichmäßig: Zwei Drittel fallen zwischen Oktober und März an. Der faire Abschlag glättet das – ein im Sommer gesenkter Abschlag holt dich im Frühjahr wieder ein.'));
    } else {
      hinweise.push(hinweis('info', 'Rechne nach jeder Preisanpassung erneut. Versorger passen den Abschlag oft erst zur nächsten Jahresabrechnung an – bis dahin wächst die Lücke still weiter.'));
    }

    return { kennzahlen: kennzahlen, zeilen: zeilen, hinweise: hinweise };
  };

  // ------------------------------------------------------- Selbstbehalt
  logik.selbstbehalt = function (felder) {
    var fehler = pflicht(felder, ['beitrag_ohne', 'beitrag_mit', 'selbstbehalt']);
    if (fehler) return fehler;

    var ohne = wertVon(felder, 'beitrag_ohne');
    var mit = wertVon(felder, 'beitrag_mit');
    var sb = wertVon(felder, 'selbstbehalt');
    if (!(sb > 0)) return fehlt(['einen Selbstbehalt größer als null']);
    var schadenhoehe = wertOder(felder, 'schadenhoehe', 0);
    var schaeden = wertOder(felder, 'schaeden', 0);
    if (!(schaeden >= 0)) schaeden = 0;

    var ersparnis = ohne - mit;
    var wirksam = schadenhoehe > 0 ? Math.min(sb, schadenhoehe) : sb;
    var breakEvenJahr = wirksam > 0 ? ersparnis / wirksam : NaN;
    var breakEven10 = breakEvenJahr * 10;
    var kostenMit = mit * 10 + schaeden * wirksam;
    var kostenOhne = ohne * 10;
    var vorteil = kostenOhne - kostenMit;

    var kennzahlen = [
      kennzahl('Beitragsersparnis', euro(ersparnis) + ' pro Jahr', false),
      kennzahl('Break-even', isFinite(breakEven10) ? nummer(breakEven10, 1) + ' Schäden in zehn Jahren' : '–', false),
      kennzahl(vorteil >= 0 ? 'Vorteil mit Selbstbehalt' : 'Nachteil mit Selbstbehalt',
        euro(Math.abs(vorteil), 0) + ' über zehn Jahre', true)
    ];

    var zeilen = [
      { label: 'Zehn Jahre ohne Selbstbehalt', wert: euro(kostenOhne, 0) },
      { label: 'Zehn Jahre mit Selbstbehalt', wert: euro(kostenMit, 0) },
      { label: 'Wirksamer Eigenanteil je Schaden', wert: euro(wirksam, 0) },
      { label: 'Angenommene Schäden', wert: nummer(schaeden, 1) + ' in zehn Jahren' }
    ];

    var hinweise = [];
    if (ersparnis <= 0) {
      hinweise.push(hinweis('achtung', 'Der Tarif mit Selbstbehalt ist nicht günstiger. Damit trägst du Risiko, ohne dafür bezahlt zu werden – in dieser Konstellation gibt es kein Argument für den Eigenanteil.'));
    } else if (vorteil > 0) {
      hinweise.push(hinweis('gut', 'Bei der angenommenen Schadenzahl ist der Selbstbehalt über zehn Jahre um ' + euro(vorteil, 0) + ' günstiger. Ab ' + nummer(breakEven10, 1) + ' Schäden in zehn Jahren kippt das Verhältnis.'));
    } else {
      hinweise.push(hinweis('warnung', 'Bei der angenommenen Schadenzahl zahlst du mit Selbstbehalt ' + euro(Math.abs(vorteil), 0) + ' mehr. Der Eigenanteil lohnt sich erst unterhalb von ' + nummer(breakEven10, 1) + ' Schäden in zehn Jahren.'));
    }
    if (schadenhoehe > 0 && schadenhoehe < sb) {
      hinweise.push(hinweis('warnung', 'Deine typische Schadenhöhe liegt unter dem Selbstbehalt. Solche Schäden meldest du gar nicht erst – die Versicherung zahlt in diesen Fällen nie, der Beitrag läuft trotzdem.'));
    }
    hinweise.push(hinweis('info', 'Der Selbstbehalt muss jederzeit sofort verfügbar sein. Wer ihn im Ernstfall über den Dispo finanziert, verliert die Ersparnis an Zinsen – rechne ihn fest in deinen Notgroschen ein.'));
    hinweise.push(hinweis('info', 'Verglichen werden darf nur identischer Leistungsumfang. Ein günstigerer Beitrag mit engeren Bedingungen ist kein Selbstbehalt-Effekt, sondern eine andere Versicherung.'));

    return { kennzahlen: kennzahlen, zeilen: zeilen, hinweise: hinweise };
  };

  // -------------------------------------------------------- Notgroschen
  logik.notgroschen = function (felder, kontext) {
    var fehler = pflicht(felder, ['ausgaben']);
    if (fehler) return fehler;

    var ausgaben = wertVon(felder, 'ausgaben');
    var monateZiel = auswahlZahl(felder, 'lage', 3);
    var erspartes = wertOder(felder, 'erspartes', 0);
    var sparrate = wertOder(felder, 'sparrate', 0);
    var zins = wertOder(felder, 'zins', 0);
    if (!(zins >= 0) || zins > 20) zins = 0;

    var ziel = monateZiel * ausgaben;
    var fehlbetrag = Math.max(0, ziel - erspartes);

    var monate = 0;
    var bestand = erspartes;
    if (fehlbetrag > 0 && sparrate > 0) {
      var faktor = 1 + (zins / 100) / 12;
      while (bestand < ziel && monate < MAX_MONATE) {
        bestand = bestand * faktor + sparrate;
        monate++;
      }
      if (monate >= MAX_MONATE) monate = NaN;
    } else if (fehlbetrag > 0) {
      monate = NaN;
    }

    var heute = heuteMittag(kontext && kontext.heute);
    var zieldatum = isFinite(monate) && monate > 0 ? monatePlus(heute, monate) : null;

    var kennzahlen = [
      kennzahl('Zielbetrag', euro(ziel, 0), true),
      kennzahl('Noch zu sparen', euro(fehlbetrag, 0), false),
      kennzahl('Dauer bis zum Ziel', fehlbetrag === 0 ? 'Ziel erreicht' : (isFinite(monate) ? dauerText(monate) : 'nicht erreichbar'), false)
    ];
    if (zieldatum) kennzahlen.push(kennzahl('Voraussichtlich erreicht', datumFormat(zieldatum), false));

    var stufen = [
      { label: 'Erste Stufe: eine Monatsausgabe', betrag: ausgaben },
      { label: 'Zweite Stufe: halbes Ziel', betrag: ziel / 2 },
      { label: 'Volles Ziel: ' + monateZiel + ' Monatsausgaben', betrag: ziel }
    ];
    var liste = stufen.map(function (s) {
      var offen = Math.max(0, s.betrag - erspartes);
      var m = 0;
      if (offen > 0 && sparrate > 0) {
        var b = erspartes, f = 1 + (zins / 100) / 12;
        while (b < s.betrag && m < MAX_MONATE) { b = b * f + sparrate; m++; }
      }
      return {
        label: s.label,
        wert: euro(s.betrag, 0),
        anteil: s.betrag > 0 ? Math.min(100, (erspartes / s.betrag) * 100) : 0,
        zusatz: offen <= 0 ? 'bereits erreicht'
          : (sparrate > 0 && m < MAX_MONATE ? 'noch ' + dauerText(m) : 'ohne Sparrate offen')
      };
    });

    var zeilen = [
      { label: 'Notwendige Ausgaben', wert: euro(ausgaben) + ' pro Monat' },
      { label: 'Zielgröße deiner Lage', wert: monateZiel + ' Monatsausgaben' },
      { label: 'Bereits verfügbar', wert: euro(erspartes, 0) },
      { label: 'Monatliche Sparrate', wert: euro(sparrate) }
    ];
    if (zins > 0) {
      var zinsertrag = isFinite(monate) ? Math.max(0, bestand - erspartes - sparrate * monate) : NaN;
      zeilen.push({ label: 'Zinsbeitrag bis zum Ziel', wert: isFinite(zinsertrag) ? euro(zinsertrag, 0) : '–' });
    }

    var hinweise = [];
    if (fehlbetrag === 0) {
      hinweise.push(hinweis('gut', 'Dein Notgroschen steht. Halte ihn auf einem jederzeit verfügbaren Konto und passe den Zielbetrag an, sobald sich deine Fixkosten verändern.'));
    } else if (sparrate <= 0) {
      hinweise.push(hinweis('achtung', 'Ohne Sparrate gibt es keinen Weg zum Ziel. Beginne mit einem Betrag, den du auch im schlechten Monat durchhältst – 25 € sind ein Anfang, 0 € ist keiner.'));
    } else if (!isFinite(monate)) {
      hinweise.push(hinweis('achtung', 'Mit dieser Kombination aus Ziel und Sparrate wird das Ziel in absehbarer Zeit nicht erreicht. Senke das Ziel auf drei Monatsausgaben oder erhöhe die Rate.'));
    } else if (monate > 60) {
      hinweise.push(hinweis('warnung', 'Fünf Jahre sind eine lange Strecke. Nimm die erste Stufe als eigentliches Ziel: Eine Monatsausgabe auf dem Konto fängt bereits die meisten Alltagsschäden ab.'));
    } else {
      hinweise.push(hinweis('gut', 'Dauer bis zum Ziel: ' + dauerText(monate) + '. Richte einen Dauerauftrag auf den Monatsanfang ein – gespart wird, was zuerst abgeht, nicht was übrig bleibt.'));
    }
    if (zins > 0) {
      hinweise.push(hinweis('info', 'Der Zins ist hier Beiwerk, nicht Zweck. Der Notgroschen muss verfügbar sein; eine höhere Rendite mit Kündigungsfrist widerspricht seiner Aufgabe.'));
    }

    return {
      kennzahlen: kennzahlen,
      liste: liste,
      listeTitel: 'Deine drei Stufen',
      zeilen: zeilen,
      hinweise: hinweise
    };
  };

  // ------------------------------------------------------------ Fristen
  logik.fristen = function (felder, kontext) {
    var fehler = pflicht(felder, ['vertragsende', 'frist_wert']);
    if (fehler) return fehler;

    var ende = datumLesen(auswahl(felder, 'vertragsende'));
    if (!ende) return fehlt(['ein gültiges Vertragsende']);
    var wert = Math.round(wertVon(felder, 'frist_wert'));
    if (!(wert >= 0)) return fehlt(['eine Frist ab null']);
    if (wert > 60) wert = 60;
    var einheit = auswahl(felder, 'frist_einheit') || 'monate';

    var letzter;
    if (einheit === 'monate') letzter = monatePlus(ende, -wert);
    else if (einheit === 'wochen') letzter = tagePlus(ende, -wert * 7);
    else letzter = tagePlus(ende, -wert);

    var heute = heuteMittag(kontext && kontext.heute);
    var tage = tageDifferenz(letzter, heute);
    var verlaengerungMonate = auswahlZahl(felder, 'verlaengerung', 0);
    var art = auswahlLabel(felder, 'vertragsart') || 'Dauervertrag';

    var naechstesEnde = null;
    if (verlaengerungMonate > 0) {
      naechstesEnde = monatePlus(ende, verlaengerungMonate);
    }

    var termine = [
      {
        id: 'vergleich',
        titel: 'Vergleich rechnen: ' + art,
        datum: tagePlus(letzter, -42),
        beschreibung: 'Sechs Wochen vor dem letzten Kündigungstag: echte Jahreskosten ermitteln und Alternativen auf Effektivpreis prüfen.'
      },
      {
        id: 'schreiben',
        titel: 'Kündigung schreiben: ' + art,
        datum: tagePlus(letzter, -14),
        beschreibung: 'Zwei Wochen Puffer für Postlaufzeit, Kündigungsschaltfläche und Empfangsbestätigung.'
      },
      {
        id: 'frist',
        titel: 'Letzter Kündigungstag: ' + art,
        datum: letzter,
        beschreibung: 'Heute muss die Kündigung beim Vertragspartner zugehen – nicht abgeschickt sein (§ 130 BGB).'
      }
    ];

    var kennzahlen = [
      kennzahl('Letzter Kündigungstag', datumFormat(letzter), true),
      kennzahl('Verbleibende Zeit', tage >= 0 ? nummer(tage) + (tage === 1 ? ' Tag' : ' Tage') : 'Frist verstrichen', false),
      kennzahl('Vertragsende', datumFormat(ende), false)
    ];
    if (naechstesEnde) {
      kennzahlen.push(kennzahl('Nächster Ausstieg, wenn du nichts tust', datumFormat(naechstesEnde), false));
    }

    var zeilen = [
      { label: 'Vertragsart', wert: art },
      { label: 'Frist laut Vertrag', wert: wert + ' ' + (einheit === 'monate' ? 'Monate' : einheit === 'wochen' ? 'Wochen' : 'Tage') },
      { label: 'Rechenweg', wert: datumFormat(ende) + ' minus ' + wert + ' ' + (einheit === 'monate' ? 'Monate' : einheit === 'wochen' ? 'Wochen' : 'Tage') + ' = ' + datumFormat(letzter) }
    ];

    var hinweise = [];
    if (tage < 0) {
      hinweise.push(hinweis('achtung', 'Der letzte Kündigungstag liegt ' + nummer(Math.abs(tage)) + ' Tage zurück.' +
        (naechstesEnde
          ? ' Der Vertrag verlängert sich; der nächste Ausstieg ist der ' + datumFormat(naechstesEnde) + '. Trag ihn jetzt ein, dann passiert es kein zweites Mal.'
          : ' Prüfe im Vertrag, ob eine ordentliche Kündigung weiterhin möglich ist.')));
    } else if (tage <= 14) {
      hinweise.push(hinweis('nachzahlung', 'Nur noch ' + nummer(tage) + ' Tage. Nutze die gesetzliche Kündigungsschaltfläche im Kundenkonto (§ 312k BGB) oder sende per Einschreiben – entscheidend ist der Zugang, nicht der Poststempel.'));
    } else if (tage <= 42) {
      hinweise.push(hinweis('warnung', 'Noch ' + nummer(tage) + ' Tage. Jetzt ist der richtige Moment für den Vergleich: Wer erst in der letzten Woche rechnet, entscheidet unter Druck.'));
    } else {
      hinweise.push(hinweis('gut', 'Du bist früh dran: ' + nummer(tage) + ' Tage bis zum letzten Kündigungstag. Lege die drei Termine in deinen Kalender und vergiss den Vertrag bis dahin.'));
    }
    if (verlaengerungMonate >= 12) {
      hinweise.push(hinweis('warnung', 'Eine Verlängerung um zwölf Monate ist in Neuverträgen seit dem Gesetz für faire Verbraucherverträge die Ausnahme. Prüfe, ob dein Vertrag noch unter die alte Regel fällt.'));
    } else if (verlaengerungMonate === 1) {
      hinweise.push(hinweis('info', 'Nach der ersten Laufzeit bist du monatlich kündbar. Ein verpasster Termin kostet dich damit höchstens einen Monat – aber den jeden Monat erneut.'));
    }
    hinweise.push(hinweis('info', 'Verbindlich ist immer dein Vertragstext. Dieses Werkzeug rechnet die Frist, es liest sie nicht aus – und es ersetzt keine Rechtsberatung.'));

    return {
      kennzahlen: kennzahlen,
      zeilen: zeilen,
      hinweise: hinweise,
      termine: termine
    };
  };

  // ------------------------------------------------------- Entscheidung
  logik.entscheidung = function (felder) {
    var kostenBekannt = auswahl(felder, 'kosten_bekannt') || 'ja';
    var bindung = auswahl(felder, 'bindung') || 'frei';
    var konditionen = auswahl(felder, 'konditionen') || 'garantie';
    var vorkasse = auswahl(felder, 'vorkasse') || 'nein';
    var ersparnis = wertVon(felder, 'ersparnis');

    var empfehlung, art, begruendung = [], schritt;

    if (kostenBekannt === 'nein') {
      empfehlung = 'Erst rechnen, dann entscheiden';
      art = 'warnung';
      begruendung.push('Ohne deine echten Jahreskosten vergleichst du einen Werbepreis mit einem Abschlag. Das ist keine Entscheidungsgrundlage.');
      begruendung.push('Die Jahresabrechnung nennt Verbrauch und Gesamtkosten – beides brauchst du, bevor ein Angebot überhaupt bewertbar ist.');
      schritt = 'Hol die letzte Jahresabrechnung und rechne sie im Abschlagsrechner nach. Danach kommst du hierher zurück.';
    } else if (vorkasse === 'ja') {
      empfehlung = 'Dieses Angebot nicht';
      art = 'achtung';
      begruendung.push('Vorkasse oder Kaution verwandelt eine rechnerische Ersparnis in ein Ausfallrisiko: Du finanzierst den Anbieter vor, ohne Gegenwert.');
      begruendung.push('Die Höhe der Ersparnis ändert daran nichts – ein Insolvenzfall kostet mehr, als jeder Tarifvorteil einbringt.');
      schritt = 'Suche eine Alternative mit monatlicher Abrechnung. Bei gleichem Preis ist das immer die bessere Struktur.';
    } else if (!isFinite(ersparnis)) {
      return fehlt(['die rechnerische Ersparnis pro Jahr']);
    } else if (ersparnis < AUFWANDSGRENZE) {
      empfehlung = 'Bleiben und Termin setzen';
      art = 'info';
      begruendung.push('Mit ' + euro(ersparnis, 0) + ' im Jahr liegt die Ersparnis unter der Aufwandsgrenze von ' + euro(AUFWANDSGRENZE, 0) + ', ab der ein Wechsel erfahrungsgemäß trägt.');
      begruendung.push('Wechselaufwand, Zählerstandsmeldung und das Risiko eines schlechteren Dienstleisters sind nicht kostenlos.');
      schritt = 'Trag dir den nächsten Kündigungstermin ein und prüfe erneut, wenn der Anbieter die Preise anpasst.';
    } else if (bindung === 'gebunden') {
      empfehlung = 'Termin setzen, jetzt nicht kündigen';
      art = 'info';
      begruendung.push('Du bist länger als sechs Monate gebunden. Ein Wechsel heute ist nicht möglich, die Ersparnis von ' + euro(ersparnis, 0) + ' im Jahr bleibt aber vorgemerkt.');
      begruendung.push('Tarife ändern sich schneller als Laufzeiten: Die Rechnung von heute ist zum Fristbeginn ohnehin neu zu machen.');
      schritt = 'Leg den letzten Kündigungstag im Fristen-Kalender an und rechne sechs Wochen vorher erneut.';
    } else if (bindung === 'bald') {
      empfehlung = 'Jetzt vorbereiten, zum Fristbeginn wechseln';
      art = 'gut';
      begruendung.push('Die Bindung endet in den nächsten sechs Monaten – damit ist der Wechsel planbar statt hektisch.');
      begruendung.push('Eine Ersparnis von ' + euro(ersparnis, 0) + ' im Jahr rechtfertigt den Aufwand, sobald die Frist läuft.');
      schritt = 'Setze dir eine Erinnerung sechs Wochen vor dem letzten Kündigungstag und vergleiche dann erneut.';
    } else if (konditionen === 'bonuslastig') {
      if (ersparnis >= 2 * AUFWANDSGRENZE) {
        empfehlung = 'Wechseln – und das Folgejahr sofort vormerken';
        art = 'gut';
        begruendung.push('Die Ersparnis von ' + euro(ersparnis, 0) + ' trägt auch dann, wenn ein Teil davon aus dem einmaligen Bonus stammt.');
        begruendung.push('Bonusmodelle sind Jahresverträge mit Verfallsdatum: Ohne Folgetermin zahlst du ab dem zweiten Jahr den Normalpreis.');
        schritt = 'Wechsle – und lege denselben Tag im nächsten Jahr als Prüftermin an, bevor du die Bestätigung weglegst.';
      } else {
        empfehlung = 'Nur wechseln, wenn du den Folgetermin wirklich hältst';
        art = 'warnung';
        begruendung.push('Der Vorteil entsteht überwiegend aus dem Neukundenbonus und wirkt genau einmal.');
        begruendung.push('Bleibt die Ersparnis unter ' + euro(2 * AUFWANDSGRENZE, 0) + ' im Jahr, kippt sie im zweiten Jahr leicht ins Gegenteil.');
        schritt = 'Entweder du führst den Wechsel als jährliche Routine – oder du suchst einen Tarif mit Preisgarantie statt Bonus.';
      }
    } else if (konditionen === 'ohne') {
      empfehlung = 'Wechseln, aber mit kurzer Laufzeit';
      art = 'gut';
      begruendung.push('Die Ersparnis von ' + euro(ersparnis, 0) + ' im Jahr ist belastbar, der Preis aber jederzeit anpassbar.');
      begruendung.push('Ohne Preisgarantie ist die kurze Laufzeit dein einziger Schutz – sie hält das nächste Fenster offen.');
      schritt = 'Wähle die kürzeste Laufzeit und trag dir den nächsten Kündigungstag direkt nach Vertragsschluss ein.';
    } else {
      empfehlung = 'Wechseln';
      art = 'gut';
      begruendung.push('Kündbar, ' + euro(ersparnis, 0) + ' Ersparnis im Jahr, Preisgarantie über die Laufzeit: Diese Kombination trägt die Entscheidung.');
      begruendung.push('Die Garantie macht die Rechnung haltbar – du vergleichst nicht gegen einen Preis, der sich im dritten Monat ändert.');
      schritt = 'Wechsle und lege den letzten Kündigungstag der neuen Laufzeit sofort im Fristen-Kalender an.';
    }

    if (vorkasse === 'nein' && kostenBekannt === 'ja' && isFinite(ersparnis)) {
      begruendung.push('Über 24 Monate entspricht das ' + euro(ersparnis * 2, 0) + '. Diese Zahl gehört in die Entscheidung, nicht der Monatsbetrag.');
    }

    var kennzahlen = [
      kennzahl('Empfehlung', empfehlung, true)
    ];
    if (isFinite(ersparnis)) {
      kennzahlen.push(kennzahl('Ersparnis pro Jahr', euro(ersparnis, 0), false));
      kennzahlen.push(kennzahl('Über 24 Monate', euro(ersparnis * 2, 0), false));
    }

    var zeilen = [
      { label: 'Jahreskosten bekannt', wert: auswahlLabel(felder, 'kosten_bekannt') },
      { label: 'Kündbarkeit', wert: auswahlLabel(felder, 'bindung') },
      { label: 'Tarifstruktur', wert: auswahlLabel(felder, 'konditionen') },
      { label: 'Vorkasse oder Kaution', wert: auswahlLabel(felder, 'vorkasse') }
    ];

    var hinweise = begruendung.map(function (text) { return hinweis(art === 'gut' ? 'info' : art, text); });
    hinweise.unshift(hinweis(art, schritt));

    return { kennzahlen: kennzahlen, zeilen: zeilen, hinweise: hinweise, empfehlung: empfehlung };
  };

  // ------------------------------------------------------------- Budget
  logik.budget = function (felder) {
    var einkommen = wertOder(felder, 'einkommen', 0);
    var gruppen = { bedarf: 0, wunsch: 0, sparen: 0 };
    var ausgaben = 0;
    var posten = [];

    for (var i = 0; i < felder.length; i++) {
      var f = felder[i];
      if (f.bucket === 'einnahme') continue;
      if (!isFinite(f.zahl) || f.zahl <= 0) continue;
      var bucket = f.bucket || 'wunsch';
      if (!(bucket in gruppen)) bucket = 'wunsch';
      gruppen[bucket] += f.zahl;
      ausgaben += f.zahl;
      posten.push({ label: f.label, wert: f.zahl, bucket: bucket });
    }

    if (einkommen <= 0 && !posten.length) {
      return fehlt(['dein Haushaltsnetto und mindestens einen Ausgabenposten']);
    }

    var saldo = einkommen - ausgaben;
    var sparquote = einkommen > 0 ? (gruppen.sparen / einkommen) * 100 : NaN;

    var ziele = { bedarf: 0.5, wunsch: 0.3, sparen: 0.2 };
    var namen = { bedarf: 'Bedarf (50 %)', wunsch: 'Wünsche (30 %)', sparen: 'Sparen & Tilgung (20 %)' };
    var liste = ['bedarf', 'wunsch', 'sparen'].map(function (key) {
      var ist = gruppen[key];
      var soll = einkommen * ziele[key];
      var anteil = einkommen > 0 ? (ist / einkommen) * 100 : 0;
      return {
        label: namen[key],
        wert: euro(ist),
        anteil: anteil,
        zusatz: einkommen > 0
          ? 'Ziel ' + euro(soll, 0) + ' · Ist ' + prozent(anteil, 0) + ' · ' +
            (ist > soll ? euro(ist - soll, 0) + ' darüber' : euro(soll - ist, 0) + ' darunter')
          : 'Ohne Einkommen keine Quote'
      };
    });

    posten.sort(function (a, b) { return b.wert - a.wert; });

    var kennzahlen = [
      kennzahl('Ausgaben gesamt', euro(ausgaben) + ' pro Monat', false),
      kennzahl(saldo >= 0 ? 'Überschuss' : 'Unterdeckung', euro(Math.abs(saldo)) + ' pro Monat', true)
    ];
    if (isFinite(sparquote)) kennzahlen.push(kennzahl('Sparquote', prozent(sparquote), false));
    kennzahlen.push(kennzahl('Hochgerechnet', euro(ausgaben * 12, 0) + ' Ausgaben pro Jahr', false));

    var zeilen = posten.slice(0, 5).map(function (p) {
      return {
        label: p.label,
        wert: euro(p.wert) + (einkommen > 0 ? ' · ' + prozent((p.wert / einkommen) * 100, 0) + ' vom Netto' : '')
      };
    });
    zeilen.push({ label: 'Summe aller Ausgaben', wert: euro(ausgaben) });

    var hinweise = [];
    if (saldo < 0) {
      hinweise.push(hinweis('achtung', 'Deine Ausgaben übersteigen das Einkommen um ' + euro(Math.abs(saldo)) + ' im Monat. Das ist kein Budgetproblem, sondern ein Fixkostenproblem – beginne beim größten Posten, nicht bei den kleinen Wünschen.'));
    } else if (saldo === 0 && einkommen > 0) {
      hinweise.push(hinweis('warnung', 'Dein Budget geht exakt auf. Jede unerwartete Rechnung landet damit auf dem Dispo – plane einen Puffer ein, bevor du sparst.'));
    } else if (einkommen > 0) {
      hinweise.push(hinweis('gut', 'Es bleiben ' + euro(saldo) + ' im Monat. Überweise diesen Betrag am Monatsanfang, nicht am Monatsende – sonst wird aus dem Überschuss unbemerkt Konsum.'));
    }
    if (einkommen > 0) {
      var bedarfQuote = (gruppen.bedarf / einkommen) * 100;
      if (bedarfQuote > 55) {
        hinweise.push(hinweis('warnung', 'Der Bedarfsanteil liegt bei ' + prozent(bedarfQuote, 0) + ' statt 50 %. In teuren Städten ist das normal – es verschiebt aber den Spielraum von „Wünsche" zu „Sparen" und macht Tarifwechsel wichtiger.'));
      }
      if (isFinite(sparquote) && sparquote < 10) {
        hinweise.push(hinweis('warnung', 'Mit ' + prozent(sparquote, 0) + ' Sparquote dauert jeder Puffer lange. Die ersten Prozentpunkte holst du am schnellsten aus Verträgen, nicht aus dem Alltag.'));
      } else if (isFinite(sparquote) && sparquote >= 20) {
        hinweise.push(hinweis('gut', 'Eine Sparquote von ' + prozent(sparquote, 0) + ' trägt. Prüfe nur, ob der Notgroschen steht, bevor du längerfristig anlegst.'));
      }
    }
    hinweise.push(hinweis('info', 'Jahreszahlungen gehören durch zwölf geteilt ins Budget. Sonst stimmt es elf Monate lang und reißt im zwölften.'));

    return {
      kennzahlen: kennzahlen,
      liste: liste,
      listeTitel: 'Verteilung nach 50-30-20',
      zeilen: zeilen,
      hinweise: hinweise
    };
  };

  // =================================================================
  // 4. EXPORT – CSV, PDF, ICS. Alles im Browser, nichts über das Netz.
  // =================================================================

  function csvFeld(wert) {
    var text = String(wert == null ? '' : wert).replace(/\r?\n/g, ' ');
    if (/[";]/.test(text)) text = '"' + text.replace(/"/g, '""') + '"';
    return text;
  }

  /** Zeilen: Array aus Arrays. Semikolon + BOM = Excel-tauglich in DE. */
  function alsCsv(zeilen) {
    var text = zeilen.map(function (z) { return z.map(csvFeld).join(';'); }).join('\r\n');
    return '\ufeff' + text + '\r\n';
  }

  // ---- Minimaler PDF-Schreiber (PDF 1.4, Helvetica, WinAnsiEncoding) ----
  var WINANSI = {
    '\u20ac': 128, '\u201a': 130, '\u0192': 131, '\u201e': 132, '\u2026': 133,
    '\u2020': 134, '\u2021': 135, '\u02c6': 136, '\u2030': 137, '\u0160': 138,
    '\u2039': 139, '\u0152': 140, '\u017d': 142, '\u2018': 145, '\u2019': 146,
    '\u201c': 147, '\u201d': 148, '\u2022': 149, '\u2013': 150, '\u2014': 151,
    '\u02dc': 152, '\u2122': 153, '\u0161': 154, '\u203a': 155, '\u0153': 156,
    '\u017e': 158, '\u0178': 159
  };

  function winAnsi(text) {
    var out = '';
    for (var i = 0; i < text.length; i++) {
      var ch = text.charAt(i), code = text.charCodeAt(i);
      if (WINANSI[ch] !== undefined) out += String.fromCharCode(WINANSI[ch]);
      else if (code < 256) out += ch;
      else out += '?';
    }
    return out;
  }

  function pdfText(text) {
    return winAnsi(String(text == null ? '' : text))
      .replace(/\\/g, '\\\\').replace(/\(/g, '\\(').replace(/\)/g, '\\)');
  }

  /** Grobe Breitenschätzung für Helvetica – reicht für den Zeilenumbruch. */
  function umbrechen(text, groesse, breite) {
    var maxZeichen = Math.max(12, Math.floor(breite / (groesse * 0.5)));
    var worte = String(text == null ? '' : text).split(/\s+/);
    var zeilen = [], aktuell = '';
    for (var i = 0; i < worte.length; i++) {
      var kandidat = aktuell ? aktuell + ' ' + worte[i] : worte[i];
      if (kandidat.length > maxZeichen && aktuell) {
        zeilen.push(aktuell);
        aktuell = worte[i];
      } else {
        aktuell = kandidat;
      }
    }
    if (aktuell) zeilen.push(aktuell);
    return zeilen.length ? zeilen : [''];
  }

  /**
   * dokument = { titel, untertitel, fusszeile, abschnitte:[{titel, zeilen:[[label,wert]] , absaetze:[text]}] }
   * Liefert eine Uint8Array mit einem gültigen, mehrseitigen PDF.
   */
  function alsPdf(dokument) {
    var SEITE_B = 595.28, SEITE_H = 841.89;
    var RAND = 56, BREITE = SEITE_B - 2 * RAND;
    var seiten = [], strom = '', y = 0;

    function neueSeite() {
      if (strom) seiten.push(strom);
      strom = '';
      y = SEITE_H - RAND;
    }

    function schreibe(text, groesse, fett, einzug, abstand) {
      var zeilen = umbrechen(text, groesse, BREITE - (einzug || 0));
      for (var i = 0; i < zeilen.length; i++) {
        if (y < RAND + 40) neueSeite();
        strom += 'BT /' + (fett ? 'F2' : 'F1') + ' ' + groesse + ' Tf ' +
          (RAND + (einzug || 0)) + ' ' + y.toFixed(2) + ' Td (' + pdfText(zeilen[i]) + ') Tj ET\n';
        y -= groesse * 1.35;
      }
      y -= (abstand || 0);
    }

    function linie() {
      if (y < RAND + 40) neueSeite();
      strom += '0.82 0.86 0.84 RG 0.7 w ' + RAND + ' ' + y.toFixed(2) + ' m ' +
        (SEITE_B - RAND) + ' ' + y.toFixed(2) + ' l S\n';
      y -= 12;
    }

    neueSeite();
    schreibe(dokument.titel || 'Franks Werkzeuge', 17, true, 0, 4);
    if (dokument.untertitel) schreibe(dokument.untertitel, 9.5, false, 0, 6);
    linie();

    var abschnitte = dokument.abschnitte || [];
    for (var a = 0; a < abschnitte.length; a++) {
      var ab = abschnitte[a];
      if (ab.titel) schreibe(ab.titel, 11, true, 0, 3);
      var zeilen = ab.zeilen || [];
      for (var z = 0; z < zeilen.length; z++) {
        var label = String(zeilen[z][0] == null ? '' : zeilen[z][0]);
        var wert = String(zeilen[z][1] == null ? '' : zeilen[z][1]);
        schreibe(wert ? label + ': ' + wert : label, 9.5, false, 10, 0);
      }
      var absaetze = ab.absaetze || [];
      for (var p = 0; p < absaetze.length; p++) {
        schreibe(absaetze[p], 9.5, false, 10, 2);
      }
      y -= 8;
    }

    if (dokument.fusszeile) {
      linie();
      schreibe(dokument.fusszeile, 8, false, 0, 0);
    }
    if (strom) seiten.push(strom);

    // ---- Objekte zusammensetzen -------------------------------------
    var objekte = [];
    var seitenIds = [];
    var naechste = 3 + seiten.length * 2;           // 1 Catalog, 2 Pages, dann je Seite 2
    for (var s = 0; s < seiten.length; s++) seitenIds.push(3 + s * 2);
    var fontRegular = naechste, fontBold = naechste + 1;

    objekte[1] = '<< /Type /Catalog /Pages 2 0 R >>';
    objekte[2] = '<< /Type /Pages /Count ' + seiten.length + ' /Kids [' +
      seitenIds.map(function (id) { return id + ' 0 R'; }).join(' ') + '] >>';
    for (var k = 0; k < seiten.length; k++) {
      var pid = seitenIds[k], cid = pid + 1;
      objekte[pid] = '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ' + SEITE_B.toFixed(2) + ' ' + SEITE_H.toFixed(2) + '] ' +
        '/Resources << /Font << /F1 ' + fontRegular + ' 0 R /F2 ' + fontBold + ' 0 R >> >> /Contents ' + cid + ' 0 R >>';
      objekte[cid] = '<< /Length ' + seiten[k].length + ' >>\nstream\n' + seiten[k] + 'endstream';
    }
    objekte[fontRegular] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>';
    objekte[fontBold] = '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>';

    var kopf = '%PDF-1.4\n%\u00e2\u00e3\u00cf\u00d3\n';
    var text = kopf, versatz = [];
    for (var o = 1; o < objekte.length; o++) {
      versatz[o] = text.length;
      text += o + ' 0 obj\n' + objekte[o] + '\nendobj\n';
    }
    var xref = text.length;
    text += 'xref\n0 ' + objekte.length + '\n0000000000 65535 f \n';
    for (var x = 1; x < objekte.length; x++) {
      text += ('0000000000' + versatz[x]).slice(-10) + ' 00000 n \n';
    }
    text += 'trailer\n<< /Size ' + objekte.length + ' /Root 1 0 R >>\nstartxref\n' + xref + '\n%%EOF\n';

    var bytes = new Uint8Array(text.length);
    for (var b = 0; b < text.length; b++) bytes[b] = text.charCodeAt(b) & 0xff;
    return bytes;
  }

  // ---- iCalendar ---------------------------------------------------
  /**
   * Zeilenfaltung nach RFC 5545: Eine Zeile darf 75 OKTETTE nicht
   * überschreiten – nicht 75 Zeichen. Umlaute und „–" belegen in UTF-8
   * zwei bis drei Bytes; eine zeichenbasierte Faltung erzeugt deshalb zu
   * lange Zeilen, an denen strenge Kalender (Outlook) aussteigen. Dieser
   * Faltung zählt Bytes und trennt nie innerhalb eines Zeichens.
   */
  function icsFalten(zeile) {
    var GRENZE = 73;            // 73 Oktette + CRLF bleibt unter 75
    var zeilen = [], aktuell = '', bytes = 0;
    for (var i = 0; i < zeile.length; i++) {
      var code = zeile.charCodeAt(i);
      var zeichen = zeile.charAt(i);
      var laenge;
      if (code >= 0xd800 && code <= 0xdbff && i + 1 < zeile.length) {
        zeichen += zeile.charAt(i + 1);
        laenge = 4;
        i++;
      } else if (code < 0x80) laenge = 1;
      else if (code < 0x800) laenge = 2;
      else laenge = 3;
      if (bytes + laenge > GRENZE) {
        zeilen.push(aktuell);
        aktuell = ' ';
        bytes = 1;
      }
      aktuell += zeichen;
      bytes += laenge;
    }
    zeilen.push(aktuell);
    return zeilen.join('\r\n');
  }

  function icsText(wert) {
    return String(wert == null ? '' : wert)
      .replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,')
      .replace(/\r?\n/g, '\\n');
  }

  function icsStempel(d) {
    var p = function (n) { return (n < 10 ? '0' : '') + n; };
    return d.getUTCFullYear() + p(d.getUTCMonth() + 1) + p(d.getUTCDate()) + 'T' +
      p(d.getUTCHours()) + p(d.getUTCMinutes()) + p(d.getUTCSeconds()) + 'Z';
  }

  /** termine: [{id, titel, datum(Date), beschreibung}] – ganztägige Einträge. */
  function alsIcs(termine, kontext) {
    var jetzt = (kontext && kontext.jetzt) || new Date();
    var zeilen = [
      'BEGIN:VCALENDAR', 'VERSION:2.0',
      'PRODID:-//FranksFinanzcheck//Werkzeuge//DE',
      'CALSCALE:GREGORIAN', 'METHOD:PUBLISH'
    ];
    for (var i = 0; i < termine.length; i++) {
      var t = termine[i];
      if (!t || !t.datum) continue;
      var tag = iso(t.datum).replace(/-/g, '');
      var ende = iso(tagePlus(t.datum, 1)).replace(/-/g, '');
      zeilen.push('BEGIN:VEVENT');
      zeilen.push('UID:' + tag + '-' + (t.id || i) + '@franksfinanzcheck.de');
      zeilen.push('DTSTAMP:' + icsStempel(jetzt));
      zeilen.push('DTSTART;VALUE=DATE:' + tag);
      zeilen.push('DTEND;VALUE=DATE:' + ende);
      zeilen.push('SUMMARY:' + icsText(t.titel));
      if (t.beschreibung) zeilen.push('DESCRIPTION:' + icsText(t.beschreibung));
      zeilen.push('TRANSP:TRANSPARENT');
      zeilen.push('BEGIN:VALARM');
      zeilen.push('TRIGGER:-PT9H');
      zeilen.push('ACTION:DISPLAY');
      zeilen.push('DESCRIPTION:' + icsText(t.titel));
      zeilen.push('END:VALARM');
      zeilen.push('END:VEVENT');
    }
    zeilen.push('END:VCALENDAR');
    return zeilen.map(icsFalten).join('\r\n') + '\r\n';
  }

  function dateiname(praefix, id, endung) {
    var d = new Date();
    return [praefix || 'franksfinanzcheck', id, iso(heuteMittag(d))].filter(Boolean).join('-') + '.' + endung;
  }

  function herunterladen(daten, name, typ, dokument) {
    var fenster = dokument && dokument.defaultView ? dokument.defaultView : (typeof window !== 'undefined' ? window : null);
    if (!fenster || !fenster.URL || typeof fenster.URL.createObjectURL !== 'function' || typeof fenster.Blob !== 'function') {
      return false;
    }
    var blob = new fenster.Blob([daten], { type: typ });
    var url = fenster.URL.createObjectURL(blob);
    var a = (dokument || fenster.document).createElement('a');
    a.href = url;
    a.download = name;
    a.rel = 'noopener';
    (dokument || fenster.document).body.appendChild(a);
    a.click();
    (dokument || fenster.document).body.removeChild(a);
    fenster.setTimeout(function () { fenster.URL.revokeObjectURL(url); }, 2000);
    return true;
  }

  // =================================================================
  // 5. DOM-ANBINDUNG
  // =================================================================

  function text(el) {
    return el ? String(el.textContent || '').replace(/\s+/g, ' ').trim() : '';
  }

  function korridorLesen(roh) {
    if (!roh) return null;
    var teile = String(roh).split(',').map(function (t) { return Number(t); });
    if (teile.length !== 2 || !isFinite(teile[0]) || !isFinite(teile[1])) return null;
    return teile;
  }

  /** Liest alle Felder einer Werkzeug-Sektion in die Struktur des Rechenkerns. */
  function felderLesen(wurzel) {
    var knoten = wurzel.querySelectorAll('[data-feld]');
    var felder = [];
    for (var i = 0; i < knoten.length; i++) {
      var el = knoten[i];
      var typ = el.getAttribute('data-typ') || 'euro';
      var wert = el.value == null ? '' : String(el.value);
      var eintrag = {
        id: el.getAttribute('data-feld'),
        label: el.getAttribute('data-label') || '',
        typ: typ,
        einheit: el.getAttribute('data-einheit') || '',
        bucket: el.getAttribute('data-bucket') || '',
        korridor: korridorLesen(el.getAttribute('data-korridor')),
        pflicht: el.hasAttribute('data-pflicht'),
        wert: wert,
        zahl: typ === 'datum' || typ === 'auswahl' ? NaN : zahl(wert),
        element: el
      };
      if (typ === 'auswahl' && el.options && el.selectedIndex >= 0) {
        var opt = el.options[el.selectedIndex];
        eintrag.auswahlLabel = opt ? String(opt.textContent || '').trim() : '';
        var z = opt ? opt.getAttribute('data-zahl') : null;
        eintrag.auswahlZahl = z == null ? NaN : Number(z);
      }
      felder.push(eintrag);
    }
    return felder;
  }

  function leere(el) {
    while (el && el.firstChild) el.removeChild(el.firstChild);
  }

  function machen(dok, tag, klasse, inhalt) {
    var el = dok.createElement(tag);
    if (klasse) el.className = klasse;
    if (inhalt != null) el.textContent = String(inhalt);
    return el;
  }

  function zeichneErgebnis(wurzel, ergebnis, dok) {
    var ausgabe = wurzel.querySelector('[data-ff-wz-ausgabe]');
    var leerText = wurzel.querySelector('[data-ff-wz-leer]');
    var fehlerBox = wurzel.querySelector('[data-ff-wz-fehler]');

    if (fehlerBox) { leere(fehlerBox); fehlerBox.hidden = true; }

    if (ergebnis && ergebnis.fehler) {
      if (ausgabe) ausgabe.hidden = true;
      if (leerText) leerText.hidden = true;
      if (fehlerBox) {
        fehlerBox.hidden = false;
        fehlerBox.appendChild(machen(dok, 'p', 'ff-wz__fehler-titel',
          'Für die Rechnung fehlt noch etwas:'));
        var ul = machen(dok, 'ul', 'ff-wz__fehler-liste');
        ergebnis.fehler.forEach(function (f) { ul.appendChild(machen(dok, 'li', null, f)); });
        fehlerBox.appendChild(ul);
      }
      return;
    }
    if (!ergebnis) return;
    if (leerText) leerText.hidden = true;
    if (!ausgabe) return;
    ausgabe.hidden = false;

    var kz = wurzel.querySelector('[data-ff-wz-kennzahlen]');
    if (kz) {
      leere(kz);
      (ergebnis.kennzahlen || []).forEach(function (k) {
        var box = machen(dok, 'div', 'ff-wz__kennzahl' + (k.stark ? ' ff-wz__kennzahl--stark' : ''));
        box.appendChild(machen(dok, 'span', 'ff-wz__kennzahl-label', k.label));
        box.appendChild(machen(dok, 'strong', 'ff-wz__kennzahl-wert', k.wert));
        kz.appendChild(box);
      });
    }

    var listeBox = wurzel.querySelector('[data-ff-wz-liste]');
    if (listeBox) {
      leere(listeBox);
      var liste = ergebnis.liste || [];
      if (liste.length) {
        listeBox.hidden = false;
        listeBox.appendChild(machen(dok, 'h4', 'ff-wz__block-titel', ergebnis.listeTitel || 'Aufschlüsselung'));
        var ol = machen(dok, 'ol', 'ff-wz__rang');
        liste.forEach(function (eintrag) {
          var li = machen(dok, 'li', 'ff-wz__rang-eintrag');
          var kopf = machen(dok, 'div', 'ff-wz__rang-kopf');
          kopf.appendChild(machen(dok, 'span', 'ff-wz__rang-label', eintrag.label));
          kopf.appendChild(machen(dok, 'strong', 'ff-wz__rang-wert', eintrag.wert));
          li.appendChild(kopf);
          var balken = machen(dok, 'div', 'ff-wz__balken');
          var fuellung = machen(dok, 'span', 'ff-wz__balken-fuellung');
          fuellung.style.width = Math.max(2, Math.min(100, eintrag.anteil || 0)).toFixed(1) + '%';
          balken.appendChild(fuellung);
          li.appendChild(balken);
          if (eintrag.zusatz) li.appendChild(machen(dok, 'p', 'ff-wz__rang-zusatz', eintrag.zusatz));
          ol.appendChild(li);
        });
        listeBox.appendChild(ol);
      } else {
        listeBox.hidden = true;
      }
    }

    var zeilenBox = wurzel.querySelector('[data-ff-wz-zeilen]');
    if (zeilenBox) {
      leere(zeilenBox);
      var zeilen = ergebnis.zeilen || [];
      if (zeilen.length) {
        zeilenBox.hidden = false;
        zeilenBox.appendChild(machen(dok, 'h4', 'ff-wz__block-titel', 'Der Rechenweg im Detail'));
        var dl = machen(dok, 'dl', 'ff-wz__zeilen');
        zeilen.forEach(function (z) {
          dl.appendChild(machen(dok, 'dt', null, z.label));
          dl.appendChild(machen(dok, 'dd', null, z.wert));
        });
        zeilenBox.appendChild(dl);
      } else {
        zeilenBox.hidden = true;
      }
    }

    var hinweisBox = wurzel.querySelector('[data-ff-wz-hinweise]');
    if (hinweisBox) {
      leere(hinweisBox);
      (ergebnis.hinweise || []).forEach(function (h) {
        hinweisBox.appendChild(machen(dok, 'p', 'ff-wz__hinweis ff-wz__hinweis--' + h.art, h.text));
      });
    }

    var termineBox = wurzel.querySelector('[data-ff-wz-termine]');
    if (termineBox) {
      leere(termineBox);
      var termine = ergebnis.termine || [];
      if (termine.length) {
        termineBox.hidden = false;
        termineBox.appendChild(machen(dok, 'h4', 'ff-wz__block-titel', 'Deine drei Termine'));
        var ul2 = machen(dok, 'ul', 'ff-wz__termine');
        termine.forEach(function (t) {
          var li = machen(dok, 'li', 'ff-wz__termin');
          li.appendChild(machen(dok, 'strong', 'ff-wz__termin-datum', datumFormat(t.datum)));
          li.appendChild(machen(dok, 'span', 'ff-wz__termin-titel', t.titel));
          li.appendChild(machen(dok, 'span', 'ff-wz__termin-text', t.beschreibung));
          ul2.appendChild(li);
        });
        termineBox.appendChild(ul2);
      } else {
        termineBox.hidden = true;
      }
    }
  }

  /** Sammelt alles für einen Export – Eingaben, Ergebnis, Formel, Quellen. */
  function exportModell(wurzel, felder, ergebnis) {
    var name = wurzel.getAttribute('data-name') || 'Werkzeug';
    var eingaben = felder
      .filter(function (f) { return f.wert !== '' && f.wert != null; })
      .map(function (f) {
        var wert = f.typ === 'auswahl' ? (f.auswahlLabel || f.wert) : f.wert;
        return [f.label || f.id, wert + (f.einheit && f.typ !== 'auswahl' ? ' ' + f.einheit : '')];
      });

    var ergebnisZeilen = [];
    (ergebnis.kennzahlen || []).forEach(function (k) { ergebnisZeilen.push([k.label, k.wert]); });
    (ergebnis.liste || []).forEach(function (l) { ergebnisZeilen.push([l.label, l.wert + (l.zusatz ? ' (' + l.zusatz + ')' : '')]); });
    (ergebnis.zeilen || []).forEach(function (z) { ergebnisZeilen.push([z.label, z.wert]); });
    (ergebnis.termine || []).forEach(function (t) { ergebnisZeilen.push([t.titel, datumFormat(t.datum)]); });

    var hinweise = (ergebnis.hinweise || []).map(function (h) { return h.text; });

    var formel = [], quellen = [], annahmen = [];
    var formelKnoten = wurzel.querySelectorAll('[data-ff-wz-formel] li');
    for (var i = 0; i < formelKnoten.length; i++) formel.push(text(formelKnoten[i]));
    var annahmeKnoten = wurzel.querySelectorAll('[data-ff-wz-annahme] li');
    for (var a = 0; a < annahmeKnoten.length; a++) annahmen.push(text(annahmeKnoten[a]));
    var quellKnoten = wurzel.querySelectorAll('[data-ff-wz-quelle]');
    for (var q = 0; q < quellKnoten.length; q++) {
      var url = quellKnoten[q].getAttribute('data-url');
      quellen.push(text(quellKnoten[q]) + (url ? ' – ' + url : ''));
    }

    return {
      name: name,
      datum: datumFormat(heuteMittag()),
      eingaben: eingaben,
      ergebnis: ergebnisZeilen,
      hinweise: hinweise,
      formel: formel,
      annahmen: annahmen,
      quellen: quellen,
      versprechen: wurzel.getAttribute('data-versprechen') || '',
      herkunft: wurzel.getAttribute('data-herkunft') || 'franksfinanzcheck.de'
    };
  }

  function csvAusModell(modell) {
    var zeilen = [];
    zeilen.push([modell.name + ' – FranksFinanzcheck']);
    zeilen.push(['Stand', modell.datum]);
    zeilen.push(['Quelle', modell.herkunft]);
    zeilen.push([]);
    zeilen.push(['Eingaben', '']);
    modell.eingaben.forEach(function (e) { zeilen.push(e); });
    zeilen.push([]);
    zeilen.push(['Ergebnis', '']);
    modell.ergebnis.forEach(function (e) { zeilen.push(e); });
    if (modell.hinweise.length) {
      zeilen.push([]);
      zeilen.push(['Einordnung', '']);
      modell.hinweise.forEach(function (h) { zeilen.push([h]); });
    }
    if (modell.formel.length) {
      zeilen.push([]);
      zeilen.push(['Formel', '']);
      modell.formel.forEach(function (f) { zeilen.push([f]); });
    }
    if (modell.annahmen.length) {
      zeilen.push([]);
      zeilen.push(['Annahmen', '']);
      modell.annahmen.forEach(function (f) { zeilen.push([f]); });
    }
    if (modell.quellen.length) {
      zeilen.push([]);
      zeilen.push(['Quellen', '']);
      modell.quellen.forEach(function (f) { zeilen.push([f]); });
    }
    if (modell.versprechen) {
      zeilen.push([]);
      zeilen.push([modell.versprechen]);
    }
    return alsCsv(zeilen);
  }

  function pdfAusModell(modell) {
    var abschnitte = [];
    if (modell.eingaben.length) abschnitte.push({ titel: 'Deine Eingaben', zeilen: modell.eingaben });
    if (modell.ergebnis.length) abschnitte.push({ titel: 'Ergebnis', zeilen: modell.ergebnis });
    if (modell.hinweise.length) abschnitte.push({ titel: 'Einordnung', absaetze: modell.hinweise });
    if (modell.formel.length) abschnitte.push({ titel: 'So wird gerechnet', absaetze: modell.formel });
    if (modell.annahmen.length) abschnitte.push({ titel: 'Annahmen und Grenzen', absaetze: modell.annahmen });
    if (modell.quellen.length) abschnitte.push({ titel: 'Quellen', absaetze: modell.quellen });
    return alsPdf({
      titel: modell.name,
      untertitel: 'FranksFinanzcheck · Stand ' + modell.datum + ' · ' + modell.herkunft,
      abschnitte: abschnitte,
      fusszeile: modell.versprechen
    });
  }

  // =================================================================
  // 6. SPEICHER (nur nach Opt-in)
  // =================================================================

  function speicherSchluessel(id) {
    return SPEICHER_PRAEFIX + id + SPEICHER_VERSION;
  }

  function speicherLesen(fenster, id) {
    try {
      var roh = fenster.localStorage.getItem(speicherSchluessel(id));
      return roh ? JSON.parse(roh) : null;
    } catch (e) { return null; }
  }

  function speicherSchreiben(fenster, id, daten) {
    try {
      fenster.localStorage.setItem(speicherSchluessel(id), JSON.stringify(daten));
      return true;
    } catch (e) { return false; }
  }

  function speicherLoeschen(fenster, id) {
    try { fenster.localStorage.removeItem(speicherSchluessel(id)); } catch (e) { /* egal */ }
  }

  // =================================================================
  // 7. VERDRAHTUNG
  // =================================================================

  function verdrahte(wurzel, fenster) {
    var dok = wurzel.ownerDocument;
    var id = wurzel.getAttribute('data-werkzeug') || 'werkzeug';
    var engine = wurzel.getAttribute('data-engine');
    var rechner = logik[engine];
    if (typeof rechner !== 'function') return;

    var form = wurzel.querySelector('form');
    var merken = wurzel.querySelector('[data-ff-wz-speichern]');
    var zuruecksetzen = wurzel.querySelector('[data-ff-wz-reset]');
    var letztes = null;
    var gerechnet = false;

    function sammeln() { return felderLesen(wurzel); }

    function speichern() {
      if (!merken || !merken.checked) return;
      var daten = {};
      sammeln().forEach(function (f) { if (f.wert !== '') daten[f.id] = f.wert; });
      speicherSchreiben(fenster, id, daten);
    }

    function rechne(fokus) {
      var felder = sammeln();
      var ergebnis;
      try {
        ergebnis = rechner(felder, { heute: new Date() });
      } catch (e) {
        ergebnis = fehlt(['eine gültige Eingabe (die Rechnung ist abgebrochen)']);
      }
      zeichneErgebnis(wurzel, ergebnis, dok);
      if (ergebnis && !ergebnis.fehler) {
        letztes = { felder: felder, ergebnis: ergebnis };
        gerechnet = true;
      } else {
        letztes = null;
        if (fokus) {
          var erstes = wurzel.querySelector('[data-pflicht]');
          if (erstes && typeof erstes.focus === 'function') erstes.focus();
        }
      }
      speichern();
      return ergebnis;
    }

    if (form) {
      form.addEventListener('submit', function (ereignis) {
        ereignis.preventDefault();
        rechne(true);
      });
      form.addEventListener('input', function () {
        if (gerechnet) rechne(false);
        else speichern();
      });
      form.addEventListener('change', function () {
        if (gerechnet) rechne(false);
        else speichern();
      });
    }

    if (zuruecksetzen) {
      zuruecksetzen.addEventListener('click', function () {
        var felder = sammeln();
        felder.forEach(function (f) {
          var standard = f.element.getAttribute('data-standard');
          if (f.element.tagName === 'SELECT') {
            for (var i = 0; i < f.element.options.length; i++) {
              f.element.options[i].selected = standard
                ? f.element.options[i].value === standard
                : i === 0;
            }
          } else {
            f.element.value = standard || '';
          }
        });
        gerechnet = false;
        letztes = null;
        var ausgabe = wurzel.querySelector('[data-ff-wz-ausgabe]');
        var leerText = wurzel.querySelector('[data-ff-wz-leer]');
        var fehlerBox = wurzel.querySelector('[data-ff-wz-fehler]');
        if (ausgabe) ausgabe.hidden = true;
        if (fehlerBox) { leere(fehlerBox); fehlerBox.hidden = true; }
        if (leerText) leerText.hidden = false;
        if (merken) merken.checked = false;
        speicherLoeschen(fenster, id);
      });
    }

    if (merken) {
      merken.addEventListener('change', function () {
        if (merken.checked) speichern();
        else speicherLoeschen(fenster, id);
      });
      var gespeichert = speicherLesen(fenster, id);
      if (gespeichert && typeof gespeichert === 'object') {
        var treffer = false;
        sammeln().forEach(function (f) {
          if (Object.prototype.hasOwnProperty.call(gespeichert, f.id)) {
            f.element.value = String(gespeichert[f.id]);
            treffer = true;
          }
        });
        if (treffer) {
          merken.checked = true;
          rechne(false);
        }
      }
    }

    var exportKnoten = wurzel.querySelectorAll('[data-ff-wz-export-format]');
    for (var e = 0; e < exportKnoten.length; e++) {
      (function (knopf) {
        knopf.addEventListener('click', function () {
          var stand = letztes || (function () {
            var ergebnis = rechne(true);
            return ergebnis && !ergebnis.fehler ? { felder: sammeln(), ergebnis: ergebnis } : null;
          })();
          if (!stand) return;
          var format = knopf.getAttribute('data-ff-wz-export-format');
          var modell = exportModell(wurzel, stand.felder, stand.ergebnis);
          var praefix = wurzel.getAttribute('data-dateipraefix') || 'franksfinanzcheck';
          if (format === 'csv') {
            herunterladen(csvAusModell(modell), dateiname(praefix, id, 'csv'), 'text/csv;charset=utf-8', dok);
          } else if (format === 'pdf') {
            herunterladen(pdfAusModell(modell), dateiname(praefix, id, 'pdf'), 'application/pdf', dok);
          } else if (format === 'ics') {
            var termine = stand.ergebnis.termine || [];
            if (!termine.length) return;
            herunterladen(alsIcs(termine), dateiname(praefix, id, 'ics'), 'text/calendar;charset=utf-8', dok);
          }
        });
      })(exportKnoten[e]);
    }
  }

  function start(dok, fenster) {
    var knoten = dok.querySelectorAll('[data-ff-werkzeug]');
    for (var i = 0; i < knoten.length; i++) verdrahte(knoten[i], fenster);
  }

  var api = {
    logik: logik,
    hilfen: {
      zahl: zahl, euro: euro, nummer: nummer, prozent: prozent,
      datumLesen: datumLesen, datumFormat: datumFormat, iso: iso,
      monatePlus: monatePlus, tagePlus: tagePlus, dauerText: dauerText
    },
    exporte: {
      csv: alsCsv, pdf: alsPdf, ics: alsIcs,
      csvAusModell: csvAusModell, pdfAusModell: pdfAusModell, modell: exportModell
    },
    felderLesen: felderLesen,
    start: start
  };

  if (typeof globalThis !== 'undefined') globalThis.FFWerkzeuge = api;
  else if (typeof window !== 'undefined') window.FFWerkzeuge = api;

  if (typeof document !== 'undefined') {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function () { start(document, window); });
    } else {
      start(document, window);
    }
  }
})();
