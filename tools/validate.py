"""校验 data/NN-id.json：原文与维基文库原文逐字一致、标记格式正确、拼音是这个字的合法读音。
用法：python validate.py [NN ...]（不给就查全部已有的）"""
import json, re, sys, glob, os
from pypinyin import pinyin, Style

ROOT = os.path.join(os.path.dirname(__file__), "..", "data")
MARK = re.compile(r"\{([^{}|]+)\|([^{}|]*)(?:\|([^{}|]*))?\}")
PUNCT = "，。：；！？“”‘’、《》·—…"

def strip(o):
    return MARK.sub(lambda m: m.group(1), o)

def check(path):
    n = os.path.basename(path)[:2]
    src_path = glob.glob(os.path.join(ROOT, "src", n + "-*.txt"))[0]
    paras = [p for p in open(src_path, encoding="utf-8").read().split("\n") if p.strip()]
    errs, warns = [], []
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return [f"JSON 解析失败：{e}"], []
    for k in ("n", "id", "title", "part", "intro", "sections"):
        if k not in d: errs.append(f"缺字段 {k}")
    secs = d.get("sections", [])
    if len(secs) != len(paras):
        errs.append(f"sections 数 {len(secs)} ≠ 原文段落数 {len(paras)}")
    n_marks = n_chars = 0
    for i, (sec, para) in enumerate(zip(secs, paras), 1):
        if not sec.get("title"): errs.append(f"第{i}段缺 title")
        sents = sec.get("sents", [])
        joined = "".join(strip(s.get("o", "")) for s in sents)
        if joined != para:
            k = next((j for j, (a, b) in enumerate(zip(joined, para)) if a != b), min(len(joined), len(para)))
            errs.append(f"第{i}段原文不一致，第{k}字附近：译文侧「{joined[max(0,k-8):k+8]}」 原文「{para[max(0,k-8):k+8]}」")
        for j, s in enumerate(sents, 1):
            o, t = s.get("o", ""), s.get("t", "")
            if not t.strip(): errs.append(f"第{i}段第{j}句缺白话")
            if "{" in t or "}" in t: errs.append(f"第{i}段第{j}句白话里有标记")
            rest = MARK.sub("", o)
            if "{" in rest or "}" in rest or "|" in rest: errs.append(f"第{i}段第{j}句标记格式错：{o[:40]}")
            n_chars += len(re.sub(f"[{PUNCT}]", "", strip(o)))
            for m in MARK.finditer(o):
                w, py, g = m.group(1), m.group(2), m.group(3)
                n_marks += 1
                if not py and not g: errs.append(f"「{w}」拼音和解释都空")
                if py:
                    syl = py.split()
                    hz = [c for c in w if c not in PUNCT]
                    if len(syl) != len(hz):
                        errs.append(f"「{w}」拼音音节数 {len(syl)} ≠ 字数 {len(hz)}：{py}")
                        continue
                    for c, y in zip(hz, syl):
                        ok = pinyin(c, style=Style.TONE, heteronym=True)[0]
                        if y not in ok and ok != [c]:
                            warns.append(f"「{c}」标 {y}，词库读音 {'/'.join(ok)}（在「{w}」）")
    return errs, warns, n_marks, n_chars

if __name__ == "__main__":
    want = sys.argv[1:]
    files = sorted(glob.glob(os.path.join(ROOT, "[0-9][0-9]-*.json")))
    if want: files = [f for f in files if os.path.basename(f)[:2] in want]
    bad = 0
    for f in files:
        r = check(f)
        errs, warns = r[0], r[1]
        name = os.path.basename(f)
        dens = f"，注释 {r[2]} 处 / {r[3]} 字" if len(r) > 2 else ""
        print(f"{'✗' if errs else '✓'} {name}{dens}，读音提醒 {len(warns)} 条")
        for e in errs: print("   错误：", e)
        for w in warns: print("   提醒：", w)
        bad += bool(errs)
    sys.exit(1 if bad else 0)
