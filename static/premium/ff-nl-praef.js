/* ============================================================
   FF-NL-PRAEF – Themen-Picker der Präferenz-Seite (first-party,
   kein Tracking, keine fremde Domain im Code)
   ------------------------------------------------------------
   Der Picker auf /newsletter/praeferenzen/ ist eine Liste mit ECHTEN
   Auswahlkästchen. Diese Schicht gibt ihm drei ehrliche Zustände:

   1) VORSCHAU (kein Token in der Adresse): die Häkchen zählen live
      mit, und der Klick auf „zum Anmeldeformular“ übernimmt die
      Auswahl in die Anmeldung (localStorage `ff_nl_themen`;
      ff-newsletter.js setzt dort die Chips vor). Kein Versprechen
      jenseits dessen: Ohne Abo gibt es nichts zu speichern.
   2) DIREKT (Token in der Adresse – z. B. über den Vollversions-
      Link der Auswahl-Seite auf der Worker-Subdomain): die aktuelle
      Auswahl lädt der Worker (GET /status – der Token ist die
      einzige Legitimation, die Adresse geht nicht mit), und
      „Auswahl speichern“ schreibt sie (POST /praferenzen). Die
      Worker-Basis kommt aus dem DOM (data-basis, im Shortcode aus
      capture.form_action abgeleitet) – deshalb lädt dieses Skript
      keine einzige Domäne, die es selbst kennt.
   3) OHNE JAVASCRIPT: nichts hier ist aktiv – die <noscript>-Zeile
      des Shortcodes weist auf den Link im Fuß jeder Mail, der
      überall funktioniert.

   Die Statuszeile ist eine role=status-Region: jede Änderung wird
   angekündigt, und der reservierte Mindesthöhen-Slot (CSS) schiebt
   die Seite nicht (PRODUCT.md §6: CLS ≈ 0). Ein Fehler beendet nie
   die Seite: statt tot zu gehen, zeigt sie den direkten Weg.
   ============================================================ */
