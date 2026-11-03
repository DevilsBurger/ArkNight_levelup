const fs = require('fs');
const { chromium } = require('playwright');
(async () => {
  const md = fs.readFileSync(process.argv[2], 'utf8');
  const blocks = [...md.matchAll(/```mermaid\n([\s\S]*?)```/g)].map(m => m[1]);
  const lib = fs.readFileSync(require.resolve('mermaid/dist/mermaid.min.js'), 'utf8');
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('console', m => { if (m.type() === 'error') console.log('console:', m.text()); });
  await page.setContent(`<!doctype html><html><body><div id="out"></div><script>${lib}</script></body></html>`);
  const results = await page.evaluate(async (blocks) => {
    mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' });
    const out = [];
    for (let i = 0; i < blocks.length; i++) {
      try {
        const p = await mermaid.parse(blocks[i]);
        const { svg } = await mermaid.render('d' + i, blocks[i]);
        out.push({ i, ok: true, type: p && p.diagramType, len: svg.length });
      } catch (e) {
        out.push({ i, ok: false, err: String(e && e.message || e).slice(0, 400) });
      }
    }
    return out;
  }, blocks);
  for (const r of results) console.log(JSON.stringify(r));
  await browser.close();
  const bad = results.filter(r => !r.ok).length;
  console.log(`total ${results.length}, failed ${bad}`);
  process.exit(bad ? 1 : 0);
})();
