/* ============================================================
   FranksFinanzcheck – Premium Lesehilfen (Vorlesen + Kurzfassung)
   03.09.2026 — Profi-Agentur & Chefredakteur-Standard · Highend v7
   · Vorlesen v7: Vollständige Vorlesefunktion auf Verlagsspitze
     (übertrifft Capital / WirtschaftsWoche / Die Zeit) — High-End Garantie
     für explizit männliche Stimme DE & EN ohne Umschalter, mit
     sofortigem Tonpfad auch bei lazy Voice-Katalogen.
     ZEIT-Standard: vorab vertonte Tonspur (männliche DE-/EN-Stimme,
     serverseitig erzeugt wie bei zeit.de) im nativen HTML5-Player –
     klingt identisch auf iPhone, Mac, Tablet, Android, PC und in jedem
     Browser. Ohne Tonspur bleibt die lokale Web-Speech-Engine aktiv.
   · Kurzfassung v5: Vollständige Verlagshaus-Kurzfassung
     (Kurzantwort, Kernaussagen, Zahlen auf einen Blick,
     Inhaltsverzeichnis, Tabellen-Highlights, Byline, Fokus-Falle)
   ------------------------------------------------------------
   - Privacy-first & First-party: lokale Web Speech API und/oder eine
     ersteigene Tonspur (static/audio) — kein Tracking, kein Fremd-CDN.
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

  // v7 – ZEIT-Standard: vorab vertonte Tonspur. Der Generator
  // (scripts/generate_reader_audio.py) schreibt die Tonspur-Konfiguration
  // in einen eigenen, austauschbaren Config-Block. Ohne diesen Block bleibt
  // der lokale Web-Speech-Pfad aktiv (kostenloser Fallback).
  var audioCfgEl = doc.getElementById('ff-reader-audio-config');
  if (audioCfgEl) {
    try {
      var audioCfg = JSON.parse(audioCfgEl.textContent || '{}') || {};
      if (audioCfg && audioCfg.audio) cfg.audio = audioCfg.audio;
    } catch (e) {}
  }

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
      voiceFallback: 'Vorlesen gestartet; dein Browser stellt die verfügbare Stimme bereit.',
      speechError: 'Dieser Abschnitt konnte nicht abgespielt werden; es geht weiter.',
      voiceLoading: 'Männliche Stimme wird geladen …',
      paused: 'Vorlesen pausiert.',
      resumed: 'Vorlesen fortgesetzt.',
      finished: 'Vorlesen beendet.',
      resumedPos: 'Vorlesen an der zuletzt gehörten Stelle fortgesetzt.',
      remaining: 'noch ca. {min} Min.',
      mediaArtist: 'FranksFinanzcheck – Artikel zum Hören',
      introLine: '{title}. Ein Beitrag von FranksFinanzcheck. Hördauer etwa {duration}.',
      durationMinutes: '{n} Minuten',
      durationMinuteOne: 'eine Minute',
      durationUnknown: 'einige Minuten',
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
      tableIntroSingular: 'Tabelle: {title}. Übersicht mit {cols} Spalten und einer Zeile.',
      tableRow: 'Zeile {row} von {total}. {content}.',
      tableSum: 'Zusammengerechnet: {content}',
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
      voiceFallback: 'Playback started; your browser provides the available voice.',
      speechError: 'This section could not be played; continuing.',
      voiceLoading: 'Loading a male voice …',
      paused: 'Audio playback paused.',
      resumed: 'Audio playback resumed.',
      finished: 'Audio playback completed.',
      resumedPos: 'Resumed from your last listening position.',
      remaining: 'approx. {min} min left',
      mediaArtist: 'FranksFinanzcheck – Article Audio',
      introLine: '{title}. An article by FranksFinanzcheck. Listening time about {duration}.',
      durationMinutes: '{n} minutes',
      durationMinuteOne: 'one minute',
      durationUnknown: 'a few minutes',
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
      tableIntroSingular: 'Table: {title}. Overview with {cols} columns and one row.',
      tableRow: 'Row {row} of {total}. {content}.',
      tableSum: 'In total: {content}',
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
  /* Zahlwort-Kongruenz für die Hördauer: „Hördauer etwa 1 Minuten" ist
     derselbe Roboter-Verräter wie „1 Zeilen" in einer Tabelle. */
  function durationPhrase(lang, minutes) {
    var t = I18N[lang] || I18N.de;
    var n = parseInt(minutes, 10);
    if (!isFinite(n) || n <= 0) return t.durationUnknown;
    return n === 1 ? t.durationMinuteOne : t.durationMinutes.replace('{n}', n);
  }

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

  function normTag(el) { return String((el && el.tagName) || '').toUpperCase(); }

  function isReaderSkipped(el) {
    return !!(el && el.closest && el.closest('script, style, noscript, [aria-hidden="true"], [data-ff-skip-read], .ff-reader-toolbar, .ff-toc, #TableOfContents, .ff-share, .ff-related'));
  }

  function isTableLike(el) {
    if (!el) return false;
    var tag = normTag(el);
    if (tag === 'TABLE') return true;
    var role = String((el.getAttribute && el.getAttribute('role')) || '').toLowerCase();
    if (role === 'table' || role === 'grid' || role === 'treegrid') return true;
    if (el.classList && (el.classList.contains('ff-table-scroll') || el.classList.contains('ff-tv-tablewrap') ||
        el.classList.contains('ff-es-tablewrap') || el.classList.contains('wp-block-table') ||
        el.classList.contains('table-wrapper') || el.classList.contains('table-responsive'))) return true;
    return false;
  }

  function innerTable(el) {
    if (!el) return null;
    if (normTag(el) === 'TABLE') return el;
    var role = String((el.getAttribute && el.getAttribute('role')) || '').toLowerCase();
    if (role === 'table' || role === 'grid' || role === 'treegrid') return el;
    return el.querySelector ? el.querySelector('table, [role="table"], [role="grid"], [role="treegrid"]') : null;
  }

  function isStandaloneEmphasis(el) {
    if (!el || !/^(STRONG|B)$/.test(normTag(el))) return false;
    if (el.closest && el.closest('p, li, blockquote, td, th, caption, h1, h2, h3, h4, h5, h6, a, button, .ff-kurzantwort, .ff-korrektur, .callout, .ff-tarif-card, .ff-einspar-box')) return false;
    return readableText(el).length > 1;
  }


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
    /* `[hidden]` gehört dazu: Verborgenes ist Deko, keine Sprache – und die
       Tonspur (scripts/generate_reader_audio.py) filtert es ebenfalls. */
    qsa('script, style, noscript, .ff-heading-copy, .anchor, [aria-hidden="true"], [hidden], .ff-reader-toolbar', clone)
      .forEach(function (n) { if (n.parentNode) n.parentNode.removeChild(n); });
    /* Zeilenumbrüche und Blockgrenzen sind Wortgrenzen. Ohne diesen
       Schritt verschmilzt „1200 Euro<br><small>pro Jahr</small>“ zu
       „1200 Europro Jahr“ – in Tabellenköpfen und Übersichtskarten
       (Vorher/Nachher/Ersparnis) war das hörbar falsch. */
    var ownerDoc = clone.ownerDocument || doc;
    qsa('br', clone).forEach(function (n) {
      if (n.parentNode) n.parentNode.replaceChild(ownerDoc.createTextNode(' '), n);
    });
    /* Nur ECHTE Blockelemente trennen. Inline-Auszeichnungen
       (strong/em/span/small) dürfen NIE getrennt werden, sonst wird aus
       „Ein <strong>fett</strong>er Teil“ ein gesprochenes „fett er“. */
    qsa('p, div, li, tr, td, th, h1, h2, h3, h4, h5, h6, blockquote, section, article', clone)
      .forEach(function (n) {
        if (n.parentNode && n.nextSibling) n.parentNode.insertBefore(ownerDoc.createTextNode(' '), n.nextSibling);
      });
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

    /* --- Entity-Reste: Markup ist keine Sprache -----------------------
       Steht im Text noch „300&nbsp;€" (zweite Escape-Stufe, Copy-Paste
       aus einem CMS, Shortcode-Ausgabe), darf daraus niemals „300 und
       nbsp Euro" werden. Zuerst die bedeutungstragenden Entities, dann
       der Rest als Wortgrenze. */
    s = s.replace(/&(?:nbsp|#160|#x0*a0);/gi, ' ');
    s = s.replace(/&(?:amp|#38);/gi, ' und ');
    s = s.replace(/&(?:shy|#173);/gi, '');
    s = s.replace(/&(?:euro|#8364);/gi, ' Euro ');
    s = s.replace(/&[a-zA-Z][a-zA-Z0-9]{1,10};/g, ' ');
    s = s.replace(/&#\d{1,7};/g, ' ');

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

    /* --- Fachzeichen: im Sichttext korrekt, gesprochen bedeutungslos ---
       Diese Zeichen sind in der Seite richtig gesetzt und bleiben dort
       unverändert. Viele Sprachengines überlesen sie aber oder
       buchstabieren sie – und dann bricht der Satz zusammen:
       „2,7 Cent × 20000 kWh" ohne das „mal" ergibt keinen Sinn mehr,
       „CO₂" wird zu „CO", „90 m²" zu „90 m". Also konsequent
       ausschreiben, bevor gesprochen wird. */
    /* Steht die Einheit bereits ausgeschrieben vor der Klammer, würde sie
       gesprochen doppelt erscheinen: „in Kubikmetern (m³)" -> „in
       Kubikmetern Kubikmeter". Die Klammer ist dann nur eine
       Schreibvariante desselben Wortes und fällt weg. */
    s = s.replace(/(Kubikmetern?|cubic meters?)\s*\(m³\)/gi, '$1');
    s = s.replace(/(Quadratmetern?|square meters?)\s*\(m²\)/gi, '$1');
    s = s.replace(/km²/g, lang === 'en' ? ' square kilometers' : ' Quadratkilometer');
    s = s.replace(/(\d)\s*[-–]?\s*m²/g, '$1' + (lang === 'en' ? ' square meters' : ' Quadratmeter'));
    s = s.replace(/m²/g, lang === 'en' ? ' square meters' : ' Quadratmeter');
    s = s.replace(/(\d)\s*[-–]?\s*m³/g, '$1' + (lang === 'en' ? ' cubic meters' : ' Kubikmeter'));
    s = s.replace(/m³/g, lang === 'en' ? ' cubic meters' : ' Kubikmeter');
    s = s.replace(/°\s*C\b/g, lang === 'en' ? ' degrees Celsius' : ' Grad Celsius');
    s = s.replace(/°/g, lang === 'en' ? ' degrees' : ' Grad');
    s = s.replace(/[₀₁₂₃₄₅₆₇₈₉]/g, function (m) {
      return String('₀₁₂₃₄₅₆₇₈₉'.indexOf(m));
    });
    s = s.replace(/[²³¹]/g, function (m) {
      return lang === 'en' ? ' to the power of ' + String('¹²³'.indexOf(m) + 1)
                           : ' hoch ' + String('¹²³'.indexOf(m) + 1);
    });
    s = s.replace(/×/g, lang === 'en' ? ' times ' : ' mal ');
    s = s.replace(/−/g, lang === 'en' ? ' minus ' : ' minus ');
    s = s.replace(/·/g, ', ');
    s = s.replace(/Ø\s*/g, lang === 'en' ? 'average ' : 'Durchschnitt ');
    /* à ist kein \w-Zeichen, \b davor matcht nie – deshalb ohne \b. */
    s = s.replace(/à\s+(?=\d)/g, lang === 'en' ? 'at ' : 'je ');
    s = s.replace(/\u2011/g, '-');            // trennfester Bindestrich -> normal

    /* Führendes Minus ist ein Vorzeichen, kein Gedankenstrich.
       „Bonus: - 180,00 Euro (Gutschrift)" muss als „minus 180,00 Euro"
       gesprochen werden – sonst klingt eine Gutschrift wie eine
       zusätzliche Forderung. */
    s = s.replace(/(^|[\s:(])\s*-\s*(?=\d)/g, '$1' + (lang === 'en' ? ' minus ' : ' minus '));

    /* --- Schrägstrich: „pro", „bis", „und" oder „oder" je nach Kontext --- */

    s = s.replace(/\s*\/\s*Kilowattstunden?\b/gi, lang === 'en' ? ' per kilowatt hour' : ' pro Kilowattstunde');
    s = s.replace(/\s*\/\s*(kWh|Kilowattstunde)\b/gi, lang === 'en' ? ' per kilowatt hour' : ' pro Kilowattstunde');
    s = s.replace(/\bVoll\s*\/\s*(Voll|Leer)\b/gi, '$1 zu $1');
    s = s.replace(/Download\s*\/\s*Upload/gi, lang === 'en' ? 'download and upload' : 'Download und Upload');
    s = s.replace(/TCP\s*\/\s*(IPv\d)/gi, 'TCP $1');
    s = s.replace(/Mobiles Netz\s*\/\s*Datennutzung/gi, 'Mobiles Netz, dann Datennutzung');
    s = s.replace(/\b(\d{4})\s*\/\s*(\d{2,4})\b/g, '$1' + (lang === 'en' ? ' to ' : ' bis ') + '$2');
    s = s.replace(/(\d)\s*\/\s*(?=\d)/g, '$1' + (lang === 'en' ? ' and ' : ' und '));
    /* Schrägstrich mit Maßeinheit im Nenner meint immer „pro", nie „oder":
       „Grundpreis / Monat", „kWh/Jahr", „80 €/Jahr", „2 bis 4 Stunden/Woche".
       Muss VOR der allgemeinen Wort/Wort-Regel stehen. */
    s = s.replace(/\s*\/\s*(Monate?|Jahre?|Kilowattstunden?|kWh|Stunden?|Minuten?|Sekunden?|Wochen?|Tagen?|Personen?|Quadratmetern?|m²)\b/gi,
      function (m, einheit) {
        /* Nach „pro" steht im Deutschen der Singular: „pro Kilowattstunde",
           nicht „pro Kilowattstunden". Die Quelle schreibt die Einheit im
           Plural, weil sie als Spaltenüberschrift steht. */
        var EINZAHL = {
          monate: 'Monat', jahr: 'Jahr', jahre: 'Jahr',
          kilowattstunde: 'Kilowattstunde', kilowattstunden: 'Kilowattstunde', kwh: 'Kilowattstunde',
          stunde: 'Stunde', stunden: 'Stunde', minute: 'Minute', minuten: 'Minute',
          sekunde: 'Sekunde', sekunden: 'Sekunde', woche: 'Woche', wochen: 'Woche',
          tag: 'Tag', tagen: 'Tag', person: 'Person', personen: 'Person',
          quadratmeter: 'Quadratmeter', 'm²': 'Quadratmeter'
        };
        var name = EINZAHL[einheit.toLowerCase()] || einheit;
        if (lang === 'en') {
          var EN = { Monat: 'month', Jahr: 'year', Kilowattstunde: 'kilowatt hour',
                     Stunde: 'hour', Minute: 'minute', Sekunde: 'second',
                     Woche: 'week', Tag: 'day', Person: 'person', Quadratmeter: 'square meter' };
          return ' per ' + (EN[name] || name.toLowerCase());
        }
        return ' pro ' + name;
      });
    /* Bandbreiten: „250 Mbit/s", „1000 MBit/s", „1 Gbit/s". Muss VOR der
       allgemeinen Wort/Wort-Regel stehen – sonst wird aus „Mbit/s" erst
       „Mbit oder s" und die Einheit passt nicht mehr. */
    s = s.replace(/\b(?:Mbit|Megabit)\s*\/\s*s\b/gi, lang === 'en' ? 'megabits per second' : 'Megabit pro Sekunde');
    s = s.replace(/\b(?:Gbit|Gigabit)\s*\/\s*s\b/gi, lang === 'en' ? 'gigabits per second' : 'Gigabit pro Sekunde');
    s = s.replace(/([A-Za-zäöüßÄÖÜ])\s*\/\s*(?=[A-Za-zäöüßÄÖÜ])/g, '$1' + (lang === 'en' ? ' or ' : ' oder '));

    /* Zahlenreihen mit drei oder mehr Gliedern sind Eigennamen, keine
       Zahlenbereiche: Aus der „50-30-20-Regel" machte die Bereichsregel
       „50 bis 30-20-Regel". Geschützt bis zum Ende der Normalisierung. */
    s = s.replace(/\b\d{1,3}(?:-\d{1,3}){2,}\b/g, function (m) {
      return m.replace(/-/g, '\u0003');
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
      s = s.replace(/(\d)\s*[-–—]\s*€\s*[-–—]\s*/g, '$1-euro-');
      s = s.replace(/(\d)\s*[-–—]\s*(?:EUR|Euro)\s*[-–—]\s*/gi, '$1-euro-');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(?:€|Euro\b|EUR\b)/gi, '$1 to $2 Euros');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*\$/g, '$1 to $2 Dollars');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*%/g, '$1 to $2 percent');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)/g, '$1 to $2');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*(?:€|Euro\b|EUR\b)/gi, '$1 Euros');
      s = s.replace(/&/g, ' and ');
      s = s.replace(/\$\s*(\d+(?:[.,]\d+)?)/g, '$1 Dollars');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*\$/g, '$1 Dollars');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*%/g, '$1 percent');
      s = s.replace(/\b(\d+)\s*(?:Cent|ct)\b/gi, '$1 Cents');
      s = s.replace(/\b(?:Cent|ct)\/kWh\b/gi, 'Cents per kilowatt hour');
      /* „kilowatt hours (kWh)" – die Klammer wiederholt nur das bereits
         ausgeschriebene Wort und würde gesprochen doppelt erscheinen. */
      s = s.replace(/(kilowatt hours?)\s*\(kWh\)/gi, '$1');
      s = s.replace(/\b(per)\s+kWh\b/gi, '$1 kilowatt hour');
      s = s.replace(/\b(?:kWh|kwh)\b/g, 'kilowatt hours');
      s = s.replace(/\b(?:Mbit|MBit|Megabit)\s*\/\s*s\b/gi, 'megabits per second');
      s = s.replace(/\b(?:Gbit|GBit|Gigabit)\s*\/\s*s\b/gi, 'gigabits per second');
      s = s.replace(/\b(?:Mbit|MBit)\b/g, 'megabit');
      s = s.replace(/\b(?:Gbit|GBit)\b/g, 'gigabit');
      s = s.replace(/\s*\/\s*s\b/g, ' per second');
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
      /* „150-€-Bonus": Steht das Währungszeichen zwischen Bindestrichen,
         muss es Teil des Wortes bleiben. Das spätere Auffangnetz
         (€ → „ Euro") machte daraus „150- Euro-Bonus" – gesprochen
         ein Stolpern mitten im Begriff. */
      s = s.replace(/(\d)\s*[-–—]\s*€\s*[-–—]\s*/g, '$1-Euro-');
      s = s.replace(/(\d)\s*[-–—]\s*(?:EUR|Euro)\s*[-–—]\s*/gi, '$1-Euro-');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(?:€|Euro\b|EUR\b)/gi, '$1 bis $2 Euro');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*(?:Cent|ct)/gi, '$1 bis $2 Cent');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)\s*%/g, '$1 bis $2 Prozent');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*[-–—]\s*(\d+(?:[.,]\d+)?)/g, '$1 bis $2');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*(?:€|Euro\b|EUR\b)/gi, '$1 Euro');
      s = s.replace(/(?:€|EUR)\s*(\d+(?:[.,]\d+)?)/gi, '$1 Euro');
      s = s.replace(/(\d+(?:[.,]\d+)?)\s*%/g, '$1 Prozent');
      s = s.replace(/\b(\d+)\s*(?:Cent|ct)\b/gi, '$1 Cent');
      s = s.replace(/\b(?:Cent|ct)\/kWh\b/gi, 'Cent pro Kilowattstunde');
      /* „Kilowattstunden (kWh)" – die Klammer wiederholt nur das bereits
         ausgeschriebene Wort: gesprochen entstünde „Kilowattstunden
         Kilowattstunden". */
      s = s.replace(/(Kilowattstunden?)\s*\(kWh\)/gi, '$1');
      /* Nach „pro" und „je" steht im Deutschen der Singular. Die Quelle
         schreibt „Arbeitspreis pro kWh" als Spaltenüberschrift. */
      s = s.replace(/\b(pro|je)\s+kWh\b/gi, '$1 Kilowattstunde');
      s = s.replace(/\b(?:kWh|kwh)\b/g, 'Kilowattstunden');
      s = s.replace(/\b(?:Mbit|MBit|Megabit)\s*\/\s*s\b/gi, 'Megabit pro Sekunde');
      s = s.replace(/\b(?:Gbit|GBit|Gigabit)\s*\/\s*s\b/gi, 'Gigabit pro Sekunde');
      s = s.replace(/\b(?:Mbit|MBit)\b/g, 'Megabit');
      s = s.replace(/\b(?:Gbit|GBit)\b/g, 'Gigabit');
      s = s.replace(/\s*\/\s*s\b/g, ' pro Sekunde');
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
      /* Gleichzeichen: zwischen Zahlen „ergibt", sonst „ist". Ohne Regel
         liest die Stimme „gleich" oder übergeht das Zeichen ganz – in den
         Rechenbeispielen der Artikel ging so der Zusammenhang verloren. */
      s = s.replace(/(\d(?:[.,]\d+)?)\s*=\s*(?=\d)/g, '$1 ergibt ');
      s = s.replace(/([\wäöüßÄÖÜ)\].,])\s*=\s*([\wäöüßÄÖÜ(])/g, '$1 ist $2');
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
    s = s.replace(/\(\s+/g, '(');
    s = s.replace(/\s+\)/g, ')');
    s = s.replace(/\(\s*\)/g, ' ');
    s = s.replace(/\b(Tipp|Hinweis|Achtung|Wichtiger Hinweis|Tip|Note|Warning):\s*\1:/gi, '$1:');
    s = s.replace(/\u0003/g, '-');   // geschützte Zahlenreihen (50-30-20)
    s = s.replace(/\s+([,.;:!?…])/g, '$1');
    s = s.replace(/([,.;:!?…]){2,}/g, '$1');
    s = s.replace(/\s+/g, ' ').trim();
    // Satzschluss garantieren – verhindert gehetzte Übergänge
    if (s && !/[.!?…:,]$/.test(s)) s += '.';
    return s;
  }

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

  /* Satzgrenzen erkennen – abkürzungs- und zahlenfest.
     Ohne die Maskierung trennt der Split an JEDEM Punkt, also auch
     mitten in „z. B.". Fallen „z." und „B." dann in verschiedene
     Sprechhäppchen, sieht die Abkürzungsauflösung sie nie zusammen und
     der Text wird als „… (zum Beispiel." bzw. „z. B." gesprochen.
     Die Kurzfassung hatte diesen Schutz schon immer; der Sprachpfad
     nicht. */
  function sentences(text) {
    return maskSentenceDots(String(text || ''))
      .replace(/([.!?…]+)(["'»)\]]*)(\s+|$)/g, '$1$2\u0001')
      .split('\u0001')
      .map(function (s) { return s.replace(/\u0002/g, '.').trim(); })
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
  var cursor = 0;
  var nextIndex = 0;  // Einheit, die als NÄCHSTE dran ist (Fortsetzen, Keep-Alive)
  var keepAliveId = null;
  var pauseTimer = null;
  var spokenChars = 0;
  var totalChars = 0;
  var prevBtn = doc.getElementById('ff-listen-prev');
  var nextBtn = doc.getElementById('ff-listen-next');
  var remainEl = doc.getElementById('ff-reader-remaining');

  /* ============================================================
     FORTSCHRITTS-ENGINE (v11) — ein Zeiger, drei Quellen, eine Regel
     ------------------------------------------------------------
     Befund 05.09.2026:
       · Der Zeit-Ticker startete erst mit `onstart`. Stimmen, die dieses
         Ereignis spät oder gar nicht liefern (ältere Android-WebViews,
         Safari mit Remote-Stimmen), ließen die Leiste stehen.
       · Die geschätzte Dauer nutzte `unit.effRate`, gesprochen wurde aber
         der auf 0,5–1,25 begrenzte Wert → die Leiste lief der Stimme
         systematisch davon oder hinterher.
       · Die Leiste erreichte nie 100 % (Obergrenze 98,5 %) und sprang am
         Artikelende sofort auf 0 — „fertig" war nie sichtbar.
       · Nach dem Fortsetzen aus der Atempause sprang sie zurück.
     Regeln jetzt:
       1. Der Ticker läuft, sobald die Einheit in die Sprach-Queue geht;
          `onstart` verankert die Schätzung neu (echter Sprechbeginn).
       2. boundary-Ereignisse korrigieren präzise, `onend` setzt exakt.
       3. Der Zeiger ist MONOTON. Zurückgesetzt wird er ausschließlich
          durch Benutzeraktionen (Neustart, Abschnittssprung, Beenden) —
          nie durch ein verspätetes Callback einer alten Wiedergabe.
       4. Am Artikelende wird 100 % gezeigt, kurz gehalten und erst dann
          in den Ruhezustand zurückgesetzt.
  ============================================================ */
  var progressTickerId = null;
  var progressTickerIsRaf = false;
  var progressTickerRun = 0;
  var displayedChars = 0;
  var progressHoldTimer = null;
  var CHARS_PER_MIN_AT_RATE_1 = 1000;
  var PROGRESS_HOLD_MS = 1200;   // „fertig" muss sichtbar sein, nicht aufblitzen
  var PROGRESS_UNIT_CAP = 0.995; // onend setzt exakt auf 1 — nie vorher

  function cancelProgressTicker() {
    if (!progressTickerId) return;
    try {
      if (progressTickerIsRaf && win.cancelAnimationFrame) win.cancelAnimationFrame(progressTickerId);
      else clearTimeout(progressTickerId);
    } catch (e) {}
    progressTickerId = null;
    progressTickerIsRaf = false;
  }

  function cancelProgressHold() {
    if (progressHoldTimer) { clearTimeout(progressHoldTimer); progressHoldTimer = null; }
  }

  function scheduleProgressTick(fn) {
    if (win.requestAnimationFrame && !reducedMotion) {
      progressTickerIsRaf = true;
      progressTickerId = win.requestAnimationFrame(fn);
    } else {
      progressTickerIsRaf = false;
      progressTickerId = setTimeout(fn, reducedMotion ? 250 : 120);
    }
  }

  function paintProgressRatio(ratio) {
    if (!progressBar) return;
    var r = Number(ratio);
    if (!isFinite(r)) r = 0;
    r = Math.max(0, Math.min(1, r));
    progressBar.style.transform = r <= 0 ? 'scaleX(0)' : (r >= 1 ? 'scaleX(1)' : 'scaleX(' + r.toFixed(4) + ')');
  }

  /**
   * Zeiger setzen. `allowBackward` ist NUR für Benutzeraktionen gedacht
   * (Neustart, Abschnittssprung, Fortsetzen aus einer Atempause).
   */
  function setProgressChars(chars, allowBackward) {
    if (!progressBar || !totalChars) return;
    var next = Math.max(0, Math.min(totalChars, chars || 0));
    if (!allowBackward && next < displayedChars) next = displayedChars;
    displayedChars = next;
    paintProgressRatio(displayedChars / totalChars);
  }

  /** Neustart des Zeigers (Neustart, Sprung, Beenden) – hebt die Monotonie auf. */
  function resetProgressChars(chars) {
    cancelProgressTicker();
    cancelProgressHold();
    displayedChars = Math.max(0, Math.min(totalChars, chars || 0));
    paintProgressRatio(totalChars ? displayedChars / totalChars : 0);
  }

  /**
   * Geschätzte Sprechdauer einer Einheit in Millisekunden.
   * Maßgeblich ist das Tempo, das die Utterance WIRKLICH bekommt
   * (`u.rate` ist auf 0,5–1,25 begrenzt) — sonst läuft die Leiste der
   * Stimme systematisch davon.
   */
  function estimatedSpeechMs(unit) {
    if (!unit || !unit.text) return 700;
    var wanted = unit.effRate || quality.rate || 1;
    var rate = Math.max(0.5, Math.min(1.25, wanted));
    var chars = Math.max(1, unit.text.length);
    var ms = (chars / (CHARS_PER_MIN_AT_RATE_1 * rate)) * 60000;
    // Zahlen und sehr dichte Texte brauchen real etwas länger.
    if (/\d/.test(unit.text)) ms *= 1.04;
    if ((unit.words || wordCountOf(unit.text)) > 24) ms *= 1.03;
    return Math.max(450, Math.min(18000, ms));
  }

  /**
   * Ticker für eine Einheit. `reanchor` wird von `onstart` aufgerufen und
   * setzt den Startzeitpunkt auf den echten Sprechbeginn — dadurch holt
   * eine langsam anlaufende Stimme die Leiste wieder ein, statt dass die
   * Leiste vorläuft.
   */
  function startProgressTicker(unit, run) {
    cancelProgressTicker();
    cancelProgressHold();
    if (!progressBar || !totalChars || !unit || !unit.text) return;
    var localRun = ++progressTickerRun;
    var base = typeof unit.startChars === 'number' ? unit.startChars : spokenChars;
    var len = unit.text.length;
    var duration = estimatedSpeechMs(unit);
    var startedAt = Date.now();
    var anchored = false;

    function tick() {
      if (!reading || !playing || run !== playbackRun || localRun !== progressTickerRun) {
        cancelProgressTicker();
        return;
      }
      var frac = duration > 0 ? Math.max(0, (Date.now() - startedAt) / duration) : 1;
      var capped = Math.min(PROGRESS_UNIT_CAP, frac);
      setProgressChars(base + len * capped, false);
      if (capped < PROGRESS_UNIT_CAP) scheduleProgressTick(tick);
      else progressTickerId = null;
    }

    unit._progressReanchor = function () {
      if (anchored) return;
      anchored = true;
      startedAt = Date.now();
    };

    setProgressChars(base, false);
    scheduleProgressTick(tick);
  }

  function finishProgressUnit(unit) {
    cancelProgressTicker();
    if (unit && unit.text) {
      setProgressChars(typeof unit.endChars === 'number' ? unit.endChars : spokenChars + unit.text.length, false);
    }
  }

  /** Artikelende: 100 % zeigen, kurz halten, dann Ruhezustand. */
  function completeProgress() {
    cancelProgressTicker();
    cancelProgressHold();
    if (progressBar && totalChars) {
      displayedChars = totalChars;
      paintProgressRatio(1);
    } else if (progressBar) {
      paintProgressRatio(1);
    }
    progressHoldTimer = setTimeout(function () {
      progressHoldTimer = null;
      displayedChars = 0;
      paintProgressRatio(0);
    }, PROGRESS_HOLD_MS);
  }

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
    studio:   { rate: 0.90, maxChunk: 210, pauseScale: 1.08, pitchShift: 0.00, dynamic: 0.000 },
    premium:  { rate: 0.88, maxChunk: 195, pauseScale: 1.12, pitchShift: 0.00, dynamic: 0.004 },
    standard: { rate: 0.86, maxChunk: 170, pauseScale: 1.18, pitchShift: 0.02, dynamic: 0.012 },
    basic:    { rate: 0.82, maxChunk: 150, pauseScale: 1.28, pitchShift: 0.05, dynamic: 0.022 }
  };
  var quality = { tier: 'standard', rate: 0.86, maxChunk: 170, pauseScale: 1.18, pitchShift: 0.02, dynamic: 0.012 };
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
    'andreas', 'marcus', 'hannes', 'andrew', 'davis', 'liam', 'christoph', 'kasper', 'alfie', 'jason',
    'thorsten', 'karlsson', 'alan', 'troy', 'austin', 'brad', 'bryce', 'northern'
  ];

  var FEMALE_KEYWORDS = [
    'alba', 'anna', 'katja', 'hedda', 'vicki', 'petra', 'marlene', 'ingrid', 'zira', 'hazel', 'samantha', 'victoria',
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
    'florianmultilingual', 'andrewmultilingual', 'brianmultilingual', 'conradneural', 'ryanneural',
    'guymultilingual', 'christopherneural', 'berndneural', 'ralfneural',
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

  /* v8 – Natürlichkeits-Tiers für den Browser-Fallback (04.09.2026):
     Nicht jede „Premium"-Kennung ist gleich wertvoll. Die Multilingual-v2-
     Stimmen (Florian/Andrew/Brian) sind die jüngste Neural-Generation und
     klingen hörbar menschlicher als ältere Desktop-/SAPI-Stimmen; „Natural"
     (Edge/Google) folgt dahinter. Gezählt wird die BESTE Stufe, nicht die
     Summe – sonst gewinnt eine Stimme nur, weil viele Kennungen im Namen
     stehen. Reihenfolge entscheidet, wenn ein Gerät nur einfache Stimmen
     mitbringt. */
  var PREMIUM_TIERS = [
    { score: 85, kw: ['multilingual', 'polyglot'] },
    { score: 70, kw: ['natural'] },
    { score: 60, kw: ['neural', 'neural2', 'wavenet', 'journey'] },
    { score: 50, kw: ['studio', 'enhanced', 'premium', 'high quality', 'highquality'] },
    { score: 40, kw: ['online'] },
    { score: 30, kw: ['siri', 'google'] }
  ];

  function premiumTierBonus(hay) {
    for (var t = 0; t < PREMIUM_TIERS.length; t++) {
      var tier = PREMIUM_TIERS[t];
      for (var k = 0; k < tier.kw.length; k++) {
        if (voiceHas(hay, tier.kw[k]) || hasNeuralToken(hay, tier.kw[k])) return tier.score;
      }
    }
    return 0;
  }
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

  /* v8 – Matcher für zusammengezogene Neural-Stimmnamen (04.09.2026).
     Edge/Chrome melden Azure-Stimmen als EIN Token, z. B. „ConradNeural",
     „FlorianMultilingual", „EmmaMultilingualNeural". Wortgrenzen-Treffer
     (voiceHas) greifen dort nicht: \bconrad\b findet „ConradNeural" nicht.
     Ohne diesen Matcher würden (a) männliche Neural-Stimmen nicht als
     männlich erkannt und (b) weibliche Multilingual-Stimmen nicht
     aussortiert – beides bricht die Nur-Männlich-Garantie.

     Absichtlich ENG gefasst: Ein Präfix-Treffer zählt nur, wenn das Token
     auf eine Neural-Kennung endet (neural/multilingual/natural/online/
     wavenet) und mindestens 10 Zeichen lang ist. Damit trifft „ava" nie
     „Available" und „nora" nie „Norbert" – die klassischen Zufallstreffer
     eines naiven Präfix-Matchings. */
  var NEURAL_TOKEN_SUFFIX = /(neural2?|multilingual|natural|online|wavenet|journey)$/;

  function neuralTokens(hay) {
    var tokens = String(hay || '').toLowerCase().replace(/[_-]+/g, ' ').split(/[^a-zäöüß0-9]+/);
    var out = [];
    for (var i = 0; i < tokens.length; i++) {
      var tok = tokens[i];
      if (tok && tok.length >= 10 && NEURAL_TOKEN_SUFFIX.test(tok)) out.push(tok);
    }
    return out;
  }

  function hasNeuralNamePrefix(hay, names) {
    var tokens = neuralTokens(hay);
    for (var i = 0; i < tokens.length; i++) {
      for (var j = 0; j < names.length; j++) {
        var n = String(names[j] || '').toLowerCase().replace(/[_-]+/g, '');
        if (n.length >= 3 && tokens[i].indexOf(n) === 0) return true;
      }
    }
    return false;
  }

  function hasNeuralToken(hay, kw) {
    var tokens = neuralTokens(hay);
    var needle = String(kw || '').toLowerCase().replace(/[_-]+/g, '');
    if (!needle) return false;
    for (var i = 0; i < tokens.length; i++) {
      if (tokens[i].indexOf(needle) !== -1) return true;
    }
    return false;
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
    var maleHit = false;
    for (var i = 0; i < mk.length; i++) {
      if (voiceHas(hay, mk[i])) { score += 145; maleHit = true; break; }
    }
    var femaleHit = false;
    for (var j = 0; j < FEMALE_KEYWORDS.length; j++) {
      if (voiceHas(hay, FEMALE_KEYWORDS[j])) { score -= 260; femaleHit = true; break; }
    }
    // Zusammengezogene Neural-Namen: „ConradNeural" (männlich) bzw.
    // „EmmaMultilingualNeural" (weiblich) – das Veto hat Vorrang.
    if (!femaleHit && hasNeuralNamePrefix(hay, FEMALE_KEYWORDS)) { score -= 260; femaleHit = true; }
    if (!maleHit && !femaleHit && hasNeuralNamePrefix(hay, KNOWN_MALE_VOICES)) score += 145;
    for (var studio = 0; studio < STUDIO_VOICES.length; studio++) {
      if (voiceHas(hay, STUDIO_VOICES[studio]) || hasNeuralNamePrefix(hay, [STUDIO_VOICES[studio]])) {
        score += 90; break;
      }
    }
    score += premiumTierBonus(hay);
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
    // „EmmaMultilingualNeural", „AvaMultilingual", „KatjaNeural": weibliche
    // Neural-Stimmen tragen den Namen als Präfix eines zusammengezogenen Tokens.
    return hasNeuralNamePrefix(hay, FEMALE_KEYWORDS);
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
    return hasNeuralNamePrefix(hay, KNOWN_MALE_VOICES);
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
      next.rate = Math.max(0.78, next.rate - 0.04 * degradeLevel);
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
    h5:            { rate: 0.95, pitch: 0.93, volume: 0.99, before: 300, after: 200 },
    h6:            { rate: 0.96, pitch: 0.94, volume: 0.98, before: 260, after: 180 },
    p:             { rate: 1.00, pitch: 0.96, volume: 1.00, before: 130, after: 190 },
    lead:          { rate: 0.96, pitch: 0.95, volume: 1.00, before: 180, after: 260 },
    li:            { rate: 1.00, pitch: 0.97, volume: 0.99, before: 110, after: 150 },
    blockquote:    { rate: 0.95, pitch: 0.95, volume: 0.96, before: 340, after: 320 },
    callout:       { rate: 0.95, pitch: 0.93, volume: 1.00, before: 380, after: 320 },
    warning:       { rate: 0.90, pitch: 0.86, volume: 1.00, before: 460, after: 380 },
    'overview-card': { rate: 0.97, pitch: 0.95, volume: 1.00, before: 300, after: 260 },
    'table-intro': { rate: 0.93, pitch: 0.90, volume: 1.00, before: 520, after: 320 },
    'table-row':   { rate: 1.02, pitch: 0.97, volume: 0.98, before: 90,  after: 210 },
    'table-sum':   { rate: 0.94, pitch: 0.91, volume: 1.00, before: 260, after: 300 },
    'table-outro': { rate: 0.94, pitch: 0.92, volume: 1.00, before: 260, after: 360 },
    'overview-title': { rate: 0.92, pitch: 0.90, volume: 1.00, before: 520, after: 300 },
    'overview-note':  { rate: 0.95, pitch: 0.94, volume: 0.98, before: 280, after: 300 },
    intro:         { rate: 0.92, pitch: 0.92, volume: 1.00, before: 0,   after: 520 },
    outro:         { rate: 0.92, pitch: 0.92, volume: 1.00, before: 520, after: 0 }
  };

  function prosodyFor(type) { return PROSODY[type] || PROSODY.p; }

  /* ============================================================
     AUTOMATISCHE LAUTSTÄRKENANPASSUNG (Auto-Gain, v10 · 05.09.2026)
     ------------------------------------------------------------
     Warum: Die Rollen-Prosodie allein erzeugt Lautheitssprünge. Eine
     Tabellenzeile (volume 0.98) direkt nach einer Überschrift (1.00)
     wirkt subjektiv deutlich leiser, weil sie zusätzlich schneller und
     höher gesprochen wird. Umgekehrt „springt“ eine Warnbox heraus.
     Das ist exakt der Punkt, an dem Laien-TTS von einer Verlags-Regie
     unterscheidbar wird.

     Diese Stufe arbeitet wie die Lautheitsregelung eines Sendestudios
     (EBU R128 / ITU-R BS.1770 in Prinzip, nicht in Messgenauigkeit —
     die Web Speech API liefert kein Ausgangssignal zum Messen):

       1. Ziel-Lautheit je Rolle (target) statt starrer Amplitude.
       2. Kompensation der wahrgenommenen Lautheit: schneller/höher
          gesprochene Einheiten werden minimal angehoben, langsam/tief
          gesprochene minimal abgesenkt (Fletcher-Munson-Näherung).
       3. Kurze Einheiten (Tabellenzellen, Aufzählungen) erhalten einen
          kleinen Zuschlag – sie sind sonst „weggehuscht“.
       4. Sprach-Ausgleich DE/EN: EN-Stimmen derselben Familie sind im
          Katalog im Mittel leiser gemastert als DE-Stimmen.
       5. Stimmenklasse: einfache (nicht-neurale) Stimmen klingen dumpfer
          und brauchen mehr Pegel als eine Studio-Neuralstimme.
       6. Sanfte Begrenzung (Soft-Limiter) statt harter Kappung, damit
          nichts verzerrt und nichts unhörbar wird.
       7. Nachbarschafts-Glättung: der Pegelsprung zwischen zwei direkt
          aufeinanderfolgenden Einheiten bleibt unter LOUDNESS_MAX_STEP.

     Ergebnis: eine durchgehend gleich laute Wiedergabe über
     Überschriften, Fließtext, Tabellen und Übersichten hinweg — ohne
     Regler, in beiden Sprachen, auf jedem Gerät.
  ============================================================ */
  var LOUDNESS_TARGET = {
    h2: 1.00, h3: 1.00, h4: 0.99, h5: 0.99, h6: 0.98,
    p: 0.98, lead: 0.99, li: 0.98,
    blockquote: 0.95, callout: 0.99, warning: 1.00,
    'overview-card': 0.99, 'overview-title': 1.00, 'overview-note': 0.96,
    'table-intro': 1.00, 'table-row': 0.99, 'table-sum': 1.00, 'table-outro': 0.99,
    intro: 1.00, outro: 1.00
  };
  // Grenzen der Automatik: nie unhörbar, nie übersteuert.
  var LOUDNESS_FLOOR = 0.72;
  var LOUDNESS_CEIL = 1.00;
  var LOUDNESS_MAX_STEP = 0.06;   // max. Pegelsprung zwischen zwei Einheiten
  var lastLoudness = null;        // zuletzt ausgegebener Pegel (Glättung)

  function loudnessTargetFor(type) {
    var t = LOUDNESS_TARGET[type];
    return t == null ? LOUDNESS_TARGET.p : t;
  }

  /* Soft-Limiter: komprimiert nur oberhalb der Kniepunkt-Schwelle,
     damit laute Rollen sich nicht gegenseitig „plattdrücken“. */
  function softLimit(v) {
    var knee = 0.94;
    if (v <= knee) return v;
    var over = v - knee;
    return knee + over / (1 + over * 3.2);
  }

  /**
   * Automatische Lautstärkenanpassung für eine Sprech-Einheit.
   * Deterministisch (gleiche Eingabe → gleicher Pegel), damit die
   * Tonspur-Parität und die Tests reproduzierbar bleiben.
   */
  function autoVolume(unit, profile, voiceRes, effRate, effPitch) {
    var p = profile || prosodyFor('p');
    var type = (unit && unit.type) || 'p';
    var base = p.volume != null ? p.volume : 1.0;
    var target = loudnessTargetFor(type);

    // 1) Rollen-Ziel und Profil-Amplitude mitteln (Ziel dominiert leicht).
    var v = base * 0.4 + target * 0.6;

    // 2) Wahrnehmungs-Ausgleich für Tempo und Tonlage. Schnell und hoch
    //    gesprochene Passagen wirken leiser -> minimal anheben.
    var rate = effRate || (p.rate || 1);
    var pitch = effPitch == null ? (p.pitch || 1) : effPitch;
    v += Math.max(-0.05, Math.min(0.05, (rate - 0.95) * 0.10));
    v += Math.max(-0.04, Math.min(0.04, (pitch - 0.95) * 0.08));

    // 3) Kurze Einheiten hörbar halten (Tabellenzellen, Listenpunkte).
    var wc = (unit && unit.words) || wordCountOf(unit && unit.text);
    if (wc && wc <= 4) v += 0.03;
    else if (wc && wc <= 8) v += 0.015;

    // 4) Sprach-Ausgleich: EN-Stimmen sind im Mittel leiser gemastert.
    if (unit && unit.lang === 'en') v += 0.02;

    // 5) Stimmenklasse: einfache Stimmen brauchen mehr Pegel.
    var tier = (quality && quality.tier) || 'standard';
    if (tier === 'basic') v += 0.05;
    else if (tier === 'standard') v += 0.025;
    // Nicht eindeutig männliche Stimmen laufen abgesenkt in der
    // männlichen Klangzone – das kostet Lautheit, die hier zurückkommt.
    if (voiceRes && voiceRes.mode && voiceRes.mode !== 'none' && !voiceRes.explicit) v += 0.02;

    // 6) Soft-Limiter + harte Grenzen.
    v = softLimit(v);
    v = Math.max(LOUDNESS_FLOOR, Math.min(LOUDNESS_CEIL, v));

    // 7) Nachbarschafts-Glättung gegen hörbare Pegelsprünge. Nach einer
    //    Gliederungspause (neuer Block) darf der Pegel frei neu ansetzen.
    if (lastLoudness != null && !(unit && unit.firstChunk)) {
      var diff = v - lastLoudness;
      if (diff > LOUDNESS_MAX_STEP) v = lastLoudness + LOUDNESS_MAX_STEP;
      else if (diff < -LOUDNESS_MAX_STEP) v = lastLoudness - LOUDNESS_MAX_STEP;
    }
    v = Math.max(LOUDNESS_FLOOR, Math.min(LOUDNESS_CEIL, v));
    lastLoudness = v;
    return Math.round(v * 1000) / 1000;
  }

  /* ---------- Satzmelodie (v9, 04.09.2026) ----------
     Ein Artikel, der nur aus Feststellungen besteht, klingt wie ein
     Kontoauszug. Deshalb wird jeder Satz auf seine **Emotion** geprüft:
     Fragen steigen in der Tonlage (+0.05) und erhalten mehr Pausenraum
     (+80 ms), Ausrufe werden leicht betont (+0.02 / +50 ms) und beide
     minimal ruhiger gelesen. Werte sind 1:1 mit
     scripts/reader_tts_backends.py (EMO_PITCH/EMO_RATE/EMO_AFTER_MS)
     synchron – das Paritäts-Gate erzwingt diese Gleichheit. */
  var EMO_PITCH = { question: 0.05, exclamation: 0.02, statement: 0.0 };
  var EMO_RATE = { question: 0.985, exclamation: 0.99, statement: 1.0 };
  var EMO_AFTER_MS = { question: 80, exclamation: 50, statement: 0 };

  function emoPitch(emo) { return EMO_PITCH[emo] || 0.0; }
  function emoRate(emo) { var r = EMO_RATE[emo]; return r == null ? 1.0 : r; }
  function emoAfterMs(emo) { return EMO_AFTER_MS[emo] || 0; }


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
  /* v8 – Sprach-Lexika sind mit scripts/reader_tts_backends.py synchron.
     Ein Satz, der in der Tonspur englisch gesprochen wird, muss auch im
     Browser-Fallback englisch erkannt werden (Paritäts-Gate:
     scripts/reader_prosody_parity_check.py). Mehrdeutige Token (in, so,
     per, was, die) fehlen bewusst – sie sind die häufigste Ursache für
     einen falschen Sprachenwechsel mitten im Satz. */
  var EN_SNIFF = {
    about: 1, after: 1, again: 1, against: 1, all: 1, also: 1, although: 1, and: 1, are: 1, article: 1,
    as: 1, at: 1, avoid: 1, be: 1, because: 1, before: 1, between: 1, both: 1, but: 1, by: 1, can: 1,
    cheaper: 1, cheapest: 1, compare: 1, compared: 1, comparison: 1, contract: 1, contracts: 1, cost: 1,
    costing: 1, costs: 1, could: 1, did: 1, do: 1, does: 1, down: 1, during: 1, each: 1, example: 1,
    expensive: 1, fee: 1, fees: 1, few: 1, first: 1, for: 1, from: 1, good: 1, had: 1, has: 1, have: 1,
    he: 1, her: 1, here: 1, higher: 1, his: 1, how: 1, however: 1, if: 1, important: 1, include: 1,
    includes: 1, including: 1, into: 1, is: 1, it: 1, just: 1, know: 1, listen: 1, lower: 1, may: 1,
    might: 1, money: 1, more: 1, most: 1, much: 1, must: 1, need: 1, new: 1, no: 1, not: 1, of: 1, off: 1,
    on: 1, once: 1, only: 1, or: 1, our: 1, out: 1, over: 1, plan: 1, plans: 1, price: 1, prices: 1,
    provider: 1, providers: 1, read: 1, reading: 1, save: 1, saved: 1, saves: 1, saving: 1, savings: 1,
    second: 1, she: 1, should: 1, show: 1, shown: 1, shows: 1, 'so-called': 1, summary: 1, switch: 1,
    switched: 1, tariff: 1, tariffs: 1, than: 1, that: 1, the: 1, their: 1, them: 1, then: 1, there: 1,
    therefore: 1, they: 1, this: 1, through: 1, to: 1, under: 1, up: 1, very: 1, want: 1, we: 1, what: 1,
    when: 1, where: 1, which: 1, while: 1, who: 1, why: 1, will: 1, with: 1, within: 1, without: 1,
    would: 1, yes: 1, you: 1, your: 1
  };
  /* Deutsches Pendant – ebenfalls 1:1 mit dem Generator synchron. */
  var DE_SNIFF = {
    ab: 1, aber: 1, acht: 1, allen: 1, aller: 1, allerdings: 1, alles: 1, als: 1, am: 1, anbieter: 1,
    auch: 1, auf: 1, aus: 1, auto: 1, 'außerdem': 1, bank: 1, bedeutet: 1, bei: 1, beim: 1, bis: 1,
    bitte: 1, bleiben: 1, bleibt: 1, damit: 1, danach: 1, danke: 1, dann: 1, darauf: 1, darf: 1,
    darunter: 1, 'darüber': 1, das: 1, dass: 1, davon: 1, davor: 1, dazu: 1, dein: 1, deine: 1, dem: 1,
    den: 1, der: 1, des: 1, deshalb: 1, dich: 1, die: 1, diese: 1, diesem: 1, diesen: 1, dieser: 1,
    dieses: 1, dir: 1, doch: 1, dort: 1, drei: 1, du: 1, durch: 1, ein: 1, eine: 1, einem: 1, einen: 1,
    einer: 1, eines: 1, er: 1, es: 1, etwas: 1, euch: 1, euro: 1, findest: 1, 'fünf': 1, 'für': 1, gas: 1,
    gegen: 1, geld: 1, gelten: 1, gilt: 1, 'günstige': 1, 'günstiger': 1, haben: 1, hat: 1, hatte: 1,
    haushalt: 1, heizung: 1, heute: 1, hier: 1, ihm: 1, ihn: 1, ihr: 1, ihre: 1, im: 1, immer: 1, ist: 1,
    jahr: 1, jahre: 1, jedoch: 1, jetzt: 1, kann: 1, kannst: 1, karte: 1, kein: 1, keine: 1, konto: 1,
    kosten: 1, kredit: 1, 'können': 1, lauten: 1, lautet: 1, leistung: 1, lohnt: 1, man: 1, manchmal: 1,
    mehr: 1, mein: 1, meine: 1, mich: 1, mit: 1, monat: 1, monate: 1, morgen: 1, muss: 1, musst: 1,
    'müssen': 1, nach: 1, neun: 1, nicht: 1, nichts: 1, nie: 1, noch: 1, nur: 1, oder: 1, oft: 1, ohne: 1,
    preis: 1, prozent: 1, rechnung: 1, schon: 1, sechs: 1, sehr: 1, seit: 1, seitdem: 1, sich: 1, sie: 1,
    sieben: 1, sind: 1, sobald: 1, sofern: 1, sollen: 1, solltest: 1, soweit: 1, spare: 1, sparen: 1,
    spart: 1, strom: 1, tarif: 1, tarife: 1, teuer: 1, teure: 1, trotzdem: 1, um: 1, und: 1, uns: 1,
    unter: 1, unters: 1, vergleich: 1, vergleichst: 1, versicherung: 1, vertrag: 1, viele: 1,
    vielleicht: 1, vier: 1, von: 1, vor: 1, war: 1, waren: 1, wechsel: 1, weil: 1, welche: 1, weniger: 1,
    wenn: 1, werden: 1, wie: 1, wir: 1, wird: 1, wollen: 1, wurde: 1, wurden: 1, 'während': 1, zehn: 1,
    zinsen: 1, zu: 1, zudem: 1, zum: 1, zur: 1, zwei: 1, zwischen: 1, 'über': 1, 'übers': 1
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
    // Tokenizer wie im Generator: nur Buchstaben-Tokens (Ziffern zählen
    // nicht mit, sonst kippt die Verhältnisregel bei „12 Euro").
    var words = (String(sentence || '').toLowerCase().match(/[a-zäöüß']+/g) || []);
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
    /* v8 – Entscheidungsregel identisch zu reader_tts_backends.sniff_lang:
       konservativ umschalten, damit ein deutscher Satz nicht wegen eines
       englischen Fachbegriffs kippt – und ein echter englischer Satz nicht
       deutsch gesprochen wird (Paritäts-Gate prüft beide Seiten). */
    var total = words.length || 1;
    if (baseLang === 'en') {
      if (de >= 2 && de > en) return 'de';
      if (de >= 1 && germ >= 2 && de > en) return 'de';
      if (en === 0 && (germ >= 2 || de / total >= 0.12)) return 'de';
      return 'en';
    }
    if (baseLang === 'de') {
      if (en >= 2 && de === 0) return 'en';
      if (en >= 3 && en > de * 2) return 'en';
      if (en >= 1 && de === 0 && germ === 0 && en / total >= 0.18) return 'en';
      return 'de';
    }
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
    if (words.length > 22) f -= 0.03;
    if (words.length > 32) f -= 0.03;
    if (words.length <= 6 && digits === 0) f += 0.02;
    return Math.min(1.05, Math.max(0.88, f));
  }

  function effectiveRateFor(unit, profile) {
    var base = profile && profile.rate != null ? profile.rate : 1;
    var cf = contentRateFactor(unit.text);
    // Satzmelodie: Fragen minimal ruhiger (0.985), Ausrufe leicht ruhiger
    // (0.99) – 1:1 zu Emo_RATE in scripts/reader_tts_backends.py.
    cf *= emoRate(unit.emo);
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
    base += emoAfterMs(unit.emo);

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
    // Satzmelodie: Fragen steigen (+0.05), Ausrufe werden betont (+0.02).
    if (unit && unit.emo) v += emoPitch(unit.emo);
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

  /* ============================================================
     TABELLEN-MODELL (v11) — eine Struktur für Kopf, Spalten, Zeilen
     ------------------------------------------------------------
     Befund 05.09.2026 (gemessen an echten Artikel-Tabellen):
       · Ohne <thead> wurde die Kopfzeile ALS DATENZEILE gesprochen
         („Anbieter. Zeile 1 von 3. Preis: Preis. Bonus: Bonus.").
       · <tfoot> wurde übersehen – Summenzeilen fehlten komplett.
       · colspan wurde ignoriert – Spaltenzahl und Spaltennamen
         verschoben sich („Öko. Test: 31 Cent. Tarif: 1,5.").
       · Zeilen, deren erste Zelle ein Link war, fielen einem
         Längen-Heuristik-Filter zum Opfer („0 Zeilen").
       · role="table"/"row"/"cell" ohne rowgroup lieferte keine Zeilen.
     Das Modell unten löst Spalten über colspan auf, erkennt Kopf- und
     Summenzeilen strukturell und verwirft nur noch echte Aktionszeilen
     (Zeilen, die AUSSERHALB von Links/Buttons keinen Text tragen).
     Dieselbe Logik steht in scripts/generate_reader_audio.py, damit
     Tonspur und Browser-Reader niemals auseinanderlaufen.
  ============================================================ */
  var TABLE_WRAP_CLASSES = ['ff-table-scroll', 'ff-tv-tablewrap', 'ff-es-tablewrap',
    'wp-block-table', 'table-wrapper', 'table-responsive'];
  var SUM_CLASSES = ['ff-es-sum', 'ff-tv-sum'];
  var SUM_LABEL_RE = /^(summe|gesamt(?:summe|ersparnis)?|insgesamt|zusammen|total|sum|overall|\u03a3|\u2211)\b/i;
  var ARIA_CELL_ROLES = { cell: 1, gridcell: 1, rowheader: 1, columnheader: 1 };

  function cellSpan(cell) {
    var raw = cell && cell.getAttribute ? cell.getAttribute('colspan') : null;
    var n = parseInt(raw, 10);
    return (isFinite(n) && n > 0) ? n : 1;
  }

  function isCellNode(el) {
    if (!el) return false;
    var tag = normTag(el);
    if (tag === 'TD' || tag === 'TH') return true;
    var role = String((el.getAttribute && el.getAttribute('role')) || '').toLowerCase();
    return !!ARIA_CELL_ROLES[role];
  }

  function isRowNode(el) {
    if (!el) return false;
    if (normTag(el) === 'TR') return true;
    return String((el.getAttribute && el.getAttribute('role')) || '').toLowerCase() === 'row';
  }

  function isHeaderCell(el) {
    if (normTag(el) === 'TH') return true;
    return String((el.getAttribute && el.getAttribute('role')) || '').toLowerCase() === 'columnheader';
  }

  /** Zellen einer Zeile MIT aufgelöstem colspan: { col, cell, span }. */
  function rowCellsExpanded(tr) {
    var out = [];
    var col = 0;
    var kids = (tr && tr.children) || [];
    for (var i = 0; i < kids.length; i++) {
      var c = kids[i];
      if (!isCellNode(c)) continue;
      var span = cellSpan(c);
      out.push({ col: col, cell: c, span: span });
      col += span;
    }
    return out;
  }

  function rowGridWidth(tr) {
    var cells = rowCellsExpanded(tr);
    if (!cells.length) return 0;
    var last = cells[cells.length - 1];
    return last.col + last.span;
  }

  function groupHasColumnHeader(groupEl) {
    var kids = (groupEl && groupEl.children) || [];
    for (var i = 0; i < kids.length; i++) {
      var c = kids[i];
      if (String((c.getAttribute && c.getAttribute('role')) || '').toLowerCase() === 'columnheader') return true;
      if (isRowNode(c)) {
        var cells = (c.children) || [];
        for (var j = 0; j < cells.length; j++) if (isHeaderCell(cells[j])) return true;
      }
    }
    return false;
  }

  /** Alle Zeilen in Dokumentreihenfolge: { group: 'head'|'body'|'foot', row }. */
  function tableRows(tableEl) {
    var out = [];
    (function walk(node, group, depth) {
      var kids = (node && node.children) || [];
      for (var i = 0; i < kids.length; i++) {
        var c = kids[i];
        var tag = normTag(c);
        var role = String((c.getAttribute && c.getAttribute('role')) || '').toLowerCase();
        if (tag === 'THEAD' || (role === 'rowgroup' && groupHasColumnHeader(c))) {
          walk(c, 'head', depth + 1);
        } else if (tag === 'TBODY' || tag === 'TFOOT' || role === 'rowgroup') {
          walk(c, tag === 'TFOOT' ? 'foot' : group, depth + 1);
        } else if (tag === 'TR' || role === 'row') {
          out.push({ group: group, row: c });
        } else if (depth < 3 && (tag === 'DIV' || tag === 'SECTION') &&
                   role !== 'table' && role !== 'grid' && role !== 'treegrid') {
          walk(c, group, depth + 1);
        }
      }
    })(tableEl, 'body', 0);
    return out;
  }

  /** Text, der in Links/Buttons steckt (Aktionszeilen-Erkennung). */
  function linkOnlyText(rowEl) {
    var parts = [];
    qsa('a, button', rowEl).forEach(function (a) {
      var t = readableText(a);
      if (t) parts.push(t);
    });
    return parts.join(' ').trim();
  }

  /** Struktur einer Tabelle: { headers, colCount, rows, hasHeaderRow }. */
  function buildTableModel(tableEl) {
    var all = tableRows(tableEl);
    var headRows = [];
    var bodyRows = [];
    all.forEach(function (r) { (r.group === 'head' ? headRows : bodyRows).push(r); });

    /* Ohne <thead>: Die erste Zeile ist genau dann die Kopfzeile, wenn sie
       ausschließlich aus <th>/[role=columnheader] besteht und weitere
       Zeilen folgen. Sonst wird die Kopfzeile als Datenzeile gesprochen. */
    if (!headRows.length && bodyRows.length > 1) {
      var firstCells = rowCellsExpanded(bodyRows[0].row);
      var allHead = firstCells.length > 0;
      firstCells.forEach(function (c) { if (!isHeaderCell(c.cell)) allHead = false; });
      if (allHead) {
        headRows.push(bodyRows.shift());
      }
    }

    /* Spaltennamen: die letzte Kopfzeile gewinnt (die genauere); Lücken
       werden aus den darüberliegenden Kopfzeilen gefüllt (Gruppentitel
       mit colspan). */
    /* Reihenfolge ist entscheidend: Bei gestapelten Kopfzeilen
       (<th colspan="2">Vergleich 2026</th> über <th>Tarif</th><th>Preis</th>)
       ist die UNTERE Zeile die genaue Spaltenbezeichnung. Sie überschreibt
       den Gruppentitel; dieser füllt nur die Lücken, die die untere Zeile
       nicht benennt. */
    var headers = {};
    headRows.forEach(function (hr) {
      rowCellsExpanded(hr.row).forEach(function (c) {
        var txt = readableText(c.cell);
        if (!txt) return;
        for (var k = 0; k < c.span; k++) headers[c.col + k] = txt;
      });
    });

    var colCount = 0;
    headRows.forEach(function (hr) { colCount = Math.max(colCount, rowGridWidth(hr.row)); });
    bodyRows.forEach(function (br) { colCount = Math.max(colCount, rowGridWidth(br.row)); });

    var rows = [];
    bodyRows.forEach(function (br) {
      var tr = br.row;
      var cells = rowCellsExpanded(tr);
      if (!cells.length) return;
      var rowText = readableText(tr);
      if (!rowText) return;

      /* Echte Aktionszeile: AUSSERHALB von Links/Buttons steht nichts.
         Der frühere Test („Rest kürzer als 12 Zeichen") warf auch
         Datenzeilen weg, deren erste Zelle ein Link war. */
      var links = linkOnlyText(tr);
      var rest = rowText;
      if (links) {
        links.split(/\s+/).forEach(function (piece) {
          if (piece) rest = rest.replace(piece, '');
        });
      }
      if (links && !/[^\s\W_]/.test(rest)) return;

      var byCol = {};
      cells.forEach(function (c) { byCol[c.col] = readableText(c.cell); });
      var label = byCol[0] || '';
      var isSum = false;
      if (tr.classList) {
        SUM_CLASSES.forEach(function (cls) { if (tr.classList.contains(cls)) isSum = true; });
      }
      if (br.group === 'foot') isSum = true;
      if (!isSum && label && SUM_LABEL_RE.test(String(label).trim())) isSum = true;

      rows.push({ cols: byCol, label: label, isSum: isSum, el: tr });
    });

    var headerCount = 0;
    Object.keys(headers).forEach(function () { headerCount++; });

    return {
      headers: headers,
      colCount: Math.max(colCount, headerCount, 1),
      rows: rows,
      hasHeaderRow: headRows.length > 0
    };
  }

  /* ---------- Tabellen-Daten-Extraktion (Maximum Barrierefreiheit) ---------- */
  function extractTableSpeechBlocks(tableEl, lang) {
    if (!tableEl) return [];
    var tTexts = I18N[lang] || I18N.de;
    var de = lang !== 'en';

    var model = buildTableModel(tableEl);
    var title = _tableTitle(tableEl, tTexts);

    var colCount = model.colCount;
    var rowCount = model.rows.length;
    var headers = model.headers;

    var tableBlocks = [];
    var introEl = tableEl.closest && tableEl.closest('.ff-table-scroll') ? tableEl.closest('.ff-table-scroll') : tableEl;

    /* Zahlwort-Kongruenz: „1 Spalten" / „1 Zeilen" / „1 minutes" ist der
       klassische Roboter-Verräter. Singular und Plural werden getrennt
       geführt – für Spalten, Zeilen und die Hördauer. */
    var colsText = colCount + ' ' + (de
      ? (colCount === 1 ? 'Spalte' : 'Spalten')
      : (colCount === 1 ? 'column' : 'columns'));
    var rowsText = de
      ? (rowCount === 1 ? 'einer Zeile' : rowCount + ' Zeilen')
      : (rowCount === 1 ? 'one row' : rowCount + ' rows');

    var introRaw = (de
      ? 'Tabelle: ' + title + '. \u00dcbersicht mit ' + colsText + ' und ' + rowsText + '.'
      : 'Table: ' + title + '. Overview with ' + colsText + ' and ' + rowsText + '.');

    var headerCount = 0;
    Object.keys(headers).forEach(function () { headerCount++; });
    if (headerCount) {
      var names = [];
      for (var i = 0; i < colCount; i++) {
        names.push(headers[i] || ((de ? 'Spalte ' : 'Column ') + (i + 1)));
      }
      introRaw += ' ' + tTexts.tableHeaders.replace('{headers}', names.join(', ')) + '.';
    }
    tableBlocks.push({ el: introEl, text: introRaw, lang: lang, type: 'table-intro' });

    model.rows.forEach(function (row, rIdx) {
      var statements = [];
      Object.keys(row.cols).sort(function (a, b) { return a - b; }).forEach(function (col) {
        var val = row.cols[col];
        if (!val) return;
        var c = parseInt(col, 10);
        if (c === 0 && row.label) return; // Zeilentitel wird vorangestellt
        var headerName = headers[c] || (tTexts.column + ' ' + (c + 1));
        statements.push(headerName + ': ' + val);
      });
      if (!statements.length && row.label) statements.push(row.label);
      if (!statements.length) return;

      /* Summenzeilen sind die Pointe einer Einsparübersicht. Sie werden
         angekündigt und ruhiger/betonter gelesen statt als „Zeile 4 von 4"
         unterzugehen. Steht in der ersten Spalte selbst „Summe", sagt die
         Anmoderation das bereits – das Etikett erklingt nicht doppelt. */
      var labelSpoken = (row.isSum && row.label && SUM_LABEL_RE.test(String(row.label).trim())) ? '' : row.label;
      var prefix = labelSpoken ? labelSpoken + '. ' : '';
      var rowRaw;
      if (row.isSum) {
        /* Bei genau einem Wert ist der Spaltenname Ballast:
           „Zusammengerechnet: 450 Euro." statt
           „Zusammengerechnet: Ersparnis: 450 Euro." */
        var sumContent = statements.length === 1
          ? String(statements[0]).replace(/^[^:]{1,40}:\s*/, '')
          : statements.join('. ');
        rowRaw = tTexts.tableSum.replace('{content}', prefix + sumContent) + '.';
      } else if (rowCount === 1) {
        // Bei genau einer Zeile ist „Zeile 1 von 1" überflüssiges Geräusch.
        rowRaw = prefix + statements.join('. ') + '.';
      } else {
        rowRaw = prefix + tTexts.tableRow
          .replace('{row}', (rIdx + 1))
          .replace('{total}', rowCount)
          .replace('{content}', statements.join('. '));
      }

      tableBlocks.push({ el: row.el || introEl, text: rowRaw, lang: lang, type: row.isSum ? 'table-sum' : 'table-row' });
    });

    tableBlocks.push({
      el: introEl,
      text: tTexts.tableOutro.replace('{title}', title),
      lang: lang,
      type: 'table-outro'
    });

    return tableBlocks;
  }

  /** Titel-Kaskade: aria-label → caption → Überschriften-Titel → Überschrift. */
  function _tableTitle(tableEl, tTexts) {
    var title = tableEl.getAttribute && tableEl.getAttribute('aria-label') ? tableEl.getAttribute('aria-label') : '';
    if (!title) {
      var caption = tableEl.querySelector ? tableEl.querySelector('caption') : null;
      if (!caption && tableEl.closest) {
        var fig = tableEl.closest('figure');
        if (fig) caption = fig.querySelector('figcaption');
      }
      if (caption) title = readableText(caption);
    }
    /* Premium-Übersichten tragen ihren Namen in der eigenen Kopfzeile
       (.ff-tv-title / .ff-es-title). */
    if (!title) {
      var wrap = tableEl.closest ? tableEl.closest('.ff-tarifvergleich, .ff-einspar') : null;
      if (wrap) {
        var head = wrap.querySelector('.ff-tv-title, .ff-es-title');
        if (head) title = readableText(head);
      }
    }
    /* Vorangehende Überschrift: Ohne sie hieß jede Markdown-Tabelle im Ohr
       „Übersichtstabelle", obwohl direkt darüber die echte Überschrift steht. */
    if (!title) {
      var startEl = (tableEl.closest && tableEl.closest('.' + TABLE_WRAP_CLASSES.join(', .'))) || tableEl;
      var prev = startEl.previousElementSibling;
      while (prev && !/^H[1-6]$/.test(normTag(prev))) prev = prev.previousElementSibling;
      if (prev && /^H[1-6]$/.test(normTag(prev))) title = readableText(prev);
    }
    if (!title) title = tTexts.tableTitleDefault;
    return title;
  }

  /* ---------- Alle vorlesbaren Blöcke im Artikel sammeln ---------- */
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
      .replace('{duration}', durationPhrase(lang, cfg.readingTime));
    out.push({ el: toolbar, text: introRaw, lang: lang, type: 'intro' });

    // Redaktionelle Vorab-Boxen (Korrektur, Kurzantwort) – sie gehören
    // inhaltlich zum Artikel und müssen hörbar sein.
    preContentBoxes().forEach(function (box) {
      /* Die sichtbare Dachzeile („Kurz & knapp – die Antwort“) wird nicht
         mitgesprochen: Der redaktionelle Cue davor sagt dasselbe. Sonst
         entstünde „Kurzantwort: Kurz & knapp – die Antwort …“. */
      var probe = box.cloneNode ? box.cloneNode(true) : box;
      qsa('.ff-kurzantwort__head, .ff-kurzantwort__label, .ff-kurzantwort__icon', probe).forEach(function (n) {
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

    /* Vollständigkeit auf Agentur-Niveau (v10):
       - h5/h6 gehören zur Gliederung und wurden bisher übersprungen.
       - Die Premium-Übersichten (Tarifvergleich, Einspartabelle) rendern
         ihre Kopfzeile, Unterzeile und Fußnote AUSSERHALB der Tabelle
         (.ff-tv-title/.ff-tv-sub/.ff-tv-footnote bzw. .ff-es-*). Sie
         wurden dadurch nie vorgelesen: Die Hörerin erfuhr weder, welche
         Übersicht folgt, noch den Hinweis darunter. */
    var nodes = qsa([
      'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'blockquote',
      'table', '[role="table"]', '[role="grid"]', '[role="treegrid"]',
      '.ff-table-scroll', '.ff-tv-tablewrap', '.ff-es-tablewrap', '.wp-block-table', '.table-wrapper', '.table-responsive',
      'figure table', 'figure [role="table"]',
      'strong', 'b',
      '.ff-tarif-card', '.ff-einspar-box', '.ff-kurzantwort', '.ff-korrektur', '.callout',
      '.ff-tv-footnote', '.ff-es-footnote'
    ].join(', '), content);

    nodes.forEach(function (el) {
      if (isReaderSkipped(el)) return;
      if (el.closest && el.closest('figure') && !isTableLike(el)) return;

      /* Die Premium-Übersichten liefern DENSELBEN Inhalt zweimal:
         als <table> (Desktop) und als Karten-Stapel (Mobil, per CSS
         umgeschaltet). Beides vorzulesen doppelt jede Zahl. Die Tabelle
         ist die vollständigere Quelle – der Kartenstapel wird stumm. */
      if (el.closest && el.closest('.ff-tv-cards, .ff-es-cards')) return;

      var elLang = (el.getAttribute('lang') || lang).toLowerCase().indexOf('en') === 0 ? 'en' : 'de';

      if (isTableLike(el)) {
        var tbl = innerTable(el);
        if (!tbl || processedTables.indexOf(tbl) !== -1) return;
        processedTables.push(tbl);
        extractTableSpeechBlocks(tbl, elLang).forEach(function (tb) { out.push(tb); });
        return;
      }

      if (el.closest && el.closest('table, .ff-table-scroll, .ff-tv-tablewrap, .ff-es-tablewrap, .wp-block-table, .table-wrapper, .table-responsive')) return;

      if (/^(STRONG|B)$/.test(el.tagName || '')) {
        if (!isStandaloneEmphasis(el)) return;
        var emphText = readableText(el);
        out.push({ el: el, text: emphText.replace(/[\s?!.…]+$/, '') + '.', lang: elLang, type: 'lead' });
        return;
      }

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

      /* Anmoderation und Nachsatz einer Premium-Übersicht: Die Kopfzeile
         kündigt die Übersicht an (ruhiger, tiefer), die Fußnote steht
         danach als redaktioneller Hinweis. */
      var cls = el.classList;
      if (cls && (cls.contains('ff-tv-title') || cls.contains('ff-es-title'))) type = 'overview-title';
      else if (cls && (cls.contains('ff-tv-sub') || cls.contains('ff-es-sub'))) type = 'overview-note';
      else if (cls && (cls.contains('ff-tv-footnote') || cls.contains('ff-es-footnote'))) type = 'overview-note';

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
      if (/^H[23456]$/.test(el.tagName)) {
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
          firstChunk: ci === 0,
          finalChunk: ci === chunks.length - 1,
          startChars: totalChars,
          endChars: totalChars + c.text.length,
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

  /* Restzeit aus DERSELBEN Schätzung wie die Fortschrittsleiste. Zwei
     getrennte Rechenwege (hier Zeichen/Minute, dort effRate) waren der
     Grund, warum Leiste und „noch ca. X Min." auseinanderliefen. */
  function estimateRemaining() {
    if (!remainEl) return;
    var ms = 0;
    var units = 0;
    for (var i = cursor; i < timeline.length; i++) {
      ms += estimatedSpeechMs(timeline[i]) + (timeline[i].after || 0) + (timeline[i].before || 0);
      units++;
    }
    if (!units) { remainEl.textContent = ''; return; }
    var minutes = ms / 60000;
    if (minutes < 0.1) { remainEl.textContent = ''; return; }
    var mm = Math.max(1, Math.round(minutes));
    remainEl.textContent = texts.remaining.replace('{min}', mm);
  }

  function highlightBlock(block) {
    var el = block && block.el ? block.el : null;
    blocks.forEach(function (b) { if (b.el && b.el !== el) b.el.classList.remove('ff-reader-active'); });
    if (!el || el === toolbar) return;
    el.classList.add('ff-reader-active');
    if (!reducedMotion) scrollTo(el, { block: 'center', behavior: 'smooth' });
    else scrollTo(el, { block: 'center' });
  }

  /* Die Markierung folgt dem Text; den Fortschritt besitzt ausschließlich
     die Fortschritts-Engine. Früher setzte highlight() die Leiste bei
     jedem Satz auf spokenChars zurück – beim Fortsetzen aus einer
     Atempause sprang sie dadurch sichtbar nach hinten. */
  function highlight(unit) {
    highlightBlock(unit && unit.block ? unit.block : null);
  }

  function clearHighlight() {
    blocks.forEach(function (b) { if (b.el) b.el.classList.remove('ff-reader-active'); });
    cancelProgressTicker();
    if (remainEl) remainEl.textContent = '';
  }

  function clearPauseTimer() { if (pauseTimer) { clearTimeout(pauseTimer); pauseTimer = null; } }

  var lastEffRate = 1;
  var liveUtterance = null;
  var playbackRun = 0;       // invalidates callbacks from canceled utterances
  var retryCounts = {};
  var voicePollId = null;
  var lastSpeechStartedAt = 0;
  var unitInFlight = false;  // true while a unit is spoken/pending (Keep-Alive-Wache)

  // v7: Kein Android-Sonderweg mehr nötig – Pause/Resume ist jetzt auf
  // allen Plattformen Cancel + Neu-Sprechen (siehe pauseReading).
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
    if (unit && typeof unit.endChars === 'number') spokenChars = unit.endChars;
    else spokenChars += unit && unit.text ? unit.text.length : 0;
    setProgressChars(spokenChars, false);
    speakUnit(index + 1, false);
  }

  function speakUnit(index, isInitial) {
    if (!reading || !speechSupported) return;
    clearPauseTimer();
    if (index >= timeline.length) { endReading(true, true); return; }
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
        // Safari/WebKit bindet eine Stimme nur zuverlässig, wenn Locale und
        // Stimme zusammenpassen. voiceURI wird zusätzlich gesetzt, weil
        // einige ältere WebViews ausschließlich darüber die Stimme auflösen.
        u.lang = voiceRes.voice.lang || (unit.lang === 'en' ? 'en-US' : 'de-DE');
        try { if (voiceRes.voice.voiceURI) u.voiceURI = voiceRes.voice.voiceURI; } catch (e) {}
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
      // Automatische Lautstärkenanpassung (Auto-Gain) statt starrer
      // Rollen-Amplitude: gleicht Tempo, Tonlage, Einheitslänge, Sprache
      // (DE/EN) und Stimmenklasse aus und glättet Pegelsprünge.
      u.volume = Math.max(0.1, Math.min(1.0, autoVolume(unit, p, voiceRes, u.rate, u.pitch)));

      var started = false;
      var settled = false;
      var watchdogTimer = null;
      function clearStartWatchdog() {
        if (watchdogTimer) { clearTimeout(watchdogTimer); watchdogTimer = null; }
      }

      u.onboundary = function (e) {
        if (!reading || !playing || run !== playbackRun || !progressBar || !totalChars) return;
        if (e && typeof e.charIndex === 'number' && e.charIndex >= 0) {
          setProgressChars((typeof unit.startChars === 'number' ? unit.startChars : spokenChars) + e.charIndex, false);
        }
      };

      // Keep a strong reference. Chromium has historically garbage-collected
      // unreferenced utterances before onend, which made long articles stop.
      liveUtterance = u;
      activeUtterances.push(u);
      win.__ff_active_utterance = u;

      function cleanupUtterance() {
        clearStartWatchdog();
        unitInFlight = false;
        var pos = activeUtterances.indexOf(u);
        if (pos !== -1) activeUtterances.splice(pos, 1);
        if (liveUtterance === u) liveUtterance = null;
        if (win.__ff_active_utterance === u) win.__ff_active_utterance = null;
      }

      u.onstart = function () {
        started = true;
        lastSpeechStartedAt = Date.now();
        clearStartWatchdog();
        /* Echter Sprechbeginn: Die Schätzung wird neu verankert, statt den
           Ticker erst jetzt zu starten. Lief der Ticker schon (er beginnt
           mit dem Einreihen in die Queue), holt die Stimme die Leiste
           dadurch ein, anstatt dass die Leiste vorläuft. */
        if (typeof unit._progressReanchor === 'function') unit._progressReanchor();
        else startProgressTicker(unit, run);
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
        finishProgressUnit(unit);
        spokenChars = typeof unit.endChars === 'number' ? unit.endChars : spokenChars + unit.text.length;
        setProgressChars(spokenChars, false);
        /* Fix (aus #169, 04.09.2026): Die nächste Einheit wird VORGEMERKT,
           solange die Atempause läuft. Früher zeigte `cursor` weiter auf die
           bereits gesprochene Einheit – ein Fortsetzen (oder die Keep-Alive-
           Wache) in dieser Lücke sprach denselben Satz ein zweites Mal. */
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
      // this silent failure mode. v7: Das Watchdog feuert NUR, wenn die
      // Engine nachweislich stillsteht (weder speaking noch pending) –
      // eine langsam anlaufende Stimme wird nicht mehr abgewürgt. Die erste
      // Einheit erhält mehr Anlaufzeit (Voice-Streaming, Remote-Stimmen).
      var watchGrace = isInitial ? 2200 : 1400;
      function watchStart() {
        if (!reading || !playing || run !== playbackRun || started) {
          clearStartWatchdog();
          return;
        }
        var busy = false;
        try { busy = !!(synth.speaking || synth.pending); } catch (e) {}
        if (busy) {
          // Engine arbeitet – verlängern statt abbrechen.
          watchdogTimer = setTimeout(watchStart, 1100);
          return;
        }
        try { synth.cancel(); } catch (e) {}
        retryCurrentUnit(index, run, unit);
      }
      watchdogTimer = setTimeout(watchStart, watchGrace);

      try {
        if (synth.paused) synth.resume();
        unitInFlight = true;
        /* Die Leiste läuft ab dem Einreihen in die Queue. Stimmen, die
           `onstart` spät oder nie liefern, frieren den Fortschritt damit
           nicht mehr ein. */
        startProgressTicker(unit, run);
        synth.speak(u);
      } catch (err) {
        unitInFlight = false;
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
    if (!reading) return;
    if (audioMode) { audioJumpToBlock(index); return; }
    if (!timeline.length) return;
    unlockAudioEngine();
    index = Math.max(0, Math.min(timeline.length - 1, index));
    spokenChars = timeline[index] && typeof timeline[index].startChars === 'number' ? timeline[index].startChars : 0;
    if (!spokenChars) { for (var i = 0; i < index; i++) spokenChars += timeline[i].text.length; }
    // Abschnittssprung: bewusste Benutzeraktion, kein Monotonie-Verstoß.
    resetProgressChars(spokenChars);
    clearPauseTimer();
    cancelProgressTicker();
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
    if (!reading) return;
    if (audioMode) { audioJumpBlock(delta); return; }
    if (!timeline.length) return;
    var curBlock = timeline[cursor] ? timeline[cursor].blockIndex : 0;
    var target = Math.max(0, curBlock + delta);
    for (var i = 0; i < timeline.length; i++) {
      if (timeline[i].blockIndex === target) { jumpTo(i); return; }
    }
    if (delta > 0) endReading(true, true);
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
      ms.setActionHandler('seekbackward', function () { jumpTo(audioMode ? audioBlock - 1 : cursor - 1); });
      ms.setActionHandler('seekforward', function () { jumpTo(audioMode ? audioBlock + 1 : cursor + 1); });
    } catch (e) {}
  }

  /* ============================================================
     ZEIT-STANDARD (v7): Vorab vertonte Artikel im HTML5-Player
     ------------------------------------------------------------
     Der Garantie-Kern für „auf ALLEN Geräten & Browsern funktioniert“:
     eine vorab erzeugte MP3-/WAV-Tonspur (männliche DE- & EN-Stimme,
     serverseitig vertont wie bei zeit.de) wird über das native
     <audio>-Element abgespielt. HTML5-Audio läuft identisch auf
     iPhone, iPad, Mac, Android, Windows/Linux und in Chrome, Safari,
     Firefox, Edge – unabhängig von den Stimmen des Betriebssystems.

     Vertrag mit dem Generator (scripts/generate_reader_audio.py):
       cfg.audio = {
         src:    "<url>",
         chunks: [ { b: blockIndex, t0: ms, t1: ms, lang: 'de'|'en' }, … ]
       }
     `b` ist der 0-basierte Block-Index in der Lesereihenfolge
     (0 = Anmoderation, 1..N = Artikelblöcke in DOM-Reihenfolge,
     letzter = Abmoderation) – exakt die Ordnung von collectBlocks().
     Fehlt die Tonspur (noch nicht generiert), bleibt der lokale
     Web-Speech-Pfad als sofortiger, kostenloser Fallback aktiv.
  ============================================================ */
  var audio = null;
  var audioMode = false;
  var audioSrc = '';
  var audioChunks = [];
  var audioCur = -1;
  var audioBlock = 0;

  function initAudio() {
    var a = cfg.audio;
    if (!a) return;
    var url = String(typeof a === 'string' ? a : (a.src || a.de || a.en || ''));
    if (!url) return;
    var elt = null;
    try { elt = doc.createElement('audio'); } catch (e) { return; }
    if (!elt || typeof elt.addEventListener !== 'function') return;
    elt.setAttribute('preload', 'metadata');
    elt.setAttribute('playsinline', '');
    elt.style.display = 'none';
    elt.setAttribute('aria-hidden', 'true');
    try { elt.src = url; } catch (e) { return; }
    audio = elt;
    audioSrc = url;
    audioChunks = (a && a.chunks && a.chunks.length) ? a.chunks : [];
    try { doc.body.appendChild(elt); } catch (e) {}

    elt.addEventListener('timeupdate', audioOnTime);
    elt.addEventListener('play', function() { cancelAudioProgressTicker(); audioProgressLoop(); });
    elt.addEventListener('pause', cancelAudioProgressTicker);
    elt.addEventListener('ended', cancelAudioProgressTicker);
    elt.addEventListener('ended', function () { endReading(true, true); });
    elt.addEventListener('error', function () {
      // Tonspur fehlt/nicht ladbar → sauber auf den lokalen
      // Web-Speech-Pfad zurückfallen, nie stumm bleiben.
      if (!reading) return;
      audioMode = false;
      try { audio.pause(); } catch (e) {}
      endReading(false);
      if (speechSupported) startReading(audioBlock);
      else setStatus(texts.unsupported);
    });
    audioMode = true;
  }

  function audioChunkIndexForBlock(bi) {
    for (var i = 0; i < audioChunks.length; i++) {
      if (audioChunks[i].b === bi) return i;
    }
    return -1;
  }

  function audioSeekBlock(bi) {
    if (!audio) return;
    var ci = audioChunkIndexForBlock(bi);
    var t = 0;
    if (ci >= 0) t = Math.max(0, audioChunks[ci].t0 || 0);
    else if (audio.duration && blocks.length) t = (bi / Math.max(1, blocks.length)) * (audio.duration * 1000);
    try { audio.currentTime = t / 1000; } catch (e) {}
  }

  var audioProgressTickerId = null;
  function cancelAudioProgressTicker() {
    if (audioProgressTickerId) {
      if (win.cancelAnimationFrame && !reducedMotion) win.cancelAnimationFrame(audioProgressTickerId);
      else clearTimeout(audioProgressTickerId);
      audioProgressTickerId = null;
    }
  }

  /** Fortschritt aus der Audiozeit – ein Rechenweg für Anzeige und Restzeit. */
  function audioTotalMs() {
    if (!audio) return 0;
    var duration = audio.duration || 0;
    if (duration && !isNaN(duration) && isFinite(duration) && duration > 0) return duration * 1000;
    if (audioChunks.length && audioChunks[audioChunks.length - 1].t1) return audioChunks[audioChunks.length - 1].t1;
    return 0;
  }

  function paintAudioProgress() {
    if (!audio || !progressBar) return;
    var total = audioTotalMs();
    if (total > 0) paintProgressRatio((audio.currentTime || 0) * 1000 / total);
  }

  function audioOnTime() {
    if (!audio || !reading) return;
    var t = (audio.currentTime || 0) * 1000;
    var total = audioTotalMs();
    if (audioChunks.length) {
      /* Hysterese-freie Blockzuordnung, aber mit sauberem Bereichstest:
         Ohne `break` lief der Index bei Lücken zwischen zwei Blöcken auf
         den letzten Block voraus – die Live-Markierung sprang dann einen
         Absatz weiter, als die Stimme war. */
      var idx = -1;
      for (var i = 0; i < audioChunks.length; i++) {
        if (t >= audioChunks[i].t0 && t < audioChunks[i].t1) { idx = i; break; }
        if (t >= audioChunks[i].t0) idx = i;
      }
      if (idx < 0) idx = 0;
      if (idx !== audioCur) {
        audioCur = idx;
        var bi = audioChunks[idx] ? audioChunks[idx].b : 0;
        if (blocks[bi]) { audioBlock = bi; highlightBlock(blocks[bi]); storeSet(STORE_POS, String(bi)); }
      }
    }
    if (total > 0) {
      paintProgressRatio(t / total);
      displayedChars = 0;  // Tonspur-Modus: Der Zeiger ist zeitbasiert.
      if (remainEl) {
        var rest = Math.max(0, (total - t) / 1000) / 60;
        remainEl.textContent = rest >= 0.1 ? texts.remaining.replace('{min}', Math.max(1, Math.round(rest))) : '';
      }
    }
  }

  function audioProgressLoop() {
    audioOnTime();
    if (!reading || !audio || audio.paused || audio.ended) {
      audioProgressTickerId = null;
      return;
    }
    if (win.requestAnimationFrame && !reducedMotion) {
      audioProgressTickerId = win.requestAnimationFrame(audioProgressLoop);
    } else {
      audioProgressTickerId = setTimeout(audioProgressLoop, 100);
    }
  }

  function audioStart(fromBlock) {
    if (!audio) return;
    audioBlock = typeof fromBlock === 'number' && fromBlock >= 0 ? Math.min(Math.max(0, fromBlock), Math.max(0, blocks.length - 1)) : 0;
    audioCur = -1;
    if (audio.error) {
      // Quelle nicht abspielbar (z. B. Tonspur noch nicht generiert).
      // Sauber auf die lokale Browser-Stimme zurückfallen, nie stumm.
      audioMode = false;
      try { audio.pause(); } catch (e) {}
      endReading(false);
      if (speechSupported) startReading(audioBlock);
      else setStatus(texts.unsupported);
      return;
    }
    audioSeekBlock(audioBlock);
    /* Wiedereinstieg an einer gemerkten Stelle: Die Leiste zeigt sofort
       die richtige Position, statt bis zum ersten timeupdate bei 0 zu
       stehen („Fortschritt springt nach dem Start los"). */
    paintAudioProgress();
    var p = null;
    try { p = audio.play(); } catch (e) { p = null; }
    if (p && p.then) {
      p.catch(function () {
        // Autoplay-Verweigerung ist im Klickkontext selten; einmalig erneut.
        try { audio.play(); } catch (e) {}
      });
    }
  }

  function audioPause() { if (audio) { try { audio.pause(); } catch (e) {} } }
  function audioResume() {
    if (!audio) return;
    var p = null;
    try { p = audio.play(); } catch (e) { p = null; }
    if (p && p.then) p.catch(function () { try { audio.play(); } catch (e) {} });
  }
  function audioStop() {
    if (!audio) return;
    try { audio.pause(); } catch (e) {}
    try { audio.currentTime = 0; } catch (e) {}
  }

  function audioJumpToBlock(bi) {
    if (!audio || !blocks.length) return;
    audioBlock = Math.max(0, Math.min(blocks.length - 1, bi));
    audioCur = -1;
    audioSeekBlock(audioBlock);
    if (audio.paused) {
      try { audio.play(); } catch (e) {}
    }
  }

  function audioJumpBlock(delta) {
    var cur = blocks[audioBlock] ? audioBlock : 0;
    var target = cur + delta;
    if (target < 0) target = 0;
    if (target >= blocks.length) { endReading(true, true); return; }
    audioJumpToBlock(target);
  }

  function blockIndexForEl(target) {
    for (var i = 0; i < blocks.length; i++) {
      var be = blocks[i].el;
      if (be === target || (be && be.contains && be.contains(target))) return i;
    }
    return -1;
  }

  initAudio();

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
    if (audioMode) {
      // ZEIT-Standard: vorab vertonte Tonspur im HTML5-Player. Die Blöcke
      // werden dennoch gesammelt, damit Live-Markierung, Fortschritt,
      // Abschnitts-Navigation und schwebender Player identisch bleiben.
      currentLang = detectArticleLanguage();
      texts = I18N[currentLang] || I18N.de;
      blocks = collectBlocks();
      if (!blocks.length) { setStatus(texts.noText); return; }
      reading = true;
      playing = true;
      spokenChars = 0;
      resetProgressChars(0);
      cursor = 0;
      setListenState('playing');
      setStatus(texts.started);
      setupMediaSession();
      var savedBlock = 0;
      if (typeof fromIndex === 'number' && fromIndex > 0 && fromIndex < blocks.length) savedBlock = fromIndex;
      else { var sv = parseInt(storeGet(STORE_POS) || '0', 10); if (sv > 0 && sv < blocks.length) savedBlock = sv; }
      audioStart(savedBlock);
      return;
    }
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
    lastLoudness = null;   // Auto-Gain: Glättung startet pro Wiedergabe neu
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
    resetProgressChars(0);
    var startIdx = 0;
    if (typeof fromIndex === 'number' && fromIndex > 0 && fromIndex < timeline.length) {
      startIdx = fromIndex;
      spokenChars = timeline[startIdx] && typeof timeline[startIdx].startChars === 'number' ? timeline[startIdx].startChars : 0;
      if (!spokenChars) { for (var i = 0; i < startIdx; i++) spokenChars += timeline[i].text.length; }
    }
    // Wiedereinstieg ist eine Benutzeraktion: Der Zeiger darf hier springen.
    resetProgressChars(spokenChars);
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
    if (audioMode) {
      playing = false;
      audioPause();
      setListenState('paused');
      setStatus(texts.paused);
      return;
    }
    playing = false;
    clearPauseTimer();
    cancelProgressTicker();
    stopVoicePolling();
    // v7 – Verlagsstandard: Pause ist IMMER ein kontrollierter Abbruch mit
    // Positions-Merken. `speechSynthesis.pause()/resume()` ist über die
    // Browser hinweg (Safari Desktop/iOS, Firefox, Android) nachweislich
    // unzuverlässig: Safari „resumed“ eine pausierte Queue ohne hörbaren
    // Ton, Android bricht selbstständig ab. Cancel + Neu-Sprechen der
    // aktuellen Einheit verhält sich dagegen auf ALLEN Plattformen gleich.
    playbackRun += 1; // in-flight Callbacks des alten Utterance invalidieren
    if (speechSupported) {
      try { synth.cancel(); } catch (e) {}
    }
    liveUtterance = null;
    activeUtterances.length = 0;
    unitInFlight = false;
    setListenState('paused');
    setStatus(texts.paused);
  }

  function resumeReading() {
    if (!reading) return;
    if (audioMode) {
      playing = true;
      audioResume();
      setListenState('playing');
      setStatus(texts.resumed);
      return;
    }
    unlockAudioEngine();
    playing = true;
    setListenState('playing');
    setStatus(texts.resumed);
    if (!speechSupported) return;
    // Universal (v7): Pause ist ein kontrollierter Abbruch, Fortsetzen
    // spricht direkt neu – kein `synth.resume()`, keine Sonderfälle pro
    // Browser. Gesprochen wird die Einheit, die als NÄCHSTE dran ist
    // (nextIndex): Pausiert man mitten in einem Satz, ist das der aktuelle
    // Satz; pausiert man in der Atempause NACH einem fertigen Satz, ist es
    // bereits der nächste – der fertige Satz wird nicht doppelt gesprochen
    // (Fix aus #169, 04.09.2026).
    speakUnit(Math.min(nextIndex, timeline.length - 1), true);
  }

  /**
   * @param {boolean} announce  Statusmeldung „Vorlesen beendet." zeigen
   * @param {boolean} completed Artikel wurde bis zum Ende gehört. Dann wird
   *                            100 % gezeigt und kurz gehalten; ein
   *                            manueller Stopp setzt sofort zurück.
   */
  function endReading(announce, completed) {
    if (audioMode) {
      reading = false;
      playing = false;
      audioStop();
      clearHighlight();
      if (completed) completeProgress(); else resetProgressChars(0);
      setListenState('idle');
      storeDel(STORE_POS);
      if (announce) setStatus(texts.finished);
      return;
    }
    reading = false;
    playing = false;
    playbackRun += 1;
    liveUtterance = null;
    unitInFlight = false;
    activeUtterances.length = 0;
    win.__ff_active_utterance = null;
    clearPauseTimer();
    cancelProgressTicker();
    stopVoicePolling();
    stopKeepAlive();
    if (speechSupported) {
      try {
        synth.cancel();
        synth.resume();
      } catch (e) {}
    }
    clearHighlight();
    if (completed) completeProgress(); else resetProgressChars(0);
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
        // unitInFlight verhindert Doppel-Speak: solange eine Einheit in der
        // Queue liegt oder ihre Nachlauf-Pause läuft, greift die Wache nicht.
        if (!synth.speaking && !synth.pending && !pauseTimer && !unitInFlight &&
            Date.now() - lastSpeechStartedAt > 900) {
          // #169-Fix: niemals den bereits fertigen Satz erneut anstoßen
          speakUnit(Math.min(nextIndex, timeline.length - 1), true);
        }
      } catch (e) {}
    }, 5000);
  }

  function stopKeepAlive() { if (keepAliveId) { clearInterval(keepAliveId); keepAliveId = null; } }

  /* ---------- Bedienelemente ---------- */
  listenBtn.addEventListener('click', function () {
    unlockAudioEngine();
    if (!reading) {
      var saved = parseInt(storeGet(STORE_POS) || '0', 10);
      startReading(saved > 0 ? saved : 0);
    } else if (playing) {
      pauseReading();
    } else {
      resumeReading();
    }
  });

  if (stopBtn) stopBtn.addEventListener('click', function () { endReading(true); });
  if (prevBtn) prevBtn.addEventListener('click', function () { jumpBlock(-1); });
  if (nextBtn) nextBtn.addEventListener('click', function () { jumpBlock(1); });

  // Klick-to-Listen: an beliebiger Stelle einsteigen (auch im Ruhezustand)
  var contentContainer = doc.querySelector('.post-content') || doc.querySelector('.md-content');
  if (contentContainer) {
    contentContainer.addEventListener('dblclick', function (e) {
      var target = e.target.closest('tr, table, [role=\"row\"], p, h2, h3, h4, h5, h6, strong, b, li, blockquote, .ff-tarif-card, .ff-einspar-box, .ff-kurzantwort, .callout');
      if (!target) return;
      unlockAudioEngine();
      if (!reading) { startReading(0); }
      if (audioMode) {
        var biA = blockIndexForEl(target);
        if (biA >= 0) audioJumpToBlock(biA);
        return;
      }
      for (var i = 0; i < timeline.length; i++) {
        if (timeline[i].block.el === target || (timeline[i].block.el && timeline[i].block.el.contains(target))) { jumpTo(i); return; }
      }
    });
    contentContainer.addEventListener('click', function (e) {
      if (!reading) return;
      var target = e.target.closest('tr, table, [role=\"row\"], p, h2, h3, h4, h5, h6, strong, b, li, blockquote, .ff-tarif-card, .ff-einspar-box, .ff-kurzantwort, .callout');
      if (!target || e.target.closest('a, button, input, select, textarea')) return;
      /* Fix (aus #169, 04.09.2026): Text markieren und kopieren darf die
         Wiedergabe nicht an eine andere Stelle springen lassen. Eine laufende
         Auswahl wird respektiert – gesprungen wird nur bei einem echten,
         kollabierten Klick. */
      try {
        var sel = win.getSelection && win.getSelection();
        if (sel && !sel.isCollapsed && String(sel.toString() || '').length > 0) return;
      } catch (err) {}
      unlockAudioEngine();
      if (audioMode) {
        var biB = blockIndexForEl(target);
        if (biB >= 0) audioJumpToBlock(biB);
        return;
      }
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


  /* Ehrliche Stimmen-Kennzeichnung (Fix aus #169, 04.09.2026).
     Die Web Speech API kennt kein Geschlechts-Merkmal im Standard. Ob eine
     männliche Stimme existiert, entscheidet allein das Betriebssystem. Der
     Button verspricht deshalb nur dann eine männliche Stimme, wenn auf DIESEM
     Gerät tatsächlich eine gefunden wurde – sonst benennt er neutral die
     Gerätstimme. Barrierefreiheit heißt hier: nichts versprechen, was das
     Gerät nicht einlösen kann. */
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
    if (male) { if (listenBtn.removeAttribute) listenBtn.removeAttribute('title'); }
    else if (listenBtn.setAttribute) listenBtn.setAttribute('title', texts.voiceFallback);
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
  } else if (toolbar.classList && !audioMode) {
    // Nur als „nicht unterstützt“ markieren, wenn es weder Web Speech noch
    // eine vorab vertonte Tonspur gibt. Mit Tonspur funktioniert Vorlesen
    // in jedem Browser (HTML5-Audio).
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
})();
