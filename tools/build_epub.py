"""把 data/NN-id.json 打包成 EPUB3（兼顾 Kindle）：原文带拼音（ruby，带括号回退），
释义做成可弹出的脚注，每句下面跟白话；《养生主》庖丁解牛一段插入 5 张水墨插画。
用法：python build_epub.py [输出路径]"""
import datetime, html, io, json, os, re, sys, uuid, zipfile
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(HERE, "..")
DATA = os.path.join(SITE, "data")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "dist", "庄子-逐句白话注释本.epub")
MARK = re.compile(r"\{([^{}|]+)\|([^{}|]*)(?:\|([^{}|]*))?\}")
FONT = "/System/Library/Fonts/Supplemental/Songti.ttc"
BOOK_ID = "urn:uuid:" + str(uuid.uuid5(uuid.NAMESPACE_URL, "michaelzhenginchina-rgb.github.io/zhuangzi"))
PARTS = ("内篇", "外篇", "杂篇")
esc = lambda s: html.escape(s, quote=True)

idx = json.load(open(os.path.join(DATA, "index.json"), encoding="utf-8"))
chapters = [json.load(open(os.path.join(DATA, c["key"] + ".json"), encoding="utf-8")) for c in idx]

# 庖丁解牛插画：放在含这些文字的句子后面
PICS = [("乃中", "cover_dance_1", "庖丁为文惠君解牛，动作合乎舞步与乐律"),
        ("臣以神遇", "no_whole_ox_1", "以神遇而不以目视：看见的只是骨节间的缝"),
        ("恢恢乎", "blade_gap_1", "以无厚入有间，恢恢乎游刃有余"),
        ("如土", "satisfied_1", "謋然已解，如土委地"),
        ("善刀", "satisfied_2", "提刀而立，踌躇满志，善刀而藏之")]


def page(title, inner):
    return ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh-CN" xml:lang="zh-CN">'
            f'<head><meta charset="utf-8"/><title>{esc(title)}</title><link rel="stylesheet" type="text/css" href="style.css"/></head>'
            f'<body>{inner}</body></html>')


def ruby(w, py):
    syl, chars = py.split(), list(w)
    if len(syl) == len(chars):  # 逐字注音，Kindle 上对齐更稳
        return "".join(f"<ruby>{esc(c)}<rp>(</rp><rt>{esc(s)}</rt><rp>)</rp></ruby>" for c, s in zip(chars, syl))
    return f"<ruby>{esc(w)}<rp>(</rp><rt>{esc(py)}</rt><rp>)</rp></ruby>"


def chapter_xhtml(d):
    notes, body = [], []
    body.append(f'<section epub:type="chapter" id="top"><h1><span class="part">{esc(d["part"])} · 第 {d["n"]} 篇</span><br/>{esc(d["title"])}</h1>')
    body.append(f'<p class="intro">{esc(d["intro"])}</p>')
    for si, sec in enumerate(d["sections"], 1):
        body.append(f'<h2 id="s{si}"><span class="no">{si:02d}</span> {esc(sec["title"])}</h2>')
        pics = list(PICS) if sec.get("illustrated") else []
        for s in sec["sents"]:
            parts, last = [], 0
            for m in MARK.finditer(s["o"]):
                w, py, g = m.group(1), m.group(2), m.group(3)
                parts.append(esc(s["o"][last:m.start()]))
                inner = ruby(w, py) if py else esc(w)
                if g:
                    n = len(notes) + 1
                    notes.append(f'<aside epub:type="footnote" id="n{n}" class="note"><p><a href="#r{n}" class="back">{esc(w)}</a>'
                                 f'{"　" + esc(py) if py else ""}：{esc(g)}</p></aside>')
                    inner = f'<a epub:type="noteref" href="#n{n}" id="r{n}" class="w">{inner}</a>'
                parts.append(inner)
                last = m.end()
            parts.append(esc(s["o"][last:]))
            body.append(f'<div class="s"><p class="o">{"".join(parts)}</p><p class="t">{esc(s["t"])}</p></div>')
            plain = MARK.sub(lambda m: m.group(1), s["o"])
            for p in list(pics):
                if p[0] in plain:
                    body.append(f'<div class="fig"><img src="img/{p[1]}.jpg" alt="{esc(p[2])}"/><p class="cap">{esc(p[2])}</p></div>')
                    pics.remove(p)
    body.append("</section>")
    if notes:
        body.append('<section epub:type="footnotes" class="notes"><h2 class="nh">注释</h2>' + "".join(notes) + "</section>")
    return page(d["title"], "".join(body)), len(notes)


