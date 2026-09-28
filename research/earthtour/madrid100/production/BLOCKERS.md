# 残っている問題

完成・公開準備完了とは判定しない。本文100品とWP作業下書きは保存済み。

## 料理写真

対応写真の充足は86/100項目。一部だけ1項目、未確保13項目。

|ID|料理|理由と再開箇所|
|---|---|---|
|M003|ガリネハスとエントレシホス|エントレシホスだけを採用。ガリネハスの権利確認済み原画像を追加する。|
|M004|カヌートス|料理そのものの再利用可能画像を確認できず。人物・無関係な検索結果を除外。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M013|ベスーゴのマドリード風|生魚・別地域の調理写真を除外。マドリード風の完成皿を未確保。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M014|ラルディのコンソメ|店名検索でもコンソメ本体の利用可能写真を未確保。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M073|モラタのパルメリタス|一般のパルミエとモラタの商品を混同せず、原典で該当品を同定できる写真を未確保。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M074|マノリートス|人物・別名店の画像を除外。ブランド商品を確認できる実写を未確保。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M081|チャティータス|ロゴ・包装画像は見つかったが、菓子本体の写真を未確保。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M085|イワシ形のチョコレート菓子|市の発表会写真は人物主体。菓子が十分に見える料理写真は未確保。アストゥリアスの別商品を除外。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M088|アランフェスのイチゴ類|列車や一般のイチゴ加工品を除外。アランフエス産と確認できる果実写真を未確保。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M089|アランフェスのアスパラガス|他地域産のアスパラガスや無関係画像を除外。アランフエス産の料理・産品写真を未確保。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M090|マドリードのオリーブ油|ロゴ、一般油、他DOPの油を除外。本文で扱うDOP Madrid商品写真を未確保。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M091|マドリードの養蜂とハチミツ|風景・養蜂作業を料理写真に数えず。該当する蜂蜜商品写真を未確保。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M096|サン・イシドロのリモナーダ|鍋で仕込む途中や他祭礼の写真を除外。サン・イシドロの完成した一杯を未確保。 photos/candidates.jsonl・work/search_log.csvから再開。|
|M097|ジャジョ（ヤヨ）|店内メニューは見つかったが、ヤヨ本体を同定できる写真を未確保。 photos/candidates.jsonl・work/search_log.csvから再開。|

## WordPress実画面の未確認

下書き12704はRESTで読み戻し、本文一致・アイキャッチ・draftを確認した。Application Passwordを付けた通常の下書きフロントURLは404だった。Windows computer-useは現在のブラウザURLを安全に判定できないとして停止し、その後この経路は操作していない。ログイン済みブラウザで下書きを開ける状態から、360・390・768・1024・1440pxのWP実画面QAを再開する。一時公開はしていない。

## 正本の完了ゲート

写真不足13品のためbuild.py checkは未合格。M003の部分写真も機械合格では解消しない。review/checklist.mdは未確認事項を[x]にしていない。通常のpostのゲートは変更していない。ユーザーが素材不足時も可能な工程と下書き保存を求めたため、同じ生成本文を作業下書きとしてREST保存した。写真・名所の実写は103点（料理87原画像、風景16原画像）。28場面中16場面に風景写真があり、正本が目安にする130〜160枚と全章の風景構成には届いていない。

## 根拠の取得範囲

初期86出典にS87〜S101を追加。HTTP取得の成否と主張の照合は分離した。S93は直取得タイムアウトのため検索サービスで取得した公式ページの本文で補完。S97・S100は直接取得不調だがWeb取得で公式本文を確認。S91/S92は最初の200取得を保存して確認した一方、別User-Agentでの再取得が404になった。全ソースの将来の到達性や営業を保証する記録ではない。research/source-retrieval.json、research/added-sources.json、review/source-audit.md参照。

無料素材が世界中に存在しないと断定していない。この作業で検索し原典と被写体を照合した範囲での未確保。許諾依頼・課金・生成画像による穴埋めは行っていない。
