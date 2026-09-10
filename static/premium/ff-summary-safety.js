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

  function run() {
    sanitizeDialog(document.getElementById('ff-voice-dialog'));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run, { once: true });
  } else {
    run();
  }
  new MutationObserver(run).observe(document.body, { childList: true, subtree: true });
}());
