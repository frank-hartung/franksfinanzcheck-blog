/* ============================================================
   FranksFinanzcheck – Premium Lesehilfen (Vorlesen + Kurzfassung)
   03.09.2026
   ------------------------------------------------------------
   Privacy-first, first-party: Die Web Speech API läuft lokal im
   Browser (keine Datenübertragung, kein Tracking, keine Cookies).
   Die Kurzfassung wird clientseitig aus dem bereits ausgelieferten
   Artikeltext erzeugt – kein Server-Roundtrip.

   Rendert nur, wenn die Toolbar (layouts/_partials/reader_toolbar.html)
   vorhanden ist. Styling: assets/css/extended/ff-reader.css
============================================================ */
(function () {
  'use strict';

  var doc = document;
  var win = window;

  var cfgEl = doc.getElementById('ff-reader-config');
  if (!cfgEl) return;

  var cfg = {};
  try { cfg = JSON.parse(cfgEl.textContent || '{}') || {}; } catch (e) { cfg = {}; }

  var toolbar = doc.getElementById('ff-reader-toolbar');
  var listenBtn = doc.getElementById('ff-listen-btn');
  var listenLabel = doc.getElementById('ff-listen-label');
  var listenIcon = listenBtn ? listenBtn.querySelector('.ff-reader-btn__icon') : null;
  var stopBtn = doc.getElementById('ff-listen-stop');
  var summaryBtn = doc.getElementById('ff-summary-btn');
  var statusEl = doc.getElementById('ff-reader-status');
  var progressBar = doc.getElementById('ff-reader-progress-bar');
  if (!toolbar || !listenBtn || !summaryBtn) return;

  var reducedMotion = !!(win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)').matches);

  /* ---------- Allgemeine Hilfsfunktionen ---------- */

  function qsa(sel, ctx) { return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel)); }

  function stripMd(s) {
    return String(s == null ? '' : s)
      .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
      .replace(/[*_`~]+/g, '')
      .replace(/\u00a0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  // Text eines Elements ohne Deko-Knoten (Kopier-Button "§", Anker "#" usw.).
  function readableText(el) {
    if (!el) return '';
    var clone = el.cloneNode(true);
    qsa('script, style, noscript, .ff-heading-copy, .anchor, [aria-hidden="true"], .ff-reader-toolbar', clone)
      .forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
    return (clone.textContent || '')
      .replace(/\u00a0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  // Satz-Splitter ohne Lookbehind (kompatibel mit älteren Engines).
  function sentences(text) {
    return String(text)
      .replace(/([.!?…]+)(["'»)\]]*)(\s+|$)/g, '$1$2\u0001')
      .split('\u0001')
      .map(function (s) { return s.trim(); })
      .filter(function (s) { return s.length > 1; });
  }

  function firstSentences(text, n) { return sentences(text).slice(0, n).join(' '); }

  // Scroll-Helfer, der in jeder Umgebung (auch ohne scrollIntoView) sicher ist.
  function scrollTo(el, opts) {
    if (!el || typeof el.scrollIntoView !== 'function') return;
    try { el.scrollIntoView(opts); }
    catch (e) { try { el.scrollIntoView(); } catch (e2) { /* ignorieren */ } }
  }

  /* ============================================================
     1) VORLESEN – Web Speech API
  ============================================================ */

  var synth = win.speechSynthesis || null;
  var speechSupported = !!(synth && typeof win.SpeechSynthesisUtterance === 'function');
  var germanVoice = null;
  var reading = false;   // Sitzung aktiv (spielt oder pausiert)
  var playing = false;   // erzeugt gerade Audio
  var blocks = [];       // vorlesbare Absätze/Überschriften/Listenpunkte
  var blockIndex = 0;
  var keepAliveId = null;

  var SPEAKER_SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor"><path d="M12 14a3 3 0 0 0 3-3V5a3 3 0 0 0-6 0v6a3 3 0 0 0 3 3Z"/><path d="M19 11a1 1 0 1 0-2 0 5 5 0 0 1-10 0 1 1 0 1 0-2 0 7 7 0 0 0 6 6.92V20H8a1 1 0 1 0 0 2h8a1 1 0 1 0 0-2h-3v-2.08A7 7 0 0 0 19 11Z"/></svg>';
  var EQ_HTML = '<span class="ff-eq" aria-hidden="true"><i></i><i></i><i></i></span>';

  function setStatus(msg) { if (statusEl) statusEl.textContent = msg || ''; }

  function setListenState(state) {
    var isActive = state !== 'idle';
    if (toolbar.classList) {
      toolbar.classList.toggle('ff-reader-toolbar--active', isActive);
      toolbar.classList.toggle('ff-reader-toolbar--playing', state === 'playing');
    }
    listenBtn.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    if (listenIcon) {
      if (state === 'playing') {
        if (!listenIcon.querySelector('.ff-eq')) listenIcon.innerHTML = EQ_HTML;
      } else if (!listenIcon.querySelector('svg')) {
        listenIcon.innerHTML = SPEAKER_SVG;
      }
    }
    if (state === 'idle') {
      listenLabel.textContent = 'Vorlesen';
      listenBtn.setAttribute('aria-label', 'Artikel vorlesen');
    } else if (state === 'playing') {
      listenLabel.textContent = 'Pausieren';
      listenBtn.setAttribute('aria-label', 'Vorlesen pausieren');
    } else {
      listenLabel.textContent = 'Weiterlesen';
      listenBtn.setAttribute('aria-label', 'Vorlesen fortsetzen');
    }
  }

  function pickGermanVoice() {
    if (!speechSupported) return null;
    var list = synth.getVoices() || [];
    var de = list.filter(function (v) { return /^de([-_]|$)/i.test(v.lang || ''); });
    if (!de.length) return null;
    var deDE = de.filter(function (v) { return /^de[-_]de$/i.test(v.lang); });
    var pool = deDE.length ? deDE : de;
    var preferred = pool.filter(function (v) { return /google|natural|wavenet|neural/i.test(v.name || ''); });
    if (!preferred.length) {
      preferred = pool.filter(function (v) { return /anna|katja|hedda|vicki|petra|marlene|ingrid|conrad|stefan/i.test(v.name || ''); });
    }
    return preferred[0] || pool[0];
  }

  function collectBlocks() {
    var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
    if (!content) return [];
    var out = [];
    qsa('h2, h3, p, li', content).forEach(function (el) {
      if (el.closest && el.closest('table, figure, script, style, noscript, [aria-hidden="true"], [data-ff-skip-read]')) return;
      if (readableText(el).length < 2) return;
      out.push(el);
    });
    return out;
  }

  function highlight(el) {
    blocks.forEach(function (b) { if (b !== el) b.classList.remove('ff-reader-active'); });
    if (!el) return;
    el.classList.add('ff-reader-active');
    if (progressBar) {
      var total = Math.max(1, blocks.length);
      progressBar.style.width = (((blockIndex + 1) / total) * 100).toFixed(1) + '%';
    }
    if (!reducedMotion) scrollTo(el, { block: 'center', behavior: 'smooth' });
  }

  function clearHighlight() {
    blocks.forEach(function (b) { b.classList.remove('ff-reader-active'); });
    if (progressBar) progressBar.style.width = '0%';
  }

  function speakBlock(index) {
    if (!reading || !speechSupported) return;
    if (index >= blocks.length) { endReading(true); return; }
    blockIndex = index;
    var el = blocks[index];
    highlight(el);
    var u = new win.SpeechSynthesisUtterance(readableText(el));
    u.lang = (germanVoice && germanVoice.lang) || 'de-DE';
    if (germanVoice) u.voice = germanVoice;
    u.rate = 0.95;
    u.pitch = 1;
    u.onend = function () { if (reading && playing) speakBlock(blockIndex + 1); };
    u.onerror = function (e) {
      if (!reading) return;
      if (e && (e.error === 'interrupted' || e.error === 'canceled')) return;
      // Nicht-blockierende Fehler (z. B. "not-allowed"): nicht hängen bleiben.
      if (playing) speakBlock(blockIndex + 1);
    };
    synth.speak(u);
  }

  function startReading() {
    if (!speechSupported) {
      setStatus('Vorlesen wird von deinem Browser nicht unterstützt.');
      return;
    }
    if (!germanVoice) germanVoice = pickGermanVoice();
    blocks = collectBlocks();
    if (!blocks.length) { setStatus('Kein vorlesbarer Text gefunden.'); return; }
    reading = true;
    playing = true;
    blockIndex = 0;
    setListenState('playing');
    setStatus('Vorlesen gestartet.');
    startKeepAlive();
    speakBlock(0);
  }

  function pauseReading() {
    if (!reading) return;
    playing = false;
    if (speechSupported) synth.pause();
    setListenState('paused');
    setStatus('Vorlesen pausiert.');
  }

  function resumeReading() {
    if (!reading) return;
    playing = true;
    if (speechSupported) synth.resume();
    setListenState('playing');
    setStatus('Vorlesen fortgesetzt.');
  }

  function endReading(announce) {
    reading = false;
    playing = false;
    stopKeepAlive();
    if (speechSupported) { try { synth.cancel(); } catch (e) {} }
    clearHighlight();
    setListenState('idle');
    if (announce) setStatus('Vorlesen beendet.');
  }

  function startKeepAlive() {
    stopKeepAlive();
    if (!speechSupported) return;
    // Chrome pausiert lange Sprachausgaben gelegentlich selbständig – sanft nachhelfen.
    keepAliveId = setInterval(function () {
      if (reading && playing) { try { synth.resume(); } catch (e) {} }
    }, 7000);
  }

  function stopKeepAlive() {
    if (keepAliveId) { clearInterval(keepAliveId); keepAliveId = null; }
  }

  listenBtn.addEventListener('click', function () {
    if (!reading) startReading();
    else if (playing) pauseReading();
    else resumeReading();
  });

  if (stopBtn) stopBtn.addEventListener('click', function () { endReading(true); });

  if (speechSupported) {
    germanVoice = pickGermanVoice();
    if (typeof synth.onvoiceschanged !== 'undefined') {
      synth.onvoiceschanged = function () { germanVoice = pickGermanVoice(); };
    }
  }

  // Beim Verlassen der Seite nicht in den nächsten Artikel hineinlesen.
  win.addEventListener('pagehide', function () { if (reading) endReading(false); });

  /* ============================================================
     2) KURZFASSUNG – redaktionell strukturierter Dialog
  ============================================================ */

  var dialog = null;
  var summaryCopyText = '';

  function extractNumbers(content) {
    var out = [];
    var seen = {};
    qsa('p, li', content).forEach(function (el) {
      if (el.closest && el.closest('table, figure, [data-ff-skip-read]')) return;
      var text = readableText(el);
      if (!/[€%]/.test(text)) return;
      sentences(text).forEach(function (s) {
        if (out.length >= 4) return;
        if (!/[€%]/.test(s)) return;
        if (s.length < 20 || s.length > 220) return;
        var key = s.toLowerCase();
        if (seen[key]) return;
        seen[key] = true;
        out.push(s);
      });
    });
    return out;
  }

  function buildSections(content) {
    var sections = [];
    qsa('h2[id]', content).forEach(function (h) {
      var title = readableText(h);
      if (!title) return;
      var lead = '';
      var next = h.nextElementSibling;
      while (next && next.tagName !== 'H2') {
        if (next.tagName === 'P' || next.tagName === 'H3') {
          var t = readableText(next);
          if (t) { lead = firstSentences(t, 1); break; }
        }
        next = next.nextElementSibling;
      }
      sections.push({ id: h.id, title: title, lead: lead });
    });
    return sections;
  }

  function buildSummaryData() {
    var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
    var sections = content ? buildSections(content) : [];
    var numbers = content ? extractNumbers(content) : [];
    var short = stripMd(cfg.kurzantwort || cfg.description || '');
    if (!short && content) {
      var firstP = qsa('p', content)[0];
      if (firstP) short = firstSentences(readableText(firstP), 2);
    }
    return { short: short, sections: sections, numbers: numbers };
  }

  function buildPlainText(data) {
    var lines = [];
    lines.push('KURZFASSUNG: ' + (stripMd(cfg.title) || doc.title));
    lines.push('');
    if (data.short) { lines.push('Das Wichtigste in 30 Sekunden:'); lines.push(data.short); lines.push(''); }
    if (data.sections.length) {
      lines.push('Die Kernaussagen:');
      data.sections.forEach(function (s) { lines.push('- ' + s.title + (s.lead ? ' — ' + s.lead : '')); });
      lines.push('');
    }
    if (data.numbers.length) {
      lines.push('Auf einen Blick – die wichtigsten Zahlen:');
      data.numbers.forEach(function (n) { lines.push('- ' + n); });
      lines.push('');
    }
    lines.push('Lesezeit: ca. ' + (cfg.readingTime || '?') + ' Min. · ' + (cfg.wordCount || '?') + ' Wörter');
    lines.push('Quelle: ' + win.location.href);
    return lines.join('\n');
  }

  function el(tag, cls, text) {
    var e = doc.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  function copyText(text, cb) {
    function fallback() {
      try {
        var ta = doc.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.opacity = '0';
        doc.body.appendChild(ta);
        ta.select();
        var ok = doc.execCommand('copy');
        doc.body.removeChild(ta);
        if (cb) cb(!!ok);
      } catch (e) { if (cb) cb(false); }
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () { if (cb) cb(true); }, fallback);
    } else {
      fallback();
    }
  }

  function buildDialog() {
    if (dialog) return dialog;

    var data = buildSummaryData();
    summaryCopyText = buildPlainText(data);

    dialog = doc.createElement('dialog');
    dialog.className = 'ff-summary';
    dialog.id = 'ff-summary-dialog';
    dialog.setAttribute('aria-labelledby', 'ff-summary-title');

    var card = el('div', 'ff-summary__card');

    var header = el('header', 'ff-summary__header');
    var headText = el('div', 'ff-summary__head-text');
    headText.appendChild(el('p', 'ff-summary__eyebrow', 'Kurzfassung'));
    var title = el('h2', 'ff-summary__title', stripMd(cfg.title) || doc.title);
    title.id = 'ff-summary-title';
    headText.appendChild(title);
    header.appendChild(headText);
    var closeBtn = el('button', 'ff-summary__close');
    closeBtn.type = 'button';
    closeBtn.setAttribute('aria-label', 'Kurzfassung schließen');
    closeBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    header.appendChild(closeBtn);

    var body = el('div', 'ff-summary__body');
    var metaParts = [];
    if (cfg.readingTime) metaParts.push('⏱️ ca. ' + cfg.readingTime + ' Min. Lesezeit');
    if (cfg.wordCount) metaParts.push(cfg.wordCount + ' Wörter');
    if (data.sections.length) metaParts.push(data.sections.length + ' Abschnitte');
    if (metaParts.length) body.appendChild(el('div', 'ff-summary__meta', metaParts.join(' · ')));

    if (data.short) {
      var s1 = el('section', 'ff-summary__section');
      s1.appendChild(el('h3', null, '💡 Das Wichtigste in 30 Sekunden'));
      s1.appendChild(el('p', null, data.short));
      body.appendChild(s1);
    }

    if (data.sections.length) {
      var s2 = el('section', 'ff-summary__section');
      s2.appendChild(el('h3', null, '📌 Die Kernaussagen'));
      var ol = el('ol');
      data.sections.forEach(function (s) {
        var li = el('li');
        var a = el('a', null, s.title);
        a.href = '#' + s.id;
        li.appendChild(a);
        if (s.lead) li.appendChild(doc.createTextNode(' — ' + s.lead));
        ol.appendChild(li);
      });
      s2.appendChild(ol);
      body.appendChild(s2);
    }

    if (data.numbers.length) {
      var s3 = el('section', 'ff-summary__section');
      s3.appendChild(el('h3', null, '💶 Auf einen Blick – die wichtigsten Zahlen'));
      var ul = el('ul');
      data.numbers.forEach(function (n) { ul.appendChild(el('li', null, n)); });
      s3.appendChild(ul);
      body.appendChild(s3);
    }

    var footer = el('footer', 'ff-summary__footer');
    var copyBtn = el('button', 'ff-summary__btn');
    copyBtn.type = 'button';
    copyBtn.id = 'ff-summary-copy';
    copyBtn.textContent = '📋 Kurzfassung kopieren';
    var readBtn = el('button', 'ff-summary__btn ff-summary__btn--primary');
    readBtn.type = 'button';
    readBtn.id = 'ff-summary-read';
    readBtn.textContent = 'Ganzen Artikel lesen →';
    footer.appendChild(copyBtn);
    footer.appendChild(readBtn);

    card.appendChild(header);
    card.appendChild(body);
    card.appendChild(footer);
    dialog.appendChild(card);

    closeBtn.addEventListener('click', closeDialog);

    copyBtn.addEventListener('click', function () {
      copyText(summaryCopyText, function (ok) {
        copyBtn.textContent = ok ? '✓ Kopiert' : 'Kopieren fehlgeschlagen';
        setTimeout(function () { copyBtn.textContent = '📋 Kurzfassung kopieren'; }, 1600);
      });
    });

    readBtn.addEventListener('click', function () {
      closeDialog();
      var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
      if (content) scrollTo(content, { behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
    });

    // Klick auf die Dialog-Rückseite (Backdrop) schließt den Dialog.
    dialog.addEventListener('click', function (e) {
      if (e.target === dialog) closeDialog();
    });

    // Abschnitts-Links schließen den Dialog und springen zum Ziel.
    body.addEventListener('click', function (e) {
      var a = e.target && e.target.closest ? e.target.closest('a[href^="#"]') : null;
      if (!a) return;
      e.preventDefault();
      var id = a.getAttribute('href').slice(1);
      closeDialog();
      var target = doc.getElementById(id);
      if (target) scrollTo(target, { behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
    });

    doc.body.appendChild(dialog);
    return dialog;
  }

  function openDialog() {
    buildDialog();
    if (typeof dialog.showModal === 'function') {
      dialog.showModal();
    } else {
      // Fallback für sehr alte Browser ohne <dialog>.showModal
      dialog.setAttribute('open', '');
      dialog.classList.add('ff-summary--fallback');
      addFallbackBackdrop();
    }
    var closeBtn = dialog.querySelector('.ff-summary__close');
    if (closeBtn) closeBtn.focus();
  }

  function closeDialog() {
    if (!dialog) return;
    if (typeof dialog.close === 'function') {
      dialog.close();
    } else {
      dialog.removeAttribute('open');
      dialog.classList.remove('ff-summary--fallback');
      removeFallbackBackdrop();
    }
    if (summaryBtn) summaryBtn.focus();
  }

  var fallbackBackdrop = null;
  function addFallbackBackdrop() {
    if (fallbackBackdrop) return;
    fallbackBackdrop = el('div', 'ff-summary-backdrop');
    fallbackBackdrop.addEventListener('click', closeDialog);
    doc.body.appendChild(fallbackBackdrop);
  }
  function removeFallbackBackdrop() {
    if (fallbackBackdrop && fallbackBackdrop.parentNode) fallbackBackdrop.parentNode.removeChild(fallbackBackdrop);
    fallbackBackdrop = null;
  }

  summaryBtn.addEventListener('click', openDialog);

  doc.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && dialog && dialog.classList.contains('ff-summary--fallback')) {
      closeDialog();
    }
  });
})();
