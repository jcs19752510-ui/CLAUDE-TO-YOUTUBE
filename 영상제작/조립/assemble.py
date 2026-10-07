#!/usr/bin/env python3
"""[구형·미사용] 이전 대본(터미널판) 기준 스크립트입니다. 현재는 조립/build_draft.py 를 사용하세요.

영상 조립: AI 음성(V01_p00.mp3 …) + 화면 녹화(B1~B11, 있으면) + 도식·챕터 카드 → 한 편의 영상.

사용법:
    python 조립/assemble.py                 # 초안 (1280x720, 음성 파일 필요)
    python 조립/assemble.py --res 1080      # 최종 (1920x1080)
    python 조립/assemble.py --draft         # 음성 파일이 없어도 '예상 길이'로 구성만 확인 (무음)

폴더 규칙 (영상제작/ 안):
    음성/V01_p00.mp3 ...         ← make_voice.py 가 만든 문단별 음성
    화면녹화/B1_*.mp4 ... B11    ← 내 화면 녹화 (이름이 B6 으로 시작하면 인식, 없으면 '자리 표시' 카드)
    그래픽/영상_mp4/*.mp4        ← 도식·카드 영상 (이미 만들어 둠)

출력 (영상제작/조립결과/):
    영상_초안.mp4 (또는 영상_최종.mp4), 대사자막.srt, 챕터타임라인.txt, 조립로그.txt
"""
import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (CHAPTER_TITLES, CHAPTERS, CHARS_PER_SEC, ROOT, duration, fmt_ts,  # noqa: E402
                    parse_paragraphs, run, tools, voice_name)
from PIL import Image, ImageDraw, ImageFilter, ImageFont  # noqa: E402

FONTS = Path(__file__).resolve().parent / "fonts"
GFX = ROOT / "그래픽" / "영상_mp4"
GAP = 0.6          # 문단 사이 쉼(초)
TAIL = 0.5         # 챕터 끝 여유(초)

# 챕터별 시각 구성
#   lead : 챕터 시작 카드(음성 없이 먼저 재생)
#   base : (소스, 시작 문단, 끝 문단) — 소스가 B# 이고 파일이 있으면 화면 녹화, 없으면 자막 카드
#   over : (그래픽, 기준 문단) — 그 문단이 시작될 때 base 위에 덮어서 재생
#   post : 챕터 끝난 뒤 이어 붙이는 그래픽(음성 없음)
SPEC = {
    "①": dict(lead=[], base=[("B1", 0, 0), ("B2", 1, 1), ("CAP", 2, 2)], over=[], post=["01_타이틀카드"]),
    "②": dict(lead=["챕터카드/11_챕터02_통증과약속", "챕터카드/12_AI음성고지카드"], base=[("CAP", 0, 4)],
              over=[("02_오늘배울3가지", 3)], post=[]),
    "③": dict(lead=["챕터카드/11_챕터03_챗코워크코드"], base=[("B3", 0, 3), ("CAP", 4, 5)],
              over=[("03_챗코워크코드_선택표", 4)], post=[]),
    "④": dict(lead=["챕터카드/11_챕터04_설치와로그인"], base=[("B4", 0, 3), ("B5", 4, 4)],
              over=[("04_설치3단계", 0), ("05_로그인_폴더신뢰", 4)], post=[]),
    "⑤": dict(lead=["챕터카드/11_챕터05_첫프로젝트"], base=[("B6", 0, 3), ("B7", 4, 4), ("CAP", 5, 5)],
              over=[], post=[]),
    "⑥": dict(lead=["챕터카드/11_챕터06_CLAUDEMD"], base=[("B8", 0, 3)], over=[], post=[]),
    "⑦": dict(lead=["챕터카드/11_챕터07_플랜모드"], base=[("B9", 0, 4)], over=[], post=[]),
    "⑧": dict(lead=["챕터카드/11_챕터08_안전장치"], base=[("B10", 0, 0), ("CAP", 1, 1)],
              over=[("06_안전장치_키3개", 0), ("07_초보실수3가지", 1)], post=[]),
    "⑨": dict(lead=["챕터카드/11_챕터09_비용기억"], base=[("B11", 0, 2)],
              over=[("08_비용기억클릭관리", 0)], post=[]),
    "⑩": dict(lead=["챕터카드/11_챕터10_마무리"], base=[("CAP", 0, 2)],
              over=[("09_5줄요약", 1)], post=["10_엔드카드_20초"]),
}
BG, BG2, ORANGE, YELLOW, WHITE, MUTED = "#0f1422", "#171d33", "#ff7a3d", "#ffd23f", "#ffffff", "#9aa6c2"


