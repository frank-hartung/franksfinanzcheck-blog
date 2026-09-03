/* ============================================================
   FranksFinanzcheck – Premium Lesehilfen (Vorlesen + Kurzfassung)
   03.09.2026 — Profi-Agentur & Chefredakteur-Standard
   ------------------------------------------------------------
   - Privacy-first & First-party: Web Speech API lokal im Browser.
   - Männliche Stimme mit sonorer, redaktioneller Timbre-Optimierung.
   - Vollautomatische Mehrsprachigkeit: Deutsch (DE) und Englisch (EN)
     ohne manuellen Umschalter.
   - Maximale Barrierefreiheit (WCAG 2.2 AAA / BITV) für Fließtext,
     Überschriften, Listen sowie Tabellen & Übersichten mit
     zeilengenauer Live-Synchronisation und Vorlese-Kontext.
   - Robuste Browser-Kompatibilität & automatische Keep-Alive-Wache.
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
  var summaryLabel = doc.getElementById('ff-summary-label');
  var statusEl = doc.getElementById('ff-reader-status');
  var progressBar = doc.getElementById('ff-reader-progress-bar');
  if (!toolbar || !listenBtn || !summaryBtn) return;

  var reducedMotion = !!(win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)').matches);

  /* ---------- I18N Lokalisierung (DE & EN) ---------- */
  var I18N = {
    de: {
      listen: 'Vorlesen',
      pause: 'Pausieren',
      resume: 'Weiterlesen',
      stop: 'Beenden',
      listenAria: 'Artikel vorlesen (männliche Stimme)',
      pauseAria: 'Vorlesen pausieren',
      resumeAria: 'Vorlesen fortsetzen',
      stopAria: 'Vorlesen beenden',
      summaryBtn: 'Kurzfassung',
      summaryAria: 'Kurzfassung des Artikels anzeigen',
      unsupported: 'Vorlesen wird von deinem Browser nicht unterstützt.',
      noText: 'Kein vorlesbarer Text gefunden.',
      started: 'Vorlesen gestartet.',
      paused: 'Vorlesen pausiert.',
      resumed: 'Vorlesen fortgesetzt.',
      finished: 'Vorlesen beendet.',
      tableTitleDefault: 'Übersichtstabelle',
      tableIntro: 'Tabelle: {title}. Übersicht mit {cols} Spalten und {rows} Zeilen.',
      tableRow: 'Zeile {row}: {content}.',
      column: 'Spalte',
      row: 'Zeile',
      summaryEyebrow: 'Kurzfassung',
      summaryQuick30: '💡 Das Wichtigste in 30 Sekunden',
      summaryKeypoints: '📌 Die Kernaussagen',
      summaryNumbers: '💶 Auf einen Blick – die wichtigsten Zahlen',
      summaryTables: '📊 Tabellen & Übersichten im Fokus',
      summaryCopy: '📋 Kurzfassung kopieren',
      summaryCopied: '✓ Kopiert',
      summaryCopyFail: 'Kopieren fehlgeschlagen',
      summaryReadFull: 'Ganzen Artikel lesen →',
      summaryClose: 'Kurzfassung schließen',
      readingTime: '⏱️ ca. {time} Min. Lesezeit',
      wordCount: '{count} Wörter',
      sectionCount: '{count} Abschnitte',
      source: 'Quelle: '
    },
    en: {
      listen: 'Listen',
      pause: 'Pause',
      resume: 'Resume',
      stop: 'Stop',
      listenAria: 'Read article aloud (male voice)',
      pauseAria: 'Pause speech',
      resumeAria: 'Resume speech',
      stopAria: 'Stop speech',
      summaryBtn: 'Summary',
      summaryAria: 'Show article summary',
      unsupported: 'Speech synthesis is not supported by your browser.',
      noText: 'No readable text found.',
      started: 'Audio playback started.',
      paused: 'Audio playback paused.',
      resumed: 'Audio playback resumed.',
      finished: 'Audio playback completed.',
      tableTitleDefault: 'Overview Table',
      tableIntro: 'Table: {title}. Overview with {cols} columns and {rows} rows.',
      tableRow: 'Row {row}: {content}.',
      column: 'Column',
      row: 'Row',
      summaryEyebrow: 'Summary',
      summaryQuick30: '💡 Key Takeaways in 30 Seconds',
      summaryKeypoints: '📌 Key Highlights',
      summaryNumbers: '💶 Key Figures & Data',
      summaryTables: '📊 Tables & Overviews in Focus',
      summaryCopy: '📋 Copy summary',
      summaryCopied: '✓ Copied',
      summaryCopyFail: 'Copy failed',
      summaryReadFull: 'Read full article →',
      summaryClose: 'Close summary',
      readingTime: '⏱️ approx. {time} min read',
      wordCount: '{count} words',
      sectionCount: '{count} sections',
      source: 'Source: '
    }
  };

  /* ---------- Automatische Spracherkennung (DE / EN) ---------- */
  function detectArticleLanguage() {
    var raw = (cfg.lang || toolbar.getAttribute('data-page-lang') || doc.documentElement.lang || 'de').toLowerCase();
    if (raw.indexOf('en') === 0) return 'en';
    if (raw.indexOf('de') === 0) return 'de';

    // Heuristik bei gemischtem/internationalem Content
    var sample = (cfg.title || '') + ' ' + (cfg.description || '') + ' ' + (doc.body ? doc.body.innerText.slice(0, 1000) : '');
    var enMatches = (sample.match(/\b(the|and|is|for|with|that|save|money|guide|table|insurance)\b/gi) || []).length;
    var deMatches = (sample.match(/\b(und|der|die|das|ist|für|mit|sparen|euro|ratgeber|tabelle|versicherung)\b/gi) || []).length;
    return enMatches > deMatches ? 'en' : 'de';
  }

  var currentLang = detectArticleLanguage();
  var texts = I18N[currentLang] || I18N.de;

  // Initiale UI-Labels
  if (listenLabel) listenLabel.textContent = texts.listen;
  if (listenBtn) listenBtn.setAttribute('aria-label', texts.listenAria);
  if (summaryLabel) summaryLabel.textContent = texts.summaryBtn;
  if (summaryBtn) summaryBtn.setAttribute('aria-label', texts.summaryAria);

  /* ---------- Allgemeine Hilfsfunktionen ---------- */

  function qsa(sel, ctx) { return Array.prototype.slice.call((ctx || doc).querySelectorAll(sel)); }

  function stripMd(s) {
    return String(s == null ? '' : s)
      .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
      .replace(/[*_`~#]+/g, '')
      .replace(/\u00a0/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

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

  /* ---------- Redaktionelle Lautschrift- & Aussprache-Optimierung ---------- */
  function speechNormalize(text, lang) {
    if (!text) return '';
    var s = ' ' + text + ' ';
    s = s.replace(/\u00a0/g, ' ');

    if (lang === 'en') {
      // Währungen & Zahlenbereiche Englisch
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(?:€|EUR|Euro)/gi, '$1 to $2 Euros');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*\$/g, '$1 to $2 Dollars');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*%/g, '$1 to $2 percent');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)/g, '$1 to $2');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*(?:€|EUR|Euro)/gi, '$1 Euros');
      s = s.replace(/\$\s*(\d+(?:[.,]\d+)?)/g, '$1 Dollars');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*%/g, '$1 percent');
      s = s.replace(/\b(\d+)\s*(?:Cent|ct)\b/gi, '$1 Cents');
      s = s.replace(/\b(?:Cent|ct)\/kWh\b/gi, 'Cents per kilowatt hour');
      s = s.replace(/\b(?:kWh|kwh)\b/g, 'kilowatt hours');
      s = s.replace(/\b(?:Mbit\/s|MBit\/s|Mbit)\b/g, 'megabits per second');
      s = s.replace(/\b(?:Gbit\/s|GBit\/s|Gbit)\b/g, 'gigabits per second');
      s = s.replace(/\b(?:m²|sqm)\b/gi, 'square meters');
      s = s.replace(/\b(?:p\.a\.|per year|\/year)\b/gi, 'per year');
      s = s.replace(/\b(?:per month|\/month)\b/gi, 'per month');
      s = s.replace(/\be\.g\.\b/gi, 'for example');
      s = s.replace(/\bi\.e\.\b/gi, 'that is');
      s = s.replace(/\bapprox\.\b/gi, 'approximately');
      s = s.replace(/\bincl\.\b/gi, 'including');
      s = s.replace(/\bexcl\.\b/gi, 'excluding');
      s = s.replace(/\bvs\.?\b/gi, 'versus');
      s = s.replace(/\bmin\.\b/gi, 'minimum');
      s = s.replace(/\bmax\.\b/gi, 'maximum');
    } else {
      // Währungen & Zahlenbereiche Deutsch (Chefredakteur-Standard)
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(?:€|EUR|Euro)/gi, '$1 bis $2 Euro');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(?:Cent|ct)/gi, '$1 bis $2 Cent');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*%/g, '$1 bis $2 Prozent');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)/g, '$1 bis $2');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*(?:€|EUR|Euro)/gi, '$1 Euro');
      s = s.replace(/(?:€|EUR)\s*(\d+(?:[.,]\d+)?)/gi, '$1 Euro');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*%/g, '$1 Prozent');
      s = s.replace(/\b(\d+)\s*(?:Cent|ct)\b/gi, '$1 Cent');
      s = s.replace(/\b(?:Cent|ct)\/kWh\b/gi, 'Cent pro Kilowattstunde');
      s = s.replace(/\b(?:kWh|kwh)\b/g, 'Kilowattstunden');
      s = s.replace(/\b(?:Mbit\/s|MBit\/s|Mbit)\b/g, 'Megabit pro Sekunde');
      s = s.replace(/\b(?:Gbit\/s|GBit\/s|Gbit)\b/g, 'Gigabit pro Sekunde');
      s = s.replace(/\b(?:m²|qm)\b/gi, 'Quadratmeter');
      s = s.replace(/\b(?:p\.a\.|pro Jahr|\/Jahr)\b/gi, 'pro Jahr');
      s = s.replace(/\b(?:mtl\.|\/Monat|pro Monat)\b/gi, 'monatlich');
      s = s.replace(/\b(?:jährl\.)\b/gi, 'jährlich');

      // Abkürzungen Deutsch
      s = s.replace(/\bz\.\s*B\.\b|\bz\.B\.\b/gi, 'zum Beispiel');
      s = s.replace(/\bd\.\s*h\.\b|\bd\.h\.\b/gi, 'das heißt');
      s = s.replace(/\bu\.\s*a\.\b|\bu\.a\.\b/gi, 'unter anderem');
      s = s.replace(/\bbzw\.\b/gi, 'beziehungsweise');
      s = s.replace(/\bca\.\b/gi, 'circa');
      s = s.replace(/\binkl\.\b/gi, 'inklusive');
      s = s.replace(/\bexkl\.\b/gi, 'exklusive');
      s = s.replace(/\bggf\.\b/gi, 'gegebenenfalls');
      s = s.replace(/\bevtl\.\b/gi, 'eventuell');
      s = s.replace(/\bmind\.\b/gi, 'mindestens');
      s = s.replace(/\bmax\.\b/gi, 'maximal');
      s = s.replace(/\bbspw\.\b/gi, 'beispielsweise');
      s = s.replace(/\bAbs\.\b/g, 'Absatz');
      s = s.replace(/\bArt\.\b/g, 'Artikel');
      s = s.replace(/\bNr\.\b/g, 'Nummer');
      s = s.replace(/\bvs\.?\b/gi, 'versus');
    }

    // Barrierefreie Aussprache von Indikatoren / Emojis
    s = s.replace(/🔴/g, lang === 'en' ? 'High Priority: ' : 'Pflicht: ');
    s = s.replace(/🟡/g, lang === 'en' ? 'Medium Priority: ' : 'Sehr sinnvoll: ');
    s = s.replace(/🟢/g, lang === 'en' ? 'Optional: ' : 'Optional: ');
    s = s.replace(/⚪/g, lang === 'en' ? 'Usually unnecessary: ' : 'Meist überflüssig: ');
    s = s.replace(/💡/g, lang === 'en' ? 'Tip: ' : 'Tipp: ');
    s = s.replace(/⚠/g, lang === 'en' ? 'Warning: ' : 'Wichtiger Hinweis: ');
    s = s.replace(/ℹ/g, lang === 'en' ? 'Note: ' : 'Hinweis: ');

    // Dekorative Icons & Markdown-Sonderzeichen bereinigen
    s = s.replace(/[⏱️📅✍️📚💶💰🛡️⚡🚗🌱🌐💳📈📋✓🔧★⭐]/g, '');
    s = s.replace(/[*_`~#|]+/g, ' ');
    s = s.replace(/\s+/g, ' ').trim();
    return s;
  }

  function sentences(text) {
    return String(text || '')
      .replace(/([.!?…]+)(["'»)\]]*)(\s+|$)/g, '$1$2\u0001')
      .split('\u0001')
      .map(function (s) { return s.trim(); })
      .filter(function (s) { return s.length > 1; });
  }

  function firstSentences(text, n) { return sentences(text).slice(0, n).join(' '); }

  function scrollTo(el, opts) {
    if (!el || typeof el.scrollIntoView !== 'function') return;
    try { el.scrollIntoView(opts); }
    catch (e) { try { el.scrollIntoView(); } catch (e2) {} }
  }

  /* ============================================================
     1) VORLESEN – Web Speech API mit Männlicher Stimme
  ============================================================ */

  var synth = win.speechSynthesis || null;
  var speechSupported = !!(synth && typeof win.SpeechSynthesisUtterance === 'function');
  var maleVoice = null;
  var reading = false;
  var playing = false;
  var blocks = [];       // Array von { el, text, lang, type, isTable }
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
      listenLabel.textContent = texts.listen;
      listenBtn.setAttribute('aria-label', texts.listenAria);
    } else if (state === 'playing') {
      listenLabel.textContent = texts.pause;
      listenBtn.setAttribute('aria-label', texts.pauseAria);
    } else {
      listenLabel.textContent = texts.resume;
      listenBtn.setAttribute('aria-label', texts.resumeAria);
    }
  }

  /* ---------- Männliche Stimmen-Auswahl-Engine (DE & EN) ---------- */
  function pickMaleVoice(lang) {
    if (!speechSupported) return null;
    var list = synth.getVoices() || [];
    if (!list.length) return null;

    var targetLang = (lang || currentLang || 'de').toLowerCase();
    var langPattern = targetLang.indexOf('en') === 0 ? /^en([-_]|$)/i : /^de([-_]|$)/i;
    var candidates = list.filter(function (v) { return langPattern.test(v.lang || ''); });
    if (!candidates.length) candidates = list; // Fallback

    var maleKeywords = targetLang.indexOf('en') === 0
      ? ['david', 'george', 'guy', 'mark', 'ryan', 'daniel', 'oliver', 'arthur', 'thomas', 'james', 'alex', 'fred', 'aaron', 'brian', 'eric', 'richard', 'tom', 'john', 'paul', 'michael', 'peter', 'frank', 'en_us_male', 'en_gb_male', 'male', 'man', '#male', 'neural2-a', 'neural2-d', 'neural2-j', 'wavenet-a', 'wavenet-b', 'wavenet-d', 'wavenet-j', 'standard-b', 'standard-d']
      : ['stefan', 'conrad', 'florian', 'bernd', 'christoph', 'ralf', 'klaus', 'markus', 'jonas', 'martin', 'yannick', 'hans', 'viktor', 'thorsten', 'de_de_male', 'de-de-x-deg#male', 'de-de-x-deb#male', 'de-de-x-dea#male', 'male', 'männlich', 'mann', '#male', 'neural2-b', 'neural2-d', 'wavenet-b', 'wavenet-d', 'standard-b', 'standard-d'];

    var femaleKeywords = [
      'anna', 'katja', 'hedda', 'vicki', 'petra', 'marlene', 'ingrid', 'zira', 'hazel', 'samantha', 'victoria',
      'karen', 'susan', 'jenny', 'helena', 'eva', 'gisela', 'luisa', 'maja', 'elke', 'steffi', 'catherine',
      'linda', 'heather', 'amy', 'emma', 'olivia', 'joanna', 'kendra', 'cortana', 'female', 'weiblich', 'frau',
      'woman', 'girl', '#female', 'siri female'
    ];

    var premiumKeywords = ['natural', 'neural', 'wavenet', 'google', 'online', 'enhanced', 'premium', 'siri', 'pro', 'highquality'];

    function scoreVoice(v) {
      var score = 0;
      var name = (v.name || '').toLowerCase();
      var uri = (v.voiceURI || '').toLowerCase();
      var langStr = (v.lang || '').toLowerCase();

      // Sprach-Präzision
      if (targetLang.indexOf('en') === 0) {
        if (langStr === 'en-us' || langStr === 'en-gb') score += 50;
        else if (langPattern.test(langStr)) score += 30;
      } else {
        if (langStr === 'de-de') score += 50;
        else if (langPattern.test(langStr)) score += 30;
      }

      // Männliche Stimme Priorität (+120)
      for (var i = 0; i < maleKeywords.length; i++) {
        if (name.indexOf(maleKeywords[i]) !== -1 || uri.indexOf(maleKeywords[i]) !== -1) {
          score += 120;
          break;
        }
      }

      // Weibliche Stimmen stark abwerten (-180)
      for (var j = 0; j < femaleKeywords.length; j++) {
        if (name.indexOf(femaleKeywords[j]) !== -1 || uri.indexOf(femaleKeywords[j]) !== -1) {
          score -= 180;
          break;
        }
      }

      // Natürliche/Neuronale Premium-Engine (+35)
      for (var k = 0; k < premiumKeywords.length; k++) {
        if (name.indexOf(premiumKeywords[k]) !== -1 || uri.indexOf(premiumKeywords[k]) !== -1) {
          score += 35;
          break;
        }
      }

      if (v.localService) score += 10;
      return score;
    }

    candidates.sort(function (a, b) { return scoreVoice(b) - scoreVoice(a); });
    return candidates[0] || null;
  }

  /* ---------- Tabellen-Daten-Extraktion (Maximum Barrierefreiheit) ---------- */
  function extractTableSpeechBlocks(tableEl, lang) {
    if (!tableEl) return [];
    var tTexts = I18N[lang] || I18N.de;

    // Tabellen-Titel/Kontext ermitteln (vorherige Überschrift, Caption oder aria-label)
    var title = tableEl.getAttribute('aria-label') || '';
    if (!title) {
      var caption = tableEl.querySelector('caption');
      if (caption) title = readableText(caption);
    }
    if (!title) {
      var prev = tableEl.previousElementSibling;
      while (prev && !/^H[1-6]$/.test(prev.tagName)) {
        if (prev.classList && prev.classList.contains('ff-table-scroll')) break;
        prev = prev.previousElementSibling;
      }
      if (prev && /^H[1-6]$/.test(prev.tagName)) title = readableText(prev);
    }
    if (!title) title = tTexts.tableTitleDefault;

    // Spaltenüberschriften sammeln
    var headers = [];
    var ths = qsa('thead th', tableEl);
    if (!ths.length) ths = qsa('tr:first-child th, tr:first-child td', tableEl);
    ths.forEach(function (th) {
      var hText = readableText(th);
      if (hText) headers.push(hText);
    });

    // Daten-Zeilen sammeln
    var rows = qsa('tbody tr', tableEl);
    if (!rows.length) {
      var allTrs = qsa('tr', tableEl);
      rows = allTrs.length > 1 ? allTrs.slice(1) : allTrs;
    }

    var tableBlocks = [];
    var colCount = Math.max(headers.length, 1);
    var rowCount = rows.length;

    // 1. Tabellen-Intro-Block
    var introRaw = tTexts.tableIntro
      .replace('{title}', title)
      .replace('{cols}', colCount)
      .replace('{rows}', rowCount);
    var introEl = tableEl.closest('.ff-table-scroll') || tableEl;
    tableBlocks.push({
      el: introEl,
      text: speechNormalize(introRaw, lang),
      lang: lang,
      type: 'table-intro'
    });

    // 2. Einzelne Zeilen mit Spalten-Zuordnung
    rows.forEach(function (tr, rIdx) {
      if (tr.closest('[data-ff-skip-read]')) return;
      var cells = qsa('td, th', tr);
      if (!cells.length) return;

      var cellStatements = [];
      cells.forEach(function (cell, cIdx) {
        var cellVal = readableText(cell);
        if (!cellVal) return;
        var headerName = headers[cIdx] || (tTexts.column + ' ' + (cIdx + 1));
        cellStatements.push(headerName + ': ' + cellVal);
      });

      if (!cellStatements.length) return;

      var rowRaw = tTexts.tableRow
        .replace('{row}', (rIdx + 1))
        .replace('{content}', cellStatements.join('; '));

      tableBlocks.push({
        el: tr,
        text: speechNormalize(rowRaw, lang),
        lang: lang,
        type: 'table-row'
      });
    });

    return tableBlocks;
  }

  /* ---------- Alle vorlesbaren Blöcke im Artikel sammeln ---------- */
  function collectBlocks() {
    var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
    if (!content) return [];
    var lang = detectArticleLanguage();
    var out = [];
    var processedTables = [];

    // Alle relevanten Elemente in DOM-Reihenfolge durchgehen
    var nodes = qsa('h2, h3, h4, p, li, table, .ff-table-scroll, .ff-tarif-card, .ff-einspar-box, .ff-kurzantwort, .ff-korrektur, .callout', content);

    nodes.forEach(function (el) {
      if (el.closest && el.closest('figure, script, style, noscript, [aria-hidden="true"], [data-ff-skip-read]')) return;

      // Element-Sprache berücksichtigen
      var elLang = (el.getAttribute('lang') || lang).toLowerCase().indexOf('en') === 0 ? 'en' : 'de';

      // Tabellen & Scroll-Wrapper
      if (el.tagName === 'TABLE' || (el.classList && el.classList.contains('ff-table-scroll'))) {
        var tbl = el.tagName === 'TABLE' ? el : el.querySelector('table');
        if (!tbl || processedTables.indexOf(tbl) !== -1) return;
        processedTables.push(tbl);
        var tBlocks = extractTableSpeechBlocks(tbl, elLang);
        tBlocks.forEach(function (tb) { out.push(tb); });
        return;
      }

      // Paragraphen / Listenpunkte innerhalb von Tabellen überspringen (wurden strukturiert erfasst)
      if (el.closest && el.closest('table, .ff-table-scroll')) return;

      // Tarif-Karten / Vergleichs-Boxen
      if (el.classList && (el.classList.contains('ff-tarif-card') || el.classList.contains('ff-einspar-box'))) {
        var cardText = readableText(el);
        if (cardText.length > 5) {
          out.push({
            el: el,
            text: speechNormalize(cardText, elLang),
            lang: elLang,
            type: 'overview-card'
          });
        }
        return;
      }

      // Callout-Boxen / Kurzantwort / Korrektur
      if (el.classList && (el.classList.contains('ff-kurzantwort') || el.classList.contains('ff-korrektur') || el.classList.contains('callout'))) {
        var calloutText = readableText(el);
        if (calloutText.length > 5) {
          out.push({
            el: el,
            text: speechNormalize(calloutText, elLang),
            lang: elLang,
            type: 'callout'
          });
        }
        return;
      }

      // Standard-Fließtext (Überschriften, Absätze, Listenpunkte)
      var text = readableText(el);
      if (text.length < 2) return;

      // Nur Absätze/Listenpunkte erfassen, die nicht Kind eines bereits erfassten Callouts sind
      if (el.closest && el.closest('.ff-kurzantwort, .ff-korrektur, .callout, .ff-tarif-card, .ff-einspar-box')) return;

      out.push({
        el: el,
        text: speechNormalize(text, elLang),
        lang: elLang,
        type: el.tagName.toLowerCase()
      });
    });

    return out;
  }

  function highlight(block) {
    blocks.forEach(function (b) { if (b.el && b.el !== block.el) b.el.classList.remove('ff-reader-active'); });
    if (!block || !block.el) return;
    block.el.classList.add('ff-reader-active');
    if (progressBar) {
      var total = Math.max(1, blocks.length);
      progressBar.style.width = (((blockIndex + 1) / total) * 100).toFixed(1) + '%';
    }
    if (!reducedMotion) scrollTo(block.el, { block: 'center', behavior: 'smooth' });
  }

  function clearHighlight() {
    blocks.forEach(function (b) { if (b.el) b.el.classList.remove('ff-reader-active'); });
    if (progressBar) progressBar.style.width = '0%';
  }

  function speakBlock(index) {
    if (!reading || !speechSupported) return;
    if (index >= blocks.length) { endReading(true); return; }
    blockIndex = index;
    var b = blocks[index];
    highlight(b);

    var bLang = b.lang || currentLang;
    var voice = pickMaleVoice(bLang);

    var u = new win.SpeechSynthesisUtterance(b.text);
    u.lang = bLang === 'en' ? 'en-US' : 'de-DE';
    if (voice) u.voice = voice;
    u.pitch = 0.95; // Männliche, sonore, redaktionelle Tonhöhe
    u.rate = 0.96;  // Ausgewogenes Tempo für Zahlen & Tabellen

    u.onend = function () { if (reading && playing) speakBlock(blockIndex + 1); };
    u.onerror = function (e) {
      if (!reading) return;
      if (e && (e.error === 'interrupted' || e.error === 'canceled')) return;
      if (playing) speakBlock(blockIndex + 1);
    };
    synth.speak(u);
  }

  function startReading() {
    if (!speechSupported) {
      setStatus(texts.unsupported);
      return;
    }
    currentLang = detectArticleLanguage();
    texts = I18N[currentLang] || I18N.de;
    maleVoice = pickMaleVoice(currentLang);

    blocks = collectBlocks();
    if (!blocks.length) { setStatus(texts.noText); return; }

    reading = true;
    playing = true;
    blockIndex = 0;
    setListenState('playing');
    setStatus(texts.started);
    startKeepAlive();
    speakBlock(0);
  }

  function pauseReading() {
    if (!reading) return;
    playing = false;
    if (speechSupported) synth.pause();
    setListenState('paused');
    setStatus(texts.paused);
  }

  function resumeReading() {
    if (!reading) return;
    playing = true;
    if (speechSupported) synth.resume();
    setListenState('playing');
    setStatus(texts.resumed);
  }

  function endReading(announce) {
    reading = false;
    playing = false;
    stopKeepAlive();
    if (speechSupported) { try { synth.cancel(); } catch (e) {} }
    clearHighlight();
    setListenState('idle');
    if (announce) setStatus(texts.finished);
  }

  function startKeepAlive() {
    stopKeepAlive();
    if (!speechSupported) return;
    keepAliveId = setInterval(function () {
      if (reading && playing) { try { synth.resume(); } catch (e) {} }
    }, 6000);
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

  // Klick-to-Listen auf Absätze, Tabellenzeilen & Überschriften
  var contentContainer = doc.querySelector('.post-content') || doc.querySelector('.md-content');
  if (contentContainer) {
    contentContainer.addEventListener('click', function (e) {
      if (!reading) return;
      var target = e.target.closest('tr, p, h2, h3, h4, li, .ff-tarif-card, .ff-einspar-box, .ff-kurzantwort');
      if (!target) return;
      for (var i = 0; i < blocks.length; i++) {
        if (blocks[i].el === target || (blocks[i].el && blocks[i].el.contains(target))) {
          synth.cancel();
          speakBlock(i);
          break;
        }
      }
    });
  }

  if (speechSupported) {
    maleVoice = pickMaleVoice(currentLang);
    if (typeof synth.onvoiceschanged !== 'undefined') {
      synth.onvoiceschanged = function () { maleVoice = pickMaleVoice(currentLang); };
    }
  }

  win.addEventListener('pagehide', function () { if (reading) endReading(false); });

  /* ============================================================
     2) KURZFASSUNG – Redaktionell strukturierter Dialog
  ============================================================ */

  var dialog = null;
  var summaryCopyText = '';

  function extractNumbers(content) {
    var out = [];
    var seen = {};
    qsa('p, li, td', content).forEach(function (el) {
      if (el.closest && el.closest('[data-ff-skip-read]')) return;
      var text = readableText(el);
      if (!/[€%]|\b(?:kwh|mbit\/s|gbit\/s|ersparnis|kosten|rabatt)\b/i.test(text)) return;
      sentences(text).forEach(function (s) {
        if (out.length >= 5) return;
        if (!/[€%]|\b(?:kwh|mbit\/s|ersparnis|kosten)\b/i.test(s)) return;
        if (s.length < 15 || s.length > 240) return;
        var key = s.toLowerCase();
        if (seen[key]) return;
        seen[key] = true;
        out.push(s);
      });
    });
    return out;
  }

  function extractTableHighlights(content) {
    var highlights = [];
    qsa('table, .ff-table-scroll table', content).forEach(function (tbl) {
      if (tbl.closest('[data-ff-skip-read]')) return;
      var ths = qsa('thead th', tbl).map(function (th) { return readableText(th); });
      var firstRows = qsa('tbody tr', tbl).slice(0, 3);
      if (ths.length && firstRows.length) {
        var rowSummaries = [];
        firstRows.forEach(function (tr) {
          var cells = qsa('td, th', tr).map(function (c) { return readableText(c); });
          if (cells.length) rowSummaries.push(cells.join(' | '));
        });
        highlights.push({ headers: ths.join(' | '), rows: rowSummaries });
      }
    });
    return highlights;
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
    var tables = content ? extractTableHighlights(content) : [];
    var short = stripMd(cfg.kurzantwort || cfg.description || '');
    if (!short && content) {
      var firstP = qsa('p', content)[0];
      if (firstP) short = firstSentences(readableText(firstP), 2);
    }
    return { short: short, sections: sections, numbers: numbers, tables: tables };
  }

  function buildPlainText(data) {
    var lines = [];
    lines.push((texts.summaryEyebrow.toUpperCase()) + ': ' + (stripMd(cfg.title) || doc.title));
    lines.push('');
    if (data.short) { lines.push(texts.summaryQuick30 + ':'); lines.push(data.short); lines.push(''); }
    if (data.sections.length) {
      lines.push(texts.summaryKeypoints + ':');
      data.sections.forEach(function (s) { lines.push('- ' + s.title + (s.lead ? ' — ' + s.lead : '')); });
      lines.push('');
    }
    if (data.numbers.length) {
      lines.push(texts.summaryNumbers + ':');
      data.numbers.forEach(function (n) { lines.push('- ' + n); });
      lines.push('');
    }
    lines.push(texts.readingTime.replace('{time}', (cfg.readingTime || '?')) + ' · ' + texts.wordCount.replace('{count}', (cfg.wordCount || '?')));
    lines.push(texts.source + win.location.href);
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

    currentLang = detectArticleLanguage();
    texts = I18N[currentLang] || I18N.de;

    var data = buildSummaryData();
    summaryCopyText = buildPlainText(data);

    dialog = doc.createElement('dialog');
    dialog.className = 'ff-summary';
    dialog.id = 'ff-summary-dialog';
    dialog.setAttribute('aria-labelledby', 'ff-summary-title');

    var card = el('div', 'ff-summary__card');

    var header = el('header', 'ff-summary__header');
    var headText = el('div', 'ff-summary__head-text');
    headText.appendChild(el('p', 'ff-summary__eyebrow', texts.summaryEyebrow));
    var title = el('h2', 'ff-summary__title', stripMd(cfg.title) || doc.title);
    title.id = 'ff-summary-title';
    headText.appendChild(title);
    header.appendChild(headText);
    var closeBtn = el('button', 'ff-summary__close');
    closeBtn.type = 'button';
    closeBtn.setAttribute('aria-label', texts.summaryClose);
    closeBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>';
    header.appendChild(closeBtn);

    var body = el('div', 'ff-summary__body');
    var metaParts = [];
    if (cfg.readingTime) metaParts.push(texts.readingTime.replace('{time}', cfg.readingTime));
    if (cfg.wordCount) metaParts.push(texts.wordCount.replace('{count}', cfg.wordCount));
    if (data.sections.length) metaParts.push(texts.sectionCount.replace('{count}', data.sections.length));
    if (metaParts.length) body.appendChild(el('div', 'ff-summary__meta', metaParts.join(' · ')));

    if (data.short) {
      var s1 = el('section', 'ff-summary__section');
      s1.appendChild(el('h3', null, texts.summaryQuick30));
      s1.appendChild(el('p', null, data.short));
      body.appendChild(s1);
    }

    if (data.sections.length) {
      var s2 = el('section', 'ff-summary__section');
      s2.appendChild(el('h3', null, texts.summaryKeypoints));
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
      s3.appendChild(el('h3', null, texts.summaryNumbers));
      var ul = el('ul');
      data.numbers.forEach(function (n) { ul.appendChild(el('li', null, n)); });
      s3.appendChild(ul);
      body.appendChild(s3);
    }

    var footer = el('footer', 'ff-summary__footer');
    var copyBtn = el('button', 'ff-summary__btn');
    copyBtn.type = 'button';
    copyBtn.id = 'ff-summary-copy';
    copyBtn.textContent = texts.summaryCopy;
    var readBtn = el('button', 'ff-summary__btn ff-summary__btn--primary');
    readBtn.type = 'button';
    readBtn.id = 'ff-summary-read';
    readBtn.textContent = texts.summaryReadFull;
    footer.appendChild(copyBtn);
    footer.appendChild(readBtn);

    card.appendChild(header);
    card.appendChild(body);
    card.appendChild(footer);
    dialog.appendChild(card);

    closeBtn.addEventListener('click', closeDialog);

    copyBtn.addEventListener('click', function () {
      copyText(summaryCopyText, function (ok) {
        copyBtn.textContent = ok ? texts.summaryCopied : texts.summaryCopyFail;
        setTimeout(function () { copyBtn.textContent = texts.summaryCopy; }, 1600);
      });
    });

    readBtn.addEventListener('click', function () {
      closeDialog();
      var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
      if (content) scrollTo(content, { behavior: reducedMotion ? 'auto' : 'smooth', block: 'start' });
    });

    dialog.addEventListener('click', function (e) {
      if (e.target === dialog) closeDialog();
    });

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
