# このリポジトリについて

GitHub Pages のサイト本体（`index.html`, `mystery-of-the-ninth-legion/`, `_astro/`, `media/`）と、
**世界ミステリー図鑑（worldmysteriesencyclopedia.com）の記事制作の装置**（`tools/`）が同居している。

## 記事を書く・直すとき

1. まず `.claude/skills/worldmystery-article/SKILL.md` を読む（このリポジトリのスキル。手順の正本）。
2. 装置は `tools/article/`（README.md に全部書いてある）。素材カタログは `tools/wm-assets/`。
3. 初回は `cd tools/article && npm install`。

### クラウド側の同期スキルとの関係（混同しないこと）
- `worldmystery-article-checklist`（同期）: **調査ルールと読み味だけ使う。** 「実写真20枚」と「納品前チェックスクリプト」の節は古い。
  写真は **15 枚以上**、チェックは **このリポジトリの3コマンド**（build / check / preview）が正。
- `worldmystery-house-design`（同期）: 読みやすさの基準（本文1000px・写真は本文より広く・SWELL対策）は有効。
  「再利用ベースCSS」を手で貼る必要はない。同じものが `tools/article/build.py` に入っている。
- `worldmystery-existing-articles`（同期）: 題材の重複確認に使う。

## やらないこと
- `tools/article/build.py` の既定デザインのまま記事を出さない（tokens / fonts / backgrounds / 図は毎回決める）。
- 素材シート（`mystery-*-elements*.png`）を記事に直貼りしない。装飾素材を原寸より大きく出さない。
- 写真は `photos.py` を通したものだけ使う。ライセンス不明の画像は使わない。
- このリポジトリは公開サイトなので、鍵・パスワード・非公開情報を置かない。
- 記事の `article.html` と `preview/` は commit しない（`.gitignore` 済み）。`article.json` は commit する。
