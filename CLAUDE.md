# 庄子互动阅读

《庄子》33 篇逐句原文 + 白话 + 注音释义的网页阅读器，外加 EPUB 和故事动画。

**背景、现状、决策、待办、踩坑都在 vault：`~/Documents/Obsidian Vault/其他项目/庄子互动阅读.md`。动手前先读那页；做完一件事，把结论写回那页。** 本文件只讲这些代码怎么用。

## 线上
- 仓库：GitHub 公开仓库 `michaelzhenginchina-rgb/zhuangzi`，`main` 分支根目录即 GitHub Pages
- 网址：https://michaelzhenginchina-rgb.github.io/zhuangzi/
- 仓库是公开的：提交前确认没有密钥、任务编号（Fish 音频的元数据里会带 `fish.audio task=`，用 `ffmpeg -map_metadata -1 -c copy` 清掉）
- 提交邮箱用 GitHub 匿名地址（仓库本地 git config 已设好）

## 目录
| 路径 | 是什么 |
|---|---|
| `index.html` `reader.html` `common.js` `site.css` | 目录页和通用阅读页（`reader.html?c=NN-id`） |
| `paoding.html` | 《庖丁解牛》完整样板页：朗读 + 插画 + 图解 |
| `data/NN-id.json` | 每篇的分段、逐句原文（带注释标记）和白话；`data/index.json` 是目录 |
| `data/src/NN-id.txt` | 维基文库原文（已转简体），**唯一依据，不许改** |
| `audio/` `img/flow/` | 朗读音频、Flow 水墨插画 |
| `tools/` | 生成、校验、合成脚本 |
| `tools/BRIEF.md` | **翻译与注释的规矩**（格式、注音标准、释义口吻），改数据前必读 |
| `videos/<故事名>/` | 动画：`cfg.json` 镜头表、`script.txt` 逐句文稿、`voice/` 配音、`media/` 画面 |
| `dist/` | 生成的 EPUB（不进仓库） |

## 环境
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
另需 `ffmpeg`（视频）。所有命令在仓库根目录下运行。

## 常用命令
- 本地预览网页：`python3 -m http.server 5321`，打开 http://localhost:5321/
- 校验数据（原文逐字一致、标记格式、拼音）：`.venv/bin/python tools/validate.py [NN ...]`，改完 `data/` 必跑，错误必须为 0
- 重建目录：`.venv/bin/python tools/build_index.py`
- 生成 EPUB：`.venv/bin/python tools/build_epub.py [输出路径]`，默认输出到 `dist/`
- 合成动画：`python3 tools/make_story_video.py videos/庄周梦蝶/cfg.json`，约 40 秒；成品在该故事的 `out/`

## 注释标记（写在原文 `o` 里）
`{字|拼音}` 只注音；`{词||解释}` 只释义；`{字|拼音|解释}` 两者都要。细则见 `tools/BRIEF.md`。

## 不进仓库的东西
- `videos/*/out/`：视频成品，各约 50 MB，可用合成命令重新生成
- `videos/*/music/`：配乐。庄周梦蝶用的是互联网档案馆（archive.org）上的「Beautiful Chinese Music - Guzheng & Bamboo Flute」，存为 `music/guzheng_flute.mp3`
- `dist/`、`.venv/`、`voice-samples/`
