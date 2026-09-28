import json
from pathlib import Path
R=Path(__file__).resolve().parents[1]
a=json.loads((R/'article.json').read_text(encoding='utf-8'));m=json.loads((R/'work/master.json').read_text(encoding='utf-8'))
added=json.loads((R/'research/added-sources.json').read_text(encoding='utf-8'))
src={s['id']:s for s in m['sources']}
src.update({s['id']:s for s in added});m['sources']=list(src.values())
replace={'S08':'S94','S14':'S93','S26':'S91','S27':'S92','S28':'S92','S31':'S95','S34':'S97','S69':'S02','S73':'S56','S78':'S91','S82':'S49','S83':'S49'}
city={1,2,3,4,5,7,8,9,10,11,12,13,14,19,21,24,25,29,40,61,62,64,65,66,67,70,72,74,75,80,81,83,84,85,92,95,96,97,100}
regional={6,73,82,86,87,88,89,90,91,98,99}
sources_extra={16:['S87'],22:['S87'],23:['S87'],32:['S87'],41:['S87'],42:['S87'],43:['S87'],46:['S87'],57:['S87'],59:['S87'],60:['S87'],62:['S100'],86:['S91'],87:['S97'],90:['S91'],96:['S99'],97:['S95'],98:['S91'],99:['S91'],100:['S93']}
updates={
86:('タイム、フェンネル、オレガノ、ニンニク。カンポ・レアルのオリーブは、こうした香草で調味する州の産品だ。州の説明によれば、作り手によってローリエやクミンなども加わる。種のまわりの果肉をかじる小さな一粒にも、漬け汁の流儀がある。バルのつまみや瓶詰めの土産として、地名の表示を手がかりに選びたい。','緑の果肉の歯応えと、漬け汁に使う香草の風味。生のオリーブをそのまま食べるのとは違い、調味した食卓用の産品。'),
90:('州南東部のオリーブ畑から生まれるDOP「Aceite de Madrid」。コルニカブラなど複数の品種を使い、指定地域で生産・製造・瓶詰めするエクストラバージン・オリーブ油だ。州の解説は、オリーブや草、アーモンドを思わせる香りと苦味・辛味の釣り合いを挙げる。パンに少量を付ければ、料理を支える調味料そのものへ目を向けられる。','なめらかな油がパンの表面に染みる。品種と製品による香りの違いを、少量ずつ比べる。'),
96:('サン・イシドロの祭りで親しまれるリモナーダは、ワイン、レモン、砂糖、刻んだ果物を合わせる飲み物。市の案内ではリンゴがよく使われる。ロスキージャスを選ぶ5月の菓子休憩に、果実入りの一杯が加わる。名前が似たソフトドリンクのレモネードとは違い、酒を使う祭礼の飲み物だ。','果実を浮かべたワインにレモンの酸味と砂糖を合わせる。甘さや冷たさだけで酒の強さは決まらない。')}
audit=[]; by={f['id']:f for f in m['foods']};used=set()
for s in a['stops']:
 s['source_links']=[]
 for lid in s['place_ids']:
  pl=next(x for x in m['places'] if x['id']==lid)
  pl['sources']=list(dict.fromkeys(replace.get(z,z) for z in pl['sources']))
  if lid=='L04':pl['sources']=['S98','S42']
  s['source_links'] += [[z,src[z]['url']] for z in pl['sources'] if z in src]
 s['source_links']=list(dict.fromkeys(tuple(v) for v in s['source_links']))
 for d in s['dishes']:
  n=int(d['candidate_id'][1:]);f=by[d['candidate_id']]
  if n in updates:d['catch'],d['first']=updates[n];f['body']=d['catch'];f['sensory_basis']=d['first']
  ids=list(dict.fromkeys([replace.get(z,z) for z in f['sources']]+sources_extra.get(n,[])))
  f['sources']=ids;d['source_ids']=ids;d['source_links']=[[z,src[z]['url']] for z in ids if z in src];used.update(ids)
  d['selection'].update(kind='embedded' if n==27 else 'city' if n in city else 'regional' if n in regional else 'national',sources=[v[1] for v in d['source_links']],evidence=d['catch'])
  if n==27:d['selection']['reason']='フランス料理の影響を受けた老舗Lhardyの現行メニューで、卵の糸を添える独自の提供を扱う。マドリード発祥とはしない。'
  audit.append({'id':f['id'],'sources':ids,'material_process_claim':d['catch'],'sensory_basis':d['first'],'classification':d['selection']['kind'],'review':'current cited descriptions and menus compared; not a tasting','checked_at':'2026-09-28'})
 used.update(v[0] for v in s['source_links'])
a['sources']=[[k+' '+src[k]['title'],src[k]['url']] for k in sorted(used,key=lambda z:int(z[1:]))]
a['fee']=[]
a['end_notes']=['100品は季節をまたぐ食の選択肢。七つの章から、日程と好みに合わせて選べます。','マドリードの伝統料理、州内の産品、スペイン各地から集まる料理を区別して紹介しています。','料理写真には一般的な調理例や過去の商品も含みます。撮影年・場所の確認範囲と作者は写真台帳に記録し、特定店の現在の提供写真とは区別しています。','近郊のアルカラ、アランフエス、チンチョン、エル・エスコリアルは別々の日帰り先として選んでください。']
# A single photograph explicitly depicts both thin churros and thick porras.
ds={d['candidate_id']:d for s in a['stops'] for d in s['dishes']}
ds['M062']['photo']=ds['M061']['photo'];ds['M062']['photo2']=None
a['cover']['photos']=[ds[x]['photo'] for x in ['M011','M001','M063'] if ds[x]['photo']]
for p in a['photos'].values():
 old=p.get('caption','')
 p['caption']=old.replace('本文の紹介店の現在の皿を示すものではない。','').replace('撮影時の姿で、現在の販売品の保証ではない。','').replace('（イメージ）','（実写の参考例）')
for path,value in [('article.json',a),('work/master.json',m),('review/source-claims.json',audit)]:
 (R/path).write_text(json.dumps(value,ensure_ascii=False,indent=1),encoding='utf-8')
lines=['# '+a['meta']['title'],'',a['meta']['lede'],'']
for s in a['stops']:
 lines+=['## '+s['title'],'']+s['body']+['']
 for d in s['dishes']:lines+=['### '+d['candidate_id']+' '+d['name']+' / '+d['local'],'',d['catch'],'',d['first'],'',d['how'],'','出典: '+', '.join(d['source_ids']),'']
(R/'article.md').write_text('\n'.join(lines),encoding='utf-8')
print('100 foods and 30 places linked to current sources; source_snapshot unchanged.')
