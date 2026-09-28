#!/usr/bin/env python3
"""tour100 の写真工程。原稿（article.json）から「どの写真が要るか」を出し、探し、見て選び、権利を元ページで確かめ、
原稿に結びつけ、WordPress に取り込むまで。どの国の記事でも同じ手順で通る。

  python3 tour100/photos.py wants  <記事>                 要る写真の一覧（料理100品・各STOPの風景・表紙）と検索語を photos/wants.json に
  python3 tour100/photos.py search <記事> [タグ…]          候補を集める（Openverse＝Flickr など／Commons／英国なら Geograph）→ photos/candidates.jsonl
  python3 tour100/photos.py sheet  <記事> <タグ> [--page N]  候補を20件ずつ番号付きで1枚に並べる（目で見て選ぶ）→ photos/sheets/<タグ>.jpg
  python3 tour100/photos.py pick   <記事> <タグ> <番号> --subject "写っているもの" --caption "キャプション" [--image]
                                                            選んだ写真を photos/picks.json に。--image＝その店・その品そのものではない（キャプションに「イメージ」と入る）
  python3 tour100/photos.py unpick <記事> <タグ> <番号>          選んだ写真を外す
                                                            手分けするときは pick に --book <名前> を付ける（photos/picks_<名前>.json に書き、あとでまとめて読む）
  python3 tour100/photos.py todo   <記事>                 まだ写真が決まっていないタグ
  python3 tour100/photos.py verify <記事>                 選んだ写真の元ページを開いて、今のライセンス・作者・大きい画像のURLを確かめる → photos/part_auto.json
  python3 tour100/photos.py attach <記事>                 写真台帳（photos/part_*.json）→ article.json（料理の photo/photo2、STOPの opener/scenes、表紙）
  python3 tour100/photos.py import <記事>                 WordPress に取り込み（Bulk Media Importer、5件ずつ完了を確かめる）、url を差し替える

タグ：料理は d001〜d100、風景は s:<photo_key>（例 s:d1-1530）、表紙は hero。
写真台帳の1件：{"id","role":"dish|scene|hero","dish","stop","url","page","creator","license","license_version",
               "subject","caption","image","notes","license_checked"}
使える写真：CC BY／CC BY-SA／CC0／PDM だけ（NC・ND・All Rights Reserved は元ページで弾く）。
"""
import argparse, base64, hashlib, html, io, json, os, re, secrets, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://earthtour.jp/wp-json/earthtour-media/v1/"
OK_LIC = {"by", "by-sa", "cc0", "pdm"}
UA = "tour100-photo/1.0 (+https://github.com/fugufugufugupuff/earthtour)"
BROWSER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
# Flickr のライセンス番号（元ページの "license":N）
FLICKR_LIC = {4: ("by", "2.0"), 5: ("by-sa", "2.0"), 9: ("cc0", "1.0"), 10: ("pdm", "1.0"), 11: ("by", "4.0"), 12: ("by-sa", "4.0")}


# ================================================================ 共通
def P(folder, *x):
    return os.path.join(folder, "photos", *x)


def jload(f, default):
    return json.load(open(f, encoding="utf-8")) if os.path.exists(f) else default


