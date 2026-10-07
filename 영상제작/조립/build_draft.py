"""새 대본(클로드 데스크탑 편) 영상 초안 조립: 실제 음성 길이 + 도식·챕터 카드 + '화면 녹화 자리' 자막 카드.
사용: python 조립/build_draft.py   (음성/V01_p00.mp3 … 가 있어야 함)
"""
import json, re, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "조립"))
from common import parse_paragraphs, voice_name, CHAPTERS, duration, fmt_ts
G = ROOT / "그래픽" / "영상_mp4"
paras = parse_paragraphs(ROOT / "07_읽기용_대본.md")
TITLES = {"①":"하이라이트","②":"통증 + 약속","③":"설치와 로그인","④":"세 개의 탭: 챗·코워크·코드","⑤":"챗(Chat) 써 보기","⑥":"코워크(Cowork) 써 보기",
          "⑦":"코드 탭: 첫 세션 만들기","⑧":"권한 모드와 플랜 모드","⑨":"더 잘 쓰는 방법 5가지","⑩":"요약 + 오늘 할 일"}
SLOT = {"①":"앱 화면 · 완성된 계산기 시연","③":"앱 화면 · 다운로드·설치·로그인","④":"앱 화면 · 세 개의 탭","⑤":"앱 화면 · Chat 시연","⑥":"앱 화면 · Cowork 시연",
        "⑦":"앱 화면 · Code 탭 첫 세션","⑧":"앱 화면 · 권한 모드·Plan","⑨":"앱 화면 · 더 잘 쓰는 5가지"}
LEAD = {"①":[], "②":["챕터카드/11_챕터02_통증과약속","챕터카드/12_AI음성고지카드"], "③":["챕터카드/11_챕터03_설치와로그인"], "④":["챕터카드/11_챕터04_세개의탭"],
        "⑤":["챕터카드/11_챕터05_챗"], "⑥":["챕터카드/11_챕터06_코워크"], "⑦":["챕터카드/11_챕터07_코드탭첫세션"], "⑧":["챕터카드/11_챕터08_권한모드와플랜"],
        "⑨":["챕터카드/11_챕터09_더잘쓰는법"], "⑩":["챕터카드/11_챕터10_마무리","09_5줄요약"]}
AFTER = {("②",2):["02_오늘배울3가지"], ("③",3):["03_설치3단계"], ("③",5):["04_요금제알아두기"], ("④",3):["05_세개의탭_챗코워크코드"],
         ("⑦",4):["06_코드탭첫세션4가지"], ("⑧",5):["07_권한모드5가지"], ("⑨",4):["08_더잘쓰는5가지"]}
POST = {"①":["01_타이틀카드"], "⑩":["10_엔드카드_20초"]}
W, H, FPS = 1280, 720, 15
def gfx(name):
    p = G / f"{name}.mp4"
    if not p.exists(): raise SystemExit(f"그래픽 없음: {p}")
    return p, duration(p)
MISSING = []
segs, starts, t = [], {}, 0.0
for ci, ch in enumerate(CHAPTERS):
    starts[ch] = t
    for g in LEAD[ch]:
        p, d = gfx(g); segs.append(("gfx", str(p), d, None, None)); t += d
    for pi, text in enumerate(paras[ch]):
        vf = ROOT / "음성" / voice_name(ci, pi)
        if vf.exists():
            d = duration(vf) + 0.5
            vpath, vlabel = str(vf), ""
        else:                       # 음성 미생성: 예상 길이(약 7자/초)의 무음으로 대체하고 카드에 표시
            d = len(text) / 7.0 + 0.5
            vpath, vlabel = None, "AI 음성:미생성(예상 길이)"
            MISSING.append(voice_name(ci, pi))
        label = f"화면 녹화 자리:{SLOT[ch]}" if ch in SLOT else ""
        label = "|".join(x for x in (label, vlabel) if x)
        segs.append(("card", dict(tag=f"{ch} {TITLES[ch]}", tm="", cap=text, src=label), d, vpath, t)); t += d
        for g in AFTER.get((ch, pi), []):
            p, gd = gfx(g); segs.append(("gfx", str(p), gd, None, None)); t += gd
    for g in POST.get(ch, []):
        p, gd = gfx(g); segs.append(("gfx", str(p), gd, None, None)); t += gd
S = Path(tempfile.mkdtemp(prefix="draft_"))
json.dump([(s[0], s[1], s[2]) for s in segs], open(S / "segs.json", "w"), ensure_ascii=False)
r = subprocess.run(["node", str(ROOT / "조립/초안카드/render_cards.mjs"), str(ROOT / "조립/초안카드"), str(S)], capture_output=True, text=True)
print(r.stdout.strip(), r.stderr.strip()[:300])
VOPT = ["-r", str(FPS), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "30", "-preset", "veryfast"]
AOPT = ["-c:a", "aac", "-b:a", "96k", "-ar", "44100", "-ac", "2"]
files = []
for i, s in enumerate(segs):
    out = S / f"s{i:03d}.mp4"
    if s[0] == "card":
        ain = ["-i", s[3]] if s[3] else ["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"]
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-framerate", str(FPS), "-t", f"{s[2]:.3f}", "-i", str(S / f"c{i:03d}.png")] + ain + \
              ["-vf", "format=yuv420p", "-af", "apad", "-t", f"{s[2]:.3f}", "-shortest"] + VOPT + AOPT + [str(out)]
    else:
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", s[1], "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
               "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p", "-t", f"{s[2]:.3f}", "-shortest"] + VOPT + AOPT + [str(out)]
    rr = subprocess.run(cmd, capture_output=True, text=True)
    if rr.returncode: print("실패", i, rr.stderr[-300:]); sys.exit(1)
    files.append(f"file '{out}'")
(S / "list.txt").write_text("\n".join(files))
OUT = ROOT / "조립결과"; OUT.mkdir(exist_ok=True)
dst = OUT / "클로드데스크탑_AI음성_초안.mp4"
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(S / "list.txt"), "-c", "copy", "-movflags", "+faststart", str(dst)], check=True)
tl = ["※ 이 초안 영상 기준 시각입니다. 편집 후에는 최종 영상 기준으로 다시 확인하세요.", ""]
for ch in CHAPTERS: tl.append(f"{fmt_ts(starts[ch])} {TITLES[ch]}")
(OUT / "챕터타임라인.txt").write_text("\n".join(tl) + "\n", encoding="utf8")
cues, n = [], 1
for s in segs:
    if s[0] != "card": continue
    t0, dur, text = s[4], s[2] - 0.5, s[1]["cap"]
    sents = [x.strip() for x in re.split(r"(?<=[.?!])\s+", text) if x.strip()]
    tot = sum(len(x) for x in sents) or 1; acc = 0
    for x in sents:
        a = t0 + dur * acc / tot; acc += len(x); b = t0 + dur * acc / tot
        cues.append(f"{n}\n{fmt_ts(a, True)} --> {fmt_ts(b, True)}\n{x}\n"); n += 1
(OUT / "대사자막.srt").write_text("\n".join(cues), encoding="utf8")
print(f"음성 미생성 문단 {len(MISSING)}개: " + (", ".join(MISSING[:6]) + (" ..." if len(MISSING)>6 else "")))
print(f"완료: {dst.name}  총 {fmt_ts(duration(dst))} ({duration(dst):.0f}초)")
