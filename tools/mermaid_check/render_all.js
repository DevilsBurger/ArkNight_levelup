const fs = require('fs');
const { chromium } = require('playwright');
(async () => {
  const [md, outPrefix, scale] = [process.argv[2], process.argv[3], Number(process.argv[4] || 2)];
  const blocks = [...fs.readFileSync(md, 'utf8').matchAll(/```mermaid\n([\s\S]*?)```/g)].map(m => m[1]);
  const lib = fs.readFileSync(require.resolve('mermaid/dist/mermaid.min.js'), 'utf8');
  const browser = await chromium.launch();
  for (let i = 0; i < blocks.length; i++) {
    const page = await browser.newPage({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: scale });
    await page.setContent(`<!doctype html><html><body style="margin:16px;background:#fff;font-family:sans-serif"><div id="out"></div><script>${lib}</script></body></html>`);
    await page.evaluate(async (code) => {
      mermaid.initialize({ startOnLoad: false, securityLevel: 'loose', fontFamily: 'sans-serif' });
      const { svg } = await mermaid.render('d', code);
      document.getElementById('out').innerHTML = svg;
    }, blocks[i]);
    const el = await page.$('#out svg');
    const name = `${outPrefix}_${String(i + 1).padStart(2, '0')}.png`;
    await el.screenshot({ path: name });
    console.log('saved', name);
    await page.close();
  }
  await browser.close();
})();
