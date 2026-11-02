// 原文标记：{字|拼音} 只注音，{词||解释} 只释义，{字|拼音|解释} 两者都有
const MARK = /\{([^{}|]+)\|([^{}|]*)(?:\|([^{}|]*))?\}/g;
const esc = s => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;");

function renderMarks(o) {
  return o.replace(MARK, (_, w, py, g) => {
    const inner = py ? `<ruby>${w}<rt>${py}</rt></ruby>` : w;
    return g ? `<span class="w" data-w="${esc(w)}" data-py="${esc(py)}" data-g="${esc(g)}">${inner}</span>` : inner;
  });
}

function bindToggles() {
  const py = document.getElementById("pyChk"), tr = document.getElementById("trChk");
  const saved = JSON.parse(localStorage.getItem("zz-view") || "{}");
  if (saved.py === false) py.checked = false;
  if (saved.tr === false) tr.checked = false;
  const apply = () => {
    document.body.classList.toggle("hide-py", !py.checked);
    document.body.classList.toggle("hide-tr", !tr.checked);
    localStorage.setItem("zz-view", JSON.stringify({ py: py.checked, tr: tr.checked }));
  };
  py.onchange = tr.onchange = apply; apply();
}

// 点（或触摸）带虚线的词，弹出解释；点别处关掉
function bindGloss() {
  const box = document.getElementById("gloss");
  let cur = null;
  const hide = () => { box.classList.remove("show"); cur?.classList.remove("on"); cur = null; };
  document.addEventListener("click", e => {
    const w = e.target.closest(".w");
    if (!w) { if (!e.target.closest(".gloss")) hide(); return; }
    e.stopPropagation();
    if (cur === w) { hide(); return; }
    cur?.classList.remove("on"); cur = w; w.classList.add("on");
    box.innerHTML = `<b>${w.dataset.w}</b>${w.dataset.py ? `<i>${w.dataset.py}</i>` : ""}<br>${w.dataset.g}`;
    const r = w.getBoundingClientRect();
    box.style.left = Math.max(8, Math.min(r.left, innerWidth - 310)) + "px";
    box.style.top = (r.bottom + 8) + "px";
    box.classList.add("show");
  });
  addEventListener("scroll", () => { if (innerWidth > 600) hide(); }, { passive: true });
}
