// ============================================================
//  SPEC: ARTIKEL-SEITE – SEO-Meta, Schema, Bilder, Vorlese-Toolbar
//  Getestet wird der NEUESTE Artikel (dynamisch von der Startseite
//  ermittelt) – robust gegen neue Veröffentlichungen.
//  Projekt: desktop + mobile
// ============================================================

import { test, expect } from './fixtures.mjs';
import { watchErrors, assertNoErrors, scrollThrough, waitForImages, newestArticlePath, SITE_ORIGIN } from './helpers.mjs';

test.describe('Artikel-Seite (neuester Beitrag)', () => {
  test('rendert Titel, H1, Meta und Breadcrumbs', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);

    await expect(page).toHaveTitle(/.+/);
    const h1 = page.locator('h1');
    expect(await h1.count(), 'Artikel: genau ein H1').toBe(1);
    expect((await h1.first().textContent()).trim().length).toBeGreaterThan(10);

    // Meta-Zeile (Datum · Lesezeit · Autor) – Redaktions-Standard
    const header = page.locator('header.post-header');
    await expect(header).toBeVisible();
    const metaText = (await header.textContent()) || '';
    expect(metaText, 'Artikel-Meta enthält Datum/Autor').toMatch(/\d{2}\.\d{2}\.\d{4}|Frank Hartung/);

    // Breadcrumbs (Schema + UX-Standard der Redaktion)
    expect(await page.locator('nav[aria-label*="readcrumb"], .breadcrumbs, nav.breadcrumbs').count()).toBeGreaterThan(0);
  });

  test('SEO-Meta: Description, Canonical, Open Graph, Twitter Card', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);

    // Meta-Description: vorhanden und sinnvoll dimensioniert
    const desc = await page
      .locator('meta[name="description"]')
      .getAttribute('content');
    expect(desc, 'Meta-Description vorhanden').toBeTruthy();
    expect(desc.length, 'Meta-Description 50–200 Zeichen').toBeGreaterThanOrEqual(50);
    expect(desc.length, 'Meta-Description nicht überladen (>200)').toBeLessThanOrEqual(200);

    // Canonical zeigt auf die kanonische Produktions-URL
    const canonical = await page.locator('link[rel="canonical"]').getAttribute('href');
    expect(canonical, 'Canonical vorhanden').toBeTruthy();
    expect(canonical.startsWith(SITE_ORIGIN), 'Canonical ist absolut auf Produktions-Domain').toBe(true);
    expect(
      canonical.replace(SITE_ORIGIN, '').replace(/\/$/, ''),
      'Canonical entspricht dem Artikel-Pfad'
    ).toBe(articlePath.replace(/\/$/, ''));

    // Open Graph (Social/Pinterest-Pflicht)
    for (const prop of ['og:title', 'og:description', 'og:image', 'og:url', 'og:type']) {
      const val = await page.locator(`meta[property="${prop}"]`).getAttribute('content');
      expect(val, `${prop} gesetzt`).toBeTruthy();
    }

    // Twitter Card
    const tw = await page.locator('meta[name="twitter:card"]').getAttribute('content');
    expect(tw, 'twitter:card gesetzt').toBeTruthy();
  });

  test('og:image ist lokal auflösbar (Cover existiert im Build)', async ({ page, request, baseURL }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);
    const ogImage = await page.locator('meta[property="og:image"]').getAttribute('content');
    const res = await request.get(ogImage.replace(SITE_ORIGIN, baseURL.replace(/\/$/, '')));
    expect(res.status(), `og:image erreichbar: ${ogImage}`).toBe(200);
    expect((await res.headers())['content-type'] || '').toContain('image/');
  });

  test('JSON-LD: valider Article-Graph mit FAQ/Breadcrumbs', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);

    const blocks = await page.locator('script[type="application/ld+json"]').allTextContents();
    expect(blocks.length, 'mindestens ein JSON-LD-Block').toBeGreaterThan(0);

    const types = new Set();
    for (const b of blocks) {
      const parsed = JSON.parse(b); // wirft → Test failt bei kaputtem Schema
      const collect = (node) => {
        if (!node || typeof node !== 'object') return;
        if (Array.isArray(node)) return node.forEach(collect);
        if (node['@type']) {
          (Array.isArray(node['@type']) ? node['@type'] : [node['@type']]).forEach((t) => types.add(t));
        }
        Object.values(node).forEach(collect);
      };
      collect(parsed);
    }
    expect(types.has('Article') || types.has('BlogPosting') || types.has('NewsArticle'),
      'Article-Schema vorhanden').toBe(true);
    expect(types.has('BreadcrumbList'), 'BreadcrumbList-Schema vorhanden').toBe(true);
  });

  test('Bilder: geladen, alt-Texte, width/height (CLS-Schutz)', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath, { waitUntil: 'load' });
    await scrollThrough(page);
    await waitForImages(page);

    // Gesamter Artikelbereich: Cover (LCP), Autoren-Foto, Lazy-Teaser
    const imgs = page.locator('article.post-single img');
    const count = await imgs.count();
    expect(count, 'Artikel enthält Bilder (mind. Cover)').toBeGreaterThan(0);

    const probleme = [];
    for (let i = 0; i < count; i++) {
      const img = imgs.nth(i);
      const src = await img.evaluate((el) => el.currentSrc || el.src);
      if (!(await img.evaluate((el) => el.complete && el.naturalWidth > 0))) {
        probleme.push(`nicht geladen: ${src}`);
      }
      const alt = await img.getAttribute('alt');
      const istDeko = (await img.getAttribute('aria-hidden')) === 'true';
      if ((alt === null || alt.trim() === '') && !istDeko) probleme.push(`ohne alt: ${src}`);
      // Layout-Stabilität (CWV-Gate des Blogs): dimensionierte Bilder
      if (!(await img.getAttribute('width')) || !(await img.getAttribute('height'))) {
        probleme.push(`ohne width/height (CLS-Risiko): ${src}`);
      }
    }
    expect(probleme, 'Artikelbilder: geladen, alt + dimensioniert').toEqual([]);
  });

  test('Desktop-Inhaltsnavigation schneidet lange Abschnittstitel nicht ab', async ({ page }) => {
    // Regression 26.09.2026: Der zweizeilige Line-Clamp kappte das deutsche
    // Kompositum sichtbar zu „Tierkrankenversicherun…“. Der Eintrag darf
    // höher werden; die komplette Navigation besitzt ohnehin einen eigenen
    // Scrollbereich.
    await page.setViewportSize({ width: 1600, height: 900 });
    await page.goto('/posts/2026-09-21-tierkrankenversicherung-hund-katze-kosten/');

    // Lesefenster (26.09.2026): Die Navigation blendet sich erst ein, wenn
    // der Artikelkörper die obere Zone erreicht – erst dorthin scrollen,
    // dann Sichtbarkeit prüfen.
    await page.evaluate(() => {
      const content = document.querySelector('.post-content');
      window.scrollTo(0, (content ? content.getBoundingClientRect().top + window.scrollY : 400) + 700);
    });
    const nav = page.locator('.ff-mini-toc');
    await expect(nav).toBeVisible();

    const label = 'Wann sich eine Tierkrankenversicherung lohnt';
    const entry = page.locator(`.ff-mini-toc a[aria-label="${label}"]`);
    await expect(entry).toBeVisible();
    await expect(entry).toHaveText(label);

    const rendering = await entry.evaluate((el) => {
      const style = getComputedStyle(el);
      const range = document.createRange();
      range.selectNodeContents(el);
      const textBottom = Math.max(...Array.from(range.getClientRects(), (rect) => rect.bottom));
      return {
        lineClamp: style.getPropertyValue('-webkit-line-clamp'),
        textBottom,
        boxBottom: el.getBoundingClientRect().bottom,
      };
    });

    expect(rendering.lineClamp, 'kein CSS-Line-Clamp auf dem Navigationseintrag').toBe('none');
    expect(rendering.textBottom, 'vollständiger Text liegt innerhalb des Eintrags').toBeLessThanOrEqual(rendering.boxBottom + 1);
  });

  // ------------------------------------------------------------
  // Regression 26.09.2026 („IM ARTIKEL verdeckt / Newsletter abonnieren
  // wird nicht richtig angezeigt“): Der Newsletter-Kopf über dem Artikel
  // ist 1024 px breit, die Textspalte nur 768 px. Die schwebende
  // „Im Artikel“-Navigation saß mit 104 px AUF dem Streifenende und
  // verdeckte rund ein Drittel des gelben „Newsletter abonnieren“-Knopfs
  // (auf JEDEM Desktop ab 1280 px). Vertrag seit der Reparatur:
  //   1. Seitenkopf: Navigation im Ruhzustand (unsichtbar, nicht klickbar),
  //      der Newsletter-Knopf ist vollständig frei.
  //   2. Lesephase: Navigation sichtbar, aber es liegt NICHTS unter ihr.
  //   3. Seitenfuß: Navigation zieht sich zurück, bevor Fuß-Blöcke die
  //      Zone erreichen.
  //   4. Anker-Sprung in den Artikel: Navigation sofort da.
  // ------------------------------------------------------------
  for (const breite of [1280, 1440, 1920]) {
    test(`Schwebende Artikel-Navigation überdeckt keinen Inhalt – Newsletter-Kopf frei (${breite}px)`, async ({ page }) => {
      await page.setViewportSize({ width: breite, height: 900 });
      await page.goto('/posts/2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro/');
      // Ruhzustand ist unsichtbar → auf Existenz (attached) warten, nicht Sichtbarkeit
      await page.waitForSelector('.ff-mini-toc', { state: 'attached' });
      await page.waitForTimeout(300);

      // 1) Seitenkopf: Ruhzustand + Newsletter-Knopf frei (Klick-Treffer
      //    an der Stelle, die früher unter der Box lag).
      const kopf = await page.evaluate(() => {
        const box = document.querySelector('.ff-mini-toc');
        const cta = document.querySelector('.ff-nl-top__cta');
        if (!box || !cta) return { da: false };
        const cs = getComputedStyle(box);
        const cr = cta.getBoundingClientRect();
        const treffer = [
          [cr.right - 6, (cr.top + cr.bottom) / 2],
          [(cr.left + cr.right) / 2, (cr.top + cr.bottom) / 2],
        ].every(([x, y]) => {
          const el = document.elementFromPoint(x, y);
          return !!el && (el === cta || cta.contains(el));
        });
        return {
          da: true,
          idle: box.classList.contains('ff-mini-toc--idle'),
          opacity: cs.opacity,
          visibility: cs.visibility,
          pointerEvents: cs.pointerEvents,
          treffer,
        };
      });
      expect(kopf.da, 'Newsletter-Kopf und schwebende Navigation vorhanden').toBe(true);
      expect(kopf.idle, 'Seitenkopf: Navigation im Ruhzustand').toBe(true);
      expect(kopf.opacity, 'Seitenkopf: Navigation unsichtbar').toBe('0');
      expect(kopf.visibility, 'Seitenkopf: Navigation aus der Tab-Ordnung').toBe('hidden');
      expect(kopf.pointerEvents, 'Seitenkopf: Navigation klickt nicht durch').toBe('none');
      expect(kopf.treffer, '„Newsletter abonnieren“-Knopf ist vollständig klickbar').toBe(true);

      // 2) Lesephase: Navigation sichtbar und frei von Überdeckung.
      //    Clip-bewusst messen: Effektiv sichtbarer Kasten = Schnitt mit
      //    allen Overflow-Vorfahren (Tabellen in Scroll-Hüllen werden
      //    visuell beschnitten, ihr rohes rect nicht).
      await page.evaluate(() => {
        const content = document.querySelector('.post-content');
        window.scrollTo(0, content.getBoundingClientRect().top + window.scrollY + 700);
      });
      await page.waitForFunction(() => {
        const box = document.querySelector('.ff-mini-toc');
        return box && !box.classList.contains('ff-mini-toc--idle') && getComputedStyle(box).opacity === '1';
      });
      const lesephase = await page.evaluate(() => {
        const box = document.querySelector('.ff-mini-toc');
        const br = box.getBoundingClientRect();
        const sichtbarerKasten = (el) => {
          let r = el.getBoundingClientRect();
          let anc = el.parentElement;
          while (anc && anc !== document.body) {
            const acs = getComputedStyle(anc);
            if (/(auto|hidden|clip|scroll)/.test(acs.overflow + acs.overflowX + acs.overflowY)) {
              const ar = anc.getBoundingClientRect();
              const l = Math.max(r.left, ar.left);
              const t = Math.max(r.top, ar.top);
              const rr = Math.min(r.right, ar.right);
              const b = Math.min(r.bottom, ar.bottom);
              r = { left: l, top: t, right: rr, bottom: b, width: rr - l, height: b - t };
            }
            anc = anc.parentElement;
          }
          return r;
        };
        const verdeckt = [];
        for (const el of document.querySelectorAll('body *')) {
          if (el.closest('.ff-mini-toc')) continue;
          const ecs = getComputedStyle(el);
          if (ecs.display === 'none' || ecs.visibility === 'hidden') continue;
          const r0 = el.getBoundingClientRect();
          if (r0.width < 4 || r0.height < 4) continue;
          const r = sichtbarerKasten(el);
          if (r.width < 4 || r.height < 4) continue;
          const ix = Math.min(r.right, br.right) - Math.max(r.left, br.left);
          const iy = Math.min(r.bottom, br.bottom) - Math.max(r.top, br.top);
          if (ix > 4 && iy > 4) verdeckt.push(el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0]);
        }
        return { idle: box.classList.contains('ff-mini-toc--idle'), verdeckt: [...new Set(verdeckt)] };
      });
      expect(lesephase.idle, 'Lesephase: Navigation sichtbar').toBe(false);
      expect(lesephase.verdeckt, 'Lesephase: kein Element liegt unter der Navigation').toEqual([]);

      // 3) Seitenfuß: Navigation zurückgezogen oder weiterhin frei.
      await page.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
      await page.waitForTimeout(400);
      const fuss = await page.evaluate(() => {
        const box = document.querySelector('.ff-mini-toc');
        const cs = getComputedStyle(box);
        if (cs.opacity === '0' || cs.visibility === 'hidden') return { zurueckgezogen: true, verdeckt: [] };
        const br = box.getBoundingClientRect();
        const verdeckt = [];
        for (const el of document.querySelectorAll('body *')) {
          if (el.closest('.ff-mini-toc')) continue;
          const ecs = getComputedStyle(el);
          if (ecs.display === 'none' || ecs.visibility === 'hidden') continue;
          const r = el.getBoundingClientRect();
          if (r.width < 4 || r.height < 4) continue;
          const ix = Math.min(r.right, br.right) - Math.max(r.left, br.left);
          const iy = Math.min(r.bottom, br.bottom) - Math.max(r.top, br.top);
          if (ix > 4 && iy > 4) verdeckt.push(el.tagName.toLowerCase() + '.' + String(el.className).split(' ')[0]);
        }
        return { zurueckgezogen: false, verdeckt: [...new Set(verdeckt)] };
      });
      expect(fuss.verdeckt, 'Seitenfuß: kein Element liegt unter der Navigation').toEqual([]);

      // 4) Anker-Sprung direkt in den Artikel: Navigation sofort da.
      const anker = await page.evaluate(() => document.querySelector('.post-content h2[id]')?.id);
      expect(anker, 'Artikel hat anspringbare H2-Abschnitte').toBeTruthy();
      await page.goto(`/posts/2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro/#${anker}`);
      await page.waitForFunction(() => {
        const box = document.querySelector('.ff-mini-toc');
        return box && !box.classList.contains('ff-mini-toc--idle');
      });
      await expect(page.locator('.ff-mini-toc')).toBeVisible();
    });
  }

  test('Schwebende Artikel-Navigation: bei reduzierter Bewegung ohne Übergang', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.goto('/posts/2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro/');
    await page.waitForSelector('.ff-mini-toc', { state: 'attached' });
    const motion = await page.evaluate(() => {
      const box = document.querySelector('.ff-mini-toc');
      const cs = getComputedStyle(box);
      return { dauer: cs.transitionDuration, eigenschaft: cs.transitionProperty };
    });
    // Haus-Standard (zzz-agency-polish.css §8): globale Reduzierung auf
    // 0.001 ms – effektiv sofort. Erlaubt: 0 s und 0.001 ms (Listen inklusive).
    expect(motion.dauer.split(',').every((d) => parseFloat(d) < 0.01),
      'prefers-reduced-motion: keine spürbare Übergangsdauer auf der Navigation').toBe(true);
  });

  test('Vorlese-Toolbar (FF Voice Studio): vorhanden & bedienbar', async ({ page }) => {
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath);

    const slot = page.locator('.ff-voice-slot');
    if ((await slot.count()) === 0) {
      test.skip(true, 'Dieser Artikel hat keine Vorlese-Toolbar');
      return;
    }
    await expect(slot.first()).toBeVisible();

    // Alle Buttons der Toolbar brauchen zugängliche Namen (WCAG 2.2 AA+,
    // Selbstanspruch der ff-voice.css)
    const buttons = slot.first().locator('button');
    const count = await buttons.count();
    expect(count, 'Toolbar hat Bedienelemente').toBeGreaterThan(0);
    for (let i = 0; i < count; i++) {
      const name = await buttons.nth(i).evaluate((el) => {
        const label = el.getAttribute('aria-label') || el.textContent || '';
        return label.trim();
      });
      expect(name.length, `Toolbar-Button ${i + 1} hat zugänglichen Namen`).toBeGreaterThan(0);
    }
  });

  test('lädt ohne JS-Fehler (ganze Seite durchscrollen)', async ({ page }) => {
    const errors = watchErrors(page);
    const articlePath = await newestArticlePath(page);
    await page.goto(articlePath, { waitUntil: 'load' });
    await scrollThrough(page);
    await page.waitForLoadState('networkidle');
    assertNoErrors(errors, 'Artikel');
  });
});
