#!/usr/bin/env python3
"""tour100 — 「行った気になる100品ツアー」記事の装置（設計は DESIGN.md、書式は README.md）

  python3 tour100/build.py themes                        使えるテーマ（国・地域）の一覧
  python3 tour100/build.py new    <記事> --place ホーチミン --theme southeast-asia --currency ₫ --rate 0.0061 --decimals 0
  python3 tour100/build.py check  <記事>                  原稿の検査（100品・写真・ライセンス・価格）
  python3 tour100/build.py media  <記事>                  WordPress に取り込んだ写真の寸法と srcset を取ってくる
  python3 tour100/build.py build  <記事>                  out/preview.html（確認用）と out/post.html（投稿用）を書き出す
  python3 tour100/build.py qa     <記事> [--live]         画面の自動検査（360/390/768/1280px）とスクリーンショット。--live は公開ページ
  python3 tour100/build.py review <記事>                  見直しチェックリスト（review/checklist.md）と写真の見直し用シート
  python3 tour100/build.py fix    <記事>                  見直しで出た直し（review/fixes*.json）を原稿に入れる
  python3 tour100/build.py css                            共通CSSをサイトの WGE Design System（bundle t100）へ送る
  python3 tour100/build.py post   <記事>                  WordPress に下書きとして保存（見直しが全部 [x] でないと止まる。公開はしない）

WordPress の認証：環境変数 EARTHTOUR_WP_APP_PASSWORD（ユーザー earthtour）。値をファイルに書かない。
"""
import argparse, base64, hashlib, json, os, re, subprocess, sys, time, urllib.parse, urllib.request
if __package__:
    from .selection import selection_errors, selection_key
    from .editorial import MODEL_NOTE, output_errors, source_errors
else:
    from selection import selection_errors, selection_key
    from editorial import MODEL_NOTE, output_errors, source_errors

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = "https://earthtour.jp"
BUNDLE = "t100"
FONTS = ("https://fonts.googleapis.com/css2?family=Dela+Gothic+One&family=DotGothic16&family=Fraunces:ital,wght@0,600;1,500"
         "&family=Klee+One:wght@600&family=Zen+Kaku+Gothic+New:wght@400;500;700&display=swap")
LIC = {"by": "CC BY", "by-sa": "CC BY-SA", "cc0": "CC0", "pdm": "パブリックドメイン"}
GENRE_COLORS = {"朝ごはん": "#d6452a", "パブ": "#7a4a1d", "屋台": "#c93c78", "市場": "#2f8a4c", "菓子": "#c93c78",
                "飲み物": "#1d4e89", "チェーン店": "#5f6472", "スーパー": "#5f6472", "ゲテモノ": "#6f52c4",
                "移民の味": "#0f7c8c", "老舗": "#8a6d1d", "ごちそう": "#b0122b", "軽食": "#b8700f"}
REQ_META = ["title", "slug", "place", "place_short", "kicker", "lede", "plan_sub", "month", "as_of", "theme", "currency", "rate_text"]
REQ_STOP = ["id", "day", "time", "slot", "area", "label", "title", "subtitle", "pm", "lat", "lng", "place_name", "hours", "access", "body", "dishes"]
REQ_DISH = ["name", "local", "gloss", "catch", "first", "tex", "how", "shop", "price", "photo"]

try:
    import jinja2
    from markupsafe import Markup, escape
except ImportError:
    sys.exit("jinja2 が必要です： pip install jinja2 budoux")
try:
    import budoux
    _BX = budoux.load_default_japanese_parser()
except Exception:
    _BX = None


# ================================================================ WordPress
def _auth():
    pw = os.environ.get("EARTHTOUR_WP_APP_PASSWORD")
    if not pw and os.path.exists("/root/.config/earthtour/wp_app_password"):
        pw = open("/root/.config/earthtour/wp_app_password").read().strip()
    if not pw:
        sys.exit("環境変数 EARTHTOUR_WP_APP_PASSWORD がない")
    return {"Authorization": "Basic " + base64.b64encode(f"earthtour:{pw}".encode()).decode(), "User-Agent": "tour100/1.0"}


def wp(path, data=None, method=None):
    h = _auth()
    body = None
    if data is not None:
        body = json.dumps(data).encode(); h["Content-Type"] = "application/json"
    req = urllib.request.Request(SITE + "/wp-json/" + path, data=body, headers=h, method=method or ("POST" if body else "GET"))
    return json.load(urllib.request.urlopen(req, timeout=120))


