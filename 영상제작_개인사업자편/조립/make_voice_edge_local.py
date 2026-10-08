#!/usr/bin/env python3
"""[사장님 PC에서 실행] 무료 임시 음성 만들기 (Microsoft Edge 읽기 서비스, 키 불필요).
이 클라우드 환경에서는 해당 서버에 접속할 수 없어 실행하지 못했습니다. 본인 PC에서만 실행하세요.
※ 비공식 경로라 약관·상업 이용이 불명확합니다 → '확인용 초안 음성'으로만 쓰고, 최종 영상은 Gemini 음성으로 교체하세요.
준비:  pip install edge-tts   (ffmpeg 필요)
실행:  python 조립/make_voice_edge_local.py            # 음성/V01_p00.mp3 … 를 만듦(이미 있는 파일은 건너뜀)
       python 조립/make_voice_edge_local.py --overwrite --voice ko-KR-InJoonNeural
"""
import argparse, asyncio, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHAPTERS, ROOT, parse_paragraphs, voice_name, find_tool
import edge_tts
ap = argparse.ArgumentParser()
ap.add_argument("--voice", default="ko-KR-SunHiNeural"); ap.add_argument("--rate", default="-5%")
ap.add_argument("--overwrite", action="store_true"); ap.add_argument("--out", default=str(ROOT / "음성"))
a = ap.parse_args(); out = Path(a.out); out.mkdir(exist_ok=True)
ff = find_tool("ffmpeg")
async def one(text, f):
    tmp = f.with_suffix(".tmp.mp3")
    await edge_tts.Communicate(text, a.voice, rate=a.rate).save(str(tmp))
    subprocess.run([ff, "-loglevel", "error", "-y", "-i", str(tmp), "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-q:a", "3", str(f)], check=True); tmp.unlink()
async def main():
    paras = parse_paragraphs(str(ROOT / "10_AI음성_입력용_대본.md")); n = 0
    for ci, ch in enumerate(CHAPTERS[:8]):
        for pi, t in enumerate(paras.get(ch, [])):
            f = out / voice_name(ci, pi)
            if f.exists() and not a.overwrite: continue
            await one(t, f); n += 1; print("생성", f.name)
    print("완료", n, "개")
asyncio.run(main())
