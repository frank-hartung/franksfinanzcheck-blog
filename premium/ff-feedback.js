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

  var SEKTIONEN = document.querySelectorAll('[data-ff-feedback]');
  if (!SEKTIONEN.length) return;

  function danke(sektion, text) {
    var knopfe = sektion.querySelector('.ff-feedback__knopfe');
    var dank = sektion.querySelector('.ff-feedback__dank');
    if (knopfe) knopfe.hidden = true;
    if (dank) dank.textContent = text;
  }

  SEKTIONEN.forEach(function (sektion) {
    var endpoint = sektion.getAttribute('data-endpoint');
    var slug = sektion.getAttribute('data-slug');
    if (!endpoint || !slug) return;

    sektion.querySelectorAll('[data-ff-feedback-wert]').forEach(function (knopf) {
      knopf.addEventListener('click', function () {
        var wert = knopf.getAttribute('data-ff-feedback-wert');
        danke(sektion, wert === 'ja'
          ? 'Danke! Dein Feedback hilft, die Ratgeber besser zu machen.'
          : 'Danke für die Rückmeldung – wir schauen uns den Ratgeber genauer an.');
        try {
          fetch(endpoint, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Accept': 'application/json',
            },
            body: JSON.stringify({ slug: slug, hilfreich: wert }),
            keepalive: true,
          }).catch(function () { /* Geste zählt, Speichern ist optional */ });
        } catch (e) { /* older browsers: still danken */ }
      });
    });
  });
})();