(function () {
  'use strict';

  var SPEICHER = 'ff_nl_themen';               // Hand-off Picker -> Anmeldeformular
  var TOKEN_RE = /^[A-Za-z0-9_-]{8,64}$/;      // Worker: 24-Zeichen-base64url, Puffer dazugegeben

  function token_lesen() {
    try {
      return String((new URLSearchParams(window.location.search).get('token')) || '').trim();
    } catch (e) {
      var m = window.location.search.match(/[?&]token=([^&]+)/);
      return m ? String(decodeURIComponent(m[1])).trim() : '';
    }
  }

  function praeferenzen() {
    var kasten = document.querySelector('fieldset[data-ff-nl-praef]');
    if (!kasten || kasten.dataset.ffNlPraefBereit === '1') return;
    kasten.dataset.ffNlPraefBereit = '1';

    var basis = String(kasten.getAttribute('data-basis') || '').replace(/\/+$/, '');
    var felder = Array.prototype.slice.call(
      kasten.querySelectorAll('input[type="checkbox"][name="themen"]'));
    var meldung = kasten.querySelector('[data-ff-nl-praef-status]');
    var aktion = kasten.querySelector('[data-ff-nl-praef-aktion]');
    var preview = kasten.querySelector('[data-ff-nl-praef-preview]');
    var speichern = kasten.querySelector('[data-ff-nl-praef-speichern]');
    if (!felder.length || !meldung) return;

    var gesamt = felder.length;
    var token = token_lesen();

    function ausgewaehlt() {
      return felder
        .filter(function (f) { return f.checked; })
        .map(function (f) { return f.value; });
    }

    function zaehler() {
      var n = ausgewaehlt().length;
      var text;
      if (n === 0) {
        text = 'Ohne Häkchen kommen alle ' + gesamt + ' Welten – aber nie mehr als zwei Mails pro Woche.';
      } else if (n === gesamt) {
        text = 'Alle ' + gesamt + ' Welten angehakt – das ist „alles“: höchstens zwei Mails pro Woche.';
      } else {
        text = 'Deine Auswahl: ' + n + ' von ' + gesamt + ' Welten – aus den anderen Welten kommt nichts in deine Mail.';
      }
      meldung.textContent = text;
    }

    function haken() {
      felder.forEach(function (f) { f.addEventListener('change', zaehler); });
    }

    /** Meldung setzten; optional einen Fallback-Link dahinterhängen
        (wenn der direkte Weg über das Netz gerade nicht geht). */
    function melden(tekst, ziel, linktext) {
      meldung.textContent = tekst;
      if (!ziel) return;
      var a = document.createElement('a');
      a.href = ziel;
      a.textContent = linktext;
      meldung.appendChild(document.createTextNode(' '));
      meldung.appendChild(a);
    }

    /** Zustand 1: Vorschau ohne Token. Der Link ist ein normales <a> –
        er funktioniert auch ohne dieses Skript; JS trägt nur die
        Auswahl mit (oder räumt sie ab, wenn nichts angehakt ist). */
    if (preview) {
      preview.addEventListener('click', function () {
        try {
          var liste = ausgewaehlt();
          if (liste.length) localStorage.setItem(SPEICHER, JSON.stringify(liste));
          else localStorage.removeItem(SPEICHER);
        } catch (e) { /* Privat-Modus: die Auswahl kommt nur im Tab an */ }
      });
    }

    /* Ohne Worker-Basis (Capture nicht geschaltet) oder ohne gültiges
       Token endet hier die Magie: der Picker bleibt eine ehrliche
       Liste mit Vorschau – kein Button, der nirgends anklopfen kann. */
    if (!basis || !speichern || !aktion || !TOKEN_RE.test(token)) {
      haken();
      zaehler();
      return;
    }

    var direkt = basis + '/praferenzen?token=' + encodeURIComponent(token);

    /* Zustand 2a: die aktuelle Auswahl laden (Token als Legitimation,
       Accept: application/json erzwingt die JSON-Antwort des Workers
       statt der HTML-Seite). */
    window.fetch(basis + '/status?token=' + encodeURIComponent(token), {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
      mode: 'cors',
      credentials: 'omit',
    }).then(function (antwort) {
      if (!antwort.ok) throw new Error(String(antwort.status));
      return antwort.json();
    }).then(function (daten) {
      var thesen = (daten && Array.isArray(daten.themen)) ? daten.themen : [];
      felder.forEach(function (f) { f.checked = thesen.indexOf(f.value) >= 0; });
      zaehler();
      var vorlage = (daten && daten.status === 'pending')
        ? 'Deine Anmeldung ist noch offen (Bestätigung läuft) – du kannst die Themen schon jetzt festlegen:'
        : 'Deine aktuelle Auswahl – Häkchen setzen, speichern, fertig: die Änderung gilt ab der nächsten Ausgabe.';
      melden(vorlage);
      if (preview) preview.setAttribute('hidden', '');
      speichern.removeAttribute('hidden');
    }).catch(function () {
      /* Netzwerk, CORS (z. B. getesteter Spiegel) oder unbekanntes
         Token: nichts ist geändert – und der servergerenderte Weg
         (funktioniert ohne JavaScript) bleibt einen Klick entfernt. */
      melden('Deine aktuelle Auswahl konnte ich gerade nicht laden – es wurde nichts geändert. Direkt ohne JavaScript:',
        direkt, 'die Auswahl-Seite');
      if (preview) preview.removeAttribute('hidden');
    });

    /* Zustand 2b: speichern. Der Worker antwortet mit einer
       Benutzer-Tabelle („Gespeichert: 3 Thema(n) …“) – wir drucken,
       was er sagt, und erfinden keinen eigenen Erfolg. */
    speichern.addEventListener('click', function () {
      if (speichern.disabled) return;
      speichern.disabled = true;
      kasten.removeAttribute('data-status');
      melden('Wird gespeichert …');
      var korper = ['token=' + encodeURIComponent(token)];
      ausgewaehlt().forEach(function (id) { korper.push('themen=' + encodeURIComponent(id)); });
      window.fetch(basis + '/praferenzen', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
          'Accept': 'application/json',
        },
        body: korper.join('&'),
        mode: 'cors',
        credentials: 'omit',
      }).then(function (antwort) {
        if (!antwort.ok) throw new Error(String(antwort.status));
        return antwort.json();
      }).then(function (daten) {
        kasten.dataset.status = 'ok';
        melden((daten && daten.text) ? daten.text : 'Gespeichert – die Auswahl gilt ab der nächsten Ausgabe.');
      }).catch(function () {
        kasten.dataset.status = 'fehler';
        melden('Die Änderung ist nicht durchgekommen – bitte erneut versuchen. Direkt ohne JavaScript:',
          direkt, 'die Auswahl-Seite');
        speichern.disabled = false;
      });
    });

    haken();
    zaehler();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', praeferenzen, { once: true });
  } else {
    praeferenzen();
  }
})();
