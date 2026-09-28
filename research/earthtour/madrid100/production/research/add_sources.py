import json,requests,concurrent.futures
from pathlib import Path
from bs4 import BeautifulSoup
R=Path(__file__).resolve().parents[1]
rows=[
('Madrid tourism: flavours from across Spain','https://www.esmadrid.com/en/flavours-all-over-spain-madrid','各地から首都へ集まる料理の地域区分'),
('Madrid tourism: flavours of Madrid','https://www.esmadrid.com/en/the-flavours-of-madrid','マドリードの料理と菓子'),
('Regional tourism: traditional gastronomy','https://www.visitmadrid.es/en/things-to-do-in-madrid/what-to-do/gastronomy-in-madrid/traditional-gastronomy','州の伝統料理'),
('Spain tourism: Madrid regional cuisine','https://www.spain.info/en/gastronomy/madrid-regional-cuisine/','伝統料理・全国の味の集積'),
('Comunidad: quality labels','https://www.comunidad.madrid/agricultura-ganaderia-medio-rural/marcas-calidad-alimentos-madrid','品質表示と産地認証の区別'),
('Comunidad: foods of Madrid','https://www.comunidad.madrid/agricultura-ganaderia-medio-rural/alimentos-madrid','州内産品'),
('La Canibal: our brewery','https://lacanibal.com/la-fabrica-nuestras-cervezas/','2023年10月の自社醸造所稼働'),
('Madrid tourism: Casa Mingo','https://www.esmadrid.com/restaurantes/casa-mingo','鶏のローストとシードル'),
('Madrid tourism: vermouth map PDF','https://www.esmadrid.com/sites/default/files/plano-vermuterias-madrid.pdf','Casa CamachoのYayoの配合'),
('Madrid tourism: vermouth map','https://www.esmadrid.com/mapa-vermuterias-madrid','ベルムー文化'),
('Quesos Campo Real','https://quesoscamporeal.com/','羊乳・混合乳の商品を区別'),
('Royal kitchens official tickets','https://tickets.patrimonionacional.es/es/tickets/cocinas-palacio-real-de-madrid','券種とスペイン語見学')]
def fetch(pair):
 i,(title,url,scope)=pair;d=dict(id=f'S{i+87:02}',title=title,url=url,scope=scope,retrieved_at='2026-09-28',kind='primary',claim_review='see review/source-claims.json')
 try:
  r=requests.get(url,timeout=45,headers={"User-Agent":"Earthtour editorial source check (+https://earthtour.jp/)"});d.update(http_status=r.status_code,final_url=r.url);r.raise_for_status()
  if 'pdf' in r.headers.get('Content-Type','') or r.content.startswith(b'%PDF'):
   (R/f'research/source-cache/{d["id"]}.pdf').write_bytes(r.content)
  else:
   s=BeautifulSoup(r.content,'html.parser')
   for n in s(['script','style','nav','footer','header']):n.decompose()
   (R/f'research/source-cache/{d["id"]}.txt').write_text(s.get_text('\n',strip=True),encoding='utf-8')
 except Exception as e:d['error']=str(e)[:160]
 return d
data=list(concurrent.futures.ThreadPoolExecutor(4).map(fetch,enumerate(rows)))
(R/'research/added-sources.json').write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding='utf-8')
print([(d['id'],d.get('http_status'),d.get('error','')) for d in data])
