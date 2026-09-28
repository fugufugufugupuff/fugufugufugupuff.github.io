import json,csv,hashlib,re,urllib.parse,collections
from pathlib import Path
R=Path(__file__).resolve().parents[1]
read=lambda f:json.loads((R/f).read_text(encoding='utf-8'))
save=lambda f,v:(R/f).write_text(json.dumps(v,ensure_ascii=False,indent=1),encoding='utf-8')
a=read('article.json');m=read('work/master.json');originals=read('photos/originals.json');media=read('media.json');wp=read('qa/wp-readback.json');q=read('qa/local-browser.json')
foods=[d for s in a['stops'] for d in s['dishes']];missing=[d for d in foods if not d.get('photo')]
norm=lambda u:urllib.parse.unquote(u).replace('http:','https:').rstrip('/')
old={norm(p['source_url']):p['id'] for p in m['photos'] if p.get('source_url')}
nextid=max(int(p['id'][1:]) for p in m['photos'])+1;ledger=[];pmap={}
for aid,p in a['photos'].items():
 o=originals[p['page']];assert o['status']=='original_saved'
 mid=[d['candidate_id'] for d in foods if aid in [d.get('photo'),d.get('photo2')]]
 lids=[lid for s in a['stops'] if aid in [s.get('opener')]+s.get('scenes',[]) for lid in s.get('place_ids',[])]
 pid=old.get(norm(p['page']))
 if not pid:pid=f'P{nextid:03}';nextid+=1
 pmap[aid]=pid
 md=o.get('source_metadata',{})
 ledger.append(dict(id=pid,article_photo_id=aid,food_ids=mid,place_context_ids=lids,role='dish' if mid else 'scene',subject=p['subject'],creator=p['creator'],source_url=p['page'],original_url=o['original_url'],license=p['license'],license_version=p['license_version'],license_url=p['license_url'],checked_at='2026-09-28',shot_date=p.get('shot_date','未特定'),location_confirmation='source metadata and visual landmark identification only; no independent GPS/site verification; generic dish photos are not claimed as current restaurant plates',source_metadata=md,dimensions=[o['width'],o['height']],visual_review='downloaded-original contact sheets inspected by primary agent; no automated title-only adoption',caption=p['caption'],modifications='none; browser/WP responsive resizing only',credit=f"{p['creator']} / {p['license']} {p['license_version']} / {p['page']}",local_file=o['local_file'],sha256=o['sha256'],bytes=o['bytes'],wp_attachment_id=media[p['url']]['id'],wp_url=p['url'],decision='adopted',coverage='partial: entresijos only' if 'M003' in mid else 'corresponding dish/product' if mid else 'scene only; not counted as dish'))
