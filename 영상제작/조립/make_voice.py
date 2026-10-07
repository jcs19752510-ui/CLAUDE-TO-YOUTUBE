#!/usr/bin/env python3
"""AI 음성 만들기 (Gemini TTS, generativelanguage.googleapis.com).

사용법:
    python 조립/make_voice.py --voice Kore              # 전체 문단 음성 생성 → 음성/V01_p00.mp3 ...
    python 조립/make_voice.py --only 6                  # ⑥ 챕터만 생성 (챕터 번호 1~20, 여러 개 가능: --only 11 12 13)
    python 조립/make_voice.py --mode paragraph --only 1 --para 1 --overwrite   # V01_p01 한 문단만 새로 생성
    python 조립/make_voice.py --only 11 12 --dry-run    # API 호출 없이 '무엇을 몇 회 요청할지'만 출력
    python 조립/make_voice.py --voice Charon --overwrite

키 전달 방식 (둘 중 하나):
    1) 클라우드 세션: 환경에 등록한 "네트워크 시크릿"이 요청에 자동으로 붙습니다 (키를 직접 다루지 않음).
    2) 내 PC: 환경 변수 GEMINI_API_KEY 에 키를 넣고 실행. (키를 파일·채팅에 적지 마세요.)

입력: 영상제작/10_AI음성_입력용_대본.md (발음 표기로 바뀐 낭독용 대본)
출력: 영상제작/음성/V{챕터}_p{문단}.mp3   (문단 하나 = 파일 하나)

주의:
  - 무료 단계는 '분당 호출 수'와 '하루 호출 수(모델별·프로젝트별)' 한도가 있습니다. 분당 한도(429)는 자동으로 기다렸다 재시도하지만, 하루 한도는 재시도로 해결되지 않습니다 (다른 모델 사용 / 한도 초기화 대기 / 다른 프로젝트 키 / 유료 전환).
  - 하루 한도(오류 본문에 PerDay/per day/daily)는 재시도 없이 즉시 중단하고 retryDelay를 출력합니다.
  - 챕터 모드는 보관된 옛 원본(음성/_원본/chapter_NN.mp3)을 다시 분리할 수 있습니다. 글이 바뀐 챕터(①②⑩)는 _STALE_RAW 로 막아 둡니다 (--mode paragraph 사용).
  - 말 속도는 파일 후처리(--speed, 기본 0.92배)로 조절합니다. (프롬프트에 속도 지시를 넣으면 지시문이 음성으로 읽힐 수 있어 쓰지 않습니다.)
  - 목소리 품질·무료 한도·상업 이용 약관은 Google 공식 문서에서 직접 확인하세요.
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import CHAPTERS, ROOT, parse_paragraphs, tools, voice_name  # noqa: E402

# 15분본 글로 만든 옛 원본이라 다시 분리하면 수정 전 문장이 되살아나는 챕터 (음성_재생성_목록.md 5장)
_STALE_RAW = {1, 2, 10}

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
            full = e.read().decode("utf8", "ignore")
            msg = full[:300]
            low = full.lower()
            if e.code == 429 and ("perday" in low or "per day" in low or "daily" in low):
                m = re.search(r'"retryDelay":\s*"([^"]+)"', full)
                delay = m[1] if m else "(응답에 retryDelay 없음)"
                raise SystemExit(f"[중단] 하루 한도 초과(429). 재시도하지 않습니다. retryDelay: {delay}\n"
                                 "  다른 모델(--model) / 한도 초기화 대기 / 다른 프로젝트 키 / 유료 전환 중에서 고르세요."
                                 " 이미 만든 파일은 건너뛰고 이어서 만듭니다.")
            if e.code == 400 and "generate text" in msg and attempt < tries - 1:
                print(f"   모델이 음성 대신 글을 만들려 함(400) → 5초 후 재시도 ({attempt + 1}/{tries - 1})")
                time.sleep(5)
                continue
            if e.code in (500, 502, 503, 504) and attempt < tries - 1:
                print(f"   서버 일시 오류({e.code}) → 15초 대기 후 재시도 ({attempt + 1}/{tries - 1})")
                time.sleep(15)
                continue
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


def split_by_silence(src_audio, n, out_paths, speed, chars=None):
    """챕터 하나의 음성을 '쉬는 구간'을 기준으로 문단 n개로 나눈다.
    가장 긴 무음 n-1개를 문단 경계로 사용. 못 찾으면 None."""
    import re as _re
    ffmpeg, _ = tools()
    total = duration_of(src_audio)
    sil = []
    # 엄격한 기준(-38dB, 0.12초)과 느슨한 기준(-30dB, 0.06초)의 쉬는 구간을 함께 후보로 쓴다.
    # 엄격한 기준만 쓰면 문단 안 문장 사이 쉼이 문단 경계로 뽑히고 실제 경계는 놓치는 경우가 있다.
    for noise, dmin in (("-38dB", "0.12"), ("-30dB", "0.06")):
        r = subprocess.run([ffmpeg, "-hide_banner", "-i", str(src_audio), "-af",
                            f"silencedetect=noise={noise}:d={dmin}", "-f", "null", "-"],
                           capture_output=True, text=True)
        starts = [float(x) for x in _re.findall(r"silence_start: ([\d.]+)", r.stderr)]
        ends = [(float(a), float(b)) for a, b in _re.findall(r"silence_end: ([\d.]+) \| silence_duration: ([\d.]+)", r.stderr)]
        for (e, d), s in zip(ends, starts):
            if s > 0.4 and e < total - 0.4:           # 맨 앞·맨 뒤 무음은 제외
                mid = (s + e) / 2
                if not any(abs(mid - (s2 + e2) / 2) < 0.15 for _, s2, e2 in sil):
                    sil.append((d, s, e))
    if n == 1:
        cuts = []
    else:
        if len(sil) < n - 1:
            # 쉬는 구간이 부족하면 글자 수 비율로 위치를 추정해서 자른다 (경고 표시용으로 estimated=True)
            cs = chars or [1] * n
            tc = float(sum(cs))
            acc = 0
            est = []
            for k in range(n - 1):
                acc += cs[k]
                x = total * acc / tc
                est.append((0.0, x, x))
            sil = est
        # 문단 경계 후보 = 무음 구간의 가운데 지점.
        # 한 군데씩 욕심내서 고르면 앞의 실수가 뒤로 번지므로, 전체를 한 번에 최적화(동적 계획법)한다:
        # 각 문단 길이가 '글자 수 비율로 예상한 길이'에 가깝고, 경계가 긴 무음일수록 좋은 조합을 고른다.
        chars = chars or [1] * n
        tot_c = float(sum(chars))
        exp_len = [total * c / tot_c for c in chars]
        cand = sorted(((s + e) / 2, d, s, e) for d, s, e in sil)
        m = len(cand)
        INF = float("inf")
        # dp[k][j] = 경계 k개를 쓰고 마지막 경계가 cand[j]일 때 최소 비용
        dp = [[INF] * m for _ in range(n)]
        back = [[-1] * m for _ in range(n)]
        for j in range(m):
            dp[1][j] = ((cand[j][0] - 0.0 - exp_len[0]) / total) ** 2 * 100 - min(cand[j][1], 1.2) * 0.3
        for k in range(2, n):
            for j in range(m):
                for i in range(j):
                    if dp[k - 1][i] == INF or cand[j][0] <= cand[i][0] + 1.0:
                        continue
                    c = dp[k - 1][i] + ((cand[j][0] - cand[i][0] - exp_len[k - 1]) / total) ** 2 * 100 - min(cand[j][1], 1.2) * 0.3
                    if c < dp[k][j]:
                        dp[k][j], back[k][j] = c, i
        best_j, best_c = -1, INF
        for j in range(m):
            if dp[n - 1][j] == INF:
                continue
            c = dp[n - 1][j] + ((total - cand[j][0] - exp_len[n - 1]) / total) ** 2 * 100
            if c < best_c:
                best_c, best_j = c, j
        if best_j < 0:
            return None
        idx, j = [], best_j
        for k in range(n - 1, 0, -1):
            idx.append(j)
            j = back[k][j]
        idx.reverse()
        cuts = [(cand[j][1], cand[j][2], cand[j][3]) for j in idx]
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


def _ch_hash(plist):
    return hashlib.sha1("\n\n".join(plist).encode("utf8")).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-3.8-flash-lite-tts")
    ap.add_argument("--voice", default="Kore", help="예: Kore, Charon, Aoede, Puck ...")
    ap.add_argument("--speed", type=float, default=0.92, help="말 속도 배율 (1.0=원래, 0.92=조금 느리게)")
    ap.add_argument("--mode", choices=["chapter", "paragraph"], default="chapter",
                    help="chapter: 챕터마다 1회 요청(하루 한도 절약, 기본) / paragraph: 문단마다 요청")
    ap.add_argument("--only", type=int, nargs="+", help="이 챕터 번호(1~20)만 생성. 여러 개 가능")
    ap.add_argument("--para", type=int, nargs="+", help="--only 챕터 안에서 이 문단 번호(0부터)만 처리 (--mode paragraph 전용)")
    ap.add_argument("--gap", type=float, default=12.0, help="요청 사이 대기(초). 무료 한도 보호용")
    ap.add_argument("--overwrite", action="store_true", help="API를 다시 호출해 음성을 새로 만든다")
    ap.add_argument("--resplit", action="store_true", help="보관된 원본 챕터 음성으로 문단만 다시 분리한다 (API 호출 없음)")
    ap.add_argument("--dry-run", action="store_true", help="API·파일 쓰기 없이 계획(방식·요청 수)만 출력")
    ap.add_argument("--script", default=str(ROOT / "10_AI음성_입력용_대본.md"))
    ap.add_argument("--out", default=str(ROOT / "음성"))
    a = ap.parse_args()

    n_ch = len(CHAPTERS)
    for n in a.only or []:
        if not 1 <= n <= n_ch:
            ap.error(f"--only 는 1~{n_ch} 입니다: {n}")
    if a.para:
        if not a.only or len(a.only) != 1:
            ap.error("--para 는 --only 에 챕터 하나를 함께 지정해야 합니다")
        if a.mode != "paragraph":
            ap.error("--para 는 --mode paragraph 에서만 쓸 수 있습니다 (챕터 모드는 챕터 전체를 한 번에 만듭니다)")

    paras = parse_paragraphs(a.script)
    out = Path(a.out)
    dry = a.dry_run
    if not dry:
        out.mkdir(parents=True, exist_ok=True)
    made = skipped = requests = 0
    warn = []
    tag = "[dry-run] " if dry else ""
    for ci, ch in enumerate(CHAPTERS):
        if a.only and (ci + 1) not in a.only:
            continue
        plist = paras.get(ch, [])
        if not plist:
            warn.append(f"{ch}: 대본에서 문단을 찾지 못함")
            continue
        files = [out / voice_name(ci, pi) for pi in range(len(plist))]
        if a.para:
            bad = [x for x in a.para if not 0 <= x < len(plist)]
            if bad:
                raise SystemExit(f"[오류] {ch} 문단 번호 범위는 0~{len(plist) - 1} 입니다: {bad}")
        if not a.overwrite and not a.resplit and all(f.exists() for f in files):
            skipped += len(files)
            print(f"{tag}{ch} 건너뜀: 음성 {len(files)}개 이미 있음")
            continue
        if a.mode == "paragraph":
            for pi, text in enumerate(plist):
                f = files[pi]
                if a.para and pi not in a.para:
                    continue
                if f.exists() and not a.overwrite:
                    skipped += 1
                    continue
                if dry:
                    print(f"{tag}{ch} {f.name} 문단 모드 요청 1회 ({len(text)}자)" + (" [덮어쓰기]" if f.exists() else " [신규]"))
                    made += 1
                    requests += 1
                    continue
                audio, mime = synth(text, a.model, a.voice)
                to_mp3(audio, mime, f, a.speed)
                made += 1
                print(f"생성: {f.name}  ({len(text)}자)")
                time.sleep(a.gap)
            continue
        # 챕터 모드: 문단 사이에 빈 줄을 넣어 한 번에 요청 → 쉬는 구간으로 문단 분리
        raw_dir = out / "_원본"
        whole = raw_dir / f"chapter_{ci + 1:02d}.mp3"
        stamp = raw_dir / f"chapter_{ci + 1:02d}.sha1"
        reuse = whole.exists() and not a.overwrite
        if reuse:
            # 옛 원본이 지금 대본과 다른 글일 수 있으면 재사용하지 않는다 (수정 전 문장이 되살아남)
            if stamp.exists() and stamp.read_text().strip() != _ch_hash(plist):
                warn.append(f"{ch}: 보관 원본이 현재 대본과 다른 글로 만들어짐 → 건너뜀 (--mode paragraph 또는 --overwrite)")
                print(f"[경고] {ch} {whole.name} 은 현재 대본과 글이 달라 쓰지 않습니다. --mode paragraph 로 문단만 다시 만드세요.")
                continue
            if not stamp.exists() and (ci + 1) in _STALE_RAW:
                warn.append(f"{ch}: 보관 원본이 수정 전(15분본) 글 → 건너뜀 (--mode paragraph --only {ci + 1} --para N --overwrite)")
                print(f"[경고] {ch} {whole.name} 은 수정 전 글이라 다시 분리하지 않습니다. --mode paragraph 를 쓰세요.")
                continue
        if dry:
            if reuse:
                print(f"{tag}{ch} 챕터 모드: 보관 원본 재분리, 요청 0회 → 문단 {len(files)}개 파일 덮어씀")
            else:
                print(f"{tag}{ch} 챕터 모드: 요청 1회 → 문단 {len(files)}개 ({sum(len(x) for x in plist)}자)")
                requests += 1
            made += len(files)
            continue
        raw_dir.mkdir(exist_ok=True)
        if reuse:
            print(f"원본 보관본 사용(재요청 없음): {whole.name}")
        else:
            audio, mime = synth("\n\n".join(plist), a.model, a.voice)
            to_mp3(audio, mime, whole, 1.0)       # 분리 전에는 원래 속도로 보관
            stamp.write_text(_ch_hash(plist))
            time.sleep(a.gap)
        res = split_by_silence(whole, len(plist), files, a.speed, [len(x) for x in plist])
        if res is None:
            warn.append(f"{ch} 문단 분리 실패 → 챕터 전체 파일만 저장: {whole.name}")
            print(f"[경고] {ch} 문단 분리 실패. 챕터 파일 {whole.name} 만 저장했습니다.")
        else:
            for pi, f in enumerate(files):
                d = duration_of(f)
                cps = len(plist[pi]) / max(d, 0.1)
                flag = ""
                if cps > 9.0 or cps < 3.5:
                    flag = "  ⚠ 길이 이상(잘림·누락 의심)"
                    warn.append(f"{f.name}: {len(plist[pi])}자 / {d:.1f}초 = {cps:.1f}자/초")
                print(f"생성: {f.name}  ({len(plist[pi])}자, {d:.1f}초, {cps:.1f}자/초){flag}")
            made += len(files)
    if warn:
        print("\n[확인 필요]")
        for w in warn:
            print(" -", w)
    if dry:
        print(f"[dry-run] 새로 만들 문단 {made}개, 건너뜀 {skipped}개, API 요청 {requests}회 (실제 호출 없음)")
    else:
        print(f"완료: 새로 {made}개, 건너뜀 {skipped}개 → {out}")


if __name__ == "__main__":
    main()