def jsave(f, obj):
    os.makedirs(os.path.dirname(f), exist_ok=True)
    json.dump(obj, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def load(folder):
    return json.load(open(os.path.join(folder, "article.json"), encoding="utf-8"))


def save(folder, art):
    json.dump(art, open(os.path.join(folder, "article.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def get(url, raw=False, ua=UA, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": ua}), timeout=40) as r:
                b = r.read()
                return b if raw else b.decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i < tries - 1:
                time.sleep(5 * (i + 1)); continue
            raise
        except Exception:
            if i < tries - 1:
                time.sleep(3); continue
            raise


def norm(s):
    s = re.sub(r"[（(].*?[）)]|「|」", "", s or "")
    return re.sub(r"[\s・＋+＆&、。]", "", s).lower()


def strip_tags(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", s or ""))).strip()


def stop_key(s):
    return s.get("photo_key") or f"d{s['day']}-{s['time'].replace(':', '')}"


def is_uk(art):
    return art["meta"].get("theme") == "uk"


# ================================================================ 1. 要る写真
def cmd_wants(a):
    art = load(a.folder)
    place = art["meta"].get("place_en") or art["meta"].get("place")
    old = jload(P(a.folder, "wants.json"), {})
    w, no = {}, 0
    for s in art["stops"]:
        for d in s["dishes"]:
            no += 1
            # 料理と写真のタグを原稿に記録する。あとで料理名を直しても、並びを変えても写真が外れない
            tag = d.setdefault("photo_tag", f"d{no:03d}")
            base = re.sub(r"[（(].*?[）)]", "", d.get("local") or d["name"]).strip()
            q = d.get("photo_q") or [base, f"{base} {place}"]
            w[tag] = dict(role="dish", dish=d["name"], stop=s["id"], need=2, queries=q)
        s.setdefault("photo_key", stop_key(s))
        k = stop_key(s)
        pn = re.sub(r"[（(].*?[）)]", "", s.get("place_name") or "").strip()
        area = re.sub(r"[／/].*", "", s.get("area_en") or "").strip()
        q = s.get("photo_q") or [x for x in (f"{pn} {place}" if pn else "", f"{area} {place}" if area else "") if x] or [place]
        w["s:" + k] = dict(role="scene", stop=s["id"], key=k, need=3, queries=q)
    w["hero"] = dict(role="hero", need=2, queries=art["meta"].get("hero_q") or [f"{place} street", f"{place} skyline"])
    for t, v in old.items():  # 手で直した検索語は残す
        if t in w and v.get("queries_edited"):
            w[t]["queries"], w[t]["queries_edited"] = v["queries"], True
    jsave(P(a.folder, "wants.json"), w)
    save(a.folder, art)
    print(f"wants.json：料理 {no} 品・風景 {len(art['stops'])} か所・表紙。検索語は原稿の local／place_name から（直すときは dish/stop に photo_q を書く）")


# ================================================================ 2. 候補を集める
def src_openverse(q, n):
    u = "https://api.openverse.org/v1/images/?" + urllib.parse.urlencode({"q": q, "license_type": "commercial", "page_size": n, "mature": "false"})
    out = []
    for r in json.loads(get(u))["results"]:
        lic = (r.get("license") or "").lower()
        if lic in OK_LIC:
            out.append(dict(src="openverse:" + (r.get("source") or ""), title=r.get("title") or "", license=lic, license_version=r.get("license_version") or "",
                            creator=r.get("creator") or "", url=r["url"], thumb=r.get("thumbnail") or r["url"], page=r["foreign_landing_url"],
                            w=r.get("width"), h=r.get("height")))
    return out


def src_commons(q, n):
    u = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "format": "json", "generator": "search", "gsrsearch": q + " filetype:bitmap", "gsrnamespace": 6, "gsrlimit": n,
        "prop": "imageinfo", "iiprop": "url|extmetadata|size", "iiurlwidth": 400})
    out = []
    for p in (json.loads(get(u)).get("query", {}).get("pages", {}) or {}).values():
        ii = p["imageinfo"][0]; m = ii.get("extmetadata", {})
        key = commons_key(m.get("LicenseShortName", {}).get("value", ""))
        if key in OK_LIC:
            out.append(dict(src="commons", title=p["title"], license=key, license_version="", creator=strip_tags(m.get("Artist", {}).get("value", "")),
                            url=ii["url"].split("?")[0], thumb=(ii.get("thumburl") or "").split("?")[0], page=ii["descriptionurl"].split("?")[0],
                            w=ii.get("width"), h=ii.get("height")))
    return out


def src_geograph(q, n):
    u = "https://api.geograph.org.uk/syndicator.php?" + urllib.parse.urlencode({"q": q, "format": "JSON"})
    out = []
    for r in json.loads(get(u)).get("items", [])[:n]:
        thumb = r.get("thumb") or ""
        out.append(dict(src="geograph", title=r.get("title", ""), license="by-sa", license_version="2.0", creator=r.get("author", ""),
                        url=r.get("image") or thumb.replace("_120x120", ""), thumb=thumb, page=r["link"], w=None, h=None))
    return out


def commons_key(s):
    s = (s or "").lower()
    return ("cc0" if "cc0" in s else "pdm" if "public domain" in s or s == "pd" else "by-sa" if "by-sa" in s
            else None if re.search(r"-nc|-nd", s) else "by" if "cc by" in s or "cc-by" in s else s)


