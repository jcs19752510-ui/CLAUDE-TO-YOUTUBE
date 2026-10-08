#!/usr/bin/env python3
"""01_메인대본.md 의 🎙 줄만 뽑아 10_AI음성_입력용_대본.md 를 만든다 (낭독 문단 = 한 줄)."""
import re, sys
from pathlib import Path
R = Path(__file__).resolve().parent
t = (R / "01_메인대본.md").read_text(encoding="utf-8")
parts = re.split(r"\n## ([①-⑧]) ([^\n]*)\n", t)
names = "①②③④⑤⑥⑦⑧"
out = ["# AI 음성 입력용 대본 (낭독용) — 개인사업자편 27분본", "",
       "> `01_메인대본.md`의 🎙 줄만 `extract_narration.py` 로 자동 추출한 파일입니다(직접 고치지 마세요). 줄 하나 = 문단 하나. 챕터 번호 = 음성 파일 번호(V01_p00.mp3 …).", ""]
tot = 0
for i in range(1, len(parts), 3):
    n, title, body = parts[i], parts[i + 1], parts[i + 2]
    paras = [l[2:].strip() for l in body.split("\n") if l.startswith("🎙 ")]
    c = sum(len(x) for x in paras); tot += c
    print(n, title.split("(")[0].strip(), len(paras), c, f"{c/5.89/60:.1f}분")
    out.append(f"## {n} {title.split('(')[0].strip()}  →  파일 이름: `V0{names.index(n)+1}_pNN.mp3`\n")
    out += [x + "\n" for x in paras]
print("합계", tot, f"{tot/5.89/60:.1f}분(5.89자/초 기준)")
(R / "10_AI음성_입력용_대본.md").write_text("\n".join(out), encoding="utf-8")
