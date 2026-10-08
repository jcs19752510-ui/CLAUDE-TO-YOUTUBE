"""30분본 영상 초안 조립: 실제 음성 길이 + 도식·챕터 카드 + '화면 녹화 자리' 자막 카드.
사용: python 조립/build_draft.py   (음성/V01_p00.mp3 … 가 있으면 쓰고, 없는 문단은 예상 길이 무음 카드)

재생 순서는 common.PLAY_ORDER:  ① … ⑦(p00~p08) → ⑪ → ⑦(p09) → ⑧ ⑨ ⑫ … ⑳ ⑩
그래픽 매핑은 아래 CHAPTER_GFX 한 곳에서만 고친다. 파일이 없으면 경고만 내고 건너뛴다.
"""
import hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "조립"))
from common import parse_paragraphs, parse_titles, voice_name, CHAPTERS, PLAY_ORDER, duration, fmt_ts

G = ROOT / "그래픽" / "영상_mp4"          # 이름은 이 폴더 기준, 확장자(.mp4) 생략. `*` 와일드카드 가능(여러 개면 이름순으로 모두 사용)

# ───────────────────────── 챕터별 그래픽 설정표 (여기만 고치면 됨) ─────────────────────────
#   lead  : 챕터가 시작될 때 (문단 전) 재생할 그래픽/챕터 카드 목록
#   after : {문단 번호: [그래픽...]}  해당 문단 음성 뒤에 재생
#   over  : {문단 번호: 그래픽} 해당 문단 음성과 동시에 재생(그래픽이 그 문단의 화면이 됨)
#   post  : 챕터 마지막 문단 뒤에 재생
#   slot  : 카드에 표시할 '화면 녹화 자리' 설명 (없으면 표시 안 함)
def _card(n):                            # 새 챕터 카드: 그래픽/영상_mp4/챕터카드/11_챕터NN_*.mp4 (다른 작업자가 추가 중)
    return [f"챕터카드/11_챕터{n:02d}_*"]

CHAPTER_GFX = {
    "①": dict(lead=[], after={}, post=["01_타이틀카드"], slot="앱 화면 · 완성된 계산기 시연"),
    "②": dict(lead=["챕터카드/11_챕터02_통증과약속", "챕터카드/12_AI음성고지카드"], after={2: ["02_오늘배울5가지"]}, post=[], slot=""),
    "③": dict(lead=["챕터카드/11_챕터03_설치와로그인"], after={3: ["03_설치3단계"], 5: ["04_요금제알아두기"]}, post=[], slot="앱 화면 · 다운로드·설치·로그인"),
    "④": dict(lead=["챕터카드/11_챕터04_세개의탭"], after={3: ["05_세개의탭_챗코워크코드"]}, post=[], slot="앱 화면 · 세 개의 탭"),
    "⑤": dict(lead=["챕터카드/11_챕터05_챗"], after={}, post=[], slot="앱 화면 · Chat 시연"),
    "⑥": dict(lead=["챕터카드/11_챕터06_코워크"], after={}, post=[], slot="앱 화면 · Cowork 시연"),
    "⑦": dict(lead=["챕터카드/11_챕터07_코드탭첫세션"], after={4: ["06_코드탭첫세션4가지"]}, post=[], slot="앱 화면 · Code 탭 첫 세션"),
    "⑧": dict(lead=["챕터카드/11_챕터08_권한모드와플랜"], after={5: ["07_권한모드5가지"]}, post=[], slot="앱 화면 · 권한 모드·Plan"),
    "⑨": dict(lead=["챕터카드/11_챕터09_더잘쓰는법"], after={4: ["08_더잘쓰는5가지"]}, post=[], slot="앱 화면 · 더 잘 쓰는 5가지"),
    "⑩": dict(lead=["챕터카드/11_챕터10_마무리"], after={}, post=["10_엔드카드_20초"], slot=""),
    # ── 새 챕터 ⑪~⑳: 카드는 파일명 규칙으로 자동 탐색. 새 다이어그램은 챕터 끝(post)에 둠 — 문단 위치를 바꾸려면 after={문단번호: [...]} 로 옮긴다.
    "⑪": dict(lead=_card(11), after={}, post=["13_체크포인트10분"], slot=""),
    "⑫": dict(lead=_card(12), after={}, post=["14_스킬커넥터플러그인구분"], slot="앱 화면 · 스킬·커넥터·플러그인 위치"),
    "⑬": dict(lead=_card(13), after={}, post=[], slot="앱 화면 · 슬래시(/) 스킬 실행"),
    "⑭": dict(lead=_card(14), after={}, post=["15_스킬파일구조"], slot="앱 화면 · 내 스킬 만들기"),
    "⑮": dict(lead=_card(15), after={}, post=["16_커넥터연결순서"], slot="앱 화면 · 커넥터 연결"),
    "⑯": dict(lead=_card(16), after={}, post=[], slot="앱 화면 · 커넥터로 일 시키기"),
    "⑰": dict(lead=_card(17), after={}, post=[], slot="앱 화면 · 플러그인"),
    "⑱": dict(lead=_card(18), after={}, post=["17_안전수칙5가지"], slot=""),
    "⑲": dict(lead=_card(19), after={}, post=["18_실전1_코워크흐름"], slot="앱 화면 · 코워크 실전"),
    "⑳": dict(lead=_card(20), after={8: ["19_실전2_코드탭4단계"]}, over={9: "09_5줄요약"}, post=[], slot="앱 화면 · Code 탭 계산기 완성"),   # p08=네 단계 낭독 뒤 / p09=5줄 요약 낭독과 동시에(over) 재생
}

