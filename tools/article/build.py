#!/usr/bin/env python3
"""article.json → WordPress(SWELL) 用 HTML フラグメントを生成する。

使い方:
  python3 tools/article/build.py path/to/article.json [-o out.html]

article.json の形は README.md を参照。デザインは design.tokens / design.fonts /
design.backgrounds / design.css_extra で毎回自由に変える。ここにあるのは下回りだけ。
"""
import argparse, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CATALOG = os.path.join(HERE, "..", "wm-assets", "catalog.json")

# ---------- 既定トークン（記事ごとに design.tokens で上書きする） ----------
DEFAULT_TOKENS = {
    "paper": "#f4ecdb", "paper-2": "#efe6d1", "paper-3": "#e9dfc6",
    "ink": "#211d18", "ink-2": "#39332b", "muted": "#6b6357", "line": "rgba(40,31,20,.16)",
    "accent": "#b2292d", "accent-deep": "#7c1a1e", "cool": "#0a6d6f", "cool-deep": "#0a5152", "cool-soft": "#dcece7",
    "shadow": "0 24px 60px rgba(38,25,10,.20)", "shadow-sm": "0 10px 26px rgba(38,25,10,.14)",
    "wrap": "min(1360px, 92vw)", "text": "1000px", "wide": "min(1520px, 94vw)", "bleed": "min(1760px, 96vw)",
}
DEFAULT_FONTS = {
    "head": '"Shippori Mincho","Noto Serif JP",serif',
    "sub": '"Noto Serif JP",serif',
    "body": '"Noto Sans JP","Hiragino Kaku Gothic ProN","Yu Gothic",sans-serif',
    "import": "https://fonts.googleapis.com/css2?family=Shippori+Mincho:wght@600;800%26family=Noto+Serif+JP:wght@600;700%26family=Noto+Sans+JP:wght@400;450;700;900%26display=swap",
}

def esc(s):
    return html.escape(str(s), quote=True)

def load_catalog():
    try:
        return {a["file"]: a for a in json.load(open(CATALOG, encoding="utf-8"))}
    except FileNotFoundError:
        return {}

