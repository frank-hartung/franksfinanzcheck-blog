/*!
 * ff-feedback.js – „War dieser Ratgeber hilfreich?" (H4, 28.09.2026)
 * ============================================================
 * Erstkontakt: layouts/_partials/ff_feedback.html (rendert die Section
 * mit data-ff-feedback, data-endpoint, data-slug).
 *
 * WAS PASSIERT BEI KLICK:
 *   POST {endpoint} mit { slug, hilfreich: 'ja'|'nein' } – der eigene
 *   Newsletter-Worker (abos.franksfinanzcheck.de) zählt NUR aggregiert
 *   je Slug hoch (feedback:<slug> -> { ja, nein }). Keine Cookies, kein
 *   localStorage, kein Umami (Feedback soll unabhängig von der
 *   Analytics-Einwilligung funktionieren – Datenschutz by design).
 *
 * FEHLERVERTRAG:
 *   * Endpoint nicht erreichbar (z. B. Worker noch nicht neu deployt):
 *     Der Leser bekommt trotzdem ein Dankeschön – sein Klick war eine
 *     Geste, kein Vertrag. Still im catch (kein Konsolen-Spam).
 *   * Doppelklick / Reload + Klick: Der Worker dedupliziert über einen
 *     kurzen IP-Hash-Schlüssel (6 h) – hier zählt zusätzlich der
 *     lokale One-Shot-State (Buttons weg nach dem ersten Klick).
 *
 * KEIN ABHÄNGIGKEITS-VERTRAG: Vanilla JS, keine Frameworks, kein Build.
 */
(function () {
  'use strict';

  /* Härtung C31 (07.10.2026): `NodeList.forEach` gibt es nicht überall –
     fehlte es, starb der ganze Baustein, bevor ein Horcher stand. */
  var SEKTIONEN = [];
  try {
    SEKTIONEN = Array.prototype.slice.call(document.querySelectorAll('[data-ff-feedback]'));
  } catch (e) { return; }
  if (!SEKTIONEN.length) return;

  /* Zeitlimit für die Geste: `keepalive` hält die Anfrage sonst offen, bis
     der Browser sie vergisst. Der FEHLERVERTRAG oben bleibt unangetastet –
     ein nicht gespeichertes Feedback ist kein Befund, den jemand braucht. */
  function senden(endpoint, körper) {
    var optionen = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: körper,
      keepalive: true
    };
    var robust = window.FFRobust;
    if (robust && typeof robust.hole === 'function') {
      optionen.zeitlimit = 8000;
      return robust.hole(endpoint, optionen);
    }
    return window.fetch(endpoint, optionen).catch(function () { return null; });
  }

  function danke(sektion, text) {
    var knopfe = sektion.querySelector('.ff-feedback__knopfe');
    var dank = sektion.querySelector('.ff-feedback__dank');
    if (knopfe) knopfe.hidden = true;
    if (dank) dank.textContent = text;
  }

  Array.prototype.forEach.call(SEKTIONEN, function (sektion) {
    var endpoint = sektion.getAttribute('data-endpoint');
    var slug = sektion.getAttribute('data-slug');
    if (!endpoint || !slug) return;

    var knoepfe = [];
    try {
      knoepfe = Array.prototype.slice.call(sektion.querySelectorAll('[data-ff-feedback-wert]'));
    } catch (e) { return; }

    Array.prototype.forEach.call(knoepfe, function (knopf) {
      knopf.addEventListener('click', function () {
        var wert = knopf.getAttribute('data-ff-feedback-wert');
        /* Ein Klick zählt einmal: Doppelklicks verdoppelten die Geste. */
        if (knopf.dataset.ffFeedbackGesendet === '1') return;
        knopf.dataset.ffFeedbackGesendet = '1';
        danke(sektion, wert === 'ja'
          ? 'Danke! Dein Feedback hilft, die Ratgeber besser zu machen.'
          : 'Danke für die Rückmeldung – wir schauen uns den Ratgeber genauer an.');
        try {
          senden(endpoint, JSON.stringify({ slug: slug, hilfreich: wert }));
        } catch (e) { /* older browsers: still danken */ }
      });
    });
  });
})();
