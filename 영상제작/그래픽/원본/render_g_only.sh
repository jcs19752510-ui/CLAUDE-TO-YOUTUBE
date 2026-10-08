#!/bin/bash
D=/home/user/CLAUDE-TO-YOUTUBE/영상제작/그래픽
S=/tmp/claude-0/-home-user-CLAUDE-TO-YOUTUBE/a67afec1-0479-542a-8e3c-4e6da4afdcc9/scratchpad
mkdir -p $S/g4
node $D/원본/render_new.mjs $D/원본 $S/g4
for f in $S/g4/*.webm; do n=$(basename "$f" .webm); ffmpeg -loglevel error -y -ss 0.5 -i "$f" -r 30 -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart -an "$D/영상_mp4/$n.mp4"; done
cp $S/g4/*.png $D/이미지_png/
echo "G4_DONE"
