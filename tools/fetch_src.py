# 从维基文库取《庄子》33 篇原文，清理模板，转简体，存成 data/src/NN-id.txt
import json, re, sys, time, urllib.parse, urllib.request
import opencc
sys.path.insert(0, __import__("os").path.dirname(__file__))

from chapters import CH
cc = opencc.OpenCC("t2s")

def raw(title):
    url = "https://zh.wikisource.org/w/index.php?title=" + urllib.parse.quote("莊子/" + title) + "&action=raw"
    req = urllib.request.Request(url, headers={"User-Agent": "zhuangzi-reader/0.1 (personal study project)"})
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")

def clean(t):
    t = re.sub(r"\{\{header2.*?\n\}\}", "", t, flags=re.S)
    t = re.sub(r"\{\{另\|([^|}]*)\|[^}]*\}\}", r"\1", t)          # 异文：取正文
    t = re.sub(r"\[\[Category:[^\]]*\]\]", "", t)
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = re.sub(r"\{\{[^{}]*\}\}", "", t)                          # footer 等其余模板
    t = t.replace("（", "").replace("）", "")                      # 校勘括注：保留字，去括号
    paras = [p.strip() for p in t.split("\n") if p.strip()]
    return paras

def rare(ch):
    o = ord(ch)
    return o > 0xFFFF or 0x3400 <= o <= 0x4DBF

def s2(p):
    # 转简体；若转出来的是扩展区生僻字形而繁体原字是常用区的字，就保留繁体原字（手机字体显示得出来）
    q = cc.convert(p)
    if len(q) == len(p):
        q = "".join(a if (rare(b) and not rare(a)) else b for a, b in zip(p, q))
    q = q.replace("「", "“").replace("」", "”").replace("『", "‘").replace("』", "’")
    return q.replace("遟", "迟")

out = []
for n, cid, tt, st, part in CH:
    r = raw(tt)
    m = re.match(r"#REDIRECT\s*\[\[莊子/([^\]]+)\]\]", r, re.I)
    if m: r = raw(m.group(1))
    paras = [s2(p) for p in clean(r)]
    body = "\n".join(paras)
    open(f"data/src/{n:02d}-{cid}.txt", "w").write(body + "\n")
    chars = len(re.sub(r"[^一-鿿]", "", body))
    out.append((n, st, part, len(paras), chars))
    time.sleep(0.5)
for o in out: print(*o)
print("合计", sum(o[4] for o in out))
