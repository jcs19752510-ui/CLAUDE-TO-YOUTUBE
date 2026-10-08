"""개인사업자편 초안 조립: 챕터 순서(①~⑧) 그대로, 실제 음성 길이 + 챕터 배경 + 자막.
사용:
    python 조립/build_draft.py            # 음성/V01_p00.mp3 … 가 있으면 쓰고, 없는 문단은 예상 길이 무음
    python 조립/build_draft.py --plan     # 인코딩 없이 배치·경고·타임라인만 확인
    python 조립/build_draft.py --root 폴더 # 작업 폴더 지정(기본: 이 스크립트의 부모 폴더)

배경: 그래픽/영상_mp4/G01.mp4 ~ G08.mp4 (챕터 번호). 있으면 반복 재생하며 하단에 자막을 얹고,
없으면 단색 자막 카드로 대신한다. 결과: 조립결과/개인사업자편_초안.mp4, 대사자막.srt, 챕터타임라인.txt
"""
import argparse, json, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (CHAPTERS, PLAY_ORDER, ROOT as DEFAULT_ROOT, duration, fmt_ts,
                    parse_paragraphs, parse_titles, render_card, voice_name, tools)

ap = argparse.ArgumentParser()
ap.add_argument("--root", default=str(DEFAULT_ROOT))
ap.add_argument("--plan", action="store_true")
args = ap.parse_args()
ROOT = Path(args.root)
G = ROOT / "그래픽" / "영상_mp4"
SCRIPT = ROOT / "10_AI음성_입력용_대본.md"
EST_CPS = 7.4      # 음성 미생성 문단 예상 길이: 글자 수 / 7.4 (낭독 속도 0.92배 기준 어림값)
PAD = 0.5          # 문단 끝 여유(초)
W, H, FPS = 1280, 720, 15
FF, _ = tools()

titles = parse_titles(SCRIPT)
paras = parse_paragraphs(SCRIPT)
for ch in CHAPTERS:
    if not paras.get(ch):
        raise SystemExit(f"[오류] {ch} 문단을 대본에서 찾지 못했습니다: {SCRIPT}")

WARN, MISSING = [], []
segs, starts, t = [], {}, 0.0      # seg = dict(ch, ci, pi, text, dur, voice, bg, bg_off)
for ch, p0, p1 in PLAY_ORDER:
    ci = CHAPTERS.index(ch)
    plist = paras[ch]
    last = len(plist) - 1 if p1 is None else p1
    bg = G / f"G{ci + 1:02d}.mp4"
    bg_len = None
    if bg.exists():
        try:
            bg_len = duration(bg)
        except SystemExit:
            WARN.append(f"배경 읽기 실패(단색 카드로 대체): {bg.name}")
    else:
        WARN.append(f"배경 없음(단색 카드로 대체): G{ci + 1:02d}.mp4")
    if p0 == 0:
        starts[ch] = t
    ch_off = 0.0                                  # 챕터 안에서 지금까지 흐른 시간(배경 영상 이어 재생용)
    for pi in range(p0, last + 1):
        name = voice_name(ci, pi)
        vf = ROOT / "음성" / name
        if vf.exists():
            d, vpath = duration(vf) + PAD, str(vf)
        else:
            d, vpath = len(plist[pi]) / EST_CPS + PAD, None
            MISSING.append(name)
        segs.append(dict(ch=ch, ci=ci, pi=pi, text=plist[pi], dur=d, voice=vpath, t0=t,
                         bg=str(bg) if bg_len else None, bg_off=(ch_off % bg_len) if bg_len else 0.0))
        t += d
        ch_off += d

print(f"세그먼트 {len(segs)}개, 예상 총 {fmt_ts(t)} ({t:.0f}초), 음성 미생성 {len(MISSING)}개")
for w in WARN:
    print("[경고]", w)
if args.plan:
    for ch, p0, _ in PLAY_ORDER:
        if p0 == 0:
            print(f"{fmt_ts(starts[ch])} {titles[ch]}")
    sys.exit(0)

VOPT = ["-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "30", "-preset", "veryfast"]
AOPT = ["-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "2"]
with tempfile.TemporaryDirectory(prefix="draft_") as td:
    S = Path(td)
    files = []
    for i, s in enumerate(segs):
        out = S / f"s{i:03d}.mp4"
        png = S / f"c{i:03d}.png"
        tag = f"{s['ch']} {titles[s['ch']]}"
        ain = ["-i", s["voice"]] if s["voice"] else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        dur = f"{s['dur']:.3f}"
        if s["bg"]:
            render_card(png, W, H, tag, s["text"], overlay=True)
            cmd = [FF, "-loglevel", "error", "-y", "-stream_loop", "-1", "-ss", f"{s['bg_off']:.3f}", "-i", s["bg"],
                   "-loop", "1", "-framerate", str(FPS), "-i", str(png)] + ain + \
                  ["-filter_complex", f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS}[b];"
                   f"[b][1:v]overlay=0:0,format=yuv420p[v]", "-map", "[v]", "-map", "2:a", "-af", "apad", "-t", dur] + VOPT + AOPT + [str(out)]
        else:
            render_card(png, W, H, tag, s["text"])
            cmd = [FF, "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", dur, "-i", str(png)] + ain + \
                  ["-vf", "format=yuv420p", "-af", "apad", "-t", dur, "-shortest"] + VOPT + AOPT + [str(out)]
        rr = subprocess.run(cmd, capture_output=True, text=True)
        if rr.returncode:
            sys.exit(f"실패 {i}: {rr.stderr[-400:]}")
        files.append(f"file '{out}'")
    (S / "list.txt").write_text("\n".join(files))
    OUT = ROOT / "조립결과"
    OUT.mkdir(exist_ok=True)
    dst = OUT / "개인사업자편_초안.mp4"
    subprocess.run([FF, "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(S / "list.txt"),
                    "-c", "copy", "-movflags", "+faststart", str(dst)], check=True)

tl = ["※ 이 초안 영상 기준 시각입니다. 편집 후에는 최종 영상 기준으로 다시 확인하세요.", ""]
tl += [f"{fmt_ts(starts[ch])} {titles[ch]}" for ch, p0, _ in PLAY_ORDER if p0 == 0]
(OUT / "챕터타임라인.txt").write_text("\n".join(tl) + "\n", encoding="utf8")
import re
cues, n = [], 1
for s in segs:
    t0, dur = s["t0"], s["dur"] - PAD
    sents = [x.strip() for x in re.split(r"(?<=[.?!])\s+", s["text"]) if x.strip()]
    tot = sum(len(x) for x in sents) or 1
    acc = 0
    for x in sents:
        a = t0 + dur * acc / tot
        acc += len(x)
        b = t0 + dur * acc / tot
        cues.append(f"{n}\n{fmt_ts(a, True)} --> {fmt_ts(b, True)}\n{x}\n")
        n += 1
(OUT / "대사자막.srt").write_text("\n".join(cues), encoding="utf8")
print(f"완료: {dst}  총 {fmt_ts(duration(dst))} ({duration(dst):.0f}초)")
