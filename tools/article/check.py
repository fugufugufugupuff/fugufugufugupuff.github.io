#!/usr/bin/env python3
"""納品前チェック。1つでも X なら終了コード 1。

  python3 tools/article/check.py article.html [--min-photos 15]
"""
import argparse, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html"); ap.add_argument("--min-photos", type=int, default=15)
    a = ap.parse_args()
    c = open(a.html, encoding="utf-8").read()
    ok = [True]
    def p(cond, msg):
        if not cond: ok[0] = False
        print(("OK  " if cond else "X   ") + msg)

    # --- WordPress との衝突 ---
    for tag in ["<!DOCTYPE", "<html", "<head>", "<body", "</body>", "</html>"]:
        p(tag not in c, f"禁止タグなし: {tag}")
    p(c.count("<style") == 1, f"<style> は1個: {c.count('<style')}")
    p(not re.search(r"^\s*body\s*\{", c, re.M), "body{} セレクタなし")
    p(c.count("<h1") <= 1, f"h1 は最大1個（SWELL がタイトルを出す）: {c.count('<h1')}")
    p(not [ch for ch in set(c) if ord(ch) > 0xFFFF], "4バイト文字（絵文字等）なし")
    p(not re.findall(r"@import url\([^)]*&[^)]*\)", c), "@import 内の & はエスケープ済み")
    p(not re.search(r"\sstyle=\"", c), "インライン style 属性なし")
    p("<small" not in c, "<small> なし")

    # --- CSS 整合 ---
    used = set(re.findall(r"var\(--([\w-]+)\)", c)); defined = set(re.findall(r"--([\w-]+)\s*:", c))
    p(not (used - defined), f"CSS 変数 全定義済み: {sorted(used - defined)}")
    hc = set(cl for x in re.findall(r'class="([^"]+)"', c) for cl in x.split())
    css = re.sub(r"url\([^)]*\)", "", c[c.find("<style"):c.find("</style>")])
    cc = set(re.findall(r"\.([A-Za-z_][\w-]*)(?=[{,:.\s>\[])", css))
    missing = [x for x in sorted(hc) if x not in cc and not x.startswith("wp-block")]
    p(not missing, f"クラス 全定義済み: {missing}")
    in_kf, bad = False, []
    for i, l in enumerate(c.split("\n"), 1):
        if "@keyframes" in l: in_kf = True
        if in_kf and re.match(r"\s*}\s*$", l): in_kf = False
        if not in_kf and re.search(r"opacity\s*:\s*0(?![.\d])", l): bad.append(i)
    p(not bad, f"keyframes 外に opacity:0 なし: {bad}")
    small = re.findall(r"font-size:\s*(?:[0-9]|1[0-4])(?:\.\d+)?px", c)
    p(not small, f"14px 以下のフォントなし: {small[:5]}")
    p("width:100vw" not in c.replace(" ", "") or "overflow:hidden" in c.replace(" ", ""), "100vw を使うなら overflow:hidden がある")

    # --- 開閉一致 ---
    for tag in ["section", "div", "figure", "ul", "ol", "table", "p", "h2", "h3", "li", "span", "a", "blockquote", "nav", "header", "main", "article"]:
        o = len(re.findall(r"<" + tag + r"[\s>]", c)); cl = c.count("</" + tag + ">")
        p(o == cl, f"<{tag}> 開閉一致 {o}/{cl}")

    # --- 写真 ---
    imgs = re.findall(r"<img\b[^>]*>", c)
    photos = [t for t in imgs if 'class="stamp' not in t and "wm-assets" not in t and not re.search(r'alt=""', t)]
    p(len(photos) >= a.min_photos, f"写真 {len(photos)} 枚（{a.min_photos} 枚以上）")
    p(not [t for t in imgs if "alt=" not in t], "全 img に alt")
    p(not [t for t in photos if 'loading="lazy"' not in t], "全写真に loading=lazy")
    figs = re.findall(r"<figure[^>]*>(.*?)</figure>", c, re.S)
    nocap = [f for f in figs if "<figcaption" not in f]
    p(not nocap, f"全 figure に figcaption（無し {len(nocap)}）")
    nocred = [f for f in figs if "<figcaption" in f and 'class="credit"' not in f and "profile-photo" not in f]
    p(not nocred, f"全キャプションにクレジット（無し {len(nocred)}）")
    commons = re.findall(r'src="(https://commons\.wikimedia\.org/wiki/Special:FilePath/[^"]+)"', c)
    p(all("?width=" in u for u in commons), f"Commons 画像 全て ?width= 付き ({len(commons)} 枚)")
    p("画像クレジット" in c, "画像クレジット一覧がある")
    p("出典" in c, "出典欄がある")

    # --- 素材カタログの寸法超過 ---
    try:
        cat = {x["url"]: x for x in json.load(open(os.path.join(HERE, "..", "wm-assets", "catalog.json"), encoding="utf-8"))}
        over = []
        for m in re.finditer(r'<img[^>]+src="([^"]+)"[^>]*width="(\d+)"', c):
            u, w = m.group(1), int(m.group(2))
            if u in cat and cat[u]["kind"] == "prop" and w > cat[u]["max_css_px"]:
                over.append(f"{cat[u]['file']} {w}>{cat[u]['max_css_px']}")
        p(not over, f"装飾素材の拡大なし: {over}")
        sheets = [u for u in re.findall(r'url\("?([^")]+)"?\)', c) + re.findall(r'src="([^"]+)"', c) if u in cat and cat[u]["kind"] == "sheet"]
        p(not sheets, f"素材シートを直接使っていない: {sheets}")
    except FileNotFoundError:
        print("--  カタログなし（素材チェック省略）")

    print("\n=== " + ("全項目 OK" if ok[0] else "要修正あり") + " ===")
    sys.exit(0 if ok[0] else 1)

if __name__ == "__main__":
    main()
