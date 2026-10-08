"""공통 함수: 대본 문단 읽기, ffmpeg 찾기, 길이 측정."""
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # 영상제작/
CHAPTERS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩",
            "⑪", "⑫", "⑬", "⑭", "⑮", "⑯", "⑰", "⑱", "⑲", "⑳"]     # 챕터 번호 = 음성 파일 번호 (재생 순서와 다름)
# 30분본 영상 재생 순서. ⑦은 p00~p08 / p09 로 갈라지고 사이에 ⑪이 들어간다. ⑩은 맨 끝.
# 항목 = (챕터, 시작 문단 번호, 끝 문단 번호(포함); None=끝까지)
PLAY_ORDER = [("①", 0, None), ("②", 0, None), ("③", 0, None), ("④", 0, None), ("⑤", 0, None),
              ("⑥", 0, None), ("⑦", 0, 8), ("⑪", 0, None), ("⑦", 9, None), ("⑧", 0, None),
              ("⑨", 0, None), ("⑫", 0, None), ("⑬", 0, None), ("⑭", 0, None), ("⑮", 0, None),
              ("⑯", 0, None), ("⑰", 0, None), ("⑱", 0, None), ("⑲", 0, None), ("⑳", 0, None),
              ("⑩", 0, None)]
CHAPTER_TITLES = {   # 구형 assemble.py 가 쓰는 값(15분본 이전 구성, 그대로 둠). 30분본 제목은 parse_titles() 사용
    "①": "하이라이트", "②": "통증 + 약속", "③": "챗·코워크·코드 선택표", "④": "설치와 로그인",
    "⑤": "첫 프로젝트", "⑥": "CLAUDE.md (업무 지침서)", "⑦": "플랜 모드",
    "⑧": "안전장치 + 초보 실수 3가지", "⑨": "비용·기억 관리", "⑩": "요약 + 오늘 할 일",
}
CHARS_PER_SEC = 4.8   # 음성 길이 어림값(글자 수 기준)


def find_tool(name):
    p = shutil.which(name)
    if p:
        return p
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if name == "ffmpeg":
            return exe
    except Exception:
        pass
    raise SystemExit(f"[오류] {name} 을(를) 찾을 수 없습니다. ffmpeg를 설치하세요 (https://ffmpeg.org).")


FFMPEG = None
FFPROBE = None


def tools():
    global FFMPEG, FFPROBE
    if FFMPEG is None:
        FFMPEG = find_tool("ffmpeg")
        try:
            FFPROBE = find_tool("ffprobe")
        except SystemExit:
            FFPROBE = None
    return FFMPEG, FFPROBE


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("[ffmpeg 오류]\n" + " ".join(map(str, cmd[:6])) + " ...\n" + r.stderr[-1500:])
    return r


def duration(path):
    """미디어 파일 길이(초)."""
    ffmpeg, ffprobe = tools()
    if ffprobe:
        r = subprocess.run([ffprobe, "-v", "error", "-show_entries", "format=duration",
                            "-of", "csv=p=0", str(path)], capture_output=True, text=True)
        try:
            return float(r.stdout.strip())
        except ValueError:
            pass
    r = subprocess.run([ffmpeg, "-i", str(path)], capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr)
    if not m:
        raise SystemExit(f"[오류] 길이를 읽을 수 없습니다: {path}")
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3])


def parse_paragraphs(path):
    """대본(.md)에서 챕터(①~⑳)별 문단 목록을 읽는다. 첫 `---`(머리말)와 챕터 사이 `---`는 문단을 끊는다."""
    out, cur = {}, None
    for line in Path(path).read_text(encoding="utf8").split("\n"):
        m = re.match(r"## ([①-⑳])", line)
        if m:
            cur = m[1]
            out[cur] = []
            continue
        if line.startswith("---") or line.startswith("총 약"):
            cur = None
            continue
        if cur and line.strip() and not line.startswith(("#", ">")):
            out[cur].append(line.strip())
    return out


def parse_titles(path):
    """대본 `## ⑪ 제목  →  파일 이름: ...` 줄에서 챕터 제목을 읽는다."""
    out = {}
    for line in Path(path).read_text(encoding="utf8").split("\n"):
        m = re.match(r"## ([①-⑳])\s+(.*?)\s*(?:→.*)?$", line)
        if m:
            out[m[1]] = m[2].strip()
    return out


def voice_name(ch_index, p_index):
    """음성 파일 이름 규칙: V01_p00.mp3 (챕터 1~20, 문단 0부터)."""
    return f"V{ch_index + 1:02d}_p{p_index:02d}.mp3"


def fmt_ts(sec, srt=False):
    sec = max(0.0, sec)
    ms = int(round((sec - int(sec)) * 1000))
    s = int(sec)
    if srt:
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d},{ms:03d}"
    return f"{s // 60}:{s % 60:02d}"
