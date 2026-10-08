#!/usr/bin/env python3
"""이미 만든 영상(mp4) 위에 2D 캐릭터를 '지정한 구간에만' 오른쪽 아래에 얹는다. 입 모양은 그 구간의 소리 크기에 맞춘다.
GPU·외부 서비스 불필요 (PIL + numpy + ffmpeg).

사용 예:
  python3 조립/add_avatar.py 입력.mp4 출력.mp4 --seg 0:15 --seg 600:620 --seg 1200:1220 --seg 1500:1520
옵션: --size 300(캐릭터 한 변 픽셀, 1080p 기준) --margin 24 --corner br(br/bl/tr/tl)
구간 = 시작초:끝초 (또는 분:초 형식 1:30:1:50 은 지원하지 않으니 초 단위로).
"""
import argparse, math, shutil, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

FPS = 30
FF = shutil.which("ffmpeg")
if not FF:
    import imageio_ffmpeg; FF = imageio_ffmpeg.get_ffmpeg_exe()


def envelope(src, a, b):
    raw = subprocess.run([FF, "-loglevel", "error", "-ss", str(a), "-t", str(b - a), "-i", str(src), "-vn", "-f", "s16le", "-ar", "16000", "-ac", "1", "-"],
                         capture_output=True).stdout
    x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
    n = int((b - a) * FPS); win = 16000 // FPS
    env = np.array([np.sqrt(np.mean(x[i * win:(i + 1) * win] ** 2) + 1e-9) if (i + 1) * win <= len(x) else 0.0 for i in range(n)])
    env = env / (np.percentile(env, 95) + 1e-9)
    sm = np.zeros(n); v0 = 0.0
    for i, v in enumerate(env):
        v0 += (min(v, 1.2) - v0) * (0.55 if v > v0 else 0.35); sm[i] = v0
    return sm


def frame(i, m, size, S=4, W=420):
    im = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = W * S // 2; s = S
    bob = int(math.sin(i / FPS * 2.2) * 5 * s)
    d.ellipse([c - 150 * s, c - 120 * s + bob, c + 150 * s, c + 170 * s + bob], fill=(255, 224, 189, 255))
    d.pieslice([c - 160 * s, c - 160 * s + bob, c + 160 * s, c + 80 * s + bob], 180, 360, fill=(50, 40, 40, 255))
    blink = (i % 110) < 4
    for ex in (-55, 55):
        ey = c - 10 * s + bob
        if blink: d.line([c + ex * s - 18 * s, ey, c + ex * s + 18 * s, ey], fill=(40, 30, 30, 255), width=5 * s)
        else: d.ellipse([c + ex * s - 14 * s, ey - 18 * s, c + ex * s + 14 * s, ey + 18 * s], fill=(40, 30, 30, 255))
    d.line([c - 80 * s, c - 50 * s + bob, c - 35 * s, c - 56 * s + bob], fill=(50, 40, 40, 255), width=5 * s)
    d.line([c + 35 * s, c - 56 * s + bob, c + 80 * s, c - 50 * s + bob], fill=(50, 40, 40, 255), width=5 * s)
    h = int((4 + 46 * min(m, 1.0)) * s); w = int((46 + 14 * min(m, 1.0)) * s); my = c + 75 * s + bob
    d.ellipse([c - w, my - h // 2, c + w, my + h // 2], fill=(150, 40, 50, 255))
    for cx in (-55, 55):
        d.ellipse([c + cx * s - 15 * s, c + 40 * s + bob, c + cx * s + 15 * s, c + 52 * s + bob], fill=(255, 170, 160, 140))
    d.rounded_rectangle([c - 110 * s, c + 150 * s + bob, c + 110 * s, c + 200 * s + bob], 20 * s, fill=(255, 205, 0, 255))
    return im.resize((size, size), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("--seg", action="append", required=True, help="시작초:끝초 (여러 번 지정)")
    ap.add_argument("--size", type=int, default=300); ap.add_argument("--margin", type=int, default=24)
    ap.add_argument("--corner", default="br", choices=["br", "bl", "tr", "tl"])
    a = ap.parse_args()
    segs = []
    for s in a.seg:
        x, y = s.split(":"); segs.append((float(x), float(y)))
    tmp = Path(a.dst).resolve().parent / "_avatar_tmp"; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
    ins = ["-i", a.src]; chain = []; last = "0:v"
    xx = f"W-w-{a.margin}" if a.corner[1] == "r" else str(a.margin)
    yy = f"H-h-{a.margin}" if a.corner[0] == "b" else str(a.margin)
    for k, (s0, s1) in enumerate(segs, 1):
        env = envelope(a.src, s0, s1); fd = tmp / f"s{k}"; fd.mkdir()
        for i, m in enumerate(env): frame(i, m, a.size).save(fd / f"{i:05d}.png")
        ins += ["-itsoffset", f"{s0}", "-framerate", str(FPS), "-i", str(fd / "%05d.png")]
        chain.append(f"[{last}][{k}:v]overlay={xx}:{yy}:eof_action=pass:repeatlast=0[v{k}]"); last = f"v{k}"
    cmd = [FF, "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "0:a?",
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", a.dst]
    subprocess.run(cmd, check=True); shutil.rmtree(tmp)
    print("만듦:", a.dst, f"(구간 {len(segs)}개)")

main() if __name__ == "__main__" else None
