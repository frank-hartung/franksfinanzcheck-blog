/* ============================================================
   FranksFinanzcheck – Premium Lesehilfen (Vorlesen + Kurzfassung)
   03.09.2026 — Profi-Agentur & Chefredakteur-Standard
   ------------------------------------------------------------
   - Privacy-first & First-party: Web Speech API lokal im Browser.
   - Männliche Stimme auf Highend-Level (sonore, redaktionelle
     Timbre-Optimierung) – automatisch gewählt, kein Stimmen-Menü.
   - Vollautomatische Mehrsprachigkeit: Deutsch (DE) und Englisch (EN)
     ohne manuellen Umschalter.
   - Automatische Qualitätsanpassung: Stimmen-Güte, Tempo, Chunk-Länge,
     Pausen und Fallback werden je Browser/Gerät selbst geregelt –
     keine Tempo-Anzeige, kein Tempo-Regler, keine Tastenkürzel.
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
      resumedPos: 'Vorlesen an der zuletzt gehörten Stelle fortgesetzt.',
      remaining: 'noch ca. {min} Min.',
      mediaArtist: 'FranksFinanzcheck – Artikel zum Hören',
      introLine: '{title}. Ein Beitrag von FranksFinanzcheck. Hördauer etwa {time} Minuten.',
      outroLine: 'Ende des Beitrags. Vielen Dank fürs Zuhören bei FranksFinanzcheck.',
      listItemNum: 'Punkt {n}:',
      cueShortAnswer: 'Kurzantwort:',
      cueSaving: 'Sparpotenzial:',
      cueTariff: 'Tarif im Überblick:',
      cueWarning: 'Achtung:',
      cueNote: 'Hinweis:',
      tableHeaders: 'Die Spalten lauten: {headers}',
      tableOutro: 'Ende der Tabelle {title}.',
      prevAria: 'Vorheriger Abschnitt',
      nextAria: 'Nächster Abschnitt',
      tableTitleDefault: 'Übersichtstabelle',
      tableIntro: 'Tabelle: {title}. Übersicht mit {cols} Spalten und {rows} Zeilen.',
      tableRow: 'Zeile {row} von {total}. {content}.',
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
      resumedPos: 'Resumed from your last listening position.',
      remaining: 'approx. {min} min left',
      voiceStudio: 'Studio',
      voicePremium: 'Premium',
      voiceStandard: 'Standard',
      mediaArtist: 'FranksFinanzcheck – Article Audio',
      introLine: '{title}. An article by FranksFinanzcheck. Listening time about {time} minutes.',
      outroLine: 'End of article. Thank you for listening to FranksFinanzcheck.',
      listItemNum: 'Point {n}:',
      cueShortAnswer: 'Short answer:',
      cueSaving: 'Savings potential:',
      cueTariff: 'Tariff at a glance:',
      cueWarning: 'Attention:',
      cueNote: 'Note:',
      tableHeaders: 'The columns are: {headers}',
      tableOutro: 'End of table {title}.',
      prevAria: 'Previous section',
      nextAria: 'Next section',
      tableTitleDefault: 'Overview Table',
      tableIntro: 'Table: {title}. Overview with {cols} columns and {rows} rows.',
      tableRow: 'Row {row} of {total}. {content}.',
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
    s = s.replace(/\u00ad/g, '');            // weiches Trennzeichen
    s = s.replace(/[\u200b-\u200d\ufeff]/g, '');

    /* --- Typografische Vorstufe: Anführungen, Striche, Auslassungen --- */
    s = s.replace(/[«»„“”‟"]/g, '');
    s = s.replace(/[‚‘’‛]/g, "'");
    // Gedankenstrich = Sprechpause, aber Zahlenbereiche (30–50) bleiben unangetastet
    s = s.replace(/(\D)\s+[–—]\s+/g, '$1, ');
    s = s.replace(/\.{3,}/g, '…');

    /* --- URLs, Mails & Domains hörbar machen --- */
    s = s.replace(/https?:\/\/(?:www\.)?([^\s/]+)[^\s]*/gi, function (m, host) {
      return (lang === 'en' ? 'the website ' : 'die Webseite ') + host.replace(/\./g, ' Punkt ');
    });
    s = s.replace(/\b([a-z0-9._%-]+)@([a-z0-9.-]+\.[a-z]{2,})\b/gi, function (m, u, d) {
      return u.replace(/\./g, ' Punkt ') + (lang === 'en' ? ' at ' : ' at ') + d.replace(/\./g, ' Punkt ');
    });

    /* --- Deutsche Zahlformatierung sprechbar machen --- */
    if (lang !== 'en') {
      // Tausenderpunkte entfernen: 1.250,50 -> 1250,50
      s = s.replace(/\b(\d{1,3})(?:\.(\d{3}))+(?:,(\d+))?\b/g, function (m) {
        return m.replace(/\./g, '').replace(',', ',');
      });
      // Datum 03.09.2026 -> 3. September 2026
      var MONTHS = ['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'];
      s = s.replace(/\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b/g, function (m, d, mo, y) {
        var mi = parseInt(mo, 10) - 1;
        return MONTHS[mi] ? (parseInt(d, 10) + '. ' + MONTHS[mi] + ' ' + y) : m;
      });
      // Uhrzeit 14:30 -> 14 Uhr 30
      s = s.replace(/\b(\d{1,2}):(\d{2})\s*Uhr\b/g, function (m, h, mi) { return h + ' Uhr ' + (mi === '00' ? '' : mi); });
      // Paragraphen & Rechtsbezüge
      s = s.replace(/§§\s*/g, 'die Paragrafen ');
      s = s.replace(/§\s*/g, 'Paragraf ');
      s = s.replace(/\bSGB\b/g, 'Sozialgesetzbuch');
      s = s.replace(/\bBGB\b/g, 'Bürgerliches Gesetzbuch');
      s = s.replace(/\bEStG\b/g, 'Einkommensteuergesetz');
      s = s.replace(/\bVVG\b/g, 'Versicherungsvertragsgesetz');
      s = s.replace(/\bDSGVO\b/g, 'Datenschutzgrundverordnung');
      // Finanz-Akronyme im Redaktions-Duden-Standard
      s = s.replace(/\bETF(s)?\b/g, function (m, pl) { return 'E T F' + (pl ? 's' : ''); });
      s = s.replace(/\bTER\b/g, 'T E R');
      s = s.replace(/\bBU\b/g, 'Berufsunfähigkeitsversicherung');
      s = s.replace(/\bKfz\b/gi, 'Kraftfahrzeug');
      s = s.replace(/\bPKV\b/g, 'private Krankenversicherung');
      s = s.replace(/\bGKV\b/g, 'gesetzliche Krankenversicherung');
      s = s.replace(/\bIBAN\b/g, 'I BAN');
      s = s.replace(/\bBIC\b/g, 'B I C');
      s = s.replace(/\bAPI\b/g, 'A P I');
      s = s.replace(/\bKfW\b/g, 'K f W');
      s = s.replace(/\bBaFin\b/g, 'Bafin');
      s = s.replace(/\bCHECK24\b/gi, 'Check 24');
      s = s.replace(/\bVerivox\b/gi, 'Verivox');
      s = s.replace(/\bEZB\b/g, 'Europäische Zentralbank');
      s = s.replace(/\bp\.\s?m\.(?![\wäöüßÄÖÜ])/gi, 'pro Monat');
      // Ordnungszahlen im Fließtext
      s = s.replace(/\bNr\.\s*(\d+)/g, 'Nummer $1');
      // Bruch- und Rechenzeichen
      s = s.replace(/\s*±\s*/g, ' plus minus ');
      s = s.replace(/\s*≈\s*/g, ' ungefähr ');
      s = s.replace(/\s*≤\s*/g, ' höchstens ');
      s = s.replace(/\s*≥\s*/g, ' mindestens ');
      s = s.replace(/\s*→\s*/g, ' führt zu ');
      s = s.replace(/(\d)\s*[x×]\s*(\d)/g, '$1 mal $2');
      s = s.replace(/\bca\b(?!\.)/g, 'circa');
    } else {
      s = s.replace(/\b(\d{1,2})\/(\d{1,2})\/(\d{4})\b/g, '$2 $1 $3');
      s = s.replace(/§§?\s*/g, 'section ');
      s = s.replace(/\bETF(s)?\b/g, function (m, pl) { return 'E T F' + (pl ? 's' : ''); });
      s = s.replace(/\bAPI\b/g, 'A P I');
      s = s.replace(/\s*±\s*/g, ' plus minus ');
      s = s.replace(/\s*≈\s*/g, ' approximately ');
      s = s.replace(/\s*→\s*/g, ' leads to ');
      s = s.replace(/(\d)\s*[x×]\s*(\d)/g, '$1 times $2');
    }

    if (lang === 'en') {
      // Währungen & Zahlenbereiche Englisch
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(?:€|EUR|Euro)/gi, '$1 to $2 Euros');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*\$/g, '$1 to $2 Dollars');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*%/g, '$1 to $2 percent');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)/g, '$1 to $2');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*(?:€|EUR|Euro)/gi, '$1 Euros');
      s = s.replace(/\$\s*(\d+(?:[.,]\d+)?)/g, '$1 Dollars');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*\$/g, '$1 Dollars');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*%/g, '$1 percent');
      s = s.replace(/\b(\d+)\s*(?:Cent|ct)\b/gi, '$1 Cents');
      s = s.replace(/\b(?:Cent|ct)\/kWh\b/gi, 'Cents per kilowatt hour');
      s = s.replace(/\b(?:kWh|kwh)\b/g, 'kilowatt hours');
      s = s.replace(/\b(?:Mbit\/s|MBit\/s|Mbit)\b/g, 'megabits per second');
      s = s.replace(/\b(?:Gbit\/s|GBit\/s|Gbit)\b/g, 'gigabits per second');
      s = s.replace(/\b(?:m²|sqm)\b/gi, 'square meters');
      s = s.replace(/\s*(?:\bp\.\s?a\.|\/\s?year)/gi, ' per year');
      s = s.replace(/\s*\/\s?(month|year|week|day|person|hour)\b/gi, ' per $1');
      s = s.replace(/\be\.g\.(?![\wäöüßÄÖÜ])/gi, 'for example');
      s = s.replace(/\bi\.e\.(?![\wäöüßÄÖÜ])/gi, 'that is');
      s = s.replace(/\bapprox\.(?![\wäöüßÄÖÜ])/gi, 'approximately');
      s = s.replace(/\bincl\.(?![\wäöüßÄÖÜ])/gi, 'including');
      s = s.replace(/\bexcl\.(?![\wäöüßÄÖÜ])/gi, 'excluding');
      s = s.replace(/\bvs\.?\b/gi, 'versus');
      s = s.replace(/\bmin\.(?![\wäöüßÄÖÜ])/gi, 'minimum');
      s = s.replace(/\bmax\.(?![\wäöüßÄÖÜ])/gi, 'maximum');
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
      s = s.replace(/(\d)\s*h\b/g, '$1 Stunden');
      s = s.replace(/(\d)\s*(?:km|Km)\b/g, '$1 Kilometer');
      s = s.replace(/(\d)\s*(?:kg)\b/gi, '$1 Kilogramm');
      s = s.replace(/\s*(?:\bp\.\s?a\.|\/\s?Jahr|\bj[äa]hrl\.)/gi, ' pro Jahr');
      s = s.replace(/\s*(?:\bmtl\.|\/\s?Monat|\bmonatl\.)/gi, ' monatlich');
      s = s.replace(/\s*\/\s?(Woche|Tag|Stunde|Person|Monat|Jahr)\b/gi, ' pro $1');

      // Abkürzungen Deutsch
      s = s.replace(/\bz\.\s*B\.(?![\wäöüßÄÖÜ])|\bz\.B\.(?![\wäöüßÄÖÜ])/gi, 'zum Beispiel');
      s = s.replace(/\bd\.\s*h\.(?![\wäöüßÄÖÜ])|\bd\.h\.(?![\wäöüßÄÖÜ])/gi, 'das heißt');
      s = s.replace(/\bu\.\s*a\.(?![\wäöüßÄÖÜ])|\bu\.a\.(?![\wäöüßÄÖÜ])/gi, 'unter anderem');
      s = s.replace(/\bbzw\.(?![\wäöüßÄÖÜ])/gi, 'beziehungsweise');
      s = s.replace(/\bca\.(?![\wäöüßÄÖÜ])/gi, 'circa');
      s = s.replace(/\binkl\.(?![\wäöüßÄÖÜ])/gi, 'inklusive');
      s = s.replace(/\bexkl\.(?![\wäöüßÄÖÜ])/gi, 'exklusive');
      s = s.replace(/\bggf\.(?![\wäöüßÄÖÜ])/gi, 'gegebenenfalls');
      s = s.replace(/\bevtl\.(?![\wäöüßÄÖÜ])/gi, 'eventuell');
      s = s.replace(/\bmind\.(?![\wäöüßÄÖÜ])/gi, 'mindestens');
      s = s.replace(/\bmax\.(?![\wäöüßÄÖÜ])/gi, 'maximal');
      s = s.replace(/\bbspw\.(?![\wäöüßÄÖÜ])/gi, 'beispielsweise');
      s = s.replace(/\bAbs\.(?![\wäöüßÄÖÜ])/g, 'Absatz');
      s = s.replace(/\bArt\.(?![\wäöüßÄÖÜ])/g, 'Artikel');
      s = s.replace(/\bNr\.(?![\wäöüßÄÖÜ])/g, 'Nummer');
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

    // Sonstige Emojis & Piktogramme sauber entfernen (kein "Emoji-Stottern")
    s = s.replace(/[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}\u{2190}-\u{21FF}\u{2B00}-\u{2BFF}]/gu, ' ');

    // Dekorative Icons & Markdown-Sonderzeichen bereinigen
    s = s.replace(/[⏱️📅✍️📚💶💰🛡️⚡🚗🌱🌐💳📈📋✓🔧★⭐]/g, '');
    s = s.replace(/[*_`~#|]+/g, ' ');
    s = s.replace(/\(\s*\)/g, ' ');
    s = s.replace(/\b(Tipp|Hinweis|Achtung|Wichtiger Hinweis|Tip|Note|Warning):\s*\1:/gi, '$1:');
    s = s.replace(/\s+([,.;:!?…])/g, '$1');
    s = s.replace(/([,.;:!?…]){2,}/g, '$1');
    s = s.replace(/\s+/g, ' ').trim();
    // Satzschluss garantieren – verhindert gehetzte Übergänge
    if (s && !/[.!?…:,]$/.test(s)) s += '.';
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
     1) VORLESEN – Highend-Sprachausgabe (Redaktions-Studio-Engine)
     ------------------------------------------------------------
     Über Verlagshaus-Niveau durch:
       - Satzgenaue Prosodie-Engine mit Atem- und Denkpausen
       - Typografische Aussprache-Veredelung (Zahlen, Daten, §§,
         Prozente, IBAN, Abkürzungen, Finanz-Akronyme, Domains)
       - Rollen-basierte Stimmführung (Überschrift, Fließtext,
         Zitat, Warnung, Tabellenzeile) wie im Hörfunk-Studio
       - Neuronale Stimmen-Rangliste (automatisch, männlich, DE/EN)
       - Automatische Qualitätsanpassung (Stimme, Tempo, Chunking,
         Pausen, Fallback) – ohne Regler, ohne Tempo-Anzeige
       - Abschnitts-Navigation, Merken der Hörposition
       - Media-Session (Sperrbildschirm/Kopfhörer-Tasten)
       - Chrome-/Safari-Härtung gegen Abbrüche nach 15 Sekunden
  ============================================================ */

  var synth = win.speechSynthesis || null;
  var speechSupported = !!(synth && typeof win.SpeechSynthesisUtterance === 'function');

  var STORE_POS = 'ff-reader:pos:' + (win.location ? win.location.pathname : '');

  function storeGet(k) { try { return win.localStorage.getItem(k); } catch (e) { return null; } }
  function storeSet(k, v) { try { win.localStorage.setItem(k, v); } catch (e) {} }
  function storeDel(k) { try { win.localStorage.removeItem(k); } catch (e) {} }

  var maleVoice = null;
  var reading = false;
  var playing = false;
  var blocks = [];        // { el, text, lang, type, role, chunks[] }
  var timeline = [];      // flache Liste aller Sprech-Einheiten
  var cursor = 0;
  var keepAliveId = null;
  var pauseTimer = null;
  var spokenChars = 0;
  var totalChars = 0;
  var prevBtn = doc.getElementById('ff-listen-prev');
  var nextBtn = doc.getElementById('ff-listen-next');
  var remainEl = doc.getElementById('ff-reader-remaining');

  /* ---------- Automatische Qualitätsanpassung (Auto-Quality) ----------
     Statt manueller Regler stellt sich die Engine selbst ein:
       - tier        : 'studio' | 'premium' | 'standard' | 'basic'
                       (aus der Güte der besten verfügbaren Stimme)
       - rate        : Grundtempo (Studio-Stimmen vertragen ein
                       natürlicheres Tempo, einfache Stimmen brauchen
                       mehr Ruhe für gute Verständlichkeit)
       - maxChunk    : maximale Satz-Chunk-Länge (Chrome bricht lange
                       Utterances ab; Neural-Stimmen vertragen längere
                       Bögen -> flüssigere Prosodie)
       - pauseScale  : Skalierung der Atem-/Denkpausen
       - pitchShift  : leichte Anhebung, falls nur einfache Stimmen
                       vorhanden sind (klingen sonst zu dumpf)
  ---------------------------------------------------------------------- */
  var QUALITY_PROFILES = {
    studio:   { rate: 1.00, maxChunk: 220, pauseScale: 1.00, pitchShift: 0.00 },
    premium:  { rate: 0.98, maxChunk: 200, pauseScale: 1.00, pitchShift: 0.00 },
    standard: { rate: 0.94, maxChunk: 170, pauseScale: 1.10, pitchShift: 0.02 },
    basic:    { rate: 0.90, maxChunk: 150, pauseScale: 1.20, pitchShift: 0.04 }
  };
  var quality = { tier: 'standard', rate: 0.94, maxChunk: 170, pauseScale: 1.1, pitchShift: 0.02 };
  var errorStreak = 0;  // Fehler in Folge (Synthese-Abbrüche)
  var degradeLevel = 0; // dauerhafte adaptive Herabstufung (0–2)

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
    if (win.navigator && win.navigator.mediaSession) {
      try { win.navigator.mediaSession.playbackState = state === 'playing' ? 'playing' : (state === 'paused' ? 'paused' : 'none'); } catch (e) {}
    }
  }

  /* ---------- Stimmen-Rangliste: Studio-Qualität zuerst ---------- */
  var MALE_KEYWORDS = {
    de: ['conrad', 'stefan', 'florian', 'bernd', 'christoph', 'ralf', 'klaus', 'markus', 'jonas', 'martin',
         'yannick', 'hans', 'viktor', 'thorsten', 'killian', 'de-de-x-deg', 'de-de-x-deb', 'de-de-x-dea',
         'de_de_male', 'male', 'männlich', 'mann', '#male', 'neural2-b', 'neural2-d', 'wavenet-b', 'wavenet-d',
         'standard-b', 'standard-d', 'polyglot'],
    en: ['david', 'george', 'guy', 'mark', 'ryan', 'daniel', 'oliver', 'arthur', 'thomas', 'james', 'alex',
         'fred', 'aaron', 'brian', 'eric', 'richard', 'tom', 'john', 'paul', 'michael', 'peter', 'frank',
         'en_us_male', 'en_gb_male', 'male', 'man', '#male', 'neural2-a', 'neural2-d', 'neural2-j',
         'wavenet-a', 'wavenet-b', 'wavenet-d', 'wavenet-j', 'standard-b', 'standard-d']
  };

  var FEMALE_KEYWORDS = [
    'anna', 'katja', 'hedda', 'vicki', 'petra', 'marlene', 'ingrid', 'zira', 'hazel', 'samantha', 'victoria',
    'karen', 'susan', 'jenny', 'helena', 'eva', 'gisela', 'luisa', 'maja', 'elke', 'steffi', 'catherine',
    'linda', 'heather', 'amy', 'emma', 'olivia', 'joanna', 'kendra', 'cortana', 'female', 'weiblich', 'frau',
    'woman', 'girl', '#female', 'siri female', 'seraphina', 'amala', 'kathy', 'nicole', 'moira', 'tessa'
  ];

  // Namentlich bekannte Studio-/Neuronal-Stimmen (höchste Natürlichkeit)
  var STUDIO_VOICES = [
    'google deutsch', 'microsoft conrad online', 'microsoft killian online', 'microsoft florian online',
    'microsoft ralf', 'anpassbare stimme', 'eloquence', 'siri stimme', 'google uk english male',
    'google us english', 'microsoft guy online', 'microsoft christopher online', 'microsoft roger online',
    'microsoft eric online', 'microsoft steffan online'
  ];

  var PREMIUM_KEYWORDS = ['natural', 'neural', 'wavenet', 'studio', 'journey', 'polyglot', 'online',
                          'enhanced', 'premium', 'siri', 'high quality', 'highquality', 'google'];
  var LOWQ_KEYWORDS = ['espeak', 'compact', 'pico', 'flite', 'festival', 'novelty', 'whisper', 'bells',
                       'bad news', 'good news', 'bubbles', 'jester', 'organ', 'trinoids', 'zarvox',
                       'albert', 'wobble', 'superstar'];

  function scoreVoice(v, targetLang) {
    var score = 0;
    var name = (v.name || '').toLowerCase();
    var uri = (v.voiceURI || '').toLowerCase();
    var langStr = (v.lang || '').toLowerCase().replace('_', '-');
    var isEN = targetLang.indexOf('en') === 0;
    var hay = name + ' ' + uri;

    if (isEN) {
      if (langStr === 'en-us' || langStr === 'en-gb') score += 60;
      else if (langStr.indexOf('en') === 0) score += 35;
      else score -= 400;
    } else {
      if (langStr === 'de-de') score += 60;
      else if (langStr.indexOf('de') === 0) score += 35;
      else score -= 400;
    }

    var mk = MALE_KEYWORDS[isEN ? 'en' : 'de'];
    for (var i = 0; i < mk.length; i++) { if (hay.indexOf(mk[i]) !== -1) { score += 130; break; } }
    for (var j = 0; j < FEMALE_KEYWORDS.length; j++) { if (hay.indexOf(FEMALE_KEYWORDS[j]) !== -1) { score -= 200; break; } }
    for (var s = 0; s < STUDIO_VOICES.length; s++) { if (hay.indexOf(STUDIO_VOICES[s]) !== -1) { score += 90; break; } }
    for (var k = 0; k < PREMIUM_KEYWORDS.length; k++) { if (hay.indexOf(PREMIUM_KEYWORDS[k]) !== -1) { score += 45; break; } }
    for (var l = 0; l < LOWQ_KEYWORDS.length; l++) { if (hay.indexOf(LOWQ_KEYWORDS[l]) !== -1) { score -= 260; break; } }

    if (v.localService) score += 8;      // stabil & offline
    if (v.default) score += 4;
    return score;
  }

  function rankVoices(lang) {
    if (!speechSupported) return [];
    var list = synth.getVoices() || [];
    if (!list.length) return [];
    var targetLang = (lang || currentLang || 'de').toLowerCase();
    var pattern = targetLang.indexOf('en') === 0 ? /^en([-_]|$)/i : /^de([-_]|$)/i;
    var candidates = list.filter(function (v) { return pattern.test(v.lang || ''); });
    if (!candidates.length) candidates = list.slice();
    return candidates
      .map(function (v) { return { voice: v, score: scoreVoice(v, targetLang) }; })
      .sort(function (a, b) { return b.score - a.score; });
  }

  function pickMaleVoice(lang) {
    var ranked = rankVoices(lang);
    if (!ranked.length) return null;
    return ranked[0].voice;
  }

  /* ---------- Automatische Qualitätsanpassung: Kalibrierung ---------- */
  function qualityTierForScore(score) {
    if (score >= 200) return 'studio';
    if (score >= 140) return 'premium';
    if (score >= 60) return 'standard';
    return 'basic';
  }

  function calibrateQuality() {
    var ranked = rankVoices(currentLang);
    var tier = ranked.length ? qualityTierForScore(ranked[0].score) : 'basic';
    var profile = QUALITY_PROFILES[tier] || QUALITY_PROFILES.standard;
    var next = {
      tier: tier,
      rate: profile.rate,
      maxChunk: profile.maxChunk,
      pauseScale: profile.pauseScale,
      pitchShift: profile.pitchShift
    };

    // Geräte-/Netz-Kontext: Datensparmodus, schwache CPU oder Mobilgerät
    // -> etwas kürzere Chunks & ruhigeres Tempo (weniger Abbrüche, klarer)
    var nav = win.navigator || {};
    var conn = nav.connection || nav.mozConnection || nav.webkitConnection;
    var lowPower = !!(conn && (conn.saveData || /(^|-)2g$/.test(conn.effectiveType || '')));
    var weakCpu = typeof nav.hardwareConcurrency === 'number' && nav.hardwareConcurrency > 0 && nav.hardwareConcurrency <= 2;
    var isMobile = !!(win.matchMedia && win.matchMedia('(pointer: coarse)').matches);
    if (lowPower || weakCpu) { next.maxChunk = Math.min(next.maxChunk, 150); next.rate = Math.min(next.rate, 0.94); }
    else if (isMobile) { next.maxChunk = Math.min(next.maxChunk, 180); }

    // Adaptive Herabstufung nach wiederholten Synthese-Fehlern
    if (degradeLevel > 0) {
      next.maxChunk = Math.max(110, next.maxChunk - 40 * degradeLevel);
      next.rate = Math.max(0.88, next.rate - 0.04 * degradeLevel);
      next.pauseScale = Math.min(1.4, next.pauseScale + 0.1 * degradeLevel);
    }

    // Nutzer-Präferenz „Bewegung reduzieren“: minimal ruhigere Sprechweise
    if (reducedMotion) next.rate = Math.min(next.rate, 0.97);

    quality = next;
    return quality;
  }

  /* ---------- Prosodie-Profile je Textrolle (Hörfunk-Regie) ---------- */
  var PROSODY = {
    h2:            { rate: 0.90, pitch: 0.88, volume: 1.00, before: 620, after: 340 },
    h3:            { rate: 0.92, pitch: 0.90, volume: 1.00, before: 460, after: 260 },
    h4:            { rate: 0.94, pitch: 0.92, volume: 0.99, before: 360, after: 220 },
    p:             { rate: 1.00, pitch: 0.96, volume: 1.00, before: 130, after: 190 },
    lead:          { rate: 0.96, pitch: 0.95, volume: 1.00, before: 180, after: 260 },
    li:            { rate: 1.00, pitch: 0.97, volume: 0.99, before: 110, after: 150 },
    blockquote:    { rate: 0.94, pitch: 1.02, volume: 0.96, before: 340, after: 320 },
    callout:       { rate: 0.95, pitch: 0.93, volume: 1.00, before: 380, after: 320 },
    warning:       { rate: 0.90, pitch: 0.86, volume: 1.00, before: 460, after: 380 },
    'overview-card': { rate: 0.97, pitch: 0.95, volume: 1.00, before: 300, after: 260 },
    'table-intro': { rate: 0.93, pitch: 0.90, volume: 1.00, before: 520, after: 320 },
    'table-row':   { rate: 1.02, pitch: 0.97, volume: 0.98, before: 90,  after: 210 },
    'table-outro': { rate: 0.94, pitch: 0.92, volume: 1.00, before: 260, after: 360 },
    intro:         { rate: 0.92, pitch: 0.92, volume: 1.00, before: 0,   after: 520 },
    outro:         { rate: 0.92, pitch: 0.92, volume: 1.00, before: 520, after: 0 }
  };

  function prosodyFor(type) { return PROSODY[type] || PROSODY.p; }

  /* ---------- Satz-Zerlegung mit Chrome-sicherer Chunk-Länge ----------
     Die maximale Länge stammt aus der automatischen Qualitätsanpassung
     (Studio-Stimmen: längere Bögen, einfache Stimmen: kürzere Chunks). */
  var MAX_CHUNK = 180;

  function splitForSpeech(text) {
    var maxChunk = (quality && quality.maxChunk) || MAX_CHUNK;
    var parts = sentences(text);
    if (!parts.length) parts = [text];
    var out = [];
    parts.forEach(function (sentence) {
      if (sentence.length <= maxChunk) { out.push(sentence); return; }
      // Zu lange Sätze an Kommata/Semikola/Gedankenstrichen atmen lassen
      var segs = sentence.replace(/([,;:–—])\s+/g, '$1\u0001').split('\u0001');
      var buf = '';
      segs.forEach(function (seg) {
        if ((buf + ' ' + seg).trim().length > maxChunk && buf) { out.push(buf.trim()); buf = seg; }
        else { buf = (buf ? buf + ' ' : '') + seg; }
      });
      if (buf.trim()) out.push(buf.trim());
    });
    // Notfall: harte Wortgrenzen
    var safe = [];
    out.forEach(function (c) {
      if (c.length <= 260) { safe.push(c); return; }
      var words = c.split(' ');
      var b = '';
      words.forEach(function (w) {
        if ((b + ' ' + w).length > 220 && b) { safe.push(b.trim()); b = w; }
        else { b = (b ? b + ' ' : '') + w; }
      });
      if (b.trim()) safe.push(b.trim());
    });
    return safe.filter(function (c) { return c && /[a-zA-ZÄÖÜäöüß0-9]/.test(c); });
  }

  /* ---------- Mikro-Pausen nach Satzschluss (natürliche Atmung) ---------- */
  function pauseAfterChunk(chunk, isLast, profile) {
    if (isLast) return profile.after;
    var tail = chunk.slice(-1);
    if (tail === '?' ) return 300;
    if (tail === '!') return 280;
    if (tail === '.' || tail === '…') return 240;
    if (tail === ':' ) return 260;
    if (tail === ',' || tail === ';') return 130;
    return 170;
  }

  /* ---------- Tabellen-Daten-Extraktion (Maximum Barrierefreiheit) ---------- */
  function extractTableSpeechBlocks(tableEl, lang) {
    if (!tableEl) return [];
    var tTexts = I18N[lang] || I18N.de;

    var title = tableEl.getAttribute('aria-label') || '';
    if (!title) {
      var caption = tableEl.querySelector('caption');
      if (caption) title = readableText(caption);
    }
    if (!title) {
      var prev = (tableEl.closest('.ff-table-scroll') || tableEl).previousElementSibling;
      while (prev && !/^H[1-6]$/.test(prev.tagName)) prev = prev.previousElementSibling;
      if (prev && /^H[1-6]$/.test(prev.tagName)) title = readableText(prev);
    }
    if (!title) title = tTexts.tableTitleDefault;

    var headers = [];
    var ths = qsa('thead th', tableEl);
    if (!ths.length) ths = qsa('tr:first-child th, tr:first-child td', tableEl);
    ths.forEach(function (th) {
      var hText = readableText(th);
      if (hText) headers.push(hText);
    });

    var rows = qsa('tbody tr', tableEl);
    if (!rows.length) {
      var allTrs = qsa('tr', tableEl);
      rows = allTrs.length > 1 ? allTrs.slice(1) : allTrs;
    }

    var tableBlocks = [];
    var colCount = Math.max(headers.length, 1);
    var rowCount = rows.length;

    var introRaw = tTexts.tableIntro
      .replace('{title}', title)
      .replace('{cols}', colCount)
      .replace('{rows}', rowCount);
    if (headers.length) {
      introRaw += ' ' + tTexts.tableHeaders.replace('{headers}', headers.join(', ')) + '.';
    }
    var introEl = tableEl.closest('.ff-table-scroll') || tableEl;
    tableBlocks.push({ el: introEl, text: speechNormalize(introRaw, lang), lang: lang, type: 'table-intro' });

    rows.forEach(function (tr, rIdx) {
      if (tr.closest('[data-ff-skip-read]')) return;
      var cells = qsa('td, th', tr);
      if (!cells.length) return;

      var rowLabel = readableText(cells[0]);
      var statements = [];
      cells.forEach(function (cell, cIdx) {
        var cellVal = readableText(cell);
        if (!cellVal) return;
        if (cIdx === 0 && rowLabel) return; // Zeilentitel wird vorangestellt
        var headerName = headers[cIdx] || (tTexts.column + ' ' + (cIdx + 1));
        statements.push(headerName + ': ' + cellVal);
      });
      if (!statements.length && rowLabel) statements.push(rowLabel);
      if (!statements.length) return;

      var rowRaw = (rowLabel ? rowLabel + '. ' : '') +
        tTexts.tableRow.replace('{row}', (rIdx + 1)).replace('{total}', rowCount).replace('{content}', statements.join('. '));

      tableBlocks.push({ el: tr, text: speechNormalize(rowRaw, lang), lang: lang, type: 'table-row' });
    });

    tableBlocks.push({
      el: introEl,
      text: speechNormalize(tTexts.tableOutro.replace('{title}', title), lang),
      lang: lang,
      type: 'table-outro'
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

    // Studio-Anmoderation: Titel & Lesedauer
    var introRaw = texts.introLine
      .replace('{title}', stripMd(cfg.title || doc.title || ''))
      .replace('{time}', cfg.readingTime || '');
    out.push({ el: toolbar, text: speechNormalize(introRaw, lang), lang: lang, type: 'intro' });

    var nodes = qsa('h2, h3, h4, p, li, blockquote, table, .ff-table-scroll, .ff-tarif-card, .ff-einspar-box, .ff-kurzantwort, .ff-korrektur, .callout', content);

    nodes.forEach(function (el) {
      if (el.closest && el.closest('figure, script, style, noscript, [aria-hidden="true"], [data-ff-skip-read], .ff-reader-toolbar, .ff-toc, #TableOfContents, .ff-share, .ff-related')) return;

      var elLang = (el.getAttribute('lang') || lang).toLowerCase().indexOf('en') === 0 ? 'en' : 'de';

      if (el.tagName === 'TABLE' || (el.classList && el.classList.contains('ff-table-scroll'))) {
        var tbl = el.tagName === 'TABLE' ? el : el.querySelector('table');
        if (!tbl || processedTables.indexOf(tbl) !== -1) return;
        processedTables.push(tbl);
        extractTableSpeechBlocks(tbl, elLang).forEach(function (tb) { out.push(tb); });
        return;
      }

      if (el.closest && el.closest('table, .ff-table-scroll')) return;

      var boxed = el.classList && (el.classList.contains('ff-tarif-card') || el.classList.contains('ff-einspar-box') ||
        el.classList.contains('ff-kurzantwort') || el.classList.contains('ff-korrektur') || el.classList.contains('callout'));

      if (boxed) {
        var boxText = readableText(el);
        if (boxText.length <= 5) return;
        var isWarn = /\b(achtung|warnung|vorsicht|wichtig|caution|warning)\b/i.test(boxText.slice(0, 60)) || el.classList.contains('ff-korrektur');
        var cue = el.classList.contains('ff-kurzantwort') ? texts.cueShortAnswer
          : el.classList.contains('ff-einspar-box') ? texts.cueSaving
          : el.classList.contains('ff-tarif-card') ? texts.cueTariff
          : isWarn ? texts.cueWarning : texts.cueNote;
        out.push({
          el: el,
          text: speechNormalize(cue + ' ' + boxText, elLang),
          lang: elLang,
          type: isWarn ? 'warning' : (el.classList.contains('ff-tarif-card') || el.classList.contains('ff-einspar-box') ? 'overview-card' : 'callout')
        });
        return;
      }

      if (el.closest && el.closest('.ff-kurzantwort, .ff-korrektur, .callout, .ff-tarif-card, .ff-einspar-box, blockquote')) return;

      var text = readableText(el);
      if (text.length < 2) return;
      if (/^(quelle|source|stand|foto|bild|anzeige|werbung|affiliate)\b/i.test(text) && text.length < 140) return;

      var tag = el.tagName.toLowerCase();
      var type = tag;
      if (tag === 'blockquote') type = 'blockquote';
      if (tag === 'p' && el.classList && el.classList.contains('ff-lead')) type = 'lead';

      // Listenpunkte hörbar als Aufzählung markieren
      var speakText = text;
      if (tag === 'li') {
        var parentList = el.parentElement;
        if (parentList && parentList.tagName === 'OL') {
          var idx = Array.prototype.indexOf.call(parentList.children, el) + 1;
          speakText = texts.listItemNum.replace('{n}', idx) + ' ' + text;
        }
      }
      if (/^H[234]$/.test(el.tagName)) speakText = text.replace(/[?!.]*$/, '') + '.';

      out.push({ el: el, text: speechNormalize(speakText, elLang), lang: elLang, type: type });
    });

    out.push({ el: toolbar, text: speechNormalize(texts.outroLine, lang), lang: lang, type: 'outro' });

    return out.filter(function (b) { return b.text && b.text.length > 1; });
  }

  /* ---------- Zeitachse aus Blöcken + Chunks ---------- */
  function buildTimeline() {
    timeline = [];
    totalChars = 0;
    blocks.forEach(function (b, bi) {
      var chunks = splitForSpeech(b.text);
      var profile = prosodyFor(b.type);
      chunks.forEach(function (c, ci) {
        totalChars += c.length;
        timeline.push({
          block: b,
          blockIndex: bi,
          text: c,
          lang: b.lang,
          type: b.type,
          profile: profile,
          before: ci === 0 ? profile.before : 0,
          after: pauseAfterChunk(c, ci === chunks.length - 1, profile)
        });
      });
    });
  }

  function estimateRemaining() {
    if (!remainEl) return;
    var rest = 0;
    for (var i = cursor; i < timeline.length; i++) rest += timeline[i].text.length;
    // ~950 Zeichen/Minute bei Rate 1.0 (deutsche Nachrichtensprache)
    var minutes = rest / (950 * Math.max(0.5, quality.rate || 1));
    if (minutes < 0.1) { remainEl.textContent = ''; return; }
    var mm = Math.max(1, Math.round(minutes));
    remainEl.textContent = texts.remaining.replace('{min}', mm);
  }

  function highlight(unit) {
    var el = unit && unit.block ? unit.block.el : null;
    blocks.forEach(function (b) { if (b.el && b.el !== el) b.el.classList.remove('ff-reader-active'); });
    if (!el || el === toolbar) return;
    el.classList.add('ff-reader-active');
    if (progressBar && totalChars) {
      progressBar.style.width = Math.min(100, (spokenChars / totalChars) * 100).toFixed(1) + '%';
    }
    if (!reducedMotion) scrollTo(el, { block: 'center', behavior: 'smooth' });
    else scrollTo(el, { block: 'center' });
  }

  function clearHighlight() {
    blocks.forEach(function (b) { if (b.el) b.el.classList.remove('ff-reader-active'); });
    if (progressBar) progressBar.style.width = '0%';
    if (remainEl) remainEl.textContent = '';
  }

  function clearPauseTimer() { if (pauseTimer) { clearTimeout(pauseTimer); pauseTimer = null; } }

  function speakUnit(index) {
    if (!reading || !speechSupported) return;
    clearPauseTimer();
    if (index >= timeline.length) { endReading(true); return; }
    cursor = index;
    var unit = timeline[index];
    highlight(unit);
    estimateRemaining();
    storeSet(STORE_POS, String(index));

    var start = function () {
      if (!reading || !playing) return;
      var voice = pickMaleVoice(unit.lang);
      var u = new win.SpeechSynthesisUtterance(unit.text);
      u.lang = unit.lang === 'en' ? 'en-US' : 'de-DE';
      if (voice) u.voice = voice;
      var p = unit.profile;
      // Automatische Qualitätsanpassung: Tempo & Tonlage je Stimmen-Güte
      u.rate = Math.min(2, Math.max(0.5, p.rate * quality.rate));
      u.pitch = Math.min(2, Math.max(0.5, p.pitch + (quality.pitchShift || 0)));
      u.volume = p.volume;

      u.onend = function () {
        if (!reading || !playing) return;
        errorStreak = 0;
        spokenChars += unit.text.length;
        var wait = Math.round((unit.after * (quality.pauseScale || 1)) / Math.max(0.6, quality.rate));
        clearPauseTimer();
        pauseTimer = setTimeout(function () { speakUnit(cursor + 1); }, wait);
      };
      u.onerror = function (e) {
        if (!reading) return;
        if (e && (e.error === 'interrupted' || e.error === 'canceled')) return;
        // Adaptive Herabstufung: nach wiederholten Fehlern kürzere Chunks
        // und ruhigeres Tempo, damit die Wiedergabe stabil weiterläuft.
        errorStreak += 1;
        if (errorStreak >= 2 && degradeLevel < 2) {
          degradeLevel += 1;
          errorStreak = 0;
          var blockIdx = unit.blockIndex;
          calibrateQuality();
          maleVoice = pickMaleVoice(unit.lang);
          buildTimeline();
          // Am nächsten Block weitermachen (Zeitachse wurde neu zerlegt)
          var nextIdx = timeline.length;
          spokenChars = 0;
          for (var i = 0; i < timeline.length; i++) {
            if (timeline[i].blockIndex > blockIdx) { nextIdx = i; break; }
            spokenChars += timeline[i].text.length;
          }
          cursor = nextIdx - 1;
        } else {
          spokenChars += unit.text.length;
        }
        if (playing) speakUnit(cursor + 1);
      };
      try { synth.speak(u); } catch (err) { speakUnit(cursor + 1); }
    };

    var lead = Math.round(((unit.before || 0) * (quality.pauseScale || 1)) / Math.max(0.6, quality.rate));
    if (lead > 0) { pauseTimer = setTimeout(start, lead); } else { start(); }
  }

  function jumpTo(index) {
    if (!reading) return;
    index = Math.max(0, Math.min(timeline.length - 1, index));
    spokenChars = 0;
    for (var i = 0; i < index; i++) spokenChars += timeline[i].text.length;
    clearPauseTimer();
    try { synth.cancel(); } catch (e) {}
    playing = true;
    setListenState('playing');
    speakUnit(index);
  }

  function jumpBlock(delta) {
    if (!reading || !timeline.length) return;
    var curBlock = timeline[cursor] ? timeline[cursor].blockIndex : 0;
    var target = Math.max(0, curBlock + delta);
    for (var i = 0; i < timeline.length; i++) {
      if (timeline[i].blockIndex === target) { jumpTo(i); return; }
    }
    if (delta > 0) endReading(true);
  }

  function setupMediaSession() {
    var ms = win.navigator && win.navigator.mediaSession;
    if (!ms || typeof win.MediaMetadata !== 'function') return;
    try {
      ms.metadata = new win.MediaMetadata({
        title: stripMd(cfg.title || doc.title || ''),
        artist: texts.mediaArtist,
        album: cfg.siteName || 'FranksFinanzcheck'
      });
      ms.setActionHandler('play', function () { if (reading && !playing) resumeReading(); else if (!reading) startReading(); });
      ms.setActionHandler('pause', function () { if (reading && playing) pauseReading(); });
      ms.setActionHandler('stop', function () { endReading(true); });
      ms.setActionHandler('previoustrack', function () { jumpBlock(-1); });
      ms.setActionHandler('nexttrack', function () { jumpBlock(1); });
      ms.setActionHandler('seekbackward', function () { jumpTo(cursor - 1); });
      ms.setActionHandler('seekforward', function () { jumpTo(cursor + 1); });
    } catch (e) {}
  }

  function startReading(fromIndex) {
    if (!speechSupported) { setStatus(texts.unsupported); return; }
    currentLang = detectArticleLanguage();
    texts = I18N[currentLang] || I18N.de;
    errorStreak = 0;
    calibrateQuality();
    maleVoice = pickMaleVoice(currentLang);

    blocks = collectBlocks();
    if (!blocks.length) { setStatus(texts.noText); return; }
    buildTimeline();
    if (!timeline.length) { setStatus(texts.noText); return; }

    reading = true;
    playing = true;
    spokenChars = 0;
    var startIdx = 0;
    if (typeof fromIndex === 'number' && fromIndex > 0 && fromIndex < timeline.length) {
      startIdx = fromIndex;
      for (var i = 0; i < startIdx; i++) spokenChars += timeline[i].text.length;
    }
    cursor = startIdx;
    try { synth.cancel(); } catch (e) {}
    setListenState('playing');
    setStatus(startIdx > 0 ? texts.resumedPos : texts.started);
    setupMediaSession();
    startKeepAlive();
    speakUnit(startIdx);
  }

  function pauseReading() {
    if (!reading) return;
    playing = false;
    clearPauseTimer();
    if (speechSupported) { try { synth.pause(); } catch (e) {} }
    setListenState('paused');
    setStatus(texts.paused);
  }

  function resumeReading() {
    if (!reading) return;
    playing = true;
    setListenState('playing');
    setStatus(texts.resumed);
    if (speechSupported) {
      try { synth.resume(); } catch (e) {}
      // Safari/Chrome-Härtung: hängt die Queue, Einheit neu starten
      setTimeout(function () {
        if (reading && playing && synth && !synth.speaking && !synth.pending) speakUnit(cursor);
      }, 260);
    }
  }

  function endReading(announce) {
    reading = false;
    playing = false;
    clearPauseTimer();
    stopKeepAlive();
    if (speechSupported) { try { synth.cancel(); } catch (e) {} }
    clearHighlight();
    setListenState('idle');
    storeDel(STORE_POS);
    if (announce) setStatus(texts.finished);
  }

  function startKeepAlive() {
    stopKeepAlive();
    if (!speechSupported) return;
    // Chrome bricht die Synthese nach ~15 s ab: regelmäßig auffrischen
    keepAliveId = setInterval(function () {
      if (!reading || !playing) return;
      try {
        if (synth.speaking) { synth.pause(); synth.resume(); }
        else if (!synth.pending && !pauseTimer) { speakUnit(cursor + 1); }
      } catch (e) {}
    }, 9000);
  }

  function stopKeepAlive() { if (keepAliveId) { clearInterval(keepAliveId); keepAliveId = null; } }

  /* ---------- Bedienelemente ---------- */
  listenBtn.addEventListener('click', function () {
    if (!reading) {
      var saved = parseInt(storeGet(STORE_POS) || '0', 10);
      startReading(saved > 0 ? saved : 0);
    } else if (playing) pauseReading();
    else resumeReading();
  });

  if (stopBtn) stopBtn.addEventListener('click', function () { endReading(true); });
  if (prevBtn) prevBtn.addEventListener('click', function () { jumpBlock(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function () { jumpBlock(1); });

  // Klick-to-Listen: an beliebiger Stelle einsteigen (auch im Ruhezustand)
  var contentContainer = doc.querySelector('.post-content') || doc.querySelector('.md-content');
  if (contentContainer) {
    contentContainer.addEventListener('dblclick', function (e) {
      var target = e.target.closest('tr, p, h2, h3, h4, li, blockquote, .ff-tarif-card, .ff-einspar-box, .ff-kurzantwort, .callout');
      if (!target) return;
      if (!reading) { startReading(0); }
      for (var i = 0; i < timeline.length; i++) {
        if (timeline[i].block.el === target || (timeline[i].block.el && timeline[i].block.el.contains(target))) { jumpTo(i); return; }
      }
    });
    contentContainer.addEventListener('click', function (e) {
      if (!reading) return;
      var target = e.target.closest('tr, p, h2, h3, h4, li, blockquote, .ff-tarif-card, .ff-einspar-box, .ff-kurzantwort, .callout');
      if (!target || e.target.closest('a, button, input, select, textarea')) return;
      for (var i = 0; i < timeline.length; i++) {
        if (timeline[i].block.el === target || (timeline[i].block.el && timeline[i].block.el.contains(target))) { jumpTo(i); return; }
      }
    });
  }

  /* ---------- Stimmen-Initialisierung & Auto-Kalibrierung ----------
     Bewusst ohne Tastatur-Kurzbefehle: Bedienung erfolgt ausschließlich
     über die sichtbaren, barrierefreien Schaltflächen (Tab + Enter/Leertaste). */
  function refreshVoices() {
    calibrateQuality();
    maleVoice = pickMaleVoice(currentLang);
  }

  if (speechSupported) {
    refreshVoices();
    if (typeof synth.onvoiceschanged !== 'undefined') {
      synth.onvoiceschanged = refreshVoices;
    }
    // Nachzügler-Stimmen (Chrome lädt asynchron)
    setTimeout(refreshVoices, 900);
    setTimeout(refreshVoices, 2500);
  } else if (toolbar.classList) {
    toolbar.classList.add('ff-reader-toolbar--unsupported');
  }

  // Bei Tab-Wechsel sauber pausieren, statt zu stottern
  doc.addEventListener('visibilitychange', function () {
    if (doc.hidden && reading && playing) pauseReading();
  });

  win.addEventListener('pagehide', function () { if (reading) endReading(false); });
  win.addEventListener('beforeunload', function () { if (reading) { try { synth.cancel(); } catch (e) {} } });

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