def cmd_search(a):
    art = load(a.folder)
    wants = jload(P(a.folder, "wants.json"), None) or sys.exit("先に wants を実行する")
    cf = P(a.folder, "candidates.jsonl")
    cands = [json.loads(l) for l in open(cf, encoding="utf-8")] if os.path.exists(cf) else []
    have = {(c["tag"], c["url"]) for c in cands}
    done_q = {(c["tag"], c.get("query")) for c in cands}
    srcs = [src_openverse, src_commons] + ([src_geograph] if is_uk(art) else [])
    tags = a.tags or [t for t in wants if not any(c["tag"] == t for c in cands)]
    f = open(cf, "a", encoding="utf-8")
    off = set()  # 制限にかかった出典は、この回はもう使わない（Openverse が Wikimedia も含むので止まらずに進める）
    for t in tags:
        qs = ([a.q] if a.q else wants[t]["queries"])
        # 語が多すぎて1件も出ないことがあるので、短くした検索語も予備に足す
        qs = qs + [" ".join(q.split()[:2]) for q in qs if len(q.split()) > 2]
        added = 0
        for q in qs:
            if (t, q) in done_q and not a.q:
                continue
            if added >= a.n * 2:
                break
            for fn in srcs:
                if fn in off:
                    continue
                try:
                    res = fn(q, a.n)
                except urllib.error.HTTPError as e:
                    if e.code == 429:  # 制限にかかった出典だけ、この回は外す
                        print(f"  [{fn.__name__[4:]}] {q}: 429（この回は使わない）", file=sys.stderr); off.add(fn)
                    else:  # 1つの検索語だけ断られたときは、その語を飛ばす
                        print(f"  [{fn.__name__[4:]}] {q}: HTTP {e.code}（この語は飛ばす）", file=sys.stderr)
                    continue
                except Exception as e:
                    print(f"  [{fn.__name__[4:]}] {q}: {str(e)[:80]}（この回は使わない）", file=sys.stderr); off.add(fn); continue
                for r in res:
                    if (t, r["url"]) in have or re.search(r"\.(pdf|djvu|tiff?|svg|webm|ogv|ogg|stl)$", r["url"], re.I):
                        continue
                    have.add((t, r["url"])); r.update(tag=t, query=q)
                    f.write(json.dumps(r, ensure_ascii=False) + "\n"); added += 1
                time.sleep(0.5)
        f.flush()
        print(f"{t}: +{added}", flush=True)
    f.close()


def cands_of(folder, tag):
    cf = P(folder, "candidates.jsonl")
    return [c for c in (json.loads(l) for l in open(cf, encoding="utf-8")) if c["tag"] == tag] if os.path.exists(cf) else []


# ================================================================ 3. 見て選ぶ
def thumb_bytes(c):
    for u in (c.get("thumb"), c["url"]):
        if not u:
            continue
        wm = "upload.wikimedia.org" in u
        if wm:
            # Wikimedia は決まった幅（330px など）のサムネイルしか返さず、説明のある User-Agent を求める
            m = re.match(r"https://upload\.wikimedia\.org/wikipedia/commons/(?:thumb/)?(\w/\w\w)/([^/?]+)", u)
            if m:
                u = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{m.group(1)}/{m.group(2)}/330px-{m.group(2)}"
        try:
            b = get(u, raw=True, ua=UA if wm else BROWSER, tries=3)
            if wm:
                time.sleep(0.5)
            return b
        except Exception:
            continue
    return None


