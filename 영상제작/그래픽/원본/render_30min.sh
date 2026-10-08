#!/bin/bash
# 30분본 신규·수정 그래픽 렌더링 (도식 + 챕터 카드 ⑩~⑳) → webm → mp4(30fps) + png
# 사용: S=<임시폴더> ./render_30min.sh      (S 미지정 시 아래 기본값)
set -e
D=/home/user/CLAUDE-TO-YOUTUBE/영상제작/그래픽
S=${S:-/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad}
G_IDS=${G_IDS:-title,summary,end,map5,check,three,skillfile,connect,safe,coflow,codeflow}
CH_IDS=${CH_IDS-11_챕터10,11_챕터11,11_챕터12,11_챕터13,11_챕터14,11_챕터15,11_챕터16,11_챕터17,11_챕터18,11_챕터19,11_챕터20}
rm -rf $S/g30 $S/ch30; mkdir -p $S/g30 $S/ch30
node $D/원본/render_new.mjs $D/원본 $S/g30 $G_IDS &
[ -n "$CH_IDS" ] && node $D/원본/render_ch_new.mjs $D/원본 $S/ch30 $CH_IDS &
wait
for f in $S/g30/*.webm; do [ -e "$f" ] || continue; n=$(basename "$f" .webm); ffmpeg -loglevel error -y -ss 0.5 -i "$f" -r 30 -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart -an "$D/영상_mp4/$n.mp4"; done
for f in $S/ch30/*.webm; do [ -e "$f" ] || continue; n=$(basename "$f" .webm); ffmpeg -loglevel error -y -ss 0.5 -i "$f" -r 30 -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart -an "$D/영상_mp4/챕터카드/$n.mp4"; done
cp $S/g30/*.png $D/이미지_png/ 2>/dev/null || true
cp $S/ch30/*.png $D/이미지_png/챕터카드/ 2>/dev/null || true
echo "GRAPHICS_30MIN_DONE"
