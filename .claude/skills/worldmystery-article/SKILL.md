---
name: worldmystery-article
description: 世界ミステリー図鑑（worldmysteriesencyclopedia.com）の記事を作る・直すときに必ず使う。このリポジトリの装置（tools/article）と素材カタログ（tools/wm-assets）を使った制作手順。調査ルール・写真15枚・毎回新しいデザイン・納品前の3コマンド。
---

# 世界ミステリー図鑑 記事制作（装置版）

同期スキル `worldmystery-article-checklist`（調査ルール・読み味）と `worldmystery-house-design`（読みやすさの基準）は引き続き有効。
**ただし写真は 20 枚ではなく 15 枚以上。納品前チェックはスキル内のスクリプトではなく、このリポジトリの3コマンドを使う。**

## 手順（この順で。飛ばさない）

1. **調査** — 複数言語で最低10回。日本語だけで終わらせない。「まだ解けていないこと」を主役に。
2. **写真 15 枚** — `python3 tools/article/photos.py search "…"` で探し、`info` で取得。NG が出たものは使わない。
   Commons 以外（NASA/NOAA/USGS/博物館の公開素材）は手で追記し、license に出所を書く。
   実写真（カメラで撮ったもの）を 15 枚。版画・SVG・手稿は別枠で追加してよいが数えない。
3. **設計案を提示して承認を待つ** — 次を1枚にまとめる：
   - デザインコンセプト名／色（tokens）／フォント／章立て
   - `tools/wm-assets/CATALOG.md` から選んだ背景 1〜2 点と小物 3〜6 点（直近 3 記事と重複しない）
   - その題材だけの図（平面図・航路図・年表図など）を何にするか
   - SEO タイトル／スラッグ／メタディスクリプション／フォーカスキーワード
   - 確保した実写真の枚数
4. **執筆** — `tools/article/example/article.json` を `tools/article/work/<slug>/article.json` に複製して書く。
   ブロックの種類は `tools/article/README.md`。題材固有の図は `html` ブロックに SVG で描き、CSS は `css_extra` に。
5. **3コマンド** — 全部 OK になるまで直す：
   ```bash
   python3 tools/article/build.py   tools/article/work/<slug>/article.json
   python3 tools/article/check.py   tools/article/work/<slug>/article.html
   node    tools/article/preview.js tools/article/work/<slug>/article.html
   ```
   preview の PNG（mobile / tablet / desktop）を **Read で開いて自分の目で見る**。
   崩れ・色被り・写真の欠け・見出しの飾り線・タイトルの二重表示がないか。
6. **納品** — article.html と、SEO タイトル／スラッグ／メタディスクリプション／フォーカスキーワード／
   調査した言語と回数／実写真の枚数と非カウント素材の内訳／使用ライセンス一覧 を添える。
   `article.json` を commit する（html と preview は commit しない）。

## デザインのルール

- 型を使い回さない。tokens・fonts・backgrounds・図は毎回決め直す。build.py の既定値のまま出さない。
- 本文は 1000px 中央、写真は本文より広く（2列 1520px / 全幅 1760px）。本文 19〜21px、行間 2.0。
- 14px 以下は全用途で禁止。`<small>` 禁止。絵文字など 4 バイト文字禁止。
- 背景写真に文字を載せるときは必ず暗色/明色のオーバーレイ。
- 装飾素材は原寸より大きく出さない（check.py と preview.js が止める）。素材シート（`mystery-*-elements*.png`）は直貼りしない。
- SWELL がタイトルを出すので `own_h1` は false のまま。見出しの飾り線は build.py が消している。

## 初回のみ

```bash
cd tools/article && npm install
```
クラウド環境では preview.js が `HTTPS_PROXY` を自動で使う。画像の読み込み失敗は3回まで自動再試行する。