# 옛(수정 전) 글로 만든 음성: 파일 내용(sha1)이 아래와 같으면 아직 재생성 전이므로 쓰지 않고 무음 카드로 대신한다.
STALE_SHA1 = {
    "V01_p01.mp3": "894d4be33a0186d8d3182162d9c5f4daf2aaf94b",
    "V02_p02.mp3": "2b07fb92157b49a446c090f1adf4392758046138",
    "V10_p01.mp3": "81bb0c98a5a93132100c07168b5751e09111cadf",
}
EST_CPS = 7.4      # 음성 미생성 문단 예상 길이: 글자 수 / 7.4자초 (atempo 0.92 적용 후 실측: 기존 음성 45개 평균 약 7.6자/초)
PAD = 0.5          # 문단 끝 여유(초)
W, H, FPS = 1280, 720, 15
# ───────────────────────────────────────────────────────────────────────────────────────────

WARN = []
titles = parse_titles(ROOT / "10_AI음성_입력용_대본.md")
paras = parse_paragraphs(ROOT / "07_읽기용_대본.md")        # 자막 카드에 쓰는 읽기용 글
spoken = parse_paragraphs(ROOT / "10_AI음성_입력용_대본.md")  # 음성으로 읽는 글(예상 길이 계산용)
for ch in CHAPTERS:
    if len(paras.get(ch, [])) != len(spoken.get(ch, [])) or not paras.get(ch):
        raise SystemExit(f"[오류] {ch} 문단 수가 읽기용({len(paras.get(ch, []))})과 음성용({len(spoken.get(ch, []))}) 대본에서 다릅니다")


def gfx(names):
    """설정표의 이름들 → [(경로, 길이)]. 없으면 경고만."""
    out = []
    for n in names:
        hits = sorted(G.glob(n + ".mp4")) if "*" in n else ([G / f"{n}.mp4"] if (G / f"{n}.mp4").exists() else [])
        if not hits:
            WARN.append(f"그래픽 없음(건너뜀): {n}.mp4")
            continue
        for p in hits:
            out.append((p, duration(p)))
    return out


segs, starts, t = [], {}, 0.0
MISSING, STALE = [], []
def add_gfx(names):
    global t
    for p, d in gfx(names):
        segs.append(("gfx", str(p), d, None, None)); t += d

