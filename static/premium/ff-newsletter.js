/* ============================================================
   FF-NEWSLETTER – Anmeldeformular ohne Backend (first-party, kein Tracking)
   ------------------------------------------------------------
   Warum überhaupt JavaScript? Das Formular muss ohne JS funktionieren (es
   POSTet dann direkt zum Anbieter) – diese Schicht ergänzt nur, was ein
   Agentur-Formaus ausmacht:
     1) Vorher prüfen statt hinterher hoffen: E-Mail-Format, Einwilligung.
     2) Auf dem Blatt bleiben: der Versand läuft als Fetch in denselben
        Tab, der Leser wird nicht zum Anbieterportal weitergereicht.
     3) Bot-Falle: Zeitstempel beim Rendern, Honigtopf beim Ausfüllen.
        Beides ersetzt einen Captcha-Dienst (kein Drittanbieter, kein Cookie,
        keine DSGVO-Angabe) und kostet 0 Euro.
     4) Merken, dass jemand schon angemeldet ist – ein zweiter Anmelde-Kasten
        auf derselben Seite ist Lärm, kein Service.

   Kein Framework, kein Fetch-Vertrauen: Der Anbieter antwortet cross-origin,
   das Ergebnis ist opaque. Deshalb meldet diese Schiebt NIEMALS „erfolgreich
   abonniert“, sondern nur „Bestätigungsmail ausgelöst“ – der zweite Klick
   gehört dem Double-Opt-In, und das kann diese Seite nicht sehen.

     5) Versandplan: den nächsten Termin RECHNEN, statt ihn zu drucken. Ein
        statisch gebauter Termin ist am Tag nach dem Bau falsch – eine
        Landingpage, die gestern ankündigt, bricht dasselbe Versprechen, das
        sie verkauft. Gerechnet wird in Europe/Berlin (Intl), weil der Versand
        dort getaktet ist und nicht in der Zeitzone des Lesers. Ohne
        verlässliche Zeitzone bleibt der kadenzrichtige Satz ohne Datum stehen.
   ============================================================ */
