/* FranksFinanzcheck — Kurzfassungs-Safety-Netz
   Entfernt ausschließlich sichtbare Markdown-/URL-Restsyntax aus dem Summary-Dialog.
   Der Inhalt wird dabei nicht neu verlinkt und Rechtszeichen wie § bleiben erhalten.
*/
(function () {
  'use strict';

  function cleanMarkdownText(value) {
    var out = String(value || '');
    for (var pass = 0; pass < 6; pass++) {
      var before = out;
      out = out.replace(/!\[([^\[\]]*)\]\((?:[^()]|\([^()]*\))*\)/g, '$1');
      out = out.replace(/\[([^\[\]]+)\]\((?:[^()]|\([^()]*\))*\)/g, '$1');
      if (out === before) break;
    }
    out = out.replace(/\]\((?:[^()]|\([^()]*\))*\)/g, '');
    out = out.replace(/[\[\]]/g, '');
    out = out.replace(/https?:\/\/[^\s<>\"')]+/gi, '');
    return out.replace(/\s+/g, ' ').trim();
  }

  function sanitizeDialog(dialog) {
    if (!dialog) return;
    var walker = document.createTreeWalker(dialog, NodeFilter.SHOW_TEXT);
    var node;
    while ((node = walker.nextNode())) {
      var raw = node.nodeValue || '';
      if (!/\[\[|\]\(|\[[^\]]*\]\(|https?:\/\//i.test(raw)) continue;
      var cleaned = cleanMarkdownText(raw);
      if (cleaned !== raw.trim()) {
        var leading = raw.match(/^\s*/)[0];
        var trailing = raw.match(/\s*$/)[0];
        node.nodeValue = leading + cleaned + trailing;
      }
    }
  }

  /* Letztes Sicherheitsnetz gegen ANKERRESTE (Befund 10.09.2026):
     Manche Erweiterungen hängen an Überschriften ein Symbol („§“, „#“).
     Steht es im Überschriften-Text, landet es im Inhaltsverzeichnis der
     Kurzfassung. Hier wird deshalb am ENDE jedes Verzeichnis-Eintrags
     ein angehängtes Ankersymbol entfernt. Ein echtes „§“ mitten im Text
     („Rechte aus § 8 EinSiG“) bleibt unangetastet.

     Härtung 10.09.2026 (Issue #248): Bestand der letzte Textknoten NUR
     aus dem Ankerrest (z. B. „Fazit “ + „§“ als eigene Knoten), blieb
     das „§“ stehen, weil die Kürzung einen nicht-leeren Rest verlangte.
     Jetzt fällt ein reiner Ankerrest-Knoten komplett weg und der
     vorangehende Knoten wird in einem zweiten Durchlauf nachgezogen. */
  function trimAnchorTrail(node) {
    if (!node || !document.createTreeWalker) return;
    for (var round = 0; round < 3; round++) {
      var walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT);
      var last = null;
      var current;
      while ((current = walker.nextNode())) last = current;
      if (!last) return;
      var raw = last.nodeValue || '';
      if (!/[\u00a7#]/.test(raw)) return; // kein Ankerrest mehr → fertig
      var cleaned = raw.replace(/[\s\u00a7#]+$/, '');
      if (cleaned === raw) return;        // endet nicht auf Ankerrest → Inhalt bleibt
      if (cleaned.length) { last.nodeValue = cleaned; return; }
      var parent = last.parentNode;       // Knoten ist reiner Ankerrest → entfernen
      if (parent) parent.removeChild(last);
    }
  }

  function cleanTocTrails(dialog) {
    if (!dialog || !dialog.querySelectorAll) return;
    var links = dialog.querySelectorAll('.ff-voice-toc a');
    for (var i = 0; i < links.length; i++) trimAnchorTrail(links[i]);
  }

  /* ---------- Härtung (Vertrag C31, 07.10.2026 – Robustheit Premium) ----------
     Dieses Netz ist das LETZTE seiner Kette: Fällt es aus, sieht der Leser
     Markdown-Reste in der Kurzfassung. Drei Ausfälle waren möglich, alle still:
       1. `document.body` fehlt (Skript läuft im <head> eines fremden
          Auslieferungswegs) → TypeError beim Beobachten, Netz tot.
       2. `MutationObserver` fehlt (alter Browser) → derselbe Abbruch.
       3. Eine Ausnahme IN einem Durchlauf (unerwarteter Knoten, gesperrtes
          DOM) beendete alle weiteren Durchläufe – das Netz riss, ohne dass
          irgendwo ein Befund stand.
     Jetzt: Fangnetz je Durchlauf, Anschluss erst mit vorhandenem Body, und
     ein Leistungsschalter, der nach drei Fehlern in Folge aufhört (ein
     Dauerläufer, der bei jeder Mutation wirft, kostet mehr als er schützt). */
  var FEHLER_LIMIT = 3;
  var fehlerFolge = 0;
  var beobachter = null;

  function melden(text) {
    try {
      if (window.FFRobust && window.FFRobust.melden) {
        window.FFRobust.melden({ quelle: 'kurzfassung-safety', text: text });
      }
    } catch (e) { /* die Wache darf nie selbst zur Fehlerquelle werden */ }
  }

  function run() {
    try {
      var dialog = document.getElementById('ff-voice-dialog');
      sanitizeDialog(dialog);
      cleanTocTrails(dialog);
      fehlerFolge = 0;
    } catch (fehler) {
      fehlerFolge += 1;
      melden(String((fehler && fehler.message) || fehler || '') + ' (Folge ' + fehlerFolge + ')');
      if (fehlerFolge >= FEHLER_LIMIT && beobachter && beobachter.disconnect) {
        beobachter.disconnect();
        beobachter = null;
        melden('nach ' + fehlerFolge + ' Fehlern abgeschaltet – der Dialog bleibt, wie er ist');
      }
    }
  }

  function anschliessen() {
    run();
    if (!document.body) return;                 /* kein Body → nichts zu beobachten */
    if (typeof MutationObserver !== 'function') return;  /* alter Browser: einmal ist einmal */
    try {
      beobachter = new MutationObserver(run);
      beobachter.observe(document.body, { childList: true, subtree: true });
    } catch (fehler) {
      melden('Beobachter nicht gestartet: ' + String((fehler && fehler.message) || fehler || ''));
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', anschliessen, { once: true });
  } else {
    anschliessen();
  }
}());