# ================================================================ 原稿
def load(folder):
    art = json.load(open(os.path.join(folder, "article.json"), encoding="utf-8"))
    media = os.path.join(folder, "media.json")
    art["_media"] = json.load(open(media, encoding="utf-8")) if os.path.exists(media) else {}
    return art


def check(art):
    errs, warns = [], []
    errs.extend(selection_errors(art))
    errs.extend(source_errors(art))
    meta, photos = art.get("meta", {}), art.get("photos", {})
    if str(meta.get('postmark_label', '')).strip().upper() == 'VISITED':
        errs.append('meta.postmark_label: 訪問記録ではないためVISITEDは使えません')
    for k in REQ_META:
        if not meta.get(k):
            errs.append(f"meta.{k} がない")
    stops = art.get("stops", [])
    dishes = [d for s in stops for d in s.get("dishes", [])]
    if len(dishes) != 100:
        errs.append(f"料理が {len(dishes)} 品（ちょうど100品にする）")
    names = [d.get("name") for d in dishes]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        errs.append(f"同じ料理が2回ある：{dup}")
    days = {d["day"] for d in art.get("days", [])}
    for s in stops:
        sid = s.get("id")
        for k in REQ_STOP:
            if meta.get('thematic') and k in ('subtitle', 'hours', 'access'):
                continue  # Optional for food themes without timed or mapped travel claims.
            if s.get(k) in (None, "", []):
                errs.append(f"{sid}：{k} がない")
        if s.get("day") not in days:
            errs.append(f"{sid}：day {s.get('day')} が days にない")
        for pid in [s.get("opener")] + list(s.get("scenes", [])):
            if pid and pid not in photos:
                errs.append(f"{sid}：写真 {pid} が photos にない")
        for d in s.get("dishes", []):
            for k in REQ_DISH:
                if not d.get(k):
                    errs.append(f"{sid} {d.get('name')}：{k} がない")
            for k in ("photo", "photo2"):
                if d.get(k) and d[k] not in photos:
                    errs.append(f"{d.get('name')}：写真 {d[k]} が photos にない")
            pr = d.get("price") or {}
            if not pr.get("seal"):
                errs.append(f"{d.get('name')}：price.seal がない")
            if pr.get("value") is None and not pr.get("included"):
                warns.append(f"{d.get('name')}：price.value がない（会計に入らない。セット込みなら included: true）")
    used = {x for s in stops for x in [s.get("opener")] + list(s.get("scenes", [])) + [y for d in s.get("dishes", []) for y in (d.get("photo"), d.get("photo2"))] if x}
    for pid, p in photos.items():
        if pid not in used and pid not in (art.get("cover", {}).get("photos") or []):
            continue
        for k in ["url", "page", "license", "subject", "creator"]:
            if not p.get(k):
                errs.append(f"写真 {pid}：{k} がない")
        if p.get("license") not in LIC:
            errs.append(f"写真 {pid}：ライセンス {p.get('license')} は使えない（CC BY／CC BY-SA／CC0／PDM のみ）")
        if not p.get("url", "").startswith(SITE + "/wp-content/"):
            warns.append(f"写真 {pid}：WordPress に取り込まれていない（外部URLのまま）")
    # 見出しの中の長いカタカナ語は途中で折り返せず、スマホ幅（1行およそ9文字）で1〜2文字だけ次の行に落ちる
    for s in art["stops"]:
        for w in re.findall(r"[ァ-ヶー]{10,}", s.get("title", "")):
            warns.append(f"{s.get('id')} の見出し：「{w}」は長くてスマホで1行に入らない（中黒で区切るか、短い言い方に）")
    return errs, warns


# ================================================================ 組み立て
def bx(t):
    """文節ごとに <wbr> を入れる（語の途中で改行しない）。"""
    t = t or ""
    if not _BX:
        return escape(t)
    return Markup("｜<wbr>".join("<wbr>".join(str(escape(x)) for x in _BX.parse(seg)) for seg in t.split("｜")))


def safe_mark(t):
    parts = re.split(r"(</?mark>)", t or "")
    return Markup("".join(p if p in ("<mark>", "</mark>") else str(escape(p)) for p in parts))


