#!/usr/bin/env python3
"""AI 음성 만들기 (Google Cloud Text-to-Speech REST API).

사용법:
    export GOOGLE_TTS_API_KEY=...        # 키는 환경 변수로만 전달 (채팅·파일에 적지 마세요)
    python 조립/make_voice.py --list-voices            # 사용 가능한 한국어 목소리 목록
    python 조립/make_voice.py --voice ko-KR-Neural2-A  # 전체 문단 음성 생성 → 음성/V01_p00.mp3 ...
    python 조립/make_voice.py --only 6                 # ⑥ 챕터만 다시 생성
    python 조립/make_voice.py --overwrite              # 이미 있는 파일도 다시 생성

입력: 영상제작/10_AI음성_입력용_대본.md (발음 표기로 바뀐 낭독용 대본)
출력: 영상제작/음성/V{챕터}_p{문단}.mp3  (문단 하나 = 파일 하나)

※ 이 스크립트는 API 키가 있어야 동작합니다. 목소리 이름·가격·무료 사용량·상업 이용 약관은
   Google Cloud 공식 문서에서 직접 확인하세요.
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHAPTERS, ROOT, parse_paragraphs, voice_name  # noqa: E402

BASE = "https://texttospeech.googleapis.com/v1"


def call(url, body=None, key=None):
    data = json.dumps(body).encode("utf8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf8", "ignore")[:600]
        raise SystemExit(f"[오류] HTTP {e.code}: {detail}")
    except urllib.error.URLError as e:
        raise SystemExit(f"[오류] 접속 실패: {e.reason}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="ko-KR-Neural2-A", help="목소리 이름 (--list-voices로 확인)")
    ap.add_argument("--rate", type=float, default=0.95, help="말 속도 (1.0 = 기본, 왕초보 대상이면 0.9~0.95)")
    ap.add_argument("--only", type=int, help="이 챕터 번호(1~10)만 생성")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--list-voices", action="store_true")
    ap.add_argument("--script", default=str(ROOT / "10_AI음성_입력용_대본.md"))
    ap.add_argument("--out", default=str(ROOT / "음성"))
    a = ap.parse_args()

    key = os.environ.get("GOOGLE_TTS_API_KEY")
    if not key:
        raise SystemExit("[오류] 환경 변수 GOOGLE_TTS_API_KEY 가 없습니다. 키를 환경 변수로 설정한 뒤 다시 실행하세요.")
    q = "?" + urllib.parse.urlencode({"key": key})

    if a.list_voices:
        r = call(f"{BASE}/voices?languageCode=ko-KR&key={urllib.parse.quote(key)}")
        for v in r.get("voices", []):
            print(v["name"], v.get("ssmlGender", ""), v.get("naturalSampleRateHertz", ""))
        return

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
            body = {
                "input": {"text": text},
                "voice": {"languageCode": "ko-KR", "name": a.voice},
                "audioConfig": {"audioEncoding": "MP3", "speakingRate": a.rate, "sampleRateHertz": 24000},
            }
            r = call(f"{BASE}/text:synthesize{q}", body)
            f.write_bytes(base64.b64decode(r["audioContent"]))
            made += 1
            print(f"생성: {f.name}  ({len(text)}자)")
            time.sleep(0.2)   # 서버에 부담을 주지 않도록 잠깐 쉼
    print(f"완료: 새로 {made}개, 건너뜀 {skipped}개 → {out}")


if __name__ == "__main__":
    main()