class Builder:
    def __init__(self, art):
        self.a = art
        self.slug = re.sub(r"[^a-z0-9-]", "-", art["slug"].lower())
        self.cls = f"wp-{self.slug}-fragment"
        self.tokens = {**DEFAULT_TOKENS, **art.get("design", {}).get("tokens", {})}
        self.fonts = {**DEFAULT_FONTS, **art.get("design", {}).get("fonts", {})}
        self.catalog = load_catalog()
        self.photos = []      # 使った写真（クレジット一覧用）
        self.chapters = []    # 目次用
        self.warnings = []

    # ---------- 写真 ----------
    def img(self, ph, cls=""):
        """写真1枚 → <figure>。ph: {src, alt, caption, credit, license, source_url, w, h}"""
        if not ph.get("src"):
            raise SystemExit("写真に src がありません: %r" % ph)
        self.photos.append(ph)
        src = ph["src"]
        if "wikimedia.org" in src and "?width=" not in src and "Special:FilePath" in src:
            src += "?width=1600"
        credit = " / ".join(x for x in [ph.get("credit"), ph.get("license")] if x)
        cap = esc(ph.get("caption", ""))
        if credit:
            cap += f' <span class="credit">（{esc(credit)}）</span>'
        wh = ""
        if ph.get("w") and ph.get("h"):
            wh = f' width="{int(ph["w"])}" height="{int(ph["h"])}"'
        open_tag = f'<figure class="{cls.strip()}">' if cls.strip() else "<figure>"
        return open_tag + \
               f'<img src="{esc(src)}" alt="{esc(ph.get("alt") or ph.get("caption", ""))}" loading="lazy" decoding="async"{wh}>' + \
               f"<figcaption>{cap}</figcaption></figure>"

    def asset_url(self, name):
        """カタログの素材名 → URL。無ければ警告して名前をそのまま返す。"""
        a = self.catalog.get(name)
        if not a:
            self.warnings.append(f"カタログにない素材: {name}")
            return name
        return a["url"]

    # ---------- ブロック ----------
    def block(self, b):
        t = b["type"]
        if t == "p":
            return f"<p>{self.inline(b['text'])}</p>"
        if t == "h3":
            return f"<h3>{esc(b['text'])}</h3>"
        if t == "ul" or t == "ol":
            return f"<{t}>" + "".join(f"<li>{self.inline(x)}</li>" for x in b["items"]) + f"</{t}>"
        if t == "figure":
            size = b.get("size", "wide")  # text | wide | full
            cls = {"text": "text-figure", "wide": "wide-figure", "full": "wide-figure full"}[size]
            return self.img(b["photo"], cls)
        if t == "photo-pair":
            return '<div class="photo-pair">' + "".join(self.img(p, "portrait" if b.get("portrait") else "") for p in b["photos"]) + "</div>"
        if t == "photo-grid":
            return '<div class="photo-grid">' + "".join(self.img(p) for p in b["photos"]) + "</div>"
        if t == "readbreak":
            return f'<div class="read-break">{self.inline(b["text"])}</div>'
        if t == "note":
            return f'<div class="note">{self.inline(b["text"])}</div>'
        if t == "theory":
            return f'<div class="theory">{self.inline(b["text"])}</div>'
        if t == "quote":
            who = f'<cite>{esc(b["who"])}</cite>' if b.get("who") else ""
            return f'<blockquote class="pull">{self.inline(b["text"])}{who}</blockquote>'
        if t == "timeline":
            rows = "".join(f'<div class="route-item"><div class="route-time">{esc(i["time"])}</div><div>{self.inline(i["text"])}</div></div>' for i in b["items"])
            return f'<div class="route">{rows}</div>'
        if t == "compare":  # 説くらべ
            head = "".join(f"<th>{esc(c)}</th>" for c in b["columns"])
            body = "".join("<tr>" + "".join(f"<td>{self.inline(c)}</td>" for c in r) + "</tr>" for r in b["rows"])
            cap = f"<caption>{esc(b['caption'])}</caption>" if b.get("caption") else ""
            return f'<div class="table-wrap"><table class="compare">{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
        if t == "table":
            head = "".join(f"<th>{esc(c)}</th>" for c in b["columns"])
            body = "".join("<tr>" + "".join(f"<td>{self.inline(c)}</td>" for c in r) + "</tr>" for r in b["rows"])
            return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'
        if t == "profile":  # 人物カード
            ph = self.img(b["photo"], "profile-photo") if b.get("photo") else ""
            return f'<div class="profile">{ph}<div class="profile-body"><div class="profile-name">{esc(b["name"])}</div><div class="profile-role">{esc(b.get("role",""))}</div><p>{self.inline(b["text"])}</p></div></div>'
        if t == "stamp":  # カタログの小物を飾りとして置く
            url = self.asset_url(b["asset"])
            a = self.catalog.get(b["asset"], {})
            w = min(int(b.get("width", a.get("w", 200))), int(a.get("w", 10**6)))
            return f'<div class="stamp {esc(b.get("pos","right"))}"><img src="{esc(url)}" alt="" width="{w}" loading="lazy"></div>'
        if t == "band":  # 背景付きの帯（章の間の全幅ブレイク）
            bg = self.asset_url(b["background"]) if b.get("background") else ""
            style_cls = f"band-{len(self.chapters)}-{abs(hash(bg)) % 10000}"
            self.band_css.append(f'.{self.cls} .{style_cls}{{background-image:url("{bg}")}}')
            return f'<div class="band {style_cls}"><div class="band-inner">{self.inline(b["text"])}</div></div>'
        if t == "html":
            return b["html"]
        raise SystemExit(f"未知のブロック type: {t}")

    def inline(self, s):
        """**強調** → .hot、__冷静__ → .cool、[ラベル] → .mini-label。それ以外はエスケープ。"""
        s = esc(s)
        s = re.sub(r"\*\*(.+?)\*\*", r'<span class="hot">\1</span>', s)
        s = re.sub(r"__(.+?)__", r'<span class="cool">\1</span>', s)
        s = re.sub(r"\[\[(.+?)\]\]", r'<span class="mini-label">\1</span>', s)
        s = re.sub(r"\{(https?://[^\s}|]+)\|([^}]+)\}", r'<a href="\1" target="_blank" rel="noopener">\2</a>', s)
        return s.replace("\n", "<br>")

    # ---------- 全体 ----------
    def build(self):
        a, c = self.a, self.cls
        self.band_css = []
        d = a.get("design", {})
        hero = a.get("hero", {})
        chips = "".join(f"<div>{self.inline(x)}</div>" for x in hero.get("chips", []))
        hero_photo = self.img(hero["photo"], "hero-photo") if hero.get("photo") else ""
        eyebrow = f'<p class="eyebrow">{esc(hero["eyebrow"])}</p>' if hero.get("eyebrow") else ""
        head_tag = "h1" if a.get("own_h1", False) else "p"  # SWELL がタイトルを出すので既定は h1 を使わない
        hero_html = f'''<header class="hero">
  <div class="hero-text">{eyebrow}<{head_tag} class="title">{esc(a["title"])}</{head_tag}>
    <p class="hero-lead">{self.inline(a["lead"])}</p>
    <div class="case-line">{chips}</div></div>
  {hero_photo}
</header>'''

        secs = []
        for i, s in enumerate(a["sections"], 1):
            sid = f"sec-{i}"
            self.chapters.append((sid, s["title"]))
            body = "".join(self.block(b) for b in s["blocks"])
            sub = f'<p class="chapter-sub">{esc(s["subtitle"])}</p>' if s.get("subtitle") else ""
            secs.append(f'<section id="{sid}"><h2>{esc(s["title"])}</h2>{sub}{body}</section>')

        toc = ""
        if a.get("toc", True):
            toc = '<nav class="toc"><p class="toc-title">目次</p><ol>' + "".join(f'<li><a href="#{sid}">{esc(t)}</a></li>' for sid, t in self.chapters) + "</ol></nav>"

        lead_sec = ""
        if a.get("summary"):
            lead_sec = '<div class="lead-section">' + "".join(f"<p>{self.inline(p)}</p>" for p in a["summary"]) + "</div>"

        sources = ""
        if a.get("sources"):
            items = []
            for s in a["sources"]:
                t = esc(s["title"])
                if s.get("url"):
                    t = f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{t}</a>'
                note = f" — {esc(s['note'])}" if s.get("note") else ""
                items.append(f"<li>{t}{note}</li>")
            sources = '<div class="sources"><p class="sources-title">出典・参考資料</p><ol>' + "".join(items) + "</ol></div>"

        credits = ""
        if self.photos:
            seen, items = set(), []
            for p in self.photos:
                key = p["src"]
                if key in seen: continue
                seen.add(key)
                who = " / ".join(x for x in [p.get("credit"), p.get("license")] if x) or "出典不明（要確認）"
                link = f' <a href="{esc(p["source_url"])}" target="_blank" rel="noopener">出典</a>' if p.get("source_url") else ""
                items.append(f"<li>{esc(p.get('caption') or p.get('alt',''))[:60]} — {esc(who)}{link}</li>")
            credits = '<div class="sources credits"><p class="sources-title">画像クレジット</p><ol>' + "".join(items) + "</ol></div>"

        css = self.css() + "\n".join(self.band_css) + "\n" + d.get("css_extra", "")
        out = f'''<style>
{css}
</style>
<div class="{c}">
<article class="article">
{hero_html}
{toc}
{lead_sec}
<main>
{"".join(secs)}
</main>
{sources}
{credits}
</article>
</div>'''
        return out

    def css(self):
        c, t, f = self.cls, self.tokens, self.fonts
        d = self.a.get("design", {})
        bgs = d.get("backgrounds", {})
        vars_ = "".join(f"--{k}:{v};" for k, v in t.items())
        hero_bg = ""
        if bgs.get("hero"):
            hero_bg = f'.{c} .hero{{background-image:linear-gradient(rgba(0,0,0,.5),rgba(0,0,0,.7)),url("{self.asset_url(bgs["hero"])}");background-size:cover;background-position:center;color:#fff}}' \
                      f'.{c} .hero .title,.{c} .hero .hero-lead,.{c} .hero .eyebrow{{color:#fff}}.{c} .hero .hero-lead{{border-left-color:#fff}}' \
                      f'.{c} .hero .case-line>div{{background:rgba(255,255,255,.14);color:#fff;border-color:rgba(255,255,255,.35)}}' \
                      f'.{c} .hero figcaption,.{c} .hero figcaption .credit{{color:rgba(255,255,255,.85)}}'
        page_bg = f'.{c}{{background:var(--paper-2)}}'
        if bgs.get("page"):
            page_bg = f'.{c}{{background:var(--paper-2) url("{self.asset_url(bgs["page"])}") center top/cover fixed}}'
        texture = ""
        if bgs.get("texture"):
            texture = f'.{c} .article::before{{content:"";position:absolute;inset:0;background:url("{self.asset_url(bgs["texture"])}") repeat;mix-blend-mode:multiply;pointer-events:none;z-index:0}}.{c} .article>*{{position:relative;z-index:1}}'
        imp = f'@import url("{f["import"]}");' if f.get("import") else ""
        return f'''{imp}
.{c}{{{vars_}}}
{page_bg}
.{c} *{{box-sizing:border-box}}
.alignfull > .wp-block-group__inner-container{{max-width:100% !important}}
.{c} .article{{max-width:none !important;width:100% !important;margin:0;position:relative;color:var(--ink);font-family:{f["body"]};
  background:radial-gradient(1200px 640px at 15% -5%, rgba(178,41,45,.06), transparent 60%),radial-gradient(1100px 620px at 88% 4%, rgba(10,109,111,.06), transparent 60%),linear-gradient(180deg,var(--paper-2) 0%, var(--paper) 40%, var(--paper-3) 100%);
  padding-bottom:clamp(60px,8vw,110px);overflow:hidden}}
{texture}
.{c} .article :where(h1,h2,h3,h4){{border:0!important;background:none!important;padding:0!important;box-shadow:none!important;text-align:left}}
.{c} .article :where(h1,h3,h4,h5,h6)::before,.{c} .article :where(h1,h3,h4,h5,h6)::after{{content:none!important;display:none!important}}
.{c} a{{color:var(--accent-deep);text-underline-offset:2px}}
.{c} img{{width:100%;height:auto;display:block}}
.{c} figure{{margin:0}}
.{c} ul,.{c} ol{{margin:0 0 1.4em;padding-left:1.4em;font-size:clamp(18px,1.3vw,20px);line-height:1.9;color:var(--ink-2)}}
.{c} li{{margin:0 0 .4em}}
.{c} .hero{{width:var(--wide);margin:0 auto;padding:clamp(48px,6vw,92px) clamp(16px,2vw,32px) clamp(40px,5vw,72px);display:grid;grid-template-columns:minmax(0,1.02fr) minmax(340px,.82fr);gap:clamp(30px,4vw,64px);align-items:end;border-radius:6px}}
.{c} .hero-text{{min-width:0}}
.{c} .eyebrow{{font-size:15px;font-weight:900;color:var(--accent);letter-spacing:.14em;display:inline-flex;align-items:center;gap:12px;margin:0 0 22px}}
.{c} .eyebrow::before{{content:"";width:52px;height:2px;background:currentColor;display:inline-block}}
.{c} .hero .title{{font-family:{f["head"]};font-weight:800;font-size:clamp(40px,5.2vw,76px);line-height:1.16;letter-spacing:.01em;color:#191410;margin:0}}
.{c} .hero-lead{{font-family:{f["sub"]};font-size:clamp(19px,1.7vw,23px);line-height:1.9;font-weight:600;color:var(--ink-2);margin:clamp(22px,2.6vw,30px) 0 0;max-width:640px;padding-left:20px;border-left:5px solid var(--accent)}}
.{c} .case-line{{display:flex;flex-wrap:wrap;gap:10px 12px;margin:26px 0 0;padding:0;background:none}}
.{c} .case-line > div{{font-size:15px;font-weight:700;color:var(--ink-2);background:rgba(255,252,244,.7);border:1px solid var(--line);padding:8px 14px;border-radius:999px}}
.{c} .hero-photo img{{border-radius:6px;box-shadow:var(--shadow);border:1px solid rgba(38,25,15,.2)}}
.{c} .toc{{max-width:var(--text);margin:clamp(30px,4vw,50px) auto 0;padding:22px 28px;background:rgba(255,253,247,.7);border:1px solid var(--line);border-radius:6px}}
.{c} .toc-title{{font-size:15px;font-weight:900;letter-spacing:.14em;color:var(--cool-deep);margin:0 0 10px}}
.{c} .toc ol{{margin:0;padding-left:1.4em;font-size:17px;line-height:1.8;column-count:2;column-gap:32px}}
.{c} .toc a{{color:var(--ink-2);text-decoration:none}}
.{c} .toc a:hover{{color:var(--accent-deep);text-decoration:underline}}
.{c} main{{counter-reset:sec;display:block}}
.{c} .lead-section,.{c} main > section{{width:100%;margin:0 auto}}
.{c} main > section{{padding:clamp(30px,4vw,58px) 0}}
.{c} .lead-section > *,.{c} main > section > :where(h2,h3,p,ul,ol,.chapter-sub,.read-break,.note,.theory,.route,.table-wrap,.pull,.profile,.text-figure,.stamp){{max-width:var(--text);margin-left:auto;margin-right:auto}}
.{c} .lead-section{{padding:clamp(30px,4vw,56px) 16px clamp(40px,5vw,70px);border-top:1px solid var(--line)}}
.{c} .lead-section p{{font-family:{f["sub"]};font-size:clamp(21px,2vw,28px);line-height:1.85;font-weight:600;color:#241f18;margin:0 auto 1.1em}}
.{c} main > section > h2{{font-family:{f["head"]};font-weight:800;font-size:clamp(30px,3.4vw,50px);line-height:1.28;color:#181310;margin:0 auto 18px;padding:26px 16px 0;position:relative}}
.{c} main > section > h2::before{{counter-increment:sec;content:"0" counter(sec) !important;display:block !important;position:static !important;inset:auto !important;width:auto !important;height:auto !important;border:0 !important;background:none !important;box-shadow:none !important;font-family:{f["body"]} !important;font-size:15px !important;font-weight:900;letter-spacing:.16em;color:var(--cool) !important;margin:0 0 12px !important;padding:0 !important;transform:none !important}}
.{c} main > section > h2::after{{content:none !important;display:none !important}}
.{c} .chapter-sub{{font-family:{f["sub"]};font-size:clamp(18px,1.5vw,22px);color:var(--muted);margin:0 auto 26px;padding:0 16px}}
.{c} main > section > h3{{font-family:{f["sub"]};font-weight:700;font-size:clamp(23px,2.4vw,32px);line-height:1.35;color:var(--accent-deep);margin:44px auto 12px;padding:0 16px}}
.{c} main > section > p,.{c} .lead-section > p:not(:first-child){{font-size:clamp(19px,1.35vw,21px);line-height:2.0;font-weight:450;color:var(--ink-2);margin:0 auto 1.4em;padding:0 16px}}
.{c} main > section > ul,.{c} main > section > ol{{padding-left:2.4em;padding-right:16px}}
.{c} .hot{{font-weight:900;color:var(--accent-deep)}}
.{c} .cool{{font-weight:900;color:var(--cool-deep)}}
.{c} .mini-label{{font-size:max(15px,.82em);font-weight:900;color:#fff8ee;background:var(--accent);padding:.14em .5em .18em;border-radius:4px;display:inline-block;letter-spacing:.02em}}
.{c} .text-figure{{margin:clamp(30px,4vw,56px) auto;padding:0 16px}}
.{c} .wide-figure{{width:var(--wide);margin:clamp(40px,5vw,76px) auto}}
.{c} .wide-figure.full{{width:var(--bleed)}}
.{c} .photo-pair{{width:var(--wide);margin:clamp(40px,5vw,76px) auto;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:clamp(18px,2vw,30px)}}
.{c} .photo-grid{{width:var(--wide);margin:clamp(40px,5vw,76px) auto;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:clamp(16px,1.6vw,26px)}}
.{c} figure img{{border-radius:5px;border:1px solid rgba(38,25,15,.18);box-shadow:var(--shadow-sm)}}
.{c} .portrait img{{aspect-ratio:3/4;object-fit:cover}}
.{c} .wide-figure img{{box-shadow:var(--shadow)}}
.{c} figcaption{{font-size:15px;line-height:1.7;color:var(--muted);margin-top:12px}}
.{c} figcaption .credit{{color:var(--muted)}}
.{c} .read-break{{margin:clamp(50px,6vw,90px) auto;padding:clamp(26px,3vw,40px) clamp(26px,3vw,44px);background:linear-gradient(180deg,rgba(255,253,247,.9),rgba(250,244,231,.85));border-left:8px solid var(--accent);border-radius:2px;box-shadow:var(--shadow-sm);font-family:{f["sub"]};font-size:clamp(20px,2vw,25px);line-height:1.8;font-weight:600;color:#23201a}}
.{c} .note{{margin:38px auto;padding:24px 28px;background:var(--cool-soft);border:1px solid rgba(10,109,111,.28);border-radius:6px;font-size:18px;line-height:1.85;color:#1f2a29}}
.{c} .theory{{margin:44px auto;padding:6px 16px 6px 26px;border-left:5px solid var(--cool);font-size:19px;line-height:1.9;color:var(--ink-2)}}
.{c} .pull{{margin:44px auto;padding:0 16px;font-family:{f["sub"]};font-size:clamp(21px,2vw,27px);line-height:1.75;font-weight:600;color:#241f18;border:0}}
.{c} .pull::before{{content:"“";display:block;font-size:3em;line-height:.6;color:var(--accent);margin-bottom:.2em}}
.{c} .pull cite{{display:block;font-size:16px;font-style:normal;color:var(--muted);margin-top:14px}}
.{c} .route{{margin:40px auto;padding:0 16px}}
.{c} .route-item{{display:grid;grid-template-columns:130px 1fr;gap:22px;padding:18px 0;border-top:1px solid var(--line);font-size:18px;line-height:1.85;color:var(--ink-2)}}
.{c} .route-item:last-child{{border-bottom:1px solid var(--line)}}
.{c} .route-time{{font-weight:900;color:var(--cool-deep);font-size:17px}}
.{c} .table-wrap{{margin:40px auto;overflow-x:auto;border-radius:6px;border:1px solid var(--line)}}
.{c} table{{width:100%;border-collapse:collapse;min-width:560px;background:rgba(255,253,247,.6)}}
.{c} caption{{caption-side:top;text-align:left;font-size:15px;font-weight:900;letter-spacing:.1em;color:var(--cool-deep);padding:12px 16px}}
.{c} th{{background:var(--cool-deep);color:#fdf7ec;font-weight:700;font-size:16px;text-align:left;padding:14px 16px}}
.{c} td{{font-size:16px;line-height:1.7;padding:13px 16px;border-top:1px solid var(--line);color:var(--ink-2);vertical-align:top}}
.{c} tr:nth-child(even) td{{background:rgba(40,31,20,.035)}}
.{c} table.compare td:first-child{{font-weight:900;color:var(--accent-deep);white-space:nowrap}}
.{c} .profile{{margin:40px auto;display:grid;grid-template-columns:180px 1fr;gap:24px;padding:22px;background:rgba(255,253,247,.75);border:1px solid var(--line);border-radius:6px}}
.{c} .profile-body{{min-width:0}}
.{c} .profile-photo img{{aspect-ratio:3/4;object-fit:cover}}
.{c} .profile-photo figcaption{{display:none}}
.{c} .profile-name{{font-family:{f["head"]};font-size:24px;font-weight:800;color:#181310}}
.{c} .profile-role{{font-size:15px;font-weight:700;color:var(--cool-deep);margin:4px 0 10px}}
.{c} .profile p{{font-size:17px;line-height:1.85;color:var(--ink-2);margin:0}}
.{c} .stamp{{display:flex;padding:0 16px;margin:10px auto}}
.{c} .stamp.right{{justify-content:flex-end}}
.{c} .stamp.center{{justify-content:center}}
.{c} .stamp img{{width:auto;max-width:40%}}
.{c} .band{{width:var(--bleed);margin:clamp(40px,5vw,76px) auto;padding:clamp(48px,7vw,120px) 24px;background-size:cover;background-position:center;border-radius:6px;position:relative;color:#fff}}
.{c} .band::before{{content:"";position:absolute;inset:0;background:rgba(10,8,6,.55);border-radius:6px}}
.{c} .band-inner{{position:relative;max-width:var(--text);margin:0 auto;font-family:{f["sub"]};font-size:clamp(22px,2.4vw,32px);line-height:1.7;font-weight:700;text-shadow:0 2px 12px rgba(0,0,0,.5)}}
.{c} .sources{{width:var(--wrap);margin:clamp(56px,7vw,90px) auto 0;max-width:var(--text);padding:30px 16px 0;border-top:3px solid var(--ink);font-size:16px;line-height:1.8;color:var(--muted)}}
.{c} .sources.credits{{margin-top:36px;border-top:1px solid var(--line)}}
.{c} .sources-title{{font-size:15px;font-weight:900;letter-spacing:.14em;color:var(--ink);margin:0 0 12px}}
.{c} .sources ol{{font-size:16px;padding-left:1.6em}}
.{c} .sources a{{word-break:break-all}}
{hero_bg}
@media(max-width:820px){{
  .{c} .hero{{grid-template-columns:1fr;gap:24px;padding-top:34px}}
  .{c} .photo-grid{{grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}
  .{c} .route-item{{grid-template-columns:1fr;gap:6px}}
  .{c} .profile{{grid-template-columns:1fr}}
  .{c} .profile-photo{{max-width:220px}}
  .{c} .toc ol{{column-count:1}}
  .{c} main > section{{padding:26px 0}}
  .{c} .read-break{{padding:22px 20px}}
  .{c} .stamp img{{max-width:55%}}
}}
@media(max-width:600px){{
  .{c} .photo-pair,.{c} .photo-grid{{grid-template-columns:1fr;gap:16px}}
}}'''

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("json")
    ap.add_argument("-o", "--out")
    args = ap.parse_args()
    art = json.load(open(args.json, encoding="utf-8"))
    b = Builder(art)
    out = b.build()
    path = args.out or os.path.join(os.path.dirname(os.path.abspath(args.json)), "article.html")
    open(path, "w", encoding="utf-8").write(out)
    print(f"wrote {path}  ({len(out)//1024} KB, 写真 {len({p['src'] for p in b.photos})} 枚, 章 {len(b.chapters)})")
    for w in b.warnings:
        print("WARN", w)

if __name__ == "__main__":
    main()
