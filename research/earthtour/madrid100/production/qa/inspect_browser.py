"""Inspect actual browser rendering; local and WordPress results are separate."""
import json,os,sys,time,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path(__file__).resolve().parents[1]
mode=sys.argv[1] if len(sys.argv)>1 else 'local'
target=(R/'out/preview.html').as_uri() if mode=='local' else sys.argv[2]
report={'mode':mode,'target':'out/preview.html' if mode=='local' else 'authenticated draft preview','widths':[]}
with sync_playwright() as pw:
 browser=pw.chromium.launch(channel='msedge',headless=True)
 ctx=browser.new_context(device_scale_factor=1)
 if mode=='wordpress':
  import base64
  auth='Basic '+base64.b64encode(('earthtour:'+os.environ['EARTHTOUR_WP_APP_PASSWORD']).encode()).decode()
  # Send credentials ONLY to this explicitly authorized origin, never image CDNs.
  def route(r):
   if r.request.url.startswith('https://earthtour.jp/'):
    r.continue_(headers={**r.request.headers,'Authorization':auth})
   else:r.continue_()
  ctx.route('**/*',route)
 page=ctx.new_page()
 for width in [360,390,768,1024,1440]:
  page.set_viewport_size({'width':width,'height':950})
  res=page.goto(target,wait_until='domcontentloaded',timeout=90000)
  page.wait_for_timeout(1500)
  if mode=='wordpress' and page.locator('#dish-001').count()==0:
   report.update(blocked=True,http_status=res.status if res else None,reason='Authenticated request did not render draft article; no publication performed')
   page.screenshot(path=str(R/f'qa/wp-preview-unavailable-{width}.png'));break
  page.evaluate("document.querySelectorAll('img').forEach(i=>{i.loading='eager';i.decoding='sync'})")
  page.evaluate("async()=>{await document.fonts.ready;await Promise.race([Promise.all([...document.images].map(i=>i.decode().catch(()=>{}))),new Promise(r=>setTimeout(r,45000))])}")
  metrics=page.evaluate('''()=>({width:innerWidth,scrollWidth:document.documentElement.scrollWidth,h1:document.querySelectorAll('h1').length,dishes:document.querySelectorAll('article[id^="dish-"]').length,missingImages:[...document.images].filter(i=>!i.complete||i.naturalWidth===0).map(i=>({src:i.currentSrc||i.src,alt:i.alt})),badAnchors:[...document.querySelectorAll('a[href^="#"]')].filter(a=>a.hash.length>1&&!document.getElementById(decodeURIComponent(a.hash.slice(1)))).map(a=>a.hash),overflow:[...document.querySelectorAll('.t100 p,.t100 h1,.t100 h2,.t100 h3,.t100 h4,.t100 a')].filter(e=>{let r=e.getBoundingClientRect();return r.width>0&&(r.right>innerWidth+2||r.left<-2)}).slice(0,20).map(e=>({text:e.innerText.slice(0,60),cls:e.className}))})''')
  metrics['screenshots']=[]
  metrics['clippedLabels']=page.evaluate("[...document.querySelectorAll('.grid100 span,.stamp span')].filter(e=>e.scrollHeight>e.clientHeight+2).map(e=>e.innerText)")
  for name,selector in [('top','body'),('toc','#t100-plan'),('main','#dish-001'),('middle','#dish-061'),('end','#t100-end'),('sources','.sources')]:
   loc=page.locator(selector).first
   if not loc.count():continue
   loc.evaluate('(e)=>window.scrollTo(0,e.getBoundingClientRect().top+window.scrollY-24)')
   page.wait_for_timeout(250)
   f=f'qa/{mode}-{width}-{name}.png';page.screenshot(path=str(R/f));metrics['screenshots'].append(f)
  report['widths'].append(metrics)
  (R/f'qa/{mode}-browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=1),encoding='utf-8')
  print(width,'overflow',metrics['scrollWidth']-width,'missing',len(metrics['missingImages']),'anchors',len(metrics['badAnchors']),flush=True)
 (R/f'qa/{mode}-browser.json').write_text(json.dumps(report,ensure_ascii=False,indent=1),encoding='utf-8')
 browser.close()
