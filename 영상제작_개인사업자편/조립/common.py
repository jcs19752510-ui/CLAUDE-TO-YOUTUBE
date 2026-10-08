"""공통 함수: 대본 문단 읽기, ffmpeg 찾기, 길이 측정."""
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # 영상제작_개인사업자편/
CHAPTERS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧"]     # 챕터 번호 = 음성 파일 번호 = 재생 순서
# 재생 순서. 항목 = (챕터, 시작 문단 번호, 끝 문단 번호(포함); None=끝까지)
PLAY_ORDER = [(ch, 0, None) for ch in CHAPTERS]
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
    """대본(.md)에서 챕터(①~⑧)별 문단 목록을 읽는다. 첫 `---`(머리말)와 챕터 사이 `---`는 문단을 끊는다."""
    out, cur = {}, None
    for line in Path(path).read_text(encoding="utf8").split("\n"):
        m = re.match(r"## ([①-⑧])", line)
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
    """대본 `## ② 제목  →  파일 이름: ...` 줄에서 챕터 제목을 읽는다."""
    out = {}
    for line in Path(path).read_text(encoding="utf8").split("\n"):
        m = re.match(r"## ([①-⑧])\s+(.*?)\s*(?:→.*)?$", line)
        if m:
            out[m[1]] = m[2].strip()
    return out


def voice_name(ch_index, p_index):
    """음성 파일 이름 규칙: V01_p00.mp3 (챕터 1~8, 문단 0부터)."""
    return f"V{ch_index + 1:02d}_p{p_index:02d}.mp3"


def fmt_ts(sec, srt=False):
    sec = max(0.0, sec)
    ms = int(round((sec - int(sec)) * 1000))
    s = int(sec)
    if srt:
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d},{ms:03d}"
    return f"{s // 60}:{s % 60:02d}"


# ---------------------------------------------------------------- 카드 그림(Pillow)
FONTS = Path(__file__).resolve().parent / "fonts"
BG, ORANGE, YELLOW, WHITE = "#0f1422", "#ff7a3d", "#ffd23f", "#ffffff"


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


def render_card(path, W, H, tag, caption, label=None, overlay=False):
    """자막 카드 PNG. overlay=True 면 배경 영상 위에 얹을 투명 PNG(하단 자막 띠)로 만든다."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA" if overlay else "RGB", (W, H), (0, 0, 0, 0) if overlay else BG)
    d = ImageDraw.Draw(img)
    f_tag = ImageFont.truetype(str(FONTS / "BlackHanSans-Regular.ttf"), int(H * 0.05))
    if overlay:
        d.rounded_rectangle([int(W * 0.02), int(H * 0.03), int(W * 0.02) + d.textlength(tag, font=f_tag) + 36,
                             int(H * 0.03) + int(H * 0.08)], radius=16, fill=(0, 0, 0, 150))
    d.text((int(W * 0.03), int(H * 0.04)), tag, font=f_tag, fill=ORANGE)
    box_w = int(W * (0.92 if overlay else 0.84))
    box_h = int(H * (0.19 if overlay else 0.56))
    size = int(H * (0.045 if overlay else 0.085))
    while True:
        font = ImageFont.truetype(str(FONTS / "NotoSansKR-Black.ttf"), size)
        lines = _wrap(caption, font, box_w, d)
        if len(lines) * size * 1.4 <= box_h or size <= int(H * 0.03):
            break
        size -= 2
    th = int(len(lines) * size * 1.4)
    y = int(H * 0.97 - th) if overlay else int(H * 0.5 - th / 2)
    if overlay:
        d.rectangle([0, y - 16, W, H], fill=(0, 0, 0, 150))
    for ln in lines:
        w = d.textlength(ln, font=font)
        d.text(((W - w) / 2, y), ln, font=font, fill=WHITE)
        y += int(size * 1.4)
    if label:
        f_l = ImageFont.truetype(str(FONTS / "NotoSansKR-Bold.ttf"), int(H * 0.034))
        tw = d.textlength(label, font=f_l)
        x0, y0 = int(W * 0.03), int(H * 0.9) if not overlay else int(H * 0.12)
        d.rounded_rectangle([x0, y0, x0 + tw + 40, y0 + int(H * 0.065)], radius=24, fill=(0, 0, 0, 170) if overlay else "#1c2236")
        d.text((x0 + 20, y0 + int(H * 0.012)), label, font=f_l, fill=YELLOW)
    img.save(path)