# ---------------------------------------------------------------- 카드 그림(Pillow)
_bg_cache = {}


def _bg(W, H):
    if (W, H) in _bg_cache:
        return _bg_cache[(W, H)].copy()
    img = Image.new("RGB", (W, H), BG)
    glow = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(glow)
    d.ellipse([int(W * 0.55), -int(H * 0.45), int(W * 1.2), int(H * 0.45)], fill="#3a2012")
    glow = glow.filter(ImageFilter.GaussianBlur(int(W * 0.08)))
    img = Image.blend(img, glow, 0.9)
    _bg_cache[(W, H)] = img
    return img.copy()


def _wrap(text, font, max_w, draw):
    lines, cur = [], ""
    for word in text.split(" "):
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def render_card(path, W, H, tag, caption, label=None):
    img = _bg(W, H)
    d = ImageDraw.Draw(img)
    f_tag = ImageFont.truetype(str(FONTS / "BlackHanSans-Regular.ttf"), int(H * 0.05))
    d.text((int(W * 0.03), int(H * 0.04)), tag, font=f_tag, fill=ORANGE)
    box_w, box_h = int(W * 0.84), int(H * 0.56)
    size = int(H * 0.085)
    while size > int(H * 0.035):
        font = ImageFont.truetype(str(FONTS / "NotoSansKR-Black.ttf"), size)
        lines = _wrap(caption, font, box_w, d)
        if len(lines) * size * 1.4 <= box_h:
            break
        size -= 2
    y = int(H * 0.5 - len(lines) * size * 1.4 / 2)
    for ln in lines:
        w = d.textlength(ln, font=font)
        d.text(((W - w) / 2, y), ln, font=font, fill=WHITE)
        y += int(size * 1.4)
    if label:
        f_l = ImageFont.truetype(str(FONTS / "NotoSansKR-Bold.ttf"), int(H * 0.034))
        tw = d.textlength(label, font=f_l)
        x0, y0 = int(W * 0.03), int(H * 0.9)
        d.rounded_rectangle([x0, y0, x0 + tw + 40, y0 + int(H * 0.065)], radius=24, outline="#ffffff55", width=2,
                            fill="#ffffff14")
        d.text((x0 + 20, y0 + int(H * 0.012)), label, font=f_l, fill=YELLOW)
    img.save(path)


# ---------------------------------------------------------------- ffmpeg 도우미
class Ctx:
    pass


def enc(c):
    return ["-r", str(c.fps), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(c.crf),
            "-preset", "veryfast", "-an"]


def vf_fit(c):
    return (f"scale={c.W}:{c.H}:force_original_aspect_ratio=decrease,"
            f"pad={c.W}:{c.H}:(ow-iw)/2:(oh-ih)/2:color={BG.lstrip('#')},fps={c.fps},format=yuv420p")


def seg_from_png(c, png, dur, out):
    run([c.ff, "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(c.fps), "-t", f"{dur:.3f}", "-i", str(png),
         "-vf", "format=yuv420p"] + enc(c) + [str(out)])


def seg_from_clip(c, clip, dur, out):
    """화면 녹화 클립을 dur 초에 맞춘다: 길면 빠르게, 짧으면 마지막 장면을 멈춰서 늘린다."""
    cd = duration(clip)
    vf = vf_fit(c)
    if cd > dur:
        f = min(cd / dur, 8.0)
        vf = f"setpts=PTS/{f:.4f}," + vf
        if cd / dur > 8.0:
            c.log.append(f"  ⚠ {Path(clip).name}: 8배속으로도 길어서 {dur:.1f}초 뒤는 잘렸습니다 (원본 {cd:.0f}초)")
    else:
        vf = vf + f",tpad=stop_mode=clone:stop_duration={dur - cd + 0.05:.3f}"
    run([c.ff, "-loglevel", "error", "-y", "-i", str(clip), "-vf", vf, "-t", f"{dur:.3f}"] + enc(c) + [str(out)])


