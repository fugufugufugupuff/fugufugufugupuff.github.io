#!/usr/bin/env python3
"""新しい記事の作業場所を作る。

  python3 tools/article/new.py <slug> ["タイトル"]
  → tools/article/work/<slug>/article.json（写真を空にした雛形）
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: new.py <slug> [title]")
    slug = sys.argv[1]
    title = sys.argv[2] if len(sys.argv) > 2 else "（タイトル）"
    d = os.path.join(HERE, "work", slug)
    path = os.path.join(d, "article.json")
    if os.path.exists(path):
        sys.exit(f"already exists: {path}")
    os.makedirs(d, exist_ok=True)
    art = {
        "slug": slug, "title": title, "lead": "（リード。何が謎かを2行で）", "own_h1": False, "toc": True,
        "hero": {"eyebrow": "（分類 / 状態）", "photo": None, "chips": ["時代：", "場所：", "状態：未解決"]},
        "summary": ["（概要1）", "（概要2）"],
        "design": {
            "_memo": "毎回ここを決め直す。tokens=色, fonts=書体, backgrounds=wm-assets の背景名, css_extra=この記事だけの CSS",
            "tokens": {"paper": "", "paper-2": "", "paper-3": "", "accent": "", "accent-deep": "", "cool": "", "cool-deep": "", "cool-soft": ""},
            "fonts": {},
            "backgrounds": {"hero": None, "page": None, "texture": None},
            "css_extra": "",
        },
        "sections": [
            {"title": "（章1）", "subtitle": "", "blocks": [
                {"type": "p", "text": "（本文）"},
                {"type": "figure", "size": "wide", "photo": None},
            ]},
        ],
        "sources": [{"title": "", "url": "", "note": ""}],
    }
    json.dump(art, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"created {path}")
    print("次: photos.py で写真を集めて photos.json に保存 → article.json の photo/photos に貼る → build / check / preview")

if __name__ == "__main__":
    main()
