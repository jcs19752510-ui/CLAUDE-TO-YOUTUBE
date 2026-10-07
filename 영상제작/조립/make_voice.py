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
  - 무료 단계는 '분당 호출 수'와 '하루 호출 수(모델별·프로젝트별)' 한도가 있습니다. 분당 한도(429)는 자동으로 기다렸다 재시도하지만, 하루 한도는 재시도로 해결되지 않습니다 (다른 모델 사용 / 한도 초기화 대기 / 다른 프로젝트 키 / 유료 전환).
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
            if e.code == 429 and "PerDay" in msg:
                raise SystemExit("[중단] 이 모델의 하루 무료 한도를 모두 썼습니다. 다른 모델(--model)을 쓰거나, 한도가 풀린 뒤"
                                 " 다시 실행하세요. (이미 만든 파일은 건너뛰고 이어서 만듭니다)")
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


def split_by_silence(src_audio, n, out_paths, speed):
    """챕터 하나의 음성을 '쉬는 구간'을 기준으로 문단 n개로 나눈다.
    가장 긴 무음 n-1개를 문단 경계로 사용. 못 찾으면 None."""
    import re as _re
    ffmpeg, _ = tools()
    total = duration_of(src_audio)
    r = subprocess.run([ffmpeg, "-hide_banner", "-i", str(src_audio), "-af",
                        "silencedetect=noise=-38dB:d=0.28", "-f", "null", "-"],
                       capture_output=True, text=True)
    starts = [float(x) for x in _re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [(float(a), float(b)) for a, b in _re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", r.stderr)]
    sil = []
    for (e, d), s in zip(ends, starts):
        if s > 0.4 and e < total - 0.4:           # 맨 앞·맨 뒤 무음은 제외
            sil.append((d, s, e))
    if n == 1:
        cuts = []
    else:
        if len(sil) < n - 1:
            return None
        cuts = sorted(sorted(sil, reverse=True)[: n - 1], key=lambda x: x[1])
    bounds = [0.0] + [(s + e) / 2 for _, s, e in cuts] + [total]
    for i, out in enumerate(out_paths):
        tmp = Path(str(out) + ".tmp.wav")
        # 1) 구간을 WAV로 먼저 자른다 (mp3에서 바로 다듬으면 무음 제거가 적용되지 않는 경우가 있음)
        rr = subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", str(src_audio),
                             "-ss", f"{bounds[i]:.3f}", "-to", f"{bounds[i + 1]:.3f}",
                             "-ar", "44100", "-ac", "1", str(tmp)], capture_output=True, text=True)
        # 2) 앞뒤 무음만 다듬고(문단 안의 쉼은 그대로), 속도 조절 후 mp3로 저장
        flt = ("silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
               "silenceremove=start_periods=1:start_threshold=-45dB,areverse")
        if abs(speed - 1.0) > 0.001:
            flt += f",atempo={speed}"
        if rr.returncode == 0:
            rr = subprocess.run([ffmpeg, "-loglevel", "error", "-y", "-i", str(tmp), "-af", flt,
                                 "-c:a", "libmp3lame", "-q:a", "3", str(out)], capture_output=True, text=True)
        tmp.unlink(missing_ok=True)
        if rr.returncode != 0:
            raise SystemExit("[ffmpeg 오류] " + rr.stderr[-400:])
    return bounds


def duration_of(path):
    from common import duration
    return duration(path)


def to_mp3(audio, mime, out_path, speed):
    """WAV 또는 원시 PCM(L16) 음성을 mp3로 변환. 말 속도는 atempo로 조절."""
    ffmpeg, _ = tools()
    import re as _re
    if audio[:4] == b"RIFF":                      # 이미 WAV
        tmp = Path(str(out_path) + ".tmp.wav")
        pre = []
    else:                                         # 원시 PCM (예: audio/L16;rate=24000)
        m = _re.search(r"rate=(\d+)", mime or "")
        rate = m[1] if m else "24000"
        tmp = Path(str(out_path) + ".tmp.pcm")
        pre = ["-f", "s16le", "-ar", rate, "-ac", "1"]
    tmp.write_bytes(audio)
    cmd = [ffmpeg, "-loglevel", "error", "-y"] + pre + ["-i", str(tmp)]
    if abs(speed - 1.0) > 0.001:
        cmd += ["-af", f"atempo={speed}"]
    cmd += ["-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-q:a", "3", str(out_path)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    tmp.unlink(missing_ok=True)
    if r.returncode != 0:
        raise SystemExit("[ffmpeg 오류] " + r.stderr[-400:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-3.8-flash-lite-tts")
    ap.add_argument("--voice", default="Kore", help="예: Kore, Charon, Aoede, Puck ...")
    ap.add_argument("--speed", type=float, default=0.92, help="말 속도 배율 (1.0=원래, 0.92=조금 느리게)")
    ap.add_argument("--mode", choices=["chapter", "paragraph"], default="chapter",
                    help="chapter: 챕터마다 1회 요청(하루 한도 절약, 기본) / paragraph: 문단마다 요청")
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
    warn = []
    for ci, ch in enumerate(CHAPTERS):
        if a.only and a.only != ci + 1:
            continue
        plist = paras.get(ch, [])
        files = [out / voice_name(ci, pi) for pi in range(len(plist))]
        if not a.overwrite and all(f.exists() for f in files):
            skipped += len(files)
            continue
        if a.mode == "paragraph":
            for pi, text in enumerate(plist):
                f = files[pi]
                if f.exists() and not a.overwrite:
                    skipped += 1
                    continue
                audio, mime = synth(text, a.model, a.voice)
                to_mp3(audio, mime, f, a.speed)
                made += 1
                print(f"생성: {f.name}  ({len(text)}자)")
                time.sleep(a.gap)
            continue
        # 챕터 모드: 문단 사이에 빈 줄을 넣어 한 번에 요청 → 쉬는 구간으로 문단 분리
        audio, mime = synth("\n\n".join(plist), a.model, a.voice)
        whole = out / f"_chapter_{ci + 1:02d}.mp3"
        to_mp3(audio, mime, whole, 1.0)           # 분리 전에는 원래 속도 유지
        res = split_by_silence(whole, len(plist), files, a.speed)
        if res is None:
            warn.append(f"{ch} 문단 분리 실패 → 챕터 전체 파일만 저장: {whole.name}")
            print(f"[경고] {ch} 문단 분리 실패. 챕터 파일 {whole.name} 만 저장했습니다.")
        else:
            whole.unlink(missing_ok=True)
            for pi, f in enumerate(files):
                d = duration_of(f)
                cps = len(plist[pi]) / max(d, 0.1)
                flag = ""
                if cps > 9.0 or cps < 3.5:
                    flag = "  ⚠ 길이 이상(잘림·누락 의심)"
                    warn.append(f"{f.name}: {len(plist[pi])}자 / {d:.1f}초 = {cps:.1f}자/초")
                print(f"생성: {f.name}  ({len(plist[pi])}자, {d:.1f}초, {cps:.1f}자/초){flag}")
            made += len(files)
        time.sleep(a.gap)
    if warn:
        print("\n[확인 필요]")
        for w in warn:
            print(" -", w)
    print(f"완료: 새로 {made}개, 건너뜀 {skipped}개 → {out}")


if __name__ == "__main__":
    main()
