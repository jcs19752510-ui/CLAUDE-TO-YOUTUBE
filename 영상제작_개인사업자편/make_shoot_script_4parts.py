#!/usr/bin/env python3
"""10_AI음성_입력용_대본.md 에서 '4파트 촬영 대본'(2챕터씩 동영상 1개)을 만든다. 직접 고치지 말고 이 스크립트로 다시 만든다."""
import re
from pathlib import Path
R = Path(__file__).resolve().parent
t = (R / "10_AI음성_입력용_대본.md").read_text(encoding="utf-8")
parts = re.split(r"\n## ([①-⑧]) ([^\n]*?)\s*→[^\n]*\n", t)
P = {}
for i in range(1, len(parts), 3):
    P[parts[i]] = (parts[i + 1].strip(), [l.strip() for l in parts[i + 2].split("\n") if l.strip() and not l.startswith(("#", ">"))])
FACE = {("①", 0): "▶ 얼굴 구간 시작 (오프닝)", ("④", 0): "▶ 얼굴 구간 시작 (10분 체크포인트)",
        ("⑥", 0): "▶ 얼굴 구간 시작 (20분 전환)", ("⑧", 2): "▶ 얼굴 구간 시작 (엔딩)"}
FACE_END = {("①", 1), ("④", 0), ("⑥", 0), ("⑧", 3)}
GROUPS = [("①", "②"), ("③", "④"), ("⑤", "⑥"), ("⑦", "⑧")]
CPS = 7.4  # 글자/초 (기존 초안과 같은 어림값)
def sents(p): return re.split(r"(?<=[.?!])\s+", p)
def secs(chs): return sum(len(x.replace(" ", "")) for c in chs for x in P[c][1]) / CPS * 1.15
o = ["# 촬영 대본 · 4파트 (동영상 4개)", "",
     "**읽는 법 4가지**", "",
     "1. 큰 글씨 줄만 읽습니다. `🔴` `⏸` `▶` `■` 가 붙은 줄은 **읽지 않는 표시**입니다.",
     "2. 한 줄이 한 문장입니다. 줄이 바뀌면 숨을 한 번 쉬세요.",
     "3. **문단 사이 = 2초 쉬기 (⏸).** 속으로 \"하나, 둘\" 세고 다음 문단을 읽습니다.",
     "4. **챕터 사이 = 30초 쉬기 (⏸⏸).** 가만히 앉아 물 한 모금 마시고 쉬세요. 편집할 때 이 긴 공백으로 챕터를 나눕니다.", "",
     "**틀렸을 때**: 그 문단을 **처음부터** 다시 읽으세요. 문단 중간에서 다시 시작하면 편집에서 경계를 못 찾습니다. 고쳐 읽기 전에 2초 쉬면 됩니다.", "",
     "| 파트 | 파일 이름(저장) | 챕터 | 읽는 시간(어림) |", "|---|---|---|---|"]
for n, (a, b) in enumerate(GROUPS, 1):
    o.append(f"| {n} | `촬영_파트{n}_{a}{b}.mp4` | {a} {P[a][0]} + {b} {P[b][0]} | 약 {secs((a, b)) / 60:.0f}분 |")
o += ["", "읽는 시간은 글자 수로 계산한 어림값입니다(실제 낭독 속도에 따라 ±20%).", "", "---", ""]
for n, (a, b) in enumerate(GROUPS, 1):
    o += [f"# 🎬 파트 {n} / 4 — {a} {P[a][0]} + {b} {P[b][0]}", "",
          f"> 저장 이름: **촬영_파트{n}_{a}{b}.mp4** · 약 {secs((a, b)) / 60:.0f}분", "",
          "🔴 **녹화 시작 → 3초 가만히 → 읽기 시작**", "", "---", ""]
    for ci, ch in enumerate((a, b)):
        title, paras = P[ch]
        o += [f"## ━━━ {ch} {title} ━━━", "", f"*(제목은 읽지 않습니다 · 문단 {len(paras)}개)*", ""]
        for pi, x in enumerate(paras):
            if (ch, pi) in FACE: o += [f"**{FACE[(ch, pi)]}** — 카메라를 보고 읽기", ""]
            o += [f"**[{ch}-{pi + 1}]**", ""]
            o += [f"### {s}\n" for s in sents(x)]
            if (ch, pi) in FACE_END: o += ["**■ 얼굴 구간 끝**", ""]
            if pi < len(paras) - 1: o += ["⏸ **2초 쉬기**", ""]
        if ci == 0: o += ["", "⏸⏸ **30초 쉬기 — 가만히 앉아 있기 (다음 챕터 준비)**", ""]
    o += ["", "⏸ **마지막 말 뒤 3초 가만히 → 🔴 녹화 끝**", "", "---", ""]
(R / "대본_촬영_4파트.md").write_text("\n".join(o), encoding="utf-8")
print("ok", len(o))