def seg_from_gfx(c, gfx, out):
    run([c.ff, "-loglevel", "error", "-y", "-i", str(gfx), "-vf", vf_fit(c)] + enc(c) + [str(out)])


def concat_videos(c, files, out):
    lst = Path(str(out) + ".txt")
    lst.write_text("\n".join(f"file '{Path(f).as_posix()}'" for f in files), encoding="utf8")
    run([c.ff, "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)])


def find_gfx(name):
    p = GFX / f"{name}.mp4"
    if not p.exists():
        raise SystemExit(f"[오류] 그래픽 파일이 없습니다: {p}")
    return p


def find_clip(tag, clips_dir):
    cands = sorted(Path(clips_dir).glob(f"{tag}_*.mp4")) + sorted(Path(clips_dir).glob(f"{tag}.mp4")) \
        + sorted(Path(clips_dir).glob(f"{tag}_*.mkv")) + sorted(Path(clips_dir).glob(f"{tag}_*.mov"))
    return cands[0] if cands else None


# ---------------------------------------------------------------- 챕터 조립
def build_chapter(c, ci, ch, paras, tmp):
    spec = SPEC[ch]
    n = len(paras)
    # 문단 음성 길이
    durs, files = [], []
    for pi in range(n):
        f = c.voice_dir / voice_name(ci, pi)
        if f.exists():
            durs.append(duration(f))
            files.append(f)
        elif c.draft:
            durs.append(max(1.5, len(paras[pi]) / CHARS_PER_SEC))
            files.append(None)
        else:
            raise SystemExit(f"[오류] 음성 파일이 없습니다: {f.name}  (먼저 make_voice.py 를 실행하세요, 또는 --draft)")
    starts, t = [], 0.0
    for d in durs:
        starts.append(t)
        t += d + GAP
    body_voice = t - GAP
    D = body_voice + TAIL
    # 덮어 얹을 그래픽이 문단 시작 + 길이만큼 필요
    over = []
    for g, pi in spec["over"]:
        gp = find_gfx(g)
        over.append((gp, starts[min(pi, n - 1)], duration(gp)))
    body_len = max([D] + [a + gd + 0.3 for _, a, gd in over])
    # 1) 바탕 구간
    parts = []
    seg_i = 0
    bounds = lambda p0, p1: (starts[p0], (starts[p1 + 1] if p1 + 1 < n else D + (body_len - D)))   # noqa: E731
    for src, p0, p1 in spec["base"]:
        t0, t1 = bounds(p0, p1)
        clip = find_clip(src, c.clips_dir) if src.startswith("B") else None
        if clip:
            out = tmp / f"{ch}_b{seg_i}.mp4"
            seg_from_clip(c, clip, t1 - t0, out)
            parts.append(out)
            c.used_clips.append(src)
        else:
            for p in range(p0, p1 + 1):
                a = starts[p]
                b = starts[p + 1] if p + 1 < n else body_len
                png = tmp / f"{ch}_card{p}.png"
                label = f"화면 녹화 {src} 자리" if src.startswith("B") else None
                if src.startswith("B"):
                    c.missing_clips.append(src)
                render_card(png, c.W, c.H, f"{ch} {CHAPTER_TITLES[ch]}", paras[p], label)
                out = tmp / f"{ch}_c{p}.mp4"
                seg_from_png(c, png, b - a, out)
                parts.append(out)
        seg_i += 1
    base = tmp / f"{ch}_base.mp4"
    concat_videos(c, parts, base)
    # 2) 그래픽 덮어쓰기
    body = base
    if over:
        body = tmp / f"{ch}_body.mp4"
        cmd = [c.ff, "-loglevel", "error", "-y", "-i", str(base)]
        for gp, _, _ in over:
            cmd += ["-i", str(gp)]
        flt, last = [], "0:v"
        for i, (gp, a, gd) in enumerate(over, start=1):
            flt.append(f"[{i}:v]scale={c.W}:{c.H},fps={c.fps},format=yuv420p,setpts=PTS-STARTPTS+{a:.3f}/TB[g{i}]")
            flt.append(f"[{last}][g{i}]overlay=enable='between(t,{a:.3f},{a + gd:.3f})':eof_action=pass[v{i}]")
            last = f"v{i}"
        cmd += ["-filter_complex", ";".join(flt), "-map", f"[{last}]", "-t", f"{body_len:.3f}"] + enc(c) + [str(body)]
        run(cmd)
    # 3) 앞(lead) · 뒤(post) 카드
    lead_v, lead_len = [], 0.0
    for g in spec["lead"]:
        gp = find_gfx(g) if "/" not in g else GFX / f"{g}.mp4"
        o = tmp / f"{ch}_lead{len(lead_v)}.mp4"
        seg_from_gfx(c, gp, o)
        lead_v.append(o)
        lead_len += duration(gp) - 0.5
    post_v, post_len = [], 0.0
    for g in spec["post"]:
        gp = find_gfx(g)
        o = tmp / f"{ch}_post{len(post_v)}.mp4"
        seg_from_gfx(c, gp, o)
        post_v.append(o)
        post_len += duration(gp) - 0.5
    video = tmp / f"{ch}_video.mp4"
    concat_videos(c, lead_v + [body] + post_v, video)
    # 4) 오디오 = 무음(lead) + 문단 음성(쉼 포함) + 무음(끝 여유·post)
    wavs = []

    def silence(sec, name):
        w = tmp / name
        run([c.ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-t", f"{max(sec, 0.01):.3f}", str(w)])
        return w
    if lead_len > 0:
        wavs.append(silence(lead_len, f"{ch}_s_lead.wav"))
    for pi in range(n):
        w = tmp / f"{ch}_v{pi}.wav"
        if files[pi]:
            run([c.ff, "-loglevel", "error", "-y", "-i", str(files[pi]), "-ar", "44100", "-ac", "2", str(w)])
        else:
            run([c.ff, "-loglevel", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                 "-t", f"{durs[pi]:.3f}", str(w)])
        wavs.append(w)
        if pi < n - 1:
            wavs.append(silence(GAP, f"{ch}_gap{pi}.wav"))
    wavs.append(silence(body_len - body_voice + post_len, f"{ch}_s_tail.wav"))
    lst = tmp / f"{ch}_a.txt"
    lst.write_text("\n".join(f"file '{w.as_posix()}'" for w in wavs), encoding="utf8")
    audio = tmp / f"{ch}_audio.wav"
    run([c.ff, "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), str(audio)])
    out = tmp / f"{ch}_final.mp4"
    total = lead_len + body_len + post_len
    run([c.ff, "-loglevel", "error", "-y", "-i", str(video), "-i", str(audio), "-c:v", "copy", "-c:a", "aac",
         "-b:a", "128k", "-ar", "44100", "-ac", "2", "-t", f"{total:.3f}", "-movflags", "+faststart", str(out)])
    real = duration(out)
    return dict(path=out, lead=lead_len, body_start=lead_len, starts=starts, durs=durs, total=real)


# ---------------------------------------------------------------- 자막
def split_sentences(text, max_len=34):
    sents = [s.strip() for s in re.split(r"(?<=[.?!])\s+", text) if s.strip()]
    out = []
    for s in sents:
        while len(s) > max_len:
            cut = max(s.rfind(", ", 0, max_len), s.rfind(" ", 0, max_len))
            if cut < 8:
                cut = max_len
            out.append(s[:cut + 1].strip())
            s = s[cut + 1:].strip()
        if s:
            out.append(s)
    return out


def make_srt(chapters_info, paras_all, chapter_offsets):
    cues, n = [], 1
    for ci, ch in enumerate(CHAPTERS):
        info = chapters_info[ch]
        for pi, text in enumerate(paras_all[ch]):
            t0 = chapter_offsets[ch] + info["body_start"] + info["starts"][pi]
            dur = info["durs"][pi]
            sents = split_sentences(text)
            tot = sum(len(s) for s in sents) or 1
            acc = 0
            for s in sents:
                a = t0 + dur * acc / tot
                acc += len(s)
                b = t0 + dur * acc / tot
                cues.append(f"{n}\n{fmt_ts(a, True)} --> {fmt_ts(b, True)}\n{s}\n")
                n += 1
    return "\n".join(cues)


# ---------------------------------------------------------------- 메인
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--res", choices=["720", "1080"], default="720")
    ap.add_argument("--draft", action="store_true", help="음성 파일 없이 예상 길이로 구성 확인 (무음)")
    ap.add_argument("--voice-dir", default=str(ROOT / "음성"))
    ap.add_argument("--clips-dir", default=str(ROOT / "화면녹화"))
    ap.add_argument("--out", default=str(ROOT / "조립결과"))
    ap.add_argument("--script", default=str(ROOT / "07_읽기용_대본.md"))
    a = ap.parse_args()

    ff, _ = tools()
    c = Ctx()
    c.ff, c.draft = ff, a.draft
    c.W, c.H = (1920, 1080) if a.res == "1080" else (1280, 720)
    c.fps, c.crf = (30, 20) if a.res == "1080" else (30, 26)
    c.voice_dir, c.clips_dir = Path(a.voice_dir), Path(a.clips_dir)
    c.log, c.used_clips, c.missing_clips = [], [], []
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    paras_all = parse_paragraphs(a.script)

    with tempfile.TemporaryDirectory(prefix="asm_") as td:
        tmp = Path(td)
        infos, finals = {}, []
        for ci, ch in enumerate(CHAPTERS):
            print(f"[{ci + 1}/10] 챕터 {ch} {CHAPTER_TITLES[ch]} 조립 중 ...", flush=True)
            infos[ch] = build_chapter(c, ci, ch, paras_all[ch], tmp)
            finals.append(infos[ch]["path"])
        offsets, t = {}, 0.0
        for ch in CHAPTERS:
            offsets[ch] = t
            t += infos[ch]["total"]
        name = "영상_초안.mp4" if (a.res == "720" or a.draft) else "영상_최종.mp4"
        concat = tmp / "all.mp4"
        lst = tmp / "all.txt"
        lst.write_text("\n".join(f"file '{f.as_posix()}'" for f in finals), encoding="utf8")
        run([ff, "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
             "-movflags", "+faststart", str(out / name)])
    (out / "대사자막.srt").write_text(make_srt(infos, paras_all, offsets), encoding="utf8")
    lines = []
    for ch in CHAPTERS:
        lines.append(f"{fmt_ts(offsets[ch])} {CHAPTER_TITLES[ch]}")
    lines[0] = "0:00 " + CHAPTER_TITLES[CHAPTERS[0]]
    (out / "챕터타임라인.txt").write_text(
        "※ 아래는 이 조립본 기준 시각입니다. 영상을 다시 편집하면 시각이 달라지니 최종 영상 기준으로 다시 확인하세요.\n"
        "※ 유튜브 챕터는 0:00으로 시작하고 3개 이상, 각 10초 이상이어야 합니다.\n\n" + "\n".join(lines) + "\n",
        encoding="utf8")
    miss = sorted(set(c.missing_clips))
    used = sorted(set(c.used_clips))
    log = [f"총 길이: {fmt_ts(t)} ({t:.0f}초)", f"해상도: {c.W}x{c.H}", f"음성: {'예상 길이(무음)' if a.draft else '실제 음성 파일'}",
           f"사용한 화면 녹화: {', '.join(used) if used else '없음'}",
           f"비어 있는 화면 녹화(자리 표시 카드로 대체): {', '.join(miss) if miss else '없음'}"] + c.log
    (out / "조립로그.txt").write_text("\n".join(log) + "\n", encoding="utf8")
    print("\n".join(log))
    print(f"\n완료 → {out / name}")


if __name__ == "__main__":
    main()
