# tour100 — 「行った気になる100品ツアー」記事の装置

原稿JSONを1つ書くと、どの国の記事でも同じ型（デザインと構成）で組み上がる。設計の考え方は [DESIGN.md](DESIGN.md)。
どのコーディングエージェント（Claude Code、Codex など）でも同じ手順で使える。作業ルールはリポジトリ直下の `AGENTS.md`、各工程の指示書は `briefs/`。

## 準備（最初の1回）
料理の選定は [SELECTION.md](SELECTION.md) が必須。候補調査の段階から各品に土地との関係と出典を記録する。全記事のcheck/postに適用し、既存記事も未整備なら止まる。postでは選定検査と原稿に対応した選定レビューを`--force`でも省略できない。自動検査は根拠の内容を証明しないため、出典を読む編集レビューも行う。

```
pip install jinja2 budoux pillow
npm i -g playwright   # 画面の自動検査に使う（Chromium が要る）
```
WordPress の Application Password は、環境変数 `EARTHTOUR_WP_APP_PASSWORD` に入れる（ユーザー名は `earthtour`）。値をファイルやチャットに書かない。

## 1本の記事を作る流れ
| # | やること | コマンド |
|---|---|---|
| 1 | ひな型を作る | `python3 tour100/build.py new hanoi-100-dishes --place ハノイ --theme southeast-asia --currency ₫ --rate 0.0059 --decimals 0` |
| 2 | 調べる：`research/logistics.md`（入国・航空・空港・交通・通貨・安全・行事と定休日）と `research/dishes.md`（候補120品前後と旅程案） | 指示書 `briefs/01_logistics.md`・`briefs/02_dishes.md` |
| 3 | 原稿 `article.json` を書く（100品・30〜35の食事）。meta・days・basics・fee・end_notes は logistics から、stops は旅程案から | 指示書 `briefs/03_stops.md` |
| 4 | 原稿を検査する | `python3 tour100/build.py check hanoi-100-dishes` |
| 5 | 写真：要る写真を出す → 探す → 見て選ぶ → 元ページで権利を確かめる（指示書 `briefs/04_photos.md`） | `photos.py wants` → `photos.py search` → `photos.py sheet <タグ>` を見て `photos.py pick` → `photos.py todo` が0件になるまで → `photos.py verify` |
| 6 | 写真を原稿に結びつけ、WordPress に取り込む | `photos.py attach` → `photos.py import` |
| 7 | 取り込んだ写真の寸法と srcset を取る | `python3 tour100/build.py media hanoi-100-dishes` |
| 8 | 組み立てる | `python3 tour100/build.py build hanoi-100-dishes` → `out/preview.html`・`out/post.html` |
| 9 | 見直す：チェックリストの全項目を確かめて `[x]` に。写真は `out/review/dishes_*.jpg` を見て料理名と照らす | `python3 tour100/build.py review hanoi-100-dishes` → `review/checklist.md`（指示書 `briefs/05_review.md`） |
| 10 | 画面を自動で検査する（360/390/768/1280px） | `python3 tour100/build.py qa hanoi-100-dishes` → `out/qa/` |
| 11 | 投稿する（見直しが全部 `[x]` でないと止まる。初回は下書き） | `python3 tour100/build.py post hanoi-100-dishes` |
| 12 | 公開して、公開ページを検査する | WordPress で公開 → `python3 tour100/build.py qa hanoi-100-dishes --live` → `out/qa-live/` |

`photos.py` は `python3 tour100/photos.py <コマンド> <記事>`。タグは料理 `d001`〜`d100`、風景 `s:d1-1530`（DAY と時刻）、表紙 `hero`。検索語は原稿の `local`（原語名）と `place_name` から作る。合わないときは料理や STOP に `photo_q: ["…"]` を書くか、`photos.py search <記事> <タグ> --q "…"` で足す。その店・その品そのものでない写真は `pick --image` にする（キャプションに「イメージ」が入る）。

`qa` は、ページが読む画像・CSS・フォントを手元に落としてから検査する。ネットワークや証明書の事情に左右されず、どの環境でも同じ条件で比べられる。`--live` で取れない画像があれば、公開ページの画像切れとして失敗にする。

Windows でインストール済み Edge を使う場合は `TOUR100_BROWSER_CHANNEL=msedge` を環境変数に設定できる。任意の Chromium 実行ファイルを指定する場合は `TOUR100_CHROMIUM_PATH` を使う。どちらも未設定なら Playwright 標準の Chromium を使う。

写真候補をまとめて目視するときは `photos.py sheet-grid <記事> d001 d002 ... --name <一覧名>`。`--offset` で候補を送れ、`--source commons` 等で出典を絞れる。候補の番号は変わらず、自動採用はしない。原稿への結び付けは料理名の一致を要求するため、別表記を使うときは料理の `aka` に写真台帳側の名前を明記する。

