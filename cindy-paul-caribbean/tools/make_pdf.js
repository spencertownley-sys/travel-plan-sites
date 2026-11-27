// Make trip.pdf from index.html using the print styles. Needs Playwright (preinstalled in the build container).
//   node tools/make_pdf.js
const path = require('path');
const { chromium } = require('playwright');
(async () => {
  const root = path.resolve(__dirname, '..');
  const b = await chromium.launch();
  const p = await b.newPage();
  await p.goto('file://' + path.join(root, 'index.html'), { waitUntil: 'load' });
  await p.evaluate(() => { document.documentElement.setAttribute('data-theme', 'light'); document.querySelectorAll('details').forEach(d => { if (!d.classList.contains('src')) d.open = true; }); });
  await p.evaluate(() => document.fonts.ready);
  await p.emulateMedia({ media: 'print' });
  await p.waitForTimeout(500);
  await p.pdf({ path: path.join(root, 'trip.pdf'), format: 'Letter', printBackground: true, scale: 0.78,
    displayHeaderFooter: true, headerTemplate: '<span></span>',
    footerTemplate: '<div style="width:100%;font:8px Arial;color:#888;text-align:center">Cindy &amp; Paul in the Caribbean · page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
    margin: { top: '0.45in', bottom: '0.55in', left: '0.5in', right: '0.5in' } });
  await b.close();
  console.log('wrote', path.join(root, 'trip.pdf'));
})();