def load_theme(art):
    themes = json.load(open(os.path.join(HERE, "themes.json"), encoding="utf-8"))
    name = art["meta"]["theme"]
    if name not in themes:
        sys.exit(f"theme '{name}' がない。使えるもの：{', '.join(themes)}")
    t = json.loads(json.dumps(themes[name]))
    ov = art.get("theme_override") or {}
    t["colors"].update(ov.get("colors", {})); t["deco"].update(ov.get("deco", {}))
    return t


def render(art, wp_mode=False):
    meta, cur = art["meta"], art["meta"]["currency"]
    rate, sym, dec = cur["rate"], cur["symbol"], cur.get("decimals", 2)
    media = art.get("_media", {})
    photos = {}
    for pid, p in art["photos"].items():
        m = media.get(p["url"], {})
        photos[pid] = dict(p, id=pid, src=p["url"], srcset=m.get("srcset"), w=m.get("w"), h=m.get("h"),
                           alt=p.get("alt") or p.get("subject") or p.get("caption") or "",
                           license_label=(LIC[p["license"]] + " " + re.sub(r"(?i)^cc[\s-]*(by(-sa)?|0)?\s*", "", p.get("license_version") or "")).strip())
    theme = load_theme(art)

    def money(v):
        if v is None:
            return "—"
        s = f"{v:,.{dec}f}" if dec else f"{round(v):,}"
        return f"{sym}{s}" if cur.get("position", "prefix") == "prefix" else f"{s}{sym}"

    def money_round(v):  # 合計のような大きい額は端数を出さない
        s = f"{round(v):,}"
        return f"{sym}{s}" if cur.get("position", "prefix") == "prefix" else f"{s}{sym}"

    def yen(v):
        return int(round(v * rate, -1))

    bots = theme["deco"].get("botanicals") or []
    stops, all_dishes, pins, no = [], [], [], 0
    for k, s0 in enumerate(art["stops"]):
        s = dict(s0, no=k + 1, anchor=f"stop-{s0['id']}", r=s0.get("r", 400), info=s0.get("info", []), tips=(s0.get("tips") or [])[:2],
                 opener=photos.get(s0.get("opener")), scenes=[photos[x] for x in s0.get("scenes", []) if x in photos],
                 botanical=bots[k % len(bots)] if bots else None, last=(k == len(art["stops"]) - 1))
        ds = []
        for d in s0["dishes"]:
            no += 1
            pr = d["price"]
            small = pr.get("small")
            if small is None and pr.get("value") is not None:
                small = f"≈{yen(pr['value']):,}円"
            if pr.get("unit"):
                small = f"{small}・{pr['unit']}" if small else pr["unit"]
            x = dict(d, no=no, seal=pr["seal"], small=small or "", value=None if pr.get("included") else pr.get("value"),
                     photo=photos.get(d.get("photo")))
            if d.get("photo2") in photos:
                s["scenes"].insert(0, photos[d["photo2"]])
            ds.append(x)
        s["scenes"] = s["scenes"][:6]
        s["dishes"] = ds
        s["total"] = sum(x["value"] for x in ds if x["value"] is not None)
        s["total_yen"] = yen(s["total"])
        stops.append(s); all_dishes += ds
        pins.append(dict(lat=s["lat"], lng=s["lng"], label=f"{k + 1:02d}", name=s["title"], day=s["day"], time=s["time"], anchor=s["anchor"]))
    days = []
    for d0 in art["days"]:
        sts = [s for s in stops if s["day"] == d0["day"]]
        for i, s in enumerate(sts):
            s["i"] = i
        strip = [x["photo"] for s in sts for x in s["dishes"][:1] if x["photo"]][:3]
        days.append(dict(d0, stops=sts, strip=strip, count=sum(len(s["dishes"]) for s in sts), total=sum(s["total"] for s in sts)))
    total = sum(d["total"] for d in days)
    stats = dict(days=len(days), stops=len(stops), dishes=no, total=total, total_yen=int(round(total * rate, -2)),
                 total_yen_man=f"{total * rate / 10000:.1f}".rstrip("0").rstrip("."))
    cv = art.get("cover", {})
    cover_photos = [photos[x] for x in cv.get("photos", []) if x in photos][:3] or [x["photo"] for x in all_dishes if x["photo"]][:3]
    tagd = next((x for x in all_dishes if x["no"] == cv.get("tag_dish")), all_dishes[0])
    used = {}
    for p in cover_photos + [x["photo"] for x in all_dishes if x["photo"]] + [p for s in stops for p in ([s["opener"]] if s["opener"] else []) + s["scenes"]] \
            + [p for d in days for p in d["strip"]]:
        used.setdefault(p["id"], p)
    env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(HERE, "templates")), autoescape=True, trim_blocks=True, lstrip_blocks=True)
    env.filters.update(bx=bx, safe_mark=safe_mark, money=money)
    body = env.get_template("article.html.j2").render(
        meta=meta, editorial_note=MODEL_NOTE, deco=theme["deco"], theme_style=";".join(f"--{k}:{v}" for k, v in theme["colors"].items()),
        stats=stats, days=days, all_dishes=all_dishes, cover_photos=cover_photos, cover_tag=dict(seal=tagd["seal"], small=tagd["small"]),
        basics=art.get("basics", []), fee=[[k, v if v != "auto" else f"約{money_round(total)}（約{stats['total_yen_man']}万円）"] for k, v in art.get("fee", [])], links=art.get("links", []), end_notes=art.get("end_notes", []),
        sources=art.get("sources", []), credits=list(used.values()), genre_color=lambda g: GENRE_COLORS.get(g, "#1d4e89"),
        pins_json=Markup(json.dumps(pins, ensure_ascii=False).replace("</", "<\\/")),
        map_js=Markup(open(os.path.join(HERE, "assets", "tour100.js"), encoding="utf-8").read()))
    css = open(os.path.join(HERE, "assets", "tour100.css"), encoding="utf-8").read()
    fonts = f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="{FONTS}" rel="stylesheet">'
    info = dict(stats, photos=len(used), theme=meta["theme"])
    if wp_mode:
        # CSS とフォントはサイトの WGE Design System（bundle t100）から配信。本文には目印だけ。
        return f"<!-- wp:html -->\n<!--wge-css:{BUNDLE}-->\n{body}\n<!-- /wp:html -->", info
    page = (f'<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{escape(meta["title"])}</title>{fonts}<style>body{{margin:0;background:#fbf6ec}}\n{css}</style></head><body>{body}</body></html>')
    return page, info


