/* FranksFinanzcheck Premium Blog Enhancements
   Dependencies: optional GSAP. Scroll-based effects use IntersectionObserver to avoid ScrollTrigger forced reflows.
   Privacy: no tracking, no cookies, no external calls except browser-level same-origin prefetch on user intent.
*/
(function () {
  'use strict';

  var doc = document;
  var win = window;
  var root = doc.documentElement;
  var prefersReducedMotion = win.matchMedia && win.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var saveData = navigator.connection && navigator.connection.saveData;
  var rafPending = false;

  function ready(fn) {
    if (doc.readyState === 'loading') {
      doc.addEventListener('DOMContentLoaded', fn, { once: true });
    } else {
      fn();
    }
  }

  function qsa(selector, context) {
    return Array.prototype.slice.call((context || doc).querySelectorAll(selector));
  }

  function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }

  function requestTick(fn) {
    if (rafPending) return;
    rafPending = true;
    win.requestAnimationFrame(function () {
      rafPending = false;
      fn();
    });
  }

  function setupProgressBar() {
    var shell = doc.createElement('div');
    var maxScroll = 1;
    shell.className = 'ff-progress-shell';
    shell.setAttribute('aria-hidden', 'true');
    shell.innerHTML = '<span class="ff-progress-bar"></span>';
    doc.body.appendChild(shell);

    function measure() {
      // Geometry read is batched outside the hot scroll path to avoid forced reflow.
      maxScroll = Math.max(1, root.scrollHeight - win.innerHeight);
    }

    function update() {
      var scrollTop = win.pageYOffset || root.scrollTop || 0;
      var progress = clamp(scrollTop / maxScroll, 0, 1);
      root.style.setProperty('--ff-scroll-progress', progress.toFixed(4));
      doc.body.classList.toggle('ff-scrolled', scrollTop > 10);
    }

    measure();
    update();
    win.addEventListener('scroll', function () { requestTick(update); }, { passive: true });
    win.addEventListener('resize', function () { requestTick(function () { measure(); update(); }); }, { passive: true });
    win.addEventListener('load', function () { requestTick(function () { measure(); update(); }); }, { once: true, passive: true });
  }

  function setupCardPointerGlow() {
    qsa('.post-entry').forEach(function (card) {
      var rect = null;
      function measure() {
        rect = card.getBoundingClientRect();
      }
      card.addEventListener('pointerenter', measure, { passive: true });
      card.addEventListener('pointermove', function (event) {
        // Use cached geometry; never measure layout in the pointermove hot path.
        if (!rect) return;
        card.style.setProperty('--ff-card-x', (event.clientX - rect.left) + 'px');
        card.style.setProperty('--ff-card-y', (event.clientY - rect.top) + 'px');
      }, { passive: true });
      card.addEventListener('pointerleave', function () { rect = null; }, { passive: true });
    });
  }

  function enhanceMoneyHighlights() {
    qsa('.home-info strong').forEach(function (el) {
      if (/€|Euro/i.test(el.textContent)) el.classList.add('ff-money-pop');
    });
  }

  function animateMoneyWithGsap() {
    // LCP/CLS guard: never rewrite numeric hero text. The final amount is
    // present in HTML from first paint; JS may only apply paint-only emphasis.
    if (prefersReducedMotion || !win.gsap) return;
    qsa('.home-info strong').forEach(function (el) {
      win.gsap.fromTo(el,
        { filter: 'brightness(1.24)' },
        { filter: 'brightness(1)', duration: 1.0, ease: 'power2.out', clearProps: 'filter' }
      );
    });
  }

  function isLcpCriticalElement(el) {
    return !!(el && (
      (el.matches && el.matches('[data-ff-lcp="candidate"], .lcp-card')) ||
      (el.querySelector && el.querySelector('[data-ff-lcp="candidate"]')) ||
      (el.closest && el.closest('[data-ff-lcp="candidate"], .lcp-card'))
    ));
  }

  function setupVanillaReveals() {
    if (prefersReducedMotion) return;
    var revealSelector = [
      '.post-entry',
      '.post-content > p',
      '.post-content > ul',
      '.post-content > ol',
      '.post-content > blockquote',
      '.post-content > table',
      '.post-content > h2',
      '.post-content > h3',
      '.md-content > p',
      '.md-content > h2',
      '.md-content > h3',
      '.ff-content-chunk > p',
      '.ff-content-chunk > ul',
      '.ff-content-chunk > ol',
      '.ff-content-chunk > blockquote',
      '.ff-content-chunk > table',
      '.ff-content-chunk > h2',
      '.ff-content-chunk > h3'
    ].join(',');

    var items = qsa(revealSelector).filter(function (el) {
      // Never hide the LCP candidate. Hiding above-the-fold images until an
      // IntersectionObserver callback causes Lighthouse "render delay" even when
      // the image resource has already loaded.
      return !el.closest('.home-info') && !isLcpCriticalElement(el);
    });

    if (!('IntersectionObserver' in win)) {
      items.forEach(function (el) { el.classList.add('ff-in-view'); });
      return;
    }

    items.forEach(function (el) { el.classList.add('ff-will-reveal'); });

    var observer = new IntersectionObserver(function (entries, obs) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('ff-in-view');
        entry.target.classList.remove('ff-will-reveal');
        obs.unobserve(entry.target);
      });
    }, { rootMargin: '0px 0px -12% 0px', threshold: 0.08 });

    items.forEach(function (el) { observer.observe(el); });
  }

  function setupGsapMotion() {
    // Forced-reflow optimizer: do not use ScrollTrigger for blog scroll effects.
    // ScrollTrigger must measure layout for start/end positions; Lighthouse reports
    // that work as forced reflow. IntersectionObserver gives the same editorial
    // reveal feel without synchronous geometry reads.
    if (prefersReducedMotion || !win.gsap) {
      setupVanillaReveals();
      return;
    }

    var gsap = win.gsap;
    gsap.config({ nullTargetWarn: false });

    // LCP text guard: the hero H1/paragraph may become the LCP element.
    // Never hide or move it with JS. Only non-text hero controls get a small
    // opacity-only enhancement after first paint.
    var heroEnhancements = qsa('.ff-home-ctas a, .ff-trust-row span');
    if (heroEnhancements.length) {
      gsap.set(heroEnhancements, { autoAlpha: 0 });
      gsap.timeline({ defaults: { ease: 'power3.out' } })
        .to(heroEnhancements, { autoAlpha: 1, duration: 0.45, stagger: 0.035, clearProps: 'opacity,visibility' });
    }

    setupVanillaReveals();
    animateMoneyWithGsap();
  }

  /* ============================================================
     Abschnitts-Link (Anker-Knopf) — Befund 10.09.2026
     ------------------------------------------------------------
     Der Knopf trug früher ein „§“ als TEXTKNOTEN direkt in der
     Überschrift. Dadurch hing an jeder Überschrift des Blogs ein
     sichtbares „§“ — überall dort, wo der Überschriften-Text
     ausgelesen wird:

       · Kurzfassung → „In diesem Artikel“ (jeder Eintrag mit „§“)
       · Kurzfassung → Tabellen-Titel und Klartext-Kopie
       · Vorlesen-Engine (sprach „… Paragraph“)
       · Mini-Inhaltsverzeichnis (dort notdürftig weggeputzt)
       · Überschriften-Name für Screenreader (WCAG/BITV)
       · Suchmaschinen (Überschriften sind ein Ranking-Signal)

     Reparatur auf Verlagshaus-Niveau:
       · SYMBOL STATT GLYPHE: reines Inline-SVG, kein Textknoten
       · `data-ff-skip-read`: Lesemaschinen überspringen den Knopf
       · `.ff-heading-text` + `aria-labelledby`: nur der echte
         Überschriften-Text beschriftet die Überschrift
     ============================================================ */
  var COPY_LABEL = 'Link zu diesem Abschnitt kopieren';
  var COPIED_LABEL = 'Link kopiert';
  var LINK_ICON = '<svg class="ff-heading-copy__ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
    + '<path d="M9.5 14.5 14.5 9.5"></path>'
    + '<path d="M11 6.5 12.6 4.9a4.2 4.2 0 0 1 5.9 5.9L17 12.5"></path>'
    + '<path d="M13 17.5 11.4 19.1a4.2 4.2 0 0 1-5.9-5.9L7 11.5"></path></svg>';
  var CHECK_ICON = '<svg class="ff-heading-copy__ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">'
    + '<path d="M20 6 9 17l-5-5"></path></svg>';
  var headingUid = 0;

  function hasCls(el, name) {
    return !!(el && el.classList && el.classList.contains(name));
  }

  /** Reiner Überschriften-Text – ohne Ankersymbol, ohne Kopierknopf. */
  function headingText(heading) {
    if (!heading) return '';
    var label = null;
    var kids = heading.children || [];
    for (var i = 0; i < kids.length; i++) {
      if (hasCls(kids[i], 'ff-heading-text')) { label = kids[i]; break; }
    }
    var text = String((label || heading).textContent || '');
    return text.replace(/[\s#§]+$/g, '').replace(/\s+/g, ' ').trim();
  }

  /**
   * Fasst den echten Überschriften-Text in ein eigenes Etikett.
   * Nur dieses Etikett beschriftet die Überschrift (aria-labelledby),
   * damit Anker und Kopierknopf den Namen nicht verunstalten.
   */
  function headingLabel(heading) {
    var kids = heading.children || [];
    for (var i = 0; i < kids.length; i++) {
      if (hasCls(kids[i], 'ff-heading-text')) return kids[i];
    }
    var label = doc.createElement('span');
    label.className = 'ff-heading-text';
    var move = [];
    for (var j = 0; j < heading.childNodes.length; j++) {
      var node = heading.childNodes[j];
      if (node.nodeType !== 1) { move.push(node); continue; }
      if (node.hasAttribute('hidden')) continue;
      if (node.getAttribute('aria-hidden') === 'true') continue;
      if (hasCls(node, 'anchor') || hasCls(node, 'ff-heading-copy') || hasCls(node, 'ff-heading-text')) continue;
      move.push(node);
    }
    for (var k = 0; k < move.length; k++) label.appendChild(move[k]);
    if (heading.firstChild) heading.insertBefore(label, heading.firstChild);
    else heading.appendChild(label);

    var id = (heading.id || 'ff-heading') + '-label';
    while (doc.getElementById(id)) id = id + '-' + (++headingUid);
    label.setAttribute('id', id);
    return label;
  }

  function addHeadingCopyButtons() {
    qsa('.post-content h2[id], .post-content h3[id], .md-content h2[id], .md-content h3[id]').forEach(function (heading) {
      if (heading.querySelector('.ff-heading-copy')) return;
      var label = headingLabel(heading);
      if (!heading.getAttribute('aria-labelledby')) heading.setAttribute('aria-labelledby', label.id);

      var button = doc.createElement('button');
      button.className = 'ff-heading-copy';
      button.type = 'button';
      button.setAttribute('aria-label', COPY_LABEL);
      button.setAttribute('title', COPY_LABEL);
      button.setAttribute('data-ff-skip-read', '');
      button.innerHTML = LINK_ICON;
      button.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        var url = win.location.origin + win.location.pathname + '#' + heading.id;
        var done = function () {
          button.classList.add('ff-copied');
          button.innerHTML = CHECK_ICON;
          button.setAttribute('aria-label', COPIED_LABEL);
          setTimeout(function () {
            button.classList.remove('ff-copied');
            button.innerHTML = LINK_ICON;
            button.setAttribute('aria-label', COPY_LABEL);
          }, 1500);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(url).then(done).catch(function () { win.location.hash = heading.id; });
        } else {
          win.location.hash = heading.id;
          done();
        }
      });
      heading.appendChild(button);
    });
  }

  /* ============================================================
     SCHWEBENDE ARTIKEL-NAVIGATION „Im Artikel“ (Desktop)
     ------------------------------------------------------------
     Befund 26.09.2026 (Frank, Tierkrankenversicherungs-Artikel):
     Das Verzeichnis listete hart nur die ERSTEN 9 H2-Abschnitte.
     Lange Ratgeber (hier 24 Abschnitte) brachen dadurch mitten im
     Text ab – „Fazit“ und „Häufige Fragen“ tauchten nie auf, und
     der Leser sah beim Scrollen keinen aktiven Eintrag mehr, weil
     die markierte Überschrift längst unterhalb der Liste lag.
     Zusätzlich lief das Kästchen auf mittleren Desktops (1241 px
     bis ~1600 px) in den Textkörper hinein.

     Premium-Reparatur (Profi-Agentur-Niveau):
       1. VOLLSTÄNDIG: alle H2-Abschnitte, kein stilles Abschneiden.
       2. Kopfzeile bleibt stehen, die Liste darunter scrollt
          (eigener Scroll-Container, Fade-Kanten per CSS).
       3. Fortschritt: „7 / 24“ + feiner Fortschrittsbalken.
       4. Ehrliche Lesemarke: scrollbasierte Positionsbestimmung
          (die letzte Überschrift oberhalb der Lesezone) statt
          IntersectionObserver – bei sehr langen Abschnitten blieb
          dort sonst gar kein Eintrag markiert.
       5. Selbstnachführung: der aktive Eintrag wird innerhalb der
          Liste sichtbar gehalten, ohne die Seite zu bewegen.
       6. Ruhige Zeilen: lange Überschriften werden am Doppelpunkt
          bzw. an der Wortgrenze gekürzt; `aria-label` und `title`
          tragen IMMER den vollen Überschriftentext (Label-Vertrag
          der „§“-Wache, scripts/ff_heading_glyph_guard_test.mjs).
     ============================================================ */

  /** Ruhiges Kurz-Etikett für die schmale Spalte.
      Der volle Text bleibt in aria-label/title erhalten. */
  function miniTocLabel(label) {
    var text = String(label || '').replace(/\s+/g, ' ').trim();
    if (text.length <= 34) return text;
    // „Fazit: Gute Tierabsicherung ist eine Budgetentscheidung“ → „Fazit“
    var colon = text.indexOf(': ');
    if (colon >= 4 && colon <= 30) return text.slice(0, colon);
    if (text.length <= 52) return text;
    // Sauber an der Wortgrenze kürzen statt mitten im Wort abschneiden
    var cut = text.slice(0, 50);
    var space = cut.lastIndexOf(' ');
    if (space > 28) cut = cut.slice(0, space);
    return cut.replace(/[\s,;:–-]+$/, '') + '…';
  }

  function createMiniToc() {
    // /posts/ ist eine Übersicht, kein Artikel. Der schwebende Artikel-ToC
    // würde die Themenkarten überdecken und nur die nachgelagerte FAQ zeigen.
    if (doc.querySelector('.ff-posts-index')) return;
    var content = doc.querySelector('.post-content');
    if (!content || doc.querySelector('.ff-mini-toc')) return;

    var headings = qsa('h2[id]', content).filter(function (h) {
      return headingText(h).length > 0;
    });
    if (headings.length < 3) return;

    var nav = doc.createElement('nav');
    // Start im Ruhzustand (ff-mini-toc--idle): Die Navigation blendet sich
    // erst ein, wenn der Lesende im Artikelkörper angekommen ist – der
    // Newsletter-Kopf über dem Artikel bleibt vollständig frei (Befund
    // 26.09.2026: die schwebende Box überlappte den 1024 px breiten Kopf-
    // Streifen samt „Newsletter abonnieren“-Knopf um 104 px). Ohne JS wird
    // die Navigation gar nicht erst erzeugt → kein no-JS-Sonderfall.
    nav.className = 'ff-mini-toc ff-mini-toc--idle';
    nav.setAttribute('aria-label', 'Artikel-Navigation');
    if (headings.length > 9) nav.classList.add('ff-mini-toc--long');

    var head = doc.createElement('div');
    head.className = 'ff-mini-toc__head';

    var title = doc.createElement('strong');
    title.className = 'ff-mini-toc__title';
    title.textContent = 'Im Artikel';
    head.appendChild(title);

    var counter = doc.createElement('span');
    counter.className = 'ff-mini-toc__count';
    counter.setAttribute('aria-hidden', 'true');
    var posEl = doc.createElement('span');
    posEl.className = 'ff-mini-toc__pos';
    posEl.textContent = '1';
    counter.appendChild(posEl);
    counter.appendChild(doc.createTextNode(' / ' + headings.length));
    head.appendChild(counter);

    var rail = doc.createElement('span');
    rail.className = 'ff-mini-toc__rail';
    rail.setAttribute('aria-hidden', 'true');
    rail.innerHTML = '<span class="ff-mini-toc__railfill"></span>';
    head.appendChild(rail);

    nav.appendChild(head);

    var list = doc.createElement('div');
    list.className = 'ff-mini-toc__list';
    nav.appendChild(list);

    var links = headings.map(function (heading) {
      var a = doc.createElement('a');
      a.href = '#' + heading.id;
      // Sauberer Überschriften-Text: Ankersymbol und Kopierknopf bleiben
      // draußen (Befund 10.09.2026 – das „§“ stand hier früher im Text).
      var label = headingText(heading);
      // Der volle Text ist der Label-Vertrag (Screenreader + Wächter-Test),
      // sichtbar ist die ruhige Kurzform.
      a.setAttribute('aria-label', label);
      a.setAttribute('title', label);
      // Premium hanging indent: split the leading "N." off the label so the
      // wrapped lines of the title align with the first word after the number
      // (grid columns in .ff-mini-toc a.ff-mini-toc--num, see z-premium-blog.css).
      var m = /^(\d{1,3}\.)\s+(.+)$/.exec(label);
      if (m) {
        a.className = 'ff-mini-toc--num';
        var num = doc.createElement('span');
        num.className = 'ff-mini-toc__num';
        num.textContent = m[1];
        num.setAttribute('aria-hidden', 'true');
        var txt = doc.createElement('span');
        txt.className = 'ff-mini-toc__txt';
        txt.textContent = miniTocLabel(m[2]);
        a.appendChild(num);
        a.appendChild(txt);
      } else {
        a.textContent = miniTocLabel(label);
      }
      list.appendChild(a);
      return a;
    });

    doc.body.appendChild(nav);
    setupMiniTocSpy(nav, list, headings, links, posEl, content);
  }

  /** Lesemarke, Zähler, Fortschritt und Selbstnachführung der Liste. */
  function setupMiniTocSpy(nav, list, headings, links, posEl, content) {
    var offsets = [];
    var activeIndex = -1;
    var ticking = false;

    /* ------------------------------------------------------------
       LESEFENSTER (Reparatur 26.09.2026, „verdeckt“-Meldung)
       Die schwebende Navigation darf NIE etwas überdecken:
       · Sie erscheint erst, wenn der Artikelkörper die obere Zone
         erreicht hat (Newsletter-Kopf, Titel, Cover bleiben frei).
       · Sie zieht sich zurück, bevor der Seitenfuß (Footer,
         Pinterest-/Newsletter-Block) die Zone betritt.
       · Sie weicht dem Consent-Banner aus (kurze Viewports).
       Geometrie wird NUR in measure() gelesen (kein Layout-Thrashing
       im Scroll-Pfad); im Scroll-Frame ist alles reine Arithmetik.
       ------------------------------------------------------------ */
    var IDLE_CLASS = 'ff-mini-toc--idle';
    var EDGE_CUSHION = 24;
    var zoneTop = 0;          // Viewport-Oberkante der Box (fix)
    var zoneHeight = 0;       // Höhe ohne Transform (offsetHeight)
    var contentTop = Infinity;   // Dokument-Kante Artikelkörper
    var exitTop = Infinity;      // Dokument-Kante Seitenfuß
    var consentBanner = doc.getElementById('ff-consent-banner');
    var consentTop = Infinity;   // Viewport-Kante des Banners (fix, gecacht)
    var idle = true;

    function measureWindow() {
      // Position:fixed → top aus dem Stylesheet ist die Viewport-Kante.
      // offsetHeight bleibt von transform:translateY unberührt.
      zoneTop = parseFloat(win.getComputedStyle(nav).top) || 0;
      zoneHeight = nav.offsetHeight || 0;
      var pageY = win.pageYOffset || root.scrollTop || 0;
      if (content) {
        contentTop = content.getBoundingClientRect().top + pageY;
      }
      // Erster Vollbreiten-Block am Seitenende, der die Zone von unten
      // betreten könnte. Alles Spalteninnere (max 768 px) kann die Box
      // geometrisch nicht erreichen – der Fuß-Zone reicht die erste Kante.
      exitTop = Infinity;
      qsa('footer.footer, .newsletter-footer.ff-nl-strip:not(.ff-nl-top), .pinterest-footer, .ff-consent-wrap').forEach(function (el) {
        var top = el.getBoundingClientRect().top + pageY;
        if (top && top < exitTop) exitTop = top;
      });
      // Consent-Banner: fixed → Kante nur in der Messphase lesen, im
      // Scroll-Pfad zählt reine Arithmetik (kein Forced Reflow).
      consentTop = Infinity;
      if (consentBanner && consentBanner.getBoundingClientRect().height > 0) {
        consentTop = consentBanner.getBoundingClientRect().top;
      }
    }

    /** Consent-Banner sichtbar UND ragt in die Box-Zone? (kurze Viewports) */
    function consentBlocks() {
      if (!consentBanner || consentTop === Infinity) return false;
      if (root.classList.contains('ff-consent-set')) return false;
      if (consentBanner.style.display === 'none') return false;
      return consentTop < zoneTop + zoneHeight + 8;
    }

    /** Sichtbarkeit aus reiner Arithmetik (kein Geometrie-Lesen). */
    function updateWindow() {
      var pageY = win.pageYOffset || root.scrollTop || 0;
      var inArticle = pageY + zoneTop + EDGE_CUSHION >= contentTop;
      var beforeExit = pageY + zoneTop + zoneHeight + EDGE_CUSHION <= exitTop;
      var show = inArticle && beforeExit && !consentBlocks();
      if (show === !idle) return;
      idle = !show;
      nav.classList.toggle(IDLE_CLASS, idle);
    }

    function measure() {
      var pageY = win.pageYOffset || root.scrollTop || 0;
      offsets = headings.map(function (h) {
        return h.getBoundingClientRect().top + pageY;
      });
    }

    /** Hält den aktiven Eintrag im sichtbaren Teil der Liste – ohne die
        Seite selbst zu scrollen (kein scrollIntoView). */
    function keepVisible(link) {
      if (!link || typeof list.scrollTop !== 'number') return;
      var viewTop = list.scrollTop;
      var viewBottom = viewTop + list.clientHeight;
      var top = link.offsetTop;
      var bottom = top + link.offsetHeight;
      var pad = 24;
      var target = null;
      if (top - pad < viewTop) target = Math.max(0, top - pad);
      else if (bottom + pad > viewBottom) target = bottom + pad - list.clientHeight;
      if (target === null) return;
      if (!prefersReducedMotion && typeof list.scrollTo === 'function') {
        try { list.scrollTo({ top: target, behavior: 'smooth' }); return; } catch (e) { /* ältere Engines */ }
      }
      list.scrollTop = target;
    }

    function update() {
      if (!offsets.length) return;
      var pageY = win.pageYOffset || root.scrollTop || 0;
      var readLine = pageY + Math.min(180, win.innerHeight * 0.28);
      var index = 0;
      for (var i = 0; i < offsets.length; i++) {
        if (offsets[i] <= readLine) index = i;
      }
      // Am Seitenende gehört die Marke auf den letzten Abschnitt.
      if (pageY + win.innerHeight >= root.scrollHeight - 8) index = offsets.length - 1;
      updateWindow();
      if (index === activeIndex) return;
      activeIndex = index;
      for (var j = 0; j < links.length; j++) {
        links[j].setAttribute('aria-current', j === index ? 'true' : 'false');
        if (j < index) links[j].classList.add('ff-mini-toc--past');
        else links[j].classList.remove('ff-mini-toc--past');
      }
      posEl.textContent = String(index + 1);
      nav.style.setProperty('--ff-toc-progress', ((index + 1) / links.length).toFixed(4));
      // Selbstnachführung nur im sichtbaren Zustand – im Ruhzustand würde
      // smooth-scroll im verborgenen Listen-Container nur Rechenzeit kosten.
      if (!idle) keepVisible(links[index]);
    }

    function onScroll() {
      if (ticking) return;
      ticking = true;
      win.requestAnimationFrame(function () {
        ticking = false;
        update();
      });
    }

    function remeasure() {
      measure();
      measureWindow();
      activeIndex = -1;
      update();
    }

    measure();
    measureWindow();
    update();
    win.addEventListener('scroll', onScroll, { passive: true });
    win.addEventListener('resize', remeasure, { passive: true });
    win.addEventListener('load', remeasure, { once: true, passive: true });
    if (doc.fonts && doc.fonts.ready && typeof doc.fonts.ready.then === 'function') {
      doc.fonts.ready.then(remeasure).catch(function () { /* egal */ });
    }
  }

  function setupIntentPrefetch() {
    if (saveData) return;
    var prefetched = new Set();
    var maxPrefetches = 12;

    function canPrefetch(anchor) {
      if (!anchor || !anchor.href || prefetched.size >= maxPrefetches) return false;
      var url = new URL(anchor.href, win.location.href);
      return url.origin === win.location.origin &&
        url.pathname !== win.location.pathname &&
        !url.hash &&
        !/\.(pdf|jpg|jpeg|png|webp|avif|gif|svg|zip|mp3|mp4)$/i.test(url.pathname);
    }

    function prefetch(anchor) {
      if (!canPrefetch(anchor)) return;
      var href = new URL(anchor.href, win.location.href).href;
      if (prefetched.has(href)) return;
      prefetched.add(href);
      var link = doc.createElement('link');
      link.rel = 'prefetch';
      link.as = 'document';
      link.href = href;
      doc.head.appendChild(link);
    }

    doc.addEventListener('mouseover', function (event) {
      var anchor = event.target.closest && event.target.closest('a[href]');
      if (anchor) prefetch(anchor);
    }, { passive: true });

    doc.addEventListener('focusin', function (event) {
      var anchor = event.target.closest && event.target.closest('a[href]');
      if (anchor) prefetch(anchor);
    });

    doc.addEventListener('touchstart', function (event) {
      var anchor = event.target.closest && event.target.closest('a[href]');
      if (anchor) prefetch(anchor);
    }, { passive: true });
  }

  ready(function () {
    root.classList.add('ff-premium-ready');
    setupProgressBar();
    setupCardPointerGlow();
    enhanceMoneyHighlights();
    addHeadingCopyButtons();
    createMiniToc();
    setupIntentPrefetch();
    setupGsapMotion();
  });
})();