CSS = """
body { font-family: serif; line-height: 1.7; margin: 0 4%; }
h1 { font-size: 1.9em; text-align: center; margin: 1.5em 0 .6em; font-weight: normal; }
h1 .part { font-size: .45em; color: #666; letter-spacing: .2em; }
h2 { font-size: 1.25em; margin: 1.6em 0 .5em; font-weight: bold; page-break-after: avoid; }
h2 .no { color: #888; font-weight: normal; font-size: .8em; }
p { margin: 0; text-indent: 0; }
.intro { color: #444; margin: 0 0 1.2em; font-size: .95em; }
.s { margin: .7em 0 .9em; }
.o { font-family: "STKai", "Kaiti SC", "KaiTi", serif; font-size: 1.15em; line-height: 2.1; }
.t { color: #555; font-size: .92em; margin-top: .15em; }
ruby rt { font-size: .5em; color: #555; }
a.w { color: inherit; text-decoration: underline; }
.fig { text-align: center; margin: 1em 0; page-break-inside: avoid; }
.fig img { max-width: 100%; }
.cap { font-size: .8em; color: #666; text-align: center; }
.notes { page-break-before: always; }
.nh { text-align: center; }
.note p { font-size: .9em; margin: .3em 0; }
.note a.back { font-weight: bold; text-decoration: none; color: inherit; }
.front p { margin: .6em 0; text-indent: 2em; }
.front h1 { margin-top: 2em; }
nav ol { list-style: none; padding-left: 1em; }
"""


def front(n_notes):
    today = datetime.date.today().isoformat()
    return page("说明", f"""<section class="front" epub:type="preface"><h1>说明</h1>
<p>这是《庄子》三十三篇的逐句对照本：每一句原文下面，紧跟着这一句的白话。</p>
<p>读音容易卡住的字，拼音标在字的上方；意思容易卡住的词带下划线，点一下会弹出解释（全书 {n_notes} 条）。每一篇的注释也集中列在这一篇末尾。</p>
<p>目录可以直接跳到每一篇里的每一个故事，比如「鲲鹏展翅」「庄周梦蝶」「庖丁解牛」「濠梁之辩」。《养生主》里的庖丁解牛一段配有五幅水墨插画。</p>
<p>原文取自维基文库《莊子》（公版），转为简体，个别异体字照原样保留。白话与注释为本书原创，由 AI 起稿，尚未逐条人工校对；有争议的地方，注释里写了“一说”。</p>
<p>网页版（含朗读）：michaelzhenginchina-rgb.github.io/zhuangzi</p>
<p>制作日期：{today}</p></section>""")


def nav_xhtml():
    items = ['<li><a href="front.xhtml">说明</a></li>']
    for part in PARTS:
        sub = []
        for ci, d in enumerate(chapters):
            if d["part"] != part:
                continue
            secs = "".join(f'<li><a href="c{ci+1:02d}.xhtml#s{si}">{esc(s["title"])}</a></li>' for si, s in enumerate(d["sections"], 1))
            sub.append(f'<li><a href="c{ci+1:02d}.xhtml#top">{esc(d["title"])}</a><ol>{secs}</ol></li>')
        first = next(ci for ci, d in enumerate(chapters) if d["part"] == part)
        items.append(f'<li><a href="c{first+1:02d}.xhtml#top">{part}</a><ol>{"".join(sub)}</ol></li>')
    return page("目录", f'<nav epub:type="toc" id="toc"><h1>目录</h1><ol>{"".join(items)}</ol></nav>'
                      '<nav epub:type="landmarks" hidden=""><ol><li><a epub:type="toc" href="nav.xhtml">目录</a></li>'
                      '<li><a epub:type="bodymatter" href="c01.xhtml">正文</a></li></ol></nav>')


def ncx():
    n = 0

    def pt(label, src, kids=""):
        nonlocal n
        n += 1
        return f'<navPoint id="p{n}" playOrder="{n}"><navLabel><text>{esc(label)}</text></navLabel><content src="{src}"/>{kids}</navPoint>'
    pts = [pt("说明", "front.xhtml")]
    for part in PARTS:
        first = next(ci for ci, d in enumerate(chapters) if d["part"] == part)
        label_n = n
        kids = ""
        head_src = f"c{first+1:02d}.xhtml#top"
        n += 1  # 先占住“部分”的序号
        part_order = n
        for ci, d in enumerate(chapters):
            if d["part"] != part:
                continue
            n += 1
            ch_order = n
            secs = "".join(pt(s["title"], f"c{ci+1:02d}.xhtml#s{si}") for si, s in enumerate(d["sections"], 1))
            kids += (f'<navPoint id="p{ch_order}" playOrder="{ch_order}"><navLabel><text>{esc(d["title"])}</text></navLabel>'
                     f'<content src="c{ci+1:02d}.xhtml#top"/>{secs}</navPoint>')
        pts.append(f'<navPoint id="p{part_order}" playOrder="{part_order}"><navLabel><text>{part}</text></navLabel>'
                   f'<content src="{head_src}"/>{kids}</navPoint>')
    return ('<?xml version="1.0" encoding="utf-8"?><ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
            f'<head><meta name="dtb:uid" content="{BOOK_ID}"/></head><docTitle><text>庄子</text></docTitle><navMap>{"".join(pts)}</navMap></ncx>')


