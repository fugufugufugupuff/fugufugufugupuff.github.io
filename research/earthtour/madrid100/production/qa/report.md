# 表示検査記録

対象：最終out/preview.html。Playwright + Microsoft Edge、device scale factor 1。WP表示とは別のローカルHTML。

|幅|横はみ出し|画像取得失敗|アンカー切れ|目次文字切れ|H1|料理|
|---|---|---|---|---|---|---|
|360|0|0|0|0|1|100|
|390|0|0|0|0|1|100|
|768|0|0|0|0|1|100|
|1024|0|0|0|0|1|100|
|1440|0|0|0|0|1|100|

lazy-load画像も読み込みを待って検査。ページ全体のDOM検査と、冒頭・目次・料理001・料理061・末尾・出典のブラウザスクリーンショットを保存。画像がない13品は「画像URL読み込み失敗0」に含まれず、素材不足として別管理。

初回の追加検査で目次の長い料理名45表示が切れる問題を検出。本文の正式名を変えず、目次だけ短い名称とフルネームtitleへ変更し、5幅で再検査した。写真未確保カードの空画像枠と番号シールの重なりを除去。スマホのラベルを短くし、未確認の価格計算・同一座標の地図・架空の時刻を表示しない。

写真元画像103点のcontact sheetを目視し、料理と対象、部分写真、風景を区別。元画像の比率・撮影年・改変なしを台帳化。全画面・全ブラウザの網羅検査ではない。

WP：wp-readback.jsonでID12704/draft/featured_media12601/本文完全一致を確認。wordpress-browser.jsonはHTTP404と未実施を記録。wp-preview-unavailable-360.pngは記事画面の検査証拠ではなく、取得できなかった画面の証拠。

screenshots: local-<width>-top/toc/main/middle/end/sources.png。写真原画像QA: photos/sheets/original-review-*.jpg、scenes-original-*.jpg、final-foods-originals.jpg。PDF目視: source-S33-04/05.png、source-S95-page2.png。
