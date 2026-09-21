#!/usr/bin/env python3
"""写真の権利門番。Wikimedia Commons から情報を取り、許可ライセンス以外はエラーで止める。

使い方:
  python3 tools/article/photos.py search "Hadrian's Wall" [-n 20]
      → 候補一覧（ファイル名・ライセンス・寸法）。ライセンス不可のものは印付き
  python3 tools/article/photos.py info "File:A.jpg" "File:B.jpg" ... [-o photos.json]
      → article.json にそのまま貼れる写真オブジェクトを出力。1枚でも不可なら終了コード 1
  python3 tools/article/photos.py check article.json
      → article.json 内の Commons 写真を再検証（ライセンス・実在）

許可: パブリックドメイン / CC0 / CC BY / CC BY-SA（各バージョン）。
不可: NC・ND を含むもの、Fair use、ライセンス不明。
Commons 以外（NASA/NOAA/USGS 等）の写真は手で {src, credit, license, source_url} を書き、
license に "Public domain (NASA)" のように出所を書く。check はそれを「手動確認済み」として通す。
"""
import argparse, json, re, sys, urllib.parse, urllib.request

API = "https://commons.wikimedia.org/w/api.php"
UA = "worldmystery-article-tools/1.0 (https://worldmysteriesencyclopedia.com)"
ALLOWED = re.compile(r"^(public domain|pd[- ]|cc0|cc[- ]by(?:[- ]sa)?(?:[- ]\d(\.\d)?)?$|cc[- ]by(?:[- ]sa)?[- ]\d)", re.I)
FORBIDDEN = re.compile(r"(\bnc\b|\bnd\b|non[- ]?commercial|no[- ]?deriv|fair[- ]use|all rights reserved|©)", re.I)

def api(params):
    params = {**params, "format": "json", "formatversion": "2"}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)

def strip_html(s):
    return re.sub(r"<[^>]+>", "", s or "").strip()

def license_ok(short):
    s = (short or "").strip()
    if not s or FORBIDDEN.search(s):
        return False
    return bool(ALLOWED.search(s)) or s.lower() in ("public domain", "pd", "cc0")

def filepath_url(title, width=1600):
    name = title.split(":", 1)[1] if title.lower().startswith("file:") else title
    return "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(name.replace(" ", "_")) + f"?width={width}"

def info(titles):
    out, bad = [], []
    for i in range(0, len(titles), 20):
        chunk = titles[i:i + 20]
        r = api({"action": "query", "prop": "imageinfo", "titles": "|".join(chunk),
                 "iiprop": "url|size|extmetadata|mime", "iiextmetadatafilter": "LicenseShortName|Artist|Credit|ImageDescription|DateTimeOriginal|Attribution"})
        for p in r["query"]["pages"]:
            if p.get("missing") or "imageinfo" not in p:
                bad.append((p["title"], "存在しない"))
                continue
            ii = p["imageinfo"][0]; md = ii.get("extmetadata", {})
            lic = strip_html(md.get("LicenseShortName", {}).get("value", ""))
            artist = strip_html(md.get("Artist", {}).get("value", "")) or strip_html(md.get("Credit", {}).get("value", ""))
            desc = strip_html(md.get("ImageDescription", {}).get("value", ""))
            ok = license_ok(lic)
            entry = {"src": filepath_url(p["title"]), "alt": "", "caption": "",
                     "credit": artist[:120], "license": lic, "source_url": ii["descriptionurl"],
                     "w": ii["width"], "h": ii["height"], "_desc": desc[:200], "_title": p["title"], "_ok": ok}
            if not ok:
                bad.append((p["title"], f"ライセンス不可: {lic or '不明'}"))
            out.append(entry)
    return out, bad

def cmd_search(q, n):
    r = api({"action": "query", "generator": "search", "gsrsearch": q, "gsrnamespace": 6, "gsrlimit": n,
             "prop": "imageinfo", "iiprop": "size|extmetadata|mime", "iiextmetadatafilter": "LicenseShortName|Artist"})
    pages = r.get("query", {}).get("pages", [])
    if not pages:
        print("見つかりません"); return
    for p in sorted(pages, key=lambda x: x.get("index", 0)):
        ii = p["imageinfo"][0]; md = ii.get("extmetadata", {})
        lic = strip_html(md.get("LicenseShortName", {}).get("value", ""))
        mark = "OK " if license_ok(lic) else "NG "
        if not ii.get("mime", "").startswith("image/") or ii.get("mime") == "image/svg+xml":
            mark = "-- "
        print(f"{mark}{ii['width']}x{ii['height']:<6} {lic[:18]:<18} {p['title']}")

def cmd_info(titles, out):
    entries, bad = info(titles)
    for t, why in bad:
        print(f"NG  {t}: {why}", file=sys.stderr)
    good = [e for e in entries if e["_ok"]]
    for e in good:
        small = "  ※幅800px未満：3列グリッドか人物カード以外に使わない" if e["w"] < 800 else ""
        print(f"OK  {e['w']}x{e['h']:<6} {e['license'][:16]:<16} {e['_title']}  [{e['credit'][:40]}]{small}")
    payload = [{k: v for k, v in e.items() if not k.startswith("_")} for e in good]
    if out:
        json.dump(payload, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"wrote {out} ({len(payload)} 枚)")
    else:
        print(json.dumps(payload, ensure_ascii=False, indent=1))
    if bad:
        print(f"\n{len(bad)} 枚が使えません。記事に入れないでください。", file=sys.stderr)
        sys.exit(1)

def walk_photos(obj):
    if isinstance(obj, dict):
        if "src" in obj and ("caption" in obj or "alt" in obj):
            yield obj
        for v in obj.values():
            yield from walk_photos(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk_photos(v)

def cmd_check(path):
    art = json.load(open(path, encoding="utf-8"))
    photos = list(walk_photos(art))
    commons, manual, problems = [], [], []
    for p in photos:
        if not p.get("license") or not p.get("credit"):
            problems.append(f"credit/license が空: {p.get('src')}")
        if "commons.wikimedia.org/wiki/Special:FilePath/" in p.get("src", ""):
            name = urllib.parse.unquote(p["src"].split("Special:FilePath/", 1)[1].split("?", 1)[0])
            commons.append(("File:" + name.replace("_", " "), p))
        else:
            manual.append(p)
            if FORBIDDEN.search(p.get("license", "")):
                problems.append(f"不可ライセンス: {p['src']} ({p['license']})")
    if commons:
        entries, bad = info([t for t, _ in commons])
        for t, why in bad:
            problems.append(f"{t}: {why}")
    print(f"写真 {len(photos)} 枚（Commons {len(commons)} / 手動 {len(manual)}）")
    for m in manual:
        print(f"  手動確認済みとして通過: {m['src'][:80]}  {m.get('license','')}")
    for pr in problems:
        print("NG ", pr)
    if problems:
        sys.exit(1)
    print("全写真 OK")

def main():
    ap = argparse.ArgumentParser(); sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search"); s.add_argument("q"); s.add_argument("-n", type=int, default=20)
    i = sub.add_parser("info"); i.add_argument("titles", nargs="+"); i.add_argument("-o")
    c = sub.add_parser("check"); c.add_argument("json")
    a = ap.parse_args()
    if a.cmd == "search": cmd_search(a.q, a.n)
    elif a.cmd == "info": cmd_info([t if t.lower().startswith("file:") else "File:" + t for t in a.titles], a.o)
    else: cmd_check(a.json)

if __name__ == "__main__":
    main()
