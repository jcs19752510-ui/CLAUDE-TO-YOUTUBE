#!/usr/bin/env python3
"""확인용 샘플: 음성 크기에 맞춰 입이 움직이는 2D 캐릭터를 그래픽 영상 위(오른쪽 아래)에 얹는다.
GPU·외부 서비스 없이 PIL+ffmpeg 만 사용. 사용: python3 샘플/make_avatar_sample.py 음성1.mp3 [음성2.mp3 ...]"""
import subprocess, sys, math, shutil
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
R = Path(__file__).resolve().parent.parent
FF = shutil.which("ffmpeg")
FPS = 30
auds = [Path(a) for a in sys.argv[1:]] or sorted((R / "음성/_이전버전").glob("V01_p0*.mp3"))[:2]
tmp = R / "샘플/_tmp"; shutil.rmtree(tmp, ignore_errors=True); tmp.mkdir(parents=True)
# 1) 음성 이어 붙이기 + 크기(엔벨로프)
lst = tmp / "l.txt"; lst.write_text("".join(f"file '{a.resolve()}'\n" for a in auds))
wav = tmp / "a.wav"
subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-ar", "16000", "-ac", "1", str(wav)], check=True)
raw = subprocess.run([FF, "-loglevel", "error", "-i", str(wav), "-f", "s16le", "-ar", "16000", "-ac", "1", "-"], capture_output=True).stdout
x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
dur = len(x) / 16000; n = int(dur * FPS)
win = 16000 // FPS
env = np.array([np.sqrt(np.mean(x[i * win:(i + 1) * win] ** 2) + 1e-9) for i in range(n)])
env = env / (np.percentile(env, 95) + 1e-9)
sm = np.zeros(n); a = 0.0
for i, v in enumerate(env):                      # 부드럽게(입이 덜덜 떨리지 않게)
    a += (min(v, 1.2) - a) * (0.55 if v > a else 0.35); sm[i] = a
# 2) 캐릭터 프레임
S = 4; W = 420
def frame(i):
    im = Image.new("RGBA", (W * S, W * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = W * S // 2; s = S
    bob = int(math.sin(i / FPS * 2.2) * 5 * s)
    d.ellipse([c - 150 * s, c - 120 * s + bob, c + 150 * s, c + 170 * s + bob], fill=(255, 224, 189, 255))       # 얼굴
    d.pieslice([c - 160 * s, c - 160 * s + bob, c + 160 * s, c + 80 * s + bob], 180, 360, fill=(50, 40, 40, 255))  # 머리카락
    blink = (i % 110) < 4
    for ex in (-55, 55):
        ey = c - 10 * s + bob
        if blink: d.line([c + ex * s - 18 * s, ey, c + ex * s + 18 * s, ey], fill=(40, 30, 30, 255), width=5 * s)
        else: d.ellipse([c + ex * s - 14 * s, ey - 18 * s, c + ex * s + 14 * s, ey + 18 * s], fill=(40, 30, 30, 255))
    d.line([c - 80 * s, c - 50 * s + bob, c - 35 * s, c - 56 * s + bob], fill=(50, 40, 40, 255), width=5 * s)
    d.line([c + 35 * s, c - 56 * s + bob, c + 80 * s, c - 50 * s + bob], fill=(50, 40, 40, 255), width=5 * s)
    m = sm[i]; h = int((4 + 46 * min(m, 1.0)) * s); w = int((46 + 14 * min(m, 1.0)) * s); my = c + 75 * s + bob
    d.ellipse([c - w, my - h // 2, c + w, my + h // 2], fill=(150, 40, 50, 255))
    d.ellipse([c - 70 * s, c + 40 * s + bob, c - 40 * s, c + 52 * s + bob], fill=(255, 170, 160, 140))   # 볼터치
    d.ellipse([c + 40 * s, c + 40 * s + bob, c + 70 * s, c + 52 * s + bob], fill=(255, 170, 160, 140))
    d.rounded_rectangle([c - 110 * s, c + 150 * s + bob, c + 110 * s, c + 200 * s + bob], 20 * s, fill=(255, 205, 0, 255))   # 옷
    return im.resize((300, 300), Image.LANCZOS)
fd = tmp / "f"; fd.mkdir()
for i in range(n): frame(i).save(fd / f"{i:05d}.png")
# 3) 배경(그래픽 영상 G01) 위에 합성
bg = R / "그래픽/영상_mp4/G01.mp4"
out = R / "샘플/AI인물_합성샘플.mp4"
subprocess.run([FF, "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", str(bg), "-framerate", str(FPS), "-i", str(fd / "%05d.png"), "-i", str(wav),
    "-filter_complex", "[0:v]scale=1920:1080,fps=30[b];[1:v]format=rgba[a];[b][a]overlay=W-w-24:H-h-16:shortest=1[v]",
    "-map", "[v]", "-map", "2:a", "-t", f"{dur:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-c:a", "aac", "-b:a", "160k", str(out)], check=True)
shutil.rmtree(tmp)
print("만듦:", out, f"{dur:.1f}초")
