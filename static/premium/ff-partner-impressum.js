/*!
 * ff-partner-impressum.js – Höhe der Partner-Kennzeichnung
 * ============================================================
 * Erstkontakt: layouts/shortcodes/partner_impressum.html
 *
 * Das Partnerdokument ist eine fremde Herkunft. Die Höhe lässt sich
 * deshalb nicht auslesen. Das Skript hebt oder setzt die Höhe nur,
 * wenn das Dokument selbst eine plausible Höhe meldet. Ohne Meldung
 * bleibt die CSS-Höhe – der Rechtstext ist auch dann sichtbar.
 *
 * ZWEI-KLICK (Sicherheitsaudit 14.10.2026, N-07): Der Rahmen hat nur
 * data-src. Erst der Klick auf „Angaben des Partners laden“ setzt src –
 * vorher fließen keine Daten an den Partner.
 *
 * Kein eigener Netzwerkverkehr, kein Speicher, kein Tracking.
 */
(function () {
  'use strict';

  var frame = document.getElementById('ff-partner-impressum-frame');
  if (!frame || !window.addEventListener) return;

  var ORIGIN = 'https://a.partner-versicherung.de';

  var knopf = document.querySelector('[data-ff-partner-laden]');
  var vorschalt = document.querySelector('[data-ff-partner-vorschalt]');
  if (knopf) {
    knopf.addEventListener('click', function () {
      var ziel = frame.getAttribute('data-src') || '';
      if (ziel.indexOf(ORIGIN + '/') !== 0) return;
      frame.setAttribute('src', ziel);
      frame.hidden = false;
      if (vorschalt) vorschalt.hidden = true;
      try { frame.focus(); } catch (e) {}
    });
  }

  function apply(height) {
    var n = Number(height);
    if (!isFinite(n) || n < 400 || n > 2200) return;
    frame.style.height = Math.ceil(n + 12) + 'px';
  }

  function read(data) {
    if (typeof data === 'number') return data;
    if (typeof data === 'string' && /^\d{3,4}$/.test(data)) return Number(data);
    if (!data || typeof data !== 'object') return 0;
    return data.height || data.iframeHeight || data.h || 0;
  }

  window.addEventListener('message', function (event) {
    if (event.origin !== ORIGIN) return;
    if (frame.contentWindow && event.source && event.source !== frame.contentWindow) return;
    apply(read(event.data));
  });
})();
