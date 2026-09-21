# article — 記事制作の装置

世界ミステリー図鑑（worldmysteriesencyclopedia.com / SWELL）向け。
**見た目は毎回ゼロから決める。装置がやるのは下回りだけ**（部品の組み立て・写真の権利門番・納品前チェック・3サイズ表示確認）。

```
tools/article/
  new.py       記事の雛形を work/<slug>/ に作る
  photos.py    写真の権利門番（Commons 検索・情報取得・再検証）
  build.py     article.json → WordPress 用 HTML（<style> + フラグメント）
  check.py     納品前チェック（禁止タグ・14px以下・閉じ忘れ・クレジット漏れ・素材の拡大…）
  preview.js   スマホ/タブレット/PC の3サイズで描画 → 横はみ出し・画像欠け・拡大ボケ・小文字を報告
  example/     見本（article.json / photos.json）。これを複製して始める
  work/<slug>/ 記事ごとの作業場所（article.json だけ commit。html と preview は無視される）
```

## 記事1本の流れ

```bash
# 0. 準備（初回のみ）
cd tools/article && npm install          # playwright

# 1. 調査（スキルの調査ルールに従う。複数言語・10回以上）

# 2. 写真を集める（15枚）。使えないライセンスは自動で弾かれる
python3 tools/article/photos.py search "Hadrian's Wall Housesteads" -n 20
python3 tools/article/photos.py info "File:A.jpg" "File:B.jpg" ... -o tools/article/work/<slug>/photos.json
#    NASA/NOAA 等 Commons 以外は photos.json に手で追記（src / credit / license / source_url / w / h）

# 3. 設計案を出して承認をもらう（色・フォント・章立て・背景と小物の選定・題材固有の図）

# 4. 雛形を作って article.json を書く（見本は example/article.json）
python3 tools/article/new.py <slug> "タイトル"

# 5. 組む → 検査 → 見る
python3 tools/article/build.py   tools/article/work/<slug>/article.json
python3 tools/article/check.py   tools/article/work/<slug>/article.html
node    tools/article/preview.js tools/article/work/<slug>/article.html
#    → preview/{mobile,tablet,desktop}.png を自分の目で見る（Read で開く）

# 6. 全部 OK になったら納品（HTML と SEO 情報）
```

## article.json の形

```jsonc
{
  "slug": "ninth-legion",              // 英数ハイフン。CSS のスコープ名になる
  "title": "…", "lead": "…",           // ヒーローの見出しとリード
  "own_h1": false,                     // SWELL がタイトルを出すので通常 false（h1 を作らない）
  "toc": true,                         // 目次を自動生成
  "hero": { "eyebrow": "…", "photo": {写真}, "chips": ["時代：…", "場所：…"] },
  "summary": ["概要1行目", "2行目"],  // 冒頭の「何が謎か」
  "design": {
    "tokens": { "paper": "#…", "accent": "#…", "cool": "#…", … },   // 色・幅。既定は build.py の DEFAULT_TOKENS
    "fonts":  { "head": "…", "sub": "…", "body": "…", "import": "…" },
    "backgrounds": { "hero": "wm-bg-fog-day-01.jpg", "page": null, "texture": "article-paper-texture-v2.webp" }, // wm-assets のファイル名
    "css_extra": ".wp-<slug>-fragment .hero{…}"   // その記事だけの追加 CSS。ここで何でもできる
  },
  "sections": [ { "title": "…", "subtitle": "…", "blocks": [ …ブロック… ] } ],
  "sources": [ { "title": "…", "url": "…", "note": "…" } ]
}
```

### 写真オブジェクト（photos.py info が作る）
`{ "src", "alt", "caption", "credit", "license", "source_url", "w", "h" }` — caption と alt は自分で書く。
credit と license は figcaption と末尾の「画像クレジット」に自動で入る。

### ブロック一覧

| type | 中身 | 用途 |
|---|---|---|
| `p` | `text` | 段落。`**強調**` `__冷静__` `[[ラベル]]` `{URL|リンク文}` `改行\n` が使える |
| `h3` | `text` | 小見出し |
| `ul` / `ol` | `items[]` | 箇条書き |
| `figure` | `photo`, `size`: `text`(1000px) / `wide`(1520px) / `full`(1760px) | 写真1枚。**原寸より広く出さない** |
| `photo-pair` | `photos[2]`, `portrait`: true で 3:4 切り抜き | 2列（1列 ≈ 700px） |
| `photo-grid` | `photos[3]` | 3列（1列 ≈ 480px） |
| `readbreak` | `text` | 赤罫の大きな一文 |
| `note` | `text` | 補足（ティール地） |
| `theory` | `text` | 説の提示（左罫） |
| `quote` | `text`, `who` | 引用 |
| `timeline` | `items[{time,text}]` | 年表 |
| `compare` | `columns[]`, `rows[][]`, `caption` | 説くらべ表（1列目が太字） |
| `table` | `columns[]`, `rows[][]` | 普通の表 |
| `profile` | `name`, `role`, `text`, `photo` | 人物カード |
| `stamp` | `asset`(wm-assets 名), `width`, `pos`: left/center/right | カタログの小物を飾りとして置く。原寸を超える width は自動で切り詰め |
| `band` | `background`(wm-assets 名), `text` | 背景写真つきの全幅の帯 |
| `html` | `html` | 生 HTML。題材固有の SVG 図などはここに。クラスは `css_extra` で定義する |

## デザインを毎回変えるための考え方

1. `tokens` で紙色・インク・アクセント2色を決める。写真から色を拾うと題材に馴染む。
2. `fonts` で見出し書体を変える（明朝／ゴシック／欧文セリフ）。
3. `backgrounds` と `stamp` / `band` で `tools/wm-assets/CATALOG.md` の素材を **1記事 3〜6点** 使う。
4. 題材固有の図（平面図・航路図・年表図）は `html` ブロックに SVG で描く。これが記事の顔になる。
5. それでも足りない見た目は `css_extra` で上書きする。build.py は触らない。

## 装置が止めるもの（check.py / preview.js）

禁止タグ・`<style>` 複数・`body{}`・h1 の二重・4バイト文字・`@import` の `&`・インライン style・`<small>`・
未定義の CSS 変数/クラス・keyframes 外の `opacity:0`・14px 以下・開閉不一致・写真 15 枚未満・alt 無し・
figcaption 無し・クレジット無し・Commons の `?width=` 無し・出典欄無し・装飾素材の拡大・素材シートの直貼り・
横スクロール・画像の欠け・原寸の 1.15 倍を超える表示・15px 未満で描画された文字。
