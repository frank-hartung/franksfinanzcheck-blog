/* ============================================================
   FranksFinanzcheck – Premium Lesehilfen (Vorlesen + Kurzfassung)
   03.09.2026 — Profi-Agentur & Chefredakteur-Standard · Highend v6
   · Vorlesen v6: Vollständige Vorlesefunktion auf Verlagsspitze
     (übertrifft Capital / WirtschaftsWoche / Die Zeit) — High-End Garantie
     für explizit männliche Stimme DE & EN ohne Umschalter, mit
     sofortigem Tonpfad auch bei lazy Voice-Katalogen
   · Kurzfassung v4: Vollständige Verlagshaus-Kurzfassung
     (Kurzantwort, Kernaussagen, Zahlen auf einen Blick,
     Inhaltsverzeichnis, Tabellen-Highlights, Byline, Fokus-Falle)
   ------------------------------------------------------------
   - Privacy-first & First-party: ausschließlich lokale Web Speech API.
   - Tonpfad & Queue-Stabilität:
       · synchrones Speech-Unfreezing im Klick-Event-Kontext
         (verhindert das Erlöschen des User-Activation-Tokens)
       · Anti-Stall Engine-Watchdog & Chrome-Queue-Reset
       · V8 Garbage-Collection-Shield für lückenlosen Klang
   - Männliche Sprache – vollautomatisch Deutsch (DE) und Englisch
     (EN), ohne manuellen Umschalter und ohne Stimmen-Menü. Die Engine
     wählt deterministisch die beste verfügbare männliche Studio-/
     Neural-Stimme je Sprache (inkl. Nachbarsprachen-Fallback).
     Englische Sätze in deutschen Artikeln liest die männliche
     EN-Stimme – und umgekehrt (zweisprachiger Hörfunk-Moderator).
     Garantie-Kern: Explizit männliche Stimmen sprechen in natürli-
     cher männlicher Tonlage; geschlechtsneutral/unbenannte Stimmen
     (z. B. „Google Deutsch“) werden automatisch in die männliche
     Klangzone abgesenkt. Wenn ein Gerät keine männliche Stimme anbietet,
     startet der Reader hörbar in der gewünschten Sprache und kennzeichnet
     den technischen Fallback ehrlich.
   - Vollautomatische Studio-Regie statt Reglern:
       · Automatische Tempoanpassung  – Rolle (Überschrift, Fließtext,
         Tabelle …) × Stimmen-Güte × Informationsdichte des Satzes:
         Zahlen, lange Komposita und Schachtelsätze werden automatisch
         ruhiger gelesen, kurze Sätze flüssiger.
       · Automatische maximale Chunk-Länge – kurze Sätze werden zu
         natürlichen Atemgruppen gebündelt, lange Sätze an Neben-
         satz-Grenzen geteilt; die Obergrenze folgt der Stimmen-Güte
         und bleibt hart unter der Chrome-15-Sekunden-Abbruchgrenze.
       · Automatische Pausen-Skalierung – Atem-, Denk- und Gliederungs-
         pausen je Satzzeichen, gehörter Satzlänge (Hör-Digest), Rolle,
         Satzmelodie und Sprechtempo – niemals starr, niemals gehetzt.
       · Automatische Tonlagen-Korrektur – männliche Grund-Tonlage je
         Rolle & Stimmenklasse, Satzmelodie (Fragen steigen, Ausrufe
         betonen), Mikro-Modulation gegen Monotonie bei einfachen
         Stimmen, Absenkung in die männliche Zone, falls als letzter
         Notnagel eine nicht-männliche Stimme dienen müsste.
       · Verlagshaus-Regie v4 – Konnektoren-Atemgruppen (Schnitte an
         Diskursmarkern wie „weil“, „allerdings“, „however“ für
         natürliche Intonationsbögen), Final-Längung am Blockende
         (wie ein Sprecher am Absatzschluss), satzfortschritts-
         genauer Fortschritt (Boundary-Ereignisse) und ein schwe-
         bender Mini-Player, der beim Scrollen verfügbar bleibt.
   - Maximale Barrierefreiheit (WCAG 2.2 AAA / BITV) für Fließtext,
     Überschriften, Listen sowie Tabellen & Übersichten mit
     zeilengenauer Live-Synchronisation und Vorlese-Kontext.
   - Robuste Browser-Kompatibilität, Stimmen-Warte-Schutz (nie mit
     einer zufälligen/weiblichen Standardstimme starten), Utterance-
     GC-Schutz gegen Chrome-Abbrüche, Android-Pause-Härtung und
     automatische Keep-Alive-Wache.
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
      listenAriaNeutral: 'Artikel vorlesen (Stimme deines Geräts)',
      pauseAria: 'Vorlesen pausieren',
      resumeAria: 'Vorlesen fortsetzen',
      stopAria: 'Vorlesen beenden',
      summaryBtn: 'Kurzfassung',
      summaryAria: 'Kurzfassung des Artikels anzeigen',
      unsupported: 'Vorlesen wird von deinem Browser nicht unterstützt.',
      noText: 'Kein vorlesbarer Text gefunden.',
      started: 'Vorlesen gestartet.',
      voiceActive: 'Männliche Stimme aktiv.',
      voiceFallback: 'Vorlesen gestartet; dein Gerät stellt keine männliche Stimme bereit.',
      speechError: 'Dieser Abschnitt konnte nicht abgespielt werden; es geht weiter.',
      voiceLoading: 'Männliche Stimme wird geladen …',
      audioReady: 'Studiostimme aktiv (Frank).',
      audioLoading: 'Audiofassung wird geladen …',
      audioPlaying: 'Audiofassung läuft.',
      audioError: 'Audiofassung nicht verfügbar – Geräte­stimme übernimmt.',
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
      cueCorrection: 'Korrekturhinweis:',
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
      summaryToc: '🧭 In diesem Artikel',
      summaryJump: 'Zum Abschnitt',
      summaryJumpTable: 'Zur Tabelle',
      summaryAuthor: 'Autor: {name}',
      summaryStand: 'Stand: {date}',
      summaryEmpty: 'Für diesen Artikel liegt derzeit keine Kurzfassung vor.',
      summaryRowCount: '{count} Zeilen',
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
      listenAriaNeutral: 'Read article aloud (voice provided by your device)',
      pauseAria: 'Pause speech',
      resumeAria: 'Resume speech',
      stopAria: 'Stop speech',
      summaryBtn: 'Summary',
      summaryAria: 'Show article summary',
      unsupported: 'Speech synthesis is not supported by your browser.',
      noText: 'No readable text found.',
      started: 'Audio playback started.',
      voiceActive: 'Male voice active.',
      voiceFallback: 'Playback started; your device does not provide a male voice.',
      speechError: 'This section could not be played; continuing.',
      voiceLoading: 'Loading a male voice …',
      audioReady: 'Studio voice active (Frank).',
      audioLoading: 'Loading audio version …',
      audioPlaying: 'Audio version playing.',
      audioError: 'Audio version unavailable – device voice takes over.',
      paused: 'Audio playback paused.',
      resumed: 'Audio playback resumed.',
      finished: 'Audio playback completed.',
      resumedPos: 'Resumed from your last listening position.',
      remaining: 'approx. {min} min left',
      mediaArtist: 'FranksFinanzcheck – Article Audio',
      introLine: '{title}. An article by FranksFinanzcheck. Listening time about {time} minutes.',
      outroLine: 'End of article. Thank you for listening to FranksFinanzcheck.',
      listItemNum: 'Point {n}:',
      cueShortAnswer: 'Short answer:',
      cueCorrection: 'Correction:',
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
      summaryToc: '🧭 In this article',
      summaryJump: 'Go to section',
      summaryJumpTable: 'Go to table',
      summaryAuthor: 'Author: {name}',
      summaryStand: 'As of {date}',
      summaryEmpty: 'No summary is currently available for this article.',
      summaryRowCount: '{count} rows',
      readingTime: '⏱️ approx. {time} min read',
      wordCount: '{count} words',
      sectionCount: '{count} sections',
      source: 'Source: '
    }
  };

  /* ---------- Automatische Spracherkennung (DE / EN) — High-End v5 ---------- 
     Ohne Umschalter: Erkennt Deutsch und Englisch VOLLAUTOMATISCH, auch wenn
     die Seite als "de" deklariert ist (einsprachiges Hugo-Setup) und der
     Artikel auf Englisch verfasst ist. Heuristik prüft Titel, Description
     UND den sichtbaren Fließtext (bis 1.800 Zeichen) mit Gewichtung für
     Umlaute/ß und typische Stoppwörter. Roh-Sprache "de" wird nur bei
     klarer EN-Mehrheit überschrieben – umgekehrt genauso. */
  function detectArticleLanguage() {
    var raw = String(cfg.lang || toolbar.getAttribute('data-page-lang') || doc.documentElement.lang || 'de').toLowerCase();
    var base = raw.indexOf('en') === 0 ? 'en' : 'de';
    var sample = String(cfg.title || '') + ' ' + String(cfg.description || '') + ' ';

    // Never use the whole body as the primary sample. Footer labels, the
    // toolbar and related articles are usually German and used to flip a
    // genuinely English article back to German. Read only the article.
    try {
      var content = doc.querySelector && (doc.querySelector('.post-content') || doc.querySelector('.md-content'));
      if (content) sample += String(content.innerText || content.textContent || '').slice(0, 5000);
      else if (doc.body && doc.body.innerText) sample += doc.body.innerText.slice(0, 2200);
    } catch (e) {}

    var tokens = sample.toLowerCase().match(/[a-zäöüß]+/g) || [];
    var deWords = {
      der: 2, die: 2, das: 2, und: 2, ist: 2, sind: 2, für: 2, mit: 2,
      von: 1, ein: 1, eine: 1, einen: 1, einem: 1, den: 1, dem: 1,
      auf: 1, zu: 1, im: 1, am: 1, bei: 1, auch: 1, sich: 1, nicht: 1,
      sparen: 2, spart: 2, euro: 2, versicherung: 2, kosten: 2,
      vertrag: 2, vergleich: 2, wechseln: 2, günstig: 2, kostenlos: 2,
      ratgeber: 2, tabelle: 2, jahr: 1, monat: 1, sollte: 1, solltest: 1,
      müssen: 1, kann: 1, wichtig: 1, tipp: 1, beachten: 1, prüfen: 1
    };
    var enWords = {
      the: 2, and: 2, is: 2, are: 2, for: 2, with: 2, that: 2, this: 2,
      from: 1, your: 2, you: 2, our: 1, save: 2, saving: 2, money: 2,
      insurance: 2, costs: 2, cost: 2, compare: 2, comparison: 2, guide: 2,
      table: 2, tariff: 1, tariffs: 1, should: 1, will: 1, can: 1,
      have: 1, more: 1, free: 1, cheap: 1, best: 1, important: 1,
      article: 1, summary: 1, read: 1, listen: 1, avoid: 1, switch: 1
    };
    var de = 0;
    var en = 0;
    var deHits = 0;
    var enHits = 0;
    tokens.forEach(function (word) {
      if (deWords[word]) { de += deWords[word]; deHits += 1; }
      if (enWords[word]) { en += enWords[word]; enHits += 1; }
      if (/[äöüß]/.test(word)) de += 2;
      if (word.length >= 6 && /(ung|keit|heit|schaft|lich|ig|isch)$/.test(word)) de += 1;
    });

    // A page language is a useful default, not an absolute lock. Require a
    // clear margin so isolated English product terms do not change a DE read.
    if (base === 'de') {
      return enHits >= 4 && en >= de + 3 && en >= Math.ceil(de * 1.25) ? 'en' : 'de';
    }
    return deHits >= 4 && de >= en + 3 && de >= Math.ceil(en * 1.15) ? 'de' : 'en';
  }

  var currentLang = detectArticleLanguage();
  var texts = I18N[currentLang] || I18N.de;

  // Initiale UI-Labels
  if (listenLabel) listenLabel.textContent = texts.listen;
  if (listenBtn) listenBtn.setAttribute('aria-label', texts.listenAria);
  if (summaryLabel) summaryLabel.textContent = texts.summaryBtn;
  if (summaryBtn) summaryBtn.setAttribute('aria-label', texts.summaryAria);
  if (toolbar) toolbar.setAttribute('aria-label', currentLang === 'en'
    ? 'Reading aids: listen and summary' : 'Lesehilfen: Vorlesen und Kurzfassung');

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
      // ISO-Datum 2026-09-03 -> 3. September 2026 (Chefredakteur-Standard)
      s = s.replace(/\b(\d{4})-(\d{2})-(\d{2})\b/g, function (m, y, mo, d) {
        var mi = parseInt(mo, 10) - 1;
        return MONTHS[mi] ? (parseInt(d, 10) + '. ' + MONTHS[mi] + ' ' + y) : m;
      });
      // Uhrzeit 14:30 -> 14 Uhr 30
      s = s.replace(/\b(\d{1,2}):(\d{2})\s*Uhr\b/g, function (m, h, mi) { return h + ' Uhr ' + (mi === '00' ? '' : mi); });
      // Uhrzeit ohne Uhr-Suffix: 14:30 -> 14 Uhr 30 (nur bei plausibler Zeit)
      s = s.replace(/\b(\d{1,2}):(\d{2})\b(?!\s*(?:Uhr|€|%|Euro))/g, function (m, h, mi) {
        if (parseInt(h, 10) <= 24 && parseInt(mi, 10) < 60) return h + ' Uhr ' + (mi === '00' ? '' : mi);
        return m;
      });
      // Jahrzehnte sprechbar: die 90er -> die Neunziger
      var DECADES = { 20: 'Zwanziger', 30: 'Dreißiger', 40: 'Vierziger', 50: 'Fünfziger', 60: 'Sechziger', 70: 'Siebziger', 80: 'Achtziger', 90: 'Neunziger' };
      s = s.replace(/\b(20|30|40|50|60|70|80|90)er\b/g, function (m, d) { return DECADES[d] || m; });
      // Paragraphen & Rechtsbezüge
      s = s.replace(/§§\s*/g, 'die Paragrafen ');
      s = s.replace(/§\s*/g, 'Paragraf ');
      // SGB mit römischer Ziffer: § 12 SGB V -> Sozialgesetzbuch Fünf
      var ROMAN_DE = { I: 'Eins', II: 'Zwei', III: 'Drei', IV: 'Vier', V: 'Fünf', VI: 'Sechs', VII: 'Sieben', VIII: 'Acht', IX: 'Neun', X: 'Zehn', XI: 'Elf', XII: 'Zwölf' };
      s = s.replace(/\bSGB\s+([IVX]+)\b/g, function (m, r) {
        var w = ROMAN_DE[r.toUpperCase()];
        return w ? 'Sozialgesetzbuch ' + w : m;
      });
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
      // Kaufmännisches & und redaktionelle Zahlgrößen-Abkürzungen
      // (Look-ahead statt \b nach dem Punkt: „Mio. “ endet auf Nichtwort)
      s = s.replace(/&/g, ' und ');
      s = s.replace(/\b(?:Tsd|tsd)\.(?![\wäöüßÄÖÜ])/g, 'Tausend');
      s = s.replace(/\b[TM]sd\b(?![\wäöüßÄÖÜ])/g, 'Tausend');
      s = s.replace(/\b(?:Mio|mio)\.(?![\wäöüßÄÖÜ])/g, 'Millionen');
      s = s.replace(/\bMio\b(?![\wäöüßÄÖÜ])/g, 'Millionen');
      s = s.replace(/\b(?:Mrd|mrd)\.(?![\wäöüßÄÖÜ])/g, 'Milliarden');
      s = s.replace(/\bMrd\b(?![\wäöüßÄÖÜ])/g, 'Milliarden');
      s = s.replace(/\b(?:Std|std)\.(?![\wäöüßÄÖÜ])/g, 'Stunden');
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
      // ISO-Datum 2026-09-03 -> September 3, 2026 (Chefredakteur-Standard;
      // bewusst VOR den Zahlenbereich-Regeln, sonst frisst „2026-09“ der Bereich)
      s = s.replace(/\b(\d{4})-(\d{2})-(\d{2})\b/g, function (m, y, mo, d) {
        var MEN = ['January','February','March','April','May','June','July','August','September','October','November','December'];
        var mi = parseInt(mo, 10) - 1;
        return MEN[mi] ? (MEN[mi] + ' ' + parseInt(d, 10) + ', ' + y) : m;
      });
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
      s = s.replace(/&/g, ' and ');
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
      /* „vs." – der Punkt MUSS mit verschwinden. Die frühere Fassung
         /\bvs\.?\b/ ließ ihn stehen („versus."), weil nach einem Punkt
         keine Wortgrenze mehr folgt und die Regex auf „vs" zurückfiel. */
      s = s.replace(/\bvs\.(?![\wäöüßÄÖÜ])/gi, 'versus');
      s = s.replace(/\bvs\b/gi, 'versus');
      s = s.replace(/\bmin\.(?![\wäöüßÄÖÜ])/gi, 'minimum');
      s = s.replace(/\bmax\.(?![\wäöüßÄÖÜ])/gi, 'maximum');
      // Zweite Redaktions-Stufe (v3): etc., No.
      s = s.replace(/\betc\.(?![\wäöüßÄÖÜ])/gi, 'et cetera');
      s = s.replace(/\bNo\.\s*(\d+)/g, 'number $1');
      // Finales Währungs-Auffangnetz Englisch
      s = s.replace(/€/g, ' Euros');
      s = s.replace(/\bEUR\b/g, 'Euros');
      s = s.replace(/%/g, ' percent');
      s = s.replace(/\$/g, ' Dollars');
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
      /* „vs." – der Punkt MUSS mit verschwinden. Die frühere Fassung
         /\bvs\.?\b/ ließ ihn stehen („versus."), weil nach einem Punkt
         keine Wortgrenze mehr folgt und die Regex auf „vs" zurückfiel. */
      s = s.replace(/\bvs\.(?![\wäöüßÄÖÜ])/gi, 'versus');
      s = s.replace(/\bvs\b/gi, 'versus');
      // Abkürzungen Deutsch – zweite Redaktions-Stufe (v3)
      s = s.replace(/\bv\.\s?a\.(?![\wäöüßÄÖÜ])/gi, 'vor allem');
      s = s.replace(/\bz\.\s?T\.(?![\wäöüßÄÖÜ])/gi, 'zum Teil');
      s = s.replace(/\bu\.\s?s\.\s?w\.(?![\wäöüßÄÖÜ])/gi, 'und so weiter');
      s = s.replace(/\bo\.\s?Ä\.(?![\wäöüßÄÖÜ])/g, 'oder Ähnliches');
      s = s.replace(/\betc\.(?![\wäöüßÄÖÜ])/gi, 'et cetera');
      s = s.replace(/\bzzgl\.(?![\wäöüßÄÖÜ])/gi, 'zuzüglich');
      s = s.replace(/\bMwSt\.?(?![\wäöüßÄÖÜ])/g, 'Mehrwertsteuer');
      s = s.replace(/\bMin\.(?![\wäöüßÄÖÜ])/g, 'Minuten');
      s = s.replace(/\bPkt\.(?![\wäöüßÄÖÜ])/g, 'Punkt');
      s = s.replace(/\bTab\.(?![\wäöüßÄÖÜ])/g, 'Tabelle');
      s = s.replace(/\bAbb\.(?![\wäöüßÄÖÜ])/g, 'Abbildung');
      s = s.replace(/(?:\bJh\.|\bJhd\.|\bJhdt\.)(?![\wäöüßÄÖÜ])/g, 'Jahrhundert');
      s = s.replace(/\bAnm\.(?![\wäöüßÄÖÜ])/g, 'Anmerkung');
      s = s.replace(/\bggf\b(?!\.)(?![\wäöüßÄÖÜ])/gi, 'gegebenenfalls');
      // Finales Währungs-Auffangnetz: jedes verbleibende Zeichen sprechbar
      s = s.replace(/€/g, ' Euro');
      s = s.replace(/\bEUR\b/g, 'Euro');
      s = s.replace(/%/g, ' Prozent');
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
     1) VORLESEN – Highend-Sprachausgabe (Redaktions-Studio-Engine v5)
     ------------------------------------------------------------
     Über Verlagshaus-Niveau durch:
       - Synchroner Start im Klickpfad ohne künstlichen Web-Audio-Chime
       - Synchrones Speech-Unfreezing im Klick-Event-Kontext
         (kein Erlöschen des User-Activation-Tokens durch Timer)
       - Satzgenaue Prosodie-Engine mit Atem- und Denkpausen
       - Typografische Aussprache-Veredelung (Zahlen, Daten, §§,
         Prozente, IBAN, Abkürzungen, Finanz-Akronyme, Domains)
       - Rollen-basierte Stimmführung (Überschrift, Fließtext,
         Zitat, Warnung, Tabellenzeile) wie im Hörfunk-Studio
       - Neuronale Stimmen-Rangliste (automatisch, männlich bevorzugt, DE/EN)
       - Automatische Qualitätsanpassung (Stimme, Tempo, Chunking,
         Pausen, Fallback) – ohne Regler, ohne Tempo-Anzeige
       - Abschnitts-Navigation, Merken der Hörposition
       - Media-Session (Sperrbildschirm/Kopfhörer-Tasten)
       - Anti-Stall-Watchdog, Utterance-GC-Shield & Android-Pause-Härtung
  ============================================================ */

  var synth = win.speechSynthesis || null;
  var speechSupported = !!(synth && typeof win.SpeechSynthesisUtterance === 'function');

  var STORE_POS = 'ff-reader:pos:' + (win.location ? win.location.pathname : '');

  function storeGet(k) { try { return win.localStorage.getItem(k); } catch (e) { return null; } }
  function storeSet(k, v) { try { win.localStorage.setItem(k, v); } catch (e) {} }
  function storeDel(k) { try { win.localStorage.removeItem(k); } catch (e) {} }

  var reading = false;
  var playing = false;
  var blocks = [];        // { el, text, lang, type, role, chunks[] }
  var timeline = [];      // flache Liste aller Sprech-Einheiten
  var cursor = 0;     // Einheit, die gerade gesprochen wird/wurde (Highlight, Fortschritt)
  var nextIndex = 0;  // Einheit, die als NÄCHSTE dran ist (Fortsetzen, Keep-Alive)
  var keepAliveId = null;
  var pauseTimer = null;
  var spokenChars = 0;
  var totalChars = 0;
  var prevBtn = doc.getElementById('ff-listen-prev');
  var nextBtn = doc.getElementById('ff-listen-next');
  var remainEl = doc.getElementById('ff-reader-remaining');

  /* ---------- Speech-Engine-Unlocking ---------------------------------
     Web Speech is not a Web-Audio stream. Creating an AudioContext and
     playing a synthetic chime here caused an extra autoplay surface and,
     on some mobile browsers, stole the very activation/queue state that
     the reader needed. Keep this path deliberately small: resume the
     speech engine synchronously in the click handler and let the selected
     SpeechSynthesisVoice be the only audio output. */
  var activeUtterances = [];
  var audioUnlocked = false;

  function unlockAudioEngine() {
    if (audioUnlocked) return;
    audioUnlocked = true;
    if (!speechSupported || !synth) return;
    try {
      if (synth.paused) synth.resume();
    } catch (e) {
      // A browser may expose speechSynthesis before it is ready. The
      // guarded resume is retried immediately before every utterance.
    }
  }
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
    studio:   { rate: 1.00, maxChunk: 210, pauseScale: 1.00, pitchShift: 0.00, dynamic: 0.000 },
    premium:  { rate: 0.98, maxChunk: 195, pauseScale: 1.00, pitchShift: 0.00, dynamic: 0.004 },
    standard: { rate: 0.94, maxChunk: 170, pauseScale: 1.10, pitchShift: 0.02, dynamic: 0.012 },
    basic:    { rate: 0.90, maxChunk: 150, pauseScale: 1.22, pitchShift: 0.05, dynamic: 0.022 }
  };
  var quality = { tier: 'standard', rate: 0.94, maxChunk: 170, pauseScale: 1.1, pitchShift: 0.02, dynamic: 0.012 };
  var errorStreak = 0;  // Fehler in Folge (Synthese-Abbrüche)
  var degradeLevel = 0; // dauerhafte adaptive Herabstufung (0–2)
  // dynamic = automatische Mikro-Modulation der Tonlage gegen Monotonie
  //            (nur bei einfachen Stimmen; Studio-Stimmen behalten 0)

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
      listenBtn.setAttribute('aria-label', hasExplicitMaleVoice() ? texts.listenAria : (texts.listenAriaNeutral || texts.listenAria));
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
    syncFloating();
  }

  /* ---------- Schwebender Mini-Player (Verlagshaus-Audioregie) ----------
     Scrollt die Leser:in während des Vorlesens nach unten, verwandelt
     sich die Toolbar in eine schwebende Steuerleiste am unteren
     Viewport-Rand – die Bedienung bleibt immer greifbar, wie bei den
     Audioplayern von Verlagshäusern. Ohne Vorlesen: keinerlei Effekt.
     Der Platzhalter-Slot hält das Seitenlayout stabil (kein Springen). */
  var toolbarSlot = toolbar.parentElement;
  var toolbarInView = true;
  var floatingActive = false;

  function syncFloating() {
    var want = !!(reading && toolbarSlot && !toolbarInView);
    if (want === floatingActive) return;
    floatingActive = want;
    try {
      if (want) {
        toolbarSlot.style.height = toolbar.offsetHeight + 'px';
        toolbar.classList.add('ff-reader-toolbar--floating');
      } else {
        toolbar.classList.remove('ff-reader-toolbar--floating');
        toolbarSlot.style.height = '';
      }
    } catch (e) {}
  }

  if (toolbarSlot && win.IntersectionObserver) {
    try {
      new win.IntersectionObserver(function (entries) {
        toolbarInView = !!(entries && entries[0] && entries[0].isIntersecting);
        syncFloating();
      }, { threshold: 0.12 }).observe(toolbarSlot);
    } catch (e) {}
  }

  /* ---------- Stimmen-Rangliste: Studio-Qualität zuerst ----------
     NUR-MÄNNLICH-Prinzip (Highend-Regie): Weiblich benannte Stimmen
     werden grundsätzlich aussortiert. Gesucht wird automatisch:
       1. männliche Studio-/Neural-Stimme der Artikelsprache (DE/EN),
       2. sonst eine männliche Stimme einer Nachbarsprache („cross“,
          z. B. macOS ohne deutsche Männerstimme) – niemals weiblich,
       3. absoluter Notnagel: einzige verfügbare Stimme der Sprache
          („fallback“, extrem selten) – die Tonlagen-Korrektur senkt
          sie dann in die männliche Zone ab.
     Die Auswahl wird je Sprache gecacht – kein wiederholtes Sortieren
     pro Satz, dadurch absolut flüssiger Sprechbetrieb.
  ------------------------------------------------------------------ */
  var MALE_KEYWORDS = {
    de: ['conrad', 'stefan', 'florian', 'bernd', 'christoph', 'ralf', 'klaus', 'markus', 'jonas', 'martin',
         'yannick', 'hans', 'viktor', 'thorsten', 'killian', 'kilian', 'jan', 'johannes', 'matthias', 'philipp',
         'sebastian', 'wolfgang', 'dieter', 'achim', 'uwe', 'joerg', 'jörg', 'heinz', 'gerd', 'holger',
         'andreas', 'marcus', 'hannes', 'tobias', 'gustav', 'karl', 'lutz', 'rene', 'kasper',
         'de-de-x-deg', 'de-de-x-deb', 'de-de-x-dea', 'de_de_male', 'male', 'männlich', 'mann', '#male',
         'neural2-b', 'neural2-d', 'wavenet-b', 'wavenet-d', 'standard-b', 'standard-d', 'polyglot'],
    en: ['david', 'george', 'guy', 'mark', 'ryan', 'daniel', 'oliver', 'arthur', 'thomas', 'james', 'alex',
         'fred', 'aaron', 'brian', 'eric', 'richard', 'tom', 'john', 'paul', 'michael', 'peter', 'frank',
         'christopher', 'roger', 'steffan', 'benjamin', 'anthony', 'matthew', 'joseph', 'charles', 'william',
         'robert', 'steven', 'kenneth', 'kevin', 'jason', 'edward', 'joshua', 'andrew', 'brandon', 'justin',
         'raymond', 'gregory', 'samuel', 'patrick', 'jack', 'harry', 'leonard', 'derek', 'liam', 'davis',
         'alfie', 'noah', 'logan',
         'en_us_male', 'en_gb_male', 'male', 'man', '#male', 'neural2-d', 'neural2-h',
         'neural2-i', 'neural2-j', 'wavenet-b', 'wavenet-d', 'standard-b', 'standard-d',
         'journey-d']
  };

  // Ergänzende namentlich männliche Stimmen für die geschlechts-übergreifende Prüfung
  var KNOWN_MALE_VOICES = [
    'conrad', 'killian', 'kilian', 'florian', 'christopher', 'roger', 'steffan', 'stefan', 'ralf', 'guy', 'george',
    'david', 'mark', 'ryan', 'daniel', 'oliver', 'arthur', 'thomas', 'james', 'eric', 'fred', 'aaron',
    'brian', 'richard', 'bernd', 'markus', 'jonas', 'martin', 'johannes', 'philipp', 'sebastian', 'matthias',
    'andreas', 'marcus', 'hannes', 'andrew', 'davis', 'liam', 'christoph', 'kasper', 'alfie', 'jason'
  ];

  var FEMALE_KEYWORDS = [
    'anna', 'katja', 'hedda', 'vicki', 'petra', 'marlene', 'ingrid', 'zira', 'hazel', 'samantha', 'victoria',
    'karen', 'susan', 'jenny', 'helena', 'eva', 'gisela', 'luisa', 'maja', 'elke', 'steffi', 'catherine',
    'linda', 'heather', 'amy', 'emma', 'olivia', 'joanna', 'kendra', 'cortana', 'female', 'weiblich', 'frau',
    'woman', 'girl', '#female', 'siri female', 'seraphina', 'amala', 'kathy', 'nicole', 'moira', 'tessa',
    'maria', 'margaret', 'daniela', 'erika', 'briana', 'brianne', 'andrea', 'alexandra', 'alexa', 'nicola',
    'christina', 'natalie', 'sophie', 'sarah', 'julia', 'laura', 'hanna', 'johanna', 'lena', 'lisa',
    'maren', 'miriam', 'sabrina', 'nadine', 'anke', 'birgit', 'gabriele', 'ursula', 'monika', 'renate',
    'angela', 'sandra', 'claudia', 'susanne', 'martina', 'tanja', 'melanie', 'svenja', 'karin', 'kristin',
    'elsa', 'elena', 'helga', 'tracy', 'michelle', 'stephanie', 'libby', 'maisie', 'sonia', 'natasha',
    'clara', 'annika', 'charlotte', 'lorraine', 'serena', 'nora', 'marissa', 'kimberly', 'salli',
    'ava', 'aria', 'luna', 'thea', 'sonja', 'liv', 'mia', 'kate', 'poppy', 'shelley', 'sandy',
    'neural2-a', 'neural2-c', 'neural2-e', 'wavenet-a', 'wavenet-c', 'wavenet-e'
  ];

  // Namentlich bekannte Studio-/Neuronal-Stimmen (höchste Natürlichkeit)
  var STUDIO_VOICES = [
    'google deutsch', 'microsoft conrad online', 'microsoft killian online', 'microsoft florian online',
    'microsoft ralf', 'anpassbare stimme', 'eloquence', 'siri stimme',
    'google us english', 'microsoft guy online', 'microsoft christopher online', 'microsoft roger online',
    'microsoft eric online', 'microsoft steffan online', 'microsoft stefan online', 'microsoft david online',
    'microsoft mark online', 'microsoft ryan online', 'google us english male', 'google uk english male',
    'microsoft christoph online', 'microsoft andreas online', 'microsoft marcus online',
    'microsoft klaus', 'microsoft andrew online', 'microsoft brian online', 'microsoft davis online',
    'microsoft thomas online', 'microsoft george online', 'microsoft jason online',
    'microsoft stefan', 'microsoft conrad', 'microsoft florian', 'microsoft killian',
    'markus (enhanced)', 'markus (premium)', 'andreas (enhanced)', 'daniel (enhanced)', 'daniel (premium)'
  ];

  var PREMIUM_KEYWORDS = ['natural', 'neural', 'wavenet', 'studio', 'journey', 'polyglot', 'online',
                          'enhanced', 'premium', 'siri', 'high quality', 'highquality', 'google'];
  var LOWQ_KEYWORDS = ['espeak', 'compact', 'pico', 'flite', 'festival', 'novelty', 'whisper', 'bells',
                       'bad news', 'good news', 'bubbles', 'jester', 'organ', 'trinoids', 'zarvox',
                       'albert', 'wobble', 'superstar'];

  /* Wortgrenzen-sicherer Stimmen-Matcher (Highend-Gate v5):
     Eigennamen werden nur als ganze Wörter erkannt – „aria“ trifft
     damit nie „Bulgarian“, „anna“ nie „Joanna“-freie Kontexte,
     „eva“ nie „Available“. Codes und Phrasen („#female“,
     „siri female“, „de-de-x-deg") bleiben Teilstring-Treffer.
     v5-Fix: Unterstriche und Bindestriche werden zu Leerzeichen
     normalisiert, damit „male“ in „en_us_male“ und „female“ in
     „en_us_female“ zuverlässig erkannt wird – entscheidend für die
     Nur-Männlich-Garantie ohne Umschalter (DE & EN). */
  var KW_RE_CACHE = {};
  function voiceHas(hay, kw) {
    var normalizedHay = String(hay || '').toLowerCase().replace(/[_-]+/g, ' ');
    var normalizedKw = String(kw || '').toLowerCase().replace(/[_-]+/g, ' ').trim();
    if (!normalizedKw) return false;
    // Tags and other non-word identifiers are deliberately matched as
    // literals; names are matched on word boundaries so “anna” cannot hit
    // “Johanna” or “aria” cannot hit “Bulgarian”.
    if (!/^[a-z0-9äöü]/.test(normalizedKw)) return normalizedHay.indexOf(normalizedKw) !== -1;
    var re = KW_RE_CACHE[normalizedKw];
    if (!re) {
      try {
        re = new RegExp('\\b' + normalizedKw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\b');
      } catch (e) {
        re = { test: function (value) { return value.indexOf(normalizedKw) !== -1; } };
      }
      KW_RE_CACHE[normalizedKw] = re;
    }
    return re.test(normalizedHay);
  }

  function voiceHay(v) {
    return ((v && v.name) || '') + ' ' + ((v && v.voiceURI) || '');
  }

  function voiceLanguage(v) {
    return String((v && v.lang) || '').toLowerCase().replace(/_/g, '-');
  }

  function languagePrefix(lang) {
    return String(lang || '').toLowerCase().replace(/_/g, '-').split('-')[0];
  }

  function reportedGender(v) {
    var gender = String((v && v.gender) || '').toLowerCase();
    if (gender === 'female' || gender === 'feminine' || gender === 'woman') return 'female';
    if (gender === 'male' || gender === 'masculine' || gender === 'man') return 'male';
    return '';
  }

  function scoreVoice(v, targetLang) {
    var score = 0;
    var langStr = voiceLanguage(v);
    var target = String(targetLang || currentLang || 'de').toLowerCase().replace(/_/g, '-');
    var prefix = languagePrefix(target);
    var hay = voiceHay(v);
    var gender = reportedGender(v);

    // Language fit is a hard preference. resolveMaleVoice additionally
    // filters candidates, so a cross-language voice can never win merely
    // because it has a higher name score.
    if (langStr === target || (target.indexOf('-') === -1 && langStr === prefix)) score += 70;
    else if (languagePrefix(langStr) === prefix) score += 40;
    else score -= 400;

    if (gender === 'male') score += 190;
    else if (gender === 'female') score -= 320;

    var mk = MALE_KEYWORDS[prefix === 'en' ? 'en' : 'de'] || [];
    for (var i = 0; i < mk.length; i++) {
      if (voiceHas(hay, mk[i])) { score += 145; break; }
    }
    for (var j = 0; j < FEMALE_KEYWORDS.length; j++) {
      if (voiceHas(hay, FEMALE_KEYWORDS[j])) { score -= 260; break; }
    }
    for (var studio = 0; studio < STUDIO_VOICES.length; studio++) {
      if (voiceHas(hay, STUDIO_VOICES[studio])) { score += 90; break; }
    }
    for (var premium = 0; premium < PREMIUM_KEYWORDS.length; premium++) {
      if (voiceHas(hay, PREMIUM_KEYWORDS[premium])) { score += 45; break; }
    }
    for (var low = 0; low < LOWQ_KEYWORDS.length; low++) {
      if (voiceHas(hay, LOWQ_KEYWORDS[low])) { score -= 260; break; }
    }

    if (v && v.localService) score += 8; // local voices are more reliable offline
    if (v && v.default) score += 4;
    return score;
  }

  function rankVoicesFromList(list, lang) {
    if (!list || !list.length) return [];
    var targetLang = String(lang || currentLang || 'de').toLowerCase().replace(/_/g, '-');
    var prefix = languagePrefix(targetLang);
    var candidates = list.filter(function (v) { return languagePrefix(voiceLanguage(v)) === prefix; });
    if (!candidates.length) return [];

    // Prefer the requested regional catalog, but do not discard a generic
    // en/de voice when the platform only exposes the other region.
    if (targetLang.indexOf('-') !== -1) {
      var exact = candidates.filter(function (v) { return voiceLanguage(v) === targetLang; });
      if (exact.length) candidates = exact;
    }
    return candidates
      .map(function (v) { return { voice: v, score: scoreVoice(v, targetLang) }; })
      .sort(function (a, b) { return b.score - a.score; });
  }

  function rankVoices(lang) {
    if (!speechSupported) return [];
    var list = [];
    try { list = synth.getVoices() || []; } catch (e) { list = []; }
    return rankVoicesFromList(dedupeVoices(list), lang);
  }

  function dedupeVoices(list) {
    var seen = {};
    var out = [];
    for (var i = 0; i < (list || []).length; i++) {
      var v = list[i];
      if (!v) continue;
      // Browsers sometimes expose the same installed voice once per URI.
      // Keep the first stable entry rather than letting order change on each
      // voiceschanged event.
      var key = voiceLanguage(v) + '|' + String(v.name || '').toLowerCase() + '|' + (v.localService ? 1 : 0);
      if (!seen[key]) { seen[key] = true; out.push(v); }
    }
    return out;
  }

  function isFemaleCandidate(v) {
    if (!v) return true;
    if (reportedGender(v) === 'female') return true;
    var hay = voiceHay(v);
    for (var i = 0; i < FEMALE_KEYWORDS.length; i++) {
      if (voiceHas(hay, FEMALE_KEYWORDS[i])) return true;
    }
    return false;
  }

  /* The browser API rarely exposes gender metadata. Unknown voices are
     therefore usable as a last-resort *neutral* candidate, but they are
     never preferred over an explicitly male voice and are pitch-managed.
     This is honest and avoids the old, silent “first voice wins” bug. */
  function isMaleCandidate(v) {
    return !!v && !isFemaleCandidate(v);
  }

  function isExplicitMaleCandidate(v) {
    return !!(v && isMaleCandidate(v) && explicitMale(v));
  }

  function explicitMale(v) {
    if (!v || isFemaleCandidate(v)) return false;
    if (reportedGender(v) === 'male') return true;
    var hay = voiceHay(v);
    var union = (MALE_KEYWORDS.de || []).concat(MALE_KEYWORDS.en || [], KNOWN_MALE_VOICES);
    for (var i = 0; i < union.length; i++) {
      if (voiceHas(hay, union[i])) return true;
    }
    return false;
  }

  /* Reihenfolge für die männliche Nachbarsprachen-Suche */
  var LANG_FALLBACK = {
    de: ['en-GB', 'en-US', 'en', 'nl-NL', 'fr-FR', 'fr', 'es-ES', 'it-IT', 'pt-PT', 'pl-PL', 'sv-SE', 'da-DK', 'no-NO'],
    en: ['de-DE', 'de', 'fr-FR', 'es-ES', 'it-IT', 'nl-NL', 'sv-SE', 'da-DK', 'no-NO', 'pl-PL', 'pt-PT']
  };

  var VOICE_EPOCH = 0;
  var VOICE_CACHE = {};

  function firstVoice(ranked, predicate) {
    for (var i = 0; i < ranked.length; i++) {
      if (predicate(ranked[i].voice)) return ranked[i].voice;
    }
    return null;
  }

  function resolveMaleVoice(lang) {
    var l = languagePrefix(lang) === 'en' ? 'en' : 'de';
    var hit = VOICE_CACHE[l];
    if (hit && hit.epoch === VOICE_EPOCH) return hit;

    var list = [];
    if (speechSupported) {
      try { list = dedupeVoices(synth.getVoices() || []); } catch (e) { list = []; }
    }
    var local = rankVoicesFromList(list, l);
    var res = { voice: null, mode: 'none', explicit: false, epoch: VOICE_EPOCH };

    // 1. The selected article language always wins. Explicit gender/name
    //    beats a neutral platform label (for example “Google Deutsch”).
    res.voice = firstVoice(local, isExplicitMaleCandidate);
    if (res.voice) {
      res.mode = 'male';
      res.explicit = true;
    } else {
      res.voice = firstVoice(local, isMaleCandidate);
      if (res.voice) res.mode = 'male';
    }

    // 2. If the local catalog has no usable voice, choose a clearly male
    //    voice in the deterministic DE/EN fallback order. Never a random
    //    female voice from another language.
    if (!res.voice) {
      var order = LANG_FALLBACK[l] || [];
      for (var oi = 0; oi < order.length && !res.voice; oi++) {
        var alt = rankVoicesFromList(list, order[oi]);
        var altMale = firstVoice(alt, isExplicitMaleCandidate);
        if (altMale) {
          res.voice = altMale;
          res.mode = 'cross';
          res.explicit = true;
        }
      }
    }

    // 3. A neutral cross-language voice is preferable to silence. It is
    //    pitch-managed, clearly marked non-explicit, and only reached when
    //    no explicit male voice exists anywhere in the preferred catalog.
    if (!res.voice) {
      var orderNeutral = LANG_FALLBACK[l] || [];
      for (var ni = 0; ni < orderNeutral.length && !res.voice; ni++) {
        var neutral = rankVoicesFromList(list, orderNeutral[ni]);
        var neutralVoice = firstVoice(neutral, isMaleCandidate);
        if (neutralVoice) {
          res.voice = neutralVoice;
          res.mode = 'cross';
          res.explicit = false;
        }
      }
    }

    // 4. Last resort: use a local female/unknown system voice only when
    //    there is no male/non-female alternative. This keeps the reader
    //    audible on restricted devices and avoids pretending it is male.
    if (!res.voice && local.length) {
      res.voice = local[0].voice;
      res.mode = 'fallback';
      res.explicit = explicitMale(res.voice);
    }

    VOICE_CACHE[l] = res;
    return res;
  }

  // Compatibility wrapper for diagnostics and first-party integrations.
  function pickMaleVoice(lang) {
    var result = resolveMaleVoice(lang);
    return result ? result.voice : null;
  }

  /* ---------- Automatische Qualitätsanpassung: Kalibrierung ---------- */
  function qualityTierForScore(score) {
    if (score >= 200) return 'studio';
    if (score >= 140) return 'premium';
    if (score >= 60) return 'standard';
    return 'basic';
  }

  function calibrateQuality() {
    // Maßgeblich ist die tatsächlich besetzte (männliche) Stimme –
    // nicht die abstrakt beste Stimme der Liste.
    var cast = resolveMaleVoice(currentLang);
    var tier = 'basic';
    if (cast && cast.voice) {
      tier = qualityTierForScore(scoreVoice(cast.voice, currentLang));
      // Ohne eindeutig männlichen Stimmbesitz (z. B. „Google Deutsch“):
      // ruhigere Regie (mehr Pausen, kürzere Bögen) für klare
      // Verständlichkeit in der abgesenkten Klangzone.
      if (!cast.explicit && tier !== 'standard' && tier !== 'basic') tier = 'standard';
    }
    var profile = QUALITY_PROFILES[tier] || QUALITY_PROFILES.standard;
    var next = {
      tier: tier,
      rate: profile.rate,
      maxChunk: profile.maxChunk,
      pauseScale: profile.pauseScale,
      pitchShift: profile.pitchShift,
      dynamic: profile.dynamic || 0
    };

    // Geräte-/Netz-Kontext: Datensparmodus, schwache CPU oder Mobilgerät
    // -> etwas kürzere Chunks & ruhigeres Tempo (weniger Abbrüche, klarer)
    var nav = win.navigator || {};
    var conn = nav.connection || nav.mozConnection || nav.webkitConnection;
    var lowPower = !!(conn && (conn.saveData || /(^|-)2g$/.test(conn.effectiveType || '')));
    var weakCpu = typeof nav.hardwareConcurrency === 'number' && nav.hardwareConcurrency > 0 && nav.hardwareConcurrency <= 2;
    var isMobile = !!(win.matchMedia && win.matchMedia('(pointer: coarse)').matches);
    if (lowPower || weakCpu) {
      next.maxChunk = Math.min(next.maxChunk, 140);
      next.rate = Math.min(next.rate, 0.93);
      next.dynamic = Math.min(0.03, (next.dynamic || 0) + 0.01);
    }
    else if (isMobile) {
      next.maxChunk = Math.min(next.maxChunk, 170);
      next.dynamic = Math.min(0.025, (next.dynamic || 0) + 0.005);
    }

    // Adaptive Herabstufung nach wiederholten Synthese-Fehlern
    if (degradeLevel > 0) {
      next.maxChunk = Math.max(110, next.maxChunk - 40 * degradeLevel);
      next.rate = Math.max(0.86, next.rate - 0.04 * degradeLevel);
      next.pauseScale = Math.min(1.5, next.pauseScale + 0.12 * degradeLevel);
      next.dynamic = Math.min(0.03, (next.dynamic || 0) + 0.008 * degradeLevel);
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
    blockquote:    { rate: 0.95, pitch: 0.95, volume: 0.96, before: 340, after: 320 },
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

  /* ---------- Automatische Sprach-Regie & Chunk-Längen ----------
     Jeder Satz wird automatisch gemessen und der Sprache zugeordnet
     (DE/EN, ohne Umschalter, wie ein zweisprachiger Hörfunk-Moderator):
     Reine englische Sätze in einem deutschen Artikel liest die
     männliche EN-Stimme, deutsche Sätze in englischen Artikeln die
     männliche DE-Stimme.

     Automatische maximale Chunk-Länge je Inhalt & Stimmenklasse:
       - kurze Sätze werden zu natürlichen Atemgruppen gebündelt
         (kein Roboter-Einzelsatz-Stakkato mehr),
       - lange Schachtelsätze werden an Nebensatz-/Komma-Grenzen
         geteilt und erhalten eine ruhigere Sprechweise,
       - die Obergrenze (quality.maxChunk) wächst/schrumpft mit der
         Stimmen-Güte und bleibt hart gedeckelt (HARD_CHUNK) unter
         der Chrome-15-Sekunden-Abbruchgrenze. */
  var MAX_CHUNK = 200;
  var HARD_CHUNK = 240;   // harte Obergrenze: ~14 s Sprechzeit, nie abgebrochen

  /* Diskursmarker (Verlagshaus-Regie v4): An diesen Konnektiven atmet
     und intoniert ein professioneller Sprecher um – ein Schnitt dort
     erzeugt natürliche Intonationsbögen statt Roboter-Fluss.
     Geschnitten wird NUR bei langen Sätzen; Mindeststücke (40 Zeichen)
     verhindern Stakkato. */
  var CONNECTIVES = {
    de: 'aber|allenfalls|allerdings|andererseits|außerdem|beispielsweise|bevor|daher|dadurch|dagegen|deshalb|deswegen|dennoch|entweder|falls|folglich|hingegen|immerhin|indem|insbesondere|jedoch|mittlerweile|nachdem|obwohl|somit|sondern|sodass|stattdessen|trotzdem|vielmehr|vor allem|während|weil|weiterhin|zudem|zuletzt|zunächst|schließlich|zumal|zum Beispiel|darüber hinaus|im Gegenteil|unter anderem',
    en: 'however|therefore|thus|hence|moreover|furthermore|nevertheless|nonetheless|besides|additionally|in addition|for example|for instance|in particular|especially|after all|as a result|meanwhile|instead|because|although|though|whereas|while|since|unless|until|before|after|yet|so that|given that|of course|above all'
  };
  var CONNECTIVE_MIN = 40;   // Mindestlänge eines Schnittstücks (keine Stakkato-Schnipsel)

  // Kompakte Stoppwort-Karten für das automatische Satz-Routing DE/EN
  var EN_SNIFF = {
    the: 1, and: 1, of: 1, to: 1, you: 1, your: 1, for: 1, is: 1, are: 1, was: 1, were: 1, be: 1,
    with: 1, that: 1, this: 1, these: 1, those: 1, it: 1, on: 1, at: 1, by: 1, from: 1, as: 1,
    not: 1, or: 1, but: 1, if: 1, then: 1, have: 1, has: 1, had: 1, will: 1, would: 1, can: 1,
    could: 1, should: 1, may: 1, our: 1, their: 1, them: 1, they: 1, we: 1, what: 1, when: 1,
    where: 1, why: 1, how: 1, who: 1, which: 1, more: 1, most: 1, only: 1, very: 1, just: 1,
    also: 1, here: 1, there: 1, all: 1, any: 1, some: 1, no: 1, yes: 1, do: 1, does: 1, did: 1,
    about: 1, into: 1, over: 1, under: 1, between: 1, through: 1, after: 1, before: 1, during: 1,
    because: 1, while: 1, against: 1, up: 1, down: 1, out: 1, off: 1, again: 1, once: 1, an: 1,
    me: 1, us: 1, him: 1, his: 1, her: 1, my: 1, every: 1, own: 1, other: 1, each: 1, both: 1,
    few: 1, first: 1, new: 1, good: 1, much: 1, than: 1, per: 1, want: 1, need: 1, know: 1
  };
  var DE_SNIFF = {
    der: 1, die: 1, das: 1, und: 1, ist: 1, sind: 1, war: 1, waren: 1, wird: 1, werden: 1,
    wurde: 1, ein: 1, eine: 1, einer: 1, einem: 1, einen: 1, nicht: 1, mit: 1, von: 1, für: 1,
    auf: 1, zu: 1, im: 1, am: 1, den: 1, dem: 1, des: 1, bei: 1, auch: 1, sich: 1, kann: 1,
    können: 1, muss: 1, müssen: 1, darf: 1, sollen: 1, haben: 1, hat: 1, hatte: 1, aber: 1,
    oder: 1, wenn: 1, weil: 1, dass: 1, wie: 1, als: 1, nach: 1, vor: 1, bis: 1, seit: 1,
    aus: 1, nur: 1, noch: 1, schon: 1, dann: 1, doch: 1, also: 1, hier: 1, jetzt: 1, über: 1,
    unter: 1, zwischen: 1, ohne: 1, gegen: 1, durch: 1, um: 1, sie: 1, wir: 1, ihr: 1, euch: 1,
    uns: 1, er: 1, es: 1, mich: 1, dich: 1, ihm: 1, ihn: 1, diese: 1, dieser: 1, dieses: 1,
    diesem: 1, diesen: 1, welche: 1, mein: 1, meine: 1, dein: 1, deine: 1, ihre: 1, kein: 1,
    keine: 1, alle: 1, allen: 1, alles: 1, viele: 1, zwei: 1, drei: 1, viel: 1, monat: 1,
    versicherung: 1, kosten: 1, vertrag: 1, beitrag: 1, jahr: 1, euro: 1, prozent: 1
  };

  // Typisch deutsche Wortendungen als morphologisches DE-Signal
  // (fängt Sätze ohne Funktionswörter: „Wer breit investiert, profitiert …“)
  var GERMAN_ENDINGS = ['ung', 'keit', 'heit', 'nis', 'schaft', 'tum', 'lich', 'ig', 'bar', 'sam', 'ieren', 'iert'];

  /* Automatische Satzsprach-Erkennung: nur bei eindeutiger Mehrheit
     wechseln (mehrere Satzglieder), damit einzelne Lehnwörter
     („Online-Banking“, „Budget“) nie einen unnötigen Sprecherwechsel
     auslösen. Deutsche Sätze werden zusätzlich über Umlaute/ß und
     typische Wortendungen erkannt (Zweisignal-Prinzip). */
  function sniffSentenceLang(sentence, baseLang) {
    var words = String(sentence || '')
      .toLowerCase()
      .replace(/[^a-zäöüß0-9'-]+/g, ' ')
      .split(' ');
    var en = 0;
    var de = 0;
    var germ = 0;
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (!w || w.length < 2) continue;
      if (EN_SNIFF[w]) en++;
      if (DE_SNIFF[w]) de++;
      if (/[äöüß]/.test(w)) germ += 2;
      if (w.length >= 5) {
        for (var e = 0; e < GERMAN_ENDINGS.length; e++) {
          if (w.indexOf(GERMAN_ENDINGS[e], w.length - GERMAN_ENDINGS[e].length) !== -1) { germ += 1; break; }
        }
      }
    }
    if (baseLang === 'de') return (en >= 3 && en > de * 2 + 1) ? 'en' : 'de';
    if (baseLang === 'en') return ((de >= 3 && de > en) || (de >= 1 && germ >= 2 && de > en)) ? 'de' : 'en';
    return baseLang;
  }

  function proseSentences(text) {
    var parts = sentences(text);
    if (!parts.length) parts = [text];
    return parts.map(function (s) {
      var emo = 'statement';
      var tail = s.slice(-1);
      if (tail === '?') emo = 'question';
      else if (tail === '!') emo = 'exclamation';
      return { s: s, emo: emo };
    });
  }

  function wordCountOf(t) {
    var w = String(t || '').trim().split(/\s+/);
    return w.length === 1 && w[0] === '' ? 0 : w.length;
  }

  function splitForSpeech(text, lang) {
    var soft = Math.max(60, (quality && quality.maxChunk) || MAX_CHUNK);
    var hard = Math.max(120, Math.min(HARD_CHUNK, soft + 60));
    var blockLang = lang === 'en' ? 'en' : 'de';
    var list = proseSentences(text);
    var groups = [];
    var cur = null;

    function flush() {
      if (cur && cur.text && cur.text.trim()) { groups.push(cur); cur = null; }
    }

    // Bündelung: kurze Sätze derselben Sprache -> eine natürliche Atemgruppe
    list.forEach(function (sn) {
      if (!sn.s) return;
      var sl = sniffSentenceLang(sn.s, blockLang);
      if (sn.emo !== 'statement') {
        // Fragen & Ausrufe sind immer eigenständige Sprecheinheiten:
        // Sie erhalten eigene Satzmelodie (Tonlage) und Pausenraum.
        flush();
        cur = { text: sn.s, lang: sl, emo: sn.emo };
        flush();
        return;
      }
      if (!cur) {
        cur = { text: sn.s, lang: sl, emo: sn.emo };
      } else if ((cur.text.length + 1 + sn.s.length) <= soft && sl === cur.lang) {
        cur.text += ' ' + sn.s;
      } else {
        flush();
        cur = { text: sn.s, lang: sl, emo: sn.emo };
      }
    });
    flush();

    /* Lange Gruppen teilen – Verlagshaus-Regie in zwei Stufen:
       1. an Diskursmarkern (Konnektiven: „weil“, „however“ …) mit
          Mindeststück-Länge, damit natürliche Intonationsbögen entstehen,
       2. anschließend an Gliederungszeichen (Komma/Semikolon/Doppelpunkt),
       3. Packen zu Atemgruppen bis zur weichen Obergrenze. */
    var out = [];
    var connRe = new RegExp('(?:^|\\s)(' + CONNECTIVES[blockLang === 'en' ? 'en' : 'de'] + ')(?=\\s)', 'gi');

    function cutAtConnectives(text) {
      var cuts = [];
      var m;
      connRe.lastIndex = 0;
      while ((m = connRe.exec(text)) !== null) {
        cuts.push(m.index + (m[0].length - m[1].length));
      }
      if (!cuts.length) return [text];
      var pieces = [];
      var start = 0;
      for (var c = 0; c < cuts.length; c++) {
        if (cuts[c] - start >= CONNECTIVE_MIN && (text.length - cuts[c]) >= CONNECTIVE_MIN) {
          pieces.push(text.slice(start, cuts[c]));
          start = cuts[c];
        }
      }
      pieces.push(text.slice(start));
      return pieces;
    }

    function commaPieces(text) {
      return text.replace(/([,;:–—])\s+/g, '$1\u0001').split('\u0001');
    }

    groups.forEach(function (g) {
      if (g.text.length <= hard) { out.push(g); return; }
      /* Konnektiv-Stücke bleiben bewusst eigene Atemgruppen (Atem +
         Intonations-Reset am Diskursmarker) – sie werden NICHT wieder
         zusammengepackt. Nur übergroße Stücke fallen in Stufe 2
         (Komma-Schnitt + Packen) und dann Stufe 3 (Wortgrenze). */
      cutAtConnectives(g.text).forEach(function (cp) {
        var piece = cp.trim();
        if (!piece) return;
        if (piece.length <= soft) {
          out.push({ text: piece, lang: g.lang, emo: g.emo });
          return;
        }
        var pieces = commaPieces(piece);
        var buf = '';
        pieces.forEach(function (p) {
          if (!p || !p.trim()) return;
          if ((buf + ' ' + p).trim().length > soft && buf) {
            out.push({ text: buf.trim(), lang: g.lang, emo: g.emo });
            buf = '';
          }
          buf = (buf ? buf + ' ' : '') + p.trim();
        });
        if (buf.trim()) out.push({ text: buf.trim(), lang: g.lang, emo: g.emo });
      });
    });

    // Notfall-Reserve: harte Wortgrenzen (nur falls ein Einzelwort-Block übrig bleibt)
    var safe = [];
    out.forEach(function (c) {
      if (c.text.length <= hard) { safe.push(c); return; }
      var words = c.text.split(' ');
      var b = '';
      words.forEach(function (w) {
        if ((b + ' ' + w).length > hard - 10 && b) {
          safe.push({ text: b.trim(), lang: c.lang, emo: c.emo });
          b = w;
        } else {
          b = (b ? b + ' ' : '') + w;
        }
      });
      if (b.trim()) safe.push({ text: b.trim(), lang: c.lang, emo: c.emo });
    });

    return safe.filter(function (c) {
      return c && c.text && /[a-zA-ZÄÖÜäöüß0-9]/.test(c.text);
    });
  }

  /* ---------- Automatische Tempo-, Pausen- & Tonlagen-Regie ----------
     Tempo:  Rolle (Überschrift, Fließtext, Tabelle …) × Stimmenklasse
             × Informationsdichte des Satzes. Zahlen, lange Komposita
             und Schachtelsätze werden automatisch ruhiger gelesen,
             kurze Alltagssätze leicht flüssiger.
     Pausen: Skalierung nach Satzzeichen, Satzlänge („Hör-Digest-Zeit“),
             Satzmelodie und Abschnittsrolle – multipliziert mit der
             automatischen Pausen-Skala der Stimmenklasse.
     Tonlage: männliche Grund-Tonlage je Rolle & Stimmenklasse plus
             Satzmelodie (Fragen steigen, Ausrufe betonen) und feiner
             Mikro-Modulation gegen Roboter-Monotonie bei einfachen
             Stimmen. Falls wider Erwarten keine männliche Stimme
             existiert, wird die Tonlage abgesenkt (Tonlagen-Korrektur). */
  function contentRateFactor(text) {
    var wc = wordCountOf(text);
    if (!wc) return 1;
    var words = String(text || '').split(/\s+/);
    var hardWords = 0;
    var digits = 0;
    var totalLen = 0;
    for (var i = 0; i < words.length; i++) {
      var w = words[i];
      if (!w) continue;
      totalLen += w.length;
      if (w.length >= 9) hardWords++;
      if (/\d/.test(w)) digits++;
    }
    var avg = totalLen / words.length;
    var f = 1.0;
    if (hardWords / words.length > 0.3) f -= 0.05;
    else if (hardWords / words.length > 0.14) f -= 0.025;
    if (avg > 8) f -= 0.03;
    else if (avg < 5.2) f += 0.02;
    if (digits >= 2) f -= 0.02;
    if (words.length <= 6 && digits === 0) f += 0.02;
    return Math.min(1.05, Math.max(0.9, f));
  }

  function effectiveRateFor(unit, profile) {
    var base = profile && profile.rate != null ? profile.rate : 1;
    var cf = contentRateFactor(unit.text);
    if (unit.emo === 'question') cf -= 0.02;
    if (unit.emo === 'exclamation') cf -= 0.01;
    // Final-Längung (Verlagshaus-Regie): der letzte Bogen eines Blocks
    // wird minimal ruhiger gesprochen – wie ein Sprecher am Absatzschluss.
    if (unit.finalChunk) cf -= 0.015;
    return Math.min(1.18, Math.max(0.5, base * (quality.rate || 1) * cf));
  }

  /* Mikro-Pausen nach Satzschluss (natürliche Atmung), automatisch
     skaliert nach Satzlänge, Satzzeichen, Rolle und Sprechtempo. */
  function pauseAfterChunk(unit, isLast, profile, effRate) {
    if (!unit || !unit.text) return profile ? (profile.after || 200) : 200;
    var tail = unit.text.slice(-1);
    var base;
    if (isLast) {
      base = profile ? (profile.after || 200) : 200;
    } else if (tail === '?') { base = 340; }
    else if (tail === '!') { base = 300; }
    else if (tail === '.' || tail === '…') { base = 250; }
    else if (tail === ':') { base = 300; }
    else if (tail === ',') { base = 140; }
    else if (tail === ';') { base = 160; }
    else { base = 180; }

    // Hör-Digest-Skala: je länger die gehörte Einheit, desto länger
    // die Verarbeitungspause (+1,5 % je Wort ab dem 7. Wort, Deckel +32 %)
    var wc = unit.words || wordCountOf(unit.text);
    base *= 1 + Math.min(0.32, Math.max(0, wc - 6) * 0.015);

    // Satzmelodie: Fragen und Ausrufe erhalten einen Moment mehr Raum
    if (unit.emo === 'question') base += 80;
    else if (unit.emo === 'exclamation') base += 50;

    // Automatische Pausen-Skala der Stimmenklasse (basic > standard)
    base *= quality.pauseScale || 1;

    // Natürliche Tempo-Kopplung: schneller gesprochen -> Pause relativ
    // kürzer, aber nie unter ~60 % der Basis-Pause
    var speed = Math.min(1.15, Math.max(0.62, 1.32 - 0.34 * (effRate || 1)));
    base *= speed;
    return Math.round(base);
  }

  /* Automatische Tonlagen-Korrektur: männliche Zone halten, Fragen
     anheben, Ausrufe betonen, Monotonie bei einfachen Stimmen brechen.
     Garantie-Kern (v4): Nur bei EINDEUTIG männlicher Stimme spricht
     die Regie in natürlicher Tonlage; geschlechtsneutrale Stimmen
     werden verlässlich in die männliche Klangzone (≤ 0.88) abgesenkt,
     der absolute Notnagel (fallback) auf ≤ 0.86. */
  function autoPitch(unit, basePitch, voiceRes) {
    var q = quality || {};
    var v = (basePitch == null ? 1 : basePitch) + (q.pitchShift || 0);
    if (unit && unit.emo === 'question') v += 0.05;
    else if (unit && unit.emo === 'exclamation') v += 0.02;
    if (unit && unit.finalChunk) v -= 0.012;   // Final-Längung: Absatzschluss klingt ruhiger
    var dyn = q.dynamic || 0;
    if (dyn > 0 && unit) v += dyn * (unit.modSign || 1);
    var mode = voiceRes ? voiceRes.mode : 'none';
    var explicit = voiceRes ? !!voiceRes.explicit : false;
    if (mode === 'fallback') v = Math.min(v - 0.02, 0.86);
    else if (mode !== 'none' && !explicit) v = Math.min(v - 0.07, 0.88);
    else if (mode === 'none') v = Math.min(v - 0.05, 0.88);
    return Math.min(1.4, Math.max(0.6, v));
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
    tableBlocks.push({ el: introEl, text: introRaw, lang: lang, type: 'table-intro' });

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

      tableBlocks.push({ el: tr, text: rowRaw, lang: lang, type: 'table-row' });
    });

    tableBlocks.push({
      el: introEl,
      text: tTexts.tableOutro.replace('{title}', title),
      lang: lang,
      type: 'table-outro'
    });

    return tableBlocks;
  }

  /* ---------- Alle vorlesbaren Blöcke im Artikel sammeln ----------
     WICHTIG (Fix 03.09.2026): Die Kurzantwort-Box („grüner Kasten“,
     layouts/single.html) und die Korrektur-Box stehen im Template VOR
     .post-content, sind also Geschwister und keine Nachfahren. Die
     Selektorenliste unten führte .ff-kurzantwort/.ff-korrektur zwar,
     suchte aber nur innerhalb von .post-content – die Boxen wurden
     deshalb nie vorgelesen (toter Code). Sie werden jetzt ausdrücklich
     in Dokumentreihenfolge vorangestellt. */
  function preContentBoxes() {
    var scope = doc.body || doc;
    if (!scope || typeof scope.querySelectorAll !== 'function') return [];
    return qsa('.ff-korrektur, .ff-kurzantwort', scope).filter(function (el) {
      if (!el.closest) return true;
      return !el.closest('.post-content, .md-content, [data-ff-skip-read], .ff-reader-toolbar');
    });
  }

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
    out.push({ el: toolbar, text: introRaw, lang: lang, type: 'intro' });

    // Redaktionelle Vorab-Boxen (Korrektur, Kurzantwort) – sie gehören
    // inhaltlich zum Artikel und müssen hörbar sein.
    preContentBoxes().forEach(function (box) {
      /* Die sichtbare Dachzeile („Kurz & knapp – die Antwort“) wird nicht
         mitgesprochen: Der redaktionelle Cue davor sagt dasselbe. Sonst
         entstünde „Kurzantwort: Kurz & knapp – die Antwort …“. */
      var probe = box.cloneNode ? box.cloneNode(true) : box;
      qsa('.ff-kurzantwort__label, .ff-kurzantwort__icon', probe).forEach(function (n) {
        if (n.parentNode) n.parentNode.removeChild(n);
      });
      var boxText = readableText(probe);
      if (boxText.length <= 5) return;
      var isKorrektur = box.classList && box.classList.contains('ff-korrektur');
      var cue = isKorrektur ? (texts.cueCorrection || texts.cueNote) : texts.cueShortAnswer;
      out.push({
        el: box,
        text: cue + ' ' + boxText,
        lang: lang,
        type: isKorrektur ? 'warning' : 'callout'
      });
    });

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
        var boxTexts = I18N[elLang] || texts;
        var cue = el.classList.contains('ff-kurzantwort') ? boxTexts.cueShortAnswer
          : el.classList.contains('ff-einspar-box') ? boxTexts.cueSaving
          : el.classList.contains('ff-tarif-card') ? boxTexts.cueTariff
          : isWarn ? boxTexts.cueWarning : boxTexts.cueNote;
        out.push({
          el: el,
          text: cue + ' ' + boxText,
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
          var listTexts = I18N[elLang] || texts;
          speakText = listTexts.listItemNum.replace('{n}', idx) + ' ' + text;
        }
      }
      /* Überschriften enden im Satzbaum meist ohne Punkt – gesprochen
         brauchen sie einen, sonst klingt die Anmoderation abgehackt.
         Eine Frage bleibt aber eine Frage: Wird das Fragezeichen zum
         Punkt, spricht die Stimme sie als Feststellung („Kann mir das
         Gas abgestellt werden." statt „…werden?"). Genau so stehen die
         FAQ-Überschriften in den Artikeln. */
      if (/^H[234]$/.test(el.tagName)) {
        var heading = text.replace(/[\s?!.…]+$/, '');
        speakText = heading + (/\?\s*$/.test(text) ? '?' : '.');
      }

      out.push({ el: el, text: speakText, lang: elLang, type: type });
    });

    out.push({ el: toolbar, text: texts.outroLine, lang: lang, type: 'outro' });

    return out.filter(function (b) { return b.text && b.text.length > 1; });
  }

  /* ---------- Zeitachse aus Blöcken + Chunks --------------------------
     Language routing must happen before pronunciation normalization. The
     previous implementation normalized every block in its DOM language,
     then tried to detect English afterwards; this made an English sentence
     inherit German currency/date rules and the wrong voice. */
  function normalizeTimelineChunks(rawChunks) {
    var out = [];
    (rawChunks || []).forEach(function (c) {
      var normalized = speechNormalize(c.text, c.lang);
      if (!normalized) return;
      if (normalized.length <= HARD_CHUNK) {
        out.push({ text: normalized, lang: c.lang, emo: c.emo });
        return;
      }

      // Expanding abbreviations (for example “Berufsunfähigkeits-…”) can
      // make a chunk longer than the pre-normalization limit. Split once
      // more at word boundaries so no browser receives a long utterance.
      var words = normalized.split(/\s+/);
      var buf = '';
      words.forEach(function (word) {
        var candidate = (buf ? buf + ' ' : '') + word;
        if (buf && candidate.length > HARD_CHUNK - 10) {
          out.push({ text: buf.trim(), lang: c.lang, emo: c.emo });
          buf = word;
        } else {
          buf = candidate;
        }
      });
      if (buf.trim()) out.push({ text: buf.trim(), lang: c.lang, emo: c.emo });
    });
    return out;
  }

  function buildTimeline() {
    timeline = [];
    totalChars = 0;
    blocks.forEach(function (b, bi) {
      var chunks = normalizeTimelineChunks(splitForSpeech(b.text, b.lang));
      var profile = prosodyFor(b.type);
      chunks.forEach(function (c, ci) {
        var unit = {
          block: b,
          blockIndex: bi,
          text: c.text,
          lang: c.lang,
          emo: c.emo,
          words: c.words || wordCountOf(c.text),
          type: b.type,
          profile: profile,
          effRate: 1,
          modSign: 1,
          finalChunk: ci === chunks.length - 1,
          before: ci === 0 ? profile.before : 0,
          after: 0
        };
        unit.effRate = effectiveRateFor(unit, profile);
        unit.after = pauseAfterChunk(unit, ci === chunks.length - 1, profile, unit.effRate);
        unit.modSign = timeline.length % 2 === 0 ? 1 : -1;
        totalChars += unit.text.length;
        timeline.push(unit);
      });
    });
  }

  function estimateRemaining() {
    if (!remainEl) return;
    var rest = 0;
    var units = 0;
    var rateSum = 0;
    for (var i = cursor; i < timeline.length; i++) {
      rest += timeline[i].text.length;
      rateSum += timeline[i].effRate || 1;
      units++;
    }
    if (!units) { remainEl.textContent = ''; return; }
    var eff = rateSum / units;
    // ~1000 Zeichen/Minute bei Rate 1.0 (deutsche Nachrichtensprache)
    // zzgl. Regie-/Atempausen (~0,5 s je Einheit)
    var minutes = rest / (1000 * Math.max(0.4, eff)) + units * 0.008;
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

  var lastEffRate = 1;
  var liveUtterance = null;
  var playbackRun = 0;       // invalidates callbacks from canceled utterances
  var retryCounts = {};
  var voicePollId = null;
  var lastSpeechStartedAt = 0;

  // Android pauset/resumed die Synthese unzuverlässig. Dort wird beim
  // Pausieren abgebrochen und beim Fortsetzen die aktuelle Einheit neu
  // gesprochen. Auf Desktop/Safari bleibt die native Pause erhalten.
  var IS_ANDROID = !!(win.navigator && /android/i.test(win.navigator.userAgent || ''));

  function stopVoicePolling() {
    if (voicePollId) { clearInterval(voicePollId); voicePollId = null; }
  }

  function retryCurrentUnit(index, run, unit) {
    if (!reading || !playing || run !== playbackRun) return;
    var attempts = retryCounts[index] || 0;
    if (attempts < 2) {
      retryCounts[index] = attempts + 1;
      if (attempts === 1 && degradeLevel < 2) {
        degradeLevel += 1;
        calibrateQuality();
      }
      setTimeout(function () {
        if (reading && playing && run === playbackRun) speakUnit(index, true);
      }, 140 * (attempts + 1));
      return;
    }

    // A broken platform voice must not stop the whole article. Skip only
    // the failed unit after two retries and make the failure accessible.
    retryCounts[index] = 0;
    if (statusEl) statusEl.textContent = texts.speechError;
    spokenChars += unit && unit.text ? unit.text.length : 0;
    speakUnit(index + 1, false);
  }

  function speakUnit(index, isInitial) {
    if (!reading || !speechSupported) return;
    clearPauseTimer();
    if (index >= timeline.length) { endReading(true); return; }
    cursor = index;
    nextIndex = index;
    var unit = timeline[index];
    if (!unit || !unit.text) {
      speakUnit(index + 1, isInitial);
      return;
    }
    var run = playbackRun;
    highlight(unit);
    estimateRemaining();
    storeSet(STORE_POS, String(index));

    var start = function () {
      if (!reading || !playing || run !== playbackRun) return;

      // Recalculate after an adaptive retry. This keeps a temporarily
      // unstable browser on shorter, slower utterances without rebuilding
      // the timeline and losing the reader's position.
      unit.effRate = effectiveRateFor(unit, unit.profile || prosodyFor('p'));
      unit.after = pauseAfterChunk(unit, !!unit.finalChunk, unit.profile || prosodyFor('p'), unit.effRate);
      var voiceRes = resolveMaleVoice(unit.lang);
      var u = new win.SpeechSynthesisUtterance(unit.text);

      // Always bind locale and voice together. Leaving either value to the
      // platform default was the source of the “silent/wrong voice” report.
      if (voiceRes && voiceRes.voice) {
        u.voice = voiceRes.voice;
        u.lang = voiceRes.voice.lang || (unit.lang === 'en' ? 'en-US' : 'de-DE');
        if (voiceRes.explicit) setStatus(texts.voiceActive);
        else setStatus(texts.voiceFallback);
      } else {
        // No browser can synthesize a voice that it does not expose. Still
        // start synchronously with the requested locale; the low pitch is a
        // safe audible fallback and a later voiceschanged event upgrades all
        // subsequent units to the selected male voice.
        u.lang = unit.lang === 'en' ? 'en-US' : 'de-DE';
      }

      var p = unit.profile || prosodyFor('p');
      u.rate = Math.min(1.25, Math.max(0.5, unit.effRate || 1));
      u.pitch = autoPitch(unit, p.pitch, voiceRes);
      u.volume = Math.max(0.1, Math.min(1.0, p.volume != null ? p.volume : 1.0));

      var started = false;
      var settled = false;
      var watchdogTimer = null;
      function clearStartWatchdog() {
        if (watchdogTimer) { clearTimeout(watchdogTimer); watchdogTimer = null; }
      }

      u.onboundary = function (e) {
        if (!reading || !playing || run !== playbackRun || !progressBar || !totalChars) return;
        if (e && typeof e.charIndex === 'number' && e.charIndex >= 0) {
          var pct = Math.min(100, ((spokenChars + e.charIndex) / totalChars) * 100);
          progressBar.style.width = pct.toFixed(1) + '%';
        }
      };

      // Keep a strong reference. Chromium has historically garbage-collected
      // unreferenced utterances before onend, which made long articles stop.
      liveUtterance = u;
      activeUtterances.push(u);
      win.__ff_active_utterance = u;

      function cleanupUtterance() {
        clearStartWatchdog();
        var pos = activeUtterances.indexOf(u);
        if (pos !== -1) activeUtterances.splice(pos, 1);
        if (liveUtterance === u) liveUtterance = null;
        if (win.__ff_active_utterance === u) win.__ff_active_utterance = null;
      }

      u.onstart = function () {
        started = true;
        lastSpeechStartedAt = Date.now();
        clearStartWatchdog();
      };

      u.onend = function () {
        cleanupUtterance();
        if (settled) return;
        settled = true;
        if (!reading || !playing || run !== playbackRun) return;
        if (!started) {
          retryCurrentUnit(index, run, unit);
          return;
        }
        retryCounts[index] = 0;
        errorStreak = 0;
        lastEffRate = unit.effRate || 1;
        spokenChars += unit.text.length;
        /* Fix 03.09.2026: Die nächste Einheit wird VORGEMERKT, solange die
           Atempause läuft. Früher zeigte `cursor` weiterhin auf die bereits
           gesprochene Einheit – ein Fortsetzen (oder die Keep-Alive-Wache)
           in dieser Lücke sprach denselben Satz ein zweites Mal. */
        nextIndex = index + 1;
        clearPauseTimer();
        pauseTimer = setTimeout(function () {
          if (reading && playing && run === playbackRun) speakUnit(index + 1, false);
        }, unit.after);
      };

      u.onerror = function (e) {
        cleanupUtterance();
        if (settled) return;
        settled = true;
        if (!reading || run !== playbackRun) return;
        if (e && (e.error === 'interrupted' || e.error === 'canceled')) {
          // A user pause/stop changes playing or playbackRun first. If the
          // engine is still supposed to be playing, an unexpected cancel is
          // a recoverable queue interruption, not a reason to go silent.
          if (playing) retryCurrentUnit(index, run, unit);
          return;
        }
        errorStreak += 1;
        retryCurrentUnit(index, run, unit);
      };

      // Detect engines that accept speak() but never emit onstart. The old
      // watchdog only resumed a paused queue and therefore missed exactly
      // this silent failure mode.
      watchdogTimer = setTimeout(function () {
        if (reading && playing && run === playbackRun && !started) {
          try { synth.cancel(); } catch (e) {}
          retryCurrentUnit(index, run, unit);
        } else {
          clearStartWatchdog();
        }
      }, 1200);

      try {
        if (synth.paused) synth.resume();
        synth.speak(u);
      } catch (err) {
        cleanupUtterance();
        retryCurrentUnit(index, run, unit);
      }
    };

    // Initial speech is deliberately synchronous in the click call stack.
    // Subsequent units receive their editorial breathing pause.
    if (isInitial) {
      start();
    } else {
      var lead = Math.round(((unit.before || 0) * (quality.pauseScale || 1)) / Math.max(0.6, lastEffRate || quality.rate || 1));
      if (lead > 0) {
        pauseTimer = setTimeout(function () {
          if (reading && playing && run === playbackRun) start();
        }, lead);
      } else {
        start();
      }
    }
  }

  function jumpTo(index) {
    if (!reading || !timeline.length) return;
    unlockAudioEngine();
    index = Math.max(0, Math.min(timeline.length - 1, index));
    nextIndex = index;
    spokenChars = 0;
    for (var i = 0; i < index; i++) spokenChars += timeline[i].text.length;
    clearPauseTimer();
    stopVoicePolling();
    playbackRun += 1;
    retryCounts = {};
    try {
      synth.cancel();
      synth.resume();
    } catch (e) {}
    playing = true;
    setListenState('playing');
    speakUnit(index, true);
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

  // Voice-Kataloge sind in Chromium, Safari und Android LAZY:
  // getVoices() ist beim ersten Klick oft noch leer und füllt sich erst
  // nach voiceschanged. Die alte v4-Logik wartete mit setTimeout – verlor
  // dabei aber das User-Activation-Token und erzeugte STUMMHEIT.
  // High-End v5: GARANTIERT männliche Stimme OHNE STUMMHEIT
  //  - Sofort synchron prüfen: wenn Katalog da → sofort männlich sprechen
  //  - Wenn Katalog leer → SOFORT synchron mit bestem verfügbaren
  //    Male-Zone-Fallback sprechen (hörbar + männliche Klangzone), und
  //    parallel im Hintergrund auf den echten männlichen Katalog warten.
  //    Sobald er da ist, werden alle FOLGE-Sätze automatisch mit der
  //    echten männlichen Studio-Stimme gesprochen (nahtloses Upgrade).
  //  - Zeigt „wird geladen“ nur kurz, blockiert aber niemals den Ton.
  function speakWhenVoiceReady(index) {
    var desired = timeline[index] && timeline[index].lang || currentLang;
    var resolved = resolveMaleVoice(desired);
    if (resolved && resolved.voice) {
      speakUnit(index, true);
      return;
    }

    // A lazy catalog must never delay the first speak() call. Waiting for
    // voices here was the original user-visible silence bug. Start now with
    // the requested locale; once voiceschanged/getVoices supplies a male
    // voice, only the next unit is upgraded (the current utterance cannot be
    // changed safely while speaking).
    setStatus(texts.voiceLoading);
    speakUnit(index, true);
    stopVoicePolling();
    var attempts = 0;
    voicePollId = setInterval(function () {
      if (!reading || !playing) { stopVoicePolling(); return; }
      var voices = [];
      try { voices = synth && synth.getVoices ? (synth.getVoices() || []) : []; } catch (e) {}
      if (voices.length) {
        stopVoicePolling();
        refreshVoices();
        if (resolveMaleVoice(desired).voice) setStatus(texts.voiceActive);
      } else if (++attempts >= 40) {
        stopVoicePolling();
        setStatus(texts.voiceFallback);
      }
    }, 150);
  }

  function startReading(fromIndex) {
    if (!speechSupported) { setStatus(texts.unsupported); return; }
    unlockAudioEngine();
    currentLang = detectArticleLanguage();
    texts = I18N[currentLang] || I18N.de;
    toolbar.setAttribute('aria-label', currentLang === 'en'
      ? 'Reading aids: listen and summary' : 'Lesehilfen: Vorlesen und Kurzfassung');
    if (listenLabel) listenLabel.textContent = texts.listen;
    if (listenBtn) listenBtn.setAttribute('aria-label', hasExplicitMaleVoice() ? texts.listenAria : (texts.listenAriaNeutral || texts.listenAria));
    if (summaryLabel) summaryLabel.textContent = texts.summaryBtn;
    if (summaryBtn) summaryBtn.setAttribute('aria-label', texts.summaryAria);
    errorStreak = 0;
    degradeLevel = 0;
    retryCounts = {};
    playbackRun += 1;
    stopVoicePolling();
    try {
      if (synth.paused) synth.resume();
      synth.cancel();
      synth.resume();
    } catch (e) {}

    // Calibrate after the catalog has been refreshed and before building the
    // timeline, so chunk length/rate match the voice actually in use.
    calibrateQuality();
    lastEffRate = quality.rate || 1;
    if (speechSupported) { resolveMaleVoice('de'); resolveMaleVoice('en'); }

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
    nextIndex = startIdx;
    setListenState('playing');
    setStatus(startIdx > 0 ? texts.resumedPos : texts.started);
    setupMediaSession();
    startKeepAlive();
    speakWhenVoiceReady(startIdx);
  }

  function pauseReading() {
    if (!reading) return;
    playing = false;
    clearPauseTimer();
    stopVoicePolling();
    if (IS_ANDROID) playbackRun += 1; // cancel callbacks from the old utterance
    if (speechSupported) {
      if (IS_ANDROID) { try { synth.cancel(); } catch (e) {} }
      else { try { synth.pause(); } catch (e) {} }
    }
    liveUtterance = null;
    setListenState('paused');
    setStatus(texts.paused);
  }

  function resumeReading() {
    if (!reading) return;
    unlockAudioEngine();
    playing = true;
    setListenState('playing');
    setStatus(texts.resumed);
    if (!speechSupported) return;
    if (IS_ANDROID) {
      speakUnit(Math.min(nextIndex, timeline.length - 1), true); // pause is implemented as cancel on Android
      return;
    }
    try {
      if (synth.paused) synth.resume();
    } catch (e) {}
    // Safari can report a resumed queue without producing audio. Retry the
    // pending unit only when the native queue is genuinely empty.
    setTimeout(function () {
      if (reading && playing && synth && !synth.speaking && !synth.pending) {
        speakUnit(Math.min(nextIndex, timeline.length - 1), true);
      }
    }, 320);
  }

  function endReading(announce) {
    reading = false;
    playing = false;
    playbackRun += 1;
    liveUtterance = null;
    activeUtterances.length = 0;
    win.__ff_active_utterance = null;
    clearPauseTimer();
    stopVoicePolling();
    stopKeepAlive();
    if (speechSupported) {
      try {
        synth.cancel();
        synth.resume();
      } catch (e) {}
    }
    clearHighlight();
    setListenState('idle');
    storeDel(STORE_POS);
    if (announce) setStatus(texts.finished);
  }

  function startKeepAlive() {
    stopKeepAlive();
    if (!speechSupported) return;
    // Do not pause/resume live speech every few seconds: that creates an
    // audible click and resets speech on several Safari/Android versions.
    // Short utterances plus this queue watchdog are more reliable.
    keepAliveId = setInterval(function () {
      if (!reading || !playing) return;
      try {
        if (synth.paused) synth.resume();
        if (!synth.speaking && !synth.pending && !pauseTimer &&
            Date.now() - lastSpeechStartedAt > 900) {
          speakUnit(Math.min(nextIndex, timeline.length - 1), true);
        }
      } catch (e) {}
    }, 5000);
  }

  function stopKeepAlive() { if (keepAliveId) { clearInterval(keepAliveId); keepAliveId = null; } }

  /* ============================================================
     1b) FIRST-PARTY-AUDIOFASSUNG — die Garantie-Stufe
     ------------------------------------------------------------
     Die Web Speech API kann eine männliche Stimme NICHT garantieren:
     Es gibt kein Geschlechts-Merkmal im Standard, Chrome/Android mit
     Google-TTS liefert für Deutsch genau eine Stimme, iOS Safari
     blendet installierte Premium-Stimmen aus, Firefox für Android
     implementiert die Synthese nur eingeschränkt.

     Liegt deshalb eine serverseitig gerenderte Fassung unter
     /audio/<slug>.mp3, hat sie VORRANG: HTML5-<audio> läuft auf
     iPhone, iPad, Mac, Android und PC in Chrome, Firefox, Safari,
     Edge und Samsung Internet gleich — ohne Stimmenbibliothek des
     Betriebssystems, offline-cachebar, immer dieselbe männliche
     Stimme. Fehlt die Datei, greift automatisch die Web-Speech-Stufe.

     Der Sprechtext der MP3 stammt aus derselben Pipeline wie der
     Browser-Reader (Export-Hook am Dateiende), Audio und Vorlesen
     können also nicht auseinanderlaufen. Die Zeitkarte
     (data/audio/<slug>.timemap.json) liefert die Abschnittssprünge.
  ============================================================ */
  var audioEl = null;
  var audioMap = null;
  var audioActive = false;
  var audioTimeline = [];
  var audioRafId = null;

  function audioSupported() {
    return !!(cfg && cfg.audio && win.HTMLAudioElement);
  }

  function formatClock(sec) {
    if (!isFinite(sec) || sec < 0) sec = 0;
    var m = Math.floor(sec / 60);
    var s = Math.round(sec % 60);
    if (s === 60) { m += 1; s = 0; }
    return m + ':' + String(s).padStart(2, '0');
  }

  function audioUnitAt(time) {
    var starts = (audioMap && audioMap.unitStart) || [];
    var found = 0;
    for (var i = 0; i < starts.length; i++) {
      if (starts[i] == null) continue;
      if (starts[i] <= time + 0.05) found = i; else break;
    }
    return found;
  }

  function audioSync() {
    if (!audioEl || !audioActive) return;
    var t = audioEl.currentTime || 0;
    var dur = audioEl.duration || (audioMap && audioMap.durationSeconds) || 0;
    if (progressBar && dur) {
      progressBar.style.width = Math.min(100, (t / dur) * 100).toFixed(2) + '%';
    }
    if (remainEl) {
      var left = dur - t;
      remainEl.textContent = left > 1 ? 'noch ' + formatClock(left) : '';
    }
    if (audioTimeline.length) {
      var idx = audioUnitAt(t);
      var unit = audioTimeline[idx];
      /* Timeline-Einheiten verweisen per blockIndex auf blocks[] – ein
         unit.block gibt es nicht. Über den Index auflösen, sonst bleibt
         die Live-Markierung in der Audiostufe stumm. */
      var block = unit ? blocks[unit.blockIndex] : null;
      var el = block ? block.el : null;
      if (el && el !== toolbar) {
        blocks.forEach(function (b) {
          if (b.el && b.el !== el) b.el.classList.remove('ff-reader-active');
        });
        el.classList.add('ff-reader-active');
        if (!reducedMotion && !audioScrolledRecently(el)) {
          scrollTo(el, { block: 'center', behavior: 'smooth' });
        }
      }
    }
    audioRafId = win.requestAnimationFrame ? win.requestAnimationFrame(audioSync) : null;
  }

  /* Nicht bei jedem Frame neu scrollen: ein Abschnitt bleibt so lange
     stehen, bis der nächste drankommt. */
  var lastScrolledEl = null;
  function audioScrolledRecently(el) {
    if (el === lastScrolledEl) return true;
    lastScrolledEl = el;
    return false;
  }

  function audioLoadMap(cb) {
    if (!cfg.audioMap) { cb(null); return; }
    if (audioMap) { cb(audioMap); return; }
    try {
      var xhr = new win.XMLHttpRequest();
      xhr.open('GET', cfg.audioMap, true);
      xhr.onreadystatechange = function () {
        if (xhr.readyState !== 4) return;
        if (xhr.status >= 200 && xhr.status < 300) {
          try { audioMap = JSON.parse(xhr.responseText); } catch (e) { audioMap = null; }
        }
        cb(audioMap);
      };
      xhr.onerror = function () { cb(null); };
      xhr.send();
    } catch (e) { cb(null); }
  }

  function audioBuildTimeline() {
    currentLang = detectArticleLanguage();
    texts = I18N[currentLang] || I18N.de;
    blocks = collectBlocks();
    buildTimeline();
    audioTimeline = timeline.slice();
    return audioTimeline.length > 0;
  }

  function audioStart() {
    if (!audioEl) {
      audioEl = doc.createElement('audio');
      audioEl.preload = 'auto';
      audioEl.setAttribute('playsinline', '');
      audioEl.setAttribute('data-ff-reader-audio', '');
      doc.body.appendChild(audioEl);

      /* Wichtig: Media-Events können verzögert eintreffen (asynchrone
         play()-Zusagen, gepufferte Quellen). Nach einem Stopp dürfen sie
         die Toolbar nicht zurück auf „läuft" kippen – deshalb prüft jeder
         Handler zuerst, ob die Audiostufe überhaupt noch aktiv ist. */
      audioEl.addEventListener('play', function () {
        if (!audioActive) return;
        playing = true;
        setListenState('playing');
        setStatus(texts.audioPlaying || texts.started);
        if (!audioRafId && win.requestAnimationFrame) audioRafId = win.requestAnimationFrame(audioSync);
      });
      audioEl.addEventListener('pause', function () {
        if (!audioActive) return;
        playing = false;
        setListenState('paused');
        setStatus(texts.paused);
        if (audioRafId && win.cancelAnimationFrame) { win.cancelAnimationFrame(audioRafId); audioRafId = null; }
      });
      audioEl.addEventListener('ended', function () {
        if (!audioActive) return;
        audioStop(true);
      });
      audioEl.addEventListener('error', function () {
        /* Defekte oder noch nicht gerenderte Datei: ehrlich melden und
           automatisch auf die Web-Speech-Stufe zurückfallen. */
        audioActive = false;
        setStatus(texts.audioError || texts.speechError);
        startReading(0);
      });
      audioEl.addEventListener('timeupdate', function () {
        if (!audioActive) return;
        try { storeSet(STORE_AUDIO_POS, String(Math.floor(audioEl.currentTime))); } catch (e) {}
      });
    }

    audioActive = true;
    if (!audioBuildTimeline()) { setStatus(texts.noText); audioActive = false; return; }

    audioEl.src = cfg.audio;
    var saved = parseInt(storeGet(STORE_AUDIO_POS) || '0', 10);
    reading = true;
    playing = true;
    setListenState('playing');
    setStatus(texts.audioLoading || texts.voiceLoading);

    audioLoadMap(function (map) {
      audioMap = map;
      var startAt = saved > 5 && (!map || saved < map.durationSeconds - 5) ? saved : 0;
      var begin = function () {
        try { audioEl.currentTime = startAt; } catch (e) {}
        setStatus(startAt > 0 ? texts.resumedPos : (texts.audioReady || texts.voiceActive));
        var p = audioEl.play();
        if (p && typeof p.catch === 'function') {
          p.catch(function () { setStatus(texts.audioError || texts.speechError); });
        }
      };
      if (audioEl.readyState >= 1) begin();
      else audioEl.addEventListener('loadedmetadata', begin, { once: true });
    });

    if (win.navigator && win.navigator.mediaSession) {
      try {
        win.navigator.mediaSession.metadata = new win.MediaMetadata({
          title: stripMd(cfg.title || doc.title || ''),
          artist: texts.mediaArtist,
          album: cfg.siteName || 'FranksFinanzcheck'
        });
      } catch (e) {}
    }
  }

  function audioPause() {
    if (!audioEl) return;
    playing = false;
    try { audioEl.pause(); } catch (e) {}
    setListenState('paused');
    setStatus(texts.paused);
  }

  function audioResume() {
    if (!audioEl) return;
    playing = true;
    setListenState('playing');
    var p = audioEl.play();
    if (p && typeof p.catch === 'function') p.catch(function () { setStatus(texts.audioError || texts.speechError); });
  }

  function audioStop(announce) {
    audioActive = false;
    reading = false;
    playing = false;
    if (audioRafId && win.cancelAnimationFrame) { win.cancelAnimationFrame(audioRafId); audioRafId = null; }
    if (audioEl) {
      try { audioEl.pause(); audioEl.removeAttribute('src'); audioEl.load(); } catch (e) {}
    }
    storeDel(STORE_AUDIO_POS);
    lastScrolledEl = null;
    clearHighlight();
    setListenState('idle');
    if (announce) setStatus(texts.finished);
  }

  function audioJump(delta) {
    if (!audioEl || !audioMap || !audioMap.unitStart) return;
    var current = audioUnitAt(audioEl.currentTime || 0);
    var target = Math.max(0, Math.min(audioTimeline.length - 1, current + delta));
    /* Auf die nächste Abschnittsgrenze springen, nicht nur eine Einheit. */
    if (delta > 0) {
      var curBlock = audioTimeline[current] ? audioTimeline[current].blockIndex : 0;
      for (var i = current + 1; i < audioTimeline.length; i++) {
        if (audioTimeline[i].blockIndex !== curBlock) { target = i; break; }
      }
    } else {
      var curBlockBack = audioTimeline[current] ? audioTimeline[current].blockIndex : 0;
      for (var j = current - 1; j >= 0; j--) {
        if (audioTimeline[j].blockIndex !== curBlockBack) { target = j; break; }
      }
    }
    var at = audioMap.unitStart[target];
    if (at == null) return;
    try { audioEl.currentTime = Math.max(0, at - 0.2); } catch (e) {}
  }

  var STORE_AUDIO_POS = 'ff-reader:audio:' + (win.location ? win.location.pathname : '');

  /* ---------- Bedienelemente ---------- */
  listenBtn.addEventListener('click', function () {
    unlockAudioEngine();
    if (audioSupported()) {
      if (!audioActive) audioStart();
      else if (playing) audioPause();
      else audioResume();
      return;
    }
    if (!reading) {
      var saved = parseInt(storeGet(STORE_POS) || '0', 10);
      startReading(saved > 0 ? saved : 0);
    } else if (playing) {
      pauseReading();
    } else {
      resumeReading();
    }
  });

  if (stopBtn) stopBtn.addEventListener('click', function () { if (audioActive) audioStop(true); else endReading(true); });
  if (prevBtn) prevBtn.addEventListener('click', function () { if (audioActive) audioJump(-1); else jumpBlock(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function () { if (audioActive) audioJump(1); else jumpBlock(1); });

  // Klick-to-Listen: an beliebiger Stelle einsteigen (auch im Ruhezustand)
  var contentContainer = doc.querySelector('.post-content') || doc.querySelector('.md-content');
  if (contentContainer) {
    contentContainer.addEventListener('dblclick', function (e) {
      var target = e.target.closest('tr, p, h2, h3, h4, li, blockquote, .ff-tarif-card, .ff-einspar-box, .ff-kurzantwort, .callout');
      if (!target) return;
      unlockAudioEngine();
      if (!reading) { startReading(0); }
      for (var i = 0; i < timeline.length; i++) {
        if (timeline[i].block.el === target || (timeline[i].block.el && timeline[i].block.el.contains(target))) { jumpTo(i); return; }
      }
    });
    contentContainer.addEventListener('click', function (e) {
      if (!reading) return;
      var target = e.target.closest('tr, p, h2, h3, h4, li, blockquote, .ff-tarif-card, .ff-einspar-box, .ff-kurzantwort, .callout');
      if (!target || e.target.closest('a, button, input, select, textarea')) return;
      /* Fix 03.09.2026: Text markieren und kopieren darf die Wiedergabe
         nicht an eine andere Stelle springen lassen. Eine laufende
         Auswahl wird deshalb respektiert – der Sprung erfolgt nur bei
         einem echten, kollabierten Klick. */
      try {
        var sel = win.getSelection && win.getSelection();
        if (sel && !sel.isCollapsed && String(sel.toString() || '').length > 0) return;
      } catch (err) {}
      unlockAudioEngine();
      for (var i = 0; i < timeline.length; i++) {
        if (timeline[i].block.el === target || (timeline[i].block.el && timeline[i].block.el.contains(target))) { jumpTo(i); return; }
      }
    });
  }

  /* ---------- Stimmen-Initialisierung & Auto-Kalibrierung ----------
     Bewusst ohne Tastatur-Kurzbefehle: Bedienung erfolgt ausschließlich
     über die sichtbaren, barrierefreien Schaltflächen (Tab + Enter/Leertaste). */
  var voiceSignature = '';
  function readVoiceCatalog() {
    if (!speechSupported || !synth || typeof synth.getVoices !== 'function') return [];
    try { return dedupeVoices(synth.getVoices() || []); } catch (e) { return []; }
  }

  /* Ehrliche Stimmen-Kennzeichnung (Fix 03.09.2026).
     Die Web Speech API kennt kein Geschlechts-Merkmal im Standard. Ob eine
     männliche Stimme existiert, entscheidet allein das Betriebssystem:
     macOS/Windows liefern männliche DE-Stimmen, Chrome auf Android mit
     Google-TTS nur „Google Deutsch“, iOS Safari blendet die Premium-Stimmen
     aus. Der Button verspricht deshalb nur dann eine männliche Stimme, wenn
     auf DIESEM Gerät tatsächlich eine gefunden wurde – sonst benennt er
     neutral die Gerätstimme. Barrierefreiheit heißt hier: nichts versprechen,
     was das Gerät nicht einlösen kann. */
  function hasExplicitMaleVoice() {
    if (!speechSupported) return false;
    try { return !!resolveMaleVoice(currentLang).explicit; } catch (e) { return false; }
  }

  function syncVoiceLabel() {
    if (!listenBtn) return;
    var male = hasExplicitMaleVoice();
    var aria = male ? texts.listenAria : (texts.listenAriaNeutral || texts.listenAria);
    if (!reading && listenBtn.setAttribute) listenBtn.setAttribute('aria-label', aria);
    if (listenBtn.setAttribute) listenBtn.setAttribute('data-ff-voice', male ? 'male' : 'device');
    if (!listenBtn.setAttribute) return;
    if (male) { if (listenBtn.removeAttribute) listenBtn.removeAttribute('title'); }
    else listenBtn.setAttribute('title', texts.voiceFallback);
  }

  function refreshVoices() {
    var list = readVoiceCatalog();
    var signature = list.map(function (v) {
      return voiceLanguage(v) + '|' + String(v.name || '') + '|' + String(v.voiceURI || '') + '|' + reportedGender(v);
    }).join('||');
    if (signature !== voiceSignature) {
      voiceSignature = signature;
      VOICE_EPOCH += 1;
      VOICE_CACHE = {};
    }
    calibrateQuality();
    syncVoiceLabel();
  }

  if (speechSupported) {
    refreshVoices();
    if (typeof synth.addEventListener === 'function') {
      synth.addEventListener('voiceschanged', refreshVoices);
    } else if ('onvoiceschanged' in synth) {
      synth.onvoiceschanged = refreshVoices;
    }

    // Pre-warm without repeatedly invalidating the cache. A voice catalog is
    // often populated asynchronously on Chromium, Safari and Android.
    (function preWarmVoices() {
      var attempts = 0;
      var preWarmId = setInterval(function () {
        attempts += 1;
        if (readVoiceCatalog().length) {
          refreshVoices();
          clearInterval(preWarmId);
        } else if (attempts >= 20) {
          clearInterval(preWarmId);
        }
      }, 150);
    })();
  } else if (toolbar.classList) {
    toolbar.classList.add('ff-reader-toolbar--unsupported');
    listenBtn.setAttribute('aria-disabled', 'true');
    setStatus(texts.unsupported);
  }

  // Bei Tab-Wechsel sauber pausieren, statt zu stottern
  doc.addEventListener('visibilitychange', function () {
    if (doc.hidden && reading && playing) pauseReading();
  });

  win.addEventListener('pagehide', function () { if (reading) endReading(false); });
  win.addEventListener('beforeunload', function () { if (reading) { try { synth.cancel(); } catch (e) {} } });

  /* ============================================================
     2) KURZFASSUNG – Verlagshaus-Highend v4 (Capital / WiWo / ZEIT)
     ------------------------------------------------------------
     Die vollständige Kurzfassung wie in großen Verlagshäusern –
     redaktionell strukturiert, automatisch erzeugt, ohne Tracking:

       · Kurzantwort        – „Das Wichtigste in 30 Sekunden“
                              (Frontmatter `kurzantwort`, sonst die
                              inhaltlich stärkste Einstiegspassage)
       · Kernaussagen       – 3–5 prägnante Bullets, redaktionell
                              gerankt (Zahlen, Spar-/Warn-Signale,
                              Faustregeln, Tipps), dublettenfrei und
                              in Lesereihenfolge
       · Zahlen             – „Auf einen Blick“: Big-Number-Karten
                              (Wert + redaktionelles Label) aus dem
                              Fließtext extrahiert
       · In diesem Artikel  – interaktives Inhaltsverzeichnis mit
                              Sprungmarken + Abschnitts-Teaser
       · Tabellen           – kompakte Übersichts-Highlights mit
                              Sprungmarke zur Originaltabelle
       · Byline/Meta        – Lesezeit, Wortzahl, Abschnitte, Autor,
                              Stand (Verlagshaus-Byline)
       · Kopieren           – sauber formatierte Klartext-Kurzfassung
       · Barrierefreiheit   – Fokus-Falle, Esc, Scroll-Sperre,
                              aria-verdrahtet (WCAG 2.2 / BITV)

     Alle Extraktoren sind abkürzungs- und zahlenfest (z. B., d. h.,
     ca., 1.250 €, 20–30 %) und sprachbewusst (DE & EN).
  ============================================================ */

  var dialog = null;
  var summaryCopyText = '';
  var lastFocused = null;
  var scrollLockState = null;

  /* ---------- Abkürzungs- & zahlenfeste Satzsegmentierung ---------- */
  var SUMMARY_ABBREVS = [
    'z. B.', 'z.B.', 'd. h.', 'd.h.', 'u. a.', 'u.a.', 'v. a.', 'v.a.',
    'z. T.', 'u. s. w.', 'o. Ä.', 'bzw.', 'ca.', 'inkl.', 'exkl.', 'ggf.',
    'ggfs.', 'evtl.', 'mind.', 'max.', 'etc.', 'usw.', 'usf.', 'bspw.',
    'e. g.', 'e.g.', 'i. e.', 'i.e.', 'approx.', 'vs.', 'Dr.', 'Prof.',
    'Nr.', 'Abs.', 'Art.', 'Tab.', 'Abb.', 'Anm.', 'Pkt.', 'Min.', 'Std.',
    'Mio.', 'Mrd.', 'Tsd.', 'MwSt.', 'zzgl.', 'sog.'
  ];

  function escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  // Maskiert Satzende-Punkte, die zu Abkürzungen oder Tausender-
  // trennern gehören, damit sie nicht fälschlich als Satzende zählen.
  function maskSentenceDots(text) {
    var t = String(text || '');
    // Tausenderpunkte: 1.250 -> 1␂250 (Chefredakteur-Standard)
    t = t.replace(/(\d)\.(\d{3})/g, '$1\u0002$2');
    for (var i = 0; i < SUMMARY_ABBREVS.length; i++) {
      var ab = SUMMARY_ABBREVS[i];
      var re = new RegExp(escapeRe(ab).replace(/ /g, '\\s*'), 'g');
      t = t.replace(re, function (m) { return m.replace(/\./g, '\u0002'); });
    }
    return t;
  }

  function summarySentences(text) {
    var masked = maskSentenceDots(String(text || '').replace(/\u00a0/g, ' '));
    return masked
      .replace(/([.!?…]+)(["'»)\]]*)(\s+|$)/g, '$1$2\u0001')
      .split('\u0001')
      .map(function (s) { return s.replace(/\u0002/g, '.').replace(/\s+/g, ' ').trim(); })
      .filter(function (s) { return s.length > 1; });
  }

  function firstSummarySentence(text, maxLen) {
    var s = summarySentences(text)[0] || '';
    var cap = maxLen || 120;
    if (s.length > cap) s = s.slice(0, cap).replace(/\s+\S*$/, '') + '…';
    return s;
  }

  /* ---------- Redaktionelle Signal-Erkennung (DE/EN) ---------- */
  var SIGNAL_DE = [
    'solltest', 'sollte', 'lohnt', 'lohnen', 'sparen', 'sparst', 'spart',
    'ersparnis', 'vermeiden', 'achtung', 'wichtig', 'faustregel', 'tipp',
    'fehler', 'falle', 'nie', 'immer', 'gilt', 'musst', 'müssen',
    'checkliste', 'merke', 'vorsicht', 'profitier', 'senken', 'senkt',
    'reduzier', 'kostet', 'kosten', 'günstig', 'gratis', 'kostenlos',
    'bonus', 'vergleich', 'wechseln', 'prüfen', 'beachten', 'rechnen',
    'fallstrick', 'schützen', 'schutz', 'absichern', 'sparplan'
  ];
  var SIGNAL_EN = [
    'should', 'save', 'saving', 'savings', 'avoid', 'attention',
    'important', 'rule of thumb', 'tip', 'mistake', 'never', 'always',
    'cost', 'costs', 'worth', 'must', 'check', 'compare', 'switch',
    'free', 'beware', 'note', 'protect', 'insurance', 'renew'
  ];

  function signalScore(text, lang) {
    var s = String(text || '');
    var t = s.toLowerCase();
    var score = 0;
    if (/\d/.test(s)) score += 2;
    if (/[€%]|\b(?:euro|prozent|kwh|cent|ct|mbit|gbit)\b/i.test(s)) score += 2;
    var words = (lang === 'en') ? SIGNAL_EN : SIGNAL_DE;
    var hits = 0;
    for (var i = 0; i < words.length; i++) {
      if (t.indexOf(words[i]) !== -1) { hits++; if (hits >= 3) break; }
    }
    score += hits;
    if (/^(?:achtung|wichtig|wichtiger hinweis|faustregel|tipp|merke|vorsicht|attention|important|note|tip|warning)\b/i.test(s.trim())) score += 2;
    var len = s.length;
    if (len < 24) score -= 3;
    else if (len > 230) score -= 2;
    else if (len >= 40 && len <= 180) score += 1;
    return score;
  }

  function normalizeKey(s) {
    return String(s || '').toLowerCase().replace(/[^\wäöüß€%]+/g, ' ').replace(/\s+/g, ' ').trim();
  }

  function overlapRatio(a, b) {
    var wa = normalizeKey(a).split(' ').filter(function (w) { return w.length > 0; });
    var wb = normalizeKey(b).split(' ').filter(function (w) { return w.length > 0; });
    if (!wa.length || !wb.length) return 0;
    var set = {};
    wa.forEach(function (w) { set[w] = 1; });
    var shared = 0;
    wb.forEach(function (w) { if (set[w]) shared++; });
    return shared / Math.min(wa.length, wb.length);
  }

  /* ---------- Dokumenttreue Element-Wanderung ---------- */
  function walkNodes(node, cb) {
    if (!node) return;
    cb(node);
    var kids = node.children || [];
    for (var i = 0; i < kids.length; i++) walkNodes(kids[i], cb);
  }

  /* ---------- Zahlen-Extraktion (Auf einen Blick) ---------- */
  var FIG_UNIT = '(?:€|%|Euro|EUR|Prozent|kWh|Cent|ct|Mbit\\/s|Gbit\\/s|MBit\\/s|GBit\\/s|Min\\.?|Std\\.?|Monate|Monaten|Monat|Jahre|Jahren|Jahr|Tage|Tagen|Wochen)';
  var FIG_PREFIX = '(?:bis zu|rund|etwa|ca\\.?|knapp|über|unter|ab|fast|mehr als|weniger als|maximal|mindestens|bis|circa|approx\\.?|up to|about|around|almost|at least|from)';
  var FIG_RE = new RegExp('(' + FIG_PREFIX + '\\s+)?(\\d[\\d.,]*(?:\\s*(?:–|—|-|bis|to|\\u2013|\\u2014)\\s*\\d[\\d.,]*)?)\\s*(' + FIG_UNIT + ')(\\s*(?:im|pro|je|per)\\s*(?:Monat|Jahr|Tag|Woche|Stunde|Quadratmeter|qm|Kilowattstunde))?', 'gi');

  function fallbackFigureLabel(unit, lang) {
    var u = String(unit || '').toLowerCase();
    if (/€|euro|eur/.test(u)) return lang === 'en' ? 'Cost' : 'Kosten';
    if (/%|prozent/.test(u)) return lang === 'en' ? 'Change' : 'Veränderung';
    if (/kwh/.test(u)) return lang === 'en' ? 'Consumption' : 'Verbrauch';
    if (/cent|ct/.test(u)) return lang === 'en' ? 'Unit price' : 'Preis je Einheit';
    if (/mbit|gbit/.test(u)) return lang === 'en' ? 'Speed' : 'Tempo';
    if (/monat|jahr|tage|wochen/.test(u)) return lang === 'en' ? 'Term' : 'Laufzeit';
    return lang === 'en' ? 'At a glance' : 'Auf einen Blick';
  }

  function figureFromMatch(s0, m, lang) {
    var unit = m[3] || '';
    var value = ((m[1] || '') + m[2] + ' ' + unit + (m[4] ? ' ' + m[4] : '')).replace(/\s+/g, ' ').trim();
    value = value.replace(/[–—]/g, '–');
    if (value.length > 32) value = value.slice(0, 30).replace(/\s+\S*$/, '') + '…';
    var before = s0.slice(0, m.index);
    var after = s0.slice(m.index + m[0].length);
    var label = '';
    if (before && before.replace(/[^\wÄÖÜäöüß€%0-9]+/g, '').length >= 4) {
      label = before;
    } else if (after) {
      label = after;
    }
    label = label.replace(/\s+/g, ' ').trim();
    label = label.replace(/^[^\wÄÖÜäöüß€%0-9]+/, '');
    label = label.replace(/^(?:und|oder|sowie|davon|dabei|also|damit|dass|weil|wenn|aber|doch|the|and|or|so|which|that|this|is|at|von|bei)\s+/i, '');
    // Kurzes Vor-Label („Älter als“) sinnvoll mit dem Rest vervollständigen
    if (label.length < 12 && after) {
      var afterClean = after.replace(/\s+/g, ' ').trim().replace(/^[^\wÄÖÜäöüß€%0-9]+/, '');
      afterClean = afterClean.replace(/^(?:und|oder|sowie|davon|dabei|also|damit|dass|weil|wenn|aber|doch|the|and|or|so|which|that|this|is|at|von|bei)\s+/i, '');
      if (afterClean) {
        if (afterClean.length <= 40) label = (label + ' ' + afterClean).replace(/\s+/g, ' ').trim();
        else label = afterClean;
      }
    }
    // Hängende Verben/Präpositionen entfernen: „…kostet oft nur“ → sauberes Label
    label = label.replace(/(?:kostet|kosten|liegt|liegen|zahlt|zahlst|zahlen|beträgt|betragen|spart|sparst|sparen|bleibt|bleiben|steigt|steigen|sinkt|sinken|lohnt|lohnen|gilt|gelten|von|auf|um|über|unter|bei|mit|für|zu|ab|nach|vor|pro)(?:\s+[a-zäöüß]+){0,2}\s*$/i, '');
    label = label.replace(/[,;:–—\s]+$/, '');
    if (!label) label = fallbackFigureLabel(unit, lang);
    if (label.length > 76) label = label.slice(0, 73).replace(/\s+\S*$/, '') + '…';
    return { value: value, label: label };
  }

  function extractFigure(s, lang) {
    var s0 = String(s || '');
    if (!/[€%]|\b(?:euro|prozent|kwh|cent|ct)\b|\b(?:monat|jahr|tage|wochen)\b/i.test(s0)) return null;
    FIG_RE.lastIndex = 0;
    var m = FIG_RE.exec(s0);
    return m ? figureFromMatch(s0, m, lang) : null;
  }

  function extractFigures(s, lang, max) {
    var s0 = String(s || '');
    var out = [];
    if (!/[€%]|\b(?:euro|prozent|kwh|cent|ct)\b|\b(?:monat|jahr|tage|wochen)\b/i.test(s0)) return out;
    FIG_RE.lastIndex = 0;
    var m;
    while ((m = FIG_RE.exec(s0)) && out.length < (max || 2)) {
      out.push(figureFromMatch(s0, m, lang));
    }
    return out;
  }

  function extractKeyFigures(content, lang) {
    var out = [];
    var seen = {};
    walkNodes(content, function (node) {
      if (!node || !node.tagName) return;
      if (node.closest && node.closest('[data-ff-skip-read]')) return;
      if (node.tagName !== 'P' && node.tagName !== 'LI') return;
      var text = readableText(node);
      if (!text) return;
      summarySentences(text).forEach(function (s) {
        if (out.length >= 6) return;
        // Regel-Pfeile („Bis 5 Jahre → Vollkasko“) sind Kernaussagen, keine Zahlen
        if (/→|->|➜/.test(s)) return;
        extractFigures(s, lang, 2).forEach(function (f) {
          if (out.length >= 6) return;
          var key = normalizeKey(f.value + ' ' + f.label);
          if (seen[key]) return;
          seen[key] = true;
          out.push(f);
        });
      });
    });
    return out;
  }

  /* ---------- Kernaussagen (3–5 redaktionelle Bullets) ---------- */
  function extractKeyBullets(content, lang) {
    var cands = [];
    var seen = {};
    var currentAnchor = '';
    var order = 0;
    walkNodes(content, function (node) {
      if (!node || !node.tagName) return;
      if (node.closest && node.closest('[data-ff-skip-read]')) return;
      var tag = node.tagName;
      if (tag === 'H2' && node.id) { currentAnchor = node.id; return; }
      if (tag !== 'P' && tag !== 'LI' && tag !== 'BLOCKQUOTE' && tag !== 'H3') return;
      var text = readableText(node);
      if (!text || text.length < 20) return;
      summarySentences(text).slice(0, 3).forEach(function (s) {
        if (s.length < 24 || s.length > 260) return;
        var key = normalizeKey(s);
        if (seen[key]) return;
        seen[key] = true;
        cands.push({ text: s, anchor: currentAnchor, score: signalScore(s, lang), order: order++ });
      });
    });

    cands.sort(function (a, b) { return b.score - a.score; });

    var perSection = {};
    var picked = [];
    cands.forEach(function (c) {
      if (picked.length >= 5) return;
      var k = c.anchor || '_';
      if ((perSection[k] || 0) >= 2) return;
      var dup = false;
      for (var i = 0; i < picked.length; i++) {
        if (overlapRatio(picked[i].text, c.text) > 0.6) { dup = true; break; }
      }
      if (dup) return;
      perSection[k] = (perSection[k] || 0) + 1;
      picked.push(c);
    });

    // Mindestbesatz: falls zu streng gefiltert wurde, auffüllen
    if (picked.length < 3) {
      cands.forEach(function (c) {
        if (picked.length >= 3) return;
        if (picked.indexOf(c) !== -1) return;
        picked.push(c);
      });
    }

    picked.sort(function (a, b) { return a.order - b.order; });
    return picked.map(function (c) { return { text: c.text, anchor: c.anchor }; });
  }

  /* ---------- Inhaltsverzeichnis (In diesem Artikel) ---------- */
  function extractToc(content) {
    var toc = [];
    var cur = null;
    walkNodes(content, function (node) {
      if (!node || !node.tagName) return;
      if (node.closest && node.closest('[data-ff-skip-read]')) return;
      var tag = node.tagName;
      if (tag === 'H2' && node.id) {
        var title = readableText(node);
        if (title) { cur = { id: node.id, title: title, lead: '' }; toc.push(cur); }
        return;
      }
      if (cur && !cur.lead && (tag === 'P' || tag === 'H3')) {
        var t = readableText(node);
        if (t) cur.lead = firstSummarySentence(t, 110);
      }
    });
    return toc;
  }

  /* ---------- Tabellen-Highlights ---------- */
  function cellTexts(row) {
    var cells = [];
    var kids = row.children || [];
    for (var i = 0; i < kids.length; i++) {
      if (kids[i].tagName === 'TH' || kids[i].tagName === 'TD') cells.push(readableText(kids[i]));
    }
    return cells;
  }

  function scanTable(tbl) {
    var headers = [];
    var rows = [];
    var rowCount = 0;
    var caption = '';
    var kids = tbl.children || [];
    for (var i = 0; i < kids.length; i++) {
      var part = kids[i];
      var tag = part.tagName;
      if (tag === 'CAPTION') { caption = readableText(part); continue; }
      if (tag === 'THEAD') {
        var htrs = part.children || [];
        for (var j = 0; j < htrs.length; j++) {
          if (htrs[j].tagName === 'TR') { headers = cellTexts(htrs[j]); break; }
        }
        continue;
      }
      if (tag === 'TBODY') {
        var trs = part.children || [];
        rowCount = trs.length;
        for (var k = 0; k < trs.length && rows.length < 3; k++) {
          if (trs[k].tagName === 'TR') rows.push(cellTexts(trs[k]));
        }
        continue;
      }
      if (tag === 'TR') { rowCount++; if (rows.length < 3) rows.push(cellTexts(part)); }
    }
    if (!headers.length && rows.length) headers = rows.shift();
    return { caption: caption, headers: headers, rows: rows, rowCount: rowCount };
  }

  function extractTables(content, lang) {
    var out = [];
    var sectionTitle = '';
    var sectionAnchor = '';
    walkNodes(content, function (node) {
      if (!node || !node.tagName) return;
      if (node.closest && node.closest('[data-ff-skip-read]')) return;
      var tag = node.tagName;
      if (tag === 'H2' || tag === 'H3') {
        var ht = readableText(node);
        if (ht) sectionTitle = ht;
        if (tag === 'H2' && node.id) sectionAnchor = node.id;
        return;
      }
      if (tag !== 'TABLE') return;
      var t = scanTable(node);
      var title = t.caption || sectionTitle || texts.tableTitleDefault;
      out.push({
        title: title,
        headers: t.headers,
        rows: t.rows,
        rowCount: t.rowCount,
        anchor: sectionAnchor
      });
    });
    return out;
  }

  /* ---------- Kurzantwort (30 Sekunden) ---------- */
  function pickShortAnswer(content, lang) {
    var short = stripMd(cfg.kurzantwort || cfg.description || '');
    if (short) return short;
    var best = '';
    var bestScore = -1;
    walkNodes(content, function (node) {
      if (!node || node.tagName !== 'P') return;
      var t = readableText(node);
      if (!t || t.length < 40) return;
      var score = signalScore(t, lang);
      // Szenen-Einstiege („Stell dir vor …“) sind keine Antworten
      if (/stell dir|vor ein|ein beispiel|story|szenario|imagine|picture this/i.test(t)) score -= 4;
      if (score > bestScore) { bestScore = score; best = t; }
    });
    if (best) return summarySentences(best).slice(0, 3).join(' ');
    return '';
  }

  /* ---------- Datensammlung ---------- */
  function buildSummaryData() {
    var content = doc.querySelector('.post-content') || doc.querySelector('.md-content');
    var lang = currentLang;
    var data = { short: '', bullets: [], figures: [], toc: [], tables: [] };
    if (content) {
      data.short = pickShortAnswer(content, lang);
      data.bullets = extractKeyBullets(content, lang);
      data.figures = extractKeyFigures(content, lang);
      data.toc = extractToc(content);
      data.tables = extractTables(content, lang);
    }
    data.author = stripMd(cfg.author || '');
    data.date = stripMd(cfg.date || '');
    data.updated = stripMd(cfg.updated || '');
    data.category = stripMd(cfg.category || '');
    return data;
  }

  /* ---------- Klartext-Kurzfassung (Kopieren) ---------- */
  function buildPlainText(data) {
    var lines = [];
    lines.push((texts.summaryEyebrow.toUpperCase()) + ': ' + (stripMd(cfg.title) || doc.title));
    lines.push(texts.source + win.location.href);
    var meta = [];
    if (cfg.readingTime) meta.push(texts.readingTime.replace('{time}', cfg.readingTime));
    if (cfg.wordCount) meta.push(texts.wordCount.replace('{count}', cfg.wordCount));
    if (data.toc.length) meta.push(texts.sectionCount.replace('{count}', data.toc.length));
    if (data.author) meta.push(texts.summaryAuthor.replace('{name}', data.author));
    if (data.updated) meta.push(texts.summaryStand.replace('{date}', data.updated));
    else if (data.date) meta.push(texts.summaryStand.replace('{date}', data.date));
    if (meta.length) lines.push(meta.join(' · '));
    lines.push('');
    if (data.short) { lines.push(texts.summaryQuick30 + ':'); lines.push(data.short); lines.push(''); }
    if (data.bullets.length) {
      lines.push(texts.summaryKeypoints + ':');
      data.bullets.forEach(function (b, i) { lines.push((i + 1) + '. ' + b.text); });
      lines.push('');
    }
    if (data.figures.length) {
      lines.push(texts.summaryNumbers + ':');
      data.figures.forEach(function (f) { lines.push('- ' + f.value + (f.label ? ' — ' + f.label : '')); });
      lines.push('');
    }
    if (data.toc.length) {
      lines.push(texts.summaryToc + ':');
      data.toc.forEach(function (s) { lines.push('- ' + s.title + (s.lead ? ' — ' + s.lead : '')); });
      lines.push('');
    }
    return lines.join('\n');
  }

  /* ---------- DOM-Helfer ---------- */
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

  /* ---------- Fokus-Falle & Scroll-Sperre (WCAG 2.2) ---------- */
  function dialogIsOpen() {
    if (!dialog) return false;
    if (dialog.open === true) return true;
    return dialog.getAttribute && dialog.getAttribute('open') !== null;
  }

  function focusableIn(root) {
    return qsa('a[href], button, [tabindex]:not([tabindex="-1"])', root).filter(function (n) {
      return !(n.disabled || (n.getAttribute && n.getAttribute('aria-hidden') === 'true'));
    });
  }

  function trapFocus(e) {
    if (!dialogIsOpen()) return;
    var nodes = focusableIn(dialog);
    if (!nodes.length) { e.preventDefault(); return; }
    var first = nodes[0];
    var last = nodes[nodes.length - 1];
    var active = doc.activeElement;
    if (e.shiftKey && (active === first || active === dialog)) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && active === last) { e.preventDefault(); first.focus(); }
  }

  function lockScroll(lock) {
    var root = doc.scrollingElement || doc.documentElement;
    if (!root || !root.style) return;
    if (lock) {
      scrollLockState = {
        html: root.style.overflow || '',
        body: (doc.body && doc.body.style && doc.body.style.overflow) || ''
      };
      root.style.overflow = 'hidden';
      if (doc.body && doc.body.style) doc.body.style.overflow = 'hidden';
    } else if (scrollLockState) {
      root.style.overflow = scrollLockState.html;
      if (doc.body && doc.body.style) doc.body.style.overflow = scrollLockState.body;
      scrollLockState = null;
    }
  }

  /* ---------- Dialog-Aufbau ---------- */
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
    dialog.setAttribute('aria-modal', 'true');

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

    // Byline / Meta-Zeile (Verlagshaus-Standard)
    var metaParts = [];
    if (cfg.readingTime) metaParts.push(texts.readingTime.replace('{time}', cfg.readingTime));
    if (cfg.wordCount) metaParts.push(texts.wordCount.replace('{count}', cfg.wordCount));
    if (data.toc.length) metaParts.push(texts.sectionCount.replace('{count}', data.toc.length));
    if (data.author) metaParts.push(texts.summaryAuthor.replace('{name}', data.author));
    if (data.updated) metaParts.push(texts.summaryStand.replace('{date}', data.updated));
    else if (data.date) metaParts.push(texts.summaryStand.replace('{date}', data.date));
    if (metaParts.length) body.appendChild(el('div', 'ff-summary__meta', metaParts.join(' · ')));

    var hasContent = !!(data.short || data.bullets.length || data.figures.length || data.toc.length || data.tables.length);

    // 1) Kurzantwort – „Das Wichtigste in 30 Sekunden“
    if (data.short) {
      var hero = el('section', 'ff-summary__section ff-summary__hero');
      hero.appendChild(el('h3', null, texts.summaryQuick30));
      hero.appendChild(el('p', 'ff-summary__hero-text', data.short));
      body.appendChild(hero);
    }

    // 2) Kernaussagen – nummerierte Bullets mit Sprungmarke
    if (data.bullets.length) {
      var s2 = el('section', 'ff-summary__section');
      s2.appendChild(el('h3', null, texts.summaryKeypoints));
      var ol = el('ol', 'ff-summary__bullets');
      data.bullets.forEach(function (b) {
        var li = el('li', 'ff-summary__bullet');
        li.appendChild(doc.createTextNode(b.text));
        if (b.anchor) {
          li.appendChild(doc.createTextNode(' '));
          var a = el('a', 'ff-summary__jump', texts.summaryJump + ' ↗');
          a.href = '#' + b.anchor;
          a.setAttribute('aria-label', texts.summaryJump + ': ' + b.text);
          li.appendChild(a);
        }
        ol.appendChild(li);
      });
      s2.appendChild(ol);
      body.appendChild(s2);
    }

    // 3) Auf einen Blick – Big-Number-Karten
    if (data.figures.length) {
      var s3 = el('section', 'ff-summary__section');
      s3.appendChild(el('h3', null, texts.summaryNumbers));
      var grid = el('div', 'ff-summary__figures');
      data.figures.forEach(function (f) {
        var card2 = el('div', 'ff-summary__figure');
        card2.appendChild(el('div', 'ff-summary__figure-value', f.value));
        card2.appendChild(el('div', 'ff-summary__figure-label', f.label));
        grid.appendChild(card2);
      });
      s3.appendChild(grid);
      body.appendChild(s3);
    }

    // 4) In diesem Artikel – Inhaltsverzeichnis
    if (data.toc.length) {
      var s4 = el('section', 'ff-summary__section');
      s4.appendChild(el('h3', null, texts.summaryToc));
      var ol2 = el('ol', 'ff-summary__toc');
      data.toc.forEach(function (s) {
        var li = el('li', 'ff-summary__toc-item');
        var a = el('a', null, s.title);
        a.href = '#' + s.id;
        li.appendChild(a);
        if (s.lead) li.appendChild(el('span', 'ff-summary__toc-lead', ' — ' + s.lead));
        ol2.appendChild(li);
      });
      s4.appendChild(ol2);
      body.appendChild(s4);
    }

    // 5) Tabellen & Übersichten im Fokus
    if (data.tables.length) {
      var s5 = el('section', 'ff-summary__section');
      s5.appendChild(el('h3', null, texts.summaryTables));
      data.tables.forEach(function (t) {
        var box = el('div', 'ff-summary__table');
        var head = el('div', 'ff-summary__table-head');
        head.appendChild(el('span', 'ff-summary__table-title', t.title));
        if (t.rowCount) head.appendChild(el('span', 'ff-summary__table-meta', texts.summaryRowCount.replace('{count}', t.rowCount)));
        box.appendChild(head);
        if (t.headers.length) box.appendChild(el('div', 'ff-summary__table-row ff-summary__table-row--head', t.headers.join(' · ')));
        t.rows.forEach(function (r) {
          box.appendChild(el('div', 'ff-summary__table-row', r.join(' · ')));
        });
        if (t.anchor) {
          var jump = el('a', 'ff-summary__jump', texts.summaryJumpTable + ' ↗');
          jump.href = '#' + t.anchor;
          box.appendChild(jump);
        }
        s5.appendChild(box);
      });
      body.appendChild(s5);
    }

    if (!hasContent) {
      body.appendChild(el('p', 'ff-summary__empty', texts.summaryEmpty));
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

    // Escape can close a native dialog without going through our button.
    // Always release the scroll lock and return focus in that path too.
    dialog.addEventListener('close', function () {
      lockScroll(false);
      removeFallbackBackdrop();
      restoreDialogFocus();
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

  /* Fokus-Rückgabe (WCAG 2.4.3).
     Fix 03.09.2026: `doc.activeElement` ist beim Öffnen fast immer <body> –
     Safari auf macOS/iOS fokussiert Buttons beim Klick nämlich bewusst NICHT.
     Der alte Code merkte sich dann <body> und gab den Fokus an ein nicht
     fokussierbares Element zurück: Tastaturnutzer:innen landeten nach dem
     Schließen am Dokumentanfang. Jetzt wird geprüft, ob das gemerkte Element
     tatsächlich fokussierbar und noch im Dokument ist – sonst springt der
     Fokus zuverlässig auf den Kurzfassung-Button zurück. */
  function isFocusable(n) {
    if (!n || typeof n.focus !== 'function') return false;
    if (n.disabled) return false;
    if (!doc.body || !doc.body.contains(n)) return false;
    var tag = String(n.tagName || '').toLowerCase();
    if (tag === 'body' || tag === 'html') return false;
    return true;
  }

  function restoreDialogFocus() {
    var target = isFocusable(lastFocused) ? lastFocused : (isFocusable(summaryBtn) ? summaryBtn : null);
    if (target) {
      try { target.focus({ preventScroll: true }); } catch (e) { try { target.focus(); } catch (e2) {} }
    }
    lastFocused = null;
  }

  function openDialog() {
    buildDialog();
    if (dialogIsOpen()) return;
    lastFocused = isFocusable(doc.activeElement) ? doc.activeElement : summaryBtn;
    lockScroll(true);
    var opened = false;
    if (typeof dialog.showModal === 'function') {
      try { dialog.showModal(); opened = true; } catch (e) {}
    }
    if (!opened) {
      dialog.setAttribute('open', '');
      dialog.classList.add('ff-summary--fallback');
      addFallbackBackdrop();
    }
    var closeBtn = dialog.querySelector('.ff-summary__close');
    if (closeBtn) closeBtn.focus({ preventScroll: true });
  }

  function closeDialog() {
    if (!dialog) return;
    var fallback = dialog.classList.contains('ff-summary--fallback');
    if (!fallback && typeof dialog.close === 'function' && dialogIsOpen()) {
      try { dialog.close(); } catch (e) {}
    }
    if (fallback || dialog.getAttribute('open') !== null) {
      dialog.removeAttribute('open');
      dialog.classList.remove('ff-summary--fallback');
      removeFallbackBackdrop();
    }
    lockScroll(false);
    restoreDialogFocus();
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
    if (!dialogIsOpen()) return;
    if (e.key === 'Escape' && dialog.classList.contains('ff-summary--fallback')) {
      closeDialog();
      return;
    }
    if (e.key === 'Tab') trapFocus(e);
  });

  /* ============================================================
     EXPORT-HOOK (read-only) — eine einzige Text-Pipeline
     ------------------------------------------------------------
     Die First-Party-Audiofassungen (static/audio/*.mp3) müssen exakt
     denselben Sprechtext verwenden wie der Browser-Reader: dieselbe
     Block-Sammlung, dasselbe DE/EN-Routing, dieselbe Aussprache-
     Normalisierung, dieselbe Atemgruppen-Bildung. Würde die Logik für
     das Rendern ein zweites Mal implementiert, liefen Audio und
     Vorlesen unweigerlich auseinander.

     Deshalb: kein Nachbau, sondern derselbe Code. `scripts/prepare_audio_chunks.mjs`
     lädt diese Datei unverändert in jsdom und ruft den Hook auf.
     Der Hook spricht nichts, setzt keinen Wiedergabezustand und ändert
     nichts am DOM.
  ============================================================ */
  function buildSpeechTimelineForExport() {
    currentLang = detectArticleLanguage();
    texts = I18N[currentLang] || I18N.de;
    calibrateQuality();
    blocks = collectBlocks();
    buildTimeline();
    return {
      lang: currentLang,
      quality: { tier: quality.tier, rate: quality.rate, maxChunk: quality.maxChunk },
      blocks: blocks.map(function (b) {
        return { type: b.type, lang: b.lang, text: b.text };
      }),
      timeline: timeline.map(function (u) {
        return {
          blockIndex: u.blockIndex,
          type: u.type,
          lang: u.lang,
          text: u.text,
          rate: u.effRate,
          pauseAfter: u.after
        };
      })
    };
  }

  win.__ffReaderExport = {
    version: 7,
    buildTimeline: buildSpeechTimelineForExport,
    speechNormalize: speechNormalize,
    detectLanguage: detectArticleLanguage,
    resolveVoice: function (lang) {
      var r = resolveMaleVoice(lang);
      if (!r || !r.voice) return null;
      return { name: r.voice.name, lang: r.voice.lang, mode: r.mode, explicit: !!r.explicit };
    }
  };
})();
