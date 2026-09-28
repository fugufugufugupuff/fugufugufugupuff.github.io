"""Map the preserved Madrid handoff into the installed tour100 schema.
Unreviewed evidence and absent pictures remain explicitly unapproved.
"""
import json, re
from pathlib import Path
R=Path(__file__).resolve().parents[1]
m=json.loads((R/'work/master.json').read_text(encoding='utf-8'))
a=json.loads((R.parent/'tour100/examples/article.template.json').read_text(encoding='utf-8'))
a['meta'].update(title='マドリード100品グルメツアー｜煮込み、バル、祝祭の菓子から近郊の味まで',slug='madrid-100-dishes-tour',place='マドリード',place_short='マドリード',place_en='Madrid Spain',kicker='行った気になる100品ツアー　スペイン',lede='ひよこ豆のコシード、イカを挟んだパン、チョコレートに浸すチュロス。マドリードの食卓は、昔ながらの煮込みと酒場の小皿、祝祭の菓子に彩られている。旧市街から王宮、美術館、近郊の菜園へ。首都の名物とスペイン各地から集まる味を、100品の選択肢でたどろう。',excerpt='マドリードの郷土料理、内臓料理、バルの小皿、菓子、飲み物、近郊の特産品を100項目で紹介。王宮や市場、美術館と食をつなぐ選択式の街歩き。',plan_sub='七つのテーマで選ぶ街歩きモデル。100品は食べ切る旅程ではなく、季節と好みに合わせた選択肢。近郊四方面は別々の日帰り先として選ぶ。',month='季節で選ぶ旅',as_of='2026年9月28日',theme='europe',currency={'symbol':'€','rate':170,'decimals':2,'position':'prefix'},rate_text='円換算は€1＝170円と仮定する場合の目安',postmark_label='MODEL TOUR')
daytitles=['ひよこ豆の鍋と王宮の街','旧市街でパンと小皿','酒場から各地の食卓へ','首都に集まる魚介と米','揚げ菓子と祝祭の暦','菓子店から近郊の畑へ','一杯に映るマドリード']
a['days']=[{'day':i+1,'date':'選べる街歩き','title':t,'sub':'この章から気になる一品を選ぶ'} for i,t in enumerate(daytitles)]
a['basics']=[['100品の選び方','まずはコシードかイカサンドを一食の軸に。小皿、菓子、飲み物は別の機会にも選べる。'],['土地との関係','マドリードの伝統と州内の特産品を中心に、首都に集まるスペイン各地の料理も含む。'],['季節','サン・イシドロの菓子は5月、アルムデナの冠形菓子は11月、ロスコンは年末年始。'],['近郊','アルカラ、アランフエス、チンチョン、エル・エスコリアルは市内散策と別の日帰り先。']]
a['cover']={'photos':[],'tag_dish':11}; a['photos']={}; a['links']=[]
a['fee']=[['料理の価格','注文する店、量、持ち帰りか着席かで異なる。'],['近郊の交通','市内の移動と分け、選んだ行先ごとに見積もる。']]
a['end_notes']=['100品は季節をまたぐ食の選択肢で、1人で七日間に食べ切る想定ではない。','味と食感は材料と調理法から紹介している。','写真の撮影場所と、本文で紹介する店の現在の皿は別に扱う。','施設の見学と飲食は別の予定。近郊四都市は同じ日にまとめない。']
a['sources']=[[s['id']+' '+s['title'],s['url']] for s in m['sources']]
a['stops']=[]
groups=[(1,4),(5,7),(8,10),(11,14),(15,17),(18,20),(21,24),(25,28),(29,31),(32,35),(36,39),(40,42),(43,46),(47,50),(51,54),(55,58),(59,62),(63,65),(66,68),(69,71),(72,75),(76,79),(80,82),(83,85),(86,89),(90,92),(93,96),(97,100)]
titles=['一つの鍋から始まる食卓','羊の部位、豚の耳','パンと鶏の古い料理','広場で選ぶイカとタラ','卵を崩し、肉を煮込む','パンも豆もスープに','バルの四つの定番','ニンニクと酢の小皿','ゴヤの礼拝堂と鶏料理','切って味わう加工肉','北の味と詰め物','肉のパイから窯の焼き物','北スペインの食卓','豆、肉、魚の食べ比べ','魚介を冷たく、熱く','市場で貝と米を選ぶ','冷たいスープ、熱い揚げ生地','春のパン菓子と輪形菓子','聖人と守護聖母の菓子','薄焼きと祝いの輪','ソルの菓子店をのぞく','蜂蜜、ナッツ、冬の菓子','スミレとアルカラの層','名前と形が楽しい菓子','近郊の町から届く産品','油と蜂蜜、濃いチョコレート','ミルクと酒場の一杯','街の酒、州の酒']
for i,((lo,hi),title) in enumerate(zip(groups,titles)):
    day=i//4+1
    fs=m['foods'][lo-1:hi]
    a['stops'].append({'id':f'd{day}s{i+1:02d}','day':day,'time':['09:00','12:00','16:00','20:00'][i%4],'slot':'食の寄り道','area':'マドリード','area_en':'Madrid','label':title,'title':title,'subtitle':'郷土の味と、各地から集まる味','pm':'マドリード','lat':40.4168,'lng':-3.7038,'r':500,'place_name':'マドリードの酒場・食堂・専門店','hours':'営業日と季節の提供は各店の公式案内で確認。','access':'この章は料理選びの案内。地図は市中心部の目安。','info':[],'body':[],'opener':None,'scenes':[],'phrase':{'en':'¿Tienen '+fs[0]['es']+'?','kana':'ティエネン（料理名）？','ja':fs[0]['jp']+'はありますか。'},'tips':[],'move':{'icon':'🚶','text':'次の章も食事の選択肢として読む。'},'photo_q':['Madrid streets'],'dishes':[]})
    for f in fs:
        d={'candidate_id':f['id'],'name':f['jp'],'local':f['es'],'gloss':f['definition'],'catch':f['body'],'first':'','tex':[],'how':'','shop':'','genre':['菓子'] if 61<=int(f['id'][1:])<=85 else ['飲み物'] if int(f['id'][1:])>=92 else ['軽食'],'taste':{},'price':{'seal':'店・量による','value':None,'included':False},'photo':None,'photo2':None,'photo_tag':'d'+f['id'][1:],'photo_q':[f['es'],f['es']+' Madrid'],'selection':{'kind':'','reason':f['relation'],'distinct':f['definition'],'evidence':'','sources':f['source_urls'].splitlines()},'review_status':'needs_editorial_review'}
        a['stops'][-1]['dishes'].append(d)
(R/'article.json').write_text(json.dumps(a,ensure_ascii=False,indent=1),encoding='utf-8')
c=[]
for p in m['photos']:
    if not p['usable']: continue
    for mid in p['food_ids']:
        c.append({'tag':'d'+mid[1:],'src':'commons' if 'commons.wikimedia' in p['source_url'] else 'flickr','title':p['title'],'license':None,'creator':p['author'],'url':p['image_url'],'thumb':p['image_url'],'page':p['source_url'],'query':'handoff '+p['id'],'handoff_id':p['id'],'handoff_caution':p['caution'],'role':p['role']})
(R/'photos/candidates.jsonl').write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in c),encoding='utf-8')
print('100 foods mapped; original source IDs retained; no image or source automatically approved.')