(function () {
  'use strict';

  var SCHLUESSEL = 'ff_nl';                 // localStorage: angemeldet | bestaetigt
  var AUSWAHL = 'ff_nl_themen';             // Auswahl der Präferenz-Seite (ff-nl-praef.js)
  var selector = 'form[data-ff-nl]';
  var ZONE = 'Europe/Berlin';               // Taktzone des Versandvertrags

  function bereiten() {
    var form = document.querySelector(selector);
    if (!form || form.dataset.ffNlBereit === '1') return;
    form.dataset.ffNlBereit = '1';

    var start = Date.now();
    var zeit = form.querySelector('[data-ff-nl-zeit]');
    if (zeit) zeit.value = String(start);

    var feld = form.querySelector('input[type="email"], input[name="email"]');
    var fall = form.querySelector('[data-ff-nl-falle]');
    var consent = form.querySelector('input[name="consent"]');
    var status = document.getElementById('ff-nl-status');
    var button = form.querySelector('button[type="submit"]');
    var bereits = false;
    try { bereits = localStorage.getItem(SCHLUESSEL) === 'angemeldet'; } catch (e) { bereits = false; }

    /* Auswahl von der Präferenz-Seite: Wer dort Welten anhakt und auf
       „zum Anmeldeformular“ geht, sieht die Häkchen hier VORgesetzt –
       die Anmeldung übernimmt sie als Startwert. Alles bleibt frei
       änderbar; das ist eine Vorgabe, kein Schloss. */
    var vorgabe = [];
    try { vorgabe = JSON.parse(localStorage.getItem(AUSWAHL) || '[]') || []; } catch (e) { vorgabe = []; }
    if (vorgabe.length) {
      Array.prototype.forEach.call(
        form.querySelectorAll('input[type="checkbox"][name^="themen"]'),
        function (k) { if (vorgabe.indexOf(k.value) >= 0) k.checked = true; });
    }

    function setzen(zustand, tekst) {
      form.dataset.status = zustand;
      if (status && tekst) status.textContent = tekst;
    }

    function fehler(tekst) {
      form.dataset.status = 'fehler';
      if (status) status.textContent = tekst;
      if (feld) feld.focus();
    }

    function gültig() {
      if (!feld || !feld.value || feld.value.indexOf('@') < 1) {
        fehler('Ohne gültige E-Mail-Adresse geht nichts – bitte Adresse prüfen.');
        return false;
      }
      if (consent && !consent.checked) {
        form.dataset.status = 'fehler';
        if (status) {
          status.textContent = 'Es fehlt die Einwilligung. Ohne das Häkchen dürfen wir ' +
            'keine Mail schicken – sie ist in einem Satz erklärt und jederzeit widerrufbar.';
        }
        if (consent) consent.focus();
        return false;
      }
      return true;
    }

    form.addEventListener('submit', function (ereignis) {
      // Kein Fetch verfügbar? Dann übernimmt der Browser den echten POST.
      if (!window.fetch) return;
      var gefüllt = fall && String(fall.value || '').length > 0;
      if (gefüllt) {
        // Die Bot-Falle: absichtlich ohne Begründung abbrechen – ein Angreifer
        // lernt aus der Rückmeldung mehr als aus dem Schweigen.
        ereignis.preventDefault();
        form.dataset.status = 'ok';
        if (status) status.textContent = 'Danke – bitte sieh in dein Postfach.';
        return;
      }
      // Die Zeitfalle wird NUR übermittelt, hier aber nie gegen einen Menschen
      // gekehrt: wer ein Formular in 1,2 Sekunden ausfüllt, ist nicht verdächtig,
      // sondern schnell. Ein Client, der deshalb still „Danke“ spielt, würde
      // zahlende Anmeldungen vernichten – und das im Ungewissen. Der Empfänger
      // (bzw. eine spätere Serverseite) kann `_zeit` immer noch auswerten.
      if (!gültig()) {
        ereignis.preventDefault();
        return;
      }
      ereignis.preventDefault();
      senden();
    });

    function senden() {
      var ziel = form.getAttribute('action');
      var daten = new FormData(form);
      var körper = [];
      daten.forEach(function (wert, schlüssel) {
        if (wert === '' && schlüssel !== 'consent') return;
        körper.push(encodeURIComponent(schlüssel) + '=' + encodeURIComponent(wert));
      });
      if (button) button.disabled = true;
      setzen('sendet', 'Wird übermittelt …');
      window.fetch(ziel, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8' },
        body: körper.join('&'),
        mode: 'no-cors',
        credentials: 'omit',
        keepalive: true
      }).then(function () {
        try { localStorage.setItem(SCHLUESSEL, 'angemeldet'); } catch (e) { /* privat-Modus */ }
        document.documentElement.setAttribute('data-ff-nl', 'angemeldet');
        setzen('ok', 'Bestätigungsmail ausgelöst. Sie kommt in den nächsten Minuten – ' +
          'falls nicht, sieh im Spam-Ordner nach und melde dich kurz auf ' +
          'kontakt@franksfinanzcheck.de. Erst mit deinem Klick auf den Link darin ' +
          '(Double-Opt-In) stehst du auf der Liste.');
        if (feld) feld.value = '';
        if (consent) consent.checked = false;
        Array.prototype.forEach.call(
          form.querySelectorAll('input[type="checkbox"][name^="themen"]'),
          function (k) { k.checked = false; });
        /* Die Auswahl hat ihren Zweck erfüllt – sonst klebte sie als
           stiller Startwert an jeder späteren Wiederanmeldung. */
        try { localStorage.removeItem(AUSWAHL); } catch (e) { /* Privat-Modus */ }
      }).catch(function () {
        if (button) button.disabled = false;
        form.dataset.status = 'fehler';
        if (status) {
          status.textContent = 'Die Übermittlung ist nicht durchgekommen – das liegt an der ' +
            'Verbindung, nicht an dir. Bitte erneut versuchen, oder melde dich direkt über ' +
            'kontakt@franksfinanzcheck.de an.';
        }
      });
    }

    if (bereits) document.documentElement.setAttribute('data-ff-nl', 'angemeldet');
  }

  /* ---------- Versandplan: Termine rechnen statt raten ----------
     Die Kacheln zeigen den Takt (Dienstag / Freitag) als Tatsache und den
     nächsten Termin als Rechnung. Beide Werte kommen aus dem DOM, das der
     Versandplan-Baustein aus data/newsletter_kadenz.json gebaut hat – hier
     steht kein Wochentag und keine Uhrzeit im Code. */

  function zweistellig(wert) {
    return (wert < 10 ? '0' : '') + wert;
  }

  /** Wanduhr in Europe/Berlin – oder null, wenn die Zeitzone nicht auflösbar ist. */
  function berlinJetzt() {
    if (typeof Intl === 'undefined' || !Intl.DateTimeFormat) return null;
    try {
      var fmt = new Intl.DateTimeFormat('de-DE', {
        timeZone: ZONE,
        hour12: false,
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit'
      });
      if (fmt.resolvedOptions().timeZone !== ZONE) return null;
      var teile = {};
      fmt.formatToParts(new Date()).forEach(function (teil) {
        teile[teil.type] = teil.value;
      });
      var jahr = Number(teile.year);
      var monat = Number(teile.month);
      var tag = Number(teile.day);
      if (!jahr || !monat || !tag) return null;
      return {
        jahr: jahr,
        monat: monat,
        tag: tag,
        stunde: Number(teile.hour) % 24,      // manche Engines liefern „24“ um Mitternacht
        minute: Number(teile.minute),
        // Date#getDay(): 0 = Sonntag – der Vertrag zählt Montag = 0 (Python weekday()).
        wochentag: (new Date(Date.UTC(jahr, monat - 1, tag)).getUTCDay() + 6) % 7
      };
    } catch (e) {
      return null;
    }
  }

  /**
   * Der nächste Termin aus `tage` (Wochentagsnummern). Der heutige Tag zählt
   * nur, solange die Versanduhrzeit noch nicht erreicht ist – „heute“ ist ein
   * Fakt, kein Versprechen, das der Double-Opt-In noch kippen kann.
   */
  function naechster(heute, tage, uhrzeit) {
    var teile = String(uhrzeit || '06:30').split(':');
    var stunde = Number(teile[0]) || 0;
    var minute = Number(teile[1]) || 0;
    var vorVersand = heute.stunde < stunde ||
      (heute.stunde === stunde && heute.minute < minute);
    var schritt = 0;
    if (!(vorVersand && tage.indexOf(heute.wochentag) >= 0)) {
      schritt = 1;
      while (schritt < 8 && tage.indexOf((heute.wochentag + schritt) % 7) < 0) {
        schritt += 1;
      }
    }
    var datum = new Date(Date.UTC(heute.jahr, heute.monat - 1, heute.tag + schritt));
    return {
      jahr: datum.getUTCFullYear(),
      monat: datum.getUTCMonth() + 1,
      tag: datum.getUTCDate(),
      wochentag: (datum.getUTCDay() + 6) % 7
    };
  }

  /** „Freitag, 26. September“ – deutsche Namen über die Locale, nicht über den Browser. */
  function lang(termin) {
    try {
      var fmt = new Intl.DateTimeFormat('de-DE', {
        timeZone: ZONE, weekday: 'long', day: 'numeric', month: 'long'
      });
      if (fmt.resolvedOptions().timeZone !== ZONE) return '';
      return fmt.format(
        new Date(Date.UTC(termin.jahr, termin.monat - 1, termin.tag, 12))
      ).trim();
    } catch (e) {
      return '';
    }
  }

  function versandplan() {
    var plan = document.querySelector('[data-ff-nl-plan]');
    if (!plan || plan.getAttribute('data-ff-nl-plan') === 'bereit') return;
    var heute = berlinJetzt();
    if (!heute) return;                     // ohne Zeitzone: Satz ohne Datum, aber richtig
    var tage = String(plan.getAttribute('data-ff-nl-tage') || '')
      .split(',')
      .map(function (wert) { return Number(wert); })
      .filter(function (wert) { return wert >= 0 && wert <= 6; });
    if (!tage.length) return;
    plan.setAttribute('data-ff-nl-plan', 'bereit');

    var uhrzeit = plan.getAttribute('data-ff-nl-uhrzeit') || '06:30';
    var kacheln = plan.querySelectorAll('[data-ff-nl-tag]');
    Array.prototype.forEach.call(kacheln, function (kachel) {
      var nummer = Number(kachel.getAttribute('data-ff-nl-tag'));
      if (!(nummer >= 0 && nummer <= 6)) return;
      var termin = naechster(heute, [nummer], uhrzeit);
      var feld = kachel.querySelector('[data-ff-nl-termin]');
      if (feld) {
        var kurz = kachel.getAttribute('data-ff-nl-tag-kurz') || '';
        feld.textContent = (kurz ? kurz + ', ' : '') +
          zweistellig(termin.tag) + '.' + zweistellig(termin.monat) + '.';
      }
      if (termin.tag === heute.tag && termin.monat === heute.monat &&
          termin.jahr === heute.jahr) {
        kachel.classList.add('ff-nl__plan-tag--heute');
      }
    });

    var erster = plan.querySelector('[data-ff-nl-erster]');
    if (erster) {
      var text = lang(naechster(heute, tage, uhrzeit));
      if (text) erster.textContent = text;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      bereiten();
      versandplan();
    }, { once: true });
  } else {
    bereiten();
    versandplan();
  }
})();
