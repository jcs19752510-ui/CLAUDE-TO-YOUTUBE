"""실제 음성 길이에 맞춰 장면을 구성하고 음성을 붙인 영상(초안)을 만든다."""
import json, os, subprocess, sys
from pathlib import Path
ROOT = Path("/home/user/CLAUDE-TO-YOUTUBE/영상제작")
sys.path.insert(0, str(ROOT / "조립"))
from common import parse_paragraphs, voice_name, CHAPTERS, CHAPTER_TITLES, duration, fmt_ts
import re
S = Path("/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad/anim2")
S.mkdir(parents=True, exist_ok=True)
paras = parse_paragraphs(ROOT / "07_읽기용_대본.md")
G = ROOT / "그래픽" / "영상_mp4"
src = {"①":"얼굴:A1|화면녹화:B1·B2","②":"얼굴:A2","③":"얼굴:A3|화면녹화:B3","④":"얼굴:A4|화면녹화:B4·B5","⑤":"얼굴:A5|화면녹화:B6·B7","⑥":"얼굴:A6|화면녹화:B8","⑦":"얼굴:A7|화면녹화:B9","⑧":"얼굴:A8|화면녹화:B10","⑨":"얼굴:A9|화면녹화:B11","⑩":"얼굴:A10"}
src = {k: v.replace("얼굴:A", "").replace("|", "|") for k, v in src.items()}
# 인물 없는 버전: 얼굴 표기는 빼고 화면녹화만 표시
def pills(k):
    m = re.search(r"화면녹화:([^|]+)", {"①":"화면녹화:B1·B2","②":"","③":"화면녹화:B3","④":"화면녹화:B4·B5","⑤":"화면녹화:B6·B7","⑥":"화면녹화:B8","⑦":"화면녹화:B9","⑧":"화면녹화:B10","⑨":"화면녹화:B11","⑩":""}[k])
    return f"화면녹화:{m[1]}" if m else ""
lead = {"①":[], "②":["챕터카드/11_챕터02_통증과약속","챕터카드/12_AI음성고지카드"], "③":["챕터카드/11_챕터03_챗코워크코드"], "④":["챕터카드/11_챕터04_설치와로그인"],
        "⑤":["챕터카드/11_챕터05_첫프로젝트"], "⑥":["챕터카드/11_챕터06_CLAUDEMD"], "⑦":["챕터카드/11_챕터07_플랜모드"], "⑧":["챕터카드/11_챕터08_안전장치"],
        "⑨":["챕터카드/11_챕터09_비용기억"], "⑩":["챕터카드/11_챕터10_마무리"]}
after_para = {("②",3):["02_오늘배울3가지"], ("③",5):["03_챗코워크코드_선택표"], ("④",0):["04_설치3단계"], ("④",4):["05_로그인_폴더신뢰"],
              ("⑧",0):["06_안전장치_키3개"], ("⑧",1):["07_초보실수3가지"], ("⑨",0):["08_비용기억클릭관리"], ("⑩",0):["09_5줄요약"]}
post = {"①":["01_타이틀카드"], "⑩":["10_엔드카드_20초"]}
segs = []   # (kind, value, dur, audio)
chapter_starts = {}
t = 0.0
def gdur(name):
    p = G / f"{name}.mp4"; return p, duration(p)
for ci, ch in enumerate(CHAPTERS):
    chapter_starts[ch] = t
    for g in lead[ch]:
        p, d = gdur(g); segs.append(("gfx", str(p), d, None)); t += d
    for pi, text in enumerate(paras[ch]):
        vf = ROOT / "음성" / voice_name(ci, pi)
        d = duration(vf) + 0.5
        segs.append(("card", dict(tag=f"{ch} {CHAPTER_TITLES[ch]}", tm="", cap=text, src=pills(ch)), d, str(vf), t))
        t += d
        for g in after_para.get((ch, pi), []):
            p, gd = gdur(g); segs.append(("gfx", str(p), gd, None)); t += gd
    for g in post.get(ch, []):
        p, gd = gdur(g); segs.append(("gfx", str(p), gd, None)); t += gd
total = t
# render용 json (kind, value, dur)
json.dump([(s[0], s[1], s[2]) for s in segs], open(S / "segs.json", "w"), ensure_ascii=False)
open(S / "meta.json", "w").write(json.dumps({"n": len(segs)}))
# PNG 렌더 (render.mjs 는 scratchpad/anim 경로를 쓰므로 인자로 경로 전달하는 버전 사용)
r = subprocess.run(["node", str(ROOT / "시안영상/원본/render2.mjs"), str(ROOT / "시안영상/원본"), str(S)], capture_output=True, text=True)
print(r.stdout.strip(), r.stderr.strip()[:300])
# 세그먼트 인코딩 (영상 + 음성)
FF = "ffmpeg"
files = []
VOPT = ["-r", "15", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "30", "-preset", "veryfast"]
AOPT = ["-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "2"]
for i, s in enumerate(segs):
    out = S / f"s{i:03d}.mp4"
    if s[0] == "card":
        cmd = [FF, "-loglevel", "error", "-y", "-loop", "1", "-framerate", "15", "-t", f"{s[2]:.3f}", "-i", str(S / f"c{i:03d}.png"),
               "-i", s[3], "-vf", "format=yuv420p", "-af", "apad", "-t", f"{s[2]:.3f}", "-shortest"] + VOPT + AOPT + [str(out)]
    else:
        cmd = [FF, "-loglevel", "error", "-y", "-i", s[1], "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
               "-vf", "scale=1280:720,fps=15,format=yuv420p", "-t", f"{s[2]:.3f}", "-shortest"] + VOPT + AOPT + [str(out)]
    rr = subprocess.run(cmd, capture_output=True, text=True)
    if rr.returncode: print("실패", i, rr.stderr[-300:]); sys.exit(1)
    files.append(f"file '{out}'")
(S / "list.txt").write_text("\n".join(files))
dst = ROOT / "시안영상" / "클로드코드_사용법_AI음성_초안.mp4"
subprocess.run([FF, "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(S / "list.txt"), "-c", "copy", "-movflags", "+faststart", str(dst)], check=True)
# 챕터 타임라인 / 자막
tl = ["※ 이 초안 영상 기준 시각입니다. 편집 후에는 최종 영상 기준으로 다시 확인하세요.", ""]
for ch in CHAPTERS: tl.append(f"{fmt_ts(chapter_starts[ch])} {CHAPTER_TITLES[ch]}")
(ROOT / "시안영상" / "챕터타임라인_AI음성초안.txt").write_text("\n".join(tl) + "\n", encoding="utf8")
cues, n = [], 1
for s in segs:
    if s[0] != "card": continue
    t0, dur, text = s[4], s[2] - 0.5, s[1]["cap"]
    sents = [x.strip() for x in re.split(r"(?<=[.?!])\s+", text) if x.strip()]
    tot = sum(len(x) for x in sents) or 1; acc = 0
    for x in sents:
        a = t0 + dur * acc / tot; acc += len(x); b = t0 + dur * acc / tot
        cues.append(f"{n}\n{fmt_ts(a, True)} --> {fmt_ts(b, True)}\n{x}\n"); n += 1
(ROOT / "시안영상" / "대사자막_AI음성초안.srt").write_text("\n".join(cues), encoding="utf8")
print(f"완료: {dst.name}  총 {fmt_ts(duration(dst))} ({duration(dst):.0f}초), 예상 {total:.0f}초")
