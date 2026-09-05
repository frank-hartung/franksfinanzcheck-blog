/* ============================================================
   FranksFinanzcheck — FF Voice Studio (Lesehilfen, Generation 2)
   05.09.2026 — Profi-Agentur-Standard
   ------------------------------------------------------------
   VORLESEN
     Zwei garantierte Tonpfade, eine Regie, kein Umschalter:
       (a) STUDIO-TONSPUR — vorab vertonte MP3 (männliche DE-/EN-
           Stimme, serverseitig erzeugt durch
           scripts/ff_voice_audio.py) im nativen HTML5-Player.
           Identischer Klang auf iPhone, iPad, Mac, Android,
           Windows/Linux und in Chrome, Safari, Firefox, Edge.
       (b) BROWSER-ENGINE — lokale Web Speech API mit derselben
           Regie, wenn keine Tonspur vorliegt oder sie nicht
           ladbar ist. Nie stumm, nie eine Warteschleife.
     Männliche Stimme. Deutsch und Englisch VOLLAUTOMATISCH —
     satzniveau-genau geroutet, ohne Sprachumschalter und ohne
     Stimmen-Menü.

   KURZFASSUNG
     Verlagshaus-Kurzfassung im barrierefreien <dialog>:
     Kurzantwort, Byline, Kernaussagen, Zahlen auf einen Blick,
     Tabellen im Fokus, Inhaltsverzeichnis, Kopier-Funktion,
     Fokus-Falle, Scroll-Sperre.

   FIRST-PARTY & PRIVACY: keine Fremd-CDNs, kein Tracking, keine
   Netzwerkaufrufe zur Laufzeit — die Tonspur liegt auf dem
   eigenen Ursprung, die Browserstimme bleibt auf dem Gerät.

   BARRIEREFREIHEIT: WCAG 2.2 / BITV — Rollen, aria-live-Status,
   Fokus-Sichtbarkeit, Fokus-Falle, Tastatursteuerung,
   prefers-reduced-motion, sichtbare Live-Markierung.

   VERTRAG MIT DEM GENERATOR (scripts/ff_voice_audio.py):
     <script type="application/json" id="ff-voice-track-config">
     { "src": "...", "version": "...", "voice": {...},
       "duration": ms,
       "chunks": [ { "b": blockIndex, "t0": ms, "t1": ms, "lang": "de" } ] }
     `b` ist der 0-basierte Blockindex in Lesereihenfolge
     (0 = Anmoderation, letzter = Abmoderation) — exakt die
     Reihenfolge von collectBlocks(). Die Parität zwischen
     Generator und Reader wird durch scripts/ff_voice_parity_check.py
     erzwungen.
============================================================ */
(function () {
  'use strict';

  var doc = document;
  var win = window;

  /* ============================================================
     1 · KONFIGURATION
     ============================================================ */

  var VOICE_VERSION = '2026.09.05-a';

  var cfgEl = doc.getElementById('ff-voice-config');
  if (!cfgEl) return;

  var cfg = {};
  try { cfg = JSON.parse(cfgEl.textContent || '{}') || {}; } catch (e) { cfg = {}; }

  // Studio-Tonspur: eigener, austauschbarer Config-Block. Fehlt er,
  // bleibt der Browser-Pfad aktiv (kostenloser Sofort-Fallback).
  var trackEl = doc.getElementById('ff-voice-track-config');
  if (trackEl) {
    try {
      var trackCfg = JSON.parse(trackEl.textContent || '{}') || {};
      if (trackCfg && trackCfg.audio) cfg.audio = trackCfg.audio;
      else if (trackCfg && trackCfg.src) cfg.audio = trackCfg;
    } catch (e) {}
  }

  var bar = doc.getElementById('ff-voice-bar');
  var slot = doc.getElementById('ff-voice-slot');
  var playBtn = doc.getElementById('ff-voice-play');
  var playLabel = doc.getElementById('ff-voice-play-label');
  var prevBtn = doc.getElementById('ff-voice-prev');
  var nextBtn = doc.getElementById('ff-voice-next');
  var stopBtn = doc.getElementById('ff-voice-stop');
  var summaryBtn = doc.getElementById('ff-voice-summary');
  var summaryLabel = doc.getElementById('ff-voice-summary-label');
  var statusEl = doc.getElementById('ff-voice-status');
  var remainEl = doc.getElementById('ff-voice-remaining');
  var progressEl = doc.getElementById('ff-voice-progress');

  if (!bar || !playBtn || !summaryBtn) return;

  var reducedMotion = !!(win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var STORE_POS = 'ff-voice-pos:' + String(cfg.slug || cfg.permalink || doc.location.pathname);

  /* ============================================================
     2 · ZWEISPRACHIGKEIT (DE / EN) — ohne Umschalter
     ============================================================ */

  var I18N = {
    de: {
      play: 'Vorlesen', pause: 'Pausieren', resume: 'Weiterlesen', stop: 'Beenden',
      playAria: 'Artikel vorlesen (männliche Stimme)',
      playAriaNeutral: 'Artikel vorlesen (Stimme deines Geräts)',
      pauseAria: 'Vorlesen pausieren', resumeAria: 'Vorlesen fortsetzen', stopAria: 'Vorlesen beenden',
      summaryBtn: 'Kurzfassung', summaryAria: 'Kurzfassung des Artikels anzeigen',
      unsupported: 'Vorlesen wird von diesem Browser nicht unterstützt.',
      noText: 'Kein vorlesbarer Text gefunden.',
      started: 'Vorlesen gestartet.',
      startedTrack: 'Studio-Tonspur läuft.',
      voiceActive: 'Männliche Stimme aktiv.',
      voiceFallback: 'Vorlesen gestartet; dein Browser stellt die verfügbare Stimme bereit.',
      voiceLoading: 'Männliche Stimme wird geladen …',
      sectionError: 'Dieser Abschnitt konnte nicht abgespielt werden; es geht weiter.',
      paused: 'Vorlesen pausiert.', resumed: 'Vorlesen fortgesetzt.',
      finished: 'Vorlesen beendet.', resumedPos: 'Vorlesen an der zuletzt gehörten Stelle fortgesetzt.',
      remaining: 'noch ca. {min} Min.',
      mediaTitle: '{title} – FranksFinanzcheck',
      mediaArtist: 'FranksFinanzcheck – Artikel zum Hören',
      introLine: '{title}. Ein Beitrag von FranksFinanzcheck. Hördauer etwa {duration}.',
      durationMinutes: '{n} Minuten', durationMinuteOne: 'eine Minute', durationUnknown: 'einige Minuten',
      outroLine: 'Ende des Beitrags. Vielen Dank fürs Zuhören bei FranksFinanzcheck.',
      listItemNum: 'Punkt {n}:',
      cueShortAnswer: 'Kurzantwort:', cueCorrection: 'Korrekturhinweis:', cueSaving: 'Sparpotenzial:',
      cueTariff: 'Tarif im Überblick:', cueWarning: 'Achtung:', cueNote: 'Hinweis:',
      columnLabel: 'Spalte', rowLabel: 'Zeile',
      tableHeaders: 'Die Spalten lauten: {headers}.',
      tableIntro: 'Tabelle: {title}. Übersicht mit {cols} Spalten und {rows} Zeilen.',
      tableIntroOne: 'Tabelle: {title}. Übersicht mit {cols} Spalten und einer Zeile.',
      tableRow: 'Zeile {row} von {total}. {content}.',
      tableSum: 'Zusammengerechnet: {content}.',
      tableOutro: 'Ende der Tabelle {title}.',
      tableDefault: 'Übersichtstabelle',
      prevAria: 'Vorheriger Abschnitt', nextAria: 'Nächster Abschnitt',
      // Kurzfassung
      summaryEyebrow: 'Kurzfassung',
      summaryQuick: 'Das Wichtigste in 30 Sekunden',
      summaryKeypoints: 'Die Kernaussagen',
      summaryFigures: 'Auf einen Blick – die wichtigsten Zahlen',
      summaryTables: 'Tabellen & Übersichten im Fokus',
      summaryToc: 'In diesem Artikel',
      summaryCopy: 'Kurzfassung kopieren',
      summaryCopied: 'Kopiert',
      summaryCopyFail: 'Kopieren fehlgeschlagen',
      summaryReadFull: 'Ganzen Artikel lesen',
      summaryClose: 'Kurzfassung schließen',
      summaryAuthor: 'Autor: {name}',
      summaryStand: 'Stand: {date}',
      summaryUpdated: 'Aktualisiert: {date}',
      summaryEmpty: 'Für diesen Artikel liegt derzeit keine Kurzfassung vor.',
      summaryRowCount: '{count} Zeilen',
      summaryRowCountOne: '1 Zeile',
      summaryReadingTime: 'ca. {time} Min. Lesezeit',
      summaryWords: '{count} Wörter',
      summaryJump: 'Zum Abschnitt'
    },
    en: {
      play: 'Listen', pause: 'Pause', resume: 'Resume', stop: 'Stop',
      playAria: 'Read article aloud (male voice)',
      playAriaNeutral: 'Read article aloud (voice provided by your device)',
      pauseAria: 'Pause speech', resumeAria: 'Resume speech', stopAria: 'Stop speech',
      summaryBtn: 'Summary', summaryAria: 'Show article summary',
      unsupported: 'Speech synthesis is not supported by this browser.',
      noText: 'No readable text found.',
      started: 'Audio playback started.',
      startedTrack: 'Studio audio track playing.',
      voiceActive: 'Male voice active.',
      voiceFallback: 'Playback started; your browser provides the available voice.',
      voiceLoading: 'Loading a male voice …',
      sectionError: 'This section could not be played; continuing.',
      paused: 'Audio playback paused.', resumed: 'Audio playback resumed.',
      finished: 'Audio playback completed.', resumedPos: 'Resumed from your last listening position.',
      remaining: 'approx. {min} min left',
      mediaTitle: '{title} – FranksFinanzcheck',
      mediaArtist: 'FranksFinanzcheck – Article Audio',
      introLine: '{title}. An article by FranksFinanzcheck. Listening time about {duration}.',
      durationMinutes: '{n} minutes', durationMinuteOne: 'one minute', durationUnknown: 'a few minutes',
      outroLine: 'End of article. Thank you for listening to FranksFinanzcheck.',
      listItemNum: 'Point {n}:',
      cueShortAnswer: 'Short answer:', cueCorrection: 'Correction:', cueSaving: 'Savings potential:',
      cueTariff: 'Tariff at a glance:', cueWarning: 'Attention:', cueNote: 'Note:',
      columnLabel: 'Column', rowLabel: 'Row',
      tableHeaders: 'The columns are: {headers}.',
      tableIntro: 'Table: {title}. Overview with {cols} columns and {rows} rows.',
      tableIntroOne: 'Table: {title}. Overview with {cols} columns and one row.',
      tableRow: 'Row {row} of {total}. {content}.',
      tableSum: 'In total: {content}.',
      tableOutro: 'End of table {title}.',
      tableDefault: 'Overview Table',
      prevAria: 'Previous section', nextAria: 'Next section',
      summaryEyebrow: 'Summary',
      summaryQuick: 'Key Takeaways in 30 Seconds',
      summaryKeypoints: 'Key Highlights',
      summaryFigures: 'Key Figures & Data',
      summaryTables: 'Tables & Overviews in Focus',
      summaryToc: 'In this article',
      summaryCopy: 'Copy summary',
      summaryCopied: 'Copied',
      summaryCopyFail: 'Copy failed',
      summaryReadFull: 'Read full article',
      summaryClose: 'Close summary',
      summaryAuthor: 'Author: {name}',
      summaryStand: 'As of {date}',
      summaryUpdated: 'Updated: {date}',
      summaryEmpty: 'No summary is currently available for this article.',
      summaryRowCount: '{count} rows',
      summaryRowCountOne: '1 row',
      summaryReadingTime: 'approx. {time} min read',
      summaryWords: '{count} words',
      summaryJump: 'Go to section'
    }
  };

  /* ============================================================
     3 · GRUNDWERKZEUGE
     ============================================================ */

  function qsa(sel, ctx) {
    var node = ctx || doc;
    if (!node || typeof node.querySelectorAll !== 'function') return [];
    return Array.prototype.slice.call(node.querySelectorAll(sel));
  }
  function tagOf(el) { return String((el && el.tagName) || '').toUpperCase(); }
  function hasClass(el, name) {
    return !!(el && el.classList && el.classList.contains(name));
  }
  function anyClass(el, names) {
    for (var i = 0; i < names.length; i++) { if (hasClass(el, names[i])) return true; }
    return false;
  }
  function closestOf(el, sel) {
    if (!el || typeof el.closest !== 'function') return null;
    return el.closest(sel);
  }
  function storeGet(k) { try { return win.localStorage.getItem(k); } catch (e) { return null; } }
  function storeSet(k, v) { try { win.localStorage.setItem(k, v); } catch (e) {} }
  function storeDel(k) { try { win.localStorage.removeItem(k); } catch (e) {} }
  function escapeRe(s) { return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }

  /** Sichtbarer Text eines Knotens – mit Zeilen-/Absatz-Abstand. */
  function readableText(el) {
    if (!el) return '';
    var clone = el;
    if (el.cloneNode) {
      clone = el.cloneNode(true);
      qsa('script, style, noscript, svg, [data-ff-skip-read], [aria-hidden="true"]', clone)
        .forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
      qsa('br', clone).forEach(function (n) {
        if (n.parentNode) n.parentNode.replaceChild(doc.createTextNode(' '), n);
      });
    }
    var raw = clone.textContent || clone.innerText || '';
    return raw.replace(/\u00a0/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function stripMd(s) {
    return String(s || '')
      .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
      .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
      .replace(/[*_`#>]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  }

  /* ============================================================
     4 · SPRACHERKENNUNG (DE / EN) — vollautomatisch
     ------------------------------------------------------------
     Die Seite ist einsprachig als „de“ deklariert. Ein englischer
     Artikel muss deshalb aus seinem eigenen Inhalt erkannt werden.
     Stichprobe: Titel + Description + sichtbarer Artikelfluss
     (nie der ganze Body – Footer, Navigation und verwandte
     Artikel sind deutsch und würden einen EN-Artikel zurückkippen).
     ============================================================ */

  var DE_HINTS = {
    der: 2, die: 2, das: 2, und: 2, ist: 2, sind: 2, für: 2, mit: 2, nicht: 2,
    von: 1, ein: 1, eine: 1, einen: 1, einem: 1, den: 1, dem: 1, auf: 1, zu: 1,
    im: 1, am: 1, bei: 1, auch: 1, sich: 1, sparen: 2, spart: 2, euro: 2,
    versicherung: 2, kosten: 2, vertrag: 2, vergleich: 2, wechseln: 2,
    günstig: 2, kostenlos: 2, ratgeber: 2, tabelle: 2, jahr: 1, monat: 1,
    sollte: 1, solltest: 1, müssen: 1, kann: 1, wichtig: 1, tipp: 1, prüfen: 1
  };
  var EN_HINTS = {
    the: 2, and: 2, is: 2, are: 2, for: 2, with: 2, that: 2, this: 2, your: 2, you: 2,
    from: 1, our: 1, save: 2, saving: 2, money: 2, insurance: 2, costs: 2, cost: 2,
    compare: 2, comparison: 2, guide: 2, table: 2, tariff: 1, tariffs: 1, should: 1,
    will: 1, can: 1, have: 1, more: 1, free: 1, cheap: 1, best: 1, important: 1,
    article: 1, summary: 1, read: 1, listen: 1, avoid: 1, switch: 1
  };

  function articleSample(maxChars) {
    var sample = String(cfg.title || '') + ' ' + String(cfg.description || '') + ' ';
    try {
      var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
      if (content) sample += String(content.textContent || '').slice(0, maxChars);
      else if (doc.body) sample += String(doc.body.textContent || '').slice(0, 2000);
    } catch (e) {}
    return sample;
  }

  function detectArticleLanguage() {
    var raw = String(cfg.lang || (bar && bar.getAttribute('data-page-lang')) || doc.documentElement.lang || 'de').toLowerCase();
    var base = raw.indexOf('en') === 0 ? 'en' : 'de';
    var sample = articleSample(5000).toLowerCase();
    var tokens = sample.match(/[a-zäöüß]+/g) || [];
    var de = 0, en = 0, deHits = 0, enHits = 0;
    for (var i = 0; i < tokens.length; i++) {
      var w = tokens[i];
      if (DE_HINTS[w]) { de += DE_HINTS[w]; deHits += 1; }
      if (EN_HINTS[w]) { en += EN_HINTS[w]; enHits += 1; }
      if (/[äöüß]/.test(w)) de += 2;
      if (w.length >= 6 && /(ung|keit|heit|schaft|lich|isch)$/.test(w)) de += 1;
    }
    // Die deklarierte Seitensprache ist eine Voreinstellung, kein Riegel:
    // erst eine klare EN-Mehrheit kippt einen deutsch deklarierten Artikel.
    if (base === 'de') {
      return (enHits >= 4 && en >= de + 3 && en >= Math.ceil(de * 1.25)) ? 'en' : 'de';
    }
    return (deHits >= 4 && de >= en + 3 && de >= Math.ceil(en * 1.15)) ? 'de' : 'en';
  }

  /** Satzweises Sprach-Routing (zweisprachiger Hörfunk-Moderator). */
  function sniffSentenceLang(sentence, baseLang) {
    var text = String(sentence || '');
    if (text.length < 12) return baseLang;
    var words = text.toLowerCase().match(/[a-zäöüß']+/g) || [];
    if (words.length < 3) return baseLang;
    var de = 0, en = 0;
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (DE_HINTS[w]) de += DE_HINTS[w];
      if (EN_HINTS[w]) en += EN_HINTS[w];
      if (/[äöüß]/.test(w)) de += 2;
      if (w.length >= 6 && /(ung|keit|heit|schaft|lich|isch)$/.test(w)) de += 1;
      if (w.length >= 4 && /(ing|tion|ment|ness|able|ible)$/.test(w)) en += 1;
    }
    if (baseLang === 'de') return (en >= 4 && en >= de + 2) ? 'en' : 'de';
    return (de >= 4 && de >= en + 2) ? 'de' : 'en';
  }

  var lang = detectArticleLanguage();
  var T = I18N[lang] || I18N.de;

  function durationPhrase(minutes) {
    var n = parseInt(minutes, 10);
    if (!isFinite(n) || n <= 0) return T.durationUnknown;
    return n === 1 ? T.durationMinuteOne : T.durationMinutes.replace('{n}', n);
  }

  /* ============================================================
     5 · SPRECHTEXT-NORMALISIERUNG (Aussprache-Regie)
     ------------------------------------------------------------
     Eine Redaktion schreibt „bis zu 650 €“, „12 – 24 Monate“,
     „ca. 3,5 %“, „§ 12“, „20.000 kWh“. Vorgelesen werden muss
     „bis zu 650 Euro“, „12 bis 24 Monate“, „circa 3,5 Prozent“,
     „Paragraph 12“, „20.000 Kilowattstunden“.

     Dieselbe Regelmenge liegt — wortgleich spezifiziert — in
     scripts/ff_voice_backends.py. Die Parität wird durch
     scripts/ff_voice_parity_check.py geprüft: Tonspur und
     Browserstimme müssen denselben Text sprechen.

     Prinzip: Jede Regel ersetzt ihren Treffer durch einen
     Platzhalter (\u0000n\u0000). Dadurch kann keine Folgeregel
     ein schon gesprochenes Wort erneut anfassen (Kaskadenfehler).
     ============================================================ */

  var HOLD_OPEN = '\u0000';
  var HOLD_CLOSE = '\u0001';

  var ABBREV = {
    de: [
      [/bzw\./gi, 'beziehungsweise'],
      [/zzgl\./gi, 'zuzüglich'],
      [/inkl\./gi, 'inklusive'],
      [/exkl\./gi, 'exklusiv'],
      [/ca\./gi, 'circa'],
      [/usw\./gi, 'und so weiter'],
      [/usf\./gi, 'und so fort'],
      [/vgl\./gi, 'vergleiche'],
      [/sog\./gi, 'sogenannt'],
      [/geb\./gi, 'geboren'],
      [/MwSt\./g, 'Mehrwertsteuer'],
      [/Abs\.\s?(\d+)/g, 'Absatz $1'],
      [/Nr\.\s?(\d+)/g, 'Nummer $1'],
      [/Nr\./g, 'Nummer'],
      [/Art\.\s?(\d+)/g, 'Artikel $1'],
      [/S\.\s?(\d+)/g, 'Seite $1'],
      [/Abb\.\s?(\d+)/g, 'Abbildung $1'],
      [/Tab\.\s?(\d+)/g, 'Tabelle $1'],
      [/\bz\.\s?B\./gi, 'zum Beispiel'],
      [/\bu\.\s?a\./gi, 'unter anderem'],
      [/\bd\.\s?h\./gi, 'das heißt'],
      [/\bi\.\s?d\.\s?R\./gi, 'in der Regel'],
      [/\bo\.\s?g\./gi, 'oben genannt'],
      [/€\s?\/\s?(Monat|Jahr|kWh|Person)/gi, 'Euro pro $1'],
      [/ct\/\s?kWh/gi, 'Cent pro Kilowattstunde'],
      [/kWh\/a/g, 'Kilowattstunden pro Jahr'],
      [/kWh/g, 'Kilowattstunden'],
      [/kWp/g, 'Kilowatt Peak'],
      [/m²/g, 'Quadratmeter'],
      [/m³/g, 'Kubikmeter'],
      [/km\/h/g, 'Kilometer pro Stunde'],
      [/Mio\.\s?€/g, 'Millionen Euro'],
      [/Mrd\.\s?€/g, 'Milliarden Euro'],
      [/\bMio\./g, 'Millionen'],
      [/\bMrd\./g, 'Milliarden'],
      [/\bTsd\./g, 'Tausend'],
      [/§\s?(\d+)/g, 'Paragraph $1'],
      [/€/g, 'Euro'],
      [/(\d)\s?%/g, '$1 Prozent'],
      [/%/g, 'Prozent']
    ],
    en: [
      [/\be\.\s?g\./gi, 'for example'],
      [/\bi\.\s?e\./gi, 'that is'],
      [/\betc\./gi, 'and so on'],
      [/\bapprox\./gi, 'approximately'],
      [/\bvs\./gi, 'versus'],
      [/\bNo\.\s?(\d+)/g, 'number $1'],
      [/\bMr\./g, 'Mister'],
      [/\bMrs\./g, 'Misses'],
      [/kWh\/a/g, 'kilowatt hours per year'],
      [/kWh/gi, 'kilowatt hours'],
      [/kWp/gi, 'kilowatt peak'],
      [/sq\s?m/gi, 'square meters'],
      [/cu\s?m/gi, 'cubic meters'],
      [/£\s?(\d[\d.,]*)/g, '$1 pounds'],
      [/\$(\d[\d.,]*)/g, '$1 dollars'],
      [/(\d[\d.,]*)\s?\$/g, '$1 dollars'],
      [/(\d)\s?%/g, '$1 percent'],
      [/%/g, 'percent'],
      [/§\s?(\d+)/g, 'section $1']
    ]
  };

  var MONTHS_DE = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
    'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
  var MONTHS_EN = ['January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'];

  function unhold(text, store) {
    return String(text).replace(new RegExp(HOLD_OPEN + '(\\d+)' + HOLD_CLOSE, 'g'), function (m, i) {
      var v = store[parseInt(i, 10)];
      return v == null ? '' : v;
    });
  }

  function normalizeUrls(text, hold, L) {
    var out = String(text);
    // E-Mail-Adressen
    out = out.replace(/[\w.+-]+@[\w-]+\.[\w.-]+/g, function (m) {
      return hold(m.replace(/@/g, L === 'de' ? ' at ' : ' at ').replace(/\./g, L === 'de' ? ' Punkt ' : ' dot '));
    });
    // Vollständige URLs
    out = out.replace(/\bhttps?:\/\/[^\s<>"')]+/gi, function (m) {
      var spoken = m.replace(/^https?:\/\//i, '').replace(/\/$/, '');
      spoken = spoken.replace(/\./g, L === 'de' ? ' Punkt ' : ' dot ').replace(/\//g, ' ');
      return hold(spoken);
    });
    // Nackte Domains (z. B. franksfinanzcheck.de)
    out = out.replace(/\b([\w-]+\.(?:de|com|org|net|io|eu|info|blog))\b/gi, function (m, dom) {
      return hold(m.replace(/\./g, L === 'de' ? ' Punkt ' : ' dot '));
    });
    return out;
  }

  function normalizeDates(text, hold, L) {
    var out = String(text);
    var months = L === 'en' ? MONTHS_EN : MONTHS_DE;
    // TT.MM.JJJJ (DE) bzw. MM/DD/YYYY (EN)
    out = out.replace(/\b(\d{1,2})[.\/](\d{1,2})[.\/](\d{4})\b/g, function (m, a, b, c) {
      var first = parseInt(a, 10);
      var second = parseInt(b, 10);
      var day, month;
      if (L === 'en') { month = first; day = second; } else { day = first; month = second; }
      if (month >= 1 && month <= 12) {
        return hold(day + '. ' + months[month - 1] + ' ' + c);
      }
      return m;
    });
    // TT.MM. (ohne Jahr)
    out = out.replace(/\b(\d{1,2})\.(\d{1,2})\.(?!\d)/g, function (m, d, mo) {
      var month = parseInt(mo, 10);
      if (month >= 1 && month <= 12) return hold(parseInt(d, 10) + '. ' + months[month - 1]);
      return m;
    });
    return out;
  }

  function normalizeTimes(text, hold, L) {
    var out = String(text);
    out = out.replace(/\b(\d{1,2}):(\d{2})\s?(Uhr)?\b/g, function (m, h, min) {
      var hh = parseInt(h, 10);
      var mm = parseInt(min, 10);
      if (L === 'de') {
        if (mm === 0) return hold(hh + ' Uhr');
        return hold(hh + ' Uhr ' + mm);
      }
      if (mm === 0) return hold(hh + " o'clock");
      return hold(hh + ' ' + (mm < 10 ? 'oh ' + mm : mm));
    });
    return out;
  }

  function normalizeRanges(text, hold, L) {
    var out = String(text);
    var word = L === 'de' ? ' bis ' : ' to ';
    // 12 – 24 / 12 - 24 / 12 bis 24 (nur mit Trennzeichen, nie bei „Covid-19“)
    out = out.replace(/(\d)\s?(?:–|—|\-)\s?(\d)/g, function (m, a, b) {
      return a + word + b;
    });
    return out;
  }

  function normalizeNumbers(text, hold, L) {
    var out = String(text);
    /* Ein Zeilenumbruch im Tausenderblock („20 000 kWh“) würde als Pause
       gelesen. Er wird zum sprachrichtigen Trennzeichen normalisiert:
       DE „20.000“, EN „20,000“. */
    var sep = (L === 'de') ? '.' : ',';
    out = out.replace(/(\d)\s(\d{3})\b/g, '$1' + sep + '$2');
    // Bereiche mit „bis“ bleiben unangetastet, Prozentzeichen schon ersetzt.
    return out;
  }

  function normalizeSymbols(text, hold, L) {
    var out = String(text);
    out = out.replace(/&/g, L === 'de' ? ' und ' : ' and ');
    out = out.replace(/\sx\s(?=\d)/g, ' mal ');
    out = out.replace(/\+/g, ' plus ');
    out = out.replace(/=/g, ' gleich ');
    out = out.replace(/[\u201c\u201d\u201e]/g, '"');
    out = out.replace(/[\u2018\u2019\u201a]/g, "'");
    return out;
  }

  /**
   * Überführt Schreibsprache in Sprechsprache.
   * @param {string} text
   * @param {string} lng 'de' | 'en'
   */
  function speechNormalize(text, lng) {
    var L = (lng === 'en') ? 'en' : 'de';
    var out = String(text == null ? '' : text);
    if (!out) return '';

    var store = [];
    function hold(value) {
      store.push(String(value));
      return HOLD_OPEN + (store.length - 1) + HOLD_CLOSE;
    }

    // HTML-Entitäten & Steuerzeichen
    out = out.replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&')
      .replace(/&szlig;/g, 'ß').replace(/&uuml;/g, 'ü').replace(/&ouml;/g, 'ö')
      .replace(/&auml;/g, 'ä').replace(/&euro;/g, '€').replace(/&[a-zA-Z]+;/g, ' ');
    out = out.replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f]/g, ' ');
    out = out.replace(/[\u2013\u2014]/g, '–');

    out = normalizeUrls(out, hold, L);
    out = normalizeDates(out, hold, L);
    out = normalizeTimes(out, hold, L);

    // Abkürzungen, Einheiten, Währungen, Paragraphen
    var rules = ABBREV[L] || ABBREV.de;
    for (var i = 0; i < rules.length; i++) out = out.replace(rules[i][0], rules[i][1]);

    out = normalizeRanges(out, hold, L);
    out = normalizeNumbers(out, hold, L);
    out = normalizeSymbols(out, hold, L);

    // Mehrfach-Leerzeichen & doppelte Satzzeichen
    out = out.replace(/\s+/g, ' ').trim();
    out = out.replace(/\.{2,}(?!\.)/g, '.');
    out = out.replace(/\s+([.,;:!?])/g, '$1');

    return unhold(out, store).replace(/\s+/g, ' ').trim();
  }

  /* ============================================================
     6 · DOKUMENTMODELL — Was wird in welcher Reihenfolge gelesen?
     ------------------------------------------------------------
     Die Reihenfolge ist VERTRAG zwischen Reader, Generator und
     Kurzfassung. Sie lautet:

       1. Anmoderation (Titel + Hördauer)
       2. Redaktionelle Vorab-Boxen vor dem Artikel
          (.ff-korrektur, .ff-kurzantwort)
       3. Alle Blöcke des Artikels in DOM-Reihenfolge
       4. Abmoderation

     Der Generator (scripts/ff_voice_audio.py) baut exakt diese
     Reihenfolge serverseitig nach; scripts/ff_voice_parity_check.py
     vergleicht beide Listen Block für Block.
     ============================================================ */

  var CONTENT_SELECTOR = [
    'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'blockquote',
    'table', '[role="table"]', '[role="grid"]', '[role="treegrid"]',
    '.ff-table-scroll', '.ff-tv-tablewrap', '.ff-es-tablewrap',
    '.wp-block-table', '.table-wrapper', '.table-responsive',
    'strong', 'b',
    '.ff-tarif-card', '.ff-einspar-box', '.ff-kurzantwort', '.ff-korrektur', '.callout',
    '.ff-tv-footnote', '.ff-es-footnote'
  ].join(', ');

  var SKIP_SELECTOR = '[data-ff-skip-read], .ff-voice-bar, nav, .toc, .ff-toc';
  var BOX_CLASSES = ['ff-tarif-card', 'ff-einspar-box', 'ff-kurzantwort', 'ff-korrektur', 'callout'];
  var TABLE_WRAPPERS = 'table, [role="table"], [role="grid"], .ff-table-scroll, .ff-tv-tablewrap, .ff-es-tablewrap, .wp-block-table, .table-wrapper, .table-responsive';

  function isReaderSkipped(el) {
    if (!el) return true;
    if (el.getAttribute && el.getAttribute('data-ff-skip-read') !== null) return true;
    if (el.getAttribute && el.getAttribute('aria-hidden') === 'true') return true;
    if (closestOf(el, SKIP_SELECTOR)) return true;
    return false;
  }

  function isTableLike(el) {
    if (!el) return false;
    var t = tagOf(el);
    if (t === 'TABLE') return true;
    var role = (el.getAttribute && el.getAttribute('role')) || '';
    if (role === 'table' || role === 'grid' || role === 'treegrid') return true;
    if (anyClass(el, ['ff-table-scroll', 'ff-tv-tablewrap', 'ff-es-tablewrap'])) return true;
    // Wrapper, die genau eine Tabelle enthalten, gelten als Tabelle.
    if (anyClass(el, ['wp-block-table', 'table-wrapper', 'table-responsive'])) {
      var inner = qsa('table', el);
      if (inner.length === 1) return true;
    }
    return false;
  }

  function innerTable(el) {
    if (!el) return null;
    if (tagOf(el) === 'TABLE') return el;
    var tables = qsa('table', el);
    if (tables.length) return tables[0];
    return el; // ARIA-Tabelle (role="table" auf div/grid)
  }

  function isStandaloneEmphasis(el) {
    // Fettdruck wird an SEINER Stelle gesprochen, wenn er nicht nur
    // ein einzelnes Wort im Satz ist, sondern ein eigener Block
    // (z. B. ein ganzer Absatz in Fettschrift oder ein Merksatz).
    if (!el) return false;
    var text = readableText(el);
    if (text.length < 12) return false;
    var parent = el.parentNode;
    if (!parent) return false;
    var siblings = parent.childNodes.length;
    var parentText = readableText(parent);
    // Steht der Fettdruck praktisch allein im Elternelement?
    return text.length >= Math.max(12, parentText.length - 2) || siblings <= 2;
  }

  /* ---------- Tabellenmodell -------------------------------- */

  function cellSpan(cell) {
    var span = 1;
    if (cell && cell.getAttribute) {
      var v = parseInt(cell.getAttribute('colspan'), 10);
      if (isFinite(v) && v > 1) span = v;
    }
    return span;
  }

  function isHeaderCell(cell) {
    if (!cell) return false;
    if (tagOf(cell) === 'TH') return true;
    var scope = (cell.getAttribute && cell.getAttribute('scope')) || '';
    if (scope === 'col' || scope === 'row' || scope === 'colgroup' || scope === 'rowgroup') return true;
    var role = (cell.getAttribute && cell.getAttribute('role')) || '';
    return role === 'columnheader' || role === 'rowheader';
  }

  function rowCells(tr) {
    if (!tr) return [];
    return qsa('th, td, [role="columnheader"], [role="rowheader"], [role="cell"], [role="gridcell"]', tr);
  }

  function tableRows(tableEl) {
    var rows = [];
    var seen = [];
    function push(tr, kind) {
      if (!tr || seen.indexOf(tr) !== -1) return;
      seen.push(tr);
      rows.push({ tr: tr, kind: kind });
    }
    qsa('thead tr', tableEl).forEach(function (tr) { push(tr, 'head'); });
    qsa('tbody tr', tableEl).forEach(function (tr) { push(tr, 'body'); });
    qsa('tfoot tr', tableEl).forEach(function (tr) { push(tr, 'foot'); });
    qsa('tr', tableEl).forEach(function (tr) {
      if (seen.indexOf(tr) === -1) push(tr, rows.length === 0 ? 'head' : 'body');
    });
    return rows;
  }

  function tableTitle(tableEl) {
    var cap = qsa('caption', tableEl)[0];
    if (cap && readableText(cap)) return readableText(cap);
    var aria = tableEl.getAttribute && tableEl.getAttribute('aria-label');
    if (aria) return aria;
    // Nächstgelegene Überschrift davor (Tarifvergleich/Einspartabelle)
    /* Die Premium-Übersichten setzen ihren Titel (.ff-tv-title /
       .ff-es-title) AUSSERHALB des Tablewrappers. Deshalb wird nach oben
       gestiegen, bis ein Vorfahre einen Titel trägt. */
    var node = tableEl;
    for (var up = 0; up < 4 && node; up++) {
      var wrap = closestOf(node, '.ff-tarifvergleich, .ff-einspar, .ff-tv-tablewrap, .ff-es-tablewrap, .ff-table-scroll');
      if (!wrap) break;
      var h = qsa('.ff-tv-title, .ff-es-title, caption, h3, h4', wrap)[0];
      if (h && h !== tableEl && readableText(h)) return readableText(h);
      node = wrap.parentElement;
    }
    var prev = tableEl.previousElementSibling;
    var guard = 0;
    while (prev && guard++ < 4) {
      if (/^H[23456]$/.test(tagOf(prev)) && readableText(prev)) return readableText(prev);
      prev = prev.previousElementSibling;
    }
    return '';
  }

  function buildTableModel(tableEl) {
    var rows = tableRows(tableEl);
    var headers = [];
    var body = [];
    var foot = [];
    var headerFound = false;

    rows.forEach(function (r) {
      var cells = rowCells(r.tr);
      var texts = cells.map(function (c) { return readableText(c); });
      var allHead = texts.length > 0 && cells.every(isHeaderCell);
      if (r.kind === 'head' || (!headerFound && allHead)) {
        if (!headerFound) { headers = texts; headerFound = true; }
        else body.push({ cells: texts, kind: 'body' });
        return;
      }
      if (r.kind === 'foot') { foot.push({ cells: texts, kind: 'foot' }); return; }
      body.push({ cells: texts, kind: 'body' });
    });

    var colCount = Math.max(
      headers.length,
      body.reduce(function (m, r) { return Math.max(m, r.cells.length); }, 0),
      foot.reduce(function (m, r) { return Math.max(m, r.cells.length); }, 0)
    );

    return {
      title: tableTitle(tableEl) || T.tableDefault,
      headers: headers,
      rows: body,
      foot: foot,
      colCount: colCount
    };
  }

  function cellSpeech(name, value, index, L) {
    var label = name && String(name).length ? String(name) : (T.columnLabel + ' ' + (index + 1));
    var val = value == null || String(value) === '' ? '' : String(value);
    if (!val) return '';
    return label + ': ' + val;
  }

  /** Eine Tabelle wird als Zusammenschau gesprochen — zeilenweise. */
  function extractTableBlocks(tableEl, blockLang) {
    var L = blockLang;
    var model = buildTableModel(tableEl);
    var out = [];
    var title = model.title || T.tableDefault;

    var rowCount = model.rows.length;
    out.push({
      el: tableEl,
      lang: L,
      type: 'table-intro',
      text: (rowCount === 1 ? T.tableIntroOne : T.tableIntro)
        .replace('{title}', title)
        .replace('{cols}', model.colCount)
        .replace('{rows}', rowCount)
    });

    if (model.headers.length) {
      out.push({
        el: tableEl,
        lang: L,
        type: 'table-header',
        text: T.tableHeaders.replace('{headers}', model.headers.join(', '))
      });
    }

    model.rows.forEach(function (row, i) {
      var parts = [];
      for (var c = 0; c < Math.max(row.cells.length, model.colCount); c++) {
        var spoken = cellSpeech(model.headers[c], row.cells[c], c, L);
        if (spoken) parts.push(spoken);
      }
      if (!parts.length) return;
      out.push({
        el: row.tr,
        lang: L,
        type: 'table-row',
        text: T.tableRow
          .replace('{row}', i + 1)
          .replace('{total}', rowCount)
          .replace('{content}', parts.join(', '))
      });
    });

    model.foot.forEach(function (row) {
      var parts = [];
      for (var c = 0; c < row.cells.length; c++) {
        var spoken = cellSpeech(model.headers[c], row.cells[c], c, L);
        if (spoken) parts.push(spoken);
      }
      if (!parts.length) return;
      out.push({
        el: row.tr,
        lang: L,
        type: 'table-sum',
        text: T.tableSum.replace('{content}', parts.join(', '))
      });
    });

    out.push({
      el: tableEl,
      lang: L,
      type: 'table-outro',
      text: T.tableOutro.replace('{title}', title)
    });

    return out;
  }

  /* ---------- Blöcke vor dem Artikel ------------------------ */

  function preContentBoxes() {
    var scope = doc.body || doc;
    return qsa('.ff-korrektur, .ff-kurzantwort', scope).filter(function (el) {
      if (closestOf(el, '.post-content, .md-content')) return false;
      if (closestOf(el, SKIP_SELECTOR)) return false;
      return true;
    });
  }

  function boxTextWithoutHeadline(box) {
    if (!box) return '';
    var probe = box;
    if (box.cloneNode) {
      probe = box.cloneNode(true);
      qsa('.ff-kurzantwort__head, .ff-kurzantwort__label, .ff-kurzantwort__icon, .ff-kurzantwort__eyebrow', probe)
        .forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
    }
    return readableText(probe);
  }

  /* ---------- Die Lesereihenfolge --------------------------- */

  function collectBlocks() {
    var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
    if (!content) return [];
    var out = [];
    var done = [];

    // (1) Anmoderation
    out.push({
      el: bar,
      lang: lang,
      type: 'intro',
      text: T.introLine
        .replace('{title}', stripMd(cfg.title || doc.title || ''))
        .replace('{duration}', durationPhrase(cfg.readingTime))
    });

    // (2) Redaktionelle Vorab-Boxen
    preContentBoxes().forEach(function (box) {
      var text = boxTextWithoutHeadline(box);
      if (text.length <= 5) return;
      var isKorrektur = hasClass(box, 'ff-korrektur');
      out.push({
        el: box,
        lang: lang,
        type: isKorrektur ? 'warning' : 'callout',
        text: (isKorrektur ? T.cueCorrection : T.cueShortAnswer) + ' ' + text
      });
    });

    // (3) Artikelblöcke in DOM-Reihenfolge
    var nodes = qsa(CONTENT_SELECTOR, content);
    nodes.forEach(function (el) {
      if (isReaderSkipped(el)) return;
      if (closestOf(el, 'figure') && !isTableLike(el)) return;
      // Premium-Übersichten liefern denselben Inhalt zweimal (Tabelle
      // für Desktop, Kartenstapel für Mobil). Die Tabelle ist die
      // vollständigere Quelle — der Kartenstapel bleibt stumm.
      if (closestOf(el, '.ff-tv-cards, .ff-es-cards')) return;

      var elLang = sniffLangOf(el, lang);

      if (isTableLike(el)) {
        var tbl = innerTable(el);
        if (!tbl || done.indexOf(tbl) !== -1) return;
        done.push(tbl);
        extractTableBlocks(tbl, elLang).forEach(function (b) { out.push(b); });
        return;
      }

      if (closestOf(el, TABLE_WRAPPERS)) return;

      // Eigener Fettdruck-Block (Merksatz) — an seiner Stelle gesprochen.
      if (/^(STRONG|B)$/.test(tagOf(el))) {
        if (!isStandaloneEmphasis(el)) return;
        var emph = readableText(el);
        if (emph.length < 8) return;
        out.push({ el: el, lang: elLang, type: 'emphasis', text: emph.replace(/[\s?!.…]+$/, '') + '.' });
        return;
      }

      if (anyClass(el, BOX_CLASSES)) {
        var boxText = readableText(el);
        if (boxText.length <= 5) return;
        var isWarn = /\b(achtung|warnung|vorsicht|wichtig|caution|warning)\b/i.test(boxText.slice(0, 60))
          || hasClass(el, 'ff-korrektur');
        var cue = hasClass(el, 'ff-kurzantwort') ? T.cueShortAnswer
          : hasClass(el, 'ff-einspar-box') ? T.cueSaving
            : hasClass(el, 'ff-tarif-card') ? T.cueTariff
              : isWarn ? T.cueWarning : T.cueNote;
        out.push({
          el: el,
          lang: elLang,
          type: isWarn ? 'warning' : (hasClass(el, 'ff-tarif-card') || hasClass(el, 'ff-einspar-box') ? 'overview-card' : 'callout'),
          text: cue + ' ' + boxText
        });
        return;
      }

      /* Nur echte Vorfahren zählen: Ein <blockquote> selbst soll gelesen
         werden, sein Inhalt nicht zusätzlich ein zweites Mal. */
      var boxAncestor = el.parentElement
        ? closestOf(el.parentElement, '.ff-kurzantwort, .ff-korrektur, .callout, .ff-tarif-card, .ff-einspar-box, blockquote')
        : null;
      if (boxAncestor) return;

      /* Besteht der Block nur aus einem eigenen Fettdruck-Merksatz, spricht
         ihn der Fettdruck-Zweig – sonst stünde derselbe Satz zweimal. */
      var ownText = readableText(el);
      if (ownText) {
        var hasOwnEmphasis = qsa('strong, b', el).some(function (k) {
          return isStandaloneEmphasis(k) && readableText(k) === ownText;
        });
        if (hasOwnEmphasis) return;
      }

      var text = ownText;
      if (text.length < 2) return;
      if (/^(quelle|source|stand|foto|bild|anzeige|werbung|affiliate)\b/i.test(text) && text.length < 140) return;

      var t = tagOf(el).toLowerCase();
      var type = t;
      if (hasClass(el, 'ff-lead')) type = 'lead';
      if (anyClass(el, ['ff-tv-title', 'ff-es-title'])) type = 'overview-title';
      else if (anyClass(el, ['ff-tv-sub', 'ff-es-sub', 'ff-tv-footnote', 'ff-es-footnote'])) type = 'overview-note';

      var speakText = text;

      // Gezählte Listenpunkte
      if (t === 'li') {
        var parentList = el.parentElement;
        if (parentList && tagOf(parentList) === 'OL') {
          var idx = Array.prototype.indexOf.call(parentList.children, el) + 1;
          speakText = T.listItemNum.replace('{n}', idx) + ' ' + text;
        }
      }

      /* Überschriften stehen im Satzbaum meist ohne Punkt. Gesprochen
         brauchen sie einen — außer bei Fragen: Aus „Kann mir das Gas
         abgestellt werden?“ darf keine Feststellung werden. */
      if (/^H[23456]$/.test(tagOf(el))) {
        var heading = text.replace(/[\s?!.…]+$/, '');
        speakText = heading + (/\?\s*$/.test(text) ? '?' : '.');
      }

      out.push({ el: el, lang: elLang, type: type, text: speakText });
    });

    // (4) Abmoderation
    out.push({ el: bar, lang: lang, type: 'outro', text: T.outroLine });

    return out.filter(function (b) { return b && b.text && b.text.length > 1; });
  }

  /** Sprach-Routing je Block: Attribut lang hat Vorrang, dann Inhalt. */
  function sniffLangOf(el, fallback) {
    if (el && el.getAttribute) {
      var attr = String(el.getAttribute('lang') || '').toLowerCase();
      if (attr.indexOf('en') === 0) return 'en';
      if (attr.indexOf('de') === 0) return 'de';
    }
    var sample = readableText(el).slice(0, 400);
    if (sample.length >= 40) return sniffSentenceLang(sample, fallback);
    return fallback;
  }

  /* ============================================================
     7 · STUDIO-REGIE — Tempo, Tonlage, Lautstärke, Pausen
     ------------------------------------------------------------
     Keine Regler, keine Stimmenwahl. Die Regie folgt drei
     Eingangsgrößen:
       · ROLLE       — Überschrift, Fließtext, Tabellenzeile,
                       Warnhinweis … bekommen je ein Grundprofil.
       · DICHTE      — Zahlen, lange Komposita, Schachtelsätze
                       werden automatisch ruhiger gelesen.
       · MELDODIE    — Fragen steigen, Ausrufe betonen, der letzte
                       Satz eines Blocks klingt aus (Final-Längung).
     Dieselben Profile fahren Tonspur (Serverseite) und
     Browserstimme — die Parität wird geprüft.
     ============================================================ */

  var PROSODY = {
    intro:          { rate: 0.99, pitch: 1.00, volume: 1.00, before: 0,   after: 520 },
    outro:          { rate: 0.94, pitch: 0.97, volume: 0.96, before: 420, after: 0 },
    h2:             { rate: 0.90, pitch: 0.96, volume: 1.00, before: 620, after: 420 },
    h3:             { rate: 0.92, pitch: 0.97, volume: 1.00, before: 520, after: 340 },
    h4:             { rate: 0.94, pitch: 0.98, volume: 1.00, before: 440, after: 280 },
    h5:             { rate: 0.96, pitch: 0.99, volume: 1.00, before: 380, after: 240 },
    h6:             { rate: 0.97, pitch: 0.99, volume: 1.00, before: 340, after: 220 },
    lead:           { rate: 0.96, pitch: 1.00, volume: 1.00, before: 420, after: 460 },
    p:              { rate: 1.00, pitch: 1.00, volume: 1.00, before: 180, after: 420 },
    li:             { rate: 1.01, pitch: 1.00, volume: 1.00, before: 120, after: 320 },
    blockquote:     { rate: 0.95, pitch: 0.98, volume: 0.98, before: 380, after: 460 },
    callout:        { rate: 0.97, pitch: 1.00, volume: 1.00, before: 380, after: 460 },
    warning:        { rate: 0.93, pitch: 0.97, volume: 1.02, before: 460, after: 520 },
    emphasis:       { rate: 0.96, pitch: 1.01, volume: 1.02, before: 320, after: 420 },
    'overview-title': { rate: 0.90, pitch: 0.96, volume: 1.00, before: 560, after: 320 },
    'overview-note':  { rate: 0.98, pitch: 0.99, volume: 0.96, before: 220, after: 380 },
    'overview-card':  { rate: 0.97, pitch: 1.00, volume: 1.00, before: 320, after: 420 },
    'table-intro':  { rate: 0.92, pitch: 0.97, volume: 1.00, before: 520, after: 320 },
    'table-header': { rate: 0.95, pitch: 0.98, volume: 1.00, before: 160, after: 300 },
    'table-row':    { rate: 0.93, pitch: 0.98, volume: 0.99, before: 120, after: 340 },
    'table-sum':    { rate: 0.92, pitch: 0.98, volume: 1.01, before: 260, after: 400 },
    'table-outro':  { rate: 0.96, pitch: 0.99, volume: 0.98, before: 300, after: 520 }
  };

  var HARD_CHUNK = 220;   // Chrome bricht Äußerungen > ~15 s ab; 220 Zeichen bleiben sicher darunter.
  var SOFT_CHUNK = 180;   // Atemgruppen-Ziel bei guter Stimme.

  function prosodyFor(type) { return PROSODY[type] || PROSODY.p; }

  /* ---------- Satzzerlegung --------------------------------- */

  // Punkte in Zahlen, Abkürzungen und Auslassungen dürfen KEIN
  // Satzende bedeuten: 1.234,56 · z. B. · Nr. 3 · … · 20.000 kWh
  function maskSentenceDots(text) {
    return String(text)
      .replace(/(\d)\.(\d)/g, '$1\u0002$2')
      .replace(/\b(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})\b/g, function (m) { return m.replace(/\./g, '\u0002'); })
      .replace(/\b(Abs|Art|Nr|S|Abb|Tab|Mio|Mrd|Tsd|bzw|ca|vgl|usw|usf|zzgl|inkl|exkl|sog|geb|MwSt|z\s?B|u\s?a|d\s?h|i\s?d\s?R|o\s?g)\./g,
        function (m) { return m.replace(/\./g, '\u0002'); })
      .replace(/\b(\w)\.(?=\w{2,}\.)/g, '$1\u0002')
      // Getrennt geschriebene Abkürzungen: „z. B.“, „u. a.“, „d. h.“, „e. g.“
      .replace(/\b([a-z])\.\s+([a-zA-Z])\./g, function (m, a, b) { return a + '\u0002 ' + b + '\u0002'; });
  }
  function unmaskDots(text) { return String(text).replace(/\u0002/g, '.'); }

  function sentences(text) {
    var masked = maskSentenceDots(text);
    var parts = masked.split(/(?<=[.!?…])\s+(?=["'“„]?[A-ZÄÖÜ0-9(])/);
    if (parts.length <= 1) parts = masked.split(/(?<=[.!?…])\s+/);
    return parts.map(unmaskDots).map(function (s) { return s.trim(); })
      .filter(function (s) { return s.length > 0; });
  }

  /* ---------- Atemgruppen ----------------------------------- */

  var CONNECTIVES = /\b(und|oder|aber|denn|weil|da|wenn|falls|obwohl|während|damit|sodass|als|wie|nachdem|bevor|seit|sowie|jedoch|allerdings|dennoch|trotzdem|deshalb|daher|darüber hinaus|außerdem|zudem|and|or|but|because|although|however|while|whereas|since|if|unless|therefore|moreover|furthermore|nevertheless|so that|as well as)\b/i;

  function cutAtConnectives(text) {
    var out = [];
    var rest = String(text);
    var guard = 0;
    while (rest.length > HARD_CHUNK && guard++ < 12) {
      var cut = -1;
      var re = new RegExp(CONNECTIVES.source, 'gi');
      var m;
      while ((m = re.exec(rest)) !== null) {
        var at = m.index;
        if (at > HARD_CHUNK * 0.4 && at < rest.length - 40) { cut = at; }
        if (at > HARD_CHUNK) break;
      }
      if (cut < 0) {
        var slice = rest.slice(0, HARD_CHUNK);
        var lastStop = Math.max(slice.lastIndexOf(', '), slice.lastIndexOf('; '), slice.lastIndexOf(': '), slice.lastIndexOf(' – '));
        cut = lastStop > HARD_CHUNK * 0.35 ? lastStop + 1 : HARD_CHUNK;
      }
      out.push(rest.slice(0, cut).trim());
      rest = rest.slice(cut).trim();
    }
    if (rest) out.push(rest);
    return out;
  }

  function commaPieces(text) {
    // Komma-Teile zu natürlichen Atemgruppen bündeln
    var pieces = String(text).split(/(?<=[,;:])\s+/);
    var out = [];
    var buf = '';
    pieces.forEach(function (piece) {
      var candidate = buf ? buf + ' ' + piece : piece;
      if (candidate.length > SOFT_CHUNK && buf) {
        out.push(buf.trim());
        buf = piece;
      } else {
        buf = candidate;
      }
    });
    if (buf.trim()) out.push(buf.trim());
    return out;
  }

  /** Zerlegt einen Block in Sprecheinheiten (Atemgruppen). */
  function splitForSpeech(text, blockLang) {
    var L = blockLang || lang;
    var out = [];
    sentences(text).forEach(function (sentence) {
      if (!sentence) return;
      // Satzweises Sprach-Routing VOR der Aussprache-Normalisierung:
      // Sonst erbt ein englischer Satz im deutschen Artikel die
      // falschen Zahlen- und Datumsregeln.
      var sLang = sniffSentenceLang(sentence, L);
      if (sentence.length <= HARD_CHUNK) {
        out.push({ text: sentence, lang: sLang });
        return;
      }
      cutAtConnectives(sentence).forEach(function (piece) {
        if (piece.length <= HARD_CHUNK) { out.push({ text: piece, lang: sniffSentenceLang(piece, sLang) }); return; }
        commaPieces(piece).forEach(function (sub) {
          if (sub.length <= HARD_CHUNK) { out.push({ text: sub, lang: sniffSentenceLang(sub, sLang) }); return; }
          var words = sub.split(/\s+/);
          var buf = '';
          words.forEach(function (w) {
            var cand = buf ? buf + ' ' + w : w;
            if (buf && cand.length > HARD_CHUNK - 12) { out.push({ text: buf.trim(), lang: sLang }); buf = w; }
            else buf = cand;
          });
          if (buf.trim()) out.push({ text: buf.trim(), lang: sLang });
        });
      });
    });
    return out;
  }

  /* ---------- Dichte & Melodie ------------------------------ */

  function densityFactor(text) {
    var t = String(text || '');
    var words = Math.max(1, (t.match(/\S+/g) || []).length);
    var numbers = (t.match(/\d/g) || []).length;
    var longWords = (t.match(/\b\w{14,}\b/g) || []).length;
    var clauses = (t.match(/[,;:]/g) || []).length;
    var score = (numbers / words) * 2.2 + (longWords / words) * 2.4 + (clauses / words) * 0.9;
    // 1.0 = neutral; dichtere Sätze werden ruhiger (bis 0.90)
    return Math.max(0.90, Math.min(1.06, 1.02 - score));
  }

  function melodyOf(text) {
    if (/\?\s*$/.test(text)) return 'question';
    if (/!\s*$/.test(text)) return 'exclaim';
    if (/…\s*$/.test(text)) return 'trailing';
    if (/[:,;]\s*$/.test(text)) return 'open';
    return 'statement';
  }

  var MELODY_PITCH = { question: 0.06, exclaim: 0.02, trailing: -0.02, open: -0.01, statement: 0 };
  var MELODY_RATE = { question: 0.98, exclaim: 1.02, trailing: 0.94, open: 0.99, statement: 1 };
  var MELODY_AFTER = { question: 240, exclaim: 200, trailing: 380, open: 60, statement: 0 };

  /* ---------- Zeitachse ------------------------------------- */

  var BASE_CPS = 15.2;   // Zeichen pro Sekunde bei rate 1.0 (Klang-Referenz: ruhige Sprechstimme)

  function effectiveRate(unit) {
    var p = unit.profile;
    var density = unit.density;
    var melody = MELODY_RATE[unit.melody] || 1;
    var quality = unit.qualityRate || 1;
    var isLast = unit.finalChunk ? 0.97 : 1;      // Final-Längung am Blockende
    return Math.max(0.75, Math.min(1.22, p.rate * density * melody * quality * isLast));
  }

  function effectivePitch(unit) {
    var p = unit.profile;
    var melody = MELODY_PITCH[unit.melody] || 0;
    var micro = (unit.index % 2 === 0 ? 0.012 : -0.012);   // Mikro-Modulation gegen Monotonie
    var zone = unit.pitchZone || 0;
    return Math.max(0.6, Math.min(1.4, p.pitch + melody + micro + zone));
  }

  function effectiveVolume(unit) {
    var p = unit.profile;
    var melody = unit.melody === 'exclaim' ? 0.04 : 0;
    return Math.max(0.55, Math.min(1, p.volume + melody));
  }

  function pauseAfter(unit) {
    var p = unit.profile;
    var base = p.after || 0;
    var melody = MELODY_AFTER[unit.melody] || 0;
    var byLength = unit.words > 28 ? 120 : (unit.words > 16 ? 60 : 0);
    var rateComp = 1 / Math.max(0.8, unit.effRate);
    return Math.round((base + melody + byLength) * rateComp);
  }

  function buildTimeline(blocks, qualityRate) {
    var units = [];
    var totalChars = 0;
    var index = 0;
    blocks.forEach(function (b, bi) {
      var profile = prosodyFor(b.type);
      var raw = splitForSpeech(speechNormalize(b.text, b.lang), b.lang);
      raw.forEach(function (c, ci) {
        if (!c.text) return;
        var density = densityFactor(c.text);
        var unit = {
          block: b,
          blockIndex: bi,
          index: index++,
          text: c.text,
          lang: c.lang || b.lang,
          type: b.type,
          profile: profile,
          melody: melodyOf(c.text),
          density: density,
          words: (c.text.match(/\S+/g) || []).length,
          qualityRate: qualityRate || 1,
          firstChunk: ci === 0,
          finalChunk: ci === raw.length - 1,
          startChars: totalChars,
          endChars: totalChars + c.text.length
        };
        unit.effRate = effectiveRate(unit);
        unit.effPitch = effectivePitch(unit);
        unit.effVolume = effectiveVolume(unit);
        unit.before = ci === 0 ? profile.before : 0;
        unit.after = pauseAfter(unit);
        totalChars += c.text.length;
        units.push(unit);
      });
    });
    return { units: units, totalChars: totalChars };
  }

  function estimatedMs(unit) {
    var ms = (unit.text.length / (BASE_CPS * Math.max(0.5, unit.effRate))) * 1000;
    return ms + (unit.before || 0) + (unit.after || 0);
  }

  /* ============================================================
     8 · STIMMEN-REGIE — männlich, DE & EN, ohne Umschalter
     ------------------------------------------------------------
     Es gibt kein Menü und keinen Umschalter. Die Regie trifft eine
     deterministische Entscheidung:

       1. Sprache        — je Sprecheinheit 'de' oder 'en'
       2. Geschlecht     — männlich, mit Veto gegen weibliche Stimmen
       3. Güte           — Studio/Neural vor Standard vor Roboter
       4. Nachbarschaft  — de-DE → de-AT → de-CH → de
                           en-US → en-GB → en-AU → en-IE → en-IN → en

     Nie stumm: Ist der Stimmen-Katalog beim Klick noch leer
     (Chromium, Safari und Android füllen ihn LAZY), wird SOFORT mit
     der angeforderten Sprache gesprochen und beim Eintreffen des
     Katalogs auf die echte männliche Stimme angehoben. Ein Warten
     auf Stimmen würde das User-Activation-Token verbrennen und
     genau die Stummheit erzeugen, die dieses Modell ausschließt.
     ============================================================ */

  var synth = (win.speechSynthesis || null);
  var speechSupported = !!(synth && win.SpeechSynthesisUtterance);

  var MALE_NAMES = ('conrad florian klaus stefan yannick bernd christoph benjamin jonas ralf kasper jeppe thomas daniel ' +
    'andrew ryan brian christopher eric guy jacob liam oliver alex fred sam michael george arthur james william henry ' +
    'nathan adam rishi arjun prabhat aarav rehan thorsten karlsson gereon jan lukas niklas sebastian david elias finn ' +
    'noah ben jannik markus martin tobias felix paul leon tim mattis oskar anton milan emil josef gregor alfred kurt ' +
    'werner rudolph owen jack charlie henry leo max hugo antonio diego javier carlos miguel pedro raj sanjay').split(' ');
  var FEMALE_NAMES = ('anna katja hedda marlene vicki elke amala clara julia lena laura sophie sofia zoe emma mia hannah ' +
    'sarah emily ashley samantha karen moira tessa fiona serena allison ava susan joan linda nancy nina victoria ' +
    'katherine katie eva marie luise lea nele maila sarah elena nora frieda ida alma mathilde johanna charlotte').split(' ');
  var ROBOTIC = ['espeak', 'pico', 'festival', 'flite', 'robotic'];
  var QUALITY_TOKENS = ['neural', 'neural2', 'wavenet', 'studio', 'premium', 'enhanced', 'natural', 'siri', 'online', 'high'];

  var voiceCache = [];
  var voiceResolved = { de: null, en: null };
  var maleVoiceFound = { de: false, en: false };

  function refreshVoices() {
    var list = [];
    try { if (synth && synth.getVoices) list = synth.getVoices() || []; } catch (e) { list = []; }
    voiceCache = list.slice();
    return voiceCache;
  }
  refreshVoices();
  if (synth && typeof win.addEventListener === 'function') {
    try { synth.addEventListener('voiceschanged', refreshVoices); } catch (e) {}
  }

  function voiceHay(v) {
    return (String((v && v.name) || '') + ' ' + String((v && v.voiceURI) || '') + ' ' + String((v && v.lang) || '')).toLowerCase();
  }
  function voiceLang(v) { return String((v && v.lang) || '').toLowerCase().replace('_', '-'); }
  function langPrefix(l) {
    var s = String(l || '').toLowerCase().replace('_', '-');
    var i = s.indexOf('-');
    return i > 0 ? s.slice(0, i) : s;
  }

  var LOCALE_CHAIN = {
    de: ['de-de', 'de-at', 'de-ch', 'de-li', 'de-lu', 'de-be', 'de'],
    en: ['en-us', 'en-gb', 'en-au', 'en-ie', 'en-ca', 'en-nz', 'en-in', 'en-za', 'en-ng', 'en']
  };

  function localeScore(v, target) {
    var l = voiceLang(v);
    var chain = LOCALE_CHAIN[target] || [target];
    var idx = chain.indexOf(l);
    if (idx === 0) return 70;
    if (idx > 0) return 60 - idx * 6;
    if (langPrefix(l) === target) return 34;
    if (l === target) return 40;
    // Nachbarsprache (z. B. nl für de) ist ein Notnagel, kein Ziel
    if (target === 'de' && (l.indexOf('nl') === 0 || l.indexOf('da') === 0)) return 6;
    return -100;
  }

  /** Namen in Wort-Tokens zerlegen („Samantha“ darf nicht als „Sam“ zählen). */
  function nameTokens(v) {
    return String((v && v.name) || '').toLowerCase().split(/[\s\-_()\[\],.]+/)
      .filter(function (t) { return t.length > 0; });
  }

  function genderScore(v) {
    var hay = voiceHay(v);
    var name = String((v && v.name) || '').toLowerCase();
    var tokens = nameTokens(v);

    // Weibliche Namen ZUERST prüfen: Ein Teilstring-Treffer („Sam“ in
    // „Samantha“) darf niemals eine Frauenstimme als männlich durchwinken.
    for (var f = 0; f < FEMALE_NAMES.length; f++) {
      if (tokens.indexOf(FEMALE_NAMES[f]) !== -1) return -600;
    }
    if (/\bfemale\b|\bweiblich\b|\bfrau\b|\bwoman\b/.test(hay)) return -600;

    for (var i = 0; i < MALE_NAMES.length; i++) {
      if (tokens.indexOf(MALE_NAMES[i]) !== -1) return 140;
    }
    if (/\bmale\b|\bmännlich\b/.test(hay)) return 100;

    // Buchstaben-Codes: Google A/C/E = weiblich, B/D/F = männlich
    var m = name.match(/[a-z]{2}-[a-z]{2}-(?:standard|wavenet|neural2|studio)-([a-f])$/i);
    if (m) return ('bdf'.indexOf(m[1].toLowerCase()) !== -1) ? 110 : -600;
    return 0;   // neutral/unbenannt
  }

  function qualityScore(v) {
    var hay = voiceHay(v);
    var score = 0;
    for (var i = 0; i < QUALITY_TOKENS.length; i++) {
      if (hay.indexOf(QUALITY_TOKENS[i]) !== -1) score += 22;
    }
    for (var r = 0; r < ROBOTIC.length; r++) {
      if (hay.indexOf(ROBOTIC[r]) !== -1) score -= 90;
    }
    try { if (v && v.localService) score += 8; } catch (e) {}
    if (hay.indexOf('compact') !== -1) score -= 26;
    return score;
  }

  function scoreVoice(v, target) {
    var locale = localeScore(v, target);
    if (locale < -50) return -9999;
    return locale + genderScore(v) + qualityScore(v);
  }

  function rankVoices(target) {
    var list = voiceCache.length ? voiceCache : refreshVoices();
    var scored = [];
    list.forEach(function (v, i) {
      var s = scoreVoice(v, target);
      if (s > -9000) scored.push({ voice: v, score: s, order: i });
    });
    scored.sort(function (a, b) {
      if (b.score !== a.score) return b.score - a.score;
      return a.order - b.order;
    });
    return scored;
  }

  var TIERS = {
    studio:   { rate: 1.00, pitchZone: 0.00, label: 'studio' },
    neural:   { rate: 0.99, pitchZone: 0.00, label: 'neural' },
    standard: { rate: 0.97, pitchZone: -0.02, label: 'standard' },
    robotic:  { rate: 0.94, pitchZone: -0.05, label: 'robotic' }
  };

  function tierFor(v) {
    var hay = voiceHay(v);
    var isRobotic = ROBOTIC.some(function (r) { return hay.indexOf(r) !== -1; });
    if (isRobotic) return TIERS.robotic;
    var hits = QUALITY_TOKENS.filter(function (q) { return hay.indexOf(q) !== -1; }).length;
    if (hits >= 2) return TIERS.studio;
    if (hits === 1) return TIERS.neural;
    return TIERS.standard;
  }

  /**
   * Ermittelt die beste männliche Stimme für eine Sprache.
   * Gibt immer ein Objekt zurück — nie null (außer bei leerem Katalog).
   */
  function resolveMaleVoice(target) {
    if (voiceResolved[target]) return voiceResolved[target];
    var ranked = rankVoices(target);
    if (!ranked.length) return { voice: null, tier: TIERS.standard, male: false, score: -1 };

    var male = null;
    for (var i = 0; i < ranked.length; i++) {
      if (genderScore(ranked[i].voice) > 0) { male = ranked[i]; break; }
    }

    var chosen = male || ranked[0];
    var tier = tierFor(chosen.voice);
    var isMale = !!male;

    /* Letzter Notnagel: keine männliche Stimme vorhanden. Dann wird die
       Stimme in die männliche Klangzone abgesenkt (nicht stumm bleiben,
       nicht mit einer hellen Stimme überraschen). */
    var zone = isMale ? 0 : -0.14;
    var result = {
      voice: chosen.voice,
      tier: { rate: tier.rate, pitchZone: tier.pitchZone + zone, label: tier.label },
      male: isMale,
      score: chosen.score
    };
    voiceResolved[target] = result;
    maleVoiceFound[target] = isMale;
    return result;
  }

  function hasExplicitMaleVoice() { return maleVoiceFound.de || maleVoiceFound.en; }

  function calibrateQuality() {
    var de = resolveMaleVoice('de');
    var en = resolveMaleVoice('en');
    // Die Regie folgt der schwächeren der beiden Stimmen: Ein
    // Sprachwechsel darf nicht plötzlich schneller klingen.
    var rate = Math.min(de.tier ? de.tier.rate : 1, en.tier ? en.tier.rate : 1);
    return { rate: rate, de: de, en: en };
  }

  var quality = { rate: 1, de: null, en: null };

  /* ============================================================
     9 · LAUFZEIT-STATUS
     ============================================================ */

  var blocks = [];
  var units = [];
  var totalChars = 0;
  var cursor = 0;
  var nextIndex = 0;
  var reading = false;
  var playing = false;
  var mode = 'speech';        // 'track' (Studio-Tonspur) | 'speech' (Browser-Engine)
  var runId = 0;              // macht Rückrufe abgebrochener Läufe ungültig

  /* ---------- Fortschritt: ein Rechenweg für alles ------------- */
  var spokenChars = 0;       // gesprochene Zeichen (Browser-Modus)
  var displayedChars = 0;    // angezeigte Zeichen (monoton steigend)
  var progressRatio = 0;
  var progressTimer = null;

  function paintProgress(ratio) {
    var r = Math.max(0, Math.min(1, ratio || 0));
    if (r < progressRatio && r < 0.999) r = progressRatio;      // monoton – nie zurück
    progressRatio = r;
    if (progressEl) progressEl.style.width = (r * 100).toFixed(2) + '%';
    if (bar) {
      bar.setAttribute('aria-valuenow', String(Math.round(r * 100)));
      bar.setAttribute('aria-valuemin', '0');
      bar.setAttribute('aria-valuemax', '100');
    }
  }

  function setProgressChars(chars, allowBackward) {
    if (!totalChars) return;
    var next = Math.max(0, Math.min(totalChars, chars));
    if (!allowBackward && next < displayedChars) next = displayedChars;
    displayedChars = next;
    paintProgress(totalChars ? next / totalChars : 0);
  }

  function resetProgress(chars) {
    progressRatio = 0;
    displayedChars = Math.max(0, chars || 0);
    if (progressEl) progressEl.style.width = '0%';
    if (totalChars && displayedChars) paintProgress(displayedChars / totalChars);
  }

  function completeProgress() { paintProgress(1); displayedChars = totalChars; }

  /* ---------- Restzeit aus demselben Modell -------------------- */
  function updateRemainingFromChars() {
    if (!remainEl) return;
    if (!units.length) { remainEl.textContent = ''; return; }
    var restChars = Math.max(0, totalChars - displayedChars);
    var cps = BASE_CPS * (quality.rate || 1);
    var minutes = restChars / cps / 60;
    remainEl.textContent = minutes >= 0.1 ? T.remaining.replace('{min}', Math.max(1, Math.round(minutes))) : '';
  }

  function updateRemainingFromTime(msLeft) {
    if (!remainEl) return;
    var minutes = Math.max(0, msLeft) / 60000;
    remainEl.textContent = minutes >= 0.1 ? T.remaining.replace('{min}', Math.max(1, Math.round(minutes))) : '';
  }

  function startProgressTicker() {
    stopProgressTicker();
    var tick = function () {
      if (!reading || !playing) { progressTimer = null; return; }
      if (mode === 'speech') {
        // Sanftes Nachführen zwischen den Wortgrenzen-Ereignissen
        setProgressChars(spokenChars, false);
        updateRemainingFromChars();
      }
      if (win.requestAnimationFrame && !reducedMotion) {
        progressTimer = win.requestAnimationFrame(tick);
      } else {
        progressTimer = setTimeout(tick, 120);
      }
    };
    if (win.requestAnimationFrame && !reducedMotion) progressTimer = win.requestAnimationFrame(tick);
    else progressTimer = setTimeout(tick, 120);
  }

  function stopProgressTicker() {
    if (progressTimer) {
      if (win.cancelAnimationFrame && !reducedMotion) win.cancelAnimationFrame(progressTimer);
      else clearTimeout(progressTimer);
      progressTimer = null;
    }
  }

  /* ---------- Live-Markierung --------------------------------- */
  function highlightBlock(block) {
    var el = block && block.el ? block.el : null;
    blocks.forEach(function (b) { if (b.el && b.el !== el) b.el.classList.remove('ff-voice-active'); });
    if (!el || el === bar) return;
    el.classList.add('ff-voice-active');
    if (!reducedMotion && el.scrollIntoView) {
      try { el.scrollIntoView({ block: 'center', behavior: 'smooth' }); } catch (e) { el.scrollIntoView(); }
    } else if (el.scrollIntoView) {
      try { el.scrollIntoView({ block: 'center' }); } catch (e) {}
    }
  }

  function clearHighlight() {
    blocks.forEach(function (b) { if (b.el) b.el.classList.remove('ff-voice-active'); });
  }

  /* ---------- Positionsgedächtnis ----------------------------- */
  function rememberBlock(bi) {
    if (cfg.slug || cfg.permalink) storeSet(STORE_POS, String(bi));
  }
  function rememberedBlock() {
    var v = parseInt(storeGet(STORE_POS) || '0', 10);
    if (!isFinite(v) || v <= 0) return 0;
    return Math.min(Math.max(0, v), Math.max(0, blocks.length - 1));
  }

  /* ============================================================
     10 · TONPFAD A — STUDIO-TONSPUR (HTML5-<audio>)
     ------------------------------------------------------------
     Verlagsstandard: vorab vertonte MP3 im nativen Player. Sie
     klingt auf jedem Gerät identisch und ist unabhängig von den
     Stimmen des Betriebssystems. Fällt sie aus (noch nicht
     generiert, Netz, Codec), wechselt der Reader nahtlos auf die
     Browser-Engine — niemals stumm.
     ============================================================ */

  var track = null;
  var trackChunks = [];
  var trackCur = -1;
  var trackBlock = 0;

  function initTrack() {
    var a = cfg.audio;
    if (!a) return false;
    var url = String(typeof a === 'string' ? a : (a.src || ''));
    if (!url) return false;
    var elt = null;
    try { elt = doc.createElement('audio'); } catch (e) { return false; }
    if (!elt || typeof elt.addEventListener !== 'function') return false;
    elt.setAttribute('preload', 'metadata');
    elt.setAttribute('playsinline', '');
    elt.setAttribute('aria-hidden', 'true');
    elt.style.display = 'none';
    try { elt.src = url; } catch (e) { return false; }
    track = elt;
    trackChunks = (a && a.chunks && a.chunks.length) ? a.chunks : [];
    try { doc.body.appendChild(elt); } catch (e) {}

    elt.addEventListener('timeupdate', trackOnTime);
    elt.addEventListener('play', function () { if (reading) startProgressTicker(); });
    elt.addEventListener('pause', stopProgressTicker);
    elt.addEventListener('ended', function () { stopProgressTicker(); endReading(true, true); });
    elt.addEventListener('error', function () { if (reading) fallbackToSpeech(); });
    return true;
  }

  function trackTotalMs() {
    if (!track) return 0;
    var d = track.duration;
    if (d && isFinite(d) && d > 0) return d * 1000;
    if (trackChunks.length) return trackChunks[trackChunks.length - 1].t1 || 0;
    return 0;
  }

  function trackOnTime() {
    if (!track || !reading) return;
    var t = (track.currentTime || 0) * 1000;
    var total = trackTotalMs();
    if (trackChunks.length) {
      var idx = -1;
      for (var i = 0; i < trackChunks.length; i++) {
        if (t >= trackChunks[i].t0 && t < trackChunks[i].t1) { idx = i; break; }
        if (t >= trackChunks[i].t0) idx = i;
      }
      if (idx >= 0 && idx !== trackCur) {
        trackCur = idx;
        var bi = trackChunks[idx] ? trackChunks[idx].b : 0;
        if (blocks[bi]) { trackBlock = bi; highlightBlock(blocks[bi]); rememberBlock(bi); }
      }
    }
    if (total > 0) {
      paintProgress(t / total);
      updateRemainingFromTime(total - t);
    }
  }

  function trackSeek(bi) {
    if (!track) return;
    var target = Math.max(0, Math.min(blocks.length - 1, bi));
    var t = 0;
    for (var i = 0; i < trackChunks.length; i++) {
      if (trackChunks[i].b === target) { t = trackChunks[i].t0 || 0; break; }
      if (trackChunks[i].b < target) t = trackChunks[i].t1 || t;
    }
    try { track.currentTime = t / 1000; } catch (e) {}
  }

  function trackStart(fromBlock) {
    if (!track) return;
    trackBlock = typeof fromBlock === 'number' && fromBlock > 0 ? Math.min(fromBlock, blocks.length - 1) : 0;
    trackCur = -1;
    if (track.error) { fallbackToSpeech(); return; }
    trackSeek(trackBlock);
    var total = trackTotalMs();
    if (total > 0 && trackChunks.length) {
      var t = 0;
      for (var i = 0; i < trackChunks.length; i++) {
        if (trackChunks[i].b === trackBlock) { t = trackChunks[i].t0 || 0; break; }
      }
      paintProgress(t / total);
    }
    playElement(track);
  }

  function playElement(elt) {
    if (!elt) return;
    var p = null;
    try { p = elt.play(); } catch (e) { p = null; }
    if (p && p.then) {
      p.catch(function () {
        // Autoplay-Verweigerung: im Klickkontext selten, einmalig erneut.
        try { var q = elt.play(); if (q && q.catch) q.catch(function () {}); } catch (e) {}
      });
    }
  }

  function trackPause() { if (track) { try { track.pause(); } catch (e) {} } }
  function trackResume() { playElement(track); }
  function trackStop() {
    if (!track) return;
    try { track.pause(); } catch (e) {}
    try { track.currentTime = 0; } catch (e) {}
  }

  function trackJump(delta) {
    var target = (blocks[trackBlock] ? trackBlock : 0) + delta;
    if (target < 0) target = 0;
    if (target >= blocks.length) { endReading(true, true); return; }
    trackBlock = target;
    trackCur = -1;
    trackSeek(target);
    if (track && track.paused) playElement(track);
    highlightBlock(blocks[target]);
    rememberBlock(target);
  }

  /** Tonspur nicht abspielbar → nahtlos auf die Browser-Engine. */
  function fallbackToSpeech() {
    if (!track) { setStatus(T.unsupported); return; }
    var resumeAt = blocks[trackBlock] ? trackBlock : 0;
    try { track.pause(); } catch (e) {}
    mode = 'speech';
    if (!speechSupported) { endReading(false, false); setStatus(T.unsupported); return; }
    startReading(resumeAt, true);
  }

  /* ============================================================
     11 · TONPFAD B — BROWSER-ENGINE (Web Speech API)
     ------------------------------------------------------------
     Härtung gegen die vier bekannten Abbruch-Ursachen:
       · Chrome beendet sehr lange Äußerungen → harte Chunk-Grenze
       · Chrome friert nach ~15 s Stille ein  → Keep-Alive-Wache
       · Safari „resumed“ ohne hörbaren Ton  → Pause = Abbruch +
                                                Neu-Sprechen derselben
                                                Einheit (plattformgleich)
       · Android bricht die Queue ab         → Anti-Stall-Watchdog mit
                                                kontrolliertem Neustart
     ============================================================ */

  var liveUtterance = null;
  var utteranceRefs = [];
  var unitInFlight = false;
  var startWatchdog = null;
  var keepAliveTimer = null;
  var pauseTimer = null;
  var errorStreak = 0;
  var retryCounts = {};

  function clearStartWatchdog() {
    if (startWatchdog) { clearTimeout(startWatchdog); startWatchdog = null; }
  }
  function clearPauseTimer() {
    if (pauseTimer) { clearTimeout(pauseTimer); pauseTimer = null; }
  }
  function stopKeepAlive() {
    if (keepAliveTimer) { clearInterval(keepAliveTimer); keepAliveTimer = null; }
  }
  function startKeepAlive() {
    stopKeepAlive();
    // Chrome friert die Queue bei längeren Pausen ein; ein sanfter
    // resume()-Impuls hält die Engine wach, ohne hörbar zu sein.
    keepAliveTimer = setInterval(function () {
      if (!reading || !playing || !synth) { stopKeepAlive(); return; }
      try { if (synth.paused && !unitInFlight) synth.resume(); } catch (e) {}
    }, 9000);
  }

  function unlockEngine() {
    if (!synth) return;
    try {
      if (synth.paused) synth.resume();
      synth.cancel();
      synth.resume();
    } catch (e) {}
  }

  function speakUnit(index, isInitial) {
    if (!reading || !playing) return;
    if (index >= units.length) { endReading(true, true); return; }

    var myRun = runId;
    var unit = units[index];
    cursor = index;
    nextIndex = index + 1;

    var res = resolveMaleVoice(unit.lang) || {};
    var voice = res.voice || null;

    var u = null;
    try { u = new win.SpeechSynthesisUtterance(unit.text); } catch (e) { u = null; }
    if (!u) { advance(index); return; }

    u.lang = (unit.lang === 'en') ? 'en-US' : 'de-DE';
    if (voice) { try { u.voice = voice; } catch (e) {} }
    u.rate = Math.max(0.6, Math.min(1.4, unit.effRate * (res.tier ? res.tier.rate : 1)));
    u.pitch = Math.max(0.5, Math.min(1.5, unit.effPitch + (res.tier && res.tier.pitchZone ? res.tier.pitchZone : 0)));
    u.volume = Math.max(0.4, Math.min(1, unit.effVolume));

    unitInFlight = true;
    liveUtterance = u;
    utteranceRefs.push(u);                       // GC-Schutz (Chrome-Abbrüche)
    if (utteranceRefs.length > 24) utteranceRefs.splice(0, utteranceRefs.length - 24);

    var started = false;

    u.onstart = function () {
      if (myRun !== runId) return;
      started = true;
      clearStartWatchdog();
      errorStreak = 0;
      highlightBlock(unit.block);
      rememberBlock(unit.blockIndex);
      setStatus(res.male ? T.voiceActive : (T.voiceFallback || T.started));
    };

    u.onboundary = function (ev) {
      if (myRun !== runId) return;
      if (ev && typeof ev.charIndex === 'number') {
        spokenChars = unit.startChars + ev.charIndex;
        setProgressChars(spokenChars, false);
        updateRemainingFromChars();
      }
    };

    u.onend = function () {
      if (myRun !== runId) return;
      clearStartWatchdog();
      unitInFlight = false;
      liveUtterance = null;
      spokenChars = unit.endChars;
      setProgressChars(spokenChars, false);
      advance(index);
    };

    u.onerror = function (ev) {
      if (myRun !== runId) return;
      clearStartWatchdog();
      unitInFlight = false;
      liveUtterance = null;
      var reason = ev && ev.error ? String(ev.error) : 'unknown';
      if (reason === 'interrupted' || reason === 'canceled') return;   // gewollter Abbruch
      errorStreak += 1;
      var tries = retryCounts[index] || 0;
      if (tries < 2 && errorStreak < 4) {
        retryCounts[index] = tries + 1;
        setStatus(T.sectionError);
        pauseTimer = setTimeout(function () {
          if (myRun !== runId) return;
          speakUnit(index, false);
        }, 320);
      } else {
        setStatus(T.sectionError);
        spokenChars = unit.endChars;
        setProgressChars(spokenChars, false);
        advance(index);
      }
    };

    // Anti-Stall-Wache: startet eine Äußerung nicht innerhalb von 4 s,
    // wird sie verworfen und die nächste gesprochen (nie Stille).
    clearStartWatchdog();
    startWatchdog = setTimeout(function () {
      if (myRun !== runId) return;
      if (started) return;
      try { synth.cancel(); } catch (e) {}
      unitInFlight = false;
      liveUtterance = null;
      var tries = retryCounts[index] || 0;
      if (tries < 2) {
        retryCounts[index] = tries + 1;
        speakUnit(index, false);
      } else {
        advance(index);
      }
    }, 4000);

    try { synth.speak(u); } catch (e) {
      clearStartWatchdog();
      unitInFlight = false;
      advance(index);
    }
  }

  /** Nächste Einheit — mit der rollengerechten Pause davor. */
  function advance(index) {
    if (!reading || !playing) return;
    var next = index + 1;
    if (next >= units.length) { endReading(true, true); return; }
    var wait = units[next].before || 0;
    clearPauseTimer();
    pauseTimer = setTimeout(function () { speakUnit(next, false); }, wait);
  }

  function startSpeech(fromIndex) {
    unlockEngine();
    errorStreak = 0;
    retryCounts = {};
    runId += 1;
    stopKeepAlive();

    quality = calibrateQuality();
    var plan = buildTimeline(blocks, quality.rate);
    units = plan.units;
    totalChars = plan.totalChars;

    if (!units.length) { setStatus(T.noText); return; }

    var startIdx = 0;
    if (typeof fromIndex === 'number' && fromIndex > 0 && fromIndex < blocks.length) {
      // Wiedereinstieg an einer gemerkten Blockgrenze
      for (var i = 0; i < units.length; i++) {
        if (units[i].blockIndex >= fromIndex) { startIdx = i; break; }
      }
    }
    spokenChars = units[startIdx] ? units[startIdx].startChars : 0;
    resetProgress(spokenChars);
    cursor = startIdx;
    nextIndex = startIdx;
    reading = true;
    playing = true;
    setBarState('playing');
    setStatus(startIdx > 0 ? T.resumedPos : T.started);
    setupMediaSession();
    startProgressTicker();
    startKeepAlive();
    speakUnit(startIdx, true);
  }

  function pauseSpeech() {
    playing = false;
    clearPauseTimer();
    clearStartWatchdog();
    stopProgressTicker();
    stopKeepAlive();
    runId += 1;                       // Rückrufe laufender Äußerungen entwerten
    unitInFlight = false;
    liveUtterance = null;
    if (synth) { try { synth.cancel(); } catch (e) {} }
    setBarState('paused');
    setStatus(T.paused);
  }

  function resumeSpeech() {
    if (!reading) return;
    playing = true;
    runId += 1;
    setBarState('playing');
    setStatus(T.resumed);
    startProgressTicker();
    startKeepAlive();
    if (!speechSupported) return;
    // Pause ist ein kontrollierter Abbruch. Fortgesetzt wird mit der
    // Einheit, die als NÄCHSTE dran ist — mitten im Satz ist das der
    // aktuelle, in der Atempause danach der folgende. Ein fertiger
    // Satz wird dadurch nie doppelt gesprochen.
    speakUnit(Math.min(nextIndex, Math.max(0, units.length - 1)), true);
  }

  /* ============================================================
     12 · REGIE — Start, Pause, Sprung, Ende
     ============================================================ */

  function setStatus(msg) {
    if (statusEl) statusEl.textContent = msg || '';
  }

  function setBarState(state) {
    if (!bar) return;
    bar.setAttribute('data-state', state);
    if (state === 'playing') {
      if (playLabel) playLabel.textContent = T.pause;
      playBtn.setAttribute('aria-label', T.pauseAria);
      playBtn.setAttribute('aria-pressed', 'true');
    } else if (state === 'paused') {
      if (playLabel) playLabel.textContent = T.resume;
      playBtn.setAttribute('aria-label', T.resumeAria);
      playBtn.setAttribute('aria-pressed', 'true');
    } else {
      if (playLabel) playLabel.textContent = T.play;
      playBtn.setAttribute('aria-label', hasExplicitMaleVoice() ? T.playAria : (T.playAriaNeutral || T.playAria));
      playBtn.setAttribute('aria-pressed', 'false');
    }
  }

  function applyLabels() {
    if (playLabel) playLabel.textContent = reading ? (playing ? T.pause : T.resume) : T.play;
    if (summaryLabel) summaryLabel.textContent = T.summaryBtn;
    if (prevBtn) prevBtn.setAttribute('aria-label', T.prevAria);
    if (nextBtn) nextBtn.setAttribute('aria-label', T.nextAria);
    if (stopBtn) stopBtn.setAttribute('aria-label', T.stopAria);
    if (bar) {
      bar.setAttribute('aria-label', lang === 'en'
        ? 'Reading aids: listen and summary' : 'Lesehilfen: Vorlesen und Kurzfassung');
    }
    if (playBtn) playBtn.setAttribute('aria-label', hasExplicitMaleVoice() ? T.playAria : (T.playAriaNeutral || T.playAria));
    if (summaryBtn) summaryBtn.setAttribute('aria-label', T.summaryAria);
  }

  function prepareBlocks() {
    lang = detectArticleLanguage();
    T = I18N[lang] || I18N.de;
    blocks = collectBlocks();
    return blocks.length > 0;
  }

  function startReading(fromIndex, forceSpeech) {
    if (reading) return;
    if (!prepareBlocks()) { setStatus(T.noText); return; }

    var useTrack = (mode === 'track' && track && !forceSpeech);
    if (!speechSupported && !useTrack) { setStatus(T.unsupported); return; }

    reading = true;
    playing = true;
    setupMediaSession();

    if (useTrack) {
      setStatus(T.startedTrack);
      setBarState('playing');
      var saved = (typeof fromIndex === 'number' && fromIndex > 0) ? fromIndex : (forceSpeech ? 0 : rememberedBlock());
      trackStart(saved);
      startProgressTicker();
      return;
    }
    startSpeech(typeof fromIndex === 'number' ? fromIndex : 0);
  }

  function pauseReading() {
    if (!reading) return;
    playing = false;
    if (mode === 'track' && track) { trackPause(); setBarState('paused'); setStatus(T.paused); return; }
    pauseSpeech();
  }

  function resumeReading() {
    if (!reading) return;
    playing = true;
    if (mode === 'track' && track) { trackResume(); setBarState('playing'); setStatus(T.resumed); return; }
    resumeSpeech();
  }

  function endReading(announce, completed) {
    reading = false;
    playing = false;
    runId += 1;
    clearPauseTimer();
    clearStartWatchdog();
    stopProgressTicker();
    stopKeepAlive();
    unitInFlight = false;
    liveUtterance = null;
    utteranceRefs.length = 0;
    if (synth) { try { synth.cancel(); } catch (e) {} }
    if (mode === 'track' && track) trackStop();
    clearHighlight();
    if (completed) { completeProgress(); storeDel(STORE_POS); }
    else { resetProgress(0); }
    if (remainEl) remainEl.textContent = '';
    setBarState('idle');
    setFloating(false);
    if (announce) setStatus(T.finished);
  }

  function jumpBlock(delta) {
    if (!reading) return;
    if (mode === 'track' && track) { trackJump(delta); return; }
    if (!units.length) return;
    var cur = units[Math.min(cursor, units.length - 1)];
    var bi = cur ? cur.blockIndex : 0;
    var target = Math.max(0, Math.min(blocks.length - 1, bi + delta));
    if (delta > 0 && bi + delta >= blocks.length) { endReading(true, true); return; }
    var idx = 0;
    for (var i = 0; i < units.length; i++) {
      if (units[i].blockIndex >= target) { idx = i; break; }
    }
    runId += 1;
    clearPauseTimer();
    if (synth) { try { synth.cancel(); } catch (e) {} }
    playing = true;
    setBarState('playing');
    spokenChars = units[idx] ? units[idx].startChars : 0;
    resetProgress(spokenChars);
    speakUnit(idx, true);
    if (blocks[target]) highlightBlock(blocks[target]);
  }

  function toggleReading() {
    if (!reading) {
      // User-Activation-Token: alle Audio-Aufrufe bleiben synchron im Klick.
      if (mode === 'track' && track) startReading(rememberedBlock(), false);
      else startReading(rememberedBlock(), false);
      return;
    }
    if (playing) pauseReading(); else resumeReading();
  }

  /* ---------- Media Session (Sperrbildschirm & Headset) ------- */
  function setupMediaSession() {
    if (!win.navigator || !win.navigator.mediaSession) return;
    try {
      win.navigator.mediaSession.metadata = new win.MediaMetadata({
        title: String(T.mediaTitle || '{title}').replace('{title}', stripMd(cfg.title || doc.title || '')),
        artist: T.mediaArtist,
        album: String(cfg.siteName || 'FranksFinanzcheck')
      });
      win.navigator.mediaSession.playbackState = 'playing';
    } catch (e) {}
    var handlers = {
      play: function () { if (reading && !playing) resumeReading(); },
      pause: function () { if (reading && playing) pauseReading(); },
      stop: function () { if (reading) endReading(true, false); },
      previoustrack: function () { if (reading) jumpBlock(-1); },
      nexttrack: function () { if (reading) jumpBlock(1); }
    };
    Object.keys(handlers).forEach(function (key) {
      try { win.navigator.mediaSession.setActionHandler(key, handlers[key]); } catch (e) {}
    });
  }

  /* ---------- Schwebender Mini-Player ------------------------ */
  var floating = false;
  function setFloating(on) {
    if (!bar || floating === !!on) return;
    floating = !!on;
    if (floating) bar.classList.add('ff-voice-bar--floating');
    else bar.classList.remove('ff-voice-bar--floating');
  }
  function syncFloating() {
    if (!reading || !bar || !slot) { setFloating(false); return; }
    var rect = slot.getBoundingClientRect();
    setFloating(rect.bottom < 8);
  }
  if (typeof win.addEventListener === 'function') {
    var scrollTicking = false;
    win.addEventListener('scroll', function () {
      if (scrollTicking) return;
      scrollTicking = true;
      win.requestAnimationFrame ? win.requestAnimationFrame(function () { scrollTicking = false; syncFloating(); })
        : setTimeout(function () { scrollTicking = false; syncFloating(); }, 100);
    }, { passive: true });
    win.addEventListener('resize', syncFloating, { passive: true });
  }

  /* ---------- Ereignisse ------------------------------------- */
  playBtn.addEventListener('click', toggleReading);
  if (prevBtn) prevBtn.addEventListener('click', function () { jumpBlock(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function () { jumpBlock(1); });
  if (stopBtn) stopBtn.addEventListener('click', function () { if (reading) endReading(true, false); });

  // Seite verlassen / Tab wechseln: gehörte Position sauber sichern.
  if (typeof doc.addEventListener === 'function') {
    doc.addEventListener('visibilitychange', function () {
      if (doc.hidden && reading && playing) pauseReading();
    });
  }
  if (typeof win.addEventListener === 'function') {
    win.addEventListener('pagehide', function () { if (reading) endReading(false, false); });
    win.addEventListener('beforeunload', function () { if (reading) endReading(false, false); });
  }

  /* ---------- Tastatur (WCAG 2.2 / BITV) --------------------- */
  if (typeof doc.addEventListener === 'function') {
    doc.addEventListener('keydown', function (e) {
      if (!e || e.defaultPrevented) return;
      var t = e.target;
      var tn = t && t.tagName ? String(t.tagName).toUpperCase() : '';
      if (tn === 'INPUT' || tn === 'TEXTAREA' || tn === 'SELECT' || (t && t.isContentEditable)) return;
      if (dialogIsOpen && dialogIsOpen()) return;
      if (e.key === 'Escape' && reading) { endReading(true, false); return; }
      if (!reading) return;
      if (e.key === ' ' || e.key === 'Spacebar') {
        // Nur wenn der Fokus in der Toolbar liegt – sonst bleibt die
        // Leertaste das normale Blättern der Seite.
        if (bar && t && bar.contains && bar.contains(t)) { e.preventDefault(); toggleReading(); }
        return;
      }
      if (e.key === 'ArrowLeft') { e.preventDefault(); jumpBlock(-1); }
      if (e.key === 'ArrowRight') { e.preventDefault(); jumpBlock(1); }
    });
  }

  /* ============================================================
     13 · KURZFASSUNG — Verlagshaus-Standard im <dialog>
     ------------------------------------------------------------
     Aufbau (Capital / WirtschaftsWoche / Die Zeit als Maßstab):
       1. Byline         Lesezeit · Wörter · Autor · Stand
       2. Kurzantwort    „Das Wichtigste in 30 Sekunden“
       3. Kernaussagen   3–5 redaktionell gerankte Aussagen
       4. Zahlen         Big-Number-Karten (Euro, Prozent, kWh …)
       5. Tabellen       Übersichten im Fokus
       6. Inhalt         Sprungverzeichnis
     Barrierefreiheit: role="dialog", aria-modal, Beschriftung,
     Fokus-Falle, Fokus-Rückkehr, Scroll-Sperre, Escape, Fallback
     für Browser ohne <dialog>.
     ============================================================ */

  var dialog = null;
  var lastFocused = null;
  var fallbackBackdrop = null;

  function el(tag, cls, text) {
    var node = doc.createElement(tag);
    if (cls) node.className = cls;
    if (text != null) node.textContent = String(text);
    return node;
  }

  function dialogIsOpen() {
    if (!dialog) return false;
    if (dialog.classList.contains('ff-voice-dialog--fallback')) return dialog.getAttribute('open') !== null;
    return typeof dialog.open === 'boolean' ? dialog.open : dialog.getAttribute('open') !== null;
  }

  function lockScroll(on) {
    try {
      if (!doc.body) return;
      if (on) {
        doc.body.style.overflow = 'hidden';
        doc.body.style.paddingRight = '0px';
      } else {
        doc.body.style.overflow = '';
        doc.body.style.paddingRight = '';
      }
    } catch (e) {}
  }

  function focusables(root) {
    return qsa('a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])', root)
      .filter(function (n) { return n.offsetWidth > 0 || n.offsetHeight > 0 || n === doc.activeElement; });
  }

  function trapFocus(e) {
    if (!dialog) return;
    var list = focusables(dialog);
    if (!list.length) return;
    var first = list[0];
    var last = list[list.length - 1];
    if (e.shiftKey && doc.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && doc.activeElement === last) { e.preventDefault(); first.focus(); }
  }

  /* ---------- Inhalte der Kurzfassung ------------------------ */

  function collectHeadings() {
    var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
    if (!content) return [];
    return qsa('h2, h3', content).filter(function (h) {
      if (isReaderSkipped(h)) return false;
      return readableText(h).length > 2;
    });
  }

  function collectTables() {
    var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
    if (!content) return [];
    var seen = [];
    var out = [];
    qsa('table, [role="table"], [role="grid"]', content).forEach(function (t) {
      if (isReaderSkipped(t)) return;
      var inner = innerTable(t);
      if (!inner || seen.indexOf(inner) !== -1) return;
      seen.push(inner);
      var model = buildTableModel(inner);
      if (!model.rows.length && !model.headers.length) return;
      out.push(model);
    });
    return out;
  }

  /** Kernaussagen: die ersten tragenden Sätze der Abschnitte. */
  function buildKeypoints(limit) {
    var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
    if (!content) return [];
    var headings = collectHeadings();
    var out = [];
    headings.forEach(function (h) {
      if (out.length >= limit) return;
      if (tagOf(h) !== 'H2') return;
      var node = h.nextElementSibling;
      var guard = 0;
      while (node && guard++ < 6) {
        if (tagOf(node) === 'P') {
          var text = readableText(node);
          if (text.length > 40) {
            out.push(firstSentences(text, 2));
            return;
          }
        }
        if (/^H[23]$/.test(tagOf(node))) return;
        node = node.nextElementSibling;
      }
    });
    if (!out.length) {
      qsa('p', content).slice(0, 6).forEach(function (p) {
        if (out.length >= limit) return;
        var text = readableText(p);
        if (text.length > 60) out.push(firstSentences(text, 2));
      });
    }
    return out.slice(0, limit);
  }

  function firstSentences(text, n) {
    return sentences(String(text)).slice(0, n).join(' ').trim();
  }

  /** Zahlen auf einen Blick: Beträge, Prozente, Energiemengen. */
  function buildFigures(limit) {
    var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
    if (!content) return [];
    var text = readableText(content);
    var found = [];
    var seen = [];

    var moneyRe = /(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?)\s?(€|EUR|Euro)/gi;
    var m;
    while ((m = moneyRe.exec(text)) !== null && found.length < limit) {
      var value = m[1] + ' €';
      var key = value.toLowerCase();
      if (seen.indexOf(key) !== -1) continue;
      seen.push(key);
      found.push({ value: value, label: labelAround(text, m.index, m[0].length, 'Euro') });
    }
    var pctRe = /(\d{1,3}(?:[.,]\d{1,2})?)\s?%/g;
    while ((m = pctRe.exec(text)) !== null && found.length < limit) {
      var pv = m[1] + ' %';
      var pkey = pv.toLowerCase();
      if (seen.indexOf(pkey) !== -1) continue;
      seen.push(pkey);
      found.push({ value: pv, label: labelAround(text, m.index, m[0].length, 'Prozent') });
    }
    return found.slice(0, limit);
  }

  /** Sucht das sinntragende Substantiv vor einem Zahlenfund. */
  function labelAround(text, index, length, fallback) {
    var before = String(text).slice(Math.max(0, index - 90), index);
    var after = String(text).slice(index + length, index + length + 60);
    var cand = (before.match(/([A-ZÄÖÜ][\wäöüßÄÖÜ-]{3,})\s+(?:von|bis|auf|um|rund|etwa|ca\.?|circa)?\s*$/) || [])[1];
    if (cand) return cand;
    var afterCand = (after.match(/^\s*(?:pro|je|für|im|pro)\s+([A-Za-zÄÖÜäöüß]{3,})/) || [])[1];
    if (afterCand) return 'pro ' + afterCand;
    return fallback;
  }

  function buildToc() {
    return collectHeadings().map(function (h) {
      var id = h.getAttribute('id');
      if (!id) {
        id = 'ff-voice-sec-' + Math.random().toString(36).slice(2, 8);
        h.setAttribute('id', id);
      }
      return { id: id, text: readableText(h), level: parseInt(tagOf(h).slice(1), 10) };
    });
  }

  function summaryPlainText() {
    var lines = [];
    lines.push(String(cfg.title || doc.title || ''));
    lines.push('');
    if (cfg.kurzantwort) { lines.push(stripMd(cfg.kurzantwort)); lines.push(''); }
    var kp = buildKeypoints(5);
    if (kp.length) {
      lines.push(T.summaryKeypoints);
      kp.forEach(function (k, i) { lines.push((i + 1) + '. ' + k); });
      lines.push('');
    }
    var toc = buildToc();
    if (toc.length) {
      lines.push(T.summaryToc);
      toc.forEach(function (t) { lines.push('· ' + t.text); });
    }
    return lines.join('\n');
  }

  /* ---------- Aufbau des Dialogs ----------------------------- */

  function buildDialog() {
    if (dialog) return dialog;
    var dlg = el('div', 'ff-voice-dialog');
    dlg.setAttribute('role', 'dialog');
    dlg.setAttribute('aria-modal', 'true');
    dlg.setAttribute('aria-label', T.summaryBtn + ' – ' + stripMd(cfg.title || ''));
    dlg.id = 'ff-voice-dialog';

    var head = el('div', 'ff-voice-dialog__head');
    var headText = el('div');
    headText.appendChild(el('div', 'ff-voice-dialog__eyebrow', T.summaryEyebrow));
    headText.appendChild(el('h2', 'ff-voice-dialog__title', stripMd(cfg.title || doc.title || '')));
    head.appendChild(headText);
    var closeBtn = el('button', 'ff-voice-dialog__close', '\u00d7');
    closeBtn.type = 'button';
    closeBtn.setAttribute('aria-label', T.summaryClose);
    head.appendChild(closeBtn);
    dlg.appendChild(head);

    var body = el('div', 'ff-voice-dialog__body');

    // 1 · Byline
    var byline = el('ul', 'ff-voice-byline');
    if (cfg.readingTime) byline.appendChild(el('li', null, T.summaryReadingTime.replace('{time}', cfg.readingTime)));
    if (cfg.wordCount) byline.appendChild(el('li', null, T.summaryWords.replace('{count}', cfg.wordCount)));
    if (cfg.author) byline.appendChild(el('li', null, T.summaryAuthor.replace('{name}', cfg.author)));
    if (cfg.date) byline.appendChild(el('li', null, T.summaryStand.replace('{date}', cfg.date)));
    if (cfg.updated) byline.appendChild(el('li', null, T.summaryUpdated.replace('{date}', cfg.updated)));
    if (byline.children.length) body.appendChild(byline);

    // 2 · Kurzantwort
    if (cfg.kurzantwort) {
      var secQuick = el('section', 'ff-voice-sec');
      secQuick.appendChild(el('h3', 'ff-voice-sec__h', T.summaryQuick));
      secQuick.appendChild(el('p', 'ff-voice-quick', stripMd(cfg.kurzantwort)));
      body.appendChild(secQuick);
    }

    // 3 · Kernaussagen
    var kp = buildKeypoints(5);
    if (kp.length) {
      var secKp = el('section', 'ff-voice-sec');
      secKp.appendChild(el('h3', 'ff-voice-sec__h', T.summaryKeypoints));
      var ul = el('ul', 'ff-voice-list ff-voice-list--plain');
      kp.forEach(function (k) { ul.appendChild(el('li', null, k)); });
      secKp.appendChild(ul);
      body.appendChild(secKp);
    }

    // 4 · Zahlen auf einen Blick
    var figures = buildFigures(6);
    if (figures.length) {
      var secFig = el('section', 'ff-voice-sec');
      secFig.appendChild(el('h3', 'ff-voice-sec__h', T.summaryFigures));
      var grid = el('div', 'ff-voice-figures');
      figures.forEach(function (f) {
        var card = el('div', 'ff-voice-figure');
        card.appendChild(el('span', 'ff-voice-figure__value', f.value));
        card.appendChild(el('span', 'ff-voice-figure__label', f.label));
        grid.appendChild(card);
      });
      secFig.appendChild(grid);
      body.appendChild(secFig);
    }

    // 5 · Tabellen & Übersichten
    var tables = collectTables();
    if (tables.length) {
      var secTab = el('section', 'ff-voice-sec');
      secTab.appendChild(el('h3', 'ff-voice-sec__h', T.summaryTables));
      var wrap = el('div', 'ff-voice-tables');
      tables.slice(0, 6).forEach(function (model) {
        var card = el('div', 'ff-voice-tablecard');
        card.appendChild(el('h4', 'ff-voice-tablecard__h', model.title || T.tableDefault));
        var rows = model.rows.length;
        var meta = T.summaryRowCount.replace('{count}', rows);
        if (rows === 1) meta = T.summaryRowCountOne;
        card.appendChild(el('p', 'ff-voice-tablecard__meta',
          model.colCount + ' \u00d7 ' + meta));
        wrap.appendChild(card);
      });
      secTab.appendChild(wrap);
      body.appendChild(secTab);
    }

    // 6 · Inhaltsverzeichnis
    var toc = buildToc();
    if (toc.length) {
      var secToc = el('section', 'ff-voice-sec');
      secToc.appendChild(el('h3', 'ff-voice-sec__h', T.summaryToc));
      var tocList = el('ul', 'ff-voice-toc');
      toc.forEach(function (item) {
        var li = el('li');
        var a = el('a', null, item.text);
        a.href = '#' + item.id;
        a.setAttribute('aria-label', T.summaryJump + ': ' + item.text);
        a.addEventListener('click', function () { closeDialog(); });
        li.appendChild(a);
        tocList.appendChild(li);
      });
      secToc.appendChild(tocList);
      body.appendChild(secToc);
    }

    if (!body.children.length) body.appendChild(el('p', null, T.summaryEmpty));

    dlg.appendChild(body);

    // Fußzeile
    var foot = el('div', 'ff-voice-dialog__foot');
    var copyBtn = el('button', 'ff-voice-btn', T.summaryCopy);
    copyBtn.type = 'button';
    copyBtn.id = 'ff-voice-copy';
    copyBtn.addEventListener('click', function () {
      var text = summaryPlainText();
      var ok = false;
      try {
        if (win.navigator && win.navigator.clipboard && win.navigator.clipboard.writeText) {
          win.navigator.clipboard.writeText(text);
          ok = true;
        } else {
          var ta = doc.createElement('textarea');
          ta.value = text;
          ta.setAttribute('readonly', '');
          ta.style.position = 'fixed';
          ta.style.opacity = '0';
          doc.body.appendChild(ta);
          ta.select();
          ok = !!doc.execCommand('copy');
          doc.body.removeChild(ta);
        }
      } catch (e) { ok = false; }
      if (win.__ff_voice_copied) win.__ff_voice_copied(text);
      copyBtn.textContent = ok ? T.summaryCopied : T.summaryCopyFail;
      setTimeout(function () { copyBtn.textContent = T.summaryCopy; }, 2200);
    });
    foot.appendChild(copyBtn);

    var readFull = el('a', 'ff-voice-link', T.summaryReadFull + ' \u2192');
    readFull.href = String(cfg.permalink || doc.location.pathname);
    readFull.addEventListener('click', function () { closeDialog(); });
    foot.appendChild(readFull);
    dlg.appendChild(foot);

    closeBtn.addEventListener('click', closeDialog);

    try { doc.body.appendChild(dlg); } catch (e) {}
    dialog = dlg;

    // Fallback, wenn <dialog> nicht unterstützt wird
    if (typeof dlg.showModal !== 'function' && typeof win.HTMLDialogElement === 'undefined') {
      dlg.classList.add('ff-voice-dialog--fallback');
    }
    return dlg;
  }

  function addFallbackBackdrop() {
    if (fallbackBackdrop) return;
    fallbackBackdrop = el('div', 'ff-voice-backdrop');
    fallbackBackdrop.addEventListener('click', closeDialog);
    try { doc.body.appendChild(fallbackBackdrop); } catch (e) {}
  }
  function removeFallbackBackdrop() {
    if (fallbackBackdrop && fallbackBackdrop.parentNode) fallbackBackdrop.parentNode.removeChild(fallbackBackdrop);
    fallbackBackdrop = null;
  }

  function openDialog() {
    lastFocused = doc.activeElement;
    var dlg = buildDialog();
    lockScroll(true);
    var useNative = typeof dlg.showModal === 'function';
    if (useNative) {
      try { dlg.showModal(); } catch (e) { useNative = false; }
    }
    if (!useNative) {
      dlg.classList.add('ff-voice-dialog--fallback');
      dlg.setAttribute('open', '');
      addFallbackBackdrop();
    }
    var focusTarget = dlg.querySelector('.ff-voice-dialog__close') || dlg;
    try { focusTarget.focus(); } catch (e) {}
  }

  function closeDialog() {
    if (!dialog || !dialogIsOpen()) return;
    var fallback = dialog.classList.contains('ff-voice-dialog--fallback');
    if (!fallback && typeof dialog.close === 'function') {
      try { dialog.close(); } catch (e) {}
    }
    if (fallback || dialog.getAttribute('open') !== null) {
      dialog.removeAttribute('open');
      dialog.classList.remove('ff-voice-dialog--fallback');
      removeFallbackBackdrop();
    }
    lockScroll(false);
    if (lastFocused && typeof lastFocused.focus === 'function') {
      try { lastFocused.focus(); } catch (e) {}
    }
    lastFocused = null;
  }

  summaryBtn.addEventListener('click', openDialog);

  if (typeof doc.addEventListener === 'function') {
    doc.addEventListener('keydown', function (e) {
      if (!dialogIsOpen()) return;
      if (e.key === 'Escape') {
        if (dialog.classList.contains('ff-voice-dialog--fallback')) { e.preventDefault(); closeDialog(); return; }
        return;   // native <dialog> behandelt Escape selbst
      }
      if (e.key === 'Tab') trapFocus(e);
    });
  }

  /* ============================================================
     14 · INITIALISIERUNG
     ============================================================ */

  var trackReady = initTrack();
  mode = trackReady ? 'track' : 'speech';
  if (!trackReady && !speechSupported) {
    if (playBtn) playBtn.disabled = true;
    setStatus(T.unsupported);
  }

  applyLabels();
  setBarState('idle');

  // Test- und Diagnose-Schnittstelle (kein Tracking, keine Netzaufrufe)
  win.__ffVoice = {
    version: VOICE_VERSION,
    get mode() { return mode; },
    get blocks() { return blocks.slice(); },
    get units() { return units.slice(); },
    get lang() { return lang; },
    get reading() { return reading; },
    get playing() { return playing; },
    get trackReady() { return trackReady; },
    speechNormalize: speechNormalize,
    sentences: sentences,
    splitForSpeech: splitForSpeech,
    collectBlocks: collectBlocks,
    buildTimeline: function () {
      if (!blocks.length) blocks = collectBlocks();
      return buildTimeline(blocks, quality.rate || 1);
    },
    resolveMaleVoice: resolveMaleVoice,
    detectArticleLanguage: detectArticleLanguage,
    sniffSentenceLang: sniffSentenceLang,
    buildTableModel: buildTableModel,
    summaryPlainText: summaryPlainText,
    buildKeypoints: function () { return buildKeypoints(5); },
    buildFigures: function () { return buildFigures(6); },
    openSummary: openDialog,
    closeSummary: closeDialog,
    start: function () { startReading(0, mode !== 'track'); },
    stop: function () { endReading(false, false); }
  };
})();
