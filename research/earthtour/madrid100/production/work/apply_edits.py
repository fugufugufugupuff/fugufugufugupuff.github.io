import json, html
from pathlib import Path
R=Path(__file__).resolve().parents[1]
a=json.loads((R/'article.json').read_text(encoding='utf-8'))
m=json.loads((R/'work/master.json').read_text(encoding='utf-8'))
ed={p[0]:p[1:] for line in (R/'work/food_edits.tsv').read_text(encoding='utf-8').splitlines() if (p:=line.split('|'))}
pe=dict(line.split('|',1) for line in (R/'work/place_edits.tsv').read_text(encoding='utf-8').splitlines())
assert len(ed)==100 and len(pe)==30
by={f['id']:f for f in m['foods']}; places={f['id']:f for f in m['places']}
mapping=[[3,4],[],[18],[1,2],[19],[20],[26],[23],[21,16],[17],[24],[30],[25],[9],[8],[10],[11,12],[22],[5],[7],[15],[6],[27],[13],[28],[],[14],[29]]
a['meta'].update(show_costs=False,thematic=True,food_first=True)
md=['# '+a['meta']['title'],'',a['meta']['lede'],'']
changes=[]
for i,s in enumerate(a['stops']):
    s['photo_key']=s.get('photo_key') or f"d{s['day']}-{s['time'].replace(':','')}"
    s['time']=f'{i+1:02d}'
    s['slot']='選べる寄り道';s['subtitle']='';s['phrase']=None;s['move']=None
    ids=[f'L{n:02}' for n in mapping[i]];s['place_ids']=ids
    s['body']=[pe[k] for k in ids]
    if not ids:
        s['body']=['羊の腸間膜、胸腺、豚の耳。内臓料理は一つの味ではなく、部位ごとに形も火の通し方も変わる。ラストロやラ・ラティーナの散策とは別に、専門店のメニューで部位を選ぶ楽しみもある。' if i==1 else '食卓に届くまでの土地も、マドリードの食の一部。州内で搾るオリーブ油と、採蜜地の表示を読む蜂蜜は、旅先の土産選びを畑や花へつなげる。濃いチョコレートは、その場で休む一杯として。']
    s['place_name']='・'.join(places[k]['jp'] for k in ids) if ids else '食のテーマから選ぶ'
    s['area']=' / '.join(dict.fromkeys(places[k]['area'] for k in ids)) if ids else '市内・州内'
    s['hours']='';s['access']='市内と別の日帰り先として選ぶ。' if any(n>=27 for n in mapping[i]) else ''
    s['info']=[];s['tips']=[]
    md+=['## '+s['title'],'']+s['body']+['']
    for d in s['dishes']:
        f=by[d['candidate_id']];old=d['catch'];p=ed[f['id']]
        d.update(catch=p[0],first=p[1],tex=p[2].split(','),how=p[3],shop=f['shop'],review_status='rewritten; claim and photo review recorded separately')
        d['selection']['reason']=f['relation'];d['source_ids']=f['sources']
        f['body']=p[0];f['sensory_basis']=p[1];f['how']=p[3];f['writing_status']='全100項目改稿済み・個別出典と写真の確認状況は監査台帳参照'
        changes.append({'id':f['id'],'old':old,'new':p[0],'sources':f['sources'],'date':'2026-09-28'})
        md+=['### '+f['id']+' '+d['name']+' / '+d['local'],'',d['catch'],'',d['first'],'',d['how'],'']
for k,p in places.items():p['body']=pe[k];p['adopted']=True
for f,o in [('article.json',a),('work/master.json',m),('review/editorial-changes.json',changes)]:
    (R/f).write_text(json.dumps(o,ensure_ascii=False,indent=1),encoding='utf-8')
(R/'article.md').write_text('\n'.join(md),encoding='utf-8')
print('Applied 100 food edits, 30 sights, 28 thematic stops.')
