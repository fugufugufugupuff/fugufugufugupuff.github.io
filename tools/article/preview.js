#!/usr/bin/env node
// 3サイズ（スマホ 390 / タブレット 820 / PC 1440）で描画し、横はみ出し・画像欠けを報告する。
//   node tools/article/preview.js article.html [outdir]
// 出力: outdir/{mobile,tablet,desktop}.png と report.json
const fs = require('fs'); const path = require('path');
const { chromium } = require('playwright');

const SIZES = { mobile: 390, tablet: 820, desktop: 1440 };
const EXE = ['/opt/pw-browsers/chromium-1194/chrome-linux/chrome', '/opt/pw-browsers/chromium/chrome'].find(p => fs.existsSync(p));

(async () => {
  const file = process.argv[2]; if (!file) { console.error('usage: preview.js article.html [outdir]'); process.exit(2); }
  const out = process.argv[3] || path.join(path.dirname(file), 'preview'); fs.mkdirSync(out, { recursive: true });
  const frag = fs.readFileSync(file, 'utf8');
  // SWELL 相当の器：本文幅制限を再現しつつ alignfull を有効に
  const page_html = `<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>html,body{margin:0;padding:0}body{font-family:sans-serif;background:#fff}.l-content{max-width:1200px;margin:0 auto}.wp-block-group.alignfull{width:100vw;margin-left:calc(50% - 50vw)}</style></head>
<body><div class="l-content"><h1 style="font:700 28px/1.4 sans-serif;padding:20px">（SWELL のタイトル位置）</h1><div class="wp-block-group alignfull"><div class="wp-block-group__inner-container">${frag}</div></div></div></body></html>`;
  // クラウド環境では HTTPS_PROXY 経由でしか外に出られない。Chromium は環境変数を見ないので明示する
  const proxy = process.env.HTTPS_PROXY || process.env.https_proxy;
  const launchOpts = { ...(EXE ? { executablePath: EXE } : {}), ...(proxy ? { proxy: { server: proxy } } : {}) };
  const browser = await chromium.launch(launchOpts);
  const report = {};
  let bad = false;
  // 1ページを使い回す（画像キャッシュを共有して、サイズごとの読み込み差をなくす）
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1, ignoreHTTPSErrors: !!proxy });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  const failedResponses = [];
  page.on('response', r => { if (r.status() >= 400) failedResponses.push([r.status(), r.url()]); });
  page.on('requestfailed', r => failedResponses.push([r.failure().errorText, r.url()]));
  await page.setContent(page_html, { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager'));
  // 画像を全部読み込ませる（最長 240 秒）
  const loaded = await Promise.race([
    page.evaluate(() => Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; }))).then(() => true)),
    new Promise(r => setTimeout(() => r(false), 240000)),
  ]);
  if (!loaded) console.log('!!  画像の読み込みが 240 秒で終わらなかった（回線が遅い可能性。欠けの報告は要再確認）');
  // Commons のサムネイル生成は同時要求が多いと 429 を返す。失敗した画像は間を空けて1枚ずつ再読込する
  for (let attempt = 1; attempt <= 3; attempt++) {
    const broken = await page.evaluate(() => [...document.images].filter(i => !i.naturalWidth).length);
    if (!broken) break;
    console.log(`..  読み込めなかった画像 ${broken} 枚を再試行 (${attempt}/3)`);
    await page.evaluate(async () => {
      for (const i of [...document.images].filter(i => !i.naturalWidth)) {
        const u = i.src; i.src = '';
        await new Promise(r => { i.onload = i.onerror = r; i.src = u; setTimeout(r, 30000); });
        await new Promise(r => setTimeout(r, 1500));
      }
    });
  }
  // それでも読めなかった画像は、ブラウザ外から HTTP で確かめる（URL が生きていれば回線の問題として扱う）
  const stillBroken = await page.evaluate(() => [...document.images].filter(i => !i.naturalWidth).map(i => i.src));
  const netOnly = new Set();
  for (const u of stillBroken) {
    const code = require('child_process').spawnSync('curl', ['-sS', '-o', '/dev/null', '-L', '--max-time', '60', '-w', '%{http_code}', u], { encoding: 'utf8' }).stdout;
    if (code === '200') { netOnly.add(u); console.log(`..  回線の問題（URL は 200）: ${decodeURIComponent(u).slice(0, 90)}`); }
    else if (code === '429') { netOnly.add(u); console.log(`..  Commons の回数制限 429（少し待てば読める）: ${decodeURIComponent(u).slice(0, 90)}`); }
    else console.log(`!!  HTTP ${code}: ${decodeURIComponent(u).slice(0, 90)}`);
  }
  const httpErrors = failedResponses.filter(([st]) => typeof st === 'number');
  for (const [st, u] of httpErrors) console.log(`     HTTP ${st}: ${u.slice(0, 100)}`);
  await page.evaluate(urls => { window.__netOnly = urls; }, [...netOnly]);
  for (const [name, width] of Object.entries(SIZES)) {
    await page.setViewportSize({ width, height: 900 });
    await page.waitForTimeout(800);
    const r = await page.evaluate(() => {
      const de = document.documentElement;
      const imgs = [...document.images];
      const broken = imgs.filter(i => !i.naturalWidth && !(window.__netOnly || []).includes(i.src)).map(i => i.src);
      const upscaled = imgs.filter(i => i.naturalWidth && i.getBoundingClientRect().width > i.naturalWidth * 1.15).map(i => `${decodeURIComponent(i.src.split('/').pop()).slice(0, 50)} ${Math.round(i.getBoundingClientRect().width)}px > 原寸${i.naturalWidth}px`);
      const inScroller = e => { for (let a = e.parentElement; a; a = a.parentElement) { const o = getComputedStyle(a).overflowX; if (o === 'auto' || o === 'scroll') return true; } return false; };
      const wide = [...document.querySelectorAll('body *')].filter(e => { const b = e.getBoundingClientRect(); return b.right > de.clientWidth + 1 && b.width > 0 && !inScroller(e); }).slice(0, 5).map(e => e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).split(' ')[0] : ''));
      const tiny = [...document.querySelectorAll('p,li,td,th,figcaption,span,div,a,h2,h3,cite')].filter(e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()) && parseFloat(getComputedStyle(e).fontSize) < 15).slice(0, 5).map(e => e.tagName.toLowerCase() + (e.className ? '.' + String(e.className).split(' ')[0] : '') + ' ' + getComputedStyle(e).fontSize);
      return { scrollWidth: de.scrollWidth, clientWidth: de.clientWidth, height: de.scrollHeight, images: imgs.length, broken, upscaled, overflowing: wide, tinyText: tiny };
    });
    r.jsErrors = errors;
    r.horizontalScroll = r.scrollWidth > r.clientWidth;
    const shot = path.join(out, `${name}.png`);
    await page.screenshot({ path: shot, fullPage: true });
    r.screenshot = shot;
    report[name] = r;
    const ng = r.horizontalScroll || r.broken.length || r.jsErrors.length || r.upscaled.length || r.tinyText.length || r.overflowing.length;
    if (ng) bad = true;
    console.log(`${ng ? 'X   ' : 'OK  '}${name} ${width}px  高さ${r.height}px 画像${r.images}枚 横スクロール:${r.horizontalScroll ? 'あり(' + r.scrollWidth + '>' + r.clientWidth + ')' : 'なし'} 欠け:${r.broken.length} 拡大ボケ:${r.upscaled.length} 小文字:${r.tinyText.length}`);
    for (const b of r.broken) console.log('     欠け: ' + b);
    for (const u of r.upscaled) console.log('     拡大: ' + u);
    for (const w of r.overflowing) console.log('     はみ出し要素: ' + w);
    for (const t of r.tinyText) console.log('     15px未満: ' + t);
    for (const e of r.jsErrors) console.log('     JSエラー: ' + e);
  }
  await page.close();
  await browser.close();
  fs.writeFileSync(path.join(out, 'report.json'), JSON.stringify(report, null, 1));
  console.log(`\nスクリーンショット: ${out}/  → 自分の目で見ること`);
  console.log('=== ' + (bad ? '要修正あり' : '3サイズ OK') + ' ===');
  process.exit(bad ? 1 : 0);
})();
