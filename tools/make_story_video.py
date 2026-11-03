"""把逐句配音 + 每个镜头一张图（或一段视频）合成讲故事短片：
画面缓慢推拉（Ken Burns）、镜头间淡入淡出、逐句字幕、片头标题，响度 -14 LUFS / 峰值 -1 dBTP。
用法：python make_story_video.py 配置.json
配置：{"out": "...mp4", "title": "庄周梦蝶", "voice_dir": "...", "script": "script.txt",
       "shots": [{"media": "b01.jpg", "lines": ["s01"], "move": "in"}, ...]}
move 可选 in / out / left / right；media 是 .mp4 时直接用视频（循环或截取到需要的长度）。"""
import json, os, re, subprocess, sys, tempfile

W, H, FPS = 1920, 1080, 24
GAP = 0.35          # 同一镜头内句与句之间的停顿
SHOT_GAP = 0.6      # 换镜头时多留的停顿
LEAD, TAIL = 1.2, 2.0
XF = 0.8            # 镜头间淡入淡出时长
FONT_DIR = "/System/Library/Fonts/Supplemental"
FONT = "Songti SC"


def dur(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def wrap(txt, limit=22):
    """中文字幕不会自动换行：太长就在靠近中间的标点后断成两行"""
    if len(txt) <= limit:
        return txt
    cuts = [i + 1 for i, c in enumerate(txt[:-1]) if c in "，、；：！？"]
    if not cuts:
        return txt
    k = min(cuts, key=lambda i: abs(i - len(txt) / 2))
    return txt[:k] + "\\N" + txt[k:]


def ts(t):
    h, t = divmod(t, 3600); m, s = divmod(t, 60)
    return f"{int(h)}:{int(m):02d}:{s:05.2f}"


def main(cfg_path):
    cfg = json.load(open(cfg_path, encoding="utf-8"))
    base = os.path.dirname(os.path.abspath(cfg_path))
    P = lambda p: p if os.path.isabs(p) else os.path.join(base, p)
    lines = dict(l.split("|", 1) for l in open(P(cfg["script"]), encoding="utf-8").read().strip().split("\n"))
    vdir = P(cfg["voice_dir"])
    tmp = tempfile.mkdtemp(prefix="storyvid-")

    # 1. 排时间：每句配音的起止时间、每个镜头的起止时间
    t = LEAD
    subs, audio_parts, shot_times = [], [], []
    for i, sh in enumerate(cfg["shots"]):
        start = t if i else 0.0
        for j, lid in enumerate(sh["lines"]):
            p = os.path.join(vdir, lid + ".mp3")
            d = dur(p)
            audio_parts.append((t, p))
            subs.append((t, t + d, lines[lid]))
            t += d + GAP
        t += SHOT_GAP
        shot_times.append([start, t])
    total = t + TAIL
    shot_times[-1][1] = total

    # 2. 每个镜头做成一段视频（比实际多出 XF 秒用于淡入淡出）
    clips = []
    moves = {"in": ("1+0.10*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
             "out": ("1.10-0.10*on/{n}", "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"),
             "left": ("1.10", "(iw-iw/zoom)*(1-on/{n})", "ih/2-(ih/zoom/2)"),
             "right": ("1.10", "(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)")}
    for i, (sh, (a, b)) in enumerate(zip(cfg["shots"], shot_times)):
        d = (b - a) + (XF if i < len(cfg["shots"]) - 1 else 0)
        n = int(round(d * FPS))
        out = os.path.join(tmp, f"shot{i:02d}.mp4")
        media = P(sh["media"])
        if media.lower().endswith(".mp4"):
            # 视频比需要的短：最多放慢到 0.8 倍（不插帧），还不够再定格最后一帧
            slow = max(0.8, min(1.0, dur(media) / d))
            vf = (f"setpts=PTS/{slow:.3f},scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},fps={FPS},"
                  f"tpad=stop_mode=clone:stop_duration={d},trim=duration={d},setsar=1,format=yuv420p")
            cmd = ["ffmpeg", "-y", "-v", "error", "-i", media, "-an", "-vf", vf, "-t", f"{d}", out]
        else:
            z, x, y = moves[sh.get("move", "in")]
            # 先放大到 2 倍再推拉，避免抖动
            vf = (f"scale={W*2}:{H*2}:force_original_aspect_ratio=increase:flags=lanczos,crop={W*2}:{H*2},"
                  f"zoompan=z='{z.format(n=n)}':x='{x.format(n=n)}':y='{y.format(n=n)}':d={n}:s={W}x{H}:fps={FPS},"
                  f"setsar=1,format=yuv420p")
            cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", media, "-vf", vf, "-frames:v", str(n), out]
        subprocess.run(cmd, check=True)
        clips.append((out, d))

    # 3. 镜头之间淡入淡出拼起来
    inputs, fc, prev, off = [], [], "0:v", 0.0
    for c, _ in clips:
        inputs += ["-i", c]
    for i in range(1, len(clips)):
        off += clips[i - 1][1] - XF
        lab = f"v{i}"
        fc.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XF}:offset={off:.3f}[{lab}]")
        prev = lab
    video = os.path.join(tmp, "video.mp4")
    if fc:
        subprocess.run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fc), "-map", f"[{prev}]",
                        "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", video], check=True)
    else:
        os.replace(clips[0][0], video)

    # 4. 配音按时间点放好
    ain, amix = [], []
    for k, (st, p) in enumerate(audio_parts):
        ain += ["-i", p]
        amix.append(f"[{k}:a]adelay={int(st*1000)}|{int(st*1000)}[a{k}]")
    mixed = os.path.join(tmp, "voice.wav")
    fc = ";".join(amix) + ";" + "".join(f"[a{k}]" for k in range(len(audio_parts))) + \
        f"amix=inputs={len(audio_parts)}:normalize=0,apad=whole_dur={total},atrim=0:{total}[a]"
    subprocess.run(["ffmpeg", "-y", "-v", "error", *ain, "-filter_complex", fc, "-map", "[a]", mixed], check=True)

    # 4b. 背景音乐：有人声时自动压低（sidechain），片头淡入、片尾淡出
    if cfg.get("music"):
        mu = cfg["music"]
        bed = os.path.join(tmp, "with_music.wav")
        st, vol = mu.get("start", 0), mu.get("volume", 0.30)
        fc = (f"[1:a]atrim={st}:{st + total},asetpts=PTS-STARTPTS,aformat=sample_rates=48000:channel_layouts=stereo,"
              f"volume={vol},afade=t=in:d=2.5,afade=t=out:st={total - 4:.2f}:d=4[m];"
              f"[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[v][sc];"
              f"[m][sc]sidechaincompress=threshold=0.02:ratio=6:attack=80:release=900[md];"
              f"[v][md]amix=inputs=2:normalize=0:duration=first[a]")
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", mixed, "-i", P(mu["file"]), "-filter_complex", fc,
                        "-map", "[a]", bed], check=True)
        mixed = bed

    # 5. 字幕（ASS）：片头大标题 + 逐句字幕
    ass = os.path.join(tmp, "subs.ass")
    title = cfg.get("title")
    with open(ass, "w", encoding="utf-8") as f:
        f.write(f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{FONT},54,&H00F4F0EA,&H00F4F0EA,&H5A14100C,&H5A14100C,0,0,0,0,100,100,3,0,3,14,0,2,200,200,60,1
Style: Title,{FONT},150,&H00201A1D,&H00201A1D,&H00E0EAF3,&H00000000,1,0,0,0,100,100,24,0,1,4,0,5,100,100,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""")
        for k, (a, b, txt) in enumerate(subs):
            if k == 0 and title and txt.strip("。") == title:
                f.write(f"Dialogue: 0,{ts(0.3)},{ts(shot_times[0][1])},Title,,0,0,0,,{{\\fad(700,700)}}{title}\n")
                continue
            f.write(f"Dialogue: 0,{ts(a)},{ts(b + 0.15)},Sub,,0,0,0,,{{\\fad(150,150)}}{wrap(txt)}\n")

    # 6. 合成：画面 + 字幕 + 配音（响度 -14 LUFS，峰值 -1 dBTP）
    out = P(cfg["out"])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video, "-i", mixed,
                    "-vf", f"ass={ass}:fontsdir={FONT_DIR},fade=t=in:st=0:d=1,fade=t=out:st={total-1.2:.2f}:d=1.2",
                    "-af", f"loudnorm=I=-14:TP=-1:LRA=11,afade=t=out:st={total-1.2:.2f}:d=1.2",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{total:.2f}", out], check=True)
    print(f"{out}  时长 {total:.1f} 秒，{len(cfg['shots'])} 个镜头，{len(subs)} 句")


if __name__ == "__main__":
    main(sys.argv[1])
