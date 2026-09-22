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
   ============================================================ */
(function () {
  'use strict';

  var SCHLUESSEL = 'ff_nl';                 // localStorage: angemeldet | bestaetigt
  var selector = 'form[data-ff-nl]';

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

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bereiten, { once: true });
  } else {
    bereiten();
  }
})();
