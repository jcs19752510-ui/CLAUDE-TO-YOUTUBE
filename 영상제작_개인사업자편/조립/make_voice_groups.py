#!/usr/bin/env python3
"""긴 챕터를 문단 묶음(그룹)으로 나눠 요청한다. 챕터 전체를 한 번에 요청하면 서버 오류(502)가 나는 경우용.
사용: python3 조립/make_voice_groups.py --only 2 3 [--maxchars 700] [--group 1]   (--group: 그룹 번호 하나만, 1부터)
요청 수 = 챕터별 ceil(글자수/maxchars). 이미 만든 문단 파일은 건너뜀. 오류(502)나 하루 한도가 나면 바로 멈춘다."""
import argparse, math, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_voice as mv
from common import CHAPTERS, ROOT, parse_paragraphs, voice_name

ap = argparse.ArgumentParser()
ap.add_argument("--only", type=int, nargs="+", required=True)
ap.add_argument("--maxchars", type=int, default=700)
ap.add_argument("--group", type=int)
ap.add_argument("--model", default="gemini-2.5-flash-preview-tts"); ap.add_argument("--voice", default="Kore")
ap.add_argument("--speed", type=float, default=0.92); ap.add_argument("--gap", type=float, default=8.0)
ap.add_argument("--dry-run", action="store_true")
a = ap.parse_args()
paras = parse_paragraphs(str(ROOT / "10_AI음성_입력용_대본.md")); out = ROOT / "음성"; raw = out / "_원본"; raw.mkdir(parents=True, exist_ok=True)

def groups(pl):
    k = max(1, math.ceil(sum(map(len, pl)) / a.maxchars)); tgt = sum(map(len, pl)) / k
    g, cur, c = [], [], 0
    for i, t in enumerate(pl):
        cur.append(i); c += len(t)
        if c >= tgt and len(g) < k - 1: g.append(cur); cur, c = [], 0
    if cur: g.append(cur)
    return g

for n in a.only:
    ch = CHAPTERS[n - 1]; pl = paras[ch]
    for gi, idx in enumerate(groups(pl), 1):
        if a.group and gi != a.group: continue
        files = [out / voice_name(n - 1, i) for i in idx]
        if all(f.exists() for f in files): print(f"{ch} 그룹{gi} 건너뜀"); continue
        text = [pl[i] for i in idx]; chars = [len(t) for t in text]
        if a.dry_run: print(f"[dry-run] {ch} 그룹{gi}: 문단 {idx[0]}~{idx[-1]} ({sum(chars)}자) 요청 1회"); continue
        audio, mime = mv.synth("\n\n".join(text), a.model, a.voice)
        whole = raw / f"chapter_{n:02d}_g{gi}.mp3"; mv.to_mp3(audio, mime, whole, 1.0)
        res = mv.split_by_silence(whole, len(files), files, a.speed, chars)
        if res is None: print(f"[경고] {ch} 그룹{gi} 분리 실패 → {whole.name} 만 저장"); continue
        for t, f in zip(text, files):
            d = mv.duration_of(f); cps = len(t) / max(d, 0.1)
            print(f"생성: {f.name} ({len(t)}자, {d:.1f}초, {cps:.1f}자/초)" + ("  ⚠ 길이 이상" if cps > 9 or cps < 3.5 else ""))
        time.sleep(a.gap)