def cover_jpg():
    W, H = 1600, 2560
    im = Image.new("RGB", (W, H), (243, 236, 223))
    art = Image.open(os.path.join(SITE, "img/flow/cover_dance_1.jpg")).convert("RGB")
    art = art.resize((W, int(art.height * W / art.width)))
    im.paste(art, (0, H - art.height - 260))
    dr = ImageDraw.Draw(im)
    big, mid, sm = (ImageFont.truetype(FONT, s, index=0) for s in (300, 80, 54))

    def center(y, text, font, fill):
        dr.text(((W - dr.textlength(text, font=font)) / 2, y), text, font=font, fill=fill)
    center(300, "庄 子", big, (29, 26, 23))
    center(700, "逐句白话 · 注音释义", mid, (90, 81, 72))
    center(830, "内篇 · 外篇 · 杂篇　三十三篇全", sm, (154, 143, 130))
    dr.rectangle([W / 2 - 85, 985, W / 2 + 85, 1165], outline=(178, 58, 42), width=6)
    center(1003, "一则", sm, (178, 58, 42))
    center(1075, "一画", sm, (178, 58, 42))
    b = io.BytesIO()
    im.save(b, "JPEG", quality=88)
    return b.getvalue()


def small_jpg(name):
    im = Image.open(os.path.join(SITE, f"img/flow/{name}.jpg")).convert("RGB")
    im.thumbnail((1200, 1200))
    b = io.BytesIO()
    im.save(b, "JPEG", quality=82)
    return b.getvalue()


def opf(files):
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    man = "".join(f'<item id="{i}" href="{h}" media-type="{t}"{p}/>' for i, h, t, p in files)
    spine = '<itemref idref="cover"/><itemref idref="nav"/>' + "".join(
        f'<itemref idref="{i}"/>' for i, h, t, p in files if h.endswith(".xhtml") and i not in ("cover", "nav"))
    return ('<?xml version="1.0" encoding="utf-8"?>'
            '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid" xml:lang="zh-CN">'
            '<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f'<dc:identifier id="bookid">{BOOK_ID}</dc:identifier><dc:title>庄子（逐句白话注释本）</dc:title>'
            '<dc:creator>庄子</dc:creator><dc:contributor>白话与注释：庄子·一则一画</dc:contributor>'
            '<dc:language>zh-CN</dc:language><dc:description>《庄子》三十三篇逐句白话对照，注音释义。</dc:description>'
            f'<meta property="dcterms:modified">{now}</meta><meta name="cover" content="cover-img"/></metadata>'
            f'<manifest>{man}</manifest><spine toc="ncx">{spine}</spine>'
            '<guide><reference type="cover" title="封面" href="cover.xhtml"/><reference type="toc" title="目录" href="nav.xhtml"/>'
            '<reference type="text" title="正文" href="c01.xhtml"/></guide></package>')


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    files = [("cover", "cover.xhtml", "application/xhtml+xml", ""),
             ("nav", "nav.xhtml", "application/xhtml+xml", ' properties="nav"'),
             ("front", "front.xhtml", "application/xhtml+xml", "")]
    files += [(f"c{ci+1:02d}", f"c{ci+1:02d}.xhtml", "application/xhtml+xml", "") for ci in range(len(chapters))]
    files += [("ncx", "toc.ncx", "application/x-dtbncx+xml", ""), ("css", "style.css", "text/css", ""),
              ("cover-img", "img/cover.jpg", "image/jpeg", ' properties="cover-image"')]
    files += [(f"img-{p[1]}", f"img/{p[1]}.jpg", "image/jpeg", "") for p in PICS]

    pages = [chapter_xhtml(d) for d in chapters]
    n_notes = sum(n for _, n in pages)
    with zipfile.ZipFile(OUT, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)

        def w(name, data):
            z.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)
        w("META-INF/container.xml", '<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">'
          '<rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>')
        w("OEBPS/content.opf", opf(files))
        w("OEBPS/toc.ncx", ncx())
        w("OEBPS/nav.xhtml", nav_xhtml())
        w("OEBPS/front.xhtml", front(n_notes))
        w("OEBPS/style.css", CSS)
        w("OEBPS/cover.xhtml", page("封面", '<div style="text-align:center"><img src="img/cover.jpg" alt="封面" style="max-width:100%;height:auto"/></div>'))
        w("OEBPS/img/cover.jpg", cover_jpg())
        for p in PICS:
            w(f"OEBPS/img/{p[1]}.jpg", small_jpg(p[1]))
        for ci, (xh, _) in enumerate(pages):
            w(f"OEBPS/c{ci+1:02d}.xhtml", xh)
    print(OUT, os.path.getsize(OUT) // 1024, "KB，注释", n_notes, "条")
