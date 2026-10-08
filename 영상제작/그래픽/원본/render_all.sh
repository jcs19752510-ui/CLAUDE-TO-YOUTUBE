#!/bin/bash
# 새 대본용 도식·챕터 카드 렌더링 → mp4 변환
set -e
D=/home/user/CLAUDE-TO-YOUTUBE/영상제작/그래픽
S=/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad
mkdir -p $S/g3 $S/ch3
node $D/원본/render_new.mjs $D/원본 $S/g3 &
node $D/원본/render_ch_new.mjs $D/원본 $S/ch3 &
wait
for f in $S/g3/*.webm; do n=$(basename "$f" .webm); ffmpeg -loglevel error -y -ss 0.5 -i "$f" -r 30 -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart -an "$D/영상_mp4/$n.mp4"; done
for f in $S/ch3/*.webm; do n=$(basename "$f" .webm); ffmpeg -loglevel error -y -ss 0.5 -i "$f" -r 30 -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart -an "$D/영상_mp4/챕터카드/$n.mp4"; done
cp $S/g3/*.png $D/이미지_png/
cp $S/ch3/*.png $D/이미지_png/챕터카드/
echo "GRAPHICS_DONE"
