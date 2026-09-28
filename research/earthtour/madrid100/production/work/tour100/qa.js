// tour100 画面の自動検査（DESIGN.md の「5. 自動検査」）
//   node tour100/qa.js <preview.html> <出力フォルダ>
// 幅 360・390・768・1280 で開き、はみ出し・画像切れ・見出しの泣き別れを調べ、各ブロックのスクリーンショットを撮る。
const path = require('path'), fs = require('fs');
const { pathToFileURL } = require('url');
let chromium;
try { ({ chromium } = require('playwright')); } catch (e) { ({ chromium } = require('/opt/node22/lib/node_modules/playwright')); }
const [file, outDir] = [process.argv[2], process.argv[3] || 'qa'];
const WIDTHS = [360, 390, 768, 1280];
const SHOTS = [['.cover', 0], ['.plan', 0], ['.index', 0], ['.day', 0], ['.stop', 0], ['.dish', 1], ['.stop', 17], ['.dish', 69], ['.stop', 32], ['.dish', 99], ['.scenes', 0], ['.memos', 0], ['.album', 0], ['.receipt', 0], ['.fee', 0]];

(async () => {
  fs.mkdirSync(outDir, { recursive: true });
  const browser = await chromium.launch({ executablePath: process.env.TOUR100_CHROMIUM_PATH || undefined, channel: process.env.TOUR100_BROWSER_CHANNEL || undefined });
  const report = {};
  let bad = 0;
  for (const w of WIDTHS) {
    const page = await browser.newPage({ viewport: { width: w, height: 900 } });
    await page.goto(pathToFileURL(path.resolve(file)).href, { waitUntil: 'load' });
    await page.evaluate(async () => {
      document.querySelectorAll('img').forEach(i => { i.loading = 'eager'; });
      // naturalWidth can be nonzero while a progressive JPEG is still loading.
      // Wait for decoding, and report any request still pending at the deadline.
      await Promise.all([...document.images].map(i => Promise.race([
        i.decode().catch(() => {}), new Promise(r => setTimeout(r, 30000))
      ])));
      await document.fonts.ready;
    });
    const r = await page.evaluate((vw) => {
      const skip = el => el.closest('.dz,.route,.leaflet-container,.mapfb,.fab,.collage,.tape');
      const out = { pageOverflow: document.documentElement.scrollWidth > vw + 1, overflow: [], brokenImages: [], pendingImages: [], widows: [] };
      document.querySelectorAll('.t100 *').forEach(el => {
        if (skip(el)) return;
        const r = el.getBoundingClientRect();
        if (r.width && (r.right > vw + 2 || r.left < -2) && getComputedStyle(el).position !== 'absolute') {
          out.overflow.push((el.className || el.tagName) + ' ' + (el.textContent || '').trim().slice(0, 30) + ` [${Math.round(r.left)}〜${Math.round(r.right)}]`);
        }
        if (el.scrollWidth > el.clientWidth + 2 && el.clientWidth > 0 && getComputedStyle(el).overflowX === 'visible' && el.children.length === 0) {
          out.overflow.push('文字あふれ：' + (el.textContent || '').trim().slice(0, 30));
        }
      });
      document.querySelectorAll('.t100 img').forEach(i => { if (i.complete && i.naturalWidth === 0) out.brokenImages.push(i.getAttribute('src').slice(-60)); });
      document.querySelectorAll('.t100 img').forEach(i => { if (!i.complete) out.pendingImages.push(i.getAttribute('src').slice(-60)); });
      document.querySelectorAll('.t100 h1 .pl,.t100 h2,.t100 h3,.t100 h4').forEach(h => {
        const rects = [];
        const walk = n => n.childNodes.forEach(c => { if (c.nodeType === 3) { const r = document.createRange(); r.selectNodeContents(c); rects.push(...[...r.getClientRects()].filter(x => x.width > 0)); } else if (c.nodeType === 1 && c.tagName !== 'SMALL') walk(c); });
        walk(h);
        if (rects.length < 2) return;
        const lastTop = Math.max(...rects.map(x => x.top));
        const lastW = rects.filter(x => Math.abs(x.top - lastTop) < 4).reduce((a, x) => a + x.width, 0);
        const fs = parseFloat(getComputedStyle(h).fontSize);
        if (lastW < fs * 2.2) out.widows.push(h.textContent.trim().slice(0, 40));
      });
      out.overflow = [...new Set(out.overflow)].slice(0, 30);
      out.widows = [...new Set(out.widows)].slice(0, 30);
      return out;
    }, w);
    report[w] = r;
    bad += (r.pageOverflow ? 1 : 0) + r.overflow.length + r.brokenImages.length + r.pendingImages.length + r.widows.length;
    for (const [sel, i] of SHOTS) {
      const ok = await page.evaluate(([s, i]) => { const e = document.querySelectorAll(s)[i]; if (!e) return false; e.scrollIntoView({ block: 'start' }); return true; }, [sel, i]);
      if (!ok) continue;
      await page.waitForTimeout(300);
      await page.screenshot({ path: path.join(outDir, `${w}_${sel.replace(/[^a-z]/g, '')}${i > 1 ? '_' + (i + 1) : ''}.png`) });
    }
    await page.close();
    console.log(`${w}px  横はみ出し:${r.pageOverflow ? 'あり' : 'なし'}  要素のはみ出し:${r.overflow.length}  画像切れ:${r.brokenImages.length}  読み込み未完了:${r.pendingImages.length}  見出しの泣き別れ:${r.widows.length}`);
  }
  fs.writeFileSync(path.join(outDir, 'report.json'), JSON.stringify(report, null, 1));
  await browser.close();
  process.exit(bad ? 1 : 0);
})();