def contact_sheet(items, out, cell=300, cols=4):
    """items: [(ラベル, 画像バイト or None)] を番号付きで1枚に。"""
    from PIL import Image, ImageDraw
    rows = (len(items) + cols - 1) // cols or 1
    sh = Image.new("RGB", (cols * cell, rows * (cell + 22)), "white"); d = ImageDraw.Draw(sh)
    for k, (label, b) in enumerate(items):
        x, y = (k % cols) * cell, (k // cols) * (cell + 22)
        try:
            im = Image.open(io.BytesIO(b)).convert("RGB"); im.thumbnail((cell - 6, cell - 6)); sh.paste(im, (x + 3, y + 3))
        except Exception:
            d.text((x + 10, y + 100), "no image", fill="red")
        d.text((x + 4, y + cell + 2), label[:48], fill="black")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sh.save(out, quality=80)


def cmd_sheet(a):
    cs = cands_of(a.folder, a.tag)
    off = 20 * (a.page if a.page is not None else (1 if a.more else 0))
    sel = list(enumerate(cs))[off:off + 20]
    tdir = P(a.folder, "thumbs"); os.makedirs(tdir, exist_ok=True)
    items = []
    for i, c in sel:
        fn = os.path.join(tdir, hashlib.md5(c["url"].encode()).hexdigest() + ".jpg")
        if not os.path.exists(fn):
            b = thumb_bytes(c)
            if b:
                open(fn, "wb").write(b)
        items.append((f"#{i} {c['license']} {c['w']}x{c['h']}", open(fn, "rb").read() if os.path.exists(fn) else None))
    out = P(a.folder, "sheets", a.tag.replace(":", "_") + (f"_p{off // 20}" if off else "") + ".jpg")
    contact_sheet(items, out)
    for i, c in sel:
        print(f"#{i} [{c['license']}] {c['title'][:60]} | {strip_tags(c['creator'])[:24]} | {c['src']}")
    print("sheet:", out)


def all_picks(folder):
    """photos/picks*.json をまとめて読む（何人かで手分けして選べるよう、pick は --book ごとに別のファイルに書く）。"""
    out = {}
    d = os.path.join(folder, "photos")
    for fn in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if re.match(r"picks.*\.json$", fn):
            for t, lst in json.load(open(os.path.join(d, fn), encoding="utf-8")).items():
                have = {p["url"] for p in out.get(t, [])}
                out.setdefault(t, []).extend(p for p in lst if p["url"] not in have)
    return out


def cmd_pick(a):
    cs = cands_of(a.folder, a.tag)
    if a.i >= len(cs):
        sys.exit(f"{a.tag} の候補は {len(cs)} 件")
    cap = a.caption
    if a.image and "イメージ" not in cap and "別の" not in cap:
        cap += "（イメージ）"
    pf = P(a.folder, f"picks_{a.book}.json" if a.book else "picks.json")
    picks = jload(pf, {})
    lst = [p for p in picks.get(a.tag, []) if p["url"] != cs[a.i]["url"]]
    lst.append(dict(i=a.i, url=cs[a.i]["url"], page=cs[a.i]["page"], subject=a.subject, caption=cap, image=bool(a.image)))
    picks[a.tag] = lst
    jsave(pf, picks)
    print(f"{a.tag}：{len(all_picks(a.folder).get(a.tag, []))} 枚")


def cmd_sheet_grid(a):
    """複数タグを目視する。候補番号を変えず、選択はpickで別途記録する。"""
    import concurrent.futures, hashlib
    selected = []
    for tag in a.tags:
        candidates = list(enumerate(cands_of(a.folder, tag)))
        if a.source:
            candidates = [(i, c) for i, c in candidates if c['src'] == a.source]
        selected.extend((tag, i, c) for i, c in candidates[a.offset:a.offset + a.limit])
    cache = P(a.folder, "thumbs"); os.makedirs(cache, exist_ok=True)
    def fetch(item):
        tag, i, c = item
        fn = os.path.join(cache, hashlib.sha256(c["url"].encode()).hexdigest() + ".jpg")
        if not os.path.exists(fn):
            b = thumb_bytes(c)
            if b:
                open(fn, "wb").write(b)
        return (f"{tag} #{i} {c['license']}", open(fn, "rb").read() if os.path.exists(fn) else None)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        items = list(pool.map(fetch, selected))
    name = a.name or "grid"
    out = P(a.folder, "sheets", name + ".jpg")
    contact_sheet(items, out, cell=280, cols=a.limit)
    jsave(P(a.folder, "sheets", name + ".json"),
          [dict(tag=t, i=i, title=c['title'], page=c['page'], creator=c['creator']) for t, i, c in selected])
    print(out, flush=True)


def cmd_unpick(a):
    """選んだ写真を外す（全部の picks*.json から）。"""
    cs = cands_of(a.folder, a.tag)
    url = cs[a.i]["url"]
    d = os.path.join(a.folder, "photos")
    for fn in os.listdir(d):
        if re.match(r"picks.*\.json$", fn):
            pk = json.load(open(os.path.join(d, fn), encoding="utf-8"))
            if a.tag in pk:
                pk[a.tag] = [p for p in pk[a.tag] if p["url"] != url]
                jsave(os.path.join(d, fn), pk)
    print(f"{a.tag} #{a.i} を外した")


def cmd_todo(a):
    wants, picks = jload(P(a.folder, "wants.json"), {}), all_picks(a.folder)
    short = {t: (len(picks.get(t, [])), w["need"]) for t, w in wants.items() if len(picks.get(t, [])) < (1 if w["role"] == "dish" else w["need"])}
    for t, (n, need) in short.items():
        print(f"{t:14s} {n}/{need}  {wants[t].get('dish') or wants[t].get('key') or ''}  候補 {len(cands_of(a.folder, t))} 件")
    print(f"— 足りないタグ {len(short)} 件（料理は1枚あれば可、2枚目があれば風景に回る）")


# ================================================================ 4. 権利を元ページで確かめる
def verify_flickr(page):
    t = get(page, ua=BROWSER)
    m = re.search(r'"license":\s*"https?://creativecommons\.org/(licenses|publicdomain)/([a-z-]+)/([0-9.]+)', t)
    if m:
        key = {"zero": "cc0", "mark": "pdm"}.get(m.group(2), m.group(2))
        ver = m.group(3)
    else:
        n = re.search(r'"license":(\d+)', t)
        key, ver = FLICKR_LIC.get(int(n.group(1)), (None, "")) if n else (None, "")
    if key not in OK_LIC:
        return dict(ok=False, why=f"Flickr のライセンスが {key or '不明／All Rights Reserved'}")
    sizes = {k: (u.replace("\\/", "/"), int(w)) for k, u, w in re.findall(r'"(o|k|h|l|c)":\{"displayUrl":"([^"]+)","width":(\d+)', t)}
    url = next(("https:" + sizes[k][0] for k in ("h", "k", "l", "c", "o") if k in sizes), None)
    owner = re.search(r'"ownerName":"([^"]+)"', t) or re.search(r'"realname":"([^"]+)"', t) or re.search(r'"username":"([^"]+)"', t)
    taken = re.search(r'"dateTaken":"(\d{4})', t)
    return dict(ok=bool(url), why="" if url else "画像URLが取れない", license=key, license_version=ver, url=url,
                creator=html.unescape(owner.group(1)) if owner else "", year=taken.group(1) if taken else "")


def verify_commons(page):
    title = urllib.parse.unquote(page.split("/wiki/", 1)[1]) if "/wiki/" in page else None
    q = {"titles": title} if title else {"pageids": page.split("curid=")[1]}
    q.update(action="query", format="json", prop="imageinfo", iiprop="url|extmetadata|size", iiurlwidth=1600)
    pg = list(json.loads(get("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(q)))["query"]["pages"].values())[0]
    ii = pg["imageinfo"][0]; m = ii["extmetadata"]
    g = lambda k: strip_tags(m.get(k, {}).get("value", ""))
    key = commons_key(g("LicenseShortName"))
    if key not in OK_LIC:
        return dict(ok=False, why=f"Commons のライセンスが {g('LicenseShortName')}")
    ver = (re.search(r"(\d\.\d)", g("LicenseShortName")) or [None, ""])[1]
    url = (ii.get("thumburl") or "").split("?")[0] if (ii.get("width") or 0) > 1600 else ii["url"]
    return dict(ok=True, license=key, license_version=ver, url=url.split("?")[0], creator=g("Artist")[:120] or "作者不明",
                year=(re.search(r"(\d{4})", g("DateTimeOriginal")) or [None, ""])[1])


def verify_one(c):
    pg = c["page"]
    if "flickr.com" in pg:
        return verify_flickr(pg)
    if "commons.wikimedia.org" in pg:
        return verify_commons(pg)
    if "geograph" in pg:
        return dict(ok=True, license="by-sa", license_version="2.0", url=c["url"], creator=c.get("creator", ""), year="")
    return dict(ok=False, why=f"確かめ方を知らない出典：{pg}")


def cmd_verify(a):
    wants, picks = jload(P(a.folder, "wants.json"), {}), all_picks(a.folder)
    vf = P(a.folder, "verified.json"); V = jload(vf, {})
    led, bad = [], []
    for tag, lst in picks.items():
        w = wants.get(tag, {})
        for k, pk in enumerate(lst):
            if pk["page"] not in V or not V[pk["page"]].get("ok"):
                try:
                    V[pk["page"]] = verify_one(dict(pk, creator=""))
                except Exception as e:
                    V[pk["page"]] = dict(ok=False, why=str(e)[:120])
                jsave(vf, V); time.sleep(1)
            v = V[pk["page"]]
            if not v.get("ok"):
                bad.append(f"{tag} #{pk['i']}：{v['why']}"); continue
            pid = re.sub(r"[^a-z0-9]", "", tag.replace("s:", "s")) + "abcdefgh"[k]
            led.append(dict(id=pid, tag=tag, role=w.get("role", "scene"), dish=w.get("dish"), stop=w.get("key"), url=v["url"], page=pk["page"],
                            creator=v["creator"] or "作者不明", license=v["license"], license_version=v["license_version"], subject=pk["subject"],
                            caption=pk["caption"], image=pk.get("image", False), kind="photo", season="na",
                            notes=f"撮影 {v.get('year') or '不明'}；ライセンスは元ページで確認（{time.strftime('%Y-%m-%d')}）", license_checked=True))
    jsave(P(a.folder, "part_auto.json"), led)
    print(f"part_auto.json：{len(led)} 枚")
    for b in bad:
        print("使えない：", b)
    if bad:
        print("→ 使えない写真は pick し直す（同じタグで別の番号）")


# ================================================================ 5. 原稿に結びつける
def ledger(folder):
    # 取り込みに失敗した写真（import_state.json の failed）は台帳から外す
    failed = set(jload(os.path.join(folder, "photos", "import_state.json"), {}).get("failed", []))
    out = []
    for f in sorted(os.listdir(os.path.join(folder, "photos"))):
        if re.match(r"part_.*\.json$", f):
            for p in json.load(open(os.path.join(folder, "photos", f), encoding="utf-8")):
                n = p.get("notes") or ""
                if p.get("url") and "不要" not in n and "見つからず" not in n and p.get("license") in OK_LIC and p["id"] not in failed:
                    out.append(p)
    return out


def attach(folder):
    """台帳の写真を原稿に結びつける。すでに結ばれていて台帳にある写真はそのまま残し（手で入れ替えた並びを壊さない）、
    空いている枠と、台帳から外れた写真の枠だけを埋める。"""
    art, led = load(folder), ledger(folder)
    prev = art.get("photos", {})
    photos = art["photos"] = {}  # 台帳にある写真だけにする（外した写真を残さない）
    for p in led:
        old = prev.get(p["id"], {})
        photos[p["id"]] = {k: p.get(k) for k in ("url", "page", "creator", "license", "license_version", "subject", "caption", "image", "kind", "season")}
        photos[p["id"]]["creator"] = re.sub("<[^>]+>", "", photos[p["id"]]["creator"] or "作者不明")
        if old.get("orig_url") == p["url"]:  # 取り込み済みの写真は WordPress のURLを保つ
            photos[p["id"]].update(url=old["url"], orig_url=old["orig_url"])
        for k, v in old.items():  # 原稿で書き足した項目（license_note など）は残す
            photos[p["id"]].setdefault(k, v)
        for k in ("caption", "subject"):  # 原稿で直したキャプションは残す
            if old.get(k) and old.get("orig_url", old.get("url")) in (p["url"], photos[p["id"]]["url"]):
                photos[p["id"]][k] = old[k]
    ok = lambda x: x in photos
    used = {x for s in art["stops"] for x in [s.get("opener")] + list(s.get("scenes") or []) +
            [y for d in s["dishes"] for y in (d.get("photo"), d.get("photo2"))] if x and ok(x)}
    bydish, bytag = {}, {}
    for p in led:
        if p.get("role") == "dish":
            bydish.setdefault(norm(p.get("dish")), []).append(p["id"])
            if p.get("tag"):
                bytag.setdefault(p["tag"], []).append(p["id"])
    missing = []
    for s in art["stops"]:
        for d in s["dishes"]:
            have = [x for x in (d.get("photo"), d.get("photo2")) if x and ok(x)]
            if len(have) < 2:
                k = norm(d.get("aka") or d["name"])
                # タグで結ぶ（wants が記録した photo_tag）。タグのない古い台帳だけ料理名で結ぶ
                c = bytag.get(d.get("photo_tag")) or bydish.get(k, [])
                add = [x for x in c if x not in used][:2 - len(have)]
                used.update(add); have += add
            d["photo"], d["photo2"] = (have + [None, None])[:2]
            if not have:
                missing.append(d["name"])
        # 風景写真は台帳の "stop" で結ぶ。時刻を後で変えても外れないよう、最初の結びつけで photo_key を記録しておく
        key = s.setdefault("photo_key", stop_key(s))
        cur = [x for x in [s.get("opener")] + list(s.get("scenes") or []) if x and ok(x)]
        new = [p["id"] for p in led if p.get("role") == "scene" and p.get("stop") == key and p["id"] not in used]
        used.update(new)
        sc = (cur + new)[:5]
        s["opener"] = sc[0] if sc else None
        s["scenes"] = sc[1:]
    cover = [x for x in (art.get("cover", {}).get("photos") or []) if ok(x)]
    if not cover:
        hero = [p["id"] for p in led if p.get("role") == "hero"]
        firsts = [s["dishes"][0]["photo"] for s in art["stops"] if s["dishes"] and s["dishes"][0]["photo"]]
        dishes = [d for s in art["stops"] for d in s["dishes"]]
        tag_no = art.get("cover", {}).get("tag_dish")
        if isinstance(tag_no, int) and 1 <= tag_no <= len(dishes):
            featured = dishes[tag_no - 1].get("photo")
            if featured:
                firsts = [featured] + [pid for pid in firsts if pid != featured]
        cover = (hero + firsts)[:3]
    art.setdefault("cover", {})["photos"] = cover
    save(folder, art)
    print(f"写真 {len(photos)} 枚／料理で写真なし {len(missing)} 品：{missing}")


# ================================================================ 6. WordPress に取り込む
def auth():
    pw = os.environ.get("EARTHTOUR_WP_APP_PASSWORD")
    if not pw and os.path.exists("/root/.config/earthtour/wp_app_password"):
        pw = open("/root/.config/earthtour/wp_app_password").read().strip()
    if not pw:
        sys.exit("環境変数 EARTHTOUR_WP_APP_PASSWORD がない")
    return {"Authorization": "Basic " + base64.b64encode(f"earthtour:{pw}".encode()).decode(), "User-Agent": "tour100/1.0"}


def api(path, data=None, tries=5):
    """Importer の REST。取得（GET）はサーバーの一時的なエラー（502・503・504）なら待ってやり直す。"""
    for i in range(tries):
        try:
            return _api(path, data)
        except urllib.error.HTTPError as e:
            if data is None and e.code in (502, 503, 504) and i < tries - 1:
                time.sleep(20 * (i + 1)); continue
            raise
        except (urllib.error.URLError, TimeoutError, ValueError):  # ValueError＝空の応答（サーバーが混んでいるとき）
            if data is None and i < tries - 1:
                time.sleep(20 * (i + 1)); continue
            raise


def _api(path, data=None):
    h = auth()
    body = None
    if data is not None:
        body = json.dumps(data).encode(); h["Content-Type"] = "application/json"
    return json.load(urllib.request.urlopen(urllib.request.Request(API + path, data=body, headers=h, method="POST" if body else "GET"), timeout=180))


def do_import(folder):
    art = load(folder)
    # A source photograph may be used for both a scene and the cover.
    # Reuse its confirmed attachment rather than submit another item ID for
    # the same URL (the importer can deduplicate that request without an item).
    imported = {p.get("orig_url"): p["url"] for p in art.get("photos", {}).values()
                if p.get("orig_url") and "earthtour.jp/wp-content" in p["url"]}
    reused = 0
    for p in art.get("photos", {}).values():
        if p["url"] in imported:
            p["orig_url"], p["url"] = p["url"], imported[p["url"]]
            reused += 1
    if reused:
        save(folder, art)
        print(f"同じ元写真の取り込み済みURLを再利用：{reused} 件")
    slug = art["meta"].get("slug", "tour").replace("-100-dishes-tour", "")
    h = api("health")
    if not (h.get("ok") and h.get("version")):
        sys.exit(f"Importer の health が異常：{h}")
    used = {x for s in art["stops"] for x in [s.get("opener")] + list(s.get("scenes") or []) + [y for d in s["dishes"] for y in (d.get("photo"), d.get("photo2"))] if x}
    used |= set(art.get("cover", {}).get("photos") or [])
    todo = [(pid, p) for pid, p in art["photos"].items() if pid in used and "earthtour.jp/wp-content" not in p["url"]]
    if not todo:
        print("取り込み済み"); return
    state_f = os.path.join(folder, "photos", "import_state.json")
    st = json.load(open(state_f)) if os.path.exists(state_f) else {"job": f"et{slug[:6]}{secrets.token_hex(9)}", "done": {}}
    print(f"取り込み {len(todo)} 枚（job {st['job']}）")
    for k in range(0, len(todo), 5):
        ch = [(pid, p) for pid, p in todo[k:k + 5] if pid not in st["done"]]
        if not ch:
            continue
        items = [dict(url=p["url"], title=f"{slug}100-{pid} " + (p.get("caption") or p.get("subject") or "")[:60], alt=p.get("subject") or "",
                      license=f"{ {'by':'CC BY','by-sa':'CC BY-SA','cc0':'CC0','pdm':'Public Domain Mark'}[p['license']] } {p.get('license_version') or ''}".strip(),
                      credit=p.get("creator") or "作者不明", source_page=p["page"],
                      filename=f"{slug}100-{pid}-" + re.sub(r"[^A-Za-z0-9._-]", "_", os.path.basename(p["url"].split("?")[0]))[-70:],
                      job_id=st["job"], item_id=f"{st['job']}-{pid}") for pid, p in ch]
        try:
            r = api("import", {"items": items, "job_id": st["job"]})
        except Exception as e:
            print("送信エラー", e); time.sleep(20); continue
        for _ in range(40):
            time.sleep(6)
            b = api("batch/" + r["batch_id"])
            if b.get("status") == "complete":
                break
        job = api("job/" + st["job"])
        for it in job["items"]:
            pid = it["item_id"].split("-", 1)[1] if "-" in it["item_id"] else None
            if it["status"] in ("success", "duplicate") and it.get("wp_url") and pid:
                st["done"][pid] = it["wp_url"]
        json.dump(st, open(state_f, "w"), ensure_ascii=False, indent=0)
        print(f"{min(k + 5, len(todo))}/{len(todo)}  取り込み済み {len(st['done'])}", flush=True)
    for pid, u in st["done"].items():
        if pid in art["photos"]:
            art["photos"][pid].setdefault("orig_url", art["photos"][pid]["url"])
            art["photos"][pid]["url"] = u
    save(folder, art)
    left = [pid for pid, p in todo if pid not in st["done"]]
    st["failed"] = sorted(set(st.get("failed", [])) | set(left))
    json.dump(st, open(state_f, "w"), ensure_ascii=False, indent=0)
    if left:
        attach(folder)  # 取り込めなかった写真を原稿から外し、空いた枠を台帳の別の写真で埋める
    print(f"完了。取り込めなかった写真 {len(left)} 枚" + (f"：{left}（原稿から外した。足りなければ pick し直して verify → attach → import）" if left else ""))


def cmd_archive(a):
    """Archive selected, verified source originals; never count thumbnails as originals."""
    from PIL import Image
    records = jload(P(a.folder, "originals.json"), {})
    V = jload(P(a.folder, "verified.json"), {})
    for tag, picked in all_picks(a.folder).items():
        for pk in picked:
            page = pk['page']
            if not V.get(page, {}).get('ok'):
                continue
            if records.get(page, {}).get('sha256'):
                continue
            r = dict(tag=tag, page=page, checked_at=time.strftime('%Y-%m-%d'),
                     visual_subject=pk['subject'], caption=pk['caption'], modifications='none',
                     license=V[page]['license'], license_version=V[page]['license_version'],
                     creator=V[page]['creator'], location_scope='not established; not evidence of the featured restaurant')
            try:
                if 'commons.wikimedia.org' in page:
                    q = {'titles': urllib.parse.unquote(page.split('/wiki/',1)[1])} if '/wiki/' in page else {'pageids':page.split('curid=')[1]}
                    q.update(action='query',format='json',prop='imageinfo',iiprop='url|extmetadata|size')
                    pg=list(json.loads(get('https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode(q)))['query']['pages'].values())[0]
                    ii=pg['imageinfo'][0]; r['original_url']=ii['url']; md=ii.get('extmetadata',{})
                    r['source_metadata']={k:strip_tags(v.get('value','')) for k,v in md.items() if k in ['Artist','ImageDescription','DateTimeOriginal','LicenseShortName','LicenseUrl','Attribution','Credit']}
                elif 'flickr.com' in page:
                    t=get(page,ua=BROWSER)
                    sizes={k:u.replace('\\/','/') for k,u in re.findall(r'"(o|k|h|l|c)":\{"displayUrl":"([^"]+)"',t)}
                    if not sizes.get('o'):
                        raise ValueError('Flickr original size unavailable; preserve candidate without claiming an original')
                    r['original_url']=('https:' if sizes['o'].startswith('//') else '')+sizes['o']
                    desc=re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]*)"',t)
                    r['source_metadata']={'description':html.unescape(desc.group(1)) if desc else '', 'year':V[page].get('year','')}
                else:
                    raise ValueError('Original resolver unavailable')
                raw=get(r['original_url'],raw=True)
                im=Image.open(io.BytesIO(raw)); im.verify()
                im=Image.open(io.BytesIO(raw)); r['width'],r['height']=im.size
                ext={"JPEG":'.jpg',"PNG":'.png',"WEBP":'.webp'}.get(im.format,'.img')
                digest=hashlib.sha256(raw).hexdigest()
                dest=P(a.folder,'originals',re.sub(r'[^A-Za-z0-9_-]','_',tag)+'-'+digest[:12]+ext)
                os.makedirs(os.path.dirname(dest),exist_ok=True)
                with open(dest,'wb') as f:f.write(raw)
                r.update(local_file=os.path.relpath(dest,a.folder).replace('\\','/'),sha256=digest,bytes=len(raw),status='original_saved')
            except Exception as e:
                r.update(status='archive_failed',error=str(e)[:200])
            records[page]=r; jsave(P(a.folder,'originals.json'),records)
            print(tag+': '+r['status'],flush=True)
    print('Original archive records: '+str(len(records)))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    for c in ("wants", "todo", "verify", "attach", "import", "archive"):
        sp.add_parser(c).add_argument("folder")
    s = sp.add_parser("search"); s.add_argument("folder"); s.add_argument("tags", nargs="*"); s.add_argument("--q", help="このタグだけ別の検索語で足す")
    s.add_argument("-n", type=int, default=15)
    t = sp.add_parser("sheet"); t.add_argument("folder"); t.add_argument("tag"); t.add_argument("--more", action="store_true")
    g = sp.add_parser("sheet-grid", help="複数タグを番号つきの目視用シートにまとめる")
    g.add_argument("folder"); g.add_argument("tags", nargs="+")
    g.add_argument("--limit", type=int, choices=range(1, 7), default=4)
    g.add_argument("--offset", type=int, default=0); g.add_argument("--name")
    g.add_argument("--source", help="候補表示を出典で絞る。候補番号と採用基準は変えない")
    t.add_argument("--page", type=int, help="何ページ目の20件を見るか（0から。--more は 1 と同じ）")
    k = sp.add_parser("pick"); k.add_argument("folder"); k.add_argument("tag"); k.add_argument("i", type=int)
    k.add_argument("--subject", required=True); k.add_argument("--caption", required=True); k.add_argument("--image", action="store_true")
    k.add_argument("--book", help="手分けするときの自分の名前（picks_<名前>.json に書く）")
    u = sp.add_parser("unpick"); u.add_argument("folder"); u.add_argument("tag"); u.add_argument("i", type=int)
    a = ap.parse_args()
    dict(wants=cmd_wants, search=cmd_search, sheet=cmd_sheet, archive=cmd_archive, **{"sheet-grid": cmd_sheet_grid}, pick=cmd_pick, unpick=cmd_unpick, todo=cmd_todo, verify=cmd_verify,
         attach=lambda a: attach(a.folder), **{"import": lambda a: do_import(a.folder)})[a.cmd](a)


if __name__ == "__main__":
    main()
