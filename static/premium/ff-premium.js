/* FranksFinanzcheck Premium Blog Enhancements
   Dependencies: optional GSAP + ScrollTrigger. Without them this file falls back to vanilla IntersectionObserver.
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
    shell.className = 'ff-progress-shell';
    shell.setAttribute('aria-hidden', 'true');
    shell.innerHTML = '<span class="ff-progress-bar"></span>';
    doc.body.appendChild(shell);

    function update() {
      var scrollTop = win.pageYOffset || root.scrollTop || 0;
      var maxScroll = Math.max(1, root.scrollHeight - win.innerHeight);
      var progress = clamp(scrollTop / maxScroll, 0, 1);
      root.style.setProperty('--ff-scroll-progress', progress.toFixed(4));
      doc.body.classList.toggle('ff-scrolled', scrollTop > 10);
    }

    update();
    win.addEventListener('scroll', function () { requestTick(update); }, { passive: true });
    win.addEventListener('resize', function () { requestTick(update); }, { passive: true });
  }

  function setupCardPointerGlow() {
    qsa('.post-entry').forEach(function (card) {
      card.addEventListener('pointermove', function (event) {
        var rect = card.getBoundingClientRect();
        card.style.setProperty('--ff-card-x', (event.clientX - rect.left) + 'px');
        card.style.setProperty('--ff-card-y', (event.clientY - rect.top) + 'px');
      }, { passive: true });
    });
  }

  function enhanceMoneyHighlights() {
    qsa('.home-info strong').forEach(function (el) {
      if (/€|Euro/i.test(el.textContent)) el.classList.add('ff-money-pop');
    });
  }

  function animateMoneyWithGsap() {
    if (prefersReducedMotion || !win.gsap) return;
    qsa('.home-info strong').forEach(function (el) {
      var text = el.textContent;
      var match = text.match(/(\d[\d\.\s]*)(\s*(?:€|Euro))/i);
      if (!match) return;

      var target = parseInt(match[1].replace(/\D/g, ''), 10);
      if (!target || target > 1000000) return;

      var suffix = match[2].trim().replace(/^Euro$/i, 'Euro');
      var state = { value: 0 };
      var format = new Intl.NumberFormat('de-DE');

      win.gsap.to(state, {
        value: target,
        duration: 1.25,
        ease: 'power2.out',
        scrollTrigger: win.ScrollTrigger ? {
          trigger: el,
          start: 'top 88%',
          once: true
        } : undefined,
        onUpdate: function () {
          el.textContent = format.format(Math.round(state.value)) + ' ' + suffix;
        }
      });
    });
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
      '.md-content > h3'
    ].join(',');

    var items = qsa(revealSelector).filter(function (el) {
      return !el.closest('.home-info');
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
    if (prefersReducedMotion || !win.gsap || !win.ScrollTrigger) {
      setupVanillaReveals();
      return;
    }

    var gsap = win.gsap;
    var ScrollTrigger = win.ScrollTrigger;
    gsap.registerPlugin(ScrollTrigger);
    gsap.config({ nullTargetWarn: false });

    var heroItems = qsa('.home-info .entry-header h1, .home-info .entry-content p, .ff-home-ctas a, .ff-trust-row span');
    if (heroItems.length) {
      gsap.set(heroItems, { autoAlpha: 0, y: 24 });
      gsap.timeline({ defaults: { ease: 'power3.out' } })
        .to(heroItems, { autoAlpha: 1, y: 0, duration: 0.72, stagger: 0.06, clearProps: 'transform,opacity,visibility' });
    }

    qsa('.post-entry').forEach(function (el, index) {
      gsap.from(el, {
        autoAlpha: 0,
        y: 34,
        duration: 0.78,
        delay: Math.min(index * 0.025, 0.16),
        ease: 'power3.out',
        scrollTrigger: {
          trigger: el,
          start: 'top 88%',
          once: true
        }
      });
    });

    qsa('.post-content > p, .post-content > ul, .post-content > ol, .post-content > blockquote, .post-content > table, .post-content > h2, .post-content > h3').forEach(function (el) {
      gsap.from(el, {
        autoAlpha: 0,
        y: 26,
        duration: 0.66,
        ease: 'power3.out',
        scrollTrigger: {
          trigger: el,
          start: 'top 90%',
          once: true
        }
      });
    });

    qsa('.entry-cover img').forEach(function (img) {
      gsap.to(img, {
        yPercent: -3,
        scale: 1.045,
        ease: 'none',
        scrollTrigger: {
          trigger: img,
          start: 'top bottom',
          end: 'bottom top',
          scrub: true
        }
      });
    });

    animateMoneyWithGsap();
  }

  function addHeadingCopyButtons() {
    qsa('.post-content h2[id], .post-content h3[id], .md-content h2[id], .md-content h3[id]').forEach(function (heading) {
      if (heading.querySelector('.ff-heading-copy')) return;
      var button = doc.createElement('button');
      button.className = 'ff-heading-copy';
      button.type = 'button';
      button.setAttribute('aria-label', 'Link zu diesem Abschnitt kopieren');
      button.innerHTML = '§';
      button.addEventListener('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
        var url = win.location.origin + win.location.pathname + '#' + heading.id;
        var done = function () {
          button.classList.add('ff-copied');
          button.setAttribute('aria-label', 'Link kopiert');
          setTimeout(function () {
            button.classList.remove('ff-copied');
            button.setAttribute('aria-label', 'Link zu diesem Abschnitt kopieren');
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

  function createMiniToc() {
    var content = doc.querySelector('.post-content');
    if (!content || doc.querySelector('.ff-mini-toc')) return;

    var headings = qsa('h2[id]', content).filter(function (h) {
      return h.textContent.trim().length > 0;
    });
    if (headings.length < 3) return;

    var nav = doc.createElement('nav');
    nav.className = 'ff-mini-toc';
    nav.setAttribute('aria-label', 'Artikel-Navigation');
    nav.innerHTML = '<strong class="ff-mini-toc__title">Im Artikel</strong>';

    var links = headings.slice(0, 9).map(function (heading) {
      var a = doc.createElement('a');
      a.href = '#' + heading.id;
      a.textContent = heading.textContent.replace(/[§#]+/g, '').trim();
      nav.appendChild(a);
      return a;
    });

    doc.body.appendChild(nav);

    if ('IntersectionObserver' in win) {
      var activeId = null;
      var observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          activeId = entry.target.id;
          links.forEach(function (link) {
            link.setAttribute('aria-current', link.getAttribute('href') === '#' + activeId ? 'true' : 'false');
          });
        });
      }, { rootMargin: '-18% 0px -72% 0px', threshold: 0.01 });
      headings.forEach(function (h) { observer.observe(h); });
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