for ch, p0, p1 in PLAY_ORDER:
    ci = CHAPTERS.index(ch)
    cfg = CHAPTER_GFX[ch]
    plist = paras[ch]
    last = len(plist) - 1 if p1 is None else p1
    if p0 == 0:
        starts[ch] = t
        add_gfx(cfg["lead"])
    for pi in range(p0, last + 1):
        text = plist[pi]
        name = voice_name(ci, pi)
        vf = ROOT / "음성" / name
        vpath = vlabel = None
        if vf.exists() and name in STALE_SHA1 and hashlib.sha1(vf.read_bytes()).hexdigest() == STALE_SHA1[name]:
            STALE.append(name)                           # 수정 전 글의 음성 → 쓰지 않음
            vlabel = "AI 음성:재생성 필요(수정 전 음성, 예상 길이)"
        elif vf.exists():
            d = duration(vf) + PAD
            vpath, vlabel = str(vf), ""
        else:
            vlabel = "AI 음성:미생성(예상 길이)"
            MISSING.append(name)
        if vpath is None:
            d = len(spoken[ch][pi]) / EST_CPS + PAD
        ov = cfg.get("over", {}).get(pi)
        if ov and vpath:                                 # 그래픽을 문단 음성과 함께 재생
            gl = gfx([ov])
            if gl:
                dg = max(gl[0][1], d)
                segs.append(("gfxa", str(gl[0][0]), dg, vpath, t, text)); t += dg
                continue
        label = f"화면 녹화 자리:{cfg['slot']}" if cfg["slot"] else ""
        label = "|".join(x for x in (label, vlabel) if x)
        segs.append(("card", dict(tag=f"{ch} {titles[ch]}", tm="", cap=text, src=label), d, vpath, t)); t += d
        add_gfx(cfg["after"].get(pi, []))
    if p1 is None:
        add_gfx(cfg["post"])

if "--plan" in sys.argv:                  # 인코딩 없이 배치·경고·타임라인만 확인
    for ch, p0, _ in PLAY_ORDER:
        if p0 == 0: print(f"{fmt_ts(starts[ch])} {titles[ch]}")
    print(f"세그먼트 {len(segs)}개, 예상 총 {fmt_ts(t)} ({t:.0f}초), 음성 미생성 {len(MISSING)}개, 수정 전 음성 제외 {STALE}")
    for w in sorted(set(WARN)): print("[경고]", w)
    sys.exit(0)
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
    elif s[0] == "gfxa":
        cmd = ["ffmpeg", "-loglevel", "error", "-y", "-i", s[1], "-i", s[3],
               "-vf", f"scale={W}:{H},fps={FPS},format=yuv420p,tpad=stop_mode=clone:stop_duration=3", "-af", "apad",
               "-t", f"{s[2]:.3f}"] + VOPT + AOPT + [str(out)]
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
for ch, p0, _ in PLAY_ORDER:
    if p0 == 0: tl.append(f"{fmt_ts(starts[ch])} {titles[ch]}")      # ⑦ 뒷부분(p09)은 새 챕터 줄을 만들지 않음
(OUT / "챕터타임라인.txt").write_text("\n".join(tl) + "\n", encoding="utf8")
cues, n = [], 1
for s in segs:
    if s[0] not in ("card", "gfxa"): continue
    t0, dur = s[4], s[2] - PAD
    text = s[1]["cap"] if s[0] == "card" else s[5]
    sents = [x.strip() for x in re.split(r"(?<=[.?!])\s+", text) if x.strip()]
    tot = sum(len(x) for x in sents) or 1; acc = 0
    for x in sents:
        a = t0 + dur * acc / tot; acc += len(x); b = t0 + dur * acc / tot
        cues.append(f"{n}\n{fmt_ts(a, True)} --> {fmt_ts(b, True)}\n{x}\n"); n += 1
(OUT / "대사자막.srt").write_text("\n".join(cues), encoding="utf8")
est = sum(s[2] for s in segs if s[0] == "card" and s[3] is None)
print(f"음성 미생성 문단 {len(MISSING)}개, 수정 전 음성이라 제외 {len(STALE)}개 {STALE} (무음 구간 합 {est:.0f}초 = {fmt_ts(est)})")
for w in sorted(set(WARN)): print("[경고]", w)
print(f"완료: {dst.name}  총 {fmt_ts(duration(dst))} ({duration(dst):.0f}초)")
