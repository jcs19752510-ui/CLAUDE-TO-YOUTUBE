#!/usr/bin/env python3
"""대본_낭독문_순수본.md 의 낭독 문단을 ~습니다/~십시오체로 바꿔 다시 쓴다(챕터 제목·표시 줄은 그대로)."""
import re, sys
from pathlib import Path
R = Path(__file__).resolve().parent
sys.path.insert(0, str(R)); from 문체변환 import sents, formal
f = R / "대본_낭독문_순수본.md"
out = []
for l in f.read_text(encoding="utf-8").split("\n"):
    keep = (not l.strip()) or l.startswith(("#", "-", "|", ">", "▶", "■")) or re.match(r"^[①-⑧] ", l)
    out.append(l if keep else " ".join(formal(z) for z in sents(l.strip())))
f.write_text("\n".join(out), encoding="utf-8")
print("ok")
