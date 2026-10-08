#!/usr/bin/env python3
"""10_AI음성_입력용_대본.md 에서 '촬영용 낭독문'(얼굴 출연 구간 표시 포함)을 만든다. 직접 고치지 말고 이 스크립트로 다시 만든다."""
import re
from pathlib import Path
R = Path(__file__).resolve().parent
t = (R / "10_AI음성_입력용_대본.md").read_text(encoding="utf-8")
parts = re.split(r"\n## ([①-⑧]) ([^\n]*?)\s*→[^\n]*\n", t)
P = {}
for i in range(1, len(parts), 3):
    P[parts[i]] = (parts[i + 1].strip(), [l.strip() for l in parts[i + 2].split("\n") if l.strip() and not l.startswith(("#", ">"))])
# 얼굴 출연 구간: (챕터, 시작 문단, 끝 문단, 번호, 이름)
FACE = [("①", 0, 1, 1, "오프닝"), ("④", 0, 0, 2, "10분 체크포인트"), ("⑥", 0, 0, 3, "20분 전환"), ("⑧", 2, 3, 4, "엔딩")]
out = ["# 대본 낭독문 · 촬영용", "",
       "- ▶ ■ 로 시작하는 줄은 **표시일 뿐 읽지 않습니다.**",
       "- ▶ 얼굴 촬영 시작 ~ ■ 얼굴 촬영 끝 사이는 **스마트폰 영상으로 촬영**합니다. 시작 전과 끝난 뒤 3초씩 가만히 계십니다.",
       "- 얼굴 구간이 아닌 곳은 음성만 녹음합니다. 문단(빈 줄) 사이는 1초, 챕터 사이는 3초 이상 쉽니다.",
       "- 챕터 제목(① 오프닝 등)은 읽지 않습니다.", "",
       "| 얼굴 구간 | 위치 | 길이(어림) |", "|---|---|---|",
       "| 1. 오프닝 | ① 첫 두 문단 | 약 20초 |", "| 2. 10분 체크포인트 | ④ 첫 문단 | 약 20초 |",
       "| 3. 20분 전환 | ⑥ 첫 문단 | 약 20초 |", "| 4. 엔딩 | ⑧ 마지막 두 문단 | 약 26초 |", "", "---", ""]
for ch, (title, paras) in P.items():
    out.append(f"## {ch} {title}\n")
    for pi, x in enumerate(paras):
        for c, a, b, n, nm in FACE:
            if c == ch and pi == a:
                out.append(f"▶ 얼굴 촬영 {n} 시작 — {nm}\n")
        out.append(x + "\n")
        for c, a, b, n, nm in FACE:
            if c == ch and pi == b:
                out.append(f"■ 얼굴 촬영 {n} 끝\n")
    out.append("")
(R / "대본_낭독문_촬영용.md").write_text("\n".join(out), encoding="utf-8")
print("ok")