デザイン（`assets/tour100.css`）を直したら `python3 tour100/build.py css` を1回実行する。サイトの共通CSS（WGE Design System の bundle `t100`）が更新され、すべての100品ツアー記事に反映される。記事を作り直す必要はない。

## テーマ（国・地域）
`python3 tour100/build.py themes` で一覧が出る。`meta.theme` に名前を書くだけで、色と「土地の飾り」（紋章・植物画・古地図・布の柄など、サイトにアップ済みのパブリックドメイン図版）が切り替わる。

| theme | 使う図版の例 |
|---|---|
| uk | 英国の紋章、紅茶の植物画、1750年の世界地図、古いメニュー |
| europe | 額縁のカルトゥーシュ、レモンと胡椒の植物画、パリのカフェのポスター |
| east-asia / japan | 雲龍の錦、茶の植物画、マッチ箱ラベル、食券 |
| southeast-asia | 生姜・唐辛子・カルダモンの植物画、スパイス市場 |
| south-asia | カラムカリ布、胡椒・クローブの植物画 |
| middle-east | イズニック・タイル、カシャーン・タイル |
| africa | ケンテ布、ゼリージュ、アンカラ布、カカオとコーヒーの植物画 |
| latin-america | サラペ、メキシコの布、タラベラ焼 |
| north-america | 19世紀のホテルのメニュー |
| oceania | タパ布 |

記事だけ少し変えたいときは `theme_override` に `colors` や `deco` を書く（テーマ本体は書き換えない）。新しい国が増えたら `themes.json` にプリセットを足す。

## article.json の書式
全体の見本は `examples/article.template.json`、実例は `london-100-dishes/article.json`。

- `meta`：タイトル、スラッグ、カテゴリー（100品ツアーは 73）、地名（`place_en` は写真検索に使う英語名）、導入文、旅の月（`month`）と値段を調べた月（`as_of`）、テーマ、通貨（`symbol`・`rate`＝1単位あたりの円・`decimals`）
- `days`：日ごとの扉（日付、見出し、一言）
- `stops`：食事ごと。時刻、区分（朝ごはん・昼ごはん…）、エリア、見出し、座標（`lat`・`lng`・円の半径 `r`）、店の名前・時間・行き方、本文、写真、注文の一言、豆知識2つ、次への移動、そして `dishes`
- `dishes`：料理ごと。名前、原語名、短い説明、キャッチ、一口目、食感3つ、味メーター（甘・塩・酸・辛・コクを0〜3）、ジャンル印、食べ方、どこで、値段（`seal` 値札の表記・`value` 会計に入れる数・セット込みなら `included: true`）、写真
- `photos`：写真IDごとに URL・元ページ・作者・ライセンス（by／by-sa／cc0／pdm）・写っているもの・キャプション

`fee`（巻末の旅費）の値に `"auto"` と書くと、100品の会計の合計（通貨と円）が入る。

## 検査で止まるもの
- 訪問記録を示す `VISITED` 表示、本文参照資料の欠落・URL不備、生成結果にモデルコースの説明がないもの。
- `post --force` でも原稿エラー・目視レビュー未完了を省略できない。`build --force` はローカル確認用だけであり、投稿の許可ではない。
- 本文の伝説・諸説は「と言われている」等で区別して残す。機械検査は史実やライセンスの正しさを証明しない。導入・本文・キャプションの実食/訪問表現は編集レビューで確認する。
- 料理がちょうど100品でない、同じ料理が2回ある
- 必須の項目が空、写真IDが存在しない、写真がない料理がある
- 写真のライセンスが CC BY／CC BY-SA／CC0／PDM 以外
- （注意）WordPress に取り込んでいない写真、会計に入らない値段
- 画面：横はみ出し、要素のはみ出し、画像切れ（`qa` が失敗を返す）。見出しの泣き別れも数える

## ファイル
```
tour100/
  build.py            装置本体（new / check / media / build / review / qa / css / post / themes）
  photos.py           写真工程（wants / search / sheet / pick / todo / verify / attach / import）
  qa.js               画面の自動検査
  themes.json         国・地域のプリセット
  templates/          article.html.j2 と parts/（表紙・しおり・もくじ・DAY扉・食事・料理カード・巻末）
  assets/             tour100.css（サイトの共通CSSとして配信）・tour100.js（地図）
  briefs/             各工程の指示書（調べる・旅程・原稿・写真・見直し）
  examples/           article.template.json（空のひな型）
  site/               サイトの WGE Design System スニペット（t100 を足した版と、足す前の控え）
```

見直しのチェックは原稿全体に対応する。料理名・店・本文・写真などを変更すると、全項目の確認済み状態が失効する。同じ番号の料理を差し替えたときも、以前のチェックを引き継がない。店・価格はAGENTS.mdのとおり概算や探し先の例を使えるが、確認済みの実売・提供店とは区別して書く。