# ================================================================ コマンド
def cmd_new(a):
    if os.path.exists(os.path.join(a.folder, "article.json")):
        sys.exit(f"{a.folder}/article.json はもうある")
    os.makedirs(a.folder, exist_ok=True)
    art = json.load(open(os.path.join(HERE, "examples", "article.template.json"), encoding="utf-8"))
    art["meta"].update(place=a.place, place_short=a.place, place_en=a.place_en or "", theme=a.theme, title=f"{a.place}100品グルメツアー｜",
                       slug=a.slug or "", currency=dict(symbol=a.currency, rate=a.rate, decimals=a.decimals),
                       rate_text=f"1{a.currency} ≈ {a.rate}円")
    json.dump(art, open(os.path.join(a.folder, "article.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"作成：{a.folder}/article.json")


def report(art):
    errs, warns = check(art)
    for w in warns[:25]:
        print("注意：", w)
    if len(warns) > 25:
        print(f"注意：ほか {len(warns) - 25} 件")
    for e_ in errs:
        print("エラー：", e_)
    print(f"— エラー {len(errs)} 件／注意 {len(warns)} 件")
    return errs


def cmd_media(a):
    art = load(a.folder)
    urls = sorted({p["url"] for p in art["photos"].values() if p["url"].startswith(SITE + "/wp-content/")})
    cache = art["_media"]
    todo = [u for u in urls if u not in cache]
    print(f"WordPress の写真 {len(urls)} 枚（未取得 {len(todo)} 枚）")
    for u in todo:
        slug = os.path.splitext(os.path.basename(urllib.parse.urlsplit(u).path))[0]
        slug = re.sub(r"-scaled$", "", slug)
        res = wp("wp/v2/media?" + urllib.parse.urlencode({"search": slug, "per_page": 5, "_fields": "id,source_url,media_details"}))
        hit = next((r for r in res if r["source_url"] == u), None)
        if not hit:
            continue
        md = hit["media_details"]; sizes = md.get("sizes", {})
        cand = [(v["width"], v["source_url"]) for k, v in sizes.items() if k in ("medium", "medium_large", "large", "1536x1536")] + [(md.get("width"), u)]
        cand = sorted({(w, s) for w, s in cand if w})
        cache[u] = dict(id=hit["id"], w=md.get("width"), h=md.get("height"), srcset=", ".join(f"{s} {w}w" for w, s in cand))
    json.dump(cache, open(os.path.join(a.folder, "media.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(f"media.json：{len(cache)} 枚")


def cmd_build(a):
    art = load(a.folder)
    if report(art) and not a.force:
        sys.exit("エラーを直してから build する（--force で強行）")
    out = os.path.join(a.folder, "out"); os.makedirs(out, exist_ok=True)
    page, info = render(load(a.folder))
    open(os.path.join(out, "preview.html"), "w", encoding="utf-8").write(page)
    post, _ = render(load(a.folder), wp_mode=True)
    open(os.path.join(out, "post.html"), "w", encoding="utf-8").write(post)
    print(json.dumps(info, ensure_ascii=False))
    print(f"書き出し：{out}/preview.html ／ {out}/post.html（{len(post):,} 文字）")


UA_BROWSER = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def _fetch(u, tries=3):
    p = urllib.parse.urlsplit(html_unescape(u))
    u = urllib.parse.urlunsplit((p.scheme, p.netloc, urllib.parse.quote(urllib.parse.unquote(p.path)), p.query, ""))
    for i in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA_BROWSER}), timeout=60).read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(8 * (i + 1)); continue
            raise
        except Exception:
            if i < tries - 1:
                time.sleep(2); continue
            raise


def localize(page, adir):
    """ページが読む画像・CSS・フォントを adir に落とし、ネットにつながなくても同じ見た目で開ける1枚にする。
    検査をどの環境でも同じ条件で行うため（ブラウザの証明書やネットワークに左右されない）。"""
    os.makedirs(adir, exist_ok=True)
    rel = os.path.basename(adir)
    page = re.sub(r"""(\s(?:src|href))='([^']*)'""", r'\1="\2"', page)  # WordPress は属性を ' で書くことがある
    page = re.sub(r'\s(?:srcset|sizes)="[^"]*"', "", page)  # 検査は src の1枚で行う

    def keep(u, ext):
        fn = hashlib.md5(u.encode()).hexdigest() + ext
        fp = os.path.join(adir, fn)
        if not os.path.exists(fp) or os.path.getsize(fp) == 0:
            m = re.match(r"https://upload\.wikimedia\.org/wikipedia/commons/(\w/\w\w)/([^/?]+)$", u)
            cands = ([f"https://upload.wikimedia.org/wikipedia/commons/thumb/{m.group(1)}/{m.group(2)}/960px-{m.group(2)}"] if m else []) + [u]
            for c in cands:
                try:
                    data = _fetch(c)
                    if not data:
                        raise ValueError("empty asset response")
                    with open(fp, "wb") as handle:
                        handle.write(data)
                    break
                except Exception:
                    continue
            else:
                return None
        return fn

    fails = 0
    for u in sorted(set(re.findall(r'href="(https://fonts\.googleapis\.com/css2[^"]+)"', page))):
        try:
            css = _fetch(u).decode()
        except Exception:
            fails += 1; continue
        for f in set(re.findall(r"url\((https://fonts\.gstatic\.com/[^)]+)\)", css)):
            fn = keep(f, ".woff2")
            if fn:
                css = css.replace(f, fn)
        fn = hashlib.md5(u.encode()).hexdigest() + ".css"
        open(os.path.join(adir, fn), "w").write(css)
        page = page.replace(f'"{u}"', f'"{rel}/{fn}"')
    # Source-credit anchors can end in .jpg while pointing at an HTML file page.
    # Localize only rendered media and stylesheet resources, keeping citations live.
    resource_urls = re.findall(r'<(?:img|source)\b[^>]*\bsrc="(https://[^"]+)"', page, re.I)
    resource_urls += re.findall(r'<link\b[^>]*\bhref="(https://[^"]+)"', page, re.I)
    for u in sorted(set(resource_urls)):
        ext = re.search(r"\.(jpe?g|png|webp|gif|css)(?:\?|$)", u.split("#")[0], re.I)
        if not ext or "fonts.googleapis" in u:
            continue
        fn = keep(u, "." + ext.group(1).lower())
        if fn:
            page = page.replace(f'"{u}"', f'"{rel}/{fn}"')
        else:
            fails += 1
    return page, fails


def html_unescape(s):
    return s.replace("&#038;", "&").replace("&amp;", "&")


def cmd_qa(a):
    art = load(a.folder)
    out = os.path.join(a.folder, "out", "qa-live" if a.live else "qa")
    os.makedirs(out, exist_ok=True)
    if a.live:
        url = f"{SITE}/{art['meta']['slug']}/"
        page = _fetch(url + f"?qa={int(time.time())}").decode("utf-8")
        print("公開ページ：", url)
    else:
        page = open(os.path.join(a.folder, "out", "preview.html"), encoding="utf-8").read()
    page, fails = localize(page, os.path.join(out, "assets"))
    open(os.path.join(out, "page.html"), "w", encoding="utf-8").write(page)
    if fails:
        print(f"取ってこられなかった画像・CSS：{fails} 件（公開ページなら画像切れの疑い）")
    r = subprocess.run(["node", os.path.join(HERE, "qa.js"), os.path.join(out, "page.html"), out])
    sys.exit(r.returncode or (1 if fails else 0))


def cmd_css(a):
    css = open(os.path.join(HERE, "assets", "tour100.css"), encoding="utf-8").read()
    key = f"wge_css_{BUNDLE}"
    cur = wp("wp/v2/settings")
    if key not in cur:
        sys.exit(f"サイトに bundle '{BUNDLE}' がまだ無い。Code Snippets の「WGE Design System」の wge_ds_bundles() に '{BUNDLE}' を足す")
    wp("wp/v2/settings", {key: css})
    print(f"{key} を更新（{len(css):,} 文字）")


# ================================================================ 見直し（人の目で確かめる工程）
BOX = re.compile(r"^- \[( |x)\] (.*?)\s*<!--k:([^>]+)-->$", re.M)


def review_items(art):
    """確かめることの一覧。(区分, キー, 文)。承認は確認した原稿だけに対応させる。"""
    it = [("旅の基本", "basics", "入国（ビザ・電子渡航認証・パスポート）、航空便と空港、空港から市内、市内の交通、通貨とレート、安全情報が、いま調べて正しい"),
          ("旅の基本", "dates", f"旅の日付（{art['meta'].get('month')}）と曜日、祝日・行事、時差や夏時間の切り替えが旅程と合っている"),
          ("旅の基本", "fee", "旅費の合計（航空券・宿・交通・食費）が本文と巻末で合っている")]
    for s in art["stops"]:
        it.append(("食事の場所", s["id"], f"{s['id']} DAY{s['day']} {s['time']} {s.get('place_name')}：店・エリア、曜日、営業時間・行き方・移動時間を資料と照合。探し先の例と確認済みの提供店を区別し、未確認の営業・取扱いを断定していない"))
    no = 0
    for s in art["stops"]:
        for d in s["dishes"]:
            no += 1
            it.append(("料理", f"d{no:03d}", f"{no:03d} {d['name']}：説明・味・食感が料理と合う、値段がだいたい合う（{d['price'].get('seal')}）"))
    for k in range(0, no, 25):
        it.append(("写真", f"sheet{k // 25 + 1}", f"料理写真 {k + 1:03d}〜{min(k + 25, no):03d}（out/review/dishes_{k // 25 + 1}.jpg）：写っているものが料理名と合う。店や品が違う写真はキャプションに「イメージ」か「別の店」"))
    it.append(("写真", "scenes", "章扉と風景の写真（out/review/scenes.jpg）：キャプションが写っているものと合う、季節が大きく外れていない"))
    it.append(("文章", "text", "誤字・表記ゆれ・時刻と移動のつじつま・同じ言い回しの繰り返しを読み直した"))
    it.append(("編集方法", "research-method", "導入・本文・キャプションに、編集部が訪問・注文・実食したという架空の記録がない。旅程は公開資料によるモデルコースとして書く。伝説や諸説は区別して残し、未確定だけを理由に削除しない"))
    it.append(("料理の選定", selection_key(art), "selectionの全出典を開き、料理ごとの土地との関係・独立した一品である理由・80品以上の地元/国内料理・city10品以上を確認。単なる提供店、一般的な飲食物、付け合わせ分割、写真都合の水増しがない（原稿変更で再確認）"))
    revision = selection_key(art)
    # A replacement at the same ordinal must not inherit the previous [x].
    return [(g, k if k == revision else f"{k}-{revision}", t) for g, k, t in it]


def review_state(folder):
    f = os.path.join(folder, "review", "checklist.md")
    if not os.path.exists(f):
        return None, {}
    return f, {k: x == "x" for x, _, k in BOX.findall(open(f, encoding="utf-8").read())}


def cmd_review(a):
    """review/checklist.md を作る（前の ✓ は残す）。写真の見直し用に、料理写真を番号付きで並べた画像も作る。"""
    art = load(a.folder)
    f, done = review_state(a.folder)
    f = f or os.path.join(a.folder, "review", "checklist.md")
    os.makedirs(os.path.dirname(f), exist_ok=True)
    lines, sec = [f"# 見直しチェックリスト：{art['meta']['title']}", "",
                  "確かめたら `[ ]` を `[x]` にする。直したことは review/ の facts.md・text.md に書く。すべて [x] になるまで `build.py post` は止まる。", ""], None
    items = review_items(art)
    for g, k, t in items:
        if g != sec:
            lines += ["", f"## {g}", ""]; sec = g
        lines.append(f"- [{'x' if done.get(k) else ' '}] {t} <!--k:{k}-->")
    open(f, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    left = sum(1 for _, k, _ in items if not done.get(k))
    print(f"{f}：{len(items)} 項目、のこり {left}")
    # 写真の見直し用シート（番号だけ入れる。料理名は下の一覧で照らし合わせる）
    sys.path.insert(0, HERE)
    import photos as ph
    rdir = os.path.join(a.folder, "out", "review"); os.makedirs(rdir, exist_ok=True)
    cache = os.path.join(rdir, "thumbs"); os.makedirs(cache, exist_ok=True)

    def img(p):
        fn = os.path.join(cache, hashlib.md5(p["url"].encode()).hexdigest() + ".jpg")
        if not os.path.exists(fn):
            small = (art["_media"].get(p["url"], {}).get("srcset") or "").split(" ")[0]  # WordPress の小さいサイズで足りる
            b = ph.thumb_bytes(dict(thumb=small or None, url=p["url"]))
            if b:
                open(fn, "wb").write(b)
        return open(fn, "rb").read() if os.path.exists(fn) else None

    dishes = [d for s in art["stops"] for d in s["dishes"]]
    listing = []
    for k in range(0, len(dishes), 25):
        items_ = []
        for i, d in enumerate(dishes[k:k + 25], k + 1):
            p = art["photos"].get(d.get("photo") or "")
            items_.append((f"{i:03d}", img(p) if p else None))
            listing.append(f"{i:03d} {d['name']}｜{(p or {}).get('caption', '写真なし')}｜{(p or {}).get('subject', '')}")
        ph.contact_sheet(items_, os.path.join(rdir, f"dishes_{k // 25 + 1}.jpg"), cell=240, cols=5)
    sc = [(s["id"], art["photos"][s["opener"]]) for s in art["stops"] if s.get("opener") in art["photos"]]
    ph.contact_sheet([(sid, img(p)) for sid, p in sc], os.path.join(rdir, "scenes.jpg"), cell=240, cols=5)
    listing += [f"{sid}｜{p.get('caption')}｜{p.get('subject')}" for sid, p in sc]
    open(os.path.join(rdir, "photos.txt"), "w", encoding="utf-8").write("\n".join(listing) + "\n")
    print(f"写真の見直し用：{rdir}/dishes_*.jpg・scenes.jpg と photos.txt（番号・料理名・キャプション・写っているもの）")


def cmd_fix(a):
    """review/fixes*.json（見直しで出た直し）を原稿に入れる。1件＝{"path": "stops[3].dishes[1].catch", "old": 今の文の一部, "new": 直した文, "why": 理由}。
    old が今の値に見つからないものは入れずに報告する（原稿がもう変わっているため）。"""
    f = os.path.join(a.folder, "article.json")
    art = json.load(open(f, encoding="utf-8"))
    rdir = os.path.join(a.folder, "review")
    done_f = os.path.join(rdir, "fixes_applied.json")
    done = json.load(open(done_f, encoding="utf-8")) if os.path.exists(done_f) else []
    seen = {(d["path"], d["old"], d["new"]) for d in done}
    ok = miss = 0
    for fn in sorted(x for x in os.listdir(rdir) if re.match(r"fixes.*\.json$", x) and x != "fixes_applied.json"):
        for fx in json.load(open(os.path.join(rdir, fn), encoding="utf-8")):
            key = (fx["path"], fx["old"], fx["new"])
            if key in seen:
                continue
            parent, last = art, None
            toks = re.findall(r"[^.\[\]]+|\[\d+\]", fx["path"])
            try:
                for t in toks[:-1]:
                    parent = parent[int(t[1:-1])] if t.startswith("[") else parent[t]
                last = toks[-1]
                last = int(last[1:-1]) if last.startswith("[") else last
                cur = parent[last]
            except (KeyError, IndexError, TypeError):
                print(f"見つからない場所：{fn} {fx['path']}"); miss += 1; continue
            if isinstance(cur, str) and fx["old"] in cur:
                parent[last] = cur.replace(fx["old"], fx["new"], 1)
            elif not isinstance(cur, str) and json.dumps(cur, ensure_ascii=False) == fx["old"]:
                parent[last] = json.loads(fx["new"])
            else:
                print(f"今の文と合わない：{fn} {fx['path']}：{fx['old'][:30]}"); miss += 1; continue
            done.append(dict(fx, file=fn)); seen.add(key); ok += 1
    json.dump(art, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(done, open(done_f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"直した {ok} 件／入れられなかった {miss} 件（入れた記録：{done_f}）")


def cmd_post(a):
    art = load(a.folder)
    selection_failures = selection_errors(art)
    if selection_failures:
        sys.exit("料理の選定が未合格（--forceでも投稿不可）：\n" + "\n".join(selection_failures))
    _, editorial_done = review_state(a.folder)
    if not editorial_done.get(selection_key(art)):
        sys.exit("現在の原稿の料理選定レビューが未完了。reviewで出典を読み直す（--forceでも投稿不可）")
    if report(art):
        sys.exit("エラーを直してから post する（投稿時は--forceで検査を省略できません）")
    f, done = review_state(a.folder)
    left = [t for _, k, t in review_items(art) if not done.get(k)]
    if left:
        sys.exit(f"見直しが終わっていない（{len(left)} 項目）：`build.py review` で review/checklist.md を作り、確かめて [x] にする\n  例：{left[0]}")
    post, info = render(load(a.folder), wp_mode=True)
    representation_failures = output_errors(post)
    if representation_failures:
        sys.exit("生成結果の編集基準が未合格：\n" + "\n".join(representation_failures))
    m = art["meta"]
    data = dict(title=m["title"], slug=m["slug"], content=post, excerpt=m.get("excerpt", ""), categories=m.get("categories", []), status="draft")
    cover = (art.get("cover", {}).get("photos") or [None])[0]
    fid = art["_media"].get(art["photos"].get(cover, {}).get("url", ""), {}).get("id")
    if fid:
        data["featured_media"] = fid  # アイキャッチ＝表紙の1枚目
    idf = os.path.join(a.folder, "post_id.txt")
    pid = open(idf).read().strip() if os.path.exists(idf) else None
    if pid:
        st = wp(f"wp/v2/posts/{pid}?context=edit&_fields=status")["status"]
        data["status"] = st  # 公開済みの記事の状態は変えない
        r = wp(f"wp/v2/posts/{pid}", data)
    else:
        r = wp("wp/v2/posts", data)
        open(idf, "w").write(str(r["id"]))
    print(f"投稿 {r['id']}（{r['status']}）：{r['link']}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    n = sp.add_parser("new"); n.add_argument("folder"); n.add_argument("--place", required=True); n.add_argument("--place-en", help="写真検索に使う英語の地名"); n.add_argument("--theme", required=True)
    n.add_argument("--currency", required=True); n.add_argument("--rate", type=float, required=True); n.add_argument("--decimals", type=int, default=2); n.add_argument("--slug")
    for c in ("check", "media", "build", "qa", "review", "fix", "post"):
        p = sp.add_parser(c); p.add_argument("folder"); p.add_argument("--force", action="store_true")
        if c == "qa":
            p.add_argument("--live", action="store_true", help="公開ページを検査する")
    sp.add_parser("css"); sp.add_parser("themes")
    a = ap.parse_args()
    if a.cmd == "themes":
        for k, v in json.load(open(os.path.join(HERE, "themes.json"), encoding="utf-8")).items():
            print(f"{k:16s} {v['label']}")
    elif a.cmd == "check":
        sys.exit(1 if report(load(a.folder)) else 0)
    else:
        dict(new=cmd_new, media=cmd_media, build=cmd_build, qa=cmd_qa, review=cmd_review, fix=cmd_fix, css=cmd_css, post=cmd_post)[a.cmd](a)


if __name__ == "__main__":
    main()
