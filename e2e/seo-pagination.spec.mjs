import { test, expect, SITE_ORIGIN } from './fixtures.mjs';
import { newestArticlePath } from './helpers.mjs';

test.describe('SEO-Regressionen: Pagination, Sitemap, Metadaten', () => {
  test('echte Folgeseiten: noindex, eigene Canonical-URL, eindeutiger Titel', async ({ page }) => {
    for (const path of ['/page/2/', '/posts/page/2/']) {
      await page.goto(path);
      await expect(page.locator('meta[name=robots]')).toHaveAttribute('content', 'noindex, follow');
      await expect(page.locator('link[rel=canonical]')).toHaveAttribute('href', SITE_ORIGIN + path);
      expect(await page.title()).toContain('Seite 2');
      await expect(page.locator('meta[property="og:url"]')).toHaveAttribute('content', SITE_ORIGIN + path);
      const schemas = await page.locator('script[type="application/ld+json"]').allTextContents();
      expect(schemas.some(s => JSON.parse(s)['@type'] === 'CollectionPage')).toBe(false);
    }
  });
  test('Sitemap enthält beide Hubs, keine Pager und keine erfundene Rechtsseiten-Frische', async ({ request, baseURL }) => {
    const response = await request.get(`${baseURL}/sitemap.xml`);
    const xml = await response.text();
    expect(xml).toContain(`<loc>${SITE_ORIGIN}/posts/</loc>`);
    expect(xml).toContain(`<loc>${SITE_ORIGIN}/pillar/</loc>`);
    expect(xml).not.toMatch(/<loc>[^<]*\/page\/\d+/);
    for (const slug of ['ueber', 'impressum', 'datenschutz']) {
      const entry = xml.match(new RegExp(`<url>\\s*<loc>${SITE_ORIGIN}/${slug}/</loc>(.*?)</url>`, 's'));
      expect(entry).not.toBeNull();
      expect(entry[1]).not.toContain('<lastmod>');
    }
  });
  test('SEO-Title konsistent; Artikel-Daten und Autorenrolle widerspruchsfrei', async ({ page }) => {
    await page.goto('/');
    const title = await page.title();
    expect(title).toContain('Geld sparen');
    await expect(page.locator('meta[property="og:title"]')).toHaveAttribute('content', title);
    await expect(page.locator('meta[name="twitter:title"]')).toHaveAttribute('content', title);
    await expect(page.locator('meta[name=robots]')).toHaveAttribute('content', /max-image-preview:large/);
    await page.goto(await newestArticlePath(page));
    const data = (await page.locator('script[type="application/ld+json"]').allTextContents()).map(JSON.parse);
    const article = data.find(d => d['@type'] === 'Article');
    const person = data.find(d => d['@type'] === 'Person');
    expect(article.author.jobTitle).toBe(person.jobTitle);
    const modified = await page.locator('meta[property="article:modified_time"]').getAttribute('content');
    expect(Date.parse(modified)).toBe(Date.parse(article.dateModified));
  });
});
