
const puppeteer = require('puppeteer-core');
const http = require('http');
const fs = require('fs');
const path = require('path');
const BASE = process.env.LAYOUT_BASE || path.join(__dirname, '..', 'public');
const PORT = 8097;
const server = http.createServer((req, res) => {
  let p = decodeURIComponent(req.url.split('?')[0]);
  if (p.endsWith('/')) p += 'index.html';
  let f = path.normalize(path.join(BASE, p));
  if (!f.startsWith(BASE)) { res.writeHead(403); res.end(); return; }
  fs.readFile(f, (e, d) => {
    if (e) { res.writeHead(404); res.end(); return; }
    const t = {'.html':'text/html','.css':'text/css','.js':'application/javascript','.jpg':'image/jpeg','.png':'image/png','.webp':'image/webp','.avif':'image/avif','.woff2':'font/woff2'};
    res.writeHead(200, {'Content-Type': t[path.extname(f)] || 'application/octet-stream'});
    res.end(d);
  });
});
(async () => {
  server.listen(PORT);
  const browser = await puppeteer.launch({ executablePath: process.env.CHROME_PATH || undefined,
    args: ['--no-sandbox', '--disable-setuid-sandbox'], headless: 'new' });
  const pages = JSON.parse(fs.readFileSync(process.env.DESIGN_PAGES || '[]', 'utf8'));
  const viewports = [{ width: 1280, height: 800 }, { width: 390, height: 844 }];
  for (const url of pages) {
    for (const vp of viewports) {
      const page = await browser.newPage();
      await page.setViewport(vp);
      await page.goto(`http://127.0.0.1:${PORT}${url}`, { waitUntil: 'networkidle0', timeout: 60000 });
      const name = `/tmp/dsn_${url.replace(/\W+/g, '') || 'home'}_${vp.width}.png`;
      await page.screenshot({ path: name });
      console.log(name);
      await page.close();
    }
  }
  await browser.close();
  server.close();
  process.exit(0);
})();