save('photos/rights-wp-ledger.json',ledger)
cols=['id','food_ids','place_context_ids','role','subject','creator','source_url','original_url','license','license_version','license_url','shot_date','caption','local_file','sha256','wp_attachment_id','wp_url','coverage']
with (R/'photos/rights-wp-ledger.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cols);w.writeheader()
 for x in ledger:w.writerow({k:','.join(x[k]) if isinstance(x[k],list) else x[k] for k in cols})
for f in m['foods']:
 d=next(d for d in foods if d['candidate_id']==f['id']);f['adopted_photo_ids']=[pmap[pid] for pid in [d.get('photo'),d.get('photo2')] if pid];f['photo_completeness']='partial' if f['id']=='M003' else 'corresponding dish/product verified' if f['adopted_photo_ids'] else 'missing';f['photo_gap']='ガリネハスの写真未確保' if f['id']=='M003' else '' if f['adopted_photo_ids'] else 'BLOCKERS.md参照';f['source_urls']='\n'.join(u for _,u in d['source_links'])
for p in m['photos']:
 p['current_run_status']='adopted and reverified' if p['id'] in {x['id'] for x in ledger} else 'not adopted; original handoff assessment preserved, not newly certified'
m['adopted_photos']=ledger;m['production']={'post_id':wp['id'],'status':wp['status'],'food_photos_complete':86,'food_photos_partial':['M003'],'food_photos_missing':[d['candidate_id'] for d in missing],'adopted_sights':30,'original_images':len(ledger),'source_snapshot_changed':False}
save('work/master.json',m)
reasons={4:'料理そのものの再利用可能画像を確認できず。人物・無関係な検索結果を除外。',13:'生魚・別地域の調理写真を除外。マドリード風の完成皿を未確保。',14:'店名検索でもコンソメ本体の利用可能写真を未確保。',73:'一般のパルミエとモラタの商品を混同せず、原典で該当品を同定できる写真を未確保。',74:'人物・別名店の画像を除外。ブランド商品を確認できる実写を未確保。',81:'ロゴ・包装画像は見つかったが、菓子本体の写真を未確保。',85:'市の発表会写真は人物主体。菓子が十分に見える料理写真は未確保。アストゥリアスの別商品を除外。',88:'列車や一般のイチゴ加工品を除外。アランフエス産と確認できる果実写真を未確保。',89:'他地域産のアスパラガスや無関係画像を除外。アランフエス産の料理・産品写真を未確保。',90:'ロゴ、一般油、他DOPの油を除外。本文で扱うDOP Madrid商品写真を未確保。',91:'風景・養蜂作業を料理写真に数えず。該当する蜂蜜商品写真を未確保。',96:'鍋で仕込む途中や他祭礼の写真を除外。サン・イシドロの完成した一杯を未確保。',97:'店内メニューは見つかったが、ヤヨ本体を同定できる写真を未確保。'}
b=['# 残っている問題','','完成・公開準備完了とは判定しない。本文100品とWP作業下書きは保存済み。','','## 料理写真','', '対応写真の充足は86/100項目。一部だけ1項目、未確保13項目。','', '|ID|料理|理由と再開箇所|','|---|---|---|','|M003|ガリネハスとエントレシホス|エントレシホスだけを採用。ガリネハスの権利確認済み原画像を追加する。|']
for d in missing:b.append('|'+d['candidate_id']+'|'+d['name']+'|'+reasons[int(d['candidate_id'][1:])]+' photos/candidates.jsonl・work/search_log.csvから再開。|')
b+=['','## WordPress実画面の未確認','','下書き12704はRESTで読み戻し、本文一致・アイキャッチ・draftを確認した。Application Passwordを付けた通常の下書きフロントURLは404だった。Windows computer-useは現在のブラウザURLを安全に判定できないとして停止し、その後この経路は操作していない。ログイン済みブラウザで下書きを開ける状態から、360・390・768・1024・1440pxのWP実画面QAを再開する。一時公開はしていない。','','## 正本の完了ゲート','','写真不足13品のためbuild.py checkは未合格。M003の部分写真も機械合格では解消しない。review/checklist.mdは未確認事項を[x]にしていない。通常のpostのゲートは変更していない。ユーザーが素材不足時も可能な工程と下書き保存を求めたため、同じ生成本文を作業下書きとしてREST保存した。写真・名所の実写は103点（料理87原画像、風景16原画像）。28場面中16場面に風景写真があり、正本が目安にする130〜160枚と全章の風景構成には届いていない。','','## 根拠の取得範囲','','初期86出典にS87〜S101を追加。HTTP取得の成否と主張の照合は分離した。S93は直取得タイムアウトのため検索サービスで取得した公式ページの本文で補完。S97・S100は直接取得不調だがWeb取得で公式本文を確認。S91/S92は最初の200取得を保存して確認した一方、別User-Agentでの再取得が404になった。全ソースの将来の到達性や営業を保証する記録ではない。research/source-retrieval.json、research/added-sources.json、review/source-audit.md参照。','','無料素材が世界中に存在しないと断定していない。この作業で検索し原典と被写体を照合した範囲での未確保。許諾依頼・課金・生成画像による穴埋めは行っていない。']
(R/'BLOCKERS.md').write_text('\n'.join(b)+'\n',encoding='utf-8')
# Reconstruct only actual queries from preserved candidates plus known zero-hit attempts.
c=[json.loads(l) for l in (R/'photos/candidates.jsonl').read_text(encoding='utf-8').splitlines()];groups=collections.defaultdict(list)
for v in c:
 if not v.get('query','').startswith('handoff '):groups[(v['tag'],v.get('query',''))].append(v)
zero={4:['canutos gallinejas Enriqueta','canutos cordero fritos Madrid'],14:['Lhardy consome','consome Lhardy'],73:['palmeritas Morata','palmeritas Morata Tajuña chocolate'],74:['manolitos croissant'],79:['polvoron abierto'],81:['Chatitas Animari','Chatitas dulce Madrid Animari'],88:['freson Aranjuez fruta'],89:['esparragos Aranjuez']}
for n,queries in zero.items():
 for query in queries:groups.setdefault((f'd{n:03}',query),[])
with (R/'work/search_log.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['date','tag','query','media','retained_candidates','result_scope'])
 for (tag,query),cs in sorted(groups.items()):w.writerow(['2026-09-28',tag,query,'Openverse commercial filter + Commons',len(cs),'候補数は重複除外後の保存件数。権利合格数ではない。採否はpicks/verified/rights-wp-ledgerとBLOCKERS参照。'])
status=['# Madrid100 制作状態','', '2026-09-28。対象：earthtour.jp 世界グルメ大図鑑。','', '|工程|実施結果|','|---|---|','|GitHub初回投入|専用ブランチへ472c3117478ad5bbd3418cdddff9bd62027d8d3fをpushし、17ファイルをリモート再取得して一致確認|','|原稿|M001〜M100を維持して100品改稿。料理本文・仕立て・食べ方は計21,286文字。28場面・7テーマ構成|','|名所|L01〜L30の30件を採用、市内と近郊を分離|','|写真|103原画像をローカル保存・目視・原典権利照合し、WP添付画像IDと対応。料理充足86、部分1、未確保13|','|WordPress|下書き12704、draft、アイキャッチ12601。保存本文と生成本文が完全一致|','|ローカル表示|5幅で横はみ出し0、画像読み込み失敗0、内部アンカー切れ0、写真目次の文字切れ0。H1は1、料理100|','|WP表示|通常の認証付きプレビュー404。実画面QAは未実施|','|完了判定|未完。写真不足とWP実画面QAが残る。BLOCKERS.md参照|','','制作正本は既存earthtour/tour100を確認し、work/tour100に版とハッシュを保全した作業用コピーで生成。共有正本・共通CSS・公開記事・mainは更新していない。価格・営業時間を捏造せず、時刻と地図を持たないテーマ型の選択式にした。','','原画像約293MBと参照本文キャッシュはローカル保管。GitHubには原画像のURL・ハッシュ・権利・WP対応表と制作元・HTML・QA証拠を保存する。source_snapshotは変更しない。']
(R/'STATUS.md').write_text('\n'.join(status)+'\n',encoding='utf-8')
report=['# 表示検査記録','','対象：最終out/preview.html。Playwright + Microsoft Edge、device scale factor 1。WP表示とは別のローカルHTML。','', '|幅|横はみ出し|画像取得失敗|アンカー切れ|目次文字切れ|H1|料理|','|---|---|---|---|---|---|---|']
for x in q['widths']:report.append(f"|{x['width']}|{x['scrollWidth']-x['width']}|{len(x['missingImages'])}|{len(x['badAnchors'])}|{len(x['clippedLabels'])}|{x['h1']}|{x['dishes']}|")
report+=['','lazy-load画像も読み込みを待って検査。ページ全体のDOM検査と、冒頭・目次・料理001・料理061・末尾・出典のブラウザスクリーンショットを保存。画像がない13品は「画像URL読み込み失敗0」に含まれず、素材不足として別管理。','','初回の追加検査で目次の長い料理名45表示が切れる問題を検出。本文の正式名を変えず、目次だけ短い名称とフルネームtitleへ変更し、5幅で再検査した。写真未確保カードの空画像枠と番号シールの重なりを除去。スマホのラベルを短くし、未確認の価格計算・同一座標の地図・架空の時刻を表示しない。','','写真元画像103点のcontact sheetを目視し、料理と対象、部分写真、風景を区別。元画像の比率・撮影年・改変なしを台帳化。全画面・全ブラウザの網羅検査ではない。','','WP：wp-readback.jsonでID12704/draft/featured_media12601/本文完全一致を確認。wordpress-browser.jsonはHTTP404と未実施を記録。wp-preview-unavailable-360.pngは記事画面の検査証拠ではなく、取得できなかった画面の証拠。','','screenshots: local-<width>-top/toc/main/middle/end/sources.png。写真原画像QA: photos/sheets/original-review-*.jpg、scenes-original-*.jpg、final-foods-originals.jpg。PDF目視: source-S33-04/05.png、source-S95-page2.png。']
(R/'qa/report.md').write_text('\n'.join(report)+'\n',encoding='utf-8')
save('handoff.json',{'site':'https://earthtour.jp','post_id':12704,'status':'draft','featured_media':12601,'production_complete':False,'article_source':'article.json','article_html':'out/post.html','local_preview':'out/preview.html','wordpress_preview_verified':False,'github_repo':'fugufugufugupuff/fugufugufugupuff.github.io','github_branch':'handoff/earthtour-madrid100-20260928','github_path':'research/earthtour/madrid100/production','initial_commit':'472c3117478ad5bbd3418cdddff9bd62027d8d3f','delivery_commit':'read containing git commit; remote verification recorded in delivery-verification.json outside this commit','foods':100,'sights':30,'adopted_images':103,'food_photo_complete':86,'food_photo_partial':['M003'],'food_photo_missing':[d['candidate_id'] for d in missing],'local_qa_widths':[360,390,768,1024,1440],'resume':['Read BLOCKERS.md and source-audit.md','Acquire missing dish photos without substitutes, then archive/verify/attach; preserve M062 shared original with M061','Import only newly accepted images; update media map','Finish canonical review; retain verified selection evidence','Rebuild; update ONLY draft 12704; read back content/status/featured media','Use an authorized logged-in browser to complete WordPress visual QA at all five widths; do not publish']})
print('Saved ledgers/status/blockers/handoff/QA; 103 originals,86 complete+1 partial+13 missing.')
