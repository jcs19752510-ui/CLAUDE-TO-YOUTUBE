#!/usr/bin/env python3
"""AI 음성 만들기 (Gemini TTS, generativelanguage.googleapis.com).

사용법:
    python 조립/make_voice.py --voice Kore              # 전체 문단 음성 생성 → 음성/V01_p00.mp3 ...
    python 조립/make_voice.py --only 6                  # ⑥ 챕터만 생성
    python 조립/make_voice.py --voice Charon --overwrite

키 전달 방식 (둘 중 하나):
    1) 클라우드 세션: 환경에 등록한 "네트워크 시크릿"이 요청에 자동으로 붙습니다 (키를 직접 다루지 않음).
    2) 내 PC: 환경 변수 GEMINI_API_KEY 에 키를 넣고 실행. (키를 파일·채팅에 적지 마세요.)

입력: 영상제작/10_AI음성_입력용_대본.md (발음 표기로 바뀐 낭독용 대본)
출력: 영상제작/음성/V{챕터}_p{문단}.mp3   (문단 하나 = 파일 하나)

주의:
  - 무료 단계는 '분당 호출 수' 한도가 있어 429 오류가 날 수 있습니다. 이 스크립트는 자동으로 기다렸다 재시도합니다.
  - 말 속도는 파일 후처리(--speed, 기본 0.92배)로 조절합니다. (프롬프트에 속도 지시를 넣으면 지시문이 음성으로 읽힐 수 있어 쓰지 않습니다.)
  - 목소리 품질·무료 한도·상업 이용 약관은 Google 공식 문서에서 직접 확인하세요.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHAPTERS, ROOT, parse_paragraphs, tools, voice_name  # noqa: E402

BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def synth(text, model, voice, tries=6):
    """문장 하나를 음성(WAV 바이트)으로 만든다. 한도(429)에 걸리면 기다렸다 재시도."""
    body = {
        "contents": [{"parts": [{"text": text}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}},
        },
    }
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("GEMINI_API_KEY")
    if key:                                   # 내 PC에서 직접 실행하는 경우
        headers["x-goog-api-key"] = key
    for attempt in range(tries):
        req = urllib.request.Request(f"{BASE}/{model}:generateContent",
                                     data=json.dumps(body).encode("utf8"), headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode("utf8"))
            part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
            return base64.b64decode(part["data"]), part.get("mimeType", "")
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf8", "ignore")[:300]
            if e.code == 429 and attempt < tries - 1:
                wait = 20 * (attempt + 1)
                print(f"   한도 도달 → {wait}초 대기 후 재시도 ({attempt + 1}/{tries - 1})")
                time.sleep(wait)
                continue
            raise SystemExit(f"[오류] HTTP {e.code}: {msg}")
        except (KeyError, IndexError):
            raise SystemExit("[오류] 응답에 음성이 없습니다. 모델 이름·목소리 이름을 확인하세요.")
        except urllib.error.URLError as e:
            raise SystemExit(f"[오류] 접속 실패: {e.reason}")
    raise SystemExit("[오류] 재시도 횟수를 초과했습니다. 잠시 후 다시 실행하세요.")


def to_mp3(wav_bytes, out_path, speed):
    ffmpeg, _ = tools()
    tmp = Path(str(out_path) + ".tmp.wav")
    tmp.write_bytes(wav_bytes)
    cmd = [ffmpeg, "-loglevel", "error", "-y", "-i", str(tmp)]
    if abs(speed - 1.0) > 0.001:
        cmd += ["-af", f"atempo={speed}"]
    cmd += ["-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-q:a", "3", str(out_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    tmp.unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit("[ffmpeg 오류] " + r.stderr[-400:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-3.8-flash-tts")
    ap.add_argument("--voice", default="Kore", help="예: Kore, Charon, Aoede, Puck ...")
    ap.add_argument("--speed", type=float, default=0.92, help="말 속도 배율 (1.0=원래, 0.92=조금 느리게)")
    ap.add_argument("--only", type=int, help="이 챕터 번호(1~10)만 생성")
    ap.add_argument("--gap", type=float, default=12.0, help="요청 사이 대기(초). 무료 한도 보호용")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--script", default=str(ROOT / "10_AI음성_입력용_대본.md"))
    ap.add_argument("--out", default=str(ROOT / "음성"))
    a = ap.parse_args()

    paras = parse_paragraphs(a.script)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    made = skipped = 0
    for ci, ch in enumerate(CHAPTERS):
        if a.only and a.only != ci + 1:
            continue
        for pi, text in enumerate(paras.get(ch, [])):
            f = out / voice_name(ci, pi)
            if f.exists() and not a.overwrite:
                skipped += 1
                continue
            wav, mime = synth(text, a.model, a.voice)
            if "wav" in mime or wav[:4] == b"RIFF":
                to_mp3(wav, f, a.speed)
            else:
                raise SystemExit(f"[오류] 예상하지 못한 음성 형식: {mime}")
            made += 1
            print(f"생성: {f.name}  ({len(text)}자)")
            time.sleep(a.gap)
    print(f"완료: 새로 {made}개, 건너뜀 {skipped}개 → {out}")


if __name__ == "__main__":
    main()
