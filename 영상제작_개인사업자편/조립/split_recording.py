"""사장님 녹음(영상 또는 음성) 한 챕터를 문단별 mp3로 자른다.
사용: python 조립/split_recording.py 촬영본/ch03.mp4 3 [--out 음성] [--root 폴더]
방법: 무음 구간을 찾고, 가장 긴 (문단수-1)개를 문단 경계로 쓴다. 문단 사이를 2초 이상 쉬면 안정적이다.
검사: 경계 후보가 문단수-1개보다 적거나, N번째와 N+1번째 무음 길이 차이가 작으면 [경고]를 낸다.
"""
import argparse, re, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHAPTERS, ROOT as DEFAULT_ROOT, duration, parse_paragraphs, voice_name, tools

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("chapter", type=int, help="챕터 번호 1~8")
ap.add_argument("--root", default=str(DEFAULT_ROOT)); ap.add_argument("--out", default="음성")
ap.add_argument("--noise", default="-35dB"); ap.add_argument("--min-gap", type=float, default=0.7)
a = ap.parse_args()
ROOT = Path(a.root); FF, _ = tools()
ci = a.chapter - 1
n = len(parse_paragraphs(ROOT / "10_AI음성_입력용_대본.md")[CHAPTERS[ci]])
r = subprocess.run([FF, "-i", a.src, "-vn", "-af", f"silencedetect=noise={a.noise}:d={a.min_gap}", "-f", "null", "-"],
                   capture_output=True, text=True)
st = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
en = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
gaps = sorted(zip(st, en), key=lambda g: g[1] - g[0], reverse=True)
total = duration(Path(a.src))
gaps = [g for g in gaps if g[0] > 1.0 and g[1] < total - 1.0]      # 맨 앞·맨 끝 무음 제외
print(f"챕터 {a.chapter}: 대본 문단 {n}개 → 경계 {n-1}개 필요, 무음 후보 {len(gaps)}개")
if len(gaps) < n - 1:
    sys.exit(f"[오류] 무음 후보가 부족합니다. 문단 사이를 2초 이상 쉬었는지 확인하세요 (--min-gap 을 낮춰도 됩니다).")
pick = sorted(gaps[:n - 1])
if len(gaps) > n - 1:
    d_in = gaps[n - 1][1] - gaps[n - 1][0]; d_out = gaps[n - 2][1] - gaps[n - 2][0]
    print(f"경계 중 가장 짧은 무음 {d_out:.2f}초 / 경계가 아닌 가장 긴 무음 {d_in:.2f}초")
    if d_out - d_in < 0.4:
        print("[경고] 두 값이 비슷합니다. 문단 경계가 잘못 잡혔을 수 있어 결과를 들어 보세요.")
cuts = [0.0] + [(s + e) / 2 for s, e in pick] + [total]
out = ROOT / a.out; out.mkdir(exist_ok=True)
for pi in range(n):
    f = out / voice_name(ci, pi)
    subprocess.run([FF, "-y", "-v", "error", "-ss", f"{cuts[pi]:.3f}", "-to", f"{cuts[pi+1]:.3f}", "-i", a.src,
                    "-vn", "-ac", "1", "-ar", "24000", "-b:a", "96k", str(f)], check=True)
    print(f"  {f.name}: {cuts[pi]:.1f}~{cuts[pi+1]:.1f}초 ({cuts[pi+1]-cuts[pi]:.1f}s)")
