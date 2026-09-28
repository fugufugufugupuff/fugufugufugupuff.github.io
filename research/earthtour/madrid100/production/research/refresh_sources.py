"""Read public evidence, preserving response status separately from editorial review."""
import concurrent.futures, datetime, hashlib, json
from pathlib import Path
import requests
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
master=json.loads((ROOT/'work/master.json').read_text(encoding='utf-8'))
cache=ROOT/'research/source-cache'; cache.mkdir(exist_ok=True)
def fetch(s):
    record={'id':s['id'],'url':s['url'],'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'claim_reviewed':False}
    try:
        r=requests.get(s['url'],timeout=35,headers={'User-Agent':'Earthtour editorial source check (+https://earthtour.jp/)'})
        record.update(http_status=r.status_code,final_url=r.url,sha256=hashlib.sha256(r.content).hexdigest())
        if r.status_code==200 and 'pdf' not in r.headers.get('Content-Type',''):
            soup=BeautifulSoup(r.content,'html.parser')
            for el in soup(['script','style','nav','header','footer','form']): el.decompose()
            node=soup.select_one('main') or soup.select_one('article') or soup
            txt=node.get_text('\n',strip=True)
            (cache/(s['id']+'.txt')).write_text(txt,encoding='utf-8')
            record['text_chars']=len(txt)
        elif r.status_code==200:
            (cache/(s['id']+'.pdf')).write_bytes(r.content)
            record['pdf_requires_visual_review']=True
    except Exception as e: record['error']=type(e).__name__+': '+str(e)[:180]
    return record
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    result=list(pool.map(fetch,master['sources']))
(ROOT/'research/source-retrieval.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'attempted':len(result),'http200':sum(x.get('http_status')==200 for x in result),'failed':[{'id':x['id'],'status':x.get('http_status'),'error':x.get('error')} for x in result if x.get('http_status')!=200]},ensure_ascii=False))
